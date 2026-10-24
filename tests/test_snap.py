"""Unit tests for src/gems91/snap.py (no competition data required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import snap  # noqa: E402


def _synthetic(h: int = 60, w: int = 80, seed: int = 3):
    rng = np.random.default_rng(seed)
    footprint = np.ones((h, w), dtype=bool)
    footprint[0, :] = False
    footprint[:, -1] = False
    cat = np.zeros((h, w), dtype=bool)
    cat[30, 10:60] = True
    dcat = ndi.distance_transform_edt(~cat)
    parent = np.zeros((h, w), dtype=bool)
    # dots on a coarse lattice, all off-collar
    for y in range(5, h - 5, 7):
        for x in range(5, w - 5, 9):
            if footprint[y, x] and dcat[y, x] > 3.0:
                parent[y, x] = True
    # two inherited collar dots at 2 < d <= 3 (IR-91-27 quarantine)
    cand = np.argwhere(footprint & (dcat > 2.0) & (dcat <= 3.0))
    for y, x in cand[:2]:
        parent[y, x] = True
    band = rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32)
    band[0, :] = -3.4028235e38
    return footprint, cat, dcat, parent, band


def test_prepare_driver_masks_outside_and_removes_a_regional_ramp():
    h, w = 70, 90
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w]
    plane = (3.0 * yy + 5.0 * xx).astype(np.float32)
    z = snap.prepare_driver(plane, fp, high_pass_sigma_px=8.0, log_compress=False)
    assert np.isneginf(z[~fp]).all()
    assert np.isfinite(z[fp]).all()
    # a pure regional ramp has no local relief: interior response must be tiny
    interior = z[12:-12, 12:-12]
    assert abs(float(np.median(interior))) < 1e-6


def test_prepare_driver_handles_signed_bands_and_nodata_sentinel():
    footprint, _, _, _, band = _synthetic()
    band = band.copy()
    band[5, 5:9] = -3.4028235e38
    z = snap.prepare_driver(band, footprint, signed=True, high_pass_sigma_px=6.0)
    assert np.isfinite(z[footprint]).all()


def test_snap_preserves_count_and_quarantines_the_collar():
    footprint, cat, dcat, parent, band = _synthetic()
    driver = snap.prepare_driver(band, footprint, high_pass_sigma_px=6.0)
    res = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0, min_cat_px=3.0)
    st = res.stats
    assert st["n_dots"] == int(parent.sum())
    assert st["n_collar_quarantined"] == int((parent & (dcat <= 3.0)).sum())
    assert st["collar_after"] == st["collar_before"]
    # collar dots are exactly where they were
    collar = parent & (dcat <= 3.0)
    assert np.array_equal(res.dots & collar, collar)
    # no mass on the catalogue and no target inside the floor
    assert int((res.dots & cat).sum()) == 0
    assert float(dcat[res.dots].min()) >= 3.0
    # every dot that MOVED is strictly outside the collar; inherited dots may sit at exactly 3.0
    assert float(dcat[res.dots & ~parent].min()) > 3.0
    assert st["max_displacement_px"] <= 2.0


def test_snap_is_deterministic():
    footprint, _, dcat, parent, band = _synthetic()
    driver = snap.prepare_driver(band, footprint, high_pass_sigma_px=6.0)
    a = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0, min_cat_px=3.0)
    b = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0, min_cat_px=3.0)
    assert np.array_equal(a.dots, b.dots)


def test_snap_moves_a_dot_onto_a_strictly_stronger_neighbour():
    h, w = 11, 11
    footprint = np.ones((h, w), dtype=bool)
    dcat = np.full((h, w), 99.0)
    parent = np.zeros((h, w), dtype=bool)
    parent[5, 5] = True
    driver = np.zeros((h, w))
    driver[5, 6] = 3.0
    driver[4, 5] = 1.0
    res = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0, min_cat_px=3.0)
    assert res.dots[5, 6] and not res.dots[5, 5]
    assert res.stats["n_moved"] == 1
    assert abs(res.stats["mean_displacement_px"] - 1.0) < 1e-9


def test_flat_driver_is_a_no_op_and_min_gain_blocks_small_improvements():
    h, w = 11, 11
    footprint = np.ones((h, w), dtype=bool)
    dcat = np.full((h, w), 99.0)
    parent = np.zeros((h, w), dtype=bool)
    parent[5, 5] = True
    flat = np.zeros((h, w))
    res = snap.snap_dots(parent, footprint, dcat, flat, radius=2.0, min_cat_px=3.0)
    assert res.stats["n_moved"] == 0
    assert np.array_equal(res.dots, parent)

    weak = np.zeros((h, w))
    weak[5, 6] = 0.4
    res = snap.snap_dots(parent, footprint, dcat, weak, radius=2.0, min_cat_px=3.0, min_gain=0.5)
    assert res.stats["n_moved"] == 0

    strong = np.zeros((h, w))
    strong[5, 6] = 0.6
    res = snap.snap_dots(parent, footprint, dcat, strong, radius=2.0, min_cat_px=3.0, min_gain=0.5)
    assert res.stats["n_moved"] == 1 and res.dots[5, 6]


def test_crest_mode_only_moves_onto_a_local_maximum():
    h, w = 13, 13
    footprint = np.ones((h, w), dtype=bool)
    dcat = np.full((h, w), 99.0)
    parent = np.zeros((h, w), dtype=bool)
    parent[6, 5] = True
    driver = np.zeros((h, w))
    driver[6, 5] = 1.0
    driver[6, 6] = 2.0  # stronger, but not a local max: 6,7 is higher
    driver[6, 7] = 3.0  # local max inside radius 2
    driver[5, 7] = 2.5
    driver[7, 7] = 2.5
    res = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0, min_cat_px=3.0, mode="lmax")
    assert res.dots[6, 7] and not res.dots[6, 5]


def test_combine_drivers_is_an_equal_weight_mean_and_masks_outside():
    fp = np.ones((4, 4), dtype=bool)
    fp[0, 0] = False
    a = np.arange(16, dtype=float).reshape(4, 4)
    b = -a
    out = snap.combine_drivers([a, b], fp)
    assert np.isneginf(out[0, 0])
    assert np.allclose(out[fp], 0.0)


def test_targets_never_collide():
    footprint, cat, dcat, parent, band = _synthetic()
    driver = snap.prepare_driver(band, footprint, high_pass_sigma_px=6.0)
    res = snap.snap_dots(parent, footprint, dcat, driver, radius=2.0, min_cat_px=3.0)
    assert int(res.dots.sum()) == int(parent.sum())  # no two dots merged
    assert int((res.dots & cat).sum()) == 0
