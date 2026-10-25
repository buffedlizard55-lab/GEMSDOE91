#!/usr/bin/env python3
"""ISO91 lane runner: isolation-matched positive-unlabelled (PU) learning.

Preregistration: docs/HYPOTHESES_ISO91.md, committed (e02f8a7) before any experiment ran.

Single method: the incumbent E0 pipeline (38-feature stack, HGB, LOQO, submodular emission,
area-share budget of 37,654, no dots within 2 px of known faults), except that the TRAINING
POSITIVES are only the visible catalogue components that have no other visible component
within 5 px (500 m). Isolated short faults are the closest labelled analogue of the faults
that mapping programmes missed (the short, low-relief tail of the fault population).

Subcommands
-----------
holdout --instrument I1   primary, live-aligned: gems91.isolated_holdout.isolated_component_draw(sep_px=5)
                          arms E0, E1, CTL_HALO, CTL_SUB, RND + leakage canary
holdout --instrument I2   legacy: vendor buffered_component_draw(seed=20); arms E0, E1, RND
                          (E0 must reproduce OLC91's recorded 0.085260 HOLDOUT-DTI)
final                     full-catalogue ISO91 model, pre-placement registry surface check,
                          37,654-dot emission, post-placement registry dot check, template
                          writer, independent re-validation, report-only SGMC control, run card

Every holdout number is HOLDOUT-DTI (evaluator gems57-pooled-hide-v2). Nothing here is a
leaderboard score; live scores exist only as organizer receipts. This runner never selects
or uploads a submission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
from gems57 import evaluate_holdout as EH  # noqa: E402
from gems57 import grid as G  # noqa: E402
from gems57 import holdout as H  # noqa: E402
from gems57 import metric as M  # noqa: E402
from gems57.network import STRUCT3  # noqa: E402
from gems91 import isolated_holdout as IH  # noqa: E402  (shared extension; template stays pinned)
import run_olc91 as O  # noqa: E402  (reuse: features, HGB settings, emitter, registry check)

LANE = "ISO91"
OUT = ROOT / "docs" / "iso91"
WORK = ROOT / "work" / "iso91"
DOWNLOADS = ROOT / "docs" / "downloads"
SAMPLE = ROOT / "data" / "official" / "sample_submission.tif"
SGMC = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
R0 = ROOT / "data" / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"

SEP_PX = 5.0                 # preregistered isolation distance (500 m); not tuned
HALO_PX = 5.0                # CTL_HALO emission exclusion around visible faults (= I1 construction)
SEED = 20                    # same model / random seeds as OLC91 so E0 reproduces on I2
FINAL_SEED = 777             # OLC91 final-model seed
BUDGET = O.BUDGET            # 37,654 (R0 dot count)
COLLAR_PX = O.COLLAR_PX      # 2.0 px: no dots on or within 2 px of known faults


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def fit_predict_pu(X, fpi, fp, positives, exclude, train_dom, predict_mask, seed):
    """OLC91 ``fit_predict`` with one documented change: the unlabelled (negative) pool always
    excludes ALL visible catalogue pixels (+3 px) via ``exclude``, not only the chosen positives,
    so non-isolated faults are never sampled as negatives. With ``exclude is positives`` this is
    exactly OLC91's E0 fit (same RNG stream, same HGB settings)."""
    rng = np.random.default_rng(seed)
    pos = fpi[positives & train_dom & fp]
    far = ndi.distance_transform_edt(~exclude) > 3
    pool = fpi[train_dom & fp & far]
    n_neg = int(min(pool.size, O.NEG_RATIO * pos.size))
    neg = rng.choice(pool, n_neg, replace=False)
    tr = np.concatenate([pos, neg])
    y = np.r_[np.ones(pos.size), np.zeros(n_neg)]
    order = np.argsort(tr)
    clf = HistGradientBoostingClassifier(**O.HGB)
    clf.fit(np.asarray(X[tr[order]], dtype=np.float32), y[order])
    p = np.zeros(fp.shape, np.float32)
    pm = predict_mask & fp
    ids = fpi[pm]
    vals = np.empty(ids.size, np.float32)
    for s in range(0, ids.size, 400_000):
        vals[s:s + 400_000] = clf.predict_proba(np.asarray(X[ids[s:s + 400_000]], np.float32))[:, 1]
    p[pm] = vals
    return p, dict(n_pos=int(pos.size), n_neg=n_neg, n_predicted=int(ids.size))


def matched_random_components(visible, train_dom, target_px, seed):
    """CTL_SUB positives: random whole visible components (inside the training domain) until
    their pixel count first reaches ``target_px`` (= E1's positive count)."""
    comp, n = ndi.label(visible & train_dom, STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n + 1)
    order = np.random.default_rng(seed).permutation(np.arange(1, n + 1))
    k = int(np.searchsorted(np.cumsum(sizes[order]), target_px)) + 1
    return np.isin(comp, order[:k]) & visible


