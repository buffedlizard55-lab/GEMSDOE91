#!/usr/bin/env python3
"""Preflight: can a build start here at all, and for which axis?

A build needs the pinned inputs of the axis it implements, and no others. The
verdict is therefore reported **per axis** from the manifest's
``axis_requirements``: an absent entry blocks only the axes that read it (brief
section 4.2). A stale global verdict is what stalled sessions 1-3 while every
input the repository actually needed was already pinned and fetchable.

Exit 0 = at least one axis has inputs, 1 = none does. This is DATA readiness
only, never permission to run an experiment or submit. For protocol blockers
use scripts/experiment_preflight.py; data availability cannot assign a lane.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems91.pinned import load_manifest, local_path_for, verify_entry  # noqa: E402

# The repository-wide minimum: the format reference plus the parent.
REQUIRED_FOR_BUILD = ["sample_submission", "parent_r0_nan"]


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

    # Per-axis readiness, from the manifest's own requirement table.
    ok_ids = {fid for fid in by_id
              if verify_entry(by_id[fid], local_path_for(by_id[fid], root))[0]}
    readiness = {}
    for axis, needs in man.get("axis_requirements", {}).items():
        gap = [n for n in needs if n not in ok_ids]
        readiness[axis] = {"ready": not gap, "missing": gap}
    ready_axes = [a for a, st in readiness.items() if st["ready"]]

    # The global verdict must reflect actual per-axis readiness. The two
    # minimum references can be present while every implemented axis is still
    # missing an additional input (for example the catalogue or feature stack).
    verdict = "INPUTS AVAILABLE" if ready_axes else "BUILD BLOCKED"
    print("\n".join(lines))
    print(f"\n{verdict}: {len(REQUIRED_FOR_BUILD) - len(missing)}/{len(REQUIRED_FOR_BUILD)} "
          f"required inputs verified")
    if missing:
        print("missing (repository-wide): " + ", ".join(missing))
    print("\naxis readiness:")
    for axis, st in readiness.items():
        mark = "READY  " if st["ready"] else "blocked"
        extra = "" if st["ready"] else f"  (missing: {', '.join(st['missing'])})"
        print(f"  [{mark}] {axis}{extra}")
    if ready_axes:
        print(f"\n{len(ready_axes)} axis/axes have inputs here (NOT experiment approval): {', '.join(ready_axes)}")
    else:
        print("\nNo axis has all of its pinned inputs; a build cannot start.")
    Path("registry").mkdir(exist_ok=True)
    Path("registry/preflight.json").write_text(json.dumps(
        {"verdict": "INPUTS AVAILABLE" if ready_axes else "BUILD BLOCKED",
         "scope": "Data availability only; not experiment or submission approval",
         "experiment_authorized": False,
         "missing": missing,
         "required": REQUIRED_FOR_BUILD,
         "ready_axes": ready_axes,
         "axis_readiness": readiness,
         "checked_utc": datetime.now(timezone.utc).date().isoformat()}, indent=2) + "\n", encoding="utf-8")
    return 0 if ready_axes else 1


if __name__ == "__main__":
    raise SystemExit(main())
