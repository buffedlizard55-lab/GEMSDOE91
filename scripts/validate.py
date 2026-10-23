#!/usr/bin/env python3
"""Re-run every hard gate on a release file, by re-reading it from disk.

    python3 scripts/validate.py releases/<file>.tif [--encoding zeros]

Exit code 0 = PASS, 1 = a gate failed. This is the same code the build uses, so
a file that passes here is the file the build signed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import gates, geom, io  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "bridge" / "sample_submission.tif"
CATALOGUE = DATA / "bridge" / "existing_faults.tif"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--encoding", choices=("nan", "zeros"), default=None,
                    help="default: inferred from the file name / values")
    args = ap.parse_args()

    if not TEMPLATE.is_file() or not CATALOGUE.is_file():
        print("pinned inputs missing - run scripts/restore_data.py first", file=sys.stderr)
        return 1
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    encoding = args.encoding or ("zeros" if "zeros" in args.path.name else "nan")

    rep = gates.validate_release(args.path, template=TEMPLATE, catalogue=cat,
                                 encoding=encoding,
                                 ledger=ROOT / "ledger" / "submissions.csv",
                                 own_id=args.path.name.replace("-zeros.tif", ".tif")[:-4]
                                 if "-zeros" in args.path.name else args.path.stem)
    print(json.dumps(rep, indent=2, default=str))
    print("\n" + ("PASS" if rep["PASS"] else f"FAIL: {rep['failed']}"))
    return 0 if rep["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
