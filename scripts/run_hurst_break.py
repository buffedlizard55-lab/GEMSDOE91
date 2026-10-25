#!/usr/bin/env python3
"""Run the one preregistered Hurst-break experiment; never submits or uploads.

Uses the pinned GeoDAWN feature TIFF, shared fold generator/evaluator, shared
registry gate, and shared fail-closed submission writer. The writer is called
only if the recorded holdout and registry evidence allow a research artifact.
"""
from __future__ import annotations

import gc
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio

from gems91 import ced, hurst_break
from gems91.io import dot_digest, sha256_file
from run_ced import dump, registry_phase, verify_inputs
from vendor.gems57 import evaluate_holdout as evaluator, spatial
from vendor.gems57.submission_writer import write_submission

SAMPLE = ROOT / "data/official/sample_submission.tif"
CATALOGUE = ROOT / "data/official/existing_faults.tif"
STACK = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
PREREG = ROOT / "docs/HYPOTHESES_05C6D613.md"
INVENTORY = ROOT / "registry/s17_comparison_inventory.json"
CACHE_ROOT = ROOT / "data/hurst-break-cache"
LOCK = ROOT / "docs/hurst-break-experiment.json"
CARD_PATH = ROOT / "docs/run-card-Hurst-Break.json"
CANARIES_PATH = ROOT / "docs/hurst-break-canaries.json"
SURFACE_REGISTRY_PATH = ROOT / "docs/hurst-break-registry-surface.json"
HOLDOUT_PATH = ROOT / "docs/hurst-break-holdout.json"
FINAL_REGISTRY_PATH = ROOT / "docs/hurst-break-registry-final.json"
DOT_BUDGET = 37_654
DOT_RADIUS_PX = 3.0
BUFFER_PX = 80
BLOCK_SIDE_PX = 200
BOOTSTRAP_DRAWS = 1_000
BOOTSTRAP_SEED = 520_819
SUBMISSION_NAME = "GEMSDOE91-HURST-BREAK-R1"
NOTE = "Hurst-like B12 terrain-texture break; research only, not approved for a slot."


def verify_grid_and_read():
    inputs = verify_inputs()
    with rasterio.open(SAMPLE) as sample:
        fp = np.isfinite(sample.read(1))
        shape = sample.shape
        sample_meta = (sample.count, sample.shape, sample.crs, sample.transform)
    with rasterio.open(CATALOGUE) as cat_src:
        if (cat_src.count, cat_src.shape, cat_src.crs, cat_src.transform) != sample_meta:
            raise ValueError("catalogue grid differs from pinned submission grid")
        catalogue = (cat_src.read(1) > 0) & fp
    with rasterio.open(STACK) as src:
        if (src.shape, src.crs, src.transform) != (sample_meta[1], sample_meta[2], sample_meta[3]):
            raise ValueError("cached GeoDAWN feature stack does not match submission grid")
        if not (src.descriptions[11] or "").startswith("det_elev "):
            raise ValueError(f"B12 is not the pinned det_elev layer: {src.descriptions[11]!r}")
        if not (src.descriptions[18] or "").startswith("det_elev_slope "):
            raise ValueError(f"B19 is not the pinned det_elev_slope layer: {src.descriptions[18]!r}")
        elev = src.read(12)
        slope = src.read(19)
        layer_receipt = {
            "stack_sha256": inputs["training_features"]["sha256"],
            "band12": {"index": 12, "description": src.descriptions[11]},
            "band19": {"index": 19, "description": src.descriptions[18]},
            "usable_b12_pixels": int((fp & np.isfinite(elev) & (elev > -1e30)).sum()),
            "usable_b19_pixels": int((fp & np.isfinite(slope) & (slope > -1e30)).sum()),
        }
    if not catalogue.any() or int(catalogue.sum()) != 60_988:
        raise ValueError(f"unexpected pinned catalogue support: {int(catalogue.sum())}")
    if not np.isfinite(elev[fp]).all() or not np.isfinite(slope[fp]).all():
        raise ValueError("nonfinite B12/B19 values inside valid footprint")
    return inputs, fp, catalogue, elev, slope, sample_meta, shape, layer_receipt


