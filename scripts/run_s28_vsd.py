#!/usr/bin/env python3
"""S28-VSD lane runner (preregistered in docs/s28-vsd/preregistration.md).

Assigned method paragraph (session prompt 2026-10-31, PARALLEL-RUN PROTOCOL §2):
reuse the template's cached feature stack, evaluate_holdout.py and
submission_writer.py; holdout = hide-and-recover with whole-segment withholding
and buffer; catalogue-based features only from visible faults (satisfied in the
strongest form: zero catalogue dependence); score pooled DTI (alpha 0.2,
beta 0.8, 300 m triangular kernel).

Subcommands:
  prep        Verify pinned inputs + preregistration + frozen 211-reference
              registry; extract the template's 38 static features AND the new
              15 VSD features into float32 memmaps; run Rule-4 single-feature
              leakage canaries (symmetric AUC <= 0.90) plus the preregistered
              CDEC orientation-shuffle negative control.
  controls    Compute & cache matched v3-buffered holdout terms for:
                - incumbent_s25_fabric_e2  (reigning matched incumbent)
                - control_oof_base         (23-feature base control)
                - control_s27static38_hgb  (template 38 statics, same trainer)
                - control_cdec_surface, control_tsr_gap6_strength,
                  control_sta_coupling (raw static-family surfaces)
  experiment  --exp e1|e2|e3 : the 3 preregistered experiments.
  package     Select best experiment by primary pooled HOLDOUT-DTI; Rule-1
              surface check vs all 211 references; CELF 37,654 dots with
              uniqueness_cap=0.64 vs the 181 competitive sparse references;
              Rule-1 dot checks; shared writer + independent validator;
              machine-readable run card.

Strictly enforces the Parallel-Run Protocol (Rules 1-6): max 3 experiments,
<= 2 hours wall-clock budget guard, zero weekly submission slots, fail-closed
gates.  If the surface or dots duplicate any registry witness (|rho| > 0.90 or
> 70% within 3 px vs a non-dense reference), the lane STOPS with a negative
verdict.
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

import run_s27_osdr as R27  # template runner: reused helpers, same protocol constants

from gems91 import fabric25  # noqa: F401  (imported for R27._ensure_s25_features side import path)
from gems91.cvdc_osdr27 import (
    ALL_STATIC_NAMES,
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
)
from gems91.vsd28 import VSD_NAMES, compute_vsd28_features
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s28-vsd"
WORK = ROOT / "data/work/s28_cache"
PREREG_PATH = OUT / "preregistration.md"
FROZEN_REG_PATH = ROOT / "docs/s27-osdr/frozen-registry.json"

BUDGET = 37_654
COLLAR_PX = 3.05
SPACING_PX = 3.05
UNIQUENESS_CAP = 0.64
SEED = 910281
MAX_WALL_MINUTES = 120.0
T0_WALL = time.monotonic()
# Lane-persistent wall clock (Protocol Rule 6): every subcommand shares one anchor.
# 2026-10-31T00:53:00Z is when the first S28 prep process started in this session.
LANE_T0_EPOCH = 1793407980.0  # 2026-10-31T00:53:00Z — first S28 prep process start
try:
    LANE_T0_EPOCH = float((WORK / ".lane_t0").read_text().strip())
except FileNotFoundError:
    pass


def _ensure_lane_t0() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    p = WORK / ".lane_t0"
    if not p.exists():
        p.write_text(f"{LANE_T0_EPOCH:.3f}\n")


def lane_minutes_used() -> float:
    try:
        return (time.time() - float((WORK / ".lane_t0").read_text().strip())) / 60.0
    except FileNotFoundError:
        return (time.time() - LANE_T0_EPOCH) / 60.0


N_STATIC = len(ALL_STATIC_NAMES)
N_VSD = len(VSD_NAMES)
N_WIDE = N_STATIC + N_VSD

S25_HGB_PARAMS = dict(R27.S25_HGB_PARAMS)
S25_NEG_PER_POS = R27.S25_NEG_PER_POS

CONTROLS = [
    "incumbent_s25_fabric_e2",
    "control_oof_base",
    "control_s27static38_hgb",
    "control_cdec_surface",
    "control_tsr_gap6_strength",
    "control_sta_coupling",
]

EXPERIMENTS = {
    "e1": "s28_e1_stack53_hgb",
    "e2": "s28_e2_stage2_ac_stack53",
    "e3": "s28_e3_celf_emission",
}

NOTE = "S28 VSD cross-domain edge concordance+relay gaps+seismic alignment; widened-stack OOF CELF 37654d; run-card verdict"
assert len(NOTE) <= 140, len(NOTE)

# Static-column indices (within the 38-col template stack) used as hard negatives,
# mirroring the template's choices (verified by name lookup, never by position guess).
HARD_STATIC_38 = [
    ALL_STATIC_NAMES.index("sub_grad_grav_b13"),
    ALL_STATIC_NAMES.index("raw_B19_det_slope"),
]
HARD_STAGE2_EXTRA = [N_WIDE + 0]  # ac_prob_s1 appended after the 53 static columns


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
    el = (time.monotonic() - T0_WALL) / 60.0
    print(f"[+{el:05.1f}min] {msg}", flush=True)


class BudgetExhausted(RuntimeError):
    pass


def wall_guard(stage: str, reserve_minutes: float = 0.0) -> None:
    used = lane_minutes_used()
    if used + reserve_minutes > MAX_WALL_MINUTES:
        raise BudgetExhausted(
            f"Wall-clock budget exhausted at stage '{stage}': {used:.1f} lane-minutes used, "
            f"{reserve_minutes:.1f} min reserve needed, cap {MAX_WALL_MINUTES:.0f} min (Protocol Rule 6)."
        )


def verify_pinned_inputs() -> dict:
    if not PREREG_PATH.is_file():
        raise ValueError("docs/s28-vsd/preregistration.md missing")
    if not FROZEN_REG_PATH.is_file():
        raise ValueError("docs/s27-osdr/frozen-registry.json missing (frozen witness registry)")
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        if row["id"] in {"sample_submission", "existing_faults", "training_features",
                         "parent_r0_zeros", "sgmc_faults_control"}:
            p = ROOT / "data" / row["local_subpath"]
            if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
                raise ValueError(f"Pinned input absent or drifted: {row['id']}")
            checked[row["id"]] = {"path": "data/" + row["local_subpath"], "sha256": row["sha256"]}
    for e in json.loads(FROZEN_REG_PATH.read_text())["entries"]:
        p = ROOT / e["local_path"]
        if not p.is_file() or p.stat().st_size != e["bytes"]:
            raise ValueError(f"Frozen registry reference absent or wrong size: {e['local_path']}")
    return checked


def open_static_memmap(n_fp: int, mode: str = "r") -> np.memmap:
    return np.memmap(WORK / "cvdc27_static38.f32.mmap", dtype="float32", mode=mode,
                     shape=(n_fp, N_STATIC))


def open_vsd_memmap(n_fp: int, mode: str = "r") -> np.memmap:
    return np.memmap(WORK / "vsd28_15.f32.mmap", dtype="float32", mode=mode,
                     shape=(n_fp, N_VSD))


def _auc_or_none(pos: np.ndarray, neg: np.ndarray) -> float | None:
    if pos.size == 0 or neg.size == 0:
        return None
    y = np.concatenate([np.ones(pos.size), np.zeros(neg.size)])
    s = np.concatenate([pos, neg])
    return float(roc_auc_score(y, s))


# --------------------------------------------------------------------- prep
def cmd_prep(_args) -> int:
    t0 = time.monotonic()
    _ensure_lane_t0()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)

    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    n_fp = int(g.footprint.sum())

    log("Ensuring raw 19-band float32 memmap cache")
    raw19 = ensure_raw19_memmap(
        ROOT / "data/bridge/gems-geodawn-numerical-features.tif", WORK / "raw19.f32.mmap"
    )

    static_path = WORK / "cvdc27_static38.f32.mmap"
    vsd_path = WORK / "vsd28_15.f32.mmap"
    ctrl_cvdc_path = WORK / "control_cvdc_surface.npy"
    ctrl_grav_path = WORK / "control_gravgrad.npy"
    ctrl_cdec_path = WORK / "control_cdec_surface.npy"
    ctrl_shuf_path = WORK / "control_cdec_orient_shuffled.npy"
    ctrl_gap_path = WORK / "control_tsr_gap6_strength.npy"
    ctrl_sta_path = WORK / "control_sta_coupling.npy"
    need_build = not (
        static_path.is_file()
        and static_path.stat().st_size == n_fp * N_STATIC * 4
        and vsd_path.is_file()
        and vsd_path.stat().st_size == n_fp * N_VSD * 4
        and all(p.is_file() for p in (ctrl_cvdc_path, ctrl_grav_path, ctrl_cdec_path,
                                      ctrl_shuf_path, ctrl_gap_path, ctrl_sta_path))
        and (OUT / "feature-receipt.json").is_file()
    )

    if need_build:
        wall_guard("prep:feature-extraction", reserve_minutes=40)
        log(f"Computing {N_STATIC} template static features into float32 memmap")
        X_mm = open_static_memmap(n_fp, "w+")
        _, surfs27, _ = R27_or_none_compute(raw19, g.footprint, X_mm)
        np.save(ctrl_cvdc_path, surfs27["control_cvdc_surface"])
        np.save(ctrl_grav_path, surfs27["control_gravgrad"])
        del X_mm, surfs27
        gc.collect()

        wall_guard("prep:vsd-extraction", reserve_minutes=20)
        log(f"Computing {N_VSD} S28-VSD features into float32 memmap")
        V_mm = open_vsd_memmap(n_fp, "w+")
        _, surfs_v, receipt_v = compute_vsd28_features(raw19, g.footprint, out_fp_matrix=V_mm)
        np.save(ctrl_cdec_path, surfs_v["control_cdec_surface"])
        np.save(ctrl_shuf_path, surfs_v["control_cdec_orient_shuffled"])
        np.save(ctrl_gap_path, surfs_v["control_tsr_gap6_strength"])
        np.save(ctrl_sta_path, surfs_v["control_sta_coupling"])
        del V_mm, surfs_v
        gc.collect()
    else:
        log("Feature memmaps already cached on disk")
        receipt_v = {}

    X_static = open_static_memmap(n_fp, "r")
    X_vsd = open_vsd_memmap(n_fp, "r")

    receipt = {
        "module_static": "gems91.cvdc_osdr27.compute_cvdc27_features (template cached stack)",
        "module_vsd": receipt_v or "cached",
        "inputs_verified": inputs,
        "preregistration": {"path": "docs/s28-vsd/preregistration.md", "sha256": sha(PREREG_PATH)},
        "frozen_registry": {"path": "docs/s27-osdr/frozen-registry.json", "sha256": sha(FROZEN_REG_PATH),
                            "n_references": len(json.loads(FROZEN_REG_PATH.read_text())["entries"])},
        "wall_minutes_at_prep_end": round(lane_minutes_used(), 2),
    }

    # ---------------- Rule-4 leakage canaries (all features, fold-wise + pooled)
    log("Running Rule-4 single-feature holdout leakage canaries (38 static + 15 VSD + 6 surfaces)")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fp_idx_grid = np.full(g.shape, -1, dtype=np.int32)
    fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int32)

    canaries = []
    max_sym = 0.0
    worst = None

    def check_feature(name: str, vec_fp: np.ndarray) -> None:
        nonlocal max_sym, worst
        pool_pos, pool_neg = [], []
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pos_rows = fp_idx_grid[fold["truth"] & valid]
            neg_rows = fp_idx_grid[(~fold["truth"]) & valid][::4]
            pv = np.asarray(vec_fp[pos_rows], dtype=np.float64)
            nv = np.asarray(vec_fp[neg_rows], dtype=np.float64)
            pool_pos.append(pv)
            pool_neg.append(nv)
            auc = _auc_or_none(pv, nv)
            if auc is None:
                continue
            sym = max(auc, 1.0 - auc)
            if sym > max_sym:
                max_sym, worst = sym, f"{name} fold{fidx}"
            canaries.append({"feature": name, "scope": f"fold{fidx}", "n_positive": int(pv.size),
                             "n_negative": int(nv.size), "auc": auc, "symmetric_auc": sym})
        pp, pn = np.concatenate(pool_pos), np.concatenate(pool_neg)
        auc_p = _auc_or_none(pp, pn)
        if auc_p is None:
            return
        sym_p = max(auc_p, 1.0 - auc_p)
        if sym_p > max_sym:
            max_sym, worst = sym_p, f"{name} pooled"
        canaries.append({"feature": name, "scope": "pooled", "n_positive": int(pp.size),
                         "n_negative": int(pn.size), "auc": auc_p, "symmetric_auc": sym_p})

    for col_j, name in enumerate(ALL_STATIC_NAMES):
        check_feature(name, X_static[:, col_j])
    for col_j, name in enumerate(VSD_NAMES):
        check_feature(name, X_vsd[:, col_j])

    for sname, fpath in [
        ("control_cvdc_surface", ctrl_cvdc_path),
        ("control_gravgrad", ctrl_grav_path),
        ("control_cdec_surface", ctrl_cdec_path),
        ("control_cdec_orient_shuffled", ctrl_shuf_path),
        ("control_tsr_gap6_strength", ctrl_gap_path),
        ("control_sta_coupling", ctrl_sta_path),
    ]:
        arr2d = np.load(fpath)
        check_feature(sname, arr2d[g.footprint])
        del arr2d

    # preregistered negative control: orientation-shuffled concordance must be
    # weaker than the true concordance (feature-alone pooled AUC).
    auc_cdec = next(c["auc"] for c in canaries if c["feature"] == "control_cdec_surface" and c["scope"] == "pooled")
    auc_shuf = next(c["auc"] for c in canaries if c["feature"] == "control_cdec_orient_shuffled" and c["scope"] == "pooled")
    negctrl = {
        "cdec_pooled_auc": auc_cdec,
        "cdec_orientation_shuffled_pooled_auc": auc_shuf,
        "shuffled_weaker": bool(max(auc_cdec, 1 - auc_cdec) >= max(auc_shuf, 1 - auc_shuf)),
    }
    receipt["negative_control_cdec"] = negctrl

    canary_pass = bool(max_sym <= 0.90)
    dump(OUT / "canaries.json", {
        "max_symmetric_auc": float(max_sym), "worst": worst, "all_pass": canary_pass,
        "threshold": 0.90, "evaluator_version": EH.VERSION,
        "split_version": folds[0]["receipt"]["split_version"],
        "n_checks": len(canaries), "elapsed_seconds": float(time.monotonic() - t0),
        "negative_control_cdec": negctrl, "canaries": canaries,
    })
    dump(OUT / "feature-receipt.json", receipt)
    log(f"Canaries complete: max symmetric AUC = {max_sym:.4f} ({worst}), pass={canary_pass}; "
        f"CDEC neg-ctrl weaker={negctrl['shuffled_weaker']}")
    return 0 if (canary_pass and negctrl["shuffled_weaker"]) else 2


def R27_or_none_compute(raw19, footprint, out_mm):
    """Delegate to the template's static-feature computation."""
    from gems91.cvdc_osdr27 import compute_cvdc27_features
    return compute_cvdc27_features(raw19, footprint, out_fp_matrix=out_mm)


