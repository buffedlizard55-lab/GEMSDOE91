#!/usr/bin/env python3
"""Session 18 (`S18-CWGR`) Preregistered Experiment Runner (`H18-1`: `cwgr_e1`, `cwgr_e2`, `cwgr_e3`).

Strictly obeys `PARALLEL-RUN PROTOCOL` Rules 1-6:
  - Preregistered in `docs/HYPOTHESES_S18_CWGR.md` (`sha256=c6d217d6711bdbbfb34540df7618effeff0522a7b9f5424abcd93424d6432eba`).
  - Evaluates all 5 label-blind prior benchmarks (`cpad_e1`, `incumbent_ptac_lb`, `ced91`,
    `s16_pgrd`, `gravity_control`) alongside the 3 preregistered `S18-CWGR` arms
    (`cwgr_e1`, `cwgr_e2`, `cwgr_e3`) on unchanged `vendor/gems57/evaluate_holdout.py`
    (`gems57-pooled-hide-v2`, `60,988` withheld positives, `1,000` paired 20-km physical-block
    bootstrap draws, `seed=520810`), plus side-by-side `IR-91-S18-02` strict `37,654`-pooled
    footprint-proportional quota diagnostics and `BLIND-SGMC-CONTROL-DTI`.
  - Runs Rule 4 single-feature leak canaries (`AUC <= 0.90` pooled and in every quadrant)
    across all `155` static + `20` rank-logit OOF auto-context features (`175` total).
  - Runs Rule 1 pre-placement (`|rho| <= 0.90`) and final-dot (`3 px` overlap `<= 70%`)
    uniqueness gates across `registry/s18_comparison_inventory.json` (`108` verified paths /
    `99` unique SHA-256 rasters, `100%` on disk), packages `-zeros.tif` + `-zeros.zip` via
    untouched `vendor/gems57/submission_writer.py`, and updates `registry/artifact_policy.json`.
"""

from __future__ import annotations

import os

for _env_k in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
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
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score
import tifffile

import validate_raster as VR
from gems91 import (
    ced,
    cpad17 as CPAD,
    cwgr18 as CWGR,
    dd_vtc_pu as DD,
    hvdc as HVDC,
    mhtr_coda as MC,
    novelty as NOV,
    pgrd as PGRD,
    ptac14 as PTAC,
    ptha as PTHA,
    readiness,
    release_gates as RG91,
    spac_coda as SC,
)
from gems91.io import sha256_file
from scripts import run_ced
from vendor.gems57 import evaluate_holdout as evaluator, metric as v57_metric, spatial
from vendor.gems57.submission_writer import write_submission

SAMPLE = ROOT / "data/official/sample_submission.tif"
CATALOGUE = ROOT / "data/official/existing_faults.tif"
STACK = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
GDR_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"
SGMC_TIF = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
PREREG = ROOT / "docs/HYPOTHESES_S18_CWGR.md"
INVENTORY_PATH = ROOT / "registry/s18_comparison_inventory.json"
CARD_PATH = ROOT / "docs/run-card-S18-CWGR.json"
OUT_DIR = ROOT / "docs/s18"
CACHE_DIR = ROOT / "data/derived/s18"
S17_CACHE_DIR = ROOT / "data/derived/s17"

DOT_BUDGET = 37_654
COLLAR_PX = 3.05
MIN_SPACING_PX = 3.05
BUFFER_PX = 80
SEED_BASE = 20261025  # exact parity seed for prior baselines
CWGR_SEED_BASE = 20261800

# Restore local cols 34..41 (axial ridge, Anderson slip/dilation, multiphysics coincidence,
# local <=30 px GDR thermal) omitted in S17-CPAD while keeping regional basin coords out.
CWGR_STATIC_LOCAL_COLS: list[int] = list(range(42)) + [44, 45, 46, 47, 48]  # 47 cols


def dump(path: Path, obj: object) -> None:
    run_ced.dump(path, obj)


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def verify_all_inputs() -> dict[str, dict[str, object]]:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    wanted = {
        "sample_submission",
        "existing_faults",
        "training_features",
        "gdr_wellspring_in_footprint",
        "sgmc_faults_control",
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


def phase_summary(report: dict) -> dict:
    return {k: v for k, v in report.items() if k != "comparisons"}


def open_or_write_surface_mmap(
    path: Path, shape: tuple[int, int], arr: np.ndarray | None = None
) -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr is not None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        mm = np.memmap(tmp, dtype=np.float32, mode="w+", shape=shape)
        mm[:] = arr.astype(np.float32, copy=False)
        mm.flush()
        del mm
        os.replace(tmp, path)
    return np.memmap(path, dtype=np.float32, mode="r", shape=shape)


def open_or_write_table_mmap(
    path: Path, shape: tuple[int, int], arr: np.ndarray | None = None
) -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr is not None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        mm = np.memmap(tmp, dtype=np.float32, mode="w+", shape=shape)
        mm[:] = arr.astype(np.float32, copy=False)
        mm.flush()
        del mm
        os.replace(tmp, path)
    return np.memmap(path, dtype=np.float32, mode="r", shape=shape)


def compute_ac_mmap(path: Path, surface_2d: np.ndarray, footprint: np.ndarray) -> np.memmap:
    n_fp = int(footprint.sum())
    n_ac = len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)
    if path.is_file() and path.stat().st_size == n_fp * n_ac * 4:
        return np.memmap(path, dtype=np.float32, mode="r", shape=(n_fp, n_ac))
    ac_arr = SC.compute_spac_autocontext_features(
        np.asarray(surface_2d, dtype=np.float32), footprint
    )
    mm = open_or_write_table_mmap(path, (n_fp, n_ac), ac_arr)
    del ac_arr
    gc.collect()
    return mm


def fast_symmetric_auc(values_1d: np.ndarray, y_bool_1d: np.ndarray) -> tuple[float, float]:
    auc = float(roc_auc_score(y_bool_1d.astype(np.uint8), values_1d))
    return auc, max(auc, 1.0 - auc)


def build_feature_tables(fp: np.ndarray) -> dict[str, object]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    S17_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    shared_cache = ROOT / "data/derived/shared_stack_v1"
    shared_cache.mkdir(parents=True, exist_ok=True)

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
    log("6/7 Loading/building S17 CPAD 16-feature memmap")
    X_cpad, cpad_names, cpad_meta = CPAD.build_or_load_cpad_feature_memmap(
        features_tif=STACK, gdr_csv=GDR_CSV, footprint=fp, cache_dir=S17_CACHE_DIR
    )
    log("7/7 Loading/building novel S18 CWGR 18-feature steerable quadrature & fault-valve memmap")
    X_cwgr, cwgr_names, cwgr_meta = CWGR.build_or_load_cwgr_memmap(
        cache_dir=CACHE_DIR, geodawn_path=STACK, gdr_csv=GDR_CSV, footprint=fp
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
        "cpad_meta": cpad_meta,
        "X_cwgr": X_cwgr,
        "cwgr_names": list(cwgr_names),
        "cwgr_meta": cwgr_meta,
    }


def assemble_cwgr_blocks(tables: dict[str, object]) -> dict[str, object]:
    raw_blocks = [
        (tables["X_static"], CWGR_STATIC_LOCAL_COLS, tables["static_names"]),
        (tables["X_s11"], CPAD.S11_LOCAL_COLS, tables["s11_names"]),
        (tables["X_s12"], CPAD.S12_LOCAL_COLS, tables["s12_names"]),
        (tables["X_ptha"], CPAD.PTHA_LOCAL_COLS, tables["ptha_names"]),
        (tables["X_hvdc"], CPAD.HVDC_LOCAL_COLS, tables["hvdc_names"]),
        (tables["X_cpad"], CPAD.CPAD_LOCAL_COLS, tables["cpad_names"]),
        (tables["X_cwgr"], list(range(len(CWGR.CWGR_FEATURE_NAMES))), tables["cwgr_names"]),
    ]

    full_blocks: list[tuple[np.ndarray, list[int]]] = []
    sub_blocks: list[tuple[np.ndarray, list[int]]] = []
    full_names: list[str] = []
    sub_names: list[str] = []

    for arr, cols, names in raw_blocks:
        f_cols = list(cols)
        s_cols = [c for c in cols if names[c] not in CWGR.CWGR_STRICT_TOPO_FEATURE_NAMES]
        full_blocks.append((arr, f_cols))
        sub_blocks.append((arr, s_cols))
        full_names.extend(names[c] for c in f_cols)
        sub_names.extend(names[c] for c in s_cols)

    full_hard_targets = {
        "b19_det_elev_slope",
        "cwgr_quad_grav_crest",
        "cwgr_quad_mag_demag_trough",
        "cwgr_quad_rtp_odd_step",
        "cwgr_piedmont_microscarp_quad",
    }
    sub_hard_targets = {
        "cwgr_quad_grav_crest",
        "cwgr_quad_mag_demag_trough",
        "cwgr_quad_rtp_odd_step",
        "cpad_cooper_theta_grav",
        "s12_tmi_asig_log",
    }
    full_hard_cols = [i for i, n in enumerate(full_names) if n in full_hard_targets]
    sub_hard_cols = [i for i, n in enumerate(sub_names) if n in sub_hard_targets]

    leaked = set(sub_names) & set(CWGR.CWGR_STRICT_TOPO_FEATURE_NAMES)
    if leaked:
        raise AssertionError(f"Topographic feature leaked into Pure-Subsurface Specialist: {leaked}")

    # Dedicated Stage-2 Structural-Topology & Quadrature-Crest static columns (8 invariants, 0 raw DEM)
    topo_cwgr_cols = [1, 2, 4, 6, 8, 11, 14, 15]
    topo_static_names = [tables["cwgr_names"][c] for c in topo_cwgr_cols]

    return {
        "full_blocks": full_blocks,
        "sub_blocks": sub_blocks,
        "full_names": full_names,
        "sub_names": sub_names,
        "full_hard_cols": full_hard_cols,
        "sub_hard_cols": sub_hard_cols,
        "topo_cwgr_cols": topo_cwgr_cols,
        "topo_static_names": topo_static_names,
    }


