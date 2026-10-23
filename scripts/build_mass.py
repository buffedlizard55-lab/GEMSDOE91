#!/usr/bin/env python3
"""MASS axis on R0: three arms that differ ONLY in how much of the parent's mass is kept.

Parent R0 = `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32), 37,654 unit
dots, sha256 baeae321... (nan) / c55bafc4... (zeros), CLAIM 0.2778.

Why this axis, and why this ranking
-----------------------------------
`ledger/README.md` records that every earlier MASS row used a ranking that was
*not* the parent's own ("0.6*clip(d_catalogue/50)+0.4*uniform(seed88)"), which is
why MASS stayed open.  The parent's real marginal-gain ranking needs
`training_features.tif` (419 MB, never mirrored, absent here).  What the parent's
lineage *is* reproducible from, byte for byte, is its generation field:
`anc_h19_5` (121,131 px), the dense map every dot in this lineage was thinned
from.  A dot's rank here is that field's local density at the dot:

    rank(dot) = gaussian_filter(H19-5 field, sigma = 1 px)[dot]

continuous, so the bottom decile is not a tie group.  (A triangular-kernel
support version was built first and rejected: 4,849 dots tie at exactly 1.0 and
the row-major tie-break pushed the drop to the north of the map - mean row 808
against 1,325.  That draft is in the ledger as SUPERSEDED-DRAFT.)

It is NOT the trained GBM ranking; the deviation is logged as IR-91-16.

Arms (one ranking, one code path, one gate stack)
------------------------------------------------
sup10minus  drop the 3,765 lowest-rank dots                  (10.00 % of R0)
sup24minus  drop the 9,164 lowest-rank dots                  (24.34 % of R0) <-- dose
            matched to the pending PRUNE `le8-norefill` rung, so the two files
            differ only in WHICH dots go, not how many
sup10plus   add the 3,765 highest-rank cells of the same field that are not dots,
            sit >= 3 px from the catalogue and >= 2 px from every other dot
            (greedy, so added dots are also >= 2 px apart)

Constraints: parent reproduced exactly from two pinned ancestors before any edit;
no mass on catalogue pixels; NaN outside the footprint; unit mass; count recorded;
every release re-read from disk and passed through `gems91.release_gates`; every
sha256 checked against the ledger.

COMMON COLLAR NORMALISATION (not part of the axis)
--------------------------------------------------
R0 keeps every dot > 2 px from the catalogue but 1,611 of them sit at 2 < d <= 3 px,
so the brief's constraint 4 ("keep >= 3 px unless AXIS=PRUNE") fails for *any*
R0-derived file (IR-91-03).  All three arms therefore delete those 1,611 dots
identically - the same edit in every arm, which is what keeps the arms comparable -
and every arm then passes `collar_ge_3px`.  Both percentages are recorded: the axis
dose and the total change against R0.

Instrument (REPORT ONLY, never a gate)
--------------------------------------
`sgmc_faults_control` -- the independent USGS/NBMG state-map compilation -- is
scored with the exact DTI algebra twice: raw, and restricted to cells more than
3 px from the known catalogue (the analogue of the organizers' mask).  The raw
version is shown to REVERSE the sign of the parent's own winning steps; the
restricted version reproduces it (see `instrument_calibration` in the evidence).
Predictions come from the restricted version.

Usage
-----
    python3 scripts/build_mass.py --build
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import dti  # noqa: E402  (scripts/dti.py: metric + exact credit)
from gems91 import geom, io, proxy, release_gates as gates  # noqa: E402
from tools import pins  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_H195 = DATA / "registry" / "calib_h195_01922.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"

PARENT_ID = "h33-h33-2-b2-20261004-e5eb6e7e"
PARENT_DOTS = 37654
KERNEL_R = 3                    # px (300 m at 100 m cells)
CAT_FLOOR_PX = 2.0              # the parent's own collar (R0 min = 2.236 px)
BRIEF_FLOOR_PX = 3.0            # brief 4.4: every NEW dot stays >= 3 px out
MIN_DOT_SEPARATION_PX = 2.0     # the parent's own suppression radius (2.83 px ring)
COMMON_COLLAR_PX = 3.0          # brief 4.4 compliance edit, applied identically to EVERY arm
RANK_SIGMA_PX = 1.0             # gaussian smoothing of the generation field

# ---- lineage economics, measured from the parent's own score history ----------
# Both steps below deleted ONLY dots inside the masked catalogue collar, i.e. dots
# whose live credit is provably zero:
#   d2.8 44,090 -> solo 40,199  (3,891 dots)  0.2600 -> 0.2708  (+0.0108)
#   solo 40,199 -> R0   37,654  (2,545 dots)  0.2708 -> 0.2778  (+0.0070)
# 2.75e-6 and 2.78e-6 per dot.  ds = T*0.2*n/den**2  =>  den = T*0.2/2.76e-6 and
# T = score*den at the mid score 0.2743  =>  den = 19,877, T = 5,452.
LIVE_CLAIM = 0.2778
PER_DOT_GAIN = 2.76e-6
DEN_EST = round(0.2743 * 0.2 / PER_DOT_GAIN)          # 19,877
T_EST = round(0.2743 * DEN_EST)                       # 5,452
DEN_ALT = 42800.0                                     # upper bracket: 0.8|G| >= den - 0.2S

ARMS = {
    "sup10minus": dict(kind="drop", n=3765,
                       label="drop the lowest-rank 10% of R0 dots"),
    "sup24minus": dict(kind="drop", n=9164,
                       label="drop the lowest-rank 24.34% (dose-matched to PRUNE le8)"),
    "sup10plus": dict(kind="add", n=3765,
                      label="add the highest-rank 10% of undotted field cells"),
}

LEDGER_COLS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
    "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
    "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
    "evidence_class", "source", "notes", "source_url",
]


def tri_kernel(radius: int = KERNEL_R) -> np.ndarray:
    k = np.zeros((2 * radius + 1, 2 * radius + 1), dtype=np.float32)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            k[dy + radius, dx + radius] = max(0.0, 1.0 - np.hypot(dy, dx) / radius)
    return k


def field_rank(field: np.ndarray, sigma: float = RANK_SIGMA_PX) -> np.ndarray:
    """Continuous rank surface: local density of the parent's own generation field."""
    return ndi.gaussian_filter(field.astype(np.float32), sigma, mode="constant")


