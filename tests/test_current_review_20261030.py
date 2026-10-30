"""Regression checks for the active fail-closed 2026-10-30 repository review."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts import render_review_20261030
from scripts.render_olc91_portal import current_review_20261030_callout

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/review-20261030"


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, dict[str, str | None]]] = []
        self.table_row_count = 0
        self.in_row = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.links.append((str(attrs["href"]), attrs))
        if tag == "tr":
            self.table_row_count += 1
            self.in_row = True

    def handle_endtag(self, tag):
        if tag == "tr":
            self.in_row = False


def test_run_card_is_a_negative_result_with_unmeasured_fields_null():
    card = json.loads((REVIEW / "run-card.json").read_text())
    assert card["branch"] == "arena/828b6720-gemsdoe91"
    assert card["verdict"] == "negative"
    assert card["candidate_generated"] is False
    assert card["ok_to_download"] is False and card["ok_to_submit"] is False
    assert card["assigned_lane"] is None and card["assignment_authenticated"] is False
    assert card["experiment_budget"]["experiments_run"] == 0
    assert card["experiment_budget"]["weekly_submission_slots_used"] == 0
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["value"] is None
    assert card["holdout"]["ci95"] is None
    assert card["holdout"]["withheld_positive_count"] is None
    assert card["holdout"]["evaluator_version"] is None
    assert card["registry_correlation_overlap"]["preplacement_surface_abs_spearman_max"] is None
    assert card["registry_correlation_overlap"]["final_dot_overlap_within_3px_max"] is None
    assert card["raster_sha256"] is None
    assert card["validator_output"]["no_nan_inside_footprint"] is None
    assert card["validator_output"]["values_in_0_1"] is None
    assert card["validator_output"]["crs_shape_transform_match"] is None
    assert card["submission_name"] is None and card["submission_note"] is None
    assert card["estimated_leaderboard_score"] is None
    assert card["organizer_confirmed_score"] is None


def test_preflight_and_data_audit_fail_closed_without_restoring_data():
    preflight = json.loads((REVIEW / "experiment-preflight.json").read_text())
    data = json.loads((REVIEW / "data-availability.json").read_text())
    assert preflight["status"] == "BLOCKED"
    assert preflight["candidate_generated"] is False and preflight["ok_to_submit"] is False
    assert data["required_pinned_input_count"] == 15
    assert len(data["missing_input_ids"]) == 15
    assert data["mismatched_input_ids"] == []
    assert data["exit_status"] == 1
    assert "no download attempted" in data["checker"] or "no download was attempted" in data["interpretation"]
    mirror = data["mirror_route_audit"]
    assert mirror["default_restore_path_uses_mirror_routes"] is True
    assert mirror["rights_authorization_status"] == "UNVERIFIED"
    assert mirror["mirror_fetch_attempted_this_review"] is False


def test_summary_contains_nine_user_reported_rows_and_no_download_controls():
    output = render_review_20261030.render()
    assert output == REVIEW / "executive-summary.html"
    html = output.read_text()
    parser = PageLinks()
    parser.feed(html)
    assert html.count("USER-REPORTED") >= 10
    assert "OK TO DOWNLOAD: NO new candidate" in html
    assert "OK TO SUBMIT: NO" in html
    assert "Not estimable" in html
    assert "PUBLIC-LEADERBOARD SNAPSHOT" in html
    assert "0.4544" in html and "0.2778" in html
    assert "do not submit" in html.lower()
    assert "HOLDOUT-DTI" in html
    assert "NOT RUN" in html
    assert "GEMSDOE28 claim distinction" in html
    assert "0.2710" in html and "0.2708" in html
    assert "70 historical research TIFFs" in html
    assert "did not fetch them" in html
    # The page names historical source commits but contains no direct download CTA.
    assert not any("download" in attrs for _, attrs in parser.links)
    sites = [f"GEMSDOE{n}" for n in (24, 25, 27, 28, 30, 31, 32, 33, 36)]
    assert all(site in html for site in sites)
    assert html.count("<tbody>") == 2


def test_summary_local_links_resolve_and_external_sources_are_official():
    page_path = REVIEW / "executive-summary.html"
    parser = PageLinks()
    parser.feed(page_path.read_text())
    for href, _ in parser.links:
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        target = (page_path.parent / unquote(parsed.path)).resolve()
        assert target.is_file(), f"broken local link: {href}"
        assert target.is_relative_to(ROOT)
    sources = json.loads((REVIEW / "source-observations.json").read_text())
    assert sources["public_leaderboard"]["status"] == "FETCHED"
    assert sources["public_leaderboard"]["evidence_class"].startswith("OFFICIAL PUBLIC-LEADERBOARD")
    assert sources["drivendata_data_page"]["status"] == "LOGIN_REQUIRED"
    assert sources["competition_input_mirror_audit"]["rights_authorization_status"] == "UNVERIFIED"
    assert sources["usgs_sgmc"]["status"].startswith("METADATA_AND_DOWNLOAD_LINK_FETCHED")
    assert sources["usgs_comcat"]["status"].startswith("REGIONAL_QUERY_RETURNED_RECORDS")
    assert sources["usgs_3dep"]["status"].endswith("AOI_TILES_NOT_VERIFIED")
    assert sources["usgs_landsat_surface_temperature"]["status"].endswith("SCENES_NOT_VERIFIED")


def test_portal_callout_is_current_and_fails_closed():
    callout = current_review_20261030_callout(ROOT)
    assert "CURRENT REVIEW · 2026-10-30" in callout
    assert "OK TO DOWNLOAD: NO NEW CANDIDATE" in callout
    assert "OK TO SUBMIT: NO" in callout
    assert "15/15 pinned inputs missing" in callout
    assert "Rights/provenance for the configured GitHub mirror routes are unresolved" in callout
    assert "review-20261030/executive-summary.html" in callout
    assert "0.4544" not in callout


def test_public_entry_points_show_20261030_review_and_archive_older_banner():
    root = (ROOT / "index.html").read_text()
    index = (ROOT / "docs/index.html").read_text()
    guide = (ROOT / "docs/executive-summary.html").read_text()
    pointer = json.loads((ROOT / "docs/current-run.json").read_text())
    assert "docs/review-20261030/executive-summary.html" in root
    for page in (index, guide):
        assert "CURRENT REVIEW · 2026-10-30" in page
        assert "NO NEW TIFF" in page and "OK TO SUBMIT: NO" in page
        assert "PRIOR REVIEW · 2026-10-29" in page
    assert pointer["run_card"] == "run-card-S22-OMTJ.json"
    assert pointer["ok_to_submit"] is False


def test_readme_preserves_standing_prompt_and_current_branch_status():
    readme = (ROOT / "README.md").read_text()
    assert readme.startswith("# GEMSDOE91 — Current review 2026-10-30")
    assert "arena/828b6720-gemsdoe91" in readme
    assert "2026-10-30 current-session addendum" in readme
    assert "## Appendix Z — the standing prompt" in readme
    assert "eligible individuals/teams/entities" in readme
    assert "AI agent cannot be the entrant" in readme
    assert "Archived 2026-10-29 S27 status block" in readme
    assert "GEMSDOE28 score labels" in readme
    assert "0.2710" in readme and "0.2708" in readme
    assert "Do not run the mirror-backed restore" in readme
    assert "not organizer validation, uniqueness, rights clearance" in readme


def test_other_branch_same_day_audit_is_archived_and_not_mislabelled():
    archive = (REVIEW / "REVIEW.md").read_text()
    card = json.loads((REVIEW / "run-card-arena-29d7bb05.json").read_text())
    assert archive.startswith("# Archived same-day repo review")
    assert "not the active branch's current decision" in archive
    assert "not an action to submit" in archive
    assert "PUBLIC-LEADERBOARD SNAPSHOT" in archive
    assert "ORGANIZER-CONFIRMED** (DrivenData leaderboard" not in archive
    assert card["organizer_confirmed_scores"] is None
    assert card["public_leaderboard_snapshot"]["evidence_class"].startswith("PUBLIC-LEADERBOARD SNAPSHOT")


def test_limitations_and_irregularities_lead_with_current_blockers():
    limitations = (ROOT / "LIMITATIONS_AND_NEXT_STEPS.md").read_text()
    irregularities = (ROOT / "IRREGULARITIES.md").read_text()
    assert limitations.startswith("## Active limitations and next steps — 30 October 2026")
    assert "15/15 pinned inputs missing" in limitations
    assert "do not rely on the prior mirrored-sample capacity bound" in limitations
    assert "Do not run it for restoration until this is cleared" in limitations
    assert irregularities.startswith("## Irregularities — active 2026-10-30 review")
    for code in ("IR-20261030-01", "IR-20261030-02", "IR-20261030-03",
                 "IR-20261030-04", "IR-20261030-05", "IR-20261030-06", "IR-20261030-07",
                 "IR-20261030-08", "IR-20261030-09"):
        assert code in irregularities
