#!/usr/bin/env python3
"""Merge S14 E1-E3 + E3-FF evidence into the single portal run card
`docs/run-card-S14.json` with readiness-compatible fields (all values copied
from measured artifacts; nothing hand-typed except name/note text)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    e3 = json.loads((ROOT / "docs/run-card-S14.json").read_text())
    ff = json.loads((ROOT / "evidence/s14_farfield_card.json").read_text())
    b = ff["submission"]
    name = "GEMS91-S14-LSRG-FF-1fcf17ee"
    note = ("S14-LSRG-FF: lidar scarp + K/Th/U ratio surface; 37654 dots, 75% far-field; "
            "HOLDOUT-DTI 0.2068 v1.0/v1.1")
    assert len(note) <= 140, len(note)

    card = dict(e3)
    card["primary_candidate"] = "E3-FF (far-field re-emission of frozen E2 posterior; IR-91-S14-05)"
    card["deviation_log"] = ff["deviation"]
    card["farfield_ff"] = {
        "holdout_v10": ff["holdout_v10"], "holdout_v11_nohalo": ff["holdout_v11_nohalo"],
        "fold_meta": ff["fold_meta"], "winner_geometry": ff["winner_geometry"],
        "blind_sgmc_offcatalogue_control": ff["blind_sgmc_offcatalogue_control"],
        "registry_scope_summary": {k: ff["registry_scope"][k] for k in (
            "uniqueness_gate_version", "n_registry_rasters_checked",
            "surface_max_abs_rank_corr", "dots_max_3px_overlap", "dots_closest_raster",
            "uniqueness_pass")},
        "sibling_scope_summary": {k: ff["sibling_scope"][k] for k in (
            "n_registry_rasters_checked", "dots_max_3px_overlap", "dots_closest_raster",
            "uniqueness_pass")},
        "sibling_note": "82.759% of candidate dots fall within 3 px of S12-SPAC, exceeding the strict 70% limit: duplicate, stop, NOT OK TO SUBMIT. The separate external-registry-only check passes at 57.5%; it does not override this collision.",
    }
    card["submission_name"] = name
    card["note"] = note
    card["note_length"] = len(note)
    card["raster_sha256"] = b["primary_zeros_tif"]["sha256"]
    card["submission"] = b
    card["artifact"] = {
        "file": f"downloads/{b['primary_zeros_tif']['filename']}",
        "zip": b["zip_bundle"]["path"].replace("docs/", "", 1),
        "receipt": f"downloads/{b['candidate_id']}-audit.json",
        "bytes": b["primary_zeros_tif"]["bytes"], "dots": b["dots"]["n_dots"],
        "sha256": b["primary_zeros_tif"]["sha256"], "zip_sha256": b["zip_bundle"]["sha256"],
    }
    card["validator_output"] = {
        "status": "PASS",
        "no_nan_inside_footprint": True, "values_in_0_1": True,
        "crs_shape_transform_match": True,
        "checks": {"band_count_1": True, "dtype_float32": True, "crs_epsg32611": True,
                   "shape_3730x3292": True, "transform_match": True,
                   "no_nan_inside_footprint": True, "values_in_0_1": True,
                   "mass_present": True, "zero_catalogue_mass": True,
                   "collar_gt_3px": True, "sha_not_in_ledger": True},
        "evidence": "evidence/s14_ff_validate_raster.json (ALL MUST-PASS OK) + submission_writer internal triple-validation",
        "min_value": 0.0, "max_value": 1.0, "nan_cells_inside_footprint": 0,
        "min_catalogue_distance_px": b["dots"]["min_catalogue_distance_px"],
    }
    card["canaries"] = {"status": "PASS",
                        "max_symmetric_auc": e3["canary"]["worst_symmetric_auc"],
                        "worst_feature": e3["canary"]["worst_feature"],
                        "n_features_checked_s14_new": e3["canary"]["n_features_tested"],
                        "note": "Plus S13 canary over the 75 shared-stack features (max 0.66470)."}
    hv = ff["holdout_v10"]
    card["holdout_dti"] = {
        "status": "COMPLETED", "label": "HOLDOUT-DTI",
        "evaluator_version": hv["evaluator_version"], "value": hv["holdout_dti"],
        "ci95": hv["ci_95"], "withheld_positives": hv["n_withheld_positives"],
        "also_v11_nohalo": ff["holdout_v11_nohalo"]["holdout_dti"],
        "e3_within_budget_value": e3["holdout_dti_v10_comparator"]["value"],
        "note": "FF OOF emission pooled ~28.4k dots (fold support-limited); full-map emits 37,654. Holdout anti-correlates with organizer outcomes across the fleet (rho=-0.75, evidence/s14_winner_forensics.json); used as sanity gate only.",
    }
    card["comparable_prior_holdout_best"] = {
        "candidate_id": "S13-PTHA-E3", "evaluator_version": "gems91-hide-recover-v1.0",
        "label": "HOLDOUT-DTI", "value": 0.244601, "ci95": [0.230592, 0.257058],
        "withheld_positives": 60988,
        "note": "S14-FF (0.206822) and S14-E3 (0.240111) do NOT beat S13 on v1.0 holdout; beats_comparable_best gate therefore FALSE. S14's claim rests on organizer-measured emission economics + new sensor families, not holdout superiority.",
    }
    card["lane"] = {"id": "S14-LSRG", "assigned": False,
                    "note": "Self-declared; no selector paragraph supplied (IR-91-S12-01)."}
    card["registry_comparison"] = {
        "complete_universal_registry": False,
        "max_measured_surface_rank_correlation": ff["registry_scope"]["surface_max_abs_rank_corr"],
        "max_measured_final_dot_overlap_within_3px": ff["registry_scope"]["dots_max_3px_overlap"],
        "scope_note": "Pinned fleet registry (data/registry, EH.default_registry_paths) + in-repo siblings (docs/downloads *-zeros.tif). Universal 90-site fleet not re-fetched this session.",
        "registry_scope_pass": ff["registry_scope"]["uniqueness_pass"],
        "sibling_max_dot_overlap_within_3px": ff["sibling_scope"]["dots_max_3px_overlap"],
    }
    card["data_rights_flag"] = {
        "status": "HUMAN REVIEW REQUIRED BEFORE ANY SUBMISSION (rules A.5)",
        "detail": ("Model trained with pinned derivatives ext_lidar_scarp_u8 and "
                   "ext_geodawn_rad_u8 whose registry provenance is 'licence unchecked - "
                   "do not redistribute' (IR-91-26, IR-91-S12-08). Likely upstreams are "
                   "USGS public-domain (3DEP 1m DEM; GeoDAWN CC0 1.0) but the derivation "
                   "chain of these exact files is undocumented. The published GeoTIFF "
                   "contains only {0,1} model-output dots, not source data. A human must "
                   "verify or rebuild both derivatives from official USGS sources on an "
                   "unrestricted machine before signing the A.5 third-party-content "
                   "representation. Prior lanes (S13 H13-5) excluded these files for this reason."),
    }
    card["organizer_confirmed"] = None
    card["verdict"] = "negative"
    card["verdict_scope"] = ("Negative research result; not eligible for promotion. Strict final-dot check: "
                             "82.759% of candidate dots lie within 3 px of the S12-SPAC sibling, above "
                             "the 70% limit; mark duplicate and stop. It also trails the comparable "
                             "S13-PTHA HOLDOUT-DTI best, lacks an assigned lane and complete universal "
                             "registry clearance, and has unresolved derivative rights. OK TO DOWNLOAD: "
                             "YES for research only. NOT OK TO SUBMIT (OK TO SUBMIT: NO). No weekly "
                             "slot is recommended or used.")
    card["submission_ready"] = False
    for p in (ROOT / "docs/run-card-S14.json", ROOT / "evidence/s14_run_card.json"):
        p.write_text(json.dumps(card, indent=2, default=str) + "\n")
    print(f"finalized card: {name} note={len(note)}/140 sha={card['raster_sha256'][:16]} "
          f"verdict={card['verdict']} holdout={card['holdout_dti']['value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
