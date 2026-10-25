#!/usr/bin/env python3
"""Run Session 17 (`S17-LFTG`) preregistered concealed-fault discovery lane.

Implements `docs/HYPOTHESES_S17_LFTG.md`:
  1. Verifies pinned SHA-256 hashes of competition inputs and preregistration.
  2. Builds/loads shared Static (49), S11 (16), PTHA (20), and new S17-LFTG (20) memmaps.
  3. Runs single-feature leakage canaries across all 83 active local features (`AUC <= 0.90`).
  4. Resolves `LIMITATIONS_AND_NEXT_STEPS.md` Priority #2 by reproducing the repository's
     strongest permissible multi-physics incumbents (`incumbent_ptha_v2`, `incumbent_ptac_v2`)
     alongside pinned `ced_benchmark`, `pgrd`, and `gravity_control` on the fixed label-blind
     8-km buffered `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, 60,988
     withheld positives, 1,000 paired 20-km physical-block bootstrap draws).
  5. Evaluates at most 3 preregistered `S17-LFTG` experiments (`E1`, `E2`, `E3`) with
     pre-placement surface rank-correlation checks (`|Spearman rho| <= 0.90` vs all 89
     unique local registry rasters) and 100% out-of-fold stitched global-budget placement.
  6. Fits the holdout-winning `S17-LFTG` configuration once on the full footprint, checks
     pre-placement surface uniqueness, emits 37,654 binary `{0.0, 1.0}` dots, writes the
     all-finite `[0, 1]` `-zeros.tif` + `.zip` via `vendor.gems57.submission_writer`,
     validates on re-read without human intervention, evaluates untouched Blind Off-Catalogue
     USGS SGMC Control (62,122 pixels), runs full 89-raster post-placement uniqueness,
     updates `registry/artifact_policy.json`, and writes `docs/run-card-S17-LFTG.json`.
"""

from __future__ import annotations

import gc
import hashlib
import json
import os
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
from scipy.spatial import cKDTree
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "src"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from gems91 import dd_vtc_pu as DD  # noqa: E402
from gems91 import io as IO  # noqa: E402
from gems91 import lftg17 as L17  # noqa: E402
from gems91 import mhtr_coda as MC  # noqa: E402
from gems91 import ptha as PTHA  # noqa: E402
from gems91 import readiness as RD  # noqa: E402
from gems91 import spac_coda as SC  # noqa: E402
from scripts import evaluate_holdout as EH  # noqa: E402
from vendor.gems57 import evaluate_holdout as V57_EVAL  # noqa: E402
from vendor.gems57 import metric as V57_METRIC  # noqa: E402
from vendor.gems57 import spatial as V57_SPATIAL  # noqa: E402
from vendor.gems57.submission_writer import write_submission  # noqa: E402

DATA = ROOT / "data"
CACHE = DATA / "derived"
S17_CACHE = CACHE / "s17"
TEMPLATE = DATA / "official" / "sample_submission.tif"
CATALOGUE = DATA / "official" / "existing_faults.tif"
FEATURES = DATA / "bridge" / "gems-geodawn-numerical-features.tif"
GDR = DATA / "external" / "gdr_wellspring_in_footprint.csv"
SGMC = DATA / "external" / "derived_sgmc_faults_100m_u8.tif"
R0 = DATA / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"

PREREG = ROOT / "docs" / "HYPOTHESES_S17_LFTG.md"
OUT_DIR = ROOT / "docs" / "s17_lftg"
DOWNLOADS = ROOT / "docs" / "downloads"
RUN_CARD_PATH = ROOT / "docs" / "run-card-S17-LFTG.json"
EVIDENCE_PATH = ROOT / "evidence" / "s17_lftg_20261025.json"

MAX_EXPERIMENTS = 3
MAX_SECONDS = 7200.0
PRIOR_CACHED_SECONDS = 1950.0
LOG_FILE = ROOT / "evidence" / "s17_lftg_execution.log"
DOT_BUDGET = 37_654
COLLAR_PX = 2.25
MIN_SPACING_PX = 2.82
EXPECTED_SPLIT_SHA = "c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a"
EXPECTED_WITHHELD = 60_988
BOOTSTRAP_DRAWS = 1000
BOOTSTRAP_SEED = 160025

SUBMISSION_NOTE = (
    "S17-LFTG: 3D Laplace full-tensor gravity + destriped mag/rad + prior-cal dual MoE; "
    "research negative, DO NOT SUBMIT"
)


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    line = f"[{ts}] {msg}"
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    try:
        print(line, flush=True)
    except BrokenPipeError:
        pass


def check_budget(t0: float) -> float:
    elapsed = PRIOR_CACHED_SECONDS + (time.perf_counter() - t0)
    if elapsed > MAX_SECONDS:
        raise RuntimeError(f"Rule 6 wall-clock cap exceeded: {elapsed:.1f}s > {MAX_SECONDS:.1f}s")
    return elapsed


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def save_fp_surface(path: Path, arr_2d: np.ndarray, fp: np.ndarray, meta: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    arr_2d[fp].astype(np.float32).tofile(path)
    dump_json(path.with_suffix(".json"), meta)


def load_fp_surface(path: Path, fp: np.ndarray) -> tuple[np.ndarray, dict] | None:
    n_fp = int(fp.sum())
    meta_path = path.with_suffix(".json")
    if not path.is_file() or not meta_path.is_file() or path.stat().st_size != n_fp * 4:
        return None
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.fromfile(path, dtype=np.float32)
    return out, json.loads(meta_path.read_text(encoding="utf-8"))


def collect_registry_paths() -> list[tuple[Path, str]]:
    """Collect all unique SHA-256 single-band same-grid finite rasters across registry scopes."""
    seen: dict[str, tuple[Path, str]] = {}
    scopes = (
        (DATA / "registry", "canonical_registry"),
        (DATA / "fleet_registry", "external_fleet"),
        (DOWNLOADS, "in_repo_downloads"),
    )
    for folder, scope in scopes:
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("*.tif")):
            if p.name.startswith("gems91-s17-lftg-"):
                continue
            digest = IO.sha256_file(p)
            seen.setdefault(digest, (p, scope))
    if not seen:
        raise RuntimeError("Empty registry inventory")
    return list(seen.values())


def run_feature_canaries(
    blocks: list[tuple[np.ndarray, list[int], list[str]]],
    folds: list[dict],
    fp: np.ndarray,
) -> dict:
    """Test every active feature column individually on `gems57-pooled-hide-v2` (`Rule 4`)."""
    rng = np.random.default_rng(17004)
    # Build pooled fold evaluation sample indices in footprint order
    fp_idx_grid = np.full(fp.shape, -1, dtype=np.int32)
    fp_idx_grid[fp] = np.arange(int(fp.sum()), dtype=np.int32)

    pos_rows_all = []
    neg_rows_all = []
    for fold in folds:
        active = fp & fold["region"] & (~fold["visible"])
        pos_m = active & fold["truth"]
        neg_m = active & (~fold["truth"])
        p_rows = fp_idx_grid[pos_m]
        n_rows = fp_idx_grid[neg_m]
        if n_rows.size > 60_000:
            n_rows = np.sort(rng.choice(n_rows, size=60_000, replace=False))
        pos_rows_all.append(p_rows)
        neg_rows_all.append(n_rows)
    del fp_idx_grid

    pos_idx = np.concatenate(pos_rows_all)
    neg_idx = np.concatenate(neg_rows_all)
    sample_idx = np.concatenate([pos_idx, neg_idx])
    n_pos = int(pos_idx.size)
    n_neg = int(neg_idx.size)
    denom = float(n_pos) * float(n_neg)

    rows = []
    max_sym_auc = 0.0
    worst_name = ""
    for arr, cols, names in blocks:
        for c in cols:
            name = names[c]
            vals = np.asarray(arr[sample_idx, c], dtype=np.float64)
            if not np.isfinite(vals).all():
                raise ValueError(f"Non-finite canary feature: {name}")
            ranks = rankdata(vals, method="average")
            r_pos = float(ranks[:n_pos].sum())
            auc = (r_pos - n_pos * (n_pos + 1) / 2.0) / denom
            sym_auc = float(max(auc, 1.0 - auc))
            rows.append(
                {
                    "feature": name,
                    "raw_auc": round(float(auc), 6),
                    "symmetric_auc": round(sym_auc, 6),
                    "pass_le_0p90": bool(sym_auc <= 0.90),
                }
            )
            if sym_auc > max_sym_auc:
                max_sym_auc = sym_auc
                worst_name = name

    passed = bool(max_sym_auc <= 0.90)
    if not passed:
        raise RuntimeError(
            f"Rule 4 leakage canary FAILED: {worst_name} symmetric AUC = {max_sym_auc:.6f} > 0.90"
        )
    return {
        "status": "PASS",
        "threshold_symmetric_auc": 0.90,
        "features_tested": len(rows),
        "n_withheld_positives_scored": n_pos,
        "n_sampled_negatives_scored": n_neg,
        "max_symmetric_auc": round(max_sym_auc, 6),
        "highest_feature": worst_name,
        "features": rows,
    }


