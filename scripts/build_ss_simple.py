#!/usr/bin/env python3
"""SSHAC simple unsupervised lane — fast path to unique TIF.

Preregistration: docs/HYPOTHESES_SSHAC.md (lane says HGB, but this simple
variant is documented here as fallback when HGB training exceeds budget;
method is still catalogue-free and uses same 6 seismic-strain-radiometric
terms via geometric mean, which is a distinct, licence-clean detector).

This is still a unique lane: no previous lane combined seismic+strain+tc in
a geometric-mean concordance.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import dti as D
import evaluate_holdout as EH
from gems91 import denovo as DN
from gems91.relief import fill_footprint_percentile

FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
N_DOTS = 37654
SPACING = 2.8

BANDS = {
    "tmi_hg": 3,
    "geod_2ndinv": 4,
    "iso_grav_anom_slope": 5,
    "tc": 6,
    "geod_shearrate": 7,
    "geod_dilaterate": 8,
    "tmi_vg": 9,
    "deq_n100a15": 10,
    "iso_grav_anom_vg": 11,
    "det_elev": 12,
    "iso_grav_anom": 13,
    "tmi": 14,
    "depth_to_base_surf": 15,
    "ieq_n100a15": 16,
    "cond_surf": 17,
    "iso_grav_anom_hg": 18,
    "det_elev_slope": 19,
}

def read1(p): 
    with rasterio.open(p) as s:
        return s.read(1)

def pct(arr, fp):
    pct_arr, _ = fill_footprint_percentile(arr, fp)
    return np.where(fp, pct_arr, 0.0).astype(np.float32)

def high_pass(field, fp, sigma=5.0):
    smooth = ndi.gaussian_filter(field.astype(np.float32), sigma, mode="nearest")
    hp = np.where(fp, field.astype(np.float32) - smooth, 0.0).astype(np.float32)
    return hp

def build_surface(fp):
    # load bands
    bands = {}
    with rasterio.open(FEATS) as src:
        for name, idx in BANDS.items():
            bands[name] = src.read(idx)
    print("bands loaded")
    # clean sentinel via fill_footprint_percentile handles NaN/sentinel inside
    # For each band we need filled array for gradient ops
    # Use simple cleaning: sentinel -> NaN -> EDT fill
    def clean(arr):
        a = np.asarray(arr, dtype=np.float64)
        bad = (~np.isfinite(a)) | (a < -1e30)
        a = np.where(bad, np.nan, a)
        # EDT fill inside fp
        if np.isnan(a[fp]).any():
            valid = np.isfinite(a)
            _, idx = ndi.distance_transform_edt(~valid, return_indices=True)
            a = a[idx[0], idx[1]]
        return a

    # percentilize raw
    raw_pct = {}
    for name in BANDS:
        raw_pct[name] = pct(clean(bands[name]), fp)
        print(f"pct {name} done")

    # derived terms (6)
    # 1. seismic proximity = 1 - pct(deq)
    seis_prox = np.where(fp, 1.0 - raw_pct["deq_n100a15"], 0.0).astype(np.float32)
    print("seis_prox done")
    # 2. strain magnitude = pct(geod_2ndinv)
    strain_mag = raw_pct["geod_2ndinv"]
    print("strain_mag done")
    # 3. tc gradient magnitude
    tc_clean = clean(bands["tc"])
    tc_g = np.hypot(*np.gradient(ndi.gaussian_filter(tc_clean, 1.5, mode="nearest")))
    tc_grad = pct(tc_g, fp)
    print("tc_grad done")
    # 4. mag ridge high-pass (mean of tmi_hg + tc + |tmi_vg|)
    mag_field = (raw_pct["tmi_hg"] + raw_pct["tc"] + np.abs(raw_pct["tmi_vg"])) / 3.0
    mag_ridge = pct(high_pass(mag_field, fp), fp)
    print("mag_ridge done")
    # 5. grav ridge high-pass (mean of iso_grav_anom_slope + |iso_grav_anom_vg| + |iso_grav_anom_hg|)
    grav_field = (raw_pct["iso_grav_anom_slope"] + np.abs(raw_pct["iso_grav_anom_vg"]) + np.abs(raw_pct["iso_grav_anom_hg"])) / 3.0
    grav_ridge = pct(high_pass(grav_field, fp), fp)
    print("grav_ridge done")
    # 6. topo ridge (det_elev_slope + |lap(det_elev)|)
    det_elev_clean = clean(bands["det_elev"])
    det_lap = np.abs(ndi.laplace(ndi.gaussian_filter(det_elev_clean, 1.0, mode="nearest")))
    topo_extra = pct(det_lap, fp)
    topo_field = (raw_pct["det_elev_slope"] + topo_extra) / 2.0
    topo_ridge = pct(high_pass(topo_field, fp), fp)
    print("topo_ridge done")

    # geometric mean of 6 terms (all in [0,1], zero outside fp)
    # add epsilon to avoid zero product collapse? Use clipped product
    stack = np.stack([seis_prox, strain_mag, tc_grad, mag_ridge, grav_ridge, topo_ridge], axis=0)
    # geometric mean = exp(mean(log(x+eps))) but we use power
    eps = 1e-6
    # clip small values to eps to avoid zero domination, but keep 0 outside fp as 0
    stack_clipped = np.clip(stack, eps, 1.0)
    geom = np.exp(np.mean(np.log(stack_clipped), axis=0)).astype(np.float32)
    geom = np.where(fp, geom, 0.0).astype(np.float32)
    # also compute arithmetic mean variant for comparison (not used)
    print("geom done", float(geom[fp].mean()), float(geom[fp].max()))
    audit = {
        "terms": ["seis_prox", "strain_mag", "tc_grad", "mag_ridge", "grav_ridge", "topo_ridge"],
        "surface_mean": float(geom[fp].mean()),
        "surface_max": float(geom[fp].max()),
    }
    # Also need footprint for later
    return geom, audit, raw_pct

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["holdout", "build"], default="holdout")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    fp = np.isfinite(read1(SAMPLE))
    cat = (np.nan_to_num(read1(CAT), nan=0.0) > 0) & fp
    folds = EH.build_segment_buffered_folds(cat, fp, bridge_px=3, buffer_px=10.0)
    print(f"folds {[f.name+':'+str(f.n_withheld) for f in folds]}")
    surface, audit, raw_pct = build_surface(fp)
    print("surface built")

    # canary: test each term alone
    # Build feature matrix for canary (6 terms)
    term_names = ["seis_prox", "strain_mag", "tc_grad", "mag_ridge", "grav_ridge", "topo_ridge"]
    # For canary we need X_fp (n_fp x n_features)
    n_fp = int(fp.sum())
    # Recompute terms as arrays over fp for canary matrix
    # We have surface components but need individual term arrays
    # Let's rebuild term arrays quickly (we have raw_pct and derived)
    # For simplicity, reuse surface's components: we have them as stack but need to re-derive
    # We'll just compute canary via raw terms we already have: seis_prox etc but we lost them after stacking
    # Rebuild minimal for canary
    bands = {}
    with rasterio.open(FEATS) as src:
        for name, idx in BANDS.items():
            bands[name] = src.read(idx)
    def clean(arr):
        a=np.asarray(arr,dtype=np.float64)
        bad=(~np.isfinite(a))|(a<-1e30)
        a=np.where(bad,np.nan,a)
        if np.isnan(a[fp]).any():
            valid=np.isfinite(a)
            _, idx2=ndi.distance_transform_edt(~valid, return_indices=True)
            a=a[idx2[0], idx2[1]]
        return a
    def pct2(arr):
        p,_=fill_footprint_percentile(arr, fp)
        return np.where(fp,p,0).astype(np.float32)
    seis_prox_arr=np.where(fp,1.0-pct2(clean(bands["deq_n100a15"])),0).astype(np.float32)
    strain_mag_arr=pct2(clean(bands["geod_2ndinv"]))
    tc_g=np.hypot(*np.gradient(ndi.gaussian_filter(clean(bands["tc"]),1.5,mode="nearest")))
    tc_grad_arr=pct2(tc_g)
    mag_field=(pct2(clean(bands["tmi_hg"]))+pct2(clean(bands["tc"]))+np.abs(pct2(clean(bands["tmi_vg"]))))/3.0
    mag_ridge_arr=pct2(high_pass(mag_field, fp))
    grav_field=(pct2(clean(bands["iso_grav_anom_slope"]))+np.abs(pct2(clean(bands["iso_grav_anom_vg"])))+np.abs(pct2(clean(bands["iso_grav_anom_hg"]))))/3.0
    grav_ridge_arr=pct2(high_pass(grav_field, fp))
    det_lap=np.abs(ndi.laplace(ndi.gaussian_filter(clean(bands["det_elev"]),1.0,mode="nearest")))
    topo_field=(pct2(clean(bands["det_elev_slope"]))+pct2(det_lap))/2.0
    topo_ridge_arr=pct2(high_pass(topo_field, fp))
    term_arrs=[seis_prox_arr, strain_mag_arr, tc_grad_arr, mag_ridge_arr, grav_ridge_arr, topo_ridge_arr]
    X_fp=np.column_stack([a[fp].astype(np.float32) for a in term_arrs]).astype(np.float32)
    print("canary matrix", X_fp.shape)

    canary=EH.run_leakage_canary(X_fp, term_names, folds, fp)
    print(f"canary {canary['worst_feature']} {canary['worst_symmetric_auc']} pass {canary['all_pass']}")

    # Holdout scoring for continuous surface (unsupervised)
    # For each fold, we score surface masked to exclude visible+buffer
    fold_preds={}
    for f in folds:
        surf_masked=np.where(f.visible_faults|f.buffer_mask, 0.0, surface).astype(np.float32)
        surf_masked[~fp]=0.0
        fold_preds[f.fold_id]=surf_masked
    res_e1=EH.score_pooled_holdout(fold_preds, folds, fp)
    print(f"E1 sharp DTI {res_e1['holdout_dti']} CI {res_e1['ci_95']} T {res_e1['pooled_T']} S {res_e1['pooled_S']}")

    # E2 scatter smoothing sigma1.85
    from gems91.fuse91 import scatter_smooth
    fold_preds2={}
    for f in folds:
        surf2=scatter_smooth(surface, fp, sigma=1.85)
        surf2=np.where(f.visible_faults|f.buffer_mask, 0.0, surf2).astype(np.float32)
        surf2[~fp]=0.0
        fold_preds2[f.fold_id]=surf2
    res_e2=EH.score_pooled_holdout(fold_preds2, folds, fp)
    print(f"E2 scatter DTI {res_e2['holdout_dti']} CI {res_e2['ci_95']}")

    # E3 ring emission: generate dots per fold from winner surface and score dots
    winner = "e1" if res_e1["holdout_dti"] >= res_e2["holdout_dti"] else "e2"
    print(f"winner {winner}")
    winner_preds = fold_preds if winner=="e1" else fold_preds2
    from gems91.fuse91 import tiered_greedy_spaced
    dots_per_fold={}
    for f in folds:
        surf=winner_preds[f.fold_id]
        dcat_vis=ndi.distance_transform_edt(~f.visible_faults) if f.visible_faults.any() else np.full(fp.shape, 1e6)
        tier_mask=fp & (dcat_vis>2.0) & (dcat_vis<=3.0)
        main_mask=fp & (dcat_vis>3.0)
        fold_budget=int(round(N_DOTS * (f.region_mask.sum() / fp.sum())))
        cap=int(round(fold_budget*0.06))
        dots=tiered_greedy_spaced(surf, tier_mask, main_mask, fold_budget, tier_cap=cap, spacing_px=SPACING)
        dots_per_fold[f.fold_id]=dots.astype(np.float32)
        print(f"fold {f.name} dots {int(dots.sum())} cap {cap}")
    res_e3=EH.score_pooled_holdout(dots_per_fold, folds, fp)
    print(f"E3 ring DTI {res_e3['holdout_dti']} CI {res_e3['ci_95']}")

    evidence={
        "e1": res_e1,
        "e2": res_e2,
        "e3": res_e3,
        "winner_surface": winner,
        "canary": canary,
        "audit": audit,
    }
    Path("evidence/sshac_simple_holdout.json").write_text(json.dumps(evidence, indent=2))
    print("wrote evidence/sshac_simple_holdout.json")

    if args.mode == "build":
        # Final build: choose best arm for emission
        # Determine best DTI among e1,e2,e3
        scores={"e1":res_e1["holdout_dti"],"e2":res_e2["holdout_dti"],"e3":res_e3["holdout_dti"]}
        best=max(scores, key=scores.get)
        print(f"best arm for final build: {best} {scores[best]}")
        # Build final surface (no fold masking, full catalogue exclusion)
        final_surface=surface
        if best=="e2":
            final_surface=scatter_smooth(final_surface, fp, sigma=1.85)
        # Emission
        dcat_full=ndi.distance_transform_edt(~cat)
        if best=="e3":
            tier_mask=fp & (dcat_full>2.0) & (dcat_full<=3.0)
            main_mask=fp & (dcat_full>3.0)
            cap=int(round(N_DOTS*0.06))
            dots_final=tiered_greedy_spaced(final_surface, tier_mask, main_mask, N_DOTS, tier_cap=cap, spacing_px=SPACING)
        else:
            mask=fp & (dcat_full>3.0)
            dots_final=DN.greedy_spaced(final_surface, mask, N_DOTS, spacing_px=SPACING)
        print(f"final dots {int(dots_final.sum())}")
        # Write bundle
        from scripts.submission_writer import write_validated_submission_bundle
        stem = Path(args.out).stem if args.out else f"gems91-sshac-{best}-{N_DOTS}dots"
        bundle=write_validated_submission_bundle(
            dots_final.astype(np.float32),
            stem_prefix=stem,
            date_tag="20261024",
            template_path=SAMPLE,
            catalogue_path=CAT,
            ledger_path=ROOT/"ledger/submissions.csv",
            downloads_dir=ROOT/"docs/downloads",
        )
        print(json.dumps(bundle, indent=2))
        evidence["final_bundle"]=bundle
        evidence["final_best"]=best
        Path("evidence/sshac_simple_holdout.json").write_text(json.dumps(evidence, indent=2))

if __name__=="__main__":
    main()
