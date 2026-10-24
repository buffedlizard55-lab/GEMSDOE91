"""Unit checks for the H12-1 placement helpers (scripts/run_h12_colocation.py).

These run on synthetic arrays only: no restored competition data are needed.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import run_h12_colocation as H  # noqa: E402


def test_emit_places_exact_count_with_minimum_spacing():
    rng = np.random.default_rng(0)
    score = rng.random((120, 140)).astype(np.float32)
    eligible = np.ones_like(score, dtype=bool)
    eligible[:, :10] = False
    dots, count = H.emit(score, eligible, 300)
    assert count == 300
    assert int(dots.sum()) == 300
    ys, xs = np.nonzero(dots)
    assert not dots[:, :10].any(), "ineligible pixels must never receive a dot"
    d = np.hypot(ys[:, None] - ys[None, :], xs[:, None] - xs[None, :])
    np.fill_diagonal(d, np.inf)
    assert d.min() > H.SPACING_PX, "dots must be strictly more than 3.05 px apart"


def test_emit_takes_highest_scores_first():
    score = np.zeros((30, 30), dtype=np.float32)
    score[5, 5] = 9.0
    score[25, 25] = 8.0
    score[5, 20] = 7.0
    eligible = np.ones_like(score, dtype=bool)
    dots, count = H.emit(score, eligible, 3)
    assert count == 3
    assert dots[5, 5] == 1 and dots[25, 25] == 1 and dots[5, 20] == 1


def test_robust_z_is_clipped_and_zero_outside_valid():
    a = np.array([[1.0, 2.0, 3.0, 100.0, -50.0]], dtype=np.float64)
    valid = np.array([[True, True, True, True, False]])
    z = H.robust_z(a, valid)
    assert z.dtype == np.float32
    assert (z >= 0).all(), "robust z is clipped at zero"
    assert z[0, 4] == 0.0, "invalid pixels are zero"
    # median 2.5, scale 20: values 1 and 2 clip to 0; 3 is slightly positive; 100 is large.
    assert z[0, 3] > z[0, 2] > 0.0 and z[0, 0] == 0.0 and z[0, 1] == 0.0
