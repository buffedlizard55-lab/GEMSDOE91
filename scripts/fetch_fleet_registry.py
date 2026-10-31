#!/usr/bin/env python3
"""Fetch every hash-pinned raster in registry/comparison_inventory.json.

Each entry records the immutable git blob sha of buffedlizard55-lab/60GEMSDOE
(or a local checkout download). We pull blobs through api.github.com (the only
GitHub host reachable here) and verify sha256 + byte length before use.

Usage: .venv/bin/python scripts/fetch_fleet_registry.py [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "registry" / "comparison_inventory.json"
BLOB_API = "https://api.github.com/repos/{repo}/git/blobs/{sha}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.raw",
        "User-Agent": "gemsdoe91-fleet-registry/1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def fetch(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tmp.open("wb") as out:
            with urllib.request.urlopen(_request(url), timeout=180) as resp:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only")
    args = ap.parse_args()
    inv = json.loads(INV.read_text())["files"]
    bad = 0
    for row in inv:
        dest = ROOT / row["path"]
        if dest.is_file():
            ok = sha256_file(dest) == row["sha256"] and dest.stat().st_size == row["bytes"]
            print(f"{'ok     ' if ok else 'MISMATCH'} {row['path']}")
            bad += 0 if ok else 1
            continue
        if args.check:
            print(f"MISSING {row['path']}")
            bad += 1
            continue
        blob = row.get("git_blob")
        if not blob:
            print(f"NO-BLOB {row['path']} (local-only reference; skipped)")
            continue
        url = BLOB_API.format(repo="buffedlizard55-lab/60GEMSDOE", sha=blob)
        print(f"fetch  {row['path']}")
        fetch(url, dest)
        ok = sha256_file(dest) == row["sha256"] and dest.stat().st_size == row["bytes"]
        print(f"{'ok     ' if ok else 'MISMATCH'} {row['path']}")
        bad += 0 if ok else 1
    if bad:
        print(f"\n{bad} reference(s) failed", file=sys.stderr)
        return 1
    print(f"\nall {len(inv)} comparison-registry references verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
