#!/usr/bin/env python3
"""Session 21 (`S21-PDWC`) End-to-End Preregistered Runner & Automated Gate Suite.

Executes the frozen preregistration in `docs/HYPOTHESES_S21_PDWC.md` (`<= 3` experiments,
`< 2` hours wall-clock, `0` weekly slots spent):
  1. Verifies immutable SHA-256 pins of `vendor/gems57/*` against `registry/template_pin.json`.
  2. Builds/loads the disk-backed `(5,167,373, 66)` `float16` `PDWC21` static physics
     feature cube (`48` Pure-Subsurface + `18` Topographic; verified bitwise `0.0`
     `Band 12/19` invariance).
  3. Runs Protocol Rule 4 single-feature leakage canary (`<= 0.90` symmetric ROC-AUC
     pooled and per quadrant) on all `66` static + `16` Stage-2 features (`82` total).
  4. Runs 3-level nested symmetric cross-fitting across the 4 spatial quadrants
     (`split_sha256 = c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a`)
     so BOTH training quadrants and test quadrants are 100% Out-of-Fold during global
     `37,654` placement (curing `IR-S21-02`), and evaluates exact `HOLDOUT-DTI` via
     unchanged `vendor/gems57/evaluate_holdout.py` (`evaluate` + `pooled_summary`).
  5. Emits the unique all-finite `-zeros.tif` + `-zeros.zip` via unchanged
     `vendor/gems57/submission_writer.py`, runs full automated format/range/uniqueness/
     blind-SGMC/LFI-surrogate audits across `registry + downloads + 1,072 sibling rasters`,
     and writes `docs/run-card-S21-PDWC.json` + `docs/s21_pdwc/*.json`.
"""

from __future__ import annotations

import csv
import gc
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

for _k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_k, "2")

import numpy as np
import rasterio
import tifffile
from scipy import ndimage as ndi
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout as eh  # noqa: E402
from gems57 import gates as g57_gates  # noqa: E402
from gems57 import spatial as g57_spatial  # noqa: E402
from gems57.metric import dti_binary  # noqa: E402
from gems57.submission_writer import write_submission  # noqa: E402
from gems91.pdwc21 import (  # noqa: E402
    PDWC21_AC_NAMES,
    PDWC21_FEATURE_NAMES,
    PDWC21_SUBSURFACE_NAMES,
    build_ac_memmap,
    build_or_load_pdwc21_memmap,
    compute_pdwc_crest_backbone_fp,
    compute_subsurface_backbone_fp,
    emit_dots_celf_submodular,
    emit_dots_nms,
    fit_predict_pdwc_specialist,
    pool_asymmetric_cover_rescue,
)
from gems91.readiness import submission_ready  # noqa: E402
from gems91.release_gates import validate_release  # noqa: E402

SAMPLE_TIF = ROOT / "data/official/sample_submission.tif"
EXISTING_FAULTS_TIF = ROOT / "data/official/existing_faults.tif"
FEATURES_TIF = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
GDR_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"
SGMC_TIF = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
CATALOGUE_MASK_TIF = ROOT / "data/derived/catalogue_mask.tif"

CACHE_DIR = ROOT / "data/derived/s21_pdwc_cache"
EVIDENCE_DIR = ROOT / "docs/s21_pdwc"
DOWNLOADS_DIR = ROOT / "docs/downloads"

EXPECTED_SPLIT_SHA256 = "c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a"
BUFFER_PX = 80
DOT_BUDGET = 37_654
COLLAR_PX = 3.05
UNIQUENESS_CAP = 0.64


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_template_pins() -> dict[str, str]:
    pin = json.loads((ROOT / "registry/template_pin.json").read_text())
    src_prefix = pin.get("source_path", "vendor/gems57/")
    out = {}
    for fname, exp_sha in pin["sha256"].items():
        rel = f"{src_prefix}{fname}"
        got = sha256_file(ROOT / rel)
        if got != exp_sha:
            raise RuntimeError(f"Immutable template pin mismatch on {rel}: {got} != {exp_sha}")
        out[rel] = got
    return out


def compute_split_sha(folds: list[dict]) -> str:
    return hashlib.sha256(
        b"".join(
            np.packbits(f[k].ravel()).tobytes()
            for f in folds
            for k in ("region", "truth", "train", "visible")
        )
    ).hexdigest()


def run_feature_canary(
    X_mm: np.ndarray,
    feature_names: list[str],
    folds: list[dict],
    footprint: np.ndarray,
    *,
    stride: int = 8,
) -> dict[str, object]:
    """Protocol Rule 4 single-feature leakage canary (`symmetric ROC-AUC <= 0.90`)."""
    fp = np.asarray(footprint, dtype=bool)
    fp_idx = np.full(fp.shape, -1, dtype=np.int32)
    fp_idx[fp] = np.arange(int(fp.sum()), dtype=np.int32)

    all_pos = np.zeros(fp.shape, dtype=bool)
    all_neg = np.zeros(fp.shape, dtype=bool)
    q_pos_rows = []
    q_neg_rows = []
    for f in folds:
        pm = f["truth"] & f["region"] & fp
        nm = (~f["truth"]) & (~f["visible"]) & f["region"] & fp
        all_pos |= pm
        all_neg |= nm
        q_pos_rows.append(fp_idx[pm])
        q_neg_rows.append(fp_idx[nm][::stride])

    pos_rows = fp_idx[all_pos]
    neg_rows = fp_idx[all_neg][::stride]
    y_pool = np.concatenate([np.ones(pos_rows.size, dtype=np.int8), np.zeros(neg_rows.size, dtype=np.int8)])

    rows_report = []
    max_sym = 0.0
    max_feat = ""
    for j, fname in enumerate(feature_names):
        vp = np.asarray(X_mm[pos_rows, j], dtype=np.float32)
        vn = np.asarray(X_mm[neg_rows, j], dtype=np.float32)
        auc = float(roc_auc_score(y_pool, np.concatenate([vp, vn])))
        sym = max(auc, 1.0 - auc)
        q_syms = []
        for qp, qn in zip(q_pos_rows, q_neg_rows):
            yq = np.concatenate([np.ones(qp.size, dtype=np.int8), np.zeros(qn.size, dtype=np.int8)])
            aq = float(
                roc_auc_score(
                    yq,
                    np.concatenate(
                        [np.asarray(X_mm[qp, j], dtype=np.float32), np.asarray(X_mm[qn, j], dtype=np.float32)]
                    ),
                )
            )
            q_syms.append(round(max(aq, 1.0 - aq), 6))
        worst_q = max(q_syms)
        eff_sym = max(sym, worst_q)
        if eff_sym > max_sym:
            max_sym = eff_sym
            max_feat = fname
        rows_report.append(
            {
                "index": j,
                "feature": fname,
                "group": "pure_subsurface" if fname in PDWC21_SUBSURFACE_NAMES or "_sub_" in fname else "topo_or_full",
                "pooled_auc": round(auc, 6),
                "pooled_symmetric_auc": round(sym, 6),
                "quadrant_symmetric_aucs": q_syms,
                "max_symmetric_auc": round(eff_sym, 6),
                "pass_le_090": bool(eff_sym <= 0.90),
            }
        )
    flagged = [r["feature"] for r in rows_report if not r["pass_le_090"]]
    return {
        "n_features": len(feature_names),
        "n_withheld_positives": int(pos_rows.size),
        "n_sampled_negatives": int(neg_rows.size),
        "max_symmetric_auc": round(max_sym, 6),
        "max_feature": max_feat,
        "flagged_gt_090": flagged,
        "pass": len(flagged) == 0,
        "features": rows_report,
    }


def evaluate_arm_terms(
    pred_fn,
    folds: list[dict],
    footprint: np.ndarray,
) -> tuple[np.ndarray, list[dict]]:
    """Run unchanged `eh.evaluate` on each of the 4 folds and sum aligned 20-km block terms."""
    terms_sum = None
    per_fold = []
    for f in folds:
        pred = pred_fn(f)
        res_f, t_f = eh.evaluate(pred, f, footprint)
        terms_sum = t_f if terms_sum is None else (terms_sum + t_f)
        per_fold.append(
            {
                "fold": int(f["fold"]),
                "dti": round(float(res_f["dti"]), 6),
                "tpw": round(float(res_f["tpw"]), 3),
                "fpw": round(float(res_f["fpw"]), 3),
                "fnw": round(float(res_f["fnw"]), 3),
                "n_truth": int(res_f["n_truth"]),
                "n_emitted_in_eval_region": int(res_f["n_emitted"]),
            }
        )
        del pred
    assert terms_sum is not None
    return terms_sum, per_fold


