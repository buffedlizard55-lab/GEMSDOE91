"""Catalogue-independent odd-moment magnetic texture juxtaposition (S22 E1).

No inferred geothermal temperature/permeability; volcanic contacts are a mimic.
All operations are on cached geophysical channels, never fault coordinates.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi


def normalized_positive(a, footprint):
    a = np.maximum(np.asarray(a, np.float32), 0)
    scale = float(np.percentile(a[footprint], 95))
    if not np.isfinite(scale):
        raise ValueError('nonfinite feature scale')
    return np.where(footprint, np.clip(a / max(scale, 1e-12), 0, 1), 0).astype(np.float32)


def fill_band(a, footprint):
    a = np.asarray(a, np.float32)
    fp = np.asarray(footprint, bool)
    if a.ndim != 2 or a.shape != fp.shape or not fp.any():
        raise ValueError('nonempty matching 2D footprint required')
    if not np.isfinite(a[fp]).all():
        raise ValueError('nonfinite geophysical input inside footprint')
    # Nearest footprint extension avoids artificial zero-valued boundary edges.
    # No catalogue or target values are involved.
    if fp.all():
        return a.copy()
    ix = ndi.distance_transform_edt(~fp, return_distances=False, return_indices=True)
    return a[tuple(ix)].copy()


def features(tmi, gravity, footprint):
    fp = np.asarray(footprint, bool)
    u = fill_band(tmi, fp)
    u -= ndi.gaussian_filter(u, 12, mode='reflect')
    scale = max(float(np.percentile(np.abs(u[fp]), 95)), 1e-12)
    u /= scale
    mean = ndi.gaussian_filter(u, 3, mode='reflect')
    second = ndi.gaussian_filter(u * u, 3, mode='reflect')
    var = np.maximum(second - mean * mean, 0)
    third = ndi.gaussian_filter(u * u * u, 3, mode='reflect')
    third -= 3 * mean * second - 2 * mean ** 3
    positive = var[fp & (var > 0)]
    floor = max(float(np.percentile(positive, 10)) if positive.size else 0, 1e-8)
    skew = np.clip(third / np.maximum(var, floor) ** 1.5, -5, 5)
    sy = ndi.gaussian_filter(skew, 1, order=(1, 0), mode='reflect')
    sx = ndi.gaussian_filter(skew, 1, order=(0, 1), mode='reflect')
    g = fill_band(gravity, fp)
    gy = ndi.gaussian_filter(g, 3, order=(1, 0), mode='reflect')
    gx = ndi.gaussian_filter(g, 3, order=(0, 1), mode='reflect')
    sm = np.hypot(sx, sy)
    gm = np.hypot(gx, gy)
    alignment = np.divide(sx * gx + sy * gy, sm * gm,
                          out=np.zeros_like(sm), where=(sm * gm) > 1e-12) ** 2
    alignment = np.where(fp, np.clip(alignment, 0, 1), 0).astype(np.float32)
    edge = normalized_positive(sm, fp)
    strength = normalized_positive(gm, fp)
    surface = np.cbrt(edge * strength * alignment).astype(np.float32)
    out = {'tmi_input': np.where(fp, tmi, 0).astype(np.float32),
           'gravity_input': np.where(fp, gravity, 0).astype(np.float32),
           'skewness': np.where(fp, skew, 0).astype(np.float32),
           'skewness_edge': edge, 'gravity_edge': strength,
           'normal_alignment_squared': alignment, 'surface': surface}
    if any(not np.isfinite(a).all() for a in out.values()):
        raise ValueError('nonfinite feature output')
    return out, {'background_sigma_px': 12, 'moment_sigma_px': 3,
                 'skew_derivative_sigma_px': 1, 'gravity_derivative_sigma_px': 3,
                 'variance_floor': floor, 'tmi_residual_scale': scale,
                 'catalogue_features': False}
