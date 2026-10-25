#!/usr/bin/env python3
"""Uniqueness vs local downloads + holdout DTI for HEXFAR91."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
from evaluate_holdout import (  # noqa: E402
    build_segment_buffered_folds,
    check_registry_uniqueness,
    score_pooled_holdout,
)

CID = "gems91-hexfar-stagger-18-35-20261025T161307Z-d102f5f0"
fp = ROOT / "docs" / "downloads" / f"{CID}-zeros.tif"
if not fp.exists():
    fp = ROOT / "releases" / f"{CID}-zeros.tif"
with rasterio.open(fp) as s:
    arr = s.read(1)
footprint = np.isfinite(arr) if np.isnan(arr).any() else np.ones(arr.shape, dtype=bool)
# zeros twin is all-finite; footprint from sample
with rasterio.open(ROOT / "data" / "official" / "sample_submission.tif") as s:
    footprint = np.isfinite(s.read(1))
surface = arr[footprint]
cand = (arr > 0) & footprint

paths = []
for p in sorted((ROOT / "docs" / "downloads").glob("*-zeros.tif")) + sorted(
    (ROOT / "docs" / "downloads").glob("*.tif")
):
    if CID in p.name:
        continue
    try:
        with rasterio.open(p) as s:
            ra = s.read(1)
        if ra.shape != arr.shape:
            continue
        if not np.isfinite(ra[footprint]).all():
            ra = np.nan_to_num(ra, nan=0.0)
        paths.append(p)
    except Exception as e:
        print("skip", p.name, e)

# de-dupe by path
seen = set()
uniq = []
for p in paths:
    if p.resolve() in seen:
        continue
    seen.add(p.resolve())
    uniq.append(p)
print("n_registry", len(uniq))
res = check_registry_uniqueness(surface, cand, footprint, uniq)
print("is_duplicate:", res["is_duplicate"])
print("uniqueness_pass:", res["uniqueness_pass"])
print("surface_max_abs_rank_corr:", res["surface_max_abs_rank_corr"])
print("dots_max_3px_overlap:", res["dots_max_3px_overlap"])
worst = sorted(res["comparisons"], key=lambda c: -c["effective_dot_overlap_3px"])[:8]
for c in worst:
    print(" ", c["registry_raster"], "rho", c["surface_abs_rank_corr"],
          "ov", c["effective_dot_overlap_3px"], "dup", c["duplicate_flag"])

catalogue = rasterio.open(ROOT / "data" / "official" / "existing_faults.tif").read(1) > 0
catalogue = catalogue & footprint
folds = build_segment_buffered_folds(catalogue, footprint, bridge_px=3, buffer_px=10.0)
pred = {f.fold_id: np.where(footprint, arr.astype(np.float32), 0.0).astype(np.float32) for f in folds}
rep = score_pooled_holdout(pred, folds, footprint, n_boot=80, tile_px=50, seed=91)
print("HOLDOUT-DTI", rep["holdout_dti"], "ci", rep["ci_95"], "n", rep["n_withheld_positives"], "ver", rep["evaluator_version"])

out = {
    "cid": CID,
    "sha256": hashlib.sha256(fp.read_bytes()).hexdigest(),
    "n_dots": int(cand.sum()),
    "uniqueness": {
        "is_duplicate": res["is_duplicate"],
        "pass": res["uniqueness_pass"],
        "surface_max_abs_rank_corr": res["surface_max_abs_rank_corr"],
        "dots_max_3px_overlap": res["dots_max_3px_overlap"],
        "n_compared": len(uniq),
        "worst": worst[:5],
    },
    "holdout": {
        "dti": rep["holdout_dti"],
        "ci_95": rep["ci_95"],
        "n_withheld_positives": rep["n_withheld_positives"],
        "evaluator_version": rep["evaluator_version"],
        "metric_label": rep.get("metric_label"),
    },
}
Path("evidence/hexfar91_score.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
print("wrote evidence/hexfar91_score.json")