def run_incumbent_ptac_lb(
    tables: dict[str, object], folds: list[dict], fp: np.ndarray
) -> tuple[list[np.ndarray], dict[str, object]]:
    """Exact deterministic OOF replay of `INCUMBENT-PTAC-LB` (`0.194221 HOLDOUT-DTI`)."""
    inc_dir = S17_CACHE_DIR / "incumbent_ptac_lb"
    inc_dir.mkdir(parents=True, exist_ok=True)
    shape = fp.shape
    ptac_static_cols = list(range(34)) + [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]
    base_blocks = [
        (tables["X_static"], ptac_static_cols),
        (tables["X_s11"], list(range(16))),
        (tables["X_s12"], list(range(20))),
        (tables["X_ptha"], list(range(20))),
        (tables["X_hvdc"], list(range(18))),
    ]
    hard_cols = [18, 45, 61]

    pair_surfs: dict[tuple[int, int], np.memmap] = {}
    for a, b in itertools.combinations(range(4), 2):
        held = [q for q in range(4) if q not in (a, b)]
        c, d = held[0], held[1]
        p_mmap = inc_dir / f"pair_{a}_{b}.f32.mmap"
        if p_mmap.is_file() and p_mmap.stat().st_size == shape[0] * shape[1] * 4:
            pair_surfs[(a, b)] = open_or_write_surface_mmap(p_mmap, shape)
            continue
        train_ab = folds[c]["train"] & folds[d]["train"]
        vis_ab = folds[c]["visible"] & folds[d]["visible"] & train_ab
        eval_cd = folds[c]["region"] | folds[d]["region"]
        log(f"[INCUMBENT-PTAC-LB] Fitting pairwise Stage-1 ({a},{b})")
        surf, _ = CPAD.fit_predict_specialist(
            blocks=base_blocks,
            hard_neg_cols_in_stack=hard_cols,
            visible_faults=vis_ab,
            train_domain=train_ab,
            footprint=fp,
            seed=SEED_BASE + 100 + 10 * a + b,
            predict_mask=eval_cd,
        )
        pair_surfs[(a, b)] = open_or_write_surface_mmap(p_mmap, shape, surf)
        del surf
        gc.collect()

    oof_dots: list[np.ndarray] = []
    for q in range(4):
        s1_path = inc_dir / f"oof_s1_q{q}.f32.mmap"
        if s1_path.is_file() and s1_path.stat().st_size == shape[0] * shape[1] * 4:
            s1_oof = open_or_write_surface_mmap(s1_path, shape)
        else:
            log(f"[INCUMBENT-PTAC-LB] Fitting OOF Stage-1 fold {q}")
            surf, _ = CPAD.fit_predict_specialist(
                blocks=base_blocks,
                hard_neg_cols_in_stack=hard_cols,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 200 + q,
                predict_mask=folds[q]["region"],
            )
            s1_oof = open_or_write_surface_mmap(s1_path, shape, surf)
            del surf
            gc.collect()

        stitch_s1 = np.zeros(shape, dtype=np.float32)
        stitch_s1[folds[q]["region"]] = s1_oof[folds[q]["region"]]
        for m in range(4):
            if m == q:
                continue
            tp = tuple(sorted(x for x in range(4) if x not in (q, m)))
            stitch_s1[folds[m]["region"]] = pair_surfs[tp][folds[m]["region"]]

        ac_q = compute_ac_mmap(inc_dir / f"ac_stitch_q{q}.f32.mmap", stitch_s1, fp)
        s2_path = inc_dir / f"oof_s2_pool_q{q}.f32.mmap"
        if s2_path.is_file() and s2_path.stat().st_size == shape[0] * shape[1] * 4:
            pooled_q = open_or_write_surface_mmap(s2_path, shape)
        else:
            log(f"[INCUMBENT-PTAC-LB] Fitting Stage-2 fold {q}")
            s2_blocks = base_blocks + [(ac_q, list(range(10)))]
            s2_cal, _ = CPAD.fit_predict_specialist(
                blocks=s2_blocks,
                hard_neg_cols_in_stack=hard_cols,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 300 + q,
            )
            pooled_arr = PTAC.log_opinion_pool(stitch_s1, s2_cal, fp, stage2_weight=0.65)
            pooled_q = open_or_write_surface_mmap(s2_path, shape, pooled_arr)
            del s2_cal, pooled_arr
            gc.collect()

        del stitch_s1, ac_q
        dots_q = CPAD.emit_global_dots_submodular(
            np.asarray(pooled_q, dtype=np.float32),
            folds[q]["visible"],
            fp,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        )
        oof_dots.append(dots_q > 0)
        del pooled_q
        gc.collect()

    return oof_dots, {"architecture": "S14-PTAC E2 on spatial.folds(buffer_px=80)"}


def run_cpad_e1_baseline(
    tables: dict[str, object], folds: list[dict], fp: np.ndarray
) -> list[np.ndarray]:
    """Exact deterministic OOF replay of `S17-CPAD E1` (`0.198183 HOLDOUT-DTI`) for paired block bootstrap."""
    cpad_dir = S17_CACHE_DIR / "cpad17_models"
    cpad_dir.mkdir(parents=True, exist_ok=True)
    shape = fp.shape

    raw_blocks = [
        (tables["X_static"], CPAD.STATIC_LOCAL_COLS, tables["static_names"]),
        (tables["X_s11"], CPAD.S11_LOCAL_COLS, tables["s11_names"]),
        (tables["X_s12"], CPAD.S12_LOCAL_COLS, tables["s12_names"]),
        (tables["X_ptha"], CPAD.PTHA_LOCAL_COLS, tables["ptha_names"]),
        (tables["X_hvdc"], CPAD.HVDC_LOCAL_COLS, tables["hvdc_names"]),
        (tables["X_cpad"], CPAD.CPAD_LOCAL_COLS, tables["cpad_names"]),
    ]
    full_blocks, sub_blocks, full_names, sub_names = [], [], [], []
    for arr, cols, names in raw_blocks:
        f_cols = list(cols)
        s_cols = [c for c in cols if names[c] not in CPAD.STRICT_TOPO_FEATURE_NAMES]
        full_blocks.append((arr, f_cols))
        sub_blocks.append((arr, s_cols))
        full_names.extend(names[c] for c in f_cols)
        sub_names.extend(names[c] for c in s_cols)
    full_hard = [
        i
        for i, n in enumerate(full_names)
        if n
        in {
            "b19_det_elev_slope",
            "cpad_cooper_theta_grav",
            "cpad_cooper_theta_rtp",
            "cpad_claycap_subsurface_baffle",
        }
    ]
    sub_hard = [
        i
        for i, n in enumerate(sub_names)
        if n
        in {
            "cpad_cooper_theta_grav",
            "cpad_cooper_theta_rtp",
            "cpad_claycap_subsurface_baffle",
            "s12_tmi_asig_log",
        }
    ]

    pair_full: dict[tuple[int, int], np.memmap] = {}
    pair_sub: dict[tuple[int, int], np.memmap] = {}
    for a, b in itertools.combinations(range(4), 2):
        held = [q for q in range(4) if q not in (a, b)]
        c, d = held[0], held[1]
        train_ab = folds[c]["train"] & folds[d]["train"]
        vis_ab = folds[c]["visible"] & folds[d]["visible"] & train_ab
        eval_cd = folds[c]["region"] | folds[d]["region"]

        pf_path = cpad_dir / f"pair_full_{a}_{b}.f32.mmap"
        if pf_path.is_file() and pf_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape)
        else:
            log(f"[S17-CPAD-E1-REF] Fitting pairwise Stage-1 Full ({a},{b})")
            surf, _ = CPAD.fit_predict_specialist(
                blocks=full_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=fp,
                seed=SEED_BASE + 1000 + 10 * a + b,
                predict_mask=eval_cd,
            )
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape, surf)
            del surf
            gc.collect()

        ps_path = cpad_dir / f"pair_sub_{a}_{b}.f32.mmap"
        if ps_path.is_file() and ps_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape)
        else:
            log(f"[S17-CPAD-E1-REF] Fitting pairwise Stage-1 Sub ({a},{b})")
            surf, _ = CPAD.fit_predict_specialist(
                blocks=sub_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=fp,
                seed=SEED_BASE + 2000 + 10 * a + b,
                predict_mask=eval_cd,
            )
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape, surf)
            del surf
            gc.collect()

    oof_s1_full: list[np.memmap] = []
    oof_s1_sub: list[np.memmap] = []
    for q in range(4):
        of_path = cpad_dir / f"oof_s1_full_q{q}.f32.mmap"
        if of_path.is_file() and of_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape))
        else:
            log(f"[S17-CPAD-E1-REF] Fitting OOF Stage-1 Full fold {q}")
            surf, _ = CPAD.fit_predict_specialist(
                blocks=full_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 3000 + q,
                predict_mask=folds[q]["region"],
            )
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape, surf))
            del surf
            gc.collect()

        os_path = cpad_dir / f"oof_s1_sub_q{q}.f32.mmap"
        if os_path.is_file() and os_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape))
        else:
            log(f"[S17-CPAD-E1-REF] Fitting OOF Stage-1 Sub fold {q}")
            surf, _ = CPAD.fit_predict_specialist(
                blocks=sub_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 4000 + q,
                predict_mask=folds[q]["region"],
            )
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape, surf))
            del surf
            gc.collect()

    e1_dots: list[np.ndarray] = []
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

        ac_f_q = compute_ac_mmap(cpad_dir / f"ac_full_q{q}.f32.mmap", stitch_f, fp)
        ac_s_q = compute_ac_mmap(cpad_dir / f"ac_sub_q{q}.f32.mmap", stitch_s, fp)
        s2f_path = cpad_dir / f"oof_s2_full_q{q}.f32.mmap"
        if s2f_path.is_file() and s2f_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_full_q = open_or_write_surface_mmap(s2f_path, shape)
        else:
            log(f"[S17-CPAD-E1-REF] Fitting OOF Stage-2 Full fold {q}")
            s2f_blocks = full_blocks + [(ac_f_q, list(range(10))), (ac_s_q, list(range(10)))]
            surf, _ = CPAD.fit_predict_specialist(
                blocks=s2f_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 5000 + q,
            )
            s2_full_q = open_or_write_surface_mmap(s2f_path, shape, surf)
            del surf
            gc.collect()

        surf_e1_q = PTAC.log_opinion_pool(
            stitch_f, np.asarray(s2_full_q, dtype=np.float32), fp, stage2_weight=0.66
        )
        d_e1 = CPAD.emit_global_dots_nms(
            surf_e1_q,
            folds[q]["visible"],
            fp,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        )
        e1_dots.append(d_e1 > 0)
        del stitch_f, stitch_s, ac_f_q, ac_s_q, s2_full_q, surf_e1_q
        gc.collect()

    return e1_dots


