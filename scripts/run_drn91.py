#!/usr/bin/env python3
"""DRN91: drainage-deflection/knickpoint features + cross-fitted HGB, shared evaluator."""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "vendor")]
from gems57 import grid as G, spatial, evaluate_holdout as EH  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems91.dd_vtc_pu import submodular_dti_emit  # noqa: E402
import rasterio  # noqa: E402

NODATA = -3.4028234663852886e+38
rng_global = np.random.default_rng(91)

def band_names():
    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        return [ds.tags(i + 1)["band_name"] for i in range(ds.count)]

def load_band(i):
    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        x = ds.read(i + 1).astype(np.float32)
    x[x <= NODATA / 2] = np.nan
    return x

def robust(x, fp):
    v = x[fp & np.isfinite(x)]
    lo, hi = np.nanpercentile(v, [1, 99])
    return np.clip((x - lo) / max(hi - lo, 1e-9), -2, 3).astype(np.float32)

def drainage_features(elev, fp):
    """D8 routing on smoothed detrended elevation. Returns 5 float32 features."""
    z = np.where(fp, elev, np.nan)
    med = np.nanmedian(z[fp])
    zf = ndi.uniform_filter(np.where(np.isfinite(z), z, med), size=5)
    zf = ndi.gaussian_filter(zf, 1.0)
    H, W = zf.shape
    # D8 receiver: steepest descent among 8 neighbours (vectorised argmin of drop)
    best_drop = np.zeros((H, W), np.float32); recv = np.full((H, W), -1, np.int32)
    flat = np.arange(H * W).reshape(H, W)
    for dy, dx, dist in [(-1,0,1),(1,0,1),(0,-1,1),(0,1,1),(-1,-1,1.414),(-1,1,1.414),(1,-1,1.414),(1,1,1.414)]:
        nb = np.roll(np.roll(zf, dy, 0), dx, 1)
        drop = (zf - nb) / dist
        upd = drop > best_drop
        # zero out wrapped edges crudely via footprint of neighbour
        upd &= fp
        best_drop = np.where(upd, drop, best_drop)
        recv = np.where(upd, np.roll(np.roll(flat, dy, 0), dx, 1), recv)
    order = np.argsort(zf.ravel(), kind="stable")[::-1]  # high -> low
    acc = np.ones(H * W, np.float64)
    recv_f = recv.ravel(); valid = recv_f >= 0
    # accumulate in descending order: each cell pushes its acc to its receiver
    acc_r = acc.copy()
    for idx in order:
        r = recv_f[idx]
        if r >= 0:
            acc_r[r] += acc_r[idx]
    acc2d = acc_r.reshape(H, W).astype(np.float32)
    logacc = np.log1p(acc2d)
    channel = (acc2d > 300) & fp
    dist_chan = ndi.distance_transform_edt(~channel).astype(np.float32)
    # deflection: angle between inflow direction and outflow direction approximated
    # by gradient-direction change along flow: use structure of gradient azimuth
    gy, gx = np.gradient(zf)
    az = np.arctan2(gy, gx)
    az_s = ndi.uniform_filter(np.cos(2 * az), 5) + 1j * ndi.uniform_filter(np.sin(2 * az), 5)
    deflect = (1 - np.abs(az_s)).astype(np.float32)  # high where azimuth incoherent (deflection/knick zone)
    # knickpoint: downstream slope break = local slope minus 9px-smoothed slope, on channels weighted
    slope = np.hypot(gx, gy).astype(np.float32)
    knick = (slope - ndi.uniform_filter(slope, 9)) * np.clip(logacc / np.log1p(300.0), 0, 1)
    converg = (-ndi.laplace(zf)).astype(np.float32)
    return [logacc, dist_chan, deflect, knick.astype(np.float32), converg], \
        ["drn_logacc", "drn_dist_channel", "drn_deflection", "drn_knickpoint", "drn_convergence"]

GRAD_BANDS = {1, 2, 5, 11, 12, 17, 18}  # rtp,tmi_hg,tc,det_elev,iso_grav,tmi_hg? indices 0-based key fields

def build_features(g):
    names = band_names()
    fp = g.footprint
    feats, fnames = [], []
    # drainage FIRST (peak-memory isolation), outputs stored float16
    b12r = robust(load_band(11), fp)
    drn, dn = drainage_features(b12r, fp); del b12r
    drn16 = [(robust(x, fp) if n != "drn_dist_channel" else np.clip(x / 20.0, 0, 3)).astype(np.float16) for x, n in zip(drn, dn)]
    del drn
    b12 = None
    for i, n in enumerate(names):
        x = robust(load_band(i), fp)
        feats.append(x.astype(np.float16)); fnames.append(n)
        if i in GRAD_BANDS:
            gy = ndi.sobel(x, 0)
            feats.append(np.hypot(ndi.sobel(x, 1), gy).astype(np.float16)); fnames.append(n + "_grad")
            del gy
        del x
    feats.extend(drn16); fnames.extend(dn)
    X = np.stack(feats).astype(np.float16); del feats, drn16
    X[:, ~fp] = 0
    return np.nan_to_num(X, nan=0), fnames

