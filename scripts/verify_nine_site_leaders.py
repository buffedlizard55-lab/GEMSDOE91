#!/usr/bin/env python3
"""Independent byte-level check of the nine user-named GEMSDOE leader rasters.

What it does (no claims are taken from prose):
  1. Lists each sibling repo buffedlizard55-lab/GEMSDOE<n> through the GitHub API
     (git trees, default branch) and finds the .tif whose path contains the
     hash token the user cited for that site.
  2. Downloads the exact blob bytes (GitHub raw content) into a cache dir
     (outside git), computes SHA-256 and reads the raster with rasterio.
  3. Checks single-band float32 binary finite values and grid metadata.
     This is not an independent sample-footprint or organizer format check.
  4. Computes dot overlap: fraction of dots of file A within 3 px (Euclidean
     distance via KD-tree) of any dot of file B, for every ordered pair.
  5. Optionally also checks local candidate rasters passed with --candidate.

Dots are positive pixels; nonbinary finite values and empty supports are rejected.
The older evidence/nine-site-leader-check.json used Chebyshev distance and is
immutable historical evidence. The corrected output defaults to work/.

Usage:
  python3 scripts/verify_nine_site_leaders.py --cache /tmp/nine \
      --candidate docs/downloads/<file>.tif --out work/nine-site-leader-check-euclidean.json
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

REPO_OWNER = "buffedlizard55-lab"

# site -> (user-cited score, hash token that identifies the file in that site's repo)
# The suffix is the encoding the user cited in the prompt ("-nan" or "-zeros"; "" = none).
LEADERS = {
    "GEMSDOE24": ("0.2477", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1", "-nan"),
    "GEMSDOE25": ("0.2600", "dotted-h19-5-d2-8-20261002-e56ea318af89", "-nan"),
    "GEMSDOE27": ("0.2449", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1", "-nan"),
    "GEMSDOE28": ("0.2710", "h36-1-rung30-blind-r1-20261003-b531dae0a36f", "-nan"),
    "GEMSDOE30": ("0.2600", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", ""),
    "GEMSDOE31": ("0.2708", "h27-4-solo-d28-20261004-8acb75e1", "-nan"),
    "GEMSDOE32": ("0.2778", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e", "-zeros"),
    "GEMSDOE33": ("0.2632", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", ""),
    "GEMSDOE36": ("0.2750", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6", "-zeros"),
}


def gh(args: list[str]) -> bytes:
    return subprocess.run(["gh", *args], check=True, capture_output=True).stdout


def find_tif(site: str, token: str, suffix: str) -> dict:
    tree = json.loads(gh(["api", f"repos/{REPO_OWNER}/{site}/git/trees/main?recursive=1"]))
    if tree.get("truncated") is not False:
        raise ValueError(f"{site}: GitHub tree is missing or truncated")
    hits = [t for t in tree["tree"] if t["path"].endswith(f"{token}{suffix}.tif")]
    if len(hits) != 1:
        raise SystemExit(f"{site}: expected exactly one tif for token {token}, found {[h['path'] for h in hits]}")
    return hits[0]


def fetch(site: str, entry: dict, cache: Path) -> Path:
    dest = cache / f"{site}__{Path(entry['path']).name}"
    if not dest.exists() or dest.stat().st_size == 0:
        blob = gh(["api", "-H", "Accept: application/vnd.github.raw",
                   f"repos/{REPO_OWNER}/{site}/contents/{entry['path']}"])
        dest.write_bytes(blob)
    content = dest.read_bytes()
    blob_id = hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
    if blob_id != entry["sha"]:
        raise ValueError(f"{site}: cached or fetched Git blob differs from the selected tree")
    return dest


def dots_of(path: Path):
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype(np.float64)
        meta = {
            "crs": ds.crs.to_string() if ds.crs else None,
            "shape": [ds.height, ds.width],
            "transform": list(ds.transform)[:6],
            "dtype": ds.dtypes[0],
            "count": ds.count,
            # NaN is valid TIFF metadata but not valid JSON; preserve its
            # meaning as a string rather than emitting a JavaScript NaN token.
            "nodata": ("nan" if ds.nodata is not None and np.isnan(ds.nodata)
                       else float(ds.nodata) if ds.nodata is not None else None),
        }
    if meta["count"] != 1 or meta["dtype"] != "float32" or meta["crs"] is None:
        raise ValueError(f"{path}: georeferenced single-band float32 required")
    if np.isinf(arr).any():
        raise ValueError(f"{path}: infinite cells are not allowed")
    finite = np.isfinite(arr)
    footprint_vals = arr[finite]
    if not footprint_vals.size or not np.isin(footprint_vals, [0, 1]).all():
        raise ValueError(f"{path}: finite dot values must be binary")
    meta.update({
        "nan_pixels": int((~finite).sum()),
        "min_finite": float(footprint_vals.min()) if footprint_vals.size else None,
        "max_finite": float(footprint_vals.max()) if footprint_vals.size else None,
        "in_0_1": bool(footprint_vals.size and footprint_vals.min() >= 0 and footprint_vals.max() <= 1),
        "dots": int((np.nan_to_num(arr, nan=0.0) > 0).sum()),
    })
    rows, cols = np.nonzero(np.nan_to_num(arr, nan=0.0) > 0)
    return np.column_stack([rows, cols]).astype(np.float64), meta


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def within3(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) == 0 or len(b) == 0:
        raise ValueError("empty dot support is unverified, not a uniqueness pass")
    d, _ = cKDTree(b).query(a, k=1, p=2)  # shared novelty gate: Euclidean pixels
    return float((d <= 3).mean())


def maximum_peer_overlaps(overlap: dict[str, float]) -> dict[str, float]:
    """Nine leaders against the other eight only, never optional candidates.

    Missing comparisons are an error. Preserve full precision because rounding
    at the strict 70% boundary could otherwise change a duplicate verdict.
    """
    return {
        site: max(overlap[f"{site} -> {peer}"] for peer in LEADERS if peer != site)
        for site in LEADERS
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data/nine_site_leaders")
    ap.add_argument("--candidate", action="append", default=[])
    ap.add_argument("--out", default="work/nine-site-leader-check-euclidean.json")
    args = ap.parse_args()

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]

    files: dict[str, dict] = {}
    for site, (score, token, suffix) in LEADERS.items():
        entry = find_tif(site, token, suffix)
        p = fetch(site, entry, cache)
        dots, meta = dots_of(p)
        files[site] = {"score_user_cited": score, "encoding_suffix": suffix, "repo_path": entry["path"],
                       "blob_sha": entry["sha"], "sha256": sha256(p), "dots_xy": dots, **meta}
    for c in args.candidate:
        p = root / c
        dots, meta = dots_of(p)
        files[f"CANDIDATE:{p.name}"] = {"score_user_cited": None, "repo_path": c, "sha256": sha256(p),
                                        "dots_xy": dots, **meta}

    names = list(files)
    grid = (files[names[0]]["crs"], files[names[0]]["shape"], files[names[0]]["transform"])
    if any((files[n]["crs"], files[n]["shape"], files[n]["transform"]) != grid for n in names):
        raise ValueError("leader/candidate grids do not match")
    overlap = {}
    for a in names:
        for b in names:
            if a != b:
                overlap[f"{a} -> {b}"] = within3(files[a]["dots_xy"], files[b]["dots_xy"])

    out = {
        "schema": "nine-site-leader-check-v2",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Git-tree-verified blob bytes; binary dots = value>0; directed A-to-B overlap uses Euclidean distance <=3 px. No independent sample-footprint or organizer receipt check.",
        "score_evidence": "User-reported claims only; no organizer receipt or score estimate.",
        "files": {k: {kk: vv for kk, vv in v.items() if kk != "dots_xy"} | {"dots": int(len(v["dots_xy"]))}
                  for k, v in files.items()},
        "max_overlap_into_any_other_leader": maximum_peer_overlaps(overlap),
        "overlap_pairs": overlap,
    }
    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"out": args.out, "max_overlap_into_any_other_leader": out["max_overlap_into_any_other_leader"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
