import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_run_card_is_fail_closed_and_schema_complete():
    card = json.loads((ROOT / "docs/run-card-3a4cca78-20261028.json").read_text())
    assert card["verdict"] == "negative"
    assert card["experiments_run"] == 0
    assert card["weekly_submission_slots_used"] == 0
    assert card["ok_to_download_new_candidate"] is False
    assert card["ok_to_submit"] is False
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["dti"] is None
    assert card["estimated_leaderboard_score"] is None
    assert card["organizer_confirmed_score"] is None
    assert card["user_reported_benchmark"]["label"] == "USER-REPORTED"
    assert card["raster_sha256"] is None
    assert card["validator_output"]["crs_shape_transform_match"] is None


def test_current_readme_and_pages_front_door_link_active_review():
    readme = (ROOT / "README.md").read_text()
    page = (ROOT / "docs/index.html").read_text()
    review = ROOT / "docs/review-3a4cca78-20261028.md"
    card = ROOT / "docs/run-card-3a4cca78-20261028.json"

    assert review.is_file() and card.is_file()
    assert "NO NEW TIFF" in readme and "OK TO SUBMIT: NO" in readme
    assert "full standing project brief" in readme
    assert "NO NEW TIFF" in page and "OK TO SUBMIT: NO" in page
    assert "ACTIVE-CHECKOUT-3A4CCA78-BEGIN" in page
    assert 'href="review-3a4cca78-20261028.md"' in page
    assert 'href="run-card-3a4cca78-20261028.json"' in page


def test_nine_requested_sites_are_covered_and_scores_are_qualified():
    review = (ROOT / "docs/review-3a4cca78-20261028.md").read_text()
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert f"[{site}]" in review
    assert "USER-REPORTED" in review
    assert "ORGANIZER-CONFIRMED scores in this review: none" in review
    assert "No experiment was started" in review
    assert "USGS 3DEP products and services" in review
