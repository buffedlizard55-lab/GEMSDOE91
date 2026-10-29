#!/usr/bin/env python3
"""S26 lane: LiDAR-scarp x GeoDawn-radiometric x GeoDawn-raw HGB, hide-and-recover v3.
Lane (assigned this session): scarp morphology (lidar_scarp u8 bands 0-10) fused with
radiometric K/Th/U/TC and the 19 GeoDawn numerical bands in one HistGradientBoosting
classifier trained ONLY on fold-visible catalogue pixels; dotted emission (min spacing
2.8 px) outside a 3.05 px catalogue collar. Non-fault mimic: terrace risers / road cuts /
shorelines produce scarp+rad anomalies without faults.
Uses shared vendor/gems57 folds+evaluator and submission_writer. No private metric fork.
"""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"vendor"), str(ROOT/"scripts")]
from gems57 import evaluate_holdout as eh
from gems57 import spatial as g57
from gems57.submission_writer import write_submission

DATA = ROOT/"data"; OUT = ROOT/"docs/s26-lidarrad"; OUT.mkdir(parents=True, exist_ok=True)
BUDGET = 37654; SPACING = 2.8; COLLAR = 3.05
FEAT_NAMES = ([f"lidar_{n}" for n in ["ex_max","ex_mean","step_max","lapneg_max","lappos_max","downface_max","upface_max","cross_max","relief","coh100","strike"]]
              + [f"rad_{n}" for n in ["K","Th","U","TC"]]
              + [f"geodawn_b{i+1}" for i in range(19)])

def load_stack(footprint):
    cache = DATA/"derived/s26_stack.npy"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists():
        return np.load(cache, mmap_mode="r")
    H, W = footprint.shape
    arr = np.lib.format.open_memmap(cache, mode="w+", dtype=np.float32, shape=(34, H, W))
    with rasterio.open(DATA/"external/lidar_scarp_features_u8.tif") as d:
        for i in range(11): arr[i] = d.read(i+1).astype(np.float32)/255.0
    with rasterio.open(DATA/"external/geodawn_rad_u8.tif") as d:
        for i in range(4): arr[11+i] = d.read(i+1).astype(np.float32)/255.0
    with rasterio.open(DATA/"bridge/gems-geodawn-numerical-features.tif") as d:
        for i in range(19):
            b = d.read(i+1).astype(np.float32)
            v = b[footprint & np.isfinite(b)]
            med = float(np.median(v)); iqr = float(np.percentile(v,75)-np.percentile(v,25))
            scale = 1.4826*iqr if iqr > 0 else 1.0
            arr[15+i] = np.clip((np.nan_to_num(b, nan=med)-med)/scale, -6, 6)
    arr.flush(); del arr
    return np.load(cache, mmap_mode="r")

