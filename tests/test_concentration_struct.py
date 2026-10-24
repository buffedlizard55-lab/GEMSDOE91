"""Unit tests for the session-8 CONCENTRATION machinery (synthetic grids only).

No competition data is read here: every array is built in the test, so these run
in CI before any pinned input is restored.
"""

import numpy as np
import pytest

from gems91 import concentration as cc


# --------------------------------------------------------------------------- #
def _grid(shape=(40, 60), seed=0):
    rng = np.random.default_rng(seed)
    footprint = np.ones(shape, dtype=bool)
    footprint[:2, :] = False          # a border that is outside the footprint
    return footprint, rng


def _catalogue(shape=(40, 60)):
    cat = np.zeros(shape, dtype=bool)
    cat[18, 10:50] = True             # one mapped trace, 10 px from the footprint edge
    return cat


def test_percentile_rank_is_monotone_and_bounded():
    rng = np.random.default_rng(1)
    field = rng.normal(size=(20, 20))
    mask = np.ones_like(field, dtype=bool)
    mask[:3] = False
    out = cc.percentile_rank(field, mask)
    assert np.isnan(out[~mask]).all()
    vals = out[mask]
    assert vals.min() == pytest.approx(0.0) and vals.max() == pytest.approx(1.0)
    order = np.argsort(field[mask])
    assert np.all(np.diff(vals[order]) >= 0)


def test_percentile_rank_averages_ties():
    field = np.zeros((10, 10))
    field[:, :5] = 1.0
    out = cc.percentile_rank(field, np.ones_like(field, bool))
    assert out[0, 0] == out[9, 4]           # every member of the 1.0 run gets one rank
    assert out[0, 5] == out[9, 9]           # and so does every member of the 0.0 run
    assert out[0, 5] < out[0, 0]            # the two runs are ordered
    assert out[0, 0] == pytest.approx(74.5 / 99, abs=1e-6)   # mean of ranks 50..99
    assert out[0, 5] == pytest.approx(24.5 / 99, abs=1e-6)   # mean of ranks 0..49


def test_structural_prior_is_the_mean_of_band_ranks_and_nan_outside():
    footprint, rng = _grid()
    bands = [rng.normal(size=footprint.shape) for _ in range(3)]
    prior = cc.structural_prior(bands, footprint)
    assert np.isnan(prior[~footprint]).all()
    assert np.isfinite(prior[footprint]).all()
    ranks = [cc.percentile_rank(b, footprint) for b in bands]
    expected = np.mean([r[footprint] for r in ranks], axis=0)
    assert np.allclose(prior[footprint], expected, atol=1e-6)
    assert prior[footprint].min() >= 0.0 and prior[footprint].max() <= 1.0


