"""DTI metric and exact marginal-gain ranking for the GEMS Prize (DrivenData #306).

Two jobs:

1. ``dti(pred, truth)`` -- the competition metric, written from the derived algebra
   in the agent brief (section 2), which is the only form pinned in this repo:

       DTI = T / (alpha*T + alpha*(S - M) + beta*|G|)

   with alpha=0.2, beta=0.8, T = kernel credit, S = sum of predictions,
   M = sum over predicted pixels of p_j * (max kernel weight to any true pixel),
   |G| = number of true-fault pixels. Kernel: triangular, R = 300 m = 3 px at 100 m.

2. ``marginal_gain`` / ``rank_dots`` -- the EXACT change in DTI from adding or
   removing one dot. The brief's cheap rule (for an isolated truth pixel a dot
   pays iff its kernel weight k > 0.2*DTI) is a special case; line-like truth
   lowers the bar, so rankings must come from this code, not from the shortcut.

Status: unit-tested (see tests/test_dti.py). NOT validated against the official
scorer -- the metric page may not be fetched from this sandbox (brief section
4.1), so the brief's algebra is treated as the specification. See
IRREGULARITIES.md item 5 for the aggregate-vs-per-pixel ambiguity.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PX_M = 100.0
KERNEL_RADIUS_M = 300.0
ALPHA = 0.2
BETA = 0.8


def kernel_radius_px(radius_m: float = KERNEL_RADIUS_M, px_m: float = PX_M) -> int:
    r = radius_m / px_m
    if abs(r - round(r)) > 1e-9:
        raise ValueError(f"kernel radius {radius_m} m / {px_m} m is not an integer pixel count")
    return int(round(r))


def _kernel_offsets(radius: int):
    """(dy, dx, weight) for every offset with a strictly positive triangular weight."""
    idx = np.arange(-radius, radius + 1)
    dx, dy = np.meshgrid(idx, idx, indexing="xy")
    dist = np.hypot(dx, dy).astype(np.float64)
    k = np.clip(1.0 - dist / radius, 0.0, None)
    keep = k > 0.0
    return dy[keep], dx[keep], k[keep]


def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """out[y, x] = a[y - dy, x - dx], zero outside the array."""
    out = np.zeros_like(a)
    h, w = a.shape
    ys_src = slice(max(0, -dy), h - max(0, dy))
    ys_dst = slice(max(0, dy), h - max(0, -dy))
    xs_src = slice(max(0, -dx), w - max(0, dx))
    xs_dst = slice(max(0, dx), w - max(0, -dx))
    out[ys_dst, xs_dst] = a[ys_src, xs_src]
    return out


def kernel_credit(pred: np.ndarray, truth: np.ndarray, radius: int | None = None) -> float:
    """T: sum over true pixels of max_j (p_j * k(dist(pred_j, truth_i))).

    Built from shifted elementwise maxes so it needs no scipy and no
    full distance matrix; memory is O(pixels), time O(pixels * offsets).
    """
    radius = kernel_radius_px() if radius is None else radius
    p = _clean(pred)
    g = _clean(truth) > 0
    best = np.zeros_like(p)
    for dy, dx, k in zip(*_kernel_offsets(radius)):
        cand = _shift(p, dy, dx) * k
        np.maximum(best, cand, out=best)
    return float(best[g].sum())


def capped_mass(pred: np.ndarray, truth: np.ndarray, radius: int | None = None) -> float:
    """M: sum over predicted pixels of p_j * max_i k(dist(pred_j, truth_i)), i true."""
    radius = kernel_radius_px() if radius is None else radius
    p = _clean(pred)
    g = (_clean(truth) > 0).astype(np.float64)
    best = np.zeros(p.shape, dtype=np.float64)
    for dy, dx, k in zip(*_kernel_offsets(radius)):
        cand = _shift(g, dy, dx) * k
        np.maximum(best, cand, out=best)
    return float((p * best).sum())


@dataclass(frozen=True)
class Components:
    T: float
    S: float
    M: float
    G: float
    score: float

    def as_dict(self) -> dict[str, float]:
        return {"T": self.T, "S": self.S, "M": self.M, "G": self.G, "dti": self.score}


def _clean(a: np.ndarray) -> np.ndarray:
    """NaN/Inf -> 0. A raster's null pixels outside the footprint carry no mass."""
    return np.nan_to_num(np.asarray(a, dtype=np.float64), nan=0.0, posinf=0.0, neginf=0.0)


