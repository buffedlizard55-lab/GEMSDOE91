"""DTI algebra and dot ranking for the GEMS prize (DrivenData #306).

STATUS: the *official* metric implementation is NOT in this repository and is not
reachable from the sandbox. Everything here is a local MODEL of the algebra stated
in the agent brief (section 2):

    DTI = T / (0.2*T + 0.2*(S - M) + 0.8*|G|)

with

    T  = kernel credit  = sum over truth pixels of min(1, sum_dots p_d * k(d, t))
    S  = sum p          = total predicted mass (one unit per dot here)
    M  = sum p*max_g k  = predicted mass that actually lands near truth
    G  = truth-side term; treated here as a CONSTANT with respect to the candidate
         dot (see ASSUMPTIONS below)
    k  = triangular kernel, radius 300 m = 3 px, weight = max(0, 1 - d_px/3)

ASSUMPTIONS (explicit, because they are not verifiable from this sandbox):
  A1. p = 1 for every dot (R0 is unit-mass: 37,654 dots, no probabilities).
  A2. T is capped at 1 per truth pixel (a truth pixel cannot pay twice).
  A3. |G| does not change when a candidate dot is added. This is what makes the
      brief's shortcut exact: adding a dot with credit c gives
          dT = c, dS = +1, dM = +c
          dDenominator = 0.2*c + 0.2*(1 - c) + 0 = +0.2   (the +c cancels)
      so  (T+c)/(D+0.2) > T/D  <=>  c > 0.2*T/D = 0.2*DTI.
      At DTI = 0.28 that bar is 0.056, matching the brief.
      If the official metric instead lets |G| shrink as truth is covered, the bar
      moves to 0.2*DTI/(1+0.8*DTI) = 0.0458 at DTI = 0.28. Both are close; the
      ranking ORDER of dots in a local window is barely affected, absolute
      predictions are. Flagged in IRREGULARITIES.md; resolve against real metric
      code before quoting any absolute number to a slot decision.

Nothing in this module returns or estimates a leaderboard score. All outputs are
MODEL quantities computed on a supplied truth mask.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

ALPHA = 0.2   # weight on T            (brief)
BETA = 0.8    # weight on |G|          (brief)
ZETA = 0.2    # weight on (S - M)      (brief)
RADIUS_PX = 3.0  # 300 m kernel at 100 m pixels


# --------------------------------------------------------------------------- #
# kernel
# --------------------------------------------------------------------------- #
def triangular_weight(d_px: np.ndarray | float, radius_px: float = RADIUS_PX):
    """Triangular kernel on Euclidean pixel-centre distance in pixels.

    weight(d) = max(0, 1 - d/radius). Weight is 0 at and beyond the radius, so the
    support is strictly inside `radius_px` (a dot 3 px away contributes nothing).
    Distance is measured on pixel centres, i.e. integer offsets, which is the only
    reading consistent with "R = 300 m (3 px)" on a 100 m grid.
    """
    d = np.asarray(d_px, dtype=np.float64)
    return np.maximum(0.0, 1.0 - d / float(radius_px))


def window_offsets(radius_px: float = RADIUS_PX) -> tuple[np.ndarray, np.ndarray]:
    """Integer (dr, dc) offsets with radius, plus their kernel weights."""
    r = int(np.floor(radius_px))
    rr, cc = np.mgrid[-r : r + 1, -r : r + 1]
    w = triangular_weight(np.hypot(rr, cc), radius_px)
    keep = w > 0
    return rr[keep], cc[keep], w[keep]


# --------------------------------------------------------------------------- #
# credit map and score
# --------------------------------------------------------------------------- #
def credit_map(
    shape: tuple[int, int],
    dots: np.ndarray,
    shape_mask: np.ndarray | None = None,
    radius_px: float = RADIUS_PX,
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """Uncapped kernel credit per pixel: sum_d p_d * k(d, pixel).

    `dots` is (N, 2) float array of (row, col) pixel coordinates, not required to be
    integer. `shape_mask` (bool) restricts accumulation to True pixels (e.g. the
    submission footprint); contributions to False pixels are dropped.
    """
    dots = np.asarray(dots, dtype=np.float64)
    if dots.size == 0:
        return np.zeros(shape, dtype=np.float64)
    if dots.ndim != 2 or dots.shape[1] != 2:
        raise ValueError(f"dots must be (N,2); got {dots.shape}")
    p = np.ones(len(dots), dtype=np.float64) if weights is None else np.asarray(weights, float)
    if p.shape != (len(dots),):
        raise ValueError("weights must broadcast to one value per dot")

    out = np.zeros(shape, dtype=np.float64)
    nrow, ncol = shape

    # Closed-form distance for each integer offset: a dot at (ri+fr, ci+fc) is
    # hypot(fr-dr, fc-dc) from pixel (ri+dr, ci+dc). Vectorised over dots, one
    # pass per kernel offset (~29 passes at radius 3).
    ri = np.floor(dots[:, 0]).astype(np.int64)
    ci = np.floor(dots[:, 1]).astype(np.int64)
    fr = dots[:, 0] - ri
    fc = dots[:, 1] - ci
    rr, cc, _w = window_offsets(radius_px)
    for dr, dc, _wk in zip(rr, cc, _w):
        r = ri + dr
        c = ci + dc
        ok = (r >= 0) & (r < nrow) & (c >= 0) & (c < ncol)
        if not ok.any():
            continue
        w = triangular_weight(np.hypot(fr[ok] - dr, fc[ok] - dc), radius_px) * p[ok]
        np.add.at(out, (r[ok], c[ok]), w)
    if shape_mask is not None:
        out *= np.asarray(shape_mask, dtype=np.float64)
    return out


def totals(credit: np.ndarray, truth: np.ndarray, n_dots: int):
    """(T, S, M_share) for a fully specified configuration.

    S = n_dots (unit mass per dot, assumption A1).
    M is not recoverable from the credit map alone (it is a per-dot quantity), so it
    is computed by the callers that have dot coordinates; here we return what the
    map supports: T, S, and the per-truth-pixel coverage profile.
    """
    credit = np.asarray(credit, float)
    covered = np.minimum(1.0, credit)
    T = float(covered[np.asarray(truth, bool)].sum())
    return T, float(n_dots)


def dti(T: float, S: float, M: float, G: float) -> float:
    """The brief's algebra, evaluated exactly as stated."""
    den = ALPHA * T + ZETA * (S - M) + BETA * abs(G)
    if den <= 0:
        return 0.0
    return float(T) / float(den)


