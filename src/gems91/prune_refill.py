"""Fixed-count PRUNE refill on the parent's H19-5 ridge support.

The support is a routing geometry inherited from R0, not fault truth and not a
score.  We use the brief's DTI algebra as a *coverage objective* on that support:
all retained and refill dots lie on support cells, so S == M and an addition's
exact DTI change is a strictly monotone function of its newly covered support
credit.  This lets a greedy heap rank by the exact marginal-DTI ordering while
updating only candidates whose 300 m kernels overlap the latest addition.

No catalogue hide/recover labels, leaderboard values, or regional probes enter
this module.  The catalogue is used only by the caller to define the PRUNE
collar, as the brief requires.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0


def kernel_offsets(radius: float = RADIUS_PX) -> list[tuple[int, int, float]]:
    """Positive triangular-kernel offsets, in deterministic row-major order."""
    span = int(np.ceil(radius))
    out = []
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            weight = 1.0 - float(np.hypot(dy, dx)) / radius
            if weight > 0.0:
                out.append((dy, dx, weight))
    return out


def best_credit(dots: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    """Maximum triangular credit from any dot at every grid cell.

    The triangular kernel decreases with distance, so the nearest dot is the
    maximum-credit dot.  EDT therefore computes the same max-kernel field as the
    metric's explicit offset loop, including its zero-credit cells at d >= R.
    """
    dots = np.asarray(dots, dtype=bool)
    if not dots.any():
        return np.zeros(dots.shape, dtype=np.float64)
    distance = ndi.distance_transform_edt(~dots)
    return np.clip(1.0 - distance / radius, 0.0, None)


def support_components(dots: np.ndarray, support: np.ndarray,
                       radius: float = RADIUS_PX) -> dict[str, float]:
    """Exact DTI components when every emitted dot is on the routing support."""
    dots = np.asarray(dots, dtype=bool)
    support = np.asarray(support, dtype=bool)
    if dots.shape != support.shape:
        raise ValueError("dots and support must share a shape")
    if np.any(dots & ~support):
        raise ValueError("support objective requires every dot to be on support")
    if not support.any():
        raise ValueError("support is empty")
    best = best_credit(dots, radius)
    T = float(best[support].sum())
    S = float(dots.sum())
    # Every dot itself is a support cell, hence max_g k = 1 and M = S.
    M = S
    G = float(support.sum())
    denominator = ALPHA * T + ALPHA * (S - M) + BETA * G
    return {"T": T, "S": S, "M": M, "G": G,
            "denominator": denominator,
            "objective_dti": T / denominator if denominator > 0 else 0.0}


def delta_support_credit(best: np.ndarray, support: np.ndarray, row: int, col: int,
                         radius: float = RADIUS_PX) -> float:
    """Exact delta_T from adding one dot, using only its affected local cells."""
    h, w = best.shape
    delta = 0.0
    for dy, dx, weight in kernel_offsets(radius):
        yy, xx = row + dy, col + dx
        if 0 <= yy < h and 0 <= xx < w and support[yy, xx]:
            delta += max(0.0, weight - float(best[yy, xx]))
    return float(delta)


def exact_add_delta(T: float, G: float, delta_T: float) -> float:
    """Exact marginal-DTI change for an on-support addition (dS = dM = 1)."""
    before_den = ALPHA * T + BETA * G
    after_den = ALPHA * (T + delta_T) + BETA * G
    before = T / before_den if before_den > 0 else 0.0
    after = (T + delta_T) / after_den if after_den > 0 else 0.0
    return float(after - before)


def _update_best(best: np.ndarray, support: np.ndarray, row: int, col: int,
                 radius: float = RADIUS_PX) -> float:
    """Apply one addition to the max-credit field; return its exact delta_T."""
    h, w = best.shape
    delta = 0.0
    for dy, dx, weight in kernel_offsets(radius):
        yy, xx = row + dy, col + dx
        if 0 <= yy < h and 0 <= xx < w and support[yy, xx]:
            improvement = weight - float(best[yy, xx])
            if improvement > 0.0:
                best[yy, xx] = weight
                delta += improvement
    return float(delta)


@dataclass
class RefillResult:
    added: np.ndarray
    stats: dict
    selections: list[dict]


def greedy_support_refill(survivors: np.ndarray, support: np.ndarray,
                          eligible: np.ndarray, n_add: int, *,
                          min_separation_px: float | None = 2.8,
                          radius: float = RADIUS_PX) -> RefillResult:
    """Select ``n_add`` cells by exact iterative marginal-DTI order.

    ``eligible`` must already enforce the PRUNE collar and footprint.  The
    optional d2.8 exclusion is applied both against survivors and iteratively
    against refill dots.  A candidate's delta_T depends only on routing-support
    cells within R, so only candidates within 2R of an addition need heap
    updates.  At any iteration exact marginal DTI is strictly monotone in
    delta_T (dS=dM=1); heap ordering by delta_T is therefore the exact marginal
    gain ordering, not the isolated-truth shortcut.
    """
    survivors = np.asarray(survivors, dtype=bool)
    support = np.asarray(support, dtype=bool)
    eligible = np.asarray(eligible, dtype=bool).copy()
    if survivors.shape != support.shape or survivors.shape != eligible.shape:
        raise ValueError("survivors, support and eligible grids must align")
    if n_add < 0:
        raise ValueError("n_add must be non-negative")
    if np.any(survivors & ~support) or np.any(eligible & ~support):
        raise ValueError("all survivor and refill cells must be on H19-5 support")
    if np.any(survivors & eligible):
        raise ValueError("eligible refill cells must exclude survivors")
    if n_add == 0:
        return RefillResult(np.zeros_like(survivors), {"n_add": 0}, [])
    n_eligible_before_separation = int(eligible.sum())
    if min_separation_px is not None:
        if min_separation_px < 0:
            raise ValueError("minimum separation must be non-negative")
        eligible &= ndi.distance_transform_edt(~survivors) > min_separation_px

    coords = np.argwhere(eligible)
    if len(coords) < n_add:
        raise ValueError(f"only {len(coords)} legal refill cells for {n_add} requested")
    n_candidates = len(coords)
    tree = cKDTree(coords.astype(np.float64))
    best = best_credit(survivors, radius)
    components = support_components(survivors, support, radius)
    T, G = components["T"], components["G"]

    current_delta = np.empty(n_candidates, dtype=np.float64)
    versions = np.zeros(n_candidates, dtype=np.int64)
    heap: list[tuple[float, int, int, int, int]] = []
    for idx, (row, col) in enumerate(coords):
        delta = delta_support_credit(best, support, int(row), int(col), radius)
        current_delta[idx] = delta
        # Deterministic ties: highest delta_T, then row, column, original index.
        heap.append((-delta, int(row), int(col), int(idx), 0))
    heapq.heapify(heap)

    selected = np.zeros(n_candidates, dtype=bool)
    blocked = np.zeros(n_candidates, dtype=bool)
    added = np.zeros_like(survivors)
    selections: list[dict] = []
    while len(selections) < n_add and heap:
        neg_delta, row, col, idx, version = heapq.heappop(heap)
        if selected[idx] or blocked[idx] or version != versions[idx]:
            continue
        # Re-read the current value; the heap key and version are deliberately
        # redundant guards against stale greedy choices.
        delta = float(current_delta[idx])
        if abs(delta + neg_delta) > 1e-10:
            continue
        before_T = T
        applied = _update_best(best, support, row, col, radius)
        if not np.isclose(applied, delta, rtol=0.0, atol=1e-10):
            raise AssertionError(f"stale marginal gain at {(row, col)}: {delta} != {applied}")
        exact_delta = exact_add_delta(before_T, G, applied)
        T = before_T + applied
        selected[idx] = True
        added[row, col] = True
        selections.append({"rank": len(selections) + 1, "row": row, "col": col,
                           "delta_support_credit": applied,
                           "exact_marginal_dti_delta_MODEL": exact_delta})

        if min_separation_px is not None:
            close = tree.query_ball_point([row, col], r=min_separation_px)
            if close:
                blocked[np.asarray(close, dtype=int)] = True

        # Only overlapping kernels can change delta_T.  The global DTI level
        # changes for everyone, but not the *ordering*: exact_add_delta is
        # strictly monotone in delta_T at a shared iteration baseline.
        affected = tree.query_ball_point([row, col], r=2.0 * radius)
        for other in affected:
            if selected[other] or blocked[other]:
                continue
            oy, ox = map(int, coords[other])
            new_delta = delta_support_credit(best, support, oy, ox, radius)
            current_delta[other] = new_delta
            versions[other] += 1
            heapq.heappush(heap, (-new_delta, oy, ox, int(other),
                                  int(versions[other])))

    if len(selections) != n_add:
        raise ValueError(
            f"only {len(selections)} refill cells feasible under "
            f"min_separation_px={min_separation_px}; requested {n_add}")
    if int(added.sum()) != n_add or np.any(added & survivors):
        raise AssertionError("fixed-count refill invariant failed")
    if min_separation_px is not None and n_add > 1:
        nearest = cKDTree(np.argwhere(added)).query(np.argwhere(added), k=2)[0][:, 1]
        if float(nearest.min()) <= min_separation_px + 1e-10:
            raise AssertionError("refill violated minimum separation")
    stats = {
        "n_add": int(n_add),
        "n_candidates_before_separation": n_eligible_before_separation,
        "n_candidates": int(n_candidates),
        "n_selected": int(len(selections)),
        "min_separation_px": min_separation_px,
        "selection_rule": "exact iterative marginal-DTI order on H19-5 support; delta_T heap key is exactly monotone",
        "support_credit_before": float(components["T"]),
        "support_credit_after": float(T),
        "support_credit_added": float(T - components["T"]),
        "exact_objective_delta_MODEL": exact_add_delta(components["T"], G, T - components["T"]),
    }
    return RefillResult(added=added, stats=stats, selections=selections)
