#!/usr/bin/env python3
"""CONCENTRATION, second generation: three arms on R0, one prior family, one seed.

Session 8 question
------------------
Seven CONCENTRATION rows already exist.  Every one of them moves mass *toward*
whatever the prior ranks highest, every one of them pushes the 1 km block-density
CV up and away from the 0.51-0.59 band the brief attributes to the best historical
files, and the GDR-thermal family moves the label-blind catalogue PROXY *down*
(-0.0008) while a uniform-random block ranking already reproduces ~70 % of its
predicted gain (evidence/concentration_axis_20261023.json -> null_diagnostic).
Nobody has asked whether the *dose* survives, or whether the parent is simply
over-served in blocks that structure does not ask for.

Arms (identical everything except the two knobs in the name)
-----------------------------------------------------------
st1km-m10   structural prior, 1 km blocks, 10 % of dots reallocated
st1km-m20   structural prior, 1 km blocks, 20 %  (dose bracket around the fleet's
            existing 15 % / 1 km structural point, +0.008 MODEL)
res1km-m20  residual prior (structure rank MINUS parent occupancy rank, occupied
            blocks only), 1 km blocks, 20 %

Prior (label-blind, licence-clean, pinned)
    percentile rank inside the footprint of Band 3 `tmi_hg`, Band 5
    `iso_grav_anom_slope`, Band 18 `iso_grav_anom_hg` of
    `data/bridge/gems-geodawn-numerical-features.tif`, averaged.
    Same three bands the ledger's `15pct-1km-grad` row names.

Shared edit rules
    count fixed at 37,654; unit mass; donors = dots in the bottom 30 % of blocks;
    acceptors = 80 % anchored on a surviving dot in the top 30 % of blocks, 20 %
    uniform, then +-4 px jitter; every acceptor cell is inside the footprint, is
    not occupied, is >= 2.0 px from every surviving dot (R0's own rule) and
    > 3.0 px from every mapped-fault cell; R0's 2,171 collar dots are quarantined
    as donors, so no arm is a PRUNE edit in disguise; fixed seed 91034.

Metric conventions, reported not reconciled
    `gems91.metric.components` sums kernel credit from every dot into each truth
    cell, so stacking mass on one truth cell raises DTI without bound.
    `gems91.relief.fast_binary_dti` gives each truth cell the credit of its
    nearest dot, so DTI <= 1.  Every arm is scored under BOTH, because the two
    conventions disagree about exactly the quantity this axis moves.

Usage
    python3 scripts/build_concentration_struct.py --build
    python3 scripts/build_concentration_struct.py          # print this docstring
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import build_concentration as bc  # noqa: E402  (memory-frugal DTI parts, shared)
import build_relief as br  # noqa: E402  (pin / lineage / ledger / manifest helpers)
import validate_raster as vr_mod  # noqa: E402
from gems91 import concentration as cc  # noqa: E402
from gems91 import geom, io, prior as priors, proxy, relief, release_gates as gates  # noqa: E402
from tools import raster_io  # noqa: E402

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
BUILD_DATE = "20261024"
SEED = 91034
LIVE_SPAN = 0.2778        # CLAIM only; the scale of a MODEL prediction
KAPPA = 0.10              # claim a tenth of the prior-as-truth effect
BAND = 0.008
STRUCT_BANDS = (3, 5, 18)  # tmi_hg, iso_grav_anom_slope, iso_grav_anom_hg

ARMS = {
    "st1km-m10": dict(prior="struct", frac=0.10,
                      description="10% of dots moved from the lowest- to the highest-structure "
                                  "1 km blocks (3-band geophysical prior)"),
    "st1km-m20": dict(prior="struct", frac=0.20,
                      description="same prior at 20% (dose bracket around the fleet's 15% point)"),
    "res1km-m20": dict(prior="residual", frac=0.20,
                       description="20% moved on the RESIDUAL prior: structural rank minus the "
                                   "parent's own occupancy rank, so over-served blocks pay"),
}

LEDGER_COLS = ["id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
               "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
               "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
               "evidence_class", "source", "notes", "source_url"]


def load_bands(path: Path, footprint: np.ndarray) -> tuple[dict[int, np.ndarray], dict]:
    """Read the structural bands, mask nodata, and name them for the evidence file."""
    out: dict[int, np.ndarray] = {}
    with rasterio.open(str(path)) as src:
        names = {i + 1: src.descriptions[i] for i in range(src.count)}
        for b in STRUCT_BANDS:
            arr = src.read(b).astype(np.float32)
            nodata = src.nodata
            if nodata is not None:
                arr[arr == np.float32(nodata)] = np.nan
            arr[~np.isfinite(arr)] = np.nan
            arr[~footprint] = np.nan
            out[b] = arr
    return out, {b: names.get(b) for b in STRUCT_BANDS}


def band_position_table(dots: np.ndarray, footprint: np.ndarray) -> dict:
    """1 km block-CV of a dot field at several block sizes, against the 0.51-0.59 band."""
    row = {}
    for size in (5, 10, 25, 50):
        cv = proxy.block_density_cv(dots, footprint, size)
        row[f"{size}px_{size * 0.1:.1f}km"] = {"cv_occupied_blocks": cv,
                                               "position": cc.cv_band_position(cv)}
    return row


def predict(rel_cell: float, delta_noise: float, delta_mask: float) -> tuple[float, list[float], str]:
    """MODEL prediction under the fleet's frozen convention (KAPPA 0.10, 3x ceiling)."""
    d = round(float(KAPPA * LIVE_SPAN * rel_cell), 4)
    lo = round(min(delta_noise, delta_mask, d - BAND), 3)
    hi = round(max(3.0 * d, d + BAND), 3)
    return d, [lo, hi], (f"per-cell surrogate rel change {rel_cell:+.4f}; floor from "
                         f"uniform-noise truth {delta_noise:+.4f} and the H19-5 lineage mask "
                         f"{delta_mask:+.4f}; ceiling 3x point")



