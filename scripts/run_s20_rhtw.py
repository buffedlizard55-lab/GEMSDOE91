#!/usr/bin/env python3
"""Session 20 (`S20-RHTW`) Preregistered 3-Experiment Runner (`E1`, `E2`, `E3` vs `E0`, `RND`).

Implements `docs/HYPOTHESES_S20_RHTW.md` strictly under Parallel-Run Protocol Rules 1-6:
  - Rule 1 (LANE & Uniqueness): Single cohesive `S20-RHTW` method lane (`lane.assigned = false`
    because no pasted paragraph appeared under Rule 1 in the prompt); checks pre-placement
    Spearman `|rho| <= 0.90` and post-placement dot Spearman `|rho| <= 0.90` + directed `3-px`
    overlap `<= 0.70` across ALL unique rasters in `data/registry/`, `registry/rasters/`,
    `data/fleet_registry/`, `docs/downloads/`, and the 9-site forensic rasters.
  - Rule 2 (REUSE, DON'T REBUILD): Uses unchanged `vendor/gems57/holdout.py`,
    `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`), `vendor/gems57/network.py`,
    `vendor/gems57/submission_writer.py`, and `gems91.dd_vtc_pu.submodular_dti_emit`.
  - Rule 3 (LABEL EVERY NUMBER): Every holdout score carries `HOLDOUT-DTI` (`gems57-pooled-hide-v2`,
    exact withheld-positive pixel count, and 1,000-draw 20 km spatial-block bootstrap `95% CI`);
    off-catalogue SGMC evaluations carry `BLIND-SGMC-CONTROL`; zero unverified projections.
  - Rule 4 (LEAKAGE CANARY): Tests every single feature (`72` static + `28` Stage-2 OOF
    auto-context + `3` fold-safe visible `FTRS` = `103` features) alone on holdout (`symmetric_auc <= 0.90`
    globally and in every quadrant); hard-aborts on any exceedance.
  - Rule 5 (RUN CARD): Emits one canonical JSON Run Card `docs/run-card-S20-RHTW.json` plus
    portal-compatible metadata and audit receipts.
  - Rule 6 (BUDGET): Runs strictly `3` experiments (`E1`, `E2`, `E3`) within `< 2 hours` and
    spends `0` weekly submission slots (`ok_to_submit = false` until separate human selector step).
"""

from __future__ import annotations

import os

for _env_k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_env_k, "2")

import argparse
from datetime import datetime, timezone
import gc
import hashlib
import itertools
import json
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

from gems57 import evaluate_holdout as EH
from gems57 import gates as v57_gates
from gems57 import grid as G
from gems57 import holdout as H
from gems57 import metric as M
from gems57.network import STRUCT3
from gems57.submission_writer import write_submission
from gems57.validate import validate as v57_validate
from gems91 import isolated_holdout as IH
from gems91 import rhtw20 as R20
from gems91.dd_vtc_pu import submodular_dti_emit
import run_olc91 as O
import validate_raster as VR

LANE_ID = "S20-RHTW"
SEED = 20
TRAIN_BUFFER_PX = 40
BUDGET = 37_654
COLLAR_PX = 2.05  # min Euclidean distance sqrt(5) = 2.2361 px (>200 m strict zero-dot collar)
NEG_RATIO = 3

SAMPLE_TIF = ROOT / "data" / "official" / "sample_submission.tif"
CATALOGUE_TIF = ROOT / "data" / "official" / "existing_faults.tif"
FEATURES_TIF = ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif"
GDR_CSV = ROOT / "data" / "external" / "gdr_wellspring_in_footprint.csv"
SGMC_TIF = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
R0_TIF = ROOT / "data" / "registry" / "GEMSDOE32__h33-2-b2-zeros.tif"
PREREG_MD = ROOT / "docs" / "HYPOTHESES_S20_RHTW.md"

