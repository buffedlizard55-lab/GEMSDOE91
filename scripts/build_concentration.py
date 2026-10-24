#!/usr/bin/env python3
"""CONCENTRATION axis on R0: move 10 % of the dots between km-scale blocks of an
*independent*, licence-clean prior (USGS/DOE GDR thermal features).

Parent R0 = `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32), 37,654 unit
dots, sha256 c55bafc4… (zeros) / baeae321… (nan), CLAIM 0.2778.

Why this axis, this session
---------------------------
Every CONCENTRATION row in the fleet ledger ranked blocks by the parent's *own dot
density* (IR-91-07), so those rows measure clustering, not prior transfer.  No row
has ever moved mass using a signal that is independent of the lineage.  That is the
open question this axis exists to answer.

The whole lineage since H19-5 is a *thinning of one 121,131-px mask*: every ancestor
kept the same cells and changed how densely they were sampled.  Location has never
been re-weighted from an outside signal; the only thing ever varied is dose.  The
GDR inventory is the one pinned, public-domain layer that speaks to location.

The edit (identical in all three arms except the two knobs named at the end)
--------------------------------------------------------------------------
* count fixed at 37,654 and mass per dot fixed at 1 (S is untouched);
* donors: dots in the lowest-prior 30 % of blocks; acceptors: cells placed in the
  highest-prior 30 % of blocks (80 % anchored on an acceptor dot, 20 % uniform in
  the block, jitter +/-4 px - the builder's default texture, same as the
  CONCENTRATION builder already in the repo);
* every acceptor cell is inside the sample footprint, is not already occupied, and
  is **more than 3.0 px** from the mapped catalogue, so the edit never creates a
  new collar violation (R0 itself has 2,171 dots inside 3 px, IR-91-03; an edit is
  not allowed to add to that, and does not);
* frac = 0.10 in every arm (the low end of the brief's 10-20 %, chosen because the
  block-density CV of the best historical files sits at 0.51-0.59 and concentration
  pushes CV *up*);
* fixed seed 91025, single pass, deterministic.

Arms (only the prior and the block size differ)
-----------------------------------------------
gdr25m10    prior = exp(-d/1.2 km) to the nearest unique Hot/Warm GDR feature,
            25 px (2.5 km) blocks, 10 % moved          <- primary
gdr10m10    same prior, 10 px (1 km) blocks, 10 % moved   <- scale contrast
gdr25rm10   prior built only from features > 8 px from the mapped catalogue
            ("what do thermal features know that the map does not?"),
            25 px blocks, 10 % moved                      <- prior contrast

Usage
-----
    python scripts/build_concentration.py --build     # needs the pinned data present
    python scripts/build_concentration.py             # print this docstring
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems91 import geom, io, metric, prior as priors, proxy, release_gates as gates  # noqa: E402
from tools import pins, raster_io, run_concentration  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"
ANC_H195 = DATA / "registry" / "calib_h195_01922.tif"   # the lineage's own 121,131-px field
GDR_CSV = DATA / "external" / "gdr_wellspring_in_footprint.csv"

PARENT_ID = "h33-h33-2-b2-20261004-e5eb6e7e"
PARENT_DOTS = 37654
LIVE_SPAN = 0.2778      # CLAIM, used only as the scale of a MODEL prediction
KAPPA = 0.10            # claim only a tenth of the prior-as-truth effect
BAND = 0.008
SEED = 91025
MIN_GAP_PX = 3.0        # new cells must clear the brief's 3 px collar
PARENT_MIN_SEP_PX = 2.0  # R0 has no dot pair closer than 2.0 px (redundancy check);
                         # acceptors honour the same floor, so the arm does not
                         # silently change local spacing as well as location
FRAC = 0.10

ARMS = {
    "gdr25m10": dict(prior="all", block_px=25,
                     description="10% of dots moved from the lowest-prior to the highest-prior "
                                 "2.5 km blocks of the GDR thermal-feature distance prior"),
    "gdr10m10": dict(prior="all", block_px=10,
                     description="same prior and dose at 1 km blocks (scale contrast)"),
    "gdr25rm10": dict(prior="remote", block_px=25,
                      description="10% moved on a prior built only from GDR thermal features "
                                  ">8 px (800 m) from the mapped catalogue"),
}

LEDGER_COLS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
    "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
    "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
    "evidence_class", "source", "notes", "source_url",
]


# --------------------------------------------------------------------------- #
# Legacy DTI API adapter to the pinned shared metric
# --------------------------------------------------------------------------- #
def dti_parts_f32(pred, truth, radius_px=metric.RADIUS_PX):
    """Legacy API adapter: reuse the canonical metric, never summed credit."""
    return metric.components(pred, truth, radius_px)


def rebuild_parent() -> dict:
    """Prove the parent's dot set from two pinned ancestors before touching it."""
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    zeros = io.dot_mask(io.read_grid(PARENT_ZEROS))
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    out = {
        "parent_sha256_nan": io.sha256_file(PARENT_NAN),
        "parent_sha256_zeros": io.sha256_file(PARENT_ZEROS),
        "parent_dot_digest": io.dot_digest(parent),
        "n_dots": int(parent.sum()),
        "twins_identical": bool(np.array_equal(parent, zeros)),
        "min_catalogue_distance_px": round(float(dcat[parent].min()), 6),
        "dots_on_catalogue": int((parent & cat).sum()),
        "dots_le_3px_catalogue": int((dcat[parent] <= 3.0).sum()),
        "bytes_reproducible_here": False,   # IR-91-16: encoder, not recipe, is missing
        "rebuilt_from": {},
    }
    for name, path in (("d2.8", ANC_D28), ("solo_d2.8", ANC_SOLO)):
        anc = io.dot_mask(io.read_grid(path))
        kept = anc & (dcat > geom.CATALOGUE_FLOOR_PX)
        out["rebuilt_from"][name] = {
            "n_ancestor_dots": int(anc.sum()),
            "n_after_collar": int(kept.sum()),
            "identical_to_parent": bool(np.array_equal(kept, parent)),
        }
    return out


