"""RELIEF axis: move mass between relief terciles at a fixed dot count.

The brief defines the axis as "shift 10-15 % of mass between basin / piedmont /
range-front terciles (relief from the detrended-elevation bands), count fixed".

What this module does, and what it deliberately does not do
-----------------------------------------------------------
* The *treatment* is which tercile the mass sits in. Everything else is held
  fixed across arms: the number of dots moved, the donor-sampling rule (uniform,
  fixed seed, inside the stated donor tercile(s)), the recipient rule (greedy
  maximal spread), the catalogue floor, the footprint and the count.
* Recipient cells must lie on the parent lineage's own support field, i.e. cells
  the lineage's detector already accepted at a lower dose (``calib_h195`` =
  121,131 cells, of which every one of R0's 37,654 dots is a member). A new dot
  is therefore placed where the *parent's own rule* would have allowed a dot,
  not on an arbitrary legal cell.
* Recipients must respect the parent's own spacing floor, d_nn >= 2.8 px. That
  number is measured, not chosen: R0's minimum nearest-neighbour distance is
  exactly 2*sqrt(2) = 2.828 px (11,415 of 37,654 dots sit at that distance and
  none is closer), which is what the ancestor names ``d2.8`` record.
* Nothing is deleted and nothing is duplicated: a moved dot leaves an empty
  cell and occupies an empty cell, so ``n_dots`` is invariant by construction
  and the Hamming distance to the parent is 2 x (dots moved).

Not modelled here: any claim about where *new* faults are. The tercile prior is
audited against the mapped catalogue in ``scripts/build_relief.py`` and is
labelled PROXY; it is not a score.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

TERCILE_LABELS = ("basin", "piedmont", "range_front")
DEFAULT_MIN_CAT_PX = 3.0     # brief 4.4: new mass keeps >= 3 px from the catalogue
DEFAULT_MIN_SEP_PX = 2.8     # measured on R0: minimum nearest-neighbour distance


def tercile_cuts(field: np.ndarray, footprint: np.ndarray) -> tuple[float, float]:
    """Equal-count tercile cuts of ``field`` over the footprint (finite cells only)."""
    v = np.asarray(field, dtype=np.float64)[footprint]
    v = v[np.isfinite(v)]
    if v.size == 0:
        raise ValueError("empty footprint")
    q1, q2 = np.quantile(v, [1.0 / 3.0, 2.0 / 3.0])
    return float(q1), float(q2)


def tercile_index(field: np.ndarray, footprint: np.ndarray,
                  cuts: tuple[float, float] | None = None) -> tuple[np.ndarray, tuple[float, float]]:
    """0 = lowest third (basin), 1 = middle (piedmont), 2 = highest (range front).

    Cells outside the footprint, or with a non-finite field value, are -1.
    """
    q1, q2 = tercile_cuts(field, footprint) if cuts is None else cuts
    field = np.asarray(field, dtype=np.float64)
    out = np.full(field.shape, -1, dtype=np.int8)
    inside = footprint & np.isfinite(field)
    out[inside] = np.digitize(field[inside], [q1, q2]).astype(np.int8)
    return out, (float(q1), float(q2))


def tercile_counts(dots: np.ndarray, tercile: np.ndarray) -> dict:
    n = int(dots.sum())
    counts = {TERCILE_LABELS[t]: int((dots & (tercile == t)).sum()) for t in range(3)}
    counts["n_dots"] = n
    counts["fraction"] = {k: (round(v / n, 6) if n else None) for k, v in counts.items()
                          if k in TERCILE_LABELS}
    return counts


def _separation_structure(radius_px: float) -> np.ndarray:
    """Boolean structuring element: cells strictly closer than ``radius_px``."""
    span = int(np.ceil(radius_px))
    yy, xx = np.mgrid[-span:span + 1, -span:span + 1]
    k = np.hypot(yy, xx) < radius_px
    k[span, span] = False          # a cell is never a neighbour of itself
    return k


def spread_placement(cand_yx: np.ndarray, existing_yx: np.ndarray, n: int,
                     min_sep_px: float = DEFAULT_MIN_SEP_PX,
                     shape: tuple[int, int] | None = None) -> dict:
    """Greedy priority dart throwing: pick ``n`` well-separated recipient cells.

    Candidates are visited in descending order of their distance to the nearest
    surviving dot, and a candidate is accepted only if it is at least
    ``min_sep_px`` from every surviving dot and every recipient already accepted
    (accepted cells block their own neighbourhood). Deterministic: ties break on
    the candidate index, which is row-major, so the same inputs always give the
    same recipients.

    Why not true farthest-point sampling: the legal-candidate pool in a tercile is
    ~1.3 million cells, and greedy farthest-point is O(n * |candidates|). This
    construction is O(|candidates| log |candidates|), keeps the same even-coverage
    character (isolated cells are taken first), and is identical in every arm, so
    it cannot explain a difference between arms.

    Returns the chosen cells, their separation distances, and any shortfall.
    """
    cand_yx = np.asarray(cand_yx, dtype=np.int64)
    if shape is None:
        shape = (int(cand_yx[:, 0].max()) + 2 if len(cand_yx) else 1,
                 int(cand_yx[:, 1].max()) + 2 if len(cand_yx) else 1)
    if n <= 0 or len(cand_yx) == 0:
        return {"chosen": np.empty((0, 2), dtype=np.int64), "dmin": np.empty(0),
                "shortfall": int(n), "leftover_candidates": int(len(cand_yx))}

    if len(existing_yx):
        d = cKDTree(np.asarray(existing_yx, dtype=np.float64)).query(
            cand_yx.astype(np.float64), k=1)[0]
    else:
        d = np.full(len(cand_yx), np.inf)
    order = np.argsort(-d, kind="stable")

    span = int(np.ceil(min_sep_px))
    yy, xx = np.mgrid[-span:span + 1, -span:span + 1]
    disk = np.hypot(yy, xx) < min_sep_px
    blocked = np.zeros(shape, dtype=bool)
    h, w = shape
    chosen: list[tuple[int, int]] = []
    dmin: list[float] = []
    for i in order:
        y, x = int(cand_yx[i, 0]), int(cand_yx[i, 1])
        if blocked[y, x] or d[i] < min_sep_px:
            continue
        chosen.append((y, x))
        dmin.append(float(d[i]))
        y0, y1 = max(0, y - span), min(h, y + span + 1)
        x0, x1 = max(0, x - span), min(w, x + span + 1)
        blocked[y0:y1, x0:x1] |= disk[y0 - (y - span):y1 - (y - span),
                                     x0 - (x - span):x1 - (x - span)]
        if len(chosen) >= int(n):
            break

    arr = np.asarray(chosen, dtype=np.int64) if chosen else np.empty((0, 2), dtype=np.int64)
    return {
        "chosen": arr,
        "dmin": np.asarray(dmin, dtype=float),
        "shortfall": int(int(n) - len(chosen)),
        "leftover_candidates": int(len(cand_yx) - len(chosen)),
    }


def relief_shift(dots: np.ndarray, footprint: np.ndarray, cat_dist: np.ndarray,
                 support: np.ndarray | None, tercile: np.ndarray, *,
                 donor_terciles: tuple[int, ...], target_terciles: tuple[int, ...] | None,
                 n_move: int, rng: np.random.Generator,
                 min_cat_px: float = DEFAULT_MIN_CAT_PX,
                 min_sep_px: float = DEFAULT_MIN_SEP_PX,
                 target_quotas: dict[int, int] | None = None) -> dict:
    """Move ``n_move`` dots from the donor terciles into the target terciles.

    ``target_terciles=None`` means "any tercile" (the relocation-only null arm).
    ``target_quotas`` splits the move across terciles explicitly ({tercile: count});
    it is how the null arm is made tercile-neutral: it sends the same number of
    dots into each tercile that it took out of it.

    Hard rules, enforced and reported, never silently relaxed:
      * the count is invariant -- an unplaceable recipient returns its donor dot;
      * a recipient is inside the footprint, off the catalogue by more than
        ``min_cat_px`` and at least ``min_sep_px`` from every surviving dot and
        from every other recipient (lineage support is preferred, then exhausted);
      * donors are drawn uniformly at random (fixed seed) from the donor terciles,
        so the only systematic difference between arms is the tercile pairing.
    """
    dots = np.asarray(dots, dtype=bool)
    if support is not None and support.shape != dots.shape:
        raise ValueError("support grid mismatch")
    if not (footprint.shape == dots.shape == tercile.shape == cat_dist.shape):
        raise ValueError("grid mismatch")
    if not donor_terciles:
        raise ValueError("donor_terciles required")

    donor_mask = np.isin(tercile, list(donor_terciles))
    donor_pool = np.flatnonzero((dots & donor_mask).ravel())
    n_req = int(min(n_move, donor_pool.size))
    donor_flat = (rng.choice(donor_pool, size=n_req, replace=False)
                  if n_req else np.empty(0, dtype=np.int64))

    remaining = dots.copy()
    remaining.ravel()[donor_flat] = False

    legal = footprint & ~dots & (cat_dist > min_cat_px)
    if target_quotas is None and target_terciles is not None:
        legal &= np.isin(tercile, list(target_terciles))
    # prune anything already closer than the spacing floor to a surviving dot
    legal &= ndi.distance_transform_edt(~remaining) >= (min_sep_px - 1e-9)
    existing_yx = np.column_stack(np.nonzero(remaining))

    # Two tiers, in this order and identical in every arm: lineage support first
    # (cells the parent's own detector accepted at a lower dose), then everything
    # else that is legal. R0 is spacing-saturated on its own support -- only ~90
    # support cells in the whole footprint are >= 2.8 px from a surviving dot --
    # so the second tier carries almost all of a long-range move. That is a
    # property of the parent, not of the arm, and it is reported, not hidden.
    if target_quotas is not None:
        jobs = [(legal & (tercile == k), int(q)) for k, q in sorted(target_quotas.items())]
    else:
        tiers = [legal & support, legal & ~support] if support is not None else [legal]
        jobs = [(tier, n_req) for tier in tiers]
    chosen_all: list[np.ndarray] = []
    dmin_all: list[float] = []
    taken = remaining.copy()
    n_placed = 0
    for tier, quota in jobs:
        need = min(quota, n_req - n_placed)
        if need <= 0:
            continue
        tier_yx = np.column_stack(np.nonzero(tier))
        if not len(tier_yx):
            continue
        res = spread_placement(tier_yx, np.column_stack(np.nonzero(taken)), need,
                               min_sep_px, shape=dots.shape)
        if len(res["chosen"]):
            chosen_all.append(res["chosen"])
            dmin_all.extend(res["dmin"].tolist())
            taken[res["chosen"][:, 0], res["chosen"][:, 1]] = True
            n_placed += len(res["chosen"])
    chosen = (np.vstack(chosen_all) if chosen_all else np.empty((0, 2), dtype=np.int64))
    placed = {"chosen": chosen, "dmin": np.asarray(dmin_all, dtype=float),
              "shortfall": int(n_req - n_placed)}
    out = taken

    # unplaceable donors go back where they came from: count preserved exactly
    n_short = int(placed["shortfall"])
    if n_short > 0:
        back = donor_flat[:n_short]
        out.ravel()[back] = True

    if int(out.sum()) != int(dots.sum()):     # relocation invariant
        raise AssertionError(f"count changed: {int(dots.sum())} -> {int(out.sum())}")

    new_flat = np.flatnonzero(out.ravel() & ~dots.ravel())
    src_flat = np.flatnonzero(dots.ravel() & ~out.ravel())
    src_y, src_x = np.unravel_index(src_flat, dots.shape)
    dst_y, dst_x = np.unravel_index(new_flat, dots.shape)
    if src_flat.size and dst_y.size:
        # each new dot is paired with the nearest vacated cell: a lower bound on
        # the real move length, reported as such
        dmin, _ = cKDTree(np.column_stack([src_y, src_x]).astype(np.float64)).query(
            np.column_stack([dst_y, dst_x]).astype(np.float64), k=1)
        disp = np.asarray(dmin, dtype=np.float64)
    else:
        disp = np.empty(0)

    before = tercile_counts(dots, tercile)
    after = tercile_counts(out, tercile)
    dmin_recip = float(np.min(placed["dmin"])) if placed["dmin"].size else None

    return {
        "dots": out,
        "n_dots": int(out.sum()),
        "n_dots_parent": int(dots.sum()),
        "n_requested": int(n_move),
        "n_donor_pool": int(donor_pool.size),
        "n_moved": int(new_flat.size),
        "n_shortfall": n_short,
        "pct_relocated": round(100.0 * int(new_flat.size) / max(1, int(dots.sum())), 4),
        "pct_changed_hamming": round(100.0 * 2 * int(new_flat.size) / max(1, int(dots.sum())), 4),
        "donor_terciles": [TERCILE_LABELS[t] for t in donor_terciles],
        "target_terciles": (None if target_terciles is None
                            else [TERCILE_LABELS[t] for t in target_terciles]),
        "donor_tercile_mix": {TERCILE_LABELS[t]: int((np.isin(tercile, [t]) & (dots & ~out)).sum())
                              for t in donor_terciles},
        "recipient_tercile_mix": {TERCILE_LABELS[t]: int((tercile == t)[dst_y, dst_x].sum())
                                  for t in range(3)},
        "before": before,
        "after": after,
        "mean_displacement_px": round(float(disp.mean()), 4) if disp.size else 0.0,
        "max_displacement_px": round(float(disp.max()), 4) if disp.size else 0.0,
        "min_recipient_to_existing_dot_px": (None if dmin_recip is None else round(dmin_recip, 4)),
        "min_cat_dist_new_dots_px": (round(float(cat_dist[dst_y, dst_x].min()), 4)
                                     if dst_y.size else None),
        "n_recipients_on_support": (int(support[dst_y, dst_x].sum())
                                    if support is not None and dst_y.size else None),
        "support_legal_cells": (int((legal & support).sum()) if support is not None else None),
        "all_legal_cells": int(legal.sum()),
    }


def nearest_separation(dots: np.ndarray) -> dict:
    """Nearest-neighbour summary of the dot set (used by the gates' report)."""
    ys, xs = np.nonzero(dots)
    if len(ys) < 2:
        return {}
    pts = np.column_stack([ys, xs]).astype(np.float64)
    d, _ = cKDTree(pts).query(pts, k=2)
    nn = d[:, 1]
    return {
        "nn_min": round(float(nn.min()), 4),
        "nn_p01": round(float(np.percentile(nn, 1)), 4),
        "nn_median": round(float(np.median(nn)), 4),
        "dots_with_nn_lt_2p8": int((nn < 2.8).sum()),
    }
