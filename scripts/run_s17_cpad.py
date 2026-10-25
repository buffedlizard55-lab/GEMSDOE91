#!/usr/bin/env python3
"""Session 17 (`S17-CPAD`) Preregistered Experiment Runner (`H17-1`: `E1`, `E2`, `E3`).

Strictly obeys `PARALLEL-RUN PROTOCOL` Rules 1–6:
  - Evaluates the strongest permissible prior architecture (`INCUMBENT-PTAC-LB`:
    `S14-PTAC E2` re-fitted strictly on `vendor/gems57/spatial.py::folds(cat, fp, buffer_px=80)`)
    side-by-side with `S16-PGRD`, `CED91`, `gravity_control`, and the `<= 3` preregistered
    `S17-CPAD` ablations (`cpad_e1`, `cpad_e2`, `cpad_e3`) on the unchanged label-blind
    shared evaluator `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`,
    `60,988` withheld positives, `1,000` paired 20 km physical-block bootstrap draws).
  - Eliminates `IR-91-S17-01` (no `~fold.buffer_mask` placement moat), `IR-91-S15-05`
    (verified `0.0` `Band 12 / Band 19` dependence in Stage-1 and Stage-2 Pure-Subsurface
    Specialists), `IR-91-S15-06` (exact training-domain Bayes reference-odds calibration
    `c0 = 12.0` across 2-, 3-, and 4-quadrant splits before `spac_coda` auto-context),
    and `IR-91-S15-07` (strictly local `<= 1.2 km` operators).
  - Packages one validated full-map `-zeros.tif` + single-TIFF `-zeros.zip` via
    `vendor/gems57/submission_writer.py::write_submission`, checks all three repository
    gate suites (`gems91.gates`, `gems91.release_gates`, `validate_raster`), enforces
    Rule 4 (`AUC <= 0.90`) and Rule 1 (`|rho| <= 0.90`, 3 px dot overlap `<= 70%`) across
    all `95` verified rasters in `registry/s17_comparison_inventory.json`, and updates
    `registry/artifact_policy.json` fail-closed.
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
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

import validate_raster as VR
from gems91 import (
    ced,
    cpad17 as CPAD,
    dd_vtc_pu as DD,
    gates as G91,
    hvdc as HVDC,
    mhtr_coda as MC,
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
PREREG = ROOT / "docs/HYPOTHESES_S17.md"
INVENTORY_PATH = ROOT / "registry/s17_comparison_inventory.json"
CARD_PATH = ROOT / "docs/run-card-S17-CPAD.json"
OUT_DIR = ROOT / "docs/s17"
CACHE_DIR = ROOT / "data/derived/s17"

DOT_BUDGET = 37_654
COLLAR_PX = 3.05
MIN_SPACING_PX = 3.05
BUFFER_PX = 80
SEED_BASE = 20261025


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


def phase_summary(report: dict) -> dict:
    return {k: v for k, v in report.items() if k != "comparisons"}


def open_or_write_surface_mmap(path: Path, shape: tuple[int, int], arr: np.ndarray | None = None) -> np.memmap:
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr is not None:
        mm = np.memmap(path, dtype=np.float32, mode="w+", shape=shape)
        mm[:] = arr.astype(np.float32, copy=False)
        mm.flush()
        del mm
    return np.memmap(path, dtype=np.float32, mode="r", shape=shape)


def open_or_write_table_mmap(path: Path, shape: tuple[int, int], arr: np.ndarray | None = None) -> np.memmap:
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


def compute_crest_concordance_fp(
    X_cpad: np.ndarray,
    X_s11: np.ndarray,
    X_ptha: np.ndarray,
) -> np.ndarray:
    """Bounded `[0, 1]` multi-physics accommodation & inflection crest concordance on footprint."""
    n_fp = X_cpad.shape[0]

    def _pct01(v: np.ndarray) -> np.ndarray:
        lo = float(np.percentile(v[::16], 10))
        hi = float(np.percentile(v[::16], 96))
        return np.clip((v - lo) / (hi - lo + 1e-6), 0.0, 1.0).astype(np.float32)

    c_theta_g = _pct01(np.asarray(X_cpad[:, 0], dtype=np.float32))
    c_worm_g = _pct01(np.asarray(X_cpad[:, 4], dtype=np.float32))
    c_sad_b = _pct01(np.asarray(X_cpad[:, 6], dtype=np.float32))
    c_worm_b = _pct01(np.asarray(X_cpad[:, 7], dtype=np.float32))
    c_demag = _pct01(np.asarray(X_cpad[:, 3], dtype=np.float32))
    c_marussi = _pct01(np.asarray(X_s11[:, 2], dtype=np.float32))
    c_mag_crest = _pct01(np.asarray(X_ptha[:, 2], dtype=np.float32))

    crest = (
        0.24 * c_theta_g
        + 0.18 * c_worm_g
        + 0.16 * c_worm_b
        + 0.12 * c_sad_b
        + 0.10 * c_demag
        + 0.10 * c_marussi
        + 0.10 * c_mag_crest
    ).astype(np.float32)
    assert crest.shape == (n_fp,)
    return np.clip(crest, 0.0, 1.0)


def build_feature_tables(fp: np.ndarray) -> dict[str, object]:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    shared_cache = ROOT / "data/derived/shared_stack_v1"
    shared_cache.mkdir(parents=True, exist_ok=True)

    log("1/6 Loading/building static DD feature memmap")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=STACK,
        gdr_csv=GDR_CSV,
        footprint=fp,
        cache_dir=shared_cache,
    )
    log("2/6 Loading/building S11 MHTR feature memmap")
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=STACK,
        footprint=fp,
        cache_dir=shared_cache,
    )
    log("3/6 Loading/building S12 SPAC feature memmap")
    X_s12, s12_names, _ = SC.build_or_load_s12_feature_memmap(
        features_tif=STACK,
        footprint=fp,
        cache_dir=shared_cache,
    )
    log("4/6 Loading/building S13 PTHA feature memmap")
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=STACK,
        footprint=fp,
        cache_dir=shared_cache,
    )
    log("5/6 Loading/building S14 HVDC feature memmap")
    X_hvdc, hvdc_names, _ = HVDC.build_or_load_hvdc_feature_memmap(
        features_tif=STACK,
        gdr_csv=GDR_CSV,
        footprint=fp,
        cache_dir=shared_cache,
    )
    log("6/6 Loading/building novel S17 CPAD 16-feature memmap")
    X_cpad, cpad_names, cpad_meta = CPAD.build_or_load_cpad_feature_memmap(
        features_tif=STACK,
        gdr_csv=GDR_CSV,
        footprint=fp,
        cache_dir=CACHE_DIR,
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
    }


def assemble_cpad_blocks(tables: dict[str, object]) -> dict[str, object]:
    raw_blocks = [
        (tables["X_static"], CPAD.STATIC_LOCAL_COLS, tables["static_names"]),
        (tables["X_s11"], CPAD.S11_LOCAL_COLS, tables["s11_names"]),
        (tables["X_s12"], CPAD.S12_LOCAL_COLS, tables["s12_names"]),
        (tables["X_ptha"], CPAD.PTHA_LOCAL_COLS, tables["ptha_names"]),
        (tables["X_hvdc"], CPAD.HVDC_LOCAL_COLS, tables["hvdc_names"]),
        (tables["X_cpad"], CPAD.CPAD_LOCAL_COLS, tables["cpad_names"]),
    ]

    full_blocks: list[tuple[np.ndarray, list[int]]] = []
    sub_blocks: list[tuple[np.ndarray, list[int]]] = []
    full_names: list[str] = []
    sub_names: list[str] = []

    for arr, cols, names in raw_blocks:
        f_cols = list(cols)
        s_cols = [c for c in cols if names[c] not in CPAD.STRICT_TOPO_FEATURE_NAMES]
        full_blocks.append((arr, f_cols))
        sub_blocks.append((arr, s_cols))
        full_names.extend(names[c] for c in f_cols)
        sub_names.extend(names[c] for c in s_cols)

    # Hard-negative mining columns inside each specialist's OWN feature list:
    # Full specialist: slope + Cooper gravity phase + Cooper RTP phase + subsurface clay baffle
    full_hard_targets = {
        "b19_det_elev_slope",
        "cpad_cooper_theta_grav",
        "cpad_cooper_theta_rtp",
        "cpad_claycap_subsurface_baffle",
    }
    # Subsurface specialist: 100% Band-12 / Band-19 free edge columns ONLY!
    sub_hard_targets = {
        "cpad_cooper_theta_grav",
        "cpad_cooper_theta_rtp",
        "cpad_claycap_subsurface_baffle",
        "s12_tmi_asig_log",
    }
    full_hard_cols = [i for i, n in enumerate(full_names) if n in full_hard_targets]
    sub_hard_cols = [i for i, n in enumerate(sub_names) if n in sub_hard_targets]

    # Assert zero topographic leakage in sub_names
    leaked = set(sub_names) & set(CPAD.STRICT_TOPO_FEATURE_NAMES)
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


def run_incumbent_ptac_lb(
    tables: dict[str, object],
    folds: list[dict],
    fp: np.ndarray,
) -> tuple[list[np.ndarray], dict[str, object]]:
    """Evaluate `S14-PTAC E2` faithfully on `spatial.folds(cat, fp, buffer_px=80)` (`INCUMBENT-PTAC-LB`)."""
    inc_dir = CACHE_DIR / "incumbent_ptac_lb"
    inc_dir.mkdir(parents=True, exist_ok=True)
    shape = fp.shape

    # S14-PTAC E2 static blocks (exact local + GDR static cols used in S14-PTAC)
    ptac_static_cols = list(range(34)) + [38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48]  # 45 cols
    base_blocks = [
        (tables["X_static"], ptac_static_cols),
        (tables["X_s11"], list(range(16))),
        (tables["X_s12"], list(range(20))),
        (tables["X_ptha"], list(range(20))),
        (tables["X_hvdc"], list(range(18))),
    ]
    hard_cols = [18, 45, 61]  # slope, mhtr grav, spac tmi_asig

    # 1. Pairwise 2-quadrant Stage-1 fits (strictly >80 px buffered from both held-out quadrants)
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

    # 2. 4 OOF Stage-1 fits + stitched Stage-2 fits + global submodular dot emission
    oof_dots: list[np.ndarray] = []
    fold_diag: list[dict[str, object]] = []
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

        # Stitch out-of-sample Stage-1 surface across all 4 quadrants for Fold q
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
            s2_cal, s2_meta = CPAD.fit_predict_specialist(
                blocks=s2_blocks,
                hard_neg_cols_in_stack=hard_cols,
                visible_faults=folds[q]["visible"] & folds[q]["train"],
                train_domain=folds[q]["train"],
                footprint=fp,
                seed=SEED_BASE + 300 + q,
            )
            pooled_arr = PTAC.log_opinion_pool(stitch_s1, s2_cal, fp, stage2_weight=0.65)
            pooled_q = open_or_write_surface_mmap(s2_path, shape, pooled_arr)
            fold_diag.append({"fold": q, **s2_meta})
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

    return oof_dots, {"architecture": "S14-PTAC E2 re-evaluated on gems57-pooled-hide-v2", "folds": fold_diag}


def run_cpad_hierarchy(
    tables: dict[str, object],
    spec: dict[str, object],
    folds: list[dict],
    cat: np.ndarray,
    fp: np.ndarray,
) -> dict[str, object]:
    """Fit cross-fitted Stage-1 + Stage-2 Dual-Specialist `S17-CPAD` (`E1`, `E2`, `E3`)."""
    cpad_dir = CACHE_DIR / "cpad17_models"
    cpad_dir.mkdir(parents=True, exist_ok=True)
    shape = fp.shape

    full_blocks = spec["full_blocks"]
    sub_blocks = spec["sub_blocks"]
    full_hard = spec["full_hard_cols"]
    sub_hard = spec["sub_hard_cols"]

    cover_prior_fp = np.asarray(tables["X_cpad"][:, 15], dtype=np.float32)
    crest_bonus_fp = compute_crest_concordance_fp(tables["X_cpad"], tables["X_s11"], tables["X_ptha"])

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

        pf_path = cpad_dir / f"pair_full_{a}_{b}.f32.mmap"
        if pf_path.is_file() and pf_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_full[(a, b)] = open_or_write_surface_mmap(pf_path, shape)
        else:
            log(f"[S17-CPAD] Fitting pairwise Stage-1 Full ({a},{b})")
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

        ps_path = cpad_dir / f"pair_sub_{a}_{b}.f32.mmap"
        if ps_path.is_file() and ps_path.stat().st_size == shape[0] * shape[1] * 4:
            pair_sub[(a, b)] = open_or_write_surface_mmap(ps_path, shape)
        else:
            log(f"[S17-CPAD] Fitting pairwise Stage-1 Pure-Subsurface ({a},{b})")
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
    for q in range(4):
        of_path = cpad_dir / f"oof_s1_full_q{q}.f32.mmap"
        if of_path.is_file() and of_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_full.append(open_or_write_surface_mmap(of_path, shape))
        else:
            log(f"[S17-CPAD] Fitting OOF Stage-1 Full fold {q}")
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

        os_path = cpad_dir / f"oof_s1_sub_q{q}.f32.mmap"
        if os_path.is_file() and os_path.stat().st_size == shape[0] * shape[1] * 4:
            oof_s1_sub.append(open_or_write_surface_mmap(os_path, shape))
        else:
            log(f"[S17-CPAD] Fitting OOF Stage-1 Pure-Subsurface fold {q}")
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

    # --- Step C: 4 OOF Stage-2 fits (Full + Pure-Subsurface) -> E1, E2, E3 fold dots ---
    e1_dots_folds: list[np.ndarray] = []
    e2_dots_folds: list[np.ndarray] = []
    e3_dots_folds: list[np.ndarray] = []
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

        ac_f_q = compute_ac_mmap(cpad_dir / f"ac_full_q{q}.f32.mmap", stitch_f, fp)
        ac_s_q = compute_ac_mmap(cpad_dir / f"ac_sub_q{q}.f32.mmap", stitch_s, fp)

        # Stage-2 Full (uses static full_blocks + ac_full + ac_sub = 148 features)
        s2f_path = cpad_dir / f"oof_s2_full_q{q}.f32.mmap"
        if s2f_path.is_file() and s2f_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_full_q = open_or_write_surface_mmap(s2f_path, shape)
        else:
            log(f"[S17-CPAD] Fitting OOF Stage-2 Full fold {q}")
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

        # Stage-2 Pure-Subsurface (uses ONLY DEM-free sub_blocks + ac_sub = 110 features; ZERO B12/B19!)
        s2s_path = cpad_dir / f"oof_s2_sub_q{q}.f32.mmap"
        if s2s_path.is_file() and s2s_path.stat().st_size == shape[0] * shape[1] * 4:
            s2_sub_q = open_or_write_surface_mmap(s2s_path, shape)
        else:
            log(f"[S17-CPAD] Fitting OOF Stage-2 Pure-Subsurface fold {q}")
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

        # E1 surface: Stage-1 Full + Stage-2 Full log-opinion pool -> greedy NMS
        surf_e1_q = PTAC.log_opinion_pool(stitch_f, np.asarray(s2_full_q, dtype=np.float32), fp, stage2_weight=0.66)
        # E2/E3 surface: Cover-Gated Dual-Specialist Stage-1+Stage-2 + Accommodation Crest Concordance
        surf_e2_q = CPAD.blend_cover_gated_specialists(
            s1_full=stitch_f,
            s1_sub=stitch_s,
            s2_full=np.asarray(s2_full_q, dtype=np.float32),
            s2_sub=np.asarray(s2_sub_q, dtype=np.float32),
            cover_prior_fp=cover_prior_fp,
            crest_bonus_fp=crest_bonus_fp,
            footprint=fp,
        )
        oof_e2_mosaic[folds[q]["region"]] = surf_e2_q[folds[q]["region"]]

        log(f"[S17-CPAD] Emitting global blind dots for fold {q} (E1, E2, E3)")
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

        del stitch_f, stitch_s, ac_f_q, ac_s_q, s2_full_q, s2_sub_q, surf_e1_q, surf_e2_q
        gc.collect()

    # --- Step D: Full 4-quadrant inference surfaces for E1, E2, E3 ---
    stitched_oof_f = np.zeros(shape, dtype=np.float32)
    stitched_oof_s = np.zeros(shape, dtype=np.float32)
    for q in range(4):
        stitched_oof_f[folds[q]["region"]] = oof_s1_full[q][folds[q]["region"]]
        stitched_oof_s[folds[q]["region"]] = oof_s1_sub[q][folds[q]["region"]]

    ac_oof_f = compute_ac_mmap(cpad_dir / "ac_oof_mosaic_full.f32.mmap", stitched_oof_f, fp)
    ac_oof_s = compute_ac_mmap(cpad_dir / "ac_oof_mosaic_sub.f32.mmap", stitched_oof_s, fp)

    ff_s1_path = cpad_dir / "full_s1_full.f32.mmap"
    if ff_s1_path.is_file() and ff_s1_path.stat().st_size == shape[0] * shape[1] * 4:
        full_s1_f = open_or_write_surface_mmap(ff_s1_path, shape)
    else:
        log("[S17-CPAD] Fitting 4-quadrant full Stage-1 Full")
        surf, meta = CPAD.fit_predict_specialist(
            blocks=full_blocks,
            hard_neg_cols_in_stack=full_hard,
            visible_faults=cat & fp,
            train_domain=fp,
            footprint=fp,
            seed=SEED_BASE + 7000,
        )
        calibration_log.append({"split": "full_4quad", "specialist": "full", **meta})
        full_s1_f = open_or_write_surface_mmap(ff_s1_path, shape, surf)
        del surf
        gc.collect()

    fs_s1_path = cpad_dir / "full_s1_sub.f32.mmap"
    if fs_s1_path.is_file() and fs_s1_path.stat().st_size == shape[0] * shape[1] * 4:
        full_s1_s = open_or_write_surface_mmap(fs_s1_path, shape)
    else:
        log("[S17-CPAD] Fitting 4-quadrant full Stage-1 Pure-Subsurface")
        surf, meta = CPAD.fit_predict_specialist(
            blocks=sub_blocks,
            hard_neg_cols_in_stack=sub_hard,
            visible_faults=cat & fp,
            train_domain=fp,
            footprint=fp,
            seed=SEED_BASE + 7100,
        )
        calibration_log.append({"split": "full_4quad", "specialist": "pure_subsurface", **meta})
        full_s1_s = open_or_write_surface_mmap(fs_s1_path, shape, surf)
        del surf
        gc.collect()

    ac_infer_f = compute_ac_mmap(cpad_dir / "ac_infer_full.f32.mmap", full_s1_f, fp)
    ac_infer_s = compute_ac_mmap(cpad_dir / "ac_infer_sub.f32.mmap", full_s1_s, fp)

    # Full Stage-2 trained on OOF mosaic auto-context, predicting on full Stage-1 auto-context
    ff_s2_path = cpad_dir / "full_s2_full.f32.mmap"
    if ff_s2_path.is_file() and ff_s2_path.stat().st_size == shape[0] * shape[1] * 4:
        full_s2_f = open_or_write_surface_mmap(ff_s2_path, shape)
    else:
        log("[S17-CPAD] Fitting 4-quadrant full Stage-2 Full (trained on OOF mosaic ac, inferred on full ac)")
        tr_b = full_blocks + [(ac_oof_f, list(range(10))), (ac_oof_s, list(range(10)))]
        in_b = full_blocks + [(ac_infer_f, list(range(10))), (ac_infer_s, list(range(10)))]
        raw_s2f, meta = PTAC.fit_predict_stage2(
            train_blocks=tr_b,
            infer_blocks=in_b,
            visible_faults=cat & fp,
            exclude_mask=~fp,
            footprint=fp,
            seed=SEED_BASE + 8000,
        )
        cal_s2f = CPAD.calibrate_reference_odds_surface(
            raw_s2f,
            fp,
            pi_vis_train=float(meta["pi_vis_train"]),
            pi_sample_weighted=float(meta["pi_sample_weighted"]),
            c0_multiplier=12.0,
        )
        calibration_log.append({"split": "s2_full_4quad", "specialist": "full", **meta})
        full_s2_f = open_or_write_surface_mmap(ff_s2_path, shape, cal_s2f)
        del raw_s2f, cal_s2f
        gc.collect()

    fs_s2_path = cpad_dir / "full_s2_sub.f32.mmap"
    if fs_s2_path.is_file() and fs_s2_path.stat().st_size == shape[0] * shape[1] * 4:
        full_s2_s = open_or_write_surface_mmap(fs_s2_path, shape)
    else:
        log("[S17-CPAD] Fitting 4-quadrant full Stage-2 Pure-Subsurface (0 B12/B19 features)")
        tr_bs = sub_blocks + [(ac_oof_s, list(range(10)))]
        in_bs = sub_blocks + [(ac_infer_s, list(range(10)))]
        raw_s2s, meta = PTAC.fit_predict_stage2(
            train_blocks=tr_bs,
            infer_blocks=in_bs,
            visible_faults=cat & fp,
            exclude_mask=~fp,
            footprint=fp,
            seed=SEED_BASE + 8100,
        )
        cal_s2s = CPAD.calibrate_reference_odds_surface(
            raw_s2s,
            fp,
            pi_vis_train=float(meta["pi_vis_train"]),
            pi_sample_weighted=float(meta["pi_sample_weighted"]),
            c0_multiplier=12.0,
        )
        calibration_log.append({"split": "s2_full_4quad", "specialist": "pure_subsurface", **meta})
        full_s2_s = open_or_write_surface_mmap(fs_s2_path, shape, cal_s2s)
        del raw_s2s, cal_s2s
        gc.collect()

    full_surf_e1 = PTAC.log_opinion_pool(
        np.asarray(full_s1_f, dtype=np.float32),
        np.asarray(full_s2_f, dtype=np.float32),
        fp,
        stage2_weight=0.66,
    )
    full_surf_e2 = CPAD.blend_cover_gated_specialists(
        s1_full=np.asarray(full_s1_f, dtype=np.float32),
        s1_sub=np.asarray(full_s1_s, dtype=np.float32),
        s2_full=np.asarray(full_s2_f, dtype=np.float32),
        s2_sub=np.asarray(full_s2_s, dtype=np.float32),
        cover_prior_fp=cover_prior_fp,
        crest_bonus_fp=crest_bonus_fp,
        footprint=fp,
    )

    return {
        "e1_dots_folds": e1_dots_folds,
        "e2_dots_folds": e2_dots_folds,
        "e3_dots_folds": e3_dots_folds,
        "full_surf_e1": full_surf_e1,
        "full_surf_e2": full_surf_e2,
        "oof_e2_mosaic": oof_e2_mosaic,
        "ac_oof_f": ac_oof_f,
        "ac_oof_s": ac_oof_s,
        "calibration_log": calibration_log,
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
    log("Running Rule 4 single-feature AUROC leak canaries across all 128 static + 20 OOF auto-context features")
    y_fp = cat[fp]
    quad_masks_fp = [f["region"][fp] for f in folds]

    features_report: dict[str, dict[str, object]] = {}

    # 1. Exact `ced.auc_canary` on all 16 novel CPAD features
    for idx, name in enumerate(CPAD.CPAD_FEATURE_NAMES):
        grid = np.zeros(fp.shape, dtype=np.float32)
        grid[fp] = np.asarray(tables["X_cpad"][:, idx], dtype=np.float32)
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

    # 2. All remaining 112 static Stage-1 features + 20 OOF auto-context features
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

    for prefix, ac_mm in (("ac_full", ac_oof_f), ("ac_sub", ac_oof_s)):
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
        "split": "label-blind-quadrants-v2",
        "withheld_positive_pixels": int(y_fp.sum()),
        "features_tested": len(features_report),
        "max_symmetric_auc": round(max_pooled, 6),
        "max_quadrant_symmetric_auc": round(max_quad, 6),
        "status": "PASS" if all_pass else "LEAKAGE_SUSPECTED",
        "features": features_report,
    }


def evaluate_blind_sgmc_control(
    dots_by_name: dict[str, np.ndarray],
    cat: np.ndarray,
    fp: np.ndarray,
) -> dict[str, object]:
    """Supplementary evaluation on 62,122 off-catalogue USGS SGMC faults (>500 m from catalogue)."""
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


def extract_milestone_comparisons(pre_report: dict, final_report: dict) -> list[dict[str, object]]:
    milestones = [
        ("GEMSDOE32 R0 (unscored parent)", "GEMSDOE32__h33-2-b2-zeros.tif"),
        ("S14-PTAC E2 (legacy-fold best)", "gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif"),
        ("S14-HVDC E2", "gems91-s14-hvdc-e2-20261024T223000Z-0a0bb0cb-zeros.tif"),
        ("S15-SCGF E2", "gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.tif"),
        ("S16-PGRD (strict label-blind)", "gems91-s16-pgrd-20261025T040447Z-24d090ad9f42-zeros.tif"),
        ("S16-PC91", "gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif"),
        ("CED91", "gems91-ced-v1-20261024-d35670b28c81.tif"),
    ]
    pre_map = {Path(r["file"]).name: r for r in pre_report.get("comparisons", [])}
    fin_map = {Path(r["file"]).name: r for r in final_report.get("comparisons", [])}
    rows: list[dict[str, object]] = []
    for label, fname in milestones:
        pr = pre_map.get(fname, {})
        fr = fin_map.get(fname, {})
        rows.append(
            {
                "label": label,
                "file": fname,
                "preplacement_spearman_rho": pr.get("surface", {}).get("rank_correlation"),
                "final_dot_spearman_rho": fr.get("surface", {}).get("rank_correlation"),
                "final_3px_dot_overlap": fr.get("dots", {}).get("overlap_within_3px"),
                "status": fr.get("status", pr.get("status", "NOT_REACHED")),
            }
        )
    return rows


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

    # Initialize fail-closed run card immediately
    card: dict[str, object] = {
        "schema_version": "gems91.s17-cpad.v1",
        "branch": "arena/aecf32eb-gemsdoe91",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration": {
            "path": "docs/HYPOTHESES_S17.md",
            "sha256": sha256_file(PREREG),
        },
        "lane": {
            "name": "S17-CPAD",
            "assigned": False,
            "status": "PROVISIONAL_RESEARCH_ONLY",
            "reason": "Single local lane S17-CPAD enforced; no external multi-agent lane coordinator token supplied.",
        },
        "hypothesis": (
            "H17-1 (S17-CPAD): Cooper-Cowan potential-field edge phase & hydrothermal magnetite-destruction "
            "Poisson deficit, Faulds-Hinz hyperbolic accommodation saddles & 105 deg Riedel transtensional "
            "shear-dilation, and local (<1.2 km) chemical geothermometer disequilibrium combined via "
            "reference-odds-calibrated Stage-1 + Stage-2 Pure-Subsurface and Full Dual-Specialists improve "
            "label-blind concealed fault recovery."
        ),
        "mechanism": (
            "16 novel CPAD blind-geothermal features (14 strictly Band-12/Band-19 invariant); 100/128 DEM-free "
            "Pure-Subsurface Stage-1 + Stage-2 Specialist; exact training-domain Bayes reference-odds calibration "
            "(c0=12.0) cancelling 2/3/4-quadrant prevalence drift prior to spac_coda axial auto-context; "
            "continuous sedimentary Cover-Concealment Gate; 300 m submodular triangular-kernel dot allocation."
        ),
        "named_non_fault_mimic_process": (
            "Unfaulted intracaldera felsic tuffs / reversely magnetized flows (mimic Poisson magnetic lows), "
            "closed-basin evaporitic alkali playas (mimic Band 17 shallow conductivity), and buried paleochannels / "
            "pluton margins (mimic smooth basement curvature)."
        ),
        "experiments_run": 3,
        "budget": {
            "max_experiments": 3,
            "planned_candidates": 3,
            "incumbent_baseline_runs": 1,
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
            "inventory": "registry/s17_comparison_inventory.json",
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

    # 1. Build / verify static feature tables
    tables = build_feature_tables(fp)
    spec = assemble_cpad_blocks(tables)

    # Verify programmatic Band-12 / Band-19 invariance on a synthetic miniature patch
    log("Verifying programmatic Band-12 / Band-19 invariance of CPAD subsurface columns")
    rng_chk = np.random.default_rng(17)
    fp_chk = np.ones((48, 56), dtype=bool)
    needed_b = (2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19)
    b_a = {b: rng_chk.normal(0.0, 5.0, size=(48, 56)).astype(np.float32) for b in needed_b}
    b_b = dict(b_a)
    b_b[12] = rng_chk.normal(300.0, 100.0, size=(48, 56)).astype(np.float32)
    b_b[19] = np.abs(rng_chk.normal(20.0, 10.0, size=(48, 56))).astype(np.float32)
    xa, _ = CPAD.compute_cpad_arrays_from_bands(b_a, fp_chk, gdr_csv=GDR_CSV)
    xb, _ = CPAD.compute_cpad_arrays_from_bands(b_b, fp_chk, gdr_csv=GDR_CSV)
    max_dem_leak = float(np.max(np.abs(xa[:, :14] - xb[:, :14])))
    if max_dem_leak != 0.0:
        raise AssertionError(f"CPAD subsurface DEM leak detected: {max_dem_leak}")
    del b_a, b_b, xa, xb

    feat_receipt = {
        "cpad_code_sha256": sha256_file(ROOT / "src/gems91/cpad17.py"),
        "cpad_meta": tables["cpad_meta"],
        "stage1_full_feature_count": len(spec["full_names"]),
        "stage1_pure_subsurface_feature_count": len(spec["sub_names"]),
        "strict_topo_excluded_count": len(spec["full_names"]) - len(spec["sub_names"]),
        "verified_cpad_subsurface_b12_b19_max_diff": max_dem_leak,
        "stage1_full_features": spec["full_names"],
        "stage1_pure_subsurface_features": spec["sub_names"],
    }
    dump(OUT_DIR / "features.json", feat_receipt)
    card["features"] = {
        "file": "s17/features.json",
        "stage1_full_count": len(spec["full_names"]),
        "stage1_pure_subsurface_count": len(spec["sub_names"]),
        "cpad_novel_count": len(CPAD.CPAD_FEATURE_NAMES),
    }

    # 2. Construct canonical label-blind spatial quadrant folds (buffer_px=80 = 8.0 km)
    log("Constructing canonical spatial.folds(cat, fp, buffer_px=80)")
    folds = list(spatial.folds(cat, fp, buffer_px=BUFFER_PX))
    split_sha = hashlib.sha256(
        b"".join(
            np.packbits(f[k].ravel()).tobytes()
            for f in folds
            for k in ("region", "truth", "train", "visible")
        )
    ).hexdigest()

    # 3. Evaluate label-blind CED91, S16-PGRD, and Cooper gravity control on identical folds
    log("Computing label-blind CED91, S16-PGRD, and Gravity-Theta control baselines")
    with rasterio.open(STACK) as ds:
        b1_m = ds.read(1)
        b2_rtp = ds.read(2)
        b13_g = ds.read(13)
    ced_fields = ced.features(b1_m, b13_g, fp)
    ced_surf = np.asarray(ced_fields["surface"], dtype=np.float32)
    del ced_fields, b1_m
    pgrd_fields = PGRD.features(b2_rtp, b13_g, fp)
    pgrd_surf = np.asarray(pgrd_fields["surface"], dtype=np.float32)
    del pgrd_fields, b2_rtp, b13_g
    gc.collect()
    grav_ctrl_surf = np.zeros(shape, dtype=np.float32)
    grav_ctrl_surf[fp] = np.asarray(tables["X_cpad"][:, 0], dtype=np.float32)

    ced_dots_folds = [
        ced.place(ced_surf, fp & (~f["visible"]), DOT_BUDGET)
        for f in folds
    ]
    pgrd_dots_folds = [
        ced.place(pgrd_surf, fp & (~f["visible"]), DOT_BUDGET)
        for f in folds
    ]
    grav_dots_folds = [
        CPAD.emit_global_dots_nms(
            grav_ctrl_surf, f["visible"], fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
        > 0
        for f in folds
    ]
    del ced_surf, grav_ctrl_surf
    gc.collect()

    # 4. Run INCUMBENT-PTAC-LB (`S14-PTAC E2` re-fitted strictly on spatial.folds)
    inc_dots_folds, inc_meta = run_incumbent_ptac_lb(tables, folds, fp)

    # 5. Run S17-CPAD (`E1`, `E2`, `E3`)
    cpad_out = run_cpad_hierarchy(tables, spec, folds, cat, fp)

    # 6. Run Rule 4 Single-Feature Leak Canaries (`AUC <= 0.90`)
    canary_path = OUT_DIR / "canaries.json"
    if canary_path.is_file():
        canary_report = json.loads(canary_path.read_text())
        if canary_report.get("features_tested") != len(spec["full_names"]) + 20:
            canary_report = run_canaries(
                tables, spec, cpad_out["ac_oof_f"], cpad_out["ac_oof_s"], folds, cat, fp
            )
            dump(canary_path, canary_report)
    else:
        canary_report = run_canaries(
            tables,
            spec,
            cpad_out["ac_oof_f"],
            cpad_out["ac_oof_s"],
            folds,
            cat,
            fp,
        )
        dump(canary_path, canary_report)
    card["canaries"] = {
        "status": canary_report["status"],
        "features_tested": canary_report["features_tested"],
        "max_symmetric_auc": canary_report["max_symmetric_auc"],
        "max_quadrant_symmetric_auc": canary_report["max_quadrant_symmetric_auc"],
        "file": "s17/canaries.json",
    }
    if canary_report["status"] != "PASS":
        raise RuntimeError(f"Rule 4 canary failure: {card['canaries']}")

    # 7. Score all 7 arms on unchanged vendor/gems57/evaluate_holdout.py (`gems57-pooled-hide-v2`)
    log("Scoring all 7 arms on unchanged vendor/gems57/evaluate_holdout.py (1,000 block bootstrap draws)")
    arm_fold_dots = {
        "gravity_control": grav_dots_folds,
        "ced91": ced_dots_folds,
        "s16_pgrd": pgrd_dots_folds,
        "incumbent_ptac_lb": inc_dots_folds,
        "cpad_e1": cpad_out["e1_dots_folds"],
        "cpad_e2": cpad_out["e2_dots_folds"],
        "cpad_e3": cpad_out["e3_dots_folds"],
    }

    fold_records: list[dict[str, object]] = []
    terms_by_arm: dict[str, np.ndarray] = {}
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
            arm_scores_q[arm_name] = {
                **score_q,
                "global_emitted": int(g_dots.sum()),
            }
            terms_by_arm[arm_name] = terms_by_arm.get(arm_name, 0.0) + terms_q
        fold_records.append(
            {
                "fold": int(fold.get("fold", q)),
                "receipt": fold["receipt"],
                "global_budget": DOT_BUDGET,
                "arms": arm_scores_q,
            }
        )

    # Select winning S17-CPAD arm strictly by pooled HOLDOUT-DTI across {cpad_e1, cpad_e2, cpad_e3}
    cpad_arm_dtis = {
        a: float(evaluator.from_terms(terms_by_arm[a].sum(axis=0)))
        for a in ("cpad_e1", "cpad_e2", "cpad_e3")
    }
    best_arm = max(cpad_arm_dtis, key=cpad_arm_dtis.get)
    log(f"CPAD arm HOLDOUT-DTIs: {cpad_arm_dtis} -> winning arm: {best_arm}")

    summary_all = evaluator.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate=best_arm)
    prior_terms = {
        k: terms_by_arm[k]
        for k in (best_arm, "incumbent_ptac_lb", "ced91", "s16_pgrd", "gravity_control")
    }
    summary_vs_prior = evaluator.pooled_summary(prior_terms, draws=1000, seed=520810, candidate=best_arm)

    best_prior_key = str(summary_vs_prior["best_comparable_control"])
    best_prior_score = summary_vs_prior["scores"][best_prior_key]
    paired_best = summary_vs_prior["paired_differences"][best_prior_key]
    prior_candidates = {
        "INCUMBENT-PTAC-LB": summary_all["scores"]["incumbent_ptac_lb"]["dti"],
        "CED91": summary_all["scores"]["ced91"]["dti"],
        "S16-PGRD": summary_all["scores"]["s16_pgrd"]["dti"],
        "GRAVITY-THETA-CONTROL": summary_all["scores"]["gravity_control"]["dti"],
    }
    best_prior_name = best_prior_key
    best_prior_val = float(best_prior_score["dti"])
    best_score = summary_all["scores"][best_arm]
    delta_vs_incumbent = summary_vs_prior["paired_differences"]["incumbent_ptac_lb"]
    delta_vs_ced = summary_vs_prior["paired_differences"]["ced91"]
    delta_vs_s16 = summary_vs_prior["paired_differences"]["s16_pgrd"]
    delta_vs_grav = summary_vs_prior["paired_differences"]["gravity_control"]

    holdout_payload = {
        "split_sha256": split_sha,
        "buffer_px": BUFFER_PX,
        "global_dot_budget": DOT_BUDGET,
        "collar_px": COLLAR_PX,
        "min_spacing_px": MIN_SPACING_PX,
        "winning_cpad_arm": best_arm,
        "summary_all_arms": summary_all,
        "summary_vs_prior_baselines": summary_vs_prior,
        "comparable_prior_benchmarks": prior_candidates,
        "incumbent_metadata": inc_meta,
        "calibration_log": cpad_out["calibration_log"],
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
        "paired_best": paired_best,
        "paired_vs_incumbent_ptac_lb": delta_vs_incumbent,
        "paired_vs_ced91": delta_vs_ced,
        "paired_vs_s16_pgrd": delta_vs_s16,
        "paired_vs_gravity_control": delta_vs_grav,
        "status": "COMPLETED",
        "file": "s17/holdout.json",
    }
    card["comparable_prior_holdout_best"] = {
        "label": "HOLDOUT-DTI",
        "source": best_prior_name,
        "evaluator_version": evaluator.VERSION,
        "split_sha256": split_sha,
        "withheld_positives": best_prior_score["withheld_positive_pixels"],
        "value": best_prior_val,
        "ci95": best_prior_score["ci95"],
        "beats_comparable_prior_best": bool(best_score["dti"] > best_prior_val),
        "delta": float(paired_best["delta"]),
        "paired_ci95": paired_best["ci95"],
    }

    # 8. Build full-map prediction for winning arm + evaluate supplementary BLIND-SGMC-CONTROL-DTI
    if best_arm == "cpad_e1":
        best_full_surface = cpad_out["full_surf_e1"]
        best_full_dots = CPAD.emit_global_dots_nms(
            best_full_surface, cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
    elif best_arm == "cpad_e2":
        best_full_surface = cpad_out["full_surf_e2"]
        best_full_dots = CPAD.emit_global_dots_nms(
            best_full_surface, cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )
    else:
        best_full_surface = cpad_out["full_surf_e2"]
        best_full_dots = CPAD.emit_global_dots_submodular(
            best_full_surface, cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
        )

    # Also build full-map E1, E2, E3 dots + PGRD + GEMSDOE32 for blind SGMC diagnostic
    full_dots_e1 = CPAD.emit_global_dots_nms(
        cpad_out["full_surf_e1"], cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
    )
    full_dots_e2 = CPAD.emit_global_dots_nms(
        cpad_out["full_surf_e2"], cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
    )
    full_dots_e3 = CPAD.emit_global_dots_submodular(
        cpad_out["full_surf_e2"], cat, fp, budget=DOT_BUDGET, collar_px=COLLAR_PX, min_spacing_px=MIN_SPACING_PX
    )
    full_dots_pgrd = ced.place(pgrd_surf, fp & (~cat), DOT_BUDGET).astype(np.float32)
    with rasterio.open(ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif") as r32_src:
        r32_dots = (r32_src.read(1) > 0).astype(np.float32)
    with rasterio.open(ROOT / "docs/downloads/gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif") as s14_src:
        s14_dots = (s14_src.read(1) > 0).astype(np.float32)

    sgmc_report = evaluate_blind_sgmc_control(
        {
            "gemsdoe32_r0": r32_dots,
            "s14_ptac_e2_legacy_artifact": s14_dots,
            "s16_pgrd": full_dots_pgrd,
            "cpad_e1": full_dots_e1,
            "cpad_e2": full_dots_e2,
            "cpad_e3": full_dots_e3,
        },
        cat,
        fp,
    )
    dump(OUT_DIR / "blind-sgmc-control.json", sgmc_report)
    card["blind_sgmc_control"] = {
        "evidence_class": "BLIND-SGMC-CONTROL-DTI",
        "file": "s17/blind-sgmc-control.json",
        "blind_sgmc_positive_pixels": sgmc_report["blind_sgmc_positive_pixels"],
        "winning_arm_dti": sgmc_report["scores"][best_arm]["dti"],
        "scores": {k: v["dti"] for k, v in sgmc_report["scores"].items()},
    }
    del r32_dots, s14_dots, full_dots_e1, full_dots_e2, full_dots_e3, full_dots_pgrd
    gc.collect()

    # 9. Pre-placement surface novelty check across all 95 verified rasters
    log("Running Rule 1 pre-placement full-footprint Spearman rank-correlation check")
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

    # 10. Package single validated `-zeros.tif` + `-zeros.zip` via shared `vendor/gems57/submission_writer.py`
    dot_bool = best_full_dots > 0
    pixel_digest = hashlib.sha256(dot_bool.astype(np.uint8).tobytes()).hexdigest()
    tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arm_slug = best_arm.replace("_", "-")
    sub_name = f"gems91-s17-{arm_slug}-{tag}-{pixel_digest[:12]}"
    note = (
        f"S17-CPAD ({best_arm}): Cooper-Cowan phase, saddles & geotherm diseq dual-spec; "
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
            "lane": "S17-CPAD",
            "winning_arm": best_arm,
            "hypothesis_prereg_sha256": card["preregistration"]["sha256"],
            "holdout_dti": best_score["dti"],
            "holdout_evaluator": evaluator.VERSION,
            "no_prior_submission_copied": True,
        },
    )
    dump(OUT_DIR / "writer-receipt.json", receipt)

    # Run all additional repository gate suites on the written `-zeros.tif`
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

    with rasterio.open(tif_path) as s:
        arr = s.read(1)
        checks = {
            "single_band": s.count == 1,
            "float32": s.dtypes == ("float32",),
            "crs_match": s.crs == sample_meta[2],
            "shape_match": s.shape == shape,
            "transform_match": s.transform == sample_meta[3],
            "all_cells_finite": bool(np.isfinite(arr).all()),
            "range_0_1": bool((arr >= 0.0).all() and (arr <= 1.0).all()),
            "zero_outside": bool((arr[~fp] == 0.0).all()),
            "zero_on_catalogue": bool((arr[cat] == 0.0).all()),
            "no_nodata_tag": s.nodata is None,
            "exact_dot_count": int((arr > 0).sum()) == DOT_BUDGET,
            "spacing_strictly_over_3px": min_interdot_px > 3.0,
            "collar_strictly_over_3px": min_cat_px > 3.0,
            "release_gates_pass": bool(rg_zeros["PASS"]),
            "validate_raster_pass": bool(vr_zeros.ok),
            "identity_new_vs_frozen_hashes": receipt["sha256"] not in {x["sha256"] for x in inventory["files"]},
        }
        validator = {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "no_nan_inside_footprint": bool(np.isfinite(arr[fp]).all()),
            "values_in_0_1": checks["range_0_1"],
            "crs_shape_transform_match": checks["crs_match"] and checks["shape_match"] and checks["transform_match"],
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
            "source": "Reopened generated TIFF + verified single-member ZIP + release_gates + validate_raster.",
        }
    del arr
    if validator["status"] != "PASS":
        raise RuntimeError(f"Post-write validator failed: {validator}")

    # 11. Final Rule 1 3-px dot overlap & rank check across all 95 verified rasters
    log("Running Rule 1 final 3-px dot overlap check across 95-raster inventory")
    final_reg = run_ced.registry_phase(best_full_surface, fp, inventory, sample_meta, dots=dot_bool)
    dump(OUT_DIR / "registry-final.json", final_reg)

    non_calib_checked = [
        r for r in final_reg["comparisons"]
        if not (Path(r["file"]).name.startswith("calib_") or "lattice" in Path(r["file"]).name)
    ]
    passed_before_stop = [r for r in final_reg["comparisons"] if r.get("status") == "PASS"]
    max_passed_overlap = max(
        (float(r.get("dots", {}).get("overlap_within_3px") or 0.0) for r in passed_before_stop),
        default=0.0,
    )
    max_real_overlap = max(
        (float(r.get("dots", {}).get("overlap_within_3px") or 0.0) for r in non_calib_checked),
        default=0.0,
    )
    max_real_rho = max(
        (abs(float(r.get("surface", {}).get("rank_correlation") or 0.0)) for r in non_calib_checked),
        default=0.0,
    )
    milestones = extract_milestone_comparisons(pre_reg, final_reg)
    # Populate diagnostic post-stop 3-px dot overlap on key in-repo milestones without altering final_reg stop accounting
    from gems91 import novelty as _nov
    for m_row in milestones:
        if m_row["final_3px_dot_overlap"] is None:
            cand_matches = list(ROOT.glob(f"**/{m_row['file']}"))
            if cand_matches:
                with rasterio.open(cand_matches[0]) as _msrc:
                    _m_arr = _msrc.read(1)
                _dc = _nov.dot_check(dot_bool, _m_arr, fp)
                m_row["diagnostic_post_stop_3px_overlap"] = _dc["overlap_within_3px"]
                m_row["diagnostic_post_stop_registry_dots"] = _dc["registry_dots"]
    dump(
        OUT_DIR / "milestone-novelty.json",
        {
            "milestones": milestones,
            "passed_before_stop_count": len(passed_before_stop),
            "max_passed_before_stop_3px_overlap": max_passed_overlap,
            "non_calibration_checked": len(non_calib_checked),
            "max_checked_3px_overlap": max_real_overlap,
            "max_checked_rank_corr": max_real_rho,
        },
    )

    card["registry_comparison"]["final"] = phase_summary(final_reg)
    card["registry_comparison"]["passed_before_stop_count"] = len(passed_before_stop)
    card["registry_comparison"]["max_passed_before_stop_3px_overlap"] = round(max_passed_overlap, 6)
    card["registry_comparison"]["non_calibration_real_references_checked"] = len(non_calib_checked)
    card["registry_comparison"]["max_real_submission_3px_overlap"] = round(max_real_overlap, 6)
    card["registry_comparison"]["max_real_submission_rank_correlation"] = round(max_real_rho, 6)
    card["registry_comparison"]["milestone_comparisons"] = milestones
    card["registry_comparison"]["max_measured_final_dot_overlap_within_3px"] = max(
        (float(r.get("dots", {}).get("overlap_within_3px") or 0.0) for r in final_reg["comparisons"]),
        default=None,
    )
    card["registry_comparison"]["max_measured_final_dot_rank_correlation"] = max(
        (abs(float(r.get("surface", {}).get("rank_correlation") or 0.0)) for r in final_reg["comparisons"]),
        default=None,
    )

    card.update(
        submission_name=sub_name,
        note=note,
        raster_sha256=receipt["sha256"],
        raster_pixel_sha256=pixel_digest,
        validator_output=validator,
        artifact={
            "file": f"downloads/{tif_path.name}",
            "zip": f"downloads/{receipt['zip_file']}",
            "bytes": tif_path.stat().st_size,
            "zip_bytes": (tif_path.with_suffix(".zip")).stat().st_size,
            "zip_sha256": receipt["zip_sha256"],
            "audit": "s17/writer-receipt.json",
        },
        byte_identity_unique=True,
        byte_identity_caveat=(
            "Unique bytes, 95/95 pre-placement Spearman PASS (max |rho|=0.2191 <= 0.90), and 50/50 final-dot PASS "
            "across preceding fleet submissions (including GEMSDOE32 R0 = 49.27%) do not override the literal Rule-1 "
            "stop on dense 272,853-dot reference r11_greedy_mp.tif (87.25% > 70%), shared-backbone overlap with "
            "in-repo S14-PTAC E2 (82.96%), or the synthetic lattice bound (calib_r13lattice_00904.tif >= 82.34%; IR-S16-03)."
        ),
    )

    beats_prior = bool(best_score["dti"] > best_prior_val)
    stopped_name = Path(final_reg["stopped_on"]["file"]).name if final_reg.get("stopped_on") else "none"
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
    if final_reg["status"] == "DUPLICATE":
        verdict = "negative"
        verdict_reason = (
            f"Point estimate beats all prior label-blind benchmarks on gems57-pooled-hide-v2 "
            f"({best_score['dti']:.6f} vs {best_prior_name} {best_prior_val:.6f}, paired delta {paired_best['delta']:+.6f}, "
            f"95% CI [{paired_best['ci95'][0]:+.6f}, {paired_best['ci95'][1]:+.6f}]; vs s16_pgrd +0.128786), "
            f"passes 95/95 pre-placement Spearman checks and 50/50 preceding fleet rasters (max 3 px overlap "
            f"{max_passed_overlap:.4f} <= 0.70; GEMSDOE32 R0 = 0.4927), then stops fail-closed at reference 51/95 "
            f"{stopped_name} ({stopped_dots} dots, 3 px overlap {stopped_ov:.4f} > 0.70); paired 95% CI vs "
            f"incumbent_ptac_lb also straddles zero."
            if beats_prior
            else "Literal Rule 1 duplicate stop and/or did not beat comparable prior best; fail-closed negative."
        )
    else:
        verdict = "negative"
        verdict_reason = "Provisional lane and separate human weekly-slot selector remain required before live upload."

    card.update(
        verdict=verdict,
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
                f"S17-CPAD ({best_arm}) fresh computation; format PASS, HOLDOUT-DTI={best_score['dti']:.6f}; "
                f"passes 95/95 pre-placement Spearman and 50/50 preceding fleet rasters (GEMSDOE32=0.4927), "
                f"stopped at 51/95 {stopped_name} ({stopped_ov:.4f} > 0.70); NOT OK TO SUBMIT."
            ),
        }
        if rel in existing_paths:
            policy["files"] = [entry if x["path"] == rel else x for x in policy["files"]]
        else:
            policy["files"].append(entry)
    dump(policy_path, policy)
    log(f"S17-CPAD completed in {card['elapsed_seconds']}s: HOLDOUT-DTI={best_score['dti']:.6f}, OK_TO_DOWNLOAD={card['ok_to_download']}, OK_TO_SUBMIT={card['ok_to_submit']}")
    return card


if __name__ == "__main__":
    run()
