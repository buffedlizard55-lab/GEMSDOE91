"""G91-COVER — cover-gated interaction features for the G91 lane.

Preregistration: docs/HYPOTHESES_G91.md (frozen 2026-10-24 before any
G91 holdout number). This module contains only the pieces that do not
already exist in the repo:

Cover-gated topographic vs subsurface trust.  The USGS/INGENIOUS catalogue
is exposure-biased: it maps faults where scarps are visible at 1 m but
omits blind/piedmont continuations beneath Quaternary cover.  Those faults
still offset basement, create gravity/magnetic contrasts and conductivity
contrasts.  Thickness is proxied by depth_to_base_surf (band 15).

Every statistic (percentiles, sigmoid parameters) is footprint-only and
label-free.  No catalogue-derived quantity is used.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .asc import percentile_grid

NEW_FEATURE_NAMES = [
    "cover_w",                    # sigmoid depth percentile -> [0,1]
    "cg_topo_suppressed",         # det_elev_slope_pct * (1-w)  trusted in outcrop
    "cg_grav_boosted",            # iso_grav_anom_hg_pct * w   trusted in cover
    "cg_mag_boosted",             # tmi_hg_pct * w
    "cg_depth_step_cover",        # depth_grad_pct * w  basement step in thick cover
    "cg_topo_in_thick_penalty",   # det_elev_slope_pct * w  high slope in thick = terrace flag
    "cg_cond_in_cover",           # cond_surf_pct * w  conductivity in cover
]

# Frozen sigmoid: w = 1/(1+exp(-(depth_pct - center)/scale))
# center 0.55 ~ median+slightly above (cover ~30-50 m), scale 0.12 smooth
CENTER = 0.55
SCALE = 0.12


def _clean_band(band: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    a = band.astype(np.float32)
    bad = ~np.isfinite(a) | (a < -1e30)
    if bad.any():
        _, idx = ndi.distance_transform_edt(bad, return_indices=True)
        a = a[idx[0], idx[1]]
    return a


def cover_gated_features(
    det_elev_slope: np.ndarray,
    iso_grav_hg: np.ndarray,
    tmi_hg: np.ndarray,
    depth_to_base: np.ndarray,
    cond_surf: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Return (n_fp, 6 or 7) float32 features in NEW_FEATURE_NAMES order.

    Inputs are cleaned full grids (float32) on the model grid, footprint bool.
    """
    fp = np.asarray(footprint, dtype=bool)

    # Percentile ranks (footprint-only) for each band
    det_s_pct = percentile_grid(_clean_band(det_elev_slope, fp), fp)
    grav_hg_pct = percentile_grid(np.abs(_clean_band(iso_grav_hg, fp)), fp)
    tmi_hg_pct = percentile_grid(_clean_band(tmi_hg, fp), fp)
    depth_pct = percentile_grid(_clean_band(depth_to_base, fp), fp)
    cond_pct = percentile_grid(_clean_band(cond_surf, fp), fp)

    # Depth gradient magnitude percentile (basement step)
    depth_clean = _clean_band(depth_to_base, fp)
    depth_sm = ndi.gaussian_filter(depth_clean, 2.0, mode="nearest")
    gy, gx = np.gradient(depth_sm)
    depth_grad = np.hypot(gx, gy)
    depth_grad_pct = percentile_grid(depth_grad, fp)
    del depth_clean, depth_sm, gy, gx, depth_grad

    # Cover weight: sigmoid of depth percentile
    w_full = 1.0 / (1.0 + np.exp(-(depth_pct - CENTER) / SCALE))
    w_full = np.where(fp, w_full, 0.0).astype(np.float32)

    # Interactions
    topo_sup = (det_s_pct * (1.0 - w_full)).astype(np.float32)
    grav_boost = (grav_hg_pct * w_full).astype(np.float32)
    mag_boost = (tmi_hg_pct * w_full).astype(np.float32)
    depth_step = (depth_grad_pct * w_full).astype(np.float32)
    topo_in_thick = (det_s_pct * w_full).astype(np.float32)
    cond_in_cover = (cond_pct * w_full).astype(np.float32)

    # Percentile each interaction (so HGB sees uniform marginals, like CTX)
    # Except w itself which is already uniform-ish via sigmoid of percentile
    f_w = np.where(fp, w_full, 0.0).astype(np.float32)
    f_topo_sup = percentile_grid(topo_sup, fp)
    f_grav_boost = percentile_grid(grav_boost, fp)
    f_mag_boost = percentile_grid(mag_boost, fp)
    f_depth_step = percentile_grid(depth_step, fp)
    f_topo_in_thick = percentile_grid(topo_in_thick, fp)
    f_cond_in_cover = percentile_grid(cond_in_cover, fp)

    cols = [f_w, f_topo_sup, f_grav_boost, f_mag_boost, f_depth_step, f_topo_in_thick, f_cond_in_cover]
    # But we promised 6 interaction features + cover_w = 7 total
    # Check names: we have 7 names, so return 7
    out = np.column_stack([c[fp] for c in cols]).astype(np.float32)
    assert out.shape[1] == len(NEW_FEATURE_NAMES), (out.shape, len(NEW_FEATURE_NAMES))

    audit = {
        "center": CENTER,
        "scale": SCALE,
        "feature_names": list(NEW_FEATURE_NAMES),
        "note": "cover_w=sigmoid(depth_pct-0.55)/0.12; interactions are elementwise products then footprint-percentile ranked",
    }
    return out, audit
