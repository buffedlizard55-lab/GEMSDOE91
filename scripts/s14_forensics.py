#!/usr/bin/env python3
"""Historical S14 forensics for the user-reported GEMSDOE32 h33-2-b2 0.2778 claim.

No organizer receipt is available; this script does not confirm the claim or its cause.
Re-scores the fleet ancestors + in-repo candidates with the SHARED evaluator
(scripts/evaluate_holdout.py, gems91-hide-recover-v1.0) and the blind SGMC
off-catalogue control, measures dot geometry (count, distance-to-catalogue,
spacing), and correlates each proxy with the organizer-confirmed scores
transcribed from the user's session prompt (labelled CLAIM-USER-REPORTED;
no receipt is pinned in this repo, see IR notes in output JSON).

No new metric is invented here (Protocol Rule 2).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate_holdout as EH  # noqa: E402

DATA = ROOT / "data"

# Organizer scores as reported in the session prompt (CLAIM-USER-REPORTED).
CLAIMED = {
    "parent_r0_zeros": 0.2778,
    "anc_h19_5": 0.1922,
    "anc_h19_4": 0.1894,
    "anc_h16_1": 0.1855,
    "anc_d1_5": 0.2477,
    "anc_d2_8": 0.2600,
    "anc_solo_d2_8": 0.2708,
}

PATHS = {
    "parent_r0_zeros": DATA / "registry/GEMSDOE32__h33-2-b2-zeros.tif",
    "anc_h19_5": DATA / "registry/calib_h195_01922.tif",
    "anc_h19_4": DATA / "registry/calib_h194_01894.tif",
    "anc_h16_1": DATA / "registry/calib_h161_01855.tif",
    "anc_d1_5": DATA / "registry/calib_d15_02477.tif",
    "anc_d2_8": DATA / "registry/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
    "anc_solo_d2_8": DATA / "registry/GEMSDOE28__h27-4-r1-solo-d2-8.tif",
    "s13_ptha_e3": ROOT / "docs/downloads/gems91-s13-ptha-e3-20261024T201500Z-660d645d-zeros.tif",
    "s12_spac_e3": ROOT / "docs/downloads/gems91-spac-e3-20261024T183000Z-a2740c89-zeros.tif",
    "denovo_hgbctx": ROOT / "docs/downloads/gems91-denovo-hgbctx-37654dots-s2.8-20261024-7941b7ab-zeros.tif",
    "asc91_e3": ROOT / "docs/downloads/gems91-asc91-e3-37654dots-s2p8-20261024-dc8e4d47-zeros.tif",
}


def load(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        return np.nan_to_num(ds.read(1).astype(np.float64), nan=0.0)


def main() -> int:
    with rasterio.open(DATA / "official/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(DATA / "official/existing_faults.tif") as ds:
        cat = (ds.read(1) > 0) & footprint
    with rasterio.open(DATA / "external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1)
    d_cat = ndi.distance_transform_edt(~cat)
    folds = EH.build_segment_buffered_folds(cat.astype(np.float32), footprint)
    print(f"folds built; withheld per fold: {[f.n_withheld for f in folds]}", flush=True)

    rows = {}
    for name, p in PATHS.items():
        if not p.is_file():
            print(f"SKIP {name}: {p} missing"); continue
        pred = load(p)
        dots = pred > 0
        ys, xs = np.nonzero(dots)
        vals = pred[dots]
        dc = d_cat[ys, xs]
        # median nearest-neighbour spacing on a subsample
        pts = np.column_stack([ys, xs]).astype(np.float64)
        if len(pts) > 2000:
            rng = np.random.default_rng(0)
            sub = pts[rng.choice(len(pts), 2000, replace=False)]
            dnn, _ = cKDTree(pts).query(sub, k=2)
            nn_med = float(np.median(dnn[:, 1]))
        else:
            nn_med = float("nan")
        hold = EH.score_pooled_holdout({f.fold_id: pred for f in folds}, folds, footprint, n_boot=200)
        hold11 = EH.score_pooled_holdout({f.fold_id: pred for f in folds}, folds, footprint,
                                         n_boot=200, mask_buffer_predictions=False)
        sg = EH.score_off_catalogue_sgmc(pred, sgmc, cat.astype(np.float32), footprint)
        rows[name] = {
            "path": str(p.relative_to(ROOT)),
            "organizer_claimed_user_reported": CLAIMED.get(name),
            "holdout_dti_fullmap_v10_halo": hold["holdout_dti"],
            "holdout_dti_fullmap_v11_nohalo": hold11["holdout_dti"],
            "holdout_v11_ci95": hold11["ci_95"],
            "holdout_v11_T_S_M": [hold11["pooled_T"], hold11["pooled_S"], hold11["pooled_M"]],
            "holdout_ci95": hold["ci_95"],
            "sgmc_offcat_dti": sg["dti"],
            "n_dots": int(dots.sum()),
            "mass": float(pred.sum()),
            "dot_value_min": float(vals.min()) if vals.size else None,
            "dot_value_max": float(vals.max()) if vals.size else None,
            "frac_dots_unit_value": float(np.mean(np.abs(vals - 1.0) < 1e-6)) if vals.size else None,
            "dist_to_catalogue_px_p10_p50_p90": [float(np.percentile(dc, q)) for q in (10, 50, 90)] if dc.size else None,
            "frac_dots_within_3px_of_catalogue": float(np.mean(dc <= 3.0)) if dc.size else None,
            "frac_dots_3to10px_of_catalogue": float(np.mean((dc > 3.0) & (dc <= 10.0))) if dc.size else None,
            "frac_dots_gt10px_of_catalogue": float(np.mean(dc > 10.0)) if dc.size else None,
            "median_nn_spacing_px": nn_med,
            "mass_on_catalogue": float(pred[cat].sum()),
        }
        print(f"{name:18s} Hv10={hold['holdout_dti']:.4f} Hv11={hold11['holdout_dti']:.4f} SGMC={sg['dti']:.4f} dots={int(dots.sum())} "
              f"dcat50={rows[name]['dist_to_catalogue_px_p10_p50_p90'][1]:.1f}px nn={nn_med:.2f}px "
              f"claimed={CLAIMED.get(name)}", flush=True)

    # Which proxy predicts the organizer score? (only rows with a claimed score)
    sub = {k: v for k, v in rows.items() if v["organizer_claimed_user_reported"] is not None}
    y = np.array([v["organizer_claimed_user_reported"] for v in sub.values()])
    corr = {}
    for key in ["holdout_dti_fullmap_v11_nohalo", "sgmc_offcat_dti", "n_dots",
                "frac_dots_within_3px_of_catalogue", "frac_dots_3to10px_of_catalogue",
                "frac_dots_gt10px_of_catalogue", "median_nn_spacing_px"]:
        x = np.array([v[key] for v in sub.values()], dtype=float)
        rho, pval = spearmanr(x, y)
        corr[key] = {"spearman_rho_vs_organizer_claimed": float(rho), "p": float(pval), "n": int(len(y))}
        print(f"corr {key:38s} rho={rho:+.3f} p={pval:.3f} n={len(y)}")

    out = {
        "label_warning": "organizer scores are CLAIM-USER-REPORTED from the session prompt; no DrivenData receipt is pinned in-repo. HOLDOUT/SGMC numbers below are MEASURED in this sandbox with scripts/evaluate_holdout.py gems91-hide-recover-v1.0.",
        "evaluator_version": EH.EVALUATOR_VERSION,
        "rows": rows,
        "proxy_correlations": corr,
    }
    dest = ROOT / "evidence/s14_winner_forensics.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
