#!/usr/bin/env python3
"""S28-VFCD lane runner (preregistered in docs/s28-vfcd/preregistration.md).

Subcommands:
  prep        Verify pinned inputs + preregistration SHA; build/reuse the shared
              feature caches (S25 base + S27 static38 are REUSED from
              data/work/s27_cache, never rebuilt); compute the new VENT (T1-T8
              base, T9-T12 fold-linked) and CONS features; run Rule-4
              single-feature leakage canaries on every feature any arm uses.
  controls    Score matched controls on the frozen v3 folds (all CELF):
              ctrl_oof_base (BASE), ctrl_oof_phys (BASE+STATIC38), and
              ref_r0_dots (pinned GEMSDOE32 champion dots, learning-only
              anchor, unmatched exact budget).
  experiment  --exp e1|e2|e3 : run one preregistered arm (PU-OOF HGB surface +
              300 m CELF emission) and record pooled HOLDOUT-DTI + paired CI.
  package     Select the arm with the highest pooled HOLDOUT-DTI (frozen rule);
              Rule-1 surface + final-dot uniqueness against every frozen
              registry reference and every docs/downloads/*.tif; emit 37,654
              dots via CELF with uniqueness_cap=0.64; write the shared
              fail-closed zeros-encoded GeoTIFF + one-TIFF ZIP + validator
              receipt; SGMC-off-catalogue blind diagnostic; run card.

Strictly enforces the Parallel-Run Protocol: max 3 experiments / 2 h, zero
weekly submission slots spent here, fail-closed gates, every number labeled.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402
from sklearn.metrics import roc_auc_score  # noqa: E402

import run_s27_osdr as S27  # noqa: E402  shared glue (S25 caches, arm scoring, halo packing)
from evaluate_holdout import score_off_catalogue_sgmc  # noqa: E402
from gems91 import vfcd28 as V  # noqa: E402
from gems91.cvdc_osdr27 import ALL_STATIC_NAMES, compute_cvdc27_features, ensure_raw19_memmap  # noqa: E402
from gems91.io import dot_digest  # noqa: E402
from gems91.novelty import SurfaceProbe, dot_check  # noqa: E402
from gems91.pdwc21 import emit_dots_celf_submodular  # noqa: E402
from vendor.gems57 import evaluate_holdout as EH  # noqa: E402
from vendor.gems57 import grid, spatial  # noqa: E402
from vendor.gems57.submission_writer import write_submission  # noqa: E402
from vendor.gems57.validate import assert_submittable, validate  # noqa: E402

OUT = ROOT / "docs/s28-vfcd"
WORK = ROOT / "data/work/s28_cache"
S27WORK = ROOT / "data/work/s27_cache"
PREREG_PATH = OUT / "preregistration.md"
PREREG_SHA256 = "152f1d5577256adcba9fa75488276436bf003160f902715ae587967a6763abee"
FROZEN_REG_PATH = ROOT / "docs/s27-osdr/frozen-registry.json"

BUDGET = 37_654
COLLAR_PX = 3.05
SPACING_PX = 3.05
UNIQUENESS_CAP = 0.64
SEED = 520810
HGB_PARAMS = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=40,
    l2_regularization=1.0,
    early_stopping=False,
)
NEG_PER_POS = 4

EXPERIMENTS = {
    "e1": "vfcd_e1_vent_celf",
    "e2": "vfcd_e2_vent_phys_celf",
    "e3": "vfcd_e3_vent_phys_cons_celf",
}
CONTROLS = ["ctrl_oof_base", "ctrl_oof_phys", "ref_r0_dots"]

NOTE = "S28 VFCD geothermometer-gated discharge conduit + SGMC-off concordance PU-OOF CELF 37654d"
assert len(NOTE) <= 140, len(NOTE)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


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
    if not PREREG_PATH.is_file() or sha(PREREG_PATH) != PREREG_SHA256:
        raise ValueError("preregistration.md missing or SHA drifted after freeze")
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        p = ROOT / "data" / row["local_subpath"]
        if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
            raise ValueError(f"Pinned input absent or drifted: {row['id']}")
        checked[row["id"]] = {"path": "data/" + row["local_subpath"], "sha256": row["sha256"]}
    return checked


def open_static_memmap(n_fp: int) -> np.memmap:
    return np.memmap(S27WORK / "cvdc27_static38.f32.mmap", dtype="float32", mode="r", shape=(n_fp, len(ALL_STATIC_NAMES)))


# ---------------------------------------------------------------- feature prep
def _ensure_static(raw19, g) -> np.memmap:
    n_fp = int(g.footprint.sum())
    p = S27WORK / "cvdc27_static38.f32.mmap"
    if not (p.is_file() and p.stat().st_size == n_fp * len(ALL_STATIC_NAMES) * 4):
        log("Computing 38 S27-CVDC static features into shared cache (not previously present)")
        X_mm = np.memmap(p, dtype="float32", mode="w+", shape=(n_fp, len(ALL_STATIC_NAMES)))
        _, surfs, _ = compute_cvdc27_features(raw19, g.footprint, out_fp_matrix=X_mm)
        np.save(S27WORK / "control_cvdc_surface.npy", surfs["control_cvdc_surface"])
        np.save(S27WORK / "control_gravgrad.npy", surfs["control_gravgrad"])
        X_mm.flush()
        del X_mm
    return open_static_memmap(n_fp)


def _ensure_vent(g, folds) -> dict:
    vent_dir = WORK / "vent"
    manifest = vent_dir / "manifest.json"
    if manifest.is_file():
        return json.loads(manifest.read_text())
    vent_dir.mkdir(parents=True, exist_ok=True)
    log("Computing VENT base features (T1-T8) from pinned GDR CSV")
    base, receipt = V.compute_vent_base_features(
        ROOT / "data/external/gdr_wellspring_in_footprint.csv", g.shape
    )
    base_paths = {}
    for name, arr in base.items():
        fp_arr = np.where(g.footprint, arr, 0.0).astype(np.float32)
        np.save(vent_dir / f"{name}.npy", fp_arr)
        base_paths[name] = str((vent_dir / f"{name}.npy").relative_to(ROOT))
    del base

    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc_bool = np.nan_to_num(ds.read(1), nan=0.0) > 0

    linked_paths = []
    for k, fold in enumerate(folds):
        log(f"Computing VENT fold-linked features (T9-T12) for fold {k}")
        lk = V.compute_vent_linked_features(
            {n: np.load(vent_dir / f"{n}.npy", mmap_mode="r") for n in V.VENT_BASE_NAMES},
            ROOT / "data/external/gdr_wellspring_in_footprint.csv",
            g.shape,
            fold["visible"],
            sgmc_bool,
        )
        kdir = vent_dir / f"fold{k}"
        kdir.mkdir(exist_ok=True)
        row = {}
        for name, arr in lk.items():
            np.save(kdir / f"{name}.npy", np.where(g.footprint, arr, 0.0).astype(np.float32))
            row[name] = str((kdir / f"{name}.npy").relative_to(ROOT))
        linked_paths.append(row)
    man = {"base": base_paths, "linked_by_fold": linked_paths, "receipt": receipt}
    dump(manifest, man)
    return man


def _ensure_cons(g) -> dict:
    cons_dir = WORK / "cons"
    manifest = cons_dir / "manifest.json"
    if manifest.is_file():
        return json.loads(manifest.read_text())
    cons_dir.mkdir(parents=True, exist_ok=True)
    log("Computing CONS features from pinned anc lineage rasters")
    anc = {
        "anc_h19_5": ROOT / "data/registry/calib_h195_01922.tif",
        "anc_h19_4": ROOT / "data/registry/calib_h194_01894.tif",
        "anc_h16_1": ROOT / "data/registry/calib_h161_01855.tif",
        "anc_d1_5": ROOT / "data/registry/calib_d15_02477.tif",
        "anc_d2_8": ROOT / "data/registry/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
        "anc_solo_d2_8": ROOT / "data/registry/GEMSDOE28__h27-4-r1-solo-d2-8.tif",
    }
    arrays = {}
    for name, p in anc.items():
        with rasterio.open(p) as ds:
            arrays[name] = np.where(g.footprint, np.nan_to_num(ds.read(1), nan=0.0), 0.0).astype(np.float64)
    feats = V.compute_consensus_features(arrays, g.footprint)
    paths = {}
    for name, arr in feats.items():
        np.save(cons_dir / f"{name}.npy", np.where(g.footprint, arr, 0.0).astype(np.float32))
        paths[name] = str((cons_dir / f"{name}.npy").relative_to(ROOT))
    dump(manifest, {"paths": paths})
    return {"paths": paths}


def _canary_feature(vec_fp, name, scope, fp_idx_grid, folds, rows_out, max_state):
    for fidx, fold in enumerate(folds):
        valid = fold["_fp"] & fold["region"] & ~fold["visible"]
        pr = fp_idx_grid[fold["truth"] & valid]
        nr = fp_idx_grid[(~fold["truth"]) & valid][::4]
        if pr.size == 0 or nr.size == 0:
            continue
        pv = np.nan_to_num(np.asarray(vec_fp[pr], np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        nv = np.nan_to_num(np.asarray(vec_fp[nr], np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        auc = float(roc_auc_score(np.concatenate([np.ones(pv.size), np.zeros(nv.size)]), np.concatenate([pv, nv])))
        sym = max(auc, 1.0 - auc)
        rows_out.append({"feature": name, "scope": f"{scope}fold{fidx}", "n_positive": int(pv.size),
                         "n_negative": int(nv.size), "auc": auc, "symmetric_auc": sym})
        if sym > max_state[0]:
            max_state[0], max_state[1] = sym, f"{name} {scope}fold{fidx}"


def cmd_prep(_args) -> int:
    t0 = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    n_fp = int(g.footprint.sum())

    raw19 = ensure_raw19_memmap(
        ROOT / "data/bridge/gems-geodawn-numerical-features.tif", S27WORK / "raw19.f32.mmap"
    )
    s25_groups = S27._ensure_s25_features(raw19, g)
    X_static = _ensure_static(raw19, g)
    vent_man = _ensure_vent(g, list(spatial.folds(g.catalogue, g.footprint, buffer_px=80)))
    cons_man = _ensure_cons(g)
    log("Feature caches ready")

    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fp_idx_grid = np.full(g.shape, -1, dtype=np.int64)
    fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int64)
    for fold in folds:
        fold["_fp"] = g.footprint

    canaries, max_state = [], [0.0, None]

    def canary_2d(arr2d, name, scope=""):
        vec = np.asarray(arr2d, np.float32).ravel()
        _canary_feature(vec, name, scope, fp_idx_grid, folds, canaries, max_state)

    for name in s25_groups["base"]:
        canary_2d(np.load(S27WORK / "s25_repro_feats" / f"{name}.npy", mmap_mode="r"), name)
    for j, name in enumerate(ALL_STATIC_NAMES):
        _canary_feature(np.asarray(X_static[:, j]), name, "", fp_idx_grid, folds, canaries, max_state)
    for name in V.VENT_BASE_NAMES:
        canary_2d(np.load(ROOT / vent_man["base"][name], mmap_mode="r"), name)
    for k, row in enumerate(vent_man["linked_by_fold"]):
        for name, rel in row.items():
            vec2d = np.load(ROOT / rel, mmap_mode="r")
            valid = g.footprint & folds[k]["region"] & ~folds[k]["visible"]
            pr = fp_idx_grid[folds[k]["truth"] & valid]
            nr = fp_idx_grid[(~folds[k]["truth"]) & valid][::4]
            if pr.size == 0 or nr.size == 0:
                continue
            pv = np.nan_to_num(np.asarray(vec2d.ravel()[pr], np.float64), nan=0.0, posinf=0.0, neginf=0.0)
            nv = np.nan_to_num(np.asarray(vec2d.ravel()[nr], np.float64), nan=0.0, posinf=0.0, neginf=0.0)
            auc = float(roc_auc_score(np.concatenate([np.ones(pv.size), np.zeros(nv.size)]), np.concatenate([pv, nv])))
            sym = max(auc, 1.0 - auc)
            canaries.append({"feature": name, "scope": f"fold{k}-linked", "n_positive": int(pv.size),
                             "n_negative": int(nv.size), "auc": auc, "symmetric_auc": sym})
            if sym > max_state[0]:
                max_state[0], max_state[1] = sym, f"{name} fold{k}-linked"
    for name in V.CONS_FEATURE_NAMES:
        canary_2d(np.load(ROOT / cons_man["paths"][name], mmap_mode="r"), name)

    canary_pass = bool(max_state[0] <= 0.90)
    dump(OUT / "canaries.json", {
        "max_symmetric_auc": float(max_state[0]),
        "worst": max_state[1],
        "all_pass": canary_pass,
        "threshold": 0.90,
        "evaluator_version": EH.VERSION,
        "split_version": folds[0]["receipt"]["split_version"],
        "n_checks": len(canaries),
        "elapsed_seconds": float(time.monotonic() - t0),
        "inputs_verified": inputs,
        "preregistration": {"path": str(PREREG_PATH.relative_to(ROOT)), "sha256": sha(PREREG_PATH)},
        "canaries": canaries,
    })
    log(f"Canaries: max symmetric AUC = {max_state[0]:.4f} ({max_state[1]}), pass={canary_pass}")
    return 0 if canary_pass else 2


# ------------------------------------------------------------------ OOF model
def _sources_for_arm(arm_features: list[str], vent_man, cons_man):
    """Return (static_sources, linked_by_fold_sources): list of (kind, payload)."""
    s25_dir = S27WORK / "s25_repro_feats"
    groups = json.loads((s25_dir / "groups.json").read_text())
    static: list = []
    for name in groups["base"]:
        if "base" in arm_features:
            static.append(("np", str(s25_dir / f"{name}.npy")))
    if "static38" in arm_features:
        for j in range(len(ALL_STATIC_NAMES)):
            static.append(("fpmem", j))
    if "cons" in arm_features:
        for name in V.CONS_FEATURE_NAMES:
            static.append(("np", cons_man["paths"][name]))
    linked = []
    for row in vent_man["linked_by_fold"]:
        fold_src = list(static)
        if "vent" in arm_features:
            for name in V.VENT_LINKED_NAMES:
                fold_src.append(("np", row[name]))
        linked.append(fold_src)
    if "vent" in arm_features:
        # vent base features are catalogue-free: append to every fold's sources
        for row_src in linked:
            for name in V.VENT_BASE_NAMES:
                row_src.append(("np", vent_man["base"][name]))
    return static, linked


def _oof_surface(sources_static, sources_by_fold, g, folds, X_static) -> np.ndarray:
    n_fp = int(g.footprint.sum())
    fp_idx_grid = np.full(g.shape, -1, dtype=np.int64)
    fp_idx_grid[g.footprint] = np.arange(n_fp, dtype=np.int64)
    flat_shape = g.shape[0] * g.shape[1]

    def gather(flat_idx: np.ndarray, sources) -> np.ndarray:
        X = np.empty((len(flat_idx), len(sources)), dtype=np.float32)
        fp_rows = fp_idx_grid.ravel()[flat_idx]
        for j, (kind, payload) in enumerate(sources):
            if kind == "np":
                X[:, j] = np.load(ROOT / payload if not str(payload).startswith("/") else payload, mmap_mode="r").ravel()[flat_idx]
            else:
                if (fp_rows < 0).any():
                    raise ValueError("flat index outside footprint asked for an fp column")
                X[:, j] = np.asarray(X_static[fp_rows, payload], dtype=np.float32)
        return X

    out = np.zeros(g.shape, dtype=np.float64)
    flat_cat = g.catalogue.ravel()
    for fidx, fold in enumerate(folds):
        sources = sources_by_fold[fidx]
        flat_train = fold["train"].ravel()
        pos = np.flatnonzero(flat_train & flat_cat)
        pool = np.flatnonzero(flat_train & ~flat_cat)
        rng = np.random.default_rng(SEED)
        neg = rng.choice(pool, size=min(NEG_PER_POS * len(pos), len(pool)), replace=False)
        idx = np.concatenate([pos, neg])
        y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
        model = HistGradientBoostingClassifier(random_state=SEED, **HGB_PARAMS)
        model.fit(gather(idx, sources), y)
        acc = np.zeros(flat_shape, dtype=np.float64)
        p_idx = np.flatnonzero(fold["region"].ravel())
        for lo in range(0, len(p_idx), 250_000):
            ch = p_idx[lo : lo + 250_000]
            acc[ch] = model.predict_proba(gather(ch, sources))[:, 1]
        out += acc.reshape(g.shape)
        del model, acc
        gc.collect()
        log(f"  OOF fold {fidx} fit+predict done ({len(sources)} features)")
    return np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)


def _load_state():
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)
    vent_man = json.loads((WORK / "vent" / "manifest.json").read_text())
    cons_man = json.loads((WORK / "cons" / "manifest.json").read_text())
    n_fp = int(g.footprint.sum())
    X_static = open_static_memmap(n_fp)
    return g, folds, budgets, vent_man, cons_man, X_static


def _terms_path():
    return WORK / "holdout-terms.npz", WORK / "per-fold-arms.json"


def _save_terms(terms_by_arm: dict, per_fold: list):
    tp, pf = _terms_path()
    np.savez_compressed(tp, **terms_by_arm)
    dump(pf, per_fold)


def _load_terms():
    tp, pf = _terms_path()
    if not tp.is_file():
        return {}, []
    with np.load(tp) as z:
        terms = {k: z[k] for k in z.files}
    per_fold = json.loads(pf.read_text()) if pf.is_file() else []
    return terms, per_fold


def cmd_controls(_args) -> int:
    t0 = time.monotonic()
    verify_pinned_inputs()
    g, folds, budgets, vent_man, cons_man, X_static = _load_state()
    terms_by_arm, per_fold = _load_terms()

    arms = {
        "ctrl_oof_base": (["base"], None),
        "ctrl_oof_phys": (["base", "static38"], None),
    }
    for arm, (feat, _) in arms.items():
        if arm in terms_by_arm:
            log(f"{arm} already cached")
            continue
        surf_path = WORK / f"{arm}_oof_surface.npy"
        if surf_path.is_file():
            surf = np.load(surf_path)
        else:
            log(f"Building OOF surface for {arm}")
            st, by_fold = _sources_for_arm(feat, vent_man, cons_man)
            surf = _oof_surface(st, by_fold, g, folds, X_static)
            np.save(surf_path, surf)
        t_arm, pf_arm = S27._score_arm_on_folds(arm, surf, g, folds, budgets, emitter="celf")
        terms_by_arm[arm] = t_arm
        per_fold.extend(pf_arm)
        _save_terms(terms_by_arm, per_fold)
        log(f"{arm}: HOLDOUT-DTI = {float(EH.from_terms(t_arm.sum(axis=0))):.6f}")
        del surf
        gc.collect()

    if "ref_r0_dots" not in terms_by_arm:
        log("Scoring pinned R0 champion dots (learning/education anchor; unmatched exact budget)")
        with rasterio.open(ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif") as ds:
            r0 = np.where(g.footprint, np.nan_to_num(ds.read(1), nan=0.0), 0.0).astype(np.float32)
        total_terms = None
        for fidx, fold in enumerate(folds):
            res, terms = EH.evaluate(r0, fold, g.footprint, block_side=200, origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            per_fold.append({"arm": "ref_r0_dots", "fold": fidx, "budget": int(res["n_emitted"]),
                             "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                             "tpw": float(res["tpw"]), "fpw": float(res["fpw"]), "fnw": float(res["fnw"]),
                             "fold_dti": float(EH.from_terms(terms.sum(axis=0)))})
        terms_by_arm["ref_r0_dots"] = total_terms
        _save_terms(terms_by_arm, per_fold)
        log(f"ref_r0_dots: HOLDOUT-DTI = {float(EH.from_terms(total_terms.sum(axis=0))):.6f}")
    log(f"Controls cached in {time.monotonic() - t0:.1f}s")
    return 0


ARM_FEATURES = {
    "e1": ["base", "vent"],
    "e2": ["base", "static38", "vent"],
    "e3": ["base", "static38", "vent", "cons"],
}


def cmd_experiment(args) -> int:
    t0 = time.monotonic()
    exp = args.exp
    if exp not in EXPERIMENTS:
        raise ValueError(f"Unknown experiment {exp}")
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").is_file():
        log(f"{exp} already recorded")
        return 0
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("Rule-4 leakage canary failed; lane stopped")
    verify_pinned_inputs()
    g, folds, budgets, vent_man, cons_man, X_static = _load_state()
    terms_by_arm, per_fold = _load_terms()
    for c in CONTROLS:
        if c not in terms_by_arm:
            raise RuntimeError("Run 'controls' before 'experiment'")

    arm = EXPERIMENTS[exp]
    surf_path = WORK / f"{arm}_oof_surface.npy"
    if surf_path.is_file():
        surf = np.load(surf_path)
    else:
        log(f"Building OOF surface for {arm} (features: {ARM_FEATURES[exp]})")
        st, by_fold = _sources_for_arm(ARM_FEATURES[exp], vent_man, cons_man)
        surf = _oof_surface(st, by_fold, g, folds, X_static)
        np.save(surf_path, surf)
    t_cand, pf_cand = S27._score_arm_on_folds(arm, surf, g, folds, budgets, emitter="celf")
    terms_by_arm[arm] = t_cand
    per_fold.extend(pf_cand)
    _save_terms(terms_by_arm, per_fold)

    arms = [arm] + CONTROLS
    sub = {a: terms_by_arm[a] for a in arms}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=arm)
    pooled["per_fold"] = [r for r in per_fold if r["arm"] in arms]
    pooled["fold_receipts"] = [f["receipt"] for f in folds]
    pooled["matched_controls"] = CONTROLS
    pooled["budget_total"] = BUDGET
    pooled["features"] = ARM_FEATURES[exp]
    pooled["elapsed_seconds"] = float(time.monotonic() - t0)
    dump(outdir / "holdout.json", pooled)
    for a in arms:
        s = pooled["scores"][a]
        log(f"  {a}: HOLDOUT-DTI = {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in CONTROLS:
        d = pooled["paired_differences"][c]
        log(f"  Delta vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return 0


# ------------------------------------------------------------------- package
def _extra_reference_entries(frozen_paths: set[str]) -> list[dict]:
    entries = []
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        rel = str(p.relative_to(ROOT))
        if rel in frozen_paths:
            continue
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        g_shape_ok = arr.shape == (3730, 3292)
        pos = int(np.isfinite(arr).sum() and ((np.nan_to_num(arr, nan=0.0) > 0)).sum())
        del arr
        entries.append({
            "sha256": sha(p),
            "local_path": rel,
            "groups": ["docs_downloads_extra"],
            "in_frozen_64": False,
            "focus_site": None,
            "positive_pixels_inside_footprint": pos,
            "is_binary_support": True,
            "is_competitive_sparse_le_90k": bool(g_shape_ok and pos <= 90_000),
        })
    return entries


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
        exp_summaries[exp] = {"arm": arm, "dti": float(hh["scores"][arm]["dti"]), "ci95": hh["scores"][arm]["ci95"], "holdout": hh}
    best_exp = max(EXPERIMENTS, key=lambda e: exp_summaries[e]["dti"])
    best_arm = exp_summaries[best_exp]["arm"]
    best_holdout = exp_summaries[best_exp]["holdout"]
    log(f"Selected by frozen rule argmax HOLDOUT-DTI: {best_exp} ({best_arm}) = {exp_summaries[best_exp]['dti']:.6f}")

    g = grid.load_grid(ROOT / "data/official")
    freg = json.loads(FROZEN_REG_PATH.read_text())
    entries = list(freg["entries"])
    frozen_paths = {e["local_path"] for e in entries}
    for e in entries:
        p = ROOT / e["local_path"]
        if not p.is_file() or sha(p) != e["sha256"]:
            raise ValueError(f"Frozen reference drifted: {e['local_path']}")
    extras = _extra_reference_entries(frozen_paths)
    all_entries = entries + extras
    log(f"References: {len(entries)} frozen + {len(extras)} extra docs/downloads")

    surf = np.load(WORK / f"{best_arm}_oof_surface.npy")
    if not np.isfinite(surf).all() or float(surf.min()) < 0.0 or float(surf.max()) > 1.0:
        raise ValueError("Invalid OOF surface")

    log("Rule-1 Phase-1: SurfaceProbe vs every reference")
    probe = SurfaceProbe(surf, g.footprint)
    surface_checks = []
    max_rho, max_rho_path = 0.0, None
    for entry in all_entries:
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            ref_a = np.where(g.footprint, np.nan_to_num(ds.read(1), nan=0.0), 0.0).astype(np.float32)
        res = probe.compare(ref_a)
        del ref_a
        row = {"path": entry["local_path"], "sha256": entry["sha256"], "groups": entry["groups"],
               "focus_site": entry.get("focus_site"), **res}
        surface_checks.append(row)
        rho = res.get("rank_correlation")
        if rho is not None and abs(rho) > max_rho:
            max_rho, max_rho_path = float(abs(rho)), entry["local_path"]
    surface_pass = bool(max_rho <= 0.90)
    dump(OUT / "surface-checks.json", {"max_abs_rho_all": max_rho, "closest_all": max_rho_path,
                                       "pass": surface_pass, "threshold": 0.90,
                                       "references_checked": len(surface_checks), "checks": surface_checks})
    log(f"Surface check: max |rho| = {max_rho:.4f} ({max_rho_path}), pass={surface_pass}")
    if not surface_pass:
        raise RuntimeError(f"Surface duplicate stop: |rho|={max_rho:.4f} > 0.90")

    comp_all = [e for e in all_entries if e.get("is_competitive_sparse_le_90k")]
    log(f"Packing 3-px halos for {len(comp_all)} competitive references")
    halo_words, comp_entries = S27._pack_competitive_halos(all_entries, g.footprint)
    log(f"Emitting {BUDGET} dots via 300 m CELF (uniqueness_cap={UNIQUENESS_CAP})")
    final_dots = emit_dots_celf_submodular(
        surf, g.catalogue, g.footprint, budget=BUDGET,
        collar_px=COLLAR_PX, min_spacing_px=SPACING_PX,
        ref_halo_words=halo_words, n_refs=len(comp_entries), uniqueness_cap=UNIQUENESS_CAP,
    )
    del halo_words
    gc.collect()
    n_final = int((final_dots > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"Emitted {n_final} dots != budget {BUDGET}")

    log("Rule-1 Phase-2: final-dot overlap vs every reference")
    dot_checks = []
    dense_rows = []
    for entry in all_entries:
        with rasterio.open(ROOT / entry["local_path"]) as ds:
            ref_a = np.where(g.footprint, np.nan_to_num(ds.read(1), nan=0.0), 0.0).astype(np.float32)
        res = dot_check(final_dots, ref_a, g.footprint)
        del ref_a
        ov = res.get("overlap_within_3px")
        is_dense = bool(entry["positive_pixels_inside_footprint"] > 90_000
                        or "lattice" in Path(entry["local_path"]).name.lower())
        row = {"path": entry["local_path"], "sha256": entry["sha256"], "groups": entry["groups"],
               "focus_site": entry.get("focus_site"),
               "reference_positive_pixels": entry["positive_pixels_inside_footprint"],
               "is_dense_blanket": is_dense, "status": res.get("status"), "overlap_within_3px": ov}
        dot_checks.append(row)
        if is_dense:
            dense_rows.append(row)
    comp_rows = [r for r in dot_checks if not r["is_dense_blanket"] and r["overlap_within_3px"] is not None]
    nine_rows = [r for r in dot_checks if r["focus_site"] is not None]
    comp_best = max(comp_rows, key=lambda r: r["overlap_within_3px"])
    nine_max = max((r["overlap_within_3px"] for r in nine_rows), default=None)
    dense_max = max((r["overlap_within_3px"] for r in dense_rows), default=None)
    comp_pass = bool(comp_best["overlap_within_3px"] <= 0.70)
    dump(OUT / "final-dot-checks.json", {
        "max_3px_overlap_competitive_le_90000px": float(comp_best["overlap_within_3px"]),
        "closest_competitive": comp_best["path"], "max_3px_overlap_nine_leaders": nine_max,
        "max_3px_overlap_dense_blanket_calibration": dense_max,
        "dense_blanket_checks": dense_rows, "competitive_pass": comp_pass,
        "threshold": 0.70, "references_checked": len(dot_checks), "checks": dot_checks,
    })
    log(f"Dot checks: competitive max={comp_best['overlap_within_3px']:.4f} ({comp_best['path']}), "
        f"nine max={nine_max}, dense/calibration max={dense_max}, pass={comp_pass}")
    if not comp_pass:
        raise RuntimeError(f"Final-dot duplicate stop vs competitive references: {comp_best['overlap_within_3px']:.4f} > 0.70")

    dot_tag = dot_digest(final_dots > 0)[:8]
    stem = f"gems91-s28-{best_arm}-37654dots-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{dot_tag}-zeros"
    out_tif = ROOT / "docs/downloads" / f"{stem}.tif"
    if out_tif.exists():
        raise RuntimeError(f"Refusing to overwrite {out_tif}")
    log(f"Writing submission bundle {out_tif.name}")
    receipt = write_submission(
        out_tif, final_dots, ROOT / "data/official/sample_submission.tif", g.footprint,
        note=NOTE, name=stem, catalogue=g.catalogue,
        metadata={"lane": "S28-VFCD", "experiment": best_exp, "arm": best_arm,
                  "holdout_evaluator_version": EH.VERSION,
                  "preregistration_sha256": sha(PREREG_PATH)},
    )
    local_val = validate(out_tif, g.footprint, g.catalogue)
    assert_submittable(local_val)

    sgmc_path = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
    with rasterio.open(sgmc_path) as ds:
        sgmc = ds.read(1)
    sgmc_diag = score_off_catalogue_sgmc(final_dots, sgmc, g.catalogue, g.footprint)
    sgmc_diag500 = score_off_catalogue_sgmc(final_dots, sgmc, g.catalogue, g.footprint, min_cat_dist_px=5.0)
    d_cat = ndi.distance_transform_edt(~g.catalogue)
    dots_y, dots_x = np.nonzero(final_dots > 0)
    diag = {
        "label": "POST-HOC DIAGNOSTICS — SGMC-OFFCAT-CONTROL-DTI (blind independent control). Not a leaderboard score.",
        "sgmc_offcat_3px": sgmc_diag,
        "sgmc_offcat_500m": sgmc_diag500,
        "dot_geography": {
            "median_distance_to_catalogue_px": float(np.median(d_cat[dots_y, dots_x])),
            "n_dots": int(len(dots_y)),
        },
    }
    dump(OUT / "diagnostics.json", diag)

    run_card = {
        "schema": "gems91.run-card.v2",
        "lane": "S28-VFCD (self-assigned; geothermometer-gated discharge conduit + SGMC-off concordance, PU-OOF CELF)",
        "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hypothesis": "H1 geothermometer-gated discharge conduit (+H2 SGMC-off concordance): high-enthalpy "
                      "discharge corridors and USGS-mapped/INGENIOUS-unmapped fault segments are surface "
                      "evidence of blind faults missing from the USGS/INGENIOUS catalogue (docs/HYPOTHESES_S28_VFCD.md).",
        "mechanism": "Permeable fault damage zones tapping the brittle-ductive transition channel high-enthalpy "
                     "fluid; vent-to-vent alignment marks the concealed strand. 12 GDR-derived features "
                     "(geothermometer-weighted kernels, vent-lineament corridor density, SGMC-off concordance) "
                     "+ the template's cached S25/S27 physics stacks feed a 4-fold PU-OOF HGB; 37,654 unit dots "
                     "are placed by 300 m CELF submodular emission with >=3.05 px catalogue collar.",
        "named_non_fault_mimic": "Groundwater discharge on permeable ash-flow tuffs / carbonate contact karst; "
                                 "basin-margin fan springs; 1:250 k SGMC generalization lines beyond field "
                                 "verification (all documented, none removed).",
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "split_version": "label-blind-quadrants-v3-feature-buffered",
            "n_withheld_positives": int(sum(f["receipt"]["truth_px"] for f in spatial.folds(g.catalogue, g.footprint, buffer_px=80))),
            "selected_arm": best_arm,
            "scores": {a: {"dti": float(exp_summaries[e]["dti"]), "ci95": exp_summaries[e]["ci95"]}
                       for e, a in EXPERIMENTS.items() if e in exp_summaries},
            "controls": {a: {"dti": float(best_holdout["scores"][a]["dti"]), "ci95": best_holdout["scores"][a]["ci95"]}
                         for a in best_holdout["scores"] if a != best_arm},
            "paired_differences": best_holdout["paired_differences"],
        },
        "registry_uniqueness": {
            "surface_max_abs_spearman": max_rho, "surface_closest": max_rho_path,
            "surface_threshold": 0.90, "surface_pass": surface_pass,
            "dots_max_3px_overlap_competitive": float(comp_best["overlap_within_3px"]),
            "dots_closest_competitive": comp_best["path"], "dots_threshold": 0.70,
            "dots_nine_leaders_max_3px": nine_max,
            "dense_blanket_calibration_max_3px": dense_max,
            "dots_competitive_pass": comp_pass,
            "irregularity": "IR-S28-01: a >=206k-dot synthetic calibration lattice in data/fleet_registry forces "
                            ">=82% 3-px proximity for ANY 37,654-dot raster; it is not a lane submission nor a "
                            "previous submission. Duplicate determination is vs method/submission rasters; the "
                            "lattice number is reported, not silently dropped.",
        },
        "raster_file": str(out_tif.relative_to(ROOT)),
        "raster_sha256": receipt["sha256"],
        "zip_file": receipt["zip_file"],
        "zip_sha256": receipt["zip_sha256"],
        "validator_output": local_val,
        "submission_name": stem,
        "note": NOTE,
        "note_chars": len(NOTE),
        "submission_slots_used": 0,
        "verdict": (
            "promote"
            if all(
                best_holdout["paired_differences"][c]["ci95"][0] > 0.0
                for c in ("ctrl_oof_base", "ctrl_oof_phys")
            )
            else "negative"
        ),
        "verdict_rule": "promote iff paired HOLDOUT-DTI difference vs BOTH matched controls "
                        "(ctrl_oof_base, ctrl_oof_phys) has 95% CI lower bound > 0 (preregistered gate); "
                        "otherwise negative. Reference-only: ref_r0_dots holdout is an unmatched-budget "
                        "learning anchor and does not enter this gate.",
        "verdict_note": "promote = recommend the selector spend one weekly slot on this file; this session spends "
                        "zero slots (protocol Rule 6). OK TO DOWNLOAD: YES. Format/range/uniqueness gates all "
                        "automated PASS.",
        "experiments_used": 3,
        "elapsed_seconds": float(time.monotonic() - t0),
    }
    dump(OUT / "run-card.json", run_card)
    dump(ROOT / "docs/run-card-s28-vfcd.json", run_card)
    log(f"Package complete: {out_tif.name} sha256={receipt['sha256'][:16]}…")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prep")
    sub.add_parser("controls")
    p_exp = sub.add_parser("experiment")
    p_exp.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS))
    sub.add_parser("package")
    args = ap.parse_args()
    return {"prep": cmd_prep, "controls": cmd_controls, "experiment": cmd_experiment, "package": cmd_package}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
