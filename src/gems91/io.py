"""Raster IO for the competition grid: hashing, dot identity, encoding.

Grid (verified from the pinned template, not from memory):
    EPSG:32611, 3730 x 3292, 100 m, transform (100, 0, 243350, 0, -100, 4508550)
    float32, one band, values in [0, 1], NaN outside the footprint.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio
import tifffile

# Encoder settings copied from the parent artifact so that twins differ only in
# fill value.  Byte-identical re-encoding is NOT claimed: see IR-91-04.
WRITE_KWARGS = dict(compression="deflate", predictor=3, tile=(256, 256))


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read_grid(path: str | Path) -> np.ndarray:
    return tifffile.imread(str(path)).astype("float32")


def dot_mask(arr: np.ndarray) -> np.ndarray:
    """Boolean mask of emitted dots (value > 0). NaN counts as no dot."""
    return np.nan_to_num(arr, nan=0.0) > 0


def dot_digest(dot: np.ndarray) -> str:
    """Stable identity of a dot *set*: sha256 over sorted flat indices (uint32 LE).

    Same convention as the prior sessions' ledgers, so digests are comparable
    across repos even when the TIFF coders differ.
    """
    return hashlib.sha256(np.flatnonzero(dot).astype("<u4").tobytes()).hexdigest()


def write_float32(path: str | Path, arr: np.ndarray, *, encoding: str,
                  template: str | Path) -> None:
    """Write one band on the template grid.

    encoding="nan"   -> NaN outside the footprint, {0,1} inside (spec-compliant primary)
    encoding="zeros" -> 0 outside the footprint, {0,1} inside (fallback twin)

    CRS and transform are copied from the template; writing them is a gate, not
    a convenience (tifffile alone silently drops both).
    """
    if encoding not in ("nan", "zeros"):
        raise ValueError(encoding)
    arr = np.asarray(arr, dtype="float32")
    if encoding == "zeros":
        arr = np.where(np.isfinite(arr), arr, np.float32(0.0))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(str(template)) as tpl:
        profile = {
            "driver": "GTiff", "height": tpl.height, "width": tpl.width, "count": 1,
            "dtype": "float32", "crs": tpl.crs, "transform": tpl.transform,
            "compress": "deflate", "predictor": 3, "tiled": True,
            "blockxsize": 256, "blockysize": 256,
        }
        if encoding == "nan":
            profile["nodata"] = float("nan")
    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(arr, 1)


def profile_of(template: str | Path) -> dict:
    with rasterio.open(str(template)) as src:
        return {
            "crs": src.crs,
            "transform": tuple(src.transform)[:6],
            "shape": (src.height, src.width),
            "dtype": src.dtypes[0],
            "count": src.count,
            "bounds": tuple(src.bounds),
        }