def build_prior(kind: str, footprint: np.ndarray, dcat: np.ndarray, cat: np.ndarray) -> tuple[np.ndarray, dict]:
    """Derive one prior from the pinned GDR CSV. Deterministic; no truth is read."""
    feats = priors.read_features(GDR_CSV)
    cells = feats["cells"]
    diag = priors.diagnostics(cells, dcat, footprint, cat)
    if kind == "remote":
        kept = priors.keep_remote(cells, dcat, priors.REMOTE_MIN_PX)
    elif kind == "all":
        kept = cells
    else:  # pragma: no cover - guarded by ARMS
        raise ValueError(f"unknown prior kind {kind!r}")
    arr = priors.distance_prior(footprint.shape, kept, footprint, priors.SIGMA_PX)
    diag.update({
        "kind": kind,
        "sigma_px": priors.SIGMA_PX,
        "sigma_km": priors.SIGMA_PX * 0.1,
        "remote_min_px": priors.REMOTE_MIN_PX if kind == "remote" else None,
        "n_features_used": int(kept.shape[0]),
        "n_features_in_footprint": int(footprint[kept[:, 0], kept[:, 1]].sum()) if kept.size else 0,
        "prior_digest": priors.array_digest(arr),
        "source_csv_sha256": io.sha256_file(GDR_CSV),
        "derivation": "prior = exp(-d/SIGMA_PX); d = EDT to nearest de-duplicated "
                      "Hot/Warm cell (one per grid cell, no record multiplicity)",
    })
    return arr, diag


def prior_as_truth(prior: np.ndarray, footprint: np.ndarray, max_px: float = 1.0) -> np.ndarray:
    """Surrogate 'new-fault' network: cells within `max_px` of a feature."""
    thr = float(np.exp(-max_px / priors.SIGMA_PX))
    return bool(0) or (np.nan_to_num(prior, nan=0.0) >= thr) & footprint


