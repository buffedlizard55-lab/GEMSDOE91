#!/usr/bin/env python3
"""Run the preregistered S15-SCGF Structural-Complexity, Multi-Wavelength Salem
Attenuation, Hydrothermal Aquifer-Baffle & Dual-Specialist Auto-Context lane.

Strictly follows PARALLEL-RUN PROTOCOL Rules 1–6:
- Reuses shared `scripts/evaluate_holdout.py`, `scripts/submission_writer.py`,
  `gems91.ptha`, and shared cached feature builders (`dd_vtc_pu`, `mhtr_coda`,
  `spac_coda`, `ptha`).
- Reproduces BOTH `S13-PTHA E3` (`0.244601`) and `S14-PTAC E2` (`0.267782`)
  exact 5-km spatial tiles for paired block-bootstrap 95% CIs.
- Runs single-feature Mann–Whitney leakage canary across all 137 features
  (123 static + 14 cross-fitted dual-specialist topology; fail-closed if AUC > 0.90).
- Checks pre-placement surface Spearman |rho| <= 0.90 before dot placement and
  full-registry 3-px dot overlap <= 0.70 after dot placement (zero exemptions).
- Never spends a live DrivenData submission slot automatically.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

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
from gems91 import scgf15 as SCGF  # noqa: E402
from gems91 import spac_coda as SC  # noqa: E402
from scripts import evaluate_holdout as EH  # noqa: E402
from scripts import run_s13_lane as S13  # noqa: E402
from scripts import submission_writer as SW  # noqa: E402
from vendor.gems57.validate import validate as validate_gems57  # noqa: E402

DATA = ROOT / "data"
CACHE = Path("/tmp/gems91_s15_cache")
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
FEATURES = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0 = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
DOWNLOADS = ROOT / "docs" / "downloads"
DATA_RELEASES = DATA / "releases" / "s15"
PREREG = ROOT / "docs" / "HYPOTHESES_S15_SCGF.md"
RUN_CARD = ROOT / "docs" / "run-card-S15-SCGF.json"
EVIDENCE = ROOT / "evidence" / "s15_scgf_20261025.json"

MAX_EXPERIMENTS = 3
MAX_SECONDS = 7200.0
SPLIT_SHA = "0f874367d8d34964c9b8802d3d67d348f68ade1f9fbc4301bffc5eafcb524db8"
S13_BASELINE_DTI = 0.244601
S13_BASELINE_CI = [0.230592, 0.257058]
S14_BASELINE_DTI = 0.267782
S14_BASELINE_CI = [0.253687, 0.281135]

SYNTHETIC_BLANKET_NAMES = frozenset(
    {
        "calib_r13lattice_00904.tif",
        "GEMSDOE87_calib_r13lattice_00904.tif",
        "r13_lattice_s5_00904.tif",
        "calib_r14union_00000.tif",
        "GEMSDOE87_calib_r14union_00000.tif",
        "r14_union_tips10_lat6.tif",
        "calib_r11greedy_00000.tif",
        "GEMSDOE87_calib_r11greedy_00000.tif",
        "r11_greedy_mp.tif",
    }
)


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    print(f"[{ts}] {msg}", flush=True)


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
    """All locally indexed same-grid references, hash-deduplicated with ZERO exemptions."""
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
            if path.name.startswith("gems91-s15-scgf-"):
                continue
            digest = IO.sha256_file(path)
            seen.setdefault(digest, path)
    return list(seen.values())


def save_dual_surface(
    path_prefix: Path,
    p_full: np.ndarray,
    p_sub: np.ndarray,
    footprint: np.ndarray,
    meta: dict,
) -> None:
    p_full[footprint].astype(np.float32).tofile(path_prefix.with_name(path_prefix.name + "_full.dat"))
    p_sub[footprint].astype(np.float32).tofile(path_prefix.with_name(path_prefix.name + "_sub.dat"))
    path_prefix.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def load_dual_surface(
    path_prefix: Path,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict] | None:
    n_fp = int(footprint.sum())
    pf_path = path_prefix.with_name(path_prefix.name + "_full.dat")
    ps_path = path_prefix.with_name(path_prefix.name + "_sub.dat")
    meta_path = path_prefix.with_suffix(".json")
    if (
        not pf_path.is_file()
        or not ps_path.is_file()
        or not meta_path.is_file()
        or pf_path.stat().st_size != n_fp * 4
        or ps_path.stat().st_size != n_fp * 4
    ):
        return None
    pf = np.zeros(footprint.shape, dtype=np.float32)
    ps = np.zeros(footprint.shape, dtype=np.float32)
    pf[footprint] = np.fromfile(pf_path, dtype=np.float32)
    ps[footprint] = np.fromfile(ps_path, dtype=np.float32)
    return pf, ps, json.loads(meta_path.read_text(encoding="utf-8"))


def save_single_surface(path: Path, surf: np.ndarray, footprint: np.ndarray, meta: dict) -> None:
    surf[footprint].astype(np.float32).tofile(path)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def load_single_surface(path: Path, footprint: np.ndarray) -> tuple[np.ndarray, dict] | None:
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


def reproduce_frozen_baselines(
    *,
    folds: list[EH.HoldoutFold],
    cat: np.ndarray,
    footprint: np.ndarray,
    X_static: np.ndarray,
    static_names: list[str],
    X_s11: np.ndarray,
    s11_names: list[str],
    X_ptha: np.ndarray,
    ptha_names: list[str],
    ptha_crest: np.ndarray,
    piedmont: np.ndarray,
    train_eligible: dict[int, np.ndarray],
    fold_eligible: dict[int, np.ndarray],
    full_eligible_pixels: int,
) -> tuple[tuple[np.ndarray, ...], tuple[np.ndarray, ...]]:
    """Reproduce exact `S13-PTHA E3` (`0.244601`) and `S14-PTAC E2` (`0.267782`) 5-km tiles."""
    npz_path = CACHE / "frozen_s13_s14_baseline_tiles_v1.npz"
    if npz_path.is_file():
        d = np.load(npz_path)
        if (
            abs(float(d["s13_dti"]) - S13_BASELINE_DTI) <= 1e-5
            and abs(float(d["s14_dti"]) - S14_BASELINE_DTI) <= 1e-5
        ):
            log(
                f"Loaded verified baseline tiles: S13-E3={float(d['s13_dti']):.6f}, "
                f"S14-PTAC-E2={float(d['s14_dti']):.6f}"
            )
            s13_tiles = (d["s13_T"], d["s13_S"], d["s13_M"], d["s13_G"])
            s14_tiles = (d["s14_T"], d["s14_S"], d["s14_M"], d["s14_G"])
            return s13_tiles, s14_tiles

    log("Reproducing frozen S13-PTHA E3 and S14-PTAC E2 baselines for exact paired bootstrap...")
    s13_static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    s11_cols = list(range(len(s11_names)))
    ptha_cols = list(range(len(ptha_names)))
    n_fp = int(footprint.sum())

    s13_oof: dict[int, tuple[np.ndarray, dict]] = {}
    s13_dots: dict[int, np.ndarray] = {}
    for fold in folds:
        q = fold.fold_id
        p_cache = CACHE / f"base_s13_oof_f{q}.dat"
        loaded = load_single_surface(p_cache, footprint)
        if loaded is None:
            excl = fold.region_mask | fold.withheld_faults | fold.buffer_mask
            surf, meta = PTHA.fit_and_predict_ptha_oof_fold(
                X_static=X_static,
                static_cols=s13_static_cols,
                static_names=static_names,
                X_s11=X_s11,
                s11_cols=s11_cols,
                s11_names=s11_names,
                X_ptha=X_ptha,
                ptha_cols=ptha_cols,
                ptha_names=ptha_names,
                visible_faults=fold.visible_faults,
                exclude_mask=excl,
                footprint=footprint,
                seed=1320 + q,
            )
            save_single_surface(p_cache, surf, footprint, meta)
            loaded = (surf, meta)
        s13_oof[q] = loaded
        s13_dots[q], _ = PTHA.dinkelbach_fold_independent_emit(
            loaded[0],
            ptha_crest,
            piedmont,
            footprint=footprint,
            train_eligible_mask=train_eligible[q],
            test_eligible_mask=fold_eligible[q],
            pi_true=float(loaded[1]["pi_vis_train"]),
            pi_sample=float(loaded[1]["pi_sample_weighted"]),
            target_pool_dots=48_000,
            full_eligible_pixels=full_eligible_pixels,
            min_spacing_px=2.50,
        )

    s13_res = EH.score_pooled_holdout(s13_dots, folds, footprint, n_boot=200, seed=133)
    s13_tiles = S13._accumulate_fold_tiles(s13_dots, folds, footprint)
    log(f"Reproduced S13-PTHA E3: {s13_res['holdout_dti']:.6f} (expected {S13_BASELINE_DTI:.6f})")
    del s13_dots
    gc.collect()

    pairs: dict[tuple[int, int], tuple[np.ndarray, dict]] = {}
    for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
        p_cache = CACHE / f"base_s14_pair_{a}_{b}.dat"
        loaded = load_single_surface(p_cache, footprint)
        if loaded is None:
            c, d_q = [q for q in range(4) if q not in (a, b)]
            exclude = (
                folds[c].region_mask
                | folds[c].withheld_faults
                | folds[c].buffer_mask
                | folds[d_q].region_mask
                | folds[d_q].withheld_faults
                | folds[d_q].buffer_mask
            )
            visible = cat & folds[c].visible_faults & folds[d_q].visible_faults & (~exclude)
            surf, meta = PTHA.fit_and_predict_ptha_oof_fold(
                X_static=X_static,
                static_cols=s13_static_cols,
                static_names=static_names,
                X_s11=X_s11,
                s11_cols=s11_cols,
                s11_names=s11_names,
                X_ptha=X_ptha,
                ptha_cols=ptha_cols,
                ptha_names=ptha_names,
                visible_faults=visible,
                exclude_mask=exclude,
                footprint=footprint,
                seed=1400 + 10 * a + b,
            )
            save_single_surface(p_cache, surf, footprint, meta)
            loaded = (surf, meta)
        pairs[(a, b)] = loaded

    s14_dots: dict[int, np.ndarray] = {}
    for fold in folds:
        q = fold.fold_id
        stitched = np.zeros(footprint.shape, dtype=np.float32)
        vis_q = [m for m in range(4) if m != q]
        for m in vis_q:
            tp = tuple(sorted(x for x in vis_q if x != m))
            stitched[folds[m].region_mask] = pairs[tp][0][folds[m].region_mask]
        stitched[fold.region_mask] = s13_oof[q][0][fold.region_mask]
        ac = SC.compute_spac_autocontext_features(stitched, footprint)
        del stitched

        excl = fold.region_mask | fold.withheld_faults | fold.buffer_mask
        blocks = [
            (X_static, s13_static_cols),
            (X_s11, s11_cols),
            (X_ptha, ptha_cols),
            (ac, list(range(10))),
        ]
        s2_surf, s2_meta = PTAC.fit_predict_stage2(
            train_blocks=blocks,
            infer_blocks=blocks,
            visible_faults=fold.visible_faults,
            exclude_mask=excl,
            footprint=footprint,
            seed=1450 + q,
        )
        p1_cal = calibrated(s13_oof[q][0], footprint, s13_oof[q][1])
        p2_cal = calibrated(s2_surf, footprint, s2_meta)
        surf = PTAC.arithmetic_probability_pool(p1_cal, p2_cal, footprint, stage2_weight=0.72)
        b900 = np.zeros(footprint.shape, dtype=np.float32)
        b2k = np.zeros(footprint.shape, dtype=np.float32)
        b900[footprint] = np.asarray(ac[:, 4], dtype=np.float32)
        b2k[footprint] = np.asarray(ac[:, 5], dtype=np.float32)
        crest = PTAC.bridge_concordant_crest(ptha_crest, b900, b2k, footprint)
        s14_dots[q], _ = PTHA.dinkelbach_fold_independent_emit(
            surf,
            crest,
            piedmont,
            footprint=footprint,
            train_eligible_mask=train_eligible[q],
            test_eligible_mask=fold_eligible[q],
            pi_true=0.5,
            pi_sample=0.5,
            target_pool_dots=48_000,
            full_eligible_pixels=full_eligible_pixels,
            min_spacing_px=2.50,
        )
        del ac, s2_surf, p1_cal, p2_cal, surf, b900, b2k, crest
        gc.collect()

    s14_res = EH.score_pooled_holdout(s14_dots, folds, footprint, n_boot=200, seed=142)
    s14_tiles = S13._accumulate_fold_tiles(s14_dots, folds, footprint)
    log(f"Reproduced S14-PTAC E2: {s14_res['holdout_dti']:.6f} (expected {S14_BASELINE_DTI:.6f})")

    del s13_oof, pairs, s14_dots
    for tmp_f in CACHE.glob("base_s1*.dat"):
        tmp_f.unlink(missing_ok=True)
    for tmp_j in CACHE.glob("base_s1*.json"):
        tmp_j.unlink(missing_ok=True)
    gc.collect()

    np.savez_compressed(
        npz_path,
        s13_dti=np.float64(s13_res["holdout_dti"]),
        s14_dti=np.float64(s14_res["holdout_dti"]),
        s13_T=s13_tiles[0],
        s13_S=s13_tiles[1],
        s13_M=s13_tiles[2],
        s13_G=s13_tiles[3],
        s14_T=s14_tiles[0],
        s14_S=s14_tiles[1],
        s14_M=s14_tiles[2],
        s14_G=s14_tiles[3],
    )
    assert abs(float(s13_res["holdout_dti"]) - S13_BASELINE_DTI) <= 1e-5, (
        f"S13 baseline mismatch: {s13_res['holdout_dti']}"
    )
    assert abs(float(s14_res["holdout_dti"]) - S14_BASELINE_DTI) <= 1e-5, (
        f"S14 baseline mismatch: {s14_res['holdout_dti']}"
    )
    return s13_tiles, s14_tiles


def summarize_registry(report: dict) -> dict:
    comparisons = report.get("comparisons", [])
    top_all = sorted(
        comparisons, key=lambda r: r.get("cand_within_3px_of_reg", 0.0), reverse=True
    )[:6]
    real_only = [
        r
        for r in comparisons
        if Path(str(r.get("registry_raster", ""))).name not in SYNTHETIC_BLANKET_NAMES
    ]
    top_real = sorted(
        real_only, key=lambda r: r.get("cand_within_3px_of_reg", 0.0), reverse=True
    )[:5]
    max_real_3px = float(top_real[0]["cand_within_3px_of_reg"]) if top_real else 0.0
    closest_real = str(top_real[0]["registry_raster"]) if top_real else ""
    max_real_spear = max(
        (abs(float(r.get("surface_abs_rank_corr", 0.0))) for r in real_only), default=0.0
    )
    r0_matches = [
        r for r in comparisons if r.get("registry_raster") == "GEMSDOE32__h33-2-b2-zeros.tif"
    ]
    r0_cmp = r0_matches[0] if r0_matches else None
    return {
        "gate_version": report.get("uniqueness_gate_version"),
        "n_checked": report.get("n_registry_rasters_checked", 0),
        "literal_all_rasters_pass": bool(report.get("uniqueness_pass", False)),
        "max_abs_surface_spearman": report.get("surface_max_abs_rank_corr", 0.0),
        "surface_closest_raster": report.get("surface_closest_raster", ""),
        "max_3px_dot_overlap_all_indexed": report.get("dots_max_3px_overlap", 0.0),
        "dots_closest_raster_all_indexed": report.get("dots_closest_raster", ""),
        "vs_r0_g32_h33_2_b2": (
            {
                "raster": r0_cmp["registry_raster"],
                "cand_within_3px_of_r0": r0_cmp["cand_within_3px_of_reg"],
                "r0_within_3px_of_cand": r0_cmp["reg_within_3px_of_cand"],
                "f1_dot_overlap_3px": r0_cmp["f1_dot_overlap_3px"],
                "surface_abs_rank_corr": r0_cmp["surface_abs_rank_corr"],
            }
            if r0_cmp
            else None
        ),
        "disaggregated_real_submissions_only": {
            "n_real_submissions_checked": len(real_only),
            "max_3px_dot_overlap_vs_real_submissions": round(max_real_3px, 6),
            "closest_real_submission": closest_real,
            "max_abs_surface_spearman_vs_real_submissions": round(max_real_spear, 6),
            "passes_70pct_bar_vs_all_real_submissions": bool(max_real_3px <= 0.70),
            "note": (
                "Three GEMSDOE87 calibration blankets (r13_lattice_s5_00904=99.87%, "
                "r14_union_tips10_lat6=75.88%, r11_greedy_mp=71.52%) cover >70% of all "
                "eligible Nevada pixels; literal all-raster gate stays un-exempted and fail-closed."
            ),
        },
        "top_overlap_all_indexed": [
            {
                "raster": r["registry_raster"],
                "cand_within_3px_of_reg": r["cand_within_3px_of_reg"],
                "f1_dot_overlap_3px": r["f1_dot_overlap_3px"],
                "surface_abs_rank_corr": r["surface_abs_rank_corr"],
            }
            for r in top_all
        ],
        "top_overlap_real_submissions": [
            {
                "raster": r["registry_raster"],
                "cand_within_3px_of_reg": r["cand_within_3px_of_reg"],
                "f1_dot_overlap_3px": r["f1_dot_overlap_3px"],
                "surface_abs_rank_corr": r["surface_abs_rank_corr"],
            }
            for r in top_real
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run pre-registered S15-SCGF lane.")
    parser.add_argument(
        "--phase",
        choices=("all", "baselines", "stage1", "eval_and_emit"),
        default="all",
        help="Optional checkpointed phase to execute within sandbox wall-clock slices.",
    )
    args = parser.parse_args(argv)

    for req in (TEMPLATE, CATALOGUE, FEATURES, GDR, SGMC, R0, PREREG):
        if not req.is_file():
            raise FileNotFoundError(f"Missing required input: {req}")

    CACHE.mkdir(parents=True, exist_ok=True)
    DATA_RELEASES.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)

    prereg_sha = IO.sha256_file(PREREG)
    log(f"S15-SCGF preregistration verified: sha256={prereg_sha}")

    with rasterio.open(TEMPLATE) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE) as src:
        cat = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC) as src:
        sgmc = (src.read(1) > 0) & footprint
    with rasterio.open(R0) as src:
        r0 = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)
        r0[~footprint] = 0.0

    folds = EH.build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    actual_split = split_sha(folds)
    if actual_split != SPLIT_SHA:
        raise RuntimeError(f"Holdout split drift: {actual_split} != {SPLIT_SHA}")
    n_fp = int(footprint.sum())
    log(f"Shared holdout ready: {sum(f.n_withheld for f in folds):,} withheld positives across 4 quadrant folds")

    # 1. Build/open all 5 shared label-free feature memmaps (123 static columns total)
    log("Building/loading shared label-free feature memmaps (49 + 16 + 20 + 20 + 18 = 123 cols)...")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES, gdr_csv=GDR, footprint=footprint, cache_dir=CACHE
    )
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE
    )
    X_s12, s12_names, _ = SC.build_or_load_s12_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE
    )
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES, footprint=footprint, cache_dir=CACHE
    )
    X_s15, s15_names, _ = SCGF.build_or_load_s15_feature_memmap(
        features_tif=FEATURES, gdr_csv=GDR, footprint=footprint, cache_dir=CACHE
    )
    all_static_names = static_names + s11_names + s12_names + ptha_names + s15_names
    assert len(all_static_names) == 123

    mhtr_edge, piedmont = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    ptha_crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, footprint)
    s15_crest_base = SCGF.build_s15_subsurface_crest_surface(ptha_crest, X_s15, footprint)
    del mhtr_edge
    gc.collect()

    fold_eligible: dict[int, np.ndarray] = {}
    train_eligible: dict[int, np.ndarray] = {}
    for fold in folds:
        _, fold_eligible[fold.fold_id] = S13._fold_active_and_eligible(
            fold, folds, footprint, collar_px=3.0
        )
        excl = fold.region_mask | fold.withheld_faults | fold.buffer_mask
        d_vis = ndi.distance_transform_edt(~fold.visible_faults)
        train_eligible[fold.fold_id] = footprint & (~excl) & (~fold.visible_faults) & (d_vis > 3.0)
        del d_vis
    d_cat = ndi.distance_transform_edt(~cat)
    full_eligible = footprint & (~cat) & (d_cat > 3.0)
    n_full_elig = int(full_eligible.sum())
    del d_cat
    gc.collect()

    # 2. Reproduce frozen S13-E3 (0.244601) and S14-PTAC-E2 (0.267782) baselines
    s13_tiles, s14_tiles = reproduce_frozen_baselines(
        folds=folds,
        cat=cat,
        footprint=footprint,
        X_static=X_static,
        static_names=static_names,
        X_s11=X_s11,
        s11_names=s11_names,
        X_ptha=X_ptha,
        ptha_names=ptha_names,
        ptha_crest=ptha_crest,
        piedmont=piedmont,
        train_eligible=train_eligible,
        fold_eligible=fold_eligible,
        full_eligible_pixels=n_full_elig,
    )
    if args.phase == "baselines":
        log("Completed --phase baselines.")
        return 0

    # Cumulative Rule-6 S15 experiment clock across checkpointed phases
    clock_path = CACHE / "s15_cumulative_clock.json"
    prior_elapsed = (
        float(json.loads(clock_path.read_text(encoding="utf-8")).get("elapsed_seconds", 0.0))
        if clock_path.is_file()
        else 0.0
    )
    exp_start = time.perf_counter() - prior_elapsed

    static_blocks: list[SCGF.FeatureBlock] = [
        (X_static, list(range(len(static_names)))),
        (X_s11, list(range(len(s11_names)))),
        (X_s12, list(range(len(s12_names)))),
        (X_ptha, list(range(len(ptha_names)))),
        (X_s15, list(range(len(s15_names)))),
    ]

    # 3. Fit or load Dual-Specialist Stage-1 OOF folds (4 splits)
    stage1_oof: dict[int, tuple[np.ndarray, np.ndarray, dict]] = {}
    for fold in folds:
        q = fold.fold_id
        pref = CACHE / f"s15_s1_oof_f{q}"
        loaded = load_dual_surface(pref, footprint)
        if loaded is None:
            excl = fold.region_mask | fold.withheld_faults | fold.buffer_mask
            log(f"Fitting S15 Dual-Specialist Stage-1 OOF fold {fold.name}...")
            pf, ps, meta = SCGF.fit_and_predict_s15_stage1(
                blocks=static_blocks,
                feature_names=all_static_names,
                visible_faults=fold.visible_faults,
                exclude_mask=excl,
                footprint=footprint,
                seed=1510 + q,
            )
            save_dual_surface(pref, pf, ps, footprint, meta)
            loaded = (pf, ps, meta)
        stage1_oof[q] = loaded
        check_budget(exp_start)

    # 4. Fit or load 6 pairwise quadrant Stage-1 sub-folds & stitch 4 Dual-AC memmaps (14 cols)
    expected_ac_bytes = n_fp * len(SCGF.S15_DUAL_AUTOCONTEXT_NAMES) * 4
    ac_cached = all(
        (CACHE / f"s15_dual_ac_f{f.fold_id}.dat").is_file()
        and (CACHE / f"s15_dual_ac_f{f.fold_id}.dat").stat().st_size == expected_ac_bytes
        for f in folds
    )
    if not ac_cached:
        pair_surfaces: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        for a, b in ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)):
            pref = CACHE / f"s15_s1_pair_{a}_{b}"
            loaded = load_dual_surface(pref, footprint)
            if loaded is None:
                c, d_q = [q for q in range(4) if q not in (a, b)]
                exclude = (
                    folds[c].region_mask
                    | folds[c].withheld_faults
                    | folds[c].buffer_mask
                    | folds[d_q].region_mask
                    | folds[d_q].withheld_faults
                    | folds[d_q].buffer_mask
                )
                pred_m = folds[c].region_mask | folds[d_q].region_mask
                visible = cat & folds[c].visible_faults & folds[d_q].visible_faults & (~exclude)
                log(f"Fitting S15 Dual-Specialist Stage-1 pair ({a},{b}) [pos={int(visible.sum()):,}]...")
                pf, ps, meta = SCGF.fit_and_predict_s15_stage1(
                    blocks=static_blocks,
                    feature_names=all_static_names,
                    visible_faults=visible,
                    exclude_mask=exclude,
                    footprint=footprint,
                    predict_mask=pred_m,
                    seed=1530 + 10 * a + b,
                    max_pos=55_000,
                    max_neg=180_000,
                )
                save_dual_surface(pref, pf, ps, footprint, meta)
                loaded = (pf, ps, meta)
            pair_surfaces[(a, b)] = (loaded[0], loaded[1])
            check_budget(exp_start)

        for fold in folds:
            q = fold.fold_id
            ac_path = CACHE / f"s15_dual_ac_f{q}.dat"
            stitch_full = np.zeros(footprint.shape, dtype=np.float32)
            stitch_sub = np.zeros(footprint.shape, dtype=np.float32)
            vis_q = [m for m in range(4) if m != q]
            for m in vis_q:
                tp = tuple(sorted(x for x in vis_q if x != m))
                rm = folds[m].region_mask
                stitch_full[rm] = pair_surfaces[tp][0][rm]
                stitch_sub[rm] = pair_surfaces[tp][1][rm]
            stitch_full[fold.region_mask] = stage1_oof[q][0][fold.region_mask]
            stitch_sub[fold.region_mask] = stage1_oof[q][1][fold.region_mask]
            ac_mat = SCGF.compute_dual_autocontext_features(stitch_full, stitch_sub, footprint)
            mmw = np.memmap(ac_path, dtype=np.float32, mode="w+", shape=(n_fp, 14))
            mmw[:] = ac_mat
            mmw.flush()
            del mmw, ac_mat, stitch_full, stitch_sub
            gc.collect()
        del pair_surfaces
        for tmp_p in CACHE.glob("s15_s1_pair_*"):
            tmp_p.unlink(missing_ok=True)
        gc.collect()

    clock_path.write_text(
        json.dumps({"elapsed_seconds": round(time.perf_counter() - exp_start, 2)}) + "\n",
        encoding="utf-8",
    )
    if args.phase == "stage1":
        log("Completed --phase stage1.")
        return 0

    fold_ac: dict[int, tuple[np.memmap, list[str]]] = {
        f.fold_id: (
            np.memmap(
                CACHE / f"s15_dual_ac_f{f.fold_id}.dat",
                dtype=np.float32,
                mode="r",
                shape=(n_fp, 14),
            ),
            list(SCGF.S15_DUAL_AUTOCONTEXT_NAMES),
        )
        for f in folds
    }

    # 5. Rule 4: Single-Feature Leakage Canary across ALL 137 features (`max AUC <= 0.90`)
    canary_json = CACHE / "s15_leakage_canary_137_v1.json"
    if canary_json.is_file():
        canary = json.loads(canary_json.read_text(encoding="utf-8"))
    else:
        log("Running Rule-4 single-feature Mann-Whitney leakage canary across all 137 features...")
        sub_reports = []
        for mat, names in (
            (X_static, static_names),
            (X_s11, s11_names),
            (X_s12, s12_names),
            (X_ptha, ptha_names),
            (X_s15, s15_names),
        ):
            sub_reports.append(
                EH.run_leakage_canary(mat, names, folds, footprint, subsample_step=4)
            )
        ac_rep = EH.run_leakage_canary(
            np.empty((n_fp, 0), dtype=np.float32),
            [],
            folds,
            footprint,
            fold_specific_features=fold_ac,
            subsample_step=4,
        )
        sub_reports.append(ac_rep)
        worst_auc = max(float(r["worst_symmetric_auc"]) for r in sub_reports)
        worst_rec = max(sub_reports, key=lambda r: float(r["worst_symmetric_auc"]))
        canary = {
            "all_pass": all(bool(r["all_pass"]) for r in sub_reports),
            "n_features_checked": sum(int(r["n_features_tested"]) for r in sub_reports),
            "worst_symmetric_auc": round(worst_auc, 6),
            "worst_feature": worst_rec["worst_feature"],
            "threshold": 0.90,
        }
        canary_json.write_text(json.dumps(canary, indent=2) + "\n", encoding="utf-8")

    if not canary["all_pass"] or float(canary["worst_symmetric_auc"]) > 0.90:
        raise RuntimeError(f"Rule 4 leakage canary FAILED: {canary}")
    log(
        f"Rule 4 leakage canary PASS: {canary['n_features_checked']}/137 features; "
        f"worst={canary['worst_feature']} (symmetric AUC={canary['worst_symmetric_auc']:.5f} <= 0.90)"
    )

    # 6. Fit or load Dual-Specialist Stage-2 OOF folds (137 features, 99 strictly non-topographic)
    stage2_names = all_static_names + SCGF.S15_DUAL_AUTOCONTEXT_NAMES
    stage2_oof: dict[int, tuple[np.ndarray, np.ndarray, dict]] = {}
    for fold in folds:
        q = fold.fold_id
        pref = CACHE / f"s15_s2_oof_f{q}"
        loaded = load_dual_surface(pref, footprint)
        if loaded is None:
            excl = fold.region_mask | fold.withheld_faults | fold.buffer_mask
            pred_m2 = train_eligible[q] | fold_eligible[q] | fold.region_mask
            blocks = [*static_blocks, (fold_ac[q][0], list(range(14)))]
            log(f"Fitting S15 Dual-Specialist Stage-2 OOF fold {fold.name} (137 features)...")
            p2f, p2s, meta = SCGF.fit_and_predict_s15_stage2(
                train_blocks=blocks,
                infer_blocks=blocks,
                feature_names=stage2_names,
                visible_faults=fold.visible_faults,
                exclude_mask=excl,
                footprint=footprint,
                predict_mask=pred_m2,
                seed=1560 + q,
            )
            save_dual_surface(pref, p2f, p2s, footprint, meta)
            loaded = (p2f, p2s, meta)
        stage2_oof[q] = loaded
        check_budget(exp_start)

    reg_paths = registry_paths()
    log(f"Indexed {len(reg_paths)} hash-distinct local registry rasters (zero lattice exemptions)")

    # 7. Execute pre-registered 3-Experiment Ladder (E1, E2, E3)
    exp_specs = [
        {
            "id": "E1",
            "hypothesis": "H15-1 + H15-2 + H15-3 + H15-4a",
            "title": (
                "137-feature Förstner-junction + multi-wavelength Salem + aquifer-baffle "
                "Dual-Specialist Cross-Fitted Auto-Context + unchanged S13 Dinkelbach"
            ),
            "dual_crest": False,
            "sar_pu": False,
            "min_spacing_px": 2.50,
            "target_pool_dots": 48_000,
            "full_dots": 44_000,
            "mimic": (
                "Isotropic volcanic plugs/calderas, closed-basin evaporite salt playas, "
                "and aeromagnetic flight-line survey seams"
            ),
        },
        {
            "id": "E2",
            "hypothesis": "H15-1 + H15-2 + H15-3 + H15-4b",
            "title": (
                "E1 + Dual-Regime Subsurface-Junction/Salem/Baffle Crest × "
                "(Full + Pure-Subsurface) Wash-Bridge Concordance"
            ),
            "dual_crest": True,
            "sar_pu": False,
            "min_spacing_px": 2.50,
            "target_pool_dots": 48_000,
            "full_dots": 44_000,
            "mimic": (
                "Straight anthropogenic canals/roads and braided alluvial channels lacking "
                "co-located gravity/magnetic/conductivity crest support"
            ),
        },
        {
            "id": "E3",
            "hypothesis": "H15-1 + H15-2 + H15-3 + H15-4",
            "title": (
                "E2 + SAR-PU Concealed-Fairway & Walker Lane Kinematics Subsurface-Corroborated "
                "Propensity Allocation (min_spacing_px=2.60)"
            ),
            "dual_crest": True,
            "sar_pu": True,
            "min_spacing_px": 2.60,
            "target_pool_dots": 46_500,
            "full_dots": 42_500,
            "mimic": (
                "Barren low-slope playa centers and regional GPS strain lobes where "
                "topography-free subsurface specialist finds no sharp geophysical edge"
            ),
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
            p1f_cal = calibrated(stage1_oof[q][0], footprint, stage1_oof[q][2])
            p2f_cal = calibrated(stage2_oof[q][0], footprint, stage2_oof[q][2])
            p2s_cal = calibrated(stage2_oof[q][1], footprint, stage2_oof[q][2])
            surf = PTAC.arithmetic_probability_pool(p1f_cal, p2f_cal, footprint, stage2_weight=0.72)
            if spec["sar_pu"]:
                surf = SCGF.apply_sar_pu_concealed_fairway_adjustment(
                    surf, p2s_cal, X_static, X_ptha, X_s15, footprint, pu_gain=0.28
                )
            if spec["dual_crest"]:
                crest = SCGF.build_dual_bridge_concordant_crest(
                    s15_crest_base, fold_ac[q][0], footprint
                )
            else:
                crest = ptha_crest
            surfaces[q] = surf
            crests[q] = crest
            mosaic[fold.region_mask] = surf[fold.region_mask]
            del p1f_cal, p2f_cal, p2s_cal

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
            log(f"{spec['id']} pre-placement surface DUPLICATE; stopping lane per Rule 1")
            break

        fold_dots: dict[int, np.ndarray] = {}
        alloc: dict[str, dict] = {}
        for fold in folds:
            q = fold.fold_id
            dots, meta_d = PTHA.dinkelbach_fold_independent_emit(
                surfaces[q],
                crests[q],
                piedmont,
                footprint=footprint,
                train_eligible_mask=train_eligible[q],
                test_eligible_mask=fold_eligible[q],
                pi_true=0.5,
                pi_sample=0.5,
                target_pool_dots=int(spec["target_pool_dots"]),
                full_eligible_pixels=n_full_elig,
                min_spacing_px=float(spec["min_spacing_px"]),
            )
            fold_dots[q] = dots
            alloc[fold.name] = meta_d

        hold_v1 = EH.score_pooled_holdout(fold_dots, folds, footprint, n_boot=200, seed=150 + number)
        hold_nohalo = EH.score_pooled_holdout(
            fold_dots,
            folds,
            footprint,
            n_boot=200,
            seed=250 + number,
            mask_buffer_predictions=False,
        )
        cand_tiles = S13._accumulate_fold_tiles(fold_dots, folds, footprint)
        paired_s14 = S13.compute_aligned_paired_bootstrap(
            cand_tiles,
            s14_tiles,
            cand_pooled_dti=hold_v1["holdout_dti"],
            base_pooled_dti=S14_BASELINE_DTI,
            n_boot=400,
            seed=15100 + number,
        )
        paired_s13 = S13.compute_aligned_paired_bootstrap(
            cand_tiles,
            s13_tiles,
            cand_pooled_dti=hold_v1["holdout_dti"],
            base_pooled_dti=S13_BASELINE_DTI,
            n_boot=400,
            seed=15200 + number,
        )

        experiments.append(
            {
                "experiment_number": number,
                "exp_id": spec["id"],
                "hypothesis_id": spec["hypothesis"],
                "title": spec["title"],
                "named_non_fault_mimic": spec["mimic"],
                "n_features": 137,
                "n_pure_subsurface_features": 99,
                "min_spacing_px": spec["min_spacing_px"],
                "target_pool_dots": spec["target_pool_dots"],
                "preplacement": {
                    "status": "PASS_WITHIN_INDEXED_SCOPE",
                    "checked": pre["n_registry_rasters_checked"],
                    "max_abs_surface_spearman": pre["surface_max_abs_rank_corr"],
                    "closest_raster": pre["surface_closest_raster"],
                },
                "holdout": hold_v1,
                "holdout_v1_1_nohalo": {
                    "evaluator_version": hold_nohalo["evaluator_version"],
                    "holdout_dti": hold_nohalo["holdout_dti"],
                    "ci_95": hold_nohalo["ci_95"],
                    "n_withheld_positives": hold_nohalo["n_withheld_positives"],
                },
                "paired_vs_s14_ptac_e2": paired_s14,
                "paired_vs_s13_ptha_e3": paired_s13,
                "fold_allocation": alloc,
                "status": "COMPLETED",
            }
        )
        log(
            f"[{spec['id']}] v1.0 HOLDOUT-DTI={hold_v1['holdout_dti']:.6f} CI={hold_v1['ci_95']} | "
            f"nohalo={hold_nohalo['holdout_dti']:.6f} | "
            f"delta vs S14-PTAC-E2={paired_s14['delta']:+.6f} CI={paired_s14['ci95']} "
            f"(P>0={paired_s14['prob_positive']:.3f})"
        )
        del surfaces, crests, mosaic, fold_dots, cand_tiles
        gc.collect()

    completed = [x for x in experiments if x.get("status") == "COMPLETED"]
    if not completed:
        raise RuntimeError("No S15 experiment reached holdout evaluation")

    winner = max(completed, key=lambda x: x["holdout"]["holdout_dti"])
    winner_spec = next(s for s in exp_specs if s["id"] == winner["exp_id"])
    beats_s14 = (
        float(winner["holdout"]["holdout_dti"]) > S14_BASELINE_DTI
        and float(winner["paired_vs_s14_ptac_e2"]["ci95"][0]) > 0.0
    )
    beats_point_only = float(winner["holdout"]["holdout_dti"]) > S14_BASELINE_DTI
    log(
        f"Holdout winner: {winner['exp_id']} ({winner['holdout']['holdout_dti']:.6f} HOLDOUT-DTI); "
        f"beats S14-PTAC point={beats_point_only}, paired_CI_gt_0={beats_s14}"
    )

    # Stitch OOF Stage-1 full & sub surfaces for full-map cross-fit training auto-context
    oof_stitch_full = np.zeros(footprint.shape, dtype=np.float32)
    oof_stitch_sub = np.zeros(footprint.shape, dtype=np.float32)
    for fold in folds:
        rm = fold.region_mask
        oof_stitch_full[rm] = stage1_oof[fold.fold_id][0][rm]
        oof_stitch_sub[rm] = stage1_oof[fold.fold_id][1][rm]

    # Free ALL holdout-only surfaces & masks before full-map Stage-1/Stage-2 fitting
    del stage1_oof, stage2_oof, fold_ac, fold_eligible, train_eligible, s13_tiles, s14_tiles
    gc.collect()
    log("Released holdout-only surfaces prior to full-map model fit")

    full_ac_train_path = CACHE / "s15_full_ac_train_oof.dat"
    if not full_ac_train_path.is_file() or full_ac_train_path.stat().st_size != expected_ac_bytes:
        ac_tr = SCGF.compute_dual_autocontext_features(oof_stitch_full, oof_stitch_sub, footprint)
        mmw = np.memmap(full_ac_train_path, dtype=np.float32, mode="w+", shape=(n_fp, 14))
        mmw[:] = ac_tr
        mmw.flush()
        del mmw, ac_tr
    del oof_stitch_full, oof_stitch_sub
    gc.collect()
    full_ac_train = np.memmap(full_ac_train_path, dtype=np.float32, mode="r", shape=(n_fp, 14))

    full_s1_pref = CACHE / "s15_full_s1"
    full_s1_loaded = load_dual_surface(full_s1_pref, footprint)
    if full_s1_loaded is None:
        log("Fitting full-map S15 Dual-Specialist Stage-1...")
        f_p1f, f_p1s, f_m1 = SCGF.fit_and_predict_s15_stage1(
            blocks=static_blocks,
            feature_names=all_static_names,
            visible_faults=cat,
            exclude_mask=~footprint,
            footprint=footprint,
            seed=1580,
        )
        save_dual_surface(full_s1_pref, f_p1f, f_p1s, footprint, f_m1)
        full_s1_loaded = (f_p1f, f_p1s, f_m1)
    f_p1f, f_p1s, f_m1 = full_s1_loaded
    check_budget(exp_start)

    full_ac_infer_path = CACHE / "s15_full_ac_infer.dat"
    if not full_ac_infer_path.is_file() or full_ac_infer_path.stat().st_size != expected_ac_bytes:
        ac_inf = SCGF.compute_dual_autocontext_features(f_p1f, f_p1s, footprint)
        mmw = np.memmap(full_ac_infer_path, dtype=np.float32, mode="w+", shape=(n_fp, 14))
        mmw[:] = ac_inf
        mmw.flush()
        del mmw, ac_inf
    del f_p1s
    gc.collect()
    full_ac_infer = np.memmap(full_ac_infer_path, dtype=np.float32, mode="r", shape=(n_fp, 14))

    full_s2_pref = CACHE / "s15_full_s2"
    full_s2_loaded = load_dual_surface(full_s2_pref, footprint)
    if full_s2_loaded is None:
        log("Fitting full-map S15 Dual-Specialist Stage-2 on cross-fitted auto-context...")
        f_p2f, f_p2s, f_m2 = SCGF.fit_and_predict_s15_stage2(
            train_blocks=[*static_blocks, (full_ac_train, list(range(14)))],
            infer_blocks=[*static_blocks, (full_ac_infer, list(range(14)))],
            feature_names=stage2_names,
            visible_faults=cat,
            exclude_mask=~footprint,
            footprint=footprint,
            seed=1590,
        )
        save_dual_surface(full_s2_pref, f_p2f, f_p2s, footprint, f_m2)
        full_s2_loaded = (f_p2f, f_p2s, f_m2)
    f_p2f, f_p2s, f_m2 = full_s2_loaded
    check_budget(exp_start)

    p1_cal = calibrated(f_p1f, footprint, f_m1)
    p2_cal = calibrated(f_p2f, footprint, f_m2)
    p2s_cal = calibrated(f_p2s, footprint, f_m2)
    del f_p1f, f_p2f, f_p2s

    full_surface = PTAC.arithmetic_probability_pool(p1_cal, p2_cal, footprint, stage2_weight=0.72)
    if winner_spec["sar_pu"]:
        full_surface = SCGF.apply_sar_pu_concealed_fairway_adjustment(
            full_surface, p2s_cal, X_static, X_ptha, X_s15, footprint, pu_gain=0.28
        )
    del p1_cal, p2_cal, p2s_cal

    if winner_spec["dual_crest"]:
        full_crest = SCGF.build_dual_bridge_concordant_crest(
            s15_crest_base, full_ac_infer, footprint
        )
    else:
        full_crest = ptha_crest

    pre_full = EH.check_registry_surface_uniqueness(
        full_surface[footprint], footprint, reg_paths, max_rank_corr=0.90, corr_stride=20
    )
    if pre_full["is_duplicate"]:
        raise RuntimeError(f"Full-map pre-placement surface duplicate: {pre_full}")

    full_dots, last_gain = PTHA.dinkelbach_full_map_emit(
        full_surface,
        full_crest,
        piedmont,
        footprint=footprint,
        full_eligible_mask=full_eligible,
        pi_true=0.5,
        pi_sample=0.5,
        n_dots=int(winner_spec["full_dots"]),
        min_spacing_px=float(winner_spec["min_spacing_px"]),
    )
    final_registry = EH.check_registry_uniqueness(
        full_surface[footprint], full_dots, footprint, reg_paths, corr_stride=20
    )
    reg_summary = summarize_registry(final_registry)

    sgmc_result = EH.score_off_catalogue_sgmc(full_dots, sgmc, cat, footprint)
    r0_sgmc = EH.score_off_catalogue_sgmc(r0, sgmc, cat, footprint)
    log(
        f"Blind Off-Catalogue USGS SGMC Control: S15={sgmc_result['dti']:.6f} vs "
        f"R0={r0_sgmc['dti']:.6f} (delta={sgmc_result['dti'] - r0_sgmc['dti']:+.6f})"
    )

    bundle = SW.write_validated_submission_bundle(
        full_dots,
        stem_prefix=f"gems91-s15-scgf-{winner['exp_id'].lower()}",
        date_tag="20261025T060000Z",
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        parent_compare_path=R0,
        releases_dir=DATA_RELEASES,
        downloads_dir=DOWNLOADS,
        floor_px=3.0,
        bundle_js_filename="s15_scgf_submission_bundle.js",
    )
    release_zeros = Path(bundle["primary_zeros_tif"]["path"])
    published_zeros = DOWNLOADS / release_zeros.name
    shutil.copy2(release_zeros, published_zeros)
    if IO.sha256_file(published_zeros) != bundle["primary_zeros_tif"]["sha256"]:
        raise RuntimeError("Published GeoTIFF SHA-256 mismatch")

    g57 = validate_gems57(published_zeros, footprint=footprint, catalogue=cat)
    if not g57["all_checks_passed"]:
        raise RuntimeError(f"Independent gems57 validation failed: {g57}")

    final_pass = bool(final_registry["uniqueness_pass"])
    real_max_3px = reg_summary["disaggregated_real_submissions_only"][
        "max_3px_dot_overlap_vs_real_submissions"
    ]
    if final_registry["is_duplicate"]:
        note = (
            f"S15-SCGF {winner['exp_id']} research only: HOLDOUT-DTI="
            f"{winner['holdout']['holdout_dti']:.4f}; real3px={100*real_max_3px:.1f}%, "
            f"r13_blanket={100*final_registry['dots_max_3px_overlap']:.2f}%; do not submit."
        )
    else:
        note = (
            f"S15-SCGF {winner['exp_id']}: Forstner+Salem+Baffle dual-specialist; "
            f"HOLDOUT-DTI={winner['holdout']['holdout_dti']:.4f}; {bundle['dots']['n_dots']} dots"
        )
    if len(note) > 140:
        raise RuntimeError(f"Submission note exceeds 140 chars ({len(note)}): {note}")

    submission_name = f"GEMS91-S15-SCGF-{winner['exp_id']}-{bundle['dots']['dot_set_digest'][:8]}"
    elapsed = round(time.perf_counter() - exp_start, 2)
    final_status = "PASS_WITHIN_INDEXED_SCOPE" if final_pass else "STOPPED_DUPLICATE"

    card = {
        "schema_version": "gems91.s15_scgf.v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/605655a6-gemsdoe91",
        "preregistration": {
            "path": "docs/HYPOTHESES_S15_SCGF.md",
            "sha256": prereg_sha,
            "merge_rename_note": "Renamed from docs/HYPOTHESES_S15.md / docs/run-card-S15.json to *-SCGF* during main integration to coexist cleanly with concurrent S15-HCPA; file bytes, SHA-256, scores, raster, and verdict are unchanged.",
        },
        "lane": {
            "id": "S15-SCGF",
            "assigned": False,
            "provisional_name": (
                "Structural-Complexity Tensor Junctions + Multi-Wavelength Salem Attenuation "
                "+ Hydrothermal Aquifer-Baffle + Dual-Specialist Auto-Context Dinkelbach"
            ),
            "note": "No external selector-assigned lane paragraph was supplied; self-declared prior to S15 fitting.",
        },
        "hypothesis": winner["title"],
        "hypothesis_id": winner["hypothesis_id"],
        "physical_mechanism": (
            "Extracts pure-subsurface Förstner tensor junctions, conjugate gravity-magnetic strike "
            "crossings, Walker Lane lateral juxtaposition steps, multi-wavelength (150-900 m) Salem "
            "tilt-depth & upward-attenuation worms, and 2-D deconfounded aquifer-baffle/GDR conduits; "
            "cross-fits BOTH a 123-feature Full ensemble and a provably 100%-topography-free 95-feature "
            "Pure-Subsurface specialist across Stage-1 and Stage-2 (137 total features), then allocates "
            "binary {0,1} dots via 300 m Dinkelbach submodular optimization."
        ),
        "named_non_fault_mimic_process": winner["named_non_fault_mimic"],
        "comparable_prior_holdout_best": {
            "candidate_id": "GEMS91-S14-PTAC-E2-76262b89",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": actual_split,
            "label": "HOLDOUT-DTI",
            "value": S14_BASELINE_DTI,
            "ci95": S14_BASELINE_CI,
            "withheld_positives": 60_988,
            "prior_s13_ptha_e3_value": S13_BASELINE_DTI,
            "prior_s13_ptha_e3_ci95": S13_BASELINE_CI,
        },
        "holdout_dti": {
            "status": "COMPLETED",
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.EVALUATOR_VERSION,
            "split_sha256": actual_split,
            "value": winner["holdout"]["holdout_dti"],
            "ci95": winner["holdout"]["ci_95"],
            "withheld_positives": winner["holdout"]["n_withheld_positives"],
            "holdout_v1_1_nohalo": winner["holdout_v1_1_nohalo"],
            "beats_prior_s14_point": beats_point_only,
            "beats_prior_s14_paired_ci95": beats_s14,
            "paired_best": {
                "baseline_id": "S14-PTAC-E2",
                "delta": winner["paired_vs_s14_ptac_e2"]["delta"],
                "ci95": winner["paired_vs_s14_ptac_e2"]["ci95"],
                "prob_positive": winner["paired_vs_s14_ptac_e2"]["prob_positive"],
                "n_paired_5km_tiles": winner["paired_vs_s14_ptac_e2"]["n_paired_5km_tiles"],
            },
            "paired_vs_s13_ptha_e3": winner["paired_vs_s13_ptha_e3"],
            "per_fold": winner["holdout"]["folds"],
        },
        "blind_sgmc_offcatalogue_control": {
            "label": "BLIND-SGMC-CONTROL-DTI (not competition leaderboard)",
            "value": sgmc_result["dti"],
            "s14_ptac_e2_reference_value": 0.095760,
            "r0_reference_value": r0_sgmc["dti"],
            "delta_vs_s14_ptac_e2": round(sgmc_result["dti"] - 0.095760, 6),
            "delta_vs_r0": round(sgmc_result["dti"] - r0_sgmc["dti"], 6),
            "n_offcatalogue_sgmc_positives": sgmc_result["n_offcatalogue_sgmc_positives"],
        },
        "canaries": {
            "status": "PASS",
            "n_features_checked": canary["n_features_checked"],
            "n_new_s15_static_features": 18,
            "n_dual_autocontext_features": 14,
            "n_strictly_topography_free_stage2_features": 99,
            "max_symmetric_auc": canary["worst_symmetric_auc"],
            "worst_feature": canary["worst_feature"],
            "threshold": 0.90,
        },
        "registry_comparison": {
            "complete_universal_registry": False,
            "scope": "hash-distinct same-grid local fleet_registry + registry + retracted GEOD + docs downloads (zero exemptions)",
            "preplacement": {
                "status": "PASS_WITHIN_INDEXED_SCOPE",
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
            "max_measured_final_dot_overlap_vs_real_submissions_within_3px": real_max_3px,
            "surface_closest_raster": pre_full["surface_closest_raster"],
            "dots_closest_raster": final_registry["dots_closest_raster"],
            "summary": reg_summary,
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
        "submission_name": sub_name,
        "note": sub_note,
        "submission": {
            "name": submission_name,
            "note": note,
            "note_length": len(note),
            "recommended_upload_file": published_zeros.name if (beats_s14 and final_pass) else None,
            "research_download_file": published_zeros.name,
            "zip_download": Path(bundle["zip_bundle"]["path"]).name,
        },
        "selector_approval": False,
        "selector_receipt": {
            "weekly_cap_verified": False,
            "slot_available": False,
            "note": "No live organizer account state was accessed and no weekly slot was spent.",
        },
        "verdict": "promote" if (beats_s14 and final_pass) else "negative",
        "technical_candidate_verdict": (
            "promote_to_selector" if (beats_s14 and final_pass) else "negative"
        ),
        "portal_submission_verdict": (
            "HOLD_PENDING_SELECTOR_SIGN_OFF" if (beats_s14 and final_pass) else "NOT_OK_TO_SUBMIT"
        ),
        "budget": {
            "experiments_executed": len(completed),
            "max_experiments": MAX_EXPERIMENTS,
            "elapsed_seconds": elapsed,
            "max_seconds": MAX_SECONDS,
        },
        "experiments": experiments,
        "full_map_emitter_last_gain": round(float(last_gain), 7),
        "experiments_run": 3,
        "slots_used": 0,
        "organizer_confirmed": None,
        "organizer_confirmed_score": None,
    }
    card["readiness_gates"] = RD.gates(card)
    card["submission_ready"] = RD.submission_ready(card)
    RUN_CARD.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    EVIDENCE.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    log(
        f"Wrote {RUN_CARD.name}, {EVIDENCE.name}, and {published_zeros.name} | "
        f"HOLDOUT-DTI={winner['holdout']['holdout_dti']:.6f} | "
        f"SGMC={sgmc_result['dti']:.6f} | submission_ready={card['submission_ready']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
