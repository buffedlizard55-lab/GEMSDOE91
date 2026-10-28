#!/usr/bin/env python3
"""S25 post-hoc diagnostics (computed AFTER the candidate raster was frozen).

1) Blind USGS SGMC off-catalogue DTI via the shared
   scripts/evaluate_holdout.score_off_catalogue_sgmc. Report-only proxy
   truth; never a gate, never a leaderboard estimate.
2) LFI leaderboard-feedback inversion REFITTED in this session on the restored
   anchor set (scripts/run_lfi.py aggregate x2 + fit, ridge 1 and 10), then
   applied to the candidate and comparators. Every output is a
   MODEL_PROJECTION_NOT_A_SCORE fitted to USER-REPORTED anchors. The
   anchor-set hash is recorded (IR-S22XB-03).

Output: docs/s25/diagnostics.json. Uses no submission slot.
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
    rc = json.loads((ROOT / "docs/s25/run-card.json").read_text())
    cand_rel = rc["artifact"]["tif"]
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
        ("s25_fabric_e2_candidate", cand_rel),
        ("parent_r0_gemsdoe32", "data/" + man["parent_r0_zeros"]["local_subpath"]),
        ("s21_pdwc_e3", "docs/downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif"),
        ("s24_cckm_e2", "docs/downloads/gems91-s24-cckm-e2-37654dots-20261027T190354Z-d69650bd-zeros.tif"),
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

    # ---- SGMC ----
    sgmc_rows = []
    preds = {}
    for name, rel in targets:
        pred = read_pred(rel)
        preds[name] = pred
        res = score_off_catalogue_sgmc(pred, sgmc, catalogue, footprint)
        sgmc_rows.append({"name": name, "path": rel, "sha256": sha(ROOT / rel),
                          "n_positive_pixels_inside": int(((np.nan_to_num(pred) > 0) & footprint).sum()),
                          **res})
        print(f"SGMC {res['dti']:.6f}  {name}", flush=True)

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

    out = {
        "label": ("POST-HOC DIAGNOSTICS — SGMC proxy control + LFI MODEL projections. "
                  "No ORGANIZER-CONFIRMED score exists for any row."),
        "candidate": {"name": "s25_fabric_e2_candidate", "tif": cand_rel,
                      "sha256": rc["raster_sha256"],
                      "organizer_confirmed_score": None},
        "sgmc": {"label": "SGMC-OFFCAT-CONTROL-DTI (report-only; not HOLDOUT-DTI)",
                 "evaluator": "scripts/evaluate_holdout.score_off_catalogue_sgmc",
                 "input_sha256": man["sgmc_faults_control"]["sha256"],
                 "rows": sorted(sgmc_rows, key=lambda r: -r["dti"])},
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
                    "A projection is never a score (protocol rule 3). LOSO RMSE ~0.02 on "
                    "anchors; rasters built with the model in view are optimistic — the S25 "
                    "candidate was NOT built or selected with LFI (selection used HOLDOUT-DTI "
                    "only), which removes that specific bias but not model error.",
                    "Public-subset fit need not transfer to private chunks (Rules 3.6.2).",
                    "Anchors are USER-REPORTED values from sibling sites, not receipts."],
                "rows": sorted(lfi_rows, key=lambda r: -r["ridge1"])},
    }
    p = ROOT / "docs/s25/diagnostics.json"
    p.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
