"""Integration tests: parent lineage proof and release gates.

Skipped when the pinned inputs are absent (they are gitignored). CI restores
them first, so these run there.
"""
from __future__ import annotations

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


def test_parent_rebuilds_byte_exactly_from_recorded_recipe():
    from gems91 import lineage
    proof = lineage.prove_r0_byte_rebuild(
        parent_nan=PARENT_NAN, parent_zeros=PARENT_ZEROS,
        ancestor_d28=ANC_D28, ancestor_solo=ANC_SOLO,
        sample=TEMPLATE, catalogue=CATALOGUE,
        work_dir=ROOT / "tests" / "_tmp" / "r0-byte-proof")
    assert proof["ok"], proof
    assert proof["byte_rebuilds"]["nan"]["hash_match"]
    assert proof["byte_rebuilds"]["zeros"]["hash_match"]


def test_template_carries_the_catalogue_not_zeros():
    """IR-91-09: the template's positive cells ARE the mapped catalogue."""
    from gems91 import io as _io
    template = _io.read_grid(TEMPLATE)
    cat = geom.catalogue_mask(_io.read_grid(CATALOGUE))
    assert np.array_equal(template > 0, cat)
    assert not np.array_equal(np.isfinite(template), np.ones_like(cat))


def test_every_release_passes_every_gate():
    """Every file listed in releases/MANIFEST.json passes the MUST gates.

    The expected dot count comes from the manifest entry (which records it per
    file, taken from the ledger), because the PRUNE ladder ships fewer dots than
    the parent while SPACING and RELIEF hold the count fixed.
    """
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    man = json.loads((ROOT / "releases" / "MANIFEST.json").read_text())
    assert man["files"], "manifest lists no releases"
    for entry in man["files"]:
        f = ROOT / "releases" / entry["file"]
        assert f.is_file(), f"{f.name} listed in the manifest but not built"
        enc = "zeros" if f.name.endswith("-zeros.tif") else "nan"
        rep = gates.validate_release(f, template=TEMPLATE, catalogue=cat, encoding=enc,
                                     expect_dots=entry["n_dots"])
        assert rep["PASS"], (f.name, rep["failed"])
        assert rep["min_catalogue_distance_px"] > 2.0