# ----------------------------------------------------------------- controls
def _hgb_oof_surface_from_memmap(X: np.memmap, feat_cols: list[int], g, folds) -> np.ndarray:
    """S25-HGB trainer (matched to R27._s25_oof_surface) but reading a memmap.

    `X` rows are footprint-relative; grid flat indices are mapped through
    `fp_idx_grid` (non-footprint cells predict 0 and are masked at the end,
    exactly like R27's full-grid version).
    """
    out = np.zeros(g.shape, dtype=np.float64)
    flat_cat = g.catalogue.ravel()
    flat_fp = g.footprint.ravel()
    n_fp = int(g.footprint.sum())
    fp_idx_grid = np.full(g.shape, -1, dtype=np.int32)
    fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int32)

    def _gather_grid(flat_idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rows = fp_idx_grid.ravel()[flat_idx]
        ok = rows >= 0
        Xs = np.zeros((len(flat_idx), len(feat_cols)), dtype=np.float32)
        if ok.any():
            r = rows[ok]
            for j, c in enumerate(feat_cols):
                Xs[ok, j] = np.asarray(X[r, c])
        return Xs, ok, rows

    for fidx, fold in enumerate(folds):
        flat_train = fold["train"].ravel() & flat_fp
        pos = np.flatnonzero(flat_train & flat_cat)
        pool = np.flatnonzero(flat_train & ~flat_cat)
        rng = np.random.default_rng(SEED)
        neg = rng.choice(pool, size=min(S25_NEG_PER_POS * len(pos), len(pool)), replace=False)
        idx = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
        from sklearn.ensemble import HistGradientBoostingClassifier
        model = HistGradientBoostingClassifier(random_state=SEED, **S25_HGB_PARAMS)
        X_fit, _, _ = _gather_grid(idx)
        model.fit(X_fit, y)
        del X_fit
        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        p_idx = np.flatnonzero(fold["region"].ravel() & flat_fp)
        for lo in range(0, len(p_idx), 250_000):
            ch = p_idx[lo: lo + 250_000]
            Xs, ok, _ = _gather_grid(ch)
            acc[ch[ok]] = model.predict_proba(Xs[ok])[:, 1]
            del Xs
        out += acc.reshape(g.shape)
        del model, acc
        gc.collect()
        log(f"  HGB({len(feat_cols)} feats) fold {fidx} done")
    return np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)


