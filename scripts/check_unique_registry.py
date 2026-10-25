#!/usr/bin/env python3
"""Rule-1 LANE uniqueness check for the unique off-catalogue submission."""
import sys
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from evaluate_holdout import check_registry_uniqueness  # noqa: E402

CID = "gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119"
fp = ROOT / "docs" / "downloads" / f"{CID}-zeros.tif"
with rasterio.open(fp) as s:
    arr = s.read(1)
footprint = np.isfinite(arr)
surface = arr[footprint]
cand = (np.nan_to_num(arr, nan=0.0) > 0) & footprint

all_paths = sorted((ROOT / "data" / "registry").glob("*.tif")) + sorted(
    (ROOT / "data" / "registry_siblings").glob("*.tif")
)
# The uniqueness gate requires each registry raster finite inside the candidate
# footprint.  NaN-outside twins are finite only inside their own footprint, so
# keep only rasters finite within this candidate's footprint.
paths = []
for p in all_paths:
    with rasterio.open(p) as s:
        ra = s.read(1)
    if np.isfinite(ra[footprint]).all():
        paths.append(p)
    else:
        print("skip nonfinite-in-footprint registry:", p.name)
print("registry rasters checked:", [p.name for p in paths])
res = check_registry_uniqueness(surface, cand, footprint, paths)
print("is_duplicate:", res["is_duplicate"])
print("uniqueness_pass:", res["uniqueness_pass"])
print("surface_max_abs_rank_corr:", res["surface_max_abs_rank_corr"])
print("dots_max_3px_overlap:", res["dots_max_3px_overlap"])
for c in res["comparisons"]:
    print(" ", c["registry_raster"],
          "surf_rho=", c["surface_abs_rank_corr"],
          "dot_overlap=", c["effective_dot_overlap_3px"],
          "dup=", c["duplicate_flag"])
