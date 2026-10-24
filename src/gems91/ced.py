"""CED91: parent-free two-scale cross-potential-field centroid displacement.

No catalogue or submission raster is accepted by feature construction. The
statistics are geological hypotheses, not estimates of fault dip or depth.
"""
from __future__ import annotations
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

VERSION = 'ced91-v1'
SCALES = (2.0, 6.0)
CENTROID_SIGMA = 3.0
DOT_BUDGET = 32_000


def percentiles(a, footprint):
    """Exact average-rank ECDF; constant features have percentile one half."""
    a, fp = np.asarray(a), np.asarray(footprint, bool)
    if a.ndim != 2 or a.shape != fp.shape or not fp.any():
        raise ValueError('nonempty matching 2-D footprint required')
    if not np.isfinite(a[fp]).all():
        raise ValueError('nonfinite input within footprint')
    out = np.zeros(a.shape, np.float32)
    out[fp] = (rankdata(a[fp], method='average') / (int(fp.sum()) + 1)).astype(np.float32)
    return out


def fill_input(values, footprint):
    """Nearest observed pixel fill for derivative support, without reading labels.

    Sentinel pixels are not measurements. Coverage statistics are reported by
    the caller; this helper refuses a band with no usable footprint data.
    """
    a = np.asarray(values, dtype=np.float32)
    fp = np.asarray(footprint, bool)
    if a.ndim != 2 or fp.shape != a.shape:
        raise ValueError('input/footprint shape mismatch')
    good = np.isfinite(a) & (a > -1e30) & fp
    if not good.any():
        raise ValueError('no usable band data')
    indexes = ndi.distance_transform_edt(~good, return_distances=False, return_indices=True)
    result = a[tuple(indexes)]
    # Scale by robust spread for numeric stability. This is label-blind.
    q25, med, q75 = np.quantile(result[fp], [.25, .5, .75])
    scale = float(q75 - q25)
    if scale <= 0:
        scale = float(np.std(result[fp])) or 1.0
    result = ((result - np.float32(med)) / np.float32(scale)).astype(np.float32)
    if not np.isfinite(result).all():
        raise ValueError('input normalization produced nonfinite values')
    return result


def edge_at_scale(a, sigma):
    gx = ndi.gaussian_filter(a, sigma, order=(0, 1), mode='nearest')
    gy = ndi.gaussian_filter(a, sigma, order=(1, 0), mode='nearest')
    strength = np.hypot(gx, gy)
    return strength, gx, gy


def centroid_shift(strength, sigma=CENTROID_SIGMA):
    """Gaussian moment identity: local edge centroid minus pixel center.

    For W(r)=edge_strength(r)*Gaussian(r-center), E[r-center] equals
    sigma^2*gradient(log(Gaussian*edge_strength)). Units are pixels.
    """
    smooth = ndi.gaussian_filter(strength, sigma, mode='nearest')
    floor = max(float(smooth.max()) * 1e-7, 1e-12)
    sx = ndi.gaussian_filter(strength, sigma, order=(0, 1), mode='nearest')
    sy = ndi.gaussian_filter(strength, sigma, order=(1, 0), mode='nearest')
    den = np.maximum(smooth, floor)
    return (sigma * sigma * sx / den).astype(np.float32), (sigma * sigma * sy / den).astype(np.float32)


