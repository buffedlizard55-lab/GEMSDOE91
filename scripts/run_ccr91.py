#!/usr/bin/env python3
"""Run the provisional CCR91 compensated-conductivity residual lane.

This lane was preregistered in docs/HYPOTHESES_CCR91.md.  It reuses the shared
holdout evaluator and submission writer.  The literal directed registry gate is
applied to the full surface before placement and to final dots after placement;
a failure stops further experiments but still permits packaging the failed
candidate as an explicitly research-only negative deliverable.
"""

from __future__ import annotations

import gc
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
for p in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import evaluate_holdout as EH  # noqa: E402
import submission_writer as SW  # noqa: E402
from gems91 import ccr as CCR  # noqa: E402
from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import mhtr_coda as MC  # noqa: E402
from vendor.gems57.validate import validate as validate_gems57  # noqa: E402

DATA = ROOT / "data"
TEMPLATE_TIF = DATA / "official" / "sample_submission.tif"
CATALOGUE_TIF = DATA / "official" / "existing_faults.tif"
FEATURES_TIF = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC_TIF = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_TIF = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
CACHE = DATA / "derived"
EVIDENCE = ROOT / "evidence"
DOCS = ROOT / "docs"
DOWNLOADS = DOCS / "downloads"
RELEASES = ROOT / "releases"
RUN_CARD = DOCS / "run-card-CCR91.json"
FULL_DOT_BUDGET = 48_000
MAX_EXPERIMENTS = 3
MAX_SECONDS = 7_200
CURRENT_BEST = 0.206406
CURRENT_BEST_CI = [0.193796, 0.220176]


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def registry_paths() -> list[Path]:
    paths: list[Path] = []
    for folder in (DATA / "fleet_registry", DATA / "registry", DOWNLOADS):
        if folder.is_dir():
            paths.extend(folder.glob("*.tif"))
    # The shared evaluator deduplicates same-named paths during comparison. The
    # pre-run receipt reports both path count and compared same-grid identities.
    return sorted({p.resolve() for p in paths})


def fold_domains(
    folds: list[EH.HoldoutFold], footprint: np.ndarray
) -> tuple[dict[int, np.ndarray], dict[int, int]]:
    eligible: dict[int, np.ndarray] = {}
    active_n: dict[int, int] = {}
    for fold in folds:
        other = np.zeros_like(footprint, dtype=bool)
        for f2 in folds:
            if f2.fold_id != fold.fold_id:
                other |= f2.withheld_faults
        domain = ((fold.region_mask & (~other)) | fold.withheld_faults) & footprint
        active = domain & (~fold.visible_faults) & (~fold.buffer_mask)
        d_vis = ndi.distance_transform_edt(~fold.visible_faults)
        eligible[fold.fold_id] = active & (d_vis > 3.0)
        active_n[fold.fold_id] = int(active.sum())
    quotas: dict[int, int] = {}
    total = sum(active_n.values())
    assigned = 0
    for fold in folds:
        if fold.fold_id < len(folds) - 1:
            q = int(round(FULL_DOT_BUDGET * active_n[fold.fold_id] / total))
            quotas[fold.fold_id] = q
            assigned += q
        else:
            quotas[fold.fold_id] = FULL_DOT_BUDGET - assigned
    return eligible, quotas


def fit_surface(
    cache_path: Path,
    X_static: np.ndarray,
    static_cols: list[int],
    X_s11: np.ndarray,
    s11_cols: list[int],
    X_ccr: np.ndarray,
    ccr_cols: list[int],
    visible: np.ndarray,
    exclude: np.ndarray,
    footprint: np.ndarray,
    seed: int,
) -> np.ndarray:
    n_fp = int(footprint.sum())
    if cache_path.is_file() and cache_path.stat().st_size == n_fp * 4:
        out = np.zeros(footprint.shape, dtype=np.float32)
        out[footprint] = np.fromfile(cache_path, dtype=np.float32)
        return out
    out = CCR.fit_and_predict_ccr_oof_fold(
        X_static,
        static_cols,
        X_s11,
        s11_cols,
        X_ccr,
        ccr_cols,
        visible,
        exclude,
        footprint,
        seed=seed,
    )
    out[footprint].astype(np.float32).tofile(cache_path)
    return out