def pay_threshold(dti_value: float) -> float:
    """Minimum kernel credit for one extra unit-mass dot to pay (A3)."""
    return ALPHA * float(dti_value)


# --------------------------------------------------------------------------- #
# marginal gain
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class DotMarginal:
    """Marginal gain of adding one unit-mass dot to a fixed configuration."""

    index: int
    row: float
    col: float
    credit: float       # c  = sum of k over truth pixels in the dot's window
    delta_t: float      # dT = sum of capped increment in T
    delta_s: float      # dS = +1 (unit mass)
    delta_m: float      # dM = max kernel weight of this dot against any truth pixel
    gain: float         # exact delta of the formula under assumptions A1-A3

    @property
    def pays(self) -> bool:
        return self.gain > 0.0


def _gain(T: float, S: float, M: float, G: float, dT: float, dS: float, dM: float) -> float:
    before = dti(T, S, M, G)
    after = dti(T + dT, S + dS, M + dM, G)
    return after - before


def score_additions(
    truth: np.ndarray,
    dots: np.ndarray,
    credit: np.ndarray | None = None,
    T: float | None = None,
    M: float | None = None,
    G: float | None = None,
    radius_px: float = RADIUS_PX,
    weights: np.ndarray | None = None,
) -> list[DotMarginal]:
    """Exact first-order marginal gain for each candidate dot, in parallel.

    This is the quantity the brief says to rank by ("rank dots by exact marginal
    gain from the metric code, not the shortcut"). Because each dot is scored
    against the SAME credit map, the ordering is a ranking hint, not a greedy
    solution: dots that share a truth pixel are double-counted. Use
    `greedy_select` when the selection order matters.

    M must be supplied by the caller (it is a per-dot property of the existing
    configuration). If omitted it is taken as sum(credit*truth), the best available
    proxy for "mass that landed near truth".
    """
    truth = np.asarray(truth, bool)
    dots = np.asarray(dots, float)
    n = len(dots)
    if n == 0:
        return []
    if credit is None:
        # `dots` are the CANDIDATES; the credit map must describe the EXISTING
        # configuration only. Building it from the candidates would let every dot
        # see its own contribution already counted and report dT = 0.
        credit = np.zeros(truth.shape, dtype=np.float64)
    if T is None:
        T = float(np.minimum(1.0, credit)[truth].sum())
    if weights is not None:
        weights = np.asarray(weights, float)
    capped = np.minimum(1.0, credit)
    if M is None:
        M = float((capped * truth).sum())
    if G is None:
        G = float(truth.sum()) - T  # default reading: uncovered truth

    rr, cc, w = window_offsets(radius_px)
    nrow, ncol = truth.shape
    out: list[DotMarginal] = []
    for i in range(n):
        r0 = int(np.floor(dots[i, 0]))
        c0 = int(np.floor(dots[i, 1]))
        delta_t = 0.0
        credit_i = 0.0
        best = 0.0
        for dr, dc, wk in zip(rr, cc, w):
            r, c = r0 + dr, c0 + dc
            if not (0 <= r < nrow and 0 <= c < ncol):
                continue
            if not truth[r, c]:
                continue
            # fractional coverage added by this dot at this truth pixel
            dd = np.hypot(dots[i, 0] - r, dots[i, 1] - c)
            wi = float(triangular_weight(dd, radius_px))
            if wi <= 0:
                continue
            credit_i += wi
            best = max(best, wi)
            delta_t += min(1.0, capped[r, c] + wi) - capped[r, c]
        out.append(
            DotMarginal(
                index=i,
                row=float(dots[i, 0]),
                col=float(dots[i, 1]),
                credit=credit_i,
                delta_t=delta_t,
                delta_s=1.0,
                delta_m=best,
                gain=_gain(T, float(n), float(M), float(G), delta_t, 1.0, best),
            )
        )
    return out


