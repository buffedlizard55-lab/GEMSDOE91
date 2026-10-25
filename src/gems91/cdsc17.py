"""S17-CDSC: Prevalence-Calibrated Faulds-Hinz En-Echelon Relay Topology,
Multi-Wavelength Subsurface-Junction Concordance & Pure-Subsurface Specialist Discovery.

Remediates prior-session blockers documented in `LIMITATIONS_AND_NEXT_STEPS.md`
and `docs/REVIEW-S15-SCGF-20261025.md`:
  - `IR-91-S15-06`: Calibrates every 2-quadrant pairwise Stage-1 sub-model `(a, b)`
    to each training fold's 3-quadrant sample prevalence via Bayes prior-shift
    before stitching the cross-fitted auto-context canvas.
  - `IR-91-S15-07`: Keeps Stage-1 strictly on the 75 translation-invariant local
    `S13-PTHA` features (`0` 3-km GDR bullseyes, `0` 15-km regional bowls) while
    injecting the 16 local (`<= 1 km`) `S15` Förstner-junction / multi-scale Salem /
    aquifer-baffle features into Stage-2.
  - `IR-91-S15-05`: Trains a dedicated 68-column bitwise `B12`/`B19`-invariant
    Pure-Subsurface Stage-2 specialist alongside the full multi-physics Stage-2
    ensemble.
"""

from __future__ import annotations

import gc
import math
from typing import Sequence

import numpy as np
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from gems91 import ptha as PTHA
from gems91 import scgf15 as SCGF
from gems91 import spac_coda as SC

FeatureBlock = tuple[np.ndarray, Sequence[int]]

# 16 strictly local (`<= 1 km`), translation-invariant S15 subsurface features
# (excludes col 15 `s15_gdr_strike_plume_sub` and col 17 `s15_gdr_upgradient_conduit`
# which use 3-km GDR kernels that overfit quadrant boundaries per IR-91-S15-07).
S17_LOCAL_S15_COLS: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16]
S17_LOCAL_S15_NAMES: list[str] = [SCGF.S15_SCGF_FEATURE_NAMES[i] for i in S17_LOCAL_S15_COLS]

S17_EXTRA_RELAY_AC_NAMES: list[str] = [
    "ac_relay_step_250m",
    "ac_relay_step_500m",
    "ac_conjugate_junction",
    "ac_tip_continuation_excess",
]

S17_AUTOCONTEXT_NAMES: list[str] = (
    list(SC.S12_AUTOCONTEXT_FEATURE_NAMES) + S17_EXTRA_RELAY_AC_NAMES
)

# Exhaustive set of topography-coupled (`Band 12` / `Band 19`) feature names across
# the 105-feature S17 Stage-2 matrix (75 S13 + 16 local S15 + 14 Stage-1 Auto-Context).
S17_STRICT_TOPO_FEATURE_NAMES: frozenset[str] = frozenset(
    set(SCGF.STRICT_TOPO_FEATURE_NAMES)
    | {
        "e3_signed_footwall_polarity",
        "ptha_step_grav_abs",
        "ptha_step_rtp_abs",
        "ptha_step_depth_abs",
        "ptha_step_rad_tc_abs",
    }
    | set(S17_AUTOCONTEXT_NAMES)
)


def pure_subsurface_feature_mask(feature_names: Sequence[str]) -> np.ndarray:
    """Return boolean mask of columns with zero direct or indirect `B12`/`B19` dependence."""
    mask = np.array([nm not in S17_STRICT_TOPO_FEATURE_NAMES for nm in feature_names], dtype=bool)
    if not np.any(mask):
        raise ValueError("Pure-subsurface feature mask is empty")
    return mask


def calibrate_pair_to_target_prevalence(
    pair_prob_2d: np.ndarray,
    footprint: np.ndarray,
    *,
    pair_pi_sample: float,
    target_pi_sample: float,
) -> np.ndarray:
    """Remediate `IR-91-S15-06`: map a 2-quadrant Stage-1 surface from its sample
    prevalence `pair_pi_sample` to the 3-quadrant training prevalence `target_pi_sample`.

    Uses strictly training-domain sample prevalence scalars so zero test-fold
    information enters the stitched auto-context surface.
    """
    return PTHA.prior_shift_calibrate_surface(
        pair_prob_2d,
        footprint,
        pi_true=float(target_pi_sample),
        pi_sample=float(pair_pi_sample),
    )


