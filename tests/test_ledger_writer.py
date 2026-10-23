"""Regression guard for the shared ledger.

The ledger is state that three sessions write to. `scripts/build_spacing.py` used
to rewrite it with its own column list, which silently dropped the `source` and
`notes` columns that the importing sessions had filled in -- every row lost its
provenance on the next rebuild. These tests fail if that comes back.
"""
from __future__ import annotations

import csv
from pathlib import Path

LEDGER = Path(__file__).resolve().parents[1] / "ledger" / "submissions.csv"

# Columns other sessions own. They must survive a session-3 rebuild untouched.
FOREIGN_COLUMNS = ("source", "notes")


def _rows():
    with LEDGER.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh)), fh.seek(0)


def test_foreign_columns_survive():
    with LEDGER.open(newline="", encoding="utf-8-sig") as fh:
        header = next(csv.reader(fh))
    for col in FOREIGN_COLUMNS:
        assert col in header, f"the shared ledger lost the '{col}' column"


def test_every_row_still_has_provenance():
    rows, _ = _rows()
    assert rows
    for r in rows:
        assert (r.get("source") or "").strip(), f"{r['id']} lost its provenance"


def test_session_rows_and_foreign_rows_coexist():
    rows, _ = _rows()
    axes = {r["axis"] for r in rows}
    assert "SPACING" in axes
    assert len(axes) >= 2
    # no duplicate identity, no duplicate hash, no repeated (parent, axis, value)
    assert len({r["id"] for r in rows}) == len(rows)
    assert len({r["sha256"] for r in rows}) == len(rows)
    assert len({(r["parent"], r["axis"], r["value"]) for r in rows}) == len(rows)
    # and still no receipt anywhere
    assert all(not (r.get("receipt_score") or "").strip() for r in rows)
