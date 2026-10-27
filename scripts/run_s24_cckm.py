#!/usr/bin/env python3
"""S24-CCKM experiments (docs/s24/preregistration.md; E2: preregistration-e2.md).

Defaults reproduce E1 exactly (20,000 dots). E2 is the same code path invoked
with --exp-id e2 --budget 37654 --out-dir docs/s24/e2 --extra-budget-arm 20000
so the budget is the only changed variable. Reuses the shared template only:
vendor/gems57 spatial folds + evaluate_holdout + submission_writer,
gems91.novelty duplicate instruments, gems91.pdwc21 emitter, gems91.capacity
bound. Data restoration is separate and SHA-checked here before any byte is
read. Refuses implicit reruns. No submission slot is used or approved here.
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
from sklearn.metrics import roc_auc_score

from gems91 import cckm24
from gems91.capacity import capacity_bound
from gems91.io import dot_digest
from gems91.novelty import SurfaceProbe, dot_check
from gems91.pdwc21 import emit_dots_nms
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s24"
WORK = ROOT / "work/s24"
BUDGET = 20_000
SPACING_PX = 3.05
COLLAR_PX = 3.05
NOTE = "S24 CCKM cross-contact kurtosis B14/B13 20k dots; research only, not slot-approved"
assert len(NOTE) <= 140


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def verify_pinned_inputs():
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        if row["id"] in {"sample_submission", "existing_faults", "training_features", "parent_r0_zeros"}:
            p = ROOT / "data" / row["local_subpath"]
            if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
                raise ValueError(f"pinned input absent or drifted: {row['id']}")
            checked[row["id"]] = {"path": "data/" + row["local_subpath"], "sha256": row["sha256"],
                                  "bytes": row["bytes"]}
    return checked


def freeze_references(g):
    """Pin every comparison raster by SHA *before* candidate construction."""
    entries = {}  # sha256 -> entry
    missing = []

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
        e["is_dense_lattice"] = "lattice" in Path(e["path"]).name.lower()
    result = {
        "frozen_before_candidate": True,
        "unique_byte_references": len(refs),
        "missing": missing,
        "organizer_complete_registry": False,
        "dense_reference_exemptions_in_data": False,
        "files": refs,
    }
    dump(OUT / "frozen-registry.json", result)
    return result, nine


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
    """Label-blind internal consistency of B13/B14 vs their derivative bands."""
    def valid(a):
        return fp & np.isfinite(a) & (np.abs(a.astype(np.float64)) < 1e30)

    def grad_corr(field, deriv, mode):
        v = valid(field) & valid(deriv)
        ve = ndi.binary_erosion(v, iterations=2)
        f = np.where(v, np.asarray(field, np.float64), 0.0)
        gy, gx = np.gradient(f)
        if mode == "mag":
            g = np.hypot(gy, gx)
            return float(np.corrcoef(np.abs(np.asarray(deriv, np.float64)[ve]), g[ve])[0, 1]), int(ve.sum())
        return float(np.corrcoef(np.asarray(deriv, np.float64)[ve], gx[ve])[0, 1]), int(ve.sum())

    b14, b13 = ds.read(14), ds.read(13)
    b03, b05, b18 = ds.read(3), ds.read(5), ds.read(18)
    report = {"descriptions": {str(i): ds.descriptions[i - 1] for i in (3, 5, 13, 14, 18)},
              "nodata_tag": repr(ds.nodata)}
    for name, a in (("B13", b13), ("B14", b14)):
        v = valid(a)
        av = np.asarray(a, np.float64)[v]
        report[name] = {"valid_pixels": int(v.sum()), "invalid_inside_footprint": int((fp & ~v).sum()),
                        "min": float(av.min()), "median": float(np.median(av)), "max": float(av.max())}
    r, n = grad_corr(b14, b03, "mag")
    report["corr_B03_vs_abs_grad_B14"] = {"r": r, "n": n}
    r, n = grad_corr(b13, b05, "mag")
    report["corr_B05_vs_abs_grad_B13"] = {"r": r, "n": n}
    r, n = grad_corr(b13, b18, "gx")
    report["corr_B18_vs_dx_B13"] = {"r": r, "n": n}
    report["interpretation"] = ("Internal derivative consistency supports, but does not externally "
                                "authenticate, the embedded B13/B14 identities. Gradients were scored "
                                "only on pixels eroded 2px from any invalid cell; no filling was used "
                                "in features.")
    dump(OUT / "band-identity.json", report)
    return report


def allocate(total_budget, areas):
    budgets, remaining = [], total_budget
    for i, a in enumerate(areas):
        q = int(round(total_budget * a / sum(areas))) if i < len(areas) - 1 else remaining
        budgets.append(q)
        remaining -= q
    return budgets


def main(argv=None) -> int:
    global OUT, WORK, BUDGET, NOTE
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exp-id", default="e1")
    ap.add_argument("--budget", type=int, default=BUDGET)
    ap.add_argument("--out-dir", type=Path, default=OUT)
    ap.add_argument("--work-dir", type=Path, default=WORK)
    ap.add_argument("--extra-budget-arm", type=int, default=None,
                    help="also score the candidate surface at this budget (paired)")
    ap.add_argument("--experiments-run", type=int, default=1)
    args = ap.parse_args(argv)
    OUT, WORK, BUDGET = args.out_dir, args.work_dir, args.budget
    EXP = args.exp_id
    CAND = f"cckm_{EXP}"
    NOTE = (f"S24 CCKM cross-contact kurtosis B14/B13 {BUDGET // 1000}k dots; "
            f"research only, not slot-approved")
    assert len(NOTE) <= 140
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    if (OUT / "run-card.json").exists():
        raise RuntimeError("S24-CCKM already recorded; no implicit rerun or tuning")
    prereg_sha = {"preregistration.md": sha(ROOT / "docs/s24/preregistration.md")}
    _amend = ROOT / "docs/s24/preregistration-e2.md"
    if EXP != "e1" and _amend.is_file():
        prereg_sha["preregistration-e2.md"] = sha(_amend)
    if EXP == "e1":
        prereg_sha = prereg_sha["preregistration.md"]
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    refs, nine_sites = freeze_references(g)

    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform:
            raise ValueError("feature grid mismatch")
        identity = band_identity(ds, g.footprint)
        raw_tmi, raw_grav = ds.read(14), ds.read(13)
    feat, support, meta = cckm24.features(raw_tmi, raw_grav, g.footprint)
    del raw_tmi, raw_grav
    dump(OUT / "feature-receipt.json", meta)

    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fold_receipts = [f["receipt"] for f in folds]

    # --- Rule 4 leakage canary: every feature alone, per fold ---
    canaries, max_sym, worst = [], 0.0, None
    for name, arr in feat.items():
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pos = np.nonzero(fold["truth"] & valid)
            neg = np.nonzero(~fold["truth"] & valid)
            sel = np.arange(len(neg[0]))[::4]
            y = np.concatenate([np.ones(len(pos[0])), np.zeros(len(sel))])
            s = np.concatenate([arr[pos], arr[neg[0][sel], neg[1][sel]]])
            auc = float(roc_auc_score(y, s)) if len(np.unique(y)) == 2 else 0.5
            sym = max(auc, 1.0 - auc)
            canaries.append({"feature": name, "fold": fidx, "auc": auc, "symmetric_auc": sym,
                             "n_positive": int(len(pos[0])), "n_negative_sampled": int(len(sel))})
            if sym > max_sym:
                max_sym, worst = sym, f"{name} fold{fidx}"
    canary_pass = bool(max_sym <= 0.90)
    dump(OUT / "canaries.json", {"max_symmetric_auc": float(max_sym), "worst": worst,
                                 "all_pass": canary_pass, "threshold": 0.90,
                                 "evaluator_version": EH.VERSION, "canaries": canaries})
    if not canary_pass:
        card = {"verdict": "negative", "stop_reason": "leakage canary > 0.90",
                "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
                "leakage_canary": {"max_symmetric_auc": float(max_sym), "worst": worst}}
        dump(OUT / "run-card.json", card)
        print(json.dumps(card, indent=2))
        return 2

    # --- Rule 1 phase 1: surface rank correlation before placement ---
    probe = SurfaceProbe(feat["surface"], g.footprint)
    surface_checks, max_rho, max_rho_path = [], 0.0, None
    for entry in refs["files"]:
        row = {"path": entry["path"], "tags": entry["tags"], "sites": entry["sites"],
               "is_dense_lattice": entry["is_dense_lattice"]}
        try:
            res = probe.compare(reference_array(entry, g))
            row.update(res)
            rho = res.get("rank_correlation")
            if rho is not None and abs(rho) > max_rho:
                max_rho, max_rho_path = abs(rho), entry["path"]
        except Exception as exc:  # recorded, never silently treated as a pass
            row.update({"status": "UNVERIFIED", "rank_correlation": None, "error": str(exc)})
        surface_checks.append(row)
    surface_verified = sum(1 for r in surface_checks if r.get("rank_correlation") is not None)
    surface_pass = bool(max_rho <= 0.90)
    dump(OUT / "surface-checks.json", {
        "max_abs_rho": float(max_rho), "closest": max_rho_path, "pass": surface_pass,
        "references_checked": len(surface_checks), "references_verified": surface_verified,
        "checks": surface_checks})
    if not surface_pass:
        card = {"verdict": "negative", "stop_reason": "surface DUPLICATE stop before placement",
                "ok_to_submit": False, "ok_to_download": False, "raster_sha256": None,
                "surface_max_abs_rho": float(max_rho), "closest": max_rho_path}
        dump(OUT / "run-card.json", card)
        print(json.dumps(card, indent=2))
        return 3

    # --- Holdout: paired arms on identical folds/budgets ---
    surfaces = {
        CAND: feat["surface"],
        "control_gravgrad": feat["gravity_grad_rank"],
        "control_kurtcontrast": feat["kurtosis_contrast_rank"],
    }
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)
    terms_by_arm, per_fold = {}, []

    def score_emission_arm(arm, surf, arm_budgets):
        total_terms = None
        for fidx, fold in enumerate(folds):
            pred = emit_dots_nms(surf, fold["visible"], g.footprint & fold["region"],
                                 budget=arm_budgets[fidx], collar_px=COLLAR_PX, min_spacing_px=SPACING_PX)
            res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200,
                                     origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            per_fold.append({"arm": arm, "fold": fidx, "budget": arm_budgets[fidx],
                             "n_truth": int(res["n_truth"]), "n_emitted": int(res["n_emitted"]),
                             "tpw": float(res["tpw"]), "fpw": float(res["fpw"]), "fnw": float(res["fnw"])})
        terms_by_arm[arm] = total_terms

    for arm, surf in surfaces.items():
        score_emission_arm(arm, surf, budgets)
    if args.extra_budget_arm:
        score_emission_arm(f"cckm_at_{args.extra_budget_arm}", feat["surface"],
                           allocate(args.extra_budget_arm, areas))
    if EXP == "e1":
        # External R0 reference (different budget and full-catalogue collar;
        # structurally handicapped here, not a matched control).
        with rasterio.open(ROOT / inputs["parent_r0_zeros"]["path"]) as ds:
            r0 = ds.read(1)
        if not np.isfinite(r0).all() or (r0 < 0).any() or (r0 > 1).any():
            raise ValueError("R0 reference not finite in [0,1]")
        total_terms = None
        for fidx, fold in enumerate(folds):
            res, terms = EH.evaluate(r0.astype(np.float32), fold, g.footprint, block_side=200,
                                     origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            per_fold.append({"arm": "r0_reference_nonmatched_budget", "fold": fidx,
                             "budget": None, "n_truth": int(res["n_truth"]),
                             "n_emitted": int(res["n_emitted"]), "tpw": float(res["tpw"]),
                             "fpw": float(res["fpw"]), "fnw": float(res["fnw"])})
        terms_by_arm["r0_reference_nonmatched_budget"] = total_terms
    np.savez_compressed(WORK / "holdout-terms.npz", **terms_by_arm)
    pooled = EH.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate=CAND)
    pooled["per_fold"] = per_fold
    pooled["fold_receipts"] = fold_receipts
    pooled["matched_controls"] = ["control_gravgrad", "control_kurtcontrast"]
    pooled["nonmatched_reference_note"] = (
        "E1 only: r0_reference_nonmatched_budget carries 37,654 dots vs 20,000 in matched "
        "arms and its collar used the full catalogue incl. withheld segments; no paired "
        "superiority claim is made against it." if EXP == "e1" else
        "R0 not re-scored in E2 (see preregistration-e2.md).")
    dump(OUT / "holdout.json", pooled)

    # --- Final full-grid emission + Rule 1 phase 2 (final dots) ---
    final = emit_dots_nms(feat["surface"], g.catalogue, g.footprint,
                          budget=BUDGET, collar_px=COLLAR_PX, min_spacing_px=SPACING_PX)
    n_final = int((final > 0).sum())
    if n_final != BUDGET:
        raise RuntimeError(f"final dot count {n_final} != budget {BUDGET}")
    dot_checks, max_ov, max_ov_path = [], 0.0, None
    nine_checks, lattice_checks = [], []
    for entry in refs["files"]:
        row = {"path": entry["path"], "tags": entry["tags"], "sites": entry["sites"],
               "is_dense_lattice": entry["is_dense_lattice"]}
        try:
            res = dot_check(final, reference_array(entry, g), g.footprint)
            row.update({k: (float(v) if isinstance(v, float) else v) for k, v in res.items()})
            ov = res.get("overlap_within_3px")
            if ov is not None and ov > max_ov:
                max_ov, max_ov_path = float(ov), entry["path"]
        except Exception as exc:
            row.update({"status": "UNVERIFIED", "overlap_within_3px": None, "error": str(exc)})
        dot_checks.append(row)
        if entry["sites"]:
            nine_checks.append(row)
        if entry["is_dense_lattice"]:
            lattice_checks.append(row)
    non_lattice = [r for r in dot_checks if not r["is_dense_lattice"] and r.get("overlap_within_3px") is not None]
    nine_max = max((r["overlap_within_3px"] for r in nine_checks if r.get("overlap_within_3px") is not None),
                   default=None)
    dump(OUT / "final-dot-checks.json", {
        "max_3px_overlap_all_references": float(max_ov), "closest_all": max_ov_path,
        "max_3px_overlap_nine_leaders": nine_max,
        "max_3px_overlap_non_lattice": max((r["overlap_within_3px"] for r in non_lattice), default=None),
        "lattice_checks": lattice_checks, "nine_leader_checks": nine_checks,
        "references_checked": len(dot_checks), "checks": dot_checks})

    # Dense-lattice geometric capacity witness at this budget.
    with rasterio.open(ROOT / "data/fleet_registry/calib_r13lattice_00904.tif") as ds:
        lat = np.isfinite(ds.read(1)) & (ds.read(1) > 0) & g.footprint
    capacity = capacity_bound(g.footprint, lat, BUDGET)

    # --- Package with the shared writer; independent re-read afterwards ---
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final > 0)[:8]
    tif_name = f"gems91-s24-cckm-{EXP}-{BUDGET}dots-{stamp}-{short}-zeros.tif"
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

    # --- Verdict (preregistered) ---
    controls = ["control_gravgrad", "control_kurtcontrast"]
    best_control = max(controls, key=lambda k: pooled["scores"][k]["dti"])
    paired = pooled["paired_differences"].get(best_control, {})
    beats_control = bool(paired.get("ci95", [0.0, 0.0])[0] > 0)
    dots_pass_all = bool(max_ov <= 0.70)
    dots_pass_nine = bool(nine_max is not None and nine_max <= 0.70)
    validator_pass = bool(local_validation["all_checks_passed"] and reread["all_finite"]
                          and reread["on_catalogue"] == 0 and reread["outside_footprint_positive"] == 0)
    promote = bool(canary_pass and surface_pass and dots_pass_all and beats_control and validator_pass)
    cand = pooled["scores"][CAND]
    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "lane": "S24-CCKM (self-assigned; no supplied method paragraph)",
        "preregistration": {"path": "docs/s24/preregistration.md", "sha256": prereg_sha},
        "hypothesis": "Buried faults juxtapose magnetically different basement across a gravity "
                      "contact, so the kurtosis of high-pass B14 texture changes across the "
                      "B13 gradient normal at contacts with strong |grad B13|.",
        "mechanism": "Masked 15px-window excess kurtosis of B14 residual (sigma 4px background), "
                     "sampled +/-9px along the B13 gradient normal; surface = "
                     f"sqrt(rank|K+ - K-| * rank|grad B13|); {BUDGET:,} dots, 3.05px spacing/collar.",
        "named_non_fault_mimic": "Unfaulted intrusive/volcanic contacts, lava-flow margins, and "
                                 "GeoDAWN survey seams.",
        "holdout": {"label": "HOLDOUT-DTI", "evaluator_version": EH.VERSION,
                    "dti": cand["dti"], "ci95": cand["ci95"],
                    "n_withheld_positives": cand["withheld_positive_pixels"],
                    "best_matched_control": best_control,
                    "best_matched_control_dti": pooled["scores"][best_control]["dti"],
                    "paired_difference_vs_best_control": paired,
                    "beats_best_matched_control_ci95": beats_control,
                    "paired_difference_vs_extra_budget_arm": (
                        pooled["paired_differences"].get(f"cckm_at_{args.extra_budget_arm}")
                        if args.extra_budget_arm else None),
                    "extra_budget_arm_dti": (
                        pooled["scores"][f"cckm_at_{args.extra_budget_arm}"]["dti"]
                        if args.extra_budget_arm else None),
                    "r0_reference_nonmatched_budget_dti": (
                        pooled["scores"]["r0_reference_nonmatched_budget"]["dti"]
                        if "r0_reference_nonmatched_budget" in pooled["scores"] else None)},
        "leakage_canary": {"max_symmetric_auc": float(max_sym), "worst": worst, "pass": canary_pass},
        "correlation_overlap_vs_registry": {
            "surface_max_abs_rho": float(max_rho), "surface_closest": max_rho_path,
            "surface_pass_le_0.90": surface_pass,
            "final_dot_max_overlap_all": float(max_ov), "final_dot_closest_all": max_ov_path,
            "final_dot_max_overlap_nine_leaders": nine_max,
            "final_dot_pass_nine_le_0.70": dots_pass_nine,
            "final_dot_pass_all_incl_lattice_le_0.70": dots_pass_all,
            "lattice_capacity_bound_at_budget": capacity,
            "references_unique_bytes": len(refs["files"]),
            "references_missing": refs["missing"],
            "organizer_complete_registry": False},
        "band_identity": identity,
        "validator_output": {"local": local_validation, "independent_reread": reread,
                             "pass": validator_pass,
                             "scope": "local [0,1]/CRS/shape/transform preflight; not organizer acceptance"},
        "raster_sha256": tif_sha,
        "submission_name": tif_name[:-4],
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "artifact": {"tif": str(out_tif.relative_to(ROOT)), "zip": str(zip_path.relative_to(ROOT)),
                     "zip_sha256": writer_receipt["zip_sha256"], "n_dots": n_final},
        "organizer_confirmed_score": None,
        "estimated_leaderboard_score": None,
        "estimated_leaderboard_score_reason": "No authenticated receipt and no validated "
                                              "holdout-to-leaderboard calibration; HOLDOUT-DTI is "
                                              "not a leaderboard score.",
        "experiments_run": args.experiments_run, "max_experiments": 3,
        "elapsed_seconds": float(time.monotonic() - start),
        "submission_slots_used": 0,
        "ok_to_download": bool(validator_pass),
        "ok_to_download_scope": "research only" if validator_pass else "none",
        "ok_to_submit": False,
        "selector_review_required": True,
        "verdict": "promote" if promote else "negative",
        "inputs_verified": inputs,
    }
    dump(OUT / "run-card.json", run_card)
    copy_name = "docs/run-card-S24-CCKM.json" if EXP == "e1" else f"docs/run-card-S24-CCKM-{EXP.upper()}.json"
    dump(ROOT / copy_name, run_card)
    print(json.dumps({k: run_card[k] for k in ("verdict", "holdout", "leakage_canary",
                                               "correlation_overlap_vs_registry",
                                               "raster_sha256", "artifact", "ok_to_download",
                                               "ok_to_submit")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
