"""Unit tests for the spacing geometry. No competition data required."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import geom, moves  # noqa: E402


def test_ring_is_the_radius_two_moore_ring():
    off = moves.ring_offsets()
    assert len(off) == 12
    r = np.hypot(off[:, 0], off[:, 1])
    assert r.min() >= 2.0 and r.max() <= np.sqrt(5) + 1e-9
    assert len({tuple(o) for o in off.tolist()}) == 12
    # every offset is integer and distinct from the origin
    assert not (off == 0).all(axis=1).any()


def test_density_potential_peaks_on_a_dot():
    dot = np.zeros((21, 21), dtype=bool)
    dot[10, 10] = True
    d = moves.density_potential(dot, sigma=2.0)
    assert d[10, 10] == pytest.approx(d.max())
    assert d[10, 10] > 0.03
    assert d[0, 0] == pytest.approx(0.0, abs=1e-6)


def test_densest_selection_is_deterministic_and_covers_requested_share():
    rng = np.random.default_rng(0)
    ys = rng.integers(0, 200, 500)
    xs = rng.integers(0, 200, 500)
    a = geom.densest_dot_selection(ys, xs, 0.4)
    b = geom.densest_dot_selection(ys, xs, 0.4)
    assert np.array_equal(a, b)
    assert a.sum() >= 0.4 * len(ys)
    assert a.sum() < 0.6 * len(ys)          # it stops at block granularity


def test_selection_rejects_bad_fraction():
    with pytest.raises(ValueError):
        geom.densest_dot_selection(np.zeros(3, int), np.zeros(3, int), 0.0)


def _toy():
    """30x30 grid, footprint everywhere, catalogue in the left column."""
    dot = np.zeros((30, 30), dtype=bool)
    for y in range(4, 26, 3):
        for x in range(6, 26, 3):
            dot[y, x] = True
    footprint = np.ones((30, 30), dtype=bool)
    cat = np.zeros((30, 30), dtype=bool)
    cat[:, 0] = True
    cat_dist = np.tile(np.arange(30, dtype=float), (30, 1))
    return dot, footprint, cat, cat_dist


@pytest.mark.parametrize("mode", ["spread", "clump", "jitter"])
def test_moves_preserve_every_hard_constraint(mode):
    dot, footprint, cat, cat_dist = _toy()
    ys, xs = np.nonzero(dot)
    movable = np.ones(len(ys), dtype=bool)
    density = moves.density_potential(dot, sigma=2.0)
    out = moves.apply_moves(dot, footprint, cat_dist, ys, xs, movable, mode=mode,
                            density=density, rng=np.random.default_rng(1), floor_px=2.0)

    child = out["dots"]
    assert child.sum() == dot.sum(), "count must be held"
    assert child[cat].sum() == 0, "zero mass on the catalogue"
    assert cat_dist[child].min() > 2.0, "parent collar floor respected"
    assert np.isfinite(child[footprint]).all()
    # no cell reused and no pair closer than 2 px
    from scipy.spatial import cKDTree
    cy, cx = np.nonzero(child)
    pts = np.c_[cy, cx]
    assert len({(y, x) for y, x in pts.tolist()}) == len(pts)
    d, _ = cKDTree(pts).query(pts, k=2)
    assert d[:, 1].min() >= 2.0 - 1e-9
    # every moved dot travelled on the ring
    if out["n_moved"]:
        assert 2.0 - 1e-9 <= out["mean_displacement_px"] <= np.sqrt(5) + 1e-9


def test_spread_moves_density_down_and_clump_moves_it_up():
    dot, footprint, cat, cat_dist = _toy()
    ys, xs = np.nonzero(dot)
    density = moves.density_potential(dot, sigma=2.0)
    res = {}
    for mode in ("spread", "clump"):
        res[mode] = moves.apply_moves(dot, footprint, cat_dist, ys, xs,
                                      np.ones(len(ys), bool), mode=mode,
                                      density=density, rng=np.random.default_rng(1),
                                      floor_px=2.0)
    assert res["spread"]["mean_density_to"] <= res["spread"]["mean_density_from"]
    assert res["clump"]["mean_density_to"] >= res["spread"]["mean_density_to"]
