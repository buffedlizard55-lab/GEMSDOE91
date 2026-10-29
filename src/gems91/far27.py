"""S27-FABRIC-FAR stratified, uniqueness-capped dot emission.

Preregistered in docs/s27/preregistration.md before any S27 result existed.
This module changes *emission geometry only*: it consumes a finished
probability surface and places binary dots by global surface-descending
greedy order, subject to (a) a catalogue collar, (b) minimum spacing,
(c) preregistered per-distance-band quotas, and optionally (d) per-reference
3-px overlap caps enforced *during* placement.

Nothing here trains a model, reads labels other than the visible catalogue
mask supplied by the caller, or knows any leaderboard score. Distance is to
the *visible* catalogue only (the fold-visible mask in holdout use, the full
catalogue in final-map use), exactly as the shared collar already used it.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage as ndi

FAR27_VERSION = "s27_far_v1"

# Frozen in docs/s27/preregistration.md (round a-priori shares; not fitted).
BAND_UPPER_EDGES_PX = (5.0, 10.0, 20.0, 40.0, float("inf"))
BAND_SHARES = (0.05, 0.15, 0.25, 0.25, 0.30)
CAP_FRACTION = 0.65


def band_quotas(budget: int, shares=BAND_SHARES) -> list[int]:
    """Deterministic largest-remainder split of `budget` by `shares`."""
    if budget < 0:
        raise ValueError("budget must be non-negative")
    raw = [budget * float(s) for s in shares]
    quotas = [int(math.floor(r)) for r in raw]
    remainder = budget - sum(quotas)
    order = sorted(range(len(shares)), key=lambda i: (-(raw[i] - quotas[i]), i))
    for i in order[:remainder]:
        quotas[i] += 1
    return quotas


def band_index(distance_px: float, collar_px: float, edges=BAND_UPPER_EDGES_PX) -> int:
    """Band of a single distance: (collar, e0], (e0, e1], ..., (e_last-1, inf)."""
    for i, e in enumerate(edges):
        if distance_px <= e:
            return i
    return len(edges) - 1


def _spacing_disk(min_spacing_px: float) -> list[tuple[int, int]]:
    rad = int(math.ceil(float(min_spacing_px)))
    return [
        (dy, dx)
        for dy in range(-rad, rad + 1)
        for dx in range(-rad, rad + 1)
        if math.hypot(dy, dx) < float(min_spacing_px)
    ]


def emit_dots_stratified(
    surface_2d: np.ndarray,
    visible_faults: np.ndarray,
    domain: np.ndarray,
    *,
    budget: int,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
    band_edges=BAND_UPPER_EDGES_PX,
    band_shares=BAND_SHARES,
    cap_bits: np.ndarray | None = None,
    cap_limit: int | None = None,
    n_cap_refs: int = 0,
) -> tuple[np.ndarray, dict]:
    """Greedy stratified emission. Returns ({0,1} float32 dots, info dict).

    `cap_bits` is an optional uint32 array: bit r set at pixel p means p lies
    within 3 px of cap reference r. A candidate is skipped if accepting it
    would push any cap reference's within-3-px count above `cap_limit`.
    Caps are checked only for candidates that pass spacing and quota, in
    both the quota pass and the redistribution pass.
    """
    surf = np.asarray(surface_2d, dtype=np.float32)
    dom = np.asarray(domain, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool) & dom
    if surf.ndim != 2 or surf.shape != dom.shape or vis.shape != dom.shape:
        raise ValueError("surface, visible_faults and domain must share a 2-D shape")
    if not np.isfinite(surf[dom]).all():
        raise ValueError("surface must be finite inside the emission domain")
    if budget <= 0:
        raise ValueError("budget must be positive")
    n_bands = len(band_edges)
    if len(band_shares) != n_bands:
        raise ValueError("band_edges and band_shares must have equal length")
    if cap_bits is not None:
        if cap_bits.shape != dom.shape or cap_bits.dtype != np.uint32:
            raise ValueError("cap_bits must be a uint32 array on the same grid")
        if cap_limit is None or n_cap_refs <= 0 or n_cap_refs > 32:
            raise ValueError("cap use requires cap_limit and 1 <= n_cap_refs <= 32")

    d_vis = (
        ndi.distance_transform_edt(~vis)
        if vis.any()
        else np.full(dom.shape, np.inf, dtype=np.float64)
    )
    allowed = dom & (~vis) & (d_vis > float(collar_px)) & (surf > 0.0)

    # Vectorised band assignment over the allowed set only.
    ys, xs = np.nonzero(allowed)
    if ys.size == 0:
        raise ValueError("no allowed emission candidates")
    dist = d_vis[ys, xs]
    bands = np.searchsorted(
        np.asarray(band_edges, dtype=np.float64), dist, side="left"
    ).astype(np.int64)
    bands = np.clip(bands, 0, n_bands - 1)

    order = np.argsort(-surf[ys, xs], kind="mergesort")
    ys, xs, bands = ys[order], xs[order], bands[order]

    quotas = band_quotas(int(budget), band_shares)
    counts = [0] * n_bands
    cap_counts = [0] * n_cap_refs
    h, w = dom.shape
    blocked = np.zeros((h, w), dtype=bool)
    out = np.zeros((h, w), dtype=np.float32)
    disk = _spacing_disk(float(min_spacing_px))
    placed = 0
    n_candidates = int(ys.size)

    def _cap_would_breach(y: int, x: int) -> bool:
        bits = int(cap_bits[y, x])
        r = 0
        while bits:
            if bits & 1 and cap_counts[r] >= cap_limit:
                return True
            bits >>= 1
            r += 1
        return False

    def _accept(y: int, x: int, b: int) -> None:
        nonlocal placed
        out[y, x] = 1.0
        counts[b] += 1
        placed += 1
        if cap_bits is not None:
            bits = int(cap_bits[y, x])
            r = 0
            while bits:
                if bits & 1:
                    cap_counts[r] += 1
                bits >>= 1
                r += 1
        for dy, dx in disk:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True

    ys_list, xs_list, band_list = ys.tolist(), xs.tolist(), bands.tolist()

    # Pass 1: respect band quotas.
    for y, x, b in zip(ys_list, xs_list, band_list):
        if placed >= budget:
            break
        if blocked[y, x] or counts[b] >= quotas[b]:
            continue
        if cap_bits is not None and _cap_would_breach(y, x):
            continue
        _accept(y, x, b)

    # Pass 2: redistribute any unfilled quota by the same global order.
    redistributed = 0
    if placed < budget:
        before = placed
        for y, x, b in zip(ys_list, xs_list, band_list):
            if placed >= budget:
                break
            if blocked[y, x]:
                continue
            if cap_bits is not None and _cap_would_breach(y, x):
                continue
            _accept(y, x, b)
        redistributed = placed - before

    info = {
        "emitter": FAR27_VERSION,
        "budget": int(budget),
        "n_placed": int(placed),
        "collar_px": float(collar_px),
        "min_spacing_px": float(min_spacing_px),
        "band_upper_edges_px": [
            (None if math.isinf(e) else float(e)) for e in band_edges
        ],
        "band_shares_preregistered": [float(s) for s in band_shares],
        "band_quotas": [int(q) for q in quotas],
        "band_counts_final": [int(c) for c in counts],
        "band_shares_final": [
            (float(c) / placed if placed else 0.0) for c in counts
        ],
        "redistributed_dots": int(redistributed),
        "n_allowed_candidates": n_candidates,
        "cap_refs": int(n_cap_refs),
        "cap_limit": (int(cap_limit) if cap_limit is not None else None),
        "cap_counts_final": [int(c) for c in cap_counts],
        "cap_max_fraction_final": (
            float(max(cap_counts) / placed) if (cap_counts and placed) else None
        ),
    }
    return out, info


def pack_cap_halos(
    support_masks: list[np.ndarray], footprint: np.ndarray
) -> np.ndarray:
    """Pack within-3-px halos of reference supports into a uint32 bitmask.

    Bit r of the returned array is set exactly where the Euclidean distance
    to reference r's positive support (inside the footprint) is <= 3.0 px —
    the same predicate `gems91.novelty.dot_check` uses, so cap enforcement
    and post-hoc dot checks agree by construction.
    """
    fp = np.asarray(footprint, dtype=bool)
    if len(support_masks) > 32:
        raise ValueError("at most 32 cap references fit a uint32 bitmask")
    bits = np.zeros(fp.shape, dtype=np.uint32)
    for r, support in enumerate(support_masks):
        sup = np.asarray(support, dtype=bool) & fp
        if sup.shape != fp.shape:
            raise ValueError("cap reference support off-grid")
        if not sup.any():
            continue
        halo = ndi.distance_transform_edt(~sup) <= 3.0
        bits |= (halo.astype(np.uint32) << np.uint32(r))
    return bits
