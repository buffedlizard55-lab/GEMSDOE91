"""H11-1: oriented topographic-lineament coherence (structure tensor, detrended elevation).

Label-blind by construction: the only input is GeoDAWN band 12 (`det_elev`,
detrended elevation). No catalogue, no submission raster and no fitted parameter
enters feature construction; the catalogue is used only for the canary and the
hide-and-recover evaluation in scripts/run_h11.py.

Signature: a fault scarp or range-front escarpment is a *coherent, oriented*
ridge/step in elevation. A structure tensor integrated over a window measures
whether gradient orientations agree along a line (anisotropy = coherence). Pure
slope magnitude (control arm) cannot separate a linear scarp from an isotropic
hill of the same steepness, so coherence is the quantity under test.

Method (fixed before any holdout run; see docs/HYPOTHESES_H11.md):
  gradient  : Gaussian derivative, sigma_g = 1.5 px
  tensor    : Gaussian integration window, sigma_w in SCALES = (3.0, 6.0) px
  coherence : ((l1 - l2) / (l1 + l2))^2 in [0, 1]
  surface   : sqrt(pct(coh_3) * pct(coh_6)) * pct(|grad|), percentiles over the footprint
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import ced

VERSION = 'h11-structure-tensor-v1'
GRAD_SIGMA = 1.5
SCALES = (3.0, 6.0)


def coherence(elev, footprint, sigma_w):
    """Structure-tensor coherence and gradient magnitude on a filled elevation grid."""
    fp = np.asarray(footprint, bool)
    gx = ndi.gaussian_filter(elev, GRAD_SIGMA, order=(0, 1), mode='nearest')
    gy = ndi.gaussian_filter(elev, GRAD_SIGMA, order=(1, 0), mode='nearest')
    jxx = ndi.gaussian_filter(gx * gx, sigma_w, mode='nearest')
    jyy = ndi.gaussian_filter(gy * gy, sigma_w, mode='nearest')
    jxy = ndi.gaussian_filter(gx * gy, sigma_w, mode='nearest')
    tr = jxx + jyy
    disc = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy ** 2)
    l1 = 0.5 * (tr + disc)
    l2 = 0.5 * (tr - disc)
    coh = np.where(tr > 1e-12, ((l1 - l2) / np.maximum(l1 + l2, 1e-12)) ** 2, 0.0)
    coh = np.clip(coh, 0.0, 1.0)
    mag = np.hypot(gx, gy)
    coh[~fp] = 0.0
    mag[~fp] = 0.0
    return coh.astype(np.float32), mag.astype(np.float32)


def features(det_elev, footprint):
    """Return the candidate and its arms. No catalogue or label-derived argument exists."""
    fp = np.asarray(footprint, bool)
    elev = ced.fill_input(det_elev, fp)
    coh3, mag = coherence(elev, fp, SCALES[0])
    coh6, _ = coherence(elev, fp, SCALES[1])
    p3 = ced.percentiles(coh3, fp)
    p6 = ced.percentiles(coh6, fp)
    pm = ced.percentiles(mag, fp)
    surface = np.sqrt(p3 * p6) * pm
    out = dict(raw_elevation=ced.percentiles(elev, fp), coherence_3px=p3, coherence_6px=p6,
               gradient_magnitude=pm, surface=surface.astype(np.float32),
               gradient_control=pm.astype(np.float32))
    for name, field in out.items():
        field[~fp] = 0
        if not np.isfinite(field).all():
            raise ValueError(f'{name}: nonfinite feature')
        out[name] = field.astype(np.float32, copy=False)
    return out
