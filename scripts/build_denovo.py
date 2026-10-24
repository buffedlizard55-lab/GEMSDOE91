#!/usr/bin/env python3
"""DENOVO-TRI3 build / holdout / canary driver (GEMSDOE91, 2026-10-24).

    python3 scripts/build_denovo.py --mode forensics
    python3 scripts/build_denovo.py --mode canary
    python3 scripts/build_denovo.py --mode holdout  --spacing 2.8 --n-dots 37654
    python3 scripts/build_denovo.py --mode build    --spacing 2.8 --n-dots 37654

Holdout protocol (parallel-run protocol section 2): withhold WHOLE catalogue
connected components (fault segments) assigned to 4 spatial checkerboard block
folds (400 px blocks, component centroid decides the fold); the only
catalogue-derived quantity the lane uses — the > 3 px candidate exclusion —
is re-derived per fold from the VISIBLE components only; visible catalogue is
masked pixel-exactly (it is simply not part of the truth); scoring is the
official DTI (scripts/dti.py, alpha 0.2 / beta 0.8 / 300 m triangular),
reported POOLED over folds (sum T, S, M, G, then DTI) with per-fold values
and a t-based 95% CI on the fold mean. Baselines scored identically: R0 dots
as-is, d2.8 dots as-is, and a seeded random spaced control at matched count.

Every number this script prints is HOLDOUT-DTI, MODEL or a file RECEIPT
(sha256/byte count re-read from disk). It never prints a live score.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import dti as D  # noqa: E402  (official max-per-truth-pixel DTI)
from gems91 import denovo as DN  # noqa: E402
from gems91 import io as GIO  # noqa: E402

FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
R0 = ROOT / "data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
D28 = ROOT / "data/registry/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
SOLO = ROOT / "data/registry/GEMSDOE28__h27-4-r1-solo-d2-8.tif"
SGMC = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
SURFACE_CACHE = ROOT / "work/denovo_surface_f32.npy"
DATE = "20261024"
SEED = 20261024


def read1(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        return s.read(1)


def footprint() -> np.ndarray:
    return np.isfinite(read1(SAMPLE))


def load_surface(fp: np.ndarray, *, refresh: bool = False) -> tuple[np.ndarray, dict]:
    if SURFACE_CACHE.is_file() and not refresh:
        surf = np.load(SURFACE_CACHE)
        return surf, {"cache": str(SURFACE_CACHE.relative_to(ROOT)),
                      "sha256_f32": hashlib.sha256(surf.tobytes()).hexdigest()}
    bands: dict[str, np.ndarray] = {}
    need = sorted(set(DN.BANDS.values()))
    inv = {v: k for k, v in DN.BANDS.items()}
    with rasterio.open(FEATS) as s:
        desc = s.descriptions
        for b in need:
            bands[inv[b]] = s.read(b)
    audit_bands = {inv[b]: {"band": b, "description": desc[b - 1]} for b in need}
    surf, audit = DN.build_surface(bands, fp)
    audit["bands_read"] = audit_bands
    SURFACE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.save(SURFACE_CACHE, surf)
    audit["sha256_f32"] = hashlib.sha256(surf.tobytes()).hexdigest()
    return surf, audit


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Mann-Whitney AUC with average ranks for ties."""
    pos = np.asarray(pos, dtype=np.float64)
    neg = np.asarray(neg, dtype=np.float64)
    pos = pos[np.isfinite(pos) & (pos > -1e30)]
    neg = neg[np.isfinite(neg) & (neg > -1e30)]
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="stable")
    ranks = np.empty(allv.size, dtype=np.float64)
    ranks[order] = np.arange(1, allv.size + 1, dtype=np.float64)
    # average ranks over exact ties
    sv = allv[order]
    i = 0
    r_sorted = ranks[order]
    while i < sv.size:
        j = i + 1
        while j < sv.size and sv[j] == sv[i]:
            j += 1
        if j - i > 1:
            r_sorted[i:j] = r_sorted[i:j].mean()
        i = j
    ranks[order] = r_sorted
    rp = ranks[: pos.size].sum()
    return float((rp - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size))


