#!/usr/bin/env python3
"""Re-derive the nine-site leader audit from bytes, not from stored JSON.

For each of the nine focus sites (GEMSDOE24/25/27/28/30/31/32/33/36) this script:

1. fetches the site's best-claimed GeoTIFF from the user's OWN public GitHub repo at the
   pinned commit recorded in docs/s25/nine-site-audit.json (GitHub contents API, raw);
2. verifies the sha256 against the recorded hash (refuses to continue on mismatch);
3. checks single band, float32, EPSG:32611, 100 m, shared grid, finite values in
   [0, 1] and positive-pixel count. The sample footprint is NOT available to this
   diagnostic: it cannot establish whether any NaNs occur inside it;
4. computes pairwise 3-px overlap: fraction of candidate's positive pixels within
   Euclidean 3 px of any positive pixel of the reference (the protocol's dot-overlap);
5. computes Spearman rank correlation on a fixed random sample of cells where both
   rasters are finite (protocol surface-correlation check, sampled not exhaustive);
6. optionally checks a local candidate (e.g. an S25 research TIFF) against all nine.

Sampled Spearman and the unmasked overlaps are diagnostics only, NOT the
protocol's exact full-footprint surface or final-dot clearance checks.

No competition data is fetched. Only the user's own submission rasters are read.

Usage:  python3 scripts/nine_site_leaders_20261028.py --out docs/nine-site-20261028/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage, stats

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs" / "s25" / "nine-site-audit.json"
LOCAL_CANDIDATE = ROOT / "docs" / "downloads" / "gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif"
API = "https://api.github.com/repos/{repo}/contents/{path}?ref={ref}"
SAMPLE_N = 400_000
SEED = 20261028


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(repo: str, path: str, ref: str) -> bytes:
    url = API.format(repo=repo, path=path, ref=ref)
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.raw",
        "User-Agent": "gemsdoe91-nine-site-audit/1",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:  # never printed or stored
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def load(data: bytes):
    """Open from memory and return (array float64 with NaN kept, profile info)."""
    from rasterio.io import MemoryFile
    with MemoryFile(data) as mf, mf.open() as ds:
        arr = ds.read(1).astype(np.float64)
        info = {
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "crs": ds.crs.to_string() if ds.crs else None,
            "res": [float(ds.res[0]), float(ds.res[1])],
            "shape": [int(ds.height), int(ds.width)],
            "transform": list(ds.transform)[:6],
            "nodata": ("nan" if ds.nodata is not None and np.isnan(ds.nodata)
                       else float(ds.nodata) if ds.nodata is not None else None),
        }
    return arr, info


def positive_mask(arr: np.ndarray) -> np.ndarray:
    return np.isfinite(arr) & (arr > 0)


def overlap_within(cand: np.ndarray, ref: np.ndarray, radius: float = 3.0) -> float:
    """Fraction of candidate positive pixels within `radius` px of a reference positive pixel."""
    cm = positive_mask(cand)
    rm = positive_mask(ref)
    n = int(cm.sum())
    if n == 0 or not rm.any():
        raise ValueError("empty dot support is unverified, not a uniqueness pass")
    dist = ndimage.distance_transform_edt(~rm)
    return float((dist[cm] <= radius).sum() / n)


def spearman_sample(a: np.ndarray, b: np.ndarray) -> float:
    both = np.isfinite(a) & np.isfinite(b)
    idx = np.flatnonzero(both.ravel())
    rng = np.random.default_rng(SEED)
    if idx.size > SAMPLE_N:
        idx = rng.choice(idx, size=SAMPLE_N, replace=False)
    if idx.size < 2:
        return None
    x, y = a.ravel()[idx], b.ravel()[idx]
    if np.ptp(x) == 0 or np.ptp(y) == 0:
        return None  # undefined correlation is not a uniqueness pass
    rho, _ = stats.spearmanr(x, y)
    return float(rho) if np.isfinite(rho) else None


def format_checks(arr: np.ndarray, info: dict) -> dict:
    finite = np.isfinite(arr)
    vals = arr[finite]
    in_range = bool(vals.size and not np.isinf(arr).any()
                    and vals.min() >= 0.0 and vals.max() <= 1.0)
    return {
        "single_band": info["count"] == 1,
        "dtype_float32": info["dtype"] == "float32",
        "crs_is_32611": info["crs"] == "EPSG:32611",
        "res_is_100m": info["res"] == [100.0, 100.0],
        "finite_in_0_1": in_range,
        "nan_count": int(np.isnan(arr).sum()),
        "infinity_count": int(np.isinf(arr).sum()),
        "footprint_verified": False,
        "positive_pixels": int(positive_mask(arr).sum()),
    }


def same_grid(a: dict, b: dict) -> bool:
    """Shape alone cannot establish geographic alignment."""
    return all(a[k] == b[k] for k in ("count", "crs", "shape", "transform"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="output directory (JSON + cache-free)")
    ap.add_argument("--local-candidate", default=str(LOCAL_CANDIDATE))
    args = ap.parse_args()

    audit = json.loads(AUDIT.read_text())
    rows = []
    arrays = {}
    grid_ref = None

    for site in audit["sites"]:
        name = site["site"]
        url = site["source_url_at_head"]
        # https://github.com/<owner>/<repo>/blob/<sha>/<path>
        parts = url.split("github.com/", 1)[1].split("/")
        owner, repo, _blob, sha = parts[0], parts[1], parts[2], parts[3]
        path = "/".join(parts[4:])
        data = fetch(f"{owner}/{repo}", path, sha)
        digest = sha256_bytes(data)
        if digest != site["sha256"]:
            print(f"SHA MISMATCH {name}: {digest} != {site['sha256']}", file=sys.stderr)
            return 2
        arr, info = load(data)
        arrays[name] = arr
        fc = format_checks(arr, info)
        if grid_ref is None:
            grid_ref = info
        rows.append({
            "site": name,
            "file": site["best_claimed_file"],
            "source_url": url,
            "sha256": digest,
            "bytes": len(data),
            "claimed_user_reported_score": site["claimed_value_user_reported"],
            "organizer_confirmed_score": None,
            "grid_matches_first_site": same_grid(info, grid_ref),
            "shape": info["shape"],
            "format": fc,
        })
        print(f"{name}: sha OK, positives={fc['positive_pixels']}, grid_ok={rows[-1]['grid_matches_first_site']}", flush=True)
        if not rows[-1]['grid_matches_first_site'] or not fc['single_band'] or not fc['dtype_float32'] or not fc['finite_in_0_1']:
            raise ValueError(f"{name}: grid or finite-value check failed")

    # local research candidate
    cand_arr, cand_info = load(Path(args.local_candidate).read_bytes())
    cand_name = Path(args.local_candidate).name
    cand_fmt = format_checks(cand_arr, cand_info)
    if not same_grid(cand_info, grid_ref) or not cand_fmt['dtype_float32'] or not cand_fmt['finite_in_0_1']:
        raise ValueError("candidate grid or finite-value check failed")

    names = [r["site"] for r in rows]
    pair = {}
    for a in names:
        for b in names:
            if a == b:
                continue
            pair[f"{a}->{b}"] = round(overlap_within(arrays[a], arrays[b]), 6)

    cand_vs = {}
    for n in names:
        cand_vs[n] = {
            "overlap_within_3px": overlap_within(cand_arr, arrays[n]),
            "spearman_sampled": spearman_sample(cand_arr, arrays[n]),
        }
    # repo-tracked research TIFFs (same grid) — the protocol's registry proxy available locally
    repo_rows = []
    skipped = []
    for tif in sorted((ROOT / "docs" / "downloads").glob("*.tif")):
        if tif.name == Path(args.local_candidate).name:
            continue
        with rasterio.open(tif) as ds:
            candidate_grid = (cand_info["count"], cand_info["shape"], cand_info["crs"], cand_info["transform"])
            actual_grid = (ds.count, list(ds.shape), ds.crs.to_string() if ds.crs else None, list(ds.transform)[:6])
            if actual_grid != candidate_grid:
                skipped.append({"file": f"docs/downloads/{tif.name}", "reason": "grid mismatch"})
                continue
            ref = ds.read(1).astype(np.float64)
        ref_finite = ref[np.isfinite(ref)]
        if (np.isinf(ref).any() or not ref_finite.size or ref_finite.min() < 0 or ref_finite.max() > 1
                or not positive_mask(ref).any()):
            skipped.append({"file": f"docs/downloads/{tif.name}", "reason": "empty or invalid support"})
            continue
        repo_rows.append({
            "file": f"docs/downloads/{tif.name}",
            "overlap_within_3px": overlap_within(cand_arr, ref),
            "positive_pixels": int(positive_mask(ref).sum()),
        })
    repo_rows.sort(key=lambda r: r["overlap_within_3px"], reverse=True)

    worst = max(cand_vs.items(), key=lambda kv: kv[1]["overlap_within_3px"])
    defined_rho = [(name, row) for name, row in cand_vs.items() if row['spearman_sampled'] is not None]
    worst_rho = max(defined_rho, key=lambda kv: abs(kv[1]["spearman_sampled"])) if defined_rho else None

    result = {
        "schema": "nine-site-leaders-20261028-v1",
        "scope": "GEMSDOE24/25/27/28/30/31/32/33/36 best-claimed files; scores USER-REPORTED, not organizer-confirmed",
        "sources": "user-owned GitHub repos at pinned commits (no competition data fetched)",
        "sites": rows,
        "reference_grid": grid_ref,
        "pairwise_overlap_within_3px": pair,
        "local_candidate": {
            "file": cand_name,
            "sha256": sha256_bytes(Path(args.local_candidate).read_bytes()),
            "format": cand_fmt,
            "vs_nine": cand_vs,
            "max_overlap_site": {"site": worst[0], "overlap": worst[1]["overlap_within_3px"]},
            "max_abs_spearman_site": ({"site": worst_rho[0], "rho": worst_rho[1]["spearman_sampled"]}
                                      if worst_rho else None),
            "repo_tif_comparisons": {"count": len(repo_rows), "top": repo_rows[:8], "skipped": skipped},
        },
        "rules": {
            "overlap_duplicate_threshold": 0.70,
            "spearman_stop_threshold": 0.90,
            "note": "Euclidean overlap is unmasked; Spearman is sampled. Neither is a full-footprint protocol clearance.",
        },
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "nine-site-leaders-20261028.json").write_text(json.dumps(result, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: result["local_candidate"][k] for k in ("file", "max_overlap_site", "max_abs_spearman_site")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
