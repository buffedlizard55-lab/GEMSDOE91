#!/usr/bin/env python3
"""Verify (default) or regenerate (--run) the current OLC91 candidate download.

The default command re-reads the published GeoTIFF, recomputes its SHA-256, re-checks the
submission format against the run card, and prints the automated verdict:

    python generate_submission.py            # verify docs/run-card-OLC91.json + its TIFF
    python generate_submission.py --run      # rerun the frozen OLC91 experiment (needs data/)
    python generate_submission.py --legacy-s16   # the historical S16 verifier

Never create mock labels in data/official, read another submission as a feature,
or describe random noise as a competition candidate. Tests use tools/make_fixture.py.
Importing this file has no filesystem side effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

RUN_CARD = "docs/run-card-OLC91.json"


def verify_olc91(root: Path) -> dict:
    card = json.loads((root / RUN_CARD).read_text(encoding="utf-8"))
    tif = root / card["raster"]["path"]
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    problems = []
    if sha != card["raster"]["sha256"]:
        problems.append("sha256 drift between TIFF and run card")
    try:
        import numpy as np
        import rasterio
        with rasterio.open(tif) as ds:
            a = ds.read(1)
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
    v = card["verdict"]
    return {
        "file": card["raster"]["path"],
        "sha256": sha,
        "format_ok": not problems,
        "problems": problems,
        "submission_name": card["submission_name"],
        "submission_note": card["submission_note"],
        "OK_TO_DOWNLOAD": v["OK_TO_DOWNLOAD"] if not problems else "NO",
        "OK_TO_SUBMIT": v["OK_TO_SUBMIT"],
        "why": v["reasons"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="store_true",
                        help="Rerun the frozen OLC91 holdout + final build once; never uploads or selects a slot")
    parser.add_argument("--legacy-s16", action="store_true", help="Run the historical S16 verifier instead")
    parser.add_argument("--with-data", action="store_true", help="(legacy S16) also verify pinned sample/catalogue")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    sys.path[:0] = [str(root), str(root / "src")]
    if args.legacy_s16:
        from scripts.verify_s16 import verify
        try:
            report = verify(with_data=args.with_data)
        except (OSError, ValueError, KeyError) as exc:
            print(json.dumps({"status": "BLOCKED", "ok_to_submit": False, "error": str(exc)}))
            return 1
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    if args.run:
        for step in (["holdout", "--seed", "20"], ["final", "--arm", "E1"]):
            rc = subprocess.call([sys.executable, str(root / "scripts" / "run_olc91.py"), *step], cwd=root)
            if rc:
                parser.exit(rc, "run_olc91 failed (the writer refuses to overwrite an existing TIFF)\n")
    try:
        report = verify_olc91(root)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "OK_TO_SUBMIT": "NO", "error": str(exc)}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["format_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