def fold_setup(cat: np.ndarray, n_folds: int = 4, block: int = 400):
    structure = np.ones((3, 3), dtype=int)
    lab, ncomp = ndi.label(cat, structure=structure)
    centroids = ndi.center_of_mass(cat, lab, np.arange(1, ncomp + 1))
    h, w = cat.shape
    comp_fold = np.zeros(ncomp + 1, dtype=np.int8)
    for k, (cr, cc) in enumerate(centroids, start=1):
        by, bx = int(cr) // block, int(cc) // block
        comp_fold[k] = (by % 2) * 2 + (bx % 2)
    rows = (np.arange(h) // block) % 2
    cols = (np.arange(w) // block) % 2
    region_fold = (rows[:, None] * 2 + cols[None, :]).astype(np.int8)
    return lab, comp_fold, region_fold, ncomp


def pooled(fold_parts: list) -> float:
    T = sum(p.T for p in fold_parts); S = sum(p.S for p in fold_parts)
    M = sum(p.M for p in fold_parts); G = sum(p.G for p in fold_parts)
    den = 0.2 * T + 0.2 * (S - M) + 0.8 * G
    return float(T / den) if den > 0 else 0.0


def mean_ci(vals: list[float]) -> list[float]:
    a = np.asarray(vals, dtype=float)
    if a.size < 2:
        return [float(a.mean()), float(a.mean())] if a.size else [float("nan")] * 2
    from scipy import stats
    se = float(a.std(ddof=1) / np.sqrt(a.size))
    t = float(stats.t.ppf(0.975, a.size - 1))
    return [round(float(a.mean() - t * se), 6), round(float(a.mean() + t * se), 6)]


# ---------------------------------------------------------------- forensics
def mode_forensics(args) -> dict:
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat)
    out: dict = {"catalogue_px": int(cat.sum()), "files": {}}
    claims = {"R0": (R0, 0.2778), "d2_8": (D28, 0.2600), "solo_d2_8": (SOLO, 0.2708)}
    dotsets = {}
    from scipy.spatial import cKDTree
    for name, (path, claim) in claims.items():
        dots = GIO.dot_mask(read1(path))
        dotsets[name] = dots
        rc = np.column_stack(np.nonzero(dots))
        tree = cKDTree(rc)
        nn, _ = tree.query(rc, k=2)
        d = nn[:, 1]
        out["files"][name] = {
            "path": str(path.relative_to(ROOT)), "claimed_score_CLAIM": claim,
            "sha256_RECEIPT": GIO.sha256_file(path), "n_dots_RECEIPT": int(dots.sum()),
            "nn_spacing_px": {"min": round(float(d.min()), 3), "p10": round(float(np.quantile(d, .1)), 3),
                              "median": round(float(np.median(d)), 3), "p90": round(float(np.quantile(d, .9)), 3)},
            "dots_by_dcat": {f"le{int(t)}": int((dcat[dots] <= t).sum()) for t in (2, 3, 8, 15)},
            "min_dcat_px": round(float(dcat[dots].min()), 4),
        }
    out["subset_R0_in_solo"] = bool((dotsets["R0"] & ~dotsets["solo_d2_8"]).sum() == 0)
    out["subset_R0_in_d28"] = bool((dotsets["R0"] & ~dotsets["d2_8"]).sum() == 0)
    # MODEL inference: if pruned dots earned ~0 hidden credit, TPw is shared by
    # the two rungs: TPw*(1/s_low - 1/s_high) = 0.2 * n_removed (kmax~0).
    return out


# ------------------------------------------------------------------- canary
def mode_canary(args) -> dict:
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat)
    rng = np.random.default_rng(SEED)
    neg_pool = np.flatnonzero(fp & ~cat & (dcat > 5.0))
    neg_idx = rng.choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
    pos_idx = np.flatnonzero(cat)
    surf, audit = load_surface(fp)
    rows = {}
    with rasterio.open(FEATS) as s:
        names = [s.tags(i)["band_name"] for i in range(1, s.count + 1)]
        for i, nm in enumerate(names, start=1):
            a = s.read(i).ravel()
            rows[nm] = {"band": i, "auc_raw": round(auc(a[pos_idx], a[neg_idx]), 4),
                        "auc_abs": round(auc(np.abs(a[pos_idx].astype(np.float64)),
                                             np.abs(a[neg_idx].astype(np.float64))), 4)}
            del a
    sr = surf.ravel()
    rows["TRI3_surface"] = {"band": None, "auc_raw": round(auc(sr[pos_idx], sr[neg_idx]), 4)}
    return {"n_positives_catalogue_px": int(pos_idx.size), "n_negatives_sampled": int(neg_idx.size),
            "neg_rule": "footprint, off-catalogue, dcat>5px, rng seed 20261024",
            "leakage_threshold": 0.90, "bands": rows, "surface_audit": audit}


