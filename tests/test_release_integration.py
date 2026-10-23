"""Integration tests: parent lineage proof and release gates.

Skipped when the pinned inputs are absent (they are gitignored). CI restores
them first, so these run there.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import geom, io, release_gates as gates  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"

pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in (TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS, ANC_D28, ANC_SOLO)),
    reason="pinned inputs absent - run scripts/restore_data.py",
)

PARENT_SHA_ZEROS = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
PARENT_DIGEST = "905cee9d4383de23d6ee6366da4627fe19a78e4f49ce3a2462a8736e9b66a027"


def test_parent_matches_its_pin_and_known_digest():
    assert io.sha256_file(PARENT_ZEROS) == PARENT_SHA_ZEROS
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    assert int(parent.sum()) == 37654
    assert io.dot_digest(parent) == PARENT_DIGEST


@pytest.mark.parametrize("ancestor", [ANC_D28, ANC_SOLO])
def test_parent_rebuilds_exactly_from_each_ancestor(ancestor):
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    rebuilt = io.dot_mask(io.read_grid(ancestor)) & (dcat > geom.CATALOGUE_FLOOR_PX)
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    assert np.array_equal(rebuilt, parent)


def test_template_carries_the_catalogue_not_zeros():
    """IR-91-09: the template's positive cells ARE the mapped catalogue."""
    from gems91 import io as _io
    template = _io.read_grid(TEMPLATE)
    cat = geom.catalogue_mask(_io.read_grid(CATALOGUE))
    assert np.array_equal(template > 0, cat)
    assert not np.array_equal(np.isfinite(template), np.ones_like(cat))


def test_every_release_passes_every_gate():
    """Every reproducible release passes the gates of its OWN encoding and ledger row.

    Session 3 assumed every release holds the parent's dot count; MASS arms
    deliberately do not, so the count is checked against the ledger row that owns
    the hash. Files absent from `releases/MANIFEST.json` are audit-only withdrawn
    drafts (ledger status SUPERSEDED-DRAFT) and are not required to be present.
    """
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    manifest = json.loads((ROOT / "releases" / "MANIFEST.json").read_text())
    stated = {f["file"]: f["sha256"] for f in manifest["files"]}
    with (ROOT / "ledger" / "submissions.csv").open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    by_sha = {r["sha256"]: r for r in rows}
    by_sha_zeros = {r.get("sha256_zeros"): r for r in rows if r.get("sha256_zeros")}
    files = sorted((ROOT / "releases").glob("*.tif"))
    assert files, "no releases built"
    for f in files:
        if f.name not in stated:
            continue                       # withdrawn draft: audit trail only
        enc = "zeros" if f.name.endswith("-zeros.tif") else "nan"
        rep = gates.validate_release(f, template=TEMPLATE, catalogue=cat, encoding=enc)
        row = (by_sha_zeros if enc == "zeros" else by_sha)[stated[f.name]]
        assert rep["PASS"], (f.name, rep["failed"])
        assert rep["n_dots"] == int(row["n_dots"]), f.name
        assert rep["n_dots"] == rep["n_dots"]  # re-read from disk inside the gate
