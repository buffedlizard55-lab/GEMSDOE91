#!/usr/bin/env python3
"""Assemble docs/run-card-ISO91.json from measured outputs only (no hand-typed numbers).

Inputs: docs/iso91/holdout-I1.json, holdout-I2.json, final.json, sibling-sweep.json, the TIFF/ZIP
in docs/downloads and the SHA-pinned sample/catalogue in data/official. The verdict is computed
from the preregistered gates in docs/HYPOTHESES_ISO91.md; it can only be "promote" if every gate
passes. The TIFF is re-opened from disk here (independent of the writer's receipt).
"""
from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "iso91"
CARD = DOCS / "run-card-ISO91.json"
GRID = dict(crs="EPSG:32611", shape=[3730, 3292], transform=[100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pinned(key: str) -> Path:
    rows = {r["id"]: r for r in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]}
    p = ROOT / "data" / rows[key]["local_subpath"]
    if sha(p) != rows[key]["sha256"]:
        raise ValueError(f"untrusted pinned input {key}")
    return p


def independent_validation(tif: Path) -> dict:
    with rasterio.open(pinned("sample_submission")) as s:
        ref = dict(crs=str(s.crs), shape=list(s.shape), transform=list(s.transform)[:6])
        fp = np.isfinite(s.read(1))
    with rasterio.open(pinned("existing_faults")) as c:
        cat = (c.read(1) > 0) & fp
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        meta = dict(count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs), shape=list(ds.shape),
                    transform=list(ds.transform)[:6], nodata=ds.nodata)
    finite = np.isfinite(a)
    dots = (a > 0) & finite
    dcat = ndi.distance_transform_edt(~cat)
    checks = {
        "single_band": meta["count"] == 1,
        "float32": meta["dtype"] == "float32",
        "crs_matches_sample": meta["crs"] == ref["crs"] == GRID["crs"],
        "shape_matches_sample": meta["shape"] == ref["shape"] == GRID["shape"],
        "transform_matches_sample": meta["transform"] == ref["transform"] == GRID["transform"],
        "no_nodata_tag": meta["nodata"] is None,
        "every_cell_finite": bool(finite.all()),
        "no_nan_inside_footprint": bool(finite[fp].all()),
        "values_in_0_1": bool(finite.all() and a.min() >= 0.0 and a.max() <= 1.0),
        "zero_outside_footprint": bool((a[~fp] == 0).all()),
        "zero_dots_on_catalogue": int((dots & cat).sum()) == 0,
    }
    return dict(method="independent rasterio re-read against SHA-pinned sample_submission + existing_faults",
                meta=meta, n_cells=int(a.size), n_nan=int(np.isnan(a).sum()), n_inf=int(np.isinf(a).sum()),
                min=float(a.min()), max=float(a.max()), n_dots=int(dots.sum()),
                unique_values=[float(v) for v in np.unique(a)[:5]],
                min_dot_distance_to_catalogue_px=round(float(dcat[dots].min()), 4),
                checks=checks, all_checks_passed=all(checks.values()))


def zip_check(tif: Path) -> dict:
    z = tif.with_suffix(".zip")
    with zipfile.ZipFile(z) as archive:
        members = archive.infolist()
        ok = len(members) == 1 and members[0].filename == tif.name and archive.read(tif.name) == tif.read_bytes()
    return dict(path=str(z.relative_to(ROOT)), sha256=sha(z), single_member_identical_to_tif=bool(ok))


