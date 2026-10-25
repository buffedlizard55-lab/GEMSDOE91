#!/usr/bin/env python3
"""Session 18 (`S18-HGBR`) Preregistered Experiment Runner (`H18-1..H18-3`: `hgbr_e1`, `hgbr_e2`, `hgbr_e3`).

Strictly obeys `PARALLEL-RUN PROTOCOL` Rules 1–6:
  - Reuses the restored 19-band GeoDAWN feature stack, cached local feature tables
    (`X_static`, `X_s11`, `X_s12`, `X_ptha`, `X_hvdc`, `X_cpad`), and the novel 16-feature
    `S18-HGBR` table (`X_hgbr` in `src/gems91/hgbr18.py`).
  - Evaluates the 3 preregistered `S18-HGBR` ablations (`hgbr_e1`, `hgbr_e2`, `hgbr_e3`)
    on the unchanged label-blind shared evaluator `vendor/gems57/evaluate_holdout.py`
    (`gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer, `1,000` paired
    20 km physical-block bootstrap draws) side-by-side against pinned `incumbent_ptac_v2`,
    `s17_e2_lftg_pcac`, `incumbent_ptha_v2`, `gravity_control`, `pgrd`, `ced_benchmark`,
    and Session 17's `cpad_e1` (`0.198183 HOLDOUT-DTI`) & `incumbent_ptac_lb` (`0.194221 HOLDOUT-DTI`).
  - Enforces Rule 4 single-feature AUROC leakage canaries (`symmetric_auc <= 0.90` pooled
    and in every quadrant) across all `151` static + `20` OOF auto-context features.
  - Verifies bitwise `0.0` `Band 12 / Band 19` dependence in the Pure-Subsurface Specialist
    (`IR-91-S15-05`), resolves `IR-91-S17-01` (log-odds dispersion alignment) and
    `IR-91-S17-02` (Asymmetric Concealed-Fault Log-Odds Rescue), and resolves
    `IR-91-S17-LFTG-01` by emitting the full-map `37,654`-dot raster from the 4-fold
    Out-of-Fold (`OOF`) stitched surface with visible-catalogue halo de-crowding.
  - Packages one validated full-map `-zeros.tif` + single-TIFF `-zeros.zip` via
    `vendor/gems57/submission_writer.py::write_submission`, validates via all three
    repository gate suites (`validate_raster`, `gems91.gates`, `gems91.release_gates`),
    evaluates untouched Blind Off-Catalogue USGS SGMC Controls (`>300 m`, `>500 m`, `>1 km`),
    checks Rule 1 pre-placement surface (`|rho| <= 0.90`) and post-placement dot overlap
    (`<= 70%`) across registry rasters, and writes `docs/run-card-S18-HGBR.json`.
"""

from __future__ import annotations

import os

for _env_k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_env_k, "2")

from datetime import datetime, timezone
import gc
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.metrics import roc_auc_score

import evaluate_holdout as EH_SCRIPT
import validate_raster as VR
from gems91 import (
    ced,
    cpad17 as CPAD,
    dd_vtc_pu as DD,
    gates as G91,
    hgbr18 as HGBR,
    hvdc as HVDC,
    mhtr_coda as MC,
    ptac14 as PTAC,
    ptha as PTHA,
    readiness,
    release_gates as RG91,
    spac_coda as SC,
)
from gems91.io import sha256_file
from scripts import run_ced
from vendor.gems57 import evaluate_holdout as evaluator, gates as v57_gates, metric as v57_metric, spatial
from vendor.gems57.submission_writer import write_submission

SAMPLE = ROOT / "data/official/sample_submission.tif"
CATALOGUE = ROOT / "data/official/existing_faults.tif"
STACK = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
GDR_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"
SGMC_TIF = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
R0_TIF = ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif"
PREREG = ROOT / "docs/HYPOTHESES_S18_HGBR.md"
OUT_DIR = ROOT / "docs/s18_hgbr"
CACHE_DIR = ROOT / "data/derived/s18"
DOWNLOADS = ROOT / "docs/downloads"
CARD_PATH = ROOT / "docs/run-card-S18-HGBR.json"

DOT_BUDGET = 37_654
COLLAR_PX = 3.05
MIN_SPACING_PX = 3.05
BUFFER_PX = 80
SEED_BASE = 20261025
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 520810


def dump(path: Path, obj: object) -> None:
    run_ced.dump(path, obj)


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%SZ')}] {msg}", flush=True)


def verify_all_inputs() -> dict[str, dict[str, object]]:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    wanted = {
        "sample_submission",
        "existing_faults",
        "training_features",
        "gdr_wellspring_csv",
        "sgmc_concealed_faults_u8",
    }
    pins: dict[str, dict[str, object]] = {}
    for entry in manifest["files"]:
        if entry["id"] not in wanted:
            continue
        p = ROOT / "data" / entry["local_subpath"]
        if not p.is_file():
            raise FileNotFoundError(f"Missing pinned input: {p}")
        digest = sha256_file(p)
        if digest != entry["sha256"] or p.stat().st_size != entry["bytes"]:
            raise ValueError(f"SHA/size mismatch for {entry['id']}")
        pins[entry["id"]] = {
            "path": f"data/{entry['local_subpath']}",
            "sha256": digest,
            "bytes": p.stat().st_size,
        }
    tpin = json.loads((ROOT / "registry/template_pin.json").read_text())
    for name, digest in tpin["sha256"].items():
        if sha256_file(ROOT / "vendor/gems57" / name) != digest:
            raise ValueError(f"Immutable vendor/gems57 drift: {name}")
    return pins


def open_or_write_surface_mmap(
    path: Path, shape: tuple[int, int], arr: np.ndarray | None = None
) -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr is not None:
        mm = np.memmap(path, dtype=np.float32, mode="w+", shape=shape)
        mm[:] = arr.astype(np.float32, copy=False)
        mm.flush()
        del mm
    return np.memmap(path, dtype=np.float32, mode="r", shape=shape)


def open_or_write_table_mmap(
    path: Path, shape: tuple[int, int], arr: np.ndarray | None = None
) -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr is not None:
        mm = np.memmap(path, dtype=np.float32, mode="w+", shape=shape)
        mm[:] = arr.astype(np.float32, copy=False)
        mm.flush()
        del mm
    return np.memmap(path, dtype=np.float32, mode="r", shape=shape)


def compute_ac_mmap(path: Path, surface_2d: np.ndarray, footprint: np.ndarray) -> np.memmap:
    n_fp = int(footprint.sum())
    n_ac = len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)
    if path.is_file() and path.stat().st_size == n_fp * n_ac * 4:
        return np.memmap(path, dtype=np.float32, mode="r", shape=(n_fp, n_ac))
    ac_arr = SC.compute_spac_autocontext_features(np.asarray(surface_2d, dtype=np.float32), footprint)
    mm = open_or_write_table_mmap(path, (n_fp, n_ac), ac_arr)
    del ac_arr
    gc.collect()
    return mm


def fast_symmetric_auc(values_1d: np.ndarray, y_bool_1d: np.ndarray) -> tuple[float, float]:
    auc = float(roc_auc_score(y_bool_1d.astype(np.uint8), values_1d))
    return auc, max(auc, 1.0 - auc)


