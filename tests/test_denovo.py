"""Tests for the DENOVO lane operators (no competition data needed)."""
import numpy as np
import pytest

from gems91 import denovo as DN


def test_greedy_spaced_count_and_spacing():
    rng = np.random.default_rng(0)
    surf = rng.random((60, 60), dtype=np.float32)
    elig = np.ones((60, 60), dtype=bool)
    dots = DN.greedy_spaced(surf, elig, 100, spacing_px=2.8)
    assert int(dots.sum()) == 100
    rc = np.column_stack(np.nonzero(dots)).astype(float)
    for i in range(len(rc)):
        d = np.hypot(*(rc - rc[i]).T)
        d[i] = np.inf
        assert d.min() >= 2.8 - 1e-9


def test_greedy_spaced_deterministic_and_order():
    surf = np.zeros((20, 20), dtype=np.float32)
    surf[5, 5] = 1.0
    surf[5, 6] = 0.9  # within spacing of the top cell: must be skipped
    surf[15, 15] = 0.8
    elig = np.ones((20, 20), dtype=bool)
    a = DN.greedy_spaced(surf, elig, 2, spacing_px=2.8)
    b = DN.greedy_spaced(surf, elig, 2, spacing_px=2.8)
    assert np.array_equal(a, b)
    assert a[5, 5] and a[15, 15] and not a[5, 6]


def test_greedy_spaced_respects_eligibility():
    surf = np.ones((10, 10), dtype=np.float32)
    elig = np.zeros((10, 10), dtype=bool)
    elig[::4, ::4] = True
    dots = DN.greedy_spaced(surf, elig, 5, spacing_px=2.8)
    assert int(dots.sum()) == 5
    assert not (dots & ~elig).any()


def test_pct32_range_and_outside_zero():
    arr = np.array([[1.0, 2.0], [3.0, np.nan]], dtype=np.float32)
    fp = np.array([[True, True], [True, False]])
    p = DN.pct32(arr, fp)
    assert p[1, 1] == 0.0
    assert 0.0 <= p[fp].min() and p[fp].max() <= 1.0
    assert p[0, 0] < p[0, 1] < p[1, 0] or p[0, 0] <= p[0, 1] <= p[1, 0]


def test_disk_offsets_radius():
    off = DN.disk_offsets(2.8)
    assert (0, 0) in off
    assert all(np.hypot(dr, dc) < 2.8 for dr, dc in off)
    # (2,2)=2.828 is outside a strict 2.8 disk; (2,1)=2.236 inside
    assert (2, 2) not in off and (2, 1) in off
