#!/usr/bin/env python3
"""S30 VCSE lane runner (lane paragraph in src/gems91/vcse30.py module docstring).

Phases:
  prep        Verify pinned inputs; build the 13 catalogue-independent VCSE
              channels + GDR prior digest check; run Rule-4 single-channel
              holdout leakage canaries on the vendor/gems57 v3 buffered folds.
  experiment  --exp e1|e2|e3   Emit per-fold CELF dots from the experiment
              surface on the fold domains (visible-catalogue collar) and score
              pooled HOLDOUT-DTI (alpha=0.2, beta=0.8, 300 m) with matched
              random-NMS and static-R0 controls.
  package     Select the best experiment strictly by pooled HOLDOUT-DTI; run
              the pre-placement surface probe vs every local reference raster;
              emit the final dots with per-reference uniqueness caps; run the
              final dot checks; package via the shared submission_writer and
              validate; write the run card.
  diagnose    Post-hoc, after the candidate is frozen: blind USGS SGMC
              off-catalogue DTI (3 px and 5 px) and comparator values.

Parallel-Run Protocol: max 3 experiments / 2 h; HOLDOUT-DTI numbers carry the
evaluator version, withheld positives and 95% CI; projections are never written
as scores; promotion is a separate selector step (0 weekly slots used here).
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
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

from gems91.pdwc21 import emit_dots_celf_submodular, emit_dots_nms
from gems91.novelty import SurfaceProbe, dot_check
from gems91 import vcse30 as V
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s30-vcse"
WORK = ROOT / "data/work/s30_cache"
BUDGETS = {"e1": 37_654, "e2": 37_654, "e3": 44_090}
SPACINGS = {"e1": 3.05, "e2": 3.05, "e3": 2.80}
COLLAR_PX = 3.05
UNIQUENESS_CAP = 0.64
SEED = 520810
NOTE = "S30 VCSE vent-concordance rad+cond+GDR+seis+strain CELF dots cap0.64; see run-card"
assert len(NOTE) <= 140, len(NOTE)
EXPERIMENTS = {
    "e1": "vcse_vote_scout",
    "e2": "vcse_vote_plus_consensus",
    # E3 amended BEFORE it was run (docs/s30-vcse/preregistration-amendment.md):
    # E1 fell below the matched random control on the catalogue-recovery
    # instrument and E2's guarded consensus starved truth neighbourhoods, so the
    # third and final experiment fuses the vent lane with a supervised
    # out-of-fold catalogue-recovery prior (the validated S27 pattern).
    "e3": "vcse_supervised_oof_plus_vent",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)


def allocate(total_budget: int, areas: list[int]) -> list[int]:
    budgets, remaining = [], total_budget
    for i, a in enumerate(areas):
        q = int(round(total_budget * a / sum(areas))) if i < len(areas) - 1 else remaining
        budgets.append(q)
        remaining -= q
    return budgets


def verify_pinned_inputs() -> dict:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    needed = {"sample_submission", "existing_faults", "training_features",
              "parent_r0_zeros", "gdr_wellspring_in_footprint",
              "ext_lidar_scarp_u8", "ext_geodawn_rad_u8"}
    checked = {}
    for row in manifest["files"]:
        if row["id"] not in needed:
            continue
        p = ROOT / "data" / row["local_subpath"]
        if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
            raise ValueError(f"Pinned input absent or drifted: {row['id']}")
        checked[row["id"]] = {"path": "data/" + row["local_subpath"], "sha256": row["sha256"]}
    return checked


def reference_rasters() -> list[dict]:
    """All locally available registry witnesses, deduped by sha256."""
    entries: list[dict] = []
    seen: set[str] = set()
    sources = []
    for p in sorted((ROOT / "data/s22-nine-sites").glob("*.tif")):
        sources.append(("nine-site-leader", p))
    nine = ("gemsdoe24", "gemsdoe25", "gemsdoe27", "gemsdoe28", "gemsdoe30",
            "gemsdoe31", "gemsdoe32", "gemsdoe33", "gemsdoe36")
    for p in sorted((ROOT / "data/fleet_registry").glob("*.tif")):
        # IR-S30-05: duplicate gate covers the nine listed GEMSDOE sites and the
        # pinned registry only.  Dense learning probes (r11_greedy_mp 272,853
        # dots etc.) are education artefacts; their 3px halos tile 99.87% of the
        # candidate domain, which would make ANY submission a "duplicate".
        if any(k in p.name.lower() for k in nine):
            sources.append(("fleet-registry", p))
    for p in sorted((ROOT / "data/registry").glob("*.tif")):
        sources.append(("pinned-registry", p))
    for kind, p in sources:
        h = sha(p)
        if h in seen:
            continue
        seen.add(h)
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        n_pos = int((np.nan_to_num(arr, nan=0.0) > 0).sum())
        entries.append({"kind": kind, "path": str(p.relative_to(ROOT)), "sha256": h,
                        "positive_pixels": n_pos,
                        "is_competitive_sparse_le_90k": bool(n_pos <= 90_000)})
    return entries


def build_surfaces(exp: str, refs: list[dict], footprint: np.ndarray):
    cache = WORK / "vcse_core.npz"
    if not cache.is_file():
        raise RuntimeError("run 'prep' first")
    with np.load(cache) as z:
        surf_e1 = z["surface_e1"]
    if exp == "e1":
        return surf_e1, None
    if exp == "e2":
        cons_file = WORK / "consensus.npy"
        if cons_file.is_file():
            consensus = np.load(cons_file)
        else:
            dots = []
            for r in refs:
                with rasterio.open(ROOT / r["path"]) as ds:
                    dots.append(np.nan_to_num(ds.read(1), nan=0.0))
            consensus = V.consensus_surface(dots, footprint)
            np.save(cons_file, consensus)
            del dots
            gc.collect()
        surf = (0.55 * consensus + 0.45 * surf_e1).astype(np.float32)
        surf[~footprint] = 0.0
        return surf, consensus
    if exp == "e3":
        oof_file = WORK / "e3_oof_surface.npy"
        if not oof_file.is_file():
            raise RuntimeError("run 'experiment --exp e3' to build the OOF surface")
        oof = np.load(oof_file)
        surf = (0.60 * oof + 0.40 * surf_e1).astype(np.float32)
        surf[~footprint] = 0.0
        return surf, None
    raise AssertionError(exp)


def build_e3_oof_surface(g, folds) -> tuple[np.ndarray, list[dict]]:
    """Supervised out-of-fold catalogue-recovery prior (hide-and-recover legal).

    For each v3 fold: positives = that fold's VISIBLE catalogue pixels; negatives
    = 4x subsample of non-catalogue training-domain pixels; features = the 13
    catalogue-independent VCSE channels (+ vent/struct vote fractions); model =
    the S25-pinned HistGradientBoosting parameters.  The held quadrant is never
    seen in training.  Returns the stitched OOF surface plus per-fold canary
    AUCs of the OOF surface against the withheld truth (Rule-4 on the derived
    surface; stop above 0.90).
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    HGB = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
               min_samples_leaf=40, l2_regularization=1.0, early_stopping=False)
    with np.load(WORK / "vcse_core.npz") as z:
        feat_names = list(V.ALL_CHANNELS) + ["vent_frac", "struct_frac"]
        feats = np.stack([z[n] for n in feat_names], axis=-1)  # (H, W, 15)
    h, w, k = feats.shape
    oof_stack = np.zeros((len(folds), h, w), np.float32)
    canary_rows = []
    for fidx, fold in enumerate(folds):
        pos = fold["visible"]
        neg_pool = g.footprint & ~g.catalogue & fold["train"]
        neg_idx = np.flatnonzero(neg_pool.ravel())
        rng = np.random.default_rng(SEED + 104729 * fidx)
        take = min(4 * int(pos.sum()), neg_idx.size)
        neg_sel = np.zeros(neg_pool.size, bool)
        neg_sel[rng.choice(neg_idx, size=take, replace=False)] = True
        neg = neg_sel.reshape(neg_pool.shape)
        tr = pos | neg
        X = feats[tr].astype(np.float64)
        y = np.concatenate([np.ones(int(pos.sum()), np.uint8),
                            np.zeros(int(neg.sum()), np.uint8)])
        clf = HistGradientBoostingClassifier(random_state=SEED, **HGB)
        clf.fit(X, y)
        del X, y
        gc.collect()
        oof_stack[fidx] = clf.predict_proba(feats.reshape(-1, k))[:, 1].reshape(h, w).astype(np.float32)
        # Rule-4 canary of the derived OOF surface vs withheld truth in its fold
        valid = g.footprint & fold["region"] & ~fold["visible"]
        pv = oof_stack[fidx][fold["truth"] & valid]
        nv = oof_stack[fidx][(~fold["truth"]) & valid][::4]
        auc = float(roc_auc_score(np.concatenate([np.ones(pv.size), np.zeros(nv.size)]),
                                  np.concatenate([pv, nv])))
        sym = max(auc, 1.0 - auc)
        canary_rows.append({"feature": "e3_oof_surface", "scope": f"fold{fidx}",
                            "auc": round(auc, 6), "symmetric_auc": round(sym, 6)})
        log(f"  e3 OOF fold{fidx}: surface canary AUC={auc:.4f} (sym {sym:.4f})")
        if sym > 0.90:
            raise RuntimeError(f"OOF surface canary exceeded 0.90 in fold{fidx}: {sym:.4f}")
    # Stitched deployment product: each pixel takes its own quadrant's OOF slice
    stitched = np.zeros((h, w), np.float32)
    for fold in folds:
        stitched[fold["region"]] = oof_stack[fold["fold"]][fold["region"]]
    np.savez_compressed(WORK / "e3_oof_stack.npz", stack=oof_stack)
    np.save(WORK / "e3_oof_surface.npy", stitched)
    return oof_stack, canary_rows