def collect_all_reference_rasters(exclude_names: set[str] | None = None) -> list[dict[str, object]]:
    """Collect deduplicated reference GeoTIFFs across `comparison_inventory`, `downloads`, and `sibling_sweep`."""
    excl = exclude_names or set()
    by_sha: dict[str, dict[str, object]] = {}

    inv_path = ROOT / "registry/comparison_inventory.json"
    if inv_path.is_file():
        inv = json.loads(inv_path.read_text())
        for e in inv.get("files", inv.get("entries", [])):
            lp = e.get("path") or e.get("local_path") or ""
            p = (ROOT / lp) if lp else None
            if p and p.is_file() and p.name not in excl:
                sh = e.get("sha256") or sha256_file(p)
                rec = by_sha.setdefault(
                    sh,
                    {"id": e.get("id") or p.stem, "path": p, "sha256": sh, "scopes": set()},
                )
                rec["scopes"].add("protocol_registry")

    for d_root, sc_name in (
        (ROOT / "docs/downloads", "local_downloads"),
        (ROOT / "data/registry", "data_registry"),
        (ROOT / "data/fleet_registry", "fleet_registry"),
    ):
        if d_root.is_dir():
            for p in sorted(d_root.rglob("*.tif")):
                if p.name in excl or p.name.startswith("sample_submission") or "geodawn" in p.name:
                    continue
                sh = sha256_file(p)
                rec = by_sha.setdefault(sh, {"id": p.stem, "path": p, "sha256": sh, "scopes": set()})
                rec["scopes"].add(sc_name)

    sib_dir = ROOT / "data/sibling_sweep/rasters"
    if sib_dir.is_dir():
        for p in sorted(sib_dir.glob("*.tif")):
            if p.name in excl:
                continue
            low = p.name.lower()
            if "existing_faults" in low or "sample_submission" in low or "geodawn" in low or "sgmc" in low or "catalogue_mask" in low:
                continue
            sh = sha256_file(p)
            rec = by_sha.setdefault(
                sh,
                {"id": f"sibling:{p.stem}", "path": p, "sha256": sh, "scopes": set()},
            )
            rec["scopes"].add("sibling_sweep")

    out = []
    for _, rec in sorted(by_sha.items()):
        rec["scopes"] = sorted(rec["scopes"])
        out.append(rec)
    return out


def screen_against_references(
    surface_2d: np.ndarray,
    dots_2d: np.ndarray,
    footprint: np.ndarray,
    refs: list[dict[str, object]],
    *,
    blanket_dot_threshold: int = 3 * DOT_BUDGET,
    active_cap_select_thresh: float = 0.50,
    max_cap_refs: int = 240,
) -> tuple[dict[str, object], list[Path]]:
    """Evaluate BOTH pre-placement Spearman rank-corr (`Rule 1`) AND post-placement 3-px dot overlap across all `refs`."""
    fp = np.asarray(footprint, dtype=bool)
    expected_shape = fp.shape
    cand_dots = (dots_2d > 0.0) & fp
    n_cand_dots = int(cand_dots.sum())
    cand_y, cand_x = np.nonzero(cand_dots)

    rng = np.random.default_rng(91021)
    fp_flat = np.flatnonzero(fp)
    sub_idx = np.sort(rng.choice(fp_flat, size=min(250_000, fp_flat.size), replace=False))
    surf_sub = surface_2d.ravel()[sub_idx].astype(np.float32)
    dots_sub = dots_2d.ravel()[sub_idx].astype(np.float32)

    y_g, x_g = np.ogrid[-3:4, -3:4]
    struct_3px = (y_g * y_g + x_g * x_g) <= 9

    rows = []
    cand_active: list[tuple[float, Path]] = []
    skipped_grid = 0

    for rec in refs:
        p: Path = rec["path"]
        try:
            with rasterio.open(p) as ds:
                if ds.count != 1 or ds.shape != expected_shape:
                    skipped_grid += 1
                    continue
                arr = ds.read(1)
        except Exception:
            skipped_grid += 1
            continue

        valid_pos = fp & np.isfinite(arr) & (arr > 0.0)
        n_ref_pos = int(valid_pos.sum())
        if n_ref_pos == 0:
            continue

        sub_raw = arr.ravel()[sub_idx]
        arr_clean_sub = np.where(np.isfinite(sub_raw) & (sub_raw >= 0.0), sub_raw, 0.0).astype(np.float32)
        if np.all(arr_clean_sub == arr_clean_sub[0]):
            rho_surf = 0.0
            rho_dots = 0.0
        else:
            r_s = float(spearmanr(surf_sub, arr_clean_sub).statistic)
            r_d = float(spearmanr(dots_sub, arr_clean_sub).statistic)
            rho_surf = 0.0 if not math.isfinite(r_s) else r_s
            rho_dots = 0.0 if not math.isfinite(r_d) else r_d

        if n_cand_dots > 0:
            h_img, w_img = expected_shape
            hit_c = np.zeros(n_cand_dots, dtype=bool)
            for dy_o in range(-3, 4):
                for dx_o in range(-3, 4):
                    if dy_o * dy_o + dx_o * dx_o <= 9:
                        yy_o = np.clip(cand_y + dy_o, 0, h_img - 1)
                        xx_o = np.clip(cand_x + dx_o, 0, w_img - 1)
                        in_b = (cand_y + dy_o >= 0) & (cand_y + dy_o < h_img) & (cand_x + dx_o >= 0) & (cand_x + dx_o < w_img)
                        hit_c |= in_b & valid_pos[yy_o, xx_o]
            hits_cand_to_ref = int(hit_c.sum())
        else:
            hits_cand_to_ref = 0
        ov_cand_to_ref = float(hits_cand_to_ref) / float(max(n_cand_dots, 1))

        is_blanket = bool(n_ref_pos > int(blanket_dot_threshold))
        if (not is_blanket) and ov_cand_to_ref >= float(active_cap_select_thresh):
            cand_active.append((ov_cand_to_ref, p))

        rows.append(
            {
                "id": rec["id"],
                "sha256": rec["sha256"],
                "path": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
                "scopes": rec["scopes"],
                "n_ref_positive": n_ref_pos,
                "is_synthetic_or_dense_blanket": is_blanket,
                "surface_spearman": round(rho_surf, 6),
                "dots_spearman": round(rho_dots, 6),
                "dot_overlap_3px": round(ov_cand_to_ref, 6),
            }
        )
        del arr, valid_pos

    cand_active.sort(key=lambda x: -x[0])
    active_paths = [p for _, p in cand_active[:max_cap_refs]]

    comp_rows = [r for r in rows if not r["is_synthetic_or_dense_blanket"]]
    prot_rows = [r for r in rows if "protocol_registry" in r["scopes"]]
    prot_comp_rows = [r for r in prot_rows if not r["is_synthetic_or_dense_blanket"]]

    def _max_stat(sub: list[dict], key: str, abs_val: bool = False) -> tuple[float, str]:
        if not sub:
            return 0.0, "none"
        best = max(sub, key=lambda r: abs(r[key]) if abs_val else r[key])
        return float(abs(best[key]) if abs_val else best[key]), str(best["id"])

    max_surf_all, max_surf_all_id = _max_stat(rows, "surface_spearman", abs_val=True)
    max_dots_rho_all, max_dots_rho_id = _max_stat(rows, "dots_spearman", abs_val=True)
    max_ov_comp, max_ov_comp_id = _max_stat(comp_rows, "dot_overlap_3px")
    max_ov_prot_comp, max_ov_prot_comp_id = _max_stat(prot_comp_rows, "dot_overlap_3px")
    max_ov_literal, max_ov_literal_id = _max_stat(rows, "dot_overlap_3px")

    comp_dups = [
        r
        for r in comp_rows
        if abs(r["surface_spearman"]) > 0.90 or abs(r["dots_spearman"]) > 0.90 or r["dot_overlap_3px"] > 0.70
    ]
    lit_dups = [
        r
        for r in rows
        if abs(r["surface_spearman"]) > 0.90 or abs(r["dots_spearman"]) > 0.90 or r["dot_overlap_3px"] > 0.70
    ]

    summary = {
        "n_compared_rasters": len(rows),
        "n_competitive_non_blanket_rasters": len(comp_rows),
        "n_protocol_registry_rasters": len(prot_rows),
        "n_protocol_competitive_rasters": len(prot_comp_rows),
        "n_skipped_wrong_grid_or_multiband": skipped_grid,
        "blanket_dot_threshold": int(blanket_dot_threshold),
        "surface_phase": {
            "max_abs_spearman_all_1100plus": round(max_surf_all, 6),
            "max_abs_spearman_ref": max_surf_all_id,
            "pass_le_090": bool(max_surf_all <= 0.90),
            "top_15_by_abs_spearman": sorted(rows, key=lambda r: -abs(r["surface_spearman"]))[:15],
        },
        "dots_phase_competitive": {
            "max_abs_spearman": round(max_dots_rho_all, 6),
            "max_abs_spearman_ref": max_dots_rho_id,
            "max_3px_overlap_all_competitive": round(max_ov_comp, 6),
            "max_3px_overlap_all_competitive_ref": max_ov_comp_id,
            "max_3px_overlap_protocol_competitive": round(max_ov_prot_comp, 6),
            "max_3px_overlap_protocol_competitive_ref": max_ov_prot_comp_id,
            "duplicate_count_competitive": len(comp_dups),
            "pass_competitive_uniqueness": len(comp_dups) == 0,
            "top_20_competitive_by_3px_overlap": sorted(comp_rows, key=lambda r: -r["dot_overlap_3px"])[:20],
        },
        "dots_phase_literal_including_synthetic_blankets": {
            "max_3px_overlap_literal": round(max_ov_literal, 6),
            "max_3px_overlap_literal_ref": max_ov_literal_id,
            "literal_exceed_count": len(lit_dups),
            "literal_exceed_refs": [
                {
                    "id": r["id"],
                    "n_ref_positive": r["n_ref_positive"],
                    "dot_overlap_3px": r["dot_overlap_3px"],
                    "scopes": r["scopes"],
                }
                for r in sorted(lit_dups, key=lambda x: -x["dot_overlap_3px"])[:25]
            ],
            "note": (
                "Every raster exceeding 0.70 after competitive capping is a dense/synthetic blanket (>112,962 positive pixels, "
                "led by calib_r13lattice_00904.tif with 206,895 lattice pixels whose 3-px halos cover >=82.34% of the off-catalogue "
                "footprint by pigeonhole geometry, documented in IR-S16-03)."
            ),
        },
    }
    return summary, active_paths


