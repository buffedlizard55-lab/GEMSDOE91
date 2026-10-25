"""VENT91: Piedmont Flexure + Depth-Conditioned Conductivity + Bouguer-Stripped Gravity

All VENT features are 100% label-free (computed strictly from the 19 official
competition bands of gems-geodawn-numerical-features.tif and the
sample_submission.tif footprint mask; never touches existing_faults.tif,
SGMC, or any prior submission raster).

New physical features (VENT-1..3):
 - VENT-1: profile curvature of B12 detrended elevation along regional-slope-
   normal, at 400 m and 1000 m LoG scales (piedmont monocline warp).
 - VENT-2: depth-conditioned B17 conductivity residual vs B15 depth bins.
 - VENT-3: Bouguer-stripped G13 gravity residual vs B15 (fold-safe linear).

Reuses S13-PTHA cached stack for the remaining 20 PTHA channels; final
concatenated VENT stack is 24 columns (4 new) → 79-81 total with S11 etc.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems91 import dd_vtc_pu as DD

VENT_FEATURE_NAMES: list[str] = [
    "vent_flex_prof_curv_400m",   # profile curvature 400m
    "vent_flex_prof_curv_1000m",  # profile curvature 1000m
    "vent_cond_depth_residual",   # B17 - median(B17 | B15 bin)
    "vent_cond_residual_grad",    # grad mag of residual
    "vent_grav_stripped",         # B13 - linear(B15, sqrt(B15), log1p(B15))
    "vent_grav_stripped_grad",    # grad mag of stripped
]

# Optional: radiometric halo not used to keep budget 3; documented in VENT-4
TOPO_FEATURE_NAMES_VENT = {
    "b12_det_elev",
    "b19_det_elev_slope",
    "vent_flex_prof_curv_400m",
    "vent_flex_prof_curv_1000m",
    "ptha_step_elev_abs",
}


def _robust_z_grid(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = arr[footprint]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826 + 1e-6
    out = np.clip((arr - med) / mad, -8.0, 8.0).astype(np.float32)
    out[~footprint] = 0.0
    return out


def _profile_curvature(det_elev: np.ndarray, footprint: np.ndarray, sigma_m: float) -> np.ndarray:
    """Profile curvature = second derivative along downslope direction.

    Steps:
      1. Smooth elevation with sigma (pixels = sigma/100).
      2. Compute gradient (gy, gx) via Sobel/8.
      3. Compute slope magnitude and direction (downslope = gradient).
      4. Compute Hessian second derivatives and project onto slope direction:
         kappa_profile = (gy^2 * hyy + 2*gy*gx*hxy + gx^2 * hxx) / (gx^2+gy^2 + eps)^{3/2}
         Simplified to signed curvature: sign follows convexity.
    """
    sig_px = sigma_m / 100.0
    sm = ndi.gaussian_filter(det_elev.astype(np.float32), sigma=sig_px)
    # Sobel gradients (approx px derivative)
    gy = ndi.sobel(sm, axis=0) / np.float32(8.0)
    gx = ndi.sobel(sm, axis=1) / np.float32(8.0)
    # Second derivatives via gaussian second order
    # Use discrete second difference: gaussian_filter with order
    hxx = ndi.gaussian_filter(sm, sigma=1.0, order=(0, 2))
    hyy = ndi.gaussian_filter(sm, sigma=1.0, order=(2, 0))
    hxy = ndi.gaussian_filter(sm, sigma=1.0, order=(1, 1))
    denom = np.hypot(gy, gx) + np.float32(1e-4)
    # Normalize gradient direction
    ny = gy / denom
    nx = gx / denom
    # profile curvature = n^T H n  (where n is slope direction)
    kappa = (ny * ny * hyy + 2 * ny * nx * hxy + nx * nx * hxx).astype(np.float32)
    # Mask non-footprint and low-slope interiors? keep all footprint
    kappa[~footprint] = 0.0
    return kappa


def _depth_conditioned_conductivity(b17_cond: np.ndarray, b15_depth: np.ndarray, footprint: np.ndarray, n_bins: int = 12) -> tuple[np.ndarray, np.ndarray]:
    """Return (residual, grad_mag) where residual = B17 - median(B17 | depth_bin).

    Depth bins are quantile bins of log1p(B15) over footprint.
    """
    logd = np.log1p(np.maximum(b15_depth, 0.0))
    vals = logd[footprint]
    # quantile edges
    qs = np.linspace(0, 100, n_bins + 1)
    edges = np.percentile(vals, qs)
    # ensure strictly increasing
    edges = np.unique(edges)
    # if fewer unique, adjust n_bins
    residual = np.zeros_like(b17_cond, dtype=np.float32)
    # Compute median per bin
    for i in range(len(edges) - 1):
        lo = edges[i]
        hi = edges[i + 1]
        if i == len(edges) - 2:
            mask_bin = (logd >= lo) & (logd <= hi) & footprint
        else:
            mask_bin = (logd >= lo) & (logd < hi) & footprint
        if not np.any(mask_bin):
            continue
        med = float(np.median(b17_cond[mask_bin]))
        residual[mask_bin] = (b17_cond[mask_bin] - med).astype(np.float32)
    # High-pass: residual outside footprint 0
    residual[~footprint] = 0.0
    # Gradient magnitude of residual at sigma 1.5 px
    res_sm = ndi.gaussian_filter(residual, sigma=1.5)
    gyy = ndi.sobel(res_sm, axis=0) / 8.0
    gxx = ndi.sobel(res_sm, axis=1) / 8.0
    grad = np.hypot(gyy, gxx).astype(np.float32)
    grad[~footprint] = 0.0
    return residual.astype(np.float32), grad


def _bouguer_stripped_gravity(b13_grav: np.ndarray, b15_depth: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fold-agnostic (full-map) stripped gravity for feature building.

    For per-fold regression coefficients, see run_vent_lane.py; this function
    uses full-map robust linear fit as approximate feature (exact per-fold
    coefficients computed in training loop and stored). Here we do simple
    full-map least squares on [1, H, sqrt(H), log1p(H)].

    Returns (stripped residual, grad_mag).
    """
    H = np.maximum(b15_depth, 0.0)
    sqrtH = np.sqrt(H, dtype=np.float32)
    logH = np.log1p(H).astype(np.float32)
    # Design matrix over footprint
    X = np.column_stack([
        np.ones(int(footprint.sum()), dtype=np.float32),
        H[footprint].astype(np.float32),
        sqrtH[footprint],
        logH[footprint],
    ])
    y = b13_grav[footprint].astype(np.float64)
    # Lstsq
    coef, *_ = np.linalg.lstsq(X.astype(np.float64), y, rcond=None)
    # Predict full map
    pred = coef[0] + coef[1]*H + coef[2]*sqrtH + coef[3]*logH
    resid = (b13_grav - pred).astype(np.float32)
    resid[~footprint] = 0.0
    # gradient mag
    rsm = ndi.gaussian_filter(resid, sigma=1.5)
    gy = ndi.sobel(rsm, axis=0)/8.0
    gx = ndi.sobel(rsm, axis=1)/8.0
    gmag = np.hypot(gy, gx).astype(np.float32)
    gmag[~footprint] = 0.0
    return resid, gmag


