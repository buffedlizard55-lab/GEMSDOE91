#!/usr/bin/env python3
"""Shared fail-closed GeoTIFF & ZIP submission writer for GEMSDOE91.

PARALLEL-RUN PROTOCOL Rule 2: delegates raster encoding and certification to
the repository's shared `src/gems91/io.py`, `src/gems91/gates.py`,
`src/gems91/release_gates.py`, and `scripts/validate_raster.py` — no private
fork of the format rules.

Prevents the DrivenData portal error `"Predicted values must be in range [0, 1]"`
against BOTH measured failure mechanisms:
  1. Sentinel bleed (`-3.4028234663852886e+38` inside footprint from
     `training_features.tif`): scrubbed before emission and asserted absent.
  2. Non-finite / nodata tag rejection: writes an all-finite `-zeros.tif` twin
     (`nodata=None`, 0 NaNs across all 12,279,160 cells, values strictly in
     `[0.0, 1.0]`) alongside the `NaN`-outside `.tif` twin, plus a single-member
     `.zip` archive and a WebCrypto SHA-256 verified `.b64.js` bundle for
     one-click GitHub Pages download without tracking raw `.tif` files in git.
"""

from __future__ import annotations

import base64
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import validate_raster as VR  # noqa: E402
from gems91 import gates as G  # noqa: E402
from gems91 import io as IO  # noqa: E402
from gems91 import release_gates as RG  # noqa: E402


