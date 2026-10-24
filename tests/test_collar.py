"""Unit tests for the collar CONCENTRATION operator (synthetic grids only).

No competition data is read here: every fixture is a small synthetic raster, so these
tests run in CI where `data/` is absent.  The real arms are exercised end to end by
`scripts/build_concentration_collar.py`.
"""
from __future__ import annotations

import numpy as np
import pytest

from gems91 import collar


def grid(n=60):
    """Sparse dot lattice plus one catalogue row at y = 20.

    Spacing (6 px) is wider than the parent floor (2.83 px) so the collar band has
    room for a dozen acceptors, and the catalogue row is a straight line so the
    distance field is exact without scipy.
    """
    footprint = np.ones((n, n), dtype=bool)
    dots = np.zeros((n, n), dtype=bool)
    dots[5:40:6, 5:n:6] = True
    dcat = np.abs(np.arange(n)[:, None] - 20).astype(float) + np.zeros((n, n))
    return footprint, dots, dcat


# ------------------------------------------------------------------ weights
def test_collar_weight_is_zero_inside_the_legal_floor_and_beyond_the_band():
    d = np.array([0.0, 2.9, 3.0, 3.04, 3.05, 4.0, 5.99, 6.0, 9.0])
    w = collar.collar_weight(d)
    assert w[0] == 0.0 and w[1] == 0.0 and w[2] == 0.0 and w[3] == 0.0
    assert w[7] == 0.0 and w[8] == 0.0
    assert 0.0 < w[4] <= 1.0
    assert w[4] >= w[5] >= w[6] > 0.0


def test_collar_prior_never_masks_a_positive_weight():
    d = np.array([3.1, 4.0, 5.5])
    vote = np.array([0, 2, 3], dtype=np.int16)
    p = collar.collar_prior(d, vote)
    assert np.all(p > 0)                       # support orders cells, it never zeroes them
    # weight at 3.1 px is (6 - 3.1) / (6 - 3.05); vote 0 halves it
    assert p[0] == pytest.approx(0.5 * (6.0 - 3.1) / (6.0 - 3.05), rel=1e-6)
    # at equal distance, more support scores higher
    same_d = np.array([4.0, 4.0, 4.0])
    p2 = collar.collar_prior(same_d, np.array([0, 2, 3], dtype=np.int16))
    assert p2[2] > p2[1] > p2[0]


def test_remote_prior_excludes_the_collar_band():
    d = np.array([3.5, 9.9, 10.0, 10.1, 30.0])
    w = collar.remote_prior(d, None)
    assert w[0] == 0.0 and w[1] == 0.0 and w[2] == 0.0
    assert w[3] > 0.0 and w[4] >= w[3]


def test_support_fraction_range():
    v = np.array([0, 1, 2, 3])
    s = collar.support_fraction(v)
    assert s[0] == pytest.approx(0.5)
    assert s[-1] == pytest.approx(1.0)
    assert np.all(np.diff(s) > 0)


# ------------------------------------------------------------------ donors
def test_donor_order_returns_flat_indices_not_positions():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    order = collar.donor_order(dots, dcat, prior, block_px=10)
    assert order.dtype == np.int64
    # every returned index must land on a dot when interpreted as a flat raster index
    rows, cols = np.divmod(order, dots.shape[1])
    assert dots[rows, cols].all()
    assert order.size == int(dots.sum())


def test_donor_order_excludes_ineligible_dots():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    eligible = dcat >= 6.0
    order = collar.donor_order(dots, dcat, prior, block_px=10, eligible=eligible)
    rows, cols = np.divmod(order, dots.shape[1])
    assert eligible[rows, cols].all()


def test_donor_order_prefers_low_prior_blocks_first():
    footprint, dots, dcat = grid()
    prior = np.zeros(dots.shape)
    prior[:, 0:10] = 0.9          # high-prior strip on the left
    order = collar.donor_order(dots, dcat, prior, block_px=10)
    rows, cols = np.divmod(order, dots.shape[1])
    # the rightmost dots (no prior) must come out before the left-hand strip
    assert cols[0] > 10 and cols[-1] < 10


# --------------------------------------------------------------- acceptors
def test_acceptor_order_is_legal_and_sorted():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    acc = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    assert acc.size > 0
    rows, cols = np.divmod(acc, dots.shape[1])
    assert (dcat[rows, cols] > 3.05).all()
    assert (dcat[rows, cols] <= 6.0).all()
    score = prior[rows, cols]
    assert np.all(np.diff(score) <= 1e-12)          # non-increasing


def test_acceptor_order_is_deterministic_and_index_tie_broken():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    a = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    b = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    assert np.array_equal(a, b)
    same = np.ones(dots.shape)
    c = collar.acceptor_order(same, footprint, dcat, min_px=3.05, max_px=6.0)
    assert np.all(np.diff(c) > 0)                   # flat index order within ties


# --------------------------------------------------------------- relocation
def test_relocate_preserves_count_and_returns_flat_targets():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    donors = collar.donor_order(dots, dcat, prior, block_px=10, eligible=dcat >= 6.0)
    acc = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    res = collar.relocate(dots, donors, acc, max_donors=8)
    assert res.stats["count_preserved"] is True
    assert int(res.dots.sum()) == int(dots.sum())
    assert res.stats["n_moved"] == 8
    assert res.targets.shape == (8, 2)
    rows, cols = res.targets[:, 0], res.targets[:, 1]
    assert res.dots[rows, cols].all()
    assert res.moved.sum() == 8


def test_relocate_never_puts_mass_on_the_catalogue_or_inside_the_floor():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    donors = collar.donor_order(dots, dcat, prior, block_px=10, eligible=dcat >= 6.0)
    acc = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    res = collar.relocate(dots, donors, acc, max_donors=12)
    rows, cols = res.targets[:, 0], res.targets[:, 1]
    assert (dcat[rows, cols] > collar.COLLAR_FLOOR_PX).all()


def test_relocate_honours_the_parent_separation_floor():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    donors = collar.donor_order(dots, dcat, prior, block_px=10, eligible=dcat >= 6.0)
    acc = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    res = collar.relocate(dots, donors, acc, max_donors=16)
    rows, cols = np.nonzero(res.dots)
    pts = np.c_[rows, cols].astype(float)
    from scipy.spatial import cKDTree
    d, _ = cKDTree(pts).query(pts, k=2)
    assert d[:, 1].min() >= collar.PARENT_MIN_NN_PX - 1e-9


def test_relocate_is_deterministic():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    donors = collar.donor_order(dots, dcat, prior, block_px=10, eligible=dcat >= 6.0)
    acc = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    a = collar.relocate(dots, donors, acc, max_donors=10)
    b = collar.relocate(dots, donors, acc, max_donors=10)
    assert np.array_equal(a.dots, b.dots)


def test_relocate_raises_when_the_acceptor_pool_is_exhausted():
    footprint, dots, dcat = grid()
    prior = collar.collar_prior(dcat, None)
    donors = collar.donor_order(dots, dcat, prior, block_px=10)
    acc = collar.acceptor_order(prior, footprint, dcat, min_px=3.05, max_px=6.0)
    with pytest.raises(collar.CollarError):
        collar.relocate(dots, donors, acc[:3], max_donors=40)


def test_block_mean_is_nan_outside_the_footprint():
    field_ = np.ones((20, 20))
    footprint = np.zeros((20, 20), dtype=bool)
    footprint[:10, :10] = True
    bm, size = collar.block_mean(field_, footprint, block_px=10)
    assert size == 10
    assert bm[0, 0] == pytest.approx(1.0)
    assert np.isnan(bm[1, 1])
