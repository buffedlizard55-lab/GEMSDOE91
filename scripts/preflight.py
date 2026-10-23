#!/usr/bin/env python3
"""Preflight: can a build start here at all?

A build needs three competition rasters (format reference, catalogue, feature
stack). This session found none of them locally and none publicly. This script
is the honest gate in front of every build: it verifies presence + sha256 and
prints why a build is blocked when it is.

Exit 0 = BUILD ALLOWED, 1 = BUILD BLOCKED.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems91.pinned import load_manifest, local_path_for, verify_entry  # noqa: E402

REQUIRED_FOR_BUILD = ["sample_submission", "existing_faults", "training_features"]


def main() -> int:
    man = load_manifest()
    by_id = {e["id"]: e for e in man["files"]}
    root = Path("data")
    missing = []
    lines = []
    for fid in REQUIRED_FOR_BUILD:
        entry = by_id[fid]
        ok, msg = verify_entry(entry, local_path_for(entry, root))
        lines.append(("OK   " if ok else "BLOCK") + f"  {fid:20s} {msg}")
        if not ok:
            missing.append(fid)

    verdict = "BUILD ALLOWED" if not missing else "BUILD BLOCKED"
    print("\n".join(lines))
    print(f"\n{verdict}: {len(REQUIRED_FOR_BUILD) - len(missing)}/{len(REQUIRED_FOR_BUILD)} "
          f"required inputs verified")
    if missing:
        print("missing: " + ", ".join(missing))
        print("These files are competition data. They are not in this repo and are not "
              "publicly mirrored; they must come from the entrant's own machine.")
    Path("registry").mkdir(exist_ok=True)
    Path("registry/preflight.json").write_text(json.dumps(
        {"verdict": verdict, "missing": missing,
         "required": REQUIRED_FOR_BUILD,
         "checked_utc": "2026-10-23"}, indent=2) + "\n", encoding="utf-8")
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
