"""XG91: cross-gradient concordance of RTP magnetics and isostatic gravity.

Preregistered in docs/HYPOTHESES_XG91.md before any holdout number. Label-free:
no catalogue pixel is read while the surface is built. Band 6 is not used.
Its file tag says tilt/curvature, but the pinned stack measures it strictly
positive, so it is not a signed tilt angle.

The 2-D cross-gradient (Gallardo & Meju 2003) is

    tau = dm/dx * dg/dy - dm/dy * dg/dx

Parallelism is |cos theta| = sqrt(1 - sin^2 theta), with sin theta = tau /
(|grad m| |grad g|). A covered normal fault can juxtapose susceptibility and
density along the same buried contact. The surface trace lies up-dip of that
contact. The shift is a geometric hypothesis, not a measured dip.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

COT55 = 0.7002075382097097  # cot(55 deg); dip hypothesis, not a fitted parameter
NODATA_FLOOR = -1.0e30


def fill_nearest(values: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Nearest finite footprint pixel. Sentinels are not measurements."""
    a = np.asarray(values, dtype=np.float32)
    fp = np.asarray(footprint, dtype=bool)
    if a.shape != fp.shape:
        raise ValueError("band/footprint shape mismatch")
    good = np.isfinite(a) & (a > NODATA_FLOOR) & fp
    if not good.any():
        raise ValueError("band has no usable footprint pixels")
    indexes = ndi.distance_transform_edt(~good, return_distances=False, return_indices=True)
    return a[tuple(indexes)].astype(np.float32, copy=False)


