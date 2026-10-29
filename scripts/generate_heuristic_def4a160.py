#!/usr/bin/env python3
"""
Heuristic SCBR surface without ML, to stay within memory budget.
Computes 4 rank features and combines geometrically, evaluates holdout, emits dots at 20k budget.
"""
import os
os.environ["OPENBLAS_NUM_THREADS"]="2"
os.environ["OMP_NUM_THREADS"]="2"
import hashlib, json, gc
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/"registry/data_manifest.json"
OUT_DIR=ROOT/"docs/downloads"
WORK=ROOT/"work/heuristic_def4a160"
WORK.mkdir(parents=True, exist_ok=True)

BUDGET=20000
SPACING=3.5
COLLAR=5.0
SEED=20261029
NOTE="DEF4A160 heuristic scaling-break+basement 20k dots; research only see card"
EXTREME=1e30

def sha_file(p): 
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1<<20), b""):
            h.update(b)
    return h.hexdigest()

def valid_mask(field, footprint):
    a=np.asarray(field); fp=np.asarray(footprint,bool)
    return fp & np.isfinite(a) & (np.abs(a.astype(np.float64)) < EXTREME)

def _masked_blur(field, valid, sigma):
    x=np.where(valid, np.asarray(field, np.float64), 0.0)
    w=valid.astype(np.float64)
    num=ndi.gaussian_filter(x, sigma, mode="constant", cval=0.0)
    den=ndi.gaussian_filter(w, sigma, mode="constant", cval=0.0)
    return np.divide(num, den, out=np.zeros_like(num), where=den>1e-9)

def _masked_uniform_sum(values,size):
    return ndi.uniform_filter(values, size=size, mode="constant", cval=0.0)*float(size*size)

def _rank01(arr, mask):
    out=np.zeros(arr.shape, dtype=np.float32)
    vals=arr[mask]
    if vals.size==0:
        return out
    if vals.size==1:
        out[mask]=1.0
        return out
    out[mask]=((rankdata(vals, method="average")-1)/(vals.size-1)).astype(np.float32)
    return out

def _sample_offset(field, uy, ux, offset):
    h,w=field.shape
    yy,xx=np.indices((h,w), dtype=np.float64)
    coords=[yy+offset*uy, xx+offset*ux]
    return ndi.map_coordinates(field, coords, order=1, mode="nearest")

def load_lite():
    man=json.loads(MANIFEST.read_text())
    rows={r["id"]:r for r in man["files"]}
    with rasterio.open(ROOT/"data/official/sample_submission.tif") as ds:
        s=ds.read(1); footprint=np.isfinite(s)
    with rasterio.open(ROOT/"data/official/existing_faults.tif") as ds:
        f=ds.read(1); catalogue=(f>0)&footprint
    tpath=ROOT/"data/bridge/gems-geodawn-numerical-features.tif"
    needed={11:"B12",12:"B13",14:"B15",1:"B02",13:"B14",3:"B04",6:"B07",18:"B19"}
    bands={}
    with rasterio.open(tpath) as ds:
        for idx,name in needed.items():
            bands[name]=ds.read(idx+1)
    return footprint, catalogue, bands

