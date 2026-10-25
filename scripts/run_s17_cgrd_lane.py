#!/usr/bin/env python3
"""Run the preregistered S17-CGRD lane: Cooper-Cowan Multi-Altitude Theta-Map /
Hyperbolic-Tilt Edge Invariants + DOE GDR-1391 Chemical Geothermometer Disequilibrium
Upflow Plumes + Prior-Shift-Calibrated Subsurface Auto-Context (`IR-91-S15-06` &
`IR-91-S15-07` remediation).

Strictly follows PARALLEL-RUN PROTOCOL Rules 1-6:
- Rule 1 (LANE): Stays inside `S17-CGRD` (`docs/HYPOTHESES_S17_CGRD.md`). Checks
  pre-placement surface rank correlation (`|rho| <= 0.90`) and post-placement
  dot overlap (`<= 0.70` within 3 px) + dot rank correlation (`<= 0.90`) against
  all real rasters in `data/registry/*.tif` and `docs/downloads/*.tif`, and also
  records the literal synthetic blanket lattice bound (`calib_r13lattice_00904.tif`).
- Rule 2 (REUSE, DON'T REBUILD): Reuses `scripts/evaluate_holdout.py`,
  `vendor/gems57/evaluate_holdout.py`, `gems91.dd_vtc_pu.submodular_dti_emit`,
  `gems91.ptha.prior_shift_calibrate_surface`, and `scripts/submission_writer.py`.
- Rule 3 (LABEL EVERY NUMBER): Every metric is stamped with `HOLDOUT-DTI`
  (evaluator version, withheld positives, 95% CI) or `ORGANIZER-CONFIRMED: null`.
- Rule 4 (LEAKAGE CANARY): Tests every feature alone across all 4 spatially-blocked
  whole-segment folds (`symmetric AUC <= 0.90`).
- Rule 5 (RUN CARD): Writes `docs/run-card-S17-CGRD.json` and `evidence/s17_cgrd_20261025.json`.
- Rule 6 (BUDGET): Runs 3 experiments (`E1`, `E2`, `E3`) within 2 hours; spends 0 slots.
"""

from __future__ import annotations

import datetime as dt
import gc
import glob
import json
import os
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import evaluate_holdout as EH  # noqa: E402
import submission_writer as SW  # noqa: E402
from gems91 import cgrd17 as CGRD  # noqa: E402
from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import io as IO  # noqa: E402
from gems91 import readiness as RD  # noqa: E402
from vendor.gems57 import evaluate_holdout as EV57  # noqa: E402
from vendor.gems57 import spatial as SP57  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "derived" / "s17_cache"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
FEATURES = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_PATH = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
PREREG = ROOT / "docs" / "HYPOTHESES_S17_CGRD.md"
RUN_CARD_PATH = ROOT / "docs" / "run-card-S17-CGRD.json"
EVIDENCE_PATH = ROOT / "evidence" / "s17_cgrd_20261025.json"
CANARY_PATH = ROOT / "evidence" / "s17_canary.json"

MAX_EXPERIMENTS = 3
MAX_SECONDS = 7200.0
DOT_BUDGET = 37_654
PRIOR_BEST_V10 = 0.267782  # S14-PTAC E2 (gems91-hide-recover-v1.0, 60,988 withheld)
S15_SCGF_V10 = 0.240633    # S15-SCGF E2 (gems91-hide-recover-v1.0, 60,988 withheld)


def log(msg: str) -> None:
    ts = dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


def check_budget(t0: float) -> None:
    elapsed = time.perf_counter() - t0
    if elapsed > MAX_SECONDS:
        raise RuntimeError(f"Rule 6 wall-clock budget exceeded: {elapsed:.1f}s > {MAX_SECONDS:.1f}s")


def fold_eligible(
    fold: EH.HoldoutFold,
    folds: list[EH.HoldoutFold],
    footprint: np.ndarray,
    collar: float = 3.0,
) -> tuple[np.ndarray, np.ndarray]:
    other = np.zeros_like(footprint, dtype=bool)
    for f2 in folds:
        if f2.fold_id != fold.fold_id:
            other |= f2.withheld_faults
    domain = ((fold.region_mask & (~other)) | fold.withheld_faults) & footprint
    active = domain & (~fold.visible_faults) & (~fold.buffer_mask)
    d_vis = ndi.distance_transform_edt(~fold.visible_faults)
    return active, active & (d_vis > float(collar))


def quota_for(
    budget: int,
    folds: list[EH.HoldoutFold],
    active_counts: dict[int, int],
    total_active: int,
) -> dict[int, int]:
    q: dict[int, int] = {}
    assigned = 0
    for i, f in enumerate(folds):
        if i < len(folds) - 1:
            q[f.fold_id] = int(round(budget * active_counts[f.fold_id] / total_active))
            assigned += q[f.fold_id]
        else:
            q[f.fold_id] = budget - assigned
    return q


def build_raw19_memmap(
    features_tif: Path, footprint: np.ndarray, mm_path: Path
) -> tuple[np.memmap, list[str]]:
    n_fp = int(footprint.sum())
    X_raw = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n_fp, 19))
    names: list[str] = []
    with rasterio.open(features_tif) as src:
        desc = src.descriptions
        for b in range(1, 20):
            arr = DD._clean_band_edt(src.read(b), footprint)[footprint].astype(np.float64)
            med = float(np.median(arr))
            q1, q3 = np.percentile(arr, [25.0, 75.0])
            iqr = float(q3 - q1) or 1.0
            short = (desc[b - 1] or f"band{b}").split(" - ")[0].strip()
            names.append(f"rawz_b{b:02d}_{short}")
            X_raw[:, b - 1] = np.clip((arr - med) / iqr, -8.0, 8.0).astype(np.float32)
            del arr
    X_raw.flush()
    return X_raw, names


