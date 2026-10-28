"""S25 ``TLF`` lane: Topographic-Lidar Fusion of lineament ridges.

Hypothesis (H25-1, mechanism first):
    Newly mapped faults in the Great Basin have a **topographic expression**
    (fault scarps, composite ridges, faceted spurs) that heals quickly in
    potential-field data but survives in a 100 m DEM slope field and in
    lidar-derived scarp attributes.  A *lineament* response -- gradient
    magnitude weighted by structure-tensor coherence, so that only elongated,
    single-direction edges answer -- should therefore separate fault traces
    from isotropic terrain relief.

    The competition truth is expert-mapped faults **absent from the public
    catalogue**; the catalogue is only used here as an *exclusion collar*
    (a predicted mass on an already-mapped trace cannot earn discovery credit
    and pays false-positive cost).

Named non-fault process that can mimic it: aeolian/playa margins, fluvial
    terrace risers and lake shorelines also make elongated topographic edges.
    The leakage canary and the SGMC off-catalogue control are the guards; the
    per-quadrant breakdown is reported so a single-region artefact cannot hide
    inside a pooled number.

Everything in this module is deterministic given its inputs: no RNG, no
    threshold fitted on the scored truth at emission time.  Weights are the
    non-negative excess AUC of each layer against the *external* control only,
    and the budget is chosen from a density-robustness curve, not from the
    maximum of the control (see ``docs/s25/REVIEW.md``).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

BAND_INDEX = {  # 1-based band numbers in gems-geodawn-numerical-features.tif
    "rtp": 2,      # reduced-to-pole magnetic anomaly
    "tc": 6,       # tilt angle / total curvature
    "dele": 19,    # detrended-elevation slope
}
LIDAR_BAND = 8     # lidar scarp features, band 8 = ``cross_max``


def read_band(path, index: int) -> np.ndarray:
    """Read one band, replacing only the declared NoData sentinel by the median.

    NoData is never treated as zero: substituting zeros into a derivative
    filter would manufacture a false step edge along every survey edge.
    """
    import rasterio
    with rasterio.open(path) as src:
        a = src.read(index).astype(np.float32)
        nod = src.nodata
    bad = ~np.isfinite(a)
    if nod is not None and np.isfinite(nod):
        bad |= np.isclose(a, np.float32(nod), rtol=0, atol=1e-6)
    if bad.any():
        a = a.copy()
        a[bad] = float(np.median(a[~bad]))
    return a


def lineament(field: np.ndarray, sigma: float = 2.0, coherence_sigma: float = 4.0) -> np.ndarray:
    """Coherence-weighted gradient magnitude (structure-tensor lineament response).

    ``R = |grad f| * (l1 - l2) / (l1 + l2)`` with ``l1, l2`` the eigenvalues of
    the smoothed structure tensor.  An isotropic blob or a 2-D patch has equal
    eigenvalues and is suppressed; a scarp is anisotropic and survives.
    """
    g = ndi.gaussian_filter(field.astype(np.float32), sigma)
    gy, gx = np.gradient(g)
    jxx = ndi.gaussian_filter(gx * gx, coherence_sigma)
    jyy = ndi.gaussian_filter(gy * gy, coherence_sigma)
    jxy = ndi.gaussian_filter(gx * gy, coherence_sigma)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr / 4.0 - det, 0.0))
    l1 = tr / 2.0 + disc
    l2 = np.maximum(tr / 2.0 - disc, 0.0)
    coherence = (l1 - l2) / (l1 + l2 + 1e-9)
    return np.sqrt(gx * gx + gy * gy) * coherence


def percentile_rank(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """Rank-transform to [0,1) inside ``valid``; 0 elsewhere."""
    r = np.zeros(x.shape, np.float32)
    v = np.asarray(x[valid], np.float64)
    order = np.argsort(v, kind="stable")
    rk = np.empty(v.size, np.float32)
    rk[order] = np.linspace(0.0, 1.0, v.size, endpoint=False)
    r[valid] = rk
    return r


def auc(score: np.ndarray, truth: np.ndarray, valid: np.ndarray) -> float:
    """Rank (Mann-Whitney) AUC; ties get average ranks."""
    s = np.asarray(score[valid], np.float64)
    y = np.asarray(truth[valid], bool)
    n1 = int(y.sum())
    n0 = int((~y).sum())
    if n1 == 0 or n0 == 0:
        return float("nan")
    order = np.argsort(s, kind="stable")
    ranks = np.empty(s.size, np.float64)
    ranks[order] = np.arange(1, s.size + 1)
    uniq, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    avg = np.bincount(inv, weights=ranks) / cnt
    ranks = avg[inv]
    return float((ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0))


def poisson_disc(score: np.ndarray, allow: np.ndarray, spacing: float, budget: int):
    """Greedy maximum-score Poisson-disc selection on the lattice.

    Cells are visited best-first and accepted only when no accepted dot lies
    within ``spacing`` pixels.  This is the emission rule that makes the
    300 m kernel tile the candidate ridge instead of stacking on it: stacked
    mass earns no extra truth credit (the metric takes ``max`` per truth cell)
    but pays full false-positive cost.
    """
    cand = np.argwhere(allow)
    if cand.size == 0:
        return np.zeros((0, 2), np.int64)
    vals = score[cand[:, 0], cand[:, 1]]
    order = np.lexsort((cand[:, 1], cand[:, 0], -vals))
    cand = cand[order]
    cell = float(spacing)
    buckets: dict[tuple[int, int], list[tuple[int, int]]] = {}
    out: list[tuple[int, int]] = []
    s2 = spacing * spacing
    for y, x in cand:
        gy, gx = int(y // cell), int(x // cell)
        ok = True
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for yy, xx in buckets.get((gy + dy, gx + dx), ()):  # noqa: E501
                    if (yy - y) ** 2 + (xx - x) ** 2 < s2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            buckets.setdefault((gy, gx), []).append((y, x))
            out.append((y, x))
            if len(out) >= budget:
                break
    return np.array(out, np.int64).reshape(-1, 2)


def emit(score: np.ndarray, allow: np.ndarray, spacing: float, budget: int,
         shape: tuple[int, int]) -> np.ndarray:
    """Binary ``float32`` dot raster on the full grid."""
    pts = poisson_disc(score, allow, spacing, budget)
    dots = np.zeros(shape, np.float32)
    if len(pts):
        dots[pts[:, 0], pts[:, 1]] = 1.0
    return dots