# ------------------------------------------------------------------ holdout
def mode_holdout(args) -> dict:
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    surf, audit = load_surface(fp)
    dots_r0 = GIO.dot_mask(read1(R0))
    dots_d28 = GIO.dot_mask(read1(D28))
    lab, comp_fold, region_fold, ncomp = fold_setup(cat)
    methods = ["tri3", "r0_as_is", "d2_8_as_is", "random_matched"]
    parts: dict[str, list] = {m: [] for m in methods}
    folds: dict[str, list[float]] = {m: [] for m in methods}
    counts: dict[str, list[int]] = {m: [] for m in methods}
    n_withheld = []
    rng_master = np.random.default_rng(SEED)
    for f in range(4):
        truth = cat & (comp_fold[lab] == f) & (lab > 0)
        visible = cat & ~truth
        d_vis = ndi.distance_transform_edt(~visible)
        region = region_fold == f
        share = float((fp & region).sum()) / float(fp.sum())
        n_f = int(round(args.n_dots * share))
        eligible = fp & region & (d_vis > 3.0)
        cand = {
            "tri3": DN.greedy_spaced(surf, eligible, n_f, spacing_px=args.spacing),
            "r0_as_is": dots_r0 & region,
            "d2_8_as_is": dots_d28 & region,
            "random_matched": DN.greedy_spaced(
                rng_master.random(surf.shape, dtype=np.float32), eligible, n_f,
                spacing_px=args.spacing),
        }
        n_withheld.append(int(truth.sum()))
        for m in methods:
            pred = cand[m].astype(np.float64)
            p = D.components(pred, truth.astype(np.float64))
            parts[m].append(p); folds[m].append(round(p.score, 6)); counts[m].append(int(cand[m].sum()))
            del pred
        print(f"fold {f}: withheld={n_withheld[-1]} n_f={n_f} " +
              " ".join(f"{m}={folds[m][-1]:.5f}" for m in methods), flush=True)
    out = {"protocol": "whole-component checkerboard-block holdout, 400px blocks; "
                       "exclusion from visible catalogue only; official DTI pooled",
           "n_components": int(ncomp), "n_withheld_positives_per_fold": n_withheld,
           "n_withheld_positives_total": int(sum(n_withheld)),
           "spacing_px": args.spacing, "n_dots_total_budget": args.n_dots,
           "surface_audit": audit, "methods": {}}
    for m in methods:
        out["methods"][m] = {"pooled_holdout_dti": round(pooled(parts[m]), 6),
                             "fold_dti": folds[m], "fold_mean_ci95": mean_ci(folds[m]),
                             "dots_per_fold": counts[m],
                             "pooled_T": round(sum(p.T for p in parts[m]), 2),
                             "pooled_S": round(sum(p.S for p in parts[m]), 2),
                             "pooled_M": round(sum(p.M for p in parts[m]), 2),
                             "pooled_G": int(sum(p.G for p in parts[m]))}
    return out


# -------------------------------------------------------------------- build
def spearman_sample(a: np.ndarray, b: np.ndarray, idx: np.ndarray) -> float:
    from scipy.stats import rankdata
    x = rankdata(np.asarray(a.ravel()[idx], dtype=np.float64))
    y = rankdata(np.asarray(b.ravel()[idx], dtype=np.float64))
    return float(np.corrcoef(x, y)[0, 1])


def mode_build(args) -> dict:
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat)
    surf, audit = load_surface(fp)
    eligible = fp & (dcat > 3.0)
    dots = DN.greedy_spaced(surf, eligible, args.n_dots, spacing_px=args.spacing)
    assert int(dots.sum()) == args.n_dots, f"placed {int(dots.sum())} != {args.n_dots}"
    assert not (dots & cat).any()
    assert float(dcat[dots].min()) > 3.0
    dot_digest = GIO.dot_digest(dots)

    arr = np.where(fp, dots.astype(np.float32), np.float32(np.nan))
    outdir = ROOT / "releases"
    outdir.mkdir(exist_ok=True)
    stem_tmp = f"gems91-denovo-tri3-{args.n_dots}dots-s{args.spacing}-{DATE}-tmp"
    p_nan_tmp, p_zero_tmp = outdir / f"{stem_tmp}-nan.tif", outdir / f"{stem_tmp}-zeros.tif"
    GIO.write_float32(p_nan_tmp, arr, encoding="nan", template=SAMPLE)
    GIO.write_float32(p_zero_tmp, arr, encoding="zeros", template=SAMPLE)
    sha_nan, sha_zero = GIO.sha256_file(p_nan_tmp), GIO.sha256_file(p_zero_tmp)
    stem = f"gems91-denovo-tri3-{args.n_dots}dots-s{args.spacing}-{DATE}-{sha_nan[:8]}"
    p_nan, p_zero = outdir / f"{stem}-nan.tif", outdir / f"{stem}-zeros.tif"
    p_nan_tmp.replace(p_nan); p_zero_tmp.replace(p_zero)

    # --- uniqueness vs registry (protocol section 1) -----------------------
    rng = np.random.default_rng(SEED)
    fp_idx = np.flatnonzero(fp)
    sample_idx = rng.choice(fp_idx, size=150_000, replace=False)
    uniq = {}
    registry = {"parent_r0": R0, "anc_d2_8": D28, "anc_solo_d2_8": SOLO,
                "anc_h19_5": ROOT / "data/registry/calib_h195_01922.tif",
                "anc_h19_4": ROOT / "data/registry/calib_h194_01894.tif",
                "anc_h16_1": ROOT / "data/registry/calib_h161_01855.tif",
                "anc_d1_5": ROOT / "data/registry/calib_d15_02477.tif"}
    for name, path in registry.items():
        other = GIO.dot_mask(read1(path))
        d_other = ndi.distance_transform_edt(~other)
        within3 = float((d_other[dots] <= 3.0).mean()) if dots.any() else 0.0
        uniq[name] = {
            "surface_spearman_sample": round(spearman_sample(surf, other.astype(np.float32), sample_idx), 4),
            "pct_our_dots_within_3px": round(100.0 * within3, 2),
            "their_positive_px": int(other.sum()),
        }
        del other, d_other

    # --- SGMC off-catalogue control (REPORT ONLY) ---------------------------
    sgmc = np.nan_to_num(read1(SGMC), nan=0.0) > 0
    sgmc_off = sgmc & (dcat > 3.0) & fp
    ctr = {}
    for name, dd in {"tri3": dots, "r0": GIO.dot_mask(read1(R0))}.items():
        p = D.components(dd.astype(np.float64), sgmc_off.astype(np.float64))
        ctr[name] = {"sgmc_off_dti_PROXY": round(p.score, 6), "T": round(p.T, 2),
                     "S": round(p.S, 2), "M": round(p.M, 2), "G": int(p.G)}

    out = {"id": stem, "n_dots": int(dots.sum()), "spacing_px": args.spacing,
           "min_dcat_px_RECEIPT": round(float(dcat[dots].min()), 4),
           "dots_on_catalogue_RECEIPT": int((dots & cat).sum()),
           "dot_set_digest": dot_digest, "surface_audit": audit,
           "files": {"nan": {"file": p_nan.name, "sha256": sha_nan, "bytes": p_nan.stat().st_size},
                     "zeros": {"file": p_zero.name, "sha256": sha_zero, "bytes": p_zero.stat().st_size}},
           "uniqueness_vs_registry": uniq,
           "duplicate_rule": "rank-corr > 0.90 OR > 70% dots within 3px of one registry raster",
           "sgmc_control_report_only": {"truth_px_off_catalogue": int(sgmc_off.sum()), **ctr}}
    out["is_duplicate"] = any(
        v["surface_spearman_sample"] > 0.90 or v["pct_our_dots_within_3px"] > 70.0
        for v in uniq.values())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["forensics", "canary", "holdout", "build", "holdout2", "build2", "holdout3", "build3"])
    ap.add_argument("--spacing", type=float, default=2.8)
    ap.add_argument("--n-dots", type=int, default=37654)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    fn = {"forensics": mode_forensics, "canary": mode_canary,
          "holdout": mode_holdout, "build": mode_build,
          "holdout2": mode_holdout2, "build2": mode_build2,
          "holdout3": mode_holdout3, "build3": mode_build3}[args.mode]
    result = fn(args)
    result = {"mode": args.mode, "evaluator": "scripts/dti.py official-DTI (alpha=0.2,beta=0.8,R=3px)",
              **result}
    text = json.dumps(result, indent=2)
    if args.out:
        p = ROOT / args.out
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text + "\n")
        print(f"wrote {args.out}")
    print(text[:6000])
    return 0




