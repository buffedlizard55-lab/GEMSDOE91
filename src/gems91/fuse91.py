"""FUSE91 — new feature/emission primitives for the F91 lane.

Preregistration: ``docs/HYPOTHESES_F91.md`` (frozen 2026-10-24 before any
F91 holdout number). This module contains only the pieces that do not
already exist in the repo:

1. Six **depth-conditioned subsurface-contact features** from sponsor
   bands 17 (``cond_surf``), 15 (``depth_to_base_surf``) and 13
   (``iso_grav_anom``). Basin fill makes raw conductivity trend with
   basement depth, so the conductivity signal is residualised within
   depth deciles (label-free, footprint statistics only) before its
   contact derivatives are taken; a buried basement step additionally
   makes the depth and gravity gradients collinear (both normal to
   strike), which the alignment feature measures directly.
2. **Scatter-cover smoothing** (F91-2): normalised Gaussian convolution
   of a detector surface with sigma = 1.85 px, the localization scatter
   of hidden traces around detector ridges fitted by GEMSDOE25's H28
   model (owner-claim-conditional; treated here as a frozen constant,
   not fitted on any label).
3. **Tiered greedy spaced emission** (F91-3): the repo's greedy spaced
   placement (`gems91.denovo.greedy_spaced` ordering/tie-break rules)
   generalised to a capped high-priority tier sharing one spacing
   exclusion mask — used for the 2–3 px catalogue collar ring.
4. Symmetric within-3-px overlap (F1) for novelty reporting alongside
   the protocol's directed fraction.

No catalogue-derived quantity is used in (1) or (2); (3) takes its
eligibility masks from the caller (visible-catalogue distances in the
holdout, full-catalogue distances in the final build).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .asc import percentile_grid
from .denovo import disk_offsets

NEW_FEATURE_NAMES = [
    "dc_cond_resid_pct",        # conductivity residual within depth deciles
    "dc_cond_resid_grad_pct",   # |gradient| of that residual (contact)
    "dc_cond_resid_lap_pct",    # |Laplacian| of that residual (contact crest)
    "dc_depth_lap_pct",         # signed Laplacian of depth-to-basement
    "dc_grav_lap_pct",          # signed Laplacian of isostatic gravity
    "dc_grad_align_pct",        # depth/gravity gradient collinearity x strength
]

SCATTER_SIGMA_PX = 1.85  # H28 fitted localization scatter (frozen, MODEL)


def _grad(field: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    sm = ndi.gaussian_filter(field.astype(np.float32), sigma, mode="nearest")
    gy, gx = np.gradient(sm)
    return gy.astype(np.float32), gx.astype(np.float32)


def depth_conditioned_features(cond: np.ndarray, depth: np.ndarray,
                               grav: np.ndarray, footprint: np.ndarray,
                               *, n_bins: int = 10) -> tuple[np.ndarray, dict]:
    """Return (n_footprint_rows, 6) float32 features in NEW_FEATURE_NAMES order.

    Inputs are cleaned full grids (sentinels already EDT-filled by the
    caller, the repo's ``_clean_band_edt`` convention). Every statistic
    (percentiles, decile medians) is computed on footprint pixels only
    and uses no label.
    """
    fp = np.asarray(footprint, dtype=bool)
    cond_pct = percentile_grid(cond, fp)
    depth_pct = percentile_grid(depth, fp)

    # Residualise conductivity against depth: subtract a *continuous*
    # conditional-median function of depth percentile (per-bin medians,
    # linearly interpolated between bin centres). Hard bin subtraction
    # would stamp sawtooth discontinuities along every depth contour
    # into the residual and its gradient; interpolation does not.
    bins = np.minimum((depth_pct * n_bins).astype(np.int64), n_bins - 1)
    bin_medians: list[float] = []
    for b in range(n_bins):
        m = fp & (bins == b)
        bin_medians.append(float(np.median(cond_pct[m])) if m.any() else 0.5)
    centres = (np.arange(n_bins, dtype=np.float64) + 0.5) / n_bins
    cond_median_of_depth = np.interp(depth_pct[fp], centres,
                                     np.asarray(bin_medians, dtype=np.float64))
    resid = np.zeros(fp.shape, dtype=np.float32)
    resid[fp] = (cond_pct[fp] - cond_median_of_depth).astype(np.float32)
    bin_medians = [round(m, 6) for m in bin_medians]
    del cond_pct, bins, cond_median_of_depth

    resid_sm = ndi.gaussian_filter(resid, 1.5, mode="nearest")
    rgy, rgx = np.gradient(resid_sm)
    f_resid = percentile_grid(resid, fp)
    f_rgrad = percentile_grid(np.hypot(rgx, rgy), fp)
    f_rlap = percentile_grid(np.abs(ndi.laplace(resid_sm)), fp)
    del resid, rgy, rgx

    depth_sm = ndi.gaussian_filter(depth.astype(np.float32), 2.0, mode="nearest")
    grav_sm = ndi.gaussian_filter(grav.astype(np.float32), 2.0, mode="nearest")
    f_dlap = percentile_grid(ndi.laplace(depth_sm), fp)
    f_glap = percentile_grid(ndi.laplace(grav_sm), fp)

    dgy, dgx = np.gradient(depth_sm)
    ggy, ggx = np.gradient(grav_sm)
    del depth_sm, grav_sm
    dmag = np.hypot(dgx, dgy)
    gmag = np.hypot(ggx, ggy)
    cosang = np.abs(dgx * ggx + dgy * ggy) / (dmag * gmag + 1e-12)
    strength = np.sqrt(percentile_grid(dmag, fp) * percentile_grid(gmag, fp))
    f_align = percentile_grid(strength * np.clip(cosang, 0.0, 1.0), fp)
    del dgy, dgx, ggy, ggx, dmag, gmag, cosang, strength

    cols = [f_resid, f_rgrad, f_rlap, f_dlap, f_glap, f_align]
    out = np.column_stack([c[fp] for c in cols]).astype(np.float32)
    audit = {"n_depth_bins": n_bins, "cond_pct_median_by_depth_bin": bin_medians,
             "feature_names": list(NEW_FEATURE_NAMES)}
    return out, audit


def scatter_smooth(surface: np.ndarray, footprint: np.ndarray,
                   sigma: float = SCATTER_SIGMA_PX) -> np.ndarray:
    """Normalised Gaussian convolution: cover field for trace scatter.

    ``smooth(surface * fp) / smooth(fp)`` so footprint edges do not droop;
    zero outside the footprint. A constant surface on the footprint is
    returned unchanged (up to float error).
    """
    fp = np.asarray(footprint, dtype=bool)
    s = np.where(fp, surface, 0.0).astype(np.float32)
    num = ndi.gaussian_filter(s, sigma, mode="constant", cval=0.0)
    den = ndi.gaussian_filter(fp.astype(np.float32), sigma, mode="constant", cval=0.0)
    out = np.where(fp & (den > 1e-9), num / np.maximum(den, 1e-9), 0.0)
    return out.astype(np.float32)


def _place(surface: np.ndarray, eligible: np.ndarray, blocked: np.ndarray,
           dots: np.ndarray, quota: int, offsets, placed: int) -> int:
    """Place up to ``quota`` dots in surface order; shared blocked mask.

    Ordering and tie-break are exactly `gems91.denovo.greedy_spaced`'s:
    stable argsort of -value over eligible flat indices.
    """
    if quota <= 0:
        return placed
    flat_idx = np.flatnonzero(eligible)
    if flat_idx.size == 0:
        return placed
    vals = surface.ravel()[flat_idx]
    cand = flat_idx[np.argsort(-vals, kind="stable")]
    del flat_idx, vals
    h, w = surface.shape
    for fidx in cand:
        if placed >= quota:
            break
        r, c = divmod(int(fidx), w)
        if blocked[r, c]:
            continue
        dots[r, c] = True
        placed += 1
        for dr, dc in offsets:
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w:
                blocked[rr, cc] = True
    return placed


def tiered_greedy_spaced(surface: np.ndarray, tier_eligible: np.ndarray,
                         main_eligible: np.ndarray, n_dots: int,
                         *, tier_cap: int, spacing_px: float = 2.8) -> np.ndarray:
    """Greedy spaced dots with a capped priority tier.

    Tier (e.g. the 2–3 px collar ring) places first, at most ``tier_cap``
    dots, in surface order; the main eligible set then fills to
    ``n_dots``. One spacing-exclusion mask is shared, so the minimum
    inter-dot distance holds across tiers. If the main set cannot reach
    ``n_dots``, remaining tier candidates are *not* used past the cap —
    the caller asserts the final count (fail-closed).
    """
    offsets = disk_offsets(spacing_px)
    blocked = np.zeros(surface.shape, dtype=bool)
    dots = np.zeros(surface.shape, dtype=bool)
    placed = _place(surface, tier_eligible, blocked, dots,
                    min(tier_cap, n_dots), offsets, 0)
    placed = _place(surface, main_eligible & ~tier_eligible, blocked, dots,
                    n_dots, offsets, placed)
    return dots


def symmetric_overlap_f1(ours: np.ndarray, theirs: np.ndarray,
                         radius_px: float = 3.0) -> dict:
    """Directed within-radius fractions both ways and their F1.

    The protocol's duplicate rule uses the directed fraction
    (our dots within ``radius_px`` of one registry raster). Against a
    dense cover that fraction saturates for *any* candidate (including
    the fleet_best R0 vs the lattice calibrator: 99.9 %), so the
    symmetric F1 — which also asks what fraction of *their* dots we
    cover — is reported alongside, never instead.
    """
    ours = np.asarray(ours, dtype=bool)
    theirs = np.asarray(theirs, dtype=bool)
    if not ours.any() or not theirs.any():
        return {"directed_ours_within": 0.0, "directed_theirs_within": 0.0, "f1": 0.0}
    d_theirs = ndi.distance_transform_edt(~theirs)
    p = float((d_theirs[ours] <= radius_px).mean())
    del d_theirs
    d_ours = ndi.distance_transform_edt(~ours)
    r = float((d_ours[theirs] <= radius_px).mean())
    del d_ours
    f1 = 0.0 if (p + r) == 0 else 2.0 * p * r / (p + r)
    return {"directed_ours_within": round(p, 6), "directed_theirs_within": round(r, 6),
            "f1": round(float(f1), 6)}
