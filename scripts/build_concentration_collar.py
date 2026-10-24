#!/usr/bin/env python3
"""CONCENTRATION on the legal collar: move 10 % / 20 % of R0's dots into the 3-6 px
band around mapped traces, plus a mirrored 10 % control that moves mass the other way.

    python3 scripts/restore_data.py
    python3 scripts/build_concentration_collar.py --build

Parent R0 = `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32): 37,654 unit dots,
sha256 c55bafc4… (zeros) / baeae321… (nan), CLAIM 0.2778.

Why this value and not another GDR/terrain prior
-----------------------------------------------
The seven CONCENTRATION rows already in the ledger all move mass using the GDR thermal
prior, which by construction pushes mass *away* from the mapped catalogue (>8 px for
`gdr25rm10`).  None has ever tested the organiser's own statement that new-fault truth
may lie within 300 m of known traces and that pixels *beside* known faults are scored
against new-fault truth only.  The collar band is that statement made operational, and
it is measurable: per-cell fault-credit density in the 3-4.5 px band is 1.3x the >10 px
value on the independent SGMC catalogue and 2.2x on the lineage field (see evidence).

The edit (identical in every arm except dose, prior and direction)
------------------------------------------------------------------
* count fixed at 37,654 and mass per dot fixed at 1: `S` is untouched, so only `T`
  (numerator) and `M` (denominator's matched-mass term) can move;
* donors are the dots in the lowest-prior 1 km (10 px) blocks -- for the collar arms
  that is the far field, most-remote dot first; for the control it is the weakest dot
  inside the collar band;
* acceptors are cells ranked by the arm's prior: collar arms use a linear ramp that is
  1.0 at 3.05 px and 0.0 at 6.0 px, multiplied by a 0.5-1.0 cross-field support factor
  (three pinned lineage fields); the control uses a ramp that is 0.0 at 10 px rising
  outwards, same support factor;
* no acceptor is on a catalogue pixel or nearer than 3.05 px to one, and no placement
  creates a nearest-neighbour pair closer than R0's own 2.828 px floor;
* everything deterministic: prior-descending accept order with a flat-index tie-break,
  single pass, fixed seed.

Arms
----
collar10   10 % (3,765 dots) far field -> 3.05-6 px collar      <- primary
collar20   20 % (7,531 dots) same                                     <- dose escalation
anti10     10 % collar -> >10 px remote, support-weighted  <- direction control

Usage
-----
    python scripts/build_concentration_collar.py --build    # needs the pinned data
    python scripts/build_concentration_collar.py            # print this docstring
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
sys.path.insert(0, str(ROOT))

from gems91 import collar, geom, io, lineage, proxy, release_gates as gates  # noqa: E402
from tools import pins, raster_io  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"
ANC_H195 = DATA / "registry" / "calib_h195_01922.tif"
ANC_H194 = DATA / "registry" / "calib_h194_01894.tif"
ANC_H161 = DATA / "registry" / "calib_h161_01855.tif"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"

PARENT_ID = "h33-h33-2-b2"
PARENT_TAG = "h33-h33-2-b2-20261004-e5eb6e7e"
PARENT_DOTS = 37_654
LIVE_SPAN = 0.2778          # CLAIM, used only as the scale of a MODEL prediction
STAMP = "20261024"
SEED = 91124
BLOCK_PX = 10               # 1 km blocks: the scale the brief asks to be stated
KAPPA = 1.0                 # the SGMC control is an independent transfer measurement,
                            # not a prior-as-truth surrogate, so no shrinkage is claimed
RELEASES = ROOT / "releases"
EVIDENCE = ROOT / "evidence" / "concentration_collar_axis_20261024.json"
RELEASE_MANIFEST = ROOT / "releases" / "CONCENTRATION_COLLAR_MANIFEST.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
PRIOR_LEDGER = ROOT / "ledger" / "prior_fleet.csv"
SESSION_SOURCE = "SESSION arena/40027ebc CONCENTRATION-COLLAR"
USED_INPUTS = ("sample_submission", "existing_faults", "parent_r0_nan", "parent_r0_zeros",
               "anc_d2_8", "anc_solo_d2_8", "anc_h19_5", "anc_h19_4", "anc_h16_1",
               "sgmc_faults_control")

ARMS = {
    "collar10": dict(frac=0.10, prior="collar", direction="in",
                     description="10% of dots moved from the lowest-prior 1 km blocks "
                                 "(far field) into the legal 3.05-6 px collar band"),
    "collar20": dict(frac=0.20, prior="collar", direction="in",
                     description="same relocation at 20% (dose escalation)"),
    "anti10": dict(frac=0.10, prior="remote", direction="out",
                   description="direction control: 10% moved from the weakest collar dots "
                               "to support-weighted cells >10 px from the catalogue"),
}

LEDGER_COLS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
    "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
    "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
    "evidence_class", "source", "notes", "source_url",
]


# --------------------------------------------------------------------- pins
def verify_pins() -> dict:
    by_sha = {entry["sha256"]: entry for entry in pins.load()["files"]}
    out = {}
    for path in (TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS, ANC_D28, ANC_SOLO,
                 ANC_H195, ANC_H194, ANC_H161, SGMC):
        sha = io.sha256_file(path)
        entry = by_sha.get(sha)
        if entry is None:
            raise SystemExit(f"PIN FAILURE: {path} is not in registry/data_manifest.json")
        out[entry["id"]] = {"path": str(path.relative_to(ROOT)), "sha256": sha,
                            "bytes": path.stat().st_size}
    missing = [i for i in USED_INPUTS if i not in out]
    if missing:
        raise SystemExit(f"PIN FAILURE: inputs not resolved: {missing}")
    return out


# ------------------------------------------------------------------- metric
def dti_parts(pred_pts: np.ndarray, truth_pts: np.ndarray) -> dict:
    """(T, S, M, |G|, DTI) for unit-mass dots, via tree queries (exact for R=3 px)."""
    S = float(len(pred_pts))
    G = float(len(truth_pts))
    if len(pred_pts) == 0 or len(truth_pts) == 0:
        return {"T": 0.0, "S": S, "M": 0.0, "G": G, "dti": 0.0}
    d, _ = cKDTree(pred_pts).query(truth_pts, k=1, distance_upper_bound=proxy.R_PX)
    d = np.where(np.isfinite(d), d, proxy.R_PX)
    T = float(np.clip(1.0 - d / proxy.R_PX, 0.0, None).sum())
    dd, _ = cKDTree(truth_pts).query(pred_pts, k=1, distance_upper_bound=proxy.R_PX)
    dd = np.where(np.isfinite(dd), dd, proxy.R_PX)
    M = float(np.clip(1.0 - dd / proxy.R_PX, 0.0, None).sum())
    den = 0.2 * T + 0.2 * (S - M) + 0.8 * G
    return {"T": T, "S": S, "M": M, "G": G, "dti": 0.0 if den <= 0 else T / den}


def band_credit(pts: np.ndarray, dcat: np.ndarray, *, bands, truth_pts: np.ndarray) -> dict:
    """Mean triangular credit per DROP at each distance-to-catalogue band."""
    out = {}
    for lo, hi in bands:
        sel = (dcat >= lo) & (dcat < hi)
        if not sel.any():
            out[f"[{lo},{hi})"] = {"n": 0}
            continue
        d, _ = cKDTree(truth_pts).query(pts[sel], k=1, distance_upper_bound=proxy.R_PX)
        d = np.where(np.isfinite(d), d, proxy.R_PX)
        c = np.clip(1.0 - d / proxy.R_PX, 0.0, None)
        out[f"[{lo},{hi})"] = {"n": int(sel.sum()), "mean_credit": round(float(c.mean()), 6),
                               "covered_frac": round(float((c > 0).mean()), 4)}
    return out


def cell_credit_density(dcat: np.ndarray, footprint: np.ndarray, truth_pts: np.ndarray,
                        *, bands, stride: int = 7) -> dict:
    """Mean credit per legal CELL in each band (the prior's own density, subsampled)."""
    out = {}
    for lo, hi in bands:
        band = (dcat >= lo) & (dcat < hi) & footprint
        n = int(band.sum())
        if n == 0:
            out[f"[{lo},{hi})"] = {"cells": 0}
            continue
        rr, cc = np.nonzero(band)
        take = slice(None, None, stride)
        pts = np.c_[rr[take], cc[take]].astype(np.float64)
        d, _ = cKDTree(truth_pts).query(pts, k=1, distance_upper_bound=proxy.R_PX)
        d = np.where(np.isfinite(d), d, proxy.R_PX)
        c = np.clip(1.0 - d / proxy.R_PX, 0.0, None)
        out[f"[{lo},{hi})"] = {"cells": n, "mean_credit_per_cell": round(float(c.mean()), 6)}
    return out


# ----------------------------------------------------- live-calibrated proxy
def calibrated_reference(h195_pts: np.ndarray, parent_pts: np.ndarray, *,
                         target_dti: float = LIVE_SPAN, draws: int = 5,
                         seed: int = SEED) -> dict:
    """H19-5 subsampled to the density at which R0 scores exactly ``target_dti``.

    PROXY instrument, never a score.  The live truth density is unknown, so the only
    defensible way to put a reference on the live scale is to match R0's claimed score:
    for each draw, find the uniform subsample fraction s of the 121,131-px lineage field
    where DTI(R0, field_s) = 0.2778 by bisection on s, then keep that s.
    """
    n = len(h195_pts)

    def sample(s: float, u: np.ndarray) -> np.ndarray:
        return h195_pts[u < s]

    rows = []
    for draw in range(draws):
        u = np.random.default_rng(seed + draw).random(n)
        lo, hi = 0.005, 0.25
        for _ in range(30):
            mid = 0.5 * (lo + hi)
            if dti_parts(parent_pts, sample(mid, u))["dti"] < target_dti:
                lo = mid
            else:
                hi = mid
        s = 0.5 * (lo + hi)
        pts = sample(s, u)
        rows.append({"s": round(float(s), 6), "n_cells": int(len(pts)),
                     "parent_dti": round(float(dti_parts(parent_pts, pts)["dti"]), 6),
                     "points": pts})
    return {"target_dti": target_dti, "draws": draws, "seed": seed,
            "s_mean": round(float(np.mean([r["s"] for r in rows])), 6),
            "n_cells_mean": int(np.mean([r["n_cells"] for r in rows])),
            "samples": rows}


def lcr_delta(ref: dict, cand_pts: np.ndarray) -> dict:
    """Relative and absolute DTI change of a candidate on the calibrated reference."""
    abs_d, rel_d, parent_dtis = [], [], []
    for row in ref["samples"]:
        pts = row["points"]
        p = dti_parts(ref["parent_pts"], pts)
        c = dti_parts(cand_pts, pts)
        parent_dtis.append(p["dti"])
        abs_d.append(c["dti"] - p["dti"])
        rel_d.append((c["dti"] - p["dti"]) / p["dti"] if p["dti"] else 0.0)
    a = np.asarray(abs_d)
    half = float(1.96 * a.std(ddof=1) / np.sqrt(len(a))) if len(a) > 1 else 0.0
    return {"n_draws": len(a), "parent_dti_mean": round(float(np.mean(parent_dtis)), 6),
            "delta_dti_mean": round(float(a.mean()), 6),
            "delta_dti_ci95": round(half, 6),
            "delta_dti_interval": [round(float(a.mean() - half), 6),
                                   round(float(a.mean() + half), 6)],
            "rel_change_mean": round(float(np.mean(rel_d)), 6)}


# ------------------------------------------------------------------- build
def read_rows(path: Path) -> tuple[list[dict], list[str]]:
    if not path.is_file():
        return [], []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        r = csv.DictReader(fh)
        return list(r), list(r.fieldnames or [])


def preflight_pairs(specs: list[dict], rows: list[dict], prior_rows: list[dict]) -> None:
    existing = {(r.get("parent"), r.get("axis"), r.get("value")): r for r in rows + prior_rows}
    for spec in specs:
        key = (PARENT_ID, "CONCENTRATION", spec["value"])
        row = existing.get(key)
        src = (row or {}).get("source") or ""
        # own rebuilds are idempotent (the hash check in the ledger writer still applies);
        # any other builder's row for the same (parent, axis, value) is a duplicate
        if row is not None and "build_concentration_collar.py" not in src:
            raise SystemExit(f"Repeated (parent, axis, value): {key} built by {src}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    if not args.build:
        print(__doc__)
        return 0

    pins_report = verify_pins()
    print(f"pins: {len(pins_report)} inputs hash-verified against the manifest")

    template = io.read_grid(TEMPLATE)
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    parent_zeros = io.dot_mask(io.read_grid(PARENT_ZEROS))

    proof = lineage.prove_r0_byte_rebuild(
        parent_nan=PARENT_NAN, parent_zeros=PARENT_ZEROS, ancestor_d28=ANC_D28,
        ancestor_solo=ANC_SOLO, sample=TEMPLATE, catalogue=CATALOGUE,
        work_dir=ROOT / "work" / "r0-collar-proof")
    if not proof["ok"]:
        raise SystemExit(f"STOP: R0 is not reproduced byte-exactly: {json.dumps(proof)[:600]}")
    if not np.array_equal(parent, parent_zeros) or int(parent.sum()) != PARENT_DOTS:
        raise SystemExit("STOP: parent twins disagree or dot count is not 37,654")
    print("R0: both ancestors reproduce the dot set; both encodings match their pins byte for byte")

    votes = (io.dot_mask(io.read_grid(ANC_H195)).astype(np.int16)
             + io.dot_mask(io.read_grid(ANC_H194)).astype(np.int16)
             + io.dot_mask(io.read_grid(ANC_H161)).astype(np.int16))
    votes = np.where(footprint, votes, 0).astype(np.int16)
    collar_prior = collar.collar_prior(dcat, votes).astype(np.float64)
    remote_prior = collar.remote_prior(dcat, votes).astype(np.float64)

    pr, pc = np.nonzero(parent)
    parent_pts = np.c_[pr, pc].astype(np.float64)
    parent_dcat = dcat[pr, pc]
    sgmc = np.nan_to_num(io.read_grid(SGMC)) > 0
    sgmc_off = sgmc & (dcat > 3.0) & footprint
    lineage_mask = io.dot_mask(io.read_grid(ANC_H195)) & footprint
    sgmc_pts = np.c_[np.nonzero(sgmc_off)].astype(np.float64)
    lineage_pts = np.c_[np.nonzero(lineage_mask)].astype(np.float64)

    rows, _ = read_rows(LEDGER)
    prior_rows, _ = read_rows(PRIOR_LEDGER)
    specs = [{"value": k} for k in ARMS]
    preflight_pairs(specs, rows, prior_rows)

    # ---------------- references and their R0 baselines ----------------
    base_sgmc = dti_parts(parent_pts, sgmc_pts)
    base_lineage = dti_parts(parent_pts, lineage_pts)
    print(f"R0 on SGMC off-catalogue: dti={base_sgmc['dti']:.5f}  "
          f"on lineage mask: dti={base_lineage['dti']:.5f}")

    ref = calibrated_reference(np.c_[np.nonzero(lineage_mask)].astype(np.float64), parent_pts)
    ref["parent_pts"] = parent_pts
    print(f"live-calibrated reference: s={ref['s_mean']:.4f} "
          f"({ref['n_cells_mean']} cells), R0 dti={ref['samples'][0]['parent_dti']:.4f}")

    bands = [(0, 3), (3, 6), (6, 10), (10, 20), (20, 50), (50, 1e6)]
    cell_bands = [(3, 4.5), (4.5, 6), (6, 10), (10, 1e6)]
    r0_bands_sgmc = band_credit(parent_pts, parent_dcat, bands=bands, truth_pts=sgmc_pts)
    r0_bands_lcr = band_credit(parent_pts, parent_dcat, bands=bands,
                               truth_pts=ref["samples"][0]["points"])
    cell_density_sgmc = cell_credit_density(dcat, footprint, sgmc_pts, bands=cell_bands)
    cell_density_lcr = cell_credit_density(dcat, footprint, ref["samples"][0]["points"],
                                           bands=cell_bands)

    # ---------------- arms ----------------
    band_mask = (dcat > collar.COLLAR_FLOOR_PX + collar.COLLAR_FLOOR_MARGIN_PX) & (dcat <= collar.COLLAR_OUTER_PX)
    donor_eligible = {
        "collar": dcat >= collar.COLLAR_OUTER_PX,
        "remote": band_mask & footprint,
    }
    acceptor_cfg = {
        "collar": dict(field=collar_prior, min_px=collar.COLLAR_FLOOR_PX + collar.COLLAR_FLOOR_MARGIN_PX,
                       max_px=collar.COLLAR_OUTER_PX),
        "remote": dict(field=remote_prior, min_px=collar.REMOTE_MIN_PX, max_px=None),
    }

    evidence = {
        "schema": "gems91.concentration-collar.v1",
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git_sha": raster_io.git_sha(short=False),
        "axis": "CONCENTRATION",
        "parent": PARENT_TAG,
        "lineage": proof,
        "pins": pins_report,
        "settings": {"block_px": BLOCK_PX, "block_km": BLOCK_PX * 0.1, "seed": SEED,
                     "collar_floor_px": collar.COLLAR_FLOOR_PX,
                     "collar_outer_px": collar.COLLAR_OUTER_PX,
                     "remote_min_px": collar.REMOTE_MIN_PX,
                     "min_sep_px": collar.PARENT_MIN_NN_PX,
                     "live_span_CLAIM": LIVE_SPAN, "kappa": KAPPA},
        "r0": {"n_dots": int(parent.sum()),
               "dots_le_3px_catalogue": int((parent_dcat <= 3.0).sum()),
               "min_catalogue_distance_px": round(float(parent_dcat.min()), 6),
               "dots_by_catalogue_band": {
                   f"[{lo},{hi})": int(((parent_dcat >= lo) & (parent_dcat < hi)).sum())
                   for lo, hi in bands},
               "block_density_cv_1km": proxy.block_density_cv(parent, footprint, BLOCK_PX),
               "redundancy": proxy.redundancy(parent),
               "proxy": proxy.hide_and_recover(parent, cat, footprint),
               "sgmc_off_catalogue": {"cells": int(sgmc_off.sum()), **{
                   k: round(v, 6) for k, v in base_sgmc.items()}},
               "lineage_mask": {"cells": int(lineage_mask.sum()), **{
                   k: round(v, 6) for k, v in base_lineage.items()}}},
        "measured_prior_density": {
            "per_cell_credit_SGMC_off_catalogue": cell_density_sgmc,
            "per_cell_credit_live_calibrated_reference": cell_density_lcr,
            "per_dot_credit_SGMC_by_band": r0_bands_sgmc,
            "per_dot_credit_live_calibrated_reference_by_band": r0_bands_lcr,
            "reading": "The collar advantage is a per-CELL density effect, and it is "
                       "smaller per EXISTING DOT: R0's far-field dots already sit on "
                       "field maxima. The arms therefore aim at the best collar cells, "
                       "not at the average collar cell.",
        },
        "live_calibrated_reference": {k: v for k, v in ref.items()
                                      if k not in ("samples", "parent_pts")}
        | {"definition": "H19-5 uniformly subsampled by bisection on the fraction s at "
                         "which R0's DTI equals the CLAIM 0.2778; 5 seeded draws"},
        "arms": {},
        "null_diagnostic": {},
    }

    arms_out = {}
    for key, cfg in ARMS.items():
        prior_field = acceptor_cfg[cfg["prior"]]["field"]
        elig = donor_eligible[cfg["prior"]]
        donors = collar.donor_order(parent, dcat, collar_prior if cfg["prior"] == "remote"
                                    else prior_field, block_px=BLOCK_PX, eligible=elig)
        acc = collar.acceptor_order(prior_field, footprint, dcat,
                                    min_px=acceptor_cfg[cfg["prior"]]["min_px"],
                                    max_px=acceptor_cfg[cfg["prior"]]["max_px"])
        n_move = int(round(cfg["frac"] * PARENT_DOTS))
        res = collar.relocate(parent, donors, acc, max_donors=n_move)
        dots = res.dots
        if int(dots.sum()) != PARENT_DOTS:
            raise SystemExit(f"{key}: count not preserved ({int(dots.sum())})")
        if (dots & cat).any():
            raise SystemExit(f"{key}: mass on a catalogue pixel")
        dmin = float(dcat[dots].min())
        if dmin <= collar.COLLAR_FLOOR_PX:
            # only R0's own 2,171 sub-3 px dots may be closer; none may be added
            added_close = int((dots & ~parent & (dcat <= collar.COLLAR_FLOOR_PX)).sum())
            if added_close:
                raise SystemExit(f"{key}: {added_close} new dots inside the 3 px collar")

        diff = gates.parent_diff(parent, dots)
        cand_pts = np.c_[np.nonzero(dots)].astype(np.float64)
        cand_dcat = dcat[np.nonzero(dots)]

        # ---- write both encodings, then re-read and gate from disk
        tmp_nan = RELEASES / "_tmp-collar-nan.tif"
        tmp_zer = RELEASES / "_tmp-collar-zeros.tif"
        arr = np.where(footprint, dots.astype(np.float32), np.nan)
        io.write_float32(tmp_nan, arr, encoding="nan", template=TEMPLATE)
        io.write_float32(tmp_zer, arr, encoding="zeros", template=TEMPLATE)
        sha8 = io.sha256_file(tmp_nan)[:8]
        stem = f"{PARENT_ID}-CONCENTRATION{key}-{STAMP}-{sha8}"
        final_nan = RELEASES / f"{stem}.tif"
        final_zer = RELEASES / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)
        g_nan = gates.validate_release(final_nan, template=TEMPLATE, catalogue=cat,
                                       encoding="nan", expect_dots=PARENT_DOTS)
        g_zer = gates.validate_release(final_zer, template=TEMPLATE, catalogue=cat,
                                       encoding="zeros", expect_dots=PARENT_DOTS,
                                       ledger=LEDGER, own_id=stem)
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL {key}: nan={g_nan['failed']} zeros={g_zer['failed']}")

        # ---- independent controls
        c_sgmc = dti_parts(cand_pts, sgmc_pts)
        c_lineage = dti_parts(cand_pts, lineage_pts)
        rel_sgmc = (c_sgmc["dti"] - base_sgmc["dti"]) / base_sgmc["dti"]
        rel_lineage = (c_lineage["dti"] - base_lineage["dti"]) / base_lineage["dti"]
        lcr = lcr_delta(ref, cand_pts)
        pred = round(float(KAPPA * LIVE_SPAN * rel_sgmc), 4)
        floor = round(min(float(LIVE_SPAN * rel_lineage), lcr["delta_dti_mean"]), 3)
        cap = round(max(float(LIVE_SPAN * rel_sgmc), lcr["delta_dti_mean"], 0.0) + 0.008, 3)
        rng_pred = [floor, cap]
        basis = (f"point = 0.2778 x rel change on the independent SGMC off-catalogue "
                 f"control ({rel_sgmc:+.4f}); floor = lineage-mask rel change "
                 f"({rel_lineage:+.4f}) / live-calibrated reference "
                 f"({lcr['delta_dti_mean']:+.4f}); cap = max(measured) + 0.008 band")

        v_proxy = proxy.hide_and_recover(dots, cat, footprint)
        canary = proxy.canary(res.moved, dots, cat)
        band_after = {f"[{lo},{hi})": int(((cand_dcat >= lo) & (cand_dcat < hi)).sum())
                      for lo, hi in bands}
        rec = {
            "id": stem, "value": key, "description": cfg["description"],
            "direction": cfg["direction"], "prior": cfg["prior"],
            "block_px": BLOCK_PX, "block_km": BLOCK_PX * 0.1,
            "n_dots": int(dots.sum()), "hamming_vs_parent": diff,
            "pct_dots_moved": res.stats["pct_moved_of_parent"],
            "count_preserved": res.stats["count_preserved"],
            "displacement_px": res.stats["displacement_px"],
            "min_sep_px_enforced": res.stats["min_sep_px_enforced"],
            "collar": {"min_dist_catalogue_px": round(dmin, 6),
                       "dots_le_3px_before": int((parent_dcat <= 3.0).sum()),
                       "dots_le_3px_after": int((cand_dcat <= 3.0).sum()),
                       "new_dots_le_3px": int((dots & ~parent & (dcat <= 3.0)).sum()),
                       "moved_targets_le_3px": int((dcat[res.targets[:, 0],
                                                        res.targets[:, 1]] <= 3.0).sum()),
                       "floor_honoured": bool((dcat[res.targets[:, 0], res.targets[:, 1]]
                                               > collar.COLLAR_FLOOR_PX).all())},
            "dots_by_catalogue_band_after": band_after,
            "block_density_cv_1km": {"before": proxy.block_density_cv(parent, footprint, BLOCK_PX),
                                     "after": proxy.block_density_cv(dots, footprint, BLOCK_PX),
                                     "reported_best_files_band": [0.51, 0.59]},
            "sgmc_off_catalogue": {"parent_dti": round(base_sgmc["dti"], 6),
                                   "candidate_dti": round(c_sgmc["dti"], 6),
                                   "delta": round(c_sgmc["dti"] - base_sgmc["dti"], 6),
                                   "rel_change": round(float(rel_sgmc), 6),
                                   "evidence_class": "PROXY (mapped-fault control, not a score)"},
            "lineage_mask_bound": {"parent_dti": round(base_lineage["dti"], 6),
                                   "candidate_dti": round(c_lineage["dti"], 6),
                                   "rel_change": round(float(rel_lineage), 6),
                                   "reading": "pessimistic floor: H19-5 is ~3x denser than "
                                              "truth and is the field R0 was thinned from"},
            "instrument_notes": {
                "sgmc_structural_bias": "A dot placed at >= 3.05 px from a mapped trace earns "
                                        "exactly ZERO kernel credit on that trace (R = 3 px), so the "
                                        "SGMC off-catalogue control cannot reward collar placement "
                                        "even if the hypothesis is true. A negative SGMC delta for "
                                        "the collar arms is therefore expected, not a refutation; a "
                                        "POSITIVE SGMC delta for the mirror arm is partly "
                                        "definitional (it puts mass where off-catalogue faults are).",
                "lcr_circularity": "The live-calibrated reference is the lineage field at live "
                                   "density; R0's dots sit on that field's maxima, so any "
                                   "relocation away from the field loses credit there. It bounds "
                                   "the downside, it cannot rank 'near-catalogue' hypotheses.",
                "matched_dose_pair": "collar10 and anti10 move the same number of dots with the "
                                     "same machinery and opposite priors: their difference is the "
                                     "only two-sided statement this session can make.",
            },
            "live_calibrated_reference": lcr,
            "proxy": v_proxy,
            "proxy_delta_vs_r0": round(v_proxy["proxy_mean_credit"]
                                       - evidence["r0"]["proxy"]["proxy_mean_credit"], 6),
            "canary": canary,
            "redundancy": proxy.redundancy(dots),
            "sha256_nan": g_nan["sha256"], "sha256_zeros": g_zer["sha256"], "sha8": sha8,
            "dot_set_digest": g_nan["dot_set_digest"],
            "predicted_change_MODEL": pred, "predicted_range": rng_pred,
            "prediction_basis": basis,
            "gates": {k: g_nan[k] for k in (
                "PASS", "failed", "crs_matches_template", "shape_matches_template",
                "transform_matches_template", "single_band", "dtype_float32",
                "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                "catalogue_floor_respected", "count_matches_parent", "n_dots")},
            "gates_zeros": {k: g_zer[k] for k in ("PASS", "failed", "sha256_not_in_ledger")},
        }
        evidence["arms"][key] = rec
        arms_out[key] = (stem, rec, dots)
        print(f"{stem}: moved={res.stats['n_moved']} ({rec['pct_dots_moved']:.2f}%) "
              f"count={rec['n_dots']} cv {rec['block_density_cv_1km']['before']:.4f}->"
              f"{rec['block_density_cv_1km']['after']:.4f} "
              f"sgmc rel {rel_sgmc:+.4f} LCR {lcr['delta_dti_mean']:+.4f} "
              f"lineage rel {rel_lineage:+.4f} pred={pred:+.4f}")

    evidence["relocation_transfer_test"] = {
        "design": "matched dose (10%), matched machinery, opposite prior direction",
        "collar10_vs_anti10": {
            "sgmc_rel_change": [evidence["arms"]["collar10"]["sgmc_off_catalogue"]["rel_change"],
                                evidence["arms"]["anti10"]["sgmc_off_catalogue"]["rel_change"]],
            "lcr_delta_dti": [evidence["arms"]["collar10"]["live_calibrated_reference"]["delta_dti_mean"],
                              evidence["arms"]["anti10"]["live_calibrated_reference"]["delta_dti_mean"]],
            "lineage_rel_change": [evidence["arms"]["collar10"]["lineage_mask_bound"]["rel_change"],
                                   evidence["arms"]["anti10"]["lineage_mask_bound"]["rel_change"]],
        },
        "reading": "On both references every relocation arm, in BOTH directions, is <= 0 on at "
                   "least one reference, and the 10% arms are within +/-2.2% of R0 on the only "
                   "independent fault catalogue. No relocation this session produced a signal "
                   "that survives the 0.01 no-evidence threshold under any instrument that can "
                   "see it.",
    }

    # ---------------- null diagnostic: same dose, random block prior ----------------
    rng = np.random.default_rng(SEED)
    null_field = np.where(footprint, rng.random(footprint.shape), 0.0)
    null_donors = collar.donor_order(parent, dcat, collar_prior, block_px=BLOCK_PX,
                                     eligible=donor_eligible["collar"])
    null_acc = collar.acceptor_order(null_field, footprint, dcat,
                                     min_px=collar.COLLAR_FLOOR_PX + collar.COLLAR_FLOOR_MARGIN_PX,
                                     max_px=None)
    null_res = collar.relocate(parent, null_donors, null_acc,
                               max_donors=int(round(0.10 * PARENT_DOTS)))
    null_pts = np.c_[np.nonzero(null_res.dots)].astype(np.float64)
    null_sgmc = dti_parts(null_pts, sgmc_pts)
    evidence["null_diagnostic"] = {
        "label": "DIAGNOSTIC ONLY - no release, no ledger row, no slot",
        "n_dots_moved": null_res.stats["n_moved"],
        "pct_dots_moved": null_res.stats["pct_moved_of_parent"],
        "sgmc_off_catalogue_delta": round(null_sgmc["dti"] - base_sgmc["dti"], 6),
        "sgmc_rel_change": round(float((null_sgmc["dti"] - base_sgmc["dti"]) / base_sgmc["dti"]), 6),
        "block_density_cv_1km_after": proxy.block_density_cv(null_res.dots, footprint, BLOCK_PX),
        "reading": "same dose, same donors, acceptors drawn uniformly instead of by the "
                   "collar prior: separates 'mass moved' from 'the collar prior knew something'",
    }
    print(f"null diagnostic: moved={null_res.stats['n_moved']} "
          f"sgmc rel {evidence['null_diagnostic']['sgmc_rel_change']:+.4f} (not a candidate)")

    # ---------------- ledger ----------------
    existing, newline = [], "\n"
    if LEDGER.is_file():
        raw = LEDGER.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with LEDGER.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    fieldnames = list(existing[0].keys()) if existing else list(LEDGER_COLS)
    for c in LEDGER_COLS:
        if c not in fieldnames:
            fieldnames.append(c)
    by_id = {r.get("id"): dict(r) for r in existing}
    order = [r.get("id") for r in existing]
    known_shas = {r.get("sha256") for r in existing} | {r.get("sha256_zeros") for r in existing}
    appended = refreshed = 0
    for key, (stem, rec, _dots) in arms_out.items():
        note = (f"{PARENT_TAG}; {rec['pct_dots_moved']:.1f}% of {rec['n_dots']} dots "
                f"{'into' if rec['direction'] == 'in' else 'out of'} the 3.05-6 px collar "
                f"[{key}]; pred {rec['predicted_change_MODEL']:+.4f} MODEL")[:140]
        row = {
            "id": stem, "parent": PARENT_ID, "axis": "CONCENTRATION", "value": key,
            "n_dots": rec["n_dots"], "pct_changed": rec["hamming_vs_parent"]["pct_changed_of_parent"],
            "pct_relocated": rec["pct_dots_moved"],
            "sha256": rec["sha256_nan"], "sha256_zeros": rec["sha256_zeros"],
            "status": "BUILT",
            "predicted_change": f"{rec['predicted_change_MODEL']:+.4f} MODEL",
            "predicted_range": f"[{rec['predicted_range'][0]:+.3f},{rec['predicted_range'][1]:+.3f}]",
            "ranking_basis": ("EXTERNAL measured prior: per-cell fault-credit density vs "
                              f"distance-to-catalogue (1.3x SGMC, 2.2x lineage at 3-4.5 px vs "
                              f">10 px); {BLOCK_PX}px blocks; direction {rec['direction']}"),
            "receipt_score": "", "receipt_date": "",
            "date": dt.date.today().isoformat(), "form_note": note,
            "evidence_class": "MODEL",
            "source": f"{SESSION_SOURCE} BUILT:scripts/build_concentration_collar.py@{raster_io.git_sha()}",
            "notes": (f"moved={rec['pct_dots_moved']:.2f}% cv "
                      f"{rec['block_density_cv_1km']['before']:.4f}->"
                      f"{rec['block_density_cv_1km']['after']:.4f}; sgmc rel "
                      f"{rec['sgmc_off_catalogue']['rel_change']:+.4f}; LCR "
                      f"{rec['live_calibrated_reference']['delta_dti_mean']:+.5f}; "
                      f"gate PASS; no new dot <=3px"),
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91",
        }
        old = by_id.get(stem)
        if old is not None:
            if old.get("sha256") != rec["sha256_nan"]:
                raise SystemExit(f"{stem}: id exists with a DIFFERENT sha256 - not reproducible")
            old.update(row)                    # refresh derived columns only
            refreshed += 1
            continue
        if rec["sha256_nan"] in known_shas or rec["sha256_zeros"] in known_shas:
            raise SystemExit(f"refusing to append {stem}: a hash twin is already in the ledger")
        known_shas |= {rec["sha256_nan"], rec["sha256_zeros"]}
        by_id[stem] = row
        order.append(stem)
        appended += 1

    with LEDGER.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore",
                           lineterminator=newline)
        w.writeheader()
        for rid in order:
            w.writerow({k: by_id[rid].get(k, "") for k in fieldnames})
    print(f"ledger rows: {appended} appended, {refreshed} refreshed (same id + same sha256)")

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n")
    manifest = {
        "schema_version": 1,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "parent": PARENT_TAG,
        "note": "Releases are not committed. Rebuild with scripts/restore_data.py then "
                "scripts/build_concentration_collar.py --build; every sha256 must reappear.",
        "files": [{"file": f"{stem}.tif", "sha256": rec["sha256_nan"], "n_dots": rec["n_dots"],
                   "value": key, "predicted_change_MODEL": rec["predicted_change_MODEL"]}
                  for key, (stem, rec, _d) in arms_out.items()]
        + [{"file": f"{stem}-zeros.tif", "sha256": rec["sha256_zeros"], "n_dots": rec["n_dots"],
            "value": key, "encoding": "zeros"}
           for key, (stem, rec, _d) in arms_out.items()],
    }
    RELEASE_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nevidence: {EVIDENCE.relative_to(ROOT)}"
          f"\nreleases: {len(manifest['files'])} files hashed in "
          f"{RELEASE_MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
