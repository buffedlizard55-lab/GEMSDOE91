#!/usr/bin/env python3
"""S22 E2 - live-anchored instrument tests (no hide-and-recover holdout is used to *validate* anything here).

Uses the matched USER-REPORTED anchors (registry/lfi_anchor_matches.json, restored by
scripts/restore_lfi_anchors.py) and the unchanged S20 leaderboard-feedback-inversion design (scripts/run_lfi.py).

(a) Instrument validity: Spearman of live score against
      - gems57-pooled-hide-v2 holdout DTI   (read from the pinned docs/lfi/holdout-e2.json; S20 reported 0.105)
      - blind USGS-SGMC DTI (>300 m, >500 m from the catalogue)   (recomputed here)
      - dots-count, far-field share, share on the h19-5 network    (recomputed here)
      - the LFI leave-one-site-out prediction                      (refit here, ridge 10, unchanged design)
    with a 1,000-draw anchor bootstrap.
(b) H22-3 kill test: refuted if the fitted truth-density factor for d in (5,20] px >= that for d in (1,5] px.
(c) H22-2 factor test: one extra tercile factor (orientation mixing of the *catalogue's own traces*) appended to the
    unchanged S20 design; accepted only if LOSO RMSE does not worsen by > 0.0005 AND the site-jackknife 95% interval of
    the fitted (hi vs lo) log-effect lies ABOVE 0 (direction predicted by H22-2; Amendment A2).

Outputs: docs/s22/instruments.json (+ docs/s22/anchor-table.csv).  All fitted quantities are MODEL (never scores).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_k, "2")

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from gems57.metric import dti_binary  # noqa: E402
from gems91 import lfi as L  # noqa: E402

OUT = ROOT / "docs/s22"
SGMC = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
RIDGE = 10.0


def _load_run_lfi():
    spec = importlib.util.spec_from_file_location("run_lfi_mod", ROOT / "scripts/run_lfi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def strike_mixing_code(catalogue: np.ndarray, footprint: np.ndarray, sigma_int: float = 30.0):
    """H22-2: orientation-mixing index of the catalogue's own traces (structure tensor, 3 km window).

    ``MO = tau_norm * (1 - coherence)``: high where mapped faults are dense (large trace ``tau``) **and** several strike
    directions meet (low coherence) - the signature of accommodation / transfer zones (Faulds & Varga 1998).
    """
    c = catalogue.astype(np.float32)
    gx = ndi.gaussian_filter(c, 1.0, order=(0, 1))
    gy = ndi.gaussian_filter(c, 1.0, order=(1, 0))
    jxx = ndi.gaussian_filter(gx * gx, sigma_int)
    jxy = ndi.gaussian_filter(gx * gy, sigma_int)
    jyy = ndi.gaussian_filter(gy * gy, sigma_int)
    tr = jxx + jyy
    disc = np.sqrt(np.maximum((jxx - jyy) ** 2 + 4.0 * jxy ** 2, 0.0))
    coh = np.where(tr > 1e-12, disc / np.maximum(tr, 1e-12), 1.0)
    tau = tr / max(float(np.percentile(tr[footprint], 99.5)), 1e-12)
    mo = np.clip(tau, 0.0, 1.0) * (1.0 - np.clip(coh, 0.0, 1.0))
    code, qs = L.tercile_codes(mo.astype(np.float32), footprint)
    return code, qs, mo


def loso(N, C, A, Lm, obs, sites, ridge, full_theta=None):
    full = L.fit(N, C, A, Lm, obs, ridge=ridge)
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    pred_loso = np.zeros(len(obs))
    thetas = {}
    for s in np.unique(sites):
        tr = sites != s
        fi = L.fit(N[tr], C[tr], A, Lm, obs[tr], ridge=ridge, theta0=full.theta)
        pr, _ = L.predict(fi.theta, fi.f, X, N[~tr], C[~tr], A)
        pred_loso[~tr] = pr
        thetas[s] = fi.theta
    rmse = float(np.sqrt(np.mean((pred_loso - obs) ** 2)))
    return full, pred_loso, rmse, float(spearmanr(pred_loso, obs).statistic), thetas


def boot_spearman(x, y, draws=1000, seed=22):
    rng = np.random.default_rng(seed)
    n = len(x)
    vals = []
    for _ in range(draws):
        i = rng.integers(0, n, n)
        if np.unique(x[i]).size < 3 or np.unique(y[i]).size < 3:
            continue
        vals.append(spearmanr(x[i], y[i]).statistic)
    return [float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="smoke test: use only the first N used anchors")
    args = ap.parse_args()
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    RL = _load_run_lfi()
    RL.WORK = ROOT / "work/lfi"
    RL.WORK.mkdir(parents=True, exist_ok=True)

    meta = json.loads((ROOT / "docs/lfi/anchors.json").read_text())
    sha_map = {}
    for d_rel in ("data/lfi_anchors", "data/fleet_registry", "data/registry"):
        dp = ROOT / d_rel
        for p in dp.glob("*.tif"):
            sha_map.setdefault(sha256(p), str(p.relative_to(ROOT)))
    rows = meta["rows"]
    for r in rows:
        if r.get("used"):
            if r.get("sha256") in sha_map:
                r["local"] = sha_map[r["sha256"]]
            else:
                r["used"] = False
                r["reason"] = "raster not restored in this checkout"
    used_all = [r for r in rows if r["used"]]
    print(f"[E2] anchors used {len(used_all)} / {len(rows)}", flush=True)

    fp, cat, net = RL.base()
    design, dcat, dnet = RL.build_design(fp, cat, net, rows)
    code2, qs2, mo = strike_mixing_code(cat, fp)
    d_ext = L.Design(fp=fp, factors=list(design.factors), meta=dict(design.meta))
    d_ext.add("strike_mix", code2, 3, ["lo", "mid", "hi"])
    bins_ext = d_ext.bin_index()
    nb_ext = d_ext.n_bins
    nb_base = design.n_bins
    assert nb_ext == nb_base * 3
    A_ext = np.bincount(bins_ext[fp & ~cat], minlength=nb_ext).astype(np.float64)
    A_base = A_ext.reshape(nb_base, 3).sum(1)

    with rasterio.open(SGMC) as ds:
        sgmc = (ds.read(1) > 0) & fp
    doms = {"gt300m": fp & (dcat > 3.0), "gt500m": fp & (dcat > 5.0)}

    use = used_all[: args.limit] if args.limit else used_all
    Ns, Cs, table = [], [], []
    for i, r in enumerate(use):
        p, why = RL.read_pred(ROOT / r["local"], fp)
        if p is None:
            print(f"  skip {r['name']}: {why}")
            continue
        N, C = L.aggregate(p, bins_ext, nb_ext, cat)
        Ns.append(N)
        Cs.append(C)
        pos = p > 0
        row = dict(site=r["site"], name=r["name"], live=r["score"], n_dots=int(pos.sum()),
                   far_gt1km=float((dcat[pos] > 10).mean()) if pos.any() else 0.0,
                   on_net15=float((dnet[pos] <= 1.51).mean()) if pos.any() else 0.0)
        for tag, dom in doms.items():
            res = dti_binary(pos & dom, sgmc & dom, valid=dom) if pos.any() else {"dti": 0.0}
            row[f"sgmc_dti_{tag}"] = float(res["dti"])
        table.append(row)
        if (i + 1) % 10 == 0:
            print(f"  [{i + 1}/{len(use)}] {time.time() - t0:.0f}s", flush=True)

    obs = np.array([t["live"] for t in table])
    sites = np.array([t["site"] for t in table])
    N_ext, C_ext = np.array(Ns), np.array(Cs)
    N_b = N_ext.reshape(len(table), nb_base, 3).sum(2)
    C_b = C_ext.reshape(len(table), nb_base, 3).sum(2)

    base_fit, base_loso, base_rmse, base_sp, _ = loso(N_b, C_b, A_base, design.level_matrix(), obs, sites, RIDGE)
    ext_fit, ext_loso, ext_rmse, ext_sp, ext_thetas = loso(N_ext, C_ext, A_ext, d_ext.level_matrix(), obs, sites, RIDGE)

    names_b = design.param_names()
    names_e = d_ext.param_names()
    theta_b = dict(zip(names_b, base_fit.theta))
    theta_e = dict(zip(names_e, ext_fit.theta))

    # (a) instrument validity
    hold = {a["name"]: a["hide_v2"] for a in json.loads((ROOT / "docs/lfi/holdout-e2.json").read_text())["anchors"]}
    for t, pr in zip(table, base_loso):
        t["lfi_loso"] = float(pr)
        t["hide_v2"] = hold.get(t["name"])
    inst = {}
    live = np.array([t["live"] for t in table])
    for key, sign in (("hide_v2", 1), ("sgmc_dti_gt300m", 1), ("sgmc_dti_gt500m", 1), ("n_dots", -1), ("far_gt1km", 1),
                      ("on_net15", 1), ("lfi_loso", 1)):
        vals = [(t[key], t["live"]) for t in table if t.get(key) is not None]
        x = np.array([v[0] for v in vals], float) * sign
        y = np.array([v[1] for v in vals], float)
        inst[key] = {"n": len(vals), "spearman_vs_live": round(float(spearmanr(x, y).statistic), 4),
                     "ci95_bootstrap": [round(v, 4) for v in boot_spearman(x, y)],
                     "sign_convention": "n_dots entered negated (fewer dots = higher expected score)" if sign < 0 else "as is"}

    # (b) H22-3 kill test on the fresh baseline refit AND on the stored S20 fit
    def dcat_effects(theta):
        keys = ["dcat=1", "dcat=1-2", "dcat=2-3", "dcat=3-5", "dcat=5-10", "dcat=10-20", "dcat=20-40", "dcat=>40"]
        return {k: round(float(np.exp(theta[k])), 3) for k in keys}

    stored = json.loads((ROOT / "docs/lfi/fit_r10.json").read_text())["theta"]
    eff_fresh, eff_stored = dcat_effects(theta_b), dcat_effects(stored)

    def killed(eff):
        near = float(np.mean([eff["dcat=1-2"], eff["dcat=2-3"], eff["dcat=3-5"]]))
        mid = float(np.mean([eff["dcat=5-10"], eff["dcat=10-20"]]))
        return {"mean_factor_(1,5]px": round(near, 3), "mean_factor_(5,20]px": round(mid, 3), "refuted": bool(mid >= near)}

    # (c) H22-2 factor test with site-jackknife interval on the hi-vs-lo log effect
    eff_hi = np.array([th[names_e.index("strike_mix=hi")] for th in ext_thetas.values()])
    n_s = len(eff_hi)
    jk_se = float(np.sqrt((n_s - 1) / n_s * np.sum((eff_hi - eff_hi.mean()) ** 2)))
    est = float(theta_e["strike_mix=hi"])
    h22_2 = {
        "factor_terciles_of_MO": [float(x) for x in qs2],
        "fitted_log_effect_hi_vs_lo": round(est, 4), "factor_hi_vs_lo": round(float(np.exp(est)), 3),
        "fitted_factor_mid_vs_lo": round(float(np.exp(theta_e["strike_mix=mid"])), 3),
        "site_jackknife_se": round(jk_se, 4), "ci95_log_effect": [round(est - 1.96 * jk_se, 4), round(est + 1.96 * jk_se, 4)],
        "ci95_excludes_0": bool(est - 1.96 * jk_se > 0 or est + 1.96 * jk_se < 0),
        "loso_rmse_baseline": round(base_rmse, 5), "loso_rmse_with_factor": round(ext_rmse, 5),
        "loso_spearman_baseline": round(base_sp, 4), "loso_spearman_with_factor": round(ext_sp, 4),
        "rmse_change": round(ext_rmse - base_rmse, 5),
    }
    # Amendment A2: H22-2 predicts MORE truth in orientation-mixing zones (hi > lo); a significant NEGATIVE effect is a
    # contradiction of the hypothesis, not support for it.
    lo_ci, hi_ci = h22_2["ci95_log_effect"]
    h22_2["direction"] = ("supports H22-2 (hi > lo)" if lo_ci > 0 else
                          "contradicts H22-2 (hi < lo)" if hi_ci < 0 else "inconclusive (interval includes 0)")
    h22_2["accepted"] = bool(h22_2["rmse_change"] <= 0.0005 and lo_ci > 0)

    out = {
        "evidence_class": "MODEL fitted to USER-REPORTED scores; never a score",
        "n_anchors": len(table), "ridge": RIDGE, "sites": int(np.unique(sites).size),
        "baseline_refit": {"loso_rmse": round(base_rmse, 5), "loso_spearman": round(base_sp, 4),
                           "stored_S20": {"loso_rmse": 0.019816, "loso_spearman": 0.957},
                           "note": "baseline = unchanged S20 design refit on the same anchors"},
        "instrument_validity": inst,
        "H22_3_damage_decay": {"fresh_refit_factors": eff_fresh, "stored_S20_factors": eff_stored,
                               "kill_test_fresh": killed(eff_fresh), "kill_test_stored": killed(eff_stored)},
        "H22_2_strike_discontinuity": h22_2,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (OUT / "instruments.json").write_text(json.dumps(out, indent=1) + "\n")
    with open(OUT / "anchor-table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    print(json.dumps({k: out[k] for k in ("baseline_refit", "instrument_validity", "H22_3_damage_decay",
                                           "H22_2_strike_discontinuity")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
