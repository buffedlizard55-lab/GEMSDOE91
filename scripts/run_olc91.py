#!/usr/bin/env python3
"""OLC91 lane runner: Oriented Line-integral Coherence of a PU posterior.

Preregistration: docs/HYPOTHESES_OLC91.md (written before any experiment ran).

Subcommands
-----------
holdout --seed S   E0 / E1 / RND on vendor gems57 buffered_component_draw (LOQO models),
                   leakage canary, pooled paired bootstrap  -> docs/olc91/holdout-seedS.json
final              full-catalogue model, E1 surface, registry surface check (pre-placement),
                   37,654-dot emission, registry dot check (post-placement), fail-closed
                   writer, independent validation, JSON run card -> docs/olc91/, docs/downloads/

Every holdout number is HOLDOUT-DTI (evaluator gems57-pooled-hide-v2). Nothing here is a
leaderboard score; live scores exist only as organizer receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as H  # noqa: E402
from gems57 import metric as M  # noqa: E402
from gems91.dd_vtc_pu import _clean_band_edt, _grad_mag, _robust_z, submodular_dti_emit  # noqa: E402

LANE = "OLC91"
WORK = ROOT / "work" / "olc91"
OUT = ROOT / "docs" / "olc91"
DOWNLOADS = ROOT / "docs" / "downloads"
FEATURES = ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data" / "official" / "sample_submission.tif"

BUDGET = 37_654            # R0 dot count; holdout folds use the area-proportional share
COLLAR_PX = 2.0            # no dots on/within 2 px of known catalogue (R0 natural experiment)
LINE_PX = 11               # 1.1 km along-strike integration length (preregistered, untuned)
N_THETA = 12               # 15 degree azimuth steps
TRAIN_BUFFER_PX = 40       # LOQO: no training pixel within 4 km of the scored quadrant
NEG_RATIO = 3
HGB = dict(max_iter=250, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0,
           random_state=0)
MAX_RANK_CORR = 0.90
MAX_DOT_OVERLAP = 0.70
BLANKET_COVERAGE = 0.70    # 3-px footprint coverage at/above which literal overlap is uninformative


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- features
def build_features(fp: np.ndarray):
    WORK.mkdir(parents=True, exist_ok=True)
    cache, names_p = WORK / "X_f16.npy", WORK / "X_names.json"
    if cache.exists() and names_p.exists():
        return np.load(cache, mmap_mode="r"), json.loads(names_p.read_text())
    idx = np.flatnonzero(fp.ravel())
    with rasterio.open(FEATURES) as ds:
        n = ds.count
        desc = [d or f"b{i + 1}" for i, d in enumerate(ds.descriptions)]
        tmp = WORK / "X_f16.tmp.npy"
        X = np.lib.format.open_memmap(tmp, mode="w+", dtype=np.float16, shape=(idx.size, 2 * n))
        for b in range(n):
            z = _robust_z(_clean_band_edt(ds.read(b + 1), fp), fp)
            X[:, b] = z.ravel()[idx]
            X[:, n + b] = _robust_z(_grad_mag(z, 1.0), fp).ravel()[idx]
            log(f"  feature band {b + 1}/{n} {desc[b]}")
        X.flush()
        del X
    tmp.rename(cache)
    names = desc + [f"grad_{d}" for d in desc]
    names_p.write_text(json.dumps(names))
    return np.load(cache, mmap_mode="r"), names


def fp_index_grid(fp: np.ndarray) -> np.ndarray:
    g = np.full(fp.shape, -1, np.int64)
    g[fp] = np.arange(int(fp.sum()))
    return g


def fit_predict(X, fpi, fp, positives, train_dom, predict_mask, seed):
    rng = np.random.default_rng(seed)
    pos = fpi[positives & train_dom & fp]
    far = ndi.distance_transform_edt(~positives) > 3
    pool = fpi[train_dom & fp & far]
    n_neg = int(min(pool.size, NEG_RATIO * pos.size))
    neg = rng.choice(pool, n_neg, replace=False)
    tr = np.concatenate([pos, neg])
    y = np.r_[np.ones(pos.size), np.zeros(n_neg)]
    order = np.argsort(tr)
    clf = HistGradientBoostingClassifier(**HGB)
    clf.fit(np.asarray(X[tr[order]], dtype=np.float32), y[order])
    p = np.zeros(fp.shape, np.float32)
    pm = predict_mask & fp
    ids = fpi[pm]
    vals = np.empty(ids.size, np.float32)
    for s in range(0, ids.size, 400_000):
        vals[s:s + 400_000] = clf.predict_proba(np.asarray(X[ids[s:s + 400_000]], np.float32))[:, 1]
    p[pm] = vals
    return p, dict(n_pos=int(pos.size), n_neg=n_neg, n_predicted=int(ids.size))


# --------------------------------------------------------------------------- OLC transform
def line_kernels(length=LINE_PX, n=N_THETA):
    r, size = (length - 1) / 2.0, length + 2
    c = size // 2
    ks = []
    for i in range(n):
        th = np.pi * i / n
        k = np.zeros((size, size), np.float64)
        for t in np.linspace(-r, r, 8 * length):
            y, x = c - t * np.sin(th), c + t * np.cos(th)
            y0, x0 = int(np.floor(y)), int(np.floor(x))
            fy, fx = y - y0, x - x0
            k[y0, x0] += (1 - fy) * (1 - fx)
            k[y0, x0 + 1] += (1 - fy) * fx
            k[y0 + 1, x0] += fy * (1 - fx)
            k[y0 + 1, x0 + 1] += fy * fx
        ks.append((k / k.sum()).astype(np.float32))
    return ks


def olc_surface(p: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """E1 surface sqrt(p * C), C = max over azimuths of the 11 px line mean of p."""
    ys, xs = np.nonzero(mask)
    pad = LINE_PX + 2
    sl = (slice(max(ys.min() - pad, 0), ys.max() + pad + 1),
          slice(max(xs.min() - pad, 0), xs.max() + pad + 1))
    sub = p[sl].astype(np.float32)
    C = np.zeros_like(sub)
    for k in line_kernels():
        np.maximum(C, np.clip(fftconvolve(sub, k, mode="same"), 0.0, 1.0), out=C)
    full_c = np.zeros_like(p)
    full_c[sl] = C
    s = np.sqrt(np.clip(p, 0, 1) * np.clip(full_c, 0, 1)).astype(np.float32)
    return np.where(mask, s, 0).astype(np.float32), np.where(mask, full_c, 0).astype(np.float32)


def emit(surface, eligible, n):
    dots = submodular_dti_emit(surface, eligible_mask=eligible, n_dots=int(n))
    return ((dots > 0) & eligible).astype(np.float32)


def random_dots(eligible, n, seed):
    rng = np.random.default_rng(seed)
    ids = np.flatnonzero(eligible.ravel())
    out = np.zeros(eligible.shape, np.float32)
    out.ravel()[rng.choice(ids, int(n), replace=False)] = 1.0
    return out


# --------------------------------------------------------------------------- holdout
def run_holdout(seed: int):
    t0 = time.time()
    g = G.load_grid(ROOT / "data" / "official")
    fp = g.footprint
    X, names = build_features(fp)
    fpi = fp_index_grid(fp)
    folds, quad = H.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
    n_fp = int(fp.sum())
    arms = ("E0", "E1", "RND")
    terms = {a: None for a in arms}
    per_fold, strata = [], {a: {} for a in arms}
    canary_truth, canary_unl = [], []
    for f in folds:
        k, region = f["fold"], f["region"]
        known = f["masked_known"]
        dist_q = ndi.distance_transform_edt(quad != k)
        train_dom = fp & (dist_q > TRAIN_BUFFER_PX)
        predict_mask = fp & (ndi.distance_transform_edt(~region) <= LINE_PX // 2 + 2)
        p, info = fit_predict(X, fpi, fp, f["visible"], train_dom, predict_mask, seed * 100 + k)
        s1, _ = olc_surface(p, predict_mask)
        elig = region & fp & ~known & (ndi.distance_transform_edt(~known) > COLLAR_PX)
        n = int(round(BUDGET * float((region & fp).sum()) / n_fp))
        preds = dict(E0=emit(p, elig, n), E1=emit(s1, elig, n), RND=random_dots(elig, n, seed * 7 + k))
        dvis = ndi.distance_transform_edt(~f["visible"])
        active = fp & region & ~known
        truth = active & f["truth"]
        row = dict(fold=f["name"], n_dots=n, withheld_positive_pixels=int(truth.sum()), **info,
                   receipt=f["receipt"])
        for a in arms:
            res, tm = EH.evaluate(preds[a], f, fp)
            terms[a] = tm if terms[a] is None else terms[a] + tm
            row[f"{a}_dti"] = round(float(res["dti"]), 6)
            row[f"{a}_n_emitted"] = int(res["n_emitted"])
            covers, _, _ = M.max_cover(np.where(active, preds[a], 0).astype(np.float64), truth)
            ty, tx = np.nonzero(truth)
            dv = dvis[ty, tx]
            for lo, hi, lab in ((3, 10, "4-10px"), (10, 30, "10-30px"), (30, 1e9, ">30px")):
                m = (dv > lo) & (dv <= hi)
                st = strata[a].setdefault(lab, [0.0, 0])
                st[0] += float(covers[m].sum())
                st[1] += int(m.sum())
        per_fold.append(row)
        canary_truth.append(fpi[truth])
        canary_unl.append(fpi[active & ~truth])
        log(f"fold {f['name']}: " + " ".join(f"{a}={row[f'{a}_dti']:.4f}" for a in arms))
    summary = EH.pooled_summary(terms, candidate="E1")
    # ---- leakage canary: every input feature alone, symmetric AUC
    rng = np.random.default_rng(seed)
    tr_ids = np.concatenate(canary_truth)
    un_ids = np.concatenate(canary_unl)
    un_ids = np.sort(rng.choice(un_ids, min(un_ids.size, 300_000), replace=False))
    ids = np.concatenate([tr_ids, un_ids])
    order = np.argsort(ids)
    yy = np.r_[np.ones(tr_ids.size), np.zeros(un_ids.size)][order]
    Xc = np.asarray(X[ids[order]], np.float32)
    canary = []
    for j, nm in enumerate(names):
        auc = float(roc_auc_score(yy, Xc[:, j]))
        canary.append(dict(feature=nm, auc=round(auc, 4), symmetric_auc=round(max(auc, 1 - auc), 4)))
    worst = max(canary, key=lambda c: c["symmetric_auc"])
    cov = {a: {lab: dict(coverage=round(v[0] / v[1], 4) if v[1] else None, n_truth=v[1])
               for lab, v in strata[a].items()} for a in arms}
    d = summary["paired_differences"]["E0"]
    promote_seed = bool(d["ci95"][0] > 0)
    out = dict(
        lane=LANE, seed=seed, evidence_class="HOLDOUT-DTI", evaluator_version=EH.VERSION,
        implementation_hashes=EH.implementation_hashes(),
        split="vendor gems57 buffered_component_draw(seed=%d, hide_frac=0.20, buffer_px=3, boundary_px=12)" % seed,
        training="leave-one-quadrant-out HGB, PU (hidden components unlabelled), %d px train buffer" % TRAIN_BUFFER_PX,
        emission=f"submodular_dti_emit, budget {BUDGET} x area share, collar > {COLLAR_PX} px from known",
        pooled=summary, per_fold=per_fold, coverage_by_distance_to_visible=cov,
        leakage_canary=dict(threshold=0.90, worst=worst, stop=bool(worst["symmetric_auc"] > 0.90),
                            n_truth=int(tr_ids.size), n_unlabelled_sample=int(un_ids.size), features=canary),
        e1_beats_e0_ci_lower_gt_0=promote_seed, runtime_s=round(time.time() - t0, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"holdout-seed{seed}.json").write_text(json.dumps(out, indent=2) + "\n")
    s = summary["scores"]
    log("POOLED " + " ".join(f"{a}={s[a]['dti']:.4f} [{s[a]['ci95'][0]:.4f},{s[a]['ci95'][1]:.4f}]" for a in arms))
    log(f"DELTA E1-E0 {d['delta']:+.4f} CI {d['ci95']} promote_seed={promote_seed}; canary worst {worst}")
    return out


# --------------------------------------------------------------------------- registry
def registry_paths():
    paths = sorted((ROOT / "data" / "registry").glob("*.tif"))
    paths += sorted((ROOT / "data" / "fleet_registry").glob("*.tif"))
    paths += sorted((ROOT / "data" / "registry_siblings").glob("*.tif"))
    paths += sorted(p for p in DOWNLOADS.glob("*.tif"))
    seen, uniq, dup = {}, [], []
    for p in paths:
        h = sha256_file(p)
        if h in seen:
            dup.append(dict(path=str(p.relative_to(ROOT)), same_bytes_as=seen[h]))
            continue
        seen[h] = str(p.relative_to(ROOT))
        uniq.append((p, h))
    return uniq, dup


def registry_check(surface, dots, fp, eligible, stride=5):
    """Pre-placement surface Spearman + post-placement directed 3-px dot overlap."""
    uniq, dup = registry_paths()
    s = surface[fp][::stride].astype(np.float64)
    rs = rankdata(s) - (s.size + 1) / 2.0
    rs_n = float(np.linalg.norm(rs))
    dfp = dots[fp][::stride].astype(np.float64)
    rd = rankdata(dfp) - (dfp.size + 1) / 2.0
    rd_n = float(np.linalg.norm(rd))
    cy, cx = np.nonzero(dots > 0)
    cand = np.c_[cy, cx].astype(np.float64)
    elig_n = int(eligible.sum())
    rows, flags = [], []
    for p, h in uniq:
        with rasterio.open(p) as ds:
            if ds.count != 1 or ds.shape != fp.shape:
                flags.append(dict(path=str(p.relative_to(ROOT)), problem="not a single-band grid raster; skipped"))
                continue
            a = ds.read(1).astype(np.float64)
        nonfinite_in_fp = int((~np.isfinite(a) & fp).sum())
        a = np.where(np.isfinite(a), a, 0.0)
        pos = (a > 0) & fp
        r = a[fp][::stride]
        rr = rankdata(r) - (r.size + 1) / 2.0
        rr_n = float(np.linalg.norm(rr))
        surf_rho = abs(float(rs @ rr) / (rs_n * rr_n)) if rr_n > 0 else None
        dot_rho = abs(float(rd @ rr) / (rd_n * rr_n)) if rr_n > 0 else None
        n_pos = int(pos.sum())
        if n_pos:
            tree = cKDTree(np.c_[np.nonzero(pos)].astype(np.float64))
            dd, _ = tree.query(cand, k=1, distance_upper_bound=3.000001)
            fwd = float(np.isfinite(dd).mean())
            near = ndi.distance_transform_edt(~pos) <= 3.000001
            chance = float((near & eligible).sum()) / max(elig_n, 1)
            fp_cov = float((near & fp).sum()) / float(fp.sum())
        else:
            fwd, chance, fp_cov = 0.0, 0.0, 0.0
        corrected = (fwd - chance) / (1 - chance) if chance < 1 else 0.0
        blanket = fp_cov >= BLANKET_COVERAGE
        literal_dup = bool((surf_rho or 0) > MAX_RANK_CORR or (dot_rho or 0) > MAX_RANK_CORR or fwd > MAX_DOT_OVERLAP)
        corrected_dup = bool((surf_rho or 0) > MAX_RANK_CORR or (dot_rho or 0) > MAX_RANK_CORR
                             or (corrected > MAX_DOT_OVERLAP if blanket else fwd > MAX_DOT_OVERLAP))
        rows.append(dict(raster=str(p.relative_to(ROOT)), sha256=h, n_positive=n_pos,
                         nonfinite_inside_footprint=nonfinite_in_fp,
                         surface_abs_spearman=None if surf_rho is None else round(surf_rho, 5),
                         dots_abs_spearman=None if dot_rho is None else round(dot_rho, 5),
                         dots_within_3px_literal=round(fwd, 5), chance_within_3px=round(chance, 5),
                         dots_within_3px_chance_corrected=round(corrected, 5),
                         reference_3px_footprint_coverage=round(fp_cov, 5), blanket_reference=blanket,
                         duplicate_literal=literal_dup, duplicate_chance_corrected=corrected_dup))
    worst_s = max(rows, key=lambda r: r["surface_abs_spearman"] or 0)
    worst_o = max(rows, key=lambda r: r["dots_within_3px_literal"])
    worst_c = max((r for r in rows if not r["blanket_reference"]), key=lambda r: r["dots_within_3px_literal"])
    return dict(
        gate="duplicate-stop if |Spearman|>0.90 (surface pre-placement and dots post-placement) or >70% of dots within 3 px of one raster",
        n_unique_rasters_checked=len(rows), byte_duplicates_skipped=dup, skipped=flags,
        surface_max_abs_spearman=worst_s["surface_abs_spearman"], surface_closest=worst_s["raster"],
        dots_max_within_3px_literal=worst_o["dots_within_3px_literal"], dots_closest_literal=worst_o["raster"],
        dots_max_within_3px_non_blanket=worst_c["dots_within_3px_literal"], dots_closest_non_blanket=worst_c["raster"],
        blanket_references=[r["raster"] for r in rows if r["blanket_reference"]],
        any_duplicate_literal=any(r["duplicate_literal"] for r in rows),
        any_duplicate_chance_corrected=any(r["duplicate_chance_corrected"] for r in rows),
        comparisons=rows)


# --------------------------------------------------------------------------- final
def run_final(arm: str):
    t0 = time.time()
    g = G.load_grid(ROOT / "data" / "official")
    fp, cat = g.footprint, g.catalogue
    X, names = build_features(fp)
    fpi = fp_index_grid(fp)
    p, info = fit_predict(X, fpi, fp, cat, fp, fp, 777)
    s1, _ = olc_surface(p, fp)
    surface = s1 if arm == "E1" else p
    eligible = fp & ~cat & (ndi.distance_transform_edt(~cat) > COLLAR_PX)
    log("final model trained; running pre-placement registry surface check")
    dots = emit(surface, eligible, BUDGET)
    n_dots = int((dots > 0).sum())
    reg = registry_check(surface, dots, fp, eligible)
    log(f"registry: surface max |rho| {reg['surface_max_abs_spearman']} ({reg['surface_closest']}); "
        f"dots literal max {reg['dots_max_within_3px_literal']} ({reg['dots_closest_literal']}); "
        f"non-blanket max {reg['dots_max_within_3px_non_blanket']}")
    pred = np.where(fp, dots, 0.0).astype(np.float32)
    content = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    name = f"gemsdoe91-olc91-{arm.lower()}-strikecoherent-37654-20261025-{content}"
    note = (f"GEMSDOE91 OLC91 {arm}: PU posterior x 1.1km strike-coherent line support, "
            f"37654 3px dots, 2px catalogue collar")
    assert len(note) <= 140 and len(name) <= 140
    dcat = ndi.distance_transform_edt(~cat)
    meta = dict(lane=LANE, arm=arm, n_dots=n_dots, model=info,
                min_dot_distance_to_catalogue_px=round(float(dcat[dots > 0].min()), 3))
    from gems57.submission_writer import write_submission
    tif = DOWNLOADS / f"{name}.tif"
    receipt = write_submission(tif, pred, SAMPLE, fp, note=note, name=name, catalogue=cat, metadata=meta)
    np.save(WORK / f"final_surface_{arm}.npy", surface.astype(np.float16))
    out = dict(name=name, note=note, tif=str(tif.relative_to(ROOT)), receipt=receipt, registry=reg,
               meta=meta, runtime_s=round(time.time() - t0, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"final-{arm}.json").write_text(json.dumps(out, indent=2) + "\n")
    log(f"wrote {tif.name} sha256 {receipt['sha256']}")
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("holdout")
    h.add_argument("--seed", type=int, default=20)
    f = sub.add_parser("final")
    f.add_argument("--arm", choices=("E0", "E1"), default="E1")
    a = ap.parse_args()
    if a.cmd == "holdout":
        run_holdout(a.seed)
    else:
        run_final(a.arm)


if __name__ == "__main__":
    main()
