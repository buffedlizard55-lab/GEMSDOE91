import numpy as np

from gems91 import ccr


def test_depth_conditional_residual_removes_broad_trend_but_keeps_contact():
    h, w = 96, 112
    yy, xx = np.indices((h, w), dtype=np.float32)
    footprint = np.ones((h, w), dtype=bool)
    depth = 100.0 + 9.0 * yy + 1.5 * xx
    broad = 2.5 + 0.003 * depth
    contact = np.where(xx >= 58, 1.25, 0.0).astype(np.float32)
    cond = broad + contact

    residual, meta = ccr._depth_conditional_residual(cond, depth, footprint, n_bins=24)
    assert np.isfinite(residual).all()
    assert meta["effective_bins"] >= 20
    # The broad depth relation is strongly suppressed while the vertical contact remains.
    raw_corr = abs(np.corrcoef(cond.ravel(), depth.ravel())[0, 1])
    residual_corr = abs(np.corrcoef(residual.ravel(), depth.ravel())[0, 1])
    assert residual_corr < raw_corr
    left = float(np.median(residual[:, 30:45]))
    right = float(np.median(residual[:, 70:85]))
    assert right - left > 0.5


def test_ccr_edge_field_is_finite_bounded_and_shape_safe():
    footprint = np.ones((12, 14), dtype=bool)
    n = int(footprint.sum())
    x = np.zeros((n, len(ccr.CCR_FEATURE_NAMES)), dtype=np.float32)
    ramp = np.linspace(0, 1, n, dtype=np.float32)
    x[:, 1] = ramp
    x[:, 2] = ramp[::-1]
    x[:, 4] = np.sqrt(ramp)
    x[:, 5] = ramp**2
    out = ccr.ccr_edge_field(x, footprint)
    assert out.shape == footprint.shape
    assert np.isfinite(out).all()
    assert float(out.min()) >= 0.0
    assert float(out.max()) <= 1.0
