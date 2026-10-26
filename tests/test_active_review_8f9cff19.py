"""Guard the active checkout review against stale promotion/readiness claims."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def test_active_review_and_readme_fail_closed():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    review = (DOCS / "REVIEW-ACTIVE-8F9CFF19-20261026.md").read_text(encoding="utf-8")
    card = json.loads((DOCS / "run-card-8f9cff19.json").read_text(encoding="utf-8"))

    # The 8f9cff19 review was merged from another lane; it is preserved as
    # evidence, but the session-fixed branch's current status must lead README.
    assert readme.startswith("<!--CURRENT-REVIEW-BEGIN-->")
    assert "#full-project-brief" in readme
    assert "NO NEW TIFF GENERATED" in readme
    assert "0.2778 USER/OWNER-REPORTED" in readme
    assert "REVIEW-ACTIVE-8F9CFF19-20261026.md" in readme
    assert "0.4437" in readme
    assert "portal pointer mismatch" in review.lower()
    submission_guide = (DOCS / "SUBMIT.md").read_text(encoding="utf-8")
    assert "This checkout has no new TIFF that is approved to submit" in submission_guide
    assert "How to submit only after explicit approval" in submission_guide
    assert card["branch"] == "arena/8f9cff19-gemsdoe91"
    assert card["verdict"] == "negative"
    assert card["experiments_run"] == 0
    assert card["weekly_submission_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert card["holdout_dti"]["value"] is None
    assert card["raster_sha256"] is None
    assert card["submission_name"] is None
    assert card["ok_to_download"] is False
    assert card["ok_to_submit"] is False
    public_board = card["official_public_leaderboard_observation"]
    assert public_board["score"] == 0.4437
    assert public_board["rank"] == 1
    assert "not an organizer submission receipt" in public_board["evidence_class"]


def test_active_review_lists_three_proposals_and_source_links_without_a_score_claim():
    review = (DOCS / "REVIEW-ACTIVE-8F9CFF19-20261026.md").read_text(encoding="utf-8")
    for marker in (
        "Dipping-contact waveform matched-filter bank",
        "Same-age alluvial-fan displacement consistency",
        "Focal-mechanism orientation coherence with geodetic strain",
        "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
        "https://www.usgs.gov/3d-elevation-program/about-3dep-products-services",
        "https://earthquake.usgs.gov/data/comcat/",
        "not a tested winner",
        "No candidate beats the supplied 0.2778",
    ):
        assert marker in review
    assert "MODEL" not in review
    assert "projection" in review.lower()


def test_preflight_snapshot_matches_missing_required_inputs():
    preflight = json.loads((ROOT / "registry/preflight.json").read_text(encoding="utf-8"))
    assert preflight["verdict"] == "BUILD BLOCKED"
    assert preflight["ready_axes"] == []
    assert set(preflight["missing"]) == {"sample_submission", "parent_r0_nan"}
    assert all(not row["ready"] for row in preflight["axis_readiness"].values())
