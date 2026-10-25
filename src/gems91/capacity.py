"""Necessary capacity bound for the literal registry dot-overlap rule.

Not a metric, placement algorithm, novelty certificate, or permission to delete
references. No candidate or labels are used. At most one binary dot per cell.
"""
from __future__ import annotations

RADIUS_PX = 3
OVERLAP_NUMERATOR = 7
OVERLAP_DENOMINATOR = 10


def capacity_bound(footprint, reference_dots, budget: int) -> dict:
    """A witness that can rule out a budget, never establish uniqueness.

    If U eligible cells are farther than 3 px from reference dots, at least
    max(0, N-U) of N candidate dots overlap. Compare integers, not rounded
    percentages, to respect the strictly-greater-than 70% stopping rule.
    The full footprint is deliberately generous: catalogue masking and spacing
    can only reduce capacity, so impossibility here also implies it there.

    NumPy/SciPy are imported lazily so command-line preflight can report missing
    runtime dependencies as machine-readable BLOCKED output instead of crashing
    during module import.
    """
    import numpy as np
    from scipy.ndimage import distance_transform_edt

    fp, ref = np.asarray(footprint), np.asarray(reference_dots)
    if fp.dtype != bool or ref.dtype != bool or fp.ndim != 2 or fp.shape != ref.shape:
        raise ValueError('footprint and reference must be equal-shape 2-D boolean masks')
    size = int(fp.sum())
    if not size or type(budget) is not int or not 0 < budget <= size:
        raise ValueError('budget must be a positive integer no greater than footprint capacity')
    # EDT on an all-True array treats implicit exterior sites specially. With
    # zero reference dots the correct distance is infinity everywhere.
    if ref.any():
        uncovered = int((fp & (distance_transform_edt(~ref) > RADIUS_PX)).sum())
    else:
        uncovered = size
    minimum = max(0, budget - uncovered)
    impossible = OVERLAP_DENOMINATOR * minimum > OVERLAP_NUMERATOR * budget
    return {
        'evidence_class': 'GEOMETRIC_CAPACITY_BOUND_NOT_A_SCORE',
        'footprint_pixels': size,
        'reference_dots': int(ref.sum()),
        'uncovered_pixels': uncovered,
        'candidate_budget': budget,
        'minimum_overlapping_dots': minimum,
        'overlap_lower_bound': minimum / budget,
        'radius_px': RADIUS_PX,
        'threshold': OVERLAP_NUMERATOR / OVERLAP_DENOMINATOR,
        'feasible_by_capacity_only': not impossible,
        'largest_budget_by_capacity_only': min(size, OVERLAP_DENOMINATOR * uncovered //
                                               (OVERLAP_DENOMINATOR - OVERLAP_NUMERATOR)),
        'status': 'IMPOSSIBLE_AT_BUDGET' if impossible else 'NOT_RULED_OUT',
        'note': 'Necessary bound only. Not a candidate comparison, score, uniqueness pass or placement guidance.',
    }
