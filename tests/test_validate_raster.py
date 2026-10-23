"""Tests for the format/safety gates.

The official sample_submission.tif is NOT in this repo (see IRREGULARITIES.md).
These tests therefore build a synthetic reference with the spec's properties
(float32, EPSG:32611, 100 m, one band) and check that each gate fires on the
defect it is supposed to catch. They do not validate against the real file.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import validate_raster as V  # noqa: E402

CRS = "EPSG:32611"
TRANSFORM = from_origin(600000.0, 4200000.0, 100.0, 100.0)
SHAPE = (24, 30)


def write_tif(path: Path, arr: np.ndarray, crs=CRS, transform=TRANSFORM, dtype="float32", count=1):
    prof = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=count,
                dtype=dtype, crs=crs, transform=transform, nodata=np.nan)
    with rasterio.open(path, "w", **prof) as dst:
        dst.write(arr.astype(dtype), 1)
        if count > 1:
            for b in range(2, count + 1):
                dst.write(arr.astype(dtype), b)
    return path


@pytest.fixture()
def ref(tmp_path):
    """Reference with a footprint: NaN in the outer frame, 0 inside."""
    arr = np.full(SHAPE, np.nan, dtype=np.float32)
    arr[2:-2, 2:-2] = 0.0
    return write_tif(tmp_path / "sample_submission.tif", arr)


def good_candidate(ref: Path, tmp_path: Path, dots=((5, 5), (10, 12), (15, 20))):
    with rasterio.open(ref) as r:
        ref_arr = r.read(1)
    arr = np.full(SHAPE, np.nan, dtype=np.float32)
    inside = np.isfinite(ref_arr)
    arr[inside] = 0.0
    for y, x in dots:
        arr[y, x] = 1.0
    return write_tif(tmp_path / "cand.tif", arr)


def gate_names(rep):
    return {g.name: g for g in rep.gates}


def test_clean_candidate_passes_all_available_gates(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    rep = V.validate_raster(cand, ref)
    g = gate_names(rep)
    for name in ("band count == 1", "dtype float32", "CRS matches", "shape matches",
                 "transform matches", "no NaN/Inf inside footprint", "NaN outside footprint",
                 "values in [0,1]", "re-read from disk matches in-memory band"):
        assert g[name].ok, (name, g[name].detail)


def test_missing_catalogue_and_ledger_are_reported_not_silently_passed(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    rep = V.validate_raster(cand, ref)
    g = gate_names(rep)
    assert not g["zero catalogue mass"].ok
    assert "UNVERIFIED" in g["zero catalogue mass"].detail
    assert not g["sha256 not already in ledger"].ok
    assert not rep.ok


def test_wrong_crs_fails(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    with rasterio.open(ref) as r:
        arr = r.read(1)
    bad = write_tif(tmp_path / "bad_crs.tif", arr, crs="EPSG:4326")
    g = gate_names(V.validate_raster(bad, ref))
    assert not g["CRS matches"].ok


def test_wrong_dtype_fails(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    with rasterio.open(cand) as r:
        arr = r.read(1)
    bad = write_tif(tmp_path / "bad_dtype.tif", arr, dtype="float64")
    g = gate_names(V.validate_raster(bad, ref))
    assert not g["dtype float32"].ok


def test_two_bands_fail(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    with rasterio.open(cand) as r:
        arr = r.read(1)
    bad = write_tif(tmp_path / "two_band.tif", arr, count=2)
    g = gate_names(V.validate_raster(bad, ref))
    assert not g["band count == 1"].ok


def test_nan_inside_footprint_fails(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    with rasterio.open(cand) as r:
        arr = r.read(1)
    arr[8, 8] = np.nan
    bad = write_tif(tmp_path / "nan_inside.tif", arr)
    g = gate_names(V.validate_raster(bad, ref))
    assert not g["no NaN/Inf inside footprint"].ok


def test_values_above_one_fail(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    with rasterio.open(cand) as r:
        arr = r.read(1)
    arr[9, 9] = 1.5
    bad = write_tif(tmp_path / "too_big.tif", arr)
    g = gate_names(V.validate_raster(bad, ref))
    assert not g["values in [0,1]"].ok


def test_zeros_outside_is_info_only_when_flagged(ref, tmp_path):
    with rasterio.open(ref) as r:
        ref_arr = r.read(1)
    arr = np.zeros(SHAPE, dtype=np.float32)  # no NaN anywhere
    arr[5, 5] = 1.0
    cand = write_tif(tmp_path / "zeros.tif", arr)
    strict = gate_names(V.validate_raster(cand, ref))
    assert not strict["NaN outside footprint"].ok
    lax = gate_names(V.validate_raster(cand, ref, allow_zeros_outside=True))
    assert not lax["NaN outside footprint"].must_pass


def test_catalogue_mass_gate(ref, tmp_path):
    cand = good_candidate(ref, tmp_path, dots=((5, 5),))
    cat_arr = np.zeros(SHAPE, dtype=np.float32)
    cat_arr[20, 20] = 1.0
    cat = write_tif(tmp_path / "catalogue.tif", cat_arr)
    g = gate_names(V.validate_raster(cand, ref, catalogue=cat))
    assert g["zero catalogue mass"].ok

    # put a dot exactly on a catalogue pixel -> gate must fail
    with rasterio.open(ref) as r:
        ref_arr = r.read(1)
    arr = np.full(SHAPE, np.nan, dtype=np.float32)
    arr[np.isfinite(ref_arr)] = 0.0
    arr[20, 20] = 1.0
    bad = write_tif(tmp_path / "bad_cat.tif", arr)
    g2 = gate_names(V.validate_raster(bad, ref, catalogue=cat))
    assert not g2["zero catalogue mass"].ok


def test_ledger_dedupe(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    digest = V.sha256_file(cand)
    fields = ["id", "sha256", "sha256_zeros", "status"]
    ledger = tmp_path / "subs.csv"
    with open(ledger, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerow({"id": "x", "sha256": "deadbeef", "sha256_zeros": "", "status": "SUBMITTED"})
    g = gate_names(V.validate_raster(cand, ref, ledger_csv=ledger))
    assert g["sha256 not already in ledger"].ok
    with open(ledger, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writerow({"id": "y", "sha256": digest, "sha256_zeros": "", "status": "SUBMITTED"})
    g2 = gate_names(V.validate_raster(cand, ref, ledger_csv=ledger))
    assert not g2["sha256 not already in ledger"].ok


def test_parent_diff_statistics(ref, tmp_path):
    parent = good_candidate(ref, tmp_path, dots=((5, 5), (10, 12)))
    child_dir = tmp_path / "child"
    child_dir.mkdir()
    child = good_candidate(ref, child_dir, dots=((5, 5), (11, 12)))
    g = gate_names(V.validate_raster(child, ref, parent=parent))
    assert g["parent-diff statistics recorded"].ok
    assert "2 pixels changed" in g["parent-diff statistics recorded"].detail


def test_identical_copy_is_caught_as_zero_diff(ref, tmp_path):
    parent = good_candidate(ref, tmp_path)
    g = gate_names(V.validate_raster(parent, ref, parent=parent))
    assert not g["parent-diff statistics recorded"].ok


def test_transform_mismatch_fails(ref, tmp_path):
    cand = good_candidate(ref, tmp_path)
    with rasterio.open(cand) as r:
        arr = r.read(1)
    bad = write_tif(tmp_path / "bad_tr.tif", arr, transform=from_origin(600050.0, 4200000.0, 100.0, 100.0))
    g = gate_names(V.validate_raster(bad, ref))
    assert not g["transform matches"].ok


def test_ledger_dedupe_ignores_built_rows(ref, tmp_path):
    """A BUILT row is bookkeeping for the file being certified (brief section 7).

    Counting it would make the gate unsatisfiable in the order the brief prescribes:
    build -> record -> certify. Only SUBMITTED rows mean the slot was spent.
    """
    cand = good_candidate(ref, tmp_path)
    digest = V.sha256_file(cand)
    ledger = tmp_path / "subs.csv"
    with open(ledger, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "sha256", "sha256_zeros", "status"])
        w.writeheader()
        w.writerow({"id": "x", "sha256": digest, "sha256_zeros": "", "status": "BUILT"})
    g = gate_names(V.validate_raster(cand, ref, ledger_csv=ledger))
    assert g["sha256 not already in ledger"].ok

    with open(ledger, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "sha256", "sha256_zeros", "status"])
        w.writeheader()
        w.writerow({"id": "x", "sha256": digest, "sha256_zeros": "", "status": "SUBMITTED"})
    g2 = gate_names(V.validate_raster(cand, ref, ledger_csv=ledger))
    assert not g2["sha256 not already in ledger"].ok