def components(
    pred: np.ndarray,
    truth: np.ndarray,
    alpha: float = ALPHA,
    beta: float = BETA,
    radius: int | None = None,
) -> Components:
    p = _clean(pred)
    t = _clean(truth)
    T = kernel_credit(p, t, radius)
    M = capped_mass(p, t, radius)
    S = float(p.sum())
    G = float((t > 0).sum())
    den = alpha * T + alpha * (S - M) + beta * G
    score = 0.0 if den <= 0 else T / den
    return Components(T=T, S=S, M=M, G=G, score=score)


def dti(
    pred: np.ndarray,
    truth: np.ndarray,
    alpha: float = ALPHA,
    beta: float = BETA,
    radius: int | None = None,
) -> float:
    """Aggregate DTI (a single score for the whole raster)."""
    return components(pred, truth, alpha, beta, radius).score


@dataclass(frozen=True)
class Gain:
    """Exact change in the metric from one edit.

    ``ratio`` = dN/dD is the quantity the metric compares against the current
    DTI: the edit raises the score iff ratio > current DTI (when dD > 0).
    """

    delta_T: float
    delta_S: float
    delta_M: float
    delta_num: float
    delta_den: float
    delta_dti: float

    @property
    def ratio(self) -> float:
        if self.delta_den == 0.0:
            return float("inf") if self.delta_num > 0 else float("-inf")
        return self.delta_num / self.delta_den


def _crop(a: np.ndarray, iy: int, ix: int, half: int) -> np.ndarray:
    """Crop with zero padding; returns the window centred on (iy, ix)."""
    h, w = a.shape
    y0, y1 = iy - half, iy + half + 1
    x0, x1 = ix - half, ix + half + 1
    out = np.zeros((2 * half + 1, 2 * half + 1), dtype=np.float64)
    sy0, sy1 = max(0, y0), min(h, y1)
    sx0, sx1 = max(0, x0), min(w, x1)
    out[sy0 - y0 : sy1 - y0, sx0 - x0 : sx1 - x0] = a[sy0:sy1, sx0:sx1]
    return out


def marginal_gain(
    pred: np.ndarray,
    truth: np.ndarray,
    iy: int,
    ix: int,
    value: float = 1.0,
    mode: str = "add",
    alpha: float = ALPHA,
    beta: float = BETA,
    radius: int | None = None,
) -> Gain:
    """Exact DTI change from putting ``value`` on pixel (iy, ix) or taking it off.

    Only predictions at the edited pixel and only truth pixels within the kernel
    of it can change the score, so the delta is computed on a (4R+1)^2 window.
    Every window that contains the edited pixel lies well inside that crop, so
    no neighbour is lost; tests/test_dti.py checks this against a full recompute.
    """
    if mode not in {"add", "remove"}:
        raise ValueError("mode must be 'add' or 'remove'")
    radius = kernel_radius_px() if radius is None else radius
    p = _clean(pred)
    t = _clean(truth)
    base = components(p, t, alpha, beta, radius)

    old = float(p[iy, ix])
    new = min(1.0, old + value) if mode == "add" else max(0.0, old - value)
    if new == old:
        return Gain(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    half = 2 * radius
    pc = _crop(p, iy, ix, half)
    tc = _crop(t, iy, ix, half)
    cy = cx = half

    before_T = kernel_credit(pc, tc, radius)
    before_M = capped_mass(pc, tc, radius)

    p2 = pc.copy()
    p2[cy, cx] = new
    after_T = kernel_credit(p2, tc, radius)
    after_M = capped_mass(p2, tc, radius)

    dT, dM, dS = after_T - before_T, after_M - before_M, new - old
    dnum = dT
    dden = alpha * dT + alpha * (dS - dM)  # |G| is unchanged by a prediction edit
    new_den = alpha * (base.T + dT) + alpha * ((base.S + dS) - (base.M + dM)) + beta * base.G
    new_score = 0.0 if new_den <= 0 else (base.T + dnum) / new_den
    return Gain(dT, dS, dM, dnum, dden, new_score - base.score)


def rank_dots(
    pred: np.ndarray,
    truth: np.ndarray,
    candidates,
    value: float = 1.0,
    mode: str = "add",
    radius: int | None = None,
) -> list[tuple[float, int, int]]:
    """Rank candidate pixels by exact marginal gain, best first.

    ``candidates`` is an iterable of (iy, ix). Returns [(delta_dti, iy, ix), ...].
    Use with PROXY truth only (a local holdout); live truth is not available.
    """
    gains = []
    for iy, ix in candidates:
        g = marginal_gain(pred, truth, int(iy), int(ix), value, mode, radius=radius)
        gains.append((g.delta_dti, int(iy), int(ix)))
    gains.sort(reverse=True)
    return gains
