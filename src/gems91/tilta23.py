"""Catalogue-independent tilt-angle x gravity-HG concordance (S23 E1).

No geothermal temperature/permeability inference; volcanic contacts are a mimic.
All operations on cached geophysical channels, never fault coordinates.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi

def normalized_positive(a, footprint):
    a = np.maximum(np.asarray(a, np.float32), 0)
    scale = float(np.percentile(a[footprint], 95)) if footprint.any() else 1.0
    if not np.isfinite(scale) or scale == 0:
        scale = 1.0
    return np.where(footprint, np.clip(a / max(scale, 1e-12), 0, 1), 0).astype(np.float32)

NODATA_CUTOFF = -1e30

def clean_band(a):
    a = np.asarray(a, np.float64)
    a = np.where(np.isfinite(a) & (a > NODATA_CUTOFF), a, np.nan)
    return a

def fill_band(a, footprint):
    a = np.asarray(a, np.float32)
    # Replace sentinels with NaN before check, then nearest-neighbor fill
    a_clean = np.where(np.isfinite(a) & (a > -1e30), a, np.nan)
    fp = np.asarray(footprint, bool)
    if a_clean.ndim != 2 or a_clean.shape != fp.shape or not fp.any():
        raise ValueError('nonempty matching 2D footprint required')
    # Allow NaNs inside footprint; they will be filled
    # Check that at least some footprint cells are finite
    if not np.isfinite(a_clean[fp]).any():
        raise ValueError('no finite geophysical input inside footprint')
    if fp.all():
        # fill NaNs inside footprint via nearest finite
        if not np.isfinite(a_clean[fp]).all():
            mask = np.isfinite(a_clean)
            if not mask.any():
                raise ValueError('no finite data')
            ix = ndi.distance_transform_edt(~mask, return_distances=False, return_indices=True)
            a_clean = a_clean[tuple(ix)]
        return a_clean.astype(np.float32)
    # First fill footprint-adjacent NaNs using nearest finite across whole grid
    mask = np.isfinite(a_clean)
    if not mask[fp].all():
        ix_fill = ndi.distance_transform_edt(~mask, return_distances=False, return_indices=True)
        a_filled = a_clean[tuple(ix_fill)]
    else:
        a_filled = a_clean
    # Then extend outside footprint via nearest footprint value (for convolution edge handling)
    ix = ndi.distance_transform_edt(~fp, return_distances=False, return_indices=True)
    return a_filled[tuple(ix)].copy().astype(np.float32)

def features(tilt_tc, grav_hg, footprint):
    fp = np.asarray(footprint, bool)
    # Clean sentinels to NaN then fill
    t_raw = clean_band(tilt_tc)
    g_raw = clean_band(grav_hg)
    t = fill_band(t_raw, fp)
    g = fill_band(g_raw, fp)
    # Ensure finite after fill
    if not np.isfinite(t[fp]).all() or not np.isfinite(g[fp]).all():
        raise ValueError('nonfinite after fill')
    # Tilt gradient vector (captures zero-crossing edge)
    ty = ndi.gaussian_filter(t, 2, order=(1,0), mode='reflect')
    tx = ndi.gaussian_filter(t, 2, order=(0,1), mode='reflect')
    gy = ndi.gaussian_filter(g, 2, order=(1,0), mode='reflect')
    gx = ndi.gaussian_filter(g, 2, order=(0,1), mode='reflect')
    tm = np.hypot(ty, tx)
    gm = np.hypot(gy, gx)
    # Alignment: squared cosine between tilt normal and grav-HG normal
    # Faults should have co-linear gradient directions (both normal to fault)
    alignment = np.divide(ty*gy + tx*gx, tm*gm, out=np.zeros_like(tm), where=(tm*gm) > 1e-12) ** 2
    alignment = np.where(fp, np.clip(alignment, 0, 1), 0).astype(np.float32)
    edge_tilt = normalized_positive(tm, fp)
    strength_grav = normalized_positive(gm, fp)
    surface = np.cbrt(np.clip(edge_tilt * strength_grav * alignment, 0, 1)).astype(np.float32)
    # For raw inputs, mask sentinels to 0 outside footprint to avoid inf
    tilt_safe = np.where(np.isfinite(tilt_tc) & (tilt_tc > -1e30), tilt_tc, 0)
    grav_safe = np.where(np.isfinite(grav_hg) & (grav_hg > -1e30), grav_hg, 0)
    out = {
        'tilt_input': np.where(fp, tilt_safe, 0).astype(np.float32),
        'grav_hg_input': np.where(fp, grav_safe, 0).astype(np.float32),
        'tilt_edge': edge_tilt,
        'grav_hg_strength': strength_grav,
        'normal_alignment_squared': alignment,
        'surface': surface,
    }
    if any(not np.isfinite(a).all() for a in out.values()):
        raise ValueError('nonfinite feature output')
    return out, {
        'tilt_sigma_px': 2,
        'grav_sigma_px': 2,
        'catalogue_features': False,
        'bands': 'B06 tc + B18 iso_grav_anom_hg',
    }
