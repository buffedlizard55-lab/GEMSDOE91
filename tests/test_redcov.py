"""Unit tests for the SPACING/redcov operator (synthetic grids, no competition data)."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage as ndi

from gems91 import redcov


def _grid():
    """60x60 grid: one tight cluster (redundant), some spaced dots, supported far cells."""
    shape = (60, 60)
    dots = np.zeros(shape, dtype=bool)
    # tight cluster around (10,10): mutual distances < 6 px -> high redundancy
    for y, x in [(10, 10), (10, 12), (12, 11), (11, 13), (13, 10)]:
        dots[y, x] = True
    # spaced line of dots
    for k in range(6):
        dots[30, 5 + 6 * k] = True
    # one isolated dot
    dots[50, 50] = True
    catalogue = np.zeros(shape, dtype=bool)
    catalogue[45, 10] = True                      # one catalogue pixel
    dots[45, 12] = True                           # collar dot at d=2 px (must be quarantined)
    dcat = ndi.distance_transform_edt(~catalogue)
    footprint = np.ones(shape, dtype=bool)
    vote = np.zeros(shape, dtype=np.int8)
    vote[20:24, 40:50] = 1                        # supported patch far from every dot
    vote[5, 40:50] = 2                            # stronger-supported row, also far
    vote[dots] = 3
    return dots, vote, dcat, footprint, catalogue


def test_redundancy_ranks_cluster_above_isolated():
    dots, *_ = _grid()
    ys, xs, red = redcov.redundancy_scores(dots)
    score = {(int(y), int(x)): float(s) for y, x, s in zip(ys, xs, red)}
    assert score[(10, 10)] > 0
    assert score[(50, 50)] == 0.0
    assert score[(10, 10)] > score[(30, 5)]


def test_count_conserved_and_collar_quarantined():
    dots, vote, dcat, footprint, catalogue = _grid()
    out = redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.15, min_vote=1)
    child, donors, recips = out["child"], out["donors"], out["recipients"]
    assert int(child.sum()) == int(dots.sum())
    assert child[45, 12], "collar dot must be inherited, never a donor"
    assert not donors[45, 12]
    assert int((dcat[recips] <= 3.0).sum()) == 0, "no recipient inside the 3 px collar"
    assert int((child & catalogue).sum()) == 0
    assert int((donors & recips).sum()) == 0, "a moved dot never refills its own cell"


def test_donors_come_from_the_cluster_not_the_isolated_dot():
    dots, vote, dcat, footprint, _ = _grid()
    out = redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.08, min_vote=1)  # moves 1 dot
    assert out["stats"]["n_moved"] == 1
    dy, dx = np.nonzero(out["donors"])
    assert (int(dy[0]), int(dx[0])) in {(10, 10), (10, 12), (12, 11), (11, 13), (13, 10)}


def test_recipients_respect_min_separation_and_support():
    dots, vote, dcat, footprint, _ = _grid()
    out = redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.25, min_vote=2)
    recips = out["recipients"]
    assert (vote[recips] >= 2).all()
    occ = out["child"]
    d = ndi.distance_transform_edt(~occ)
    # every recipient's nearest *other* dot is >= 2.8 px: check pairwise via EDT on child minus self
    ys, xs = np.nonzero(recips)
    for y, x in zip(ys, xs):
        others = occ.copy(); others[y, x] = False
        assert ndi.distance_transform_edt(~others)[y, x] >= 2.8 - 1e-9


def test_deterministic_and_frac_bounds():
    dots, vote, dcat, footprint, _ = _grid()
    a = redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.15, min_vote=1)
    b = redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.15, min_vote=1)
    assert np.array_equal(a["child"], b["child"])
    with pytest.raises(ValueError):
        redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.6)
    with pytest.raises(ValueError):
        redcov.apply_redcov(dots, vote, dcat, footprint, frac=0.1, min_vote=0)
