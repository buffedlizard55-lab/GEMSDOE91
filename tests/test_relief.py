"""RELIEF operator tests on a synthetic grid (no competition data).

The fixture supplies a smooth field that plays the role of the relief band, a
catalogue, a footprint and a plausible dot set; nothing here is competition data.

    python -m pytest tests/test_relief.py -q
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage
from scipy.spatial import cKDTree

from gems91 import relief
from tools import make_fixture, raster_io


@pytest.fixture(scope="module")
def arrays(tmp_path_factory):
    out = tmp_path_factory.mktemp("fixture_relief")
    paths = {k: Path(v) for k, v in make_fixture.make(out, seed=5, n_dots=900).items()}
    parent = raster_io.read_band(paths["parent_R0"])
    field = raster_io.read_band(paths["prior_kmscale"])
    catalogue = raster_io.read_band(paths["catalogue_mask"]) > 0
    footprint, _ = raster_io.footprint_from_sample(paths["sample_submission"])
    dots = raster_io.dots_from_band(parent)
    support = np.zeros(footprint.shape, bool)
    support[footprint] = True                      # parent's own support, widened
    dot_mask = np.zeros(footprint.shape, bool)
    dot_mask[dots[:, 0], dots[:, 1]] = True
    dist = ndimage.distance_transform_edt(~catalogue)
    tercile, cuts = relief.tercile_index(field, footprint)
    return dict(dots=dot_mask, footprint=footprint, catalogue=catalogue, dist=dist,
                support=support, field=field, tercile=tercile, cuts=cuts)


def _run(arrays, *, donor=(2,), target=(1,), n_move=90, seed=91):
    return relief.relief_shift(
        arrays["dots"], arrays["footprint"], arrays["dist"], arrays["support"],
        arrays["tercile"], donor_terciles=donor, target_terciles=target,
        n_move=n_move, rng=np.random.default_rng(seed))


def test_count_is_invariant_and_catalogue_is_untouched(arrays):
    res = _run(arrays)
    assert res["n_dots"] == res["n_dots_parent"] == int(arrays["dots"].sum())
    assert not (res["dots"] & arrays["catalogue"]).any()
    assert not (res["dots"] & ~arrays["footprint"]).any()
    assert res["min_cat_dist_new_dots_px"] > 3.0
    assert res["min_recipient_to_existing_dot_px"] >= 2.8 - 1e-6


def test_mass_moves_from_the_donor_tercile_into_the_target(arrays):
    res = _run(arrays, donor=(2,), target=(1,))
    before = res["before"]["range_front"]
    after = res["after"]["range_front"]
    assert after < before                       # donors left the range front
    assert res["after"]["piedmont"] > res["before"]["piedmont"]
    assert res["n_moved"] > 0
    # every new dot is in the target tercile
    assert res["recipient_tercile_mix"].get("piedmont", 0) == res["n_moved"]


def test_null_arm_does_not_target_a_tercile(arrays):
    res = _run(arrays, donor=(0, 1, 2), target=None)
    assert res["n_moved"] > 0
    assert res["target_terciles"] is None
    assert set(res["recipient_tercile_mix"].values()) != {0}


def test_deterministic_for_a_fixed_seed_and_different_for_another(arrays):
    a = _run(arrays, seed=91)
    b = _run(arrays, seed=91)
    c = _run(arrays, seed=92)
    assert np.array_equal(a["dots"], b["dots"])
    assert not np.array_equal(a["dots"], c["dots"])
    assert a["n_dots"] == c["n_dots"]


def _nn(dots):
    ys, xs = np.nonzero(dots)
    pts = np.column_stack([ys, xs]).astype(float)
    return pts, cKDTree(pts).query(pts, k=2)[0][:, 1]


def test_spacing_floor_is_not_worsened_by_the_edit(arrays):
    # The synthetic parent is randomly drawn and already contains cells closer
    # than 2.8 px, so the claim is not "the set is 2.8-clean" but "the edit does
    # not create a single new sub-floor pair" -- which is what the rule buys.
    res = _run(arrays, n_move=120)
    pts, nn = _nn(res["dots"])
    ppts, pnn = _nn(arrays["dots"])
    new = res["dots"] & ~arrays["dots"]
    assert int((nn < 2.8 - 1e-6).sum()) <= int((pnn < 2.8 - 1e-6).sum())
    assert int((nn[new[pts[:, 0].astype(int), pts[:, 1].astype(int)]] < 2.8 - 1e-6).sum()) == 0


def test_shortfall_returns_donors_and_preserves_the_count(arrays):
    huge = int(arrays["dots"].sum()) * 10
    res = _run(arrays, n_move=huge)
    assert res["n_dots"] == res["n_dots_parent"]
    assert res["n_moved"] <= res["n_donor_pool"]
    assert res["n_shortfall"] >= 0


def test_terciles_are_equal_count_and_labelled(arrays):
    counts = [int((arrays["tercile"] == t).sum()) for t in range(3)]
    assert max(counts) - min(counts) <= 2          # equal-count cut
    assert relief.tercile_index(arrays["field"], arrays["footprint"])[1] == arrays["cuts"]
