"""SPACING/redcov operator: matched-count move from kernel-redundant dots to uncovered support.

Brief section 5 defines the session axes; SPACING is "lattice vs Poisson-disk vs
along-strike at matched count".  The three arms built here (``redcov10``,
``redcov20``, ``redcov10v2``) are the Poisson-disk direction of that axis, applied
as a relocation rather than the local ring-2 nudges of ``SPACING/spread40``:

    donors      the off-collar R0 dots with the highest *kernel-overlap redundancy*
                red_i = sum_{j: 0 < d_ij < 6 px} (1 - d_ij / 6)
                i.e. dots whose 300 m DTI kernel footprint is most duplicated by
                neighbouring dots.  A truth pixel's credit is a max over dots, so a
                dot whose disk is covered by other dots earns ~0 marginal T for
                *any* truth geometry; the donor rule reads no label and no feature
                band, only the parent's own dot geometry.
    recipients  lineage-supported cells (cross-field vote >= ``min_vote`` over the
                pinned anc_h19_5 / anc_h19_4 / anc_h16_1 fields, the same support
                vote as ``gems91.consensus``) ranked by distance to the nearest
                *surviving* dot, descending -- the cells the d2.8 spacing thinning
                suppressed that remain furthest from any dot's kernel.  Greedy
                placement enforces >= 2.8 px from every surviving or already-placed
                dot (the lineage's own thinning scale).

Invariants (asserted by the builder, unit-tested here)
-------------------------------------------------------
1. Count conserved exactly (37,654); unit mass {0, 1} preserved.
2. Catalogue collar quarantined (IR-91-27): donors require d_cat > 3 px and
   recipients require d_cat > 3 px, so R0's 2,171 dots at 2 < d_cat <= 3 px are
   inherited unchanged and the arm cannot silently become a PRUNE edit.
3. Donor cells are excluded from the recipient pool: a "moved" dot never refills
   the hole it just left (the prototype that allowed refill re-placed 194-979
   donor cells; the shipped rule forbids it and the builder re-measures).
4. Deterministic: pairs are sorted before accumulation and every ordering ends
   in a (row, col) lexsort tie-break.  No RNG anywhere.

Why this axis, measured before building (session 8 screens, all PROXY)
----------------------------------------------------------------------
Every MASS ranking the pinned inputs support puts its bottom decile within
~2 points of the 11.8 % break-even precision (IR-91-22), so mass edits are
predicted |Delta| < 0.002 -- under the brief's 0.01 evidence bar.  On the
independent off-catalogue SGMC control (USGS DS-1052, report-only), this
relocation is the only screened family with a materially positive *exact*
fixed-count DTI delta (relT +7.5 % at 10 % moved).  The full screen log,
including the families that failed, is in evidence/redcov_axis_20261024.json
and IR-91-33/34.  SGMC was used to *screen* mechanism-backed families, never
as a per-dot optimiser and never as a gate.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

#: Kernel-overlap radius for the redundancy score: two dots closer than twice the
#: 3 px DTI kernel radius can credit the same truth pixel.
REDUNDANCY_RADIUS_PX = 6.0
#: Minimum separation enforced on recipients -- the lineage d2.8 thinning scale.
MIN_SEPARATION_PX = 2.8
#: Brief constraint 4: no new or moved mass at <= 3 px from the catalogue.
COLLAR_PX = 3.0


def redundancy_scores(dots: np.ndarray, radius: float = REDUNDANCY_RADIUS_PX) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-dot kernel-overlap redundancy.  Returns (rows, cols, score) in row-major order.

    score_i = sum over other dots j with 0 < d_ij < radius of (1 - d_ij / radius).
    Pairs are sorted before accumulation so the float sum is order-stable.
    """
    ys, xs = np.nonzero(np.asarray(dots, dtype=bool))
    pts = np.c_[ys, xs].astype(np.float64)
    if len(pts) == 0:
        return ys, xs, np.zeros(0, dtype=np.float64)
    pairs = cKDTree(pts).query_pairs(radius, output_type="ndarray")
    score = np.zeros(len(pts), dtype=np.float64)
    if len(pairs):
        pairs = pairs[np.lexsort((pairs[:, 1], pairs[:, 0]))]
        d = np.hypot(pts[pairs[:, 0], 0] - pts[pairs[:, 1], 0],
                     pts[pairs[:, 0], 1] - pts[pairs[:, 1], 1])
        w = np.clip(1.0 - d / float(radius), 0.0, None)
        np.add.at(score, pairs[:, 0], w)
        np.add.at(score, pairs[:, 1], w)
    return ys, xs, score


