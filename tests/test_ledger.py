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
    # GEOD (main, 2026-10-24 strain-prior lane) and DENOVO (2026-10-24 de novo
    # surface lane, no parent dots; see IR-91-36) extend the brief's axis list.
    allowed = {"MASS", "CONCENTRATION", "SNAP", "PRUNE", "RELIEF", "SPACING", "TRACKB", "GEOD", "DENOVO", "BASEMENT", "ASC91", "FUSE91", "SPAC", "S14LSRG", "S16PC91", "S17EULR", "TLF25"}  # S17EULR: session 17 Euler-deconvolution fusion lane row (docs/HYPOTHESES_S17.md); S16PC91: session 16 phase-congruency lane row (docs/HYPOTHESES_S16.md); BASEMENT: session 10 row (IR-91-S10-02); ASC91: antisymmetric step lane row (docs/HYPOTHESES_ASC91.md); FUSE91: step x context fusion lane row (docs/HYPOTHESES_F91.md); SPAC: session 12 3D Analytic Signal/SPI + Swarm + Radon Auto-Context lane (docs/HYPOTHESES_S12.md); S14LSRG: session 14 LiDAR-scarp + radiometric-ratio lane (docs/HYPOTHESES_S14.md)
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