def _rel_or_str(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def write_validated_submission_bundle(
    dot_or_prob_grid: np.ndarray,
    *,
    stem_prefix: str,
    date_tag: str,
    template_path: str | Path,
    catalogue_path: str | Path,
    ledger_path: str | Path | None = ROOT / "ledger" / "submissions.csv",
    parent_compare_path: str | Path | None = None,
    releases_dir: str | Path = ROOT / "releases",
    downloads_dir: str | Path | None = ROOT / "docs" / "downloads",
    floor_px: float = 3.0,
) -> dict:
    """Write, hash-stamp, re-read, and triple-validate a candidate GeoTIFF pair
    (NaN-outside `.tif` + all-finite `-zeros.tif` + single-member `.zip` +
    browser `.tif.b64.js` bundle).

    Raises `RuntimeError` immediately if ANY format, range `[0, 1]`, NaN, CRS,
    shape, transform, zero-catalogue-mass, or collar gate fails.
    """
    template_p = Path(template_path)
    catalogue_p = Path(catalogue_path)
    releases_p = Path(releases_dir)
    releases_p.mkdir(parents=True, exist_ok=True)

    with rasterio.open(template_p) as tpl:
        tpl_arr = tpl.read(1)
        footprint = np.isfinite(tpl_arr)
    with rasterio.open(catalogue_p) as cat_src:
        cat_mask = (cat_src.read(1) > 0) & footprint

    arr = np.asarray(dot_or_prob_grid, dtype=np.float32)
    if arr.shape != footprint.shape:
        raise ValueError(f"grid shape {arr.shape} != template {footprint.shape}")

    # Scrub non-finite / out-of-range values inside footprint fail-closed
    inside_clean = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    if float(inside_clean[footprint].min()) < 0.0 or float(inside_clean[footprint].max()) > 1.0:
        raise ValueError(
            f"pre-write range violation: [{inside_clean[footprint].min()}, {inside_clean[footprint].max()}]"
        )

    # Zero outside footprint and zero known catalogue pixels pixel-exactly
    inside_clean[~footprint] = np.float32(0.0)
    inside_clean[cat_mask] = np.float32(0.0)

    nan_grid = np.where(footprint, inside_clean, np.float32(np.nan)).astype(np.float32)
    zeros_grid = inside_clean.copy()

    # Write temporary files first to compute exact content-addressed sha8
    tmp_nan = releases_p / f"_tmp_{stem_prefix}_{date_tag}_nan.tif"
    tmp_zeros = releases_p / f"_tmp_{stem_prefix}_{date_tag}_zeros.tif"
    try:
        IO.write_float32(tmp_nan, nan_grid, encoding="nan", template=template_p)
        IO.write_float32(tmp_zeros, zeros_grid, encoding="zeros", template=template_p)
        sha_nan = IO.sha256_file(tmp_nan)
        sha_zeros = IO.sha256_file(tmp_zeros)
        sha8 = sha_nan[:8]

        cand_id = f"{stem_prefix}-{date_tag}-{sha8}"
        final_nan = releases_p / f"{cand_id}.tif"
        final_zeros = releases_p / f"{cand_id}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zeros.replace(final_zeros)
    finally:
        tmp_nan.unlink(missing_ok=True)
        tmp_zeros.unlink(missing_ok=True)

    # Re-read from disk and run ALL THREE repository gate suites
    with rasterio.open(final_zeros) as zsrc:
        z_arr = zsrc.read(1)
        z_nodata = zsrc.nodata
        z_crs = str(zsrc.crs)
        z_shape = (zsrc.height, zsrc.width)
        z_transform = tuple(zsrc.transform)[:6]
        z_dtype = zsrc.dtypes[0]
        z_count = zsrc.count

    all_finite_zeros = bool(np.isfinite(z_arr).all())
    z_min = float(z_arr.min())
    z_max = float(z_arr.max())
    n_dots = int((z_arr > 0).sum())

    if not all_finite_zeros or z_nodata is not None or z_min < 0.0 or z_max > 1.0:
        raise RuntimeError(
            f"all-finite range [0,1] check failed on {final_zeros.name}: "
            f"all_finite={all_finite_zeros}, nodata={z_nodata}, min={z_min}, max={z_max}"
        )

    # Suite 1: src/gems91/gates.py (strict 3.0 px collar gate included!)
    g_nan = G.validate(
        final_nan,
        sample_submission=template_p,
        catalogue=catalogue_p,
        ledger_csv=ledger_path,
        axis="DISCOVERY",
        reread=True,
    )
    if ledger_path is not None:
        if g_nan.verdict != "CERTIFIED":
            raise RuntimeError(f"gems91.gates failed on {final_nan.name}: {g_nan.to_dict()}")
    else:
        bad_g = {k: v for k, v in g_nan.gates.items() if k != "sha_unseen" and v != "PASS"}
        if bad_g:
            raise RuntimeError(f"gems91.gates failed on {final_nan.name}: {bad_g}")

    # Suite 2: src/gems91/release_gates.py (both encodings)
    rg_nan = RG.validate_release(
        final_nan,
        template=template_p,
        catalogue=cat_mask,
        ledger=ledger_path,
        encoding="nan",
        floor_px=floor_px,
        expect_dots=n_dots,
        own_id=cand_id,
    )
    rg_zeros = RG.validate_release(
        final_zeros,
        template=template_p,
        catalogue=cat_mask,
        ledger=ledger_path,
        encoding="zeros",
        floor_px=floor_px,
        expect_dots=n_dots,
        own_id=cand_id,
    )
    if not rg_nan["PASS"] or not rg_zeros["PASS"]:
        raise RuntimeError(
            f"release_gates failed: nan={rg_nan['failed']}, zeros={rg_zeros['failed']}"
        )

    # Suite 3: scripts/validate_raster.py (both encodings)
    eff_parent = parent_compare_path
    if eff_parent is None:
        default_r0 = ROOT / "data" / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
        if default_r0.is_file():
            with rasterio.open(default_r0) as r0_src:
                if (r0_src.height, r0_src.width) == z_shape:
                    eff_parent = default_r0
        if eff_parent is None:
            eff_parent = template_p

    vr_nan = VR.validate_raster(
        final_nan,
        template_p,
        catalogue=catalogue_p,
        ledger_csv=ledger_path,
        parent=eff_parent,
        allow_zeros_outside=False,
    )
    vr_zeros = VR.validate_raster(
        final_zeros,
        template_p,
        catalogue=catalogue_p,
        ledger_csv=ledger_path,
        parent=eff_parent,
        allow_zeros_outside=True,
    )
    if not vr_nan.ok or not vr_zeros.ok:
        raise RuntimeError(
            f"validate_raster failed:\nNAN:\n{vr_nan.text()}\nZEROS:\n{vr_zeros.text()}"
        )

    zip_info = None
    b64_info = None
    if downloads_dir is not None:
        dl_dir = Path(downloads_dir)
        dl_dir.mkdir(parents=True, exist_ok=True)
        # Single-member ZIP containing `<cand_id>-zeros.tif` (directly accepted by DrivenData)
        zip_path = dl_dir / f"{cand_id}-zeros.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zi = zipfile.ZipInfo(filename=final_zeros.name, date_time=(2026, 10, 24, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, final_zeros.read_bytes())
        sha_zip = IO.sha256_file(zip_path)
        zip_info = {
            "path": _rel_or_str(zip_path),
            "filename": zip_path.name,
            "inner_geotiff": final_zeros.name,
            "bytes": zip_path.stat().st_size,
            "sha256": sha_zip,
        }

        # Browser-decodable exact `.tif` bundle (verified via WebCrypto SHA-256 in browser)
        b64_zeros = base64.b64encode(final_zeros.read_bytes()).decode("ascii")
        b64_nan = base64.b64encode(final_nan.read_bytes()).decode("ascii")
        b64_js_path = dl_dir / "h91_submission_bundle.js"
        payload = {
            "candidate_id": cand_id,
            "primary_zeros": {
                "filename": final_zeros.name,
                "sha256": sha_zeros,
                "bytes": final_zeros.stat().st_size,
                "base64": b64_zeros,
            },
            "companion_nan": {
                "filename": final_nan.name,
                "sha256": sha_nan,
                "bytes": final_nan.stat().st_size,
                "base64": b64_nan,
            },
        }
        js_body = (
            "// Auto-generated by scripts/submission_writer.py — exact byte-verified GeoTIFF payload\n"
            f"window.GEMS91_SUBMISSION_BUNDLE = {json.dumps(payload, separators=(',', ':'))};\n"
        )
        b64_js_path.write_text(js_body, encoding="utf-8")
        b64_info = {
            "path": _rel_or_str(b64_js_path),
            "bytes": b64_js_path.stat().st_size,
            "sha256": IO.sha256_file(b64_js_path),
        }

    audit = {
        "candidate_id": cand_id,
        "primary_zeros_tif": {
            "filename": final_zeros.name,
            "path": _rel_or_str(final_zeros),
            "sha256": sha_zeros,
            "bytes": final_zeros.stat().st_size,
            "nodata": z_nodata,
            "all_cells_finite": all_finite_zeros,
            "total_cells": int(z_arr.size),
            "nan_cells_anywhere": int((~np.isfinite(z_arr)).sum()),
            "min_value": z_min,
            "max_value": z_max,
        },
        "companion_nan_tif": {
            "filename": final_nan.name,
            "path": _rel_or_str(final_nan),
            "sha256": sha_nan,
            "bytes": final_nan.stat().st_size,
            "nodata": "NaN",
            "nan_inside_footprint": 0,
            "nan_outside_footprint": int((~footprint).sum()),
        },
        "zip_bundle": zip_info,
        "browser_tif_bundle": b64_info,
        "grid": {
            "crs": z_crs,
            "shape": list(z_shape),
            "transform": list(z_transform),
            "dtype": z_dtype,
            "band_count": z_count,
            "footprint_pixels": int(footprint.sum()),
        },
        "dots": {
            "n_dots": n_dots,
            "dot_set_digest": rg_zeros["dot_set_digest"],
            "zero_catalogue_mass": True,
            "min_catalogue_distance_px": round(float(rg_zeros["min_catalogue_distance_px"]), 4),
            "dots_le_3px": int(g_nan.notes.get("dots_le_3px", 0)),
        },
        "validators": {
            "gems91_gates_verdict": g_nan.verdict,
            "release_gates_nan_pass": bool(rg_nan["PASS"]),
            "release_gates_zeros_pass": bool(rg_zeros["PASS"]),
            "validate_raster_nan_pass": bool(vr_nan.ok or eff_parent is None),
            "validate_raster_zeros_pass": bool(vr_zeros.ok or eff_parent is None),
            "range_0_1_portal_safe": True,
        },
    }
    if downloads_dir is not None:
        audit_path = Path(downloads_dir) / f"{cand_id}-audit.json"
        audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    return audit
