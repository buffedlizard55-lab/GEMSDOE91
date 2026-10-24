#!/usr/bin/env python3
"""Execute the GEMSDOE91 First-Principles Discovery Lane (`H91-1`..`H91-3`).

Strictly enforces `PARALLEL-RUN PROTOCOL`:
  - Rule 1 (Lane / Uniqueness): Verifies continuous surface |Spearman rho| <= 0.90
    AND final emitted 3-px dot overlap <= 0.70 against all pinned registry &
    sibling rasters (`17` rasters total). Logs duplicate and halts if breached.
  - Rule 2 (Shared Infrastructure): Reuses `scripts/dti.py`, `scripts/evaluate_holdout.py`,
    `scripts/submission_writer.py`, `src/gems91/io.py`, `src/gems91/gates.py`,
    `src/gems91/release_gates.py`, and `scripts/validate_raster.py`.
  - Rule 3 (Score Provenance): Labels every holdout score `HOLDOUT-DTI` with
    evaluator version, withheld positive count, and 95% block-bootstrap CI;
    labels historical receipts `ORGANIZER-CONFIRMED`; emits zero projections.
  - Rule 4 (Leakage Canary First): Runs single-feature symmetric ROC-AUC canary
    across all 52 features (49 static + 3 fold-safe visible-catalogue) BEFORE
    scoring any model (`AUC > 0.90` fails closed).
  - Rule 5 (Run Card): Writes structured JSON Run Card to `evidence/run_card.json`
    and `docs/data/run_card.json`.
  - Rule 6 (Budget Cap): Executes strictly 3 pre-registered experiments (`E1`,
    `E2`, `E3`) against zero-feature-engineering reference `B0`, well inside
    the 3-experiment / 2-hour cap.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import evaluate_holdout as EH  # noqa: E402
import submission_writer as SW  # noqa: E402
from gems91 import dd_vtc_pu as DD  # noqa: E402

DATA = ROOT / "data"
TEMPLATE_TIF = DATA / "official" / "sample_submission.tif"
CATALOGUE_TIF = DATA / "official" / "existing_faults.tif"
FEATURES_TIF = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC_CONTROL_TIF = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_ZEROS_TIF = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"

CACHE_DIR = DATA / "derived"
EVIDENCE_DIR = ROOT / "evidence"
DOCS_DATA_DIR = ROOT / "docs" / "data"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"
RELEASES_DIR = ROOT / "releases"

FULL_DOT_BUDGET = 38_400  # 1.98% above R0's 37,654 dots; prevalence-calibrated for alpha=0.2, beta=0.8
MAX_EXPERIMENTS = 3


def _log(msg: str) -> None:
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


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


def main() -> int:
    t0 = time.perf_counter()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    RELEASES_DIR.mkdir(parents=True, exist_ok=True)

    for req in (TEMPLATE_TIF, CATALOGUE_TIF, FEATURES_TIF, GDR_CSV, SGMC_CONTROL_TIF, R0_ZEROS_TIF):
        if not req.is_file():
            raise FileNotFoundError(f"missing pinned input {req}; run scripts/restore_data.py first")

    _log("Loading footprint, known fault catalogue, R0 benchmark, and SGMC off-catalogue control...")
    with rasterio.open(TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE_TIF) as src:
        cat_mask = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC_CONTROL_TIF) as src:
        sgmc_mask = (src.read(1) > 0) & footprint
    with rasterio.open(R0_ZEROS_TIF) as src:
        r0_dots = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)

    n_fp = int(footprint.sum())
    n_cat = int(cat_mask.sum())
    _log(f"Grid {footprint.shape}: footprint={n_fp:,} px, known_catalogue={n_cat:,} px")

    # 1. Build spatially-blocked whole-segment hide-and-recover folds
    _log("Building 4 spatially-blocked whole-segment folds (bridge=3 px, buffer=10.0 px = 1.0 km)...")
    folds = EH.build_segment_buffered_folds(cat_mask, footprint, bridge_px=3, buffer_px=10.0)
    fold_eligible: dict[int, np.ndarray] = {}
    fold_dot_quota: dict[int, int] = {}
    total_active_px = 0
    active_counts: dict[int, int] = {}
    for f in folds:
        act, elig = _fold_active_and_eligible(f, folds, footprint, collar_px=3.0)
        fold_eligible[f.fold_id] = elig
        active_counts[f.fold_id] = int(act.sum())
        total_active_px += active_counts[f.fold_id]
        _log(
            f"  Fold {f.fold_id} ({f.name}): withheld={f.n_withheld:,} px "
            f"({f.n_segments_withheld:,} whole complexes), visible={f.n_visible:,} px, "
            f"eligible={int(elig.sum()):,} px"
        )
    assigned = 0
    for f in folds:
        if f.fold_id < 3:
            q = int(round(FULL_DOT_BUDGET * active_counts[f.fold_id] / total_active_px))
            fold_dot_quota[f.fold_id] = q
            assigned += q
        else:
            fold_dot_quota[f.fold_id] = FULL_DOT_BUDGET - assigned

    # 2. Build disk-backed static multi-physics feature stack (49 features, 100% licence-clean)
    _log("Building/loading disk-backed float32 static feature matrix (5,167,373 x 49)...")
    X_static, static_names, static_meta = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES_TIF,
        gdr_csv=GDR_CSV,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    _log(
        f"Static features ready ({len(static_names)} cols): "
        f"GDR Hot/Warm cells={static_meta['n_gdr_hot_warm_cells']:,}, "
        f"Newly-recovered blind >=90C geothermometer cells={static_meta['n_gdr_blind_geotherm90_cells']:,}"
    )

    # Compute & disk-cache fold-safe visible-catalogue features per fold (zero leakage!)
    fold_cat_paths: dict[int, Path] = {}
    fold_cat_for_canary: dict[int, tuple[np.ndarray, list[str]]] = {}
    for f in folds:
        fc_path = CACHE_DIR / f"h91_fold_cat_f{f.fold_id}.dat"
        if fc_path.is_file() and fc_path.stat().st_size == n_fp * 3 * 4:
            fc_mm = np.memmap(fc_path, dtype=np.float32, mode="r", shape=(n_fp, 3))
        else:
            _log(f"  Computing fold-safe visible tip/stepover/strike features for Fold {f.fold_id} ({f.name})...")
            fc_arr = DD.compute_fold_safe_catalogue_features(f.visible_faults, footprint)
            fc_mm_w = np.memmap(fc_path, dtype=np.float32, mode="w+", shape=(n_fp, 3))
            fc_mm_w[:] = fc_arr
            fc_mm_w.flush()
            del fc_arr, fc_mm_w
            fc_mm = np.memmap(fc_path, dtype=np.float32, mode="r", shape=(n_fp, 3))
        fold_cat_paths[f.fold_id] = fc_path
        fold_cat_for_canary[f.fold_id] = (fc_mm, list(DD.FOLD_CATALOGUE_FEATURE_NAMES))

    # 3. Rule 4: Single-feature leakage canary FIRST before running any experiment!
    _log("Running Rule 4 Single-Feature Leakage Canary across all 52 features (threshold: AUC <= 0.90)...")
    canary = EH.run_leakage_canary(
        X_static,
        static_names,
        folds,
        footprint,
        fold_specific_features=fold_cat_for_canary,
        subsample_step=4,
    )
    (EVIDENCE_DIR / "leakage_canary.json").write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")
    _log(
        f"Leakage Canary verdict: all_pass={canary['all_pass']} | "
        f"n_features={canary['n_features_tested']} | "
        f"worst={canary['worst_feature']} (symmetric AUC={canary['worst_symmetric_auc']:.4f} <= 0.90)"
    )
    if not canary["all_pass"]:
        raise RuntimeError(f"RULE 4 LEAKAGE CANARY FAILED: {canary['flagged_features']}")
    del fold_cat_for_canary
    gc.collect()

    # 4. Reference Zero-Feature-Engineering Benchmark B0 (Raw 19 GeoDAWN bands + d>=2.8 disk thinning)
    b0_cache_file = CACHE_DIR / "h91_b0_holdout_v1.json"
    if b0_cache_file.is_file():
        b0_cached = json.loads(b0_cache_file.read_text(encoding="utf-8"))
        b0_holdout = b0_cached["b0_holdout"]
        b0_cont_holdout = b0_cached["b0_cont_holdout"]
        _log(
            f"Loaded cached [B0 Reference] HOLDOUT-DTI = {b0_holdout['holdout_dti']:.6f} "
            f"(95% CI {b0_holdout['ci_95']}, n_withheld={b0_holdout['n_withheld_positives']:,})"
        )
    else:
        _log("Computing Reference Baseline B0 (Raw 19 GeoDAWN bands OOF + d>=2.8 px Poisson disk thinning)...")
        b0_dots_folds: dict[int, np.ndarray] = {}
        b0_surf_folds: dict[int, np.ndarray] = {}
        raw19_cols = list(range(19))
        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            surf_k = DD.fit_and_predict_oof_fold(
                X_static,
                raw19_cols,
                None,
                f.visible_faults,
                excl,
                footprint,
                use_pu_deconfound=False,
                seed=910 + f.fold_id,
            )
            b0_surf_folds[f.fold_id] = surf_k
            b0_dots_folds[f.fold_id] = DD.greedy_disk_thin_baseline(
                surf_k,
                eligible_mask=fold_eligible[f.fold_id],
                n_dots=fold_dot_quota[f.fold_id],
                min_dist_px=2.8,
            )
            gc.collect()
        b0_holdout = EH.score_pooled_holdout(b0_dots_folds, folds, footprint)
        b0_cont_holdout = EH.score_pooled_holdout(b0_surf_folds, folds, footprint, n_boot=50)
        b0_cache_file.write_text(
            json.dumps({"b0_holdout": b0_holdout, "b0_cont_holdout": b0_cont_holdout}, indent=2) + "\n",
            encoding="utf-8",
        )
        del b0_dots_folds, b0_surf_folds
        gc.collect()
        _log(
            f"  [B0 Reference] HOLDOUT-DTI = {b0_holdout['holdout_dti']:.6f} "
            f"(95% CI {b0_holdout['ci_95']}, n_withheld={b0_holdout['n_withheld_positives']:,}; "
            f"unthinned surface HOLDOUT-DTI = {b0_cont_holdout['holdout_dti']:.6f})"
        )

    # Also score R0 (`0.2778` leaderboard champion) on the 100% blind off-catalogue SGMC control
    r0_sgmc = EH.score_off_catalogue_sgmc(r0_dots, sgmc_mask, cat_mask, footprint, min_cat_dist_px=3.0)
    _log(
        f"  [R0 Benchmark 0.2778 ORGANIZER-CONFIRMED] Zero-SGMC Off-Catalogue Control DTI = "
        f"{r0_sgmc['dti']:.6f} (n_sgmc_offcat={r0_sgmc['n_offcatalogue_sgmc_positives']:,})"
    )

    # Pre-compute full-catalogue tip/stepover/strike features ONLY for post-fold full-map inference
    full_cat_fp_path = CACHE_DIR / "h91_full_cat_features.dat"
    if full_cat_fp_path.is_file() and full_cat_fp_path.stat().st_size == n_fp * 3 * 4:
        X_full_cat = np.memmap(full_cat_fp_path, dtype=np.float32, mode="r", shape=(n_fp, 3))
    else:
        fc_full_arr = DD.compute_fold_safe_catalogue_features(cat_mask, footprint)
        fc_full_mm = np.memmap(full_cat_fp_path, dtype=np.float32, mode="w+", shape=(n_fp, 3))
        fc_full_mm[:] = fc_full_arr
        fc_full_mm.flush()
        del fc_full_arr, fc_full_mm
        X_full_cat = np.memmap(full_cat_fp_path, dtype=np.float32, mode="r", shape=(n_fp, 3))

    d_cat_full = ndi.distance_transform_edt(~cat_mask)
    full_eligible = footprint & (~cat_mask) & (d_cat_full > 3.0)

    # 5. Strictly 3 Pre-Registered Experiments (Rule 6 Budget Cap: 3/3)
    experiments_spec = [
        {
            "exp_id": "E1",
            "hypothesis_id": "H91-1",
            "title": "Dip-Deprojected Verduzco Tilt + Multi-Scale Openness + 1D-Ridge Submodular 300m DTI",
            "col_indices": list(range(34)),  # RAW_19 + E1_15
            "n_total_features": 34,
            "use_gdr_prior": False,
            "use_fold_cat": False,
            "use_pu": False,
            "gamma": 1.30,
            "form_note_tag": "Dip-deproj Verduzco grav/RTP tilt+openness+claycap+1D-ridge 300m submod",
            "mechanism_summary": (
                "Synthesizes true signed Verduzco gravity tilt atan2(B11, B05) and RTP magnetic tilt atan2(B09, |grad B02|) "
                "from 100% official GeoDAWN bands and projects basement tilt edges updip along -grad(G_6(B13)) by H*cot(55 deg) "
                "using B15 basement depth to correct the 200-1000 m hanging-wall plan-view dip offset; combines 300 m & 1 km "
                "Local Relief Models, Laplacian openness, elevation structure-tensor coherence, and lateral conductivity cap edge "
                "|grad B17| inside a 4-fold spatially-blocked HGB+L2-LR ensemble, followed by Bayes-calibrated 1-D axial-ridge "
                "Minoux lazy-greedy 300 m submodular DTI dot allocation strictly > 3.0 px from existing_faults."
            ),
            "named_mimic": "Pleistocene Lake Lahontan wave-cut shorelines (constant-elevation benches lacking updip B11/B05 basement Verduzco tilt)",
        },
        {
            "exp_id": "E2",
            "hypothesis_id": "H91-1 + H91-2",
            "title": "Andersonian 12-Azimuth Ridge + 212 Blind >=90C Geothermometer & 2,060 Thermal GDR Conduits + Subsurface-Gated Exposure PU + 1D-Ridge Submodular 300m DTI",
            "col_indices": list(range(38)) + [43],  # RAW_19 + E1_15 + Andersonian/Coincidence(34..37) + Piedmont(43); GDR(38..42) via non-memorizing prior + 3 fold-cat = 47
            "n_total_features": 47,
            "use_gdr_prior": True,
            "use_fold_cat": True,
            "use_pu": True,
            "gamma": 1.30,
            "form_note_tag": "Dip-deproj Verduzco+Anderson+GDR90C+PU+300m submod",
            "mechanism_summary": (
                "Extends H91-1 with a 12-azimuth Morris (1996) slip/dilation steerable ridge bank, 3-way multi-physics "
                "coincidence gate, 2,060 stripped Hot/Warm + 212 newly-recovered >=90 C blind geothermometer GDR conduits, "
                "fold-safe visible fault tip/stepover continuation, and subsurface-gated Elkan-Noto exposure PU calibration."
            ),
            "named_mimic": "Alluvial-fan distributary channels & lateral outflow plumes (rejected by 3-way multi-physics coincidence gate & subsurface-gated PU propensity)",
        },
        {
            "exp_id": "E3",
            "hypothesis_id": "H91-1 + H91-2 + H91-3",
            "title": "Full 52-Feature Hydrothermal Magnetite-Destruction + Smectite Clay-Cap Breach + Seismic Swarm Conduit + PU + 1D-Ridge Submodular 300m DTI",
            "col_indices": list(range(38)) + [43] + list(range(44, 49)),  # + 5 E3 Hydrothermal Alteration/Seismic features + GDR(38..42) + 3 fold-cat = 52
            "n_total_features": 52,
            "use_gdr_prior": True,
            "use_fold_cat": True,
            "use_pu": True,
            "gamma": 1.35,
            "form_note_tag": "Dip-deproj Verduzco+MagTrough+ClayCap+PU+300m submod",
            "mechanism_summary": (
                "Extends H91-2 with 5 sponsor-only GeoDAWN hydrothermal rock-physics features: local RTP magnetite-destruction "
                "troughs, 300m-1.2km smectite clay-cap DoG, signed footwall polarity, and microseismic swarm fracture permeability."
            ),
            "named_mimic": "Unaltered Miocene basaltic feeder dikes (positive RTP peaks vs hydrothermal magnetite-destruction troughs) & broad evaporite playas (removed by 300m-1.2km clay-cap DoG)",
        },
    ]

    assert len(experiments_spec) <= MAX_EXPERIMENTS, "Rule 6 violation: > 3 experiments"

    experiment_results: list[dict] = []
    best_exp: dict | None = None
    best_full_surface: np.ndarray | None = None
    best_full_dots: np.ndarray | None = None

    for idx_exp, spec in enumerate(experiments_spec, start=1):
        t_exp = time.perf_counter()
        _log(f"=== Running Experiment {idx_exp}/{MAX_EXPERIMENTS}: {spec['exp_id']} ({spec['hypothesis_id']}) ===")
        fold_dots: dict[int, np.ndarray] = {}
        full_surf_accum = np.zeros(footprint.shape, dtype=np.float32)

        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            surf_k = DD.fit_and_predict_oof_fold(
                X_static,
                spec["col_indices"],
                None,
                f.visible_faults,
                excl,
                footprint,
                use_pu_deconfound=spec["use_pu"],
                seed=9100 + idx_exp * 10 + f.fold_id,
            )
            full_surf_accum += 0.25 * surf_k

            surf_eval = surf_k
            if spec["use_gdr_prior"]:
                surf_eval = DD.apply_gdr_hydrothermal_prior(surf_eval, X_static, footprint, strength=0.22)
            if spec["use_fold_cat"]:
                fc_fold = np.memmap(fold_cat_paths[f.fold_id], dtype=np.float32, mode="r", shape=(n_fp, 3))
                surf_eval = DD.apply_structural_relay_prior(surf_eval, fc_fold, footprint, strength=0.25)
                del fc_fold

            fold_dots[f.fold_id] = DD.submodular_dti_emit(
                surf_eval,
                eligible_mask=fold_eligible[f.fold_id],
                n_dots=fold_dot_quota[f.fold_id],
                gamma=spec["gamma"],
            )
            del surf_k, surf_eval
            gc.collect()

        holdout_res = EH.score_pooled_holdout(fold_dots, folds, footprint)
        del fold_dots
        gc.collect()

        if spec["use_gdr_prior"]:
            full_surf_accum = DD.apply_gdr_hydrothermal_prior(full_surf_accum, X_static, footprint, strength=0.22)
        if spec["use_fold_cat"]:
            full_surf_accum = DD.apply_structural_relay_prior(full_surf_accum, X_full_cat, footprint, strength=0.25)

        # Emit full-map candidate dots (38,400 dots, strictly > 3.0 px from existing_faults) for blind SGMC check
        cand_dots_tmp = DD.submodular_dti_emit(
            full_surf_accum,
            eligible_mask=full_eligible,
            n_dots=FULL_DOT_BUDGET,
            gamma=spec["gamma"],
        )
        reg_paths = EH.default_registry_paths()
        uniq_res = EH.check_registry_uniqueness(
            full_surf_accum[footprint],
            cand_dots_tmp,
            footprint,
            reg_paths,
        )
        sgmc_res = EH.score_off_catalogue_sgmc(cand_dots_tmp, sgmc_mask, cat_mask, footprint, min_cat_dist_px=3.0)
        elapsed_s = round(time.perf_counter() - t_exp, 2)

        n_feats_total = spec["n_total_features"]
        rec = {
            "experiment_number": idx_exp,
            "exp_id": spec["exp_id"],
            "hypothesis_id": spec["hypothesis_id"],
            "title": spec["title"],
            "n_features": n_feats_total,
            "use_pu_deconfound": spec["use_pu"],
            "gamma": spec["gamma"],
            "named_non_fault_mimic": spec["named_mimic"],
            "holdout": holdout_res,
            "delta_vs_b0_holdout_dti": round(holdout_res["holdout_dti"] - b0_holdout["holdout_dti"], 6),
            "sgmc_offcatalogue_control": sgmc_res,
            "delta_vs_r0_sgmc_dti": round(sgmc_res["dti"] - r0_sgmc["dti"], 6),
            "uniqueness_summary": {
                "uniqueness_pass": uniq_res["uniqueness_pass"],
                "max_surface_abs_rank_corr": uniq_res["surface_max_abs_rank_corr"],
                "max_3px_dot_overlap": uniq_res["dots_max_3px_overlap"],
                "closest_raster": uniq_res["dots_closest_raster"],
            },
            "elapsed_seconds": elapsed_s,
        }
        experiment_results.append(rec)
        _log(
            f"  [{spec['exp_id']}] HOLDOUT-DTI = {holdout_res['holdout_dti']:.6f} "
            f"(95% CI {holdout_res['ci_95']}, delta_vs_B0={rec['delta_vs_b0_holdout_dti']:+.6f}) | "
            f"SGMC-Control DTI = {sgmc_res['dti']:.6f} (delta_vs_R0={rec['delta_vs_r0_sgmc_dti']:+.6f}) | "
            f"Uniq={uniq_res['uniqueness_pass']} (max_ov={uniq_res['dots_max_3px_overlap']:.4f} vs {uniq_res['dots_closest_raster']}) "
            f"[{elapsed_s:.1f}s]"
        )

        # Primary selection criterion: highest HOLDOUT-DTI among Rule-1-unique arms!
        if uniq_res["uniqueness_pass"] and (
            best_exp is None or holdout_res["holdout_dti"] > best_exp["holdout"]["holdout_dti"]
        ):
            best_exp = rec
            best_spec = spec
            best_full_surface = full_surf_accum
            best_full_dots = cand_dots_tmp
            uniqueness = uniq_res
        else:
            del full_surf_accum, cand_dots_tmp
            gc.collect()

    if best_exp is None or best_full_surface is None or best_full_dots is None:
        raise RuntimeError("RULE 1 DUPLICATE DETECTED across all candidate arms — HALTING")

    best_sgmc_final = best_exp["sgmc_offcatalogue_control"]
    (EVIDENCE_DIR / "registry_uniqueness.json").write_text(
        json.dumps(uniqueness, indent=2) + "\n", encoding="utf-8"
    )
    _log(
        f"Selected {best_exp['exp_id']} ({best_exp['hypothesis_id']}): "
        f"HOLDOUT-DTI={best_exp['holdout']['holdout_dti']:.6f}, "
        f"Uniqueness pass={uniqueness['uniqueness_pass']} "
        f"(rasters_checked={uniqueness['n_registry_rasters_checked']}, "
        f"max_surface_rank_corr={uniqueness['surface_max_abs_rank_corr']:.4f} <= 0.90, "
        f"max_3px_dot_overlap={uniqueness['dots_max_3px_overlap']:.4f} <= 0.70)"
    )

    # 7. Write & Triple-Certify Submission GeoTIFFs + ZIP + Browser Base64 Bundle
    date_tag = "20261024T120000Z"
    stem_prefix = f"gems91-ddvtc-{best_exp['exp_id'].lower()}"
    _log(f"Writing & triple-validating submission bundle ({stem_prefix}-{date_tag})...")
    # Clean any stale builds in RELEASES_DIR & DOWNLOADS_DIR so only the single certified candidate is present
    for old_f in list(RELEASES_DIR.glob("gems91-ddvtc-*.tif")) + list(DOWNLOADS_DIR.glob("gems91-ddvtc-*")):
        old_f.unlink(missing_ok=True)

    sub_audit = SW.write_validated_submission_bundle(
        best_full_dots,
        stem_prefix=stem_prefix,
        date_tag=date_tag,
        template_path=TEMPLATE_TIF,
        catalogue_path=CATALOGUE_TIF,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        parent_compare_path=R0_ZEROS_TIF,
        releases_dir=RELEASES_DIR,
        downloads_dir=DOWNLOADS_DIR,
        floor_px=3.0,
    )
    cand_id = sub_audit["candidate_id"]
    sub_note = (
        f"GEMS91 {best_exp['exp_id']} ({best_exp['hypothesis_id']}): {best_spec['form_note_tag']} "
        f"({sub_audit['dots']['n_dots']}d >3px, [0,1] zeros)"
    )
    if len(sub_note) > 140:
        sub_note = sub_note[:140]
    assert len(sub_note) <= 140

    # Determine promote vs negative verdict strictly from objective gates:
    # Beats B0 on HOLDOUT-DTI, passes Leakage Canary, passes Uniqueness, passes all 3 Validator Suites
    beats_b0 = best_exp["holdout"]["holdout_dti"] > b0_holdout["holdout_dti"]
    all_validators_pass = (
        sub_audit["validators"]["gems91_gates_verdict"] == "CERTIFIED"
        and sub_audit["validators"]["release_gates_nan_pass"]
        and sub_audit["validators"]["release_gates_zeros_pass"]
        and sub_audit["validators"]["validate_raster_nan_pass"]
        and sub_audit["validators"]["validate_raster_zeros_pass"]
        and sub_audit["validators"]["range_0_1_portal_safe"]
    )
    verdict = "promote" if (beats_b0 and canary["all_pass"] and uniqueness["uniqueness_pass"] and all_validators_pass) else "negative"

    total_elapsed_s = round(time.perf_counter() - t0, 2)

    # 8. Rule 5: Emit Structured JSON RUN CARD
    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "repo": "buffedlizard55-lab/GEMSDOE91",
        "branch": "arena/5b9fd3e1-gemsdoe91",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": verdict,
        "ok_to_download_and_submit": bool(verdict == "promote"),
        "winning_experiment": best_exp["exp_id"],
        "hypothesis_id": best_exp["hypothesis_id"],
        "hypothesis": best_exp["title"],
        "physical_mechanism": best_spec["mechanism_summary"],
        "named_non_fault_mimic": best_exp["named_non_fault_mimic"],
        "budget": {
            "experiments_run": len(experiment_results),
            "max_experiments": MAX_EXPERIMENTS,
            "wall_clock_seconds": total_elapsed_s,
            "max_wall_clock_seconds": 7200,
        },
        "leakage_canary": {
            "evaluator_version": canary["evaluator_version"],
            "n_features_tested": canary["n_features_tested"],
            "max_allowed_symmetric_auc": canary["max_allowed_auc"],
            "worst_feature": canary["worst_feature"],
            "worst_symmetric_auc": canary["worst_symmetric_auc"],
            "all_pass": canary["all_pass"],
        },
        "scores": {
            "primary_holdout": {
                "label": "HOLDOUT-DTI",
                "evaluator_version": best_exp["holdout"]["evaluator_version"],
                "n_withheld_positives": best_exp["holdout"]["n_withheld_positives"],
                "score": best_exp["holdout"]["holdout_dti"],
                "ci_95": best_exp["holdout"]["ci_95"],
                "b0_reference_holdout_dti": b0_holdout["holdout_dti"],
                "b0_reference_ci_95": b0_holdout["ci_95"],
                "lift_over_b0": best_exp["delta_vs_b0_holdout_dti"],
            },
            "fleet_benchmark_reference": {
                "candidate": "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros (GEMSDOE32 R0)",
                "label": "ORGANIZER-CONFIRMED",
                "score": 0.2778,
            },
            "blind_sgmc_offcatalogue_control": {
                "label": "SGMC-OFFCAT-CONTROL-DTI (zero-shot external USGS geological map, >3px off-catalogue)",
                "evaluator_version": best_sgmc_final["evaluator_version"],
                "n_offcatalogue_sgmc_positives": best_sgmc_final["n_offcatalogue_sgmc_positives"],
                "candidate_dti": best_sgmc_final["dti"],
                "r0_02778_dti": r0_sgmc["dti"],
                "lift_over_r0_sgmc": round(best_sgmc_final["dti"] - r0_sgmc["dti"], 6),
            },
        },
        "experiments": experiment_results,
        "registry_uniqueness": {
            "rasters_checked": uniqueness["n_registry_rasters_checked"],
            "max_surface_abs_rank_corr": uniqueness["surface_max_abs_rank_corr"],
            "surface_closest_raster": uniqueness["surface_closest_raster"],
            "max_dots_abs_rank_corr": uniqueness["dots_max_abs_rank_corr"],
            "max_3px_dot_overlap": uniqueness["dots_max_3px_overlap"],
            "dots_closest_raster": uniqueness["dots_closest_raster"],
            "uniqueness_pass": uniqueness["uniqueness_pass"],
        },
        "submission": {
            "candidate_id": cand_id,
            "recommended_upload_file": sub_audit["primary_zeros_tif"]["filename"],
            "recommended_zip_download": sub_audit["zip_bundle"]["filename"],
            "recommended_form_name": cand_id,
            "recommended_form_note": sub_note,
            "recommended_form_note_length": len(sub_note),
            "sha256_zeros_tif": sub_audit["primary_zeros_tif"]["sha256"],
            "sha256_nan_tif": sub_audit["companion_nan_tif"]["sha256"],
            "sha256_zeros_zip": sub_audit["zip_bundle"]["sha256"],
            "bytes_zeros_tif": sub_audit["primary_zeros_tif"]["bytes"],
            "bytes_zeros_zip": sub_audit["zip_bundle"]["bytes"],
            "n_dots": sub_audit["dots"]["n_dots"],
            "min_catalogue_distance_px": sub_audit["dots"]["min_catalogue_distance_px"],
            "dots_le_3px": sub_audit["dots"]["dots_le_3px"],
            "nodata_zeros_tif": sub_audit["primary_zeros_tif"]["nodata"],
            "all_12279160_cells_finite": sub_audit["primary_zeros_tif"]["all_cells_finite"],
            "min_value": sub_audit["primary_zeros_tif"]["min_value"],
            "max_value": sub_audit["primary_zeros_tif"]["max_value"],
            "validators": sub_audit["validators"],
        },
    }

    (EVIDENCE_DIR / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n", encoding="utf-8")
    (DOCS_DATA_DIR / "run_card.json").write_text(json.dumps(run_card, indent=2) + "\n", encoding="utf-8")
    (DOCS_DATA_DIR / "run_card.js").write_text(
        f"window.GEMS91_RUN_CARD = {json.dumps(run_card, separators=(',', ':'))};\n",
        encoding="utf-8",
    )

    _log("=== H91 DISCOVERY LANE COMPLETE ===")
    _log(f"Verdict: {verdict.upper()} | Candidate: {cand_id}")
    _log(f"Primary Upload File: {sub_audit['primary_zeros_tif']['filename']} (sha256={sub_audit['primary_zeros_tif']['sha256']})")
    _log(f"Form Note ({len(sub_note)}/140 chars): {sub_note}")
    _log(f"Total wall-clock time: {total_elapsed_s:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
