"""S14-PTAC: cross-fit posterior-topology auto-context utilities.

The module contains no holdout labels, registry rasters, prior-submission pixels, or
metric implementation. It only fits a Stage-2 classifier from caller-supplied,
fold-safe feature blocks and combines calibrated posterior surfaces. Scoring and
writing remain in the repository's shared evaluator and submission writer.
"""

from __future__ import annotations

import gc
from typing import Sequence

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


FeatureBlock = tuple[np.ndarray, Sequence[int]]


def _stack_rows(blocks: Sequence[FeatureBlock], rows: np.ndarray) -> np.ndarray:
    active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    if not active:
        raise ValueError("at least one non-empty feature block is required")
    return np.hstack(
        [np.asarray(arr[rows][:, cols], dtype=np.float32) for arr, cols in active]
    )


def _stack_slice(blocks: Sequence[FeatureBlock], start: int, end: int) -> np.ndarray:
    active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    if not active:
        raise ValueError("at least one non-empty feature block is required")
    return np.hstack(
        [np.asarray(arr[start:end][:, cols], dtype=np.float32) for arr, cols in active]
    )


def fit_predict_stage2(
    *,
    train_blocks: Sequence[FeatureBlock],
    infer_blocks: Sequence[FeatureBlock],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    neg_pos_ratio: float = 3.65,
    chunk_size: int = 400_000,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Fit a prior-invariant Stage-2 HGB/HGB/LR ensemble and predict the footprint.

    `train_blocks` and `infer_blocks` must have identical dimensions and feature
    ordering. Their final block may differ: full-map fitting uses cross-fitted
    auto-context for training and full Stage-1 auto-context for inference. For an
    OOF fold they are the same fold-safe stitched matrix.
    """
    if len(train_blocks) != len(infer_blocks):
        raise ValueError("training and inference block counts differ")
    train_width = sum(len(cols) for _, cols in train_blocks)
    infer_width = sum(len(cols) for _, cols in infer_blocks)
    if train_width <= 0 or train_width != infer_width:
        raise ValueError(
            f"feature widths must be positive and equal, got {train_width} and {infer_width}"
        )

    rng = np.random.default_rng(seed)
    visible = np.asarray(visible_faults, dtype=bool) & footprint
    excluded = np.asarray(exclude_mask, dtype=bool) | (~footprint)

    d_vis = ndi.distance_transform_edt(~visible)
    pos_fp = visible[footprint] & (~excluded[footprint])
    neg_fp = (~visible[footprint]) & (~excluded[footprint]) & (d_vis[footprint] > 3.5)
    pos_idx = np.flatnonzero(pos_fp)
    neg_pool = np.flatnonzero(neg_fp)
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Stage-2 training requires both positive and safe-negative pixels")

    target_neg = min(int(round(float(neg_pos_ratio) * pos_idx.size)), neg_pool.size)
    neg_idx = (
        np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
        if target_neg < neg_pool.size
        else neg_pool
    )
    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate(
        [
            np.ones(pos_idx.size, dtype=np.int32),
            np.zeros(neg_idx.size, dtype=np.int32),
        ]
    )
    X_train = _stack_rows(train_blocks, train_idx)

    hgb_deep = HistGradientBoostingClassifier(
        learning_rate=0.052,
        max_iter=210,
        max_leaf_nodes=41,
        min_samples_leaf=70,
        l2_regularization=3.2,
        early_stopping=False,
        random_state=seed,
    ).fit(X_train, y_train)
    hgb_shallow = HistGradientBoostingClassifier(
        learning_rate=0.048,
        max_iter=180,
        max_leaf_nodes=23,
        max_depth=6,
        min_samples_leaf=110,
        l2_regularization=6.5,
        early_stopping=False,
        random_state=seed + 17,
    ).fit(X_train, y_train)

    scaler = StandardScaler()
    X_train_scaled = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.22, max_iter=300, random_state=seed + 31)
    lr.fit(X_train_scaled, y_train)
    del X_train, X_train_scaled, y_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    for start in range(0, n_fp, chunk_size):
        end = min(start + chunk_size, n_fp)
        Xc = _stack_slice(infer_blocks, start, end)
        p_deep = hgb_deep.predict_proba(Xc)[:, 1]
        p_shallow = hgb_shallow.predict_proba(Xc)[:, 1]
        p_lr = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        pred_fp[start:end] = (
            0.50 * p_deep + 0.30 * p_shallow + 0.20 * p_lr
        ).astype(np.float32)
        del Xc, p_deep, p_shallow, p_lr

    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = pred_fp
    pi_true = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_sample = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    return out, {
        "pi_vis_train": round(pi_true, 8),
        "pi_sample_weighted": round(pi_sample, 8),
        "n_pos_train": int(pos_idx.size),
        "n_safe_neg_domain": int(neg_pool.size),
        "n_neg_sample": int(neg_idx.size),
        "n_features": int(train_width),
    }


def arithmetic_probability_pool(
    stage1_calibrated: np.ndarray,
    stage2_calibrated: np.ndarray,
    footprint: np.ndarray,
    *,
    stage2_weight: float = 0.72,
) -> np.ndarray:
    """Frozen H14-1 calibrated probability pool."""
    w2 = float(stage2_weight)
    if not (0.0 <= w2 <= 1.0):
        raise ValueError("stage2_weight must be in [0,1]")
    out = (
        (1.0 - w2) * np.asarray(stage1_calibrated, dtype=np.float32)
        + w2 * np.asarray(stage2_calibrated, dtype=np.float32)
    ).astype(np.float32)
    out[~footprint] = 0.0
    return np.clip(out, 0.0, 1.0)


def log_opinion_pool(
    stage1_calibrated: np.ndarray,
    stage2_calibrated: np.ndarray,
    footprint: np.ndarray,
    *,
    stage2_weight: float = 0.65,
) -> np.ndarray:
    """Frozen H14-3 weighted geometric pool in odds space."""
    w2 = float(stage2_weight)
    if not (0.0 <= w2 <= 1.0):
        raise ValueError("stage2_weight must be in [0,1]")
    eps = np.float32(1e-5)
    p1 = np.clip(np.asarray(stage1_calibrated, dtype=np.float32), eps, 1.0 - eps)
    p2 = np.clip(np.asarray(stage2_calibrated, dtype=np.float32), eps, 1.0 - eps)
    logit = (1.0 - w2) * np.log(p1 / (1.0 - p1)) + w2 * np.log(p2 / (1.0 - p2))
    out = (1.0 / (1.0 + np.exp(-np.clip(logit, -20.0, 20.0)))).astype(np.float32)
    out[~footprint] = 0.0
    return out


def bridge_concordant_crest(
    base_crest: np.ndarray,
    bridge_900m: np.ndarray,
    bridge_2km: np.ndarray,
    footprint: np.ndarray,
    *,
    bridge_weight: float = 0.45,
) -> np.ndarray:
    """H14-2: boost a physical crest only where two-sided topology persists.

    This cannot create a crest from posterior context alone: `base_crest` remains
    the multiplicative support, reducing straight-channel/road interpolation.
    """
    base = np.clip(np.asarray(base_crest, dtype=np.float32), 0.0, 1.0)
    bridge = np.sqrt(
        np.maximum(np.asarray(bridge_900m, dtype=np.float32), 0.0)
        * np.maximum(np.asarray(bridge_2km, dtype=np.float32), 0.0)
    ).astype(np.float32)
    valid = bridge[footprint]
    if valid.size:
        q50 = float(np.percentile(valid, 50.0))
        q95 = float(np.percentile(valid, 95.0))
        bridge_norm = np.clip((bridge - q50) / max(q95 - q50, 1e-6), 0.0, 1.0)
    else:
        bridge_norm = np.zeros_like(bridge)
    out = np.clip(base * (1.0 + float(bridge_weight) * bridge_norm), 0.0, 1.0)
    out[~footprint] = 0.0
    return out.astype(np.float32)
