"""REPORT-ONLY local instruments. None of these is a score.

catalogue hide-and-recover PROXY
    Withhold a spatially blocked share of the mapped catalogue and ask how much
    triangular-kernel credit each candidate's dots place on the withheld cells.
    It measures "if new-fault truth looks like mapped-fault truth a few cells
    away, which arrangement covers it better". Prior sessions measured its
    correlation with live scores at -0.87..+0.54 on 12-14 files, so it is used
    to sanity-check the mechanism and NEVER as a gate.

leakage canary
    AUC of the per-dot "was this dot moved by the edit" indicator against
    "does this dot land kernel credit on a withheld catalogue cell". A value
    above 0.90 means the edit is target-proximal by construction (the edit is
    effectively reading the held-out truth) and the session must stop.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

R_PX = 3.0  # triangular kernel radius, 300 m at 100 m cells


def _credit_on(targets: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Best-dot triangular credit at each target cell. targets: (n,2) y,x."""
    if len(pts) == 0:
        return np.zeros(len(targets))
    tree = cKDTree(pts.astype(np.float64))
    d, _ = tree.query(targets.astype(np.float64), k=1, distance_upper_bound=R_PX)
    d = np.where(np.isfinite(d), d, R_PX)
    return np.clip(1.0 - d / R_PX, 0.0, 1.0)


def hide_and_recover(dot: np.ndarray, catalogue: np.ndarray, footprint: np.ndarray,
                     *, draws: int = 5, hold_frac: float = 0.2, block: int = 10,
                     seed: int = 91) -> dict:
    ys, xs = np.nonzero(dot)
    pts = np.c_[ys, xs]
    cys, cxs = np.nonzero(catalogue)
    cpts = np.c_[cys, cxs]
    rng = np.random.default_rng(seed)
    bid = (cys // block).astype(np.int64) * 100_000 + (cxs // block).astype(np.int64)
    uniq = np.unique(bid)
    out = []
    for _ in range(draws):
        take = rng.permutation(uniq)
        keep_blocks = set()
        n_hold = 0
        target = hold_frac * len(cpts)
        for b in take:
            if n_hold >= target:
                break
            keep_blocks.add(b)
            n_hold += int((bid == b).sum())
        held = np.isin(bid, list(keep_blocks))
        hp = cpts[held]
        credit = _credit_on(hp, pts)
        out.append({
            "n_held": int(held.sum()),
            "mean_credit": float(credit.mean()),
            "coverage": float((credit > 0).mean()),
        })
    mu = np.array([o["mean_credit"] for o in out])
    cv = np.array([o["coverage"] for o in out])
    half = 1.96 * mu.std(ddof=1) / np.sqrt(len(mu)) if len(mu) > 1 else 0.0
    return {
        "proxy_mean_credit": round(float(mu.mean()), 6),
        "proxy_mean_credit_ci95": round(float(half), 6),
        "proxy_coverage": round(float(cv.mean()), 6),
        "draws": draws,
        "hold_frac": hold_frac,
        "block_px": block,
        "n_held_per_draw": int(out[0]["n_held"]),
    }


def redundancy(dot: np.ndarray) -> dict:
    """Share of mass that duplicates a neighbour's kernel (overlap < 2R)."""
    ys, xs = np.nonzero(dot)
    pts = np.c_[ys, xs].astype(np.float64)
    if len(pts) < 2:
        return {}
    d, _ = cKDTree(pts).query(pts, k=2)
    nn = d[:, 1]
    return {
        "dots_with_neighbour_lt_2p83px": int((nn < 2.83).sum()),
        "dots_with_neighbour_lt_2px": int((nn < 2.0).sum()),
        "mean_nn_px": round(float(nn.mean()), 4),
    }


def block_density_cv(dot: np.ndarray, footprint: np.ndarray, size: int = 10) -> float:
    """CV of dot counts over the footprint's occupied blocks (prior sessions: R0 = 0.619)."""
    ys, xs = np.nonzero(dot)
    if len(ys) == 0:
        return float("nan")
    ids = (ys // size) * 100_000 + (xs // size)
    _, counts = np.unique(ids, return_counts=True)
    return round(float(counts.std() / counts.mean()), 4)


def _auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney AUC, no sklearn dependency. NaN when a class is empty."""
    pos = labels > 0.5
    n_pos, n_neg = int(pos.sum()), int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=np.float64)
    ranks[order] = np.arange(1, len(scores) + 1, dtype=np.float64)
    # average ranks across ties, otherwise a constant score would read as AUC 1.0
    uniq, inv, counts = np.unique(scores, return_inverse=True, return_counts=True)
    sums = np.zeros(len(uniq))
    np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def canary(moved: np.ndarray, dot: np.ndarray, catalogue: np.ndarray,
           *, draws: int = 3, hold_frac: float = 0.2, block: int = 10, seed: int = 7) -> dict:
    """AUC of moved-indicator against withheld-catalogue credit. > 0.90 => stop."""
    ys, xs = np.nonzero(dot)
    pts = np.c_[ys, xs]
    moved = np.asarray(moved, dtype=bool).reshape(dot.shape)[ys, xs]  # per-dot indicator
    cys, cxs = np.nonzero(catalogue)
    cpts = np.c_[cys, cxs]
    bid = (cys // block) * 100_000 + (cxs // block)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        held = np.isin(bid, rng.permutation(np.unique(bid))[: max(1, int(hold_frac * len(np.unique(bid))))])
        hp = cpts[held]
        # per-dot: does this dot sit within the kernel radius of a WITHHELD cell?
        dmin, _ = cKDTree(hp.astype(np.float64)).query(pts.astype(np.float64), k=1,
                                                       distance_upper_bound=R_PX)
        touched = np.isfinite(dmin)
        vals.append(_auc(moved.astype(float), touched.astype(float)))
    return {"canary_auc": round(float(np.mean(vals)), 4), "draws": draws,
            "stop_rule": "AUC > 0.90 means investigate before shipping"}


def _tri_kernel(r_px: float = R_PX) -> np.ndarray:
    n = int(np.ceil(r_px))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1]
    k = np.clip(1.0 - np.hypot(yy, xx) / r_px, 0.0, None)
    return k.astype(np.float32)


def uniform_truth_credit(dot: np.ndarray, footprint: np.ndarray) -> dict:
    """Expected kernel credit per footprint cell if truth were uniform (PROXY).

    This is the *ceiling* of what a spacing edit can buy: it is maximised by
    construction by the spread arm, because a uniform truth prior always prefers
    even coverage. It is reported to bound the size of the effect, never to
    predict its sign.
    """
    credit = ndi.convolve(dot.astype(np.float32), _tri_kernel(), mode="constant")
    credit = np.clip(credit, 0.0, 1.0)
    vals = credit[footprint]
    return {
        "uniform_truth_mean_credit": round(float(vals.mean()), 8),
        "uniform_truth_cells_uncovered": int((vals <= 0).sum()),
        "cells": int(vals.size),
    }