def main() -> int:
    started = time.perf_counter()
    if RUN_CARD.exists():
        raise RuntimeError(f"locked completed experiment exists: {RUN_CARD}; refusing silent rerun")
    for folder in (CACHE, EVIDENCE, DOWNLOADS, RELEASES):
        folder.mkdir(parents=True, exist_ok=True)
    for required in (TEMPLATE_TIF, CATALOGUE_TIF, FEATURES_TIF, GDR_CSV, SGMC_TIF, R0_TIF):
        if not required.is_file():
            raise FileNotFoundError(f"missing pinned input {required}; run scripts/restore_data.py")

    log("Loading pinned footprint/catalogue/control rasters")
    with rasterio.open(TEMPLATE_TIF) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE_TIF) as src:
        catalogue = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC_TIF) as src:
        sgmc = (src.read(1) > 0) & footprint

    folds = EH.build_segment_buffered_folds(catalogue, footprint, bridge_px=3, buffer_px=10.0)
    eligible, quotas = fold_domains(folds, footprint)
    n_withheld = sum(f.n_withheld for f in folds)
    if n_withheld != 60_988:
        raise RuntimeError(f"unexpected withheld-positive count {n_withheld}; expected 60988")

    log("Building/reusing 49 static, 16 MHTR, and 6 new CCR cached features")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES_TIF, gdr_csv=GDR_CSV, footprint=footprint, cache_dir=CACHE
    )
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE
    )
    X_ccr, ccr_names, ccr_meta = CCR.build_or_load_ccr_feature_memmap(
        features_tif=FEATURES_TIF, footprint=footprint, cache_dir=CACHE
    )

    # Existing S11 canary receipt covers every reused base column on these exact
    # folds.  Run the shared canary anew for every CCR feature before fitting E1.
    base_canary = json.loads((EVIDENCE / "s11_leakage_canary.json").read_text())
    if not base_canary.get("all_pass"):
        raise RuntimeError("reused S11 base-feature leakage canary is not PASS")
    ccr_canary = EH.run_leakage_canary(X_ccr, ccr_names, folds, footprint, subsample_step=4)
    (EVIDENCE / "ccr91_leakage_canary.json").write_text(json.dumps(ccr_canary, indent=2) + "\n")
    log(
        f"CCR leakage canary: {ccr_canary['n_features_tested']} features, "
        f"worst symmetric AUC={ccr_canary['worst_symmetric_auc']:.5f}"
    )
    if not ccr_canary["all_pass"]:
        raise RuntimeError(f"CCR leakage canary failed: {ccr_canary['flagged_features']}")

    mhtr_edge, piedmont = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    ccr_edge = CCR.ccr_edge_field(X_ccr, footprint)
    d_cat = ndi.distance_transform_edt(~catalogue)
    full_eligible = footprint & (~catalogue) & (d_cat > 3.0)
    reg_paths = registry_paths()
    log(f"Available registry scope: {len(reg_paths)} paths (frozen inventory is missing 2 pins)")

    # Frozen order from the preregistration. E2/E3 are reached only if the prior
    # experiment passes both literal lane-drift checks.
    configs = [
        {
            "id": "E1",
            "title": "CCR-joint: S11-E2 learner/emitter plus all six compensated-conductivity residual features",
            "ccr_cols": list(range(6)),
            "gate_strength": 0.0,
        },
        {
            "id": "E2",
            "title": "CCR-gated: E1 with preregistered 0.12 residual-contact corroboration",
            "ccr_cols": list(range(6)),
            "gate_strength": 0.12,
        },
        {
            "id": "E3",
            "title": "CCR-parsimonious: S11-E2 plus residual, residual-gradient, and residual-DoG only",
            "ccr_cols": [0, 1, 2],
            "gate_strength": 0.0,
        },
    ]
    static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    s11_cols = list(range(16))
    experiments: list[dict] = []
    final_surface: np.ndarray | None = None
    final_dots: np.ndarray | None = None
    final_surface_gate: dict | None = None
    final_dot_gate: dict | None = None
    final_sgmc: dict | None = None
    stopped_reason: str | None = None

    for exp_index, cfg in enumerate(configs):
        if exp_index >= MAX_EXPERIMENTS or time.perf_counter() - started >= MAX_SECONDS:
            stopped_reason = "budget reached before next experiment"
            break
        exp_start = time.perf_counter()
        log(f"Experiment {cfg['id']}: {cfg['title']}")
        fold_dots: dict[int, np.ndarray] = {}
        for fold in folds:
            exclusion = fold.region_mask | fold.withheld_faults | fold.buffer_mask
            surf = fit_surface(
                CACHE / f"ccr91_{cfg['id'].lower()}_oof_f{fold.fold_id}.dat",
                X_static,
                static_cols,
                X_s11,
                s11_cols,
                X_ccr,
                cfg["ccr_cols"],
                fold.visible_faults,
                exclusion,
                footprint,
                seed=2400 + exp_index * 10 + fold.fold_id,
            )
            if cfg["gate_strength"]:
                surf = np.where(
                    footprint,
                    np.clip(surf * (1.0 + cfg["gate_strength"] * (ccr_edge - 0.5)), 0.0, 1.0),
                    0.0,
                ).astype(np.float32)
            fold_dots[fold.fold_id] = MC.mhtr_corridor_submodular_emit(
                surf,
                mhtr_edge,
                piedmont,
                eligible_mask=eligible[fold.fold_id],
                n_dots=quotas[fold.fold_id],
                gamma=1.20,
                mhtr_weight=0.48,
                piedmont_quota_frac=0.24,
                min_spacing_px=2.45,
            )
            del surf
            gc.collect()
        holdout = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=291 + exp_index)
        del fold_dots
        gc.collect()

        full_surface = fit_surface(
            CACHE / f"ccr91_{cfg['id'].lower()}_full.dat",
            X_static,
            static_cols,
            X_s11,
            s11_cols,
            X_ccr,
            cfg["ccr_cols"],
            catalogue,
            np.zeros_like(footprint, dtype=bool),
            footprint,
            seed=2500 + exp_index,
        )
        if cfg["gate_strength"]:
            full_surface = np.where(
                footprint,
                np.clip(full_surface * (1.0 + cfg["gate_strength"] * (ccr_edge - 0.5)), 0.0, 1.0),
                0.0,
            ).astype(np.float32)

        # Rule 1 phase 1 is deliberately before final placement.
        surface_gate = EH.check_registry_surface_uniqueness(
            full_surface[footprint], footprint, reg_paths
        )
        exp_record = {
            "experiment_number": exp_index + 1,
            "experiment_id": cfg["id"],
            "title": cfg["title"],
            "n_reused_features": len(static_cols) + len(s11_cols),
            "n_ccr_features": len(cfg["ccr_cols"]),
            "holdout": holdout,
            "delta_vs_current_best_holdout_dti": round(holdout["holdout_dti"] - CURRENT_BEST, 6),
            "preplacement_surface_gate": surface_gate,
            "elapsed_seconds_before_placement": round(time.perf_counter() - exp_start, 2),
        }
        if not surface_gate["uniqueness_pass"]:
            exp_record["verdict"] = "duplicate-surface-stop"
            experiments.append(exp_record)
            stopped_reason = "surface rank-correlation exceeded 0.90; stopped before placement"
            final_surface = full_surface
            final_surface_gate = surface_gate
            break

        dots = MC.mhtr_corridor_submodular_emit(
            full_surface,
            mhtr_edge,
            piedmont,
            eligible_mask=full_eligible,
            n_dots=FULL_DOT_BUDGET,
            gamma=1.20,
            mhtr_weight=0.48,
            piedmont_quota_frac=0.24,
            min_spacing_px=2.45,
        )
        dot_gate = EH.check_registry_uniqueness(full_surface[footprint], dots, footprint, reg_paths)
        sgmc_result = EH.score_off_catalogue_sgmc(dots, sgmc, catalogue, footprint)
        exp_record.update({
            "final_dot_gate": dot_gate,
            "sgmc_offcatalogue_control": sgmc_result,
            "elapsed_seconds": round(time.perf_counter() - exp_start, 2),
            "verdict": "pass" if dot_gate["uniqueness_pass"] else "duplicate-final-dots-stop",
        })
        experiments.append(exp_record)
        log(
            f"{cfg['id']} HOLDOUT-DTI={holdout['holdout_dti']:.6f} "
            f"CI={holdout['ci_95']} (n={holdout['n_withheld_positives']}); "
            f"surface rho={surface_gate['surface_max_abs_rank_corr']:.5f}; "
            f"dot overlap={dot_gate['dots_max_3px_overlap']:.5f}"
        )
        final_surface = full_surface
        final_dots = dots
        final_surface_gate = surface_gate
        final_dot_gate = dot_gate
        final_sgmc = sgmc_result
        if not dot_gate["uniqueness_pass"]:
            stopped_reason = "final directed 3-pixel dot overlap exceeded 0.70; stopped under Rule 1"
            break
        del full_surface, dots
        gc.collect()

    if not experiments:
        raise RuntimeError("no experiment completed")
    winner = max(experiments, key=lambda r: r["holdout"]["holdout_dti"])
    beats_best = bool(winner["holdout"]["holdout_dti"] > CURRENT_BEST)

    # A surface-only stop cannot produce honest final dots. In the expected dense-
    # registry case E1 reaches final placement and is packaged as a negative.
    if final_dots is None or final_dot_gate is None or final_surface_gate is None:
        raise RuntimeError(stopped_reason or "no final dot candidate available")

    audit = SW.write_validated_submission_bundle(
        final_dots,
        stem_prefix="gems91-ccr91-e1-research",
        date_tag="20261024T235900Z",
        template_path=TEMPLATE_TIF,
        catalogue_path=CATALOGUE_TIF,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        parent_compare_path=R0_TIF,
        releases_dir=RELEASES,
        downloads_dir=DOWNLOADS,
        floor_px=3.0,
        bundle_js_filename="ccr91_submission_bundle.js",
    )
    zeros_name = audit["primary_zeros_tif"]["filename"]
    zeros_release = RELEASES / zeros_name
    zeros_download = DOWNLOADS / zeros_name
    shutil.copy2(zeros_release, zeros_download)
    g57 = validate_gems57(zeros_download, footprint=footprint, catalogue=catalogue)
    if not g57["all_checks_passed"]:
        raise RuntimeError(f"vendor validator failed: {g57}")

    all_gates = bool(
        beats_best
        and ccr_canary["all_pass"]
        and final_surface_gate["uniqueness_pass"]
        and final_dot_gate["uniqueness_pass"]
    )
    note = (
        "CCR91: depth-compensated conductivity+gravity contact; all gates pass; pending separate slot selector."
        if all_gates
        else "CCR91 research-only: depth-compensated conductivity+gravity contact; duplicate gate failed; do not submit."
    )
    if len(note) > 140:
        raise RuntimeError("submission note exceeds 140 characters")
    elapsed = round(time.perf_counter() - started, 2)
    card = {
        "schema": "gems-parallel-run-card-v1",
        "session": "CCR91",
        "repo": "buffedlizard55-lab/GEMSDOE91",
        "branch": "arena/02c6b911-gemsdoe91",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis": winner["title"],
        "mechanism": (
            "Depth-quantile median residualization of B17 conductivity against B15 basement depth, followed by "
            "residual gradient/DoG curvature and B13/B05 gravity-edge alignment in low-relief covered terrain."
        ),
        "named_non_fault_process_that_could_mimic_it": "saline groundwater or clay-rich basin fill",
        "lane_assignment_status": "provisional autonomous selection; assigned method paragraph absent from user brief",
        "budget": {
            "experiments_run": len(experiments),
            "max_experiments": MAX_EXPERIMENTS,
            "wall_clock_seconds": elapsed,
            "max_wall_clock_seconds": MAX_SECONDS,
            "stopped_reason": stopped_reason,
        },
        "leakage_canary": {
            "reused_base_receipt": "evidence/s11_leakage_canary.json",
            "reused_base_features": base_canary["n_features_tested"],
            "new_ccr_features": ccr_canary["n_features_tested"],
            "new_ccr_worst_feature": ccr_canary["worst_feature"],
            "new_ccr_worst_symmetric_auc": ccr_canary["worst_symmetric_auc"],
            "threshold": 0.90,
            "pass": ccr_canary["all_pass"],
        },
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "n_withheld_positives": winner["holdout"]["n_withheld_positives"],
            "score": winner["holdout"]["holdout_dti"],
            "ci_95": winner["holdout"]["ci_95"],
            "current_best_reference": CURRENT_BEST,
            "current_best_reference_ci_95": CURRENT_BEST_CI,
            "beats_current_best": beats_best,
            "organizer_score": None,
        },
        "experiments": experiments,
        "correlation_overlap_vs_registry": {
            "registry_scope_complete": False,
            "available_paths_checked": final_dot_gate["n_registry_rasters_checked"],
            "missing_pinned_references": 2,
            "uniqueness_gate_version": EH.UNIQUENESS_GATE_VERSION,
            "surface_max_abs_rank_corr": final_surface_gate["surface_max_abs_rank_corr"],
            "surface_closest_raster": final_surface_gate["surface_closest_raster"],
            "final_max_directed_dot_overlap_3px": final_dot_gate["dots_max_3px_overlap"],
            "final_closest_raster": final_dot_gate["dots_closest_raster"],
            "surface_pass": final_surface_gate["uniqueness_pass"],
            "final_dots_pass": final_dot_gate["uniqueness_pass"],
        },
        "sgmc_offcatalogue_control": final_sgmc,
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "validator_output": {
            "status": "PASS",
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs_shape_transform_match": True,
            "all_cells_finite": audit["primary_zeros_tif"]["all_cells_finite"],
            "nodata": audit["primary_zeros_tif"]["nodata"],
            "min_value": audit["primary_zeros_tif"]["min_value"],
            "max_value": audit["primary_zeros_tif"]["max_value"],
            "min_catalogue_distance_px": audit["dots"]["min_catalogue_distance_px"],
            "dots_le_3px": audit["dots"]["dots_le_3px"],
            "shared_writer_validators": audit["validators"],
            "vendor_gems57": g57,
        },
        "submission_name": audit["candidate_id"],
        "note": note,
        "note_length": len(note),
        "download": f"docs/downloads/{zeros_name}",
        "zip_download": audit["zip_bundle"]["path"],
        "verdict": "promote" if all_gates else "negative",
        "ok_to_download": True,
        "ok_to_submit": all_gates,
        "weekly_slots_used": 0,
        "feature_receipt": ccr_meta,
    }
    RUN_CARD.write_text(json.dumps(card, indent=2) + "\n")
    (EVIDENCE / "ccr91_run_card.json").write_text(json.dumps(card, indent=2) + "\n")
    (EVIDENCE / "ccr91_registry_surface.json").write_text(json.dumps(final_surface_gate, indent=2) + "\n")
    (EVIDENCE / "ccr91_registry_final.json").write_text(json.dumps(final_dot_gate, indent=2) + "\n")
    log(f"CCR91 {card['verdict'].upper()}: {zeros_name}; sha256={card['raster_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