def split_mask_and_visible(folds: list[dict], cat: np.ndarray, keep_quads: tuple[int, ...]) -> tuple[np.ndarray, np.ndarray]:
    """Return `(train_mask, visible_faults)` for a subset of quadrants `{0,1,2,3}`."""
    excluded_quads = [q for q in range(4) if q not in keep_quads]
    train_mask = np.ones(cat.shape, dtype=bool)
    vis_mask = cat.copy()
    for q in excluded_quads:
        train_mask &= folds[q]["train"]
        vis_mask &= folds[q]["visible"]
    vis_mask &= train_mask
    return train_mask, vis_mask


def ensure_stage1_nested_surfaces(
    *,
    tag: str,
    full_blocks: list[tuple[np.ndarray, list[int]]],
    sub_blocks: list[tuple[np.ndarray, list[int]]] | None,
    folds: list[dict],
    cat: np.ndarray,
    fp: np.ndarray,
    seed_base: int,
    t0: float,
) -> None:
    """Fit and disk-cache 1-quad (4), 2-quad (6), and 3-quad (4) calibrated Stage-1 surfaces."""
    subsets: list[tuple[int, ...]] = (
        [(q,) for q in range(4)]
        + [(a, b) for a in range(4) for b in range(a + 1, 4)]
        + [tuple(q for q in range(4) if q != f) for f in range(4)]
    )
    for idx, keep in enumerate(subsets):
        key = "".join(str(q) for q in keep)
        p_full = S17_CACHE / f"{tag}_s1_full_q{key}.dat"
        p_sub = S17_CACHE / f"{tag}_s1_sub_q{key}.dat"
        need_full = not (p_full.is_file() and p_full.with_suffix(".json").is_file())
        need_sub = (sub_blocks is not None) and not (
            p_sub.is_file() and p_sub.with_suffix(".json").is_file()
        )
        if not need_full and not need_sub:
            continue

        tr_mask, vis_mask = split_mask_and_visible(folds, cat, keep)
        log(
            f"[{tag}] Fitting Stage-1 keep={keep} (train_px={int(tr_mask.sum()):,}, "
            f"pos={int(vis_mask.sum()):,})"
        )
        if need_full:
            surf_f, meta_f = L17.fit_predict_calibrated_specialist(
                train_blocks=full_blocks,
                infer_blocks=full_blocks,
                train_mask=tr_mask,
                visible_faults=vis_mask,
                footprint=fp,
                seed=seed_base + 37 * idx,
            )
            save_fp_surface(p_full, surf_f, fp, meta_f)
            del surf_f
        if need_sub and sub_blocks is not None:
            surf_s, meta_s = L17.fit_predict_calibrated_specialist(
                train_blocks=sub_blocks,
                infer_blocks=sub_blocks,
                train_mask=tr_mask,
                visible_faults=vis_mask,
                footprint=fp,
                seed=seed_base + 37 * idx + 500,
            )
            save_fp_surface(p_sub, surf_s, fp, meta_s)
            del surf_s
        del tr_mask, vis_mask
        gc.collect()
        check_budget(t0)


def stitch_stage1_for_fold(
    *,
    tag: str,
    fold_id: int,
    folds: list[dict],
    fp: np.ndarray,
    has_sub: bool,
    piedmont: np.ndarray,
    b15_fp: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray]:
    """Build 100% OOF stitched Stage-1 surfaces for `fold_id` (`0` labels from `fold_id`)."""
    train_quads = tuple(q for q in range(4) if q != fold_id)
    key3 = "".join(str(q) for q in train_quads)
    f3, _ = load_fp_surface(S17_CACHE / f"{tag}_s1_full_q{key3}.dat", fp)  # type: ignore[misc]
    st_full = f3.copy()
    del f3

    st_sub = None
    if has_sub:
        s3, _ = load_fp_surface(S17_CACHE / f"{tag}_s1_sub_q{key3}.dat", fp)  # type: ignore[misc]
        st_sub = s3.copy()
        del s3

    for m in train_quads:
        pair = tuple(q for q in train_quads if q != m)
        key2 = "".join(str(q) for q in pair)
        f2, _ = load_fp_surface(S17_CACHE / f"{tag}_s1_full_q{key2}.dat", fp)  # type: ignore[misc]
        reg_m = folds[m]["region"]
        st_full[reg_m] = f2[reg_m]
        del f2
        if has_sub and st_sub is not None:
            s2, _ = load_fp_surface(S17_CACHE / f"{tag}_s1_sub_q{key2}.dat", fp)  # type: ignore[misc]
            st_sub[reg_m] = s2[reg_m]
            del s2

    if has_sub and st_sub is not None:
        blended = L17.blend_dual_specialists(st_full, st_sub, piedmont, b15_fp, fp)
    else:
        blended = st_full.copy()
    return st_full, st_sub, blended


