"""Raster read/write helpers shared by the gate validator and the axis builders.

Two output forms are always produced together (brief section 7):
  <id>.tif        NaN outside the footprint   (primary)
  <id>-zeros.tif  zeros outside the footprint (fallback)
The zeros twin exists only because at least 8 historical slots were spent proving
the two score identically; the ledger collapses them as one experiment.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import subprocess
from pathlib import Path

import numpy as np
import rasterio


def read_band(path: Path | str) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1)


def footprint_from_sample(path: Path | str) -> tuple[np.ndarray, dict]:
    """Scored-area mask and profile from sample_submission.tif.

    NaN nodata must be tested with isfinite, not `band != nodata`: every comparison
    with NaN is False, which silently turns the footprint into the whole grid.
    """
    with rasterio.open(path) as ds:
        band = ds.read(1)
        profile = ds.profile.copy()
        nodata = ds.nodata
    if nodata is None:
        foot = np.isfinite(band)
        source = "sample:finite-only(ASSUMPTION)"
    elif isinstance(nodata, float) and np.isnan(nodata):
        foot = np.isfinite(band)
        source = "sample:nodata=nan"
    else:
        foot = band != nodata
        source = f"sample:nodata={nodata}"
    return foot, {"profile": profile, "source": source}


def read_profile(path: Path | str) -> dict:
    with rasterio.open(path) as ds:
        return ds.profile.copy()


def sha256_file(path: Path | str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def git_sha(short: bool = True) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short" if short else "--verify", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception:  # noqa: BLE001 - provenance must not crash a build
        return "unknown"


def dots_from_band(band: np.ndarray, thresh: float = 0.0) -> np.ndarray:
    """(N,2) integer (row, col) of positive pixels, sorted row-major (deterministic)."""
    rr, cc = np.nonzero(np.nan_to_num(band, nan=0.0) > thresh)
    return np.column_stack([rr, cc]).astype(np.int64)


def band_from_dots(shape: tuple[int, int], dots: np.ndarray, footprint: np.ndarray | None = None) -> np.ndarray:
    """Unit-mass raster from integer dot coordinates; non-finite outside footprint."""
    out = np.full(shape, np.nan, dtype=np.float64)
    if footprint is not None:
        out[footprint] = 0.0
    rr = dots[:, 0].astype(int)
    cc = dots[:, 1].astype(int)
    out[rr, cc] = 1.0
    return out


def write_submission(
    out_dir: Path,
    stem: str,
    band: np.ndarray,
    profile: dict,
    footprint: np.ndarray | None = None,
    compress: str | None = None,
) -> dict:
    """Write the primary (NaN outside) and zeros-outside twins; return their paths + hashes.

    `compress` is opt-in and defaults to None, which keeps every earlier builder's bytes
    unchanged (the release MANIFEST hashes are a contract).  Pass "lzw" or "deflate" to
    match the competition template's container instead of writing ~49 MB per arm.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    prof = profile.copy()
    prof.update(driver="GTiff", count=1, dtype="float32", nodata=np.nan)
    for key in ("compress", "blockxsize", "blockysize", "tiled"):
        prof.pop(key, None)
    if compress:
        prof["compress"] = compress

    nan_band = np.asarray(band, dtype=np.float32)
    if footprint is not None:
        nan_band = np.where(footprint, nan_band, np.float32("nan"))

    nan_path = out_dir / f"{stem}.tif"
    with rasterio.open(nan_path, "w", **prof) as ds:
        ds.write(nan_band.astype(np.float32), 1)

    z_prof = prof.copy()
    z_prof.update(nodata=0.0)
    zeros_band = np.where(np.isfinite(nan_band), nan_band, np.float32(0.0))
    zeros_path = out_dir / f"{stem}-zeros.tif"
    with rasterio.open(zeros_path, "w", **z_prof) as ds:
        ds.write(zeros_band.astype(np.float32), 1)

    # re-read from disk: never report a hash of an in-memory object
    return {
        "primary": str(nan_path),
        "zeros": str(zeros_path),
        "sha256": sha256_file(nan_path),
        "sha256_zeros": sha256_file(zeros_path),
        "sha8": sha256_file(nan_path)[:8],
    }


def release_stem(parent_tag: str, axis: str, value: str, sha8: str, date: _dt.date | None = None) -> str:
    d = (date or _dt.date.today()).strftime("%Y%m%d")
    safe_value = str(value).replace("/", "-").replace(" ", "").replace("%", "pct")
    return f"{parent_tag}-{axis}{safe_value}-{d}-{sha8}"


def form_note(parent_tag: str, change: str, predicted: str, limit: int = 140) -> str:
    note = f"{parent_tag}; {change}; predicted {predicted}"
    if len(note) > limit:
        note = note[: limit - 3] + "..."
    return note


def write_named_release(
    out_dir: Path,
    parent_tag: str,
    axis: str,
    value: str,
    band: np.ndarray,
    profile: dict,
    footprint: np.ndarray | None = None,
    date: _dt.date | None = None,
    compress: str | None = None,
) -> dict:
    """Write primary + zeros twin under the canonical name, which embeds the file hash.

    The hash cannot be known before writing, so the pair is written under a temporary
    stem, hashed from disk, then renamed. Renaming does not change the bytes, so the
    embedded sha8 stays true.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_stem = release_stem(parent_tag, axis, value, "tmp", date)
    written = write_submission(out_dir, tmp_stem, band, profile, footprint, compress=compress)
    sha8 = written["sha8"]
    final_stem = release_stem(parent_tag, axis, value, sha8, date)
    final_primary = out_dir / f"{final_stem}.tif"
    final_zeros = out_dir / f"{final_stem}-zeros.tif"
    Path(written["primary"]).replace(final_primary)
    Path(written["zeros"]).replace(final_zeros)
    return {
        "primary": str(final_primary),
        "zeros": str(final_zeros),
        "sha256": sha256_file(final_primary),
        "sha256_zeros": sha256_file(final_zeros),
        "sha8": sha8,
        "stem": final_stem,
    }
