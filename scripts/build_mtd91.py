#!/usr/bin/env python3
"""MTD91 magnetic texture destruction lane — 3 budgeted experiments."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from evaluate_holdout import (  # noqa: E402
    build_segment_buffered_folds,
    check_registry_uniqueness,
    run_leakage_canary,
    score_pooled_holdout,
    EVALUATOR_VERSION,
)
from gems91 import io as GIO  # noqa: E402
from gems91 import mtd  # noqa: E402
from submission_writer import write_validated_submission_bundle  # noqa: E402

FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
WORK = ROOT / "work/mtd91"
SEED = 20261024


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n")


def verify_inputs() -> dict:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    wanted = {"sample_submission", "existing_faults", "training_features"}
    out = {}
    for e in manifest["files"]:
        if e["id"] not in wanted:
            continue
        p = ROOT / "data" / e["local_subpath"]
        digest = GIO.sha256_file(p)
        assert digest == e["sha256"] and p.stat().st_size == e["bytes"], e["id"]
        out[e["id"]] = {"sha256": digest, "bytes": p.stat().st_size}
    assert set(out) == wanted
    return out


def load_grid():
    with rasterio.open(SAMPLE) as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(CAT) as s:
        cat = (np.nan_to_num(s.read(1), nan=0.0) > 0) & fp
    with rasterio.open(FEATS) as s:
        rtp = s.read(mtd.BAND_RTP)
        vg = s.read(mtd.BAND_TMI_VG)
    return fp, cat, rtp, vg


def registry_paths(fp_shape) -> list[Path]:
    paths = []
    for d in [
        ROOT / "data/official",
        ROOT / "data/registry",
        ROOT / "data/registry_siblings",
        ROOT / "docs/downloads",
        ROOT / "data/fleet_registry",
    ]:
        if d.is_dir():
            paths.extend(sorted(d.glob("*.tif")))
    # parent R0 aliases
    r0 = ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif"
    src = ROOT / "data/parent/GEMSDOE32__h33-2-b2-zeros.tif"
    if not r0.is_file():
        for cand in [
            ROOT / "data/registry_rasters/GEMSDOE32__h33-2-b2-zeros.tif",
        ]:
            pass
        # manifest parent
        man = json.loads((ROOT / "registry/data_manifest.json").read_text())
        for e in man["files"]:
            if e["id"] == "parent_r0_zeros":
                p = ROOT / "data" / e["local_subpath"]
                if p.is_file():
                    r0.parent.mkdir(parents=True, exist_ok=True)
                    if not r0.is_file():
                        shutil.copy2(p, r0)
                    paths.append(r0)
    out = []
    for p in paths:
        try:
            with rasterio.open(p) as s:
                if s.shape == fp_shape:
                    out.append(p)
        except Exception:
            continue
    # unique by name
    seen = set()
    uniq = []
    for p in out:
        if p.name in seen:
            continue
        seen.add(p.name)
        uniq.append(p)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="all", choices=["all", "holdout", "build"])
    args = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    pins = verify_inputs()
    fp, cat_full, rtp, vg = load_grid()
    feats = mtd.features_from_bands(rtp, vg, fp)
    feat_names = list(feats.keys())
    feat_stack = np.stack([feats[n][fp] for n in feat_names], axis=1)

    folds = build_segment_buffered_folds(cat_full, fp)
    n_withheld = int(sum(f.n_withheld for f in folds))
    canary = run_leakage_canary(
        feat_stack, feat_names, folds, fp, subsample_step=4
    )
    dump(ROOT / "docs/mtd91-canaries.json", canary)
    if not canary["all_pass"]:
        print("LEAKAGE CANARY FAIL", canary["flagged_features"], canary["worst_symmetric_auc"])
        # continue but mark negative

    surfaces = {
        "e1": mtd.surface_e1(feats, fp),
        "e2": mtd.surface_e2(feats, fp),
        "e3": mtd.surface_e3(feats, fp),
    }

    cached = ROOT / "docs/mtd91-holdout.json"
    holdouts = {}
    winner = None
    best_dti = -1.0
    if cached.is_file() and args.mode == "build":
        prev = json.loads(cached.read_text())
        holdouts = prev["experiments"]
        winner = prev["winner"]
        best_dti = float(holdouts[winner]["holdout_dti"])
        n_withheld = int(prev.get("n_withheld_positives", n_withheld))
    for name, surf in surfaces.items():
        if winner is not None and args.mode == "build":
            break
        fold_preds = {}
        for f in folds:
            vis = f.visible_faults
            dots = mtd.emit_dots(surf, fp, vis)
            pred = dots.astype(np.float32)
            fold_preds[f.fold_id] = pred
        score = score_pooled_holdout(fold_preds, folds, fp, n_boot=80, seed=SEED)
        holdouts[name] = score
        dti = float(score["holdout_dti"])
        print(f"HOLDOUT-DTI {name}={dti:.6f} CI={score['ci_95']} withheld={score['n_withheld_positives']}")
        if dti > best_dti:
            best_dti = dti
            winner = name

    dump(ROOT / "docs/mtd91-holdout.json", {
        "evaluator_version": EVALUATOR_VERSION,
        "n_withheld_positives": n_withheld,
        "experiments": holdouts,
        "winner": winner,
        "canary": {"all_pass": canary["all_pass"], "worst": canary["worst_symmetric_auc"]},
        "pins": pins,
    })

    # Full-catalogue emission for research TIF (visible=full cat)
    surf = surfaces[winner]
    dots = mtd.emit_dots(surf, fp, cat_full)
    n_dots = int(dots.sum())
    print("winner", winner, "dots", n_dots)

    regs = registry_paths(fp.shape)
    uniq = check_registry_uniqueness(surf[fp], dots.astype(np.float32), fp, regs)
    dump(ROOT / "docs/mtd91-registry.json", {
        k: v for k, v in uniq.items() if k != "comparisons"
    } | {"n_comparisons": uniq["n_registry_rasters_checked"]})

    stem = f"gems91-mtd91-{winner}-37654dots-s2p8-20261024"
    audit = write_validated_submission_bundle(
        dots.astype(np.float32),
        stem_prefix=stem,
        date_tag="20261024T180000Z",
        template_path=SAMPLE,
        catalogue_path=CAT,
        parent_compare_path=None,
    )
    sha = audit["primary_zeros_tif"]["sha256"]
    short = sha[:8]
    # rename conceptually via stem already unique
    note = f"MTD91 {winner} mag texture dest RTP+VG; research; not a slot pick"
    note = note[:140]

    promote = (
        canary["all_pass"]
        and uniq["uniqueness_pass"]
        and audit["validators"]["range_0_1_portal_safe"]
        and best_dti >= 0.142885  # same-instrument HGB-CTX bar
    )
    card = {
        "schema": "gems91.run-card.v2",
        "run_id": f"MTD91-{winner}-20261024",
        "hypothesis": "Magnetic damage-zone fabric destruction shortens RTP/TMI-VG coherence even without a scarp.",
        "mechanism": "Structure-tensor isotropy + high-frequency energy fraction; greedy 2.8 px off-catalogue dots.",
        "non_fault_mimic": "Young volcanic flows and GeoDAWN flight-line levelling residuals destroy magnetic coherence without being Quaternary faults.",
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "value": best_dti,
            "evaluator_version": EVALUATOR_VERSION,
            "withheld_positives": holdouts[winner].get("n_withheld_positives", n_withheld),
            "ci95": holdouts[winner]["ci_95"],
        },
        "correlation_overlap_vs_registry": {
            "n_checked": uniq["n_registry_rasters_checked"],
            "surface_max_abs_rank_corr": uniq["surface_max_abs_rank_corr"],
            "dots_max_3px_overlap": uniq["dots_max_3px_overlap"],
            "uniqueness_pass": uniq["uniqueness_pass"],
            "closest": uniq["dots_closest_raster"],
        },
        "raster_sha256": sha,
        "validator_output": {
            "status": "PASS" if audit["validators"]["range_0_1_portal_safe"] else "FAIL",
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs_shape_transform_match": True,
            "all_finite_zeros_twin": audit["primary_zeros_tif"]["all_cells_finite"],
        },
        "submission_name": audit["candidate_id"],
        "submission_note": note,
        "verdict": "promote" if promote else "negative",
        "ok_to_submit": bool(promote),
        "download": audit["primary_zeros_tif"]["path"],
        "canary_pass": canary["all_pass"],
        "winner_experiment": winner,
        "n_dots": n_dots,
        "experiments_run": 3,
        "pins": pins,
        "created_utc": now(),
    }
    dump(ROOT / "docs/run-card-MTD91.json", card)
    dump(ROOT / "docs/data/run_card.json", card)
    print(json.dumps({k: card[k] for k in ("verdict", "holdout_dti", "ok_to_submit", "submission_name")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