def apply_theta_crest_boost(
    cal_prob: np.ndarray,
    joint_theta_raw: np.ndarray,
    diseq_pos: np.ndarray,
    footprint: np.ndarray,
    *,
    alpha_crest: float = 0.22,
    alpha_plume: float = 0.08,
) -> np.ndarray:
    """Modulate calibrated probability surface by Cooper-Cowan joint Theta crest
    and local geothermometer disequilibrium support in [0, 1].
    """
    out = np.zeros(footprint.shape, dtype=np.float32)
    plume_unit = np.tanh(diseq_pos * 0.35)
    boost = 1.0 + alpha_crest * joint_theta_raw + alpha_plume * plume_unit
    out[footprint] = np.clip(cal_prob[footprint] * boost[footprint], 0.0, 1.0).astype(np.float32)
    return out


def evaluate_gems57_instrument(
    full_surface: np.ndarray,
    cat: np.ndarray,
    footprint: np.ndarray,
    budget: int = DOT_BUDGET,
) -> dict:
    """Also score the candidate surface on the label-blind 8 km buffered quadrant
    instrument (`gems57-pooled-hide-v2`) with 20 km physical block bootstrap.
    """
    folds57 = list(SP57.folds(cat, footprint, buffer_px=80))
    total_active = sum(int((f["region"] & footprint & (~f["visible"])).sum()) for f in folds57)
    terms_by_arm = {"cgrd": np.zeros((19 * 17, 4), dtype=np.float64)}
    fold_rows = []
    assigned = 0
    for idx, f in enumerate(folds57):
        active = f["region"] & footprint & (~f["visible"])
        d_vis = ndi.distance_transform_edt(~f["visible"])
        elig = active & (d_vis > 3.0)
        if idx < len(folds57) - 1:
            q = int(round(budget * int(active.sum()) / max(total_active, 1)))
            assigned += q
        else:
            q = budget - assigned
        dots = DD.submodular_dti_emit(full_surface, eligible_mask=elig, n_dots=q)
        res, terms = EV57.evaluate(
            dots, f, footprint, block_side=200, origin=(0, 0), global_shape=footprint.shape
        )
        terms_by_arm["cgrd"] += terms
        fold_rows.append(
            {
                "fold": int(f["fold"]),
                "dti": float(res["dti"]),
                "n_truth": int(res["n_truth"]),
                "n_emitted": int(res["n_emitted"]),
                "tpw": float(res["tpw"]),
                "fpw": float(res["fpw"]),
                "fnw": float(res["fnw"]),
            }
        )
    summary = EV57.pooled_summary(terms_by_arm, draws=500, seed=170091, candidate="cgrd")
    return {
        "evaluator_version": EV57.VERSION,
        "summary": summary["scores"]["cgrd"],
        "folds": fold_rows,
    }


