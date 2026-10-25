#!/usr/bin/env python3
"""Restore/check the frozen pre-experiment registry; never discover references.

The frozen inventory is evidence, not a discovery mechanism.  This script never
expands it by globbing current downloads, removes a dense reference, or calls a
partial index "universal".  A failed restore is reported for *every* unavailable
pin so a runner can fail closed instead of silently treating a partial registry
as complete.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = "buffedlizard55-lab/60GEMSDOE"


def validate_rows(rows, candidate_sha):
    """Reject self-comparisons, duplicate paths, and paths outside approved roots."""
    paths = set()
    for row in rows:
        path = ROOT / row["path"]
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        if not relative.startswith(("data/fleet_registry/", "docs/downloads/")):
            raise ValueError(f"Unexpected registry path: {relative}")
        if relative in paths or row["sha256"] == candidate_sha:
            raise ValueError("Repeated reference path or forbidden candidate self-comparison")
        paths.add(relative)


def restore(row, check=False):
    """Restore one immutable blob, then verify byte count, SHA-256, and Git blob."""
    dest = ROOT / row["path"]
    if dest.is_file():
        data = dest.read_bytes()
    else:
        if check or "git_blob" not in row:
            provenance = "no git_blob pinned" if "git_blob" not in row else "--check forbids network"
            raise ValueError(f"Missing pinned reference: {row['path']} ({provenance})")
        data = subprocess.check_output(
            [
                "gh",
                "api",
                f"repos/{REPO}/git/blobs/{row['git_blob']}",
                "-H",
                "Accept: application/vnd.github.raw",
            ],
            timeout=120,
        )
    if hashlib.sha256(data).hexdigest() != row["sha256"] or len(data) != row["bytes"]:
        raise ValueError(f"Registry SHA256/size mismatch: {row['path']}")
    if "git_blob" in row:
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != row["git_blob"]:
            raise ValueError(f"Registry Git blob mismatch: {row['path']}")
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_suffix(dest.suffix + ".part")
        temp.write_bytes(data)
        temp.replace(dest)
    return row["path"]


def restore_all(rows, *, check=False):
    """Attempt every row and return ``(verified_paths, failures)`` deterministically.

    It is intentional that successful immutable references remain cached when a
    different row cannot be recovered.  The returned failures make the scope
    explicitly incomplete; callers must never use a partial success as a pass.
    """
    restored = []
    failures = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(restore, row, check): row for row in rows}
        for future in as_completed(futures):
            row = futures[future]
            try:
                restored.append(future.result())
            except Exception as exc:  # report all missing/invalid pins, not just the first
                failures.append({"path": row.get("path", "<invalid row>"), "error": str(exc)})
    return sorted(restored), sorted(failures, key=lambda item: item["path"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="Verify existing files; no network")
    args = ap.parse_args()
    inventory = ROOT / "registry/comparison_inventory.json"
    if not inventory.is_file():
        raise SystemExit("Frozen index missing. Obtain its pinned source; do not rebuild it from current downloads.")
    rows = json.loads(inventory.read_text(encoding="utf-8"))["files"]
    candidate = json.loads((ROOT / "docs/run-card.json").read_text(encoding="utf-8")).get("raster_sha256")
    validate_rows(rows, candidate)
    before = inventory.read_bytes()
    restored, failures = restore_all(rows, check=args.check)
    if before != inventory.read_bytes():
        raise RuntimeError("Frozen registry was unexpectedly modified")
    if failures:
        for failure in failures:
            print(f"BLOCK  {failure['path']}: {failure['error']}")
        print(
            f"Verified {len(restored)}/{len(rows)} frozen references; {len(failures)} unavailable or invalid; "
            "inventory unchanged; completeness UNVERIFIED; no experiment run."
        )
        return 1
    print(
        f"Verified {len(restored)} frozen references; inventory unchanged; "
        "completeness UNVERIFIED; no experiment run."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
