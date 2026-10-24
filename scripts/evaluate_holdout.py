"""Historical H91-local holdout evaluator and feature-alone canary.

This module is retained for provenance and small regression tests; it is not
`vendor.gems57.evaluate_holdout.py` and its H91 scores are not comparable to the
pinned shared evaluator. Registry measurements are a thin adapter to
`vendor.gems57.uniqueness`; path-only subsets can never certify uniqueness.
"""

from __future__ import annotations

import glob
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import dti as D  # noqa: E402

EVALUATOR_VERSION = "gems91-hide-recover-v1.0"
DEFAULT_BRIDGE_PX = 3
DEFAULT_BUFFER_PX = 10.0
MAX_LEAKAGE_AUC = 0.90
MAX_SURFACE_RANK_CORR = 0.90
MAX_DOT_OVERLAP_3PX = 0.70


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


def score_pooled_holdout(
    fold_predictions: dict[int, np.ndarray],
    folds: list[HoldoutFold],
    footprint: np.ndarray,
    *,
    n_boot: int = 200,
    tile_px: int = 50,
    seed: int = 91,
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
        # Mask visible faults & buffer pixel-exactly
        active_domain = domain & (~f.visible_faults) & (~f.buffer_mask)

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
        "evaluator_version": EVALUATOR_VERSION,
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


def check_registry_uniqueness(
    surface_fp: np.ndarray,
    candidate_dots: np.ndarray,
    footprint: np.ndarray,
    registry_paths: Iterable[str | Path] | dict | str | Path,
    *,
    max_rank_corr: float = MAX_SURFACE_RANK_CORR,
    max_dot_overlap_3px: float = MAX_DOT_OVERLAP_3PX,
    corr_stride: int = 1,
) -> dict:
    """Compatibility adapter to the pinned shared literal uniqueness gate.

    Historical H91 supplied a curated list and applied symmetric F1 to dense
    references. That was not the standing rule. Measurements delegate to
    ``vendor.gems57.uniqueness.compare_array_to_registry``: exact full-footprint
    ranks, directed candidate-dot overlap at 3 px, and no density exception.
    The adapter applies the rank threshold to continuous surfaces and the
    directed-overlap threshold to emitted dots. A path list is diagnostic only
    and cannot certify uniqueness without a complete-inventory certificate.
    """
    import json

    if max_rank_corr != 0.90 or max_dot_overlap_3px != 0.70 or corr_stride != 1:
        raise ValueError("The shared protocol fixes full-footprint rho at 0.90 and 3px directed overlap at 0.70")

    from vendor.gems57.uniqueness import compare_array_to_registry

    fp = np.asarray(footprint)
    if fp.ndim != 2 or fp.dtype != np.dtype(bool) or not fp.any():
        raise ValueError("nonempty 2-D boolean footprint required")
    surface_values = np.asarray(surface_fp, dtype=np.float32)
    if surface_values.shape == fp.shape:
        surface = surface_values
    elif surface_values.ndim == 1 and surface_values.size == int(fp.sum()):
        surface = np.zeros(fp.shape, dtype=np.float32)
        surface[fp] = surface_values
    else:
        raise ValueError("surface must be a footprint-sized vector or full 2-D grid")
    dots = np.asarray(candidate_dots, dtype=np.float32)
    if dots.shape != fp.shape:
        raise ValueError("candidate dots and footprint grids differ")

    # Normalize legacy inventory shapes only; all measurements and duplicate
    # decisions remain in the pinned shared module.
    if isinstance(registry_paths, dict):
        index = dict(registry_paths)
    elif isinstance(registry_paths, (str, Path)) and str(registry_paths).lower().endswith(".json"):
        raw = json.loads(Path(registry_paths).read_text(encoding="utf-8"))
        if "rasters" in raw:
            index = raw
        elif "files" in raw:
            index = {
                "complete_accessible_scan": bool(raw.get("complete_universal_registry", False)),
                "errors": list(raw.get("missing_scope", [])),
                "rasters": [
                    {
                        "repo_first": raw.get("scope", "pinned registry inventory"),
                        "sources": [item.get("source_url", item["path"])],
                        "cache_file": item["path"],
                        "sha256": item.get("sha256"),
                    }
                    for item in raw["files"]
                ],
            }
        else:
            raise ValueError("registry JSON must contain rasters or files")
    else:
        paths = [Path(registry_paths)] if isinstance(registry_paths, (str, Path)) else [Path(x) for x in registry_paths]
        unique_paths = []
        seen = set()
        for path in sorted(paths):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                unique_paths.append(resolved)
        index = {
            "complete_accessible_scan": False,
            "errors": ["Curated local path list has no complete-registry certificate; diagnostic only"],
            "rasters": [
                {
                    "repo_first": "local diagnostic inventory",
                    "sources": [path.name],
                    "cache_file": str(path),
                    "sha256": None,
                }
                for path in unique_paths
            ],
        }

    surface_report = compare_array_to_registry(surface, index, fp)
    dots_report = compare_array_to_registry(dots, index, fp)
    surface_rows = surface_report["rows"]
    dot_rows = dots_report["rows"]

    def _max_abs_rho(rows):
        available = [r for r in rows if "error" not in r and r.get("spearman_full_footprint") is not None]
        if not available:
            return None, ""
        row = max(available, key=lambda r: abs(float(r["spearman_full_footprint"])))
        return abs(float(row["spearman_full_footprint"])), row.get("submission", "")

    def _max_overlap(rows):
        available = [r for r in rows if "error" not in r and r.get("my_dots_within_3px_of_theirs") is not None]
        if not available:
            return None, ""
        row = max(available, key=lambda r: float(r["my_dots_within_3px_of_theirs"]))
        return float(row["my_dots_within_3px_of_theirs"]), row.get("submission", "")

    surface_rho, surface_name = _max_abs_rho(surface_rows)
    dots_rho, _ = _max_abs_rho(dot_rows)
    overlap, overlap_name = _max_overlap(dot_rows)

    # compare_array_to_registry is a general raster comparator and reports both
    # rank and support-overlap flags for every input. The protocol assigns the
    # rank threshold to the continuous surface and directed overlap to emitted
    # dots; treating a positive-valued score surface as a dot mask would make
    # every broad surface look like a duplicate. Keep the shared measurements,
    # but apply each literal threshold only to its designated representation.
    surface_rank_duplicate = any(
        "error" not in row and row.get("spearman_full_footprint") is not None
        and abs(float(row["spearman_full_footprint"])) > max_rank_corr
        for row in surface_rows
    )
    dot_overlap_duplicate = any(
        "error" not in row and row.get("my_dots_within_3px_of_theirs") is not None
        and float(row["my_dots_within_3px_of_theirs"]) > max_dot_overlap_3px
        for row in dot_rows
    )
    exact_dot_duplicate = any(
        "error" not in row and (row.get("identical_bytes") or row.get("identical_decoded_predictions"))
        for row in dot_rows
    )
    duplicate = bool(surface_rank_duplicate or dot_overlap_duplicate or exact_dot_duplicate)
    complete = bool(surface_report["complete_accessible_scan"] and dots_report["complete_accessible_scan"])
    errors = list(surface_report.get("source_errors", []))
    errors.extend(dots_report.get("source_errors", []))
    errors.extend(
        f"{row.get('submission', row.get('file', 'unknown'))}: {row['error']}"
        for row in surface_rows + dot_rows if "error" in row
    )
    measurement_unverified = []
    for row in surface_rows:
        if "error" not in row and row.get("spearman_full_footprint") is None:
            measurement_unverified.append(
                f"{row.get('submission', row.get('file', 'unknown'))}: continuous-surface rank correlation unavailable"
            )
    for row in dot_rows:
        if "error" not in row and row.get("my_dots_within_3px_of_theirs") is None:
            measurement_unverified.append(
                f"{row.get('submission', row.get('file', 'unknown'))}: final-dot overlap unavailable"
            )

    surface_measurements = []
    for row in surface_rows:
        if "error" in row:
            surface_measurements.append({"submission": row.get("submission", ""), "error": row["error"]})
            continue
        rho = row.get("spearman_full_footprint")
        surface_measurements.append({
            "submission": row.get("submission", ""),
            "file": row.get("file", ""),
            "sha256": row.get("sha256"),
            "spearman_full_footprint": rho,
            "surface_rank_measurement_status": "MEASURED" if rho is not None else "UNVERIFIED",
            "surface_rank_duplicate": bool(rho is not None and abs(float(rho)) > max_rank_corr),
            "positive_support_overlap_diagnostic_only": row.get("my_dots_within_3px_of_theirs"),
        })
    dot_measurements = []
    for row in dot_rows:
        if "error" in row:
            dot_measurements.append({"submission": row.get("submission", ""), "error": row["error"]})
            continue
        dot_overlap_value = row.get("my_dots_within_3px_of_theirs")
        dot_measurements.append({
            "submission": row.get("submission", ""),
            "file": row.get("file", ""),
            "sha256": row.get("sha256"),
            "my_dots_within_3px_of_theirs": dot_overlap_value,
            "dot_overlap_measurement_status": "MEASURED" if dot_overlap_value is not None else "UNVERIFIED",
            "dot_overlap_duplicate": bool(dot_overlap_value is not None and float(dot_overlap_value) > max_dot_overlap_3px),
            "spearman_full_footprint_diagnostic_only": row.get("spearman_full_footprint"),
            "identical_bytes": row.get("identical_bytes", False),
            "identical_decoded_predictions": row.get("identical_decoded_predictions", False),
        })

    return {
        "n_registry_rasters_checked": int(min(surface_report["registry_rasters_checked"], dots_report["registry_rasters_checked"])),
        "registry_rasters_expected": max(surface_report["registry_rasters_expected"], dots_report["registry_rasters_expected"]),
        "registry_inventory_complete": complete,
        "registry_source_errors": errors,
        "registry_measurement_unverified": measurement_unverified,
        "surface_max_abs_rank_corr": surface_rho,
        "surface_closest_raster": surface_name,
        "dots_abs_rank_corr": dots_rho,
        "dots_max_3px_overlap": overlap,
        "dots_closest_raster": overlap_name,
        "surface_rank_duplicate": surface_rank_duplicate,
        "dot_overlap_duplicate": dot_overlap_duplicate,
        "exact_dot_duplicate": exact_dot_duplicate,
        "is_duplicate": duplicate,
        "uniqueness_pass": bool(complete and not errors and not measurement_unverified and not duplicate
                                and surface_report["candidate_rank_variation"]
                                and dots_report["my_dots"] > 0),
        "binding_rule": "literal-all-rasters; continuous-surface |Spearman| > 0.90 or final-dot directed 3px overlap > 0.70",
        "surface_report": {
            "protocol_phase": "continuous_surface",
            "binding_metric": "full-footprint absolute Spearman correlation",
            "measurements": surface_measurements,
        },
        "dots_report": {
            "protocol_phase": "final_candidate_dots",
            "binding_metric": "directed candidate-dot overlap within 3 px",
            "measurements": dot_measurements,
        },
    }

def default_registry_paths() -> list[Path]:
    """Return locally present comparison rasters for diagnostics, never clearance.

    The pinned public comparison inventory also contains entries that are not
    restored locally; the checker receives a path list only as a diagnostic and
    therefore reports ``registry_inventory_complete=False``.
    """
    roots = [
        ROOT / "data" / "registry",
        ROOT / "data" / "registry_siblings",
        ROOT / "data" / "fleet_registry",
    ]
    paths = []
    seen = set()
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.tif")):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(resolved)
    return paths