def score_arm_on_folds(arm: str, surf, g, folds, budgets, spacing,
                       consensus=None) -> tuple[np.ndarray, list[dict]]:
    total_terms = None
    per_fold = []
    for fidx, fold in enumerate(folds):
        dom = g.footprint & fold["region"]
        s = surf[fidx] if isinstance(surf, list) else surf
        if consensus is not None:
            # Hide-and-recover: registry-consensus encodes the full catalogue's
            # geometry, so within the 80 px feature-context buffer of a withheld
            # component the consensus channel is removed for this fold.
            held = np.asarray(fold["held_all"], bool)
            if held.any():
                dist_held = ndi.distance_transform_edt(~held)
                s = np.where(dist_held > 80.0, surf, 0.0).astype(np.float32)
        pred = emit_dots_celf_submodular(
            s, fold["visible"], dom, budget=int(budgets[fidx]),
            collar_px=COLLAR_PX, min_spacing_px=spacing)
        res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                 origin=(0, 0), global_shape=g.shape)
        total_terms = terms if total_terms is None else total_terms + terms
        per_fold.append({"arm": arm, "fold": fidx, "budget": int(budgets[fidx]),
                         "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                         "tpw": round(float(res["tpw"]), 3), "fpw": round(float(res["fpw"]), 3),
                         "fnw": round(float(res["fnw"]), 3),
                         "fold_dti": round(float(EH.from_terms(terms.sum(axis=0))), 6)})
        log(f"  {arm} fold{fidx}: dti={per_fold[-1]['fold_dti']:.6f} "
            f"emitted={per_fold[-1]['n_emitted']}/{budgets[fidx]} truth={per_fold[-1]['n_truth']}")
        del pred
        gc.collect()
    return total_terms, per_fold


