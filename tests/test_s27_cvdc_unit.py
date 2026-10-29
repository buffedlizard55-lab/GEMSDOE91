"""Unit tests for Session 27 (`S27-CVDC`) physics features, sentinel immunity,
pure-subsurface B12/B19 invariance, Stage-2 axial bridge, and CELF uniqueness caps.
"""
from __future__ import annotations

import numpy as np
import pytest
from scipy.spatial import cKDTree

from gems91 import cvdc27


def _synthetic_bands(seed: int = 42, shape: tuple[int, int] = (96, 100)) -> tuple[dict[int, np.ndarray], np.ndarray]:
    rng = np.random.default_rng(seed)
    h, w = shape
    fp = np.ones((h, w), dtype=bool)
    fp[:4, :] = False
    fp[-4:, :] = False
    fp[:, :4] = False
    fp[:, -4:] = False

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    bands: dict[int, np.ndarray] = {}
    for b in range(1, 20):
        arr = (0.2 * np.sin(xx / 9.0 + b) + 0.3 * np.cos(yy / 11.0 - 0.5 * b) + 0.05 * rng.standard_normal((h, w))).astype(np.float32)
        if b in (3, 4, 5, 7, 15, 17, 19):
            arr = np.abs(arr) + np.float32(1.0)
        # Inject an interior sentinel pocket + exterior NaNs
        arr[42:46, 48:53] = np.float32(-3.4e38)
        arr[~fp] = np.nan
        bands[b] = arr
    return bands, fp


def test_sentinel_values_never_bleed_into_any_static_feature():
    bands_a, fp = _synthetic_bands(seed=10)
    bands_b = {k: v.copy() for k, v in bands_a.items()}
    # Replace all invalid/sentinel cells with wildly different sentinels (+9.9e37 and NaN)
    for b, arr in bands_b.items():
        bad = (~fp) | (~np.isfinite(arr)) | (np.abs(arr) >= 1.0e30)
        arr[bad] = np.float32(9.9e37)
        arr[43, 50] = np.nan

    saved_a: dict[str, np.ndarray] = {}
    saved_b: dict[str, np.ndarray] = {}
    groups_a, meta_a = cvdc27.build_all_static_features(lambda i: bands_a[i], fp, lambda k, v: saved_a.__setitem__(k, v))
    cvdc27.build_all_static_features(lambda i: bands_b[i], fp, lambda k, v: saved_b.__setitem__(k, v))

    assert meta_a["catalogue_used_in_features"] is False
    assert meta_a["b06_used_in_features"] is False
    assert len(groups_a["all_static"]) == 34

    for name in groups_a["all_static"] + groups_a["surfaces"]:
        a, b = saved_a[name], saved_b[name]
        assert np.array_equal(a, b, equal_nan=True), f"sentinel bleed in {name}"
        # Interior sentinel pocket [42:46, 48:53] must be NaN in every static feature
        if name in groups_a["all_static"]:
            assert np.isnan(a[43, 50]), f"sentinel cell not masked in {name}"


def test_pure_subsurface_features_have_bitwise_zero_b12_b19_dependence():
    bands_a, fp = _synthetic_bands(seed=21)
    bands_b = {k: v.copy() for k, v in bands_a.items()}
    rng = np.random.default_rng(999)
    # Perturb B12, B19, and B06 massively (including adding new invalid cells in B12/B19!)
    with np.errstate(over="ignore", invalid="ignore"):
        bands_b[12] = (bands_b[12] * -7.5 + 500.0 + rng.standard_normal(fp.shape)).astype(np.float32)
        bands_b[12][20:25, 20:25] = np.float32(-3.4e38)
        bands_b[19] = (np.abs(bands_b[19]) * 13.0 + 42.0).astype(np.float32)
        bands_b[19][60:65, 60:65] = np.float32(-3.4e38)
        bands_b[6] = np.full(fp.shape, np.float32(-3.4e38), dtype=np.float32)

    saved_a: dict[str, np.ndarray] = {}
    saved_b: dict[str, np.ndarray] = {}
    cvdc27.build_all_static_features(lambda i: bands_a[i], fp, lambda k, v: saved_a.__setitem__(k, v))
    cvdc27.build_all_static_features(lambda i: bands_b[i], fp, lambda k, v: saved_b.__setitem__(k, v))

    assert len(cvdc27.PURE_SUBSURFACE_STATIC_FEATURES) == 17
    for name in cvdc27.PURE_SUBSURFACE_STATIC_FEATURES:
        assert np.array_equal(saved_a[name], saved_b[name], equal_nan=True), f"B12/B19/B06 leak in {name}"


