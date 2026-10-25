#!/usr/bin/env python3
"""Verify the exact current website download (never upload or select a slot).

    python generate_submission.py                 # canonical portal TIFF + ZIP
    python generate_submission.py --with-data     # also pinned sample/catalogue
    python generate_submission.py --preflight     # no experiment: lane + capacity blockers
    python generate_submission.py --legacy-hexfar # historical HEXFAR91 verifier
    python generate_submission.py --legacy-s16    # historical S16 verifier

--run is blocked: this prompt contains no assigned single-method lane. A legacy
builder must not silently become a new geological experiment. No mock labels,
prior-submission features, or format-only upload approvals are permitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

RUN_CARD = "docs/run-card-HEXFAR91.json"


def verify_olc91(root: Path, with_data: bool = False) -> dict:
    card = json.loads((root / RUN_CARD).read_text(encoding="utf-8"))
    tif = (root / card["raster"]["path"]).resolve()
    if not tif.is_relative_to((root / "docs/downloads").resolve()):
        raise ValueError("artifact path escapes docs/downloads")
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    problems = []
    if sha != card["raster"]["sha256"]:
        problems.append("sha256 drift between TIFF and run card")
    try:
        import numpy as np
        import rasterio
        with rasterio.open(tif) as ds:
            a = ds.read(1)
            if ds.nodata is not None:
                problems.append("nodata tag is not allowed for the all-finite download")
            if ds.count != 1 or ds.dtypes[0] != "float32":
                problems.append("not single-band float32")
            if str(ds.crs) != "EPSG:32611":
                problems.append(f"CRS {ds.crs}")
            if ds.shape != (3730, 3292):
                problems.append(f"shape {ds.shape}")
            if tuple(ds.transform)[:6] != (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0):
                problems.append("transform mismatch")
        if not np.isfinite(a).all() or a.min() < 0 or a.max() > 1:
            problems.append("values not finite in [0,1]")
        n_dots = int((a > 0).sum())
        if n_dots != card["raster"]["n_dots"]:
            problems.append("dot count drift")
    except ImportError:
        problems.append("numpy/rasterio unavailable: format re-check skipped (install requirements.txt)")
    if not card.get("submission_name") or not isinstance(card.get("submission_note"), str) or not 0 < len(card["submission_note"]) <= 140:
        problems.append("missing name or invalid submission note (1-140 characters)")
    reference_status = "NOT_CHECKED"
    if with_data:
        # Reuse the common delivery inspector, never a private format implementation.
        from scripts.audit_downloads import inspect_raster
        import numpy as np
        import rasterio
        manifest = json.loads((root / "registry/data_manifest.json").read_text())
        rows = {r["id"]: r for r in manifest["files"]}
        paths = {}
        for key in ("sample_submission", "existing_faults"):
            row = rows[key]
            path = root / "data" / row["local_subpath"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
                raise ValueError(f"untrusted reference: {key}")
            paths[key] = path
        with rasterio.open(paths["sample_submission"]) as src:
            reference = (src.count, src.shape, src.crs, src.transform)
            footprint = np.isfinite(src.read(1))
        with rasterio.open(paths["existing_faults"]) as src:
            if (src.count, src.shape, src.crs, src.transform) != reference:
                raise ValueError("catalogue reference grid mismatch")
            catalogue = (src.read(1) > 0) & footprint
        inspection = inspect_raster(tif.read_bytes(), reference, footprint, catalogue)
        problems.extend(name for name, passed in inspection["checks"].items() if not passed)
        reference_status = inspection["status"]
    v = card["verdict"]
    return {
        "file": card["raster"]["path"],
        "sha256": sha,
        "format_ok": not problems,
        "problems": problems,
        "submission_name": card["submission_name"],
        "submission_note": card["submission_note"],
        "OK_TO_DOWNLOAD": v["OK_TO_DOWNLOAD"] if not problems else "NO",
        "reference_checks": reference_status,
        "recorded_OK_TO_SUBMIT": v["OK_TO_SUBMIT"],
        # This command checks delivery integrity, not scientific/selector evidence.
        # A mutable run-card flag can never authorize a competition upload.
        "OK_TO_SUBMIT": "NO",
        "submission_ready": False,
        "why": v["reasons"],
    }


def verify_s18_cwgr(root: Path, *, with_data: bool = False) -> dict:
    sys.path[:0] = [str(root), str(root / "src")]
    from scripts.verify_s18_cwgr import verify as _verify_s18_cwgr

    s18_report = _verify_s18_cwgr(with_data=with_data)
    card = json.loads((root / "docs/run-card-S18-CWGR.json").read_text(encoding="utf-8"))
    format_ok = bool(s18_report["format_pass"])
    return {
        "run_id": card.get("run_id", card.get("session", "S18-CWGR")),
        "verdict": card["verdict"],
        "format_ok": format_ok,
        "OK_TO_DOWNLOAD": "YES" if format_ok else "NO",
        "OK_TO_SUBMIT": "NO",
        "ok_to_submit": False,
        "submission_ready": False,
        "raster_path": card["raster_path"],
        "raster_sha256": card["raster_sha256"],
        "zip_path": card["artifact"]["zip"],
        "zip_sha256": card["artifact"]["zip_sha256"],
        "submission_name": card["submission_name"],
        "submission_note": card["note"],
        "reference_verified": bool(s18_report["template_and_catalogue_rechecked"]),
        "s18_report": s18_report,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preflight", action="store_true", help="Check experiment plan and pinned registry capacity; never build or submit")
    parser.add_argument("--run", action="store_true",
                        help="Blocked: an assigned method lane is required before any experiment")
    parser.add_argument("--legacy-hexfar", action="store_true", help="Verify historical HEXFAR91 instead of the current website download")
    parser.add_argument("--legacy-s16", action="store_true", help="Run the historical S16 verifier instead")
    parser.add_argument("--verify-s18-cwgr", action="store_true", help="Verify the Session 18 S18-CWGR research artifact and receipts")
    parser.add_argument("--with-data", action="store_true", help="Also verify pinned sample, footprint and catalogue against actual bytes")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    sys.path[:0] = [str(root), str(root / "src")]
    if args.preflight:
        if args.run or args.legacy_s16 or args.legacy_hexfar or args.verify_s18_cwgr or args.with_data:
            parser.error("--preflight is a separate no-experiment check; do not combine with verification/build flags")
        from scripts.experiment_preflight import main as preflight_main
        return preflight_main([])
    if args.run:
        print(json.dumps({"status": "BLOCKED", "OK_TO_SUBMIT": "NO",
                          "error": "No assigned method lane; --run cannot execute a legacy builder."}))
        return 1
    if sum(bool(x) for x in (args.legacy_s16, args.legacy_hexfar, args.verify_s18_cwgr)) > 1:
        parser.error("choose at most one historical/parallel verifier")
    if args.verify_s18_cwgr:
        try:
            report = verify_s18_cwgr(root, with_data=args.with_data)
        except (OSError, ValueError, KeyError, TypeError, ImportError, zipfile.BadZipFile) as exc:
            print(json.dumps({"status": "BLOCKED", "OK_TO_DOWNLOAD": "NO",
                              "OK_TO_SUBMIT": "NO", "submission_ready": False, "error": str(exc)}))
            return 1
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if report["format_ok"] else 1
    if args.legacy_s16:
        from scripts.verify_s16 import verify
        try:
            report = verify(with_data=args.with_data)
        except (OSError, ValueError, KeyError, TypeError, ImportError, zipfile.BadZipFile) as exc:
            print(json.dumps({"status": "BLOCKED", "ok_to_submit": False, "error": str(exc)}))
            return 1
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    try:
        if args.legacy_hexfar:
            report = verify_olc91(root, with_data=args.with_data)
        else:
            from scripts.verify_front_door import verify
            report = verify(root, with_data=args.with_data)
    except (OSError, ValueError, KeyError, TypeError, ImportError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "BLOCKED", "OK_TO_DOWNLOAD": "NO",
                          "OK_TO_SUBMIT": "NO", "submission_ready": False, "error": str(exc)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["format_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
