import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems91.gates import (PINNED_GRID, min_distance_to_mask, sha256_file,
                          validate)

H, W = PINNED_GRID["height"], PINNED_GRID["width"]
TRANSFORM = from_origin(PINNED_GRID["left"], PINNED_GRID["top"], 100.0, 100.0)


def write_tif(path, arr, dtype="float32", crs="EPSG:32611", transform=TRANSFORM):
    nodata = np.nan if np.issubdtype(np.dtype(dtype), np.floating) else None
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0],
                       width=arr.shape[1], count=1, dtype=dtype, crs=crs,
                       transform=transform, nodata=nodata) as dst:
        dst.write(arr.astype(dtype), 1)
    return path


def small_grid(arr):
    """Write a small test raster with a matching small 'sample_submission'."""
    h, w = arr.shape
    tr = TRANSFORM
    ss = np.zeros((h, w), dtype="float32")
    ss[:] = 0.0
    return arr, tr, ss


@pytest.fixture
def data(tmp_path):
    """Small synthetic stack: sample_submission, catalogue, candidate."""
    h, w = 60, 60
    tr = from_origin(243350.0, 4508550.0, 100.0, 100.0)
    sample = np.zeros((h, w), "float32")
    sample[0:50, 0:50] = 0.0      # footprint = rows 0..49, cols 0..49
    sample[50:, :] = np.nan
    sample[:, 50:] = np.nan
    ss = tmp_path / "sample_submission.tif"
    write_tif(ss, sample, transform=tr)

    cat = np.zeros((h, w), "float32")
    cat[10, 10] = 1.0             # catalogue pixel
    cat[10, 11] = 1.0
    catp = tmp_path / "existing_faults.tif"
    write_tif(catp, cat, transform=tr)

    cand = np.zeros((h, w), "float32")
    cand[20, 20] = 1.0            # far from catalogue -> collar ok
    cand[50:, :] = np.nan
    cand[:, 50:] = np.nan
    candp = tmp_path / "cand.tif"
    write_tif(candp, cand, transform=tr)
    return {"sample": ss, "catalogue": catp, "cand": candp, "dir": tmp_path,
            "transform": tr, "shape": (h, w)}


def test_clean_candidate_certifies(data, tmp_path):
    ledger = tmp_path / "empty_ledger.csv"
    ledger.write_text("id,sha256,sha256_zeros\n", encoding="utf-8")
    rep = validate(data["cand"], sample_submission=data["sample"],
                   catalogue=data["catalogue"], ledger_csv=ledger,
                   axis="MASS", reread=False)
    assert rep.failed == [], rep.gates
    assert rep.verdict == "CERTIFIED", rep.gates


def test_nan_inside_footprint_fails(data):
    arr = np.zeros(data["shape"], "float32")
    arr[20, 20] = 1.0
    arr[5, 5] = np.nan            # inside footprint, must fail
    arr[50:, :] = np.nan
    arr[:, 50:] = np.nan
    p = write_tif(data["dir"] / "bad_nan.tif", arr, transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["no_nan_inside_footprint"] == "FAIL"


def test_live_value_outside_footprint_fails(data):
    arr = np.zeros(data["shape"], "float32")
    arr[20, 20] = 1.0
    arr[55, 55] = 1.0             # outside the footprint, must fail
    arr[50:, :] = np.nan
    arr[:, 50:] = np.nan
    arr[55, 55] = 1.0
    p = write_tif(data["dir"] / "out.tif", arr, transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["nan_outside_footprint"] == "FAIL"


def test_values_above_one_fail(data):
    arr = np.zeros(data["shape"], "float32")
    arr[20, 20] = 1.5
    arr[50:, :] = np.nan
    arr[:, 50:] = np.nan
    p = write_tif(data["dir"] / "hi.tif", arr, transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["values_in_0_1"] == "FAIL"


def test_wrong_dtype_fails(data):
    arr = np.zeros(data["shape"], "uint8")
    arr[20, 20] = 1
    p = write_tif(data["dir"] / "u8.tif", arr, dtype="uint8",
                  transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["dtype"] == "FAIL"


def test_wrong_crs_fails(data):
    arr = np.zeros(data["shape"], "float32")
    arr[20, 20] = 1.0
    p = write_tif(data["dir"] / "crs.tif", arr, crs="EPSG:4326",
                  transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["crs"] == "FAIL"


def test_catalogue_mass_fails(data):
    arr = np.zeros(data["shape"], "float32")
    arr[10, 10] = 1.0             # exactly on a catalogue pixel
    arr[50:, :] = np.nan
    arr[:, 50:] = np.nan
    p = write_tif(data["dir"] / "cat.tif", arr, transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["zero_catalogue_mass"] == "FAIL"


def test_collar_within_3px_fails_for_non_prune(data):
    arr = np.zeros(data["shape"], "float32")
    arr[12, 12] = 1.0             # ~2.8 px from catalogue pixel (10,11)
    arr[50:, :] = np.nan
    arr[:, 50:] = np.nan
    p = write_tif(data["dir"] / "collar.tif", arr, transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], axis="MASS", reread=False)
    assert rep.gates["collar_ge_3px"] == "FAIL"


def test_collar_exempt_for_prune(data):
    arr = np.zeros(data["shape"], "float32")
    arr[12, 12] = 1.0
    arr[50:, :] = np.nan
    arr[:, 50:] = np.nan
    p = write_tif(data["dir"] / "collar_prune.tif", arr, transform=data["transform"])
    rep = validate(p, sample_submission=data["sample"],
                   catalogue=data["catalogue"], axis="PRUNE", reread=False)
    assert rep.gates["collar_ge_3px"] == "PASS"


def test_missing_catalogue_is_unverified_not_pass(data):
    rep = validate(data["cand"], sample_submission=data["sample"],
                   catalogue=None, axis="MASS", reread=False)
    assert rep.gates["zero_catalogue_mass"] == "UNVERIFIED"
    assert rep.gates["collar_ge_3px"] == "UNVERIFIED"
    assert rep.verdict != "CERTIFIED"


def test_missing_sample_submission_is_unverified(data):
    rep = validate(data["cand"], sample_submission=None,
                   catalogue=data["catalogue"], reread=False)
    assert rep.gates["no_nan_inside_footprint"] == "UNVERIFIED"
    assert rep.verdict != "CERTIFIED"


def test_ledger_dedupe_flags_known_hash(data, tmp_path):
    ledger = tmp_path / "ledger.csv"
    with open(ledger, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "sha256", "sha256_zeros"])
        w.writerow(["other", sha256_file(data["cand"]), ""])
    rep = validate(data["cand"], sample_submission=data["sample"],
                   catalogue=data["catalogue"], ledger_csv=ledger, reread=False)
    assert rep.gates["sha_unseen"] == "FAIL"


def test_min_distance_to_mask_exactness():
    m = np.zeros((11, 11), bool)
    m[5, 5] = True
    t = np.zeros((11, 11), bool)
    t[5, 5] = True
    t[5, 8] = True
    t[0, 0] = True
    d = min_distance_to_mask(m, t, max_px=5)
    # np.nonzero is row-major: (0,0) is 7.07 px away (beyond the 5 px window),
    # then (5,5) on-mask, then (5,8) at 3 px.
    assert list(d) == [np.inf, 0.0, 3.0]
