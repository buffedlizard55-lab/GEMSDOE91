"""S28 candidate gates: the file we are prepared to submit must stay honest.

These tests are the automated stand-in for a human inspector: they re-read the
candidate bytes, re-run the shared validator, re-measure overlap against the nine
focus-site leaders and every local prior raster, and assert that the published
claims match the machine artefacts exactly.  Nothing here is a leaderboard
score; a score requires an organizer receipt.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from scipy.spatial import cKDTree

from vendor.gems57.grid import HEIGHT, WIDTH, load_grid
from vendor.gems57.validate import assert_submittable, validate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "s28"
STOP = 0.70


@pytest.fixture(scope="module")
def cand():
    return json.loads((OUT / "candidate.json").read_text())


@pytest.fixture(scope="module")
def card():
    return json.loads((OUT / "run-card.json").read_text())


@pytest.fixture(scope="module")
def grid():
    return load_grid(ROOT / "data" / "official")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_candidate_bytes_match_the_registered_hash(cand):
    tif = ROOT / cand["tif"]
    assert tif.is_file(), "the submitted GeoTIFF is missing from docs/downloads"
    assert _sha(tif) == cand["sha256"]
    assert tif.stat().st_size == cand["bytes"]
    with zipfile.ZipFile(ROOT / cand["zip"]) as z:
        names = z.namelist()
    assert names == [tif.name], "the ZIP must contain exactly the one GeoTIFF"


def test_candidate_passes_the_shared_format_validator(cand, grid):
    receipt = validate(ROOT / cand["tif"], footprint=grid.footprint, catalogue=grid.catalogue)
    assert_submittable(receipt)
    assert receipt["all_checks_passed"] is True
    assert receipt["meta"]["shape"] == [HEIGHT, WIDTH]
    assert receipt["meta"]["dtype"] == "float32"
    assert receipt["emitted_positive_pixels"] == cand["geometry"]["n_dots"]
    assert receipt["on_catalogue_positive_pixels"] == 0


def test_values_are_finite_and_inside_zero_one(cand):
    with rasterio.open(ROOT / cand["tif"]) as ds:
        a = ds.read(1)
    assert a.shape == (HEIGHT, WIDTH)
    assert np.isfinite(a).all()
    assert a.min() >= 0.0 and a.max() <= 1.0
    assert set(np.unique(a)).issubset({0.0, 1.0})


def test_emission_geometry_stays_inside_the_leaderboard_envelope(cand, grid):
    with rasterio.open(ROOT / cand["tif"]) as ds:
        a = ds.read(1)
    yy, xx = np.nonzero(a > 0)
    assert yy.size == cand["geometry"]["n_dots"]
    from scipy import ndimage as ndi

    d_cat = ndi.distance_transform_edt(~grid.catalogue)
    d = d_cat[yy, xx]
    assert d.min() > 3.0, "no dot may sit inside the 300 m catalogue collar"
    assert 34000 <= yy.size <= 44000
    nn = cKDTree(np.column_stack([yy, xx]).astype(np.float32)).query(
        np.column_stack([yy, xx]).astype(np.float32), k=2)[0][:, 1]
    assert nn.min() >= 2.8, "dots must not collapse onto each other"
    assert 2.8 <= float(np.median(nn)) <= 4.5


def test_candidate_is_unique_against_the_nine_focus_sites(cand):
    rows = json.loads((OUT / "candidate-vs-nine.json").read_text())
    assert len(rows) == 9
    worst = max(r["mine_within_3px"] for r in rows)
    assert worst < STOP, f"{worst:.4f} of our dots sit within 3 px of a focus-site leader"


def test_candidate_is_unique_against_every_local_prior(cand):
    uniq = cand["uniqueness"]
    assert uniq["worst"]["mine_within_3px"] < STOP
    assert uniq["n_priors_compared"] >= 70


def test_run_card_is_complete_and_never_calls_a_projection_a_score(card):
    assert card["verdict"] in {"promote", "negative"}
    for key in ("hypothesis", "mechanism", "non_fault_process_that_could_mimic_it",
                "holdout", "correlation_overlap_vs_registry", "raster_sha256",
                "validator", "submission"):
        assert card[key], key
    assert card["holdout"]["dti"] is not None
    assert card["holdout"]["withheld_positives"] > 0
    assert "not a leaderboard score" in card["what_this_is_not"].lower() or \
challenge_not_a_score(card)
    assert card["weekly_slots_spent"] == 0
    assert len(card["submission"]["note"]) <= 140
    assert len(card["submission"]["name"]) <= 140
    assert card["validator"]["all_checks_passed"] is True


def challenge_not_a_score(card):
    return "projection" in json.dumps(card).lower()


def test_run_card_numbers_match_the_holdout_and_candidate_artefacts(card):
    hold = json.loads((OUT / "holdout.json").read_text())
    cand = json.loads((OUT / "candidate.json").read_text())
    assert card["holdout"]["dti"] == pytest.approx(hold["arms"][hold["best_arm"]]["dti"], abs=1e-6)
    assert card["holdout"]["withheld_positives"] == hold["arms"][hold["best_arm"]]["n_truth"]
    assert card["raster_sha256"] == cand["sha256"]
    assert card["holdout"]["control_same_geometry"]["physics_baseline"] == pytest.approx(
        hold["arms"]["E1_physics_baseline"]["dti"], abs=1e-6)
    assert card["holdout"]["leakage_canary"]["max_single_layer_auc"] < 0.90


def test_executive_summary_links_the_downloadable_file(card):
    html = (OUT / "executive-summary.html").read_text(encoding="utf-8")
    assert f"downloads/{Path(card['submission']['tif']).name}" in html
    assert card["raster_sha256"] in html
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28",
                 "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in html
    assert "MODEL PROJECTION" in html
    assert "not a score" in html.lower()


def test_nine_site_forensics_used_the_pinned_bytes():
    snap = json.loads((ROOT / "docs/review-20261030/nine-site-snapshot.json").read_text())
    forensics = json.loads((OUT / "nine-site-forensics.json").read_text())
    pinned = {s["site"]: s["sha256"] for s in snap["sites"]}
    for row in forensics["sites"]:
        assert row["sha256"] == pinned[row["site"]], row["site"]
        assert row["positive_pixels"] > 0
        assert row["dcat"]["median_px"] > 0


def test_artifact_policy_registers_the_candidate(cand):
    policy = json.loads((ROOT / "registry/artifact_policy.json").read_text())
    rows = {r["path"]: r for r in policy["files"]}
    assert rows[cand["tif"]]["sha256"] == cand["sha256"]
    assert rows[cand["tif"]]["status"] == "selector_approved"
    assert rows[cand["zip"]]["status"] == "selector_approved"
