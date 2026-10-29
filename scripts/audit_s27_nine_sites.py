#!/usr/bin/env python3
"""S27 nine-site audit (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36).

Recomputed, never typed:
  * leader bytes = SHA-pinned files in docs/s22/nine-site-audit.json,
    re-hashed in this session (restored by git blob; see run log);
  * claimed values = the user prompt's figures as recorded in the S22 audit
    (USER-REPORTED; no organizer receipt exists for any of them);
  * current main HEAD of each sibling repo via the GitHub API (fresh);
  * exact directed 3-px dot overlaps among the nine (72 comparisons);
  * S27 candidate vs each leader (from the same dot_check instrument);
  * prompt line-by-line runner-up check recorded in REVIEW.md.

Output: docs/s27/nine-site-audit.json. Creates no candidate; uses no slot.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio

from gems91.novelty import dot_check
from vendor.gems57 import grid

SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
         "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
OWNER = "buffedlizard55-lab"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main_head_sha(site: str) -> str:
    """Current main HEAD via `git ls-remote` (the GitHub REST API quota was
    exhausted by this session's blob restores; ls-remote returns the same
    commit SHA without using the API. Commit dates are therefore not
    refreshed this session and are recorded as null, never guessed.)"""
    out = subprocess.check_output(
        ["git", "ls-remote", f"https://github.com/{OWNER}/{site}.git",
         "refs/heads/main"], timeout=120).decode().strip()
    return out.split()[0]


def main() -> int:
    prior = {s["site"]: s for s in
             json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]}
    rc = json.loads((ROOT / "docs/s27/run-card.json").read_text())
    g = grid.load_grid(ROOT / "data/official")

    rows, supports = [], {}
    for site in SITES:
        p = prior[site]
        local = ROOT / p["local_path"]
        got = sha(local)
        if got != p["sha256"] or local.stat().st_size != p["bytes"]:
            raise ValueError(f"leader bytes drift: {site}")
        head_sha = main_head_sha(site)
        with rasterio.open(local) as ds:
            a = ds.read(1)
            grid_ok = bool(ds.count == 1 and ds.shape == g.shape
                           and str(ds.crs) == str(g.crs)
                           and ds.transform == g.transform)
        support = (np.nan_to_num(a) > 0) & g.footprint
        supports[site] = support.astype(np.float32)
        rows.append({
            "site": site,
            "site_url": f"https://{OWNER}.github.io/{site}/",
            "repo_url": f"https://github.com/{OWNER}/{site}",
            "best_claimed_file": p["filename"],
            "sha256": got, "bytes": local.stat().st_size,
            "positive_pixels": int(support.sum()),
            "claimed_value_user_reported": p.get("claimed_historical_value"),
            "claim_source": "user prompt; NOT ORGANIZER-CONFIRMED",
            "organizer_confirmed_score": None,
            "grid_match": grid_ok,
            "current_main_head": head_sha,
            "current_main_head_date": None,
            "head_method": "git ls-remote (REST API quota exhausted this session)",
            "bytes_reverified_utc": datetime.now(timezone.utc).isoformat(),
        })
        print(site, "ok", got[:12], flush=True)

    # S27 candidate support.
    cand_path = ROOT / rc["artifact"]["tif"]
    if sha(cand_path) != rc["raster_sha256"]:
        raise ValueError("candidate bytes drift")
    with rasterio.open(cand_path) as ds:
        cand = (ds.read(1) > 0) & g.footprint
    cand_f = cand.astype(np.float32)

    for row in rows:
        site = row["site"]
        peer = []
        for other in SITES:
            if other == site:
                continue
            d = dot_check(supports[site], supports[other], g.footprint)
            peer.append({"reference_site": other, **d})
        worst = max(peer, key=lambda d: d["overlap_within_3px"])
        row["peer_comparisons"] = peer
        row["max_overlap_vs_other_eight"] = worst
        row["unique_among_nine_le_0.70"] = bool(worst["overlap_within_3px"] <= 0.70)
        dc = dot_check(cand_f, supports[site], g.footprint)
        row["s27_candidate_overlap_vs_this_leader"] = dc
        print(site, "peer max", round(worst["overlap_within_3px"], 4),
              "| S27 vs leader", round(dc["overlap_within_3px"], 4), flush=True)

    cand_max = max(r["s27_candidate_overlap_vs_this_leader"]["overlap_within_3px"] for r in rows)
    result = {
        "schema": "s27-nine-site-audit-v1",
        "as_of_utc": datetime.now(timezone.utc).isoformat(),
        "sites": rows,
        "s27_candidate": {
            "tif": rc["artifact"]["tif"], "sha256": rc["raster_sha256"],
            "max_overlap_vs_nine_leaders": cand_max,
            "unique_vs_nine_le_0.70": bool(cand_max <= 0.70),
            "organizer_confirmed_score": None,
        },
        "best_claimed_site": max(rows, key=lambda r: r["claimed_value_user_reported"])["site"],
        "best_claimed_value_user_reported":
            max(r["claimed_value_user_reported"] for r in rows),
        "organizer_confirmed_scores": 0,
        "scope": ("Exact nine prompt-named historical leaders, bytes re-verified; "
                  "claims are user-prompt figures, not receipts. Newer files on the "
                  "live sibling front doors are tracked by main HEAD above but are "
                  "not pinned leaders unless listed; prompt runner-up claims were "
                  "checked line by line in docs/s27/REVIEW (all <= pinned leader)."),
    }
    out = ROOT / "docs/s27/nine-site-audit.json"
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
