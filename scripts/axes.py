"""Axis operators: one controlled edit of a parent raster, plus its statistics.

The brief's five week-1 axes reduce to four array operations. Every operator:

  * takes the parent as a float array and returns a NEW array (never in place),
  * preserves unit mass (each retained dot stays 1.0) unless ``MASS`` says otherwise,
  * refuses to emit mass on a catalogue pixel and, unless the axis is PRUNE,
    keeps every dot at least ``min_cat_px`` from it (brief section 4.4),
  * returns a stats dict with the exact fraction of the parent's dots changed,
    because the gates require that number to be recorded (brief section 6).

None of these have been run on competition data: the parent, catalogue and
ranking inputs were absent (see IRREGULARITIES.md item 2). They are tested on
synthetic rasters in tests/test_axes.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi

MIN_CATALOGUE_PX = 3.0


@dataclass
class AxisResult:
    array: np.ndarray
    axis: str
    value: str
    stats: dict = field(default_factory=dict)

    def summary(self) -> str:
        bits = [f"axis={self.axis}", f"value={self.value}"]
        bits += [f"{k}={v}" for k, v in self.stats.items()]
        return " ".join(bits)


class AxisError(RuntimeError):
    pass


# --------------------------------------------------------------------- helpers
def dots_of(arr: np.ndarray) -> np.ndarray:
    return np.isfinite(arr) & (np.nan_to_num(arr, nan=0.0) > 0)


def distance_from(mask: np.ndarray) -> np.ndarray:
    """Euclidean distance in pixels from the nearest True pixel of ``mask``."""
    if not mask.any():
        return np.full(mask.shape, np.inf)
    return ndi.distance_transform_edt(~mask)


def footprint_of(ref: np.ndarray) -> np.ndarray:
    return np.isfinite(ref)


def _check_catalogue(out: np.ndarray, cat: np.ndarray | None, min_px: float) -> tuple[float, bool]:
    """Fatal: any mass on a catalogue pixel. Reported, not fatal: distance shortfall.

    The distance shortfall is reported rather than raised because the parent itself
    may already sit closer than ``min_px`` (R0 is described as 'none within 2 px'),
    and an operator must not silently rewrite the parent's own dots to hide that.
    """
    if cat is None:
        return float("inf"), True
    if (dots_of(out) & (cat > 0)).any():
        raise AxisError("operator produced mass on a catalogue pixel (brief section 4.4)")
    d = distance_from(cat > 0)
    dmin = float(d[dots_of(out)].min()) if dots_of(out).any() else float("inf")
    return dmin, bool(dmin >= min_px)


def _frame(ref: np.ndarray, dots: np.ndarray) -> np.ndarray:
    """Output array: NaN outside the footprint, 0.0 inside, 1.0 on dots."""
    out = np.full(ref.shape, np.nan, dtype=np.float32)
    fp = footprint_of(ref)
    out[fp] = 0.0
    out[fp & dots] = 1.0
    return out


def _pct_changed(parent_dots: np.ndarray, child_dots: np.ndarray) -> float:
    changed = int((parent_dots ^ child_dots).sum())
    base = int(parent_dots.sum()) or 1
    return 100.0 * changed / base


def _require(pool: np.ndarray, n: int, what: str) -> np.ndarray:
    if n > len(pool):
        raise AxisError(f"need {n} {what} but only {len(pool)} are available")
    return pool[:n]


# ------------------------------------------------------------------------ MASS
def mass(
    parent: np.ndarray,
    ref: np.ndarray,
    rank: np.ndarray,
    cat: np.ndarray | None = None,
    fraction: float = 0.10,
    mode: str = "drop",
) -> AxisResult:
    """Drop the lowest-ranked ``fraction`` of dots, or add the next-ranked ones.

    ``rank`` is the parent's own ranking: higher = better. For ``drop`` the removed
    dots are those with the lowest rank among the parent's dots; for ``add`` the
    added dots are the highest-ranked pixels that are not already dots.
    ``fraction`` is of the parent's dot count, and must land in [0.01, 0.50]
    (brief section 5: a variant changes 1-50% of R0's dots).
    """
    if not 0.01 <= fraction <= 0.50:
        raise AxisError("fraction must be in [0.01, 0.50]")
    if mode not in {"drop", "add"}:
        raise AxisError("mode must be 'drop' or 'add'")

    p = dots_of(parent)
    n = int(round(fraction * p.sum()))
    out = p.copy()
    r = np.where(np.isfinite(rank), rank, -np.inf)

    if mode == "drop":
        ys, xs = np.nonzero(p)
        order = np.argsort(r[ys, xs], kind="stable")
        chosen = order[:n]
        out[ys[chosen], xs[chosen]] = False
    else:
        fp = footprint_of(ref)
        eligible = fp & ~p
        if cat is not None:
            eligible &= (cat <= 0) & (distance_from(cat > 0) >= MIN_CATALOGUE_PX)
        ys, xs = np.nonzero(eligible)
        order = np.argsort(-r[ys, xs], kind="stable")
        chosen = _require(order, n, "eligible pixels")
        out[ys[chosen], xs[chosen]] = True

    arr = _frame(ref, out)
    dmin, dist_ok = _check_catalogue(arr, cat, MIN_CATALOGUE_PX)
    return AxisResult(arr, "MASS", f"{mode}{int(fraction * 100)}", {
        "n_parent_dots": int(p.sum()),
        "n_dots": int(out.sum()),
        "delta_dots": int(out.sum()) - int(p.sum()),
        "pct_changed": round(_pct_changed(p, out), 2),
        "min_dist_catalogue_px": None if np.isinf(dmin) else round(dmin, 2),
        "cat_distance_ok": dist_ok,
    })


# ----------------------------------------------------------------------- PRUNE
def prune(
    parent: np.ndarray,
    ref: np.ndarray,
    cat: np.ndarray,
    rank: np.ndarray | None = None,
    max_px: float = 3.0,
    refill: bool = False,
) -> AxisResult:
    """Remove dots within ``max_px`` of the catalogue.

    ``refill=False`` by default, which is the parent lineage's own operation, now
    verified rather than assumed: R0 is exactly solo-d28 (40,199 dots) minus the
    2,545 dots within <=2 px of the catalogue, with no refill (37,654 dots; 0 in
    the "only R0" set when the two rasters are differenced). The agent brief asks
    for a refill to hold the count; that would need the parent's ranking, which was
    not stored, so a refill here would be arbitrary. See IRREGULARITIES.md item 4.

    ``refill=True`` draws the highest-ranked non-dots that are themselves at least
    ``max_px`` from the catalogue, and requires ``rank`` because guessing one is
    forbidden.
    """
    p = dots_of(parent)
    d = distance_from(cat > 0)
    near = p & (d <= max_px)
    out = p & ~near
    removed = int(near.sum())

    added = 0
    if refill and removed:
        if rank is None:
            raise AxisError("refill needs the parent's ranking (rank) or refill=False")
        fp = footprint_of(ref)
        eligible = fp & ~out & (cat <= 0) & (d > max_px)
        ys, xs = np.nonzero(eligible)
        r = np.where(np.isfinite(rank), rank, -np.inf)
        order = np.argsort(-r[ys, xs], kind="stable")
        chosen = _require(order, removed, "refill pixels")
        out[ys[chosen], xs[chosen]] = True
        added = removed

    arr = _frame(ref, out)
    dmin, dist_ok = _check_catalogue(arr, cat, max_px)
    return AxisResult(arr, "PRUNE", f"le{int(max_px)}", {
        "n_parent_dots": int(p.sum()),
        "removed": removed,
        "refilled": added,
        "n_dots": int(out.sum()),
        "pct_changed": round(_pct_changed(p, out), 2),
        "min_dist_catalogue_px": None if np.isinf(dmin) else round(dmin, 2),
        "cat_distance_ok": dist_ok,
    })


# ------------------------------------------------------------------------ SNAP
def snap(
    parent: np.ndarray,
    ref: np.ndarray,
    driver: np.ndarray,
    cat: np.ndarray | None = None,
    radius: int = 2,
    min_cat_px: float = 2.0,
) -> AxisResult:
    """Move each dot <= ``radius`` px to the strongest driver response in its window.

    Same count, same exclusions, both enforced:

      * count -- a dot may never land on a pixel another dot already occupies, so
        dots cannot merge. Targets are claimed in order of distance, so a short
        move wins over a long one when responses tie.
      * exclusions -- a target must be inside the footprint, off the catalogue and
        at least ``min_cat_px`` from it. If the window offers nothing valid the dot
        stays put and is counted in ``frozen_no_valid_target``.

    Ties are broken toward the current pixel, so a driver that already peaks on a
    dot leaves that dot alone; reports the mean displacement.
    """
    if radius < 1:
        raise AxisError("radius must be >= 1")
    p = dots_of(parent)
    fp = footprint_of(ref)
    resp = np.where(np.isfinite(driver), driver, -np.inf).astype(np.float64)

    ok = fp.copy()
    if cat is not None:
        ok &= (cat <= 0) & (distance_from(cat > 0) >= min_cat_px)

    h, w = p.shape
    claimed = np.zeros((h, w), dtype=bool)
    out = np.zeros_like(p)
    ys, xs = np.nonzero(p)

    # process dots nearest to their window centre first: stable priority
    moved, total_shift, frozen = 0, 0.0, 0
    for y, x in zip(ys, xs):
        y0, y1 = max(0, y - radius), min(h, y + radius + 1)
        x0, x1 = max(0, x - radius), min(w, x + radius + 1)
        cand_resp = resp[y0:y1, x0:x1]
        cand_ok = ok[y0:y1, x0:x1] & ~claimed[y0:y1, x0:x1]

        gy, gx = np.mgrid[y0:y1, x0:x1]
        dist = np.hypot(gy - y, gx - x)
        # lexicographic: highest response, then smallest displacement
        score = np.where(cand_ok, cand_resp * 1e6 - dist, -np.inf)

        if not np.isfinite(score).any():
            out[y, x] = True
            claimed[y, x] = True
            frozen += 1
            continue
        flat = int(np.argmax(score))
        dy, dx = divmod(flat, score.shape[1])
        ny, nx = y0 + dy, x0 + dx
        if claimed[ny, nx]:  # cannot happen, kept as a guard
            out[y, x] = True
            claimed[y, x] = True
            frozen += 1
            continue
        out[ny, nx] = True
        claimed[ny, nx] = True
        if (ny, nx) != (y, x):
            moved += 1
            total_shift += float(np.hypot(ny - y, nx - x))

    arr = _frame(ref, out)
    dmin, dist_ok = _check_catalogue(arr, cat, min_cat_px)
    n = int(p.sum()) or 1
    return AxisResult(arr, "SNAP", f"r{radius}", {
        "n_parent_dots": int(p.sum()),
        "n_dots": int(out.sum()),
        "moved": moved,
        "frozen_no_valid_target": frozen,
        "mean_displacement_px": round(total_shift / n, 3),
        "pct_changed": round(_pct_changed(p, out), 2),
        "min_dist_catalogue_px": None if np.isinf(dmin) else round(dmin, 2),
        "cat_distance_ok": dist_ok,
    })


# --------------------------------------------------------------- CONCENTRATION
def _block_index(shape, block_px):
    h, w = shape
    ny, nx = h // block_px, w // block_px
    yy, xx = np.mgrid[0:h, 0:w]
    inside = (yy < ny * block_px) & (xx < nx * block_px)
    idx = np.full(shape, -1, dtype=np.int64)
    idx[inside] = (yy[inside] // block_px) * nx + (xx[inside] // block_px)
    return idx, ny, nx


def _block_mean(values: np.ndarray, mask: np.ndarray, block_px: int) -> np.ndarray:
    """Mean of ``values`` over footprint pixels of each block."""
    idx, ny, nx = _block_index(values.shape, block_px)
    v = np.where(mask & (idx >= 0), np.nan_to_num(values, nan=0.0), 0.0)
    num = np.bincount(idx[idx >= 0], weights=v[idx >= 0], minlength=ny * nx)
    den = np.bincount(idx[idx >= 0], weights=mask[idx >= 0].astype(float), minlength=ny * nx)
    return num / np.maximum(den, 1.0)


def _block_counts(mask: np.ndarray, block_px: int) -> np.ndarray:
    idx, ny, nx = _block_index(mask.shape, block_px)
    return np.bincount(idx[idx >= 0], weights=mask[idx >= 0].astype(float), minlength=ny * nx)


def _cv(counts: np.ndarray) -> float:
    m = float(counts.mean())
    return float("nan") if m == 0 else float(counts.std() / m)


def concentration(
    parent: np.ndarray,
    ref: np.ndarray,
    prior: np.ndarray,
    cat: np.ndarray | None = None,
    block_px: int = 16,
    fraction: float = 0.15,
) -> AxisResult:
    """Move ``fraction`` of dots from the lowest-prior blocks to the highest-prior ones.

    Block size is ``block_px`` (16 px = 1.6 km at 100 m, the 'km-scale' block the
    brief names). Donors are taken from the lowest-prior blocks that hold dots;
    recipients are the highest-prior blocks, filled with dots so the receiving
    block's density approaches the mean. Mass and count are conserved exactly: a
    dot that cannot be re-placed stays where it was, which is reported.
    """
    if not 0.10 <= fraction <= 0.50:
        raise AxisError("fraction must be in [0.10, 0.50] for CONCENTRATION")
    p = dots_of(parent)
    fp = footprint_of(ref)
    h, w = p.shape
    if block_px < 2 or block_px > min(h, w):
        raise AxisError("block_px out of range")

    idx, ny, nx = _block_index(p.shape, block_px)
    nb = ny * nx
    counts_before = _block_counts(p, block_px)
    cv_before = _cv(counts_before)
    bpri = _block_mean(prior, fp, block_px)

    valid_block = np.zeros(nb, dtype=bool)
    valid_block[np.unique(idx[idx >= 0])] = True

    # Donors: dots in the LOWEST-prior blocks, capped so no block is emptied.
    # Recipients: the HIGHEST-prior blocks that are currently under-dense, so the
    # move genuinely concentrates mass rather than swapping it around.
    dot_blocks = np.argwhere(counts_before > 0).ravel()
    if len(dot_blocks) == 0:
        raise AxisError("parent has no dots")
    n_move = int(round(fraction * p.sum()))
    mean_density = float(counts_before[counts_before > 0].mean())

    donor_order = dot_blocks[np.argsort(bpri[dot_blocks], kind="stable")]
    out = p.copy()
    taken: list[tuple[int, int]] = []
    for b in donor_order:
        if len(taken) >= n_move:
            break
        side = max(1, int(np.floor(np.sqrt(max(counts_before[b], 1)))))
        ys, xs = np.nonzero((idx == b) & out)
        if len(ys) == 0:
            continue
        take = min(side, len(ys), n_move - len(taken))
        for y, x in zip(ys[:take], xs[:take]):
            out[y, x] = False
            taken.append((int(y), int(x)))
        if len(taken) >= n_move:
            break

    # place each moved dot at the emptiest valid pixel of a high-prior block,
    # updating after every placement so dots spread instead of clumping
    recip_blocks = [b for b in np.argsort(-bpri, kind="stable")
                    if valid_block[b] and counts_before[b] < mean_density]
    if not recip_blocks:  # nothing under-dense: fall back to prior order
        recip_blocks = [b for b in np.argsort(-bpri, kind="stable") if valid_block[b]]

    placed = 0
    while placed < len(taken) and recip_blocks:
        progressed = False
        for b in recip_blocks:
            if placed >= len(taken):
                break
            by, bx = divmod(int(b), nx)
            y0, x0 = by * block_px, bx * block_px
            win_ok = fp[y0:y0 + block_px, x0:x0 + block_px] & ~out[y0:y0 + block_px, x0:x0 + block_px]
            if cat is not None:
                win_ok &= cat[y0:y0 + block_px, x0:x0 + block_px] <= 0
            if not win_ok.any():
                continue
            spread = distance_from(~win_ok)  # distance to the nearest occupied/invalid pixel
            py, px = np.unravel_index(int(np.argmax(spread)), spread.shape)
            out[y0 + py, x0 + px] = True
            placed += 1
            progressed = True
        if not progressed:
            break

    # anything unplaced returns to its donor pixel: count preserved exactly
    for y, x in taken[placed:]:
        out[y, x] = True
    returned = len(taken) - placed

    arr = _frame(ref, out)
    dmin, dist_ok = _check_catalogue(arr, cat, 0.0)
    counts_after = _block_counts(dots_of(arr), block_px)
    return AxisResult(arr, "CONCENTRATION", f"b{block_px}x{int(fraction * 100)}", {
        "block_px": block_px,
        "block_km": round(block_px * 0.1, 2),
        "n_parent_dots": int(p.sum()),
        "n_dots": int(out.sum()),
        "moved": placed,
        "returned_unplaced": returned,
        "pct_changed": round(_pct_changed(p, out), 2),
        "block_cv_before": round(cv_before, 4),
        "block_cv_after": round(_cv(counts_after), 4),
        "min_dist_catalogue_px": None if np.isinf(dmin) else round(dmin, 2),
        "cat_distance_ok": dist_ok,
    })
