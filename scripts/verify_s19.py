#!/usr/bin/env python3
"""Re-verify Session 19 (`S19-SVHF`) published bytes and measured evidence; no scientific rerun.

Exit zero means the S19-SVHF research deliverable is internally consistent,
byte-verified by two independent TIFF decoders (`tifffile` + `rasterio`), and
auditable. It NEVER means permission to upload to DrivenData: `ok_to_submit` is
read separately and remains `False`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
import tifffile
from scipy.ndimage import distance_transform_edt as edt
from scipy.spatial import cKDTree

from gems91.readiness import gates, submission_ready
from scripts.verify_current_artifact import published_path
from vendor.gems57 import evaluate_holdout as ev
from scripts.source_integrity import verify_historical_source


def read_json(relative: str):
    return json.loads((ROOT / relative).read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(with_data: bool = False) -> dict:
    card = read_json("docs/run-card-S19-SVHF.json")
    a = card["artifact"]
    tif = published_path(a["file"])
    zipped = published_path(a["zip"])
    receipt = read_json("docs/s19_svhf/writer-receipt.json")

    require(sha(tif) == card["raster_sha256"] == receipt["sha256"], "TIFF SHA-256 mismatch")
    require(sha(zipped) == a["zip_sha256"] == receipt["zip_sha256"], "ZIP SHA-256 mismatch")
    require(tif.stat().st_size == a["bytes"] == receipt["bytes"], "TIFF byte count mismatch")
    require(zipped.stat().st_size == a["zip_bytes"], "ZIP byte count mismatch")

    with zipfile.ZipFile(zipped) as zf:
        require(zf.namelist() == [tif.name], "ZIP must contain exactly one root-level GeoTIFF")
        require(zf.read(tif.name) == tif.read_bytes(), "ZIP GeoTIFF bytes differ from standalone GeoTIFF")

    require(card["submission_name"] == receipt["submission_name"], "submission_name drift")
    require(card["note"] == receipt["note"] and 0 < len(card["note"]) <= 140, "note drift or >140 chars")
    require(0 < len(card["submission_name"]) <= 140, "submission_name length invalid")

    # Independent TIFF decoder #1 (tifffile) + #2 (rasterio)
    arr = tifffile.imread(tif)
    require(arr.shape == (3730, 3292) and arr.dtype == np.float32, "TIFF array shape/dtype mismatch")
    require(bool(np.isfinite(arr).all()), "Non-finite NaN/Inf cell in GeoTIFF")
    require(float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0, "Values outside [0, 1]")
    require(bool(np.isin(arr, [0.0, 1.0]).all()), "S19-SVHF binary dot artifact must contain only {0.0, 1.0}")
    require(int((arr > 0).sum()) == card["validator_output"]["positive_pixels"] == 37654, "Positive dot count mismatch")
    require(
        hashlib.sha256(arr.astype(np.uint8).tobytes()).hexdigest() == card["raster_pixel_sha256"],
        "Pixel SHA-256 mismatch",
    )

    with rasterio.open(tif) as s:
        require(s.count == 1 and s.dtypes == ("float32",) and str(s.crs) == "EPSG:32611", "Band/dtype/CRS mismatch")
        require(tuple(s.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0), "Affine transform mismatch")
        require(s.nodata is None, "GeoTIFF must not carry a sentinel nodata tag")
        require(np.array_equal(s.read(1), arr), "rasterio vs tifffile pixel decode mismatch")
        actual_meta = (s.count, s.shape, s.crs, s.transform)

    pts = np.argwhere(arr > 0)
    min_dist = float(cKDTree(pts).query(pts, k=2)[0][:, 1].min())
    require(min_dist > 3.0 and round(min_dist, 5) == card["validator_output"]["min_spacing_px"], "Dot spacing mismatch")

    if with_data:
        pin_rows = {r["id"]: r for r in read_json("registry/data_manifest.json")["files"]}
        for key in ("sample_submission", "existing_faults"):
            path = ROOT / "data" / pin_rows[key]["local_subpath"]
            require(sha(path) == card["inputs"][key]["sha256"], f"{key} SHA-256 mismatch vs pinned input")
        with rasterio.open(ROOT / "data" / pin_rows["sample_submission"]["local_subpath"]) as s:
            require((s.count, s.shape, s.crs, s.transform) == actual_meta, "Template grid mismatch")
            fp = np.isfinite(s.read(1))
        with rasterio.open(ROOT / "data" / pin_rows["existing_faults"]["local_subpath"]) as s:
            require((s.count, s.shape, s.crs, s.transform) == actual_meta, "Catalogue grid mismatch")
            cat = (s.read(1) > 0) & fp
        require(bool((arr[~fp] == 0.0).all()) and bool((arr[cat] == 0.0).all()), "Footprint/catalogue zero-masking violated")
        d_cat = float(edt(~cat)[arr > 0].min())
        require(d_cat > 3.0 and round(d_cat, 5) == card["validator_output"]["min_catalogue_distance_px"], "Catalogue collar <= 3 px")

    # Preregistration & feature provenance checks
    prereg = card["preregistration"]
    require(sha(ROOT / prereg["path"]) == prereg["sha256"], "Preregistration modified after experiment")
    feat = read_json("docs/s19_svhf/features.json")
    require(feat["svhf_code_sha256"] == sha(ROOT / "src/gems91/svhf19.py"), "svhf19.py modified after experiment")
    require(feat["stage1_full_feature_count"] == 58 and feat["stage1_pure_subsurface_feature_count"] == 42, "Stage-1 feature counts drifted")
    require(feat["stage2_qdac_feature_count"] == 14, "Stage-2 QDAC feature count drifted")
    require(feat["verified_subsurface_b12_b19_max_diff"] == 0.0, "Subsurface features leaked Band 12 / Band 19")
    require("dist_known_fault_px" in feat["svhf_meta"]["gdr_stats"]["banned_columns_excluded"], "dist_known_fault_px must be banned")
    require(
        not any("dist_known_fault" in f or "cat_dist" in f for f in feat["stage1_full_features"] + feat["stage2_qdac_features"]),
        "Catalogue distance leaked into feature stack",
    )

    # Holdout arithmetic, fold sums, & implementation SHA-256 verification
    holdout = read_json("docs/s19_svhf/holdout.json")
    summary_all = holdout["summary_all_arms"]
    for fname, expected_sha in summary_all["implementation_sha256"].items():
        verify_historical_source(ROOT, f"vendor/gems57/{fname}", expected_sha)

    h = card["holdout_dti"]
    win_res = summary_all["scores"][h["winning_arm"]]
    require(h["label"] == "HOLDOUT-DTI" and h["evaluator_version"] == ev.VERSION, "Metric label/version drift")
    require(h["value"] == win_res["dti"] and h["ci95"] == win_res["ci95"], "Winning HOLDOUT-DTI or CI95 drift")
    require(h["withheld_positives"] == win_res["withheld_positive_pixels"] == 60988, "Withheld positive count drift")
    require(h["split_sha256"] == holdout["split_sha256"], "Holdout split SHA-256 drift")
    require(h["paired_best"] == summary_all["paired_differences"]["incumbent_ptac_v2"], "Paired best CI95/delta drift")

    for name in ("svhf_e1", "svhf_e2", "svhf_e3"):
        sc = summary_all["scores"][name]
        exact_dti = sc["tpw"] / (sc["tpw"] + 0.2 * sc["fpw"] + 0.8 * sc["fnw"])
        require(bool(np.isclose(exact_dti, sc["dti"], rtol=1e-12)), f"Pooled Tversky DTI formula drift for {name}")
        require(sc["ci95"][0] < sc["dti"] < sc["ci95"][1], f"Bootstrap CI95 does not bracket point DTI for {name}")
        for key in ("tpw", "fpw", "fnw"):
            require(
                bool(np.isclose(sum(f["arms"][name][key] for f in holdout["folds"]), sc[key], rtol=1e-12)),
                f"Fold {key} sum mismatch for {name}",
            )
    for fold in holdout["folds"]:
        r = fold["receipt"]
        require(r["evaluation_region_label_blind"] and r["shared_train_truth_components"] == 0, "Unsafe fold receipt")
        require(r["buffer_px"] == 80 and r["nearest_training_to_region_px"] > 80, "80-px training buffer violated")

    # Rule 4 single-feature leakage canaries
    canary = read_json("docs/s19_svhf/canaries.json")
    fvals = list(canary["features"].values())
    require(len(fvals) == card["canaries"]["features_tested"] == 72, "Canary feature count mismatch")
    require(all(len(c["quadrant_symmetric_aucs"]) == 4 for c in fvals), "Missing 4-quadrant canary AUCs")
    require(
        all(
            c["status"] == "PASS"
            and 0.5 <= c["symmetric_auc"] <= 0.90
            and all(0.5 <= q <= 0.90 for q in c["quadrant_symmetric_aucs"])
            for c in fvals
        ),
        "Failed or out-of-range canary",
    )
    require(round(max(c["symmetric_auc"] for c in fvals), 6) == card["canaries"]["max_symmetric_auc"], "Canary max AUC drift")
    require(
        round(max(max(c["quadrant_symmetric_aucs"]) for c in fvals), 6) == card["canaries"]["max_quadrant_symmetric_auc"],
        "Canary max quadrant AUC drift",
    )

    # Rule 1 registry checks against 100-raster inventory
    inventory = read_json("registry/s19_comparison_inventory.json")
    require(len(inventory["files"]) == 100, "S19 comparison inventory count mismatch")
    for phase, filename in (("preplacement", "surface"), ("final", "final")):
        report = read_json(f"docs/s19_svhf/registry-{filename}.json")
        require(report["checked"] == len(report["comparisons"]) == 100, f"Registry {phase} count drift")
        require(report["not_checked_after_stop"] == 0, f"Registry {phase} must evaluate all 100 rasters without skipping")
        for expected, measured in zip(inventory["files"], report["comparisons"]):
            require(
                expected["path"] == measured["file"] and expected["sha256"] == measured["sha256"],
                f"Registry {phase} file/hash order drift",
            )
    fin = read_json("docs/s19_svhf/registry-final.json")
    require(fin["competitive_le_80k_pass_count"] == fin["competitive_le_80k_count"] == 90, "Competitive <=80k PASS count drift")
    require(fin["max_competitive_le_80k_3px_overlap"] <= 0.70, "Competitive <=80k overlap > 0.70")

    # Policy registration & fail-closed readiness checks
    policy = {r["path"]: r for r in read_json("registry/artifact_policy.json")["files"]}
    for rel, digest in ((f"docs/{a['file']}", card["raster_sha256"]), (f"docs/{a['zip']}", a["zip_sha256"])):
        require(rel in policy and policy[rel]["sha256"] == digest, f"Missing/mismatched artifact_policy entry: {rel}")
        require(policy[rel]["status"] == "current_research_only", f"Unexpected artifact_policy status: {rel}")

    computed_gates = gates(card)
    require({k: v for k, v in computed_gates.items() if k != "buffered_context"} == card["automated_gates"],
            "historical automated_gates drift vs readiness.gates(card)")
    require(computed_gates["buffered_context"] is False, "Historical v2 context cannot satisfy corrected gate")
    require(computed_gates["format"] is True and computed_gates["canary"] is True, "Format or canary gate False")
    require(card["ok_to_download"] is True, "ok_to_download must be True for format-valid research artifact")
    require(submission_ready(card) is False and card["ok_to_submit"] is False and card["submission_ready"] is False, "Must remain fail-closed False")
    require(card["verdict"] == "negative" and card["organizer_confirmed"] is None, "Verdict/organizer_confirmed violation")

    return {
        "status": "PASS",
        "scope": "S19-SVHF research artifact & evidence verification only; NOT submission approval",
        "with_data": with_data,
        "winning_arm": h["winning_arm"],
        "holdout_dti": h["value"],
        "ci95": h["ci95"],
        "competitive_le_80k_pass": f"{fin['competitive_le_80k_pass_count']}/{fin['competitive_le_80k_count']}",
        "max_competitive_3px_overlap": fin["max_competitive_le_80k_3px_overlap"],
        "raster_sha256": card["raster_sha256"],
        "zip_sha256": a["zip_sha256"],
        "ok_to_download": card["ok_to_download"],
        "ok_to_submit": card["ok_to_submit"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--with-data", action="store_true", help="Also verify against restored official GeoTIFF grids")
    args = ap.parse_args()
    res = verify(with_data=args.with_data)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
