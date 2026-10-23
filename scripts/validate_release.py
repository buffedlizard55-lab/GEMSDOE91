#!/usr/bin/env python3
"""Validate one candidate raster against the brief's MUST gates.

    python scripts/validate_release.py releases/<id>.tif --axis MASS \
        --sample data/official/sample_submission.tif \
        --catalogue data/official/existing_faults.tif

Exit codes: 0 CERTIFIED, 1 NOT CERTIFIED.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems91.gates import validate  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--axis", default=None, help="MASS|CONCENTRATION|SNAP|PRUNE|RELIEF|SPACING")
    ap.add_argument("--sample", default="data/official/sample_submission.tif")
    ap.add_argument("--catalogue", default="data/official/existing_faults.tif")
    ap.add_argument("--ledger", default="ledger/submissions.csv")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    rep = validate(args.file,
                   sample_submission=args.sample if Path(args.sample).exists() else None,
                   catalogue=args.catalogue if Path(args.catalogue).exists() else None,
                   ledger_csv=args.ledger if Path(args.ledger).exists() else None,
                   axis=args.axis)
    out = rep.to_dict()
    print(json.dumps(out, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nVERDICT: {rep.verdict}")
    if rep.unverified:
        print("unverified gates: " + ", ".join(rep.unverified))
        print("An unverified gate is not a pass. Supply the missing input or do not submit.")
    return 0 if rep.verdict == "CERTIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
