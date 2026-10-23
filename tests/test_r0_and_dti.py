from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_prune_refine as run  # noqa: E402
from scripts import build_prune_variants as bpv  # noqa: E402
from gems57 import metric  # noqa: E402


def test_all_manifest_pins_and_exact_r0_rebuild() -> None:
    verified = bpv.verify_manifest(ROOT / "registry" / "data_manifest.json")
    assert len(verified) == 14
    lineage = bpv.rebuild_r0_from_lineage(verified)
    assert int(lineage["r0"].sum()) == 37_654
    assert lineage["rebuilt_zeros_sha256"] == bpv.PARENT_SHA_ZEROS
    assert lineage["rebuilt_nan_sha256"] == bpv.PARENT_SHA_NAN
    assert not np.any(lineage["r0"] & lineage["catalogue"])
    assert int((lineage["d_cat"][lineage["r0"]] <= 2.0).sum()) == 0


def test_exact_binary_metric_algebra_matches_reference_metric() -> None:
    pred = np.zeros((15, 17), dtype=bool)
    pred[2, 3] = True
    pred[7, 8] = True
    truth = np.zeros_like(pred)
    truth[2, 4:8] = True
    truth[8, 7] = True
    valid = np.ones_like(pred)
    valid[:, :2] = False
    known = np.zeros_like(pred)
    known[2, 4] = True

    got = bpv.dti_algebra_components(pred.astype(np.float32), truth, valid=valid, known=known)
    ref = metric.dti_binary(pred, truth, valid=valid, known=known)
    assert abs(got["dti"] - ref["dti"]) < 1e-12


def test_selected_prune_values_are_distinct_and_within_allowed_change_range() -> None:
    assert run.AXIS == "PRUNE"
    assert tuple(run.RUN_VALUES) == ("p2p6",)
    assert set(run.RADII) == set(run.RUN_VALUES)
    assert all(2.0 < run.RADII[value] < 4.0 for value in run.RUN_VALUES)
    assert len({run.RADII[v] for v in run.RUN_VALUES}) == 1


def test_no_candidate_tiff_is_tracked_by_gitignore_policy() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "/data/" in ignore
    assert "/releases/*.tif" in ignore
