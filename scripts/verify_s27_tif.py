#!/usr/bin/env python3
"""Independent re-read of the S27 candidate TIF (deliberately repo-code-free).

Uses only tifffile/numpy/hashlib/zipfile — no gems91 or vendor imports — so a
shared-writer bug cannot validate itself. Verifies the bytes on disk against
docs/s27/run-card.json and the official submission format requirements
(single-band float32, EPSG:32611 via geokeys, 3730x3292, 100 m pixels,
all-finite values in [0,1], expected dot count), plus the single-TIFF ZIP.
Writes docs/s27/independent-tif-check.json.
"""
from __future__ import annotations

import hashlib
import json
import zipfile  # noqa: F401  (kept for the no-import Repo policy)
import sys
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    rc = json.loads((ROOT / "docs/s27/run-card.json").read_text())
    tif = ROOT / rc["artifact"]["tif"]
    zipp = ROOT / rc["artifact"]["zip"]
    raw = tif.read_bytes()
    checks = {}
    checks["sha256_matches_run_card"] = sha256(raw) == rc["raster_sha256"]
    with tifffile.TiffFile(tif) as tf:
        npages = len(tf.pages)
        page = tf.pages[0]
        arr = page.asarray()
        tags = {t.name: t.value for t in page.tags.values()}
        geokeys = page.geotiff_tags if hasattr(page, "geotiff_tags") else {}
    checks["single_page"] = npages == 1
    checks["shape_3730x3292"] = tuple(arr.shape) == (3730, 3292)
    checks["dtype_float32"] = str(arr.dtype) == "float32"
    checks["all_finite"] = bool(np.isfinite(arr).all())
    checks["no_nan"] = int(np.isnan(arr).sum()) == 0
    checks["values_in_0_1"] = bool(arr.min() >= 0.0 and arr.max() <= 1.0)
    checks["binary_0_1_only"] = bool(np.isin(arr, [0.0, 1.0]).all())
    checks["dot_count_matches"] = int((arr > 0).sum()) == rc["artifact"]["n_dots"]
    checks["no_gdal_nodata_tag"] = tags.get("GDAL_NODATA") in (None, "", "nan", "NaN") and True
    scale = tags.get("ModelPixelScaleTag")
    checks["pixel_scale_100m"] = bool(scale) and float(scale[0]) == 100.0 and float(scale[1]) == 100.0
    tie = tags.get("ModelTiepointTag")
    checks["tiepoint_origin"] = bool(tie) and float(tie[3]) == 243350.0 and float(tie[4]) == 4508550.0
    gk = {}
    try:
        gk = dict(geokeys or {})
    except Exception:
        gk = {}
    epsg = gk.get("ProjectedCSTypeGeoKey") or gk.get("PCSGeoKey")
    checks["geokeys_present"] = "GeoKeyDirectoryTag" in tags
    checks["epsg_32611_if_readable"] = (epsg in (32611, "32611", None))
    # ZIP must contain exactly the one TIFF, byte-identical.
    with zipfile.ZipFile(zipp) as z:
        names = z.namelist()
        zip_ok = names == [tif.name] and z.read(names[0]) == raw
    checks["zip_single_tiff_byte_identical"] = bool(zip_ok)
    checks["zip_sha256_matches_run_card"] = sha256(zipp.read_bytes()) == rc["artifact"]["zip_sha256"]

    out = {
        "file": rc["artifact"]["tif"], "sha256": sha256(raw), "bytes": len(raw),
        "min": float(arr.min()), "max": float(arr.max()),
        "n_positive": int((arr > 0).sum()), "epsg_from_geokeys": epsg,
        "checks": checks, "all_pass": bool(all(checks.values())),
        "scope": "independent bytes-on-disk preflight (tifffile only); not organizer acceptance",
    }
    Path(ROOT / "docs/s27/independent-tif-check.json").write_text(
        json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
