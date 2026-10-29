#!/usr/bin/env python3
"""
DEF4A160-SCBR LITE: memory-efficient version, budget 20000.
Uses 12 features total to stay within 3.8GB.
"""
import os
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")
import hashlib, json, time, gc
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "data_manifest.json"
OUT_DIR = ROOT / "docs" / "downloads"
WORK = ROOT / "work" / "def4a160_lite"
WORK.mkdir(parents=True, exist_ok=True)

BUDGET=20000
SPACING_PX=3.5
COLLAR_PX=5.0
BUFFER_PX=80
NEG_PER_POS=4
SEED=20261029
NOTE="DEF4A160-SCBR scaling-break+basement-strain lite OOF 20k dots; see run card"
EXTREME=1e30

def sha_file(p:Path)->str:
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

def masked_local_var(field, valid, window, min_valid_frac=0.8):
    x=np.where(valid, np.asarray(field, np.float64), 0.0)
    m=valid.astype(np.float64)
    count=_masked_uniform_sum(m, window)
    s1=_masked_uniform_sum(x, window)
    s2=_masked_uniform_sum(x*x, window)
    safe=count>0
    mean=np.divide(s1,count,out=np.zeros_like(count),where=safe)
    e2=np.divide(s2,count,out=np.zeros_like(count),where=safe)
    var=np.clip(e2-mean*mean,0,None)
    support=safe & (count>=min_valid_frac*float(window*window)) & (var>1e-12)
    return mean,var,support

def _sample_offset(field, uy, ux, offset):
    h,w=field.shape
    yy,xx=np.indices((h,w), dtype=np.float64)
    coords=[yy+offset*uy, xx+offset*ux]
    return ndi.map_coordinates(field, coords, order=1, mode="nearest")

def load_inputs_lite():
    man=json.loads(MANIFEST.read_text())
    rows={r["id"]:r for r in man["files"]}
    def load_tif(id):
        row=rows[id]
        p=ROOT/"data"/row["local_subpath"]
        with rasterio.open(p) as ds:
            arr=ds.read(1)
            shape=(ds.height, ds.width)
        return arr
    sample_arr=load_tif("sample_submission")
    faults_arr=load_tif("existing_faults")
    trow=rows["training_features"]
    tpath=ROOT/"data"/trow["local_subpath"]
    # Load only needed bands: indices 0,1,3,6,11,12,13,14,17,18 (B01,B02,B04,B07,B12,B13,B14,B15,B18,B19)
    needed={0:"B01",1:"B02",3:"B04",6:"B07",11:"B12",12:"B13",13:"B14",14:"B15",17:"B18",18:"B19"}
    bands={}
    with rasterio.open(tpath) as ds:
        for idx,name in needed.items():
            bands[name]=ds.read(idx+1)
    footprint=np.isfinite(sample_arr)
    catalogue=(faults_arr>0) & footprint
    return footprint, catalogue, bands

