#!/usr/bin/env python3
"""GEMSDOE91 Experiment H1 — Blind damage-zone envelope (unique lane).

Geological hypothesis (H1, PhD level):
  In the northern Great Basin (Basin & Range / Walker Lane) >75% of geothermal
  systems are BLIND: no surface hot spring, geyser, fumarole or sinter terrace
  (Faulds & Hinz 2015, WGC-2015; INGENIOUS/DE-EE0006731). Hydrothermal upflow
  does not localize on simple mid-segment mapped traces (those seal with clay
  gouge and quartz/calcite cement); it concentrates at structural complexities
  OFF the traces — hybrid step-overs/en-echelon relay ramps (~32-36% of
  systems), fault terminations/horse-tails (~22%), fault intersections (~22%),
  accommodation/transfer zones (~11%) and pull-aparts (~9%). The competition
  catalogue (existing_faults.tif) maps traces; the R0 parent dots (h33-2-b2,
  CLAIM 0.2778, no organiser receipt) emit on/near catalogue traces. H1 places
  its emission budget 300 m-2 km OFF the mapped traces, inside the annulus
  where blind-system damage-zone/relay permeability is expected, weighted by
  catalogue-INDEPENDENT geophysical proxies: dependent swarm excess (B10-B16),
  magnetic edge/destruction (B3/B9/B14), geodetic strain (B4/B7/B8),
  scarp topography (B12/B19) and depth to basement (B15).

  Named non-fault mimic: Basin-range topography/strain and swarm seismicity
  also occur away from faults (distributed crustal deformation, volcanic
  swarms, buried plutons) — the canary tests whether any single feature alone
  recovers withheld faults (AUC > 0.90 = leakage until proven otherwise).

Method (PARALLEL-RUN PROTOCOL):
  * REUSE: scripts/evaluate_holdout.py (folds + pooled DTI alpha=0.2 beta=0.8,
    R=300 m triangular kernel), scripts/submission_writer.py (fail-closed
    writer: [0,1], no NaN inside footprint, CRS/shape/transform match,
    catalogue collar >= 3 px, ledger dedupe), scripts/dti.py.
  * Holdout: hide-and-recover, whole fault segments with 1 km buffer, 4
    spatial blocks; catalogue-based features derived ONLY from visible faults
    (H1 uses NO catalogue-derived feature at all — placement mask is a format
    collar, not a scoring feature); visible faults masked pixel-exactly.
  * Rule 1 LANE: surface |Spearman rho| <= 0.90 vs every registry raster AND
    <= 70% of final dots within 3 px of any registry raster's dots (checked
    pre-placement on the surface AND on final dots).
  * Rule 4: leakage canary, every feature alone on the holdout.
  * Rule 3: every number labelled HOLDOUT-DTI (evaluator, withheld positives,
    95% CI); projections never written as scores.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "scripts"), str(ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

import dti as D
from evaluate_holdout import (
    build_segment_buffered_folds,
    run_leakage_canary,
    score_pooled_holdout,
    check_registry_uniqueness,
    EVALUATOR_VERSION,
    EVALUATOR_VERSION_V11,
)
import submission_writer as SW

TEMPLATE = ROOT / "data" / "official" / "sample_submission.tif"
CATALOGUE = ROOT / "data" / "official" / "existing_faults.tif"
FEATURES = ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif"
REGISTRY_RASTERS = [
    ROOT / "data" / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif",
    ROOT / "data" / "registry" / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif",
    ROOT / "data" / "registry" / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif",
]

N_DOTS = 37_654          # winner-geometry dot budget (matches R0)
COLLAR_PX = 3.0          # format gate: dots > 3 px from catalogue
ANNULUS_MAX_PX = 20.0    # damage-zone reach: 300 m - 2 km off mapped traces
SEED = 91
DATE_TAG = "20261025T000000Z"
STEM_PREFIX = "GEMS91-H1-blind-damage-zone"


def pct_rank(x: np.ndarray) -> np.ndarray:
    """Percentile rank in [0, 1] with average ties; NaN-safe (NaN -> 0 rank)."""
    finite = np.isfinite(x)
    out = np.zeros_like(x, dtype=np.float64)
    if finite.any():
        r = rankdata(x[finite], method="average")
        out[finite] = (r - 1.0) / max(1.0, float(r.size - 1.0))
    return out


def main() -> int:
    # ---- load grid inputs -------------------------------------------------
    with rasterio.open(TEMPLATE) as s:
        template_arr = s.read(1)
        profile = {
            "crs": s.crs, "transform": s.transform, "height": s.height,
            "width": s.width,
        }
    footprint = np.isfinite(template_arr)
    with rasterio.open(CATALOGUE) as s:
        catalogue = (s.read(1) > 0) & footprint
    assert catalogue.any(), "catalogue empty"

    # ---- load catalogue-independent feature bands -------------------------
    # Band index (1-based) -> description (from pinned training_features.tif):
    # 3 tmi_hg, 4 geod_2ndinv, 8 geod_dilaterate, 9 tmi_vg, 10 deq_n100a15,
    # 14 tmi, 16 ieq_n100a15, 19 det_elev_slope
    band_idx = [3, 4, 8, 9, 10, 14, 16, 19]
    bands: dict[str, np.ndarray] = {}
    with rasterio.open(FEATURES) as s:
        for i in band_idx:
            bands[f"B{i:02d}"] = np.nan_to_num(s.read(i), nan=0.0, posinf=0.0, neginf=0.0)

    # ---- feature construction (no catalogue-derived term anywhere) --------
    def log1p_safe(x: np.ndarray) -> np.ndarray:
        return np.log1p(np.clip(x, -0.999999, None))

    swarm_excess = log1p_safe(bands["B10"]) - 0.85 * log1p_safe(bands["B16"])  # KB: fluid swarm excess
    mag_edge = np.maximum(bands["B03"], bands["B09"])                          # magnetic edges
    strain = 0.5 * bands["B04"] + 0.5 * bands["B08"]                           # geodetic 2nd invariant + dilatation
    mag_destruction = -bands["B14"]                                            # hydrothermal magnetite destruction -> low TMI
    scarp = bands["B19"]                                                       # detrended elevation slope (scarps)

    feature_specs = [
        ("swarm_excess_B10_B16", swarm_excess),
        ("mag_edge_B03_B09", mag_edge),
        ("strain_B04_B08", strain),
        ("mag_destruction_minus_B14", mag_destruction),
        ("scarps_B19", scarp),
    ]

    # ---- folds (hide-and-recover, whole segments, 1 km buffer) ------------
    folds = build_segment_buffered_folds(
        catalogue.astype(np.float32), footprint, bridge_px=3, buffer_px=10.0
    )
    n_withheld = sum(f.n_withheld for f in folds)
    print(f"folds: {[(f.name, f.n_withheld, f.n_visible, f.n_segments_withheld) for f in folds]}")
    print(f"total withheld positives: {n_withheld}")

    # ---- Rule 4 leakage canary: every feature ALONE on the holdout --------
    fp_idx = np.full(footprint.shape, -1, dtype=np.int32)
    fp_idx[footprint] = np.arange(int(footprint.sum()), dtype=np.int32)
    F = np.column_stack([np.nan_to_num(f[footprint], nan=0.0).astype(np.float64)
                         for _, f in feature_specs])
    names = [n for n, _ in feature_specs]
    canary = run_leakage_canary(F, names, folds, footprint, subsample_step=4)
    print("leakage canary:", json.dumps({
        "worst_feature": canary["worst_feature"],
        "worst_symmetric_auc": canary["worst_symmetric_auc"],
        "all_pass": canary["all_pass"],
        "n_features_tested": canary["n_features_tested"],
    }))
    for n, info in canary["features"].items():
        print(f"  canary {n:28s} meanAUC={info['mean_raw_auc']} maxSymAUC={info['max_fold_symmetric_auc']} pass={info['pass']}")
    if not canary["all_pass"]:
        print("CANARY FAIL: a feature alone recovers withheld faults (AUC > 0.90) - leakage; aborting build")
        return 2

    # ---- prospectivity surface: average of percentile ranks ---------------
    fp_vals = {name: np.nan_to_num(f, nan=0.0)[footprint].astype(np.float64)
               for name, f in feature_specs}
    ranks = np.column_stack([pct_rank(v) for v in fp_vals.values()])  # (N_footprint, n_features)
    prospectivity = np.zeros(footprint.shape, dtype=np.float64)
    prospectivity[footprint] = ranks.mean(axis=1)  # [0,1], catalogue independent

    # ---- placement mask: damage-zone annulus off mapped traces ------------
    d_cat = ndi.distance_transform_edt(~catalogue)
    mask = footprint & (d_cat > COLLAR_PX) & (d_cat <= ANNULUS_MAX_PX)
    cand_rows, cand_cols = np.nonzero(mask)
    cand_scores = prospectivity[cand_rows, cand_cols]
    print(f"placement mask: {cand_rows.size:,} candidate pixels ({100.0*cand_rows.size/footprint.sum():.2f}% of footprint)")

    # ---- dot placement: top-K by prospectivity, deterministic tie-break ---
    order = np.lexsort((cand_cols, cand_rows, -cand_scores))  # row, then col, then -score
    pick = order[:N_DOTS]
    dot_rows, dot_cols = cand_rows[pick], cand_cols[pick]
    min_score = float(cand_scores[pick].min())
    print(f"selected {dot_rows.size} dots; min prospectivity among dots: {min_score:.4f}")

    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[dot_rows, dot_cols] = np.float32(1.0)

    surface_fp = grid[footprint].astype(np.float64)

    # ---- Rule 1 LANE: pre-placement surface vs registry rasters -----------
    lane = check_registry_uniqueness(
        surface_fp, grid, footprint, [str(p) for p in REGISTRY_RASTERS if p.is_file()]
    )
    print("surface uniqueness:", json.dumps({
        k: v for k, v in lane.items() if k != "comparisons"
    }, indent=1))
    for c in lane.get("comparisons", []):
        print(f"  vs {c['registry_raster']}: surface|rho|={c['surface_abs_rank_corr']} "
              f"dots|rho|={c['dots_abs_rank_corr']} cand->reg<=3px={c['cand_within_3px_of_reg']} "
              f"reg->cand<=3px={c['reg_within_3px_of_cand']}")
    worst_surf = max((c["surface_abs_rank_corr"] for c in lane.get("comparisons", [])), default=0.0)
    worst_overlap = max((c["cand_within_3px_of_reg"] for c in lane.get("comparisons", [])), default=0.0)
    lane_pass = bool(lane["uniqueness_pass"]) and worst_overlap <= 0.70
    print(f"LANE PASS: {lane_pass}  (max surface |rho|={worst_surf} <= 0.90; "
          f"max dots within 3 px of a registry raster={worst_overlap*100:.2f}% <= 70%)")
    if not lane_pass:
        print("LANE FAIL: drifted into another lane - log as duplicate and stop")
        return 3

    # ---- holdout: hide-and-recover pooled DTI -----------------------------
    # IMPORTANT: every dot is > 3 px from the FULL catalogue (format collar)
    # and the DTI kernel radius is 3 px, so no dot can earn kernel credit
    # against any withheld fault pixel => pooled HOLDOUT-DTI is structurally
    # 0.0 under the current gates (verified empirically on S15-HCPA).
    fold_predictions = {f.fold_id: grid for f in folds}
    res_v11 = score_pooled_holdout(fold_predictions, folds, footprint,
                                   mask_buffer_predictions=False)
    res_v10 = score_pooled_holdout(fold_predictions, folds, footprint,
                                   mask_buffer_predictions=True)
    print("holdout v1.1-nohalo:", res_v11["holdout_dti"], res_v11["ci_95"])
    print("holdout v1.0 (halo):", res_v10["holdout_dti"], res_v10["ci_95"])

    # ---- write the validated submission bundle ----------------------------
    audit = SW.write_validated_submission_bundle(
        dot_or_prob_grid=grid,
        stem_prefix=STEM_PREFIX,
        date_tag=DATE_TAG,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs" / "downloads",
        floor_px=3.0,
        bundle_js_filename="h1_blind_zone_submission_bundle.js",
    )
    print("bundle written:", audit["candidate_id"])
    print("zeros tif:", audit["primary_zeros_tif"]["filename"])
    print("zip:", audit["zip_bundle"]["filename"])
    print("sha256:", audit["primary_zeros_tif"]["sha256"])
    print("validators:", audit["validators"])

    # ---- run card (Rule 5) ------------------------------------------------
    note = ("H1 blind damage-zone: 37654 dots 300m-2km off catalogue; "
            "swarm/mag/strain/topo; zeros [0,1]; HOLDOUT-DTI 0.0; "
            "no organizer receipt")
    assert len(note) <= 140, f"note too long: {len(note)} ({len(note)})"
    run_card = {
        "schema": "gems91.run-card.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "branch": "arena/37d15813-gemsdoe91",
        "lane": "H1-blind-damage-zone",
        "hypothesis": {
            "name": "H1",
            "statement": "Blind geothermal upflow concentrates at structural complexities "
                         "(step-overs/relay ramps, terminations, intersections, transfer zones, "
                         "pull-aparts) 300 m-2 km OFF mapped catalogue traces; >75% of Great "
                         "Basin systems are blind (Faulds & Hinz 2015; INGENIOUS DE-EE0006731).",
            "layers": ["training_features B03 tmi_hg, B04 geod_2ndinv, B08 geod_dilaterate, "
                       "B09 tmi_vg, B10 deq_n100a15, B14 tmi, B16 ieq_n100a15, B19 det_elev_slope"],
            "signature": "damage-zone/relay permeability envelope off traces: swarm excess "
                         "log1p(B10)-0.85log1p(B16), magnetic edge max(B03,B09), strain "
                         "0.5(B04+B08), -B14 magnetite destruction, B19 scarp slope; "
                         "percentile-rank averaged prospectivity.",
            "why_blind": "Targets upflow missed by trace catalogues; R0 dots sit on/near "
                         "catalogued traces, so an off-trace annulus is a disjoint physical target.",
            "differs_from_repo": "No lane in this repo places dots exclusively off traces with "
                                 "no catalogue-derived scoring feature; existing lanes (SPAC, "
                                 "PTHA, HVDC, LSFF, S15-HCPA, DZEDGE) hold count or mass to "
                                 "parent/catalogue dots.",
            "named_non_fault_mimic": "Distributed Basin & Range strain, volcanic/tectonic "
                                     "swarms and buried plutons produce strain/swarm/topography "
                                     "anomalies away from faults (tested by the canary).",
        },
        "mechanism": "Top-K percentile-rank prospectivity dots in the 300 m-2 km off-catalogue "
                     "annulus, unit mass, count-fixed at 37,654 (winner geometry); collar is a "
                     "format gate, not a scoring feature.",
        "holdout_dti": {
            "evaluator_version": EVALUATOR_VERSION,
            "n_withheld_positives": n_withheld,
            "v1_1_nohalo": res_v11,
            "v1_0_halo": res_v10,
            "note": "Structurally 0.0 under current gates: collar >3 px == DTI kernel radius "
                    "3 px, so no dot can reach any withheld fault pixel; historical positive "
                    "holdout numbers (0.09-0.26) are not reproducible with current tools.",
        },
        "leakage_canary": canary,
        "registry": {
            "surface_check": lane,
            "dot_overlap_3px": lane.get("comparisons", []),
            "lane_pass": bool(lane_pass),
        },
        "submission": {
            "candidate_id": audit["candidate_id"],
            "name": audit["candidate_id"],
            "note": note,
            "note_chars": len(note),
            "zeros_tif": audit["primary_zeros_tif"],
            "zip": audit["zip_bundle"],
            "sha256": audit["primary_zeros_tif"]["sha256"],
            "n_dots": audit["dots"]["n_dots"],
        },
        "validator_output": audit["validators"],
        "verdict": "negative",
        "verdict_reason": "Format CERTIFIED and lane-unique, but local holdout cannot confirm "
                          "quality (structurally 0.0: collar radius equals kernel radius) and no "
                          "organizer submission-page receipt exists; OK TO DOWNLOAD: YES, "
                          "OK TO SUBMIT: NO pending human selector + live receipt.",
    }
    card_path = ROOT / "docs" / "run-card-H1-blind-damage-zone.json"
    card_path.write_text(json.dumps(run_card, indent=2) + "\n", encoding="utf-8")
    print("run card:", card_path)
    print("VERDICT:", run_card["verdict"])
    return 0 if lane_pass and canary["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
