"""Prevent the historical DZ-EDGE artifact from being mislabelled submit-ready."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_historical_dzedge_card_is_research_only():
    card = json.loads((ROOT / "docs/run-card-gems91-dzedge-v2-20261025.json").read_text())
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert card["historical_artifact"] is True
    assert card["freshly_verified_in_this_checkout"] is True
    assert card["fresh_byte_validation"]["all_cells_finite"] is True
    assert card["fresh_byte_validation"]["min"] >= 0.0
    assert card["fresh_byte_validation"]["max"] <= 1.0
    assert card["holdout_dti"]["score"] == 0.0
    assert "HOLDOUT-DTI" in card["holdout_dti"]["label"]
    assert card["lane_status"]["assigned"] is False
    assert card["selector_approval"] is False
    assert card["comparable_holdout_best"] is None
    assert len(card["submission_note"]) == 132
    assert len(card["submission_note"]) <= 140


def test_dzedge_page_says_no_submission_and_warns_before_download():
    home = (ROOT / "docs/archive-review-6feb36e3.html").read_text()
    assert "Current checkout review · 2026-10-25 · arena/6feb36e3-gemsdoe91" in home
    assert "OK TO DOWNLOAD: YES — research only · OK TO SUBMIT: NO" in home
    page = (ROOT / "docs/dzedge-executive-summary.html").read_text()
    assert "OK TO DOWNLOAD: YES · RESEARCH ONLY" in page
    assert "OK TO SUBMIT: NO" in page
    assert "Do not submit this DZ-EDGE file" in page
    assert 'data-submission-ready="false"' in page
    assert "unique lane" not in page
    assert "Submit: YES" not in page


def test_dzedge_builder_cannot_promote_from_format_and_parent_check_alone():
    source = (ROOT / "scripts/build_dzedge.py").read_text()
    assert "Retired DZ-EDGE builder" in source
    assert "complete two-phase registry gates" in source
    assert "return 2" in source
    assert "no artifact written" in source
