"""Regression checks for the active no-candidate review and portal overlay."""
import json
from pathlib import Path
import re
from urllib.parse import urlparse

from scripts import render_review_20261030

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVIEW = DOCS / "review-20261030"
EXPECTED = [
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
]


def load(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_active_review_run_card_is_negative_and_contains_no_score_or_candidate():
    card = load("docs/review-20261030/run-card.json")
    assert card["repository_branch"] == "arena/83350cee-gemsdoe91"
    assert card["review_status"] == "BLOCKED"
    assert card["candidate_generated"] is False
    assert card["candidate_path"] is card["candidate_sha256"] is None
    assert card["ok_to_download_new_candidate"] is False
    assert card["ok_to_submit"] is False
    assert card["historical_reference_files"]["ok_to_download_for_research_or_inspection"] is True
    assert card["historical_reference_files"]["ok_to_submit"] is False
    assert card["leaderboard_score_estimate"] is None
    assert card["holdout_dti"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["status"] == "NOT RUN"
    assert all(card["holdout_dti"][k] is None for k in (
        "value", "evaluator_version", "withheld_positive_count", "ci95"))
    assert card["organizer_confirmed"]["evidence_class"] == "ORGANIZER-CONFIRMED"
    assert card["organizer_confirmed"]["value"] is None
    assert card["organizer_confirmed"]["submission_receipt"] is None
    assert card["experiment_plan"]["lane"] is None
    assert card["experiment_plan"]["experiments_run_this_review"] == 0
    assert card["data_preflight"]["pinned_manifest_inputs_missing"] == 15
    assert card["data_preflight"]["official_sample_submission_present"] is False
    assert not list(REVIEW.glob("*.tif"))
    assert not list(REVIEW.glob("*.tiff"))


def test_nine_site_snapshot_has_pinned_files_hashes_and_qualified_claims():
    snapshot = load("docs/review-20261030/nine-site-snapshot.json")
    assert snapshot["site_order"] == EXPECTED
    assert [row["site"] for row in snapshot["sites"]] == EXPECTED
    assert snapshot["no_defensible_leaderboard_estimate"] is True
    assert snapshot["organizer_confirmed_scores_in_snapshot"] == 0
    for row in snapshot["sites"]:
        assert row["repository_owner"] == "buffedlizard55-lab"
        assert row["repository_name"] == row["site"]
        assert row["download_url"].startswith(
            f"https://raw.githubusercontent.com/buffedlizard55-lab/{row['site']}/{row['commit']}/")
        assert row["source_blob_url"].startswith(
            f"https://github.com/buffedlizard55-lab/{row['site']}/blob/{row['commit']}/")
        assert row["byte_verification_status"] == "PASS"
        assert row["byte_verification_utc"] == "2026-10-30"
        assert len(row["sha256"]) == 64
        assert row["reported_value_evidence_class"].startswith("USER-REPORTED")
        assert row["organizer_confirmed_score"] is None
        assert row["unique_within_nine_at_70pct"] is False


def test_current_pages_and_readme_link_the_active_no_candidate_review():
    render_review_20261030.render(ROOT)
    root = (ROOT / "index.html").read_text(encoding="utf-8")
    index = (DOCS / "index.html").read_text(encoding="utf-8")
    current = (DOCS / "current-review.json").read_text(encoding="utf-8")
    guide = (DOCS / "submission-guide.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "url=docs/index.html" in root
    assert "2026-10-30" in root
    assert load("docs/current-review.json")["branch"] == "arena/83350cee-gemsdoe91"
    assert "docs/review-20261030/executive-summary.html" in root
    assert "ACTIVE REVIEW · 2026-10-30" in index
    assert "review-20261030/run-card.json" in index
    assert "candidate_generated\": false" in current
    assert "OK TO SUBMIT: NO" in guide
    assert "There is no new GeoTIFF candidate" in guide
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/" in guide
    assert "ACTIVE BRANCH: `arena/83350cee-gemsdoe91`" in readme
    assert "Maximize P(Win) · Own the Outcome" in readme
    assert "full-project-brief" in readme


def test_executive_table_labels_all_reported_values_and_rejects_score_estimates():
    html = (REVIEW / "executive-summary.html").read_text(encoding="utf-8")
    assert html.count("USER-REPORTED_PUBLIC_DTI") >= len(EXPECTED)
    assert html.count("NONE RECORDED") == len(EXPECTED)
    assert html.count("OK TO DOWNLOAD: YES") == len(EXPECTED)
    assert "OK TO SUBMIT: NO" in html
    assert "research/inspection only" in html
    assert "closest:" in html and "peer-only, max within 3 px" in html
    assert "NOT A VERIFIED SCORE" in html
    assert "No alternative leaderboard score is estimated here" in html
    assert "data-submission-ready=\"false\"" in html
    assert "data-submission-ready=\"true\"" not in html
    for site in EXPECTED:
        assert site in html
    assert "0.2778" in html
    assert "no candidate exists today" in html.lower()
    assert "2026-10-29 audit" in html
    assert "complete-registry clearance" in html


def test_hypotheses_and_official_sources_are_proposals_with_limits():
    hypotheses = (REVIEW / "HYPOTHESES.md").read_text(encoding="utf-8")
    sources = load("docs/review-20261030/sources.json")
    card = load("docs/review-20261030/run-card.json")
    source_ids = {row["id"] for row in sources["sources"]}
    assert {"drivendata-problem", "usgs-geodawn", "usgs-gems-sgmc-2026",
            "usgs-3dep", "usgs-slip-dilation-2026"} <= source_ids
    assert card["experiment_plan"]["lane"] is None
    assert "none is an assigned method lane" in hypotheses.lower()
    assert "not fetched" in hypotheses.lower()
    assert "label leakage" in hypotheses.lower()
    assert "negative controls" in hypotheses.lower() or "negative control" in hypotheses.lower()


def test_internal_links_in_new_review_pages_resolve():
    pages = [
        REVIEW / "executive-summary.html",
        DOCS / "submission-guide.html",
    ]
    for page in pages:
        text = page.read_text(encoding="utf-8")
        hrefs = re.findall(r'href="([^"]+)"', text)
        for href in hrefs:
            parsed = urlparse(href)
            if parsed.scheme or href.startswith("#") or not parsed.path:
                continue
            target = (page.parent / parsed.path).resolve()
            assert target.is_relative_to(ROOT.resolve()), f"path escapes repo: {href}"
            assert target.exists(), f"broken local link in {page.relative_to(ROOT)}: {href}"


def test_review_renderer_is_idempotent():
    paths = [
        ROOT / "index.html",
        DOCS / "index.html",
        DOCS / "executive-summary.html",
        DOCS / "submission-guide.html",
        DOCS / "current-review.json",
        REVIEW / "executive-summary.html",
    ]
    before = {path: path.read_bytes() for path in paths}
    render_review_20261030.render(ROOT)
    assert before == {path: path.read_bytes() for path in paths}
