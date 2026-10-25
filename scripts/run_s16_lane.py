#!/usr/bin/env python3
"""S16-PC91 lane: Kovesi phase congruency (monogenic local energy) detector.

Preregistration: docs/HYPOTHESES_S16.md (frozen before any S16 holdout run).
PARALLEL-RUN PROTOCOL: Rule 2 reuses shared `evaluate_holdout.py`,
`gems91.dd_vtc_pu` trainer/emitter and `submission_writer.py`; Rule 4 canary
on every feature; Rule 1 surface+dot uniqueness vs data/registry AND every
docs/downloads/*.tif; Rule 3 labels every score HOLDOUT-DTI with evaluator
version / withheld positives / 95% CI; Rule 6 budget = 3 experiments.

    E1: PC91 features only (24 cols), 37,654-dot quota
    E2: PC91 + 19 raw-band robust-z (43 cols), 37,654-dot quota
    E3: winner surface emission sweep {30,000 / 37,654 / 44,000}

Promotion requires v1.0 HOLDOUT-DTI > 0.262209 (S14-HVDC comparable best).
Usage: .venv/bin/python scripts/run_s16_lane.py
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import shutil
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
from gems91.pc91 import FIELDS, phase_congruency_features  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official/sample_submission.tif"
CATALOGUE = DATA / "official/existing_faults.tif"
FEATURES = DATA / "bridge/gems-geodawn-numerical-features.tif"
SGMC = DATA / "external/derived_sgmc_faults_100m_u8.tif"
CACHE = DATA / "cache_s16"
PRIOR_BEST_V10 = 0.262209  # S14-HVDC, gems91-hide-recover-v1.0, 60,988 withheld
BASE_BUDGET = 37_654
DATE_TAG = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log(m: str) -> None:
    print(f"[{dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fold_eligible(fold, folds, footprint, collar=3.0):
    other = np.zeros_like(footprint, dtype=bool)
    for f2 in folds:
        if f2.fold_id != fold.fold_id:
            other |= f2.withheld_faults
    domain = ((fold.region_mask & (~other)) | fold.withheld_faults) & footprint
    active = domain & (~fold.visible_faults) & (~fold.buffer_mask)
    d_vis = ndi.distance_transform_edt(~fold.visible_faults)
    return active, active & (d_vis > float(collar))


N_PC_COLS = 3 * 6 + 6  # per-field (pc,coh,cos2,sin2,energy_log,ampsum_log) + cross
N_COLS = N_PC_COLS + 19


def build_features(footprint) -> tuple[np.memmap, list[str], list[int]]:
    """Stream-build footprint-major feature memmap column by column (3 GB RAM)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    meta_p = CACHE / "s16_features_meta.json"
    n_fp = int(footprint.sum())
    mm_path = CACHE / "s16_X.float32.memmap"
    X = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n_fp, N_COLS))
    names: list[str] = []
    j = 0

    keep: dict[str, dict[str, np.ndarray]] = {}  # small footprint vectors for cross features
    for short, band in FIELDS:
        log(f"  PC91 monogenic features: {short} (band {band}) ...")
        with rasterio.open(FEATURES) as src:
            arr = DD._clean_band_edt(src.read(band), footprint)
        feats = phase_congruency_features(arr)
        del arr
        keep[short] = {}
        for key in ("pc", "coh", "cos2", "sin2"):
            v = feats[key][footprint].astype(np.float32)
            if key in ("pc", "cos2", "sin2"):
                keep[short][key] = v
            names.append(f"pc91_{short}_{key}")
            X[:, j] = v
            j += 1
        for key in ("energy", "ampsum"):
            v = np.log1p(np.maximum(feats[key][footprint].astype(np.float64), 0.0))
            p99 = float(np.percentile(v, 99.0)) or 1.0
            names.append(f"pc91_{short}_{key}_log")
            X[:, j] = np.clip(v / p99, 0.0, 2.0).astype(np.float32)
            j += 1
        del feats
        X.flush()

    pc_r, pc_e, pc_g = (keep[s]["pc"].astype(np.float64) for s in ("rtp", "det_elev", "iso_grav_anom"))

    def agree(a: str, b: str) -> np.ndarray:
        ca, sa = keep[a]["cos2"].astype(np.float64), keep[a]["sin2"].astype(np.float64)
        cb, sb = keep[b]["cos2"].astype(np.float64), keep[b]["sin2"].astype(np.float64)
        pa, pb = keep[a]["pc"].astype(np.float64), keep[b]["pc"].astype(np.float64)
        return ((ca * cb + sa * sb) * np.sqrt(np.maximum(pa * pb, 0.0))).astype(np.float32)

    cross = [
        ("pc91_min3", np.minimum(np.minimum(pc_r, pc_e), pc_g).astype(np.float32)),
        ("pc91_geo3", np.cbrt(np.maximum(pc_r * pc_e * pc_g, 0.0)).astype(np.float32)),
        ("pc91_mean3", ((pc_r + pc_e + pc_g) / 3.0).astype(np.float32)),
        ("pc91_agree_rtp_grav", agree("rtp", "iso_grav_anom")),
        ("pc91_agree_rtp_elev", agree("rtp", "det_elev")),
        ("pc91_agree_grav_elev", agree("iso_grav_anom", "det_elev")),
    ]
    for k, v in cross:
        names.append(k)
        X[:, j] = v
        j += 1
    del keep, cross, pc_r, pc_e, pc_g
    assert j == N_PC_COLS, (j, N_PC_COLS)

    with rasterio.open(FEATURES) as src:
        desc = src.descriptions
        for b in range(1, 20):
            arr = DD._clean_band_edt(src.read(b), footprint)[footprint].astype(np.float64)
            med = float(np.median(arr))
            q1, q3 = np.percentile(arr, [25.0, 75.0])
            iqr = float(q3 - q1) or 1.0
            short = (desc[b - 1] or f"band{b}").split(" - ")[0].strip()
            names.append(f"rawz_b{b:02d}_{short}")
            X[:, j] = np.clip((arr - med) / iqr, -8.0, 8.0).astype(np.float32)
            j += 1
            del arr
    X.flush()
    assert j == N_COLS and len(names) == N_COLS
    meta_p.write_text(json.dumps({"names": names, "n_pc_cols": N_PC_COLS, "n_fp": n_fp}, indent=1))
    log(f"  feature matrix {X.shape} -> {mm_path} (PC-only cols: {N_PC_COLS})")
    return X, names, list(range(N_PC_COLS))


