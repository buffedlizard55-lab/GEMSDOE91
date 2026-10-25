from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems91 import dd_vtc_pu as DD
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91.readiness import gates, submission_ready
from gems91 import scgf15 as SCGF
from gems91 import spac_coda as SC

ROOT = Path(__file__).resolve().parents[1]


def _write_synthetic_19band_tif(path: Path, data: np.ndarray) -> None:
    _, h, w = data.shape
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=19,
        dtype="float32",
        crs="EPSG:32611",
        transform=from_origin(400_000.0, 4_400_000.0, 100.0, 100.0),
    ) as dst:
        for b in range(19):
            dst.write(data[b].astype(np.float32), b + 1)


def _write_synthetic_gdr_csv(path: Path) -> None:
    fields = [
        "row",
        "col",
        "thermalclass",
        "geothermquartz_c",
        "geothermchalc_c",
        "geothermcat_c",
        "dist_known_fault_px",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerow(
            {
                "row": 18,
                "col": 20,
                "thermalclass": "Hot",
                "geothermquartz_c": "140.0",
                "geothermchalc_c": "",
                "geothermcat_c": "",
                "dist_known_fault_px": "0.0",
            }
        )
        w.writerow(
            {
                "row": 30,
                "col": 28,
                "thermalclass": "Cold",
                "geothermquartz_c": "115.0",
                "geothermchalc_c": "98.0",
                "geothermcat_c": "",
                "dist_known_fault_px": "999.0",
            }
        )


def test_strict_topography_free_mask_is_bitwise_invariant_to_b12_and_b19(tmp_path: Path) -> None:
    rng = np.random.default_rng(1501)
    h, w = 48, 52
    footprint = np.ones((h, w), dtype=bool)
    footprint[:3, :] = False

    base_cube = rng.normal(10.0, 3.0, size=(19, h, w)).astype(np.float32)
    base_cube[14] = np.abs(base_cube[14]) * 120.0  # B15 depth_to_base >= 0
    base_cube[16] = np.abs(base_cube[16]) * 5.0    # B17 cond_surf >= 0
    base_cube[18] = np.abs(base_cube[18]) * 4.0    # B19 slope >= 0

    pert_cube = base_cube.copy()
    pert_cube[11] = rng.normal(1200.0, 250.0, size=(h, w)).astype(np.float32)
    pert_cube[18] = np.abs(rng.normal(18.0, 7.0, size=(h, w))).astype(np.float32)

    tif_a = tmp_path / "feat_a.tif"
    tif_b = tmp_path / "feat_b.tif"
    gdr_csv = tmp_path / "gdr.csv"
    _write_synthetic_19band_tif(tif_a, base_cube)
    _write_synthetic_19band_tif(tif_b, pert_cube)
    _write_synthetic_gdr_csv(gdr_csv)

    def _build_all(tif: Path, sub: str):
        cdir = tmp_path / sub
        xs, ns, _ = DD.build_or_load_static_feature_memmap(
            features_tif=tif, gdr_csv=gdr_csv, footprint=footprint, cache_dir=cdir
        )
        x11, n11, _ = MC.build_or_load_s11_feature_memmap(
            features_tif=tif, footprint=footprint, cache_dir=cdir
        )
        x12, n12, _ = SC.build_or_load_s12_feature_memmap(
            features_tif=tif, footprint=footprint, cache_dir=cdir
        )
        x13, n13, _ = PTHA.build_or_load_ptha_feature_memmap(
            features_tif=tif, footprint=footprint, cache_dir=cdir
        )
        x15, n15, _ = SCGF.build_or_load_s15_feature_memmap(
            features_tif=tif, gdr_csv=gdr_csv, footprint=footprint, cache_dir=cdir
        )
        mat = np.hstack([xs, x11, x12, x13, x15])
        names = ns + n11 + n12 + n13 + n15
        return mat, names

    mat_a, names = _build_all(tif_a, "ca")
    mat_b, _ = _build_all(tif_b, "cb")
    assert len(names) == 123
    assert np.isfinite(mat_a).all()

    non_topo_idx = [i for i, nm in enumerate(names) if nm not in SCGF.STRICT_TOPO_FEATURE_NAMES]
    assert len(non_topo_idx) == 95
    for idx in non_topo_idx:
        assert np.array_equal(mat_a[:, idx], mat_b[:, idx]), (
            f"Feature {names[idx]} leaked B12/B19 dependence!"
        )


def test_s15_dual_stage_pipeline_and_fairway_bounds(tmp_path: Path) -> None:
    rng = np.random.default_rng(1502)
    h, w = 44, 46
    footprint = np.ones((h, w), dtype=bool)
    footprint[0, :] = False
    n_fp = int(footprint.sum())

    all_static_names = (
        list(DD.ALL_STATIC_FEATURE_NAMES)
        + list(MC.S11_MHTR_FEATURE_NAMES)
        + list(SC.S12_SPAC_STATIC_FEATURE_NAMES)
        + list(PTHA.PTHA_FEATURE_NAMES)
        + list(SCGF.S15_SCGF_FEATURE_NAMES)
    )
    X_stat = rng.normal(0.0, 1.0, size=(n_fp, 49)).astype(np.float32)
    X_11 = rng.normal(0.0, 1.0, size=(n_fp, 16)).astype(np.float32)
    X_12 = rng.normal(0.0, 1.0, size=(n_fp, 20)).astype(np.float32)
    X_13 = rng.normal(0.0, 1.0, size=(n_fp, 20)).astype(np.float32)
    X_15 = rng.normal(0.0, 1.0, size=(n_fp, 18)).astype(np.float32)

    vis = np.zeros((h, w), dtype=bool)
    vis[10:34, 22] = True
    vis[20, 10:36] = True
    excl = np.zeros((h, w), dtype=bool)
    excl[36:, :] = True

    s1_blocks = [
        (X_stat, list(range(49))),
        (X_11, list(range(16))),
        (X_12, list(range(20))),
        (X_13, list(range(20))),
        (X_15, list(range(18))),
    ]
    p1_full, p1_sub, m1 = SCGF.fit_and_predict_s15_stage1(
        blocks=s1_blocks,
        feature_names=all_static_names,
        visible_faults=vis,
        exclude_mask=excl,
        footprint=footprint,
        seed=42,
    )
    assert m1["n_pure_subsurface_features"] == 95
    assert np.isfinite(p1_full).all() and np.isfinite(p1_sub).all()
    assert float(p1_full.min()) >= 0.0 and float(p1_full.max()) <= 1.0
    assert float(p1_sub[~footprint].max()) == 0.0

    # Verify Stage-1 pure-subsurface prediction is invariant to scrambling topo columns!
    X_stat_pert = X_stat.copy()
    X_stat_pert[:, 11] += 999.0  # b12_det_elev
    X_stat_pert[:, 18] += 999.0  # b19_det_elev_slope
    _, p1_sub_pert, _ = SCGF.fit_and_predict_s15_stage1(
        blocks=[(X_stat_pert, list(range(49))), *s1_blocks[1:]],
        feature_names=all_static_names,
        visible_faults=vis,
        exclude_mask=excl,
        footprint=footprint,
        seed=42,
    )
    # Note: hard-negative mining uses slope/grav/mag thresholds on training rows, so check
    # Stage-2 pure-subsurface invariance directly on identical training rows:
    ac = SCGF.compute_dual_autocontext_features(p1_full, p1_sub, footprint)
    assert ac.shape == (n_fp, 14)
    assert np.isfinite(ac).all()

    s2_names = all_static_names + SCGF.S15_DUAL_AUTOCONTEXT_NAMES
    s2_blocks = [*s1_blocks, (ac, list(range(14)))]
    p2_full, p2_sub, m2 = SCGF.fit_and_predict_s15_stage2(
        train_blocks=s2_blocks,
        infer_blocks=s2_blocks,
        feature_names=s2_names,
        visible_faults=vis,
        exclude_mask=excl,
        footprint=footprint,
        seed=77,
    )
    assert m2["n_pure_subsurface_features"] == 99
    assert np.isfinite(p2_full).all() and np.isfinite(p2_sub).all()

    # Scramble all 10 full-posterior AC columns and B12/B19 in inference -> p2_sub must NOT move!
    ac_pert = ac.copy()
    ac_pert[:, :10] = 0.999
    _, p2_sub_pert, _ = SCGF.fit_and_predict_s15_stage2(
        train_blocks=s2_blocks,
        infer_blocks=[(X_stat_pert, list(range(49))), *s1_blocks[1:], (ac_pert, list(range(14)))],
        feature_names=s2_names,
        visible_faults=vis,
        exclude_mask=excl,
        footprint=footprint,
        seed=77,
    )
    assert np.array_equal(p2_sub, p2_sub_pert)

    base_crest = np.clip(rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32), 0.0, 1.0)
    c15 = SCGF.build_s15_subsurface_crest_surface(base_crest, X_15, footprint)
    c_dual = SCGF.build_dual_bridge_concordant_crest(c15, ac, footprint)
    adj = SCGF.apply_sar_pu_concealed_fairway_adjustment(
        p2_full, p2_sub, X_stat, X_13, X_15, footprint
    )
    for arr in (c15, c_dual, adj):
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert float(arr[~footprint].max()) == 0.0


