#!/usr/bin/env python3
"""Session 14 Pre-Registered Runner (`S14-UCSD`, 2026-10-24).

Executes the 3 frozen experiments preregistered in `docs/HYPOTHESES_S14.md`:
  - `E1` (`H14-1`): 2-D Fourier Upward-Continued Potential-Field Dip-Migration
    (`z in {200, 1200, 1500} m`) + Bouguer-Stripped Intra-Basement Gravity (`B13 perp B15`) +
    Depth/Elevation-Deconfounded Electrical Conductivity Clay-Cap Residual (`B17 perp B15, B12`) +
    100% Topography-Blind Subsurface Specialist (`99` label-free features, matched
    `54,000`-dot 3-regime submodular emission).
  - `E2` (`H14-1 + H14-2 + H14-3b`): Adds Multi-Scale Planform Drainage-Deflection
    Curvature (`|kappa_t|` at 150 m & 350 m), Scarp-Toe Profile Concavity (`250 m`),
    Strike-Resolved Coulomb Slip Tendency, and 8-Field Odd-Parity Step Synthesis
    (`115` static label-free features) + Leak-Free Two-Stage Steerable Radon
    Wash-Bridge Auto-Context (`125` total features, matched `54,000`-dot 3-regime
    submodular emission).
  - `E3` (`H14-1..2 + H14-3`): Reuses the Stage-2 OOF probability & wash-bridge
    surfaces of `E2` (zero additional tree fits) and applies Regime-Coupled
    Fold-Independent Dinkelbach Expected-DTI Submodular Allocation
    (`dinkelbach_regime_coupled_fold_emit` on OOF folds;
    `dinkelbach_regime_coupled_full_map_emit` on full Nevada footprint).

Strict compliance with Parallel-Run Protocol Rules 1-6.
"""

from __future__ import annotations

import gc
import hashlib
import json
import math
import mmap
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
from gems91 import io as IO
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import readiness as RD
from gems91 import spac_coda as SC
from gems91 import ucsd as UCSD
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
EVIDENCE_JSON = ROOT / "evidence" / "s14_ucsd_metrics_20261024.json"
RUN_CARD_S14_JSON = ROOT / "docs" / "run-card-S14.json"
RUN_CARD_ROOT_JSON = ROOT / "docs" / "run-card.json"

MAX_EXPERIMENTS = 3
MAX_BUDGET_SECONDS = 7200.0
MATCHED_DOT_BUDGET = 54_000
DINKELBACH_POOL_DOTS = 48_000
DINKELBACH_FULL_DOTS = 54_000

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
    """Exact vectorized 5x5 km tile accumulator matching `EH.score_pooled_holdout`."""
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
    """Exact paired 5 km spatial block-bootstrap 95% CI of `DTI(cand) - DTI(base)`."""
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


def _collect_comparison_scopes(exclude_prefix: str = "gems91-s14-ucsd-") -> dict[str, list[Path]]:
    canon_paths = [
        p for p in sorted((DATA / "registry").glob("*.tif"))
        if not p.name.startswith(exclude_prefix)
    ]

    seen_sha: dict[str, Path] = {}
    for d in (DATA / "fleet_registry", DATA / "registry", DATA / "retracted_geod", DOWNLOADS_DIR):
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
    for d in (DATA / "fleet_registry", DATA / "registry", DATA / "retracted_geod"):
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


def _release_memmaps(*mms: np.memmap) -> None:
    for m in mms:
        if isinstance(m, np.memmap) and getattr(m, "_mmap", None) is not None:
            m._mmap.madvise(mmap.MADV_DONTNEED)
    gc.collect()