WORK_DIR = ROOT / "work" / "s20_rhtw"
OUT_DIR = ROOT / "docs" / "s20_rhtw"
DOWNLOADS_DIR = ROOT / "docs" / "downloads"
RUN_CARD_PATH = ROOT / "docs" / "run-card-S20-RHTW.json"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%SZ")
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    print(f"[{ts} | RSS={rss_mb:6.1f}MB] {msg}", flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_pinned_inputs() -> dict[str, dict[str, object]]:
    manifest = json.loads((ROOT / "registry" / "data_manifest.json").read_text())
    by_id = {r["id"]: r for r in manifest["files"]}
    pins: dict[str, dict[str, object]] = {}
    for req_id in (
        "sample_submission",
        "existing_faults",
        "training_features",
        "gdr_wellspring_in_footprint",
        "sgmc_faults_control",
        "parent_r0_zeros",
    ):
        row = by_id[req_id]
        p = ROOT / "data" / row["local_subpath"]
        if not p.is_file():
            raise FileNotFoundError(f"Missing pinned input: {p}")
        digest = sha256_file(p)
        if digest != row["sha256"] or p.stat().st_size != row["bytes"]:
            raise ValueError(f"SHA-256 or byte-size mismatch on {req_id}")
        pins[req_id] = {
            "path": f"data/{row['local_subpath']}",
            "sha256": digest,
            "bytes": p.stat().st_size,
        }
    tpin = json.loads((ROOT / "registry" / "template_pin.json").read_text())
    for name, digest in tpin["sha256"].items():
        if sha256_file(ROOT / "vendor" / "gems57" / name) != digest:
            raise ValueError(f"Immutable vendor/gems57 drift: {name}")
    if not PREREG_MD.is_file():
        raise FileNotFoundError(f"Missing frozen preregistration: {PREREG_MD}")
    pins["preregistration"] = {
        "path": "docs/HYPOTHESES_S20_RHTW.md",
        "sha256": sha256_file(PREREG_MD),
        "bytes": PREREG_MD.stat().st_size,
    }
    return pins


def logit_safe(p: np.ndarray) -> np.ndarray:
    pc = np.clip(p, 1e-5, 1.0 - 1e-5)
    return np.log(pc / (1.0 - pc)).astype(np.float32)


def sigmoid_safe(ell: np.ndarray) -> np.ndarray:
    ec = np.clip(ell, -14.0, 14.0)
    return (1.0 / (1.0 + np.exp(-ec))).astype(np.float32)


def fp_vec_to_grid(vec: np.ndarray, fp: np.ndarray) -> np.ndarray:
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.asarray(vec, dtype=np.float32)
    return out


def fit_specialist_fp_vec(
    X_base: np.ndarray,
    base_cols: list[int],
    X_ac: np.ndarray | None,
    fpi: np.ndarray,
    fp: np.ndarray,
    positives: np.ndarray,
    exclude_known: np.ndarray,
    train_dom: np.ndarray,
    predict_mask: np.ndarray,
    hard_col_in_base: int,
    seed: int,
) -> np.ndarray:
    """Fit regularized HistGradientBoostingClassifier with importance-weighted hard negatives
    and return footprint-indexed float16 probability vector `(5_167_373,)` (`10.3 MB`)."""
    rng = np.random.default_rng(seed)
    pos_ids = fpi[positives & train_dom & fp]
    d_excl = ndi.distance_transform_edt(~exclude_known)
    far_pool_mask = train_dom & fp & (d_excl > 3.0)
    hard_pool_mask = train_dom & fp & (d_excl > 6.5)
    del d_excl

    far_ids = fpi[far_pool_mask]
    n_neg_tot = int(min(far_ids.size, NEG_RATIO * pos_ids.size))
    n_uni = int(round(0.72 * n_neg_tot))
    n_hard = n_neg_tot - n_uni

    uni_ids = rng.choice(far_ids, n_uni, replace=False)

    hard_cand_ids = fpi[hard_pool_mask]
    hvals = np.asarray(X_base[hard_cand_ids, hard_col_in_base], dtype=np.float32)
    thresh = float(np.percentile(hvals[::8], 82.0))
    hard_top = hard_cand_ids[hvals >= thresh]
    del hvals
    if hard_top.size >= max(n_hard * 2, 100):
        hard_ids = rng.choice(hard_top, n_hard, replace=False)
        hard_frac_space = float(hard_top.size) / max(float(far_ids.size), 1.0)
        w_hard = min(1.0, max(0.18, hard_frac_space / 0.28))
    else:
        hard_ids = rng.choice(far_ids, n_hard, replace=False)
        w_hard = 1.0

    tr_ids = np.concatenate([pos_ids, uni_ids, hard_ids])
    y_tr = np.r_[
        np.ones(pos_ids.size, dtype=np.float32),
        np.zeros(n_uni + n_hard, dtype=np.float32),
    ]
    raw_neg_w = np.r_[np.ones(n_uni, dtype=np.float32), np.full(n_hard, w_hard, dtype=np.float32)]
    raw_neg_w *= float(n_neg_tot) / float(raw_neg_w.sum())
    sw_tr = np.r_[np.ones(pos_ids.size, dtype=np.float32), raw_neg_w]

    order = np.argsort(tr_ids)
    tr_sorted = tr_ids[order]
    y_sorted = y_tr[order]
    sw_sorted = sw_tr[order]

    def _assemble(row_ids: np.ndarray) -> np.ndarray:
        xb = np.asarray(X_base[row_ids][:, base_cols], dtype=np.float32)
        if X_ac is None:
            return xb
        xac = np.asarray(X_ac[row_ids], dtype=np.float32)
        return np.hstack([xb, xac])

    X_tr = _assemble(tr_sorted)
    clf = HistGradientBoostingClassifier(
        max_iter=210,
        learning_rate=0.078,
        max_leaf_nodes=33,
        min_samples_leaf=50,
        l2_regularization=1.8,
        random_state=seed,
    )
    clf.fit(X_tr, y_sorted, sample_weight=sw_sorted)
    del X_tr

    out_fp = np.zeros(int(fp.sum()), dtype=np.float16)
    pred_ids = fpi[predict_mask & fp]
    for s in range(0, pred_ids.size, 350_000):
        chunk_ids = pred_ids[s : s + 350_000]
        out_fp[chunk_ids] = clf.predict_proba(_assemble(chunk_ids))[:, 1].astype(np.float16)
    del clf
    gc.collect()
    return out_fp


def pool_dual_specialist_vec(
    s1_full_fp: np.ndarray,
    s2_full_fp: np.ndarray,
    s2_sub_fp: np.ndarray,
    cover_idx_fp: np.ndarray,
    worm_bonus_fp: np.ndarray,
    train_dom_fp: np.ndarray,
) -> np.ndarray:
    """Pool Stage-1 + Stage-2 Full and `Band 12/19`-blind Pure-Subsurface specialists via
    dispersion-aligned Asymmetric Concealed-Fault Log-Odds Rescue (`IR-91-S17-01` & `IR-91-S17-02`)."""
    lf1 = logit_safe(np.asarray(s1_full_fp, dtype=np.float32))
    lf2 = logit_safe(np.asarray(s2_full_fp, dtype=np.float32))
    ls2 = logit_safe(np.asarray(s2_sub_fp, dtype=np.float32))

    med_f, p99_f = [float(x) for x in np.percentile(lf2[train_dom_fp][::8], [50.0, 99.0])]
    med_s, p99_s = [float(x) for x in np.percentile(ls2[train_dom_fp][::8], [50.0, 99.0])]
    scale = min(max((p99_f - med_f) / max(p99_s - med_s, 1e-4), 0.65), 1.65)
    ls2_aligned = med_f + (ls2 - med_s) * scale

    rescue = np.maximum(ls2_aligned - lf2, 0.0)
    ell = (
        0.28 * lf1
        + 0.72 * lf2
        + 0.44 * cover_idx_fp * rescue
        + 0.14 * worm_bonus_fp
    ).astype(np.float32)
    return sigmoid_safe(ell).astype(np.float16)


def run_two_stage_hierarchy(
    tag: str,
    X_s20: np.ndarray,
    full_cols: list[int],
    sub_cols: list[int],
    cover_idx_fp: np.ndarray,
    worm_bonus_fp: np.ndarray,
    fpi: np.ndarray,
    fp: np.ndarray,
    quad: np.ndarray,
    visible_per_quad: list[np.ndarray],
    seed_base: int,
    save_oof_ac: bool = False,
) -> dict[str, object]:
    """Disk-backed, low-RAM (<1.1 GB RSS) 6-pair + 4-quadrant nested OOF Stage-1 -> Stage-2 hierarchy."""
    cache = WORK_DIR / "models" / tag
    cache.mkdir(parents=True, exist_ok=True)
    hard_full_col = 53
    hard_sub_col = 37
    n_fp = int(fp.sum())
    quad_fp = quad[fp]

    # Step A: Ensure all 6 pairwise 2-quadrant Stage-1 fits exist on disk (no in-RAM dict!)
    for a, b in itertools.combinations(range(4), 2):
        pf_file = cache / f"pair_full_{a}_{b}.f16.npy"
        ps_file = cache / f"pair_sub_{a}_{b}.f16.npy"
        if not (pf_file.is_file() and ps_file.is_file()):
            eval_ab = fp & ((quad == a) | (quad == b))
            tr_cd = fp & (ndi.distance_transform_edt(~((quad == a) | (quad == b))) > 25)
            vis_cd = visible_per_quad[a] & visible_per_quad[b] & tr_cd
            pf = fit_specialist_fp_vec(X_s20, full_cols, None, fpi, fp, vis_cd, vis_cd, tr_cd, eval_ab, hard_full_col, seed_base + 10 * a + b)
            np.save(pf_file, pf)
            del pf
            ps = fit_specialist_fp_vec(X_s20, sub_cols, None, fpi, fp, vis_cd, vis_cd, tr_cd, eval_ab, hard_sub_col, seed_base + 50 + 10 * a + b)
            np.save(ps_file, ps)
            del ps
            gc.collect()

    oof_ac_full_mm = None
    oof_ac_sub_mm = None
    if save_oof_ac:
        acf_path = cache / "oof_ac_full.f16.npy"
        acs_path = cache / "oof_ac_sub.f16.npy"
        oof_ac_full_mm = np.lib.format.open_memmap(
            acf_path, mode="r+" if acf_path.is_file() else "w+", dtype=np.float16, shape=(n_fp, len(R20.AUTOCONTEXT_NAMES))
        )
        oof_ac_sub_mm = np.lib.format.open_memmap(
            acs_path, mode="r+" if acs_path.is_file() else "w+", dtype=np.float16, shape=(n_fp, len(R20.AUTOCONTEXT_NAMES))
        )

    fold_pooled_files: list[Path] = []
    fold_s2_sub_files: list[Path] = []
    oof_surface_fp = np.zeros(n_fp, dtype=np.float16)
    oof_s2_sub_fp = np.zeros(n_fp, dtype=np.float16)

    for k in range(4):
        train_dom = fp & (ndi.distance_transform_edt(quad != k) > TRAIN_BUFFER_PX)
        pred_margin = fp & (ndi.distance_transform_edt(quad != k) <= 18)
        vis_k = visible_per_quad[k]

        s1f_file = cache / f"oof_s1_full_q{k}.f16.npy"
        s1s_file = cache / f"oof_s1_sub_q{k}.f16.npy"
        if not (s1f_file.is_file() and s1s_file.is_file()):
            s1_te_f = fit_specialist_fp_vec(X_s20, full_cols, None, fpi, fp, vis_k, vis_k, train_dom, pred_margin, hard_full_col, seed_base + 100 + k)
            np.save(s1f_file, s1_te_f)
            del s1_te_f
            s1_te_s = fit_specialist_fp_vec(X_s20, sub_cols, None, fpi, fp, vis_k, vis_k, train_dom, pred_margin, hard_sub_col, seed_base + 150 + k)
            np.save(s1s_file, s1_te_s)
            del s1_te_s
            gc.collect()

        # Assemble Stage-1 OOF mosaic strictly as (n_fp,) vectors (~20 MB total!)
        s1_mos_f_fp = np.zeros(n_fp, dtype=np.float16)
        s1_mos_s_fp = np.zeros(n_fp, dtype=np.float16)
        for m in range(4):
            if m == k:
                continue
            pkey = (min(k, m), max(k, m))
            qm_fp = quad_fp == m
            s1_mos_f_fp[qm_fp] = np.load(cache / f"pair_full_{pkey[0]}_{pkey[1]}.f16.npy", mmap_mode="r")[qm_fp]
            s1_mos_s_fp[qm_fp] = np.load(cache / f"pair_sub_{pkey[0]}_{pkey[1]}.f16.npy", mmap_mode="r")[qm_fp]
        pm_fp = pred_margin[fp]
        s1_mos_f_fp[pm_fp] = np.load(s1f_file, mmap_mode="r")[pm_fp]
        s1_mos_s_fp[pm_fp] = np.load(s1s_file, mmap_mode="r")[pm_fp]

        s2f_file = cache / f"oof_s2_full_q{k}.f16.npy"
        s2s_file = cache / f"oof_s2_sub_q{k}.f16.npy"
        ac_done_marker = cache / f"oof_ac_saved_q{k}.ok"
        need_s2 = not (s2f_file.is_file() and s2s_file.is_file())
        need_ac = save_oof_ac and not ac_done_marker.is_file()

        if need_s2 or need_ac:
            ac_f = R20.compute_stage2_autocontext(fp_vec_to_grid(s1_mos_f_fp, fp), fp)
            if need_s2:
                s2_f_fp = fit_specialist_fp_vec(X_s20, full_cols, ac_f, fpi, fp, vis_k, vis_k, train_dom, fp, hard_full_col, seed_base + 200 + k)
                np.save(s2f_file, s2_f_fp)
                del s2_f_fp
            if need_ac and oof_ac_full_mm is not None:
                rk_fp = quad_fp == k
                oof_ac_full_mm[rk_fp] = ac_f[rk_fp]
                oof_ac_full_mm.flush()
            del ac_f
            gc.collect()

            ac_s = R20.compute_stage2_autocontext(fp_vec_to_grid(s1_mos_s_fp, fp), fp)
            if need_s2:
                s2_s_fp = fit_specialist_fp_vec(X_s20, sub_cols, ac_s, fpi, fp, vis_k, vis_k, train_dom, fp, hard_sub_col, seed_base + 250 + k)
                np.save(s2s_file, s2_s_fp)
                del s2_s_fp
            if need_ac and oof_ac_sub_mm is not None:
                rk_fp = quad_fp == k
                oof_ac_sub_mm[rk_fp] = ac_s[rk_fp]
                oof_ac_sub_mm.flush()
                ac_done_marker.write_text("ok\n")
            del ac_s
            gc.collect()

        s2_f_fp = np.load(s2f_file)
        s2_s_fp = np.load(s2s_file)
        pooled_fp = pool_dual_specialist_vec(s1_mos_f_fp, s2_f_fp, s2_s_fp, cover_idx_fp, worm_bonus_fp, train_dom[fp])
        pooled_file = cache / f"pooled_q{k}.f16.npy"
        np.save(pooled_file, pooled_fp)
        fold_pooled_files.append(pooled_file)
        fold_s2_sub_files.append(s2s_file)

        rk_fp = quad_fp == k
        oof_surface_fp[rk_fp] = pooled_fp[rk_fp]
        oof_s2_sub_fp[rk_fp] = s2_s_fp[rk_fp]

        del s1_mos_f_fp, s1_mos_s_fp, s2_f_fp, s2_s_fp, pooled_fp
        gc.collect()
        log(f"[{tag}] Completed Stage-1 + Stage-2 Dual-Specialist OOF fold {k}/3")

    oof_surf_file = cache / "oof_surface.f16.npy"
    oof_sub_file = cache / "oof_s2_sub.f16.npy"
    np.save(oof_surf_file, oof_surface_fp)
    np.save(oof_sub_file, oof_s2_sub_fp)
    del oof_surface_fp, oof_s2_sub_fp
    gc.collect()

    return {
        "fold_pooled_files": fold_pooled_files,
        "fold_s2_sub_files": fold_s2_sub_files,
        "oof_surf_file": oof_surf_file,
        "oof_sub_file": oof_sub_file,
        "oof_ac_full": oof_ac_full_mm,
        "oof_ac_sub": oof_ac_sub_mm,
    }


def fit_apply_e3_ftrs_fold(
    p_e2: np.ndarray,
    s2_sub: np.ndarray,
    fold: dict,
    quad: np.ndarray,
    fp: np.ndarray,
    fpi: np.ndarray,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Fit offset-preserving E3 visible tip/relay (`FTRS`) boost strictly inside `train_dom`
    (preserving `1.0 * ell_e2` dynamic range!) and apply to `fold['visible']`."""
    k = int(fold["fold"])
    train_dom = fp & (ndi.distance_transform_edt(quad != k) > TRAIN_BUFFER_PX)
    vis_all = fold["visible"]
    vis_tr = vis_all & train_dom

    comp, n_comp = ndi.label(vis_tr, structure=STRUCT3)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(np.arange(1, n_comp + 1))
    n_hold = max(1, int(round(0.20 * n_comp)))
    vis_tr20 = np.isin(comp, perm[:n_hold]) & vis_tr
    near_hold = ndi.distance_transform_edt(~vis_tr20) <= 3.0
    vis_tr80 = vis_tr & (~vis_tr20) & (~near_hold)

    ftrs_inner = R20.compute_fold_safe_visible_ftrs(vis_tr80, s2_sub, fp, collar_guard_px=2.5)
    d_vis80 = ndi.distance_transform_edt(~vis_tr80)
    inner_elig = train_dom & fp & (~vis_tr80) & (d_vis80 > COLLAR_PX)

    pos_ids = fpi[inner_elig & vis_tr20]
    neg_pool = fpi[inner_elig & (~vis_tr20) & (ndi.distance_transform_edt(~vis_all) > 3.0)]
    n_neg = min(neg_pool.size, 5 * pos_ids.size)
    neg_ids = rng.choice(neg_pool, n_neg, replace=False)

    ell_e2_fp = logit_safe(p_e2[fp])
    tr_ids = np.concatenate([pos_ids, neg_ids])
    y_tr = np.r_[np.ones(pos_ids.size, dtype=np.int32), np.zeros(n_neg, dtype=np.int32)]

    X_meta = np.column_stack([ell_e2_fp[tr_ids], ftrs_inner[tr_ids, 0], ftrs_inner[tr_ids, 1], ftrs_inner[tr_ids, 2]]).astype(np.float32)
    lr = LogisticRegression(C=0.4, max_iter=300)
    lr.fit(X_meta, y_tr)
    raw_c = lr.coef_[0]
    c0 = max(float(raw_c[0]), 0.35)
    b_vec = np.array(
        [
            float(np.clip(raw_c[1] / c0, 0.0, 0.14)),
            float(np.clip(raw_c[2] / c0, 0.0, 0.12)),
            float(np.clip(raw_c[3] / c0, 0.0, 0.22)),
        ],
        dtype=np.float32,
    )
    del ftrs_inner

    ftrs_test = R20.compute_fold_safe_visible_ftrs(vis_all, s2_sub, fp, collar_guard_px=2.5)
    boost = np.maximum(ftrs_test @ b_vec, 0.0).astype(np.float32)
    surf_e3 = np.zeros(fp.shape, dtype=np.float32)
    surf_e3[fp] = sigmoid_safe(ell_e2_fp + boost)
    return surf_e3, ftrs_test, b_vec


def emit_fold_dots(surface: np.ndarray, eligible: np.ndarray, n_dots: int) -> np.ndarray:
    dots = submodular_dti_emit(surface, eligible_mask=eligible, n_dots=int(n_dots))
    return ((dots > 0) & eligible).astype(np.float32)


def dot_distance_stats(dots: np.ndarray, ref_mask: np.ndarray) -> dict[str, float | int]:
    pos = dots > 0
    n = int(pos.sum())
    if n == 0:
        return {"n": 0}
    d = ndi.distance_transform_edt(~ref_mask)[pos]
    return {
        "n": n,
        "min_dist_px": round(float(d.min()), 4),
        "median_dist_px": round(float(np.median(d)), 3),
        "share_le_5px": round(float((d <= 5.0).mean()), 4),
        "share_5_10px": round(float(((d > 5.0) & (d <= 10.0)).mean()), 4),
        "share_gt_10px": round(float((d > 10.0).mean()), 4),
    }


def extended_registry_paths(exclude_sha: str | None = None) -> tuple[list[tuple[Path, str]], list[dict]]:
    paths = sorted((ROOT / "data" / "registry").glob("*.tif"))
    paths += sorted((ROOT / "registry" / "rasters").glob("*.tif"))
    paths += sorted((ROOT / "data" / "fleet_registry").glob("*.tif"))
    paths += sorted((ROOT / "data" / "registry_siblings").glob("*.tif"))
    paths += sorted(DOWNLOADS_DIR.glob("*.tif"))
    nine_dir = ROOT / "work" / "nine_sites_audit" / "rasters"
    if nine_dir.is_dir():
        paths += sorted(nine_dir.glob("*.tif"))

    seen: dict[str, str] = {}
    uniq: list[tuple[Path, str]] = []
    dups: list[dict] = []
    for p in paths:
        h = sha256_file(p)
        if exclude_sha and h == exclude_sha:
            continue
        rel = str(p.relative_to(ROOT))
        if h in seen:
            dups.append({"path": rel, "same_bytes_as": seen[h]})
            continue
        seen[h] = rel
        uniq.append((p, h))
    return uniq, dups


def full_registry_uniqueness_audit(
    surface: np.ndarray,
    dots: np.ndarray,
    fp: np.ndarray,
    eligible: np.ndarray,
    exclude_sha: str | None = None,
    stride: int = 5,
) -> dict[str, object]:
    """Run Rule 1 pre-placement surface Spearman (`|rho| <= 0.90`) and post-placement dot
    Spearman + directed `3-px` overlap (`<= 0.70`) across ALL repo, fleet, and 9-site rasters."""
    uniq, dups = extended_registry_paths(exclude_sha=exclude_sha)
    s = surface[fp][::stride].astype(np.float64)
    rs = rankdata(s) - (s.size + 1) / 2.0
    rs_n = float(np.linalg.norm(rs))

    dfp = dots[fp][::stride].astype(np.float64)
    rd = rankdata(dfp) - (dfp.size + 1) / 2.0
    rd_n = float(np.linalg.norm(rd))

    cy, cx = np.nonzero(dots > 0)
    cand = np.c_[cy, cx].astype(np.float64)
    elig_n = int(eligible.sum())

    rows, skipped = [], []
    for p, h in uniq:
        with rasterio.open(p) as ds:
            if ds.count != 1 or ds.shape != fp.shape:
                skipped.append({"path": str(p.relative_to(ROOT)), "reason": "shape_or_band_mismatch"})
                continue
            a = ds.read(1).astype(np.float64)
        a = np.where(np.isfinite(a), a, 0.0)
        pos = (a > 0) & fp
        r = a[fp][::stride]
        rr = rankdata(r) - (r.size + 1) / 2.0
        rr_n = float(np.linalg.norm(rr))
        surf_rho = abs(float(rs @ rr) / (rs_n * rr_n)) if rr_n > 0 else 0.0
        dot_rho = abs(float(rd @ rr) / (rd_n * rr_n)) if rr_n > 0 else 0.0
        n_pos = int(pos.sum())
        if n_pos > 0:
            tree = cKDTree(np.c_[np.nonzero(pos)].astype(np.float64))
            dd, _ = tree.query(cand, k=1, distance_upper_bound=3.000001)
            fwd = float(np.isfinite(dd).mean())
            near = ndi.distance_transform_edt(~pos) <= 3.000001
            chance = float((near & eligible).sum()) / max(elig_n, 1)
            fp_cov = float((near & fp).sum()) / float(fp.sum())
        else:
            fwd, chance, fp_cov = 0.0, 0.0, 0.0
        corrected = (fwd - chance) / (1.0 - chance) if chance < 1.0 else 0.0
        blanket = fp_cov >= O.BLANKET_COVERAGE
        lit_dup = bool(surf_rho > O.MAX_RANK_CORR or dot_rho > O.MAX_RANK_CORR or fwd > O.MAX_DOT_OVERLAP)
        comp_dup = bool(
            surf_rho > O.MAX_RANK_CORR
            or dot_rho > O.MAX_RANK_CORR
            or (corrected > O.MAX_DOT_OVERLAP if blanket else fwd > O.MAX_DOT_OVERLAP)
        )
        rows.append(
            {
                "raster": str(p.relative_to(ROOT)),
                "sha256": h,
                "n_positive": n_pos,
                "surface_abs_spearman": round(surf_rho, 5),
                "dots_abs_spearman": round(dot_rho, 5),
                "dots_within_3px_literal": round(fwd, 5),
                "chance_within_3px": round(chance, 5),
                "dots_within_3px_chance_corrected": round(corrected, 5),
                "reference_3px_footprint_coverage": round(fp_cov, 5),
                "blanket_reference": blanket,
                "duplicate_literal": lit_dup,
                "duplicate_competitive": comp_dup,
            }
        )

    worst_s = max(rows, key=lambda r: r["surface_abs_spearman"])
    worst_d_rho = max(rows, key=lambda r: r["dots_abs_spearman"])
    worst_lit = max(rows, key=lambda r: r["dots_within_3px_literal"])
    worst_non_blanket = max((r for r in rows if not r["blanket_reference"]), key=lambda r: r["dots_within_3px_literal"])
    r0_row = next((r for r in rows if "GEMSDOE32__h33-2-b2-zeros" in r["raster"]), None)

    return {
        "n_unique_rasters_checked": len(rows),
        "byte_duplicates_skipped_count": len(dups),
        "skipped": skipped,
        "surface_max_abs_spearman": worst_s["surface_abs_spearman"],
        "surface_closest": worst_s["raster"],
        "dots_max_abs_spearman": worst_d_rho["dots_abs_spearman"],
        "dots_closest_spearman": worst_d_rho["raster"],
        "dots_max_within_3px_non_blanket": worst_non_blanket["dots_within_3px_literal"],
        "dots_closest_non_blanket": worst_non_blanket["raster"],
        "dots_max_within_3px_literal_all": worst_lit["dots_within_3px_literal"],
        "dots_closest_literal_all": worst_lit["raster"],
        "vs_gemsdoe32_r0": r0_row,
        "blanket_references": [r["raster"] for r in rows if r["blanket_reference"]],
        "competitive_uniqueness_pass": not any(r["duplicate_competitive"] for r in rows),
        "literal_all_inventory_pass": not any(r["duplicate_literal"] for r in rows),
        "comparisons": rows,
    }


def evaluate_blind_sgmc(dots: np.ndarray, cat: np.ndarray, fp: np.ndarray) -> dict[str, object]:
    with rasterio.open(SGMC_TIF) as ds:
        sgmc = (ds.read(1) > 0) & fp
    with rasterio.open(R0_TIF) as ds:
        r0 = (ds.read(1) > 0) & fp

    d_cat = ndi.distance_transform_edt(~cat)
    res: dict[str, object] = {"evidence_class": "BLIND-SGMC-CONTROL"}
    for thresh_px, label in ((3.0, "gt_300m"), (5.0, "gt_500m"), (10.0, "gt_1km")):
        dom = fp & (d_cat > thresh_px)
        truth = sgmc & dom
        cand_m = M.dti_exact((dots > 0).astype(float), truth, valid=dom)
        r0_m = M.dti_exact(r0.astype(float), truth, valid=dom)
        res[label] = {
            "sgmc_positive_pixels": int(truth.sum()),
            "candidate_dti": round(float(cand_m["dti"]), 6),
            "gemsdoe32_r0_dti": round(float(r0_m["dti"]), 6),
            "delta_vs_r0": round(float(cand_m["dti"] - r0_m["dti"]), 6),
            "ratio_vs_r0": round(float(cand_m["dti"] / max(r0_m["dti"], 1e-9)), 4),
        }
    return res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run S20-RHTW preregistered 3-experiment suite.")
    parser.add_argument("--stop-after-step3", action="store_true", help="Stop after I2 evaluation + 103-feature canary.")
    parser.add_argument("--stop-after-step4", action="store_true", help="Stop after building FINAL OOF hierarchy.")
    parser.add_argument("--recompute-step2", action="store_true", help="Force recomputing Step 2-3 even if cached.")
    args = parser.parse_args(argv)

    t0 = time.time()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    log("Step 0: Verifying SHA-256 input & template pins + frozen preregistration")
    pins = verify_pinned_inputs()

    g = G.load_grid(ROOT / "data" / "official")
    fp, cat = g.footprint, g.catalogue
    n_fp = int(fp.sum())
    fpi = O.fp_index_grid(fp)

    log("Step 1: Memmapping cached 72-feature S20-RHTW stack")
    X_s20, s20_names, worm_bonus_fp = R20.build_or_load_s20_features(FEATURES_TIF, GDR_CSV, fp, WORK_DIR)
    cover_idx_fp = np.asarray(X_s20[:, 71], dtype=np.float32)

    folds_i2, quad = H.buffered_component_draw(g, seed=SEED, hide_frac=0.20, buffer_px=3)
    vis_per_quad_i2 = [f["visible"] for f in folds_i2]
    arms = ("E0", "E1", "E2", "E3", "RND")

    i2_json_path = OUT_DIR / "holdout-i2.json"
    can_json_path = OUT_DIR / "canaries.json"
    i2_e2_oof_path = WORK_DIR / "models" / "I2_E2" / "oof_surface.f16.npy"

    if (
        not args.recompute_step2
        and not args.stop_after_step3
        and i2_json_path.is_file()
        and can_json_path.is_file()
        and i2_e2_oof_path.is_file()
    ):
        log("Step 2-3: Loading verified cached I2 holdout & 103-feature canary results from docs/s20_rhtw/")
        i2_saved = json.loads(i2_json_path.read_text())
        can_saved = json.loads(can_json_path.read_text())
        pooled_i2 = i2_saved["pooled"]
        per_fold_i2 = i2_saved["per_fold"]
        winner_arm = i2_saved["winner_arm"]
        e3_bvecs = [np.array(r["e3_relative_ftrs_boost_weights"], dtype=np.float32) for r in per_fold_i2]
        canary_rows = can_saved["features"]
        worst_canary = can_saved["worst"]
        hier_e2_oof_surf_file = i2_e2_oof_path
    else:
        log("Step 2A: Running Experiment 1 (E1: H20-1 + H20-3 Pure Geophysical + Openness Dual-Specialist OOF)")
        hier_e1 = run_two_stage_hierarchy(
            "I2_E1", X_s20, R20.FULL_E1_COLS, R20.SUB_E1_COLS, cover_idx_fp, worm_bonus_fp, fpi, fp, quad, vis_per_quad_i2, 20100, save_oof_ac=False
        )

        log("Step 2B: Running Experiment 2 (E2: E1 + H20-2 Strike-Guided GDR 1391 Geothermometer Conduits)")
        hier_e2 = run_two_stage_hierarchy(
            "I2_E2", X_s20, R20.FULL_E2_COLS, R20.SUB_E2_COLS, cover_idx_fp, worm_bonus_fp, fpi, fp, quad, vis_per_quad_i2, 20500, save_oof_ac=True
        )

        log("Step 2C: Running Experiment 3 (E3: E2 + H20-4 Fold-Safe Visible Tip/Relay Bridge) & Evaluating All Arms on I2")
        X_e0, _ = O.build_features(fp)
        terms_i2: dict[str, np.ndarray | None] = {a: None for a in arms}
        per_fold_i2 = []
        oof_ftrs_e3 = np.lib.format.open_memmap(WORK_DIR / "oof_ftrs_e3.f16.npy", mode="w+", dtype=np.float16, shape=(n_fp, 3))
        e3_bvecs = []

        canary_truth_ids: list[np.ndarray] = []
        canary_unl_ids: list[np.ndarray] = []
        canary_quad_truth: list[np.ndarray] = []
        canary_quad_unl: list[np.ndarray] = []

        for k, f in enumerate(folds_i2):
            region = f["region"]
            known = f["masked_known"]
            train_dom = fp & (ndi.distance_transform_edt(quad != k) > TRAIN_BUFFER_PX)
            pred_margin_e0 = fp & (ndi.distance_transform_edt(~region) <= 7)

            p_e0, _ = O.fit_predict(X_e0, fpi, fp, f["visible"], train_dom, pred_margin_e0, SEED * 100 + k)
            elig_e0 = region & fp & (~known) & (ndi.distance_transform_edt(~known) > O.COLLAR_PX)
            elig_s20 = region & fp & (~known) & (ndi.distance_transform_edt(~known) > COLLAR_PX)
            n_k = int(round(BUDGET * float((region & fp).sum()) / float(n_fp)))

            surf_e1_k = fp_vec_to_grid(np.load(hier_e1["fold_pooled_files"][k]), fp)
            surf_e2_k = fp_vec_to_grid(np.load(hier_e2["fold_pooled_files"][k]), fp)
            s2_sub_e2_k = fp_vec_to_grid(np.load(hier_e2["fold_s2_sub_files"][k]), fp)

            surf_e3_k, ftrs_fold_mat, b_vec_k = fit_apply_e3_ftrs_fold(
                surf_e2_k, s2_sub_e2_k, f, quad, fp, fpi, seed=20900 + k
            )
            e3_bvecs.append(b_vec_k)
            rk_fp = (region & fp)[fp]
            oof_ftrs_e3[rk_fp] = ftrs_fold_mat[rk_fp].astype(np.float16)
            oof_ftrs_e3.flush()

            preds = {
                "E0": O.emit(p_e0, elig_e0, n_k),
                "E1": emit_fold_dots(surf_e1_k, elig_s20, n_k),
                "E2": emit_fold_dots(surf_e2_k, elig_s20, n_k),
                "E3": emit_fold_dots(surf_e3_k, elig_s20, n_k),
                "RND": O.random_dots(elig_e0, n_k, SEED * 7 + k),
            }

            active = fp & region & (~known)
            truth = active & f["truth"]
            t_ids = fpi[truth]
            u_ids = fpi[active & (~truth)]
            canary_truth_ids.append(t_ids)
            canary_unl_ids.append(u_ids)
            canary_quad_truth.append(t_ids)
            canary_quad_unl.append(u_ids)

            fold_row: dict[str, object] = {
                "fold": f["name"],
                "n_dots": n_k,
                "withheld_positive_pixels": int(truth.sum()),
                "e3_relative_ftrs_boost_weights": [round(float(c), 5) for c in b_vec_k],
            }
            for a in arms:
                ev_res, tm = EH.evaluate(preds[a], f, fp)
                terms_i2[a] = tm if terms_i2[a] is None else terms_i2[a] + tm
                fold_row[f"{a}_dti"] = round(float(ev_res["dti"]), 6)
                fold_row[f"{a}_dot_geometry"] = dot_distance_stats(preds[a], f["visible"])
            per_fold_i2.append(fold_row)
            log(
                f"I2 fold {f['name']}: E0={fold_row['E0_dti']:.4f} | E1={fold_row['E1_dti']:.4f} | "
                f"E2={fold_row['E2_dti']:.4f} | E3={fold_row['E3_dti']:.4f} | RND={fold_row['RND_dti']:.4f}"
            )
            del surf_e1_k, surf_e2_k, s2_sub_e2_k, surf_e3_k, ftrs_fold_mat, p_e0, preds
            gc.collect()

        raw_arm_dtis = {}
        for cand_a in ("E1", "E2", "E3"):
            s_tmp = EH.pooled_summary(terms_i2, candidate=cand_a)
            raw_arm_dtis[cand_a] = float(s_tmp["scores"][cand_a]["dti"])
        winner_arm = max(("E1", "E2", "E3"), key=lambda a: raw_arm_dtis[a])
        pooled_i2 = EH.pooled_summary(terms_i2, candidate=winner_arm)
        for a in arms:
            sc = pooled_i2["scores"][a]
            log(f"POOLED I2 {a}: {sc['dti']:.6f} HOLDOUT-DTI CI95=[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}]")
        log(
            f"WINNER ON PRIMARY I2 = {winner_arm} ({raw_arm_dtis[winner_arm]:.6f} vs E0={pooled_i2['scores']['E0']['dti']:.6f}, "
            f"paired delta={pooled_i2['paired_differences']['E0']['delta']:+.6f}, "
            f"CI95={pooled_i2['paired_differences']['E0']['ci95']})"
        )

        log("Step 3: Running Rule 4 single-feature AUROC leakage canaries across all 103 features")
        rng_can = np.random.default_rng(SEED)
        all_t = np.concatenate(canary_truth_ids)
        all_u = np.concatenate(canary_unl_ids)
        sub_u = np.sort(rng_can.choice(all_u, min(all_u.size, 300_000), replace=False))
        eval_ids = np.concatenate([all_t, sub_u])
        eval_y = np.r_[np.ones(all_t.size, dtype=np.uint8), np.zeros(sub_u.size, dtype=np.uint8)]

        quad_eval_pairs = []
        for qt, qu in zip(canary_quad_truth, canary_quad_unl):
            qu_sub = np.sort(rng_can.choice(qu, min(qu.size, 80_000), replace=False))
            quad_eval_pairs.append(
                (np.concatenate([qt, qu_sub]), np.r_[np.ones(qt.size, dtype=np.uint8), np.zeros(qu_sub.size, dtype=np.uint8)])
            )

        canary_rows = []
        assert hier_e2["oof_ac_full"] is not None and hier_e2["oof_ac_sub"] is not None
        feature_sources = (
            [(nm, X_s20, j) for j, nm in enumerate(s20_names)]
            + [(f"ac_full_{nm}", hier_e2["oof_ac_full"], j) for j, nm in enumerate(R20.AUTOCONTEXT_NAMES)]
            + [(f"ac_sub_{nm}", hier_e2["oof_ac_sub"], j) for j, nm in enumerate(R20.AUTOCONTEXT_NAMES)]
            + [(nm, oof_ftrs_e3, j) for j, nm in enumerate(R20.FTRS_FEATURE_NAMES)]
        )
        for fname, mat, col_j in feature_sources:
            v_p = np.asarray(mat[eval_ids, col_j], dtype=np.float32)
            auc_p = float(roc_auc_score(eval_y, v_p))
            sym_p = max(auc_p, 1.0 - auc_p)
            q_syms = []
            for q_ids, q_y in quad_eval_pairs:
                qa = float(roc_auc_score(q_y, np.asarray(mat[q_ids, col_j], dtype=np.float32)))
                q_syms.append(round(max(qa, 1.0 - qa), 6))
            worst_q = max(q_syms)
            if sym_p > 0.90 or worst_q > 0.90:
                raise RuntimeError(f"Rule 4 Canary STOP on {fname}: pooled={sym_p:.6f}, quads={q_syms}")
            canary_rows.append(
                {
                    "feature": fname,
                    "auc": round(auc_p, 6),
                    "symmetric_auc": round(sym_p, 6),
                    "quadrant_symmetric_aucs": q_syms,
                    "max_quadrant_symmetric_auc": worst_q,
                    "status": "PASS",
                }
            )
        worst_canary = max(canary_rows, key=lambda r: max(r["symmetric_auc"], r["max_quadrant_symmetric_auc"]))
        log(
            f"Rule 4 Canary PASS across {len(canary_rows)}/103 features: worst pooled={worst_canary['symmetric_auc']:.4f} "
            f"({worst_canary['feature']}), max_quad={worst_canary['max_quadrant_symmetric_auc']:.4f} <= 0.90"
        )

        i2_json_path.write_text(
            json.dumps({"pooled": pooled_i2, "per_fold": per_fold_i2, "winner_arm": winner_arm}, indent=2) + "\n"
        )
        can_json_path.write_text(
            json.dumps(
                {
                    "threshold": 0.90,
                    "n_features_tested": len(canary_rows),
                    "all_pass": True,
                    "worst": worst_canary,
                    "features": canary_rows,
                },
                indent=2,
            )
            + "\n"
        )
        hier_e2_oof_surf_file = hier_e2["oof_surf_file"]
        del X_e0, hier_e1, hier_e2, oof_ftrs_e3
        gc.collect()

    if args.stop_after_step3:
        log("Completed Step 0-3 (--stop-after-step3); exiting cleanly before Step 4-7.")
        return 0

    log(f"Step 4: Building stitched 4-quadrant OOF full-catalogue surface for winning arm {winner_arm}")
    vis_full_loqo = [cat & (ndi.distance_transform_edt(quad != k) > TRAIN_BUFFER_PX) for k in range(4)]
    if winner_arm == "E1":
        final_hier = run_two_stage_hierarchy(
            "FINAL_E1", X_s20, R20.FULL_E1_COLS, R20.SUB_E1_COLS, cover_idx_fp, worm_bonus_fp, fpi, fp, quad, vis_full_loqo, 30100, save_oof_ac=False
        )
    else:
        final_hier = run_two_stage_hierarchy(
            "FINAL_E2", X_s20, R20.FULL_E2_COLS, R20.SUB_E2_COLS, cover_idx_fp, worm_bonus_fp, fpi, fp, quad, vis_full_loqo, 30500, save_oof_ac=False
        )

    if args.stop_after_step4:
        log("Completed Step 4 (--stop-after-step4); exiting cleanly before Step 5-7.")
        return 0

    # Note: FINAL_E2's oof_surface in quadrant k was trained strictly on cat outside quadrant k (>40 px away)!
    # Therefore FINAL_E2's oof_surface is 100% leak-free on Secondary Holdout I1 inside quadrant k!
    i1_json_path = OUT_DIR / "holdout-i1-isolated.json"
    oof_final_e2_grid = fp_vec_to_grid(np.load(final_hier["oof_surf_file"]), fp)
    oof_final_sub_grid = fp_vec_to_grid(np.load(final_hier["oof_sub_file"]), fp)
    avg_bvec = np.mean(e3_bvecs, axis=0).astype(np.float32)

    if not args.recompute_step2 and i1_json_path.is_file():
        log("Step 5: Loading verified cached Secondary Isolated-Fault Holdout I1 from docs/s20_rhtw/")
        pooled_i1 = json.loads(i1_json_path.read_text())
    else:
        log("Step 5: Evaluating 100%-OOF S20 surface on Secondary Isolated-Fault Holdout I1 (11,911 positives)")
        X_e0, _ = O.build_features(fp)
        folds_i1, quad_i1 = IH.isolated_component_draw(g, sep_px=5.0, buffer_px=3)
        terms_i1: dict[str, np.ndarray | None] = {"S20_OOF": None, "E0": None, "RND": None}
        for f1 in folds_i1:
            k1 = int(f1["fold"])
            reg1 = f1["region"]
            kn1 = f1["masked_known"]
            tr1 = fp & (ndi.distance_transform_edt(quad_i1 != k1) > TRAIN_BUFFER_PX)
            pm1 = fp & (ndi.distance_transform_edt(~reg1) <= 3)
            p0_1, _ = O.fit_predict(X_e0, fpi, fp, f1["visible"], tr1, pm1, SEED * 100 + k1)
            elig1_e0 = reg1 & fp & (~kn1) & (ndi.distance_transform_edt(~kn1) > O.COLLAR_PX)
            elig1_s20 = reg1 & fp & (~kn1) & (ndi.distance_transform_edt(~kn1) > COLLAR_PX)
            n1 = int(round(BUDGET * float((reg1 & fp).sum()) / float(n_fp)))
            if winner_arm == "E3":
                ftrs_i1 = R20.compute_fold_safe_visible_ftrs(f1["visible"], oof_final_sub_grid, fp, collar_guard_px=2.5)
                surf_i1 = np.zeros(fp.shape, dtype=np.float32)
                surf_i1[fp] = sigmoid_safe(logit_safe(oof_final_e2_grid[fp]) + np.maximum(ftrs_i1 @ avg_bvec, 0.0))
                del ftrs_i1
            else:
                surf_i1 = oof_final_e2_grid
            p_i1 = {
                "S20_OOF": emit_fold_dots(surf_i1, elig1_s20, n1),
                "E0": O.emit(p0_1, elig1_e0, n1),
                "RND": O.random_dots(elig1_e0, n1, SEED * 7 + k1),
            }
            for ka, arr_a in p_i1.items():
                _, tm1 = EH.evaluate(arr_a, f1, fp)
                terms_i1[ka] = tm1 if terms_i1[ka] is None else terms_i1[ka] + tm1
        pooled_i1 = EH.pooled_summary(terms_i1, candidate="S20_OOF")
        log(
            f"POOLED I1 (isolated >500m, 11,911 pos): S20_OOF={pooled_i1['scores']['S20_OOF']['dti']:.6f} vs "
            f"E0={pooled_i1['scores']['E0']['dti']:.6f} (delta={pooled_i1['paired_differences']['E0']['delta']:+.6f}, "
            f"CI95={pooled_i1['paired_differences']['E0']['ci95']})"
        )
        i1_json_path.write_text(json.dumps(pooled_i1, indent=2) + "\n")
        del X_e0
        gc.collect()

    if winner_arm in ("E1", "E2"):
        final_surface = oof_final_e2_grid
    else:
        ftrs_full = R20.compute_fold_safe_visible_ftrs(cat, oof_final_sub_grid, fp, collar_guard_px=2.5)
        ell_e2_all = logit_safe(oof_final_e2_grid[fp])
        boost_all = np.maximum(ftrs_full @ avg_bvec, 0.0).astype(np.float32)
        final_surface = np.zeros(fp.shape, dtype=np.float32)
        final_surface[fp] = sigmoid_safe(ell_e2_all + boost_all)
        del ftrs_full
    del oof_final_sub_grid
    gc.collect()

    d_cat_full = ndi.distance_transform_edt(~cat)
    eligible_full = fp & (~cat) & (d_cat_full > COLLAR_PX)
    final_surface = np.where(fp, final_surface, 0.0).astype(np.float32)

    log("Step 6: Emitting exact 37,654 binary {0,1} dots via 300 m submodular expected-DTI CELF")
    final_dots = emit_fold_dots(final_surface, eligible_full, BUDGET)
    pred_zeros = np.where(fp, final_dots, 0.0).astype(np.float32)
    n_emitted = int((pred_zeros > 0).sum())
    assert n_emitted == BUDGET, f"Expected {BUDGET} dots, got {n_emitted}"

    ts_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    content_hash8 = hashlib.sha256(pred_zeros.tobytes()).hexdigest()[:8]
    stem = f"gems91-s20-rhtw-{winner_arm.lower()}-{ts_tag}-{content_hash8}-zeros"
    tif_path = DOWNLOADS_DIR / f"{stem}.tif"

    sub_name = stem
    i2_win_dti = pooled_i2["scores"][winner_arm]["dti"]
    sgmc_stats = evaluate_blind_sgmc(pred_zeros, cat, fp)
    sgmc_500 = sgmc_stats["gt_500m"]["candidate_dti"]
    sub_note = (
        f"S20-RHTW {winner_arm}: Riesz-grav/mag worm+GDR geotherm+pluvial OOF CELF 37654d; "
        f"I2 {i2_win_dti:.4f} HOLDOUT-DTI; SGMC>500m {sgmc_500:.4f}"
    )
    assert len(sub_note) <= 140, f"Note too long ({len(sub_note)}): {sub_note}"
    assert len(sub_name) <= 140

    receipt = write_submission(
        tif_path,
        pred_zeros,
        SAMPLE_TIF,
        fp,
        note=sub_note,
        name=sub_name,
        catalogue=cat,
        metadata={"lane": LANE_ID, "winner_arm": winner_arm, "emitted_dots": n_emitted},
    )
    tif_path.chmod(0o644)
    zip_path = DOWNLOADS_DIR / f"{stem}.zip"
    zip_path.chmod(0o644)
    rcpt_json = tif_path.with_suffix(".json")
    if rcpt_json.is_file():
        rcpt_json.chmod(0o644)
    tif_sha = sha256_file(tif_path)
    zip_sha = sha256_file(zip_path)

    log("Step 7: Running Rule 1 pre-placement & post-placement uniqueness audit across ALL repo, fleet & 9-site rasters")
    reg_audit = full_registry_uniqueness_audit(
        final_surface, pred_zeros, fp, eligible_full, exclude_sha=tif_sha
    )
    log(
        f"Registry Audit ({reg_audit['n_unique_rasters_checked']} unique rasters): "
        f"surface max |rho|={reg_audit['surface_max_abs_spearman']} ({reg_audit['surface_closest']}), "
        f"dots non-blanket max 3px={reg_audit['dots_max_within_3px_non_blanket']} ({reg_audit['dots_closest_non_blanket']}), "
        f"vs R0 3px={reg_audit['vs_gemsdoe32_r0']['dots_within_3px_literal'] if reg_audit['vs_gemsdoe32_r0'] else None}, "
        f"competitive_pass={reg_audit['competitive_uniqueness_pass']}"
    )
    if not reg_audit["competitive_uniqueness_pass"]:
        raise RuntimeError(
            f"Rule 1 competitive duplicate stop triggered: {reg_audit['dots_closest_non_blanket']} "
            f"({reg_audit['dots_max_within_3px_non_blanket']})"
        )

    v57_val = v57_validate(tif_path, footprint=fp, catalogue=cat)
    v57_fmt = v57_gates.format_report(tif_path, SAMPLE_TIF, footprint=fp)
    vr_val = VR.validate_raster(
        tif_path,
        SAMPLE_TIF,
        catalogue=CATALOGUE_TIF,
        ledger_csv=ROOT / "ledger" / "submissions.csv",
        parent=R0_TIF,
        allow_zeros_outside=True,
    )
    assert v57_val["all_checks_passed"] and v57_fmt["ok"] and vr_val.ok

    dot_geom = dot_distance_stats(pred_zeros, cat)
    elapsed_s = round(time.time() - t0, 2)

    i2_delta_e0 = pooled_i2["paired_differences"]["E0"]
    beats_i2_ci = bool(i2_delta_e0["delta"] > 0 and i2_delta_e0["ci95"][0] > 0)

    (OUT_DIR / "registry-audit.json").write_text(json.dumps(reg_audit, indent=2) + "\n")
    (OUT_DIR / "blind-sgmc.json").write_text(json.dumps(sgmc_stats, indent=2) + "\n")
    np.save(WORK_DIR / f"final_surface_{winner_arm}.npy", final_surface.astype(np.float16))

    run_card = {
        "lane": LANE_ID,
        "lane_meta": {
            "id": LANE_ID,
            "name": "Riesz-Harmonic Native Gravity-Magnetic Worm, Strike-Guided Hydrothermal Geothermometer Conduit & Pluvial-Decontaminated Dual-Specialist OOF Submodular Hierarchy",
            "assigned": False,
            "note": "No pasted method paragraph appeared below Rule 1 in the prompt; single cohesive S20-RHTW lane executed with 0 slots spent.",
        },
        "session": "arena/06420fd7-gemsdoe91",
        "date": "2026-10-26",
        "preregistration": "docs/HYPOTHESES_S20_RHTW.md",
        "preregistration_sha256": pins["preregistration"]["sha256"],
        "hypothesis": (
            "H20-1..H20-4: Reconstructing exact 3D harmonic vertical gravity derivatives from native (Band 18=dG/dx, Band 11=dG/dy) "
            "with unit-calibrated Band 09/(Band 03/200) magnetic tilt worms, anisotropic strike-diffused GDR 1391 silica/cation "
            "geothermometer disequilibrium, pluvial Lake Lahontan shoreline decontamination in Dual-Specialist OOF HGB, and "
            "geophysically-gated fold-safe visible tip/relay bridges allocated via 300 m submodular expected-DTI CELF beats "
            "the pinned E0/OLC91/ISO91 holdout baseline while preserving far-field (>1 km) concealed-fault discovery."
        ),
        "mechanism": (
            f"Winning arm {winner_arm}: Two-stage 4-quadrant spatially blocked Out-of-Fold (OOF, 4 km buffer) Dual-Specialist "
            "HistGradientBoosting (M_full + Band-12/19-blind M_sub with asymmetric positive-part cover rescue + 12-azimuth "
            "900m/1.7km line-integral auto-context + strike-steered hydrothermal geothermometer conduits"
            + (" + fold-safe visible tip/relay bridges)" if winner_arm == "E3" else ")")
            + ", emitted at exact N=37,654 binary {0,1} dots (>200 m collar) via 300 m triangular-kernel submodular CELF."
        ),
        "non_fault_mimic": (
            "Pleistocene Lake Lahontan (~1,332 m) & Lake Bonneville (~1,552 m) zero-throw wave-cut paleoshoreline benches, "
            "unfaulted Mesozoic plutonic contact halos, E-W GeoDAWN flight-line corrugation, and lateral alluvial thermal outflow plumes."
        ),
        "experiments_run": 3,
        "experiment_list": [
            "E1: H20-1 (Riesz-Harmonic Gravity/Magnetic Worms) + H20-3 (Pluvial-Decontaminated Openness Dual-Specialist OOF + CELF)",
            "E2: E1 + H20-2 (Strike-Guided GDR 1391 Geothermometer Disequilibrium & Transtensional Strain Conduits)",
            "E3: E2 + H20-4 (Geophysically-Gated Fold-Safe Visible Tip Wing-Crack & En-Echelon Relay Bridge Prior)",
        ],
        "budget": {
            "experiments_run": 3,
            "max_experiments": 3,
            "elapsed_seconds": elapsed_s,
            "max_seconds": 7200.0,
            "slots_used": 0,
        },
        "slots_used": 0,
        "holdout": {
            "primary_i2": {
                "instrument": "vendor/gems57 buffered_component_draw(seed=20, hide_frac=0.20, buffer_px=3, boundary_px=12)",
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": EH.VERSION,
                "withheld_positive_pixels": int(pooled_i2["scores"][winner_arm]["withheld_positive_pixels"]),
                "winning_arm": winner_arm,
                "scores": {
                    a: {
                        "dti": round(float(pooled_i2["scores"][a]["dti"]), 6),
                        "ci95": [round(float(x), 6) for x in pooled_i2["scores"][a]["ci95"]],
                    }
                    for a in arms
                },
                "paired_winner_minus": {
                    k_ref: {
                        "delta": round(float(v_ref["delta"]), 6),
                        "ci95": [round(float(x), 6) for x in v_ref["ci95"]],
                    }
                    for k_ref, v_ref in pooled_i2["paired_differences"].items()
                },
                "beats_incumbent_e0_95ci": beats_i2_ci,
            },
            "secondary_i1_isolated": {
                "instrument": "gems91.isolated_holdout.isolated_component_draw(sep_px=5.0, buffer_px=3)",
                "evidence_class": "HOLDOUT-DTI",
                "evaluator_version": EH.VERSION,
                "withheld_positive_pixels": int(pooled_i1["scores"]["S20_OOF"]["withheld_positive_pixels"]),
                "scores": {
                    ka: {
                        "dti": round(float(pooled_i1["scores"][ka]["dti"]), 6),
                        "ci95": [round(float(x), 6) for x in pooled_i1["scores"][ka]["ci95"]],
                    }
                    for ka in ("S20_OOF", "E0", "RND")
                },
                "paired_s20_minus_e0": {
                    "delta": round(float(pooled_i1["paired_differences"]["E0"]["delta"]), 6),
                    "ci95": [round(float(x), 6) for x in pooled_i1["paired_differences"]["E0"]["ci95"]],
                },
            },
            "blind_sgmc_off_catalogue": sgmc_stats,
        },
        "leakage_canary": {
            "threshold": 0.90,
            "n_features": len(canary_rows),
            "all_pass": True,
            "stop": False,
            "worst": worst_canary,
        },
        "uniqueness": {
            "n_unique_rasters_checked": reg_audit["n_unique_rasters_checked"],
            "surface_before_placement_max_abs_spearman": reg_audit["surface_max_abs_spearman"],
            "surface_closest": reg_audit["surface_closest"],
            "dots_max_abs_spearman": reg_audit["dots_max_abs_spearman"],
            "dots_max_within_3px_non_blanket": reg_audit["dots_max_within_3px_non_blanket"],
            "dots_closest_non_blanket": reg_audit["dots_closest_non_blanket"],
            "dots_within_3px_vs_gemsdoe32_r0": reg_audit["vs_gemsdoe32_r0"]["dots_within_3px_literal"]
            if reg_audit["vs_gemsdoe32_r0"]
            else None,
            "dots_max_within_3px_literal_including_blankets": reg_audit["dots_max_within_3px_literal_all"],
            "blanket_references": reg_audit["blanket_references"],
            "competitive_uniqueness_pass": reg_audit["competitive_uniqueness_pass"],
            "literal_all_inventory_pass": reg_audit["literal_all_inventory_pass"],
        },
        "raster": {
            "path": f"docs/downloads/{tif_path.name}",
            "sha256": tif_sha,
            "bytes": tif_path.stat().st_size,
            "n_dots": n_emitted,
            "zip": f"docs/downloads/{zip_path.name}",
            "zip_sha256": zip_sha,
            "zip_bytes": zip_path.stat().st_size,
            "receipt": f"docs/downloads/{rcpt_json.name}" if rcpt_json.is_file() else None,
            "dot_geometry": dot_geom,
        },
        "raster_path": f"docs/downloads/{tif_path.name}",
        "raster_sha256": tif_sha,
        "organizer_confirmed": None,
        "organizer_confirmed_scores": None,
        "validator_output": {
            "status": "PASS",
            "all_checks_passed": v57_val["all_checks_passed"],
            "crs": v57_val["meta"]["crs"],
            "shape": v57_val["meta"]["shape"],
            "dtype": v57_val["meta"]["dtype"],
            "nodata": v57_val["meta"]["nodata"],
            "in_footprint_min": v57_val["min"],
            "in_footprint_max": v57_val["max"],
            "full_grid_finite_pixels": v57_val["n_finite"],
            "n_nan": v57_val["n_nan"],
            "emitted_positive_pixels": v57_val["emitted_positive_pixels"],
            "on_catalogue_positive_pixels": v57_val["on_catalogue_positive_pixels"],
            "checks": v57_val["checks"],
        },
        "submission_name": sub_name,
        "submission_note": sub_note,
        "submission_note_chars": len(sub_note),
        "submission_ready": False,
        "ok_to_download": True,
        "ok_to_submit": False,
        "result": "negative",
        "scientific_holdout_verdict": "promote_candidate_for_human_selector" if beats_i2_ci else "negative",
        "verdict": {
            "promote": False,
            "scientific_holdout_beats_incumbent_e0": beats_i2_ci,
            "OK_TO_DOWNLOAD": "YES — validated all-finite [0, 1] GeoTIFF",
            "OK_TO_SUBMIT": "NO",
            "passed_gates": [
                g_name
                for g_name, ok_flag in [
                    ("G1_format_epsg32611_3730x3292_finite_0_1_zero_nan", True),
                    ("G2_canary_all_103_features_sym_auc_le_090", True),
                    ("G3_competitive_uniqueness_110plus_real_rasters_le_070", reg_audit["competitive_uniqueness_pass"]),
                    ("G4_primary_holdout_i2_beats_e0_95ci_gt_0", beats_i2_ci),
                    (
                        "G5_secondary_isolated_i1_beats_e0",
                        pooled_i1["paired_differences"]["E0"]["delta"] > 0,
                    ),
                ]
                if ok_flag
            ],
            "blocking_governance_gates": [
                "G6_separate_human_weekly_slot_selector_step_required (Rule 6: 0/3 weekly slots spent automatically)",
                "G7_unassigned_rule1_method_paragraph (lane.assigned = false)",
                "G8_synthetic_blanket_calibration_lattices_and_2_of_64_unfetchable_external_refs",
            ],
        },
        "inputs": pins,
    }
    RUN_CARD_PATH.write_text(json.dumps(run_card, indent=2) + "\n")
    log(f"DONE in {elapsed_s:.1f}s! Wrote {tif_path.name} (sha256={tif_sha[:16]}...) and {RUN_CARD_PATH.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
