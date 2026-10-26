#!/usr/bin/env python3
"""Restore the matched live-score anchor rasters from their pinned git blobs and verify every SHA-1.

`registry/lfi_anchor_matches.json` (committed, written by `scripts/lfi_match_anchors.py`) lists, for each
USER-REPORTED anchor in `registry/lfi_live_anchors.csv`, the owner repository, path and git-blob SHA-1 of
the published GeoTIFF.  This script only *fetches and verifies* those blobs into `data/lfi_anchors/`
(git-ignored); it never re-discovers or re-matches anything, so a fresh checkout reproduces exactly the
anchor set used by the leaderboard-feedback inversion.

    python3 scripts/restore_lfi_anchors.py            # fetch missing, verify all
    python3 scripts/restore_lfi_anchors.py --check    # verify only, no network
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import sibling_sweep as SS  # noqa: E402  (shared authenticated GitHub API helper)

MATCHES = ROOT / "registry" / "lfi_anchor_matches.json"


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify only; never touch the network")
    args = ap.parse_args()
    rows = [r for r in json.loads(MATCHES.read_text()) if r.get("status") == "MATCHED"]
    bad = fetched = ok = 0
    for r in rows:
        dest = ROOT / r["local"]
        if dest.is_file() and dest.stat().st_size == int(r["bytes"]) and blob_sha1(dest.read_bytes()) == r["git_blob"]:
            ok += 1
            continue
        if args.check:
            print(f"MISSING/BAD {r['local']}")
            bad += 1
            continue
        data = SS._api(f"https://api.github.com/repos/{SS.OWNER}/{r['repo']}/git/blobs/{r['git_blob']}",
                       "application/vnd.github.raw")
        if blob_sha1(data) != r["git_blob"] or len(data) != int(r["bytes"]):
            print(f"SHA MISMATCH {r['repo']}/{r['path']}")
            bad += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
        fetched += 1
    print(f"anchors matched={len(rows)} already-ok={ok} fetched={fetched} bad={bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
