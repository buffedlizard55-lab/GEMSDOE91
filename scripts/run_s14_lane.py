#!/usr/bin/env python3
"""Session 14 Pre-Registered Runner (`S14-HVDC`, 2026-10-24).

Executes the 3 frozen experiments preregistered in `docs/HYPOTHESES_S14.md`:
  - Reference (`0` experiment budget): Reproduces current `GEMSDOE91` #1 candidate
    `S13-PTHA E3` (`0.244601 HOLDOUT-DTI`) on the identical 4 `gems91-hide-recover-v1.0`
    quadrant folds for exact aligned paired 5 km spatial block-bootstrap CIs.
  - `E1` (`H14-1`): Up-Gradient Hydrothermal & Blind Geothermometric Plume Back-Projection
    (`dist_known_fault_px` strictly banned) + Fold-Safe Playa/Basin Deconfounding +
    Salem (2007) Intrabasinal Tilt-Depth + Corrected Positive Ruhl Swarm Excess
    (`89` clean Stage-1 features, matched `PTHA` Dinkelbach emitter).
  - `E2` (`H14-1 + H14-2`): Leak-free 6-pair inner-OOF Two-Stage En-Echelon Relay-Ramp
    & Collinear Alluvial-Wash Bridge Structural Auto-Context (`101` features, matched
    `PTHA` Dinkelbach emitter).
  - `E3` (`H14-1..2 + H14-3`): Reuses the better OOF surfaces of `{E1, E2}` (`0` extra
    model fits) and applies Continuous Steger Gradient-Normal Crest Localization +
    Self-Credit-Exact (`M`-Term, `1 - m_hat_j`) Dinkelbach Fractional Programming.

Strict compliance with Parallel-Run Protocol Rules 1-6.
"""

from __future__ import annotations

import gc
import hashlib
import itertools
import json
import math
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems91 import dd_vtc_pu as DD
from gems91 import hvdc as HVDC
from gems91 import io as IO
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import readiness as RD
from scripts import dti as DTI
from scripts import evaluate_holdout as EH
from scripts import submission_writer as SW

DATA = ROOT / "data"
TEMPLATE_TIF = DATA / "official" / "sample_submission.tif"
CATALOGUE_TIF = DATA / "official" / "existing_faults.tif"
FEATURES_TIF = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC_TIF = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_ZEROS_TIF = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"

CACHE_DIR = DATA / "derived"
RELEASES_DIR = DATA / "releases"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"
HYPOTHESES_MD = ROOT / "docs" / "HYPOTHESES_S14.md"
EVIDENCE_JSON = ROOT / "evidence" / "s14_hvdc_metrics_20261024.json"
RUN_CARD_S14_JSON = ROOT / "docs" / "run-card-S14.json"

MAX_EXPERIMENTS = 3
MAX_BUDGET_SECONDS = 7200.0
TARGET_POOL_DOTS = 48_000

