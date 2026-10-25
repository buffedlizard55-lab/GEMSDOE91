#!/usr/bin/env python3
"""Run the preregistered S14-PTAC cross-fit posterior-topology lane.

Reuses the shared cached stacks, `scripts/evaluate_holdout.py`, S13's unchanged
Dinkelbach emitter, and `scripts/submission_writer.py`. No organizer upload occurs.
"""

from __future__ import annotations

import gc
import hashlib
import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "src"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import io as IO  # noqa: E402
from gems91 import mhtr_coda as MC  # noqa: E402
from gems91 import ptac14 as PTAC  # noqa: E402
from gems91 import ptha as PTHA  # noqa: E402
from gems91 import readiness as RD  # noqa: E402
from gems91 import spac_coda as SC  # noqa: E402
from scripts import evaluate_holdout as EH  # noqa: E402
from scripts import run_s13_lane as S13  # noqa: E402
from scripts import submission_writer as SW  # noqa: E402
from vendor.gems57.validate import validate as validate_gems57  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "derived"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
FEATURES = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0 = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
DOWNLOADS = ROOT / "docs" / "downloads"
DATA_RELEASES = DATA / "releases" / "s14"
PREREG = ROOT / "docs" / "HYPOTHESES_S14_PTAC.md"
RUN_CARD = ROOT / "docs" / "run-card-S14-PTAC.json"
EVIDENCE = ROOT / "evidence" / "s14_ptac_20261024.json"

MAX_EXPERIMENTS = 3
MAX_SECONDS = 7200.0
DOT_BUDGET = 44_000
BASELINE_DTI = 0.244601
BASELINE_CI = [0.230592, 0.257058]
SPLIT_SHA = "0f874367d8d34964c9b8802d3d67d348f68ade1f9fbc4301bffc5eafcb524db8"


def log(message: str) -> None:
    now = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{now}] {message}", flush=True)


def check_budget(start: float) -> None:
    elapsed = time.perf_counter() - start
    if elapsed > MAX_SECONDS:
        raise RuntimeError(f"Rule 6 wall-clock budget exceeded: {elapsed:.1f}s > {MAX_SECONDS:.1f}s")


def split_sha(folds: list[EH.HoldoutFold]) -> str:
    h = hashlib.sha256()
    for fold in folds:
        h.update(fold.name.encode("utf-8"))
        h.update(np.packbits(fold.region_mask.ravel()).tobytes())
        h.update(np.packbits(fold.withheld_faults.ravel()).tobytes())
    return h.hexdigest()


def registry_paths() -> list[Path]:
    """All locally indexed same-grid references, hash-deduplicated but not exempted."""
    seen: dict[str, Path] = {}
    for folder in (
        DATA / "fleet_registry",
        DATA / "registry",
        DATA / "retracted_geod",
        DOWNLOADS,
    ):
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.tif")):
            if path.name.startswith("gems91-s14-ptac-"):
                continue
            digest = IO.sha256_file(path)
            seen.setdefault(digest, path)
    return list(seen.values())


def load_grid(path: Path, footprint: np.ndarray) -> np.ndarray:
    with rasterio.open(path) as src:
        arr = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)
    arr[~footprint] = 0.0
    return arr


def save_surface(path: Path, surface: np.ndarray, footprint: np.ndarray, meta: dict) -> None:
    surface[footprint].astype(np.float32).tofile(path)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def load_surface(path: Path, footprint: np.ndarray) -> tuple[np.ndarray, dict] | None:
    n_fp = int(footprint.sum())
    meta_path = path.with_suffix(".json")
    if not path.is_file() or not meta_path.is_file() or path.stat().st_size != n_fp * 4:
        return None
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.fromfile(path, dtype=np.float32)
    return out, json.loads(meta_path.read_text(encoding="utf-8"))


def calibrated(prob: np.ndarray, footprint: np.ndarray, meta: dict) -> np.ndarray:
    return PTHA.prior_shift_calibrate_surface(
        prob,
        footprint,
        pi_true=float(meta["pi_vis_train"]),
        pi_sample=float(meta["pi_sample_weighted"]),
    )


