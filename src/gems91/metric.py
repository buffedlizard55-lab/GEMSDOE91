"""DTI metric, re-derived from the competition brief rather than copied.

Formula (brief section 2, derived, NOT read from organiser source):

    DTI = T / (alpha*T + alpha*(S - M) + beta*|G|)

    T      = total kernel credit: for every truth pixel, the sum of
             p * k(distance) over candidate dots within the kernel radius
    S      = total predicted mass (sum of p over all dots)
    M      = sum over dots of p * max_g k  (mass that found a truth pixel)
    |G|    = number of truth pixels
    alpha  = 0.2, beta = 0.8, triangular kernel, R = 300 m = 3 px at 100 m

Consequences the unit tests pin down:
  * a single dot on an isolated truth pixel is a perfect prediction (DTI = 1)
  * mass that matches no truth pixel strictly lowers DTI; mass that fully
    matches a truth pixel (max_g k = 1) costs nothing in the denominator, so
    every gram of it that earns credit is a gain
  * the brief's rule of thumb "a dot pays iff credit > alpha * DTI" (~0.056 at
    DTI 0.28) is NOT an identity of this formula: it is the break-even condition
    for mass that is *unmatched*, which is why it is only a shortcut. Ranking by
    the shortcut is safe only for isolated truth; line-like truth lowers the
    bar. `marginal_gain` below is the authority, and `isolated_truth_pays`
    exposes the rule of thumb for comparison only.

CAVEAT: this is a MODEL of the organiser metric. It has never been diffed
against organiser code (that code is not public and the terms ban automated
access). Do not quote its output as a score; label it MODEL.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
PIXEL_M = 100.0


def triangular_kernel(distance_px: np.ndarray | float, radius_px: float = RADIUS_PX):
    """k(r) = max(0, 1 - r/R). Zero at and beyond R."""
    d = np.asarray(distance_px, dtype=np.float64)
    return np.maximum(0.0, 1.0 - d / float(radius_px))


def _offsets(radius_px: float) -> list[tuple[int, int, float]]:
    """Integer (dr, dc, k) stencil for the triangular kernel."""
    span = int(math.ceil(radius_px))
    out = []
    for dr in range(-span, span + 1):
        for dc in range(-span, span + 1):
            k = float(triangular_kernel(math.hypot(dr, dc), radius_px))
            if k > 0.0:
                out.append((dr, dc, k))
    return out


@dataclass(frozen=True)
class DtiParts:
    T: float
    S: float
    M: float
    n_truth: int

    def dti(self, alpha: float = ALPHA, beta: float = BETA) -> float:
        denom = alpha * self.T + alpha * (self.S - self.M) + beta * self.n_truth
        if denom <= 0.0:
            raise ValueError("degenerate DTI denominator (no truth, no mass)")
        return self.T / denom


def _check_grid(pred: np.ndarray, truth: np.ndarray) -> None:
    if pred.shape != truth.shape:
        raise ValueError(f"shape mismatch: pred {pred.shape} vs truth {truth.shape}")
    if pred.ndim != 2:
        raise ValueError("expected 2-D arrays")
    if np.any(pred < 0):
        raise ValueError("negative predicted mass")


def components(
    pred: np.ndarray,
    truth: np.ndarray,
    radius_px: float = RADIUS_PX,
    extra_mass: tuple[int, int, float] | None = None,
) -> DtiParts:
    """Compute (T, S, M, |G|).

    `extra_mass=(row, col, p)` adds one hypothetical dot without copying the
    whole prediction array, so exact marginal gain stays cheap.
    """
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, dtype=bool)
    _check_grid(pred, truth)
    if not truth.any():
        raise ValueError("truth set is empty; DTI undefined")

    mass = pred
    offsets = _offsets(radius_px)

    # T: credit accumulated on truth pixels by every dot.
    credit = np.zeros_like(pred)
    for dr, dc, k in offsets:
        credit += k * _shift(pred, dr, dc)
    if extra_mass is not None:
        r, c, p = extra_mass
        for dr, dc, k in offsets:
            tr, tc = r + dr, c + dc
            if 0 <= tr < credit.shape[0] and 0 <= tc < credit.shape[1]:
                credit[tr, tc] += p * k
    T = float(credit[truth].sum())

    # M: for each dot, its best match anywhere on the truth set (saturated at 1).
    truth_dilate = np.zeros_like(pred)
    for dr, dc, k in offsets:
        truth_dilate = np.maximum(truth_dilate, k * _shift(truth.astype(np.float64), dr, dc))
    M = float((mass * truth_dilate).sum())
    if extra_mass is not None:
        r, c, p = extra_mass
        # truth_dilate already holds max_g k for a dot at this exact cell.
        M += float(p * truth_dilate[r, c])

    total_mass = float(mass.sum()) + (extra_mass[2] if extra_mass else 0.0)
    return DtiParts(T=T, S=total_mass, M=M, n_truth=int(truth.sum()))


def _shift(a: np.ndarray, dr: int, dc: int) -> np.ndarray:
    """out[r, c] = a[r - dr, c - dc], zero outside."""
    out = np.zeros_like(a)
    h, w = a.shape
    rs_src = slice(max(0, -dr), min(h, h - dr))
    rs_dst = slice(max(0, dr), min(h, h + dr))
    cs_src = slice(max(0, -dc), min(w, w - dc))
    cs_dst = slice(max(0, dc), min(w, w + dc))
    out[rs_dst, cs_dst] = a[rs_src, cs_src]
    return out


def dti(pred: np.ndarray, truth: np.ndarray, radius_px: float = RADIUS_PX,
        alpha: float = ALPHA, beta: float = BETA) -> float:
    return components(pred, truth, radius_px).dti(alpha, beta)


def marginal_gain(pred: np.ndarray, truth: np.ndarray, row: int, col: int,
                  p: float = 1.0, radius_px: float = RADIUS_PX,
                  alpha: float = ALPHA, beta: float = BETA) -> float:
    """Exact change in DTI from emitting one extra dot of mass `p` at (row, col).

    This is the authority for ranking dots (brief section 2). Negative when the
    extra mass costs more in the (S - M) penalty than it earns in credit.
    """
    base = components(pred, truth, radius_px)
    after = components(pred, truth, radius_px, extra_mass=(int(row), int(col), float(p)))
    return after.dti(alpha, beta) - base.dti(alpha, beta)


def isolated_truth_pays(credit: float, dti_value: float, alpha: float = ALPHA) -> bool:
    """Rule of thumb from brief section 2: break-even for UNMATCHED extra mass.

    A dot that earns credit `c` while adding mass to (S - M) shifts DTI to
    (T + c) / (D + alpha*p); the sign of the change is c*p*D > alpha*p*T, i.e.
    c > alpha*DTI. Reported for comparison with `marginal_gain`, never used to
    rank dots.
    """
    return credit > alpha * dti_value
