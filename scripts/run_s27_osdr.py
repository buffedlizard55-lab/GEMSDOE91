#!/usr/bin/env python3
"""S27-CVDC lane runner (preregistered in docs/s27-osdr/preregistration.md).

Subcommands:
  prep        Verify pinned inputs, preregistration SHA, and 211-raster frozen
              registry; extract 38 S27-CVDC static features into a memory-bounded
              float32 memmap; run Rule-4 single-feature holdout leakage canaries.
  controls    Compute & cache matched v3-buffered holdout terms for:
                - incumbent_s25_fabric_e2 (reigning v3 holdout best: 0.147741)
                - control_oof_base (23-feature base OOF control: 0.124744)
                - control_cvdc_surface (unsupervised CVDC x OSDR surface)
                - control_gravgrad (B13 gravity horizontal-gradient rank surface)
  experiment  --exp e1|e2|e3 : Run the 3 preregistered experiments on unchanged
              vendor/gems57 v3 folds (label-blind-quadrants-v3-feature-buffered).
  package     Select best experiment strictly by pooled HOLDOUT-DTI; run Rule-1
              Phase-1 surface duplicate check across all 211 references; emit
              37,654 {0, 1} dots from the stitched 4-fold v3-buffered OOF surface
              via 300 m CELF submodular optimization (uniqueness_cap=0.64 across
              all 181 competitive sparse references); run Rule-1 Phase-2 dot
              checks; package via shared submission_writer.py + validate.py;
              write machine-readable run card.

Strictly enforces the Parallel-Run Protocol (Rules 1-6): max 3 experiments,
< 2 hours wall-clock, zero weekly submission slots spent, fail-closed gates.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")

import argparse
import gc
import hashlib
import json
import resource
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

from gems91 import fabric25
from gems91.capacity import capacity_bound
from gems91.cvdc_osdr27 import (
    ALL_STATIC_NAMES,
    COVER_INDEX_COL,
    PURE_SUBSURFACE_INDICES,
    PURE_SUBSURFACE_NAMES,
    TOPO_DISCORDANCE_NAMES,
    compute_cvdc27_features,
    compute_cvdc_crest_fp,
    compute_osdr_sub_backbone_fp,
    ensure_raw19_memmap,
)
from gems91.io import dot_digest
from gems91.novelty import SurfaceProbe, dot_check
from gems91.pdwc21 import (
    PDWC21_AC_FULL_NAMES,
    compute_directional_ac_8,
    emit_dots_celf_submodular,
    emit_dots_nms,
    fit_predict_pdwc_specialist,
    pool_asymmetric_cover_rescue,
)
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s27-osdr"
WORK = ROOT / "data/work/s27_cache"
PREREG_PATH = OUT / "preregistration.md"
PREREG_SHA256 = "df5f5e820fbd3d5265ebcbc888bddf20a17617b859900924cbc39c03f2f3b389"
FROZEN_REG_PATH = OUT / "frozen-registry.json"

BUDGET = 37_654
COLLAR_PX = 3.05
SPACING_PX = 3.05
UNIQUENESS_CAP = 0.64
SEED = 520810

# Exact S25 HGB params for byte-reproducible matched controls (incumbent_s25_fabric_e2 & control_oof_base)
S25_HGB_PARAMS = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=40,
    l2_regularization=1.0,
    early_stopping=False,
)
S25_NEG_PER_POS = 4

CONTROLS = [
    "incumbent_s25_fabric_e2",
    "control_oof_base",
    "control_cvdc_surface",
    "control_gravgrad",
]

EXPERIMENTS = {
    "e1": "cvdc_e1_stage1_celf",
    "e2": "cvdc_e2_stage2_ac_celf",
    "e3": "cvdc_e3_dual_cover_celf",
}

NOTE = "S27 CVDC contour-potential discordance+OSDR spatial-OOF CELF 37654d; check run-card verdict"
assert len(NOTE) <= 140, len(NOTE)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def log(msg: str) -> None:
    print(
        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z | peakRSS={rss_mb():.0f}MB] {msg}",
        flush=True,
    )


def allocate(total_budget: int, areas: list[int]) -> list[int]:
    budgets, remaining = [], total_budget
    for i, a in enumerate(areas):
        q = int(round(total_budget * a / sum(areas))) if i < len(areas) - 1 else remaining
        budgets.append(q)
        remaining -= q
    return budgets


def verify_pinned_inputs() -> dict:
    if not PREREG_PATH.is_file() or sha(PREREG_PATH) != PREREG_SHA256:
        raise ValueError("preregistration.md missing or SHA drifted after freeze")
    if not FROZEN_REG_PATH.is_file():
        raise ValueError("docs/s27-osdr/frozen-registry.json missing; must freeze before execution")

    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        if row["id"] in {
            "sample_submission",
            "existing_faults",
            "training_features",
            "parent_r0_zeros",
            "sgmc_faults_control",
        }:
            p = ROOT / "data" / row["local_subpath"]
            if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
                raise ValueError(f"Pinned input absent or drifted: {row['id']}")
            checked[row["id"]] = {
                "path": "data/" + row["local_subpath"],
                "sha256": row["sha256"],
                "bytes": row["bytes"],
            }
    return checked


def open_static_memmap(n_fp: int, mode: str = "r") -> np.memmap:
    p = WORK / "cvdc27_static38.f32.mmap"
    return np.memmap(p, dtype="float32", mode=mode, shape=(n_fp, len(ALL_STATIC_NAMES)))


# ------------------------------------------------------------------------ prep
def cmd_prep(_args) -> int:
    t0 = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    n_fp = int(g.footprint.sum())

    log("Ensuring raw 19-band float32 memmap cache")
    raw19 = ensure_raw19_memmap(
        ROOT / "data/bridge/gems-geodawn-numerical-features.tif",
        WORK / "raw19.f32.mmap",
    )

    static_mmap_path = WORK / "cvdc27_static38.f32.mmap"
    ctrl_cvdc_path = WORK / "control_cvdc_surface.npy"
    ctrl_grav_path = WORK / "control_gravgrad.npy"

    if (
        static_mmap_path.is_file()
        and static_mmap_path.stat().st_size == n_fp * len(ALL_STATIC_NAMES) * 4
        and ctrl_cvdc_path.is_file()
        and ctrl_grav_path.is_file()
        and (OUT / "feature-receipt.json").is_file()
    ):
        log("Static S27-CVDC features already cached on disk")
        X_static = open_static_memmap(n_fp, "r")
        ctrl_cvdc = np.load(ctrl_cvdc_path)
        ctrl_grav = np.load(ctrl_grav_path)
    else:
        log("Computing 38 S27-CVDC static features into float32 memmap")
        X_mm = open_static_memmap(n_fp, "w+")
        _, surfs, receipt = compute_cvdc27_features(raw19, g.footprint, out_fp_matrix=X_mm)
        ctrl_cvdc = surfs["control_cvdc_surface"]
        ctrl_grav = surfs["control_gravgrad"]
        np.save(ctrl_cvdc_path, ctrl_cvdc)
        np.save(ctrl_grav_path, ctrl_grav)
        receipt["inputs_verified"] = inputs
        receipt["preregistration"] = {
            "path": "docs/s27-osdr/preregistration.md",
            "sha256": sha(PREREG_PATH),
        }
        receipt["frozen_registry"] = {
            "path": "docs/s27-osdr/frozen-registry.json",
            "sha256": sha(FROZEN_REG_PATH),
        }
        dump(OUT / "feature-receipt.json", receipt)
        del X_mm
        X_static = open_static_memmap(n_fp, "r")

    log("Running Rule-4 single-feature holdout leakage canaries across all 38 features + 2 surfaces")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fp_idx_grid = np.full(g.shape, -1, dtype=np.int32)
    fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int32)

    canaries = []
    max_sym = 0.0
    worst = None

    # Check all 38 static features per-fold and pooled
    for col_j, name in enumerate(ALL_STATIC_NAMES):
        vec_fp = X_static[:, col_j]
        pool_pos, pool_neg = [], []
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pos_rows = fp_idx_grid[fold["truth"] & valid]
            neg_rows = fp_idx_grid[(~fold["truth"]) & valid][::4]
            pv = np.asarray(vec_fp[pos_rows], dtype=np.float64)
            nv = np.asarray(vec_fp[neg_rows], dtype=np.float64)
            pool_pos.append(pv)
            pool_neg.append(nv)
            y = np.concatenate([np.ones(pv.size), np.zeros(nv.size)])
            s = np.concatenate([pv, nv])
            auc = float(roc_auc_score(y, s))
            sym = max(auc, 1.0 - auc)
            if sym > max_sym:
                max_sym, worst = sym, f"{name} fold{fidx}"
            canaries.append(
                {
                    "feature": name,
                    "scope": f"fold{fidx}",
                    "n_positive": int(pv.size),
                    "n_negative": int(nv.size),
                    "auc": auc,
                    "symmetric_auc": sym,
                }
            )
        pp = np.concatenate(pool_pos)
        pn = np.concatenate(pool_neg)
        auc_p = float(roc_auc_score(np.concatenate([np.ones(pp.size), np.zeros(pn.size)]), np.concatenate([pp, pn])))
        sym_p = max(auc_p, 1.0 - auc_p)
        if sym_p > max_sym:
            max_sym, worst = sym_p, f"{name} pooled"
        canaries.append(
            {
                "feature": name,
                "scope": "pooled",
                "n_positive": int(pp.size),
                "n_negative": int(pn.size),
                "auc": auc_p,
                "symmetric_auc": sym_p,
            }
        )

    for sname, sarr in [("control_cvdc_surface", ctrl_cvdc), ("control_gravgrad", ctrl_grav)]:
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pv = np.asarray(sarr[fold["truth"] & valid], dtype=np.float64)
            nv = np.asarray(sarr[(~fold["truth"]) & valid][::4], dtype=np.float64)
            auc = float(roc_auc_score(np.concatenate([np.ones(pv.size), np.zeros(nv.size)]), np.concatenate([pv, nv])))
            sym = max(auc, 1.0 - auc)
            if sym > max_sym:
                max_sym, worst = sym, f"{sname} fold{fidx}"
            canaries.append(
                {
                    "feature": sname,
                    "scope": f"fold{fidx}",
                    "n_positive": int(pv.size),
                    "n_negative": int(nv.size),
                    "auc": auc,
                    "symmetric_auc": sym,
                }
            )

    canary_pass = bool(max_sym <= 0.90)
    dump(
        OUT / "canaries.json",
        {
            "max_symmetric_auc": float(max_sym),
            "worst": worst,
            "all_pass": canary_pass,
            "threshold": 0.90,
            "evaluator_version": EH.VERSION,
            "split_version": folds[0]["receipt"]["split_version"],
            "n_checks": len(canaries),
            "elapsed_seconds": float(time.monotonic() - t0),
            "canaries": canaries,
        },
    )
    log(f"Canaries complete: max symmetric AUC = {max_sym:.4f} ({worst}), pass={canary_pass}")
    return 0 if canary_pass else 2


# -------------------------------------------------------------------- controls
def _ensure_s25_features(raw19: np.ndarray, g) -> dict:
    s25_dir = WORK / "s25_repro_feats"
    meta_path = s25_dir / "groups.json"
    if meta_path.is_file():
        return json.loads(meta_path.read_text())
    s25_dir.mkdir(parents=True, exist_ok=True)
    log("Building S25-FABRIC features once for exact paired incumbent comparison")
    groups, _ = fabric25.build_all(
        lambda i: np.asarray(raw19[i - 1], dtype=np.float32),
        g.footprint,
        lambda name, arr: np.save(s25_dir / f"{name}.npy", arr),
    )
    dump(meta_path, groups)
    gc.collect()
    return groups


def _s25_oof_surface(feat_names: list[str], g, folds) -> np.ndarray:
    s25_dir = WORK / "s25_repro_feats"

    def _gather(flat_idx: np.ndarray) -> np.ndarray:
        X = np.empty((len(flat_idx), len(feat_names)), dtype=np.float32)
        for j, n in enumerate(feat_names):
            X[:, j] = np.load(s25_dir / f"{n}.npy", mmap_mode="r").ravel()[flat_idx]
        return X

    out = np.zeros(g.shape, dtype=np.float64)
    flat_cat = g.catalogue.ravel()
    for fidx, fold in enumerate(folds):
        flat_train = fold["train"].ravel()
        pos = np.flatnonzero(flat_train & flat_cat)
        pool = np.flatnonzero(flat_train & ~flat_cat)
        rng = np.random.default_rng(SEED)
        neg = rng.choice(pool, size=min(S25_NEG_PER_POS * len(pos), len(pool)), replace=False)
        idx = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
        model = HistGradientBoostingClassifier(random_state=SEED, **S25_HGB_PARAMS)
        model.fit(_gather(idx), y)

        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        p_idx = np.flatnonzero(fold["region"].ravel())
        for lo in range(0, len(p_idx), 250_000):
            ch = p_idx[lo : lo + 250_000]
            acc[ch] = model.predict_proba(_gather(ch))[:, 1]
        out += acc.reshape(g.shape)
        del model, acc
        gc.collect()
        log(f"  S25 paired control ({len(feat_names)} feats) fold {fidx} done")
    return np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)


def _score_arm_on_folds(
    arm: str,
    surf: np.ndarray,
    g,
    folds: list[dict],
    budgets: list[int],
    *,
    emitter: str = "nms",
) -> tuple[np.ndarray, list[dict]]:
    total_terms = None
    per_fold = []
    for fidx, fold in enumerate(folds):
        dom = g.footprint & fold["region"]
        if emitter == "celf":
            pred = emit_dots_celf_submodular(
                surf,
                fold["visible"],
                dom,
                budget=budgets[fidx],
                collar_px=COLLAR_PX,
                min_spacing_px=SPACING_PX,
            )
        elif emitter == "nms":
            pred = emit_dots_nms(
                surf,
                fold["visible"],
                dom,
                budget=budgets[fidx],
                collar_px=COLLAR_PX,
                min_spacing_px=SPACING_PX,
            )
        else:
            raise ValueError(f"Unknown emitter: {emitter}")
        res, terms = EH.evaluate(
            pred, fold, g.footprint, block_side=200, origin=(0, 0), global_shape=g.shape
        )
        total_terms = terms if total_terms is None else total_terms + terms
        per_fold.append(
            {
                "arm": arm,
                "fold": fidx,
                "budget": budgets[fidx],
                "n_truth": int(res["n_truth"]),
                "n_emitted": int(res["n_emitted"]),
                "tpw": float(res["tpw"]),
                "fpw": float(res["fpw"]),
                "fnw": float(res["fnw"]),
                "fold_dti": float(EH.from_terms(terms.sum(axis=0))),
            }
        )
    return total_terms, per_fold


def cmd_controls(_args) -> int:
    t0 = time.monotonic()
    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)

    terms_file = WORK / "holdout-terms.npz"
    pf_file = WORK / "per-fold-controls.json"
    terms_by_arm = {}
    per_fold_all = []
    if terms_file.is_file() and pf_file.is_file():
        with np.load(terms_file) as z:
            terms_by_arm = {k: z[k] for k in z.files}
        per_fold_all = json.loads(pf_file.read_text())

    raw19 = ensure_raw19_memmap(
        ROOT / "data/bridge/gems-geodawn-numerical-features.tif",
        WORK / "raw19.f32.mmap",
    )

    if "incumbent_s25_fabric_e2" not in terms_by_arm or "control_oof_base" not in terms_by_arm:
        s25_groups = _ensure_s25_features(raw19, g)
        if "control_oof_base" not in terms_by_arm:
            log("Scoring matched control: control_oof_base")
            surf_base = _s25_oof_surface(list(s25_groups["base"]), g, folds)
            np.save(WORK / "surf_control_oof_base.npy", surf_base)
            t_b, pf_b = _score_arm_on_folds("control_oof_base", surf_base, g, folds, budgets, emitter="nms")
            terms_by_arm["control_oof_base"] = t_b
            per_fold_all.extend(pf_b)
            del surf_base
        if "incumbent_s25_fabric_e2" not in terms_by_arm:
            log("Scoring matched incumbent: incumbent_s25_fabric_e2")
            surf_inc = _s25_oof_surface(list(s25_groups["base"]) + list(s25_groups["new"]), g, folds)
            np.save(WORK / "surf_incumbent_s25_fabric_e2.npy", surf_inc)
            t_i, pf_i = _score_arm_on_folds("incumbent_s25_fabric_e2", surf_inc, g, folds, budgets, emitter="nms")
            terms_by_arm["incumbent_s25_fabric_e2"] = t_i
            per_fold_all.extend(pf_i)
            del surf_inc

    for cname, fname in [
        ("control_cvdc_surface", "control_cvdc_surface.npy"),
        ("control_gravgrad", "control_gravgrad.npy"),
    ]:
        if cname not in terms_by_arm:
            log(f"Scoring static control: {cname}")
            s = np.load(WORK / fname)
            t_c, pf_c = _score_arm_on_folds(cname, s, g, folds, budgets, emitter="nms")
            terms_by_arm[cname] = t_c
            per_fold_all.extend(pf_c)

    np.savez_compressed(terms_file, **terms_by_arm)
    dump(pf_file, per_fold_all)
    for cname in CONTROLS:
        dti = float(EH.from_terms(terms_by_arm[cname].sum(axis=0)))
        log(f"Control {cname}: HOLDOUT-DTI = {dti:.6f}")
    log(f"Controls cached in {time.monotonic() - t0:.1f}s")
    return 0


# ------------------------------------------------------------ PU Stage helpers
def _quadrant_grid(shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    yy, xx = np.indices((h, w), sparse=True)
    return (yy >= h // 2).astype(np.int8) * 2 + (xx >= w // 2).astype(np.int8)


def _mode_cols_and_hard(mode: str) -> tuple[list[int], list[int]]:
    assert mode in ("full", "sub")
    cols = list(range(len(ALL_STATIC_NAMES))) if mode == "full" else list(PURE_SUBSURFACE_INDICES)
    if mode == "full":
        hard_cols = [
            ALL_STATIC_NAMES.index("sub_grad_grav_b13"),
            ALL_STATIC_NAMES.index("raw_B19_det_slope"),
            ALL_STATIC_NAMES.index("cvdc_sin2_elev_grav_s3p5"),
        ]
    else:
        hard_cols = [
            PURE_SUBSURFACE_NAMES.index("sub_grad_grav_b13"),
            PURE_SUBSURFACE_NAMES.index("sub_grad_rtp_b02"),
            PURE_SUBSURFACE_NAMES.index("osdr_grav_step_w5"),
        ]
    return cols, hard_cols


def _ensure_outer_stage1_oof(
    mode: str,
    X_static: np.ndarray,
    g,
    folds: list[dict],
) -> np.ndarray:
    """Compute outer 4-fold v3-buffered Stage-1 OOF surface with per-fold checkpointing."""
    outer_path = WORK / f"s1_{mode}_outer_oof.npy"
    if outer_path.is_file():
        log(f"Stage-1 ({mode}) outer OOF already cached")
        return np.load(outer_path)

    cols, hard_cols = _mode_cols_and_hard(mode)
    outer_oof = np.zeros(g.shape, dtype=np.float32)
    for k, fold in enumerate(folds):
        f_cache = WORK / f"s1_{mode}_outer_fold{k}.npy"
        if f_cache.is_file():
            p_reg = np.load(f_cache)
            outer_oof[fold["region"]] = p_reg
            log(f"Stage-1 ({mode}) outer fold {k} loaded from checkpoint")
            continue
        log(f"Stage-1 ({mode}) outer fold {k}: fitting outer PU specialist")
        p_outer, _ = fit_predict_pdwc_specialist(
            blocks=[(X_static, cols)],
            hard_neg_cols_in_stack=hard_cols,
            visible_faults=fold["visible"],
            train_domain=fold["train"],
            footprint=g.footprint,
            seed=SEED + 101 * k + (0 if mode == "full" else 17),
            predict_mask=fold["region"],
        )
        p_reg = p_outer[fold["region"]].astype(np.float32)
        np.save(f_cache, p_reg)
        outer_oof[fold["region"]] = p_reg
        del p_outer, p_reg
        gc.collect()

    np.save(outer_path, outer_oof)
    return outer_oof


def _ensure_nested_ac_cache(
    mode: str,
    X_static: np.ndarray,
    g,
    folds: list[dict],
) -> list[Path]:
    """Compute nested cross-quadrant Stage-1 OOF directional AC memmaps per fold."""
    n_fp = int(g.footprint.sum())
    expected_bytes = n_fp * 8 * 2
    ac_paths = [WORK / f"ac8_{mode}_fold{k}.f16.mmap" for k in range(4)]
    if all(p.is_file() and p.stat().st_size == expected_bytes for p in ac_paths):
        log(f"Stage-1 ({mode}) nested AC caches already present for all 4 folds")
        return ac_paths

    cols, hard_cols = _mode_cols_and_hard(mode)
    quad = _quadrant_grid(g.shape)
    quad_inner_safe = {
        q: ndi.distance_transform_edt(quad != q) > 80.0 for q in range(4)
    }

    for k, fold in enumerate(folds):
        if ac_paths[k].is_file() and ac_paths[k].stat().st_size == expected_bytes:
            log(f"Stage-1 ({mode}) nested AC fold {k} already cached")
            continue

        other_quads = [q for q in range(4) if q != k]
        p_nested = np.zeros(g.shape, dtype=np.float32)
        non_train_fp = g.footprint & (~fold["train"])
        non_train_acc = np.zeros(g.shape, dtype=np.float64)

        for q_val in other_quads:
            log(f"Stage-1 ({mode}) nested fold {k} inner leave-out quadrant {q_val}: fitting")
            val_mask = fold["train"] & (quad == q_val)
            in_train = fold["train"] & quad_inner_safe[q_val]
            in_vis = fold["visible"] & quad_inner_safe[q_val]
            pred_target = val_mask | non_train_fp
            p_in, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, cols)],
                hard_neg_cols_in_stack=hard_cols,
                visible_faults=in_vis,
                train_domain=in_train,
                footprint=g.footprint,
                seed=SEED + 313 * k + 29 * q_val + (0 if mode == "full" else 7),
                predict_mask=pred_target,
            )
            p_nested[val_mask] = p_in[val_mask]
            non_train_acc[non_train_fp] += p_in[non_train_fp] / float(len(other_quads))
            del p_in
            gc.collect()

        p_nested[non_train_fp] = non_train_acc[non_train_fp].astype(np.float32)
        del non_train_acc

        log(f"Stage-1 ({mode}) nested fold {k}: computing 8 directional auto-context features")
        ac_list = compute_directional_ac_8(p_nested, g.footprint)
        tmp_path = WORK / f"ac8_{mode}_fold{k}.tmp.mmap"
        mm_ac = np.memmap(tmp_path, dtype="float16", mode="w+", shape=(n_fp, 8))
        for j, arr2d in enumerate(ac_list):
            mm_ac[:, j] = np.clip(arr2d[g.footprint], -32.0, 32.0).astype(np.float16)
        mm_ac.flush()
        del ac_list, mm_ac, p_nested
        tmp_path.replace(ac_paths[k])
        gc.collect()

    return ac_paths


def _fit_stage2_oof(
    mode: str,
    X_static: np.ndarray,
    ac_paths: list[Path],
    g,
    folds: list[dict],
) -> np.ndarray:
    assert mode in ("full", "sub")
    out_path = WORK / f"s2_{mode}_outer_oof.npy"
    if out_path.is_file():
        log(f"Stage-2 ({mode}) outer OOF already cached")
        return np.load(out_path)

    n_fp = int(g.footprint.sum())
    cols = list(range(len(ALL_STATIC_NAMES))) if mode == "full" else list(PURE_SUBSURFACE_INDICES)
    if mode == "full":
        hard_cols = [
            ALL_STATIC_NAMES.index("sub_grad_grav_b13"),
            ALL_STATIC_NAMES.index("raw_B19_det_slope"),
            len(cols) + 0,  # ac_prob_s1
        ]
    else:
        hard_cols = [
            PURE_SUBSURFACE_NAMES.index("sub_grad_grav_b13"),
            PURE_SUBSURFACE_NAMES.index("osdr_grav_step_w5"),
            len(cols) + 0,  # sub_ac_prob_s1
        ]

    s2_oof = np.zeros(g.shape, dtype=np.float32)
    for k, fold in enumerate(folds):
        log(f"Stage-2 ({mode}) outer fold {k}: fitting PU specialist with nested AC features")
        mm_ac = np.memmap(ac_paths[k], dtype="float16", mode="r", shape=(n_fp, 8))
        p2, _ = fit_predict_pdwc_specialist(
            blocks=[(X_static, cols), (mm_ac, list(range(8)))],
            hard_neg_cols_in_stack=hard_cols,
            visible_faults=fold["visible"],
            train_domain=fold["train"],
            footprint=g.footprint,
            seed=SEED + 709 * k + (3 if mode == "full" else 41),
            predict_mask=fold["region"],
        )
        s2_oof[fold["region"]] = p2[fold["region"]]
        del p2, mm_ac
        gc.collect()

    np.save(out_path, s2_oof)
    return s2_oof


# ------------------------------------------------------------------ experiment
def cmd_experiment(args) -> int:
    t0 = time.monotonic()
    exp = args.exp
    if exp not in EXPERIMENTS:
        raise ValueError(f"Unknown experiment {exp}; must be one of {list(EXPERIMENTS)}")
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").is_file():
        log(f"{exp} already recorded at {outdir / 'holdout.json'}")
        return 0

    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("Rule-4 single-feature leakage canary failed; stopping lane")

    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    n_fp = int(g.footprint.sum())
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fold_receipts = [f["receipt"] for f in folds]
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)

    terms_file = WORK / "holdout-terms.npz"
    pf_ctrl_file = WORK / "per-fold-controls.json"
    if not terms_file.is_file() or not pf_ctrl_file.is_file():
        raise RuntimeError("Run 'controls' subcommand before 'experiment'")
    with np.load(terms_file) as z:
        terms_by_arm = {k: z[k] for k in z.files}
    per_fold = list(json.loads(pf_ctrl_file.read_text()))

    X_static = open_static_memmap(n_fp, "r")
    crest_fp = compute_cvdc_crest_fp(X_static)
    cover_fp = np.clip(np.asarray(X_static[:, COVER_INDEX_COL], dtype=np.float32), 0.0, 1.0)
    cand = EXPERIMENTS[exp]

    s1_full_oof = _ensure_outer_stage1_oof("full", X_static, g, folds)

    if exp == "e1":
        # E1: Single-stage Full PU OOF + slight catalogue-blind CVDC crest sharpness + 300 m CELF
        surf_oof = pool_asymmetric_cover_rescue(
            s1_full=s1_full_oof,
            s1_sub=s1_full_oof,
            s2_full=None,
            s2_sub=None,
            cover_fp=cover_fp,
            crest_fp=crest_fp,
            sub_backbone_fp=None,
            footprint=g.footprint,
            max_cover_rescue=0.0,
            crest_alpha=0.18,
        )
    elif exp == "e2":
        ac_full_paths = _ensure_nested_ac_cache("full", X_static, g, folds)
        # Check Rule-4 leakage canary on nested OOF AC features on fold["region"]
        fp_idx_grid = np.full(g.shape, -1, dtype=np.int32)
        fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int32)
        ac_max_sym = 0.0
        for k, fold in enumerate(folds):
            mm_ac = np.memmap(ac_full_paths[k], dtype="float16", mode="r", shape=(n_fp, 8))
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pr = fp_idx_grid[fold["truth"] & valid]
            nr = fp_idx_grid[(~fold["truth"]) & valid][::4]
            for j, aname in enumerate(PDWC21_AC_FULL_NAMES):
                pv = np.asarray(mm_ac[pr, j], dtype=np.float64)
                nv = np.asarray(mm_ac[nr, j], dtype=np.float64)
                auc = float(roc_auc_score(np.concatenate([np.ones(pv.size), np.zeros(nv.size)]), np.concatenate([pv, nv])))
                ac_max_sym = max(ac_max_sym, auc, 1.0 - auc)
            del mm_ac
        log(f"E2 nested OOF auto-context canary max symmetric AUC = {ac_max_sym:.4f}")
        if ac_max_sym > 0.90:
            raise RuntimeError(f"Auto-context canary exceeded 0.90: {ac_max_sym:.4f}")

        s2_full_oof = _fit_stage2_oof("full", X_static, ac_full_paths, g, folds)
        surf_oof = pool_asymmetric_cover_rescue(
            s1_full=s1_full_oof,
            s1_sub=s1_full_oof,
            s2_full=s2_full_oof,
            s2_sub=s2_full_oof,
            cover_fp=cover_fp,
            crest_fp=crest_fp,
            sub_backbone_fp=None,
            footprint=g.footprint,
            stage2_weight=0.68,
            max_cover_rescue=0.0,
            crest_alpha=0.20,
        )
    elif exp == "e3":
        ac_full_paths = _ensure_nested_ac_cache("full", X_static, g, folds)
        s2_full_oof = _fit_stage2_oof("full", X_static, ac_full_paths, g, folds)
        s1_sub_oof = _ensure_outer_stage1_oof("sub", X_static, g, folds)
        ac_sub_paths = _ensure_nested_ac_cache("sub", X_static, g, folds)
        s2_sub_oof = _fit_stage2_oof("sub", X_static, ac_sub_paths, g, folds)
        sub_bb_fp = compute_osdr_sub_backbone_fp(X_static)
        surf_oof = pool_asymmetric_cover_rescue(
            s1_full=s1_full_oof,
            s1_sub=s1_sub_oof,
            s2_full=s2_full_oof,
            s2_sub=s2_sub_oof,
            cover_fp=cover_fp,
            crest_fp=crest_fp,
            sub_backbone_fp=sub_bb_fp,
            footprint=g.footprint,
            stage2_weight=0.68,
            max_cover_rescue=0.52,
            crest_alpha=0.20,
            sub_backbone_alpha=0.22,
        )
    else:
        raise AssertionError(exp)

    np.save(WORK / f"{exp}_oof_surface.npy", surf_oof)
    t_cand, pf_cand = _score_arm_on_folds(cand, surf_oof, g, folds, budgets, emitter="celf")
    terms_by_arm[cand] = t_cand
    per_fold.extend(pf_cand)
    np.savez_compressed(terms_file, **terms_by_arm)

    arms = [cand] + CONTROLS
    sub = {a: terms_by_arm[a] for a in arms}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=cand)
    pooled["per_fold"] = per_fold
    pooled["fold_receipts"] = fold_receipts
    pooled["matched_controls"] = CONTROLS
    pooled["budget_total"] = BUDGET
    pooled["elapsed_seconds"] = float(time.monotonic() - t0)
    dump(outdir / "holdout.json", pooled)

    for a in arms:
        s = pooled["scores"][a]
        log(f"  {a}: HOLDOUT-DTI = {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in CONTROLS:
        d = pooled["paired_differences"][c]
        log(f"  Delta vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return 0


# --------------------------------------------------------------------- package
def _pack_competitive_halos(entries: list[dict], footprint: np.ndarray) -> tuple[np.ndarray, list[dict]]:
    comp = [e for e in entries if e["is_competitive_sparse_le_90k"]]
    h, w = footprint.shape
    n_refs = len(comp)
    n_words = (n_refs + 63) // 64
    words = np.zeros((h, w, n_words), dtype=np.uint64)
    y_g, x_g = np.ogrid[-3:4, -3:4]
    struct_3px = (y_g * y_g + x_g * x_g) <= 9
    for idx, entry in enumerate(comp):
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            arr = ds.read(1)
        pos = footprint & np.isfinite(arr) & (arr > 0.0)
        halo = ndi.binary_dilation(pos, structure=struct_3px)
        words[halo, idx >> 6] |= np.uint64(1) << np.uint64(idx & 63)
        del arr, pos, halo
    return words, comp


def cmd_package(_args) -> int:
    t0 = time.monotonic()
    verify_pinned_inputs()
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("Cannot package: leakage canary failed")

    exp_summaries = {}
    for exp, arm in EXPERIMENTS.items():
        hp = OUT / exp / "holdout.json"
        if not hp.is_file():
            raise RuntimeError(f"Missing holdout.json for {exp}; run all 3 experiments first")
        hh = json.loads(hp.read_text())
        exp_summaries[exp] = {
            "arm": arm,
            "dti": float(hh["scores"][arm]["dti"]),
            "ci95": hh["scores"][arm]["ci95"],
            "holdout": hh,
        }

    # Preregistered frozen selection rule: argmax_{e1, e2, e3} HOLDOUT-DTI
    best_exp = max(EXPERIMENTS.keys(), key=lambda e: exp_summaries[e]["dti"])
    best_arm = exp_summaries[best_exp]["arm"]
    best_holdout = exp_summaries[best_exp]["holdout"]
    log(f"Selected winning experiment by HOLDOUT-DTI: {best_exp} ({best_arm}) = {exp_summaries[best_exp]['dti']:.6f}")

    g = grid.load_grid(ROOT / "data/official")
    freg = json.loads(FROZEN_REG_PATH.read_text())
    entries = freg["entries"]
    for e in entries:
        p = ROOT / e["local_path"]
        if not p.is_file() or sha(p) != e["sha256"]:
            raise ValueError(f"Frozen reference drifted: {e['local_path']}")

    # Stitched 4-fold v3-buffered OOF surface (ZERO in-sample g.catalogue training!)
    surf_oof = np.load(WORK / f"{best_exp}_oof_surface.npy")
    if not np.isfinite(surf_oof).all() or float(surf_oof.min()) < 0.0 or float(surf_oof.max()) > 1.0:
        raise ValueError("Invalid OOF surface")

    log(f"Running Rule-1 Phase-1 SurfaceProbe across all {len(entries)} frozen references")
    probe = SurfaceProbe(surf_oof, g.footprint)
    surface_checks = []
    max_rho, max_rho_path = 0.0, None
    max_rho_frozen64, max_rho_frozen64_path = 0.0, None
    for entry in entries:
        row = {
            "path": entry["local_path"],
            "sha256": entry["sha256"],
            "groups": entry["groups"],
            "in_frozen_64": entry["in_frozen_64"],
            "focus_site": entry["focus_site"],
        }
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            ref_a = np.where(g.footprint, ds.read(1), 0.0).astype(np.float32)
        res = probe.compare(ref_a)
        del ref_a
        row.update(res)
        rho = res.get("rank_correlation")
        if rho is not None:
            if abs(rho) > max_rho:
                max_rho, max_rho_path = float(abs(rho)), entry["local_path"]
            if entry["in_frozen_64"] and abs(rho) > max_rho_frozen64:
                max_rho_frozen64, max_rho_frozen64_path = float(abs(rho)), entry["local_path"]
        surface_checks.append(row)

    surface_pass = bool(max_rho <= 0.90)
    dump(
        OUT / "surface-checks.json",
        {
            "max_abs_rho_all_211": float(max_rho),
            "closest_all_211": max_rho_path,
            "max_abs_rho_frozen_64": float(max_rho_frozen64),
            "closest_frozen_64": max_rho_frozen64_path,
            "pass": surface_pass,
            "threshold": 0.90,
            "references_checked": len(surface_checks),
            "checks": surface_checks,
        },
    )
    log(f"Surface check: max |rho| = {max_rho:.4f} ({max_rho_path}), pass={surface_pass}")
    if not surface_pass:
        raise RuntimeError(f"Surface duplicate stop: |rho|={max_rho:.4f} > 0.90")

    log(f"Packing 3-px halos for {freg['competitive_sparse_le_90k_count']} competitive sparse references")
    halo_words, comp_entries = _pack_competitive_halos(entries, g.footprint)
    log(f"Emitting {BUDGET} dots via 300 m submodular CELF (uniqueness_cap={UNIQUENESS_CAP})")
    final_dots = emit_dots_celf_submodular(
        surf_oof,
        g.catalogue,
        g.footprint,
        budget=BUDGET,
        collar_px=COLLAR_PX,
        min_spacing_px=SPACING_PX,
        ref_halo_words=halo_words,
        n_refs=len(comp_entries),
        uniqueness_cap=UNIQUENESS_CAP,
    )
    del halo_words
    gc.collect()

    n_final = int((final_dots > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"Emitted {n_final} dots != expected budget {BUDGET}")

    log(f"Running Rule-1 Phase-2 3-px dot overlap checks across all {len(entries)} references")
    dot_checks = []
    max_ov_all, max_ov_all_path = 0.0, None
    max_ov_f64, max_ov_f64_path = 0.0, None
    for entry in entries:
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            ref_a = np.where(g.footprint, ds.read(1), 0.0).astype(np.float32)
        res = dot_check(final_dots, ref_a, g.footprint)
        del ref_a
        ov = float(res["overlap_within_3px"]) if res.get("overlap_within_3px") is not None else None
        is_dense = bool(
            entry["positive_pixels_inside_footprint"] > 90_000
            or "lattice" in Path(entry["local_path"]).name.lower()
        )
        row = {
            "path": entry["local_path"],
            "sha256": entry["sha256"],
            "groups": entry["groups"],
            "in_frozen_64": entry["in_frozen_64"],
            "focus_site": entry["focus_site"],
            "reference_positive_pixels": entry["positive_pixels_inside_footprint"],
            "is_dense_blanket": is_dense,
            "status": res["status"],
            "overlap_within_3px": ov,
            "exact_support_equal": bool(res.get("exact_support_equal", False)),
        }
        dot_checks.append(row)
        if ov is not None:
            if ov > max_ov_all:
                max_ov_all, max_ov_all_path = ov, entry["local_path"]
            if entry["in_frozen_64"] and ov > max_ov_f64:
                max_ov_f64, max_ov_f64_path = ov, entry["local_path"]

    nine_rows = [r for r in dot_checks if r["focus_site"] is not None]
    comp_rows = [r for r in dot_checks if r["overlap_within_3px"] is not None and not r["is_dense_blanket"]]
    dense_rows = [r for r in dot_checks if r["is_dense_blanket"]]
    gems92_rows = [r for r in dot_checks if "gemsdoe92_leader" in r["groups"]]

    nine_max = max(r["overlap_within_3px"] for r in nine_rows)
    comp_best_row = max(comp_rows, key=lambda r: r["overlap_within_3px"])
    comp_max = float(comp_best_row["overlap_within_3px"])
    gems92_ov = float(gems92_rows[0]["overlap_within_3px"]) if gems92_rows else None

    dump(
        OUT / "final-dot-checks.json",
        {
            "max_3px_overlap_all_211": float(max_ov_all),
            "closest_all_211": max_ov_all_path,
            "max_3px_overlap_frozen_64": float(max_ov_f64),
            "closest_frozen_64": max_ov_f64_path,
            "max_3px_overlap_nine_leaders": float(nine_max),
            "gemsdoe92_lbmc1_3px_overlap": gems92_ov,
            "max_3px_overlap_competitive_le_90000px": comp_max,
            "closest_competitive_le_90000px": comp_best_row["path"],
            "competitive_references_checked": len(comp_rows),
            "nine_leader_checks": nine_rows,
            "gemsdoe92_checks": gems92_rows,
            "dense_blanket_checks": dense_rows,
            "references_checked": len(dot_checks),
            "checks": dot_checks,
        },
    )
    log(
        f"Dot checks: nine_leaders_max={nine_max:.4f} | gemsdoe92_lbmc1={gems92_ov:.4f} | "
        f"competitive_181_max={comp_max:.4f} ({comp_best_row['path']}) | all_max={max_ov_all:.4f} ({max_ov_all_path})"
    )

    lat_path = ROOT / "data/fleet_registry/calib_r13lattice_00904.tif"
    with rasterio.open(lat_path) as ds:
        la = ds.read(1)
        lat = np.isfinite(la) & (la > 0) & g.footprint
    capacity = capacity_bound(g.footprint, lat, BUDGET)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final_dots > 0)[:8]
    tif_name = f"gems91-s27-cvdc-{best_exp}-{BUDGET}dots-{stamp}-{short}-zeros.tif"
    out_tif = ROOT / "docs/downloads" / tif_name
    receipt = write_submission(
        out_tif,
        final_dots.astype(np.float32),
        ROOT / "data/official/sample_submission.tif",
        g.footprint,
        note=NOTE,
        name=tif_name[:-4],
        catalogue=g.catalogue,
    )
    local_val = validate(out_tif, g.footprint, g.catalogue)
    assert_submittable(local_val)
    for p_dl in (out_tif, out_tif.with_suffix(".zip"), out_tif.with_suffix(".json")):
        if p_dl.is_file():
            p_dl.chmod(0o644)

    with rasterio.open(out_tif) as ds:
        disk = ds.read(1)
        reread = {
            "crs": str(ds.crs),
            "shape": [ds.height, ds.width],
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "transform": list(ds.transform)[:6],
            "nodata": ds.nodata,
            "nodata_is_none": ds.nodata is None,
            "all_finite": bool(np.isfinite(disk).all()),
            "min": float(disk.min()),
            "max": float(disk.max()),
            "n_dots": int((disk > 0).sum()),
            "on_catalogue": int((disk[g.catalogue] > 0).sum()),
            "outside_footprint_positive": int((disk[~g.footprint] > 0).sum()),
        }
    if not np.array_equal(disk > 0, final_dots > 0):
        raise RuntimeError("On-disk GeoTIFF support differs from in-memory final_dots")

    tif_sha = sha(out_tif)
    zip_path = out_tif.with_suffix(".zip")
    writer_receipt = {
        "file": str(out_tif.relative_to(ROOT)),
        "sha256": tif_sha,
        "bytes": out_tif.stat().st_size,
        "zip": str(zip_path.relative_to(ROOT)),
        "zip_sha256": sha(zip_path),
        "support_dot_digest": dot_digest(final_dots > 0),
        "emission_surface": f"stitched 4-fold v3-buffered OOF surface ({best_exp}); zero in-sample catalogue training",
        "writer_receipt": receipt,
        "independent_validator": local_val,
        "independent_reread": reread,
    }
    dump(OUT / "writer-receipt.json", writer_receipt)

    scores = best_holdout["scores"]
    cand_score = scores[best_arm]
    paired_vs_inc = best_holdout["paired_differences"]["incumbent_s25_fabric_e2"]
    paired_vs_base = best_holdout["paired_differences"]["control_oof_base"]
    beats_incumbent_ci = bool(paired_vs_inc["ci95"][0] > 0.0)
    beats_incumbent_point = bool(paired_vs_inc["delta"] > 0.0)
    beats_base_ci = bool(paired_vs_base["ci95"][0] > 0.0)

    dots_pass_all = bool(max_ov_all <= 0.70)
    dots_pass_comp = bool(comp_max <= 0.70)
    dots_pass_nine = bool(nine_max <= 0.70)
    validator_pass = bool(
        local_val["all_checks_passed"]
        and reread["all_finite"]
        and reread["on_catalogue"] == 0
        and reread["outside_footprint_positive"] == 0
    )

    stop_reasons = []
    if not dots_pass_all:
        stop_reasons.append(
            f"Literal all-reference 3-px overlap is {max_ov_all:.4f} against synthetic 5-px calibration lattice "
            f"{max_ov_all_path} (mathematically unavoidable floor >= {capacity['overlap_lower_bound']:.4f} "
            f"at {BUDGET} dots because only {capacity['uncovered_pixels']} footprint cells lie >3 px from that lattice); "
            f"competitive <=90k overlap across all {len(comp_rows)} rasters is {comp_max:.4f} <= 0.70."
        )
    if not beats_incumbent_ci:
        stop_reasons.append(
            f"Paired 95% CI vs incumbent S25-FABRIC E2 ({scores['incumbent_s25_fabric_e2']['dti']:.6f}) is "
            f"[{paired_vs_inc['ci95'][0]:+.6f}, {paired_vs_inc['ci95'][1]:+.6f}]."
        )
    stop_reasons.append(
        "Lane is self-assigned (registry/experiment_plan.json has lane=null) and Protocol Rule 6 reserves "
        "weekly submission slot approval to a separate selector step."
    )

    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "S27-CVDC (self-assigned; Rule-of-V contour-potential discordance + OSDR + MVSD + OOF CELF)",
        "assigned_lane": False,
        "preregistration": {"path": "docs/s27-osdr/preregistration.md", "sha256": sha(PREREG_PATH)},
        "selected_experiment": best_exp,
        "selected_arm": best_arm,
        "experiments_run": len(EXPERIMENTS),
        "budget_cap_experiments": 3,
        "weekly_submission_slots_used": 0,
        "raster_file": str(out_tif.relative_to(ROOT)),
        "raster_sha256": tif_sha,
        "raster_bytes": out_tif.stat().st_size,
        "zip_file": str(zip_path.relative_to(ROOT)),
        "zip_sha256": sha(zip_path),
        "support_dot_digest": writer_receipt["support_dot_digest"],
        "submission_note": NOTE,
        "submission_note_length": len(NOTE),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "split_version": best_holdout["fold_receipts"][0]["split_version"],
            "dti": float(cand_score["dti"]),
            "ci95": [float(cand_score["ci95"][0]), float(cand_score["ci95"][1])],
            "n_withheld_positives": int(cand_score["withheld_positive_pixels"]),
            "emitted_positive_pixels": BUDGET,
            "tpw": float(cand_score["tpw"]),
            "fpw": float(cand_score["fpw"]),
            "fnw": float(cand_score["fnw"]),
            "paired_vs_incumbent_s25_fabric_e2": paired_vs_inc,
            "paired_vs_control_oof_base": paired_vs_base,
            "all_experiments": {
                e: {
                    "arm": s["arm"],
                    "dti": s["dti"],
                    "ci95": s["ci95"],
                    "delta_vs_incumbent_s25_fabric_e2": s["holdout"]["paired_differences"][
                        "incumbent_s25_fabric_e2"
                    ],
                    "delta_vs_control_oof_base": s["holdout"]["paired_differences"]["control_oof_base"],
                }
                for e, s in exp_summaries.items()
            },
            "controls": {
                c: {
                    "dti": float(scores[c]["dti"]),
                    "ci95": [float(scores[c]["ci95"][0]), float(scores[c]["ci95"][1])],
                }
                for c in CONTROLS
            },
        },
        "organizer_confirmed": {
            "label": "ORGANIZER-CONFIRMED",
            "score": None,
            "status": "NOT SUBMITTED (0 weekly slots used)",
        },
        "leakage_canary": {
            "max_symmetric_auc": float(can["max_symmetric_auc"]),
            "worst": can["worst"],
            "threshold": 0.90,
            "pass": bool(can["all_pass"]),
        },
        "uniqueness": {
            "complete_organizer_registry": False,
            "references_checked": len(entries),
            "competitive_sparse_references_checked": len(comp_rows),
            "surface_max_abs_rho_all_211": float(max_rho),
            "surface_closest_all_211": max_rho_path,
            "surface_max_abs_rho_frozen_64": float(max_rho_frozen64),
            "surface_pass": surface_pass,
            "dot_3px_max_nine_focus_leaders": float(nine_max),
            "dot_3px_pass_nine_focus_leaders": dots_pass_nine,
            "dot_3px_gemsdoe92_lbmc1": gems92_ov,
            "dot_3px_max_competitive_le_90000px": comp_max,
            "dot_3px_closest_competitive_le_90000px": comp_best_row["path"],
            "dot_3px_pass_competitive_le_90000px": dots_pass_comp,
            "dot_3px_max_frozen_64_all": float(max_ov_f64),
            "dot_3px_closest_frozen_64_all": max_ov_f64_path,
            "dot_3px_pass_all_literal_no_exemption": dots_pass_all,
            "lattice_capacity_proof": capacity,
        },
        "format_validation": {
            "validator_pass": validator_pass,
            "crs": reread["crs"],
            "shape": reread["shape"],
            "dtype": reread["dtype"],
            "nodata": reread["nodata"],
            "min": reread["min"],
            "max": reread["max"],
            "all_finite": reread["all_finite"],
            "n_dots": reread["n_dots"],
            "on_catalogue": reread["on_catalogue"],
            "outside_footprint_positive": reread["outside_footprint_positive"],
        },
        "gates": {
            "canary_pass": bool(can["all_pass"]),
            "surface_pass": surface_pass,
            "dots_pass_nine_focus_leaders": dots_pass_nine,
            "dots_pass_competitive_181": dots_pass_comp,
            "dots_pass_all_literal_with_lattice": dots_pass_all,
            "beats_control_oof_base_95ci": beats_base_ci,
            "beats_incumbent_s25_point": beats_incumbent_point,
            "beats_incumbent_s25_95ci": beats_incumbent_ci,
            "validator_pass": validator_pass,
            "assigned_lane": False,
        },
        "ok_to_download": bool(validator_pass),
        "ok_to_submit": False,
        "verdict": "negative",
        "stop_reasons": stop_reasons,
        "elapsed_seconds": float(time.monotonic() - t0),
    }
    dump(OUT / "run-card.json", run_card)
    dump(ROOT / "docs/run-card-S27-OSDR.json", run_card)
    log(f"Packaged {out_tif.name} (sha256={tif_sha[:16]}...); ok_to_download={run_card['ok_to_download']}, ok_to_submit=False")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    sub.add_parser("controls")
    p_exp = sub.add_parser("experiment")
    p_exp.add_argument("--exp", required=True, choices=["e1", "e2", "e3"])
    sub.add_parser("package")
    args = ap.parse_args()
    if args.cmd == "prep":
        return cmd_prep(args)
    if args.cmd == "controls":
        return cmd_controls(args)
    if args.cmd == "experiment":
        return cmd_experiment(args)
    if args.cmd == "package":
        return cmd_package(args)
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