def feature_cache(elev, slope, fp, inputs, layer_receipt):
    module_sha = sha256_file(ROOT / "src/gems91/hurst_break.py")
    cache_key = hashlib.sha256(json.dumps({
        "version": hurst_break.VERSION,
        "inputs": inputs,
        "layers": layer_receipt,
        "module_sha256": module_sha,
        "constants": {
            "lags_px": hurst_break.LAGS_PX,
            "window_px": hurst_break.WINDOW_PX,
            "edge_buffer_px": hurst_break.EDGE_BUFFER_PX,
            "gradient_sigma_px": hurst_break.HURST_GRAD_SIGMA_PX,
            "min_local_pair_fraction": hurst_break.MIN_LOCAL_PAIR_FRACTION,
        },
    }, sort_keys=True).encode()).hexdigest()
    directory = CACHE_ROOT / cache_key[:16]
    receipt_path = directory / "cache.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text())
        if receipt.get("cache_key") != cache_key:
            raise ValueError("Hurst feature cache key mismatch")
        arrays = {}
        for name, expected in receipt["files"].items():
            path = directory / f"{name}.npy"
            if sha256_file(path) != expected:
                raise ValueError(f"Hurst feature cache checksum mismatch: {name}")
            arrays[name] = np.load(path, mmap_mode="r", allow_pickle=False)
        return arrays, receipt

    print("Computing preregistered B12 local semivariograms (label-blind).", flush=True)
    arrays = hurst_break.features(elev, slope, fp)
    directory.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, value in arrays.items():
        path = directory / f"{name}.npy"
        np.save(path, value, allow_pickle=False)
        files[name] = sha256_file(path)
    receipt = {
        "version": hurst_break.VERSION,
        "cache_key": cache_key,
        "module_sha256": module_sha,
        "inputs": inputs,
        "layers": layer_receipt,
        "fixed_parameters": {
            "lags_px": list(hurst_break.LAGS_PX),
            "window_px": hurst_break.WINDOW_PX,
            "edge_buffer_px": hurst_break.EDGE_BUFFER_PX,
            "gradient_sigma_px": hurst_break.HURST_GRAD_SIGMA_PX,
            "min_local_pair_fraction": hurst_break.MIN_LOCAL_PAIR_FRACTION,
            "directions": [[0, lag] for lag in hurst_break.LAGS_PX]
            + [[lag, 0] for lag in hurst_break.LAGS_PX],
            "effective_hurst_definition": "0.5 * OLS slope of log(local mean squared increment) vs log(lag)",
            "candidate_surface": "average-rank percentile of Gaussian-gradient magnitude of effective Hurst-like exponent",
            "candidate_valid_pixels": int((arrays["surface"] > 0).sum()),
        },
        "files": files,
    }
    dump(receipt_path, receipt)
    del arrays
    gc.collect()
    arrays = {
        name: np.load(directory / f"{name}.npy", mmap_mode="r", allow_pickle=False)
        for name in files
    }
    return arrays, receipt


def _write_card(card):
    dump(CARD_PATH, card)


def stop(card, reason, *, verdict="negative"):
    card.update(
        verdict=verdict,
        verdict_reason=reason,
        submission_ready=False,
        completed_utc=datetime.now(timezone.utc).isoformat(),
        download_status={
            "ok_to_download_new_candidate": False,
            "reason": "No new TIFF was written; do not download or describe a non-unique raster as unique.",
        },
        submission_status={
            "ok_to_submit": False,
            "reason": reason,
            "slots_used": 0,
            "selector_approval": False,
            "organizer_confirmed": False,
        },
    )
    _write_card(card)
    print(reason, flush=True)
    return card