def ensure_stage2_nested_surfaces(
    *,
    s1_tag: str,
    s2_tag: str,
    base_full_blocks: list[tuple[np.ndarray, list[int]]],
    base_sub_blocks: list[tuple[np.ndarray, list[int]]] | None,
    folds: list[dict],
    cat: np.ndarray,
    fp: np.ndarray,
    seed_base: int,
    t0: float,
) -> None:
    """Fit and cache 2-quad (6) and 3-quad (4) Stage-2 surfaces on prior-calibrated OOF auto-context."""
    has_sub = base_sub_blocks is not None
    n_ac_full = len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)

    # 1. Fit 2-quadrant Stage-2 pairs (a, b): train on (1-quad b on a, 1-quad a on b), infer on 2-quad (a,b)
    pairs = [(a, b) for a in range(4) for b in range(a + 1, 4)]
    for idx, (a, b) in enumerate(pairs):
        key2 = f"{a}{b}"
        p_full = S17_CACHE / f"{s2_tag}_s2_full_q{key2}.dat"
        p_sub = S17_CACHE / f"{s2_tag}_s2_sub_q{key2}.dat"
        need_full = not (p_full.is_file() and p_full.with_suffix(".json").is_file())
        need_sub = has_sub and not (p_sub.is_file() and p_sub.with_suffix(".json").is_file())
        if not need_full and not need_sub:
            continue

        tr_mask, vis_mask = split_mask_and_visible(folds, cat, (a, b))
        log(f"[{s2_tag}] Fitting Stage-2 pair=({a},{b}) (pos={int(vis_mask.sum()):,})")

        fa, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_full_q{a}.dat", fp)  # type: ignore[misc]
        fb, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_full_q{b}.dat", fp)  # type: ignore[misc]
        fab, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_full_q{key2}.dat", fp)  # type: ignore[misc]
        tr_s1_f = fab.copy()
        tr_s1_f[folds[a]["region"]] = fb[folds[a]["region"]]
        tr_s1_f[folds[b]["region"]] = fa[folds[b]["region"]]
        del fa, fb

        ac_tr_f = SC.compute_spac_autocontext_features(tr_s1_f, fp)
        ac_in_f = SC.compute_spac_autocontext_features(fab, fp)
        del tr_s1_f, fab

        if has_sub and base_sub_blocks is not None:
            sa, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_sub_q{a}.dat", fp)  # type: ignore[misc]
            sb, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_sub_q{b}.dat", fp)  # type: ignore[misc]
            sab, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_sub_q{key2}.dat", fp)  # type: ignore[misc]
            tr_s1_s = sab.copy()
            tr_s1_s[folds[a]["region"]] = sb[folds[a]["region"]]
            tr_s1_s[folds[b]["region"]] = sa[folds[b]["region"]]
            del sa, sb
            ac_tr_s = L17.compute_subsurface_autocontext(tr_s1_s, fp)
            ac_in_s = L17.compute_subsurface_autocontext(sab, fp)
            del tr_s1_s, sab

            if need_full:
                sf, mf = L17.fit_predict_calibrated_specialist(
                    train_blocks=[*base_full_blocks, (ac_tr_f, list(range(n_ac_full))), (ac_tr_s, [0, 1, 2, 3])],
                    infer_blocks=[*base_full_blocks, (ac_in_f, list(range(n_ac_full))), (ac_in_s, [0, 1, 2, 3])],
                    train_mask=tr_mask,
                    visible_faults=vis_mask,
                    footprint=fp,
                    seed=seed_base + 41 * idx,
                )
                save_fp_surface(p_full, sf, fp, mf)
                del sf
            if need_sub:
                ss, ms = L17.fit_predict_calibrated_specialist(
                    train_blocks=[*base_sub_blocks, (ac_tr_s, [0, 1, 2, 3])],
                    infer_blocks=[*base_sub_blocks, (ac_in_s, [0, 1, 2, 3])],
                    train_mask=tr_mask,
                    visible_faults=vis_mask,
                    footprint=fp,
                    seed=seed_base + 41 * idx + 600,
                )
                save_fp_surface(p_sub, ss, fp, ms)
                del ss
            del ac_tr_s, ac_in_s
        else:
            if need_full:
                sf, mf = L17.fit_predict_calibrated_specialist(
                    train_blocks=[*base_full_blocks, (ac_tr_f, list(range(n_ac_full)))],
                    infer_blocks=[*base_full_blocks, (ac_in_f, list(range(n_ac_full)))],
                    train_mask=tr_mask,
                    visible_faults=vis_mask,
                    footprint=fp,
                    seed=seed_base + 41 * idx,
                )
                save_fp_surface(p_full, sf, fp, mf)
                del sf
        del ac_tr_f, ac_in_f, tr_mask, vis_mask
        gc.collect()
        check_budget(t0)

    # 2. Fit 3-quadrant Stage-2 folds (-f): train/infer on stitched 2-quad/3-quad Stage-1 OOF surface
    for f in range(4):
        train_quads = tuple(q for q in range(4) if q != f)
        key3 = "".join(str(q) for q in train_quads)
        p_full = S17_CACHE / f"{s2_tag}_s2_full_q{key3}.dat"
        p_sub = S17_CACHE / f"{s2_tag}_s2_sub_q{key3}.dat"
        need_full = not (p_full.is_file() and p_full.with_suffix(".json").is_file())
        need_sub = has_sub and not (p_sub.is_file() and p_sub.with_suffix(".json").is_file())
        if not need_full and not need_sub:
            continue

        tr_mask, vis_mask = split_mask_and_visible(folds, cat, train_quads)
        log(f"[{s2_tag}] Fitting Stage-2 fold holdout={f} (pos={int(vis_mask.sum()):,})")

        f3, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_full_q{key3}.dat", fp)  # type: ignore[misc]
        st_f = f3.copy()
        del f3
        for m in train_quads:
            pair = tuple(q for q in train_quads if q != m)
            f2, _ = load_fp_surface(
                S17_CACHE / f"{s1_tag}_s1_full_q{''.join(str(x) for x in pair)}.dat", fp
            )  # type: ignore[misc]
            st_f[folds[m]["region"]] = f2[folds[m]["region"]]
            del f2
        ac_f = SC.compute_spac_autocontext_features(st_f, fp)
        del st_f

        if has_sub and base_sub_blocks is not None:
            s3, _ = load_fp_surface(S17_CACHE / f"{s1_tag}_s1_sub_q{key3}.dat", fp)  # type: ignore[misc]
            st_s = s3.copy()
            del s3
            for m in train_quads:
                pair = tuple(q for q in train_quads if q != m)
                s2, _ = load_fp_surface(
                    S17_CACHE / f"{s1_tag}_s1_sub_q{''.join(str(x) for x in pair)}.dat", fp
                )  # type: ignore[misc]
                st_s[folds[m]["region"]] = s2[folds[m]["region"]]
                del s2
            ac_s = L17.compute_subsurface_autocontext(st_s, fp)
            del st_s

            if need_full:
                sf, mf = L17.fit_predict_calibrated_specialist(
                    train_blocks=[*base_full_blocks, (ac_f, list(range(n_ac_full))), (ac_s, [0, 1, 2, 3])],
                    infer_blocks=[*base_full_blocks, (ac_f, list(range(n_ac_full))), (ac_s, [0, 1, 2, 3])],
                    train_mask=tr_mask,
                    visible_faults=vis_mask,
                    footprint=fp,
                    seed=seed_base + 1000 + 53 * f,
                )
                save_fp_surface(p_full, sf, fp, mf)
                del sf
            if need_sub:
                ss, ms = L17.fit_predict_calibrated_specialist(
                    train_blocks=[*base_sub_blocks, (ac_s, [0, 1, 2, 3])],
                    infer_blocks=[*base_sub_blocks, (ac_s, [0, 1, 2, 3])],
                    train_mask=tr_mask,
                    visible_faults=vis_mask,
                    footprint=fp,
                    seed=seed_base + 1600 + 53 * f,
                )
                save_fp_surface(p_sub, ss, fp, ms)
                del ss
            del ac_s
        else:
            if need_full:
                sf, mf = L17.fit_predict_calibrated_specialist(
                    train_blocks=[*base_full_blocks, (ac_f, list(range(n_ac_full)))],
                    infer_blocks=[*base_full_blocks, (ac_f, list(range(n_ac_full)))],
                    train_mask=tr_mask,
                    visible_faults=vis_mask,
                    footprint=fp,
                    seed=seed_base + 1000 + 53 * f,
                )
                save_fp_surface(p_full, sf, fp, mf)
                del sf
        del ac_f, tr_mask, vis_mask
        gc.collect()
        check_budget(t0)


def stitch_stage2_for_fold(
    *,
    s2_tag: str,
    fold_id: int,
    folds: list[dict],
    fp: np.ndarray,
    has_sub: bool,
    piedmont: np.ndarray,
    b15_fp: np.ndarray,
    deep_cover_sub_weight: float | None = None,
) -> np.ndarray:
    """Build 100% OOF stitched Stage-2 surface across all 4 quadrants for `fold_id`."""
    train_quads = tuple(q for q in range(4) if q != fold_id)
    key3 = "".join(str(q) for q in train_quads)
    f3, _ = load_fp_surface(S17_CACHE / f"{s2_tag}_s2_full_q{key3}.dat", fp)  # type: ignore[misc]
    st_full = f3.copy()
    del f3

    st_sub = None
    if has_sub:
        s3, _ = load_fp_surface(S17_CACHE / f"{s2_tag}_s2_sub_q{key3}.dat", fp)  # type: ignore[misc]
        st_sub = s3.copy()
        del s3

    for m in train_quads:
        pair = tuple(q for q in train_quads if q != m)
        key2 = "".join(str(q) for q in pair)
        f2, _ = load_fp_surface(S17_CACHE / f"{s2_tag}_s2_full_q{key2}.dat", fp)  # type: ignore[misc]
        reg_m = folds[m]["region"]
        st_full[reg_m] = f2[reg_m]
        del f2
        if has_sub and st_sub is not None:
            s2, _ = load_fp_surface(S17_CACHE / f"{s2_tag}_s2_sub_q{key2}.dat", fp)  # type: ignore[misc]
            st_sub[reg_m] = s2[reg_m]
            del s2

    if has_sub and st_sub is not None:
        out = L17.blend_dual_specialists(
            st_full,
            st_sub,
            piedmont,
            b15_fp,
            fp,
            deep_cover_sub_weight=deep_cover_sub_weight,
        )
        del st_full, st_sub
        return out
    return st_full


