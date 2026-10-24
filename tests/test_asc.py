"""Unit tests for the ASC91 antisymmetric step filter on synthetic fields."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems91 import asc  # noqa: E402


def _vertical_step(h=60, w=60, boundary=30, low=0.0, high=10.0):
    f = np.full((h, w), low, dtype=np.float32)
    f[:, boundary:] = high
    return f


def test_step_detected_at_matching_azimuth_and_sign():
    f = _vertical_step()  # N-S boundary at col 30, high side to the east
    s0 = asc.step_response(f, 0.0)
    # strike 0 (N-S): +n is east, field higher east -> positive at boundary
    assert s0[30, 29] > 5.0
    assert s0[30, 30] > 5.0
    # far from the boundary the response vanishes
    assert abs(s0[30, 5]) < 1e-5
    assert abs(s0[30, 55]) < 1e-5


def test_step_vanishes_at_perpendicular_azimuth():
    f = _vertical_step()
    s90 = asc.step_response(f, 90.0)  # across-strike is N-S; field constant N-S
    assert np.max(np.abs(s90[10:-10, 10:-10])) < 1e-4


def test_constant_and_symmetric_ridge_give_no_step():
    const = np.full((40, 40), 3.0, dtype=np.float32)
    assert np.max(np.abs(asc.step_response(const, 0.0))) < 1e-5
    ridge = np.zeros((60, 60), dtype=np.float32)
    ridge[:, 29:32] = 10.0  # symmetric N-S ridge: a crest, not a step
    s = asc.step_response(ridge, 0.0)
    assert abs(s[30, 30]) < 1.0  # << the >5 response of a true 10-unit step


def test_reversed_step_flips_sign():
    f = _vertical_step(low=10.0, high=0.0)
    s0 = asc.step_response(f, 0.0)
    assert s0[30, 30] < -5.0


def test_azimuth_180_equivalence_class():
    # Azimuths are axial: bins cover 0..157.5 only, bin distance wraps.
    d = asc.axial_bin_distance(np.array([0]), np.array([7]))
    assert int(d[0]) == 1
    d = asc.axial_bin_distance(np.array([0]), np.array([4]))
    assert int(d[0]) == 4


def test_percentile_grid_ranks_and_ties():
    fp = np.ones((2, 4), dtype=bool)
    vals = np.array([[0.0, 1.0, 1.0, 3.0], [2.0, 2.0, 2.0, 4.0]], dtype=np.float32)
    p = asc.percentile_grid(vals, fp)
    assert p.min() >= 0.0 and p.max() <= 1.0
    assert p[0, 0] == 0.0 and p[1, 3] == 1.0
    assert p[0, 1] == p[0, 2]  # tied values share a rank
    assert p[1, 0] == p[1, 1] == p[1, 2]
    fp2 = fp.copy(); fp2[0, 0] = False
    p2 = asc.percentile_grid(vals, fp2)
    assert p2[0, 0] == 0.0  # outside footprint is exactly 0
