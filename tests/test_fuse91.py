"""FUSE91 primitives: depth-conditioning, scatter cover, tiered emission."""
import numpy as np
from scipy.spatial import cKDTree

from gems91 import fuse91 as F


def _step_fields(n=60):
    """A synthetic buried step: depth and conductivity step at col n/2,
    conductivity also trends with depth (the confound to remove).
    Smooth 2-D variation + noise so percentiles are not degenerate."""
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:n, 0:n]
    depth = (100.0 + 700.0 * (xx >= n // 2) + 30.0 * np.sin(yy / 7.0)
             + 20.0 * np.cos(xx / 11.0) + rng.normal(0, 3, (n, n))).astype(np.float32)
    cond = (0.02 * depth + 5.0 * (xx >= n // 2)
            + rng.normal(0, 0.4, (n, n))).astype(np.float32)
    grav = (5.0 - 25.0 * (xx >= n // 2) + 2.0 * np.sin((xx + yy) / 9.0)
            + rng.normal(0, 0.3, (n, n))).astype(np.float32)
    fp = np.ones((n, n), dtype=bool)
    return cond, depth, grav, fp


def test_depth_conditioned_features_shape_and_finiteness():
    cond, depth, grav, fp = _step_fields()
    X, audit = F.depth_conditioned_features(cond, depth, grav, fp)
    assert X.shape == (60 * 60, 6)
    assert np.isfinite(X).all()
    assert (X >= 0).all() and (X <= 1).all()  # all percentile features
    assert audit["feature_names"] == F.NEW_FEATURE_NAMES
    assert len(audit["cond_pct_median_by_depth_bin"]) == 10


def test_residual_gradient_peaks_at_the_step():
    cond, depth, grav, fp = _step_fields()
    X, _ = F.depth_conditioned_features(cond, depth, grav, fp)
    grad = X[:, 1].reshape(60, 60)
    # the contact column band out-ranks the far field on average
    assert grad[:, 27:34].mean() > grad[:, 2:12].mean()
    assert grad[:, 27:34].mean() > grad[:, 48:58].mean()


def test_scatter_smooth_constant_is_identity_inside():
    fp = np.ones((40, 40), dtype=bool)
    fp[:5, :] = False
    s = np.where(fp, 0.7, 0.0).astype(np.float32)
    out = F.scatter_smooth(s, fp, sigma=1.85)
    assert np.allclose(out[fp], 0.7, atol=1e-5)
    assert (out[~fp] == 0).all()


def test_tiered_greedy_respects_cap_spacing_and_count():
    rng = np.random.default_rng(7)
    surf = rng.random((80, 80), dtype=np.float32)
    tier = np.zeros((80, 80), dtype=bool)
    tier[:, :20] = True
    main = np.ones((80, 80), dtype=bool)
    dots = F.tiered_greedy_spaced(surf, tier, main, 200, tier_cap=12, spacing_px=2.8)
    assert int(dots.sum()) == 200
    assert int((dots & tier).sum()) <= 12
    yy, xx = np.nonzero(dots)
    d = cKDTree(np.c_[yy, xx]).query(np.c_[yy, xx], k=2)[0][:, 1]
    assert float(d.min()) >= 2.8 - 1e-9 or float(d.min()) > 2.79


def test_tiered_greedy_is_deterministic():
    rng = np.random.default_rng(3)
    surf = rng.random((50, 50), dtype=np.float32)
    tier = np.zeros((50, 50), dtype=bool)
    tier[:10, :] = True
    main = np.ones((50, 50), dtype=bool)
    a = F.tiered_greedy_spaced(surf, tier, main, 60, tier_cap=5)
    b = F.tiered_greedy_spaced(surf, tier, main, 60, tier_cap=5)
    assert np.array_equal(a, b)


def test_symmetric_overlap_f1_bounds():
    a = np.zeros((30, 30), dtype=bool)
    b = np.zeros((30, 30), dtype=bool)
    a[10, 10] = True
    b[10, 11] = True  # within 3 px of each other
    r = F.symmetric_overlap_f1(a, b)
    assert r["directed_ours_within"] == 1.0 and r["f1"] == 1.0
    b2 = np.zeros((30, 30), dtype=bool)
    b2[25, 25] = True
    r2 = F.symmetric_overlap_f1(a, b2)
    assert r2["directed_ours_within"] == 0.0 and r2["f1"] == 0.0
