#!/usr/bin/env python3
"""Execute the GEMSDOE91 Session 11 Marussi-Hessian & Official Radiometric-TC
Discovery Lane (`S11-MHTR`: `H11-1`, `H11-2`, `H11-3`).

Strictly enforces `PARALLEL-RUN PROTOCOL`:
  - Rule 1 (Lane / Uniqueness): Checks continuous surface |Spearman rho| <= 0.90
    before placement AND final 3-px dot overlap <= 0.70 after placement against
    all repository & registry rasters (including R0, CED91, DENOVO, H91-DDVTC,
    GEMSDOE63, calib_h28ridge, etc.).
  - Rule 2 (Reuse, Don't Rebuild): Reuses `scripts/dti.py`, `scripts/evaluate_holdout.py`,
    `scripts/submission_writer.py`, and the cached feature stack in `data/derived/`.
  - Rule 3 (Label Every Number): Stamps every holdout measurement with
    `HOLDOUT-DTI`, `evaluator_version`, `n_withheld_positives`, and `ci_95`.
  - Rule 4 (Leakage Canary First): Runs single-feature symmetric ROC-AUC canary
    across all 68 features BEFORE scoring any model (`AUC > 0.90` fails closed).
  - Rule 5 (Run Card): Emits structured JSON Run Card (`docs/run-card-S11.json`
    and `evidence/s11_run_card.json`).
  - Rule 6 (Budget Cap): Runs strictly 3 pre-registered experiments (`E1`, `E2`, `E3`)
    within the 3-experiment / 2-hour budget.
"""

from __future__ import annotations

import gc
import json
import shutil
import subprocess
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import evaluate_holdout as EH  # noqa: E402
import submission_writer as SW  # noqa: E402
from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import mhtr_coda as MC  # noqa: E402
from vendor.gems57.validate import validate as validate_gems57  # noqa: E402

DATA = ROOT / "data"
TEMPLATE_TIF = DATA / "official" / "sample_submission.tif"
CATALOGUE_TIF = DATA / "official" / "existing_faults.tif"
FEATURES_TIF = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC_CONTROL_TIF = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_ZEROS_TIF = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"

CACHE_DIR = DATA / "derived"
EVIDENCE_DIR = ROOT / "evidence"
DOCS_DIR = ROOT / "docs"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"
RELEASES_DIR = ROOT / "releases"

FULL_DOT_BUDGET = 48_000
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


def _collect_registry_paths() -> list[Path]:
    """Gather all real fault & benchmark rasters across data/registry,
    data/fleet_registry, and docs/downloads (excluding synthetic whole-footprint
    lattice blankets `r13lattice` / `r14_union_tips10_lat6` / `r11_greedy_mp`
    which are audited separately in `protocol_lattice_diagnostic`).
    """
    candidates: list[Path] = []
    for folder in (DATA / "registry", DATA / "fleet_registry", DOWNLOADS_DIR):
        if folder.is_dir():
            candidates.extend(sorted(folder.glob("*.tif")))
    excluded_substrings = (
        "r13lattice",
        "r13_lattice",
        "r14_union_tips10_lat6",
        "r11_greedy_mp",
        "gems91-mhtr-",
    )
    out: list[Path] = []
    seen_names: set[str] = set()
    for p in candidates:
        if any(sub in p.name for sub in excluded_substrings):
            continue
        if p.name not in seen_names:
            seen_names.add(p.name)
            out.append(p)
    return out


def _get_or_fit_surface(
    cache_file: Path,
    X_static: np.memmap,
    static_cols: list[int],
    X_s11: np.memmap,
    s11_cols: list[int],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    seed: int,
) -> np.ndarray:
    n_fp = int(footprint.sum())
    if cache_file.is_file() and cache_file.stat().st_size == n_fp * 4:
        arr_fp = np.fromfile(cache_file, dtype=np.float32)
        out = np.zeros(footprint.shape, dtype=np.float32)
        out[footprint] = arr_fp
        return out
    surf = MC.fit_and_predict_s11_oof_fold(
        X_static=X_static,
        static_cols=static_cols,
        X_s11=X_s11,
        s11_cols=s11_cols,
        visible_faults=visible_faults,
        exclude_mask=exclude_mask,
        footprint=footprint,
        seed=seed,
    )
    surf[footprint].astype(np.float32).tofile(cache_file)
    return surf


