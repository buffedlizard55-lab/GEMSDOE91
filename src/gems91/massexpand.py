"""MASS axis (expansion): add unit-mass dots at cells the parent lineage's *own field* chose
but the parent's spacing-thinning discarded.

Why this is the parent's own ranking
------------------------------------
The brief (section 5) defines MASS as "drop the lowest-ranked 10 % / add the next-ranked
10 %, by the parent's own ranking (rebuild the ranking from the recorded recipe if it is
not stored)".  Previous sessions recorded the ranking as **unrecoverable** because every
pinned ancestor is a binary mask and `training_features` does not carry the H33 score
(registry/data_manifest.json, `mass_ranking_note`; ledger/README.md, `ranking_basis`).
That conclusion is right about a continuous score and wrong about the ranking that
matters here:

* `anc_h19_5` (calib_h195_01922.tif) is the lineage's own 121,131-px field, and **all
  37,654 R0 dots are cells of it**;
* 83,477 of its cells are *not* in R0.  R0 is that field after (a) a 2-px spacing
  thinning and (b) a "delete everything within 2 px of the catalogue" prune.  Both steps
  removed cells by *geometry*, not by score.

So the field itself is the ranking, and the cells R0 never used are precisely "the next
cells the parent's own model selected".  Within the field the only ordering that the
lineage records is **cross-field support** (the 0-3 vote over anc_h19_5/h19_4/h16_1,
`gems91.consensus`), which is what previous MASS rows used too - but at a 10 % dose from
one ordering only.  This module ranks vote-major and exposes two *geometric* pools so the
dose response and the spacing confound can be separated.

The two pools (this is the experiment)
--------------------------------------
`adj`    cells 8-adjacent to an R0 dot.  Adding these *stacks* mass on cells the lineage
         already accepted; distance from the added dot to the nearest R0 dot is 1.0 or
         1.41 px.  This is the metric-native play: with
         DTI = T / (0.2T + 0.2(S-M) + 0.8|G|), a dot whose own max kernel value is m
         costs 0.2*(1-m) in the denominator, so mass that lands within the 3-px kernel
         of truth is close to free while its credit is added to T.
`spaced` cells **not** 8-adjacent to any dot (nearest dot > 1.41 px, and selected cells
         are also mutually non-adjacent).  Same count, same field, same vote stratum,
         but the parent's no-8-adjacency texture is preserved - the control for
         "is any gain just clustering?" (SPACING clump40 predicted -0.0023).

Both pools exclude catalogue pixels and anything within `min_gap_px` of the catalogue
(brief section 4.4), stay inside the scored footprint, and never move or delete a parent
dot: the edit is addition only, so `S` rises by exactly the number added.

CAVEAT: everything here is a *design*, not a result.  Nothing in this module measures a
score; the algebra it leans on is a MODEL of the organiser metric (see gems91.metric).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

EIGHT = np.ones((3, 3), dtype=bool)

#: pool names this module can build
POOLS = ("adj", "spaced")


def vote_map(*fields: np.ndarray) -> np.ndarray:
    """Cross-field support in 0..n: how many of the lineage's own masks contain the cell."""
    if not fields:
        raise ValueError("vote_map needs at least one field")
    shape = fields[0].shape
    vote = np.zeros(shape, dtype=np.int8)
    for f in fields:
        if f.shape != shape:
            raise ValueError("all fields must share a grid")
        vote += (np.nan_to_num(f, nan=0.0) > 0).astype(np.int8)
    return vote


def candidate_pools(
    field: np.ndarray,
    votes: np.ndarray,
    parent: np.ndarray,
    catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    vote_threshold: int = 1,
    min_gap_px: float = 3.0,
) -> dict[str, np.ndarray]:
    """Boolean masks of eligible cells, per pool, for cells the parent does not already use.

    Eligibility (identical for every pool):
      * inside the scored footprint;
      * positive in the lineage field (the parent's own selection);
      * vote >= `vote_threshold`;
      * not already a parent dot;
      * strictly more than `min_gap_px` from every catalogue pixel.
    """
    field_pos = np.nan_to_num(field, nan=0.0) > 0
    cat = np.nan_to_num(catalogue, nan=0.0) > 0
    parent_dots = np.nan_to_num(parent, nan=0.0) > 0
    dcat = ndi.distance_transform_edt(~cat) if cat.any() else np.full(field_pos.shape, np.inf)
    free = field_pos & ~parent_dots & footprint & (votes >= vote_threshold) & (dcat > min_gap_px)
    adj = ndi.binary_dilation(parent_dots, EIGHT) & ~parent_dots
    return {
        "eligible": free,
        "adj": free & adj,
        "spaced": free & ~ndi.binary_dilation(parent_dots, EIGHT),
        "distance_to_catalogue_px": dcat,
        "parent_dots": parent_dots,
    }


