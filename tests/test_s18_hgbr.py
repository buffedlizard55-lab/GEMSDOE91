"""Unit and integration verification suite for Session 18 (`S18-HGBR`)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import rasterio

from gems91 import hgbr18 as HGBR

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_hgbr_feature_names_and_strict_topo_isolation():
    assert len(HGBR.HGBR_FEATURE_NAMES) == 16
    assert len(set(HGBR.HGBR_FEATURE_NAMES)) == 16
    subsurface_14 = set(HGBR.HGBR_FEATURE_NAMES[:14])
    topo_2 = set(HGBR.HGBR_FEATURE_NAMES[14:])
    assert topo_2 == {"hgbr18_elev_hurst_break", "hgbr18_slope_variogram_step"}
    assert topo_2 <= HGBR.STRICT_TOPO_FEATURE_NAMES
    assert subsurface_14.isdisjoint(HGBR.STRICT_TOPO_FEATURE_NAMES)


def test_local_hurst_and_anisotropy_synthetic_step_vs_ramp():
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")

    # Smooth planar ramp has H ~ 1 (low deficit), whereas sharp N-S fault step at x=32 has high deficit & anisotropy
    ramp = 0.05 * xx
    step = np.where(xx >= 32.0, 4.0, 0.0).astype(np.float32) + 0.02 * yy
    psi_ns = np.full((h, w), np.pi / 2.0, dtype=np.float32)

    res_ramp = HGBR.compute_local_hurst_and_anisotropy(ramp, fp, strike_psi=psi_ns)
    res_step = HGBR.compute_local_hurst_and_anisotropy(step, fp, strike_psi=psi_ns)

    for k in ("deficit", "anisotropy", "scale_break"):
        assert np.isfinite(res_step[k]).all()
        assert np.all(res_step[k][~fp] == 0.0)

    # Fault trace at x=32 has significantly higher Hurst deficit and strike anisotropy than interior ramp
    assert float(res_step["deficit"][20:44, 31:34].mean()) > float(res_ramp["deficit"][20:44, 10:20].mean()) + 0.25
    assert float(res_step["anisotropy"][20:44, 31:34].mean()) > float(res_step["anisotropy"][20:44, 10:20].mean()) + 0.25


def test_asymmetric_cover_specialist_pool_never_vetoes_exposed_scarp():
    shape = (10, 10)
    fp = np.ones(shape, dtype=bool)
    n_fp = int(fp.sum())

    s1_full = np.full(shape, 0.70, dtype=np.float32)
    s2_full = np.full(shape, 0.80, dtype=np.float32)
    # Pure-subsurface is weaker on an exposed scarp (0.20) on top half, stronger on buried fault (0.92) on bottom half
    s1_sub = np.full(shape, 0.20, dtype=np.float32)
    s2_sub = np.full(shape, 0.20, dtype=np.float32)
    s1_sub[5:, :] = 0.90
    s2_sub[5:, :] = 0.92

    cover = np.full(n_fp, 0.85, dtype=np.float32)
    crest = np.full(n_fp, 0.35, dtype=np.float32)

    full_only = HGBR.pool_full_specialist_with_crest(
        s1_full, s2_full, crest, fp, stage2_weight=0.66, crest_alpha=0.0
    )
    dual = HGBR.pool_asymmetric_cover_specialists(
        s1_full=s1_full,
        s1_sub=s1_sub,
        s2_full=s2_full,
        s2_sub=s2_sub,
        cover_prior_fp=cover,
        crest_bonus_fp=crest,
        footprint=fp,
        stage2_weight=0.66,
        max_cover_rescue_weight=0.42,
        cover_threshold=0.38,
        crest_alpha=0.0,
    )
    # Top half (where sub < full): zero suppression relative to full_only!
    np.testing.assert_allclose(dual[:5, :], full_only[:5, :], rtol=1e-5, atol=1e-6)
    # Bottom half (where sub > full under high cover): strictly rescued above full_only!
    assert np.all(dual[5:, :] > full_only[5:, :] + 0.04)


def test_align_stage1_log_odds_dispersion_and_oof_stitch():
    shape = (20, 20)
    fp = np.ones(shape, dtype=bool)
    rng = np.random.default_rng(42)
    surf = np.clip(rng.beta(0.5, 10.0, size=shape).astype(np.float32), 1e-4, 0.99)
    reg = np.zeros(shape, dtype=bool)
    reg[:10, :] = True

    aligned = HGBR.align_stage1_log_odds_dispersion(surf, reg, target_upper_span=3.2, footprint=fp)
    assert aligned.shape == shape
    assert np.isfinite(aligned).all()
    assert np.all((aligned >= 0.0) & (aligned <= 1.0))
    # Outside reg is untouched
    np.testing.assert_array_equal(aligned[10:, :], surf[10:, :])

    folds = [
        {"region": reg},
        {"region": ~reg},
    ]
    cat = np.zeros(shape, dtype=bool)
    cat[5, 5] = True
    stitched = HGBR.stitch_oof_full_map_surface(
        [surf, aligned], folds, cat, fp, feather_px=2.0, halo_radius_px=6.0, halo_atten=0.40
    )
    assert stitched.shape == shape
    assert np.isfinite(stitched).all()
    assert np.all((stitched >= 0.0) & (stitched <= 1.0))


def test_s18_hgbr_run_card_holdout_and_artifact_integrity():
    prereg = ROOT / "docs/HYPOTHESES_S18_HGBR.md"
    card_path = ROOT / "docs/run-card-S18-HGBR.json"
    holdout_path = ROOT / "docs/s18_hgbr/holdout.json"
    canaries_path = ROOT / "docs/s18_hgbr/canaries.json"
    sgmc_path = ROOT / "docs/s18_hgbr/blind-sgmc.json"
    features_path = ROOT / "docs/s18_hgbr/features.json"

    for p in (prereg, card_path, holdout_path, canaries_path, sgmc_path, features_path):
        assert p.is_file(), f"Missing S18-HGBR artifact: {p}"

    card = json.loads(card_path.read_text())
    holdout = json.loads(holdout_path.read_text())
    canaries = json.loads(canaries_path.read_text())
    sgmc = json.loads(sgmc_path.read_text())
    feats = json.loads(features_path.read_text())

    # 1. Preregistration SHA-256 match
    assert card["preregistration"]["sha256"] == _sha256(prereg)

    # 2. Rule 4 Canaries & IR-91-S15-05 Topo Isolation
    assert canaries["all_pass"] is True
    assert canaries["n_features_tested"] == 171
    assert canaries["max_pooled_symmetric_auc"] <= 0.90
    assert canaries["max_quadrant_symmetric_auc"] <= 0.90
    assert feats["ir_91_s15_05_subsurface_topo_overlap"] == 0

    # 3. Rule 3 Labels & Holdout Improvement over S17-CPAD E1 and INCUMBENT-PTAC-LB
    assert card["evaluator"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["evaluator"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["evaluator"]["withheld_positive_pixels"] == 60988
    win_dti = float(card["holdout_results"]["dti"])
    assert win_dti > 0.2000
    assert holdout["beats_s17_cpad_e1"] is True
    assert holdout["beats_incumbent_ptac_lb"] is True
    assert win_dti > float(holdout["s17_cpad_reference"]["cpad_e1"]["dti"])
    assert win_dti > float(holdout["s17_cpad_reference"]["incumbent_ptac_lb"]["dti"])

    # 4. Blind Off-Catalogue USGS SGMC Control beats GEMSDOE32 R0 and S17-LFTG at >300m, >500m, >1km
    s18_sgmc = sgmc["scores"]["s18_hgbr_winner"]
    r0_sgmc = sgmc["scores"]["gemsdoe32_r0"]
    lftg_sgmc = sgmc["scores"]["s17_lftg"]
    for k in ("dti_gt_300m", "dti_gt_500m", "dti_gt_1km"):
        assert float(s18_sgmc[k]) > float(r0_sgmc[k])
        assert float(s18_sgmc[k]) > float(lftg_sgmc[k])

    # 5. Generated GeoTIFF and single-TIFF ZIP validation
    tif_path = ROOT / card["artifact"]["tif_path"]
    zip_path = ROOT / card["artifact"]["zip_path"]
    assert tif_path.is_file() and zip_path.is_file()
    assert _sha256(tif_path) == card["artifact"]["tif_sha256"]
    assert _sha256(zip_path) == card["artifact"]["zip_sha256"]
    assert 1 <= card["artifact"]["submission_note_length"] <= 140
    assert card["budget"]["experiments_run"] <= 3
    assert card["budget"]["slots_used"] == 0

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert ds.dtypes == ("float32",)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.shape == (3730, 3292)
        assert ds.nodata is None
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
        assert int((arr > 0).sum()) == 37654

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert hashlib.sha256(zf.read(tif_path.name)).hexdigest() == card["artifact"]["tif_sha256"]
