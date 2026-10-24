"""Basement-step ridge candidate (session 10, GEMSDOE91).

Hypothesis (pre-registered before any holdout run, see docs/HYPOTHESES_S10.md, H10-1):
  Normal and strike-slip faults in the Great Basin displace the sedimentary-basement
  surface.  A fault that offsets basement produces a narrow lateral step in
  depth-to-basement (band 15 of the pinned GeoDAWN feature stack).  Basin-margin
  flexure and onlap produce broad, gentle gradients instead.  A thin ridge of the
  gradient magnitude of smoothed log-depth should therefore mark steps, not broad
  basin shoulders.

Output encoding (matches the organizer sample: float32, one band, NaN outside the
footprint, values in [0, 1]):  the K highest-scoring ridge cells receive a continuous
rank ramp  p = 1 - r / (K + 1)  (r = 0 is the best cell).  Every other footprint cell
is 0.  Catalogue cells are masked to zero (validator gate: zero mass on catalogue).

Nothing here reads a competition file by itself.  Callers pass arrays.  The ranking
uses only the depth band and the (visible) catalogue mask, so the holdout can rebuild
it per fold with the withheld segments hidden.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

NODATA_CUTOFF = -1e38          # sentinel values in the pinned feature stack are ~ -3.4e38
SIGMA_PX = 2.0                 # 200 m Gaussian before differentiation (pre-registered)
DEPTH_OFFSET_M = 50.0          # log(depth + 50 m): keeps outcrop (~0 m) finite
EDGE_ERODE_PX = 2              # drop cells whose gradient stencil touches the footprint edge
K_DEFAULT = 60988              # = catalogue fault pixels (pre-registered budget)


def clean_depth(raw: np.ndarray) -> np.ndarray:
    """Float64 depth with sentinels and non-finite values replaced by NaN."""
    d = np.asarray(raw, dtype=np.float64).copy()
    d[~np.isfinite(d) | (d < NODATA_CUTOFF)] = np.nan
    return d


def smoothed_log_depth(depth: np.ndarray, sigma: float = SIGMA_PX) -> np.ndarray:
    """Normalised-convolution Gaussian smoothing of log(max(depth,0)+offset).

    NaN cells do not contribute; output is NaN only where no valid neighbour exists
    within the kernel support.
    """
    valid = np.isfinite(depth)
    depth_pos = np.where(valid, np.clip(depth, 0.0, None), 0.0)
    logd = np.log(depth_pos + DEPTH_OFFSET_M)
    num = ndi.gaussian_filter(np.where(valid, logd, 0.0), sigma, mode="nearest")
    den = ndi.gaussian_filter(valid.astype(np.float64), sigma, mode="nearest")
    out = np.full(depth.shape, np.nan)
    ok = den > 1e-6
    out[ok] = num[ok] / den[ok]
    return out


def _fill_nan_nearest(field: np.ndarray) -> np.ndarray:
    bad = ~np.isfinite(field)
    if not bad.any():
        return field
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return field[tuple(idx)]


def gradient_magnitude(field: np.ndarray) -> np.ndarray:
    """|grad| of a 2-D field in cell units (100 m cells; constant factor irrelevant to ranking)."""
    filled = _fill_nan_nearest(field)
    gy, gx = np.gradient(filled)
    return np.hypot(gx, gy), gx, gy


def ridge_nms(mag: np.ndarray, gx: np.ndarray, gy: np.ndarray) -> np.ndarray:
    """Keep a cell only if it is a local maximum of |grad| along the gradient direction."""
    with np.errstate(invalid="ignore", divide="ignore"):
        ux = np.where(mag > 0, gx / mag, 0.0)
        uy = np.where(mag > 0, gy / mag, 0.0)
    yy, xx = np.mgrid[0 : mag.shape[0], 0 : mag.shape[1]].astype(np.float64)
    fwd = ndi.map_coordinates(mag, [yy + uy, xx + ux], order=1, mode="nearest")
    bwd = ndi.map_coordinates(mag, [yy - uy, xx - ux], order=1, mode="nearest")
    return (mag >= fwd) & (mag >= bwd)


def interior_mask(footprint: np.ndarray, erode: int = EDGE_ERODE_PX) -> np.ndarray:
    return ndi.binary_erosion(footprint, iterations=erode, border_value=0)


def score_field(depth: np.ndarray, footprint: np.ndarray, use_nms: bool = True) -> np.ndarray:
    """Per-cell ridge score (0 where not eligible).  Independent of the catalogue."""
    d = clean_depth(depth)
    field = smoothed_log_depth(d)
    field = np.where(footprint, field, np.nan)
    mag, gx, gy = gradient_magnitude(field)
    eligible = interior_mask(footprint) & np.isfinite(d)
    if use_nms:
        eligible &= ridge_nms(mag, gx, gy)
    score = np.where(eligible & np.isfinite(mag), mag, 0.0)
    return score


def rank_ramp(score: np.ndarray, exclude: np.ndarray, k: int = K_DEFAULT) -> np.ndarray:
    """Top-k cells (excluding `exclude`) get 1 - r/(k+1); everything else 0.

    Ties are broken row-major (stable sort), so the output is deterministic.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    s = np.where(exclude, 0.0, score).ravel()
    order = np.argsort(-s, kind="stable")
    keep = order[: min(k, int((s > 0).sum()))]
    out = np.zeros(s.shape, dtype=np.float64)
    r = np.arange(keep.size, dtype=np.float64)
    out[keep] = 1.0 - r / (k + 1.0)
    return out.reshape(score.shape)


def build_candidate(
    depth: np.ndarray,
    footprint: np.ndarray,
    visible_catalogue: np.ndarray,
    k: int = K_DEFAULT,
    use_nms: bool = True,
) -> np.ndarray:
    """Full candidate map (float64, zero outside the footprint is applied by the writer).

    `visible_catalogue` is the set of catalogue cells the method is allowed to see.  On the
    full submission it is the whole catalogue; in a holdout fold it excludes the withheld
    segments (pixel-exact).  Visible cells receive zero mass.
    """
    score = score_field(depth, footprint, use_nms=use_nms)
    return rank_ramp(score, exclude=visible_catalogue | ~footprint, k=k)


def random_placement(footprint: np.ndarray, exclude: np.ndarray, k: int, seed: int) -> np.ndarray:
    """Null: k cells drawn uniformly from eligible footprint cells, same ramp encoding."""
    eligible = np.flatnonzero((footprint & ~exclude).ravel())
    rng = np.random.default_rng(seed)
    pick = rng.choice(eligible, size=min(k, eligible.size), replace=False)
    pick = pick[np.argsort(rng.random(pick.size))]  # random rank order, same ramp shape
    out = np.zeros(footprint.size, dtype=np.float64)
    out[pick] = 1.0 - np.arange(pick.size, dtype=np.float64) / (k + 1.0)
    return out.reshape(footprint.shape)
