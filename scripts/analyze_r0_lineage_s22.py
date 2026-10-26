#!/usr/bin/env python3
"""Why did GEMSDOE32 R0 (USER-REPORTED 0.2778) score highest?  A byte-level natural-experiment decomposition.

Everything is recomputed from SHA-pinned raster bytes plus the USER-REPORTED anchor table
(`registry/lfi_live_anchors.csv`).  No score is invented: every live number is read from that table and labelled
USER-REPORTED; every derived number is labelled MODEL and lists its assumptions.

Method
------
For a binary dot raster ``DTI = T / (0.2 T + 0.2 FP + 0.8 G)`` with ``T`` = kernel credit on truth, ``FP`` = unmatched
dot mass, ``G`` = truth size (official definition, DrivenData page 967).  For nested rasters the *difference set*
is known exactly from the bytes.  If the difference set carries ~zero truth credit (pure false positives) then ``T`` is
unchanged and the denominator moves by exactly ``0.2 * |difference|``; one live-score pair therefore identifies ``T``,
and that single number must then predict every other nested step.  The script reports where this holds and where it
does not (a residual means the difference set carried credit).

Output: docs/s22/r0-decomposition.json
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from gems91.xbreed22 import credit_from_pure_fp_step, predicted_dti_after_pure_fp  # noqa: E402

ANCHORS = ROOT / "registry/lfi_live_anchors.csv"
FLEET = ROOT / "data/fleet_registry"
LFI = ROOT / "data/lfi_anchors"
OUT = ROOT / "docs/s22/r0-decomposition.json"

FILES = {
    "H19-5 binary network": FLEET / "19GEMSDOE__h19-5-powerlaw-budget-multiline.tif",
    "D1.5": FLEET / "GEMSDOE24__h25-1-dotted-h19-5-d1-5.tif",
    "D2.8": FLEET / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-zeros.tif",
    "H27-4 (solo D2.8, >1 px collar)": FLEET / "GEMSDOE28__h27-4-r1-solo-d2-8.tif",
    "R0 (H33-2-B2, >2 px collar)": FLEET / "GEMSDOE32__h33-2-b2-zeros.tif",
    "GEMSDOE36 anderson-pinn-38854": LFI / "GEMSDOE36__gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros-tif.tif",
}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_mask(p: Path) -> np.ndarray:
    with rasterio.open(p) as ds:
        a = ds.read(1)
    return np.nan_to_num(a, nan=0.0) > 0.5


def anchor(site: str, name_contains: str) -> dict:
    rows = [r for r in csv.DictReader(open(ANCHORS)) if r["site"] == site and name_contains in r["submission_name"]]
    if len(rows) != 1:
        raise RuntimeError(f"expected exactly one anchor for {site}/{name_contains}, got {len(rows)}")
    r = rows[0]
    return {"site": site, "submission_name": r["submission_name"], "score": float(r["user_reported_public_dti"]),
            "evidence_class": "USER-REPORTED"}


def main() -> int:
    # resolve the anderson file by glob (local name carries the encoding suffix)
    pinn = sorted(LFI.glob("GEMSDOE36__*anderson-geothermal-pinn-38854*"))
    if len(pinn) != 1:
        raise RuntimeError("GEMSDOE36 anchor raster missing: run scripts/restore_lfi_anchors.py")
    FILES["GEMSDOE36 anderson-pinn-38854"] = pinn[0]

    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        cat = ds.read(1) == 1
    d_cat = ndi.distance_transform_edt(~cat)

    masks, info = {}, {}
    for name, path in FILES.items():
        m = read_mask(path)
        masks[name] = m
        dd = d_cat[m]
        bins = [(0, 1.01), (1.01, 2.01), (2.01, 3.01), (3.01, 5.01), (5.01, 10.01), (10.01, 1e9)]
        info[name] = {
            "file": str(path.relative_to(ROOT)), "sha256": sha256(path), "n_dots": int(m.sum()),
            "min_distance_to_catalogue_px": round(float(dd.min()), 3),
            "dots_by_distance_to_catalogue_px": {f"({lo:g},{min(hi, 999):g}]": int(((dd > lo) & (dd <= hi)).sum())
                                                 for lo, hi in bins},
            "share_gt_10px": round(float((dd > 10.01).mean()), 4),
        }

    n = {k: info[k]["n_dots"] for k in info}
    d28, h274, r0, pinn_k = (masks["D2.8"], masks["H27-4 (solo D2.8, >1 px collar)"],
                             masks["R0 (H33-2-B2, >2 px collar)"], masks["GEMSDOE36 anderson-pinn-38854"])
    net = masks["H19-5 binary network"]
    nesting = {
        "R0 subset of H27-4": bool((r0 & ~h274).sum() == 0),
        "H27-4 subset of D2.8": bool((h274 & ~d28).sum() == 0),
        "D2.8 subset of H19-5 network": bool((d28 & ~net).sum() == 0),
        "R0 subset of GEMSDOE36 file": bool((r0 & ~pinn_k).sum() == 0),
        "D1.5 subset of H19-5 network": bool((masks["D1.5"] & ~net).sum() == 0),
        "D2.8 subset of D1.5": bool((d28 & ~masks["D1.5"]).sum() == 0),
    }
    removed1 = d28 & ~h274
    removed2 = h274 & ~r0
    added_pinn = pinn_k & ~r0
    diffsets = {
        "D2.8 minus H27-4": {"n": int(removed1.sum()), "max_distance_to_catalogue_px": round(float(d_cat[removed1].max()), 3)},
        "H27-4 minus R0": {"n": int(removed2.sum()),
                           "min_distance_to_catalogue_px": round(float(d_cat[removed2].min()), 3),
                           "max_distance_to_catalogue_px": round(float(d_cat[removed2].max()), 3)},
        "GEMSDOE36 minus R0": {"n": int(added_pinn.sum()),
                               "median_distance_to_catalogue_px": round(float(np.median(d_cat[added_pinn])), 2),
                               "share_on_h19_5_network_within_0px": round(float((added_pinn & net).sum() / max(added_pinn.sum(), 1)), 4)},
    }

    s_d28 = anchor("GEMSDOE25", "dotted-h19-5-d2-8")["score"]
    s_h274 = anchor("GEMSDOE28", "h27-4-r1-solo-d2-8")["score"]
    s_h274_alt = anchor("GEMSDOE31", "h27-4-solo-d28")["score"]
    s_r0 = anchor("GEMSDOE32", "h33-2-b2")["score"]
    s_pinn = anchor("GEMSDOE36", "anderson-geothermal-pinn")["score"]
    byte_identical_31_28 = bool((read_mask(next(LFI.glob("GEMSDOE31__*h27-4-solo-d28*"))) == h274).all())

    # step 1: D2.8 -> H27-4 identifies T under the pure-FP assumption
    k1 = n["D2.8"] - n["H27-4 (solo D2.8, >1 px collar)"]
    k2 = n["H27-4 (solo D2.8, >1 px collar)"] - n["R0 (H33-2-B2, >2 px collar)"]
    T = credit_from_pure_fp_step(n["D2.8"], n["H27-4 (solo D2.8, >1 px collar)"], s_d28, s_h274)
    pred_h274_to_r0 = predicted_dti_after_pure_fp(T, s_h274, k2)
    pred_r0_to_pinn = predicted_dti_after_pure_fp(T, s_r0, -int(added_pinn.sum()))
    T2 = credit_from_pure_fp_step(n["H27-4 (solo D2.8, >1 px collar)"], n["R0 (H33-2-B2, >2 px collar)"], s_h274, s_r0)
    # implied credit of the 1,200 added dots if their matched mass were zero
    D_r0 = T / s_r0
    kk = int(added_pinn.sum())
    t_add = (s_pinn * (D_r0 + 0.2 * kk) - T) / (1.0 - 0.2 * s_pinn)

    n_r0 = n["R0 (H33-2-B2, >2 px collar)"]
    D = T / s_r0
    scale = {}
    for lab, M in (("M=0", 0.0), ("M=5% of dots", 0.05 * n_r0), ("M=10% of dots", 0.10 * n_r0), ("M=T", T)):
        G = (D - 0.2 * T - 0.2 * (n_r0 - M)) / 0.8
        scale[lab] = {"G_truth_pixels_in_scored_region": round(G), "recall_T_over_G": round(T / G, 3)}
    oracle = {f"remove_{k}_pure_fp_dots": round(predicted_dti_after_pure_fp(T, s_r0, k), 4) for k in (1000, 5000, 10000, 20000)}

    out = {
        "evidence_classes": {"live scores": "USER-REPORTED (not organizer receipts)", "T/G/recall/oracle": "MODEL (assumptions below)",
                             "dot counts, nesting, distances": "BYTES (SHA-256 pinned rasters)"},
        "official_metric_source": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/ (retrieved 2026-10-26)",
        "rasters": info,
        "nesting_exact": nesting,
        "difference_sets": diffsets,
        "live_scores_user_reported": {"D2.8": s_d28, "H27-4 (GEMSDOE28)": s_h274, "H27-4 (GEMSDOE31, same pixels)": s_h274_alt,
                                      "R0": s_r0, "GEMSDOE36 (R0 + 1,200 dots)": s_pinn},
        "replicate_check": {"GEMSDOE31 raster pixel-identical to GEMSDOE28 H27-4": byte_identical_31_28,
                            "scores equal": s_h274 == s_h274_alt,
                            "note": "the same pixels scored 0.2708 on two separate submissions: the board is deterministic at 4 dp"},
        "pure_fp_model": {
            "assumption": "the removed/added dot sets carry ~zero truth credit and are all false positives",
            "T_from_step1_D2.8_to_H27-4": round(T, 1),
            "T_from_step2_H27-4_to_R0": round(T2, 1),
            "rounding_band_on_T_from_step1_pct": round(100 * 0.00005 * (1 / s_d28**2 + 1 / s_h274**2) / (1 / s_d28 - 1 / s_h274), 2),
            "prediction_H27-4_to_R0": {"predicted": round(pred_h274_to_r0, 4), "user_reported": s_r0,
                                       "residual": round(pred_h274_to_r0 - s_r0, 4)},
            "prediction_R0_to_GEMSDOE36": {"predicted": round(pred_r0_to_pinn, 4), "user_reported": s_pinn,
                                           "residual": round(pred_r0_to_pinn - s_pinn, 4),
                                           "implied_credit_of_added_1200_dots_if_M_added_is_0": round(t_add, 1),
                                           "implied_credit_per_added_dot": round(t_add / kk, 4)},
            "interpretation": ("One number (T ~ 5.0e3) predicts R0 from the first step to within 0.001 and the 1,200-dot "
                               "GEMSDOE36 addition to within 0.001: both pruned and added sets are, to first order, pure "
                               "false positives. Step 2 alone implies a larger T (see T_from_step2), i.e. the (1,2] px set "
                               "carried a little credit; the residual quantifies it."),
        },
        "R0_scale_model": {"n_dots": n_r0, "T": round(T, 1), "credit_per_dot": round(T / n_r0, 4), "scenarios": scale,
                           "caveat": "G is not observable here; it is bracketed by the unknown matched mass M"},
        "oracle_headroom_if_pure_fp_dots_were_identifiable": oracle,
        "ceiling_check": "an oracle that removes 10,000 dead dots would reach ~0.31; no method here can identify them without new information",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("nesting_exact", "difference_sets", "pure_fp_model", "R0_scale_model", "replicate_check")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
