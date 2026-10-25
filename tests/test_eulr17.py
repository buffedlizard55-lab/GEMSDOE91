"""S17-EULR solver tests (preregistration docs/HYPOTHESES_S17.md S2.3).

The fast slab/box-filter solver must match the brute-force per-window
reference, and both must recover known source geometry on exact
Euler-homogeneous synthetic fields, before any real-data build is trusted.
These are solver-algebra tests, not geological claims.
"""
import numpy as np
import pytest
from scipy import ndimage as ndi

from gems91.eulr17 import (
    EULR_FEATURE_NAMES,
    _fft_vertical_derivative_perpx,
    accept_euler_solutions,
    euler_solve_fast,
    euler_window_solve_bruteforce,
    rasterize_solutions,
)


def _homogeneous_fields(structural_index: int, x0: float, y0: float, d: float,
                        shape=(61, 71)):
    """Exact Euler-homogeneous test fields on the observation plane zeta=0.

    N=1: F = 1/r (degree -1); N=0: F = (x-x0)/r (degree 0), where
    r^2 = (x-x0)^2 + (y-y0)^2 + d^2 and Fz = dF/dzeta at zeta=0 (zeta down).
    """
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float64)
    u, v = xx - x0, yy - y0
    r = np.sqrt(u * u + v * v + d * d)
    if structural_index == 1:
        F = 1.0 / r
        Fx, Fy, Fz = -u / r**3, -v / r**3, d / r**3
    else:
        F = u / r
        Fx = 1.0 / r - u * u / r**3
        Fy = -u * v / r**3
        Fz = u * d / r**3
    return F, Fx, Fy, Fz


@pytest.mark.parametrize("n_idx", [0, 1])
def test_bruteforce_recovers_homogeneous_source(n_idx):
    x0, y0, d = 33.4, 28.6, 7.5
    F, Fx, Fy, Fz = _homogeneous_fields(n_idx, x0, y0, d)
    sol = euler_window_solve_bruteforce(F, Fx, Fy, Fz, structural_index=float(n_idx), window_px=11)
    yc, xc = 30, 35  # arbitrary centre near the source
    assert sol["dx0"][yc, xc] == pytest.approx(x0 - xc, abs=1e-4)
    assert sol["dy0"][yc, xc] == pytest.approx(y0 - yc, abs=1e-4)
    assert sol["depth"][yc, xc] == pytest.approx(d, abs=1e-4)
    assert sol["rel_unc"][yc, xc] < 1e-6  # exact field -> ~zero residuals


@pytest.mark.parametrize("n_idx", [0.0, 1.0])
def test_fast_matches_bruteforce(n_idx):
    rng = np.random.default_rng(17)
    base = ndi.gaussian_filter(rng.standard_normal((64, 72)), sigma=3.0).astype(np.float32)
    F = (base * 50.0 + 500.0).astype(np.float32)
    Fx = ndi.gaussian_filter1d(F, 1.2, axis=1, order=1, mode="nearest").astype(np.float32)
    Fy = ndi.gaussian_filter1d(F, 1.2, axis=0, order=1, mode="nearest").astype(np.float32)
    Fz = ndi.gaussian_filter(rng.standard_normal((64, 72)), sigma=2.0).astype(np.float32)
    brute = euler_window_solve_bruteforce(F, Fx, Fy, Fz, structural_index=n_idx, window_px=9)
    fast = euler_solve_fast(F, Fx, Fy, Fz, structural_index=n_idx, window_px=9, slab_rows=17)
    ok = np.isfinite(brute["depth"]) & np.isfinite(fast["depth"])
    assert ok.sum() > 1000
    for key in ("dx0", "dy0", "depth"):
        assert np.allclose(fast[key][ok], brute[key][ok], rtol=1e-3, atol=1e-4), key
    both = (ok & np.isfinite(brute["rel_unc"]) & (brute["depth"] > 1.0)
            & (brute["rel_unc"] > 0) & (brute["rel_unc"] < 5))
    assert np.allclose(fast["rel_unc"][both], brute["rel_unc"][both], rtol=2e-2, atol=1e-4)


def test_fft_vertical_derivative_eigenvalue():
    h, w = 96, 120
    yy, xx = np.mgrid[0:h, 0:w]
    F = np.cos(2 * np.pi * 3 * xx / w) * np.cos(2 * np.pi * 2 * yy / h)
    k = 2 * np.pi * np.hypot(3 / w, 2 / h)
    dz = _fft_vertical_derivative_perpx(F.astype(np.float32), pad=0)
    assert np.allclose(dz, k * F, rtol=2e-3, atol=1e-4)


def test_acceptance_gates():
    sol = {
        "dx0": np.array([[1.0, 20.0, 1.0]], dtype=np.float32),   # 2nd: offset too large
        "dy0": np.array([[0.0, 0.0, 0.0]], dtype=np.float32),
        "depth": np.array([[5.0, 5.0, 0.1]], dtype=np.float32),  # 3rd: too shallow
        "rel_unc": np.array([[0.1, 0.1, 0.1]], dtype=np.float32),
    }
    sr, sc, dep, rel = accept_euler_solutions(sol)
    assert sr.tolist() == [0] and sc.tolist() == [1]  # centre (0,0) + dx0=1
    assert dep.tolist() == [5.0]


def test_rasterize_shapes_and_defined():
    sr = np.array([10, 10, 10, 10, 10, 10, 20])
    sc = np.array([10, 10, 10, 11, 11, 11, 20])
    dens, dep, unc, defined = rasterize_solutions(
        (40, 40), sr, sc,
        np.array([5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 9.0]),
        np.array([0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.2]))
    assert dens.shape == (40, 40) and np.isfinite(dens).all()
    assert dens[10, 10] > dens[0, 0]
    assert defined[10, 10] and not defined[0, 0]


def test_feature_names_locked():
    assert len(EULR_FEATURE_NAMES) == 14
    assert EULR_FEATURE_NAMES[0] == "s17_eulr_mag0_dens"
    assert EULR_FEATURE_NAMES[-1] == "s17_eulr_mag0_b15_agree"
    assert all(n.startswith("s17_eulr_") for n in EULR_FEATURE_NAMES)
