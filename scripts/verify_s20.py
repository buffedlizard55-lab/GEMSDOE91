#!/usr/bin/env python3
"""Re-verify Session 20 (`S20-RHTW`) published bytes and measured evidence; no scientific rerun.

Exit zero means the `S20-RHTW` research deliverable is internally consistent,
byte-verified by two independent TIFF decoders (`tifffile` + `rasterio`), and
auditable. It NEVER means permission to upload to DrivenData: `ok_to_submit` is
read separately and remains `False`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
import tifffile
from scipy.ndimage import distance_transform_edt as edt

from scripts.verify_current_artifact import published_path


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(with_data: bool = False) -> dict:
    card = read_json("docs/run-card-S20-RHTW.json")
    r = card["raster"]
    tif = published_path(r["path"].removeprefix("docs/"))
    zipped = published_path(r["zip"].removeprefix("docs/"))
    receipt = read_json(r["receipt"])

    require(sha(tif) == card["raster_sha256"] == r["sha256"] == receipt["sha256"], "TIFF SHA-256 mismatch")
    require(sha(zipped) == r["zip_sha256"] == receipt["zip_sha256"], "ZIP SHA-256 mismatch")
    require(tif.stat().st_size == r["bytes"] == receipt["bytes"], "TIFF byte count mismatch")
    require(zipped.stat().st_size == r["zip_bytes"], "ZIP byte count mismatch")
    require((tif.stat().st_mode & 0o777) == 0o644, "TIFF permissions must be 0644")
    require((zipped.stat().st_mode & 0o777) == 0o644, "ZIP permissions must be 0644")

    with zipfile.ZipFile(zipped) as zf:
        require(zf.namelist() == [tif.name], "ZIP must contain exactly one root-level GeoTIFF")
        require(zf.read(tif.name) == tif.read_bytes(), "ZIP GeoTIFF bytes differ from standalone GeoTIFF")

    require(card["submission_name"] == receipt["submission_name"], "submission_name drift")
    require(card["submission_note"] == receipt["note"], "submission_note drift vs writer receipt")
    require(0 < len(card["submission_note"]) <= 140, "submission_note must be 1..140 chars")
    require(len(card["submission_note"]) == card["submission_note_chars"], "submission_note_chars mismatch")

    # Independent TIFF decoder #1 (tifffile) + #2 (rasterio)
    arr = tifffile.imread(tif)
    require(arr.shape == (3730, 3292) and arr.dtype == np.float32, "TIFF array shape/dtype mismatch")
    require(bool(np.isfinite(arr).all()), "Non-finite NaN/Inf cell in GeoTIFF")
    require(float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, "Values outside [0, 1]")
    require(bool(np.isin(arr, [0.0, 1.0]).all()), "S20-RHTW binary dot artifact must contain only {0.0, 1.0}")
    require(int((arr > 0).sum()) == card["validator_output"]["emitted_positive_pixels"] == 37654, "Positive dot count mismatch")

    with rasterio.open(tif) as s:
        require(s.count == 1 and s.dtypes == ("float32",) and str(s.crs) == "EPSG:32611", "Band/dtype/CRS mismatch")
        require(tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0), "Affine transform mismatch")
        require(s.nodata is None, "GeoTIFF must not carry a sentinel nodata tag")
        require(np.array_equal(s.read(1), arr), "rasterio vs tifffile pixel decode mismatch")
        actual_meta = (s.count, s.shape, s.crs, s.transform)

    # Preregistration & shared template pins
    prereg_path = ROOT / card["preregistration"]
    require(prereg_path.is_file() and sha(prereg_path) == card["preregistration_sha256"], "Preregistration SHA-256 drift")
    tpin = read_json("registry/template_pin.json")
    for fname, expected_sha in tpin["sha256"].items():
        require(sha(ROOT / "vendor/gems57" / fname) == expected_sha, f"Shared template file modified: {fname}")

    # Holdout, canary, uniqueness, and fail-closed selector invariants
    i2 = card["holdout"]["primary_i2"]
    i1 = card["holdout"]["secondary_i1_isolated"]
    require(i2["evidence_class"] == "HOLDOUT-DTI" and i2["evaluator_version"] == "gems57-pooled-hide-v2", "I2 label mismatch")
    require(i2["withheld_positive_pixels"] == 11321, "I2 withheld positive count mismatch")
    require(i2["scores"]["E3"]["dti"] > i2["scores"]["E0"]["dti"], "E3 must exceed E0 on I2")
    require(i2["paired_winner_minus"]["E0"]["ci95"][0] > 0.0, "E3 - E0 paired 95% CI lower bound must exceed 0 on I2")
    require(i1["scores"]["S20_OOF"]["dti"] > i1["scores"]["E0"]["dti"], "S20_OOF must exceed E0 on I1")
    require(i1["paired_s20_minus_e0"]["ci95"][0] > 0.0, "S20_OOF - E0 paired 95% CI lower bound must exceed 0 on I1")

    can = card["leakage_canary"]
    require(can["all_pass"] is True and can["worst"]["symmetric_auc"] <= 0.90, "Leakage canary breach")
    uniq = card["uniqueness"]
    require(uniq["surface_before_placement_max_abs_spearman"] <= 0.90, "Pre-placement Spearman breach")
    require(uniq["dots_within_3px_vs_gemsdoe32_r0"] <= 0.70, "R0 3-px dot overlap breach")
    require(uniq["dots_max_within_3px_non_blanket"] <= 0.70, "Non-blanket 3-px dot overlap breach")

    require(card["ok_to_download"] is True, "ok_to_download must be True")
    require(card["ok_to_submit"] is False and card["submission_ready"] is False, "Negative/unapproved candidate promoted")
    require(card["result"] == "negative" and card["verdict"]["promote"] is False, "Rule 6 fail-closed verdict violated")
    require(card["slots_used"] == 0 and card["budget"]["experiments_run"] <= 3, "Budget/slot invariant violated")
    require(card["organizer_confirmed"] is None, "Unverified organizer_confirmed claim")

    if with_data:
        pin_rows = {row["id"]: row for row in read_json("registry/data_manifest.json")["files"]}
        for key in ("sample_submission", "existing_faults"):
            path = ROOT / "data" / pin_rows[key]["local_subpath"]
            require(sha(path) == card["inputs"][key]["sha256"], f"{key} SHA-256 mismatch vs pinned input")
        with rasterio.open(ROOT / "data" / pin_rows["sample_submission"]["local_subpath"]) as s:
            require((s.count, s.shape, s.crs, s.transform) == actual_meta, "Template grid mismatch")
            fp = np.isfinite(s.read(1))
        require(float(np.abs(arr[~fp]).max()) == 0.0, "Non-zero predictions outside competition footprint")
        with rasterio.open(ROOT / "data" / pin_rows["existing_faults"]["local_subpath"]) as s:
            raw_cat = s.read(1)
            cat = np.isfinite(raw_cat) & (raw_cat > 0) & fp
        require(int((arr[cat] > 0).sum()) == 0, "Predicted dots overlap mapped catalogue pixels")
        d_cat = edt(~cat)
        min_d_cat = float(d_cat[arr > 0].min())
        require(min_d_cat > 2.0, f"Minimum distance to catalogue too small: {min_d_cat:.4f} px")

    return {
        "status": "PASS",
        "lane": card["lane"],
        "raster_sha256": card["raster_sha256"],
        "zip_sha256": r["zip_sha256"],
        "positive_pixels": 37654,
        "ok_to_download": card["ok_to_download"],
        "ok_to_submit": card["ok_to_submit"],
        "with_data": with_data,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--with-data", action="store_true", help="Also verify against pinned sample_submission & existing_faults")
    args = ap.parse_args()
    report = verify(with_data=args.with_data)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
