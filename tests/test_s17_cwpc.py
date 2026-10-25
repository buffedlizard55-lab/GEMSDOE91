from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems91 import cwpc17 as CWPC

ROOT = Path(__file__).resolve().parents[1]
RUN_CARD_PATH = ROOT / "docs/run-card-S17-CWPC.json"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_cwpc_physics_and_calibration_unit() -> None:
    rng = np.random.default_rng(17)
    shape = (48, 52)
    fp = np.zeros(shape, dtype=bool)
    fp[4:44, 5:47] = True

    bands = {
        name: rng.normal(size=shape).astype(np.float32)
        for name in (
            "rtp",
            "tc",
            "iso_grav_anom",
            "cond_surf",
            "tmi",
            "tmi_hg",
            "tmi_vg",
                "iso_grav_anom_hg",
                "iso_grav_anom_vg",
                "iso_grav_anom_slope",
                "depth_to_base_surf",
            "geod_shearrate",
            "geod_dilaterate",
            "geod_2ndinv",
            "deq_n100a15",
            "ieq_n100a15",
        )
    }
    bands["tc"] = np.abs(bands["tc"]) + 5.0
    bands["depth_to_base_surf"] = np.abs(bands["depth_to_base_surf"]) * 800.0

    buf = np.zeros((len(CWPC.CWPC_PHYSICS_FEATURE_NAMES), *shape), dtype=np.float16)
    stack, names = CWPC.build_cwpc_physics_features(
        bands, fp, out_dtype=np.float16, out_buffer=buf
    )
    assert names == CWPC.CWPC_PHYSICS_FEATURE_NAMES
    assert stack.shape == (16, 48, 52)
    assert stack.dtype == np.float16
    assert np.isfinite(stack).all()
    assert np.all(stack[:, ~fp] == 0.0)

    # Prior-shift calibration (IR-91-S15-06)
    raw_p = np.clip(rng.beta(2.0, 6.0, size=shape).astype(np.float32), 0.0, 1.0)
    cal = CWPC.prior_shift_calibrate_surface(raw_p, fp, pi_true=0.012, pi_sample=0.25)
    assert cal.shape == shape
    assert cal.dtype == np.float32
    assert np.all(cal[~fp] == 0.0)
    assert 0.0 <= float(cal.min()) <= float(cal.max()) <= 1.0
    assert float(cal[fp].mean()) < float(raw_p[fp].mean())

    # Local <=900m auto-context features (IR-91-S15-07)
    crest = np.abs(stack[0].astype(np.float32))
    ac_stack, ac_names = CWPC.build_local_autocontext_features(
        cal, crest, fp, out_dtype=np.float16
    )
    assert ac_names == CWPC.AUTOCONTEXT_FEATURE_NAMES
    assert ac_stack.shape == (7, 48, 52)
    assert np.isfinite(ac_stack).all()
    assert np.all(ac_stack[:, ~fp] == 0.0)

    # Topographic exclusion invariant (IR-91-S15-05)
    assert {"det_elev", "det_elev_slope", "det_elev_grad", "det_elev_slope_grad"} <= set(
        CWPC.TOPO_DEPENDENT_FEATURE_NAMES
    )


def test_s17_cwpc_run_card_and_artifact_contracts() -> None:
    assert RUN_CARD_PATH.is_file()
    rc = json.loads(RUN_CARD_PATH.read_text(encoding="utf-8"))

    assert rc["session_id"] == "S17-CWPC"
    assert rc["branch"] == "arena/4f695c18-gemsdoe91"
    prereg_path = ROOT / rc["lane"]["preregistration_path"]
    assert prereg_path.is_file()
    assert _sha256(prereg_path) == rc["lane"]["preregistration_sha256"]

    assert rc["experiments_run"] == 3
    assert rc["slots_used"] == 0
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False
    assert rc["submission_ready"] is False
    assert rc["verdict"] == "negative"
    assert 1 <= len(rc["note"]) <= 140
    assert 1 <= len(rc["submission_name"]) <= 140

    # Leakage canary contract (Rule 4)
    canary = rc["leakage_canary"]
    assert canary["all_pass"] is True
    assert canary["n_features_tested"] == 43
    assert canary["worst_symmetric_auc"] <= 0.90
    for diag in rc["holdout_dti"]["e3_prior_shift_calibration_diagnostics"]:
        for auc_v in diag["autocontext_canaries"].values():
            assert auc_v <= 0.90

    # Holdout DTI contract (Rule 3)
    hd = rc["holdout_dti"]
    assert hd["label"] == "HOLDOUT-DTI"
    assert hd["evaluator_version"] == "gems57-pooled-hide-v2"
    assert hd["withheld_positives"] == 60988
    exps = hd["experiments"]
    assert set(exps.keys()) == {
        "E1_cwpc_physics_hgb",
        "E2_cwpc_integrated_hgb",
        "E3_cwpc_calibrated_dual_autocontext",
    }
    assert exps["E2_cwpc_integrated_hgb"]["holdout_dti_gems57_v2"]["dti"] > exps["E1_cwpc_physics_hgb"]["holdout_dti_gems57_v2"]["dti"]
    assert exps["E3_cwpc_calibrated_dual_autocontext"]["holdout_dti_gems57_v2"]["paired_differences"]["random_null"]["delta"] > 0.0

    # Registry uniqueness contract (Rule 1)
    reg = rc["registry_comparison"]
    assert reg["r0_comparison"]["dot_overlap_3px"] <= 0.70
    assert abs(reg["r0_comparison"]["surface_spearman"]) <= 0.90
    assert reg["repo_and_r0_scope"]["pass_vs_r0_and_nonblanket"] is True
    assert reg["repo_and_r0_scope"]["max_dot_overlap_3px"] <= 0.70

    # GeoTIFF + ZIP format contract
    tif_path = ROOT / rc["artifact"]["primary_zeros_tif"]
    zip_path = ROOT / rc["artifact"]["zip_bundle"]
    assert tif_path.is_file()
    assert zip_path.is_file()
    assert _sha256(tif_path) == rc["raster_sha256"]
    assert _sha256(zip_path) == rc["artifact"]["zip_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert (ds.height, ds.width) == (3730, 3292)
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert ds.nodata is None
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0
        assert float(arr.max()) <= 1.0
        assert int((arr > 0).sum()) == 37654

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert hashlib.sha256(zf.read(names[0])).hexdigest() == rc["raster_sha256"]