def score_random_control(arm: str, g, folds, budgets, spacing) -> tuple[np.ndarray, list[dict]]:
    total_terms = None
    per_fold = []
    for fidx, fold in enumerate(folds):
        dom = g.footprint & fold["region"]
        rng = np.random.default_rng(SEED + 7919 * fidx)
        surf = rng.random(g.shape, dtype=np.float32)
        surf[~dom] = 0.0
        pred = emit_dots_nms(surf, fold["visible"], dom, budget=int(budgets[fidx]),
                             collar_px=COLLAR_PX, min_spacing_px=spacing)
        res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                 origin=(0, 0), global_shape=g.shape)
        total_terms = terms if total_terms is None else total_terms + terms
        per_fold.append({"arm": arm, "fold": fidx, "budget": int(budgets[fidx]),
                         "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                         "fold_dti": round(float(EH.from_terms(terms.sum(axis=0))), 6)})
        del pred, surf
        gc.collect()
    return total_terms, per_fold


def score_static_arm(arm: str, raster_path: Path, g, folds) -> tuple[np.ndarray, list[dict]]:
    with rasterio.open(raster_path) as ds:
        arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
    total_terms = None
    per_fold = []
    for fidx, fold in enumerate(folds):
        dom = g.footprint & fold["region"]
        pred = np.where(dom, arr, 0.0)
        res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                 origin=(0, 0), global_shape=g.shape)
        total_terms = terms if total_terms is None else total_terms + terms
        per_fold.append({"arm": arm, "fold": fidx, "budget": int((pred > 0).sum()),
                         "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                         "fold_dti": round(float(EH.from_terms(terms.sum(axis=0))), 6)})
    return total_terms, per_fold


# ------------------------------------------------------------------ prep
def cmd_prep(_args) -> int:
    t0 = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")

    core = WORK / "vcse_core.npz"
    if core.is_file():
        log("VCSE core already computed")
    else:
        log("Loading pinned rasters")
        with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
            raw19 = ds.read()
        with rasterio.open(ROOT / "data/external/geodawn_rad_u8.tif") as ds:
            rad = ds.read()
        with rasterio.open(ROOT / "data/external/lidar_scarp_features_u8.tif") as ds:
            lidar = ds.read()
        log("Building 13 VCSE channels")
        built = V.build_channels(raw19, rad, lidar,
                                 ROOT / "data/external/gdr_wellspring_in_footprint.csv",
                                 g.footprint)
        surf = V.vote_surface(built["channels"], g.footprint, raw19, lidar)
        del raw19, rad, lidar
        gc.collect()

        # GDR prior digest contract (IR-91-18): the rebuilt prior must match the
        # digest pinned in registry/derived_priors.json (kind "all").
        pinned = json.loads((ROOT / "registry/derived_priors.json").read_text())
        expect = next(p for p in pinned["priors"] if p["kind"] == "all")["array_digest"]
        if built["gdr_prior_digest"] != expect:
            raise ValueError(f"GDR prior digest drift: {built['gdr_prior_digest']} != {expect}")

        np.savez_compressed(
            core, surface_e1=surf["surface_e1"], vent_frac=surf["vent_frac"],
            struct_frac=surf["struct_frac"], **built["channels"])
        dump(OUT / "feature-receipt.json", {
            "inputs_verified": inputs,
            "gdr_prior_digest": built["gdr_prior_digest"],
            "gdr_prior_digest_pinned": expect,
            "gdr_features": built["gdr_features"],
            "playa_veto_px": surf["playa_veto_px"],
            "channels": V.ALL_CHANNELS,
            "lane_paragraph": "src/gems91/vcse30.py module docstring",
        })
        log(f"channels cached; GDR digest PASS; playa veto {surf['playa_veto_px']} px")

    # ---- Rule-4 single-channel leakage canaries on v3 buffered folds ----
    can_path = OUT / "canaries.json"
    if can_path.is_file():
        log("canaries already recorded")
        return 0
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    with np.load(core) as z:
        names = [n for n in z.files if n in V.ALL_CHANNELS or n == "surface_e1"]
        canaries = []
        max_sym, worst = 0.0, None
        for name in names:
            vec = z[name]
            pool_pos, pool_neg = [], []
            for fidx, fold in enumerate(folds):
                valid = g.footprint & fold["region"] & ~fold["visible"]
                pv = np.asarray(vec[fold["truth"] & valid], np.float64)
                nv = np.asarray(vec[(~fold["truth"]) & valid][::4], np.float64)
                pool_pos.append(pv)
                pool_neg.append(nv)
                y = np.concatenate([np.ones(pv.size), np.zeros(nv.size)])
                s = np.concatenate([pv, nv])
                auc = float(roc_auc_score(y, s))
                sym = max(auc, 1.0 - auc)
                if sym > max_sym:
                    max_sym, worst = sym, f"{name} fold{fidx}"
                canaries.append({"feature": name, "scope": f"fold{fidx}",
                                 "n_positive": int(pv.size), "n_negative": int(nv.size),
                                 "auc": round(auc, 6), "symmetric_auc": round(sym, 6)})
            pp = np.concatenate(pool_pos)
            pn = np.concatenate(pool_neg)
            auc_p = float(roc_auc_score(np.concatenate([np.ones(pp.size), np.zeros(pn.size)]),
                                        np.concatenate([pp, pn])))
            sym_p = max(auc_p, 1.0 - auc_p)
            if sym_p > max_sym:
                max_sym, worst = sym_p, f"{name} pooled"
            canaries.append({"feature": name, "scope": "pooled",
                             "n_positive": int(pp.size), "n_negative": int(pn.size),
                             "auc": round(auc_p, 6), "symmetric_auc": round(sym_p, 6)})
    dump(can_path, {
        "rule": "Rule-4 single-feature holdout leakage canary",
        "threshold": 0.90, "max_symmetric_auc": round(float(max_sym), 6),
        "worst": worst, "all_pass": bool(max_sym <= 0.90),
        "evaluator_version": EH.VERSION,
        "split_version": folds[0]["receipt"]["split_version"],
        "fold_receipts": [f["receipt"] for f in folds],
        "canaries": canaries,
        "elapsed_seconds": round(time.monotonic() - t0, 1),
    })
    log(f"canaries: max symmetric AUC={max_sym:.4f} ({worst}) "
        f"{'PASS' if max_sym <= 0.90 else 'FAIL'}")
    return 0 if max_sym <= 0.90 else 1


# ------------------------------------------------------------ experiment
def cmd_experiment(args) -> int:
    t0 = time.monotonic()
    exp = args.exp
    if exp not in EXPERIMENTS:
        raise ValueError(f"exp must be one of {list(EXPERIMENTS)}")
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").is_file():
        log(f"{exp} already recorded")
        return 0
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("Rule-4 canary failed; stopping lane")
    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGETS[exp], areas)
    refs = reference_rasters()
    log(f"{exp}: surface build ({EXPERIMENTS[exp]}), budget={BUDGETS[exp]}")
    fold_surfs = None
    if exp == "e3":
        # Honest hide-and-recover: fold f must be scored with the OOF slice that
        # never trained on fold f's quadrant.
        oof_file = WORK / "e3_oof_surface.npy"
        if not oof_file.is_file():
            log("building supervised OOF recovery prior (e3)")
            _, can_rows = build_e3_oof_surface(g, folds)
            can["canaries"].extend(can_rows)
            can["max_symmetric_auc"] = max(can["max_symmetric_auc"],
                                           max(r["symmetric_auc"] for r in can_rows))
            dump(OUT / "canaries.json", can)
        with np.load(WORK / "vcse_core.npz") as z:
            e1 = z["surface_e1"]
        stack_file = WORK / "e3_oof_stack.npz"
        if stack_file.is_file():
            oof_stack = np.load(stack_file)["stack"]
        else:
            oof_stack, _ = build_e3_oof_surface(g, folds)
        fold_surfs = [np.where(g.footprint, 0.60 * oof_stack[f] + 0.40 * e1, 0.0).astype(np.float32)
                      for f in range(len(folds))]
        del oof_stack
        gc.collect()
    surf, consensus = build_surfaces(exp, refs, g.footprint)

    log("scoring candidate arm on 4 v3 folds")
    t_cand, pf_cand = score_arm_on_folds(EXPERIMENTS[exp], fold_surfs if fold_surfs is not None else surf,
                                         g, folds, budgets,
                                         SPACINGS[exp], consensus=consensus)
    log("scoring matched random NMS control")
    t_rand, pf_rand = score_random_control("control_random_nms", g, folds, budgets, SPACINGS[exp])
    log("scoring static R0 anchor")
    t_r0, pf_r0 = score_static_arm("control_static_r0",
                                   ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif",
                                   g, folds)

    arms = {EXPERIMENTS[exp]: t_cand, "control_random_nms": t_rand, "control_static_r0": t_r0}
    pooled = EH.pooled_summary(arms, draws=1000, seed=SEED, candidate=EXPERIMENTS[exp])
    pooled["per_fold"] = pf_cand + pf_rand + pf_r0
    pooled["fold_receipts"] = [f["receipt"] for f in folds]
    pooled["budget_total"] = BUDGETS[exp]
    pooled["spacing_px"] = SPACINGS[exp]
    pooled["collar_px"] = COLLAR_PX
    pooled["elapsed_seconds"] = round(time.monotonic() - t0, 1)
    dump(outdir / "holdout.json", pooled)
    for a, s in pooled["scores"].items():
        log(f"  HOLDOUT-DTI {a} = {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    return 0


# --------------------------------------------------------------- package
def cmd_package(_args) -> int:
    t0 = time.monotonic()
    verify_pinned_inputs()
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("canary failed; cannot package")
    g = grid.load_grid(ROOT / "data/official")
    refs = reference_rasters()
    log(f"{len(refs)} unique local reference rasters (sha-deduped)")

    summaries = {}
    for exp in EXPERIMENTS:
        hp = OUT / exp / "holdout.json"
        if not hp.is_file():
            raise RuntimeError(f"missing {hp}")
        hh = json.loads(hp.read_text())
        summaries[exp] = {"arm": EXPERIMENTS[exp], "dti": float(hh["scores"][EXPERIMENTS[exp]]["dti"]),
                          "ci95": hh["scores"][EXPERIMENTS[exp]]["ci95"], "holdout": hh}
    best_exp = max(EXPERIMENTS, key=lambda e: summaries[e]["dti"])
    log(f"best by pooled HOLDOUT-DTI: {best_exp} = {summaries[best_exp]['dti']:.6f}")

    surf, consensus = build_surfaces(best_exp, refs, g.footprint)

    # Rule-1 Phase-1: pre-placement surface probe vs every reference
    probe = SurfaceProbe(surf, g.footprint)
    surface_checks = []
    max_rho, max_rho_ref = 0.0, None
    for r in refs:
        with rasterio.open(ROOT / r["path"]) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float64)
        res = probe.compare(arr)
        rho = abs(res["rank_correlation"] or 0.0)
        surface_checks.append({**r, "rank_correlation": res["rank_correlation"],
                               "status": res["status"]})
        if rho > max_rho:
            max_rho, max_rho_ref = rho, r["path"]
        del arr
    log(f"surface probe: max |rho| = {max_rho:.4f} vs {max_rho_ref}")
    if max_rho > 0.90:
        dump(OUT / "package-failed-surface.json", {"max_rho": max_rho,
                                                   "ref": max_rho_ref,
                                                   "surface_checks": surface_checks})
        raise RuntimeError("Rule-1 Phase-1 stop: surface rank correlation > 0.90")

    # Final emission with per-reference uniqueness caps
    halo_path = WORK / "ref_halo_words.npy"
    if halo_path.is_file():
        halo_words = np.load(halo_path)
    else:
        n_refs = len(refs)
        n_words = (n_refs + 63) // 64
        h, w = g.shape
        halo_words = np.zeros((h, w, n_words), dtype=np.uint64)
        y_g, x_g = np.ogrid[-3:4, -3:4]
        struct_3px = (y_g * y_g + x_g * x_g) <= 9
        for idx, r in enumerate(refs):
            with rasterio.open(ROOT / r["path"]) as ds:
                arr = np.nan_to_num(ds.read(1), nan=0.0)
            pos = (arr > 0.0) & g.footprint
            halo = ndi.binary_dilation(pos, structure=struct_3px)
            halo_words[halo, idx >> 6] |= np.uint64(1) << np.uint64(idx & 63)
            del arr, pos, halo
            if idx % 20 == 0:
                log(f"  halo {idx}/{n_refs}")
        np.save(halo_path, halo_words)
    n_refs = len(refs)
    log(f"emitting {BUDGETS[best_exp]} dots via CELF (cap={UNIQUENESS_CAP} vs {n_refs} refs)")
    dots = emit_dots_celf_submodular(
        surf, g.catalogue, g.footprint, budget=BUDGETS[best_exp],
        collar_px=COLLAR_PX, min_spacing_px=SPACINGS[best_exp],
        ref_halo_words=halo_words, n_refs=n_refs, uniqueness_cap=UNIQUENESS_CAP)
    n_dots = int((dots > 0).sum())
    log(f"placed {n_dots} dots")

    # Rule-1 Phase-2: final dot checks vs every reference
    dot_checks = []
    max_ov, max_ov_ref = 0.0, None
    for r in refs:
        with rasterio.open(ROOT / r["path"]) as ds:
            arr = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float64)
        res = dot_check(dots.astype(np.float64), arr, g.footprint)
        dot_checks.append({**r, "overlap_within_3px": res["overlap_within_3px"],
                           "status": res["status"]})
        ov = res["overlap_within_3px"] or 0.0
        if ov > max_ov:
            max_ov, max_ov_ref = ov, r["path"]
        del arr
    log(f"final dots: max 3px overlap {max_ov*100:.2f}% vs {max_ov_ref}")
    if max_ov > 0.70:
        dump(OUT / "package-failed-dots.json", {"max_overlap": max_ov, "ref": max_ov_ref,
                                                "dot_checks": dot_checks})
        raise RuntimeError("Rule-1 Phase-2 stop: >70% dot overlap with a registry raster")

    # package via shared writer (all-finite zeros-outside encoding)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha8 = hashlib.sha256(dots.tobytes()).hexdigest()[:8]
    stem = f"gems91-s30-vcse-{best_exp}-{n_dots}dots-{stamp}-{sha8}-zeros"
    name = stem
    tif_path = ROOT / "docs/downloads" / f"{stem}.tif"
    meta = {
        "lane": "VCSE-30 vent-concordance strand emission (src/gems91/vcse30.py)",
        "experiment": best_exp, "holdout_dti": summaries[best_exp]["dti"],
        "holdout_ci95": summaries[best_exp]["ci95"],
        "evaluator_version": EH.VERSION, "uniqueness_cap": UNIQUENESS_CAP,
        "n_reference_witnesses": n_refs, "max_surface_rho": max_rho,
        "max_dot_overlap": max_ov,
    }
    receipt = write_submission(tif_path, dots, ROOT / "data/official/sample_submission.tif",
                               g.footprint, note=NOTE, name=name, catalogue=g.catalogue,
                               metadata=meta)
    zip_path = tif_path.with_suffix(".zip")
    log(f"wrote {tif_path.name} and {zip_path.name}")
    v = validate(tif_path, g.footprint, g.catalogue)
    assert_submittable(v)
    log("validator: " + json.dumps(v.get("checks", v), default=str))

    raster_sha = sha(tif_path)
    run_card = {
        "schema": "gems91.s30-vcse-run-card.v1",
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "lane": {
            "id": "S30-VCSE",
            "paragraph": ("Vent-Concordance Strand Emission: predict unmapped fault strands where "
                          "geothermal-vent evidence concurs (radiometric alteration K/Th/U/TC, "
                          "conductive clay-cap cond_surf, GDR warm springs, seismicity deq/ieq, "
                          "strain 2nd-invariant/shear/dilatation), corroborated by magnetic/gravity "
                          "edges, cover-thickness steps and lidar scarps; CELF binary-dot emission."),
            "assignment_source": ("standing brief: 'scientific discovery of geothermal vents' + "
                                  "'find sources of data that others are overlooking'; no other "
                                  "authenticated lane paragraph supplied (IR-S30-01)"),
        },
        "hypothesis": ("Hidden faults in a geothermal province carry a vent/alteration + strain "
                       "concordance signature that mapped-fault-adjacent ridge networks (the "
                       "0.24-0.28 family) do not fully occupy; off-collar dots placed on "
                       "multi-channel concordance cells recover more hidden truth per dot than "
                       "family-clutter dots."),
        "mechanism": ("Hydrothermal upflow along permeable fault strands produces K-depletion/"
                      "Th-U-fractionation anomalies, conductive clay caps and warm springs; "
                      "seismogenic and straining crust marks active slip; differential-depth "
                      "edges (gravity vs magnetics vs cover steps) discriminate faults from "
                      "lithologic contacts."),
        "non_fault_mimic": ("Playa/lake-bottom conductivity: saline basin floors are conductive, "
                            "K-poor, flat and lidar-incoherent; gated by the basin-floor veto and "
                            "by requiring structural concurrence (vent evidence alone cannot "
                            "emit). Alluvial-fan radiometric noise: vetoed by the same rule."),
        "experiments": {e: {"arm": EXPERIMENTS[e], "holdout_dti": summaries[e]["dti"],
                            "ci95": summaries[e]["ci95"]} for e in EXPERIMENTS},
        "selected_experiment": best_exp,
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "split_version": "label-blind-quadrants-v3-feature-buffered",
            "value": summaries[best_exp]["dti"],
            "ci95": summaries[best_exp]["ci95"],
            "withheld_positive_count": int(sum(
                f["n_truth"] for f in summaries[best_exp]["holdout"]["per_fold"]
                if f["arm"] == EXPERIMENTS[best_exp])),
            "pooled_dti_alpha": 0.2, "pooled_dti_beta": 0.8,
            "distance_support_m": 300,
            "live_correlation_caveat": ("hide-v2-family holdout correlates ~0.105 with live "
                                        "scores across 112 anchors (S22 instruments.json); "
                                        "holdout is a promotion gate, not a leaderboard estimate"),
        },
        "controls": {
            "control_random_nms": summaries[best_exp]["holdout"]["scores"]["control_random_nms"],
            "control_static_r0": summaries[best_exp]["holdout"]["scores"]["control_static_r0"],
        },
        "leakage_canaries": {"max_symmetric_auc": can["max_symmetric_auc"],
                             "all_pass": can["all_pass"], "threshold": 0.90},
        "registry_uniqueness": {
            "surface_max_abs_rank_correlation": max_rho,
            "surface_max_reference": max_rho_ref,
            "dot_max_overlap_within_3px": max_ov,
            "dot_max_reference": max_ov_ref,
            "thresholds": {"rank_correlation": 0.90, "dot_overlap": 0.70},
            "references_checked": n_refs,
            "unavailable_witnesses": [
                "docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21-zeros.tif (local inherited; no upstream mirror)",
                "docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21.tif (local inherited; no upstream mirror)"],
        },
        "raster_sha256": raster_sha,
        "validator_output": v,
        "submission": {"name": name, "note": NOTE,
                       "tif": str(tif_path.relative_to(ROOT)),
                       "zip": str(zip_path.relative_to(ROOT)),
                       "n_dots": n_dots,
                       "encoding": "all-finite float32 {0,1} zeros outside dots (safe for "
                                   "'Predicted values must be in range [0, 1]')"},
        "leaderboard_estimate": {
            "organizer_confirmed": None,
            "model_projection": None,
            "family_inversion_bracket": None,
            "note": "filled by the diagnose phase; projections are never scores",
        },
        "verdict": "pending_diagnostics",
        "budget": {"experiments_used": 3, "experiments_max": 3,
                   "weekly_submission_slots_used": 0,
                   "elapsed_seconds": round(time.monotonic() - t0, 1)},
    }
    dump(OUT / "run-card.json", run_card)
    dump(OUT / "surface-checks.json", surface_checks)
    dump(OUT / "dot-checks.json", dot_checks)
    (OUT / "latest.txt").write_text(stem + "\n")
    log("run-card written (verdict pending_diagnostics)")
    return 0