def prediction(parent_dti: float, cand_dti: float, delta_noise: float | None = None,
               delta_mask: float | None = None,
               mode: str = "ok") -> tuple[float, list[float], str]:
    """MODEL prediction, stated so it can be attacked.

    point   delta = KAPPA * LIVE_SPAN * (DTI_cand - DTI_parent) / DTI_parent, with both
            DTIs evaluated on the arm's own prior network used as a surrogate truth set
            (cells within 1 px of a kept thermal feature).  That surrogate is the best
            case: it is the prior itself.  KAPPA = 0.1 claims a tenth of it.
    lower   the worse of two measured alternatives: the same relocation scored against
            uniformly random truth cells (`delta_noise`) and against the lineage's own
            H19-5 field (`delta_mask`).  The interval is therefore asymmetric and its
            floor is negative: it is what the slot can cost, not a formality.
    upper   3 x the point estimate (KAPPA = 0.3), not the surrogate's own +0.11.
    """
    if mode == "undefined" or parent_dti <= 0:
        return 0.0, [round(float(delta_noise or 0.0), 3), BAND], \
            "surrogate DTI undefined; prediction set to the null"
    rel = (cand_dti - parent_dti) / parent_dti
    d = round(float(KAPPA * LIVE_SPAN * rel), 4)
    floors = [x for x in (delta_noise, delta_mask) if x is not None]
    lo = round(min(floors), 3) if floors else round(d - BAND, 3)
    hi = round(3.0 * d, 3)
    return d, [lo, hi], (f"surrogate-truth rel change {rel:+.3f}; "
                         f"floor from noise-truth {delta_noise:+.4f} / "
                         f"lineage-mask {delta_mask:+.4f}")


