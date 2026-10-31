"""Regression checks for the 2026-10-26 read-only nine-site audit and portal status."""
from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from scripts import render_review_20261030

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EXPECTED_SITES = (
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
)


class AuditPage(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.text: list[str] = []
        self.states: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if "id" in values:
            self.ids.add(values["id"])
        if tag == "a" and "href" in values:
            self.links.append(values["href"])
        if "data-submission-ready" in values:
            self.states.append(values["data-submission-ready"])

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def parse_page(path: Path) -> AuditPage:
    parser = AuditPage()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


def test_nine_site_register_is_pinned_and_preserves_unverified_score_status():
    data = json.loads((DOCS / "research/nine-site-audit-20261026.json").read_text(encoding="utf-8"))
    assert tuple(row["site"] for row in data["repositories"]) == EXPECTED_SITES
    assert data["current_checkout"]["fresh_experiment_run"] is False
    assert data["current_checkout"]["new_tiff_generated"] is False
    assert data["current_checkout"]["submission_approved"] is False
    assert data["current_checkout"]["organizer_confirmed_score"] is None
    assert data["current_checkout"]["best_file_to_submit"] is None
    assert data["current_checkout"]["reported_best_among_supplied_nine"]["score"] == 0.2778
    assert data["leaderboard_claims"]["user_supplied_values_conflict"] == [0.3195, 0.4413]
    for repo in data["repositories"]:
        assert re.fullmatch(r"[0-9a-f]{40}", repo["commit"])
        assert repo["snapshot_sources"]
        assert all(repo["commit"] in source["url"] for source in repo["snapshot_sources"])
        assert any(marker in repo["strongest_supplied"]["evidence_status"].upper() for marker in ("UNVERIFIED", "NOT ORGANIZER-CONFIRMED"))


def test_no_run_card_is_fail_closed_and_has_no_fabricated_candidate_metrics():
    card = json.loads((DOCS / "run-card-SITE-AUDIT-20261026.json").read_text(encoding="utf-8"))
    assert card["verdict"] == "negative"
    assert card["experiments_run"] == 0
    assert card["weekly_submission_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["value"] is None
    assert card["holdout_dti"]["evaluator_version"] == "NOT RUN"
    assert card["correlation_overlap_vs_registry"]["final_dot_overlap_within_3px"] is None
    assert card["raster_sha256"] is None
    assert card["validator_output"]["values_in_0_1"] is None
    assert card["submission_name"] is None and card["submission_note"] is None
    assert card["ok_to_download"] is False and card["ok_to_submit"] is False


def test_executive_audit_links_resolve_and_exposes_no_current_download_or_submission():
    page_path = DOCS / "nine-site-audit-20261026.html"
    parser = parse_page(page_path)
    body = " ".join(parser.text)
    assert "NO NEW TIFF FROM THIS REVIEW" in body
    assert "OK TO SUBMIT: NO" in body
    assert "0.2778" in body and "0.3195" in body and "0.4413" in body
    assert "NOT RUN" in body or "not tested" in body.lower()
    assert parser.states and all(state == "false" for state in parser.states)
    assert "OK TO SUBMIT: YES" not in body
    for href in parser.links:
        url = urlsplit(href)
        if url.scheme or url.netloc:
            continue
        target = (page_path.parent / unquote(url.path)).resolve() if url.path else page_path
        assert target.is_file(), href
        assert target.is_relative_to(ROOT), href
        if url.fragment and target.suffix == ".html":
            assert url.fragment in parse_page(target).ids, href


def test_current_root_and_legacy_download_portal_disambiguate_old_iso91_file():
    render_review_20261030.render(ROOT)
    root = parse_page(ROOT / "index.html")
    root_text = " ".join(root.text)
    assert "OK TO DOWNLOAD: YES" in root_text
    assert "OK TO SUBMIT: NO" in root_text
    assert "docs/index.html" in root.links
    assert "docs/review-20261030/executive-summary.html" in root.links
    current = parse_page(DOCS / "index.html")
    assert "review-20261030/executive-summary.html" in current.links
    assert "review-20261030/run-card.json" in current.links

    # The no-run audit is historical; do not force a later real run to claim
    # that it generated no raster. Its immutable ISO91 pages retain that note.
    for name in ("iso91-index-src.html", "iso91-exec-src.html"):
        page = parse_page(DOCS / name)
        text = " ".join(page.text)
        assert "NO NEW TIFF GENERATED" in text, name
        assert "2026-10-25" in text, name
        assert "NOT OK TO SUBMIT" in text, name
        assert "nine-site-audit-20261026.html" in page.links, name
    guide = " ".join(parse_page(DOCS / "executive-summary.html").text)
    assert "Do not upload the S22 file" in guide
    assert "not an approval to upload that file" in guide
