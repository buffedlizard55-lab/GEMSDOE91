"""The active review must keep research delivery separate from submission approval."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"a", "link"} and "href" in attrs:
            self.hrefs.append(attrs["href"])

    def handle_data(self, data):
        self.text.append(data)


def test_current_run_card_is_negative_and_does_not_fabricate_a_candidate():
    card = json.loads((ROOT / "docs/run-card-7564a0e0.json").read_text())
    assert card["branch"] == "arena/7564a0e0-gemsdoe91"
    assert card["verdict"] == "negative" and card["promote"] is False
    assert card["experiments_used"] == 0 and card["weekly_slots_used"] == 0
    assert card["organizer_confirmed_score"] is None

    holdout = card["holdout_dti"]
    assert holdout["label"] == "HOLDOUT-DTI"
    assert holdout["status"].startswith("NOT RUN")
    assert holdout["value"] is None
    assert holdout["evaluator_version"] is None
    assert holdout["withheld_positives"] is None and holdout["ci95"] is None

    comparison = card["registry_correlation_overlap"]
    assert comparison["status"].startswith("NOT RUN")
    assert comparison["surface_rank_correlation"] is None
    assert comparison["max_final_dot_overlap_within_3px"] is None
    assert card["raster_sha256"] is None and card["raster_path"] is None
    assert card["validator_output"]["status"].startswith("NOT APPLICABLE")
    assert card["submission_name"] is None and card["submission_note"] is None

    existing = card["existing_research_download"]
    path = ROOT / existing["path"]
    assert path.is_file()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == existing["sha256"]
    assert existing["ok_to_download"] is True and existing["ok_to_submit"] is False
    delivery = existing["validator_output"]
    assert delivery["status"].startswith("PASS") and delivery["submission_approval"] is False
    assert delivery["single_band"] and delivery["float32"] and delivery["no_nan_inside_footprint"]
    assert delivery["values_in_0_1"] and delivery["crs"] == "EPSG:32611"
    assert delivery["shape"] == [3730, 3292] and delivery["transform_matches_sample"]
    assert existing["research_download_note_characters"] <= card["submission_note_max_characters"]

    upstream = card["upstream_research_demo"]
    s18_tif = ROOT / upstream["path"]
    s18_zip = ROOT / upstream["zip_path"]
    assert s18_tif.is_file() and s18_zip.is_file()
    assert hashlib.sha256(s18_tif.read_bytes()).hexdigest() == upstream["raster_sha256"]
    assert hashlib.sha256(s18_zip.read_bytes()).hexdigest() == upstream["zip_sha256"]
    assert upstream["ok_to_download"] is True and upstream["ok_to_submit"] is False
    assert upstream["holdout_dti"]["value"] is None
    assert upstream["registry_uniqueness"]["status"].startswith("NOT CERTIFIED")
    assert upstream["submission_note_characters"] <= card["submission_note_max_characters"]

    prior = existing["prior_olc91_holdout"]
    assert prior["candidate"]["label"] == "HOLDOUT-DTI"
    assert prior["candidate"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert prior["candidate"]["withheld_positives"] == 11321
    assert prior["candidate"]["ci95"][0] < prior["candidate"]["value"] < prior["candidate"]["ci95"][1]


def test_current_download_audit_covers_s18_without_granting_submission_approval():
    audit = json.loads((ROOT / "docs/review-7564a0e0/download-audit.json").read_text())
    assert audit["files_checked"] == 89
    assert audit["format_pass"] == 80 and audit["format_fail"] == 9
    assert audit["ok_to_submit"] is False
    rows = {row["path"]: row for row in audit["files"]}
    for suffix in (
        "docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405.tif",
        "docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405.zip",
    ):
        assert rows[suffix]["status"] == "PASS"
        assert rows[suffix]["ok_to_submit"] is False


def test_claim_and_public_leaderboard_values_have_distinct_evidence_classes():
    card = json.loads((ROOT / "docs/run-card-7564a0e0.json").read_text())
    evidence = card["score_evidence"]
    assert evidence["gemsdoe32_h33_2_b2_claim"]["evidence_label"] == "USER-REPORTED-UNVERIFIED"
    assert evidence["gemsdoe32_h33_2_b2_claim"]["organizer_receipt"] is None
    assert evidence["public_leaderboard_rank_1"]["evidence_label"].startswith("PUBLIC-LEADERBOARD")
    assert evidence["public_leaderboard_rank_24"]["evidence_label"].startswith("PUBLIC-LEADERBOARD")
    assert evidence["public_leaderboard_rank_50"]["evidence_label"].startswith("PUBLIC-LEADERBOARD")


def test_active_review_pages_links_and_readme_prompt_are_preserved():
    for name in ("docs/review-7564a0e0.html", "docs/index.html", "docs/executive-summary.html"):
        path = ROOT / name
        parser = Links()
        parser.feed(path.read_text())
        assert parser.hrefs
        for href in parser.hrefs:
            url = urlsplit(href)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            assert target.is_file(), (name, href)
            assert target.is_relative_to(ROOT)

    summary = (ROOT / "docs/review-7564a0e0.html").read_text()
    assert "OK TO DOWNLOAD: YES" in summary
    assert "OK TO SUBMIT: NO" in summary
    assert "no candidate, raster, score, or slot use" in summary
    assert "OK TO SUBMIT: NO — OLC91 NEGATIVE; S18 HOLDOUT NOT RUN" in summary
    assert "S18-UNIQUE research demo" in summary
    assert "USER-REPORTED-UNVERIFIED" in summary
    assert "PUBLIC-LEADERBOARD" in summary

    readme = (ROOT / "README.md").read_text()
    assert "<a id=\"full-project-brief\"></a>" in readme
    assert "Current request addendum" in readme
    assert "Preserved standing user prompt" in readme
    assert "Start every session" in readme

    sources = json.loads((ROOT / "docs/review-7564a0e0/sources.json").read_text())
    assert sources["review_id"] == "ARENA-7564A0E0-20261025"
    assert any(row["id"] == "usgs_fdsn_broad_query" for row in sources["sources"])
    assert any(row["id"] == "drivendata_data_tab" for row in sources["sources"])


def test_active_portal_status_is_generated_from_current_source_templates():
    assert (ROOT / "docs/index.html").read_bytes() == (ROOT / "docs/olc91-index-src.html").read_bytes()
    assert (ROOT / "docs/executive-summary.html").read_bytes() == (ROOT / "docs/olc91-exec-src.html").read_bytes()
    index = (ROOT / "docs/index.html").read_text()
    assert "Active review arena/7564a0e0" in index
    assert "review-7564a0e0.html" in index
    assert "EXISTING OLC91-E1 RESEARCH DOWNLOAD" in index
    assert "OK TO SUBMIT: NO — HOLDOUT NOT RUN" in index
    assert "S18-UNIQUE research demo" in index
    assert "REVIEW-ACTIVE-FFB91DA8-20261025.md" not in index