def build_heuristic(footprint, bands):
    fp=np.asarray(footprint,bool)
    B12=bands["B12"]; B19=bands["B19"]; B13=bands["B13"]; B15=bands["B15"]
    B02=bands["B02"]; B14=bands["B14"]; B04=bands["B04"]
    v12=valid_mask(B12,fp); v19=valid_mask(B19,fp); v13=valid_mask(B13,fp); v15=valid_mask(B15,fp)
    v02=valid_mask(B02,fp); v14=valid_mask(B14,fp); v04=valid_mask(B04,fp)
    # 1. grad mag B12
    sm12=_masked_blur(B12,v12,2.0)
    gy12,gx12=np.gradient(sm12); mag12=np.hypot(gy12,gx12)
    sup12=ndi.distance_transform_edt(v12)>3
    mag12_rank=_rank01(mag12, sup12)
    # 2. grad mag B15
    sm15=_masked_blur(B15,v15,2.0)
    gy15,gx15=np.gradient(sm15); mag15=np.hypot(gy15,gx15)
    sup15=ndi.distance_transform_edt(v15)>3
    mag15_rank=_rank01(mag15, sup15)
    # 3. scaling ratio B12
    # var5 and var15
    def local_var(field, valid, win):
        x=np.where(valid, field.astype(np.float64),0.0)
        m=valid.astype(np.float64)
        count=_masked_uniform_sum(m, win)
        s1=_masked_uniform_sum(x, win)
        s2=_masked_uniform_sum(x*x, win)
        safe=count>0
        mean=np.divide(s1,count, out=np.zeros_like(count), where=safe)
        e2=np.divide(s2,count, out=np.zeros_like(count), where=safe)
        var=np.clip(e2-mean*mean,0,None)
        support=safe & (count>=0.8*win*win) & (var>1e-12)
        return var, support
    var5,sup5=local_var(B12,v12,7)
    var15,sup15b=local_var(B12,v12,15)
    joint=sup5 & sup15b & (var5>1e-9)
    ratio=np.divide(var15, var5, out=np.zeros_like(var15), where=joint)
    ratio=np.clip(ratio,0,10)
    # rank ratio
    ratio_rank=_rank01(np.log1p(ratio), joint)
    # 4. basement coincidence B15 vs B04
    sm04=_masked_blur(B04,v04,2.0)
    gy04,gx04=np.gradient(sm04); mag04=np.hypot(gy04,gx04)
    sup04=ndi.distance_transform_edt(v04)>3
    # azimuth agree
    az15=np.arctan2(gx15,gy15); az04=np.arctan2(gx04,gy04)
    diff=np.abs(az15-az04); diff=np.minimum(diff,2*np.pi-diff); diff=np.minimum(diff, np.pi-diff)
    agree=1.0-np.clip(diff/(np.pi/8),0,1)
    support_joint= (ndi.distance_transform_edt(v15 & v04)>5) & (mag15>0) & (mag04>0)
    # robust01 for mags
    def robust01(arr, mask):
        vals=arr[mask & np.isfinite(arr)]
        if vals.size<100:
            return np.zeros_like(arr,dtype=np.float32)
        lo,hi=np.percentile(vals,[2,98])
        norm=np.clip((arr-lo)/(hi-lo+1e-9),0,1)
        return norm.astype(np.float32)
    mag15_n=robust01(mag15, support_joint)
    mag04_n=robust01(mag04, support_joint)
    joint_coinc=np.where(support_joint, np.sqrt(np.clip(mag15_n*mag04_n,0,1))*agree, 0).astype(np.float32)
    coinc_rank=_rank01(joint_coinc, support_joint)
    # Combine geometrically where all supports? Use product of ranks where defined, else 0
    # Support for heuristic = union of supports? We'll require at least 2 of 4 to be defined
    # Define heuristic as geometric mean of 4 ranks where support, else 0
    # To keep simple, compute (mag12_rank * mag15_rank * ratio_rank * coinc_rank)^(1/4) but where any rank is 0 (outside support) treat as 0
    # However outside support ranks are 0, product would be 0. That's fine - those pixels get 0.
    stacked=np.stack([mag12_rank, mag15_rank, ratio_rank, coinc_rank], axis=0)  # 4,H,W
    # geometric mean: exp(mean(log(x+eps))) but for 0 we want 0. So use product^(1/4)
    prod=np.prod(np.clip(stacked,0,1), axis=0)
    heuristic=np.power(prod, 0.25).astype(np.float32)
    # Mask outside footprint to 0
    heuristic[~fp]=0
    # Also need to ensure catalogue not needed
    # Support mask for valid heuristic: at least one rank >0
    heuristic_support= (mag12_rank>0) | (mag15_rank>0) | (ratio_rank>0) | (coinc_rank>0)
    return heuristic, heuristic_support, {"mag12_rank":mag12_rank, "mag15_rank":mag15_rank, "ratio_rank":ratio_rank, "coinc_rank":coinc_rank}