def sample_xy(X, domain, cat, seed, neg_ratio=3):
    ys, xs = np.nonzero(domain & cat); yn, xn = np.nonzero(domain & ~cat)
    r = np.random.default_rng(seed)
    nn = min(len(yn), len(ys) * neg_ratio)
    sel = r.choice(len(yn), nn, replace=False)
    idx = (np.r_[ys, yn[sel]], np.r_[xs, xn[sel]])
    y = np.r_[np.ones(len(ys)), np.zeros(nn)].astype(int)
    return np.asarray(X[:, idx[0], idx[1]].T, dtype=np.float32), y

def canaries(X, fnames, folds_list, g):
    out = {}
    # pooled sample: positives = withheld truth, negatives = region non-truth
    for fi, n in enumerate(fnames):
        aucs = []
        for f in folds_list:
            m = f["region"] & g.footprint
            ys, xs = np.nonzero(m & f["truth"]); yn, xn = np.nonzero(m & ~f["truth"] & ~f["visible"])
            if len(ys) < 50: continue
            r = np.random.default_rng(7)
            sel = r.choice(len(yn), min(len(yn), len(ys) * 3), replace=False)
            v = np.r_[X[fi, ys, xs], X[fi, yn[sel], xn[sel]]]
            if np.ptp(v) == 0: continue
            lab = np.r_[np.ones(len(ys)), np.zeros(len(sel))]
            a = roc_auc_score(lab, v); aucs.append(max(a, 1 - a))
        out[n] = float(np.mean(aucs)) if aucs else None
    return out