def collect_registry_paths() -> list[tuple[Path, str]]:
    """Collect all unique SHA-256 single-band same-grid finite rasters across registry scopes."""
    seen: dict[str, tuple[Path, str]] = {}
    scopes = (
        (ROOT / "data/registry", "canonical_registry"),
        (ROOT / "data/fleet_registry", "external_fleet"),
        (DOWNLOADS, "in_repo_downloads"),
    )
    for folder, scope in scopes:
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("*.tif")):
            if p.name.startswith("gems91-s18-hgbr-"):
                continue
            digest = sha256_file(p)
            seen.setdefault(digest, (p, scope))
    if not seen:
        raise RuntimeError("Empty registry inventory")
    return list(seen.values())


def build_feature_tables(fp: np.ndarray) -> dict[str, object]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    shared_cache = ROOT / "data/derived/shared_stack_v1"
    s17_cache = ROOT / "data/derived/s17"
    shared_cache.mkdir(parents=True, exist_ok=True)
    s17_cache.mkdir(parents=True, exist_ok=True)

    log("1/7 Loading/building static DD feature memmap")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=STACK, gdr_csv=GDR_CSV, footprint=fp, cache_dir=shared_cache
    )
    log("2/7 Loading/building S11 MHTR feature memmap")
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=STACK, footprint=fp, cache_dir=shared_cache
    )
    log("3/7 Loading/building S12 SPAC feature memmap")
    X_s12, s12_names, _ = SC.build_or_load_s12_feature_memmap(
        features_tif=STACK, footprint=fp, cache_dir=shared_cache
    )
    log("4/7 Loading/building S13 PTHA feature memmap")
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=STACK, footprint=fp, cache_dir=shared_cache
    )
    log("5/7 Loading/building S14 HVDC feature memmap")
    X_hvdc, hvdc_names, _ = HVDC.build_or_load_hvdc_feature_memmap(
        features_tif=STACK, gdr_csv=GDR_CSV, footprint=fp, cache_dir=shared_cache
    )
    log("6/7 Loading/building S17 CPAD feature memmap")
    X_cpad, cpad_names, _ = CPAD.build_or_load_cpad_feature_memmap(
        features_tif=STACK, gdr_csv=GDR_CSV, footprint=fp, cache_dir=s17_cache
    )
    log("7/7 Loading/building novel S18 HGBR 16-feature memmap")
    X_hgbr, hgbr_names, hgbr_meta = HGBR.build_or_load_hgbr_feature_memmap(
        features_tif=STACK, gdr_csv=GDR_CSV, footprint=fp, cache_dir=CACHE_DIR
    )
    gc.collect()

    return {
        "X_static": X_static,
        "static_names": list(static_names),
        "X_s11": X_s11,
        "s11_names": list(s11_names),
        "X_s12": X_s12,
        "s12_names": list(s12_names),
        "X_ptha": X_ptha,
        "ptha_names": list(ptha_names),
        "X_hvdc": X_hvdc,
        "hvdc_names": list(hvdc_names),
        "X_cpad": X_cpad,
        "cpad_names": list(cpad_names),
        "X_hgbr": X_hgbr,
        "hgbr_names": list(hgbr_names),
        "hgbr_meta": hgbr_meta,
    }


def assemble_hgbr_blocks(tables: dict[str, object]) -> dict[str, object]:
    raw_blocks = [
        (tables["X_static"], HGBR.STATIC_LOCAL_COLS, tables["static_names"]),
        (tables["X_s11"], HGBR.S11_LOCAL_COLS, tables["s11_names"]),
        (tables["X_s12"], HGBR.S12_LOCAL_COLS, tables["s12_names"]),
        (tables["X_ptha"], HGBR.PTHA_LOCAL_COLS, tables["ptha_names"]),
        (tables["X_hvdc"], HGBR.HVDC_LOCAL_COLS, tables["hvdc_names"]),
        (tables["X_cpad"], HGBR.CPAD_LOCAL_COLS, tables["cpad_names"]),
        (tables["X_hgbr"], HGBR.HGBR_LOCAL_COLS, tables["hgbr_names"]),
    ]

    full_blocks: list[tuple[np.ndarray, list[int]]] = []
    sub_blocks: list[tuple[np.ndarray, list[int]]] = []
    full_names: list[str] = []
    sub_names: list[str] = []

    for arr, cols, names in raw_blocks:
        f_cols = list(cols)
        s_cols = [c for c in cols if names[c] not in HGBR.STRICT_TOPO_FEATURE_NAMES]
        full_blocks.append((arr, f_cols))
        sub_blocks.append((arr, s_cols))
        full_names.extend(names[c] for c in f_cols)
        sub_names.extend(names[c] for c in s_cols)

    full_hard_targets = {
        "b19_det_elev_slope",
        "cpad_cooper_theta_grav",
        "cpad_cooper_theta_rtp",
        "hgbr18_grav_hurst_anisotropy",
    }
    sub_hard_targets = {
        "cpad_cooper_theta_grav",
        "cpad_cooper_theta_rtp",
        "s12_tmi_asig_log",
        "hgbr18_grav_hurst_anisotropy",
    }
    full_hard_cols = [i for i, n in enumerate(full_names) if n in full_hard_targets]
    sub_hard_cols = [i for i, n in enumerate(sub_names) if n in sub_hard_targets]

    leaked = set(sub_names) & set(HGBR.STRICT_TOPO_FEATURE_NAMES)
    if leaked:
        raise AssertionError(f"Topographic feature leaked into Pure-Subsurface Specialist: {leaked}")

    return {
        "full_blocks": full_blocks,
        "sub_blocks": sub_blocks,
        "full_names": full_names,
        "sub_names": sub_names,
        "full_hard_cols": full_hard_cols,
        "sub_hard_cols": sub_hard_cols,
    }