def features(magnetic, gravity, footprint):
    """Return all surface inputs for canary testing; no fitted parameters."""
    fp = np.asarray(footprint, bool)
    m, g = fill_input(magnetic, fp), fill_input(gravity, fp)
    ranks_m, ranks_g, alignment, displacements = [], [], [], []
    for sigma in SCALES:
        ms, mx, my = edge_at_scale(m, sigma)
        gs, gx, gy = edge_at_scale(g, sigma)
        ranks_m.append(percentiles(ms, fp)); ranks_g.append(percentiles(gs, fp))
        denominator = np.maximum(ms * gs, 1e-12)
        align = np.minimum(np.abs((mx * gx + my * gy) / denominator), 1.0)
        alignment.append(align.astype(np.float32))
        mcx, mcy = centroid_shift(ms)
        gcx, gcy = centroid_shift(gs)
        disp = ((gcx - mcx) * mx + (gcy - mcy) * my) / np.maximum(ms, 1e-12)
        displacements.append(disp.astype(np.float32))
    mp = np.sqrt(ranks_m[0] * ranks_m[1])
    gp = np.sqrt(ranks_g[0] * ranks_g[1])
    axial = np.sqrt(alignment[0] * alignment[1])
    stable = np.exp(-np.abs(displacements[0] - displacements[1]) / 2.0)
    surface = np.sqrt(mp * gp) * axial * stable
    result = dict(raw_magnetic=percentiles(m, fp), raw_gravity=percentiles(g, fp),
                  magnetic_persistence=mp, gravity_persistence=gp,
                  axial_alignment=axial, displacement_consistency=stable,
                  signed_displacement_fine=displacements[0],
                  signed_displacement_coarse=displacements[1], surface=surface)
    for name, field in result.items():
        field[~fp] = 0
        if not np.isfinite(field).all():
            raise ValueError(f'{name}: nonfinite feature')
        result[name] = field.astype(np.float32, copy=False)
    return result


def auc_canary(field, truth, active):
    """Exact AUROC on held positives vs catalogue-zero proxies, not absence labels."""
    a, t, mask = np.asarray(field), np.asarray(truth, bool), np.asarray(active, bool)
    if a.shape != t.shape or a.shape != mask.shape:
        raise ValueError('canary grid mismatch')
    values, target = a[mask], t[mask]
    if not np.isfinite(values).all():
        raise ValueError('nonfinite canary feature')
    n_pos, n_neg = int(target.sum()), int((~target).sum())
    if not n_pos or not n_neg:
        raise ValueError('canary requires positives and negative proxies')
    ranks = rankdata(values, method='average')
    auc = float((ranks[target].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))
    symmetric = max(auc, 1.0 - auc)
    return dict(evidence_class='HOLDOUT-DTI', statistic='feature-alone AUROC (not DTI)',
                auc=auc, symmetric_auc=symmetric, withheld_positive_pixels=n_pos,
                negative_proxy_pixels=n_neg, threshold=.90,
                status='LEAKAGE_SUSPECTED' if symmetric > .90 else 'PASS',
                caveat='Catalogue-zero pixels are unlabeled proxies, not verified absence; passing is not proof of no leakage.')


def place(surface, eligible, budget, radius=3.0):
    """Deterministic greedy dots separated by strictly more than radius pixels.

    Geometry and budget must be label-blind apart from exact visible masking.
    Stable tie-breaking is ascending row-major index, never random jitter.
    """
    s, e = np.asarray(surface), np.asarray(eligible, bool)
    if s.ndim != 2 or s.shape != e.shape or not np.isfinite(s[e]).all():
        raise ValueError('finite surface on matching 2-D eligible mask required')
    if not isinstance(budget, (int, np.integer)) or budget < 0 or radius <= 0:
        raise ValueError('nonnegative integer budget and positive radius required')
    out = np.zeros(s.shape, bool)
    if budget == 0: return out
    ids = np.flatnonzero(e & (s > 0))
    order = ids[np.argsort(-s.ravel()[ids], kind='stable')]
    blocked = ~e.copy()
    h, w = s.shape
    span = int(np.ceil(radius))
    yy, xx = np.mgrid[-span:span+1, -span:span+1]
    offsets = np.c_[yy[(yy*yy + xx*xx) <= radius*radius], xx[(yy*yy + xx*xx) <= radius*radius]]
    count = 0
    for index in order:
        y, x = divmod(int(index), w)
        if blocked[y, x]: continue
        out[y, x] = True; count += 1
        dy, dx = y + offsets[:, 0], x + offsets[:, 1]
        good = (dy >= 0) & (dy < h) & (dx >= 0) & (dx < w)
        blocked[dy[good], dx[good]] = True
        if count == budget: break
    if count != budget:
        raise ValueError(f'Placement capacity {count} is below requested budget {budget}; no silent budget change')
    return out