# -------------------------------------------------------------- diagnose
def cmd_diagnose(_args) -> int:
    from evaluate_holdout import score_off_catalogue_sgmc
    rc_path = OUT / "run-card.json"
    rc = json.loads(rc_path.read_text())
    if rc["verdict"] != "pending_diagnostics":
        raise RuntimeError("diagnostics already finalized")
    cand_rel = rc["submission"]["tif"]
    if sha(ROOT / cand_rel) != rc["raster_sha256"]:
        raise ValueError("candidate drift")
    g = grid.load_grid(ROOT / "data/official")
    summaries = {}
    for exp in EXPERIMENTS:
        hp = OUT / exp / "holdout.json"
        hh = json.loads(hp.read_text())
        summaries[exp] = {"dti": float(hh["scores"][EXPERIMENTS[exp]]["dti"])}
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1)
    with rasterio.open(ROOT / cand_rel) as ds:
        cand = ds.read(1)

    targets = [("vcse_candidate", cand)]
    for label, rel in [
        ("parent_r0_gemsdoe32", "data/registry/GEMSDOE32__h33-2-b2-zeros.tif"),
        ("nine_gemsoe36_anderson", "data/s22-nine-sites/GEMSDOE36.tif"),
    ]:
        with rasterio.open(ROOT / rel) as ds:
            targets.append((label, np.nan_to_num(ds.read(1), nan=0.0)))

    rows = []
    for dist in (3.0, 5.0):
        for name, arr in targets:
            res = score_off_catalogue_sgmc(arr.astype(np.float64), sgmc,
                                           np.where(g.catalogue, 1.0, 0.0),
                                           g.footprint.astype(np.float64),
                                           min_cat_dist_px=dist)
            rows.append({"name": name, "min_cat_dist_px": dist, **res})
            log(f"SGMC>{dist:.0f}px {name}: dti={res['dti']:.6f}")
    rc["diagnostics_sgmc"] = {
        "metric_label": "SGMC-OFFCAT-CONTROL-DTI (blind proxy truth; NOT a leaderboard score)",
        "rows": rows,
    }

    # Family-inversion bracket (S22 arithmetic, MODEL): given the candidate's
    # dot count n and the fitted per-dot credit of comparable de novo lanes,
    # bracket DTI under stated assumptions.  Pure arithmetic on measured
    # quantities + USER-REPORTED anchors; labelled MODEL.
    import csv as _csv
    with open(ROOT / "registry/lfi_live_anchors.csv", newline="") as fh:
        anchors = [r for r in _csv.DictReader(fh)]
    family = {"h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros": 0.2778,
              "dotted-h19-5-d2-8-20261002-e56ea318af89-nan": 0.2600}
    n = int(rc["submission"]["n_dots"])
    # S22 inversion: T(R0)=5073 for 37,654 dots (avg credit 0.135); de novo
    # dots observed at ~0.013-0.05 credit (GEMSDOE36 add-on = 0.013; S27-scale
    # de novo lanes project 0.15-0.22).  Bracket: scout dots 0.03-0.08 credit.
    t_low, t_high = 0.03 * n, 0.08 * n
    g_lo, g_hi = 12_100.0, 13_400.0

    def dti_model(t, K, n_dots, m_frac):
        m = m_frac * n_dots
        D = 0.2 * (t + n_dots - m) + 0.8 * K
        return t / D
    bracket = [dti_model(t_low, g_hi, n, 0.10), dti_model(t_high, g_lo, n, 0.25)]
    rc["leaderboard_estimate"] = {
        "organizer_confirmed": None,
        "model_projection": None,
        "family_inversion_bracket": {
            "evidence_class": "MODEL (arithmetic on USER-REPORTED anchors + S22 inversion; NOT A SCORE)",
            "range": [round(min(bracket), 4), round(max(bracket), 4)],
            "assumptions": ("per-dot truth credit 0.03-0.08 (GEMSDOE36 add-on measured 0.013; "
                            "R0 average 0.135); |G| 12,100-13,400 (S22 bracket); matched mass "
                            "M = 0.10-0.25 of n"),
            "reported_family_anchors": family,
        },
    }
    best = min(rows, key=lambda r: r["dti"] if r["min_cat_dist_px"] == 5.0 else 1e9)
    r0_5 = next(r for r in rows if r["name"] == "parent_r0_gemsdoe32" and r["min_cat_dist_px"] == 5.0)
    cand_5 = next(r for r in rows if r["name"] == "vcse_candidate" and r["min_cat_dist_px"] == 5.0)
    g5_pass = bool(cand_5["dti"] > r0_5["dti"])
    # Standing protocol (amendment): promote to a submission slot only if the
    # candidate beats the current holdout best (0.159482, S27-OSDR E2, same
    # instrument).  G5 is the blind gate; both must pass.
    best_holdout = max(float(v["dti"]) for v in summaries.values()) if summaries else 0.0
    holdout_gate = bool(best_holdout >= 0.159482)
    rc["holdout_gate"] = {"best_pooled_holdout_dti": best_holdout,
                          "bar": 0.159482, "pass": holdout_gate,
                          "bar_source": "S27-OSDR E2, gems57-pooled-hide-v2 (registered holdout best)"}
    rc["verdict"] = "promote" if (g5_pass and holdout_gate) else "negative"
    rc["submission_slot_decision"] = ("spend-slot" if (g5_pass and holdout_gate) else
                                      "hold: do NOT spend a weekly submission slot (see holdout_gate)")
    rc["verdict_rule"] = ("preregistered: G5 = blind SGMC off-catalogue DTI at 500 m must exceed "
                          "parent R0's AND the pooled HOLDOUT-DTI must beat the registered holdout "
                          "best (0.159482); verdict promote iff both pass and uniqueness/canary "
                          "gates passed. A negative result remains a deliverable.")
    rc["g5_blind_sgmc_pass"] = g5_pass
    dump(rc_path, rc)
    log(f"diagnostics done; G5 pass={g5_pass}; verdict={rc['verdict']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    p_exp = sub.add_parser("experiment")
    p_exp.add_argument("--exp", required=True, choices=list(EXPERIMENTS))
    sub.add_parser("package")
    sub.add_parser("diagnose")
    args = ap.parse_args()
    return {"prep": cmd_prep, "experiment": cmd_experiment,
            "package": cmd_package, "diagnose": cmd_diagnose}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