def greedy_select(
    truth: np.ndarray,
    candidates: np.ndarray,
    k: int,
    G: float | None = None,
    radius_px: float = RADIUS_PX,
    start_credit: np.ndarray | None = None,
    start_n: int = 0,
) -> list[DotMarginal]:
    """Greedily add `k` dots of unit mass, updating credit after each pick.

    This is the honest ranking when dots compete for the same truth pixels (a line
    or a dense cluster). Cost is O(k * n_candidates * support); intended for small
    truth masks and tests, not for 37k dots in one call.
    """
    truth = np.asarray(truth, bool)
    cand = np.asarray(candidates, float)
    if G is None:
        G = float(truth.sum())
    credit = np.zeros(truth.shape, float) if start_credit is None else np.array(start_credit, float)
    T = float(np.minimum(1.0, credit)[truth].sum())
    S = float(start_n)
    M = float((np.minimum(1.0, credit) * truth).sum())
    nrow, ncol = truth.shape

    def window_deltas(row: float, col: float) -> tuple[float, float, float]:
        """(dT, credit_window, best_weight) for one dot against the current credit."""
        dT = credit_w = best_w = 0.0
        for dr, dc, _wk in zip(*window_offsets(radius_px)):
            r, c = int(np.floor(row)) + dr, int(np.floor(col)) + dc
            if not (0 <= r < nrow and 0 <= c < ncol) or not truth[r, c]:
                continue
            w = float(triangular_weight(np.hypot(row - r, col - c), radius_px))
            if w <= 0.0:
                continue
            credit_w += w
            best_w = max(best_w, w)
            dT += min(1.0, credit[r, c] + w) - min(1.0, credit[r, c])
        return dT, credit_w, best_w

    chosen: list[DotMarginal] = []
    used: set[int] = set()
    for _ in range(min(k, len(cand))):
        best_i, best = None, None
        for i in range(len(cand)):
            if i in used:
                continue
            dT, credit_w, best_w = window_deltas(cand[i, 0], cand[i, 1])
            g = _gain(T, S, M, float(G), dT, 1.0, best_w)
            if best is None or g > best.gain:
                best_i = i
                best = DotMarginal(i, float(cand[i, 0]), float(cand[i, 1]),
                                   credit_w, dT, 1.0, best_w, g)
        if best_i is None or best is None:
            break
        used.add(best_i)
        for dr, dc, _wk in zip(*window_offsets(radius_px)):
            r, c = int(np.floor(cand[best_i, 0])) + dr, int(np.floor(cand[best_i, 1])) + dc
            if 0 <= r < nrow and 0 <= c < ncol:
                credit[r, c] += float(
                    triangular_weight(np.hypot(cand[best_i, 0] - r, cand[best_i, 1] - c), radius_px)
                )
        T = float(np.minimum(1.0, credit)[truth].sum())
        S += 1.0
        M += best.delta_m
        chosen.append(best)
    return chosen
