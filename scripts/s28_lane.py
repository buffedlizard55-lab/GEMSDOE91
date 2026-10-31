"""S28 lane: catalogue-prior transfer classifier on the official 19-band stack.

Hypothesis (H-S28-1, "CPT-19"): a classifier trained to separate *mapped* faults
from far-field background using only the official 19-band GEODAWN numeric
features learns a transferable expression of what an unmapped Great Basin
normal-fault trace looks like in potential-field / topographic / strain data.
Applied everywhere on the grid and emitted as a sparse dotted field outside the
mapped-fault collar, it should locate hidden traces better than the single-band
ridge formulas the fleet used up to GEMSDOE36.

Instrument: the shared buffered whole-component hide-and-recover holdout
(``vendor.gems57.holdout.buffered_component_draw``) with pixel-exact masking and
pooled distance-weighted Tversky (alpha 0.2, beta 0.8, 300 m triangular kernel).
The instrument measures recovery of *withheld catalogue* faults only; it cannot
measure hidden-fault discovery. Emission geometry is therefore frozen from the
nine-site leaderboard evidence (dot budget, spacing, catalogue collar) and *not*
tuned on the instrument -- see docs/s28/REVIEW.md for the argument.

Subcommands
    exp     run E1/E2/E3 on the holdout and write docs/s28/holdout.json
    build   train on the full catalogue, emit, validate, write the candidate
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from vendor.gems57 import metric  # noqa: E402
from vendor.gems57.grid import HEIGHT, WIDTH, load_grid  # noqa: E402
from vendor.gems57.holdout import buffered_component_draw  # noqa: E402

OFFICIAL = ROOT / "data" / "official"
WORK = ROOT / "data" / "work" / "s28"
OUT = ROOT / "docs" / "s28"

N_DOTS = 37654          # leaderboard-evidenced sparse budget (34-40k band)
SEP_PX = 2              # min Chebyshev separation -> Euclidean NN >= 2.83 px (fleet optimum ~3.0 px)
COLLAR_PX = 3.0         # 300 m: the kernel radius, matches the best sites
# distance-band quotas (share of dots), from the nine-site leaderboard envelope
# tuned to the nine-site leaderboard envelope: cumulative share below 20 px = 50 %
# (the two best sites sat at median 19.24-19.65 px, 69.8 % beyond 10 px)
QUOTAS = [(3.0, 5.0, 0.04), (5.0, 10.0, 0.14), (10.0, 20.0, 0.32),
          (20.0, 40.0, 0.28), (40.0, np.inf, 0.22)]


# --------------------------------------------------------------------------- io
def load_features() -> np.ndarray:
    meta = json.loads((WORK / "features.json").read_text())
    n = meta["n_layers"]
    feats = np.load(WORK / "features.npy", mmap_mode="r")
    assert feats.shape == (n, HEIGHT, WIDTH), feats.shape
    return feats


def gather(feats: np.ndarray, y: np.ndarray, x: np.ndarray) -> np.ndarray:
    out = np.empty((y.size, feats.shape[0]), np.float32)
    for i in range(feats.shape[0]):
        out[:, i] = feats[i].ravel()[y * WIDTH + x]
    return out


def predict_grid(model, feats: np.ndarray, rows=256) -> np.ndarray:
    p = np.zeros((HEIGHT, WIDTH), np.float32)
    for r0 in range(0, HEIGHT, rows):
        r1 = min(HEIGHT, r0 + rows)
        block = np.asarray(feats[:, r0:r1, :], np.float32).transpose(1, 2, 0).reshape(-1, feats.shape[0])
        p[r0:r1] = model.predict_proba(block)[:, 1].reshape(r1 - r0, WIDTH)
    return p


# ------------------------------------------------------------------- training
def train_xy(feats, footprint, cat, rng, neg_min_px=8.0, neg_mult=2.0):
    pos = np.argwhere(cat)
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    cand = footprint & (d_cat > neg_min_px)
    yy, xx = np.nonzero(cand)
    idx = rng.choice(yy.size, size=min(yy.size, int(neg_mult * pos.shape[0])), replace=False)
    neg = np.column_stack([yy[idx], xx[idx]])
    y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
    X = np.concatenate([gather(feats, pos[:, 0], pos[:, 1]), gather(feats, neg[:, 0], neg[:, 1])])
    return X, y


def fit_logistic(X, y, seed=28):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=400, n_jobs=1))
    m.fit(X, y)
    return m


def fit_hgb(X, y, seed=28, max_iter=150):
    from sklearn.ensemble import HistGradientBoostingClassifier

    m = HistGradientBoostingClassifier(max_iter=max_iter, learning_rate=0.1,
                                       max_leaf_nodes=31, l2_regularization=1.0,
                                       early_stopping=False, random_state=seed)
    m.fit(X, y)
    return m


# -------------------------------------------------------------------- emission
def emit(prob: np.ndarray, footprint: np.ndarray, d_cat: np.ndarray, *,
         n_dots: int = N_DOTS, sep: int = SEP_PX, collar: float = COLLAR_PX,
         quotas=QUOTAS) -> np.ndarray:
    """Greedy probability-ranked dotted emission with distance-band quotas."""
    out = np.zeros((HEIGHT, WIDTH), np.uint8)
    allowed = footprint & (d_cat > collar)
    remaining = n_dots
    bands = []
    for lo, hi, share in quotas:
        m = allowed & (d_cat > lo) & (d_cat <= hi)
        yy, xx = np.nonzero(m)
        if yy.size == 0:
            bands.append((share, 0, yy, xx, None))
            continue
        s = prob[yy, xx]
        order = np.argsort(-s)
        bands.append((share, yy.size, yy[order], xx[order], s[order]))

    # first pass: per-band quotas, generous oversample scan window
    placed = 0
    plan = [(b, int(round(n_dots * b[0]))) for b in bands]
    for (share, n_cand, yy, xx, s), quota in plan:
        need = min(quota, n_cand)
        taken = 0
        for k in range(min(n_cand, max(2000, need * 25))):
            y, x = int(yy[k]), int(xx[k])
            if out[y, x]:
                continue
            y0, y1 = max(0, y - sep), min(HEIGHT, y + sep + 1)
            x0, x1 = max(0, x - sep), min(WIDTH, x + sep + 1)
            if out[y0:y1, x0:x1].any():
                continue
            out[y, x] = 1
            taken += 1
            if taken >= need:
                break
        placed += taken

    # second pass: fill any shortfall from the global probability ranking
    if placed < n_dots:
        yy, xx = np.nonzero(allowed)
        s = prob[yy, xx]
        order = np.argsort(-s)
        for k in range(order.size):
            if placed >= n_dots:
                break
            y, x = int(yy[order[k]]), int(xx[order[k]])
            if out[y, x]:
                continue
            y0, y1 = max(0, y - sep), min(HEIGHT, y + sep + 1)
            x0, x1 = max(0, x - sep), min(WIDTH, x + sep + 1)
            if out[y0:y1, x0:x1].any():
                continue
            out[y, x] = 1
            placed += 1
    return out


def score_dots(dots: np.ndarray, truth: np.ndarray, valid: np.ndarray, known: np.ndarray) -> dict:
    r = metric.dti_exact(dots.astype(np.float32), truth, valid=valid, known=known)
    return dict(tp=r["tp"], fp=r["fp"], fn=r["fn"], n_truth=r["n_truth"],
                n_emitted=r["n_emitted"], dti=r["dti"], coverage=r["coverage"])


# ---------------------------------------------------------------------- holdout
def folds_and_truth(grid, seed=20):
    folds, quad = buffered_component_draw(grid, seed=seed, hide_frac=0.20, buffer_px=3)
    return folds


def run_experiments() -> int:
    t0 = time.time()
    grid = load_grid(OFFICIAL)
    feats = load_features()
    folds = folds_and_truth(grid)
    fp = grid.footprint
    rng = np.random.default_rng(28)

    results = {"schema": "gems91.s28.holdout.v1",
               "instrument": dict(evaluator="vendor.gems57.metric.dti_exact via buffered_component_draw",
                                  split="buffered whole-component LOQO v2", hide_frac=0.20,
                                  buffer_px=3, alpha=metric.ALPHA, beta=metric.BETA,
                                  radius_px=metric.RADIUS_PX),
               "emission": dict(n_dots=N_DOTS, sep_px=SEP_PX, collar_px=COLLAR_PX,
                                quotas=[list(q) for q in QUOTAS],
                                note="geometry frozen from nine-site leaderboard evidence; not tuned on the instrument"),
               "arms": {}}

    # ---- leakage canaries: each layer alone, withheld truth vs background -----
    canaries = []
    sample_bg = np.argwhere(fp & ~grid.catalogue & ~folds[0]["hidden_all"])
    bg = sample_bg[rng.choice(len(sample_bg), size=40000, replace=False)]
    for arm in ("logistic", "hgb"):
        pass
    from sklearn.metrics import roc_auc_score

    layer_names = json.loads((WORK / "features.json").read_text())["layers"]
    for li, nm in enumerate(layer_names):
        aucs = []
        for f in folds:
            pos = np.argwhere(f["truth"])
            if pos.size == 0:
                continue
            a = feats[li].ravel()[pos[:, 0] * WIDTH + pos[:, 1]]
            b = feats[li].ravel()[bg[:, 0] * WIDTH + bg[:, 1]]
            y = np.concatenate([np.ones(a.size), np.zeros(b.size)])
            aucs.append(float(roc_auc_score(y, np.concatenate([a, b]))))
        canaries.append(dict(layer=nm, auc=float(np.mean(aucs)),
                             auc_max=float(np.max(aucs)),
                             verdict="LEAKAGE-SUSPECT" if max(aucs) > 0.90 else "pass"))
    results["leakage_canaries"] = canaries
    results["canary_max_auc"] = float(max(c["auc_max"] for c in canaries))
    print(f"canary max AUC {results['canary_max_auc']:.4f}", flush=True)

    # ---- arms ---------------------------------------------------------------
    # ---- E0: the fleet-style hand-crafted physics surface (control) ---------
    def physics_surface(d_vis):
        """Catalogue-free composite the fleet used: HG edges + scarp + curvature."""
        layers = json.loads((WORK / "features.json").read_text())["layers"]
        i = {n: k for k, n in enumerate(layers)}
        surf = (np.asarray(feats[i["s4_tmi_hg"]]) + np.asarray(feats[i["s4_iso_grav_anom_hg"]])
                + np.asarray(feats[i["s4_iso_grav_anom_slope"]])
                + 0.5 * np.asarray(feats[i["s4_det_elev_slope"]])
                + 0.5 * np.asarray(feats[i["curv_det_elev"]]))
        surf = ndi.gaussian_filter(surf, 1.5)
        lo, hi = np.percentile(surf[fp], [1, 99])
        return np.clip((surf - lo) / (hi - lo), 0, 1).astype(np.float32)

    arms = {"E1_physics_baseline": None, "E2_logistic": fit_logistic, "E3_hgb": fit_hgb}
    pooled = {}
    for name, fit in arms.items():
        terms = []
        per_fold = []
        for f in folds:
            visible = f["visible"]
            d_vis = ndi.distance_transform_edt(~visible).astype(np.float32)
            if fit is None:
                prob = physics_surface(d_vis)
            else:
                X, y = train_xy(feats, fp, visible, rng)
                model = fit(X, y)
                prob = predict_grid(model, feats)
            dots = emit(prob, fp, d_vis)
            r = score_dots(dots, f["truth"], f["region"] & fp, f["masked_known"])
            per_fold.append(dict(fold=f["name"], **r,
                                 withheld=int(f["truth"].sum()),
                                 mean_prob_on_truth=float(prob[f["truth"]].mean()),
                                 mean_prob_bg=float(prob[bg[:, 0], bg[:, 1]].mean())))
            terms.append(r)
            print(name, f["name"], f"{r['dti']:.6f} tp={r['tp']:.1f} k={r['n_truth']}", flush=True)
        tp = sum(t["tp"] for t in terms); fpc = sum(t["fp"] for t in terms)
        fn = sum(t["fn"] for t in terms); k = sum(t["n_truth"] for t in terms)
        dti = metric.dti_from_components(tp, fpc, fn, metric.ALPHA, metric.BETA)
        pooled[name] = dict(tp=tp, fp=fpc, fn=fn, n_truth=k, dti=dti,
                            withheld_positives_total=int(k), per_fold=per_fold)
        results["arms"][name] = pooled[name]
        print(f"{name} pooled DTI {dti:.6f} (n_truth={k})", flush=True)

    best = max(pooled, key=lambda k: pooled[k]["dti"])
    results["best_arm"] = best
    results["runtime_s"] = time.time() - t0
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "holdout.json").write_text(json.dumps(results, indent=1, default=float))
    print("best arm:", best, "runtime", round(time.time() - t0, 1), "s")
    return 0


def build_candidate(tag: str | None = None) -> int:
    """Train on the full mapped catalogue, emit, validate and publish."""
    import hashlib

    from vendor.gems57 import gates
    from vendor.gems57.validate import assert_submittable, validate

    t0 = time.time()
    grid = load_grid(OFFICIAL)
    feats = load_features()
    fp = grid.footprint
    cat = grid.catalogue
    rng = np.random.default_rng(28)
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)

    import os

    if os.environ.get("S28_REUSE_PROB") == "1" and (WORK / "prob_full.npy").exists():
        prob = np.load(WORK / "prob_full.npy")
        print("reused cached probability surface", flush=True)
    else:
        X, y = train_xy(feats, fp, cat, rng)
        print(f"training rows {X.shape} positives {int(y.sum())}", flush=True)
        model = fit_hgb(X, y, max_iter=200)
        prob = predict_grid(model, feats)
        np.save(WORK / "prob_full.npy", prob)

    dots = emit(prob, fp, d_cat)
    n = int(dots.sum())
    dd = d_cat[dots > 0]
    from scipy.spatial import cKDTree
    yy, xx = np.nonzero(dots)
    pts = np.column_stack([yy, xx]).astype(np.float32)
    nn = cKDTree(pts).query(pts, k=2)[0][:, 1]
    geometry = dict(n_dots=n, median_dcat_px=float(np.median(dd)),
                    frac_le3px=float((dd <= 3).mean()), frac_gt10px=float((dd > 10).mean()),
                    nn_median_px=float(np.median(nn)), nn_min_px=float(nn.min()),
                    on_catalogue=int((dots.astype(bool) & cat).sum()),
                    outside_footprint=int((dots.astype(bool) & ~fp).sum()))
    print("geometry", geometry, flush=True)

    value = dots.astype(np.float32)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = tag or f"gems91-s28-cpt19-hgb-{n}dots-{stamp}"
    downloads = ROOT / "docs" / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    tif = downloads / f"{name}-zeros.tif"
    from vendor.gems57.grid import write_submission as _w

    _w(tif, value, mode="zeros")
    receipt = validate(tif, footprint=fp, catalogue=cat)
    assert_submittable(receipt)
    sha = receipt["sha256"]
    final_name = f"{name}-{sha[:8]}-zeros"
    final_tif = downloads / f"{final_name}.tif"
    if final_tif.exists():
        final_tif.unlink()
    tif.rename(final_tif)
    receipt = validate(final_tif, footprint=fp, catalogue=cat)
    assert_submittable(receipt)

    import zipfile

    zpath = downloads / f"{final_name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(final_tif, arcname=final_tif.name)

    # uniqueness against every local prior raster + the nine focus sites
    prior_paths = sorted(set(list((ROOT / "docs" / "downloads").glob("*.tif"))
                             + list((ROOT / "data" / "nine_site_raster").glob("*.tif"))))
    prior_paths = [p for p in prior_paths if p.resolve() != final_tif.resolve()]
    import rasterio

    overlaps = []
    mine = pts
    for p in prior_paths:
        try:
            with rasterio.open(p) as ds:
                a = ds.read(1)
        except Exception:
            continue
        if a.shape != (HEIGHT, WIDTH):
            continue
        pyy, pxx = np.nonzero(np.asarray(a) > 0)
        if pyy.size == 0:
            continue
        theirs = np.column_stack([pyy, pxx]).astype(np.float32)
        d_me_to_them = cKDTree(theirs).query(mine, k=1)[0]
        d_them_to_me = cKDTree(mine).query(theirs, k=1)[0]
        overlaps.append(dict(prior=p.name,
                             mine_within_3px=float((d_me_to_them <= 3).mean()),
                             theirs_within_3px=float((d_them_to_me <= 3).mean()),
                             prior_dots=int(pyy.size)))
    overlaps.sort(key=lambda r: -r["mine_within_3px"])
    worst = overlaps[0]
    uniqueness = dict(n_priors_compared=len(overlaps), worst=worst,
                      unique_at_70pct=bool(worst["mine_within_3px"] < 0.70),
                      registry_scope="local docs/downloads (this repository) + the nine focus-site rasters; NOT the full fleet",
                      top10=overlaps[:10])

    payload = dict(
        schema="gems91.s28.candidate.v1", generated_utc=stamp, name=final_name,
        tif=str(final_tif.relative_to(ROOT)), zip=str(zpath.relative_to(ROOT)),
        sha256=sha, bytes=final_tif.stat().st_size,
        note=f"S28 CPT-19: HGB transfer classifier on the 19 official GEODAWN bands, {n} dots, 3px lattice, >300m off catalogue",
        model="HistGradientBoostingClassifier(max_iter=200) on 41 catalogue-free layers",
        emission=dict(n_dots=N_DOTS, sep_px=SEP_PX, collar_px=COLLAR_PX,
                      quotas=[list(q) for q in QUOTAS]),
        geometry=geometry, validation=receipt, uniqueness=uniqueness,
        runtime_s=time.time() - t0)
    (OUT / "candidate.json").write_text(json.dumps(payload, indent=1, default=float))
    print(json.dumps({k: payload[k] for k in ("name", "sha256", "bytes", "geometry")}, indent=1))
    print("uniqueness worst:", worst)
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "exp"
    if cmd == "exp":
        raise SystemExit(run_experiments())
    if cmd == "build":
        raise SystemExit(build_candidate(sys.argv[2] if len(sys.argv) > 2 else None))
    raise SystemExit(f"unknown command {cmd}")
