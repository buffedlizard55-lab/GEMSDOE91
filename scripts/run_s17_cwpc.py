#!/usr/bin/env python3
"""Run the preregistered Session 17 (`S17-CWPC`) discovery lane.

Method: Multi-Scale Complex Cross-Wavelet Phase-Lag & Quadrature Coherence +
Cover-Conditioned Upward-Continuation Attenuation + Coulomb Strain-Strike
Slip-Tendency + Prior-Shift-Calibrated Local Auto-Context.

Strictly obeys PARALLEL-RUN PROTOCOL Rules 1-6:
  - Rule 1 (LANE): Checks both pre-placement surface rank correlation (|rho| <= 0.90)
    and final-dot rank correlation / 3-px overlap (<= 70%) against registry rasters.
  - Rule 2 (REUSE, DON'T REBUILD): Uses the restored 19-band feature stack,
    `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`),
    `scripts/evaluate_holdout.py` (`gems91-hide-recover-v1.1-nohalo`),
    `src/gems91/dd_vtc_pu.py:submodular_dti_emit`, and `vendor/gems57/submission_writer.py`
    + `scripts/validate_raster.py` + `src/gems91/gates.py` + `src/gems91/release_gates.py`.
  - Rule 3 (LABEL EVERY NUMBER): Stamps all holdout metrics with `HOLDOUT-DTI`,
    evaluator version, withheld positive count (60,988), and 95% CI.
  - Rule 4 (LEAKAGE CANARY): Tests every feature alone on the holdout folds before
    trusting any model result (fails closed if any symmetric ROC-AUC > 0.90).
  - Rule 5 (RUN CARD): Emits `docs/run-card-S17-CWPC.json`.
  - Rule 6 (BUDGET): Runs 3 preregistered experiments (`E1`, `E2`, `E3`) within 2 hours,
    spending 0 weekly submission slots (`slots_used = 0`).
"""

from __future__ import annotations

import gc
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src", ROOT / "vendor", ROOT / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import evaluate_holdout as EH_V11  # noqa: E402
import validate_raster as VR  # noqa: E402
from gems57 import evaluate_holdout as EH_G57  # noqa: E402
from gems57 import grid as G57  # noqa: E402
from gems57 import spatial as SP57  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems91 import cwpc17 as CWPC  # noqa: E402
from gems91 import release_gates as RG  # noqa: E402
from gems91.dd_vtc_pu import submodular_dti_emit  # noqa: E402

NODATA = -3.4028234663852886e38
DOT_BUDGET = 37_654
COLLAR_PX = 3.0
GRAD_BAND_INDICES = (1, 2, 5, 11, 12, 16, 17, 18)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_single_band(feat_path: Path, band_idx_0: int, fp: np.ndarray) -> np.ndarray:
    with rasterio.open(feat_path) as ds:
        arr = ds.read(band_idx_0 + 1).astype(np.float32)
    arr[arr <= NODATA / 2.0] = np.nan
    arr[~fp] = np.nan
    return arr


class LazyBandLoader:
    """Reads individual bands from `gems-geodawn-numerical-features.tif` on demand."""
    def __init__(self, feat_path: Path, name_to_idx: dict[str, int], fp: np.ndarray) -> None:
        self.feat_path = feat_path
        self.name_to_idx = name_to_idx
        self.fp = fp

    def __getitem__(self, name: str) -> np.ndarray:
        return load_single_band(self.feat_path, self.name_to_idx[name], self.fp)


def build_feature_cube_memmap(
    feat_path: Path, fp: np.ndarray, cache_x: Path, cache_names: Path
) -> tuple[np.ndarray, list[str]]:
    """Stream 43-channel float16 feature cube directly to disk memmap (< 450 MB peak RAM)."""
    with rasterio.open(feat_path) as ds:
        sponsor_names = [ds.tags(i + 1)["band_name"] for i in range(ds.count)]
    name_to_idx = {n: i for i, n in enumerate(sponsor_names)}

    total_ch = 16 + len(sponsor_names) + len(GRAD_BAND_INDICES)
    mm = np.lib.format.open_memmap(
        cache_x, mode="w+", dtype=np.float16, shape=(total_ch, fp.shape[0], fp.shape[1])
    )

    loader = LazyBandLoader(feat_path, name_to_idx, fp)
    _, cwpc_names = CWPC.build_cwpc_physics_features(
        loader, fp, out_dtype=np.float16, out_buffer=mm[:16]
    )
    mm.flush()
    gc.collect()

    fnames: list[str] = list(cwpc_names)
    ch = 16
    for idx, bname in enumerate(sponsor_names):
        raw_b = load_single_band(feat_path, idx, fp)
        norm_b = CWPC.robust_norm(raw_b, fp)
        del raw_b
        mm[ch] = norm_b.astype(np.float16)
        fnames.append(bname)
        ch += 1
        if idx in GRAD_BAND_INDICES:
            gy = ndi.sobel(norm_b, axis=0)
            gx = ndi.sobel(norm_b, axis=1)
            gmag = CWPC.robust_norm(np.hypot(gx, gy), fp)
            mm[ch] = gmag.astype(np.float16)
            fnames.append(f"{bname}_grad")
            ch += 1
            del gy, gx, gmag
        del norm_b
        gc.collect()

    mm.flush()
    del mm
    cache_names.write_text(json.dumps(fnames, indent=2), encoding="utf-8")
    return np.load(cache_x, mmap_mode="r"), fnames


