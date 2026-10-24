#!/usr/bin/env python3
"""Build the three MASS variants of R0 that differ only in cross-field support.

    python scripts/build_mass_consensus.py --dry-run     # measure, write nothing
    python scripts/build_mass_consensus.py               # write + certify the pair

Arms (one axis, one parent, three new (axis, value) pairs):

    MASS/cons1drop  drop every R0 dot supported by only 1 of the 3 lineage fields
                    (4,541 dots = 12.06%), no tie-break needed
    MASS/cons2drop  drop every dot supported by <= 2 fields
                    (10,741 dots = 28.53%), the next whole stratum
    MASS/cons3add   add 3,765 dots (10.00%) from the best-supported, furthest-from-a-dot
                    eligible cells, never within 3 px of the catalogue

Order of operations is the brief's: verify every pinned byte this axis reads, apply
ONE axis, write the NaN-outside release and its zeros-outside twin, re-read from
disk, run both gate implementations, then print the ledger rows.  It never writes
to the ledger and never submits; the human fills receipt_score / receipt_date.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import validate_raster as V  # noqa: E402
from gems91 import consensus as C  # noqa: E402
from gems91 import gates as GATES  # noqa: E402
from gems91 import io as G  # noqa: E402
from gems91 import release_gates as RG  # noqa: E402
from verify_manifest import check, load_manifest  # noqa: E402

PARENT = "data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
TEMPLATE = "data/official/sample_submission.tif"
CATALOGUE = "data/official/existing_faults.tif"
FIELD_PATHS = {
    "anc_h19_5": "data/registry/calib_h195_01922.tif",
    "anc_h19_4": "data/registry/calib_h194_01894.tif",
    "anc_h16_1": "data/registry/calib_h161_01855.tif",
}
TAG = "h33-h33-2-b2"
DATE = "20261023"  # pinned fleet build date (IR-91-29): ids must reproduce, not roll daily

# --- the prediction model, stated so it can be checked ----------------------
# Per-dot expected change in DTI (first order, kernel R = 3 px, alpha = 0.2):
#     E[dDTI] = (p * cbar - gamma) / D,      gamma = alpha*dTI/(1 - alpha*dTI)
# where p is the dot's precision (chance the nearest truth pixel is within
# 2.83 px), cbar the mean credit earned when it is, D the DTI denominator and
# dTI the claimed 0.2778.  gamma = 0.0556: that is the break-even credit, which
# is why a dot pays iff it is within 2.83 px of truth (IR-91-22).
GAMMA = 0.2 * 0.2778 / (1.0 - 0.2 * 0.2778)
CBAR = 0.50          # mean triangular-kernel credit for a dot inside 2.83 px
D_BRACKET = (1.0e4, 3.5e4)   # DTI denominator, bracketed from 0.15-0.35 matched fraction

ARMS = {
    "cons1drop": dict(mode="drop", max_vote=1, p=(0.05, 0.12, 0.25),
                      why="single-field-support dots are the lowest-precision stratum"),
    "cons2drop": dict(mode="drop", max_vote=2, p=(0.08, 0.18, 0.30),
                      why="dose escalation on the same ordering; identifies its slope"),
    "cons3add": dict(mode="add", fraction=0.10, p=(0.10, 0.22, 0.35),
                     why="highest-support unspent cells; tests whether the thinning overshot"),
}


def predict(n: int, p: tuple[float, float, float], sign: int) -> dict:
    """MODEL prediction and range; ``sign`` = +1 for added dots, -1 for removed.

    The range spans the *precision* bracket at the mid denominator, because that is
    the quantity the experiment measures.  Denominator uncertainty is reported
    separately as a multiplicative ``d_scale`` rather than multiplied into the same
    interval, which would pretend the two are independent corners.
    """
    d_mid = float(np.mean(D_BRACKET))
    vals = [sign * (pi * CBAR - GAMMA) * n / d_mid for pi in p]
    mid = sign * (p[1] * CBAR - GAMMA) * n / d_mid
    return {"predicted": round(mid, 4), "range": [round(min(vals), 4), round(max(vals), 4)],
            "d_scale": [round(d_mid / D_BRACKET[1], 2), round(d_mid / D_BRACKET[0], 2)],
            "gamma_breakeven_credit": round(GAMMA, 4),
            "breakeven_precision": round(GAMMA / CBAR, 4)}


def read(path: str | Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Build the three MASS/consensus variants of R0.")
    ap.add_argument("--dry-run", action="store_true", help="measure and predict, write nothing")
    ap.add_argument("--out", default="releases")
    ap.add_argument("--report", default="reports/build-mass-consensus.json")
    ap.add_argument("--ledger", default="ledger/submissions.csv")
    args = ap.parse_args(argv)

    # STEP 1 -- every byte this axis reads must be pinned and hash-verified first
    manifest = load_manifest(ROOT / "registry" / "data_manifest.json")
    rows, _ = check(manifest, "data")
    ok_ids = {r["id"] for r in rows if r["status"] == "OK"}
    need = ["parent_r0_nan", "sample_submission", "existing_faults", *C.FIELD_IDS]
    missing = [i for i in need if i not in ok_ids]
    if missing:
        print(f"STOP: unpinned or unverified inputs: {', '.join(missing)}", file=sys.stderr)
        return 2
    print(f"[READY] {len(need)} pinned inputs hash-verified for MASS: {', '.join(need)}")

    parent_arr = read(PARENT)
    template = read(TEMPLATE)
    cat_mask = read(CATALOGUE) > 0
    dots = G.dot_mask(parent_arr)
    footprint = np.isfinite(template)
    dcat = ndi.distance_transform_edt(~cat_mask)

    fields = [read(FIELD_PATHS[i]) > 0 for i in C.FIELD_IDS]
    rank = C.build_rank(fields, dots)

    print(f"parent dots              {int(dots.sum())}")
    print(f"consensus histogram      {rank.histogram(dots)}  (vote 0..3)")
    print(f"catalogue pixels         {int(cat_mask.sum())}")
    print(f"parent min d_cat         {dcat[dots].min():.3f} px  "
          f"({int((dcat[dots] <= 3.0).sum())} dots at 2-3 px, inherited -- IR-91-03)")

    # The parent's own collar count, so an inherited violation is provable, not asserted.
    parent_collar = GATES.validate(PARENT, sample_submission=TEMPLATE, catalogue=CATALOGUE,
                                   ledger_csv=None, axis="MASS")
    parent_le3 = int(parent_collar.notes.get("dots_le_3px", -1))

    n_parent = int(dots.sum())
    built: list[dict] = []
    for value, spec in ARMS.items():
        if spec["mode"] == "drop":
            child = dots & ~C.select_drop(dots, rank, spec["max_vote"])
            n_change = int((dots & ~child).sum())
            pred = predict(n_change, spec["p"], sign=-1)
        else:
            n_want = int(round(spec["fraction"] * n_parent))
            add = C.select_add(dots, rank, footprint, dcat, n_want)
            child = dots | add
            n_change = int(add.sum())
            pred = predict(n_change, spec["p"], sign=+1)
        stats = C.diff_stats(dots, child)
        assert stats["changed"] == n_change
        if not (1.0 <= stats["pct_changed"] <= 50.0):
            print(f"STOP: {value} changes {stats['pct_changed']}% of dots (brief: 1-50%)", file=sys.stderr)
            return 2
        on_cat = int((child & cat_mask).sum())
        if on_cat:
            print(f"STOP: {value} emits mass on {on_cat} catalogue pixels", file=sys.stderr)
            return 2

        row = {"value": value, "arm": spec["mode"], "stats": stats, "prediction": pred,
               "mechanism_note": spec["why"], "min_dcat_px": float(dcat[child].min()),
               "dots_2_3px_from_catalogue": int(((dcat[child] > 2.0) & (dcat[child] <= 3.0)).sum())}
        print(f"\n[{value}] {stats}")
        print(f"         prediction MODEL {pred['predicted']:+} {pred['range']} "
              f"(x{pred['d_scale']} for denominator) breakeven precision {pred['breakeven_precision']}")
        if args.dry_run:
            built.append(row)
            continue

        # STEP 2 -- write to a temporary name, hash, then rename to the id that carries sha8
        arr = C.frame(child, footprint)
        tmp_nan = Path(args.out) / f"_tmp-{value}.tif"
        tmp_zer = Path(args.out) / f"_tmp-{value}-zeros.tif"
        G.write_float32(tmp_nan, arr, encoding="nan", template=TEMPLATE)
        G.write_float32(tmp_zer, np.where(footprint, arr, 0.0), encoding="zeros", template=TEMPLATE)
        sha = G.sha256_file(tmp_nan)
        sha_zeros = G.sha256_file(tmp_zer)
        vid = f"{TAG}-MASS{value}-{DATE}-{sha[:8]}"
        nan_path, zer_path = Path(args.out) / f"{vid}.tif", Path(args.out) / f"{vid}-zeros.tif"
        tmp_nan.replace(nan_path)
        tmp_zer.replace(zer_path)
        assert G.sha256_file(nan_path) == sha and G.sha256_file(zer_path) == sha_zeros

        # STEP 3 -- gates: both implementations, on files re-read from disk
        rep = V.validate_raster(nan_path, TEMPLATE, catalogue=CATALOGUE,
                                ledger_csv=args.ledger, parent=PARENT)
        rep_z = V.validate_raster(zer_path, TEMPLATE, catalogue=CATALOGUE, ledger_csv=args.ledger,
                                  parent=PARENT, allow_zeros_outside=True)
        # The second implementation runs the brief's MUST gates AND the section 4.4 collar.
        # The collar is reported separately: R0 itself fails it (IR-91-03), so a build that
        # inherits R0's dots cannot pass it without becoming a PRUNE arm.
        g3 = GATES.validate(nan_path, sample_submission=TEMPLATE, catalogue=CATALOGUE,
                            ledger_csv=args.ledger, axis="MASS")
        g2 = RG.validate_release(nan_path, template=TEMPLATE, catalogue=cat_mask, ledger=args.ledger,
                                 encoding="nan", floor_px=2.0, own_id=vid)
        g2z = RG.validate_release(zer_path, template=TEMPLATE, catalogue=cat_mask, ledger=args.ledger,
                                  encoding="zeros", floor_px=2.0, own_id=vid)
        print(rep.text())
        must_fail = [f for f in g3.failed if f != "collar_ge_3px"]
        collar_fail = "collar_ge_3px" in g3.failed
        le3 = int(g3.notes.get("dots_le_3px", -1))
        ok = rep.ok and rep_z.ok and g2["PASS"] and g2z["PASS"] and not must_fail
        print(f"[{'PASS' if not collar_fail else 'INHERITED-FAIL'}] collar_ge_3px: "
              f"{le3} dots <= 3 px (parent R0 has {parent_le3}; IR-91-03)")
        print(f"[{'PASS' if not must_fail else 'FAIL'}] gems91.gates: all other MUST gates "
              f"({len(g3.gates) - len(g3.failed)}/{len(g3.gates)} PASS)")
        row.update({
            "id": vid, "sha256": sha, "sha256_zeros": sha_zeros,
            "dot_set_digest": G.dot_digest(child), "n_dots": int(child.sum()),
            "gates_scripts": {"pass": rep.ok, "zeros_pass": rep_z.ok, "text": rep.text()},
            "gates_pkg": {"pass": g2["PASS"], "failed": g2["failed"],
                          "zeros_pass": g2z["PASS"], "zeros_failed": g2z["failed"],
                          "min_catalogue_distance_px": g2["min_catalogue_distance_px"]},
            "gates_must": {"pass": not must_fail, "failed": must_fail,
                           "n_gates": len(g3.gates), "verdict": g3.verdict},
            "collar": {"dots_le_3px": le3, "parent_dots_le_3px": parent_le3,
                       "inherited_not_caused_by_edit": le3 <= parent_le3},
            "all_gates_pass": bool(ok), "files": [str(nan_path), str(zer_path)],
        })
        print(f"wrote {nan_path}\nwrote {zer_path}")
        print(f"VERDICT {'PASS' if ok else 'FAIL'} (MUST gates, both implementations; "
              f"collar inherited from R0: {le3} <= {parent_le3})")
        built.append(row)
        if not ok:
            return 1

    if not args.dry_run and built:
        report = {"schema": "gems91.mass-consensus.v1", "date": DATE,
                  "parent": PARENT, "parent_dots": n_parent,
                  "field_ids": list(C.FIELD_IDS), "field_paths": FIELD_PATHS,
                  "consensus_histogram_parent": rank.histogram(dots),
                  "prediction_model": {"gamma": GAMMA, "cbar": CBAR, "D_bracket": D_BRACKET},
                  "variants": built}
        rp = Path(args.report)
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nreport {rp}")
        print("\nledger rows (receipt columns are the human's):")
        for r in built:
            note = (f"{r['value']}: {r['arm']} {r['stats']['changed']} dots "
                    f"({r['stats']['pct_changed']:.2f}%), support-ranked; MODEL {r['prediction']['predicted']:+}")
            print(f"  {r['id']}  n_dots={r['n_dots']}  pct_changed={r['stats']['pct_changed']}  "
                  f"sha256={r['sha256']}")
            print(f"    form_note ({len(note)} chars): {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
