"""Unit tests for S27-CVDC feature physics, sentinel handling, and Pure-Subsurface isolation."""
from __future__ import annotations

import numpy as np

from gems91.cvdc_osdr27 import (
    ALL_STATIC_NAMES,
    PURE_SUBSURFACE_INDICES,
    PURE_SUBSURFACE_NAMES,
    compute_cvdc27_features,
    compute_cvdc_crest_fp,
    compute_osdr_sub_backbone_fp,
)


def _synthetic_stack(h: int = 80, w: int = 80, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    bands = rng.normal(loc=10.0, scale=1.0, size=(19, h, w)).astype(np.float32)
    # Keep positive-domain bands positive (e.g., B04, B06, B07, B15, B16, B17, B19)
    for b in (3, 5, 6, 9, 14, 15, 16, 18):
        bands[b] = np.abs(bands[b]) + 2.0
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False
    fp[-3:, :] = False
    fp[:, :3] = False
    fp[:, -3:] = False
    return bands, fp


def test_nodata_sentinel_exclusion_and_bounds():
    bands, fp = _synthetic_stack()
    # Inject float32 NoData sentinels (-3.4e38), NaN, and +Inf inside the footprint
    bands[:, 10:15, 10:15] = np.float32(-3.4028235e38)
    bands[12, 22, 22] = np.nan
    bands[1, 25, 25] = np.inf

    X, surfaces, receipt = compute_cvdc27_features(bands, fp)
    assert X.shape == (int(fp.sum()), len(ALL_STATIC_NAMES))
    assert np.isfinite(X).all(), "All static features must be strictly finite despite sentinels"
    for name, surf in surfaces.items():
        assert surf.shape == fp.shape
        assert np.isfinite(surf).all(), f"{name} contains non-finite values"
        assert float(surf.min()) >= 0.0 and float(surf.max()) <= 1.0, f"{name} outside [0, 1]"
        assert float(surf[~fp].max()) == 0.0, f"{name} non-zero outside footprint"
    assert receipt["catalogue_features_used"] is False
    assert "NOT magnetic tilt" in receipt["band_06_semantics"]


def test_pure_subsurface_has_bitwise_zero_b12_b19_dependence():
    bands_a, fp = _synthetic_stack(seed=7)
    bands_b = bands_a.copy()
    rng = np.random.default_rng(999)
    # Completely replace Band 12 (idx 11) and Band 19 (idx 18)
    bands_b[11] = rng.uniform(-900.0, 1800.0, size=fp.shape).astype(np.float32)
    bands_b[18] = rng.uniform(0.0, 80.0, size=fp.shape).astype(np.float32)

    X_a, _, _ = compute_cvdc27_features(bands_a, fp)
    X_b, _, _ = compute_cvdc27_features(bands_b, fp)

    assert len(PURE_SUBSURFACE_INDICES) == 26
    assert np.array_equal(
        X_a[:, PURE_SUBSURFACE_INDICES],
        X_b[:, PURE_SUBSURFACE_INDICES],
    ), "Pure-Subsurface features leaked B12 or B19 information!"
    assert np.array_equal(
        compute_osdr_sub_backbone_fp(X_a),
        compute_osdr_sub_backbone_fp(X_b),
    ), "Pure-Subsurface OSDR backbone leaked B12 or B19!"
    crest = compute_cvdc_crest_fp(X_a)
    assert crest.min() >= 0.0 and crest.max() <= 1.0
    # Topographic/CVDC block MUST respond to B12/B19 changes
    assert not np.allclose(X_a[:, 26:], X_b[:, 26:])


def test_cvdc_detects_contour_crossing_discordance_over_parallel_ramp():
    h = w = 96
    yy, xx = np.indices((h, w), dtype=np.float32)
    fp = np.ones((h, w), dtype=bool)

    # Case 1: Orthogonal crossing (elev contours horizontal, gravity step vertical at x=48)
    b_ortho, _ = _synthetic_stack(h, w, seed=11)
    b_ortho[11] = 10.0 * yy  # B12 det_elev gradient points +y
    b_ortho[12] = 20.0 * np.tanh((xx - 48.0) / 3.0)  # B13 gravity gradient points +x

    # Case 2: Parallel range-front (both elev and gravity vary along +x)
    b_para = b_ortho.copy()
    b_para[11] = 10.0 * xx

    X_ortho, _, _ = compute_cvdc27_features(b_ortho, fp)
    X_para, _, _ = compute_cvdc27_features(b_para, fp)

    c_idx = ALL_STATIC_NAMES.index("cvdc_sin2_elev_grav_s3p5")
    p_idx = ALL_STATIC_NAMES.index("cvdc_multiscale_persist")
    g_ortho = X_ortho[:, c_idx].reshape(h, w)[30:66, 45:51].mean()
    g_para = X_para[:, c_idx].reshape(h, w)[30:66, 45:51].mean()
    assert g_ortho > 0.45
    assert g_para < 0.05
    assert X_ortho[:, p_idx].reshape(h, w)[30:66, 45:51].mean() > 5.0 * X_para[:, p_idx].reshape(h, w)[30:66, 45:51].mean()


def test_osdr_prefers_localized_sign_locked_step_over_uniform_ramp():
    h = w = 96
    _, xx = np.indices((h, w), dtype=np.float32)
    fp = np.ones((h, w), dtype=bool)

    b_step, _ = _synthetic_stack(h, w, seed=21)
    step_prof = 15.0 * np.tanh((xx - 48.0) / 2.0)
    b_step[12] = step_prof  # B13 gravity sharp fault step
    b_step[1] = 200.0 * np.tanh((xx - 48.0) / 2.0)  # B02 RTP sign-locked step

    b_ramp = b_step.copy()
    b_ramp[12] = 0.35 * (xx - 48.0)  # Uniform non-fault regional gradient
    b_ramp[1] = -5.0 * xx + 3.0 * np.sin(xx)  # Inconsistent / non-stepped RTP

    X_step, _, _ = compute_cvdc27_features(b_step, fp)
    X_ramp, _, _ = compute_cvdc27_features(b_ramp, fp)

    step_col = PURE_SUBSURFACE_NAMES.index("osdr_grav_step_w5")
    lock_col = PURE_SUBSURFACE_NAMES.index("osdr_grav_rtp_sign_lock")
    s_center = X_step[:, step_col].reshape(h, w)[30:66, 47:50].mean()
    r_center = X_ramp[:, step_col].reshape(h, w)[30:66, 47:50].mean()
    assert s_center > 3.0 * r_center
    assert X_step[:, lock_col].reshape(h, w)[30:66, 47:50].mean() > X_ramp[:, lock_col].reshape(h, w)[30:66, 47:50].mean()


def test_mvsd_valley_bridge_peaks_across_alluvial_gap():
    h = w = 96
    fp = np.ones((h, w), dtype=bool)
    bands, _ = _synthetic_stack(h, w, seed=33)
    bands[18] = 1.0  # Flat valley floor B19 slope
    # Two colinear N-S scarp segments along col 48 separated by a 10-px valley wash (rows 43..53)
    bands[18, 20:43, 47:50] = 25.0
    bands[18, 53:76, 47:50] = 25.0

    X, _, _ = compute_cvdc27_features(bands, fp)
    b_col = ALL_STATIC_NAMES.index("mvsd_valley_bridge_product")
    bridge_grid = X[:, b_col].reshape(h, w)
    gap_response = float(bridge_grid[47:50, 46:51].max())
    off_strike_bg = float(bridge_grid[47:50, 15:25].max())
    assert gap_response > 5.0 * max(off_strike_bg, 1e-3)