def build_features_lite(footprint, bands):
    fp=np.asarray(footprint,bool)
    B12=bands["B12"]; B19=bands["B19"]; B13=bands["B13"]; B15=bands["B15"]
    B02=bands["B02"]; B14=bands["B14"]; B04=bands["B04"]; B07=bands["B07"]
    v12=valid_mask(B12,fp); v19=valid_mask(B19,fp); v13=valid_mask(B13,fp); v15=valid_mask(B15,fp)
    v02=valid_mask(B02,fp); v14=valid_mask(B14,fp); v04=valid_mask(B04,fp); v07=valid_mask(B07,fp)
    features={}
    # 4 grad mags as base
    for name, arr, vm in [("b02",B02,v02),("b12",B12,v12),("b13",B13,v13),("b14",B14,v14)]:
        smooth=_masked_blur(arr, vm, 2.0)
        gy,gx=np.gradient(smooth)
        gmag=np.hypot(gy,gx)
        support=ndi.distance_transform_edt(vm)>3
        out=np.where(support, gmag, np.nan).astype(np.float32)
        features[f"gradmag_{name}"]=out
        del smooth, gy,gx,gmag
    gc.collect()
    # scaling-break: 4 features (ratio + contrast for B12 and B19)
    for bname, barr, vm in [("b12",B12,v12),("b19",B19,v19)]:
        _,var5,sup5=masked_local_var(barr, vm, 7)
        _,var15,sup15=masked_local_var(barr, vm, 15)
        joint_sup=sup5 & sup15 & (var5>1e-9)
        ratio=np.divide(var15, var5, out=np.zeros_like(var15), where=joint_sup)
        ratio=np.clip(ratio,0,10)
        smooth=_masked_blur(barr, vm, 3.0)
        gy,gx=np.gradient(smooth)
        mag=np.hypot(gy,gx)
        has=vm & (mag>0)
        uy=np.divide(gy,mag,out=np.zeros_like(mag),where=has)
        ux=np.divide(gx,mag,out=np.zeros_like(mag),where=has)
        r_plus=_sample_offset(ratio, uy,ux,7.0)
        r_minus=_sample_offset(ratio, uy,ux,-7.0)
        sup_plus=_sample_offset(joint_sup.astype(float), uy,ux,7.0)>0.5
        sup_minus=_sample_offset(joint_sup.astype(float), uy,ux,-7.0)>0.5
        has_plus=_sample_offset(has.astype(float), uy,ux,7.0)>0.5
        has_minus=_sample_offset(has.astype(float), uy,ux,-7.0)>0.5
        contrast=np.abs(r_plus-r_minus)
        support_sb=joint_sup & sup_plus & sup_minus & has_plus & has_minus & has & (ndi.distance_transform_edt(vm)>20)
        features[f"scbr_ratio_{bname}"]=np.where(joint_sup, np.log1p(ratio), np.nan).astype(np.float32)
        features[f"scbr_contrast_{bname}"]=np.where(support_sb, np.log1p(contrast), np.nan).astype(np.float32)
        del var5,var15,sup5,sup15,ratio,smooth,gy,gx,mag,has,uy,ux,r_plus,r_minus,sup_plus,sup_minus,has_plus,has_minus,contrast
        gc.collect()
    # basement-step coincidence: 4 features
    # Compute grad mags for B15, B13, B04, B07 already partly done, but need magnitude maps
    grads={}
    for bname, barr, vm in [("b15",B15,v15),("b13",B13,v13),("b04",B04,v04),("b07",B07,v07)]:
        smooth=_masked_blur(barr, vm, 2.0)
        gy,gx=np.gradient(smooth)
        mag=np.hypot(gy,gx)
        support=ndi.distance_transform_edt(vm)>3
        grads[bname]= (mag, support, gy,gx)
        features[f"gradmag2_{bname}"]=np.where(support, mag, np.nan).astype(np.float32)
        # keep gy,gx for later? We'll recompute
    # Azimuth agreement B15 vs B04
    sm15=_masked_blur(B15, v15,2.0)
    gy15,gx15=np.gradient(sm15)
    mag15=np.hypot(gy15,gx15); has15=v15 & (mag15>0)
    sm04=_masked_blur(B04, v04,2.0)
    gy04,gx04=np.gradient(sm04)
    mag04=np.hypot(gy04,gx04); has04=v04 & (mag04>0)
    az15=np.arctan2(gx15,gy15); az04=np.arctan2(gx04,gy04)
    diff=np.abs(az15-az04); diff=np.minimum(diff,2*np.pi-diff)
    diff_axial=np.minimum(diff, np.pi-diff)
    agree=1.0-np.clip(diff_axial/(np.pi/8),0,1)
    support_joint=has15 & has04 & (ndi.distance_transform_edt(v15 & v04)>5)
    def robust01(arr,vm):
        vals=arr[vm & np.isfinite(arr)]
        if vals.size<100:
            return np.zeros_like(arr,dtype=np.float32)
        lo,hi=np.percentile(vals,[2,98])
        norm=np.clip((arr-lo)/(hi-lo+1e-9),0,1)
        return norm.astype(np.float32)
    mag15_n=robust01(mag15, support_joint)
    mag04_n=robust01(mag04, support_joint)
    # B13 vs B15 agreement
    sm13=_masked_blur(B13, v13,2.0)
    gy13,gx13=np.gradient(sm13)
    az13=np.arctan2(gx13,gy13)
    diff13_15=np.abs(az13-az15); diff13_15=np.minimum(diff13_15,2*np.pi-diff13_15)
    diff13_15=np.minimum(diff13_15, np.pi-diff13_15)
    agree13_15=1.0-np.clip(diff13_15/(np.pi/8),0,1)
    mag13=np.hypot(gy13,gx13); mag13_n=robust01(mag13, support_joint)
    joint_b15_b04=np.where(support_joint, np.sqrt(np.clip(mag15_n*mag04_n,0,1))*agree, np.nan).astype(np.float32)
    joint_b15_b13=np.where(support_joint, np.sqrt(np.clip(mag15_n*mag13_n,0,1))*agree13_15, np.nan).astype(np.float32)
    features["basement_coinc_b15_b04"]=joint_b15_b04
    features["basement_coinc_b15_b13"]=joint_b15_b13
    return features