def dot_geometry(dots, visible):
    d = ndi.distance_transform_edt(~visible)[dots > 0]
    if d.size == 0:
        return {}
    return dict(n=int(d.size), frac_le_5px=round(float((d <= 5).mean()), 4),
                frac_5_10px=round(float(((d > 5) & (d <= 10)).mean()), 4),
                frac_gt_10px=round(float((d > 10).mean()), 4),
                median_px=round(float(np.median(d)), 3))


# --------------------------------------------------------------------------- holdout
def run_holdout(instrument: str):
    t0 = time.time()
    g = G.load_grid(ROOT / "data" / "official")
    fp = g.footprint
    X, names = O.build_features(fp)
    fpi = O.fp_index_grid(fp)
    if instrument == "I1":
        folds, quad = IH.isolated_component_draw(g, sep_px=SEP_PX, buffer_px=3)
        arms = ("E0", "E1", "CTL_HALO", "CTL_SUB", "RND")
        split = f"gems91.isolated_holdout.isolated_component_draw(sep_px={SEP_PX}, buffer_px=3, boundary_px=12) [shared extension of pinned vendor gems57], per-fold hidden set"
    else:
        folds, quad = H.buffered_component_draw(g, seed=SEED, hide_frac=0.20, buffer_px=3)
        arms = ("E0", "E1", "RND")
        split = f"vendor gems57 buffered_component_draw(seed={SEED}, hide_frac=0.20, buffer_px=3, boundary_px=12)"
    n_fp = int(fp.sum())
    terms = {a: None for a in arms}
    per_fold, canary_truth, canary_unl = [], [], []
    for f in folds:
        k, region = f["fold"], f["region"]
        visible, known = f["visible"], f["masked_known"]
        train_dom = fp & (ndi.distance_transform_edt(quad != k) > O.TRAIN_BUFFER_PX)
        predict_mask = fp & (ndi.distance_transform_edt(~region) <= 3)
        iso_vis, _, _ = IH.isolated_components(visible, SEP_PX)
        p0, i0 = O.fit_predict(X, fpi, fp, visible, train_dom, predict_mask, SEED * 100 + k)
        p1, i1 = fit_predict_pu(X, fpi, fp, iso_vis, visible, train_dom, predict_mask, SEED * 100 + k)
        info = dict(E0=i0, E1=i1)
        dknown = ndi.distance_transform_edt(~known)
        elig = region & fp & ~known & (dknown > COLLAR_PX)
        n = int(round(BUDGET * float((region & fp).sum()) / n_fp))
        preds = dict(E0=O.emit(p0, elig, n), E1=O.emit(p1, elig, n),
                     RND=O.random_dots(elig, n, SEED * 7 + k))
        if "CTL_HALO" in arms:
            preds["CTL_HALO"] = O.emit(p0, elig & (dknown > HALO_PX), n)
        if "CTL_SUB" in arms:
            sub = matched_random_components(visible, train_dom, i1["n_pos"], SEED * 1000 + k)
            p2, i2 = fit_predict_pu(X, fpi, fp, sub, visible, train_dom, predict_mask, SEED * 100 + k)
            info["CTL_SUB"] = i2
            preds["CTL_SUB"] = O.emit(p2, elig, n)
        active = fp & region & ~known
        truth = active & f["truth"]
        row = dict(fold=f["name"], n_dots=n, withheld_positive_pixels=int(truth.sum()),
                   models=info, receipt=f["receipt"])
        for a in arms:
            res, tm = EH.evaluate(preds[a], f, fp)
            terms[a] = tm if terms[a] is None else terms[a] + tm
            row[f"{a}_dti"] = round(float(res["dti"]), 6)
            row[f"{a}_n_emitted"] = int(res["n_emitted"])
            row[f"{a}_dot_geometry_vs_visible"] = dot_geometry(preds[a], visible)
        per_fold.append(row)
        canary_truth.append(fpi[truth])
        canary_unl.append(fpi[active & ~truth])
        log(f"{instrument} fold {f['name']}: " + " ".join(f"{a}={row[f'{a}_dti']:.4f}" for a in arms)
            + f" | pos E0={i0['n_pos']} E1={i1['n_pos']}")
        del p0, p1
    summary = EH.pooled_summary(terms, candidate="E1")
    out = dict(lane=LANE, instrument=instrument, evidence_class="HOLDOUT-DTI",
               evaluator_version=EH.VERSION, implementation_hashes=EH.implementation_hashes(),
               split=split,
               training="leave-one-quadrant-out HGB (OLC91 settings), PU, %d px train buffer" % O.TRAIN_BUFFER_PX,
               emission=f"submodular_dti_emit, budget {BUDGET} x area share, no dots within {COLLAR_PX} px of known",
               arms={"E0": "incumbent: all visible catalogue pixels as positives",
                     "E1": f"ISO91: only visible components with no other visible component within {SEP_PX} px",
                     "CTL_HALO": f"E0 posterior, emission also excluded within {HALO_PX} px of visible faults",
                     "CTL_SUB": "random whole visible components, pixel count matched to E1 positives",
                     "RND": "uniform random dots on the same eligible mask"},
               pooled=summary, per_fold=per_fold)
    if instrument == "I1":
        rng = np.random.default_rng(SEED)
        tr_ids = np.concatenate(canary_truth)
        un_ids = np.concatenate(canary_unl)
        un_ids = np.sort(rng.choice(un_ids, min(un_ids.size, 300_000), replace=False))
        ids = np.concatenate([tr_ids, un_ids])
        order = np.argsort(ids)
        yy = np.r_[np.ones(tr_ids.size), np.zeros(un_ids.size)][order]
        Xc = np.asarray(X[ids[order]], np.float32)
        canary = []
        for j, nm in enumerate(names):
            auc = float(roc_auc_score(yy, Xc[:, j]))
            canary.append(dict(feature=nm, auc=round(auc, 4), symmetric_auc=round(max(auc, 1 - auc), 4)))
        worst = max(canary, key=lambda c: c["symmetric_auc"])
        out["leakage_canary"] = dict(threshold=0.90, worst=worst, stop=bool(worst["symmetric_auc"] > 0.90),
                                     n_truth=int(tr_ids.size), n_unlabelled_sample=int(un_ids.size),
                                     features=canary)
    out["runtime_s"] = round(time.time() - t0, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"holdout-{instrument}.json").write_text(json.dumps(out, indent=2) + "\n")
    s, d = summary["scores"], summary["paired_differences"]
    log("POOLED " + " ".join(f"{a}={s[a]['dti']:.6f} [{s[a]['ci95'][0]:.6f},{s[a]['ci95'][1]:.6f}]" for a in arms))
    log("PAIRED E1 minus: " + " ".join(f"{a} {d[a]['delta']:+.6f} [{d[a]['ci95'][0]:+.6f},{d[a]['ci95'][1]:+.6f}]" for a in d))
    if "leakage_canary" in out:
        log(f"canary worst {out['leakage_canary']['worst']}")
    return out


