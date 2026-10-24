#!/usr/bin/env python3
"""Fast final build for SSHAC simple lane — no holdout scoring, just emission."""

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
    p,_ = fill_footprint_percentile(arr, fp)
    return np.where(fp,p,0).astype(np.float32)

def high_pass(field, fp, sigma=5.0):
    smooth = ndi.gaussian_filter(field.astype(np.float32), sigma, mode="nearest")
    hp = np.where(fp, field.astype(np.float32)-smooth, 0).astype(np.float32)
    return hp

def main():
    fp = np.isfinite(read1(SAMPLE))
    cat = (np.nan_to_num(read1(CAT), nan=0.0) > 0) & fp
    print("fp", fp.sum(), "cat", cat.sum())
    bands={}
    with rasterio.open(FEATS) as src:
        for name, idx in BANDS.items():
            bands[name]=src.read(idx)
    print("bands loaded")
    def clean(arr):
        a=np.asarray(arr,dtype=np.float64)
        bad=(~np.isfinite(a))|(a<-1e30)
        a=np.where(bad,np.nan,a)
        if np.isnan(a[fp]).any():
            valid=np.isfinite(a)
            _, idx2=ndi.distance_transform_edt(~valid, return_indices=True)
            a=a[idx2[0], idx2[1]]
        return a
    raw_pct={}
    for name in BANDS:
        raw_pct[name]=pct(clean(bands[name]), fp)
        print(f"pct {name} ok")
    seis_prox=np.where(fp,1.0-pct(clean(bands["deq_n100a15"]),fp),0).astype(np.float32)
    print("seis_prox")
    strain_mag=raw_pct["geod_2ndinv"]
    tc_g=np.hypot(*np.gradient(ndi.gaussian_filter(clean(bands["tc"]),1.5,mode="nearest")))
    tc_grad=pct(tc_g, fp)
    print("tc_grad")
    mag_field=(raw_pct["tmi_hg"]+raw_pct["tc"]+np.abs(raw_pct["tmi_vg"]))/3.0
    mag_ridge=pct(high_pass(mag_field, fp), fp)
    print("mag_ridge")
    grav_field=(raw_pct["iso_grav_anom_slope"]+np.abs(raw_pct["iso_grav_anom_vg"])+np.abs(raw_pct["iso_grav_anom_hg"]))/3.0
    grav_ridge=pct(high_pass(grav_field, fp), fp)
    print("grav_ridge")
    det_lap=np.abs(ndi.laplace(ndi.gaussian_filter(clean(bands["det_elev"]),1.0,mode="nearest")))
    topo_field=(raw_pct["det_elev_slope"]+pct(det_lap, fp))/2.0
    topo_ridge=pct(high_pass(topo_field, fp), fp)
    print("topo_ridge")
    stack=np.stack([seis_prox, strain_mag, tc_grad, mag_ridge, grav_ridge, topo_ridge], axis=0)
    eps=1e-6
    stack_clipped=np.clip(stack, eps, 1.0)
    geom=np.exp(np.mean(np.log(stack_clipped), axis=0)).astype(np.float32)
    geom=np.where(fp, geom, 0).astype(np.float32)
    print("geom mean", float(geom[fp].mean()), "max", float(geom[fp].max()))
    # emission
    dcat=ndi.distance_transform_edt(~cat)
    mask=fp & (dcat>3.0)
    print("emitting", N_DOTS, "spacing", SPACING, "eligible", int(mask.sum()))
    dots=DN.greedy_spaced(geom, mask, N_DOTS, spacing_px=SPACING)
    print("dots", int(dots.sum()), flush=True)
    print("starting write bundle", flush=True)
    # write bundle
    import importlib.util, pathlib, traceback
    spec=importlib.util.spec_from_file_location("submission_writer", ROOT/"scripts/submission_writer.py")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        bundle=mod.write_validated_submission_bundle(
            dots.astype(np.float32),
            stem_prefix=f"gems91-sshac-simple-{N_DOTS}dots",
            date_tag="20261024",
            template_path=SAMPLE,
            catalogue_path=CAT,
            ledger_path=ROOT/"ledger/submissions.csv",
            downloads_dir=ROOT/"docs/downloads",
        )
        print(json.dumps(bundle, indent=2), flush=True)
    except Exception as e:
        traceback.print_exc()
        print(f"write failed {e}", flush=True)
        raise
    # also save surface for audit
    np.save(ROOT/"evidence/sshac_surface.npy", geom)
    Path("evidence/sshac_simple_build.json").write_text(json.dumps({"audit": {"surface_mean": float(geom[fp].mean())}, "bundle": bundle}, indent=2))

if __name__=="__main__":
    main()
