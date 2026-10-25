#!/usr/bin/env python3
"""CWP91 lane runner: completeness-weighted PU (Elkan-Noto spatial label frequency).

Preregistration: docs/HYPOTHESES_CWP91.md (frozen before any CWP91 scoring).

Subcommands
-----------
holdout --seed S   E0 / E1 / CTL / RND on vendor gems57 buffered_component_draw
                   (LOQO models), leakage canary (input features + chat), pooled
                   paired bootstrap -> docs/cwp91/holdout-seedS.json
final              LOQO-stitched phat_vis + full-catalogue posterior, E1 surface,
                   registry surface check (pre-placement), 37,654-dot emission,
                   registry dot check (post-placement), fail-closed vendor writer,
                   independent validation -> docs/cwp91/, docs/downloads/

Reuse (Parallel-Run Protocol Rule 2): the cached 19-band + gradient feature stack,
LOQO PU-HGB recipe, submodular emitter and registry checker are imported from
scripts/run_olc91.py unchanged; the evaluator / split / writer / validator are the
pinned vendor/gems57 template. The only new science code is src/gems91/cwp.py.

Every holdout number is HOLDOUT-DTI (evaluator gems57-pooled-hide-v2). Nothing
here is a leaderboard score; live scores exist only as organizer receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as H  # noqa: E402
from gems57 import metric as M  # noqa: E402
import run_olc91 as OLC  # noqa: E402  (shared stack/recipe/emitter/registry)
from gems91 import cwp as CWP  # noqa: E402

LANE = "CWP91"
WORK = ROOT / "work" / "cwp91"
OUT = ROOT / "docs" / "cwp91"
DOWNLOADS = ROOT / "docs" / "downloads"
SAMPLE = ROOT / "data" / "official" / "sample_submission.tif"

BUDGET = OLC.BUDGET              # 37,654 (R0 dot count)
COLLAR_PX = OLC.COLLAR_PX        # 2.0 px (R0 natural experiment)
TRAIN_BUFFER_PX = OLC.TRAIN_BUFFER_PX  # 40 px LOQO buffer
PREDICT_DILATE_PX = 32           # > 3*sigma Gaussian support (frozen addendum)
ARMS = ("E0", "E1", "CTL", "RND")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# --------------------------------------------------------------------------- holdout
def run_holdout(seed: int):
    t0 = time.time()
    g = G.load_grid(ROOT / "data" / "official")
    fp = g.footprint
    X, names = OLC.build_features(fp)
    fpi = OLC.fp_index_grid(fp)
    folds, quad = H.buffered_component_draw(g, seed=seed, hide_frac=0.20, buffer_px=3)
    n_fp = int(fp.sum())
    terms = {a: None for a in ARMS}
    per_fold, strata = [], {a: {} for a in ARMS}
    canary_truth, canary_unl = [], []
    chat_truth, chat_unl = [], []
    for f in folds:
        k, region = f["fold"], f["region"]
        known = f["masked_known"]
        visible = f["visible"]
        dist_q = ndi.distance_transform_edt(quad != k)
        train_dom = fp & (dist_q > TRAIN_BUFFER_PX)
        predict_mask = fp & (ndi.distance_transform_edt(~region) <= PREDICT_DILATE_PX)
        p, info = OLC.fit_predict(X, fpi, fp, visible, train_dom, predict_mask,
                                  seed * 100 + k)
        calib = region & fp
        s1, chat, diag1 = CWP.cwp_surface(p, visible, fp, calibration_mask=calib)
        s_ctl, chat_ctl, diagc = CWP.ctl_surface(p, visible, fp, calibration_mask=calib)
        elig = region & fp & ~known & (ndi.distance_transform_edt(~known) > COLLAR_PX)
        n = int(round(BUDGET * float((region & fp).sum()) / n_fp))
        preds = dict(E0=OLC.emit(p, elig, n), E1=OLC.emit(s1, elig, n),
                     CTL=OLC.emit(s_ctl, elig, n),
                     RND=OLC.random_dots(elig, n, seed * 7 + k))
        dvis = ndi.distance_transform_edt(~visible)
        active = fp & region & ~known
        truth = active & f["truth"]
        row = dict(fold=f["name"], n_dots=n,
                   withheld_positive_pixels=int(truth.sum()), **info,
                   cwp=diag1, ctl=diagc, receipt=f["receipt"])
        for a in ARMS:
            res, tm = EH.evaluate(preds[a], f, fp)
            terms[a] = tm if terms[a] is None else terms[a] + tm
            row[f"{a}_dti"] = round(float(res["dti"]), 6)
            row[f"{a}_n_emitted"] = int(res["n_emitted"])
            covers, _, _ = M.max_cover(np.where(active, preds[a], 0).astype(np.float64),
                                       truth)
            ty, tx = np.nonzero(truth)
            dv = dvis[ty, tx]
            for lo, hi, lab in ((3, 10, "4-10px"), (10, 30, "10-30px"),
                                (30, 1e9, ">30px")):
                m = (dv > lo) & (dv <= hi)
                st = strata[a].setdefault(lab, [0.0, 0])
                st[0] += float(covers[m].sum())
                st[1] += int(m.sum())
        per_fold.append(row)
        canary_truth.append(fpi[truth])
        canary_unl.append(fpi[active & ~truth])
        chat_truth.append(chat[truth].astype(np.float64))
        chat_unl.append(chat[active & ~truth].astype(np.float64))
        log(f"fold {f['name']}: " + " ".join(f"{a}={row[f'{a}_dti']:.4f}" for a in ARMS)
            + f" c_bar={diag1['c_bar']}")
        del p, s1, s_ctl, chat, chat_ctl, preds
    summary = EH.pooled_summary(terms, candidate="E1")
    # ---- leakage canary: every input feature alone + chat / (1-chat)
    rng = np.random.default_rng(seed)
    tr_ids = np.concatenate(canary_truth)
    un_ids_all = np.concatenate(canary_unl)
    un_ids = np.sort(rng.choice(un_ids_all, min(un_ids_all.size, 300_000),
                                 replace=False))
    ids = np.concatenate([tr_ids, un_ids])
    order = np.argsort(ids)
    yy = np.r_[np.ones(tr_ids.size), np.zeros(un_ids.size)][order]
    Xc = np.asarray(X[ids[order]], np.float32)
    canary = []
    for j, nm in enumerate(names):
        auc = float(roc_auc_score(yy, Xc[:, j]))
        canary.append(dict(feature=nm, auc=round(auc, 4),
                           symmetric_auc=round(max(auc, 1 - auc), 4)))
    del Xc
    # chat canary on the identical pooled truth/unlabelled population (full, unsampled
    # unlabelled set is ~5M values; subsample deterministically for the AUC only)
    ct = np.concatenate(chat_truth)
    cu_all = np.concatenate(chat_unl)
    cu = rng.choice(cu_all, min(cu_all.size, 300_000), replace=False)
    y2 = np.r_[np.ones(ct.size), np.zeros(cu.size)]
    for nm, vals in (("cwp_chat", np.r_[ct, cu]),
                     ("cwp_1_minus_chat", 1.0 - np.r_[ct, cu])):
        auc = float(roc_auc_score(y2, vals))
        canary.append(dict(feature=nm, auc=round(auc, 4),
                           symmetric_auc=round(max(auc, 1 - auc), 4)))
    worst = max(canary, key=lambda c: c["symmetric_auc"])
    cov = {a: {lab: dict(coverage=round(v[0] / v[1], 4) if v[1] else None, n_truth=v[1])
               for lab, v in strata[a].items()} for a in ARMS}
    d_e0 = summary["paired_differences"]["E0"]
    d_ctl = summary["paired_differences"]["CTL"]
    promote_seed = bool(d_e0["ci95"][0] > 0 and d_ctl["ci95"][0] > 0)
    out = dict(
        lane=LANE, seed=seed, evidence_class="HOLDOUT-DTI",
        evaluator_version=EH.VERSION,
        implementation_hashes=EH.implementation_hashes(),
        split=("vendor gems57 buffered_component_draw(seed=%d, hide_frac=0.20, "
               "buffer_px=3, boundary_px=12)" % seed),
        training=("leave-one-quadrant-out HGB, PU (hidden components unlabelled), "
                  "%d px train buffer" % TRAIN_BUFFER_PX),
        transform=("E1: p*(1-chat), chat=clip(G10*visible_cat / G10*clip(p/c_bar,0,1),0,1); "
                   "CTL: same with catalogue shifted (+173,-211) px"),
        emission=f"submodular_dti_emit, budget {BUDGET} x area share, collar > {COLLAR_PX} px from known",
        pooled=summary, per_fold=per_fold, coverage_by_distance_to_visible=cov,
        leakage_canary=dict(threshold=0.90, worst=worst,
                            stop=bool(worst["symmetric_auc"] > 0.90),
                            n_truth=int(tr_ids.size),
                            n_unlabelled_sample=int(un_ids.size),
                            features=canary),
        promotion=dict(beats_E0_ci_lower_gt_0=bool(d_e0["ci95"][0] > 0),
                       beats_CTL_ci_lower_gt_0=bool(d_ctl["ci95"][0] > 0),
                       both=promote_seed),
        runtime_s=round(time.time() - t0, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"holdout-seed{seed}.json").write_text(json.dumps(out, indent=2) + "\n")
    s = summary["scores"]
    log("POOLED " + " ".join(
        f"{a}={s[a]['dti']:.4f} [{s[a]['ci95'][0]:.4f},{s[a]['ci95'][1]:.4f}]"
        for a in ARMS))
    log(f"DELTA E1-E0 {d_e0['delta']:+.4f} CI {d_e0['ci95']}; "
        f"E1-CTL {d_ctl['delta']:+.4f} CI {d_ctl['ci95']}; "
        f"promote_seed={promote_seed}; canary worst {worst}")
    return out


# --------------------------------------------------------------------------- final
def run_final():
    t0 = time.time()
    WORK.mkdir(parents=True, exist_ok=True)
    g = G.load_grid(ROOT / "data" / "official")
    fp, cat = g.footprint, g.catalogue
    X, names = OLC.build_features(fp)
    fpi = OLC.fp_index_grid(fp)
    quad = H.quadrant_ids(fp)
    # LOQO-stitched phat_vis (each pixel predicted by a model that never trained
    # on its quadrant), then the full-catalogue posterior for ranking.
    phat_vis = np.zeros(fp.shape, np.float32)
    loqo_info = []
    for k in range(4):
        train_dom = fp & (ndi.distance_transform_edt(quad != k) > TRAIN_BUFFER_PX)
        pred_mask = (quad == k) & fp
        pk, info = OLC.fit_predict(X, fpi, fp, cat, train_dom, pred_mask, 9100 + k)
        phat_vis[pred_mask] = pk[pred_mask]
        loqo_info.append(dict(quadrant=int(k), **info))
        log(f"LOQO quadrant {k} done {info}")
        del pk
    p_full, info_full = OLC.fit_predict(X, fpi, fp, cat, fp, fp, 777)
    log(f"full model done {info_full}")
    chat, diag = CWP.completeness_field(cat, phat_vis, fp, calibration_mask=fp)
    surface = np.where(
        fp, np.clip(p_full, 0, 1) * (1.0 - chat), 0.0).astype(np.float32)
    log(f"completeness field: {diag}")
    eligible = fp & ~cat & (ndi.distance_transform_edt(~cat) > COLLAR_PX)
    dots = OLC.emit(surface, eligible, BUDGET)
    n_dots = int((dots > 0).sum())
    log(f"emitted {n_dots} dots; running pre+post placement registry check")
    reg = OLC.registry_check(surface, dots, fp, eligible)
    log(f"registry: surface max |rho| {reg['surface_max_abs_spearman']} "
        f"({reg['surface_closest']}); dots literal max "
        f"{reg['dots_max_within_3px_literal']} ({reg['dots_closest_literal']}); "
        f"non-blanket max {reg['dots_max_within_3px_non_blanket']} "
        f"({reg['dots_closest_non_blanket']})")
    pred = np.where(fp, dots, 0.0).astype(np.float32)
    content = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    name = f"gemsdoe91-cwp91-e1-completenesspu-37654-20261025-{content}"
    note = ("GEMSDOE91 CWP91 E1: PU posterior x (1-spatial completeness), "
            "37654 dots, 2px catalogue collar")
    assert len(note) <= 140 and len(name) <= 140, (len(name), len(note))
    dcat = ndi.distance_transform_edt(~cat)
    meta = dict(lane=LANE, arm="E1", n_dots=n_dots,
                model_full=info_full, model_loqo=loqo_info, cwp=diag,
                min_dot_distance_to_catalogue_px=round(
                    float(dcat[dots > 0].min()), 3))
    from gems57.submission_writer import write_submission
    tif = DOWNLOADS / f"{name}.tif"
    receipt = write_submission(tif, pred, SAMPLE, fp, note=note, name=name,
                               catalogue=cat, metadata=meta)
    np.save(WORK / "final_surface_E1.npy", surface.astype(np.float16))
    np.save(WORK / "final_chat_E1.npy", chat.astype(np.float16))
    out = dict(name=name, note=note, note_chars=len(note),
               tif=str(tif.relative_to(ROOT)), receipt=receipt, registry=reg,
               meta=meta, runtime_s=round(time.time() - t0, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "final-E1.json").write_text(json.dumps(out, indent=2) + "\n")
    log(f"wrote {tif.name} sha256 {receipt['sha256']}")
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("holdout")
    h.add_argument("--seed", type=int, default=20)
    sub.add_parser("final")
    a = ap.parse_args()
    if a.cmd == "holdout":
        run_holdout(a.seed)
    else:
        run_final()


if __name__ == "__main__":
    main()
