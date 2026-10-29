#!/usr/bin/env python3
"""S27 post-hoc diagnostics (computed AFTER the candidate raster was frozen).

1) Blind USGS SGMC off-catalogue DTI at min_cat_dist_px 3 and 5 via the shared
   scripts/evaluate_holdout.score_off_catalogue_sgmc. The 5 px (500 m) variant
   is preregistered gate G5; SGMC is report-only proxy truth, never a
   leaderboard estimate.
2) LFI leaderboard-feedback inversion REFITTED in this session on the restored
   anchor set (scripts/run_lfi.py), then applied to the frozen candidate and
   comparators. Every output is MODEL_PROJECTION_NOT_A_SCORE fitted to
   USER-REPORTED anchors. The candidate was not built or selected with LFI.
3) Dot-geography profile (distance-to-catalogue, distance-to-H19-5-network,
   consensus votes) for candidate vs S25 candidate vs R0 vs S21-PDWC.

Finalizes docs/s27/run-card.json: folds G5 into the frozen gate table and sets
the verdict by the preregistered rule. Creates no candidate; uses no slot.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import numpy as np
import rasterio
from scipy import ndimage as ndi

from evaluate_holdout import score_off_catalogue_sgmc
from gems91 import lfi as L


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def run(cmd):
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    rc = json.loads((ROOT / "docs/s27/run-card.json").read_text())
    if rc.get("verdict") != "pending_diagnostics_G5":
        raise RuntimeError("S27 diagnostics already finalized; no implicit rerun")
    cand_rel = rc["artifact"]["tif"]
    if sha(ROOT / cand_rel) != rc["raster_sha256"]:
        raise ValueError("candidate raster changed since packaging")
    man = {r["id"]: r for r in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]}
    for rid in ("sample_submission", "existing_faults", "sgmc_faults_control", "parent_r0_zeros"):
        p = ROOT / "data" / man[rid]["local_subpath"]
        if sha(p) != man[rid]["sha256"]:
            raise ValueError(f"pinned input drift: {rid}")
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        catalogue = ds.read(1)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1)

    targets = [
        ("s27_fabricfar_candidate", cand_rel),
        ("s25_fabric_e2_candidate",
         "docs/downloads/gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif"),
        ("parent_r0_gemsdoe32", "data/" + man["parent_r0_zeros"]["local_subpath"]),
        ("s21_pdwc_e3", "docs/downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif"),
    ]
    nine = json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]
    for s in nine:
        if sha(ROOT / s["local_path"]) != s["sha256"]:
            raise ValueError(f"nine-leader bytes drift: {s['site']}")
        targets.append((f"nine_{s['site'].lower()}", s["local_path"]))

    def read_pred(rel):
        with rasterio.open(ROOT / rel) as ds:
            if ds.shape != footprint.shape or str(ds.crs) != "EPSG:32611" or ds.count != 1:
                raise ValueError(f"grid mismatch: {rel}")
            return ds.read(1)

    # ---- SGMC at 3 px and 5 px (G5 is the 5 px / 500 m variant) ----
    sgmc_by_dist = {3: [], 5: []}
    preds = {}
    for name, rel in targets:
        pred = read_pred(rel)
        preds[name] = pred
        for dist in (3, 5):
            res = score_off_catalogue_sgmc(pred, sgmc, catalogue, footprint,
                                           min_cat_dist_px=float(dist))
            sgmc_by_dist[dist].append({"name": name, "path": rel, "sha256": sha(ROOT / rel),
                               "n_positive_pixels_inside": int(((np.nan_to_num(pred) > 0) & footprint).sum()),
                               **res})
        print(f"SGMC>3px {sgmc_by_dist[3][-1]['dti']:.6f}  SGMC>5px {sgmc_by_dist[5][-1]['dti']:.6f}  {name}", flush=True)
    cand5 = next(r for r in sgmc_by_dist[5] if r["name"] == "s27_fabricfar_candidate")
    r0_5 = next(r for r in sgmc_by_dist[5] if r["name"] == "parent_r0_gemsdoe32")
    g5_pass = bool(cand5["dti"] > r0_5["dti"])

    # ---- LFI refit (shared driver; two-pass aggregate for the consensus factor) ----
    work = ROOT / "work/lfi"
    py = sys.executable
    run([py, "scripts/run_lfi.py", "aggregate"])
    (work / "anchors_base.json").write_bytes((work / "anchors.json").read_bytes())
    run([py, "scripts/run_lfi.py", "aggregate"])
    run([py, "scripts/run_lfi.py", "fit", "--ridge", "1"])
    run([py, "scripts/run_lfi.py", "fit", "--ridge", "10"])

    meta = json.loads((work / "anchors.json").read_text())
    used = [r for r in meta["rows"] if r.get("used")]
    anchor_set_hash = hashlib.sha256(
        "\n".join(sorted(f"{r['name']}|{r['sha256']}" for r in used)).encode()).hexdigest()
    z = np.load(work / "agg.npz")
    A, Lm = z["A"], z["L"]
    bins = np.load(work / "bins.npy")
    nb = int(meta["n_bins"])
    pnames = meta["param_names"]
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    cat_mask = (np.nan_to_num(catalogue) > 0) & footprint
    fits = {}
    for tag, fn in (("ridge1", "fit_r1.0_fNone.json"), ("ridge10", "fit_r10.0_fNone.json")):
        fd = json.loads((work / fn).read_text())
        if set(fd["theta"]) != set(pnames):
            raise ValueError("LFI param-name mismatch between fit and design")
        fits[tag] = {"theta": np.array([fd["theta"][k] for k in pnames], dtype=np.float64),
                     "f": float(fd["f"]), "rmse_loso": fd["rmse_loso"],
                     "spearman_loso": fd["spearman_loso"], "pearson_loso": fd["pearson_loso"],
                     "n_anchors": fd["n_anchors"], "fit_file": f"work/lfi/{fn}"}

    lfi_rows = []
    for name, rel in targets:
        a = np.where(footprint, np.nan_to_num(preds[name].astype(np.float64), nan=0.0), 0.0)
        if a.min() < 0 or a.max() > 1:
            raise ValueError(f"values outside [0,1]: {rel}")
        N_c, C_c = L.aggregate(a.astype(np.float32), bins, nb, cat_mask)
        row = {"name": name, "path": rel, "sha256": sha(ROOT / rel),
               "label_class": "MODEL_PROJECTION_NOT_A_SCORE"}
        for tag, fd in fits.items():
            y_hat, _ = L.predict(fd["theta"], fd["f"], X, N_c[None, :], C_c[None, :], A)
            row[tag] = round(float(y_hat[0]), 5)
        lfi_rows.append(row)
        print(f"LFI {name}: ridge1={row['ridge1']} ridge10={row['ridge10']}", flush=True)

    # ---- Dot geography profile ----
    net = (np.nan_to_num(read_pred("data/fleet_registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif")) > 0) & footprint
    dcat = ndi.distance_transform_edt(~cat_mask)
    dnet = ndi.distance_transform_edt(~net)
    votes = np.load(work / "cons_votes.npy")
    dcat_edges = [(0, 3), (3, 5), (5, 10), (10, 20), (20, 40), (40, float("inf"))]
    dnet_edges = [(0, 1.5), (1.5, 3), (3, 6), (6, float("inf"))]

    def hist(v, edges):
        return {f"({lo},{hi}]": round(float(((v > lo) & (v <= hi)).mean()), 4)
                for lo, hi in edges}

    profile_rows = []
    for name in ("s27_fabricfar_candidate", "s25_fabric_e2_candidate",
                 "parent_r0_gemsdoe32", "s21_pdwc_e3"):
        rel = next(r for n, r in targets if n == name)
        dots = (np.nan_to_num(preds[name]) > 0) & footprint
        dc, dn, vt = dcat[dots], dnet[dots], votes[dots]
        profile_rows.append({
            "name": name, "path": rel, "sha256": sha(ROOT / rel),
            "n_dots": int(dots.sum()),
            "dcat_px_hist": hist(dc, dcat_edges),
            "dcat_px_median": round(float(np.median(dc)), 3),
            "dnet_px_hist": hist(dn, dnet_edges),
            "dnet_px_median": round(float(np.median(dn)), 3),
            "cons_votes_hist": {"0": round(float((vt == 0).mean()), 4),
                                "1": round(float((vt == 1).mean()), 4),
                                "2": round(float((vt == 2).mean()), 4),
                                ">=3": round(float((vt >= 3).mean()), 4)}})
        print(f"profile {name}: median dcat {profile_rows[-1]['dcat_px_median']} px", flush=True)

    out = {
        "label": ("POST-HOC DIAGNOSTICS — SGMC proxy control + LFI MODEL projections. "
                  "No ORGANIZER-CONFIRMED score exists for any row."),
        "candidate": {"name": "s27_fabricfar_candidate", "tif": cand_rel,
                      "sha256": rc["raster_sha256"],
                      "organizer_confirmed_score": None},
        "sgmc": {"label": "SGMC-OFFCAT-CONTROL-DTI (report-only; not HOLDOUT-DTI)",
                 "evaluator": "scripts/evaluate_holdout.score_off_catalogue_sgmc",
                 "input_sha256": man["sgmc_faults_control"]["sha256"],
                 "rows_min_cat_dist_3px": sorted(sgmc_by_dist[3], key=lambda r: -r["dti"]),
                 "rows_min_cat_dist_5px": sorted(sgmc_by_dist[5], key=lambda r: -r["dti"]),
                 "gate_G5": {"definition": "candidate SGMC DTI (min_cat_dist_px=5) > R0 at identical parameter",
                             "candidate_dti_5px": cand5["dti"], "r0_dti_5px": r0_5["dti"],
                             "pass": g5_pass}},
        "lfi": {"label_class": "MODEL_PROJECTION_NOT_A_SCORE",
                "method": ("Leaderboard-feedback inversion (src/gems91/lfi.py) refitted this "
                           "session via scripts/run_lfi.py on restored USER-REPORTED anchors; "
                           "leave-one-site-out diagnostics from the fit driver."),
                "anchor_set": {"n_used": len(used), "n_rows": len(meta["rows"]),
                               "set_sha256": anchor_set_hash,
                               "matches_file": "registry/lfi_anchor_matches.json"},
                "fits": {k: {kk: v[kk] for kk in ("f", "rmse_loso", "spearman_loso",
                                                  "pearson_loso", "n_anchors", "fit_file")}
                         for k, v in fits.items()},
                "caveats": [
                    "A projection is never a score (protocol rule 3). The S27 candidate was "
                    "NOT built, selected or tuned with LFI (emission quotas were frozen in "
                    "the preregistration), which removes the optimizer's-curse bias of "
                    "maximizing the estimating model, but not model error itself.",
                    "Public-subset fit need not transfer to private chunks.",
                    "Anchors are USER-REPORTED values from sibling sites, not receipts."],
                "rows": sorted(lfi_rows, key=lambda r: -r["ridge1"])},
        "dot_profile": {"label": "DESCRIPTIVE DOT PROFILE (not a score)", "rows": profile_rows},
    }
    p = ROOT / "docs/s27/diagnostics.json"
    p.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print("wrote", p)

    # ---- Finalize run-card verdict by the preregistered rule ----
    gates = dict(rc["gates_at_packaging"])
    gates["G5_sgmc"] = g5_pass
    promote = bool(gates["G1_canary"] and gates["G2_surface"] and gates["G3_dots_nine"]
                   and gates["G3_dots_competitive"] and gates["G4_holdout_beats_ctrl_ci95"]
                   and gates["G5_sgmc"] and gates["G6_format"])
    cand_lfi = next(r for r in lfi_rows if r["name"] == "s27_fabricfar_candidate")
    rc["gates_final"] = gates
    rc["gate_G3_all_scope_note"] = (
        "G3 in the all-including-dense-blankets scope fails against the 206,895-dot "
        "calibration lattice; the capacity bound in correlation_overlap_vs_registry "
        "proves >=82.34% overlap is forced at this 37,654-dot budget for ANY raster. "
        "Reported, never exempted or evaded; coordinator scope policy still required.")
    rc["gate_G4_note"] = (
        "All three emission arms are mathematically identical inside the v3 holdout "
        "folds (zero visible catalogue pixels inside every test quadrant; median "
        "distance-to-visible 234-808 px), so paired HOLDOUT-DTI delta is exactly 0 "
        "by instrument construction. See docs/s27/holdout.json and REVIEW.md.")
    rc["sgmc_gate_G5"] = out["sgmc"]["gate_G5"]
    rc["lfi_model_projection_not_a_score"] = {
        "ridge1": cand_lfi["ridge1"], "ridge10": cand_lfi["ridge10"],
        "anchor_set_sha256": anchor_set_hash,
        "fit_loso": {k: {"rmse": v["rmse_loso"], "spearman": v["spearman_loso"]}
                     for k, v in fits.items()},
        "diagnostics_file": "docs/s27/diagnostics.json"}
    rc["post_hoc_diagnostics_file"] = "docs/s27/diagnostics.json"
    rc["verdict"] = "promote" if promote else "negative"
    rc["ok_to_submit"] = False  # slot selection is a separate selector step (rule 6)
    rc["ok_to_download"] = True
    rc["ok_to_download_scope"] = "research only"
    p2 = ROOT / "docs/s27/run-card.json"
    p2.write_text(json.dumps(rc, indent=2, allow_nan=False) + "\n")
    print(f"finalized run card: verdict={rc['verdict']} G5={'PASS' if g5_pass else 'FAIL'} "
          f"LFI ridge1={cand_lfi['ridge1']} ridge10={cand_lfi['ridge10']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