def cmd_controls(_args) -> int:
    t0 = time.monotonic()
    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = R27.allocate(BUDGET, areas)

    terms_file = WORK / "holdout-terms.npz"
    pf_file = WORK / "per-fold-controls.json"
    terms_by_arm, per_fold_all = {}, []
    if terms_file.is_file() and pf_file.is_file():
        with np.load(terms_file) as z:
            terms_by_arm = {k: z[k] for k in z.files}
        per_fold_all = json.loads(pf_file.read_text())

    raw19 = ensure_raw19_memmap(
        ROOT / "data/bridge/gems-geodawn-numerical-features.tif", WORK / "raw19.f32.mmap"
    )

    if "incumbent_s25_fabric_e2" not in terms_by_arm or "control_oof_base" not in terms_by_arm:
        wall_guard("controls:s25", reserve_minutes=30)
        R27.WORK = WORK  # cache S25 repro features inside this lane's work dir
        s25_groups = R27._ensure_s25_features(raw19, g)
        if "control_oof_base" not in terms_by_arm:
            log("Scoring matched control: control_oof_base")
            surf_base = R27._s25_oof_surface(list(s25_groups["base"]), g, folds)
            np.save(WORK / "surf_control_oof_base.npy", surf_base)
            t_b, pf_b = R27._score_arm_on_folds("control_oof_base", surf_base, g, folds, budgets, emitter="nms")
            terms_by_arm["control_oof_base"] = t_b
            per_fold_all.extend(pf_b)
            del surf_base
        if "incumbent_s25_fabric_e2" not in terms_by_arm:
            log("Scoring matched incumbent: incumbent_s25_fabric_e2")
            surf_inc = R27._s25_oof_surface(list(s25_groups["base"]) + list(s25_groups["new"]), g, folds)
            np.save(WORK / "surf_incumbent_s25_fabric_e2.npy", surf_inc)
            t_i, pf_i = R27._score_arm_on_folds("incumbent_s25_fabric_e2", surf_inc, g, folds, budgets, emitter="nms")
            terms_by_arm["incumbent_s25_fabric_e2"] = t_i
            per_fold_all.extend(pf_i)
            del surf_inc
        gc.collect()

    n_fp = int(g.footprint.sum())
    if "control_s27static38_hgb" not in terms_by_arm:
        wall_guard("controls:static38", reserve_minutes=30)
        log("Scoring matched control: control_s27static38_hgb (template 38 statics, same trainer)")
        X_static = open_static_memmap(n_fp, "r")
        surf_s38 = _hgb_oof_surface_from_memmap(X_static, list(range(N_STATIC)), g, folds)
        np.save(WORK / "surf_control_s27static38_hgb.npy", surf_s38)
        t_s, pf_s = R27._score_arm_on_folds("control_s27static38_hgb", surf_s38, g, folds, budgets, emitter="nms")
        terms_by_arm["control_s27static38_hgb"] = t_s
        per_fold_all.extend(pf_s)
        del X_static, surf_s38
        gc.collect()

    for cname, fname in [
        ("control_cvdc_surface", "control_cvdc_surface.npy"),
        ("control_gravgrad", "control_gravgrad.npy"),
        ("control_cdec_surface", "control_cdec_surface.npy"),
        ("control_tsr_gap6_strength", "control_tsr_gap6_strength.npy"),
        ("control_sta_coupling", "control_sta_coupling.npy"),
    ]:
        if cname in terms_by_arm or not (WORK / fname).is_file():
            continue
        log(f"Scoring static control: {cname}")
        s = np.load(WORK / fname)
        t_c, pf_c = R27._score_arm_on_folds(cname, s, g, folds, budgets, emitter="nms")
        terms_by_arm[cname] = t_c
        per_fold_all.extend(pf_c)
        del s

    missing = [c for c in CONTROLS if c not in terms_by_arm]
    if missing:
        raise RuntimeError(f"Controls missing after controls stage: {missing}")

    np.savez_compressed(terms_file, **terms_by_arm)
    dump(pf_file, per_fold_all)
    for cname in CONTROLS:
        dti = float(EH.from_terms(terms_by_arm[cname].sum(axis=0)))
        log(f"Control {cname}: HOLDOUT-DTI = {dti:.6f}")
    log(f"Controls cached in {time.monotonic() - t0:.1f}s")
    return 0


