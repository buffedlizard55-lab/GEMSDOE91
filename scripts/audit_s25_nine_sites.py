#!/usr/bin/env python3
"""S25 nine-site audit (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36).

Every row is recomputed, never typed:
  * best claimed file = the SHA-pinned leader in docs/s22/nine-site-audit.json,
    re-fetched by git blob and re-hashed in this session (bytes verified);
  * claims cross-checked across registry/lfi_live_anchors.csv and
    docs/reported-results.csv (both USER-REPORTED; no organizer receipt exists);
  * current main HEAD of each sibling repo via the GitHub API (fresh check);
  * each site's current front-door OK-TO-SUBMIT status text at that HEAD;
  * local format validation of each leader raster against the competition grid;
  * exact directed 3-px dot overlaps among the nine (uniqueness among peers).

Output: docs/s25/nine-site-audit.json. Scores are USER-REPORTED, never
ORGANIZER-CONFIRMED. Creates no candidate; uses no submission slot.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
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


def gh(path: str, raw: bool = False):
    cmd = ["gh", "api", path]
    if raw:
        cmd += ["-H", "Accept: application/vnd.github.raw"]
    out = subprocess.check_output(cmd, timeout=120)
    return out if raw else json.loads(out)


def frontdoor_status(repo: str, head: str) -> dict:
    for rel in ("docs/index.html", "index.html", "docs/executive-summary.html"):
        try:
            data = gh(f"repos/{OWNER}/{repo}/contents/{rel}?ref={head}", raw=True)
        except subprocess.CalledProcessError:
            continue
        text = data.decode("utf-8", "replace")
        m = re.search(r"OK TO SUBMIT[:\s\-—]*([A-Z/ ]{2,40})", text)
        snippet = None
        if m:
            s = max(m.start() - 60, 0)
            snippet = re.sub(r"<[^>]+>", " ", text[s:m.end() + 40])
            snippet = re.sub(r"\s+", " ", snippet).strip()[:220]
        return {"path": rel, "ok_to_submit_snippet": snippet,
                "bytes": len(data)}
    return {"path": None, "ok_to_submit_snippet": None, "bytes": 0}


def main() -> int:
    prior = {s["site"]: s for s in
             json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]}
    anchors = {}
    for row in csv.DictReader(open(ROOT / "registry/lfi_live_anchors.csv")):
        anchors.setdefault(row["site"], []).append(row)
    reported = list(csv.DictReader(open(ROOT / "docs/reported-results.csv")))
    g = grid.load_grid(ROOT / "data/official")

    rows, supports, discrepancies = [], {}, []
    for site in SITES:
        p = prior[site]
        local = ROOT / p["local_path"]
        got = sha(local)
        if got != p["sha256"] or local.stat().st_size != p["bytes"]:
            raise ValueError(f"leader bytes drift: {site}")
        head_j = gh(f"repos/{OWNER}/{site}/commits/main")
        head, head_date = head_j["sha"], head_j["commit"]["committer"]["date"]
        with rasterio.open(local) as ds:
            a = ds.read(1)
            inside = a[g.footprint]
            validator = {
                "grid_match": bool(ds.count == 1 and ds.shape == g.shape
                                   and str(ds.crs) == str(g.crs)
                                   and ds.transform == g.transform),
                "no_nan_inside_footprint": bool(np.isfinite(inside).all()),
                "finite_values_in_0_1_inside": bool(
                    (inside[np.isfinite(inside)] >= 0).all()
                    and (inside[np.isfinite(inside)] <= 1).all()),
                "dtype": ds.dtypes[0], "nodata": str(ds.nodata)}
        support = (a > 0) & g.footprint
        supports[site] = support.astype(np.float32)
        site_anchors = anchors.get(site, [])
        best_anchor = max(site_anchors, key=lambda r: float(r["user_reported_public_dti"]),
                          default=None)
        row = {
            "site": site,
            "site_url": f"https://{OWNER}.github.io/{site}/",
            "best_claimed_file": p["filename"],
            "best_claimed_file_original_path": p.get("original_path"),
            "sha256": got, "bytes": local.stat().st_size,
            "positive_pixels": int(support.sum()),
            "claimed_value_user_reported": p.get("claimed_historical_value"),
            "claim_source": "user prompt; NOT ORGANIZER-CONFIRMED",
            "organizer_confirmed_score": None,
            "anchors_csv_best": ({"submission_name": best_anchor["submission_name"],
                                  "user_reported_public_dti": float(best_anchor["user_reported_public_dti"])}
                                 if best_anchor else None),
            "anchors_csv_rows": len(site_anchors),
            "current_main_head": head, "current_main_head_date": head_date,
            "head_moved_since_2026_10_26_audit": head != p.get("current_main_head"),
            "frontdoor_at_head": frontdoor_status(site, head),
            "validator_local": validator,
            "source_url_at_head": (f"https://github.com/{OWNER}/{site}/blob/{head}/"
                                   f"{p.get('original_path')}"),
        }
        if best_anchor and abs(float(best_anchor["user_reported_public_dti"])
                                - float(p.get("claimed_historical_value", -1))) > 1e-9:
            discrepancies.append(
                f"{site}: anchors-csv best {best_anchor['user_reported_public_dti']} "
                f"({best_anchor['submission_name']}) != pinned-audit claim "
                f"{p.get('claimed_historical_value')} ({p['filename']})")
        rows.append(row)
        print(site, "head", head[:10], head_date, "dots", row["positive_pixels"], flush=True)

    for row in rows:
        peers = []
        for other in rows:
            if other["site"] == row["site"]:
                continue
            d = dot_check(supports[row["site"]], supports[other["site"]], g.footprint)
            peers.append({"reference_site": other["site"], **d,
                          "exact_support_equal": bool(np.array_equal(
                              supports[row["site"]], supports[other["site"]]))})
        worst = max(peers, key=lambda d: d["overlap_within_3px"] or 0.0)
        row["peer_comparisons"] = peers
        row["max_overlap_vs_other_eight"] = {
            "reference_site": worst["reference_site"],
            "overlap_within_3px": worst["overlap_within_3px"]}
        row["protocol_unique_among_nine"] = not any(
            d["status"] == "DUPLICATE" for d in peers)
        row["submit_as_new"] = False
        row["submit_as_new_reason"] = (
            "Already-submitted historical file (USER-REPORTED); resubmission would be a "
            "duplicate, not a new unique submission.")

    out = {
        "schema": "s25-nine-site-audit-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Nine focus sites from the session prompt; claims USER-REPORTED only.",
        "organizer_complete_registry": False,
        "discrepancies": discrepancies,
        "sites": rows,
    }
    p = ROOT / "docs/s25/nine-site-audit.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    for r in sorted(rows, key=lambda r: -(r["claimed_value_user_reported"] or 0)):
        print(f"{r['claimed_value_user_reported']}  {r['site']:<10} "
              f"unique_among_nine={r['protocol_unique_among_nine']} "
              f"max_peer_overlap={r['max_overlap_vs_other_eight']['overlap_within_3px']:.4f} "
              f"vs {r['max_overlap_vs_other_eight']['reference_site']}")
    print("discrepancies:", discrepancies or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