# ------------------------------------------------- experiment 2: SUP-CONCORD
# Preregistered 2026-10-24 AFTER experiment 1 (TRI3 pooled HOLDOUT-DTI
# 0.091215 vs random-matched 0.070827 vs leakage-flattered d2.8-as-is
# 0.156058; evidence/holdout_denovo_tri3_20261024.json). TRI3's pixel-exact
# AND-gate is too strict: mag/grav crests sit off-trace (cf. SNAP, IR-91-28).
# SUP-CONCORD keeps the same emission and exclusion, but the surface is an
# L2 logistic regression on footprint percentiles of all 19 sponsor bands
# plus the TRI3 surface, trained per fold ONLY on pixels outside the fold
# region (positives = visible catalogue there; negatives = sampled pixels
# > 5 px from the visible catalogue there). No distance-to-catalogue feature
# (halo/leakage). Percentiles use a fixed 300k-pixel footprint reference
# sample (seed 20261024) for every fold and for the final full-grid build.

REF_N = 300_000


def _ref_sample(fp):
    rng = np.random.default_rng(SEED)
    idx = np.flatnonzero(fp)
    return np.sort(rng.choice(idx, size=min(REF_N, idx.size), replace=False))


def _band_refs(ref_idx, surf):
    """Sorted reference values per feature (19 bands + TRI3 surface)."""
    refs = []
    with rasterio.open(FEATS) as s:
        for b in range(1, s.count + 1):
            a = s.read(b).ravel()[ref_idx].astype(np.float64)
            a = a[np.isfinite(a) & (a > -1e30)]
            refs.append(np.sort(a))
            del a
    a = surf.ravel()[ref_idx].astype(np.float64)
    refs.append(np.sort(a[np.isfinite(a)]))
    return refs


def _pct_from_ref(values, ref_sorted):
    v = np.asarray(values, dtype=np.float64)
    bad = ~np.isfinite(v) | (v < -1e30)
    out = np.searchsorted(ref_sorted, np.where(bad, np.median(ref_sorted), v)) / max(1, ref_sorted.size)
    return out.astype(np.float32)


def _sample_matrix(idx, refs, surf):
    cols = []
    with rasterio.open(FEATS) as s:
        for b in range(1, s.count + 1):
            a = s.read(b).ravel()
            cols.append(_pct_from_ref(a[idx], refs[b - 1]))
            del a
    cols.append(_pct_from_ref(surf.ravel()[idx], refs[-1]))
    return np.column_stack(cols).astype(np.float32)


def _predict_grid(coef, intercept, refs, surf, fp):
    logit = np.full(surf.shape, float(intercept), dtype=np.float32)
    with rasterio.open(FEATS) as s:
        for b in range(1, s.count + 1):
            if coef[b - 1] == 0.0:
                continue
            a = s.read(b)
            logit += float(coef[b - 1]) * _pct_from_ref(a.ravel(), refs[b - 1]).reshape(surf.shape)
            del a
    logit += float(coef[-1]) * _pct_from_ref(surf.ravel(), refs[-1]).reshape(surf.shape)
    return np.where(fp, logit, -1e30).astype(np.float32)  # rank surface (logit)


