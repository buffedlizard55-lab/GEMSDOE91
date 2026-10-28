"""Synthetic tests for the S25-FABRIC feature module (no competition data)."""
import numpy as np
import pytest

from gems91 import fabric25 as F


def test_line_footprints():
    for ang in (0, 45, 90, 135):
        fp = F._line_footprint(11, ang)
        assert fp.shape == (11, 11)
        assert int(fp.sum()) == 11
    assert F._line_footprint(5, 0)[2, :].all()
    assert F._line_footprint(5, 90)[:, 2].all()
    d45 = F._line_footprint(5, 45)
    assert all(d45[k, k] for k in range(5)) and not d45[0, 4]
    d135 = F._line_footprint(5, 135)
    assert all(d135[k, 4 - k] for k in range(5)) and not d135[0, 0]
    with pytest.raises(ValueError):
        F._line_footprint(4, 0)


def test_phase_correlation_recovers_shift():
    rng = np.random.default_rng(7)
    a = rng.normal(size=(64, 64))
    # b is a shifted by (dy, dx) = (3, -2): b[y, x] = a[y-3, x+2]
    b = np.roll(np.roll(a, 3, axis=0), -2, axis=1)
    dy, dx, coh = F._phase_correlation_lag(a, b, 8)
    assert (dy, dx) == (3.0, -2.0)
    assert coh > 1.0
    dy0, dx0, _ = F._phase_correlation_lag(a, a, 8)
    assert (dy0, dx0) == (0.0, 0.0)


def _synthetic_bands(h=192, w=192):
    rng = np.random.default_rng(11)
    yy, xx = np.mgrid[0:h, 0:w]
    bands = {}
    # Elevation: smooth west block, rough east block (fabric step at x = w//2).
    elev = 100.0 + 0.05 * xx + rng.normal(0, 0.3, (h, w))
    elev[:, w // 2:] += rng.normal(0, 4.0, (h, w - w // 2)) + 3.0 * np.sin(yy[:, w // 2:] / 3.0)
    bands[12] = elev.astype(np.float32)
    gy, gx = np.gradient(elev)
    bands[19] = np.hypot(gy, gx).astype(np.float32)
    # Gravity/magnetics: same sinusoid pattern, magnetics shifted by +3 px in x.
    pat = np.sin((xx + 0.3 * yy) / 4.0) + 0.5 * rng.normal(size=(h, w))
    bands[13] = pat.astype(np.float32)
    bands[14] = np.roll(pat, 3, axis=1).astype(np.float32)
    for i in range(1, 20):
        bands.setdefault(i, (rng.normal(size=(h, w)) + i).astype(np.float32))
    # Sentinel block in every band (declared NoData must never be read as a value).
    for a in bands.values():
        a[10:16, 10:16] = np.float32(-3.4028234663852886e38)
    return bands


def test_build_all_synthetic():
    h = w = 192
    bands = _synthetic_bands(h, w)
    fp = np.ones((h, w), dtype=bool)
    saved = {}
    groups, meta = F.build_all(lambda i: bands[i], fp,
                               lambda name, arr: saved.__setitem__(name, arr))
    assert len(groups["base"]) == 19 + 4
    assert len(groups["new"]) == 8 + 6
    assert groups["surfaces"] == ["surface_new_standalone", "surface_gravgrad"]
    for name in groups["base"] + groups["new"]:
        a = saved[name]
        assert a.shape == (h, w) and a.dtype == np.float32
        finite = a[np.isfinite(a)]
        assert finite.size > 0
        assert np.abs(finite).max() < 1e30, f"sentinel leaked into {name}"
        # Sentinel block itself must be NaN in every feature.
        assert np.isnan(a[10:16, 10:16]).all(), name
    for name in groups["surfaces"]:
        s = saved[name]
        assert np.isfinite(s).all() and float(s.min()) >= 0.0 and float(s.max()) <= 1.0
    # OGC fabric contrast should respond near the synthetic fabric step (x ~ w//2)
    # more than deep inside the smooth west block (both away from eroded rims).
    energy = saved["ogc_emax_l11"]
    east = np.nanmedian(energy[60:130, w // 2 + 5:w // 2 + 25])
    west = np.nanmedian(energy[60:130, 30:50])
    assert east > west
    # CSPL: magnetics were rolled +3 in x vs gravity, so |lag_dx| should be ~3
    # somewhere in the supported interior (sign convention recorded in module).
    lag_dx = saved["cspl_lag_dx"]
    vals = lag_dx[np.isfinite(lag_dx)]
    assert np.median(np.abs(vals)) > 1.0
    assert meta["footprint_pixels"] == h * w
