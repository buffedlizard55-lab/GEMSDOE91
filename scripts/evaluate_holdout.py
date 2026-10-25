#!/usr/bin/env python3
"""Shared hide-and-recover holdout evaluator, single-feature leakage canary,
and registry lane-drift / uniqueness checker for GEMSDOE91.

PARALLEL-RUN PROTOCOL compliance:
  - Rule 1 (LANE): checks BOTH the continuous surface before placement
    (Spearman |rho| <= 0.90) AND final emitted dots (fraction of candidate dots
    within <= 3.0 px of any registry raster's dots <= 0.70).
  - Rule 2 (REUSE, DON'T REBUILD): delegates DTI scoring directly to the
    repository's canonical `scripts/dti.py` (alpha=0.2, beta=0.8, R=300 m = 3 px
    triangular kernel, T = sum_g max_j p_j * k(||j - g||)).
  - Rule 3 (LABEL EVERY NUMBER): every output score is stamped with
    `HOLDOUT-DTI`, `evaluator_version`, `n_withheld_positives`, and `ci_95`.
  - Rule 4 (LEAKAGE CANARY): tests every single feature alone on the holdout
    folds and fails closed if any symmetric ROC-AUC > 0.90.
"""

from __future__ import annotations

import glob
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import dti as D  # noqa: E402

EVALUATOR_VERSION = "gems91-hide-recover-v1.0"
DEFAULT_BRIDGE_PX = 3
DEFAULT_BUFFER_PX = 10.0
MAX_LEAKAGE_AUC = 0.90
MAX_SURFACE_RANK_CORR = 0.90
MAX_DOT_OVERLAP_3PX = 0.70
UNIQUENESS_GATE_VERSION = "gems91-directed-registry-v1.1"


@dataclass(frozen=True)
class HoldoutFold:
    fold_id: int
    name: str
    region_mask: np.ndarray      # bool (H, W): spatial test quadrant/block
    withheld_faults: np.ndarray  # bool (H, W): whole fault segments held out
    visible_faults: np.ndarray   # bool (H, W): training catalogue faults (> buffer_px from withheld)
    buffer_mask: np.ndarray      # bool (H, W): buffer exclusion zone around withheld segments
    n_withheld: int
    n_visible: int
    n_segments_withheld: int


