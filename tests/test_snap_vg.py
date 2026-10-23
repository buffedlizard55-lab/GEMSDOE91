"""Invariants of the SNAP (vertical-gradient) operator, on synthetic arrays.

These are the promises the SNAP arms in `releases/` make, restated as tests so a future
session cannot quietly break one while rebuilding:

  * count preserved exactly (SNAP never adds or removes mass);
  * the 2 px spacing floor survives the edit (R0 has 0 pairs < 2 px, the d2.8 rule);
  * dots already inside the 3 px catalogue collar are frozen, not moved
    (otherwise the axis silently also runs a partial PRUNE - IR-91-27);
  * displacements never exceed the stated radius (Euclidean, not a square window);
  * the mean driver value at the dots rises, or the arm is a no-op and must not ship;
  * the operator is deterministic (no RNG on the treatment path).

No competition data is read.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import build_snap_geodetic as S  # noqa: E402

SHAPE = (80, 80)


def make_case(n_dots: int = 300, seed: int = 5, n_cat: int = 3):
    """Synthetic grid: footprint, a N-S catalogue line, scattered dots, smooth driver."""
    rng = np.random.default_rng(seed)
    ref = np.full(SHAPE, np.nan, dtype=np.float32)
    ref[2:-2, 2:-2] = 0.0
    footprint = np.isfinite(ref)

    cat = np.zeros(SHAPE, dtype=bool)
    cat[10:70, 20] = True                      # a N-S trace
    dcat = ndimage.distance_transform_edt(~cat)

    # dots: Poisson-ish, honouring the 2 px floor and the 3 px collar
    ok = footprint & (dcat > S.MIN_CAT_PX)
    ys, xs = np.nonzero(ok)
    order = rng.permutation(len(ys))
    taken: list[tuple[int, int]] = []
    for k in order:
        y, x = int(ys[k]), int(xs[k])
        if all((y - a) ** 2 + (x - b) ** 2 >= 4 for a, b in taken):
            taken.append((y, x))
        if len(taken) == n_dots:
            break
    parent = np.zeros(SHAPE, dtype=bool)
    for y, x in taken:
        parent[y, x] = True

    # a few inherited collar dots inside 2 < d_cat <= 3 px, like R0's 2,171
    collar = footprint & (dcat > 2.0) & (dcat <= 3.0)
    cys, cxs = np.nonzero(collar)
    pick = rng.choice(len(cys), size=min(n_cat, len(cys)), replace=False)
    for k in pick:
        parent[int(cys[k]), int(cxs[k])] = True

    # smooth driver with ridges, so a local argmax exists almost everywhere
    yy, xx = np.mgrid[0:SHAPE[0], 0:SHAPE[1]]
    driver = (np.sin(yy / 3.0) + np.cos(xx / 4.0) + 0.3 * rng.standard_normal(SHAPE))
    driver[~footprint] = np.nan
    return dict(parent=parent, footprint=footprint, dcat=dcat, cat=cat, driver=driver)


def min_separation(dots: np.ndarray) -> float:
    ys, xs = np.nonzero(dots)
    pts = np.c_[ys, xs].astype(float)
    d, _ = cKDTree(pts).query(pts, k=2)
    return float(d[:, 1].min())


@pytest.mark.parametrize("radius", [1, 2, 3])
def test_count_preserved_and_displacement_bounded(radius):
    c = make_case()
    res = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=radius)
    assert res["n_dots"] == int(c["parent"].sum())
    assert res["max_displacement_px"] <= radius + 1e-9


@pytest.mark.parametrize("radius", [1, 2, 3])
def test_spacing_floor_survives(radius):
    c = make_case()
    res = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=radius)
    assert min_separation(c["parent"]) >= 2.0      # precondition on the fixture
    assert res["min_separation_after_px"] >= 2.0 - 1e-9


@pytest.mark.parametrize("radius", [1, 2, 3])
def test_collar_dots_are_frozen(radius):
    c = make_case()
    dcat, parent = c["dcat"], c["parent"]
    res = S.snap(parent, c["driver"], c["footprint"], dcat, radius=radius)
    before = parent & (dcat <= S.MIN_CAT_PX)
    after = res["dots"] & (dcat <= S.MIN_CAT_PX)
    assert np.array_equal(before, after), "a collared dot moved: the axis became part-PRUNE"


def test_no_dot_ever_lands_in_the_collar_or_on_the_catalogue():
    c = make_case()
    res = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=3)
    new = res["dots"] & ~c["parent"]
    assert not (new & c["cat"]).any()
    assert (c["dcat"][new] > S.MIN_CAT_PX).all()


def test_mean_driver_rises_at_the_dots():
    c = make_case()
    res = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=2)
    assert res["driver_pct_after"] > res["driver_pct_before"]


def test_deterministic_across_calls():
    c = make_case()
    a = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=2)
    b = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=2)
    assert np.array_equal(a["dots"], b["dots"])
    assert a["moved"] == b["moved"]


def test_null_arm_is_reproducible_for_a_seeded_generator():
    c = make_case()
    a = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=2,
               rng=np.random.default_rng(91))
    b = S.snap(c["parent"], c["driver"], c["footprint"], c["dcat"], radius=2,
               rng=np.random.default_rng(91))
    assert np.array_equal(a["dots"], b["dots"])
    # the null must not also maximise the driver
    assert a["driver_pct_after"] < 0.60


def test_pct_rank_strips_the_minus_3e38_sentinel():
    arr = np.full((6, 6), -3.4028235e38, dtype=np.float32)
    arr[1:5, 1:5] = np.arange(16, dtype=np.float32).reshape(4, 4)
    fp = np.zeros((6, 6), dtype=bool)
    fp[1:5, 1:5] = True
    pct = S.pct_rank_in_footprint(arr, fp)
    assert np.isfinite(pct[fp]).all()
    assert np.isnan(pct[~fp]).all()
    assert pct[fp].min() == 0.0 and pct[fp].max() == 1.0
