"""Unit tests for Session 17 (`S17-CDSC`) physics, prevalence calibration, and
bitwise `B12`/`B19`-invariant Pure-Subsurface specialist isolation.
"""

from __future__ import annotations

import numpy as np
import pytest

from gems91 import cdsc17 as CDSC
from gems91 import dd_vtc_pu as DD
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA


def _s17_feature_names() -> list[str]:
    s13_static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    static_names = [DD.ALL_STATIC_FEATURE_NAMES[i] for i in s13_static_cols]
    s11_names = list(MC.S11_MHTR_FEATURE_NAMES)
    ptha_names = list(PTHA.PTHA_FEATURE_NAMES)
    return (
        static_names
        + s11_names
        + ptha_names
        + CDSC.S17_LOCAL_S15_NAMES
        + CDSC.S17_AUTOCONTEXT_NAMES
    )


def test_s17_feature_dimensions_and_pure_subsurface_mask() -> None:
    names = _s17_feature_names()
    assert len(names) == 105
    assert len(set(names)) == 105
    sub_mask = CDSC.pure_subsurface_feature_mask(names)
    assert sub_mask.shape == (105,)
    assert int(sub_mask.sum()) == 72
    for nm, keep in zip(names, sub_mask):
        if keep:
            assert nm not in CDSC.S17_STRICT_TOPO_FEATURE_NAMES
            assert "elev" not in nm and "topo" not in nm and "lrm" not in nm


def test_prevalence_calibration_remediates_ir91_s15_06() -> None:
    fp = np.ones((16, 16), dtype=bool)
    pair_prob = np.full((16, 16), 0.12, dtype=np.float32)
    cal = CDSC.calibrate_pair_to_target_prevalence(
        pair_prob,
        fp,
        pair_pi_sample=0.12,
        target_pi_sample=0.20,
    )
    assert np.allclose(cal, 0.20, atol=1e-5)
    same = CDSC.calibrate_pair_to_target_prevalence(
        pair_prob,
        fp,
        pair_pi_sample=0.12,
        target_pi_sample=0.12,
    )
    assert np.allclose(same, pair_prob, atol=1e-6)


def test_faulds_hinz_en_echelon_relay_and_junction_operators() -> None:
    h, w = 40, 40
    fp = np.ones((h, w), dtype=bool)
    # Create an en-echelon stepped fault across a gap at row 20 (col 18 -> col 22)
    surf = np.zeros((h, w), dtype=np.float32)
    surf[6:18, 18] = 0.90
    surf[22:34, 22] = 0.90
    ac = CDSC.compute_s17_calibrated_autocontext_features(surf, fp)
    assert ac.shape == (h * w, 14)
    assert np.isfinite(ac).all()
    relay_250 = ac[:, 10].reshape(h, w)
    # The step-over center (20, 20) should have strong en-echelon relay response
    assert float(relay_250[20, 20]) > float(relay_250[5, 5]) + 0.15


def test_stage2_pure_subsurface_specialist_is_bitwise_topo_invariant() -> None:
    names = _s17_feature_names()
    h, w = 24, 24
    fp = np.ones((h, w), dtype=bool)
    n_fp = h * w
    rng = np.random.default_rng(1701)
    X_a = rng.standard_normal((n_fp, 105)).astype(np.float32)
    X_b = X_a.copy()
    sub_mask = CDSC.pure_subsurface_feature_mask(names)
    # Massively perturb every topographic / Stage-1 AC column (`~sub_mask`) with independent noise
    X_b[:, ~sub_mask] = rng.standard_normal(X_b[:, ~sub_mask].shape).astype(np.float32) * 5.0

    vis = np.zeros((h, w), dtype=bool)
    vis[3:10, 5] = True
    vis[14:21, 18] = True
    excl = np.zeros((h, w), dtype=bool)

    base_a, sub_a, meta_a = CDSC.fit_predict_s17_stage2(
        train_blocks=[(X_a, list(range(105)))],
        infer_blocks=[(X_a, list(range(105)))],
        feature_names=names,
        visible_faults=vis,
        exclude_mask=excl,
        footprint=fp,
        seed=1702,
    )
    base_b, sub_b, meta_b = CDSC.fit_predict_s17_stage2(
        train_blocks=[(X_b, list(range(105)))],
        infer_blocks=[(X_b, list(range(105)))],
        feature_names=names,
        visible_faults=vis,
        exclude_mask=excl,
        footprint=fp,
        seed=1702,
    )
    # Pure-subsurface specialist must be 100% bitwise identical despite B12/B19 perturbation
    assert np.array_equal(sub_a, sub_b)
    assert meta_a["n_pure_subsurface_features"] == 72
    assert not np.allclose(base_a, base_b)


