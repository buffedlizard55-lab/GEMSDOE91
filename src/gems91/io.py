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
# fill value.  Byte-identical re-encoding is NOT claimed: see IR-91-12.
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
    """Low-level encoder; it does not approve or publish a submission.

    The input is validated *before* float32 conversion. Only NaNs outside the
    template footprint may be encoded as zeros in the local-range twin; no
    nonfinite in-footprint values, infinities, out-of-range finite values or
    positive mass outside the footprint are ever silently repaired. Use the
    shared submission writer for staged validation and publication.
    """
    if encoding not in ("nan", "zeros"):
        raise ValueError(encoding)
    if np.ma.isMaskedArray(arr) and np.ma.getmaskarray(arr).any():
        raise ValueError("masked predictions must be resolved before encoding")
    values = np.asarray(arr)
    if values.ndim != 2 or values.dtype.kind not in 'buif':
        raise ValueError("prediction must be a real numeric 2-D array")
    with rasterio.open(str(template)) as tpl:
        if tpl.count != 1 or tpl.crs is None or values.shape != tpl.shape:
            raise ValueError("prediction must match a single-band georeferenced template")
        template_values = tpl.read(1)
        footprint = np.isfinite(template_values) & (tpl.read_masks(1) > 0)
        if not footprint.any():
            raise ValueError("empty template footprint")
        finite = np.isfinite(values)
        if not finite[footprint].all() or np.isinf(values).any():
            raise ValueError("non-finite prediction inside footprint or infinity anywhere")
        if np.any((values[finite] < 0) | (values[finite] > 1)):
            raise ValueError("prediction values must already be in [0,1]")
        if np.any((values > 0) & ~footprint):
            raise ValueError("positive prediction outside footprint")
        arr32 = np.zeros(values.shape, dtype=np.float32)
        arr32[footprint] = values[footprint].astype(np.float32, copy=False)
        if np.any((values[footprint] > 0) & (arr32[footprint] == 0)):
            raise ValueError("positive prediction support underflows during float32 conversion")
        if encoding == "nan":
            arr32[~footprint] = np.nan
        profile = {
            "driver": "GTiff", "height": tpl.height, "width": tpl.width, "count": 1,
            "dtype": "float32", "crs": tpl.crs, "transform": tpl.transform,
            "compress": "deflate", "predictor": 3, "tiled": True,
            "blockxsize": 256, "blockysize": 256,
        }
        if encoding == "nan":
            profile["nodata"] = float("nan")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(arr32, 1)


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
