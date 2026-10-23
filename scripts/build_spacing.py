#!/usr/bin/env python3
"""SPACING axis on R0: three matched arms that differ ONLY in re-spacing direction.

Parent R0 = `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32), 37,654 unit
dots, sha256 c55bafc4...  (zeros) / baeae321... (nan), CLAIM 0.2778.

The edit
--------
* Same 40 % of dots in all three arms: the dots sitting in the densest 1 km
  blocks (10 x 10 cells), ranked by block dot count until 40 % of all dots are
  covered. Deterministic, identical across arms.
* Same displacement budget in all three arms: every moved dot lands on one of
  the 12 integer cells at 2.0-2.236 px (the radius-2 Moore ring). Only the
  *direction* differs, so any difference in outcome is attributable to
  direction and not to how far the dots travel.
* Count fixed at 37,654, no cell reused, footprint and the parent's own
  catalogue floor (d_cat > 2.0 px) respected, nothing deleted or added.

Arms
----
div40   move away from the unit-vector mean of the dot's neighbours within 6 px
conv40  move toward that mean (the sign flip)
jit40   move in a fixed-seed pseudo-random direction (the null)

Usage
-----
    python3 scripts/build_spacing.py --build
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import geom, io, moves, proxy, release_gates as gates  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"

PARENT_ID = "h33-h33-2-b2-20261004-e5eb6e7e"
PARENT_DOTS = 37654
SELECT_FRAC = 0.40
BLOCK_PX = 10          # 1 km blocks
SEED = 91
SHRINK = 0.1           # prediction rule: a tenth of the proxy-implied relative change
LIVE_SPAN = 0.2778     # CLAIM, used only as the scale of a MODEL prediction

ARMS = {
    "spread40": dict(
        label="SPACING-spread",
        value="spread40",
        mode="spread",
        description="40% of dots moved to the emptiest legal cell on the ring-2 offsets (2.0-2.24 px)",
    ),
    "clump40": dict(
        label="SPACING-clump",
        value="clump40",
        mode="clump",
        description="40% of dots moved to the densest legal cell on the ring-2 offsets (sign flip)",
    ),
    "jitter40": dict(
        label="SPACING-jitter-null",
        value="jitter40",
        mode="jitter",
        description="40% of dots moved to a fixed-seed pseudo-random legal cell on the same ring (null)",
    ),
}

LEDGER_COLS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
    "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
    "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
    "evidence_class", "source_url",
]


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


def build_arm(key: str, parent: np.ndarray, footprint: np.ndarray, dcat: np.ndarray,
              ys: np.ndarray, xs: np.ndarray, selected: np.ndarray,
              density: np.ndarray, seed: int) -> dict:
    cfg = ARMS[key]
    rng = np.random.default_rng(seed)
    res = moves.apply_moves(parent, footprint, dcat, ys, xs, selected,
                            mode=cfg["mode"], density=density, rng=rng,
                            floor_px=geom.CATALOGUE_FLOOR_PX)
    return {"cfg": cfg, **res}


def prediction(mode: str, proxy_r0: float, proxy_v: float) -> tuple[float, list[float], str]:
    """MODEL prediction, stated so it can be attacked.

    rule:   delta_live = SHRINK * LIVE_SPAN * (proxy_v - proxy_r0) / proxy_r0
            for the two dosed arms; the null arm is 0.0 by construction
            (its expectation is zero; its proxy wobble is noise).
    band:   +/- 0.008 - the axis is expected to be flat, and the instrument
            that drives the sign is nearly blind to it (see the mechanism card).
    why SHRINK=0.1: the proxy's own live correlation is unmeasured on this axis,
            so only a tenth of its implied relative change is claimed.
    """
    if mode == "jitter" or proxy_r0 <= 0:
        return 0.0, [-0.008, 0.008], "null arm: expectation 0 by construction"
    rel = (proxy_v - proxy_r0) / proxy_r0
    d = round(float(SHRINK * LIVE_SPAN * rel), 4)
    return d, [round(d - 0.008, 3), round(d + 0.008, 3)], f"rel proxy change {rel:+.3f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    if not args.build:
        print(__doc__)
        return 0

    for p in (TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS, ANC_D28, ANC_SOLO):
        if not p.is_file():
            raise SystemExit(f"missing pinned input {p}; run scripts/restore_data.py")

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

    ys, xs = np.nonzero(parent)
    selected = geom.densest_dot_selection(ys, xs, SELECT_FRAC, BLOCK_PX)
    density = moves.density_potential(parent, sigma=2.0)

    r0_proxy = proxy.hide_and_recover(parent, cat, footprint)
    r0_stats = {
        "proxy": r0_proxy,
        "redundancy": proxy.redundancy(parent),
        "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
        "nn": moves.nearest_neighbour_stats(parent),
        "uniform_truth_credit": proxy.uniform_truth_credit(parent, footprint),
    }

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    releases = ROOT / "releases"
    rows, evidence = [], {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                          "parent": PARENT_ID, "lineage": lineage, "r0": r0_stats,
                          "select_frac": SELECT_FRAC, "block_px": BLOCK_PX, "arms": {}}

    for key in ARMS:
        built = build_arm(key, parent, footprint, dcat, ys, xs, selected, density, SEED)
        dots = built["dots"]
        diff = gates.parent_diff(parent, dots)

        # write, then name from the actual sha8 (prior-session convention)
        tmp_nan = releases / "_tmp-nan.tif"
        tmp_zer = releases / "_tmp-zeros.tif"
        io.write_float32(tmp_nan, np.where(footprint, dots.astype("float32"), np.nan), encoding="nan", template=TEMPLATE)
        io.write_float32(tmp_zer, np.where(footprint, dots.astype("float32"), np.nan), encoding="zeros", template=TEMPLATE)
        sha8 = io.sha256_file(tmp_nan)[:8]
        stem = f"{PARENT_ID}-SPACING{key}-{today}-{sha8}"
        final_nan = releases / f"{stem}.tif"
        final_zer = releases / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(final_nan, template=TEMPLATE, catalogue=cat,
                                       encoding="nan", expect_dots=PARENT_DOTS)
        g_zer = gates.validate_release(final_zer, template=TEMPLATE, catalogue=cat,
                                       encoding="zeros", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv")
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL {key}: nan={g_nan['failed']} zeros={g_zer['failed']}")

        # collar drift: did the edit quietly move mass INTO the 2-3 px ring, which is
        # what the hide-and-recover proxy actually measures? (see mechanism card)
        moved_new = dots & ~parent
        collar = {
            "mean_dcat_moved_source_px": round(float(dcat[parent & ~dots].mean()), 4) if (parent & ~dots).any() else None,
            "mean_dcat_moved_target_px": round(float(dcat[moved_new].mean()), 4) if moved_new.any() else None,
            "targets_in_2to3px_collar": int(((dcat > 2.0) & (dcat <= 3.0) & moved_new).sum()),
            "sources_in_2to3px_collar": int(((dcat > 2.0) & (dcat <= 3.0) & parent & ~dots).sum()),
        }
        v_proxy = proxy.hide_and_recover(dots, cat, footprint)
        u_credit = proxy.uniform_truth_credit(dots, footprint)
        pred, band, basis = prediction(ARMS[key]["mode"], r0_proxy["proxy_mean_credit"],
                                       v_proxy["proxy_mean_credit"])
        moved_mask = dots & ~parent
        can = proxy.canary(moved_mask, dots, cat)

        rec = {
            "id": stem,
            "axis": "SPACING",
            "value": key,
            "description": ARMS[key]["description"],
            "n_dots": int(dots.sum()),
            "relocated_dots": int(built["n_moved"]),
            "pct_relocated_of_parent": round(100.0 * built["n_moved"] / PARENT_DOTS, 4),
            "hamming_vs_parent": diff,
            "mean_displacement_px": round(built["mean_displacement_px"], 4),
            "max_displacement_px": built["max_displacement_px"],
            "n_selected": built["n_movable"],
            "n_blocked_by_geometry": built["n_blocked"],
            "mean_density_from": round(built["mean_density_from"], 6),
            "mean_density_to": round(built["mean_density_to"], 6),
            "sha256_nan": g_nan["sha256"],
            "sha256_zeros": g_zer["sha256"],
            "sha8": sha8,
            "dot_set_digest": g_nan["dot_set_digest"],
            "proxy": v_proxy,
            "collar_drift": collar,
            "uniform_truth_credit": u_credit,
            "proxy_delta_vs_r0": round(v_proxy["proxy_mean_credit"] - r0_proxy["proxy_mean_credit"], 6),
            "redundancy": proxy.redundancy(dots),
            "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
            "nn": moves.nearest_neighbour_stats(dots),
            "canary": can,
            "predicted_change_MODEL": pred,
            "predicted_range": band,
            "prediction_basis": basis,
            "gates": {k: v for k, v in g_nan.items() if k in
                      ("PASS", "failed", "crs_matches_template", "shape_matches_template",
                       "transform_matches_template", "single_band", "dtype_float32",
                       "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                       "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                       "catalogue_floor_respected", "count_matches_parent")},
            "gates_zeros": {k: g_zer[k] for k in ("PASS", "failed", "sha256_not_in_ledger")},
        }
        evidence["arms"][key] = rec

        note = (f"{PARENT_ID}; {ARMS[key]['description']}; "
                f"{built['n_moved']} dots ({rec['pct_relocated_of_parent']:.2f}%), "
                f"count fixed {int(dots.sum())}; predicted {pred:+.4f} MODEL")[:140]
        rows.append({
            "id": stem, "parent": PARENT_ID, "axis": "SPACING", "value": key,
            "n_dots": int(dots.sum()), "pct_changed": rec["pct_relocated_of_parent"],
            "pct_relocated": rec["pct_relocated_of_parent"],
            "sha256": g_nan["sha256"], "sha256_zeros": g_zer["sha256"],
            "status": "BUILT", "predicted_change": f"{pred:+.4f} MODEL",
            "predicted_range": f"[{band[0]:+.3f},{band[1]:+.3f}]",
            "ranking_basis": f"local density potential sigma=2px, {ARMS[key]['mode']} of ring-2 cells",
            "receipt_score": "", "receipt_date": "", "date": dt.date.today().isoformat(),
            "form_note": note, "evidence_class": "MODEL",
            "source_url": "https://github.com/buffedlizard55-lab/GEMSDOE91/pull/1",
        })
        print(f"{stem}: dots={int(dots.sum())} relocated={built['n_moved']} "
              f"({rec['pct_relocated_of_parent']:.2f}%) mean_disp={rec['mean_displacement_px']} "
              f"dens {built['mean_density_from']:.4f}->{built['mean_density_to']:.4f} "
              f"proxy={v_proxy['proxy_mean_credit']:.6f} pred={pred:+.4f}")

    ledger = ROOT / "ledger" / "submissions.csv"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if ledger.is_file():
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    ids = {r["id"] for r in existing}
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LEDGER_COLS, extrasaction="ignore")
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in LEDGER_COLS})
        for r in rows:
            if r["id"] not in ids:
                w.writerow(r)

    out = ROOT / "evidence" / "spacing_axis_20261023.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"\nledger rows appended: {len(rows)}\nevidence: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
