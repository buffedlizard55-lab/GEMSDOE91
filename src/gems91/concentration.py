"""CONCENTRATION, second generation: block reallocation on a *structural* prior.

Why a second generation exists
------------------------------
Every CONCENTRATION row in the fleet ledger before this module moves dots the same
way: **cold block -> hot block**, i.e. it sharpens whatever ranking it is given
(thermal features, geophysical bands, or the parent's own density).  All of them
raise the 1 km block-density CV away from the `0.51-0.59` band the brief reports
for the best historical files, and the USGS/DOE GDR arms move the label-blind
catalogue PROXY the wrong way (-0.0008) while a *uniform random* block ranking
already reproduces ~70 % of their predicted gain.  Two questions were therefore
never asked:

  Q1 dose   does the structural prior do anything above the 15 % already built, or
            is the whole effect just "dots were relocated"?
  Q2 residual  the parent's field is dense in some 1 km blocks for reasons that
            have nothing to do with structure (thinning, the H19-5 mask, collar
            removal).  If those blocks are over-served, the *residual* of
            structural support over what the parent already holds is a better
            allocator than structural support itself.

This module supplies the three pieces those questions need and nothing else:

  * `percentile_rank` / `structural_prior` - a deterministic, label-blind,
    licence-clean km-scale structural field from the pinned GeoDAWN bands
    (Band 3 `tmi_hg`, Band 5 `iso_grav_anom_slope`, Band 18 `iso_grav_anom_hg`;
    the same three bands the ledger's `15pct-1km-grad` row names).  Percentile
    ranks are used so that three bands with different units and heavy tails
    average without one of them dominating.
  * `residual_prior` - structural percentile minus occupancy percentile, block by
    block, over *occupied* blocks only (empty blocks get NaN, so the edit can
    never invent mass in a place the parent's own lineage never touched).
  * `relocate` - the block reallocation itself: count fixed, unit mass, donors
    restricted by an explicit mask (the caller quarantines the 2,171 collar dots
    of IR-91-03), acceptors floored at `MIN_GAP_PX` from the mapped catalogue and
    `MIN_SEP_PX` from every surviving dot.

Nothing here reads truth, the ledger, or the network.  Every function is pure and
deterministic given its inputs and `seed`.
"""
from __future__ import annotations

import math

import numpy as np

# Frozen knobs.  Changing one of these changes every arm's bytes, so they live
# here rather than in the driver script.
BLOCK_PX = 10             # 1 km blocks: the size the brief's CV band is quoted at
LOW_Q = 0.30              # donors come from the bottom 30 % of blocks
HIGH_Q = 0.30             # acceptors come from the top 30 % of blocks
MIN_GAP_PX = 3.0          # brief section 4.4: >= 3 px from every mapped-fault cell
MIN_SEP_PX = 2.0          # R0 has no dot pair closer than 2.0 px; keep that rule
JITTER_PX = 4             # +-4 px texture around an acceptor anchor
ANCHOR_FRAC = 0.8         # 80 % anchored on a surviving high-block dot, 20 % uniform
CV_BAND = (0.51, 0.59)    # brief section 5: "the best files reportedly sit" here

# integer offsets strictly closer than 2.0 px (4-neighbours, diagonals, and the
# distance-2 cells): the same set the repo's CONCENTRATION builder already uses.
SEP_OFFSETS = [(dr, dc) for dr in range(-2, 3) for dc in range(-2, 3)
               if 0 < (dr * dr + dc * dc) <= 4.0]