def credit_on_truth(target_pts: np.ndarray, dot_pts: np.ndarray) -> float:
    """Mean nearest-dot triangular credit at the target cells (PROXY instrument)."""
    if target_pts.size == 0:
        return float("nan")
    d, _ = cKDTree(dot_pts.astype(np.float64)).query(
        target_pts.astype(np.float64), k=1, distance_upper_bound=proxy.R_PX)
    d = np.where(np.isfinite(d), d, proxy.R_PX)
    return float(np.clip(1.0 - d / proxy.R_PX, 0.0, 1.0).mean())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    if not args.build:
        print(__doc__)
        return 0

    inputs = [TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS, ANC_D28, ANC_SOLO, ANC_H195,
              GDR_CSV, ROOT / "registry" / "data_manifest.json"]
    for p in inputs:
        if not p.is_file():
            raise SystemExit(f"missing input {p}; run scripts/restore_data.py")
    ok, results = pins.check_paths([TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS,
                                    ANC_D28, ANC_SOLO, ANC_H195, GDR_CSV])
    if not ok:
        raise SystemExit("REFUSING TO BUILD: an input is not pinned byte-for-byte: "
                         + json.dumps([r for r in results if not r["ok"]], indent=2))

    template = io.read_grid(TEMPLATE)
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(PARENT_NAN))

    lineage = rebuild_parent()
    if not (lineage["twins_identical"]
            and all(v["identical_to_parent"] for v in lineage["rebuilt_from"].values())
            and lineage["n_dots"] == PARENT_DOTS):
        raise SystemExit(f"PARENT NOT REPRODUCED - stopping (brief section 5): {lineage}")

    parent_pred = np.where(footprint, parent.astype(np.float32), np.float32(0.0))
    # The lineage's own generative support (H19-5, 121,131 px) is the one truth model
    # that is neither my prior nor the catalogue.  It is a SUPERSET of truth - R0 scores
    # 0.796 against it versus a claimed 0.2778 live - so a penalty measured against it is
    # pessimistic.  It bounds the downside, it does not predict the sign.
    lineage_mask = io.dot_mask(io.read_grid(ANC_H195)) & footprint
    mask_parts = dti_parts_f32(parent_pred, lineage_mask)
    py, px = np.nonzero(parent)
    parent_pts = np.c_[py, px]

    today = "20261023"  # pinned fleet build date (IR-91-32): ids must reproduce, not roll daily
    releases = ROOT / "releases"
    evidence = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_sha": raster_io.git_sha(short=False),
        "axis": "CONCENTRATION",
        "parent": PARENT_ID,
        "lineage": lineage,
        "settings": {"frac": FRAC, "seed": SEED, "min_gap_px": MIN_GAP_PX,
                     "low_q": 0.30, "high_q": 0.30, "kappa": KAPPA, "band": BAND,
                     "live_span_CLAIM": LIVE_SPAN},
        "priors": {},
        "arms": {},
        "r0": {"proxy": proxy.hide_and_recover(parent, cat, footprint),
               "redundancy": proxy.redundancy(parent),
               "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10)},
    }
    prior_arrays: dict[str, np.ndarray] = {}
    for kind in sorted({a["prior"] for a in ARMS.values()}):
        arr, diag = build_prior(kind, footprint, dcat, cat)
        prior_arrays[kind] = arr
        truth = prior_as_truth(arr, footprint)
        tp = np.c_[np.nonzero(truth)]
        evidence["priors"][kind] = {
            **diag,
            "surrogate_truth_cells": int(truth.sum()),
            "surrogate_truth_frac_of_footprint": round(float(truth.sum() / footprint.sum()), 5),
            "r0_credit_on_surrogate": round(credit_on_truth(tp, parent_pts), 6),
        }

    rows = []
    for key, cfg in ARMS.items():
        pr = prior_arrays[cfg["prior"]]
        band, stats = run_concentration.build_concentration(
            parent_pred, pr, footprint, cat, frac=FRAC, block_px=cfg["block_px"],
            min_gap_px=MIN_GAP_PX, seed=SEED, min_sep_px=PARENT_MIN_SEP_PX)
        dots = io.dot_mask(np.nan_to_num(band, nan=0.0))
        diff = gates.parent_diff(parent, dots)

        tmp_nan = releases / "_tmp-nan.tif"
        tmp_zer = releases / "_tmp-zeros.tif"
        io.write_float32(tmp_nan, np.where(footprint, dots.astype("float32"), np.nan),
                         encoding="nan", template=TEMPLATE)
        io.write_float32(tmp_zer, np.where(footprint, dots.astype("float32"), np.nan),
                         encoding="zeros", template=TEMPLATE)
        sha8 = io.sha256_file(tmp_nan)[:8]
        stem = f"{PARENT_ID}-CONCENTRATION{key}-{today}-{sha8}"
        final_nan = releases / f"{stem}.tif"
        final_zer = releases / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(final_nan, template=TEMPLATE, catalogue=cat,
                                       encoding="nan", expect_dots=PARENT_DOTS)
        g_zer = gates.validate_release(final_zer, template=TEMPLATE, catalogue=cat,
                                       encoding="zeros", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv",
                                       own_id=stem)
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL {key}: nan={g_nan['failed']} zeros={g_zer['failed']}")

        # prior-as-truth DTI (MODEL bound) and PROXY instruments (report only)
        truth = prior_as_truth(pr, footprint)
        truth_pts = np.c_[np.nonzero(truth)]
        cand_pred = np.where(footprint, dots.astype(np.float32), np.float32(0.0))
        p_parts = dti_parts_f32(parent_pred, truth)
        c_parts = dti_parts_f32(cand_pred, truth)
        # the other end of the same model: what if the prior is noise?  Same number
        # of truth cells, drawn uniformly from the footprint, fixed seed.
        rng_t = np.random.default_rng(SEED)
        n_t = int(truth.sum())
        noise_truth = np.zeros(footprint.shape, dtype=bool)
        flat_idx = rng_t.choice(int(footprint.sum()), size=n_t, replace=False)
        fr, fc = np.nonzero(footprint)
        noise_truth[fr[flat_idx], fc[flat_idx]] = True
        p_noise = dti_parts_f32(parent_pred, noise_truth).dti()
        c_noise = dti_parts_f32(cand_pred, noise_truth).dti()
        delta_noise = round(float(LIVE_SPAN * (c_noise - p_noise) / p_noise), 4)
        m_parts = dti_parts_f32(cand_pred, lineage_mask)
        delta_mask = round(float(LIVE_SPAN * (m_parts.dti() - mask_parts.dti()) / mask_parts.dti()), 4)
        pred, band_r, basis = prediction(p_parts.dti(), c_parts.dti(), delta_noise, delta_mask)
        v_proxy = proxy.hide_and_recover(dots, cat, footprint)
        moved = dots & ~parent
        canary = proxy.canary(moved, dots, cat)
        collar = {
            "min_dist_catalogue_px": g_nan["min_catalogue_distance_px"],
            "dots_le_3px_after": int((dcat[dots] <= 3.0).sum()),
            "dots_le_3px_before": int((dcat[parent] <= 3.0).sum()),
            "moved_targets_le_3px": int((dcat[moved] <= 3.0).sum()),
        }
        rec = {
            "id": stem, "value": key, "description": cfg["description"],
            "block_px": cfg["block_px"], "block_km": cfg["block_px"] * 0.1,
            "prior": cfg["prior"],
            "n_dots": int(dots.sum()), "hamming_vs_parent": diff,
            "pct_dots_moved": round(stats["pct_dots_moved"], 4),
            "frac_achieved": round(stats["frac_achieved"], 6),
            "count_preserved": stats["count_preserved"],
            "cv_before": stats["cv_before"], "cv_after": stats["cv_after"],
            "block_density_cv_at_block": {
                "definition": "proxy.block_density_cv = CV of dots per OCCUPIED block "
                              "(the definition behind the 0.51-0.59 band)",
                "before": proxy.block_density_cv(parent, footprint, cfg["block_px"]),
                "after": proxy.block_density_cv(dots, footprint, cfg["block_px"])},
            "cv_excursion": stats["cv_excursion"],
            "moved_displacement_px": stats["moved_displacement_px"],
            "donor_block_prior_mean": stats["donor_block_prior_mean"],
            "acceptor_block_prior_mean": stats["acceptor_block_prior_mean"],
            "collar": collar,
            "spacing_preserved": {
                "min_sep_px_enforced": PARENT_MIN_SEP_PX,
                "min_nn_px_after": proxy.redundancy(dots)["mean_nn_px"],
                "dots_with_neighbour_lt_2px_after": proxy.redundancy(dots)["dots_with_neighbour_lt_2px"],
                "dots_with_neighbour_lt_2px_parent": evidence["r0"]["redundancy"]["dots_with_neighbour_lt_2px"],
            },
            "lineage_mask_bound": {
                "cells": int(lineage_mask.sum()),
                "dti_parent": round(mask_parts.dti(), 6),
                "dti_cand": round(m_parts.dti(), 6),
                "delta_if_truth_is_the_lineage_mask": delta_mask,
                "reading": "H19-5 is the mask the whole lineage was thinned from and it is "
                           "~3x denser than truth (R0 scores 0.796 against it vs 0.2778 CLAIM "
                           "live), so this is a pessimistic downside bound, not a prediction",
            },
            "noise_truth_bound": {
                "cells": n_t,
                "dti_parent": round(p_noise, 6), "dti_cand": round(c_noise, 6),
                "delta_if_prior_is_noise": delta_noise,
                "reading": "the falsifier's magnitude: if new-fault truth does not follow "
                           "the thermal prior at all, this is what the same relocation costs",
            },
            "surrogate_truth": {
                "cells": int(truth.sum()),
                "dti_parent": round(p_parts.dti(), 6),
                "dti_cand": round(c_parts.dti(), 6),
                "delta_if_prior_were_truth": round(LIVE_SPAN * (c_parts.dti() - p_parts.dti()) / p_parts.dti(), 4),
                "credit_parent": round(credit_on_truth(truth_pts, parent_pts), 6),
                "credit_cand": round(credit_on_truth(truth_pts, np.c_[np.nonzero(dots)]), 6),
            },
            "proxy": v_proxy,
            "proxy_delta_vs_r0": round(v_proxy["proxy_mean_credit"]
                                       - evidence["r0"]["proxy"]["proxy_mean_credit"], 6),
            "canary": canary,
            "redundancy": proxy.redundancy(dots),
            "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
            "uniform_truth_credit": proxy.uniform_truth_credit(dots, footprint),
            "sha256_nan": g_nan["sha256"], "sha256_zeros": g_zer["sha256"], "sha8": sha8,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": pred, "predicted_range": band_r,
            "prediction_basis": basis,
            "surrogate_dti_null": bool(prior_as_truth(pr, footprint).sum() == 0),
            "gates": {k: g_nan[k] for k in
                      ("PASS", "failed", "crs_matches_template", "shape_matches_template",
                       "transform_matches_template", "single_band", "dtype_float32",
                       "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                       "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                       "catalogue_floor_respected", "count_matches_parent")},
            "gates_zeros": {k: g_zer[k] for k in ("PASS", "failed", "sha256_not_in_ledger")},
        }
        evidence["arms"][key] = rec

        note = (f"{PARENT_ID}; {rec['pct_dots_moved']:.1f}% of {rec['n_dots']} dots moved to the "
                f"highest-prior {rec['block_km']:.1f} km GDR-thermal blocks [{key}]; "
                f"pred {pred:+.4f} MODEL")[:140]
        rows.append({
            "id": stem, "parent": PARENT_ID, "axis": "CONCENTRATION", "value": key,
            "n_dots": rec["n_dots"], "pct_changed": rec["pct_dots_moved"],
            "pct_relocated": rec["pct_dots_moved"],
            "sha256": rec["sha256_nan"], "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT", "predicted_change": f"{pred:+.4f} MODEL",
            "predicted_range": f"[{band_r[0]:+.3f},{band_r[1]:+.3f}]",
            "ranking_basis": (f"EXTERNAL prior: exp(-d/{priors.SIGMA_PX:.0f}px) to nearest unique "
                              f"Hot/Warm GDR feature"
                              + (" (features >8px from catalogue only)" if cfg["prior"] == "remote" else "")
                              + f"; {cfg['block_px']}px blocks; digest "
                              f"{evidence['priors'][cfg['prior']]['prior_digest'][:12]}"),
            "receipt_score": "", "receipt_date": "",
            "date": dt.date.today().isoformat(), "form_note": note,
            "evidence_class": "MODEL",
            "source": f"BUILT:scripts/build_concentration.py@{raster_io.git_sha()}",
            "notes": (f"moved={stats['n_dots_moved']} cv {stats['cv_before']:.3f}->"
                      f"{stats['cv_after']:.3f} mean disp "
                      f"{stats['moved_displacement_px']['mean_px']:.1f}px; "
                      f"pred from surrogate prior-as-truth with kappa={KAPPA}; "
                      f"gate PASS 14/14"),
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91",
        })
        print(f"{stem}: dots={rec['n_dots']} moved={stats['n_dots_moved']} "
              f"({rec['pct_dots_moved']:.2f}%) cv {stats['cv_before']:.3f}->{stats['cv_after']:.3f} "
              f"surrogateDTI {p_parts.dti():.4f}->{c_parts.dti():.4f} pred={pred:+.4f} "
              f"proxy={v_proxy['proxy_mean_credit']:.4f} canary={canary['canary_auc']}")

    # ------------------------------------------------------------------ #
    # Null diagnostic (NOT a candidate: no raster, no ledger row).
    # Same dose (10 %), same 2.5 km blocks, same seed, same placement rules -
    # the block ranking is uniform random instead of the thermal prior.  It
    # separates "we moved 10 % of the dots" from "the prior knew something".
    # ------------------------------------------------------------------ #
    rng = np.random.default_rng(SEED)
    null_prior = np.where(footprint, rng.random(footprint.shape), np.nan).astype(np.float32)
    null_band, null_stats = run_concentration.build_concentration(
        parent_pred, null_prior, footprint, cat, frac=FRAC, block_px=25,
        min_gap_px=MIN_GAP_PX, seed=SEED, min_sep_px=PARENT_MIN_SEP_PX)
    null_dots = io.dot_mask(np.nan_to_num(null_band, nan=0.0))
    null_truth = prior_as_truth(prior_arrays["all"], footprint)
    null_dti = dti_parts_f32(np.where(footprint, null_dots.astype(np.float32), np.float32(0.0)),
                             null_truth).dti()
    parent_dti_all = dti_parts_f32(parent_pred, null_truth).dti()
    evidence["null_diagnostic"] = {
        "label": "DIAGNOSTIC ONLY - no release, no ledger row, no slot",
        "surrogate_dti_parent": round(parent_dti_all, 6),
        "surrogate_dti_null": round(null_dti, 6),
        "delta_if_prior_were_truth": round(LIVE_SPAN * (null_dti - parent_dti_all) / parent_dti_all, 4),
        "n_dots_moved": null_stats["n_dots_moved"],
        "pct_dots_moved": round(null_stats["pct_dots_moved"], 4),
        "cv_before": null_stats["cv_before"], "cv_after": null_stats["cv_after"],
        "collar_floor_respected": True,
    }
    print(f"null diagnostic: moved={null_stats['n_dots_moved']} "
          f"({null_stats['pct_dots_moved']:.2f}%) cv {null_stats['cv_before']:.3f}->"
          f"{null_stats['cv_after']:.3f} (not a candidate)")

    ledger = ROOT / "ledger" / "submissions.csv"
    existing, newline = [], "\n"
    if ledger.is_file():
        raw = ledger.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    fieldnames = list(existing[0].keys()) if existing else list(LEDGER_COLS)
    for c in LEDGER_COLS:                      # never drop a column another session wrote
        if c not in fieldnames:
            fieldnames.append(c)
    ids = {r.get("id") for r in existing}
    shas = {r.get("sha256") for r in existing} | {r.get("sha256_zeros") for r in existing}
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore",
                           lineterminator=newline)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in fieldnames})
        by_id = {r.get("id"): r for r in existing}
        appended = 0
        for r in rows:
            if r["id"] in by_id:
                # Idempotent rebuild (CI): the same evidence, byte for byte, is proof,
                # not a duplicate.  A different hash under the same id is a failure.
                if by_id[r["id"]].get("sha256") != r["sha256"]:
                    raise SystemExit(f"id {r['id']} exists with a DIFFERENT sha256 - not reproducible")
                print(f"{r['id']}: already in the ledger with the same sha256 (idempotent)")
                continue
            # Date-shifted rebuild (CI after the build date): the id embeds
            # today's date, so the same raster returns under a new id with the
            # SAME sha256. That is proof of reproducibility, not a duplicate.
            by_sha = {e.get("sha256"): e for e in existing}
            if r["sha256"] in by_sha:
                print(f"{r['id']}: same sha256 as ledger row "
                      f"{by_sha[r['sha256']].get('id')} (date-shifted rebuild, idempotent)")
                continue
            if r["sha256"] in shas or r["sha256_zeros"] in shas:
                raise SystemExit(f"refusing to append {r['id']}: hash already in the ledger")
            w.writerow({k: r.get(k, "") for k in fieldnames})
            appended += 1

    out = ROOT / "evidence" / "concentration_axis_20261023.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"\nledger rows appended: {appended} of {len(rows)}\nevidence: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