def _train_logreg(X, y):
    from sklearn.linear_model import LogisticRegression
    clf = LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs")
    clf.fit(X, y)
    return clf.coef_[0].astype(np.float64), float(clf.intercept_[0])


def mode_holdout2(args) -> dict:
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    surf, audit = load_surface(fp)
    lab, comp_fold, region_fold, ncomp = fold_setup(cat)
    ref_idx = _ref_sample(fp)
    refs = _band_refs(ref_idx, surf)
    rng = np.random.default_rng(SEED + 7)
    parts, folds, counts, train_auc = [], [], [], []
    n_withheld = []
    for f in range(4):
        truth = cat & (comp_fold[lab] == f) & (lab > 0)
        visible = cat & ~truth
        d_vis = ndi.distance_transform_edt(~visible)
        region = region_fold == f
        train_area = fp & ~region
        pos_idx = np.flatnonzero(visible & train_area)
        neg_pool = np.flatnonzero(train_area & (d_vis > 5.0) & ~visible)
        neg_idx = rng.choice(neg_pool, size=min(3 * pos_idx.size, neg_pool.size), replace=False)
        X_pos = _sample_matrix(pos_idx, refs, surf)
        X_neg = _sample_matrix(neg_idx, refs, surf)
        X = np.vstack([X_pos, X_neg]); y = np.r_[np.ones(len(X_pos)), np.zeros(len(X_neg))]
        coef, intercept = _train_logreg(X, y)
        train_auc.append(round(auc(X_pos @ coef + intercept, X_neg @ coef + intercept), 4))
        del X, X_pos, X_neg
        sup = _predict_grid(coef, intercept, refs, surf, fp)
        share = float((fp & region).sum()) / float(fp.sum())
        n_f = int(round(args.n_dots * share))
        eligible = fp & region & (d_vis > 3.0)
        dots = DN.greedy_spaced(sup, eligible, n_f, spacing_px=args.spacing)
        del sup
        p = D.components(dots.astype(np.float64), truth.astype(np.float64))
        parts.append(p); folds.append(round(p.score, 6)); counts.append(int(dots.sum()))
        n_withheld.append(int(truth.sum()))
        print(f"fold {f}: SUP DTI={p.score:.5f} trainAUC={train_auc[-1]} "
              f"pos={pos_idx.size} neg={neg_idx.size}", flush=True)
    return {"experiment": 2, "method": "SUP-CONCORD logreg(19 band pcts + TRI3 pct), "
            "trained outside fold region only, no dcat feature",
            "n_withheld_positives_per_fold": n_withheld,
            "pooled_holdout_dti": round(pooled(parts), 6), "fold_dti": folds,
            "fold_mean_ci95": mean_ci(folds), "dots_per_fold": counts,
            "train_auc_per_fold": train_auc,
            "pooled_T": round(sum(p.T for p in parts), 2),
            "pooled_S": round(sum(p.S for p in parts), 2),
            "pooled_M": round(sum(p.M for p in parts), 2),
            "pooled_G": int(sum(p.G for p in parts)),
            "spacing_px": args.spacing, "n_dots_total_budget": args.n_dots}