# --------------------------------------------------------------- experiments
def _score_experiment(arm: str, surf: np.ndarray, emitter: str, g, folds, budgets, terms_by_arm, per_fold, outdir: Path, extra: dict) -> dict:
    t_cand, pf_cand = R27._score_arm_on_folds(arm, surf, g, folds, budgets, emitter=emitter)
    terms_by_arm[arm] = t_cand
    per_fold.extend(pf_cand)
    np.savez_compressed(WORK / "holdout-terms.npz", **terms_by_arm)
    dump(WORK / "per-fold-controls.json", per_fold)

    arms = [arm] + CONTROLS
    sub = {a: terms_by_arm[a] for a in arms}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=arm)
    pooled["per_fold"] = per_fold
    pooled["fold_receipts"] = [f["receipt"] for f in folds]
    pooled["matched_controls"] = CONTROLS
    pooled["budget_total"] = BUDGET
    pooled["emitter"] = emitter
    pooled["extra"] = extra
    pooled["wall_minutes"] = round(lane_minutes_used(), 2)
    dump(outdir / "holdout.json", pooled)

    s = pooled["scores"][arm]
    log(f"  {arm} [{emitter}]: HOLDOUT-DTI = {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in ("incumbent_s25_fabric_e2", "control_s27static38_hgb"):
        if c in pooled.get("paired_differences", {}):
            d = pooled["paired_differences"][c]
            log(f"  Delta vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return pooled


def _ensure_wide_nested_ac_cache(X_wide: np.memmap, g, folds) -> list[Path]:
    """Nested leave-one-quadrant-out stage-1 on the widened stack + AC8 features per fold."""
    n_fp = int(g.footprint.sum())
    expected_bytes = n_fp * 8 * 2
    ac_paths = [WORK / f"ac8_wide_fold{k}.f16.mmap" for k in range(4)]
    if all(p.is_file() and p.stat().st_size == expected_bytes for p in ac_paths):
        log("Nested widened-AC caches already present for all 4 folds")
        return ac_paths

    h, w = g.shape
    yy, xx = np.indices((h, w), sparse=True)
    quad = (yy >= h // 2).astype(np.int8) * 2 + (xx >= w // 2).astype(np.int8)
    quad_inner_safe = {q: ndi.distance_transform_edt(quad != q) > 80.0 for q in range(4)}

    wide_cols = list(range(N_WIDE))
    hard_cols = [HARD_STATIC_38[0], HARD_STATIC_38[1]]

    for k, fold in enumerate(folds):
        wall_guard(f"e2:nested-ac-fold{k}", reserve_minutes=25)
        if ac_paths[k].is_file() and ac_paths[k].stat().st_size == expected_bytes:
            continue
        other_quads = [q for q in range(4) if q != k]
        p_nested = np.zeros(g.shape, dtype=np.float32)
        non_train_fp = g.footprint & (~fold["train"])
        non_train_acc = np.zeros(g.shape, dtype=np.float64)
        for q_val in other_quads:
            log(f"  E2 nested fold {k} inner leave-out quadrant {q_val}: fitting widened specialist")
            val_mask = fold["train"] & (quad == q_val)
            in_train = fold["train"] & quad_inner_safe[q_val]
            in_vis = fold["visible"] & quad_inner_safe[q_val]
            pred_target = val_mask | non_train_fp
            p_in, _ = fit_predict_pdwc_specialist(
                blocks=[(X_wide, wide_cols)],
                hard_neg_cols_in_stack=hard_cols,
                visible_faults=in_vis,
                train_domain=in_train,
                footprint=g.footprint,
                seed=SEED + 313 * k + 29 * q_val,
                predict_mask=pred_target,
            )
            p_nested[val_mask] = p_in[val_mask]
            non_train_acc[non_train_fp] += p_in[non_train_fp] / float(len(other_quads))
            del p_in
            gc.collect()
        p_nested[non_train_fp] = non_train_acc[non_train_fp].astype(np.float32)
        del non_train_acc
        log(f"  E2 nested fold {k}: computing 8 directional auto-context features")
        ac_list = compute_directional_ac_8(p_nested, g.footprint)
        tmp_path = WORK / f"ac8_wide_fold{k}.tmp.mmap"
        mm_ac = np.memmap(tmp_path, dtype="float16", mode="w+", shape=(n_fp, 8))
        for j, arr2d in enumerate(ac_list):
            mm_ac[:, j] = np.clip(arr2d[g.footprint], -32.0, 32.0).astype(np.float16)
        mm_ac.flush()
        del ac_list, mm_ac, p_nested
        tmp_path.replace(ac_paths[k])
        gc.collect()
    return ac_paths


def _stage2_wide_oof(X_wide: np.memmap, ac_paths: list[Path], g, folds) -> np.ndarray:
    out_path = WORK / "s2_wide_outer_oof.npy"
    if out_path.is_file():
        log("Stage-2 (wide) outer OOF already cached")
        return np.load(out_path)
    n_fp = int(g.footprint.sum())
    wide_cols = list(range(N_WIDE))
    hard_cols = [HARD_STATIC_38[0], HARD_STATIC_38[1]] + HARD_STAGE2_EXTRA
    s2_oof = np.zeros(g.shape, dtype=np.float32)
    for k, fold in enumerate(folds):
        wall_guard(f"e2:stage2-fold{k}", reserve_minutes=25)
        log(f"  E2 stage-2 outer fold {k}: fitting widened PU specialist with nested AC features")
        mm_ac = np.memmap(ac_paths[k], dtype="float16", mode="r", shape=(n_fp, 8))
        p2, _ = fit_predict_pdwc_specialist(
            blocks=[(X_wide, wide_cols), (mm_ac, list(range(8)))],
            hard_neg_cols_in_stack=hard_cols,
            visible_faults=fold["visible"],
            train_domain=fold["train"],
            footprint=g.footprint,
            seed=SEED + 709 * k + 3,
            predict_mask=fold["region"],
        )
        s2_oof[fold["region"]] = p2[fold["region"]]
        del p2, mm_ac
        gc.collect()
    np.save(out_path, s2_oof)
    return s2_oof


def _e2_fallback_ac(g, folds) -> list[Path]:
    """Preregistered E2b fallback: fold-local AC features from the E1 OOF surface.

    Used only if the wall-clock guard trips (trigger recorded in the run card).
    The E1 surface is out-of-fold by construction, so within each fold's region
    the AC features never see that fold's labels; this is a weaker context probe
    than the nested specialist and is labelled as such everywhere.
    """
    surf = np.load(WORK / "e1_oof_surface.npy")
    n_fp = int(g.footprint.sum())
    ac_paths = []
    for k, fold in enumerate(folds):
        p = WORK / f"ac8_fallback_fold{k}.f16.mmap"
        if p.is_file() and p.stat().st_size == n_fp * 8 * 2:
            ac_paths.append(p)
            continue
        local = np.zeros(g.shape, dtype=np.float32)
        local[fold["region"]] = surf[fold["region"]]
        ac_list = compute_directional_ac_8(local, g.footprint)
        tmp = WORK / f"ac8_fallback_fold{k}.tmp.mmap"
        mm = np.memmap(tmp, dtype="float16", mode="w+", shape=(n_fp, 8))
        for j, arr2d in enumerate(ac_list):
            mm[:, j] = np.clip(arr2d[g.footprint], -32.0, 32.0).astype(np.float16)
        mm.flush()
        del ac_list, mm
        tmp.replace(p)
        ac_paths.append(p)
    return ac_paths


def cmd_experiment(args) -> int:
    exp = args.exp
    if exp not in EXPERIMENTS:
        raise ValueError(f"Unknown experiment {exp}; must be one of {list(EXPERIMENTS)}")
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").is_file():
        log(f"{exp} already recorded")
        return 0

    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("Rule-4 single-feature leakage canary failed; stopping lane")

    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    n_fp = int(g.footprint.sum())
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = R27.allocate(BUDGET, areas)

    terms_file = WORK / "holdout-terms.npz"
    pf_file = WORK / "per-fold-controls.json"
    if not terms_file.is_file() or not pf_file.is_file():
        raise RuntimeError("Run 'controls' subcommand before 'experiment'")
    with np.load(terms_file) as z:
        terms_by_arm = {k: z[k] for k in z.files}
    per_fold = list(json.loads(pf_file.read_text()))

    X_static = open_static_memmap(n_fp, "r")
    X_vsd = open_vsd_memmap(n_fp, "r")
    # Materialise the wide matrix once as a float32 memmap on disk (53 cols).
    wide_path = WORK / "wide53.f32.mmap"
    if not wide_path.is_file() or wide_path.stat().st_size != n_fp * N_WIDE * 4:
        wall_guard("e1:wide-matrix", reserve_minutes=15)
        log("Materialising widened 53-column memmap (38 template statics + 15 VSD)")
        mm = np.memmap(wide_path, dtype="float32", mode="w+", shape=(n_fp, N_WIDE))
        step = 500_000
        for lo in range(0, n_fp, step):
            hi = min(n_fp, lo + step)
            mm[lo:hi, :N_STATIC] = X_static[lo:hi, :]
            mm[lo:hi, N_STATIC:] = X_vsd[lo:hi, :]
        mm.flush()
        del mm
        gc.collect()
    X_wide = np.memmap(wide_path, dtype="float32", mode="r", shape=(n_fp, N_WIDE))

    if exp == "e1":
        wall_guard("e1", reserve_minutes=40)
        log("E1: widened-stack HGB (S25-matched trainer) -> stitched 4-fold OOF -> NMS")
        surf_oof = _hgb_oof_surface_from_memmap(X_wide, list(range(N_WIDE)), g, folds)
        np.save(WORK / "e1_oof_surface.npy", surf_oof)
        _score_experiment(EXPERIMENTS["e1"], surf_oof, "nms", g, folds, budgets, terms_by_arm, per_fold, outdir,
                          extra={"factor_under_test": "VSD families added to template statics (same trainer/emitter as controls)"})

    elif exp == "e2":
        wall_guard("e2", reserve_minutes=60)
        e2_mode = os.environ.get("S28_E2_MODE", "nested")
        if not (WORK / "e1_oof_surface.npy").is_file():
            raise RuntimeError("E1 must run before E2 (selection/fallback dependency)")
        e2_path_used = None
        if e2_mode == "nested":
            log("E2: nested widened stage-1 + AC8 + widened PU-specialist stage-2")
            try:
                ac_paths = _ensure_wide_nested_ac_cache(X_wide, g, folds)
                e2_path_used = "nested-specialist"
            except BudgetExhausted as be:
                log(f"E2 nested path hit the wall-clock guard ({be}); switching to the predeclared fallback")
                ac_paths = _e2_fallback_ac(g, folds)
                e2_path_used = "fallback-fold-local-ac8-hgb (nested path tripped Rule-6 guard)"
        else:
            log("E2 FALLBACK (predeclared): fold-local AC8 from E1 OOF surface + widened HGB stage-2")
            ac_paths = _e2_fallback_ac(g, folds)
            e2_path_used = "fallback-fold-local-ac8-hgb"
        # Rule-4 canary on the AC features themselves
        fp_idx_grid = np.full(g.shape, -1, dtype=np.int32)
        fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int32)
        ac_max_sym = 0.0
        for k, fold in enumerate(folds):
            mm_ac = np.memmap(ac_paths[k], dtype="float16", mode="r", shape=(n_fp, 8))
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pr = fp_idx_grid[fold["truth"] & valid]
            nr = fp_idx_grid[(~fold["truth"]) & valid][::4]
            for j in range(8):
                pv = np.asarray(mm_ac[pr, j], dtype=np.float64)
                nv = np.asarray(mm_ac[nr, j], dtype=np.float64)
                auc = _auc_or_none(pv, nv)
                if auc is not None:
                    ac_max_sym = max(ac_max_sym, auc, 1.0 - auc)
            del mm_ac
        log(f"E2 auto-context canary max symmetric AUC = {ac_max_sym:.4f}")
        if ac_max_sym > 0.90:
            raise RuntimeError(f"Auto-context canary exceeded 0.90: {ac_max_sym:.4f}")

        if e2_path_used == "nested-specialist":
            try:
                surf_oof = _stage2_wide_oof(X_wide, ac_paths, g, folds)
            except BudgetExhausted as be:
                log(f"E2 stage-2 hit the wall-clock guard ({be}); switching to the predeclared fallback")
                ac_paths = _e2_fallback_ac(g, folds)
                e2_path_used = "fallback-fold-local-ac8-hgb (stage-2 tripped Rule-6 guard)"
        if e2_path_used != "nested-specialist":
            out_path = WORK / "s2_fallback_oof.npy"
            if out_path.is_file():
                surf_oof = np.load(out_path)
            else:
                wide61 = _wide_plus_ac_view(X_wide, ac_paths, n_fp)
                surf_oof = _hgb_oof_surface_from_memmap(wide61, list(range(N_WIDE + 8)), g, folds)
                np.save(out_path, surf_oof)
        np.save(WORK / "e2_oof_surface.npy", surf_oof)
        _score_experiment(EXPERIMENTS["e2"], surf_oof, "nms", g, folds, budgets, terms_by_arm, per_fold, outdir,
                          extra={"factor_under_test": "stage-2 spatial auto-context on widened stack",
                                 "e2_path_used": e2_path_used})

    elif exp == "e3":
        wall_guard("e3", reserve_minutes=30)
        log("E3: emission-policy arm (per-fold submodular CELF vs NMS) on the winning surface")
        cands = []
        for e, arm in EXPERIMENTS.items():
            hp = OUT / e / "holdout.json"
            if hp.is_file():
                hh = json.loads(hp.read_text())
                cands.append((hh["scores"][arm]["dti"], e, arm))
        if not cands:
            raise RuntimeError("E3 requires at least one completed prior experiment")
        _, best_e, best_arm = max(cands)
        surf = np.load(WORK / f"{best_e}_oof_surface.npy")
        log(f"E3 winner surface = {best_e} ({best_arm}); scoring per-fold CELF emission")
        _score_experiment(EXPERIMENTS["e3"], surf, "celf", g, folds, budgets,
                          terms_by_arm, per_fold, outdir,
                          extra={"factor_under_test": "emission policy at fixed budget",
                                 "winner_surface": f"{best_e}:{best_arm}"})
        np.save(WORK / "e3_oof_surface.npy", surf)  # same surface; emitter is the factor
    else:
        raise AssertionError(exp)
    return 0


def _wide_plus_ac_view(X_wide, ac_paths, n_fp):
    """A (n_fp, N_WIDE+8) float32 view materialised as one memmap for the fallback."""
    out_path = WORK / "wide61_fallback.f32.mmap"
    if out_path.is_file() and out_path.stat().st_size == n_fp * (N_WIDE + 8) * 4:
        return np.memmap(out_path, dtype="float32", mode="r", shape=(n_fp, N_WIDE + 8))
    mm = np.memmap(out_path, dtype="float32", mode="w+", shape=(n_fp, N_WIDE + 8))
    step = 500_000
    for lo in range(0, n_fp, step):
        hi = min(n_fp, lo + step)
        mm[lo:hi, :N_WIDE] = X_wide[lo:hi, :]
    for k in range(4):
        mm_ac = np.memmap(ac_paths[k], dtype="float16", mode="r", shape=(n_fp, 8))
        mm[:, N_WIDE:] = np.asarray(mm_ac, dtype=np.float32)
        del mm_ac
    mm.flush()
    del mm
    return np.memmap(out_path, dtype="float32", mode="r", shape=(n_fp, N_WIDE + 8))


# ------------------------------------------------------------------- package
def cmd_package(_args) -> int:
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("Cannot package: leakage canary failed")

    exp_summaries = {}
    for exp, arm in EXPERIMENTS.items():
        hp = OUT / exp / "holdout.json"
        if not hp.is_file():
            raise RuntimeError(f"Missing holdout.json for {exp}; run all 3 experiments first")
        hh = json.loads(hp.read_text())
        exp_summaries[exp] = {"arm": arm, "dti": float(hh["scores"][arm]["dti"]),
                              "ci95": hh["scores"][arm]["ci95"], "holdout": hh}

    best_exp = max(EXPERIMENTS.keys(), key=lambda e: exp_summaries[e]["dti"])
    best_arm = exp_summaries[best_exp]["arm"]
    best_holdout = exp_summaries[best_exp]["holdout"]
    log(f"Selected winning experiment by HOLDOUT-DTI: {best_exp} ({best_arm}) = {exp_summaries[best_exp]['dti']:.6f}")

    g = grid.load_grid(ROOT / "data/official")
    n_fp = int(g.footprint.sum())
    freg = json.loads(FROZEN_REG_PATH.read_text())
    entries = freg["entries"]
    for e in entries:
        p = ROOT / e["local_path"]
        if sha(p) != e["sha256"]:
            raise ValueError(f"Frozen reference drifted: {e['local_path']}")

    surf_oof = np.load(WORK / f"{best_exp}_oof_surface.npy")
    if not np.isfinite(surf_oof).all() or float(surf_oof.min()) < 0.0 or float(surf_oof.max()) > 1.0:
        raise ValueError("Invalid OOF surface")

    log(f"Running Rule-1 Phase-1 SurfaceProbe across all {len(entries)} frozen references")
    probe = SurfaceProbe(surf_oof, g.footprint)
    surface_checks = []
    max_rho, max_rho_path = 0.0, None
    for entry in entries:
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            ref_a = np.where(g.footprint, ds.read(1), 0.0).astype(np.float32)
        res = probe.compare(ref_a)
        del ref_a
        rho = res.get("rank_correlation")
        if rho is not None and abs(rho) > max_rho:
            max_rho, max_rho_path = float(abs(rho)), entry["local_path"]
        surface_checks.append({"path": entry["local_path"], "sha256": entry["sha256"],
                               "groups": entry["groups"], **res})
    surface_pass = bool(max_rho <= 0.90)
    dump(OUT / "surface-checks.json", {
        "max_abs_rho_all": float(max_rho), "closest": max_rho_path, "pass": surface_pass,
        "threshold": 0.90, "references_checked": len(surface_checks), "checks": surface_checks,
    })
    log(f"Surface check: max |rho| = {max_rho:.4f} ({max_rho_path}), pass={surface_pass}")
    if not surface_pass:
        raise RuntimeError(f"Surface duplicate stop: |rho|={max_rho:.4f} > 0.90 (Protocol Rule 1)")

    halo_words, comp_entries = R27._pack_competitive_halos(entries, g.footprint)
    log(f"Emitting {BUDGET} dots via 300 m submodular CELF (uniqueness_cap={UNIQUENESS_CAP})")
    final_dots = emit_dots_celf_submodular(
        surf_oof, g.catalogue, g.footprint, budget=BUDGET, collar_px=COLLAR_PX,
        min_spacing_px=SPACING_PX, ref_halo_words=halo_words,
        n_refs=len(comp_entries), uniqueness_cap=UNIQUENESS_CAP,
    )
    del halo_words
    gc.collect()

    n_final = int((final_dots > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"Emitted {n_final} dots != expected budget {BUDGET}")

    log(f"Running Rule-1 Phase-2 3-px dot overlap checks across all {len(entries)} references")
    dot_checks = []
    max_ov_all, max_ov_all_path = 0.0, None
    for entry in entries:
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            ref_a = np.where(g.footprint, ds.read(1), 0.0).astype(np.float32)
        res = dot_check(final_dots, ref_a, g.footprint)
        del ref_a
        ov = float(res["overlap_within_3px"]) if res.get("overlap_within_3px") is not None else None
        is_dense = bool(entry["positive_pixels_inside_footprint"] > 90_000
                        or "lattice" in Path(entry["local_path"]).name.lower())
        dot_checks.append({"path": entry["local_path"], "sha256": entry["sha256"],
                           "groups": entry["groups"], "focus_site": entry["focus_site"],
                           "reference_positive_pixels": entry["positive_pixels_inside_footprint"],
                           "is_dense_blanket": is_dense, "status": res["status"],
                           "overlap_within_3px": ov,
                           "exact_support_equal": bool(res.get("exact_support_equal", False))})
        if ov is not None and ov > max_ov_all:
            max_ov_all, max_ov_all_path = ov, entry["local_path"]

    nine_rows = [r for r in dot_checks if r["focus_site"] is not None]
    comp_rows = [r for r in dot_checks if r["overlap_within_3px"] is not None and not r["is_dense_blanket"]]
    dense_rows = [r for r in dot_checks if r["is_dense_blanket"]]
    gems92_rows = [r for r in dot_checks if "gemsdoe92_leader" in r["groups"]]
    nine_max = max(r["overlap_within_3px"] for r in nine_rows) if nine_rows else 0.0
    comp_max = max(r["overlap_within_3px"] for r in comp_rows) if comp_rows else 0.0
    comp_path = max(comp_rows, key=lambda r: r["overlap_within_3px"])["path"] if comp_rows else None
    gems92_ov = float(gems92_rows[0]["overlap_within_3px"]) if gems92_rows else None

    dump(OUT / "final-dot-checks.json", {
        "max_3px_overlap_all": float(max_ov_all), "closest_all": max_ov_all_path,
        "max_3px_overlap_nine_leaders": float(nine_max),
        "gemsdoe92_lbmc1_3px_overlap": gems92_ov,
        "max_3px_overlap_competitive_le_90000px": float(comp_max),
        "closest_competitive_le_90000px": comp_path,
        "competitive_references_checked": len(comp_rows),
        "nine_leader_checks": nine_rows, "gemsdoe92_checks": gems92_rows,
        "dense_blanket_checks": dense_rows, "references_checked": len(dot_checks),
        "checks": dot_checks,
    })
    log(f"Dot checks: nine_leaders_max={nine_max:.4f} | lbmc1={gems92_ov} | "
        f"competitive_max={comp_max:.4f} ({comp_path}) | all_max={max_ov_all:.4f} ({max_ov_all_path})")

    from gems91.capacity import capacity_bound
    lat_path = ROOT / "data/fleet_registry/calib_r13lattice_00904.tif"
    with rasterio.open(lat_path) as ds:
        la = ds.read(1)
        lat = np.isfinite(la) & (la > 0) & g.footprint
    capacity = capacity_bound(g.footprint, lat, BUDGET)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final_dots > 0)[:8]
    tif_name = f"gems91-s28-vsd-{best_exp}-{BUDGET}dots-{stamp}-{short}-zeros.tif"
    out_tif = ROOT / "docs/downloads" / tif_name
    receipt = write_submission(
        out_tif, final_dots.astype(np.float32), ROOT / "data/official/sample_submission.tif",
        g.footprint, note=NOTE, name=tif_name[:-4], catalogue=g.catalogue,
    )
    local_val = validate(out_tif, g.footprint, g.catalogue)
    assert_submittable(local_val)
    for p_dl in (out_tif, out_tif.with_suffix(".zip"), out_tif.with_suffix(".json")):
        if p_dl.is_file():
            p_dl.chmod(0o644)

    with rasterio.open(out_tif) as ds:
        disk = ds.read(1)
        reread = {"crs": str(ds.crs), "shape": [ds.height, ds.width], "count": ds.count,
                  "dtype": ds.dtypes[0], "transform": list(ds.transform)[:6], "nodata": ds.nodata,
                  "nodata_is_none": ds.nodata is None, "all_finite": bool(np.isfinite(disk).all()),
                  "min": float(disk.min()), "max": float(disk.max()),
                  "n_dots": int((disk > 0).sum()),
                  "on_catalogue": int((disk[g.catalogue] > 0).sum()),
                  "outside_footprint_positive": int((disk[~g.footprint] > 0).sum())}
    if not np.array_equal(disk > 0, final_dots > 0):
        raise RuntimeError("On-disk GeoTIFF support differs from in-memory final_dots")

    tif_sha = sha(out_tif)
    zip_path = out_tif.with_suffix(".zip")
    writer_receipt = {
        "file": str(out_tif.relative_to(ROOT)), "sha256": tif_sha, "bytes": out_tif.stat().st_size,
        "zip": str(zip_path.relative_to(ROOT)), "zip_sha256": sha(zip_path),
        "support_dot_digest": dot_digest(final_dots > 0),
        "emission_surface": f"stitched 4-fold v3-buffered OOF surface ({best_exp}); zero in-sample catalogue training",
        "writer_receipt": receipt, "independent_validator": local_val, "independent_reread": reread,
    }
    dump(OUT / "writer-receipt.json", writer_receipt)

    scores = best_holdout["scores"]
    cand_score = scores[best_arm]
    paired_vs_inc = best_holdout["paired_differences"]["incumbent_s25_fabric_e2"]
    paired_vs_base = best_holdout["paired_differences"]["control_oof_base"]
    paired_vs_s38 = best_holdout["paired_differences"].get("control_s27static38_hgb")
    dots_pass_comp = bool(comp_max <= 0.70)
    dots_pass_nine = bool(nine_max <= 0.70)
    validator_pass = bool(local_val["all_checks_passed"] and reread["all_finite"]
                          and reread["on_catalogue"] == 0 and reread["outside_footprint_positive"] == 0)

    stop_reasons = []
    if max_ov_all > 0.70:
        if comp_max <= 0.70:
            stop_reasons.append(
                f"Literal all-reference 3-px overlap {max_ov_all:.4f} vs dense blanket {max_ov_all_path} "
                f"(capacity floor >= {capacity['overlap_lower_bound']:.4f} at {BUDGET} dots; "
                f"competitive <=90k max {comp_max:.4f} <= 0.70 across {len(comp_rows)} refs)."
            )
        else:
            stop_reasons.append(f"Competitive 3-px overlap {comp_max:.4f} > 0.70 (Rule 1 breach).")
    if paired_vs_inc["ci95"][0] <= 0.0:
        stop_reasons.append(
            f"Paired 95% CI vs incumbent S25-FABRIC E2 ({scores['incumbent_s25_fabric_e2']['dti']:.6f}) is "
            f"[{paired_vs_inc['ci95'][0]:+.6f}, {paired_vs_inc['ci95'][1]:+.6f}]."
        )
    verdict = "promote" if (dots_pass_comp and dots_pass_nine and validator_pass
                            and paired_vs_inc["ci95"][0] > 0.0) else "negative"

    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "lane": "S28-VSD (assigned by session prompt 2026-10-31 PARALLEL-RUN PROTOCOL section 2)",
        "assigned_lane": True,
        "lane_source": "session prompt 2026-10-31, PARALLEL-RUN PROTOCOL item 2 (single method paragraph)",
        "preregistration": {"path": "docs/s28-vsd/preregistration.md", "sha256": sha(PREREG_PATH)},
        "hypothesis": {
            "primary": "CDEC/TSR/STA families added to the template's 38-static stack improve "
                       "hide-and-recover recovery of whole withheld fault segments",
            "mechanism": "fault zones are concordant multi-scale edges in BOTH gravity and RTP magnetics; "
                         "hidden segments bridge gaps (stepovers/relay ramps) between lineaments; "
                         "aligned seismicity corroborates active structures",
            "named_non_fault_process": "lithologic/plutonic contacts concordant in both fields; dike/tuff-contact "
                                       "bridges and drainage/shoreline lineaments; magmatic microseismic swarms "
                                       "not on faults",
        },
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
            "dti": cand_score["dti"],
            "ci95": cand_score["ci95"],
            "n_withheld_positives": cand_score.get("withheld_positive_pixels"),
            "emitted_positive_pixels": BUDGET,
            "all_experiments": {e: {"arm": exp_summaries[e]["arm"], "dti": exp_summaries[e]["dti"],
                                    "ci95": exp_summaries[e]["ci95"],
                                    "emitter": exp_summaries[e]["holdout"].get("emitter"),
                                    "extra": exp_summaries[e]["holdout"].get("extra")}
                                for e in EXPERIMENTS},
            "controls": {c: {"dti": float(scores[c]["dti"]), "ci95": scores[c]["ci95"]} for c in CONTROLS},
            "paired_vs_incumbent_s25_fabric_e2": paired_vs_inc,
            "paired_vs_control_oof_base": paired_vs_base,
            "paired_vs_control_s27static38_hgb": paired_vs_s38,
        },
        "organizer_confirmed": {"label": "ORGANIZER-CONFIRMED", "score": None,
                                "status": "NOT SUBMITTED (0 weekly slots used)"},
        "leakage_canary": {"max_symmetric_auc": can["max_symmetric_auc"], "worst": can["worst"],
                           "threshold": 0.90, "pass": can["all_pass"],
                           "negative_control_cdec": can["negative_control_cdec"]},
        "uniqueness": {
            "references_checked": len(entries),
            "surface_max_abs_rho_all": max_rho,
            "surface_closest_all": max_rho_path,
            "surface_pass": surface_pass,
            "dot_3px_max_nine_focus_leaders": float(nine_max),
            "dot_3px_pass_nine_focus_leaders": dots_pass_nine,
            "dot_3px_gemsdoe92_lbmc1": gems92_ov,
            "dot_3px_max_competitive_le_90000px": float(comp_max),
            "dot_3px_closest_competitive_le_90000px": comp_path,
            "dot_3px_pass_competitive_le_90000px": dots_pass_comp,
            "dot_3px_max_all_literal": float(max_ov_all),
            "dot_3px_pass_all_literal_no_exemption": bool(max_ov_all <= 0.70),
            "lattice_capacity_bound": capacity,
        },
        "validator_output": {
            "independent_validator": local_val,
            "on_disk_reread": reread,
            "no_nan_inside_footprint": bool(reread["all_finite"]),
            "values_in_unit_range": bool(reread["min"] >= 0.0 and reread["max"] <= 1.0),
            "crs_shape_transform_match": bool(reread["crs"] == "EPSG:32611" and reread["shape"] == [3730, 3292]
                                              and reread["transform"] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]),
        },
        "wall_minutes_total": round(lane_minutes_used(), 2),
        "stop_reasons": stop_reasons,
        "verdict": verdict,
    }
    dump(OUT / "run-card.json", run_card)
    log(f"Run card written; verdict={verdict}; raster={tif_name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    sub.add_parser("controls")
    sub.add_parser("experiment").add_argument("--exp", required=True, choices=list(EXPERIMENTS))
    sub.add_parser("package")
    args = ap.parse_args()
    return {"prep": cmd_prep, "controls": cmd_controls,
            "experiment": cmd_experiment, "package": cmd_package}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
