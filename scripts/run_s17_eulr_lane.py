#!/usr/bin/env python3
"""Session 17 Pre-Registered Runner (`S17-EULR`, 2026-10-25).

Executes the 3 frozen experiments preregistered in `docs/HYPOTHESES_S17.md`:

- `E1` (ablation control): exact S13 recipe — 39 static + 16 S11 + 20 PTHA
  features, shared PTHA OOF learner, matched 48,000-dot corridor emission.
- `E2` (`H17-1` test): E1 + 14 label-free Euler-deconvolution features
  (`gems91.eulr17`), identical learner/emitter/quotas. The paired 5 km-tile
  bootstrap `E2 - E1` is the primary scientific readout.
- `E3`: fold-independent Dinkelbach emission on the better of {E1, E2} OOF
  surfaces (S13 rule), zero additional fits.

Shared template tools only (Protocol Rule 2): `scripts/evaluate_holdout.py`,
`scripts/dti.py`, `scripts/submission_writer.py`, S13 tile/paired helpers,
cached feature builders. Primary score is `gems91-hide-recover-v1.0`
(`mask_buffer_predictions=True`, comparable with S13-S15 cards); the v1.1
nohalo receipt is recorded alongside and must agree on eligible-restricted
fold dots (IR-S17-02).

Stages (`--stage`, default `all`) checkpoint through `data/derived/` so a
memory-constrained host can run `features -> canary -> experiments -> full`
as separate processes with identical results.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gems91 import dd_vtc_pu as DD
from gems91 import eulr17 as EU
from gems91 import io as IO
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import readiness as RD
from scripts import evaluate_holdout as EH
from scripts import run_s13_lane as S13
from scripts import submission_writer as SW
from vendor.gems57.validate import validate as validate_gems57

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
HYPOTHESES_MD = ROOT / "docs" / "HYPOTHESES_S17.md"
EVIDENCE_JSON = ROOT / "evidence" / "s17_eulr_metrics_20261025.json"
CHECKPOINT_JSON = ROOT / "evidence" / "s17_experiments_checkpoint.json"
RUN_CARD_JSON = ROOT / "docs" / "run-card-S17-EULR.json"
COMBINED_DAT = CACHE_DIR / "s17_ptha_eulr34_v1.dat"
COMBINED_META = CACHE_DIR / "s17_ptha_eulr34_v1.json"
CANARY_JSON = CACHE_DIR / "s17_canary_v1.json"

EXPECTED_SPLIT_SHA256 = "0f874367d8d34964c9b8802d3d67d348f68ade1f9fbc4301bffc5eafcb524db8"
EXPECTED_WITHHELD = 60_988
MAX_EXPERIMENTS = 3
MAX_EXPERIMENT_SECONDS = 7200.0
MATCHED_DOT_BUDGET = 48_000
DINKELBACH_FULL_DOTS = 44_000
DATE_TAG = "20261025T160000Z"
OWN_PREFIX = "gems91-s17-eulr-"

# Frozen comparable promotion bar (docs/run-card-S14-PTAC.json). No paired
# bootstrap vs S14 is attempted (its frozen caches are not restorable here);
# any comparison to this bar is point-only and labelled as such.
S14_BAR = {
    "candidate_id": "S14-PTAC-E2 (docs/run-card-S14-PTAC.json)",
    "evaluator_version": "gems91-hide-recover-v1.0",
    "split_sha256": EXPECTED_SPLIT_SHA256,
    "label": "HOLDOUT-DTI",
    "value": 0.267782,
    "ci95": [0.253687, 0.281135],
    "withheld_positives": EXPECTED_WITHHELD,
}


def _log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def _load_masks() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with rasterio.open(TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE_TIF) as src:
        cat_mask = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC_TIF) as src:
        sgmc_mask = (src.read(1) > 0) & footprint
    with rasterio.open(R0_ZEROS_TIF) as src:
        r0_dots = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)
    return footprint, cat_mask, sgmc_mask, r0_dots


def _build_folds(cat_mask: np.ndarray, footprint: np.ndarray):
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=10.0)
    split_sha = S13._compute_fold_split_sha256(folds)
    n_withheld = int(sum(f.n_withheld for f in folds))
    if split_sha != EXPECTED_SPLIT_SHA256 or n_withheld != EXPECTED_WITHHELD:
        raise RuntimeError(
            f"holdout instrument drift: split_sha={split_sha} withheld={n_withheld} "
            f"(expected {EXPECTED_SPLIT_SHA256} / {EXPECTED_WITHHELD}); refusing to score"
        )
    return folds, split_sha


def _fold_quotas(folds, footprint):
    fold_eligible: dict[int, np.ndarray] = {}
    active_counts: dict[int, int] = {}
    total_active = 0
    for f in folds:
        act, elig = S13._fold_active_and_eligible(f, folds, footprint, collar_px=3.0)
        fold_eligible[f.fold_id] = elig
        active_counts[f.fold_id] = int(act.sum())
        total_active += active_counts[f.fold_id]
    fold_dot_quota: dict[int, int] = {}
    assigned = 0
    for f in folds:
        if f.fold_id < 3:
            q = int(round(MATCHED_DOT_BUDGET * active_counts[f.fold_id] / total_active))
            fold_dot_quota[f.fold_id] = q
            assigned += q
        else:
            fold_dot_quota[f.fold_id] = MATCHED_DOT_BUDGET - assigned
    return fold_eligible, fold_dot_quota


def _open_feature_blocks(footprint: np.ndarray):
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES_TIF, gdr_csv=GDR_CSV, footprint=footprint, cache_dir=CACHE_DIR)
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE_DIR)
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE_DIR)
    X_eulr, eulr_names, eulr_meta = EU.build_or_load_eulr_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE_DIR)
    return X_static, static_names, X_s11, s11_names, X_ptha, ptha_names, X_eulr, eulr_names, eulr_meta


def _build_or_open_combined(X_ptha, ptha_names, X_eulr, eulr_names, n_fp: int):
    names34 = list(ptha_names) + list(eulr_names)
    if len(names34) != 34:
        raise RuntimeError(f"combined block must have 34 cols, got {len(names34)}")
    if COMBINED_DAT.is_file() and COMBINED_META.is_file():
        meta = json.loads(COMBINED_META.read_text(encoding="utf-8"))
        if meta.get("feature_names") == names34 and COMBINED_DAT.stat().st_size == n_fp * 34 * 4:
            return np.memmap(COMBINED_DAT, dtype=np.float32, mode="r", shape=(n_fp, 34)), names34
    mm = np.memmap(COMBINED_DAT, dtype=np.float32, mode="w+", shape=(n_fp, 34))
    for s in range(0, n_fp, 250_000):
        e = min(s + 250_000, n_fp)
        mm[s:e, :20] = np.asarray(X_ptha[s:e, :])
        mm[s:e, 20:] = np.asarray(X_eulr[s:e, :])
    mm.flush()
    del mm
    COMBINED_META.write_text(json.dumps({"feature_names": names34, "n_fp": n_fp}, indent=2) + "\n", encoding="utf-8")
    return np.memmap(COMBINED_DAT, dtype=np.float32, mode="r", shape=(n_fp, 34)), names34


def _registry_inventory_status() -> dict:
    """Verify present frozen-inventory fleet files by SHA-256; never edit pins."""
    inv = json.loads((ROOT / "registry" / "comparison_inventory.json").read_text(encoding="utf-8"))
    checked, not_checked = [], []
    for row in inv["files"]:
        path = ROOT / row["path"]
        if "git_blob" not in row:
            not_checked.append({"path": row["path"], "reason": "frozen row has no git_blob pin (IR-S17-03)"})
        elif not path.is_file():
            not_checked.append({"path": row["path"], "reason": "file absent locally"})
        elif IO.sha256_file(path) == row["sha256"] and path.stat().st_size == row["bytes"]:
            checked.append(row["path"])
        else:
            not_checked.append({"path": row["path"], "reason": "SHA-256/size mismatch vs frozen pin"})
    return {
        "frozen_inventory_rows": len(inv["files"]),
        "verified_present": len(checked),
        "not_checked": not_checked,
        "complete_universal_registry": False,
    }


def _registry_paths() -> list[Path]:
    """Hash-distinct same-grid local references, zero exemptions (own lane excluded)."""
    seen: dict[str, Path] = {}
    for folder in (DATA / "fleet_registry", DATA / "registry", DATA / "retracted_geod", DOWNLOADS_DIR):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.tif")):
            if path.name.startswith(OWN_PREFIX):
                continue
            seen.setdefault(IO.sha256_file(path), path)
    return list(seen.values())


def stage_features(ctx: dict) -> None:
    footprint = ctx["footprint"]
    blocks = _open_feature_blocks(footprint)
    (X_static, static_names, X_s11, s11_names, X_ptha, ptha_names,
     X_eulr, eulr_names, eulr_meta) = blocks
    X34, names34 = _build_or_open_combined(X_ptha, ptha_names, X_eulr, eulr_names, ctx["n_fp"])
    meta = {
        "static_cols_49": static_names,
        "s11_cols_16": s11_names,
        "ptha_cols_20": ptha_names,
        "eulr_cols_14": eulr_names,
        "combined34": names34,
        "eulr_builder_meta": eulr_meta,
    }
    (CACHE_DIR / "s17_feature_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    ctx.update({
        "X_static": X_static, "static_names": static_names, "X_s11": X_s11,
        "s11_names": s11_names, "X_ptha": X_ptha, "ptha_names": ptha_names,
        "X_eulr": X_eulr, "eulr_names": eulr_names, "eulr_meta": eulr_meta,
        "X34": X34, "names34": names34,
    })
    _log(f"features ready: static={len(static_names)} s11={len(s11_names)} ptha={len(ptha_names)} eulr={len(eulr_names)}")


def stage_canary(ctx: dict) -> dict:
    if CANARY_JSON.is_file():
        report = json.loads(CANARY_JSON.read_text(encoding="utf-8"))
        _log(f"loaded cached canary PASS={report['canary_pass']} worst={report['worst_feature']}@{report['worst_symmetric_auc']}")
        ctx["canary"] = report
        return report
    folds, footprint = ctx["folds"], ctx["footprint"]
    base_cols = ctx["base_static_cols"]
    _log("Rule 4 leakage canary over all 89 candidate features (symmetric AUC <= 0.90)...")
    static_block = np.asarray(ctx["X_static"][:, base_cols], dtype=np.float32)
    c_static = EH.run_leakage_canary(
        static_block, [ctx["static_names"][i] for i in base_cols], folds, footprint, subsample_step=4)
    del static_block
    gc.collect()
    c_s11 = EH.run_leakage_canary(ctx["X_s11"], ctx["s11_names"], folds, footprint, subsample_step=4)
    c_ptha = EH.run_leakage_canary(ctx["X_ptha"], ctx["ptha_names"], folds, footprint, subsample_step=4)
    c_eulr = EH.run_leakage_canary(ctx["X_eulr"], ctx["eulr_names"], folds, footprint, subsample_step=4)
    combined = {**c_static["features"], **c_s11["features"], **c_ptha["features"], **c_eulr["features"]}
    worst_kv = max(combined.items(), key=lambda kv: kv[1]["max_fold_symmetric_auc"])
    flagged = [k for k, v in combined.items() if not v["pass"]]
    report = {
        "evaluator_version": EH.EVALUATOR_VERSION,
        "max_allowed_auc": EH.MAX_LEAKAGE_AUC,
        "n_features_checked": len(combined),
        "canary_pass": len(flagged) == 0,
        "worst_feature": worst_kv[0],
        "worst_symmetric_auc": worst_kv[1]["max_fold_symmetric_auc"],
        "flagged_features": flagged,
        "eulr_features": c_eulr["features"],
        "features": combined,
    }
    CANARY_JSON.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    _log(f"canary PASS={report['canary_pass']} worst={report['worst_feature']}@{report['worst_symmetric_auc']} n={len(combined)}")
    ctx["canary"] = report
    return report


def _score_both(fold_dots, folds, footprint, idx: int) -> tuple[dict, dict]:
    v1 = EH.score_pooled_holdout(
        fold_dots, folds, footprint, n_boot=200, seed=170 + idx, mask_buffer_predictions=True)
    v11 = EH.score_pooled_holdout(
        fold_dots, folds, footprint, n_boot=200, seed=270 + idx, mask_buffer_predictions=False)
    if abs(v1["holdout_dti"] - v11["holdout_dti"]) > 1e-6:
        raise RuntimeError(
            f"v1.0/v1.1 pooled disagreement on eligible-restricted dots: "
            f"{v1['holdout_dti']} vs {v11['holdout_dti']} (IR-S17-02 invariant broken)")
    return v1, v11


def _save_tiles(exp_id: str, tiles) -> None:
    np.savez(CACHE_DIR / f"s17_tiles_{exp_id.lower()}.npz",
             T=tiles[0], S=tiles[1], M=tiles[2], G=tiles[3])


def _load_tiles(exp_id: str):
    z = np.load(CACHE_DIR / f"s17_tiles_{exp_id.lower()}.npz")
    return z["T"], z["S"], z["M"], z["G"]


def stage_experiments(ctx: dict) -> dict:
    if CHECKPOINT_JSON.is_file() and not ctx["args"].force_experiments:
        ckpt = json.loads(CHECKPOINT_JSON.read_text(encoding="utf-8"))
        _log(f"loaded experiments checkpoint (winner={ckpt['winner_exp_id']})")
        ctx["checkpoint"] = ckpt
        return ckpt
    if not ctx["canary"]["canary_pass"]:
        raise RuntimeError(f"RULE 4 LEAKAGE CANARY FAILED: {ctx['canary']['flagged_features']}")

    footprint, folds = ctx["footprint"], ctx["folds"]
    n_fp = ctx["n_fp"]
    fold_eligible, fold_dot_quota = ctx["fold_eligible"], ctx["fold_dot_quota"]
    reg_paths = ctx["reg_paths"]
    _log(f"registry scope for pre-placement checks: {len(reg_paths)} hash-distinct rasters")

    mhtr_edge, piedmont_mask = MC.compute_mhtr_structural_edge_field(ctx["X_s11"], ctx["X_static"], footprint)
    ptha_crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, ctx["X_ptha"], footprint)
    ctx.update({"piedmont_mask": piedmont_mask, "ptha_crest": ptha_crest})
    del mhtr_edge
    gc.collect()

    exp_specs = [
        {"exp_id": "E1", "hypothesis_id": "ablation-control (S13 recipe)",
         "title": "S13 recipe ablation control: 39 static + 16 S11 + 20 PTHA, corridor emission",
         "block_cols": list(range(20)),
         "named_non_fault_mimic": "Unfaulted Tertiary volcanic flow lobes, aeromagnetic flight-line seams, erosional range-front cliffs"},
        {"exp_id": "E2", "hypothesis_id": "H17-1",
         "title": "E1 + 14 Euler deconvolution source-geometry features (mag/grav SI 0/1 density, depth, uncertainty)",
         "block_cols": list(range(34)),
         "named_non_fault_mimic": "Unfaulted lithologic basement contacts; isolated volcanic plugs (point sources scatter at SI 0/1)"},
    ]

    exp_start = time.perf_counter()
    results: list[dict] = []
    tiles_by_exp: dict[str, tuple] = {}
    cal_by_exp: dict[str, dict[int, dict]] = {}

    for idx, spec in enumerate(exp_specs):
        te0 = time.perf_counter()
        eid = spec["exp_id"]
        cols = spec["block_cols"]
        n_feats = len(ctx["base_static_cols"]) + len(ctx["s11_names"]) + len(cols)
        _log(f"--- Experiment {idx + 1}/{MAX_EXPERIMENTS}: {eid} ({spec['hypothesis_id']}, {n_feats} features) ---")

        # Phase A: fold OOF fits (cached), stitch pre-placement mosaic.
        mosaic = np.zeros(footprint.shape, dtype=np.float32)
        cal_map: dict[int, dict] = {}
        for f in folds:
            oof_dat = CACHE_DIR / f"s17_oof_{eid.lower()}_f{f.fold_id}.dat"
            oof_meta = CACHE_DIR / f"s17_oof_{eid.lower()}_f{f.fold_id}.json"
            if oof_dat.is_file() and oof_meta.is_file() and oof_dat.stat().st_size == n_fp * 4:
                prob_f = np.zeros(footprint.shape, dtype=np.float32)
                prob_f[footprint] = np.fromfile(oof_dat, dtype=np.float32)
                cal_f = json.loads(oof_meta.read_text(encoding="utf-8"))
            else:
                excl = f.region_mask | f.withheld_faults | f.buffer_mask
                prob_f, cal_f = PTHA.fit_and_predict_ptha_oof_fold(
                    X_static=ctx["X_static"], static_cols=ctx["base_static_cols"],
                    static_names=ctx["static_names"],
                    X_s11=ctx["X_s11"], s11_cols=list(range(len(ctx["s11_names"]))),
                    s11_names=ctx["s11_names"],
                    X_ptha=ctx["X34"], ptha_cols=cols, ptha_names=ctx["names34"],
                    visible_faults=f.visible_faults, exclude_mask=excl,
                    footprint=footprint, seed=1700 + idx * 20 + f.fold_id,
                )
                prob_f[footprint].astype(np.float32).tofile(oof_dat)
                oof_meta.write_text(json.dumps(cal_f) + "\n", encoding="utf-8")
            if not np.isfinite(prob_f[footprint]).all():
                raise RuntimeError(f"{eid} fold {f.fold_id}: nonfinite OOF surface")
            cal_map[f.fold_id] = cal_f
            mosaic[f.region_mask] = prob_f[f.region_mask]
            del prob_f
            gc.collect()

        # Phase B: Rule 1 pre-placement surface check BEFORE any dot placement.
        pre = EH.check_registry_surface_uniqueness(
            mosaic[footprint], footprint, reg_paths, max_rank_corr=0.90, corr_stride=20)
        _log(f"[{eid}] pre-placement: max|rho|={pre['surface_max_abs_rank_corr']} vs {pre['surface_closest_raster']} "
             f"(n={pre['n_registry_rasters_checked']}, duplicate={pre['is_duplicate']})")
        del mosaic
        gc.collect()
        if pre["is_duplicate"]:
            results.append({"experiment_number": idx + 1, "exp_id": eid,
                            "hypothesis_id": spec["hypothesis_id"], "title": spec["title"],
                            "n_features": n_feats, "status": "STOPPED_PREPLACEMENT_DUPLICATE",
                            "preplacement": pre})
            _log(f"{eid} pre-placement DUPLICATE; stopping lane per Rule 1")
            break

        # Phase C: matched corridor emission + scoring.
        fold_dots: dict[int, np.ndarray] = {}
        for f in folds:
            prob_f = np.zeros(footprint.shape, dtype=np.float32)
            prob_f[footprint] = np.fromfile(CACHE_DIR / f"s17_oof_{eid.lower()}_f{f.fold_id}.dat", dtype=np.float32)
            fold_dots[f.fold_id] = MC.mhtr_corridor_submodular_emit(
                prob_f, ptha_crest, piedmont_mask,
                eligible_mask=fold_eligible[f.fold_id], n_dots=fold_dot_quota[f.fold_id],
                gamma=1.20, mhtr_weight=0.48, piedmont_quota_frac=0.24, min_spacing_px=2.45)
            del prob_f
            gc.collect()

        hold_v1, hold_v11 = _score_both(fold_dots, folds, footprint, idx)
        tiles = S13._accumulate_fold_tiles(fold_dots, folds, footprint)
        _save_tiles(eid, tiles)
        tiles_by_exp[eid] = tiles
        cal_by_exp[eid] = cal_map
        del fold_dots
        gc.collect()
        el = time.perf_counter() - te0
        _log(f"[{eid}] HOLDOUT-DTI(v1.0)={hold_v1['holdout_dti']:.6f} CI={hold_v1['ci_95']} "
             f"(v1.1 receipt={hold_v11['holdout_dti']:.6f}) [{el:.1f}s]")
        results.append({
            "experiment_number": idx + 1, "exp_id": eid, "hypothesis_id": spec["hypothesis_id"],
            "title": spec["title"], "n_features": n_feats, "block_cols": cols,
            "emission_mode": "matched_48k_area_quota_submodular",
            "named_non_fault_mimic": spec["named_non_fault_mimic"],
            "preplacement": {k: pre[k] for k in ("n_registry_rasters_checked", "surface_max_abs_rank_corr", "surface_closest_raster", "is_duplicate", "uniqueness_pass")},
            "holdout": hold_v1, "holdout_v1_1_nohalo_receipt": hold_v11,
            "elapsed_seconds": round(el, 2),
        })

    completed = [r for r in results if "holdout" in r]
    if len(completed) == 2:
        paired_e2_e1 = S13.compute_aligned_paired_bootstrap(
            tiles_by_exp["E2"], tiles_by_exp["E1"],
            cand_pooled_dti=results[1]["holdout"]["holdout_dti"],
            base_pooled_dti=results[0]["holdout"]["holdout_dti"],
            n_boot=400, seed=17101)
        results[1]["paired_vs_e1_ablation"] = paired_e2_e1
        _log(f"paired E2-E1: delta={paired_e2_e1['delta']:+.6f} CI={paired_e2_e1['ci95']} P(>0)={paired_e2_e1['prob_positive']}")

        # E3: Dinkelbach emission on the better OOF (S13 rule).
        te3 = time.perf_counter()
        base_eid = "E2" if results[1]["holdout"]["holdout_dti"] >= results[0]["holdout"]["holdout_dti"] else "E1"
        base_res = results[1] if base_eid == "E2" else results[0]
        _log(f"--- Experiment 3/{MAX_EXPERIMENTS}: E3 (Dinkelbach on {base_eid} OOF) ---")
        e3_dots: dict[int, np.ndarray] = {}
        e3_alloc: dict[str, dict] = {}
        for f in folds:
            prob_f = np.zeros(footprint.shape, dtype=np.float32)
            prob_f[footprint] = np.fromfile(CACHE_DIR / f"s17_oof_{base_eid.lower()}_f{f.fold_id}.dat", dtype=np.float32)
            cal_f = cal_by_exp[base_eid][f.fold_id]
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            d_vis = ndi.distance_transform_edt(~f.visible_faults)
            train_elig = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)
            dots_f, alloc = PTHA.dinkelbach_fold_independent_emit(
                prob_f, ptha_crest, piedmont_mask, footprint=footprint,
                train_eligible_mask=train_elig, test_eligible_mask=fold_eligible[f.fold_id],
                pi_true=cal_f["pi_vis_train"], pi_sample=cal_f["pi_sample_weighted"],
                target_pool_dots=MATCHED_DOT_BUDGET, full_eligible_pixels=ctx["n_full_elig"],
                min_spacing_px=2.50)
            e3_dots[f.fold_id] = dots_f
            e3_alloc[f.name] = alloc
            del prob_f, d_vis, train_elig
            gc.collect()
        e3_v1, e3_v11 = _score_both(e3_dots, folds, footprint, 2)
        e3_tiles = S13._accumulate_fold_tiles(e3_dots, folds, footprint)
        _save_tiles("E3", e3_tiles)
        del e3_dots
        gc.collect()
        paired_e3_e1 = S13.compute_aligned_paired_bootstrap(
            e3_tiles, tiles_by_exp["E1"], cand_pooled_dti=e3_v1["holdout_dti"],
            base_pooled_dti=results[0]["holdout"]["holdout_dti"], n_boot=400, seed=17102)
        paired_e3_base = S13.compute_aligned_paired_bootstrap(
            e3_tiles, tiles_by_exp[base_eid], cand_pooled_dti=e3_v1["holdout_dti"],
            base_pooled_dti=base_res["holdout"]["holdout_dti"], n_boot=400, seed=17103)
        el3 = time.perf_counter() - te3
        _log(f"[E3] HOLDOUT-DTI(v1.0)={e3_v1['holdout_dti']:.6f} CI={e3_v1['ci_95']} [{el3:.1f}s]")
        results.append({
            "experiment_number": 3, "exp_id": "E3",
            "hypothesis_id": f"{base_res['hypothesis_id']} + Dinkelbach emission",
            "title": f"{base_res['title']} + fold-independent Dinkelbach allocation",
            "n_features": base_res["n_features"], "block_cols": base_res["block_cols"],
            "base_oof_experiment": base_eid,
            "emission_mode": "fold_independent_dinkelbach_submodular",
            "fold_dinkelbach_allocation": e3_alloc,
            "named_non_fault_mimic": "Broad pluton-margin probability blobs and barren interior playa false positives",
            "holdout": e3_v1, "holdout_v1_1_nohalo_receipt": e3_v11,
            "paired_vs_e1_ablation": paired_e3_e1,
            "paired_vs_base_oof": paired_e3_base,
            "elapsed_seconds": round(el3, 2),
        })
        del e3_tiles

    exp_elapsed = time.perf_counter() - exp_start
    scored = [r for r in results if "holdout" in r]
    winner = max(scored, key=lambda r: r["holdout"]["holdout_dti"]) if scored else None
    ckpt = {
        "experiments": results,
        "winner_exp_id": winner["exp_id"] if winner else None,
        "experiment_seconds": round(exp_elapsed, 2),
        "max_experiment_seconds": MAX_EXPERIMENT_SECONDS,
        "within_budget": bool(exp_elapsed <= MAX_EXPERIMENT_SECONDS and len(results) <= MAX_EXPERIMENTS),
        "split_sha256": ctx["split_sha"],
    }
    CHECKPOINT_JSON.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_JSON.write_text(json.dumps(ckpt, indent=2) + "\n", encoding="utf-8")
    _log(f"experiments done in {exp_elapsed:.1f}s; winner={ckpt['winner_exp_id']} (checkpoint written)")
    ctx["checkpoint"] = ckpt
    return ckpt


def _summarize_final(final: dict, r0_name: str) -> dict:
    comps = final["comparisons"]
    lattice = [c for c in comps if "lattice" in c["registry_raster"]]
    real = [c for c in comps if c["n_registry_positive"] < 65_000 and "lattice" not in c["registry_raster"]]
    r0 = [c for c in comps if c["registry_raster"] == r0_name]
    def _max(rows, key):
        return max((r[key] for r in rows), default=None)
    def _argmax(rows, key):
        return max(rows, key=lambda r: r[key])["registry_raster"] if rows else None
    return {
        "n_checked_total": len(comps),
        "strict_directed_gate_pass_all": bool(final["uniqueness_pass"]),
        "max_overlap_all": final["dots_max_3px_overlap"],
        "closest_all": final["dots_closest_raster"],
        "lattice_rows": lattice,
        "real_dotted_submissions_only": {
            "n": len(real),
            "max_3px_dot_overlap": _max(real, "cand_within_3px_of_reg"),
            "closest": _argmax(real, "cand_within_3px_of_reg"),
        },
        "vs_r0_claim_leader": r0[0] if r0 else None,
        "top5_by_overlap": sorted(comps, key=lambda c: c["cand_within_3px_of_reg"], reverse=True)[:5],
    }


def stage_full(ctx: dict) -> dict:
    ckpt = ctx["checkpoint"]
    winner_id = ckpt["winner_exp_id"]
    if winner_id is None:
        raise RuntimeError("no scored experiment; lane stopped before full-map stage")
    win = next(r for r in ckpt["experiments"] if r["exp_id"] == winner_id)
    footprint, cat_mask = ctx["footprint"], ctx["cat_mask"]
    n_fp = ctx["n_fp"]
    cols = win["block_cols"]

    if "ptha_crest" not in ctx:  # separate-process stage: rebuild structural surfaces
        mhtr_edge, piedmont_mask = MC.compute_mhtr_structural_edge_field(ctx["X_s11"], ctx["X_static"], footprint)
        ctx["ptha_crest"] = PTHA.build_ptha_structural_crest_surface(mhtr_edge, ctx["X_ptha"], footprint)
        ctx["piedmont_mask"] = piedmont_mask
        del mhtr_edge
        gc.collect()

    full_dat = CACHE_DIR / f"s17_full_{winner_id.lower()}.dat"
    full_meta = CACHE_DIR / f"s17_full_{winner_id.lower()}.json"
    if full_dat.is_file() and full_meta.is_file() and full_dat.stat().st_size == n_fp * 4:
        full_prob = np.zeros(footprint.shape, dtype=np.float32)
        full_prob[footprint] = np.fromfile(full_dat, dtype=np.float32)
        full_cal = json.loads(full_meta.read_text(encoding="utf-8"))
    else:
        _log(f"fitting full-map model ({winner_id} recipe, {len(cols)} block cols) on complete catalogue...")
        full_prob, full_cal = PTHA.fit_and_predict_ptha_oof_fold(
            X_static=ctx["X_static"], static_cols=ctx["base_static_cols"], static_names=ctx["static_names"],
            X_s11=ctx["X_s11"], s11_cols=list(range(len(ctx["s11_names"]))), s11_names=ctx["s11_names"],
            X_ptha=ctx["X34"], ptha_cols=cols, ptha_names=ctx["names34"],
            visible_faults=cat_mask, exclude_mask=~footprint, footprint=footprint, seed=1791)
        full_prob[footprint].astype(np.float32).tofile(full_dat)
        full_meta.write_text(json.dumps(full_cal) + "\n", encoding="utf-8")
    if not np.isfinite(full_prob[footprint]).all():
        raise RuntimeError("nonfinite full-map surface")

    pre_full = EH.check_registry_surface_uniqueness(
        full_prob[footprint], footprint, ctx["reg_paths"], max_rank_corr=0.90, corr_stride=20)
    _log(f"full-map pre-placement max|rho|={pre_full['surface_max_abs_rank_corr']} duplicate={pre_full['is_duplicate']}")
    if pre_full["is_duplicate"]:
        raise RuntimeError(f"Full-map pre-placement surface duplicate: {pre_full['surface_closest_raster']}")

    if winner_id == "E3":
        full_dots, full_last_gain = PTHA.dinkelbach_full_map_emit(
            full_prob, ctx["ptha_crest"], ctx["piedmont_mask"], footprint=footprint,
            full_eligible_mask=ctx["full_eligible"], pi_true=full_cal["pi_vis_train"],
            pi_sample=full_cal["pi_sample_weighted"], n_dots=DINKELBACH_FULL_DOTS, min_spacing_px=2.50)
    else:
        full_dots = MC.mhtr_corridor_submodular_emit(
            full_prob, ctx["ptha_crest"], ctx["piedmont_mask"], eligible_mask=ctx["full_eligible"],
            n_dots=MATCHED_DOT_BUDGET, gamma=1.20, mhtr_weight=0.48,
            piedmont_quota_frac=0.24, min_spacing_px=2.45)
        full_last_gain = 0.0

    full_w_surf, _, _ = PTHA.build_dinkelbach_expected_intensity(
        full_prob, ctx["ptha_crest"], ctx["piedmont_mask"], footprint,
        calibration_mask=ctx["full_eligible"], pi_true=full_cal["pi_vis_train"],
        pi_sample=full_cal["pi_sample_weighted"])
    del full_prob
    gc.collect()

    final_registry = EH.check_registry_uniqueness(
        full_w_surf[footprint], full_dots, footprint, ctx["reg_paths"], corr_stride=5)
    reg_summary = _summarize_final(final_registry, R0_ZEROS_TIF.name)
    _log(f"final registry: pass={final_registry['uniqueness_pass']} max_overlap={final_registry['dots_max_3px_overlap']} "
         f"vs {final_registry['dots_closest_raster']} (n={final_registry['n_registry_rasters_checked']})")

    sgmc_res = EH.score_off_catalogue_sgmc(full_dots, ctx["sgmc_mask"], cat_mask, footprint)
    r0_sgmc = EH.score_off_catalogue_sgmc(ctx["r0_dots"], ctx["sgmc_mask"], cat_mask, footprint)
    _log(f"blind SGMC: candidate={sgmc_res['dti']:.6f} vs R0={r0_sgmc['dti']:.6f}")

    audit = SW.write_validated_submission_bundle(
        full_dots, stem_prefix=f"{OWN_PREFIX}{winner_id.lower()}", date_tag=DATE_TAG,
        template_path=TEMPLATE_TIF, catalogue_path=CATALOGUE_TIF,
        ledger_path=ROOT / "ledger" / "submissions.csv", parent_compare_path=R0_ZEROS_TIF,
        releases_dir=RELEASES_DIR, downloads_dir=DOWNLOADS_DIR, floor_px=3.0,
        bundle_js_filename="s17_submission_bundle.js")
    cand_id = audit["candidate_id"]
    rel_zeros = Path(audit["primary_zeros_tif"]["path"])
    dl_zeros = DOWNLOADS_DIR / rel_zeros.name
    if rel_zeros.resolve() != dl_zeros.resolve():
        shutil.copy2(rel_zeros, dl_zeros)
    if IO.sha256_file(dl_zeros) != audit["primary_zeros_tif"]["sha256"]:
        raise RuntimeError("Published GeoTIFF SHA-256 mismatch")
    rel_zip = Path(audit["zip_bundle"]["path"])
    dl_zip = DOWNLOADS_DIR / rel_zip.name
    if rel_zip.resolve() != dl_zip.resolve():  # writer already publishes ZIP to downloads
        shutil.copy2(rel_zip, dl_zip)
    if IO.sha256_file(dl_zip) != audit["zip_bundle"]["sha256"]:
        raise RuntimeError("Published ZIP SHA-256 mismatch")
    aux_audit = DOWNLOADS_DIR / f"{cand_id}-audit.json"
    if aux_audit.is_file():
        aux_audit.unlink()
    del full_dots, full_w_surf
    gc.collect()

    g57 = validate_gems57(dl_zeros, footprint=footprint, catalogue=cat_mask)
    if not g57["all_checks_passed"]:
        raise RuntimeError(f"Independent gems57 validation failed: {g57}")

    e1 = next(r for r in ckpt["experiments"] if r["exp_id"] == "E1")
    win_hold = win["holdout"]
    paired_primary = win.get("paired_vs_e1_ablation") or {
        "delta": 0.0, "ci95": [0.0, 0.0], "prob_positive": 0.0, "n_paired_5km_tiles": 0}
    e2 = next((r for r in ckpt["experiments"] if r["exp_id"] == "E2"), None)
    euler_delta = (e2 or {}).get("paired_vs_e1_ablation", {})
    point_vs_s14 = round(win_hold["holdout_dti"] - S14_BAR["value"], 6)
    beats_bar_point = bool(win_hold["holdout_dti"] > S14_BAR["value"])
    euler_helps = bool(euler_delta.get("ci95", [0, 0])[0] > 0) if euler_delta else False

    sub_name = f"GEMS91-S17-EULR-{winner_id}-{audit['dots']['dot_set_digest'][:8]}"
    sub_note = (f"S17-EULR {winner_id}: Euler deconv fusion; HOLDOUT-DTI={win_hold['holdout_dti']:.4f}; "
                f"{audit['dots']['n_dots']} dots; HOLD selector")
    assert len(sub_note) <= 140, f"note too long ({len(sub_note)})"

    inv_status = ctx["inventory_status"]
    n_not_checked = len(inv_status["not_checked"])
    final_pass = bool(final_registry["uniqueness_pass"])
    card = {
        "schema_version": "gems91.s17_eulr.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/597b6f3f-gemsdoe91",
        "preregistration": {"path": "docs/HYPOTHESES_S17.md", "sha256": ctx["prereg_sha256"]},
        "lane": {
            "id": f"S17-EULR-{winner_id}", "assigned": False,
            "provisional_name": "Euler Deconvolution Source-Geometry Fusion (S13 stack + 14 Euler features)",
            "note": ("Brief promises an assigned 'single method paragraph' it does not contain; lane "
                     "self-declared and frozen in docs/HYPOTHESES_S17.md before any fit."),
        },
        "hypothesis": win["title"],
        "hypothesis_id": win["hypothesis_id"],
        "physical_mechanism": (
            "Windowed Euler deconvolution (11x11 px, structural indices 0/1) inverts magnetic "
            "(B14 + B09x100) and gravity (B13 + FFT vertical derivative) gradient ratios for 3-D "
            "source position/depth with formal uncertainty; accepted-solution density, mean depth "
            "and depth uncertainty (plus mag0 depth vs B15 agreement) encode buried-contact geometry "
            "independent of anomaly amplitude, fused as 14 supervised features atop the proven S13 "
            "stack. Correct structural index clusters solutions along real contacts; wrong index "
            "scatters them. Targets concealed/lateral contacts missed by amplitude-scaled edge "
            "detectors and normal-throw concordance features."),
        "named_non_fault_mimic_process": (
            "Unfaulted lithologic basement contacts (Euler-equivalent to faulted contacts; separated "
            "only by supervised fusion with step/strain features); isolated volcanic plugs; "
            "aeromagnetic flight-line seams (depth~0 solutions)"),
        "comparable_prior_holdout_best": S14_BAR,
        "holdout_dti": {
            "status": "COMPLETED", "label": "HOLDOUT-DTI",
            "evaluator_version": win_hold["evaluator_version"],
            "split_sha256": ctx["split_sha"],
            "value": win_hold["holdout_dti"], "ci95": win_hold["ci_95"],
            "withheld_positives": win_hold["n_withheld_positives"],
            "paired_best": {
                "baseline_id": "S17-E1 same-session S13-recipe ablation (NOT S14-PTAC)",
                "delta": paired_primary["delta"], "ci95": paired_primary["ci95"],
                "prob_positive": paired_primary["prob_positive"],
                "n_paired_5km_tiles": paired_primary["n_paired_5km_tiles"],
                "note": ("Paired bootstrap exists only vs the same-session E1 ablation; no paired "
                         "comparison vs S14-PTAC was computed (frozen S14 caches unrestorable here). "
                         "readiness.beats_comparable_best therefore correctly evaluates false."),
            },
            "per_fold": win_hold["folds"],
            "v1_1_nohalo_receipt": win["holdout_v1_1_nohalo_receipt"],
        },
        "scientific_readout_euler_ablation": {
            "paired_e2_minus_e1": euler_delta or None,
            "euler_block_adds_holdout_value_ci_excludes_zero": euler_helps,
            "e1_holdout_dti": e1["holdout"]["holdout_dti"],
        },
        "point_comparison_vs_s14_bar_not_paired": {
            "s14_value": S14_BAR["value"], "candidate_value": win_hold["holdout_dti"],
            "point_delta": point_vs_s14, "point_above_bar": beats_bar_point,
            "label": "HOLDOUT-DTI point comparison only; NOT a paired promotion test; NOT a leaderboard projection",
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-CONTROL-DTI (not competition leaderboard)",
            "value": sgmc_res["dti"], "r0_reference_value": r0_sgmc["dti"],
            "delta_vs_r0": round(sgmc_res["dti"] - r0_sgmc["dti"], 6),
            "n_offcatalogue_sgmc_positives": sgmc_res["n_offcatalogue_sgmc_positives"],
        },
        "canaries": {
            "status": "PASS" if ctx["canary"]["canary_pass"] else "FAIL",
            "n_features_checked": ctx["canary"]["n_features_checked"],
            "max_symmetric_auc": ctx["canary"]["worst_symmetric_auc"],
            "worst_feature": ctx["canary"]["worst_feature"],
            "threshold": 0.90,
            "eulr_features": ctx["canary"]["eulr_features"],
        },
        "registry_comparison": {
            "complete_universal_registry": False,
            "scope": "hash-distinct same-grid local fleet_registry + registry + docs/downloads (zero exemptions, lattice included)",
            "frozen_inventory": inv_status,
            "preplacement": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if pre_full["uniqueness_pass"] else "FAIL_WITHIN_INDEXED_SCOPE",
                "checked": int(pre_full["n_registry_rasters_checked"]),
                "not_checked_after_stop": int(n_not_checked),
                "max_abs_rank_corr_full_surface": pre_full["surface_max_abs_rank_corr"],
                "closest_raster": pre_full["surface_closest_raster"],
                "per_experiment": {r["exp_id"]: r.get("preplacement") for r in ckpt["experiments"]},
            },
            "final": {
                "status": "PASS_WITHIN_INDEXED_SCOPE" if final_pass else "FAIL_LITERAL_DIRECTED_GATE_WITHIN_INDEXED_SCOPE",
                "checked": int(final_registry["n_registry_rasters_checked"]),
                "not_checked_after_stop": int(n_not_checked),
                "summary": reg_summary,
            },
            "max_measured_surface_rank_correlation": final_registry["surface_max_abs_rank_corr"],
            "max_measured_final_dot_overlap_within_3px": final_registry["dots_max_3px_overlap"],
            "note": ("Literal directed gate includes the synthetic 206,895-dot Nevada lattice whose "
                     "3 px dilation covers 99.8713% of the footprint (docs/s16/registry-feasibility.json), "
                     "so failure at standard dot budgets is mathematically forced; reported, never waived. "
                     "2 frozen retracted-GEOD rows lack git_blob pins and are counted not_checked (IR-S17-03)."),
        },
        "artifact": {
            "candidate_id": cand_id,
            "primary_zeros_tif": f"docs/downloads/{dl_zeros.name}",
            "primary_zeros_sha256": audit["primary_zeros_tif"]["sha256"],
            "primary_zeros_bytes": audit["primary_zeros_tif"]["bytes"],
            "zip_bundle": f"docs/downloads/{dl_zip.name}",
            "zip_sha256": audit["zip_bundle"]["sha256"],
            "zip_bytes": audit["zip_bundle"]["bytes"],
            "n_dots": audit["dots"]["n_dots"],
            "dot_set_digest": audit["dots"]["dot_set_digest"],
            "min_catalogue_distance_px": audit["dots"]["min_catalogue_distance_px"],
            "full_map_last_gain": full_last_gain,
        },
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "validator_output": {
            "status": "PASS",
            "no_nan_inside_footprint": audit["primary_zeros_tif"]["nan_cells_anywhere"] == 0,
            "values_in_0_1": (0.0 <= audit["primary_zeros_tif"]["min_value"]
                              and audit["primary_zeros_tif"]["max_value"] <= 1.0),
            "crs_shape_transform_match": (audit["grid"]["crs"] == "EPSG:32611"
                                          and audit["grid"]["shape"] == [3730, 3292]),
            "checks": {
                "gems91_gates_pass": audit["validators"]["gems91_gates_verdict"] == "CERTIFIED",
                "release_gates_nan_pass": audit["validators"]["release_gates_nan_pass"],
                "release_gates_zeros_pass": audit["validators"]["release_gates_zeros_pass"],
                "validate_raster_nan_pass": audit["validators"]["validate_raster_nan_pass"],
                "validate_raster_zeros_pass": audit["validators"]["validate_raster_zeros_pass"],
                "gems57_independent_pass": bool(g57["all_checks_passed"]),
                "zero_catalogue_overlap": audit["dots"]["zero_catalogue_mass"],
                "min_300m_catalogue_clearance": audit["dots"]["dots_le_3px"] == 0,
            },
        },
        "submission": {"name": sub_name, "note": sub_note, "note_length": len(sub_note)},
        "selector_approval": False,
        "selector_receipt": {
            "weekly_cap_verified": False, "slot_available": False,
            "note": "No selector assignment or authenticated weekly-cap receipt exists in this session.",
        },
        "technical_candidate_verdict": (
            "promote_to_selector" if (beats_bar_point and final_pass and euler_helps) else "negative"),
        "portal_submission_verdict": "HOLD_PENDING_SELECTOR_SIGN_OFF",
        "ok_to_download": "YES — RESEARCH",
        "ok_to_submit": "NO",
        "budget": {
            "experiments_executed": len(ckpt["experiments"]),
            "max_experiments": MAX_EXPERIMENTS,
            "experiment_seconds": ckpt["experiment_seconds"],
            "max_experiment_seconds": MAX_EXPERIMENT_SECONDS,
            "within_budget": ckpt["within_budget"],
            "engineering_seconds_total_process": round(time.perf_counter() - ctx["t0"], 2),
        },
        "eulr_feature_build": ctx["eulr_meta"],
        "experiments": ckpt["experiments"],
        "irregularities": ["IR-S17-01 sample-values==catalogue", "IR-S17-02 evaluator default flip (explicit args used)",
                            "IR-S17-03 frozen registry 2 rows unpinnable"],
    }
    card["readiness_gates"] = RD.gates(card)
    card["submission_ready"] = RD.submission_ready(card)
    RUN_CARD_JSON.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    EVIDENCE_JSON.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_JSON.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    _log(f"wrote {RUN_CARD_JSON.name}; readiness={card['readiness_gates']}")
    _log(f"technical verdict={card['technical_candidate_verdict']} | OK TO SUBMIT: NO (selector/lane/registry gates)")
    return card


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["features", "canary", "experiments", "full", "all"], default="all")
    ap.add_argument("--force-experiments", action="store_true")
    args = ap.parse_args()

    t0 = time.perf_counter()
    for d in (CACHE_DIR, RELEASES_DIR, DOWNLOADS_DIR, EVIDENCE_JSON.parent):
        d.mkdir(parents=True, exist_ok=True)
    if not HYPOTHESES_MD.is_file():
        raise RuntimeError(f"Pre-registration missing: {HYPOTHESES_MD}")
    prereg_sha = IO.sha256_file(HYPOTHESES_MD)
    _log(f"=== S17-EULR runner | stage={args.stage} | prereg_sha256={prereg_sha[:16]} ===")

    footprint, cat_mask, sgmc_mask, r0_dots = _load_masks()
    folds, split_sha = _build_folds(cat_mask, footprint)
    fold_eligible, fold_dot_quota = _fold_quotas(folds, footprint)
    d_cat = ndi.distance_transform_edt(~cat_mask)
    full_eligible = footprint & (~cat_mask) & (d_cat > 3.0)
    del d_cat
    inventory_status = _registry_inventory_status()
    reg_paths = _registry_paths()
    _log(f"footprint={int(footprint.sum()):,} catalogue={int(cat_mask.sum()):,} "
         f"registry_paths={len(reg_paths)} inventory_verified={inventory_status['verified_present']} "
         f"not_checked={len(inventory_status['not_checked'])}")

    ctx: dict = {
        "args": args, "t0": t0, "prereg_sha256": prereg_sha,
        "footprint": footprint, "cat_mask": cat_mask, "sgmc_mask": sgmc_mask,
        "r0_dots": r0_dots, "folds": folds, "split_sha": split_sha,
        "fold_eligible": fold_eligible, "fold_dot_quota": fold_dot_quota,
        "full_eligible": full_eligible, "n_full_elig": int(full_eligible.sum()),
        "n_fp": int(footprint.sum()),
        "base_static_cols": list(range(34)) + [44, 45, 46, 47, 48],
        "inventory_status": inventory_status, "reg_paths": reg_paths,
    }

    stage_features(ctx)
    if args.stage == "features":
        return 0
    stage_canary(ctx)
    if args.stage == "canary":
        return 0
    if args.stage in ("experiments", "all"):
        stage_experiments(ctx)
        if args.stage == "experiments":
            return 0
    if args.stage in ("full", "all"):
        if "checkpoint" not in ctx:
            ctx["checkpoint"] = json.loads(CHECKPOINT_JSON.read_text(encoding="utf-8"))
        stage_full(ctx)
    _log(f"done stage={args.stage} in {time.perf_counter() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
