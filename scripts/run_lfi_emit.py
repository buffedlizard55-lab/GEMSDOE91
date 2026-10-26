#!/usr/bin/env python3
"""LFI emission + surrogate gate.

    python scripts/run_lfi_emit.py emit  --ridge 10 --cap 0.65     # -> work/lfi/cand_dots.npy
    python scripts/run_lfi_emit.py gate  --boot 60                  # paired surrogate projection vs R0

Everything printed here is MODEL / PROJECTION (fitted to USER-REPORTED scores), never a score.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]
from gems91 import lfi as L, lfi_emit as E  # noqa: E402
import run_lfi as R  # noqa: E402

WORK = ROOT / "work/lfi"
R0 = ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif"
BINDING_NAMES = [
    "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros",
    "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", "h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan",
    "h38-1-hf-euler-r30-r1-20261003-56a9f473edc7-nan", "h32-1-prethin-tip-euler-d2-8-20261003-31e35eee884e-nan",
    "h33d-analog-tip-stepover-r30-20261004-cb490425926e", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan",
    "wormrank-d28-20261003-59dcaf6dd11d-zeros", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan",
    "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan",
    "h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-nan",
    "h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-nan",
    "h16-1-topo-geophys-baseline-ridges-20260930-df20f65e-nan",
    "h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-20260930-be0e8f6b-nan",
    "h20-5-continuous-pu-proxy-unverified-20260930-824ce73a-nan",
]


def qmap(theta, f, bins, Lm, cat):
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    qb = np.exp(np.clip(X @ theta, -30, 5))
    q = np.where(bins >= 0, qb[np.maximum(bins, 0)], 0.0).astype(np.float32)
    q[cat] = 0.0
    return q, float((qb * 0 + qb) @ np.bincount(bins[(bins >= 0) & ~cat], minlength=len(qb)))


def binding_refs(meta, fp):
    rows = {r["name"]: r for r in meta["rows"] if r.get("used")}
    names = BINDING_NAMES + [c["name"] for c in meta["meta"]["consensus_anchors"]]
    halo = np.zeros(fp.shape, np.uint32)
    used = []
    for i, nm in enumerate(n for n in names if n in rows):
        p, _ = R.read_pred(ROOT / rows[nm]["local"], fp)
        halo |= ((L.dist_px(p > 0) <= 3.0).astype(np.uint32) << np.uint32(len(used)))
        used.append(dict(bit=len(used), name=nm, site=rows[nm]["site"], local=rows[nm]["local"]))
    return halo, used


def cmd_emit(ridge, cap, collar):
    fp, cat, net = R.base()
    bins = np.load(WORK / "bins.npy")
    z = np.load(WORK / "agg.npz")
    meta = json.loads((WORK / "anchors.json").read_text())
    th = np.load(WORK / f"fit_r{ridge}_fNone_theta.npy")
    theta, f = th[:-1], float(th[-1])
    q, K = qmap(theta, f, bins, z["L"], cat)
    dcat = L.dist_px(cat)
    allowed = fp & ~cat & (dcat > collar)
    halo, refs = binding_refs(meta, fp)
    print(f"f={f:.3f} K={K:.0f} binding refs={len(refs)} allowed px={int(allowed.sum())}")
    dots, trace, counts = E.greedy(q, f, K, allowed, halo, len(refs), cap=cap)
    dots = E.repair(dots, q, f, halo, len(refs), cap)
    ys, xs = np.nonzero(dots)
    counts = np.array([int(((halo[ys, xs] >> np.uint32(r)) & 1).sum()) for r in range(len(refs))])
    np.save(WORK / "cand_dots.npy", dots)
    np.save(WORK / "cand_q.npy", q)
    (WORK / "emit.json").write_text(json.dumps(dict(
        ridge=ridge, cap=cap, collar_px=collar, f=f, K_model=K, n_dots=int(dots.sum()), trace=trace,
        binding_refs=[dict(**r, frac=float(counts[r["bit"]] / max(dots.sum(), 1))) for r in refs]), indent=1))
    print(f"emitted {int(dots.sum())} dots")


FAMILY_BITS = 16   # the first 16 binding refs are the h19-5 ridge-network family (R0 lineage)


def extra_refs(thresh):
    """Sparse (<= 3x candidate dots) registry/sibling-sweep rasters whose measured literal 3-px overlap with the
    previous candidate exceeded ``thresh``: added as binding uniqueness constraints (pass-2 fix, S20)."""
    import hashlib
    out, seen = [], set()
    for f in ("docs/lfi/registry-check.json", "docs/lfi/sibling-check.json"):
        p = ROOT / f
        if not p.exists():
            continue
        for r in json.loads(p.read_text())["rows"]:
            if r["dense"] or r["within_3px_literal"] < thresh:
                continue
            h = hashlib.sha256((ROOT / r["raster"]).read_bytes()).hexdigest()
            if h not in seen:
                seen.add(h)
                out.append(r["raster"])
    return out


def cmd_emit2(ridge, cap, collar, extra_thresh=None, n_lo=15_000, n_hi=70_000):
    fp, cat, net = R.base()
    bins = np.load(WORK / "bins.npy")
    z = np.load(WORK / "agg.npz")
    meta = json.loads((WORK / "anchors.json").read_text())
    th = np.load(WORK / f"fit_r{ridge}_fNone_theta.npy")
    theta, f = th[:-1], float(th[-1])
    q, K = qmap(theta, f, bins, z["L"], cat)
    dcat = L.dist_px(cat)
    allowed = fp & ~cat & (dcat > collar)
    halo, refs = binding_refs(meta, fp)
    fam = (halo & np.uint32((1 << FAMILY_BITS) - 1)) > 0
    print(f"f={f:.3f} K={K:.0f} family-halo px={int((fam & allowed).sum())} free px={int((~fam & allowed).sum())}")
    print("ranking in-halo pool H"); hy, hx, hv = E.ranked_pool(q, f, allowed & fam)
    print("ranking off-halo pool F"); fy, fx, fv = E.ranked_pool(q, f, allowed & ~fam)
    print(f"pool sizes H={hy.size} F={fx.size}")
    cy = np.concatenate([hy, fy]); cx = np.concatenate([hx, fx]); cv = np.concatenate([hv, fv])
    order = np.argsort(-cv, kind="stable")
    cy, cx = cy[order], cx[order]
    cbits = halo[cy, cx]
    nref = len(refs)
    bitmat = ((cbits[:, None] >> np.arange(nref, dtype=np.uint32)[None, :]) & 1).astype(bool)
    extra = extra_refs(extra_thresh) if extra_thresh is not None else []
    cols = []
    for path in extra:
        p, _ = R.read_pred(ROOT / path, fp)
        cols.append((L.dist_px(p > 0) <= 3.000001)[cy, cx])
    if cols:
        bitmat = np.hstack([bitmat, np.stack(cols, 1)])
        refs = refs + [dict(bit=nref + i, name=Path(pth).stem, site="extra", local=pth) for i, pth in enumerate(extra)]
        nref = len(refs)
    print(f"binding references: {nref} ({len(extra)} extra from registry/sibling checks)", flush=True)

    def fill(n_target):
        lim = cap * n_target
        counts = np.zeros(nref, np.int64)
        take = np.zeros(cy.size, bool)
        k = 0
        for i in range(cy.size):
            b = bitmat[i]
            if b.any() and np.any(counts[b] + 1 > lim):
                continue
            counts[b] += 1
            take[i] = True
            k += 1
            if k >= n_target:
                break
        d = np.zeros(fp.shape, bool)
        d[cy[take], cx[take]] = True
        return d

    best, rows = None, []
    def fill_exact(n_target):
        """Fixed point: refill with target = achieved count until every cap holds against the REAL n."""
        for _ in range(50):
            d = fill(n_target)
            n = int(d.sum())
            if n == 0:
                return d
            if bitmat[d[cy, cx]].sum(0).max() <= cap * n:
                return d
            n_target = n - 1
        return d

    for n in range(n_lo, n_hi + 1, 2_500):
        d = fill_exact(n)
        md = E.model_dti(d, q, f, K)
        rows.append(dict(n_target=n, n=int(d.sum()), model_dti=md))
        print(f"  n_target={n:6d} n={int(d.sum()):6d} model-DTI={md:.4f}", flush=True)
        if best is None or md > best[0]:
            best = (md, d)
    dots = best[1]
    # exact repair over ALL binding columns (pool membership matrix; dots are a subset of the pool)
    sel = dots[cy, cx]
    for it in range(500):
        n = int(sel.sum()); counts = bitmat[sel].sum(0)
        worst = int(np.argmax(counts))
        if counts[worst] <= cap * n:
            print(f"repair: done after {it} passes; n={n}; max frac={counts.max()/n:.4f}"); break
        need = int(np.ceil((counts[worst] - cap * n) / (1 - cap))) + 1
        idx = np.flatnonzero(sel & bitmat[:, worst])
        sel[idx[-need:]] = False      # pool is in descending value order: drop the lowest-valued members
    else:
        raise RuntimeError("repair did not converge")
    dots = np.zeros(fp.shape, bool); dots[cy[sel], cx[sel]] = True
    counts = bitmat[sel].sum(0)
    np.save(WORK / "cand_dots.npy", dots)
    np.save(WORK / "cand_q.npy", q)
    (WORK / "emit.json").write_text(json.dumps(dict(
        method="two-pool", extra_thresh=extra_thresh, ridge=ridge, cap=cap, collar_px=collar, f=f, K_model=K, n_dots=int(dots.sum()),
        model_dti_selected=E.model_dti(dots, q, f, K), size_scan=rows,
        binding_refs=[dict(**r, frac=float(counts[r["bit"]] / max(dots.sum(), 1))) for r in refs]), indent=1))
    print(f"emitted {int(dots.sum())} dots; max binding-ref frac {counts.max()/dots.sum():.4f}")


def cmd_gate(boot, seed=20261026):
    fp, cat, net = R.base()
    bins = np.load(WORK / "bins.npy")
    N, C, A, Lm, obs, used, meta = R.load()
    nb = Lm.shape[0]
    dots = np.load(WORK / "cand_dots.npy").astype(np.float32)
    r0, _ = R.read_pred(R0, fp)
    Nc, Cc = L.aggregate(dots, bins, nb, cat)
    Nr, Cr = L.aggregate(r0, bins, nb, cat)
    X = np.hstack([np.ones((nb, 1)), Lm])
    sites = np.array([r["site"] for r in used])
    us = np.unique(sites)
    rng = np.random.default_rng(seed)
    cons_sites = {c["site"] for c in meta["meta"]["consensus_anchors"]}
    out = {}
    for label, ridge, blind in (("ridge1", 1.0, False), ("ridge10", 10.0, False), ("ridge1_blindcons", 1.0, True)):
        base_mask = np.array([(s not in cons_sites) for s in sites]) if blind else np.ones(len(sites), bool)
        full = L.fit(N[base_mask], C[base_mask], A, Lm, obs[base_mask], ridge=ridge)
        pc, _ = L.predict(full.theta, full.f, X, Nc[None], Cc[None], A)
        pr, _ = L.predict(full.theta, full.f, X, Nr[None], Cr[None], A)
        deltas, cands, r0s = [], [], []
        for b in range(boot):
            pick = rng.choice(us, size=len(us), replace=True)
            w = np.zeros(len(sites))
            for s in pick:
                w[sites == s] += 1.0
            w = w * base_mask
            keep = w > 0
            fi = L.fit(N[keep], C[keep], A, Lm, obs[keep], ridge=ridge, weights=w[keep], theta0=full.theta)
            a, _ = L.predict(fi.theta, fi.f, X, Nc[None], Cc[None], A)
            r, _ = L.predict(fi.theta, fi.f, X, Nr[None], Cr[None], A)
            cands.append(float(a[0])); r0s.append(float(r[0])); deltas.append(float(a[0] - r[0]))
        d = np.array(deltas)
        out[label] = dict(model_cand=float(pc[0]), model_r0=float(pr[0]), delta=float(pc[0] - pr[0]),
                          boot_delta_ci95=[float(np.quantile(d, .025)), float(np.quantile(d, .975))],
                          p_delta_gt0=float((d > 0).mean()), boot=boot,
                          projection_vs_reported_r0=float(0.2778 + pc[0] - pr[0]))
        print(label, json.dumps(out[label]))
    (WORK / "gate.json").write_text(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["emit", "emit2", "gate"])
    ap.add_argument("--ridge", type=float, default=10.0)
    ap.add_argument("--cap", type=float, default=0.65)
    ap.add_argument("--extra-thresh", type=float, default=None)
    ap.add_argument("--n-lo", type=int, default=15_000)
    ap.add_argument("--n-hi", type=int, default=70_000)
    ap.add_argument("--collar", type=float, default=2.01)
    ap.add_argument("--boot", type=int, default=60)
    a = ap.parse_args()
    if a.cmd == "emit":
        cmd_emit(a.ridge, a.cap, a.collar)
    elif a.cmd == "emit2":
        cmd_emit2(a.ridge, a.cap, a.collar, a.extra_thresh, a.n_lo, a.n_hi)
    else:
        cmd_gate(a.boot)


if __name__ == "__main__":
    main()
