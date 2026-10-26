#!/usr/bin/env python3
"""E2 — instrument validity + leakage canaries on the shared hide-and-recover evaluator.

Scores every anchor raster (fixed, as published) and the LFI candidate on `gems57-pooled-hide-v2`
(vendor/gems57/spatial.folds buffer 80 px + evaluate_holdout.evaluate, unchanged), then reports the
Spearman correlation between hide-v2 HOLDOUT-DTI and the USER-REPORTED live score across anchors.
Also runs the protocol-rule-4 single-feature canaries for the six LFI factors.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr, pearsonr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]
from vendor.gems57 import evaluate_holdout as EH, spatial  # noqa: E402
import run_lfi as R  # noqa: E402

WORK = ROOT / "work/lfi"
OUT = ROOT / "docs/lfi"
R0 = ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fp, cat, net = R.base()
    folds = list(spatial.folds(cat, fp, buffer_px=80))
    split_sha = hashlib.sha256(b"".join(np.packbits(f[k].ravel()).tobytes() for f in folds
                                        for k in ("region", "truth", "train", "visible"))).hexdigest()
    n_truth = int(sum(f["truth"].sum() for f in folds))
    print(f"split_sha256={split_sha} withheld positives={n_truth}")

    def score(p):
        terms = None
        for f in folds:
            _, t = EH.evaluate(p, f, fp)
            terms = t if terms is None else terms + t
        return terms

    meta = json.loads((WORK / "anchors.json").read_text())
    used = [r for r in meta["rows"] if r["used"]]
    rows, terms_by = [], {}
    cand = np.load(WORK / "cand_dots.npy").astype(np.float32)
    r0, _ = R.read_pred(R0, fp)
    terms_by["lfi_candidate"] = score(cand)
    terms_by["r0_gemsdoe32"] = score(r0)
    seen = {}
    reuse = None
    if "--reuse-anchors" in sys.argv:
        prev = json.loads((OUT / "pass1-holdout-e2.json").read_text())
        assert prev["split_sha256"] == split_sha and prev["evaluator_version"] == EH.VERSION
        reuse = {(a["site"], a["name"]): a for a in prev["anchors"]}
    for r in used:
        if reuse is not None:
            rows.append(dict(reuse[(r["site"], r["name"])]))
            continue
        key = r["sha256"]
        if key not in seen:
            p, _ = R.read_pred(ROOT / r["local"], fp)
            seen[key] = score(p)
        t = seen[key].sum(axis=0)
        rows.append(dict(site=r["site"], name=r["name"], live=r["score"], hide_v2=float(EH.from_terms(t))))
        print(f"live {r['score']:.4f} hide-v2 {rows[-1]['hide_v2']:.4f} {r['name'][:60]}", flush=True)
    live = np.array([x["live"] for x in rows]); hv = np.array([x["hide_v2"] for x in rows])
    summ = EH.pooled_summary(terms_by, draws=1000, seed=520810, candidate="lfi_candidate")
    lfi_fit = json.loads((WORK / "fit_r10.0_fNone.json").read_text())
    loso = {(a["site"], a["name"]): a["loso"] for a in lfi_fit["anchors"]}
    lo = np.array([loso[(x["site"], x["name"])] for x in rows])

    # protocol rule 4 canaries: each LFI factor alone vs hide-v2 withheld truth (all folds pooled)
    bins = np.load(WORK / "bins.npy")
    shapes = [6 if False else None]
    names = [n for n in ("dcat", "dnet", "det_elev_slope", "depth_to_base", "det_elev", "geod_2ndinv", "cons")]
    levels = [9, 6, 3, 3, 3, 3, 4]
    idx = np.array(np.unravel_index(np.maximum(bins, 0), levels))  # factors x H x W
    canaries = {}
    for j, nm in enumerate(names):
        y_all, s_all = [], []
        for f in folds:
            dom = f["region"] & ~f["visible"]
            code = idx[j][dom].astype(float)
            if nm == "dcat":
                # recompute distance from VISIBLE faults only (rule 2) for the canary
                from gems91 import lfi as L
                code = np.digitize(L.dist_px(f["visible"]), L.DCAT_EDGES)[dom].astype(float)
            y_all.append(f["truth"][dom]); s_all.append(code)
        y = np.concatenate(y_all); s = np.concatenate(s_all)
        auc = float(roc_auc_score(y, s))
        canaries[nm] = dict(auc=auc, symmetric_auc=max(auc, 1 - auc))
    out = dict(
        evaluator_version=EH.VERSION, split_sha256=split_sha, withheld_positives=n_truth,
        instrument_validity=dict(
            n_anchors=len(rows),
            spearman_hide_v2_vs_live=float(spearmanr(hv, live).statistic),
            pearson_hide_v2_vs_live=float(pearsonr(hv, live).statistic),
            spearman_lfi_loso_vs_live=float(spearmanr(lo, live).statistic),
            pearson_lfi_loso_vs_live=float(pearsonr(lo, live).statistic)),
        candidate_vs_r0=summ, canaries=canaries,
        canary_pass=all(v["symmetric_auc"] <= 0.90 for v in canaries.values()),
        anchors=rows)
    (OUT / "holdout-e2.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("anchors", "candidate_vs_r0")}, indent=1))
    for k in ("lfi_candidate", "r0_gemsdoe32"):
        print(k, summ["scores"][k])
    print("paired", summ["paired_differences"])


if __name__ == "__main__":
    main()
