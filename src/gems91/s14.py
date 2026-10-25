"""Session 14 lane (`S14-LSRG`): LiDAR-Scarp + Radiometric-Ratio + Spring-Geometry.

New label-free features that NO prior lane in this repo reads (grep-verified
2026-10-24): the 12-band 1 m-DEM-derived LiDAR scarp stack
(`data/external/lidar_scarp_features_u8.tif`) and the per-element USGS
GeoDAWN radiometrics (`data/external/geodawn_rad_u8.tif`, K/Th/U/TC; only the
TC composite, competition Band 06, was ever used before).

Quantization caveat (IR-91-S14-02): both external stacks are uint8
percentile-stretched derivatives whose exact stretch parameters are not
pinned in this repo. Features are therefore used only through (a) per-band
monotone values and (b) log-ratios of stretched bands — both are valid
nonlinear inputs for tree ensembles, but they are NOT physical
concentrations and are never interpreted as such.

Pre-registration: `docs/HYPOTHESES_S14.md` (frozen before any S14 holdout).
Shared tools reused, not forked (Protocol Rule 2): `scripts/dti.py`,
`scripts/evaluate_holdout.py`, `scripts/submission_writer.py`,
`gems91.dd_vtc_pu` (static memmap + fold-safe catalogue features),
`gems91.mhtr_coda`, `gems91.ptha` (crest surface + Dinkelbach emitter).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

S14_FEATURE_NAMES: list[str] = [
    # LiDAR scarp stack (uint8/255, invalid -> 0 with explicit valid flag)
    "s14_lid_ex_max",
    "s14_lid_ex_mean",
    "s14_lid_step_max",
    "s14_lid_lapneg_max",
    "s14_lid_lappos_max",
    "s14_lid_downface_max",
    "s14_lid_upface_max",
    "s14_lid_cross_max",
    "s14_lid_relief",
    "s14_lid_coh100",
    "s14_lid_valid",
    # LiDAR interactions: a scarp is a step that persists along strike
    "s14_lid_step_x_coh",
    "s14_lid_face_asym",
    # GeoDAWN radiometrics (stretched uint8/255 + log-ratios + ratio steps)
    "s14_rad_k",
    "s14_rad_th",
    "s14_rad_u",
    "s14_rad_tc",
    "s14_rad_log_th_k",
    "s14_rad_log_u_k",
    "s14_rad_log_u_th",
    "s14_rad_thk_step",
    "s14_rad_uk_step",
    "s14_rad_tc_step",
]


def _grad_mag(arr: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    gy = ndi.gaussian_filter1d(arr, sigma, axis=0, order=1, mode="nearest")
    gx = ndi.gaussian_filter1d(arr, sigma, axis=1, order=1, mode="nearest")
    return np.hypot(gy, gx).astype(np.float32)


def build_or_load_s14_feature_memmap(
    *,
    lidar_tif: str | Path,
    rad_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open disk-backed `(N_fp, 23)` float32 S14 feature matrix."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s14_lsrg_features_v1.dat"
    meta_path = cache_p / "s14_lsrg_features_v1.json"
    n_fp = int(footprint.sum())
    n_cols = len(S14_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("feature_names") == S14_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S14_FEATURE_NAMES), meta

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    col = {n: i for i, n in enumerate(S14_FEATURE_NAMES)}

    with rasterio.open(lidar_tif) as src:
        lid = [src.read(i + 1).astype(np.float32) / 255.0 for i in range(12)]
    valid = lid[11] > 0.5
    lid_names = ["ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max",
                 "downface_max", "upface_max", "cross_max", "relief", "coh100"]
    for i, nm in enumerate(lid_names):
        band = np.where(valid, lid[i], 0.0).astype(np.float32)
        mm[:, col[f"s14_lid_{nm}"]] = band[footprint]
    mm[:, col["s14_lid_valid"]] = valid[footprint].astype(np.float32)
    step = np.where(valid, lid[2], 0.0)
    coh = np.where(valid, lid[9], 0.0)
    mm[:, col["s14_lid_step_x_coh"]] = (step * coh).astype(np.float32)[footprint]
    mm[:, col["s14_lid_face_asym"]] = np.abs(lid[5] - lid[6]).astype(np.float32)[footprint]
    del lid
    gc.collect()

    with rasterio.open(rad_tif) as src:
        k_b = src.read(1).astype(np.float32)
        th_b = src.read(2).astype(np.float32)
        u_b = src.read(3).astype(np.float32)
        tc_b = src.read(4).astype(np.float32)
    mm[:, col["s14_rad_k"]] = (k_b / 255.0)[footprint]
    mm[:, col["s14_rad_th"]] = (th_b / 255.0)[footprint]
    mm[:, col["s14_rad_u"]] = (u_b / 255.0)[footprint]
    mm[:, col["s14_rad_tc"]] = (tc_b / 255.0)[footprint]
    log_th_k = np.log((th_b + 8.0) / (k_b + 8.0)).astype(np.float32)
    log_u_k = np.log((u_b + 8.0) / (k_b + 8.0)).astype(np.float32)
    log_u_th = np.log((u_b + 8.0) / (th_b + 8.0)).astype(np.float32)
    mm[:, col["s14_rad_log_th_k"]] = log_th_k[footprint]
    mm[:, col["s14_rad_log_u_k"]] = log_u_k[footprint]
    mm[:, col["s14_rad_log_u_th"]] = log_u_th[footprint]
    mm[:, col["s14_rad_thk_step"]] = _grad_mag(log_th_k)[footprint]
    mm[:, col["s14_rad_uk_step"]] = _grad_mag(log_u_k)[footprint]
    mm[:, col["s14_rad_tc_step"]] = _grad_mag(tc_b / 255.0)[footprint]
    mm.flush()

    meta = {"n_fp": n_fp, "n_cols": n_cols, "feature_names": list(S14_FEATURE_NAMES),
            "lidar_valid_frac_of_footprint": float(valid[footprint].mean())}
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S14_FEATURE_NAMES), meta


def _assemble(blocks: list[tuple[np.memmap | np.ndarray, list[int] | None]],
              row_idx: np.ndarray) -> np.ndarray:
    parts = []
    for arr, cols in blocks:
        sub = np.asarray(arr[row_idx])
        if cols is not None:
            sub = sub[:, cols]
        parts.append(sub.astype(np.float32))
    return np.hstack(parts)


def fit_and_predict_s14_fold(
    *,
    blocks: list[tuple[np.memmap | np.ndarray, list[int] | None]],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    hard_neg_fp: np.ndarray | None = None,
    max_pos: int = 65_000,
    max_neg: int = 230_000,
    seed: int = 914,
) -> tuple[np.ndarray, dict[str, float]]:
    """Fold-safe HGB ensemble (full + column-subsample + logistic), mirroring
    the S13-PTHA training protocol (`gems91.ptha.fit_and_predict_ptha_oof_fold`)
    but over a generic block list so the S14 memmap and fold-safe catalogue
    features can join the shared static/S11/PTHA stack. Trains ONLY on
    `visible_faults`; `exclude_mask` (test region + withheld + buffer) never
    contributes a training row of either class.
    """
    rng = np.random.default_rng(seed)
    pos_fp = visible_faults[footprint] & (~exclude_mask[footprint])
    neg_fp = (~visible_faults[footprint]) & (~exclude_mask[footprint])
    pos_all = np.flatnonzero(pos_fp)
    neg_all = np.flatnonzero(neg_fp)
    pi_true = float(pos_all.size) / float(max(pos_all.size + neg_all.size, 1))

    pos_idx = (np.sort(rng.choice(pos_all, size=max_pos, replace=False))
               if pos_all.size > max_pos else pos_all)
    if hard_neg_fp is not None:
        hv = np.asarray(hard_neg_fp, dtype=np.float32)[neg_all]
        thr = float(np.percentile(hv, 75))
        hard_pool, easy_pool = neg_all[hv >= thr], neg_all[hv < thr]
        del hv
    else:
        hard_pool, easy_pool = neg_all[:0], neg_all
    n_hard = min(max_neg // 2, hard_pool.size)
    n_easy = min(max_neg - n_hard, easy_pool.size)
    neg_hard = (np.sort(rng.choice(hard_pool, size=n_hard, replace=False))
                if hard_pool.size > n_hard else hard_pool)
    neg_easy = (np.sort(rng.choice(easy_pool, size=n_easy, replace=False))
                if easy_pool.size > n_easy else easy_pool)
    neg_idx = np.concatenate([neg_hard, neg_easy])
    w_neg = np.concatenate([np.full(neg_hard.size, 0.55, np.float32),
                            np.full(neg_easy.size, 1.45, np.float32)])

    X_train = np.vstack([_assemble(blocks, pos_idx), _assemble(blocks, neg_idx)])
    y_train = np.concatenate([np.ones(pos_idx.size, np.int32),
                              np.zeros(neg_idx.size, np.int32)])
    w_train = np.concatenate([np.ones(pos_idx.size, np.float32), w_neg])
    pi_sample = float(pos_idx.size) / float(w_train.sum())

    models = []
    hgb_full = HistGradientBoostingClassifier(
        loss="log_loss", learning_rate=0.055, max_iter=230, max_leaf_nodes=41,
        min_samples_leaf=85, l2_regularization=3.0, max_bins=255,
        early_stopping=False, random_state=seed)
    hgb_full.fit(X_train, y_train, sample_weight=w_train)
    models.append(("full", hgb_full, 0.50))
    hgb_col = HistGradientBoostingClassifier(
        loss="log_loss", learning_rate=0.055, max_iter=220, max_leaf_nodes=35,
        max_depth=7, min_samples_leaf=100, l2_regularization=4.5,
        max_features=0.55, max_bins=255, early_stopping=False,
        random_state=seed + 101)
    hgb_col.fit(X_train, y_train, sample_weight=w_train)
    models.append(("colsub", hgb_col, 0.30))

    med = np.median(X_train, axis=0)
    scale = np.median(np.abs(X_train - med), axis=0) * 1.4826 + 1e-5
    lr = LogisticRegression(C=0.25, max_iter=250, random_state=seed)
    lr.fit(np.clip((X_train - med) / scale, -6, 6), y_train, sample_weight=w_train)
    models.append(("lr", lr, 0.20))
    del X_train, y_train, w_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.zeros(n_fp, dtype=np.float32)
    chunk = 400_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        idx = np.arange(s, e)
        Xc = _assemble(blocks, idx)
        acc = np.zeros(e - s, dtype=np.float32)
        for name, mdl, wgt in models:
            Xin = np.clip((Xc - med) / scale, -6, 6) if name == "lr" else Xc
            acc += np.float32(wgt) * mdl.predict_proba(Xin)[:, 1].astype(np.float32)
        pred_fp[s:e] = acc
        del Xc, acc
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = pred_fp
    return out, {"pi_true": pi_true, "pi_sample": pi_sample,
                  "n_pos_train": int(pos_all.size), "n_neg_train": int(neg_all.size)}


def rank_pct_fp(vals_fp: np.ndarray) -> np.ndarray:
    """Footprint rank-percentile in [0,1] (average ranks, O(N log N))."""
    order = np.argsort(vals_fp, kind="mergesort")
    ranks = np.empty(vals_fp.size, dtype=np.float64)
    ranks[order] = np.arange(vals_fp.size, dtype=np.float64)
    # average ties
    sv = vals_fp[order]
    i = 0
    while i < sv.size:
        j = i + 1
        while j < sv.size and sv[j] == sv[i]:
            j += 1
        if j - i > 1:
            ranks[order[i:j]] = 0.5 * (i + j - 1)
        i = j
    return (ranks / max(vals_fp.size - 1, 1)).astype(np.float32)


def corroboration_gate(
    prob_2d: np.ndarray,
    family_surfaces_2d: list[np.ndarray],
    footprint: np.ndarray,
    *,
    floor: float = 0.30,
) -> np.ndarray:
    """H14-5 / E2: multiply the posterior by `floor + (1-floor)*agree`, where
    `agree` is the mean footprint rank-percentile of physically independent
    crest families (magnetic/gravity crest, LiDAR scarp, radiometric step).
    Label-free; computed from feature surfaces only.
    """
    agree_fp = np.zeros(int(footprint.sum()), dtype=np.float32)
    for fam in family_surfaces_2d:
        agree_fp += rank_pct_fp(np.asarray(fam, dtype=np.float32)[footprint])
    agree_fp /= float(len(family_surfaces_2d))
    out = np.zeros_like(prob_2d, dtype=np.float32)
    mult = np.float32(floor) + np.float32(1.0 - floor) * agree_fp
    out[footprint] = prob_2d[footprint] * mult
    return out
