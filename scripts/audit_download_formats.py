#!/usr/bin/env python3
"""Format audit for every research GeoTIFF in docs/downloads/.

Reads each raster and records CRS, shape, dtype, band count, nodata tag,
NaN count, value range, and the count of exact 1.0 cells. Pairs of
`-nan` / `-zeros` twins are reported so the range-error hypothesis
(NaN outside the footprint fails a [0, 1] check) can be tested directly.

Usage: .venv/bin/python scripts/audit_download_formats.py
Writes docs/review-20261030/tif-format-audit.json.
"""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "review-20261030" / "tif-format-audit.json"


def audit(path: Path) -> dict:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype("float64")
        finite = a[np.isfinite(a)]
        return {
            "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "crs": str(ds.crs),
            "height": ds.height,
            "width": ds.width,
            "res": list(ds.res),
            "dtype": ds.dtypes[0],
            "bands": ds.count,
            "nodata": None if ds.nodata is None else str(ds.nodata),
            "nan_cells": int(np.isnan(a).sum()),
            "min_finite": float(finite.min()) if finite.size else None,
            "max_finite": float(finite.max()) if finite.size else None,
            "ones": int((finite == 1.0).sum()),
            "all_finite_in_0_1": bool(finite.size == a.size and finite.min() >= 0 and finite.max() <= 1),
        }


def main() -> None:
    paths = sorted(Path(p) for p in glob.glob(str(ROOT / "docs" / "downloads" / "*.tif")))
    rows = [audit(p) for p in paths]
    nan_twins = [r["file"] for r in rows if r["nan_cells"] > 0]
    summary = {
        "files": len(rows),
        "with_nan_cells": len(nan_twins),
        "all_finite_in_0_1": sum(r["all_finite_in_0_1"] for r in rows),
        "nan_files": nan_twins,
        "note": (
            "Files with nan_cells > 0 carry NaN outside the footprint. This is the "
            "likely cause of 'Predicted values must be in range [0, 1]' (inference, "
            "not reproduced: the organizer validator is not accessible)."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
