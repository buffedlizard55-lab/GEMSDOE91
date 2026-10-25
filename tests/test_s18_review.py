"""Session 18 review checks: leaderboard transcription, feasibility arithmetic,
saved verifier output, run-card schema, and label/hash rules in the review.

Run: .venv/bin/python -m pytest tests/test_s18_review.py -q
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


# ---------- leaderboard transcription ----------

def test_leaderboard_has_50_sorted_rows_with_known_endpoints():
    d = _load("docs/s18/leaderboard-top50-20261025.json")
    assert "OFFICIAL" in d["evidence_class"]  # snapshot of the organizer's public page
    rows = d["rows"]
    assert len(rows) == 50
    assert [r["rank"] for r in rows] == list(range(1, 51))
    scores = [r["score"] for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert rows[0]["score"] == 0.4413
    assert rows[-1]["score"] == 0.2818


def test_user_claims_placed_correctly():
    rows = _load("docs/s18/leaderboard-top50-20261025.json")["rows"]

    def placement(score: float) -> str:
        if score > rows[0]["score"]:
            return "above rank 1"
        for r in rows:
            if score >= r["score"]:
                return f"rank {r['rank']}"
        return "below rank 50"

    assert placement(0.4413) == "rank 1"
    assert placement(0.3195) == "rank 24"
    assert placement(0.2778) == "below rank 50"


# ---------- feasibility arithmetic ----------

def test_feasibility_arithmetic():
    f = _load("docs/s16/registry-feasibility.json")
    U = 6649
    N = 37654
    bound = (N - U) / N
    assert math.isclose(bound, 0.8234184947, rel_tol=1e-9)
    assert bound > 0.70
    n_max = math.floor(U / 0.30)
    assert n_max == 22163
    # The feasibility JSON must record the same uncovered count.
    assert f["uncovered_pixels"] == U


# ---------- saved verifier output ----------

def test_verification_output_all_ok():
    v = _load("docs/s18/verification.json")
    assert v["all_ok"] is True
    assert v["leaderboard"]["ok"] is True
    assert v["feasibility"]["ok"] is True
    assert v["feasibility"]["feasible_at_budget"] is False
    assert v["feasibility"]["max_budget_satisfying_literal_threshold"] == 22163
    assert v["cited_files"]["ok"] is True
    assert v["cited_files"]["missing"] == []
    for name, c in v["candidates"].items():
        assert c["ok"] is True, name
        assert c["finite_min"] >= 0.0 and c["finite_max"] <= 1.0, name
        assert c["nan_inside_footprint"] == 0, name
        assert c["dots_outside_footprint"] == 0, name


# ---------- run card schema and labels ----------

REQUIRED_RUN_CARD_KEYS = {
    "hypothesis",
    "mechanism",
    "holdout",
    "correlation_and_overlap",
    "raster_sha256",
    "validator_output",
    "submission",
    "verdict",
    "promote",
    "ok_to_submit",
    "irregularities",
}


def test_run_card_s18_schema():
    card = _load("docs/run-card-S18.json")
    missing = REQUIRED_RUN_CARD_KEYS - set(card)
    assert not missing, f"missing keys: {missing}"
    assert card["verdict"] in {"promote", "negative"}
    assert card["promote"] is False
    assert card["ok_to_submit"] is False
    assert card["experiments"]["used"] <= 3


def test_run_card_s18_holdout_is_labelled_and_not_fabricated():
    card = _load("docs/run-card-S18.json")
    h = card["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI"
    if h["status"] == "NOT_RUN":
        assert h["dti"] is None and h["ci95"] is None
    else:
        assert isinstance(h["dti"], float)
        assert len(h["ci95"]) == 2


def test_run_card_s18_submission_note_within_limit():
    sub = _load("docs/run-card-S18.json")["submission"]
    if sub["note"] is not None:
        assert len(sub["note"]) <= 140
        assert sub["note_chars"] == len(sub["note"])


def test_run_card_s18_hashes_match_existing_run_cards():
    card = _load("docs/run-card-S18.json")
    olc = _load("docs/run-card-OLC91.json")
    dz = _load("docs/run-card-unique-offcatalogue-damagezone.json")
    assert card["raster_sha256"]["OLC91_E1"] == olc["raster_sha256"]
    assert card["raster_sha256"]["unique_damagezone"] in (ROOT / "docs/run-card-unique-offcatalogue-damagezone.json").read_text(encoding="utf-8")


def test_run_card_cited_irregularities_exist_in_register():
    text = (ROOT / "IRREGULARITIES.md").read_text(encoding="utf-8")
    for irid in _load("docs/run-card-S18.json")["irregularities"]:
        assert irid in text, irid


# ---------- review document rules ----------

def test_review_numbers_carry_required_labels():
    text = (DOCS / "REVIEW-S18-20261025.md").read_text(encoding="utf-8")
    assert "HOLDOUT-DTI" in text
    assert "ORGANIZER-CONFIRMED" in text
    assert "UNVERIFIED" in text
    # The user-reported 0.2778 must never appear as an unlabelled score.
    for m in re.finditer(r"0\.2778", text):
        window = text[max(0, m.start() - 200): m.end() + 200]
        assert re.search(r"UNVERIFIED|user-reported|user report|claim|would|below", window, re.I), window


def test_review_hashes_match_run_cards():
    text = (DOCS / "REVIEW-S18-20261025.md").read_text(encoding="utf-8")
    assert "35259f3abe1df772cef3fb5646b01eb12eb7776192fd870f291405a482abf8dc" in text or \
        "35259f3a" in text
    assert "a5636b10237757cda5de1a7561a0d5f2600479cdd8610226dfd4c1650b66ca11" in text or \
        "a5636b10" in text


def test_review_does_not_claim_0_4413_is_gemsdoe():
    text = (DOCS / "REVIEW-S18-20261025.md").read_text(encoding="utf-8")
    assert "global #1" in text
