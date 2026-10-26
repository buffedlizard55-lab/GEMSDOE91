"""Regression checks for the branch-specific current review front door."""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


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


def test_current_run_card_is_fail_closed_and_branch_scoped():
    card = json.loads((ROOT / "docs/run-card-ARENA-5CD5E4F7-20261026.json").read_text())
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


def test_root_and_portal_front_doors_prominently_link_current_audit():
    for rel in ("index.html", "docs/index.html"):
        path = ROOT / rel
        page = Links()
        page.feed(path.read_text())
        text = " ".join(page.text)
        assert "NO NEW TIFF GENERATED" in text
        assert "OK TO SUBMIT: NO" in text
        assert "0.2778" in text and "UNVERIFIED" in text.upper()
        assert "high-score-submissions-review.html" in page.hrefs or rel == "index.html"
        assert any(href.endswith("run-card-ARENA-5CD5E4F7-20261026.json") for href in page.hrefs)
        for href in page.hrefs:
            u = urlsplit(href)
            if u.scheme or u.netloc:
                continue
            target = (path.parent / unquote(u.path)).resolve() if u.path else path
            assert target.is_file(), f"broken local link in {rel}: {href}"
            assert target.is_relative_to(ROOT)


def test_site_summary_hypotheses_and_user_score_provenance_are_explicit():
    review = (ROOT / "docs/REVIEW-SITE-AUDIT-20261026.md").read_text()
    assert "USER/OWNER-REPORTED, UNVERIFIED" in review
    assert "GEMSDOE32" in review and "0.2778" in review
    assert "Ranked hypotheses — proposals, not results" in review
    assert all(f"| **{rank}** |" in review for rank in (1, 2, 3))
    assert "Not viable until those checks/access are completed" in review
    assert "No experiment was launched" in review

    summary = (ROOT / "docs/high-score-submissions-review.html").read_text()
    assert "Prospective score estimate" in summary
    assert "Cross-site uniqueness / download verdict" in summary
    assert summary.count("Not estimable: no new candidate or holdout run.") == 9
    assert "LIKELY DUPLICATE" in summary and "pixel-identical" in summary
    assert "do not upload" in summary.lower()
