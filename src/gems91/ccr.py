"""Compensated Conductivity Residual (CCR91) feature lane.

The transform is label-free: it residualizes sponsor band 17 conductivity against
sponsor band 15 basement depth, then derives narrow residual contacts and requires
potential-field corroboration.  No catalogue or prior submission raster enters
these features.
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
from sklearn.preprocessing import StandardScaler

from . import dd_vtc_pu as DD

CCR_FEATURE_NAMES = [
    "ccr_cond_depth_residual",
    "ccr_residual_grad_200m",
    "ccr_residual_dog_1km",
    "ccr_residual_gravity_alignment",
    "ccr_residual_gravity_joint",
    "ccr_concealed_contact_joint",
]


def _norm01(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = arr[footprint][::20]
    q50, q95 = np.percentile(vals, [50.0, 95.0])
    return np.clip((arr - float(q50)) / max(float(q95 - q50), 1e-6), 0.0, 1.0).astype(np.float32)


def _depth_conditional_residual(
    conductivity: np.ndarray,
    depth: np.ndarray,
    footprint: np.ndarray,
    *,
    n_bins: int = 64,
) -> tuple[np.ndarray, dict]:
    """Robustly remove the broad B17-on-B15 relation using depth quantile bins.

    Quantile bins keep support approximately balanced.  Bin medians are smoothed
    along depth with a 1-D Gaussian before subtraction, avoiding sharp artificial
    residual boundaries at bin edges.  This uses no fault labels.
    """
    d = depth[footprint].astype(np.float64)
    c = conductivity[footprint].astype(np.float64)
    edges = np.unique(np.quantile(d, np.linspace(0.0, 1.0, n_bins + 1)))
    if edges.size < 4:
        raise ValueError("depth_to_base has too few distinct values for CCR residualization")
    # digitize against internal edges; valid bins are [0, n_effective-1]
    bins = np.digitize(d, edges[1:-1], right=False)
    n_eff = edges.size - 1
    med = np.empty(n_eff, dtype=np.float64)
    global_med = float(np.median(c))
    for i in range(n_eff):
        vi = c[bins == i]
        med[i] = float(np.median(vi)) if vi.size else global_med
    med_smooth = ndi.gaussian_filter1d(med, sigma=1.25, mode="nearest")
    residual_fp = c - med_smooth[bins]
    r_med = float(np.median(residual_fp))
    r_iqr = float(np.percentile(residual_fp, 75) - np.percentile(residual_fp, 25))
    residual_fp = np.clip((residual_fp - r_med) / max(r_iqr / 1.349, 1e-6), -6.0, 6.0)
    residual = np.zeros(footprint.shape, dtype=np.float32)
    residual[footprint] = residual_fp.astype(np.float32)
    return residual, {
        "method": "64-quantile-bin median B17(cond_surf)|B15(depth_to_base), 1-D Gaussian bin smoothing sigma=1.25",
        "requested_bins": n_bins,
        "effective_bins": int(n_eff),
        "residual_median_before_scaling": r_med,
        "residual_iqr_before_scaling": r_iqr,
    }


def build_or_load_ccr_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build/open the six-column CCR feature matrix for footprint pixels."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "ccr91_features_v1.dat"
    meta_path = cache_p / "ccr91_features_v1.json"
    n_fp = int(footprint.sum())
    n_cols = len(CCR_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == CCR_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            return (
                np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols)),
                list(CCR_FEATURE_NAMES),
                meta,
            )

    with rasterio.open(features_tif) as src:
        grav_slope = np.maximum(DD._clean_band_edt(src.read(5), footprint), 0.0)
        grav = DD._clean_band_edt(src.read(13), footprint)
        depth = np.maximum(DD._clean_band_edt(src.read(15), footprint), 0.0)
        conductivity = DD._clean_band_edt(src.read(17), footprint)
        topo_slope = np.maximum(DD._clean_band_edt(src.read(19), footprint), 0.0)

    residual, residual_meta = _depth_conditional_residual(conductivity, depth, footprint)
    residual_s = ndi.gaussian_filter(residual, sigma=1.5)
    ry, rx = np.gradient(residual_s)
    residual_grad = np.hypot(ry, rx).astype(np.float32)
    residual_dog = np.abs(
        ndi.gaussian_filter(residual, sigma=2.0) - ndi.gaussian_filter(residual, sigma=10.0)
    ).astype(np.float32)

    grav_s = ndi.gaussian_filter(grav, sigma=2.5)
    gy, gx = np.gradient(grav_s)
    align = np.abs(ry * gy + rx * gx) / (
        (np.hypot(ry, rx) + 1e-5) * (np.hypot(gy, gx) + 1e-5)
    )
    align = np.clip(align, 0.0, 1.0).astype(np.float32)

    grad_n = _norm01(residual_grad, footprint)
    dog_n = _norm01(residual_dog, footprint)
    grav_n = np.maximum(_norm01(grav_slope, footprint), _norm01(np.hypot(gy, gx), footprint))
    gravity_joint = (np.sqrt(grad_n * grav_n) * (0.55 + 0.45 * align)).astype(np.float32)

    depth_n = np.clip((depth - 220.0) / 700.0, 0.0, 1.0).astype(np.float32)
    low_relief = np.clip((10.5 - topo_slope) / 8.0, 0.0, 1.0).astype(np.float32)
    concealed_joint = (
        (0.55 * gravity_joint + 0.25 * dog_n + 0.20 * grad_n)
        * (0.35 + 0.65 * np.maximum(depth_n, low_relief))
    ).astype(np.float32)

    arrays = [residual, residual_grad, residual_dog, align, gravity_joint, concealed_joint]
    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    for j, arr in enumerate(arrays):
        vals = np.nan_to_num(arr[footprint], nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        if not np.isfinite(vals).all():
            raise RuntimeError(f"nonfinite CCR feature {CCR_FEATURE_NAMES[j]}")
        mm[:, j] = vals
    mm.flush()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": CCR_FEATURE_NAMES,
        "label_free": True,
        "source_bands": [5, 13, 15, 17, 19],
        "residualization": residual_meta,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols)), list(CCR_FEATURE_NAMES), meta


def fit_and_predict_ccr_oof_fold(
    X_static: np.memmap | np.ndarray,
    static_cols: list[int],
    X_s11: np.memmap | np.ndarray,
    s11_cols: list[int],
    X_ccr: np.memmap | np.ndarray,
    ccr_cols: list[int],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    seed: int,
    max_neg_samples: int = 165_000,
) -> np.ndarray:
    """S11-E2's frozen HGB+LR learner with the preregistered CCR columns added."""
    rng = np.random.default_rng(seed)
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]
    d_vis = ndi.distance_transform_edt(~visible_faults)
    safe_neg = (~vis_fp) & (~excl_fp) & (d_vis[footprint] > 3.5)
    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    neg_pool = np.flatnonzero(safe_neg)
    if neg_pool.size > max_neg_samples:
        neg_idx = np.sort(rng.choice(neg_pool, size=max_neg_samples, replace=False))
    else:
        neg_idx = neg_pool
    train_idx = np.concatenate([pos_idx, neg_idx])
    y = np.concatenate([np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)])

    def stack_rows(rows: slice | np.ndarray) -> np.ndarray:
        return np.hstack([
            np.asarray(X_static[rows][:, static_cols], dtype=np.float32),
            np.asarray(X_s11[rows][:, s11_cols], dtype=np.float32),
            np.asarray(X_ccr[rows][:, ccr_cols], dtype=np.float32),
        ])

    Xtr = stack_rows(train_idx)
    hgb = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=190,
        max_leaf_nodes=35,
        min_samples_leaf=75,
        l2_regularization=3.0,
        random_state=seed,
    )
    hgb.fit(Xtr, y)
    scaler = StandardScaler()
    Xtr_sc = np.clip(scaler.fit_transform(Xtr), -6.0, 6.0)
    lr = LogisticRegression(C=0.22, max_iter=300, random_state=seed)
    lr.fit(Xtr_sc, y)
    del Xtr, Xtr_sc
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    for start in range(0, n_fp, 450_000):
        end = min(start + 450_000, n_fp)
        Xc = stack_rows(slice(start, end))
        p_hgb = hgb.predict_proba(Xc)[:, 1]
        p_lr = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        pred_fp[start:end] = (0.78 * p_hgb + 0.22 * p_lr).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = pred_fp
    return out


def ccr_edge_field(X_ccr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Label-free CCR corroboration surface in [0,1] for preregistered E2."""
    grad = np.asarray(X_ccr[:, 1], dtype=np.float32)
    dog = np.asarray(X_ccr[:, 2], dtype=np.float32)
    grav = np.asarray(X_ccr[:, 4], dtype=np.float32)
    concealed = np.asarray(X_ccr[:, 5], dtype=np.float32)

    def norm(v: np.ndarray) -> np.ndarray:
        q50, q95 = np.percentile(v[::20], [50.0, 95.0])
        return np.clip((v - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    field_fp = np.clip(0.25 * norm(grad) + 0.15 * norm(dog) + 0.30 * norm(grav) + 0.30 * norm(concealed), 0, 1)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = field_fp
    return out
