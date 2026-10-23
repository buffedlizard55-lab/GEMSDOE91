#!/usr/bin/env python3
"""Regenerate releases/MANIFEST.json from the files on disk and the ledger.

`releases/*.tif` are gitignored, so the manifest is the only contract that a
rebuild reproduced the same bytes. Several builders write their own entries; this
script is the single authority: it scans `releases/`, takes `axis` and `n_dots`
for each file from `ledger/submissions.csv` (matching either the NaN or the zeros
sha256), and rewrites the manifest with one entry per file.

    python3 scripts/update_release_manifest.py            # rewrite + verify
    python3 scripts/update_release_manifest.py --check    # verify only

Exit code 1 if any file on disk is not in the manifest, any manifest entry is
missing on disk, or any sha256 differs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"
LEDGER = ROOT / "ledger" / "submissions.csv"
MANIFEST = RELEASES / "MANIFEST.json"

NOTE = ("Releases are NOT committed (this repo does not publish derived copies of competition "
        "rasters). These hashes are the contract: rebuild with `python3 scripts/restore_data.py "
        "&& make releases` and every sha256 below must reappear byte for byte. CI enforces this.")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ledger_index() -> dict[str, dict]:
    """sha256 (NaN twin or zeros twin) -> {axis, n_dots, value, id}."""
    out: dict[str, dict] = {}
    if not LEDGER.is_file():
        return out
    with LEDGER.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            entry = {"axis": row.get("axis", ""), "n_dots": row.get("n_dots", ""),
                     "value": row.get("value", ""), "id": row.get("id", "")}
            for key in (row.get("sha256", ""), row.get("sha256_zeros", "")):
                if key.strip():
                    out[key.strip()] = entry
    return out


def build() -> tuple[dict, list[str]]:
    idx = ledger_index()
    files = sorted(p for p in RELEASES.glob("*.tif"))
    entries, problems = [], []
    for p in files:
        digest = sha256_file(p)
        meta = idx.get(digest, {})
        if not meta:
            problems.append(f"{p.name}: sha256 not in the ledger (unregistered release)")
        entries.append({
            "file": p.name,
            "sha256": digest,
            "bytes": p.stat().st_size,
            "axis": meta.get("axis", ""),
            "n_dots": int(meta["n_dots"]) if str(meta.get("n_dots", "")).strip().isdigit() else None,
            "ledger_id": meta.get("id", ""),
        })
    manifest = {"schema_version": 1, "parent": "h33-h33-2-b2-20261004-e5eb6e7e",
                "note": NOTE, "files": entries}
    return manifest, problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    manifest, problems = build()
    if args.check:
        if not MANIFEST.is_file():
            print("MISSING releases/MANIFEST.json")
            return 1
        have = {f["file"]: f for f in json.loads(MANIFEST.read_text())["files"]}
        want = {f["file"]: f for f in manifest["files"]}
        for name in sorted(set(have) - set(want)):
            problems.append(f"{name}: in the manifest but not built")
        for name in sorted(set(want) - set(have)):
            problems.append(f"{name}: built but not in the manifest")
        for name in sorted(set(have) & set(want)):
            if have[name]["sha256"] != want[name]["sha256"]:
                problems.append(f"{name}: sha256 changed")
    else:
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")

    for p in problems:
        print("PROBLEM:", p)
    print(f"manifest: {len(manifest['files'])} files, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
