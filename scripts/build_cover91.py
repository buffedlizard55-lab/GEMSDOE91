#!/usr/bin/env python3
"""G91-COVER driver (GEMSDOE91, 2026-10-24) — cache / holdout / build.

    python3 scripts/build_cover91.py --mode cache
    python3 scripts/build_cover91.py --mode holdout
    python3 scripts/build_cover91.py --mode build

Lane and frozen experiment plan: docs/HYPOTHESES_G91.md. Reuse, don't
rebuild (protocol S2): TRI3 surface, percentile/context features, HGB
training, folds, pooled/CI helpers from scripts/build_denovo.py; ASC
step features from scripts/build_asc91.py (run as a subprocess so its
own receipts regenerate); scoring from scripts/dti.py; writing via
vendor/gems57/submission_writer.py. New code is limited to
src/gems91/cover_gate.py (7 cover-gated interaction features) and this
assembly driver, plus the 6 depth-conditioned features from fuse91.

Every score printed is HOLDOUT-DTI on the identical instrument as the
FUSE91 receipt (0.167293, 60,988 withheld positives). No organizer
score is claimed.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import subprocess
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
import build_asc91 as BA  # noqa: E402
from evaluate_holdout import fast_mann_whitney_auc  # noqa: E402
from gems91 import denovo as DN  # noqa: E402
from gems91 import fuse91 as F  # noqa: E402
from gems91 import cover_gate as CG  # noqa: E402
from gems91 import io as GIO  # noqa: E402
from gems91.dd_vtc_pu import _clean_band_edt  # noqa: E402

FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CATP = ROOT / "data/official/existing_faults.tif"
SGMC = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
R0P = ROOT / "data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
WORK = ROOT / "work/cover91"
ASC_FEAT = ROOT / "work/asc91/features_fp.npy"
SEED = 20261024
N_DOTS = 37654
SPACING = 2.8
PRIOR_BEST = 0.167293  # FUSE91 pooled HOLDOUT-DTI, identical instrument — new bar
PRIOR_BEST_HGBCTX = 0.142885
EXPECTED_WITHHELD = [15105, 15978, 12874, 17031]
RING_CAP_FRAC = 0.06

FEATURE_NAMES: list[str] = []


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        return s.read(1)


def footprint() -> np.ndarray:
    return np.isfinite(read1(SAMPLE))


def catalogue(fp: np.ndarray) -> np.ndarray:
    return (np.nan_to_num(read1(CATP), nan=0.0) > 0) & fp


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(obj, indent=2) + "\n")
    tmp.replace(path)


def feature_names() -> list[str]:
    global FEATURE_NAMES
    if not FEATURE_NAMES:
        FEATURE_NAMES = BD._ctx_feature_names() + list(BA.FEATURE_NAMES) + list(F.NEW_FEATURE_NAMES) + list(CG.NEW_FEATURE_NAMES)
    return FEATURE_NAMES


# ---------------------------------------------------------------------- cache
def mode_cache(args) -> dict:
    inputs = BA.verify_inputs()
    fp = footprint()
    cat = catalogue(fp)
    fp_flat = np.flatnonzero(fp)
    n_fp = int(fp_flat.size)
    names = feature_names()
    assert len(names) == 59, len(names)
    WORK.mkdir(parents=True, exist_ok=True)

    if not ASC_FEAT.is_file():
        print("ASC feature cache missing -> running scripts/build_asc91.py --mode features", flush=True)
        r = subprocess.run([sys.executable, str(ROOT / "scripts/build_asc91.py"), "--mode", "features"],
                           cwd=ROOT)
        if r.returncode != 0 or not ASC_FEAT.is_file():
            raise SystemExit("ASC feature build failed; refusing to continue")

    print("TRI3 surface (build_denovo.load_surface)", flush=True)
    surf, surf_audit = BD.load_surface(fp)
    ref_idx = BD._ref_sample(fp)
    refs = BD._band_refs(ref_idx, surf)

    feat_path = WORK / "features_fp.npy"
    feat = np.lib.format.open_memmap(feat_path, mode="w+", dtype=np.float32,
                                     shape=(n_fp, len(names)))
    col = 0
    print("CTX percentile + context columns (build_denovo order)", flush=True)
    for b in range(20):
        g = BD._pct_grid(b, refs, surf)
        feat[:, col] = g.ravel()[fp_flat]
        col += 1
        if (b + 1) in BD.CTX_BANDS:
            ctx = ndi.uniform_filter(g, BD.CTX_SIZE, mode="nearest")
            feat[:, col] = ctx.ravel()[fp_flat]
            col += 1
            del ctx
        del g
        feat.flush()
    assert col == 28, col
    del surf
    gc.collect()

    print("ASC step columns (cached by build_asc91)", flush=True)
    asc = np.load(ASC_FEAT, mmap_mode="r")
    assert asc.shape == (n_fp, 18), asc.shape
    for a in range(0, n_fp, 250_000):
        b = min(n_fp, a + 250_000)
        feat[a:b, 28:46] = np.asarray(asc[a:b], dtype=np.float32)
    del asc
    feat.flush()

    print("NEW depth-conditioned columns (gems91.fuse91)", flush=True)
    with rasterio.open(FEATS) as s:
        cond = _clean_band_edt(s.read(17), fp)
        depth = _clean_band_edt(s.read(15), fp)
        grav = _clean_band_edt(s.read(13), fp)
        tags = {b: s.tags(b).get("band_name") for b in (13, 15, 17)}
    assert tags == {13: "iso_grav_anom", 15: "depth_to_base_surf", 17: "cond_surf"}, tags
    new6, new_audit = F.depth_conditioned_features(cond, depth, grav, fp)
    # keep cond/depth/grav for cover_gated step
    assert new6.shape == (n_fp, 6)
    feat[:, 46:52] = new6
    del new6
    feat.flush()

    print("NEW cover-gated columns (gems91.cover_gate)", flush=True)
    # Need raw bands for cover gating: det_elev_slope (19), iso_grav_anom_hg (18), tmi_hg (3)
    with rasterio.open(FEATS) as s:
        det_slope_raw = s.read(19)
        grav_hg_raw = s.read(18)
        tmi_hg_raw = s.read(3)
        # reuse depth and cond already cleaned but need raw for cover_gate which cleans internally
        # we have depth, cond cleaned above; need to re-read depth and cond raw for cover_gate
        depth_raw = s.read(15)
        cond_raw = s.read(17)
    cover7, cover_audit = CG.cover_gated_features(det_slope_raw, grav_hg_raw, tmi_hg_raw, depth_raw, cond_raw, fp)
    assert cover7.shape == (n_fp, 7)
    feat[:, 52:59] = cover7
    del cover7, det_slope_raw, grav_hg_raw, tmi_hg_raw, depth_raw, cond_raw, cond, depth, grav
    feat.flush()
    feat_arr = np.asarray(feat)
    assert np.isfinite(feat_arr).all(), "non-finite fused feature"
    cache_sha = GIO.sha256_file(feat_path)

    # Leakage canary (protocol S4): every feature alone, symmetric AUC,
    # catalogue px vs 150k px >5px off catalogue, seed fixed (ASC rule).
    print("leakage canary: 59 features alone", flush=True)
    cat_flat = np.flatnonzero(cat)
    pos_rows = np.searchsorted(fp_flat, cat_flat)
    dcat = ndi.distance_transform_edt(~cat)
    rng = np.random.default_rng(SEED)
    neg_pool = np.flatnonzero(fp & ~cat & (dcat > 5.0))
    neg_flat = rng.choice(neg_pool, size=min(150_000, neg_pool.size), replace=False)
    neg_rows = np.searchsorted(fp_flat, neg_flat)
    del dcat, neg_pool
    canary = {}
    for j, name in enumerate(names):
        x = np.concatenate([feat_arr[pos_rows, j], feat_arr[neg_rows, j]]).astype(np.float64)
        y = np.r_[np.ones(pos_rows.size, bool), np.zeros(neg_rows.size, bool)]
        a = fast_mann_whitney_auc(x, y)
        canary[name] = {"auc_raw": round(float(a), 4),
                        "auc_symmetric": round(float(max(a, 1.0 - a)), 4)}
    worst_name = max(canary, key=lambda k: canary[k]["auc_symmetric"])
    worst = canary[worst_name]["auc_symmetric"]

    out = {"mode": "cache", "generated_utc": now(), "lane": "G91-COVER",
           "inputs_RECEIPT": inputs, "feature_names": names,
           "n_features": len(names), "n_footprint_px": n_fp,
           "feature_cache": {"path": str(feat_path.relative_to(ROOT)), "sha256": cache_sha},
           "tri3_surface_audit": surf_audit, "new_feature_audit": new_audit, "cover_audit": cover_audit,
           "leakage_canary": {"rule": "catalogue px vs 150k sampled px >5px off catalogue, seed 20261024",
                              "threshold_symmetric_auc": 0.90, "per_feature": canary,
                              "max_symmetric_auc": worst, "worst_feature": worst_name,
                              "pass": bool(worst <= 0.90)}}
    dump(ROOT / "evidence/cover91_features_canary_20261024.json", out)
    dump(WORK / "feature_names.json", {"feature_names": names, "cache_sha256": cache_sha})
    print(json.dumps({"canary_max_sym_auc": worst, "worst_feature": worst_name,
                      "cache_sha256": cache_sha}, indent=2))
    return out


# -------------------------------------------------------------------- holdout
def load_feat(fp):
    fp_flat = np.flatnonzero(fp)
    names = json.loads((WORK / "feature_names.json").read_text())["feature_names"]
    feat = np.load(WORK / "features_fp.npy", mmap_mode="r")
    assert feat.shape == (fp_flat.size, len(names)), feat.shape
    return feat, fp_flat, names


def _parts_dict(parts, fold_dti, counts, n_with):
    return {"pooled_holdout_dti": round(BD.pooled(parts), 6), "fold_dti": fold_dti,
            "fold_mean_ci95": BD.mean_ci(fold_dti), "dots_per_fold": counts,
            "n_withheld_positives_per_fold": n_with,
            "pooled_T": round(sum(p.T for p in parts), 2),
            "pooled_S": round(sum(p.S for p in parts), 2),
            "pooled_M": round(sum(p.M for p in parts), 2),
            "pooled_G": int(sum(p.G for p in parts)),
            "per_dot_credit_T_over_S": round(sum(p.T for p in parts) / sum(p.S for p in parts), 4)}


def mode_holdout(args) -> dict:
    BA.verify_inputs()
    can = json.loads((ROOT / "evidence/cover91_features_canary_20261024.json").read_text())
    assert can["leakage_canary"]["pass"], "leakage canary failed - refusing to score"
    fp = footprint()
    cat = catalogue(fp)
    feat, fp_flat, names = load_feat(fp)
    lab, comp_fold, region_fold, _ = BD.fold_setup(cat)
    h, w = fp.shape
    WORK.mkdir(parents=True, exist_ok=True)
    surf_mm = np.memmap(WORK / "fold_surfaces.f32", dtype=np.float32, mode="w+", shape=(4, h, w))

    rng = np.random.default_rng(SEED + 7)
    res = {k: {"parts": [], "fold": [], "counts": [], "nwith": []} for k in ("E1", "E2")}
    fold_truth = []
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
        rws = np.searchsorted(fp_flat, idx)
        X = np.asarray(feat[rws], dtype=np.float32)
        clf = BD._train_hgb(X, y)
        del X
        sup = BA.predict_grid(clf, feat, fp, fp_flat)
        del clf
        surf_mm[f] = sup
        surf_mm.flush()
        fold_truth.append((truth, d_vis, region))
        n_f = int(round(N_DOTS * float((fp & region).sum()) / float(fp.sum())))
        eligible = fp & region & (d_vis > 3.0)
        smooth = F.scatter_smooth(sup, fp)
        for key, surface in (("E1", sup), ("E2", smooth)):
            dots = DN.greedy_spaced(surface, eligible, n_f, spacing_px=SPACING)
            p = D.components(dots.astype(np.float64), truth.astype(np.float64))
            res[key]["parts"].append(p); res[key]["fold"].append(round(p.score, 6))
            res[key]["counts"].append(int(dots.sum())); res[key]["nwith"].append(int(truth.sum()))
            del dots
        print(f"fold {f}: E1={res['E1']['fold'][-1]:.5f} E2={res['E2']['fold'][-1]:.5f} "
              f"withheld={int(truth.sum())} pos={pos_idx.size}", flush=True)
        del sup, smooth, pos_idx, neg_pool, neg_idx, idx, rws
        gc.collect()

    out = {"mode": "holdout", "generated_utc": now(), "lane": "G91-COVER",
           "label": "HOLDOUT-DTI",
           "evaluator": "scripts/dti.py official-DTI (alpha=0.2,beta=0.8,R=3px), pooled",
           "protocol": "build_denovo.fold_setup whole-component checkerboard (identical instrument to FUSE91/HGB-CTX receipt)",
           "features": names,
           "prior_best_same_instrument": {"method": "FUSE91", "pooled_holdout_dti": PRIOR_BEST,
                                          "receipt": "evidence/fuse91_holdout_20261024.json"},
           "prior_best_hgbctx": PRIOR_BEST_HGBCTX,
           "experiments": {}}
    for key, desc in (("E1", "G91-COVER 59-feature HGB, sharp surface, >3px collar"),
                      ("E2", "E1 fold surfaces scatter-smoothed sigma=1.85px, >3px collar")):
        r = res[key]
        out["experiments"][key] = {"label": "HOLDOUT-DTI", "method": desc,
                                   **_parts_dict(r["parts"], r["fold"], r["counts"], r["nwith"])}
    assert out["experiments"]["E1"]["n_withheld_positives_per_fold"] == EXPECTED_WITHHELD, \
        "withheld counts drifted from the identical-instrument receipts"

    # E3 (frozen branch): winner(E1,E2) surface type + collar ring.
    e1d = out["experiments"]["E1"]["pooled_holdout_dti"]
    e2d = out["experiments"]["E2"]["pooled_holdout_dti"]
    base = "E2" if e2d > e1d else "E1"
    out["e3_base"] = base
    parts, fold_dti, counts, n_with, ring_counts = [], [], [], [], []
    for f in range(4):
        truth, d_vis, region = fold_truth[f]
        sup = np.asarray(surf_mm[f], dtype=np.float32)
        surface = F.scatter_smooth(sup, fp) if base == "E2" else sup
        n_f = int(round(N_DOTS * float((fp & region).sum()) / float(fp.sum())))
        tier = fp & region & (d_vis > 2.0) & (d_vis <= 3.0)
        main = fp & region & (d_vis > 3.0)
        cap = int(round(RING_CAP_FRAC * n_f))
        dots = F.tiered_greedy_spaced(surface, tier, main, n_f, tier_cap=cap, spacing_px=SPACING)
        ring_counts.append(int((dots & tier).sum()))
        p = D.components(dots.astype(np.float64), truth.astype(np.float64))
        parts.append(p); fold_dti.append(round(p.score, 6)); counts.append(int(dots.sum()))
        n_with.append(int(truth.sum()))
        print(f"fold {f}: E3(base={base}+ring)={p.score:.5f} ring_dots={ring_counts[-1]}/{cap}", flush=True)
        del sup, surface, dots
    out["experiments"]["E3"] = {"label": "HOLDOUT-DTI",
                                "method": f"{base} surface + collar ring 2<d<=3px capped at 6% of budget",
                                "ring_dots_per_fold": ring_counts,
                                **_parts_dict(parts, fold_dti, counts, n_with)}

    # Context control (not an experiment): seeded random spaced, same stream rule
    rng_master = np.random.default_rng(SEED)
    parts, fold_dti, counts, n_with = [], [], [], []
    for f in range(4):
        truth, d_vis, region = fold_truth[f]
        n_f = int(round(N_DOTS * float((fp & region).sum()) / float(fp.sum())))
        eligible = fp & region & (d_vis > 3.0)
        dots = DN.greedy_spaced(rng_master.random(fp.shape, dtype=np.float32), eligible,
                                n_f, spacing_px=SPACING)
        p = D.components(dots.astype(np.float64), truth.astype(np.float64))
        parts.append(p); fold_dti.append(round(p.score, 6)); counts.append(int(dots.sum()))
        n_with.append(int(truth.sum()))
        del dots
    out["random_matched_control"] = {"label": "HOLDOUT-DTI", **_parts_dict(parts, fold_dti, counts, n_with)}
    out["random_control_receipt_expected"] = 0.070827

    exps = {k: v["pooled_holdout_dti"] for k, v in out["experiments"].items()}
    out["winner"] = max(exps, key=exps.get)
    out["winner_beats_prior_best_FUSE91"] = bool(exps[out["winner"]] > PRIOR_BEST)
    out["winner_beats_prior_best_HGBCTX"] = bool(exps[out["winner"]] > PRIOR_BEST_HGBCTX)
    dump(ROOT / "evidence/cover91_holdout_20261024.json", out)
    print(json.dumps({"winner": out["winner"], "pooled": exps,
                      "random_control": out["random_matched_control"]["pooled_holdout_dti"],
                      "beats_FUSE91": out["winner_beats_prior_best_FUSE91"],
                      "beats_HGBCTX": out["winner_beats_prior_best_HGBCTX"]}, indent=2))
    return out


# ---------------------------------------------------------------------- build
def registry_rasters() -> list[Path]:
    cands = (sorted((ROOT / "data/fleet_registry").glob("*.tif"))
             + sorted((ROOT / "data/registry").glob("*.tif"))
             + sorted((ROOT / "docs/downloads").glob("*.tif")))
    seen: dict[str, Path] = {}
    for p in cands:
        seen.setdefault(GIO.sha256_file(p), p)
    return list(seen.values())


def novelty(surface, dots, fp) -> dict:
    rng = np.random.default_rng(SEED)
    sample_idx = rng.choice(np.flatnonzero(fp), size=150_000, replace=False)
    d_ours = ndi.distance_transform_edt(~dots)
    rows = {}
    for path in registry_rasters():
        other_f = np.nan_to_num(read1(path), nan=0.0).astype(np.float32)
        rho = BD.spearman_sample(surface, other_f, sample_idx)
        other = other_f > 0
        del other_f
        d_other = ndi.distance_transform_edt(~other)
        directed = float((d_other[dots] <= 3.0).mean()) if dots.any() else 0.0
        del d_other
        theirs_within = float((d_ours[other] <= 3.0).mean()) if other.any() else 0.0
        f1 = 0.0 if (directed + theirs_within) == 0 else 2 * directed * theirs_within / (directed + theirs_within)
        rows[path.name] = {"path": str(path.relative_to(ROOT)), "sha256": GIO.sha256_file(path),
                           "surface_spearman_sample": round(float(rho), 4),
                           "their_positive_px": int(other.sum()),
                           "frac_our_dots_within_3px_directed": round(directed, 5),
                           "frac_their_px_within_3px_of_ours": round(theirs_within, 5),
                           "symmetric_within3_f1": round(float(f1), 5),
                           "is_synthetic_lattice": "lattice" in path.name.lower()}
        del other
    del d_ours
    real = {k: v for k, v in rows.items() if not v["is_synthetic_lattice"]}
    lat = {k: v for k, v in rows.items() if v["is_synthetic_lattice"]}
    max_rho = max((abs(v["surface_spearman_sample"]) for v in rows.values()), default=0.0)
    max_dir = max((v["frac_our_dots_within_3px_directed"] for v in real.values()), default=0.0)
    worst = max(real, key=lambda k: real[k]["frac_our_dots_within_3px_directed"]) if real else None
    return {"n_registry_rasters_dedup_by_sha": len(rows), "n_real": len(real), "n_lattice": len(lat),
            "surface_max_abs_spearman_all": round(float(max_rho), 4), "surface_threshold": 0.90,
            "surface_pass": bool(max_rho <= 0.90),
            "dots_max_directed_frac_real": round(float(max_dir), 5), "dots_worst_real_raster": worst,
            "dots_threshold": 0.70, "dots_pass_real": bool(max_dir <= 0.70),
            "lattice_reported_separately": lat,
            "lattice_note": "Synthetic lattice calibrators cover 99.87% of the footprint within 3px and "
                            "reject R0 itself (99.9%); directed overlap vs them measures cover density, "
                            "not copying (evidence/forensics_f91_20261024.json). Symmetric F1 is given "
                            "for every raster in per_raster.",
            "per_raster": rows}


def mode_build(args) -> dict:
    from vendor.gems57.submission_writer import write_submission

    hold = json.loads((ROOT / "evidence/cover91_holdout_20261024.json").read_text())
    winner = hold["winner"]
    base = hold.get("e3_base", "E1") if winner == "E3" else winner
    BA.verify_inputs()
    fp = footprint()
    cat = catalogue(fp)
    feat, fp_flat, names = load_feat(fp)
    dcat = ndi.distance_transform_edt(~cat)

    print("final training on full catalogue (build3 sampling rule)", flush=True)
    rng = np.random.default_rng(SEED + 7)
    pos_idx = np.flatnonzero(cat)
    neg_pool = np.flatnonzero(fp & (dcat > 5.0))
    neg_idx = rng.choice(neg_pool, size=min(3 * pos_idx.size, neg_pool.size), replace=False)
    idx = np.r_[pos_idx, neg_idx]
    y = np.r_[np.ones(pos_idx.size), np.zeros(neg_idx.size)]
    rws = np.searchsorted(fp_flat, idx)
    X = np.asarray(feat[rws], dtype=np.float32)
    clf = BD._train_hgb(X, y)
    del X
    sharp = BA.predict_grid(clf, feat, fp, fp_flat)
    del clf
    np.save(WORK / "final_surface_sharp.npy", sharp)
    surf = F.scatter_smooth(sharp, fp) if base == "E2" else sharp
    if base == "E2":
        np.save(WORK / "final_surface_scatter.npy", surf)
    surf_sha = hashlib.sha256(surf.tobytes()).hexdigest()

    print("emission (winner arm) + novelty", flush=True)
    if winner == "E3":
        tier = fp & (dcat > 2.0) & (dcat <= 3.0)
        main = fp & (dcat > 3.0)
        cap = int(round(RING_CAP_FRAC * N_DOTS))
        dots = F.tiered_greedy_spaced(surf, tier, main, N_DOTS, tier_cap=cap, spacing_px=SPACING)
        emission = f"{base} surface + collar ring 2<d<=3px cap {cap}; greedy spaced 2.8px"
        min_d_expected = 2.0
    else:
        dots = DN.greedy_spaced(surf, fp & (dcat > 3.0), N_DOTS, spacing_px=SPACING)
        emission = f"{base} surface; greedy spaced 2.8px; >3px off catalogue"
        min_d_expected = 3.0
    assert int(dots.sum()) == N_DOTS, int(dots.sum())
    assert not (dots & cat).any()
    assert float(dcat[dots].min()) > min_d_expected, float(dcat[dots].min())
    digest = GIO.dot_digest(dots)
    nov = novelty(surf, dots, fp)

    # SGMC off-catalogue control (REPORT ONLY, never a gate)
    sgmc = (np.nan_to_num(read1(SGMC), nan=0.0) > 0) & (dcat > 3.0) & fp
    sg = {}
    for nm, dd in (("cover91", dots), ("r0_parent", GIO.dot_mask(read1(R0P)))):
        p = D.components(dd.astype(np.float64), sgmc.astype(np.float64))
        sg[nm] = {"sgmc_off_dti_REPORT_ONLY": round(p.score, 6), "T": round(p.T, 2),
                  "S": round(p.S, 2), "M": round(p.M, 2), "G": int(p.G)}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fstem = f"gems91-cover91-{winner.lower()}-{N_DOTS}dots-{ts}-{digest[:8]}-zeros"
    note = (f"GEMS91 G91-COVER {winner} HGB 59f cover-gated topo/grav/mag 37654d s2.8 zeros")
    # trim if over 140
    if len(note) > 140:
        note = note[:140]
    assert len(note) <= 140, note
    pred = np.where(fp, dots.astype(np.float32), np.float32(0.0))
    out_path = ROOT / "docs/downloads" / f"{fstem}.tif"
    hold_v = hold["experiments"][winner]
    receipt = write_submission(
        out_path, pred, SAMPLE, fp, note=note, name=fstem, catalogue=cat,
        metadata={"lane": "G91-COVER", "winner": winner, "emission": emission,
                  "features": names, "surface_sha256_f32": surf_sha,
                  "dot_set_digest": digest, "holdout_label": "HOLDOUT-DTI",
                  "holdout_pooled": hold_v["pooled_holdout_dti"],
                  "holdout_ci95_fold_mean": hold_v["fold_mean_ci95"],
                  "holdout_evaluator": hold["evaluator"],
                  "holdout_withheld_positives": int(sum(hold_v["n_withheld_positives_per_fold"])),
                  "prior_best_FUSE91": PRIOR_BEST, "prior_best_HGBCTX": PRIOR_BEST_HGBCTX})
    audit = {"mode": "build", "generated_utc": now(), "lane": "G91-COVER",
             "winner_experiment": winner, "emission": emission, "features": names,
             "n_dots": N_DOTS, "spacing_px": SPACING,
             "min_catalogue_distance_px_RECEIPT": round(float(dcat[dots].min()), 4),
             "ring_dots_2_3px_RECEIPT": int(((dcat[dots] > 2.0) & (dcat[dots] <= 3.0)).sum()),
             "dots_on_catalogue_RECEIPT": int((dots & cat).sum()),
             "dot_set_digest": digest, "surface_sha256_f32": surf_sha,
             "novelty": nov, "sgmc_control_report_only": {"truth_px_off_catalogue": int(sgmc.sum()), **sg},
             "holdout_evidence_class": "HOLDOUT-DTI", "holdout": hold_v,
             "prior_best_FUSE91": PRIOR_BEST, "prior_best_HGBCTX": PRIOR_BEST_HGBCTX,
             "beats_FUSE91": bool(hold_v["pooled_holdout_dti"] > PRIOR_BEST),
             "beats_HGBCTX": bool(hold_v["pooled_holdout_dti"] > PRIOR_BEST_HGBCTX),
             "writer_receipt_file": str(out_path.with_suffix(".json").relative_to(ROOT)),
             "raster_sha256_RECEIPT": GIO.sha256_file(out_path),
             "raster_bytes_RECEIPT": out_path.stat().st_size,
             "submission_name": fstem, "note": note, "note_chars": len(note)}
    audit["is_duplicate"] = not (nov["surface_pass"] and nov["dots_pass_real"])
    dump(ROOT / "docs/downloads" / f"{fstem}-audit.json", audit)
    dump(ROOT / "evidence/cover91_build_20261024.json", audit)
    print(json.dumps({"file": out_path.name, "sha256": audit["raster_sha256_RECEIPT"],
                      "is_duplicate": audit["is_duplicate"], "note": note,
                      "surface_max_abs_rho": nov["surface_max_abs_spearman_all"],
                      "dots_max_directed_real": nov["dots_max_directed_frac_real"],
                      "dots_worst_real": nov["dots_worst_real_raster"]}, indent=2))
    return audit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["cache", "holdout", "build"])
    args = ap.parse_args()
    {"cache": mode_cache, "holdout": mode_holdout, "build": mode_build}[args.mode](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