def rebuild_parent() -> dict:
    """Gate 0: the parent's dot set must come back exactly from two ancestors."""
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
        "dots_inside_3px": int((parent & (dcat < BRIEF_FLOOR_PX)).sum()),
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


def build_arm(key: str, parent: np.ndarray, dcat: np.ndarray, rank: np.ndarray,
              field: np.ndarray) -> dict:
    cfg = ARMS[key]
    ys, xs = np.nonzero(parent)
    r = rank[ys, xs]

    if cfg["kind"] == "drop":
        n = int(cfg["n"])
        order = np.lexsort((xs, ys, r))           # rank asc, ties row-major
        chosen = order[:n]
        removed = np.zeros_like(parent)
        removed[ys[chosen], xs[chosen]] = True
        dots = parent & ~removed
        if int(removed.sum()) != n:
            raise SystemExit(f"{key}: removed {int(removed.sum())} != requested {n}")
        info = {
            "n_changed": n,
            "rank_range_removed": [round(float(r[chosen].min()), 6),
                                   round(float(r[chosen].max()), 6)],
            "rank_next_kept": round(float(np.sort(r)[n]), 6),
            "rank_tie_share_removed": round(float(np.mean(r[chosen] == r[chosen].max())), 4),
            "dcat_removed_median_px": round(float(np.median(dcat[ys[chosen], xs[chosen]])), 3),
            "dcat_removed_max_px": round(float(dcat[ys[chosen], xs[chosen]].max()), 3),
            "removed_in_collar_lt3px": int((dcat[ys[chosen], xs[chosen]] < 3.0).sum()),
            "mean_row_removed": round(float(ys[chosen].mean()), 1),
            "mean_row_kept": round(float(np.delete(ys, chosen).mean()), 1),
        }
    else:
        n = int(cfg["n"])
        ddot = ndi.distance_transform_edt(~parent)
        pool = field & ~parent & (dcat >= BRIEF_FLOOR_PX) & (ddot >= MIN_DOT_SEPARATION_PX)
        pys, pxs = np.nonzero(pool)
        if len(pys) < n:
            raise SystemExit(f"{key}: pool {len(pys)} < {n} requested")
        pr = rank[pys, pxs]
        order = np.lexsort((pxs, pys, -pr))       # rank desc, ties row-major
        # greedy: keep the parent's own suppression radius among the added dots too
        tree = cKDTree(np.c_[ys, xs].astype(np.float64))
        keep: list[int] = []
        added_pts: list[tuple[float, float]] = []
        for i in order:
            pt = (float(pys[i]), float(pxs[i]))
            if tree.query(pt, k=1)[0] < MIN_DOT_SEPARATION_PX:
                continue                      # too close to a parent dot
            if added_pts:
                d = np.hypot(*(np.asarray(added_pts) - np.asarray(pt)).T)
                if d.min() < MIN_DOT_SEPARATION_PX:
                    continue                  # too close to an already-added dot
            keep.append(i)
            added_pts.append(pt)
            if len(keep) == n:
                break
        if len(keep) < n:
            raise SystemExit(f"{key}: only {len(keep)} legal cells, needed {n}")
        pick = np.asarray(keep)
        added = np.zeros_like(parent)
        added[pys[pick], pxs[pick]] = True
        dots = parent | added
        arr_pts = np.asarray(added_pts)
        sub = arr_pts[:2000]                       # sampled: O(n^2) otherwise
        dd = np.hypot(sub[:, None, 0] - arr_pts[None, :, 0],
                      sub[:, None, 1] - arr_pts[None, :, 1])
        np.fill_diagonal(dd[:, :2000], np.inf)     # exclude self-distance
        adj = [float(v) for v in dd.min(axis=1)]
        info = {
            "n_changed": n,
            "pool_size": int(len(pys)),
            "rank_min_added": round(float(pr[pick].min()), 6),
            "rank_max_added": round(float(pr[pick].max()), 6),
            "min_separation_added_px": round(float(min(adj)), 3) if adj else None,
            "median_separation_added_px": round(float(np.median(adj)), 3) if adj else None,
            "dcat_added_min_px": round(float(dcat[pys[pick], pxs[pick]].min()), 3),
            "dcat_added_median_px": round(float(np.median(dcat[pys[pick], pxs[pick]])), 3),
        }
    info["dots"] = dots
    return info


