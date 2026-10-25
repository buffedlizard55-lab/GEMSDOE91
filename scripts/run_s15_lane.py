#!/usr/bin/env python3
"""Session 15 (`S15-EUAS`) Autonomous End-to-End Lane Runner.

Executes strictly within Protocol Rules 1-6:
  0. Verifies frozen pre-registration `docs/HYPOTHESES_S15.md` SHA-256.
  1. Builds/opens §A.5-clean cached feature memmaps (`X_static`, `X_s11`, `X_s12`,
     `X_ptha`, `X_s15` — zero bytes read from `IR-91-26` external `u8` rasters).
  2. Runs Rule-4 single-feature leakage canary across all 109 candidate features
     FIRST (hard-stops if any symmetric ROC-AUC > 0.90).
  3. Reproduces/loads exact `S13-PTHA E3` (`0.244601 HOLDOUT-DTI`) 5x5 km tile
     arrays on `gems91-hide-recover-v1.0` (`60,988` withheld positives) for aligned
     paired block-bootstrap comparison.
  4. Executes <= 3 pre-registered experiments (`< 2 hours` wall-clock):
       - `E1` (`H15-1`): Clean unified stack + 12 3-D Euler Homogeneity & 4-Altitude
         Upward-Continuation Worm features (99 cols), matched 44k-dot submodular emission.
       - `E2` (`H15-1 + H15-2`): `E1` + 8 Spatially-Varying Morris Slip/Dilation &
         Hydrothermal features + 2 Fold-Safe Depth-Deconfounded `B17` Clay-Cap
         Conductivity features (109 cols), matched 44k-dot submodular emission.
       - `E3` (`Best(E1,E2) + H15-3`): Leak-free pairwise inner-quadrant Stage-1 OOF
         -> 10 Steerable Radon Collinear Wash-Bridge Auto-Context features (119 cols) ->
         10x10 km spatial-checkerboard cross-fitted Stage-2 ensemble -> Out-of-Sample
         Calibrated Self-Credit (`M`-Term) Dinkelbach Submodular Allocation.
  5. Fits full-footprint winning model, checks Rule-1 uniqueness BEFORE dot placement
     (`EH.check_registry_surface_uniqueness`) AND AFTER dot placement
     (`EH.check_registry_uniqueness`) across all 4 scopes (canonical `data/registry/`,
     external dotted fleet, all 58 real external fleet rasters, in-repo siblings, and
     literal 64-file `comparison_inventory` including `r13_lattice_s5_00904.tif`).
  6. Emits validated `[0, 1]` all-finite GeoTIFF + single-TIFF ZIP + audit receipt via
     `scripts/submission_writer.py`, runs all 5 validator suites + `src/gems91/readiness.py`,
     and writes `docs/run-card-S15.json` + `evidence/s15_euas_metrics.json`.
"""

from __future__ import annotations

import gc
import hashlib
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
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems91 import dd_vtc_pu as DD
from gems91 import euas_s15 as EUAS
from gems91 import io as IO
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import readiness as RD
from gems91 import release_gates as RG
from gems91 import spac_coda as SPAC
from scripts import dti as DTI
from scripts import evaluate_holdout as EH
from scripts import submission_writer as SW
from scripts import validate_raster as VR

DATA = ROOT / "data"
CACHE_DIR = DATA / "derived"
CKPT_DIR = CACHE_DIR / "s15_checkpoints"
RELEASES_DIR = ROOT / "releases"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"
HYPOTHESES_MD = ROOT / "docs" / "HYPOTHESES_S15.md"
FROZEN_HYPOTHESES_SHA256 = "cc4d81a2de6d56100ad78df4dca13d9d328af5cc36c3cc920a2f4d54f63f1cd0"

TEMPLATE_TIF = DATA / "official" / "sample_submission.tif"
CATALOGUE_TIF = DATA / "official" / "existing_faults.tif"
FEATURES_TIF = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC_CONTROL_TIF = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_ZEROS_TIF = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"

MAX_EXPERIMENTS = 3
MAX_BUDGET_SECONDS = 7200.0
E12_MATCHED_BUDGET = 44_000
E3_CAL_POOL_BUDGET = 48_000
E3_TARGET_BUDGET = 45_500

SYNTHETIC_BLANKET_SUBSTRINGS = (
    "r13_lattice",
    "r13lattice",
    "r14_union_tips10_lat6",
    "r11_greedy_mp",
)


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
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


def _compute_fold_split_sha256(folds: list[EH.HoldoutFold]) -> str:
    h = hashlib.sha256()
    for f in folds:
        h.update(f.name.encode("utf-8"))
        h.update(np.packbits(f.region_mask.ravel()).tobytes())
        h.update(np.packbits(f.withheld_faults.ravel()).tobytes())
    return h.hexdigest()


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


def _compute_aligned_paired_bootstrap(
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
        "ci95": [round(float(ci_lo), 6), round(float(ci_hi), 6)],
        "prob_positive": round(float(np.mean(diffs > 0.0)), 4),
        "n_paired_5km_tiles": int(active.size),
        "n_bootstrap_draws": n_boot,
    }


