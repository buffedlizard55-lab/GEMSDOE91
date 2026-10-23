"""CONCENTRATION builder tests, and an end-to-end build -> certify proof.

The point of this file is that the merged repository can now show its gates and its
builder agreeing on a real raster. Everything runs on the synthetic fixture
(`tools/make_fixture.py`): no competition data is read, stored or approximated.

    python -m pytest tests -q
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage

from gems91.gates import validate as certify
from tools import make_fixture, pins, raster_io, run_concentration, stor
from tools.run_concentration import block_cv, block_prior, build_concentration


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
    _, stats = build_concentration(parent, prior, footprint, catalogue, frac=0.12, block_px=20)
    assert 1.0 <= stats["pct_dots_moved"] <= 50.0
    assert stats["pct_dots_moved"] == pytest.approx(12.0, abs=1.5)


def test_mass_moves_toward_high_prior_blocks(arrays):
    parent, prior, footprint, catalogue = arrays
    _, stats = build_concentration(parent, prior, footprint, catalogue, frac=0.15, block_px=20)
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


@pytest.mark.parametrize("bad", [0.05, 0.35])
def test_fraction_outside_brief_range_is_refused(arrays, bad):
    parent, prior, footprint, catalogue = arrays
    with pytest.raises(ValueError, match="frac must be within"):
        build_concentration(parent, prior, footprint, catalogue, frac=bad, block_px=20)


def test_non_unit_mass_parent_is_refused(arrays):
    parent, prior, footprint, catalogue = arrays
    bad = np.where(np.isfinite(parent), parent * 0.5, np.nan)
    with pytest.raises(ValueError, match="not unit mass"):
        build_concentration(bad, prior, footprint, catalogue, frac=0.15, block_px=20)


def test_block_cv_math():
    footprint = np.ones((10, 10), bool)
    dots = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=int)
    out = block_cv(dots, footprint, block_px=5)
    assert out["n_blocks_scored"] == 4
    # densities 0.16, 0, 0, 0 -> mean 0.04, std 0.0693, cv = sqrt(3)
    assert out["cv"] == pytest.approx(np.sqrt(3.0), abs=1e-6)


def test_block_prior_ignores_blocks_without_footprint():
    prior = np.ones((10, 10))
    footprint = np.zeros((10, 10), bool)
    footprint[:5, :] = True
    bp = block_prior(prior, footprint, block_px=5)
    assert np.isfinite(bp[0, 0]) and np.isnan(bp[1, 0])


def _argv(fx, out_dir, ledger, *extra):
    return [
        "--parent", str(fx["parent_R0"]), "--sample", str(fx["sample_submission"]),
        "--catalogue", str(fx["catalogue_mask"]), "--prior", str(fx["prior_kmscale"]),
        "--parent-tag", "SYNTH", "--frac", "0.15", "--block-px", "20",
        "--out-dir", str(out_dir), "--ledger", str(ledger), "--allow-unpinned", *extra,
    ]


def _empty_ledger(path: Path) -> Path:
    """A ledger with headers only: this is the state the dedupe gate needs to run."""
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        csv.DictWriter(fh, fieldnames=stor.COLUMNS).writeheader()
    return path


def test_end_to_end_build_then_certify(fx, tmp_path):
    """Build, then run the repository's own certification gates on the result."""
    out = tmp_path / "releases"
    ledger = _empty_ledger(tmp_path / "ledger.csv")
    assert run_concentration.main(_argv(fx, out, ledger)) == 0
    tifs = sorted(out.glob("*.tif"))
    assert len(tifs) == 2  # primary + zeros twin
    primary = [p for p in tifs if not p.stem.endswith("-zeros")][0]

    rep = certify(primary, sample_submission=fx["sample_submission"],
                  catalogue=fx["catalogue_mask"], ledger_csv=ledger, axis="CONCENTRATION")
    assert rep.verdict == "CERTIFIED", rep.to_dict()
    assert rep.gates["zero_catalogue_mass"] == "PASS"
    assert rep.notes["dots_le_3px"] == 0
    assert rep.gates["reread_from_disk"] == "PASS"
    # the canonical name embeds the file's own hash
    assert primary.stem.endswith(rep.sha256[:8])


