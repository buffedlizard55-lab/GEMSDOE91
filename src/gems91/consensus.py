"""MASS ranking rebuilt from the lineage's own fields (the parent's ranking was never stored).

Why this module exists
----------------------
Brief section 5 defines MASS as "drop the lowest-ranked 10% / add the next-ranked
10%, by the parent's own ranking (rebuild the ranking from the recorded recipe if
it is not stored)".  The recipe cannot be rebuilt: every ancestor raster that
survives in the pinned set is **binary** (values in {0,1}: `calib_h195_01922`,
`calib_h194_01894`, `calib_h161_01855`, `calib_d15_02477`, the d2.8 raster and
solo-d28), and `training_features.tif` -- the only input that would carry a
continuous score -- has no public mirror and is absent.  So no stored artifact
ranks R0's dots.  See IRREGULARITIES.md IR-91-19.

What is available, and is pinned and hash-verified, is the *support structure*
that generated the parent: R0's dot set is contained in three independently built
H-hypothesis fields of the same lineage.

    R0 (37,654) subset of solo-d28 (40,199) subset of d2.8 (44,090) subset of H19.5 (121,131)

For every R0 dot, count how many of the three hypothesis fields (H19.5, H19.4,
H16.1) emit it:

    consensus 3 : 26,913 dots   (71.5%)   all three fields agree
    consensus 2 :  6,200 dots   (16.5%)
    consensus 1 :  4,541 dots   (12.1%)   H19.5 only -- single-interpretation support
    consensus 0 :      0 dots

That is an ordinal, fully pinned, per-dot ranking with no external data and no
label use.  It is NOT the parent's original continuous ranking and must never be
described as such; it is a *cross-field support* ordering.  Both directions of the
MASS edit are defined on it, and every tie is broken deterministically, so the
selection rule is reproducible from pinned bytes alone.

Metric relevance (why a support ordering is the right thing to rank by)
----------------------------------------------------------------------
For the triangular kernel (R = 3 px) at the claimed precision d = 0.2778 the
per-dot break-even is exact, not a rule of thumb: emitting a dot whose credit to
the nearest truth pixel is c and whose self-match is k changes DTI by

    sign(dDTI) = sign( c*(D - a*T) - a*T*(1 - k) ),   a = 0.2

so with dTI = T/D and k ~= c an isolated truth pixel pays iff c > a*d/(1 - a*d),
i.e. iff the dot is within 2.83 px of a truth pixel.  Everything is one narrow
band: the axis can only win by *moving mass across the 2.83 px boundary*, never
by shifting within it.  A support ordering is therefore a hypothesis about
precision, and the two arms of this session measure whether it is right.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi

#: The three lineage fields, in the order they enter the consensus count.
#: Manifest ids: anc_h19_5, anc_h19_4, anc_h16_1 (all pinned + hash-verified).
FIELD_IDS = ("anc_h19_5", "anc_h19_4", "anc_h16_1")

#: Brief 4.4. New mass of any non-PRUNE axis must sit this far from the catalogue.
MIN_CATALOGUE_PX = 3.0


@dataclass(frozen=True)
class ConsensusRank:
    """Integer support count (0-3) plus the tie-break fields, all deterministic."""

    vote: np.ndarray            # int8, 0..3 -- number of fields emitting the pixel
    dot_distance: np.ndarray    # float64, px to the nearest existing parent dot
    flat_index: np.ndarray      # int64, row-major index (last-resort tie-break)

    def histogram(self, dots: np.ndarray) -> list[int]:
        return [int(n) for n in np.bincount(self.vote[dots], minlength=len(FIELD_IDS) + 1)]


def vote_count(fields: list[np.ndarray] | tuple[np.ndarray, ...]) -> np.ndarray:
    """Number of fields emitting each pixel (0..len(fields)).

    ``fields`` are boolean-or-0/1 arrays on the competition grid.  No threshold is
    invented here: the inputs are already binary, and a non-binary input is
    refused rather than silently binarised.
    """
    if not fields:
        raise ValueError("at least one field is required")
    shape = fields[0].shape
    out = np.zeros(shape, dtype=np.int8)
    for f in fields:
        f = np.asarray(f)
        if f.shape != shape:
            raise ValueError("all fields must share the grid")
        vals = np.unique(f[np.isfinite(f)] if f.dtype.kind == "f" else f)
        if not np.all(np.isin(vals, (0, 1))):
            raise ValueError("consensus fields must be binary (0/1); refusing to threshold")
        out += (np.nan_to_num(f, nan=0.0) > 0).astype(np.int8)
    return out


def build_rank(fields: list[np.ndarray], dots: np.ndarray) -> ConsensusRank:
    """Cross-field support for every pixel, plus the deterministic tie-breaks."""
    vote = vote_count(fields)
    dot_distance = ndi.distance_transform_edt(~dots) if dots.any() else np.full(dots.shape, np.inf)
    flat = np.arange(dots.size, dtype=np.int64).reshape(dots.shape)
    return ConsensusRank(vote=vote, dot_distance=dot_distance, flat_index=flat)


def select_drop(dots: np.ndarray, rank: ConsensusRank, max_vote: int) -> np.ndarray:
    """Dots whose support is at most ``max_vote`` fields.

    Whole support strata are removed, never a fraction of one: a partial stratum
    would need an arbitrary tie-break *inside* the ordering under test, which would
    contaminate the comparison with a second, unstated rule.
    """
    if max_vote < 0:
        raise ValueError("max_vote must be >= 0")
    return dots & (rank.vote <= max_vote)


def select_add(dots: np.ndarray, rank: ConsensusRank, footprint: np.ndarray,
               cat_distance: np.ndarray, n: int,
               min_cat_px: float = MIN_CATALOGUE_PX) -> np.ndarray:
    """The ``n`` best addable pixels, ranked by support then by distance from a dot.

    Ranking key, applied in this order (np.lexsort: last key is primary):

    1. ``vote`` descending  -- highest cross-field agreement first;
    2. ``dot_distance`` descending -- of two equally supported cells, prefer the one
       furthest from an existing parent dot.  The lineage's d2.8 thinning removed
       77,041 field pixels on a *spacing* rule, not on a score difference, so the
       cells it suppressed near survivors are the ones most worth re-testing;
    3. row-major index ascending -- pure determinism, never a model.

    Eligibility is the brief's, with nothing relaxed: inside the footprint, not
    already a dot, off the catalogue, and **strictly more than** ``min_cat_px`` from
    it. The comparison is strict (``>``, not ``>=``) so that new mass never sits on
    the 3.0 px boundary, where ``gems91.gates`` counts a dot as inside the collar.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    eligible = (
        np.asarray(footprint, dtype=bool)
        & ~dots
        & (rank.vote >= 1)                       # no field supports it -> not a fault cell
        & (np.nan_to_num(cat_distance, nan=0.0) > min_cat_px)
    )
    ys, xs = np.nonzero(eligible)
    if n > len(ys):
        raise ValueError(f"need {n} addable pixels but only {len(ys)} are eligible")
    order = np.lexsort((rank.flat_index[ys, xs], -rank.dot_distance[ys, xs], -rank.vote[ys, xs]))
    chosen = order[:n]
    out = np.zeros_like(dots)
    out[ys[chosen], xs[chosen]] = True
    return out


def frame(dots: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Release array: NaN outside the footprint, 0.0 inside, 1.0 on dots."""
    out = np.full(dots.shape, np.nan, dtype=np.float32)
    out[np.asarray(footprint, dtype=bool)] = 0.0
    out[dots] = 1.0
    return out


def diff_stats(parent_dots: np.ndarray, child_dots: np.ndarray) -> dict:
    added = int((child_dots & ~parent_dots).sum())
    removed = int((parent_dots & ~child_dots).sum())
    base = int(parent_dots.sum()) or 1
    return {
        "n_parent_dots": int(parent_dots.sum()),
        "n_dots": int(child_dots.sum()),
        "added": added,
        "removed": removed,
        "changed": added + removed,
        "pct_changed": round(100.0 * (added + removed) / base, 4),
    }
