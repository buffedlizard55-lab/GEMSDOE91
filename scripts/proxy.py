"""Catalogue hide-and-recover PROXY. REPORT ONLY -- never a gate (brief section 6).

The circular way to "check" a prune is to score the pruned file against the catalogue
it was pruned with. That is worthless: pruning near catalogue pixels then rewards
itself. This proxy withholds a spatial block of catalogue positives, rebuilds the
variant using ONLY the remaining catalogue, and scores the rebuilt file against the
withheld positives. The withheld faults are then, to the pruner, new faults.

What it measures: whether a file still places dots on faults it was not shown.
What it does NOT measure: the live score. The withheld positives are known USGS /
INGENIOUS geometry, and the competition masks exactly those, so a high value here is
evidence about recall of *catalogue-like* structure, not of new-fault truth.

Reports n withheld positives and a 95% CI. A wide CI is the expected outcome and is
information: it says this proxy cannot separate variants this close together.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))

import axes as A  # noqa: E402
import dti as D  # noqa: E402


def block_folds(shape: tuple[int, int], catalogue: np.ndarray, n_folds: int, block: int = 8):
    """Assign catalogue pixels to folds by spatial block, so folds are contiguous."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    by = (yy // (100 * block)) % 2
    bx = (xx // (100 * block)) % 2
    quad = by * 2 + bx
    ys, xs = np.nonzero(catalogue > 0)
    folds = []
    for f in range(n_folds):
        mask = np.zeros(shape, dtype=bool)
        sel = quad[ys, xs] % n_folds == f
        mask[ys[sel], xs[sel]] = True
        folds.append(mask)
    return folds


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    """Mean and 95% CI half-width from the t distribution (small n)."""
    n = len(values)
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    m = float(values.mean())
    if n == 1:
        return m, m, m
    se = float(values.std(ddof=1) / np.sqrt(n))
    try:
        from scipy import stats

        t = float(stats.t.ppf(0.975, n - 1))
    except Exception:  # pragma: no cover
        t = 1.96 if n > 30 else 2.776
    return m - t * se, m + t * se, se


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Hide-and-recover proxy for PRUNE variants (report only).")
    ap.add_argument("--parent", default="data/R0.tif")
    ap.add_argument("--reference", default="data/sample_submission.tif")
    ap.add_argument("--catalogue", default="data/catalogue.tif")
    ap.add_argument("--values", default="3,8,15")
    ap.add_argument("--folds", type=int, default=4)
    ap.add_argument("--out", default="reports/proxy.json")
    args = ap.parse_args(argv)

    with rasterio.open(args.parent) as s:
        parent = s.read(1)
    with rasterio.open(args.reference) as s:
        ref = s.read(1)
    with rasterio.open(args.catalogue) as s:
        cat = s.read(1)
    cat_bool = cat > 0
    values = [float(v) for v in args.values.split(",") if v.strip()]

    folds = block_folds(parent.shape, cat, args.folds)
    results = {f"le{int(v)}": [] for v in values}
    results["R0_as_is"] = []

    for f, held in enumerate(folds):
        n_held = int(held.sum())
        if n_held == 0:
            continue
        truth = held.astype(np.uint8)
        cat_train = np.where(held, 0, cat_bool).astype(np.uint8)
        # parent scored as-is, with each dot's nearest withheld fault as truth
        results["R0_as_is"].append(D.dti(parent, truth))
        for v in values:
            res = A.prune(parent, ref, cat_train, None, v)
            results[f"le{int(v)}"].append(D.dti(res.array, truth))

    out = {}
    print(f"hide-and-recover PROXY  (n_folds={args.folds}, report only, never a gate)")
    for key, vals in results.items():
        arr = np.array(vals, dtype=float)
        lo, hi, se = mean_ci(arr)
        out[key] = {
            "mean": float(arr.mean()) if len(arr) else None,
            "ci95": [float(lo), float(hi)] if len(arr) else None,
            "se": float(se) if len(arr) else None,
            "folds": [round(float(x), 6) for x in arr],
        }
        print(f"  {key:10s} mean={arr.mean():.5f}  95% CI [{lo:.5f}, {hi:.5f}]  n_folds={len(arr)}")

    withheld = [int(f.sum()) for f in folds]
    out["n_withheld_positives_per_fold"] = withheld
    out["note"] = ("PROXY, not a score. Withheld positives are known catalogue geometry; the "
                   "competition masks those pixels, so this measures recall of catalogue-like "
                   "structure only. Never a gate.")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    print(f"\nwrote {args.out}")
    print("PROXY values are not scores.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