def run():
    if LOCK.exists():
        raise FileExistsError(
            f"This preregistered run is already recorded ({LOCK.relative_to(ROOT)}); do not rerun."
        )
    if not PREREG.is_file():
        raise FileNotFoundError(f"missing frozen preregistration: {PREREG}")
    if not INVENTORY.is_file():
        raise FileNotFoundError(f"missing pinned S17 inventory: {INVENTORY}")

    started = datetime.now(timezone.utc).isoformat()
    lock = {
        "run_id": "HURST-BREAK-v1-20261025",
        "status": "STARTED",
        "started_utc": started,
        "preregistration_sha256": sha256_file(PREREG),
        "experiment_count": 1,
        "max_experiments": 3,
        "max_elapsed_seconds": 7_200,
    }
    dump(LOCK, lock)

    inputs, fp, catalogue, elev, slope, sample_meta, shape, layer_receipt = verify_grid_and_read()
    inventory = json.loads(INVENTORY.read_text())
    baseline = json.loads((ROOT / "docs/s17/holdout.json").read_text())
    best = baseline["summary_all_arms"]["scores"]["cpad_e1"]
    card = {
        "schema": "gems91.run-card.v3",
        "run_id": lock["run_id"],
        "started_utc": started,
        "hypothesis": "Local effective Hurst-like texture-scaling breaks in GeoDAWN B12 may mark scarp-diffusion or cover transitions associated with unmapped faults.",
        "mechanism": "11x11-pixel local structure functions at 100/200/400 m; half the OLS log-semivariogram/log-lag slope; score the local Gaussian-gradient magnitude of that exponent.",
        "non_fault_mimic": "Lithologic/soil boundary, alluvial-fan or playa margin, drainage texture change, vegetation/land-use edge.",
        "novelty_vs_repo": "No Hurst/semivariogram implementation or result found in src/gems91 or scripts. Related Hurst/spectral-slope idea was already proposed in S18/FFB review; H11 structure-tensor coherence also uses B12. This is not a wholly new written proposal or a new sensor.",
        "lane": {
            "name": "Hurst-like terrain-texture scaling",
            "assigned": False,
            "status": "RESEARCH_ONLY_UNASSIGNED",
            "reason": "One B12-only hypothesis tested; no competition lane or slot was assigned by this review.",
        },
        "budget": {
            "experiments_run": 1,
            "max_experiments": 3,
            "max_seconds": 7_200,
            "dot_budget": DOT_BUDGET,
            "dot_radius_px": DOT_RADIUS_PX,
            "fold_buffer_px": BUFFER_PX,
        },
        "inputs": inputs,
        "feature_receipt": {
            "cache_key": None,
            "cache_files": None,
            "code_sha256": sha256_file(ROOT / "src/gems91/hurst_break.py"),
            "layers": layer_receipt,
            "fixed_parameters": {
                "lags_px": list(hurst_break.LAGS_PX),
                "window_px": hurst_break.WINDOW_PX,
                "edge_buffer_px": hurst_break.EDGE_BUFFER_PX,
                "gradient_sigma_px": hurst_break.HURST_GRAD_SIGMA_PX,
                "min_local_pair_fraction": hurst_break.MIN_LOCAL_PAIR_FRACTION,
            },
        },
        "canaries": {"status": "NOT_RUN", "file": str(CANARIES_PATH.relative_to(ROOT))},
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "status": "NOT_RUN",
            "evaluator_version": evaluator.VERSION,
            "alpha": 0.2,
            "beta": 0.8,
            "triangular_radius_m": 300.0,
            "withheld_positives": None,
            "value": None,
            "ci95": None,
            "file": str(HOLDOUT_PATH.relative_to(ROOT)),
        },
        "comparable_prior_best": {
            "evidence_class": "HOLDOUT-DTI",
            "arm": "cpad_e1",
            "value": best["dti"],
            "ci95": best["ci95"],
            "withheld_positives": best["withheld_positive_pixels"],
            "evaluator_version": best["evaluator_version"],
            "source": "docs/s17/holdout.json#summary_all_arms.scores.cpad_e1",
            "paired_ci_available": False,
        },
        "registry_comparison": {
            "scope": "S17 index has 95 paths across the 62-file fleet snapshot, three retracted-geology paths, and pre-S17 downloads. At HURST-BREAK run time, the three retracted TIFFs were absent locally, so only 92/95 paths had comparable surfaces.",
            "source_scope_claim": inventory["scope"],
            "pinned_inventory_counts": inventory.get("counts"),
            "inventory_missing_files_field_at_freeze": inventory.get("missing_files_on_disk", []),
            "inventory_scope_reconciliation": "The pinned inventory scope text says all three retracted rasters were restored and its missing-files field is empty, but the run-time surface check found the three indexed paths absent. This run records the observed UNVERIFIED state.",
            "indexed_rasters": len(inventory["files"]),
            "complete_universal_registry": inventory.get("complete_universal_registry", False),
            "missing_files_on_disk_in_checked_index": None,
            "missing_scope": inventory.get("missing_scope", []),
            "thresholds": {
                "positive_surface_rank_correlation_strictly_greater_than": 0.90,
                "final_dot_overlap_within_px": DOT_RADIUS_PX,
                "final_dot_overlap_strictly_greater_than": 0.70,
            },
            "preplacement": {"status": "NOT_RUN", "file": str(SURFACE_REGISTRY_PATH.relative_to(ROOT))},
            "final_dots": {"status": "NOT_RUN", "file": str(FINAL_REGISTRY_PATH.relative_to(ROOT))},
            "scope_caveat": "S17 inventory is frozen and useful but not universal; three retracted TIFFs are absent locally. No uniqueness claim is allowed from this index alone.",
        },
        "final_dot_mask_sha256": None,
        "raster_sha256": None,
        "raster_written": False,
        "validator_output": {"status": "NOT_RUN_NO_RASTER"},
        "submission": {
            "name_proposed_not_used": SUBMISSION_NAME,
            "note": NOTE,
            "note_chars": len(NOTE),
            "selected_for_slot": False,
            "slot_count": 0,
        },
        "download_status": {"ok_to_download_new_candidate": False, "reason": "Run not yet evaluated."},
        "submission_status": {"ok_to_submit": False, "slots_used": 0, "selector_approval": False, "organizer_confirmed": False},
        "verdict": "negative",
        "verdict_reason": "Run not yet evaluated.",
        "organizer_confirmed": None,
        "slots_used": 0,
        "selector_approval": False,
    }
    _write_card(card)

    fields, feature_receipt = feature_cache(elev, slope, fp, inputs, layer_receipt)
    del elev, slope
    gc.collect()
    card["feature_receipt"].update(
        cache_key=feature_receipt["cache_key"],
        cache_files=feature_receipt["files"],
        candidate_valid_pixels=feature_receipt["fixed_parameters"]["candidate_valid_pixels"],
        cache_path=str((CACHE_ROOT / feature_receipt["cache_key"][:16]).relative_to(ROOT)),
    )

    canary_features = {}
    catalogue_positive_pixels = int(catalogue.sum())
    for name, value in fields.items():
        result = ced.auc_canary(value, catalogue, fp)
        # The shared helper's legacy metadata calls these catalogue positives
        # "withheld" and labels its AUC as HOLDOUT-DTI. Correct that report
        # vocabulary without changing the underlying statistic or result.
        result.pop("evidence_class", None)
        result.pop("withheld_positive_pixels", None)
        result["evidence_class"] = "LEAKAGE-CANARY-AUC"
        result["catalogue_positive_pixels"] = catalogue_positive_pixels
        canary_features[name] = result
    max_auc = max(r["symmetric_auc"] for r in canary_features.values())
    canary_report = {
        "evidence_class": "LEAKAGE-CANARY-AUC",
        "statistic": "maximum symmetric feature-alone AUROC (not DTI)",
        "implementation": "gems91.ced.auc_canary exact empirical AUROC",
        "split": "label-blind feature fields evaluated on catalogue positives vs catalogue-zero proxies",
        "catalogue_positive_pixels": catalogue_positive_pixels,
        "features": canary_features,
        "max_symmetric_auc": max_auc,
        "threshold": 0.90,
        "interpretation": "AUC >0.90 is treated as leakage until disproven; catalogue-zero pixels are proxies, not verified absences; passing is not proof of independence.",
    }
    dump(CANARIES_PATH, canary_report)
    card["canaries"] = {
        "status": "LEAKAGE_SUSPECTED" if max_auc > 0.90 else "PASS",
        "evidence_class": "LEAKAGE-CANARY-AUC",
        "statistic": "LEAKAGE-CANARY-AUC (not DTI)",
        "max_symmetric_auc": max_auc,
        "catalogue_positive_pixels": catalogue_positive_pixels,
        "threshold": 0.90,
        "file": str(CANARIES_PATH.relative_to(ROOT)),
    }
    if max_auc > 0.90:
        lock.update(status="STOPPED_LEAKAGE_CANARY", completed_utc=datetime.now(timezone.utc).isoformat())
        dump(LOCK, lock)
        return stop(card, "An individual-feature leakage canary exceeded 0.90; stopped before registry checks or placement.")

    pre = registry_phase(fields["surface"], fp, inventory, sample_meta)
    dump(SURFACE_REGISTRY_PATH, pre)
    pre_rows = pre.get("comparisons", [])
    pre_unverified = [row for row in pre_rows if row.get("status") == "UNVERIFIED"]
    card["registry_comparison"]["missing_files_on_disk_in_checked_index"] = len(pre_unverified)
    card["registry_comparison"]["inventory_rasters_missing_from_disk"] = len(pre_unverified)
    card["registry_comparison"]["unverified_paths_in_checked_index"] = [row.get("file") for row in pre_unverified]
    pre_rhos = [
        row["surface"]["rank_correlation"]
        for row in pre_rows
        if row.get("surface", {}).get("rank_correlation") is not None
    ]
    card["registry_comparison"]["preplacement"] = {
        "status": pre["status"],
        "checked": pre.get("checked"),
        "checked_semantics": "indexed entries attempted, including UNVERIFIED rows for missing TIFFs",
        "comparable_rasters": len(pre_rows) - len(pre_unverified),
        "unverified_rasters": len(pre_unverified),
        "not_checked_after_stop": pre.get("not_checked_after_stop"),
        "max_positive_rank_correlation": max(pre_rhos) if pre_rhos else None,
        "closest_raster": max(
            (row for row in pre_rows if row.get("surface", {}).get("rank_correlation") is not None),
            key=lambda row: row["surface"]["rank_correlation"],
            default=None,
        ),
        "file": str(SURFACE_REGISTRY_PATH.relative_to(ROOT)),
    }
    if pre["status"] == "DUPLICATE":
        lock.update(status="STOPPED_PREPLACEMENT_DUPLICATE", completed_utc=datetime.now(timezone.utc).isoformat())
        dump(LOCK, lock)
        return stop(card, "Continuous candidate surface exceeded the registry correlation threshold; stopped before any dot placement.")

    nrows = math.ceil(shape[0] / BLOCK_SIDE_PX)
    ncols = math.ceil(shape[1] / BLOCK_SIDE_PX)
    nblocks = nrows * ncols
    arms = ("hurst_break", "gradient_control", "random_null")
    terms = {arm: np.zeros((nblocks, 4), dtype=np.float64) for arm in arms}
    fold_receipts = []
    total_withheld = 0

    for fold_index, fold in enumerate(spatial.folds(catalogue, fp, buffer_px=BUFFER_PX)):
        ys, xs = np.nonzero(fold["region"])
        if not len(ys):
            raise ValueError(f"empty label-blind holdout region in fold {fold['fold']}")
        sl = (
            slice(int(ys.min()), int(ys.max()) + 1),
            slice(int(xs.min()), int(xs.max()) + 1),
        )
        budget = int(round(DOT_BUDGET * int(fold["region"].sum()) / int(fp.sum())))
        small = {key: fold[key][sl] for key in ("region", "visible", "truth")}
        # Pixel-exact visible-catalogue masking; hidden components remain eligible.
        eligible = small["region"] & ~small["visible"]
        random_surface = np.random.default_rng(BOOTSTRAP_SEED + fold_index).random(eligible.shape)
        surfaces = {
            "hurst_break": fields["surface"][sl],
            "gradient_control": fields["gradient_control_b19"][sl],
            "random_null": random_surface,
        }
        result = {"fold": fold["receipt"], "budget": budget, "arms": {}}
        for arm in arms:
            dots = ced.place(surfaces[arm], eligible, budget, radius=DOT_RADIUS_PX)
            score, block_terms = evaluator.evaluate(
                dots.astype(np.float32),
                small,
                fp[sl],
                origin=(sl[0].start, sl[1].start),
                global_shape=shape,
            )
            terms[arm] += block_terms
            result["arms"][arm] = score
            del dots, block_terms
        total_withheld += int(fold["truth"].sum())
        fold_receipts.append(result)
        print(
            f"Completed fixed-quadrant whole-component fold {fold['fold']} "
            f"({int(fold['truth'].sum())} withheld positives).",
            flush=True,
        )
        del surfaces, random_surface, small, eligible
        gc.collect()

    if total_withheld != 60_988:
        raise ValueError(f"unexpected pooled withheld-positive count: {total_withheld}")
    summary = evaluator.pooled_summary(
        terms,
        draws=BOOTSTRAP_DRAWS,
        seed=BOOTSTRAP_SEED,
        candidate="hurst_break",
    )
    holdout = {
        "summary": summary,
        "folds": fold_receipts,
        "scope": "Known-catalogue hide-and-recover over label-blind quadrants; this is not the hidden competition fault set.",
        "fold_protocol": {
            "component_rule": "whole 8-connected catalogue components",
            "quadrants": "fixed and label-blind",
            "buffer_px": BUFFER_PX,
            "buffer_m": BUFFER_PX * 100,
            "visible_catalogue_mask": "pixel-exact before placement and in evaluation",
            "withheld_positive_pixels": total_withheld,
        },
        "budget": {"global_dots": DOT_BUDGET, "radius_px": DOT_RADIUS_PX},
        "bootstrap": {
            "block_px": BLOCK_SIDE_PX,
            "block_m": BLOCK_SIDE_PX * 100,
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
        },
    }
    dump(HOLDOUT_PATH, holdout)
    candidate = summary["scores"]["hurst_break"]
    controls = summary["paired_differences"]
    delta_vs_best = candidate["dti"] - best["dti"]
    card["holdout_dti"] = {
        "label": "HOLDOUT-DTI",
        "status": "COMPLETED",
        "evaluator_version": evaluator.VERSION,
        "alpha": 0.2,
        "beta": 0.8,
        "triangular_radius_m": 300.0,
        "withheld_positives": candidate["withheld_positive_pixels"],
        "value": candidate["dti"],
        "ci95": candidate["ci95"],
        "paired_controls": controls,
        "folds": [
            {"fold": r["fold"]["fold"], "withheld_positives": r["fold"]["truth_px"], "candidate_dti": r["arms"]["hurst_break"]["dti"]}
            for r in fold_receipts
        ],
        "file": str(HOLDOUT_PATH.relative_to(ROOT)),
    }
    card["comparison_vs_recorded_best"] = {
        "label": "HOLDOUT-DTI",
        "baseline_arm": "cpad_e1",
        "baseline_value": best["dti"],
        "baseline_ci95": best["ci95"],
        "baseline_withheld_positives": best["withheld_positive_pixels"],
        "baseline_evaluator_version": best["evaluator_version"],
        "candidate_minus_baseline_point_difference": delta_vs_best,
        "paired_ci_available": False,
        "paired_ci_reason": "The stored S17 JSON has pooled CPAD terms and fold summaries but no aligned CPAD 20-km block terms for this new candidate.",
        "beats_recorded_best_point_estimate": bool(candidate["dti"] > best["dti"]),
    }

    final_dots = ced.place(fields["surface"], fp & ~catalogue, DOT_BUDGET, radius=DOT_RADIUS_PX)
    dot_hash = dot_digest(final_dots)
    dump(
        FINAL_REGISTRY_PATH,
        registry_phase(fields["surface"], fp, inventory, sample_meta, dots=final_dots),
    )
    final_report = json.loads(FINAL_REGISTRY_PATH.read_text())
    final_rows = final_report.get("comparisons", [])
    overlaps = [
        row["dots"]["overlap_within_3px"]
        for row in final_rows
        if row.get("dots", {}).get("overlap_within_3px") is not None
    ]
    max_overlap_row = max(
        (row for row in final_rows if row.get("dots", {}).get("overlap_within_3px") is not None),
        key=lambda row: row["dots"]["overlap_within_3px"],
        default=None,
    )
    card["registry_comparison"]["final_dots"] = {
        "status": final_report["status"],
        "checked": final_report.get("checked"),
        "not_checked_after_stop": final_report.get("not_checked_after_stop"),
        "final_dots": int(final_dots.sum()),
        "max_measured_overlap_within_3px_among_checked": max(overlaps) if overlaps else None,
        "first_violating_overlap_within_3px": (max_overlap_row["dots"]["overlap_within_3px"] if final_report["status"] == "DUPLICATE" and max_overlap_row else None),
        "first_violating_registry_dots": (max_overlap_row["dots"]["registry_dots"] if final_report["status"] == "DUPLICATE" and max_overlap_row else None),
        "measured_overlaps_are_partial_due_to_stop": final_report["status"] == "DUPLICATE",
        "closest_raster": max_overlap_row,
        "file": str(FINAL_REGISTRY_PATH.relative_to(ROOT)),
    }
    card["final_dot_mask_sha256"] = dot_hash

    if final_report["status"] == "DUPLICATE":
        card["scientific_verdict"] = (
            "BEATS_RECORDED_HOLDOUT_BEST" if candidate["dti"] > best["dti"] else "NEGATIVE_VS_RECORDED_HOLDOUT_BEST"
        )
        lock.update(status="STOPPED_FINAL_DOT_DUPLICATE", completed_utc=datetime.now(timezone.utc).isoformat())
        dump(LOCK, lock)
        del final_dots, terms
        gc.collect()
        return stop(
            card,
            "Final candidate dots exceeded a registry duplicate threshold; no TIFF was written, no anti-registry placement was attempted, and no submission slot was selected.",
        )

    if final_report["status"] != "PASS_WITHIN_INDEXED_SCOPE" or not inventory.get("complete_universal_registry", False):
        card["scientific_verdict"] = (
            "BEATS_RECORDED_HOLDOUT_BEST" if candidate["dti"] > best["dti"] else "NEGATIVE_VS_RECORDED_HOLDOUT_BEST"
        )
        lock.update(status="STOPPED_UNVERIFIED_REGISTRY_SCOPE", completed_utc=datetime.now(timezone.utc).isoformat())
        dump(LOCK, lock)
        del final_dots, terms
        gc.collect()
        return stop(
            card,
            "Holdout completed, but the pinned registry comparison is incomplete/non-universal; no unique TIFF can be certified, so no artifact was written.",
            verdict="not_promoted",
        )

    # This branch is unreachable with the current known-incomplete S17 inventory;
    # if a future complete gate exists, publish as a clearly marked research download.
    raster_path = ROOT / "docs/downloads/hurst-break-research-r1-20261025-zeros.tif"
    writer_receipt = write_submission(
        raster_path,
        final_dots.astype(np.float32),
        SAMPLE,
        fp,
        name=SUBMISSION_NAME,
        note=NOTE,
        catalogue=catalogue,
        metadata={"run_id": lock["run_id"], "dot_mask_sha256": dot_hash, "research_only": True},
    )
    scientific_verdict = (
        "BEATS_RECORDED_HOLDOUT_BEST" if candidate["dti"] > best["dti"] else "NEGATIVE_VS_RECORDED_HOLDOUT_BEST"
    )
    card.update(
        raster_sha256=writer_receipt["sha256"],
        raster_written=True,
        artifact={"path": str(raster_path.relative_to(ROOT)), "bytes": writer_receipt["bytes"]},
        validator_output={"status": "PASS", "writer_receipt": writer_receipt},
        scientific_verdict=scientific_verdict,
        verdict="negative" if scientific_verdict.startswith("NEGATIVE") else "not_promoted",
        verdict_reason="Research artifact only; no promotion or submission slot was selected.",
        submission_ready=False,
        download_status={"ok_to_download_new_candidate": True, "status": "RESEARCH_ONLY", "artifact": str(raster_path.relative_to(ROOT))},
        submission_status={"ok_to_submit": False, "reason": "Separate human selector/slot decision required; no score is organizer-confirmed.", "slots_used": 0, "selector_approval": False, "organizer_confirmed": False},
        completed_utc=datetime.now(timezone.utc).isoformat(),
    )
    lock.update(status="COMPLETED_WRITTEN_RESEARCH_ONLY", completed_utc=datetime.now(timezone.utc).isoformat())
    dump(LOCK, lock)
    _write_card(card)
    return card


def main():
    run()


if __name__ == "__main__":
    main()
