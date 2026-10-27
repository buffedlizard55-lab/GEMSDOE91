"""Shared parallel-run duplicate instruments. Missing evidence is never a pass.

Full-footprint exact ranks (no subsampling) and literal positive support. A soft
registry raster is NOT thresholded at .5 and a dense one gets no exemption.
"""
import numpy as np
from scipy.stats import rankdata
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


class SurfaceProbe:
    """Cache candidate ranks once; exactly equivalent to scipy Spearman.

    Binary-reference closed form avoids re-sorting millions of tied zeros.
    This changes cost, not the footprint, tolerance, or gate.
    """
    def __init__(self, candidate, footprint):
        a, _, self.mask = _arrays(candidate, candidate, footprint)
        self.shape = a.shape
        x = a[self.mask]
        self.valid = len(x) > 1 and x.max() != x.min()
        self.centered = rankdata(x, method='average') - (len(x) + 1) / 2
        self.norm = float(np.linalg.norm(self.centered))

    def compare(self, reference):
        b = np.asarray(reference)
        if b.shape != self.shape:
            raise ValueError('registry grid mismatch')
        y = b[self.mask]
        if not np.isfinite(y).all():
            raise ValueError('nonfinite registry values inside footprint')
        if not self.valid or y.max() == y.min():
            return {'status': 'UNVERIFIED', 'rank_correlation': None,
                    'reason': 'constant or insufficient surface'}
        if np.isin(y, [0, 1]).all():
            ones = y == 1
            n, k = len(y), int(ones.sum())
            rho = float(self.centered[ones].sum() / (self.norm * np.sqrt(k * (n-k) / n)))
        else:
            ry = rankdata(y, method='average') - (len(y) + 1) / 2
            rho = float(np.dot(self.centered, ry) / (self.norm * np.linalg.norm(ry)))
        # Roundoff may put an otherwise exact identity a few ulps outside [-1,1].
        rho = float(np.clip(rho, -1.0, 1.0))
        # Readiness and experiment reports require |rho| <= 0.90.  Checking
        # only positive rho incorrectly cleared a perfectly inverted surface.
        return {'status': 'DUPLICATE' if abs(rho) > .90 else 'PASS', 'rank_correlation': rho}


def combine_final_checks(rank_result, dot_result):
    """Combine both required final-dot checks without overwriting a failure.

    Missing, malformed, or unverified results are never a pass. A duplicate
    witness wins over an unverified second instrument so callers stop at once.
    """
    rank_status = rank_result.get('status') if isinstance(rank_result, dict) else None
    dot_status = dot_result.get('status') if isinstance(dot_result, dict) else None
    if 'DUPLICATE' in (rank_status, dot_status):
        return 'DUPLICATE'
    if rank_status == 'PASS' and dot_status == 'PASS':
        return 'PASS'
    return 'UNVERIFIED'


def surface_check(candidate, reference, footprint):
    a, b, mask = _arrays(candidate, reference, footprint)
    return SurfaceProbe(a, mask).compare(b)


def check_final_pair(probe, candidate, reference, footprint):
    """Run both final instruments independently; an error cannot mask a stop."""
    try:
        rank = probe.compare(reference)
    except ValueError as exc:
        rank = {'status': 'UNVERIFIED', 'reason': str(exc)}
    try:
        dots = dot_check(candidate, reference, footprint)
    except ValueError as exc:
        dots = {'status': 'UNVERIFIED', 'reason': str(exc)}
    return rank, dots, combine_final_checks(rank, dots)


def dot_check(candidate, reference, footprint):
    a, b, mask = _arrays(candidate, reference, footprint)
    if not np.isin(a[mask], [0, 1]).all():
        raise ValueError('candidate dot mask must be binary')
    if (b[mask] < 0).any() or (b[mask] > 1).any():
        raise ValueError('registry support must be in [0,1]')
    p, q = np.argwhere((a > 0) & mask), np.argwhere((b > 0) & mask)
    if not len(p) or not len(q):
        return {'status': 'UNVERIFIED', 'overlap_within_3px': None,
                'reason': 'empty candidate or registry support'}
    # EDT avoids a multi-million-node KD tree for dense continuous references.
    if len(q) > 250_000:
        from scipy.ndimage import distance_transform_edt
        distances = distance_transform_edt(~((b > 0) & mask))[p[:, 0], p[:, 1]]
    else:
        distances = cKDTree(q).query(p, k=1)[0]
    overlap = float(np.mean(distances <= 3.0))
    return {'status': 'DUPLICATE' if overlap > .70 else 'PASS',
            'overlap_within_3px': overlap, 'candidate_dots': len(p),
            'registry_dots': len(q)}