def stage1_pair_surfaces(
    *,
    folds: list[EH.HoldoutFold],
    cat: np.ndarray,
    footprint: np.ndarray,
    X_static: np.ndarray,
    static_cols: list[int],
    static_names: list[str],
    X_s11: np.ndarray,
    s11_names: list[str],
    X_ptha: np.ndarray,
    ptha_names: list[str],
    exp_start: float,
) -> dict[tuple[int, int], tuple[np.ndarray, dict]]:
    pairs: dict[tuple[int, int], tuple[np.ndarray, dict]] = {}
    for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
        path = CACHE / f"s14_pair_s13_e2_{a}_{b}.dat"
        cached = load_surface(path, footprint)
        if cached is not None:
            pairs[(a, b)] = cached
            log(f"Loaded cross-fit Stage-1 pair ({a},{b})")
            continue

        c, d = [q for q in range(4) if q not in (a, b)]
        exclude = (
            folds[c].region_mask
            | folds[c].withheld_faults
            | folds[c].buffer_mask
            | folds[d].region_mask
            | folds[d].withheld_faults
            | folds[d].buffer_mask
        )
        visible = cat & folds[c].visible_faults & folds[d].visible_faults & (~exclude)
        log(f"Fitting cross-fit Stage-1 pair ({a},{b}); train positives={int(visible.sum()):,}")
        surface, meta = PTHA.fit_and_predict_ptha_oof_fold(
            X_static=X_static,
            static_cols=static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_cols=list(range(len(s11_names))),
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_cols=list(range(len(ptha_names))),
            ptha_names=ptha_names,
            visible_faults=visible,
            exclude_mask=exclude,
            footprint=footprint,
            seed=1400 + 10 * a + b,
        )
        save_surface(path, surface, footprint, meta)
        pairs[(a, b)] = (surface, meta)
        log(f"Saved cross-fit Stage-1 pair ({a},{b})")
        check_budget(exp_start)
    return pairs


def make_fold_autocontext(
    *,
    folds: list[EH.HoldoutFold],
    footprint: np.ndarray,
    pairs: dict[tuple[int, int], tuple[np.ndarray, dict]],
    stage1_oof: dict[int, tuple[np.ndarray, dict]],
) -> dict[int, tuple[np.memmap, list[str]]]:
    n_fp = int(footprint.sum())
    result: dict[int, tuple[np.memmap, list[str]]] = {}
    for fold in folds:
        q = fold.fold_id
        ac_path = CACHE / f"s14_ptac_fold_f{q}.dat"
        expected = n_fp * len(SC.S12_AUTOCONTEXT_FEATURE_NAMES) * 4
        if not ac_path.is_file() or ac_path.stat().st_size != expected:
            stitched = np.zeros(footprint.shape, dtype=np.float32)
            visible_quads = [m for m in range(4) if m != q]
            for m in visible_quads:
                train_pair = tuple(sorted(x for x in visible_quads if x != m))
                stitched[folds[m].region_mask] = pairs[train_pair][0][folds[m].region_mask]
            stitched[fold.region_mask] = stage1_oof[q][0][fold.region_mask]
            ac = SC.compute_spac_autocontext_features(stitched, footprint)
            mmw = np.memmap(
                ac_path,
                dtype=np.float32,
                mode="w+",
                shape=(n_fp, len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)),
            )
            mmw[:] = ac
            mmw.flush()
            del mmw, ac, stitched
            gc.collect()
        result[q] = (
            np.memmap(
                ac_path,
                dtype=np.float32,
                mode="r",
                shape=(n_fp, len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)),
            ),
            list(SC.S12_AUTOCONTEXT_FEATURE_NAMES),
        )
    return result


def full_registry_summary(report: dict) -> dict:
    comparisons = report.get("comparisons", [])
    top = sorted(
        comparisons,
        key=lambda row: row.get("cand_within_3px_of_reg", 0.0),
        reverse=True,
    )[:5]
    return {
        "gate_version": report.get("uniqueness_gate_version"),
        "n_checked": report.get("n_registry_rasters_checked", 0),
        "pass": bool(report.get("uniqueness_pass", False)),
        "max_abs_surface_spearman": report.get("surface_max_abs_rank_corr", 0.0),
        "surface_closest_raster": report.get("surface_closest_raster", ""),
        "max_3px_dot_overlap": report.get("dots_max_3px_overlap", 0.0),
        "dots_closest_raster": report.get("dots_closest_raster", ""),
        "top_5_by_overlap": top,
    }