def select_cells(
    pool: np.ndarray,
    n: int,
    *,
    seed: int = 91024,
    forbid_mutual_adjacency: bool = False,
) -> tuple[np.ndarray, dict]:
    """Deterministically pick `n` cells from `pool` (row-major order shuffled by `seed`).

    The shuffle is the only stochastic element: the field is binary, so within a vote
    stratum there is no score to sort on and a seeded draw is the honest tie-break.
    `forbid_mutual_adjacency` keeps the *added* dots from touching each other, which is
    what makes the `spaced` arm a genuine spacing control rather than a second stacking
    arm.
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    idx = np.argwhere(pool)
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(idx))
    chosen: list[tuple[int, int]] = []
    taken = np.zeros(pool.shape, dtype=bool)
    for k in order:
        if len(chosen) >= n:
            break
        r, c = int(idx[k, 0]), int(idx[k, 1])
        if forbid_mutual_adjacency:
            r0, r1 = max(0, r - 1), min(pool.shape[0], r + 2)
            c0, c1 = max(0, c - 1), min(pool.shape[1], c + 2)
            if taken[r0:r1, c0:c1].any():
                continue
        taken[r, c] = True
        chosen.append((r, c))
    out = np.array(sorted(chosen), dtype=np.int64).reshape(-1, 2)
    return out, {
        "n_requested": int(n),
        "n_selected": int(len(out)),
        "shortfall": int(n - len(out)),
        "pool_size": int(pool.sum()),
        "forbid_mutual_adjacency": bool(forbid_mutual_adjacency),
        "seed": int(seed),
    }


def spacing_stats(parent: np.ndarray, added: np.ndarray, dcat: np.ndarray) -> dict:
    """Parent-diff statistics the brief requires, plus the geometry that defines each arm."""
    parent_dots = np.nan_to_num(parent, nan=0.0) > 0
    n_parent = int(parent_dots.sum())
    band = np.zeros(parent_dots.shape, dtype=bool)
    if len(added):
        band[added[:, 0], added[:, 1]] = True
    if (band & parent_dots).any():
        raise ValueError("an added cell is already a parent dot")
    dd = ndi.distance_transform_edt(~parent_dots)
    near = dd[added[:, 0], added[:, 1]] if len(added) else np.array([])
    n_sq = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], dtype=np.int8)
    n_neigh = ndi.convolve(parent_dots, n_sq, mode="constant")
    return {
        "n_dots_parent": n_parent,
        "n_added": int(len(added)),
        "n_removed": 0,
        "n_dots_candidate": n_parent + int(len(added)),
        "pct_changed_of_parent": round(100.0 * len(added) / max(1, n_parent), 4),
        "added_distance_to_nearest_parent_dot_px": {
            "min": float(near.min()) if near.size else None,
            "mean": float(near.mean()) if near.size else None,
            "max": float(near.max()) if near.size else None,
            "frac_8_adjacent": float((near <= np.sqrt(2) + 1e-9).mean()) if near.size else None,
        },
        "added_distance_to_catalogue_px": {
            "min": float(dcat[added[:, 0], added[:, 1]].min()) if len(added) else None,
            "mean": float(dcat[added[:, 0], added[:, 1]].mean()) if len(added) else None,
        },
        "parent_dots_with_8_neighbour": int((n_neigh[parent_dots] > 0).sum()),
        "candidate_dots_with_8_neighbour": int(
            (ndi.convolve((parent_dots | band), n_sq, mode="constant")[parent_dots | band] > 0
             ).sum()
        ),
    }


def build_arm(
    parent: np.ndarray,
    field: np.ndarray,
    votes: np.ndarray,
    catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    n_add: int,
    pool: str,
    seed: int = 91024,
    min_gap_px: float = 3.0,
    vote_threshold: int = 3,
) -> tuple[np.ndarray, dict]:
    """Return (unit-mass band with `n_add` new dots, statistics).  Pure function."""
    if pool not in POOLS:
        raise ValueError(f"pool must be one of {POOLS}; got {pool!r}")
    pools = candidate_pools(field, votes, parent, catalogue, footprint,
                            vote_threshold=vote_threshold, min_gap_px=min_gap_px)
    spaced = pool == "spaced"
    added, sel = select_cells(pools[pool], n_add, seed=seed, forbid_mutual_adjacency=spaced)
    if sel["shortfall"]:
        raise ValueError(
            f"pool {pool!r} only supplied {sel['n_selected']} of {n_add} requested cells; "
            "the dose would silently shrink - lower n_add or pick another pool"
        )
    vals = np.nan_to_num(parent, nan=0.0)
    if not np.allclose(vals[vals > 0], 1.0):
        raise ValueError("parent must be unit mass; MASS expansion assumes one dot = one unit")
    band = np.where(footprint, vals, np.nan).astype(np.float64)
    band[added[:, 0], added[:, 1]] = 1.0
    if not np.isfinite(band[footprint]).all():
        raise ValueError("non-finite value inside footprint")
    stats = spacing_stats(parent, added, pools["distance_to_catalogue_px"])
    stats.update({
        "axis": "MASS",
        "pool": pool,
        "min_gap_px": min_gap_px,
        "selection": sel,
        "vote_threshold": int(vote_threshold),
        "pool_sizes": {k: int(pools[k].sum()) for k in ("adj", "spaced", "eligible")},
        "added_cells_head": added[:5].tolist(),
    })
    return band, stats
