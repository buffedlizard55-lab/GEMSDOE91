#!/usr/bin/env python3
"""S22-XB E3: final unique file from the preregistered best arm + every automated gate + the run card.

Reads (never recomputes) docs/s22/holdout.json written by ``run_s22_xbreed.py evaluate``; picks the arm with the
highest CELF pooled HOLDOUT-DTI (preregistered rule); builds the stitched 4-fold out-of-fold surface; emits the equalized
per-quadrant CELF dots with the **global** catalogue collar; screens them against every raster in the registry, the
repo downloads and the 102-repo sibling sweep; falls back to a hard-capped global CELF only if the screen fails; writes the
all-finite zeros-encoded float32 GeoTIFF + one-TIFF ZIP with the unchanged shared writer; validates with the three repo
gate suites and an independent tifffile re-read; computes the blind-SGMC control and the LFI (live-anchored) projections of
the file and of every independent-model comparator; evaluates gates G1-G6; writes docs/run-card-S22-XB.json.

Nothing here selects a submission for the user: ``ok_to_submit`` is a pure function of the gates, and the card prints
``slots_used = 0``.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import tifffile  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57 import gates as g57_gates  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems91 import xbreed22 as X  # noqa: E402
from gems91.pdwc21 import emit_dots_celf_submodular  # noqa: E402
from gems91.release_gates import validate_release  # noqa: E402

EVIDENCE = ROOT / "docs/s22"
DOWNLOADS = ROOT / "docs/downloads"
PINNED_HOLDOUT = {"S21 pdwc_e3": 0.195724, "S18 hgbr_e1": 0.200742}
UNIQUENESS_CAP_FALLBACK = 0.55
PASS1_MAX_COMPETITIVE_OVERLAP = 0.65  # margin below the 0.70 protocol limit

COMPARATORS = {  # independent-model rasters only (LFI-optimized rasters are excluded: optimizer's-curse inflated)
    "S18 hgbr_e1": "docs/downloads/gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.tif",
    "S19 svhf_e3": "docs/downloads/gems91-s19-svhf-e3-oof-20261025T194830Z-5cc11f080635-zeros.tif",
    "S20 rhtw_e3": "docs/downloads/gems91-s20-rhtw-e3-20261026T043618Z-4d501134-zeros.tif",
    "S21 pdwc_e3": "docs/downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif",
}
CONTEXT = {  # reported, never gating
    "GEMSDOE32 R0 (USER-REPORTED 0.2778)": "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif",
    "S20 lfi_consensus (LFI-optimized)": "docs/downloads/gems91-s20-lfi-consensus-29671dots-20261026T014752Z-a8cc1b6e-zeros.tif",
    "S21 fam3 (LFI-optimized)": "docs/downloads/gems91-s21-fam3-23481dots-20261026T065950Z-f6411d38-zeros.tif",
}


def load_s21():
    spec = importlib.util.spec_from_file_location("run_s21_pdwc_mod", ROOT / "scripts/run_s21_pdwc.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.CACHE_DIR = X.CACHE
    return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lfi_projections(paths: dict[str, Path], footprint, catalogue) -> dict[str, dict]:
    """S20 LFI model-only projection (stored fits) for several rasters with ONE design build. MODEL, never a score."""
    from gems91 import lfi as L

    spec = importlib.util.spec_from_file_location("run_lfi_mod2", ROOT / "scripts/run_lfi.py")
    rl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rl)
    rl.WORK = ROOT / "work/lfi"
    rl.WORK.mkdir(parents=True, exist_ok=True)
    sha_map = {}
    for d_rel in ("data/lfi_anchors", "data/fleet_registry", "data/registry"):
        for p in (ROOT / d_rel).glob("*.tif"):
            sha_map.setdefault(sha256_file(p), str(p.relative_to(ROOT)))
    meta = json.loads((ROOT / "docs/lfi/anchors.json").read_text())
    for r in meta["rows"]:
        if r.get("used"):
            if r.get("sha256") in sha_map:
                r["local"] = sha_map[r["sha256"]]
            else:
                r["used"] = False
    fp, cat, net = rl.base()
    design, _, _ = rl.build_design(fp, cat, net, meta["rows"])
    bins = design.bin_index()
    nb = design.n_bins
    A = np.bincount(bins[fp & ~cat], minlength=nb).astype(np.float64)
    Lm = design.level_matrix()
    Xd = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    pnames = design.param_names()
    fits = {}
    for tag in ("r1", "r10"):
        fd = json.loads((ROOT / f"docs/lfi/fit_{tag}.json").read_text())
        fits[tag] = (np.array([float(fd["theta"][k]) for k in pnames]), float(fd["f"]), float(fd["rmse_loso"]))
    out = {}
    for name, path in paths.items():
        if isinstance(path, np.ndarray):
            arr = path
        else:
            with rasterio.open(path) as ds:
                a = ds.read(1)
            arr = np.where(np.isfinite(a) & fp, a, 0.0).astype(np.float32)
        N, C = L.aggregate(arr, bins, nb, cat)
        rec = {"label_class": "MODEL_PROJECTION_NOT_A_SCORE", "n_dots": int((arr > 0).sum())}
        for tag, (theta, f, rmse) in fits.items():
            y, _ = L.predict(theta, f, Xd, N[None, :], C[None, :], A)
            rec[tag] = {"projected": round(float(y[0]), 5), "loso_rmse": round(rmse, 5)}
        out[name] = rec
        print(f"  LFI projection {name:42s} ridge10={rec['r10']['projected']:.4f} ridge1={rec['r1']['projected']:.4f}", flush=True)
    return out


def _common():
    s21 = load_s21()
    pins = s21.verify_template_pins()
    hold = json.loads((EVIDENCE / "holdout.json").read_text())
    canary = json.loads((EVIDENCE / "canary.json").read_text())
    scores = hold["scores"]
    arm = max(("A", "B", "C"), key=lambda a: scores[f"{a}_celf"]["dti"] if f"{a}_celf" in scores else -1.0)
    footprint, catalogue, folds = X.load_common()
    cubes = X.load_cubes(footprint)
    cover_fp, crest_fp = X.cover_and_crest(cubes)
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    return s21, pins, hold, canary, scores, arm, footprint, catalogue, folds, cover_fp, crest_fp, d_cat


def _quadrant_dots(surface, catalogue, footprint, folds, d_cat, caps=None):
    dots = np.zeros(footprint.shape, np.float32)
    for q, f in enumerate(folds):
        dq = X.emit_quadrant_final(surface, catalogue, footprint, f["region"], d_cat, q, "celf", caps=caps)
        dots = np.maximum(dots, dq)
        print(f"  quadrant {q}: {int((dq > 0).sum())} dots (budget {X.QUAD_BUDGETS[q]})", flush=True)
        del dq
    return dots


def stage_capped() -> int:
    """Persist the active reference set from the pass-1 (uncapped) dots and evaluate arms A and C under the shipped recipe."""
    t0 = time.time()
    s21, pins, hold, canary, scores, arm, footprint, catalogue, folds, cover_fp, crest_fp, d_cat = _common()
    print(f"[capped] selected arm {arm}", flush=True)
    surface = X.stitched_oof_surface(arm, folds, footprint, cover_fp, crest_fp)
    pass1 = X.CACHE / f"pass1_dots_{arm}.npy"
    if pass1.is_file():
        dots = np.load(pass1)
    else:
        dots = _quadrant_dots(surface, catalogue, footprint, folds, d_cat)
        np.save(pass1, dots)
    for old in DOWNLOADS.glob("gems91-s22-*"):
        old.unlink()
    refs = s21.collect_all_reference_rasters()
    screen, active_paths = s21.screen_against_references(surface, dots, footprint, refs,
                                                         active_cap_select_thresh=X.ACTIVE_REF_MIN_OVERLAP,
                                                         max_cap_refs=X.MAX_CAP_REFS)
    comp = screen["dots_phase_competitive"]
    print(f"[capped] pass-1 screen: max competitive overlap {comp['max_3px_overlap_all_competitive']:.4f} "
          f"({comp['max_3px_overlap_all_competitive_ref']}); active refs {len(active_paths)}", flush=True)
    (EVIDENCE / "registry-screen-pass1.json").write_text(json.dumps(screen, indent=1) + "\n")
    ov = {r["path"]: r["dot_overlap_3px"] for r in comp.get("top_20_competitive_by_3px_overlap", [])}
    (EVIDENCE / "active-references.json").write_text(json.dumps({
        "rule": f"non-blanket references whose pass-1 3-px overlap >= {X.ACTIVE_REF_MIN_OVERLAP}, top {X.MAX_CAP_REFS}",
        "n": len(active_paths), "uniqueness_cap": X.UNIQUENESS_CAP,
        "references": [{"path": str(p.relative_to(ROOT)), "sha256": sha256_file(p),
                        "pass1_overlap_if_top20": ov.get(str(p.relative_to(ROOT)))} for p in active_paths]}, indent=1) + "\n")

    words, n_refs = s21.pack_reference_halos_uint64(active_paths, footprint)
    caps = {"words": words, "n_refs": n_refs, "cap": X.UNIQUENESS_CAP}
    terms, per_fold = {}, {}

    def run_arm(name, pred_fn):
        t_sum, pf = s21.evaluate_arm_terms(pred_fn, folds, footprint)
        terms[name], per_fold[name] = t_sum, pf
        print(f"[capped] {name:12s} HOLDOUT-DTI = {float(eh.from_terms(t_sum.sum(axis=0))):.6f}  ({time.time() - t0:.0f}s)", flush=True)

    for a in ("A", "C"):
        cache = {}

        def surf(q, _a=a, _c=cache):
            if q not in _c:
                _c.clear()
                _c[q] = X.quadrant_surface(_a, q, footprint, cover_fp, crest_fp)
            return _c[q]

        run_arm(f"{a}_celf_cap", lambda f, _s=surf, _c=caps: X.emit_quadrant(_s(int(f["fold"])), f, footprint, int(f["fold"]), "celf", caps=_c))
        del cache
        gc.collect()
    pooled = {}
    for cand in terms:
        pooled[cand] = eh.pooled_summary(terms, draws=1000, seed=520810, candidate=cand)
    sc = {n: {"dti": round(pooled["C_celf_cap"]["scores"][n]["dti"], 6),
              "ci95": [round(x, 6) for x in pooled["C_celf_cap"]["scores"][n]["ci95"]]} for n in terms}
    d = pooled["C_celf_cap"]["paired_differences"]["A_celf_cap"]
    out = {"evaluator_version": eh.VERSION, "split_sha256": hold["split_sha256"],
           "withheld_positive_pixels": hold["withheld_positive_pixels"],
           "design": "equalized per-quadrant CELF with hard per-reference caps (amendment A3)",
           "uniqueness_cap": X.UNIQUENESS_CAP, "n_active_references": len(active_paths),
           "scores": sc, "per_fold": per_fold,
           "paired_C_minus_A_celf_cap": {"delta": round(d["delta"], 6), "ci95": [round(x, 6) for x in d["ci95"]]},
           "pooled": pooled, "elapsed_s": round(time.time() - t0, 1)}
    (EVIDENCE / "holdout-capped.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"scores": sc, "paired": out["paired_C_minus_A_celf_cap"]}, indent=1), flush=True)
    return 0


def stage_posthoc() -> int:
    """POST-HOC sensitivity (not preregistered, cannot change any verdict): cap each arm against ITS OWN active set.

    Amendment A3 derived the active reference set from arm C's pass-1 dots and applied it to both arms, which binds C harder
    than A.  Here arm A gets the set derived from its own pass-1 dots, so each arm is evaluated as the unique raster it
    could actually ship.  Arm C's capped scores are re-used (its set is its own).
    """
    t0 = time.time()
    s21, pins, hold, canary, scores, arm, footprint, catalogue, folds, cover_fp, crest_fp, d_cat = _common()
    capped = json.loads((EVIDENCE / "holdout-capped.json").read_text())
    surface_a = X.stitched_oof_surface("A", folds, footprint, cover_fp, crest_fp)
    dots_a = _quadrant_dots(surface_a, catalogue, footprint, folds, d_cat)
    refs = s21.collect_all_reference_rasters()
    screen_a, active_a = s21.screen_against_references(surface_a, dots_a, footprint, refs,
                                                       active_cap_select_thresh=X.ACTIVE_REF_MIN_OVERLAP, max_cap_refs=X.MAX_CAP_REFS)
    comp_a = screen_a["dots_phase_competitive"]
    print(f"[posthoc] arm A pass-1: max competitive overlap {comp_a['max_3px_overlap_all_competitive']:.4f} "
          f"({comp_a['max_3px_overlap_all_competitive_ref']}); own active refs {len(active_a)}", flush=True)
    words, n_refs = s21.pack_reference_halos_uint64(active_a, footprint)
    caps = {"words": words, "n_refs": n_refs, "cap": X.UNIQUENESS_CAP}
    cache = {}

    def surf(q):
        if q not in cache:
            cache.clear()
            cache[q] = X.quadrant_surface("A", q, footprint, cover_fp, crest_fp)
        return cache[q]

    t_a, pf_a = s21.evaluate_arm_terms(lambda f: X.emit_quadrant(surf(int(f["fold"])), f, footprint, int(f["fold"]), "celf", caps=caps),
                                       folds, footprint)
    dti_a = float(eh.from_terms(t_a.sum(axis=0)))
    print(f"[posthoc] A_celf_cap_own HOLDOUT-DTI = {dti_a:.6f}", flush=True)
    # C's capped terms: rebuild them from the stored pooled structure is not possible, so re-evaluate C with its own set
    active_c = X.active_reference_paths()
    words_c, n_c = s21.pack_reference_halos_uint64(active_c, footprint)
    caps_c = {"words": words_c, "n_refs": n_c, "cap": X.UNIQUENESS_CAP}
    cache_c = {}

    def surf_c(q):
        if q not in cache_c:
            cache_c.clear()
            cache_c[q] = X.quadrant_surface("C", q, footprint, cover_fp, crest_fp)
        return cache_c[q]

    t_c, pf_c = s21.evaluate_arm_terms(lambda f: X.emit_quadrant(surf_c(int(f["fold"])), f, footprint, int(f["fold"]), "celf", caps=caps_c),
                                       folds, footprint)
    terms = {"A_celf_cap_own": t_a, "C_celf_cap": t_c}
    pooled = eh.pooled_summary(terms, draws=1000, seed=520810, candidate="C_celf_cap")
    d = pooled["paired_differences"]["A_celf_cap_own"]
    out = {"label": "POST-HOC sensitivity analysis (not preregistered; cannot change any verdict)",
           "evaluator_version": eh.VERSION, "uniqueness_cap": X.UNIQUENESS_CAP,
           "arm_A_own_active_references": len(active_a), "arm_C_active_references": len(active_c),
           "arm_A_pass1_max_competitive_overlap": comp_a["max_3px_overlap_all_competitive"],
           "arm_A_pass1_max_competitive_ref": comp_a["max_3px_overlap_all_competitive_ref"],
           "scores": {n: {"dti": round(v["dti"], 6), "ci95": [round(x, 6) for x in v["ci95"]]} for n, v in pooled["scores"].items()},
           "paired_C_minus_A_own": {"delta": round(d["delta"], 6), "ci95": [round(x, 6) for x in d["ci95"]]},
           "reference_asymmetric_A3_value": capped["paired_C_minus_A_celf_cap"], "elapsed_s": round(time.time() - t0, 1)}
    (EVIDENCE / "holdout-capped-symmetric-posthoc.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1), flush=True)
    return 0


def stage_final() -> int:
    t0 = time.time()
    s21, pins, hold, canary, scores, arm, footprint, catalogue, folds, cover_fp, crest_fp, d_cat = _common()
    capped = json.loads((EVIDENCE / "holdout-capped.json").read_text())
    prereg = ROOT / "docs/HYPOTHESES_S22_XBREED.md"
    print(f"[final] arm {arm}", flush=True)
    surface = X.stitched_oof_surface(arm, folds, footprint, cover_fp, crest_fp)
    for old in DOWNLOADS.glob("gems91-s22-*"):
        old.unlink()
    refs = s21.collect_all_reference_rasters()
    active_paths = X.active_reference_paths()
    recipe = (f"equalized per-quadrant 300 m CELF on the stitched 4-fold OOF surface with hard per-reference 3-px caps "
              f"<= {X.UNIQUENESS_CAP} on {len(active_paths)} active references (amendment A3), global catalogue collar")
    screen = None
    for rnd in range(3):
        words, n_refs = s21.pack_reference_halos_uint64(active_paths, footprint)
        dots = _quadrant_dots(surface, catalogue, footprint, folds, d_cat,
                              caps={"words": words, "n_refs": n_refs, "cap": X.UNIQUENESS_CAP})
        del words
        screen, more = s21.screen_against_references(surface, dots, footprint, refs,
                                                     active_cap_select_thresh=X.ACTIVE_REF_MIN_OVERLAP, max_cap_refs=X.MAX_CAP_REFS)
        comp = screen["dots_phase_competitive"]
        print(f"[final] round {rnd}: n={int((dots > 0).sum())} max competitive overlap "
              f"{comp['max_3px_overlap_all_competitive']:.4f} ({comp['max_3px_overlap_all_competitive_ref']})", flush=True)
        if comp["pass_competitive_uniqueness"] and screen["surface_phase"]["pass_le_090"] and int((dots > 0).sum()) == X.DOT_BUDGET:
            break
        active_paths = (active_paths + [p for p in more if p not in set(active_paths)])[:256]
    (EVIDENCE / "registry-screen-final.json").write_text(json.dumps(screen, indent=1) + "\n")
    comp = screen["dots_phase_competitive"]
    lit = screen["dots_phase_literal_including_synthetic_blankets"]
    n_dots = int((dots > 0).sum())
    quad_counts = [int(((dots > 0) & f["region"]).sum()) for f in folds]
    # the rest of this stage is unchanged: write, validate, project, gate, card
    return _write_and_gate(s21, pins, hold, capped, canary, scores, arm, footprint, catalogue, folds, d_cat, surface, dots,
                           screen, comp, lit, n_dots, quad_counts, recipe, prereg, t0)


def _write_and_gate(s21, pins, hold, capped, canary, scores, arm, footprint, catalogue, folds, d_cat, surface, dots,
                    screen, comp, lit, n_dots, quad_counts, recipe, prereg, t0):
    # ---- write + validate ------------------------------------------------------------------------------------------
    git_sha8 = subprocess.run(["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, check=True, capture_output=True,
                              text=True).stdout.strip()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"gems91-s22-xbreed-{arm.lower()}-{n_dots}dots-{ts}-{git_sha8}-zeros"
    out_tif, out_zip = DOWNLOADS / f"{stem}.tif", DOWNLOADS / f"{stem}.zip"
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    h_c = scores[f"{arm}_celf"]
    h_cap = capped["scores"][f"{arm}_celf_cap"]
    note = (f"S22-XB arm {arm} PDWC66+HGBR16 OOF+capped CELF {n_dots}d; hide-v2 HOLDOUT-DTI={h_cap['dti']:.4f}; "
            f"LFI projection only; research")[:140]
    meta = write_submission(out_tif, dots, X.SAMPLE_TIF, footprint, note=note, name=stem, catalogue=catalogue)
    fmt = g57_gates.format_report(out_tif, X.SAMPLE_TIF, footprint=footprint)
    rel = validate_release(out_tif, template=X.SAMPLE_TIF, catalogue=catalogue, encoding="zeros", floor_px=3.0,
                           expect_dots=n_dots)
    tf = tifffile.imread(out_tif)
    with zipfile.ZipFile(out_zip) as zf:
        members, bad = zf.namelist(), zf.testzip()
    with rasterio.open(out_tif) as ds, rasterio.open(X.SAMPLE_TIF) as ref:
        same_grid = (ds.crs == ref.crs and ds.shape == ref.shape and ds.transform == ref.transform and ds.count == 1
                     and ds.dtypes[0] == "float32" and ds.nodata is None)
    min_cat_dist = float(d_cat[dots > 0].min())
    from scipy.spatial import cKDTree
    yy, xx = np.nonzero(dots > 0)
    dd, _ = cKDTree(np.c_[yy, xx]).query(np.c_[yy, xx], k=2)
    min_inter_dot = float(dd[:, 1].min())
    validator = {
        "automated_without_human_intervention": True,
        "crs_shape_transform_match_sample": bool(same_grid),
        "n_dots": n_dots, "min_catalogue_distance_px": round(min_cat_dist, 4),
        "min_inter_dot_distance_px": round(min_inter_dot, 4),
        "positives_on_catalogue": int(((dots > 0) & catalogue).sum()),
        "positives_outside_footprint": int(((dots > 0) & ~footprint).sum()),
        "nan_or_inf_pixels": int((~np.isfinite(tf)).sum()),
        "min_value": float(tf.min()), "max_value": float(tf.max()),
        "unique_values": [float(v) for v in np.unique(tf)],
        "gems57_format_report_ok": bool(fmt["ok"]), "gems91_release_gates_pass": bool(rel["PASS"]),
        "zip_single_tif_member": members == [out_tif.name], "zip_crc_ok": bad is None,
    }
    validator["pass"] = bool(validator["crs_shape_transform_match_sample"] and validator["gems57_format_report_ok"]
                             and validator["gems91_release_gates_pass"] and validator["zip_single_tif_member"]
                             and validator["zip_crc_ok"] and validator["nan_or_inf_pixels"] == 0
                             and validator["min_value"] >= 0.0 and validator["max_value"] <= 1.0
                             and validator["positives_on_catalogue"] == 0 and min_cat_dist > 3.0)
    print(f"[final] wrote {out_tif.name} ({out_tif.stat().st_size:,} B) validator pass={validator['pass']}", flush=True)

    sgmc = s21.evaluate_blind_sgmc_suite(dots, catalogue, footprint)
    paths = {k: ROOT / v for k, v in {**COMPARATORS, **CONTEXT}.items() if (ROOT / v).is_file()}
    paths["S22-XB (this file)"] = dots
    proj = lfi_projections(paths, footprint, catalogue)
    cand_proj = proj["S22-XB (this file)"]["r10"]["projected"]
    comp_proj = {k: proj[k]["r10"]["projected"] for k in COMPARATORS if k in proj}
    best_comp_name = max(comp_proj, key=comp_proj.get) if comp_proj else None

    # ---- gates (computed, not asserted) ----------------------------------------------------------------------------
    d_unc = hold["paired_differences"].get("C_minus_A_celf")
    d_cap = capped["paired_C_minus_A_celf_cap"]
    g4 = bool(arm == "C" and d_unc is not None and d_unc["ci95"][0] > 0.0 and d_cap["ci95"][0] > 0.0)
    gates = {
        "G1_format": {"pass": bool(validator["pass"])},
        "G2_uniqueness_protocol": {"pass": bool(screen["surface_phase"]["pass_le_090"] and comp["pass_competitive_uniqueness"]),
                                   "max_competitive_3px_overlap": comp["max_3px_overlap_all_competitive"],
                                   "max_competitive_ref": comp["max_3px_overlap_all_competitive_ref"],
                                   "max_abs_surface_spearman": screen["surface_phase"]["max_abs_spearman_all_1100plus"],
                                   "n_compared_rasters": screen["n_compared_rasters"],
                                   "n_competitive_rasters": screen["n_competitive_non_blanket_rasters"],
                                   "literal_all_raster_max_overlap": lit["max_3px_overlap_literal"],
                                   "literal_ref": lit["max_3px_overlap_literal_ref"],
                                   "note": "literal figure includes dense synthetic blankets (IR-S16-03 / IR-S21-04); disclosed, not gating"},
        "G3_leakage_canary": {"pass": bool(canary["overall_pass_le_090"]), "max_symmetric_auc": canary["overall_max_symmetric_auc"]},
        "G4_holdout_paired": {"pass": g4, "selected_arm": arm, "paired_C_minus_A_uncapped_celf": d_unc,
                              "paired_C_minus_A_capped_celf": d_cap,
                              "nominal_vs_pinned_references": {k: {"reference": v, "candidate_uncapped": round(h_c["dti"], 6),
                                                                   "candidate_capped": round(h_cap["dti"], 6),
                                                                   "exceeds_capped": bool(h_cap["dti"] > v)} for k, v in PINNED_HOLDOUT.items()},
                              "note": "pinned references use S21/S18's global-budget design; context only (Amendments A1, A3)"},
        "G5_live_anchored_projection": {"pass": bool(best_comp_name is not None and cand_proj >= comp_proj[best_comp_name]),
                                        "candidate_ridge10": cand_proj, "best_independent_comparator": best_comp_name,
                                        "comparators_ridge10": comp_proj,
                                        "label": "MODEL_PROJECTION_NOT_A_SCORE; LOSO RMSE ~0.02"},
        "G6_informational_vs_R0": {"candidate_ridge10": cand_proj,
                                   "R0_ridge10": proj.get("GEMSDOE32 R0 (USER-REPORTED 0.2778)", {}).get("r10", {}).get("projected")},
    }
    ok_dl = bool(gates["G1_format"]["pass"])
    required = ("G1_format", "G2_uniqueness_protocol", "G3_leakage_canary", "G4_holdout_paired", "G5_live_anchored_projection")
    ok_sub = bool(all(gates[g]["pass"] for g in required))
    failed = [g for g in required if not gates[g]["pass"]]

    card = {
        "schema_version": "gems-run-card-v2", "lane_id": "S22-XB", "date_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "branch": "arena/c722cd53-gemsdoe91",
        "preregistration": {"path": "docs/HYPOTHESES_S22_XBREED.md", "sha256_final": sha256_file(prereg),
                            "sha256_before_experiments": "14d2af0020c81e3fb76e9f73725bb11639a466327a118f7d7a0671fdefbd8ebd",
                            "amendments": {"A1": "8c5d61d53dfc3c7cd59a27a25946c161dc83435c38ae8196494ef8cd61c92b92",
                                           "A2": "5c404390734b9b9fbd34be0d799080835f69ccd41ea2892a7f8674ad84ae23d5",
                                           "A3": "c1f9914992ffca2b8842cd4622baefc431bd6aab2814027f34dc9dce1b865724"},
                            "experiments_run": 3, "budget_max_experiments": 3, "elapsed_seconds_final_stage": round(time.time() - t0, 1)},
        "hypothesis": "H22-1: PDWC66 (dipping-contact waveform + phase congruency) jointly trained with HGBR16 (local Hurst/anisotropy regime breaks) improves out-of-fold fault ranking over either feature family alone under equalized quadrant budgets",
        "mechanism": "A fault edge in potential-field data should show a localized amplitude/phase signature (PDWC) AND a change of local roughness/anisotropy regime across the trace (HGBR); requiring both cues lets the model reject lithologic contacts that show only one.",
        "named_non_fault_mimic": "Unfaulted dipping pluton/caldera walls and tilted welded tuff (PDWC cue) and airborne flight-line seams (both families); the pure-subsurface sub-model and the seam guard are retained to limit them.",
        "recipe": recipe, "selected_arm": arm,
        "verdict": "promote" if ok_sub else "negative", "ok_to_download": ok_dl, "ok_to_submit": ok_sub,
        "failed_gates": failed, "slots_used": 0, "organizer_confirmed_score": None,
        "holdout": {"score_label": "HOLDOUT-DTI", "evaluator_version": hold["evaluator_version"], "split_sha256": hold["split_sha256"],
                    "n_withheld_positives": hold["withheld_positive_pixels"], "design": hold["design"],
                    "selected_experiment_uncapped": f"{arm}_celf", "holdout_dti_uncapped": h_c["dti"], "ci95_uncapped": h_c["ci95"],
                    "selected_experiment_shipped_recipe": f"{arm}_celf_cap", "holdout_dti": h_cap["dti"], "ci95": h_cap["ci95"],
                    "all_scores_uncapped": scores, "paired_differences_uncapped": hold["paired_differences"],
                    "all_scores_capped": capped["scores"], "paired_C_minus_A_capped": d_cap, "per_fold": hold["per_fold"],
                    "per_fold_capped": capped["per_fold"]},
        "blind_sgmc_control": {"label": "BLIND-SGMC-CONTROL (diagnostic; not the organizer test set)", "candidate": sgmc},
        "lfi_projection": {"label_class": "MODEL_PROJECTION_NOT_A_SCORE", "all": proj},
        "canary": {"n_features_tested": canary["pdwc66"]["n_features"] + canary["hgbr16"]["n_features"],
                   "max_symmetric_auc": canary["overall_max_symmetric_auc"], "pass": canary["overall_pass_le_090"]},
        "uniqueness": {"n_compared_rasters_total": screen["n_compared_rasters"],
                       "n_competitive_non_blanket_rasters": screen["n_competitive_non_blanket_rasters"],
                       "surface_max_abs_spearman": screen["surface_phase"]["max_abs_spearman_all_1100plus"],
                       "surface_max_abs_spearman_ref": screen["surface_phase"]["max_abs_spearman_ref"],
                       "dots_max_abs_spearman": comp["max_abs_spearman"],
                       "dots_max_3px_overlap_competitive": comp["max_3px_overlap_all_competitive"],
                       "dots_max_3px_overlap_competitive_ref": comp["max_3px_overlap_all_competitive_ref"],
                       "dots_max_3px_overlap_protocol_competitive": comp["max_3px_overlap_protocol_competitive"],
                       "competitive_unique_pass": bool(comp["pass_competitive_uniqueness"]),
                       "literal_all_raster_max_3px_overlap": lit["max_3px_overlap_literal"],
                       "literal_all_raster_max_ref": lit["max_3px_overlap_literal_ref"]},
        "validator": validator,
        "quadrant_dot_counts": quad_counts,
        "raster_sha256": meta["sha256"],
        "submission": {"name": stem, "file": str(out_tif.relative_to(ROOT)), "tif_file": str(out_tif.relative_to(ROOT)),
                       "zip_file": str(out_zip.relative_to(ROOT)), "tif_bytes": out_tif.stat().st_size,
                       "zip_bytes": out_zip.stat().st_size, "sha256": meta["sha256"], "zip_sha256": sha256_file(out_zip),
                       "note": note, "note_length": len(note)},
        "gates": gates, "template_pins_verified": pins,
    }
    (ROOT / "docs/run-card-S22-XB.json").write_text(json.dumps(card, indent=1) + "\n")
    (DOWNLOADS / f"{stem}.json").write_text(json.dumps({"name": stem, "note": note, "sha256": meta["sha256"], "verdict": card["verdict"],
                                                       "ok_to_download": ok_dl, "ok_to_submit": ok_sub, "failed_gates": failed,
                                                       "validator": validator}, indent=1) + "\n")
    print(json.dumps({"verdict": card["verdict"], "ok_to_download": ok_dl, "ok_to_submit": ok_sub, "failed_gates": failed,
                      "holdout_dti_capped": h_cap["dti"], "lfi_ridge10": cand_proj, "best_comparator": best_comp_name,
                      "max_competitive_overlap": comp["max_3px_overlap_all_competitive"], "file": out_tif.name}, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["capped", "final", "posthoc"])
    args = ap.parse_args()
    return {"capped": stage_capped, "final": stage_final, "posthoc": stage_posthoc}[args.stage]()


if __name__ == "__main__":
    raise SystemExit(main())
