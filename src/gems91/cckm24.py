"""S24-CCKM: cross-contact kurtosis of magnetic texture (B14 across B13).

Single-method lane preregistered in docs/s24/preregistration.md. Catalogue
independent: no fault coordinates enter any feature. Declared-NoData sentinels
are excluded from every statistic via masked (valid-only) normalised
convolution -- never filled with invented values, never read as data. This
repairs the S22-OMTJ failure mode (sentinel treated as a finite value) without
S23's unvalidated nearest-neighbour imputation.

Named non-fault mimics: unfaulted intrusive/volcanic contacts, lava-flow
margins, GeoDAWN survey seams, lithologic texture changes without displacement.
Nothing here measures geothermal heat, permeability, or venting.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

RESIDUAL_SIGMA_PX = 4.0
GRAVITY_SIGMA_PX = 3.0
KURTOSIS_WINDOW_PX = 15
KURTOSIS_MIN_VALID_FRAC = 0.8
KURTOSIS_CLIP = (-2.0, 30.0)
OFFSET_PX = 9.0
EXTREME_CUTOFF = 1e30


def valid_mask(field, footprint):
    """In-footprint cells with a genuine finite value (sentinel excluded)."""
    a = np.asarray(field)
    fp = np.asarray(footprint, bool)
    if a.ndim != 2 or a.shape != fp.shape:
        raise ValueError("field and footprint must be matching 2-D arrays")
    return fp & np.isfinite(a) & (np.abs(a.astype(np.float64)) < EXTREME_CUTOFF)


def _masked_blur(field, valid, sigma):
    """Local weighted mean over valid cells only (normalised convolution)."""
    x = np.where(valid, np.asarray(field, np.float64), 0.0)
    w = valid.astype(np.float64)
    num = ndi.gaussian_filter(x, sigma, mode="constant", cval=0.0)
    den = ndi.gaussian_filter(w, sigma, mode="constant", cval=0.0)
    return np.divide(num, den, out=np.zeros_like(num), where=den > 1e-9)


def _masked_uniform_sum(values, size):
    return ndi.uniform_filter(values, size=size, mode="constant", cval=0.0) * float(size * size)


def local_excess_kurtosis(residual, valid, *, window=KURTOSIS_WINDOW_PX,
                          min_valid_frac=KURTOSIS_MIN_VALID_FRAC):
    """Windowed excess kurtosis (4th central moment) over valid cells only.

    Returns (kurtosis, support) where support requires at least
    ``min_valid_frac`` of the window to be valid and a positive variance.
    """
    x = np.where(valid, np.asarray(residual, np.float64), 0.0)
    m = valid.astype(np.float64)
    count = _masked_uniform_sum(m, window)
    s1 = _masked_uniform_sum(x, window)
    x2 = x * x
    s2 = _masked_uniform_sum(x2, window)
    s3 = _masked_uniform_sum(x2 * x, window)
    s4 = _masked_uniform_sum(x2 * x2, window)
    del x, x2
    safe = count > 0
    mu = np.divide(s1, count, out=np.zeros_like(count), where=safe)
    e2 = np.divide(s2, count, out=np.zeros_like(count), where=safe)
    e3 = np.divide(s3, count, out=np.zeros_like(count), where=safe)
    e4 = np.divide(s4, count, out=np.zeros_like(count), where=safe)
    del s1, s2, s3, s4
    m2 = np.clip(e2 - mu * mu, 0.0, None)
    m4 = e4 - 4.0 * mu * e3 + 6.0 * mu * mu * e2 - 3.0 * mu**4
    del e2, e3, e4, mu
    support = safe & (count >= min_valid_frac * float(window * window)) & (m2 > 1e-12)
    kurt = np.divide(m4, m2 * m2, out=np.zeros_like(m2), where=support) - 3.0
    return np.where(support, kurt, 0.0), support


def _rank01(values, mask):
    """Percentile rank in [0,1] over mask (average ties), 0 outside mask."""
    out = np.zeros(np.shape(values), dtype=np.float32)
    vals = np.asarray(values, np.float64)[mask]
    if vals.size == 0:
        return out
    if vals.size == 1:
        out[mask] = 1.0
        return out
    out[mask] = ((rankdata(vals, method="average") - 1.0) / (vals.size - 1.0)).astype(np.float32)
    return out


def _sample_offset(field, uy, ux, offset):
    h, w = field.shape
    yy, xx = np.indices((h, w), dtype=np.float64)
    coords = [yy + offset * uy, xx + offset * ux]
    return ndi.map_coordinates(field, coords, order=1, mode="nearest")


def features(tmi, gravity, footprint):
    """CCKM feature dict + receipt metadata. All outputs finite, 0 outside fp."""
    fp = np.asarray(footprint, bool)
    t_valid = valid_mask(tmi, fp)
    g_valid = valid_mask(gravity, fp)
    if not t_valid.any() or not g_valid.any():
        raise ValueError("no valid geophysical input inside footprint")

    t = np.asarray(tmi, np.float64)
    residual = np.where(t_valid, t - _masked_blur(t, t_valid, RESIDUAL_SIGMA_PX), 0.0)
    del t
    kurt_raw, k_support = local_excess_kurtosis(residual, t_valid)
    del residual
    lo, hi = KURTOSIS_CLIP
    k_log = np.log1p(np.clip(kurt_raw, lo, hi) - lo)  # log1p(K - (-2)) = log1p(K+2)

    g_smooth = _masked_blur(gravity, g_valid, GRAVITY_SIGMA_PX)
    gy, gx = np.gradient(g_smooth)
    del g_smooth
    gmag = np.hypot(gy, gx)
    has_dir = g_valid & (gmag > 0)
    uy = np.divide(gy, gmag, out=np.zeros_like(gmag), where=has_dir)
    ux = np.divide(gx, gmag, out=np.zeros_like(gmag), where=has_dir)
    del gy, gx

    k_plus = _sample_offset(k_log, uy, ux, OFFSET_PX)
    k_minus = _sample_offset(k_log, uy, ux, -OFFSET_PX)
    s_plus = _sample_offset(k_support.astype(np.float64), uy, ux, OFFSET_PX) > 0.5
    s_minus = _sample_offset(k_support.astype(np.float64), uy, ux, -OFFSET_PX) > 0.5
    del uy, ux
    contrast = np.abs(k_plus - k_minus)
    del k_plus, k_minus
    support = fp & k_support & s_plus & s_minus & has_dir
    del s_plus, s_minus, has_dir

    contrast_rank = _rank01(contrast, support)
    grav_rank = _rank01(gmag, support)
    surface = np.where(
        support,
        np.sqrt(np.clip(contrast_rank.astype(np.float64) * grav_rank.astype(np.float64), 0.0, 1.0)),
        0.0,
    ).astype(np.float32)

    t_safe = np.where(t_valid, np.asarray(tmi, np.float64), 0.0)
    g_safe = np.where(g_valid, np.asarray(gravity, np.float64), 0.0)
    out = {
        "tmi_input": t_safe.astype(np.float32),
        "gravity_input": g_safe.astype(np.float32),
        "kurtosis_center_log": np.where(fp, k_log, 0.0).astype(np.float32),
        "kurtosis_contrast_rank": contrast_rank,
        "gravity_grad_rank": grav_rank,
        "gravity_grad_raw": np.where(fp, gmag, 0.0).astype(np.float32),
        "surface": surface,
    }
    if any(not np.isfinite(a).all() for a in out.values()):
        raise ValueError("nonfinite feature output")
    if float(surface.min()) < 0.0 or float(surface.max()) > 1.0:
        raise ValueError("surface outside [0,1]")
    ks = kurt_raw[k_support] if k_support.any() else np.array([0.0])
    meta = {
        "bands": "B14 tmi + B13 iso_grav_anom",
        "catalogue_features": False,
        "residual_sigma_px": RESIDUAL_SIGMA_PX,
        "gravity_sigma_px": GRAVITY_SIGMA_PX,
        "kurtosis_window_px": KURTOSIS_WINDOW_PX,
        "kurtosis_min_valid_frac": KURTOSIS_MIN_VALID_FRAC,
        "kurtosis_clip": list(KURTOSIS_CLIP),
        "offset_px": OFFSET_PX,
        "footprint_pixels": int(fp.sum()),
        "tmi_valid_pixels": int(t_valid.sum()),
        "gravity_valid_pixels": int(g_valid.sum()),
        "tmi_invalid_inside_footprint": int((fp & ~t_valid).sum()),
        "gravity_invalid_inside_footprint": int((fp & ~g_valid).sum()),
        "kurtosis_support_pixels": int(k_support.sum()),
        "surface_support_pixels": int(support.sum()),
        "kurtosis_raw_percentiles_on_support": {
            "p05": float(np.percentile(ks, 5)), "p50": float(np.percentile(ks, 50)),
            "p95": float(np.percentile(ks, 95)), "p99": float(np.percentile(ks, 99)),
        },
        "nodata_policy": "exclude non-finite or |value| >= 1e30 cells from every "
                         "statistic via masked normalised convolution; no filling",
    }
    return out, support, meta
