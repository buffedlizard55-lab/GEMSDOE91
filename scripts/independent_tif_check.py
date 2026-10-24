#!/usr/bin/env python3
"""Independent check of every downloadable GeoTIFF in docs/downloads/.

Deliberately does NOT import any repo module (no shared-code risk). Uses only
numpy, tifffile (+ imagecodecs for the float predictor) and scipy.

Checks per file: sha256, dtype, shape, band count, nodata tag, NaN/inf counts,
min/max, positive-pixel count, geotiff tags.
Pairwise: fraction of A's positive pixels within 3 px of B's positive pixels
(the lane protocol's dot-overlap statistic; > 0.70 = duplicate).

Usage:  python scripts/independent_tif_check.py
Writes: evidence/s13_independent_tif_check.json
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "s13_independent_tif_check.json"


def main() -> None:
    files = sorted(glob.glob(str(ROOT / "docs" / "downloads" / "*.tif")))
    rows, dots = [], {}
    for f in files:
        raw = open(f, "rb").read()
        with tifffile.TiffFile(f) as tf:
            npages = len(tf.pages)
            page = tf.pages[0]
            arr = page.asarray().astype(np.float64)
            tags = {t.name: t.value for t in page.tags.values()}
        finite = np.isfinite(arr)
        pos = (arr > 0) & finite
        name = os.path.basename(f)
        dots[name] = pos
        rows.append({
            "file": name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "shape": list(arr.shape),
            "dtype": str(page.dtype),
            "bands": npages,
            "nodata_tag": tags.get("GDAL_NODATA"),
            "n_nan": int(np.isnan(arr).sum()),
            "n_inf": int(np.isinf(arr).sum()),
            "min": float(arr[finite].min()),
            "max": float(arr[finite].max()),
            "n_positive": int(pos.sum()),
            "model_pixel_scale": list(tags["ModelPixelScaleTag"]) if "ModelPixelScaleTag" in tags else None,
            "model_tiepoint": list(tags["ModelTiepointTag"]) if "ModelTiepointTag" in tags else None,
            "has_geokeys": "GeoKeyDirectoryTag" in tags,
            "range_0_1_and_finite": bool(finite.all() and arr.min() >= 0 and arr.max() <= 1),
        })

    names = list(dots)
    overlap = {}
    for a in names:
        for b in names:
            if a == b or dots[a].shape != dots[b].shape or not dots[a].any():
                continue
            dist_to_b = ndimage.distance_transform_edt(~dots[b])
            overlap[f"{a} -> {b}"] = round(float((dist_to_b[dots[a]] <= 3).mean()), 4)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "checker": "scripts/independent_tif_check.py",
        "note": "Independent of repo validators. Overlap > 0.70 = duplicate under the lane protocol.",
        "files": rows,
        "dot_within_3px_of_second": overlap,
    }, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} files, {len(overlap)} ordered pairs")


if __name__ == "__main__":
    main()