# --------------------------------------------------------------------------- uniqueness
def surface_precheck(surface, fp, stride=5):
    """Rule 1a: |Spearman| of the continuous surface vs every registry raster BEFORE placement."""
    uniq, dup = O.registry_paths()
    s = surface[fp][::stride].astype(np.float64)
    rs = rankdata(s) - (s.size + 1) / 2.0
    rs_n = float(np.linalg.norm(rs))
    rows = []
    for p, h in uniq:
        with rasterio.open(p) as ds:
            if ds.count != 1 or ds.shape != fp.shape:
                continue
            a = ds.read(1).astype(np.float64)
        a = np.where(np.isfinite(a), a, 0.0)[fp][::stride]
        rr = rankdata(a) - (a.size + 1) / 2.0
        rr_n = float(np.linalg.norm(rr))
        rho = abs(float(rs @ rr) / (rs_n * rr_n)) if rr_n > 0 else 0.0
        rows.append(dict(raster=str(p.relative_to(ROOT)), surface_abs_spearman=round(rho, 5)))
    worst = max(rows, key=lambda r: r["surface_abs_spearman"])
    return dict(n_checked=len(rows), max_abs_spearman=worst["surface_abs_spearman"],
                closest=worst["raster"], stop=bool(worst["surface_abs_spearman"] > 0.90), rows=rows)


def sgmc_control(preds: dict, cat, fp):
    """REPORT-ONLY blind off-catalogue SGMC control (S17-LFTG definition); never a gate."""
    with rasterio.open(SGMC) as src:
        sg = (src.read(1) > 0) & fp
    d_cat = ndi.distance_transform_edt(~cat)
    t3, t5 = sg & (d_cat > 3.0), sg & (d_cat > 5.0)
    active = fp & ~cat
    out = {}
    for name, arr in preds.items():
        pred = np.where(active, arr, 0.0)
        r3 = M.dti_exact(pred, t3, valid=active)
        r5 = M.dti_exact(pred, t5, valid=active)
        dots = (arr > 0) & fp
        out[name] = dict(label="SGMC-OFFCAT-CONTROL-DTI (report-only)", dti_gt300m=round(float(r3["dti"]), 6),
                         dti_gt500m=round(float(r5["dti"]), 6), n_dots=int(dots.sum()),
                         frac_dots_gt_1km_from_catalogue=round(float((d_cat[dots] > 10).mean()), 4))
    return dict(n_truth_gt300m=int(t3.sum()), n_truth_gt500m=int(t5.sum()), arms=out)


