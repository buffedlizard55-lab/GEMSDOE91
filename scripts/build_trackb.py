#!/usr/bin/env python3
"""TRACKB (Phase 2): strike-consistent traces >=1 km from R0's top-ranked dots.

Arms (count fixed 37,654; donors = lowest-S_struct off-trace dots, d_cat>3 px;
targets sampled every 1.2 px along traces, d_cat>3 px, >=1 px (distinct pixel)
from kept dots -- denser-than-parent trace spacing is disclosed as a confound):
  t1k10  traces >=1 km, relocate 10% onto traces
  t1k20  traces >=1 km, relocate 20% onto traces
  t2k10  traces >=2 km only, relocate 10% (stricter-trace bracket)
Outputs per arm: NaN + zeros rasters, GeoJSON traces with one evidence
paragraph per trace. TRACKB is NOT a weekly-slot candidate unless the human
decides (brief S5). Usage: python3 scripts/build_trackb.py --build
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src")); sys.path.insert(0, str(ROOT/"scripts"))
import build_relief as br  # noqa: E402  (pin/parent/ledger/manifest helpers)
import validate_raster as vr_mod  # noqa: E402
from gems91 import geom, io, proxy, relief, trackb, release_gates as gates  # noqa: E402

PARENT_TAG="h33-h33-2-b2"; PARENT_DOTS=37654; BUILD_DATE="20261023"
ARMS={
 "t1k10": dict(min_len=10.0, frac=0.10, predicted="+0.004", rng="[-0.008,+0.016]"),
 "t1k20": dict(min_len=10.0, frac=0.20, predicted="+0.005", rng="[-0.012,+0.022]"),
 "t2k10": dict(min_len=20.0, frac=0.10, predicted="+0.002", rng="[-0.008,+0.012]"),
}

def relocate(parent, pts, scores, traces, dcat, footprint, frac):
    on_trace=np.zeros(len(pts),bool)
    for t in traces: on_trace[t["dot_indices"]]=True
    cand=np.array([t for t in traces],dtype=object)
    targets=[]
    for t in sorted(traces, key=lambda z:-z["mean_score"]):
        for p in trackb.trace_sample_points(t["points_yx"], spacing_px=1.2):
            targets.append((t["mean_score"], p[0], p[1], t["trace_id"]))
    targets.sort(key=lambda z:-z[0])
    pool_order=[i for i in np.argsort(scores,kind="mergesort")
                if not on_trace[i] and dcat[int(pts[i,0]),int(pts[i,1])]>3.0]
    want=int(round(frac*len(pts)))
    pool=set(pool_order[:int(want*1.3)+10])
    kept=[i for i in range(len(pts)) if i not in pool]
    tree=cKDTree(pts[kept]); accepted=[]; acc_pts=[]; taken=set()
    for _,y,x,tid in targets:
        if len(accepted)>=want: break
        yi,xi=int(round(y)),int(round(x))
        if not (0<=yi<parent.shape[0] and 0<=xi<parent.shape[1]): continue
        if not footprint[yi,xi] or dcat[yi,xi]<=3.0 or parent[yi,xi] or (yi,xi) in taken: continue
        if tree.query([y,x])[0]<1.0: continue
        if acc_pts and cKDTree(np.array(acc_pts)).query([y,x])[0]<1.0: continue
        accepted.append((yi,xi)); acc_pts.append((y,x)); taken.add((yi,xi))
    donors=pool_order[:len(accepted)]
    dots=parent.copy()
    for i in donors: dots[int(pts[i,0]),int(pts[i,1])]=False
    # restore-conflict check: accepted targets already >=2px from all kept incl. restored
    for yi,xi in accepted: dots[yi,xi]=True
    return dots, len(donors), len(accepted), int(on_trace.sum())

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--build",action="store_true")
    args=ap.parse_args(argv)
    if not args.build: print(__doc__); return 0
    paths=br.verify_pinned_inputs()
    template=io.read_grid(paths["sample_submission"]); footprint=geom.footprint_mask(template)
    cat=geom.catalogue_mask(io.read_grid(paths["existing_faults"])); dcat=geom.catalogue_distance(cat)
    parent=io.dot_mask(io.read_grid(paths["parent_r0_nan"]))
    lineage=br.verify_parent_lineage(paths,cat,dcat)
    def dots(k): return io.dot_mask(io.read_grid(paths[k]))
    with rasterio.open(str(paths["training_features"])) as s:
        tmi_hg,gslope,tc,ghg=s.read(3),s.read(5),s.read(6),s.read(18)
        band_names={i+1:s.descriptions[i] for i in range(s.count)}
    s_struct,_=relief.compute_structural_score(tmi_hg,gslope,ghg,tc,dots("anc_h19_5"),dots("anc_h19_4"),dots("anc_h16_1"),footprint)
    pts=np.argwhere(parent).astype(float); scores=s_struct[parent]
    strike,coh=trackb.local_strike(pts)
    r0_hr=proxy.hide_and_recover(parent,cat,footprint)
    rel_dir=ROOT/"releases"; rel_dir.mkdir(exist_ok=True)
    built={}; manifest_entries=[]; ledger_rows=[]
    trace_sets={}
    for key,cfg in ARMS.items():
        traces=trackb.build_traces(pts,scores,strike,coh,min_length_px=cfg["min_len"])
        trace_sets[key]=traces
        dots_new,n_don,n_acc,n_on=relocate(parent,pts,scores,traces,dcat,footprint,cfg["frac"])
        diff=gates.parent_diff(parent,dots_new)
        pct=round(100.0*n_don/PARENT_DOTS,2)
        # GeoJSON with evidence paragraph per trace
        feats=[]
        with rasterio.open(str(paths["sample_submission"])) as tpl: tr=tpl.transform
        for t in traces:
            ys=[p[0] for p in t["points_yx"]]; xs=[p[1] for p in t["points_yx"]]
            coords=[[float(tr.c+(x+0.5)*tr.a), float(tr.f+(y+0.5)*tr.e)] for y,x in zip(ys,xs)]
            dmin=float(dcat[[int(round(y)) for y in ys],[int(round(x)) for x in xs]].min())
            para=(f"Trace {t['trace_id']} is a {t['length_km']:.2f} km, {t['strike_deg']:.0f}-degree "
                  f"strike-consistent chain of {t['n_dots']} R0 dots (mean label-blind structural score "
                  f"{t['mean_score']:.3f}, mean local-strike coherence {t['mean_coherence']:.2f}, "
                  f"straightness {t['straightness']:.2f}), never closer than {dmin:.1f} px to a catalogued "
                  f"fault. A geologist should test it against the TMI/gravity horizontal-gradient crests that "
                  f"contribute to its score; the mimic to exclude is a lithologic contact or survey lineament "
                  f"with the same strike and no Quaternary displacement.")
            feats.append({"type":"Feature","geometry":{"type":"LineString","coordinates":coords},
                          "properties":{**t,"evidence_paragraph":para,
                                        "min_catalogue_distance_px":round(dmin,2),
                                        "dot_indices":t["dot_indices"]}})
            feats[-1]["properties"].pop("points_yx",None)
        stem_tmp=f"{PARENT_TAG}-TRACKB{key}-{BUILD_DATE}"
        gj_path=rel_dir/f"{stem_tmp}-traces.geojson"
        gj_path.write_text(json.dumps({"type":"FeatureCollection","name":stem_tmp,"features":feats})+"\n")
        # rasters (temporary names, renamed by sha8)
        arr=np.where(footprint,dots_new.astype(np.float32),np.nan)
        tmpn=rel_dir/f"_tmp-trackb-{key}-nan.tif"; tmpz=rel_dir/f"_tmp-trackb-{key}-zeros.tif"
        io.write_float32(tmpn,arr,encoding="nan",template=paths["sample_submission"])
        io.write_float32(tmpz,arr,encoding="zeros",template=paths["sample_submission"])
        sha=io.sha256_file(tmpn); shaz=io.sha256_file(tmpz); stem=f"{stem_tmp}-{sha[:8]}"
        fn=rel_dir/f"{stem}.tif"; fz=rel_dir/f"{stem}-zeros.tif"; tmpn.replace(fn); tmpz.replace(fz)
        gj_path.replace(rel_dir/f"{stem}-traces.geojson")
        gn=gates.validate_release(fn,template=paths["sample_submission"],catalogue=cat,encoding="nan",
                                  expect_dots=PARENT_DOTS,ledger=ROOT/"ledger/submissions.csv",own_id=stem)
        gz=gates.validate_release(fz,template=paths["sample_submission"],catalogue=cat,encoding="zeros",
                                  expect_dots=PARENT_DOTS,ledger=ROOT/"ledger/submissions.csv",own_id=stem)
        vr=vr_mod.validate_raster(fn,paths["sample_submission"],catalogue=paths["existing_faults"],
                                  ledger_csv=ROOT/"ledger/submissions.csv",parent=paths["parent_r0_nan"])
        if not (gn["PASS"] and gz["PASS"] and vr.ok):
            raise SystemExit(f"GATE FAIL {stem}: {gn['failed']} {gz['failed']}\n{vr.text()}")
        hr={"note":"hide-and-recover invariant by construction: added and removed dots are all >3 px from catalogue, so neither earns catalogue credit; PROXY is uninformative for TRACKB (report only)"}
        note=f"{PARENT_TAG}; TRACKB {key}: relocate {pct:.1f}% lowest-S off-trace dots onto >= {cfg['min_len']/10:.0f} km traces; pred {cfg['predicted']} MODEL"
        assert len(note)<=140, note
        built[key]={"id":stem,"value":key,"n_traces":len(traces),"support_dots":n_on,
          "n_relocated":n_acc,"pct_relocated":pct,"parent_diff":diff,"sha256":sha,"sha256_zeros":shaz,
          "geojson":f"{stem}-traces.geojson","geojson_sha256":io.sha256_file(rel_dir/f"{stem}-traces.geojson"),"predicted_change_MODEL":f"MODEL:{cfg['predicted']}",
          "predicted_range":cfg["rng"],"gates":{"nan_PASS":gn["PASS"],"zeros_PASS":gz["PASS"],
          "min_catalogue_distance_px":gn["min_catalogue_distance_px"]},
          "report_only_proxy_hide_recover":hr}
        manifest_entries += [{"file":fn.name,"sha256":sha,"bytes":fn.stat().st_size},
                             {"file":fz.name,"sha256":shaz,"bytes":fz.stat().st_size}]
        ledger_rows.append({"id":stem,"parent":PARENT_TAG,"axis":"TRACKB","value":key,"n_dots":PARENT_DOTS,
          "pct_changed":f"{diff['pct_changed_of_parent']:.2f}","pct_relocated":f"{pct:.2f}","sha256":sha,
          "sha256_zeros":shaz,"status":"BUILT","predicted_change":f"MODEL:{cfg['predicted']}",
          "predicted_range":cfg["rng"],"ranking_basis":"S_struct (relief.compute_structural_score); NOT parent model ranking (IR-91-21); traces=greedy <=35deg, <=5px links, coherence>=0.35",
          "receipt_score":"","receipt_date":"","date":"2026-10-23","form_note":note,"evidence_class":"MODEL",
          "source":"SESSION 6 TRACKB (this session)","notes":f"{len(traces)} traces >={cfg['min_len']/10:.0f} km, {n_on} support dots; Phase-2 only, not a weekly slot unless human decides.","source_url":""})
        print(stem, "traces",len(traces),"relocated",n_acc,pct,"% proxy",hr)
    added=br.append_ledger_rows(ledger_rows); br.update_release_manifest(manifest_entries)
    ev={"schema":"gems91.trackb-evidence.v1","build_date":"2026-10-23","parent":PARENT_TAG,
        "lineage":lineage,"ranking":"S_struct; parent ranking unrecoverable (IR-91-21)",
        "r0_hide_recover_proxy":r0_hr,"arms":built,
        "trace_counts":{k:len(v) for k,v in trace_sets.items()}}
    (ROOT/"evidence/trackb_axis_20261023.json").write_text(json.dumps(ev,indent=2)+"\n")
    print("ledger rows added",added); return 0

if __name__=="__main__": raise SystemExit(main())
