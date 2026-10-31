#!/usr/bin/env python3
"""Anchored GEMS live-score estimator (MODEL PROJECTION, never a score).

Seven rasters in this repository have OWNER-REPORTED DrivenData live scores
(the H19-5 lineage measured here byte-for-byte).  This script computes the same
three diagnostics for each anchor and for a candidate raster:

  * holdout_dti  - pooled HOLDOUT-DTI on vendor/gems57 hide-and-recover v3 folds
  * sgmc_off_dti - DTI of the dot field vs the strictly-off-catalogue SGMC truth
                   subset (external proxy truth; diagnostic only)
  * mass         - n_dots / 37,654

and fits OLS live_score ~ 1 + holdout_dti + sgmc_off_dti + mass.  The candidate
projection is reported with a leave-one-out residual 95% interval and is labeled
MODEL_PROJECTION_NOT_A_SCORE.  A projection is never written as a score.

Usage:
    python scripts/estimate_score.py docs/downloads/<candidate>.tif [--out x.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial

ALPHA, BETA, RADIUS = 0.2, 0.8, 3.0

# Byte-pinned registry rasters with OWNER-REPORTED live scores (receipt class:
# user/owner report in the session prompt or ledger/prior_fleet.csv; NOT
# ORGANIZER-CONFIRMED receipts available in this checkout).
ANCHORS = [
    ("data/registry/calib_h195_01922.tif", 0.1922, "h19-5-powerlaw-budget-multiline"),
    ("data/registry/calib_h194_01894.tif", 0.1894, "h19-4-multiline-openness-thermal"),
    ("data/registry/calib_h161_01855.tif", 0.1855, "h16-1-topo-geophys-baseline-ridges"),
    ("data/registry/calib_d15_02477.tif", 0.2477, "h25-1-dotted-h19-5-d1-5"),
    ("data/registry/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600, "dotted-h19-5-d2-8"),
    ("data/registry/GEMSDOE28__h27-4-r1-solo-d2-8.tif", 0.2708, "h27-4-r1-solo-d2-8"),
    ("data/registry/GEMSDOE32__h33-2-b2-zeros.tif", 0.2778, "h33-h33-2-b2 (champion)"),
]


def read_mask(path: Path, shape) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    if shape is not None and arr.shape != tuple(shape):
        raise ValueError(f"{path}: shape {arr.shape} != {shape}")
    with np.errstate(invalid="ignore"):
        return np.where(np.isfinite(arr) & (arr > 0), 1.0, 0.0)


def binary_dti(pred: np.ndarray, truth: np.ndarray, valid: np.ndarray) -> dict:
    """Official DTI for a binary dot field: kernel radius 3 px, alpha 0.2, beta 0.8."""
    p = (np.asarray(pred) > 0) & valid
    g = (np.asarray(truth) > 0) & valid
    n_truth = int(g.sum())
    n_dots = int(p.sum())
    if n_truth == 0:
        raise ValueError("empty truth")
    if n_dots == 0:
        return {"dti": 0.0, "tpw": 0.0, "fpw": 0.0, "fnw": float(n_truth),
                "n_truth": n_truth, "n_dots": 0}
    k = lambda d: np.maximum(1.0 - d / RADIUS, 0.0)
    d_to_p = ndi.distance_transform_edt(~p)
    tpw = float(k(d_to_p[g]).sum())
    d_to_g = ndi.distance_transform_edt(~g)
    m = float(k(d_to_g[p]).sum())
    fpw = n_dots - m
    fnw = n_truth - tpw
    den = tpw + ALPHA * fpw + BETA * fnw
    return {"dti": float(tpw / den), "tpw": tpw, "fpw": float(fpw), "fnw": float(fnw),
            "n_truth": n_truth, "n_dots": n_dots}


def _score_mask_on_folds(mask, g, folds):
    total = None
    m = np.asarray(mask) > 0
    for fold in folds:
        _res, terms = EH.evaluate(np.where(m, 1.0, 0.0), fold, g.footprint,
                                  block_side=200, origin=(0, 0), global_shape=g.shape)
        total = terms if total is None else total + terms
    return float(EH.from_terms(total.sum(axis=0)))


def _score_reemitted(mask, g, folds, n_dots_global: int = 37_654):
    """Matched-semantics holdout: fold-blind re-emission from the trough-filled
    ridge surface with the fold-visible collar (identical to the candidate's
    emission semantics; fixed-mask scoring is deflated by the reverse leak)."""
    from gems91.pdwc21 import emit_dots_nms
    m = (np.asarray(mask) > 0).astype(np.float32)
    surf = ndi.gaussian_filter(ndi.maximum_filter(m, size=7), sigma=1.0).astype(np.float32)
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    total_area = sum(areas)
    total = None
    for fold, area in zip(folds, areas):
        dom = g.footprint & fold["region"]
        budget = int(round(n_dots_global * area / total_area))
        pred = emit_dots_nms(surf, fold["visible"], dom, budget=budget,
                             collar_px=2.05, min_spacing_px=2.8)
        _res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                  origin=(0, 0), global_shape=g.shape)
        total = terms if total is None else total + terms
    return float(EH.from_terms(total.sum(axis=0)))


def diagnostics(mask, g, folds, sgmc_off) -> dict:
    d = binary_dti(mask, sgmc_off, g.footprint)
    return {
        "n_dots": int((np.asarray(mask) > 0).sum()),
        "holdout_dti_fixed": _score_mask_on_folds(mask, g, folds),
        "holdout_dti": _score_reemitted(mask, g, folds),
        "sgmc_off_dti": d["dti"],
        "sgmc_off_detail": d,
    }


def _features(diag: dict) -> list[float]:
    return [1.0, diag["holdout_dti"], diag["sgmc_off_dti"], diag["n_dots"] / 37_654.0]


def fit_and_project(anchor_diags, anchor_scores, cand_diag):
    # 2 predictors max: with 7 anchors a 4-parameter fit overfits (R^2~0.999
    # artefact). Mass (n_dots) is dropped: within the family, live score is
    # driven by emission hygiene that the collar already matches.
    X = np.array([[1.0, d["holdout_dti"], d["sgmc_off_dti"]] for d in anchor_diags], dtype=np.float64)
    y = np.array(anchor_scores, dtype=np.float64)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    xc = np.array([1.0, cand_diag["holdout_dti"], cand_diag["sgmc_off_dti"]], dtype=np.float64)
    point = float(xc @ beta)
    # leave-one-out residuals for an honest residual scale
    loo_err = []
    for i in range(len(y)):
        idx = [j for j in range(len(y)) if j != i]
        b, *_ = np.linalg.lstsq(X[idx], y[idx], rcond=None)
        loo_err.append(y[i] - X[i] @ b)
    loo_err = np.array(loo_err)
    sd = float(np.std(loo_err, ddof=2)) if len(loo_err) > 2 else float(np.std(y - X @ beta))
    span = float(y.max() - y.min())
    r2 = float(1.0 - ((y - X @ beta) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-12))
    # Conformal floor: a new field carries at least half the anchor live span of
    # uncertainty; the LOO scale alone is overconfident for extrapolation.
    half = max(1.96 * sd, 0.5 * span)
    # Extrapolation guard: flag when the candidate leaves the anchor hull.
    hull_extrapolation = bool(
        cand_diag["holdout_dti"] < min(d["holdout_dti"] for d in anchor_diags)
        or cand_diag["holdout_dti"] > max(d["holdout_dti"] for d in anchor_diags)
        or cand_diag["sgmc_off_dti"] < min(d["sgmc_off_dti"] for d in anchor_diags)
        or cand_diag["sgmc_off_dti"] > max(d["sgmc_off_dti"] for d in anchor_diags)
    )
    if hull_extrapolation:
        # Outside the anchor hull the regression extrapolates absurdly (its
        # anti-live coefficients blow up).  Replace it with a traceable,
        # non-parametric bracket over the owner-reported non-family submissions
        # at matched ~37k-dot budgets (every value below is a receipt value from
        # the session prompt's site ledger, not a model output).
        cohort = [
            ("apartgemsdoe3-h2-cshd-37654", 0.1633),
            ("gemsdoesass2-hvfd-37654", 0.1881),
            ("gemsdoekarage3-csst-37654", 0.1978),
            ("gems27-h29-hydrothermal-piedmont-celf", 0.2190),
            ("gems27-h31-drcg-wl-celf", 0.2250),
            ("gate_ortho_w0.25-40k", 0.2376),
            ("gems70-p5-dual-submod30k", 0.2478),
            ("anderson-geothermal-pinn-38854", 0.2750),
        ]
        vals = np.array([v for _, v in cohort])
        lo = float(vals.min())
        hi = 0.2778 + 0.002   # family hygiene-matched ceiling + one family step
        point = 0.5 * (lo + hi)
        return {
            "label": "MODEL_PROJECTION_NOT_A_SCORE",
            "point": point,
            "ci95": [lo, hi],
            "ci_half_width": 0.5 * (hi - lo),
            "model": ("BRACKETING estimator (regression extrapolation rejected: candidate "
                      "diagnostics lie outside the anchor hull): [min, max+step] of the "
                      "owner-reported non-family matched-budget cohort vs the family "
                      "hygiene-matched ceiling"),
            "regression_in_hull_only": {
                "coefficients": [float(b) for b in beta],
                "r2_in_sample": r2,
                "loO_residual_sd": sd,
                "note": "in-hull fit retained for audit only; NOT used for this candidate",
            },
            "cohort_bracket": [{"name": n, "live_owner_reported": v} for n, v in cohort],
            "cohort_median": float(np.median(vals)),
            "n_anchors": len(y),
            "hull_extrapolation": True,
            "projection_reliability": "LOW",
            "reference_lines": {
                "family_live_ceiling_owner_reported": 0.2778,
                "non_family_live_ceiling_owner_reported": 0.2750,
                "non_family_ceiling_source": ("session-prompt site receipts; GEMSDOE32 arena51 "
                                              "livescore audit independently found no non-family "
                                              "detector above 0.2478 on its 53-mask set"),
            },
            "caveats": [
                "all cohort values are OWNER-REPORTED (no organizer receipts in this checkout)",
                "the hide-and-recover instrument is ANTI-live within the H19-5 family (measured Spearman -0.75 to -0.82): no local instrument can certify a live score above 0.2778 for any candidate",
                "candidate is non-family; the bracket assumes matched emission hygiene (37,654 dots, B=2 collar, 2.8 px packing) transfers",
                "this is not a leaderboard score and not an ORGANIZER-CONFIRMED value",
            ],
        }
    lo = max(0.0, point - half)
    hi = point + half
    return {
        "label": "MODEL_PROJECTION_NOT_A_SCORE",
        "point": point,
        "ci95": [lo, hi],
        "ci_half_width": half,
        "model": ("OLS live_score ~ 1 + holdout_dti + sgmc_off_dti on 7 byte-pinned anchors "
                  "(mass dropped: 7 points cannot support 4 parameters)"),
        "coefficients": [float(b) for b in beta],
        "r2_in_sample": r2,
        "loO_residual_sd": sd,
        "loO_errors": [float(e) for e in loo_err],
        "n_anchors": len(y),
        "hull_extrapolation": hull_extrapolation,
        "projection_reliability": "LOW",
        "reference_lines": {
            "family_live_ceiling_owner_reported": 0.2778,
            "non_family_live_ceiling_owner_reported": 0.2478,
            "non_family_ceiling_source": ("GEMSDOE32 arena51 livescore audit: across 53 scored "
                                          "masks no non-family detector exceeded 0.2478 (n=36)"),
        },
        "caveats": [
            "anchor live scores are OWNER-REPORTED (no organizer receipts in this checkout)",
            "the hide-and-recover instrument is ANTI-live within the H19-5 family (measured Spearman -0.75 to -0.82 across pooled/detached/SGMC-off variants): anchors with flank removal score LOW on holdout while scoring HIGHEST live; regression coefficients inherit this inversion",
            "candidate diagnostics are measured from its emitted mask via matched re-emission (smoothed-ridge proxy), degrading comparability with the selection-time arm score",
            "family membership dominates live scores (GEMSDOE32 arena51: Spearman +0.844); this candidate is non-family and no local instrument can certify a live score above the champion's 0.2778",
            "this is not a leaderboard score and not an ORGANIZER-CONFIRMED value",
        ],
    }


def estimate(pred: np.ndarray, g, folds) -> dict:
    cat_dist = ndi.distance_transform_edt(~g.catalogue)
    with rasterio.open(ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0)
    sgmc_off = sgmc & g.footprint & (cat_dist > 3.0)
    anchor_diags, anchor_scores, rows = [], [], []
    for rel, score, label in ANCHORS:
        p = ROOT / rel
        if not p.is_file():
            rows.append({"anchor": label, "status": "missing"})
            continue
        m = read_mask(p, g.shape)
        d = diagnostics(m, g, folds, sgmc_off)
        anchor_diags.append(d)
        anchor_scores.append(score)
        rows.append({"anchor": label, "raster": rel,
                     "live_score_owner_reported": score, "diagnostics": d})
        print(f"  anchor {label:34s} live={score:.4f} holdout={d['holdout_dti']:.4f} "
              f"sgmc={d['sgmc_off_dti']:.4f} n={d['n_dots']}", flush=True)
    cand_diag = diagnostics(pred, g, folds, sgmc_off)
    fit = fit_and_project(anchor_diags, anchor_scores, cand_diag)
    fit["anchors"] = rows
    fit["candidate_diagnostics"] = cand_diag
    fit["sgmc_off_truth_pixels"] = int(sgmc_off.sum())
    return fit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("raster")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    g = grid.load_grid(ROOT / "data" / "official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    m = read_mask(Path(args.raster), g.shape)
    est = estimate(m, g, folds)
    text = json.dumps(est, indent=2, allow_nan=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
