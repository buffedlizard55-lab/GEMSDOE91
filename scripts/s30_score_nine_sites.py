#!/usr/bin/env python
"""Score the nine listed GEMSDOE site leaders (and the S30-VCSE candidate) on
the pooled hide-and-recover holdout, so the executive summary can give every
row a labelled HOLDOUT-DTI (gems57-pooled-hide-v2) estimate.

Honesty notes: the nine-site leaders were fit on the full catalogue, so their
HOLDOUT-DTI here estimates recovery of hidden (off-catalogue) truth only.
Public-leaderboard figures remain USER-REPORTED and unverified; they are never
written as scores.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio

from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial

SEED = 520810
OUT = ROOT / "docs/s30-vcse"

TARGETS = [
    ("GEMSDOE24", "data/s22-nine-sites/GEMSDOE24.tif", 60069),
    ("GEMSDOE25", "data/s22-nine-sites/GEMSDOE25.tif", 44090),
    ("GEMSDOE27", "data/s22-nine-sites/GEMSDOE27.tif", 61328),
    ("GEMSDOE28", "data/s22-nine-sites/GEMSDOE28.tif", 37660),
    ("GEMSDOE30", "data/s22-nine-sites/GEMSDOE30.tif", 44090),
    ("GEMSDOE31", "data/s22-nine-sites/GEMSDOE31.tif", 40199),
    ("GEMSDOE32", "data/s22-nine-sites/GEMSDOE32.tif", 37654),
    ("GEMSDOE33", "data/s22-nine-sites/GEMSDOE33.tif", 41865),
    ("GEMSDOE36", "data/s22-nine-sites/GEMSDOE36.tif", 38854),
]


def main() -> int:
    g = grid.load_grid(str(ROOT / "data/official"))
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    terms_by_arm = {}
    details = {}
    for name, rel, n_dots in TARGETS:
        with rasterio.open(ROOT / rel) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
        total_terms = None
        per_fold = []
        for fidx, fold in enumerate(folds):
            dom = g.footprint & fold["region"]
            pred = np.where(dom, arr, 0.0)
            res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                     origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            per_fold.append({"arm": name, "fold": fidx,
                             "budget": int((pred > 0).sum()),
                             "n_truth": int(res["n_truth"]),
                             "n_emitted": int(res["n_emitted"])})
        terms_by_arm[name] = total_terms
        details[name] = {"path": rel, "n_dots": n_dots, "per_fold": per_fold}
        print(f"{name}: terms done", flush=True)
        del arr

    pooled = EH.pooled_summary(terms_by_arm, draws=1000, seed=SEED,
                               candidate="GEMSDOE32")
    result = {
        "metric_label": "HOLDOUT-DTI (gems57-pooled-hide-v2; 60,988 withheld positives; "
                        "20 km block bootstrap, draws=1000, seed=520810; 95% CI)",
        "instrument": {"version": getattr(EH, "VERSION", "gems57-pooled-hide-v2"),
                       "withheld_positives": 60988,
                       "folds": "label-blind-quadrants-v3-feature-buffered, buffer_px=80"},
        "pooled": pooled,
        "details": details,
        "caveat": "Estimates of hidden-truth (off-catalogue) recovery on OUR instrument; "
                  "not organizer scores. Public figures for these sites are USER-REPORTED "
                  "and unverified.",
    }
    (OUT / "nine-site-holdout-estimates.json").write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps(pooled, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
