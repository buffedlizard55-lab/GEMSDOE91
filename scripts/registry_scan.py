#!/usr/bin/env python3
"""Registry uniqueness scan for a candidate GeoTIFF (session 10, GEMSDOE91).

Enumerates every *.tif / *.tiff in the GEMSDOE repositories of the GitHub account
`buffedlizard55-lab` (the "GEMSDOE sites" the prompt lists) through the GitHub API via
`gh api`, caches them under data/registry_cache/ (gitignored), and compares the
candidate against each one:

  * exact sha256 match                        -> DUPLICATE (hard stop)
  * Spearman rank correlation of footprint values
                                             -> > 0.90 counts as lane drift
  * share of candidate mass cells within 3 px of the registry raster's mass cells
                                             -> > 70 % counts as lane drift

The 0.90 / 70 % / 3 px thresholds come from the parallel-run protocol in README.md.
The registry raster's "mass cells" are its nonzero cells when there are at most 100 k
of them (binary dot rasters); otherwise its top-K cells by value.

Usage:
    python3 scripts/registry_scan.py --candidate releases/x.tif --out registry/s10_registry_scan.json
    python3 scripts/registry_scan.py --candidate ... --refresh   # re-download the cache
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "registry_cache"
OWNER = "buffedlizard55-lab"
RHO_LIMIT = 0.90
OVERLAP_LIMIT = 0.70
PX_RADIUS = 3.0
TOPK = 60988
SAMPLE_N = 1_000_000
SEED = 91


def gh_json(args: list[str]):
    out = subprocess.run(["gh", "api", *args], check=True, capture_output=True, text=True).stdout
    return json.loads(out) if out.strip() else None


def list_gems_repos() -> list[dict]:
    # --paginate emits one JSON array per page; --jq flattens to one object per line.
    out = subprocess.run(
        ["gh", "api", "--paginate", f"users/{OWNER}/repos?per_page=100",
         "--jq", ".[] | [.name, .default_branch] | @tsv"],
        check=True, capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        name, branch = line.split("\t")
        if "gemsdoe" in name.lower():
            rows.append({"name": name, "branch": branch})
    return rows


def list_tifs(repo: str, branch: str) -> list[dict]:
    tree = gh_json([f"repos/{OWNER}/{repo}/git/trees/{branch}?recursive=1"])
    return [{"path": t["path"], "sha": t["sha"], "size": t.get("size", 0)}
            for t in tree.get("tree", []) if t["path"].lower().endswith((".tif", ".tiff"))]


class RateLimited(RuntimeError):
    """GitHub API quota exhausted. The scan stops; cached files resume on the next run."""


def fetch_cached(repo: str, entry: dict, refresh: bool) -> Path:
    dest = CACHE / repo / entry["path"].replace("/", "__")
    if dest.exists() and not refresh and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        blob = gh_json([f"repos/{OWNER}/{repo}/git/blobs/{entry['sha']}"])
    except subprocess.CalledProcessError as exc:
        if "rate limit" in (exc.stderr or "").lower() or "rate limit" in str(exc).lower():
            raise RateLimited(repo) from exc
        raise
    data = base64.b64decode(blob["content"])
    dest.write_bytes(data)
    return dest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def mass_cells(a: np.ndarray) -> np.ndarray:
    """Boolean mask of a raster's mass cells (see module docstring)."""
    pos = np.isfinite(a) & (a > 0)
    if pos.sum() <= 100_000:
        return pos
    flat = np.where(np.isfinite(a), a, -np.inf).ravel()
    idx = np.argpartition(-flat, TOPK)[:TOPK]
    m = np.zeros(a.size, dtype=bool)
    m[idx] = True
    return m.reshape(a.shape)


