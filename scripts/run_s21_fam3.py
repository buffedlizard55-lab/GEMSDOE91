#!/usr/bin/env python3
"""S21-FAM3 lane driver (preregistration: docs/HYPOTHESES_S21_FAM3.md).

Reuses, unchanged: src/gems91/lfi.py (exact-DTI aggregate inversion),
src/gems91/lfi_emit.py (coverage-aware greedy pools + model DTI),
vendor/gems57/evaluate_holdout.py + spatial.folds (hide-and-recover),
vendor/gems57/submission_writer.py (writer/validator, via write step).

    python scripts/run_s21_fam3.py aggregate
    python scripts/run_s21_fam3.py fit --ridge 10
    python scripts/run_s21_fam3.py fit --ridge 1
    python scripts/run_s21_fam3.py surface            # q-map + pre-placement rank check
    python scripts/run_s21_fam3.py emit               # -> work/s21/cand_dots.npy
    python scripts/run_s21_fam3.py gate --boot 60     # paired projection vs R0 (MODEL)
    python scripts/run_s21_fam3.py holdout            # HOLDOUT-DTI + canaries

Every fitted/projected number written by this script is MODEL/PROJECTION
(fitted to USER-REPORTED scores) unless the key says HOLDOUT-DTI.
"""
from __future__ import annotations

import os
for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_k, "2")
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT)]
from gems91 import lfi as L, lfi_emit as E  # noqa: E402
import run_lfi as R  # noqa: E402  (base + read_pred, shared with S20)

WORK = ROOT / "work/s21"
OUT = ROOT / "docs/s21"
STACK = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
R0 = ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif"
F33 = ROOT / "data/fleet_registry/GEMSDOE33__h33d-analog-tip-stepover-r30.tif"
F36 = ROOT / "data/lfi_anchors/GEMSDOE36__gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"
NINE_SITES = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
              "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
