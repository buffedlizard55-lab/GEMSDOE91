#!/usr/bin/env python3
"""LFI lane driver: aggregate anchors -> fit inversion -> leave-one-out -> diagnostics.

    python scripts/run_lfi.py aggregate     # cache per-anchor bin aggregates (work/lfi/agg.npz)
    python scripts/run_lfi.py fit           # fit + LOO; writes docs/lfi/fit.json
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

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from gems91 import lfi as L  # noqa: E402

SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
STACK = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
NET = ROOT / "data/fleet_registry/19GEMSDOE__h19-5-powerlaw-budget-multiline.tif"
WORK = ROOT / "work/lfi"
OUT = ROOT / "docs/lfi"
MATCHES = ROOT / "registry/lfi_anchor_matches.json"
# Anchors that the strict name matcher could not find in the sibling index but which exist in the
# SHA-pinned local fleet registry (scripts/restore_registry.py) under a name that encodes the score.
FALLBACK = {
    "h33d-analog-tip-stepover-r30-20261004-cb490425926e": "data/fleet_registry/GEMSDOE33__h33d-analog-tip-stepover-r30.tif",
    "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca": "data/fleet_registry/GEMSDOE30__d28-poisson300m-offcat-44090.tif",
    "H25-ctx-ridge-20260927T232947704150Z-6452ae1d00": "data/fleet_registry/calib_h25ctx_01280.tif",
    "h19-4-reference-20260930-691e4dfa": "data/fleet_registry/19GEMSDOE__h19-4-multiline-corroborated.tif",
}
BANDS = {"det_elev_slope": 19, "depth_to_base": 15, "det_elev": 12, "geod_2ndinv": 4}
# Consensus covariate: independent high-scoring (USER-REPORTED >= 0.18) anchors that put most of their dots
# OFF the h19-5 network (frac within 1.5 px < 0.80). Selected by a rule on the anchor table, not by hand-picking
# pixels; the list is printed into anchors.json for audit.
CONS_MIN_SCORE, CONS_MAX_ONNET, CONS_RADIUS = 0.18, 0.80, 1.5
CONS_EDGES = (0.5, 1.5, 2.5)   # 0, 1, 2, >=3 agreeing anchors


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def base():
    with rasterio.open(SAMPLE) as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(CAT) as s:
        cat = (s.read(1) > 0) & fp
    with rasterio.open(NET) as s:
        net = (np.nan_to_num(s.read(1)) > 0) & fp
    return fp, cat, net


def consensus_votes(fp, rows_meta):
    """Number of distinct-site consensus anchors with a positive pixel within CONS_RADIUS px."""
    votes = np.zeros(fp.shape, np.int16)
    used_sites, chosen = set(), []
    for r in sorted(rows_meta, key=lambda r: -r["score"]):
        if not r.get("used") or r["score"] < CONS_MIN_SCORE or r["frac_on_net15"] >= CONS_MAX_ONNET:
            continue
        if r["site"] in used_sites:
            continue
        p, _ = read_pred(ROOT / r["local"], fp)
        votes += (L.dist_px(p > 0) <= CONS_RADIUS).astype(np.int16)
        used_sites.add(r["site"])
        chosen.append(dict(site=r["site"], name=r["name"], score=r["score"], frac_on_net15=r["frac_on_net15"]))
    return votes, chosen


def build_design(fp, cat, net, rows_meta=None):
    d = L.Design(fp=fp)
    dcat = L.dist_px(cat)
    dnet = L.dist_px(net)
    d.add("dcat", np.digitize(dcat, L.DCAT_EDGES), len(L.DCAT_EDGES) + 1,
          ["0", "1", "1-2", "2-3", "3-5", "5-10", "10-20", "20-40", ">40"])
    d.add("dnet", np.digitize(dnet, L.DNET_EDGES), len(L.DNET_EDGES) + 1, ["on", "1", "1-2", "2-3", "3-6", ">6"])
    with rasterio.open(STACK) as s:
        for name, b in BANDS.items():
            v = s.read(b).astype(np.float32)
            code, qs = L.tercile_codes(v, fp)
            d.add(name, code, 3, ["lo", "mid", "hi"])
            d.meta[name] = dict(band=b, terciles=qs)
    if rows_meta is not None:
        votes, chosen = consensus_votes(fp, rows_meta)
        d.add("cons", np.digitize(votes, CONS_EDGES), len(CONS_EDGES) + 1, ["0", "1", "2", ">=3"])
        d.meta["consensus_anchors"] = chosen
        np.save(WORK / "cons_votes.npy", votes)
    return d, dcat, dnet


def read_pred(path: Path, fp):
    with rasterio.open(path) as s:
        if s.count != 1 or s.shape != fp.shape:
            return None, f"shape/count {s.count}x{s.shape}"
        a = s.read(1).astype(np.float32)
    a = np.where(np.isfinite(a), a, 0.0)
    a = np.where(fp, a, 0.0)
    if a.min() < 0 or a.max() > 1:
        return None, f"values outside [0,1]: [{a.min()}, {a.max()}]"
    return a, "ok"


def cmd_aggregate():
    WORK.mkdir(parents=True, exist_ok=True)
    fp, cat, net = base()
    prev = json.loads((WORK / "anchors_base.json").read_text())["rows"] if (WORK / "anchors_base.json").exists() else None
    d, dcat, dnet = build_design(fp, cat, net, prev)
    bins = d.bin_index()
    np.save(WORK / "bins.npy", bins)
    nb = d.n_bins
    A = np.bincount(bins[fp & ~cat], minlength=nb).astype(np.float64)
    matches = json.loads(MATCHES.read_text())
    rows, Ns, Cs = [], [], []
    for m in matches:
        local = m.get("local") if m["status"] == "MATCHED" else FALLBACK.get(m["name"])
        if not local:
            rows.append(dict(name=m["name"], site=m["site"], score=m["score"], used=False, reason="unmatched"))
            continue
        p, why = read_pred(ROOT / local, fp)
        if p is None:
            rows.append(dict(name=m["name"], site=m["site"], score=m["score"], used=False, reason=why, local=local))
            continue
        N, C = L.aggregate(p, bins, nb, cat)
        Ns.append(N)
        Cs.append(C)
        pos = p > 0
        rows.append(dict(name=m["name"], site=m["site"], score=m["score"], used=True, local=local,
                         source="sibling-index" if m["status"] == "MATCHED" else "fleet-registry-fallback",
                         sha256=sha256(ROOT / local), n_pos=int(pos.sum()), mass=float(p.sum()),
                         binary=bool(np.all((p == 0) | (p == 1))), on_catalogue=int((pos & cat).sum()),
                         frac_dcat_le2=float((dcat[pos] <= 2.01).mean()) if pos.any() else 0.0,
                         frac_on_net15=float((dnet[pos] <= 1.51).mean()) if pos.any() else 0.0))
        print(f"{m['score']:.4f} n={int(pos.sum()):7d} {m['name'][:70]}", flush=True)
    np.savez_compressed(WORK / "agg.npz", N=np.array(Ns), C=np.array(Cs), A=A, L=d.level_matrix())
    (WORK / "anchors.json").write_text(json.dumps(dict(rows=rows, param_names=d.param_names(), meta=d.meta,
                                                       n_bins=nb), indent=1))
    print(f"used {sum(r['used'] for r in rows)} / {len(rows)} anchors; bins={nb}")


def load():
    z = np.load(WORK / "agg.npz")
    meta = json.loads((WORK / "anchors.json").read_text())
    used = [r for r in meta["rows"] if r["used"]]
    obs = np.array([r["score"] for r in used])
    return z["N"], z["C"], z["A"], z["L"], obs, used, meta


def cmd_fit(ridge: float, f_fixed):
    N, C, A, Lm, obs, used, meta = load()
    names = meta["param_names"]
    full = L.fit(N, C, A, Lm, obs, ridge=ridge, f_fixed=f_fixed)
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    _, parts = L.predict(full.theta, full.f, X, N, C, A)
    # leave-one-site-out (all anchors of one site removed together) — anchors from the same site are
    # often near-duplicates, so leave-one-anchor-out would be optimistic.
    sites = np.array([r["site"] for r in used])
    loo = np.zeros(len(obs))
    for s in np.unique(sites):
        tr = sites != s
        fi = L.fit(N[tr], C[tr], A, Lm, obs[tr], ridge=ridge, f_fixed=f_fixed, theta0=full.theta)
        pr, _ = L.predict(fi.theta, fi.f, X, N[~tr], C[~tr], A)
        loo[~tr] = pr
    from scipy.stats import spearmanr, pearsonr
    res = dict(
        evidence_class="MODEL (fitted to USER-REPORTED public scores; never a score)",
        n_anchors=len(obs), ridge=ridge, f_fixed=f_fixed, f=full.f, K_expected=parts["K"],
        rmse_in_sample=full.rmse, rmse_loso=float(np.sqrt(np.mean((loo - obs) ** 2))),
        spearman_loso=float(spearmanr(loo, obs).statistic), pearson_loso=float(pearsonr(loo, obs).statistic),
        theta={n: float(t) for n, t in zip(names, full.theta)},
        anchors=[dict(site=r["site"], name=r["name"], obs=float(o), fit=float(p), loso=float(l))
                 for r, o, p, l in zip(used, obs, full.pred, loo)],
    )
    OUT.mkdir(parents=True, exist_ok=True)
    tag = f"fit_r{ridge}_f{f_fixed}"
    (WORK / f"{tag}.json").write_text(json.dumps(res, indent=1))
    np.save(WORK / f"{tag}_theta.npy", np.concatenate([full.theta, [full.f]]))
    print(json.dumps({k: v for k, v in res.items() if k not in ("anchors",)}, indent=1))
    worst = sorted(res["anchors"], key=lambda a: -abs(a["loso"] - a["obs"]))[:12]
    for a in worst:
        print(f"  obs {a['obs']:.4f} fit {a['fit']:.4f} loso {a['loso']:.4f}  {a['site']} {a['name'][:60]}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["aggregate", "fit"])
    ap.add_argument("--ridge", type=float, default=1.0)
    ap.add_argument("--f", type=float, default=None)
    a = ap.parse_args()
    if a.cmd == "aggregate":
        cmd_aggregate()
    else:
        cmd_fit(a.ridge, a.f)


if __name__ == "__main__":
    main()