def compare(cand: np.ndarray, reg: np.ndarray, fp: np.ndarray) -> dict:
    both = fp & np.isfinite(cand) & np.isfinite(reg)
    idx = np.flatnonzero(both.ravel())
    rng = np.random.default_rng(SEED)
    if idx.size > SAMPLE_N:
        idx = rng.choice(idx, size=SAMPLE_N, replace=False)
    rho = float(spearmanr(cand.ravel()[idx], reg.ravel()[idx]).statistic) if idx.size > 2 else float("nan")
    c_mass = np.isfinite(cand) & (cand > 0)
    r_mass = mass_cells(reg)
    dist_to_reg = ndi.distance_transform_edt(~r_mass)
    frac_c_near_reg = float((dist_to_reg[c_mass] <= PX_RADIUS).mean()) if c_mass.any() else 0.0
    return {"rank_corr_footprint": round(rho, 4),
            "candidate_mass_within_3px_of_registry_mass": round(frac_c_near_reg, 4),
            "registry_mass_cells": int(r_mass.sum())}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--reference", type=Path, default=ROOT / "data" / "official" / "sample_submission.tif")
    ap.add_argument("--out", type=Path, default=ROOT / "registry" / "s10_registry_scan.json")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args(argv)

    cand_sha = sha256_file(args.candidate)
    with rasterio.open(args.candidate) as s:
        cand = s.read(1).astype(np.float64)
    with rasterio.open(args.reference) as s:
        fp = np.isfinite(s.read(1))

    repos = list_gems_repos()
    rows, errors = [], []
    rate_limited = False
    for r in repos:
        if rate_limited:
            break
        try:
            tifs = list_tifs(r["name"], r["branch"])
        except subprocess.CalledProcessError as exc:
            msg = (exc.stderr or "").strip()[:200]
            if "rate limit" in msg.lower():
                rate_limited = True
                break
            errors.append({"repo": r["name"], "error": msg})
            continue
        for t in tifs:
            try:
                path = fetch_cached(r["name"], t, args.refresh)
            except RateLimited:
                rate_limited = True
                break
            except (subprocess.CalledProcessError, KeyError) as exc:
                errors.append({"repo": r["name"], "path": t["path"], "error": str(exc)[:200]})
                continue
            digest = sha256_file(path)
            row = {"repo": r["name"], "path": t["path"], "bytes": path.stat().st_size, "sha256": digest,
                   "exact_duplicate": digest == cand_sha}
            try:
                with rasterio.open(path) as s:
                    shape = [s.height, s.width]
                    crs = str(s.crs)
                    arr = s.read(1).astype(np.float64)
                row.update({"shape": shape, "crs": crs})
                if shape == list(cand.shape):
                    row.update(compare(cand, arr, fp))
                else:
                    row.update({"comparable": False, "note": "shape differs"})
            except Exception as exc:  # unreadable or non-raster: keep the hash, record the reason
                row.update({"comparable": False, "note": f"unreadable: {type(exc).__name__}"})
            rows.append(row)
            print(f"{r['name']}/{t['path']}  sha={digest[:12]}  rho={row.get('rank_corr_footprint')}  "
                  f"near3={row.get('candidate_mass_within_3px_of_registry_mass')}", flush=True)

    comparable = [x for x in rows if x.get("comparable", True) and "rank_corr_footprint" in x]
    complete = not errors and not rate_limited
    summary = {
        "candidate_sha256": cand_sha,
        "complete": complete,
        "rate_limited_stop": rate_limited,
        "scan_errors": len(errors),
        "repos_scanned": len(repos),
        "tif_files_found": len(rows),
        "exact_duplicates": sum(x["exact_duplicate"] for x in rows),
        "comparable_files": len(comparable),
        "max_rank_corr": max((x["rank_corr_footprint"] for x in comparable), default=None),
        "max_candidate_mass_within_3px": max((x["candidate_mass_within_3px_of_registry_mass"]
                                              for x in comparable), default=None),
        "limits": {"rank_corr": RHO_LIMIT, "overlap": OVERLAP_LIMIT, "px_radius": PX_RADIUS},
    }
    summary["lane_drift"] = bool(
        summary["exact_duplicates"] > 0
        or (summary["max_rank_corr"] is not None and summary["max_rank_corr"] > RHO_LIMIT)
        or (summary["max_candidate_mass_within_3px"] is not None
            and summary["max_candidate_mass_within_3px"] > OVERLAP_LIMIT)
    )
    summary["uniqueness_status"] = (
        "INCOMPLETE - re-run after the GitHub API quota resets; no uniqueness claim" if not complete
        else ("LANE DRIFT - do not submit" if summary["lane_drift"] else "PASS (complete scan)"))
    out = {"summary": summary, "files": rows, "errors": errors}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if complete else 3


if __name__ == "__main__":
    sys.exit(main())
