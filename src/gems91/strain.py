"""Geodetic-strain km-scale priors from the pinned GeoDAWN feature stack.

Session 8 implements the GEODETIC-STRAIN CONCENTRATION axis that merged
SLOT_PLAN.md pre-proposed (Sessions 5-7) but never built.  This module only
*derives the prior fields*; the dot moves are made by the fleet's existing
CONCENTRATION builder (`tools.run_concentration.build_concentration`), so the
strain arms differ from the GDR thermal arms in prior source alone (plus the
IR-91-27 collar-donor quarantine, IR-91-36).

Bands (descriptions read from the pinned raster, `training_features`,
sha256 4371c82e...3bc5 in `registry/data_manifest.json`):

    band 4  geod_2ndinv      second invariant of the strain-rate tensor
    band 7  geod_shearrate   shear strain rate
    band 8  geod_dilaterate  dilatation (areal) strain rate, signed

Design rules, each removing a degree of freedom (frozen in
`registry/strain_concentration_preregistration.json` before any build):

1. **Sentinel fill, never deletion.**  Each band carries the raster nodata
   Sentinel (-3.4028e38) on 3,061 footprint boundary cells.  Those cells are
   filled from the nearest valid footprint cell (EDT indices), exactly the
   RELIEF session's treatment of the same cells, and the filled count is
   reported.  Averaging the Sentinel into a block prior would be a silent
   data-corruption bug, not a modelling choice.
2. **Percentile ranks, average ties.**  The three bands have unrelated units
   and band 7 is exactly 0.0 on 18.9% of the footprint, so each band is mapped
   to its average-tie percentile rank over footprint cells before any
   combination.  No threshold, no fitted weight: the strain prior is the
   equal-weight mean of the band-4 and band-7 ranks.
3. **No lineage multiplier.**  The SLOT_PLAN proposal's falsifier sentence
   mentions `geod_2ndinv x S_struct`.  S_struct is 60% lineage support, so
   multiplying by it would make the "independent prior" partly a re-statement
   of the parent (the IR-91-07 failure).  The prior here is geodetic bands
   only; see IR-91-37.
4. **Digest-pinned.**  Each derived prior is identified by
   `gems91.prior.array_digest` (sha256 of shape + float32 payload), recorded
   in `registry/derived_priors.json`; the builder refuses a mismatch.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

#: Raster nodata Sentinel in the pinned feature stack is -3.4028e38; anything
#: at or below this threshold inside the footprint is missing, not data.
SENTINEL_MAX = -1e30

BAND_2NDINV = 4
BAND_SHEARRATE = 7
BAND_DILATERATE = 8


def fill_sentinel(band: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, int]:
    """Nearest-valid-cell fill of Sentinel/non-finite cells inside the footprint.

    Returns (filled float64 copy, n_filled).  Cells outside the footprint are
    returned unchanged; the caller masks them.  A band with no valid footprint
    cell at all is refused rather than filled from nothing.
    """
    band = np.asarray(band, dtype=np.float64).copy()
    footprint = np.asarray(footprint, dtype=bool)
    if band.shape != footprint.shape:
        raise ValueError("band and footprint must share the grid")
    valid = footprint & np.isfinite(band) & (band > SENTINEL_MAX)
    if not valid.any():
        raise ValueError("band has no valid footprint cells: prior undefined")
    bad = footprint & ~valid
    n = int(bad.sum())
    if n:
        # distance_transform_edt measures distance to the zero cells; zeros at
        # valid cells => return_indices points each bad cell at its nearest
        # valid one.
        idx = ndi.distance_transform_edt(~valid, return_indices=True)[1]
        band[bad] = band[idx[0][bad], idx[1][bad]]
    return band, n


def percentile_rank(band: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Average-tie percentile rank over footprint cells, in [0, 1]; NaN outside.

    Exact (unique-value) ranks, deterministic under ties: a value shared by
    k cells receives the mean of the ranks those cells would occupy, so the
    18.9%-zero shear band's zeros all sit at one low percentile rather than
    being spread by sort order.
    """
    band = np.asarray(band, dtype=np.float64)
    footprint = np.asarray(footprint, dtype=bool)
    vals = band[footprint]
    if vals.size == 0:
        raise ValueError("empty footprint")
    if not np.isfinite(vals).all():
        raise ValueError("percentile_rank needs filled bands (see fill_sentinel)")
    uniq, inverse, counts = np.unique(vals, return_inverse=True, return_counts=True)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]]).astype(np.float64)
    avg_rank0 = starts + (counts - 1) / 2.0          # 0-based average rank
    pct_vals = avg_rank0 / max(1, vals.size - 1)
    out = np.full(band.shape, np.nan, dtype=np.float64)
    out[footprint] = pct_vals[inverse]
    return out


def band_prior(band: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    """One band -> (percentile-rank prior (float32, NaN outside), fill stats)."""
    filled, n_filled = fill_sentinel(band, footprint)
    inside = filled[np.asarray(footprint, dtype=bool)]
    stats = {
        "n_sentinel_filled": n_filled,
        "raw_min_after_fill": round(float(inside.min()), 6),
        "raw_median_after_fill": round(float(np.median(inside)), 6),
        "raw_max_after_fill": round(float(inside.max()), 6),
    }
    return percentile_rank(filled, footprint).astype(np.float32), stats


def strain_prior(
    band_2ndinv: np.ndarray, band_shearrate: np.ndarray, footprint: np.ndarray
) -> tuple[np.ndarray, dict]:
    """Equal-weight mean of the band-4 and band-7 percentile ranks."""
    p4, s4 = band_prior(band_2ndinv, footprint)
    p7, s7 = band_prior(band_shearrate, footprint)
    combo = (0.5 * np.nan_to_num(p4, nan=0.0) + 0.5 * np.nan_to_num(p7, nan=0.0)).astype(np.float32)
    combo[~np.asarray(footprint, dtype=bool)] = np.nan
    return combo, {"geod_2ndinv": s4, "geod_shearrate": s7, "weights": [0.5, 0.5]}


def dilatation_prior(band_dilaterate: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    """Percentile rank of band 8 alone; high percentile = most positive value.

    Sign convention (assumption, recorded in the preregistration): larger raw
    dilatation = areal expansion (extension), per the pinned band description
    "rate of volumetric strain (expansion/contraction)".
    """
    p8, s8 = band_prior(band_dilaterate, footprint)
    return p8, {"geod_dilaterate": s8, "sign": "high percentile = most positive (expansion)"}