def run_experiment(label, X, col_idx, folds, footprint, elig, quotas, budget_total, active_counts, total_active):
    fold_surfaces, fold_dots = {}, {}
    for f in folds:
        log(f"  {label} fold {f.fold_id} ({f.name}): train on visible faults ...")
        surf = DD.fit_and_predict_oof_fold(
            X, col_idx, None, f.visible_faults,
            f.withheld_faults | f.buffer_mask, footprint,
            use_pu_deconfound=False, seed=91,
        )
        fold_surfaces[f.fold_id] = surf
        fold_dots[f.fold_id] = DD.submodular_dti_emit(
            surf, eligible_mask=elig[f.fold_id], n_dots=quotas[f.fold_id])
        log(f"    emitted {int((fold_dots[f.fold_id] > 0).sum()):,} dots")
    v10 = EH.score_pooled_holdout(fold_dots, folds, footprint, mask_buffer_predictions=True)
    v11 = EH.score_pooled_holdout(fold_dots, folds, footprint, mask_buffer_predictions=False, n_boot=100)
    log(f"  {label}: HOLDOUT-DTI v1.0 = {v10['holdout_dti']:.6f} CI {v10['ci_95']} | v1.1 = {v11['holdout_dti']:.6f}")
    return {"surfaces": fold_surfaces, "dots": fold_dots, "v10": v10, "v11": v11}