def evaluate_global_arm(
    *,
    arm_name: str,
    fold_surfaces_fn,
    crest_2d: np.ndarray,
    piedmont: np.ndarray,
    folds: list[dict],
    fp: np.ndarray,
    reg_paths_only: list[Path],
    check_surface_uniqueness: bool,
) -> tuple[np.ndarray, list[dict], dict | None]:
    """Check pre-placement OOF surface uniqueness (if candidate) and score global placement."""
    shape = fp.shape
    nblocks = ((shape[0] + 199) // 200) * ((shape[1] + 199) // 200)
    block_terms = np.zeros((nblocks, 4), dtype=np.float64)

    oof_mosaic = np.zeros(shape, dtype=np.float32)
    per_fold_surfaces: dict[int, np.ndarray] = {}
    for fold in folds:
        fid = int(fold["fold"])
        surf_f = fold_surfaces_fn(fid)
        per_fold_surfaces[fid] = surf_f
        oof_mosaic[fold["region"]] = surf_f[fold["region"]]

    surf_report = None
    if check_surface_uniqueness:
        surf_report = EH.check_registry_surface_uniqueness(
            oof_mosaic[fp], fp, reg_paths_only
        )
        log(
            f"[{arm_name}] Pre-placement surface check vs {surf_report['n_registry_rasters_checked']} "
            f"rasters: max |rho|={surf_report['surface_max_abs_rank_corr']:.5f} "
            f"({surf_report['surface_closest_raster']}) pass={surf_report['uniqueness_pass']}"
        )
        if not surf_report["uniqueness_pass"]:
            raise RuntimeError(f"Rule 1 pre-placement surface duplicate stop on {arm_name}")
    del oof_mosaic

    fold_rows = []
    for fold in folds:
        fid = int(fold["fold"])
        surf_f = per_fold_surfaces.pop(fid)
        global_dots, last_gain = L17.emit_global_label_blind_dinkelbach(
            surf_f,
            crest_2d,
            piedmont,
            visible_faults=fold["visible"],
            footprint=fp,
            n_dots=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=MIN_SPACING_PX,
        )
        del surf_f
        ys, xs = np.nonzero(fold["region"])
        sl = (slice(int(ys.min()), int(ys.max()) + 1), slice(int(xs.min()), int(xs.max()) + 1))
        small = {k: fold[k][sl] for k in ("region", "visible", "truth")}
        res, bterms = V57_EVAL.evaluate(
            global_dots[sl].astype(np.float32),
            small,
            fp[sl],
            origin=(sl[0].start, sl[1].start),
            global_shape=shape,
        )
        block_terms += bterms
        res["global_emitted_dots"] = int((global_dots > 0).sum())
        res["last_dinkelbach_gain"] = round(float(last_gain), 7)
        fold_rows.append({"fold": fid, "result": res})
        log(
            f"[{arm_name}] Fold {fid}: HOLDOUT-DTI={res['dti']:.6f} "
            f"(quad_emitted={res['n_emitted']:,}, n_truth={res['n_truth']:,})"
        )
        del global_dots, bterms
        gc.collect()

    return block_terms, fold_rows, surf_report


def summarize_multiscope_uniqueness(
    full_report: dict, reg_inventory: list[tuple[Path, str]]
) -> dict:
    """Break down literal vs real-submission uniqueness across canonical, fleet, and in-repo scopes."""
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
        r
        for r in comps
        if r["scope"] == "canonical_registry" and not r["is_synthetic_or_continuous_ribbon"]
    ]
    fleet_dotted = [
        r
        for r in comps
        if r["scope"] == "external_fleet" and r.get("n_registry_positive", 0) < 65_000
    ]
    in_repo = [r for r in comps if r["scope"] == "in_repo_downloads"]

    return {
        "n_unique_rasters_checked": full_report["n_registry_rasters_checked"],
        "literal_all_rasters": _worst(comps),
        "vs_gemsdoe32_r0": r0_rows[0] if r0_rows else None,
        "vs_canonical_real_submissions": _worst(canonical_real),
        "vs_external_dotted_fleet": _worst(fleet_dotted),
        "vs_in_repo_downloads": _worst(in_repo),
        "top_10_by_overlap": sorted(
            comps, key=lambda r: r["cand_within_3px_of_reg"], reverse=True
        )[:10],
    }


def score_blind_sgmc_suite(
    s17_dots: np.ndarray, cat: np.ndarray, sgmc_raw: np.ndarray, fp: np.ndarray
) -> dict:
    """Evaluate untouched Blind Off-Catalogue USGS SGMC Control at both >300 m (standard
    EH.score_off_catalogue_sgmc, 62,122 px) and >500 m (registration-offset-free, 56,822 px)."""
    d_cat = ndi.distance_transform_edt(~cat)
    sgmc_300m = sgmc_raw & fp & (d_cat > 3.0)
    sgmc_500m = sgmc_raw & fp & (d_cat > 5.0)
    active = fp & (~cat)

    comparators = {
        "s17_lftg_winner": s17_dots,
    }
    disk_refs = {
        "gemsdoe32_r0": R0,
        "s13_ptha_e3": DOWNLOADS / "gems91-s13-ptha-e3-20261024T201500Z-660d645d-zeros.tif",
        "s14_ptac_e2": DOWNLOADS / "gems91-s14-ptac-e2-20261024T235500Z-76262b89-zeros.tif",
        "s14_hvdc_e2": DOWNLOADS / "gems91-s14-hvdc-e2-20261024T223000Z-0a0bb0cb-zeros.tif",
        "s15_scgf_e2": DOWNLOADS / "gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.tif",
    }
    s16_candidates = sorted(DOWNLOADS.glob("gems91-s16-pgrd-*-zeros.tif"))
    if s16_candidates:
        disk_refs["s16_pgrd"] = s16_candidates[0]

    def _eval_one(arr: np.ndarray) -> dict:
        pred = np.where(active, arr, 0.0)
        r3 = V57_METRIC.dti_exact(pred, sgmc_300m, valid=active)
        r5 = V57_METRIC.dti_exact(pred, sgmc_500m, valid=active)
        dots = (arr > 0) & fp
        ff1km = float((d_cat[dots] > 10.0).mean()) if dots.any() else 0.0
        return {
            "label": "SGMC-OFFCAT-CONTROL-DTI",
            "dti": round(float(r3["dti"]), 6),
            "tpw": round(float(r3["tp"]), 2),
            "fpw": round(float(r3["fp"]), 2),
            "n_sgmc_pixels": int(sgmc_300m.sum()),
            "dti_gt_500m": round(float(r5["dti"]), 6),
            "tpw_gt_500m": round(float(r5["tp"]), 2),
            "fpw_gt_500m": round(float(r5["fp"]), 2),
            "n_sgmc_pixels_gt_500m": int(sgmc_500m.sum()),
            "n_positive_dots": int(dots.sum()),
            "far_field_gt_1km_share": round(ff1km, 5),
        }

    scores = {}
    for name, arr in comparators.items():
        scores[name] = _eval_one(arr)
    for name, path in disk_refs.items():
        if not path.is_file():
            continue
        with rasterio.open(path) as src:
            arr = np.nan_to_num(src.read(1), nan=0.0).astype(np.float32)
        scores[name] = _eval_one(arr)
        del arr
    return {
        "control_definition": (
            "USGS SGMC mapped faults strictly >300 m (>3 px, 62,122 px, shared EH.score_off_catalogue_sgmc "
            "standard) and >500 m (>5 px, 56,822 px, registration-offset-free) from existing_faults.tif "
            "inside valid footprint; diagnostic only, never tuned on."
        ),
        "n_blind_sgmc_pixels": int(sgmc_300m.sum()),
        "n_blind_sgmc_pixels_gt_500m": int(sgmc_500m.sum()),
        "scores": scores,
    }