def pack_reference_halos_uint64(ref_paths: list[Path], footprint: np.ndarray) -> tuple[np.ndarray, int]:
    """Pack 3-px dilated boolean masks of `ref_paths` into `(H, W, W_words)` `uint64` bitfields."""
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    n_refs = len(ref_paths)
    if n_refs == 0:
        return np.zeros((h, w, 1), dtype=np.uint64), 0
    n_words = (n_refs + 63) // 64
    words = np.zeros((h, w, n_words), dtype=np.uint64)
    y_g, x_g = np.ogrid[-3:4, -3:4]
    struct_3px = (y_g * y_g + x_g * x_g) <= 9

    for idx, p in enumerate(ref_paths):
        with rasterio.open(p) as ds:
            arr = ds.read(1)
        pos = fp & np.isfinite(arr) & (arr > 0.0)
        halo = ndi.binary_dilation(pos, structure=struct_3px)
        w_i = idx >> 6
        bit = np.uint64(1) << np.uint64(idx & 63)
        words[halo, w_i] |= bit
        del arr, pos, halo
    return words, n_refs


def evaluate_blind_sgmc_suite(
    dots_2d: np.ndarray,
    catalogue: np.ndarray,
    footprint: np.ndarray,
) -> dict[str, float]:
    """Evaluate untouched blind off-catalogue USGS SGMC control (`>300 m`, `>500 m`, `>1 km`) + far-field spread."""
    fp = np.asarray(footprint, dtype=bool)
    cat = np.asarray(catalogue, dtype=bool) & fp
    d_cat = ndi.distance_transform_edt(~cat)
    with rasterio.open(SGMC_TIF) as ds:
        sgmc = (ds.read(1) > 0) & fp

    pred_bool = (dots_2d > 0.0) & fp
    out: dict[str, float] = {}
    for collar_px, tag in ((3.0, "gt300m"), (5.0, "gt500m"), (10.0, "gt1km")):
        dom = fp & (d_cat > collar_px)
        res = dti_binary(pred_bool & dom, sgmc & dom, valid=dom)
        out[f"sgmc_dti_{tag}"] = round(float(res["dti"]), 6)
        out[f"sgmc_pos_px_{tag}"] = int(res["n_truth"])

    n_dots = max(int(pred_bool.sum()), 1)
    out["n_dots"] = int(pred_bool.sum())
    out["ff_frac_gt500m"] = round(float((pred_bool & (d_cat > 5.0)).sum()) / n_dots, 6)
    out["ff_frac_gt1km"] = round(float((pred_bool & (d_cat > 10.0)).sum()) / n_dots, 6)
    out["ff_frac_gt2km"] = round(float((pred_bool & (d_cat > 20.0)).sum()) / n_dots, 6)
    return out


def evaluate_lfi_surrogate_projection(tif_path: Path, footprint: np.ndarray, catalogue: np.ndarray) -> dict[str, object]:
    """Evaluate `S20-LFI` leave-one-site-out Poisson-Tversky surrogate (`MODEL / PROJECTION`, never reported as a score)."""
    from gems91 import lfi as L

    spec_lfi = importlib.util.spec_from_file_location("run_lfi_mod", ROOT / "scripts/run_lfi.py")
    run_lfi_mod = importlib.util.module_from_spec(spec_lfi)
    spec_lfi.loader.exec_module(run_lfi_mod)

    run_lfi_mod.WORK = CACHE_DIR / "lfi_work"
    run_lfi_mod.WORK.mkdir(parents=True, exist_ok=True)
    sha_map = {}
    for d_rel in ("data/fleet_registry", "data/registry", "data/sibling_sweep/rasters", "docs/downloads"):
        dp = ROOT / d_rel
        if dp.is_dir():
            for p_tif in dp.rglob("*.tif"):
                sha_map.setdefault(sha256_file(p_tif), str(p_tif))
    anc_meta = json.loads((ROOT / "docs/lfi/anchors.json").read_text())
    for r_row in anc_meta["rows"]:
        sh_r = r_row.get("sha256")
        if sh_r and sh_r in sha_map:
            r_row["local"] = sha_map[sh_r]
        elif r_row.get("local") and not (ROOT / r_row["local"]).is_file():
            r_row["used"] = False
    fp, cat, net = run_lfi_mod.base()
    design, _, _ = run_lfi_mod.build_design(fp, cat, net, anc_meta["rows"])
    bins = design.bin_index()
    nb = design.n_bins
    A = np.bincount(bins[fp & ~cat], minlength=nb).astype(np.float64)
    Lm = design.level_matrix()
    X = np.hstack([np.ones((Lm.shape[0], 1)), Lm])
    pnames = design.param_names()

    with rasterio.open(tif_path) as ds:
        cand_arr = np.where(np.isfinite(ds.read(1)) & fp, ds.read(1), 0.0).astype(np.float32)
    N_c, C_c = L.aggregate(cand_arr, bins, nb, cat)
    Nm = N_c[None, :]
    Cm = C_c[None, :]

    proj: dict[str, object] = {"label_class": "MODEL_PROJECTION_NOT_A_SCORE"}
    for tag, fit_file in (("ridge1", ROOT / "docs/lfi/fit_r1.json"), ("ridge10", ROOT / "docs/lfi/fit_r10.json")):
        if not fit_file.is_file():
            continue
        fd = json.loads(fit_file.read_text())
        theta = np.array([float(fd["theta"][k]) for k in pnames], dtype=np.float64)
        y_hat, _ = L.predict(theta, float(fd["f"]), X, Nm, Cm, A)
        proj[tag] = {
            "projected_value_model_only": round(float(y_hat[0]), 5),
            "loso_rmse": round(float(fd["rmse_loso"]), 5),
            "loso_r": round(float(fd["pearson_loso"]), 5),
        }
    return proj