def build_or_load_vent_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open disk-backed (N_fp, 6) float32 VENT feature matrix."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "vent_features_v1.dat"
    meta_path = cache_p / "vent_features_v1.json"
    n_fp = int(footprint.sum())
    n_cols = len(VENT_FEATURE_NAMES)
    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (meta.get("n_fp") == n_fp and meta.get("n_cols") == n_cols and meta.get("feature_names") == VENT_FEATURE_NAMES and dat_path.stat().st_size == n_fp * n_cols * 4):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(VENT_FEATURE_NAMES), meta
    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    # Load bands
    with rasterio.open(features_tif) as src:
        b12_elev = DD._clean_band_edt(src.read(12), footprint)
        b13_grav = DD._clean_band_edt(src.read(13), footprint)
        b15_depth = np.maximum(DD._clean_band_edt(src.read(15), footprint), 0.0)
        b17_cond = np.maximum(DD._clean_band_edt(src.read(17), footprint), 0.0)

    # VENT-1 curvature
    curv400 = _profile_curvature(b12_elev, footprint, sigma_m=400.0)
    curv1000 = _profile_curvature(b12_elev, footprint, sigma_m=1000.0)
    mm[:, 0] = np.abs(curv400[footprint]).astype(np.float32)  # use magnitude; will also keep signed? abs for detection
    # Keep raw signed for alternative? store abs; but we also want convexity magnitude
    mm[:, 1] = np.abs(curv1000[footprint]).astype(np.float32)
    del curv400, curv1000
    gc.collect()

    # VENT-2 conductivity depth residual
    cond_res, cond_grad = _depth_conditioned_conductivity(b17_cond, b15_depth, footprint, n_bins=12)
    mm[:, 2] = cond_res[footprint]
    mm[:, 3] = cond_grad[footprint]
    del cond_res, cond_grad, b17_cond
    gc.collect()

    # VENT-3 stripped gravity
    grav_strip, grav_grad = _bouguer_stripped_gravity(b13_grav, b15_depth, footprint)
    mm[:, 4] = grav_strip[footprint]
    mm[:, 5] = grav_grad[footprint]
    del grav_strip, grav_grad, b13_grav, b15_depth, b12_elev
    mm.flush()
    gc.collect()
    meta = {"n_fp": n_fp, "n_cols": n_cols, "feature_names": VENT_FEATURE_NAMES, "dtype": "float32"}
    meta_path.write_text(json.dumps(meta, indent=2)+"\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(VENT_FEATURE_NAMES), meta
