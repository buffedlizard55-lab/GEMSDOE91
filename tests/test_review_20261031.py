"""Regression checks for the 2026-10-31 blocked review and its evidence files.

These tests read only tracked JSON/Markdown. They do not touch the network and
do not need competition data.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "review-20261031"


def _load(path: Path):
    return json.loads(path.read_text())


def test_leaderboard_snapshot_is_internally_consistent():
    lb = _load(ROOT / "evidence" / "public-leaderboard-2026-10-31.json")
    rows = lb["rows"]
    assert lb["rows_shown"] == len(rows) == 50
    assert [r["rank"] for r in rows] == list(range(1, 51))
    scores = [r["best_public_dw_tversky"] for r in rows]
    assert all(a >= b for a, b in zip(scores, scores[1:])), "scores must not increase down the table"
    assert scores[0] == lb["top_score"] == 0.4544
    assert scores[-1] == lb["cutoff_rank_50_score"] == 0.3195
    assert lb["user_reported_values_present_in_top_50"] is False
    assert not any(s in (0.4413, 0.2778, 0.2600, 0.2708) for s in scores)


def test_encoding_audit_matches_pinned_snapshot_and_footprint():
    doc = _load(REVIEW / "nine-site-encoding-audit.json")
    files = doc["files"]
    assert len(files) == 9
    assert all(f["sha256_matches_pinned_snapshot"] and f["bytes_match_pinned_snapshot"] for f in files)
    assert all(f["crs"] == "EPSG:32611" and f["shape"] == [3730, 3292] for f in files)
    assert all(f["dtype"] == "float32" and f["count"] == 1 for f in files)
    assert all(f["finite_min"] >= 0.0 and f["finite_max"] <= 1.0 for f in files)
    assert all(f["dots_outside_footprint"] == 0 for f in files)
    assert doc["footprint_cells"] == 5167373
    assert doc["grid_cells"] == 3730 * 3292 == 12279160
    assert doc["nan_encoded_files_share_one_footprint"] is True
    assert doc["nan_encoded_sites"] == ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE31"]
    assert doc["zero_encoded_sites"] == ["GEMSDOE30", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def test_recorded_subset_relations_hold():
    doc = _load(REVIEW / "nine-site-encoding-audit.json")
    rel = {(r["subset"], r["superset"]): r["dots_in_superset_not_subset"] for r in doc["exact_subset_relations"]}
    # GEMSDOE32 is an exact subset of 25/30 (6,436 removed), 31 (2,545), and 36 (1,200).
    assert rel[("GEMSDOE32", "GEMSDOE25")] == 6436
    assert rel[("GEMSDOE32", "GEMSDOE30")] == 6436
    assert rel[("GEMSDOE32", "GEMSDOE31")] == 2545
    assert rel[("GEMSDOE32", "GEMSDOE36")] == 1200
    assert rel[("GEMSDOE31", "GEMSDOE25")] == 3891


def test_run_card_records_a_blocked_state_with_null_measurements():
    card = _load(REVIEW / "run-card.json")
    assert card["verdict"] == "negative_blocked"
    assert card["candidate_generated"] is False
    assert card["ok_to_submit"] is False
    assert card["ok_to_download_new_candidate"] is False
    assert card["lane"] is None
    assert card["experiments_used"] == 0
    assert card["weekly_slots_used"] == 0
    assert card["holdout_dti"]["value"] is None
    assert card["organizer_confirmed_score"] is None
    assert card["leaderboard_estimate"] is None
    assert card["raster_sha256"] is None
    assert card["submission_name"] is None
    assert card["submission_note_max_chars"] == 140


def test_review_links_the_official_sources_and_states_the_verdict():
    text = (REVIEW / "REVIEW.md").read_text()
    for url in (
        "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
        "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
        "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
        "https://github.com/drivendataorg/gems-prize-reference-solution",
    ):
        assert url in text, url
    assert "BLOCKED" in text and "OK TO SUBMIT: NO" in text
    assert "`0.4544`" in text and "`0.3195`" in text