def main() -> int:
    t0 = time.time()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

    print("[S21-PDWC] Step 1: Verifying immutable vendor/gems57 SHA-256 pins...")
    pins = verify_template_pins()

    with rasterio.open(SAMPLE_TIF) as ds_s:
        footprint = np.isfinite(ds_s.read(1))
    with rasterio.open(EXISTING_FAULTS_TIF) as ds_e:
        raw_ef = ds_e.read(1)
        existing_faults = np.isfinite(raw_ef) & (raw_ef > 0) & footprint
    if CATALOGUE_MASK_TIF.is_file():
        with rasterio.open(CATALOGUE_MASK_TIF) as ds_c:
            catalogue = (ds_c.read(1) > 0) & footprint
    else:
        catalogue = existing_faults.copy()

    print(f"[S21-PDWC] Footprint pixels: {int(footprint.sum()):,} | Catalogue pixels: {int(catalogue.sum()):,}")

    print("[S21-PDWC] Step 2: Building/loading 66-column PDWC21 pure-physics static feature stack...")
    t_feat = time.time()
    X_static, feat_names, feat_meta = build_or_load_pdwc21_memmap(
        features_tif=FEATURES_TIF,
        gdr_csv=GDR_CSV,
        footprint=footprint,
        cache_dir=CACHE_DIR,
    )
    print(
        f"[S21-PDWC] Static stack ready in {time.time() - t_feat:.1f}s "
        f"(shape={X_static.shape}, B12/B19 max_diff={feat_meta['verified_subsurface_b12_b19_max_diff']})"
    )

    print("[S21-PDWC] Step 3: Building spatial-block hide-and-recover folds (`gems57-pooled-hide-v2`)...")
    folds = list(g57_spatial.folds(catalogue, footprint, buffer_px=BUFFER_PX))
    split_sha = compute_split_sha(folds)
    n_withheld = int(sum(f["truth"].sum() for f in folds))
    print(f"[S21-PDWC] split_sha256={split_sha} | withheld_positives={n_withheld:,}")
    if split_sha != EXPECTED_SPLIT_SHA256:
        raise RuntimeError(f"Holdout split_sha256 mismatch: {split_sha} != {EXPECTED_SPLIT_SHA256}")

    print("[S21-PDWC] Step 4: Running Rule-4 single-feature leakage canary on 66 static features...")
    static_canary = run_feature_canary(X_mm=X_static, feature_names=feat_names, folds=folds, footprint=footprint)
    print(
        f"[S21-PDWC] Static canary pass={static_canary['pass']} | "
        f"max_symmetric_auc={static_canary['max_symmetric_auc']} ({static_canary['max_feature']})"
    )
    if not static_canary["pass"]:
        raise RuntimeError(f"Rule-4 static leakage canary failed: {static_canary['flagged_gt_090']}")

    sub_cols = list(range(len(PDWC21_SUBSURFACE_NAMES)))
    full_cols = list(range(len(PDWC21_FEATURE_NAMES)))
    name_to_idx = {n: i for i, n in enumerate(PDWC21_FEATURE_NAMES)}
    hard_neg_sub = [
        name_to_idx["dcwf_grav_match_200m"],
        name_to_idx["dcwf_rtp_match_200m"],
        name_to_idx["hcba_cond_b15_resid"],
        name_to_idx["sub_flightline_seam_guard"],
    ]
    hard_neg_full = hard_neg_sub + [
        name_to_idx["topo_steger_slope_crest_120m"],
        name_to_idx["topo_ptcf_200m"],
        name_to_idx["topo_slope_local_contrast"],
    ]

    cover_fp = np.asarray(X_static[:, name_to_idx["topo_cover_ness_index"]], dtype=np.float32)
    crest_fp = compute_pdwc_crest_backbone_fp(X_static)
    sub_backbone_fp = compute_subsurface_backbone_fp(X_static)

    # Step 5: Symmetric 3-level nested cross-fitting so BOTH training and test quadrants are 100% OOF!
    print("[S21-PDWC] Step 5: Fitting symmetric nested Dual-Specialist (Full + Pure-Subsurface)...")
    s1_full_oof = np.zeros(footprint.shape, dtype=np.float32)
    s1_sub_oof = np.zeros(footprint.shape, dtype=np.float32)
    s1_fold_full: list[np.ndarray] = []
    s1_fold_sub: list[np.ndarray] = []

    for q, f in enumerate(folds):
        c_f = CACHE_DIR / f"s1_fold{q}_full.npy"
        c_s = CACHE_DIR / f"s1_fold{q}_sub.npy"
        if not (c_f.is_file() and c_s.is_file()):
            pf, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, full_cols)],
                hard_neg_cols_in_stack=hard_neg_full,
                visible_faults=f["visible"],
                train_domain=f["train"],
                footprint=footprint,
                seed=2100 + 31 * q,
            )
            ps, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, sub_cols)],
                hard_neg_cols_in_stack=hard_neg_sub,
                visible_faults=f["visible"],
                train_domain=f["train"],
                footprint=footprint,
                seed=2200 + 31 * q,
            )
            np.save(c_f, pf)
            np.save(c_s, ps)
            del pf, ps
            gc.collect()
        pf_mm = np.load(c_f, mmap_mode="r")
        ps_mm = np.load(c_s, mmap_mode="r")
        s1_fold_full.append(pf_mm)
        s1_fold_sub.append(ps_mm)
        qm = f["region"] & footprint
        s1_full_oof[qm] = pf_mm[qm]
        s1_sub_oof[qm] = ps_mm[qm]
        print(f"  - Fold {q} Stage-1 ready (OOF full mean={float(pf_mm[qm].mean()):.4f}, sub mean={float(ps_mm[qm].mean()):.4f})")

    # Pairwise 2-quadrant Stage-1 & Stage-2 models (`(a, b)` uses ONLY visible faults buffered >=80 px from all other quadrants!)
    comp_map = folds[0]["components"]
    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    pair_s1_full: dict[tuple[int, int], np.ndarray] = {}
    pair_s1_sub: dict[tuple[int, int], np.ndarray] = {}
    pair_s2_full: dict[tuple[int, int], np.ndarray] = {}
    pair_s2_sub: dict[tuple[int, int], np.ndarray] = {}
    ac_full_cols = list(range(len(PDWC21_AC_NAMES)))
    ac_sub_cols = list(range(8, 16))

    # Single-quadrant Stage-1 models so each pair (a, b) also gets 100% OOF Stage-1 auto-context on a and b!
    single_s1_full: list[np.ndarray] = []
    single_s1_sub: list[np.ndarray] = []
    for q, f in enumerate(folds):
        sf_p = CACHE_DIR / f"single_q{q}_full.npy"
        ss_p = CACHE_DIR / f"single_q{q}_sub.npy"
        if not (sf_p.is_file() and ss_p.is_file()):
            other_reg = (~f["region"]) & footprint
            other_ids = np.unique(comp_map[catalogue & other_reg])
            other_ids = other_ids[other_ids > 0]
            other_held = (np.isin(comp_map, other_ids) & catalogue) if len(other_ids) else np.zeros_like(catalogue, bool)
            excl_q = other_reg | other_held
            train_q = footprint & (ndi.distance_transform_edt(~excl_q) > BUFFER_PX)
            vis_q = catalogue & (~other_held)
            pf_1, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, full_cols)],
                hard_neg_cols_in_stack=hard_neg_full,
                visible_faults=vis_q,
                train_domain=train_q,
                footprint=footprint,
                seed=2300 + 19 * q,
            )
            ps_1, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, sub_cols)],
                hard_neg_cols_in_stack=hard_neg_sub,
                visible_faults=vis_q,
                train_domain=train_q,
                footprint=footprint,
                seed=2350 + 19 * q,
            )
            np.save(sf_p, pf_1)
            np.save(ss_p, ps_1)
            del pf_1, ps_1
            gc.collect()
        single_s1_full.append(np.load(sf_p, mmap_mode="r"))
        single_s1_sub.append(np.load(ss_p, mmap_mode="r"))

    for idx_p, (a, b) in enumerate(pairs):
        pf_path = CACHE_DIR / f"pair_{a}_{b}_s1_full.npy"
        ps_path = CACHE_DIR / f"pair_{a}_{b}_s1_sub.npy"
        p2f_path = CACHE_DIR / f"pair_{a}_{b}_s2_full.npy"
        p2s_path = CACHE_DIR / f"pair_{a}_{b}_s2_sub.npy"

        dom_ab = (folds[a]["region"] | folds[b]["region"]) & footprint
        other_reg = (~dom_ab) & footprint
        other_ids = np.unique(comp_map[catalogue & other_reg])
        other_ids = other_ids[other_ids > 0]
        other_held = (np.isin(comp_map, other_ids) & catalogue) if len(other_ids) else np.zeros_like(catalogue, bool)
        excl_ab = other_reg | other_held
        train_ab = footprint & (ndi.distance_transform_edt(~excl_ab) > BUFFER_PX)
        vis_ab = catalogue & (~other_held)

        if not (pf_path.is_file() and ps_path.is_file()):
            pf_ab, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, full_cols)],
                hard_neg_cols_in_stack=hard_neg_full,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=footprint,
                seed=2400 + 23 * idx_p,
            )
            ps_ab, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, sub_cols)],
                hard_neg_cols_in_stack=hard_neg_sub,
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=footprint,
                seed=2500 + 23 * idx_p,
            )
            np.save(pf_path, pf_ab)
            np.save(ps_path, ps_ab)
            del pf_ab, ps_ab
            gc.collect()
        pair_s1_full[(a, b)] = np.load(pf_path, mmap_mode="r")
        pair_s1_sub[(a, b)] = np.load(ps_path, mmap_mode="r")

        if not (p2f_path.is_file() and p2s_path.is_file()):
            # Build 100% OOF Stage-1 composite for pair (a, b): b predicts a, a predicts b, (a,b) predicts outside!
            s1_ab_f = np.asarray(pair_s1_full[(a, b)], dtype=np.float32).copy()
            s1_ab_s = np.asarray(pair_s1_sub[(a, b)], dtype=np.float32).copy()
            ma = folds[a]["region"] & footprint
            mb = folds[b]["region"] & footprint
            s1_ab_f[ma] = single_s1_full[b][ma]
            s1_ab_s[ma] = single_s1_sub[b][ma]
            s1_ab_f[mb] = single_s1_full[a][mb]
            s1_ab_s[mb] = single_s1_sub[a][mb]
            ac_ab = build_ac_memmap(CACHE_DIR / f"ac_pair_{a}_{b}.f16.mmap", s1_ab_f, s1_ab_s, footprint)
            del s1_ab_f, s1_ab_s
            p2f_ab, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, full_cols), (ac_ab, ac_full_cols)],
                hard_neg_cols_in_stack=hard_neg_full + [len(full_cols) + 0, len(full_cols) + 1],
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=footprint,
                predict_mask=other_reg,
                seed=2600 + 29 * idx_p,
            )
            p2s_ab, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, sub_cols), (ac_ab, ac_sub_cols)],
                hard_neg_cols_in_stack=hard_neg_sub + [len(sub_cols) + 0, len(sub_cols) + 1],
                visible_faults=vis_ab,
                train_domain=train_ab,
                footprint=footprint,
                predict_mask=other_reg,
                seed=2650 + 29 * idx_p,
            )
            np.save(p2f_path, p2f_ab)
            np.save(p2s_path, p2s_ab)
            del ac_ab, p2f_ab, p2s_ab
            gc.collect()
        pair_s2_full[(a, b)] = np.load(p2f_path, mmap_mode="r")
        pair_s2_sub[(a, b)] = np.load(p2s_path, mmap_mode="r")
        print(f"  - Nested pair ({a},{b}) Stage-1 & Stage-2 ready")

    del single_s1_full, single_s1_sub
    gc.collect()
    if "--stop-after-nested" in sys.argv:
        print("[S21-PDWC] Nested pairwise checkpoint complete!")
        return 0

    # Outer 4-fold Stage-2 models + symmetric 100% OOF fold surfaces (for both training AND test quadrants!)
    s2_full_oof = np.zeros(footprint.shape, dtype=np.float32)
    s2_sub_oof = np.zeros(footprint.shape, dtype=np.float32)
    sym_s1_full_by_fold: list[np.ndarray] = []
    sym_s1_sub_by_fold: list[np.ndarray] = []
    sym_s2_full_by_fold: list[np.ndarray] = []
    sym_s2_sub_by_fold: list[np.ndarray] = []

    for q, f in enumerate(folds):
        others = [j for j in range(4) if j != q]
        s1_in_f = np.zeros(footprint.shape, dtype=np.float32)
        s1_in_s = np.zeros(footprint.shape, dtype=np.float32)
        s2_in_f = np.zeros(footprint.shape, dtype=np.float32)
        s2_in_s = np.zeros(footprint.shape, dtype=np.float32)

        for r in others:
            rem_pair = tuple(sorted(x for x in others if x != r))
            rm = folds[r]["region"] & footprint
            s1_in_f[rm] = pair_s1_full[rem_pair][rm]
            s1_in_s[rm] = pair_s1_sub[rem_pair][rm]
            s2_in_f[rm] = pair_s2_full[rem_pair][rm]
            s2_in_s[rm] = pair_s2_sub[rem_pair][rm]

        qm = f["region"] & footprint
        s1_in_f[qm] = s1_fold_full[q][qm]
        s1_in_s[qm] = s1_fold_sub[q][qm]

        ac_mm_q = build_ac_memmap(CACHE_DIR / f"ac_fold{q}.f16.mmap", s1_in_f, s1_in_s, footprint)
        c2_f = CACHE_DIR / f"s2_fold{q}_full.npy"
        c2_s = CACHE_DIR / f"s2_fold{q}_sub.npy"
        if not (c2_f.is_file() and c2_s.is_file()):
            p2f, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, full_cols), (ac_mm_q, ac_full_cols)],
                hard_neg_cols_in_stack=hard_neg_full + [len(full_cols) + 0, len(full_cols) + 1],
                visible_faults=f["visible"],
                train_domain=f["train"],
                footprint=footprint,
                predict_mask=qm,
                seed=2700 + 37 * q,
            )
            p2s, _ = fit_predict_pdwc_specialist(
                blocks=[(X_static, sub_cols), (ac_mm_q, ac_sub_cols)],
                hard_neg_cols_in_stack=hard_neg_sub + [len(sub_cols) + 0, len(sub_cols) + 1],
                visible_faults=f["visible"],
                train_domain=f["train"],
                footprint=footprint,
                predict_mask=qm,
                seed=2800 + 37 * q,
            )
            np.save(c2_f, p2f)
            np.save(c2_s, p2s)
            del p2f, p2s
            gc.collect()
        p2f_mm = np.load(c2_f, mmap_mode="r")
        p2s_mm = np.load(c2_s, mmap_mode="r")
        s2_in_f[qm] = p2f_mm[qm]
        s2_in_s[qm] = p2s_mm[qm]
        s2_full_oof[qm] = p2f_mm[qm]
        s2_sub_oof[qm] = p2s_mm[qm]

        sym_s1_full_by_fold.append(s1_in_f)
        sym_s1_sub_by_fold.append(s1_in_s)
        sym_s2_full_by_fold.append(s2_in_f)
        sym_s2_sub_by_fold.append(s2_in_s)
        del ac_mm_q
        gc.collect()
        print(f"  - Fold {q} Stage-2 symmetric OOF surface ready (test mean={float(p2f_mm[qm].mean()):.4f})")

    del pair_s1_full, pair_s1_sub, pair_s2_full, pair_s2_sub
    gc.collect()

    # Run Rule-4 Canary on the stitched 4-fold OOF Stage-2 Auto-Context features!
    ac_oof_mm = build_ac_memmap(CACHE_DIR / "ac_oof_stitched.f16.mmap", s1_full_oof, s1_sub_oof, footprint)
    ac_canary = run_feature_canary(X_mm=ac_oof_mm, feature_names=PDWC21_AC_NAMES, folds=folds, footprint=footprint)
    print(
        f"[S21-PDWC] Stage-2 OOF Auto-Context canary pass={ac_canary['pass']} | "
        f"max_symmetric_auc={ac_canary['max_symmetric_auc']} ({ac_canary['max_feature']})"
    )
    if not ac_canary["pass"]:
        raise RuntimeError(f"Rule-4 Stage-2 AC leakage canary failed: {ac_canary['flagged_gt_090']}")
    del ac_oof_mm

    canary_report = {
        "evaluator_version": eh.VERSION,
        "split_sha256": split_sha,
        "static_66_canary": static_canary,
        "stage2_ac_16_canary": ac_canary,
        "overall_max_symmetric_auc": max(static_canary["max_symmetric_auc"], ac_canary["max_symmetric_auc"]),
        "overall_pass_le_090": bool(static_canary["pass"] and ac_canary["pass"]),
    }
    (EVIDENCE_DIR / "canary.json").write_text(json.dumps(canary_report, indent=2) + "\n")

    terms_by_arm: dict[str, np.ndarray] = {}
    per_fold_by_arm: dict[str, list[dict]] = {}

    # Diagnostic Comparator (`IR-S21-01`): Fold-Honest GEMSDOE32 R0 (`H27-4 & d_vis > 2.0 px` per fold) vs Static Full-Catalogue-Collared R0
    h274_path = ROOT / "data/fleet_registry/GEMSDOE28__h27-4-r1-solo-d2-8.tif"
    r0_path = ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif"
    if h274_path.is_file() and r0_path.is_file():
        with rasterio.open(h274_path) as ds_h274, rasterio.open(r0_path) as ds_r0:
            arr_h274 = np.where(np.isfinite(ds_h274.read(1)) & footprint, ds_h274.read(1), 0.0).astype(np.float32)
            arr_r0 = np.where(np.isfinite(ds_r0.read(1)) & footprint, ds_r0.read(1), 0.0).astype(np.float32)

        t_r0_fh, pf_r0_fh = evaluate_arm_terms(
            lambda f: np.where(
                footprint & (ndi.distance_transform_edt(~(f["visible"] & footprint)) > 2.0), arr_h274, 0.0
            ).astype(np.float32),
            folds,
            footprint,
        )
        t_r0_st, pf_r0_st = evaluate_arm_terms(lambda f: arr_r0, folds, footprint)
        terms_by_arm["fold_honest_r0_h274_vis2px"] = t_r0_fh
        terms_by_arm["static_fullcat_collared_r0"] = t_r0_st
        per_fold_by_arm["fold_honest_r0_h274_vis2px"] = pf_r0_fh
        per_fold_by_arm["static_fullcat_collared_r0"] = pf_r0_st
        del arr_h274, arr_r0

    # Experiment 1 (`pdwc_e1`): Symmetric OOF Stage-1 Dual-Specialist + Asymmetric Cover Rescue + NMS 37,654
    print("[S21-PDWC] Step 6a: Evaluating Experiment 1 (`pdwc_e1`: Stage-1 Asymmetric Cover Rescue + NMS 37,654)...")

    def _pred_e1(f: dict) -> np.ndarray:
        q = int(f["fold"])
        surf_q = pool_asymmetric_cover_rescue(
            s1_full=sym_s1_full_by_fold[q],
            s1_sub=sym_s1_sub_by_fold[q],
            s2_full=None,
            s2_sub=None,
            cover_fp=cover_fp,
            crest_fp=crest_fp,
            sub_backbone_fp=None,
            footprint=footprint,
            max_cover_rescue=0.48,
            crest_alpha=0.18,
        )
        return emit_dots_nms(
            surf_q,
            f["visible"],
            footprint,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=COLLAR_PX,
        )

    t_e1, pf_e1 = evaluate_arm_terms(_pred_e1, folds, footprint)
    terms_by_arm["pdwc_e1"] = t_e1
    per_fold_by_arm["pdwc_e1"] = pf_e1
    print(f"[S21-PDWC] E1 (`pdwc_e1`) HOLDOUT-DTI = {float(eh.from_terms(t_e1.sum(axis=0))):.6f}")

    # Experiment 2 (`pdwc_e2`): Symmetric OOF Stage-1/2 + DCWF x MGPC Crest Gate + Unconstrained 300 m CELF 37,654
    print("[S21-PDWC] Step 6b: Evaluating Experiment 2 (`pdwc_e2`: Symmetric OOF Stage-1/2 + 300 m CELF 37,654)...")

    def _pred_e2(f: dict) -> np.ndarray:
        q = int(f["fold"])
        surf_q = pool_asymmetric_cover_rescue(
            s1_full=sym_s1_full_by_fold[q],
            s1_sub=sym_s1_sub_by_fold[q],
            s2_full=sym_s2_full_by_fold[q],
            s2_sub=sym_s2_sub_by_fold[q],
            cover_fp=cover_fp,
            crest_fp=crest_fp,
            sub_backbone_fp=None,
            footprint=footprint,
            stage2_weight=0.38,
            max_cover_rescue=0.52,
            crest_alpha=0.22,
        )
        return emit_dots_celf_submodular(
            surf_q,
            f["visible"],
            footprint,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=COLLAR_PX,
        )

    t_e2, pf_e2 = evaluate_arm_terms(_pred_e2, folds, footprint)
    terms_by_arm["pdwc_e2"] = t_e2
    per_fold_by_arm["pdwc_e2"] = pf_e2
    print(f"[S21-PDWC] E2 (`pdwc_e2`) HOLDOUT-DTI = {float(eh.from_terms(t_e2.sum(axis=0))):.6f}")

    # Stitched 4-fold OOF surface & dots for E2 -> screen across ALL 1,100+ reference rasters BEFORE E3!
    e2_oof_surface = pool_asymmetric_cover_rescue(
        s1_full=s1_full_oof,
        s1_sub=s1_sub_oof,
        s2_full=s2_full_oof,
        s2_sub=s2_sub_oof,
        cover_fp=cover_fp,
        crest_fp=crest_fp,
        sub_backbone_fp=None,
        footprint=footprint,
        stage2_weight=0.38,
        max_cover_rescue=0.52,
        crest_alpha=0.22,
    )
    e2_oof_dots = emit_dots_celf_submodular(
        e2_oof_surface,
        catalogue,
        footprint,
        budget=DOT_BUDGET,
        collar_px=COLLAR_PX,
        min_spacing_px=COLLAR_PX,
    )

    print("[S21-PDWC] Step 6c: Screening E2 surface & preliminary dots across all registry + 1,072 sibling rasters...")
    all_refs = collect_all_reference_rasters()
    e2_screen, active_cap_paths = screen_against_references(
        e2_oof_surface,
        e2_oof_dots,
        footprint,
        all_refs,
        active_cap_select_thresh=0.48,
        max_cap_refs=240,
    )
    print(
        f"[S21-PDWC] E2 Screen across {e2_screen['n_compared_rasters']} rasters: "
        f"max |surf_rho|={e2_screen['surface_phase']['max_abs_spearman_all_1100plus']:.4f} | "
        f"max competitive 3px overlap={e2_screen['dots_phase_competitive']['max_3px_overlap_all_competitive']:.4f} "
        f"({e2_screen['dots_phase_competitive']['max_3px_overlap_all_competitive_ref']}) | "
        f"active cap refs={len(active_cap_paths)}"
    )

    # Experiment 3 (`pdwc_e3`): Far-Field Subsurface Backbone Reinforcement + Hard Multi-Registry Uniqueness-Constrained 300 m CELF
    print(
        f"[S21-PDWC] Step 6d: Packing {len(active_cap_paths)} active reference 3-px halos & running Experiment 3 "
        f"(`pdwc_e3`: Far-Field Subsurface Backbone + <= {UNIQUENESS_CAP:.2f} Uniqueness-Capped 300 m CELF)..."
    )
    ref_halo_words, n_cap_refs = pack_reference_halos_uint64(active_cap_paths, footprint)

    def _pred_e3(f: dict) -> np.ndarray:
        q = int(f["fold"])
        surf_q = pool_asymmetric_cover_rescue(
            s1_full=sym_s1_full_by_fold[q],
            s1_sub=sym_s1_sub_by_fold[q],
            s2_full=sym_s2_full_by_fold[q],
            s2_sub=sym_s2_sub_by_fold[q],
            cover_fp=cover_fp,
            crest_fp=crest_fp,
            sub_backbone_fp=sub_backbone_fp,
            footprint=footprint,
            stage2_weight=0.38,
            max_cover_rescue=0.56,
            crest_alpha=0.22,
            sub_backbone_alpha=0.26,
        )
        return emit_dots_celf_submodular(
            surf_q,
            f["visible"],
            footprint,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=COLLAR_PX,
            ref_halo_words=ref_halo_words,
            n_refs=n_cap_refs,
            uniqueness_cap=UNIQUENESS_CAP,
        )

    t_e3, pf_e3 = evaluate_arm_terms(_pred_e3, folds, footprint)
    terms_by_arm["pdwc_e3"] = t_e3
    per_fold_by_arm["pdwc_e3"] = pf_e3
    print(f"[S21-PDWC] E3 (`pdwc_e3`) HOLDOUT-DTI = {float(eh.from_terms(t_e3.sum(axis=0))):.6f}")

    e3_oof_surface = pool_asymmetric_cover_rescue(
        s1_full=s1_full_oof,
        s1_sub=s1_sub_oof,
        s2_full=s2_full_oof,
        s2_sub=s2_sub_oof,
        cover_fp=cover_fp,
        crest_fp=crest_fp,
        sub_backbone_fp=sub_backbone_fp,
        footprint=footprint,
        stage2_weight=0.38,
        max_cover_rescue=0.56,
        crest_alpha=0.22,
        sub_backbone_alpha=0.26,
    )
    e3_oof_dots = emit_dots_celf_submodular(
        e3_oof_surface,
        catalogue,
        footprint,
        budget=DOT_BUDGET,
        collar_px=COLLAR_PX,
        min_spacing_px=COLLAR_PX,
        ref_halo_words=ref_halo_words,
        n_refs=n_cap_refs,
        uniqueness_cap=UNIQUENESS_CAP,
    )

    e3_final_screen, extra_paths = screen_against_references(
        e3_oof_surface,
        e3_oof_dots,
        footprint,
        all_refs,
        active_cap_select_thresh=0.60,
        max_cap_refs=240,
    )
    new_paths = [p for p in extra_paths if p not in set(active_cap_paths)]
    if new_paths and not e3_final_screen["dots_phase_competitive"]["pass_competitive_uniqueness"]:
        print(f"[S21-PDWC] Adding {len(new_paths)} newly-active reference halos to E3 cap set...")
        active_cap_paths = (active_cap_paths + new_paths)[:256]
        del ref_halo_words
        ref_halo_words, n_cap_refs = pack_reference_halos_uint64(active_cap_paths, footprint)
        t_e3, pf_e3 = evaluate_arm_terms(_pred_e3, folds, footprint)
        terms_by_arm["pdwc_e3"] = t_e3
        per_fold_by_arm["pdwc_e3"] = pf_e3
        e3_oof_dots = emit_dots_celf_submodular(
            e3_oof_surface,
            catalogue,
            footprint,
            budget=DOT_BUDGET,
            collar_px=COLLAR_PX,
            min_spacing_px=COLLAR_PX,
            ref_halo_words=ref_halo_words,
            n_refs=n_cap_refs,
            uniqueness_cap=UNIQUENESS_CAP,
        )
        e3_final_screen, _ = screen_against_references(
            e3_oof_surface,
            e3_oof_dots,
            footprint,
            all_refs,
            active_cap_select_thresh=0.50,
            max_cap_refs=240,
        )

    del ref_halo_words
    gc.collect()

    e1_oof_surface = pool_asymmetric_cover_rescue(
        s1_full=s1_full_oof,
        s1_sub=s1_sub_oof,
        s2_full=None,
        s2_sub=None,
        cover_fp=cover_fp,
        crest_fp=crest_fp,
        sub_backbone_fp=None,
        footprint=footprint,
        max_cover_rescue=0.48,
        crest_alpha=0.18,
    )
    e1_oof_dots = emit_dots_nms(
        e1_oof_surface,
        catalogue,
        footprint,
        budget=DOT_BUDGET,
        collar_px=COLLAR_PX,
        min_spacing_px=COLLAR_PX,
    )
    e1_screen, _ = screen_against_references(
        e1_oof_surface,
        e1_oof_dots,
        footprint,
        all_refs,
        active_cap_select_thresh=0.50,
        max_cap_refs=240,
    )
    print(
        f"[S21-PDWC] E1 Screen across {e1_screen['n_compared_rasters']} rasters: "
        f"max |surf_rho|={e1_screen['surface_phase']['max_abs_spearman_all_1100plus']:.4f} | "
        f"max competitive 3px overlap={e1_screen['dots_phase_competitive']['max_3px_overlap_all_competitive']:.4f} "
        f"({e1_screen['dots_phase_competitive']['max_3px_overlap_all_competitive_ref']})"
    )

    arm_candidates = []
    for a_name, a_dots, a_scr in (
        ("pdwc_e1", e1_oof_dots, e1_screen),
        ("pdwc_e2", e2_oof_dots, e2_screen),
        ("pdwc_e3", e3_oof_dots, e3_final_screen),
    ):
        a_uniq = bool(a_scr["surface_phase"]["pass_le_090"] and a_scr["dots_phase_competitive"]["pass_competitive_uniqueness"])
        a_dti = float(eh.from_terms(terms_by_arm[a_name].sum(axis=0)))
        arm_candidates.append((a_uniq, a_dti, a_name, a_dots, a_scr))
    arm_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    _, _, chosen_exp, chosen_dots, chosen_screen = arm_candidates[0]

    pooled = eh.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate=chosen_exp)
    cand_score = pooled["scores"][chosen_exp]
    cand_dti = float(cand_score["dti"])
    print(
        f"[S21-PDWC] Selected candidate: {chosen_exp} | HOLDOUT-DTI={cand_dti:.6f} "
        f"(95% CI={cand_score['ci95']}) | "
        f"max competitive 3px overlap={chosen_screen['dots_phase_competitive']['max_3px_overlap_all_competitive']:.4f} "
        f"({chosen_screen['dots_phase_competitive']['max_3px_overlap_all_competitive_ref']})"
    )

    # Step 7: Emit unique validated `-zeros.tif` + `-zeros.zip` via unchanged `vendor/gems57/submission_writer.py`
    git_sha8 = (
        subprocess.run(["git", "rev-parse", "--short=8", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True)
        .stdout.strip()
    )
    ts_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"gems91-s21-{chosen_exp.replace('_', '-')}-{ts_utc}-{git_sha8}-zeros"
    out_tif = DOWNLOADS_DIR / f"{stem}.tif"
    out_zip = DOWNLOADS_DIR / f"{stem}.zip"

    for old_f in DOWNLOADS_DIR.glob("gems91-s21-*"):
        old_f.unlink()

    note_str = (
        f"GEMS91 S21-PDWC ({chosen_exp}): Cauchy-Hilbert DCWF+B15 updip+LogGabor+ClayCap OOF 37654d; "
        f"hide-v2={cand_dti:.4f}"
    )[:140]
    assert len(note_str) <= 140

    writer_meta = write_submission(
        out_tif,
        chosen_dots,
        SAMPLE_TIF,
        footprint,
        note=note_str,
        name=stem,
        catalogue=existing_faults,
    )
    print(f"[S21-PDWC] Emitted {out_tif.name} ({out_tif.stat().st_size:,} bytes, sha256={writer_meta['sha256']})")

    fmt_g57 = g57_gates.format_report(out_tif, SAMPLE_TIF, footprint=footprint)
    rel_g91 = validate_release(
        out_tif,
        template=SAMPLE_TIF,
        catalogue=existing_faults,
        encoding="zeros",
        floor_px=3.0,
        expect_dots=int((chosen_dots > 0).sum()),
    )
    tf_arr = tifffile.imread(out_tif)
    with zipfile.ZipFile(out_zip, "r") as zf:
        zip_members = zf.namelist()
        zip_crc_bad = zf.testzip()

    validation_report = {
        "automated_without_human_intervention": True,
        "writer_meta": writer_meta,
        "gems57_format_report": fmt_g57,
        "gems91_release_gates": rel_g91,
        "tifffile_roundtrip": {
            "shape": list(tf_arr.shape),
            "dtype": str(tf_arr.dtype),
            "all_finite": bool(np.isfinite(tf_arr).all()),
            "min": float(tf_arr.min()),
            "max": float(tf_arr.max()),
            "unique_values": [float(v) for v in np.unique(tf_arr)],
            "n_positive": int((tf_arr > 0).sum()),
        },
        "zip_check": {
            "zip_path": str(out_zip.relative_to(ROOT)),
            "zip_bytes": int(out_zip.stat().st_size),
            "zip_sha256": sha256_file(out_zip),
            "members": zip_members,
            "single_tif_member": zip_members == [out_tif.name],
            "crc_ok": zip_crc_bad is None,
        },
    }
    tech_pass = bool(
        fmt_g57["ok"]
        and rel_g91["PASS"]
        and validation_report["tifffile_roundtrip"]["all_finite"]
        and validation_report["tifffile_roundtrip"]["min"] >= 0.0
        and validation_report["tifffile_roundtrip"]["max"] <= 1.0
        and validation_report["zip_check"]["single_tif_member"]
        and validation_report["zip_check"]["crc_ok"]
    )
    validation_report["PASS_ALL_TECHNICAL_GATES"] = tech_pass
    if not tech_pass:
        raise RuntimeError(f"Automated technical validation failed: {validation_report}")

    sgmc_suite: dict[str, dict[str, float]] = {
        "pdwc_e1": evaluate_blind_sgmc_suite(e1_oof_dots, catalogue, footprint),
        "pdwc_e2": evaluate_blind_sgmc_suite(e2_oof_dots, catalogue, footprint),
        "pdwc_e3": evaluate_blind_sgmc_suite(e3_oof_dots, catalogue, footprint),
    }
    for b_id, b_rel in (
        ("gemsdoe32_r0", "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif"),
        ("s18_hgbr_e1", "docs/downloads/gems91-s18-hgbr-hgbr-e1-20261025T184458Z-d5b042a3-zeros.tif"),
        ("s19_svhf_e3", "docs/downloads/gems91-s19-svhf-e3-oof-20261025T194830Z-5cc11f080635-zeros.tif"),
        ("s20_lfi", "docs/downloads/gems91-s20-lfi-consensus-29671dots-20261026T014752Z-a8cc1b6e-zeros.tif"),
    ):
        bp = ROOT / b_rel
        if bp.is_file():
            with rasterio.open(bp) as ds_b:
                b_arr = np.where(np.isfinite(ds_b.read(1)), ds_b.read(1), 0.0).astype(np.float32)
            sgmc_suite[b_id] = evaluate_blind_sgmc_suite(b_arr, catalogue, footprint)

    lfi_proj = evaluate_lfi_surrogate_projection(out_tif, footprint, catalogue)

    s18_best_dti = 0.200742
    s19_best_dti = 0.147791
    s20_best_dti = 0.078916
    fh_r0_dti = (
        float(pooled["scores"]["fold_honest_r0_h274_vis2px"]["dti"])
        if "fold_honest_r0_h274_vis2px" in pooled["scores"]
        else 0.161506
    )

    beats_s18_hgbr = bool(cand_dti > s18_best_dti)
    beats_fold_honest_r0 = bool(cand_dti > fh_r0_dti)
    beats_s19_svhf = bool(cand_dti > s19_best_dti)
    beats_s20_lfi = bool(cand_dti > s20_best_dti)
    chosen_comp_unique = bool(
        chosen_screen["surface_phase"]["pass_le_090"]
        and chosen_screen["dots_phase_competitive"]["pass_competitive_uniqueness"]
    )

    verdict = (
        "promote"
        if (tech_pass and canary_report["overall_pass_le_090"] and chosen_comp_unique and beats_s18_hgbr)
        else "negative"
    )

    note_str = (
        f"GEMS91 S21-PDWC ({chosen_exp}): Cauchy-Hilbert DCWF+B15 updip+LogGabor+ClayCap OOF+CELF 37654d; "
        f"hide-v2={cand_dti:.4f}"
    )[:140]
    assert len(note_str) <= 140

    elapsed_s = round(time.time() - t0, 2)
    fold_honest_r0_report = None
    if "fold_honest_r0_h274_vis2px" in pooled["scores"]:
        fold_honest_r0_report = {
            "static_full_catalogue_collared_r0": pooled["scores"]["static_fullcat_collared_r0"],
            "fold_honest_2px_vis_collared_h274": pooled["scores"]["fold_honest_r0_h274_vis2px"],
            "explanation": (
                "Static R0 (`GEMSDOE32__h33-2-b2-zeros.tif`) stripped 2,545 dots in (1,2] px around ALL 60,988 full-catalogue "
                "pixels before evaluation (`0.006697`). Applying R0's exact 2-px collar strictly to each fold's visible faults "
                "`f['visible']` on parent `H27-4` (`GEMSDOE28__h27-4-r1-solo-d2-8.tif`) recovers its true fold-honest score (`IR-S21-01`)."
            ),
        }

    holdout_payload = {
        "evaluator_module": "vendor/gems57/evaluate_holdout.py",
        "evaluator_version": eh.VERSION,
        "split_sha256": split_sha,
        "n_withheld_positives": n_withheld,
        "buffer_px": BUFFER_PX,
        "experiments_run_count": 3,
        "budget_cap_experiments": 3,
        "elapsed_seconds": elapsed_s,
        "pooled_summary": pooled,
        "per_fold_by_arm": per_fold_by_arm,
        "selected_experiment": chosen_exp,
        "comparators_same_evaluator": {
            "S18_HGBR_e1_holdout_dti": s18_best_dti,
            "fold_honest_GEMSDOE32_R0_h274_vis2px_holdout_dti": round(fh_r0_dti, 6),
            "S19_SVHF_e3_holdout_dti": s19_best_dti,
            "S20_LFI_e2_holdout_dti": s20_best_dti,
        },
        "fold_honest_r0_diagnostic_IR_S21_01": fold_honest_r0_report,
        "blind_sgmc_off_catalogue_suite": sgmc_suite,
        "lfi_surrogate_projection_not_a_score": lfi_proj,
    }
    (EVIDENCE_DIR / "holdout.json").write_text(json.dumps(holdout_payload, indent=2) + "\n")
    (EVIDENCE_DIR / "uniqueness.json").write_text(json.dumps(chosen_screen, indent=2) + "\n")
    (EVIDENCE_DIR / "validation.json").write_text(json.dumps(validation_report, indent=2) + "\n")

    card = {
        "schema_version": "gems-run-card-v2",
        "lane_id": "S21-PDWC",
        "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": "arena/a31c96c3-gemsdoe91",
        "preregistration": {
            "path": "docs/HYPOTHESES_S21_PDWC.md",
            "sha256_before_experiments": "25b06ce3945c0ee9609482aab71a92aa3a8ee0b8cdeceacffc4e66aa00ed9af0",
            "experiments_run": 3,
            "budget_max_experiments": 3,
            "elapsed_seconds": elapsed_s,
            "within_2h_budget": bool(elapsed_s < 7200.0),
        },
        "hypothesis": (
            "H21-1 + H21-2 + H21-3 (`S21-PDWC`): Signed 2-D Cauchy-Hilbert Dipping-Contact Waveform "
            "Matched-Filter Bank (`DCWF`) + Band-15 `z*cot(beta)` up-dip surface-trace projection + "
            "Kovesi multi-scale Riesz monogenic phase congruency & bispectral triad coupling (`MGPC-BICO`) + "
            "Band-15-deconfounded smectite clay-cap dip-normal baffle (`HCBA`), fused via symmetric 3-level "
            "nested spatially-blocked OOF Asymmetric Cover-Gated Log-Odds Rescue and uniqueness-capped "
            "(`<=64%`) 300 m CELF submodular dot placement (`37,654` binary `{0,1}` dots)."
        ),
        "mechanism": (
            "Inclined Basin-and-Range normal faults beneath Quaternary fill generate an analytical Cauchy-bell / "
            "Hilbert-odd potential-field horizontal-gradient waveform displaced down-dip into the hanging wall by "
            "`B15 * cot(beta)`, lock Fourier phases across `(800m, 400m, 267m)` harmonic triads, and partition "
            "conductive hanging-wall smectite clay-cap outflow (`Band 17` regressed on `Band 15`) against resistive "
            "footwall silica sealing without relying on surface scarp relief (`Band 12/19` bitwise `0.0` in `model_sub`)."
        ),
        "named_non_fault_mimic": (
            "Unfaulted dipping pluton/caldera walls and tilted welded ash-flow tuff hogbacks (`DCWF`), Pleistocene "
            "Lake Lahontan wave-cut paleoshoreline benches at ~1,330 m (`MGPC-BICO`), and closed-basin evaporite / "
            "saline playa brines in Carson and Humboldt Sinks (`HCBA`)."
        ),
        "verdict": verdict,
        "ok_to_download": bool(tech_pass and canary_report["overall_pass_le_090"] and chosen_comp_unique),
        "ok_to_submit": False,
        "organizer_confirmed_score": None,
        "holdout": {
            "score_label": "HOLDOUT-DTI",
            "evaluator_module": "vendor/gems57/evaluate_holdout.py",
            "evaluator_version": eh.VERSION,
            "split_sha256": split_sha,
            "n_withheld_positives": n_withheld,
            "selected_experiment": chosen_exp,
            "holdout_dti": round(cand_dti, 6),
            "ci95": [round(float(x), 6) for x in cand_score["ci95"]],
            "tpw": round(float(cand_score["tpw"]), 3),
            "fpw": round(float(cand_score["fpw"]), 3),
            "fnw": round(float(cand_score["fnw"]), 3),
            "per_fold": per_fold_by_arm[chosen_exp],
            "all_3_experiments": {
                k: {
                    "holdout_dti": round(float(pooled["scores"][k]["dti"]), 6),
                    "ci95": [round(float(x), 6) for x in pooled["scores"][k]["ci95"]],
                    "tpw": round(float(pooled["scores"][k]["tpw"]), 3),
                    "fpw": round(float(pooled["scores"][k]["fpw"]), 3),
                    "sum_test_emitted_dots": int(sum(r["n_emitted_in_eval_region"] for r in per_fold_by_arm[k])),
                }
                for k in ("pdwc_e1", "pdwc_e2", "pdwc_e3")
            },
            "paired_differences": pooled["paired_differences"],
            "beats_s18_hgbr_0200742": beats_s18_hgbr,
            "beats_fold_honest_r0": beats_fold_honest_r0,
            "beats_s19_svhf_0147791": beats_s19_svhf,
            "beats_s20_lfi_0078916": beats_s20_lfi,
        },
        "blind_sgmc_control": {
            "score_label": "BLIND-SGMC-CONTROL (diagnostic off-catalogue USGS SGMC faults, not organizer test set)",
            "candidate": sgmc_suite[chosen_exp],
            "comparators": {k: v for k, v in sgmc_suite.items() if k != chosen_exp},
        },
        "lfi_surrogate_projection": lfi_proj,
        "canary": {
            "n_features_tested": 82,
            "max_symmetric_auc": canary_report["overall_max_symmetric_auc"],
            "subsurface_b12_b19_max_diff": feat_meta["verified_subsurface_b12_b19_max_diff"],
            "pass": canary_report["overall_pass_le_090"],
        },
        "uniqueness": {
            "n_compared_rasters_total": chosen_screen["n_compared_rasters"],
            "n_competitive_non_blanket_rasters": chosen_screen["n_competitive_non_blanket_rasters"],
            "surface_max_abs_spearman": chosen_screen["surface_phase"]["max_abs_spearman_all_1100plus"],
            "surface_max_abs_spearman_ref": chosen_screen["surface_phase"]["max_abs_spearman_ref"],
            "dots_max_abs_spearman": chosen_screen["dots_phase_competitive"]["max_abs_spearman"],
            "dots_max_3px_overlap_competitive": chosen_screen["dots_phase_competitive"]["max_3px_overlap_all_competitive"],
            "dots_max_3px_overlap_competitive_ref": chosen_screen["dots_phase_competitive"]["max_3px_overlap_all_competitive_ref"],
            "dots_max_3px_overlap_protocol_competitive": chosen_screen["dots_phase_competitive"]["max_3px_overlap_protocol_competitive"],
            "competitive_unique_pass": chosen_comp_unique,
            "literal_all_raster_max_3px_overlap": chosen_screen["dots_phase_literal_including_synthetic_blankets"]["max_3px_overlap_literal"],
            "literal_all_raster_max_ref": chosen_screen["dots_phase_literal_including_synthetic_blankets"]["max_3px_overlap_literal_ref"],
            "pass": bool(chosen_screen["dots_phase_literal_including_synthetic_blankets"]["literal_exceed_count"] == 0),
        },
        "validator": {
            "automated_without_human_intervention": True,
            "crs": fmt_g57["crs"],
            "shape": [fmt_g57["height"], fmt_g57["width"]],
            "transform": fmt_g57["transform"],
            "dtype": fmt_g57["dtype"],
            "nodata": fmt_g57["nodata"],
            "no_nan_inside_footprint": bool(rel_g91["no_nan_inside_footprint"]),
            "nan_pixels_total": int(fmt_g57["nan_pixels"]),
            "infinity_pixels_total": int(fmt_g57["infinity_pixels"]),
            "values_in_0_1": bool(rel_g91["values_within_0_1"]),
            "min_value": float(fmt_g57["min"]),
            "max_value": float(fmt_g57["max"]),
            "crs_shape_transform_match": bool(
                rel_g91["crs_matches_template"]
                and rel_g91["shape_matches_template"]
                and rel_g91["transform_matches_template"]
            ),
            "zero_catalogue_mass": bool(rel_g91["zero_catalogue_mass"]),
            "min_catalogue_distance_px": round(float(rel_g91["min_catalogue_distance_px"]), 4),
            "n_dots": int(rel_g91["n_dots"]),
            "pass": tech_pass,
        },
        "raster_sha256": writer_meta["sha256"],
        "submission": {
            "name": stem,
            "file": f"docs/downloads/{out_tif.name}",
            "tif_file": f"docs/downloads/{out_tif.name}",
            "zip_file": f"docs/downloads/{out_zip.name}",
            "tif_bytes": int(out_tif.stat().st_size),
            "zip_bytes": int(out_zip.stat().st_size),
            "sha256": writer_meta["sha256"],
            "zip_sha256": validation_report["zip_check"]["zip_sha256"],
            "note": note_str,
            "note_length": len(note_str),
        },
        "gates": {
            "format": {"pass": tech_pass},
            "canary": {"pass": canary_report["overall_pass_le_090"]},
            "competitive_uniqueness_1100plus": {"pass": chosen_comp_unique},
            "literal_registry_including_blanket_lattice": {
                "pass": bool(chosen_screen["dots_phase_literal_including_synthetic_blankets"]["literal_exceed_count"] == 0)
            },
            "holdout_beats_s18_hgbr": {"pass": beats_s18_hgbr},
            "holdout_beats_fold_honest_r0": {"pass": beats_fold_honest_r0},
            "holdout_beats_s19_svhf": {"pass": beats_s19_svhf},
            "weekly_slot_selector_receipt": {"pass": False},
        },
        "template_pins_verified": pins,
    }
    card["ok_to_submit"] = submission_ready(card)
    (ROOT / "docs/run-card-S21-PDWC.json").write_text(json.dumps(card, indent=2) + "\n")

    print(
        f"[S21-PDWC] COMPLETE in {elapsed_s:.1f}s | verdict={verdict} | "
        f"ok_to_download={card['ok_to_download']} | ok_to_submit={card['ok_to_submit']} | "
        f"HOLDOUT-DTI={cand_dti:.6f} | SGMC>500m={sgmc_suite[chosen_exp]['sgmc_dti_gt500m']:.6f} | "
        f"LFI_ridge1={lfi_proj['ridge1']['projected_value_model_only']:.4f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
