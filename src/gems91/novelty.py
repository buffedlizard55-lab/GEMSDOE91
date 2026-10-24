"""Thin project adapter to the pinned shared uniqueness implementation.

This module adds only fail-closed input/status handling. Rank correlation and
3-pixel directed dot overlap are calculated by ``vendor.gems57.uniqueness``;
there is no second local implementation of either measurement.
"""
from __future__ import annotations

import numpy as np

from vendor.gems57.metric import RADIUS_PX
from vendor.gems57.uniqueness import OVERLAP_LIMIT, RHO_LIMIT, dot_overlap, surface_rho


def _arrays(candidate, reference, footprint):
    a = np.asarray(candidate)
    b = np.asarray(reference)
    mask = np.asarray(footprint)
    if a.ndim != 2 or a.shape != b.shape or a.shape != mask.shape:
        raise ValueError("common 2-D grid required")
    if mask.dtype != np.dtype(bool) or not mask.any():
        raise ValueError("nonempty boolean footprint required")
    if not np.isfinite(a[mask]).all() or not np.isfinite(b[mask]).all():
        raise ValueError("nonfinite values inside footprint")
    return a, b, mask


class SurfaceProbe:
    """Compatibility wrapper that delegates every rank measurement upstream.

    The historical CED registry loop reuses one probe object. Retaining this
    small API adapter avoids changing that runner while keeping the actual
    statistic in the pinned shared ``surface_rho`` implementation.
    """

    def __init__(self, candidate, footprint):
        candidate_array, _, mask = _arrays(candidate, candidate, footprint)
        self.candidate = candidate_array
        self.footprint = mask
        self.shape = candidate_array.shape

    def compare(self, reference):
        reference_array = np.asarray(reference)
        if reference_array.shape != self.shape:
            raise ValueError("registry grid mismatch")
        if not np.isfinite(reference_array[self.footprint]).all():
            raise ValueError("nonfinite values inside footprint")
        value = surface_rho(self.candidate, reference_array, self.footprint)["spearman_full_footprint"]
        if value is None or not np.isfinite(value):
            return {
                "status": "UNVERIFIED",
                "rank_correlation": None,
                "reason": "constant or insufficient surface",
            }
        rho = float(np.clip(value, -1.0, 1.0))
        return {
            "status": "DUPLICATE" if abs(rho) > RHO_LIMIT else "PASS",
            "rank_correlation": rho,
        }

def surface_check(candidate, reference, footprint):
    """Apply the shared exact full-footprint Spearman duplicate threshold."""
    a, b, mask = _arrays(candidate, reference, footprint)
    measurement = surface_rho(a, b, mask)["spearman_full_footprint"]
    if measurement is None or not np.isfinite(measurement):
        return {
            "status": "UNVERIFIED",
            "rank_correlation": None,
            "reason": "constant or insufficient surface",
        }
    rho = float(np.clip(measurement, -1.0, 1.0))
    return {
        "status": "DUPLICATE" if abs(rho) > RHO_LIMIT else "PASS",
        "rank_correlation": rho,
    }


def dot_check(candidate, reference, footprint):
    """Apply the shared literal finite-positive support overlap rule."""
    a, b, mask = _arrays(candidate, reference, footprint)
    if not np.isin(a[mask], [0, 1]).all():
        raise ValueError("candidate dot mask must be binary")
    if (b[mask] < 0).any() or (b[mask] > 1).any():
        raise ValueError("registry support must be in [0,1]")
    candidate_support = np.isfinite(a) & (a > 0) & mask
    reference_support = np.isfinite(b) & (b > 0) & mask
    if not candidate_support.any() or not reference_support.any():
        return {
            "status": "UNVERIFIED",
            "overlap_within_3px": None,
            "reason": "empty candidate or registry support",
        }
    # Mask outside-footprint cells before using the pinned shared routine.
    masked_candidate = np.where(mask, a, 0)
    masked_reference = np.where(mask, b, 0)
    overlap = dot_overlap(masked_candidate, masked_reference, radius_px=RADIUS_PX)
    return {
        "status": "DUPLICATE" if overlap > OVERLAP_LIMIT else "PASS",
        "overlap_within_3px": overlap,
        "candidate_dots": int(candidate_support.sum()),
        "registry_dots": int(reference_support.sum()),
    }
