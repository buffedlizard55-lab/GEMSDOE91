#!/usr/bin/env python3
"""Shared fail-closed GeoTIFF & ZIP submission writer for GEMSDOE91.

PARALLEL-RUN PROTOCOL Rule 2: delegates raster encoding and certification to
the repository's shared `src/gems91/io.py`, `src/gems91/gates.py`,
`src/gems91/release_gates.py`, and `scripts/validate_raster.py` — no private
fork of the format rules.

This legacy interface checks original, pre-conversion predictions without
silently fixing invalid values. It stages and re-reads both encodings and the
single-TIFF ZIP before publishing, and refuses to overwrite existing outputs.
It performs technical checks only: it cannot identify the cause of a past
organizer error, establish organizer acceptance, or authorize a weekly slot.
The organizer description specifies null/NaN outside the bounds; the extra
all-finite ``-zeros`` twin is only a local range precaution, not proof that
its outside-footprint representation is accepted.
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import tempfile
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


def _plain_name(value: str, label: str) -> None:
    """Keep caller-supplied names inside their output directories."""
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError(f"{label} must be a nonempty plain filename component")


def write_validated_submission_bundle(
    dot_or_prob_grid: np.ndarray, *, stem_prefix: str, date_tag: str,
    template_path: str | Path, catalogue_path: str | Path,
    ledger_path: str | Path | None = ROOT / "ledger" / "submissions.csv",
    parent_compare_path: str | Path | None = None,
    releases_dir: str | Path = ROOT / "releases",
    downloads_dir: str | Path | None = ROOT / "docs" / "downloads",
    floor_px: float = 3.0, bundle_js_filename: str = "h91_submission_bundle.js",
) -> dict:
    """Stage, validate and publish the legacy bundle without clobbering files.

    Validation failures leave no new artifacts. Atomic hard links provide
    no-overwrite publication on each target filesystem; on a publication
    exception the links already created by this call are rolled back. A hard
    process crash during multi-file publication is not an atomic transaction.
    This never promotes a candidate or spends a competition slot.
    """
    _plain_name(stem_prefix, "stem_prefix")
    _plain_name(date_tag, "date_tag")
    _plain_name(bundle_js_filename, "bundle_js_filename")
    releases = Path(releases_dir)
    releases.mkdir(parents=True, exist_ok=True)
    downloads = Path(downloads_dir) if downloads_dir is not None else None
    if downloads is not None:
        downloads.mkdir(parents=True, exist_ok=True)

    from contextlib import ExitStack
    with ExitStack() as stack:
        stage_release = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".gems-stage-", dir=releases)))
        stage_download = (Path(stack.enter_context(tempfile.TemporaryDirectory(prefix=".gems-stage-", dir=downloads)))
                          if downloads is not None else None)
        audit = _write_staged_submission_bundle(
            dot_or_prob_grid, stem_prefix=stem_prefix, date_tag=date_tag,
            template_path=template_path, catalogue_path=catalogue_path,
            ledger_path=ledger_path, parent_compare_path=parent_compare_path,
            releases_dir=stage_release, downloads_dir=stage_download,
            floor_px=floor_px, bundle_js_filename=bundle_js_filename)

        moves = []
        for key in ("companion_nan_tif", "primary_zeros_tif"):
            row = audit[key]
            dest = releases / row["filename"]
            moves.append((stage_release / row["filename"], dest))
            row["path"] = _rel_or_str(dest)
        if downloads is not None:
            zip_row = audit["zip_bundle"]
            zip_dest = downloads / zip_row["filename"]
            js_dest = downloads / bundle_js_filename
            audit_dest = downloads / f"{audit['candidate_id']}-audit.json"
            zip_row["path"] = _rel_or_str(zip_dest)
            audit["browser_tif_bundle"]["path"] = _rel_or_str(js_dest)
            audit_source = stage_download / audit_dest.name
            audit_source.write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8")
            # Publishing TIFFs last keeps them out of sight until other files exist.
            moves = [(stage_download / zip_row["filename"], zip_dest),
                     (stage_download / bundle_js_filename, js_dest),
                     (audit_source, audit_dest)] + moves
        destinations = [destination for _, destination in moves]
        if len({path.resolve() for path in destinations}) != len(destinations):
            raise ValueError("output paths collide")
        committed = []
        try:
            for source, destination in moves:
                # link() fails if a destination exists, including dangling symlinks;
                # unlike an exists()+replace() check it cannot clobber in a race.
                os.link(source, destination)
                committed.append((source, destination))
        except Exception:
            for source, destination in reversed(committed):
                try:
                    # Do not knowingly remove a file replaced by another writer.
                    if os.path.samefile(source, destination):
                        destination.unlink()
                except FileNotFoundError:
                    pass
            raise
        return audit


def _write_staged_submission_bundle(
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
    bundle_js_filename: str = "h91_submission_bundle.js",
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
        if tpl.count != 1 or tpl.crs is None:
            raise ValueError("template must be a single-band georeferenced raster")
        template_grid = (tpl.shape, tpl.crs, tpl.transform)
        tpl_arr = tpl.read(1)
        footprint = np.isfinite(tpl_arr) & (tpl.read_masks(1) > 0)
    if not footprint.any():
        raise ValueError("template footprint must not be empty")
    with rasterio.open(catalogue_p) as cat_src:
        if cat_src.count != 1 or (cat_src.shape, cat_src.crs, cat_src.transform) != template_grid:
            raise ValueError("catalogue CRS, shape, transform and band count must match the template")
        catalogue_values = cat_src.read(1)
        if (not np.isfinite(catalogue_values[footprint]).all()
                or np.any(cat_src.read_masks(1)[footprint] == 0)):
            raise ValueError("catalogue contains non-finite or masked values inside the footprint")
        if not np.isin(catalogue_values[footprint], [0, 1]).all():
            raise ValueError("catalogue must be binary inside the footprint")
        cat_mask = (catalogue_values > 0) & footprint

    # Validate the original values before narrowing to float32: for example,
    # 1 + 1e-9 must not silently round down to an apparently valid 1.0.
    if np.ma.isMaskedArray(dot_or_prob_grid) and np.ma.getmaskarray(dot_or_prob_grid).any():
        raise ValueError("masked predictions must be resolved before encoding")
    arr = np.asarray(dot_or_prob_grid)
    if arr.shape != footprint.shape:
        raise ValueError(f"grid shape {arr.shape} != template {footprint.shape}")
    if arr.dtype.kind not in 'buif':
        raise ValueError("prediction must be a real numeric array")
    finite = np.isfinite(arr)
    if not finite[footprint].all() or np.isinf(arr).any():
        raise ValueError("non-finite prediction inside footprint or infinity anywhere")
    if np.any((arr[finite] < 0) | (arr[finite] > 1)):
        raise ValueError("pre-write range violation: finite predictions must be in [0,1]")
    if np.any((arr > 0) & ~footprint):
        raise ValueError("positive prediction outside footprint")
    if np.any((arr > 0) & cat_mask):
        raise ValueError("positive prediction on mapped catalogue")

    # Outside-footprint NaN is allowed as input and explicitly encoded in the
    # NaN twin; only that outside region is set to zero in the local-range twin.
    inside_clean = np.zeros(arr.shape, dtype=np.float32)
    inside_clean[footprint] = arr[footprint].astype(np.float32, copy=False)
    if np.any((arr[footprint] > 0) & (inside_clean[footprint] == 0)):
        raise ValueError("positive prediction support underflows during float32 conversion")

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
        # Single-member ZIP containing `<cand_id>-zeros.tif`; acceptance is unverified.
        zip_path = dl_dir / f"{cand_id}-zeros.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            zi = zipfile.ZipInfo(filename=final_zeros.name, date_time=(2026, 10, 24, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, final_zeros.read_bytes())
        with zipfile.ZipFile(zip_path, "r") as zf:
            if zf.namelist() != [final_zeros.name] or zf.read(final_zeros.name) != final_zeros.read_bytes():
                raise ValueError("single-TIFF ZIP failed byte-for-byte roundtrip")
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
        if Path(bundle_js_filename).name != bundle_js_filename:
            raise ValueError("bundle_js_filename must be a plain filename")
        b64_js_path = dl_dir / bundle_js_filename
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
        "ok_to_submit": False,
        "organizer_acceptance_verified": False,
        "scope": "Local technical checks only; no scientific, registry or selector approval.",
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
