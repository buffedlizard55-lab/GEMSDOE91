#!/usr/bin/env python3
"""Independently re-read the historical S16-PC91 TIFF and ZIP.

This is a format/evidence verifier only. It never approves a competition slot:
``ok_to_submit`` is always false. Missing local pinned data returns a structured
BLOCKED result, while malformed or invalid candidate bytes return FAIL.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_pinned_inputs(root: Path) -> tuple[Path, Path]:
    manifest_path = root / "registry/data_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing pinned data manifest: {manifest_path.relative_to(root)}")
    manifest = json.loads(manifest_path.read_text())
    pins = {row["id"]: row for row in manifest["files"]}
    result = {}
    for key in ("sample_submission", "existing_faults"):
        pin = pins[key]
        path = root / "data" / pin["local_subpath"]
        display_path = path.relative_to(root)
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned {key}: {display_path}")
        if path.stat().st_size != pin["bytes"] or sha(path) != pin["sha256"]:
            raise ValueError(f"pinned {key} hash/byte-count mismatch: {display_path}")
        result[key] = path
    return result["sample_submission"], result["existing_faults"]


def verify(root: Path = ROOT) -> dict:
    root = Path(root)
    card_path = root / "docs/run-card-S16PC.json"
    if not card_path.is_file():
        raise FileNotFoundError(f"missing S16-PC91 run card: {card_path.relative_to(root)}")
    card = json.loads(card_path.read_text())
    name = card["submission_name"]
    if not isinstance(name, str) or not name or Path(name).name != name or ".." in name:
        raise ValueError("unsafe or missing submission name in run card")

    tif_path = root / "docs/downloads" / f"{name}-zeros.tif"
    zip_path = root / "docs/downloads" / f"{name}-zeros.zip"
    if not tif_path.is_file():
        raise FileNotFoundError(f"missing candidate TIFF: {tif_path.relative_to(root)}")
    if not zip_path.is_file():
        raise FileNotFoundError(f"missing single-TIFF ZIP: {zip_path.relative_to(root)}")

    sample_path, catalogue_path = _read_pinned_inputs(root)
    disk_sha = sha(tif_path)
    with rasterio.open(sample_path) as sample:
        ref = sample.read(1)
        ref_meta = (sample.count, sample.shape, sample.crs, sample.transform)
    footprint = np.isfinite(ref)
    with rasterio.open(catalogue_path) as source:
        catalogue = (np.nan_to_num(source.read(1), nan=0.0) > 0) & footprint
        catalogue_meta = (source.count, source.shape, source.crs, source.transform)
    if catalogue_meta != ref_meta:
        raise ValueError("pinned catalogue grid differs from pinned sample grid")

    with rasterio.open(tif_path) as candidate:
        values = candidate.read(1)
        meta = (candidate.count, candidate.shape, candidate.crs, candidate.transform)
        one_band = candidate.count == 1
        float32 = candidate.dtypes == ("float32",)
        no_nodata_tag = candidate.nodata is None

    finite = np.isfinite(values)
    all_finite = bool(finite.all())
    if finite.any():
        finite_values = values[finite]
        minimum = float(finite_values.min())
        maximum = float(finite_values.max())
    else:
        minimum = maximum = None
    values_in_range = bool(
        all_finite and minimum is not None and minimum >= 0.0 and maximum <= 1.0
    )
    dots = (values > 0) & footprint
    zero_outside_footprint = bool(np.all(values[~footprint] == 0.0))
    dot_values = np.unique(values[dots])
    binary_unit_dots = bool(dots.any() and np.array_equal(dot_values, np.array([1.0], dtype=values.dtype)))
    distance = ndi.distance_transform_edt(~catalogue)
    minimum_catalogue_distance = float(distance[dots].min()) if dots.any() else None

    zip_single_member = False
    zip_inner_sha_match = False
    zip_error = None
    try:
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.namelist()
            zip_single_member = members == [tif_path.name]
            if zip_single_member:
                zip_inner_sha_match = hashlib.sha256(archive.read(tif_path.name)).hexdigest() == disk_sha
    except zipfile.BadZipFile as exc:
        zip_error = str(exc)

    checks = {
        "sha_disk_equals_run_card": disk_sha == card.get("raster_sha256"),
        "crs_match": meta[2] == ref_meta[2],
        "shape_match": meta[1] == ref_meta[1],
        "transform_match": meta[3] == ref_meta[3],
        "dtype_float32": float32,
        "one_band": one_band,
        "nodata_none": no_nodata_tag,
        "all_cells_finite": all_finite,
        "values_in_0_1": values_in_range,
        "nan_cells_zero": int(np.isnan(values).sum()) == 0,
        "zero_outside_footprint": zero_outside_footprint,
        "dots_on_catalogue_zero": int((dots & catalogue).sum()) == 0,
        "min_catalogue_distance_gt_3px": bool(
            minimum_catalogue_distance is not None and minimum_catalogue_distance > 3.0
        ),
        "binary_unit_dots": binary_unit_dots,
        "zip_single_member": zip_single_member,
        "zip_inner_sha_match": zip_inner_sha_match,
    }
    format_pass = bool(all(checks.values()))
    return {
        "status": "PASS" if format_pass else "FAIL",
        "scope": "Independent TIFF/ZIP byte, range, grid, footprint and catalogue checks; not a submission selector",
        "candidate": name,
        "sha256": disk_sha,
        "checks": checks,
        "min_value": minimum,
        "max_value": maximum,
        "n_dots": int(dots.sum()),
        "min_catalogue_distance_px": minimum_catalogue_distance,
        "zip_error": zip_error,
        "format_pass": format_pass,
        "ok_to_download": format_pass,
        "ok_to_submit": False,
        "submission_ready": False,
        "run_card_verdict": card.get("verdict"),
        "reason": "A research download is cleared only when all independent format checks pass. Format verification never grants submission approval.",
    }


def main(root: Path | None = None) -> int:
    root = ROOT if root is None else Path(root)
    try:
        report = verify(root)
    except FileNotFoundError as exc:
        report = {
            "status": "BLOCKED",
            "ok_to_download": None,
            "ok_to_submit": False,
            "submission_ready": False,
            "error": str(exc),
        }
    except (OSError, ValueError, KeyError, rasterio.errors.RasterioError) as exc:
        report = {
            "status": "FAIL",
            "ok_to_download": False,
            "ok_to_submit": False,
            "submission_ready": False,
            "error": str(exc),
        }

    evidence = root / "evidence/s16pc_independent_check.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
