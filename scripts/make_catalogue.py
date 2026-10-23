"""Derive the catalogue mask from the existing-faults (training labels) raster.

The organizer states that known USGS/INGENIOUS fault pixels are masked
pixel-exactly, identical to the training labels (forum thread 11516). The parent
lineage used the same thing: its manifest reports ``dots_on_catalogue: 0`` against
this raster, reproducible here.

    existing_faults.tif (a.k.a labels.tif): int8, -1 outside footprint, 0, 1
    catalogue.tif: uint8 1 where labels > 0, else 0

Deterministic; no model, no threshold, no label probing (the mask is the known
catalogue, never the withheld new-fault truth).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio

SRC = "data/official/existing_faults.tif"
DST = "data/derived/catalogue_mask.tif"


def main(argv: list[str]) -> int:
    src = Path(argv[0] if argv else SRC)
    dst = Path(argv[1] if len(argv) > 1 else DST)
    with rasterio.open(src) as s:
        lab = s.read(1)
        profile = s.profile.copy()
    cat = (lab > 0).astype("uint8")
    profile.update(dtype="uint8", count=1, nodata=None, compress="deflate")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(dst, "w", **profile) as d:
        d.write(cat, 1)
    print(f"{dst}: {int(cat.sum())} catalogue pixels (from {src})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
