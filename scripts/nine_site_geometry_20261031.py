#!/usr/bin/env python3
"""Nine-site leader dot-geometry + pairwise overlap audit (local bytes only).

Recomputes, from SHA-256-verified local TIFFs, everything the executive summary
claims about the nine prompt-named site leaders:
  * positive-pixel count and outside-footprint encoding
  * median / quartile distance of dots to the mapped catalogue
  * pairwise directed overlap within 3 px (row = candidate share)
  * rank correlation of each pair of dot surfaces

Output: docs/review-20261031/nine-site-geometry.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems91.novelty import SurfaceProbe, dot_check

OUT = ROOT / "docs/review-20261031"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    audit = json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())
    snapshot = {s["site"]: s for s in json.loads(
        (ROOT / "docs/review-20261030/nine-site-snapshot.json").read_text())["sites"]}
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        cat_arr = ds.read(1)
    catalogue = (cat_arr == 1) & footprint
    d_cat = ndi.distance_transform_edt(~catalogue)

    sites, preds = [], {}
    for s in audit["sites"]:
        name = s["site"]
        p = ROOT / s["local_path"]
        with rasterio.open(p) as ds:
            a = ds.read(1)
            crs, shape, nodata = str(ds.crs), ds.shape, ds.nodata
        got = sha(p)
        if got != s["sha256"]:
            raise ValueError(f"bytes drift for {name}")
        finite = np.isfinite(a)
        pos = (np.nan_to_num(a, nan=0.0) > 0) & footprint
        pos_all = np.nan_to_num(a, nan=0.0) > 0
        dpos = d_cat[pos]
        preds[name] = pos
        sites.append({
            "site": name,
            "file": s["local_path"],
            "reported_file": snapshot[name]["reported_file"],
            "download_url": snapshot[name]["download_url"],
            "source_blob_url": snapshot[name]["source_blob_url"],
            "sha256": got,
            "bytes": p.stat().st_size,
            "crs": crs,
            "shape": list(shape),
            "nodata": nodata,
            "encoding": "nan-outside" if not finite.all() else "all-finite",
            "positive_pixels_inside_footprint": int(pos.sum()),
            "positive_pixels_outside_footprint": int(pos_all.sum() - pos.sum()),
            "values_inside_footprint": sorted(set(np.unique(a[finite]).tolist()))[:6],
            "median_d_cat_px": float(np.median(dpos)),
            "q25_d_cat_px": float(np.percentile(dpos, 25)),
            "q75_d_cat_px": float(np.percentile(dpos, 75)),
            "reported_public_dti": snapshot[name]["reported_public_dti"],
            "reported_value_evidence_class": "USER-REPORTED (NOT ORGANIZER-CONFIRMED)",
        })
        print(f"{name}: {pos.sum()} dots, encoding={sites[-1]['encoding']}, "
              f"median d_cat={sites[-1]['median_d_cat_px']:.1f}px", flush=True)

    names = [s["site"] for s in sites]
    pairwise = {}
    for i, na in enumerate(names):
        row = {}
        probe = SurfaceProbe(preds[na].astype(np.float64), footprint)
        for nb in names:
            if na == nb:
                row[nb] = {"overlap_within_3px": 1.0, "rank_correlation": 1.0}
                continue
            dc = dot_check(preds[na].astype(np.float64), preds[nb].astype(np.float64), footprint)
            rc = probe.compare(preds[nb].astype(np.float64))
            row[nb] = {"overlap_within_3px": dc["overlap_within_3px"],
                       "rank_correlation": rc["rank_correlation"]}
        pairwise[na] = row
        m = max((v["overlap_within_3px"], k) for k, v in row.items() if k != na)
        print(f"{na}: max peer overlap {m[0]*100:.2f}% vs {m[1]}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "nine-site-geometry.json").write_text(json.dumps({
        "schema": "gems91.nine-site-geometry.v1",
        "computed_utc": "2026-10-31",
        "inputs_verified": "all nine TIFFs sha256-matched docs/s22/nine-site-audit.json at pinned commits",
        "uniqueness_rule": "DUPLICATE if >70% of candidate dots within 3 px of a registry raster (parallel-run protocol)",
        "sites": sites,
        "pairwise_directed_overlap": pairwise,
    }, indent=2) + "\n")
    print("wrote", OUT / "nine-site-geometry.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
