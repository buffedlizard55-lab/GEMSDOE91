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
        "User-Agent": "gemsdoe91-restore/1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:  # never printed, never logged, never written
        req.add_header("Authorization", f"Bearer {token}")
    return req


def fetch_to(urls: list[str], dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tmp.open("wb") as out:
            for url in urls:
                try:
                    with urllib.request.urlopen(_request(url), timeout=180) as resp:
                        while True:
                            chunk = resp.read(1 << 20)
                            if not chunk:
                                break
                            out.write(chunk)
                except urllib.error.HTTPError as exc:
                    if exc.code in (403, 429):
                        raise SystemExit(
                            f"GitHub API refused the fetch ({exc.code}); rate limits or permissions "
                            "may be blocking it. This is not proof of a missing pin. Check the "
                            "GitHub connection/rate-limit state; CI supplies its own workflow token."
                        ) from exc
                    raise
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify only")
    ap.add_argument("--only", help="comma-separated pinned IDs; useful for format-only CI")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text())
    wanted = {x.strip() for x in args.only.split(',') if x.strip()} if args.only is not None else None
    available = {f['id'] for f in manifest['files']}
    if wanted is not None and (not wanted or wanted - available):
        ap.error(f'--only must name existing pinned IDs; unknown: {sorted(wanted - available)}')
    bad = 0
    for f in manifest["files"]:
        if wanted is not None and f['id'] not in wanted:
            continue
        dest = ROOT / "data" / f.get("local_subpath", f["id"])
        mirror = f.get("mirror")
        if not dest.is_file():
            if mirror is None:
                print(f"MISSING {f['id']:<18} no mirror pinned; cannot verify this required input")
                bad += 1
                continue
            if args.check:
                print(f"MISSING {f['id']:<18} {dest.relative_to(ROOT)}")
                bad += 1
                continue
            if "blobs" in mirror:
                urls = [BLOB_API.format(repo=mirror["repo"], sha=s) for s in mirror["blobs"]]
                label = f"{len(urls)} git blobs"
            else:
                urls = [API.format(repo=mirror["repo"], path=mirror["path"], ref=mirror["ref"])]
                label = mirror["path"]
            print(f"fetch  {f['id']:<18} {mirror['repo']}@{mirror['ref'][:12]} {label}")
            fetch_to(urls, dest)
        got = sha256_file(dest)
        ok = got == f["sha256"] and dest.stat().st_size == f["bytes"]
        print(f"{'ok     ' if ok else 'MISMATCH'} {f['id']:<18} {got[:16]} {dest.stat().st_size:>9} B")
        bad += 0 if ok else 1
    if bad:
        print(f"\n{bad} pinned input(s) failed verification - refusing to continue", file=sys.stderr)
        return 1
    selected = sum(wanted is None or f["id"] in wanted for f in manifest["files"])
    print(f"\nall {selected} selected pinned inputs verified ({len(manifest['files'])} total manifest entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