# --------------------------------------------------------------------------- final
def run_final():
    t0 = time.time()
    g = G.load_grid(ROOT / "data" / "official")
    fp, cat = g.footprint, g.catalogue
    X, names = O.build_features(fp)
    fpi = O.fp_index_grid(fp)
    iso, _, iso_ids = IH.isolated_components(cat, SEP_PX)
    p1, info = fit_predict_pu(X, fpi, fp, iso, cat, fp, fp, FINAL_SEED)
    p0, info0 = O.fit_predict(X, fpi, fp, cat, fp, fp, FINAL_SEED)
    log(f"final models: ISO91 positives {info['n_pos']} ({len(iso_ids)} isolated components); E0 positives {info0['n_pos']}")
    pre = surface_precheck(p1, fp)
    log(f"pre-placement surface check: max |rho| {pre['max_abs_spearman']} ({pre['closest']}) stop={pre['stop']}")
    if pre["stop"]:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "final.json").write_text(json.dumps(dict(status="DUPLICATE-STOP before placement", surface=pre), indent=2) + "\n")
        raise SystemExit("duplicate-stop: surface rank correlation > 0.90")
    dcat = ndi.distance_transform_edt(~cat)
    eligible = fp & ~cat & (dcat > COLLAR_PX)
    dots = O.emit(p1, eligible, BUDGET)
    dots0 = O.emit(p0, eligible, BUDGET)
    n_dots = int((dots > 0).sum())
    reg = O.registry_check(p1, dots, fp, eligible)
    log(f"post-placement: dots literal max {reg['dots_max_within_3px_literal']} ({reg['dots_closest_literal']}); "
        f"non-blanket max {reg['dots_max_within_3px_non_blanket']} ({reg['dots_closest_non_blanket']}); "
        f"any literal dup {reg['any_duplicate_literal']}; any chance-corrected dup {reg['any_duplicate_chance_corrected']}")
    with rasterio.open(R0) as ds:
        r0 = np.where(np.isfinite(ds.read(1)), ds.read(1), 0).astype(np.float32)
    sg = sgmc_control({"ISO91_E1_final": dots, "E0_final_same_emission": dots0, "R0_gemsdoe32_h33_2_b2": r0}, cat, fp)
    pred = np.where(fp, dots, 0.0).astype(np.float32)
    content = hashlib.sha256(pred.tobytes()).hexdigest()[:8]
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    name = f"gemsdoe91-iso91-isolationpu-{n_dots}-{stamp}-{content}"
    note = "GEMSDOE91 ISO91: PU learned only from isolated (>500m) catalogue faults, 37654 binary dots, 2px collar"
    assert len(note) <= 140 and len(name) <= 140
    meta = dict(lane=LANE, n_dots=n_dots, model=info, isolation_sep_px=SEP_PX,
                n_isolated_components=int(len(iso_ids)),
                min_dot_distance_to_catalogue_px=round(float(dcat[dots > 0].min()), 3),
                dot_geometry_vs_catalogue=dot_geometry(dots, cat),
                e0_same_emission_dot_geometry_vs_catalogue=dot_geometry(dots0, cat))
    from gems57.submission_writer import write_submission
    tif = DOWNLOADS / f"{name}-zeros.tif"
    receipt = write_submission(tif, pred, SAMPLE, fp, note=note, name=name, catalogue=cat, metadata=meta)
    WORK.mkdir(parents=True, exist_ok=True)
    np.save(WORK / "final_surface_E1.npy", p1.astype(np.float16))
    out = dict(name=name, note=note, tif=str(tif.relative_to(ROOT)), receipt=receipt,
               surface_precheck={k: v for k, v in pre.items() if k != "rows"}, registry=reg,
               sgmc_control_report_only=sg, meta=meta, runtime_s=round(time.time() - t0, 1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "final.json").write_text(json.dumps(out, indent=2) + "\n")
    (OUT / "surface-precheck.json").write_text(json.dumps(pre, indent=2) + "\n")
    log(f"wrote {tif.name} sha256 {receipt['sha256']}")
    log("SGMC (report-only): " + json.dumps(sg["arms"]))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("holdout")
    h.add_argument("--instrument", choices=("I1", "I2"), required=True)
    sub.add_parser("final")
    a = ap.parse_args()
    if a.cmd == "holdout":
        run_holdout(a.instrument)
    else:
        run_final()


if __name__ == "__main__":
    main()
