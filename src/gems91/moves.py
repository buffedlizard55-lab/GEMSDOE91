"""The SPACING edit: relocate dots within a fixed radius-2 Moore ring.

Design constraints that make the arms comparable
------------------------------------------------
* Same selected set (40 % of dots, the densest 1 km blocks) in every arm.
* Same displacement budget: every moved dot lands on one of the 12 integer
  cells at 2.0-2.236 px from its own cell. The arms differ only in *which*
  legal cell on that ring is chosen.
* Same hard constraints on every arm: inside the footprint, farther than the
  parent's own catalogue floor (d_cat > 2.0 px), no cell reused, and no two
  dots closer than 2.0 px after the edit (a 1 px duplicate is not a spacing
  treatment, it is a wasted dot).

Treatment
---------
The arms do not use a hand-rolled "direction"; they optimise a stated
potential D = Gaussian-smoothed dot density (sigma = 2 px, i.e. inside the
kernel radius). For each movable dot the legal ring cells are ranked by D:

    spread40  choose the legal cell with the LOWEST D   (coverage per unit mass)
    clump40   choose the legal cell with the HIGHEST D  (trace sharpening)
    jitter40  choose a legal cell pseudo-randomly       (null; same ring, same set)

So "spread" is defined by the quantity the mechanism claims to move, not by an
angle, and `clump` reports its own realised dose because a jammed parent may
leave it nowhere legal to go.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

# The 12 integer offsets with 2.0 <= |offset| <= 2.2361 px.
RING: tuple[tuple[int, int], ...] = (
    (2, 0), (0, 2), (-2, 0), (0, -2),
    (2, 1), (2, -1), (-2, 1), (-2, -1),
    (1, 2), (1, -2), (-1, 2), (-1, -2),
)
MIN_SEPARATION_PX = 2.0


def ring_offsets() -> np.ndarray:
    return np.array(RING, dtype=np.int64)


def density_potential(dot: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    """Gaussian-smoothed dot density: the quantity 'spacing' is supposed to change."""
    return ndi.gaussian_filter(dot.astype(np.float32), sigma=sigma, mode="constant")


def _separation_kernel() -> np.ndarray:
    k = np.zeros((5, 5), dtype=bool)
    yy, xx = np.mgrid[-2:3, -2:3]
    k[np.hypot(yy, xx) < MIN_SEPARATION_PX] = True
    k[2, 2] = False  # a dot may occupy its own cell
    return k


_SEP = _separation_kernel()


def apply_moves(dot: np.ndarray, footprint: np.ndarray, cat_dist: np.ndarray,
                ys: np.ndarray, xs: np.ndarray, movable: np.ndarray,
                *, mode: str, density: np.ndarray, rng: np.random.Generator,
                floor_px: float = 2.0) -> dict:
    """Relocate movable dots; never delete, never add, never reuse a cell.

    mode: "spread" (minimise D) | "clump" (maximise D) | "jitter" (random legal)
    """
    if mode not in ("spread", "clump", "jitter"):
        raise ValueError(mode)
    out = dot.copy()
    h, w = dot.shape
    # Cells within MIN_SEPARATION_PX of an existing dot are forbidden as targets.
    # A vacated cell is NOT released within the pass (conservative, deterministic).
    blocked = ndi.binary_dilation(dot, structure=_SEP)
    moved = 0
    disp: list[float] = []
    dens_from: list[float] = []
    dens_to: list[float] = []
    ring = ring_offsets()

    for i in np.flatnonzero(movable):
        y, x = int(ys[i]), int(xs[i])
        ty, tx = y + ring[:, 0], x + ring[:, 1]
        ok = ((ty >= 0) & (ty < h) & (tx >= 0) & (tx < w))
        ok &= footprint[ty.clip(0, h - 1), tx.clip(0, w - 1)]
        ok &= cat_dist[ty.clip(0, h - 1), tx.clip(0, w - 1)] > floor_px
        ok &= out[ty.clip(0, h - 1), tx.clip(0, w - 1)] == 0         # cell free
        ok &= ~blocked[ty.clip(0, h - 1), tx.clip(0, w - 1)]          # separation floor
        if not ok.any():
            continue
        cand = np.flatnonzero(ok)
        d_target = density[ty[cand], tx[cand]]
        if mode == "spread":
            j = cand[np.argmin(d_target)]
        elif mode == "clump":
            j = cand[np.argmax(d_target)]
        else:
            j = cand[rng.integers(0, len(cand))]
        ny, nx = int(ty[j]), int(tx[j])
        out[y, x] = np.float32(0.0)
        out[ny, nx] = np.float32(1.0)
        y0, y1 = max(0, ny - 2), min(h, ny + 3)
        x0, x1 = max(0, nx - 2), min(w, nx + 3)
        blocked[y0:y1, x0:x1] |= _SEP[y0 - (ny - 2):y1 - (ny - 2), x0 - (nx - 2):x1 - (nx - 2)]
        moved += 1
        disp.append(float(np.hypot(ny - y, nx - x)))
        dens_from.append(float(density[y, x]))
        dens_to.append(float(density[ny, nx]))

    return {
        "dots": out,
        "n_moved": moved,
        "n_movable": int(movable.sum()),
        "n_blocked": int(movable.sum()) - moved,
        "mean_displacement_px": float(np.mean(disp)) if disp else 0.0,
        "max_displacement_px": float(np.max(disp)) if disp else 0.0,
        "mean_density_from": float(np.mean(dens_from)) if dens_from else 0.0,
        "mean_density_to": float(np.mean(dens_to)) if dens_to else 0.0,
    }


def nearest_neighbour_stats(dot: np.ndarray) -> dict:
    from scipy.spatial import cKDTree
    ys, xs = np.nonzero(dot)
    if len(ys) < 2:
        return {}
    pts = np.c_[ys, xs].astype(np.float64)
    d, _ = cKDTree(pts).query(pts, k=2)
    d = d[:, 1]
    return {
        "nn_min": float(d.min()),
        "nn_median": float(np.median(d)),
        "nn_p90": float(np.percentile(d, 90)),
        "pairs_lt_2p83": int((d < 2.83).sum()),
        "pairs_lt_2px": int((d < 2.0).sum()),
    }