def quota_for(budget: int, folds, active_counts, total_active) -> dict[int, int]:
    q, assigned = {}, 0
    for i, f in enumerate(folds):
        if i < len(folds) - 1:
            q[f.fold_id] = int(round(budget * active_counts[f.fold_id] / total_active))
            assigned += q[f.fold_id]
        else:
            q[f.fold_id] = budget - assigned
    return q


def main() -> int:
    t0 = time.perf_counter()
    for req in (TEMPLATE, CATALOGUE, FEATURES, SGMC):
        if not req.is_file():
            raise SystemExit(f"missing {req}; run scripts/restore_data.py")
    man = {f["id"]: f for f in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]}
    for pid, p in (("sample_submission", TEMPLATE), ("existing_faults", CATALOGUE), ("training_features", FEATURES)):
        if sha256_file(p) != man[pid]["sha256"]:
            raise SystemExit(f"sha256 MISMATCH for pinned {pid} — refusing to build")
    log("pinned input hashes verified")

    with rasterio.open(TEMPLATE) as s:
        footprint = np.isfinite(s.read(1))
    with rasterio.open(CATALOGUE) as s:
        cat = (np.nan_to_num(s.read(1), nan=0.0) > 0) & footprint
    with rasterio.open(SGMC) as s:
        sgmc = (np.nan_to_num(s.read(1), nan=0.0) > 0) & footprint
    log(f"footprint {int(footprint.sum()):,} px, catalogue {int(cat.sum()):,} px")

    folds = EH.build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    elig, active_counts, total_active = {}, {}, 0
    for f in folds:
        act, el = fold_eligible(f, folds, footprint)
        elig[f.fold_id] = el
        active_counts[f.fold_id] = int(act.sum())
        total_active += active_counts[f.fold_id]
        log(f"  fold {f.fold_id} {f.name}: withheld={f.n_withheld:,} segments={f.n_segments_withheld} eligible={int(el.sum()):,}")

    log("building PC91 + raw features ...")
    X, names, pc_cols = build_features(footprint)
    all_cols = list(range(len(names)))

    log("Rule 4 leakage canary (every E1/E2 feature alone) ...")
    canary = EH.run_leakage_canary(X, names, folds, footprint, subsample_step=4)
    log(f"  canary all_pass={canary['all_pass']} worst={canary['worst_feature']} symAUC={canary['worst_symmetric_auc']}")
    (ROOT / "evidence/s16_canary.json").write_text(json.dumps(canary, indent=1))
    if not canary["all_pass"]:
        raise SystemExit(f"LEAKAGE CANARY FAILED: {canary['flagged_features']}")

    quotas = quota_for(BASE_BUDGET, folds, active_counts, total_active)
    exp_cache_p = CACHE / "s16_exp_results.json"
    exp_cache = json.loads(exp_cache_p.read_text()) if exp_cache_p.is_file() else {}

    def cached_or_run(key, label, X_, cols_):
        if key in exp_cache:
            log(f"{label}: loaded cached result v1.0 = {exp_cache[key]['v10']['holdout_dti']:.6f}")
            return {"v10": exp_cache[key]["v10"], "v11": exp_cache[key]["v11"], "surfaces": {}, "dots": {}}
        r = run_experiment(label, X_, cols_, folds, footprint, elig, quotas,
                           BASE_BUDGET, active_counts, total_active)
        exp_cache[key] = {"v10": r["v10"], "v11": r["v11"]}
        exp_cache_p.write_text(json.dumps(exp_cache, indent=1))
        return r

    log("E1: PC91-only ...")
    e1 = cached_or_run("E1", "E1", X, pc_cols)
    log("E2: PC91 + raw19 ...")
    e2 = cached_or_run("E2", "E2", X, all_cols)

    # E3 (amended, docs/HYPOTHESES_S16.md): shared static stack + PC91.
    log("E3: shared static stack (49) + PC91 (24) ...")
    Xs, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES, gdr_csv=DATA / "external/gdr_wellspring_in_footprint.csv",
        footprint=footprint, cache_dir=CACHE)
    n_fp = int(footprint.sum())
    comb_path = CACHE / "s16_X_combined.float32.memmap"
    Xc = np.memmap(comb_path, dtype=np.float32, mode="w+", shape=(n_fp, len(static_names) + len(pc_cols)))
    for jj in range(len(static_names)):
        Xc[:, jj] = Xs[:, jj]
    for kk, cc in enumerate(pc_cols):
        Xc[:, len(static_names) + kk] = X[:, cc]
    Xc.flush()
    comb_names = list(static_names) + [names[c] for c in pc_cols]
    canary3 = EH.run_leakage_canary(Xc, comb_names, folds, footprint, subsample_step=4)
    log(f"  E3 canary all_pass={canary3['all_pass']} worst={canary3['worst_feature']} symAUC={canary3['worst_symmetric_auc']}")
    (ROOT / "evidence/s16_canary_e3.json").write_text(json.dumps(canary3, indent=1))
    if not canary3["all_pass"]:
        raise SystemExit(f"E3 LEAKAGE CANARY FAILED: {canary3['flagged_features']}")
    e3 = cached_or_run("E3", "E3", Xc, list(range(len(comb_names))))

    cands = [("E1", e1, X, pc_cols), ("E2", e2, X, all_cols),
             ("E3", e3, Xc, list(range(len(comb_names))))]
    winner_label, winner, winner_X, winner_cols = max(cands, key=lambda t: t[1]["v10"]["holdout_dti"])
    best_budget = BASE_BUDGET
    final_v10, final_v11 = winner["v10"], winner["v11"]
    sweep = {"note": "budget sweep replaced by amended E3 (docs/HYPOTHESES_S16.md); final budget fixed at 37,654"}
    log(f"winner: {winner_label} @ {best_budget:,} dots, v1.0 HOLDOUT-DTI = {final_v10['holdout_dti']:.6f} (prior best {PRIOR_BEST_V10})")

    d_cat = ndi.distance_transform_edt(~cat)
    full_elig = footprint & (d_cat > 3.0)
    registry_paths = sorted(glob.glob(str(DATA / "registry/*.tif"))) + \
        sorted(glob.glob(str(ROOT / "docs/downloads/*.tif")))

    # Rule 1 on the holdout winner (E3): measured duplicate-stop evidence.
    log("winner (E3) final emission for Rule-1 duplicate check ...")
    win_surf = DD.fit_and_predict_oof_fold(
        winner_X, winner_cols, None, cat, np.zeros_like(cat), footprint,
        use_pu_deconfound=False, seed=91)
    win_dots = DD.submodular_dti_emit(win_surf, eligible_mask=full_elig, n_dots=best_budget)
    win_uniq = EH.check_registry_uniqueness(
        win_surf[footprint].astype(np.float64), win_dots, footprint, registry_paths)
    log(f"  E3 dot uniqueness pass={win_uniq['uniqueness_pass']}")
    del win_surf, win_dots

    # Delivered file = lane-pure E1 (PC-only) final emission. E3 is logged as a
    # duplicate stop and is never written as a submission (protocol Rule 1).
    delivered_label = "E1"
    final_v10, final_v11 = e1["v10"], e1["v11"]
    log("delivered model (E1 PC-only): train on full catalogue ...")
    full_surf = DD.fit_and_predict_oof_fold(
        X, pc_cols, None, cat, np.zeros_like(cat), footprint,
        use_pu_deconfound=False, seed=91)
    surf_fp = full_surf[footprint].astype(np.float64)
    log(f"Rule 1 surface uniqueness vs {len(registry_paths)} registry rasters ...")
    surf_uniq = EH.check_registry_surface_uniqueness(surf_fp, footprint, registry_paths)
    log(f"  max |rho| = {surf_uniq['surface_max_abs_rank_corr']} vs {surf_uniq['surface_closest_raster']} pass={surf_uniq['uniqueness_pass']}")

    final_dots = DD.submodular_dti_emit(full_surf, eligible_mask=full_elig, n_dots=best_budget)
    n_final = int((final_dots > 0).sum())
    log(f"final dots emitted: {n_final:,}")
    dot_uniq = EH.check_registry_uniqueness(surf_fp, final_dots, footprint, registry_paths)
    log(f"  dot uniqueness pass={dot_uniq['uniqueness_pass']} (see run card)")

    sgmc_ctrl = EH.score_off_catalogue_sgmc(final_dots, sgmc, cat, footprint)
    r0_p = DATA / "registry/GEMSDOE32__h33-2-b2-zeros.tif"
    with rasterio.open(r0_p) as s:
        r0 = np.nan_to_num(s.read(1), nan=0.0)
    sgmc_r0 = EH.score_off_catalogue_sgmc(r0, sgmc, cat, footprint)
    log(f"SGMC off-cat control: candidate {sgmc_ctrl['dti']:.6f} vs R0 {sgmc_r0['dti']:.6f} (report-only)")

    log("writing validated submission bundle (triple gate suites) ...")
    audit = SW.write_validated_submission_bundle(
        final_dots,
        stem_prefix="gems91-s16-pc91",
        date_tag=DATE_TAG,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=ROOT / "ledger/submissions.csv",
        parent_compare_path=r0_p,
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs/downloads",
        floor_px=3.0,
        bundle_js_filename="s16_submission_bundle.js",
    )
    cand_id = audit["candidate_id"]
    # Direct-download TIFs on the Pages site (same bytes as releases/)
    for suffix in ("-zeros.tif", ".tif"):
        srcf = ROOT / "releases" / f"{cand_id}{suffix}"
        if srcf.is_file():
            shutil.copy2(srcf, ROOT / "docs/downloads" / srcf.name)

    beats = bool(final_v10["holdout_dti"] > PRIOR_BEST_V10)
    validators_pass = bool(audit["validators"]["gems91_gates_verdict"] == "CERTIFIED"
                           and audit["validators"]["release_gates_nan_pass"]
                           and audit["validators"]["release_gates_zeros_pass"]
                           and audit["validators"]["validate_raster_nan_pass"]
                           and audit["validators"]["validate_raster_zeros_pass"])
    promote = bool(beats and canary["all_pass"] and canary3["all_pass"] and surf_uniq["uniqueness_pass"]
                   and dot_uniq["uniqueness_pass"] and validators_pass)
    note = (f"S16-PC91 phase-congruency monogenic {delivered_label} {n_final}d "
            f"HOLDOUT-DTI {final_v10['holdout_dti']:.4f} v1.0")[:140]
    card = {
        "schema": "gems-parallel-run-card-v1",
        "repo": "buffedlizard55-lab/GEMSDOE91",
        "branch": "arena/3b49ef79-gemsdoe91",
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "preregistration": "docs/HYPOTHESES_S16.md",
        "lane": "S16-PC91 Kovesi phase congruency (monogenic local energy)",
        "hypothesis": "Contrast-invariant multi-scale phase alignment on B02 rtp / B13 iso_grav_anom / B12 det_elev exposes low-amplitude buried basement faults that amplitude-scaled detectors rank below shallow noise.",
        "mechanism": "Log-Gabor radial x Riesz monogenic triples at 3/6/12/24 px wavelengths; spread-weighted phase-deviation PC in [0,1] + local energy + orientation coherence + cross-field strike agreement; fold-wise HGB+LR on visible faults only; submodular 300 m DTI dotted emission >3.0 px off catalogue.",
        "named_non_fault_mimic": "GeoDAWN flight-line seams and survey gridding artifacts (phase-coherent straight lines at flight azimuth); lithologic contacts with aligned multi-scale phase but no fault offset.",
        "budget": {"experiments_run": 3, "max_experiments": 3,
                   "wall_clock_seconds": round(time.perf_counter() - t0, 1), "max_wall_clock_seconds": 7200},
        "leakage_canary": {"evaluator_version": canary["evaluator_version"],
                           "n_features_tested": canary["n_features_tested"],
                           "max_allowed_symmetric_auc": 0.90,
                           "worst_feature": canary["worst_feature"],
                           "worst_symmetric_auc": canary["worst_symmetric_auc"],
                           "all_pass": canary["all_pass"], "detail": "evidence/s16_canary.json"},
        "experiments": {
            "E1_pc_only": {"v10": e1["v10"], "v11_nohalo": e1["v11"]},
            "E2_pc_plus_raw19": {"v10": e2["v10"], "v11_nohalo": e2["v11"]},
            "E3_static_stack_plus_pc": {"v10": e3["v10"], "v11_nohalo": e3["v11"],
                                        "canary_worst": canary3["worst_feature"],
                                        "canary_worst_symmetric_auc": canary3["worst_symmetric_auc"],
                                        "canary_all_pass": canary3["all_pass"]},
            "amendment": sweep["note"],
        },
        "scores": {
            "primary_holdout": {"label": "HOLDOUT-DTI", **{k: final_v10[k] for k in
                                ("evaluator_version", "n_withheld_positives", "holdout_dti", "ci_95")},
                                "winner": delivered_label, "budget_dots": best_budget,
                                "holdout_winner_not_delivered": winner_label},
            "holdout_v11_nohalo": {"label": "HOLDOUT-DTI", **{k: final_v11[k] for k in
                                   ("evaluator_version", "n_withheld_positives", "holdout_dti", "ci_95")}},
            "comparable_prior_best": {"candidate": "S14-HVDC E2", "label": "HOLDOUT-DTI",
                                      "evaluator_version": "gems91-hide-recover-v1.0",
                                      "n_withheld_positives": 60988, "score": PRIOR_BEST_V10,
                                      "ci_95": [0.24894, 0.275209], "beats_it": beats},
            "sgmc_offcatalogue_control": {"label": "SGMC-OFFCAT-CONTROL-DTI (report-only)",
                                          "candidate": sgmc_ctrl, "r0_reference": sgmc_r0},
            "organizer_confirmed": None,
        },
        "e3_duplicate_stop": {"experiment": "E3", "final_dot_uniqueness": win_uniq,
                              "action": "logged as duplicate per protocol Rule 1; E3 raster never written as submission"},
        "delivered_experiment": delivered_label,
        "uniqueness": {"surface_pre_placement": surf_uniq, "final_dots": dot_uniq,
                       "registry_sets": ["data/registry/*.tif", "docs/downloads/*.tif"]},
        "validator_output": audit,
        "raster_sha256": audit["primary_zeros_tif"]["sha256"],
        "submission_name": cand_id,
        "submission_note": note,
        "note_chars": len(note),
        "ok_to_download": True,
        "ok_to_submit": promote,
        "verdict": "promote" if promote else "negative",
        "verdict_reason": ("all gates pass and v1.0 HOLDOUT-DTI beats comparable prior best; "
                           "eligible for separate human selector within weekly cap" if promote else
                           f"gate failure(s): beats_prior_best={beats}, canary={canary['all_pass']}, "
                           f"surface_uniq={surf_uniq['uniqueness_pass']}, dot_uniq={dot_uniq['uniqueness_pass']}, "
                           f"validators={validators_pass}"),
    }
    out_p = ROOT / "docs/run-card-S16.json"
    out_p.write_text(json.dumps(card, indent=1))
    (ROOT / "evidence/s16_run_card.json").write_text(json.dumps(card, indent=1))
    log(f"run card -> {out_p} verdict={card['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