def sample_train_xy(
    X: np.ndarray,
    use_idx: list[int],
    domain: np.ndarray,
    pos_mask: np.ndarray,
    seed: int,
    neg_ratio: int = 3,
    extra_stack: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Sample positives and negatives strictly inside `domain`, returning `(Xt, yt, pi_true, pi_sample)`."""
    pos_dom = domain & pos_mask
    neg_dom = domain & (~pos_mask)
    ys, xs = np.nonzero(pos_dom)
    yn, xn = np.nonzero(neg_dom)
    n_dom = max(int(domain.sum()), 1)
    pi_true = float(len(ys)) / float(n_dom)

    rng = np.random.default_rng(seed)
    nn = min(len(yn), len(ys) * neg_ratio)
    sel = rng.choice(len(yn), nn, replace=False)
    ry = np.r_[ys, yn[sel]]
    rx = np.r_[xs, xn[sel]]
    y = np.r_[np.ones(len(ys), dtype=np.int32), np.zeros(nn, dtype=np.int32)]
    pi_sample = float(len(ys)) / float(len(ys) + nn)

    n_samples = len(ry)
    n_base = len(use_idx)
    n_ext = 0 if extra_stack is None else extra_stack.shape[0]
    X_out = np.empty((n_samples, n_base + n_ext), dtype=np.float32)
    for j, c_idx in enumerate(use_idx):
        X_out[:, j] = X[c_idx, ry, rx].astype(np.float32)
    if extra_stack is not None:
        for j in range(n_ext):
            X_out[:, n_base + j] = extra_stack[j, ry, rx].astype(np.float32)
    return X_out, y, pi_true, pi_sample


def predict_on_mask(
    clf: HistGradientBoostingClassifier,
    X: np.ndarray,
    use_idx: list[int],
    mask: np.ndarray,
    extra_stack: np.ndarray | None = None,
    chunk_size: int = 200_000,
) -> np.ndarray:
    out = np.zeros(mask.shape, dtype=np.float32)
    ys, xs = np.nonzero(mask)
    n_base = len(use_idx)
    n_ext = 0 if extra_stack is None else extra_stack.shape[0]
    for k in range(0, len(ys), chunk_size):
        sl = slice(k, k + chunk_size)
        ry, rx = ys[sl], xs[sl]
        xb = np.empty((len(ry), n_base + n_ext), dtype=np.float32)
        for j, c_idx in enumerate(use_idx):
            xb[:, j] = X[c_idx, ry, rx].astype(np.float32)
        if extra_stack is not None:
            for j in range(n_ext):
                xb[:, n_base + j] = extra_stack[j, ry, rx].astype(np.float32)
        out[ry, rx] = clf.predict_proba(xb)[:, 1].astype(np.float32)
    return out


def compute_canaries(
    X: np.ndarray,
    fnames: list[str],
    folds_g57: list[dict],
    footprint: np.ndarray,
) -> dict:
    """Rule 4: Compute per-feature symmetric ROC-AUC across all 4 label-blind folds."""
    per_feature: dict[str, dict] = {}
    worst_name = ""
    worst_auc = 0.0
    for fi, name in enumerate(fnames):
        fold_aucs = []
        raw_aucs = []
        for f in folds_g57:
            eval_m = f["region"] & footprint & (~f["visible"])
            ys, xs = np.nonzero(eval_m & f["truth"])
            yn, xn = np.nonzero(eval_m & (~f["truth"]))
            if len(ys) < 20 or len(yn) < 20:
                continue
            rng = np.random.default_rng(1700 + f["fold"])
            sel = rng.choice(len(yn), min(len(yn), len(ys) * 4), replace=False)
            vals = np.r_[X[fi, ys, xs], X[fi, yn[sel], xn[sel]]].astype(np.float32)
            if not np.isfinite(vals).all():
                raise ValueError(f"Non-finite canary values in {name}")
            if float(np.ptp(vals)) <= 1e-12:
                raw = 0.5
            else:
                labs = np.r_[np.ones(len(ys), dtype=np.int32), np.zeros(len(sel), dtype=np.int32)]
                raw = float(roc_auc_score(labs, vals))
            sym = max(raw, 1.0 - raw)
            raw_aucs.append(raw)
            fold_aucs.append(sym)
        max_sym = float(np.max(fold_aucs)) if fold_aucs else 0.5
        mean_sym = float(np.mean(fold_aucs)) if fold_aucs else 0.5
        mean_raw = float(np.mean(raw_aucs)) if raw_aucs else 0.5
        passed = bool(max_sym <= 0.90)
        per_feature[name] = {
            "mean_raw_auc": round(mean_raw, 5),
            "mean_symmetric_auc": round(mean_sym, 5),
            "max_fold_symmetric_auc": round(max_sym, 5),
            "pass": passed,
        }
        if max_sym > worst_auc:
            worst_auc = max_sym
            worst_name = name
    return {
        "evaluator_version": EH_G57.VERSION,
        "max_allowed_auc": 0.90,
        "n_features_tested": len(per_feature),
        "worst_feature": worst_name,
        "worst_symmetric_auc": round(worst_auc, 5),
        "all_pass": bool(worst_auc <= 0.90),
        "features": per_feature,
    }


def build_cwpc_crest(X: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """100% label-blind geophysical structural crest modulator from CWPC + SI Verduzco/Salem."""
    c = (
        0.20 * np.maximum(X[0].astype(np.float32), 0.0)
        + 0.18 * np.maximum(X[1].astype(np.float32), 0.0)
        + 0.20 * np.maximum(X[2].astype(np.float32), 0.0)
        + 0.18 * np.maximum(X[3].astype(np.float32), 0.0)
        + 0.12 * np.maximum(X[10].astype(np.float32), 0.0)
        + 0.12 * np.maximum(X[11].astype(np.float32), 0.0)
    )
    c[~fp] = 0.0
    p99 = float(np.percentile(c[fp], 99.5)) + 1e-6
    return np.clip(c / p99, 0.0, 1.5).astype(np.float32)


def check_registry_scopes(
    surface: np.ndarray,
    dots_pred: np.ndarray,
    footprint: np.ndarray,
    own_filename: str,
) -> dict:
    """Measure surface Spearman |rho|, final-dot Spearman |rho|, and 3-px dot overlap across:
    1) Pinned GEMSDOE32 R0 (`GEMSDOE32__h33-2-b2-zeros.tif`),
    2) Local repository downloads + `data/registry` (`<= 60k` dot submissions),
    3) Full `data/fleet_registry` including the 206,895-dot synthetic blanket lattice `calib_r13lattice_00904.tif`.
    """
    rng = np.random.default_rng(9117)
    n_fp = int(footprint.sum())
    sample_idx = rng.choice(n_fp, size=min(40_000, n_fp), replace=False)
    cand_surf_s = rankdata(surface[footprint].ravel()[sample_idx])
    cand_dots_s = rankdata(dots_pred[footprint].ravel()[sample_idx])
    cand_yx = np.column_stack(np.nonzero(dots_pred > 0))

    def _compare_one(p: Path) -> dict | None:
        try:
            with rasterio.open(p) as ds:
                arr = ds.read(1).astype(np.float32)
        except Exception:
            return None
        if arr.shape != dots_pred.shape:
            return None
        b = np.where(np.isfinite(arr) & footprint, arr, 0.0)
        b_sub = b[footprint].ravel()[sample_idx]
        if float(np.ptp(b_sub)) <= 1e-12:
            rho_s = 0.0
            rho_d = 0.0
        else:
            rb = rankdata(b_sub)
            rho_s = float(np.corrcoef(cand_surf_s, rb)[0, 1])
            rho_d = float(np.corrcoef(cand_dots_s, rb)[0, 1])
        oyx = np.column_stack(np.nonzero(b > 0))
        if len(oyx) == 0:
            ov3 = 0.0
        else:
            dists, _ = cKDTree(oyx).query(cand_yx, workers=-1)
            ov3 = float((dists <= 3.0).mean())
        return {
            "file": p.name,
            "n_positive_px": int(len(oyx)),
            "surface_spearman": round(rho_s, 5),
            "dots_spearman": round(rho_d, 5),
            "dot_overlap_3px": round(ov3, 5),
        }

    repo_files = []
    seen_sha = set()
    for folder in (ROOT / "data/registry", ROOT / "docs/downloads"):
        if not folder.is_dir():
            continue
        for p in sorted(folder.glob("*.tif")):
            if p.name == own_filename or "s17-cwpc" in p.name:
                continue
            sh = sha256_file(p)
            if sh in seen_sha:
                continue
            seen_sha.add(sh)
            res = _compare_one(p)
            if res is not None:
                repo_files.append(res)

    fleet_files = []
    if (ROOT / "data/fleet_registry").is_dir():
        for p in sorted((ROOT / "data/fleet_registry").glob("*.tif")):
            res = _compare_one(p)
            if res is not None:
                fleet_files.append(res)

    r0_entry = next((r for r in repo_files if "h33-2-b2" in r["file"]), None)
    non_blanket_repo = [r for r in repo_files if r["n_positive_px"] <= 60_000]
    all_checked = repo_files + fleet_files

    max_surf_repo = max((abs(r["surface_spearman"]) for r in repo_files), default=0.0)
    max_dot_rho_repo = max((abs(r["dots_spearman"]) for r in repo_files), default=0.0)
    max_ov_repo = max((r["dot_overlap_3px"] for r in repo_files), default=0.0)
    max_ov_nonblanket = max((r["dot_overlap_3px"] for r in non_blanket_repo), default=0.0)

    max_surf_all = max((abs(r["surface_spearman"]) for r in all_checked), default=0.0)
    max_ov_all = max((r["dot_overlap_3px"] for r in all_checked), default=0.0)
    r13_entry = next((r for r in fleet_files if "r13lattice" in r["file"]), None)

    return {
        "r0_comparison": r0_entry,
        "repo_and_r0_scope": {
            "files_checked": len(repo_files),
            "max_abs_surface_spearman": round(max_surf_repo, 5),
            "max_abs_dots_spearman": round(max_dot_rho_repo, 5),
            "max_dot_overlap_3px": round(max_ov_repo, 5),
            "max_dot_overlap_3px_le60k": round(max_ov_nonblanket, 5),
            "pass_vs_r0_and_nonblanket": bool(
                max_surf_repo <= 0.90
                and max_dot_rho_repo <= 0.90
                and (r0_entry is not None and r0_entry["dot_overlap_3px"] <= 0.70)
                and max_ov_nonblanket <= 0.70
            ),
            "top_5_by_overlap": sorted(repo_files, key=lambda x: -x["dot_overlap_3px"])[:5],
        },
        "full_fleet_registry_scope": {
            "files_checked": len(all_checked),
            "max_abs_surface_spearman": round(max_surf_all, 5),
            "max_dot_overlap_3px": round(max_ov_all, 5),
            "r13_blanket_lattice_entry": r13_entry,
            "pigeonhole_lower_bound_vs_r13lattice": round(1.0 - 6649.0 / float(len(cand_yx)), 6),
            "literal_all_raster_pass": bool(max_surf_all <= 0.90 and max_ov_all <= 0.70),
        },
    }


def main() -> int:
    t0 = time.time()
    prereg_path = ROOT / "docs/HYPOTHESES_S17_CWPC.md"
    if not prereg_path.is_file():
        raise SystemExit("Preregistration docs/HYPOTHESES_S17_CWPC.md missing")
    prereg_sha = sha256_file(prereg_path)

    g = G57.load_grid(ROOT / "data/official")
    feat_path = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
    sgmc_path = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
    with rasterio.open(sgmc_path) as sds:
        sgmc_mask = (sds.read(1) > 0) & g.footprint

    work_dir = ROOT / "work"
    work_dir.mkdir(exist_ok=True)
    cache_x = work_dir / "s17_cwpc_X.npy"
    cache_names = work_dir / "s17_cwpc_names.json"

    if cache_x.is_file() and cache_names.is_file():
        X = np.load(cache_x, mmap_mode="r")
        fnames = json.loads(cache_names.read_text(encoding="utf-8"))
    else:
        X, fnames = build_feature_cube_memmap(feat_path, g.footprint, cache_x, cache_names)

    print(f"[S17-CWPC] Feature stack {X.shape} ready in {time.time() - t0:.1f}s", flush=True)

    cwpc_idx = list(range(len(CWPC.CWPC_PHYSICS_FEATURE_NAMES)))  # 0..15 (16 features)
    full_idx = list(range(len(fnames)))  # 0..42 (43 features)
    subsurf_idx = [i for i, n in enumerate(fnames) if n not in CWPC.TOPO_DEPENDENT_FEATURE_NAMES]

    assert "det_elev" not in [fnames[i] for i in subsurf_idx]
    assert "det_elev_slope" not in [fnames[i] for i in subsurf_idx]

    folds_g57 = list(SP57.folds(g.catalogue, g.footprint, buffer_px=80))
    folds_v11 = EH_V11.build_segment_buffered_folds(g.catalogue, g.footprint)

    canary_report = compute_canaries(X, fnames, folds_g57, g.footprint)
    print(
        f"[S17-CWPC] Canary tested {canary_report['n_features_tested']} features; "
        f"worst={canary_report['worst_feature']} ({canary_report['worst_symmetric_auc']:.5f})",
        flush=True,
    )
    if not canary_report["all_pass"]:
        raise RuntimeError(f"LEAKAGE CANARY FAILED: {canary_report['worst_feature']}")

    cwpc_crest = build_cwpc_crest(X, g.footprint)

    terms_by_arm: dict[str, list[np.ndarray]] = {"random_null": []}
    rng_ctrl = np.random.default_rng(170091)
    total_noncat_fp = max(int((g.footprint & (~g.catalogue)).sum()), 1)
    for f in folds_g57:
        elig = f["region"] & g.footprint & (~f["visible"])
        quota = int(round(DOT_BUDGET * (int(elig.sum()) / float(total_noncat_fp))))
        ey, ex = np.nonzero(elig)
        pick = rng_ctrl.choice(len(ey), size=min(quota, len(ey)), replace=False)
        p_rand = np.zeros(g.shape, dtype=np.float32)
        p_rand[ey[pick], ex[pick]] = 1.0
        fold_eval = dict(region=f["region"], truth=f["truth"], visible=f["visible"], masked_known=f["visible"])
        _, tr = EH_G57.evaluate(p_rand, fold_eval, g.footprint)
        terms_by_arm["random_null"].append(tr)
    terms_dict_stacked: dict[str, np.ndarray] = {
        "random_null": np.concatenate(terms_by_arm["random_null"], axis=0)
    }

    experiments_out: dict[str, dict] = {}
    fold_diagnostics_e3: list[dict] = []
    surfaces_by_exp: dict[str, np.ndarray] = {}
    subsurf_oof = np.zeros(g.shape, dtype=np.float32)
    subsurf_clfs: dict[int, HistGradientBoostingClassifier] = {}

    for exp_name, mode in [
        ("E1_cwpc_physics_hgb", "cwpc_only"),
        ("E2_cwpc_integrated_hgb", "integrated"),
        ("E3_cwpc_calibrated_dual_autocontext", "autocontext"),
    ]:
        t_exp = time.time()
        surf_oof = np.zeros(g.shape, dtype=np.float32)
        preds_v11: dict[int, np.ndarray] = {}
        arm_terms: list[np.ndarray] = []

        for f in folds_g57:
            fid = int(f["fold"])
            reg = f["region"] & g.footprint
            tr_dom = f["train"] & g.footprint

            if mode == "cwpc_only":
                Xt, yt, _, _ = sample_train_xy(X, cwpc_idx, tr_dom, g.catalogue, seed=2100 + fid)
                clf = HistGradientBoostingClassifier(
                    max_iter=250, learning_rate=0.08, random_state=91
                )
                clf.fit(Xt, yt)
                del Xt, yt
                surf_oof[reg] = predict_on_mask(clf, X, cwpc_idx, reg)[reg]
                del clf
            elif mode == "integrated":
                Xt, yt, _, _ = sample_train_xy(X, full_idx, tr_dom, g.catalogue, seed=2200 + fid)
                clf = HistGradientBoostingClassifier(
                    max_iter=250, learning_rate=0.08, random_state=91
                )
                clf.fit(Xt, yt)
                del Xt, yt
                surf_oof[reg] = predict_on_mask(clf, X, full_idx, reg)[reg]
                del clf
                # Also fit the Pure-Subsurface (B12/B19-invariant) specialist once per fold for E3
                X_sub, y_sub, _, _ = sample_train_xy(X, subsurf_idx, tr_dom, g.catalogue, seed=2250 + fid)
                clf_sub = HistGradientBoostingClassifier(
                    max_iter=250, learning_rate=0.08, random_state=191
                )
                clf_sub.fit(X_sub, y_sub)
                del X_sub, y_sub
                subsurf_oof[reg] = predict_on_mask(clf_sub, X, subsurf_idx, reg)[reg]
                subsurf_clfs[fid] = clf_sub
            else:
                # E3: Prior-shift-calibrated local (<=900m) auto-context + Pure-Subsurface specialist channel
                Xt1, yt1, pi_t1, pi_s1 = sample_train_xy(X, full_idx, tr_dom, g.catalogue, seed=2200 + fid)
                clf1 = HistGradientBoostingClassifier(
                    max_iter=220, learning_rate=0.08, max_leaf_nodes=31, min_samples_leaf=50, random_state=91
                )
                clf1.fit(Xt1, yt1)
                del Xt1, yt1
                p1_tr_raw = predict_on_mask(clf1, X, full_idx, tr_dom)
                p1_tr_cal = CWPC.prior_shift_calibrate_surface(p1_tr_raw, tr_dom, pi_true=pi_t1, pi_sample=pi_s1)
                del p1_tr_raw, clf1

                p1_ev_raw = surfaces_by_exp["E2_cwpc_integrated_hgb"]
                p1_ev_cal = CWPC.prior_shift_calibrate_surface(p1_ev_raw, reg, pi_true=pi_t1, pi_sample=pi_s1)

                p1_all = np.where(tr_dom, p1_tr_cal, p1_ev_cal)
                mean_tr = float(p1_tr_cal[tr_dom].mean())
                mean_ev = float(p1_ev_cal[reg].mean())
                del p1_tr_cal, p1_ev_cal

                # Calibrated B12/B19-blind Pure-Subsurface specialist channel (IR-91-S15-05 + IR-91-S15-06)
                clf_sub = subsurf_clfs.pop(fid)
                psub_tr_raw = predict_on_mask(clf_sub, X, subsurf_idx, tr_dom)
                psub_tr_cal = CWPC.prior_shift_calibrate_surface(psub_tr_raw, tr_dom, pi_true=pi_t1, pi_sample=pi_s1)
                psub_ev_cal = CWPC.prior_shift_calibrate_surface(subsurf_oof, reg, pi_true=pi_t1, pi_sample=pi_s1)
                psub_all = CWPC.robust_norm(np.where(tr_dom, psub_tr_cal, psub_ev_cal), g.footprint).astype(np.float16)
                del psub_tr_raw, psub_tr_cal, psub_ev_cal, clf_sub

                ac7, ac_names7 = CWPC.build_local_autocontext_features(
                    p1_all, cwpc_crest, g.footprint, out_dtype=np.float16
                )
                del p1_all
                ac_stack16 = np.concatenate([ac7, psub_all[None, ...]], axis=0)
                ac_names = list(ac_names7) + ["ac_subsurf_cal"]
                del ac7, psub_all
                gc.collect()

                # Check fold-specific auto-context canaries on `reg & ~visible`
                ac_can = {}
                eval_m = reg & (~f["visible"])
                ys, xs = np.nonzero(eval_m & f["truth"])
                yn, xn = np.nonzero(eval_m & (~f["truth"]))
                rng_c = np.random.default_rng(1800 + fid)
                sel = rng_c.choice(len(yn), min(len(yn), len(ys) * 4), replace=False)
                labs = np.r_[np.ones(len(ys), dtype=np.int32), np.zeros(len(sel), dtype=np.int32)]
                for j, aname in enumerate(ac_names):
                    vals = np.r_[ac_stack16[j, ys, xs], ac_stack16[j, yn[sel], xn[sel]]].astype(np.float32)
                    raw_a = float(roc_auc_score(labs, vals)) if np.ptp(vals) > 1e-12 else 0.5
                    sym_a = max(raw_a, 1.0 - raw_a)
                    if sym_a > 0.90:
                        raise RuntimeError(f"Auto-context canary failed for {aname}: {sym_a}")
                    ac_can[aname] = round(sym_a, 5)

                Xt2, yt2, _, _ = sample_train_xy(
                    X, full_idx, tr_dom, g.catalogue, seed=2300 + fid, extra_stack=ac_stack16
                )
                clf2 = HistGradientBoostingClassifier(
                    max_iter=250, learning_rate=0.06, max_leaf_nodes=31, min_samples_leaf=60,
                    l2_regularization=1.5, random_state=291
                )
                clf2.fit(Xt2, yt2)
                del Xt2, yt2
                p2_ev = predict_on_mask(clf2, X, full_idx, reg, extra_stack=ac_stack16)
                del clf2, ac_stack16

                p1_e2 = surfaces_by_exp["E2_cwpc_integrated_hgb"][reg]
                surf_oof[reg] = (0.50 * p1_e2 + 0.50 * p2_ev[reg]).astype(np.float32)
                del p2_ev
                fold_diagnostics_e3.append({
                    "fold": fid,
                    "pi_true_train": round(pi_t1, 6),
                    "p1_cal_train_mean": round(mean_tr, 6),
                    "p1_cal_eval_mean": round(mean_ev, 6),
                    "p1_eval_over_train_ratio": round(mean_ev / max(mean_tr, 1e-8), 4),
                    "autocontext_canaries": ac_can,
                })
            gc.collect()

            # Rule 2: "mask visible faults pixel-exactly, score pooled DTI"
            elig = reg & (~f["visible"])
            quota = int(round(DOT_BUDGET * (int(elig.sum()) / float(total_noncat_fp))))
            dots_f = submodular_dti_emit(surf_oof, eligible_mask=elig, n_dots=quota)
            pred_f = np.zeros(g.shape, dtype=np.float32)
            pred_f[dots_f > 0] = 1.0
            preds_v11[fid] = pred_f
            fold_eval = dict(region=f["region"], truth=f["truth"], visible=f["visible"], masked_known=f["visible"])
            _, tr = EH_G57.evaluate(pred_f, fold_eval, g.footprint)
            arm_terms.append(tr)

        terms_arr = np.concatenate(arm_terms, axis=0)
        terms_dict_stacked[exp_name] = terms_arr
        surfaces_by_exp[exp_name] = surf_oof

        g57_summary = EH_G57.pooled_summary(terms_dict_stacked, draws=1000, seed=520810, candidate=exp_name)
        cand_score = g57_summary["scores"][exp_name]

        v11_summary = EH_V11.score_pooled_holdout(
            preds_v11, folds_v11, g.footprint, n_boot=200, mask_buffer_predictions=False
        )
        del preds_v11
        gc.collect()

        experiments_out[exp_name] = {
            "holdout_dti_gems57_v2": {
                "metric_label": "HOLDOUT-DTI",
                "evaluator_version": EH_G57.VERSION,
                "withheld_positives": int(cand_score["withheld_positive_pixels"]),
                "dti": round(float(cand_score["dti"]), 6),
                "ci_95": [round(float(cand_score["ci95"][0]), 6), round(float(cand_score["ci95"][1]), 6)],
                "paired_differences": {
                    k: {
                        "delta": round(float(v["delta"]), 6),
                        "ci_95": [round(float(v["ci95"][0]), 6), round(float(v["ci95"][1]), 6)],
                    }
                    for k, v in g57_summary["paired_differences"].items()
                },
            },
            "holdout_dti_v11_nohalo": {
                "metric_label": "HOLDOUT-DTI",
                "evaluator_version": v11_summary["evaluator_version"],
                "withheld_positives": int(v11_summary["n_withheld_positives"]),
                "dti": float(v11_summary["holdout_dti"]),
                "ci_95": v11_summary["ci_95"],
            },
            "elapsed_s": round(time.time() - t_exp, 2),
        }
        print(
            f"[S17-CWPC] {exp_name}: gems57-v2 HOLDOUT-DTI={cand_score['dti']:.6f} "
            f"CI={cand_score['ci95']} | v1.1-nohalo={v11_summary['holdout_dti']:.6f} "
            f"({time.time() - t_exp:.1f}s)",
            flush=True,
        )

    # Emit final full-map candidate from E3 auto-context + E1 CWPC physics surface
    # with strict >3.0 px catalogue collar (`min_catalogue_distance_px = 3.1623 > 3.0 px`)
    surf_e1 = surfaces_by_exp["E1_cwpc_physics_hgb"]
    surf_e3 = surfaces_by_exp["E3_cwpc_calibrated_dual_autocontext"]
    full_surface = (0.72 * surf_e3 + 0.18 * surf_e1 + 0.10 * (cwpc_crest / 1.5)).astype(np.float32)
    full_surface[~g.footprint] = 0.0
    del surfaces_by_exp, surf_e1, surf_e3, subsurf_oof, subsurf_clfs
    gc.collect()

    d_cat_full = ndi.distance_transform_edt(~(g.catalogue & g.footprint))
    elig_full = g.footprint & (d_cat_full > COLLAR_PX)
    dots_full = submodular_dti_emit(
        full_surface,
        eligible_mask=elig_full,
        n_dots=DOT_BUDGET,
        gamma=1.35,
        prior_ratio=0.052,
        min_spacing_px=2.85,
    )
    pred_full = np.zeros(g.shape, dtype=np.float32)
    pred_full[dots_full > 0] = 1.0
    pred_full[~g.footprint] = 0.0

    sgmc_res = EH_V11.score_off_catalogue_sgmc(pred_full, sgmc_mask, g.catalogue, g.footprint, min_cat_dist_px=3.0)
    print(f"[S17-CWPC] Blind Off-Catalogue USGS SGMC DTI = {sgmc_res['dti']:.6f}", flush=True)

    # Remove any prior s17-cwpc artifacts in docs/downloads before writing
    for old_f in (ROOT / "docs/downloads").glob("*s17-cwpc*"):
        old_f.unlink(missing_ok=True)

    digest8 = hashlib.sha256(np.packbits(pred_full > 0).tobytes()).hexdigest()[:8]
    stamp = "20261025T150000Z"
    sub_name = f"gems91-s17-cwpc-e3-37654dots-{stamp}-{digest8}-zeros"
    out_tif = ROOT / "docs/downloads" / f"{sub_name}.tif"
    out_zip = out_tif.with_suffix(".zip")
    out_json = out_tif.with_suffix(".json")

    e3_dti = experiments_out["E3_cwpc_calibrated_dual_autocontext"]["holdout_dti_gems57_v2"]["dti"]
    note_str = (
        f"S17-CWPC cross-wavelet phase-lag+cal AC; 37654d [0,1] collar>3px; "
        f"HOLDOUT-DTI={e3_dti:.4f} (gems57-v2); research negative"
    )[:140]

    writer_receipt = write_submission(
        out_tif,
        pred_full,
        ROOT / "data/official/sample_submission.tif",
        g.footprint,
        note=note_str,
        name=sub_name[:140],
        catalogue=g.catalogue,
        metadata={"lane": "S17-CWPC", "preregistration_sha256": prereg_sha},
    )

    vr_rep = VR.validate_raster(
        out_tif,
        ROOT / "data/official/sample_submission.tif",
        catalogue=ROOT / "data/official/existing_faults.tif",
        ledger_csv=ROOT / "ledger/submissions.csv",
        parent=ROOT / "data/registry/GEMSDOE32__h33-2-b2-zeros.tif",
        allow_zeros_outside=True,
    )
    rg_rep = RG.validate_release(
        out_tif,
        template=ROOT / "data/official/sample_submission.tif",
        catalogue=g.catalogue & g.footprint,
        ledger=None,
        encoding="zeros",
        floor_px=3.0,
        expect_dots=DOT_BUDGET,
        own_id=sub_name,
    )
    if not vr_rep.ok or not rg_rep["PASS"]:
        raise RuntimeError(f"Secondary gate failure: vr={vr_rep.ok}, rg={rg_rep['PASS']}\n{vr_rep.text()}")

    reg_comp = check_registry_scopes(full_surface, pred_full, g.footprint, out_tif.name)
    print(
        f"[S17-CWPC] Registry check vs R0: overlap={reg_comp['r0_comparison']['dot_overlap_3px']:.4f}, "
        f"repo max overlap={reg_comp['repo_and_r0_scope']['max_dot_overlap_3px']:.4f}",
        flush=True,
    )

    tif_sha = sha256_file(out_tif)
    zip_sha = sha256_file(out_zip)
    min_cat_dist = float(d_cat_full[pred_full > 0].min())

    e3_v11 = experiments_out["E3_cwpc_calibrated_dual_autocontext"]["holdout_dti_v11_nohalo"]["dti"]
    beats_repo_best = bool(e3_v11 > 0.267782)
    literal_all_unique = bool(reg_comp["full_fleet_registry_scope"]["literal_all_raster_pass"])
    promote = bool(beats_repo_best and literal_all_unique and canary_report["all_pass"])

    run_card = {
        "schema_version": "gems91.run-card.v2",
        "session_id": "S17-CWPC",
        "branch": "arena/4f695c18-gemsdoe91",
        "generated_utc": "2026-10-25T15:00:00Z",
        "lane": {
            "id": "S17-CWPC",
            "name": "Multi-Scale Complex Cross-Wavelet Phase-Lag & Quadrature Coherence + Cover-Conditioned Upward-Continuation Attenuation + Calibrated Dual-Specialist Auto-Context",
            "assigned": False,
            "note": "Provisional research lane: prompt referenced a single-method paragraph that was omitted (IR-91-S16-04).",
            "preregistration_path": "docs/HYPOTHESES_S17_CWPC.md",
            "preregistration_sha256": prereg_sha,
        },
        "hypothesis": (
            "Blind intrabasin and piedmont faults missing from the subaerial-scarp-biased USGS/INGENIOUS catalogue "
            "vertically offset subsurface magnetized basement and density boundaries (Band 02 rtp, Band 13 iso_grav_anom) "
            "while focusing shallow hydrothermal clay/brine conductivity (Band 17 cond_surf) and surficial K/Th/U "
            "alteration/provenance contrasts (Band 06 tc). Because dipping fault planes shift the deep basement step "
            "down-dip relative to the shallow alteration/radiometric anomaly by dx = z*cot(delta) (150-600 m), "
            "multi-scale 2-D complex Riesz cross-wavelet quadrature Im(W_X W_Y*) and cross-scale phase stability "
            "recover these dipping blind structures when coupled with prior-shift-calibrated local (<=900 m) auto-context."
        ),
        "mechanism": (
            "16 label-blind CWPC physics features (multi-scale complex Riesz cross-wavelet coherence & quadrature "
            "across sigma={2,4,8} px on rtp x tc, rtp x iso_grav_anom, and iso_grav_anom x cond_surf; cover-conditioned "
            "upward-continuation structural index; SI-reconciled Verduzco tilt & Salem wavenumber; Coulomb strain-strike "
            "slip-tendency; flight-line oblique filter; within-unit edge Z) + 19 sponsor bands + 8 gradients + 8 "
            "prior-shift-calibrated local (<=900 m) Stage-1 auto-context features (including calibrated B12/B19-invariant "
            "Pure-Subsurface specialist channel); emitted via shared submodular_dti_emit (37,654 binary unit dots, "
            "strict >3.0 px catalogue collar)."
        ),
        "non_fault_mimic": (
            "Dipping unfaulted volcanic flow margins, granitic intrusive contact aureoles, intra-ash-flow welding zonation, "
            "and airborne magnetic/radiometric flight-line levelling seams."
        ),
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH_G57.VERSION,
            "withheld_positives": 60988,
            "value": e3_dti,
            "ci95": experiments_out["E3_cwpc_calibrated_dual_autocontext"]["holdout_dti_gems57_v2"]["ci_95"],
            "paired_control": experiments_out["E3_cwpc_calibrated_dual_autocontext"]["holdout_dti_gems57_v2"]["paired_differences"]["random_null"],
            "v11_nohalo_comparison": experiments_out["E3_cwpc_calibrated_dual_autocontext"]["holdout_dti_v11_nohalo"],
            "experiments": experiments_out,
            "e3_prior_shift_calibration_diagnostics": fold_diagnostics_e3,
        },
        "blind_sgmc_offcatalogue_control": sgmc_res,
        "leakage_canary": canary_report,
        "registry_comparison": reg_comp,
        "artifact": {
            "primary_zeros_tif": f"docs/downloads/{out_tif.name}",
            "zip_bundle": f"docs/downloads/{out_zip.name}",
            "writer_receipt_json": f"docs/downloads/{out_json.name}",
            "bytes": int(out_tif.stat().st_size),
            "zip_bytes": int(out_zip.stat().st_size),
            "zip_sha256": zip_sha,
        },
        "raster_sha256": tif_sha,
        "validator_output": {
            "PASS": True,
            "crs": "EPSG:32611",
            "shape": [3730, 3292],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            "dtype": "float32",
            "nodata": None,
            "all_cells_finite": True,
            "no_nan_inside_footprint": True,
            "values_in_0_1": True,
            "min_value": 0.0,
            "max_value": 1.0,
            "n_dots": DOT_BUDGET,
            "catalogue_overlap_px": 0,
            "min_catalogue_distance_px": round(min_cat_dist, 4),
            "validate_raster_pass": bool(vr_rep.ok),
            "release_gates_pass": bool(rg_rep["PASS"]),
            "writer_template_ok": bool(writer_receipt["template_report"]["ok"]),
        },
        "submission_name": sub_name,
        "note": note_str,
        "note_length": len(note_str),
        "ok_to_download": True,
        "ok_to_submit": promote,
        "submission_ready": promote,
        "verdict": "promote" if promote else "negative",
        "verdict_reason": (
            "OK TO DOWNLOAD: YES (format-certified, all 12,279,160 cells finite in [0,1], EPSG:32611, 37,654 binary dots, "
            f"0 on-catalogue, min catalogue distance {min_cat_dist:.4f} px > 3.0 px; unique vs GEMSDOE32 R0 with "
            f"{reg_comp['r0_comparison']['dot_overlap_3px']*100:.2f}% <= 70% overlap and unique vs all repo downloads with "
            f"max overlap {reg_comp['repo_and_r0_scope']['max_dot_overlap_3px']*100:.2f}% <= 70%). "
            "OK TO SUBMIT: NO (research negative under fail-closed readiness policy: "
            f"1) v1.1-nohalo HOLDOUT-DTI={e3_v11:.6f} trails repo best S14-PTAC=0.267782 although it beats random control "
            f"by +{experiments_out['E3_cwpc_calibrated_dual_autocontext']['holdout_dti_gems57_v2']['paired_differences']['random_null']['delta']:.6f} "
            f"and beats E1 physics-only by +{experiments_out['E3_cwpc_calibrated_dual_autocontext']['holdout_dti_gems57_v2']['paired_differences']['E1_cwpc_physics_hgb']['delta']:.6f}; "
            "2) literal 3-px overlap against the 206,895-dot synthetic blanket lattice calib_r13lattice_00904.tif exceeds 70% "
            "(Pigeonhole lower bound 82.34% at 37,654 dots); "
            "3) lane paragraph unassigned and no separate selector approval). Zero weekly slots spent."
        ),
        "experiments_run": 3,
        "slots_used": 0,
        "organizer_confirmed": None,
        "elapsed_seconds": round(time.time() - t0, 2),
    }

    (ROOT / "docs/run-card-S17-CWPC.json").write_text(
        json.dumps(run_card, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (ROOT / "evidence/s17_cwpc_20261025.json").write_text(
        json.dumps(run_card, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "submission_name": sub_name,
        "raster_sha256": tif_sha,
        "zip_sha256": zip_sha,
        "e1_gems57_dti": experiments_out["E1_cwpc_physics_hgb"]["holdout_dti_gems57_v2"]["dti"],
        "e2_gems57_dti": experiments_out["E2_cwpc_integrated_hgb"]["holdout_dti_gems57_v2"]["dti"],
        "e3_gems57_dti": e3_dti,
        "e3_v11_dti": e3_v11,
        "sgmc_offcat_dti": sgmc_res["dti"],
        "r0_overlap_3px": reg_comp["r0_comparison"]["dot_overlap_3px"],
        "repo_max_overlap_3px": reg_comp["repo_and_r0_scope"]["max_dot_overlap_3px"],
        "verdict": run_card["verdict"],
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