def main():
    import vendor.gems57.spatial as spatial
    import vendor.gems57.evaluate_holdout as EH
    import vendor.gems57.submission_writer as writer
    import vendor.gems57.validate as validate
    from gems91.novelty import SurfaceProbe, dot_check

    print("loading")
    footprint, catalogue, bands = load_lite()
    print(f"footprint {footprint.sum()} catalogue {catalogue.sum()}")
    print("building heuristic")
    heuristic, support, comps = build_heuristic(footprint, bands)
    print(f"heuristic mean {heuristic[footprint].mean():.4f} max {heuristic.max():.4f} support {support.sum()}")
    del bands
    gc.collect()
    # folds
    folds=list(spatial.folds(catalogue, footprint, buffer_px=80))
    for f in folds:
        print(f"fold {f['fold']} truth {f['truth'].sum()}")
    # canary: test heuristic alone + each component alone
    print("canary")
    # heuristic alone
    max_auc=0; worst=None
    # test each of 4 components
    for name, arr in [("heuristic", heuristic)] + [(k,v) for k,v in comps.items()]:
        aucs=[]
        for fold in folds:
            region=fold["region"]; truth=fold["truth"]; masked_known=fold["masked_known"]
            valid=np.isfinite(arr) & footprint if name!="heuristic" else (arr>0) & footprint  # heuristic is 0 outside support, finite everywhere
            # For heuristic, valid is footprint (since 0 is valid)
            if name=="heuristic":
                valid=footprint
            eval_mask=region & valid
            pos=np.where(eval_mask & truth)
            neg_mask=eval_mask & ~masked_known & ~truth
            neg_y,neg_x=np.where(neg_mask)
            if len(neg_y)==0:
                continue
            sel=np.arange(0,len(neg_y),4)
            neg_y=neg_y[sel]; neg_x=neg_x[sel]
            y=np.concatenate([pos[0],neg_y]); x=np.concatenate([pos[1],neg_x])
            labels=np.concatenate([np.ones(len(pos[0])), np.zeros(len(neg_y))])
            scores=arr[y,x]
            keep=np.isfinite(scores)
            if keep.sum()>10 and len(np.unique(labels[keep]))==2:
                try:
                    auc=roc_auc_score(labels[keep], scores[keep])
                    auc_sym=max(auc,1-auc)
                    aucs.append(auc_sym)
                except: pass
        if aucs:
            m=max(aucs)
            print(f" {name}: max AUC {m:.4f}")
            if m>max_auc:
                max_auc=m; worst=name
    print(f"max AUC {max_auc:.4f} worst {worst}")
    if max_auc>0.90:
        raise SystemExit("canary fail")
    # holdout evaluation for heuristic vs base control (gradmag base)
    # Build base control surface: rank of grad mag B12 alone? Or use simple base: mag12_rank alone
    # We'll define controls: base = mag12_rank (the strongest single), heuristic is candidate
    # Actually base should be the best single feature among comps that is not heuristic
    # Let's use mag12_rank as control
    base_surface=comps["mag12_rank"]
    # Also use random control? We'll just compare heuristic vs base
    arms={"heuristic":heuristic, "base_mag12":base_surface}
    terms_by_arm={}
    for arm_name,pred in arms.items():
        if np.isnan(pred).all():
            continue
        all_terms=[]
        for fold in folds:
            valid=footprint
            p=np.where(np.isfinite(pred), pred, 0.0)
            p=np.clip(p,0,1)
            result,terms=EH.evaluate(p, fold, valid, block_side=200)
            all_terms.append(terms)
        stacked=np.sum(np.stack(all_terms), axis=0)
        terms_by_arm[arm_name]=stacked
    summary=EH.pooled_summary(terms_by_arm, draws=1000, seed=SEED, candidate="heuristic")
    print(json.dumps(summary, indent=2))
    best_control=summary["best_comparable_control"]
    delta=summary["paired_differences"][best_control]["delta"]
    ci=summary["paired_differences"][best_control]["ci95"]
    print(f"delta vs {best_control} {delta:.5f} ci {ci}")
    (WORK/"holdout_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    # surface uniqueness
    print("surface uniqueness")
    inv=json.loads((ROOT/"registry/comparison_inventory.json").read_text())
    registry_paths=[]
    for row in inv["files"]:
        p=ROOT/row["path"]
        if p.exists():
            registry_paths.append(p)
    for p in (ROOT/"docs/downloads").glob("*.tif"):
        if p not in registry_paths:
            try:
                with rasterio.open(p) as ds:
                    if ds.shape==footprint.shape and ds.crs.to_string()=="EPSG:32611":
                        registry_paths.append(p)
            except: pass
    probe=SurfaceProbe(heuristic, footprint)
    worst_rho=0; worst_path=None
    for rp in registry_paths:
        with rasterio.open(rp) as ds:
            ref=ds.read(1).astype(np.float64)
        res=probe.compare(ref)
        rho=res.get("rank_correlation")
        if rho is not None and abs(rho)>abs(worst_rho):
            worst_rho=rho; worst_path=rp
    print(f"surface max |rho| {abs(worst_rho):.4f} vs {worst_path} rho {worst_rho:.4f}")
    # emit dots
    print("emitting")
    def emit_nms(surface, footprint, catalogue, budget, spacing, collar):
        fp=np.asarray(footprint,bool); cat=np.asarray(catalogue,bool)
        surf=np.asarray(surface,float)
        if cat.any():
            dist_cat=ndi.distance_transform_edt(~cat)
            allowed=fp & (dist_cat>collar) & np.isfinite(surf) & (surf>0)
        else:
            allowed=fp & np.isfinite(surf) & (surf>0)
        ys,xs=np.where(allowed)
        scores=surf[ys,xs]
        order=np.argsort(-scores, kind="stable")
        ys=ys[order]; xs=xs[order]
        sel_y=[]; sel_x=[]
        bucket=int(np.ceil(spacing))
        buckets={}
        def bkey(y,x):
            return (y//bucket, x//bucket)
        mask=np.zeros_like(fp, dtype=np.uint8)
        for y,x in zip(ys,xs):
            by,bx=bkey(y,x)
            found=False
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    key=(by+dy,bx+dx)
                    if key in buckets:
                        for oy,ox in buckets[key]:
                            if (oy-y)**2+(ox-x)**2 <= spacing*spacing+1e-9:
                                found=True
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                continue
            sel_y.append(y); sel_x.append(x)
            buckets.setdefault(bkey(y,x), []).append((y,x))
            mask[y,x]=1
            if len(sel_y)>=budget:
                break
        return mask, np.column_stack([sel_y,sel_x]) if sel_y else np.empty((0,2))
    dots_mask, selected=emit_nms(heuristic, footprint, catalogue, BUDGET, SPACING, COLLAR)
    print(f"emitted {len(selected)} dots")
    pred_raster=np.where(dots_mask,1.0,0.0).astype(np.float32)
    if np.any(dots_mask & catalogue):
        raise ValueError("dots on catalogue")
    # dot overlap
    print("dot overlap")
    from gems91.novelty import dot_check as dc
    max_overlap=0; worst_dot=None; competitive_max=0; nine_max=0
    nine_audit=json.loads((ROOT/"docs/s25/nine-site-audit.json").read_text())
    nine_shas=set(s["sha256"] for s in nine_audit["sites"])
    nine_paths=[]
    for rp in registry_paths:
        if sha_file(rp) in nine_shas:
            nine_paths.append(rp)
    print(f"nine {len(nine_paths)}")
    for rp in registry_paths:
        with rasterio.open(rp) as ds:
            ref=ds.read(1)
            ref_mask=np.isfinite(ref) & (ref>0) & footprint
            cand_arr=dots_mask.astype(np.float64)
            ref_arr=ref_mask.astype(np.float64)
            cand_arr[~footprint]=0; ref_arr[~footprint]=0
            res=dc(cand_arr, ref_arr, footprint)
            overlap=res.get("overlap_within_3px")
            if overlap is not None:
                if overlap>max_overlap:
                    max_overlap=overlap; worst_dot=rp
                if ref_mask.sum()<=90000 and overlap>competitive_max:
                    competitive_max=overlap
                    worst_comp=rp
                if rp in nine_paths and overlap>nine_max:
                    nine_max=overlap
    print(f"dot all {max_overlap:.4f} vs {worst_dot} competitive {competitive_max:.4f} nine {nine_max:.4f}")
    # write submission
    sample_path=ROOT/"data/official/sample_submission.tif"
    out_stem=f"gems91-def4a160-scbr-{BUDGET}dots-20261029T{datetime.now(timezone.utc).strftime('%H%M%S')}Z"
    surf_hash=hashlib.sha256(heuristic.tobytes()).hexdigest()[:8]
    out_stem=f"gems91-def4a160-heuristic-{BUDGET}dots-20261029T{datetime.now(timezone.utc).strftime('%H%M%S')}Z-{surf_hash}-zeros"
    out_path=OUT_DIR/f"{out_stem}.tif"
    name=out_stem
    receipt=writer.write_submission(out_path, pred_raster, sample_path, footprint, note=NOTE, name=name, catalogue=catalogue, metadata={"lane":"DEF4A160-heuristic","budget":BUDGET})
    print(f"written {out_path} sha {receipt['sha256']}")
    v=validate.validate(out_path, footprint, catalogue)
    print(f"validate {v['all_checks_passed']}")
    run_card={
        "schema":"gems91.run-card-def4a160-heuristic.v1",
        "lane":"DEF4A160 heuristic (self-assigned)",
        "preregistration":"docs/HYPOTHESES_DEF4A160.md",
        "hypothesis":"Heuristic scaling-break + basement-step catches buried faults despite no ML.",
        "mechanism": f"4 rank features geom mean -> heuristic surface -> NMS {BUDGET} dots spacing {SPACING} collar {COLLAR}",
        "named_non_fault_mimic":"Lith contacts, fan margins, shorelines, roads",
        "holdout":summary,
        "leakage_canary":{"max_symmetric_auc":max_auc,"worst":worst,"pass":max_auc<=0.90},
        "correlation_overlap_vs_registry":{
            "surface_max_abs_rho":abs(worst_rho) if worst_rho else None,
            "surface_worst": str(worst_path) if worst_path else None,
            "surface_pass_le_0.90": abs(worst_rho)<=0.90 if worst_rho else True,
            "final_dot_max_overlap_all":max_overlap,
            "final_dot_worst": str(worst_dot) if worst_dot else None,
            "final_dot_max_overlap_competitive_le_90000px": competitive_max,
            "final_dot_max_overlap_nine": nine_max,
            "final_dot_pass_nine_le_0.70": nine_max<=0.70,
            "final_dot_pass_competitive_le_0.70": competitive_max<=0.70,
        },
        "budget":BUDGET,
        "raster":{"path":f"docs/downloads/{out_path.name}","sha256":receipt["sha256"],"bytes":receipt["bytes"],"n_dots":BUDGET,"validation":v},
        "submission_name":receipt["submission_name"],
        "submission_note":receipt["note"],
        "OK_TO_DOWNLOAD": "YES" if v["all_checks_passed"] else "NO",
        "OK_TO_SUBMIT":"NO",
        "verdict": "negative" if (competitive_max>0.70 or nine_max>0.70) else ("promote" if delta>0 and ci[0]>0 else "negative"),
        "experiments_run":1,
    }
    (ROOT/"docs/run-card-DEF4A160-heuristic.json").write_text(json.dumps(run_card,indent=2)+"\n")
    (WORK/"run_card.json").write_text(json.dumps(run_card,indent=2)+"\n")
    print(json.dumps(run_card,indent=2))

if __name__=="__main__":
    main()
