#!/usr/bin/env python3
"""S28-VSD post-hoc diagnostics (run strictly AFTER the candidate raster is frozen).

Outputs docs/s28-vsd/diagnostics.json with, all explicitly labelled:
  1. SGMC-OFFCAT-CONTROL-DTI — blind USGS SGMC off-catalogue control via the
     shared scripts/evaluate_holdout.score_off_catalogue_sgmc (total + >500 m
     far-field), a report-only proxy, NEVER a leaderboard score.
  2. LFI MODEL_PROJECTION_NOT_A_SCORE — leaderboard-feedback inversion refit on
     the restored USER-REPORTED anchors (ridge 1 and 10), projected on this
     candidate's dots. A projection is never written as a score.
  3. Radial dot-geography profile vs catalogue and h19-5 network.

Creates NO candidate and spends ZERO weekly submission slots.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT)]

import numpy as np
import rasterio
from scipy import ndimage as ndi

import run_lfi as R
from gems91 import lfi as L
from vendor.gems57 import grid as G

OUT = ROOT / "docs/s28-vsd"
WORK = ROOT / "work/lfi"


def main() -> int:
    card = json.loads((OUT / "run-card.json").read_text())
    pred_path = ROOT / card["raster_file"]
    g = G.load_grid(ROOT / "data/official")

    with rasterio.open(pred_path) as ds:
        assert ds.count == 1 and (ds.height, ds.width) == g.shape
        a = ds.read(1)
    p = np.where(np.isfinite(a), a, 0.0).astype(np.float32)
    p = np.where(g.footprint, p, 0.0)
    assert p.min() >= 0.0 and p.max() <= 1.0
    pos = p > 0

    # ---- 1. SGMC off-catalogue blind control --------------------------------
    import dti as D  # shared canonical DTI (scripts/evaluate_holdout delegates here too)
    import evaluate_holdout as LEH

    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sg = ds.read(1)
    sgmc_mask = (np.nan_to_num(sg, nan=0.0) > 0) & g.footprint
    res_total = LEH.score_off_catalogue_sgmc(p, sgmc_mask, g.catalogue, g.footprint)
    cat_d = ndi.distance_transform_edt(~((np.nan_to_num(g.catalogue, nan=0.0) > 0) & g.footprint))
    far = sgmc_mask & (cat_d > 5.0)
    res_far = LEH.score_off_catalogue_sgmc(p, far, g.catalogue, g.footprint)
    sgmc_block = {
        "metric_label": "SGMC-OFFCAT-CONTROL-DTI (blind independent control; not a leaderboard score)",
        "total": res_total,
        "far_field_gt500m": res_far,
    }

    # ---- 2. LFI projection ---------------------------------------------------
    z = np.load(WORK / "agg.npz")
    meta = json.loads((WORK / "anchors.json").read_text())
    nb = meta["n_bins"]
    bins = np.load(WORK / "bins.npy")
    N, C = L.aggregate(p, bins, nb, g.catalogue)
    lm = z["L"] if "L" in z.files else z["Lm"]
    X = np.hstack([np.ones((lm.shape[0], 1)), lm])
    projections = {}
    for ridge, tag in ((1.0, "fit_r1.0_fNone"), (10.0, "fit_r10.0_fNone")):
        fjson = WORK / f"{tag}.json"
        theta_np = WORK / f"{tag}_theta.npy"
        if not fjson.is_file() or not theta_np.is_file():
            continue
        theta = np.load(theta_np)
        f = float(theta[-1])
        pr, parts = L.predict(theta[:-1], f, X, N[None, :], C[None, :], z["A"])
        projections[f"ridge{int(ridge)}"] = {
            "label": "MODEL_PROJECTION_NOT_A_SCORE",
            "projected_public_dti": float(np.asarray(pr).ravel()[0]),
            "f_public_fraction": f,
            "fit_rmse_in_sample": json.loads(fjson.read_text())["rmse_in_sample"],
            "fit_rmse_loso": json.loads(fjson.read_text())["rmse_loso"],
        }

    # ---- 3. dot geography ----------------------------------------------------
    net = (np.nan_to_num(_read(R.NET), nan=0.0) > 0) & g.footprint
    d_cat = ndi.distance_transform_edt(~((np.nan_to_num(g.catalogue, nan=0.0) > 0) & g.footprint))
    d_net = ndi.distance_transform_edt(~net)
    prof = {
        "n_dots": int(pos.sum()),
        "median_px_to_catalogue": float(np.median(d_cat[pos])),
        "frac_within_2px_catalogue": float((d_cat[pos] <= 2.01).mean()),
        "median_px_to_h195_net": float(np.median(d_net[pos])),
        "frac_within_1p5px_h195": float((d_net[pos] <= 1.51).mean()),
    }

    out = {
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "raster": card["raster_file"],
        "raster_sha256": card["raster_sha256"],
        "sgmc_off_catalogue_control": sgmc_block,
        "lfi": projections,
        "dot_geography": prof,
        "evidence_policy": "every number here is a MODEL projection or a blind control, never a leaderboard score",
    }
    (OUT / "diagnostics.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: out[k] for k in ("lfi", "dot_geography")}, indent=1))
    print("SGMC off-cat total:", res_total.get("dti"), "far:", res_far.get("dti"))
    return 0


def _read(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        return ds.read(1)


if __name__ == "__main__":
    raise SystemExit(main())
