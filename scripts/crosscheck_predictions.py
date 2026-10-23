#!/usr/bin/env python3
"""Score every shipped release against the only truth visible from here.

Truth in this challenge is the (hidden) fault raster. The one truth-adjacent
instrument available is the *catalogue*: the 60,988 cells the organisers already
map as faults, which `sample_submission.tif` carries as its positive class. A DTI
computed with the catalogue as truth therefore says nothing about the real score
-- but it does say, exactly and reproducibly, what each edit does to the reward
that is *observable* from this sandbox, and it decomposes that change into credit
earned (T) and unmatched mass (S - M).

That decomposition is the decision-relevant part before a human spends a slot:

  * dots far from every catalogue trace earn no credit here at all, so deleting
    them is proxy-positive by construction. Whether they earn credit in reality
    depends on unmapped faults, which this instrument cannot see.
  * a dot 2.2 px from a trace still earns credit here, so deleting the collar is
    *not* automatically proxy-positive -- and the brief's 300 m exclusion clause
    applies to the organisers' mapping, not to this metric.

Outputs evidence/predictions_crosscheck_20261023.json. PROXY, report-only: it is
never a gate and never a score.

    python3 scripts/crosscheck_predictions.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import metric  # noqa: E402

RELEASES = ROOT / "releases"
CATALOGUE = ROOT / "data" / "derived" / "catalogue_mask.tif"
SAMPLE = ROOT / "data" / "official" / "sample_submission.tif"
PARENT = ROOT / "data" / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
OUT = ROOT / "evidence" / "predictions_crosscheck_20261023.json"

BANDS = [(0.0, 3.0), (3.0, 5.0), (5.0, 10.0), (10.0, 20.0), (20.0, 40.0), (40.0, np.inf)]


def read_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1)
    return np.nan_to_num(a, nan=0.0) > 0.0


def band_report(dots: np.ndarray, dist: np.ndarray, credit: np.ndarray, mass: np.ndarray) -> list[dict]:
    out = []
    d = dist[dots]
    c = credit[dots]
    for lo, hi in BANDS:
        sel = (d >= lo) & (d < hi)
        n = int(sel.sum())
        if n == 0:
            out.append({"lo_px": lo, "hi_px": None if np.isinf(hi) else hi, "n_dots": 0})
            continue
        out.append({
            "lo_px": lo, "hi_px": None if np.isinf(hi) else hi,
            "n_dots": n,
            "share_of_dots": round(n / int(dots.sum()), 6),
            "share_of_mass": round(float(mass[dots][sel].sum() / mass.sum()), 6),
            "share_of_credit": round(float(c[sel].sum() / credit[dots].sum()), 6),
            "mean_credit_per_dot": round(float(c[sel].mean()), 6),
            "n_dots_with_zero_credit": int((c[sel] == 0).sum()),
        })
    return out


def main() -> int:
    truth = read_mask(CATALOGUE)
    with rasterio.open(SAMPLE) as ds:
        transform = ds.transform
        shape = (ds.height, ds.width)
    # distance from every cell to the nearest catalogue cell (px)
    dist_to_cat = ndi.distance_transform_edt(~truth)

    parent = read_mask(PARENT).astype(np.float64)
    base = metric.components(parent, truth)
    base_dti = base.dti()

    def credit_of(pred: np.ndarray) -> np.ndarray:
        """Kernel-weighted truth at each cell: sampling this at a dot gives the
        kernel credit that dot earns (and summing it over dots gives T)."""
        out = np.zeros_like(pred)
        for dr, dc, k in metric._offsets(metric.RADIUS_PX):
            out += k * metric._shift(pred, dr, dc)
        return out

    parent_credit = credit_of(truth.astype(np.float64))
    result = {
        "label": "PROXY",
        "note": ("DTI with the 60,988-cell catalogue as truth. Not the competition score: "
                 "unmapped faults are invisible to this instrument, so it over-rewards deleting "
                 "anything far from a mapped trace. Report-only, never a gate."),
        "grid": {"height": shape[0], "width": shape[1],
                 "transform": list(transform)[:6], "truth_cells": int(truth.sum())},
        "parent": {
            "file": PARENT.name,
            "dti_proxy": round(base_dti, 8),
            "T": round(base.T, 6), "S": round(base.S, 6), "M": round(base.M, 6),
            "n_dots": int(parent.sum()),
            "bands": band_report(parent > 0, dist_to_cat, parent_credit, parent),
        },
        "releases": [],
        # A deleted dot pays for its own removal iff its kernel credit is below
        # 0.2*DTI/(1 - 0.2*DTI) times what it frees in the (S - M) term; at the
        # claimed live DTI (0.2778) and a typical max-weight m ~ 0.25 that is
        # ~0.059 credit per unit of deleted mass.
        "breakeven_credit_per_deleted_dot": {
            "at_claimed_dti_0.2778": round(0.2 * 0.2778 / (1 - 0.2 * 0.2778) * 0.75, 6),
            "at_proxy_dti": round(0.2 * base_dti / (1 - 0.2 * base_dti) * 0.75, 6),
            "note": ("credit per dot below this number => deleting it raises DTI. "
                     "Assumes the deleted dot's max kernel weight to truth m = 0.25, i.e. it "
                     "sits at the parent's 2.236 px collar; for dots with m = 0 the threshold "
                     "is 0.0588 at DTI 0.2778."),
        },
    }

    for path in sorted(RELEASES.glob("*.tif")):
        if path.name.endswith("-zeros.tif"):
            continue  # same dot set as the NaN twin by construction
        pred = read_mask(path).astype(np.float64)
        parts = metric.components(pred, truth)
        d = parts.dti()
        credit = credit_of(truth.astype(np.float64))
        result["releases"].append({
            "file": path.name,
            "n_dots": int(pred.sum()),
            "dti_proxy": round(d, 8),
            "delta_vs_parent": round(d - base_dti, 8),
            "T": round(parts.T, 6), "S": round(parts.S, 6), "M": round(parts.M, 6),
            "bands": band_report(pred > 0, dist_to_cat, credit, pred),
        })
        print(f"{path.name[-46:]:>46}  n={int(pred.sum()):6d}  dti={d:.6f}  "
              f"delta={d - base_dti:+.6f}")

    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"\nparent dti_proxy {base_dti:.6f}  T {base.T:.4f}  M {base.M:.4f}  "
          f"truth {int(truth.sum())}")
    print("wrote", OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