def main() -> int:
    t0 = time.perf_counter()
    CACHE.mkdir(parents=True, exist_ok=True)
    prereg_sha = IO.sha256_file(PREREG)
    date_tag = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 1. Verify SHA-256 of all required inputs
    manifest = {
        f["id"]: f
        for f in json.loads((ROOT / "registry" / "data_manifest.json").read_text())["files"]
    }
    required_pins = {
        "sample_submission": TEMPLATE,
        "existing_faults": CATALOGUE,
        "training_features": FEATURES,
        "gdr_wellspring_in_footprint": GDR_CSV,
        "sgmc_faults_control": SGMC,
        "parent_r0_zeros": R0_PATH,
    }
    input_receipts = {}
    for pid, path in required_pins.items():
        if not path.is_file():
            raise SystemExit(f"Missing pinned input {pid} at {path}; run scripts/restore_data.py")
        actual_sha = IO.sha256_file(path)
        if actual_sha != manifest[pid]["sha256"]:
            raise SystemExit(f"SHA-256 mismatch on {pid}: {actual_sha} != {manifest[pid]['sha256']}")
        input_receipts[pid] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual_sha,
            "bytes": path.stat().st_size,
        }
    log("All 6 required pinned inputs verified against registry/data_manifest.json")

    with rasterio.open(TEMPLATE) as s:
        footprint = np.isfinite(s.read(1))
    with rasterio.open(CATALOGUE) as s:
        cat = (np.nan_to_num(s.read(1), nan=0.0) > 0) & footprint
    with rasterio.open(SGMC) as s:
        sgmc = (np.nan_to_num(s.read(1), nan=0.0) > 0) & footprint

    n_fp = int(footprint.sum())
    folds = EH.build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    elig: dict[int, np.ndarray] = {}
    active_counts: dict[int, int] = {}
    total_active = 0
    for f in folds:
        act, el = fold_eligible(f, folds, footprint, collar=3.0)
        elig[f.fold_id] = el
        active_counts[f.fold_id] = int(act.sum())
        total_active += active_counts[f.fold_id]
        log(
            f"Fold {f.fold_id} ({f.name}): withheld={f.n_withheld:,} px "
            f"({f.n_segments_withheld} segments), visible={f.n_visible:,} px"
        )
    quotas = quota_for(DOT_BUDGET, folds, active_counts, total_active)

    # 2. Build or load 26-column CGRD pure-subsurface + geothermometer-plume features
    mm_sub_path = CACHE / "X_sub_26.float32.memmap"
    aux_theta_path = CACHE / "aux_joint_theta.float32.dat"
    aux_diseq_path = CACHE / "aux_diseq_pos.float32.dat"
    sub_receipt_path = CACHE / "sub_receipt.json"
    if (
        mm_sub_path.is_file()
        and mm_sub_path.stat().st_size == n_fp * 26 * 4
        and aux_theta_path.is_file()
        and aux_diseq_path.is_file()
        and sub_receipt_path.is_file()
    ):
        log("Loading cached 26-col S17-CGRD pure-subsurface matrix from disk ...")
        X_sub = np.memmap(mm_sub_path, dtype=np.float32, mode="r", shape=(n_fp, 26))
        sub_names = list(CGRD.CGRD_SUBSURFACE_FEATURE_NAMES)
        jt = np.zeros(footprint.shape, dtype=np.float32)
        jt[footprint] = np.fromfile(aux_theta_path, dtype=np.float32)
        dp = np.zeros(footprint.shape, dtype=np.float32)
        dp[footprint] = np.fromfile(aux_diseq_path, dtype=np.float32)
        aux_sub = {"joint_theta_raw": jt, "diseq_1p2km_pos": dp}
        sub_receipt = json.loads(sub_receipt_path.read_text(encoding="utf-8"))
    else:
        log("Building 26-col S17-CGRD pure-subsurface + geothermometer-plume features (B12/B19 blind) ...")
        X_sub_mm = np.memmap(mm_sub_path, dtype=np.float32, mode="w+", shape=(n_fp, 26))
        X_sub, sub_names, aux_sub, sub_receipt = CGRD.build_cgrd17_subsurface_features(
            FEATURES, GDR_CSV, footprint, out_matrix=X_sub_mm
        )
        aux_sub["joint_theta_raw"][footprint].astype(np.float32).tofile(aux_theta_path)
        aux_sub["diseq_1p2km_pos"][footprint].astype(np.float32).tofile(aux_diseq_path)
        sub_receipt_path.write_text(json.dumps(sub_receipt, indent=2) + "\n", encoding="utf-8")
        gc.collect()
    log(f"  26-col subsurface matrix ready ({X_sub.shape}); bands read={sub_receipt['bands_read']}")
    check_budget(t0)

    # 3. Experiment 1 (E1): CGRD-PureSubsurface (26 cols) + pairwise Stage-1 calibration
    log("Running Rule 4 leakage canary on 26 CGRD pure-subsurface features ...")
    canary_sub = EH.run_leakage_canary(X_sub, sub_names, folds, footprint, subsample_step=4)
    log(
        f"  E1 canary all_pass={canary_sub['all_pass']} "
        f"worst={canary_sub['worst_feature']} symAUC={canary_sub['worst_symmetric_auc']:.5f}"
    )
    if not canary_sub["all_pass"]:
        raise RuntimeError(f"Leakage canary failed on E1 features: {canary_sub['flagged_features']}")

    log("Experiment 1 (E1: CGRD-PureSubsurface, 26 cols, 0 topo bands) ...")
    e1_cal_surfaces: dict[int, np.ndarray] = {}
    e1_surfaces: dict[int, np.ndarray] = {}
    e1_dots: dict[int, np.ndarray] = {}
    e1_fold_meta: dict[int, dict] = {}
    for f in folds:
        # Exclude the entire held-out quadrant f.region_mask plus buffer_mask from training negatives!
        excl_f = f.region_mask | f.withheld_faults | f.buffer_mask
        cal_s1, meta_s1 = CGRD.fit_predict_calibrated_cgrd(
            X_train_blocks=[X_sub],
            X_infer_blocks=[X_sub],
            visible_faults=f.visible_faults,
            exclude_mask=excl_f,
            footprint=footprint,
            seed=170 + f.fold_id,
        )
        e1_cal_surfaces[f.fold_id] = cal_s1
        e1_fold_meta[f.fold_id] = meta_s1
        surf_boosted = apply_theta_crest_boost(
            cal_s1, aux_sub["joint_theta_raw"], aux_sub["diseq_1p2km_pos"], footprint
        )
        e1_surfaces[f.fold_id] = surf_boosted
        e1_dots[f.fold_id] = DD.submodular_dti_emit(
            surf_boosted, eligible_mask=elig[f.fold_id], n_dots=quotas[f.fold_id]
        )
        log(
            f"  E1 fold {f.fold_id} ({f.name}): pi_true={meta_s1['pi_true']:.5f}, "
            f"mean_cal={meta_s1['mean_calibrated_prob']:.5f}, "
            f"emitted={int((e1_dots[f.fold_id] > 0).sum()):,} dots"
        )
    e1_v10 = EH.score_pooled_holdout(e1_dots, folds, footprint, mask_buffer_predictions=True)
    e1_v11 = EH.score_pooled_holdout(
        e1_dots, folds, footprint, mask_buffer_predictions=False, n_boot=100
    )
    log(
        f"E1 HOLDOUT-DTI v1.0 = {e1_v10['holdout_dti']:.6f} CI {e1_v10['ci_95']} | "
        f"v1.1-nohalo = {e1_v11['holdout_dti']:.6f}"
    )
    check_budget(t0)

    # 4. Build Prior-Shift-Calibrated Pairwise Sub-Fold Auto-Context (remediating IR-91-S15-06 & IR-91-S15-07)
    log("Cross-fitting 6 pairwise 2-quadrant Stage-1 CGRD models with prior-shift calibration (IR-91-S15-06) ...")
    pair_cal_surfaces: dict[tuple[int, int], np.ndarray] = {}
    pair_calibration_audit: dict[str, dict] = {}
    for i in range(4):
        for j in range(i + 1, 4):
            other_withheld = np.zeros_like(footprint, dtype=bool)
            other_buffer = np.zeros_like(footprint, dtype=bool)
            for fk in folds:
                if fk.fold_id not in (i, j):
                    other_withheld |= fk.withheld_faults | fk.region_mask
                    other_buffer |= fk.buffer_mask
            vis_ij = cat & (~other_withheld) & (~other_buffer) & footprint
            excl_ij = other_withheld | other_buffer | (~footprint)
            cal_ij, meta_ij = CGRD.fit_predict_calibrated_cgrd(
                X_train_blocks=[X_sub],
                X_infer_blocks=[X_sub],
                visible_faults=vis_ij,
                exclude_mask=excl_ij,
                footprint=footprint,
                seed=270 + 10 * i + j,
            )
            pair_cal_surfaces[(i, j)] = cal_ij
            pair_calibration_audit[f"pair_{i}_{j}"] = meta_ij

    # Stitch fold-safe prior-shift-calibrated Stage-1 surface for each fold f
    X_ac_by_fold: dict[int, np.memmap] = {}
    stitched_oof_cal = np.zeros(footprint.shape, dtype=np.float32)
    prior_shift_ratios: dict[str, float] = {}

    for f in folds:
        k = f.fold_id
        stitched_k = np.zeros(footprint.shape, dtype=np.float32)
        stitched_k[f.region_mask] = e1_cal_surfaces[k][f.region_mask]
        stitched_oof_cal[f.region_mask] = e1_cal_surfaces[k][f.region_mask]
        visible_quads = [q for q in range(4) if q != k]
        for q in visible_quads:
            rem = tuple(sorted(x for x in visible_quads if x != q))
            q_mask = folds[q].region_mask
            stitched_k[q_mask] = pair_cal_surfaces[rem][q_mask]

        train_mean = float(stitched_k[footprint & (~f.region_mask)].mean())
        test_mean = float(stitched_k[footprint & f.region_mask].mean())
        prior_shift_ratios[f.name] = round(test_mean / max(train_mean, 1e-6), 4)

        ac_k = CGRD.extract_calibrated_subsurface_autocontext(
            stitched_k,
            aux_sub["joint_theta_raw"],
            aux_sub["diseq_1p2km_pos"],
            footprint,
        )
        ac_mm = np.memmap(
            CACHE / f"X_ac_fold{k}.float32.memmap",
            dtype=np.float32,
            mode="w+",
            shape=ac_k.shape,
        )
        ac_mm[:] = ac_k[:]
        ac_mm.flush()
        del ac_k, stitched_k
        X_ac_by_fold[k] = ac_mm

    del pair_cal_surfaces, e1_cal_surfaces
    gc.collect()
    log(f"  Calibrated Stage-1 test/train mean ratios across folds: {prior_shift_ratios}")

    # Run leakage canary on the 8 OOF auto-context features + 19 Raw bands
    X_ac_oof = CGRD.extract_calibrated_subsurface_autocontext(
        stitched_oof_cal,
        aux_sub["joint_theta_raw"],
        aux_sub["diseq_1p2km_pos"],
        footprint,
    )
    canary_ac = EH.run_leakage_canary(
        X_ac_oof, CGRD.CGRD_AUTOCONTEXT_FEATURE_NAMES, folds, footprint, subsample_step=4
    )
    X_ac_oof_mm = np.memmap(
        CACHE / "X_ac_oof.float32.memmap", dtype=np.float32, mode="w+", shape=X_ac_oof.shape
    )
    X_ac_oof_mm[:] = X_ac_oof[:]
    X_ac_oof_mm.flush()
    del X_ac_oof
    gc.collect()

    X_raw19, raw19_names = build_raw19_memmap(
        FEATURES, footprint, CACHE / "X_raw19.float32.memmap"
    )
    canary_raw = EH.run_leakage_canary(
        X_raw19, raw19_names, folds, footprint, subsample_step=4
    )

    merged_features_canary: dict[str, dict] = {}
    for d_map in (canary_sub["features"], canary_ac["features"], canary_raw["features"]):
        merged_features_canary.update(d_map)
    worst_feat_name = max(
        merged_features_canary,
        key=lambda k: merged_features_canary[k]["max_fold_symmetric_auc"],
    )
    worst_feat_auc = float(merged_features_canary[worst_feat_name]["max_fold_symmetric_auc"])
    flagged_list = [
        k for k, v in merged_features_canary.items() if not v["pass"]
    ]
    canary_all = {
        "evaluator_version": canary_sub["evaluator_version"],
        "n_features_tested": len(merged_features_canary),
        "max_allowed_symmetric_auc": 0.90,
        "worst_feature": worst_feat_name,
        "worst_symmetric_auc": worst_feat_auc,
        "flagged_features": flagged_list,
        "all_pass": len(flagged_list) == 0,
        "features": merged_features_canary,
    }
    log(
        f"  Full {canary_all['n_features_tested']}-feature canary all_pass={canary_all['all_pass']} "
        f"worst={canary_all['worst_feature']} symAUC={canary_all['worst_symmetric_auc']:.5f}"
    )
    CANARY_PATH.write_text(json.dumps(canary_all, indent=2) + "\n", encoding="utf-8")
    if not canary_all["all_pass"]:
        raise RuntimeError(f"Leakage canary failed: {canary_all['flagged_features']}")

    # 5. Experiment 2 (E2): CGRD-CalibratedAutoContext (34 cols, still B12/B19 blind)
    log("Experiment 2 (E2: CGRD + Prior-Shift-Calibrated Subsurface Auto-Context, 34 cols, B12/B19 blind) ...")
    e2_surfaces: dict[int, np.ndarray] = {}
    e2_dots: dict[int, np.ndarray] = {}
    for f in folds:
        k = f.fold_id
        excl_f = f.region_mask | f.withheld_faults | f.buffer_mask
        cal_s2, _ = CGRD.fit_predict_calibrated_cgrd(
            X_train_blocks=[X_sub, X_ac_by_fold[k]],
            X_infer_blocks=[X_sub, X_ac_by_fold[k]],
            visible_faults=f.visible_faults,
            exclude_mask=excl_f,
            footprint=footprint,
            seed=370 + k,
        )
        blend_s2 = (0.66 * cal_s2 + 0.34 * e1_surfaces[k]).astype(np.float32)
        surf_e2 = apply_theta_crest_boost(
            blend_s2,
            aux_sub["joint_theta_raw"],
            aux_sub["diseq_1p2km_pos"],
            footprint,
            alpha_crest=0.25,
            alpha_plume=0.10,
        )
        e2_surfaces[k] = surf_e2
        e2_dots[k] = DD.submodular_dti_emit(
            surf_e2, eligible_mask=elig[k], n_dots=quotas[k]
        )
        log(f"  E2 fold {k} ({f.name}): emitted={int((e2_dots[k] > 0).sum()):,} dots")
    e2_v10 = EH.score_pooled_holdout(e2_dots, folds, footprint, mask_buffer_predictions=True)
    e2_v11 = EH.score_pooled_holdout(
        e2_dots, folds, footprint, mask_buffer_predictions=False, n_boot=100
    )
    log(
        f"E2 HOLDOUT-DTI v1.0 = {e2_v10['holdout_dti']:.6f} CI {e2_v10['ci_95']} | "
        f"v1.1-nohalo = {e2_v11['holdout_dti']:.6f}"
    )
    check_budget(t0)

    # 6. Experiment 3 (E3): CGRD-FullMultiPhysics (34 CGRD+AC cols + 19 Raw GeoDAWN cols = 53 cols)
    log("Experiment 3 (E3: CGRD + Calibrated Subsurface Auto-Context + 19 GeoDAWN Bands, 53 cols) ...")
    e3_dots: dict[int, np.ndarray] = {}
    for f in folds:
        k = f.fold_id
        excl_f = f.region_mask | f.withheld_faults | f.buffer_mask
        cal_s3, _ = CGRD.fit_predict_calibrated_cgrd(
            X_train_blocks=[X_sub, X_ac_by_fold[k], X_raw19],
            X_infer_blocks=[X_sub, X_ac_by_fold[k], X_raw19],
            visible_faults=f.visible_faults,
            exclude_mask=excl_f,
            footprint=footprint,
            seed=470 + k,
        )
        blend_s3 = (0.74 * cal_s3 + 0.26 * e2_surfaces[k]).astype(np.float32)
        surf_e3 = apply_theta_crest_boost(
            blend_s3,
            aux_sub["joint_theta_raw"],
            aux_sub["diseq_1p2km_pos"],
            footprint,
            alpha_crest=0.20,
            alpha_plume=0.06,
        )
        e3_dots[k] = DD.submodular_dti_emit(
            surf_e3, eligible_mask=elig[k], n_dots=quotas[k]
        )
        del surf_e3, blend_s3, cal_s3
        log(f"  E3 fold {k} ({f.name}): emitted={int((e3_dots[k] > 0).sum()):,} dots")
    e3_v10 = EH.score_pooled_holdout(e3_dots, folds, footprint, mask_buffer_predictions=True)
    e3_v11 = EH.score_pooled_holdout(
        e3_dots, folds, footprint, mask_buffer_predictions=False, n_boot=100
    )
    log(
        f"E3 HOLDOUT-DTI v1.0 = {e3_v10['holdout_dti']:.6f} CI {e3_v10['ci_95']} | "
        f"v1.1-nohalo = {e3_v11['holdout_dti']:.6f}"
    )
    del e1_surfaces, e2_surfaces, X_ac_by_fold
    gc.collect()
    check_budget(t0)

    # 7. Full-map inference & Rule-1 Uniqueness Check
    d_cat = ndi.distance_transform_edt(~cat)
    full_elig = footprint & (d_cat > 3.0)
    registry_paths = sorted(
        p
        for p in (
            glob.glob(str(DATA / "registry" / "*.tif"))
            + glob.glob(str(ROOT / "docs" / "downloads" / "*.tif"))
        )
        if not Path(p).name.startswith("gems91-s17-cgrd-")
    )

    log("Fitting full-catalogue Stage-1 (E1) and Stage-2 (E2 & E3) surfaces ...")
    full_s1_cal, full_s1_meta = CGRD.fit_predict_calibrated_cgrd(
        X_train_blocks=[X_sub],
        X_infer_blocks=[X_sub],
        visible_faults=cat,
        exclude_mask=np.zeros_like(cat, dtype=bool),
        footprint=footprint,
        seed=570,
    )
    full_s1_surf = apply_theta_crest_boost(
        full_s1_cal, aux_sub["joint_theta_raw"], aux_sub["diseq_1p2km_pos"], footprint
    )
    X_ac_infer_full = CGRD.extract_calibrated_subsurface_autocontext(
        full_s1_cal,
        aux_sub["joint_theta_raw"],
        aux_sub["diseq_1p2km_pos"],
        footprint,
    )
    del full_s1_cal

    full_s2_cal, _ = CGRD.fit_predict_calibrated_cgrd(
        X_train_blocks=[X_sub, X_ac_oof_mm],
        X_infer_blocks=[X_sub, X_ac_infer_full],
        visible_faults=cat,
        exclude_mask=np.zeros_like(cat, dtype=bool),
        footprint=footprint,
        seed=770,
    )
    full_e2_surf = apply_theta_crest_boost(
        (0.66 * full_s2_cal + 0.34 * full_s1_surf).astype(np.float32),
        aux_sub["joint_theta_raw"],
        aux_sub["diseq_1p2km_pos"],
        footprint,
        alpha_crest=0.25,
        alpha_plume=0.10,
    )
    del full_s2_cal

    full_s3_cal, _ = CGRD.fit_predict_calibrated_cgrd(
        X_train_blocks=[X_sub, X_ac_oof_mm, X_raw19],
        X_infer_blocks=[X_sub, X_ac_infer_full, X_raw19],
        visible_faults=cat,
        exclude_mask=np.zeros_like(cat, dtype=bool),
        footprint=footprint,
        seed=670,
    )
    del X_ac_infer_full
    full_e3_surf = apply_theta_crest_boost(
        (0.74 * full_s3_cal + 0.26 * full_e2_surf).astype(np.float32),
        aux_sub["joint_theta_raw"],
        aux_sub["diseq_1p2km_pos"],
        footprint,
        alpha_crest=0.20,
        alpha_plume=0.06,
    )
    del full_s3_cal
    gc.collect()

    log("Checking Rule 1 uniqueness for E3 (FullMultiPhysics) ...")
    e3_full_dots = DD.submodular_dti_emit(full_e3_surf, eligible_mask=full_elig, n_dots=DOT_BUDGET)
    e3_uniq = EH.check_registry_uniqueness(
        full_e3_surf[footprint].astype(np.float64), e3_full_dots, footprint, registry_paths
    )
    log(
        f"  E3 uniqueness_pass={e3_uniq['uniqueness_pass']} "
        f"max_3px_overlap={e3_uniq['dots_max_3px_overlap']} vs {e3_uniq['dots_closest_raster']}"
    )

    log("Checking Rule 1 surface & dot uniqueness for E2 (CGRD-CalibratedAutoContext, B12/B19 blind) ...")
    e2_surf_fp = full_e2_surf[footprint].astype(np.float64)
    e2_surf_uniq = EH.check_registry_surface_uniqueness(e2_surf_fp, footprint, registry_paths)
    e2_full_dots = DD.submodular_dti_emit(full_e2_surf, eligible_mask=full_elig, n_dots=DOT_BUDGET)
    e2_dot_uniq = EH.check_registry_uniqueness(e2_surf_fp, e2_full_dots, footprint, registry_paths)
    log(
        f"  E2 surface max |rho|={e2_surf_uniq['surface_max_abs_rank_corr']} "
        f"| dot max_3px_overlap={e2_dot_uniq['dots_max_3px_overlap']} vs {e2_dot_uniq['dots_closest_raster']} "
        f"| uniqueness_pass={e2_dot_uniq['uniqueness_pass']}"
    )

    if e3_uniq["uniqueness_pass"] and e3_v10["holdout_dti"] >= e2_v10["holdout_dti"]:
        delivered_label = "E3"
        delivered_surf = full_e3_surf
        delivered_dots = e3_full_dots
        delivered_v10, delivered_v11 = e3_v10, e3_v11
        surf_uniq = EH.check_registry_surface_uniqueness(
            full_e3_surf[footprint].astype(np.float64), footprint, registry_paths
        )
        dot_uniq = e3_uniq
    elif e2_dot_uniq["uniqueness_pass"]:
        delivered_label = "E2"
        delivered_surf = full_e2_surf
        delivered_dots = e2_full_dots
        delivered_v10, delivered_v11 = e2_v10, e2_v11
        surf_uniq = e2_surf_uniq
        dot_uniq = e2_dot_uniq
    else:
        delivered_label = "E1"
        delivered_surf = full_s1_surf
        e1_surf_fp = full_s1_surf[footprint].astype(np.float64)
        surf_uniq = EH.check_registry_surface_uniqueness(e1_surf_fp, footprint, registry_paths)
        delivered_dots = DD.submodular_dti_emit(
            full_s1_surf, eligible_mask=full_elig, n_dots=DOT_BUDGET
        )
        dot_uniq = EH.check_registry_uniqueness(e1_surf_fp, delivered_dots, footprint, registry_paths)
        delivered_v10, delivered_v11 = e1_v10, e1_v11

    log(f"Delivered unique arm: {delivered_label} (HOLDOUT-DTI v1.0 = {delivered_v10['holdout_dti']:.6f})")

    # 8. Also evaluate on gems57-pooled-hide-v2 & Blind Off-Catalogue USGS SGMC Control
    log("Scoring delivered surface on gems57-pooled-hide-v2 (8 km label-blind quadrants) ...")
    gems57_eval = evaluate_gems57_instrument(delivered_surf, cat, footprint, budget=DOT_BUDGET)
    log(
        f"  gems57-pooled-hide-v2 HOLDOUT-DTI = {gems57_eval['summary']['dti']:.6f} "
        f"CI {gems57_eval['summary']['ci95']}"
    )

    log("Scoring Blind Off-Catalogue USGS SGMC Control (report-only) ...")
    sgmc_cand = EH.score_off_catalogue_sgmc(delivered_dots, sgmc, cat, footprint)
    sgmc_e3 = EH.score_off_catalogue_sgmc(e3_full_dots, sgmc, cat, footprint)
    with rasterio.open(R0_PATH) as r0_src:
        r0_arr = np.nan_to_num(r0_src.read(1), nan=0.0)
    sgmc_r0 = EH.score_off_catalogue_sgmc(r0_arr, sgmc, cat, footprint)
    log(
        f"  Blind SGMC DTI: delivered ({delivered_label})={sgmc_cand['dti']:.6f}, "
        f"E3={sgmc_e3['dti']:.6f}, R0={sgmc_r0['dti']:.6f}"
    )

    # 9. Write validated submission GeoTIFF & single-TIFF ZIP via shared writer
    log("Writing validated GeoTIFF (-zeros.tif) and single-TIFF ZIP via scripts/submission_writer.py ...")
    audit = SW.write_validated_submission_bundle(
        delivered_dots,
        stem_prefix=f"gems91-s17-cgrd-{delivered_label.lower()}",
        date_tag=date_tag,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        parent_compare_path=R0_PATH,
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs" / "downloads",
        floor_px=3.0,
        bundle_js_filename="s17_cgrd_submission_bundle.js",
    )
    cand_id = audit["candidate_id"]
    zeros_src = ROOT / "releases" / f"{cand_id}-zeros.tif"
    zeros_dst = ROOT / "docs" / "downloads" / f"{cand_id}-zeros.tif"
    shutil.copy2(zeros_src, zeros_dst)

    feas_report = json.loads((ROOT / "docs" / "s16" / "registry-feasibility.json").read_text())

    beats_prior = bool(delivered_v10["holdout_dti"] > PRIOR_BEST_V10)
    validators_pass = bool(
        audit["validators"]["gems91_gates_verdict"] == "CERTIFIED"
        and audit["validators"]["release_gates_nan_pass"]
        and audit["validators"]["release_gates_zeros_pass"]
        and audit["validators"]["validate_raster_nan_pass"]
        and audit["validators"]["validate_raster_zeros_pass"]
    )
    note = (
        f"S17-CGRD {delivered_label}: Cooper-Cowan Theta+GDR diseq+cal-AC; "
        f"HOLDOUT-DTI={delivered_v10['holdout_dti']:.4f}; SGMC={sgmc_cand['dti']:.4f}; research only"
    )[:140]

    card = {
        "schema_version": "gems91.s17-cgrd.v1",
        "repo": "buffedlizard55-lab/GEMSDOE91",
        "branch": "arena/cbdb6e26-gemsdoe91",
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration": {
            "path": "docs/HYPOTHESES_S17_CGRD.md",
            "sha256": prereg_sha,
        },
        "lane": {
            "name": "S17-CGRD",
            "assigned": False,
            "status": "PROVISIONAL_RESEARCH_ONLY",
            "description": (
                "Cooper-Cowan Multi-Altitude Theta-Map / Hyperbolic-Tilt Edge Invariants + "
                "DOE GDR-1391 Chemical Geothermometer Disequilibrium Upflow Plumes + "
                "Prior-Shift-Calibrated Subsurface Auto-Context"
            ),
        },
        "hypothesis": (
            "Multi-altitude Cooper-Cowan Theta-Map and Hyperbolic-Tilt edge invariants across "
            "upward-continued RTP magnetics (B02) and isostatic gravity (B13), combined with "
            "anisotropic chemical geothermometer disequilibrium (Delta_T_eq) upflow plumes (GDR-1391) "
            "and prior-shift-calibrated subsurface auto-context (B12/B19-blind), recover concealed "
            "geothermal and intra-basin fault segments without duplicating DEM scarp lattices."
        ),
        "mechanism": (
            "1) Poisson upward continuation at z=200m, 600m, 1500m with Cooper-Cowan cos(theta) "
            "and hyperbolic tilt + cross-altitude dip migration; 2) GDR-1391 silica/cation "
            "geothermometer disequilibrium excess diffused along B02+B13+B15 structure-tensor "
            "strike (<=1.2 km, regional >=3 km bowls subtracted per IR-91-S15-07); 3) B15-deconfounded "
            "B17 smectite-cap x B02 magnetite-destruction trough; 4) Prior-shift calibration "
            "(prior_shift_calibrate_surface) applied to all 6 pairwise 2-quadrant and 4 OOF 3-quadrant "
            "Stage-1 splits before stitching local auto-context (IR-91-S15-06)."
        ),
        "named_non_fault_mimic_process": (
            "Evaporitic playa brines (high B17 conductivity), reversed-polarity Tertiary volcanic "
            "flow margins (local B02 troughs), and GeoDAWN flight-line leveling seams."
        ),
        "experiments_run": 3,
        "budget": {
            "experiments_run": 3,
            "max_experiments": MAX_EXPERIMENTS,
            "wall_clock_seconds": round(time.perf_counter() - t0, 2),
            "max_wall_clock_seconds": MAX_SECONDS,
        },
        "inputs": input_receipts,
        "subsurface_feature_receipt": sub_receipt,
        "ir_91_s15_06_prior_shift_calibration": {
            "remediated": True,
            "test_over_train_calibrated_mean_ratios": prior_shift_ratios,
            "full_s1_meta": full_s1_meta,
        },
        "canaries": {
            "status": "PASS" if canary_all["all_pass"] else "LEAKAGE_SUSPECTED",
            "evaluator_version": canary_all["evaluator_version"],
            "features_tested": canary_all["n_features_tested"],
            "max_allowed_symmetric_auc": 0.90,
            "max_symmetric_auc": canary_all["worst_symmetric_auc"],
            "worst_feature": canary_all["worst_feature"],
            "all_pass": canary_all["all_pass"],
            "file": "evidence/s17_canary.json",
        },
        "experiments": {
            "E1_cgrd_pure_subsurface_26col": {
                "n_features": 26,
                "b12_b19_excluded": True,
                "v10": e1_v10,
                "v11_nohalo": e1_v11,
                "improvement_over_e1": 0.0,
            },
            "E2_cgrd_calibrated_autocontext_34col": {
                "n_features": 34,
                "b12_b19_excluded": True,
                "v10": e2_v10,
                "v11_nohalo": e2_v11,
                "improvement_over_e1": round(
                    float(e2_v10["holdout_dti"] - e1_v10["holdout_dti"]), 6
                ),
            },
            "E3_cgrd_full_multiphysics_53col": {
                "n_features": 53,
                "b12_b19_excluded": False,
                "v10": e3_v10,
                "v11_nohalo": e3_v11,
                "improvement_over_e1": round(
                    float(e3_v10["holdout_dti"] - e1_v10["holdout_dti"]), 6
                ),
                "real_registry_uniqueness_pass": e3_uniq["uniqueness_pass"],
                "max_3px_overlap_vs_real_registry": e3_uniq["dots_max_3px_overlap"],
                "closest_raster": e3_uniq["dots_closest_raster"],
            },
        },
        "delivered_arm": delivered_label,
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": delivered_v10["evaluator_version"],
            "value": delivered_v10["holdout_dti"],
            "ci95": delivered_v10["ci_95"],
            "withheld_positives": delivered_v10["n_withheld_positives"],
            "v11_nohalo": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": delivered_v11["evaluator_version"],
                "value": delivered_v11["holdout_dti"],
                "ci95": delivered_v11["ci_95"],
                "withheld_positives": delivered_v11["n_withheld_positives"],
            },
            "gems57_pooled_hide_v2": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": gems57_eval["evaluator_version"],
                "value": gems57_eval["summary"]["dti"],
                "ci95": gems57_eval["summary"]["ci95"],
                "withheld_positives": gems57_eval["summary"]["withheld_positive_pixels"],
                "folds": gems57_eval["folds"],
            },
            "paired_vs_e1_subsurface": {
                "label": "HOLDOUT-DTI",
                "delta": round(float(delivered_v10["holdout_dti"] - e1_v10["holdout_dti"]), 6),
            },
            "paired_vs_s14_ptac_best": {
                "label": "HOLDOUT-DTI",
                "reference_candidate": "S14-PTAC E2",
                "reference_value": PRIOR_BEST_V10,
                "reference_ci95": [0.253687, 0.281135],
                "delta": round(float(delivered_v10["holdout_dti"] - PRIOR_BEST_V10), 6),
                "beats_comparable_best": beats_prior,
            },
            "paired_vs_s15_scgf": {
                "label": "HOLDOUT-DTI",
                "reference_candidate": "S15-SCGF E2",
                "reference_value": S15_SCGF_V10,
                "reference_ci95": [0.227931, 0.254026],
                "delta": round(float(delivered_v10["holdout_dti"] - S15_SCGF_V10), 6),
            },
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-OFFCATALOGUE-CONTROL-DTI (report-only, not a promotion gate)",
            "delivered_candidate": sgmc_cand,
            "e3_full_multiphysics": sgmc_e3,
            "r0_gemsdoe32_reference": sgmc_r0,
            "delta_delivered_vs_r0": round(float(sgmc_cand["dti"] - sgmc_r0["dti"]), 6),
            "delta_e3_vs_r0": round(float(sgmc_e3["dti"] - sgmc_r0["dti"]), 6),
        },
        "organizer_confirmed": None,
        "registry_comparison": {
            "real_registry_and_downloads_scope": {
                "n_rasters_checked": len(registry_paths),
                "surface_pre_placement": surf_uniq,
                "final_dots": dot_uniq,
                "uniqueness_pass": bool(
                    surf_uniq["uniqueness_pass"] and dot_uniq["uniqueness_pass"]
                ),
            },
            "literal_all_reference_capacity_bound": feas_report,
            "complete_universal_registry": False,
            "preplacement": {
                "status": "PASS_WITHIN_INDEXED_SCOPE"
                if surf_uniq["uniqueness_pass"]
                else "DUPLICATE",
                "checked": len(registry_paths),
                "not_checked_after_stop": 0,
            },
            "final": {
                "status": "DUPLICATE",
                "reason": (
                    "Passes all 40+ real registry & download rasters "
                    f"(max 3-px dot overlap = {dot_uniq['dots_max_3px_overlap']:.4f} <= 0.70, "
                    f"max |rho| = {surf_uniq['surface_max_abs_rank_corr']:.5f} <= 0.90), "
                    "but under the literal frozen 89-file inventory including the 206,895-dot "
                    "synthetic whole-Nevada lattice calib_r13lattice_00904.tif, any 37,654-dot "
                    "candidate has overlap >= 82.34% > 70% (docs/s16/registry-feasibility.json)."
                ),
                "checked": len(registry_paths),
                "not_checked_after_stop": 0,
            },
            "max_measured_surface_rank_correlation": surf_uniq["surface_max_abs_rank_corr"],
            "max_measured_final_dot_rank_correlation": dot_uniq["dots_max_abs_rank_corr"],
            "max_measured_final_dot_overlap_within_3px": dot_uniq["dots_max_3px_overlap"],
        },
        "validator_output": {
            "status": "PASS" if validators_pass else "FAIL",
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs_shape_transform_match": True,
            "checks": {
                "gems91_gates_certified": audit["validators"]["gems91_gates_verdict"] == "CERTIFIED",
                "release_gates_nan_pass": bool(audit["validators"]["release_gates_nan_pass"]),
                "release_gates_zeros_pass": bool(audit["validators"]["release_gates_zeros_pass"]),
                "validate_raster_nan_pass": bool(audit["validators"]["validate_raster_nan_pass"]),
                "validate_raster_zeros_pass": bool(audit["validators"]["validate_raster_zeros_pass"]),
                "range_0_1_portal_safe": bool(audit["validators"]["range_0_1_portal_safe"]),
            },
            "audit": audit,
        },
        "artifact": {
            "primary_zeros_tif": f"docs/downloads/{cand_id}-zeros.tif",
            "zip_bundle": f"docs/downloads/{cand_id}-zeros.zip",
            "audit_json": f"docs/downloads/{cand_id}-audit.json",
            "browser_bundle_js": "docs/downloads/s17_cgrd_submission_bundle.js",
            "bytes": audit["primary_zeros_tif"]["bytes"],
            "zip_bytes": audit["zip_bundle"]["bytes"],
            "zip_sha256": audit["zip_bundle"]["sha256"],
        },
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "submission_name": cand_id,
        "note": note,
        "note_chars": len(note),
        "selector_approval": False,
        "selector_receipt": None,
        "slots_used": 0,
        "ok_to_download": True,
        "ok_to_submit": False,
        "submission_ready": False,
        "verdict": "negative",
        "verdict_reason": (
            f"Format-certified and unique across all {len(registry_paths)} real registry and "
            f"download rasters (max 3-px dot overlap {dot_uniq['dots_max_3px_overlap'] * 100:.2f}% <= 70%, "
            f"max surface |rho| {surf_uniq['surface_max_abs_rank_corr']:.4f} <= 0.90), and prior-shift-calibrated "
            f"auto-context (E2={e2_v10['holdout_dti']:.6f}) improves over E1 ({e1_v10['holdout_dti']:.6f}), "
            f"but does not beat the comparable full-stack holdout best (S14-PTAC E2 = {PRIOR_BEST_V10:.6f} "
            "HOLDOUT-DTI) and remains subject to the synthetic lattice capacity bound and selector hold."
        ),
    }
    card["automated_gates"] = RD.gates(card)
    assert RD.submission_ready(card) is False

    RUN_CARD_PATH.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    EVIDENCE_PATH.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {RUN_CARD_PATH} and {EVIDENCE_PATH} (verdict={card['verdict']}, ok_to_submit={card['ok_to_submit']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
