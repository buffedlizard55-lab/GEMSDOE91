#!/usr/bin/env python3
"""Session 14 lane runner (`S14-LSRG`): LiDAR-Scarp + Radiometric-Ratio +
Spring-Geometry surface with winner-economics Dinkelbach emission.

Pre-registration: docs/HYPOTHESES_S14.md (hash-checked at start; the runner
refuses to run without it). Experiments (budget 3, Protocol Rule 6):
  E1  HGB ensemble on shared stack (static 49 incl. e2 GDR springs, S11 16,
      PTHA 20) + NEW S14 block (lidar scarp 13 + radiometric ratios 10) +
      fold-safe catalogue geometry (3). Scored on HOLDOUT-DTI v1.0 (frozen
      comparator; S13-PTHA best = 0.244601) AND v1.1-nohalo (IR-91-S14-01).
  E2  E1 posterior x multi-family corroboration gate (H14-5).
  E3  Emission-budget sweep {30000, 37654, 44000} on the E1/E2 winner
      (by v1.1), then full-map emission, registry uniqueness (Rule 1),
      validated submission bundle (shared writer), JSON run card (Rule 5).

Every score is labelled HOLDOUT-DTI (evaluator version, n withheld, 95% CI)
or SGMC-OFFCAT-CONTROL-DTI. ORGANIZER-CONFIRMED is null: no slot is spent.
"""
from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import evaluate_holdout as EH  # noqa: E402
import submission_writer as SW  # noqa: E402
from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import mhtr_coda as MC  # noqa: E402
from gems91 import ptha as PTHA  # noqa: E402
from gems91 import s14 as S14  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "derived"
TEMPLATE = DATA / "official/sample_submission.tif"
CATALOGUE = DATA / "official/existing_faults.tif"
FEATURES = DATA / "bridge/gems-geodawn-numerical-features.tif"
SGMC = DATA / "external/derived_sgmc_faults_100m_u8.tif"
GDR = DATA / "external/gdr_wellspring_in_footprint.csv"
LIDAR = DATA / "external/lidar_scarp_features_u8.tif"
RAD = DATA / "external/geodawn_rad_u8.tif"
PREREG = ROOT / "docs/HYPOTHESES_S14.md"
EMIT_BUDGET_E12 = 40_000
E3_BUDGETS = [30_000, 37_654, 44_000]
STEM = "gems91-s14-lsrg-e3"
DATE_TAG = "20261024T235900Z"


def log(m: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fold_eligible(f, folds, footprint, collar=3.0):
    other = np.zeros_like(footprint)
    for f2 in folds:
        if f2.fold_id != f.fold_id:
            other |= f2.withheld_faults
    domain = ((f.region_mask & (~other)) | f.withheld_faults) & footprint
    active = domain & (~f.visible_faults) & (~f.buffer_mask)
    d_vis = ndi.distance_transform_edt(~f.visible_faults)
    return active & (d_vis > collar)


def emit_and_score(probs, cals, folds, footprint, crest, piedmont, elig,
                   n_full_elig, budget, tag):
    """Quota-mode submodular emission (S13 E1/E2 mode): per-fold dot quota
    proportional to eligible area, exact 300 m-kernel lazy greedy, threshold 0.

    The tau-transfer variant (`dinkelbach_fold_independent_emit`) was measured
    broken in this lane (IR-91-S14-04): its train-territory gain threshold is
    set by in-sample-inflated gains near visible faults, starving honest OOF
    folds (574-3,000 dots vs 40k target; S13's NW fold hit its floor the same
    way). Intensity calibration (`q_floor`) still uses train territory only.
    """
    total_elig = sum(int(elig[f.fold_id].sum()) for f in folds)
    fold_dots, metas = {}, {}
    assigned = 0
    for i, f in enumerate(folds):
        quota = (int(round(budget * int(elig[f.fold_id].sum()) / total_elig))
                 if i < len(folds) - 1 else budget - assigned)
        assigned += quota
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        d_vis = ndi.distance_transform_edt(~f.visible_faults)
        train_elig = footprint & (~excl) & (~f.visible_faults) & (d_vis > 3.0)
        w_surf, rank_s, q_floor = PTHA.build_dinkelbach_expected_intensity(
            probs[f.fold_id], crest, piedmont, footprint,
            calibration_mask=train_elig,
            pi_true=cals[f.fold_id]["pi_true"], pi_sample=cals[f.fold_id]["pi_sample"])
        dots, last_gain = PTHA._lazy_greedy_submodular_select(
            w_surf, elig[f.fold_id], rank_surf=rank_s, max_dots=quota,
            min_gain_threshold=0.0, min_spacing_px=2.50)
        fold_dots[f.fold_id] = dots
        metas[f.name] = {"quota": quota, "n_test_emitted_dots": int((dots > 0).sum()),
                         "q_floor_train": round(float(q_floor), 7),
                         "last_gain": round(float(last_gain), 7)}
        log(f"  [{tag} {f.name}] emitted {metas[f.name]['n_test_emitted_dots']:,}/{quota:,} dots")
    v10 = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=141)
    v11 = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=141,
                                  mask_buffer_predictions=False)
    log(f"  [{tag}] HOLDOUT-DTI v1.0={v10['holdout_dti']:.6f} CI{v10['ci_95']} | "
        f"v1.1-nohalo={v11['holdout_dti']:.6f} CI{v11['ci_95']} | "
        f"pooled dots={sum(int((d>0).sum()) for d in fold_dots.values()):,}")
    return fold_dots, v10, v11, metas


