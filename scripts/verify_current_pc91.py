#!/usr/bin/env python3
"""Independently re-read the current PC91 research TIFF without training data.

This verifies file identity, GeoTIFF metadata, finite [0,1] values and ZIP byte
identity. It deliberately reports template-grid and catalogue checks as blocked
when the protected competition reference rasters are absent.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify() -> dict:
    card = json.loads((ROOT / "docs/run-card-S16PC.json").read_text(encoding="utf-8"))
    name = card["submission_name"]
    tif = ROOT / "docs/downloads" / f"{name}-zeros.tif"
    zip_path = tif.with_suffix(".zip")
    if not tif.is_file() or not zip_path.is_file():
        raise FileNotFoundError("Current PC91 TIFF or ZIP is missing")

    digest = sha256(tif)
    with rasterio.open(tif) as src:
        values = src.read(1)
        checks = {
            "sha_matches_run_card": digest == card["raster_sha256"],
            "one_band": src.count == 1,
            "dtype_float32": src.dtypes[0] == "float32",
            "shape": list(src.shape),
            "crs": str(src.crs),
            "transform": list(src.transform)[:6],
            "nodata_none": src.nodata is None,
            "all_cells_finite": bool(np.isfinite(values).all()),
            "min_value": float(values.min()),
            "max_value": float(values.max()),
            "values_in_0_1": bool(float(values.min()) >= 0 and float(values.max()) <= 1),
            "positive_cells": int((values > 0).sum()),
            "positive_values_are_unit": bool(np.array_equal(np.unique(values[values > 0]), np.array([1.0], dtype=values.dtype))),
        }
    with zipfile.ZipFile(zip_path) as archive:
        members = archive.namelist()
        checks["zip_member_count"] = len(members)
        checks["zip_single_tif"] = len(members) == 1 and members[0].lower().endswith(".tif")
        checks["zip_inner_sha_matches_tif"] = bool(
            len(members) == 1 and hashlib.sha256(archive.read(members[0])).hexdigest() == digest
        )

    sample = ROOT / "data/official/sample_submission.tif"
    checks["sample_grid_match"] = None
    checks["sample_grid_match_blocker"] = "reference sample raster absent" if not sample.is_file() else None
    # This utility purposely does not make a catalogue claim; labels are absent too.
    checks["catalogue_exclusion_check"] = "NOT RUN: existing_faults.tif absent from data/"
    checks["sha256"] = digest
    checks["bytes"] = tif.stat().st_size
    check_keys = (
        "sha_matches_run_card", "one_band", "dtype_float32", "nodata_none",
        "all_cells_finite", "values_in_0_1", "positive_values_are_unit",
        "zip_single_tif", "zip_inner_sha_matches_tif",
    )
    checks["status"] = "PASS_PARTIAL_GRID_UNAVAILABLE" if all(checks[k] for k in check_keys) else "FAIL"
    checks["ok_to_download"] = card["ok_to_download"]
    checks["ok_to_submit"] = card["ok_to_submit"]
    return checks


def main() -> int:
    result = verify()
    (ROOT / "evidence/current_review_tif_check.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
