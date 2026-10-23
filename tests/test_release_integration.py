"""Integration tests: parent lineage proof and release gates.

Skipped when the pinned inputs are absent (they are gitignored). CI restores
them first, so these run there.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import gates, geom, io  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "bridge" / "sample_submission.tif"
CATALOGUE = DATA / "bridge" / "existing_faults.tif"
PARENT_NAN = DATA / "parent" / "r0-nan.tif"
PARENT_ZEROS = DATA / "parent" / "r0-zeros.tif"
ANC_D28 = DATA / "ancestors" / "d2.8-nan.tif"
ANC_SOLO = DATA / "ancestors" / "solo-d2.8.tif"

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
    """IR-91-01: the template's positive cells ARE the mapped catalogue."""
    from gems91 import io as _io
    template = _io.read_grid(TEMPLATE)
    cat = geom.catalogue_mask(_io.read_grid(CATALOGUE))
    assert np.array_equal(template > 0, cat)
    assert not np.array_equal(np.isfinite(template), np.ones_like(cat))


def test_every_release_passes_every_gate():
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    files = sorted((ROOT / "releases").glob("*.tif"))
    assert files, "no releases built"
    for f in files:
        enc = "zeros" if f.name.endswith("-zeros.tif") else "nan"
        rep = gates.validate_release(f, template=TEMPLATE, catalogue=cat, encoding=enc,
                                     expect_dots=37654)
        assert rep["PASS"], (f.name, rep["failed"])
        assert rep["min_catalogue_distance_px"] > 2.0
