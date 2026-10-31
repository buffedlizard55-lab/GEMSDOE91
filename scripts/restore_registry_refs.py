#!/usr/bin/env python3
"""Restore the nine-site leader TIFFs and the 64-raster fleet registry.

Follows the same fail-closed pattern as scripts/restore_data.py: fetch from the
immutable GitHub commit recorded in the pinned inventories, verify SHA-256 and
byte length before the file is allowed to stay on disk.

Sources (both commit-pinned, recorded in-repo):
  * docs/review-20261030/nine-site-snapshot.json  (9 prompt-named site leaders)
  * docs/s22/nine-site-audit.json                 (sha256/bytes witness for the 9)
  * registry/comparison_inventory.json            (64-raster fleet registry at
    buffedlizard55-lab/60GEMSDOE@02563d07fb85d2f4d35887503d380d34d4017197)

Usage: python3 scripts/restore_registry_refs.py [--check]
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
API_CONTENTS = "https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _request(url: str) -> urllib.request.Request:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.raw",
        "User-Agent": "gemsdoe91-restore-registry/1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return req


def fetch_to(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tmp.open("wb") as out, urllib.request.urlopen(_request(url), timeout=300) as resp:
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
    ap.add_argument("--check", action="store_true", help="verify only, no network")
    args = ap.parse_args()

    snapshot = json.loads((ROOT / "docs/review-20261030/nine-site-snapshot.json").read_text())
    audit = {s["site"]: s for s in json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]}
    inventory = json.loads((ROOT / "registry/comparison_inventory.json").read_text())

    jobs = []
    for s in snapshot["sites"]:
        site = s["site"]
        wit = audit[site]
        if wit["sha256"] != s["sha256"] or wit["bytes"] != s["bytes"]:
            print(f"WITNESS MISMATCH for {site}: snapshot vs docs/s22/nine-site-audit.json", file=sys.stderr)
            return 2
        jobs.append({
            "label": f"nine:{site}",
            "dest": ROOT / wit["local_path"],
            "url": API_CONTENTS.format(repo=f"{s['repository_owner']}/{s['repository_name']}",
                                       path=s["repository_path"], ref=s["commit"]),
            "sha256": s["sha256"],
            "bytes": s["bytes"],
        })
    repo = "buffedlizard55-lab/60GEMSDOE"
    ref = "02563d07fb85d2f4d35887503d380d34d4017197"
    unavailable = []
    for f in inventory["files"]:
        rel = f["path"]
        src = f.get("source_url", "")
        if "/blob/" not in src:
            # Local-checkout inherited artifact: verify only if present here.
            if (ROOT / rel).is_file() and sha256_file(ROOT / rel) == f["sha256"]:
                print(f"ok     fleet:{Path(rel).name:<54} local inherited artifact verified")
            else:
                unavailable.append(rel)
                print(f"UNAVAIL fleet:{Path(rel).name:<54} no upstream mirror; local bytes absent")
            continue
        jobs.append({
            "label": f"fleet:{Path(rel).name}",
            "dest": ROOT / rel,
            "url": API_CONTENTS.format(repo=repo, path="registry/rasters/" + Path(rel).name, ref=ref),
            "sha256": f["sha256"],
            "bytes": f["bytes"],
        })

    bad = 0
    for job in jobs:
        dest = job["dest"]
        if not dest.is_file():
            if args.check:
                print(f"MISSING  {job['label']}")
                bad += 1
                continue
            print(f"fetch  {job['label']}")
            # fleet rasters live at registry/rasters/... upstream; inventory path
            # already includes the local data/fleet_registry/ prefix but upstream
            # path is registry/rasters/<name>.
            url = job["url"]
            if job["label"].startswith("fleet:"):
                url = API_CONTENTS.format(repo=repo, path="registry/rasters/" + Path(job["label"]).name[len("fleet:"):], ref=ref)
            fetch_to(url, dest)
        got = sha256_file(dest)
        ok = got == job["sha256"] and dest.stat().st_size == job["bytes"]
        print(f"{'ok     ' if ok else 'MISMATCH'} {job['label']:<60} {got[:12]} {dest.stat().st_size:>8} B")
        if not ok:
            bad += 1
    print(f"\n{len(jobs)} reference raster(s) checked; {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