def test_rule_of_v_discordance_distinguishes_cross_cutting_from_parallel_strikes():
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # Elevation slopes strictly N-S (contours run E-W)
    elev = yy * 2.0
    # Gravity case 1: parallel to elevation (also slopes N-S -> sin^2 = 0)
    grav_par = yy * 3.0
    # Gravity case 2: orthogonal to elevation (slopes E-W -> cuts across contours -> sin^2 = 1)
    grav_perp = xx * 3.0

    _, c2e, s2e = cvdc27._grad_mag_and_double_angle(elev, fp, 2.0)
    _, c2_par, s2_par = cvdc27._grad_mag_and_double_angle(grav_par, fp, 2.0)
    _, c2_perp, s2_perp = cvdc27._grad_mag_and_double_angle(grav_perp, fp, 2.0)

    sin2_par, _ = cvdc27._sin2_cos2_diff(c2_par, s2_par, c2e, s2e)
    sin2_perp, _ = cvdc27._sin2_cos2_diff(c2_perp, s2_perp, c2e, s2e)

    assert float(sin2_par[20:60, 20:60].max()) < 1.0e-4
    assert float(sin2_perp[20:60, 20:60].min()) > 0.999


def test_stage2_axial_bridge_lights_up_relay_gap():
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    p = np.zeros((h, w), dtype=np.float32)
    # Two aligned E-W fault segments with a 6-px buried relay gap at cols 29..34
    p[32, 16:29] = 0.9
    p[32, 35:48] = 0.9
    feats = cvdc27.stage2_axial_features(p, fp, "s2_full")
    assert set(feats) == set(cvdc27.STAGE2_FULL_FEATURES)
    relay = feats["s2_full_relay_900m"]
    # Relay gap center (32, 32) must strongly exceed off-axis background (10, 32)
    assert float(relay[32, 32]) > 0.5
    assert float(relay[10, 32]) < 1.0e-5


def test_celf_submodular_enforces_collar_spacing_and_uniqueness_cap():
    rng = np.random.default_rng(7)
    h, w = 90, 90
    fp = np.ones((h, w), dtype=bool)
    vis = np.zeros((h, w), dtype=bool)
    vis[45, 20:70] = True
    surf = rng.uniform(0.05, 0.95, size=(h, w)).astype(np.float32)

    # Create a reference raster that covers the highest-scoring pixels
    ref1 = cvdc27.emit_dots_celf_submodular(surf, vis, fp, budget=80, collar_px=3.05, min_spacing_px=3.05)
    assert int((ref1 > 0).sum()) == 80

    words = cvdc27.build_reference_halo_words([ref1 > 0], fp, radius_px=3.0)
    cand = cvdc27.emit_dots_celf_submodular(
        surf,
        vis,
        fp,
        budget=80,
        collar_px=3.05,
        min_spacing_px=3.05,
        farfield_ramp=True,
        ref_halo_words=words,
        n_refs=1,
        uniqueness_cap=0.60,
    )
    assert int((cand > 0).sum()) == 80
    assert int((cand[vis] > 0).sum()) == 0

    p_pts = np.argwhere(cand > 0)
    q_pts = np.argwhere(ref1 > 0)
    v_pts = np.argwhere(vis)
    # Collar > 3.05 px
    assert float(cKDTree(v_pts).query(p_pts, k=1)[0].min()) > 3.05 - 1e-6
    # Mutual spacing >= 3.05 px
    d2 = cKDTree(p_pts).query(p_pts, k=2)[0][:, 1]
    assert float(d2.min()) >= 3.05 - 1e-6
    # 3-px overlap vs ref1 strictly <= 0.60
    ov = float((cKDTree(q_pts).query(p_pts, k=1)[0] <= 3.0).mean())
    assert ov <= 0.60 + 1e-9