def build_segment_buffered_folds(
    catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    bridge_px: int = DEFAULT_BRIDGE_PX,
    buffer_px: float = DEFAULT_BUFFER_PX,
) -> list[HoldoutFold]:
    """Partition `catalogue` into 4 spatially-blocked hide-and-recover folds by
    WHOLE fault-segment complexes, with a `buffer_px` exclusion zone.

    1. Dilate `catalogue` by `bridge_px` so stepped/splayed strands of the same
       fault system receive a single connected-component ID (whole segments are
       never split across train and test).
    2. Assign each fault complex to one of 4 spatial quadrants (NW, NE, SW, SE)
       balanced at the footprint median row and column using complex centroids.
    3. Define `visible_faults` as catalogue pixels NOT in `withheld_faults` AND
       strictly further than `buffer_px` Euclidean pixels from `withheld_faults`.
    """
    cat = (np.nan_to_num(catalogue, nan=0.0) > 0) & footprint
    if not cat.any():
        raise ValueError("catalogue has zero positive pixels inside footprint")

    yy, xx = np.nonzero(footprint)
    row_med = float(np.median(yy))
    col_med = float(np.median(xx))

    # Bridge nearby strands into whole fault-segment complexes
    if bridge_px > 0:
        r = int(bridge_px)
        oy, ox = np.mgrid[-r : r + 1, -r : r + 1]
        struct = (np.hypot(oy, ox) <= float(bridge_px)).astype(bool)
        bridged = ndi.binary_dilation(cat, structure=struct)
    else:
        bridged = cat.copy()

    comp_labels, n_comp = ndi.label(bridged, structure=np.ones((3, 3), dtype=int))
    cat_comp = np.where(cat, comp_labels, 0)

    # Compute centroid of each complex on actual catalogue pixels
    cy, cx = np.nonzero(cat)
    cids = cat_comp[cy, cx]
    max_id = int(cids.max())
    counts = np.bincount(cids, minlength=max_id + 1)
    sum_y = np.bincount(cids, weights=cy.astype(np.float64), minlength=max_id + 1)
    sum_x = np.bincount(cids, weights=cx.astype(np.float64), minlength=max_id + 1)

    comp_quad = np.full(max_id + 1, -1, dtype=np.int32)
    valid_ids = np.nonzero(counts > 0)[0]
    valid_ids = valid_ids[valid_ids > 0]
    mean_y = sum_y[valid_ids] / counts[valid_ids]
    mean_x = sum_x[valid_ids] / counts[valid_ids]
    quad_ids = ((mean_y >= row_med).astype(np.int32) * 2) + (mean_x >= col_med).astype(np.int32)
    comp_quad[valid_ids] = quad_ids

    grid_y, grid_x = np.indices(cat.shape)
    quad_names = ["NW", "NE", "SW", "SE"]
    folds: list[HoldoutFold] = []

    for q in range(4):
        if q == 0:
            reg = (grid_y < row_med) & (grid_x < col_med) & footprint
        elif q == 1:
            reg = (grid_y < row_med) & (grid_x >= col_med) & footprint
        elif q == 2:
            reg = (grid_y >= row_med) & (grid_x < col_med) & footprint
        else:
            reg = (grid_y >= row_med) & (grid_x >= col_med) & footprint

        withheld = (cat_comp > 0) & (comp_quad[cat_comp] == q)
        if not withheld.any():
            raise ValueError(f"fold {q} ({quad_names[q]}) received 0 withheld fault pixels")

        dist_to_withheld = ndi.distance_transform_edt(~withheld)
        buf = (dist_to_withheld <= float(buffer_px)) & (~withheld) & footprint
        visible = cat & (~withheld) & (dist_to_withheld > float(buffer_px))

        # Extend evaluation region slightly to include full withheld segments that
        # cross the quadrant midline, while keeping folds disjoint on positives
        n_seg = int(np.sum(comp_quad[valid_ids] == q))
        folds.append(
            HoldoutFold(
                fold_id=q,
                name=quad_names[q],
                region_mask=reg,
                withheld_faults=withheld,
                visible_faults=visible,
                buffer_mask=buf,
                n_withheld=int(withheld.sum()),
                n_visible=int(visible.sum()),
                n_segments_withheld=n_seg,
            )
        )
    return folds


