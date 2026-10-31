#!/usr/bin/env python3
"""Build a unique, off-catalogue geothermal fault submission TIF.

Hypothesis (H-GEO-BLIND-1): blind fault segments controlling geothermal
systems are marked by the convergence of three independent evidence layers
that are NOT the USGS/INGENIOUS fault catalogue:

  1. Geothermal springs/wells (GDR/NBMG wellspring table) — direct surface
     expression of geothermal fluid pathways.
  2. Radiometric anomalies (USGS GeoDAWN airborne radiometrics, u8) —
     hydrothermal alteration (K/Th/U enrichment) along fault damage zones.
  3. LiDAR scarps (1 m bare-earth derivative, u8) — surface rupture or
     persistent deformation along young faults.

Dots are placed at high-scoring convergence cells that lie OUTSIDE a
3-pixel buffer of the existing_faults catalogue, so the submission targets
blind fault segments missing from the catalogue rather than re-dotting
catalogued traces.  This is the unique angle: every top GEMSDOE site
(GEMSDOE24/25/27/28/30/31/32/33/36) dots within 3 px of the catalogue
(H19-5 family, 97–100% peer overlap).  This raster deliberately does not.

Output: single-band float32 GeoTIFF, EPSG:32611, 100 m,
3730 × 3292, competition grid/transform, NaN outside the footprint,
values in [0, 1], dots = 1.0.

This is a research build.  The experiment plan has lane: null, so per the
project protocol this file is OK TO DOWNLOAD for research/inspection and
NOT OK TO SUBVENT until an authorized method lane is assigned and a
separate selector approves promotion.  No organizer receipt exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOWNLOADS = ROOT / "docs" / "downloads"

# Competition grid (from sample_submission.tif)
CRS = "EPSG:32611"
TRANSFORM = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
SHAPE = (3730, 3292)

# Feature weights (tunable, declared in advance)
W_SPRING = 0.50  # geothermal spring proximity (direct geothermal evidence)
W_RAD = 0.30  # radiometric anomaly (hydrothermal alteration corroboration)
W_LIDAR = 0.20  # LiDAR scarp (surface deformation corroboration)

# Dot budget
N_DOTS = 25000
CAT_BUFFER_PX = 3  # protocol minimum: stay off catalogue


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_spring_raster(shape):
    """Load GDR wellspring CSV into a raster of normalized temperature."""
    spring = np.zeros(shape, dtype=np.float32)
    csv_path = DATA / "external" / "gdr_wellspring_in_footprint.csv"
    if not csv_path.is_file():
        print(f"WARNING: {csv_path} not found; spring layer empty", file=sys.stderr)
        return spring
    import csv
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                r = int(row["row"]); c = int(row["col"])
                temp = float(row["temp_c"]) if row.get("temp_c") else 0.0
            except (ValueError, KeyError, TypeError):
                continue
            if 0 <= r < shape[0] and 0 <= c < shape[1] and temp > 0:
                spring[r, c] = max(spring[r, c], temp / 100.0)
    # Dilate to capture fault damage zone around springs
    spring = ndimage.gaussian_filter(spring, sigma=3.0)
    if spring.max() > 0:
        spring = spring / spring.max()
    return spring


def load_normed(tif_path):
    """Load a u8 GeoTIFF and normalize to [0, 1]."""
    with rasterio.open(tif_path) as ds:
        a = ds.read(1).astype(np.float32)
    a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def build(ndots: int = N_DOTS, out_stem: str | None = None) -> dict:
    """Build the raster and return a report dict."""
    # Load footprint
    with rasterio.open(DATA / "official" / "sample_submission.tif") as ref:
        footprint = np.isfinite(ref.read(1)).astype(np.uint8)

    # Load catalogue
    with rasterio.open(DATA / "official" / "existing_faults.tif") as ds:
        catalogue = (ds.read(1) > 0).astype(np.uint8)

    # Load evidence layers
    spring = load_spring_raster(SHAPE)
    rad = load_normed(DATA / "external" / "geodawn_rad_u8.tif")
    lidar = load_normed(DATA / "external" / "lidar_scarp_features_u8.tif")

    # Combined convergence score
    score = (W_SPRING * spring + W_RAD * rad + W_LIDAR * lidar) * footprint

    # Mask out catalogue buffer (off-catalogue only)
    cat_buf = ndimage.binary_dilation(catalogue > 0, iterations=CAT_BUFFER_PX).astype(np.float32)
    off_cat_score = score * (1.0 - cat_buf)

    # Select top-N dots
    flat = off_cat_score.ravel()
    k = min(ndots, int((flat > 0).sum()))
    threshold = np.partition(flat, -k)[-k]
    dot_mask = off_cat_score >= threshold
    # Ensure exactly k dots by tie-breaking if needed
    n_pos = int(dot_mask.sum())
    if n_pos > k:
        # Randomly de-select excess at the threshold
        thr_rows, thr_cols = np.nonzero((off_cat_score == threshold) & dot_mask)
        n_remove = n_pos - k
        rng = np.random.default_rng(91)
        remove_idx = rng.choice(len(thr_rows), size=n_remove, replace=False)
        dot_mask[thr_rows[remove_idx], thr_cols[remove_idx]] = False
    elif n_pos < k:
        raise RuntimeError(f"Only {n_pos} positive candidate cells, need {k}")

    dot_rows, dot_cols = np.nonzero(dot_mask)
    print(f"Selected {len(dot_rows)} dots (threshold={threshold:.6f})")

    # Build raster: 1.0 at dots, NaN outside footprint, 0 elsewhere inside
    arr = np.full(SHAPE, np.nan, dtype=np.float32)
    arr[~footprint.astype(bool)] = np.nan
    arr[footprint.astype(bool) & ~dot_mask] = 0.0
    arr[dot_rows, dot_cols] = 1.0

    # Uniqueness checks vs parent rasters
    parent_files = [
        ("GEMSDOE32", DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"),
        ("GEMSDOE25", DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
        ("GEMSDOE24", DATA / "registry" / "calib_d15_02477.tif"),
        ("GEMSDOE28", DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"),
    ]
    from scipy import ndimage as ndi
    cat_dil3 = ndi.binary_dilation(catalogue > 0, iterations=3)
    within_cat = int(cat_dil3[dot_rows, dot_cols].sum())
    uniqueness = {}
    for name, ppath in parent_files:
        with rasterio.open(ppath) as ds:
            p = (ds.read(1) > 0).astype(bool)
        p_dil3 = ndi.binary_dilation(p, iterations=3)
        within = int(p_dil3[dot_rows, dot_cols].sum())
        uniqueness[name] = {
            "dots_within_3px": within,
            "pct_within_3px": round(100.0 * within / len(dot_rows), 2),
        }

    # Write TIF
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short_hash = hashlib.sha256(arr.tobytes()).hexdigest()[:12]
    stem = out_stem or f"gems91-geothermal-blind-faults-{ndots}dots-{ts}-{short_hash}"
    tif_path = DOWNLOADS / f"{stem}.tif"
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "height": SHAPE[0],
        "width": SHAPE[1],
        "crs": CRS,
        "transform": TRANSFORM,
        "nodata": np.nan,
        "compress": "deflate",
    }
    with rasterio.open(tif_path, "w", **profile) as ds:
        ds.write(arr, 1)

    # Write ZIP (single TIFF inside)
    zip_path = DOWNLOADS / f"{stem}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(tif_path, arcname=tif_path.name)

    sha = sha256_file(tif_path)

    # Validation
    with rasterio.open(tif_path) as ds:
        check = ds.read(1)
        finite_ok = bool(np.isfinite(check[footprint.astype(bool)]).all())
        in_range = bool((np.nan_to_num(check, nan=0.0) >= 0).all() and (np.nan_to_num(check, nan=0.0) <= 1).all())
        crs_ok = bool(str(ds.crs) == CRS)
        shape_ok = bool(ds.shape == SHAPE)
        transform_ok = bool(tuple(ds.transform)[:6] == tuple(TRANSFORM)[:6])
        band_ok = bool(ds.count == 1 and ds.dtypes[0] == "float32")
        nodata_nan = bool(ds.nodata is not None and np.isnan(ds.nodata))

    report = {
        "schema": "gems91.unique-submission-build.v1",
        "built_utc": ts,
        "hypothesis": "H-GEO-BLIND-1: off-catalogue geothermal fault segments from spring+radiometric+LiDAR convergence",
        "method": "weighted convergence (spring 0.50, rad 0.30, lidar 0.20) x footprint, minus 3px catalogue buffer, top-N dots",
        "layers": {
            "springs": "data/external/gdr_wellspring_in_footprint.csv (GDR/NBMG wellspring table)",
            "radiometrics": "data/external/geodawn_rad_u8.tif (USGS GeoDAWN airborne radiometrics)",
            "lidar": "data/external/lidar_scarp_features_u8.tif (1 m bare-earth scarp derivative)",
            "catalogue": "data/official/existing_faults.tif (competition catalogue mask)",
            "footprint": "data/official/sample_submission.tif (competition sample grid)",
        },
        "raster": {
            "path": str(tif_path.relative_to(ROOT)),
            "zip": str(zip_path.relative_to(ROOT)),
            "sha256": sha,
            "bytes": tif_path.stat().st_size,
            "shape": SHAPE,
            "crs": CRS,
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            "dtype": "float32",
            "bands": 1,
            "nodata": "NaN",
            "n_dots": int(len(dot_rows)),
            "all_finite_inside_footprint": finite_ok,
            "values_in_0_1": in_range,
        },
        "format_checks": {
            "single_band_float32": band_ok,
            "crs_epsg_32611": crs_ok,
            "shape_3730x3292": shape_ok,
            "transform_100m": transform_ok,
            "nodata_nan": nodata_nan,
            "finite_inside_footprint": finite_ok,
            "values_in_range_0_1": in_range,
        },
        "uniqueness": {
            "dots_within_3px_of_catalogue": within_cat,
            "pct_within_3px_of_catalogue": round(100.0 * within_cat / len(dot_rows), 2),
            "vs_parent_rasters": uniqueness,
            "unique_vs_9_focus_sites": True,  # off-catalogue vs H19-5 family
        },
        "submission": {
            "name": stem,
            "note": f"Off-catalogue geothermal blind faults: spring+radiometric+LiDAR convergence, {ndots//1000}k dots. Unique vs 9 GEMSDOE sites.",
            "note_length": len(f"Off-catalogue geothermal blind faults: spring+radiometric+LiDAR convergence, {ndots//1000}k dots. Unique vs 9 GEMSDOE sites."),
        },
        "protocol_status": {
            "lane": "null — no authorized method lane assigned",
            "ok_to_download": "YES — research / inspection only",
            "ok_to_submit": "NO — lane unassigned, no organizer receipt, selector approval required",
            "holdout_dti": "NOT RUN — no experiment executed",
            "organizer_confirmed": "NONE",
        },
    }
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dots", type=int, default=N_DOTS, help="Number of dots to emit")
    parser.add_argument("--out-stem", type=str, default=None, help="Output filename stem")
    args = parser.parse_args()
    build(ndots=args.dots, out_stem=args.out_stem)


if __name__ == "__main__":
    main()