# --------------------------------------------------------------------------- #
# Priors
# --------------------------------------------------------------------------- #
def percentile_rank(field: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Rank `field` within `valid` onto [0, 1]; NaN everywhere else, ties averaged.

    Ties are averaged rather than broken by position: geophysical derivative bands
    are flat over large areas, and a positional tie-break would make the prior a
    map of array order instead of a map of signal.
    """
    field = np.asarray(field, dtype=np.float64)
    valid = np.asarray(valid, dtype=bool) & np.isfinite(field)
    n = int(valid.sum())
    if n < 2:
        raise ValueError("percentile_rank needs at least two valid cells")
    out = np.full(field.shape, np.nan, dtype=np.float32)
    values = field[valid]
    uniq, inv, counts = np.unique(values, return_inverse=True, return_counts=True)
    upper = np.cumsum(counts) - 1                 # 0-based last rank in each tie run
    lower = upper - counts + 1                    # 0-based first rank in each tie run
    mean_rank = 0.5 * (upper + lower)
    out[valid] = (mean_rank[inv] / (n - 1)).astype(np.float32)
    return out


def structural_prior(bands: list[np.ndarray] | tuple[np.ndarray, ...],
                     footprint: np.ndarray) -> np.ndarray:
    """Mean percentile rank of the given bands inside the footprint; NaN outside.

    All bands must be nodata-masked to non-finite values by the caller.
    """
    footprint = np.asarray(footprint, dtype=bool)
    if not bands:
        raise ValueError("structural_prior needs at least one band")
    ranks = [percentile_rank(b, footprint) for b in bands]
    stack = np.stack(ranks, axis=0)
    out = np.full(footprint.shape, np.nan, dtype=np.float32)
    with np.errstate(invalid="ignore"):
        out[footprint] = np.nanmean(stack[:, footprint], axis=0).astype(np.float32)
    return out


def block_counts(dots: np.ndarray, shape: tuple[int, int], block_px: int = BLOCK_PX) -> np.ndarray:
    """Dots per block on the block grid (row-major blocks)."""
    nbr, nbc = -(-shape[0] // block_px), -(-shape[1] // block_px)
    counts = np.zeros((nbr, nbc), dtype=np.int32)
    if len(dots):
        np.add.at(counts, (dots[:, 0] // block_px, dots[:, 1] // block_px), 1)
    return counts


def residual_prior(structural: np.ndarray, dots: np.ndarray, footprint: np.ndarray,
                   block_px: int = BLOCK_PX) -> tuple[np.ndarray, dict]:
    """Structural percentile minus occupancy percentile, per *occupied* block.

    Returns a pixel-level field (constant inside each occupied block, NaN in every
    empty block and outside the footprint) plus the diagnostics behind it.  A high
    value means "structure says fault here, but the parent barely samples it"; a
    low value means "the parent is dense here, and structure does not ask for it".
    """
    footprint = np.asarray(footprint, dtype=bool)
    shape = structural.shape
    nbr, nbc = -(-shape[0] // block_px), -(-shape[1] // block_px)
    counts = block_counts(np.asarray(dots, dtype=np.int64), shape, block_px)

    # structural block mean over footprint cells (NaN where the block has none)
    num = np.zeros((nbr, nbc), dtype=np.float64)
    den = np.zeros((nbr, nbc), dtype=np.float64)
    fin = np.isfinite(structural) & footprint
    rr, cc = np.nonzero(fin)
    np.add.at(num, (rr // block_px, cc // block_px), structural[rr, cc])
    np.add.at(den, (rr // block_px, cc // block_px), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        smean = np.where(den > 0, num / den, np.nan)

    occupied = counts > 0
    usable = occupied & np.isfinite(smean)
    if int(usable.sum()) < 10:
        raise ValueError("too few occupied blocks with structural support")

    rank_s = percentile_rank(smean, usable)
    rank_o = percentile_rank(counts.astype(np.float64), usable)

    resid = np.full((nbr, nbc), np.nan, dtype=np.float32)
    resid[usable] = (rank_s[usable] - rank_o[usable]).astype(np.float32)

    out = np.full(shape, np.nan, dtype=np.float32)
    tiled = np.repeat(np.repeat(resid, block_px, axis=0), block_px, axis=1)
    tiled = tiled[: shape[0], : shape[1]]
    out[footprint] = tiled[footprint]

    diag = {
        "definition": "residual = rank_pct(structural block mean) - rank_pct(dots per block); "
                      "occupied blocks only, NaN elsewhere",
        "n_blocks_total": int((nbr * nbc)),
        "n_blocks_occupied": int(occupied.sum()),
        "n_blocks_usable": int(usable.sum()),
        "occupancy_mean_dots_per_occupied_block": round(float(counts[occupied].mean()), 4),
        "occupancy_p95_dots_per_occupied_block": float(np.percentile(counts[occupied], 95)),
        "residual_min": round(float(np.nanmin(resid)), 4),
        "residual_max": round(float(np.nanmax(resid)), 4),
        "corr_struct_occupancy": round(float(np.corrcoef(
            rank_s[usable], rank_o[usable])[0, 1]), 4),
    }
    return out, diag


def surrogate_truth(structural: np.ndarray, footprint: np.ndarray, n_cells: int) -> np.ndarray:
    """The `n_cells` best-supported structural cells, as an upper-bound truth set.

    Used only to state a MODEL bound ("what if truth followed this prior?"), never
    as a gate, a score, or a ranking.
    """
    footprint = np.asarray(footprint, dtype=bool)
    vals = structural[footprint & np.isfinite(structural)]
    n_cells = int(min(max(n_cells, 1), vals.size))
    thr = float(np.partition(vals, vals.size - n_cells)[vals.size - n_cells])
    return (np.nan_to_num(structural, nan=-np.inf) >= thr) & footprint


# --------------------------------------------------------------------------- #
# The edit
# --------------------------------------------------------------------------- #
def _valid_target(r: int, c: int, *, footprint, dcat, occupied: set, shape,
                  min_gap_px: float, min_sep_px: float) -> bool:
    nrow, ncol = shape
    if not (0 <= r < nrow and 0 <= c < ncol):
        return False
    if not footprint[r, c]:
        return False
    if dcat[r, c] <= min_gap_px:
        return False
    if (r, c) in occupied:
        return False
    if min_sep_px > 0.0:
        for dr, dc in SEP_OFFSETS:
            if (r + dr, c + dc) in occupied:
                return False
    return True


def relocate(parent_dots: np.ndarray, prior_field: np.ndarray, footprint: np.ndarray,
             dcat: np.ndarray, *, frac: float, block_px: int = BLOCK_PX,
             donor_mask: np.ndarray | None = None, low_q: float = LOW_Q,
             high_q: float = HIGH_Q, min_gap_px: float = MIN_GAP_PX,
             min_sep_px: float = MIN_SEP_PX, jitter_px: int = JITTER_PX,
             anchor_frac: float = ANCHOR_FRAC, seed: int = 0
             ) -> tuple[np.ndarray, dict]:
    """Move `frac` of the dots from low-prior blocks to high-prior blocks.

    Count is preserved: a dot that cannot be re-placed stays where it was.  Donors
    are ranked by their block's prior (lowest first, ties broken by position);
    acceptors are 80 % anchored on a surviving dot in a high-prior block and 20 %
    uniform inside one, then jittered, then screened by `_valid_target`.

    `donor_mask` is the caller's exclusion list (False = never move this dot).  The
    driver uses it to quarantine R0's 2,171 collar dots, which sit 2.0-3.0 px from
    the mapped catalogue (IR-91-03): moving those would make the arm a PRUNE edit
    wearing a CONCENTRATION label.
    """
    if not (0.10 <= frac <= 0.20):
        raise ValueError(f"frac must be within [0.10, 0.20] per brief section 5; got {frac}")
    parent_dots = np.asarray(parent_dots, dtype=bool)
    shape = parent_dots.shape
    dots = np.argwhere(parent_dots)
    if dots.size == 0:
        raise ValueError("parent has no dots")

    from tools.run_concentration import block_cv, block_prior  # local import: shared code

    bp = block_prior(prior_field, footprint, block_px)
    finite = np.isfinite(bp)
    if int(finite.sum()) < 4:
        raise ValueError("fewer than four blocks carry a km-scale prior inside the footprint")
    flat = bp[finite]
    lo_thr = float(np.quantile(flat, low_q))
    hi_thr = float(np.quantile(flat, 1.0 - high_q))
    low_blocks = finite & (bp <= lo_thr)
    high_blocks = finite & (bp >= hi_thr)

    b_of = (dots[:, 0] // block_px, dots[:, 1] // block_px)
    dot_prior = bp[b_of]
    in_low = low_blocks[b_of] & np.isfinite(dot_prior)
    in_high = high_blocks[b_of]

    if donor_mask is None:
        eligible = np.ones(len(dots), dtype=bool)
    else:
        eligible = np.asarray(donor_mask, dtype=bool)
        if eligible.shape != (len(dots),):
            raise ValueError("donor_mask must be one bool per parent dot")

    n_move = int(round(frac * len(dots)))
    primary = np.flatnonzero(eligible & in_low)
    order = np.lexsort((dots[primary, 1], dots[primary, 0], dot_prior[primary]))
    movers = primary[order][:n_move]
    if movers.size < n_move:
        rest = np.setdiff1d(np.flatnonzero(eligible & ~in_high), primary, assume_unique=True)
        rest_order = np.lexsort((dots[rest, 1], dots[rest, 0],
                                 np.nan_to_num(dot_prior[rest], nan=-1e9)))
        movers = np.concatenate([movers, rest[rest_order][: n_move - movers.size]])

    is_mover = np.zeros(len(dots), dtype=bool)
    is_mover[movers] = True
    occ = {tuple(d) for d in dots[~is_mover].tolist()}

    anchor_idx = np.flatnonzero(in_high & ~is_mover)
    hi_rows = np.argwhere(high_blocks)
    hi_w = bp[high_blocks]
    hi_w = hi_w / hi_w.sum()

    rng = np.random.default_rng(seed)
    pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
    unplaced = 0
    for d in dots[movers].tolist():
        placed = False
        for _ in range(200):
            if anchor_idx.size and rng.random() < anchor_frac:
                a = dots[anchor_idx[rng.integers(len(anchor_idx))]]
                r0, c0 = int(a[0]), int(a[1])
            else:
                br, bc = hi_rows[rng.choice(len(hi_rows), p=hi_w)]
                r0 = int(br * block_px + rng.integers(block_px))
                c0 = int(bc * block_px + rng.integers(block_px))
            r = r0 + int(rng.integers(-jitter_px, jitter_px + 1))
            c = c0 + int(rng.integers(-jitter_px, jitter_px + 1))
            if _valid_target(r, c, footprint=footprint, dcat=dcat, occupied=occ,
                             shape=shape, min_gap_px=min_gap_px, min_sep_px=min_sep_px):
                occ.add((r, c))
                pairs.append((tuple(d), (r, c)))
                placed = True
                break
        if not placed:
            occ.add(tuple(d))          # count is preserved: the dot stays put
            unplaced += 1

    new_dots = np.zeros(shape, dtype=bool)
    if occ:
        arr = np.array(sorted(occ), dtype=np.int64)
        new_dots[arr[:, 0], arr[:, 1]] = True

    before = block_cv(dots, footprint, block_px)
    after = block_cv(np.argwhere(new_dots), footprint, block_px)
    if pairs:
        pd = np.array([math.hypot(t[0] - d0[0], t[1] - d0[1]) for d0, t in pairs])
        disp = {"n": int(len(pd)), "mean_px": round(float(pd.mean()), 4),
                "p50_px": round(float(np.percentile(pd, 50)), 4),
                "p95_px": round(float(np.percentile(pd, 95)), 4),
                "max_px": round(float(pd.max()), 4)}
    else:  # pragma: no cover - only if nothing could be placed
        disp = {"n": 0, "mean_px": None, "p50_px": None, "p95_px": None, "max_px": None}

    stats = {
        "frac_requested": float(frac),
        "frac_achieved": round(len(pairs) / max(1, len(dots)), 6),
        "n_dots_parent": int(len(dots)),
        "n_dots_candidate": int(new_dots.sum()),
        "count_preserved": bool(new_dots.sum() == len(dots)),
        "n_moved": int(len(pairs)),
        "n_unplaced": int(unplaced),
        "pct_dots_moved": round(100.0 * len(pairs) / max(1, len(dots)), 4),
        "block_px": int(block_px),
        "n_low_blocks": int(low_blocks.sum()),
        "n_high_blocks": int(high_blocks.sum()),
        "donor_block_prior_mean": round(float(np.nanmean(dot_prior[movers])), 6) if movers.size else None,
        "acceptor_block_prior_mean": round(float(np.nanmean(
            bp[new_dots.nonzero()[0] // block_px, new_dots.nonzero()[1] // block_px])), 6),
        "moved_displacement_px": disp,
        "cv_footprint_blocks_before": round(float(before["cv"]), 6),
        "cv_footprint_blocks_after": round(float(after["cv"]), 6),
        "cv_definition_footprint_blocks":
            "CV of dots per footprint cell across every block that intersects the footprint "
            "(run_concentration.block_cv); the parent sits at 1.885 at 1 km, so the 0.51-0.59 "
            "band does NOT refer to this definition",
    }
    return new_dots, stats


def cv_band_position(cv: float) -> str:
    """Where a CV sits relative to the brief's reported band."""
    lo, hi = CV_BAND
    if cv < lo:
        return "below the 0.51-0.59 band (more even than the best historical files)"
    if cv > hi:
        return "above the 0.51-0.59 band (clumpier than the best historical files)"
    return "inside the 0.51-0.59 band"


__all__ = ["BLOCK_PX", "LOW_Q", "HIGH_Q", "MIN_GAP_PX", "MIN_SEP_PX", "JITTER_PX",
           "ANCHOR_FRAC", "CV_BAND", "SEP_OFFSETS", "percentile_rank", "structural_prior",
           "block_counts", "residual_prior", "surrogate_truth", "relocate", "cv_band_position"]