def mode_build2(args) -> dict:
    """Final SUP build: train on the full catalogue, emit, same gates data."""
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat)
    surf, audit = load_surface(fp)
    ref_idx = _ref_sample(fp)
    refs = _band_refs(ref_idx, surf)
    rng = np.random.default_rng(SEED + 7)
    pos_idx = np.flatnonzero(cat)
    neg_pool = np.flatnonzero(fp & (dcat > 5.0))
    neg_idx = rng.choice(neg_pool, size=min(3 * pos_idx.size, neg_pool.size), replace=False)
    X_pos = _sample_matrix(pos_idx, refs, surf)
    X_neg = _sample_matrix(neg_idx, refs, surf)
    X = np.vstack([X_pos, X_neg]); y = np.r_[np.ones(len(X_pos)), np.zeros(len(X_neg))]
    coef, intercept = _train_logreg(X, y)
    with rasterio.open(FEATS) as s:
        names = [s.tags(i)["band_name"] for i in range(1, s.count + 1)] + ["TRI3_surface"]
    weights = {names[i]: round(float(coef[i]), 4) for i in range(len(names))}
    del X, X_pos, X_neg
    sup = _predict_grid(coef, intercept, refs, surf, fp)
    np.save(ROOT / "work/denovo_sup_surface_f32.npy", sup)
    eligible = fp & (dcat > 3.0)
    dots = DN.greedy_spaced(sup, eligible, args.n_dots, spacing_px=args.spacing)
    assert int(dots.sum()) == args.n_dots
    arr = np.where(fp, dots.astype(np.float32), np.float32(np.nan))
    outdir = ROOT / "releases"; outdir.mkdir(exist_ok=True)
    stem_tmp = f"gems91-denovo-sup-{args.n_dots}dots-s{args.spacing}-{DATE}-tmp"
    p_nan_tmp, p_zero_tmp = outdir / f"{stem_tmp}-nan.tif", outdir / f"{stem_tmp}-zeros.tif"
    GIO.write_float32(p_nan_tmp, arr, encoding="nan", template=SAMPLE)
    GIO.write_float32(p_zero_tmp, arr, encoding="zeros", template=SAMPLE)
    sha_nan, sha_zero = GIO.sha256_file(p_nan_tmp), GIO.sha256_file(p_zero_tmp)
    stem = f"gems91-denovo-sup-{args.n_dots}dots-s{args.spacing}-{DATE}-{sha_nan[:8]}"
    p_nan, p_zero = outdir / f"{stem}-nan.tif", outdir / f"{stem}-zeros.tif"
    p_nan_tmp.replace(p_nan); p_zero_tmp.replace(p_zero)
    # uniqueness + SGMC (same code path as build)
    rng2 = np.random.default_rng(SEED)
    sample_idx = rng2.choice(np.flatnonzero(fp), size=150_000, replace=False)
    uniq = {}
    registry = {"parent_r0": R0, "anc_d2_8": D28, "anc_solo_d2_8": SOLO,
                "anc_h19_5": ROOT / "data/registry/calib_h195_01922.tif",
                "anc_h19_4": ROOT / "data/registry/calib_h194_01894.tif",
                "anc_h16_1": ROOT / "data/registry/calib_h161_01855.tif",
                "anc_d1_5": ROOT / "data/registry/calib_d15_02477.tif"}
    for name, path in registry.items():
        other = GIO.dot_mask(read1(path))
        d_other = ndi.distance_transform_edt(~other)
        uniq[name] = {"surface_spearman_sample": round(spearman_sample(sup, other.astype(np.float32), sample_idx), 4),
                      "pct_our_dots_within_3px": round(100.0 * float((d_other[dots] <= 3.0).mean()), 2),
                      "their_positive_px": int(other.sum())}
        del other, d_other
    tri3_corr = round(spearman_sample(sup, surf, sample_idx), 4)
    sgmc = np.nan_to_num(read1(SGMC), nan=0.0) > 0
    sgmc_off = sgmc & (dcat > 3.0) & fp
    ctr = {}
    for name, dd in {"sup": dots, "r0": GIO.dot_mask(read1(R0))}.items():
        p = D.components(dd.astype(np.float64), sgmc_off.astype(np.float64))
        ctr[name] = {"sgmc_off_dti_PROXY": round(p.score, 6), "T": round(p.T, 2),
                     "S": round(p.S, 2), "M": round(p.M, 2), "G": int(p.G)}
    out = {"id": stem, "method": "SUP-CONCORD logreg on 19 band percentiles + TRI3 percentile; "
           "trained on full catalogue; greedy spaced emission >3px off catalogue",
           "logreg_weights_on_percentiles": weights, "logreg_intercept": round(intercept, 4),
           "n_dots": int(dots.sum()), "spacing_px": args.spacing,
           "min_dcat_px_RECEIPT": round(float(dcat[dots].min()), 4),
           "dots_on_catalogue_RECEIPT": int((dots & cat).sum()),
           "dot_set_digest": GIO.dot_digest(dots),
           "sup_surface_sha256_f32": hashlib.sha256(sup.tobytes()).hexdigest(),
           "tri3_surface_spearman_vs_sup": tri3_corr,
           "files": {"nan": {"file": p_nan.name, "sha256": sha_nan, "bytes": p_nan.stat().st_size},
                     "zeros": {"file": p_zero.name, "sha256": sha_zero, "bytes": p_zero.stat().st_size}},
           "uniqueness_vs_registry": uniq,
           "duplicate_rule": "rank-corr > 0.90 OR > 70% dots within 3px of one registry raster",
           "sgmc_control_report_only": {"truth_px_off_catalogue": int(sgmc_off.sum()), **ctr}}
    out["is_duplicate"] = any(v["surface_spearman_sample"] > 0.90 or v["pct_our_dots_within_3px"] > 70.0
                               for v in uniq.values())
    return out




# ------------------------------------------- experiment 3: HGB-CTX (sponsor)
# Preregistered 2026-10-24 after E2 (SUP pooled 0.097146). Same folds,
# exclusion and emission. Features: 19 band percentiles + TRI3 percentile +
# 11x11 local mean of the percentile grid for bands 3,4,5,6,9,11,18,19
# (context lets an off-trace mag/grav crest vote for the trace). Model:
# HistGradientBoosting (300 iters, lr 0.06, 63 leaves, min_leaf 40, seed
# fixed). Trained outside the fold region only, as in E2. This is the last
# of the 3 protocol experiments; the build uses the E1-E3 winner.

CTX_BANDS = (3, 4, 5, 6, 9, 11, 18, 19)
CTX_SIZE = 11


def _pct_grid(band_idx0, refs, surf=None):
    if band_idx0 < 19:
        with rasterio.open(FEATS) as s:
            a = s.read(band_idx0 + 1)
    else:
        a = surf
    g = _pct_from_ref(a.ravel(), refs[band_idx0]).reshape(a.shape)
    del a
    return g


def _ctx_matrix(idx, refs, surf):
    cols = []
    for b in range(20):
        g = _pct_grid(b, refs, surf)
        cols.append(g.ravel()[idx])
        if (b + 1) in CTX_BANDS:
            ctx = ndi.uniform_filter(g, CTX_SIZE, mode="nearest")
            cols.append(ctx.ravel()[idx])
            del ctx
        del g
    return np.column_stack(cols).astype(np.float32)