def run_cwgr_hierarchy(
    tables: dict[str, object],
    spec: dict[str, object],
    folds: list[dict],
    cat: np.ndarray,
    fp: np.ndarray,
) -> dict[str, object]:
    """Fit cross-fitted `S18-CWGR` Tri-Specialist hierarchy (`cwgr_e1`, `cwgr_e2`, `cwgr_e3`)."""
    cwgr_dir = CACHE_DIR / "cwgr18_models"
    cwgr_dir.mkdir(parents=True, exist_ok=True)
    shape = fp.shape

    full_blocks = spec["full_blocks"]
    sub_blocks = spec["sub_blocks"]
    full_hard = spec["full_hard_cols"]
    sub_hard = spec["sub_hard_cols"]
    topo_cwgr_cols = spec["topo_cwgr_cols"]

    # Unified multi-physics crest concordance (subsurface crest + piedmont micro-scarp)
    sub_crest_fp = np.asarray(tables["X_cwgr"][:, 14], dtype=np.float32)
    pied_crest_fp = np.asarray(tables["X_cwgr"][:, 15], dtype=np.float32)
    crest_fp = np.clip(0.72 * sub_crest_fp + 0.28 * pied_crest_fp, 0.0, 1.0).astype(np.float32)

    vis_grid = np.zeros(shape, dtype=np.float32)
    vis_grid[fp] = np.asarray(tables["X_cwgr"][:, 17], dtype=np.float32)
    vis_flat = vis_grid.ravel()
    fp_flat = fp.ravel()
    del vis_grid

    area_quotas = CWGR.compute_fold_area_quotas(folds, fp, total_budget=DOT_BUDGET)

    # --- Step A: 6 Pairwise 2-quadrant Stage-1 fits (Full + Pure-Subsurface) ---
    pair_full: dict[tuple[int, int], np.memmap] = {}
    pair_sub: dict[tuple[int, int], np.memmap] = {}
    calibration_log: list[dict[str, object]] = []

    for a, b in itertools.combinations(range(4), 2):
        held = [q for q in range(4) if q not in (a, b)]
        c, d = held[0], held[1]
        train_ab = folds[c]["train"] & folds[d]["train"]
        vis_ab = folds[c]["visible"] & folds[d]["visible"] & train_ab
        eval_cd = folds[c]["region"] | folds[d]["region"]

        pf_path = cwgr_dir / f"pair_full_{a}_{b}.f32.mmap"
        if pf_path.is_file() and pf_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape)
        else:
            log(f"[S18-CWGR] Fitting pairwise Stage-1 Full ({a},{b})")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=full_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=fp,
                seed=CWGR_SEED_BASE + 100 + 10 * a + b,
                predict_mask=eval_cd,
            )
            calibration_log.append({"split": f"pair_{a}_{b}", "specialist": "full", **meta})
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape, surf)
            del surf
            gc.collect()

        ps_path = cwgr_dir / f"pair_sub_{a}_{b}.f32.mmap"
        if ps_path.is_file() and ps_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape)
        else:
            log(f"[S18-CWGR] Fitting pairwise Stage-1 Pure-Subsurface ({a},{b})")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=sub_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=fp,
                seed=CWGR_SEED_BASE + 200 + 10 * a + b,
                predict_mask=eval_cd,
            )
            calibration_log.append(
                {"split": f"pair_{a}_{b}", "specialist": "pure_subsurface", **meta}
            )
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape, surf)
            del surf
            gc.collect()

    # --- Step B: 4 OOF 3-quadrant Stage-1 fits (Full + Pure-Subsurface) ---
    oof_s1_full: list[np.memmap] = []
    oof_s1_sub: list[np.memmap] = []
    for q in range(4):
        of_path = cwgr_dir / f"oof_s1_full_q{q}.f32.mmap"
        if of_path.is_file() and of_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape))
        else:
            log(f"[S18-CWGR] Fitting OOF Stage-1 Full fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=full_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=CWGR_SEED_BASE + 300 + q,
                predict_mask=folds[q]["region"],
            )
            calibration_log.append({"split": f"oof_q{q}", "specialist": "full", **meta})
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape, surf))
            del surf
            gc.collect()

        os_path = cwgr_dir / f"oof_s1_sub_q{q}.f32.mmap"
        if os_path.is_file() and os_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape))
        else:
            log(f"[S18-CWGR] Fitting OOF Stage-1 Pure-Subsurface fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=sub_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=CWGR_SEED_BASE + 400 + q,
                predict_mask=folds[q]["region"],
            )
            calibration_log.append(
                {"split": f"oof_q{q}", "specialist": "pure_subsurface", **meta}
            )
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape, surf))
            del surf
            gc.collect()

    # --- Step C: Per-fold Rank-Logit AC + Tri-Specialist Stage-2 (`cwgr_e1`, `cwgr_e2`, `cwgr_e3`) ---
    e1_dots_folds: list[np.ndarray] = []
    e2_dots_folds: list[np.ndarray] = []
    e3_dots_folds: list[np.ndarray] = []
    e1_quota_folds: list[np.ndarray] = []
    e2_quota_folds: list[np.ndarray] = []
    e3_quota_folds: list[np.ndarray] = []
    rank_ac_audit: list[dict[str, object]] = []
    sar_propensity_log: list[dict[str, object]] = []

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

        # IR-91-S17-01 fix: label-free mid-rank probit-logistic quadrant standardization before spac_coda
        std_f = CWGR.rank_logit_standardize_per_quadrant(stitch_f, folds, fp)
        std_s = CWGR.rank_logit_standardize_per_quadrant(stitch_s, folds, fp)
        q_means_before = [float(stitch_f[folds[m]["region"]].mean()) for m in range(4)]
        q_means_after = [float(std_f[folds[m]["region"]].mean()) for m in range(4)]
        q_p95_after = [float(np.percentile(std_f[folds[m]["region"]], 95.0)) for m in range(4)]
        rank_ac_audit.append(
            {
                "fold": q,
                "raw_quadrant_means": [round(x, 6) for x in q_means_before],
                "standardized_quadrant_means": [round(x, 6) for x in q_means_after],
                "standardized_quadrant_p95": [round(x, 6) for x in q_p95_after],
                "test_to_train_mean_ratio": round(
                    q_means_after[q] / (sum(q_means_after[m] for m in range(4) if m != q) / 3.0),
                    6,
                ),
            }
        )

        ac_f_q = compute_ac_mmap(cwgr_dir / f"ac_rank_full_q{q}.f32.mmap", std_f, fp)
        ac_s_q = compute_ac_mmap(cwgr_dir / f"ac_rank_sub_q{q}.f32.mmap", std_s, fp)
        del std_f, std_s

        s2f_blocks = full_blocks + [(ac_f_q, list(range(10))), (ac_s_q, list(range(10)))]
        s2s_blocks = sub_blocks + [(ac_s_q, list(range(10)))]
        s2t_blocks = [
            (ac_f_q, list(range(10))),
            (ac_s_q, list(range(10))),
            (tables["X_cwgr"], topo_cwgr_cols),
        ]
        topo_hard = [0, 10, 20, 26]  # ac_full_0, ac_sub_0, cwgr_quad_grav_crest, sub_skeleton

        vis_q = folds[q]["visible"] & folds[q]["train"]
        dom_q = folds[q]["train"]

        # Unweighted SCAR Stage-2 Tri-Specialists (`cwgr_e1`)
        p_f_path = cwgr_dir / f"oof_s2_full_unw_q{q}.f32.mmap"
        if p_f_path.is_file() and p_f_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_f_unw = open_or_write_surface_mmap(p_f_path, shape)
        else:
            log(f"[S18-CWGR E1] Fitting unweighted Stage-2 Full fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=s2f_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=vis_q,
                train_domain=dom_q,
                footprint=fp,
                seed=CWGR_SEED_BASE + 500 + q,
            )
            calibration_log.append({"split": f"s2_unw_q{q}", "specialist": "full", **meta})
            s2_f_unw = open_or_write_surface_mmap(p_f_path, shape, surf)
            del surf

        p_s_path = cwgr_dir / f"oof_s2_sub_unw_q{q}.f32.mmap"
        if p_s_path.is_file() and p_s_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_s_unw = open_or_write_surface_mmap(p_s_path, shape)
        else:
            log(f"[S18-CWGR E1] Fitting unweighted Stage-2 Pure-Subsurface fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=s2s_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=vis_q,
                train_domain=dom_q,
                footprint=fp,
                seed=CWGR_SEED_BASE + 600 + q,
            )
            calibration_log.append(
                {"split": f"s2_unw_q{q}", "specialist": "pure_subsurface", **meta}
            )
            s2_s_unw = open_or_write_surface_mmap(p_s_path, shape, surf)
            del surf

        p_t_path = cwgr_dir / f"oof_s2_topo_unw_q{q}.f32.mmap"
        if p_t_path.is_file() and p_t_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_t_unw = open_or_write_surface_mmap(p_t_path, shape)
        else:
            log(f"[S18-CWGR E1] Fitting unweighted Stage-2 Topology Specialist fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=s2t_blocks,
                hard_neg_cols_in_stack=topo_hard,
                visible_faults=vis_q,
                train_domain=dom_q,
                footprint=fp,
                seed=CWGR_SEED_BASE + 700 + q,
                topology_mode=True,
            )
            calibration_log.append({"split": f"s2_unw_q{q}", "specialist": "topology", **meta})
            s2_t_unw = open_or_write_surface_mmap(p_t_path, shape, surf)
            del surf

        surf_e1_q = CWGR.pool_tri_specialists_logit(
            np.asarray(s2_f_unw, dtype=np.float32),
            np.asarray(s2_s_unw, dtype=np.float32),
            np.asarray(s2_t_unw, dtype=np.float32),
            stitch_f,
            fp,
            w_full=0.46,
            w_sub=0.20,
            w_topo=0.20,
            w_s1=0.14,
            crest_fp=crest_fp,
            crest_gain=0.16,
        )
        del s2_f_unw, s2_s_unw, s2_t_unw
        gc.collect()

        # SAR Propensity-Weighted Stage-2 Tri-Specialists (`cwgr_e2` & `cwgr_e3`)
        e_hat_flat, w_pos_flat, sar_diag = CWGR.estimate_sar_propensity(
            vis_flat, fp_flat, dom_q.ravel(), vis_q.ravel()
        )
        sar_propensity_log.append({"fold": q, **sar_diag})
        pos_w_fp = w_pos_flat[fp_flat]
        e_hat_2d = e_hat_flat.reshape(shape)

        pw_f_path = cwgr_dir / f"oof_s2_full_sar_q{q}.f32.mmap"
        if pw_f_path.is_file() and pw_f_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_f_sar = open_or_write_surface_mmap(pw_f_path, shape)
        else:
            log(f"[S18-CWGR E2] Fitting SAR-weighted Stage-2 Full fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=s2f_blocks,
                hard_neg_cols_in_stack=full_hard,
                visible_faults=vis_q,
                train_domain=dom_q,
                footprint=fp,
                seed=CWGR_SEED_BASE + 800 + q,
                pos_weights_fp=pos_w_fp,
            )
            calibration_log.append({"split": f"s2_sar_q{q}", "specialist": "full", **meta})
            s2_f_sar = open_or_write_surface_mmap(pw_f_path, shape, surf)
            del surf

        pw_s_path = cwgr_dir / f"oof_s2_sub_sar_q{q}.f32.mmap"
        if pw_s_path.is_file() and pw_s_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_s_sar = open_or_write_surface_mmap(pw_s_path, shape)
        else:
            log(f"[S18-CWGR E2] Fitting SAR-weighted Stage-2 Pure-Subsurface fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=s2s_blocks,
                hard_neg_cols_in_stack=sub_hard,
                visible_faults=vis_q,
                train_domain=dom_q,
                footprint=fp,
                seed=CWGR_SEED_BASE + 900 + q,
                pos_weights_fp=pos_w_fp,
            )
            calibration_log.append(
                {"split": f"s2_sar_q{q}", "specialist": "pure_subsurface", **meta}
            )
            s2_s_sar = open_or_write_surface_mmap(pw_s_path, shape, surf)
            del surf

        pw_t_path = cwgr_dir / f"oof_s2_topo_sar_q{q}.f32.mmap"
        if pw_t_path.is_file() and pw_t_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_t_sar = open_or_write_surface_mmap(pw_t_path, shape)
        else:
            log(f"[S18-CWGR E2] Fitting SAR-weighted Stage-2 Topology Specialist fold {q}")
            surf, meta = CWGR.fit_predict_specialist_cwgr(
                blocks=s2t_blocks,
                hard_neg_cols_in_stack=topo_hard,
                visible_faults=vis_q,
                train_domain=dom_q,
                footprint=fp,
                seed=CWGR_SEED_BASE + 950 + q,
                pos_weights_fp=pos_w_fp,
                topology_mode=True,
            )
            calibration_log.append({"split": f"s2_sar_q{q}", "specialist": "topology", **meta})
            s2_t_sar = open_or_write_surface_mmap(pw_t_path, shape, surf)
            del surf

        surf_e2_q = CWGR.pool_tri_specialists_logit(
            np.asarray(s2_f_sar, dtype=np.float32),
            np.asarray(s2_s_sar, dtype=np.float32),
            np.asarray(s2_t_sar, dtype=np.float32),
            stitch_f,
            fp,
            w_full=0.45,
            w_sub=0.22,
            w_topo=0.20,
            w_s1=0.13,
            crest_fp=crest_fp,
            crest_gain=0.18,
        )

        # Arm E3: Analytical Unmapped-Fault Posterior P(Y=1 | S=0, x) anchored on Sub+Topo
        sub_dom_q = CWGR.pool_tri_specialists_logit(
            np.asarray(s2_f_sar, dtype=np.float32),
            np.asarray(s2_s_sar, dtype=np.float32),
            np.asarray(s2_t_sar, dtype=np.float32),
            stitch_s,
            fp,
            w_full=0.28,
            w_sub=0.34,
            w_topo=0.28,
            w_s1=0.10,
            crest_fp=sub_crest_fp,
            crest_gain=0.24,
        )
        surf_e3_q = CWGR.compute_unmapped_fault_posterior(sub_dom_q, e_hat_2d, fp, lambda_e=0.65)
        del s2_f_sar, s2_s_sar, s2_t_sar, sub_dom_q, e_hat_2d, e_hat_flat, w_pos_flat, pos_w_fp
        del stitch_f, stitch_s, ac_f_q, ac_s_q
        gc.collect()

        dots_cache = cwgr_dir / f"emitted_dots_q{q}.npz"
        if dots_cache.is_file():
            z = np.load(dots_cache)
            e1_dots_folds.append(z["e1"] > 0)
            e2_dots_folds.append(z["e2"] > 0)
            e3_dots_folds.append(z["e3"] > 0)
            e1_quota_folds.append(z["e1_q"] > 0)
            e2_quota_folds.append(z["e2_q"] > 0)
            e3_quota_folds.append(z["e3_q"] > 0)
            del z, surf_e1_q, surf_e2_q, surf_e3_q
            gc.collect()
            continue

        log(f"[S18-CWGR] Emitting global + area-quota submodular dots for fold {q} (E1, E2, E3)")
        d_e1 = (
            CWGR.emit_cwgr_submodular_skeleton(
                surf_e1_q,
                folds[q]["visible"],
                fp,
                budget=DOT_BUDGET,
                collar_px=COLLAR_PX,
                min_spacing_px=MIN_SPACING_PX,
            )
            > 0
        )
        d_e2 = (
            CWGR.emit_cwgr_submodular_skeleton(
                surf_e2_q,
                folds[q]["visible"],
                fp,
                budget=DOT_BUDGET,
                collar_px=COLLAR_PX,
                min_spacing_px=MIN_SPACING_PX,
            )
            > 0
        )
        d_e3 = (
            CWGR.emit_cwgr_submodular_skeleton(
                surf_e3_q,
                folds[q]["visible"],
                fp,
                budget=DOT_BUDGET,
                collar_px=COLLAR_PX,
                min_spacing_px=MIN_SPACING_PX,
            )
            > 0
        )

        # IR-91-S18-02 strict 37,654-pooled footprint-proportional quota control
        q_budget = area_quotas[q]
        dq_e1 = (
            CWGR.emit_fold_quota_dots_submodular(
                surf_e1_q, fp, folds[q]["visible"], folds[q]["region"], q_budget
            )
            > 0
        )
        dq_e2 = (
            CWGR.emit_fold_quota_dots_submodular(
                surf_e2_q, fp, folds[q]["visible"], folds[q]["region"], q_budget
            )
            > 0
        )
        dq_e3 = (
            CWGR.emit_fold_quota_dots_submodular(
                surf_e3_q, fp, folds[q]["visible"], folds[q]["region"], q_budget
            )
            > 0
        )
        np.savez_compressed(
            dots_cache,
            e1=d_e1.astype(np.uint8),
            e2=d_e2.astype(np.uint8),
            e3=d_e3.astype(np.uint8),
            e1_q=dq_e1.astype(np.uint8),
            e2_q=dq_e2.astype(np.uint8),
            e3_q=dq_e3.astype(np.uint8),
        )
        e1_dots_folds.append(d_e1)
        e2_dots_folds.append(d_e2)
        e3_dots_folds.append(d_e3)
        e1_quota_folds.append(dq_e1)
        e2_quota_folds.append(dq_e2)
        e3_quota_folds.append(dq_e3)
        del surf_e1_q, surf_e2_q, surf_e3_q
        gc.collect()

    # --- Step D: Full 4-quadrant inference surfaces for E1, E2, E3 ---
    stitched_oof_f = np.zeros(shape, dtype=np.float32)
    stitched_oof_s = np.zeros(shape, dtype=np.float32)
    for q in range(4):
        stitched_oof_f[folds[q]["region"]] = oof_s1_full[q][folds[q]["region"]]
        stitched_oof_s[folds[q]["region"]] = oof_s1_sub[q][folds[q]["region"]]

    std_oof_f = CWGR.rank_logit_standardize_per_quadrant(stitched_oof_f, folds, fp)
    std_oof_s = CWGR.rank_logit_standardize_per_quadrant(stitched_oof_s, folds, fp)
    ac_oof_f = compute_ac_mmap(cwgr_dir / "ac_rank_oof_mosaic_full.f32.mmap", std_oof_f, fp)
    ac_oof_s = compute_ac_mmap(cwgr_dir / "ac_rank_oof_mosaic_sub.f32.mmap", std_oof_s, fp)
    del stitched_oof_f, stitched_oof_s, std_oof_f, std_oof_s

    ff_s1_path = cwgr_dir / "full_s1_full.f32.mmap"
    if ff_s1_path.is_file() and ff_s1_path.stat().st_size == shape[0] * shape[1] * 4:
        full_s1_f = open_or_write_surface_mmap(ff_s1_path, shape)
    else:
        log("[S18-CWGR] Fitting 4-quadrant full Stage-1 Full")
        surf, meta = CWGR.fit_predict_specialist_cwgr(
            blocks=full_blocks,
            hard_neg_cols_in_stack=full_hard,
            visible_faults=cat & fp,
            train_domain=fp,
            footprint=fp,
            seed=CWGR_SEED_BASE + 1000,
        )
        calibration_log.append({"split": "full_4quad", "specialist": "full", **meta})
        full_s1_f = open_or_write_surface_mmap(ff_s1_path, shape, surf)
        del surf

    fs_s1_path = cwgr_dir / "full_s1_sub.f32.mmap"
    if fs_s1_path.is_file() and fs_s1_path.stat().st_size == shape[0] * shape[1] * 4:
        full_s1_s = open_or_write_surface_mmap(fs_s1_path, shape)
    else:
        log("[S18-CWGR] Fitting 4-quadrant full Stage-1 Pure-Subsurface")
        surf, meta = CWGR.fit_predict_specialist_cwgr(
            blocks=sub_blocks,
            hard_neg_cols_in_stack=sub_hard,
            visible_faults=cat & fp,
            train_domain=fp,
            footprint=fp,
            seed=CWGR_SEED_BASE + 1100,
        )
        calibration_log.append({"split": "full_4quad", "specialist": "pure_subsurface", **meta})
        full_s1_s = open_or_write_surface_mmap(fs_s1_path, shape, surf)
        del surf

    std_infer_f = CWGR.rank_logit_standardize_per_quadrant(
        np.asarray(full_s1_f, dtype=np.float32), folds, fp
    )
    std_infer_s = CWGR.rank_logit_standardize_per_quadrant(
        np.asarray(full_s1_s, dtype=np.float32), folds, fp
    )
    ac_infer_f = compute_ac_mmap(cwgr_dir / "ac_rank_infer_full.f32.mmap", std_infer_f, fp)
    ac_infer_s = compute_ac_mmap(cwgr_dir / "ac_rank_infer_sub.f32.mmap", std_infer_s, fp)
    del std_infer_f, std_infer_s

    s2f_oof_blocks = full_blocks + [(ac_oof_f, list(range(10))), (ac_oof_s, list(range(10)))]
    s2s_oof_blocks = sub_blocks + [(ac_oof_s, list(range(10)))]
    s2t_oof_blocks = [
        (ac_oof_f, list(range(10))),
        (ac_oof_s, list(range(10))),
        (tables["X_cwgr"], topo_cwgr_cols),
    ]
    topo_hard = [0, 10, 20, 26]

    # Fit Stage-2 on strictly OOF mosaic AC, evaluate on 4-quadrant inference AC!
    def _fit_s2_full_map(
        oof_blocks,
        infer_blocks,
        hard_cols,
        seed,
        out_path: Path,
        pos_w_fp: np.ndarray | None = None,
        topo: bool = False,
    ) -> np.memmap:
        if out_path.is_file() and out_path.stat().st_size == shape[0] * shape[1] * 4:
            return open_or_write_surface_mmap(out_path, shape)
        # Fit on OOF AC (`predict_mask` empty first? No — fit_predict_specialist_cwgr predicts on `blocks`!)
        # To train on OOF AC and predict on infer AC without duplicating code, build a clean helper:
        rng = np.random.default_rng(seed)
        vis = cat & fp
        d_vis = ndi.distance_transform_edt(~vis)
        pos_idx = np.flatnonzero(vis[fp])
        neg_pool = np.flatnonzero((~vis[fp]) & (d_vis[fp] > 3.5))
        target_neg = min(int(round(3.65 * pos_idx.size)), neg_pool.size)
        active_tr = [(arr, list(cols)) for arr, cols in oof_blocks if len(cols) > 0]
        active_in = [(arr, list(cols)) for arr, cols in infer_blocks if len(cols) > 0]
        hard_mask = np.zeros(neg_pool.size, dtype=bool)
        hard_set = {int(c) for c in hard_cols}
        cur = 0
        for arr, cols in active_tr:
            for c in cols:
                if cur in hard_set:
                    vals = np.asarray(arr[neg_pool, c], dtype=np.float32)
                    hard_mask |= vals >= float(np.percentile(vals[::4], 78))
                cur += 1
        n_hard = int(round(0.35 * target_neg))
        hp, ep = neg_pool[hard_mask], neg_pool[~hard_mask]
        if hp.size >= n_hard and ep.size >= (target_neg - n_hard):
            neg_idx = np.sort(
                np.concatenate(
                    [
                        rng.choice(hp, size=n_hard, replace=False),
                        rng.choice(ep, size=target_neg - n_hard, replace=False),
                    ]
                )
            )
        else:
            neg_idx = np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
        tr_idx = np.concatenate([pos_idx, neg_idx])
        y_tr = np.concatenate(
            [np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)]
        )
        sw = None
        pos_mass = float(pos_idx.size)
        if pos_w_fp is not None:
            pw = np.asarray(pos_w_fp[pos_idx], dtype=np.float32)
            pos_mass = float(pw.sum())
            sw = np.concatenate([pw, np.ones(neg_idx.size, dtype=np.float32)])
        X_tr = np.hstack(
            [np.asarray(arr[tr_idx][:, cols], dtype=np.float32) for arr, cols in active_tr]
        )
        np.nan_to_num(X_tr, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        if topo:
            m1 = HistGradientBoostingClassifier(
                learning_rate=0.050,
                max_iter=150,
                max_leaf_nodes=25,
                min_samples_leaf=110,
                l2_regularization=5.0,
                early_stopping=False,
                random_state=seed,
            ).fit(X_tr, y_tr, sample_weight=sw)
            m2 = HistGradientBoostingClassifier(
                learning_rate=0.045,
                max_iter=125,
                max_leaf_nodes=17,
                max_depth=5,
                min_samples_leaf=150,
                l2_regularization=8.0,
                early_stopping=False,
                random_state=seed + 19,
            ).fit(X_tr, y_tr, sample_weight=sw)
            w1, w2, w3 = 0.42, 0.34, 0.24
        else:
            m1 = HistGradientBoostingClassifier(
                learning_rate=0.055,
                max_iter=175,
                max_leaf_nodes=37,
                min_samples_leaf=75,
                l2_regularization=3.5,
                early_stopping=False,
                random_state=seed,
            ).fit(X_tr, y_tr, sample_weight=sw)
            m2 = HistGradientBoostingClassifier(
                learning_rate=0.050,
                max_iter=145,
                max_leaf_nodes=23,
                max_depth=6,
                min_samples_leaf=115,
                l2_regularization=6.8,
                early_stopping=False,
                random_state=seed + 19,
            ).fit(X_tr, y_tr, sample_weight=sw)
            w1, w2, w3 = 0.50, 0.32, 0.18
        sc = StandardScaler()
        X_sc = np.clip(sc.fit_transform(X_tr), -6.0, 6.0)
        m3 = LogisticRegression(C=0.20, max_iter=300, random_state=seed + 37).fit(
            X_sc, y_tr, sample_weight=sw
        )
        del X_tr, X_sc
        n_fp = int(fp.sum())
        pred_fp = np.empty(n_fp, dtype=np.float32)
        for st in range(0, n_fp, 600_000):
            en = min(st + 600_000, n_fp)
            Xc = np.hstack(
                [np.asarray(arr[st:en][:, cols], dtype=np.float32) for arr, cols in active_in]
            )
            np.nan_to_num(Xc, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
            pred_fp[st:en] = (
                w1 * m1.predict_proba(Xc)[:, 1]
                + w2 * m2.predict_proba(Xc)[:, 1]
                + w3 * m3.predict_proba(np.clip(sc.transform(Xc), -6.0, 6.0))[:, 1]
            ).astype(np.float32)
            del Xc
        raw_s = np.zeros(shape, dtype=np.float32)
        raw_s[fp] = pred_fp
        cal_s = CPAD.calibrate_reference_odds_surface(
            raw_s,
            fp,
            pi_vis_train=float(pos_idx.size) / float(pos_idx.size + neg_pool.size),
            pi_sample_weighted=float(pos_mass) / float(pos_mass + neg_idx.size),
            c0_multiplier=12.0,
        )
        del raw_s, pred_fp
        gc.collect()
        return open_or_write_surface_mmap(out_path, shape, cal_s)

    s2f_in_blocks = full_blocks + [(ac_infer_f, list(range(10))), (ac_infer_s, list(range(10)))]
    s2s_in_blocks = sub_blocks + [(ac_infer_s, list(range(10)))]
    s2t_in_blocks = [
        (ac_infer_f, list(range(10))),
        (ac_infer_s, list(range(10))),
        (tables["X_cwgr"], topo_cwgr_cols),
    ]

    log("[S18-CWGR] Fitting full-map Stage-2 unweighted Tri-Specialists (E1)")
    full_s2_f_unw = _fit_s2_full_map(
        s2f_oof_blocks, s2f_in_blocks, full_hard, CWGR_SEED_BASE + 1200, cwgr_dir / "full_s2_f_unw.f32.mmap"
    )
    full_s2_s_unw = _fit_s2_full_map(
        s2s_oof_blocks, s2s_in_blocks, sub_hard, CWGR_SEED_BASE + 1300, cwgr_dir / "full_s2_s_unw.f32.mmap"
    )
    full_s2_t_unw = _fit_s2_full_map(
        s2t_oof_blocks,
        s2t_in_blocks,
        topo_hard,
        CWGR_SEED_BASE + 1400,
        cwgr_dir / "full_s2_t_unw.f32.mmap",
        topo=True,
    )
    full_surf_e1 = CWGR.pool_tri_specialists_logit(
        np.asarray(full_s2_f_unw, dtype=np.float32),
        np.asarray(full_s2_s_unw, dtype=np.float32),
        np.asarray(full_s2_t_unw, dtype=np.float32),
        np.asarray(full_s1_f, dtype=np.float32),
        fp,
        w_full=0.46,
        w_sub=0.20,
        w_topo=0.20,
        w_s1=0.14,
        crest_fp=crest_fp,
        crest_gain=0.16,
    )

    log("[S18-CWGR] Fitting full-map Stage-2 SAR-weighted Tri-Specialists (E2 & E3)")
    e_hat_full, w_pos_full, full_sar_diag = CWGR.estimate_sar_propensity(
        vis_flat, fp_flat, fp_flat, (cat & fp).ravel()
    )
    sar_propensity_log.append({"fold": "full_4quad", **full_sar_diag})
    pos_w_full_fp = w_pos_full[fp_flat]
    full_s2_f_sar = _fit_s2_full_map(
        s2f_oof_blocks,
        s2f_in_blocks,
        full_hard,
        CWGR_SEED_BASE + 1500,
        cwgr_dir / "full_s2_f_sar.f32.mmap",
        pos_w_fp=pos_w_full_fp,
    )
    full_s2_s_sar = _fit_s2_full_map(
        s2s_oof_blocks,
        s2s_in_blocks,
        sub_hard,
        CWGR_SEED_BASE + 1600,
        cwgr_dir / "full_s2_s_sar.f32.mmap",
        pos_w_fp=pos_w_full_fp,
    )
    full_s2_t_sar = _fit_s2_full_map(
        s2t_oof_blocks,
        s2t_in_blocks,
        topo_hard,
        CWGR_SEED_BASE + 1700,
        cwgr_dir / "full_s2_t_sar.f32.mmap",
        pos_w_fp=pos_w_full_fp,
        topo=True,
    )
    full_surf_e2 = CWGR.pool_tri_specialists_logit(
        np.asarray(full_s2_f_sar, dtype=np.float32),
        np.asarray(full_s2_s_sar, dtype=np.float32),
        np.asarray(full_s2_t_sar, dtype=np.float32),
        np.asarray(full_s1_f, dtype=np.float32),
        fp,
        w_full=0.45,
        w_sub=0.22,
        w_topo=0.20,
        w_s1=0.13,
        crest_fp=crest_fp,
        crest_gain=0.18,
    )
    full_sub_dom = CWGR.pool_tri_specialists_logit(
        np.asarray(full_s2_f_sar, dtype=np.float32),
        np.asarray(full_s2_s_sar, dtype=np.float32),
        np.asarray(full_s2_t_sar, dtype=np.float32),
        np.asarray(full_s1_s, dtype=np.float32),
        fp,
        w_full=0.28,
        w_sub=0.34,
        w_topo=0.28,
        w_s1=0.10,
        crest_fp=sub_crest_fp,
        crest_gain=0.24,
    )
    full_surf_e3 = CWGR.compute_unmapped_fault_posterior(
        full_sub_dom, e_hat_full.reshape(shape), fp, lambda_e=0.65
    )

    dump(OUT_DIR / "rank-logit-ac-audit.json", {"folds": rank_ac_audit})
    dump(OUT_DIR / "sar-propensity-audit.json", {"splits": sar_propensity_log})

    return {
        "e1_dots_folds": e1_dots_folds,
        "e2_dots_folds": e2_dots_folds,
        "e3_dots_folds": e3_dots_folds,
        "e1_quota_folds": e1_quota_folds,
        "e2_quota_folds": e2_quota_folds,
        "e3_quota_folds": e3_quota_folds,
        "area_quotas": area_quotas,
        "full_surf_e1": full_surf_e1,
        "full_surf_e2": full_surf_e2,
        "full_surf_e3": full_surf_e3,
        "ac_oof_f": ac_oof_f,
        "ac_oof_s": ac_oof_s,
        "calibration_log": calibration_log,
        "rank_ac_audit": rank_ac_audit,
        "sar_propensity_log": sar_propensity_log,
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
    log("Running Rule 4 single-feature AUROC leak canaries across all 155 static + 20 OOF AC features")
    y_fp = cat[fp]
    quad_masks_fp = [f["region"][fp] for f in folds]
    features_report: dict[str, dict[str, object]] = {}

    for idx, name in enumerate(CWGR.CWGR_FEATURE_NAMES):
        grid = np.zeros(fp.shape, dtype=np.float32)
        grid[fp] = np.asarray(tables["X_cwgr"][:, idx], dtype=np.float32)
        res = ced.auc_canary(grid, cat, fp)
        col_v = grid[fp]
        q_aucs = [round(fast_symmetric_auc(col_v[qm], y_fp[qm])[1], 6) for qm in quad_masks_fp]
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

    for prefix, ac_mm in (("ac_rank_full", ac_oof_f), ("ac_rank_sub", ac_oof_s)):
        for j, base_name in enumerate(SC.S12_AUTOCONTEXT_FEATURE_NAMES):
            fname = f"{prefix}__{base_name}"
            vals = np.asarray(ac_mm[:, j], dtype=np.float32)
            auc_p, sym_p = fast_symmetric_auc(vals, y_fp)
            q_aucs = [round(fast_symmetric_auc(vals[qm], y_fp[qm])[1], 6) for qm in quad_masks_fp]
            worst = max(sym_p, max(q_aucs))
            features_report[fname] = {
                "evidence_class": "HOLDOUT-DTI",
                "statistic": "OOF auto-context feature-alone AUROC (not DTI)",
                "auc": round(auc_p, 6),
                "symmetric_auc": round(sym_p, 6),
                "quadrant_symmetric_aucs": q_aucs,
                "max_quadrant_symmetric_auc": max(q_aucs),
                "withheld_positive_pixels": int(y_fp.sum()),
                "negative_proxy_pixels": int((~y_fp).sum()),
                "threshold": 0.90,
                "status": "LEAKAGE_SUSPECTED" if worst > 0.90 else "PASS",
            }

    max_pooled = max(float(v["symmetric_auc"]) for v in features_report.values())
    max_quad = max(float(v["max_quadrant_symmetric_auc"]) for v in features_report.values())
    all_pass = all(v["status"] == "PASS" for v in features_report.values())
    return {
        "evidence_class": "HOLDOUT-DTI",
        "evaluator_version": evaluator.VERSION,
        "features_tested": len(features_report),
        "threshold": 0.90,
        "max_symmetric_auc": round(max_pooled, 6),
        "max_quadrant_symmetric_auc": round(max_quad, 6),
        "status": "PASS" if all_pass else "LEAKAGE_SUSPECTED",
        "features": features_report,
    }


def evaluate_blind_sgmc_control(
    dots_by_name: dict[str, np.ndarray], cat: np.ndarray, fp: np.ndarray
) -> dict[str, object]:
    with rasterio.open(SGMC_TIF) as src:
        sgmc_raw = (src.read(1) > 0) & fp
    d_cat = ndi.distance_transform_edt(~(cat & fp))
    sgmc_blind = sgmc_raw & (d_cat > 5.0)
    active = fp & (~cat)
    scores: dict[str, dict[str, object]] = {}
    for name, dots in dots_by_name.items():
        pred = np.where(active, np.asarray(dots, dtype=np.float32), 0.0)
        res = v57_metric.dti_exact(pred, sgmc_blind, valid=active)
        scores[name] = {
            "evidence_class": "BLIND-SGMC-CONTROL-DTI",
            "dti": round(float(res["dti"]), 6),
            "tp": round(float(res["tp"]), 3),
            "fp": round(float(res["fp"]), 3),
            "fn": round(float(res["fn"]), 3),
            "blind_sgmc_positive_pixels": int(sgmc_blind.sum()),
            "emitted_dots": int((pred > 0).sum()),
        }
    return {
        "evidence_class": "BLIND-SGMC-CONTROL-DTI",
        "caveat": "Off-catalogue USGS SGMC bedrock/concealed faults (>500 m from existing_faults.tif); independent geological sanity check, NOT HOLDOUT-DTI or ORGANIZER-CONFIRMED.",
        "blind_sgmc_positive_pixels": int(sgmc_blind.sum()),
        "scores": scores,
    }


def compute_exhaustive_diagnostic_overlaps(
    dot_bool: np.ndarray,
    pre_reg: dict,
    fp: np.ndarray,
    inventory: dict,
) -> dict[str, object]:
    """Measure exact 3-px dot overlap across ALL 108 inventory entries, reusing pre_reg Spearman rho."""
    rho_by_name = {
        Path(r["file"]).name: float(r.get("surface", {}).get("rank_correlation") or 0.0)
        for r in pre_reg.get("comparisons", [])
    }
    rows_by_cat: dict[str, list[dict[str, object]]] = {}
    all_rows: list[dict[str, object]] = []
    for entry in inventory["files"]:
        p = ROOT / entry["path"]
        with rasterio.open(p) as ds:
            ref_arr = ds.read(1)
        dc = NOV.dot_check(dot_bool, ref_arr, fp)
        cat_name = entry.get("category", "uncategorized")
        nm = Path(entry["path"]).name
        rec = {
            "path": entry["path"],
            "name": nm,
            "category": cat_name,
            "is_calibration_probe": nm.startswith("calib_"),
            "registry_dots": int(dc["registry_dots"]),
            "overlap_within_3px": round(float(dc["overlap_within_3px"]), 6),
            "preplacement_spearman_rho": round(rho_by_name.get(nm, 0.0), 6),
        }
        all_rows.append(rec)
        rows_by_cat.setdefault(cat_name, []).append(rec)

    cat_summary: dict[str, object] = {}
    for cat_name, items in rows_by_cat.items():
        worst = max(items, key=lambda r: r["overlap_within_3px"])
        non_calib = [r for r in items if not r["is_calibration_probe"]]
        worst_nc = max(non_calib, key=lambda r: r["overlap_within_3px"]) if non_calib else worst
        cat_summary[cat_name] = {
            "count": len(items),
            "pass_le_70pct": sum(1 for r in items if r["overlap_within_3px"] <= 0.70),
            "max_overlap_within_3px": worst["overlap_within_3px"],
            "max_overlap_file": worst["name"],
            "non_calib_count": len(non_calib),
            "non_calib_pass_le_70pct": sum(1 for r in non_calib if r["overlap_within_3px"] <= 0.70),
            "non_calib_max_overlap_within_3px": worst_nc["overlap_within_3px"],
            "non_calib_max_overlap_file": worst_nc["name"],
            "max_abs_spearman_rho": round(
                max(abs(r["preplacement_spearman_rho"]) for r in items), 6
            ),
        }
    return {"category_summary": cat_summary, "all_108_entries": all_rows}


def run() -> dict:
    started = time.monotonic()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    inputs = verify_all_inputs()
    inventory = json.loads(INVENTORY_PATH.read_text())

    with rasterio.open(SAMPLE) as s:
        fp = np.isfinite(s.read(1))
        shape = s.shape
        sample_meta = (s.count, s.shape, s.crs, s.transform)
    with rasterio.open(CATALOGUE) as s:
        if (s.count, s.shape, s.crs, s.transform) != sample_meta:
            raise ValueError("catalogue/sample grid mismatch")
        cat = (s.read(1) > 0) & fp

    card: dict[str, object] = {
        "schema_version": "gems91.s18-cwgr.v1",
        "branch": "arena/892fab6a-gemsdoe91",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": {
            "path": "docs/HYPOTHESES_S18_CWGR.md",
            "sha256": sha256_file(PREREG),
        },
        "lane": {
            "name": "S18-CWGR",
            "assigned": False,
            "status": "PROVISIONAL_RESEARCH_ONLY",
            "reason": "Single local lane S18-CWGR enforced; prompt omitted external multi-agent lane coordinator token ([PASTE ONE METHOD]).",
        },
        "hypothesis": (
            "H18-1 (S18-CWGR): Freeman-Adelson multi-scale steerable G1/G2 odd-step/even-trough quadrature "
            "skeletonization, spatially varying Basin-and-Range <-> Walker Lane Byerlee-Morris & Sibson "
            "fault-valve continuum mechanics, quadrant-invariant rank-logit auto-context (IR-91-S17-01), "
            "dedicated Stage-2 Structural-Topology Specialist (IR-91-S17-02), and SAR mapper-completeness "
            "propensity modeling improve label-blind fault discovery over S17-CPAD E1 and INCUMBENT-PTAC-LB."
        ),
        "mechanism": (
            "18 novel CWGR features (15 strictly Band-12/Band-19-invariant steerable quadrature, Athy gravity "
            "silicification, and kinematic Byerlee-Sibson fault-valve features + 3 piedmont micro-scarp / "
            "pluvial-shoreline deconfounder / mapper-visibility features); label-free mid-rank probit-logistic "
            "quadrant standardization prior to spac_coda auto-context; Tri-Specialist Stage-2 log-opinion pool "
            "(Full 174-col + Pure-Subsurface 129-col + Topology 28-col); centerline-anchored 8-orientation "
            "300-m submodular dot emitter."
        ),
        "named_non_fault_mimic_process": (
            "Unfaulted Tertiary volcanic flow lobes, caldera ring dikes, and pluton hornfels margins (suppressed "
            "by azimuthal quadrature elongation anisotropy and cross-physics strike lock), plus Lake Lahontan "
            "wave-cut pluvial shorelines and incised braided fan channels (suppressed by contour-orthogonality "
            "and Pure-Subsurface specialist pooling)."
        ),
        "experiments_run": 3,
        "budget": {
            "max_experiments": 3,
            "planned_candidates": 3,
            "prior_benchmark_replays": 2,
            "max_seconds": 7200,
        },
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": evaluator.VERSION,
            "value": None,
            "ci95": None,
            "withheld_positives": None,
            "status": "RUNNING",
        },
        "comparable_prior_holdout_best": None,
        "organizer_confirmed": None,
        "selector_approval": False,
        "selector_receipt": None,
        "slots_used": 0,
        "registry_comparison": {
            "scope": inventory["scope"],
            "complete_universal_registry": False,
            "inventory": "registry/s18_comparison_inventory.json",
            "missing_files_on_disk": inventory.get("missing_files_on_disk", 0),
            "missing_scope": inventory["missing_scope"],
        },
        "inputs": inputs,
        "raster_sha256": None,
        "validator_output": {"status": "NOT_RUN"},
        "submission_name": None,
        "note": None,
        "verdict": "negative",
        "submission_ready": False,
    }
    dump(CARD_PATH, card)

    # 1. Build/load static feature memmaps + programmatic Band-12 / Band-19 invariance check
    tables = build_feature_tables(fp)
    spec = assemble_cwgr_blocks(tables)

    log("Verifying programmatic Band-12 / Band-19 bitwise invariance on CWGR subsurface columns 0..14")
    rng_chk = np.random.default_rng(18)
    fp_chk = np.ones((56, 60), dtype=bool)
    b_chk_a = rng_chk.normal(0.0, 2.0, size=(19, 56, 60)).astype(np.float32)
    b_chk_a[14] = np.abs(b_chk_a[14]) * 300.0
    b_chk_b = b_chk_a.copy()
    b_chk_b[11] = rng_chk.uniform(-4000.0, 4000.0, size=(56, 60)).astype(np.float32)
    b_chk_b[18] = rng_chk.uniform(0.0, 80.0, size=(56, 60)).astype(np.float32)
    fa = CWGR.extract_cwgr_features(b_chk_a, fp_chk)
    fb = CWGR.extract_cwgr_features(b_chk_b, fp_chk)
    max_dem_leak = float(np.max(np.abs(fa[:15] - fb[:15])))
    if max_dem_leak != 0.0:
        raise AssertionError(f"CWGR subsurface DEM leak detected: {max_dem_leak}")
    del b_chk_a, b_chk_b, fa, fb

    feat_receipt = {
        "cwgr_code_sha256": sha256_file(ROOT / "src/gems91/cwgr18.py"),
        "cwgr_meta": tables["cwgr_meta"],
        "stage1_full_feature_count": len(spec["full_names"]),
        "stage1_pure_subsurface_feature_count": len(spec["sub_names"]),
        "stage2_full_feature_count": len(spec["full_names"]) + 20,
        "stage2_pure_subsurface_feature_count": len(spec["sub_names"]) + 10,
        "stage2_topology_specialist_feature_count": 20 + len(spec["topo_cwgr_cols"]),
        "strict_topo_excluded_count": len(spec["full_names"]) - len(spec["sub_names"]),
        "verified_cwgr_subsurface_b12_b19_max_diff": max_dem_leak,
        "cwgr_novel_features": list(CWGR.CWGR_FEATURE_NAMES),
        "topology_specialist_static_features": spec["topo_static_names"],
    }
    dump(OUT_DIR / "features.json", feat_receipt)
    card["features"] = {
        "file": "s18/features.json",
        "stage1_full_count": len(spec["full_names"]),
        "stage1_pure_subsurface_count": len(spec["sub_names"]),
        "stage2_topology_specialist_count": 20 + len(spec["topo_cwgr_cols"]),
        "cwgr_novel_count": len(CWGR.CWGR_FEATURE_NAMES),
    }

    # 2. Construct canonical label-blind spatial folds (buffer_px=80)
    log("Constructing canonical spatial.folds(cat, fp, buffer_px=80)")
    folds = list(spatial.folds(cat, fp, buffer_px=BUFFER_PX))
    split_sha = hashlib.sha256(
        b"".join(
            np.packbits(f[k].ravel()).tobytes()
            for f in folds
            for k in ("region", "truth", "train", "visible")
        )
    ).hexdigest()

    # 3. Prior label-blind baselines
    log("Computing label-blind CED91, S16-PGRD, and Gravity-Theta control baselines")
    with rasterio.open(STACK) as ds:
        b1_m = ds.read(1)
        b2_rtp = ds.read(2)
        b13_g = ds.read(13)
    ced_surf = np.asarray(ced.features(b1_m, b13_g, fp)["surface"], dtype=np.float32)
    del b1_m
    pgrd_surf = np.asarray(PGRD.features(b2_rtp, b13_g, fp)["surface"], dtype=np.float32)
    del b2_rtp, b13_g
    gc.collect()
    grav_ctrl_surf = np.zeros(shape, dtype=np.float32)
    grav_ctrl_surf[fp] = np.asarray(tables["X_cpad"][:, 0], dtype=np.float32)

    ced_dots_folds = [ced.place(ced_surf, fp & (~f["visible"]), DOT_BUDGET) for f in folds]
    pgrd_dots_folds = [ced.place(pgrd_surf, fp & (~f["visible"]), DOT_BUDGET) for f in folds]
    grav_dots_folds = [
        CPAD.emit_global_dots_nms(
            grav_ctrl_surf,
            f["visible"],
            fp,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        )
        > 0
        for f in folds
    ]
    del ced_surf, grav_ctrl_surf
    gc.collect()

    inc_dots_folds, inc_meta = run_incumbent_ptac_lb(tables, folds, fp)
    cpad_e1_dots_folds = run_cpad_e1_baseline(tables, folds, fp)

    # 4. Run 3 preregistered S18-CWGR candidate arms (`cwgr_e1`, `cwgr_e2`, `cwgr_e3`)
    cwgr_out = run_cwgr_hierarchy(tables, spec, folds, cat, fp)

    # 5. Rule 4 Single-Feature Leak Canaries (`AUC <= 0.90`)
    canary_path = OUT_DIR / "canaries.json"
    if canary_path.is_file():
        canary_report = json.loads(canary_path.read_text())
        if canary_report.get("features_tested") != len(spec["full_names"]) + 20:
            canary_report = run_canaries(
                tables, spec, cwgr_out["ac_oof_f"], cwgr_out["ac_oof_s"], folds, cat, fp
            )
            dump(canary_path, canary_report)
    else:
        canary_report = run_canaries(
            tables, spec, cwgr_out["ac_oof_f"], cwgr_out["ac_oof_s"], folds, cat, fp
        )
        dump(canary_path, canary_report)
    card["canaries"] = {
        "status": canary_report["status"],
        "features_tested": canary_report["features_tested"],
        "max_symmetric_auc": canary_report["max_symmetric_auc"],
        "max_quadrant_symmetric_auc": canary_report["max_quadrant_symmetric_auc"],
        "file": "s18/canaries.json",
    }
    if canary_report["status"] != "PASS":
        raise RuntimeError(f"Rule 4 canary failure: {card['canaries']}")

    # 6. Score all 8 primary arms + 3 IR-91-S18-02 area-quota diagnostic arms on `evaluate_holdout.py`
    log("Scoring all 8 primary arms + 3 area-quota controls on unchanged vendor/gems57/evaluate_holdout.py")
    arm_fold_dots = {
        "gravity_control": grav_dots_folds,
        "ced91": ced_dots_folds,
        "s16_pgrd": pgrd_dots_folds,
        "incumbent_ptac_lb": inc_dots_folds,
        "cpad_e1": cpad_e1_dots_folds,
        "cwgr_e1": cwgr_out["e1_dots_folds"],
        "cwgr_e2": cwgr_out["e2_dots_folds"],
        "cwgr_e3": cwgr_out["e3_dots_folds"],
    }
    quota_fold_dots = {
        "cwgr_e1_quota37654": cwgr_out["e1_quota_folds"],
        "cwgr_e2_quota37654": cwgr_out["e2_quota_folds"],
        "cwgr_e3_quota37654": cwgr_out["e3_quota_folds"],
    }

    fold_records: list[dict[str, object]] = []
    terms_by_arm: dict[str, np.ndarray] = {}
    quota_terms_by_arm: dict[str, np.ndarray] = {}
    for q, fold in enumerate(folds):
        ys, xs = np.nonzero(fold["region"])
        sl = (slice(int(ys.min()), int(ys.max()) + 1), slice(int(xs.min()), int(xs.max()) + 1))
        origin = (sl[0].start, sl[1].start)
        cropped_fold = {k: fold[k][sl] for k in ("region", "truth", "visible")}
        valid_crop = fp[sl]
        arm_scores_q: dict[str, object] = {}
        for arm_name, dots_list in arm_fold_dots.items():
            g_dots = np.asarray(dots_list[q], dtype=bool)
            score_q, terms_q = evaluator.evaluate(
                g_dots[sl].astype(np.float32),
                cropped_fold,
                valid_crop,
                origin=origin,
                global_shape=shape,
            )
            arm_scores_q[arm_name] = {**score_q, "global_emitted": int(g_dots.sum())}
            terms_by_arm[arm_name] = terms_by_arm.get(arm_name, 0.0) + terms_q

        quota_scores_q: dict[str, object] = {}
        for q_name, dots_list in quota_fold_dots.items():
            g_dots = np.asarray(dots_list[q], dtype=bool)
            score_q, terms_q = evaluator.evaluate(
                g_dots[sl].astype(np.float32),
                cropped_fold,
                valid_crop,
                origin=origin,
                global_shape=shape,
            )
            quota_scores_q[q_name] = {**score_q, "quota_emitted": int(g_dots.sum())}
            quota_terms_by_arm[q_name] = quota_terms_by_arm.get(q_name, 0.0) + terms_q

        fold_records.append(
            {
                "fold": int(fold.get("fold", q)),
                "receipt": fold["receipt"],
                "global_budget": DOT_BUDGET,
                "area_quota_budget": cwgr_out["area_quotas"][q],
                "arms": arm_scores_q,
                "quota_diagnostic_arms": quota_scores_q,
            }
        )

    cwgr_arm_dtis = {
        a: float(evaluator.from_terms(terms_by_arm[a].sum(axis=0)))
        for a in ("cwgr_e1", "cwgr_e2", "cwgr_e3")
    }
    best_arm = max(cwgr_arm_dtis, key=cwgr_arm_dtis.get)
    log(f"S18-CWGR arm HOLDOUT-DTIs: {cwgr_arm_dtis} -> winning arm: {best_arm}")

    summary_all = evaluator.pooled_summary(
        terms_by_arm, draws=1000, seed=520810, candidate=best_arm
    )
    prior_terms = {
        k: terms_by_arm[k]
        for k in (
            best_arm,
            "cpad_e1",
            "incumbent_ptac_lb",
            "ced91",
            "s16_pgrd",
            "gravity_control",
        )
    }
    summary_vs_prior = evaluator.pooled_summary(
        prior_terms, draws=1000, seed=520810, candidate=best_arm
    )
    quota_summary = evaluator.pooled_summary(
        quota_terms_by_arm, draws=1000, seed=520810, candidate=f"{best_arm}_quota37654"
    )

    best_prior_key = str(summary_vs_prior["best_comparable_control"])
    best_prior_score = summary_vs_prior["scores"][best_prior_key]
    paired_best = summary_vs_prior["paired_differences"][best_prior_key]
    best_score = summary_all["scores"][best_arm]

    prior_candidates = {
        "S17-CPAD-E1": summary_all["scores"]["cpad_e1"]["dti"],
        "INCUMBENT-PTAC-LB": summary_all["scores"]["incumbent_ptac_lb"]["dti"],
        "CED91": summary_all["scores"]["ced91"]["dti"],
        "S16-PGRD": summary_all["scores"]["s16_pgrd"]["dti"],
        "GRAVITY-THETA-CONTROL": summary_all["scores"]["gravity_control"]["dti"],
    }

    holdout_payload = {
        "split_sha256": split_sha,
        "buffer_px": BUFFER_PX,
        "global_dot_budget": DOT_BUDGET,
        "area_quotas_ir91_s18_02": cwgr_out["area_quotas"],
        "collar_px": COLLAR_PX,
        "min_spacing_px": MIN_SPACING_PX,
        "winning_cwgr_arm": best_arm,
        "summary_all_arms": summary_all,
        "summary_vs_prior_baselines": summary_vs_prior,
        "quota_diagnostic_summary_ir91_s18_02": quota_summary,
        "comparable_prior_benchmarks": prior_candidates,
        "incumbent_metadata": inc_meta,
        "rank_logit_ac_audit": cwgr_out["rank_ac_audit"],
        "sar_propensity_audit": cwgr_out["sar_propensity_log"],
        "calibration_log": cwgr_out["calibration_log"],
        "folds": fold_records,
    }
    dump(OUT_DIR / "holdout.json", holdout_payload)

    card["holdout_dti"] = {
        "label": "HOLDOUT-DTI",
        "evaluator_version": evaluator.VERSION,
        "split_sha256": split_sha,
        "winning_arm": best_arm,
        "value": best_score["dti"],
        "ci95": best_score["ci95"],
        "withheld_positives": best_score["withheld_positive_pixels"],
        "all_arms": {
            k: {
                "dti": summary_all["scores"][k]["dti"],
                "ci95": summary_all["scores"][k]["ci95"],
                "withheld_positives": summary_all["scores"][k]["withheld_positive_pixels"],
            }
            for k in summary_all["scores"]
        },
        "quota_diagnostic_ir91_s18_02": {
            k: {
                "dti": quota_summary["scores"][k]["dti"],
                "ci95": quota_summary["scores"][k]["ci95"],
                "pooled_emitted_dots": DOT_BUDGET,
            }
            for k in quota_summary["scores"]
        },
        "paired_best": paired_best,
        "paired_vs_cpad_e1": summary_vs_prior["paired_differences"]["cpad_e1"],
        "paired_vs_incumbent_ptac_lb": summary_vs_prior["paired_differences"]["incumbent_ptac_lb"],
        "paired_vs_ced91": summary_vs_prior["paired_differences"]["ced91"],
        "paired_vs_s16_pgrd": summary_vs_prior["paired_differences"]["s16_pgrd"],
        "paired_vs_gravity_control": summary_vs_prior["paired_differences"]["gravity_control"],
        "status": "COMPLETED",
        "file": "s18/holdout.json",
    }
    card["comparable_prior_holdout_best"] = {
        "label": "HOLDOUT-DTI",
        "source": best_prior_key,
        "evaluator_version": evaluator.VERSION,
        "split_sha256": split_sha,
        "withheld_positives": best_prior_score["withheld_positive_pixels"],
        "value": float(best_prior_score["dti"]),
        "ci95": best_prior_score["ci95"],
        "beats_comparable_prior_best": bool(best_score["dti"] > float(best_prior_score["dti"])),
        "delta": float(paired_best["delta"]),
        "paired_ci95": paired_best["ci95"],
    }

    # 7. Emit full-map dots for E1, E2, E3 + evaluate BLIND-SGMC-CONTROL-DTI
    full_dots_map = {
        "cwgr_e1": CWGR.emit_cwgr_submodular_skeleton(
            cwgr_out["full_surf_e1"],
            cat,
            fp,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        ),
        "cwgr_e2": CWGR.emit_cwgr_submodular_skeleton(
            cwgr_out["full_surf_e2"],
            cat,
            fp,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        ),
        "cwgr_e3": CWGR.emit_cwgr_submodular_skeleton(
            cwgr_out["full_surf_e3"],
            cat,
            fp,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        ),
    }
    surf_by_arm = {
        "cwgr_e1": cwgr_out["full_surf_e1"],
        "cwgr_e2": cwgr_out["full_surf_e2"],
        "cwgr_e3": cwgr_out["full_surf_e3"],
    }
    best_full_surface = surf_by_arm[best_arm]
    best_full_dots = full_dots_map[best_arm]

    full_dots_pgrd = ced.place(pgrd_surf, fp & (~cat), DOT_BUDGET).astype(np.float32)
    with rasterio.open(ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif") as r32_src:
        r32_dots = (r32_src.read(1) > 0).astype(np.float32)
    with rasterio.open(
        ROOT / "docs/downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif"
    ) as s17_src:
        s17_dots = (s17_src.read(1) > 0).astype(np.float32)
    with rasterio.open(
        ROOT / "docs/downloads/gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif"
    ) as s14_src:
        s14_dots = (s14_src.read(1) > 0).astype(np.float32)

    sgmc_report = evaluate_blind_sgmc_control(
        {
            "gemsdoe32_r0": r32_dots,
            "s14_ptac_e2_legacy_artifact": s14_dots,
            "s16_pgrd": full_dots_pgrd,
            "cpad_e1": s17_dots,
            "cwgr_e1": full_dots_map["cwgr_e1"],
            "cwgr_e2": full_dots_map["cwgr_e2"],
            "cwgr_e3": full_dots_map["cwgr_e3"],
        },
        cat,
        fp,
    )
    dump(OUT_DIR / "blind-sgmc-control.json", sgmc_report)
    card["blind_sgmc_control"] = {
        "evidence_class": "BLIND-SGMC-CONTROL-DTI",
        "file": "s18/blind-sgmc-control.json",
        "blind_sgmc_positive_pixels": sgmc_report["blind_sgmc_positive_pixels"],
        "winning_arm_dti": sgmc_report["scores"][best_arm]["dti"],
        "scores": {k: v["dti"] for k, v in sgmc_report["scores"].items()},
    }
    del r32_dots, s14_dots, s17_dots, full_dots_pgrd
    gc.collect()

    # 8. Rule 1 Pre-Placement Surface Novelty Check across all 108 verified rasters
    log("Running Rule 1 pre-placement full-footprint Spearman rank-correlation check (108 rasters)")
    pre_reg = run_ced.registry_phase(best_full_surface, fp, inventory, sample_meta)
    dump(OUT_DIR / "registry-surface.json", pre_reg)
    card["registry_comparison"]["preplacement"] = phase_summary(pre_reg)
    max_pre_rho = max(
        (abs(r.get("surface", {}).get("rank_correlation") or 0.0) for r in pre_reg["comparisons"]),
        default=None,
    )
    card["registry_comparison"]["max_measured_preplacement_rank_correlation"] = max_pre_rho
    card["registry_comparison"]["max_measured_surface_rank_correlation"] = max_pre_rho
    if pre_reg["status"] == "DUPLICATE":
        card.update(
            verdict="negative",
            verdict_reason="Pre-placement surface rank correlation exceeded 0.90; stopped.",
            completed_utc=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=round(time.monotonic() - started, 3),
        )
        card["automated_gates"] = readiness.gates(card)
        card["ok_to_download"] = False
        card["ok_to_submit"] = readiness.submission_ready(card)
        dump(CARD_PATH, card)
        return card

    # 9. Write & triple-validate `-zeros.tif` + `-zeros.zip` via untouched `submission_writer.py`
    dot_bool = best_full_dots > 0
    pixel_digest = hashlib.sha256(dot_bool.astype(np.uint8).tobytes()).hexdigest()
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arm_slug = best_arm.replace("_", "-")
    sub_name = f"gems91-s18-{arm_slug}-{tag}-{pixel_digest[:12]}"
    note = (
        f"S18-CWGR ({best_arm}): Freeman-Adelson quadrature & Byerlee-Sibson tri-spec; "
        f"37654 dots; research artifact, slot unapproved."
    )
    assert len(note) <= 140, f"note too long: {len(note)}"
    tif_path = ROOT / "docs/downloads" / f"{sub_name}-zeros.tif"

    log(f"Writing and triple-validating {tif_path.name} via shared submission_writer")
    receipt = write_submission(
        tif_path,
        dot_bool.astype(np.float32),
        SAMPLE,
        fp,
        note=note,
        name=sub_name,
        catalogue=cat,
        metadata={
            "lane": "S18-CWGR",
            "winning_arm": best_arm,
            "hypothesis_prereg_sha256": card["preregistration"]["sha256"],
            "holdout_dti": best_score["dti"],
            "holdout_evaluator": evaluator.VERSION,
            "no_prior_submission_copied": True,
        },
    )
    dump(OUT_DIR / "writer-receipt.json", receipt)

    pts = np.argwhere(dot_bool)
    min_interdot_px = float(cKDTree(pts).query(pts, k=2)[0][:, 1].min())
    min_cat_px = float(ndi.distance_transform_edt(~cat)[dot_bool].min())

    rg_zeros = RG91.validate_release(
        tif_path,
        template=SAMPLE,
        catalogue=cat,
        ledger=None,
        encoding="zeros",
        floor_px=3.0,
        expect_dots=DOT_BUDGET,
        own_id=sub_name,
    )
    vr_zeros = VR.validate_raster(
        tif_path,
        SAMPLE,
        catalogue=CATALOGUE,
        ledger_csv=ROOT / "ledger/submissions.csv",
        parent=ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif",
        allow_zeros_outside=True,
    )
    # Independent second TIFF decoder check via tifffile
    tf_arr = tifffile.imread(tif_path)

    with rasterio.open(tif_path) as s:
        arr = s.read(1)
        checks = {
            "single_band": s.count == 1,
            "float32": s.dtypes == ("float32",) and tf_arr.dtype == np.float32,
            "crs_match": s.crs == sample_meta[2],
            "shape_match": s.shape == shape and tf_arr.shape == shape,
            "transform_match": s.transform == sample_meta[3],
            "all_cells_finite": bool(np.isfinite(arr).all() and np.isfinite(tf_arr).all()),
            "range_0_1": bool((arr >= 0.0).all() and (arr <= 1.0).all()),
            "independent_tifffile_bitwise_match": bool(np.array_equal(arr, tf_arr)),
            "zero_outside": bool((arr[~fp] == 0.0).all()),
            "zero_on_catalogue": bool((arr[cat] == 0.0).all()),
            "no_nodata_tag": s.nodata is None,
            "exact_dot_count": int((arr > 0).sum()) == DOT_BUDGET,
            "spacing_strictly_over_3px": min_interdot_px > 3.0,
            "collar_strictly_over_3px": min_cat_px > 3.0,
            "release_gates_pass": bool(rg_zeros["PASS"]),
            "validate_raster_pass": bool(vr_zeros.ok),
            "identity_new_vs_frozen_hashes": receipt["sha256"]
            not in {x["sha256"] for x in inventory["files"]},
        }
        validator = {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "no_nan_inside_footprint": bool(np.isfinite(arr[fp]).all()),
            "values_in_0_1": checks["range_0_1"],
            "crs_shape_transform_match": checks["crs_match"]
            and checks["shape_match"]
            and checks["transform_match"],
            "crs": str(s.crs),
            "shape": list(s.shape),
            "transform": list(s.transform)[:6],
            "min": float(arr.min()),
            "max": float(arr.max()),
            "nan_inside": int(np.isnan(arr[fp]).sum()),
            "nan_anywhere": int(np.isnan(arr).sum()),
            "positive_pixels": int(dot_bool.sum()),
            "min_spacing_px": round(min_interdot_px, 5),
            "min_catalogue_distance_px": round(min_cat_px, 5),
            "source": "Reopened generated TIFF with rasterio + independent tifffile + verified single-member ZIP + release_gates + validate_raster.",
        }
    del arr, tf_arr
    if validator["status"] != "PASS":
        raise RuntimeError(f"Post-write validator failed: {validator}")

    # 10. Final Rule 1 3-px dot overlap check + exhaustive 108-raster diagnostic audit
    log("Running Rule 1 final 3-px dot overlap check across 108-raster inventory")
    final_reg = run_ced.registry_phase(best_full_surface, fp, inventory, sample_meta, dots=dot_bool)
    dump(OUT_DIR / "registry-final.json", final_reg)

    exhaustive = compute_exhaustive_diagnostic_overlaps(dot_bool, pre_reg, fp, inventory)
    # Also compute E3's diagnostic overlap against GEMSDOE32 and S17-CPAD to verify E3 orthogonality
    e3_bool = full_dots_map["cwgr_e3"] > 0
    with rasterio.open(ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif") as _r32:
        e3_vs_r32 = NOV.dot_check(e3_bool, _r32.read(1), fp)
    with rasterio.open(
        ROOT / "docs/downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif"
    ) as _s17:
        e3_vs_s17 = NOV.dot_check(e3_bool, _s17.read(1), fp)
    exhaustive["e3_orthogonality_diagnostic"] = {
        "cwgr_e3_vs_gemsdoe32_r0_3px_overlap": round(float(e3_vs_r32["overlap_within_3px"]), 6),
        "cwgr_e3_vs_s17_cpad_e1_3px_overlap": round(float(e3_vs_s17["overlap_within_3px"]), 6),
    }
    dump(OUT_DIR / "milestone-novelty.json", exhaustive)

    passed_before_stop = [r for r in final_reg["comparisons"] if r.get("status") == "PASS"]
    max_passed_overlap = max(
        (float(r.get("dots", {}).get("overlap_within_3px") or 0.0) for r in passed_before_stop),
        default=0.0,
    )
    r32_ov = next(
        (
            r["overlap_within_3px"]
            for r in exhaustive["all_108_entries"]
            if "h33-2-b2" in r["name"]
        ),
        None,
    )

    card["registry_comparison"]["final"] = phase_summary(final_reg)
    card["registry_comparison"]["passed_before_stop_count"] = len(passed_before_stop)
    card["registry_comparison"]["max_passed_before_stop_3px_overlap"] = round(
        max_passed_overlap, 6
    )
    card["registry_comparison"]["category_summary"] = exhaustive["category_summary"]
    card["registry_comparison"]["e3_orthogonality_diagnostic"] = exhaustive[
        "e3_orthogonality_diagnostic"
    ]
    card["registry_comparison"]["gemsdoe32_r0_3px_overlap"] = r32_ov
    card["registry_comparison"]["max_measured_final_dot_overlap_within_3px"] = max(
        (
            float(r.get("dots", {}).get("overlap_within_3px") or 0.0)
            for r in final_reg["comparisons"]
        ),
        default=None,
    )
    card["registry_comparison"]["max_measured_final_dot_rank_correlation"] = max(
        (
            abs(float(r.get("surface", {}).get("rank_correlation") or 0.0))
            for r in final_reg["comparisons"]
        ),
        default=None,
    )

    stopped_name = (
        Path(final_reg["stopped_on"]["file"]).name if final_reg.get("stopped_on") else "none"
    )
    stopped_ov = (
        float(final_reg["stopped_on"]["dots"]["overlap_within_3px"])
        if final_reg.get("stopped_on") and "dots" in final_reg["stopped_on"]
        else 0.0
    )
    stopped_dots = (
        int(final_reg["stopped_on"]["dots"]["registry_dots"])
        if final_reg.get("stopped_on") and "dots" in final_reg["stopped_on"]
        else 0
    )

    card.update(
        submission_name=sub_name,
        note=note,
        raster_path=f"docs/downloads/{tif_path.name}",
        raster_sha256=receipt["sha256"],
        raster_pixel_sha256=pixel_digest,
        validator_output=validator,
        artifact={
            "file": f"downloads/{tif_path.name}",
            "zip": f"downloads/{receipt['zip_file']}",
            "bytes": tif_path.stat().st_size,
            "zip_bytes": tif_path.with_suffix(".zip").stat().st_size,
            "zip_sha256": receipt["zip_sha256"],
            "audit": "s18/writer-receipt.json",
        },
        byte_identity_unique=True,
        byte_identity_caveat=(
            f"Unique bytes, 108/108 pre-placement Spearman PASS (max |rho|={max_pre_rho:.4f} <= 0.90), "
            f"and {len(passed_before_stop)} preceding/orthogonal rasters PASS (GEMSDOE32 R0 = {r32_ov:.4f} <= 0.70) "
            f"do not override the literal Rule-1 duplicate stop at {stopped_name} ({stopped_dots} dots, "
            f"3-px overlap {stopped_ov:.4f} > 0.70) or the synthetic lattice bound (calib_r13lattice >= 0.8234)."
        ),
    )

    beats_prior = bool(best_score["dti"] > float(best_prior_score["dti"]))
    ci_excludes_zero = bool(paired_best["ci95"][0] > 0.0)
    verdict_reason = (
        f"HOLDOUT-DTI={best_score['dti']:.6f} vs prior best {best_prior_key}={best_prior_score['dti']:.6f} "
        f"(paired delta {paired_best['delta']:+.6f}, 95% CI [{paired_best['ci95'][0]:+.6f}, {paired_best['ci95'][1]:+.6f}], "
        f"ci_excludes_zero={ci_excludes_zero}); passes 108/108 pre-placement Spearman checks and "
        f"{len(passed_before_stop)} real rasters before literal Rule-1 stop on {stopped_name} "
        f"({stopped_dots} dots, overlap {stopped_ov:.4f} > 0.70); fail-closed negative for live slot expenditure."
    )

    card.update(
        verdict="negative",
        result="negative",
        verdict_reason=verdict_reason,
        submission_ready=False,
        completed_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    card["automated_gates"] = readiness.gates(card)
    card["ok_to_download"] = card["validator_output"]["status"] == "PASS"
    card["ok_to_submit"] = readiness.submission_ready(card)
    dump(CARD_PATH, card)

    # Register new `.tif` and `.zip` in `registry/artifact_policy.json`
    policy_path = ROOT / "registry/artifact_policy.json"
    policy = json.loads(policy_path.read_text())
    existing_paths = {f["path"] for f in policy["files"]}
    for p in (tif_path, tif_path.with_suffix(".zip")):
        rel = p.relative_to(ROOT).as_posix()
        entry = {
            "path": rel,
            "sha256": sha256_file(p),
            "status": "current_research_only",
            "reason": (
                f"S18-CWGR ({best_arm}) fresh computation; format PASS, HOLDOUT-DTI={best_score['dti']:.6f} "
                f"(paired delta vs {best_prior_key} {paired_best['delta']:+.6f}); passes 108/108 pre-placement "
                f"Spearman and GEMSDOE32 R0 ({r32_ov:.4f} <= 0.70), stopped fail-closed at {stopped_name} "
                f"({stopped_ov:.4f} > 0.70); NOT OK TO SUBMIT."
            ),
        }
        if rel in existing_paths:
            policy["files"] = [entry if x["path"] == rel else x for x in policy["files"]]
        else:
            policy["files"].append(entry)
    dump(policy_path, policy)
    log(
        f"S18-CWGR completed in {card['elapsed_seconds']}s: HOLDOUT-DTI={best_score['dti']:.6f}, "
        f"beats_comparable_best={card['automated_gates']['beats_comparable_best']}, "
        f"OK_TO_DOWNLOAD={card['ok_to_download']}, OK_TO_SUBMIT={card['ok_to_submit']}"
    )
    return card


if __name__ == "__main__":
    run()
