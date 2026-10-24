"""Unit tests for the MASS-expansion builder (synthetic grids only, no competition data)."""
from __future__ import annotations

import numpy as np
import pytest

from gems91 import massexpand


def _grid(h=40, w=60):
    field = np.zeros((h, w), dtype=np.float32)
    field[10:30, 10:50] = 1.0
    votes = np.full((h, w), 3, dtype=np.int8)
    parent = np.zeros((h, w), dtype=np.float32)
    parent[10:30:4, 10:50:4] = 1.0
    parent[~np.ones((h, w), dtype=bool)] = np.nan   # nothing outside the footprint anyway
    catalogue = np.zeros((h, w), dtype=np.float32)
    catalogue[20, 30] = 1.0
    footprint = np.ones((h, w), dtype=bool)
    return field, votes, parent, catalogue, footprint


def test_vote_map_counts_support():
    a = np.array([[0, 1], [1, 0]], dtype=np.float32)
    b = np.array([[1, 1], [0, 0]], dtype=np.float32)
    v = massexpand.vote_map(a, b)
    assert v.tolist() == [[1, 2], [1, 0]]


def test_vote_map_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        massexpand.vote_map(np.zeros((3, 3)), np.zeros((3, 4)))


def test_pools_respect_catalogue_floor_and_field():
    field, votes, parent, catalogue, footprint = _grid()
    pools = massexpand.candidate_pools(field, votes, parent, catalogue, footprint, min_gap_px=3.0)
    elig = pools["eligible"]
    assert not elig[parent > 0].any(), "parent dots must not be candidates"
    assert not elig[np.nan_to_num(catalogue) > 0].any()
    d = pools["distance_to_catalogue_px"]
    assert (d[elig] > 3.0).all()
    assert elig.sum() > 0


def test_vote_threshold_filters_low_support_cells():
    field, votes, parent, catalogue, footprint = _grid()
    votes = votes.copy()
    votes[:15] = 1
    lo = massexpand.candidate_pools(field, votes, parent, catalogue, footprint, vote_threshold=1)
    hi = massexpand.candidate_pools(field, votes, parent, catalogue, footprint, vote_threshold=3)
    assert 0 < hi["adj"].sum() < lo["adj"].sum()
    assert not hi["adj"][:15].any()


def test_adj_arm_only_touches_parent_dots():
    field, votes, parent, catalogue, footprint = _grid()
    band, stats = massexpand.build_arm(parent, field, votes, catalogue, footprint,
                                       n_add=25, pool="adj")
    added = (band > 0) & (parent <= 0)
    assert added.sum() == 25
    assert stats["added_distance_to_nearest_parent_dot_px"]["max"] <= np.sqrt(2) + 1e-9
    assert stats["n_added"] == 25 and stats["n_removed"] == 0
    assert stats["n_dots_candidate"] == stats["n_dots_parent"] + 25


def test_spaced_arm_preserves_the_no_adjacency_texture():
    field, votes, parent, catalogue, footprint = _grid()
    band, stats = massexpand.build_arm(parent, field, votes, catalogue, footprint,
                                       n_add=25, pool="spaced")
    occ = band > 0
    from scipy import ndimage as ndi
    k = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int8)   # centre excluded
    neigh = ndi.convolve(occ.astype(np.int8), k, mode="constant")
    assert (neigh[occ] == 0).all(), "no two dots (added or parent) may be 8-adjacent"
    assert stats["added_distance_to_nearest_parent_dot_px"]["min"] > np.sqrt(2)


def test_selection_is_deterministic_and_seed_sensitive():
    field, votes, parent, catalogue, footprint = _grid()
    pools = massexpand.candidate_pools(field, votes, parent, catalogue, footprint)
    a, _ = massexpand.select_cells(pools["adj"], 12, seed=91024)
    b, _ = massexpand.select_cells(pools["adj"], 12, seed=91024)
    c, _ = massexpand.select_cells(pools["adj"], 12, seed=7)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_shortfall_is_an_error_not_a_silent_shrink():
    field, votes, parent, catalogue, footprint = _grid()
    pools = massexpand.candidate_pools(field, votes, parent, catalogue, footprint)
    too_many = int(pools["spaced"].sum()) + 5
    with pytest.raises(ValueError, match="only supplied"):
        massexpand.build_arm(parent, field, votes, catalogue, footprint,
                             n_add=too_many, pool="spaced")


def test_band_has_nan_outside_footprint_and_unit_mass_inside():
    field, votes, parent, catalogue, footprint = _grid()
    footprint = footprint.copy()
    footprint[:, 55:] = False
    band, _ = massexpand.build_arm(parent, field, votes, catalogue, footprint,
                                   n_add=10, pool="adj")
    assert np.isnan(band[~footprint]).all()
    assert np.isfinite(band[footprint]).all()
    assert set(np.unique(band[footprint])) <= {0.0, 1.0}


def test_bad_pool_is_rejected():
    field, votes, parent, catalogue, footprint = _grid()
    with pytest.raises(ValueError, match="pool must be"):
        massexpand.build_arm(parent, field, votes, catalogue, footprint, n_add=1, pool="nope")