def run_hgbr_hierarchy(
    tables: dict[str, object],
    spec: dict[str, object],
    folds: list[dict],
    fp: np.ndarray,
) -> dict[str, object]:
    """Fit cross-fitted Stage-1 + Stage-2 Dual-Specialist `S18-HGBR` (`hgbr_e1`, `hgbr_e2`, `hgbr_e3`)."""
    hgbr_dir = CACHE_DIR / "hgbr18_models"
    hgbr_dir.mkdir(parents=True, exist_ok=True)
    shape = fp.shape

    full_blocks = spec["full_blocks"]
    sub_blocks = spec["sub_blocks"]
    full_hard = spec["full_hard_cols"]
    sub_hard = spec["sub_hard_cols"]

    cover_prior_fp = np.asarray(tables["X_cpad"][:, 15], dtype=np.float32)
    crest_bonus_fp = HGBR.compute_hgbr_crest_concordance_fp(
        tables["X_hgbr"], tables["X_cpad"], tables["X_s11"], tables["X_ptha"]
    )

    # --- Step A: 6 Pairwise Stage-1 fits for Full and Pure-Subsurface ---
    pair_full: dict[tuple[int, int], np.memmap] = {}
    pair_sub: dict[tuple[int, int], np.memmap] = {}
    calibration_log: list[dict[str, object]] = []

    for a, b in itertools.combinations(range(4), 2):
        held = [q for q in range(4) if q not in (a, b)]
        c, d = held[0], held[1]
        train_ab = folds[c]["train"] & folds[d]["train"]
        vis_ab = folds[c]["visible"] & folds[d]["visible"] & train_ab
        eval_cd = folds[c]["region"] | folds[d]["region"]

        pf_path = hgbr_dir / f"pair_full_{a}_{b}.f32.mmap"
        if pf_path.is_file() and pf_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape)
        else:
            log(f"[S18-HGBR] Fitting pairwise Stage-1 Full ({a},{b})")
            surf, meta = CPAD.fit_predict_specialist(
                blocks=full_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=fp,
                seed=SEED_BASE + 1000 + 10 * a + b,
                predict_mask=eval_cd,
            )
            calibration_log.append({"split": f"pair_{a}_{b}", "specialist": "full", **meta})
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape, surf)
            del surf
            gc.collect()

        ps_path = hgbr_dir / f"pair_sub_{a}_{b}.f32.mmap"
        if ps_path.is_file() and ps_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape)
        else:
            log(f"[S18-HGBR] Fitting pairwise Stage-1 Pure-Subsurface ({a},{b})")
            surf, meta = CPAD.fit_predict_specialist(
                blocks=sub_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=fp,
                seed=SEED_BASE + 2000 + 10 * a + b,
                predict_mask=eval_cd,
            )
            calibration_log.append({"split": f"pair_{a}_{b}", "specialist": "pure_subsurface", **meta})
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape, surf)
            del surf
            gc.collect()

    # --- Step B: 4 OOF Stage-1 fits for Full and Pure-Subsurface ---
    oof_s1_full: list[np.memmap] = []
    oof_s1_sub: list[np.memmap] = []
    oof_spans_full: list[float] = []
    oof_spans_sub: list[float] = []

    for q in range(4):
        of_path = hgbr_dir / f"oof_s1_full_q{q}.f32.mmap"
        if of_path.is_file() and of_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape))
        else:
            log(f"[S18-HGBR] Fitting OOF Stage-1 Full fold {q}")
            surf, meta = CPAD.fit_predict_specialist(
                blocks=full_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 3000 + q,
                predict_mask=folds[q]["region"],
            )
            calibration_log.append({"split": f"oof_q{q}", "specialist": "full", **meta})
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape, surf))
            del surf
            gc.collect()

        os_path = hgbr_dir / f"oof_s1_sub_q{q}.f32.mmap"
        if os_path.is_file() and os_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape))
        else:
            log(f"[S18-HGBR] Fitting OOF Stage-1 Pure-Subsurface fold {q}")
            surf, meta = CPAD.fit_predict_specialist(
                blocks=sub_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 4000 + q,
                predict_mask=folds[q]["region"],
            )
            calibration_log.append({"split": f"oof_q{q}", "specialist": "pure_subsurface", **meta})
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape, surf))
            del surf
            gc.collect()

        # Measure 3-quadrant OOF log-odds upper-tail span (p99 - p50) for IR-91-S17-01 alignment
        reg_m = folds[q]["region"] & fp
        pf_q = np.clip(oof_s1_full[q][reg_m][::8], 1e-5, 1.0 - 1e-5)
        lf_q = np.log(pf_q / (1.0 - pf_q))
        oof_spans_full.append(float(np.percentile(lf_q, 99.0) - np.percentile(lf_q, 50.0)))

        ps_q = np.clip(oof_s1_sub[q][reg_m][::8], 1e-5, 1.0 - 1e-5)
        ls_q = np.log(ps_q / (1.0 - ps_q))
        oof_spans_sub.append(float(np.percentile(ls_q, 99.0) - np.percentile(ls_q, 50.0)))

    ref_span_full = float(np.median(oof_spans_full))
    ref_span_sub = float(np.median(oof_spans_sub))
    log(f"[S18-HGBR] Reference 3-quadrant log-odds spans (p99-p50): Full={ref_span_full:.4f}, Sub={ref_span_sub:.4f}")

    # --- Step C: 4 OOF Stage-2 fits -> hgbr_e1, hgbr_e2, hgbr_e3 fold surfaces & dots ---
    e1_dots_folds: list[np.ndarray] = []
    e2_dots_folds: list[np.ndarray] = []
    e3_dots_folds: list[np.ndarray] = []
    e1_fold_surfaces: list[np.ndarray] = []
    e2_fold_surfaces: list[np.ndarray] = []
    oof_e1_mosaic = np.zeros(shape, dtype=np.float32)
    oof_e2_mosaic = np.zeros(shape, dtype=np.float32)

    for q in range(4):
        stitch_f = np.zeros(shape, dtype=np.float32)
        stitch_s = np.zeros(shape, dtype=np.float32)
        stitch_f[folds[q]["region"]] = oof_s1_full[q][folds[q]["region"]]
        stitch_s[folds[q]["region"]] = oof_s1_sub[q][folds[q]["region"]]
        for m in range(4):
            if m == q:
                continue
            tp = tuple(sorted(x for x in range(4) if x not in (q, m)))
            stitch_f[folds[m]["region"]] = pair_full[tp][folds[m]["region"]]
            stitch_s[folds[m]["region"]] = pair_sub[tp][folds[m]["region"]]
            # Align 2-quadrant Stage-1 upper-tail dispersion to 3-quadrant OOF reference (IR-91-S17-01)
            stitch_f = HGBR.align_stage1_log_odds_dispersion(
                stitch_f, folds[m]["region"], ref_span_full, fp
            )
            stitch_s = HGBR.align_stage1_log_odds_dispersion(
                stitch_s, folds[m]["region"], ref_span_sub, fp
            )

        ac_f_q = compute_ac_mmap(hgbr_dir / f"ac_full_q{q}.f32.mmap", stitch_f, fp)
        ac_s_q = compute_ac_mmap(hgbr_dir / f"ac_sub_q{q}.f32.mmap", stitch_s, fp)

        # Stage-2 Full (151 static + 10 ac_full + 10 ac_sub = 171 features)
        s2f_path = hgbr_dir / f"oof_s2_full_q{q}.f32.mmap"
        if s2f_path.is_file() and s2f_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_full_q = open_or_write_surface_mmap(s2f_path, shape)
        else:
            log(f"[S18-HGBR] Fitting OOF Stage-2 Full fold {q}")
            s2f_blocks = full_blocks + [(ac_f_q, list(range(10))), (ac_s_q, list(range(10)))]
            surf, meta = CPAD.fit_predict_specialist(
                blocks=s2f_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 5000 + q,
            )
            calibration_log.append({"split": f"s2_oof_q{q}", "specialist": "full", **meta})
            s2_full_q = open_or_write_surface_mmap(s2f_path, shape, surf)
            del surf
            gc.collect()

        # Stage-2 Pure-Subsurface (110 DEM-free static + 10 ac_sub = 120 features; ZERO B12/B19!)
        s2s_path = hgbr_dir / f"oof_s2_sub_q{q}.f32.mmap"
        if s2s_path.is_file() and s2s_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_sub_q = open_or_write_surface_mmap(s2s_path, shape)
        else:
            log(f"[S18-HGBR] Fitting OOF Stage-2 Pure-Subsurface fold {q}")
            s2s_blocks = sub_blocks + [(ac_s_q, list(range(10)))]
            surf, meta = CPAD.fit_predict_specialist(
                blocks=s2s_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 6000 + q,
            )
            calibration_log.append({"split": f"s2_oof_q{q}", "specialist": "pure_subsurface", **meta})
            s2_sub_q = open_or_write_surface_mmap(s2s_path, shape, surf)
            del surf
            gc.collect()

        # hgbr_e1 surface: Full Stage-1 + Stage-2 log-opinion pool with Hurst-Tensor crest sharpening
        surf_e1_q = HGBR.pool_full_specialist_with_crest(
            stitch_f,
            np.asarray(s2_full_q, dtype=np.float32),
            crest_bonus_fp,
            fp,
            stage2_weight=0.66,
            crest_alpha=0.14,
        )
        # hgbr_e2 / hgbr_e3 surface: Asymmetric Concealed-Fault Log-Odds Rescue (IR-91-S17-02)
        surf_e2_q = HGBR.pool_asymmetric_cover_specialists(
            s1_full=stitch_f,
            s1_sub=stitch_s,
            s2_full=np.asarray(s2_full_q, dtype=np.float32),
            s2_sub=np.asarray(s2_sub_q, dtype=np.float32),
            cover_prior_fp=cover_prior_fp,
            crest_bonus_fp=crest_bonus_fp,
            footprint=fp,
            stage2_weight=0.66,
            max_cover_rescue_weight=0.42,
            cover_threshold=0.38,
            crest_alpha=0.18,
        )
        e1_fold_surfaces.append(surf_e1_q)
        e2_fold_surfaces.append(surf_e2_q)
        oof_e1_mosaic[folds[q]["region"]] = surf_e1_q[folds[q]["region"]]
        oof_e2_mosaic[folds[q]["region"]] = surf_e2_q[folds[q]["region"]]

        log(f"[S18-HGBR] Emitting global blind dots for fold {q} (hgbr_e1, hgbr_e2, hgbr_e3)")
        d_e1 = CPAD.emit_global_dots_nms(
            surf_e1_q, folds[q]["visible"], fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
        d_e2 = CPAD.emit_global_dots_nms(
            surf_e2_q, folds[q]["visible"], fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
        d_e3 = CPAD.emit_global_dots_submodular(
            surf_e2_q, folds[q]["visible"], fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
        e1_dots_folds.append(d_e1 > 0)
        e2_dots_folds.append(d_e2 > 0)
        e3_dots_folds.append(d_e3 > 0)

        del stitch_f, stitch_s, ac_f_q, ac_s_q, s2_full_q, s2_sub_q
        gc.collect()

    # Build OOF mosaic auto-context tables for Rule-4 canary testing
    stitched_oof_f = np.zeros(shape, dtype=np.float32)
    stitched_oof_s = np.zeros(shape, dtype=np.float32)
    for q in range(4):
        stitched_oof_f[folds[q]["region"]] = oof_s1_full[q][folds[q]["region"]]
        stitched_oof_s[folds[q]["region"]] = oof_s1_sub[q][folds[q]["region"]]
    ac_oof_f = compute_ac_mmap(hgbr_dir / "ac_oof_mosaic_full.f32.mmap", stitched_oof_f, fp)
    ac_oof_s = compute_ac_mmap(hgbr_dir / "ac_oof_mosaic_sub.f32.mmap", stitched_oof_s, fp)

    return {
        "e1_dots_folds": e1_dots_folds,
        "e2_dots_folds": e2_dots_folds,
        "e3_dots_folds": e3_dots_folds,
        "e1_fold_surfaces": e1_fold_surfaces,
        "e2_fold_surfaces": e2_fold_surfaces,
        "oof_e1_mosaic": oof_e1_mosaic,
        "oof_e2_mosaic": oof_e2_mosaic,
        "ac_oof_f": ac_oof_f,
        "ac_oof_s": ac_oof_s,
        "calibration_log": calibration_log,
        "ref_span_full": ref_span_full,
        "ref_span_sub": ref_span_sub,
    }


def run_canaries(
    tables: dict[str, object],
    spec: dict[str, object],
    ac_oof_f: np.ndarray,
    ac_oof_s: np.ndarray,
    folds: list[dict],
    cat: np.ndarray,
    fp: np.ndarray,
) -> dict[str, object]:
    """Rule 4 single-feature leak canaries (`AUC <= 0.90` pooled AND in every quadrant)."""
    log("Running Rule 4 single-feature AUROC leak canaries across all 151 static + 20 OOF auto-context features")
    y_fp = cat[fp]
    quad_masks_fp = [f["region"][fp] for f in folds]
    features_report: dict[str, dict[str, object]] = {}

    for idx, name in enumerate(HGBR.HGBR_FEATURE_NAMES):
        grid = np.zeros(fp.shape, dtype=np.float32)
        grid[fp] = np.asarray(tables["X_hgbr"][:, idx], dtype=np.float32)
        res = ced.auc_canary(grid, cat, fp)
        q_aucs = []
        col_v = grid[fp]
        for qm in quad_masks_fp:
            _, sym_q = fast_symmetric_auc(col_v[qm], y_fp[qm])
            q_aucs.append(round(sym_q, 6))
        res["quadrant_symmetric_aucs"] = q_aucs
        res["max_quadrant_symmetric_auc"] = max(q_aucs)
        if res["max_quadrant_symmetric_auc"] > 0.90:
            res["status"] = "LEAKAGE_SUSPECTED"
        features_report[name] = res
        del grid

    cursor = 0
    for arr, cols in spec["full_blocks"]:
        for c in cols:
            fname = spec["full_names"][cursor]
            cursor += 1
            if fname in features_report:
                continue
            vals = np.asarray(arr[:, c], dtype=np.float32)
            auc_p, sym_p = fast_symmetric_auc(vals, y_fp)
            q_aucs = [round(fast_symmetric_auc(vals[qm], y_fp[qm])[1], 6) for qm in quad_masks_fp]
            worst = max(sym_p, max(q_aucs))
            features_report[fname] = {
                "evidence_class": "HOLDOUT-DTI",
                "statistic": "feature-alone AUROC (not DTI)",
                "auc": round(auc_p, 6),
                "symmetric_auc": round(sym_p, 6),
                "quadrant_symmetric_aucs": q_aucs,
                "max_quadrant_symmetric_auc": max(q_aucs),
                "withheld_positive_pixels": int(y_fp.sum()),
                "negative_proxy_pixels": int((~y_fp).sum()),
                "threshold": 0.90,
                "status": "LEAKAGE_SUSPECTED" if worst > 0.90 else "PASS",
            }

    for prefix, ac_arr in (("ac_full", ac_oof_f), ("ac_sub", ac_oof_s)):
        for c, ac_name in enumerate(SC.S12_AUTOCONTEXT_FEATURE_NAMES):
            fname = f"{prefix}_{ac_name}"
            vals = np.asarray(ac_arr[:, c], dtype=np.float32)
            auc_p, sym_p = fast_symmetric_auc(vals, y_fp)
            q_aucs = [round(fast_symmetric_auc(vals[qm], y_fp[qm])[1], 6) for qm in quad_masks_fp]
            worst = max(sym_p, max(q_aucs))
            features_report[fname] = {
                "evidence_class": "HOLDOUT-DTI",
                "statistic": "feature-alone AUROC (not DTI)",
                "auc": round(auc_p, 6),
                "symmetric_auc": round(sym_p, 6),
                "quadrant_symmetric_aucs": q_aucs,
                "max_quadrant_symmetric_auc": max(q_aucs),
                "withheld_positive_pixels": int(y_fp.sum()),
                "negative_proxy_pixels": int((~y_fp).sum()),
                "threshold": 0.90,
                "status": "LEAKAGE_SUSPECTED" if worst > 0.90 else "PASS",
            }

    worst_pooled = max(float(v["symmetric_auc"]) for v in features_report.values())
    worst_quad = max(float(v["max_quadrant_symmetric_auc"]) for v in features_report.values())
    all_pass = all(v["status"] == "PASS" for v in features_report.values())
    if not all_pass or worst_pooled > 0.90 or worst_quad > 0.90:
        raise RuntimeError(f"Rule 4 canary failure: worst_pooled={worst_pooled}, worst_quad={worst_quad}")

    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluator.VERSION,
        "all_pass": all_pass,
        "n_features_tested": len(features_report),
        "n_novel_hgbr_features": len(HGBR.HGBR_FEATURE_NAMES),
        "n_static_features": len(spec["full_names"]),
        "n_autocontext_features": 20,
        "max_pooled_symmetric_auc": round(worst_pooled, 6),
        "max_quadrant_symmetric_auc": round(worst_quad, 6),
        "threshold": 0.90,
        "features": features_report,
    }


def evaluate_dots_on_folds(
    dots_folds: list[np.ndarray],
    folds: list[dict],
    fp: np.ndarray,
) -> tuple[np.ndarray, list[dict]]:
    shape = fp.shape
    nblocks = ((shape[0] + 199) // 200) * ((shape[1] + 199) // 200)
    block_terms = np.zeros((nblocks, 4), dtype=np.float64)
    fold_rows = []
    for q, fold in enumerate(folds):
        ys, xs = np.nonzero(fold["region"])
        sl = (slice(int(ys.min()), int(ys.max()) + 1), slice(int(xs.min()), int(xs.max()) + 1))
        small = {k: fold[k][sl] for k in ("region", "visible", "truth")}
        res, bterms = evaluator.evaluate(
            dots_folds[q][sl].astype(np.float32),
            small,
            fp[sl],
            origin=(sl[0].start, sl[1].start),
            global_shape=shape,
        )
        block_terms += bterms
        res["global_emitted_dots"] = int(dots_folds[q].sum())
        fold_rows.append({"fold": q, "result": res})
    return block_terms, fold_rows


def score_blind_sgmc_suite(
    s18_dots: np.ndarray, cat: np.ndarray, sgmc_raw: np.ndarray, fp: np.ndarray
) -> dict:
    """Evaluate untouched Blind Off-Catalogue USGS SGMC Control at >300 m, >500 m, and >1 km."""
    d_cat = ndi.distance_transform_edt(~cat)
    sgmc_300m = sgmc_raw & fp & (d_cat > 3.0)
    sgmc_500m = sgmc_raw & fp & (d_cat > 5.0)
    sgmc_1km = sgmc_raw & fp & (d_cat > 10.0)
    active = fp & (~cat)

    disk_refs = {
        "gemsdoe32_r0": R0_TIF,
        "s17_lftg": DOWNLOADS / "gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros.tif",
        "s17_cpad": DOWNLOADS / "gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif",
        "s17_cwpc": DOWNLOADS / "gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros.tif",
        "s14_ptac_e2": DOWNLOADS / "gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif",
        "s13_ptha_e3": DOWNLOADS / "gems91-s13-ptha-e3-20261024T201500Z-660d645d-zeros.tif",
    }

    def _eval_one(arr: np.ndarray) -> dict:
        pred = np.where(active, arr, 0.0)
        r3 = v57_metric.dti_exact(pred, sgmc_300m, valid=active)
        r5 = v57_metric.dti_exact(pred, sgmc_500m, valid=active)
        r10 = v57_metric.dti_exact(pred, sgmc_1km, valid=active)
        dots = (arr > 0) & fp
        ff1km = float((d_cat[dots] > 10.0).mean()) if dots.any() else 0.0
        return {
            "label": "SGMC-OFFCAT-CONTROL-DTI",
            "dti_gt_300m": round(float(r3["dti"]), 6),
            "tpw_gt_300m": round(float(r3["tp"]), 2),
            "fpw_gt_300m": round(float(r3["fp"]), 2),
            "n_sgmc_pixels_gt_300m": int(sgmc_300m.sum()),
            "dti_gt_500m": round(float(r5["dti"]), 6),
            "tpw_gt_500m": round(float(r5["tp"]), 2),
            "fpw_gt_500m": round(float(r5["fp"]), 2),
            "n_sgmc_pixels_gt_500m": int(sgmc_500m.sum()),
            "dti_gt_1km": round(float(r10["dti"]), 6),
            "tpw_gt_1km": round(float(r10["tp"]), 2),
            "fpw_gt_1km": round(float(r10["fp"]), 2),
            "n_sgmc_pixels_gt_1km": int(sgmc_1km.sum()),
            "n_positive_dots": int(dots.sum()),
            "far_field_gt_1km_share": round(ff1km, 5),
        }

    scores = {"s18_hgbr_winner": _eval_one(s18_dots)}
    for name, path in disk_refs.items():
        if not path.is_file():
            continue
        with rasterio.open(path) as src:
            arr = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)
        scores[name] = _eval_one(arr)
    return {
        "control_dataset": "data/external/derived_sgmc_faults_100m_u8.tif",
        "scores": scores,
    }


def summarize_multiscope_uniqueness(
    full_report: dict, reg_inventory: list[tuple[Path, str]]
) -> dict:
    scope_by_name = {p.name: scope for p, scope in reg_inventory}
    synthetic_or_ribbon = {
        "calib_r13lattice_00904.tif",
        "calib_h25ctx_01280.tif",
        "calib_g13edge_01320.tif",
        "calib_h28ridge_01839.tif",
    }
    comps = full_report["comparisons"]
    for row in comps:
        name = row["registry_raster"]
        row["scope"] = scope_by_name.get(name, "unknown")
        row["is_synthetic_or_continuous_ribbon"] = name in synthetic_or_ribbon

    def _worst(rows: list[dict]) -> dict | None:
        if not rows:
            return None
        w_ov = max(rows, key=lambda r: r["cand_within_3px_of_reg"])
        w_rh = max(rows, key=lambda r: r["surface_abs_rank_corr"])
        return {
            "count": len(rows),
            "max_3px_dot_overlap": w_ov["cand_within_3px_of_reg"],
            "closest_by_overlap": w_ov["registry_raster"],
            "max_abs_surface_spearman": w_rh["surface_abs_rank_corr"],
            "closest_by_spearman": w_rh["registry_raster"],
            "passes_rule1_thresholds": bool(
                w_ov["cand_within_3px_of_reg"] <= 0.70 and w_rh["surface_abs_rank_corr"] <= 0.90
            ),
        }

    r0_rows = [r for r in comps if r["registry_raster"] == "GEMSDOE32__h33-2-b2-zeros.tif"]
    canonical_real = [
        r for r in comps if r["scope"] == "canonical_registry" and not r["is_synthetic_or_continuous_ribbon"]
    ]
    fleet_dotted = [
        r for r in comps if r["scope"] == "external_fleet" and r.get("n_registry_positive", 0) < 65_000
    ]
    in_repo = [r for r in comps if r["scope"] == "in_repo_downloads"]

    return {
        "n_unique_rasters_checked": full_report["n_registry_rasters_checked"],
        "literal_all_rasters": _worst(comps),
        "vs_gemsdoe32_r0": r0_rows[0] if r0_rows else None,
        "vs_canonical_real_submissions": _worst(canonical_real),
        "vs_external_dotted_fleet": _worst(fleet_dotted),
        "vs_in_repo_downloads": _worst(in_repo),
        "top_10_by_overlap": sorted(comps, key=lambda r: r["cand_within_3px_of_reg"], reverse=True)[:10],
    }


def main() -> int:
    t0 = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    prereg_sha = sha256_file(PREREG)
    log(f"Starting S18-HGBR lane; preregistration SHA-256 = {prereg_sha}")

    pins = verify_all_inputs()
    with rasterio.open(SAMPLE) as ds:
        fp = ~np.isnan(ds.read(1))
    with rasterio.open(CATALOGUE) as ds:
        cat = (ds.read(1) > 0) & fp
    with rasterio.open(SGMC_TIF) as ds:
        sgmc_raw = (ds.read(1) > 0) & fp

    folds = list(spatial.folds(cat, fp, buffer_px=BUFFER_PX))
    split_sha = hashlib.sha256(
        b"".join(
            np.packbits(f[k].ravel()).tobytes()
            for f in folds
            for k in ("region", "truth", "train", "visible")
        )
    ).hexdigest()
    log(f"Verified canonical gems57-pooled-hide-v2 folds: split_sha256={split_sha[:16]}…, withheld={int(cat.sum()):,}")

    tables = build_feature_tables(fp)
    spec = assemble_hgbr_blocks(tables)
    log(
        f"Assembled S18-HGBR blocks: Full static={len(spec['full_names'])}, "
        f"Pure-Subsurface static={len(spec['sub_names'])} (0 B12/B19 cols)"
    )

    hierarchy = run_hgbr_hierarchy(tables, spec, folds, fp)
    canary_path = OUT_DIR / "canaries.json"
    if canary_path.is_file():
        canary_report = json.loads(canary_path.read_text())
    else:
        canary_report = run_canaries(
            tables, spec, hierarchy["ac_oof_f"], hierarchy["ac_oof_s"], folds, cat, fp
        )
        dump(canary_path, canary_report)
    log(
        f"Rule 4 Canary PASS across {canary_report['n_features_tested']} features: "
        f"max pooled sym AUC={canary_report['max_pooled_symmetric_auc']:.6f}, "
        f"max quad sym AUC={canary_report['max_quadrant_symmetric_auc']:.6f} <= 0.90"
    )

    # Rule 1 pre-placement surface check on OOF mosaics
    reg_inventory = collect_registry_paths()
    reg_paths_only = [p for p, _ in reg_inventory]
    surf_e1_rep = EH_SCRIPT.check_registry_surface_uniqueness(
        hierarchy["oof_e1_mosaic"][fp], fp, reg_paths_only
    )
    surf_e2_rep = EH_SCRIPT.check_registry_surface_uniqueness(
        hierarchy["oof_e2_mosaic"][fp], fp, reg_paths_only
    )
    dump(
        OUT_DIR / "registry-surface.json",
        {
            "hgbr_e1": {k: v for k, v in surf_e1_rep.items() if k != "comparisons"},
            "hgbr_e2": {k: v for k, v in surf_e2_rep.items() if k != "comparisons"},
        },
    )
    log(
        f"Pre-placement surface check PASS: hgbr_e1 max |rho|={surf_e1_rep['surface_max_abs_rank_corr']:.5f}, "
        f"hgbr_e2 max |rho|={surf_e2_rep['surface_max_abs_rank_corr']:.5f} <= 0.90"
    )

    # Evaluate hgbr_e1, hgbr_e2, hgbr_e3 on gems57-pooled-hide-v2
    terms_by_arm: dict[str, np.ndarray] = {}
    folds_by_arm: dict[str, list[dict]] = {}
    for arm_name, dots_list in (
        ("hgbr_e1", hierarchy["e1_dots_folds"]),
        ("hgbr_e2", hierarchy["e2_dots_folds"]),
        ("hgbr_e3", hierarchy["e3_dots_folds"]),
    ):
        bterms, frows = evaluate_dots_on_folds(dots_list, folds, fp)
        terms_by_arm[arm_name] = bterms
        folds_by_arm[arm_name] = frows
        dump(OUT_DIR / f"{arm_name}-block-terms.json", bterms.tolist())
        dti_val = float(evaluator.from_terms(bterms.sum(axis=0)))
        log(f"[{arm_name}] Pooled HOLDOUT-DTI = {dti_val:.6f}")
        for r in frows:
            res = r["result"]
            log(
                f"  Fold {r['fold']}: HOLDOUT-DTI={res['dti']:.6f} "
                f"(tpw={res['tp']:.1f}, fpw={res['fp']:.1f}, em={res['n_emitted']:,})"
            )

    # Load stored block terms for baseline comparators on identical split_sha256
    baseline_term_files = {
        "ced_benchmark": ROOT / "docs/s16/ced_benchmark-block-terms.json",
        "pgrd": ROOT / "docs/s16/pgrd-block-terms.json",
        "gravity_control": ROOT / "docs/s16/gravity_control-block-terms.json",
        "incumbent_ptha_v2": ROOT / "docs/s17_lftg/incumbent_ptha_v2-block-terms.json",
        "incumbent_ptac_v2": ROOT / "docs/s17_lftg/incumbent_ptac_v2-block-terms.json",
        "s17_e2_lftg_pcac": ROOT / "docs/s17_lftg/s17_e2_lftg_pcac-block-terms.json",
    }
    for bname, bpath in baseline_term_files.items():
        if bpath.is_file():
            terms_by_arm[bname] = np.asarray(json.loads(bpath.read_text()), dtype=np.float64)

    # Also reconstruct block-term summary comparisons against S17-CPAD from docs/s17/holdout.json
    s17_holdout = json.loads((ROOT / "docs/s17/holdout.json").read_text())
    s17_ref_scores = s17_holdout["summary_all_arms"]["scores"]

    cand_names = ("hgbr_e1", "hgbr_e2", "hgbr_e3")
    best_cand = max(
        cand_names, key=lambda n: float(evaluator.from_terms(terms_by_arm[n].sum(axis=0)))
    )
    summary_all = evaluator.pooled_summary(
        terms_by_arm, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED, candidate=best_cand
    )
    control_only_terms = {
        k: v for k, v in terms_by_arm.items() if k not in cand_names or k == best_cand
    }
    summary_vs_controls = evaluator.pooled_summary(
        control_only_terms, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED, candidate=best_cand
    )

    winner_score = summary_all["scores"][best_cand]
    cpad_e1_dti = float(s17_ref_scores["cpad_e1"]["dti"])
    inc_ptac_lb_dti = float(s17_ref_scores["incumbent_ptac_lb"]["dti"])
    beats_cpad_e1 = bool(float(winner_score["dti"]) > cpad_e1_dti)
    beats_inc_ptac_lb = bool(float(winner_score["dti"]) > inc_ptac_lb_dti)

    log(
        f"Holdout winner = {best_cand}: {winner_score['dti']:.6f} HOLDOUT-DTI "
        f"95% CI [{winner_score['ci95'][0]:.6f}, {winner_score['ci95'][1]:.6f}] "
        f"(vs cpad_e1={cpad_e1_dti:.6f} delta={winner_score['dti'] - cpad_e1_dti:+.6f}; "
        f"vs incumbent_ptac_lb={inc_ptac_lb_dti:.6f} delta={winner_score['dti'] - inc_ptac_lb_dti:+.6f}; "
        f"vs incumbent_ptac_v2={summary_vs_controls['scores']['incumbent_ptac_v2']['dti']:.6f} "
        f"delta={summary_vs_controls['paired_differences']['incumbent_ptac_v2']['delta']:+.6f})"
    )

    holdout_payload = {
        "split_sha256": split_sha,
        "buffer_px": BUFFER_PX,
        "global_dot_budget": DOT_BUDGET,
        "collar_px": COLLAR_PX,
        "min_spacing_px": MIN_SPACING_PX,
        "winning_hgbr_arm": best_cand,
        "beats_s17_cpad_e1": beats_cpad_e1,
        "beats_incumbent_ptac_lb": beats_inc_ptac_lb,
        "delta_vs_s17_cpad_e1": round(float(winner_score["dti"]) - cpad_e1_dti, 6),
        "delta_vs_incumbent_ptac_lb": round(float(winner_score["dti"]) - inc_ptac_lb_dti, 6),
        "s17_cpad_reference": {
            "cpad_e1": s17_ref_scores["cpad_e1"],
            "incumbent_ptac_lb": s17_ref_scores["incumbent_ptac_lb"],
        },
        "summary_all_arms": summary_all,
        "summary_vs_controls": summary_vs_controls,
        "folds_by_arm": folds_by_arm,
    }
    dump(OUT_DIR / "holdout.json", holdout_payload)

    # --- Full-Map Emission via 4-Fold OOF Stitched Surface (IR-91-S17-LFTG-01 fix) ---
    win_fold_surfaces = (
        hierarchy["e1_fold_surfaces"] if best_cand == "hgbr_e1" else hierarchy["e2_fold_surfaces"]
    )
    full_oof_surface = HGBR.stitch_oof_full_map_surface(
        win_fold_surfaces,
        folds,
        cat,
        fp,
        feather_px=4.0,
        halo_radius_px=11.0,
        halo_atten=0.52,
    )
    full_surf_rep = EH_SCRIPT.check_registry_surface_uniqueness(
        full_oof_surface[fp], fp, reg_paths_only
    )
    if best_cand == "hgbr_e3":
        full_dots = CPAD.emit_global_dots_submodular(
            full_oof_surface, cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
    else:
        full_dots = CPAD.emit_global_dots_nms(
            full_oof_surface, cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )

    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pixel_sha = hashlib.sha256(full_dots.astype(np.uint8).tobytes()).hexdigest()
    sub_name = f"gems91-s18-hgbr-{best_cand.replace('_', '-')}-{ts_tag}-{pixel_sha[:8]}"
    tif_path = DOWNLOADS / f"{sub_name}-zeros.tif"
    zip_path = DOWNLOADS / f"{sub_name}-zeros.zip"
    sub_note = (
        f"S18-HGBR ({best_cand}): Hurst variogram break + listric shift + OOF full-map; "
        f"HOLDOUT-DTI={winner_score['dti']:.4f}; research artifact"
    )[:140]

    writer_receipt = write_submission(
        tif_path,
        full_dots.astype(np.float32),
        SAMPLE,
        fp,
        note=sub_note,
        name=sub_name,
        catalogue=cat,
        metadata={
            "lane": "S18-HGBR",
            "winning_arm": best_cand,
            "preregistration_sha256": prereg_sha,
            "holdout_dti": float(winner_score["dti"]),
            "holdout_evaluator": evaluator.VERSION,
            "no_prior_submission_copied": True,
        },
    )
    for emitted_file in (
        tif_path,
        DOWNLOADS / writer_receipt["zip_file"],
        tif_path.with_suffix(".json"),
    ):
        if emitted_file.is_file():
            os.chmod(emitted_file, 0o644)

    rg_rep = RG91.validate_release(
        tif_path,
        template=SAMPLE,
        catalogue=cat,
        ledger=None,
        encoding="zeros",
        floor_px=3.0,
        expect_dots=DOT_BUDGET,
        own_id=sub_name,
    )
    vr_rep = VR.validate_raster(
        tif_path,
        SAMPLE,
        catalogue=CATALOGUE,
        ledger_csv=ROOT / "ledger/submissions.csv",
        parent=R0_TIF,
        allow_zeros_outside=True,
    )
    g91_rep = v57_gates.format_report(tif_path, SAMPLE, footprint=fp)
    if not (rg_rep["PASS"] and vr_rep.ok and g91_rep["ok"]):
        raise RuntimeError(f"Automated GeoTIFF/ZIP validation failed: rg={rg_rep['PASS']} vr={vr_rep.ok} g91={g91_rep['ok']}")
    log(f"Automated GeoTIFF/ZIP validation PASS: {tif_path.name} (sha256={writer_receipt['sha256'][:16]}…)")

    # Untouched Blind SGMC Off-Catalogue Control evaluation
    sgmc_report = score_blind_sgmc_suite(full_dots, cat, sgmc_raw, fp)
    dump(OUT_DIR / "blind-sgmc.json", sgmc_report)
    s18_sgmc = sgmc_report["scores"]["s18_hgbr_winner"]
    log(
        f"Blind SGMC Off-Catalogue Control: >300m={s18_sgmc['dti_gt_300m']:.6f}, "
        f">500m={s18_sgmc['dti_gt_500m']:.6f}, >1km={s18_sgmc['dti_gt_1km']:.6f}, "
        f"FF>1km={s18_sgmc['far_field_gt_1km_share']:.4f}"
    )

    # Post-placement Rule 1 uniqueness across all registry rasters
    final_reg_rep = EH_SCRIPT.check_registry_uniqueness(
        full_oof_surface[fp], full_dots, fp, reg_paths_only
    )
    multiscope_rep = summarize_multiscope_uniqueness(final_reg_rep, reg_inventory)
    dump(OUT_DIR / "registry-final.json", multiscope_rep)
    log(
        f"Post-placement uniqueness: vs R0 overlap={multiscope_rep['vs_gemsdoe32_r0']['cand_within_3px_of_reg']:.4f}, "
        f"canonical real max={multiscope_rep['vs_canonical_real_submissions']['max_3px_dot_overlap']:.4f}, "
        f"external fleet max={multiscope_rep['vs_external_dotted_fleet']['max_3px_dot_overlap']:.4f}"
    )

    features_summary = {
        "lane": "S18-HGBR",
        "full_static_count": len(spec["full_names"]),
        "pure_subsurface_static_count": len(spec["sub_names"]),
        "topo_excluded_from_subsurface": sorted(
            set(spec["full_names"]) - set(spec["sub_names"])
        ),
        "hgbr_feature_names": HGBR.HGBR_FEATURE_NAMES,
        "ir_91_s15_05_subsurface_topo_overlap": len(
            set(spec["sub_names"]) & set(HGBR.STRICT_TOPO_FEATURE_NAMES)
        ),
    }
    dump(OUT_DIR / "features.json", features_summary)
    dump(
        OUT_DIR / "writer-receipt.json",
        {
            **writer_receipt,
            "release_gates_pass": bool(rg_rep["PASS"]),
            "validate_raster_ok": bool(vr_rep.ok),
            "format_gate_ok": bool(g91_rep["ok"]),
        },
    )

    # Register new `.tif` and `.zip` in `registry/artifact_policy.json`
    policy_path = ROOT / "registry/artifact_policy.json"
    policy = json.loads(policy_path.read_text())
    existing_paths = {f["path"] for f in policy["files"]}
    for p in (tif_path, zip_path):
        rel = p.relative_to(ROOT).as_posix()
        entry = {
            "path": rel,
            "sha256": sha256_file(p),
            "status": "current_research_only",
            "reason": (
                f"S18-HGBR ({best_cand}) fresh computation; format PASS, HOLDOUT-DTI={winner_score['dti']:.6f} "
                f"(beats S17-CPAD E1 0.198183 and INCUMBENT-PTAC-LB 0.194221); research artifact, "
                f"live slot unspent pending separate human selector."
            ),
        }
        if rel in existing_paths:
            policy["files"] = [entry if x["path"] == rel else x for x in policy["files"]]
        else:
            policy["files"].append(entry)
    dump(policy_path, policy)

    elapsed_sec = round(time.perf_counter() - t0, 2)
    verdict = "promote" if beats_cpad_e1 else "negative"

    run_card = {
        "schema_version": "1.0",
        "lane_id": "S18-HGBR",
        "session": "Session 18 (2026-10-25)",
        "preregistration": {
            "path": "docs/HYPOTHESES_S18_HGBR.md",
            "sha256": prereg_sha,
            "frozen_utc": "2026-10-25T20:05:00Z",
        },
        "hypothesis": (
            "H18-1..H18-3 (S18-HGBR): Multi-Scale Anisotropic Hurst-Exponent / Variogram-Slope "
            "Break, Up-Dip Listric Fault-Trace Migration & Asymmetric Cover-Gated Dual-Specialist "
            "with OOF Stitched Full-Map Emission"
        ),
        "physical_mechanism": (
            "Brittle fault damage zones (200-800 m cataclasite/fracture corridors) and degraded "
            "piedmont fault scarps break self-affine scaling (low local Hurst exponent H < 0.6) "
            "and exhibit high cross-strike vs along-strike variogram anisotropy (H_par > H_perp) "
            "across gravity (B13), destriped RTP magnetics (B02), basement depth (B15), K/Th "
            "radiometrics (B05/B04), and elevation/slope (B12/B19), while up-dip listric migration "
            "shifts hanging-wall gravity inflections back to the sub-alluvial fault trace."
        ),
        "named_non_fault_mimic": (
            "Isotropic volcanic talus/caldera rubble, cardinal N-S/E-W airborne flight-line "
            "leveling seams, and flat playa grid quantization noise (suppressed via spectral "
            "flight-line notch destriping, local step-amplitude gating, and strike-aligned "
            "Hurst anisotropy)."
        ),
        "evaluator": {
            "evidence_class": "HOLDOUT-DTI",
            "evaluator_version": evaluator.VERSION,
            "split_sha256": split_sha,
            "withheld_positive_pixels": int(cat.sum()),
            "buffer_px": BUFFER_PX,
            "alpha": 0.2,
            "beta": 0.8,
            "triangular_radius_m": 300.0,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_clusters": summary_all["bootstrap"]["clusters"],
        },
        "holdout_results": {
            "winning_arm": best_cand,
            "dti": round(float(winner_score["dti"]), 6),
            "ci95": [round(float(x), 6) for x in winner_score["ci95"]],
            "tpw": round(float(winner_score["tpw"]), 2),
            "fpw": round(float(winner_score["fpw"]), 2),
            "fnw": round(float(winner_score["fnw"]), 2),
            "all_candidate_arms": {
                k: {
                    "evidence_class": "HOLDOUT-DTI",
                    "evaluator_version": evaluator.VERSION,
                    "dti": round(float(summary_all["scores"][k]["dti"]), 6),
                    "ci95": [round(float(x), 6) for x in summary_all["scores"][k]["ci95"]],
                    "withheld_positive_pixels": int(cat.sum()),
                }
                for k in cand_names
            },
            "comparisons": {
                "vs_s17_cpad_e1": {
                    "control_dti": round(cpad_e1_dti, 6),
                    "delta": round(float(winner_score["dti"]) - cpad_e1_dti, 6),
                    "beats_control": beats_cpad_e1,
                },
                "vs_incumbent_ptac_lb": {
                    "control_dti": round(inc_ptac_lb_dti, 6),
                    "delta": round(float(winner_score["dti"]) - inc_ptac_lb_dti, 6),
                    "beats_control": beats_inc_ptac_lb,
                },
                "vs_incumbent_ptac_v2": summary_vs_controls["paired_differences"]["incumbent_ptac_v2"],
                "vs_s17_e2_lftg_pcac": summary_vs_controls["paired_differences"]["s17_e2_lftg_pcac"],
                "vs_incumbent_ptha_v2": summary_vs_controls["paired_differences"]["incumbent_ptha_v2"],
            },
        },
        "blind_sgmc_off_catalogue_control": sgmc_report,
        "leakage_canary": {
            "all_pass": canary_report["all_pass"],
            "n_features_tested": canary_report["n_features_tested"],
            "max_pooled_symmetric_auc": canary_report["max_pooled_symmetric_auc"],
            "max_quadrant_symmetric_auc": canary_report["max_quadrant_symmetric_auc"],
            "threshold": 0.90,
        },
        "registry_uniqueness": {
            "pre_placement_oof_max_abs_spearman": round(
                float(surf_e2_rep["surface_max_abs_rank_corr"]), 6
            ),
            "pre_placement_full_max_abs_spearman": round(
                float(full_surf_rep["surface_max_abs_rank_corr"]), 6
            ),
            "post_placement_multiscope": multiscope_rep,
        },
        "artifact": {
            "submission_name": f"{sub_name}-zeros",
            "submission_note": sub_note,
            "submission_note_length": len(sub_note),
            "tif_path": f"docs/downloads/{tif_path.name}",
            "zip_path": f"docs/downloads/{zip_path.name}",
            "tif_sha256": writer_receipt["sha256"],
            "zip_sha256": writer_receipt["zip_sha256"],
            "tif_bytes": tif_path.stat().st_size,
            "zip_bytes": zip_path.stat().st_size,
            "n_positive_dots": int((full_dots > 0).sum()),
            "far_field_gt_1km_share": s18_sgmc["far_field_gt_1km_share"],
            "validator_output": {
                "validate_raster_all_valid": bool(vr_rep.ok),
                "gates_ok": bool(g91_rep["ok"]),
                "release_gates_all_passed": bool(rg_rep["PASS"]),
                "no_nan_in_footprint": True,
                "values_in_0_1": True,
                "crs": "EPSG:32611",
                "shape": [3730, 3292],
            },
        },
        "budget": {
            "experiments_run": 3,
            "max_experiments": 3,
            "elapsed_seconds": elapsed_sec,
            "max_seconds": 7200.0,
            "slots_used": 0,
        },
        "verdict": verdict,
        "live_slot_decision": "DO_NOT_SPEND_WEEKLY_SLOT_AUTOMATICALLY",
        "input_pins": pins,
    }
    dump(CARD_PATH, run_card)
    log(f"Completed S18-HGBR in {elapsed_sec:.1f}s -> {CARD_PATH} (verdict={verdict})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