def test_unpinned_inputs_are_refused(fx, tmp_path):
    """Without --allow-unpinned the builder must refuse on the real manifest."""
    argv = [a for a in _argv(fx, tmp_path / "blocked", tmp_path / "l.csv") if a != "--allow-unpinned"]
    assert run_concentration.main(argv) == 2
    assert not (tmp_path / "blocked").exists()


def test_refuses_without_inputs(tmp_path):
    rc = run_concentration.main([
        "--parent", str(tmp_path / "nope.tif"), "--sample", str(tmp_path / "nope.tif"),
        "--catalogue", str(tmp_path / "nope.tif"), "--prior", str(tmp_path / "nope.tif"),
        "--allow-unpinned",
    ])
    assert rc == 2
    assert not (tmp_path / "releases").exists()


def test_register_locks_axis_value_pairs(fx, tmp_path):
    """A second build with the same (parent, axis, value) must be refused."""
    ledger = tmp_path / "submissions.csv"
    assert run_concentration.main(_argv(fx, tmp_path / "rel", ledger, "--register")) == 0
    rows = stor.read_ledger(ledger)
    assert len(rows) == 1
    row = rows[0]
    assert row["status"] == "BUILT" and row["axis"] == "CONCENTRATION"
    # ledger schema is the merged repo's, both twin hashes recorded
    assert set(row) == set(stor.COLUMNS)
    assert len(row["sha256"]) == 64 and len(row["sha256_zeros"]) == 64
    assert "EXTERNAL prior" in row["ranking_basis"]
    assert row["source"].startswith("BUILT:")

    argv2 = [a for a in _argv(fx, tmp_path / "rel2", ledger, "--register") if a != "--register"]
    argv2 += ["--seed", "5", "--register"]
    with pytest.raises(SystemExit, match="already built"):
        run_concentration.main(argv2)


def test_ledger_row_survives_the_repo_invariants(fx, tmp_path):
    """The appended row must satisfy the invariants main's test_ledger.py enforces."""
    ledger = tmp_path / "submissions.csv"
    assert run_concentration.main(_argv(fx, tmp_path / "rel", ledger, "--register")) == 0
    rows = stor.read_ledger(ledger)
    import csv

    with open(ledger, newline="", encoding="utf-8") as fh:
        assert list(csv.DictReader(fh).fieldnames) == stor.COLUMNS
    for r in rows:
        assert r["axis"] in {"MASS", "CONCENTRATION", "SNAP", "PRUNE", "RELIEF", "SPACING", "TRACKB"}
        assert "MODEL" in r["predicted_change"]
        assert len(r["sha256"]) == 64
        assert r["receipt_score"] == ""


def test_pinned_hashes_come_from_the_real_manifest():
    manifest = pins.load(pins.MANIFEST)
    by_hash = pins.pinned_hashes(manifest)
    assert len(by_hash) == len(manifest["files"]) == 15
    assert all(len(h) == 64 for h in by_hash)


def test_axis_input_matrix_points_at_pinned_ids():
    manifest = pins.load(pins.MANIFEST)
    ids = {f["id"] for f in manifest["files"]}
    for axis, needed in pins.AXIS_INPUTS.items():
        assert set(needed) <= ids, f"{axis} needs an id that is not pinned"
        assert "parent_r0_nan" in needed


def test_current_checkout_cannot_build_concentration():
    """Both the pins and the preflight verdict must agree: blocked, no build."""
    clear, reasons = pins.check_axis("CONCENTRATION")
    assert not clear
    assert any("training_features" in r for r in reasons)
