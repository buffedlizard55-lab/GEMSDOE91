"""S16-PGRD: band-matched magnetic/gravity transfer residual (label-blind).

A potential-field exploration hypothesis, not a density inversion or vent map.
No catalogue or reference submission is accepted by the feature constructor.
"""
from __future__ import annotations

import numpy as np
from scipy import fft, ndimage as ndi

from .ced import fill_input, percentiles

VERSION = 'pgrd-v1'
DOT_BUDGET = 37_654
SIGMA_FINE = 2.0
SIGMA_COARSE = 5.0
BANDPASS_SIGMAS = (2.0, 16.0)
REGRESSION_SIGMA = 25.0
PAD = 64


def bandpass(field, *, integrate=False, sigmas=BANDPASS_SIGMAS, pad=PAD):
    """Gaussian bandpass; optional pole-reduced pseudogravity 1/|k|.

    k is radians/pixel. DC is zero; long-wave integration is regularized by
    the bandpass. Reflect padding reduces, but does not eliminate, edge effects.
    """
    a = np.asarray(field, dtype=np.float32)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError('finite 2-D field required')
    if len(sigmas) != 2 or not 0 < sigmas[0] < sigmas[1]:
        raise ValueError('positive, ordered bandpass sigmas required')
    if not isinstance(pad, int) or pad < 0:
        raise ValueError('nonnegative integer padding required')
    padded = np.pad(a, pad, mode='reflect') if pad else a
    spec = fft.rfft2(padded, workers=1)
    ky = (2 * np.pi * fft.fftfreq(padded.shape[0])).astype(np.float32)[:, None]
    kx = (2 * np.pi * fft.rfftfreq(padded.shape[1])).astype(np.float32)[None, :]
    k2 = ky * ky + kx * kx
    response = np.exp(-.5 * sigmas[0] ** 2 * k2) - np.exp(-.5 * sigmas[1] ** 2 * k2)
    if integrate:
        response = np.divide(response, np.sqrt(k2), out=np.zeros_like(response), where=k2 > 0)
    response[0, 0] = 0
    spec *= response
    result = fft.irfft2(spec, s=padded.shape, workers=1)
    if pad:
        result = result[pad:-pad, pad:-pad]
    return result.astype(np.float32, copy=True)


def local_transfer(pseudogravity, gravity, footprint, sigma=REGRESSION_SIGMA):
    """Local ridge-regression gravity residual and absolute-correlation deficit.

    All statistics use only geophysical observations, not labels. A ridge floor
    prevents division by near-zero pseudogravity variance. Constant inputs have
    zero correlation (not evidence of an alteration anomaly).
    """
    p, g, fp = np.asarray(pseudogravity), np.asarray(gravity), np.asarray(footprint)
    if p.shape != g.shape or p.shape != fp.shape or p.ndim != 2 or not fp.any():
        raise ValueError('matching nonempty 2-D grids required')
    if not np.isfinite(p).all() or not np.isfinite(g).all() or sigma <= 0:
        raise ValueError('finite inputs and positive sigma required')
    smooth = lambda x: ndi.gaussian_filter(x, sigma, mode='reflect')
    mp, mg = smooth(p), smooth(g)
    vp = np.maximum(smooth(p * p) - mp * mp, 0)
    vg = np.maximum(smooth(g * g) - mg * mg, 0)
    cov = smooth(p * g) - mp * mg
    ridge = max(.05 * float(np.median(vp[fp])), 1e-8)
    slope = cov / (vp + ridge)
    residual = g - (mg + slope * (p - mp))
    denom = np.sqrt(vp * vg)
    corr = np.divide(cov, denom, out=np.zeros_like(cov), where=denom > 1e-8)
    discordance = 1 - np.clip(np.abs(corr), 0, 1)
    return residual.astype(np.float32), discordance.astype(np.float32), slope.astype(np.float32)


def gradient(field, sigma):
    gy = ndi.gaussian_filter(field, sigma, order=(1, 0), mode='reflect')
    gx = ndi.gaussian_filter(field, sigma, order=(0, 1), mode='reflect')
    return np.hypot(gy, gx), gy, gx


def features(rtp, gravity, footprint):
    """Compute all surface inputs, including intermediates for leakage canaries."""
    fp = np.asarray(footprint, dtype=bool)
    if np.shape(rtp) != fp.shape or np.shape(gravity) != fp.shape:
        raise ValueError('feature/footprint shape mismatch')
    good = (fp & np.isfinite(rtp) & np.isfinite(gravity)
            & (np.asarray(rtp) > -1e30) & (np.asarray(gravity) > -1e30))
    m, g = fill_input(rtp, fp), fill_input(gravity, fp)
    p = bandpass(m, integrate=True)
    gb = bandpass(g)
    residual, discordance, slope = local_transfer(p, gb, fp)
    fields = {
        'rtp_rank': percentiles(m, fp),
        'gravity_rank': percentiles(g, fp),
        'pseudogravity_rank': percentiles(p, fp),
        'band_gravity_rank': percentiles(gb, fp),
        'transfer_slope_rank': percentiles(slope, fp),
        'residual_rank': percentiles(residual, fp),
        'discordance': discordance,
    }
    for label, field in (('gravity', gb), ('residual', residual)):
        fine, gy, gx = gradient(field, SIGMA_FINE)
        coarse, _, _ = gradient(field, SIGMA_COARSE)
        fields[label + '_edge_fine'] = percentiles(fine, fp)
        fields[label + '_edge_coarse'] = percentiles(coarse, fp)
        fields[label + '_persistence'] = np.sqrt(fields[label + '_edge_fine'] * fields[label + '_edge_coarse'])
        if label == 'residual':
            jxx = ndi.gaussian_filter(gx * gx, 3, mode='reflect')
            jyy = ndi.gaussian_filter(gy * gy, 3, mode='reflect')
            jxy = ndi.gaussian_filter(gx * gy, 3, mode='reflect')
            denom = jxx + jyy
            coherence = np.divide(np.hypot(jxx - jyy, 2 * jxy), denom,
                                  out=np.zeros_like(denom), where=denom > 1e-12)
            fields['residual_coherence'] = np.clip(coherence, 0, 1)
    # Explicit false padding makes distance to the array edge well-defined too.
    support_dist = ndi.distance_transform_edt(np.pad(good, 1, constant_values=False))[1:-1, 1:-1]
    fields['input_support'] = np.clip(support_dist / 8.0, 0, 1).astype(np.float32)
    fields['surface'] = (fields['residual_persistence'] * fields['gravity_persistence']
                         * fields['residual_coherence'] * (.5 + .5 * discordance)
                         * fields['input_support'])
    for name, field in fields.items():
        field = np.asarray(field, dtype=np.float32)
        field[~fp] = 0
        if not np.isfinite(field).all() or (field < 0).any() or (field > 1).any():
            raise ValueError(f'{name}: nonfinite or unnormalized feature')
        fields[name] = field
    return fields