def apply_redcov(
    parent_dots: np.ndarray,
    vote: np.ndarray,
    dcat: np.ndarray,
    footprint: np.ndarray,
    *,
    frac: float,
    min_vote: int = 1,
    collar_px: float = COLLAR_PX,
    min_sep: float = MIN_SEPARATION_PX,
) -> dict[str, object]:
    """Move ``frac`` of ``parent_dots`` from redundancy maxima to coverage maxima.

    Returns {"child", "donors", "recipients", "stats"} -- all boolean masks on the
    grid, plus the donor/recipient score ranges the mechanism card quotes.
    """
    if not (0.0 < frac <= 0.50):
        raise ValueError(f"frac must lie in (0, 0.50] (brief 1-50% rule); got {frac}")
    if min_vote < 1:
        raise ValueError("min_vote must be >= 1: recipients need lineage support")
    p = np.asarray(parent_dots, dtype=bool)
    n_parent = int(p.sum())
    n_move = int(round(frac * n_parent))
    if n_move < 1:
        raise ValueError("move count rounded to 0 dots")

    # --- donors: highest redundancy among off-collar dots -------------------
    ys, xs, red = redundancy_scores(p)
    order = np.lexsort((xs, ys, -red))            # primary: redundancy desc
    off_collar = dcat[ys, xs] > collar_px
    off_ordered = np.asarray([i for i in order if off_collar[i]], dtype=np.int64)
    donor_idx = off_ordered[:n_move]
    if len(donor_idx) < n_move:
        raise RuntimeError(f"only {len(donor_idx)} off-collar donor dots (< {n_move})")
    donors = np.zeros_like(p)
    donors[ys[donor_idx], xs[donor_idx]] = True
    surviving = p & ~donors

    # --- recipients: supported cells furthest from a surviving dot ----------
    eligible = (
        np.asarray(footprint, dtype=bool)
        & ~surviving
        & ~donors                                  # invariant 3: no refill
        & (np.asarray(vote) >= min_vote)
        & (np.nan_to_num(dcat, nan=0.0) > collar_px)
    )
    ey, ex = np.nonzero(eligible)
    if len(ey) < n_move:
        raise RuntimeError(f"only {len(ey)} eligible recipient cells (< {n_move})")
    d_surv = ndi.distance_transform_edt(~surviving)
    e_order = np.lexsort((ex, ey, -d_surv[ey, ex]))  # primary: coverage distance desc

    h, w = p.shape
    rr = int(np.ceil(min_sep))
    occ = surviving.copy()
    chosen: list[int] = []
    for i in e_order:
        if len(chosen) >= n_move:
            break
        y, x = int(ey[i]), int(ex[i])
        if d_surv[y, x] < min_sep:
            continue
        y0, y1 = max(0, y - rr), min(h, y + rr + 1)
        x0, x1 = max(0, x - rr), min(w, x + rr + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        if (occ[y0:y1, x0:x1] & (np.hypot(yy - y, xx - x) < min_sep)).any():
            continue
        occ[y, x] = True
        chosen.append(i)
    if len(chosen) < n_move:
        raise RuntimeError(f"placed only {len(chosen)}/{n_move} recipients at >={min_sep} px")

    recipients = np.zeros_like(p)
    recipients[ey[chosen], ex[chosen]] = True
    child = surviving | recipients

    stats = {
        "n_parent_dots": n_parent,
        "n_dots": int(child.sum()),
        "n_moved": n_move,
        "pct_relocated": round(100.0 * n_move / n_parent, 4),
        "pct_changed_symdiff": round(200.0 * n_move / n_parent, 4),
        "donor_redundancy_min": round(float(red[donor_idx].min()), 4),
        "donor_redundancy_median": round(float(np.median(red[donor_idx])), 4),
        "kept_redundancy_max_offcollar": round(
            float(red[off_ordered[n_move]]), 4
        ) if len(off_ordered) > n_move else None,
        "recipient_dist_to_survivor_min_px": round(float(d_surv[recipients].min()), 4),
        "recipient_dist_to_survivor_median_px": round(float(np.median(d_surv[recipients])), 4),
        "donor_vote_histogram": [int(v) for v in np.bincount(np.asarray(vote)[donors], minlength=4)],
        "recipient_vote_histogram": [int(v) for v in np.bincount(np.asarray(vote)[recipients], minlength=4)],
        "donor_dcat_median_px": round(float(np.median(dcat[donors])), 3),
        "recipient_dcat_median_px": round(float(np.median(dcat[recipients])), 3),
        "donor_cells_reused_as_recipients": int((donors & recipients).sum()),
        "min_vote": int(min_vote),
        "frac": float(frac),
    }
    assert stats["n_dots"] == n_parent, "count not conserved"
    assert stats["donor_cells_reused_as_recipients"] == 0
    return {"child": child, "donors": donors, "recipients": recipients, "stats": stats}


__all__ = ["REDUNDANCY_RADIUS_PX", "MIN_SEPARATION_PX", "COLLAR_PX",
           "redundancy_scores", "apply_redcov"]
