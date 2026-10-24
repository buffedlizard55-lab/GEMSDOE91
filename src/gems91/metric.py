"""Compatibility adapter to the pinned shared template metric.

The former local implementation summed contributions at each truth pixel. That
was wrong: truth credit is a MAX over predicted pixels, not a sum. It could
exceed one and invalidate legacy proxy comparisons (IR-91-37). New experiments
use vendor.gems57.evaluate_holdout directly. This adapter keeps legacy APIs
without maintaining a second/private scoring implementation.

These are local HOLDOUT-DTI arithmetic primitives, not organizer acceptance.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from vendor.gems57 import metric as shared

ALPHA, BETA = shared.ALPHA, shared.BETA
RADIUS_PX, PIXEL_M = shared.RADIUS_PX, shared.PIXEL_M


def triangular_kernel(distance_px, radius_px=RADIUS_PX):
    if not np.isfinite(radius_px) or radius_px <= 0:
        raise ValueError('positive finite radius required')
    return shared.kernel(distance_px, radius_px)


def _offsets(radius_px):
    return [(int(y), int(x), float(k)) for y, x, k in zip(*shared.offsets(radius_px))]


@dataclass(frozen=True)
class DtiParts:
    T: float
    S: float
    M: float
    n_truth: int

    def dti(self, alpha=ALPHA, beta=BETA):
        if self.n_truth == 0 and self.S <= 0:
            raise ValueError('degenerate DTI denominator')
        return shared.dti_from_components(self.T, self.S-self.M, self.n_truth-self.T, alpha, beta)


def components(pred, truth, radius_px=RADIUS_PX, extra_mass=None):
    if radius_px != RADIUS_PX:
        raise ValueError('the shared pinned evaluator uses the fixed 300 m radius')
    p, t = np.asarray(pred, dtype=np.float64), np.asarray(truth, dtype=bool)
    if p.ndim != 2 or p.shape != t.shape:
        raise ValueError('matching 2-D grids required')
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('predictions must be finite in [0,1]')
    if not t.any(): raise ValueError('truth set is empty; DTI undefined')
    if extra_mass is not None:
        y, x, value = extra_mass
        if not (0 <= y < p.shape[0] and 0 <= x < p.shape[1]):
            raise ValueError('extra-mass pixel outside grid')
        p = p.copy(); p[y, x] += value
    credit, q, _ = shared.max_cover(p, t)
    return DtiParts(T=float(credit.sum()), S=float(p.sum()),
                    M=float((p*q).sum()), n_truth=int(t.sum()))


def _shift(a, dr, dc):
    out = np.zeros_like(a)
    h, w = a.shape
    out[max(0, dr):min(h, h+dr), max(0, dc):min(w, w+dc)] = a[max(0, -dr):min(h, h-dr), max(0, -dc):min(w, w-dc)]
    return out


def dti(pred, truth, radius_px=RADIUS_PX, alpha=ALPHA, beta=BETA):
    return components(pred, truth, radius_px).dti(alpha, beta)


def marginal_gain(pred, truth, row, col, p=1.0, radius_px=RADIUS_PX, alpha=ALPHA, beta=BETA):
    before = components(pred, truth, radius_px)
    after = components(pred, truth, radius_px, extra_mass=(int(row), int(col), float(p)))
    return after.dti(alpha, beta) - before.dti(alpha, beta)


def isolated_truth_pays(credit, dti_value, alpha=ALPHA):
    """Nonredundant isolated-truth rule of thumb, not a general gain oracle."""
    return credit > alpha * dti_value