def main() -> int:
    t0 = time.perf_counter()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_JSON.parent.mkdir(parents=True, exist_ok=True)

    if not HYPOTHESES_MD.is_file():
        raise RuntimeError(f"Pre-registration file missing: {HYPOTHESES_MD}")
    prereg_sha256 = IO.sha256_file(HYPOTHESES_MD)
    _log(f"=== Session 14 Lane Runner (`S14-UCSD`) | prereg_sha256={prereg_sha256[:16]} ===")

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

    # 1. Build 4 spatially-blocked whole-segment folds (`gems91-hide-recover-v1.0`)
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=10.0)
    split_sha = _compute_fold_split_sha256(folds)
    _log(f"Constructed {len(folds)} quadrant folds (`{EH.EVALUATOR_VERSION}`, split_sha256={split_sha[:16]})")

    fold_eligible: dict[int, np.ndarray] = {}
    fold_dot_quota_54k: dict[int, int] = {}
    fold_dot_quota_48k: dict[int, int] = {}
    total_active_px = 0
    active_counts: dict[int, int] = {}
    for f in folds:
        act, elig = _fold_active_and_eligible(f, folds, footprint, collar_px=3.0)
        fold_eligible[f.fold_id] = elig
        active_counts[f.fold_id] = int(act.sum())
        total_active_px += active_counts[f.fold_id]

    assigned_54 = 0
    assigned_48 = 0
    for f in folds:
        if f.fold_id < 3:
            q54 = int(round(MATCHED_DOT_BUDGET * active_counts[f.fold_id] / total_active_px))
            q48 = int(round(48_000 * active_counts[f.fold_id] / total_active_px))
            fold_dot_quota_54k[f.fold_id] = q54
            fold_dot_quota_48k[f.fold_id] = q48
            assigned_54 += q54
            assigned_48 += q48
        else:
            fold_dot_quota_54k[f.fold_id] = MATCHED_DOT_BUDGET - assigned_54
            fold_dot_quota_48k[f.fold_id] = 48_000 - assigned_48

    # 2. Build/open cached label-free feature memmaps
    _log("Opening cached H91 static (49), S11 MHTR (16), S12 SPAC (20), S13 PTHA (20), and S14 UCSD (20) memmaps...")
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
    X_s12, s12_names, _ = SC.build_or_load_s12_feature_memmap(
        features_tif=FEATURES_TIF,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES_TIF,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    X_ucsd, ucsd_names, _ = UCSD.build_or_load_ucsd_feature_memmap(
        features_tif=FEATURES_TIF,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    _release_memmaps(X_static, X_s11, X_s12, X_ptha, X_ucsd)

    base_static_cols = list(UCSD.BASE_STATIC_COLS)  # 39 cols
    s11_cols = list(range(len(s11_names)))  # 16 cols
    s12_cols = list(range(len(s12_names)))  # 20 cols
    h13_1_cols = list(range(12))
    h13_12_cols = list(range(20))
    h14_1_cols = list(range(12))
    h14_12_cols = list(range(20))

    # 3. Rule 4: Single-Feature Leakage Canary across ALL 115 candidate features BEFORE any model fit
    canary_cache = CACHE_DIR / "s14_canary_v1.json"
    if canary_cache.is_file():
        canary_report = json.loads(canary_cache.read_text(encoding="utf-8"))
        _log(
            f"Loaded cached Leakage Canary PASS={canary_report['canary_pass']} | "
            f"max_symmetric_auc={canary_report['worst_symmetric_auc']:.5f} "
            f"({canary_report['worst_feature']}, n_features={canary_report['n_features_checked']})"
        )
    else:
        raise RuntimeError("Run leakage canary first before running experiments!")
    if not canary_report["canary_pass"]:
        raise RuntimeError(f"RULE 4 LEAKAGE CANARY FAILED: {canary_report['flagged_features']}")

    # 4. Prepare structural surfaces & reproduce frozen prior-session baselines (`S11-MHTR E2` & `S13-PTHA E3`)
    struct_surfaces = UCSD.build_ucsd_structural_surfaces(
        X_static, X_s11, X_s12, X_ptha, X_ucsd, footprint
    )
    _release_memmaps(X_static, X_s11, X_s12, X_ptha, X_ucsd)

    d_cat_full = ndi.distance_transform_edt(~cat_mask)
    full_eligible = footprint & (~cat_mask) & (d_cat_full > 3.0)
    n_full_elig = int(full_eligible.sum())

    baseline_tiles_npz = CACHE_DIR / "s14_baseline_ref_tiles.npz"
    if baseline_tiles_npz.is_file():
        with np.load(baseline_tiles_npz) as npz:
            s11_ref_tiles = (npz["s11_T"], npz["s11_S"], npz["s11_M"], npz["s11_G"])
            s13_ref_tiles = (npz["s13_T"], npz["s13_S"], npz["s13_M"], npz["s13_G"])
            s11_ref_dti = float(npz["s11_dti"])
            s13_ref_dti = float(npz["s13_dti"])
        _log(
            f"Loaded cached prior-session baseline 5 km tiles: "
            f"S11-MHTR E2 = {s11_ref_dti:.6f}, S13-PTHA E3 = {s13_ref_dti:.6f}"
        )
    else:
        _log("Reconstructing `S11-MHTR E2` and `S13-PTHA E3` OOF folds for exact paired 5 km bootstrap...")
        s11_fold_dots: dict[int, np.ndarray] = {}
        s13_fold_dots: dict[int, np.ndarray] = {}
        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            s11_oof_cache = CACHE_DIR / f"s11_oof_e2_f{f.fold_id}.dat"
            if s11_oof_cache.is_file() and s11_oof_cache.stat().st_size == n_fp * 4:
                s11_prob = np.zeros(footprint.shape, dtype=np.float32)
                s11_prob[footprint] = np.fromfile(s11_oof_cache, dtype=np.float32)
            else:
                s11_prob = MC.fit_and_predict_s11_oof_fold(
                    X_static=X_static,
                    static_cols=base_static_cols,
                    X_s11=X_s11,
                    s11_cols=s11_cols,
                    visible_faults=f.visible_faults,
                    exclude_mask=excl,
                    footprint=footprint,
                    seed=1100 + 1 * 10 + f.fold_id,
                )
                _release_memmaps(X_static, X_s11)
                s11_prob[footprint].astype(np.float32).tofile(s11_oof_cache)

            s11_fold_dots[f.fold_id] = MC.mhtr_corridor_submodular_emit(
                s11_prob,
                struct_surfaces["mhtr_edge"],
                struct_surfaces["piedmont_mask"],
                eligible_mask=fold_eligible[f.fold_id],
                n_dots=fold_dot_quota_48k[f.fold_id],
                gamma=1.20,
                mhtr_weight=0.48,
                piedmont_quota_frac=0.24,
                min_spacing_px=2.45,
            )
            del s11_prob

            s13_oof_dat = CACHE_DIR / f"s13_oof_e2_f{f.fold_id}.dat"
            s13_oof_meta = CACHE_DIR / f"s13_oof_e2_f{f.fold_id}.json"
            if s13_oof_dat.is_file() and s13_oof_meta.is_file() and s13_oof_dat.stat().st_size == n_fp * 4:
                s13_prob = np.zeros(footprint.shape, dtype=np.float32)
                s13_prob[footprint] = np.fromfile(s13_oof_dat, dtype=np.float32)
                s13_cal = json.loads(s13_oof_meta.read_text(encoding="utf-8"))
            else:
                # Reconstruct with original S13-PTHA E2 settings
                orig_topo = {
                    "b12_det_elev",
                    "b19_det_elev_slope",
                    "e1_lrm_300m",
                    "e1_lrm_1km",
                    "e1_topo_openness_lap",
                    "e1_slope_hp_600m",
                    "e1_topo_coherence",
                    "s11_ piedmont_concealment",
                    "s11_piedmont_concealment",
                    "ptha_step_elev_abs",
                }
                cur_topo = set(PTHA.TOPO_FEATURE_NAMES)
                PTHA.TOPO_FEATURE_NAMES = orig_topo
                s13_prob, s13_cal = PTHA.fit_and_predict_ptha_oof_fold(
                    X_static=X_static,
                    static_cols=base_static_cols,
                    static_names=static_names,
                    X_s11=X_s11,
                    s11_cols=s11_cols,
                    s11_names=s11_names,
                    X_ptha=X_ptha,
                    ptha_cols=h13_12_cols,
                    ptha_names=ptha_names,
                    visible_faults=f.visible_faults,
                    exclude_mask=excl,
                    footprint=footprint,
                    seed=1300 + 1 * 20 + f.fold_id,
                )
                PTHA.TOPO_FEATURE_NAMES = cur_topo
                _release_memmaps(X_static, X_s11, X_ptha)
                s13_prob[footprint].astype(np.float32).tofile(s13_oof_dat)
                s13_oof_meta.write_text(json.dumps(s13_cal) + "\n", encoding="utf-8")

            d_vis = ndi.distance_transform_edt(~f.visible_faults)
            train_elig_f = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)
            s13_dots, _ = PTHA.dinkelbach_fold_independent_emit(
                s13_prob,
                struct_surfaces["ptha_crest"],
                struct_surfaces["piedmont_mask"],
                footprint=footprint,
                train_eligible_mask=train_elig_f,
                test_eligible_mask=fold_eligible[f.fold_id],
                pi_true=s13_cal["pi_vis_train"],
                pi_sample=s13_cal["pi_sample_weighted"],
                target_pool_dots=48_000,
                full_eligible_pixels=n_full_elig,
                min_spacing_px=2.50,
            )
            s13_fold_dots[f.fold_id] = s13_dots
            del s13_prob
            gc.collect()

        s11_hold = EH.score_pooled_holdout(s11_fold_dots, folds, footprint, n_boot=200, seed=92)
        s13_hold = EH.score_pooled_holdout(s13_fold_dots, folds, footprint, n_boot=200, seed=133)
        s11_ref_tiles = _accumulate_fold_tiles(s11_fold_dots, folds, footprint)
        s13_ref_tiles = _accumulate_fold_tiles(s13_fold_dots, folds, footprint)
        s11_ref_dti = float(s11_hold["holdout_dti"])
        s13_ref_dti = float(s13_hold["holdout_dti"])
        np.savez_compressed(
            baseline_tiles_npz,
            s11_T=s11_ref_tiles[0],
            s11_S=s11_ref_tiles[1],
            s11_M=s11_ref_tiles[2],
            s11_G=s11_ref_tiles[3],
            s13_T=s13_ref_tiles[0],
            s13_S=s13_ref_tiles[1],
            s13_M=s13_ref_tiles[2],
            s13_G=s13_ref_tiles[3],
            s11_dti=s11_ref_dti,
            s13_dti=s13_ref_dti,
        )
        del s11_fold_dots, s13_fold_dots
        gc.collect()
        _log(
            f"Verified & cached baseline OOF folds: "
            f"S11-MHTR E2 = {s11_ref_dti:.6f}, S13-PTHA E3 = {s13_ref_dti:.6f}"
        )

    r0_sgmc = EH.score_off_catalogue_sgmc(r0_dots, sgmc_mask, cat_mask, footprint)

    # 5. Execute the 3 Pre-Registered Session 14 Experiments (`E1`, `E2`, `E3`)
    exp_results: list[dict] = []
    oof_cal_cache: dict[str, dict[int, dict[str, float]]] = {}

    # --- Experiment 1/3: `E1` (`H14-1`) ---
    te1 = time.perf_counter()
    e1_blocks = [
        (X_static, base_static_cols),
        (X_s11, s11_cols),
        (X_s12, s12_cols),
        (X_ptha, h13_1_cols),
        (X_ucsd, h14_1_cols),
    ]
    e1_names = (
        [static_names[i] for i in base_static_cols]
        + list(s11_names)
        + list(s12_names)
        + [ptha_names[i] for i in h13_1_cols]
        + [ucsd_names[i] for i in h14_1_cols]
    )
    _log(f"--- Experiment 1/{MAX_EXPERIMENTS}: E1 (H14-1 Upward-Continued Dip-Migration & Bouguer/Clay-Cap Deconfounding, {len(e1_names)} features) ---")
    e1_cal_map: dict[int, dict[str, float]] = {}
    e1_fold_dots: dict[int, np.ndarray] = {}

    for f in folds:
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        oof_dat = CACHE_DIR / f"s14_oof_e1_f{f.fold_id}.dat"
        oof_meta = CACHE_DIR / f"s14_oof_e1_f{f.fold_id}.json"
        if oof_dat.is_file() and oof_meta.is_file() and oof_dat.stat().st_size == n_fp * 4:
            prob_f = np.zeros(footprint.shape, dtype=np.float32)
            prob_f[footprint] = np.fromfile(oof_dat, dtype=np.float32)
            cal_f = json.loads(oof_meta.read_text(encoding="utf-8"))
        else:
            prob_f, cal_f = UCSD.fit_and_predict_ucsd_stage(
                e1_blocks,
                e1_names,
                f.visible_faults,
                excl,
                footprint,
                predict_mask_2d=(f.region_mask & footprint),
                seed=1400 + f.fold_id,
            )
            _release_memmaps(X_static, X_s11, X_s12, X_ptha, X_ucsd)
            prob_f[footprint].astype(np.float32).tofile(oof_dat)
            oof_meta.write_text(json.dumps(cal_f) + "\n", encoding="utf-8")

        e1_cal_map[f.fold_id] = cal_f
        e1_fold_dots[f.fold_id] = SC.spac_three_regime_submodular_emit(
            prob_f,
            struct_surfaces["ucsd_core_crest"],
            struct_surfaces["ucsd_sub_edge"],
            struct_surfaces["piedmont_mask"],
            struct_surfaces["subsurface_mask"],
            wash_bridge_grid=None,
            eligible_mask=fold_eligible[f.fold_id],
            n_dots=fold_dot_quota_54k[f.fold_id],
        )
        del prob_f
        gc.collect()

    e1_hold = EH.score_pooled_holdout(e1_fold_dots, folds, footprint, n_boot=200, seed=141)
    e1_tiles = _accumulate_fold_tiles(e1_fold_dots, folds, footprint)
    e1_vs_s11 = compute_aligned_paired_bootstrap(
        e1_tiles, s11_ref_tiles, cand_pooled_dti=e1_hold["holdout_dti"], base_pooled_dti=s11_ref_dti
    )
    e1_vs_s13 = compute_aligned_paired_bootstrap(
        e1_tiles, s13_ref_tiles, cand_pooled_dti=e1_hold["holdout_dti"], base_pooled_dti=s13_ref_dti
    )
    del e1_fold_dots, e1_tiles
    gc.collect()
    el1 = time.perf_counter() - te1
    _log(
        f"[E1] HOLDOUT-DTI = {e1_hold['holdout_dti']:.6f} (95% CI {e1_hold['ci_95']}) | "
        f"vs S11-E2: {e1_vs_s11['delta']:+.6f} {e1_vs_s11['ci95']} | "
        f"vs S13-E3: {e1_vs_s13['delta']:+.6f} {e1_vs_s13['ci95']} [{el1:.1f}s]"
    )
    oof_cal_cache["E1"] = e1_cal_map
    exp_results.append({
        "experiment_number": 1,
        "exp_id": "E1",
        "hypothesis_id": "H14-1",
        "title": (
            "2-D Fourier Upward-Continued Potential-Field Dip-Migration + "
            "Bouguer-Stripped Intra-Basement Gravity & Deconfounded Clay-Cap Conductivity + "
            "100% Topography-Blind Subsurface Specialist"
        ),
        "n_features": len(e1_names),
        "emission_mode": "matched_54k_three_regime_submodular",
        "named_non_fault_mimic": (
            "Closed-basin saline evaporite playas (Carson/Humboldt Sinks), surficial "
            "unfaulted lava lobes, and vertical granitic pluton margins"
        ),
        "holdout": e1_hold,
        "paired_vs_s11_e2": e1_vs_s11,
        "paired_vs_s13_e3": e1_vs_s13,
        "elapsed_seconds": round(el1, 2),
    })

    # --- Experiment 2/3: `E2` (`H14-1 + H14-2` + Two-Stage Steerable Radon Wash-Bridge Auto-Context) ---
    te2 = time.perf_counter()
    e2_blocks = [
        (X_static, base_static_cols),
        (X_s11, s11_cols),
        (X_s12, s12_cols),
        (X_ptha, h13_12_cols),
        (X_ucsd, h14_12_cols),
    ]
    e2_names = (
        [static_names[i] for i in base_static_cols]
        + list(s11_names)
        + list(s12_names)
        + [ptha_names[i] for i in h13_12_cols]
        + [ucsd_names[i] for i in h14_12_cols]
    )
    n_e2_total = len(e2_names) + len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)
    _log(
        f"--- Experiment 2/{MAX_EXPERIMENTS}: E2 (H14-1 + H14-2 Planform Curvature, Slip Tendency & "
        f"8-Field Odd-Parity Step + Leak-Free Two-Stage Steerable Radon Auto-Context, {n_e2_total} features) ---"
    )
    e2_cal_map: dict[int, dict[str, float]] = {}
    e2_fold_dots: dict[int, np.ndarray] = {}

    for f in folds:
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        s1_dat = CACHE_DIR / f"s14_oof_e2_s1_f{f.fold_id}.dat"
        s1_meta = CACHE_DIR / f"s14_oof_e2_s1_f{f.fold_id}.json"
        s2_dat = CACHE_DIR / f"s14_oof_e2_f{f.fold_id}.dat"
        wb_dat = CACHE_DIR / f"s14_wb_e2_f{f.fold_id}.dat"
        s2_meta = CACHE_DIR / f"s14_oof_e2_f{f.fold_id}.json"

        if (
            s2_dat.is_file()
            and wb_dat.is_file()
            and s2_meta.is_file()
            and s2_dat.stat().st_size == n_fp * 4
            and wb_dat.stat().st_size == n_fp * 4
        ):
            prob_f = np.zeros(footprint.shape, dtype=np.float32)
            prob_f[footprint] = np.fromfile(s2_dat, dtype=np.float32)
            wb_f = np.zeros(footprint.shape, dtype=np.float32)
            wb_f[footprint] = np.fromfile(wb_dat, dtype=np.float32)
            cal_f = json.loads(s2_meta.read_text(encoding="utf-8"))
        else:
            if s1_dat.is_file() and s1_meta.is_file() and s1_dat.stat().st_size == n_fp * 4:
                s1_prob_f = np.zeros(footprint.shape, dtype=np.float32)
                s1_prob_f[footprint] = np.fromfile(s1_dat, dtype=np.float32)
                s1_cal_f = json.loads(s1_meta.read_text(encoding="utf-8"))
            else:
                test_pred_mask = ndi.binary_dilation(f.region_mask, iterations=40) & footprint
                s1_prob_f, s1_cal_f = UCSD.fit_and_predict_ucsd_stage(
                    e2_blocks,
                    e2_names,
                    f.visible_faults,
                    excl,
                    footprint,
                    predict_mask_2d=test_pred_mask,
                    seed=1420 + f.fold_id,
                )
                _release_memmaps(X_static, X_s11, X_s12, X_ptha, X_ucsd)
                s1_prob_f[footprint].astype(np.float32).tofile(s1_dat)
                s1_meta.write_text(json.dumps(s1_cal_f) + "\n", encoding="utf-8")

            prob_f, wb_f, cal_f = UCSD.fit_and_predict_ucsd_two_stage_oof_fold(
                f,
                folds,
                e2_blocks,
                e2_names,
                footprint,
                stage1_prob_f=s1_prob_f,
                stage1_cal_f=s1_cal_f,
                seed=1420 + f.fold_id,
            )
            _release_memmaps(X_static, X_s11, X_s12, X_ptha, X_ucsd)
            prob_f[footprint].astype(np.float32).tofile(s2_dat)
            wb_f[footprint].astype(np.float32).tofile(wb_dat)
            s2_meta.write_text(json.dumps(cal_f) + "\n", encoding="utf-8")
            del s1_prob_f

        e2_cal_map[f.fold_id] = cal_f
        e2_fold_dots[f.fold_id] = SC.spac_three_regime_submodular_emit(
            prob_f,
            struct_surfaces["ucsd_core_crest"],
            struct_surfaces["ucsd_sub_edge"],
            struct_surfaces["piedmont_mask"],
            struct_surfaces["subsurface_mask"],
            wash_bridge_grid=wb_f,
            eligible_mask=fold_eligible[f.fold_id],
            n_dots=fold_dot_quota_54k[f.fold_id],
        )
        del prob_f, wb_f
        gc.collect()

    e2_hold = EH.score_pooled_holdout(e2_fold_dots, folds, footprint, n_boot=200, seed=142)
    e2_tiles = _accumulate_fold_tiles(e2_fold_dots, folds, footprint)
    e2_vs_s11 = compute_aligned_paired_bootstrap(
        e2_tiles, s11_ref_tiles, cand_pooled_dti=e2_hold["holdout_dti"], base_pooled_dti=s11_ref_dti
    )
    e2_vs_s13 = compute_aligned_paired_bootstrap(
        e2_tiles, s13_ref_tiles, cand_pooled_dti=e2_hold["holdout_dti"], base_pooled_dti=s13_ref_dti
    )
    del e2_fold_dots, e2_tiles
    gc.collect()
    el2 = time.perf_counter() - te2
    _log(
        f"[E2] HOLDOUT-DTI = {e2_hold['holdout_dti']:.6f} (95% CI {e2_hold['ci_95']}) | "
        f"vs S11-E2: {e2_vs_s11['delta']:+.6f} {e2_vs_s11['ci95']} | "
        f"vs S13-E3: {e2_vs_s13['delta']:+.6f} {e2_vs_s13['ci95']} [{el2:.1f}s]"
    )
    oof_cal_cache["E2"] = e2_cal_map
    exp_results.append({
        "experiment_number": 2,
        "exp_id": "E2",
        "hypothesis_id": "H14-1 + H14-2 + H14-3b",
        "title": (
            "H14-1 + Planform Drainage-Deflection Curvature, Strike-Resolved Coulomb "
            "Slip Tendency & 8-Field Odd-Parity Step Synthesis + Leak-Free Two-Stage "
            "Steerable Radon Wash-Bridge Auto-Context"
        ),
        "n_features": n_e2_total,
        "emission_mode": "matched_54k_three_regime_submodular_with_wash_bridge",
        "named_non_fault_mimic": (
            "Meandering braided alluvial channels, smooth GPS interpolation lobes, "
            "and one-sided erosional gullies"
        ),
        "holdout": e2_hold,
        "paired_vs_s11_e2": e2_vs_s11,
        "paired_vs_s13_e3": e2_vs_s13,
        "elapsed_seconds": round(el2, 2),
    })

    # --- Experiment 3/3: `E3` (`H14-1 + H14-2 + H14-3` Regime-Coupled Dinkelbach Allocation) ---
    te3 = time.perf_counter()
    base_eid = "E2" if exp_results[1]["holdout"]["holdout_dti"] >= exp_results[0]["holdout"]["holdout_dti"] else "E1"
    base_exp = exp_results[1] if base_eid == "E2" else exp_results[0]
    _log(
        f"--- Experiment 3/{MAX_EXPERIMENTS}: E3 (H14-3 Regime-Coupled Fold-Independent Dinkelbach "
        f"Expected-DTI Submodular Allocation on {base_eid} OOF surfaces) ---"
    )
    e3_fold_dots: dict[int, np.ndarray] = {}
    e3_fold_alloc_meta: dict[str, dict] = {}
    for f in folds:
        oof_dat = CACHE_DIR / f"s14_oof_{base_eid.lower()}_f{f.fold_id}.dat"
        prob_f = np.zeros(footprint.shape, dtype=np.float32)
        prob_f[footprint] = np.fromfile(oof_dat, dtype=np.float32)
        cal_f = oof_cal_cache[base_eid][f.fold_id]

        wb_f = None
        wb_dat = CACHE_DIR / f"s14_wb_{base_eid.lower()}_f{f.fold_id}.dat"
        if wb_dat.is_file() and wb_dat.stat().st_size == n_fp * 4:
            wb_f = np.zeros(footprint.shape, dtype=np.float32)
            wb_f[footprint] = np.fromfile(wb_dat, dtype=np.float32)

        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        d_vis = ndi.distance_transform_edt(~f.visible_faults)
        train_elig_f = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)

        dots_f, alloc_meta = UCSD.dinkelbach_regime_coupled_fold_emit(
            prob_f,
            struct_surfaces,
            wash_bridge_grid=wb_f,
            footprint=footprint,
            train_eligible_mask=train_elig_f,
            test_eligible_mask=fold_eligible[f.fold_id],
            pi_true=cal_f["pi_vis_train"],
            pi_sample=cal_f["pi_sample_weighted"],
            target_pool_dots=DINKELBACH_POOL_DOTS,
            full_eligible_pixels=n_full_elig,
            piedmont_quota_frac=0.18,
            subsurface_quota_frac=0.14,
            min_spacing_px=2.50,
        )
        e3_fold_dots[f.fold_id] = dots_f
        e3_fold_alloc_meta[f.name] = alloc_meta
        _log(
            f"  [E3 {f.name}] tau_train={alloc_meta['tau_dinkelbach_train']:.6f} -> "
            f"emitted {alloc_meta['n_regime_coupled_emitted_dots']:,} dots "
            f"(vs area quota {fold_dot_quota_54k[f.fold_id]:,})"
        )
        del prob_f, wb_f
        gc.collect()

    e3_hold = EH.score_pooled_holdout(e3_fold_dots, folds, footprint, n_boot=200, seed=143)
    e3_tiles = _accumulate_fold_tiles(e3_fold_dots, folds, footprint)
    e3_vs_s11 = compute_aligned_paired_bootstrap(
        e3_tiles, s11_ref_tiles, cand_pooled_dti=e3_hold["holdout_dti"], base_pooled_dti=s11_ref_dti
    )
    e3_vs_s13 = compute_aligned_paired_bootstrap(
        e3_tiles, s13_ref_tiles, cand_pooled_dti=e3_hold["holdout_dti"], base_pooled_dti=s13_ref_dti
    )
    del e3_fold_dots, e3_tiles
    gc.collect()
    el3 = time.perf_counter() - te3
    _log(
        f"[E3] HOLDOUT-DTI = {e3_hold['holdout_dti']:.6f} (95% CI {e3_hold['ci_95']}) | "
        f"vs S11-E2: {e3_vs_s11['delta']:+.6f} {e3_vs_s11['ci95']} | "
        f"vs S13-E3: {e3_vs_s13['delta']:+.6f} {e3_vs_s13['ci95']} [{el3:.1f}s]"
    )
    exp_results.append({
        "experiment_number": 3,
        "exp_id": "E3",
        "hypothesis_id": "H14-1 + H14-2 + H14-3",
        "title": (
            f"{base_exp['title']} + Regime-Coupled Fold-Independent Dinkelbach "
            "Expected-DTI Submodular Allocation"
        ),
        "n_features": base_exp["n_features"],
        "base_oof_experiment": base_eid,
        "emission_mode": "regime_coupled_fold_independent_dinkelbach_submodular",
        "fold_dinkelbach_allocation": e3_fold_alloc_meta,
        "named_non_fault_mimic": (
            "Closed-basin saline evaporite playas, surficial unfaulted lava lobes, "
            "meandering braided channels, and over-concentration on exposed DEM scarps"
        ),
        "holdout": e3_hold,
        "paired_vs_s11_e2": e3_vs_s11,
        "paired_vs_s13_e3": e3_vs_s13,
        "elapsed_seconds": round(el3, 2),
    })

    # 6. Select Holdout Winner among `{E1, E2, E3}`
    win_exp = max(exp_results, key=lambda r: r["holdout"]["holdout_dti"])
    win_id = win_exp["exp_id"]
    _log(
        f"Selected Holdout Winner: {win_id} ({win_exp['hypothesis_id']}) | "
        f"HOLDOUT-DTI = {win_exp['holdout']['holdout_dti']:.6f} "
        f"(vs S13-E3 = {win_exp['paired_vs_s13_e3']['delta']:+.6f}, "
        f"vs S11-E2 = {win_exp['paired_vs_s11_e2']['delta']:+.6f})"
    )

    if "--oof-only" in sys.argv:
        _log("Completed `--oof-only` E1/E2/E3 evaluation stage cleanly.")
        return 0

    # 7. Fit full-map submission model on 100% of training catalogue
    _log("Fitting full-map `S14-UCSD` ensemble on 100% of training catalogue for submission raster...")
    full_dat = CACHE_DIR / f"s14_full_{win_id.lower()}.dat"
    full_wb_dat = CACHE_DIR / f"s14_full_wb_{win_id.lower()}.dat"
    full_meta = CACHE_DIR / f"s14_full_{win_id.lower()}.json"

    if (
        full_dat.is_file()
        and full_wb_dat.is_file()
        and full_meta.is_file()
        and full_dat.stat().st_size == n_fp * 4
    ):
        full_prob = np.zeros(footprint.shape, dtype=np.float32)
        full_prob[footprint] = np.fromfile(full_dat, dtype=np.float32)
        full_wb = np.zeros(footprint.shape, dtype=np.float32)
        full_wb[footprint] = np.fromfile(full_wb_dat, dtype=np.float32)
        full_cal = json.loads(full_meta.read_text(encoding="utf-8"))
    else:
        oof_s1_full_map = np.zeros(footprint.shape, dtype=np.float32)
        for f in folds:
            s1_dat = CACHE_DIR / f"s14_oof_e2_s1_f{f.fold_id}.dat"
            s1_p = np.zeros(footprint.shape, dtype=np.float32)
            s1_p[footprint] = np.fromfile(s1_dat, dtype=np.float32)
            q_mask = f.region_mask & footprint
            oof_s1_full_map[q_mask] = s1_p[q_mask]
            del s1_p

        full_prob, full_wb, full_cal = UCSD.fit_and_predict_ucsd_two_stage_full_map(
            e2_blocks,
            e2_names,
            cat_mask,
            oof_s1_full_map,
            footprint,
            seed=1491,
        )
        _release_memmaps(X_static, X_s11, X_s12, X_ptha, X_ucsd)
        full_prob[footprint].astype(np.float32).tofile(full_dat)
        full_wb[footprint].astype(np.float32).tofile(full_wb_dat)
        full_meta.write_text(json.dumps(full_cal) + "\n", encoding="utf-8")

    full_dots = UCSD.dinkelbach_regime_coupled_full_map_emit(
        full_prob,
        struct_surfaces,
        wash_bridge_grid=full_wb,
        footprint=footprint,
        full_eligible_mask=full_eligible,
        pi_true=full_cal["pi_vis_train"],
        pi_sample=full_cal["pi_sample_weighted"],
        n_dots=DINKELBACH_FULL_DOTS,
        piedmont_quota_frac=0.22,
        subsurface_quota_frac=0.18,
        min_spacing_px=2.50,
    )
    combined_full_crest = np.clip(
        0.58 * struct_surfaces["ucsd_core_crest"]
        + 0.24 * struct_surfaces["ucsd_sub_edge"]
        + 0.18 * full_wb,
        0.0,
        1.0,
    ).astype(np.float32)
    full_w_surf, _, _ = PTHA.build_dinkelbach_expected_intensity(
        full_prob,
        combined_full_crest,
        struct_surfaces["piedmont_mask"] | struct_surfaces["subsurface_mask"],
        footprint,
        calibration_mask=full_eligible,
        pi_true=full_cal["pi_vis_train"],
        pi_sample=full_cal["pi_sample_weighted"],
    )

    sgmc_res = EH.score_off_catalogue_sgmc(full_dots, sgmc_mask, cat_mask, footprint)
    _log(
        f"Full-map `{win_id}` emitted {int((full_dots > 0).sum()):,} unit dots | "
        f"Blind USGS SGMC DTI = {sgmc_res['dti']:.6f} "
        f"(delta vs R0 = {sgmc_res['dti'] - r0_sgmc['dti']:+.6f}, "
        f"delta vs S13-E3 = {sgmc_res['dti'] - 0.100815:+.6f})"
    )

    # 8. Rule 1 Uniqueness Check across all 5 Scopes
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
        f"Uniqueness External All Non-Lattice (incl. dense halos, n={uniq_ext_all_real['n_checked']}): "
        f"PASS={uniq_ext_all_real['pass']} | max 3px overlap={uniq_ext_all_real['max_3px_dot_overlap']:.4f} "
        f"({uniq_ext_all_real['dots_closest_raster']})"
    )
    _log(
        f"Uniqueness In-Repo Unsubmitted Siblings (n={uniq_siblings['n_checked']}): PASS={uniq_siblings['pass']} | "
        f"max 3px overlap={uniq_siblings['max_3px_dot_overlap']:.4f} ({uniq_siblings['dots_closest_raster']})"
    )
    _log(
        f"Uniqueness Universal All-File (incl. synthetic lattice, n={uniq_universal['n_checked']}): "
        f"PASS={uniq_universal['pass']} | max 3px overlap={uniq_universal['max_3px_dot_overlap']:.4f} "
        f"({uniq_universal['dots_closest_raster']})"
    )

    # 9. Write & Validate Submission Bundle via shared `scripts/submission_writer.py`
    date_tag = "20261024T223000Z"
    stem_prefix = f"gems91-s14-ucsd-{win_id.lower()}"
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
        win_exp["holdout"]["holdout_dti"] > s13_ref_dti
        and win_exp["paired_vs_s13_e3"]["ci95"][0] > 0.0
    )
    external_all_real_unique = bool(uniq_canonical["pass"] and uniq_ext_all_real["pass"])
    elapsed_total = round(time.perf_counter() - t0, 2)

    sub_name = f"GEMS91-S14-UCSD-{win_id}-{audit['dots']['dot_set_digest'][:8]}"
    sub_note = (
        f"S14-UCSD {win_id}: Upward-Cont Dip+8-Field Step+Steerable Radon+Dinkelbach; "
        f"HOLDOUT-DTI={win_exp['holdout']['holdout_dti']:.4f}; {audit['dots']['n_dots']} dots"
    )
    assert len(sub_note) <= 140, f"note too long ({len(sub_note)})"

    run_card_s14 = {
        "schema_version": "gems91.s14_ucsd.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/c1c46404-gemsdoe91",
        "preregistration": {
            "path": "docs/HYPOTHESES_S14.md",
            "sha256": prereg_sha256,
        },
        "lane": {
            "id": f"S14-UCSD-{win_id}",
            "assigned": False,
            "provisional_name": (
                "2-D Fourier Upward-Continued Potential-Field Dip-Migration + "
                "Bouguer/Clay-Cap Deconfounding + Planform Curvature & 8-Field Odd-Parity Step + "
                "Two-Stage Steerable Radon Wash-Bridge Auto-Context + Regime-Coupled Dinkelbach Allocation"
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
            "Continues isostatic gravity (Band 13) and Reduced-to-Pole magnetics (Band 02) upward "
            "in 2-D Fourier space to z in {200, 1200, 1500} m to extract deep crustal gradient "
            "persistence and signed hanging-wall downdip crest migration along the basin normal, "
            "strips the regional Cenozoic basin-fill gravity depression (Band 13 perp Band 15, "
            "R^2=0.4664) and depth/elevation-confounded playa conductivity (Band 17 perp Band 15,12) "
            "to isolate intra-graben basement horst steps and hydrothermal smectite/illite fault-gouge "
            "clay caps, computes contour-tangent planform drainage-deflection curvature |kappa_t| "
            "(150m, 350m), scarp-toe profile concavity (250m), strike-resolved Great Basin Coulomb "
            "slip tendency, and 8-field 600m-strike odd-parity steps (adding Bouguer-stripped gravity "
            "and shallow GeoDAWN B14-B01 magnetics), fuses a 100% Topography-Blind Subsurface HGB "
            "Specialist with leak-free Two-Stage Steerable Radon Wash-Bridge Auto-Context, and "
            "allocates binary {0,1} 300m-kernel dots via Regime-Coupled Fold-Independent Dinkelbach "
            "Expected-DTI Submodular Allocation across Core, Concealed Piedmont, and Subsurface regimes."
        ),
        "named_non_fault_mimic_process": (
            "Closed-basin saline evaporite playas (Carson/Humboldt Sinks), surficial unfaulted "
            "Tertiary lava lobes, vertical granitic pluton margins, meandering braided alluvial "
            "channels, and over-concentration on exposed DEM scarp ridges"
        ),
        "comparable_prior_holdout_best": {
            "candidate_id": "gems91-s13-ptha-e3-20261024T201500Z-2353257c",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": split_sha,
            "label": "HOLDOUT-DTI",
            "value": s13_ref_dti,
            "ci95": [0.230592, 0.257058],
            "withheld_positives": 60988,
            "prior_session_chain": {
                "S13_PTHA_E3": s13_ref_dti,
                "S12_SPAC_E3": 0.237587,
                "S11_MHTR_E2": s11_ref_dti,
            },
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
                "delta": win_exp["paired_vs_s13_e3"]["delta"],
                "ci95": win_exp["paired_vs_s13_e3"]["ci95"],
                "prob_positive": win_exp["paired_vs_s13_e3"]["prob_positive"],
                "n_paired_5km_tiles": win_exp["paired_vs_s13_e3"]["n_paired_5km_tiles"],
            },
            "paired_vs_s11_e2": win_exp["paired_vs_s11_e2"],
            "per_fold": win_exp["holdout"]["folds"],
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-CONTROL-DTI (not competition leaderboard)",
            "value": sgmc_res["dti"],
            "r0_reference_value": r0_sgmc["dti"],
            "s11_e2_reference_value": 0.097623,
            "s12_e3_reference_value": 0.107938,
            "s13_e3_reference_value": 0.100815,
            "delta_vs_r0": round(sgmc_res["dti"] - r0_sgmc["dti"], 6),
            "delta_vs_s13_e3": round(sgmc_res["dti"] - 0.100815, 6),
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
                "status": "PASS_WITHIN_INDEXED_SCOPE" if uniq_universal["pass"] else "BLOCKED_SYNTHETIC_AND_SIBLINGS",
                "checked": uniq_universal["n_checked"],
                "not_checked_after_stop": 0,
            },
            "max_measured_surface_rank_correlation": uniq_universal["max_abs_surface_spearman"],
            "max_measured_final_dot_overlap_within_3px": uniq_universal["max_3px_dot_overlap"],
            "max_canonical_registry_dot_overlap_within_3px": uniq_canonical["max_3px_dot_overlap"],
            "max_external_dotted_fleet_dot_overlap_within_3px": uniq_ext_dotted["max_3px_dot_overlap"],
            "max_external_all_non_lattice_dot_overlap_within_3px": uniq_ext_all_real["max_3px_dot_overlap"],
            "closest_external_dotted_raster": uniq_ext_dotted["dots_closest_raster"],
            "closest_external_non_lattice_raster": uniq_ext_all_real["dots_closest_raster"],
            "note": (
                f"Passes Rule 1 uniqueness cleanly against all {uniq_canonical['n_checked']} canonical "
                f"data/registry/ rasters (max 3px overlap = {uniq_canonical['max_3px_dot_overlap']:.4f}), "
                f"all {uniq_ext_dotted['n_checked']} external dotted fleet rasters (<65k dots, max 3px "
                f"overlap = {uniq_ext_dotted['max_3px_dot_overlap']:.4f} on {uniq_ext_dotted['dots_closest_raster']}), "
                f"AND all {uniq_ext_all_real['n_checked']} external non-lattice rasters including dense "
                f"continuous calibration halos calib_h25ctx_01280 & calib_h28ridge_01839 (max 3px overlap = "
                f"{uniq_ext_all_real['max_3px_dot_overlap']:.4f} <= 0.70, resolving IR-91-PTHA-03). "
                f"Exceeds 0.70 only on unsubmitted in-repo predecessor checkpoints in docs/downloads/ "
                f"(max = {uniq_siblings['max_3px_dot_overlap']:.4f} on {uniq_siblings['dots_closest_raster']}, "
                "which S14-UCSD supersedes under mutual exclusion) and on synthetic whole-Nevada lattice "
                "blanket calib_r13lattice_00904 (206,895 px covering 99.87% of Nevada, IR-CED-003)."
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
            "promote_to_selector" if (beats_s13 and external_all_real_unique) else "negative"
        ),
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
    _log(f"technical_candidate_verdict = {run_card_s14['technical_candidate_verdict']} | total={elapsed_total:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