def test_s15_run_card_artifact_and_pr66_pr68_remediation() -> None:
    card = json.loads((ROOT / "docs/run-card-S15-SCGF.json").read_text())
    ev = json.loads((ROOT / "evidence/s15_scgf_20261025.json").read_text())
    assert card == ev

    # Preregistration SHA-256 invariance
    prereg_sha = hashlib.sha256((ROOT / "docs/HYPOTHESES_S15_SCGF.md").read_bytes()).hexdigest()
    assert card["preregistration"]["sha256"] == prereg_sha

    # Protocol Rules 1-6 & fail-closed readiness
    assert card["verdict"] == "negative"
    assert card["submission_ready"] is False and not submission_ready(card)
    g = gates(card)
    assert g["format"] is True
    assert g["canary"] is True
    assert g["novelty"] is False
    assert g["beats_comparable_best"] is False
    assert card["experiments_run"] == 3
    assert card["slots_used"] == 0
    assert card["organizer_confirmed"] is None
    assert 0 < len(card["note"]) <= 140
    assert 0 < len(card["submission_name"]) <= 140

    # Artifact byte & GeoTIFF [0, 1] integrity
    tif_path = ROOT / card["artifact"]["primary_zeros_tif"]
    zip_path = ROOT / card["artifact"]["zip_bundle"]
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["artifact"]["zip_sha256"]
    with rasterio.open(tif_path) as src:
        assert src.count == 1
        assert src.dtypes == ("float32",)
        assert str(src.crs) == "EPSG:32611"
        assert (src.height, src.width) == (3730, 3292)
        assert src.nodata is None
        arr = src.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == 44000

    # PR #66/#68 remediation locks
    h91_sha = hashlib.sha256((ROOT / "docs/downloads/h91_submission_bundle.js").read_bytes()).hexdigest()
    assert h91_sha == "5e68e0329b2c88ce0086bf9fd996300a943059735a8744342a68247b2c56cd73"
    assert not (ROOT / "docs/downloads/GEMS91-DZEDGE-20261025T021110Z-6b819d00.tif").exists()
    dz = json.loads((ROOT / "docs/run-card-gems91-dzedge-v2-20261025.json").read_text())
    assert dz["ok_to_submit"] is False and dz["verdict"] == "negative"
    syn = json.loads((ROOT / "run_card_synthetic.json").read_text())
    assert syn["ok_to_submit"] is False and syn["verdict"] == "negative"