def main() -> int:
    t0 = time.perf_counter()
    if not PREREG.is_file():
        raise RuntimeError("pre-registration docs/HYPOTHESES_S14.md missing")
    prereg_sha = sha256(PREREG)
    log(f"S14-LSRG start | prereg sha256={prereg_sha[:16]}")
    CACHE.mkdir(parents=True, exist_ok=True)

    with rasterio.open(TEMPLATE) as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(CATALOGUE) as ds:
        cat = (ds.read(1) > 0) & footprint
    with rasterio.open(SGMC) as ds:
        sgmc = ds.read(1)
    n_fp = int(footprint.sum())
    log(f"footprint={n_fp:,} catalogue={int(cat.sum()):,}")

    folds = EH.build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    elig = {f.fold_id: fold_eligible(f, folds, footprint) for f in folds}
    d_cat = ndi.distance_transform_edt(~cat)
    full_elig = footprint & (~cat) & (d_cat > 3.0)
    n_full_elig = int(full_elig.sum())

    log("building/loading memmaps (static49, s11-16, ptha20, s14-23)...")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES, gdr_csv=GDR, footprint=footprint, cache_dir=CACHE)
    log(f"  static ready {time.perf_counter()-t0:.0f}s")
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE)
    log(f"  s11 ready {time.perf_counter()-t0:.0f}s")
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE)
    log(f"  ptha ready {time.perf_counter()-t0:.0f}s")
    X_s14, s14_names, s14_meta = S14.build_or_load_s14_feature_memmap(
        lidar_tif=LIDAR, rad_tif=RAD, footprint=footprint, cache_dir=CACHE)
    log(f"  s14 ready {time.perf_counter()-t0:.0f}s meta={s14_meta}")

    # Fold-safe catalogue geometry per fold (visible faults only)
    foldcat = {}
    for f in folds:
        fc_dat = CACHE / f"s14_foldcat_f{f.fold_id}.dat"
        if fc_dat.is_file() and fc_dat.stat().st_size == n_fp * 3 * 4:
            foldcat[f.fold_id] = np.memmap(fc_dat, dtype=np.float32, mode="r", shape=(n_fp, 3))
        else:
            arr = DD.compute_fold_safe_catalogue_features(f.visible_faults, footprint)
            arr.astype(np.float32).tofile(fc_dat)
            foldcat[f.fold_id] = np.memmap(fc_dat, dtype=np.float32, mode="r", shape=(n_fp, 3))
    fullcat = DD.compute_fold_safe_catalogue_features(cat, footprint)
    log("fold-safe catalogue geometry ready")

    # Rule 4 leakage canary on all NEW/restored features (S14 23 + static e2 10 + foldcat 3).
    # The other 75 features were canaried in S13 (docs/run-card-S13.json: max AUC 0.66470).
    canary_path = CACHE / "s14_canary_v1.json"
    if canary_path.is_file():
        canary = json.loads(canary_path.read_text())
        log(f"loaded cached canary pass={canary['all_pass']} worst={canary['worst_symmetric_auc']}")
    else:
        log("running Rule-4 leakage canary (new features)...")
        c1 = EH.run_leakage_canary(np.asarray(X_s14), s14_names, folds, footprint, subsample_step=4)
        e2_cols = list(range(34, 44))
        c2 = EH.run_leakage_canary(np.asarray(X_static)[:, e2_cols],
                                   [static_names[i] for i in e2_cols], folds, footprint, subsample_step=4)
        c3 = EH.run_leakage_canary(
            np.zeros((n_fp, 0), dtype=np.float32), [], folds, footprint,
            fold_specific_features={f.fold_id: (np.asarray(foldcat[f.fold_id]),
                                                DD.FOLD_CATALOGUE_FEATURE_NAMES) for f in folds},
            subsample_step=4)
        feats = {**c1["features"], **c2["features"], **c3["features"]}
        worst = max(feats.items(), key=lambda kv: kv[1]["max_fold_symmetric_auc"])
        canary = {"evaluator_version": EH.EVALUATOR_VERSION, "max_allowed_auc": 0.90,
                  "n_features_tested": len(feats), "worst_feature": worst[0],
                  "worst_symmetric_auc": worst[1]["max_fold_symmetric_auc"],
                  "flagged_features": [k for k, v in feats.items() if not v["pass"]],
                  "all_pass": all(v["pass"] for v in feats.values()), "features": feats,
                  "note": "Remaining 75 shared-stack features canaried in S13 (max sym AUC 0.66470, docs/run-card-S13.json)."}
        canary_path.write_text(json.dumps(canary, indent=2) + "\n")
        log(f"canary pass={canary['all_pass']} worst={canary['worst_feature']} "
            f"AUC={canary['worst_symmetric_auc']} n={len(feats)}")
    if not canary["all_pass"]:
        raise RuntimeError(f"LEAKAGE CANARY FAILED: {canary['flagged_features']}")

    mhtr_edge, piedmont = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, footprint)
    slope_fp = np.asarray(X_static[:, 18], dtype=np.float32)

    # IR-91-S14-03: fold-catalogue geometry must NEVER be a training feature
    # (it is defined by the visible-fault labels: tip-proximity ~= 1 exactly on
    # visible faults -> HGB memorization, withheld AUC 0.54, measured). It is
    # applied post-hoc as the bounded relay prior (H91 usage), per H14-4.
    def blocks_for(fold_id):
        return [(X_static, None), (X_s11, None), (X_ptha, None), (X_s14, None)]

    # ---------------- E1 ----------------
    probs, cals = {}, {}
    for f in folds:
        dat = CACHE / f"s14_oof_e1b_f{f.fold_id}.dat"
        meta_j = CACHE / f"s14_oof_e1b_f{f.fold_id}.json"
        if dat.is_file() and meta_j.is_file() and dat.stat().st_size == n_fp * 4:
            p = np.zeros(footprint.shape, dtype=np.float32)
            p[footprint] = np.fromfile(dat, dtype=np.float32)
            probs[f.fold_id] = p
            cals[f.fold_id] = json.loads(meta_j.read_text())
            log(f"[E1 {f.name}] loaded cached OOF")
            continue
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        tf = time.perf_counter()
        p, cal = S14.fit_and_predict_s14_fold(
            blocks=blocks_for(f.fold_id), visible_faults=f.visible_faults,
            exclude_mask=excl, footprint=footprint, hard_neg_fp=slope_fp,
            seed=914 + f.fold_id)
        p = DD.apply_structural_relay_prior(p, np.asarray(foldcat[f.fold_id]), footprint)
        probs[f.fold_id] = p
        cals[f.fold_id] = cal
        p[footprint].astype(np.float32).tofile(dat)
        meta_j.write_text(json.dumps(cal, indent=2) + "\n")
        log(f"[E1 {f.name}] trained in {time.perf_counter()-tf:.0f}s pi_true={cal['pi_true']:.5f}")
        gc.collect()

    _, e1_v10, e1_v11, e1_meta = emit_and_score(
        probs, cals, folds, footprint, crest, piedmont, elig, n_full_elig,
        EMIT_BUDGET_E12, "E1")

    # ---------------- E2 corroboration gate ----------------
    lid_surf = np.zeros(footprint.shape, dtype=np.float32)
    lid_surf[footprint] = np.asarray(X_s14[:, s14_names.index("s14_lid_step_x_coh")])
    rad_surf = np.zeros(footprint.shape, dtype=np.float32)
    rad_surf[footprint] = np.asarray(X_s14[:, s14_names.index("s14_rad_thk_step")])
    probs_e2 = {k: S14.corroboration_gate(p, [crest, lid_surf, rad_surf], footprint)
                for k, p in probs.items()}
    _, e2_v10, e2_v11, e2_meta = emit_and_score(
        probs_e2, cals, folds, footprint, crest, piedmont, elig, n_full_elig,
        EMIT_BUDGET_E12, "E2")

    winner = "E2" if e2_v11["holdout_dti"] >= e1_v11["holdout_dti"] else "E1"
    win_probs = probs_e2 if winner == "E2" else probs
    win_v10 = e2_v10 if winner == "E2" else e1_v10
    log(f"winner by v1.1-nohalo: {winner} (E1 {e1_v11['holdout_dti']:.4f} / E2 {e2_v11['holdout_dti']:.4f})")

    # ---------------- E3 budget sweep ----------------
    e3_rows = {}
    for b in E3_BUDGETS:
        _, bv10, bv11, bmeta = emit_and_score(
            win_probs, cals, folds, footprint, crest, piedmont, elig,
            n_full_elig, b, f"E3-b{b}")
        e3_rows[str(b)] = {"v10": bv10, "v11": bv11, "fold_meta": bmeta}
    best_budget = max(E3_BUDGETS, key=lambda b: e3_rows[str(b)]["v11"]["holdout_dti"])
    log(f"E3 best budget by v1.1: {best_budget}")

    # ---------------- Full-map model + emission ----------------
    full_dat = CACHE / "s14_full_prob_b.dat"
    full_meta_j = CACHE / "s14_full_prob_b.json"
    if full_dat.is_file() and full_meta_j.is_file() and full_dat.stat().st_size == n_fp * 4:
        full_prob = np.zeros(footprint.shape, dtype=np.float32)
        full_prob[footprint] = np.fromfile(full_dat, dtype=np.float32)
        full_cal = json.loads(full_meta_j.read_text())
        log("loaded cached full-map posterior")
    else:
        tf = time.perf_counter()
        full_prob, full_cal = S14.fit_and_predict_s14_fold(
            blocks=[(X_static, None), (X_s11, None), (X_ptha, None), (X_s14, None)],
            visible_faults=cat, exclude_mask=np.zeros_like(footprint),
            footprint=footprint, hard_neg_fp=slope_fp, seed=1400)
        full_prob = DD.apply_structural_relay_prior(full_prob, fullcat, footprint)
        full_prob[footprint].astype(np.float32).tofile(full_dat)
        full_meta_j.write_text(json.dumps(full_cal, indent=2) + "\n")
        log(f"full-map model trained in {time.perf_counter()-tf:.0f}s")
    if winner == "E2":
        full_prob = S14.corroboration_gate(full_prob, [crest, lid_surf, rad_surf], footprint)

    full_dots, last_gain = PTHA.dinkelbach_full_map_emit(
        full_prob, crest, piedmont, footprint=footprint, full_eligible_mask=full_elig,
        pi_true=full_cal["pi_true"], pi_sample=full_cal["pi_sample"],
        n_dots=best_budget, min_spacing_px=2.50)
    n_dots = int((full_dots > 0).sum())
    log(f"full-map dots emitted: {n_dots:,}")

    # ---------------- Rule 1 uniqueness ----------------
    reg_paths = sorted((DATA / "registry").glob("*.tif")) + \
        sorted(p for p in (ROOT / "docs/downloads").glob("*-zeros.tif")
               if not p.name.startswith("gems91-s14"))
    log(f"uniqueness vs {len(reg_paths)} registry/sibling rasters...")
    surf_check = EH.check_registry_surface_uniqueness(
        full_prob[footprint].astype(np.float64), footprint, reg_paths)
    dot_check = EH.check_registry_uniqueness(
        full_prob[footprint].astype(np.float64), full_dots, footprint, reg_paths)
    log(f"surface max|rho|={surf_check['surface_max_abs_rank_corr']:.3f} "
        f"({surf_check['surface_closest_raster']}) "
        f"dots max3px={dot_check['dots_max_3px_overlap']:.3f} "
        f"({dot_check['dots_closest_raster']}) pass={dot_check['uniqueness_pass']}")

    # Winner-geometry + SGMC control on the final raster
    ys, xs = np.nonzero(full_dots > 0)
    dc = d_cat[ys, xs]
    geom = {"n_dots": n_dots,
            "frac_dots_gt10px_of_catalogue": float(np.mean(dc > 10.0)),
            "frac_dots_3to10px_of_catalogue": float(np.mean((dc > 3.0) & (dc <= 10.0))),
            "min_dist_to_catalogue_px": float(dc.min())}
    from scipy.spatial import cKDTree
    pts = np.column_stack([ys, xs]).astype(np.float64)
    rng = np.random.default_rng(0)
    sub = pts[rng.choice(len(pts), min(2000, len(pts)), replace=False)]
    dnn, _ = cKDTree(pts).query(sub, k=2)
    geom["median_nn_spacing_px"] = float(np.median(dnn[:, 1]))
    sg = EH.score_off_catalogue_sgmc(full_dots, sgmc, cat.astype(np.float32), footprint)
    log(f"geometry={geom} SGMC={sg['dti']:.4f}")

    # ---------------- Bundle (shared fail-closed writer) ----------------
    bundle = SW.write_validated_submission_bundle(
        full_dots, stem_prefix=STEM, date_tag=DATE_TAG,
        template_path=TEMPLATE, catalogue_path=CATALOGUE,
        parent_compare_path=DATA / "registry/GEMSDOE32__h33-2-b2-zeros.tif",
        bundle_js_filename="s14_submission_bundle.js")
    log(f"bundle written: {json.dumps(bundle.get('files', bundle), default=str)[:600]}")

    win_v11 = e3_rows[str(best_budget)]["v11"]
    win_v10_b = e3_rows[str(best_budget)]["v10"]
    surface_sane = bool(win_v10_b["holdout_dti"] >= 0.20)
    geom_ok = bool(geom["median_nn_spacing_px"] >= 2.8 and geom["frac_dots_gt10px_of_catalogue"] >= 0.60)
    verdict = "promote" if (dot_check["uniqueness_pass"] and surf_check["uniqueness_pass"]
                            and surface_sane) else "negative"
    card = {
        "schema_version": "gems91.s14_lsrg.v1",
        "generated_utc": DATE_TAG,
        "branch": "arena/eeaf78c1-gemsdoe91",
        "preregistration": {"path": "docs/HYPOTHESES_S14.md", "sha256": prereg_sha},
        "lane": {"id": "S14-LSRG", "assigned": False,
                 "note": "Self-declared; no selector paragraph supplied (IR-91-S12-01)."},
        "hypothesis": "H14-1 LiDAR scarp + H14-2 radiometric ratios + H14-3 springs + H14-4 fold-safe tip/stepover + H14-5 corroboration & winner-economics Dinkelbach emission",
        "mechanism": "1m-DEM scarp decomposition and GeoDAWN K/Th/U ratio steps detect Holocene ruptures and hydrothermal alteration along blind faults; HGB ensemble over shared 85-feature stack + 23 new S14 + 3 fold-safe catalogue-geometry features; unit dots emitted by exact expected-DTI Dinkelbach greedy at winner spacing/budget.",
        "named_non_fault_mimic_process": "Lake Lahontan shoreline benches, road cuts, dune slipfaces, felsic pluton K highs, basin-margin artesian springs, flight-line seams",
        "experiments": {
            "E1": {"holdout_v10": e1_v10, "holdout_v11_nohalo": e1_v11, "fold_meta": e1_meta},
            "E2": {"holdout_v10": e2_v10, "holdout_v11_nohalo": e2_v11, "fold_meta": e2_meta},
            "E3_budget_sweep": e3_rows, "winner_surface": winner, "best_budget": best_budget},
        "holdout_dti_primary": {
            "label": "HOLDOUT-DTI", "evaluator_version": win_v11["evaluator_version"],
            "value": win_v11["holdout_dti"], "ci95": win_v11["ci_95"],
            "n_withheld_positives": win_v11["n_withheld_positives"]},
        "holdout_dti_v10_comparator": {
            "label": "HOLDOUT-DTI", "evaluator_version": win_v10_b["evaluator_version"],
            "value": win_v10_b["holdout_dti"], "ci95": win_v10_b["ci_95"],
            "n_withheld_positives": win_v10_b["n_withheld_positives"],
            "prior_best_s13_ptha": 0.244601, "surface_sanity_gate_0p20_pass": surface_sane},
        "blind_sgmc_offcatalogue_control": sg,
        "organizer_confirmed": None,
        "canary": {k: canary[k] for k in ("n_features_tested", "worst_feature",
                                          "worst_symmetric_auc", "all_pass", "flagged_features")},
        "registry_comparison": {"surface": surf_check, "dots": dot_check,
                                "n_registry_rasters": len(reg_paths)},
        "winner_geometry": geom, "winner_geometry_gate_pass": geom_ok,
        "submission": bundle,
        "verdict": verdict,
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
    }
    (ROOT / "docs/run-card-S14.json").write_text(json.dumps(card, indent=2, default=str) + "\n")
    (ROOT / "evidence/s14_run_card.json").write_text(json.dumps(card, indent=2, default=str) + "\n")
    log(f"RUN CARD verdict={verdict} v11={win_v11['holdout_dti']:.4f} v10={win_v10_b['holdout_dti']:.4f} "
        f"budget={best_budget} dots={n_dots:,} elapsed={time.perf_counter()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
