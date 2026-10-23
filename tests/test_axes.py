"""Tests for the axis operators, on synthetic rasters.

The real parent is absent, so these tests assert the INVARIANTS each axis promises
(count preservation where the brief demands it, zero catalogue mass, recorded
% changed), not the live score effect. A synthetic 'parent' is a scattered dot
field inside a footprint with a catalogue line to prune against.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import axes as A  # noqa: E402

SHAPE = (64, 64)


def make_case(n_dots=200, seed=3):
    rng = np.random.default_rng(seed)
    ref = np.full(SHAPE, np.nan, dtype=np.float32)
    ref[2:-2, 2:-2] = 0.0
    fp = np.isfinite(ref)

    cat = np.zeros(SHAPE, dtype=np.float32)
    cat[32, :] = 1.0  # a horizontal catalogue trace through the middle

    ys, xs = np.nonzero(fp & (cat <= 0))
    dist = A.distance_from(cat > 0)
    ok = fp & (cat <= 0) & (dist >= 3)
    ys, xs = np.nonzero(ok)
    pick = rng.choice(len(ys), size=n_dots, replace=False)
    parent = np.full(SHAPE, np.nan, dtype=np.float32)
    parent[fp] = 0.0
    parent[ys[pick], xs[pick]] = 1.0

    rank = rng.random(SHAPE).astype(np.float32)
    prior = np.zeros(SHAPE, dtype=np.float32)
    prior[:, 40:] = 1.0  # everything in the east half has prior
    driver = rng.random(SHAPE).astype(np.float32)
    return dict(ref=ref, parent=parent, cat=cat, rank=rank, prior=prior, driver=driver)


def dots(a):
    return A.dots_of(a)


def test_footprint_convention_is_nan_outside_zero_inside():
    c = make_case()
    res = A.mass(c["parent"], c["ref"], c["rank"], c["cat"], 0.10, "drop")
    fp = np.isfinite(c["ref"])
    assert np.isnan(res.array[~fp]).all()
    assert np.all(np.isfinite(res.array[fp]))
    assert set(np.unique(res.array[fp])) <= {0.0, 1.0}


def test_zero_mass_on_catalogue_everywhere():
    c = make_case()
    for res in [
        A.mass(c["parent"], c["ref"], c["rank"], c["cat"], 0.10, "add"),
        A.prune(c["parent"], c["ref"], c["cat"], c["rank"], 3.0, refill=True),
        A.snap(c["parent"], c["ref"], c["driver"], c["cat"]),
        A.concentration(c["parent"], c["ref"], c["prior"], c["cat"]),
    ]:
        assert not (dots(res.array) & (c["cat"] > 0)).any(), res.axis


def test_mass_drop_removes_the_stated_fraction_and_never_adds():
    c = make_case()
    res = A.mass(c["parent"], c["ref"], c["rank"], c["cat"], 0.10, "drop")
    n0 = int(dots(c["parent"]).sum())
    assert dots(res.array).sum() == n0 - round(0.10 * n0)
    assert (dots(res.array) & ~dots(c["parent"])).sum() == 0
    assert res.stats["pct_changed"] == pytest.approx(10.0, abs=0.1)
    assert res.stats["delta_dots"] < 0


def test_mass_drop_removes_the_lowest_ranked_dots():
    c = make_case()
    rank = np.zeros(SHAPE, dtype=np.float32)
    par = c["parent"]
    ys, xs = np.nonzero(dots(par))
    rank[ys, xs] = np.arange(len(ys))  # deterministic ordering
    res = A.mass(par, c["ref"], rank, c["cat"], 0.10, "drop")
    removed = dots(par) & ~dots(res.array)
    kept_vals = rank[ys, xs]
    removed_vals = rank[removed]
    assert removed_vals.max() <= np.sort(kept_vals)[round(0.10 * len(ys)) - 1]


def test_mass_add_raises_the_count_by_the_stated_fraction():
    c = make_case()
    n0 = int(dots(c["parent"]).sum())
    res = A.mass(c["parent"], c["ref"], c["rank"], c["cat"], 0.10, "add")
    assert dots(res.array).sum() == n0 + round(0.10 * n0)
    assert res.stats["delta_dots"] > 0


def test_mass_rejects_out_of_range_fraction():
    c = make_case()
    for f in (0.005, 0.75):
        with pytest.raises(A.AxisError):
            A.mass(c["parent"], c["ref"], c["rank"], c["cat"], f, "drop")


def test_prune_removes_only_near_catalogue_dots():
    c = make_case()
    dist = A.distance_from(c["cat"] > 0)
    res = A.prune(c["parent"], c["ref"], c["cat"], c["rank"], 3.0, refill=True)
    removed = dots(c["parent"]) & ~dots(res.array)
    if removed.any():
        assert (dist[removed] <= 3.0).all()
    # an explicit refill holds the count
    assert dots(res.array).sum() == dots(c["parent"]).sum()
    assert res.stats["removed"] == res.stats["refilled"]


def test_prune_without_refill_drops_the_count():
    c = make_case()
    res = A.prune(c["parent"], c["ref"], c["cat"], None, 3.0, refill=False)
    assert dots(res.array).sum() == dots(c["parent"]).sum() - res.stats["removed"]


def test_prune_refill_requires_a_ranking():
    c = make_case()
    # force dots that need pruning
    cat = np.zeros(SHAPE, dtype=np.float32)
    cat[:, 30] = 1.0
    par = dots(c["parent"]) | (np.add.outer(np.arange(SHAPE[0]), np.zeros(SHAPE[1])) == 0)
    par[10:20, 29] = True
    p = np.where(par, 1.0, 0.0).astype(np.float32)
    with pytest.raises(A.AxisError):
        A.prune(p, c["ref"], cat, None, 3.0, refill=True)


def test_snap_preserves_count_and_respects_radius():
    c = make_case()
    res = A.snap(c["parent"], c["ref"], c["driver"], c["cat"], radius=2)
    assert dots(res.array).sum() == dots(c["parent"]).sum()
    assert res.stats["mean_displacement_px"] <= 2.0 * np.sqrt(2) + 1e-9
    assert res.stats["frozen_no_valid_target"] >= 0


def test_snap_is_identity_when_the_driver_peaks_where_the_dots_are():
    c = make_case(n_dots=60)
    par = c["parent"]
    driver = np.where(dots(par), 1.0, 0.0).astype(np.float32)
    # make each dot's own pixel strictly the max in its window
    res = A.snap(par, c["ref"], driver, c["cat"], radius=2)
    assert res.stats["moved"] == 0
    assert res.stats["mean_displacement_px"] == 0.0


def test_concentration_conserves_count_and_reduces_cv():
    c = make_case()
    res = A.concentration(c["parent"], c["ref"], c["prior"], c["cat"], block_px=16, fraction=0.15)
    assert dots(res.array).sum() == dots(c["parent"]).sum()
    assert res.stats["block_cv_after"] <= res.stats["block_cv_before"] + 1e-9
    assert 10.0 <= res.stats["pct_changed"] <= 50.0


def test_concentration_reports_its_block_size():
    c = make_case()
    res = A.concentration(c["parent"], c["ref"], c["prior"], c["cat"], block_px=8, fraction=0.10)
    assert res.stats["block_px"] == 8
    assert res.stats["block_km"] == pytest.approx(0.8)


def test_pct_changed_is_recorded_for_every_axis():
    c = make_case()
    for res in [
        A.mass(c["parent"], c["ref"], c["rank"], c["cat"], 0.10, "drop"),
        A.prune(c["parent"], c["ref"], c["cat"], c["rank"], 3.0, refill=True),
        A.snap(c["parent"], c["ref"], c["driver"], c["cat"]),
        A.concentration(c["parent"], c["ref"], c["prior"], c["cat"]),
    ]:
        assert "pct_changed" in res.stats, res.axis
        assert res.stats["n_dots"] == int(dots(res.array).sum())


def test_operators_do_not_mutate_the_parent():
    c = make_case()
    before = c["parent"].copy()
    A.mass(c["parent"], c["ref"], c["rank"], c["cat"], 0.10, "drop")
    A.prune(c["parent"], c["ref"], c["cat"], c["rank"], 3.0)
    A.snap(c["parent"], c["ref"], c["driver"], c["cat"])
    A.concentration(c["parent"], c["ref"], c["prior"], c["cat"])
    assert np.array_equal(c["parent"], before, equal_nan=True)