def main():
    i1 = json.loads((OUT / "holdout-I1.json").read_text())
    i2 = json.loads((OUT / "holdout-I2.json").read_text())
    fin = json.loads((OUT / "final.json").read_text())
    sweep_p = OUT / "sibling-sweep.json"
    sweep = json.loads(sweep_p.read_text()) if sweep_p.exists() else None
    tif = ROOT / fin["tif"]
    v = independent_validation(tif)
    zc = zip_check(tif)
    s1, d1 = i1["pooled"]["scores"], i1["pooled"]["paired_differences"]
    s2, d2 = i2["pooled"]["scores"], i2["pooled"]["paired_differences"]
    reg = fin["registry"]
    canary = i1["leakage_canary"]
    non_blanket_max = reg["dots_max_within_3px_non_blanket"]
    sweep_ok = sweep is not None and sweep["verdict"] == "UNIQUE"
    gates = {
        "G1_I1_E1_minus_E0_ci_lower_gt_0": dict(pass_=d1["E0"]["ci95"][0] > 0, value=d1["E0"]),
        "G2_I1_E1_minus_CTL_HALO_ci_lower_gt_0": dict(pass_=d1["CTL_HALO"]["ci95"][0] > 0, value=d1["CTL_HALO"]),
        "G3_I1_E1_minus_CTL_SUB_delta_gt_0": dict(pass_=d1["CTL_SUB"]["delta"] > 0, value=d1["CTL_SUB"]),
        "G4_I2_E1_noninferior_to_E0_ci_upper_ge_0": dict(pass_=d2["E0"]["ci95"][1] >= 0, value=d2["E0"]),
        "G5_leakage_canary_max_auc_le_0_90": dict(pass_=not canary["stop"], value=canary["worst"]),
        "G6a_uniqueness_protocol_registry": dict(
            pass_=(not fin["surface_precheck"]["stop"]) and (not reg["any_duplicate_chance_corrected"])
                  and non_blanket_max <= 0.70,
            value=dict(scope="preregistered: protocol registry (data/registry + data/fleet_registry + docs/downloads)",
                       n_checked=reg["n_unique_rasters_checked"],
                       surface_max_abs_spearman=reg["surface_max_abs_spearman"],
                       dots_max_within_3px_non_blanket=non_blanket_max,
                       dots_closest_non_blanket=reg["dots_closest_non_blanket"])),
        "G6b_uniqueness_extended_gemsdoe_sweep": dict(
            pass_=sweep_ok,
            value=None if sweep is None else dict(
                scope="added this session (not preregistered): 977 GeoTIFFs from 102 GEMSDOE* repositories",
                verdict=sweep["verdict"], duplicates=sweep["duplicates"],
                n_literal_flags=len(sweep["literal_flags"]),
                max_surface_abs_spearman=(sweep["max_surface_abs_spearman"] or {}).get("surface_abs_spearman"),
                flagged=[dict(raster=r["raster"], n_positive=r["n_positive"], within_3px_literal=r["within_3px_literal"],
                              chance_corrected=r["chance_corrected"], dots_abs_spearman=r.get("dots_abs_spearman"),
                              surface_abs_spearman=r.get("surface_abs_spearman"))
                         for r in sweep["rows"] if r["duplicate"]])),
        "G7_format_independent_revalidation": dict(pass_=v["all_checks_passed"] and zc["single_member_identical_to_tif"],
                                                   value=v["checks"]),
    }
    gates = {k: dict(**{"pass": bool(g["pass_"])}, value=g["value"]) for k, g in gates.items()}
    promote = all(g["pass"] for g in gates.values())
    failed = [k for k, g in gates.items() if not g["pass"]]
    ok_download = v["all_checks_passed"] and zc["single_member_identical_to_tif"]
    blanket_rows = [r for r in reg["comparisons"] if r["blanket_reference"]]
    r0_rows = [r for r in reg["comparisons"] if "h33-2-b2" in r["raster"] or "h33-h33-2-b2" in r["raster"]]
    card = {
        "lane": "ISO91",
        "session": "arena/bacc7c26-gemsdoe91",
        "date": "2026-10-25",
        "preregistration": "docs/HYPOTHESES_ISO91.md (commit e02f8a7, before any experiment)",
        "hypothesis": ("Undiscovered faults are preferentially the short, spatially isolated tail of the fault population, "
                       "so a PU model trained only on isolated catalogue components (no other component within 500 m) "
                       "should recover isolated hidden faults better than the incumbent trained on all faults."),
        "mechanism": ("Domain-matched positive selection: same 38-feature stack, HGB, LOQO, emission and collar as E0; only "
                      "the training positives change (visible components isolated by >5 px)."),
        "non_fault_mimic": ("Isolated linear features of non-tectonic origin: Lake Lahontan shorelines, lithologic contacts, "
                            "incised drainages, flight-line striping in magnetic grids."),
        "result": "positive" if promote else "negative",
        "experiments_run": 3,
        "experiment_list": ["I1 holdout (all arms)", "I2 legacy holdout (E0, E1, RND)", "full-catalogue final build"],
        "slots_used": 0,
        "holdout": {
            "primary": dict(instrument="I1 isolated-whole-components-loqo-v1 (sep 5 px, per-fold hidden set)",
                            evidence_class="HOLDOUT-DTI", evaluator_version=i1["evaluator_version"],
                            withheld_positive_pixels=s1["E1"]["withheld_positive_pixels"],
                            scores={a: dict(dti=round(s1[a]["dti"], 6), ci95=[round(x, 6) for x in s1[a]["ci95"]]) for a in s1},
                            paired_E1_minus={a: dict(delta=round(d1[a]["delta"], 6), ci95=[round(x, 6) for x in d1[a]["ci95"]]) for a in d1}),
            "secondary_legacy": dict(instrument="I2 buffered-whole-components-loqo-v2 (seed 20)",
                                     evidence_class="HOLDOUT-DTI", evaluator_version=i2["evaluator_version"],
                                     withheld_positive_pixels=s2["E1"]["withheld_positive_pixels"],
                                     scores={a: dict(dti=round(s2[a]["dti"], 6), ci95=[round(x, 6) for x in s2[a]["ci95"]]) for a in s2},
                                     paired_E1_minus={a: dict(delta=round(d2[a]["delta"], 6), ci95=[round(x, 6) for x in d2[a]["ci95"]]) for a in d2},
                                     e0_reproduces_recorded_olc91_e0=abs(s2["E0"]["dti"] - 0.08526008331650262) < 1e-12),
            "bootstrap": "paired 20 km spatial-block percentile bootstrap, 1000 draws, seed 520810",
            "not_comparable_with": "leaderboard scores; gems91-hide-recover-v1.0 numbers; the 60,988-positive LOQO instrument",
        },
        "leakage_canary": dict(threshold=0.90, worst=canary["worst"], stop=canary["stop"],
                               n_features=len(canary["features"]), n_truth=canary["n_truth"]),
        "uniqueness": {
            "registry_scope": "protocol registry: data/registry (8 pinned) + data/fleet_registry (62 restored, 60GEMSDOE@02563d07) + docs/downloads",
            "n_unique_rasters_checked": reg["n_unique_rasters_checked"],
            "byte_duplicates_skipped": len(reg["byte_duplicates_skipped"]),
            "surface_before_placement_max_abs_spearman": reg["surface_max_abs_spearman"],
            "surface_closest": reg["surface_closest"],
            "dots_max_abs_spearman": max((r["dots_abs_spearman"] or 0) for r in reg["comparisons"]),
            "dots_max_within_3px_non_blanket": non_blanket_max,
            "dots_closest_non_blanket": reg["dots_closest_non_blanket"],
            "blanket_references": [dict(raster=r["raster"], literal=r["dots_within_3px_literal"],
                                        chance=r["chance_within_3px"], chance_corrected=r["dots_within_3px_chance_corrected"],
                                        coverage=r["reference_3px_footprint_coverage"]) for r in blanket_rows],
            "vs_R0_gemsdoe32_h33_2_b2": dict(within_3px=r0_rows[0]["dots_within_3px_literal"],
                                             surface_abs_spearman=r0_rows[0]["surface_abs_spearman"]) if r0_rows else None,
            "any_duplicate_literal": reg["any_duplicate_literal"],
            "any_duplicate_chance_corrected": reg["any_duplicate_chance_corrected"],
            "sibling_sweep": None if sweep is None else dict(
                scope=sweep["scope"], rule=sweep["rule"], n_compared=sweep["n_compared"], n_skipped=sweep["n_skipped"],
                n_dense=sweep["n_dense"], n_blanket=sweep["n_blanket"],
                literal_verdict=sweep["literal_verdict"], n_literal_flags=len(sweep["literal_flags"]),
                verdict=sweep["verdict"], duplicates=sweep["duplicates"],
                max_literal_sparse=sweep["max_literal_sparse"],
                max_matched_budget_dense=sweep["max_matched_budget_dense"],
                max_dots_abs_spearman=sweep["max_dots_abs_spearman"],
                max_surface_abs_spearman=sweep["max_surface_abs_spearman"],
                evidence=["docs/iso91/sibling-sweep.json", "docs/iso91/sibling-sweep-literal-v1.json"]),
            "evidence": ["docs/iso91/final.json", "docs/iso91/surface-precheck.json"],
        },
        "uniqueness_summary": (
            "Protocol registry (preregistered G6a): " + ("PASS" if gates["G6a_uniqueness_protocol_registry"]["pass"] else "FAIL")
            + f" over {reg['n_unique_rasters_checked']} rasters (surface rho max {reg['surface_max_abs_spearman']}, "
            + f"non-blanket overlap max {100 * non_blanket_max:.1f}%). Extended GEMSDOE sweep (G6b): "
            + ("no duplicate" if sweep_ok else
               "; ".join(f"{Path(r['raster']).name}: {100 * r['within_3px_literal']:.1f}% of dots within 3 px "
                         f"(chance-corrected {100 * r['chance_corrected']:.1f}%, dots rho {r.get('dots_abs_spearman')})"
                         for r in (sweep or {}).get("rows", []) if r["duplicate"]) + " - literal duplicate flag, logged")),
        "sgmc_control_report_only": fin["sgmc_control_report_only"],
        "raster": dict(path=fin["tif"], sha256=sha(tif), bytes=tif.stat().st_size, n_dots=v["n_dots"],
                       zip=zc["path"], zip_sha256=zc["sha256"], receipt=fin["tif"].replace(".tif", ".json"),
                       encoding="zeros outside footprint, all-finite, no nodata tag"),
        "raster_path": fin["tif"],
        "raster_sha256": sha(tif),
        "validator": dict(template=fin["receipt"]["validator"]["checks"],
                          template_all_checks_passed=fin["receipt"]["validator"]["all_checks_passed"],
                          independent=v, zip=zc, all_checks_passed=bool(ok_download)),
        "submission_name": fin["name"],
        "submission_note": fin["note"],
        "submission_note_chars": len(fin["note"]),
        "gates": gates,
        "verdict": {
            "promote": promote,
            "OK_TO_DOWNLOAD": "YES — format-valid research file" if ok_download else "NO",
            "OK_TO_SUBMIT": "YES" if promote else "NO",
            "failed_gates": failed,
            "reasons": ([] if promote else
                        [f"{k} failed" for k in failed] +
                        ["Do not spend a weekly slot: ISO91 did not beat the incumbent on the preregistered holdout."]),
        },
        "ok_to_submit": bool(promote),
        "submission_ready": bool(promote),
        "organizer_confirmed_scores": None,
        "user_reported_context": {
            "R0_gemsdoe32_h33_2_b2": "0.2778 USER-REPORTED (owner page: no organiser score exists)",
            "public_leaderboard_rank1": "0.4413 PUBLIC-LEADERBOARD (xiaofanhu, read 2026-10-25)",
            "user_quoted_0_3195": "0.3195 USER-QUOTED; on 2026-10-04 it was #2 (DARD) on the public board",
        },
    }
    CARD.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(dict(card=str(CARD.relative_to(ROOT)), promote=promote, failed=failed,
                          OK_TO_DOWNLOAD=card["verdict"]["OK_TO_DOWNLOAD"], OK_TO_SUBMIT=card["verdict"]["OK_TO_SUBMIT"]),
                     indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