def main() -> int:
    for required in (TEMPLATE, CATALOGUE, FEATURES, GDR, SGMC, R0, PREREG):
        if not required.is_file():
            raise FileNotFoundError(f"missing required input {required}")
    CACHE.mkdir(parents=True, exist_ok=True)
    DATA_RELEASES.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)

    prereg_sha = IO.sha256_file(PREREG)
    log(f"S14-PTAC preregistration sha256={prereg_sha}")
    with rasterio.open(TEMPLATE) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE) as src:
        cat = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC) as src:
        sgmc = (src.read(1) > 0) & footprint
    r0 = load_grid(R0, footprint)

    folds = EH.build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    actual_split = split_sha(folds)
    if actual_split != SPLIT_SHA:
        raise RuntimeError(f"holdout split drift: {actual_split} != {SPLIT_SHA}")
    n_fp = int(footprint.sum())
    log(f"Shared holdout ready: {sum(f.n_withheld for f in folds):,} withheld positives")

    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES, gdr_csv=GDR, footprint=footprint, cache_dir=CACHE
    )
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE
    )
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE
    )
    static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    s11_cols = list(range(len(s11_names)))
    ptha_cols = list(range(len(ptha_names)))
    ptha_crest = PTHA.build_ptha_structural_crest_surface(
        MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)[0], X_ptha, footprint
    )
    _, piedmont = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)

    fold_eligible: dict[int, np.ndarray] = {}
    train_eligible: dict[int, np.ndarray] = {}
    for fold in folds:
        _, fold_eligible[fold.fold_id] = S13._fold_active_and_eligible(
            fold, folds, footprint, collar_px=3.0
        )
        exclude = fold.region_mask | fold.withheld_faults | fold.buffer_mask
        d_vis = ndi.distance_transform_edt(~fold.visible_faults)
        train_eligible[fold.fold_id] = (
            footprint & (~exclude) & (~fold.visible_faults) & (d_vis > 3.0)
        )
    d_cat = ndi.distance_transform_edt(~cat)
    full_eligible = footprint & (~cat) & (d_cat > 3.0)

    # Load the frozen S13 E2 OOF surfaces and reconstruct its E3 Dinkelbach baseline.
    stage1_oof: dict[int, tuple[np.ndarray, dict]] = {}
    baseline_dots: dict[int, np.ndarray] = {}
    for fold in folds:
        q = fold.fold_id
        loaded = load_surface(CACHE / f"s13_oof_e2_f{q}.dat", footprint)
        if loaded is None:
            raise FileNotFoundError(
                f"missing frozen S13 cache for fold {q}; run scripts/run_s13_lane.py --oof-only"
            )
        stage1_oof[q] = loaded
        baseline_dots[q], _ = PTHA.dinkelbach_fold_independent_emit(
            loaded[0],
            ptha_crest,
            piedmont,
            footprint=footprint,
            train_eligible_mask=train_eligible[q],
            test_eligible_mask=fold_eligible[q],
            pi_true=float(loaded[1]["pi_vis_train"]),
            pi_sample=float(loaded[1]["pi_sample_weighted"]),
            target_pool_dots=48_000,
            full_eligible_pixels=int(full_eligible.sum()),
            min_spacing_px=2.50,
        )
    baseline = EH.score_pooled_holdout(baseline_dots, folds, footprint, n_boot=200, seed=133)
    if baseline["holdout_dti"] != BASELINE_DTI:
        raise RuntimeError(f"S13 baseline did not reproduce: {baseline['holdout_dti']}")
    baseline_tiles = S13._accumulate_fold_tiles(baseline_dots, folds, footprint)
    log(f"Reproduced S13-PTHA E3 baseline: {BASELINE_DTI:.6f} HOLDOUT-DTI")

    exp_start = time.perf_counter()
    expected_ac_bytes = n_fp * len(SC.S12_AUTOCONTEXT_FEATURE_NAMES) * 4
    fold_ac_cached = all(
        (CACHE / f"s14_ptac_fold_f{fold.fold_id}.dat").is_file()
        and (CACHE / f"s14_ptac_fold_f{fold.fold_id}.dat").stat().st_size
        == expected_ac_bytes
        for fold in folds
    )
    if fold_ac_cached:
        # Loading six dense pair surfaces costs hundreds of MB and is unnecessary
        # once all four fold-safe auto-context matrices have been materialized.
        pairs: dict[tuple[int, int], tuple[np.ndarray, dict]] = {}
        log("Loaded four cached cross-fit auto-context matrices")
    else:
        pairs = stage1_pair_surfaces(
            folds=folds,
            cat=cat,
            footprint=footprint,
            X_static=X_static,
            static_cols=static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_names=ptha_names,
            exp_start=exp_start,
        )
    fold_ac = make_fold_autocontext(
        folds=folds, footprint=footprint, pairs=pairs, stage1_oof=stage1_oof
    )
    del pairs
    gc.collect()

    # Leakage canary: all 75 inherited S13 features already passed; test every new AC feature now.
    ac_canary = EH.run_leakage_canary(
        np.empty((n_fp, 0), dtype=np.float32),
        [],
        folds,
        footprint,
        fold_specific_features=fold_ac,
        subsample_step=4,
    )
    inherited_canary = json.loads((CACHE / "s13_canary_v1.json").read_text(encoding="utf-8"))
    canary_pass = bool(ac_canary["all_pass"] and inherited_canary["canary_pass"])
    worst_auc = max(
        float(ac_canary["worst_symmetric_auc"]),
        float(inherited_canary["worst_symmetric_auc"]),
    )
    worst_feature = (
        ac_canary["worst_feature"]
        if float(ac_canary["worst_symmetric_auc"])
        >= float(inherited_canary["worst_symmetric_auc"])
        else inherited_canary["worst_feature"]
    )
    if not canary_pass or worst_auc > 0.90:
        raise RuntimeError(f"Rule 4 canary failed: {worst_feature} AUC={worst_auc}")
    log(f"Leakage canary PASS: 85/85 features; worst symmetric AUC={worst_auc:.5f}")

    # Fit Stage-2 once per fold; all three experiments reuse these outputs.
    stage2_oof: dict[int, tuple[np.ndarray, dict]] = {}
    for fold in folds:
        q = fold.fold_id
        cache_path = CACHE / f"s14_stage2_oof_f{q}.dat"
        loaded = load_surface(cache_path, footprint)
        if loaded is None:
            exclude = fold.region_mask | fold.withheld_faults | fold.buffer_mask
            ac_mm = fold_ac[q][0]
            blocks = [
                (X_static, static_cols),
                (X_s11, s11_cols),
                (X_ptha, ptha_cols),
                (ac_mm, list(range(10))),
            ]
            log(f"Fitting H14 Stage-2 OOF fold {fold.name}")
            surface, meta = PTAC.fit_predict_stage2(
                train_blocks=blocks,
                infer_blocks=blocks,
                visible_faults=fold.visible_faults,
                exclude_mask=exclude,
                footprint=footprint,
                seed=1450 + q,
            )
            save_surface(cache_path, surface, footprint, meta)
            loaded = (surface, meta)
        stage2_oof[q] = loaded
        check_budget(exp_start)

    reg_paths = registry_paths()
    log(f"Indexed {len(reg_paths)} hash-distinct registry rasters (no lattice exemption)")

    exp_specs = [
        {
            "id": "E1",
            "hypothesis": "H14-1",
            "title": "Cross-fit S13 posterior-topology auto-context + calibrated arithmetic pool + Dinkelbach",
            "pool": "arithmetic",
            "bridge_crest": False,
            "mimic": "Braided ephemeral channels, roads, and Lake Lahontan shorelines",
        },
        {
            "id": "E2",
            "hypothesis": "H14-1 + H14-2",
            "title": "H14-1 + two-sided wash-bridge × independent multi-physics crest concordance",
            "pool": "arithmetic",
            "bridge_crest": True,
            "mimic": "Straight canals, roads, and aeromagnetic flight-line seams",
        },
        {
            "id": "E3",
            "hypothesis": "H14-1 + H14-2 + H14-3",
            "title": "H14-2 + Stage-1/Stage-2 calibrated log-opinion consensus",
            "pool": "log",
            "bridge_crest": True,
            "mimic": "Broad pluton margins, basin-scale strain lobes, and diffuse alteration halos",
        },
    ]
    experiments: list[dict] = []

    for number, spec in enumerate(exp_specs, start=1):
        check_budget(exp_start)
        surfaces: dict[int, np.ndarray] = {}
        crests: dict[int, np.ndarray] = {}
        mosaic = np.zeros(footprint.shape, dtype=np.float32)
        for fold in folds:
            q = fold.fold_id
            p1 = calibrated(stage1_oof[q][0], footprint, stage1_oof[q][1])
            p2 = calibrated(stage2_oof[q][0], footprint, stage2_oof[q][1])
            if spec["pool"] == "log":
                surf = PTAC.log_opinion_pool(p1, p2, footprint, stage2_weight=0.65)
            else:
                surf = PTAC.arithmetic_probability_pool(p1, p2, footprint, stage2_weight=0.72)
            ac_mm = fold_ac[q][0]
            if spec["bridge_crest"]:
                b900 = np.zeros(footprint.shape, dtype=np.float32)
                b2k = np.zeros(footprint.shape, dtype=np.float32)
                b900[footprint] = np.asarray(ac_mm[:, 4], dtype=np.float32)
                b2k[footprint] = np.asarray(ac_mm[:, 5], dtype=np.float32)
                crest = PTAC.bridge_concordant_crest(ptha_crest, b900, b2k, footprint)
            else:
                crest = ptha_crest
            surfaces[q] = surf
            crests[q] = crest
            mosaic[fold.region_mask] = surf[fold.region_mask]

        pre = EH.check_registry_surface_uniqueness(
            mosaic[footprint], footprint, reg_paths, max_rank_corr=0.90, corr_stride=20
        )
        if pre["is_duplicate"]:
            experiments.append(
                {
                    "experiment_number": number,
                    "exp_id": spec["id"],
                    "hypothesis_id": spec["hypothesis"],
                    "status": "STOPPED_PREPLACEMENT_DUPLICATE",
                    "preplacement": pre,
                }
            )
            log(f"{spec['id']} pre-placement surface DUPLICATE; protocol stop")
            break

        fold_dots: dict[int, np.ndarray] = {}
        allocation: dict[str, dict] = {}
        for fold in folds:
            q = fold.fold_id
            dots, meta = PTHA.dinkelbach_fold_independent_emit(
                surfaces[q],
                crests[q],
                piedmont,
                footprint=footprint,
                train_eligible_mask=train_eligible[q],
                test_eligible_mask=fold_eligible[q],
                pi_true=0.5,
                pi_sample=0.5,
                target_pool_dots=48_000,
                full_eligible_pixels=int(full_eligible.sum()),
                min_spacing_px=2.50,
            )
            fold_dots[q] = dots
            allocation[fold.name] = meta
        holdout = EH.score_pooled_holdout(
            fold_dots, folds, footprint, n_boot=200, seed=140 + number
        )
        tiles = S13._accumulate_fold_tiles(fold_dots, folds, footprint)
        paired = S13.compute_aligned_paired_bootstrap(
            tiles,
            baseline_tiles,
            cand_pooled_dti=holdout["holdout_dti"],
            base_pooled_dti=baseline["holdout_dti"],
            n_boot=400,
            seed=14100 + number,
        )
        experiments.append(
            {
                "experiment_number": number,
                "exp_id": spec["id"],
                "hypothesis_id": spec["hypothesis"],
                "title": spec["title"],
                "named_non_fault_mimic": spec["mimic"],
                "n_features": 85,
                "emission_mode": "fold-independent S13 Dinkelbach",
                "preplacement": {
                    "status": "PASS_WITHIN_INDEXED_SCOPE",
                    "checked": pre["n_registry_rasters_checked"],
                    "max_abs_surface_spearman": pre["surface_max_abs_rank_corr"],
                    "closest_raster": pre["surface_closest_raster"],
                },
                "holdout": holdout,
                "paired_vs_s13_e3": paired,
                "fold_allocation": allocation,
                "status": "COMPLETED",
            }
        )
        log(
            f"{spec['id']}: {holdout['holdout_dti']:.6f} HOLDOUT-DTI "
            f"95% CI {holdout['ci_95']}; delta vs S13={paired['delta']:+.6f} "
            f"paired CI {paired['ci95']}"
        )

    completed = [x for x in experiments if x.get("status") == "COMPLETED"]
    if not completed:
        raise RuntimeError("No S14 experiment reached holdout scoring")
    winner = max(completed, key=lambda x: x["holdout"]["holdout_dti"])
    winner_spec = next(s for s in exp_specs if s["id"] == winner["exp_id"])
    beats_best = (
        winner["holdout"]["holdout_dti"] > BASELINE_DTI
        and winner["paired_vs_s13_e3"]["ci95"][0] > 0.0
    )
    log(f"Holdout winner {winner['exp_id']} beats frozen S13 bar={beats_best}")

    # Full-map Stage-1 and cross-fit train/inference auto-context.
    full_train_stage1 = np.zeros(footprint.shape, dtype=np.float32)
    for fold in folds:
        full_train_stage1[fold.region_mask] = stage1_oof[fold.fold_id][0][fold.region_mask]

    # The topology extractor transiently holds many full-grid arrays. Release all
    # holdout-only surfaces, dots, masks, and memmap views before entering it. The
    # first implementation retained every arm's four surfaces/crests here and was
    # correctly killed by the 4 GB sandbox before artifact emission.
    del (
        stage1_oof,
        stage2_oof,
        fold_ac,
        baseline_dots,
        baseline_tiles,
        fold_eligible,
        train_eligible,
        surfaces,
        crests,
        fold_dots,
        dots,
        tiles,
        mosaic,
        p1,
        p2,
        surf,
        crest,
        ac_mm,
        b900,
        b2k,
    )
    gc.collect()
    log("Released holdout-only arrays before full-map fitting")

    full_ac_train_path = CACHE / "s14_ptac_full_train_oof.dat"
    expected_ac = n_fp * 10 * 4
    if not full_ac_train_path.is_file() or full_ac_train_path.stat().st_size != expected_ac:
        ac_train = SC.compute_spac_autocontext_features(full_train_stage1, footprint)
        mmw = np.memmap(full_ac_train_path, dtype=np.float32, mode="w+", shape=(n_fp, 10))
        mmw[:] = ac_train
        mmw.flush()
        del mmw, ac_train
    full_ac_train = np.memmap(full_ac_train_path, dtype=np.float32, mode="r", shape=(n_fp, 10))

    full_stage1_path = CACHE / "s14_s13_full_stage1.dat"
    full_stage1_loaded = load_surface(full_stage1_path, footprint)
    if full_stage1_loaded is None:
        log("Fitting full-map S13 Stage-1 model")
        full_stage1_surface, full_stage1_meta = PTHA.fit_and_predict_ptha_oof_fold(
            X_static=X_static,
            static_cols=static_cols,
            static_names=static_names,
            X_s11=X_s11,
            s11_cols=s11_cols,
            s11_names=s11_names,
            X_ptha=X_ptha,
            ptha_cols=ptha_cols,
            ptha_names=ptha_names,
            visible_faults=cat,
            exclude_mask=~footprint,
            footprint=footprint,
            seed=1491,
        )
        save_surface(full_stage1_path, full_stage1_surface, footprint, full_stage1_meta)
        full_stage1_loaded = (full_stage1_surface, full_stage1_meta)
    full_stage1_surface, full_stage1_meta = full_stage1_loaded

    full_ac_infer_path = CACHE / "s14_ptac_full_infer.dat"
    if not full_ac_infer_path.is_file() or full_ac_infer_path.stat().st_size != expected_ac:
        ac_infer = SC.compute_spac_autocontext_features(full_stage1_surface, footprint)
        mmw = np.memmap(full_ac_infer_path, dtype=np.float32, mode="w+", shape=(n_fp, 10))
        mmw[:] = ac_infer
        mmw.flush()
        del mmw, ac_infer
    full_ac_infer = np.memmap(full_ac_infer_path, dtype=np.float32, mode="r", shape=(n_fp, 10))

    full_stage2_path = CACHE / "s14_stage2_full.dat"
    full_stage2_loaded = load_surface(full_stage2_path, footprint)
    if full_stage2_loaded is None:
        log("Fitting full-map H14 Stage-2 on cross-fitted auto-context")
        train_blocks = [
            (X_static, static_cols),
            (X_s11, s11_cols),
            (X_ptha, ptha_cols),
            (full_ac_train, list(range(10))),
        ]
        infer_blocks = [
            (X_static, static_cols),
            (X_s11, s11_cols),
            (X_ptha, ptha_cols),
            (full_ac_infer, list(range(10))),
        ]
        full_stage2_surface, full_stage2_meta = PTAC.fit_predict_stage2(
            train_blocks=train_blocks,
            infer_blocks=infer_blocks,
            visible_faults=cat,
            exclude_mask=~footprint,
            footprint=footprint,
            seed=1492,
        )
        save_surface(full_stage2_path, full_stage2_surface, footprint, full_stage2_meta)
        full_stage2_loaded = (full_stage2_surface, full_stage2_meta)
    full_stage2_surface, full_stage2_meta = full_stage2_loaded
    check_budget(exp_start)

    p1_full = calibrated(full_stage1_surface, footprint, full_stage1_meta)
    p2_full = calibrated(full_stage2_surface, footprint, full_stage2_meta)
    if winner_spec["pool"] == "log":
        full_surface = PTAC.log_opinion_pool(p1_full, p2_full, footprint, stage2_weight=0.65)
    else:
        full_surface = PTAC.arithmetic_probability_pool(p1_full, p2_full, footprint, stage2_weight=0.72)
    if winner_spec["bridge_crest"]:
        b900 = np.zeros(footprint.shape, dtype=np.float32)
        b2k = np.zeros(footprint.shape, dtype=np.float32)
        b900[footprint] = np.asarray(full_ac_infer[:, 4], dtype=np.float32)
        b2k[footprint] = np.asarray(full_ac_infer[:, 5], dtype=np.float32)
        full_crest = PTAC.bridge_concordant_crest(ptha_crest, b900, b2k, footprint)
    else:
        full_crest = ptha_crest

    pre_full = EH.check_registry_surface_uniqueness(
        full_surface[footprint], footprint, reg_paths, max_rank_corr=0.90, corr_stride=20
    )
    if pre_full["is_duplicate"]:
        raise RuntimeError(
            "Full-map pre-placement surface is a registry duplicate; protocol stops before writing dots"
        )
    full_dots, last_gain = PTHA.dinkelbach_full_map_emit(
        full_surface,
        full_crest,
        piedmont,
        footprint=footprint,
        full_eligible_mask=full_eligible,
        pi_true=0.5,
        pi_sample=0.5,
        n_dots=DOT_BUDGET,
        min_spacing_px=2.50,
    )
    final_registry = EH.check_registry_uniqueness(
        full_surface[footprint], full_dots, footprint, reg_paths, corr_stride=20
    )
    final_summary = full_registry_summary(final_registry)
    if final_registry["is_duplicate"]:
        log(
            f"FINAL DOTS DUPLICATE: max directed 3px overlap="
            f"{final_registry['dots_max_3px_overlap']:.5f} vs {final_registry['dots_closest_raster']}; "
            "stopping lane after this negative deliverable"
        )

    sgmc_result = EH.score_off_catalogue_sgmc(full_dots, sgmc, cat, footprint)
    r0_sgmc = EH.score_off_catalogue_sgmc(r0, sgmc, cat, footprint)

    bundle = SW.write_validated_submission_bundle(
        full_dots,
        stem_prefix=f"gems91-s14-ptac-{winner['exp_id'].lower()}",
        date_tag="20261024T235500Z",
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        parent_compare_path=R0,
        releases_dir=DATA_RELEASES,
        downloads_dir=DOWNLOADS,
        floor_px=3.0,
        bundle_js_filename="s14_ptac_submission_bundle.js",
    )
    release_zeros = Path(bundle["primary_zeros_tif"]["path"])
    published_zeros = DOWNLOADS / release_zeros.name
    shutil.copy2(release_zeros, published_zeros)
    if IO.sha256_file(published_zeros) != bundle["primary_zeros_tif"]["sha256"]:
        raise RuntimeError("published GeoTIFF hash drift")
    g57 = validate_gems57(published_zeros, footprint=footprint, catalogue=cat)
    if not g57["all_checks_passed"]:
        raise RuntimeError(f"independent gems57 validation failed: {g57}")

    note = (
        f"S14-PTAC research only: final 3px overlap "
        f"{100.0 * final_registry['dots_max_3px_overlap']:.3f}%; duplicate gate failed; do not submit."
        if final_registry["is_duplicate"]
        else (
            f"S14-PTAC {winner['exp_id']}: cross-fit S13 posterior topology + Dinkelbach; "
            f"HOLDOUT-DTI={winner['holdout']['holdout_dti']:.4f}; {bundle['dots']['n_dots']} dots"
        )
    )
    if len(note) > 140:
        raise RuntimeError(f"submission note too long: {len(note)}")
    submission_name = f"GEMS91-S14-PTAC-{winner['exp_id']}-{bundle['dots']['dot_set_digest'][:8]}"
    elapsed = round(time.perf_counter() - exp_start, 2)
    final_pass = bool(final_registry["uniqueness_pass"])
    pre_status = "PASS_WITHIN_INDEXED_SCOPE"
    final_status = "PASS_WITHIN_INDEXED_SCOPE" if final_pass else "STOPPED_DUPLICATE"

    card = {
        "schema_version": "gems91.s14_ptac.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/ed1ec9e1-gemsdoe91",
        "preregistration": {"path": "docs/HYPOTHESES_S14_PTAC.md", "sha256": prereg_sha},
        "lane": {
            "id": "S14-PTAC",
            "assigned": False,
            "provisional_name": "Cross-fit S13 posterior-topology auto-context + physical-crest concordance + Dinkelbach",
            "note": "No external selector-assigned lane paragraph was supplied; self-declared before S14 fitting.",
        },
        "hypothesis": winner["title"],
        "hypothesis_id": winner["hypothesis_id"],
        "physical_mechanism": (
            "Cross-fits the S13 dimensionally calibrated magnetic/gravity/radiometric/depth/strain/seismic "
            "fault posterior, measures two-sided 0.9-2.0 km strike continuity across alluvial cover, and "
            "uses the unchanged 300 m Dinkelbach submodular emitter to retain only marginally useful dots."
        ),
        "named_non_fault_mimic_process": winner["named_non_fault_mimic"],
        "comparable_prior_holdout_best": {
            "candidate_id": "GEMS91-S13-PTHA-E3-9b32da74",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": actual_split,
            "label": "HOLDOUT-DTI",
            "value": BASELINE_DTI,
            "ci95": BASELINE_CI,
            "withheld_positives": 60_988,
        },
        "holdout_dti": {
            "status": "COMPLETED",
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": actual_split,
            "value": winner["holdout"]["holdout_dti"],
            "ci95": winner["holdout"]["ci_95"],
            "withheld_positives": winner["holdout"]["n_withheld_positives"],
            "paired_best": {
                "baseline_id": "S13-PTHA-E3",
                "delta": winner["paired_vs_s13_e3"]["delta"],
                "ci95": winner["paired_vs_s13_e3"]["ci95"],
                "prob_positive": winner["paired_vs_s13_e3"]["prob_positive"],
                "n_paired_5km_tiles": winner["paired_vs_s13_e3"]["n_paired_5km_tiles"],
            },
            "per_fold": winner["holdout"]["folds"],
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-CONTROL-DTI (not competition leaderboard)",
            "value": sgmc_result["dti"],
            "r0_reference_value": r0_sgmc["dti"],
            "delta_vs_r0": round(sgmc_result["dti"] - r0_sgmc["dti"], 6),
            "n_offcatalogue_sgmc_positives": sgmc_result["n_offcatalogue_sgmc_positives"],
        },
        "canaries": {
            "status": "PASS",
            "n_features_checked": 85,
            "n_new_autocontext_features": 10,
            "max_symmetric_auc": round(worst_auc, 5),
            "worst_feature": worst_feature,
            "threshold": 0.90,
        },
        "registry_comparison": {
            "complete_universal_registry": False,
            "scope": "hash-distinct same-grid local fleet_registry + registry + retracted GEOD + docs downloads",
            "preplacement": {
                "status": pre_status,
                "checked": pre_full["n_registry_rasters_checked"],
                "not_checked_after_stop": 0,
            },
            "final": {
                "status": final_status,
                "checked": final_registry["n_registry_rasters_checked"],
                "not_checked_after_stop": 0,
            },
            "max_measured_surface_rank_correlation": pre_full["surface_max_abs_rank_corr"],
            "max_measured_final_dot_overlap_within_3px": final_registry["dots_max_3px_overlap"],
            "surface_closest_raster": pre_full["surface_closest_raster"],
            "dots_closest_raster": final_registry["dots_closest_raster"],
            "summary": final_summary,
        },
        "artifact": {
            "candidate_id": bundle["candidate_id"],
            "primary_zeros_tif": f"docs/downloads/{published_zeros.name}",
            "primary_zeros_sha256": bundle["primary_zeros_tif"]["sha256"],
            "primary_zeros_bytes": bundle["primary_zeros_tif"]["bytes"],
            "zip_bundle": bundle["zip_bundle"]["path"],
            "zip_sha256": bundle["zip_bundle"]["sha256"],
            "zip_bytes": bundle["zip_bundle"]["bytes"],
            "n_dots": bundle["dots"]["n_dots"],
            "dot_set_digest": bundle["dots"]["dot_set_digest"],
            "min_catalogue_distance_px": bundle["dots"]["min_catalogue_distance_px"],
        },
        "raster_sha256": bundle["primary_zeros_tif"]["sha256"],
        "validator_output": {
            "status": "PASS",
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "crs_shape_transform_match": True,
            "checks": {
                "gems91_gates_pass": bundle["validators"]["gems91_gates_verdict"] == "CERTIFIED",
                "release_gates_nan_pass": bundle["validators"]["release_gates_nan_pass"],
                "release_gates_zeros_pass": bundle["validators"]["release_gates_zeros_pass"],
                "validate_raster_nan_pass": bundle["validators"]["validate_raster_nan_pass"],
                "validate_raster_zeros_pass": bundle["validators"]["validate_raster_zeros_pass"],
                "gems57_pass": g57["all_checks_passed"],
                "zero_catalogue_overlap": bundle["dots"]["zero_catalogue_mass"],
                "min_300m_catalogue_clearance": bundle["dots"]["dots_le_3px"] == 0,
            },
            "all_cells_finite": bundle["primary_zeros_tif"]["all_cells_finite"],
            "nodata": bundle["primary_zeros_tif"]["nodata"],
            "min_value": bundle["primary_zeros_tif"]["min_value"],
            "max_value": bundle["primary_zeros_tif"]["max_value"],
        },
        "submission": {
            "name": submission_name,
            "note": note,
            "note_length": len(note),
            "recommended_upload_file": published_zeros.name if final_pass else None,
            "research_download_file": published_zeros.name,
            "zip_download": Path(bundle["zip_bundle"]["path"]).name,
        },
        "selector_approval": False,
        "selector_receipt": {
            "weekly_cap_verified": False,
            "slot_available": False,
            "note": "No live organizer account state was accessed and no slot was used.",
        },
        "technical_candidate_verdict": (
            "promote_to_selector" if beats_best and final_pass else "negative"
        ),
        "portal_submission_verdict": (
            "HOLD_PENDING_SELECTOR_SIGN_OFF" if beats_best and final_pass else "NOT_OK_TO_SUBMIT"
        ),
        "budget": {
            "experiments_executed": len(completed),
            "max_experiments": MAX_EXPERIMENTS,
            "elapsed_seconds": elapsed,
            "max_seconds": MAX_SECONDS,
        },
        "experiments": experiments,
        "full_map_emitter_last_gain": round(float(last_gain), 7),
        "organizer_confirmed_score": None,
    }
    card["readiness_gates"] = RD.gates(card)
    card["submission_ready"] = RD.submission_ready(card)
    RUN_CARD.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    EVIDENCE.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {RUN_CARD} and {published_zeros.name}; submission_ready={card['submission_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
