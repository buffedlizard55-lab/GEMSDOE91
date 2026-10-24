"""Strain-prior derivation and donor-quarantine tests (Session 8).

Everything runs on tiny synthetic arrays: no competition data is read.
"""
from __future__ import annotations

import numpy as np
import pytest

from gems91 import prior as priors
from gems91 import strain
from tools.run_concentration import build_concentration


def test_fill_sentinel_uses_nearest_valid_cell():
    fp = np.ones((3, 3), dtype=bool)
    band = np.array([[1.0, 2.0, -3.4e38],
                     [3.0, 4.0, 5.0],
                     [6.0, 7.0, 8.0]])
    filled, n = strain.fill_sentinel(band, fp)
    assert n == 1
    # nearest valid cells to (0,2) are (0,1)=2 and (1,2)=5 (both 1 px); EDT tie
    # resolution is deterministic but either neighbour proves the Sentinel is gone
    assert filled[0, 2] in (2.0, 5.0)
    assert np.isfinite(filled).all()
    assert band[0, 2] == -3.4e38  # input not mutated


def test_fill_sentinel_counts_nonfinite_and_ignores_outside():
    fp = np.array([[True, True], [True, False]])
    band = np.array([[1.0, np.nan], [2.0, -3.4e38]])
    filled, n = strain.fill_sentinel(band, fp)
    assert n == 1                      # only the footprint NaN is filled
    assert filled[0, 1] in (1.0, 2.0)
    assert filled[1, 1] == -3.4e38     # outside footprint untouched


def test_fill_sentinel_refuses_an_all_sentinel_band():
    with pytest.raises(ValueError, match="no valid footprint cells"):
        strain.fill_sentinel(np.full((2, 2), -3.4e38), np.ones((2, 2), bool))


def test_percentile_rank_average_ties():
    fp = np.ones((2, 3), dtype=bool)
    band = np.array([[0.0, 0.0, 5.0], [5.0, 5.0, 9.0]])
    pct = strain.percentile_rank(band, fp)
    # ranks (0-based avg): 0 -> 0.5, 5 -> 3.0, 9 -> 5.0; divide by n-1 = 5
    assert pct[0, 0] == pytest.approx(0.1) and pct[0, 1] == pytest.approx(0.1)
    assert pct[0, 2] == pytest.approx(0.6) and pct[1, 2] == pytest.approx(1.0)


def test_percentile_rank_nan_outside_and_refuses_unfilled():
    fp = np.array([[True, False]])
    with pytest.raises(ValueError, match="filled"):
        strain.percentile_rank(np.array([[np.nan, 1.0]]), fp)
    pct = strain.percentile_rank(np.array([[3.0, 1.0]]), fp)
    assert np.isnan(pct[0, 1])


def test_strain_prior_is_equal_weight_and_digest_stable():
    fp = np.ones((4, 4), dtype=bool)
    b4 = np.arange(16, dtype=float).reshape(4, 4)
    b7 = np.flip(b4)
    arr, stats = strain.strain_prior(b4, b7, fp)
    # reversed equal-weight ranks cancel exactly: every cell is the median rank
    assert np.allclose(arr, 0.5)
    assert stats["weights"] == [0.5, 0.5]
    arr2, _ = strain.strain_prior(b4.copy(), b7.copy(), fp)
    assert priors.array_digest(arr) == priors.array_digest(arr2)


def test_dilatation_prior_high_percentile_is_most_positive():
    fp = np.ones((1, 4), dtype=bool)
    arr, _ = strain.dilatation_prior(np.array([[-16.5, -1.0, 5.5, 34.5]]), fp)
    assert arr[0, 0] == 0.0 and arr[0, 3] == 1.0


def _synthetic(seed=3, n=60, shape=(120, 140)):
    rng = np.random.default_rng(seed)
    footprint = np.ones(shape, dtype=bool)
    catalogue = np.zeros(shape, dtype=bool)
    catalogue[60, :] = True
    prior = np.tile(np.linspace(0, 1, shape[1]), (shape[0], 1)).astype(np.float32)
    from scipy import ndimage as ndi
    dcat = ndi.distance_transform_edt(~catalogue)
    cells = []
    while len(cells) < n:
        r, c = int(rng.integers(shape[0])), int(rng.integers(shape[1]))
        if dcat[r, c] > 2.0 and (r, c) not in cells:
            cells.append((r, c))
    parent = np.zeros(shape, dtype=np.float32)
    for r, c in cells:
        parent[r, c] = 1.0
    return parent, prior, footprint, catalogue, dcat, cells


def test_donor_exclude_quarantines_dots_in_place():
    parent, prior, footprint, catalogue, dcat, cells = _synthetic()
    exclude = dcat <= 3.0
    band, stats = build_concentration(parent, prior, footprint, catalogue,
                                      frac=0.15, block_px=20, seed=7,
                                      donor_exclude=exclude)
    kept = {(int(r), int(c)) for r, c in zip(*np.nonzero(parent > 0))}
    after = {(int(r), int(c)) for r, c in zip(*np.nonzero(np.nan_to_num(band) > 0))}
    quarantined = {(r, c) for r, c in cells if exclude[r, c]}
    assert quarantined <= after, "a quarantined (collar) dot was moved"
    assert stats["donor_excluded_dots"] == len(quarantined)
    assert stats["count_preserved"] and len(after) == len(kept)


def test_donor_exclude_defaults_to_old_behaviour():
    parent, prior, footprint, catalogue, _, _ = _synthetic()
    a, sa = build_concentration(parent, prior, footprint, catalogue,
                                frac=0.15, block_px=20, seed=7)
    b, sb = build_concentration(parent, prior, footprint, catalogue,
                                frac=0.15, block_px=20, seed=7, donor_exclude=None)
    assert np.array_equal(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9))
    assert sa["n_dots_moved"] == sb["n_dots_moved"]
    assert sa["donor_excluded_dots"] == 0


def test_donor_exclude_wrong_shape_is_refused():
    parent, prior, footprint, catalogue, _, _ = _synthetic()
    with pytest.raises(ValueError, match="donor_exclude"):
        build_concentration(parent, prior, footprint, catalogue, frac=0.15,
                            block_px=20, donor_exclude=np.zeros((3, 3), bool))
