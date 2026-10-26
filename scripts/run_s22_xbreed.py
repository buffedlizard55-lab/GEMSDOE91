#!/usr/bin/env python3
"""Session 22 (`S22-XB`) runner: PDWC66 x HGBR16 cross-breed under equalized quadrant budgets.

Preregistration: docs/HYPOTHESES_S22_XBREED.md (+ Amendment A1), frozen before any result.

Stages (each resumable; every expensive artefact is cached under data/derived/s22_cache/):

    fit       --arm A|B|C   4 folds x {full, pure-subsurface} specialists -> out-of-fold surfaces
    evaluate                canary + equalized-quadrant emission (NMS and CELF) + paired bootstrap
                            -> docs/s22/holdout.json, docs/s22/canary.json

Arms
    A  PDWC66 only                        (S21 feature set)
    B  HGBR16 only                        (S18 feature set; 14 subsurface-only columns for the sub-model)
    C  PDWC66 + HGBR16 (82 columns)       (the cross-breed)

All models reuse `gems91.pdwc21.fit_predict_pdwc_specialist` unchanged and the shared, unchanged evaluator
`vendor/gems57`.  The final-file stage lives in `scripts/emit_s22_xbreed.py`.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
from pathlib import Path

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from gems57 import evaluate_holdout as eh  # noqa: E402
from gems91 import xbreed22 as X  # noqa: E402
from gems91.pdwc21 import fit_predict_pdwc_specialist  # noqa: E402

EVIDENCE = ROOT / "docs/s22"


def cmd_fit(arm: str) -> int:
    footprint, catalogue, folds = X.load_common()
    cubes = X.load_cubes(footprint)
    full_blocks, sub_blocks = X.arm_blocks(arm)
    hn_full, hn_sub = X.hard_negative_indices(arm)
    t_arm = time.time()
    for q, f in enumerate(folds):
        for kind, blocks, hn, seed in (("full", full_blocks, hn_full, 2100 + 31 * q),
                                       ("sub", sub_blocks, hn_sub, 2200 + 31 * q)):
            out = X.fit_path(arm, q, kind)
            if out.is_file():
                continue
            t0 = time.time()
            pred, stats = fit_predict_pdwc_specialist(
                blocks=[(cubes[k], cols) for k, cols in blocks],
                hard_neg_cols_in_stack=hn,
                visible_faults=f["visible"],
                train_domain=f["train"],
                footprint=footprint,
                predict_mask=f["region"] & footprint,
                seed=seed,
            )
            tmp = out.with_name(out.stem + ".tmp.npy")
            np.save(tmp, pred)
            os.replace(tmp, out)
            qm = f["region"] & footprint
            print(f"[fit {arm}] fold {q} {kind}: {time.time() - t0:6.1f}s  n_pos={stats['n_pos_train']} "
                  f"n_feat={stats['n_features']}  test mean={float(pred[qm].mean()):.5f}", flush=True)
            del pred
            gc.collect()
    print(f"[fit {arm}] done in {time.time() - t_arm:.0f}s", flush=True)
    return 0


def _load_canary_helper():
    import importlib.util

    spec = importlib.util.spec_from_file_location("run_s21_pdwc_mod", ROOT / "scripts/run_s21_pdwc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cmd_evaluate(arms: list[str]) -> int:
    from gems91.hgbr18 import HGBR_FEATURE_NAMES
    from gems91.pdwc21 import PDWC21_FEATURE_NAMES

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    s21 = _load_canary_helper()
    pins = s21.verify_template_pins()
    footprint, catalogue, folds = X.load_common()
    cubes = X.load_cubes(footprint)
    split_sha = X.compute_split_sha(folds)
    n_withheld = int(sum(int(f["truth"].sum()) for f in folds))
    print(f"[S22] split_sha256={split_sha} withheld_positives={n_withheld:,}", flush=True)

    canary_path = EVIDENCE / "canary.json"
    if canary_path.is_file():
        canary = json.loads(canary_path.read_text())
    else:
        c_p = s21.run_feature_canary(X_mm=cubes["P"], feature_names=list(PDWC21_FEATURE_NAMES),
                                     folds=folds, footprint=footprint)
        c_h = s21.run_feature_canary(X_mm=cubes["H"], feature_names=list(HGBR_FEATURE_NAMES),
                                     folds=folds, footprint=footprint)
        canary = {
            "evaluator_version": eh.VERSION, "split_sha256": split_sha,
            "pdwc66": c_p, "hgbr16": c_h,
            "overall_max_symmetric_auc": max(c_p["max_symmetric_auc"], c_h["max_symmetric_auc"]),
            "overall_pass_le_090": bool(c_p["pass"] and c_h["pass"]),
        }
        canary_path.write_text(json.dumps(canary, indent=1) + "\n")
    print(f"[S22] canary: max symmetric AUC {canary['overall_max_symmetric_auc']} "
          f"pass={canary['overall_pass_le_090']}", flush=True)
    if not canary["overall_pass_le_090"]:
        raise RuntimeError("Rule-4 leakage canary failed; evaluation halted")

    cover_fp, crest_fp = X.cover_and_crest(cubes)
    terms: dict[str, np.ndarray] = {}
    per_fold: dict[str, list[dict]] = {}

    def run_arm(name, pred_fn):
        t_sum, pf = s21.evaluate_arm_terms(pred_fn, folds, footprint)
        terms[name] = t_sum
        per_fold[name] = pf
        print(f"[S22] {name:12s} HOLDOUT-DTI = {float(eh.from_terms(t_sum.sum(axis=0))):.6f}", flush=True)

    for arm in arms:
        surf_cache: dict[int, np.ndarray] = {}

        def surf(q, _arm=arm, _c=surf_cache):
            if q not in _c:
                _c.clear()
                _c[q] = X.quadrant_surface(_arm, q, footprint, cover_fp, crest_fp)
            return _c[q]

        for method in ("nms", "celf"):
            run_arm(f"{arm}_{method}",
                    lambda f, _m=method, _s=surf: X.emit_quadrant(_s(int(f["fold"])), f, footprint, int(f["fold"]), _m))
        del surf_cache
        gc.collect()

    # context arms: equalized random null, fold-honest R0 and static R0 (collar paradox, IR-S21-01)
    rng = np.random.default_rng(220)

    def null_pred(f):
        q = int(f["fold"])
        region = np.asarray(f["region"], bool) & footprint
        d_vis = ndi.distance_transform_edt(~(np.asarray(f["visible"], bool) & footprint))
        allowed = np.flatnonzero((region & (d_vis > X.COLLAR_PX)).ravel())
        pick = rng.choice(allowed, size=X.QUAD_BUDGETS[q], replace=False)
        out = np.zeros(footprint.shape, np.float32)
        out.ravel()[pick] = 1.0
        return out

    run_arm("random_null", null_pred)
    with rasterio.open(ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif") as ds:
        r0 = ds.read(1)
    r0 = np.where(np.isfinite(r0) & footprint, r0, 0.0).astype(np.float32)
    run_arm("static_R0", lambda f: r0)

    out = {
        "evaluator_version": eh.VERSION, "split_sha256": split_sha, "withheld_positive_pixels": n_withheld,
        "design": "equalized quadrant budgets 9414/9414/9413/9413 inside each test quadrant (Amendment A1)",
        "template_pins_verified": pins, "per_fold": per_fold, "pooled": {},
    }
    for cand in [n for n in terms if n.endswith(("_nms", "_celf"))]:
        out["pooled"][cand] = eh.pooled_summary(terms, draws=1000, seed=520810, candidate=cand)
    # compact decision table
    table = {}
    for name in terms:
        s = out["pooled"][next(iter(out["pooled"]))]["scores"][name]
        table[name] = {"dti": round(s["dti"], 6), "ci95": [round(x, 6) for x in s["ci95"]]}
    out["scores"] = table
    diffs = {}
    for method in ("nms", "celf"):
        for lhs, rhs in (("C", "A"), ("C", "B"), ("B", "A")):
            if f"{lhs}_{method}" in out["pooled"] and f"{rhs}_{method}" in terms:
                d = out["pooled"][f"{lhs}_{method}"]["paired_differences"][f"{rhs}_{method}"]
                diffs[f"{lhs}_minus_{rhs}_{method}"] = {"delta": round(d["delta"], 6),
                                                        "ci95": [round(x, 6) for x in d["ci95"]]}
    out["paired_differences"] = diffs
    (EVIDENCE / "holdout.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"scores": table, "paired": diffs}, indent=1), flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["fit", "evaluate"])
    ap.add_argument("--arm", choices=list(X.ARM_NAMES), default="A")
    ap.add_argument("--arms", default="A,B,C", help="comma-separated arms for `evaluate`")
    args = ap.parse_args()
    if args.stage == "fit":
        return cmd_fit(args.arm)
    return cmd_evaluate([a for a in args.arms.split(",") if a])


if __name__ == "__main__":
    raise SystemExit(main())