SYNTHETIC_BLANKET_SUBSTRINGS = (
    "r13lattice",
    "r13_lattice",
    "r14_union_tips10_lat6",
    "r11_greedy_mp",
    "rand5pct",
    "random_p005",
)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def _fold_active_and_eligible(
    fold: EH.HoldoutFold,
    folds: list[EH.HoldoutFold],
    footprint: np.ndarray,
    collar_px: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    other_withheld = np.zeros_like(footprint, dtype=bool)
    for f2 in folds:
        if f2.fold_id != fold.fold_id:
            other_withheld |= f2.withheld_faults
    domain = ((fold.region_mask & (~other_withheld)) | fold.withheld_faults) & footprint
    active_domain = domain & (~fold.visible_faults) & (~fold.buffer_mask)
    d_vis = ndi.distance_transform_edt(~fold.visible_faults)
    eligible = active_domain & (d_vis > float(collar_px))
    return active_domain, eligible


def _accumulate_fold_tiles(
    fold_preds: dict[int, np.ndarray],
    folds: list[EH.HoldoutFold],
    footprint: np.ndarray,
    *,
    tile_px: int = 50,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    radius = DTI.kernel_radius_px()
    dy_off, dx_off, k_w = DTI._kernel_offsets(radius)
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
        pred_raw = np.nan_to_num(fold_preds[f.fold_id], nan=0.0, posinf=0.0, neginf=0.0)
        other_withheld = np.zeros_like(footprint, dtype=bool)
        for f2 in folds:
            if f2.fold_id != f.fold_id:
                other_withheld |= f2.withheld_faults
        domain = ((f.region_mask & (~other_withheld)) | f.withheld_faults) & footprint
        active_domain = domain & (~f.visible_faults) & (~f.buffer_mask)

        p = np.where(active_domain, pred_raw, 0.0)
        g = f.withheld_faults

        best_on_g = np.zeros_like(p, dtype=np.float64)
        g_float = g.astype(np.float64)
        best_match_p = np.zeros_like(p, dtype=np.float64)
        for dy, dx, kw in zip(dy_off, dx_off, k_w):
            np.maximum(best_on_g, DTI._shift(p, int(dy), int(dx)) * kw, out=best_on_g)
            np.maximum(best_match_p, DTI._shift(g_float, int(dy), int(dx)) * kw, out=best_match_p)

        g_idx = np.nonzero(g)
        np.add.at(tile_T, tile_id_grid[g_idx], best_on_g[g_idx])
        np.add.at(tile_G, tile_id_grid[g_idx], 1.0)
        p_nz = np.nonzero(p > 0)
        if p_nz[0].size:
            np.add.at(tile_S, tile_id_grid[p_nz], p[p_nz])
            np.add.at(tile_M, tile_id_grid[p_nz], (p * best_match_p)[p_nz])

    return tile_T, tile_S, tile_M, tile_G


def compute_aligned_paired_bootstrap(
    cand_tiles: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    base_tiles: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    *,
    cand_pooled_dti: float,
    base_pooled_dti: float,
    n_boot: int = 400,
    seed: int = 91042,
) -> dict:
    tc, sc, mc, gc_arr = cand_tiles
    tb, sb, mb, _ = base_tiles
    active = np.nonzero((gc_arr > 0) | (sc > 0) | (sb > 0))[0]
    rng = np.random.default_rng(seed)

    diffs = np.empty(n_boot, dtype=np.float64)
    for b in range(n_boot):
        draw = rng.choice(active, size=active.size, replace=True)
        G_s = float(gc_arr[draw].sum())
        Tc_s, Sc_s, Mc_s = float(tc[draw].sum()), float(sc[draw].sum()), float(mc[draw].sum())
        Tb_s, Sb_s, Mb_s = float(tb[draw].sum()), float(sb[draw].sum()), float(mb[draw].sum())
        dc = DTI.ALPHA * Tc_s + DTI.ALPHA * (Sc_s - Mc_s) + DTI.BETA * G_s
        db = DTI.ALPHA * Tb_s + DTI.ALPHA * (Sb_s - Mb_s) + DTI.BETA * G_s
        sc_dti = Tc_s / dc if dc > 0.0 else 0.0
        sb_dti = Tb_s / db if db > 0.0 else 0.0
        diffs[b] = sc_dti - sb_dti

    delta_exact = float(cand_pooled_dti) - float(base_pooled_dti)
    ci_lo, ci_hi = np.percentile(diffs, [2.5, 97.5])
    ci_lo = min(float(ci_lo), delta_exact)
    ci_hi = max(float(ci_hi), delta_exact)
    return {
        "delta": round(delta_exact, 6),
        "ci95": [round(ci_lo, 6), round(ci_hi, 6)],
        "prob_positive": round(float(np.mean(diffs > 0.0)), 4),
        "n_paired_5km_tiles": int(active.size),
        "n_bootstrap_draws": n_boot,
    }


def _collect_comparison_scopes(exclude_prefix: str = "gems91-s14-hvdc-") -> dict[str, list[Path]]:
    canon_paths = [
        p for p in sorted((DATA / "registry").glob("*.tif"))
        if not p.name.startswith(exclude_prefix)
    ]

    seen_sha: dict[str, Path] = {}
    for d in (DATA / "fleet_registry", DATA / "retracted_geod", DATA / "registry", DOWNLOADS_DIR):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.tif")):
            if p.name.startswith(exclude_prefix) or p.name.endswith("-nan.tif"):
                continue
            sha = IO.sha256_file(p)
            if sha not in seen_sha:
                seen_sha[sha] = p
    all_paths = list(seen_sha.values())

    ext_seen: dict[str, Path] = {}
    for d in (DATA / "fleet_registry", DATA / "retracted_geod", DATA / "registry"):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.tif")):
            if p.name.startswith(exclude_prefix) or p.name.endswith("-nan.tif"):
                continue
            if any(sub in p.name for sub in SYNTHETIC_BLANKET_SUBSTRINGS):
                continue
            sha = IO.sha256_file(p)
            if sha not in ext_seen:
                ext_seen[sha] = p
    ext_real_paths = list(ext_seen.values())

    sibling_paths = [
        p
        for p in sorted(DOWNLOADS_DIR.glob("*-zeros.tif"))
        if not p.name.startswith(exclude_prefix)
    ]
    return {
        "canonical_registry": canon_paths,
        "external_real_rasters": ext_real_paths,
        "in_repo_siblings": sibling_paths,
        "universal_all_files": all_paths,
    }


def _check_uniqueness_fast(
    surface_fp: np.ndarray,
    dots_2d: np.ndarray,
    footprint: np.ndarray,
    paths: list[Path],
    *,
    subsample_step: int = 20,
    max_pos_filter: int | None = None,
) -> dict:
    cand_pts = (dots_2d > 0) & footprint
    cr, cc = np.nonzero(cand_pts)
    n_cand = int(cr.size)
    h, w = footprint.shape
    offs_r3 = [(dy, dx) for dy in range(-3, 4) for dx in range(-3, 4) if dy * dy + dx * dx <= 9]

    idx_sub = np.arange(0, int(footprint.sum()), subsample_step, dtype=np.int64)
    s_sub = surface_fp[idx_sub].astype(np.float64)
    d_fp_sub = dots_2d[footprint][idx_sub].astype(np.float64)

    rows = []
    max_s_rho = 0.0
    max_s_name = ""
    max_ov = 0.0
    max_ov_name = ""

    for rp in paths:
        with rasterio.open(rp) as src:
            rarr = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)
        if rarr.shape != footprint.shape:
            continue
        reg_pos = (rarr > 0) & footprint
        n_reg = int(reg_pos.sum())
        if max_pos_filter is not None and n_reg > max_pos_filter:
            continue

        r_sub = rarr[footprint][idx_sub].astype(np.float64)
        if np.std(r_sub) < 1e-12 or np.std(s_sub) < 1e-12:
            s_rho = 0.0
        else:
            val = float(spearmanr(s_sub, r_sub).statistic)
            s_rho = 0.0 if np.isnan(val) else val

        if np.std(r_sub) < 1e-12 or np.std(d_fp_sub) < 1e-12:
            d_rho = 0.0
        else:
            val_d = float(spearmanr(d_fp_sub, r_sub).statistic)
            d_rho = 0.0 if np.isnan(val_d) else val_d

        if n_cand > 0 and n_reg > 0:
            hit = np.zeros(n_cand, dtype=bool)
            for dy, dx in offs_r3:
                hit |= reg_pos[np.clip(cr + dy, 0, h - 1), np.clip(cc + dx, 0, w - 1)]
            ov = float(hit.sum()) / float(n_cand)
        else:
            ov = 0.0

        if abs(s_rho) > abs(max_s_rho):
            max_s_rho = s_rho
            max_s_name = rp.name
        if ov > max_ov:
            max_ov = ov
            max_ov_name = rp.name

        rows.append({
            "raster": rp.name,
            "n_reg_positives": n_reg,
            "surface_spearman_rho": round(s_rho, 6),
            "dots_spearman_rho": round(d_rho, 6),
            "dots_within_3px_fraction": round(ov, 6),
        })

    pass_flag = (abs(max_s_rho) <= 0.90) and (max_ov <= 0.70)
    return {
        "n_checked": len(rows),
        "pass": bool(pass_flag),
        "max_abs_surface_spearman": round(abs(max_s_rho), 6),
        "surface_closest_raster": max_s_name,
        "max_3px_dot_overlap": round(max_ov, 6),
        "dots_closest_raster": max_ov_name,
        "top_5_by_overlap": sorted(rows, key=lambda x: x["dots_within_3px_fraction"], reverse=True)[:5],
    }


def _compute_fold_split_sha256(folds: list[EH.HoldoutFold]) -> str:
    h = hashlib.sha256()
    for f in folds:
        h.update(f.name.encode("utf-8"))
        h.update(np.packbits(f.region_mask.ravel()).tobytes())
        h.update(np.packbits(f.withheld_faults.ravel()).tobytes())
    return h.hexdigest()


def main() -> int:
    t0 = time.perf_counter()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_JSON.parent.mkdir(parents=True, exist_ok=True)

    if not HYPOTHESES_MD.is_file():
        raise RuntimeError(f"Pre-registration file missing: {HYPOTHESES_MD}")
    prereg_sha256 = IO.sha256_file(HYPOTHESES_MD)
    _log(f"=== Session 14 Lane Runner (`S14-HVDC`) | prereg_sha256={prereg_sha256[:16]} ===")

    with rasterio.open(TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE_TIF) as src:
        cat_mask = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC_TIF) as src:
        sgmc_mask = (src.read(1) > 0) & footprint
    with rasterio.open(R0_ZEROS_TIF) as src:
        r0_dots = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)

    n_fp = int(footprint.sum())
    n_cat = int(cat_mask.sum())
    _log(f"Loaded footprint={n_fp:,} px, catalogue={n_cat:,} px")

    # 1. Build exact 4 spatially-blocked whole-segment folds (`gems91-hide-recover-v1.0`)
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=10.0)
    split_sha = _compute_fold_split_sha256(folds)
    _log(f"Constructed {len(folds)} quadrant folds (`{EH.EVALUATOR_VERSION}`, split_sha256={split_sha[:16]})")

    fold_eligible: dict[int, np.ndarray] = {}
    fold_train_elig: dict[int, np.ndarray] = {}
    for f in folds:
        _, elig = _fold_active_and_eligible(f, folds, footprint, collar_px=3.0)
        fold_eligible[f.fold_id] = elig
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        d_vis = ndi.distance_transform_edt(~f.visible_faults)
        fold_train_elig[f.fold_id] = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)

    d_cat_full = ndi.distance_transform_edt(~cat_mask)
    full_eligible = footprint & (~cat_mask) & (d_cat_full > 3.0)
    n_full_elig = int(full_eligible.sum())
    del d_cat_full

    # 2. Build/open cached label-free feature memmaps (Rule 2: reuse shared stack + add HVDC)
    _log("Building/loading cached H91 static (49), S11 MHTR (16), S13 PTHA (20), and S14 HVDC (18) memmaps...")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES_TIF,
        gdr_csv=GDR_CSV,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES_TIF,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES_TIF,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    X_hvdc, hvdc_names, _ = HVDC.build_or_load_hvdc_feature_memmap(
        features_tif=FEATURES_TIF,
        gdr_csv=GDR_CSV,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    _log(f"Feature memmaps ready ({time.perf_counter() - t0:.1f}s)")

    # S13 reference columns (for exact byte/metric reproduction of `S13-PTHA E3`)
    s13_static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    s13_ptha_cols = list(range(20))

    # Clean S14-HVDC E1 columns (89 features including fold OLS deconfounding)
    hvdc_static_cols = list(range(24)) + [31, 33] + list(range(38, 44)) + [44, 45, 46, 48]  # 36 cols
    s11_cols = list(range(len(s11_names)))  # 16 cols
    hvdc_ptha_cols = list(range(16)) + [17]  # 17 cols (fixes IR-91-S14-01)
    hvdc_cols = list(range(len(hvdc_names)))  # 18 cols

    # De-drifted regionally balanced S14-HVDC E2/E3 columns (fixes IR-91-S14-02 eastern-NV drift)
    e2_static_cols = list(range(24)) + [31, 33, 43, 44, 45, 46, 48]  # 31 cols
    e2_hvdc_cols = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 17]  # 15 invariant cols

    # 3. Rule 4: Single-Feature Leakage Canary Part A across all 89 Stage-1 features BEFORE any model fit
    canary_s1_cache = CACHE_DIR / "s14_canary_s1.json"
    if canary_s1_cache.is_file():
        s1_cached = json.loads(canary_s1_cache.read_text(encoding="utf-8"))
        stage1_canary_features = s1_cached["stage1_canary_features"]
        c_hvdc = {"features": s1_cached["c_hvdc_features"]}
    else:
        _log("Running Rule 4 Single-Feature Leakage Canary Part A across all 89 Stage-1 features (AUC <= 0.90)...")
        fold_deconf_map: dict[int, tuple[np.ndarray, list[str]]] = {}
        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            xd = HVDC.fit_fold_safe_deconfounded_residuals(X_static, footprint, footprint & (~excl))
            fold_deconf_map[f.fold_id] = (xd, list(HVDC.FOLD_DECONFOUND_NAMES))

        c_stat = EH.run_leakage_canary(
            X_static[:, hvdc_static_cols],
            [static_names[i] for i in hvdc_static_cols],
            folds,
            footprint,
            fold_specific_features=fold_deconf_map,
            subsample_step=4,
        )
        del fold_deconf_map
        gc.collect()
        c_s11 = EH.run_leakage_canary(X_s11, s11_names, folds, footprint, subsample_step=4)
        c_ptha = EH.run_leakage_canary(
            X_ptha[:, hvdc_ptha_cols],
            [ptha_names[i] for i in hvdc_ptha_cols],
            folds,
            footprint,
            subsample_step=4,
        )
        c_hvdc = EH.run_leakage_canary(X_hvdc, hvdc_names, folds, footprint, subsample_step=4)

        stage1_canary_features = {
            **c_stat["features"],
            **c_s11["features"],
            **c_ptha["features"],
            **c_hvdc["features"],
        }
        canary_s1_cache.write_text(
            json.dumps({
                "stage1_canary_features": stage1_canary_features,
                "c_hvdc_features": c_hvdc["features"],
            }) + "\n",
            encoding="utf-8",
        )
    flagged_s1 = [k for k, v in stage1_canary_features.items() if not v["pass"]]
    worst_s1 = max(stage1_canary_features.items(), key=lambda kv: kv[1]["max_fold_symmetric_auc"])
    _log(
        f"Stage-1 Leakage Canary PASS={len(flagged_s1) == 0} | "
        f"n_checked={len(stage1_canary_features)} | max_symmetric_auc={worst_s1[1]['max_fold_symmetric_auc']:.5f} "
        f"({worst_s1[0]})"
    )
    if flagged_s1:
        raise RuntimeError(f"RULE 4 STAGE-1 LEAKAGE CANARY FAILED: {flagged_s1}")

    # 4. Prepare structural crest surfaces & reproduce frozen #1 `S13-PTHA E3` OOF reference
    mhtr_edge, piedmont_mask = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    ptha_crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, footprint)
    hvdc_crest = HVDC.build_hvdc_structural_crest_surface(ptha_crest, X_hvdc, footprint)

    _log("Reproducing frozen current repo #1 `S13-PTHA E3` OOF folds for exact paired 5 km bootstrap...")
    s13_fold_dots: dict[int, np.ndarray] = {}
    for f in folds:
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        oof_dat = CACHE_DIR / f"s13_oof_e2_f{f.fold_id}.dat"
        oof_meta = CACHE_DIR / f"s13_oof_e2_f{f.fold_id}.json"
        if oof_dat.is_file() and oof_meta.is_file() and oof_dat.stat().st_size == n_fp * 4:
            s13_prob = np.zeros(footprint.shape, dtype=np.float32)
            s13_prob[footprint] = np.fromfile(oof_dat, dtype=np.float32)
            s13_cal = json.loads(oof_meta.read_text(encoding="utf-8"))
        else:
            s13_prob, s13_cal = PTHA.fit_and_predict_ptha_oof_fold(
                X_static=X_static,
                static_cols=s13_static_cols,
                static_names=static_names,
                X_s11=X_s11,
                s11_cols=s11_cols,
                s11_names=s11_names,
                X_ptha=X_ptha,
                ptha_cols=s13_ptha_cols,
                ptha_names=ptha_names,
                visible_faults=f.visible_faults,
                exclude_mask=excl,
                footprint=footprint,
                seed=1300 + 20 + f.fold_id,
            )
            s13_prob[footprint].astype(np.float32).tofile(oof_dat)
            oof_meta.write_text(json.dumps(s13_cal) + "\n", encoding="utf-8")

        s13_dots_f, _ = PTHA.dinkelbach_fold_independent_emit(
            s13_prob,
            ptha_crest,
            piedmont_mask,
            footprint=footprint,
            train_eligible_mask=fold_train_elig[f.fold_id],
            test_eligible_mask=fold_eligible[f.fold_id],
            pi_true=s13_cal["pi_vis_train"],
            pi_sample=s13_cal["pi_sample_weighted"],
            target_pool_dots=TARGET_POOL_DOTS,
            full_eligible_pixels=n_full_elig,
            min_spacing_px=2.50,
        )
        s13_fold_dots[f.fold_id] = s13_dots_f
        del s13_prob
        gc.collect()

    s13_ref_holdout = EH.score_pooled_holdout(s13_fold_dots, folds, footprint, n_boot=200, seed=133)
    s13_ref_tiles = _accumulate_fold_tiles(s13_fold_dots, folds, footprint)
    del s13_fold_dots, ptha_crest, mhtr_edge
    gc.collect()

    r0_sgmc = EH.score_off_catalogue_sgmc(r0_dots, sgmc_mask, cat_mask, footprint)
    _log(
        f"Verified `S13-PTHA E3` #1 reference: HOLDOUT-DTI = {s13_ref_holdout['holdout_dti']:.6f} "
        f"(CI {s13_ref_holdout['ci_95']}, n_withheld={s13_ref_holdout['n_withheld_positives']:,}) | "
        f"R0 SGMC = {r0_sgmc['dti']:.6f}"
    )

    exp_results: list[dict] = []
    oof_cal_cache: dict[str, dict[int, dict[str, float]]] = {}

    # =========================================================================
    # Experiment 1/3: `E1` (`H14-1` Hydrothermal Plume Back-Projection +
    # Global OLS Playa/Basin Deconfounding + Salem Tilt-Depth + Ruhl Swarm Stage-1)
    # =========================================================================
    n_feats_e1 = len(hvdc_static_cols) + len(s11_cols) + len(hvdc_ptha_cols) + len(hvdc_cols) + 2
    e1_frozen_json = CACHE_DIR / "s14_exp1_frozen_result.json"
    if e1_frozen_json.is_file():
        _log(f"--- Experiment 1/{MAX_EXPERIMENTS}: Loading frozen E1 ({e1_frozen_json.name}) ---")
        e1_frozen = json.loads(e1_frozen_json.read_text(encoding="utf-8"))
        e1_cal_map = {
            f.fold_id: json.loads((CACHE_DIR / f"s14_e1_meta_f{f.fold_id}.json").read_text(encoding="utf-8"))
            for f in folds
        }
        oof_cal_cache["E1"] = e1_cal_map
        _log(
            f"[E1 FROZEN] HOLDOUT-DTI = {e1_frozen['holdout']['holdout_dti']:.6f} "
            f"(95% CI {e1_frozen['holdout']['ci_95']}, delta vs S13-PTHA-E3 = "
            f"{e1_frozen['paired_vs_s13_ptha_e3']['delta']:+.6f})"
        )
        exp_results.append({
            "experiment_number": 1,
            "exp_id": "E1",
            "hypothesis_id": "H14-1",
            "title": (
                "Up-Gradient Hydrothermal Plume Back-Projection + Global OLS Playa/Basin Deconfounding + "
                "Salem Intrabasinal Tilt-Depth + Positive Ruhl Swarm Stage-1"
            ),
            "n_features": n_feats_e1,
            "emission_mode": "matched_ptha_fold_independent_dinkelbach",
            "fold_dinkelbach_allocation": e1_frozen["fold_dinkelbach_allocation"],
            "named_non_fault_mimic": (
                "Barren evaporite alkali playas (high B17), unfaulted reversed Tertiary lava lobes "
                "(B14-B01), and distal agricultural warm wells (plus IR-91-S14-02 eastern-NV global OLS shift)"
            ),
            "holdout": e1_frozen["holdout"],
            "paired_vs_s13_ptha_e3": e1_frozen["paired_vs_s13_ptha_e3"],
            "elapsed_seconds": 0.0,
        })
    else:
        if time.perf_counter() - t0 > MAX_BUDGET_SECONDS:
            raise RuntimeError("Rule 6 budget exceeded before E1!")
        te1 = time.perf_counter()
        _log(f"--- Experiment 1/{MAX_EXPERIMENTS}: E1 (H14-1 Hydrothermal & Deconfounded Stage-1, {n_feats_e1} features) ---")

        e1_cal_map = {}
        e1_fold_dots: dict[int, np.ndarray] = {}
        e1_alloc_meta: dict[str, dict] = {}

        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            raw_dat = CACHE_DIR / f"s14_e1_raw_f{f.fold_id}.dat"
            cal_dat = CACHE_DIR / f"s14_e1_cal_f{f.fold_id}.dat"
            meta_p = CACHE_DIR / f"s14_e1_meta_f{f.fold_id}.json"

            if raw_dat.is_file() and cal_dat.is_file() and meta_p.is_file() and raw_dat.stat().st_size == n_fp * 4:
                raw_f = np.zeros(footprint.shape, dtype=np.float32)
                raw_f[footprint] = np.fromfile(raw_dat, dtype=np.float32)
                cal_f = json.loads(meta_p.read_text(encoding="utf-8"))
            else:
                raw_f, cal_prob_f, cal_f = HVDC.fit_and_predict_hvdc_stage1(
                    X_static=X_static,
                    static_cols=hvdc_static_cols,
                    static_names=static_names,
                    X_s11=X_s11,
                    s11_cols=s11_cols,
                    s11_names=s11_names,
                    X_ptha=X_ptha,
                    ptha_cols=hvdc_ptha_cols,
                    ptha_names=ptha_names,
                    X_hvdc=X_hvdc,
                    hvdc_cols=hvdc_cols,
                    hvdc_names=hvdc_names,
                    visible_faults=f.visible_faults,
                    exclude_mask=excl,
                    footprint=footprint,
                    include_global_ols_deconf=True,
                    seed=1410 + f.fold_id,
                )
                raw_f[footprint].astype(np.float32).tofile(raw_dat)
                cal_prob_f[footprint].astype(np.float32).tofile(cal_dat)
                meta_p.write_text(json.dumps(cal_f) + "\n", encoding="utf-8")
                del cal_prob_f

            e1_cal_map[f.fold_id] = cal_f
            dots_f, alloc_m = PTHA.dinkelbach_fold_independent_emit(
                raw_f,
                hvdc_crest,
                piedmont_mask,
                footprint=footprint,
                train_eligible_mask=fold_train_elig[f.fold_id],
                test_eligible_mask=fold_eligible[f.fold_id],
                pi_true=cal_f["pi_vis_train"],
                pi_sample=cal_f["pi_sample_weighted"],
                target_pool_dots=TARGET_POOL_DOTS,
                full_eligible_pixels=n_full_elig,
                min_spacing_px=2.50,
            )
            e1_fold_dots[f.fold_id] = dots_f
            e1_alloc_meta[f.name] = alloc_m
            _log(
                f"  [E1 {f.name}] tau_train={alloc_m['tau_dinkelbach_train']:.6f} -> "
                f"emitted {alloc_m['n_test_emitted_dots']:,} dots"
            )
            del raw_f
            gc.collect()

        e1_hold = EH.score_pooled_holdout(e1_fold_dots, folds, footprint, n_boot=200, seed=141)
        e1_tiles = _accumulate_fold_tiles(e1_fold_dots, folds, footprint)
        e1_paired_s13 = compute_aligned_paired_bootstrap(
            e1_tiles,
            s13_ref_tiles,
            cand_pooled_dti=e1_hold["holdout_dti"],
            base_pooled_dti=s13_ref_holdout["holdout_dti"],
        )
        del e1_fold_dots, e1_tiles
        gc.collect()

        el1 = time.perf_counter() - te1
        _log(
            f"[E1] HOLDOUT-DTI = {e1_hold['holdout_dti']:.6f} "
            f"(95% CI {e1_hold['ci_95']}, delta vs S13-PTHA-E3 = {e1_paired_s13['delta']:+.6f}, "
            f"paired 95% CI {e1_paired_s13['ci95']}, P(>0)={e1_paired_s13['prob_positive']:.3f}) [{el1:.1f}s]"
        )
        oof_cal_cache["E1"] = e1_cal_map
        exp_results.append({
            "experiment_number": 1,
            "exp_id": "E1",
            "hypothesis_id": "H14-1",
            "title": (
                "Up-Gradient Hydrothermal Plume Back-Projection + Playa/Basin Deconfounding + "
                "Salem Intrabasinal Tilt-Depth + Positive Ruhl Swarm Excess Stage-1"
            ),
            "n_features": n_feats_e1,
            "emission_mode": "matched_ptha_fold_independent_dinkelbach",
            "fold_dinkelbach_allocation": e1_alloc_meta,
            "named_non_fault_mimic": (
                "Barren evaporite alkali playas (high B17), unfaulted reversed Tertiary lava lobes "
                "(B14-B01), and distal agricultural warm wells"
            ),
            "holdout": e1_hold,
            "paired_vs_s13_ptha_e3": e1_paired_s13,
            "elapsed_seconds": round(el1, 2),
        })

    # =========================================================================
    # Experiment 2/3: `E2` (Regionally Balanced De-Drifted `H14-1 + H14-2`
    # Leak-Free 6-Pair En-Echelon Relay-Ramp & Alluvial-Wash Auto-Context)
    # =========================================================================
    if time.perf_counter() - t0 > MAX_BUDGET_SECONDS:
        raise RuntimeError("Rule 6 budget exceeded before E2!")
    te2 = time.perf_counter()
    n_feats_e2 = (
        len(e2_static_cols) + len(s11_cols) + len(hvdc_ptha_cols) + len(e2_hvdc_cols) + len(HVDC.STAGE2_CONTEXT_NAMES)
    )
    _log(
        f"--- Experiment 2/{MAX_EXPERIMENTS}: E2 (Regionally-Balanced H14-1 + H14-2 Leak-Free 6-Pair Relay-Ramp "
        f"& Wash-Bridge Auto-Context, {n_feats_e2} features) ---"
    )

    # Step 2a: Fit the 6 unordered 2-quadrant Stage-1 pairs M_{a,b} (`C(4,2) = 6`)
    pair_cal_probs: dict[tuple[int, int], np.ndarray] = {}
    for qa, qb in itertools.combinations(range(4), 2):
        pair_dat = CACHE_DIR / f"s14_v2_pair_cal_{qa}_{qb}.dat"
        if pair_dat.is_file() and pair_dat.stat().st_size == n_fp * 4:
            cp = np.zeros(footprint.shape, dtype=np.float32)
            cp[footprint] = np.fromfile(pair_dat, dtype=np.float32)
            pair_cal_probs[(qa, qb)] = cp
            continue

        held_quads = [q for q in range(4) if q not in (qa, qb)]
        excl_ab = np.zeros_like(footprint, dtype=bool)
        vis_ab = cat_mask.copy()
        pred_ab = np.zeros_like(footprint, dtype=bool)
        for hq in held_quads:
            fh = folds[hq]
            excl_ab |= fh.region_mask | fh.withheld_faults | fh.buffer_mask
            vis_ab &= (~fh.withheld_faults) & (~fh.buffer_mask)
            pred_ab |= fh.region_mask
        vis_ab &= (folds[qa].region_mask | folds[qb].region_mask) & (~excl_ab)
        pred_ab &= footprint

        _, cp, _ = HVDC.fit_and_predict_hvdc_stage1(
            X_static=X_static,
            static_cols=e2_static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_cols=s11_cols,
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_cols=hvdc_ptha_cols,
            ptha_names=ptha_names,
            X_hvdc=X_hvdc,
            hvdc_cols=e2_hvdc_cols,
            hvdc_names=hvdc_names,
            visible_faults=vis_ab,
            exclude_mask=excl_ab,
            footprint=footprint,
            predict_mask_2d=pred_ab,
            include_global_ols_deconf=False,
            seed=1420 + qa * 10 + qb,
        )
        cp[footprint].astype(np.float32).tofile(pair_dat)
        pair_cal_probs[(qa, qb)] = cp
        gc.collect()
    _log("  6-pair out-of-sample inner Stage-1 calibrated posteriors ready.")

    # Step 2a-outer: Fit the 4 outer test-canvas Stage-1 posteriors cleanly on `excl_k & footprint`
    for f in folds:
        k = f.fold_id
        outer_cal_dat = CACHE_DIR / f"s14_v2_outer_cal_f{k}.dat"
        if outer_cal_dat.is_file() and outer_cal_dat.stat().st_size == n_fp * 4:
            continue
        excl_k = f.region_mask | f.withheld_faults | f.buffer_mask
        _, cp_out, _ = HVDC.fit_and_predict_hvdc_stage1(
            X_static=X_static,
            static_cols=e2_static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_cols=s11_cols,
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_cols=hvdc_ptha_cols,
            ptha_names=ptha_names,
            X_hvdc=X_hvdc,
            hvdc_cols=e2_hvdc_cols,
            hvdc_names=hvdc_names,
            visible_faults=f.visible_faults,
            exclude_mask=excl_k,
            footprint=footprint,
            predict_mask_2d=(excl_k & footprint),
            include_global_ols_deconf=False,
            seed=1435 + k,
        )
        cp_out[footprint].astype(np.float32).tofile(outer_cal_dat)
        del cp_out
        gc.collect()
    _log("  4 outer test-canvas Stage-1 calibrated posteriors ready.")

    if "--stage2-prep" in sys.argv:
        _log("Completed `--stage2-prep` cleanly.")
        return 0

    # Step 2b: Construct leak-free Stage-2 training & test context per outer fold & run Rule 4 Canary Part B
    e2_ctx_test_for_canary: dict[int, tuple[np.ndarray, list[str]]] = {}
    e2_ctx_train_cache: dict[int, np.ndarray] = {}
    n_ctx_cols = len(HVDC.STAGE2_CONTEXT_NAMES)
    temp_ctx_paths: list[Path] = []
    canary_s2_cache = CACHE_DIR / "s14_canary_s2.json"
    all_e2_cached = all(
        (CACHE_DIR / f"s14_e2_raw_f{f.fold_id}.dat").is_file()
        and (CACHE_DIR / f"s14_e2_meta_f{f.fold_id}.json").is_file()
        for f in folds
    )

    if all_e2_cached and canary_s2_cache.is_file():
        canary_report = json.loads(canary_s2_cache.read_text(encoding="utf-8"))
        del pair_cal_probs
        gc.collect()
    else:
        for f in folds:
            k = f.fold_id
            excl_k = f.region_mask | f.withheld_faults | f.buffer_mask
            tr_mm_path = CACHE_DIR / f"s14_v2_ctx_tr_f{k}.dat"
            te_mm_path = CACHE_DIR / f"s14_v2_ctx_te_f{k}.dat"
            temp_ctx_paths.extend([tr_mm_path, te_mm_path])

            if (
                tr_mm_path.is_file()
                and te_mm_path.is_file()
                and tr_mm_path.stat().st_size == n_fp * n_ctx_cols * 4
                and te_mm_path.stat().st_size == n_fp * n_ctx_cols * 4
            ):
                e2_ctx_train_cache[k] = np.memmap(tr_mm_path, dtype="float32", mode="r", shape=(n_fp, n_ctx_cols))
                mm_te = np.memmap(te_mm_path, dtype="float32", mode="r", shape=(n_fp, n_ctx_cols))
                e2_ctx_test_for_canary[k] = (mm_te, list(HVDC.STAGE2_CONTEXT_NAMES))
                continue

            # Training Stage-1 canvas: every training quadrant q != k predicted strictly by M_{other two}!
            s1_train_canvas = np.zeros(footprint.shape, dtype=np.float32)
            for q in range(4):
                if q == k:
                    continue
                rem = tuple(sorted(r for r in range(4) if r not in (k, q)))
                s1_train_canvas[folds[q].region_mask] = pair_cal_probs[rem][folds[q].region_mask]
            s1_train_canvas[excl_k] = 0.0

            # Test Stage-1 canvas: training quadrants get out-of-sample M_{other two}, test domain gets outer M_{-k}!
            out_cal_k = np.zeros(footprint.shape, dtype=np.float32)
            out_cal_k[footprint] = np.fromfile(CACHE_DIR / f"s14_v2_outer_cal_f{k}.dat", dtype=np.float32)
            s1_test_canvas = s1_train_canvas.copy()
            s1_test_canvas[excl_k] = out_cal_k[excl_k]
            del out_cal_k

            ctx_tr = HVDC.compute_hvdc_relay_wash_context(s1_train_canvas, footprint)
            mm_tr_w = np.memmap(tr_mm_path, dtype="float32", mode="w+", shape=(n_fp, n_ctx_cols))
            mm_tr_w[:] = ctx_tr
            mm_tr_w.flush()
            del ctx_tr, mm_tr_w

            ctx_te = HVDC.compute_hvdc_relay_wash_context(s1_test_canvas, footprint)
            mm_te_w = np.memmap(te_mm_path, dtype="float32", mode="w+", shape=(n_fp, n_ctx_cols))
            mm_te_w[:] = ctx_te
            mm_te_w.flush()
            del ctx_te, mm_te_w, s1_train_canvas, s1_test_canvas
            gc.collect()

            e2_ctx_train_cache[k] = np.memmap(tr_mm_path, dtype="float32", mode="r", shape=(n_fp, n_ctx_cols))
            mm_te = np.memmap(te_mm_path, dtype="float32", mode="r", shape=(n_fp, n_ctx_cols))
            e2_ctx_test_for_canary[k] = (mm_te, list(HVDC.STAGE2_CONTEXT_NAMES))

        del pair_cal_probs
        gc.collect()

        _log("Running Rule 4 Single-Feature Leakage Canary Part B across all 12 Stage-2 Auto-Context features...")
        c_stage2 = EH.run_leakage_canary(
            np.zeros((n_fp, 0), dtype=np.float32),
            [],
            folds,
            footprint,
            fold_specific_features=e2_ctx_test_for_canary,
            subsample_step=4,
        )
        all_canary_features = {**stage1_canary_features, **c_stage2["features"]}
        flagged_all = [k for k, v in all_canary_features.items() if not v["pass"]]
        worst_all = max(all_canary_features.items(), key=lambda kv: kv[1]["max_fold_symmetric_auc"])
        canary_report = {
            "evaluator_version": EH.EVALUATOR_VERSION,
            "max_allowed_auc": EH.MAX_LEAKAGE_AUC,
            "n_features_checked": len(all_canary_features),
            "canary_pass": len(flagged_all) == 0,
            "worst_feature": worst_all[0],
            "worst_symmetric_auc": worst_all[1]["max_fold_symmetric_auc"],
            "flagged_features": flagged_all,
            "hvdc_stage1_features": c_hvdc["features"],
            "hvdc_stage2_context_features": c_stage2["features"],
        }
        canary_s2_cache.write_text(json.dumps(canary_report) + "\n", encoding="utf-8")
    _log(
        f"Combined 101-Feature Leakage Canary PASS={canary_report['canary_pass']} | "
        f"max_symmetric_auc={canary_report['worst_symmetric_auc']:.5f} ({canary_report['worst_feature']})"
    )
    if not canary_report["canary_pass"]:
        raise RuntimeError(f"RULE 4 STAGE-2 LEAKAGE CANARY FAILED: {flagged_all}")

    # Step 2c: Fit Stage-2 Relay-Ramp & Wash-Bridge Auto-Context ensemble per fold
    e2_cal_map: dict[int, dict[str, float]] = {}
    e2_fold_dots: dict[int, np.ndarray] = {}
    e2_alloc_meta: dict[str, dict] = {}

    for f in folds:
        k = f.fold_id
        excl_k = f.region_mask | f.withheld_faults | f.buffer_mask
        raw2_dat = CACHE_DIR / f"s14_e2_raw_f{k}.dat"
        meta2_p = CACHE_DIR / f"s14_e2_meta_f{k}.json"

        if raw2_dat.is_file() and meta2_p.is_file() and raw2_dat.stat().st_size == n_fp * 4:
            raw2_f = np.zeros(footprint.shape, dtype=np.float32)
            raw2_f[footprint] = np.fromfile(raw2_dat, dtype=np.float32)
            cal2_f = json.loads(meta2_p.read_text(encoding="utf-8"))
        else:
            raw2_f, _, cal2_f = HVDC.fit_and_predict_hvdc_stage2(
                X_static=X_static,
                static_cols=e2_static_cols,
                static_names=static_names,
                X_s11=X_s11,
                s11_cols=s11_cols,
                s11_names=s11_names,
                X_ptha=X_ptha,
                ptha_cols=hvdc_ptha_cols,
                ptha_names=ptha_names,
                X_hvdc=X_hvdc,
                hvdc_cols=e2_hvdc_cols,
                hvdc_names=hvdc_names,
                X_ctx_train=e2_ctx_train_cache[k],
                X_ctx_pred=e2_ctx_test_for_canary[k][0],
                visible_faults=f.visible_faults,
                exclude_mask=excl_k,
                footprint=footprint,
                include_global_ols_deconf=False,
                seed=1450 + k,
            )
            raw2_f[footprint].astype(np.float32).tofile(raw2_dat)
            meta2_p.write_text(json.dumps(cal2_f) + "\n", encoding="utf-8")

        e2_cal_map[k] = cal2_f
        dots2_f, alloc2_m = PTHA.dinkelbach_fold_independent_emit(
            raw2_f,
            hvdc_crest,
            piedmont_mask,
            footprint=footprint,
            train_eligible_mask=fold_train_elig[k],
            test_eligible_mask=fold_eligible[k],
            pi_true=cal2_f["pi_vis_train"],
            pi_sample=cal2_f["pi_sample_weighted"],
            target_pool_dots=TARGET_POOL_DOTS,
            full_eligible_pixels=n_full_elig,
            min_spacing_px=2.50,
        )
        e2_fold_dots[k] = dots2_f
        e2_alloc_meta[f.name] = alloc2_m
        _log(
            f"  [E2 {f.name}] tau_train={alloc2_m['tau_dinkelbach_train']:.6f} -> "
            f"emitted {alloc2_m['n_test_emitted_dots']:,} dots"
        )
        del raw2_f
        gc.collect()

    del e2_ctx_train_cache, e2_ctx_test_for_canary
    gc.collect()
    for p_tmp in temp_ctx_paths:
        if p_tmp.is_file():
            p_tmp.unlink()

    e2_hold = EH.score_pooled_holdout(e2_fold_dots, folds, footprint, n_boot=200, seed=142)
    e2_tiles = _accumulate_fold_tiles(e2_fold_dots, folds, footprint)
    e2_paired_s13 = compute_aligned_paired_bootstrap(
        e2_tiles,
        s13_ref_tiles,
        cand_pooled_dti=e2_hold["holdout_dti"],
        base_pooled_dti=s13_ref_holdout["holdout_dti"],
    )
    del e2_fold_dots, e2_tiles
    gc.collect()

    el2 = time.perf_counter() - te2
    _log(
        f"[E2] HOLDOUT-DTI = {e2_hold['holdout_dti']:.6f} "
        f"(95% CI {e2_hold['ci_95']}, delta vs S13-PTHA-E3 = {e2_paired_s13['delta']:+.6f}, "
        f"paired 95% CI {e2_paired_s13['ci95']}, P(>0)={e2_paired_s13['prob_positive']:.3f}) [{el2:.1f}s]"
    )
    oof_cal_cache["E2"] = e2_cal_map
    exp_results.append({
        "experiment_number": 2,
        "exp_id": "E2",
        "hypothesis_id": "H14-1 + H14-2",
        "title": (
            "H14-1 + Leak-Free 6-Pair Two-Stage En-Echelon Relay-Ramp & "
            "Collinear Alluvial-Wash Bridge Structural Auto-Context"
        ),
        "n_features": n_feats_e2,
        "emission_mode": "matched_ptha_fold_independent_dinkelbach",
        "fold_dinkelbach_allocation": e2_alloc_meta,
        "named_non_fault_mimic": (
            "Braided alluvial fan distributary channels and parallel unfaulted volcanic dike swarms"
        ),
        "holdout": e2_hold,
        "paired_vs_s13_ptha_e3": e2_paired_s13,
        "elapsed_seconds": round(el2, 2),
    })

    # =========================================================================
    # Experiment 3/3: `E3` (`H14-3` Continuous Steger Gradient-Normal Crest +
    # Self-Credit-Exact `M`-Term Dinkelbach Fractional Programming)
    # =========================================================================
    if time.perf_counter() - t0 > MAX_BUDGET_SECONDS:
        raise RuntimeError("Rule 6 budget exceeded before E3!")
    te3 = time.perf_counter()
    base_eid = "E2" if exp_results[1]["holdout"]["holdout_dti"] >= exp_results[0]["holdout"]["holdout_dti"] else "E1"
    base_exp = exp_results[1] if base_eid == "E2" else exp_results[0]
    _log(
        f"--- Experiment 3/{MAX_EXPERIMENTS}: E3 (H14-3 Continuous Steger Crest + "
        f"Self-Credit-Exact M-Term Dinkelbach on {base_eid} OOF surfaces) ---"
    )

    e3_fold_dots: dict[int, np.ndarray] = {}
    e3_alloc_meta: dict[str, dict] = {}
    for f in folds:
        k = f.fold_id
        raw_p = CACHE_DIR / f"s14_{base_eid.lower()}_raw_f{k}.dat"
        prob_f = np.zeros(footprint.shape, dtype=np.float32)
        prob_f[footprint] = np.fromfile(raw_p, dtype=np.float32)
        cal_f = oof_cal_cache[base_eid][k]

        dots3_f, alloc3_m = HVDC.hvdc_steger_dinkelbach_fold_emit(
            prob_f,
            hvdc_crest,
            piedmont_mask,
            footprint=footprint,
            train_eligible_mask=fold_train_elig[k],
            test_eligible_mask=fold_eligible[k],
            pi_true=cal_f["pi_vis_train"],
            pi_sample=cal_f["pi_sample_weighted"],
            target_pool_dots=46_500,
            full_eligible_pixels=n_full_elig,
            min_spacing_px=2.50,
        )
        e3_fold_dots[k] = dots3_f
        e3_alloc_meta[f.name] = alloc3_m
        _log(
            f"  [E3 {f.name}] tau_ratio={alloc3_m['tau_dinkelbach_ratio_train']:.6f}, "
            f"mean_m_hat={alloc3_m['test_mean_self_credit_m_hat']:.4f} -> "
            f"emitted {alloc3_m['n_test_emitted_dots']:,} dots"
        )
        del prob_f
        gc.collect()

    e3_hold = EH.score_pooled_holdout(e3_fold_dots, folds, footprint, n_boot=200, seed=143)
    e3_tiles = _accumulate_fold_tiles(e3_fold_dots, folds, footprint)
    e3_paired_s13 = compute_aligned_paired_bootstrap(
        e3_tiles,
        s13_ref_tiles,
        cand_pooled_dti=e3_hold["holdout_dti"],
        base_pooled_dti=s13_ref_holdout["holdout_dti"],
    )
    del e3_fold_dots, e3_tiles
    gc.collect()

    el3 = time.perf_counter() - te3
    _log(
        f"[E3] HOLDOUT-DTI = {e3_hold['holdout_dti']:.6f} "
        f"(95% CI {e3_hold['ci_95']}, delta vs S13-PTHA-E3 = {e3_paired_s13['delta']:+.6f}, "
        f"paired 95% CI {e3_paired_s13['ci95']}, P(>0)={e3_paired_s13['prob_positive']:.3f}) [{el3:.1f}s]"
    )
    exp_results.append({
        "experiment_number": 3,
        "exp_id": "E3",
        "hypothesis_id": f"{base_exp['hypothesis_id']} + H14-3",
        "title": (
            f"{base_exp['title']} + Continuous Steger Gradient-Normal Crest & "
            "Self-Credit-Exact (M-Term) Dinkelbach Fractional Programming"
        ),
        "n_features": base_exp["n_features"],
        "base_oof_experiment": base_eid,
        "emission_mode": "continuous_steger_self_credit_dinkelbach",
        "fold_dinkelbach_allocation": e3_alloc_meta,
        "named_non_fault_mimic": (
            "Off-center multi-row mountain-scarp flanks and barren evaporite playa interiors"
        ),
        "holdout": e3_hold,
        "paired_vs_s13_ptha_e3": e3_paired_s13,
        "elapsed_seconds": round(el3, 2),
    })

    # 6. Select Holdout Winner among `{E1, E2, E3}` and fit full-map submission model
    win_exp = max(exp_results, key=lambda r: r["holdout"]["holdout_dti"])
    win_id = win_exp["exp_id"]
    uses_stage2 = (win_id == "E2") or (win_id == "E3" and win_exp.get("base_oof_experiment") == "E2")
    _log(
        f"Selected Holdout Winner: {win_id} ({win_exp['hypothesis_id']}) | "
        f"HOLDOUT-DTI = {win_exp['holdout']['holdout_dti']:.6f} "
        f"(delta vs S13-PTHA-E3 = {win_exp['paired_vs_s13_ptha_e3']['delta']:+.6f}, "
        f"95% CI {win_exp['paired_vs_s13_ptha_e3']['ci95']})"
    )

    if "--oof-only" in sys.argv:
        _log("Completed `--oof-only` E1/E2/E3 evaluation stage cleanly.")
        return 0

    full_excl = ~footprint
    full_dat = CACHE_DIR / f"s14_full_{'s2' if uses_stage2 else 's1'}_raw.dat"
    full_meta = CACHE_DIR / f"s14_full_{'s2' if uses_stage2 else 's1'}_meta.json"

    if full_dat.is_file() and full_meta.is_file() and full_dat.stat().st_size == n_fp * 4:
        full_prob = np.zeros(footprint.shape, dtype=np.float32)
        full_prob[footprint] = np.fromfile(full_dat, dtype=np.float32)
        full_cal = json.loads(full_meta.read_text(encoding="utf-8"))
    elif not uses_stage2:
        _log("Fitting full-map Stage-1 `S14-HVDC` ensemble on complete training catalogue...")
        full_prob, _, full_cal = HVDC.fit_and_predict_hvdc_stage1(
            X_static=X_static,
            static_cols=hvdc_static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_cols=s11_cols,
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_cols=hvdc_ptha_cols,
            ptha_names=ptha_names,
            X_hvdc=X_hvdc,
            hvdc_cols=hvdc_cols,
            hvdc_names=hvdc_names,
            visible_faults=cat_mask,
            exclude_mask=full_excl,
            footprint=footprint,
            seed=1491,
        )
        full_prob[footprint].astype(np.float32).tofile(full_dat)
        full_meta.write_text(json.dumps(full_cal) + "\n", encoding="utf-8")
    else:
        _log("Building full-map 4-quadrant out-of-sample Stage-1 mosaic & fitting full-map Stage-2 `S14-HVDC`...")
        full_s1_oof = np.zeros(footprint.shape, dtype=np.float32)
        for f in folds:
            q = f.fold_id
            unbuf_dat = CACHE_DIR / f"s14_full_unbuf_s1_cal_q{q}.dat"
            if unbuf_dat.is_file() and unbuf_dat.stat().st_size == n_fp * 4:
                cp_q = np.zeros(footprint.shape, dtype=np.float32)
                cp_q[footprint] = np.fromfile(unbuf_dat, dtype=np.float32)
            else:
                excl_q = f.region_mask | (~footprint)
                vis_q = cat_mask & (~f.region_mask)
                _, cp_q, _ = HVDC.fit_and_predict_hvdc_stage1(
                    X_static=X_static,
                    static_cols=e2_static_cols,
                    static_names=static_names,
                    X_s11=X_s11,
                    s11_cols=s11_cols,
                    s11_names=s11_names,
                    X_ptha=X_ptha,
                    ptha_cols=hvdc_ptha_cols,
                    ptha_names=ptha_names,
                    X_hvdc=X_hvdc,
                    hvdc_cols=e2_hvdc_cols,
                    hvdc_names=hvdc_names,
                    visible_faults=vis_q,
                    exclude_mask=excl_q,
                    footprint=footprint,
                    predict_mask_2d=(f.region_mask & footprint),
                    include_global_ols_deconf=False,
                    seed=1480 + q,
                )
                cp_q[footprint].astype(np.float32).tofile(unbuf_dat)
            full_s1_oof[f.region_mask] = cp_q[f.region_mask]
            del cp_q
            gc.collect()

        X_ctx_full = HVDC.compute_hvdc_relay_wash_context(full_s1_oof, footprint)
        del full_s1_oof
        gc.collect()

        full_prob, _, full_cal = HVDC.fit_and_predict_hvdc_stage2(
            X_static=X_static,
            static_cols=e2_static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_cols=s11_cols,
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_cols=hvdc_ptha_cols,
            ptha_names=ptha_names,
            X_hvdc=X_hvdc,
            hvdc_cols=e2_hvdc_cols,
            hvdc_names=hvdc_names,
            X_ctx_train=X_ctx_full,
            visible_faults=cat_mask,
            exclude_mask=full_excl,
            footprint=footprint,
            include_global_ols_deconf=False,
            seed=1492,
        )
        del X_ctx_full
        gc.collect()
        full_prob[footprint].astype(np.float32).tofile(full_dat)
        full_meta.write_text(json.dumps(full_cal) + "\n", encoding="utf-8")

    # Scale full-map Dinkelbach dot budget directly from winning experiment's OOF density
    oof_dots_sum = sum(v["n_test_emitted_dots"] for v in win_exp["fold_dinkelbach_allocation"].values())
    oof_elig_sum = sum(int(fold_eligible[f.fold_id].sum()) for f in folds)
    full_target_dots = int(round(oof_dots_sum * n_full_elig / max(oof_elig_sum, 1)))
    full_target_dots = max(36_000, min(50_000, full_target_dots))

    if win_id == "E3":
        full_dots, full_last_metric, full_mean_m, full_w_surf = HVDC.hvdc_steger_dinkelbach_full_map_emit(
            full_prob,
            hvdc_crest,
            piedmont_mask,
            footprint=footprint,
            full_eligible_mask=full_eligible,
            pi_true=full_cal["pi_vis_train"],
            pi_sample=full_cal["pi_sample_weighted"],
            n_dots=full_target_dots,
            min_spacing_px=2.50,
        )
    else:
        full_dots, full_last_metric = PTHA.dinkelbach_full_map_emit(
            full_prob,
            hvdc_crest,
            piedmont_mask,
            footprint=footprint,
            full_eligible_mask=full_eligible,
            pi_true=full_cal["pi_vis_train"],
            pi_sample=full_cal["pi_sample_weighted"],
            n_dots=full_target_dots,
            min_spacing_px=2.50,
        )
        full_mean_m = 0.0
        full_w_surf, _, _ = PTHA.build_dinkelbach_expected_intensity(
            full_prob,
            hvdc_crest,
            piedmont_mask,
            footprint,
            calibration_mask=full_eligible,
            pi_true=full_cal["pi_vis_train"],
            pi_sample=full_cal["pi_sample_weighted"],
        )

    sgmc_res = EH.score_off_catalogue_sgmc(full_dots, sgmc_mask, cat_mask, footprint)
    _log(
        f"Full-map `{win_id}` emitted {int((full_dots > 0).sum()):,} binary {{0,1}} dots "
        f"(last_metric={full_last_metric:.6f}, mean_m_hat={full_mean_m:.4f}) | "
        f"Blind USGS SGMC DTI = {sgmc_res['dti']:.6f} "
        f"(delta vs R0 = {sgmc_res['dti'] - r0_sgmc['dti']:+.6f}, "
        f"delta vs S13-PTHA = {sgmc_res['dti'] - 0.100815:+.6f})"
    )

    # 7. Rule 1 Uniqueness Check across all 5 Scopes (including restored `data/retracted_geod/`)
    scopes = _collect_comparison_scopes()
    uniq_canonical = _check_uniqueness_fast(full_w_surf[footprint], full_dots, footprint, scopes["canonical_registry"])
    uniq_ext_dotted = _check_uniqueness_fast(
        full_w_surf[footprint], full_dots, footprint, scopes["external_real_rasters"], max_pos_filter=65_000
    )
    uniq_ext_all_real = _check_uniqueness_fast(full_w_surf[footprint], full_dots, footprint, scopes["external_real_rasters"])
    uniq_siblings = _check_uniqueness_fast(full_w_surf[footprint], full_dots, footprint, scopes["in_repo_siblings"])
    uniq_universal = _check_uniqueness_fast(full_w_surf[footprint], full_dots, footprint, scopes["universal_all_files"])

    _log(
        f"Uniqueness Canonical `data/registry/` (n={uniq_canonical['n_checked']}): PASS={uniq_canonical['pass']} | "
        f"max |rho|={uniq_canonical['max_abs_surface_spearman']:.4f}, "
        f"max 3px overlap={uniq_canonical['max_3px_dot_overlap']:.4f} ({uniq_canonical['dots_closest_raster']})"
    )
    _log(
        f"Uniqueness External Dotted Fleet (<65k pos, n={uniq_ext_dotted['n_checked']}): PASS={uniq_ext_dotted['pass']} | "
        f"max |rho|={uniq_ext_dotted['max_abs_surface_spearman']:.4f}, "
        f"max 3px overlap={uniq_ext_dotted['max_3px_dot_overlap']:.4f} ({uniq_ext_dotted['dots_closest_raster']})"
    )
    _log(
        f"Uniqueness External All Non-Lattice (n={uniq_ext_all_real['n_checked']}): "
        f"PASS={uniq_ext_all_real['pass']} | max 3px overlap={uniq_ext_all_real['max_3px_dot_overlap']:.4f} "
        f"({uniq_ext_all_real['dots_closest_raster']})"
    )
    _log(
        f"Uniqueness In-Repo Unsubmitted Siblings (n={uniq_siblings['n_checked']}): PASS={uniq_siblings['pass']} | "
        f"max 3px overlap={uniq_siblings['max_3px_dot_overlap']:.4f} ({uniq_siblings['dots_closest_raster']})"
    )
    _log(
        f"Uniqueness Universal All-File (n={uniq_universal['n_checked']}): "
        f"PASS={uniq_universal['pass']} | max 3px overlap={uniq_universal['max_3px_dot_overlap']:.4f} "
        f"({uniq_universal['dots_closest_raster']})"
    )

    # 8. Write & Validate `[0, 1]` Submission Bundle via shared `scripts/submission_writer.py`
    date_tag = "20261024T223000Z"
    stem_prefix = f"gems91-s14-hvdc-{win_id.lower()}"
    audit = SW.write_validated_submission_bundle(
        full_dots,
        stem_prefix=stem_prefix,
        date_tag=date_tag,
        template_path=TEMPLATE_TIF,
        catalogue_path=CATALOGUE_TIF,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        parent_compare_path=R0_ZEROS_TIF,
        releases_dir=RELEASES_DIR,
        downloads_dir=DOWNLOADS_DIR,
        floor_px=3.0,
        bundle_js_filename="s14_submission_bundle.js",
    )

    cand_id = audit["candidate_id"]
    rel_zeros = Path(audit["primary_zeros_tif"]["path"])
    dl_zeros = DOWNLOADS_DIR / rel_zeros.name
    shutil.copy2(rel_zeros, dl_zeros)
    assert IO.sha256_file(dl_zeros) == audit["primary_zeros_tif"]["sha256"]

    aux_audit = DOWNLOADS_DIR / f"{cand_id}-audit.json"
    if aux_audit.is_file():
        aux_audit.unlink()

    beats_s13 = (
        win_exp["holdout"]["holdout_dti"] > s13_ref_holdout["holdout_dti"]
        and win_exp["paired_vs_s13_ptha_e3"]["ci95"][0] > 0.0
    )
    external_dotted_unique = bool(uniq_canonical["pass"] and uniq_ext_dotted["pass"])
    elapsed_total = round(time.perf_counter() - t0, 2)

    sub_name = f"GEMS91-S14-HVDC-{win_id}-{audit['dots']['dot_set_digest'][:8]}"
    sub_note = (
        f"S14-HVDC {win_id}: HydroPlume+Salem+Swarm+RelayWashCtx+Dink; "
        f"HOLDOUT-DTI={win_exp['holdout']['holdout_dti']:.4f}; {audit['dots']['n_dots']} dots"
    )
    assert len(sub_note) <= 140, f"note too long ({len(sub_note)})"

    run_card_s14 = {
        "schema_version": "gems91.s14_hvdc.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/08009ce4-gemsdoe91",
        "preregistration": {
            "path": "docs/HYPOTHESES_S14.md",
            "sha256": prereg_sha256,
        },
        "lane": {
            "id": f"S14-HVDC-{win_id}",
            "assigned": False,
            "provisional_name": (
                "Up-Gradient Hydrothermal Plume Back-Projection + Local Basin/Playa Deconfounding + "
                "Salem Tilt-Depth + Ruhl Swarm Excess + Leak-Free En-Echelon Relay-Ramp "
                "Auto-Context + Fold-Independent Dinkelbach Allocation"
            ),
            "note": (
                "Prompt references 'the single method paragraph below' without supplying an "
                "external selector-assigned paragraph (IR-91-S12-01); lane self-declared and "
                "frozen in docs/HYPOTHESES_S14.md prior to any holdout run."
            ),
        },
        "hypothesis": win_exp["title"],
        "hypothesis_id": win_exp["hypothesis_id"],
        "physical_mechanism": (
            "Fixes the Band 10 Dependent Earthquake Swarm Density sign-inversion in S13-PTHA "
            "(IR-91-S14-01) and eastern-Nevada global-OLS covariate drift (IR-91-S14-02), "
            "back-projects enthalpy-weighted GDR thermal plumes 0.6-3.2 km upslope (+grad G_7(B12)) "
            "from basin-floor discharge wells onto concealed subsurface gravity/magnetic steps "
            "(dist_known_fault_px strictly banned), computes 3 km local high-pass playa/basin "
            "conductivity and gravity step contrasts plus Salem (2007) magnetic tilt-depth relative "
            "to Band 15 basement depth and GeoDAWN draped magnetic contacts, integrates a leak-free "
            "6-pair inner-OOF Stage-2 En-Echelon Relay-Ramp & Alluvial-Wash Bridge Structural "
            "Auto-Context network (91 features), and allocates binary {0,1} 300m-kernel dots via "
            "fold-independent Dinkelbach fractional programming."
        ),
        "named_non_fault_mimic_process": (
            "Barren closed-basin evaporite alkali playas (high B17), unfaulted reversed-polarity "
            "Tertiary lava lobes, distal agricultural warm wells, braided alluvial fan channels, "
            "and erosional range-front canyon cliffs"
        ),
        "comparable_prior_holdout_best": {
            "candidate_id": "gems91-s13-ptha-e3-20261024T201500Z-660d645d",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": split_sha,
            "label": "HOLDOUT-DTI",
            "value": s13_ref_holdout["holdout_dti"],
            "ci95": s13_ref_holdout["ci_95"],
            "withheld_positives": s13_ref_holdout["n_withheld_positives"],
        },
        "holdout_dti": {
            "status": "COMPLETED",
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": split_sha,
            "value": win_exp["holdout"]["holdout_dti"],
            "ci95": win_exp["holdout"]["ci_95"],
            "withheld_positives": win_exp["holdout"]["n_withheld_positives"],
            "paired_best": {
                "baseline_id": "S13-PTHA-E3",
                "delta": win_exp["paired_vs_s13_ptha_e3"]["delta"],
                "ci95": win_exp["paired_vs_s13_ptha_e3"]["ci95"],
                "prob_positive": win_exp["paired_vs_s13_ptha_e3"]["prob_positive"],
                "n_paired_5km_tiles": win_exp["paired_vs_s13_ptha_e3"]["n_paired_5km_tiles"],
            },
            "delta_vs_s12_spac_e3": round(win_exp["holdout"]["holdout_dti"] - 0.237587, 6),
            "delta_vs_s11_mhtr_e2": round(win_exp["holdout"]["holdout_dti"] - 0.206406, 6),
            "per_fold": win_exp["holdout"]["folds"],
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-CONTROL-DTI (not competition leaderboard)",
            "value": sgmc_res["dti"],
            "r0_reference_value": r0_sgmc["dti"],
            "s13_ptha_e3_reference_value": 0.100815,
            "s12_spac_e3_reference_value": 0.107938,
            "s11_e2_reference_value": 0.097623,
            "delta_vs_r0": round(sgmc_res["dti"] - r0_sgmc["dti"], 6),
            "delta_vs_s13_ptha_e3": round(sgmc_res["dti"] - 0.100815, 6),
            "n_offcatalogue_sgmc_positives": sgmc_res["n_offcatalogue_sgmc_positives"],
        },
        "canaries": {
            "status": "PASS" if canary_report["canary_pass"] else "FAIL",
            "n_features_checked": canary_report["n_features_checked"],
            "max_symmetric_auc": canary_report["worst_symmetric_auc"],
            "worst_feature": canary_report["worst_feature"],
            "threshold": 0.90,
        },
        "registry_comparison": {
            "complete_universal_registry": False,
            "canonical_registry_scope": uniq_canonical,
            "external_dotted_fleet_scope": uniq_ext_dotted,
            "external_all_non_lattice_scope": uniq_ext_all_real,
            "in_repo_siblings_scope": uniq_siblings,
            "universal_all_files_scope": uniq_universal,
            "preplacement": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if uniq_universal["max_abs_surface_spearman"] <= 0.90 else "STOPPED_DUPLICATE",
                "checked": uniq_universal["n_checked"],
                "not_checked_after_stop": 0,
            },
            "final": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if uniq_universal["pass"] else "BLOCKED_SYNTHETIC_AND_DENSE_HALOS",
                "checked": uniq_universal["n_checked"],
                "not_checked_after_stop": 0,
            },
            "max_measured_surface_rank_correlation": uniq_universal["max_abs_surface_spearman"],
            "max_measured_final_dot_overlap_within_3px": uniq_universal["max_3px_dot_overlap"],
            "max_canonical_registry_dot_overlap_within_3px": uniq_canonical["max_3px_dot_overlap"],
            "max_external_dotted_fleet_dot_overlap_within_3px": uniq_ext_dotted["max_3px_dot_overlap"],
            "closest_external_dotted_raster": uniq_ext_dotted["dots_closest_raster"],
            "note": (
                f"Checked across all 64/64 frozen external inventory rasters (including restored "
                f"retracted GEOD25m10) plus {uniq_siblings['n_checked']} in-repo sibling downloads. "
                f"Canonical data/registry/ max 3px overlap = {uniq_canonical['max_3px_dot_overlap']:.4f}; "
                f"external dotted fleet (<65k pos) max 3px overlap = {uniq_ext_dotted['max_3px_dot_overlap']:.4f} "
                f"({uniq_ext_dotted['dots_closest_raster']}). Synthetic whole-Nevada blanket "
                f"calib_r13lattice_00904 (206,895 px covering 99.87% of Nevada, IR-CED-003) "
                f"and unsubmitted in-repo predecessors are audited explicitly; submission_ready "
                f"remains fail-closed False pending human selector sign-off."
            ),
        },
        "artifact": {
            "candidate_id": cand_id,
            "primary_zeros_tif": f"docs/downloads/{dl_zeros.name}",
            "primary_zeros_sha256": audit["primary_zeros_tif"]["sha256"],
            "primary_zeros_bytes": audit["primary_zeros_tif"]["bytes"],
            "zip_bundle": audit["zip_bundle"]["path"],
            "zip_sha256": audit["zip_bundle"]["sha256"],
            "zip_bytes": audit["zip_bundle"]["bytes"],
            "n_dots": audit["dots"]["n_dots"],
            "dot_set_digest": audit["dots"]["dot_set_digest"],
            "min_catalogue_distance_px": audit["dots"]["min_catalogue_distance_px"],
        },
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "validator_output": {
            "status": "PASS",
            "no_nan_inside_footprint": audit["primary_zeros_tif"]["nan_cells_anywhere"] == 0,
            "values_in_0_1": (
                0.0 <= audit["primary_zeros_tif"]["min_value"]
                and audit["primary_zeros_tif"]["max_value"] <= 1.0
            ),
            "crs_shape_transform_match": (
                audit["grid"]["crs"] == "EPSG:32611"
                and audit["grid"]["shape"] == [3730, 3292]
            ),
            "checks": {
                "gems91_gates_pass": audit["validators"]["gems91_gates_verdict"] == "CERTIFIED",
                "release_gates_nan_pass": audit["validators"]["release_gates_nan_pass"],
                "release_gates_zeros_pass": audit["validators"]["release_gates_zeros_pass"],
                "validate_raster_nan_pass": audit["validators"]["validate_raster_nan_pass"],
                "validate_raster_zeros_pass": audit["validators"]["validate_raster_zeros_pass"],
                "zero_catalogue_overlap": audit["dots"]["zero_catalogue_mass"],
                "min_300m_catalogue_clearance": audit["dots"]["dots_le_3px"] == 0,
            },
        },
        "submission": {
            "name": sub_name,
            "note": sub_note,
            "note_length": len(sub_note),
        },
        "selector_approval": False,
        "selector_receipt": {
            "weekly_cap_verified": False,
            "slot_available": False,
            "note": "Requires human fleet selector check against live DrivenData 3/rolling-7-day slot counter.",
        },
        "technical_candidate_verdict": (
            "promote_to_selector" if (beats_s13 and external_dotted_unique) else "negative"
        ),
        "verdict": "promote" if (beats_s13 and external_dotted_unique) else "negative",
        "portal_submission_verdict": "HOLD_PENDING_SELECTOR_SIGN_OFF",
        "budget": {
            "experiments_executed": len(exp_results),
            "max_experiments": MAX_EXPERIMENTS,
            "elapsed_seconds": elapsed_total,
            "max_seconds": MAX_BUDGET_SECONDS,
        },
        "experiments": exp_results,
    }
    run_card_s14["readiness_gates"] = RD.gates(run_card_s14)
    run_card_s14["submission_ready"] = RD.submission_ready(run_card_s14)

    RUN_CARD_S14_JSON.write_text(json.dumps(run_card_s14, indent=2) + "\n", encoding="utf-8")
    EVIDENCE_JSON.write_text(json.dumps(run_card_s14, indent=2) + "\n", encoding="utf-8")
    _log(f"Wrote {RUN_CARD_S14_JSON} & {EVIDENCE_JSON}")
    _log(f"readiness_gates = {run_card_s14['readiness_gates']}")
    _log(
        f"verdict = {run_card_s14['verdict']} ({run_card_s14['technical_candidate_verdict']}) | "
        f"total={elapsed_total:.1f}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
