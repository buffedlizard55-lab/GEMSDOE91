"""Parallel-run duplicate instruments. Missing evidence is never a pass.

Call surface_check before placement and dot_check afterwards for EVERY registry
raster on a common grid. These checks establish measured similarity, not legal
permission to submit or scientific novelty. No subsampling is used.
"""
import numpy as np
from scipy.stats import spearmanr
from scipy.spatial import cKDTree


def _arrays(candidate, reference, footprint):
    a, b, mask = np.asarray(candidate), np.asarray(reference), np.asarray(footprint)
    if a.ndim != 2 or a.shape != b.shape or a.shape != mask.shape:
        raise ValueError('common 2-D grid required')
    if mask.dtype != np.bool_ or not mask.any():
        raise ValueError('nonempty boolean footprint required')
    if not np.isfinite(a[mask]).all() or not np.isfinite(b[mask]).all():
        raise ValueError('nonfinite values inside footprint')
    return a, b, mask


def surface_check(candidate, reference, footprint):
    a, b, mask = _arrays(candidate, reference, footprint)
    x, y = a[mask], b[mask]
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return {'status': 'UNVERIFIED', 'rank_correlation': None,
                'reason': 'constant or insufficient surface'}
    rho = float(spearmanr(x, y).statistic)
    return {'status': 'DUPLICATE' if rho > 0.90 else 'PASS',
            'rank_correlation': rho}


def dot_check(candidate, reference, footprint):
    a, b, mask = _arrays(candidate, reference, footprint)
    if not np.isin(a[mask], [0, 1]).all() or not np.isin(b[mask], [0, 1]).all():
        raise ValueError('dot masks must be binary')
    p, q = np.argwhere((a > 0) & mask), np.argwhere((b > 0) & mask)
    if not len(p) or not len(q):
        return {'status': 'UNVERIFIED', 'overlap_within_3px': None,
                'reason': 'empty candidate or registry dots'}
    distances = cKDTree(q).query(p, k=1)[0]
    overlap = float(np.mean(distances <= 3.0))
    return {'status': 'DUPLICATE' if overlap > 0.70 else 'PASS',
            'overlap_within_3px': overlap, 'candidate_dots': len(p),
            'registry_dots': len(q)}
