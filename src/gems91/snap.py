"""SNAP axis: move each dot <= radius px onto the strongest local edge response.

The brief defines SNAP as *same count, same exclusions*: every dot is re-placed
inside a small window, no dot is added or removed, and the catalogue collar is
untouched.  Two repo rules make the implementation stricter than ``axes.snap``:

* **IR-91-27** -- R0 carries 2,171 dots at ``2 < d_cat <= 3 px``.  Touching them
  would execute a silent PRUNE edit inside a SNAP build, so they are quarantined
  (left exactly where they are, still counted, and still excluded from every
  target window).  ``collar_before == collar_after`` is asserted by the builder.
* **No regional drift** -- a raw gradient band has km-scale trends; snapping to
  its global maximum inside a 2 px window would drag whole neighbourhoods one way
  and turn SNAP into a CONCENTRATION edit.  The driver is therefore
  *locally high-passed* (band minus a 600 m Gaussian) before ranking, so only the
  local crest of the edge response can win.

Driver preparation is in ``prepare_driver``; the move itself is in ``snap_dots``.
Everything is deterministic: dots are processed in a fixed priority order and
ties break on displacement, then row-major position.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage as ndi

NODATA_SENTINEL = -1.0e30  # competition bands use -3.4028235e38
DEFAULT_CATALOGUE_PX = 3.0  # brief section 4.4: keep >= 3 px from the catalogue


@dataclass
class SnapResult:
    dots: np.ndarray
    stats: dict = field(default_factory=dict)


def _fill_nodata(values: np.ndarray, bad: np.ndarray) -> np.ndarray:
    """Nearest-valid fill. Outside-footprint nodata is filled too, then masked later."""
    if not bad.any():
        return values.astype(np.float64, copy=True)
    idx = ndi.distance_transform_edt(bad, return_distances=False, return_indices=True)
    return values[tuple(idx)].astype(np.float64, copy=False)


def prepare_driver(
    band: np.ndarray,
    footprint: np.ndarray,
    *,
    signed: bool = False,
    high_pass_sigma_px: float = 6.0,
    log_compress: bool = True,
) -> np.ndarray:
    """Turn a gradient band into a local edge-response field.

    Steps, in order: take ``|band|`` if the band is a signed directional
    derivative, compress the heavy tail with ``log1p``, nearest-fill nodata,
    subtract a Gaussian low-pass (``sigma`` pixels = 600 m at 100 m cells), and
    divide by a robust scale (1.4826 * MAD over the footprint).  Cells outside
    the footprint are set to ``-inf`` so they can never win a window.
    """
    v = np.asarray(band, dtype=np.float64)
    bad = ~np.isfinite(v) | (v <= NODATA_SENTINEL)
    v = np.where(bad, 0.0, v)
    if signed:
        v = np.abs(v)
    if log_compress:
        v = np.log1p(np.clip(v, 0.0, None))
    v = _fill_nodata(v, bad)
    local = ndi.gaussian_filter(v, sigma=float(high_pass_sigma_px), mode="nearest")
    hp = v - local
    ref = hp[footprint]
    med = float(np.median(ref))
    mad = float(np.median(np.abs(ref - med)))
    scale = 1.4826 * mad if mad > 0 else float(ref.std() or 1.0)
    z = (hp - med) / scale
    z = np.where(footprint, z, -np.inf)
    return z.astype(np.float64)


def combine_drivers(fields: list[np.ndarray], footprints: np.ndarray) -> np.ndarray:
    """Equal-weight mean of already-standardised drivers (z is comparable)."""
    if not fields:
        raise ValueError("need at least one driver")
    stack = np.stack(fields, axis=0)
    mean = stack.mean(axis=0)
    return np.where(footprints, mean, -np.inf)


def _window_offsets(radius: float) -> list[tuple[int, int, float]]:
    n = int(np.ceil(radius))
    out = []
    for dy in range(-n, n + 1):
        for dx in range(-n, n + 1):
            d = float(np.hypot(dy, dx))
            if d <= radius:
                out.append((dy, dx, d))
    return out


def snap_dots(
    parent: np.ndarray,
    footprint: np.ndarray,
    dcat: np.ndarray,
    driver: np.ndarray,
    *,
    radius: float = 2.0,
    min_cat_px: float = DEFAULT_CATALOGUE_PX,
    min_gain: float = 0.0,
    mode: str = "max",
) -> SnapResult:
    """Move every eligible dot at most ``radius`` px to the strongest driver cell.

    ``mode="max"`` snaps to the highest valid cell in the window (the literal
    brief rule); ``mode="lmax"`` snaps only to a 3x3 *local maximum* of the
    driver (the strongest crest in the window), which stops a dot that sits on a
    smooth regional slope from sliding to the window edge every time.

    ``parent`` is a boolean dot mask.  Dots at ``d_cat <= min_cat_px`` are
    quarantined in place (IR-91-27); every other dot is offered a window of cells
    that are inside the footprint, ``> min_cat_px`` from the catalogue and not
    already claimed by another dot.  A dot moves only if some valid cell has a
    strictly larger driver value than the cell it occupies; ties prefer the
    shorter move and then the current cell, so a flat driver is a no-op.
    """
    p = np.asarray(parent, dtype=bool)
    fp = np.asarray(footprint, dtype=bool)
    resp = np.where(fp & np.isfinite(driver), driver, -np.inf)

    valid_cell = fp & (np.asarray(dcat, dtype=np.float64) > float(min_cat_px))
    collar = p & ~valid_cell
    eligible = p & valid_cell

    if mode not in ("max", "lmax"):
        raise ValueError(mode)
    crest = None
    if mode == "lmax":
        crest = np.isfinite(resp) & (resp == ndi.maximum_filter(resp, size=3))

    ys, xs = np.nonzero(eligible)
    offsets = _window_offsets(radius)
    h, w = p.shape

    # Priority: dots with the largest raw window gain move first, so the
    # best-defined crest is claimed before a neighbour can take it.
    gains = np.empty(len(ys), dtype=np.float64)
    for k, (y, x) in enumerate(zip(ys, xs)):
        y0, y1 = max(0, y - int(np.ceil(radius))), min(h, y + int(np.ceil(radius)) + 1)
        x0, x1 = max(0, x - int(np.ceil(radius))), min(w, x + int(np.ceil(radius)) + 1)
        gains[k] = float(resp[y0:y1, x0:x1].max()) - float(resp[y, x])
    order = np.lexsort((xs, ys, -gains))

    out = collar.copy()
    # Every parent dot owns its cell until it leaves it, so no dot can be evicted
    # by a neighbour that processed earlier; a moved dot frees its old cell.
    claimed = p.copy()
    moved = 0
    total_shift = 0.0
    max_shift = 0.0
    gain_sum = 0.0
    n_improved = 0
    for k in order:
        y, x = int(ys[k]), int(xs[k])
        # (response, -distance, y, x); ties prefer the shorter move then own cell
        best = (resp[y, x], 0.0, y, x)
        for dy, dx, dist in offsets:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < h and 0 <= nx < w):
                continue
            if not valid_cell[ny, nx]:
                continue
            if claimed[ny, nx]:
                continue
            if crest is not None and not crest[ny, nx]:
                continue
            cand = resp[ny, nx]
            key = (cand, -dist)
            if key > (best[0], best[1]):
                best = (cand, -dist, ny, nx)
        _, negd, ny, nx = best
        if (ny, nx) != (y, x) and float(resp[ny, nx] - resp[y, x]) <= float(min_gain):
            ny, nx, negd = y, x, 0.0  # gain below the pre-registered dose: stay put
        out[ny, nx] = True
        claimed[ny, nx] = True
        if (ny, nx) != (y, x):
            claimed[y, x] = False  # vacated: a later dot may take it
            dist = -negd
            moved += 1
            total_shift += dist
            max_shift = max(max_shift, dist)
            gain_sum += float(resp[ny, nx] - resp[y, x])
            n_improved += 1

    n = int(p.sum()) or 1
    collar_n = int(collar.sum())
    return SnapResult(out, {
        "n_parent_dots": int(p.sum()),
        "n_dots": int(out.sum()),
        "n_collar_quarantined": collar_n,
        "n_eligible": int(eligible.sum()),
        "n_moved": moved,
        "n_stayed": int(eligible.sum()) - moved,
        "pct_moved": round(100.0 * moved / n, 4),
        "pct_hamming": round(200.0 * moved / n, 4),
        "mean_displacement_px": round(total_shift / n, 4),
        "mean_displacement_moved_px": round(total_shift / moved, 4) if moved else 0.0,
        "max_displacement_px": round(max_shift, 4),
        "mean_driver_gain_z": round(gain_sum / n_improved, 4) if moved else 0.0,
        "collar_before": collar_n,
        "collar_after": int((out & ~valid_cell).sum()),
    })
