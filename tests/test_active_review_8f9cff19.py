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

    assert "<!--ACTIVE-8F9CFF19-BEGIN-->" in readme
    assert readme.startswith("# GEMSDOE91 — S22 OMTJ")  # Later measured run owns current status.
    assert "#full-project-brief" in readme
    assert "NO NEW TIFF FROM THIS REVIEW" in readme
    assert "0.2778 USER/OWNER-REPORTED" in readme
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
    assert "Nine-site file / score / uniqueness matrix" in review
    for site, filename in (
        ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan"),
        ("GEMSDOE25", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan"),
        ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan"),
        ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan"),
        ("GEMSDOE30", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca"),
        ("GEMSDOE31", "h27-4-solo-d28-20261004-8acb75e1-nan"),
        ("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros"),
        ("GEMSDOE33", "h33d-analog-tip-stepover-r30-20261004-cb490425926e"),
        ("GEMSDOE36", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros"),
    ):
        assert site in review and filename in review


def test_preflight_snapshot_matches_missing_required_inputs():
    preflight = json.loads((ROOT / "registry/preflight.json").read_text(encoding="utf-8"))
    assert preflight["verdict"] == "BUILD BLOCKED"
    assert preflight["ready_axes"] == []
    assert set(preflight["missing"]) == {"sample_submission", "parent_r0_nan"}
    assert all(not row["ready"] for row in preflight["axis_readiness"].values())
