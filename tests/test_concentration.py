"""Tests for the CONCENTRATION axis builder (synthetic fixture only).

    python -m pytest tests -q
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

from tools import make_fixture, raster_io, run_concentration
from tools.run_concentration import build_concentration, block_cv, block_prior
from tools.validate_submission import validate


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    out = tmp_path_factory.mktemp("fixture_c")
    return {k: Path(v) for k, v in make_fixture.make(out, seed=11, n_dots=800).items()}


@pytest.fixture
def arrays(fx):
    parent = raster_io.read_band(fx["parent_R0"])
    prior = raster_io.read_band(fx["prior_kmscale"])
    catalogue = raster_io.read_band(fx["catalogue_mask"]) > 0
    footprint, _ = raster_io.footprint_from_sample(fx["sample_submission"])
    return parent, prior, footprint, catalogue


def test_count_is_preserved_and_nothing_lands_on_the_catalogue(arrays):
    parent, prior, footprint, catalogue = arrays
    band, stats = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20)
    assert stats["count_preserved"]
    assert stats["n_dots_candidate"] == stats["n_dots_parent"]
    assert np.nansum(np.abs(band[catalogue])) == 0.0
    assert np.nansum(np.abs(band[~footprint])) == 0.0
    dist = ndimage.distance_transform_edt(~catalogue)
    dots = raster_io.dots_from_band(band)
    assert dist[dots[:, 0], dots[:, 1]].min() > 3.0


def test_changed_fraction_is_in_the_brief_range(arrays):
    parent, prior, footprint, catalogue = arrays
    band, stats = build_concentration(parent, prior, footprint, catalogue, frac=0.12, block_px=20)
    assert 1.0 <= stats["pct_dots_moved"] <= 50.0
    assert stats["pct_dots_moved"] == pytest.approx(12.0, abs=1.5)


def test_mass_moves_toward_high_prior_blocks(arrays):
    parent, prior, footprint, catalogue = arrays
    band, stats = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20)
    assert stats["acceptor_block_prior_mean"] > stats["donor_block_prior_mean"]
    assert stats["n_dots_moved"] > 0


def test_cv_is_reported_before_and_after(arrays):
    parent, prior, footprint, catalogue = arrays
    _, stats = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20)
    assert np.isfinite(stats["cv_before"]) and np.isfinite(stats["cv_after"])
    assert stats["cv_detail_before"]["block_px"] == 20
    assert stats["cv_detail_before"]["block_km"] == pytest.approx(2.0)


def test_same_seed_is_reproducible(arrays):
    parent, prior, footprint, catalogue = arrays
    a, sa = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20, seed=7)
    b, sb = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20, seed=7)
    assert np.allclose(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9))
    assert sa["n_dots_moved"] == sb["n_dots_moved"]


def test_different_seed_changes_the_result(arrays):
    parent, prior, footprint, catalogue = arrays
    a, _ = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20, seed=1)
    b, _ = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20, seed=2)
    assert not np.allclose(np.nan_to_num(a, nan=-9), np.nan_to_num(b, nan=-9))


def test_fraction_outside_brief_range_is_refused(arrays):
    parent, prior, footprint, catalogue = arrays
    for bad in (0.05, 0.35):
        with pytest.raises(ValueError, match="frac must be within"):
            build_concentration(parent, prior, footprint, catalogue, frac=bad, block_px=20)


def test_non_unit_mass_parent_is_refused(arrays):
    parent, prior, footprint, catalogue = arrays
    bad = np.where(np.isfinite(parent), parent * 0.5, np.nan)
    with pytest.raises(ValueError, match="not unit mass"):
        build_concentration(bad, prior, footprint, catalogue, frac=0.15, block_px=20)


def test_block_cv_math():
    footprint = np.ones((10, 10), bool)
    dots = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=int)  # 4 in one block
    out = block_cv(dots, footprint, block_px=5)
    assert out["n_blocks_scored"] == 4
    # densities: 0.16, 0, 0, 0 -> mean 0.04, std 0.0693, cv = sqrt(3) ~ 1.732
    assert out["cv"] == pytest.approx(np.sqrt(3.0), abs=1e-6)


def test_block_prior_ignores_blocks_without_footprint():
    prior = np.ones((10, 10))
    footprint = np.zeros((10, 10), bool)
    footprint[:5, :] = True
    bp = block_prior(prior, footprint, block_px=5)
    assert np.isfinite(bp[0, 0]) and np.isnan(bp[1, 0])


def test_end_to_end_cli_passes_all_gates(fx, tmp_path, monkeypatch):
    out = tmp_path / "releases"
    ledger = tmp_path / "ledger.csv"
    argv = [
        "--parent", str(fx["parent_R0"]), "--sample", str(fx["sample_submission"]),
        "--catalogue", str(fx["catalogue_mask"]), "--prior", str(fx["prior_kmscale"]),
        "--parent-tag", "SYNTH", "--frac", "0.15", "--block-px", "20",
        "--out-dir", str(out), "--allow-unpinned",
    ]
    assert run_concentration.main(argv) == 0
    tifs = sorted(p for p in out.glob("*.tif"))
    assert len(tifs) == 2  # primary + zeros twin
    primary = [p for p in tifs if not p.stem.endswith("-zeros")][0]
    rep = validate(
        candidate=primary, sample=fx["sample_submission"], catalogue=fx["catalogue_mask"],
        footprint_path=fx["footprint_mask"], ledger=ledger, parent=fx["parent_R0"],
        stacklevel_output=False,
    )
    assert rep["pass"], rep["failed_gates"]
    # the canonical name embeds the file's own hash
    assert primary.stem.endswith(rep["sha8"])


def test_unpinned_inputs_are_refused(fx, tmp_path):
    """The real manifest pins nothing, so the builder must refuse before writing."""
    rc = run_concentration.main([
        "--parent", str(fx["parent_R0"]), "--sample", str(fx["sample_submission"]),
        "--catalogue", str(fx["catalogue_mask"]), "--prior", str(fx["prior_kmscale"]),
        "--parent-tag", "SYNTH", "--frac", "0.15", "--block-px", "20",
        "--out-dir", str(tmp_path / "blocked"),
    ])
    assert rc == 2
    assert not (tmp_path / "blocked").exists()


def test_refuses_without_inputs(tmp_path):
    rc = run_concentration.main([
        "--parent", str(tmp_path / "nope.tif"), "--sample", str(tmp_path / "nope.tif"),
        "--catalogue", str(tmp_path / "nope.tif"), "--prior", str(tmp_path / "nope.tif"),
    ])
    assert rc == 2
    assert not (tmp_path / "releases").exists()


def test_register_locks_axis_value_pairs(fx, tmp_path):
    """A second build with the same (parent, axis, value) must be refused."""
    from tools import stor

    argv = [
        "--parent", str(fx["parent_R0"]), "--sample", str(fx["sample_submission"]),
        "--catalogue", str(fx["catalogue_mask"]), "--prior", str(fx["prior_kmscale"]),
        "--parent-tag", "SYNTH", "--frac", "0.15", "--block-px", "20",
        "--out-dir", str(tmp_path / "rel"), "--register", "--allow-unpinned",
        "--ledger", str(tmp_path / "submissions.csv"),
    ]
    assert run_concentration.main(argv) == 0
    rows = stor.read_ledger(tmp_path / "submissions.csv")
    assert len(rows) == 1 and rows[0]["status"] == "BUILT"
    assert rows[0]["axis"] == "CONCENTRATION" and rows[0]["sha8"]

    # second run, same pair but a different seed -> different bytes, same (parent, axis, value)
    argv2 = [a for a in argv if a != "--register"] + ["--seed", "5", "--register"]
    with pytest.raises(SystemExit, match="already built"):
        run_concentration.main(argv2)
