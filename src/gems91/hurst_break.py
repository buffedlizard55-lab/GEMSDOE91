"""Local roughness-regime breaks from the pinned GeoDAWN elevation bands.

This is a label-blind, single-channel hypothesis. ``B12 det_elev`` is the only
candidate input; ``B19 det_elev_slope`` is returned solely as a predeclared
slope-only control. The effective Hurst-like exponent is a local structure-
function slope, not a measured fractal property, scarp throw, or fault age.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import ced

VERSION = "hurst-break-variogram-v1"
LAGS_PX = (1, 2, 4)
WINDOW_PX = 11
EDGE_BUFFER_PX = 8
HURST_GRAD_SIGMA_PX = 2.0
MIN_LOCAL_PAIR_FRACTION = 0.50


def _pair_semivariance(z: np.ndarray, footprint: np.ndarray, dy: int, dx: int):
    """Local mean squared increment for one offset; return value and validity.

    Each comparison is placed at its first-pixel location. Out-of-grid pairs and
    pairs involving pixels outside the data footprint contribute neither a
    value nor a count. Uniform filters use the same zero padding in numerator
    and denominator so their ratio is the mean squared difference over only the
    valid pairs in the local window.
    """
    h, w = z.shape
    if abs(dy) >= h or abs(dx) >= w:
        raise ValueError("lag offset exceeds raster dimensions")

    if dy >= 0:
        y0, y1 = 0, h - dy
        yn0, yn1 = dy, h
    else:
        y0, y1 = -dy, h
        yn0, yn1 = 0, h + dy
    if dx >= 0:
        x0, x1 = 0, w - dx
        xn0, xn1 = dx, w
    else:
        x0, x1 = -dx, w
        xn0, xn1 = 0, w + dx

    base = (slice(y0, y1), slice(x0, x1))
    neighbor = (slice(yn0, yn1), slice(xn0, xn1))
    pair_ok = footprint[base] & footprint[neighbor]
    increment = z[base] - z[neighbor]
    np.square(increment, out=increment)
    increment[~pair_ok] = 0.0

    squared = np.zeros(z.shape, dtype=np.float32)
    pair_mask = np.zeros(z.shape, dtype=np.float32)
    squared[base] = increment
    pair_mask[base] = pair_ok
    del increment, pair_ok

    numerator = ndi.uniform_filter(
        squared, size=WINDOW_PX, mode="constant", cval=0.0
    )
    fraction = ndi.uniform_filter(
        pair_mask, size=WINDOW_PX, mode="constant", cval=0.0
    )
    valid = fraction >= MIN_LOCAL_PAIR_FRACTION
    gamma = np.zeros(z.shape, dtype=np.float32)
    np.divide(numerator, fraction, out=gamma, where=valid)
    del squared, pair_mask, numerator, fraction
    return gamma, valid


def features(det_elev, det_elev_slope, footprint):
    """Compute Hurst-like texture, its spatial break, and a B19 control.

    There is deliberately no catalogue, truth, previous candidate, or fitted
    parameter argument. All scale/window settings are fixed module constants.
    Returned arrays are finite, aligned, and zero outside their analysis mask.
    """
    fp = np.asarray(footprint, dtype=bool)
    elev = np.asarray(det_elev)
    slope = np.asarray(det_elev_slope)
    if fp.ndim != 2 or not fp.any() or elev.shape != fp.shape or slope.shape != fp.shape:
        raise ValueError("nonempty matching 2-D elevation, slope, and footprint required")

    z = ced.fill_input(elev, fp)
    gamma_by_lag = []
    valid_by_lag = []
    for lag in LAGS_PX:
        total = np.zeros(fp.shape, dtype=np.float32)
        count = np.zeros(fp.shape, dtype=np.uint8)
        for dy, dx in ((0, lag), (lag, 0)):
            gamma, valid = _pair_semivariance(z, fp, dy, dx)
            total[valid] += gamma[valid]
            count[valid] += 1
            del gamma, valid
        valid_lag = count > 0
        np.divide(total, count, out=total, where=valid_lag)
        gamma_by_lag.append(total)
        valid_by_lag.append(valid_lag)
        del count

    valid_hurst = np.logical_and.reduce(valid_by_lag)
    x = np.log(np.asarray(LAGS_PX, dtype=np.float64))
    x_centered = x - x.mean()
    denominator = float(np.dot(x_centered, x_centered))
    if denominator <= 0:
        raise AssertionError("fixed Hurst scale vector is degenerate")

    log_gamma = np.stack(
        [np.log(np.maximum(gamma, np.float32(1e-12))) for gamma in gamma_by_lag],
        axis=0,
    )
    slope_log_gamma = np.tensordot(x_centered, log_gamma, axes=(0, 0)) / denominator
    effective_hurst = (0.5 * slope_log_gamma).astype(np.float32)
    del log_gamma, slope_log_gamma, gamma_by_lag, valid_by_lag

    # Do not rank edge-fill or invalid-neighborhood artifacts. The 8-pixel
    # footprint erosion is preregistered; the additional 4-pixel validity
    # erosion protects the sigma=2 gradient from incomplete semivariograms.
    dist_to_edge = ndi.distance_transform_edt(fp)
    dist_to_invalid_hurst = ndi.distance_transform_edt(valid_hurst)
    analysis_mask = (
        fp
        & valid_hurst
        & (dist_to_edge > EDGE_BUFFER_PX)
        & (dist_to_invalid_hurst > int(np.ceil(2.0 * HURST_GRAD_SIGMA_PX)))
    )
    if int(analysis_mask.sum()) < 2:
        raise ValueError("insufficient valid interior for local roughness analysis")

    h_fill = float(np.median(effective_hurst[analysis_mask]))
    h_for_gradient = np.where(analysis_mask, effective_hurst, np.float32(h_fill))
    roughness_break = ndi.gaussian_gradient_magnitude(
        h_for_gradient, sigma=HURST_GRAD_SIGMA_PX, mode="nearest"
    ).astype(np.float32)

    h_out = np.zeros(fp.shape, dtype=np.float32)
    break_out = np.zeros(fp.shape, dtype=np.float32)
    h_out[analysis_mask] = effective_hurst[analysis_mask]
    break_out[analysis_mask] = roughness_break[analysis_mask]
    # Recompute only the two endpoint semivariances retained for canaries would
    # double the filter cost. Their source arrays were discarded after the
    # regression, so the canary set below uses the effective exponent, its
    # spatial break, B19, and the candidate rank surface.
    del z, effective_hurst, roughness_break, h_for_gradient, dist_to_edge, dist_to_invalid_hurst

    slope_norm = ced.fill_input(slope, fp)
    gradient_control = ced.percentiles(slope_norm, fp)
    surface = ced.percentiles(break_out, analysis_mask)

    out = {
        "effective_hurst_like": h_out,
        "roughness_break": break_out,
        "gradient_control_b19": gradient_control,
        "surface": surface,
    }
    for name, field in out.items():
        field[~fp] = 0.0
        if not np.isfinite(field).all():
            raise ValueError(f"{name}: nonfinite feature")
        out[name] = field.astype(np.float32, copy=False)
    return out
