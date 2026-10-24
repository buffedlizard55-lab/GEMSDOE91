#!/usr/bin/env python3
"""ASC91 lane driver: features + leakage canary, holdout E1-E3, final build.

    python3 scripts/build_asc91.py --mode features   # step-feature cache + canary
    python3 scripts/build_asc91.py --mode holdout    # E1, E2, frozen-branch E3
    python3 scripts/build_asc91.py --mode build --winner e2

Method is frozen in docs/HYPOTHESES_ASC91.md. Shared tools are reused, never
rebuilt: folds / quota / emission / HGB hyper-parameters / fold CI from
scripts/build_denovo.py, official DTI from scripts/dti.py, greedy spaced
emission from gems91.denovo, sentinel fill + robust-z from gems91.dd_vtc_pu,
tie-aware AUC from scripts/evaluate_holdout.py, fail-closed writing from
vendor/gems57/submission_writer.py. Every score printed is HOLDOUT-DTI.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import dti as D  # noqa: E402
import build_denovo as BD  # noqa: E402
from evaluate_holdout import fast_mann_whitney_auc  # noqa: E402
from gems91 import asc  # noqa: E402
from gems91 import denovo as DN  # noqa: E402
from gems91 import io as GIO  # noqa: E402
from gems91.dd_vtc_pu import _clean_band_edt, _robust_z  # noqa: E402

FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
WORK = ROOT / "work/asc91"
SEED = 20261024
N_DOTS = 37654
SPACING = 2.8
PRIOR_BEST = 0.142885  # HGB-CTX pooled HOLDOUT-DTI, same instrument (receipt JSON)

FEATURE_NAMES = (
    [f"stepabs_pct_{n}" for n in asc.FIELD_NAMES]
    + [f"aniso_pct_{n}" for n in asc.FIELD_NAMES]
    + [f"signed_z_{n}" for n in asc.FIELD_NAMES]
    + ["az_agree", "az_sin2", "az_cos2"]
)
STEPABS_COLS = list(range(0, 5))
SIGNED_COLS = {name: 10 + i for i, name in enumerate(asc.FIELD_NAMES)}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read1(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        return s.read(1)


def footprint() -> np.ndarray:
    return np.isfinite(read1(SAMPLE))


def catalogue(fp: np.ndarray) -> np.ndarray:
    return (np.nan_to_num(read1(CAT), nan=0.0) > 0) & fp


def verify_inputs() -> dict:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    wanted = {"sample_submission", "existing_faults", "training_features"}
    out = {}
    for e in manifest["files"]:
        if e["id"] not in wanted:
            continue
        p = ROOT / "data" / e["local_subpath"]
        digest = GIO.sha256_file(p)
        assert digest == e["sha256"] and p.stat().st_size == e["bytes"], e["id"]
        out[e["id"]] = {"sha256": digest, "bytes": p.stat().st_size}
    assert set(out) == wanted
    return out


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    tmp.replace(path)


# --------------------------------------------------------------------- features
def mode_features(args) -> dict:
    inputs = verify_inputs()
    fp = footprint()
    cat = catalogue(fp)
    h, w = fp.shape
    fp_flat = np.flatnonzero(fp)
    n_fp = int(fp_flat.size)
    WORK.mkdir(parents=True, exist_ok=True)

    steps_path = WORK / "steps.f32"
    steps = np.memmap(steps_path, dtype=np.float32, mode="w+",
                      shape=(len(asc.FIELDS), len(asc.AZIMUTHS_DEG), h, w))
    band_meta = {}
    with rasterio.open(FEATS) as s:
        for fi, (name, band) in enumerate(asc.FIELDS):
            tag = s.tags(band).get("band_name")
            assert tag == name, f"band {band}: tag {tag!r} != {name!r}"
            raw = s.read(band)
            band_meta[name] = {"band": band, "tag": tag,
                               "description": s.descriptions[band - 1]}
            field = _clean_band_edt(raw, fp)
            del raw
            for ai, az in enumerate(asc.AZIMUTHS_DEG):
                steps[fi, ai] = asc.step_response(field, az)
            del field
            steps.flush()
            print(f"steps done: {name} (band {band})", flush=True)
    del steps
    gc.collect()

    # Feature matrix on footprint rows only (memory-safe on 3.8 GiB).
    feat_path = WORK / "features_fp.npy"
    feat = np.lib.format.open_memmap(feat_path, mode="w+", dtype=np.float32,
                                     shape=(n_fp, len(FEATURE_NAMES)))
    steps = np.memmap(steps_path, dtype=np.float32, mode="r",
                      shape=(len(asc.FIELDS), len(asc.AZIMUTHS_DEG), h, w))
    argmax_maps = np.zeros((len(asc.FIELDS), h, w), dtype=np.int8)
    for fi, name in enumerate(asc.FIELD_NAMES):
        best = np.full((h, w), -1.0, dtype=np.float32)
        stack_abs = np.empty((len(asc.AZIMUTHS_DEG), h, w), dtype=np.float32)
        for ai in range(len(asc.AZIMUTHS_DEG)):
            a = np.abs(np.asarray(steps[fi, ai], dtype=np.float32))
            stack_abs[ai] = a
            upd = a > best
            best[upd] = a[upd]
            argmax_maps[fi][upd] = ai
        med = np.median(stack_abs, axis=0).astype(np.float32)
        del stack_abs
        feat[:, fi] = asc.percentile_grid(best, fp)[fp]
        feat[:, 5 + fi] = asc.percentile_grid(best - med, fp)[fp]
        del best, med
        feat.flush()
        print(f"stepabs/aniso done: {name}", flush=True)

    # Cross-field modal azimuth and agreement.
    counts = np.zeros((len(asc.AZIMUTHS_DEG), h, w), dtype=np.int8)
    for fi in range(len(asc.FIELDS)):
        for ai in range(len(asc.AZIMUTHS_DEG)):
            counts[ai] += (argmax_maps[fi] == ai)
    modal = np.argmax(counts, axis=0).astype(np.int8)
    del counts
    agree = np.zeros((h, w), dtype=np.float32)
    for fi in range(len(asc.FIELDS)):
        agree += (asc.axial_bin_distance(argmax_maps[fi], modal) <= 1)
    agree /= float(len(asc.FIELDS))
    del argmax_maps
    feat[:, 15] = agree[fp]
    theta = np.radians(modal[fp].astype(np.float64) * 22.5)
    feat[:, 16] = np.sin(2.0 * theta).astype(np.float32)
    feat[:, 17] = np.cos(2.0 * theta).astype(np.float32)
    del agree, theta

    # Signed step at modal azimuth, oriented so det_elev step > 0.
    signed = []
    for fi in range(len(asc.FIELDS)):
        sel = np.zeros((h, w), dtype=np.float32)
        for ai in range(len(asc.AZIMUTHS_DEG)):
            m = modal == ai
            if m.any():
                layer = np.asarray(steps[fi, ai], dtype=np.float32)
                sel[m] = layer[m]
                del layer
        signed.append(sel)
    del steps, modal
    orient = np.where(signed[0] < 0, -1.0, 1.0).astype(np.float32)
    for fi, name in enumerate(asc.FIELD_NAMES):
        z = _robust_z(signed[fi] * orient, fp)
        feat[:, 10 + fi] = z[fp]
        del z
    del signed, orient
    feat.flush()
    feat_arr = np.asarray(feat)
    assert np.isfinite(feat_arr).all(), "non-finite ASC feature"

    # E1 surface (frozen formula) cached as a full-grid float32 raster array.
    log_gm = np.mean([np.log(np.clip(feat_arr[:, c], 1e-6, None)) for c in STEPABS_COLS], axis=0)
    e1_rows = (np.exp(log_gm) * (0.75 + 0.25 * feat_arr[:, 15])).astype(np.float32)
    e1 = np.zeros(fp.shape, dtype=np.float32)
    e1.ravel()[fp_flat] = e1_rows
    np.save(WORK / "e1_surface.npy", e1)
    e1_sha = hashlib.sha256(e1.tobytes()).hexdigest()

    # Leakage canary (protocol S4): each feature alone, symmetric AUC.
    cat_flat = np.flatnonzero(cat)
    assert np.isin(cat_flat, fp_flat).all()
    pos_rows = np.searchsorted(fp_flat, cat_flat)
    dcat = ndi.distance_transform_edt(~cat)
    rng = np.random.default_rng(SEED)
    neg_pool = np.flatnonzero(fp & ~cat & (dcat > 5.0))
    neg_flat = rng.choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
    neg_rows = np.searchsorted(fp_flat, neg_flat)
    del dcat, neg_pool
    canary = {}
    for j, name in enumerate(FEATURE_NAMES):
        col = np.concatenate([feat_arr[pos_rows, j], feat_arr[neg_rows, j]]).astype(np.float64)
        y = np.r_[np.ones(pos_rows.size, bool), np.zeros(neg_rows.size, bool)]
        a = fast_mann_whitney_auc(col, y)
        canary[name] = {"auc_raw": round(float(a), 4),
                        "auc_symmetric": round(float(max(a, 1.0 - a)), 4)}
    worst = max(v["auc_symmetric"] for v in canary.values())

    # Pre-placement surface novelty of the E1 surface (protocol S1, phase 1).
    surf_novelty = surface_novelty(e1, fp)
    out = {
        "mode": "features", "generated_utc": now(), "inputs_RECEIPT": inputs,
        "bands_verified_from_tags": band_meta,
        "feature_names": FEATURE_NAMES, "n_footprint_px": n_fp,
        "feature_cache": {"path": str(feat_path.relative_to(ROOT)),
                          "sha256": GIO.sha256_file(feat_path)},
        "e1_surface": {"sha256_f32": e1_sha,
                       "formula": "(prod stepabs_pct)^(1/5) * (0.75+0.25*az_agree)"},
        "leakage_canary": {"rule": "catalogue px vs 150k sampled px >5px off catalogue, seed 20261024",
                           "threshold_symmetric_auc": 0.90, "per_feature": canary,
                           "max_symmetric_auc": worst, "pass": bool(worst <= 0.90)},
        "e1_surface_novelty_preplacement": surf_novelty,
    }
    dump(ROOT / "evidence/asc91_features_canary_20261024.json", out)
    print(json.dumps({"canary_max_sym_auc": worst,
                      "e1_surface_max_abs_spearman": surf_novelty["max_abs_spearman_sample"]}, indent=2))
    return out


# --------------------------------------------------------------------- novelty
def registry_rasters() -> list[Path]:
    reg = sorted((ROOT / "data/registry").glob("*.tif"))
    local = [ROOT / "docs/downloads/gems91-ced-v1-20261024-d35670b28c81.tif",
             ROOT / "docs/downloads/gems91-ddvtc-e1-20261024T120000Z-df50cc0c-zeros.tif",
             ROOT / "docs/downloads/gems91-denovo-hgbctx-37654dots-s2.8-20261024-7941b7ab-zeros.tif"]
    return reg + [p for p in local if p.is_file()]


def surface_novelty(surface: np.ndarray, fp: np.ndarray) -> dict:
    rng = np.random.default_rng(SEED)
    sample_idx = rng.choice(np.flatnonzero(fp), size=150_000, replace=False)
    rows = {}
    for path in registry_rasters():
        other = np.nan_to_num(read1(path), nan=0.0).astype(np.float32)
        rho = BD.spearman_sample(surface, other, sample_idx)
        rows[path.name] = {"sha256": GIO.sha256_file(path),
                           "spearman_sample": round(float(rho), 4),
                           "their_positive_px": int((other > 0).sum())}
        del other
    mx = max((abs(v["spearman_sample"]) for v in rows.values()), default=0.0)
    return {"n_registry_rasters": len(rows), "max_abs_spearman_sample": round(float(mx), 4),
            "threshold": 0.90, "pass": bool(mx <= 0.90), "per_raster": rows}


def dots_novelty(dots: np.ndarray) -> dict:
    rows = {}
    for path in registry_rasters():
        other = GIO.dot_mask(read1(path))
        d_other = ndi.distance_transform_edt(~other)
        frac = float((d_other[dots] <= 3.0).mean())
        rows[path.name] = {"sha256": GIO.sha256_file(path),
                           "frac_our_dots_within_3px": round(frac, 5),
                           "their_positive_px": int(other.sum())}
        del other, d_other
    mx = max((v["frac_our_dots_within_3px"] for v in rows.values()), default=0.0)
    worst = max(rows, key=lambda k: rows[k]["frac_our_dots_within_3px"]) if rows else None
    return {"n_registry_rasters": len(rows), "max_frac_within_3px": round(float(mx), 5),
            "worst_raster": worst, "threshold": 0.70, "pass": bool(mx <= 0.70),
            "per_raster": rows}


# --------------------------------------------------------------------- holdout
def load_features(fp):
    fp_flat = np.flatnonzero(fp)
    feat = np.load(WORK / "features_fp.npy", mmap_mode="r")
    assert feat.shape == (fp_flat.size, len(FEATURE_NAMES))
    return feat, fp_flat


def rows_of(fp_flat, flat_idx):
    return np.searchsorted(fp_flat, flat_idx)


def predict_grid(clf, feat, fp, fp_flat, extra_col=None) -> np.ndarray:
    out_rows = np.empty(fp_flat.size, dtype=np.float32)
    step = 250_000
    for a in range(0, fp_flat.size, step):
        b = min(fp_flat.size, a + step)
        X = np.asarray(feat[a:b], dtype=np.float32)
        if extra_col is not None:
            X = np.column_stack([X, extra_col[a:b]]).astype(np.float32)
        out_rows[a:b] = clf.predict_proba(X)[:, 1].astype(np.float32)
        del X
    grid = np.zeros(fp.shape, dtype=np.float32)
    grid.ravel()[fp_flat] = out_rows
    return grid


def tri3_pct_col(fp, fp_flat) -> np.ndarray:
    cache = WORK / "tri3_pct_fp.npy"
    if cache.is_file():
        return np.load(cache)
    surf, _audit = BD.load_surface(fp)
    pct = asc.percentile_grid(surf, fp)
    col = pct.ravel()[fp_flat].astype(np.float32)
    np.save(cache, col)
    return col


def score_surface(surface, folds, fp, cat) -> dict:
    lab, comp_fold, region_fold, _ncomp = folds
    parts, fold_dti, counts, n_with = [], [], [], []
    for f in range(4):
        truth = cat & (comp_fold[lab] == f) & (lab > 0)
        visible = cat & ~truth
        d_vis = ndi.distance_transform_edt(~visible)
        region = region_fold == f
        n_f = int(round(N_DOTS * float((fp & region).sum()) / float(fp.sum())))
        eligible = fp & region & (d_vis > 3.0)
        surf_f = surface(rng_f=f) if callable(surface) else surface
        dots = DN.greedy_spaced(surf_f, eligible, n_f, spacing_px=SPACING)
        p = D.components(dots.astype(np.float64), truth.astype(np.float64))
        parts.append(p); fold_dti.append(round(p.score, 6)); counts.append(int(dots.sum()))
        n_with.append(int(truth.sum()))
        print(f"  fold {f}: DTI={p.score:.5f} dots={counts[-1]} withheld={n_with[-1]}", flush=True)
        del dots, d_vis, truth, visible
    return {"pooled_holdout_dti": round(BD.pooled(parts), 6), "fold_dti": fold_dti,
            "fold_mean_ci95": BD.mean_ci(fold_dti), "dots_per_fold": counts,
            "n_withheld_positives_per_fold": n_with,
            "pooled_T": round(sum(p.T for p in parts), 2),
            "pooled_S": round(sum(p.S for p in parts), 2),
            "pooled_M": round(sum(p.M for p in parts), 2),
            "pooled_G": int(sum(p.G for p in parts))}


def score_supervised(feat, fp, fp_flat, cat, folds, *, extra_col=None) -> dict:
    lab, comp_fold, region_fold, _ncomp = folds
    rng = np.random.default_rng(SEED + 7)  # identical stream rule to build_denovo holdout3
    parts, fold_dti, counts, n_with = [], [], [], []
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
        rws = rows_of(fp_flat, idx)
        X = np.asarray(feat[rws], dtype=np.float32)
        if extra_col is not None:
            X = np.column_stack([X, extra_col[rws]]).astype(np.float32)
        clf = BD._train_hgb(X, y)
        del X
        sup = predict_grid(clf, feat, fp, fp_flat, extra_col=extra_col)
        del clf
        n_f = int(round(N_DOTS * float((fp & region).sum()) / float(fp.sum())))
        eligible = fp & region & (d_vis > 3.0)
        dots = DN.greedy_spaced(sup, eligible, n_f, spacing_px=SPACING)
        del sup
        p = D.components(dots.astype(np.float64), truth.astype(np.float64))
        parts.append(p); fold_dti.append(round(p.score, 6)); counts.append(int(dots.sum()))
        n_with.append(int(truth.sum()))
        print(f"  fold {f}: DTI={p.score:.5f} dots={counts[-1]} pos={pos_idx.size}", flush=True)
        del dots, d_vis, truth, visible, pos_idx, neg_pool, neg_idx, idx, rws
        gc.collect()
    return {"pooled_holdout_dti": round(BD.pooled(parts), 6), "fold_dti": fold_dti,
            "fold_mean_ci95": BD.mean_ci(fold_dti), "dots_per_fold": counts,
            "n_withheld_positives_per_fold": n_with,
            "pooled_T": round(sum(p.T for p in parts), 2),
            "pooled_S": round(sum(p.S for p in parts), 2),
            "pooled_M": round(sum(p.M for p in parts), 2),
            "pooled_G": int(sum(p.G for p in parts))}


def mode_holdout(args) -> dict:
    verify_inputs()
    canary = json.loads((ROOT / "evidence/asc91_features_canary_20261024.json").read_text())
    assert canary["leakage_canary"]["pass"], "leakage canary failed - refusing to score"
    fp = footprint()
    cat = catalogue(fp)
    feat, fp_flat = load_features(fp)
    folds = BD.fold_setup(cat)
    out = {"mode": "holdout", "generated_utc": now(),
           "evaluator": "scripts/dti.py official-DTI (alpha=0.2,beta=0.8,R=3px), pooled",
           "protocol": "build_denovo.fold_setup whole-component checkerboard (identical instrument to HGB-CTX receipt)",
           "prior_best_same_instrument": {"method": "HGB-CTX", "pooled_holdout_dti": PRIOR_BEST,
                                          "receipt": "evidence/holdout3_hgbctx_20261024.json"},
           "expected_withheld_per_fold": [15105, 15978, 12874, 17031],
           "experiments": {}}

    print("E1 ASC-U (unsupervised step concordance)", flush=True)
    e1 = np.load(WORK / "e1_surface.npy")
    out["experiments"]["E1_ASC_U"] = {"label": "HOLDOUT-DTI", **score_surface(e1, folds, fp, cat)}
    del e1

    print("control: random spaced, matched quota (seed stream = build_denovo)", flush=True)
    rng_master = np.random.default_rng(SEED)
    out["experiments"]["random_matched_control"] = {
        "label": "HOLDOUT-DTI",
        **score_surface(lambda rng_f: rng_master.random(fp.shape, dtype=np.float32), folds, fp, cat)}

    print("E2 ASC-S (HGB on 18 ASC features)", flush=True)
    out["experiments"]["E2_ASC_S"] = {"label": "HOLDOUT-DTI", "features": FEATURE_NAMES,
                                      **score_supervised(feat, fp, fp_flat, cat, folds)}

    e1d = out["experiments"]["E1_ASC_U"]["pooled_holdout_dti"]
    e2d = out["experiments"]["E2_ASC_S"]["pooled_holdout_dti"]
    if e2d > e1d:
        print("E3 branch (frozen): E2 + TRI3 percentile feature", flush=True)
        col = tri3_pct_col(fp, fp_flat)
        out["experiments"]["E3_ASC_S_plus_TRI3"] = {
            "label": "HOLDOUT-DTI", "features": FEATURE_NAMES + ["TRI3_surface_pct"],
            **score_supervised(feat, fp, fp_flat, cat, folds, extra_col=col)}
        out["e3_branch"] = "E2>1 pooled -> E2 + TRI3 percentile (docs/HYPOTHESES_ASC91.md S2)"
    else:
        print("E3 branch (frozen): E1 x polarity-consistency multiplier", flush=True)
        feat_arr = np.asarray(feat)
        pol = ((feat_arr[:, SIGNED_COLS["depth_to_base_surf"]] < 0).astype(np.float32)
               + (feat_arr[:, SIGNED_COLS["iso_grav_anom"]] > 0).astype(np.float32)
               + (feat_arr[:, SIGNED_COLS["cond_surf"]] < 0).astype(np.float32)) / 3.0
        e1 = np.load(WORK / "e1_surface.npy")
        e3 = e1.copy()
        e3.ravel()[fp_flat] = e1.ravel()[fp_flat] * (0.7 + 0.3 * pol)
        np.save(WORK / "e3_polarity_surface.npy", e3)
        out["experiments"]["E3_ASC_U_polarity"] = {"label": "HOLDOUT-DTI",
                                                   **score_surface(e3, folds, fp, cat)}
        out["e3_branch"] = "E1>=E2 pooled -> E1 x (0.7+0.3*pol) (docs/HYPOTHESES_ASC91.md S2)"
        del e1, e3, pol

    exps = {k: v["pooled_holdout_dti"] for k, v in out["experiments"].items()
            if k != "random_matched_control"}
    winner = max(exps, key=exps.get)
    out["winner"] = winner
    out["winner_beats_prior_best_same_instrument"] = bool(exps[winner] > PRIOR_BEST)
    out["withheld_match_expected"] = all(
        v["n_withheld_positives_per_fold"] == out["expected_withheld_per_fold"]
        for v in out["experiments"].values())
    dump(ROOT / "evidence/asc91_holdout_20261024.json", out)
    print(json.dumps({"winner": winner, "pooled": exps,
                      "beats_prior_best": out["winner_beats_prior_best_same_instrument"]}, indent=2))
    return out


# --------------------------------------------------------------------- build
def final_surface(winner: str, feat, fp, fp_flat, cat) -> tuple[np.ndarray, str]:
    if winner == "e1":
        return np.load(WORK / "e1_surface.npy"), "ASC-U unsupervised step concordance"
    if winner == "e3" and (WORK / "e3_polarity_surface.npy").is_file():
        return np.load(WORK / "e3_polarity_surface.npy"), "ASC-U x polarity consistency"
    extra = tri3_pct_col(fp, fp_flat) if winner == "e3" else None
    desc = "ASC-S HGB on 18 step features" + (" + TRI3 percentile" if winner == "e3" else "")
    dcat = ndi.distance_transform_edt(~cat)
    rng = np.random.default_rng(SEED + 7)
    pos_idx = np.flatnonzero(cat)
    neg_pool = np.flatnonzero(fp & (dcat > 5.0))
    neg_idx = rng.choice(neg_pool, size=min(3 * pos_idx.size, neg_pool.size), replace=False)
    idx = np.r_[pos_idx, neg_idx]
    y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
    rws = rows_of(fp_flat, idx)
    X = np.asarray(feat[rws], dtype=np.float32)
    if extra is not None:
        X = np.column_stack([X, extra[rws]]).astype(np.float32)
    clf = BD._train_hgb(X, y)
    del X
    surf = predict_grid(clf, feat, fp, fp_flat, extra_col=extra)
    del clf
    return surf, desc


def mode_build(args) -> dict:
    from vendor.gems57.submission_writer import write_submission

    hold = json.loads((ROOT / "evidence/asc91_holdout_20261024.json").read_text())
    winner_key = {"e1": "E1_ASC_U", "e2": "E2_ASC_S"}.get(args.winner) or \
        next(k for k in hold["experiments"] if k.startswith("E3"))
    assert winner_key == hold["winner"], f"--winner {args.winner} != holdout winner {hold['winner']}"
    verify_inputs()
    fp = footprint()
    cat = catalogue(fp)
    feat, fp_flat = load_features(fp)
    surf, method_desc = final_surface(args.winner, feat, fp, fp_flat, cat)
    np.save(WORK / "final_surface.npy", surf)
    surf_sha = hashlib.sha256(surf.tobytes()).hexdigest()

    print("novelty phase 1: surface before placement", flush=True)
    snov = surface_novelty(surf, fp)

    dcat = ndi.distance_transform_edt(~cat)
    eligible = fp & (dcat > 3.0)
    dots = DN.greedy_spaced(surf, eligible, N_DOTS, spacing_px=SPACING)
    assert int(dots.sum()) == N_DOTS, int(dots.sum())
    assert not (dots & cat).any() and float(dcat[dots].min()) > 3.0
    digest = GIO.dot_digest(dots)

    print("novelty phase 2: final dots", flush=True)
    dnov = dots_novelty(dots)
    pred = np.where(fp, dots.astype(np.float32), np.float32(0.0))  # all-finite [0,1]
    fstem = f"gems91-asc91-{args.winner}-{N_DOTS}dots-s2p8-20261024-{digest[:8]}-zeros"
    note = f"ASC91 {args.winner.upper()} antisymmetric step concordance 37,654 dots"
    out_path = ROOT / "docs/downloads" / f"{fstem}.tif"
    hold_v = hold["experiments"][winner_key]
    receipt = write_submission(
        out_path, pred, SAMPLE, fp, note=note, name=fstem, catalogue=cat,
        metadata={"lane": "ASC91", "method": method_desc, "winner": winner_key,
                  "surface_sha256_f32": surf_sha, "dot_set_digest": digest,
                  "holdout_label": "HOLDOUT-DTI",
                  "holdout_pooled": hold_v["pooled_holdout_dti"],
                  "holdout_ci95_fold_mean": hold_v["fold_mean_ci95"],
                  "holdout_evaluator": hold["evaluator"],
                  "holdout_withheld_positives": sum(hold_v["n_withheld_positives_per_fold"])})
    audit = {
        "mode": "build", "generated_utc": now(), "lane": "ASC91",
        "method": method_desc, "winner_experiment": winner_key,
        "features": FEATURE_NAMES + (["TRI3_surface_pct"] if "TRI3" in winner_key else []),
        "n_dots": N_DOTS, "spacing_px": SPACING,
        "min_catalogue_distance_px_RECEIPT": round(float(dcat[dots].min()), 4),
        "dots_on_catalogue_RECEIPT": int((dots & cat).sum()),
        "dot_set_digest": digest, "surface_sha256_f32": surf_sha,
        "novelty_surface_preplacement": snov, "novelty_final_dots": dnov,
        "holdout_evidence_class": "HOLDOUT-DTI",
        "holdout": hold_v, "prior_best_same_instrument": PRIOR_BEST,
        "beats_prior_best_same_instrument": bool(hold_v["pooled_holdout_dti"] > PRIOR_BEST),
        "writer_receipt_file": str(out_path.with_suffix(".json").relative_to(ROOT)),
        "raster_sha256_RECEIPT": GIO.sha256_file(out_path),
        "raster_bytes_RECEIPT": out_path.stat().st_size,
        "submission_name": fstem, "note": note, "note_chars": len(note),
    }
    audit["is_duplicate"] = not (snov["pass"] and dnov["pass"])
    dump(ROOT / "docs/downloads" / f"{fstem}-audit.json", audit)
    dump(ROOT / "evidence/asc91_build_20261024.json", audit)
    print(json.dumps({"file": out_path.name, "sha256": audit["raster_sha256_RECEIPT"],
                      "is_duplicate": audit["is_duplicate"],
                      "surface_max_abs_rho": snov["max_abs_spearman_sample"],
                      "dots_max_frac_3px": dnov["max_frac_within_3px"]}, indent=2))
    return audit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["features", "holdout", "build"])
    ap.add_argument("--winner", choices=["e1", "e2", "e3"], default="e2")
    args = ap.parse_args()
    {"features": mode_features, "holdout": mode_holdout, "build": mode_build}[args.mode](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
