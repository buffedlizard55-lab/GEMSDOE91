#!/usr/bin/env python3
"""Holdout-DTI for the unique off-catalogue submission (catalogue as withheld truth).

Honest expectation: dots are deliberately >3 px off the catalogue
(damage-zone annulus), so they cannot cover withheld catalogue faults =>
HOLDOUT-DTI ~ 0.  This is reported as a negative result, per the protocol
("Negative results are deliverables").
"""
import sys
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from evaluate_holdout import (  # noqa: E402
    build_segment_buffered_folds,
    score_pooled_holdout,
)

CID = "gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119"
fp = ROOT / "docs" / "downloads" / f"{CID}-zeros.tif"
with rasterio.open(fp) as s:
    arr = s.read(1)
footprint = np.isfinite(arr)
catalogue = rasterio.open(ROOT / "data" / "official" / "existing_faults.tif").read(1) > 0
catalogue = catalogue & footprint

folds = build_segment_buffered_folds(catalogue, footprint, bridge_px=3, buffer_px=10.0)
print("folds:", [(f.name, f.n_withheld, f.n_segments_withheld) for f in folds],
      "total withheld:", sum(f.n_withheld for f in folds))

pred = {f.fold_id: np.where(footprint, np.nan_to_num(arr, nan=0.0), 0.0).astype(np.float32)
        for f in folds}
rep = score_pooled_holdout(pred, folds, footprint, n_boot=200, tile_px=50, seed=91)
print("HOLDOUT-DTI label:", rep["metric_label"], "version:", rep["evaluator_version"])
print("holdout_dti:", rep["holdout_dti"], "ci95:", rep["ci_95"],
      "withheld_positives:", rep["n_withheld_positives"])
for fs in rep["folds"]:
    print("  fold", fs["name"], "dti", fs["fold_dti"], "withheld", fs["n_withheld_positives"],
          "emitted_mass", fs["emitted_mass"])
