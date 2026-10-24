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
    allowed = {"MASS", "CONCENTRATION", "SNAP", "PRUNE", "RELIEF", "SPACING", "TRACKB", "GEOD"}
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

def test_every_row_has_the_header_width():
    """IR-91-37: tools/stor.append_ledger writes 16 of this file's 21 columns.

    A short row is silently padded by DictReader and shifts every value one column left
    (sha256 lands in pct_relocated), so the check has to be on the raw csv reader.
    """
    with LEDGER.open(newline="", encoding="utf-8-sig") as fh:
        raw = list(csv.reader(fh))
    width = len(raw[0])
    assert width == 21, f"header width changed: {width}"
    bad = [i for i, r in enumerate(raw[1:], start=2) if len(r) != width]
    assert not bad, f"rows {bad[:5]} are not {width} fields wide (IR-91-37)"