def main():
    import vendor.gems57.spatial as spatial
    import vendor.gems57.evaluate_holdout as EH
    import vendor.gems57.submission_writer as writer
    import vendor.gems57.validate as validate
    from gems91.novelty import SurfaceProbe, dot_check
    from gems91.capacity import capacity_bound

    print("[LITE] verifying pinned...")
    for row in json.loads(MANIFEST.read_text())["files"]:
        if row["id"] in {"sample_submission","existing_faults","training_features"}:
            p=ROOT/"data"/row["local_subpath"]
            if not p.is_file() or sha_file(p)!=row["sha256"]:
                raise SystemExit(f"pinned drift {row['id']}")
    print("[LITE] loading inputs lite...")
    footprint, catalogue, bands = load_inputs_lite()
    print(f"footprint {footprint.sum()} catalogue {catalogue.sum()} bands {list(bands.keys())}")
    print("[LITE] building features lite...")
    features=build_features_lite(footprint,bands)
    # free bands
    del bands
    gc.collect()
    print(f"features {len(features)}")
    for k,v in features.items():
        print(f" {k}: finite {(np.isfinite(v)&footprint).sum()} mean {np.nanmean(v[footprint]):.3f}")
    # folds
    print("[LITE] folds...")
    folds=list(spatial.folds(catalogue, footprint, buffer_px=80))
    for f in folds:
        print(f" fold {f['fold']} truth {f['truth'].sum()} train {f['train'].sum()}")
    # canary
    print("[LITE] canary...")
    max_auc=0; worst=None
    for fname, arr in features.items():
        aucs=[]
        for fold in folds:
            region=fold["region"]; truth=fold["truth"]; masked_known=fold["masked_known"]
            valid=np.isfinite(arr)
            eval_mask=region & valid
            pos_idx=np.where(eval_mask & truth)
            neg_mask=eval_mask & ~masked_known & ~truth
            neg_y,neg_x=np.where(neg_mask)
            if len(neg_y)>0:
                sel=np.arange(0,len(neg_y),4)
                neg_y=neg_y[sel]; neg_x=neg_x[sel]
                y=np.concatenate([pos_idx[0],neg_y]); x=np.concatenate([pos_idx[1],neg_x])
                labels=np.concatenate([np.ones(len(pos_idx[0])), np.zeros(len(neg_y))])
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
            if m>max_auc:
                max_auc=m; worst=fname
    print(f"max AUC {max_auc:.4f} worst {worst}")
    if max_auc>0.90:
        raise SystemExit("canary fail")
    # prepare feature stacking for training but avoid huge flat
    names=sorted(features.keys())
    base_names=[n for n in names if n.startswith("gradmag_")]
    new_names=[n for n in names if n.startswith("scbr_") or n.startswith("basement_") or n.startswith("gradmag2_")]
    print(f"base {len(base_names)} new {len(new_names)} total {len(names)}")
    H,W=footprint.shape
    # Build flat as list of arrays for indexing? We'll keep dict and index per training sample via lookup
    # For training we need to gather X_train matrices: for each fold, for each arm, we need to sample positives and negatives and fetch feature vectors
    # Instead of flat, we can fetch via stacking per sample
    def get_X(y_idx, x_idx, idxs):
        # idxs = list of feature indices in names order
        cols=[]
        for i in idxs:
            fname=names[i]
            arr=features[fname]
            cols.append(arr[y_idx, x_idx])
        return np.column_stack(cols)
    # Map names to idx
    name_to_idx={n:i for i,n in enumerate(names)}
    base_idxs=[name_to_idx[n] for n in base_names]
    new_idxs=[name_to_idx[n] for n in new_names]
    full_idxs=list(range(len(names)))
    rng=np.random.default_rng(SEED)
    oof_full=np.full((H,W), np.nan, dtype=np.float64)
    oof_base=np.full((H,W), np.nan, dtype=np.float64)
    oof_new=np.full((H,W), np.nan, dtype=np.float64)
    for fold in folds:
        fid=fold["fold"]
        train_mask=fold["train"]; region_mask=fold["region"]
        # For each arm, define valid and pos
        for tag, idxs, oof_arr in [("base",base_idxs,oof_base),("new",new_idxs,oof_new),("full",full_idxs,oof_full)]:
            # valid where any feature in group finite
            # need to compute valid for this group: any finite among those features within train
            # Build valid mask on fly: any finite
            valid=np.zeros((H,W),bool)
            for i in idxs:
                fname=names[i]
                valid |= np.isfinite(features[fname])
            valid &= train_mask
            pos_mask=valid & catalogue
            n_pos=int(pos_mask.sum())
            if n_pos<20:
                print(f"fold {fid} {tag} too few pos {n_pos}")
                continue
            neg_candidates=np.where(valid & ~catalogue)
            n_neg_needed=n_pos*NEG_PER_POS
            if len(neg_candidates[0])<n_neg_needed:
                sel=rng.choice(len(neg_candidates[0]), size=n_neg_needed, replace=True)
            else:
                sel=rng.choice(len(neg_candidates[0]), size=n_neg_needed, replace=False)
            neg_y=neg_candidates[0][sel]; neg_x=neg_candidates[1][sel]
            pos_y,pos_x=np.where(pos_mask)
            train_y=np.concatenate([pos_y, neg_y]); train_x=np.concatenate([pos_x, neg_x])
            train_labels=np.concatenate([np.ones(len(pos_y)), np.zeros(len(neg_y))])
            X_train=get_X(train_y, train_x, idxs)
            # check NaN handling: HGB handles NaN, but we should ensure not all NaN row
            clf=HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0, early_stopping=False, random_state=SEED+fid)
            clf.fit(X_train, train_labels)
            region_y, region_x=np.where(region_mask)
            X_region=get_X(region_y, region_x, idxs)
            probs=clf.predict_proba(X_region)[:,1]
            oof_arr[region_y, region_x]=probs
            print(f"fold {fid} {tag} train pos {n_pos} neg {len(neg_y)} oof mean {np.nanmean(probs):.3f}")
            del X_train, X_region, clf
            gc.collect()
    # Evaluate
    print("[LITE] evaluating HOLDOUT...")
    arms={"full":oof_full,"base":oof_base,"new":oof_new}
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
    summary=EH.pooled_summary(terms_by_arm, draws=1000, seed=SEED, candidate="full")
    print(json.dumps(summary, indent=2))
    best_control=summary["best_comparable_control"]
    delta=summary["paired_differences"][best_control]["delta"]
    ci=summary["paired_differences"][best_control]["ci95"]
    print(f"delta vs {best_control} {delta:.5f} ci {ci}")
    (WORK/"holdout_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    # Final full model
    print("[LITE] training final full model...")
    def train_final(idxs):
        valid=np.zeros((H,W),bool)
        for i in idxs:
            fname=names[i]
            valid |= np.isfinite(features[fname])
        valid &= footprint
        pos_mask=valid & catalogue
        n_pos=int(pos_mask.sum())
        print(f" final valid {valid.sum()} pos {n_pos}")
        neg_candidates=np.where(valid & ~catalogue)
        n_neg_needed=n_pos*NEG_PER_POS
        sel=rng.choice(len(neg_candidates[0]), size=n_neg_needed, replace=False if len(neg_candidates[0])>=n_neg_needed else True)
        neg_y=neg_candidates[0][sel]; neg_x=neg_candidates[1][sel]
        pos_y,pos_x=np.where(pos_mask)
        train_y=np.concatenate([pos_y,neg_y]); train_x=np.concatenate([pos_x,neg_x])
        train_labels=np.concatenate([np.ones(len(pos_y)), np.zeros(len(neg_y))])
        X_train=get_X(train_y,train_x,idxs)
        clf=HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0, early_stopping=False, random_state=SEED)
        clf.fit(X_train, train_labels)
        # predict full footprint where valid
        pred=np.full((H,W), np.nan, dtype=np.float64)
        valid_y,valid_x=np.where(valid)
        batch=400000
        for i in range(0,len(valid_y),batch):
            batch_y=valid_y[i:i+batch]; batch_x=valid_x[i:i+batch]
            Xb=get_X(batch_y,batch_x,idxs)
            probs=clf.predict_proba(Xb)[:,1]
            pred[batch_y,batch_x]=probs
            del Xb
        pred_filled=np.where(np.isfinite(pred)&footprint, pred, 0.0)
        pred_filled=np.clip(pred_filled,0,1)
        return pred_filled
    final_full=train_final(full_idxs)
    final_base=train_final(base_idxs)
    # Surface uniqueness
    print("[LITE] surface uniqueness...")
    from gems91.novelty import SurfaceProbe
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
    probe=SurfaceProbe(final_full, footprint)
    worst_rho=0; worst_path=None
    for rp in registry_paths:
        with rasterio.open(rp) as ds:
            ref=ds.read(1).astype(np.float64)
        res=probe.compare(ref)
        rho=res.get("rank_correlation")
        if rho is not None and abs(rho)>abs(worst_rho):
            worst_rho=rho; worst_path=rp
    print(f"surface max |rho| {abs(worst_rho):.4f} vs {worst_path}")
    # Emit dots
    print("[LITE] emitting...")
    # use simple NMS via grid hashing to stay fast
    def emit_nms(surface, footprint, catalogue, budget, spacing, collar):
        fp=np.asarray(footprint,bool); cat=np.asarray(catalogue,bool)
        surf=np.asarray(surface,float)
        if cat.any():
            dist_cat=ndi.distance_transform_edt(~cat)
            allowed=fp & (dist_cat>collar) & np.isfinite(surf)
        else:
            allowed=fp & np.isfinite(surf)
        ys,xs=np.where(allowed)
        scores=surf[ys,xs]
        order=np.argsort(-scores, kind="stable")
        ys=ys[order]; xs=xs[order]
        sel_y=[]; sel_x=[]
        # grid bucket for fast spacing check: bucket size = spacing
        bucket=int(np.ceil(spacing))
        # Use dict of buckets
        buckets={}
        def bucket_key(y,x):
            return (y//bucket, x//bucket)
        selected_mask=np.zeros_like(fp, dtype=np.uint8)
        for y,x in zip(ys,xs):
            # check neighboring buckets
            by,bx=bucket_key(y,x)
            found=False
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    key=(by+dy,bx+dx)
                    if key in buckets:
                        for (oy,ox) in buckets[key]:
                            if (oy-y)**2 + (ox-x)**2 <= spacing*spacing+1e-9:
                                found=True
                                break
                        if found:
                            break
                if found:
                    break
            if found:
                continue
            # select
            sel_y.append(y); sel_x.append(x)
            key=bucket_key(y,x)
            buckets.setdefault(key, []).append((y,x))
            selected_mask[y,x]=1
            if len(sel_y)>=budget:
                break
        return selected_mask, np.column_stack([sel_y,sel_x]) if sel_y else np.empty((0,2))

    dots_mask, selected=emit_nms(final_full, footprint, catalogue, BUDGET, SPACING_PX, COLLAR_PX)
    print(f"emitted {len(selected)} dots")
    pred_raster=np.where(dots_mask,1.0,0.0).astype(np.float32)
    if np.any(dots_mask & catalogue):
        raise ValueError("dots on catalogue")
    # Dot overlap
    print("[LITE] dot overlap...")
    from gems91.novelty import dot_check as dc
    max_overlap=0; worst_dot=None; competitive_max=0; nine_max=0
    nine_audit=json.loads((ROOT/"docs/s25/nine-site-audit.json").read_text())
    nine_shas=set(s["sha256"] for s in nine_audit["sites"])
    nine_paths=[]
    for rp in registry_paths:
        if sha_file(rp) in nine_shas:
            nine_paths.append(rp)
    print(f"nine paths {len(nine_paths)}")
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
    print(f"dot max all {max_overlap:.4f} vs {worst_dot} competitive {competitive_max:.4f} nine {nine_max:.4f}")
    # Write submission
    sample_path=ROOT/"data/official/sample_submission.tif"
    out_stem=f"gems91-def4a160-scbr-{BUDGET}dots-20261029T{datetime.now(timezone.utc).strftime('%H%M%S')}Z"
    surf_hash=hashlib.sha256(final_full.tobytes()).hexdigest()[:8]
    out_stem=f"gems91-def4a160-scbr-{BUDGET}dots-20261029T{datetime.now(timezone.utc).strftime('%H%M%S')}Z-{surf_hash}-zeros"
    out_path=OUT_DIR/f"{out_stem}.tif"
    name=out_stem
    # Use writer
    receipt=writer.write_submission(out_path, pred_raster, sample_path, footprint, note=NOTE, name=name, catalogue=catalogue, metadata={"lane":"DEF4A160-SCBR-lite","budget":BUDGET})
    print(f"written {out_path} sha {receipt['sha256']}")
    v=validate.validate(out_path, footprint, catalogue)
    print(f"validate {v['all_checks_passed']}")
    run_card={
        "schema":"gems91.run-card-def4a160.v1",
        "lane":"DEF4A160-SCBR-lite (self-assigned)",
        "preregistration":"docs/HYPOTHESES_DEF4A160.md",
        "hypothesis":"Scaling-break + basement-strain coincidence catches buried faults under alluvium where catalogue is blind.",
        "mechanism": f"{len(names)} features ({len(base_names)} base + {len(new_names)} new) -> HGB OOF v3 -> final NMS {BUDGET} dots spacing {SPACING_PX} collar {COLLAR_PX}",
        "named_non_fault_mimic":"Lithologic contacts, fan margins, shorelines, roads, subsidence",
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
        "OK_TO_SUBMIT": "NO",
        "verdict": "negative" if (competitive_max>0.70 or nine_max>0.70) else ("promote" if delta>0 and ci[0]>0 else "negative"),
        "experiments_run":1,
    }
    (ROOT/"docs/run-card-DEF4A160.json").write_text(json.dumps(run_card,indent=2)+"\n")
    (WORK/"run_card.json").write_text(json.dumps(run_card,indent=2)+"\n")
    print(json.dumps(run_card,indent=2))

if __name__=="__main__":
    main()
