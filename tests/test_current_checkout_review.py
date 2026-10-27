"""Regression checks for current status and immutable prior checkout reviews."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CARD_PATH = DOCS / "run-card-ARENA-52711765-20261027.json"
REVIEW_PATH = DOCS / "REVIEW-ARENA-52711765-20261027.md"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and "href" in values:
            self.hrefs.append(values["href"])

    def handle_data(self, data):
        self.text.append(data)


def test_previous_checkout_review_card_remains_immutable_historical_evidence():
    card = json.loads((DOCS / "run-card-ARENA-5CD5E4F7-20261026.json").read_text())
    assert card["branch"] == "arena/5cd5e4f7-gemsdoe91"
    assert card["verdict"] == "negative"
    assert card["experiments_run"] == 0
    assert card["weekly_submission_slots_used"] == 0
    assert card["assigned_lane"] is None
    assert card["holdout_dti"]["value"] is None
    assert card["holdout_dti"]["evaluator_version"] == "NOT RUN"
    assert card["raster_sha256"] is None
    assert card["submission_name"] is None and card["submission_note"] is None
    assert card["ok_to_download"] is False and card["ok_to_submit"] is False
    assert card["preflight"]["sample_submission_present"] is False
    assert card["preflight"]["registry_witness_present"] is False


def test_previous_checkout_audit_page_keeps_all_local_links_valid():
    page_path = DOCS / "high-score-submissions-review.html"
    page = Links()
    page.feed(page_path.read_text())
    text = " ".join(page.text)
    assert "generated no new TIFF" in text
    assert "OK TO SUBMIT: NO" in text
    assert "0.2778" in text and "UNVERIFIED" in text.upper()
    assert any(href.endswith("run-card-ARENA-5CD5E4F7-20261026.json") for href in page.hrefs)
    for href in page.hrefs:
        url = urlsplit(href)
        if url.scheme or url.netloc:
            continue
        target = (page_path.parent / unquote(url.path)).resolve() if url.path else page_path
        assert target.is_file(), f"broken local link: {href}"
        assert target.is_relative_to(ROOT)


def test_prior_site_summary_and_hypothesis_provenance_remain_explicit():
    review = (DOCS / "REVIEW-SITE-AUDIT-20261026.md").read_text()
    assert "USER/OWNER-REPORTED, UNVERIFIED" in review
    assert "GEMSDOE32" in review and "0.2778" in review
    assert "Ranked hypotheses — proposals, not results" in review
    assert all(f"| **{rank}** |" in review for rank in (1, 2, 3))
    assert "Not viable until those checks/access are completed" in review
    assert "No experiment was launched" in review
    summary = (DOCS / "high-score-submissions-review.html").read_text()
    assert "Prospective score estimate" in summary
    assert "Cross-site uniqueness / download verdict" in summary
    assert summary.count("Not estimable: no new candidate or holdout run.") == 9
    assert "LIKELY DUPLICATE" in summary and "pixel-identical" in summary
    assert "do not upload" in summary.lower()


def test_current_run_card_does_not_claim_unmeasured_candidate_results():
    card = json.loads(CARD_PATH.read_text(encoding="utf-8"))
    assert card["branch"] == "arena/52711765-gemsdoe91"
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is False
    assert card["ok_to_submit"] is False
    assert card["budget"]["experiments_used_this_review"] == 0
    assert card["budget"]["weekly_slots_used"] == 0
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["dti"] is None
    assert card["holdout"]["evaluator_version"] is None
    assert card["holdout"]["withheld_positive_pixels"] is None
    assert card["holdout"]["ci95"] is None
    assert card["registry_correlation_overlap"]["preplacement_surface_rank_correlation"] is None
    assert card["registry_correlation_overlap"]["final_dot_overlap_within_3px"] is None
    assert card["raster_sha256"] is None
    assert card["validator_output"]["no_nan_inside_footprint"] is None
    assert card["validator_output"]["values_in_0_1"] is None
    assert card["validator_output"]["crs_shape_transform_match"] is None
    assert card["submission_name"] is None
    assert card["submission_note"] is None
    assert card["estimated_leaderboard_score"] is None
    assert card["organizer_confirmed_score"] is None


def test_current_review_has_all_nine_sites_and_no_score_forecast():
    review = REVIEW_PATH.read_text(encoding="utf-8")
    assert "no new tiff generated" in review.lower()
    assert "OK TO DOWNLOAD: NO new candidate" in review
    assert "OK TO SUBMIT: NO" in review
    assert "0 / 3" in review
    assert "15/15 missing" in review
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28",
                 "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in review
    assert "Estimated leaderboard score" in review
    assert "Unavailable" in review
    assert "Unique vs other eight?" in review
    assert "no verified receipt-to-raster binding" in review


def test_prior_s18_files_are_registered_as_quarantined_research_artifacts():
    policy = json.loads((ROOT / "registry/artifact_policy.json").read_text(encoding="utf-8"))
    rows = {row["path"]: row for row in policy["files"]}
    for suffix in (".tif", ".zip"):
        path = "docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261026T213155Z-29db2405" + suffix
        assert rows[path]["status"] == "parallel_quarantined"
        assert "research artifact" in rows[path]["reason"]
    audit = json.loads((DOCS / "download-audit.json").read_text(encoding="utf-8"))
    assert audit["audit_completed"] is True
    assert audit["ok_to_submit"] is False
    assert audit["files_checked"] == len(rows)


def test_latest_status_is_in_public_entry_points_and_render_source():
    root = (ROOT / "index.html").read_text(encoding="utf-8")
    site = (DOCS / "index.html").read_text(encoding="utf-8")
    renderer = (ROOT / "scripts/render_olc91_portal.py").read_text(encoding="utf-8")
    # Root redirects to the newer review, while the concurrent prior review
    # remains linked as historical evidence rather than current status.
    assert 'url=docs/index.html' in root
    assert 'NO NEW TIFF' in root and 'OK TO SUBMIT: NO' in root
    assert 'NO NEW TIFF' in site and 'OK TO SUBMIT: NO' in site
    assert 'review-8e8d86f2/REVIEW.md' in site
    assert 'REVIEW-ARENA-52711765-20261027.md' in site
    assert 'render_review_8e8d86f2' in renderer


def test_untried_candidate_rankings_include_confounds_and_data_access_limits():
    review = REVIEW_PATH.read_text(encoding="utf-8")
    for term in (
        "Local cross-band copula break",
        "Ordinal-pattern entropy contrast",
        "Map-unit-conditioned within-unit potential-field residual displacement",
        "Repeat-season Landsat thermal residual",
        "intrusive margin",
        "volcanic-flow",
        "not viable",
        "USGS Landsat Collection 2 Surface Temperature",
    ):
        assert term.lower() in review.lower()
