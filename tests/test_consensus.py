"""Tests for the MASS/consensus ranking (src/gems91/consensus.py).

Synthetic geometry for the rules, plus one integration check that pins the real
parent's support histogram when the pinned inputs happen to be present.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import consensus as C  # noqa: E402

DATA = ROOT / "data"
PARENT = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
FIELDS = [DATA / "registry" / n for n in ("calib_h195_01922.tif", "calib_h194_01894.tif",
                                          "calib_h161_01855.tif")]
pytestmark = []


def grid(dots_at=(), fields=(), shape=(12, 12)):
    dots = np.zeros(shape, dtype=bool)
    for r, c in dots_at:
        dots[r, c] = True
    fs = []
    for cells in fields:
        f = np.zeros(shape, dtype=bool)
        for r, c in cells:
            f[r, c] = True
        fs.append(f)
    return dots, fs


def test_vote_count_is_a_sum_not_a_threshold():
    _, fs = grid(fields=[[(1, 1)], [(1, 1)], []])
    v = C.vote_count(fs)
    assert v[1, 1] == 2
    assert int(v.sum()) == 2


def test_vote_count_refuses_non_binary():
    f = np.zeros((4, 4), dtype=np.float32)
    f[0, 0] = 0.5
    with pytest.raises(ValueError):
        C.vote_count([f])


def test_vote_count_refuses_shape_mismatch():
    with pytest.raises(ValueError):
        C.vote_count([np.zeros((4, 4)), np.zeros((4, 5))])


def test_select_drop_removes_whole_strata_only():
    dots, fs = grid(dots_at=[(2, 2), (3, 3), (4, 4)], fields=[[(2, 2), (3, 3)], [(2, 2)], []])
    rank = C.build_rank(fs, dots)
    # (2,2) is in two fields, (3,3) in one, (4,4) in none -> votes 2, 1, 0
    assert rank.histogram(dots) == [1, 1, 1, 0]
    drop1 = C.select_drop(dots, rank, 1)
    assert int(drop1.sum()) == 2 and drop1[3, 3] and drop1[4, 4] and not drop1[2, 2]
    drop2 = C.select_drop(dots, rank, 2)
    assert int(drop2.sum()) == 3


def test_select_add_is_deterministic_and_exact():
    dots, fs = grid(dots_at=[(6, 6)], fields=[[(r, 6) for r in range(12)]])
    rank = C.build_rank(fs, dots)
    fp = np.ones((12, 12), dtype=bool)
    dcat = np.full((12, 12), 99.0)
    a = C.select_add(dots, rank, fp, dcat, 5)
    b = C.select_add(dots, rank, fp, dcat, 5)
    assert np.array_equal(a, b)
    assert int(a.sum()) == 5
    assert not (a & dots).any()


def test_select_add_respects_footprint_and_collar():
    dots, fs = grid(dots_at=[(6, 6)], fields=[[(r, 6) for r in range(12)]])
    rank = C.build_rank(fs, dots)
    fp = np.ones((12, 12), dtype=bool)
    fp[0, :] = False                      # out of footprint
    dcat = np.full((12, 12), 99.0)
    dcat[:, 6] = 1.0                      # the whole ridge is inside the collar
    with pytest.raises(ValueError):
        C.select_add(dots, rank, fp, dcat, 3)
    dcat[:, 6] = 5.0
    a = C.select_add(dots, rank, fp, dcat, 3)
    assert not a[0, :].any()


def test_select_add_prefers_support_then_distance_from_a_dot():
    dots, fs = grid(dots_at=[(5, 5)], fields=[[(5, 2), (10, 10)], [(10, 10)], []])
    rank = C.build_rank(fs, dots)
    fp = np.ones((12, 12), dtype=bool)
    dcat = np.full((12, 12), 99.0)
    # (10,10) has support 2 and (5,2) support 1: support dominates distance.
    first = C.select_add(dots, rank, fp, dcat, 1)
    assert first[10, 10]


def test_select_add_never_invents_mass_where_no_field_supports_it():
    dots, fs = grid(dots_at=[(5, 5)], fields=[[(5, 2)]])
    rank = C.build_rank(fs, dots)
    fp = np.ones((12, 12), dtype=bool)
    dcat = np.full((12, 12), 99.0)
    with pytest.raises(ValueError):
        C.select_add(dots, rank, fp, dcat, 2)   # only one supported cell exists


def test_frame_encoding_and_diff_stats():
    dots = np.zeros((4, 4), dtype=bool)
    dots[1, 1] = True
    fp = np.zeros((4, 4), dtype=bool)
    fp[1:3, 1:3] = True
    arr = C.frame(dots, fp)
    assert np.isnan(arr[~fp]).all()
    assert arr[1, 1] == 1.0 and arr[2, 2] == 0.0
    st = C.diff_stats(dots, dots)
    assert st["changed"] == 0 and st["pct_changed"] == 0.0


@pytest.mark.skipif(not all(p.is_file() for p in [PARENT, *FIELDS]),
                    reason="pinned inputs absent - run scripts/restore_data.py")
def test_real_parent_support_histogram_is_pinned():
    """The numbers quoted in the mechanism cards and SLOT_PLAN, measured, not remembered."""
    import rasterio

    def rd(p):
        with rasterio.open(p) as s:
            return s.read(1)

    dots = rd(PARENT) > 0
    fields = [rd(p) > 0 for p in FIELDS]
    rank = C.build_rank(fields, dots)
    assert int(dots.sum()) == 37654
    assert rank.histogram(dots) == [0, 4541, 6200, 26913]
    assert np.all(rank.vote[dots] >= 1)          # no R0 dot sits outside all three fields
    assert np.all(rank.dot_distance[dots] == 0)  # a dot is at distance 0 from itself
