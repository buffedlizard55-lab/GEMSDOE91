"""Grid geometry: footprint, catalogue, distances, block selection."""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

CATALOGUE_FLOOR_PX = 2.0   # R0's own exclusion rule: no dot with d_cat <= 2.0
NEIGHBOUR_R_PX = 6.0       # 2 x kernel radius (R = 3 px): the credit-overlap reach


def footprint_mask(sample_submission: np.ndarray) -> np.ndarray:
    """Cells the organizer scores. The template is NaN outside the footprint."""
    return np.isfinite(sample_submission)


def catalogue_mask(existing_faults: np.ndarray) -> np.ndarray:
    """Mapped-fault cells. The raster carries -1 outside the footprint, 0/1 inside."""
    return np.nan_to_num(existing_faults, nan=0.0) > 0


def catalogue_distance(catalogue: np.ndarray) -> np.ndarray:
    """Euclidean distance, in 100 m cells, from every cell to the nearest mapped-fault cell."""
    return ndi.distance_transform_edt(~catalogue)


def block_ids(ys: np.ndarray, xs: np.ndarray, size: int) -> np.ndarray:
    """Row-major block index at `size` cells per side (size=10 -> 1 km blocks)."""
    return (ys // size).astype(np.int64) * 100_000 + (xs // size).astype(np.int64)


def densest_dot_selection(ys: np.ndarray, xs: np.ndarray, frac: float, size: int = 10) -> np.ndarray:
    """Boolean mask selecting dots in the densest blocks until >= frac of dots are covered.

    Deterministic: blocks are ranked by dot count (desc), ties broken by block id
    (row-major), so the same parent always yields the same selection.
    """
    if not 0.0 < frac < 1.0:
        raise ValueError(frac)
    ids = block_ids(ys, xs, size)
    uniq, inv, counts = np.unique(ids, return_inverse=True, return_counts=True)
    order = np.lexsort((uniq, -counts))          # count desc, then block id asc
    cum = np.cumsum(counts[order])
    n_blocks = int(np.searchsorted(cum, frac * len(ys)) + 1)
    chosen_ids = uniq[order[:n_blocks]]
    return np.isin(ids, chosen_ids)


def neighbour_direction(pts: np.ndarray, idx: np.ndarray, tree: cKDTree,
                        radius: float = NEIGHBOUR_R_PX) -> np.ndarray:
    """Unit-vector mean from each selected dot to its neighbours within `radius`.

    Returns a (len(idx), 2) array of unit vectors in (dy, dx); rows with no
    neighbours, or with a vanishing mean, are returned as zeros (= do not move).
    """
    out = np.zeros((len(idx), 2), dtype=np.float64)
    for k, i in enumerate(idx):
        nb = tree.query_ball_point(pts[i], r=radius)
        nb = [j for j in nb if j != i]
        if not nb:
            continue
        delta = pts[nb] - pts[i]
        norm = np.hypot(delta[:, 0], delta[:, 1])
        keep = norm > 0
        if not keep.any():
            continue
        u = (delta[keep] / norm[keep, None]).sum(axis=0)
        n = np.hypot(u[0], u[1])
        if n < 1e-9:
            continue
        out[k] = u / n
    return out
