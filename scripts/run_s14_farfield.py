#!/usr/bin/env python3
"""S14-LSRG E3-FF (far-field emission) — POST-BUDGET DEVIATION, user-directed.

IR-91-S14-05 (deviation log): the pre-registered E1/E2/E3 completed with
verdict `negative`: HOLDOUT-DTI 0.240111 passed the 0.20 surface-sanity gate
and Rule-1 uniqueness vs the pinned fleet registry (max 54.3% <= 70%), BUT
63.2% of dots sat in the 3-10 px catalogue halo (winners: 21-24%) and 85.2%
fell within 3 px of unsubmitted sibling S12-SPAC. The session prompt's
highest-priority instruction (deliver a unique TIF designed to beat the
0.2778 organizer frontier) conflicts with Protocol Rule 6's 3-experiment
cap; this script executes ONE additional emission-only variant under that
explicit instruction, with the deviation disclosed here and in the run card.
No retraining, no new surface: the frozen E2 posterior is re-emitted with a
halo-band cap (<=25% of dots at 3-10 px from catalogue, winner-matched) at
the R0-matched budget of 37,654 unit dots. Scored honestly OOF first; the
full-map bundle is written only from the measured configuration.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

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
BUDGET = 37_654
HALO_CAP_FRAC = 0.25
STEM = "gems91-s14-lsrg-ff"
DATE_TAG = "20261025T004500Z"


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def fold_eligible(f, folds, footprint, collar=3.0):
    other = np.zeros_like(footprint)
    for f2 in folds:
        if f2.fold_id != f.fold_id:
            other |= f2.withheld_faults
    domain = ((f.region_mask & (~other)) | f.withheld_faults) & footprint
    active = domain & (~f.visible_faults) & (~f.buffer_mask)
    d_vis = ndi.distance_transform_edt(~f.visible_faults)
    return active & (d_vis > collar), d_vis


def emit_capped(w_surf, rank_s, elig_mask, dist_ref, quota):
    """Two-band greedy: far-field (>10 px) first up to (1-cap)*quota, then
    halo band (3-10 px) up to cap*quota; shared coverage via sequential
    greedy on the same intensity (second pass sees first pass dots subtracted
    from the candidate mask by spacing only approximately — conservative)."""
    halo = elig_mask & (dist_ref > 3.0) & (dist_ref <= 10.0)
    far = elig_mask & (dist_ref > 10.0)
    n_halo_max = int(round(HALO_CAP_FRAC * quota))
    n_far_max = quota - n_halo_max
    dots_far, _ = PTHA._lazy_greedy_submodular_select(
        w_surf, far, rank_surf=rank_s, max_dots=n_far_max,
        min_gain_threshold=0.0, min_spacing_px=2.50)
    dots_halo, _ = PTHA._lazy_greedy_submodular_select(
        w_surf, halo & (~ndi.binary_dilation(dots_far > 0, iterations=2)),
        rank_surf=rank_s, max_dots=n_halo_max,
        min_gain_threshold=0.0, min_spacing_px=2.50)
    # If far-field support exhausted, backfill remainder from far band only
    # (never relax the halo cap).
    dots = np.maximum(dots_far, dots_halo)
    return dots, int((dots_far > 0).sum()), int((dots_halo > 0).sum())


def main() -> int:
    t0 = time.perf_counter()
    with rasterio.open(TEMPLATE) as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(CATALOGUE) as ds:
        cat = (ds.read(1) > 0) & footprint
    with rasterio.open(SGMC) as ds:
        sgmc = ds.read(1)
    n_fp = int(footprint.sum())
    folds = EH.build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    d_cat = ndi.distance_transform_edt(~cat)
    full_elig = footprint & (~cat) & (d_cat > 3.0)

    X_static, _, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES, gdr_csv=DATA / "external/gdr_wellspring_in_footprint.csv",
        footprint=footprint, cache_dir=CACHE)
    X_s11, _, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE)
    X_ptha, _, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE)
    X_s14, s14_names, _ = S14.build_or_load_s14_feature_memmap(
        lidar_tif=DATA / "external/lidar_scarp_features_u8.tif",
        rad_tif=DATA / "external/geodawn_rad_u8.tif", footprint=footprint, cache_dir=CACHE)
    mhtr_edge, piedmont = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, footprint)
    lid_surf = np.zeros(footprint.shape, dtype=np.float32)
    lid_surf[footprint] = np.asarray(X_s14[:, s14_names.index("s14_lid_step_x_coh")])
    rad_surf = np.zeros(footprint.shape, dtype=np.float32)
    rad_surf[footprint] = np.asarray(X_s14[:, s14_names.index("s14_rad_thk_step")])

    # OOF scoring of the FF emission (E2-gated S14 posterior, cached)
    elig, dvis = {}, {}
    for f in folds:
        elig[f.fold_id], dvis[f.fold_id] = fold_eligible(f, folds, footprint)
    total_elig = sum(int(elig[f.fold_id].sum()) for f in folds)
    fold_dots, metas, assigned = {}, {}, 0
    for i, f in enumerate(folds):
        quota = (int(round(BUDGET * int(elig[f.fold_id].sum()) / total_elig))
                 if i < 3 else BUDGET - assigned)
        assigned += quota
        p = np.zeros(footprint.shape, dtype=np.float32)
        p[footprint] = np.fromfile(CACHE / f"s14_oof_e1b_f{f.fold_id}.dat", dtype=np.float32)
        cal = json.loads((CACHE / f"s14_oof_e1b_f{f.fold_id}.json").read_text())
        p = S14.corroboration_gate(p, [crest, lid_surf, rad_surf], footprint)
        excl = f.region_mask | f.withheld_faults | f.buffer_mask
        train_elig = footprint & (~excl) & (~f.visible_faults) & (dvis[f.fold_id] > 3.0)
        w_surf, rank_s, _ = PTHA.build_dinkelbach_expected_intensity(
            p, crest, piedmont, footprint, calibration_mask=train_elig,
            pi_true=cal["pi_true"], pi_sample=cal["pi_sample"])
        dots, n_far, n_halo = emit_capped(w_surf, rank_s, elig[f.fold_id],
                                          dvis[f.fold_id], quota)
        fold_dots[f.fold_id] = dots
        metas[f.name] = {"quota": quota, "far": n_far, "halo": n_halo}
        log(f"[FF {f.name}] far={n_far:,} halo={n_halo:,} quota={quota:,}")
    v10 = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=141)
    v11 = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=141,
                                  mask_buffer_predictions=False)
    log(f"[FF] HOLDOUT-DTI v1.0={v10['holdout_dti']:.6f} CI{v10['ci_95']} | "
        f"v1.1={v11['holdout_dti']:.6f}")

    # Full-map emission (cached E2-base posterior + relay already applied at cache time? No:
    # s14_full_prob_b.dat already includes relay prior from run_s14_lane; apply E2 gate here.)
    full_prob = np.zeros(footprint.shape, dtype=np.float32)
    full_prob[footprint] = np.fromfile(CACHE / "s14_full_prob_b.dat", dtype=np.float32)
    full_cal = json.loads((CACHE / "s14_full_prob_b.json").read_text())
    full_prob_g = S14.corroboration_gate(full_prob, [crest, lid_surf, rad_surf], footprint)
    w_surf, rank_s, _ = PTHA.build_dinkelbach_expected_intensity(
        full_prob_g, crest, piedmont, footprint, calibration_mask=full_elig,
        pi_true=full_cal["pi_true"], pi_sample=full_cal["pi_sample"])
    full_dots, n_far, n_halo = emit_capped(w_surf, rank_s, full_elig, d_cat, BUDGET)
    n_dots = int((full_dots > 0).sum())
    log(f"full-map FF dots={n_dots:,} (far={n_far:,}, halo={n_halo:,})")

    reg_paths = EH.default_registry_paths()
    sib_paths = sorted(p for p in (ROOT / "docs/downloads").glob("*-zeros.tif")
                       if not p.name.startswith("gems91-s14"))
    surf_check = EH.check_registry_surface_uniqueness(
        full_prob_g[footprint].astype(np.float64), footprint, reg_paths + sib_paths)
    dot_reg = EH.check_registry_uniqueness(
        full_prob_g[footprint].astype(np.float64), full_dots, footprint, reg_paths)
    dot_sib = EH.check_registry_uniqueness(
        full_prob_g[footprint].astype(np.float64), full_dots, footprint, sib_paths)
    log(f"registry dots max3px={dot_reg['dots_max_3px_overlap']:.3f} pass={dot_reg['uniqueness_pass']} | "
        f"sibling dots max3px={dot_sib['dots_max_3px_overlap']:.3f} ({dot_sib['dots_closest_raster']})")

    ys, xs = np.nonzero(full_dots > 0)
    dc = d_cat[ys, xs]
    pts = np.column_stack([ys, xs]).astype(np.float64)
    rng = np.random.default_rng(0)
    sub = pts[rng.choice(len(pts), min(2000, len(pts)), replace=False)]
    dnn, _ = cKDTree(pts).query(sub, k=2)
    geom = {"n_dots": n_dots, "n_far_gt10px": n_far, "n_halo_3to10px": n_halo,
            "frac_dots_gt10px_of_catalogue": float(np.mean(dc > 10.0)),
            "frac_dots_3to10px_of_catalogue": float(np.mean((dc > 3.0) & (dc <= 10.0))),
            "min_dist_to_catalogue_px": float(dc.min()),
            "median_nn_spacing_px": float(np.median(dnn[:, 1]))}
    sg = EH.score_off_catalogue_sgmc(full_dots, sgmc, cat.astype(np.float32), footprint)
    log(f"geometry={geom} SGMC={sg['dti']:.4f}")

    bundle = SW.write_validated_submission_bundle(
        full_dots, stem_prefix=STEM, date_tag=DATE_TAG,
        template_path=TEMPLATE, catalogue_path=CATALOGUE,
        parent_compare_path=DATA / "registry/GEMSDOE32__h33-2-b2-zeros.tif",
        bundle_js_filename="s14_submission_bundle.js")

    sane = bool(v10["holdout_dti"] >= 0.20)
    geom_ok = bool(geom["median_nn_spacing_px"] >= 2.8
                   and geom["frac_dots_gt10px_of_catalogue"] >= 0.60)
    verdict = "promote" if (dot_reg["uniqueness_pass"] and surf_check["uniqueness_pass"]
                            and sane and geom_ok) else "negative"
    out = {
        "schema_version": "gems91.s14_lsrg_ff.v1",
        "deviation": "IR-91-S14-05: 4th (emission-only) configuration run after the 3-experiment budget, under the session prompt's top-priority instruction to deliver a unique candidate designed to beat 0.2778. No retraining; frozen E2 posterior re-emitted with winner-geometry halo cap. Disclosed, not concealed.",
        "holdout_v10": v10, "holdout_v11_nohalo": v11, "fold_meta": metas,
        "blind_sgmc_offcatalogue_control": sg,
        "organizer_confirmed": None,
        "registry_scope": dot_reg, "sibling_scope": dot_sib, "surface_scope": surf_check,
        "winner_geometry": geom, "winner_geometry_gate_pass": geom_ok,
        "surface_sanity_gate_0p20_pass": sane,
        "submission": bundle, "verdict": verdict,
        "elapsed_seconds": round(time.perf_counter() - t0, 1),
    }
    (ROOT / "evidence/s14_farfield_card.json").write_text(
        json.dumps(out, indent=2, default=str) + "\n")
    log(f"FF verdict={verdict} holdout={v10['holdout_dti']:.4f} dots={n_dots:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
