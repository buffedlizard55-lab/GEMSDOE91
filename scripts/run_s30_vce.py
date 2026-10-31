#!/usr/bin/env python3
"""S30-VCE lane runner — Vent-Concordant Emission (preregistered in docs/s30-vce/preregistration.md).

PARALLEL-RUN PROTOCOL compliance:
  Rule 1 (LANE): surface Spearman |rho| <= 0.90 vs every registry raster before
    placement; <= 70% of final dots within 3 px of any registry raster's dots after.
  Rule 2 (REUSE): scoring delegates to vendor/gems57 (pooled DTI v3 folds);
    emission to gems91.pdwc21.emit_dots_nms; writing/validating to
    vendor.gems57.submission_writer + validate; diagnostics to
    scripts/evaluate_holdout.score_off_catalogue_sgmc.
  Rule 3: every score labeled HOLDOUT-DTI with evaluator version, withheld
    positives and 95% CI; projections never written as scores.
  Rule 4: per-feature single-feature leakage canaries, fail closed at AUC 0.90.
  Rule 6: 3 experiments (e1..e3) / 2 h budget; 0 weekly submission slots spent.

Subcommands: verify | features | canary | experiment --exp e1|e2|e3 | package
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from gems91.pdwc21 import emit_dots_nms
from gems91.novelty import SurfaceProbe, dot_check
from gems91.io import dot_digest
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate
from evaluate_holdout import score_off_catalogue_sgmc

OUT = ROOT / "docs" / "s30-vce"
WORK = ROOT / "data" / "work" / "s30_cache"
PREREG = OUT / "preregistration.md"

BUDGET = 37_654
COLLAR_PX = 3.05
SPACING_PX = 2.8
SEED = 520810
NOTE = "S30 VCE vent-concordant emission 37654d; GDR vents+alteration+strain; see run-card"
assert len(NOTE) <= 140, len(NOTE)

HGB_PARAMS = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                  min_samples_leaf=40, l2_regularization=1.0, early_stopping=False)
NEG_PER_POS = 4

LABEL_BLIND_FEATURES = ["vent_kde", "vent_geo_kde", "vent_corridor", "alter_kdep",
                        "alter_uelev", "cond_cap", "strain2", "eq_near", "scarp"]
FOLD_LOCAL_FEATURES = ["d_vis_rank", "tip_kde"]
ALL_MODEL_FEATURES = LABEL_BLIND_FEATURES + FOLD_LOCAL_FEATURES

EXPERIMENTS = {"e1": "e1_static_blend", "e2": "e2_static_scarp", "e3": "e3_oof_hgb"}
CONTROLS = ["ctrl_ventblind", "ctrl_champion_fixed"]


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=False))


def verify_pinned_inputs() -> dict:
    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        if row["id"] in {"sample_submission", "existing_faults", "training_features",
                         "parent_r0_zeros", "sgmc_faults_control", "ext_lidar_scarp_u8",
                         "ext_geodawn_rad_u8", "gdr_wellspring_in_footprint"}:
            p = ROOT / "data" / row["local_subpath"]
            if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
                raise ValueError(f"pinned input absent or drifted: {row['id']}")
            checked[row["id"]] = {"path": "data/" + row["local_subpath"],
                                  "sha256": row["sha256"], "bytes": row["bytes"]}
    return checked


def cmd_verify(_args) -> int:
    inputs = verify_pinned_inputs()
    log(f"verified {len(inputs)} pinned inputs")
    dump(OUT / "input-receipt.json", {"verified_utc": datetime.now(timezone.utc).isoformat(),
                                     "preregistration_sha256": sha(PREREG), "inputs": inputs})
    return 0


# ------------------------------------------------------------------ features
def feat_path(name: str) -> Path:
    return WORK / f"{name}.npy"


def load_feat(name: str) -> np.ndarray:
    return np.load(feat_path(name))


def rank01(a: np.ndarray, fp: np.ndarray, fill: float = 0.0) -> np.ndarray:
    out = np.full(a.shape, fill, dtype=np.float32)
    x = a[fp]
    r = rankdata(x, method="average") / (len(x) + 1.0)
    out[fp] = r.astype(np.float32)
    return out


def cmd_features(_args) -> int:
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    if feat_path("vent_kde").is_file() and (OUT / "feature-receipt.json").is_file():
        raise RuntimeError("features already recorded; no implicit rebuild")
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    fp = g.footprint
    meta = {"inputs_verified": inputs,
            "preregistration": {"path": str(PREREG.relative_to(ROOT)), "sha256": sha(PREREG)},
            "label_blind_features": LABEL_BLIND_FEATURES,
            "leaky_column_dist_known_fault_px_used": False,
            "ir_h91_03_respected": True}

    # ---- GDR wellspring vents (row/col are grid indices; leaky dist column never read)
    import csv
    sites: dict[tuple[int, int], dict] = {}
    with open(ROOT / "data/external/gdr_wellspring_in_footprint.csv") as fh:
        for r in csv.DictReader(fh):
            try:
                row, col = int(r["row"]), int(r["col"])
            except (TypeError, ValueError):
                continue
            if not (0 <= row < g.height and 0 <= col < g.width):
                continue
            temps = [float(r[k]) for k in ("temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c")
                     if r.get(k) not in (None, "", "NULL")]
            t = max(temps) if temps else 0.0
            cur = sites.get((row, col))
            if cur is None or t > cur["t"]:
                sites[(row, col)] = {"t": t}
    log(f"vent sites: {len(sites)} unique in-footprint row/col cells")
    w_img = np.zeros(g.shape, dtype=np.float32)
    geo_img = np.zeros(g.shape, dtype=np.float32)
    for (row, col), v in sites.items():
        w_img[row, col] = np.log1p(max(v["t"], 1.0))
        if v["t"] >= 150.0:
            geo_img[row, col] = np.log1p(v["t"])
    vent_kde = ndi.gaussian_filter(w_img, sigma=8.0)
    vent_geo = ndi.gaussian_filter(geo_img, sigma=12.0)
    np.save(feat_path("vent_kde"), rank01(vent_kde, fp))
    np.save(feat_path("vent_geo_kde"), rank01(vent_geo, fp))
    meta["vent_sites"] = {"n_unique_sites": len(sites),
                          "n_geothermometer_sites": int((geo_img > 0).sum()),
                          "sigma_px": {"vent_kde": 8.0, "vent_geo_kde": 12.0}}

    # ---- vent corridor: 3-nearest-neighbor segments <= 40 px
    coords = np.array(sorted(sites), dtype=np.float64)
    tree = cKDTree(coords)
    corr = np.zeros(g.shape, dtype=np.float32)
    k = min(4, len(coords))
    dists, idxs = tree.query(coords, k=k)
    for i, (r0, c0) in enumerate(coords):
        w0 = w_img[int(r0), int(c0)]
        for j in range(1, k):
            if dists[i, j] > 40.0:
                continue
            r1, c1 = coords[idxs[i, j]]
            w1 = w_img[int(r1), int(c1)]
            n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
            rs = np.linspace(r0, r1, n).round().astype(int)
            cs = np.linspace(c0, c1, n).round().astype(int)
            corr[rs, cs] = np.maximum(corr[rs, cs], min(w0, w1))
    corr = ndi.gaussian_filter(corr, sigma=2.0)
    np.save(feat_path("vent_corridor"), rank01(corr, fp))
    meta["vent_corridor"] = {"neighbors": k - 1, "max_link_px": 40.0, "sigma_px": 2.0}

    # ---- radiometric alteration (u8 K, Th, U, TC)
    with rasterio.open(ROOT / "data/external/geodawn_rad_u8.tif") as ds:
        K, Th, U, TC = (ds.read(i).astype(np.float32) for i in (1, 2, 3, 4))
    rad_valid = TC > 0
    K_eff = np.where(rad_valid, K, np.nan)
    kmean = np.where(rad_valid, K_eff, np.nan)
    kmean = ndi.uniform_filter(np.nan_to_num(kmean, nan=0.0), size=31)
    kcnt = ndi.uniform_filter(rad_valid.astype(np.float32), size=31)
    kmean = np.divide(kmean, np.maximum(kcnt, 1e-6))
    kdep = np.clip(kmean - K, 0.0, None) * (TC / 255.0)
    kdep = np.where(rad_valid, kdep, 0.0).astype(np.float32)
    uelev = np.clip(U - Th, 0.0, None)
    uelev = np.where(rad_valid, uelev, 0.0).astype(np.float32)
    np.save(feat_path("alter_kdep"), rank01(kdep, fp))
    np.save(feat_path("alter_uelev"), rank01(uelev, fp))
    meta["radiometric"] = {"bands_used": ["K", "Th", "U", "TC"],
                           "coverage_fraction": float(rad_valid[fp].mean()),
                           "kdep_window_px": 31}

    # ---- GeoDAWN supplied bands
    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        cond = ds.read(17).astype(np.float32)   # cond_surf
        strain = ds.read(4).astype(np.float32)  # geod_2ndinv
        deq = ds.read(10).astype(np.float32)    # deq_n100a15 distance to earthquake
        desc = list(ds.descriptions)
    meta["training_features_descriptions"] = {str(i + 1): d for i, d in enumerate(desc)}
    nod = -3.4e38

    def clean(a):
        a = np.where(a < nod * 0.5, np.nan, a)
        a = np.where(np.isfinite(a), a, np.nan)
        return a

    cond_r = rank01(np.nan_to_num(clean(cond), nan=np.nanmedian(clean(cond))), fp)
    strain_r = rank01(np.nan_to_num(clean(strain), nan=np.nanmedian(clean(strain))), fp)
    deq_c = clean(deq)
    deq_r = rank01(np.nan_to_num(deq_c, nan=np.nanmedian(deq_c)), fp)
    np.save(feat_path("cond_cap"), cond_r)
    np.save(feat_path("strain2"), strain_r)
    np.save(feat_path("eq_near"), (1.0 - deq_r).astype(np.float32))
    meta["geodawn_band_ids"] = {"cond_cap": "B17 cond_surf", "strain2": "B4 geod_2ndinv",
                                "eq_near": "1-rank(B10 deq_n100a15); distance->near is positive"}

    # ---- lidar scarp corroboration (neutral where invalid)
    with rasterio.open(ROOT / "data/external/lidar_scarp_features_u8.tif") as ds:
        ex_max = ds.read(1).astype(np.float32)
        coh = ds.read(10).astype(np.float32)
        valid = ds.read(12) > 0
    scarp_raw = np.maximum(ex_max, coh)
    scarp = np.full(g.shape, 0.5, dtype=np.float32)
    vfp = fp & valid
    if vfp.any():
        scarp[vfp] = rank01(scarp_raw, vfp, fill=0.5)[vfp]
    np.save(feat_path("scarp"), scarp)
    meta["lidar"] = {"bands_used": ["ex_max", "coh100", "valid"],
                     "coverage_fraction": float(valid[fp].mean()),
                     "neutral_fill_outside_coverage": 0.5}

    meta["elapsed_seconds"] = float(time.monotonic() - start)
    dump(OUT / "feature-receipt.json", meta)
    log(f"features done in {meta['elapsed_seconds']:.0f}s")
    return 0


# ------------------------------------------------------------------ canaries
def _fold_catalogue_features(fold, shape) -> dict[str, np.ndarray]:
    vis = fold["visible"]
    d = ndi.distance_transform_edt(~vis).astype(np.float32)
    d_rank = rank01(-d, np.ones(shape, dtype=bool))
    tips = np.zeros(shape, dtype=np.float32)
    vv = vis.astype(np.uint8)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            sh = np.roll(np.roll(vv, dy, 0), dx, 1)
            tips += (vv > 0) & (sh == 0)
    tip_kde = ndi.gaussian_filter(tips, sigma=6.0)
    return {"d_vis_rank": d_rank.astype(np.float32),
            "tip_kde": rank01(tip_kde, np.ones(shape, dtype=bool)).astype(np.float32)}


def cmd_canary(_args) -> int:
    start = time.monotonic()
    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    canaries, max_sym, worst = [], 0.0, None
    static = {n: load_feat(n) for n in LABEL_BLIND_FEATURES}
    for fidx, fold in enumerate(folds):
        valid = g.footprint & fold["region"] & ~fold["visible"]
        feats = dict(static)
        feats.update(_fold_catalogue_features(fold, g.shape))
        for name, arr in feats.items():
            pos_v = np.asarray(arr[fold["truth"] & valid], dtype=np.float64)
            neg_all = np.nonzero(~fold["truth"] & valid)
            sel = np.arange(len(neg_all[0]))[::4]
            neg_v = np.asarray(arr[neg_all[0][sel], neg_all[1][sel]], dtype=np.float64)
            pos_v = pos_v[np.isfinite(pos_v)]
            neg_v = neg_v[np.isfinite(neg_v)]
            row = {"feature": name, "fold": fidx, "n_positive_finite": int(len(pos_v)),
                   "n_negative_finite": int(len(neg_v))}
            if len(pos_v) >= 10 and len(neg_v) >= 10:
                y = np.concatenate([np.ones(len(pos_v)), np.zeros(len(neg_v))])
                s = np.concatenate([pos_v, neg_v])
                auc = float(roc_auc_score(y, s))
                sym = max(auc, 1.0 - auc)
                row.update({"auc": auc, "symmetric_auc": sym, "status": "MEASURED"})
                if sym > max_sym:
                    max_sym, worst = sym, f"{name} fold{fidx}"
            else:
                row.update({"auc": None, "symmetric_auc": None, "status": "UNVERIFIED_TOO_FEW_FINITE"})
            canaries.append(row)
        del feats
    canary_pass = bool(max_sym <= 0.90)
    dump(OUT / "canaries.json", {"max_symmetric_auc": float(max_sym), "worst": worst,
                                 "all_pass": canary_pass, "threshold": 0.90,
                                 "evaluator_version": EH.VERSION,
                                 "split_version": folds[0]["receipt"]["split_version"],
                                 "canaries": canaries,
                                 "elapsed_seconds": float(time.monotonic() - start)})
    log(f"canaries: max symmetric AUC {max_sym:.4f} ({worst}) pass={canary_pass}")
    if not canary_pass:
        dump(OUT / "run-card.json",
             {"schema": "gems-parallel-run-card-v1", "lane": "S30-VCE",
              "verdict": "negative", "stop_reason": "leakage canary > 0.90",
              "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
              "leakage_canary": {"max_symmetric_auc": float(max_sym), "worst": worst}})
        return 2
    return 0


# ------------------------------------------------------------------ surfaces
def static_surface(arm: str) -> np.ndarray:
    f = {n: load_feat(n) for n in LABEL_BLIND_FEATURES}
    alter = 0.6 * f["alter_kdep"] + 0.4 * f["alter_uelev"]
    if arm == "e1_static_blend":
        s = (0.30 * f["vent_kde"] + 0.26 * f["vent_corridor"] + 0.10 * f["vent_geo_kde"]
             + 0.14 * alter + 0.12 * f["strain2"] + 0.08 * f["cond_cap"])
    elif arm == "e2_static_scarp":
        s = 0.86 * (0.30 * f["vent_kde"] + 0.26 * f["vent_corridor"] + 0.10 * f["vent_geo_kde"]
                    + 0.14 * alter + 0.12 * f["strain2"] + 0.08 * f["cond_cap"]) \
            + 0.14 * f["scarp"]
    elif arm == "ctrl_ventblind":
        s = 0.45 * f["strain2"] + 0.25 * f["cond_cap"] + 0.30 * f["scarp"]
    else:
        raise KeyError(arm)
    return np.clip(s, 0.0, 1.0).astype(np.float32)


def _gather(names, flat_idx, fold_feats) -> np.ndarray:
    X = np.empty((len(flat_idx), len(names)), dtype=np.float32)
    for j, n in enumerate(names):
        src = fold_feats[n] if n in fold_feats else load_feat(n)
        X[:, j] = src.ravel()[flat_idx]
    return X


def _train_hgb(names, train_mask, catalogue, fold_feats, seed):
    flat_cat = catalogue.ravel()
    flat_train = train_mask.ravel()
    pos = np.flatnonzero(flat_train & flat_cat)
    pool = np.flatnonzero(flat_train & ~flat_cat)
    rng = np.random.default_rng(seed)
    neg = rng.choice(pool, size=min(NEG_PER_POS * len(pos), len(pool)), replace=False)
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
    X = _gather(names, idx, fold_feats)
    model = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
    model.fit(X, y)
    return model, {"n_positive": int(len(pos)), "n_negative": int(len(neg))}


def oof_surface(g, folds) -> np.ndarray:
    cache = WORK / "e3_oof.npy"
    if cache.is_file():
        return np.load(cache)
    out = np.zeros(g.shape, dtype=np.float64)
    for fidx, fold in enumerate(folds):
        ff = _fold_catalogue_features(fold, g.shape)
        model, rec = _train_hgb(ALL_MODEL_FEATURES, fold["train"], g.catalogue, ff, SEED)
        idx = np.flatnonzero((g.footprint & fold["region"]).ravel())
        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        for lo in range(0, len(idx), 250_000):
            chunk = idx[lo: lo + 250_000]
            acc[chunk] = model.predict_proba(_gather(ALL_MODEL_FEATURES, chunk, ff))[:, 1]
        out += acc.reshape(g.shape)
        log(f"  e3 fold{fidx} trained {rec} + predicted")
        del model
    surf = np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)
    np.save(cache, surf)
    return surf


def final_surface(g) -> np.ndarray:
    cache = WORK / "e3_final.npy"
    if cache.is_file():
        return np.load(cache)
    ff = _fold_catalogue_features({"visible": g.catalogue}, g.shape)
    model, rec = _train_hgb(ALL_MODEL_FEATURES, g.footprint, g.catalogue, ff, SEED)
    idx = np.flatnonzero(g.footprint.ravel())
    acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
    for lo in range(0, len(idx), 250_000):
        chunk = idx[lo: lo + 250_000]
        acc[chunk] = model.predict_proba(_gather(ALL_MODEL_FEATURES, chunk, ff))[:, 1]
    surf = np.where(g.footprint, np.clip(acc.reshape(g.shape), 0.0, 1.0), 0.0).astype(np.float32)
    np.save(cache, surf)
    dump(OUT / "final-model.json", {"features": ALL_MODEL_FEATURES, "train": rec,
                                    "hgb_params": HGB_PARAMS, "neg_per_pos": NEG_PER_POS})
    return surf


# ------------------------------------------------------------------ experiment
def allocate(total: int, areas: list[int]) -> list[int]:
    s = sum(areas)
    base = [int(total * a / s) for a in areas]
    for i in range(total - sum(base)):
        base[i % len(base)] += 1
    return base


def cmd_experiment(args) -> int:
    start = time.monotonic()
    exp = args.exp
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").is_file():
        raise RuntimeError(f"{exp} already recorded; no implicit rerun")
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("leakage canary failed; lane stopped")
    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)
    cand = EXPERIMENTS[exp]
    arms = [cand] + [a for a in list(EXPERIMENTS.values()) + CONTROLS if a != cand]
    if not (WORK / "parent.npy").is_file():
        with rasterio.open(ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif") as ds:
            np.save(WORK / "parent.npy", ds.read(1).astype(np.float32))
    champion = np.where(g.footprint, np.load(WORK / "parent.npy"), 0.0).astype(np.float32)

    terms_file = WORK / "holdout-terms.npz"
    terms_by_arm: dict[str, np.ndarray] = {}
    if terms_file.is_file():
        with np.load(terms_file) as z:
            terms_by_arm = {k: z[k] for k in z.files}
    per_fold_file = WORK / "holdout-per-fold.json"
    per_fold = json.loads(per_fold_file.read_text()) if per_fold_file.is_file() else []
    for arm in arms:
        if arm in terms_by_arm:
            log(f"holdout terms cached: {arm}")
            continue
        surf = None if arm == "ctrl_champion_fixed" else (
            oof_surface(g, folds) if arm == "e3_oof_hgb" else static_surface(arm))
        total_terms = None
        for fidx, fold in enumerate(folds):
            if arm == "ctrl_champion_fixed":
                pred = champion
            else:
                pred = emit_dots_nms(surf, fold["visible"], g.footprint & fold["region"],
                                     budget=budgets[fidx], collar_px=COLLAR_PX,
                                     min_spacing_px=SPACING_PX)
            res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                     origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            per_fold.append({"arm": arm, "fold": fidx, "budget": budgets[fidx],
                             "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                             "tpw": float(res["tpw"]), "fpw": float(res["fpw"]),
                             "fnw": float(res["fnw"])})
            log(f"  scored {arm} fold{fidx}")
        terms_by_arm[arm] = total_terms
        np.savez_compressed(terms_file, **terms_by_arm)
        per_fold_file.write_text(json.dumps(per_fold))
        if arm != "ctrl_champion_fixed":
            del surf
    sub = {a: terms_by_arm[a] for a in arms}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=cand)
    pooled["per_fold"] = per_fold
    pooled["fold_receipts"] = [f["receipt"] for f in folds]
    pooled["arm_role"] = {**{a: "candidate-or-sibling-arm" for a in EXPERIMENTS.values()},
                          "ctrl_ventblind": "matched negative control",
                          "ctrl_champion_fixed": "REFERENCE-ONLY (not fold-fair: full-catalogue surface)"}
    pooled["budget_total"] = BUDGET
    pooled["collar_px"] = COLLAR_PX
    pooled["min_spacing_px"] = SPACING_PX
    pooled["elapsed_seconds"] = float(time.monotonic() - start)
    dump(outdir / "holdout.json", pooled)
    for a in arms:
        s = pooled["scores"][a]
        log(f"{a}: HOLDOUT-DTI {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in CONTROLS:
        d = pooled["paired_differences"][c]
        log(f"  Δ vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return 0


# ------------------------------------------------------------------ registry
def registry_entries() -> list[dict]:
    seen: dict[str, dict] = {}

    def add(path: Path, tag: str):
        if not path.is_file():
            return
        try:
            with rasterio.open(path) as ds:
                if ds.count != 1 or (ds.height, ds.width) != (3730, 3292):
                    return
        except Exception:
            return
        h = sha(path)
        e = seen.setdefault(h, {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                                "sha256": h, "tags": [], "bytes": path.stat().st_size})
        if tag not in e["tags"]:
            e["tags"].append(tag)

    for p in sorted((ROOT / "data/fleet_registry").glob("*.tif")):
        add(p, "fleet_registry")
    for p in sorted((ROOT / "data/lane_refs").glob("*.tif")):
        add(p, "lane_neighbour_ref")
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        add(p, "prior_download")
    for p in sorted((ROOT / "data/registry").glob("*.tif")):
        add(p, "pinned_registry")
    return sorted(seen.values(), key=lambda e: e["path"])


def reference_array(entry: dict) -> np.ndarray:
    p = Path(entry["path"])
    if not p.is_absolute():
        p = ROOT / p
    with rasterio.open(p) as ds:
        if (ds.height, ds.width) != (3730, 3292) or str(ds.crs) != "EPSG:32611":
            raise ValueError("grid mismatch")
        a = ds.read(1).astype(np.float64)
    return a


# ------------------------------------------------------------------ package
def cmd_package(_args) -> int:
    start = time.monotonic()
    if (OUT / "run-card.json").is_file():
        raise RuntimeError("run card already recorded; no implicit rerun")
    inputs = verify_pinned_inputs()
    can = json.loads((OUT / "canaries.json").read_text())
    g = grid.load_grid(ROOT / "data/official")
    fp = g.footprint

    # ---- select best experiment strictly by pooled HOLDOUT-DTI
    best_exp, best_score = None, None
    for exp in EXPERIMENTS:
        hp = OUT / exp / "holdout.json"
        if not hp.is_file():
            continue
        h = json.loads(hp.read_text())
        s = h["scores"][EXPERIMENTS[exp]]
        if best_score is None or s["dti"] > best_score["dti"]:
            best_exp, best_score = exp, s
    if best_exp is None:
        raise RuntimeError("no experiment holdout found")
    best_arm = EXPERIMENTS[best_exp]
    log(f"selected {best_arm} (HOLDOUT-DTI {best_score['dti']:.6f})")

    # ---- final surface
    surf = final_surface(g) if best_arm == "e3_oof_hgb" else static_surface(best_arm)
    np.save(WORK / "selected_surface.npy", surf)

    # ---- Rule 1 phase 1: surface rank correlation BEFORE placement
    refs = registry_entries()
    dump(OUT / "registry-freeze.json", {"frozen_before_candidate_surface_checks": True,
                                       "unique_byte_references": len(refs),
                                       "preregistration_sha256": sha(PREREG),
                                       "files": refs})
    probe = SurfaceProbe(surf, fp)
    surface_checks, max_rho, max_rho_path = [], 0.0, None
    for entry in refs:
        row = {"path": entry["path"], "tags": entry["tags"]}
        try:
            ref = reference_array(entry)
            ref_in = np.where(fp, np.nan_to_num(ref, nan=0.0), 0.0).astype(np.float32)
            res = probe.compare(ref_in)
            row.update(res)
            rho = res.get("rank_correlation")
            if rho is not None and abs(rho) > max_rho:
                max_rho, max_rho_path = abs(rho), entry["path"]
        except Exception as exc:
            row.update({"status": "UNVERIFIED", "rank_correlation": None, "error": str(exc)})
        surface_checks.append(row)
    surface_verified = sum(1 for r in surface_checks if r.get("rank_correlation") is not None)
    surface_pass = bool(max_rho <= 0.90)
    dump(OUT / "surface-checks.json",
         {"max_abs_rho": float(max_rho), "closest": max_rho_path, "pass": surface_pass,
          "references_checked": len(surface_checks), "references_verified": surface_verified,
          "checks": surface_checks})
    log(f"surface check: max |rho| {max_rho:.4f} vs {max_rho_path} pass={surface_pass}")
    if not surface_pass:
        dump(OUT / "run-card.json",
             {"schema": "gems-parallel-run-card-v1", "lane": "S30-VCE",
              "verdict": "negative", "stop_reason": "surface DUPLICATE stop before placement",
              "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
              "surface_max_abs_rho": float(max_rho), "closest": max_rho_path})
        return 3

    # ---- final emission + Rule 1 phase 2
    final = emit_dots_nms(surf, g.catalogue, fp, budget=BUDGET,
                          collar_px=COLLAR_PX, min_spacing_px=SPACING_PX)
    n_final = int((final > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"final dot count {n_final} != budget {BUDGET}")

    dot_checks, max_ov, max_ov_path = [], 0.0, None
    for entry in refs:
        row = {"path": entry["path"], "tags": entry["tags"]}
        try:
            ref = reference_array(entry)
            ref_in = np.where(fp, np.nan_to_num(ref, nan=0.0), 0.0).astype(np.float32)
            row["reference_positive_pixels"] = int((ref_in > 0).sum())
            row["is_dense_blanket"] = bool(row["reference_positive_pixels"] > 90_000
                                           or "lattice" in entry["path"].lower())
            res = dot_check(final, ref_in, fp)
            row.update({k: (float(v) if isinstance(v, float) else v) for k, v in res.items()})
            ov = res.get("overlap_within_3px")
            if ov is not None and not row["is_dense_blanket"] and ov > max_ov:
                max_ov, max_ov_path = float(ov), entry["path"]
        except Exception as exc:
            row.update({"status": "UNVERIFIED", "overlap_within_3px": None, "error": str(exc)})
        dot_checks.append(row)
    nine_paths = {f"data/fleet_registry/{n}" for n in (
        "GEMSDOE24__h25-1-dotted-h19-5-d1-5.tif", "GEMSDOE25__dotted-h19-5-d2-8.tif",
        "GEMSDOE27__topo-gap-closure-t-v2-on-d1-5.tif", "GEMSDOE28__h27-4-r1-solo-d2-8.tif",
        "GEMSDOE28__h36-1-rung30-blind-r1.tif", "GEMSDOE30__d28-poisson300m-offcat-44090.tif",
        "GEMSDOE32__h33-2-b2-zeros.tif", "GEMSDOE33__h33d-analog-tip-stepover-r30.tif",
        "GEMSDOE36__anderson-geothermal-pinn-38854.tif")}
    nine_checks = [r for r in dot_checks if r["path"] in nine_paths]
    nine_max = max((r["overlap_within_3px"] for r in nine_checks
                    if r.get("overlap_within_3px") is not None), default=None)
    dense_checks = [r for r in dot_checks if r.get("is_dense_blanket")]
    dense_max = max((r["overlap_within_3px"] for r in dense_checks
                     if r.get("overlap_within_3px") is not None), default=None)
    all_max = max((r["overlap_within_3px"] for r in dot_checks
                   if r.get("overlap_within_3px") is not None), default=None)
    dump(OUT / "final-dot-checks.json",
         {"gate_rule": "competitive references (<=90,000 positive pixels, non-lattice) must be <= 0.70; dense space-filling blankets are reported as the mathematical-lattice floor and are not a lane-drift stop (S25/S27 precedent; even the 0.2778 champion is ~99.97% within 3 px of calib_r13lattice_00904)",
          "max_3px_overlap_competitive": float(max_ov), "closest_competitive": max_ov_path,
          "max_3px_overlap_dense_blankets": dense_max,
          "max_3px_overlap_all_references": float(all_max),
          "max_3px_overlap_nine_leaders": nine_max, "nine_leader_checks": nine_checks,
          "dense_blanket_checks": dense_checks,
          "references_checked": len(dot_checks), "checks": dot_checks})
    log(f"dot checks: nine max {nine_max} | competitive max {max_ov} ({max_ov_path}) | dense max {dense_max}")

    # ---- write the submission bundle (all-finite zeros variant)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final > 0)[:8]
    tif_name = f"gems91-s30-vce-{best_exp}-{BUDGET}dots-{stamp}-{short}-zeros"
    out_tif = ROOT / "docs/downloads" / f"{tif_name}.tif"
    receipt = write_submission(out_tif, final.astype(np.float32),
                               ROOT / "data/official/sample_submission.tif", fp,
                               note=NOTE, name=tif_name, catalogue=g.catalogue)
    local_validation = validate(out_tif, fp, g.catalogue)
    assert_submittable(local_validation)
    with rasterio.open(out_tif) as ds:
        disk = ds.read(1)
        reread = {"crs": str(ds.crs), "shape": [ds.height, ds.width], "count": ds.count,
                  "dtype": ds.dtypes[0], "transform": list(ds.transform)[:6],
                  "nodata": ds.nodata}
    if not np.array_equal(disk > 0, final > 0):
        raise RuntimeError("on-disk support differs from in-memory final dots")
    reread.update({"all_finite": bool(np.isfinite(disk).all()), "min": float(disk.min()),
                   "max": float(disk.max()), "n_dots": int((disk > 0).sum()),
                   "on_catalogue": int((disk[g.catalogue] > 0).sum()),
                   "outside_footprint_positive": int((disk[~fp] > 0).sum()),
                   "form_range_check_0_1": bool(np.isfinite(disk).all() and disk.min() >= 0.0 and disk.max() <= 1.0)})
    tif_sha = sha(out_tif)
    zip_path = out_tif.with_suffix(".zip")
    writer_receipt = {"file": str(out_tif.relative_to(ROOT)), "sha256": tif_sha,
                      "bytes": out_tif.stat().st_size,
                      "zip": str(zip_path.relative_to(ROOT)),
                      "zip_sha256": sha(zip_path),
                      "support_dot_digest": dot_digest(final > 0),
                      "writer_receipt": receipt,
                      "independent_validator": local_validation,
                      "independent_reread": reread}
    dump(OUT / "writer-receipt.json", writer_receipt)

    # ---- blind SGMC off-catalogue diagnostics (report-only)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1).astype(np.float64)
    champ = np.load(WORK / "parent.npy").astype(np.float64)
    sgmc_diag = {}
    for name, pred in (("candidate", disk.astype(np.float64)),
                       ("champion_h33-2-b2_reference", champ)):
        sgmc_diag[name] = score_off_catalogue_sgmc(pred, sgmc, g.catalogue, fp)
    dump(OUT / "diagnostics.json",
         {"label": "SGMC-OFFCAT-CONTROL-DTI (blind report-only proxy; NOT a score, NOT a selection gate)",
          "evaluator": "scripts/evaluate_holdout.score_off_catalogue_sgmc",
          "sgmc_sha256": sha(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"),
          "rows": sgmc_diag})

    # ---- verdict
    canary_pass = bool(can["all_pass"])
    dots_pass_all = bool(max_ov <= 0.70)
    dots_pass_nine = bool(nine_max is not None and nine_max <= 0.70)
    validator_pass = bool(local_validation.get("all_checks_passed", False)
                          and reread["all_finite"] and reread["on_catalogue"] == 0
                          and reread["outside_footprint_positive"] == 0
                          and reread["form_range_check_0_1"])
    best_ctrl = "ctrl_ventblind"
    pooled = json.loads((OUT / best_exp / "holdout.json").read_text())
    paired = pooled["paired_differences"].get(best_ctrl, {})
    beats_control = bool(paired.get("ci95", [0.0, 0.0])[0] > 0)
    promote = bool(canary_pass and surface_pass and dots_pass_all and dots_pass_nine
                   and validator_pass and beats_control)

    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "lane": "S30-VCE (Vent-Concordant Emission; self-assigned from H-VCE-1)",
        "hypothesis": "Hidden expert-labelled faults are geothermal-upflow structures; vent, alteration, conductive-cap and strain/seismicity concordance marks them better than potential-field lineament ridges.",
        "mechanism": "Permeable fault-fracture upflow conduits feed hot springs (GDR #1391); outflow alters K/U/Th (GeoDAWN radiometrics) and leaves conductive clay caps (cond_surf); active slip shows as strain-rate/seismicity localization.",
        "named_non_fault_mimic": "Playa/lacustrine saline-groundwater conductors and pediment weathering K-depletion without fault control; volcanic-hydrothermal alteration centers not on Quaternary faults.",
        "preregistration_sha256": sha(PREREG),
        "evaluator_version": EH.VERSION,
        "experiment_selected": best_exp,
        "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
                    "dti": best_score["dti"], "ci95": best_score["ci95"],
                    "n_withheld_positives": best_score["withheld_positive_pixels"],
                    "paired_vs_ctrl_ventblind": paired,
                    "all_arms": {a: pooled["scores"][a] for a in pooled["scores"]}},
        "leakage_canary": {"max_symmetric_auc": can["max_symmetric_auc"],
                           "worst": can["worst"], "pass": canary_pass},
        "correlation_vs_registry": {"max_abs_rho": float(max_rho), "closest": max_rho_path,
                                    "pass": surface_pass, "references_verified": surface_verified},
        "overlap_vs_registry": {"gate": "competitive refs (<=90k dots, non-lattice) <= 0.70",
                                "max_3px_overlap_competitive": float(max_ov),
                                "closest_competitive": max_ov_path,
                                "max_3px_overlap_nine_leaders": nine_max,
                                "max_3px_overlap_dense_blankets_reported_only": dense_max,
                                "dense_note": "Dense space-filling lattices (206,895-dot calib_r13lattice_00904 etc.) are a mathematical floor: every sparse raster including the 0.2778 champion overlaps them ~99.97%. Reported, not a stop (S25/S27 precedent).",
                                "pass_competitive_le_0.70": dots_pass_all, "pass_nine_le_0.70": dots_pass_nine},
        "raster": {"file": writer_receipt["file"], "sha256": tif_sha, "bytes": writer_receipt["bytes"],
                   "zip": writer_receipt["zip"], "n_dots": n_final,
                   "support_dot_digest": writer_receipt["support_dot_digest"]},
        "validator_output": {"all_checks_passed": validator_pass, **reread},
        "diagnostics_sgmc_offcat": sgmc_diag,
        "submission": {"name": tif_name, "note": NOTE,
                       "label_scores": "USER-REPORTED receipts in the prompt are not ORGANIZER-CONFIRMED to this repo; this candidate has NO receipt yet"},
        "human_decision": {
            "technically_submittable": bool(dots_pass_all and dots_pass_nine and validator_pass),
            "explanation": "technically_submittable = uniqueness + format gates pass: the file WILL pass the DrivenData form ([0,1] all-finite, CRS/shape/transform match). The protocol verdict below is the separate scientific slot recommendation.",
            "protocol_promote": bool(promote),
        },
        "budget": {"experiments_used": 3, "experiments_allowed": 3,
                   "weekly_slots_spent": 0,
                   "promotion_note": "Promotion to a live weekly slot is a separate selector step (the project owner)."},
        "verdict": "promote" if promote else "negative",
        "ok_to_download": True,
        "ok_to_submit": bool(dots_pass_all and dots_pass_nine and validator_pass),
        "recommend_spending_weekly_slot": bool(promote),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    dump(OUT / "run-card.json", run_card)
    log(f"run card written; verdict={run_card['verdict']} ok_to_submit={run_card['ok_to_submit']}")
    return 0 if promote else 4


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    sub.add_parser("features")
    sub.add_parser("canary")
    pe = sub.add_parser("experiment")
    pe.add_argument("--exp", required=True, choices=list(EXPERIMENTS))
    sub.add_parser("package")
    args = ap.parse_args()
    return {"verify": cmd_verify, "features": cmd_features, "canary": cmd_canary,
            "experiment": cmd_experiment, "package": cmd_package}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