def _grads(field: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gx = ndi.gaussian_filter(field, sigma, order=(0, 1), mode="nearest")
    gy = ndi.gaussian_filter(field, sigma, order=(1, 0), mode="nearest")
    mag = np.hypot(gx, gy).astype(np.float32)
    return gx.astype(np.float32), gy.astype(np.float32), mag


def parallelism(magnetic: np.ndarray, gravity: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    """Return (|cos theta|, |grad m| * |grad g|) at one scale. Both are >= 0."""
    mx, my, mm = _grads(magnetic, sigma)
    gx, gy, gm = _grads(gravity, sigma)
    tau = mx * gy - my * gx
    denom = np.maximum(mm * gm, 1e-12)
    sin2 = np.clip((tau * tau) / (denom * denom), 0.0, 1.0)
    cos_abs = np.sqrt(1.0 - sin2).astype(np.float32)
    strength = (mm * gm).astype(np.float32)
    return cos_abs, strength


def percentile_rank(values: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Average-rank percentile in (0, 1) inside the footprint, 0 outside."""
    fp = np.asarray(footprint, dtype=bool)
    out = np.zeros(fp.shape, dtype=np.float32)
    v = np.asarray(values, dtype=np.float64)[fp]
    if v.size == 0:
        raise ValueError("empty footprint")
    sorted_v = np.sort(v)
    left = np.searchsorted(sorted_v, v, side="left")
    right = np.searchsorted(sorted_v, v, side="right")
    avg = (left + right + 1) / 2.0
    out[fp] = (avg / (v.size + 1.0)).astype(np.float32)
    return out


def concordance_surface(
    rtp: np.ndarray,
    gravity: np.ndarray,
    footprint: np.ndarray,
    *,
    sigmas: tuple[float, float] = (2.0, 6.0),
) -> dict[str, np.ndarray]:
    """Label-free concordance. Geometric mean across scales so both must agree."""
    fp = np.asarray(footprint, dtype=bool)
    m = fill_nearest(rtp, fp)
    g = fill_nearest(gravity, fp)
    parts = []
    out: dict[str, np.ndarray] = {}
    for sigma in sigmas:
        cos_abs, strength = parallelism(m, g, sigma)
        # Down-weight parallel noise where either gradient is weak.
        score = cos_abs * percentile_rank(strength, fp)
        score = np.where(fp, score, 0.0).astype(np.float32)
        key = f"xg_concord_s{int(sigma)}"
        out[key] = score
        parts.append(score)
    concord = np.sqrt(np.maximum(parts[0], 0) * np.maximum(parts[1], 0)).astype(np.float32)
    concord = np.where(fp, concord, 0.0)
    out["xg_concord"] = concord
    return out


def updip_shadow(
    concord: np.ndarray,
    depth_m: np.ndarray,
    footprint: np.ndarray,
    *,
    min_px: float = 2.0,
    max_px: float = 8.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Sample the contact score from the downdip side onto the updip trace.

    Depth gradient points toward thicker cover (downdip for a basin-bounding
    normal fault). The buried geophysical contact is downdip of the surface
    trace, so the value written at the trace is the concordance sampled
    `shift` px along +grad(depth).
    """
    fp = np.asarray(footprint, dtype=bool)
    depth = fill_nearest(depth_m, fp)
    # Smooth the depth gradient so a one-pixel basement artifact does not flip dip.
    gy = ndi.gaussian_filter(depth, 3.0, order=(1, 0), mode="nearest")
    gx = ndi.gaussian_filter(depth, 3.0, order=(0, 1), mode="nearest")
    mag = np.hypot(gy, gx)
    uy = np.divide(gy, mag, out=np.zeros_like(gy), where=mag > 1e-6)
    ux = np.divide(gx, mag, out=np.zeros_like(gx), where=mag > 1e-6)
    shift = np.clip(np.maximum(depth, 0.0) * np.float32(COT55) / 100.0, min_px, max_px).astype(np.float32)
    yy, xx = np.indices(concord.shape)
    src_y = yy + uy * shift
    src_x = xx + ux * shift
    sampled = ndi.map_coordinates(concord, [src_y, src_x], order=1, mode="nearest").astype(np.float32)
    sampled = np.where(fp, sampled, 0.0)
    return sampled, shift


def deep_cover_weight(depth_m: np.ndarray, footprint: np.ndarray, *, soft: bool) -> np.ndarray:
    """Soft weight keeps range fronts; hard weight is the preregistered E3 gate."""
    fp = np.asarray(footprint, dtype=bool)
    depth = fill_nearest(depth_m, fp)
    pct = percentile_rank(depth, fp)
    if soft:
        weight = (0.35 + 0.65 * pct).astype(np.float32)
    else:
        threshold = float(np.quantile(depth[fp], 0.75))
        weight = np.where(depth >= threshold, np.float32(1.0), np.float32(0.0))
    return np.where(fp, weight, 0.0).astype(np.float32)


def emit_spaced_dots(
    score: np.ndarray,
    eligible: np.ndarray,
    *,
    spacing_px: float,
    n_dots: int,
) -> np.ndarray:
    """Deterministic local-maximum thinning. Unit dots, zero elsewhere."""
    if spacing_px < 1.0 or n_dots < 1:
        raise ValueError("spacing and budget must be positive")
    elig = np.asarray(eligible, dtype=bool)
    field = np.where(elig, np.asarray(score, dtype=np.float32), 0.0)
    size = int(np.floor(spacing_px))
    size = max(size, 1)
    local = ndi.maximum_filter(field, size=size)
    peaks = elig & (field > 0) & (field >= local)
    ys, xs = np.nonzero(peaks)
    if ys.size == 0:
        raise ValueError("no eligible peaks")
    order = np.argsort(field[ys, xs], kind="mergesort")[::-1]
    cell = int(np.ceil(spacing_px))
    buckets: dict[tuple[int, int], list[tuple[int, int]]] = {}
    keep_y: list[int] = []
    keep_x: list[int] = []
    min_d2 = float(spacing_px) * float(spacing_px)
    for i in order:
        y = int(ys[i])
        x = int(xs[i])
        cy, cx = y // cell, x // cell
        ok = True
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for py, px in buckets.get((cy + dy, cx + dx), ()):
                    if (py - y) * (py - y) + (px - x) * (px - x) < min_d2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if not ok:
            continue
        buckets.setdefault((cy, cx), []).append((y, x))
        keep_y.append(y)
        keep_x.append(x)
        if len(keep_y) >= n_dots:
            break
    out = np.zeros(score.shape, dtype=np.float32)
    out[np.asarray(keep_y), np.asarray(keep_x)] = 1.0
    return out
