"""Tests for ledger maintenance: collapse repeats, dedupe, weekly slot counting."""

from __future__ import annotations

import csv
import datetime as dt
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ledger as L  # noqa: E402

RAW = """site\tname\tscore\tencoding\tn_dots\tsha8\tparent\treceipt
GEMSDOE\ta\t0.1922\tnan\t121000\t11111111\t\tY
GEMSDOE\tb\t0.2477\tnan\t44000\t22222222\ta\tY
GEMSDOE\tb\t0.2477\tzeros\t44000\t22222222\ta\tY
GEMSDOE\tc\t0.2778\tnan\t37654\t33333333\tb\tY
GEMSDOE\td\t0.2343\tnan\t40000\t44444444\ta\tN
"""


@pytest.fixture()
def raw_file(tmp_path):
    p = tmp_path / "raw_paste.txt"
    p.write_text(RAW)
    return p


def test_parse_and_collapse_repeats(raw_file, tmp_path):
    rows = L.parse_raw(raw_file)
    assert len(rows) == 5
    unique, repeats = L.collapse(rows)
    assert len(unique) == 4
    assert len(repeats) == 1
    assert repeats[0]["name"] == "b"


def test_collapse_keeps_the_higher_score(tmp_path):
    p = tmp_path / "raw.txt"
    p.write_text(
        "site\tname\tscore\tencoding\tn_dots\tsha8\tparent\treceipt\n"
        "S\tx\t0.20\tnan\t100\tdeadbeef\t\tY\n"
        "S\tx\t0.25\tnan\t100\tdeadbeef\t\tY\n"
    )
    unique, repeats = L.collapse(L.parse_raw(p))
    assert len(unique) == 1
    assert float(unique[0]["score"]) == 0.25
    assert len(repeats) == 1


def test_pipe_and_comma_separators(raw_file, tmp_path):
    p = tmp_path / "pipe.txt"
    p.write_text("S | y | 0.21 | nan | 100 | abcdef12 |  | Y\n")
    rows = L.parse_raw(p)
    assert rows[0]["name"] == "y"
    assert rows[0]["score"] == "0.21"


def test_ledger_rows_label_receipt_vs_claim(raw_file, tmp_path):
    unique, _ = L.collapse(L.parse_raw(raw_file))
    rows = L.to_ledger_rows(unique)
    by_name = {r["name"]: r for r in rows}
    assert by_name["a"]["status"] == "SUBMITTED"
    assert by_name["a"]["receipt_score"] == "0.1922"
    assert by_name["d"]["status"] == "CLAIM"
    assert by_name["d"]["receipt_score"] == ""  # no receipt -> never a score


def test_roundtrip_write_read(tmp_path, raw_file):
    out = tmp_path / "subs.csv"
    unique, _ = L.collapse(L.parse_raw(raw_file))
    L.write_rows(L.to_ledger_rows(unique), out)
    back = L.read_rows(out)
    assert len(back) == 4
    assert set(back[0]) == set(L.COLUMNS)


def test_is_repeat_on_hash(tmp_path):
    rows = [{"id": "x", "sha256": "a" * 64, "sha8": "a" * 8, "parent": "", "axis": "", "value": ""}]
    assert L.is_repeat(rows, "a" * 64, "", "", "")
    assert not L.is_repeat(rows, "b" * 64, "", "", "")


def test_is_repeat_on_parent_axis_value(tmp_path):
    rows = [{"id": "x", "sha256": "", "sha8": "", "parent": "R0", "axis": "PRUNE", "value": "3"}]
    assert L.is_repeat(rows, "c" * 64, "R0", "PRUNE", "3")
    assert not L.is_repeat(rows, "c" * 64, "R0", "PRUNE", "1")


def test_week_slots_counts_only_recent_receipts():
    today = dt.date(2026, 10, 23)
    rows = [
        {"status": "SUBMITTED", "receipt_date": "2026-10-22"},
        {"status": "SUBMITTED", "receipt_date": "2026-10-10"},
        {"status": "BUILT", "receipt_date": "2026-10-22"},
        {"status": "SUBMITTED", "receipt_date": ""},
    ]
    used, quota = L.week_slots(rows, today=today)
    assert (used, quota) == (1, 3)


def test_add_refuses_a_repeat(tmp_path):
    led = tmp_path / "s.csv"
    L.write_rows([{"id": "x", "sha256": "a" * 64, "sha8": "a" * 8}], led)
    rc = L.main(["--ledger", str(led), "add", "--id", "y", "--sha256", "a" * 64])
    assert rc == 1


def test_add_accepts_a_new_file(tmp_path):
    led = tmp_path / "s.csv"
    L.write_rows([], led)
    rc = L.main(["--ledger", str(led), "add", "--id", "y", "--sha256", "b" * 64,
                 "--parent", "R0", "--axis", "PRUNE", "--value", "3"])
    assert rc == 0
    rows = L.read_rows(led)
    assert rows[0]["id"] == "y"
    assert rows[0]["sha8"] == "b" * 8
    assert rows[0]["status"] == "BUILT"
