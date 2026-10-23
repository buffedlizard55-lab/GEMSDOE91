#!/usr/bin/env python3
"""RELIEF axis on R0: three matched arms that differ ONLY in relief-tercile direction.

Parent R0 = `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32), 37,654 unit dots,
sha256 baeae321... (NaN) / c55bafc4... (zeros), CLAIM 0.2778, no receipt anywhere
in this lineage.

Relief field
------------
Band 12 of the pinned feature stack, `det_elev` (detrended elevation; band 19
`det_elev_slope` is carried through the audit as a robustness check). Terciles are
equal-count over the 5,167,373 footprint cells:

    0 basin       det_elev <= q33          (cut reported in the evidence JSON)
    1 piedmont    q33 < det_elev <= q67
    2 range front det_elev >  q67

The edit
--------
15 % of R0's dots (5,648) are relocated. In every arm:

* the same number of dots moves, and the count is invariant (a dot that cannot
  be placed returns to its own cell, so nothing is deleted or duplicated);
* donors are drawn uniformly at random (seed 91) from the arm's donor tercile(s),
  so the donor set is not selected by any second criterion;
* recipients keep > 3 px from the catalogue (brief 4.4) and >= 2.8 px from every
  surviving dot and from each other -- 2.8 px is R0's measured spacing floor
  (min nn = 2*sqrt(2), 11,415 dots sit exactly there);
* recipients are placed OFF the parent lineage's own detector support (the
  `calib_h195` field that contains all 37,654 R0 dots). Reason, measured: R0 is
  **spacing-saturated on its own support** -- only 90 support cells in the whole
  footprint are >= 2.8 px from a surviving dot -- and a support preference would
  hand the arms different numbers of on-support recipients (96 for the narrow arm
  vs 2,409 for the null arm), confounding the tercile contrast. Placing every arm
  off support keeps that mix identical at 0;
* recipients are chosen by the same greedy priority rule in every arm.

Arms
----
r2m15    range front -> piedmont        (best-supported direction in the audit)
m2r15    piedmont -> range front        (exact sign flip)
null15   uniform donors, any tercile    (relocation-only control)

The brief's own example direction, basin -> range front, is NOT built: the audit
shows it has almost no donors (191 dots sit in the lowest det_elev_slope tercile)
and that the two terciles carry nearly the same mapped-fault density (1.077 % vs
1.027 %), so it is a near-no-op. Its predicted delta is computed and reported.

Usage
-----
    python3 scripts/build_relief.py --check     # inputs only
    python3 scripts/build_relief.py --build     # writes releases/, ledger rows
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

from gems91 import geom, io, moves, proxy, relief, release_gates as gates  # noqa: E402

DATA = ROOT / "data"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
PARENT_NAN = DATA / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif"
PARENT_ZEROS = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
ANC_D28 = DATA / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"
ANC_SOLO = DATA / "registry" / "GEMSDOE28__h27-4-r1-solo-d2-8.tif"
ANC_FIELD = DATA / "registry" / "calib_h195_01922.tif"
FEATURES = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
MANIFEST = ROOT / "registry" / "data_manifest.json"

BAND_DET_ELEV = 12
BAND_DET_ELEV_SLOPE = 19

PARENT_ID = "h33-h33-2-b2-20261004-e5eb6e7e"
PARENT_DOTS = 37654
FRACTION = 0.15
SEED = 91
MIN_CAT_PX = 3.0
MIN_SEP_PX = 2.8
SHRINK = 0.5          # only half of the prior-implied change is claimed
LIVE_SPAN = 0.2778    # CLAIM, used only as the scale of a MODEL prediction

ARMS = {
    "r2m15": dict(value="r2m15", donors=(2,), targets=(1,), quotas=None,
                  short="RELIEF range-front->piedmont (band12 terciles)",
                  description="15% of dots moved range-front->piedmont terciles"),
    "m2r15": dict(value="m2r15", donors=(1,), targets=(2,), quotas=None,
                  short="RELIEF sign flip piedmont->range-front",
                  description="15% of dots moved piedmont->range-front terciles (sign flip)"),
    "null15": dict(value="null15", donors=(0, 1, 2), targets=None, quotas="donor_mix",
                   short="RELIEF null, tercile mix held",
                   description="15% of dots relocated with no tercile target (null)"),
}

LEDGER_COLS = [
    "id", "parent", "axis", "value", "n_dots", "pct_changed", "pct_relocated",
    "sha256", "sha256_zeros", "status", "predicted_change", "predicted_range",
    "ranking_basis", "receipt_score", "receipt_date", "date", "form_note",
    "evidence_class", "source", "notes", "source_url",
]


def pinned_sha256(entry_id: str) -> str | None:
    man = json.loads(MANIFEST.read_text())
    for f in man["files"]:
        if f["id"] == entry_id:
            return f["sha256"]
    return None


def require_inputs() -> None:
    missing = [p for p in (TEMPLATE, CATALOGUE, PARENT_NAN, PARENT_ZEROS, ANC_D28,
                           ANC_SOLO, ANC_FIELD, FEATURES) if not p.is_file()]
    if missing:
        raise SystemExit("missing pinned inputs: " + ", ".join(str(p) for p in missing)
                         + "\nrun scripts/restore_data.py first")
    for path, pin in ((FEATURES, pinned_sha256("training_features")),
                      (TEMPLATE, pinned_sha256("sample_submission")),
                      (CATALOGUE, pinned_sha256("existing_faults")),
                      (PARENT_NAN, pinned_sha256("parent_r0_nan")),
                      (PARENT_ZEROS, pinned_sha256("parent_r0_zeros")),
                      (ANC_D28, pinned_sha256("anc_d2_8")),
                      (ANC_SOLO, pinned_sha256("anc_solo_d2_8"))):
        got = io.sha256_file(path)
        if pin and got != pin:
            raise SystemExit(f"HASH MISMATCH {path.name}: {got} != pinned {pin}")


def read_band(path: Path, band: int) -> np.ndarray:
    import rasterio
    with rasterio.open(path) as ds:
        return ds.read(band).astype(np.float64)


def rebuild_parent(cat_dist: np.ndarray) -> dict:
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    zeros = io.dot_mask(io.read_grid(PARENT_ZEROS))
    out = {
        "parent_sha256_nan": io.sha256_file(PARENT_NAN),
        "parent_sha256_zeros": io.sha256_file(PARENT_ZEROS),
        "parent_dot_digest": io.dot_digest(parent),
        "n_dots": int(parent.sum()),
        "twins_identical": bool(np.array_equal(parent, zeros)),
        "min_catalogue_distance_px": round(float(cat_dist[parent].min()), 6),
        "dots_on_catalogue": int((parent & (cat_dist == 0)).sum()),
        "rebuilt_from": {},
    }
    for name, path in (("d2.8", ANC_D28), ("solo_d2.8", ANC_SOLO)):
        anc = io.dot_mask(io.read_grid(path))
        kept = anc & (cat_dist > geom.CATALOGUE_FLOOR_PX)
        out["rebuilt_from"][name] = {
            "n_ancestor_dots": int(anc.sum()),
            "n_after_collar": int(kept.sum()),
            "identical_to_parent": bool(np.array_equal(kept, parent)),
        }
    return out


def tercile_table(field: np.ndarray, footprint: np.ndarray, cat: np.ndarray,
                  dots: np.ndarray, tercile: np.ndarray, dcat: np.ndarray) -> list[dict]:
    rows = []
    for t in range(3):
        m = footprint & (tercile == t)
        c = int((cat & m).sum())
        d = int((dots & m).sum())
        rows.append({
            "tercile": t,
            "label": relief.TERCILE_LABELS[t],
            "footprint_px": int(m.sum()),
            "field_min": round(float(field[m].min()), 4),
            "field_max": round(float(field[m].max()), 4),
            "catalogue_px": c,
            "catalogue_density_pct": round(100.0 * c / int(m.sum()), 4),
            "dots": d,
            "dot_density_pct": round(100.0 * d / int(m.sum()), 4),
            "dot_to_catalogue_ratio": round((d / int(m.sum())) / (c / int(m.sum())), 4),
            "mean_dcat_of_dots_px": round(float(dcat[dots & m].mean()), 3) if d else None,
        })
    return rows


def geom_support_distance(dots: np.ndarray) -> np.ndarray:
    return geom_module_distance(dots)


def geom_module_distance(dots: np.ndarray) -> np.ndarray:
    from scipy import ndimage as ndi
    return ndi.distance_transform_edt(~dots)


def expected_credit_density(tercile: np.ndarray, footprint: np.ndarray, cat: np.ndarray) -> dict:
    """PROXY estimator of the per-dot truth prior, one number per tercile."""
    out = {}
    for t in range(3):
        m = footprint & (tercile == t)
        out[t] = float((cat & m).sum()) / float(m.sum())
    out["all"] = float(cat[footprint].sum()) / float(footprint.sum())
    return out


def predict(donor_counts: dict, target_counts: dict, n_moved: int, dots: np.ndarray,
            tercile: np.ndarray, rho: dict) -> dict:
    """MODEL prediction from the tercile prior alone (no hidden truth is used).

    rule:  dT/T = n_moved * (rho_target - rho_donors) / sum_t(n_t * rho_t)
           delta_live = SHRINK * LIVE_SPAN * dT/T
    The rule assumes kernel credit per dot is proportional to the mapped-fault
    density of the tercile it sits in. That is the whole assumption; it is a
    transfer claim from mapped faults to new faults and is stated as such.
    """
    n_t = {t: int((dots & (tercile == t)).sum()) for t in range(3)}
    base = sum(n_t[t] * rho[t] for t in range(3))
    nd = sum(donor_counts.values())
    nt = sum(target_counts.values())
    rho_donor = sum(n * rho[t] for t, n in donor_counts.items()) / nd if nd else 0.0
    rho_target = sum(n * rho[t] for t, n in target_counts.items()) / nt if nt else 0.0
    drel = (n_moved * (rho_target - rho_donor) / base) if base else 0.0
    delta = round(float(SHRINK * LIVE_SPAN * drel), 4)
    return {
        "rho_target_pct": round(100.0 * rho_target, 4),
        "rho_donor_pct": round(100.0 * rho_donor, 4),
        "dT_over_T": round(float(drel), 6),
        "predicted_change": delta,
        "predicted_range": [round(delta - 0.010, 3), round(delta + 0.010, 3)],
        "basis": ("MODEL: dT/T from tercile catalogue density, SHRINK=0.5, LIVE_SPAN=0.2778 CLAIM; "
                  "assumes new-fault density follows mapped-fault density in tercile space"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if not (args.build or args.check):
        print(__doc__)
        return 0

    require_inputs()
    print("[OK] every pinned input present and hash-verified")

    template = io.read_grid(TEMPLATE)
    footprint = geom.footprint_mask(template)
    cat = geom.catalogue_mask(io.read_grid(CATALOGUE))
    dcat = geom.catalogue_distance(cat)
    parent = io.dot_mask(io.read_grid(PARENT_NAN))
    support = io.dot_mask(io.read_grid(ANC_FIELD))

    lineage = rebuild_parent(dcat)
    ok = (lineage["twins_identical"] and lineage["n_dots"] == PARENT_DOTS
          and all(v["identical_to_parent"] for v in lineage["rebuilt_from"].values()))
    print(f"[{'OK' if ok else 'FAIL'}] parent dot set rebuilt from both ancestors "
          f"({lineage['n_dots']} dots, digest {lineage['parent_dot_digest'][:8]})")
    if not ok:
        raise SystemExit(f"PARENT NOT REPRODUCED - stopping (brief section 5): {lineage}")
    if int((parent & ~support).sum()):
        raise SystemExit("support field does not contain every R0 dot")

    field = read_band(FEATURES, BAND_DET_ELEV)
    slope = read_band(FEATURES, BAND_DET_ELEV_SLOPE)
    tercile, cuts = relief.tercile_index(field, footprint)
    tercile_slope, cuts_slope = relief.tercile_index(slope, footprint)

    audit = {
        "band": BAND_DET_ELEV,
        "band_name": "det_elev",
        "cuts": [round(cuts[0], 4), round(cuts[1], 4)],
        "terciles": tercile_table(field, footprint, cat, parent, tercile, dcat),
        "robustness_band": BAND_DET_ELEV_SLOPE,
        "robustness_band_name": "det_elev_slope",
        "robustness_cuts": [round(cuts_slope[0], 4), round(cuts_slope[1], 4)],
        "robustness_terciles": tercile_table(slope, footprint, cat, parent, tercile_slope, dcat),
    }
    rho = expected_credit_density(tercile, footprint, cat)
    rho_slope = expected_credit_density(tercile_slope, footprint, cat)

    n_move = int(round(FRACTION * PARENT_DOTS))
    legal = footprint & ~parent & (dcat > MIN_CAT_PX) & (
        geom_module_distance(parent) >= MIN_SEP_PX - 1e-9)
    print(f"[audit] legal recipient cells at d_nn>={MIN_SEP_PX} px and d_cat>{MIN_CAT_PX} px: "
          f"{int(legal.sum())}, of which on lineage support: {int((legal & support).sum())} "
          f"(the parent is spacing-saturated on its own support)")
    n_t_parent = {t: int((parent & (tercile == t)).sum()) for t in range(3)}
    brief_dir = predict({0: n_t_parent[0]}, {2: n_move}, n_move, parent, tercile, rho)
    audit["brief_direction_basin_to_range_front"] = {
        "n_donors_available": int((parent & (tercile == 0)).sum()),
        "n_donors_available_slope_definition": int((parent & (tercile_slope == 0)).sum()),
        "prediction_if_built": brief_dir,
        "note": ("not built: near-no-op (see SLOT_PLAN.md). Under the brief's own "
                 "relief definition the low tercile holds almost no mass and its "
                 "mapped-fault density is within 5 % of the high tercile."),
    }
    print("[audit] det_elev terciles:")
    for row in audit["terciles"]:
        print(f"   {row['label']:<12} cat {row['catalogue_density_pct']:.3f}%  "
              f"dots {row['dots']:>6}  dot/cat {row['dot_to_catalogue_ratio']:.3f}")
    print("[audit] det_elev_slope terciles (robustness):")
    for row in audit["robustness_terciles"]:
        print(f"   {row['label']:<12} cat {row['catalogue_density_pct']:.3f}%  "
              f"dots {row['dots']:>6}  dot/cat {row['dot_to_catalogue_ratio']:.3f}")
    print(f"[audit] brief direction basin->range_front: {brief_dir['predicted_change']:+.4f} MODEL "
          f"({audit['brief_direction_basin_to_range_front']['n_donors_available']} donors available)")

    if args.check:
        return 0

    # null arm: send the same number of dots into each tercile it took out of it
    donor_mix = {t: n_t_parent[t] for t in range(3)}
    raw = {t: FRACTION * n for t, n in donor_mix.items()}
    quotas_null = {t: int(np.floor(v)) for t, v in raw.items()}
    rem = n_move - sum(quotas_null.values())
    for t in sorted(raw, key=lambda k: -(raw[k] - quotas_null[k]))[:rem]:
        quotas_null[t] += 1

    r0_proxy = proxy.hide_and_recover(parent, cat, footprint)
    r0_stats = {
        "proxy": r0_proxy,
        "redundancy": proxy.redundancy(parent),
        "block_density_cv_1km": proxy.block_density_cv(parent, footprint, 10),
        "nn": moves.nearest_neighbour_stats(parent),
        "uniform_truth_credit": proxy.uniform_truth_credit(parent, footprint),
        "tercile_counts": relief.tercile_counts(parent, tercile),
    }

    today = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
    releases = ROOT / "releases"
    evidence = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "axis": "RELIEF",
        "parent": PARENT_ID,
        "parent_dots": PARENT_DOTS,
        "lineage": lineage,
        "fraction": FRACTION,
        "n_move_requested": n_move,
        "seed": SEED,
        "min_cat_px": MIN_CAT_PX,
        "min_sep_px": MIN_SEP_PX,
        "support_field": "calib_h195_01922.tif (121,131 cells; contains all 37,654 R0 dots)",
        "feature_file_sha256": io.sha256_file(FEATURES),
        "audit": audit,
        "r0": r0_stats,
        "arms": {},
    }
    rows = []
    for key, cfg in ARMS.items():
        quotas = quotas_null if cfg["quotas"] == "donor_mix" else cfg["quotas"]
        res = relief.relief_shift(
            parent, footprint, dcat, None, tercile,
            donor_terciles=cfg["donors"], target_terciles=cfg["targets"],
            n_move=n_move, rng=np.random.default_rng(SEED),
            min_cat_px=MIN_CAT_PX, min_sep_px=MIN_SEP_PX,
            target_quotas=quotas)
        if not 1.0 <= res["pct_relocated"] <= 50.0:
            raise SystemExit(
                f"STOP: {key} relocated {res['pct_relocated']}% of dots; brief 5 requires 1-50% "
                f"(shortfall {res['n_shortfall']} of {res['n_requested']})")
        dots = res["dots"]
        diff = gates.parent_diff(parent, dots)

        tmp_nan = releases / "_tmp-relief-nan.tif"
        tmp_zer = releases / "_tmp-relief-zeros.tif"
        io.write_float32(tmp_nan, np.where(footprint, dots.astype("float32"), np.nan),
                         encoding="nan", template=TEMPLATE)
        io.write_float32(tmp_zer, np.where(footprint, dots.astype("float32"), np.nan),
                         encoding="zeros", template=TEMPLATE)
        sha8 = io.sha256_file(tmp_nan)[:8]
        stem = f"{PARENT_ID}-RELIEF{key}-{today}-{sha8}"
        final_nan = releases / f"{stem}.tif"
        final_zer = releases / f"{stem}-zeros.tif"
        tmp_nan.replace(final_nan)
        tmp_zer.replace(final_zer)

        g_nan = gates.validate_release(final_nan, template=TEMPLATE, catalogue=cat,
                                       encoding="nan", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv", own_id=stem)
        g_zer = gates.validate_release(final_zer, template=TEMPLATE, catalogue=cat,
                                       encoding="zeros", expect_dots=PARENT_DOTS,
                                       ledger=ROOT / "ledger" / "submissions.csv", own_id=stem)
        if not (g_nan["PASS"] and g_zer["PASS"]):
            raise SystemExit(f"GATE FAIL {key}: nan={g_nan['failed']} zeros={g_zer['failed']}")

        donor_counts = {t: n_t_parent[t] for t in cfg["donors"]}
        target_counts = (quotas if quotas is not None
                         else {t: res["n_moved"] for t in cfg["targets"]})
        pred = predict(donor_counts, target_counts, res["n_moved"], parent, tercile, rho)
        v_proxy = proxy.hide_and_recover(dots, cat, footprint)
        canary = proxy.canary(dots & ~parent, dots, cat)
        rec = {
            "id": stem,
            "axis": "RELIEF",
            "value": cfg["value"],
            "description": cfg["description"],
            "donor_terciles": res["donor_terciles"],
            "target_terciles": res["target_terciles"],
            "n_dots": res["n_dots"],
            "n_moved": res["n_moved"],
            "n_requested": res["n_requested"],
            "n_donor_pool": res["n_donor_pool"],
            "n_shortfall": res["n_shortfall"],
            "pct_relocated_of_parent": res["pct_relocated"],
            "pct_changed_hamming": res["pct_changed_hamming"],
            "hamming_vs_parent": diff,
            "target_quotas": quotas,
            "donor_tercile_mix": res["donor_tercile_mix"],
            "recipient_tercile_mix": res["recipient_tercile_mix"],
            "tercile_dot_fraction_before": res["before"]["fraction"],
            "tercile_dot_fraction_after": res["after"]["fraction"],
            "mean_displacement_px": res["mean_displacement_px"],
            "max_displacement_px": res["max_displacement_px"],
            "min_recipient_to_existing_dot_px": res["min_recipient_to_existing_dot_px"],
            "min_cat_dist_new_dots_px": res["min_cat_dist_new_dots_px"],
            "n_recipients_on_support": res["n_recipients_on_support"],
            "recipients_off_support_by_design": True,
            "support_cells_legal_before_move": int(((footprint & ~parent & (dcat > MIN_CAT_PX))
                                                    & (geom_support_distance(parent) >= MIN_SEP_PX - 1e-9)
                                                    & support).sum()),
            "all_legal_cells": res["all_legal_cells"],
            "support_legal_cells": res["support_legal_cells"],
            "nn": relief.nearest_separation(dots),
            "sha256_nan": g_nan["sha256"],
            "sha256_zeros": g_zer["sha256"],
            "sha8": sha8,
            "dot_set_digest": g_nan["dot_set_digest"],
            "proxy": v_proxy,
            "proxy_delta_vs_r0": round(v_proxy["proxy_mean_credit"]
                                       - r0_proxy["proxy_mean_credit"], 6),
            "canary": canary,
            "redundancy": proxy.redundancy(dots),
            "block_density_cv_1km": proxy.block_density_cv(dots, footprint, 10),
            "uniform_truth_credit": proxy.uniform_truth_credit(dots, footprint),
            "prediction_MODEL": pred,
            "gates": {k: v for k, v in g_nan.items() if k in
                      ("PASS", "failed", "crs_matches_template", "shape_matches_template",
                       "transform_matches_template", "single_band", "dtype_float32",
                       "no_nan_inside_footprint", "nan_outside_footprint", "values_within_0_1",
                       "unit_mass_dots", "zero_catalogue_mass", "min_catalogue_distance_px",
                       "catalogue_floor_respected", "count_matches_parent", "sha256_not_in_ledger")},
            "gates_zeros": {k: g_zer[k] for k in ("PASS", "failed", "sha256_not_in_ledger",
                                                  "zeros_outside_footprint")},
        }
        evidence["arms"][key] = rec

        note = (f"R0 h33-2-b2; {cfg['short']}: {res['n_moved']} dots moved "
                f"({res['pct_relocated']:.2f}%), count fixed {res['n_dots']}; "
                f"pred {pred['predicted_change']:+.4f} MODEL")[:140]
        rows.append({
            "id": stem, "parent": PARENT_ID, "axis": "RELIEF", "value": cfg["value"],
            "n_dots": res["n_dots"], "pct_changed": res["pct_relocated"],
            "pct_relocated": res["pct_relocated"],
            "sha256": g_nan["sha256"], "sha256_zeros": g_zer["sha256"],
            "status": "BUILT", "predicted_change": f"{pred['predicted_change']:+.4f} MODEL",
            "predicted_range": f"[{pred['predicted_range'][0]:+.3f},{pred['predicted_range'][1]:+.3f}]",
            "ranking_basis": ("no ranking used: donors uniform at fixed seed inside the donor "
                              "tercile; one greedy placement rule in every arm, off the lineage "
                              "support, d_nn>=2.8 px, d_cat>3 px (band 12 det_elev terciles)"),
            "receipt_score": "", "receipt_date": "", "date": dt.date.today().isoformat(),
            "form_note": note, "evidence_class": "MODEL",
            "source": "SESSION 5 (this branch)",
            "notes": (f"shortfall {res['n_shortfall']}; min d_nn after edit "
                      f"{relief.nearest_separation(dots)['nn_min']} px; min d_cat of new dots "
                      f"{res['min_cat_dist_new_dots_px']} px; canary {canary['canary_auc']}"),
        })
        print(f"{stem}: moved={res['n_moved']} ({res['pct_relocated']:.2f}%) "
              f"mean_disp={res['mean_displacement_px']:.1f} px "
              f"tercile_frac {res['before']['fraction']} -> {res['after']['fraction']} "
              f"pred={pred['predicted_change']:+.4f} canary={canary['canary_auc']}")

    ledger = ROOT / "ledger" / "submissions.csv"
    existing = []
    newline = "\n"
    if ledger.is_file():
        raw = ledger.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        with ledger.open(newline="", encoding="utf-8-sig") as fh:
            existing = list(csv.DictReader(fh))
    fieldnames = list(existing[0].keys()) if existing else []
    for c in LEDGER_COLS:
        if c not in fieldnames:
            fieldnames.append(c)
    ids = {r["id"] for r in existing}
    with ledger.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator=newline)
        w.writeheader()
        for r in existing:
            w.writerow({k: r.get(k, "") for k in fieldnames})
        for r in rows:
            if r["id"] not in ids:
                w.writerow({k: r.get(k, "") for k in fieldnames})

    out = ROOT / "evidence" / f"relief_axis_{today}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"\nledger rows appended: {len(rows)}\nevidence: {out}")

    # keep releases/MANIFEST.json the contract: hash of every shipped file
    man_path = releases / "MANIFEST.json"
    man = json.loads(man_path.read_text()) if man_path.is_file() else {"files": []}
    known = {f["file"]: f for f in man["files"]}
    for stem in [r["id"] for r in rows]:
        for name in (f"{stem}.tif", f"{stem}-zeros.tif"):
            p = releases / name
            entry = dict(known.get(name, {}))          # never drop fields another
            entry.update({"file": name,                # session recorded (eg n_dots)
                          "sha256": io.sha256_file(p),
                          "bytes": p.stat().st_size,
                          "axis": "RELIEF",
                          "n_dots": PARENT_DOTS})
            known[name] = entry
    man["files"] = [known[k] for k in sorted(known)]
    man["note"] = man.get("note", "")
    man_path.write_text(json.dumps(man, indent=2) + "\n")
    print(f"releases/MANIFEST.json updated: {len(man['files'])} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
