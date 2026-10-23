"""Derive the catalogue mask from the training labels.

The organizer states that known USGS/INGENIOUS fault pixels are masked
pixel-exactly, identical to the training labels (forum thread 11516). The parent
lineage used the same thing: its manifest reports ``dots_on_catalogue: 0`` against
``labels.tif``, and that is reproducible here.

    labels.tif: int8, -1 outside footprint, 0 negative, 1 known-fault pixel
    catalogue.tif: uint8 1 where labels > 0, else 0

Deterministic; no model, no threshold, no label probing (the mask is the known
catalogue, never the withheld new-fault truth).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio


def main(argv: list[str]) -> int:
    src = Path(argv[0] if argv else "data/labels.tif")
    dst = Path(argv[1] if len(argv) > 1 else "data/catalogue.tif")
    with rasterio.open(src) as s:
        lab = s.read(1)
        profile = s.profile.copy()
    cat = (lab > 0).astype("uint8")
    profile.update(dtype="uint8", count=1, nodata=None, compress="deflate")
    with rasterio.open(dst, "w", **profile) as d:
        d.write(cat, 1)
    print(f"{dst}: {int(cat.sum())} catalogue pixels (from {src})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