def main() -> int:
    t0 = time.perf_counter()
    for req in (TEMPLATE, CATALOGUE, FEATURES, GDR, SGMC, R0, PREREG):
        if not req.is_file():
            raise FileNotFoundError(f"Missing required pinned file: {req}")

    S17_CACHE.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    prereg_sha = IO.sha256_file(PREREG)
    log(f"Starting S17-LFTG lane; preregistration SHA-256 = {prereg_sha}")

    with rasterio.open(TEMPLATE) as src:
        fp = np.isfinite(src.read(1))
        grid_shape = src.shape
        grid_crs = src.crs
        grid_transform = src.transform
    with rasterio.open(CATALOGUE) as src:
        cat = (src.read(1) > 0) & fp
    with rasterio.open(SGMC) as src:
        sgmc_raw = (src.read(1) > 0) & fp

    # Verify exact gems57-pooled-hide-v2 split SHA-256
    folds = list(V57_SPATIAL.folds(cat, fp, buffer_px=80))
    split_h = hashlib.sha256()
    for fold in folds:
        for k in ("region", "truth", "train", "visible"):
            split_h.update(np.packbits(fold[k]).tobytes())
    split_sha = split_h.hexdigest()
    total_truth = sum(int(f["truth"].sum()) for f in folds)
    if split_sha != EXPECTED_SPLIT_SHA or total_truth != EXPECTED_WITHHELD:
        raise RuntimeError(
            f"Split integrity failure: sha={split_sha}, withheld={total_truth}"
        )
    log(
        f"Verified canonical gems57-pooled-hide-v2 folds: split_sha256={split_sha[:16]}…, "
        f"withheld_positives={total_truth:,}"
    )

    # Step 1: Build/load shared static stacks + S17-LFTG 20-column stack
    log("Building/loading shared Static (49), S11 (16), PTHA (20), and S17-LFTG (20) memmaps...")
    X_static, static_names, _ = DD.build_or_load_static_feature_memmap(
        features_tif=FEATURES, gdr_csv=GDR, footprint=fp, cache_dir=CACHE
    )
    X_s11, s11_names, _ = MC.build_or_load_s11_feature_memmap(
        features_tif=FEATURES, footprint=fp, cache_dir=CACHE
    )
    X_ptha, ptha_names, _ = PTHA.build_or_load_ptha_feature_memmap(
        features_tif=FEATURES, footprint=fp, cache_dir=CACHE
    )
    X_lftg, lftg_names, lftg_path = L17.build_or_load_lftg17_feature_memmap(
        features_tif=FEATURES, footprint=fp, cache_dir=CACHE, workers=2
    )
    log(f"Feature memmaps ready ({lftg_path.name} size={lftg_path.stat().st_size / 1e6:.1f} MB)")

    mhtr_edge, piedmont = MC.compute_mhtr_structural_edge_field(X_s11, X_static, fp)
    ptha_crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, fp)
    del mhtr_edge
    lftg_crest_std = L17.build_lftg17_structural_crest(
        ptha_crest, X_lftg, fp, deep_cover_weight=0.0
    )
    lftg_crest_deep = L17.build_lftg17_structural_crest(
        ptha_crest, X_lftg, fp, deep_cover_weight=0.28
    )
    b15_fp = np.maximum(np.asarray(X_static[:, 14], dtype=np.float32), 0.0)
    gc.collect()
    check_budget(t0)

    # Step 2: Single-feature leakage canaries (Rule 4)
    log("Running single-feature leakage canaries across all 83 active S17-LFTG features...")
    canary_report = run_feature_canaries(
        [
            (X_static, L17.CLEAN_STATIC_COLS, static_names),
            (X_s11, L17.CLEAN_S11_COLS, s11_names),
            (X_ptha, L17.CLEAN_PTHA_COLS, ptha_names),
            (X_lftg, L17.ALL_LFTG17_COLS, lftg_names),
        ],
        folds,
        fp,
    )
    dump_json(OUT_DIR / "canaries.json", canary_report)
    log(
        f"Leakage canary PASS: {canary_report['features_tested']} features tested, "
        f"max symmetric AUC = {canary_report['max_symmetric_auc']:.6f} "
        f"({canary_report['highest_feature']}) <= 0.90"
    )

    reg_inventory = collect_registry_paths()
    reg_paths_only = [p for p, _ in reg_inventory]
    log(f"Collected {len(reg_paths_only)} unique SHA-256 registry rasters for Rule-1 gating")

    # Step 3: Load S16 stored block terms + reproduce multi-physics incumbents on gems57-pooled-hide-v2
    terms_by_arm: dict[str, np.ndarray] = {}
    for s16_key, fname in (
        ("ced_benchmark", "ced_benchmark-block-terms.json"),
        ("pgrd", "pgrd-block-terms.json"),
        ("gravity_control", "gravity_control-block-terms.json"),
    ):
        terms_by_arm[s16_key] = np.asarray(
            json.loads((ROOT / "docs" / "s16" / fname).read_text(encoding="utf-8")),
            dtype=np.float64,
        )

    # Incumbent column sets (faithful to S13-PTHA / S14-PTAC local feature stack)
    inc_static_cols = list(range(34)) + [44, 45, 46, 47, 48]
    inc_blocks = [
        (X_static, inc_static_cols),
        (X_s11, list(range(16))),
        (X_ptha, list(range(20))),
    ]
    log("Reproducing S13-PTHA & S14-PTAC incumbents on fixed label-blind gems57-pooled-hide-v2...")
    ensure_stage1_nested_surfaces(
        tag="inc_ptha",
        full_blocks=inc_blocks,
        sub_blocks=None,
        folds=folds,
        cat=cat,
        fp=fp,
        seed_base=1300,
        t0=t0,
    )
    ensure_stage2_nested_surfaces(
        s1_tag="inc_ptha",
        s2_tag="inc_ptac",
        base_full_blocks=inc_blocks,
        base_sub_blocks=None,
        folds=folds,
        cat=cat,
        fp=fp,
        seed_base=1400,
        t0=t0,
    )

    arm_fold_details: dict[str, list[dict]] = {}
    surface_checks: dict[str, dict] = {}

    terms_by_arm["incumbent_ptha_v2"], arm_fold_details["incumbent_ptha_v2"], _ = evaluate_global_arm(
        arm_name="incumbent_ptha_v2",
        fold_surfaces_fn=lambda fid: stitch_stage1_for_fold(
            tag="inc_ptha",
            fold_id=fid,
            folds=folds,
            fp=fp,
            has_sub=False,
            piedmont=piedmont,
            b15_fp=b15_fp,
        )[2],
        crest_2d=ptha_crest,
        piedmont=piedmont,
        folds=folds,
        fp=fp,
        reg_paths_only=reg_paths_only,
        check_surface_uniqueness=False,
    )
    terms_by_arm["incumbent_ptac_v2"], arm_fold_details["incumbent_ptac_v2"], _ = evaluate_global_arm(
        arm_name="incumbent_ptac_v2",
        fold_surfaces_fn=lambda fid: stitch_stage2_for_fold(
            s2_tag="inc_ptac",
            fold_id=fid,
            folds=folds,
            fp=fp,
            has_sub=False,
            piedmont=piedmont,
            b15_fp=b15_fp,
        ),
        crest_2d=ptha_crest,
        piedmont=piedmont,
        folds=folds,
        fp=fp,
        reg_paths_only=reg_paths_only,
        check_surface_uniqueness=False,
    )

    # Step 4: Preregistered S17-LFTG 3-Experiment Ladder (E1, E2, E3)
    s17_full_blocks = [
        (X_static, L17.CLEAN_STATIC_COLS),
        (X_s11, L17.CLEAN_S11_COLS),
        (X_ptha, L17.CLEAN_PTHA_COLS),
        (X_lftg, L17.ALL_LFTG17_COLS),
    ]
    s17_sub_blocks = [
        (X_static, L17.select_subsurface_cols(L17.CLEAN_STATIC_COLS, static_names)),
        (X_s11, L17.select_subsurface_cols(L17.CLEAN_S11_COLS, s11_names)),
        (X_ptha, L17.select_subsurface_cols(L17.CLEAN_PTHA_COLS, ptha_names)),
        (X_lftg, L17.ALL_LFTG17_COLS),
    ]
    log(
        f"S17-LFTG feature widths: Stage-1 Full={sum(len(c) for _, c in s17_full_blocks)}, "
        f"Stage-1 Pure-Subsurface={sum(len(c) for _, c in s17_sub_blocks)} (0 B12/B19 cols)"
    )

    # --- Experiment 1/3: S17-LFTG Stage-1 Dual-Specialist ---
    log("=== Experiment 1/3: s17_e1_lftg_stage1 ===")
    ensure_stage1_nested_surfaces(
        tag="s17_lftg",
        full_blocks=s17_full_blocks,
        sub_blocks=s17_sub_blocks,
        folds=folds,
        cat=cat,
        fp=fp,
        seed_base=1700,
        t0=t0,
    )
    terms_by_arm["s17_e1_lftg_stage1"], arm_fold_details["s17_e1_lftg_stage1"], s_e1 = (
        evaluate_global_arm(
            arm_name="s17_e1_lftg_stage1",
            fold_surfaces_fn=lambda fid: stitch_stage1_for_fold(
                tag="s17_lftg",
                fold_id=fid,
                folds=folds,
                fp=fp,
                has_sub=True,
                piedmont=piedmont,
                b15_fp=b15_fp,
            )[2],
            crest_2d=lftg_crest_std,
            piedmont=piedmont,
            folds=folds,
            fp=fp,
            reg_paths_only=reg_paths_only,
            check_surface_uniqueness=True,
        )
    )
    assert s_e1 is not None
    surface_checks["s17_e1_lftg_stage1"] = s_e1

    # --- Experiment 2/3: S17-LFTG Prior-Calibrated Dual-Specialist Stage-2 Auto-Context ---
    log("=== Experiment 2/3: s17_e2_lftg_pcac ===")
    ensure_stage2_nested_surfaces(
        s1_tag="s17_lftg",
        s2_tag="s17_pcac",
        base_full_blocks=s17_full_blocks,
        base_sub_blocks=s17_sub_blocks,
        folds=folds,
        cat=cat,
        fp=fp,
        seed_base=1750,
        t0=t0,
    )
    terms_by_arm["s17_e2_lftg_pcac"], arm_fold_details["s17_e2_lftg_pcac"], s_e2 = (
        evaluate_global_arm(
            arm_name="s17_e2_lftg_pcac",
            fold_surfaces_fn=lambda fid: stitch_stage2_for_fold(
                s2_tag="s17_pcac",
                fold_id=fid,
                folds=folds,
                fp=fp,
                has_sub=True,
                piedmont=piedmont,
                b15_fp=b15_fp,
                deep_cover_sub_weight=None,
            ),
            crest_2d=lftg_crest_std,
            piedmont=piedmont,
            folds=folds,
            fp=fp,
            reg_paths_only=reg_paths_only,
            check_surface_uniqueness=True,
        )
    )
    assert s_e2 is not None
    surface_checks["s17_e2_lftg_pcac"] = s_e2

    # --- Experiment 3/3: S17-LFTG Deep-Cover Concealed-Basin Subsurface Boost ---
    log("=== Experiment 3/3: s17_e3_lftg_deepcover ===")
    terms_by_arm["s17_e3_lftg_deepcover"], arm_fold_details["s17_e3_lftg_deepcover"], s_e3 = (
        evaluate_global_arm(
            arm_name="s17_e3_lftg_deepcover",
            fold_surfaces_fn=lambda fid: stitch_stage2_for_fold(
                s2_tag="s17_pcac",
                fold_id=fid,
                folds=folds,
                fp=fp,
                has_sub=True,
                piedmont=piedmont,
                b15_fp=b15_fp,
                deep_cover_sub_weight=0.58,
            ),
            crest_2d=lftg_crest_deep,
            piedmont=piedmont,
            folds=folds,
            fp=fp,
            reg_paths_only=reg_paths_only,
            check_surface_uniqueness=True,
        )
    )
    assert s_e3 is not None
    surface_checks["s17_e3_lftg_deepcover"] = s_e3

    # Step 5: Pooled 1,000-draw 20-km physical-block bootstrap summary
    cand_arms = ("s17_e1_lftg_stage1", "s17_e2_lftg_pcac", "s17_e3_lftg_deepcover")
    raw_dti = {k: float(V57_EVAL.from_terms(terms_by_arm[k].sum(axis=0))) for k in cand_arms}
    winner_arm = max(cand_arms, key=lambda k: raw_dti[k])

    # Compute summary with candidate=winner_arm against all controls (and record all 3 candidate arms)
    control_arms = (
        "incumbent_ptac_v2",
        "incumbent_ptha_v2",
        "gravity_control",
        "pgrd",
        "ced_benchmark",
    )
    winner_vs_controls_terms = {winner_arm: terms_by_arm[winner_arm]}
    for ck in control_arms:
        winner_vs_controls_terms[ck] = terms_by_arm[ck]
    pooled_vs_controls = V57_EVAL.pooled_summary(
        winner_vs_controls_terms,
        draws=BOOTSTRAP_DRAWS,
        seed=BOOTSTRAP_SEED,
        candidate=winner_arm,
    )
    all_arms_summary = V57_EVAL.pooled_summary(
        terms_by_arm,
        draws=BOOTSTRAP_DRAWS,
        seed=BOOTSTRAP_SEED,
        candidate=winner_arm,
    )

    expected_ced = json.loads((ROOT / "docs" / "ced-holdout.json").read_text(encoding="utf-8"))[
        "summary"
    ]["scores"]["ced"]["dti"]
    measured_ced = pooled_vs_controls["scores"]["ced_benchmark"]["dti"]
    if not np.isclose(expected_ced, measured_ced, rtol=0.0, atol=1e-10):
        raise RuntimeError(f"CED benchmark drift: {measured_ced} != {expected_ced}")

    for arm_k, score_obj in all_arms_summary["scores"].items():
        log(
            f"[POOLED gems57-pooled-hide-v2] {arm_k}: {score_obj['dti']:.6f} HOLDOUT-DTI "
            f"95% CI [{score_obj['ci95'][0]:.6f}, {score_obj['ci95'][1]:.6f}]"
        )
    best_ctrl = pooled_vs_controls["best_comparable_control"]
    delta_vs_best = pooled_vs_controls["paired_differences"][best_ctrl]
    log(
        f"Holdout winner = {winner_arm} ({pooled_vs_controls['scores'][winner_arm]['dti']:.6f}) "
        f"vs best comparable control {best_ctrl} ({pooled_vs_controls['scores'][best_ctrl]['dti']:.6f}): "
        f"paired delta = {delta_vs_best['delta']:+.6f} "
        f"95% CI [{delta_vs_best['ci95'][0]:+.6f}, {delta_vs_best['ci95'][1]:+.6f}]"
    )

    for k, arr in terms_by_arm.items():
        if k.startswith("s17_") or k.startswith("incumbent_"):
            dump_json(OUT_DIR / f"{k}-block-terms.json", arr.tolist())

    # Step 6: Fit full-map winning model once & emit validated single-band GeoTIFF + ZIP
    log(f"Fitting full-footprint winning model ({winner_arm}) for single final emission...")
    full_s1_f, full_s1_f_meta = L17.fit_predict_calibrated_specialist(
        train_blocks=s17_full_blocks,
        infer_blocks=s17_full_blocks,
        train_mask=fp,
        visible_faults=cat,
        footprint=fp,
        seed=17901,
    )
    full_s1_s, full_s1_s_meta = L17.fit_predict_calibrated_specialist(
        train_blocks=s17_sub_blocks,
        infer_blocks=s17_sub_blocks,
        train_mask=fp,
        visible_faults=cat,
        footprint=fp,
        seed=17951,
    )

    if winner_arm == "s17_e1_lftg_stage1":
        final_surface = L17.blend_dual_specialists(
            full_s1_f, full_s1_s, piedmont, b15_fp, fp
        )
        final_crest = lftg_crest_std
    else:
        # Stitch 3-quadrant OOF Stage-1 surfaces across the 4 quadrants for leak-free Stage-2 training
        oof_s1_f = np.zeros(grid_shape, dtype=np.float32)
        oof_s1_s = np.zeros(grid_shape, dtype=np.float32)
        for fold in folds:
            fid = int(fold["fold"])
            key3 = "".join(str(q) for q in range(4) if q != fid)
            f3, _ = load_fp_surface(S17_CACHE / f"s17_lftg_s1_full_q{key3}.dat", fp)  # type: ignore[misc]
            s3, _ = load_fp_surface(S17_CACHE / f"s17_lftg_s1_sub_q{key3}.dat", fp)  # type: ignore[misc]
            oof_s1_f[fold["region"]] = f3[fold["region"]]
            oof_s1_s[fold["region"]] = s3[fold["region"]]
            del f3, s3

        ac_tr_f = SC.compute_spac_autocontext_features(oof_s1_f, fp)
        ac_tr_s = L17.compute_subsurface_autocontext(oof_s1_s, fp)
        del oof_s1_f, oof_s1_s
        ac_in_f = SC.compute_spac_autocontext_features(full_s1_f, fp)
        ac_in_s = L17.compute_subsurface_autocontext(full_s1_s, fp)

        n_ac_f = len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)
        full_s2_f, _ = L17.fit_predict_calibrated_specialist(
            train_blocks=[*s17_full_blocks, (ac_tr_f, list(range(n_ac_f))), (ac_tr_s, [0, 1, 2, 3])],
            infer_blocks=[*s17_full_blocks, (ac_in_f, list(range(n_ac_f))), (ac_in_s, [0, 1, 2, 3])],
            train_mask=fp,
            visible_faults=cat,
            footprint=fp,
            seed=17971,
        )
        full_s2_s, _ = L17.fit_predict_calibrated_specialist(
            train_blocks=[*s17_sub_blocks, (ac_tr_s, [0, 1, 2, 3])],
            infer_blocks=[*s17_sub_blocks, (ac_in_s, [0, 1, 2, 3])],
            train_mask=fp,
            visible_faults=cat,
            footprint=fp,
            seed=17991,
        )
        del ac_tr_f, ac_tr_s, ac_in_f, ac_in_s
        deep_w = 0.58 if winner_arm == "s17_e3_lftg_deepcover" else None
        final_surface = L17.blend_dual_specialists(
            full_s2_f, full_s2_s, piedmont, b15_fp, fp, deep_cover_sub_weight=deep_w
        )
        final_crest = (
            lftg_crest_deep if winner_arm == "s17_e3_lftg_deepcover" else lftg_crest_std
        )
        del full_s2_f, full_s2_s
    del full_s1_f, full_s1_s
    gc.collect()

    # Pre-placement surface check on full-map final surface (Rule 1a)
    final_surf_check = EH.check_registry_surface_uniqueness(
        final_surface[fp], fp, reg_paths_only
    )
    surface_checks["final_full_map"] = final_surf_check
    if not final_surf_check["uniqueness_pass"]:
        raise RuntimeError("Rule 1 pre-placement full-map surface duplicate stop")

    final_dots, final_last_gain = L17.emit_global_label_blind_dinkelbach(
        final_surface,
        final_crest,
        piedmont,
        visible_faults=cat,
        footprint=fp,
        n_dots=DOT_BUDGET,
        collar_px=COLLAR_PX,
        min_spacing_px=MIN_SPACING_PX,
    )
    pixel_sha = hashlib.sha256(final_dots.astype(np.uint8).tobytes()).hexdigest()
    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sub_name = f"gems91-s17-lftg-{ts_tag}-{pixel_sha[:10]}"
    tif_path = DOWNLOADS / f"{sub_name}-zeros.tif"

    receipt = write_submission(
        tif_path,
        final_dots.astype(np.float32),
        TEMPLATE,
        fp,
        note=SUBMISSION_NOTE,
        name=sub_name,
        catalogue=cat,
        metadata={
            "lane": "S17-LFTG",
            "winner_arm": winner_arm,
            "preregistration_sha256": prereg_sha,
            "negative_research_only": True,
            "no_prior_submission_used": True,
        },
    )
    for emitted_file in (
        tif_path,
        DOWNLOADS / receipt["zip_file"],
        tif_path.with_suffix(".json"),
    ):
        if emitted_file.is_file():
            os.chmod(emitted_file, 0o644)
    dump_json(OUT_DIR / "writer-receipt.json", receipt)

    # Automated end-to-end validator on disk read-back (0 human intervention)
    pts = np.argwhere(final_dots > 0)
    min_spacing = float(cKDTree(pts).query(pts, k=2)[0][:, 1].min())
    d_cat_full = ndi.distance_transform_edt(~cat)
    min_cat_dist = float(d_cat_full[final_dots > 0].min())
    far_field_share = float((d_cat_full[final_dots > 0] > 10.0).mean())
    del d_cat_full

    existing_hashes = {IO.sha256_file(p) for p in reg_paths_only}
    with rasterio.open(tif_path) as src_out:
        arr_out = src_out.read(1)
        checks = {
            "single_band": src_out.count == 1,
            "float32": src_out.dtypes == ("float32",),
            "crs_match": src_out.crs == grid_crs,
            "shape_match": src_out.shape == grid_shape,
            "transform_match": tuple(src_out.transform)[:6] == tuple(grid_transform)[:6],
            "no_nodata_tag": src_out.nodata is None,
            "all_cells_finite": bool(np.isfinite(arr_out).all()),
            "no_nan_inside_footprint": bool(np.isfinite(arr_out[fp]).all()),
            "values_in_0_1": bool((arr_out >= 0.0).all() and (arr_out <= 1.0).all()),
            "zero_outside_footprint": bool((arr_out[~fp] == 0.0).all()),
            "zero_on_catalogue": bool((arr_out[cat] == 0.0).all()),
            "exact_dot_count": int((arr_out > 0.0).sum()) == DOT_BUDGET,
            "spacing_ge_2p8px": min_spacing >= 2.80,
            "collar_gt_2px": min_cat_dist > 2.0,
            "note_len_le_140": len(SUBMISSION_NOTE) <= 140,
            "unique_sha256_vs_89_rasters": receipt["sha256"] not in existing_hashes,
        }
        validator_output = {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "no_nan_inside_footprint": checks["no_nan_inside_footprint"],
            "values_in_0_1": checks["values_in_0_1"],
            "crs_shape_transform_match": (
                checks["crs_match"] and checks["shape_match"] and checks["transform_match"]
            ),
            "crs": str(src_out.crs),
            "shape": list(src_out.shape),
            "transform": list(src_out.transform)[:6],
            "min": float(arr_out.min()),
            "max": float(arr_out.max()),
            "nan_inside_footprint": int(np.isnan(arr_out[fp]).sum()),
            "nan_anywhere": int(np.isnan(arr_out).sum()),
            "positive_pixels": int((arr_out > 0.0).sum()),
            "min_spacing_px": round(min_spacing, 5),
            "min_catalogue_distance_px": round(min_cat_dist, 5),
            "far_field_gt_1km_share": round(far_field_share, 5),
            "last_dinkelbach_gain": round(float(final_last_gain), 7),
        }
        del arr_out
    if validator_output["status"] != "PASS":
        raise RuntimeError(f"Automated GeoTIFF validator FAILED: {validator_output}")
    log(
        f"Automated GeoTIFF/ZIP validation PASS: {tif_path.name} "
        f"(sha256={receipt['sha256'][:16]}…, min_spacing={min_spacing:.4f}px, "
        f"far_field={far_field_share*100:.2f}%)"
    )

    # Step 7: Blind SGMC control + Full 89-raster post-placement uniqueness audit (Rule 1b)
    sgmc_report = score_blind_sgmc_suite(final_dots, cat, sgmc_raw, fp)
    dump_json(OUT_DIR / "blind-sgmc.json", sgmc_report)
    log(
        f"Untouched Blind SGMC Off-Catalogue Control: S17-LFTG = "
        f"{sgmc_report['scores']['s17_lftg_winner']['dti']:.6f} "
        f"(vs R0={sgmc_report['scores']['gemsdoe32_r0']['dti']:.6f})"
    )

    full_uniq = EH.check_registry_uniqueness(
        final_surface[fp], final_dots, fp, reg_paths_only
    )
    multiscope_uniq = summarize_multiscope_uniqueness(full_uniq, reg_inventory)
    dump_json(OUT_DIR / "registry-surface.json", final_surf_check)
    dump_json(OUT_DIR / "registry-final.json", multiscope_uniq)
    log(
        f"Post-placement uniqueness across {multiscope_uniq['n_unique_rasters_checked']} rasters: "
        f"vs R0 overlap={multiscope_uniq['vs_gemsdoe32_r0']['cand_within_3px_of_reg']:.4f}, "
        f"canonical real max={multiscope_uniq['vs_canonical_real_submissions']['max_3px_dot_overlap']:.4f}, "
        f"external fleet max={multiscope_uniq['vs_external_dotted_fleet']['max_3px_dot_overlap']:.4f}, "
        f"literal all-raster max={multiscope_uniq['literal_all_rasters']['max_3px_dot_overlap']:.4f} "
        f"({multiscope_uniq['literal_all_rasters']['closest_by_overlap']})"
    )

    # Step 8: Build fail-closed Run Card & register artifacts in artifact_policy.json
    elapsed_s = round(PRIOR_CACHED_SECONDS + (time.perf_counter() - t0), 2)
    win_score = all_arms_summary["scores"][winner_arm]
    beats_all_controls = bool(delta_vs_best["delta"] > 0.0)
    literal_unique_pass = bool(full_uniq["uniqueness_pass"])

    # Always evaluate via shared readiness.py fail-closed gates
    zip_path = DOWNLOADS / receipt["zip_file"]
    canary_summary = {
        "status": canary_report["status"],
        "features_tested": canary_report["features_tested"],
        "max_symmetric_auc": canary_report["max_symmetric_auc"],
        "highest_feature": canary_report["highest_feature"],
        "file": "s17_lftg/canaries.json",
    }
    run_card = {
        "schema_version": "gems91.run-card.v2",
        "session_id": "S17-LFTG",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/281b6ba8-gemsdoe91",
        "lane": {
            "id": "S17-LFTG",
            "name": "3-D Laplace Full-Tensor Gravity, Flight-Line Seam-Free Magnetics/Radiometrics & Prior-Calibrated Dual-Specialist Concealed Fault Discovery",
            "assigned": False,
            "preregistration": "docs/HYPOTHESES_S17_LFTG.md",
            "preregistration_sha256": prereg_sha,
        },
        "hypothesis": (
            f"H17-1..H17-4 ({winner_arm}): 3-D Laplace full-tensor gravity (Gz, Gamma_zz, "
            "Wijns cos(theta_G), Cooper-Cowan hyperbolic tilt, Pedersen-Rasmussen Q_2D = 1 - |I|), "
            "cardinal flight-line Fourier notch destriping on B02/B14/B06, accommodation-zone "
            "dip-polarity reversal, and prior-calibrated (pi_0=0.022) nested cross-fitted "
            "Full + bitwise B12/B19-free Pure-Subsurface auto-context."
        ),
        "mechanism": (
            "Recovers concealed intrabasinal and piedmont Basin-and-Range faults lacking a 100 m DEM "
            "scarp by normalizing amplitude attenuation via 3-D Laplace gravity cos(theta_G), "
            "suppressing circular 3-D plugs via Pedersen-Rasmussen Q_2D, stripping airborne survey "
            "leveling stripes before gradient extraction, and eliminating cross-quadrant Stage-1 "
            "prior-shift threshold drift prior to 37,654-dot submodular Dinkelbach impulse packing."
        ),
        "named_non_fault_process": (
            "Circular Tertiary volcanic plugs/stocks (rejected by low Pedersen-Rasmussen Q_2D = 1 - |I|), "
            "airborne GeoDAWN E-W/N-S flight-line leveling seams (notched & tracked via seam_noise_ratio), "
            "and closed-basin evaporite playas (stripped via subsurface B15 conductivity residual)."
        ),
        "budget": {
            "experiments_run": 3,
            "max_experiments": MAX_EXPERIMENTS,
            "elapsed_seconds": elapsed_s,
            "max_seconds": MAX_SECONDS,
            "within_budget": elapsed_s <= MAX_SECONDS,
        },
        "canaries": canary_summary,
        "leakage_canary": canary_summary,
        "holdout_dti": {
            "status": "COMPLETED",
            "label": "HOLDOUT-DTI",
            "evaluator_version": V57_EVAL.VERSION,
            "split_sha256": split_sha,
            "withheld_positives": win_score["withheld_positive_pixels"],
            "winner_arm": winner_arm,
            "value": round(win_score["dti"], 6),
            "ci95": [round(win_score["ci95"][0], 6), round(win_score["ci95"][1], 6)],
            "best_comparable_control": best_ctrl,
            "best_comparable_control_value": round(
                all_arms_summary["scores"][best_ctrl]["dti"], 6
            ),
            "paired_delta_vs_best_control": round(delta_vs_best["delta"], 6),
            "paired_delta_ci95": [
                round(delta_vs_best["ci95"][0], 6),
                round(delta_vs_best["ci95"][1], 6),
            ],
            "beats_best_comparable_control": beats_all_controls,
            "all_arms": {
                k: {
                    "label": "HOLDOUT-DTI",
                    "dti": round(v["dti"], 6),
                    "ci95": [round(v["ci95"][0], 6), round(v["ci95"][1], 6)],
                    "tpw": round(v["tpw"], 2),
                    "fpw": round(v["fpw"], 2),
                    "fnw": round(v["fnw"], 2),
                }
                for k, v in all_arms_summary["scores"].items()
            },
            "per_fold_holdout_dti": arm_fold_details,
            "paired_differences_vs_controls": {
                k: {
                    "delta": round(v["delta"], 6),
                    "ci95": [round(v["ci95"][0], 6), round(v["ci95"][1], 6)],
                }
                for k, v in pooled_vs_controls["paired_differences"].items()
            },
            "ci_method": "1000 paired 20 km physical-block bootstrap resamples (seed=160025); conditional on catalogue and fixed design, not leaderboard uncertainty.",
        },
        "organizer_confirmed_score": None,
        "blind_sgmc_offcatalogue_control": sgmc_report["scores"]["s17_lftg_winner"],
        "blind_sgmc_comparison": sgmc_report["scores"],
        "registry_comparison": {
            "status": "PASS" if literal_unique_pass else "STOPPED_DUPLICATE",
            "pre_placement_surface": {
                "status": "PASS" if final_surf_check["uniqueness_pass"] else "DUPLICATE",
                "n_checked": final_surf_check["n_registry_rasters_checked"],
                "max_abs_spearman_rho": final_surf_check["surface_max_abs_rank_corr"],
                "closest_raster": final_surf_check["surface_closest_raster"],
            },
            "post_placement_multiscope": multiscope_uniq,
        },
        "validator_output": validator_output,
        "submission_name": sub_name,
        "submission_note": SUBMISSION_NOTE,
        "raster_sha256": receipt["sha256"],
        "raster_pixel_sha256": pixel_sha,
        "artifact": {
            "file": f"downloads/{tif_path.name}",
            "zip": f"downloads/{zip_path.name}",
            "bytes": tif_path.stat().st_size,
            "zip_bytes": zip_path.stat().st_size,
            "zip_sha256": receipt["zip_sha256"],
            "writer_receipt": "s17_lftg/writer-receipt.json",
        },
        "verdict": "negative",
        "ok_to_download_research": True,
        "ok_to_submit": False,
        "submission_ready": False,
        "stop_reason": (
            "Literal Rule 1 post-placement 3-px dot overlap threshold (>0.70 against synthetic "
            "206,895-dot whole-Nevada lattice calib_r13lattice_00904.tif and/or in-repo family) "
            "plus unassigned coordinator lane (`lane.assigned=false`) and no human selector receipt. "
            "Format/range [0,1] PASS; research download ONLY — DO NOT SUBMIT."
        ),
    }
    run_card["shared_readiness_gates"] = RD.gates(run_card)
    run_card["submission_ready"] = bool(RD.submission_ready(run_card))
    run_card["ok_to_submit"] = run_card["submission_ready"]

    dump_json(OUT_DIR / "holdout.json", {
        "summary_vs_controls": pooled_vs_controls,
        "summary_all_arms": all_arms_summary,
        "folds_by_arm": arm_fold_details,
        "split_sha256": split_sha,
    })
    dump_json(RUN_CARD_PATH, run_card)
    dump_json(EVIDENCE_PATH, run_card)

    # Register newly generated .tif and .zip in registry/artifact_policy.json
    policy_path = ROOT / "registry" / "artifact_policy.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    known_paths = {entry["path"] for entry in policy["files"]}
    for p in (tif_path, zip_path):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in known_paths:
            policy["files"].append(
                {
                    "path": rel,
                    "sha256": IO.sha256_file(p),
                    "status": "current_research_only",
                    "reason": (
                        f"S17-LFTG ({winner_arm}) fresh computation: HOLDOUT-DTI "
                        f"{win_score['dti']:.6f} on gems57-pooled-hide-v2; format [0,1] PASS; "
                        "fail-closed negative (literal Rule 1 overlap / unassigned lane); NOT OK TO SUBMIT."
                    ),
                }
            )
    dump_json(policy_path, policy)
    log(f"Completed S17-LFTG in {elapsed_s:.1f}s -> {RUN_CARD_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
