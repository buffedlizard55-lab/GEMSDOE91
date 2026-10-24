#!/usr/bin/env python3
"""MASS axis (expansion) on R0: add dots the parent's own field chose and its thinning dropped.

Parent R0 = ``h33-h33-2-b2`` (GEMSDOE32): 37,654 unit-mass dots, sha256
``baeae321...c77dd`` (NaN encoding) / ``c55bafc4...6fa9`` (zeros encoding), 0 dots on the
catalogue, min catalogue distance 2.236 px, CLAIM 0.2778.

Why MASS, and why now
---------------------
Every axis in the fleet ledger (47 BUILT rows, 0 receipts) has been a *relocation* or a
*deletion* at a 10-20 % dose.  Count has been raised exactly once, by 10 %
(``MASScons3add``, +0.0086 MODEL), and the upstream import ``MASSm10plus`` predicted the
opposite sign (-0.010).  The metric algebra says why that dose is too small to settle it:

    DTI = T / (0.2T + 0.2(S - M) + 0.8|G|)

A dot contributes credit ``c`` to T and costs ``0.2*(1 - m)`` in the denominator, where
``m`` is its own best kernel value against truth.  For a dot inside the 3-px kernel
``m -> 1``, so matched mass is almost free while every unit of credit is added.  Addition
is therefore worth ~10x more per dot than deletion at equal precision, and the break-even
precision for *adding* is ``p* = 0.2*DTI/(c + 0.2*DTI)`` ~ 0.07 (MODEL).  Nothing in the
ledger tests that claim at a dose where it could show up above the 0.01 evidence bar.

The ranking is the parent's own, not a cross-session compromise
---------------------------------------------------------------
The lineage field ``anc_h19_5`` (121,131 px) contains all 37,654 R0 dots.  83,477 of its
cells are *not* in R0: they were dropped by a 2-px spacing thinning and by the
"delete <= 2 px of the catalogue" prune, i.e. by geometry, not by score.  Those cells are
"the next cells the parent's own model selected".  Within the field the lineage's only
recorded ordering is cross-field support (vote 0-3 over anc_h19_5/h19_4/h16_1), so the
arms take vote-3 cells only.

Arms (three, all addition-only, count +12.5 % / +25 %, never a delete)
---------------------------------------------------------------------
``a12adj``  +4,707 dots (12.5 %) at cells 8-adjacent to an R0 dot  -> STACKING.
            Nearest parent dot is 1.0-1.41 px away: mass on cells the lineage already
            accepted, which is where the kernel makes mass nearly free.
``a25adj``  +9,414 dots (25.0 %), same rule                          -> DOSE.
            Linear-in-dose reading of ``a12adj``; the first count test at a dose that can
            clear the 0.01 bar if the mechanism is real.
``a12spc``  +4,707 dots (12.5 %) at cells NOT 8-adjacent to any dot, selected mutually
            non-adjacent                                          -> SPACING CONTROL.
            Same count, same field, same vote stratum as ``a12adj``; the parent's
            no-8-adjacency texture is preserved.  ``a12adj - a12spc`` isolates
            "more mass" from "more clustering".

Every arm: inside the scored footprint, vote == 3, > 3.0 px from the catalogue (brief 4.4),
no parent dot moved or deleted, unit mass, fixed seed 91024.

Usage
-----
    python3 scripts/build_mass_expand.py --check     # verify pins + parent hash, build nothing
    python3 scripts/build_mass_expand.py --build     # write both encodings, gates, evidence
    python3 scripts/build_mass_expand.py --build --register   # also append ledger rows
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from gems91 import gates as strict_gates, io, massexpand, release_gates as gates  # noqa: E402
from tools import raster_io, stor  # noqa: E402

DATA = ROOT / "data"
MANIFEST = ROOT / "registry" / "data_manifest.json"
LEDGER = ROOT / "ledger" / "submissions.csv"
RELEASES = ROOT / "releases"
EVIDENCE = ROOT / "evidence" / "mass_expand_20261024.json"

PARENT_TAG = "h33-h33-2-b2"
PARENT_DOTS = 37654
PARENT_SHA_NAN = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
PARENT_SHA_ZEROS = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
BUILD_DATE = dt.date(2026, 10, 24)
SEED = 91024

SAMPLE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
F_H195 = DATA / "registry" / "calib_h195_01922.tif"
F_H194 = DATA / "registry" / "calib_h194_01894.tif"
F_H161 = DATA / "registry" / "calib_h161_01855.tif"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"

REQUIRED_PINS = ("sample_submission", "existing_faults", "parent_r0_nan", "parent_r0_zeros",
                 "anc_h19_5", "anc_h19_4", "anc_h16_1", "sgmc_faults_control")

#: value -> (pool, fraction of the parent count added)
ARMS = {
    "a12adj": ("adj", 0.125),
    "a25adj": ("adj", 0.250),
    "a12spc": ("spaced", 0.125),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_pins() -> dict[str, Path]:
    manifest = json.loads(MANIFEST.read_text())
    by_id = {f["id"]: f for f in manifest["files"]}
    paths: dict[str, Path] = {}
    problems: list[str] = []
    for pid in REQUIRED_PINS:
        entry = by_id.get(pid)
        if entry is None:
            problems.append(f"{pid}: not in registry/data_manifest.json")
            continue
        path = DATA / entry.get("local_subpath", pid)
        if not path.is_file():
            problems.append(f"{pid}: missing at {path} (run scripts/restore_data.py)")
            continue
        got = sha256_file(path)
        if got != entry["sha256"]:
            problems.append(f"{pid}: sha256 {got[:16]} != pinned {entry['sha256'][:16]}")
        paths[pid] = path
    if problems:
        raise SystemExit("REFUSING TO BUILD - pinned inputs not verified:\n  " + "\n  ".join(problems))
    return paths


def verify_parent() -> np.ndarray:
    got_nan = sha256_file(PARENT_NAN)
    got_zeros = sha256_file(PARENT_ZEROS)
    if got_nan != PARENT_SHA_NAN or got_zeros != PARENT_SHA_ZEROS:
        raise SystemExit(
            "STOP: the parent does not match its pinned sha256 "
            f"({got_nan[:16]} / {got_zeros[:16]}). Never approximate the parent - report instead.")
    parent = raster_io.read_band(PARENT_NAN)
    dots = np.nan_to_num(parent, nan=0.0) > 0
    if int(dots.sum()) != PARENT_DOTS:
        raise SystemExit(f"STOP: parent has {int(dots.sum())} dots, expected {PARENT_DOTS}")
    if not np.allclose(np.nan_to_num(parent, nan=0.0)[dots], 1.0):
        raise SystemExit("STOP: parent is not unit mass")
    return parent


#: fleet calibration: MASScons3add added 4,643 dots (+10 %) and was projected at +0.0086
#: MODEL by session 4; expressed per added dot so the new doses are on the same scale.
FLEET_MASS_PER_DOT = 0.0086 / 4643.0


def model_prediction(n_added: int, pool: str, *, dti: float = 0.2778,
                     d_bracket=(45_000.0, 75_000.0), credit_bracket=(1.5, 3.0),
                     precision_bracket=(0.01, 0.03, 0.06, 0.10, 0.16), m: float = 0.8) -> dict:
    """MODEL projection for an addition-only arm.  Never a score.

    First-order change from one added dot (gems91.metric algebra, T = dti*D):

        d(DTI)/dot = [ p*c*(1 - 0.2*dti) - 0.2*dti*(1 - p*m) ] / D

    p = probability the cell has truth within 3 px, c = the credit it then earns (the kernel
    sum over the truth pixels it reaches; ~1.5 at 2 px off a trace, ~3 on one), m = its own
    best kernel value.  D and p are unobservable, so the sweep is the range; the point
    estimate is the fleet's own per-dot calibration, which is independent of this script.
    """
    scale = {"adj": 1.0, "spaced": 0.6}[pool]   # spaced cells sit further from accepted mass
    lo, hi = float("inf"), float("-inf")
    for d in d_bracket:
        for c in credit_bracket:
            for p in precision_bracket:
                per_dot = (p * c * (1 - 0.2 * dti) - 0.2 * dti * (1 - p * m)) / d
                lo, hi = min(lo, n_added * per_dot), max(hi, n_added * per_dot)
    point = n_added * FLEET_MASS_PER_DOT * scale
    return {
        "n_added": int(n_added),
        "pool": pool,
        "point": round(point, 4),
        "delta_dti_range": [round(lo * scale, 4), round(hi * scale, 4)],
        "breakeven_precision": round(0.2 * dti / (credit_bracket[1] + 0.2 * dti * m), 4),
        "fleet_per_dot": round(FLEET_MASS_PER_DOT, 8),
        "note": "MODEL, never a score; the point is the fleet calibration, the range is the algebra sweep",
    }


def sgmc_check(added: np.ndarray, parent: np.ndarray) -> dict:
    """REPORT ONLY: independent off-catalogue USGS SGMC map (never a gate).

    If the added cells were far worse than the parent's own dots on the one independent
    fault map available, the precision assumption behind MASS expansion would be wrong.
    """
    with rasterio.open(SGMC) as ds:
        sg = ds.read(1) > 0
    cat = raster_io.read_band(CATALOGUE) > 0
    dcat = ndi.distance_transform_edt(~cat)
    sg_only = sg & (dcat > 3)
    d_so = ndi.distance_transform_edt(~sg_only) if sg_only.any() else np.full(sg.shape, np.inf)
    pd = np.argwhere(np.nan_to_num(parent, nan=0.0) > 0)
    out = {"sgmc_only_px": int(sg_only.sum())}
    for r in (1, 2, 3):
        out[f"parent_frac_within_{r}px"] = round(float((d_so[pd[:, 0], pd[:, 1]] <= r).mean()), 4)
        out[f"added_frac_within_{r}px"] = (
            round(float((d_so[added[:, 0], added[:, 1]] <= r).mean()), 4) if len(added) else None)
    return out


def leakage_canary(votes: np.ndarray, catalogue: np.ndarray) -> dict:
    """REPORT ONLY: a feature that predicts the catalogue ring too well is a leakage alarm.

    Rank-based (Mann-Whitney) AUC with ties counted as 1/2, so this stays O(n log n) on a
    12.3 M-pixel grid instead of building a cross tabulation.
    """
    cat = np.nan_to_num(catalogue, nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat)
    feat = votes.astype(np.float64)
    pos = feat[dcat <= 3].ravel()
    neg = feat[dcat >= 7].ravel()
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    ranks = np.empty(allv.size, dtype=np.float64)
    ranks[order] = np.arange(1, allv.size + 1, dtype=np.float64)
    # average ranks over ties
    sv = allv[order]
    uniq, inv, counts = np.unique(sv, return_inverse=True, return_counts=True)
    sums = np.zeros(uniq.size)
    np.add.at(sums, inv, ranks[order])
    ranks[order] = (sums / counts)[inv]
    r_pos = ranks[: pos.size].sum()
    auc = (r_pos - pos.size * (pos.size + 1) / 2.0) / (pos.size * neg.size)
    return {"feature": "cross-field support vote (0-3)",
            "auc_vs_catalogue_ring": round(float(auc), 4),
            "n_ring_px": int(pos.size), "n_background_px": int(neg.size),
            "threshold": 0.9,
            "verdict": "below threshold" if auc < 0.9 else "STOP AND INVESTIGATE"}


def append_rows(rows: list[dict]) -> int:
    """Append to ledger/submissions.csv using the file's OWN 21-column schema."""
    header = [
        "id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated", "sha256",
        "sha256_zeros", "status", "predicted_change", "predicted_range", "ranking_basis",
        "receipt_score", "receipt_date", "date", "form_note", "evidence_class", "source",
        "notes", "source_url",
    ]
    existing = list(csv.DictReader(LEDGER.open(newline="", encoding="utf-8-sig")))
    seen_sha = {r.get("sha256") for r in existing} | {r.get("sha256_zeros") for r in existing}
    seen_triple = {(r.get("parent"), r.get("axis"), r.get("value")) for r in existing}
    for row in rows:
        if row["sha256"] in seen_sha or row["sha256_zeros"] in seen_sha:
            raise SystemExit(f"refusing: {row['id']} reuses an sha256 already in the ledger")
        if (row["parent"], row["axis"], row["value"]) in seen_triple:
            raise SystemExit(f"refusing: ({row['parent']}, MASS, {row['value']}) already built")
    with LEDGER.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        for row in rows:
            w.writerow({c: row.get(c, "") for c in header})
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify pins and parent only")
    ap.add_argument("--build", action="store_true", help="build, gate, write evidence")
    ap.add_argument("--register", action="store_true", help="append ledger rows after gating")
    args = ap.parse_args(argv)
    if not (args.check or args.build):
        ap.print_help()
        return 0

    verify_pins()
    print(f"[ok] {len(REQUIRED_PINS)} pinned inputs hash-verified")
    parent = verify_parent()
    print(f"[ok] parent R0 sha256 matches both pinned encodings ({PARENT_DOTS:,} dots)")
    footprint, meta = raster_io.footprint_from_sample(SAMPLE)
    catalogue = raster_io.read_band(CATALOGUE)
    field = raster_io.read_band(F_H195)
    votes = massexpand.vote_map(field, raster_io.read_band(F_H194), raster_io.read_band(F_H161))
    if args.check:
        pools = massexpand.candidate_pools(field, votes, parent, catalogue, footprint,
                                           vote_threshold=3)
        print(json.dumps({k: int(pools[k].sum()) for k in ("eligible", "adj", "spaced")}, indent=2))
        for value, (pool, frac) in ARMS.items():
            print(f"  {value}: pool={pool} n_add={int(round(frac * PARENT_DOTS))}")
        return 0

    tpl = SAMPLE
    results, evidence = [], {"schema": "gems91.mass-expand.v1", "generated_utc":
                             dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                             "git_sha": raster_io.git_sha(), "axis": "MASS",
                             "parent": PARENT_TAG, "parent_dots": PARENT_DOTS,
                             "parent_sha256_nan": PARENT_SHA_NAN,
                             "parent_sha256_zeros": PARENT_SHA_ZEROS,
                             "ranking_basis": ("lineage field anc_h19_5 (121,131 px) restricted to "
                                               "cells R0 does not use, vote==3 over "
                                               "anc_h19_5/h19_4/h16_1, seeded tie-break"),
                             "seed": SEED, "arms": {}}
    for value, (pool, frac) in ARMS.items():
        n_add = int(round(frac * PARENT_DOTS))
        band, stats = massexpand.build_arm(parent, field, votes, catalogue, footprint,
                                           n_add=n_add, pool=pool, seed=SEED)
        written = raster_io.write_named_release(RELEASES, PARENT_TAG, "MASS", value, band,
                                                meta["profile"], footprint, date=BUILD_DATE,
                                                compress="lzw")
        added = np.argwhere((np.nan_to_num(band, nan=0.0) > 0) & (np.nan_to_num(parent, nan=0.0) <= 0))
        report_nan = gates.validate_release(written["primary"], template=tpl, catalogue=catalogue,
                                            ledger=LEDGER, encoding="nan", floor_px=2.0,
                                            own_id=written["stem"])
        report_zeros = gates.validate_release(written["zeros"], template=tpl, catalogue=catalogue,
                                              ledger=LEDGER, encoding="zeros", floor_px=2.0,
                                              own_id=written["stem"])
        diff = gates.parent_diff(np.nan_to_num(parent, nan=0.0) > 0,
                                 io.dot_mask(io.read_grid(written["primary"])))
        pred = model_prediction(n_add, pool)
        # second, independent gate implementation (gems91.gates).  It reports the inherited
        # catalogue collar as a failure for every non-PRUNE axis; IR-91-03 is the human's call.
        strict = strict_gates.validate(written["primary"], sample_submission=str(SAMPLE),
                                       catalogue=str(CATALOGUE), ledger_csv=str(LEDGER),
                                       axis="MASS").to_dict()
        arm = {"value": value, "id": written["stem"], "sha256": written["sha256"],
               "sha256_zeros": written["sha256_zeros"], "n_dots": diff["n_dots_child"],
               "pool": pool, "n_add": n_add, "stats": stats, "parent_diff": diff,
               "gates_nan": {k: v for k, v in report_nan.items() if k != "text"},
               "gates_zeros": {k: v for k, v in report_zeros.items() if k != "text"},
               "both_gates_pass": bool(report_nan["PASS"] and report_zeros["PASS"]),
               "model_prediction": pred,
               "gems91_gates_report_only": {
                   "verdict": strict["verdict"],
                   "gates": strict["gates"],
                   "inherited_collar_note": (
                       "collar_ge_3px fails on the 2,171 R0 dots inherited at 2<d<=3 px "
                       "(IR-91-03). The edit itself adds 0 dots within 3 px "
                       f"(min added->catalogue {stats['added_distance_to_catalogue_px']['min']:.3f} px)."),
               },
               "sgmc_report_only": sgmc_check(added, parent)}
        evidence["arms"][value] = arm
        results.append(arm)
        status = "PASS" if arm["both_gates_pass"] else "FAIL: " + ",".join(
            report_nan.get("failed", []) + report_zeros.get("failed", []))
        print(f"[{status}] {written['stem']}  dots={diff['n_dots_child']} "
              f"added={diff['added']} pct={diff['pct_changed_of_parent']:.2f}% "
              f"min_cat={report_nan['min_catalogue_distance_px']:.3f}px")

    evidence["leakage_canary"] = leakage_canary(votes, catalogue)
    evidence["report_only_note"] = ("SGMC and the canary are instruments, never gates. "
                                    "The catalogue hide-and-recover proxy is invariant by "
                                    "construction here: every added cell is >3 px from the "
                                    "catalogue and no parent dot moves.")
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"[ok] evidence -> {EVIDENCE.relative_to(ROOT)}")

    if not all(a["both_gates_pass"] for a in results):
        print("REFUSING TO REGISTER: at least one arm failed a MUST gate", file=sys.stderr)
        return 1
    if not args.register:
        print("not registered (pass --register after the gates pass)")
        return 0

    rows = []
    for a in results:
        pred = a["model_prediction"]["delta_dti_range"]
        point = a["model_prediction"]["point"]
        rows.append({
            "id": a["id"], "parent": PARENT_TAG, "axis": "MASS", "value": a["value"],
            "n_dots": a["n_dots"], "pct_changed": a["parent_diff"]["pct_changed_of_parent"],
            "pct_relocated": 0.0, "sha256": a["sha256"], "sha256_zeros": a["sha256_zeros"],
            "status": "GATED",
            "predicted_change": f"MODEL:{point:+.3f} ({pred[0]:+.3f}..{pred[1]:+.3f})",
            "predicted_range": f"[{pred[0]:+.3f},{pred[1]:+.3f}]",
            "ranking_basis": ("anc_h19_5 field cells R0 does not use; vote==3 over "
                              "anc_h19_5/h19_4/h16_1; seeded tie-break"),
            "receipt_score": "", "receipt_date": "", "date": BUILD_DATE.isoformat(),
            "form_note": raster_io.form_note(
                PARENT_TAG,
                f"+{a['n_add']} dots ({100*a['n_add']/PARENT_DOTS:.1f}%) at {a['pool']} "
                f"vote-3 field cells",
                f"MODEL {point:+.3f}"),
            "evidence_class": "MODEL",
            "source": f"SESSION 8 (this branch): scripts/build_mass_expand.py@{raster_io.git_sha()}",
            "notes": (f"pool={a['pool']} added={a['n_add']} count={a['n_dots']} "
                      f"min_cat={a['gates_nan']['min_catalogue_distance_px']:.3f}px "
                      f"nearest_parent_dot_mean="
                      f"{a['stats']['added_distance_to_nearest_parent_dot_px']['mean']:.2f}px "
                      f"SGMC r<=1 added={a['sgmc_report_only']['added_frac_within_1px']} "
                      f"vs parent {a['sgmc_report_only']['parent_frac_within_1px']} PROXY"),
            "source_url": "",
        })
    n = append_rows(rows)
    print(f"[ok] appended {n} ledger rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
