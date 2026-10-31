#!/usr/bin/env python3
"""Outside-footprint encoding audit for the nine user-named GEMSDOE leader rasters.

Reads the byte cache written by scripts/verify_nine_site_leaders.py
(`<cache>/<SITE>__<basename>.tif`), then records, per file:

  * SHA-256 and byte count, compared with the commit-pinned snapshot in
    docs/review-20261030/nine-site-snapshot.json (identity check);
  * the NaN-vs-zero encoding outside the common footprint;
  * whether any positive (dot) cell lies outside that footprint.

The footprint is the set of finite cells in the NaN-encoded files. It is derived
from the user's own files; it is NOT verified against the organizer's sample
submission, which is absent from this sandbox (IR-S26-05). Nothing here is a
score, an organizer check, or a submission approval.

Usage:
    python3 scripts/audit_nine_site_encoding.py --cache /tmp/nine \
        --out docs/review-20261031/nine-site-encoding-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs" / "review-20261030" / "nine-site-snapshot.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cache = Path(args.cache)
    snap = {s["site"]: s for s in json.loads(SNAPSHOT.read_text())["sites"]}

    records = []
    arrays: dict[str, np.ndarray] = {}
    for site in sorted(snap):
        pinned = snap[site]
        path = cache / f"{site}__{Path(pinned['repository_path']).name}"
        data = path.read_bytes()
        with rasterio.open(path) as ds:
            arr = ds.read(1)
            meta = {
                "crs": str(ds.crs),
                "shape": [ds.height, ds.width],
                "transform": list(ds.transform)[:6],
                "dtype": ds.dtypes[0],
                "count": ds.count,
                "nodata": ds.nodata if ds.nodata is None else str(ds.nodata),
            }
        arrays[site] = arr
        records.append({
            "site": site,
            "file": Path(pinned["repository_path"]).name,
            "sha256": sha256_bytes(data),
            "sha256_matches_pinned_snapshot": sha256_bytes(data) == pinned["sha256"],
            "bytes": len(data),
            "bytes_match_pinned_snapshot": len(data) == pinned["bytes"],
            **meta,
            "nan_cells": int(np.isnan(arr).sum()),
            "dots": int((arr > 0).sum()),
            "finite_min": float(np.nanmin(arr)),
            "finite_max": float(np.nanmax(arr)),
        })

    nan_sites = [r["site"] for r in records if r["nan_cells"] > 0]
    footprint = ~np.isnan(arrays[nan_sites[0]])
    identical = all(np.array_equal(~np.isnan(arrays[s]), footprint) for s in nan_sites)
    for r in records:
        arr = arrays[r["site"]]
        outside = ~footprint
        vals = np.unique(arr[outside])
        r["outside_footprint_values"] = [None if np.isnan(v) else float(v) for v in vals]
        r["dots_outside_footprint"] = int((arr[outside] > 0).sum())
        r["encoding_outside_footprint"] = "nan" if r["nan_cells"] > 0 else "zeros"

    # Exact (cell-level, not 3-px) dot-set relations among the nine files.
    dot_sets = {r["site"]: set(map(tuple, np.argwhere(arrays[r["site"]] > 0).tolist())) for r in records}
    relations = []
    for a in sorted(dot_sets):
        for b in sorted(dot_sets):
            if a == b:
                continue
            sa, sb = dot_sets[a], dot_sets[b]
            if sa <= sb:
                relations.append({"subset": a, "superset": b, "subset_dots": len(sa),
                                  "superset_dots": len(sb), "dots_in_superset_not_subset": len(sb - sa)})

    doc = {
        "schema": "nine-site-encoding-audit-v1",
        "exact_subset_relations": relations,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cache": str(cache),
        "footprint_cells": int(footprint.sum()),
        "grid_cells": int(footprint.size),
        "nan_encoded_files_share_one_footprint": identical,
        "nan_encoded_sites": nan_sites,
        "zero_encoded_sites": [r["site"] for r in records if r["nan_cells"] == 0],
        "claim_boundary": (
            "Identity, encoding, and dot-location facts only. Not a score, not an "
            "organizer format check, not a submission approval. The footprint is "
            "derived from the user's own files and is unverified against the "
            "organizer sample."
        ),
        "files": records,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({k: doc[k] for k in ("footprint_cells", "nan_encoded_files_share_one_footprint", "nan_encoded_sites", "zero_encoded_sites")}, indent=2))
    return 0 if identical else 1


if __name__ == "__main__":
    raise SystemExit(main())
