"""Byte-exact R0 lineage proof from pinned ancestors.

The recorded encoder recipe is deflate / predictor=3 / zlevel=9 / 256 px tiles
on the catalogue grid profile.  It reproduces both published R0 encodings, not
merely their dot sets.  No candidate is allowed to approximate this parent.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from . import geom, io

R0_NAN_SHA256 = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
R0_ZEROS_SHA256 = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
R0_NAN_BYTES = 355_443
R0_ZEROS_BYTES = 219_065
R0_DOT_DIGEST = "905cee9d4383de23d6ee6366da4627fe19a78e4f49ce3a2462a8736e9b66a027"
R0_DOTS = 37_654


def write_z9(path: str | Path, dots: np.ndarray, footprint: np.ndarray, *,
             profile_source: str | Path, encoding: str) -> str:
    """Write a binary field with the recorded R0 encoder and return its sha256."""
    if encoding not in ("nan", "zeros"):
        raise ValueError(encoding)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(str(profile_source)) as src:
        profile = src.profile.copy()
    profile.update(driver="GTiff", dtype="float32", count=1,
                   compress="deflate", predictor=3, zlevel=9,
                   tiled=True, blockxsize=256, blockysize=256,
                   nodata=float("nan") if encoding == "nan" else None)
    outside = np.float32(np.nan if encoding == "nan" else 0.0)
    arr = np.where(footprint, np.asarray(dots, dtype=np.float32), outside).astype(np.float32)
    with rasterio.open(str(path), "w", **profile) as dst:
        dst.write(arr, 1)
    return io.sha256_file(path)


def prove_r0_byte_rebuild(*, parent_nan: str | Path, parent_zeros: str | Path,
                          ancestor_d28: str | Path, ancestor_solo: str | Path,
                          sample: str | Path, catalogue: str | Path,
                          work_dir: str | Path) -> dict:
    """Recompute R0 from both ancestors and require byte-identical TIFF twins."""
    parent_nan, parent_zeros = Path(parent_nan), Path(parent_zeros)
    required = [parent_nan, parent_zeros, Path(ancestor_d28), Path(ancestor_solo),
                Path(sample), Path(catalogue)]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        return {"ok": False, "rebuild_kind": "independent_recompute",
                "missing": missing}

    nan_mask = io.dot_mask(io.read_grid(parent_nan))
    zeros_mask = io.dot_mask(io.read_grid(parent_zeros))
    cat = geom.catalogue_mask(io.read_grid(catalogue))
    footprint = geom.footprint_mask(io.read_grid(sample))
    dcat = geom.catalogue_distance(cat)
    report = {
        "ok": True,
        "rebuild_kind": "independent_recompute",
        "encoder": "deflate predictor=3 zlevel=9 tiled=256; catalogue grid profile",
        "parent_sha256_nan": io.sha256_file(parent_nan),
        "parent_sha256_zeros": io.sha256_file(parent_zeros),
        "parent_dot_digest": io.dot_digest(nan_mask),
        "n_dots": int(nan_mask.sum()),
        "twins_identical": bool(np.array_equal(nan_mask, zeros_mask)),
        "min_catalogue_distance_px": float(dcat[nan_mask].min()),
        "dots_on_catalogue": int((nan_mask & cat).sum()),
        "rebuilt_from": {},
        "byte_rebuilds": {},
    }
    for name, path in (("d2.8", ancestor_d28), ("solo_d2.8", ancestor_solo)):
        ancestor = io.dot_mask(io.read_grid(path))
        rebuilt = ancestor & (dcat > geom.CATALOGUE_FLOOR_PX)
        identical = bool(np.array_equal(rebuilt, nan_mask))
        report["rebuilt_from"][name] = {
            "path": str(path), "n_ancestor_dots": int(ancestor.sum()),
            "n_after_collar": int(rebuilt.sum()), "identical_to_parent": identical,
        }
        report["ok"] &= identical

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    for encoding, expected_sha, expected_bytes in (
            ("nan", R0_NAN_SHA256, R0_NAN_BYTES),
            ("zeros", R0_ZEROS_SHA256, R0_ZEROS_BYTES)):
        out = work_dir / f"r0-rebuild-{encoding}.tif"
        got = write_z9(out, nan_mask, footprint, profile_source=catalogue,
                       encoding=encoding)
        size = out.stat().st_size
        report["byte_rebuilds"][encoding] = {
            "path": str(out), "sha256": got, "expected_sha256": expected_sha,
            "bytes": size, "expected_bytes": expected_bytes,
            "hash_match": got == expected_sha, "bytes_match": size == expected_bytes,
        }
        report["ok"] &= bool(got == expected_sha and size == expected_bytes)

    report["ok"] &= bool(report["twins_identical"] and report["n_dots"] == R0_DOTS
                         and report["parent_dot_digest"] == R0_DOT_DIGEST
                         and report["parent_sha256_nan"] == R0_NAN_SHA256
                         and report["parent_sha256_zeros"] == R0_ZEROS_SHA256)
    return report