def _ctx_feature_names():
    with rasterio.open(FEATS) as s:
        base = [s.tags(i)["band_name"] for i in range(1, s.count + 1)] + ["TRI3_surface"]
    out = []
    for i, nm in enumerate(base, start=1):
        out.append(nm)
        if i in CTX_BANDS:
            out.append(nm + "_mean11")
    return out


def _train_hgb(X, y):
    from sklearn.ensemble import HistGradientBoostingClassifier
    clf = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
        min_samples_leaf=40, l2_regularization=1.0, random_state=SEED)
    clf.fit(X, y)
    return clf


def _predict_grid_hgb(clf, refs, surf, fp, block_rows=220, halo=8):
    h, w = surf.shape
    out = np.full((h, w), -1e30, dtype=np.float32)
    # percentile grids are computed block-wise from window reads; context uses
    # the halo so the 11x11 mean is exact inside the core block.
    for r0 in range(0, h, block_rows):
        r1 = min(h, r0 + block_rows)
        wr0, wr1 = max(0, r0 - halo), min(h, r1 + halo)
        cols = []
        shape = (wr1 - wr0, w)
        for b in range(20):
            if b < 19:
                with rasterio.open(FEATS) as s:
                    from rasterio.windows import Window
                    a = s.read(b + 1, window=Window(0, wr0, w, wr1 - wr0))
            else:
                a = surf[wr0:wr1]
            g = _pct_from_ref(a.ravel(), refs[b]).reshape(shape)
            cols.append(g[r0 - wr0: r0 - wr0 + (r1 - r0)].ravel())
            if (b + 1) in CTX_BANDS:
                ctx = ndi.uniform_filter(g, CTX_SIZE, mode="nearest")
                cols.append(ctx[r0 - wr0: r0 - wr0 + (r1 - r0)].ravel())
                del ctx
            del a, g
        Xb = np.column_stack(cols).astype(np.float32)
        del cols
        proba = clf.predict_proba(Xb)[:, 1].astype(np.float32)
        del Xb
        out[r0:r1] = proba.reshape(r1 - r0, w)
    return np.where(fp, out, -1e30).astype(np.float32)


def mode_holdout3(args) -> dict:
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    surf, audit = load_surface(fp)
    lab, comp_fold, region_fold, ncomp = fold_setup(cat)
    ref_idx = _ref_sample(fp)
    refs = _band_refs(ref_idx, surf)
    rng = np.random.default_rng(SEED + 7)
    parts, folds, counts, n_withheld = [], [], [], []
    for f in range(4):
        truth = cat & (comp_fold[lab] == f) & (lab > 0)
        visible = cat & ~truth
        d_vis = ndi.distance_transform_edt(~visible)
        region = region_fold == f
        train_area = fp & ~region
        pos_idx = np.flatnonzero(visible & train_area)
        neg_pool = np.flatnonzero(train_area & (d_vis > 5.0) & ~visible)
        neg_idx = rng.choice(neg_pool, size=min(3 * pos_idx.size, neg_pool.size), replace=False)
        idx = np.r_[pos_idx, neg_idx]
        y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
        X = _ctx_matrix(idx, refs, surf)
        clf = _train_hgb(X, y)
        del X
        sup = _predict_grid_hgb(clf, refs, surf, fp)
        share = float((fp & region).sum()) / float(fp.sum())
        n_f = int(round(args.n_dots * share))
        eligible = fp & region & (d_vis > 3.0)
        dots = DN.greedy_spaced(sup, eligible, n_f, spacing_px=args.spacing)
        del sup
        p = D.components(dots.astype(np.float64), truth.astype(np.float64))
        parts.append(p); folds.append(round(p.score, 6)); counts.append(int(dots.sum()))
        n_withheld.append(int(truth.sum()))
        print(f"fold {f}: HGB-CTX DTI={p.score:.5f} pos={pos_idx.size}", flush=True)
    return {"experiment": 3, "method": "HGB-CTX HistGB on 20 percentiles + 8 mean11 contexts, "
            "trained outside fold region only, no dcat feature",
            "features": _ctx_feature_names(),
            "n_withheld_positives_per_fold": n_withheld,
            "pooled_holdout_dti": round(pooled(parts), 6), "fold_dti": folds,
            "fold_mean_ci95": mean_ci(folds), "dots_per_fold": counts,
            "pooled_T": round(sum(p.T for p in parts), 2),
            "pooled_S": round(sum(p.S for p in parts), 2),
            "pooled_M": round(sum(p.M for p in parts), 2),
            "pooled_G": int(sum(p.G for p in parts)),
            "spacing_px": args.spacing, "n_dots_total_budget": args.n_dots}


