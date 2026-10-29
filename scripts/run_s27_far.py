#!/usr/bin/env python3
"""S27-FABRIC-FAR lane runner (docs/s27/preregistration.md).

Subcommands:
  features    freeze registry, verify pinned inputs, rebuild the frozen S25
              37-feature stack (shared gems91.fabric25), leakage canaries.
  experiment  retrain the S25 fabric_e2 OOF surface identically; score three
              emission arms paired on the shared v3 folds/evaluator:
              ctrl_collar3 (matched incumbent), e1_collar10, e2_stratified.
  package     final full-footprint surface, Rule-1 surface check,
              stratified + uniqueness-capped 37,654-dot emission, Rule-1 dot
              checks, shared writer, full run card.

Shared template only: vendor/gems57 spatial folds + evaluate_holdout +
submission_writer + validate; gems91.novelty instruments; gems91.capacity.
Refuses implicit reruns. No submission slot is used or approved here.
The detector recipe is frozen from S25; only emission geometry changes.
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

from gems91 import fabric25, far27
from gems91.capacity import capacity_bound
from gems91.io import dot_digest
from gems91.novelty import SurfaceProbe, dot_check
from gems91.pdwc21 import emit_dots_nms
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s27"
WORK = ROOT / "work/s27"
FEAT = WORK / "features"
OOFD = WORK / "oof"
BUDGET = 37_654
SPACING_PX = 3.05
COLLAR_PX = 3.05
SEED = 520810  # identical to S25: the detector is a reproduction
HGB_PARAMS = dict(max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
                  min_samples_leaf=40, l2_regularization=1.0, early_stopping=False)
NEG_PER_POS = 4
ARMS = ["ctrl_collar3", "e1_collar10", "e2_stratified"]
CANDIDATE_ARM = "e2_stratified"
NOTE = "S27 FABRIC-FAR stratified+capped emission on S25 fabric surface 37654 dots; see run-card verdict"
assert len(NOTE) <= 140, len(NOTE)

# Cap references frozen in docs/s27/preregistration.md from prior receipts.
S25_BINDING_COMPETITIVE = [
    "docs/downloads/gems91-bhar-e3-20261024T184500Z-a4b69ca7-zeros.tif",
    "docs/downloads/gems91-spac-e3-20261024T183000Z-a2740c89-zeros.tif",
    "data/fleet_registry/calib_h28ridge_01839.tif",
    "docs/downloads/gems91-cover91-e1-37654dots-20261024T194354Z-328b876d-zeros.tif",
    "docs/downloads/gems91-fuse91-e1-37654dots-20261024T184241Z-730f6bda-zeros.tif",
    "docs/downloads/gems91-spid-e3-20261024T190000Z-25a94861-zeros.tif",
    "docs/downloads/gems91-ccr91-e1-research-20261024T235900Z-53eab7eb-zeros.tif",
    "docs/downloads/gems91-mhtr-e2-20261024T170000Z-9554f718-zeros.tif",
    "docs/downloads/gems91-s14-lsrg-e3-20261024T235900Z-e6540657-zeros.tif",
    "docs/downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif",
    "docs/downloads/gems91-s14-hvdc-e2-20261024T223000Z-0a0bb0cb-zeros.tif",
    "docs/downloads/gems91-denovo-hgbctx-37654dots-s2.8-20261024-7941b7ab-zeros.tif",
    "docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif",
    "docs/downloads/gemsdoe91-cwp91-e1-completenesspu-37654-20261025-562325b2.tif",
    "docs/downloads/gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif",
    "docs/downloads/gems91-ddvtc-e1-20261024T120000Z-df50cc0c-zeros.tif",
]
S25_CANDIDATE = "docs/downloads/gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif"


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


def prereg_sha() -> str:
    return sha(OUT / "preregistration.md")


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


def freeze_references():
    """Pin every comparison raster by SHA before candidate construction."""
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


def read_reference_file(path_rel, g):
    return reference_array({"path": path_rel}, g)


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
        raise RuntimeError("S27 features already recorded; no implicit rebuild")
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    log("freezing registry references")
    freeze_references()
    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform:
            raise ValueError("feature grid mismatch")
        log("building features (frozen S25 recipe: base + OGC + CSPL)")
        groups, meta = fabric25.build_all(
            lambda i: ds.read(i), g.footprint,
            lambda name, arr: np.save(feat_path(name), arr))
    meta["inputs_verified"] = inputs
    meta["preregistration"] = {"path": "docs/s27/preregistration.md", "sha256": prereg_sha()}
    meta["detector_provenance"] = (
        "Identical rebuild of the S25-FABRIC feature stack via shared "
        "gems91.fabric25.build_all; band-identity receipt inherited from "
        "docs/s25/band-identity.json (same training_features SHA-256, "
        "re-verified above). No detector change is part of this lane.")
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
             {"schema": "gems-parallel-run-card-v1", "lane": "S27-FABRIC-FAR (self-assigned)",
              "verdict": "negative", "stop_reason": "leakage canary > 0.90",
              "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
              "leakage_canary": {"max_symmetric_auc": float(max_sym), "worst": worst}})
        return 2
    return 0


# ---------------------------------------------------------------- OOF surface
def feature_names():
    gr = json.loads((OUT / "feature-receipt.json").read_text())["groups"]
    return list(gr["base"]) + list(gr["new"])


def _gather(names, flat_idx) -> np.ndarray:
    X = np.empty((len(flat_idx), len(names)), dtype=np.float32)
    for j, n in enumerate(names):
        X[:, j] = load_feat(n).ravel()[flat_idx]
    return X


def _train_one(names, train_mask, catalogue, seed):
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


def oof_surface(g, folds) -> np.ndarray:
    OOFD.mkdir(parents=True, exist_ok=True)
    cache = OOFD / "fabric_e2_oof_full.npy"
    receipt_path = OUT / "oof-fabric_e2_oof_full.json"
    if cache.is_file() and receipt_path.is_file():
        log("OOF surface cached")
        return np.load(cache)
    names = feature_names()
    out = np.zeros(g.shape, dtype=np.float64)
    receipts = []
    for fidx, fold in enumerate(folds):
        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        model, rec = _train_one(names, fold["train"], g.catalogue, SEED)
        _predict_into(model, names, fold["region"], acc)
        receipts.append({"fold": fidx, **rec})
        del model
        log(f"  OOF fold{fidx} trained+predicted")
        out += acc.reshape(g.shape)
        del acc
    surf = np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)
    if not np.isfinite(surf).all():
        raise ValueError("non-finite OOF surface")
    np.save(cache, surf)
    dump(receipt_path, {"arm": "fabric_e2_oof_full", "features": names, "seeds": [SEED],
                        "hgb_params": HGB_PARAMS, "neg_per_pos": NEG_PER_POS,
                        "folds": receipts,
                        "scope": "identical reproduction of the S25 e2 OOF recipe"})
    return surf


def final_surface(g) -> np.ndarray:
    cache = OOFD / "final-fabric_e2_oof_full.npy"
    receipt_path = OUT / "final-model-fabric_e2_oof_full.json"
    if cache.is_file() and receipt_path.is_file():
        return np.load(cache)
    names = feature_names()
    acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
    model, rec = _train_one(names, g.footprint, g.catalogue, SEED)
    _predict_into(model, names, g.footprint, acc)
    del model
    log("  final full-footprint model trained+predicted")
    surf = np.where(g.footprint, np.clip(acc.reshape(g.shape), 0.0, 1.0), 0.0).astype(np.float32)
    del acc
    if not np.isfinite(surf).all():
        raise ValueError("non-finite final surface")
    np.save(cache, surf)
    dump(receipt_path, {"arm": "fabric_e2_oof_full", "features": names, "seeds": [SEED],
                        "hgb_params": HGB_PARAMS, "neg_per_pos": NEG_PER_POS,
                        "training": [rec],
                        "scope": "full-footprint final model (all catalogue positives)"})
    return surf


def emit_arm(arm, surf, visible, domain, budget):
    """One preregistered emission arm; returns (dots, emitter_info_or_None)."""
    if arm == "ctrl_collar3":
        return emit_dots_nms(surf, visible, domain, budget=budget,
                             collar_px=COLLAR_PX, min_spacing_px=SPACING_PX), None
    if arm == "e1_collar10":
        return emit_dots_nms(surf, visible, domain, budget=budget,
                             collar_px=10.0, min_spacing_px=SPACING_PX), None
    if arm == "e2_stratified":
        return far27.emit_dots_stratified(surf, visible, domain, budget=budget,
                                          collar_px=COLLAR_PX, min_spacing_px=SPACING_PX)
    raise ValueError(f"unknown arm {arm}")


# ---------------------------------------------------------------- experiment
def cmd_experiment(_args) -> int:
    start = time.monotonic()
    if (OUT / "holdout.json").exists():
        raise RuntimeError("S27 holdout already recorded; no implicit rerun")
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("leakage canary failed; lane stopped")
    verify_pinned_inputs()
    if prereg_sha() != json.loads((OUT / "feature-receipt.json").read_text())["preregistration"]["sha256"]:
        raise RuntimeError("preregistration changed after features; refusing to continue")
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fold_receipts = [f["receipt"] for f in folds]
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)
    surf = oof_surface(g, folds)

    WORK.mkdir(parents=True, exist_ok=True)
    terms_file = WORK / "holdout-terms.npz"
    terms_by_arm = {}
    if terms_file.is_file():
        with np.load(terms_file) as z:
            terms_by_arm = {k: z[k] for k in z.files}
    per_fold = []
    strat_fold_info = []
    for arm in ARMS:
        if arm in terms_by_arm:
            log(f"holdout terms cached: {arm}")
            continue
        total_terms = None
        for fidx, fold in enumerate(folds):
            pred, info = emit_arm(arm, surf, fold["visible"],
                                  g.footprint & fold["region"], budgets[fidx])
            if info is not None:
                strat_fold_info.append({"fold": fidx, **info})
            res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                     origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            per_fold.append({"arm": arm, "fold": fidx, "budget": budgets[fidx],
                             "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                             "tpw": float(res["tpw"]), "fpw": float(res["fpw"]),
                             "fnw": float(res["fnw"])})
            log(f"  scored {arm} fold{fidx}")
            del pred
        terms_by_arm[arm] = total_terms
        np.savez_compressed(terms_file, **terms_by_arm)
    del surf
    sub = {a: terms_by_arm[a] for a in ARMS}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=CANDIDATE_ARM)
    pooled["per_fold"] = per_fold
    pooled["stratified_fold_emission"] = strat_fold_info
    pooled["fold_receipts"] = fold_receipts
    pooled["matched_incumbent"] = "ctrl_collar3"
    pooled["budget_total"] = BUDGET
    pooled["experiments"] = {
        "e1": "e1_collar10 vs ctrl_collar3 (collar ablation)",
        "e2": "e2_stratified vs ctrl_collar3 (candidate arm)",
    }
    pooled["elapsed_seconds"] = float(time.monotonic() - start)
    dump(OUT / "holdout.json", pooled)
    for a in ARMS:
        s = pooled["scores"][a]
        log(f"{a}: HOLDOUT-DTI {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in pooled["paired_differences"]:
        d = pooled["paired_differences"][c]
        log(f"  Δ e2 vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return 0


# ---------------------------------------------------------------- package
def cap_reference_paths(nine):
    """Frozen cap list (preregistration): nine + S25-binding competitive + S25."""
    paths = [s["local_path"] for s in nine] + list(S25_BINDING_COMPETITIVE) + [S25_CANDIDATE]
    seen_sha, out = set(), []
    for rel in paths:
        p = ROOT / rel
        if not p.is_file():
            raise FileNotFoundError(f"cap reference missing: {rel}")
        h = sha(p)
        if h in seen_sha:
            continue
        seen_sha.add(h)
        out.append({"path": rel, "sha256": h, "bytes": p.stat().st_size})
    return out


def cmd_package(_args) -> int:
    start = time.monotonic()
    if (OUT / "run-card.json").exists():
        raise RuntimeError("S27 already packaged; no implicit rerun")
    can = json.loads((OUT / "canaries.json").read_text())
    pooled = json.loads((OUT / "holdout.json").read_text())
    verify_pinned_inputs()
    refs = load_frozen_references()
    nine = json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]
    g = grid.load_grid(ROOT / "data/official")

    surf = final_surface(g)

    # Cap halos are built before placement from the frozen cap list only.
    cap_refs = cap_reference_paths(nine)
    log(f"building cap halos for {len(cap_refs)} frozen references")
    supports = []
    for e in cap_refs:
        a = read_reference_file(e["path"], g)
        supports.append((a > 0) & g.footprint)
        del a
    cap_bits = far27.pack_cap_halos(supports, g.footprint)
    del supports
    cap_limit = int(np.floor(far27.CAP_FRACTION * BUDGET))
    for e, s in zip(cap_refs, range(len(cap_refs))):
        e["bit"] = int(s)
    dump(OUT / "cap-references.json",
         {"cap_fraction": far27.CAP_FRACTION, "cap_limit_dots": cap_limit,
          "budget": BUDGET, "references": cap_refs,
          "source": "frozen in docs/s27/preregistration.md from S22/S25 receipts"})

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
    paired_ctrl = pooled["paired_differences"].get("ctrl_collar3", {})
    beats_ctrl = bool(paired_ctrl.get("ci95", [0.0, 0.0])[0] > 0)
    cand_score = scores[CANDIDATE_ARM]

    if not surface_pass:
        card = {"schema": "gems-parallel-run-card-v1", "lane": "S27-FABRIC-FAR (self-assigned)",
                "verdict": "negative", "stop_reason": "surface DUPLICATE stop before placement",
                "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
                "surface_max_abs_rho": float(max_rho), "closest": max_rho_path,
                "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
                            "dti": cand_score["dti"], "ci95": cand_score["ci95"],
                            "n_withheld_positives": cand_score["withheld_positive_pixels"]}}
        dump(OUT / "run-card.json", card)
        log("STOP: surface duplicate; no TIF emitted")
        return 3

    # Final emission: E2 stratified rule + preregistered caps.
    final, emit_info = far27.emit_dots_stratified(
        surf, g.catalogue, g.footprint, budget=BUDGET,
        collar_px=COLLAR_PX, min_spacing_px=SPACING_PX,
        cap_bits=cap_bits, cap_limit=cap_limit, n_cap_refs=len(cap_refs))
    del surf, cap_bits
    emit_info["cap_reference_paths_in_bit_order"] = [e["path"] for e in cap_refs]
    dump(OUT / "final-emission.json", emit_info)
    n_final = int((final > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"final dot count {n_final} != budget {BUDGET} "
                           f"(caps/quotas infeasible; see final-emission.json)")
    log(f"final dots placed: {n_final}; band shares {emit_info['band_shares_final']}")

    # Rule 1 phase 2: final dot checks vs every frozen reference.
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
        del la, lat

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final > 0)[:8]
    tif_name = f"gems91-s27-fabricfar-{BUDGET}dots-{stamp}-{short}-zeros.tif"
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
    del disk
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
    # G5 (SGMC) is evaluated post-hoc by scripts/score_s27_diagnostics.py and
    # folded into the verdict there; the packaging card records it as pending.
    gates = {"G1_canary": canary_pass, "G2_surface": surface_pass,
             "G3_dots_nine": dots_pass_nine, "G3_dots_competitive": dots_pass_competitive,
             "G3_dots_all_incl_blankets": dots_pass_all,
             "G4_holdout_beats_ctrl_ci95": beats_ctrl, "G5_sgmc": None,
             "G6_format": validator_pass}
    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "lane": "S27-FABRIC-FAR (self-assigned; no supplied method paragraph)",
        "preregistration": {"path": "docs/s27/preregistration.md", "sha256": prereg_sha()},
        "hypothesis": ("Catalogue-missing buried faults separate different surface fabrics "
                       "and offset the gravity boundary from the magnetic boundary (S25 "
                       "detector, validated); the scored live truth lies predominantly far "
                       "from mapped traces, so the same surface emitted with preregistered "
                       "distance-stratified quotas and uniqueness caps should retain holdout "
                       "skill while fixing S25's catalogue-hugging dot geography."),
        "mechanism": ("Frozen S25 detector: 23 base band/gradient features + 8 oriented-"
                      "granulometry features (B12/B19) + 6 phase-lag features (B13/B14) -> "
                      "spatially cross-fitted HGB; emission changed only: 37,654 dots, "
                      "3.05 px spacing/collar, distance-band quotas 5/15/25/25/30% over "
                      "(3.05,5],(5,10],(10,20],(20,40],(40,inf) px, per-reference "
                      "within-3-px caps <=65% during placement."),
        "named_non_fault_mimic": ("Unfaulted dipping lithologic contacts, remanent-"
                                  "magnetization offsets, fan-lobe/shoreline fabrics, and "
                                  "GeoDAWN flight-line seams."),
        "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
                    "split_version": pooled["fold_receipts"][0]["split_version"],
                    "implementation_sha256": pooled.get("implementation_sha256"),
                    "dti": cand_score["dti"], "ci95": cand_score["ci95"],
                    "n_withheld_positives": cand_score["withheld_positive_pixels"],
                    "matched_incumbent": "ctrl_collar3",
                    "matched_incumbent_dti": scores["ctrl_collar3"]["dti"],
                    "paired_difference_vs_incumbent": paired_ctrl,
                    "beats_matched_incumbent_ci95": beats_ctrl,
                    "all_arm_scores": {a: scores[a]["dti"] for a in scores},
                    "e1_collar10_dti": scores["e1_collar10"]["dti"],
                    "cross_instrument_note": ("CTRL is the identical-recipe reproduction of "
                                              "S25 fabric_e2 on today's v3 instrument; S25 "
                                              "reported 0.147741 for the same arm.")},
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
            "lattice_capacity_bound_at_budget": capacity,
            "references_unique_bytes": refs["unique_byte_references"],
            "references_missing": refs["missing"],
            "organizer_complete_registry": False},
        "final_emission": emit_info,
        "validator_output": {"local": local_validation, "independent_reread": reread,
                             "pass": validator_pass,
                             "scope": "local [0,1]/CRS/shape/transform preflight; not organizer acceptance"},
        "raster_sha256": tif_sha,
        "submission_name": tif_name[:-4],
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "artifact": {"tif": str(out_tif.relative_to(ROOT)),
                     "zip": str(zip_path.relative_to(ROOT)),
                     "zip_sha256": writer_receipt["zip_sha256"], "n_dots": BUDGET},
        "organizer_confirmed_score": None,
        "estimated_leaderboard_score": None,
        "estimated_leaderboard_score_reason": ("No organizer receipt exists. The labelled LFI "
                                               "MODEL projection (not a score) is computed "
                                               "post-hoc in docs/s27/diagnostics.json."),
        "gates_at_packaging": gates,
        "experiments_run": 2,
        "max_experiments": 3,
        "elapsed_seconds_package": float(time.monotonic() - start),
        "submission_slots_used": 0,
        "ok_to_download": True,
        "ok_to_download_scope": "research only",
        "ok_to_submit": False,
        "selector_review_required": True,
        "verdict": "pending_diagnostics_G5",
        "inputs_verified": verify_pinned_inputs(),
    }
    dump(OUT / "run-card.json", run_card)
    log(f"packaged {tif_name} sha256 {tif_sha[:16]} gates={gates}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("features")
    sub.add_parser("experiment")
    sub.add_parser("package")
    args = ap.parse_args()
    return {"features": cmd_features, "experiment": cmd_experiment,
            "package": cmd_package}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