def test_s17_crest_and_concealed_pool_bounds() -> None:
    h, w = 20, 20
    fp = np.ones((h, w), dtype=bool)
    fp[:2, :] = False
    n_fp = int(fp.sum())
    rng = np.random.default_rng(1703)
    ptha_crest = np.clip(rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32), 0.0, 1.0)
    s15_crest = np.clip(rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32), 0.0, 1.0)
    ac_fp = np.clip(rng.uniform(0.0, 1.0, size=(n_fp, 14)).astype(np.float32), 0.0, 1.0)
    X_s15 = rng.standard_normal((n_fp, 18)).astype(np.float32)

    crest = CDSC.build_s17_relay_subsurface_concordant_crest(
        ptha_crest, s15_crest, ac_fp, fp
    )
    assert np.isfinite(crest).all()
    assert float(crest.min()) >= 0.0 and float(crest.max()) <= 1.0
    assert float(crest[~fp].max()) == 0.0

    p1 = np.clip(rng.uniform(0.01, 0.99, size=(h, w)).astype(np.float32), 0.0, 1.0)
    p2b = np.clip(rng.uniform(0.01, 0.99, size=(h, w)).astype(np.float32), 0.0, 1.0)
    p2s = np.clip(rng.uniform(0.01, 0.99, size=(h, w)).astype(np.float32), 0.0, 1.0)
    pied = (rng.uniform(0.0, 1.0, size=(h, w)) > 0.5) & fp
    pool = CDSC.build_s17_concealed_subsurface_corroborated_pool(
        p1, p2b, p2s, pied, X_s15, fp
    )
    assert np.isfinite(pool).all()
    assert float(pool.min()) >= 0.0 and float(pool.max()) <= 1.0
    assert float(pool[~fp].max()) == 0.0


def test_s17_run_card_artifact_and_portal_integrity() -> None:
    import hashlib
    import json
    from pathlib import Path
    import zipfile
    import rasterio
    from gems91.readiness import gates, submission_ready

    root = Path(__file__).resolve().parents[1]
    card = json.loads((root / "docs/run-card-S17-CDSC.json").read_text(encoding="utf-8"))
    ev = json.loads((root / "evidence/s17_cdsc_20261025.json").read_text(encoding="utf-8"))
    assert card == ev

    prereg_sha = hashlib.sha256((root / "docs/HYPOTHESES_S17_CDSC.md").read_bytes()).hexdigest()
    assert card["preregistration"]["sha256"] == prereg_sha

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

    # Verify IR-91-S15-06 scale alignment audit & holdout gains over S13-PTHA and S15-SCGF
    scale_audit = card["ir91_s15_06_scale_alignment_audit"]
    assert scale_audit["NW"]["calibrated_test_over_train_ratio"] < scale_audit["NW"]["uncalibrated_test_over_train_ratio"]
    assert scale_audit["NE"]["calibrated_test_over_train_ratio"] < scale_audit["NE"]["uncalibrated_test_over_train_ratio"]
    assert card["holdout_dti"]["value"] > card["comparable_prior_holdout_best"]["prior_s13_ptha_e3_value"]
    assert card["holdout_dti"]["value"] > card["comparable_prior_holdout_best"]["prior_s15_scgf_e2_value"]
    assert card["holdout_dti"]["paired_vs_s13_ptha_e3"]["ci95"][0] > 0.0

    # Verify external fleet novelty (<= 70% PASS) vs literal blanket fail-closed
    ext_nov = card["registry_comparison"]["summary"]["disaggregated_external_fleet_real_only"]
    assert ext_nov["passes_70pct_bar_vs_external_real_submissions"] is True
    assert ext_nov["max_3px_dot_overlap_vs_external_real_submissions"] <= 0.70

    tif_path = root / card["artifact"]["primary_zeros_tif"]
    zip_path = root / card["artifact"]["zip_bundle"]
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["artifact"]["zip_sha256"]
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()
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

