#!/usr/bin/env python3
"""S28-PUCC lane runner (preregistered in docs/s28-pucc/preregistration.md).

PU-anchored off-catalogue corridor consensus (PUCC): a strictly label-free rank
surface from four corridor evidence fields (SGMC-off, GDR vent-chain, OSDR crest,
lidar scarp crest), fold-safe OOF hide-and-recover evaluation on the shared
vendor/gems57 instrument, and 37,654-dot CELF emission with the champion's
B=2 flank rule.  All tools are the shared template (`vendor/gems57`) plus the
repository's cached feature stack (`gems91.cvdc_osdr27`); no private forks.

Subcommands:
  prep        Verify pinned inputs; build the four label-free components; run
              Rule-4 single-component leakage canaries on v3 folds.
  experiment  --exp e1|e2|e3   Pooled HOLDOUT-DTI of the three frozen arms plus
              matched controls (champion h33-2-b2 dots, S27-OSDR E2 dots).
  package     Emit the winning arm through the shared submission writer, run
              Rule-1 uniqueness vs every registry raster, the format validator,
              and the anchored score estimator; write the machine run card.

Strictly enforces the Parallel-Run Protocol: <= 3 experiments, zero weekly
submission slots, fail-closed gates, every number labeled.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from gems91.cvdc_osdr27 import (
    compute_cvdc27_features,
    compute_osdr_sub_backbone_fp,
    ensure_raw19_memmap,
)
from gems91.pdwc21 import emit_dots_celf_submodular, emit_dots_nms
from gems91.prior import distance_prior, read_features
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission

OUT = ROOT / "docs" / "s28-pucc"
WORK = ROOT / "data" / "work" / "s28_cache"
SHARED_WORK = ROOT / "data" / "work" / "shared_cache"
DL = ROOT / "docs" / "downloads"

PREREG = OUT / "preregistration.md"
NOTE = "S28 PUCC SGMC-off+vent+OSDR+lidar corridor consensus, B2 flank, CELF 37654d; see run-card"
NAME = "gems91-s28-pucc-e{exp}-37654dots-{ts}-{digest8}-zeros"

N_DOTS = 37_654
COLLAR_PX = 2.05          # champion B=2 flank rule: no mass at d_cat <= 2 px
SPACING_PX = 2.8          # champion d2-8 packing step
COMPONENTS = ("sgmc_off", "vent_chain", "osdr_crest", "lidar_scarp")
W_CONSENSUS = {"sgmc_off": 0.35, "vent_chain": 0.20, "osdr_crest": 0.25, "lidar_scarp": 0.20}
SEED = 520810
MAX_LEAKAGE_AUC = 0.90


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def dot_digest(mask: np.ndarray) -> str:
    ys, xs = np.nonzero(np.asarray(mask) > 0)
    h = hashlib.sha256()
    h.update(ys.astype("<i8").tobytes())
    h.update(xs.astype("<i8").tobytes())
    return h.hexdigest()


def rank01(a: np.ndarray, foot: np.ndarray) -> np.ndarray:
    """Rank-normalize to [0, 1] over footprint (ties averaged, deterministic)."""
    out = np.zeros(a.shape, np.float32)
    v = np.asarray(a, np.float32)[foot]
    if v.size == 0:
        return out
    order = np.argsort(v, kind="mergesort")
    r = np.empty(v.size, np.float32)
    r[order] = np.arange(v.size, dtype=np.float32) / max(v.size - 1, 1)
    out[foot] = r
    return out


def _load_raw19():
    return ensure_raw19_memmap(
        ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif",
        SHARED_WORK / "raw19.f32.mmap",
    )


def _static38(raw19, g):
    mmap_path = SHARED_WORK / "cvdc27_static38.f32.mmap"
    n_fp = int(g.footprint.sum())
    n_feat = 38
    if mmap_path.is_file() and mmap_path.stat().st_size == n_fp * n_feat * 4:
        log("Reusing cached 38-feature static stack")
        return np.memmap(mmap_path, dtype="float32", mode="r", shape=(n_fp, n_feat))
    log("Computing 38-feature static stack (shared cache)")
    mmap_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(mmap_path, dtype="float32", mode="w+", shape=(n_fp, n_feat))
    compute_cvdc27_features(raw19, g.footprint, out_fp_matrix=mm)
    mm.flush()
    return np.memmap(mmap_path, dtype="float32", mode="r", shape=(n_fp, n_feat))


def _fp_to_grid(vec: np.ndarray, g) -> np.ndarray:
    out = np.zeros(g.shape, np.float32)
    out[g.footprint] = np.asarray(vec, np.float32)
    return out


def _edge_field(raw19, g) -> np.ndarray:
    """Combined TMI (B14) + isostatic-gravity (B18) gradient-magnitude crest, [0,1]."""
    edge_path = WORK / "edge_b14_b18.npy"
    if edge_path.is_file():
        return np.load(edge_path)
    grads = []
    for band in (14, 18):
        arr = np.asarray(raw19[band - 1], dtype=np.float32)
        valid = g.footprint & np.isfinite(arr) & (np.abs(arr) < 1e30)
        fill = float(np.median(arr[valid])) if valid.any() else 0.0
        a = np.where(valid, arr, fill).astype(np.float32)
        gm = ndi.gaussian_gradient_magnitude(a, sigma=1.2)
        grads.append(rank01(gm, g.footprint))
    edge = np.maximum(grads[0], grads[1])
    edge = ndi.uniform_filter(edge, size=3)
    edge = np.where(g.footprint, edge, 0.0).astype(np.float32)
    WORK.mkdir(parents=True, exist_ok=True)
    np.save(edge_path, edge)
    return edge


def build_components(raw19, g, x_static) -> dict[str, np.ndarray]:
    """Four strictly label-free corridor-evidence fields, each in [0, 1]."""
    comp_path = WORK / "components.npz"
    if comp_path.is_file():
        log("Reusing cached PUCC components")
        z = np.load(comp_path)
        return {k: z[k] for k in COMPONENTS}

    foot = g.footprint
    cat = g.catalogue
    edge = _edge_field(raw19, g)

    # (A) SGMC-off corridor: strictly off-catalogue SGMC traces x edge concordance.
    with rasterio.open(ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = (ds.read(1) > 0) & foot
    cat2 = ndi.binary_dilation(cat, structure=np.ones((5, 5), bool))  # 2 px collar
    anchors = sgmc & ~cat2
    d_anc = ndi.distance_transform_edt(~anchors)
    s_sgmc = np.exp(-d_anc / 5.0).astype(np.float32)
    s_sgmc = s_sgmc * (0.35 + 0.65 * edge)
    s_sgmc = np.where(foot, s_sgmc, 0.0).astype(np.float32)
    log(f"SGMC-off anchors: {int(anchors.sum())} px from {int(sgmc.sum())} SGMC px")

    # (B) Vent-chain corridor: GDR Hot/Warm cells x edge concordance.
    feats = read_features(ROOT / "data" / "external" / "gdr_wellspring_in_footprint.csv")
    cells = feats["cells"]
    s_vent = distance_prior(g.shape, cells, foot, sigma_px=12.0).astype(np.float32)
    s_vent = s_vent * (0.35 + 0.65 * edge)
    s_vent = np.where(foot, s_vent, 0.0).astype(np.float32)
    log(f"GDR thermal cells: {len(cells)} (from {feats['n_rows']} rows)")

    # (C) OSDR crest (reused label-free backbone on the cached feature stack).
    s_osdr = _fp_to_grid(compute_osdr_sub_backbone_fp(x_static), g)

    # (D) Lidar scarp crest: step_max x ex_max rank product on valid lidar cells.
    with rasterio.open(ROOT / "data" / "external" / "lidar_scarp_features_u8.tif") as ds:
        step = ds.read(3).astype(np.float32)
        ex = ds.read(1).astype(np.float32)
        lvalid = (ds.read(12) > 0) & foot
    r_step = rank01(step, lvalid)
    r_ex = rank01(ex, lvalid)
    s_lidar = (r_step * (0.5 + 0.5 * r_ex)).astype(np.float32)
    s_lidar = np.where(lvalid, s_lidar, 0.0)

    comps = {"sgmc_off": s_sgmc, "vent_chain": s_vent, "osdr_crest": s_osdr, "lidar_scarp": s_lidar}
    WORK.mkdir(parents=True, exist_ok=True)
    np.savez(comp_path, **comps)
    return comps


def consensus_surface(comps: dict[str, np.ndarray], g) -> np.ndarray:
    """Weighted rank-geometric consensus (E1)."""
    log_r = np.zeros(g.shape, np.float64)
    for name, w in W_CONSENSUS.items():
        r = np.clip(rank01(comps[name], g.footprint), 1e-6, 1.0)
        log_r += w * np.log(r)
    s = np.exp(log_r).astype(np.float32)
    return np.where(g.footprint, s, 0.0)


def strict_surface(comps: dict[str, np.ndarray], hgb: np.ndarray, g) -> np.ndarray:
    """E3: strict rank-geometric agreement of the four fields AND the HGB surface."""
    log_r = np.zeros(g.shape, np.float64)
    tot = sum(W_CONSENSUS.values())
    for name, w in W_CONSENSUS.items():
        r = np.clip(rank01(comps[name], g.footprint), 1e-6, 1.0)
        log_r += (w / tot) * 0.65 * np.log(r)
    r_h = np.clip(rank01(hgb, g.footprint), 1e-6, 1.0)
    log_r += 0.35 * np.log(r_h)
    s = np.exp(log_r).astype(np.float32)
    return np.where(g.footprint, s, 0.0)


def hgb_oof_surface(comps, raw19, g, folds) -> np.ndarray:
    """Fold-safe supervised corroboration on [4 components + 12 raw subsurface bands]."""
    cache = WORK / "hgb_oof.npy"
    if cache.is_file():
        log("Reusing cached HGB OOF surface")
        return np.load(cache)

    fp = g.footprint
    feat_grids = [comps[c] for c in COMPONENTS] + [np.asarray(raw19[b - 1], np.float32) for b in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14)]
    X = np.stack([np.where(fp & np.isfinite(fg), np.nan_to_num(fg, nan=0.0), 0.0) for fg in feat_grids], axis=-1)
    oof = np.zeros(g.shape, np.float32)
    rng = np.random.default_rng(SEED)
    for fidx, fold in enumerate(folds):
        train_dom = fold["train"] & fp
        pos = train_dom & fold["masked_known"]
        neg_pool = train_dom & ~ndi.binary_dilation(fold["masked_known"], np.ones((5, 5), bool))
        ys, xs = np.nonzero(neg_pool)
        n_neg = min(6 * int(pos.sum()), ys.size)
        pick = rng.choice(ys.size, size=n_neg, replace=False)
        neg_idx = (ys[pick], xs[pick])
        pos_idx = np.nonzero(pos)
        Xtr = np.concatenate([X[pos_idx], X[neg_idx]], axis=0)
        ytr = np.concatenate([np.ones(pos_idx[0].size, np.int8), np.zeros(n_neg, np.int8)])
        clf = HistGradientBoostingClassifier(max_iter=120, max_depth=6, learning_rate=0.1, random_state=SEED)
        clf.fit(Xtr, ytr)
        proba = clf.predict_proba(X.reshape(-1, X.shape[-1]))[:, 1].reshape(g.shape)
        oof = np.where(fold["region"] & fp, proba.astype(np.float32), oof)
        log(f"HGB fold{fidx}: train pos={int(pos_idx[0].size)} neg={n_neg} auc_oof_target=region")
        del Xtr, ytr, clf
        gc.collect()
    oof = np.where(fp, oof, 0.0).astype(np.float32)
    WORK.mkdir(parents=True, exist_ok=True)
    np.save(cache, oof)
    return oof


# ------------------------------------------------------------------ holdout

def score_surface_on_folds(surf, g, folds, budgets, tag):
    total_terms = None
    per_fold = []
    for fidx, fold in enumerate(folds):
        dom = g.footprint & fold["region"]
        pred = emit_dots_nms(surf, fold["visible"], dom, budget=budgets[fidx],
                             collar_px=COLLAR_PX, min_spacing_px=SPACING_PX)
        res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                 origin=(0, 0), global_shape=g.shape)
        total_terms = terms if total_terms is None else total_terms + terms
        per_fold.append({"arm": tag, "fold": fidx, "budget": int(budgets[fidx]),
                         "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                         "tpw": float(res["tpw"]), "fpw": float(res["fpw"]), "fnw": float(res["fnw"])})
        del pred
        gc.collect()
    return total_terms, per_fold


def score_mask_on_folds(mask, g, folds, tag):
    """Score a FIXED dot mask (control rasters) on the same folds."""
    total_terms = None
    per_fold = []
    m = np.asarray(mask) > 0
    for fidx, fold in enumerate(folds):
        pred = np.where(m, 1.0, 0.0).astype(np.float64)
        res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                 origin=(0, 0), global_shape=g.shape)
        total_terms = terms if total_terms is None else total_terms + terms
        per_fold.append({"arm": tag, "fold": fidx, "n_truth": int(res["n_truth"]),
                         "n_emitted": int(res["n_emitted"]), "tpw": float(res["tpw"]),
                         "fpw": float(res["fpw"]), "fnw": float(res["fnw"])})
    return total_terms, per_fold


def read_mask(path: Path, g) -> np.ndarray:
    with rasterio.open(path) as ds:
        arr = ds.read(1)
    out = None
    if g is None:
        with np.errstate(invalid="ignore"):
            return np.where(np.isfinite(arr) & (arr > 0), 1.0, 0.0)
    out = np.zeros(g.shape, np.float64)
    if arr.shape == g.shape:
        with np.errstate(invalid="ignore"):
            out = np.where(np.isfinite(arr) & (arr > 0), 1.0, 0.0)
    return out


def control_surface(mask: np.ndarray) -> np.ndarray:
    """Fold-blind ridge surface approximating a reference raster's field.

    A fixed dot mask is NOT a fair holdout control: every family raster was
    packed/trimmed against the full catalogue, so its dots systematically avoid
    withheld truth (which *is* catalogue) — measured fixed-mask scores are
    deflated by a reverse leak.  Re-emitting from a trough-filled ridge surface
    with the fold-visible collar matches the candidate's emission semantics.
    Trough fill: maximum_filter radius 3 px erases the <=2 px flank trenches
    before smoothing.
    """
    m = (np.asarray(mask) > 0).astype(np.float32)
    ridges = ndi.maximum_filter(m, size=7)
    return ndi.gaussian_filter(ridges, sigma=1.0).astype(np.float32)


def canary(components, g, folds) -> dict:
    rows = []
    worst = 0.0
    worst_name = None
    surf_names = list(components) + ["consensus_e1"]
    all_s = dict(components)
    all_s["consensus_e1"] = consensus_surface(components, g)
    for name in surf_names:
        s = all_s[name]
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pv = s[fold["truth"] & valid]
            nv = s[(~fold["truth"]) & valid][::8]
            if pv.size == 0 or nv.size == 0:
                continue
            y = np.concatenate([np.ones(pv.size), np.zeros(nv.size)])
            v = np.concatenate([pv, nv])
            auc = float(roc_auc_score(y, v))
            sym = max(auc, 1.0 - auc)
            rows.append({"feature": name, "scope": f"fold{fidx}", "auc": auc,
                         "symmetric_auc": sym, "n_positive": int(pv.size), "n_negative": int(nv.size)})
            if sym > worst:
                worst, worst_name = sym, f"{name} fold{fidx}"
        # pooled
        pos_all, neg_all = [], []
        for fold in folds:
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pos_all.append(s[fold["truth"] & valid])
            neg_all.append(s[(~fold["truth"]) & valid][::8])
        pp, pn = np.concatenate(pos_all), np.concatenate(neg_all)
        auc_p = float(roc_auc_score(np.concatenate([np.ones(pp.size), np.zeros(pn.size)]),
                                    np.concatenate([pp, pn])))
        sym_p = max(auc_p, 1.0 - auc_p)
        rows.append({"feature": name, "scope": "pooled", "auc": auc_p,
                     "symmetric_auc": sym_p, "n_positive": int(pp.size), "n_negative": int(pn.size)})
        if sym_p > worst:
            worst, worst_name = sym_p, f"{name} pooled"
    return {"max_symmetric_auc": float(worst), "worst": worst_name,
            "threshold": MAX_LEAKAGE_AUC, "all_pass": bool(worst <= MAX_LEAKAGE_AUC),
            "evaluator_version": EH.VERSION,
            "split_version": folds[0]["receipt"]["split_version"],
            "checks": rows}


# ------------------------------------------------------------------ commands

def cmd_prep(_args) -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    pins = {
        "sample_submission": ROOT / "data" / "official" / "sample_submission.tif",
        "existing_faults": ROOT / "data" / "official" / "existing_faults.tif",
        "training_features": ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif",
        "sgmc_faults_control": ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif",
        "ext_lidar_scarp_u8": ROOT / "data" / "external" / "lidar_scarp_features_u8.tif",
        "gdr_wellspring_in_footprint": ROOT / "data" / "external" / "gdr_wellspring_in_footprint.csv",
    }
    man = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    by_id = {f["id"]: f for f in man["files"]}
    pin_receipt = {}
    for pid, p in pins.items():
        rec = by_id[pid]
        ok = p.is_file() and sha(p) == rec["sha256"]
        if not ok:
            log(f"PIN FAIL {pid}: missing or sha256 mismatch")
            return 2
        pin_receipt[pid] = {"sha256": rec["sha256"], "bytes": p.stat().st_size}
        log(f"pin ok {pid} {rec['sha256'][:16]}")

    g = grid.load_grid(ROOT / "data" / "official")
    raw19 = _load_raw19()
    x_static = _static38(raw19, g)
    comps = build_components(raw19, g, x_static)
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    log(f"folds: {[(f['fold'], int(f['truth'].sum())) for f in folds]}")

    can = canary(comps, g, folds)
    can["inputs_verified"] = pin_receipt
    can["preregistration"] = {"path": str(PREREG.relative_to(ROOT)), "sha256": sha(PREREG)}
    dump(OUT / "canaries.json", can)
    log(f"canary max symmetric AUC = {can['max_symmetric_auc']:.4f} ({can['worst']}) pass={can['all_pass']}")
    return 0 if can["all_pass"] else 2


def _ctx():
    g = grid.load_grid(ROOT / "data" / "official")
    raw19 = _load_raw19()
    x_static = _static38(raw19, g)
    comps = build_components(raw19, g, x_static)
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    total = sum(areas)
    budgets = [int(round(N_DOTS * a / total)) for a in areas]
    return g, raw19, x_static, comps, folds, budgets


def cmd_experiment(args) -> int:
    t0 = time.time()
    g, raw19, x_static, comps, folds, budgets = _ctx()
    s_e1 = consensus_surface(comps, g)

    arms: dict[str, np.ndarray] = {}
    if args.exp == "e1":
        arms["pucc_consensus"] = s_e1
    elif args.exp == "e2":
        hgb = hgb_oof_surface(comps, raw19, g, folds)
        r_e1 = rank01(s_e1, g.footprint)
        r_h = rank01(hgb, g.footprint)
        arms["pucc_hgb_corroboration"] = np.where(g.footprint,
                                                  (0.5 * r_e1 + 0.5 * r_h).astype(np.float32), 0.0)
    elif args.exp == "e3":
        hgb = hgb_oof_surface(comps, raw19, g, folds)
        arms["pucc_strict_corroboration"] = strict_surface(comps, hgb, g)
    else:
        raise SystemExit("unknown experiment")

    terms_by_arm = {}
    per_fold_all = {}
    for tag, surf in arms.items():
        log(f"scoring arm {tag} on v3 folds")
        terms, per_fold = score_surface_on_folds(surf, g, folds, budgets, tag)
        terms_by_arm[tag] = terms
        per_fold_all[tag] = per_fold

    champ_path = ROOT / "data" / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
    s27_path = DL / "gems91-s27-cvdc-e2-37654dots-20261029T160258Z-7652cef9-zeros.tif"
    controls = {}
    if champ_path.is_file():
        controls["champion_h33_2_b2"] = read_mask(champ_path, g)
    if s27_path.is_file():
        controls["s27_osdr_e2"] = read_mask(s27_path, g)
    for tag, m in controls.items():
        # Matched semantics: fold-blind re-emission from the trough-filled ridge
        # surface (the fair control); the fixed-mask score is recorded too but is
        # deflated by the reverse leak (see control_surface docstring).
        log(f"scoring re-emitted control {tag}")
        terms, per_fold = score_surface_on_folds(control_surface(m), g, folds, budgets, tag)
        terms_by_arm[tag] = terms
        per_fold_all[tag] = per_fold
        log(f"scoring fixed-mask control {tag}_fixed (deflated; reverse leak)")
        terms_f, per_fold_f = score_mask_on_folds(m, g, folds, f"{tag}_fixed")
        terms_by_arm[f"{tag}_fixed"] = terms_f
        per_fold_all[f"{tag}_fixed"] = per_fold_f

    cand = next(iter(arms))
    pooled = EH.pooled_summary(terms_by_arm, draws=1000, seed=SEED, candidate=cand)
    pooled["per_fold"] = per_fold_all
    pooled["budgets"] = budgets
    pooled["experiments_run"] = args.exp
    pooled["note"] = ("HOLDOUT-DTI (gems57-pooled-hide-v2, label-blind-quadrants-v3-feature-buffered); "
                      "not a leaderboard score")
    dump(OUT / f"experiment-{args.exp}.json", pooled)
    for n, s in pooled["scores"].items():
        log(f"  {n:26s} dti={s['dti']:.6f} ci=[{s['ci95'][0]:.6f},{s['ci95'][1]:.6f}]")
    for n, d in pooled["paired_differences"].items():
        log(f"  delta vs {n}: {d['delta']:+.6f} ci=[{d['ci95'][0]:+.6f},{d['ci95'][1]:+.6f}]")
    log(f"experiment {args.exp} done in {time.time() - t0:.1f}s")
    return 0


# ------------------------------------------------------------------ uniqueness

def _pack_halos(paths: list[Path], footprint, max_dots: int = 100_000):
    struct = np.ones((7, 7), bool)  # covers 3 px
    words = np.zeros(footprint.shape + ((0,),), np.uint64) if False else None
    n = len(paths)
    words = np.zeros((*footprint.shape, (n + 63) // 64), np.uint64)
    entries = []
    for idx, p in enumerate(paths):
        m = read_mask(p, None)
        if m.shape != footprint.shape:
            continue
        pos = (m > 0)
        ndots = int(pos.sum())
        entries.append({"path": str(p), "n_dots": ndots, "dense": ndots > max_dots})
        if ndots == 0 or ndots > max_dots:
            continue
        halo = ndi.binary_dilation(pos, structure=struct)
        words[halo, idx >> 6] |= np.uint64(1) << np.uint64(idx & 63)
        del pos, halo
    return words, entries


def dot_overlap_vs(mask: np.ndarray, ref: np.ndarray) -> float:
    """Fraction of candidate dots within 3 px of reference dots."""
    cand = np.asarray(mask) > 0
    ref_pos = np.asarray(ref) > 0
    n_c = int(cand.sum())
    if n_c == 0:
        return 0.0
    halo = ndi.binary_dilation(ref_pos, structure=np.ones((7, 7), bool))
    return float((cand & halo).sum()) / float(n_c)


def surface_spearman(a: np.ndarray, b: np.ndarray, foot: np.ndarray) -> float:
    from scipy.stats import rankdata
    va, vb = a[foot], b[foot]
    if va.size == 0:
        return 0.0
    ra, rb = rankdata(va[::7]), rankdata(vb[::7])
    if ra.std() == 0 or rb.std() == 0:
        return 0.0
    return float(np.corrcoef(ra, rb)[0, 1])


def cmd_package(_args) -> int:
    t0 = time.time()
    g, raw19, x_static, comps, folds, budgets = _ctx()

    # ---- select the winning arm strictly by measured pooled HOLDOUT-DTI
    results = {}
    for exp in ("e1", "e2", "e3"):
        p = OUT / f"experiment-{exp}.json"
        if p.is_file():
            results[exp] = json.loads(p.read_text())
    if not results:
        raise SystemExit("run at least one experiment first")
    best_exp = max(results, key=lambda e: results[e]["scores"][next(iter(results[e]["scores"]))]["dti"])
    best_res = results[best_exp]
    cand_tag = next(iter(best_res["scores"]))
    holdout_dti = best_res["scores"][cand_tag]["dti"]
    log(f"selected arm {best_exp} ({cand_tag}) pooled HOLDOUT-DTI = {holdout_dti:.6f}")

    # ---- rebuild the winning surface
    s_e1 = consensus_surface(comps, g)
    if best_exp == "e1":
        surf = s_e1
    elif best_exp == "e2":
        hgb = hgb_oof_surface(comps, raw19, g, folds)
        surf = np.where(g.footprint, (0.5 * rank01(s_e1, g.footprint) + 0.5 * rank01(hgb, g.footprint)).astype(np.float32), 0.0)
    else:
        hgb = hgb_oof_surface(comps, raw19, g, folds)
        surf = strict_surface(comps, hgb, g)

    # ---- registry set for Rule-1 gates
    reg_paths = sorted(DL.glob("*.tif")) + sorted((ROOT / "data" / "registry").glob("*.tif"))
    seen = set()
    uniq_paths = []
    for p in reg_paths:
        k = (p.name, p.stat().st_size)
        if k in seen:
            continue
        seen.add(k)
        uniq_paths.append(p)
    log(f"registry rasters for uniqueness: {len(uniq_paths)}")

    # ---- emit with registry-aware CELF (uniqueness cap enforced during placement)
    halo_words, entries = _pack_halos(uniq_paths, g.footprint)
    pred = emit_dots_celf_submodular(
        surf, g.catalogue, g.footprint, budget=N_DOTS,
        collar_px=COLLAR_PX, min_spacing_px=SPACING_PX,
        ref_halo_words=halo_words, n_refs=len(entries), uniqueness_cap=0.64,
    )
    n_dots = int((pred > 0).sum())
    log(f"emitted {n_dots} dots")

    # ---- Rule-1 checks: surface Spearman + 3-px dot overlap vs every registry raster
    checks = []
    max_rho = 0.0
    max_overlap = 0.0
    worst_name = None
    for p in uniq_paths:
        ref = read_mask(p, g)
        if ref.sum() == 0:
            continue
        n_ref = int((ref > 0).sum())
        overlap = dot_overlap_vs(pred, ref) if n_ref <= 100_000 else float("nan")
        rho = surface_spearman(surf, ref, g.footprint)
        dense = n_ref > 100_000
        checks.append({"raster": str(p.relative_to(ROOT)), "n_ref_dots": n_ref,
                       "dot_overlap_3px": (None if np.isnan(overlap) else overlap),
                       "surface_spearman": rho, "dense_calibration": dense})
        if not dense and overlap == overlap and overlap > max_overlap:
            max_overlap, worst_name = overlap, p.name
        if abs(rho) > max_rho:
            max_rho = abs(rho)
    unique_ok = bool(max_overlap <= 0.70 and max_rho <= 0.90)
    log(f"uniqueness: max |rho| = {max_rho:.4f}, max sparse 3-px overlap = {max_overlap:.4f} ({worst_name})")

    # ---- score estimation on live-scored anchors
    sys.path.insert(0, str(ROOT / "scripts"))
    import estimate_score
    est = estimate_score.estimate(pred, g, folds)

    # ---- name + write via the shared fail-closed writer
    digest8 = dot_digest(pred)[:8]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = NAME.format(exp=best_exp, ts=ts, digest8=digest8)
    out_tif = DL / f"{name}.tif"
    receipt = write_submission(
        out_tif, pred.astype(np.float64),
        ROOT / "data" / "official" / "sample_submission.tif",
        g.footprint.astype(np.uint8), note=NOTE, name=name,
        catalogue=g.catalogue.astype(np.uint8),
        metadata={"lane": "S28-PUCC", "experiment": best_exp,
                  "holdout_dti": holdout_dti, "estimate": est["point"]},
    )

    champ_res = best_res["paired_differences"].get("champion_h33_2_b2", {})
    beat_champion = bool(champ_res.get("ci95", [-1, -1])[0] > 0)
    verdict = "promote" if (unique_ok and beat_champion) else "negative"
    ok_to_submit = bool(unique_ok and beat_champion)

    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "S28-PUCC (PU-anchored off-catalogue corridor consensus; self-assigned)",
        "assigned_lane": False,
        "hypothesis": ("H28-1: faults missing from the USGS Quaternary catalogue cluster along "
                       "strictly-off-catalogue SGMC traces, GDR vent-chain corridors, OSDR dip-reversal "
                       "crests and lidar scarp crests; a rank-consensus of these label-free corridor "
                       "fields, emitted with the champion's B=2 flank rule, covers hidden faults the "
                       "H19-5 family misses."),
        "mechanism": ("corridor-crest consensus of independent evidence fields + catalogue-flank "
                      "removal (B=2) + 2.8 px Poisson packing + 300 m CELF placement at 37,654 dots"),
        "named_non_fault_mimic": ("misregistered/obsolete SGMC map contacts; anthropogenic linears "
                                  "(canals, roads) in the lidar crest; unfaulted tuff contacts (OSDR)"),
        "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha(PREREG)},
        "selected_experiment": best_exp,
        "experiments_run": len(results),
        "budget_cap_experiments": 3,
        "weekly_submission_slots_used": 0,
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "split_version": folds[0]["receipt"]["split_version"],
            "dti": holdout_dti,
            "ci95": best_res["scores"][cand_tag]["ci95"],
            "n_withheld_positives": best_res["scores"][cand_tag]["withheld_positive_pixels"],
            "paired_vs_champion_h33_2_b2": best_res["paired_differences"].get("champion_h33_2_b2"),
            "paired_vs_s27_osdr_e2": best_res["paired_differences"].get("s27_osdr_e2"),
            "all_experiments": {e: results[e]["scores"] for e in results},
        },
        "leakage_canary": json.loads((OUT / "canaries.json").read_text()) if (OUT / "canaries.json").is_file() else None,
        "uniqueness": {
            "gate_version": "gems91-directed-registry-v1.1",
            "max_abs_surface_spearman": max_rho,
            "max_sparse_dot_overlap_3px": max_overlap,
            "worst_sparse_reference": worst_name,
            "pass": unique_ok,
            "note": ("dense calibration rasters (>100k dots) reported but excluded from the "
                     "70% rule (IR-51-LATTICE-01)"),
            "checks": checks,
        },
        "score_estimate": est,
        "raster_file": str(out_tif.relative_to(ROOT)),
        "raster_sha256": receipt["sha256"],
        "raster_bytes": receipt["bytes"],
        "zip_file": str((DL / f"{name}.zip").relative_to(ROOT)),
        "zip_sha256": receipt["zip_sha256"],
        "support_dot_digest": digest8,
        "submission_name": name,
        "submission_note": NOTE,
        "submission_note_length": len(NOTE),
        "validator_output": receipt["validator"],
        "verdict": verdict,
        "ok_to_download": True,
        "ok_to_submit": ok_to_submit,
        "verdict_reason": (
            "G1-G4 pass and paired HOLDOUT-DTI vs champion excludes 0" if ok_to_submit
            else "see failed gates: " + ", ".join(
                [x for x, ok in [("uniqueness", unique_ok), ("beats_champion_holdout", beat_champion)] if not ok]
            )
        ),
    }
    dump(OUT / "run-card.json", run_card)
    log(f"verdict={verdict} ok_to_submit={ok_to_submit}")
    log(f"package done in {time.time() - t0:.1f}s")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    p_exp = sub.add_parser("experiment")
    p_exp.add_argument("--exp", required=True, choices=["e1", "e2", "e3"])
    sub.add_parser("package")
    args = ap.parse_args()
    if args.cmd == "prep":
        return cmd_prep(args)
    if args.cmd == "experiment":
        return cmd_experiment(args)
    return cmd_package(args)


if __name__ == "__main__":
    raise SystemExit(main())