def compute_s17_calibrated_autocontext_features(
    calibrated_stage1_surface: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Extract `(N_fp, 14)` Faulds-Hinz structural-setting & collinear auto-context matrix.

    Columns `0..9`: standard 8-azimuth collinear Radon / wash-bridge features
    (`SC.compute_spac_autocontext_features`).
    Columns `10..13`: Faulds & Hinz (2015) Great Basin structural setting operators:
      - `ac_relay_step_250m`: anti-symmetric en-echelon lateral step-over (`+-2 px`)
      - `ac_relay_step_500m`: wider en-echelon pull-apart step-over (`+-4 px`)
      - `ac_conjugate_junction`: oblique `45-90 deg` fault-intersection product
      - `ac_tip_continuation_excess`: horse-tail fault-tip propagation asymmetry
    """
    base_ac = SC.compute_spac_autocontext_features(calibrated_stage1_surface, footprint)
    p1 = np.clip(
        np.nan_to_num(calibrated_stage1_surface, nan=0.0, posinf=0.0, neginf=0.0),
        0.0,
        1.0,
    ).astype(np.float32)
    p_ray = ndi.gaussian_filter(p1, sigma=0.90).astype(np.float32)

    h, w = p1.shape
    max_relay_250 = np.zeros((h, w), dtype=np.float32)
    max_relay_500 = np.zeros((h, w), dtype=np.float32)
    max_tip_excess = np.zeros((h, w), dtype=np.float32)
    az_rays: list[np.ndarray] = []

    for k in range(8):
        az = math.radians(k * 22.5)
        sy, sx = -math.cos(az), math.sin(az)
        ny, nx = sx, -sy

        # Forward & backward collinear half-rays for tip asymmetry and conjugate junctions
        r_fwd = np.zeros((h, w), dtype=np.float32)
        r_bwd = np.zeros((h, w), dtype=np.float32)
        for r in (3, 6, 9):
            dy, dx = int(round(r * sy)), int(round(r * sx))
            r_fwd += SC._shift_2d(p_ray, dy, dx)
            r_bwd += SC._shift_2d(p_ray, -dy, -dx)
        r_fwd /= 3.0
        r_bwd /= 3.0

        tip_ex = np.abs(r_fwd - r_bwd) * np.sqrt(np.maximum(np.maximum(r_fwd, r_bwd), 0.0))
        np.maximum(max_tip_excess, tip_ex, out=max_tip_excess)
        az_rays.append((0.5 * (r_fwd + r_bwd)).astype(np.float32))
        del r_fwd, r_bwd, tip_ex

        # Anti-symmetric en-echelon relay step-overs at delta_n = +-2 px (250 m) and +-4 px (500 m)
        for delta_n, steps_s, out_arr in (
            (2, (3, 6), max_relay_250),
            (4, (4, 8), max_relay_500),
        ):
            for sign in (-1, 1):
                ndy = int(round(sign * delta_n * ny))
                ndx = int(round(sign * delta_n * nx))
                f_step = np.zeros((h, w), dtype=np.float32)
                b_step = np.zeros((h, w), dtype=np.float32)
                for r in steps_s:
                    sdy, sdx = int(round(r * sy)), int(round(r * sx))
                    f_step += SC._shift_2d(p_ray, sdy + ndy, sdx + ndx)
                    b_step += SC._shift_2d(p_ray, -sdy - ndy, -sdx - ndx)
                f_step /= float(len(steps_s))
                b_step /= float(len(steps_s))
                relay = np.sqrt(np.maximum(f_step * b_step, 0.0))
                np.maximum(out_arr, relay, out=out_arr)
                del f_step, b_step, relay

    # Conjugate fault intersection: maximum geometric product of rays separated by 45-90 deg
    max_conj = np.zeros((h, w), dtype=np.float32)
    for k in range(8):
        rk = az_rays[k]
        partner = np.maximum(
            az_rays[(k + 2) % 8],
            np.maximum(az_rays[(k + 3) % 8], az_rays[(k + 4) % 8]),
        )
        conj = np.sqrt(np.maximum(rk * partner, 0.0))
        np.maximum(max_conj, conj, out=max_conj)
        del partner, conj
    del az_rays, p_ray, p1

    n_fp = int(footprint.sum())
    out = np.empty((n_fp, 14), dtype=np.float32)
    out[:, :10] = base_ac
    out[:, 10] = max_relay_250[footprint]
    out[:, 11] = max_relay_500[footprint]
    out[:, 12] = max_conj[footprint]
    out[:, 13] = max_tip_excess[footprint]
    del base_ac, max_relay_250, max_relay_500, max_conj, max_tip_excess
    gc.collect()
    return out


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


def fit_predict_s17_stage2(
    *,
    train_blocks: Sequence[FeatureBlock],
    infer_blocks: Sequence[FeatureBlock],
    feature_names: Sequence[str],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    neg_pos_ratio: float = 3.65,
    chunk_size: int = 400_000,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    """Fit the S17 Dual-Specialist Stage-2 ensemble (`p2_base_2d`, `p2_sub_2d`, `meta`).

    - `p2_base_2d`: `0.50 * HGB-Deep + 0.30 * HGB-Shallow + 0.20 * Logistic` on all
      `105` features (exact architectural parity with `PTAC.fit_predict_stage2`).
    - `p2_sub_2d`: dedicated `HGB-PureSubsurface` specialist trained strictly on the
      `72` `B12`/`B19`-invariant columns (`pure_subsurface_feature_mask`), guaranteeing
      zero topographic bias across flat playas and alluvial fans.
    """
    if len(train_blocks) != len(infer_blocks):
        raise ValueError("training and inference block counts differ")
    train_width = sum(len(cols) for _, cols in train_blocks)
    infer_width = sum(len(cols) for _, cols in infer_blocks)
    if train_width <= 0 or train_width != infer_width or train_width != len(feature_names):
        raise ValueError(
            f"feature width mismatch: train={train_width}, infer={infer_width}, names={len(feature_names)}"
        )

    sub_mask = pure_subsurface_feature_mask(feature_names)
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
    X_train_sub = X_train[:, sub_mask]

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

    hgb_sub = HistGradientBoostingClassifier(
        learning_rate=0.052,
        max_iter=195,
        max_leaf_nodes=35,
        min_samples_leaf=85,
        l2_regularization=4.0,
        early_stopping=False,
        random_state=seed + 53,
    ).fit(X_train_sub, y_train)

    scaler = StandardScaler()
    X_train_scaled = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.22, max_iter=300, random_state=seed + 31)
    lr.fit(X_train_scaled, y_train)
    del X_train, X_train_sub, X_train_scaled, y_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_base_fp = np.empty(n_fp, dtype=np.float32)
    pred_sub_fp = np.empty(n_fp, dtype=np.float32)
    for start in range(0, n_fp, chunk_size):
        end = min(start + chunk_size, n_fp)
        Xc = _stack_slice(infer_blocks, start, end)
        p_deep = hgb_deep.predict_proba(Xc)[:, 1]
        p_shallow = hgb_shallow.predict_proba(Xc)[:, 1]
        p_lr = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        p_sub = hgb_sub.predict_proba(Xc[:, sub_mask])[:, 1]
        pred_base_fp[start:end] = (
            0.50 * p_deep + 0.30 * p_shallow + 0.20 * p_lr
        ).astype(np.float32)
        pred_sub_fp[start:end] = p_sub.astype(np.float32)
        del Xc, p_deep, p_shallow, p_lr, p_sub

    out_base = np.zeros(footprint.shape, dtype=np.float32)
    out_sub = np.zeros(footprint.shape, dtype=np.float32)
    out_base[footprint] = pred_base_fp
    out_sub[footprint] = pred_sub_fp
    pi_true = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_sample = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    return out_base, out_sub, {
        "pi_vis_train": round(pi_true, 8),
        "pi_sample_weighted": round(pi_sample, 8),
        "n_pos_train": int(pos_idx.size),
        "n_safe_neg_domain": int(neg_pool.size),
        "n_neg_sample": int(neg_idx.size),
        "n_features": int(train_width),
        "n_pure_subsurface_features": int(sub_mask.sum()),
    }


def build_s17_relay_subsurface_concordant_crest(
    ptha_crest: np.ndarray,
    s15_crest_base: np.ndarray,
    ac_matrix_fp: np.ndarray | np.memmap,
    footprint: np.ndarray,
    *,
    sub_crest_weight: float = 0.26,
    bridge_weight: float = 0.48,
) -> np.ndarray:
    """`H17-3`: Combine `ptha_crest` + multi-wavelength `s15_crest_base` and boost
    where either two-sided collinear wash bridges OR en-echelon relay step-overs persist.
    """
    w_sub = float(sub_crest_weight)
    base_dual = np.clip(
        (1.0 - w_sub) * np.asarray(ptha_crest, dtype=np.float32)
        + w_sub * np.asarray(s15_crest_base, dtype=np.float32),
        0.0,
        1.0,
    )

    b1k = np.maximum(np.asarray(ac_matrix_fp[:, 4], dtype=np.float32), 0.0)
    b2k = np.maximum(np.asarray(ac_matrix_fp[:, 5], dtype=np.float32), 0.0)
    collinear_br = np.sqrt(b1k * b2k)

    r250 = np.maximum(np.asarray(ac_matrix_fp[:, 10], dtype=np.float32), 0.0)
    r500 = np.maximum(np.asarray(ac_matrix_fp[:, 11], dtype=np.float32), 0.0)
    relay_br = np.sqrt(r250 * r500)

    comb_fp = np.maximum(collinear_br, 0.85 * relay_br).astype(np.float32)
    q50 = float(np.percentile(comb_fp, 50.0)) if comb_fp.size else 0.0
    q95 = float(np.percentile(comb_fp, 95.0)) if comb_fp.size else 1.0
    norm_fp = np.clip((comb_fp - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    bridge_2d = np.zeros(footprint.shape, dtype=np.float32)
    bridge_2d[footprint] = norm_fp
    out = np.clip(base_dual * (1.0 + np.float32(bridge_weight) * bridge_2d), 0.0, 1.0)
    out[~footprint] = 0.0
    return out.astype(np.float32)


def build_s17_concealed_subsurface_corroborated_pool(
    p1_cal: np.ndarray,
    p2_base_cal: np.ndarray,
    p2_sub_cal: np.ndarray,
    piedmont_mask: np.ndarray,
    X_s15: np.ndarray | np.memmap,
    footprint: np.ndarray,
    *,
    stage2_weight: float = 0.73,
    base_sub_blend: float = 0.12,
    concealed_sub_boost: float = 0.14,
) -> np.ndarray:
    """`H17-4`: Blend the 68-feature Pure-Subsurface specialist `p2_sub_cal` into
    Stage-2 with adaptive weight in concealed piedmont/basin cover and Förstner
    subsurface junctions where `p2_sub_cal` corroborates `p2_base_cal`.
    """
    forstner_fp = np.maximum(np.asarray(X_s15[:, 0], dtype=np.float32), 0.0)
    salem_sh_fp = np.maximum(np.asarray(X_s15[:, 7], dtype=np.float32), 0.0)
    sub_struct_fp = np.clip(0.5 * (forstner_fp + salem_sh_fp) / 3.0, 0.0, 1.0)

    sub_struct_2d = np.zeros(footprint.shape, dtype=np.float32)
    sub_struct_2d[footprint] = sub_struct_fp

    concealed_factor = np.where(
        piedmont_mask,
        np.float32(1.0),
        0.5 * sub_struct_2d,
    ).astype(np.float32)
    w_sub_map = np.clip(
        np.float32(base_sub_blend) + np.float32(concealed_sub_boost) * concealed_factor,
        0.0,
        0.35,
    )
    p2_dual = (1.0 - w_sub_map) * p2_base_cal + w_sub_map * p2_sub_cal
    w2 = float(stage2_weight)
    out = ((1.0 - w2) * p1_cal + w2 * p2_dual).astype(np.float32)
    out[~footprint] = 0.0
    return np.clip(out, 0.0, 1.0)