def main():
    t0 = time.time()
    g = G.load_grid(ROOT / "data/official")
    cache = ROOT / "work/drn91_X.npy"; cache.parent.mkdir(exist_ok=True)
    import os
    if cache.exists() and (ROOT / "work/drn91_names.json").exists():
        X = np.load(cache, mmap_mode="r"); fnames = json.loads((ROOT / "work/drn91_names.json").read_text())
    else:
        X, fnames = build_features(g)
        np.save(cache, X); (ROOT / "work/drn91_names.json").write_text(json.dumps(fnames))
        X = np.load(cache, mmap_mode="r")
    print(f"features {X.shape} in {time.time()-t0:.0f}s", flush=True)
    folds_list = list(spatial.folds(g.catalogue, g.footprint))
    can = canaries(X, fnames, folds_list, g)
    max_can = max(v for v in can.values() if v)
    print("max canary AUC", max_can, flush=True)
    if max_can > 0.90: raise SystemExit(f"LEAKAGE CANARY FAIL {max_can}")
    results = {}
    for mode, use_idx in [("E1_drainage_only", list(range(26, 31))), ("E2_all_plus_drainage", list(range(X.shape[0])))]:
        terms, surf = {}, np.zeros(g.shape, np.float32)
        for f in folds_list:
            Xt, yt = sample_xy(X[use_idx], f["train"], g.catalogue & f["train"], 100 + f["fold"])
            clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, max_depth=None, random_state=91)
            clf.fit(Xt, yt)
            reg = f["region"] & g.footprint
            ys, xs = np.nonzero(reg)
            for k in range(0, len(ys), 200000):
                sl = slice(k, k + 200000)
                surf[ys[sl], xs[sl]] = clf.predict_proba(np.asarray(X[use_idx][:, ys[sl], xs[sl]].T, dtype=np.float32))[:, 1]
        # score per fold with shared evaluator on dotted emission
        for n_dots, tag in [(37654, "n37654")]:
            terms_by = {}
            for f in folds_list:
                elig = f["region"] & g.footprint & ~f["visible"]
                dots = submodular_dti_emit(surf, eligible_mask=elig, n_dots=int(n_dots * elig.sum() / max((g.footprint & ~g.catalogue).sum(), 1)))
                pred = np.zeros(g.shape, np.float32); pred[dots > 0] = 1.0
                fold = dict(region=f["region"], truth=f["truth"], visible=f["visible"], masked_known=f["visible"])
                res, tr = EH.evaluate(pred, fold, g.footprint)
                terms_by.setdefault("cand", []).append(tr)
            terms_arr = np.concatenate(terms_by["cand"])
            np.save(ROOT / f"work/drn91_terms_{mode}.npy", terms_arr)
            pooled = float(EH.from_terms(terms_arr.sum(axis=0, keepdims=True))[0])
            summ = EH.pooled_summary({"cand": terms_arr}, candidate="cand")
            results[f"{mode}_{tag}"] = dict(holdout_dti=pooled, summary=json.loads(json.dumps(summ, default=str)))
            print(mode, tag, pooled, flush=True)
    # Final model on all data, E2 surface
    Xt, yt = sample_xy(X, g.footprint, g.catalogue, 999)
    clf = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, random_state=91).fit(Xt, yt)
    ys, xs = np.nonzero(g.footprint)
    surf = np.zeros(g.shape, np.float32)
    for k in range(0, len(ys), 200000):
        sl = slice(k, k + 200000)
        surf[ys[sl], xs[sl]] = clf.predict_proba(np.asarray(X[:, ys[sl], xs[sl]].T, dtype=np.float32))[:, 1]
    elig = g.footprint & ~g.catalogue
    dots = submodular_dti_emit(surf, eligible_mask=elig, n_dots=37654)
    pred = np.zeros(g.shape, np.float32); pred[dots > 0] = 1.0; pred[~g.footprint] = 0.0
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    digest = hashlib.sha256(np.packbits(dots > 0).tobytes()).hexdigest()[:8]
    name = f"gems91-drn91-e2-37654dots-{stamp}-{digest}-zeros"
    out = ROOT / "docs/downloads" / f"{name}.tif"
    rec = write_submission(out, pred, ROOT / "data/official/sample_submission.tif", g.footprint,
        note="DRN91 drainage-deflection HGB dotted; see run card verdict", name=name[:140],
        catalogue=g.catalogue, metadata=dict(lane="DRN91"))
    sha = hashlib.sha256(out.read_bytes()).hexdigest()
    # uniqueness vs local registry/download rasters
    from scipy.stats import rankdata
    from scipy.spatial import cKDTree
    cand_yx = np.column_stack(np.nonzero(pred > 0))
    uni = []
    sample_idx = rng_global.choice(int(g.footprint.sum()), 20000, replace=False)
    cand_surf_s = surf[g.footprint].ravel()[sample_idx]
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")) + sorted((ROOT / "data/registry").glob("*.tif")) if (ROOT/"data/registry").exists() else sorted((ROOT / "docs/downloads").glob("*.tif")):
        if p.name == out.name or "drn91" in p.name: continue
        try:
            with rasterio.open(p) as ds: a = ds.read(1).astype(np.float32)
        except Exception: continue
        if a.shape != pred.shape: continue
        b = np.where(np.isfinite(a), a, 0)
        rho = float(np.corrcoef(rankdata(cand_surf_s), rankdata(b[g.footprint].ravel()[sample_idx]))[0, 1])
        oyx = np.column_stack(np.nonzero(b > 0))
        ov = float((cKDTree(oyx).query(cand_yx, workers=-1)[0] <= 3).mean()) if len(oyx) else 0.0
        uni.append(dict(file=p.name, spearman=rho, dot_overlap_3px=ov))
    best_rho = max((abs(u["spearman"]) for u in uni), default=0)
    best_ov = max((u["dot_overlap_3px"] for u in uni), default=0)
    e2 = results.get("E2_all_plus_drainage_n37654", {}).get("holdout_dti", 0)
    promote = bool(e2 > 0.267782 and best_rho <= 0.90 and best_ov <= 0.70)
    card = dict(schema="gems91.run-card.v2", lane="DRN91 drainage-deflection/knickpoint (PROVISIONAL, no assigned paragraph supplied)",
        hypothesis="Young blind faults deflect piedmont drainages and create knickpoints on B12 even where scarps are buried; D8 flow-accumulation/deflection/knickpoint features plus sponsor bands, cross-fitted HGB, dotted DTI emission catches catalogue-missing faults.",
        mechanism="D8 routing on smoothed det_elev -> log-accumulation, channel distance, azimuth-incoherence deflection, channel-weighted slope-break knickpoint, convergence; HGB surface; shared submodular dotted emission at 37,654 dots.",
        non_fault_mimic="Lithology-controlled knickpoints and alluvial-fan channel avulsion",
        holdout_dti=dict(label="HOLDOUT-DTI", evaluator_version=EH.VERSION, withheld_positives=int(sum(int(f['truth'].sum()) for f in folds_list)), experiments=results),
        canary_max_symmetric_auc=max_can, canaries=can,
        registry_comparison=dict(scope="docs/downloads/*.tif in this repo + pinned parent in data if present (NOT universal fleet registry)", max_abs_surface_spearman=best_rho, max_dot_overlap_3px=best_ov, per_file=uni, duplicate=bool(best_rho > 0.90 or best_ov > 0.70)),
        raster_sha256=sha, validator_output=rec.get("validator") or rec,
        submission_name=name, note="DRN91 drainage-deflection dotted HGB; verdict in run card"[:140],
        ok_to_download=True, ok_to_submit=promote, verdict="promote" if promote else "negative",
        slots_used=0, organizer_confirmed=None, elapsed_s=time.time() - t0)
    (ROOT / "docs/run-card-DRN91.json").write_text(json.dumps(card, indent=2, default=str))
    (ROOT / "docs/current-run.json").write_text(json.dumps(dict(run_card="run-card-DRN91.json", ok_to_download=True, ok_to_submit=promote, raster_sha256=sha, submission_name=name), indent=2))
    print(json.dumps(dict(name=name, sha=sha, e2=e2, best_rho=best_rho, best_ov=best_ov, verdict=card["verdict"]), indent=2))

if __name__ == "__main__":
    main()