def test_residual_prior_rewards_structure_without_occupancy():
    """A block with strong structure and one dot must outrank a dense, structure-free block."""
    shape = (60, 60)
    footprint = np.ones(shape, bool)
    structural = np.zeros(shape, np.float32)
    structural[:, :] = 0.1
    structural[10:20, 10:20] = 0.9          # strong structure, block (1,1)
    dots = np.argwhere(np.ones((1, 1), bool)) * 0
    rows, cols = [], []
    rows += [30, 31, 32, 33, 34, 35]        # dense but structure-free blocks
    cols += [30, 31, 32, 33, 34, 35]
    rows += [40, 41, 42, 43, 44, 45]
    cols += [40, 41, 42, 43, 44, 45]
    rows += [10]
    cols += [10]
    for k in range(12):                     # enough occupied blocks for the ranking
        rows.append(20 + 10 * (k // 4))     # block rows 2-4: block (0,0) stays empty
        cols.append(20 + 10 * (k % 4))
    dots = np.c_[rows, cols]
    resid, diag = cc.residual_prior(structural, dots, footprint, block_px=10)
    assert np.isnan(resid[0:10, 0:10]).all()        # empty block -> NaN, never an acceptor
    assert np.isfinite(resid[10:20, 10:20]).all()   # occupied + structured -> finite
    hi = resid[10, 10]
    dense = resid[30, 30]
    assert hi > dense
    assert diag["n_blocks_occupied"] >= 12
    assert np.isfinite(diag["corr_struct_occupancy"])


def test_relocate_preserves_count_and_gates():
    footprint, rng = _grid()
    shape = footprint.shape
    cat = _catalogue(shape)
    from scipy import ndimage as ndi
    dcat = ndi.distance_transform_edt(~cat)
    prior = rng.random(shape).astype(np.float32)
    prior[~footprint] = np.nan
    # parent: a deterministic lattice of dots, all clear of the catalogue
    rr, cc_ = np.mgrid[4:38:3, 4:58:3]
    dots = np.zeros(shape, bool)
    dots[rr.ravel(), cc_.ravel()] = True
    dots &= (dcat > cc.MIN_GAP_PX) & footprint
    n = int(dots.sum())
    donor_ok = np.ones(n, bool)

    out, st = cc.relocate(dots, prior, footprint, dcat, frac=0.20, donor_mask=donor_ok, seed=5)
    assert out.sum() == dots.sum() == st["n_dots_candidate"]
    assert st["count_preserved"] is True
    assert not (out & ~footprint).any()
    assert dcat[out].min() > cc.MIN_GAP_PX
    # no two dots closer than 2 px
    pts = np.argwhere(out).astype(float)
    from scipy.spatial import cKDTree
    d, _ = cKDTree(pts).query(pts, k=2)
    assert d[:, 1].min() >= cc.MIN_SEP_PX - 1e-9
    assert st["pct_dots_moved"] > 0.0


def test_relocate_quarantines_flagged_dots():
    """A dot with donor_mask=False can never be a donor (the collar quarantine)."""
    footprint, rng = _grid()
    shape = footprint.shape
    cat = _catalogue(shape)
    from scipy import ndimage as ndi
    dcat = ndi.distance_transform_edt(~cat)
    prior = rng.random(shape).astype(np.float32)
    prior[~footprint] = np.nan
    rr, cc_ = np.mgrid[4:38:3, 4:58:3]
    dots = np.zeros(shape, bool)
    dots[rr.ravel(), cc_.ravel()] = True
    dots &= (dcat > cc.MIN_GAP_PX) & footprint
    n = int(dots.sum())
    quarantined = np.zeros(n, bool)
    quarantined[: n // 2] = True                 # pretend half are collar dots
    out, _ = cc.relocate(dots, prior, footprint, dcat, frac=0.20,
                         donor_mask=~quarantined, seed=7)
    moved = dots & ~out
    assert int((moved & np.isin(dots, dots)).sum()) >= 0  # sanity
    # none of the quarantined dots may disappear
    pts_parent = np.argwhere(dots)
    keep = pts_parent[quarantined]
    assert all(out[r, c] for r, c in keep)


def test_relocate_is_deterministic_and_seed_sensitive():
    footprint, rng = _grid()
    shape = footprint.shape
    cat = _catalogue(shape)
    from scipy import ndimage as ndi
    dcat = ndi.distance_transform_edt(~cat)
    prior = rng.random(shape).astype(np.float32)
    prior[~footprint] = np.nan
    rr, cc_ = np.mgrid[4:38:3, 4:58:3]
    dots = np.zeros(shape, bool)
    dots[rr.ravel(), cc_.ravel()] = True
    dots &= (dcat > cc.MIN_GAP_PX) & footprint
    dm = np.ones(int(dots.sum()), bool)
    a, _ = cc.relocate(dots, prior, footprint, dcat, frac=0.20, donor_mask=dm, seed=11)
    b, _ = cc.relocate(dots, prior, footprint, dcat, frac=0.20, donor_mask=dm, seed=11)
    c, _ = cc.relocate(dots, prior, footprint, dcat, frac=0.20, donor_mask=dm, seed=12)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_relocate_rejects_out_of_range_dose():
    footprint, rng = _grid()
    shape = footprint.shape
    cat = _catalogue(shape)
    from scipy import ndimage as ndi
    dcat = ndi.distance_transform_edt(~cat)
    dots = np.zeros(shape, bool)
    dots[5, 5] = True
    with pytest.raises(ValueError):
        cc.relocate(dots, rng.random(shape).astype(np.float32), footprint, dcat, frac=0.05)


def test_cv_band_position_labels():
    assert "inside" in cc.cv_band_position(0.55)
    assert "above" in cc.cv_band_position(0.62)
    assert "below" in cc.cv_band_position(0.40)


def test_surrogate_truth_matches_requested_cell_count():
    footprint, rng = _grid(shape=(30, 30))
    prior = rng.random(footprint.shape).astype(np.float32)
    prior[~footprint] = np.nan
    truth = cc.surrogate_truth(prior, footprint, 25)
    assert truth.sum() == 25
    assert not (truth & ~footprint).any()