def fast_mann_whitney_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Exact tie-aware ROC-AUC in O(N log N). Returns NaN if a class is empty."""
    s = np.asarray(scores, dtype=np.float64)
    y = np.asarray(labels, dtype=bool)
    finite = np.isfinite(s)
    s = s[finite]
    y = y[finite]
    n_pos = int(y.sum())
    n_neg = int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = rankdata(s, method="average")
    auc = (float(ranks[y].sum()) - n_pos * (n_pos + 1) / 2.0) / (float(n_pos) * float(n_neg))
    return float(auc)


def run_leakage_canary(
    features_fp: np.ndarray,
    feature_names: list[str],
    folds: list[HoldoutFold],
    footprint: np.ndarray,
    *,
    fold_specific_features: dict[int, tuple[np.ndarray, list[str]]] | None = None,
    subsample_step: int = 4,
    max_auc: float = MAX_LEAKAGE_AUC,
) -> dict:
    """Rule 4 LEAKAGE CANARY: test every single feature alone against withheld
    fault segments on the holdout folds before trusting any model result.

    Uses symmetric AUC `max(auc, 1 - auc)` so negated leaks are caught equally.
    """
    fp_idx = np.full(footprint.shape, -1, dtype=np.int32)
    fp_idx[footprint] = np.arange(int(footprint.sum()), dtype=np.int32)

    per_feature: dict[str, dict] = {}
    worst_name = ""
    worst_auc = 0.0

    # 1. Static fold-invariant features
    for j, name in enumerate(feature_names):
        col = features_fp[:, j]
        fold_aucs = []
        for f in folds:
            # Evaluate on fold's test region + withheld segments, masking visible faults & buffer
            eval_mask = (f.region_mask | f.withheld_faults) & (~f.visible_faults) & (~f.buffer_mask) & footprint
            ey, ex = np.nonzero(eval_mask)
            if subsample_step > 1:
                # Keep ALL withheld positives + strided negatives for exact low-variance AUC
                pos_m = f.withheld_faults[ey, ex]
                keep = pos_m | ((np.arange(ey.size) % subsample_step) == 0)
                ey, ex = ey[keep], ex[keep]
            idx = fp_idx[ey, ex]
            y = f.withheld_faults[ey, ex]
            raw_auc = fast_mann_whitney_auc(col[idx], y)
            sym_auc = max(raw_auc, 1.0 - raw_auc) if np.isfinite(raw_auc) else 0.5
            fold_aucs.append((raw_auc, sym_auc))
        mean_raw = float(np.mean([a[0] for a in fold_aucs]))
        mean_sym = float(np.mean([a[1] for a in fold_aucs]))
        max_sym = float(np.max([a[1] for a in fold_aucs]))
        per_feature[name] = {
            "mean_raw_auc": round(mean_raw, 5),
            "mean_symmetric_auc": round(mean_sym, 5),
            "max_fold_symmetric_auc": round(max_sym, 5),
            "pass": bool(max_sym <= max_auc),
        }
        if max_sym > worst_auc:
            worst_auc = max_sym
            worst_name = name

    # 2. Fold-derived visible-catalogue features (computed strictly from visible_faults_k)
    if fold_specific_features:
        f0_arr, f_names = next(iter(fold_specific_features.values()))
        for j, name in enumerate(f_names):
            fold_aucs = []
            for f in folds:
                f_arr, _ = fold_specific_features[f.fold_id]
                col = f_arr[:, j]
                eval_mask = (f.region_mask | f.withheld_faults) & (~f.visible_faults) & (~f.buffer_mask) & footprint
                ey, ex = np.nonzero(eval_mask)
                if subsample_step > 1:
                    pos_m = f.withheld_faults[ey, ex]
                    keep = pos_m | ((np.arange(ey.size) % subsample_step) == 0)
                    ey, ex = ey[keep], ex[keep]
                idx = fp_idx[ey, ex]
                y = f.withheld_faults[ey, ex]
                raw_auc = fast_mann_whitney_auc(col[idx], y)
                sym_auc = max(raw_auc, 1.0 - raw_auc) if np.isfinite(raw_auc) else 0.5
                fold_aucs.append((raw_auc, sym_auc))
            mean_raw = float(np.mean([a[0] for a in fold_aucs]))
            mean_sym = float(np.mean([a[1] for a in fold_aucs]))
            max_sym = float(np.max([a[1] for a in fold_aucs]))
            per_feature[name] = {
                "mean_raw_auc": round(mean_raw, 5),
                "mean_symmetric_auc": round(mean_sym, 5),
                "max_fold_symmetric_auc": round(max_sym, 5),
                "pass": bool(max_sym <= max_auc),
            }
            if max_sym > worst_auc:
                worst_auc = max_sym
                worst_name = name

    flagged = [name for name, info in per_feature.items() if not info["pass"]]
    all_pass = len(flagged) == 0
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "max_allowed_auc": max_auc,
        "n_features_tested": len(per_feature),
        "worst_feature": worst_name,
        "worst_symmetric_auc": round(worst_auc, 5),
        "flagged_features": flagged,
        "all_pass": all_pass,
        "features": per_feature,
    }


EVALUATOR_VERSION_V11 = "gems91-hide-recover-v1.1-nohalo"


def score_pooled_holdout(
    fold_predictions: dict[int, np.ndarray],
    folds: list[HoldoutFold],
    footprint: np.ndarray,
    *,
    n_boot: int = 200,
    tile_px: int = 50,
    seed: int = 91,
    mask_buffer_predictions: bool = True,
) -> dict:
    """Rule 2 & Rule 3: Score hide-and-recover holdout predictions using exact
    pooled DTI (`alpha=0.2, beta=0.8, R=300 m` triangular kernel).

    For each fold `k`:
      - Visible training faults (`visible_faults`) and the segment buffer (`buffer_mask`)
        are masked pixel-exactly (`pred_masked[visible_faults | buffer_mask] = 0`).
      - Predictions restricted to the fold's evaluation domain (`region_mask | withheld_faults`,
        disjoint on positives across folds) are scored against `withheld_faults`.
      - Pooled `T`, `S`, `M`, `|G|` across all 4 folds yield exact pooled `HOLDOUT-DTI`.
      - Spatial block-bootstrap (`tile_px x tile_px` = 5x5 km tiles, `n_boot` draws)
        yields a spatially-honest 95% confidence interval.

    `mask_buffer_predictions` (S14, IR-91-S14-01): with the v1.0 default
    (`True`) every prediction inside the 1 km (10 px) buffer around a withheld
    segment is deleted before scoring. Because the DTI kernel radius is only
    3 px, this "halo deletion" makes near-miss credit impossible and forces
    HOLDOUT-DTI = 0 for ANY real submission raster (all fleet rasters carry
    zero mass exactly on catalogue pixels; measured 2026-10-24,
    evidence/s14_winner_forensics.json). The PARALLEL-RUN PROTOCOL only
    requires "mask visible faults pixel-exactly"; the buffer's role is to
    exclude *training* samples/features near withheld segments. Passing
    `False` therefore scores with evaluator version
    `gems91-hide-recover-v1.1-nohalo`: identical folds, identical masking of
    visible faults, but predictions in the buffer earn honest 300 m-kernel
    credit exactly as on the DrivenData leaderboard. v1.0 numbers and v1.1
    numbers are NEVER comparable; every result dict carries its version.
    """
    radius = D.kernel_radius_px()
    dy_off, dx_off, k_w = D._kernel_offsets(radius)

    total_T = 0.0
    total_S = 0.0
    total_M = 0.0
    total_G = 0
    fold_summaries = []

    # Tile accumulators for spatial block bootstrap
    h, w = footprint.shape
    nt_y = int(math.ceil(h / tile_px))
    nt_x = int(math.ceil(w / tile_px))
    n_tiles = nt_y * nt_x
    tile_T = np.zeros(n_tiles, dtype=np.float64)
    tile_S = np.zeros(n_tiles, dtype=np.float64)
    tile_M = np.zeros(n_tiles, dtype=np.float64)
    tile_G = np.zeros(n_tiles, dtype=np.float64)

    yy_grid, xx_grid = np.indices((h, w))
    tile_id_grid = (yy_grid // tile_px) * nt_x + (xx_grid // tile_px)

    for f in folds:
        pred_raw = np.nan_to_num(fold_predictions[f.fold_id], nan=0.0, posinf=0.0, neginf=0.0)
        # Evaluation domain for fold k: quadrant (excluding other folds' withheld faults) + own withheld faults
        other_withheld = np.zeros_like(footprint, dtype=bool)
        for f2 in folds:
            if f2.fold_id != f.fold_id:
                other_withheld |= f2.withheld_faults

        domain = ((f.region_mask & (~other_withheld)) | f.withheld_faults) & footprint
        # Mask visible faults pixel-exactly; buffer masking of predictions is
        # the v1.0 halo deletion (see docstring / IR-91-S14-01).
        active_domain = domain & (~f.visible_faults)
        if mask_buffer_predictions:
            active_domain &= ~f.buffer_mask

        p = np.where(active_domain, pred_raw, 0.0)
        g = f.withheld_faults

        # Compute per-truth-pixel best credit map and per-prediction-pixel best match map
        best_on_g = np.zeros_like(p, dtype=np.float64)
        g_float = g.astype(np.float64)
        best_match_p = np.zeros_like(p, dtype=np.float64)
        for dy, dx, kw in zip(dy_off, dx_off, k_w):
            np.maximum(best_on_g, D._shift(p, int(dy), int(dx)) * kw, out=best_on_g)
            np.maximum(best_match_p, D._shift(g_float, int(dy), int(dx)) * kw, out=best_match_p)

        T_k = float(best_on_g[g].sum())
        S_k = float(p.sum())
        M_k = float((p * best_match_p).sum())
        G_k = int(g.sum())
        den_k = D.ALPHA * T_k + D.ALPHA * (S_k - M_k) + D.BETA * G_k
        dti_k = 0.0 if den_k <= 0.0 else T_k / den_k

        total_T += T_k
        total_S += S_k
        total_M += M_k
        total_G += G_k

        fold_summaries.append({
            "fold_id": f.fold_id,
            "name": f.name,
            "n_withheld_positives": G_k,
            "n_segments_withheld": f.n_segments_withheld,
            "emitted_mass": round(S_k, 2),
            "T": round(T_k, 3),
            "M": round(M_k, 3),
            "fold_dti": round(dti_k, 6),
        })

        # Accumulate per-5km-tile contributions for block bootstrap CI
        g_idx = np.nonzero(g)
        np.add.at(tile_T, tile_id_grid[g_idx], best_on_g[g_idx])
        np.add.at(tile_G, tile_id_grid[g_idx], 1.0)
        p_nz = np.nonzero(p > 0)
        if p_nz[0].size:
            np.add.at(tile_S, tile_id_grid[p_nz], p[p_nz])
            np.add.at(tile_M, tile_id_grid[p_nz], (p * best_match_p)[p_nz])

    pooled_den = D.ALPHA * total_T + D.ALPHA * (total_S - total_M) + D.BETA * total_G
    pooled_dti = 0.0 if pooled_den <= 0.0 else total_T / pooled_den

    active_tiles = np.nonzero((tile_G > 0) | (tile_S > 0))[0]
    rng = np.random.default_rng(seed)
    boot_scores = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        draw = rng.choice(active_tiles, size=active_tiles.size, replace=True)
        bT = float(tile_T[draw].sum())
        bS = float(tile_S[draw].sum())
        bM = float(tile_M[draw].sum())
        bG = float(tile_G[draw].sum())
        bden = D.ALPHA * bT + D.ALPHA * (bS - bM) + D.BETA * bG
        boot_scores[b] = 0.0 if bden <= 0.0 else bT / bden

    ci_lo, ci_hi = np.percentile(boot_scores, [2.5, 97.5])
    return {
        "metric_label": "HOLDOUT-DTI",
        "evaluator_version": EVALUATOR_VERSION if mask_buffer_predictions else EVALUATOR_VERSION_V11,
        "mask_buffer_predictions": bool(mask_buffer_predictions),
        "alpha": D.ALPHA,
        "beta": D.BETA,
        "kernel_radius_m": D.KERNEL_RADIUS_M,
        "n_withheld_positives": int(total_G),
        "holdout_dti": round(float(pooled_dti), 6),
        "ci_95": [round(float(ci_lo), 6), round(float(ci_hi), 6)],
        "bootstrap_tiles_5km": int(active_tiles.size),
        "bootstrap_draws": int(n_boot),
        "pooled_T": round(total_T, 3),
        "pooled_S": round(total_S, 2),
        "pooled_M": round(total_M, 3),
        "folds": fold_summaries,
    }


def score_off_catalogue_sgmc(
    pred: np.ndarray,
    sgmc_mask: np.ndarray,
    catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    min_cat_dist_px: float = 3.0,
) -> dict:
    """Blind independent geological control: USGS SGMC faults strictly > 3 px
    from the competition catalogue (`existing_faults.tif`), scored with exact DTI.
    """
    cat = (np.nan_to_num(catalogue, nan=0.0) > 0) & footprint
    d_cat = ndi.distance_transform_edt(~cat)
    sgmc_off = (np.nan_to_num(sgmc_mask, nan=0.0) > 0) & footprint & (d_cat > float(min_cat_dist_px))
    p = np.where(footprint & (~cat), np.nan_to_num(pred, nan=0.0), 0.0)
    comp = D.components(p, sgmc_off)
    return {
        "metric_label": "SGMC-OFFCAT-CONTROL-DTI",
        "evaluator_version": EVALUATOR_VERSION,
        "n_offcatalogue_sgmc_positives": int(comp.G),
        "dti": round(float(comp.score), 6),
        "T": round(float(comp.T), 3),
        "S": round(float(comp.S), 2),
        "M": round(float(comp.M), 3),
    }


def check_registry_surface_uniqueness(
    surface_fp: np.ndarray,
    footprint: np.ndarray,
    registry_paths: Iterable[str | Path],
    *,
    max_rank_corr: float = MAX_SURFACE_RANK_CORR,
    corr_stride: int = 5,
) -> dict:
    """Run the Rule-1 continuous-surface check *before* dot placement.

    This separate entry point makes the protocol's ordering testable.  It uses
    the same deterministic strided Spearman calculation as
    :func:`check_registry_uniqueness`, but has no dot input and therefore cannot
    accidentally turn a post-placement check into evidence of a pre-placement
    gate.
    """
    vals = np.asarray(surface_fp, dtype=np.float64)
    if vals.ndim != 1 or vals.size != int(footprint.sum()):
        raise ValueError("surface_fp must be one value for every footprint pixel")
    s_sub = vals[::corr_stride]
    r_surf = rankdata(s_sub, method="average")
    r_surf_c = r_surf - r_surf.mean()
    r_surf_norm = float(np.linalg.norm(r_surf_c))

    comparisons = []
    seen_names: set[str] = set()
    max_rho = 0.0
    closest = ""
    for rp in sorted(Path(p) for p in registry_paths):
        if not rp.is_file() or rp.name in seen_names:
            continue
        seen_names.add(rp.name)
        with rasterio.open(rp) as src:
            reg_arr = np.nan_to_num(src.read(1), nan=0.0, posinf=0.0, neginf=0.0)
        if reg_arr.shape != footprint.shape:
            continue
        reg_fp = reg_arr[footprint][::corr_stride].astype(np.float64)
        r_reg = rankdata(reg_fp, method="average")
        r_reg_c = r_reg - r_reg.mean()
        r_reg_norm = float(np.linalg.norm(r_reg_c))
        rho = (
            abs(float(np.dot(r_surf_c, r_reg_c)) / (r_surf_norm * r_reg_norm))
            if (r_surf_norm > 0 and r_reg_norm > 0)
            else 0.0
        )
        comparisons.append({"registry_raster": rp.name, "surface_abs_rank_corr": round(rho, 5)})
        if rho > max_rho:
            max_rho = rho
            closest = rp.name

    return {
        "uniqueness_gate_version": UNIQUENESS_GATE_VERSION,
        "phase": "pre-placement continuous surface",
        "n_registry_rasters_checked": len(comparisons),
        "max_allowed_rank_corr": max_rank_corr,
        "surface_max_abs_rank_corr": round(max_rho, 5),
        "surface_closest_raster": closest,
        "is_duplicate": bool(max_rho > max_rank_corr),
        "uniqueness_pass": bool(max_rho <= max_rank_corr),
        "comparisons": comparisons,
    }


def check_registry_uniqueness(
    surface_fp: np.ndarray,
    candidate_dots: np.ndarray,
    footprint: np.ndarray,
    registry_paths: Iterable[str | Path],
    *,
    max_rank_corr: float = MAX_SURFACE_RANK_CORR,
    max_dot_overlap_3px: float = MAX_DOT_OVERLAP_3PX,
    corr_stride: int = 5,
) -> dict:
    """Rule 1 LANE / UNIQUENESS GATE:
    Checks BOTH:
      1. Continuous surface BEFORE placement: |Spearman rho| vs every registry raster <= 0.90
      2. Final emitted dots AFTER placement: fraction of candidate dots within <= 3.0 px
         of any registry raster's positive pixels <= 0.70.
    """
    cand_bool = (np.nan_to_num(candidate_dots, nan=0.0) > 0) & footprint
    cy, cx = np.nonzero(cand_bool)
    cand_pts = np.c_[cy, cx].astype(np.float64)
    n_cand = int(cand_pts.shape[0])
    if n_cand == 0:
        raise ValueError("candidate has 0 emitted dots inside footprint")

    # Subsample footprint deterministically for fast exact rank correlation (N ~ 1.03M pixels)
    s_sub = np.asarray(surface_fp[::corr_stride], dtype=np.float64)
    r_surf = rankdata(s_sub, method="average")
    r_surf_c = r_surf - r_surf.mean()
    r_surf_norm = float(np.linalg.norm(r_surf_c))

    # Also rank-correlate final binary dot raster on footprint
    dots_fp = cand_bool[footprint][::corr_stride].astype(np.float64)
    r_dots = rankdata(dots_fp, method="average")
    r_dots_c = r_dots - r_dots.mean()
    r_dots_norm = float(np.linalg.norm(r_dots_c))

    cand_tree = cKDTree(cand_pts)
    comparisons = []
    max_surf_rho = 0.0
    max_surf_name = ""
    max_dot_rho = 0.0
    max_overlap_fwd = 0.0
    max_overlap_name = ""
    max_overlap_mutual = 0.0

    seen_names: set[str] = set()
    for rp in sorted(Path(p) for p in registry_paths):
        if not rp.is_file() or rp.name in seen_names:
            continue
        seen_names.add(rp.name)
        with rasterio.open(rp) as src:
            reg_arr = np.nan_to_num(src.read(1), nan=0.0, posinf=0.0, neginf=0.0)
        if reg_arr.shape != footprint.shape:
            continue

        reg_fp = reg_arr[footprint][::corr_stride].astype(np.float64)
        r_reg = rankdata(reg_fp, method="average")
        r_reg_c = r_reg - r_reg.mean()
        r_reg_norm = float(np.linalg.norm(r_reg_c))

        surf_rho = (
            abs(float(np.dot(r_surf_c, r_reg_c)) / (r_surf_norm * r_reg_norm))
            if (r_surf_norm > 0 and r_reg_norm > 0)
            else 0.0
        )
        dot_rho = (
            abs(float(np.dot(r_dots_c, r_reg_c)) / (r_dots_norm * r_reg_norm))
            if (r_dots_norm > 0 and r_reg_norm > 0)
            else 0.0
        )

        reg_pos = (reg_arr > 0) & footprint
        ry, rx = np.nonzero(reg_pos)
        n_reg = int(ry.size)
        if n_reg > 0:
            reg_pts = np.c_[ry, rx].astype(np.float64)
            reg_tree = cKDTree(reg_pts)
            d_c2r, _ = reg_tree.query(cand_pts, k=1, distance_upper_bound=3.000001)
            fwd_ov = float(np.isfinite(d_c2r).mean())
            d_r2c, _ = cand_tree.query(reg_pts, k=1, distance_upper_bound=3.000001)
            rev_ov = float(np.isfinite(d_r2c).mean())
            mut_ov = min(fwd_ov, rev_ov)
        else:
            fwd_ov = rev_ov = mut_ov = 0.0

        # The user protocol is a directed coverage test with no dense-reference
        # exception: "more than 70% of *your dots* within 3 px of one registry
        # raster's dots" means cand->registry overlap for every raster.  Older
        # code substituted symmetric F1 for dense references.  That silently
        # weakened the stated gate and could mark a near-universally covered
        # candidate unique.  Keep F1 as a diagnostic only; never use it for the
        # verdict (IR-91-CCR-02).
        f1_ov = (2.0 * fwd_ov * rev_ov / (fwd_ov + rev_ov)) if (fwd_ov + rev_ov) > 0 else 0.0
        eff_dot_ov = fwd_ov
        is_dup = (surf_rho > max_rank_corr) or (dot_rho > max_rank_corr) or (fwd_ov > max_dot_overlap_3px)
        comparisons.append({
            "registry_raster": rp.name,
            "n_registry_positive": n_reg,
            "surface_abs_rank_corr": round(surf_rho, 5),
            "dots_abs_rank_corr": round(dot_rho, 5),
            "cand_within_3px_of_reg": round(fwd_ov, 5),
            "reg_within_3px_of_cand": round(rev_ov, 5),
            "f1_dot_overlap_3px": round(f1_ov, 5),
            "mutual_min_overlap_3px": round(mut_ov, 5),
            "effective_dot_overlap_3px": round(eff_dot_ov, 5),
            "duplicate_flag": bool(is_dup),
        })

        if surf_rho > max_surf_rho:
            max_surf_rho = surf_rho
            max_surf_name = rp.name
        if dot_rho > max_dot_rho:
            max_dot_rho = dot_rho
        if eff_dot_ov > max_overlap_fwd:
            max_overlap_fwd = eff_dot_ov
            max_overlap_name = rp.name
        if mut_ov > max_overlap_mutual:
            max_overlap_mutual = mut_ov

    any_dup = any(c["duplicate_flag"] for c in comparisons)
    return {
        "uniqueness_gate_version": UNIQUENESS_GATE_VERSION,
        "dot_overlap_policy": "strict directed candidate-within-3px-of-registry for every registry raster",
        "n_registry_rasters_checked": len(comparisons),
        "max_allowed_rank_corr": max_rank_corr,
        "max_allowed_dot_overlap_3px": max_dot_overlap_3px,
        "surface_max_abs_rank_corr": round(max_surf_rho, 5),
        "surface_closest_raster": max_surf_name,
        "dots_max_abs_rank_corr": round(max_dot_rho, 5),
        "dots_max_3px_overlap": round(max_overlap_fwd, 5),
        "dots_closest_raster": max_overlap_name,
        "dots_max_mutual_3px_overlap": round(max_overlap_mutual, 5),
        "is_duplicate": bool(any_dup),
        "uniqueness_pass": not any_dup,
        "comparisons": comparisons,
    }


def _sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 without loading a raster into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frozen_registry_paths(*, verify_hashes: bool = True) -> tuple[list[Path], dict]:
    """Load the frozen registry inventory without pretending it is universal.

    The parallel-run protocol is an *any registry raster* gate.  Earlier callers
    used only ``data/registry`` (usually eight convenience references), even
    when the checked-in frozen inventory named many more references in
    ``data/fleet_registry``.  That is a scoped diagnostic, not a valid complete
    gate.  This helper reads ``registry/comparison_inventory.json``, reports
    every missing or hash-mismatched pin, and returns only verified paths.

    ``complete_inventory`` means every file named by the frozen inventory is
    available and (when requested) matches its pinned hash.  It deliberately
    does **not** mean that the inventory is a universal public registry; that
    provenance boundary is carried separately in the JSON inventory.
    """
    inventory_path = ROOT / "registry" / "comparison_inventory.json"
    status = {
        "inventory_path": str(inventory_path.relative_to(ROOT)),
        "inventory_present": inventory_path.is_file(),
        "complete_inventory": False,
        "complete_universal_registry": False,
        "n_declared": 0,
        "n_verified": 0,
        "missing": [],
        "hash_mismatches": [],
        "invalid_rows": [],
    }
    if not inventory_path.is_file():
        return [], status

    try:
        payload = json.loads(inventory_path.read_text(encoding="utf-8"))
        rows = payload["files"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        status["invalid_rows"].append(f"inventory parse error: {exc}")
        return [], status

    status["complete_universal_registry"] = bool(payload.get("complete_universal_registry", False))
    verified: list[Path] = []
    seen_paths: set[Path] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("sha256"), str):
            status["invalid_rows"].append(f"row {index}: missing path or sha256")
            continue
        path = ROOT / row["path"]
        try:
            path.resolve().relative_to(ROOT.resolve())
        except ValueError:
            status["invalid_rows"].append(f"row {index}: path escapes repository")
            continue
        if not path.is_file():
            status["missing"].append(row["path"])
            continue
        if verify_hashes and _sha256_file(path) != row["sha256"]:
            status["hash_mismatches"].append(row["path"])
            continue
        if path not in seen_paths:
            verified.append(path)
            seen_paths.add(path)

    status["n_declared"] = len(rows)
    status["n_verified"] = len(verified)
    status["complete_inventory"] = not (
        status["missing"] or status["hash_mismatches"] or status["invalid_rows"]
    ) and len(verified) == len(rows)
    return sorted(verified), status


def default_registry_paths() -> list[Path]:
    """Return every locally available frozen-reference raster, not just eight.

    This remains a local index, so callers that decide whether an artifact is
    submittable must also inspect :func:`frozen_registry_paths` and reject an
    incomplete or non-universal scope.  The old ``data/registry`` and sibling
    locations are retained for cold checkouts and compatibility with historical
    evidence.
    """
    paths, _status = frozen_registry_paths(verify_hashes=False)
    legacy_dirs = (
        ROOT / "data" / "registry",
        ROOT / "data" / "registry_siblings",
        ROOT / "data" / "fleet_registry",
    )
    seen = {path.resolve() for path in paths}
    for folder in legacy_dirs:
        for path in sorted(folder.glob("*.tif")):
            if path.resolve() not in seen:
                paths.append(path)
                seen.add(path.resolve())
    return sorted(paths)