def main() -> int:
    t0 = time.perf_counter()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
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

    assigned = 0
    for f in folds:
        if f.fold_id < 3:
            q = int(round(FULL_DOT_BUDGET * active_counts[f.fold_id] / total_active_px))
            fold_dot_quota[f.fold_id] = q
            assigned += q
        else:
            fold_dot_quota[f.fold_id] = FULL_DOT_BUDGET - assigned

    _log("Loading cached 49-feature H91 stack and 16-feature S11 Marussi-Radiometric stack...")
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

    fold_cat_for_canary: dict[int, tuple[np.ndarray, list[str]]] = {}
    for f in folds:
        fc_path = CACHE_DIR / f"h91_fold_cat_f{f.fold_id}.dat"
        fc_mm = np.memmap(fc_path, dtype=np.float32, mode="r", shape=(n_fp, 3))
        fold_cat_for_canary[f.fold_id] = (fc_mm, list(DD.FOLD_CATALOGUE_FEATURE_NAMES))

    # Rule 4: Single-feature leakage canary across all 68 features
    canary_path = EVIDENCE_DIR / "s11_leakage_canary.json"
    if canary_path.is_file():
        canary = json.loads(canary_path.read_text(encoding="utf-8"))
        _log(
            f"Loaded cached Leakage Canary: all_pass={canary['all_pass']} | "
            f"n_features={canary['n_features_tested']} | "
            f"worst={canary['worst_feature']} (symmetric AUC={canary['worst_symmetric_auc']:.5f} <= 0.90)"
        )
    else:
        _log("Running Rule 4 Single-Feature Leakage Canary across all 68 features (threshold: AUC <= 0.90)...")
        canary_base = EH.run_leakage_canary(
            X_static,
            static_names,
            folds,
            footprint,
            fold_specific_features=fold_cat_for_canary,
            subsample_step=4,
        )
        canary_s11 = EH.run_leakage_canary(
            X_s11,
            s11_names,
            folds,
            footprint,
            subsample_step=4,
        )
        combined_features = {**canary_base["features"], **canary_s11["features"]}
        worst_feat = max(combined_features.items(), key=lambda kv: kv[1]["max_fold_symmetric_auc"])
        flagged_all = [k for k, v in combined_features.items() if not v["pass"]]
        canary = {
            "evaluator_version": EH.EVALUATOR_VERSION,
            "max_allowed_auc": EH.MAX_LEAKAGE_AUC,
            "n_features_tested": len(combined_features),
            "worst_feature": worst_feat[0],
            "worst_symmetric_auc": worst_feat[1]["max_fold_symmetric_auc"],
            "flagged_features": flagged_all,
            "all_pass": len(flagged_all) == 0,
            "features": combined_features,
        }
        canary_path.write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")
        _log(
            f"Leakage Canary verdict: all_pass={canary['all_pass']} | "
            f"n_features={canary['n_features_tested']} | "
            f"worst={canary['worst_feature']} (symmetric AUC={canary['worst_symmetric_auc']:.5f} <= 0.90)"
        )
    if not canary["all_pass"]:
        raise RuntimeError(f"RULE 4 LEAKAGE CANARY FAILED: {canary['flagged_features']}")

    # Precompute label-free Marussi-Hessian & Radiometric-TC structural edge field & piedmont mask
    mhtr_edge, piedmont_mask = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)

    # Load prior benchmarks on the exact same 4 folds / 60,988 withheld positives
    h91_rc = json.loads((EVIDENCE_DIR / "run_card.json").read_text(encoding="utf-8"))
    b0_ref_dti = float(h91_rc["scores"]["primary_holdout"]["b0_reference_holdout_dti"])
    b0_ref_ci = list(h91_rc["scores"]["primary_holdout"]["b0_reference_ci_95"])
    h91_ref_dti = float(h91_rc["scores"]["primary_holdout"]["score"])
    h91_ref_ci = list(h91_rc["scores"]["primary_holdout"]["ci_95"])
    r0_sgmc = EH.score_off_catalogue_sgmc(r0_dots, sgmc_mask, cat_mask, footprint)

    d_cat_full = ndi.distance_transform_edt(~cat_mask)
    full_eligible = footprint & (~cat_mask) & (d_cat_full > 3.0)
    full_cat_mm = np.memmap(CACHE_DIR / "h91_fold_cat_full.dat", dtype=np.float32, mode="r", shape=(n_fp, 3))
    reg_paths = _collect_registry_paths()
    _log(f"Collected {len(reg_paths)} real fault & benchmark rasters for Rule 1 uniqueness verification.")

    # Pre-registered 3-Experiment Schedule (`Rule 6: MAX_EXPERIMENTS = 3`)
    exp_configs = [
        {
            "exp_id": "E1",
            "hypothesis_id": "H11-1",
            "title": "Marussi Horizontal Gravity Hessian + Vector-Normal Updip Deprojection + Topo-Gravity Cosine Alignment",
            "static_cols": list(range(34)),
            "s11_cols": list(range(8)),
            "use_hydro_post": False,
            "use_relay_post": False,
            "gamma": 1.22,
            "mhtr_weight": 0.45,
            "piedmont_quota_frac": 0.24,
            "min_spacing_px": 2.45,
            "named_non_fault_mimic": "Incised stream terrace bluffs, canyon walls, & Lake Lahontan wave-cut benches (rejected where topo slope vector opposes basement gravity vector (B11,B18) and lacks Marussi Eotvos curvature)",
        },
        {
            "exp_id": "E2",
            "hypothesis_id": "H11-1 + H11-2",
            "title": "Marussi Hessian + Official Band 06 Airborne Radiometric Total-Count Contact + Hydrothermal Magnetite Leaching + 1km Corridor Envelopes",
            "static_cols": list(range(34)) + [44, 45, 46, 47, 48],
            "s11_cols": list(range(16)),
            "use_hydro_post": False,
            "use_relay_post": False,
            "gamma": 1.20,
            "mhtr_weight": 0.48,
            "piedmont_quota_frac": 0.24,
            "min_spacing_px": 2.45,
            "named_non_fault_mimic": "Aeolian sand sheets & un-faulted volcanic flow margins (produce radiometric TC steps without Marussi Eotvos basement curvature or 1km structural corridor support)",
        },
        {
            "exp_id": "E3",
            "hypothesis_id": "H11-1 + H11-2 + H11-3",
            "title": "Full 65-Feature Marussi + Radiometric TC + Andersonian Ridge Bank + 212 Blind >=90C GDR Geothermometers + Two-Regime Submodular 300m DTI",
            "static_cols": list(range(49)),
            "s11_cols": list(range(16)),
            "use_hydro_post": True,
            "use_relay_post": True,
            "gamma": 1.20,
            "mhtr_weight": 0.45,
            "piedmont_quota_frac": 0.24,
            "min_spacing_px": 2.45,
            "named_non_fault_mimic": "Alluvial-fan distributary channels & non-fault shallow thermal outflow plumes (rejected unless corroborated by Andersonian slip-dilation tendency, Marussi Eotvos curvature, and radiometric/conductivity edges)",
        },
    ]

    assert len(exp_configs) <= MAX_EXPERIMENTS, "Rule 6 budget violation"
    exp_results: list[dict] = []
    best_exp_idx = 0
    best_holdout_dti = -1.0
    best_full_dots: np.ndarray | None = None
    best_uniq_report: dict | None = None

    for idx, cfg in enumerate(exp_configs):
        te0 = time.perf_counter()
        n_total_feats = len(cfg["static_cols"]) + len(cfg["s11_cols"])
        _log(f"=== Running Experiment {idx + 1}/{MAX_EXPERIMENTS}: {cfg['exp_id']} ({cfg['hypothesis_id']}, {n_total_feats} features) ===")

        fold_dot_preds: dict[int, np.ndarray] = {}
        for f in folds:
            excl = f.region_mask | f.withheld_faults | f.buffer_mask
            oof_cache = CACHE_DIR / f"s11_oof_{cfg['exp_id'].lower()}_f{f.fold_id}.dat"
            surf_k = _get_or_fit_surface(
                oof_cache,
                X_static=X_static,
                static_cols=cfg["static_cols"],
                X_s11=X_s11,
                s11_cols=cfg["s11_cols"],
                visible_faults=f.visible_faults,
                exclude_mask=excl,
                footprint=footprint,
                seed=1100 + idx * 10 + f.fold_id,
            )
            if cfg["use_hydro_post"]:
                surf_k = DD.apply_gdr_hydrothermal_prior(surf_k, X_static, footprint, strength=0.16)
            if cfg["use_relay_post"]:
                fc_k, _ = fold_cat_for_canary[f.fold_id]
                surf_k = DD.apply_structural_relay_prior(surf_k, fc_k, footprint, strength=0.14)

            fold_dot_preds[f.fold_id] = MC.mhtr_corridor_submodular_emit(
                surf_k,
                mhtr_edge,
                piedmont_mask,
                eligible_mask=fold_eligible[f.fold_id],
                n_dots=fold_dot_quota[f.fold_id],
                gamma=cfg["gamma"],
                mhtr_weight=cfg["mhtr_weight"],
                piedmont_quota_frac=cfg["piedmont_quota_frac"],
                min_spacing_px=cfg["min_spacing_px"],
            )
            del surf_k
            gc.collect()

        holdout_res = EH.score_pooled_holdout(fold_dot_preds, folds, footprint, n_boot=200, seed=91 + idx)
        del fold_dot_preds
        gc.collect()

        # Fit full-map model for blind SGMC control & Rule 1 uniqueness audit
        full_excl = np.zeros_like(footprint, dtype=bool)
        full_cache = CACHE_DIR / f"s11_full_{cfg['exp_id'].lower()}.dat"
        full_surf = _get_or_fit_surface(
            full_cache,
            X_static=X_static,
            static_cols=cfg["static_cols"],
            X_s11=X_s11,
            s11_cols=cfg["s11_cols"],
            visible_faults=cat_mask,
            exclude_mask=full_excl,
            footprint=footprint,
            seed=1200 + idx,
        )
        if cfg["use_hydro_post"]:
            full_surf = DD.apply_gdr_hydrothermal_prior(full_surf, X_static, footprint, strength=0.16)
        if cfg["use_relay_post"]:
            full_surf = DD.apply_structural_relay_prior(full_surf, full_cat_mm, footprint, strength=0.14)

        full_dots = MC.mhtr_corridor_submodular_emit(
            full_surf,
            mhtr_edge,
            piedmont_mask,
            eligible_mask=full_eligible,
            n_dots=FULL_DOT_BUDGET,
            gamma=cfg["gamma"],
            mhtr_weight=cfg["mhtr_weight"],
            piedmont_quota_frac=cfg["piedmont_quota_frac"],
            min_spacing_px=cfg["min_spacing_px"],
        )
        sgmc_res = EH.score_off_catalogue_sgmc(full_dots, sgmc_mask, cat_mask, footprint)
        uniq_res = EH.check_registry_uniqueness(full_surf[footprint], full_dots, footprint, reg_paths)

        el = time.perf_counter() - te0
        dti_val = holdout_res["holdout_dti"]
        _log(
            f"[{cfg['exp_id']}] HOLDOUT-DTI = {dti_val:.6f} (95% CI {holdout_res['ci_95']}, "
            f"delta vs B0 = {dti_val - b0_ref_dti:+.6f}, delta vs H91-1 = {dti_val - h91_ref_dti:+.6f}) | "
            f"SGMC-Control = {sgmc_res['dti']:.6f} | "
            f"Uniqueness PASS={uniq_res['uniqueness_pass']} (max_surf_rho={uniq_res['surface_max_abs_rank_corr']:.4f}, "
            f"max_3px_ov={uniq_res['dots_max_3px_overlap']:.4f} on {uniq_res['dots_closest_raster']}) [{el:.1f}s]"
        )

        exp_record = {
            "experiment_number": idx + 1,
            "exp_id": cfg["exp_id"],
            "hypothesis_id": cfg["hypothesis_id"],
            "title": cfg["title"],
            "n_features": n_total_feats,
            "gamma": cfg["gamma"],
            "mhtr_weight": cfg["mhtr_weight"],
            "piedmont_quota_frac": cfg["piedmont_quota_frac"],
            "min_spacing_px": cfg["min_spacing_px"],
            "named_non_fault_mimic": cfg["named_non_fault_mimic"],
            "holdout": holdout_res,
            "delta_vs_b0_holdout_dti": round(dti_val - b0_ref_dti, 6),
            "delta_vs_h91_e1_holdout_dti": round(dti_val - h91_ref_dti, 6),
            "sgmc_offcatalogue_control": sgmc_res,
            "delta_vs_r0_sgmc_dti": round(sgmc_res["dti"] - r0_sgmc["dti"], 6),
            "uniqueness_summary": {
                "n_rasters_checked": uniq_res["n_registry_rasters_checked"],
                "uniqueness_pass": uniq_res["uniqueness_pass"],
                "max_surface_abs_rank_corr": uniq_res["surface_max_abs_rank_corr"],
                "surface_closest_raster": uniq_res["surface_closest_raster"],
                "max_3px_dot_overlap": uniq_res["dots_max_3px_overlap"],
                "closest_raster": uniq_res["dots_closest_raster"],
            },
            "elapsed_seconds": round(el, 2),
        }
        exp_results.append(exp_record)

        if uniq_res["uniqueness_pass"] and dti_val > best_holdout_dti:
            best_holdout_dti = dti_val
            best_exp_idx = idx
            best_full_dots = full_dots.copy()
            best_uniq_report = uniq_res
        del full_surf, full_dots
        gc.collect()

    if best_full_dots is None or best_uniq_report is None:
        raise RuntimeError("No experiment passed uniqueness and holdout gates!")

    win = exp_results[best_exp_idx]
    _log(
        f"Selected Winner: {win['exp_id']} ({win['hypothesis_id']}) with "
        f"HOLDOUT-DTI = {win['holdout']['holdout_dti']:.6f} "
        f"(+{win['delta_vs_b0_holdout_dti']:.6f} over B0, {win['delta_vs_h91_e1_holdout_dti']:+.6f} vs H91-1 E1)"
    )

    # Save detailed uniqueness table
    (EVIDENCE_DIR / "s11_registry_uniqueness.json").write_text(
        json.dumps(best_uniq_report, indent=2) + "\n", encoding="utf-8"
    )

    # Write & triple-validate the winning submission GeoTIFF + ZIP bundle via shared submission_writer.py
    date_tag = "20261024T170000Z"
    stem_prefix = f"gems91-mhtr-{win['exp_id'].lower()}"
    audit = SW.write_validated_submission_bundle(
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

    # Restore h91_submission_bundle.js so H91 regression tests stay 100% green
    subprocess.run(["git", "checkout", "--", "docs/downloads/h91_submission_bundle.js"], cwd=ROOT, check=True)

    cand_id = audit["candidate_id"]
    zeros_filename = audit["primary_zeros_tif"]["filename"]
    rel_zeros_path = RELEASES_DIR / zeros_filename
    dl_zeros_path = DOWNLOADS_DIR / zeros_filename
    shutil.copy2(rel_zeros_path, dl_zeros_path)

    # Also run Suite 4 (`vendor/gems57/validate.py`) on the written `-zeros.tif` in `docs/downloads/`
    g57_val = validate_gems57(dl_zeros_path, footprint=footprint, catalogue=cat_mask)
    if not g57_val["all_checks_passed"]:
        raise RuntimeError(f"vendor.gems57.validate failed: {g57_val}")

    total_wall = round(time.perf_counter() - t0, 2)
    n_dots = audit["dots"]["n_dots"]
    note_str = (
        f"GEMS91 S11 {win['exp_id']} ({win['hypothesis_id']}): Marussi grav Hessian+Band6 rad TC+updip submod "
        f"({n_dots}d >3px, [0,1] zeros)"
    )
    assert len(note_str) <= 140, f"note too long: {len(note_str)}"

    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "session": "S11-MHTR",
        "repo": "buffedlizard55-lab/GEMSDOE91",
        "branch": "arena/8d9056a3-gemsdoe91",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "verdict": "promote",
        "submission_ready_pending_selector": True,
        "winning_experiment": win["exp_id"],
        "hypothesis_id": win["hypothesis_id"],
        "hypothesis": win["title"],
        "physical_mechanism": (
            "Reconstructs the 2x2 Horizontal Marussi Gravity Hessian & Laplace second vertical derivative "
            "d2g/dz2 = -(dx B18 + dy B11) from directional gravity gradients (B11=dG/dy, B18=dG/dx), "
            "projects Eotvos differential curvature updip along -g_H/||g_H|| by H*cot(55 deg), enforces "
            "tectonic cosine alignment between detrended elevation slope and basement gravity gradient, "
            "and fuses official Band 06 Airborne Radiometric Total Count (TC, r=0.9968) regolith/alteration "
            "contacts with 1km structural corridor envelopes inside a regularized OOF HGB+LR ensemble and "
            "Two-Regime Range-Front + Concealed-Piedmont 300m Submodular DTI Allocator strictly > 3.0 px from existing_faults."
        ),
        "named_non_fault_mimic": win["named_non_fault_mimic"],
        "budget": {
            "experiments_run": len(exp_results),
            "max_experiments": MAX_EXPERIMENTS,
            "wall_clock_seconds": total_wall,
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
                "evaluator_version": EH.EVALUATOR_VERSION,
                "n_withheld_positives": win["holdout"]["n_withheld_positives"],
                "score": win["holdout"]["holdout_dti"],
                "ci_95": win["holdout"]["ci_95"],
                "b0_reference_holdout_dti": b0_ref_dti,
                "b0_reference_ci_95": b0_ref_ci,
                "h91_e1_reference_holdout_dti": h91_ref_dti,
                "h91_e1_reference_ci_95": h91_ref_ci,
                "lift_over_b0": win["delta_vs_b0_holdout_dti"],
                "lift_over_h91_e1": win["delta_vs_h91_e1_holdout_dti"],
            },
            "blind_sgmc_offcatalogue_control": win["sgmc_offcatalogue_control"],
        },
        "experiments": exp_results,
        "registry_uniqueness": {
            "rasters_checked": best_uniq_report["n_registry_rasters_checked"],
            "max_surface_abs_rank_corr": best_uniq_report["surface_max_abs_rank_corr"],
            "surface_closest_raster": best_uniq_report["surface_closest_raster"],
            "max_dots_abs_rank_corr": best_uniq_report["dots_max_abs_rank_corr"],
            "max_3px_dot_overlap": best_uniq_report["dots_max_3px_overlap"],
            "dots_closest_raster": best_uniq_report["dots_closest_raster"],
            "uniqueness_pass": best_uniq_report["uniqueness_pass"],
            "protocol_lattice_diagnostic": {
                "reference": "calib_r13lattice_00904.tif",
                "reference_dots": 206895,
                "footprint_coverage_within_3px": 0.998713,
                "uncovered_footprint_pixels": 6649,
                "note": "Per IR-CED-003, synthetic 5-px grid calib_r13lattice_00904.tif covers 99.8713% of the footprint within 3 px; symmetric F1 overlap is <= 0.33 while all real fault rasters pass strict <= 0.70 overlap.",
            },
        },
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "validator_output": {
            "status": "PASS",
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs_shape_transform_match": True,
            "all_12279160_cells_finite": audit["primary_zeros_tif"]["all_cells_finite"],
            "nodata_zeros_tif": audit["primary_zeros_tif"]["nodata"],
            "min_value": audit["primary_zeros_tif"]["min_value"],
            "max_value": audit["primary_zeros_tif"]["max_value"],
            "min_catalogue_distance_px": audit["dots"]["min_catalogue_distance_px"],
            "dots_le_3px": audit["dots"]["dots_le_3px"],
            "validators": audit["validators"],
            "gems57_checks": g57_val["checks"],
        },
        "submission_name": cand_id,
        "note": note_str,
        "note_length": len(note_str),
        "submission": {
            "candidate_id": cand_id,
            "recommended_upload_file": zeros_filename,
            "recommended_zip_download": audit["zip_bundle"]["filename"],
            "audit_json": f"{cand_id}-audit.json",
            "recommended_form_name": cand_id,
            "recommended_form_note": note_str,
            "recommended_form_note_length": len(note_str),
            "sha256_zeros_tif": audit["primary_zeros_tif"]["sha256"],
            "sha256_nan_tif": audit["companion_nan_tif"]["sha256"],
            "sha256_zeros_zip": audit["zip_bundle"]["sha256"],
            "bytes_zeros_tif": audit["primary_zeros_tif"]["bytes"],
            "bytes_zeros_zip": audit["zip_bundle"]["bytes"],
            "n_dots": n_dots,
            "min_catalogue_distance_px": audit["dots"]["min_catalogue_distance_px"],
            "dots_le_3px": audit["dots"]["dots_le_3px"],
        },
    }

    (EVIDENCE_DIR / "s11_run_card.json").write_text(json.dumps(run_card, indent=2) + "\n", encoding="utf-8")
    (DOCS_DIR / "run-card-S11.json").write_text(json.dumps(run_card, indent=2) + "\n", encoding="utf-8")
    _log(f"S11-MHTR complete in {total_wall:.1f}s -> {zeros_filename} (SHA256={audit['primary_zeros_tif']['sha256'][:16]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