def mode_build3(args) -> dict:
    fp = footprint()
    cat = np.nan_to_num(read1(CAT), nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat)
    surf, audit = load_surface(fp)
    ref_idx = _ref_sample(fp)
    refs = _band_refs(ref_idx, surf)
    rng = np.random.default_rng(SEED + 7)
    pos_idx = np.flatnonzero(cat)
    neg_pool = np.flatnonzero(fp & (dcat > 5.0))
    neg_idx = rng.choice(neg_pool, size=min(3 * pos_idx.size, neg_pool.size), replace=False)
    idx = np.r_[pos_idx, neg_idx]
    y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
    X = _ctx_matrix(idx, refs, surf)
    clf = _train_hgb(X, y)
    train_auc = round(auc(clf.predict_proba(X[pos_idx.size * 0:pos_idx.size])[:, 1],
                            clf.predict_proba(X[pos_idx.size:])[:, 1]), 4) if False else None
    del X
    sup = _predict_grid_hgb(clf, refs, surf, fp)
    np.save(ROOT / "work/denovo_hgbctx_surface_f32.npy", sup)
    eligible = fp & (dcat > 3.0)
    dots = DN.greedy_spaced(sup, eligible, args.n_dots, spacing_px=args.spacing)
    assert int(dots.sum()) == args.n_dots, f"placed {int(dots.sum())}"
    arr = np.where(fp, dots.astype(np.float32), np.float32(np.nan))
    outdir = ROOT / "releases"; outdir.mkdir(exist_ok=True)
    stem_tmp = f"gems91-denovo-hgbctx-{args.n_dots}dots-s{args.spacing}-{DATE}-tmp"
    p_nan_tmp, p_zero_tmp = outdir / f"{stem_tmp}-nan.tif", outdir / f"{stem_tmp}-zeros.tif"
    GIO.write_float32(p_nan_tmp, arr, encoding="nan", template=SAMPLE)
    GIO.write_float32(p_zero_tmp, arr, encoding="zeros", template=SAMPLE)
    sha_nan, sha_zero = GIO.sha256_file(p_nan_tmp), GIO.sha256_file(p_zero_tmp)
    stem = f"gems91-denovo-hgbctx-{args.n_dots}dots-s{args.spacing}-{DATE}-{sha_nan[:8]}"
    p_nan, p_zero = outdir / f"{stem}-nan.tif", outdir / f"{stem}-zeros.tif"
    p_nan_tmp.replace(p_nan); p_zero_tmp.replace(p_zero)
    rng2 = np.random.default_rng(SEED)
    sample_idx = rng2.choice(np.flatnonzero(fp), size=150_000, replace=False)
    uniq = {}
    registry = {"parent_r0": R0, "anc_d2_8": D28, "anc_solo_d2_8": SOLO,
                "anc_h19_5": ROOT / "data/registry/calib_h195_01922.tif",
                "anc_h19_4": ROOT / "data/registry/calib_h194_01894.tif",
                "anc_h16_1": ROOT / "data/registry/calib_h161_01855.tif",
                "anc_d1_5": ROOT / "data/registry/calib_d15_02477.tif"}
    for name, path in registry.items():
        other = GIO.dot_mask(read1(path))
        d_other = ndi.distance_transform_edt(~other)
        uniq[name] = {"surface_spearman_sample": round(spearman_sample(sup, other.astype(np.float32), sample_idx), 4),
                      "pct_our_dots_within_3px": round(100.0 * float((d_other[dots] <= 3.0).mean()), 2),
                      "their_positive_px": int(other.sum())}
        del other, d_other
    sgmc = np.nan_to_num(read1(SGMC), nan=0.0) > 0
    sgmc_off = sgmc & (dcat > 3.0) & fp
    ctr = {}
    for name, dd in {"hgbctx": dots, "r0": GIO.dot_mask(read1(R0))}.items():
        p = D.components(dd.astype(np.float64), sgmc_off.astype(np.float64))
        ctr[name] = {"sgmc_off_dti_PROXY": round(p.score, 6), "T": round(p.T, 2),
                     "S": round(p.S, 2), "M": round(p.M, 2), "G": int(p.G)}
    out = {"id": stem, "method": "HGB-CTX HistGB on 19 sponsor-band percentiles + TRI3 percentile "
           "+ 8 mean11 contexts; trained on full catalogue vs dcat>5 negatives; "
           "greedy spaced emission >3px off catalogue",
           "features": _ctx_feature_names(),
           "n_dots": int(dots.sum()), "spacing_px": args.spacing,
           "min_dcat_px_RECEIPT": round(float(dcat[dots].min()), 4),
           "dots_on_catalogue_RECEIPT": int((dots & cat).sum()),
           "dot_set_digest": GIO.dot_digest(dots),
           "surface_sha256_f32": hashlib.sha256(sup.tobytes()).hexdigest(),
           "files": {"nan": {"file": p_nan.name, "sha256": sha_nan, "bytes": p_nan.stat().st_size},
                     "zeros": {"file": p_zero.name, "sha256": sha_zero, "bytes": p_zero.stat().st_size}},
           "uniqueness_vs_registry": uniq,
           "duplicate_rule": "rank-corr > 0.90 OR > 70% dots within 3px of one registry raster",
           "sgmc_control_report_only": {"truth_px_off_catalogue": int(sgmc_off.sum()), **ctr}}
    out["is_duplicate"] = any(v["surface_spearman_sample"] > 0.90 or v["pct_our_dots_within_3px"] > 70.0
                               for v in uniq.values())
    return out


if __name__ == "__main__":
    raise SystemExit(main())
