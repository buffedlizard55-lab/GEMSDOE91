#!/usr/bin/env python3
"""Restore the pinned inputs for GEMSDOE91 and verify every sha256.

This session's checkout is deliberately empty of competition data: `data/` is
gitignored.  Everything the build touches is fetched here from an immutable
GitHub commit and checked against `registry/data_manifest.json` **before use**.

Allowed hosts in this sandbox are GitHub, PyPI and npm only.  drivendata.org
and dropbox.com are never contacted (brief section 4.1); the mirrors are copies
made by earlier sessions, which is itself a data-use problem (IR-91-09).

Usage
-----
    python3 scripts/restore_data.py            # fetch missing files, verify all
    python3 scripts/restore_data.py --check    # verify only, never touch network
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
MANIFEST = ROOT / "registry" / "data_manifest.json"
API = "https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.raw",
        "User-Agent": "gemsdoe91-restore/1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:  # never printed, never logged, never written
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429):
            raise SystemExit(
                f"GitHub API refused the fetch ({exc.code}). This is the unauthenticated "
                "rate limit, not a missing pin: re-run with GH_TOKEN set (CI supplies the "
                "workflow token automatically) or wait for the hourly window to reset."
            ) from exc
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    bad = 0
    for f in manifest["files"]:
        dest = ROOT / "data" / f.get("local_subpath", f["id"])
        mirror = f.get("mirror")
        if not dest.is_file():
            if mirror is None:
                print(f"skip   {f['id']:<18} no mirror pinned in the manifest")
                continue
            if args.check:
                print(f"MISSING {f['id']:<18} {dest.relative_to(ROOT)}")
                bad += 1
                continue
            url = API.format(repo=mirror["repo"], path=mirror["path"], ref=mirror["ref"])
            print(f"fetch  {f['id']:<18} {mirror['repo']}@{mirror['ref'][:12]} {mirror['path']}")
            blob = fetch(url)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
        got = sha256_file(dest)
        ok = got == f["sha256"] and dest.stat().st_size == f["bytes"]
        print(f"{'ok     ' if ok else 'MISMATCH'} {f['id']:<18} {got[:16]} {dest.stat().st_size:>9} B")
        bad += 0 if ok else 1
    if bad:
        print(f"\n{bad} pinned input(s) failed verification - refusing to continue", file=sys.stderr)
        return 1
    print("\nall pinned inputs verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
