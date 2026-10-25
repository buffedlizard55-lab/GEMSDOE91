"""Synthetic checks for the XG91 cross-gradient. Not a holdout score."""
import numpy as np
from gems91 import xg91


def test_parallel_ramps_are_more_concordant_than_crossing_ramps():
    h = w = 48
    yy, xx = np.mgrid[:h, :w]
    fp = np.ones((h, w), dtype=bool)
    parallel_m = xx.astype(np.float32)
    parallel_g = (0.5 * xx + 1.0).astype(np.float32)
    cross_g = yy.astype(np.float32)
    cos_p, _ = xg91.parallelism(parallel_m, parallel_g, 1.5)
    cos_c, _ = xg91.parallelism(parallel_m, cross_g, 1.5)
    assert float(cos_p[fp].mean()) > 0.9
    assert float(cos_c[fp].mean()) < 0.2


def test_shadow_samples_downdip_and_dots_respect_spacing_and_catalogue():
    h = w = 40
    fp = np.ones((h, w), dtype=bool)
    concord = np.zeros((h, w), np.float32)
    concord[:, 20] = 1.0
    depth = np.full((h, w), 400.0, np.float32)
    depth[:, :20] = 50.0  # shallower to the west; gradient points east (downdip)
    shadow, shift = xg91.updip_shadow(concord, depth, fp, min_px=2.0, max_px=4.0)
    assert np.isfinite(shadow).all()
    assert float(shift.min()) >= 2.0 and float(shift.max()) <= 4.0
    # The crest itself should not be the unique maximum after an updip shift.
    assert float(shadow[:, 20].mean()) < 1.0 or float(shadow[:, 17].max()) > 0.0
    cat = np.zeros((h, w), dtype=bool)
    cat[:, 10] = True
    dots = xg91.emit_spaced_dots(shadow, fp & ~cat, spacing_px=3.0, n_dots=12)
    assert dots.dtype == np.float32
    assert float(dots.min()) == 0.0 and float(dots.max()) == 1.0
    assert int(dots[cat].sum()) == 0
    ys, xs = np.nonzero(dots > 0)
    assert 1 <= len(ys) <= 12
    if len(ys) > 1:
        d2 = (ys[:, None] - ys[None, :]) ** 2 + (xs[:, None] - xs[None, :]) ** 2
        np.fill_diagonal(d2, 999)
        assert float(d2.min()) >= 9.0