def dotted_select(surface, allowed, budget, spacing=SPACING, seed=0):
    """Greedy highest-first with grid-hash min spacing; returns bool mask."""
    ys, xs = np.nonzero(allowed & np.isfinite(surface))
    vals = surface[ys, xs]
    order = np.argsort(-vals, kind="stable")
    cell = spacing; grid = {}
    sel_y, sel_x = [], []
    rng = np.random.default_rng(seed)
    # deterministic tie jitter by index only (stable sort already deterministic)
    for idx in order:
        y, x = int(ys[idx]), int(xs[idx])
        key = (y//cell, x//cell)
        ok = True
        for gy in (key[0]-1, key[0], key[0]+1):
            for gx in (key[1]-1, key[1], key[1]+1):
                for (py, px) in grid.get((gy, gx), ()):
                    if (py-y)**2 + (px-x)**2 < spacing*spacing: ok=False; break
                if not ok: break
            if not ok: break
        if ok:
            grid.setdefault(key, []).append((y, x)); sel_y.append(y); sel_x.append(x)
            if len(sel_y) >= budget: break
    out = np.zeros(surface.shape, bool); out[sel_y, sel_x] = True
    return out

def main():
    t0=time.time()
    with rasterio.open(DATA/"official/sample_submission.tif") as d:
        footprint = np.isfinite(d.read(1)); profile = d.profile.copy()
    with rasterio.open(DATA/"official/existing_faults.tif") as d:
        raw = d.read(1)
    catalogue = np.isfinite(raw) & (raw>0) & footprint
    folds = list(g57.folds(catalogue, footprint, buffer_px=80))
    X = load_stack(footprint)  # (34,H,W) memmap
    H, W = footprint.shape
    # ---- canary: each feature alone, withheld truth vs sampled negatives in region&~known
    rng = np.random.default_rng(26)
    canary = []
    for fi, name in enumerate(FEAT_NAMES):
        aucs=[]
        for f in folds:
            m = f["region"] & ~f["masked_known"] & footprint
            ty, tx = np.nonzero(f["truth"] & m)
            ay, ax = np.nonzero(m & ~f["truth"])
            if len(ty)==0 or len(ay)==0: continue
            neg = rng.choice(len(ay), size=min(len(ay), max(2000, 3*len(ty))), replace=False)
            vals = np.concatenate([np.asarray(X[fi, ty, tx], float), np.asarray(X[fi, ay[neg], ax[neg]], float)])
            y = np.r_[np.ones(len(ty)), np.zeros(len(neg))]
            if np.nanstd(vals) < 1e-12: continue
            a = roc_auc_score(y, np.nan_to_num(vals)); aucs.append(max(a, 1-a))
        canary.append({"feature": name, "max_symmetric_auc": float(np.mean(aucs)) if aucs else None})
    max_auc = max(c["max_symmetric_auc"] for c in canary if c["max_symmetric_auc"] is not None)
    # ---- OOF training / prediction per fold (chunked rows)
    oof = np.zeros((H, W), np.float32)
    for f in folds:
        pos_y, pos_x = np.nonzero(f["train"] & f["visible"])
        # negatives: train-domain non-catalogue, sampled 4x positives
        neg_pool_y, neg_pool_x = np.nonzero(f["train"] & ~f["masked_known"])
        n_neg = min(len(neg_pool_y), 4*len(pos_y))
        sel = rng.choice(len(neg_pool_y), size=n_neg, replace=False)
        ty = np.r_[pos_y, neg_pool_y[sel]]; tx = np.r_[pos_x, neg_pool_x[sel]]
        ytr = np.r_[np.ones(len(pos_y), int), np.zeros(n_neg, int)]
        Xtr = np.stack([np.asarray(X[i, ty, tx], float) for i in range(X.shape[0])], 1)
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                                             min_samples_leaf=40, l2_regularization=1.0, random_state=2600+int(f["fold"]))
        clf.fit(np.nan_to_num(Xtr), ytr)
        ry, rx = np.nonzero(f["region"] & footprint)
        # chunk predict
        preds = np.empty(len(ry), np.float32)
        for s in range(0, len(ry), 200000):
            e = min(s+200000, len(ry))
            Xc = np.stack([np.asarray(X[i, ry[s:e], rx[s:e]], float) for i in range(X.shape[0])], 1)
            preds[s:e] = clf.predict_proba(np.nan_to_num(Xc))[:,1]
        oof[ry, rx] = preds
        print(f"fold {f['fold']}: pos={len(pos_y)} neg={n_neg} done {time.time()-t0:.0f}s", flush=True)
    np.save(OUT/"oof_surface.npy", oof)
    # ---- holdout emission: per fold, mask masked_known dilated collar, dotted, pooled budget by quadrant share
    dist_cat = ndi.distance_transform_edt(~catalogue)
    terms = {}; per_fold=[]
    # candidate: per-fold dotted using that fold's visible-only collar (use masked_known)
    cand_terms = None
    for f in folds:
        dist_vis = ndi.distance_transform_edt(~f["masked_known"])
        allowed = f["region"] & footprint & (dist_vis > COLLAR)
        dots = dotted_select(oof, allowed, BUDGET//4)
        pred = dots.astype(np.float64)
        res, trm = eh.evaluate(pred, f, footprint)
        cand_terms = trm if cand_terms is None else cand_terms + trm
        per_fold.append({"fold": int(f["fold"]), "dti": float(res["score"] if "score" in res else eh.from_terms(trm.sum(axis=0))), "n_dots": int(dots.sum())})
        print(per_fold[-1], flush=True)
    # controls: R0 static raster and random under same folds
    with rasterio.open(DATA/"registry/GEMSDOE32__h33-2-b2-zeros.tif") as d: r0 = (d.read(1)>0)
    terms_by = {"S26_candidate": cand_terms}
    for name, dots_fn in [("R0_static_GEMSDOE32", lambda f: r0), ]:
        tr = None
        for f in folds:
            res, trm = eh.evaluate(dots_fn(f).astype(np.float64), f, footprint)
            tr = trm if tr is None else tr + trm
        terms_by[name]=tr
    rt = None
    for f in folds:
        allowed = f["region"] & footprint & (ndi.distance_transform_edt(~f["masked_known"]) > COLLAR)
        ay, ax = np.nonzero(allowed); sel = rng.choice(len(ay), size=min(BUDGET//4, len(ay)), replace=False)
        dmask = np.zeros((H,W), bool); dmask[ay[sel], ax[sel]]=True
        res, trm = eh.evaluate(dmask.astype(np.float64), f, footprint)
        rt = trm if rt is None else rt + trm
    terms_by["random_equal_budget"]=rt
    # pooled_summary requires aligned terms dict candidate first
    summary = eh.pooled_summary(terms_by, candidate="S26_candidate")
    # surface rank corr vs R0 surface (binary) on sampled footprint pixels
    sy, sx = np.nonzero(footprint); sidx = rng.choice(len(sy), 200000, replace=False)
    from scipy.stats import spearmanr
    surf_rho = float(spearmanr(oof[sy[sidx], sx[sidx]], r0[sy[sidx], sx[sidx]]).statistic)
    result = {"lane":"S26 lidar-scarp x radiometric x GeoDawn-raw HGB, dotted 2.8px, 3.05px collar",
              "evaluator_version": eh.VERSION, "n_withheld_positives": int(sum(int(f['truth'].sum()) for f in folds)),
              "canary_max_symmetric_auc": max_auc, "canary_pass_le_0.90": bool(max_auc<=0.90), "canary": canary,
              "per_fold": per_fold, "pooled": summary, "surface_spearman_vs_R0": surf_rho,
              "elapsed_s": time.time()-t0}
    (OUT/"holdout.json").write_text(json.dumps(result, indent=1, default=float))
    print(json.dumps({"holdout": summary["scores"], "canary_max": max_auc, "surf_rho_vs_R0": surf_rho}, indent=1, default=float))
    # ---- final emission on full footprint using model retrained on all visible catalogue
    pos_y, pos_x = np.nonzero(catalogue)
    neg_pool_y, neg_pool_x = np.nonzero(footprint & ~catalogue)
    sel = rng.choice(len(neg_pool_y), size=min(len(neg_pool_y), 4*len(pos_y)), replace=False)
    ty = np.r_[pos_y, neg_pool_y[sel]]; tx = np.r_[pos_x, neg_pool_x[sel]]
    ytr = np.r_[np.ones(len(pos_y), int), np.zeros(len(sel), int)]
    Xtr = np.stack([np.asarray(X[i, ty, tx], float) for i in range(X.shape[0])], 1)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0, random_state=2699)
    clf.fit(np.nan_to_num(Xtr), ytr)
    full = np.zeros((H,W), np.float32)
    fy, fx = np.nonzero(footprint)
    for s in range(0, len(fy), 200000):
        e=min(s+200000, len(fy)); Xc=np.stack([np.asarray(X[i, fy[s:e], fx[s:e]], float) for i in range(X.shape[0])],1)
        full[fy[s:e], fx[s:e]] = clf.predict_proba(np.nan_to_num(Xc))[:,1]
    np.save(OUT/"full_surface.npy", full)
    allowed = footprint & (dist_cat > COLLAR)
    dots = dotted_select(full, allowed, BUDGET)
    name = f"gems91-s26-lidarrad-{int(dots.sum())}dots-20261029"
    arr = np.where(footprint, dots.astype(np.float32), 0.0).astype(np.float32)
    sha = hashlib.sha256(arr.tobytes()).hexdigest()[:10]
    fname = f"{name}-{sha}-zeros.tif"
    write_submission(ROOT/"docs/downloads"/fname, arr, DATA/"official/sample_submission.tif", footprint,
                     note="S26 lidar-scarp x radiometric HGB dotted2.8 collar3.05 37654d", name=fname)
    # uniqueness vs restored registry rasters
    uniq={}
    for p in sorted((DATA/"registry").glob("*.tif")):
        with rasterio.open(p) as d: other=(d.read(1)>0)
        oy, ox = np.nonzero(dots)
        if len(oy):
            # fraction within 3px via distance transform of other
            dist_o = ndi.distance_transform_edt(~other)
            uniq[p.name]=float((dist_o[oy,ox]<=3.0).mean())
    meta={"file":fname, "dots":int(dots.sum()), "sha256_file": hashlib.sha256((ROOT/"docs/downloads"/fname).read_bytes()).hexdigest(),
          "array_sha256": hashlib.sha256(arr.tobytes()).hexdigest(), "overlap3px_vs_registry": uniq,
          "max_overlap3px": max(uniq.values()) if uniq else None,
          "surface_spearman_vs_R0_full": float(spearmanr(full[sy[sidx],sx[sidx]], r0[sy[sidx],sx[sidx]]).statistic)}
    (OUT/"final.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta, indent=1))

if __name__ == "__main__":
    main()