def catalogue_credit(dot: np.ndarray, cat: np.ndarray) -> float:
    """Kernel credit against the mapped catalogue. Masked live => an UPPER bound."""
    d = ndi.distance_transform_edt(~cat)
    return float(np.clip(1.0 - d[dot] / KERNEL_R, 0.0, 1.0).sum())


def instrument_delta(parent: np.ndarray, dots: np.ndarray, truth: np.ndarray) -> dict:
    """Delta of the exact DTI components between parent and candidate on a truth surrogate."""
    a = dti.components(parent.astype(np.float32), truth)
    b = dti.components(dots.astype(np.float32), truth)
    dT = b.T - a.T
    dsm = (b.S - b.M) - (a.S - a.M)
    return {"dti_parent": round(a.score, 6), "dti_candidate": round(b.score, 6),
            "delta_dti": round(b.score - a.score, 6),
            "dT": round(dT, 3), "dS_minus_M": round(dsm, 3),
            "dden": round(0.2 * dT + 0.2 * dsm, 3),
            "G": int(b.G)}


def predict_from_instrument(inst: dict) -> dict:
    """MODEL projection: instrument credit change -> live score change.

    ds_live = dT/den - DTI_live * dden/den

    dT and dden are measured on the instrument; the mapping assumes the withheld
    new-fault truth carries credit of the same order as the restrained SGMC
    compilation (the only unmasked fault map here).  den is bracketed by the
    lineage-derived 19,877 and the alpha-mass bound 42,800; dT is also scaled
    by 0.5 and 2.0 to price the assumption.
    """
    dT, dden = inst["dT"], inst["dden"]
    out = {}
    for name, den in (("central", DEN_EST), ("alt", DEN_ALT)):
        ds = dT / den - LIVE_CLAIM * dden / den
        out[name] = round(float(ds), 4)
    lo = min(0.5 * dT / DEN_EST - LIVE_CLAIM * (0.5 * dT + 0.2 * inst["dS_minus_M"]) / DEN_EST,
             2.0 * dT / DEN_EST - LIVE_CLAIM * (2.0 * dT + 0.2 * inst["dS_minus_M"]) / DEN_EST,
             out["alt"])
    hi = max(0.5 * dT / DEN_EST - LIVE_CLAIM * (0.5 * dT + 0.2 * inst["dS_minus_M"]) / DEN_EST,
             2.0 * dT / DEN_EST - LIVE_CLAIM * (2.0 * dT + 0.2 * inst["dS_minus_M"]) / DEN_EST,
             out["alt"])
    return {"central": out["central"], "range": [round(float(lo - 0.004), 3),
                                                 round(float(hi + 0.004), 3)],
            "alt_den": out["alt"],
            "basis": (f"restrained-SGMC dT={dT:+.1f}, dden={inst['dden']:+.1f}; "
                      f"den={DEN_EST} (bracket {DEN_ALT:.0f}); DTI_live={LIVE_CLAIM} CLAIM")}