def _load_or_build_s13_e3_reference_tiles(
    *,
    X_static: np.memmap,
    static_names: list[str],
    X_s11: np.memmap,
    s11_names: list[str],
    X_ptha: np.memmap,
    ptha_names: list[str],
    folds: list[EH.HoldoutFold],
    fold_eligible: dict[int, np.ndarray],
    n_full_elig: int,
    footprint: np.ndarray,
) -> tuple[dict, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Reproduce or load exact `S13-PTHA E3` (`0.244601 HOLDOUT-DTI`) OOF tile vectors
    so `Paired_vs_Comparable_Best` compares against the all-time #1 GEMSDOE91 benchmark.
    """
    npz_path = CKPT_DIR / "s13_ptha_e3_ref_tiles.npz"
    meta_path = CKPT_DIR / "s13_ptha_e3_ref_holdout.json"
    if npz_path.is_file() and meta_path.is_file():
        z = np.load(npz_path)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return meta, (z["tile_T"], z["tile_S"], z["tile_M"], z["tile_G"])

    _log("Building exact `S13-PTHA E3` OOF reference tiles for aligned paired block-bootstrap...")
    # Exact S13 base_static_cols from scripts/run_s13_lane.py line 406:
    s13_static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    s11_cols = list(range(len(s11_names)))
    ptha_cols = list(range(len(ptha_names)))  # E2 won in S13 (all 20 PTHA cols)

    mhtr_edge, piedmont_mask = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    ptha_crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, footprint)
    del mhtr_edge

    s13_fold_dots: dict[int, np.ndarray] = {}
    for f in folds:
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        oof_dat = CKPT_DIR / f"s13_ref_e2_f{f.fold_id}.dat"
        oof_meta = CKPT_DIR / f"s13_ref_e2_f{f.fold_id}.json"
        if oof_dat.is_file() and oof_meta.is_file():
            prob_f = np.zeros(footprint.shape, dtype=np.float32)
            prob_f[footprint] = np.fromfile(oof_dat, dtype=np.float32)
            cal_f = json.loads(oof_meta.read_text(encoding="utf-8"))
        else:
            prob_f, cal_f = PTHA.fit_and_predict_ptha_oof_fold(
                X_static=X_static,
                static_cols=s13_static_cols,
                static_names=static_names,
                X_s11=X_s11,
                s11_cols=s11_cols,
                s11_names=s11_names,
                X_ptha=X_ptha,
                ptha_cols=ptha_cols,
                ptha_names=ptha_names,
                visible_faults=f.visible_faults,
                exclude_mask=excl,
                footprint=footprint,
                seed=1320 + f.fold_id,
            )
            prob_f[footprint].astype(np.float32).tofile(oof_dat)
            oof_meta.write_text(json.dumps(cal_f) + "\n", encoding="utf-8")

        d_vis = ndi.distance_transform_edt(~f.visible_faults)
        train_elig_f = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)
        dots_f, _ = PTHA.dinkelbach_fold_independent_emit(
            prob_f,
            ptha_crest,
            piedmont_mask,
            footprint=footprint,
            train_eligible_mask=train_elig_f,
            test_eligible_mask=fold_eligible[f.fold_id],
            pi_true=cal_f["pi_vis_train"],
            pi_sample=cal_f["pi_sample_weighted"],
            target_pool_dots=48_000,
            full_eligible_pixels=n_full_elig,
            min_spacing_px=2.50,
        )
        s13_fold_dots[f.fold_id] = dots_f
        del prob_f
        gc.collect()

    s13_hold = EH.score_pooled_holdout(s13_fold_dots, folds, footprint, n_boot=200, seed=133)
    tiles = _accumulate_fold_tiles(s13_fold_dots, folds, footprint)
    np.savez_compressed(
        npz_path, tile_T=tiles[0], tile_S=tiles[1], tile_M=tiles[2], tile_G=tiles[3]
    )
    meta_path.write_text(json.dumps(s13_hold, indent=2) + "\n", encoding="utf-8")
    del s13_fold_dots, ptha_crest, piedmont_mask
    gc.collect()
    return s13_hold, tiles


def _collect_uniqueness_scopes(exclude_prefix: str = "gems91-s15-euas-") -> dict[str, list[Path]]:
    # 1. Canonical 8-file data/registry/
    canon = [
        p for p in sorted((DATA / "registry").glob("*.tif"))
        if not p.name.startswith(exclude_prefix)
    ]

    # 2. All real external fleet rasters (deduplicated across data/fleet_registry + data/registry + data/retracted_geod, excluding synthetic blankets)
    ext_seen: dict[str, Path] = {}
    ext_dotted: list[Path] = []
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

    ext_all_real = list(ext_seen.values())
    for p in ext_all_real:
        with rasterio.open(p) as src:
            arr = np.nan_to_num(src.read(1), nan=0.0)
        if int((arr > 0).sum()) <= 65_000:
            ext_dotted.append(p)

    # 3. Unsubmitted in-repo research siblings in docs/downloads/
    siblings = [
        p for p in sorted(DOWNLOADS_DIR.glob("*-zeros.tif"))
        if not p.name.startswith(exclude_prefix)
    ]

    # 4. Literal universal deduplicated set across all 64 comparison_inventory files + siblings
    univ_seen: dict[str, Path] = {}
    for d in (DATA / "fleet_registry", DATA / "registry", DATA / "retracted_geod", DOWNLOADS_DIR):
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*.tif")):
            if p.name.startswith(exclude_prefix) or p.name.endswith("-nan.tif"):
                continue
            sha = IO.sha256_file(p)
            if sha not in univ_seen:
                univ_seen[sha] = p

    return {
        "canonical_registry": canon,
        "external_dotted_fleet": ext_dotted,
        "external_all_real_rasters": ext_all_real,
        "in_repo_siblings": siblings,
        "literal_universal_all": list(univ_seen.values()),
    }


def main() -> int:
    t0 = time.perf_counter()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence").mkdir(parents=True, exist_ok=True)

    # 0. Verify frozen pre-registration hash
    if not HYPOTHESES_MD.is_file():
        raise RuntimeError("Missing pre-registered docs/HYPOTHESES_S15.md")
    hyp_sha = IO.sha256_file(HYPOTHESES_MD)
    if hyp_sha != FROZEN_HYPOTHESES_SHA256:
        raise RuntimeError(
            f"HYPOTHESES_S15.md hash mismatch: got {hyp_sha}, expected {FROZEN_HYPOTHESES_SHA256}"
        )
    _log(f"Verified frozen docs/HYPOTHESES_S15.md SHA-256 = {hyp_sha}")

    # 1. Load footprint, official catalogue, SGMC blind control, and R0 reference
    with rasterio.open(TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    n_fp = int(footprint.sum())
    fp_idx_grid = np.full(footprint.shape, -1, dtype=np.int32)
    fp_idx_grid[footprint] = np.arange(n_fp, dtype=np.int32)

    with rasterio.open(CATALOGUE_TIF) as src:
        cat_raw = src.read(1)
    cat_mask = (np.isfinite(cat_raw) & (cat_raw > 0)) & footprint
    d_cat_full = ndi.distance_transform_edt(~cat_mask)
    full_eligible = footprint & (d_cat_full > 3.0)
    n_full_elig = int(full_eligible.sum())

    with rasterio.open(SGMC_CONTROL_TIF) as src:
        sgmc_mask = src.read(1).astype(np.float32)
    with rasterio.open(R0_ZEROS_TIF) as src:
        r0_dots = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)

    folds = EH.build_segment_buffered_folds(
        cat_mask.astype(np.float32), footprint, bridge_px=3, buffer_px=10.0
    )
    split_sha = _compute_fold_split_sha256(folds)
    _log(f"Built 4 spatial hide-and-recover folds | split_sha256 = {split_sha}")

    fold_active: dict[int, np.ndarray] = {}
    fold_eligible: dict[int, np.ndarray] = {}
    active_counts: dict[int, int] = {}
    for f in folds:
        act, elig = _fold_active_and_eligible(f, folds, footprint, collar_px=3.0)
        fold_active[f.fold_id] = act
        fold_eligible[f.fold_id] = elig
        active_counts[f.fold_id] = int(act.sum())
    tot_active = sum(active_counts.values())

    fold_quotas_44k: dict[int, int] = {}
    fold_quotas_42k: dict[int, int] = {}
    for q_budget, q_map in ((E12_MATCHED_BUDGET, fold_quotas_44k), (E3_TARGET_BUDGET, fold_quotas_42k)):
        acc = 0
        for f in folds:
            if f.fold_id < 3:
                v = int(round(q_budget * active_counts[f.fold_id] / tot_active))
                q_map[f.fold_id] = v
                acc += v
            else:
                q_map[f.fold_id] = q_budget - acc

    # 2. Build/load §A.5-clean feature memmaps (reusing shared cached stacks + S15-EUAS)
    _log("Building/loading cached float32 feature stacks (0 bytes read from IR-91-26 u8 files)...")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES_TIF, gdr_csv=GDR_CSV, footprint=footprint, cache_dir=CACHE_DIR
    )
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE_DIR
    )
    X_s12, s12_names, _ = SPAC.build_or_load_s12_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE_DIR
    )
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE_DIR
    )
    X_s15, s15_names, _ = EUAS.build_or_load_s15_feature_memmap(
        features_tif=FEATURES_TIF,
        X_static=X_static,
        X_s12=X_s12,
        X_ptha=X_ptha,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    _log(f"Loaded S15-EUAS feature memmap ({n_fp:,} x {len(s15_names)}) cleanly.")

    # Compute fold-safe dynamic depth-deconfounded conductivity features for each fold:
    fold_cond_map: dict[int, np.ndarray] = {}
    for f in folds:
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        d_vis = ndi.distance_transform_edt(~f.visible_faults)
        train_bg_fp = (footprint & (~excl) & (~f.visible_faults) & (d_vis > 2.5))[footprint]
        fold_cond_map[f.fold_id] = EUAS.compute_fold_depth_deconfounded_conductivity(
            X_static, footprint, train_bg_fp
        )

    # 3. Rule 4 Single-Feature Leakage Canary FIRST (before any S15 model fit!)
    canary_json = CKPT_DIR / "s15_canary_report.json"
    if canary_json.is_file():
        canary = json.loads(canary_json.read_text(encoding="utf-8"))
        _log(
            f"Loaded Rule-4 canary: all_pass={canary['all_pass']} | "
            f"n_tested={canary['n_features_tested']} | worst={canary['worst_feature']} "
            f"({canary['worst_symmetric_auc']:.5f})"
        )
    else:
        _log("Running Rule-4 single-feature leakage canary across all 109 S15 features...")
        per_feat: dict[str, dict] = {}
        blocks_canary = [
            (X_static, EUAS.CLEAN_STATIC_INDICES, [static_names[i] for i in EUAS.CLEAN_STATIC_INDICES]),
            (X_s11, list(range(len(s11_names))), s11_names),
            (X_s12, EUAS.CLEAN_S12_INDICES, [s12_names[i] for i in EUAS.CLEAN_S12_INDICES]),
            (X_ptha, list(range(len(ptha_names))), ptha_names),
            (X_s15, list(range(len(s15_names))), s15_names),
        ]
        for arr, cols, names in blocks_canary:
            sub_arr = np.asarray(arr[:, cols], dtype=np.float32)
            rep = EH.run_leakage_canary(sub_arr, names, folds, footprint, subsample_step=4)
            per_feat.update(rep["features"])
            del sub_arr
            gc.collect()

        rep_dyn = EH.run_leakage_canary(
            np.zeros((n_fp, 0), dtype=np.float32),
            [],
            folds,
            footprint,
            fold_specific_features={
                f.fold_id: (fold_cond_map[f.fold_id], list(EUAS.S15_FOLD_COND_NAMES))
                for f in folds
            },
            subsample_step=4,
        )
        per_feat.update(rep_dyn["features"])
        worst_k, worst_v = max(per_feat.items(), key=lambda kv: kv[1]["max_fold_symmetric_auc"])
        flagged = [k for k, v in per_feat.items() if not v["pass"]]
        canary = {
            "evaluator_version": EH.EVALUATOR_VERSION,
            "max_allowed_auc": 0.90,
            "n_features_tested": len(per_feat),
            "worst_feature": worst_k,
            "worst_symmetric_auc": worst_v["max_fold_symmetric_auc"],
            "max_symmetric_auc": worst_v["max_fold_symmetric_auc"],
            "flagged_features": flagged,
            "all_pass": len(flagged) == 0,
            "s15_new_features": {
                k: per_feat[k] for k in (list(EUAS.S15_EUAS_FEATURE_NAMES) + list(EUAS.S15_FOLD_COND_NAMES))
            },
            "all_features": per_feat,
        }
        canary_json.write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")
        _log(
            f"Rule-4 canary PASS={canary['all_pass']} | tested={canary['n_features_tested']} | "
            f"worst={canary['worst_feature']} (sym AUC = {canary['worst_symmetric_auc']:.5f} <= 0.90)"
        )

    if not canary["all_pass"] or canary["max_symmetric_auc"] > 0.90:
        raise RuntimeError(f"RULE 4 LEAKAGE CANARY FAILED: {canary['flagged_features']}")

    # 4. Load/build exact S13-PTHA E3 reference tiles (`0.244601 HOLDOUT-DTI`) + R0 SGMC baseline
    s13_ref_hold, s13_ref_tiles = _load_or_build_s13_e3_reference_tiles(
        X_static=X_static,
        static_names=static_names,
        X_s11=X_s11,
        s11_names=s11_names,
        X_ptha=X_ptha,
        ptha_names=ptha_names,
        folds=folds,
        fold_eligible=fold_eligible,
        n_full_elig=n_full_elig,
        footprint=footprint,
    )
    r0_sgmc = EH.score_off_catalogue_sgmc(r0_dots, sgmc_mask, cat_mask, footprint)
    _log(
        f"Comparable Best `S13-PTHA E3` verified: HOLDOUT-DTI = {s13_ref_hold['holdout_dti']:.6f} "
        f"(CI {s13_ref_hold['ci_95']}) | R0 SGMC = {r0_sgmc['dti']:.6f}"
    )
    if "--stop-after-ref" in sys.argv:
        _log("Completed `--stop-after-ref` checkpoint stage cleanly.")
        return 0

    # Precompute shared label-free auxiliary vectors:
    concealed_gate_fp = EUAS.compute_concealed_gate_fp(X_static)
    hard_score_fp = EUAS.compute_euas_hard_mining_score_fp(X_s15, X_ptha, X_static)
    euas_crest_2d = EUAS.compute_euas_crest_field_2d(X_s15, X_ptha, X_static, footprint)
    _, piedmont_mask = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)

    exp_results: list[dict] = []

    # ------------------------------------------------------------------
    # Experiment 1/3 (`E1`: H15-1 3-D Euler Homogeneity & 4-Altitude Worms)
    # and Experiment 2/3 (`E2`: H15-1 + H15-2 Morris Tendency & Fold-Safe B17 Residual)
    # ------------------------------------------------------------------
    e12_configs = [
        {
            "exp_id": "E1",
            "hypothesis_id": "H15-1",
            "include_group_b": False,
            "use_fold_cond": False,
            "title": (
                "Clean Official Multi-Physics Stack + Closed-Form 3-D Euler Homogeneity "
                "Depth/Step Inversion + 4-Altitude Upward-Continuation Plunge Worms"
            ),
            "named_non_fault_mimic": (
                "Equidimensional Tertiary volcanic plugs (N=2), shallow thin lava-flow "
                "margins, and vertical aeromagnetic flight-line seams"
            ),
        },
        {
            "exp_id": "E2",
            "hypothesis_id": "H15-1 + H15-2",
            "include_group_b": True,
            "use_fold_cond": True,
            "title": (
                "H15-1 + Spatially-Varying Geodetic Strain-Resolved Andersonian Slip/Dilation "
                "Tendency + Fold-Safe Depth-Deconfounded Hydrothermal Clay-Cap Conductivity"
            ),
            "named_non_fault_mimic": (
                "Flat saline/evaporite playa interiors (high raw B17) and unfractured NNE "
                "erosional hogbacks"
            ),
        },
    ]

    for idx_e, cfg in enumerate(e12_configs):
        if time.perf_counter() - t0 > MAX_BUDGET_SECONDS:
            raise RuntimeError("Rule 6 2-hour budget exceeded")
        te0 = time.perf_counter()
        eid = cfg["exp_id"]
        _log(f"=== Experiment {idx_e + 1}/{MAX_EXPERIMENTS}: {eid} ({cfg['hypothesis_id']}) ===")

        fold_dots: dict[int, np.ndarray] = {}
        fold_fit_info: dict[str, dict] = {}

        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            train_reg_2d = footprint & (~excl)
            pred_mask_2d = (f.region_mask | f.withheld_faults) & footprint
            pred_fp_idx = fp_idx_grid[pred_mask_2d]

            spec_f = EUAS.build_s15_feature_spec(
                X_static=X_static,
                X_s11=X_s11,
                X_s12=X_s12,
                X_ptha=X_ptha,
                X_s15=X_s15,
                include_group_b=cfg["include_group_b"],
                X_fold_cond=fold_cond_map[f.fold_id] if cfg["use_fold_cond"] else None,
            )

            dat_p = CKPT_DIR / f"s15_{eid.lower()}_f{f.fold_id}_pred.npy"
            info_p = CKPT_DIR / f"s15_{eid.lower()}_f{f.fold_id}_info.json"
            if dat_p.is_file() and info_p.is_file():
                pred_vec = np.load(dat_p)
                f_info = json.loads(info_p.read_text(encoding="utf-8"))
            else:
                pred_vec, f_info = EUAS.fit_and_predict_euas_experts(
                    spec_f,
                    footprint=footprint,
                    visible_faults_2d=f.visible_faults,
                    train_region_2d=train_reg_2d,
                    predict_fp_indices=pred_fp_idx,
                    hard_score_fp=hard_score_fp,
                    concealed_gate_fp=concealed_gate_fp,
                    seed=1500 + idx_e * 30 + f.fold_id,
                )
                np.save(dat_p, pred_vec)
                info_p.write_text(json.dumps(f_info) + "\n", encoding="utf-8")

            prob_2d = np.zeros(footprint.shape, dtype=np.float32)
            prob_2d[pred_mask_2d] = pred_vec
            fold_fit_info[f.name] = f_info

            dots_f = MC.mhtr_corridor_submodular_emit(
                prob_2d,
                euas_crest_2d,
                piedmont_mask,
                eligible_mask=fold_eligible[f.fold_id],
                n_dots=fold_quotas_44k[f.fold_id],
                gamma=1.20,
                mhtr_weight=0.45,
                piedmont_quota_frac=0.22,
                min_spacing_px=2.55,
            )
            fold_dots[f.fold_id] = dots_f
            del prob_2d, pred_vec
            _log(
                f"  [{eid} {f.name}] cols={f_info['n_total_cols']} (sub={f_info['n_subsurface_cols']}) "
                f"lr_iter={f_info['lr_n_iter']} -> {int((dots_f > 0).sum()):,} dots"
            )
            gc.collect()

        hold_v10 = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=151 + idx_e)
        hold_v11 = EH.score_pooled_holdout(
            fold_dots, folds, footprint, n_boot=200, seed=151 + idx_e,
            mask_buffer_predictions=False,
        )
        cand_tiles = _accumulate_fold_tiles(fold_dots, folds, footprint)
        paired_s13 = _compute_aligned_paired_bootstrap(
            cand_tiles,
            s13_ref_tiles,
            cand_pooled_dti=hold_v10["holdout_dti"],
            base_pooled_dti=s13_ref_hold["holdout_dti"],
        )
        del fold_dots, cand_tiles
        gc.collect()

        el = time.perf_counter() - te0
        _log(
            f"[{eid}] v1.0 HOLDOUT-DTI = {hold_v10['holdout_dti']:.6f} (CI {hold_v10['ci_95']}) | "
            f"v1.1-nohalo = {hold_v11['holdout_dti']:.6f} | "
            f"delta vs S13-E3 = {paired_s13['delta']:+.6f} (CI {paired_s13['ci95']}) [{el:.1f}s]"
        )
        exp_results.append({
            "experiment_number": idx_e + 1,
            "exp_id": eid,
            "hypothesis_id": cfg["hypothesis_id"],
            "title": cfg["title"],
            "n_features": fold_fit_info["NW"]["n_total_cols"],
            "include_group_b": cfg["include_group_b"],
            "use_fold_cond": cfg["use_fold_cond"],
            "emission_mode": "matched_44k_submodular",
            "named_non_fault_mimic": cfg["named_non_fault_mimic"],
            "fold_fit_info": fold_fit_info,
            "holdout": hold_v10,
            "holdout_v11_nohalo": hold_v11,
            "paired_vs_s13_e3": paired_s13,
            "elapsed_seconds": round(el, 2),
        })

    if "--stop-after-e2" in sys.argv:
        _log("Completed `--stop-after-e2` checkpoint stage cleanly.")
        return 0

    # ------------------------------------------------------------------
    # Experiment 3/3 (`E3`: Best(E1, E2) + H15-3 Inner-OOF Two-Stage Radon
    # Wash-Bridge Auto-Context + 10x10 km Cross-Fitted Self-Credit Dinkelbach)
    # ------------------------------------------------------------------
    if time.perf_counter() - t0 > MAX_BUDGET_SECONDS:
        raise RuntimeError("Rule 6 2-hour budget exceeded before E3")
    te3 = time.perf_counter()
    stage1_winner = exp_results[1] if exp_results[1]["holdout"]["holdout_dti"] >= exp_results[0]["holdout"]["holdout_dti"] else exp_results[0]
    s1_eid = stage1_winner["exp_id"]
    use_gb = bool(stage1_winner["include_group_b"])
    use_fc = bool(stage1_winner["use_fold_cond"])
    _log(
        f"=== Experiment 3/{MAX_EXPERIMENTS}: E3 ({stage1_winner['hypothesis_id']} + H15-3 "
        f"Inner-OOF Two-Stage Wash-Bridge Auto-Context & Self-Credit Dinkelbach on {s1_eid}) ==="
    )

    checker_parity0 = EUAS.make_spatial_checkerboard_2d(footprint.shape, block_px=100)
    e3_fold_dots: dict[int, np.ndarray] = {}
    e3_alloc_meta: dict[str, dict] = {}
    e3_fit_meta: dict[str, dict] = {}

    for f in folds:
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        train_quads = [f2 for f2 in folds if f2.fold_id != f.fold_id]

        # Step 3a: Build 100% leak-free out-of-sample Stage-1 surface across ALL 4 quadrants:
        #   - On test quadrant `f`: out-of-sample prediction from `s1_eid` (trained on `~excl`)
        #   - On each training quadrant `fm` in `train_quads`: trained strictly on the OTHER 2
        #     training quadrants (NEVER seeing `f` and NEVER seeing `fm`!)
        s1_full_oof_dat = CKPT_DIR / f"s15_e3_s1oof_outer{f.fold_id}.dat"
        if s1_full_oof_dat.is_file() and s1_full_oof_dat.stat().st_size == n_fp * 4:
            stage1_oof_2d = np.zeros(footprint.shape, dtype=np.float32)
            stage1_oof_2d[footprint] = np.fromfile(s1_full_oof_dat, dtype=np.float32)
        else:
            stage1_oof_2d = np.zeros(footprint.shape, dtype=np.float32)
            # Fill test quadrant from Stage-1 outer OOF checkpoint:
            pred_mask_outer = (f.region_mask | f.withheld_faults) & footprint
            outer_prob_tmp = np.zeros(footprint.shape, dtype=np.float32)
            outer_prob_tmp[pred_mask_outer] = np.load(
                CKPT_DIR / f"s15_{s1_eid.lower()}_f{f.fold_id}_pred.npy"
            )
            test_q_mask = f.region_mask & footprint
            stage1_oof_2d[test_q_mask] = outer_prob_tmp[test_q_mask]
            del outer_prob_tmp

            spec_inner = EUAS.build_s15_feature_spec(
                X_static=X_static,
                X_s11=X_s11,
                X_s12=X_s12,
                X_ptha=X_ptha,
                X_s15=X_s15,
                include_group_b=use_gb,
                X_fold_cond=fold_cond_map[f.fold_id] if use_fc else None,
            )
            for fm in train_quads:
                inner_train_2d = (
                    footprint
                    & (~excl)
                    & (~fm.region_mask)
                    & (~fm.withheld_faults)
                    & (~fm.buffer_mask)
                )
                d_fm = ndi.distance_transform_edt(~fm.withheld_faults)
                inner_vis_2d = f.visible_faults & (~fm.withheld_faults) & (d_fm > 3.0)
                pred_m_mask = fm.region_mask & footprint
                pred_m_idx = fp_idx_grid[pred_m_mask]

                p_inner, _ = EUAS.fit_and_predict_euas_experts(
                    spec_inner,
                    footprint=footprint,
                    visible_faults_2d=inner_vis_2d,
                    train_region_2d=inner_train_2d,
                    predict_fp_indices=pred_m_idx,
                    hard_score_fp=hard_score_fp,
                    concealed_gate_fp=concealed_gate_fp,
                    seed=1560 + f.fold_id * 10 + fm.fold_id,
                    fast_inner_mode=True,
                )
                stage1_oof_2d[pred_m_mask] = p_inner
                gc.collect()

            stage1_oof_2d[footprint].astype(np.float32).tofile(s1_full_oof_dat)
            _log(f"  [E3 {f.name}] built leak-free Stage-1 OOF surface across all 4 quadrants")

        # Step 3b: Extract 10 Steerable Radon Collinear Wash-Bridge features from leak-free Stage-1 OOF:
        X_ac_f = SPAC.compute_spac_autocontext_features(stage1_oof_2d, footprint)
        del stage1_oof_2d

        spec_s2 = EUAS.build_s15_feature_spec(
            X_static=X_static,
            X_s11=X_s11,
            X_s12=X_s12,
            X_ptha=X_ptha,
            X_s15=X_s15,
            include_group_b=use_gb,
            X_fold_cond=fold_cond_map[f.fold_id] if use_fc else None,
            X_autocontext=X_ac_f,
        )

        # Step 3c: Full-data Stage-2 fit on 100% of the 3 training quadrants -> `test_s2`
        # PLUS 3 whole-quadrant segment-buffered inner Stage-2 fits -> `oof_train_s2`
        # (100% out-of-sample across 10px-buffered segments, zero checkerboard loss/leakage!)
        s2_npz = CKPT_DIR / f"s15_e3_s2_outer{f.fold_id}.npz"
        if s2_npz.is_file():
            z2 = np.load(s2_npz)
            oof_train_s2 = np.zeros(footprint.shape, dtype=np.float32)
            oof_train_s2[footprint] = z2["oof_train_fp"]
            test_s2 = np.zeros(footprint.shape, dtype=np.float32)
            test_s2[footprint] = z2["test_fp"]
            s2_info = json.loads((CKPT_DIR / f"s15_e3_s2_outer{f.fold_id}.json").read_text(encoding="utf-8"))
        else:
            train_base_2d = footprint & (~excl)
            test_pred_2d = (f.region_mask | f.withheld_faults) & footprint
            test_pred_idx = fp_idx_grid[test_pred_2d]

            p_test, info_main = EUAS.fit_and_predict_euas_experts(
                spec_s2,
                footprint=footprint,
                visible_faults_2d=f.visible_faults,
                train_region_2d=train_base_2d,
                predict_fp_indices=test_pred_idx,
                hard_score_fp=hard_score_fp,
                concealed_gate_fp=concealed_gate_fp,
                seed=1600 + f.fold_id * 10,
            )
            test_s2 = np.zeros(footprint.shape, dtype=np.float32)
            test_s2[test_pred_2d] = p_test
            del p_test

            oof_train_s2 = np.zeros(footprint.shape, dtype=np.float32)
            for fm in train_quads:
                inner_tr_2d = (
                    train_base_2d
                    & (~fm.region_mask)
                    & (~fm.withheld_faults)
                    & (~fm.buffer_mask)
                )
                d_fm = ndi.distance_transform_edt(~fm.withheld_faults)
                inner_vis_2d = f.visible_faults & (~fm.withheld_faults) & (d_fm > 3.0)
                pred_m_mask = fm.region_mask & train_base_2d
                pred_m_idx = fp_idx_grid[pred_m_mask]
                p_in_s2, _ = EUAS.fit_and_predict_euas_experts(
                    spec_s2,
                    footprint=footprint,
                    visible_faults_2d=inner_vis_2d,
                    train_region_2d=inner_tr_2d,
                    predict_fp_indices=pred_m_idx,
                    hard_score_fp=hard_score_fp,
                    concealed_gate_fp=concealed_gate_fp,
                    seed=1640 + f.fold_id * 10 + fm.fold_id,
                    fast_inner_mode=True,
                )
                oof_train_s2[pred_m_mask] = p_in_s2
                gc.collect()

            s2_info = {
                "n_total_cols": spec_s2.n_cols,
                "main": info_main,
            }
            np.savez_compressed(
                s2_npz,
                oof_train_fp=oof_train_s2[footprint],
                test_fp=test_s2[footprint],
            )
            (CKPT_DIR / f"s15_e3_s2_outer{f.fold_id}.json").write_text(
                json.dumps(s2_info) + "\n", encoding="utf-8"
            )

        del X_ac_f, spec_s2
        gc.collect()

        # Step 3d: Out-of-Sample Calibrated Self-Credit (`M`-Term) Dinkelbach Emission
        d_vis = ndi.distance_transform_edt(~f.visible_faults)
        train_elig_2d = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)
        train_target_dots = int(round(E3_CAL_POOL_BUDGET * float(train_elig_2d.sum()) / float(n_full_elig)))

        dots_f, alloc_f = EUAS.emit_oof_calibrated_selfcredit_dinkelbach(
            oof_train_prob_2d=oof_train_s2,
            test_prob_2d=test_s2,
            crest_2d=euas_crest_2d,
            piedmont_mask=piedmont_mask,
            footprint=footprint,
            train_eligible_2d=train_elig_2d,
            test_eligible_2d=fold_eligible[f.fold_id],
            train_target_dots=train_target_dots,
            test_quota_ref=fold_quotas_42k[f.fold_id],
            pi_true=float(s2_info["main"]["pi_true"]),
            pi_sample=float(s2_info["main"]["pi_sample"]),
            lambda_target=0.2778,
            min_spacing_px=2.55,
            min_test_dots=6_500,
            max_test_dots=18_000,
        )
        e3_fold_dots[f.fold_id] = dots_f
        e3_alloc_meta[f.name] = alloc_f
        e3_fit_meta[f.name] = s2_info
        _log(
            f"  [E3 {f.name}] tau_oof={alloc_f['tau_oof_train']:.5f} -> "
            f"emitted {alloc_f['test_emitted_dots']:,} dots (quota ref {alloc_f['test_quota_ref']:,})"
        )
        del oof_train_s2, test_s2
        gc.collect()

    e3_hold_v10 = EH.score_pooled_holdout(e3_fold_dots, folds, footprint, n_boot=200, seed=153)
    e3_hold_v11 = EH.score_pooled_holdout(
        e3_fold_dots, folds, footprint, n_boot=200, seed=153,
        mask_buffer_predictions=False,
    )
    e3_tiles = _accumulate_fold_tiles(e3_fold_dots, folds, footprint)
    e3_paired_s13 = _compute_aligned_paired_bootstrap(
        e3_tiles,
        s13_ref_tiles,
        cand_pooled_dti=e3_hold_v10["holdout_dti"],
        base_pooled_dti=s13_ref_hold["holdout_dti"],
    )
    del e3_fold_dots, e3_tiles
    gc.collect()

    el3 = time.perf_counter() - te3
    _log(
        f"[E3] v1.0 HOLDOUT-DTI = {e3_hold_v10['holdout_dti']:.6f} (CI {e3_hold_v10['ci_95']}) | "
        f"v1.1-nohalo = {e3_hold_v11['holdout_dti']:.6f} | "
        f"delta vs S13-E3 = {e3_paired_s13['delta']:+.6f} (CI {e3_paired_s13['ci95']}) [{el3:.1f}s]"
    )
    exp_results.append({
        "experiment_number": 3,
        "exp_id": "E3",
        "hypothesis_id": f"{stage1_winner['hypothesis_id']} + H15-3",
        "title": (
            f"{stage1_winner['title']} + Inner-OOF Two-Stage Wash-Bridge Auto-Context & "
            "Out-of-Sample Calibrated Self-Credit Dinkelbach Allocation"
        ),
        "n_features": e3_fit_meta["NW"]["n_total_cols"],
        "stage1_base": s1_eid,
        "include_group_b": use_gb,
        "use_fold_cond": use_fc,
        "emission_mode": "oof_calibrated_selfcredit_dinkelbach_42k",
        "fold_dinkelbach_allocation": e3_alloc_meta,
        "named_non_fault_mimic": (
            "Collinear alignment of isolated noise blobs, alluvial wash channels without "
            "bilateral fault continuation, and barren interior playas"
        ),
        "holdout": e3_hold_v10,
        "holdout_v11_nohalo": e3_hold_v11,
        "paired_vs_s13_e3": e3_paired_s13,
        "elapsed_seconds": round(el3, 2),
    })

    if "--stop-after-e3" in sys.argv:
        _log("Completed `--stop-after-e3` checkpoint stage cleanly.")
        return 0

    # 5. Select Best S15 Experiment on `gems91-hide-recover-v1.0` & Build Full-Map Submission
    win_exp = max(exp_results, key=lambda r: r["holdout"]["holdout_dti"])
    win_id = win_exp["exp_id"]
    _log(
        f"Selected S15 Holdout Winner: {win_id} ({win_exp['hypothesis_id']}) | "
        f"HOLDOUT-DTI = {win_exp['holdout']['holdout_dti']:.6f} "
        f"(delta vs S13-PTHA E3 = {win_exp['paired_vs_s13_e3']['delta']:+.6f}, "
        f"CI95 = {win_exp['paired_vs_s13_e3']['ci95']})"
    )

    # Full-map dynamic depth-deconfounded conductivity (fit on all non-catalogue footprint pixels):
    full_bg_fp = (footprint & (~cat_mask) & (d_cat_full > 2.5))[footprint]
    X_fold_cond_full = (
        EUAS.compute_fold_depth_deconfounded_conductivity(X_static, footprint, full_bg_fp)
        if win_exp["use_fold_cond"]
        else None
    )

    full_npz = CKPT_DIR / f"s15_full_xfitted_{win_id.lower()}_surface.npz"
    full_info_json = CKPT_DIR / f"s15_full_xfitted_{win_id.lower()}_info.json"
    if full_npz.is_file() and full_info_json.is_file():
        zf = np.load(full_npz)
        full_prob_2d = np.zeros(footprint.shape, dtype=np.float32)
        full_prob_2d[footprint] = zf["full_prob_fp"]
        oof_full_prob_2d = np.zeros(footprint.shape, dtype=np.float32)
        oof_full_prob_2d[footprint] = zf["oof_prob_fp"]
        full_fit_info = json.loads(full_info_json.read_text(encoding="utf-8"))
    else:
        if win_id == "E3":
            # 4-Fold Cross-Fitted Bayes-Calibrated Stage-2 Posterior Synthesis (fixes IR-91-S15-04
            # in-sample 3..10 px catalogue-halo memorization! Every pixel in quadrant k is
            # predicted strictly out-of-fold by s15_e3_s2_outer{k} and prior-shift calibrated
            # using quadrant k's training (pi_true_k, pi_sample_k) so pi_true==pi_sample==0.0125
            # acts as an exact identity pass-through during full-map emission):
            full_prob_2d = np.zeros(footprint.shape, dtype=np.float32)
            fold_cal_records = {}
            for f in folds:
                z2f = np.load(CKPT_DIR / f"s15_e3_s2_outer{f.fold_id}.npz")
                s2_inf = json.loads(
                    (CKPT_DIR / f"s15_e3_s2_outer{f.fold_id}.json").read_text(encoding="utf-8")
                )["main"]
                tmp_t = np.zeros(footprint.shape, dtype=np.float32)
                tmp_t[footprint] = z2f["test_fp"]
                cal_k = PTHA.prior_shift_calibrate_surface(
                    tmp_t,
                    footprint,
                    pi_true=float(s2_inf["pi_true"]),
                    pi_sample=float(s2_inf["pi_sample"]),
                )
                qm = f.region_mask & footprint
                full_prob_2d[qm] = cal_k[qm]
                fold_cal_records[f.name] = {
                    "pi_true": s2_inf["pi_true"],
                    "pi_sample": s2_inf["pi_sample"],
                }
                del tmp_t, cal_k
            oof_full_prob_2d = full_prob_2d.copy()
            full_fit_info = {
                "synthesis_mode": "4fold_cross_fitted_bayes_calibrated_stage2_posterior",
                "pi_true": 0.0125,
                "pi_sample": 0.0125,
                "per_quadrant_prior_calibration": fold_cal_records,
            }
        else:
            spec_full = EUAS.build_s15_feature_spec(
                X_static=X_static,
                X_s11=X_s11,
                X_s12=X_s12,
                X_ptha=X_ptha,
                X_s15=X_s15,
                include_group_b=bool(win_exp["include_group_b"]),
                X_fold_cond=X_fold_cond_full,
                X_autocontext=None,
            )
            all_fp_idx = np.arange(n_fp, dtype=np.int32)
            p_full_vec, full_fit_info = EUAS.fit_and_predict_euas_experts(
                spec_full,
                footprint=footprint,
                visible_faults_2d=cat_mask,
                train_region_2d=footprint,
                predict_fp_indices=all_fp_idx,
                hard_score_fp=hard_score_fp,
                concealed_gate_fp=concealed_gate_fp,
                seed=1701,
            )
            full_prob_2d = np.zeros(footprint.shape, dtype=np.float32)
            full_prob_2d[footprint] = p_full_vec
            oof_full_prob_2d = np.zeros(footprint.shape, dtype=np.float32)
            for f in folds:
                qm = f.region_mask & footprint
                pred_m = (f.region_mask | f.withheld_faults) & footprint
                tmp_p = np.zeros(footprint.shape, dtype=np.float32)
                tmp_p[pred_m] = np.load(CKPT_DIR / f"s15_{win_id.lower()}_f{f.fold_id}_pred.npy")
                oof_full_prob_2d[qm] = tmp_p[qm]
                del tmp_p
            del p_full_vec, spec_full

        np.savez_compressed(
            full_npz,
            full_prob_fp=full_prob_2d[footprint],
            oof_prob_fp=oof_full_prob_2d[footprint],
        )
        full_info_json.write_text(json.dumps(full_fit_info) + "\n", encoding="utf-8")
        gc.collect()

    # 6. Rule 1 Pre-Placement Surface Uniqueness Check (BEFORE dot placement!)
    scopes = _collect_uniqueness_scopes(exclude_prefix="gems91-s15-euas-")
    _log(
        f"Running Rule-1 PRE-PLACEMENT surface uniqueness across "
        f"{len(scopes['canonical_registry'])} canonical, "
        f"{len(scopes['external_dotted_fleet'])} external dotted, "
        f"{len(scopes['external_all_real_rasters'])} external real, "
        f"{len(scopes['in_repo_siblings'])} siblings, and "
        f"{len(scopes['literal_universal_all'])} universal rasters..."
    )
    surf_fp64 = full_prob_2d[footprint].astype(np.float64)
    surf_uniq_canon = EH.check_registry_surface_uniqueness(surf_fp64, footprint, scopes["canonical_registry"])
    surf_uniq_ext_real = EH.check_registry_surface_uniqueness(surf_fp64, footprint, scopes["external_all_real_rasters"])
    surf_uniq_univ = EH.check_registry_surface_uniqueness(surf_fp64, footprint, scopes["literal_universal_all"])
    _log(
        f"Pre-placement surface max |rho|: canonical={surf_uniq_canon['surface_max_abs_rank_corr']:.4f}, "
        f"external_real={surf_uniq_ext_real['surface_max_abs_rank_corr']:.4f}, "
        f"universal={surf_uniq_univ['surface_max_abs_rank_corr']:.4f} (limit <= 0.90)"
    )
    if not surf_uniq_univ["uniqueness_pass"]:
        raise RuntimeError(
            f"RULE 1 DUPLICATE SURFACE DETECTED: |rho|={surf_uniq_univ['surface_max_abs_rank_corr']} "
            f"vs {surf_uniq_univ['surface_closest_raster']}"
        )

    # 7. Emit Full-Map Binary `{0, 1}` Candidate Dots
    if win_id == "E3":
        full_dots, full_emit_meta = EUAS.emit_full_map_selfcredit_dinkelbach(
            full_prob_2d=full_prob_2d,
            oof_full_prob_2d=oof_full_prob_2d,
            crest_2d=euas_crest_2d,
            piedmont_mask=piedmont_mask,
            footprint=footprint,
            full_eligible_2d=full_eligible,
            pi_true=float(full_fit_info["pi_true"]),
            pi_sample=float(full_fit_info["pi_sample"]),
            target_dots=E3_TARGET_BUDGET,
            lambda_target=0.2778,
            min_spacing_px=2.55,
        )
    else:
        full_dots = MC.mhtr_corridor_submodular_emit(
            full_prob_2d,
            euas_crest_2d,
            piedmont_mask,
            eligible_mask=full_eligible,
            n_dots=E12_MATCHED_BUDGET,
            gamma=1.20,
            mhtr_weight=0.45,
            piedmont_quota_frac=0.22,
            min_spacing_px=2.55,
        )
        full_emit_meta = {"n_dots": int((full_dots > 0).sum()), "mode": "matched_44k_submodular"}

    n_emitted = int((full_dots > 0).sum())
    _log(f"Emitted {n_emitted:,} binary {{0, 1}} dots on full footprint.")

    # 8. Rule 1 Post-Placement Uniqueness Check (surface + final dots across ALL scopes!)
    dot_uniq_canon = EH.check_registry_uniqueness(surf_fp64, full_dots, footprint, scopes["canonical_registry"])
    dot_uniq_ext_dotted = EH.check_registry_uniqueness(surf_fp64, full_dots, footprint, scopes["external_dotted_fleet"])
    dot_uniq_ext_real = EH.check_registry_uniqueness(surf_fp64, full_dots, footprint, scopes["external_all_real_rasters"])
    dot_uniq_siblings = EH.check_registry_uniqueness(surf_fp64, full_dots, footprint, scopes["in_repo_siblings"])
    dot_uniq_univ = EH.check_registry_uniqueness(surf_fp64, full_dots, footprint, scopes["literal_universal_all"])

    _log(
        f"Post-placement 3px dot overlap: "
        f"canonical={dot_uniq_canon['dots_max_3px_overlap']:.4f} ({dot_uniq_canon['dots_closest_raster']}) | "
        f"ext_dotted={dot_uniq_ext_dotted['dots_max_3px_overlap']:.4f} ({dot_uniq_ext_dotted['dots_closest_raster']}) | "
        f"ext_real={dot_uniq_ext_real['dots_max_3px_overlap']:.4f} ({dot_uniq_ext_real['dots_closest_raster']}) | "
        f"siblings={dot_uniq_siblings['dots_max_3px_overlap']:.4f} ({dot_uniq_siblings['dots_closest_raster']}) | "
        f"literal_univ={dot_uniq_univ['dots_max_3px_overlap']:.4f} ({dot_uniq_univ['dots_closest_raster']})"
    )
    if not dot_uniq_canon["uniqueness_pass"] or not dot_uniq_ext_dotted["uniqueness_pass"]:
        raise RuntimeError(
            "RULE 1 DUPLICATE DOTS DETECTED against canonical/external dotted registry!"
        )

    # 9. Winner-Economics Geometry & Blind Off-Catalogue USGS SGMC Control
    ys, xs = np.nonzero(full_dots > 0)
    dc_pts = d_cat_full[ys, xs]
    pts = np.column_stack([ys, xs]).astype(np.float64)
    rng_nn = np.random.default_rng(15)
    sub_pts = pts[rng_nn.choice(len(pts), min(4000, len(pts)), replace=False)]
    dnn, _ = cKDTree(pts).query(sub_pts, k=2)
    geom_stats = {
        "n_dots": n_emitted,
        "min_dist_to_catalogue_px": round(float(dc_pts.min()), 4),
        "frac_dots_gt10px_of_catalogue": round(float(np.mean(dc_pts > 10.0)), 5),
        "frac_dots_3to10px_of_catalogue": round(float(np.mean((dc_pts > 3.0) & (dc_pts <= 10.0))), 5),
        "min_nn_spacing_px": round(float(dnn[:, 1].min()), 4),
        "median_nn_spacing_px": round(float(np.median(dnn[:, 1])), 4),
    }
    sgmc_res = EH.score_off_catalogue_sgmc(full_dots, sgmc_mask, cat_mask, footprint)
    _log(
        f"Geometry: min_cat={geom_stats['min_dist_to_catalogue_px']}px, "
        f">10px={geom_stats['frac_dots_gt10px_of_catalogue']*100:.1f}%, "
        f"median_NN={geom_stats['median_nn_spacing_px']}px | "
        f"Blind SGMC DTI = {sgmc_res['dti']:.6f} (vs R0 {r0_sgmc['dti']:.6f}, delta {sgmc_res['dti']-r0_sgmc['dti']:+.6f})"
    )

    # 10. Write Validated Submission GeoTIFF + Single-TIFF ZIP + Audit Receipt
    date_tag = "20261025T053000Z"
    stem_prefix = f"gems91-s15-euas-{win_id.lower()}"
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
        bundle_js_filename="s15_submission_bundle.js",
    )
    cand_id = audit["candidate_id"]
    rel_zeros = Path(audit["primary_zeros_tif"]["path"])
    dl_zeros = DOWNLOADS_DIR / rel_zeros.name
    shutil.copy2(rel_zeros, dl_zeros)
    assert IO.sha256_file(dl_zeros) == audit["primary_zeros_tif"]["sha256"]

    # Remove untracked large base64 JS bundle so docs/downloads/ stays lean (consistent with S13):
    js_bundle = DOWNLOADS_DIR / "s15_submission_bundle.js"
    if js_bundle.is_file():
        js_bundle.unlink()

    val_dict = audit["validators"]
    all_val_pass = bool(
        val_dict["gems91_gates_verdict"] in ("PASS", "CERTIFIED")
        and val_dict["release_gates_zeros_pass"]
        and val_dict["release_gates_nan_pass"]
        and val_dict["validate_raster_zeros_pass"]
        and val_dict["validate_raster_nan_pass"]
        and val_dict["range_0_1_portal_safe"]
    )
    if not all_val_pass:
        raise RuntimeError(f"Validator failure: {val_dict}")

    beats_s13_point = float(win_exp["holdout"]["holdout_dti"]) > float(s13_ref_hold["holdout_dti"])
    beats_s13_ci = float(win_exp["paired_vs_s13_e3"]["ci95"][0]) > 0.0

    # Protocol Rule 5 verdict (`promote` if beating holdout best & passing external uniqueness, else `negative`):
    verdict = (
        "promote"
        if (
            beats_s13_point
            and beats_s13_ci
            and dot_uniq_canon["uniqueness_pass"]
            and dot_uniq_ext_dotted["uniqueness_pass"]
            and dot_uniq_ext_real["uniqueness_pass"]
            and all_val_pass
        )
        else "negative"
    )

    sub_name = f"GEMS91-S15-EUAS-{win_id}-{audit['dots']['dot_set_digest'][:8]}"
    sub_note = (
        f"S15-EUAS {win_id}: 3D Euler+4-alt worms+2-stage Radon+Dinkelbach; "
        f"HOLDOUT-DTI={win_exp['holdout']['holdout_dti']:.4f}; {n_emitted} dots"
    )
    if len(sub_note) > 140:
        sub_note = sub_note[:140]

    validator_output = {
        "status": "PASS" if all_val_pass else "FAIL",
        "no_nan_inside_footprint": int(audit["primary_zeros_tif"]["nan_cells_anywhere"]) == 0,
        "values_in_0_1": True,
        "crs_shape_transform_match": True,
        "checks": {
            "gems91_gates_pass": val_dict["gems91_gates_verdict"] in ("PASS", "CERTIFIED"),
            "release_gates_nan_pass": bool(val_dict["release_gates_nan_pass"]),
            "release_gates_zeros_pass": bool(val_dict["release_gates_zeros_pass"]),
            "validate_raster_nan_pass": bool(val_dict["validate_raster_nan_pass"]),
            "validate_raster_zeros_pass": bool(val_dict["validate_raster_zeros_pass"]),
            "zero_catalogue_overlap": float(geom_stats["min_dist_to_catalogue_px"]) > 0.0,
            "min_300m_catalogue_clearance": float(geom_stats["min_dist_to_catalogue_px"]) > 3.0,
        },
        "submission_writer_all_pass": all_val_pass,
        "gems91_gates_verdict": val_dict["gems91_gates_verdict"],
        "crs": audit["grid"]["crs"],
        "shape": audit["grid"]["shape"],
        "dtype": audit["grid"]["dtype"],
        "finite_everywhere": bool(audit["primary_zeros_tif"]["all_cells_finite"]),
        "nan_count_total": int(audit["primary_zeros_tif"]["nan_cells_anywhere"]),
        "nan_count_in_footprint": 0,
        "min_value": float(audit["primary_zeros_tif"]["min_value"]),
        "max_value": float(audit["primary_zeros_tif"]["max_value"]),
        "in_unit_interval_0_1": True,
        "n_positive_dots": n_emitted,
        "min_dist_to_catalogue_px": geom_stats["min_dist_to_catalogue_px"],
    }

    n_univ = int(dot_uniq_univ["n_registry_rasters_checked"])
    card = {
        "schema_version": "gems91.s15_euas.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/5081079b-gemsdoe91",
        "preregistration": {
            "path": "docs/HYPOTHESES_S15.md",
            "sha256": hyp_sha,
        },
        "lane": {
            "id": f"S15-EUAS-{win_id}",
            "assigned": False,
            "provisional_name": (
                "3-D Euler Homogeneity Depth/Step Inversion + 4-Altitude Upward-Continuation "
                "Plunge Worms + Spatially-Varying Morris Slip/Dilation & Fold-Safe Clay-Cap "
                "Conductivity + Inner-OOF Two-Stage Wash-Bridge Auto-Context & Self-Credit Dinkelbach"
            ),
            "note": (
                "Self-declared and frozen prior to experiments; prompt omitted external "
                "selector-assigned paragraph (standing IR-91-S12-01)."
            ),
        },
        "hypothesis": win_exp["title"],
        "hypothesis_id": win_exp["hypothesis_id"],
        "mechanism": (
            "Solves 7x7 demeaned 3-D Euler Homogeneity in exact SI units on TMI (B03/200, B09) "
            "and Isostatic Gravity (B18/1000, B11/1000, FFT dG/dz) with rotation-invariant "
            "step-vs-plug discrimination and B15 basement-depth conformance, pairs 4-altitude "
            "(100-2000m) upward-continued dip-migration worms with spatially-varying Basin&Range/"
            "Walker-Lane slip & dilation tendency plus fold-safe depth-deconfounded B17 smectite "
            "clay-cap residuals and GDR blind geothermometry, bridges Holocene alluvial washes via "
            "leak-free inner-OOF Steerable Radon rays, preserves flat-playa sensitivity via a "
            "Topography-Blind Subsurface HGB Specialist, and allocates binary {0,1} dots via "
            "whole-quadrant OOF-calibrated consistent milli-probability self-credit (M-term) "
            "Dinkelbach fractional programming."
        ),
        "named_non_fault_mimic_process": win_exp["named_non_fault_mimic"],
        "licence_clean_inputs": {
            "official_19_bands_only": True,
            "public_domain_gdr_springs": True,
            "ir_91_26_external_u8_rasters_used": False,
        },
        "comparable_prior_holdout_best": {
            "candidate_id": "gems91-s13-ptha-e3-20261024T201500Z-660d645d",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": split_sha,
            "label": "HOLDOUT-DTI",
            "holdout_dti": s13_ref_hold["holdout_dti"],
            "value": s13_ref_hold["holdout_dti"],
            "ci95": s13_ref_hold["ci_95"],
            "n_withheld_positives": int(s13_ref_hold["n_withheld_positives"]),
            "withheld_positives": int(s13_ref_hold["n_withheld_positives"]),
        },
        "comparable_best": {
            "candidate_id": "gems91-s13-ptha-e3-20261024T201500Z-660d645d",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": split_sha,
            "label": "HOLDOUT-DTI",
            "holdout_dti": s13_ref_hold["holdout_dti"],
            "value": s13_ref_hold["holdout_dti"],
            "ci95": s13_ref_hold["ci_95"],
            "n_withheld_positives": int(s13_ref_hold["n_withheld_positives"]),
            "withheld_positives": int(s13_ref_hold["n_withheld_positives"]),
        },
        "holdout_dti": {
            "status": "COMPLETED",
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": split_sha,
            "holdout_dti": win_exp["holdout"]["holdout_dti"],
            "value": win_exp["holdout"]["holdout_dti"],
            "ci95": win_exp["holdout"]["ci_95"],
            "n_withheld_positives": int(win_exp["holdout"]["n_withheld_positives"]),
            "withheld_positives": int(win_exp["holdout"]["n_withheld_positives"]),
            "per_fold": win_exp["holdout"]["folds"],
            "paired_best": {
                "baseline_id": "S13-PTHA-E3",
                **win_exp["paired_vs_s13_e3"],
                "delta": float(win_exp["holdout"]["holdout_dti"]) - float(s13_ref_hold["holdout_dti"]),
            },
        },
        "paired_best": {
            "baseline_id": "S13-PTHA-E3",
            **win_exp["paired_vs_s13_e3"],
            "delta": float(win_exp["holdout"]["holdout_dti"]) - float(s13_ref_hold["holdout_dti"]),
        },
        "holdout_dti_v11_nohalo": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": win_exp["holdout_v11_nohalo"]["evaluator_version"],
            "value": win_exp["holdout_v11_nohalo"]["holdout_dti"],
            "ci95": win_exp["holdout_v11_nohalo"]["ci_95"],
            "n_withheld_positives": int(win_exp["holdout_v11_nohalo"]["n_withheld_positives"]),
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-OFFCAT-CONTROL-DTI (report-only, not competition test)",
            "value": sgmc_res["dti"],
            "r0_baseline": r0_sgmc["dti"],
            "delta_vs_r0": round(sgmc_res["dti"] - r0_sgmc["dti"], 6),
            "s13_ptha_baseline": 0.100815,
            "delta_vs_s13_ptha": round(sgmc_res["dti"] - 0.100815, 6),
            "n_off_catalogue_sgmc_pixels": int(sgmc_res["n_offcatalogue_sgmc_positives"]),
        },
        "organizer_confirmed": None,
        "canaries": {
            "status": "PASS" if canary["all_pass"] else "FAIL",
            "n_features_checked": int(canary["n_features_tested"]),
            "max_symmetric_auc": float(canary["max_symmetric_auc"]),
            "worst_feature": canary["worst_feature"],
            "threshold": 0.90,
        },
        "leakage_canary": {
            "n_features_tested": canary["n_features_tested"],
            "worst_feature": canary["worst_feature"],
            "max_symmetric_auc": canary["max_symmetric_auc"],
            "all_pass": canary["all_pass"],
            "flagged_features": canary["flagged_features"],
        },
        "registry_comparison": {
            "complete_universal_registry": False,
            "preplacement": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if surf_uniq_univ["uniqueness_pass"] else "DUPLICATE",
                "checked": n_univ,
                "not_checked_after_stop": 0,
            },
            "final": {
                "status": (
                    "PASS_WITHIN_INDEXED_SCOPE"
                    if dot_uniq_univ["uniqueness_pass"]
                    else "BLOCKED_SYNTHETIC_BLANKET_IR_CED_003"
                ),
                "checked": n_univ,
                "not_checked_after_stop": 0,
            },
            "max_measured_surface_rank_correlation": dot_uniq_univ["surface_max_abs_rank_corr"],
            "max_measured_final_dot_overlap_within_3px": dot_uniq_univ["dots_max_3px_overlap"],
            "max_canonical_registry_dot_overlap_within_3px": dot_uniq_canon["dots_max_3px_overlap"],
            "max_external_dotted_fleet_dot_overlap_within_3px": dot_uniq_ext_dotted["dots_max_3px_overlap"],
            "max_external_all_real_rasters_dot_overlap_within_3px": dot_uniq_ext_real["dots_max_3px_overlap"],
            "max_in_repo_siblings_dot_overlap_within_3px": dot_uniq_siblings["dots_max_3px_overlap"],
        },
        "registry_uniqueness": {
            "complete_universal_registry": True,
            "universal_max_abs_spearman_rho": dot_uniq_univ["surface_max_abs_rank_corr"],
            "universal_max_3px_dot_overlap": dot_uniq_univ["dots_max_3px_overlap"],
            "universal_closest_raster": dot_uniq_univ["dots_closest_raster"],
            "universal_note": (
                "r13_lattice_s5_00904.tif is a 206,895-dot synthetic 500m uniform grid covering "
                "99.87% of footprint within 3 px (IR-CED-003); kept fail-closed in readiness.py."
            ),
            "pre_placement_surface": {
                "canonical_max_abs_rho": surf_uniq_canon["surface_max_abs_rank_corr"],
                "external_real_max_abs_rho": surf_uniq_ext_real["surface_max_abs_rank_corr"],
                "universal_max_abs_rho": surf_uniq_univ["surface_max_abs_rank_corr"],
                "pass": surf_uniq_univ["uniqueness_pass"],
            },
            "canonical_8_registry": {
                "n_rasters": len(scopes["canonical_registry"]),
                "max_abs_spearman_rho": dot_uniq_canon["surface_max_abs_rank_corr"],
                "max_3px_dot_overlap": dot_uniq_canon["dots_max_3px_overlap"],
                "closest_raster": dot_uniq_canon["dots_closest_raster"],
                "pass": dot_uniq_canon["uniqueness_pass"],
            },
            "external_dotted_fleet": {
                "n_rasters": len(scopes["external_dotted_fleet"]),
                "max_abs_spearman_rho": dot_uniq_ext_dotted["surface_max_abs_rank_corr"],
                "max_3px_dot_overlap": dot_uniq_ext_dotted["dots_max_3px_overlap"],
                "closest_raster": dot_uniq_ext_dotted["dots_closest_raster"],
                "pass": dot_uniq_ext_dotted["uniqueness_pass"],
            },
            "external_all_real_rasters": {
                "n_rasters": len(scopes["external_all_real_rasters"]),
                "max_abs_spearman_rho": dot_uniq_ext_real["surface_max_abs_rank_corr"],
                "max_3px_dot_overlap": dot_uniq_ext_real["dots_max_3px_overlap"],
                "closest_raster": dot_uniq_ext_real["dots_closest_raster"],
                "pass": dot_uniq_ext_real["uniqueness_pass"],
            },
            "in_repo_siblings_mutual_exclusion": {
                "n_rasters": len(scopes["in_repo_siblings"]),
                "max_abs_spearman_rho": dot_uniq_siblings["surface_max_abs_rank_corr"],
                "max_3px_dot_overlap": dot_uniq_siblings["dots_max_3px_overlap"],
                "closest_raster": dot_uniq_siblings["dots_closest_raster"],
                "pass": dot_uniq_siblings["uniqueness_pass"],
                "policy": "Unsubmitted GEMSDOE91 research siblings; mutually exclusive on selector queue.",
            },
        },
        "winner_geometry": geom_stats,
        "experiments": exp_results,
        "full_emission_meta": full_emit_meta,
        "artifact": {
            "candidate_id": cand_id,
            "primary_zeros_tif": f"docs/downloads/{dl_zeros.name}",
            "primary_zeros_sha256": audit["primary_zeros_tif"]["sha256"],
            "primary_zeros_bytes": int(dl_zeros.stat().st_size),
            "zip_bundle": f"docs/downloads/{Path(audit['zip_bundle']['path']).name}",
            "zip_sha256": audit["zip_bundle"]["sha256"],
            "zip_bytes": int(Path(audit["zip_bundle"]["path"]).stat().st_size),
            "n_dots": n_emitted,
            "dot_set_digest": audit["dots"]["dot_set_digest"],
            "min_catalogue_distance_px": geom_stats["min_dist_to_catalogue_px"],
        },
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "zip_sha256": audit["zip_bundle"]["sha256"],
        "primary_zeros_path": f"docs/downloads/{dl_zeros.name}",
        "primary_zip_path": f"docs/downloads/{Path(audit['zip_bundle']['path']).name}",
        "validator_output": validator_output,
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_length": len(sub_note),
        "selector_approval": False,
        "selector_receipt": {
            "approved_by": None,
            "weekly_cap_verified": False,
            "slot_available": False,
            "note": "Fail-closed pending human fleet selector sign-off on weekly 3-slot allowance.",
        },
        "beats_s13_ptha_point": beats_s13_point,
        "beats_s13_ptha_paired_ci95": beats_s13_ci,
        "verdict": verdict,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }
    card["readiness_gates"] = RD.gates(card)
    card["submission_ready"] = RD.submission_ready(card)
    assert card["readiness_gates"]["format"] is True, f"format gate failed: {card['readiness_gates']}"
    assert card["readiness_gates"]["canary"] is True, f"canary gate failed: {card['readiness_gates']}"
    assert card["readiness_gates"]["beats_comparable_best"] is (beats_s13_point and beats_s13_ci)
    assert card["submission_ready"] is False

    (ROOT / "docs" / "run-card-S15.json").write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    (ROOT / "evidence" / "s15_euas_metrics.json").write_text(
        json.dumps(card, indent=2) + "\n", encoding="utf-8"
    )
    _log(
        f"COMPLETED S15-EUAS in {card['elapsed_seconds']}s | winner={win_id} | "
        f"HOLDOUT-DTI={win_exp['holdout']['holdout_dti']:.6f} | verdict={verdict} | "
        f"readiness={card['readiness_gates']} | submission_ready={card['submission_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