FACTOR_LEVELS = [9, 6, 3, 3, 3, 3, 3, 3]
FACTOR_NAMES = ["dcat", "dnet_h195", "d_gemsdoe33", "d_gemsdoe36",
                "det_elev_slope_B19", "depth_to_base_B15", "det_elev_B12", "grad_B15"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def clean_band(v: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Replace stack sentinels (-3.4e38 outside footprint) with the footprint median."""
    v = v.astype(np.float64)
    good = fp & np.isfinite(v) & (v > -1e30)
    med = float(np.median(v[good]))
    return np.where(good | fp, np.where(np.isfinite(v) & (v > -1e30), v, med), med)


def build_design_s21(fp, cat, net):
  d = L.Design(fp=fp)
  dcat = L.dist_px(cat)
  dnet = L.dist_px(net)
  d.add("dcat", np.digitize(dcat, L.DCAT_EDGES), 9,
        ["0", "1", "1-2", "2-3", "3-5", "5-10", "10-20", "20-40", ">40"])
  d.add("dnet_h195", np.digitize(dnet, L.DNET_EDGES), 6, ["on", "1", "1-2", "2-3", "3-6", ">6"])
  for name, path in (("d_gemsdoe33", F33), ("d_gemsdoe36", F36)):
      p, why = R.read_pred(path, fp)
      assert p is not None, (name, why)
      dist = L.dist_px(p > 0)
      d.add(name, np.digitize(dist, (1.01, 3.01)), 3, ["<=1", "1-3", ">3"])
      d.meta[name] = dict(source=str(path.relative_to(ROOT)), sha256=sha256(path), n_pos=int((p > 0).sum()))
  with rasterio.open(STACK) as s:
      bands = {}
      for nm, b in (("det_elev_slope_B19", 19), ("depth_to_base_B15", 15), ("det_elev_B12", 12)):
          v = clean_band(s.read(b), fp)
          bands[nm] = v
          code, qs = L.tercile_codes(v.astype(np.float32), fp)
          d.add(nm, code, 3, ["lo", "mid", "hi"])
          d.meta[nm] = dict(band=b, terciles=qs)
      b15 = bands["depth_to_base_B15"]
      gy = ndi.sobel(b15, axis=0)
      gx = ndi.sobel(b15, axis=1)
      grad = np.hypot(gy, gx).astype(np.float32)
      code, qs = L.tercile_codes(grad, fp)
      d.add("grad_B15", code, 3, ["lo", "mid", "hi"])
      d.meta["grad_B15"] = dict(band=15, transform="Sobel gradient magnitude of sentinel-cleaned B15",
                                terciles=qs)
      np.save(WORK / "grad_b15.npy", grad)
  return d, dcat, dnet


def anchor_rows():
    """The same 112 used anchors as S20 (docs/lfi/anchors.json), locals already restored."""
    meta = json.loads((ROOT / "docs/lfi/anchors.json").read_text())
    return [r for r in meta["rows"] if r.get("used")]


def cmd_aggregate():
    WORK.mkdir(parents=True, exist_ok=True)
    fp, cat, net = R.base()
    d, dcat, dnet = build_design_s21(fp, cat, net)
    bins = d.bin_index()
    np.save(WORK / "bins.npy", bins)
    nb = d.n_bins
    A = np.bincount(bins[fp & ~cat], minlength=nb).astype(np.float64)
    rows = anchor_rows()
    Ns, Cs, used = [], [], []
    for r in rows:
        p, why = R.read_pred(ROOT / r["local"], fp)
        assert p is not None, (r["name"], why)
        assert sha256(ROOT / r["local"]) == r["sha256"], r["name"]
        N, C = L.aggregate(p, bins, nb, cat)
        Ns.append(N); Cs.append(C); used.append(r)
        print(f"{r['score']:.4f} {r['site']:10s} {r['name'][:60]}", flush=True)
    np.savez_compressed(WORK / "agg.npz", N=np.array(Ns), C=np.array(Cs), A=A, L=d.level_matrix())
    (WORK / "design.json").write_text(json.dumps(dict(
        param_names=d.param_names(), meta=d.meta, n_bins=nb,
        factor_names=FACTOR_NAMES, factor_levels=FACTOR_LEVELS,
        anchors=[dict(site=r["site"], name=r["name"], score=r["score"], local=r["local"],
                      sha256=r["sha256"]) for r in used]), indent=1))
    print(f"aggregated {len(used)} anchors; bins={nb}; params={len(d.param_names())}")


def load():
    z = np.load(WORK / "agg.npz")
    meta = json.loads((WORK / "design.json").read_text())
    obs = np.array([r["score"] for r in meta["anchors"]])
    return z["N"], z["C"], z["A"], z["L"], obs, meta


def cmd_fit(ridge):
    from scipy.stats import spearmanr, pearsonr
    N, C, A, Lm, obs, meta = load()
    names = meta["param_names"]
    full = L.fit(N, C, A, Lm, obs, ridge=ridge)
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    _, parts = L.predict(full.theta, full.f, X, N, C, A)
    sites = np.array([r["site"] for r in meta["anchors"]])
    loo = np.zeros(len(obs))
    for s in np.unique(sites):
        tr = sites != s
        fi = L.fit(N[tr], C[tr], A, Lm, obs[tr], ridge=ridge, theta0=full.theta)
        pr, _ = L.predict(fi.theta, fi.f, X, N[~tr], C[~tr], A)
        loo[~tr] = pr
        print(f"loso {s} done", flush=True)
    res = dict(
        evidence_class="MODEL (fitted to USER-REPORTED public scores; never a score)",
        design="S21-FAM3 (no consensus covariate; d33/d36 + grad_B15 factors)",
        n_anchors=len(obs), ridge=ridge, f=full.f, K_expected=parts["K"],
        rmse_in_sample=full.rmse, rmse_loso=float(np.sqrt(np.mean((loo - obs) ** 2))),
        spearman_loso=float(spearmanr(loo, obs).statistic),
        pearson_loso=float(pearsonr(loo, obs).statistic),
        theta={n: float(t) for n, t in zip(names, full.theta)},
        anchors=[dict(site=r["site"], name=r["name"], obs=float(o), fit=float(p), loso=float(l))
                 for r, o, p, l in zip(meta["anchors"], obs, full.pred, loo)],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    tag = f"fit_r{ridge:g}"
    (OUT / f"{tag}.json").write_text(json.dumps(res, indent=1))
    np.save(WORK / f"{tag}_theta.npy", np.concatenate([full.theta, [full.f]]))
    print(json.dumps({k: v for k, v in res.items() if k != "anchors"}, indent=1))


def qmap_from(ridge):
    fp, cat, net = R.base()
    bins = np.load(WORK / "bins.npy")
    z = np.load(WORK / "agg.npz")
    th = np.load(WORK / f"fit_r{ridge:g}_theta.npy")
    theta, f = th[:-1], float(th[-1])
    Lm = z["L"]
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    qb = np.exp(np.clip(X @ theta, -30, 5))
    q = np.where(bins >= 0, qb[np.maximum(bins, 0)], 0.0).astype(np.float32)
    q[cat] = 0.0
    A = np.bincount(bins[(bins >= 0) & ~cat], minlength=len(qb)).astype(np.float64)
    K = float(qb @ A)
    return q, f, K, fp, cat


def registry_set():
    """fleet registry + LFI anchors + own downloads, byte-deduped."""
    seen, out = {}, []
    for sub in ("data/fleet_registry", "data/lfi_anchors", "docs/downloads"):
        for p in sorted((ROOT / sub).glob("*.tif")):
            h = sha256(p)
            if h in seen:
                continue
            seen[h] = str(p.relative_to(ROOT))
            out.append((str(p.relative_to(ROOT)), h))
    return out


def cmd_surface(ridge=10.0):
    """Pre-placement (protocol rule 1): q-surface rank correlation vs registry set."""
    from scipy.stats import rankdata
    q, f, K, fp, cat = qmap_from(ridge)
    np.save(WORK / "cand_q.npy", q)
    fp_idx = np.flatnonzero(fp.ravel())
    sv = q.astype(np.float64).ravel()[fp_idx][::5]
    rs = rankdata(sv) - (sv.size + 1) / 2.0
    rs_n = float(np.linalg.norm(rs))
    rows = []
    for local, h in registry_set():
        with rasterio.open(ROOT / local) as ds:
            if ds.count != 1 or ds.shape != fp.shape:
                continue
            a = ds.read(1)
        a = np.nan_to_num(a.astype(np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        rv = a.ravel()[fp_idx][::5]
        rr = rankdata(rv) - (rv.size + 1) / 2.0
        rr_n = float(np.linalg.norm(rr))
        rho = abs(float(rs @ rr) / (rs_n * rr_n)) if rr_n > 0 else 0.0
        rows.append(dict(raster=local, surface_abs_spearman=round(rho, 5),
                         n_positive=int((a.ravel()[fp_idx] > 0).sum())))
    rows.sort(key=lambda r: -r["surface_abs_spearman"])
    OUT.mkdir(parents=True, exist_ok=True)
    rep = dict(phase="surface_preplacement", ridge=ridge, f=f, K_model=K,
               rule="duplicate-stop if |Spearman(q-surface, reference)| > 0.90 (stride-5 footprint sample, as sibling_sweep.cmd_check)",
               n_compared=len(rows), max_surface_abs_spearman=rows[0]["surface_abs_spearman"],
               verdict="PASS" if rows[0]["surface_abs_spearman"] <= 0.90 else "DUPLICATE-STOP",
               worst=rows[:10])
    (OUT / "surface-precheck.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: rep[k] for k in ("n_compared", "max_surface_abs_spearman", "verdict")}, indent=1))
    print("worst:", rows[0])


def cmd_emit(ridge=10.0, cap=0.65, collar=3.01, extra_thresh=None):
    q, f, K, fp, cat = qmap_from(ridge)
    dcat = L.dist_px(cat)
    allowed = fp & ~cat & (dcat > collar)
    # family halo (union of nine-site lineage supports dilated 3 px) for the two-pool design
    fam_paths = [R0, F33, F36, ROOT / "data/fleet_registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif",
                 ROOT / "data/lfi_anchors/GEMSDOE28__gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
                 ROOT / "data/lfi_anchors/GEMSDOE25__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"]
    fam = np.zeros(fp.shape, bool)
    for pth in fam_paths:
        p, _ = R.read_pred(pth, fp)
        fam |= L.dist_px(p > 0) <= 3.000001
    print(f"f={f:.3f} K={K:.0f} allowed={int(allowed.sum())} fam&allowed={int((fam & allowed).sum())}", flush=True)
    # Pass-2 only: a lower pool bar (lam=0.06) so the cap-fill has enough dots
    # OUTSIDE the worst sibling halos; pass-1 (lam=0.10) pools are unchanged.
    lam = 0.06 if extra_thresh is not None else 0.10
    print("pool H (in family halo)", flush=True)
    hy, hx, hv = E.ranked_pool(q, f, allowed & fam, lam=lam)
    print("pool F (off family halo)", flush=True)
    fy, fx, fv = E.ranked_pool(q, f, allowed & ~fam, lam=lam)
    if extra_thresh is not None:
        hy, hx, hv = hy[:90_000], hx[:90_000], hv[:90_000]
        fy, fx, fv = fy[:90_000], fx[:90_000], fv[:90_000]
    cy = np.concatenate([hy, fy]); cx = np.concatenate([hx, fx]); cv = np.concatenate([hv, fv])
    order = np.argsort(-cv, kind="stable")[:160_000]
    cy, cx = cy[order], cx[order]
    print(f"pool merged={cy.size} (H={hy.size} F={fy.size})", flush=True)
    # binding columns: every registry-set raster with 0 < n_pos <= 150k (sparse for any final n >= ~30k;
    # capping denser ones too is stricter than the rule, recorded in emit.json)
    cols, refs = [], []
    for local, h in registry_set():
        p, why = R.read_pred(ROOT / local, fp)
        if p is None:
            continue
        n_pos = int((p > 0).sum())
        if n_pos == 0 or n_pos > 150_000:
            continue
        cols.append((L.dist_px(p > 0) <= 3.000001)[cy, cx])
        refs.append(dict(raster=local, sha256=h, n_positive=n_pos, origin="registry-set"))
    if extra_thresh is not None:
        # Pass-2 (S20 precedent): every sparse sibling-sweep raster whose measured
        # literal overlap with the pass-1 candidate was >= extra_thresh becomes a
        # hard cap column. Deduped by sha256 against the registry-set columns.
        known = {r["sha256"] for r in refs}
        sib = json.loads((OUT / "pass1-sibling-check.json").read_text())
        extra_paths = []
        for r in sib["rows"]:
            if r["dense"] or r["within_3px_literal"] < extra_thresh:
                continue
            h = sha256(ROOT / r["raster"])
            if h not in known:
                known.add(h)
                extra_paths.append((r["raster"], h))
        for local, h in extra_paths:
            p, why = R.read_pred(ROOT / local, fp)
            assert p is not None, (local, why)
            cols.append((L.dist_px(p > 0) <= 3.000001)[cy, cx])
            refs.append(dict(raster=local, sha256=h, n_positive=int((p > 0).sum()),
                             origin=f"sibling-sweep pass1 >={extra_thresh}"))
        print(f"pass-2 extra caps from sibling sweep: {len(extra_paths)}", flush=True)
    bitmat = np.stack(cols, 1)
    np.savez_compressed(WORK / "emit_debug.npz", cy=cy, cx=cx, bitmat=bitmat)
    colfrac = bitmat.mean(0)
    print("bitmat", bitmat.shape, "col frac>0.99:", int((colfrac > 0.99).sum()),
          "max colfrac", float(colfrac.max()), "refs with colfrac>0.9:",
          [(refs[i]["raster"], round(float(colfrac[i]), 3)) for i in np.flatnonzero(colfrac > 0.9)][:8], flush=True)
    nref = len(refs)
    print(f"binding refs capped at {cap}: {nref}", flush=True)

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
        return d, take

    def fill_exact(n_target):
        for _ in range(60):
            d, take = fill(n_target)
            n = int(d.sum())
            if n == 0 or bitmat[take].sum(0).max() <= cap * n:
                return d
            n_target = n - 1
        return d

    def repair_sel(sel):
        sel = sel.copy()
        for _ in range(2000):
            n = int(sel.sum()); counts = bitmat[sel].sum(0)
            worst = int(np.argmax(counts))
            if n == 0 or counts[worst] <= cap * n:
                return sel
            need = int(np.ceil((counts[worst] - cap * n) / (1 - cap))) + 1
            idx = np.flatnonzero(sel & bitmat[:, worst])
            sel[idx[-need:]] = False
        raise RuntimeError("repair did not converge")

    def floor_fill(slack=200, max_k=60_000):
        # Ratio-aware greedy in pool-value order: accept iff every cap stays
        # <= cap*(k+1) + slack, so the 65% ratio holds throughout the build
        # (final slack/k is removed by repair_sel). Replaces two failures found
        # in pass 2 on work/s21/emit_debug.npz: S20-style fill_exact ratchets to
        # 681 dots when supply-limited under 312 caps, and a fixed-floor fill
        # saturates then collapses to ~1.9k dots under deletion repair; the
        # ratio fill reaches 37,654 feasible dots on the identical bitmatrix.
        counts = np.zeros(nref, np.int64)
        acc = []
        k = 0
        for i in range(cy.size):
            b = bitmat[i]
            if b.any() and np.any(counts[b] + 1 > cap * (k + 1) + slack):
                continue
            counts[b] += 1
            acc.append(i)
            k += 1
            if k >= max_k:
                break
        return np.array(acc, dtype=np.int64)

    best, rows = None, []
    if extra_thresh is None:
        for n in (25_000, 30_000, 35_000, 37_654, 40_000, 45_000):
            d = fill_exact(n)
            md = E.model_dti(d, q, f, K)
            rows.append(dict(n_target=n, n=int(d.sum()), model_dti=md))
            print(f"  n_target={n} n={int(d.sum())} model-DTI(PROJECTION)={md:.4f}", flush=True)
            if best is None or md > best[0]:
                best = (md, d)
        dots = best[1]
    else:
        acc = floor_fill()
        print(f"ratio-fill accepted {acc.size} pool dots", flush=True)
        for n in (20_000, 25_000, 30_000, 35_000, 40_000, int(acc.size)):
            if n > acc.size:
                continue
            sel = np.zeros(cy.size, bool)
            sel[acc[:n]] = True
            sel = repair_sel(sel)
            d = np.zeros(fp.shape, bool)
            d[cy[sel], cx[sel]] = True
            md = E.model_dti(d, q, f, K)
            rows.append(dict(n_target=n, n=int(d.sum()), model_dti=md))
            print(f"  prefix={n} n={int(d.sum())} model-DTI(PROJECTION)={md:.4f}", flush=True)
            if best is None or md > best[0]:
                best = (md, d)
        dots = best[1]
    sel = dots[cy, cx]
    for _ in range(500):
        n = int(sel.sum()); counts = bitmat[sel].sum(0)
        worst = int(np.argmax(counts))
        if counts[worst] <= cap * n:
            break
        need = int(np.ceil((counts[worst] - cap * n) / (1 - cap))) + 1
        idx = np.flatnonzero(sel & bitmat[:, worst])
        sel[idx[-need:]] = False
    dots = np.zeros(fp.shape, bool)
    dots[cy[sel], cx[sel]] = True
    counts = bitmat[sel].sum(0)
    np.save(WORK / "cand_dots.npy", dots)
    np.save(WORK / "cand_q.npy", q)
    (WORK / "emit.json").write_text(json.dumps(dict(
        method="two-pool ranked_pool + cap-fill (S20 emit2 pattern, shared lfi_emit)",
        extra_thresh=extra_thresh,
        ridge=ridge, cap=cap, collar_px=collar, f=f, K_model=K, n_dots=int(dots.sum()),
        model_dti_selected=E.model_dti(dots, q, f, K), size_scan=rows,
        n_binding_refs=nref, max_binding_frac=float(counts.max() / dots.sum()),
        worst_refs=sorted((dict(raster=r["raster"], frac=float(counts[i] / dots.sum()))
                             for i, r in enumerate(refs)), key=lambda r: -r["frac"])[:12],
        pool=dict(H=int(hy.size), F=int(fy.size), merged_capped=int(cy.size))), indent=1))
    print(f"emitted {int(dots.sum())} dots; max binding frac {counts.max()/dots.sum():.4f}")


def cmd_gate(boot=60, seed=20261026):
    fp, cat, net = R.base()
    bins = np.load(WORK / "bins.npy")
    N, C, A, Lm, obs, meta = load()
    nb = Lm.shape[0]
    dots = np.load(WORK / "cand_dots.npy").astype(np.float32)
    r0, _ = R.read_pred(R0, fp)
    Nc, Cc = L.aggregate(dots, bins, nb, cat)
    Nr, Cr = L.aggregate(r0, bins, nb, cat)
    X = np.hstack([np.ones((nb, 1)), Lm])
    sites = np.array([r["site"] for r in meta["anchors"]])
    us = np.unique(sites)
    rng = np.random.default_rng(seed)
    out = {}
    for label, ridge, blind in (("ridge10", 10.0, False), ("ridge1", 1.0, False),
                                ("ridge1_blind_nine", 1.0, True)):
        base_mask = np.array([s not in NINE_SITES for s in sites]) if blind else np.ones(len(sites), bool)
        full = L.fit(N[base_mask], C[base_mask], A, Lm, obs[base_mask], ridge=ridge)
        pc, _ = L.predict(full.theta, full.f, X, Nc[None], Cc[None], A)
        pr, _ = L.predict(full.theta, full.f, X, Nr[None], Cr[None], A)
        deltas = []
        for _ in range(boot):
            pick = rng.choice(us, size=len(us), replace=True)
            w = np.zeros(len(sites))
            for s in pick:
                w[sites == s] += 1.0
            w = w * base_mask
            keep = w > 0
            fi = L.fit(N[keep], C[keep], A, Lm, obs[keep], ridge=ridge, weights=w[keep], theta0=full.theta)
            a, _ = L.predict(fi.theta, fi.f, X, Nc[None], Cc[None], A)
            r, _ = L.predict(fi.theta, fi.f, X, Nr[None], Cr[None], A)
            deltas.append(float(a[0] - r[0]))
        dv = np.array(deltas)
        out[label] = dict(
            label="PROJECTION (surrogate, paired vs R0, site bootstrap; not a score)",
            model_cand=float(pc[0]), model_r0=float(pr[0]), delta=float(pc[0] - pr[0]),
            boot_delta_ci95=[float(np.quantile(dv, .025)), float(np.quantile(dv, .975))],
            p_delta_gt0=float((dv > 0).mean()), boot=boot,
            projection_vs_reported_r0=float(0.2778 + pc[0] - pr[0]),
            n_fit_anchors=int(base_mask.sum()))
        print(label, json.dumps(out[label]), flush=True)
    (OUT / "gate.json").write_text(json.dumps(out, indent=1))


def cmd_holdout():
    from scipy.stats import spearmanr
    from sklearn.metrics import roc_auc_score
    sys.path.insert(0, str(ROOT / "vendor"))
    from vendor.gems57 import evaluate_holdout as EH, spatial  # noqa: E402
    fp, cat, net = R.base()
    folds = list(spatial.folds(cat, fp, buffer_px=80))
    split_sha = hashlib.sha256(b"".join(np.packbits(f[k].ravel()).tobytes() for f in folds
                                        for k in ("region", "truth", "train", "visible"))).hexdigest()
    n_truth = int(sum(f["truth"].sum() for f in folds))
    print(f"split_sha256={split_sha} withheld={n_truth} evaluator={EH.VERSION}", flush=True)

    def score(p):
        terms = None
        for f in folds:
            _, t = EH.evaluate(p, f, fp)
            terms = t if terms is None else terms + t
        return terms

    arms = {}
    cand = np.load(WORK / "cand_dots.npy").astype(np.float32)
    arms["s21_candidate"] = cand
    arms["r0_gemsdoe32"], _ = R.read_pred(R0, fp)
    nine = {
        "GEMSDOE24": ("h25-1-dotted-h19-5-d1-5", 0.2477, "data/lfi_anchors/GEMSDOE24__gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
        "GEMSDOE25/30": ("dotted-h19-5-d2-8", 0.2600, "data/lfi_anchors/GEMSDOE25__gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
        "GEMSDOE27": ("topo-gap-closure-t-v2-on-d1-5", 0.2449, "data/lfi_anchors/GEMSDOE27__gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
        "GEMSDOE28/31": ("h27-4-solo-d2-8", 0.2708, "data/lfi_anchors/GEMSDOE28__gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif"),
        "GEMSDOE28b": ("h36-1-rung30-blind-r1", 0.2710, "data/lfi_anchors/GEMSDOE28__gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif"),
        "GEMSDOE33": ("h33d-analog-tip-stepover-r30", 0.2632, "data/fleet_registry/GEMSDOE33__h33d-analog-tip-stepover-r30.tif"),
        "GEMSDOE36": ("anderson-geothermal-pinn-38854", 0.2750, "data/lfi_anchors/GEMSDOE36__gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"),
    }
    for key, (_, _, local) in nine.items():
        arms[key], _ = R.read_pred(ROOT / local, fp)
    terms_by = {k: score(v) for k, v in arms.items()}
    summ = EH.pooled_summary(terms_by, draws=1000, seed=520810, candidate="s21_candidate")
    # canaries: each S21 factor alone vs withheld truth (dcat/dnet recomputed from visible only where catalogue-based)
    bins = np.load(WORK / "bins.npy")
    idx = np.array(np.unravel_index(np.maximum(bins, 0), FACTOR_LEVELS))
    canaries = {}
    for j, nm in enumerate(FACTOR_NAMES):
        y_all, s_all = [], []
        for f in folds:
            dom = f["region"] & ~f["visible"]
            if nm == "dcat":
                code = np.digitize(L.dist_px(f["visible"]), L.DCAT_EDGES)[dom].astype(float)
            else:
                code = idx[j][dom].astype(float)
            y_all.append(f["truth"][dom]); s_all.append(code)
        y = np.concatenate(y_all); s = np.concatenate(s_all)
        auc = float(roc_auc_score(y, s))
        canaries[nm] = dict(auc=auc, symmetric_auc=max(auc, 1 - auc))
    # instrument check on the scored nine-site arms (+R0): hide-v2 vs USER-REPORTED live
    live_keys = [(k, nine[k][0], nine[k][1]) for k in nine] + [("r0_gemsdoe32", "h33-h33-2-b2", 0.2778)]
    live = np.array([v for _, _, v in live_keys])
    hv = np.array([summ["scores"][k]["dti"] for k, _, _ in live_keys])
    prev = json.loads((ROOT / "docs/lfi/holdout-e2.json").read_text())
    out = dict(
        label="HOLDOUT-DTI", evaluator_version=EH.VERSION, split_sha256=split_sha,
        withheld_positives=n_truth, pooled=summ, canaries=canaries,
        canary_pass=all(v["symmetric_auc"] <= 0.90 for v in canaries.values()),
        instrument_check_nine_sites=dict(
            n=len(live_keys), spearman_hide_v2_vs_live=float(spearmanr(hv, live).statistic),
            s20_full_112_anchor_spearman=prev["instrument_validity"]["spearman_hide_v2_vs_live"],
            s20_split_sha256=prev["split_sha256"], split_matches_s20=bool(split_sha == prev["split_sha256"]),
            note="USER-REPORTED live scores; hide-v2 withholds catalogued pixels, live truth excludes the catalogue."),
    )
    (OUT / "holdout.json").write_text(json.dumps(out, indent=1))
    for k in arms:
        print(k, summ["scores"][k]["dti"], summ["scores"][k]["ci95"])
    print("canaries", canaries)
    print("instrument nine-site Spearman", out["instrument_check_nine_sites"]["spearman_hide_v2_vs_live"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["aggregate", "fit", "surface", "emit", "gate", "holdout"])
    ap.add_argument("--ridge", type=float, default=10.0)
    ap.add_argument("--boot", type=int, default=60)
    ap.add_argument("--extra-thresh", type=float, default=None)
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    if a.cmd == "aggregate":
        cmd_aggregate()
    elif a.cmd == "fit":
        cmd_fit(a.ridge)
    elif a.cmd == "surface":
        cmd_surface(a.ridge)
    elif a.cmd == "emit":
        cmd_emit(a.ridge, extra_thresh=a.extra_thresh)
    elif a.cmd == "gate":
        cmd_gate(a.boot)
    else:
        cmd_holdout()


if __name__ == "__main__":
    main()
