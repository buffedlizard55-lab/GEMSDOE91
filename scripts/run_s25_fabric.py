#!/usr/bin/env python3
"""S25-FABRIC lane runner (docs/s25/preregistration.md).

Subcommands:
  features    freeze registry, verify pinned inputs, build+cached features,
              band-identity checks, Rule-4 leakage canaries.
  experiment  --exp e1|e2|e3 : spatially cross-fitted OOF arms + static
              controls scored paired on vendor/gems57 v3 folds.
  package     --arm ARM --exp eX : final full-footprint model, Rule-1 surface
              check, 37,654-dot emission, Rule-1 dot checks, shared writer,
              full run card.

Shared template only: vendor/gems57 spatial folds + evaluate_holdout +
submission_writer + validate; gems91.novelty duplicate instruments;
gems91.pdwc21 emitter; gems91.capacity bound. Refuses implicit reruns.
No submission slot is used or approved here.
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
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from gems91 import fabric25
from gems91.capacity import capacity_bound
from gems91.io import dot_digest
from gems91.novelty import SurfaceProbe, dot_check
from gems91.pdwc21 import emit_dots_nms
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s25"
WORK = ROOT / "work/s25"
FEAT = WORK / "features"
OOFD = WORK / "oof"
BUDGET = 37_654
SPACING_PX = 3.05
COLLAR_PX = 3.05
SEED = 520810
HGB_PARAMS = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                  min_samples_leaf=40, l2_regularization=1.0, early_stopping=False)
NEG_PER_POS = 4
NOTE = "S25 FABRIC granulometry+phase-lag spatial OOF 37654 dots; see run-card verdict before slot use"
assert len(NOTE) <= 140, len(NOTE)

CONTROLS = ["control_oof_base", "control_new_surface", "control_gravgrad"]
EXPERIMENTS = {
    "e1": "fabric_e1_oof_new",
    "e2": "fabric_e2_oof_full",
    "e3": "fabric_e3_oof_bagged",
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


def verify_pinned_inputs():
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        if row["id"] in {"sample_submission", "existing_faults", "training_features",
                         "parent_r0_zeros", "sgmc_faults_control"}:
            p = ROOT / "data" / row["local_subpath"]
            if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
                raise ValueError(f"pinned input absent or drifted: {row['id']}")
            checked[row["id"]] = {"path": "data/" + row["local_subpath"],
                                  "sha256": row["sha256"], "bytes": row["bytes"]}
    return checked


def freeze_references(g):
    """Pin every comparison raster by SHA *before* candidate construction."""
    entries, missing = {}, []

    def add(path_rel, expected_sha, expected_bytes, tag, site=None):
        p = ROOT / path_rel
        if not p.is_file():
            missing.append({"path": path_rel, "tag": tag})
            return
        got = sha(p)
        if expected_sha is not None and (got != expected_sha or p.stat().st_size != expected_bytes):
            raise ValueError(f"registry bytes drift: {path_rel}")
        e = entries.setdefault(got, {"path": path_rel, "sha256": got,
                                      "bytes": p.stat().st_size, "tags": [], "sites": []})
        if tag not in e["tags"]:
            e["tags"].append(tag)
        if site and site not in e["sites"]:
            e["sites"].append(site)

    inv = json.loads((ROOT / "registry/comparison_inventory.json").read_text())["files"]
    for r in inv:
        add(r["path"], r["sha256"], r["bytes"], "frozen_registry")
    nine = json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]
    for s in nine:
        add(s["local_path"], s["sha256"], s["bytes"], "nine_leader", site=s["site"])
    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        add(str(p.relative_to(ROOT)), None, None, "prior_download")
    refs = sorted(entries.values(), key=lambda e: e["path"])
    for e in refs:
        e["is_dense_lattice_name"] = "lattice" in Path(e["path"]).name.lower()
    result = {"frozen_before_candidate": True, "unique_byte_references": len(refs),
              "missing": missing, "organizer_complete_registry": False,
              "dense_reference_exemptions_in_data": False, "files": refs}
    dump(OUT / "frozen-registry.json", result)
    return result, nine


def load_frozen_references():
    result = json.loads((OUT / "frozen-registry.json").read_text())
    for e in result["files"]:
        p = ROOT / e["path"]
        if not p.is_file() or sha(p) != e["sha256"]:
            raise ValueError(f"frozen reference drifted since freeze: {e['path']}")
    return result


def reference_array(entry, g):
    with rasterio.open(ROOT / entry["path"]) as ds:
        if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform or ds.count != 1:
            raise ValueError("grid mismatch")
        a = ds.read(1)
    if not np.isfinite(a[g.footprint]).all():
        raise ValueError("non-finite inside footprint")
    if (a[g.footprint] < 0).any() or (a[g.footprint] > 1).any():
        raise ValueError("values outside [0,1] inside footprint")
    return np.where(g.footprint, a, 0).astype(np.float32)


def band_identity(ds, fp):
    """Label-blind internal consistency of derivative band claims."""
    def valid(a):
        return fp & np.isfinite(a) & (np.abs(a.astype(np.float64)) < 1e30)

    def grad_corr(field, deriv, mode):
        v = valid(field) & valid(deriv)
        ve = ndi.binary_erosion(v, iterations=2)
        f = np.where(v, np.asarray(field, np.float64), 0.0)
        gy, gx = np.gradient(f)
        if mode == "mag":
            gg = np.hypot(gy, gx)
            return float(np.corrcoef(np.abs(np.asarray(deriv, np.float64)[ve]), gg[ve])[0, 1]), int(ve.sum())
        return float(np.corrcoef(np.asarray(deriv, np.float64)[ve], gx[ve])[0, 1]), int(ve.sum())

    report = {"descriptions": {str(i): ds.descriptions[i - 1] for i in range(1, 20)},
              "nodata_tag": repr(ds.nodata)}
    pairs = [("corr_B03_vs_abs_grad_B14", 14, 3, "mag"),
             ("corr_B05_vs_abs_grad_B13", 13, 5, "mag"),
             ("corr_B18_vs_dx_B13", 13, 18, "gx"),
             ("corr_B19_vs_abs_grad_B12", 12, 19, "mag")]
    cache = {}
    for name, fband, dband, mode in pairs:
        for b in (fband, dband):
            cache.setdefault(b, ds.read(b))
        r, n = grad_corr(cache[fband], cache[dband], mode)
        report[name] = {"r": r, "n": n}
    for b in (12, 13, 14, 19):
        v = valid(cache[b])
        av = np.asarray(cache[b], np.float64)[v]
        report[f"B{b}"] = {"valid_pixels": int(v.sum()),
                            "invalid_inside_footprint": int((fp & ~v).sum()),
                            "min": float(av.min()), "median": float(np.median(av)),
                            "max": float(av.max())}
    report["interpretation"] = ("Internal derivative consistency supports, but does not "
                                "externally authenticate, the embedded band identities. "
                                "Gradients scored only on pixels eroded 2 px from any invalid "
                                "cell; no filling was used in features.")
    dump(OUT / "band-identity.json", report)
    return report


def allocate(total_budget, areas):
    budgets, remaining = [], total_budget
    for i, a in enumerate(areas):
        q = int(round(total_budget * a / sum(areas))) if i < len(areas) - 1 else remaining
        budgets.append(q)
        remaining -= q
    return budgets


# ---------------------------------------------------------------- features
def feat_path(name: str) -> Path:
    return FEAT / f"{name}.npy"


def load_feat(name: str, mmap: bool = True) -> np.ndarray:
    return np.load(feat_path(name), mmap_mode="r" if mmap else None)


def cmd_features(_args) -> int:
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    FEAT.mkdir(parents=True, exist_ok=True)
    if (OUT / "feature-receipt.json").exists():
        raise RuntimeError("S25 features already recorded; no implicit rebuild")
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    log("freezing registry references")
    freeze_references(g)
    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform:
            raise ValueError("feature grid mismatch")
        band_identity(ds, g.footprint)
        log("building features (base + OGC + CSPL)")
        groups, meta = fabric25.build_all(
            lambda i: ds.read(i), g.footprint,
            lambda name, arr: np.save(feat_path(name), arr))
    meta["inputs_verified"] = inputs
    meta["preregistration"] = {"path": "docs/s25/preregistration.md",
                                "sha256": sha(ROOT / "docs/s25/preregistration.md")}
    dump(OUT / "feature-receipt.json", meta)
    log(f"features done in {time.monotonic()-start:.0f}s; running leakage canaries")

    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    canaries, max_sym, worst = [], 0.0, None
    names = groups["base"] + groups["new"] + groups["surfaces"]
    for name in names:
        arr = load_feat(name)
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
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
        del arr
    canary_pass = bool(max_sym <= 0.90)
    dump(OUT / "canaries.json", {"max_symmetric_auc": float(max_sym), "worst": worst,
                                 "all_pass": canary_pass, "threshold": 0.90,
                                 "evaluator_version": EH.VERSION,
                                 "split_version": folds[0]["receipt"]["split_version"],
                                 "canaries": canaries})
    log(f"canaries: max symmetric AUC {max_sym:.4f} ({worst}) pass={canary_pass}")
    if not canary_pass:
        dump(OUT / "run-card.json",
             {"schema": "gems-parallel-run-card-v1", "lane": "S25-FABRIC (self-assigned)",
              "verdict": "negative", "stop_reason": "leakage canary > 0.90",
              "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
              "leakage_canary": {"max_symmetric_auc": float(max_sym), "worst": worst}})
        return 2
    return 0


# ---------------------------------------------------------------- OOF arms
def groups() -> dict:
    return json.loads((OUT / "feature-receipt.json").read_text())["groups"]


def arm_spec(arm: str):
    gr = groups()
    if arm == "fabric_e1_oof_new":
        return ("oof", list(gr["new"]), (SEED,))
    if arm == "control_oof_base":
        return ("oof", list(gr["base"]), (SEED,))
    if arm == "fabric_e2_oof_full":
        return ("oof", list(gr["base"]) + list(gr["new"]), (SEED,))
    if arm == "fabric_e3_oof_bagged":
        return ("oof", list(gr["base"]) + list(gr["new"]), (SEED, SEED + 1, SEED + 2))
    if arm == "control_new_surface":
        return ("static", "surface_new_standalone", None)
    if arm == "control_gravgrad":
        return ("static", "surface_gravgrad", None)
    raise ValueError(f"unknown arm {arm}")


def _gather(names, flat_idx) -> np.ndarray:
    X = np.empty((len(flat_idx), len(names)), dtype=np.float32)
    for j, n in enumerate(names):
        X[:, j] = load_feat(n).ravel()[flat_idx]
    return X


def _train_one(names, shape, train_mask, catalogue, seed):
    flat_cat = catalogue.ravel()
    flat_train = train_mask.ravel()
    pos = np.flatnonzero(flat_train & flat_cat)
    pool = np.flatnonzero(flat_train & ~flat_cat)
    rng = np.random.default_rng(seed)
    neg = rng.choice(pool, size=min(NEG_PER_POS * len(pos), len(pool)), replace=False)
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
    X = _gather(names, idx)
    model = HistGradientBoostingClassifier(random_state=seed, **HGB_PARAMS)
    model.fit(X, y)
    return model, {"n_positive": int(len(pos)), "n_negative": int(len(neg)), "seed": int(seed)}


def _predict_into(model, names, pred_mask, out_flat):
    idx = np.flatnonzero(pred_mask.ravel())
    for lo in range(0, len(idx), 250_000):
        chunk = idx[lo: lo + 250_000]
        out_flat[chunk] += model.predict_proba(_gather(names, chunk))[:, 1].astype(np.float64)
    return out_flat


def oof_surface(arm: str, g, folds) -> np.ndarray:
    OOFD.mkdir(parents=True, exist_ok=True)
    cache = OOFD / f"{arm}.npy"
    receipt_path = OUT / f"oof-{arm}.json"
    if cache.is_file() and receipt_path.is_file():
        log(f"OOF surface cached: {arm}")
        return np.load(cache)
    kind, names, seeds = arm_spec(arm)
    assert kind == "oof"
    out = np.zeros(g.shape, dtype=np.float64)
    receipts = []
    for fidx, fold in enumerate(folds):
        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        for seed in seeds:
            model, rec = _train_one(names, g.shape, fold["train"], g.catalogue, seed)
            _predict_into(model, names, fold["region"], acc)
            receipts.append({"fold": fidx, **rec})
            del model
            log(f"  {arm} fold{fidx} seed{seed} trained+predicted")
        out += (acc / len(seeds)).reshape(g.shape)
        del acc
    surf = np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)
    if not np.isfinite(surf).all():
        raise ValueError("non-finite OOF surface")
    np.save(cache, surf)
    dump(receipt_path, {"arm": arm, "features": names, "seeds": list(seeds),
                        "hgb_params": HGB_PARAMS, "neg_per_pos": NEG_PER_POS,
                        "folds": receipts})
    return surf


def final_surface(arm: str, g) -> np.ndarray:
    kind, names, seeds = arm_spec(arm)
    assert kind == "oof"
    cache = OOFD / f"final-{arm}.npy"
    receipt_path = OUT / f"final-model-{arm}.json"
    if cache.is_file() and receipt_path.is_file():
        return np.load(cache)
    acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
    receipts = []
    for seed in seeds:
        model, rec = _train_one(names, g.shape, g.footprint, g.catalogue, seed)
        _predict_into(model, names, g.footprint, acc)
        receipts.append(rec)
        del model
        log(f"  final {arm} seed{seed} trained+predicted")
    surf = np.where(g.footprint, np.clip((acc / len(seeds)).reshape(g.shape), 0.0, 1.0),
                    0.0).astype(np.float32)
    del acc
    if not np.isfinite(surf).all():
        raise ValueError("non-finite final surface")
    np.save(cache, surf)
    dump(receipt_path, {"arm": arm, "features": names, "seeds": list(seeds),
                        "hgb_params": HGB_PARAMS, "neg_per_pos": NEG_PER_POS,
                        "training": receipts,
                        "scope": "full-footprint final model (all catalogue positives)"})
    return surf


def arm_surface(arm: str, g, folds) -> np.ndarray:
    kind, spec, _seeds = arm_spec(arm)
    if kind == "static":
        return np.asarray(load_feat(spec, mmap=False), dtype=np.float32)
    return oof_surface(arm, g, folds)


# ---------------------------------------------------------------- experiment
def cmd_experiment(args) -> int:
    start = time.monotonic()
    exp = args.exp
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").exists():
        raise RuntimeError(f"{exp} already recorded; no implicit rerun")
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("leakage canary failed; lane stopped")
    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fold_receipts = [f["receipt"] for f in folds]
    cand = EXPERIMENTS[exp]
    arms = [cand] + CONTROLS
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)

    WORK.mkdir(parents=True, exist_ok=True)
    terms_file = WORK / "holdout-terms.npz"
    terms_by_arm = {}
    if terms_file.is_file():
        with np.load(terms_file) as z:
            terms_by_arm = {k: z[k] for k in z.files}
    per_fold = []
    for arm in arms:
        if arm in terms_by_arm:
            log(f"holdout terms cached: {arm}")
            continue
        surf = arm_surface(arm, g, folds)
        total_terms = None
        for fidx, fold in enumerate(folds):
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
        del surf
    sub = {a: terms_by_arm[a] for a in arms}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=cand)
    pooled["per_fold"] = per_fold
    pooled["fold_receipts"] = fold_receipts
    pooled["matched_controls"] = CONTROLS
    pooled["budget_total"] = BUDGET
    pooled["elapsed_seconds"] = float(time.monotonic() - start)
    dump(outdir / "holdout.json", pooled)
    for a in arms:
        s = pooled["scores"][a]
        log(f"{a}: HOLDOUT-DTI {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in CONTROLS:
        d = pooled["paired_differences"][c]
        log(f"  Δ vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return 0


# ---------------------------------------------------------------- package
def cmd_package(args) -> int:
    start = time.monotonic()
    arm, exp = args.arm, args.exp
    if EXPERIMENTS.get(exp) != arm:
        raise ValueError(f"arm {arm} is not the preregistered candidate of {exp}")
    if (OUT / "run-card.json").exists():
        raise RuntimeError("run card already recorded; no implicit rerun")
    pooled = json.loads((OUT / exp / "holdout.json").read_text())
    can = json.loads((OUT / "canaries.json").read_text())
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    refs = load_frozen_references()
    log(f"packaging {arm}: training final full-footprint model")
    surf = final_surface(arm, g)

    # Rule 1 phase 1: surface rank correlation before placement.
    probe = SurfaceProbe(surf, g.footprint)
    surface_checks, max_rho, max_rho_path = [], 0.0, None
    for entry in refs["files"]:
        row = {"path": entry["path"], "tags": entry["tags"], "sites": entry["sites"]}
        try:
            res = probe.compare(reference_array(entry, g))
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

    scores = pooled["scores"]
    best_control = max(CONTROLS, key=lambda k: scores[k]["dti"])
    paired = pooled["paired_differences"].get(best_control, {})
    beats_control = bool(paired.get("ci95", [0.0, 0.0])[0] > 0)
    cand_score = scores[arm]

    if not surface_pass:
        card = {"schema": "gems-parallel-run-card-v1", "lane": "S25-FABRIC (self-assigned)",
                "verdict": "negative", "stop_reason": "surface DUPLICATE stop before placement",
                "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
                "surface_max_abs_rho": float(max_rho), "closest": max_rho_path,
                "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
                            "dti": cand_score["dti"], "ci95": cand_score["ci95"],
                            "n_withheld_positives": cand_score["withheld_positive_pixels"]}}
        dump(OUT / "run-card.json", card)
        log("STOP: surface duplicate; no TIF emitted")
        return 3

    # Final emission + Rule 1 phase 2.
    final = emit_dots_nms(surf, g.catalogue, g.footprint, budget=BUDGET,
                          collar_px=COLLAR_PX, min_spacing_px=SPACING_PX)
    del surf
    n_final = int((final > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"final dot count {n_final} != budget {BUDGET}")
    dot_checks, max_ov, max_ov_path = [], 0.0, None
    for entry in refs["files"]:
        row = {"path": entry["path"], "tags": entry["tags"], "sites": entry["sites"],
               "is_dense_lattice_name": entry.get("is_dense_lattice_name", False)}
        try:
            ref = reference_array(entry, g)
            row["reference_positive_pixels"] = int(((ref > 0) & g.footprint).sum())
            row["is_dense_blanket"] = bool(row["reference_positive_pixels"] > 90_000
                                           or row["is_dense_lattice_name"])
            res = dot_check(final, ref, g.footprint)
            del ref
            row.update({k: (float(v) if isinstance(v, float) else v) for k, v in res.items()})
            ov = res.get("overlap_within_3px")
            if ov is not None and ov > max_ov:
                max_ov, max_ov_path = float(ov), entry["path"]
        except Exception as exc:
            row.update({"status": "UNVERIFIED", "overlap_within_3px": None, "error": str(exc)})
        dot_checks.append(row)
    nine_checks = [r for r in dot_checks if r["sites"]]
    comp_checks = [r for r in dot_checks if r.get("overlap_within_3px") is not None
                   and not r.get("is_dense_blanket", False)]
    dense_checks = [r for r in dot_checks if r.get("is_dense_blanket")]
    nine_max = max((r["overlap_within_3px"] for r in nine_checks
                    if r.get("overlap_within_3px") is not None), default=None)
    comp_max = max((r["overlap_within_3px"] for r in comp_checks), default=None)
    comp_closest = max(comp_checks, key=lambda r: r["overlap_within_3px"])["path"] if comp_checks else None
    dump(OUT / "final-dot-checks.json",
         {"max_3px_overlap_all_references": float(max_ov), "closest_all": max_ov_path,
          "max_3px_overlap_nine_leaders": nine_max,
          "max_3px_overlap_competitive_le_90000px": comp_max, "closest_competitive": comp_closest,
          "dense_blanket_checks": dense_checks, "nine_leader_checks": nine_checks,
          "references_checked": len(dot_checks), "checks": dot_checks})
    log(f"dot checks: nine max {nine_max} | competitive max {comp_max} | all max {max_ov}")

    capacity = None
    lat_path = ROOT / "data/fleet_registry/calib_r13lattice_00904.tif"
    if lat_path.is_file():
        with rasterio.open(lat_path) as ds:
            la = ds.read(1)
            lat = np.isfinite(la) & (la > 0) & g.footprint
        capacity = capacity_bound(g.footprint, lat, BUDGET)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final > 0)[:8]
    tif_name = f"gems91-s25-fabric-{exp}-{BUDGET}dots-{stamp}-{short}-zeros.tif"
    out_tif = ROOT / "docs/downloads" / tif_name
    receipt = write_submission(out_tif, final.astype(np.float32),
                               ROOT / "data/official/sample_submission.tif", g.footprint,
                               note=NOTE, name=tif_name[:-4], catalogue=g.catalogue)
    local_validation = validate(out_tif, g.footprint, g.catalogue)
    assert_submittable(local_validation)
    with rasterio.open(out_tif) as ds:
        disk = ds.read(1)
        reread = {"crs": str(ds.crs), "shape": [ds.height, ds.width], "count": ds.count,
                  "dtype": ds.dtypes[0], "transform": list(ds.transform)[:6],
                  "nodata": ds.nodata, "nodata_is_none": ds.nodata is None}
    if not np.array_equal(disk > 0, final > 0):
        raise RuntimeError("on-disk support differs from in-memory final dots")
    reread.update({"all_finite": bool(np.isfinite(disk).all()), "min": float(disk.min()),
                   "max": float(disk.max()), "n_dots": int((disk > 0).sum()),
                   "on_catalogue": int((disk[g.catalogue] > 0).sum()),
                   "outside_footprint_positive": int((disk[~g.footprint] > 0).sum())})
    tif_sha, zip_path = sha(out_tif), out_tif.with_suffix(".zip")
    writer_receipt = {"file": str(out_tif.relative_to(ROOT)), "sha256": tif_sha,
                      "bytes": out_tif.stat().st_size, "zip": str(zip_path.relative_to(ROOT)),
                      "zip_sha256": sha(zip_path), "support_dot_digest": dot_digest(final > 0),
                      "writer_receipt": receipt, "independent_validator": local_validation,
                      "independent_reread": reread}
    dump(OUT / "writer-receipt.json", writer_receipt)

    canary_pass = bool(can["all_pass"])
    dots_pass_all = bool(max_ov <= 0.70)
    dots_pass_nine = bool(nine_max is not None and nine_max <= 0.70)
    dots_pass_competitive = bool(comp_max is not None and comp_max <= 0.70)
    validator_pass = bool(local_validation["all_checks_passed"] and reread["all_finite"]
                          and reread["on_catalogue"] == 0
                          and reread["outside_footprint_positive"] == 0)
    promote = bool(canary_pass and surface_pass and dots_pass_all and beats_control
                   and validator_pass)
    identity = json.loads((OUT / "band-identity.json").read_text())
    experiments = {}
    for e, a in EXPERIMENTS.items():
        hp = OUT / e / "holdout.json"
        if hp.is_file():
            hh = json.loads(hp.read_text())
            experiments[e] = {"candidate_arm": a, "holdout_dti": hh["scores"][a]["dti"],
                              "ci95": hh["scores"][a]["ci95"]}
    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "lane": "S25-FABRIC (self-assigned; no supplied method paragraph)",
        "preregistration": {"path": "docs/s25/preregistration.md",
                            "sha256": sha(ROOT / "docs/s25/preregistration.md")},
        "hypothesis": ("Catalogue-missing buried faults separate different surface fabrics "
                       "and offset the gravity boundary from the magnetic boundary: oriented "
                       "granulometry spectra of detrended elevation change across the trace "
                       "and B13/B14 show a coherent local cross-spectral phase lag."),
        "mechanism": (f"{len(groups()['base'])} base band/gradient features + 8 oriented-"
                      f"granulometry features (B12/B19) + 6 phase-lag features (B13/B14) -> "
                      f"spatially cross-fitted HGB ({arm}); {BUDGET:,} dots, 3.05 px "
                      f"spacing/collar (shared NMS emitter)."),
        "named_non_fault_mimic": ("Unfaulted dipping lithologic contacts, remanent-"
                                  "magnetization offsets, fan-lobe/shoreline fabrics, and "
                                  "GeoDAWN flight-line seams."),
        "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
                    "split_version": pooled["fold_receipts"][0]["split_version"],
                    "implementation_sha256": pooled.get("implementation_sha256"),
                    "dti": cand_score["dti"], "ci95": cand_score["ci95"],
                    "n_withheld_positives": cand_score["withheld_positive_pixels"],
                    "best_matched_control": best_control,
                    "best_matched_control_dti": scores[best_control]["dti"],
                    "paired_difference_vs_best_control": paired,
                    "beats_best_matched_control_ci95": beats_control,
                    "all_arm_scores": {a: scores[a]["dti"] for a in scores},
                    "experiments_summary": experiments,
                    "cross_instrument_note": ("No earlier repo HOLDOUT-DTI is matched to the "
                                              "current v3 fold instrument (see preregistration); "
                                              "historical values are context only.")},
        "leakage_canary": {"max_symmetric_auc": can["max_symmetric_auc"],
                           "worst": can["worst"], "pass": canary_pass},
        "correlation_overlap_vs_registry": {
            "surface_max_abs_rho": float(max_rho), "surface_closest": max_rho_path,
            "surface_pass_le_0.90": surface_pass,
            "final_dot_max_overlap_all": float(max_ov), "final_dot_closest_all": max_ov_path,
            "final_dot_max_overlap_nine_leaders": nine_max,
            "final_dot_max_overlap_competitive_le_90000px": comp_max,
            "final_dot_closest_competitive": comp_closest,
            "final_dot_pass_nine_le_0.70": dots_pass_nine,
            "final_dot_pass_competitive_le_0.70": dots_pass_competitive,
            "final_dot_pass_all_incl_blankets_le_0.70": dots_pass_all,
            "dense_blankets": [{"path": r["path"],
                                "reference_positive_pixels": r.get("reference_positive_pixels"),
                                "overlap_within_3px": r.get("overlap_within_3px")}
                               for r in dense_checks],
            "lattice_capacity_bound_at_budget": capacity,
            "references_unique_bytes": len(refs["files"]),
            "references_missing": refs["missing"],
            "organizer_complete_registry": False},
        "band_identity": identity,
        "validator_output": {"local": local_validation, "independent_reread": reread,
                             "pass": validator_pass,
                             "scope": ("local [0,1]/CRS/shape/transform preflight; not "
                                       "organizer acceptance")},
        "raster_sha256": tif_sha,
        "submission_name": tif_name[:-4],
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "artifact": {"tif": str(out_tif.relative_to(ROOT)),
                     "zip": str(zip_path.relative_to(ROOT)),
                     "zip_sha256": writer_receipt["zip_sha256"], "n_dots": n_final},
        "organizer_confirmed_score": None,
        "estimated_leaderboard_score": None,
        "estimated_leaderboard_score_reason": ("No authenticated receipt exists. The labelled "
                                               "LFI MODEL projection (not a score) is computed "
                                               "post-hoc in docs/s25/diagnostics.json."),
        "post_hoc_diagnostics_file": "docs/s25/diagnostics.json",
        # Total preregistered experiments with recorded receipts (not the
        # packaged experiment's index; corrected post-hoc for the S25 card in
        # docs/s25/run-card-correction.json, whose recorded value is 2).
        "experiments_run": sum(1 for e in EXPERIMENTS
                               if (OUT / e / "holdout.json").is_file()),
        "max_experiments": 3,
        "elapsed_seconds_package": float(time.monotonic() - start),
        "submission_slots_used": 0,
        "ok_to_download": bool(validator_pass),
        "ok_to_download_scope": "research only" if validator_pass else "none",
        "ok_to_submit": bool(promote),
        "selector_review_required": True,
        "verdict": "promote" if promote else "negative",
        "inputs_verified": inputs,
    }
    dump(OUT / "run-card.json", run_card)
    dump(ROOT / "docs/run-card-S25-FABRIC.json", run_card)
    log(f"verdict={run_card['verdict']} ok_to_submit={run_card['ok_to_submit']} "
        f"tif={tif_name} sha={tif_sha[:16]}")
    print(json.dumps({k: run_card[k] for k in ("verdict", "ok_to_download", "ok_to_submit",
                                               "raster_sha256", "artifact")}, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("features")
    pe = sub.add_parser("experiment")
    pe.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS))
    pp = sub.add_parser("package")
    pp.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS))
    pp.add_argument("--arm", required=True)
    args = ap.parse_args()
    if args.cmd == "features":
        return cmd_features(args)
    if args.cmd == "experiment":
        return cmd_experiment(args)
    return cmd_package(args)


if __name__ == "__main__":
    raise SystemExit(main())