def _append_new_rows_only(rows: list[dict]) -> int:
    """Append rows whose id is not in the ledger yet; never rewrite an existing row.

    `build_relief.append_ledger_rows` replaces a row by id, which would wipe
    `receipt_score` / `receipt_date` the human fills in after uploading.  A rebuild
    that returns the same id with a *different* sha256 is a reproducibility failure,
    so it raises instead.
    """
    ledger = ROOT / "ledger" / "submissions.csv"
    existing: list[dict] = []
    if ledger.is_file():
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    by_id = {r["id"]: r for r in existing}
    known_shas = {r.get("sha256") for r in existing} | {r.get("sha256_zeros") for r in existing}
    fresh = []
    for r in rows:
        if r["id"] in by_id:
            if by_id[r["id"]].get("sha256") != r["sha256"]:
                raise SystemExit(f"{r['id']} exists with a DIFFERENT sha256 - not reproducible")
            print(f"{r['id']}: already in the ledger with the same sha256 (idempotent)")
            continue
        if r["sha256"] in known_shas:
            raise SystemExit(f"refusing to append {r['id']}: hash already in the ledger")
        fresh.append(r)
    return br.append_ledger_rows(fresh) if fresh else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args(argv)
    if not args.build:
        print(__doc__)
        return 0

    paths = br.verify_pinned_inputs()
    template = io.read_grid(paths["sample_submission"])
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(paths["existing_faults"]))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(paths["parent_r0_nan"]))
    lineage = br.verify_parent_lineage(paths, cat, dcat)

    # ---------------------------------------------------------------- priors --
    bands, band_names = load_bands(paths["training_features"], footprint)
    struct = cc.structural_prior([bands[b] for b in STRUCT_BANDS], footprint)
    py, px = np.nonzero(parent)
    parent_px = np.c_[py, px]
    resid, resid_diag = cc.residual_prior(struct, parent_px, footprint, cc.BLOCK_PX)

    n_surrogate = int(cat.sum())
    truth_surrogate = cc.surrogate_truth(struct, footprint, n_surrogate)
    rng_t = np.random.default_rng(SEED)
    fr, fc = np.nonzero(footprint)
    pick = rng_t.choice(fr.size, size=int(truth_surrogate.sum()), replace=False)
    truth_noise = np.zeros(footprint.shape, dtype=bool)
    truth_noise[fr[pick], fc[pick]] = True
    truth_lineage = io.dot_mask(io.read_grid(paths["anc_h19_5"])) & footprint
    with rasterio.open(str(paths["sgmc_faults_control"])) as src:
        sgmc_truth = (src.read(1) > 0) & footprint & (dcat > 3.0)

    # R0 baseline under both metric conventions
    r0 = {
        "n_dots": int(parent.sum()),
        "proxy": proxy.hide_and_recover(parent, cat, footprint),
        "redundancy": proxy.redundancy(parent),
        "cv_1km_occupied_blocks": proxy.block_density_cv(parent, footprint, 10),
        "cv_table": band_position_table(parent, footprint),
        "dti_surrogate_sumconv": round(float(bc.dti_parts_f32(
            np.where(footprint, parent.astype(np.float32), 0.0), truth_surrogate).dti()), 6),
        "dti_surrogate_cellconv": round(float(relief.fast_binary_dti(
            parent, truth_surrogate)["dti"]), 6),
        "dti_lineage_mask_cellconv": round(float(relief.fast_binary_dti(
            parent, truth_lineage)["dti"]), 6),
        "dti_sgmc_cellconv": round(float(relief.fast_binary_dti(parent, sgmc_truth)["dti"]), 6),
        "dti_catalogue_sumconv": round(float(bc.dti_parts_f32(
            np.where(footprint, parent.astype(np.float32), 0.0), cat).dti()), 6),
        "dti_catalogue_cellconv": round(float(relief.fast_binary_dti(parent, cat)["dti"]), 6),
    }
    parent_pred = np.where(footprint, parent.astype(np.float32), np.float32(0.0))
    mask_parts = bc.dti_parts_f32(parent_pred, truth_lineage)

    evidence = {
        "schema": "gems91.concentration-struct-evidence.v1",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_sha": raster_io.git_sha(short=False),
        "git_sha_short": raster_io.git_sha(),
        "axis": "CONCENTRATION",
        "session": "arena/bc249fc7-gemsdoe91 (session 8)",
        "parent": PARENT_TAG,
        "lineage": lineage,
        "settings": {"block_px": cc.BLOCK_PX, "low_q": cc.LOW_Q, "high_q": cc.HIGH_Q,
                     "min_gap_px": cc.MIN_GAP_PX, "min_sep_px": cc.MIN_SEP_PX,
                     "jitter_px": cc.JITTER_PX, "anchor_frac": cc.ANCHOR_FRAC,
                     "seed": SEED, "kappa": KAPPA, "band": BAND,
                     "live_span_CLAIM": LIVE_SPAN,
                     "collar_quarantined_px": cc.MIN_GAP_PX},
        "prior": {
            "kind": "structural",
            "bands": band_names,
            "band_sha256": io.sha256_file(paths["training_features"]),
            "definition": "mean percentile rank (ties averaged) of the three bands inside the "
                          "footprint; NaN outside; block-mean at 1 km inside the edit",
            "percentile_min": round(float(np.nanmin(struct)), 6),
            "percentile_max": round(float(np.nanmax(struct)), 6),
            "percentile_mean_inside_footprint": round(float(np.nanmean(struct[footprint])), 6),
        },
        "residual_prior": resid_diag,
        "instruments": {
            "surrogate_truth": {
                "kind": "top structural cells, same cell count as the mapped catalogue",
                "n_cells": int(truth_surrogate.sum()),
                "catalogue_cells": int(cat.sum()),
                "threshold_percentile": round(100.0 * truth_surrogate.sum() / footprint.sum(), 3),
                "reading": "MODEL upper bound: 'what if new-fault truth followed this prior'",
            },
            "noise_truth": {"kind": "uniform random footprint cells, same count, seed 91034",
                            "n_cells": int(truth_noise.sum())},
            "lineage_mask": {"kind": "H19-5 ancestor field (121,131 px), pessimistic superset",
                             "n_cells": int(truth_lineage.sum())},
            "sgmc_control": {"kind": "USGS SGMC bedrock faults, off-catalogue (>3 px), report only",
                             "n_cells": int(sgmc_truth.sum())},
        },
        "metric_conventions": {
            "sum_conv": "gems91.metric.components: T sums credit from EVERY dot into each truth "
                        "cell; DTI is unbounded above (2 dots on one isolated truth cell = 1.667)",
            "cell_conv": "gems91.relief.fast_binary_dti: each truth cell takes its nearest dot's "
                         "credit; DTI <= 1",
            "why_it_matters": "this axis moves mass between over- and under-served blocks; under "
                              "the sum convention redundancy never costs anything, under the cell "
                              "convention an uncovered cell is the only thing that pays",
        },
        "r0": r0,
        "arms": {},
        "null_diagnostic": {},
    }
    del mask_parts

    releases = ROOT / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    donor_ok = dcat[parent] > cc.MIN_GAP_PX        # collar quarantine (IR-91-03)
    prior_fields = {"struct": struct, "residual": resid}
    prior_digests = {"struct": priors.array_digest(struct),
                     "residual": priors.array_digest(resid)}

    rows = []
    for key, cfg in ARMS.items():
        pf = prior_fields[cfg["prior"]]
        dots, st = cc.relocate(parent, pf, footprint, dcat, frac=cfg["frac"],
                               block_px=cc.BLOCK_PX, donor_mask=donor_ok,
                               seed=SEED)
        diff = gates.parent_diff(parent, dots)

        tmp_nan, tmp_zer = releases / "_tmp-conc2-nan.tif", releases / "_tmp-conc2-zeros.tif"
        io.write_float32(tmp_nan, np.where(footprint, dots.astype("float32"), np.nan),
                         encoding="nan", template=paths["sample_submission"])
        io.write_float32(tmp_zer, np.where(footprint, dots.astype("float32"), np.nan),
                         encoding="zeros", template=paths["sample_submission"])
        sha8 = io.sha256_file(tmp_nan)[:8]
        stem = f"{PARENT_TAG}-CONCENTRATION{key}-{BUILD_DATE}-{sha8}"
        fn, fz = releases / f"{stem}.tif", releases / f"{stem}-zeros.tif"
        tmp_nan.replace(fn)
        tmp_zer.replace(fz)

        gn = gates.validate_release(fn, template=paths["sample_submission"], catalogue=cat,
                                    encoding="nan", expect_dots=PARENT_DOTS)
        gz = gates.validate_release(fz, template=paths["sample_submission"], catalogue=cat,
                                    encoding="zeros", expect_dots=PARENT_DOTS,
                                    ledger=ROOT / "ledger" / "submissions.csv", own_id=stem)
        vr = vr_mod.validate_raster(fn, paths["sample_submission"], catalogue=paths["existing_faults"],
                                    ledger_csv=ROOT / "ledger" / "submissions.csv",
                                    parent=paths["parent_r0_nan"])
        if not (gn["PASS"] and gz["PASS"] and vr.ok):
            raise SystemExit(f"GATE FAIL {stem}: {gn['failed']} {gz['failed']}\n{vr.text()}")

        # ---- instruments (report only) ----
        cand_pred = np.where(footprint, dots.astype(np.float32), np.float32(0.0))
        p_sum = bc.dti_parts_f32(parent_pred, truth_surrogate).dti()
        c_sum = bc.dti_parts_f32(cand_pred, truth_surrogate).dti()
        p_cell = relief.fast_binary_dti(parent, truth_surrogate)["dti"]
        c_cell = relief.fast_binary_dti(dots, truth_surrogate)["dti"]
        p_noise = relief.fast_binary_dti(parent, truth_noise)["dti"]
        c_noise = relief.fast_binary_dti(dots, truth_noise)["dti"]
        p_lin = relief.fast_binary_dti(parent, truth_lineage)["dti"]
        c_lin = relief.fast_binary_dti(dots, truth_lineage)["dti"]
        p_sg = relief.fast_binary_dti(parent, sgmc_truth)["dti"]
        c_sg = relief.fast_binary_dti(dots, sgmc_truth)["dti"]
        delta_noise = round(float(LIVE_SPAN * (c_noise - p_noise) / p_noise), 4)
        delta_mask = round(float(LIVE_SPAN * (c_lin - p_lin) / p_lin), 4)
        rel_cell = float((c_cell - p_cell) / p_cell)
        rel_sum = float((c_sum - p_sum) / p_sum)
        pred, pred_range, basis = predict(rel_cell, delta_noise, delta_mask)

        v_proxy = proxy.hide_and_recover(dots, cat, footprint)
        canary = proxy.canary(dots & ~parent, dots, cat)
        moved = dots & ~parent
        collar = {
            "dots_le_3px_before": int((dcat[parent] <= cc.MIN_GAP_PX).sum()),
            "dots_le_3px_after": int((dcat[dots] <= cc.MIN_GAP_PX).sum()),
            "moved_targets_le_3px": int((dcat[moved] <= cc.MIN_GAP_PX).sum()),
            "donors_excluded_by_quarantine": int((~(donor_ok)).sum()),
        }
        cv_occ = proxy.block_density_cv(dots, footprint, 10)
        rec = {
            "id": stem, "value": key, "description": cfg["description"],
            "prior": cfg["prior"], "prior_digest": prior_digests[cfg["prior"]],
            "block_px": cc.BLOCK_PX, "block_km": cc.BLOCK_PX * 0.1,
            "frac_requested": cfg["frac"], "frac_achieved": st["frac_achieved"],
            "n_dots": int(dots.sum()), "count_preserved": st["count_preserved"],
            "parent_diff": diff,
            "pct_dots_changed": round(100.0 * diff["changed"] / PARENT_DOTS, 4),
            "pct_dots_moved": st["pct_dots_moved"], "n_moved": st["n_moved"],
            "n_unplaced": st["n_unplaced"],
            "moved_displacement_px": st["moved_displacement_px"],
            "donor_block_prior_mean": st["donor_block_prior_mean"],
            "acceptor_block_prior_mean": st["acceptor_block_prior_mean"],
            "block_density_cv": {
                "definition_occupied_blocks": "proxy.block_density_cv: CV of dots per OCCUPIED "
                                              "1 km block, the definition the 0.51-0.59 band is "
                                              "quoted against",
                "before": r0["cv_1km_occupied_blocks"], "after": cv_occ,
                "position_before": cc.cv_band_position(r0["cv_1km_occupied_blocks"]),
                "position_after": cc.cv_band_position(cv_occ),
                "moved_toward_band": abs(cv_occ - 0.55) < abs(r0["cv_1km_occupied_blocks"] - 0.55),
                "definition_footprint_blocks": {
                    "before": st["cv_footprint_blocks_before"],
                    "after": st["cv_footprint_blocks_after"],
                    "note": st["cv_definition_footprint_blocks"]},
            },
            "collar": collar,
            "redundancy": proxy.redundancy(dots),
            "proxy": v_proxy,
            "proxy_delta_vs_r0": round(float(v_proxy["proxy_mean_credit"]
                                             - r0["proxy"]["proxy_mean_credit"]), 6),
            "canary": canary,
            "sgmc_control": {"n_cells": int(sgmc_truth.sum()),
                             "dti_parent": round(float(p_sg), 6),
                             "dti_candidate": round(float(c_sg), 6),
                             "delta_dti": round(float(c_sg - p_sg), 6),
                             "delta_if_live": round(float(LIVE_SPAN * (c_sg - p_sg) / p_sg), 4)},
            "surrogate_truth": {
                "n_cells": int(truth_surrogate.sum()),
                "dti_parent_cell_conv": round(float(p_cell), 6),
                "dti_candidate_cell_conv": round(float(c_cell), 6),
                "rel_change_cell_conv": round(rel_cell, 6),
                "dti_parent_sum_conv": round(float(p_sum), 6),
                "dti_candidate_sum_conv": round(float(c_sum), 6),
                "rel_change_sum_conv": round(rel_sum, 6),
                "delta_if_prior_were_truth_cell_conv":
                    round(float(LIVE_SPAN * rel_cell), 4),
                "delta_if_prior_were_truth_sum_conv": round(float(LIVE_SPAN * rel_sum), 4),
            },
            "noise_truth_bound": {"dti_parent": round(float(p_noise), 6),
                                  "dti_candidate": round(float(c_noise), 6),
                                  "delta_if_prior_is_noise": delta_noise},
            "lineage_mask_bound": {"n_cells": int(truth_lineage.sum()),
                                   "dti_parent": round(float(p_lin), 6),
                                   "dti_candidate": round(float(c_lin), 6),
                                   "delta_if_truth_is_lineage_mask": delta_mask},
            "predicted_change_MODEL": pred, "predicted_range": pred_range,
            "prediction_basis": basis,
            "sha256_nan": gn["sha256"], "sha256_zeros": gz["sha256"], "sha8": sha8,
            "gates_nan": {k: gn[k] for k in ("PASS", "failed", "min_catalogue_distance_px",
                                             "zero_catalogue_mass", "count_matches_parent",
                                             "unit_mass_dots", "nan_outside_footprint",
                                             "no_nan_inside_footprint", "values_within_0_1")},
            "gates_zeros": {k: gz[k] for k in ("PASS", "failed", "sha256_not_in_ledger")},
            "validator": {"ok": bool(vr.ok),
                          "checks_passed": int(sum(1 for g in vr.gates if g.ok)),
                          "checks_total": int(len(vr.gates))},
        }
        evidence["arms"][key] = rec

        note = (f"{PARENT_TAG}; CONCENTRATION{key}: {rec['pct_dots_moved']:.1f}% of {rec['n_dots']} "
                f"dots reallocated across 1 km blocks ({cfg['prior']} prior); pred {pred:+.4f} MODEL")
        assert len(note) <= 140, f"form note too long ({len(note)}): {note}"
        rows.append({
            "id": stem, "parent": PARENT_TAG, "axis": "CONCENTRATION", "value": key,
            "n_dots": rec["n_dots"], "pct_changed": f"{rec['pct_dots_changed']:.2f}",
            "pct_relocated": f"{rec['pct_dots_moved']:.2f}",
            "sha256": rec["sha256_nan"], "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT", "predicted_change": f"MODEL:{pred:+.4f}",
            "predicted_range": f"[{pred_range[0]:+.3f},{pred_range[1]:+.3f}]",
            "ranking_basis": (f"{cfg['prior']} km-scale prior (bands 3/5/18 percentile mean"
                              + (", minus parent occupancy rank" if cfg["prior"] == "residual" else "")
                              + f"); {cc.BLOCK_PX}px blocks; digest {rec['prior_digest'][:12]}"),
            "receipt_score": "", "receipt_date": "", "date": "2026-10-24", "form_note": note,
            "evidence_class": "MODEL",
            "source": f"BUILT:scripts/build_concentration_struct.py@{raster_io.git_sha()}",
            "notes": (f"moved={rec['n_moved']} unplaced={rec['n_unplaced']} "
                      f"disp {rec['moved_displacement_px']['mean_px']}px; "
                      f"cv_occupied {rec['block_density_cv']['before']}->{cv_occ}; "
                      f"proxy {rec['proxy_delta_vs_r0']:+.4f}; sgmc {rec['sgmc_control']['delta_dti']:+.4f}; "
                      f"canary {canary['canary_auc']}; gates PASS"),
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91",
        })
        print(f"{stem}: moved={rec['n_moved']} ({rec['pct_dots_moved']:.2f}%) "
              f"cv1km {rec['block_density_cv']['before']}->{cv_occ} "
              f"cellDTI {p_cell:.4f}->{c_cell:.4f} rel {rel_cell:+.3f} pred {pred:+.4f} "
              f"proxy {rec['proxy_delta_vs_r0']:+.4f} sgmc {rec['sgmc_control']['delta_dti']:+.4f}")

    # ------------------------------------------------- null (diagnostic only) --
    rng = np.random.default_rng(SEED)
    null_prior = np.where(footprint, rng.random(footprint.shape), np.nan).astype(np.float32)
    null_dots, null_st = cc.relocate(parent, null_prior, footprint, dcat, frac=0.20,
                                     block_px=cc.BLOCK_PX, donor_mask=donor_ok, seed=SEED)
    evidence["null_diagnostic"] = {
        "label": "DIAGNOSTIC ONLY - no release, no ledger row, no slot",
        "design": "same dose (20%), same blocks, same seed, same collar quarantine; block "
                  "ranking is uniform random instead of the structural prior",
        "n_moved": null_st["n_moved"], "pct_dots_moved": null_st["pct_dots_moved"],
        "cv_before": r0["cv_1km_occupied_blocks"],
        "cv_after": proxy.block_density_cv(null_dots, footprint, 10),
        "dti_parent_cell_conv": round(float(relief.fast_binary_dti(parent, truth_surrogate)["dti"]), 6),
        "dti_null_cell_conv": round(float(relief.fast_binary_dti(null_dots, truth_surrogate)["dti"]), 6),
        "delta_if_prior_were_truth_cell_conv": round(float(LIVE_SPAN * (
            relief.fast_binary_dti(null_dots, truth_surrogate)["dti"]
            - relief.fast_binary_dti(parent, truth_surrogate)["dti"])
            / relief.fast_binary_dti(parent, truth_surrogate)["dti"]), 4),
    }
    print(f"null: moved={null_st['n_moved']} surrogate delta "
          f"{evidence['null_diagnostic']['delta_if_prior_were_truth_cell_conv']:+.4f}")

    out = ROOT / "evidence" / f"concentration_struct_{BUILD_DATE}.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    added = _append_new_rows_only(rows)
    br.update_release_manifest([{"file": f"{r['id']}.tif", "sha256": r["sha256"],
                                 "bytes": (releases / f"{r['id']}.tif").stat().st_size}
                                for r in rows]
                               + [{"file": f"{r['id']}-zeros.tif", "sha256": r["sha256_zeros"],
                                   "bytes": (releases / f"{r['id']}-zeros.tif").stat().st_size}
                                  for r in rows])
    print(f"\nledger rows added: {added} of {len(rows)}\nevidence: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
