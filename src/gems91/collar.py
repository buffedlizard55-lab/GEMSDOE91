"""CONCENTRATION on the *legal collar*: move dots into the 3-6 px band around mapped traces.

Why this prior, and why it is not a re-run of the seven CONCENTRATION rows already in
the fleet ledger (all of which moved mass using the GDR thermal prior, i.e. away from
the mapped catalogue):

* The organiser states that new-fault truth may lie within 300 m (3 px) of known
  traces and that pixels *beside* known faults are scored normally against
  new-fault truth only (community.drivendata.org/t/.../11516).
* Measured here, not assumed: per-cell fault credit density falls monotonically with
  distance from the mapped catalogue.  On the independent, public-domain SGMC
  catalogue the 3-4.5 px band carries 0.053 credit/cell versus 0.041 at >10 px
  (1.3x); on the lineage's own H19-5 field 0.021 versus 0.010 (2.2x).
* R0 spends only 13.2 % of its dots inside that band and 49.4 % more than 10 px away.

The edit is a *relocation at fixed count and fixed unit mass*: no dot is added, no dot
changes mass, `S` is untouched, so `(S - M)` can only fall or stay equal and the whole
effect rides on `T` (the numerator) and `M` (the denominator's matched-mass term).

Hard rules encoded here (brief section 4.4):
  * never place a dot on a catalogue pixel;
  * never place a dot closer than ``COLLAR_FLOOR_PX`` (3 px) to the catalogue;
  * never reduce the parent's own spacing floor (R0's nearest dot pair is 2.828 px, so
    a placement is refused if it would create a pair closer than that);
  * everything deterministic: a fixed accept order with an index tie-break.

Nothing in this module reads withheld truth, and nothing writes files.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

#: Brief 4.4 -- mass must stay >= 3 px from the mapped catalogue outside AXIS=PRUNE.
COLLAR_FLOOR_PX = 3.0
#: A tenth of a pixel of float head-room: the gate tests `> 3.0`, this keeps the
#: intended cells deterministic under any distance rounding.
COLLAR_FLOOR_MARGIN_PX = 0.05
#: Outer edge of the "legal collar" band, in pixels (600 m at 100 m cells).
COLLAR_OUTER_PX = 6.0
#: R0's own nearest-neighbour distance, measured from the pinned parent
#: (proxy.redundancy -> min_nn_px = 2.8284271).  Placements honour the same floor,
#: so an arm changes location without silently changing local spacing.
PARENT_MIN_NN_PX = 2.8284271247461903
#: Distance beyond which a cell counts as "remote" for the mirrored control arm.
REMOTE_MIN_PX = 10.0

#: integer offsets strictly closer than PARENT_MIN_NN_PX (dr^2 + dc^2 <= 8)
_SEP_OFFSETS = tuple((dr, dc) for dr in range(-2, 3) for dc in range(-2, 3)
                     if 0 < (dr * dr + dc * dc) <= 8)


class CollarError(RuntimeError):
    pass


@dataclass
class CollarResult:
    dots: np.ndarray                       # bool mask, same shape as the parent
    moved: np.ndarray                      # bool mask of dots that moved (old positions)
    targets: np.ndarray                    # (n, 2) int array of new positions
    stats: dict = field(default_factory=dict)


# ------------------------------------------------------------------ priors
def collar_weight(distance_px: np.ndarray, *, outer: float = COLLAR_OUTER_PX,
                  floor: float = COLLAR_FLOOR_PX + COLLAR_FLOOR_MARGIN_PX) -> np.ndarray:
    """Linear ramp 1.0 at the legal floor down to 0.0 at the band's outer edge.

    Cells at or inside the floor, or at/beyond ``outer``, get exactly 0.0, so the
    ramp can never place mass inside the catalogue collar.
    """
    d = np.asarray(distance_px, dtype=np.float64)
    w = (float(outer) - d) / (float(outer) - float(floor))
    w = np.clip(w, 0.0, 1.0)
    w[d < float(floor)] = 0.0
    return w


def support_fraction(vote: np.ndarray) -> np.ndarray:
    """Cross-field support (0..3 fields emitting a cell) mapped to 0.5..1.0.

    Used only to break ties between cells that are equally close to the mapped
    traces.  The 0.5 floor keeps the geometric prior dominant.
    """
    v = np.asarray(vote, dtype=np.float64)
    return 0.5 + 0.5 * np.clip(v, 0.0, 3.0) / 3.0


def collar_prior(distance_px: np.ndarray, vote: np.ndarray | None = None) -> np.ndarray:
    """The acceptor prior: collar proximity, nudged by structural support."""
    w = collar_weight(distance_px)
    if vote is not None:
        w = w * support_fraction(vote)
    return w


def remote_prior(distance_px: np.ndarray, vote: np.ndarray | None = None, *,
                 min_px: float = REMOTE_MIN_PX) -> np.ndarray:
    """Mirror prior for the control arm: support-weighted cells far from the catalogue."""
    d = np.asarray(distance_px, dtype=np.float64)
    w = np.clip((d - float(min_px)) / 10.0, 0.0, 1.0)      # ramps in over 10 px
    w[d < float(min_px)] = 0.0
    if vote is not None:
        w = w * support_fraction(vote)
    return w


# ------------------------------------------------------------- donor ranking
def block_mean(field_: np.ndarray, footprint: np.ndarray, block_px: int = 10) -> tuple[np.ndarray, int]:
    """Mean prior per ``block_px`` block over footprint pixels (NaN where empty)."""
    if block_px <= 0:
        raise CollarError("block_px must be positive")
    nrow, ncol = field_.shape
    nbr, nbc = -(-nrow // block_px), -(-ncol // block_px)
    num = np.zeros((nbr, nbc))
    den = np.zeros((nbr, nbc))
    fin = np.isfinite(field_) & footprint
    rr, cc = np.nonzero(fin)
    vals = np.asarray(field_, dtype=np.float64)[rr, cc]
    np.add.at(num, (rr // block_px, cc // block_px), vals)
    np.add.at(den, (rr // block_px, cc // block_px), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = np.where(den > 0, num / den, np.nan)
    return out, block_px


def donor_order(dots: np.ndarray, dcat: np.ndarray, prior_field: np.ndarray,
                *, block_px: int = 10, eligible: np.ndarray | None = None) -> np.ndarray:
    """Dot indices, lowest-prior-block first (deterministic tie-breaks).

    Donors are ordered by (mean prior of their 1 km block ascending), then by
    distance-to-catalogue descending (move the most remote dot first), then by flat
    raster index.  ``eligible`` restricts which dots may be donors at all.
    """
    rows, cols = np.nonzero(dots)
    n = len(rows)
    if n == 0:
        return np.zeros(0, dtype=np.int64)
    bp = prior_field
    if bp.shape != dots.shape:
        raise CollarError("prior field must share the parent's shape")
    bp, _ = block_mean(np.where(np.isfinite(bp), bp, 0.0), np.ones(dots.shape, bool), block_px)
    block_val = np.nan_to_num(bp[rows // block_px, cols // block_px], nan=-1.0)
    dist = np.asarray(dcat, float)[rows, cols]
    flat = rows.astype(np.int64) * dots.shape[1] + cols
    order = np.lexsort((flat, -dist, block_val))
    if eligible is not None:
        keep = np.asarray(eligible, bool)[rows, cols]
        order = order[keep[order]]
    return flat[order]        # flat raster indices, same convention as acceptor_order


def acceptor_order(prior_field: np.ndarray, footprint: np.ndarray, dcat: np.ndarray,
                   *, min_px: float, max_px: float | None = None) -> np.ndarray:
    """Flat raster indices of legal acceptor cells, best prior first.

    Legal means: inside the footprint, strictly further than ``min_px`` from the
    catalogue, and (optionally) no further than ``max_px``.
    """
    d = np.asarray(dcat, dtype=np.float64)
    ok = np.asarray(footprint, bool) & (d > float(min_px))
    if max_px is not None:
        ok &= d <= float(max_px)
    ok &= np.asarray(prior_field, np.float64) > 0.0
    idx = np.flatnonzero(ok)
    if idx.size == 0:
        raise CollarError("no legal acceptor cells for this prior")
    score = np.asarray(prior_field, np.float64).ravel()[idx]
    order = np.lexsort((idx, -score))
    return idx[order].astype(np.int64)


# ---------------------------------------------------------------- relocation
def relocate(dots: np.ndarray, donor_idx: np.ndarray, accept_idx: np.ndarray,
             *, min_sep_px: float = PARENT_MIN_NN_PX,
             max_donors: int | None = None) -> CollarResult:
    """Move ``donor_idx`` dots onto ``accept_idx`` cells, best acceptor first.

    The number moved is ``len(donor_idx)`` (or ``max_donors`` if that is smaller).
    A cell is accepted only if it is empty and no kept dot lies closer than
    ``min_sep_px`` (checked on the exact integer stencil, so the check is exact for
    the parent's 2.83 px floor).
    """
    dots = np.asarray(dots, bool)
    shape = dots.shape
    nrow, ncol = shape
    donors = np.asarray(donor_idx, dtype=np.int64)
    if max_donors is not None:
        donors = donors[: int(max_donors)]
    n_move = int(donors.size)
    if n_move == 0:
        raise CollarError("no donors to move")

    donor_rows, donor_cols = np.divmod(donors, ncol)
    occupied = dots.copy()
    occupied[donor_rows, donor_cols] = False          # donors are freed before placement

    targets: list[tuple[int, int]] = []
    ptr = 0
    flat_accept = np.asarray(accept_idx, dtype=np.int64)
    while len(targets) < n_move:
        placed_this = False
        while ptr < flat_accept.size and not placed_this:
            flat = int(flat_accept[ptr]); ptr += 1
            r, c = divmod(flat, ncol)
            if occupied[r, c]:
                continue
            sep_ok = True
            for dr, dc in _SEP_OFFSETS:
                rr, cc = r + dr, c + dc
                if 0 <= rr < nrow and 0 <= cc < ncol and occupied[rr, cc]:
                    sep_ok = False
                    break
            if not sep_ok:
                continue
            occupied[r, c] = True
            targets.append((r, c))
            placed_this = True
        if not placed_this and ptr >= flat_accept.size:
            raise CollarError(
                f"only {len(targets)} of {n_move} acceptors could be placed at "
                f">= {min_sep_px:.3f} px separation")

    tgt = np.asarray(targets, dtype=np.int64)
    moved = np.zeros(shape, bool)
    moved[donor_rows[:tgt.shape[0]], donor_cols[:tgt.shape[0]]] = True
    out_dots = occupied
    disp = np.hypot(donor_rows[:tgt.shape[0]] - tgt[:, 0],
                    donor_cols[:tgt.shape[0]] - tgt[:, 1])
    stats = {
        "n_dots": int(out_dots.sum()),
        "n_moved": int(tgt.shape[0]),
        "pct_moved_of_parent": round(100.0 * tgt.shape[0] / max(1, int(dots.sum())), 4),
        "count_preserved": bool(int(out_dots.sum()) == int(dots.sum())),
        "displacement_px": {
            "n": int(disp.size),
            "mean_px": round(float(disp.mean()), 4),
            "median_px": round(float(np.median(disp)), 4),
            "p95_px": round(float(np.percentile(disp, 95)), 4),
            "max_px": round(float(disp.max()), 4),
        },
        "min_sep_px_enforced": float(min_sep_px),
    }
    return CollarResult(dots=out_dots, moved=moved, targets=tgt, stats=stats)


__all__ = ["COLLAR_FLOOR_PX", "COLLAR_FLOOR_MARGIN_PX", "COLLAR_OUTER_PX",
           "PARENT_MIN_NN_PX", "REMOTE_MIN_PX", "CollarError", "CollarResult",
           "collar_weight", "support_fraction", "collar_prior", "remote_prior",
           "block_mean", "donor_order", "acceptor_order", "relocate"]
