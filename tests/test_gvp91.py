"""Unit and end-to-end verification tests for GVP91 (`src/gems91/gvp91.py` and `docs/run-card-GVP91.json`)."""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

from gems91 import dd_vtc_pu as DD
from gems91 import gvp91 as GVP
from gems91 import mhtr_coda as MC

ROOT = Path(__file__).resolve().parents[1]


def _synthetic_gvp_inputs(h: int = 48, w: int = 48):
    rng = np.random.default_rng(42)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False

    # Synthetic buried vertical contact at x = w // 2
    step = (xx >= (w // 2)).astype(np.float32)
    b02 = (10.0 * step + 2.0 * np.sin(yy / 6.0) + rng.normal(0, 0.2, (h, w))).astype(np.float32)
    # Horizontal gradient peaks at contact; vertical gradient changes sign across contact
    b03 = (5.0 * np.exp(-0.5 * ((xx - w / 2.0) / 2.0) ** 2) + 0.5 + rng.uniform(0, 0.2, (h, w))).astype(np.float32)
    b09 = (4.0 * np.tanh((xx - w / 2.0) / 2.0) + rng.normal(0, 0.1, (h, w))).astype(np.float32)
    b06 = (18.0 + 3.0 * step + rng.normal(0, 0.3, (h, w))).astype(np.float32)
    b07 = (10.0 + 2.0 * np.cos(xx / 8.0) + rng.uniform(0, 1.0, (h, w))).astype(np.float32)
    b08 = (1.5 * np.sin(yy / 7.0) + rng.normal(0, 0.2, (h, w))).astype(np.float32)
    b10 = (2.0 + rng.uniform(0, 1.0, (h, w))).astype(np.float32)
    b16 = (b10 + 3.0 * np.exp(-0.5 * ((xx - w / 2.0) ** 2 + (yy - h / 2.0) ** 2) / 16.0)).astype(np.float32)
    b11 = rng.normal(0, 0.3, (h, w)).astype(np.float32)
    b18 = (4.0 * np.exp(-0.5 * ((xx - w / 2.0) / 2.5) ** 2) + rng.normal(0, 0.2, (h, w))).astype(np.float32)
    b15 = (300.0 + 400.0 * step + rng.normal(0, 10.0, (h, w))).astype(np.float32)

    n_fp = int(fp.sum())
    eotvos_fp = rng.uniform(0.1, 1.0, n_fp).astype(np.float32)
    gdr_hw12_fp = rng.uniform(0.0, 1.0, n_fp).astype(np.float32)
    gdr_bg12_fp = rng.uniform(0.0, 1.0, n_fp).astype(np.float32)
    asc_aniso_fp = rng.uniform(0.2, 0.9, n_fp).astype(np.float32)
    asc_agree_fp = rng.uniform(0.2, 0.8, n_fp).astype(np.float32)
    dc_resid_fp = rng.uniform(0.0, 1.0, n_fp).astype(np.float32)
    dc_grad_fp = rng.uniform(0.0, 1.0, n_fp).astype(np.float32)

    return dict(
        b02_rtp=b02,
        b03_tmi_hg=b03,
        b06_tc=b06,
        b07_shear=b07,
        b08_dilat=b08,
        b09_tmi_vg=b09,
        b10_deq=b10,
        b11_gvy=b11,
        b15_depth=b15,
        b16_ieq=b16,
        b18_gvx=b18,
        eotvos_fp=eotvos_fp,
        gdr_hw12_fp=gdr_hw12_fp,
        gdr_bg12_fp=gdr_bg12_fp,
        asc_subsurface_aniso_fp=asc_aniso_fp,
        asc_az_agree_fp=asc_agree_fp,
        dc_cond_resid_fp=dc_resid_fp,
        dc_cond_grad_fp=dc_grad_fp,
        footprint=fp,
    )


def test_gvp91_features_shape_finiteness_and_contact_peak():
    inp = _synthetic_gvp_inputs(48, 48)
    fp = inp["footprint"]
    X, meta = GVP.compute_gvp91_features_from_grids(**inp)
    assert X.shape == (int(fp.sum()), 12)
    assert np.isfinite(X).all()
    assert meta["feature_names"] == GVP.GVP91_FEATURE_NAMES
    assert meta["label_free_100pct"] is True

    # Salem tilt-depth contact (col 2) should peak near the synthetic contact column x = 24
    salem_grid = np.zeros(fp.shape, dtype=np.float32)
    salem_grid[fp] = X[:, 2]
    assert salem_grid[3:, 22:27].mean() > salem_grid[3:, 4:14].mean()
    assert salem_grid[3:, 22:27].mean() > salem_grid[3:, 34:44].mean()


def test_model_b_column_set_is_strictly_topography_blind():
    assert len(GVP.MODEL_A_STATIC_COLS) + len(GVP.MODEL_A_S11_COLS) + len(GVP.MODEL_A_FUSE_COLS) + len(GVP.MODEL_A_GVP_COLS) == 91
    assert len(GVP.MODEL_B_STATIC_COLS) + len(GVP.MODEL_B_S11_COLS) + len(GVP.MODEL_B_FUSE_COLS) + len(GVP.MODEL_B_GVP_COLS) == 81

    # Verify zero topographic bands or topographic derivatives in Model B
    forbidden_static = {11, 18, 19, 20, 21, 22, 23, 34, 35, 36, 37, 42, 43, 46}
    assert not (set(GVP.MODEL_B_STATIC_COLS) & forbidden_static)
    for col in GVP.MODEL_B_STATIC_COLS:
        name = DD.ALL_STATIC_FEATURE_NAMES[col]
        assert "elev" not in name and "lrm" not in name and "topo" not in name

    forbidden_s11 = {6, 7, 14}
    assert not (set(GVP.MODEL_B_S11_COLS) & forbidden_s11)
    for col in GVP.MODEL_B_S11_COLS:
        name = MC.S11_MHTR_FEATURE_NAMES[col]
        assert "topo" not in name

    forbidden_fuse_det_elev = {28, 33, 38}
    assert not (set(GVP.MODEL_B_FUSE_COLS) & forbidden_fuse_det_elev)


def test_three_regime_submodular_emit_spacing_and_determinism():
    rng = np.random.default_rng(19)
    h, w = 64, 64
    surf = rng.uniform(0.05, 0.90, (h, w)).astype(np.float32)
    sub_surf = rng.uniform(0.05, 0.90, (h, w)).astype(np.float32)
    edge = rng.uniform(0.25, 0.95, (h, w)).astype(np.float32)
    vent = rng.uniform(0.30, 0.95, (h, w)).astype(np.float32)
    pied = np.zeros((h, w), dtype=bool)
    pied[:, :32] = True
    elig = np.ones((h, w), dtype=bool)

    d1 = GVP.gvp_three_regime_submodular_emit(
        surf, sub_surf, edge, vent, pied,
        eligible_mask=elig, n_dots=90, min_spacing_px=2.65,
    )
    d2 = GVP.gvp_three_regime_submodular_emit(
        surf, sub_surf, edge, vent, pied,
        eligible_mask=elig, n_dots=90, min_spacing_px=2.65,
    )
    assert np.array_equal(d1, d2)
    assert int((d1 > 0).sum()) == 90
    yy, xx = np.nonzero(d1 > 0)
    dists, _ = cKDTree(np.c_[yy, xx]).query(np.c_[yy, xx], k=2)
    assert float(dists[:, 1].min()) >= 2.65 - 1e-6


def test_gvp91_run_card_and_certified_geotiff_artifacts() -> None:
    rc_docs = json.loads((ROOT / "docs" / "run-card-GVP91.json").read_text(encoding="utf-8"))
    rc_ev = json.loads((ROOT / "evidence" / "gvp91_run_card.json").read_text(encoding="utf-8"))
    assert rc_docs == rc_ev

    assert rc_docs["verdict"] == "promote"
    assert rc_docs["submission_ready_pending_selector"] is True
    assert rc_docs["winning_experiment"] == "E2"
    assert rc_docs["budget"]["experiments_run"] == 3
    assert rc_docs["budget"]["wall_clock_seconds"] <= 7200
    assert rc_docs["leakage_canary"]["all_pass"] is True
    assert rc_docs["leakage_canary"]["n_features_tested"] == 104
    assert rc_docs["leakage_canary"]["worst_symmetric_auc"] <= 0.90
    assert rc_docs["leakage_canary"]["worst_gvp91_symmetric_auc"] <= 0.90

    ph = rc_docs["scores"]["primary_holdout"]
    assert ph["label"] == "HOLDOUT-DTI"
    assert ph["evaluator_version"] == "gems91-hide-recover-v1.0"
    assert ph["n_withheld_positives"] == 60988
    assert ph["score"] > ph["s11_e2_reference_holdout_dti"] > ph["fuse91_e1_reference_holdout_dti"] > ph["h91_e1_reference_holdout_dti"] > ph["b0_reference_holdout_dti"]
    assert ph["ci_95"][0] > ph["s11_e2_reference_ci_95"][1]  # Non-overlapping 95% CIs vs S11-E2!

    cb = rc_docs["scores"]["secondary_checkerboard_400px_holdout"]
    assert cb["label"] == "HOLDOUT-DTI"
    assert cb["n_withheld_positives"] == 60988
    assert cb["pooled_holdout_dti"] > cb["fuse91_e1_reference_dti"] > cb["denovo_hgb_ctx_reference_dti"]
    assert cb["ci_95"][0] > 0.168782  # Non-overlapping 95% CI vs FUSE91 E1!

    sgmc = rc_docs["scores"]["blind_sgmc_offcatalogue_control"]
    assert sgmc["dti"] > 0.100  # First candidate in repo > 0.100 on blind SGMC control

    uniq = rc_docs["registry_uniqueness"]
    assert uniq["uniqueness_pass"] is True
    assert uniq["rasters_checked"] == 69
    assert uniq["max_surface_abs_rank_corr"] <= 0.90
    assert uniq["max_3px_dot_overlap"] <= 0.70

    sub = rc_docs["submission"]
    assert 1 <= len(sub["recommended_form_note"]) <= 140
    assert sub["recommended_form_note_length"] == len(sub["recommended_form_note"])

    tif_path = ROOT / "docs" / "downloads" / sub["recommended_upload_file"]
    zip_path = ROOT / "docs" / "downloads" / sub["recommended_zip_download"]
    audit_path = ROOT / "docs" / "downloads" / sub["audit_json"]
    assert tif_path.is_file()
    assert zip_path.is_file()
    assert audit_path.is_file()

    tif_bytes = tif_path.read_bytes()
    assert len(tif_bytes) == sub["bytes_zeros_tif"]
    assert hashlib.sha256(tif_bytes).hexdigest() == sub["sha256_zeros_tif"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == sub["sha256_zeros_zip"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [sub["recommended_upload_file"]]
        assert zf.read(sub["recommended_upload_file"]) == tif_bytes

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0
        assert float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == sub["n_dots"]

    for html_rel in (Path("docs/gvp91.html"), Path("docs/gvp91-executive-summary.html")):
        hp = ROOT / html_rel
        assert hp.is_file()
        txt = hp.read_text(encoding="utf-8")
        assert sub["candidate_id"] in txt
        assert sub["sha256_zeros_tif"] in txt
        assert sub["recommended_form_note"] in html.unescape(txt)
        for m in re.finditer(r'(?:href|src)="([^"]+)"', txt):
            target = m.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
                continue
            clean_rel = target.split("#", 1)[0].split("?", 1)[0]
            if not clean_rel:
                continue
            resolved = (hp.parent / clean_rel).resolve()
            assert resolved.exists(), f"Broken link {target!r} in {html_rel}"
            rel_to_root = resolved.relative_to(ROOT)
            ign = subprocess.run(["git", "check-ignore", "-q", str(rel_to_root)], cwd=ROOT)
            assert ign.returncode != 0, f"GitHub Pages asset {rel_to_root} is gitignored!"

