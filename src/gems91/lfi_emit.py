"""Greedy expected-DTI emission on an LFI truth-density map, with hard per-raster uniqueness caps.

Marginal test (exact algebra of the official metric, see vendor/gems57/metric.py):
adding one dot x with expected new truth credit dT(x) and expected own credit m(x) raises DTI iff

    dT (1 - alpha*DTI) > alpha*DTI*(f - m)

where f is the public-chunk mass fraction (FP is only charged inside public chunks).
dT(x) = sum_o q(x+o) * max(0, k_o - cov(x+o)) is the facility-location (submodular) coverage gain.

Uniqueness is a *constraint*, not an afterthought: for every binding reference raster R the fraction of our
dots lying within 3 px of any positive pixel of R is kept <= cap at every acceptance step.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from .lfi import ALPHA, BETA, OFFSETS, coverage, mu


def _shift_add(acc, arr, dy, dx):
    """acc[y, x] += arr[y+dy, x+dx] (zero outside)."""
    h, w = arr.shape
    ys, yd = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
    xs, xd = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
    acc[yd, xd] += arr[ys, xs]


def gain_map(q, cov):
    g = np.zeros_like(q)
    for dy, dx, k in OFFSETS:
        term = q * np.maximum(np.float32(k) - cov, 0.0)
        _shift_add(g, term, dy, dx)
    return g


def greedy(q, f, K, allowed, halo_bits, n_refs, cap=0.65, per_round=4000, max_rounds=80, nms=5,
           lam0=0.15, n_floor=25_000, log=print):
    """Return (dots bool array, trace list). ``halo_bits`` uint32: bit r set if pixel within 3 px of ref r."""
    q = q.astype(np.float32)
    m = (f * mu(q.astype(np.float64) / f)).astype(np.float32)
    dots = np.zeros(q.shape, bool)
    cov = np.zeros(q.shape, np.float32)
    counts = np.zeros(n_refs, np.int64)
    n = 0
    T = M = 0.0
    lam = lam0
    trace = []
    for rnd in range(max_rounds):
        g = gain_map(q, cov)
        v = g * (1 - ALPHA * lam) - ALPHA * lam * (f - m)
        v[~allowed | dots] = -np.inf
        peak = (v == ndi.maximum_filter(v, size=nms)) & (v > 0)
        ys, xs = np.nonzero(peak)
        if ys.size == 0:
            break
        order = np.argsort(-v[ys, xs])
        ys, xs = ys[order], xs[order]
        acc = 0
        for y, x in zip(ys, xs):
            if acc >= per_round:
                break
            bits = int(halo_bits[y, x])
            if bits:
                ok = True
                for r in range(n_refs):
                    if bits >> r & 1 and (counts[r] + 1) > cap * max(n + 1, n_floor):
                        ok = False
                        break
                if not ok:
                    continue
                for r in range(n_refs):
                    if bits >> r & 1:
                        counts[r] += 1
            dots[y, x] = True
            n += 1
            acc += 1
        cov = coverage(dots.astype(np.float32))
        T = float((q * cov).sum())
        M = float(m[dots].sum())
        lam_new = T / (ALPHA * T + ALPHA * max(f * n - M, 0) + BETA * K)
        trace.append(dict(round=rnd, accepted=acc, n=n, T=T, M=M, dti_model=lam_new,
                          max_ref_frac=float(counts.max() / max(n, 1))))
        log(f"round {rnd:2d} +{acc:5d} n={n:6d} model-DTI={lam_new:.4f} max-ref-frac={counts.max()/max(n,1):.3f}")
        lam = lam_new
        if acc == 0:
            break
    return dots, trace, counts


def repair(dots, q, f, halo_bits, n_refs, cap, log=print):
    """Exact post-hoc enforcement: while any reference holds > cap of our dots, delete that reference's
    lowest-marginal-value dot (value = own coverage contribution, recomputed in blocks). Returns dots."""
    dots = dots.copy()
    for it in range(200):
        ys, xs = np.nonzero(dots)
        n = ys.size
        bits = halo_bits[ys, xs]
        counts = np.array([int(((bits >> np.uint32(r)) & 1).sum()) for r in range(n_refs)])
        worst = int(np.argmax(counts / max(n, 1)))
        if counts[worst] <= cap * n:
            log(f"repair: done after {it} passes; n={n}; max frac={counts.max()/n:.4f}")
            return dots
        # number to delete from the worst ref so that c - d <= cap (n - d)  ->  d >= (c - cap n)/(1 - cap)
        need = int(np.ceil((counts[worst] - cap * n) / (1 - cap))) + 1
        inref = ((bits >> np.uint32(worst)) & 1).astype(bool)
        # value proxy: q-weighted kernel mass under the dot (lower = less useful)
        val = np.zeros(n, np.float64)
        for dy, dx, k in OFFSETS:
            yy = np.clip(ys + dy, 0, q.shape[0] - 1)
            xx = np.clip(xs + dx, 0, q.shape[1] - 1)
            val += k * q[yy, xx]
        cand = np.flatnonzero(inref)
        drop = cand[np.argsort(val[cand])[:need]]
        dots[ys[drop], xs[drop]] = False
    raise RuntimeError("repair did not converge")


def ranked_pool(q, f, allowed, lam=0.10, per_round=6000, max_rounds=60, nms=5, log=print):
    """Coverage-aware greedy at a fixed bar ``lam``; returns dots in acceptance order (ys, xs, value)."""
    q = q.astype(np.float32)
    m = (f * mu(q.astype(np.float64) / f)).astype(np.float32)
    dots = np.zeros(q.shape, bool)
    cov = np.zeros(q.shape, np.float32)
    out_y, out_x, out_v = [], [], []
    for rnd in range(max_rounds):
        g = gain_map(q, cov)
        v = g * (1 - ALPHA * lam) - ALPHA * lam * (f - m)
        v[~allowed | dots] = -np.inf
        peak = (v == ndi.maximum_filter(v, size=nms)) & (v > 0)
        ys, xs = np.nonzero(peak)
        if ys.size == 0:
            break
        o = np.argsort(-v[ys, xs])[:per_round]
        ys, xs = ys[o], xs[o]
        dots[ys, xs] = True
        out_y.append(ys); out_x.append(xs); out_v.append(v[ys, xs])
        cov = coverage(dots.astype(np.float32))
        log(f"  pool round {rnd:2d} +{ys.size:5d} total={int(dots.sum())}")
    if not out_y:
        return np.zeros(0, int), np.zeros(0, int), np.zeros(0)
    return np.concatenate(out_y), np.concatenate(out_x), np.concatenate(out_v)


def model_dti(dots, q, f, K):
    cov = coverage(dots.astype(np.float32))
    T = float((q * cov).sum())
    m = f * mu(q[dots].astype(np.float64) / f)
    n = int(dots.sum())
    return T / (ALPHA * T + ALPHA * max(f * n - float(m.sum()), 0.0) + BETA * K)
