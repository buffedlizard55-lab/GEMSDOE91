"""Ledger invariants. These protect the two dedupe rules in brief section 6:
exact hash, and repeated (parent, axis, value). No overlap or rank-correlation
thresholds are applied anywhere.
"""

import csv
from collections import Counter
from pathlib import Path

import pytest

LEDGER = Path(__file__).resolve().parents[1] / "ledger" / "submissions.csv"
REQUIRED = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "sha256",
            "status", "predicted_change", "receipt_score"]


@pytest.fixture(scope="module")
def rows():
    with open(LEDGER, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_required_columns_present():
    with open(LEDGER, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    for col in REQUIRED:
        assert col in header, f"ledger is missing column {col}"


def test_ids_unique(rows):
    dupes = [k for k, v in Counter(r["id"] for r in rows).items() if v > 1]
    assert dupes == []


def test_no_duplicate_sha256(rows):
    dupes = [k for k, v in Counter(r["sha256"] for r in rows).items() if v > 1]
    assert dupes == []


def test_no_repeated_parent_axis_value(rows):
    dupes = [k for k, v in Counter((r["parent"], r["axis"], r["value"]) for r in rows).items() if v > 1]
    assert dupes == []


def test_axes_are_from_the_brief(rows):
    allowed = {"MASS", "CONCENTRATION", "SNAP", "PRUNE", "RELIEF", "SPACING", "TRACKB"}
    assert {r["axis"] for r in rows} <= allowed


def test_scores_are_labelled(rows):
    """A receipt_score may be empty. If present it must be a float; the ledger
    must never carry a PROXY or MODEL in a receipt column."""
    for r in rows:
        val = r["receipt_score"].strip()
        if val:
            float(val)


def test_sha256_is_64_hex(rows):
    for r in rows:
        assert len(r["sha256"]) == 64 and int(r["sha256"], 16) >= 0