def prune_ladder_comparison(parent: np.ndarray, dcat: np.ndarray, truth: np.ndarray) -> dict:
    """REPORT ONLY: score the pending PRUNE rungs with the same instrument.

    Rebuilds the three `le*-norefill` rows from the ledger (R0 minus every dot
    inside d_cat <= L) so the human can see how this session's ranking compares
    at a matched dose.  These are measurements of EXISTING ledger rows, not new
    candidates: nothing is written.
    """
    out = {}
    for label, limit in (("le3", 3.0), ("le8", 8.0), ("le15", 15.0)):
        dots = parent & ~(dcat <= limit)
        inst = instrument_delta(parent, dots, truth)
        pred = predict_from_instrument(inst)
        out[label] = {"n_dots": int(dots.sum()), "removed": int((parent & ~dots).sum()),
                      "pct_changed": round(100.0 * (parent & ~dots).sum() / parent.sum(), 3),
                      "instrument": inst, "predicted_change_MODEL": pred["central"],
                      "predicted_range": pred["range"]}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    if not args.build:
        print(__doc__)
        return 0

    inputs = [TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS, ANC_H195, ANC_D28, ANC_SOLO, SGMC]
    ok, res = pins.check_paths(inputs)
    for r in res:
        print(f"[{'ok' if r['ok'] else 'REFUSE'}] {Path(r['path']).name}: {r['detail']}")
    if not ok:
        raise SystemExit("an input is not pinned - refusing to build (brief 4.2)")

    template = io.read_grid(TEMPLATE)
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    field = io.dot_mask(io.read_grid(ANC_H195))
    rank = field_rank(field)

    lineage = rebuild_parent()
    if not (lineage["twins_identical"] and lineage["n_dots"] == PARENT_DOTS
            and all(v["identical_to_parent"] for v in lineage["rebuilt_from"].values())):
        raise SystemExit(f"PARENT NOT REPRODUCED - stopping (brief 5): {lineage}")
    print(f"parent reproduced: {lineage['n_dots']} dots, digest {lineage['parent_dot_digest'][:8]}, "
          f"from {list(lineage['rebuilt_from'])}")

    sgmc = io.read_grid(SGMC) > 0
    truth_raw = sgmc.astype(np.float32)
    truth_restr = (sgmc & (dcat > KERNEL_R)).astype(np.float32)   # mask analogue

    # ---- instrument calibration on the parent's own ladder ---------------------
    ladder = {"H19_5": ANC_H195, "d2.8": ANC_D28, "solo": ANC_SOLO, "R0": PARENT_NAN}
    calib = {}
    prev = None
    for name, path in ladder.items():
        dots = io.dot_mask(io.read_grid(path))
        rec = {"n_dots": int(dots.sum())}
        for tag, truth in (("raw", truth_raw), ("restricted", truth_restr)):
            c = dti.components(dots.astype(np.float32), truth)
            rec[f"dti_{tag}"] = round(c.score, 6)
        if prev is not None:
            rec["d_dti_raw"] = round(rec["dti_raw"] - prev["dti_raw"], 6)
            rec["d_dti_restricted"] = round(rec["dti_restricted"] - prev["dti_restricted"], 6)
        calib[name] = rec
        prev = rec
    print("instrument calibration (live CLAIMs 0.1922/0.2600/0.2708/0.2778):")
    for k, v in calib.items():
        print(f"  {k:6s} {v['n_dots']:6d}  raw {v['dti_raw']:.5f} "
              f"restricted {v['dti_restricted']:.5f}"
              + (f"  d_raw {v.get('d_dti_raw', 0):+.5f} d_restr {v.get('d_dti_restricted', 0):+.5f}"
                 if 'd_dti_raw' in v else ""))

    r0_cat_credit = catalogue_credit(parent, cat)
    r0_proxy = proxy.hide_and_recover(parent, cat, footprint)
    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    releases = ROOT / "releases"
    releases.mkdir(exist_ok=True)
    ledger = ROOT / "ledger" / "submissions.csv"
    existing_hashes: set[str] = set()
    hash_owner: dict[str, str] = {}          # sha256 -> ledger id, for rebuilds
    if ledger.is_file():
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                for c in ("sha256", "sha256_zeros"):
                    v = (r.get(c) or "").strip()
                    if v:
                        existing_hashes.add(v)
                        hash_owner[v] = (r.get("id") or "").strip()

    rows, evidence = [], {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "axis": "MASS", "parent": PARENT_ID, "lineage": lineage,
        "ranking": {"input": "anc_h19_5 (pinned generation field, 121,131 px)",
                    "definition": "gaussian_filter(H19-5, sigma=1 px) at the cell",
                    "tie_break": "row-major (x, then y); no tie group above 0.02% of dots",
                    "rejected_variant": ("triangular-kernel support: 4,849 dots tie at 1.0 and "
                                         "the row-major tie-break biased the drop north "
                                         "(mean row 808 vs 1,325)"),
                    "not_the_same_as": ("the parent's trained GBM marginal-gain ranking "
                                        "(needs training_features.tif, absent) - IR-91-16")},
        "economics": {"LIVE_CLAIM": LIVE_CLAIM, "per_dot_gain_MODEL": PER_DOT_GAIN,
                      "den_est": DEN_EST, "T_est": T_EST, "den_alt": DEN_ALT},
        "instrument_calibration": calib,
        "r0": {"catalogue_credit": round(r0_cat_credit, 3), "proxy": r0_proxy,
               "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
               "redundancy": proxy.redundancy(parent)},
        "arms": {},
    }

    for key, cfg in ARMS.items():
        built = build_arm(key, parent, dcat, rank, field)
        axis_dots = built.pop("dots")
        # brief 4.4 compliance, IDENTICAL in every arm: R0's 2<d<=3 px dots go
        dots = axis_dots & (dcat > COMMON_COLLAR_PX)
        collar_removed = int((axis_dots & ~dots).sum())
        diff = gates.parent_diff(parent, dots)

        tmp_nan = releases / "_tmp-nan.tif"
        tmp_zer = releases / "_tmp-zeros.tif"
        arr = np.where(footprint, dots.astype("float32"), np.float32(np.nan))
        io.write_float32(tmp_nan, arr, encoding="nan", template=TEMPLATE)
        io.write_float32(tmp_zer, arr, encoding="zeros", template=TEMPLATE)
        sha8 = io.sha256_file(tmp_nan)[:8]
        stem = f"{PARENT_ID}-MASS{key}-{today}-{sha8}"
        final_nan = releases / f"{stem}.tif"
        final_zer = releases / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(final_nan, template=TEMPLATE, catalogue=cat,
                                       encoding="nan")
        g_zer = gates.validate_release(final_zer, template=TEMPLATE, catalogue=cat,
                                       encoding="zeros")
        # a rebuild of an already-recorded file is not a duplicate: the ledger row
        # that owns these hashes must be THIS id (same rule as release_gates)
        unseen = all(h not in existing_hashes or hash_owner.get(h) == stem
                     for h in (g_nan["sha256"], g_zer["sha256"]))
        if not (g_nan["PASS"] and g_zer["PASS"] and unseen):
            raise SystemExit(f"GATE FAIL {key}: nan={g_nan['failed']} zeros={g_zer['failed']} "
                             f"unseen={unseen}")

        removed = int((parent & ~dots).sum())
        added = int((~parent & dots).sum())
        n_changed = removed + added
        pct = 100.0 * n_changed / PARENT_DOTS
        pct_axis = 100.0 * int(built["n_changed"]) / PARENT_DOTS
        cat_lost = catalogue_credit(parent & ~dots, cat) if removed else 0.0
        inst_r = instrument_delta(parent, dots, truth_restr)
        inst_raw = instrument_delta(parent, dots, truth_raw)
        pred = predict_from_instrument(inst_r)
        v_proxy = proxy.hide_and_recover(dots, cat, footprint)
        can = proxy.canary(dots & ~parent, dots, cat)

        rec = {
            "id": stem, "axis": "MASS", "value": key, "description": cfg["label"],
            "n_dots": int(dots.sum()), "removed": removed, "added": added,
            "collar_normalised_removed": collar_removed,
            "pct_changed_of_parent": round(pct, 4),
            "pct_axis_dose_of_parent": round(pct_axis, 4), "hamming_vs_parent": diff,
            "rank_stats": built,
            "catalogue_credit_lost": round(cat_lost, 3),
            "catalogue_credit_share_lost_pct": round(100.0 * cat_lost / r0_cat_credit, 3),
            "sha256_nan": g_nan["sha256"], "sha256_zeros": g_zer["sha256"], "sha8": sha8,
            "dot_set_digest": g_nan["dot_set_digest"],
            "min_catalogue_distance_px": g_nan["min_catalogue_distance_px"],
            "n_dots_inside_3px_collar": int((dots & (dcat < BRIEF_FLOOR_PX)).sum()),
            "proxy": v_proxy,
            "proxy_delta_vs_r0": round(v_proxy["proxy_mean_credit"]
                                       - r0_proxy["proxy_mean_credit"], 6),
            "canary": can,
            "instrument_restricted": inst_r, "instrument_raw": inst_raw,
            "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
            "redundancy": proxy.redundancy(dots),
            "predicted_change_MODEL": pred["central"],
            "predicted_range": pred["range"],
            "predicted_change_at_alt_den": pred["alt_den"],
            "prediction_basis": pred["basis"],
            "gates": {k: g_nan[k] for k in
                      ("PASS", "failed", "crs_matches_template", "shape_matches_template",
                       "transform_matches_template", "single_band", "dtype_float32",
                       "no_nan_inside_footprint", "nan_outside_footprint",
                       "values_within_0_1", "unit_mass_dots", "zero_catalogue_mass",
                       "min_catalogue_distance_px", "n_dots")},
            "gates_zeros": {k: g_zer[k] for k in ("PASS", "failed", "zeros_outside_footprint")},
        }
        evidence["arms"][key] = rec

        if added:
            change_txt = (f"add {added} highest-field-rank cells, drop {collar_removed} collar dots "
                          f"({pct:.2f}%), count {int(dots.sum())}")
        else:
            change_txt = (f"drop {removed} lowest-field-rank dots ({pct:.2f}%, "
                          f"{collar_removed} of them the common collar), count {int(dots.sum())}")
        note = f"{PARENT_ID}; {change_txt}; pred {pred['central']:+.3f} MODEL"[:140]
        rows.append({
            "id": stem, "parent": PARENT_ID, "axis": "MASS", "value": key,
            "n_dots": int(dots.sum()), "pct_changed": round(pct, 4), "pct_relocated": "",
            "sha256": g_nan["sha256"], "sha256_zeros": g_zer["sha256"],
            "status": "BUILT",
            "predicted_change": f"{pred['central']:+.4f} MODEL",
            "predicted_range": f"[{pred['range'][0]:+.3f},{pred['range'][1]:+.3f}]",
            "ranking_basis": ("H19-5 generation-field rank (gaussian sigma=1 px); "
                              "not the trained marginal-gain ranking (IR-91-16)"),
            "receipt_score": "", "receipt_date": "", "date": dt.date.today().isoformat(),
            "form_note": note, "evidence_class": "MODEL",
            "source": "SESSION 5 (arena/7dffc20d, MASS)",
            "notes": (f"removed={removed} added={added} (incl. {collar_removed} collar>3px in "
                      f"every arm); catalogue credit lost {cat_lost:.1f} "
                      f"({100*cat_lost/max(r0_cat_credit,1e-9):.1f}% of R0's); restrained-SGMC "
                      f"dT={inst_r['dT']:+.1f} dden={inst_r['dden']:+.1f}; all gates pass"),
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91",
        })
        print(f"{stem}: dots={int(dots.sum())} -{removed} +{added} ({pct:.2f}%) "
              f"cat_lost={cat_lost:.1f} inst_dT={inst_r['dT']:+.1f} "
              f"inst_dden={inst_r['dden']:+.1f} pred={pred['central']:+.4f} "
              f"{pred['range']}")

    # ---- how the pending PRUNE rungs look under the same instrument ------------
    evidence["prune_ladder_measured_with_same_instrument"] = prune_ladder_comparison(
        parent, dcat, truth_restr)
    for label, rec in evidence["prune_ladder_measured_with_same_instrument"].items():
        print(f"  [report] PRUNE {label}: {rec['n_dots']} dots ({rec['pct_changed']:.2f}%) "
              f"inst_dT={rec['instrument']['dT']:+.1f} "
              f"pred={rec['predicted_change_MODEL']:+.4f} {rec['predicted_range']}")

    # ---- ledger append (never drop a column another session wrote) --------------
    existing_rows, newline = [], "\n"
    if ledger.is_file():
        raw = ledger.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing_rows = list(csv.DictReader(fh))
    fieldnames = list(existing_rows[0].keys()) if existing_rows else []
    for c in LEDGER_COLS:
        if c not in fieldnames:
            fieldnames.append(c)
    ids = {r["id"] for r in existing_rows}
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore",
                           lineterminator=newline)
        w.writeheader()
        for r in existing_rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
        for r in rows:
            if r["id"] not in ids:
                w.writerow({k: r.get(k, "") for k in fieldnames})

    out = ROOT / "evidence" / "mass_axis_20261023.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"\nledger rows appended: {len(rows)}\nevidence: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
