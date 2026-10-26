"""S22-XB library: PDWC66 x HGBR16 cross-breed under equalized quadrant budgets.

Preregistration: ``docs/HYPOTHESES_S22_XBREED.md`` (+ Amendment A1).

Nothing here re-implements a model or a metric.  Specialists come from
``gems91.pdwc21.fit_predict_pdwc_specialist``; scoring uses the unchanged shared evaluator
``vendor/gems57``.  This module only (a) declares the three preregistered arms, (b) loads the
label-blind feature cubes, (c) turns cached out-of-fold specialist surfaces into per-quadrant
surfaces and dots with an **equal dot budget per test quadrant**, and (d) provides the small
analytic helpers used by the evidence scripts (exact DTI algebra for nested rasters).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]

SAMPLE_TIF = ROOT / "data/official/sample_submission.tif"
EXISTING_FAULTS_TIF = ROOT / "data/official/existing_faults.tif"
FEATURES_TIF = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
GDR_CSV = ROOT / "data/external/gdr_wellspring_in_footprint.csv"
SGMC_TIF = ROOT / "data/external/derived_sgmc_faults_100m_u8.tif"
CACHE = ROOT / "data/derived/s22_cache"

EXPECTED_SPLIT_SHA256 = "c79f1acaf337fd548d0873d576a8a3c286d373ae2cb19cfce4464597d448d18a"
BUFFER_PX = 80
DOT_BUDGET = 37_654
QUAD_BUDGETS = (9_414, 9_414, 9_413, 9_413)  # equalized per test quadrant; sum == DOT_BUDGET
COLLAR_PX = 3.05

assert sum(QUAD_BUDGETS) == DOT_BUDGET


def feature_counts() -> tuple[int, int, int, int]:
    from gems91.hgbr18 import HGBR_FEATURE_NAMES
    from gems91.pdwc21 import PDWC21_FEATURE_NAMES, PDWC21_SUBSURFACE_NAMES

    return len(PDWC21_FEATURE_NAMES), len(PDWC21_SUBSURFACE_NAMES), len(HGBR_FEATURE_NAMES), 14


def arm_blocks(arm: str):
    """(full blocks, sub blocks); block key ``P`` = PDWC cube, ``H`` = HGBR cube."""
    n_p, n_psub, n_h, n_hsub = feature_counts()
    table = {
        "A": ([("P", list(range(n_p)))], [("P", list(range(n_psub)))]),
        "B": ([("H", list(range(n_h)))], [("H", list(range(n_hsub)))]),
        "C": ([("P", list(range(n_p))), ("H", list(range(n_h)))],
              [("P", list(range(n_psub))), ("H", list(range(n_hsub)))]),
    }
    return table[arm]


ARM_NAMES = ("A", "B", "C")


def compute_split_sha(folds: list[dict]) -> str:
    """Identical to ``scripts/run_s21_pdwc.py::compute_split_sha`` (the pinned split fingerprint)."""
    return hashlib.sha256(
        b"".join(
            np.packbits(f[k].ravel()).tobytes()
            for f in folds
            for k in ("region", "truth", "train", "visible")
        )
    ).hexdigest()


def load_common():
    """Footprint, catalogue and the four hide-and-recover folds of ``gems57-pooled-hide-v2``."""
    from gems57 import spatial as g57_spatial

    with rasterio.open(SAMPLE_TIF) as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(EXISTING_FAULTS_TIF) as ds:
        raw = ds.read(1)
    catalogue = np.isfinite(raw) & (raw > 0) & footprint
    folds = list(g57_spatial.folds(catalogue, footprint, buffer_px=BUFFER_PX))
    sha = compute_split_sha(folds)
    if sha != EXPECTED_SPLIT_SHA256:
        raise RuntimeError(f"hide-v2 split fingerprint mismatch: {sha}")
    return footprint, catalogue, folds


def load_cubes(footprint):
    from gems91.hgbr18 import HGBR_FEATURE_NAMES, build_or_load_hgbr_feature_memmap
    from gems91.pdwc21 import PDWC21_FEATURE_NAMES, build_or_load_pdwc21_memmap

    CACHE.mkdir(parents=True, exist_ok=True)
    xp, names_p, _ = build_or_load_pdwc21_memmap(
        features_tif=FEATURES_TIF, gdr_csv=GDR_CSV, footprint=footprint, cache_dir=CACHE)
    xh, names_h, _ = build_or_load_hgbr_feature_memmap(
        features_tif=FEATURES_TIF, gdr_csv=GDR_CSV, footprint=footprint, cache_dir=CACHE)
    assert list(names_p) == list(PDWC21_FEATURE_NAMES) and list(names_h) == list(HGBR_FEATURE_NAMES)
    return {"P": xp, "H": xh}


def hard_negative_indices(arm: str) -> tuple[list[int], list[int]]:
    """Hard-negative column positions in the concatenated block order (PDWC columns come first)."""
    from gems91.pdwc21 import PDWC21_FEATURE_NAMES

    if arm == "B":
        return [], []
    idx = {n: i for i, n in enumerate(PDWC21_FEATURE_NAMES)}
    sub = [idx["dcwf_grav_match_200m"], idx["dcwf_rtp_match_200m"], idx["hcba_cond_b15_resid"],
           idx["sub_flightline_seam_guard"]]
    full = sub + [idx["topo_steger_slope_crest_120m"], idx["topo_ptcf_200m"], idx["topo_slope_local_contrast"]]
    return full, sub


def cover_and_crest(cubes) -> tuple[np.ndarray, np.ndarray]:
    """Label-blind PDWC cover index and crest backbone on footprint pixels (shared by arms A and C)."""
    from gems91.pdwc21 import PDWC21_FEATURE_NAMES, compute_pdwc_crest_backbone_fp

    idx = {n: i for i, n in enumerate(PDWC21_FEATURE_NAMES)}
    cover = np.asarray(cubes["P"][:, idx["topo_cover_ness_index"]], dtype=np.float32)
    crest = compute_pdwc_crest_backbone_fp(cubes["P"])
    return cover, crest


def fit_path(arm: str, q: int, kind: str) -> Path:
    return CACHE / f"fit_{arm}_fold{q}_{kind}.npy"


def quadrant_surface(arm: str, q: int, footprint, cover_fp, crest_fp) -> np.ndarray:
    """Out-of-fold surface for test quadrant ``q`` (full + sub specialists, asymmetric cover rescue).

    Arm B is HGBR-only, so it uses neither the PDWC cover index nor the PDWC crest backbone: the
    rescue degenerates to the plain full-model log-odds (a pure ablation of the HGBR block).
    """
    from gems91.pdwc21 import pool_asymmetric_cover_rescue

    full = np.load(fit_path(arm, q, "full"), mmap_mode="r")
    sub = np.load(fit_path(arm, q, "sub"), mmap_mode="r")
    if arm == "B":
        cover_fp = np.zeros_like(cover_fp)
        crest_fp = np.zeros_like(crest_fp)
    return pool_asymmetric_cover_rescue(
        s1_full=full, s1_sub=sub, s2_full=None, s2_sub=None,
        cover_fp=cover_fp, crest_fp=crest_fp, sub_backbone_fp=None, footprint=footprint,
        max_cover_rescue=0.48, crest_alpha=0.18,
    )


def emit_quadrant(surface, fold: dict, footprint, q: int, method: str) -> np.ndarray:
    """Equalized per-quadrant emission: dots only inside test quadrant ``q``, budget ``QUAD_BUDGETS[q]``."""
    from gems91.pdwc21 import emit_dots_celf_submodular, emit_dots_nms

    region = np.asarray(fold["region"], dtype=bool) & footprint
    fn = {"nms": emit_dots_nms, "celf": emit_dots_celf_submodular}[method]
    return fn(surface, fold["visible"], region, budget=QUAD_BUDGETS[q],
              collar_px=COLLAR_PX, min_spacing_px=COLLAR_PX)


def stitched_oof_surface(arm: str, folds, footprint, cover_fp, crest_fp) -> np.ndarray:
    """Whole-footprint surface where every quadrant comes from the model that never saw it."""
    out = np.zeros(footprint.shape, dtype=np.float32)
    for q, f in enumerate(folds):
        sq = quadrant_surface(arm, q, footprint, cover_fp, crest_fp)
        m = np.asarray(f["region"], dtype=bool) & footprint
        out[m] = sq[m]
        del sq
    return out


# --------------------------------------------------------------------------------------------
# Exact DTI algebra for nested rasters (used by docs/s22/r0-decomposition.json)
# --------------------------------------------------------------------------------------------

def credit_from_pure_fp_step(n_before: int, n_after: int, dti_before: float, dti_after: float,
                             alpha: float = 0.2) -> float:
    """TP credit ``T`` implied by one nested step if the removed/added dots are pure false positives.

    ``DTI = T / (alpha*T + alpha*FP + beta*G)``.  Removing ``k`` pure-FP dots leaves ``T`` unchanged and
    lowers the denominator by ``alpha*k`` exactly, so ``1/DTI_after - 1/DTI_before = -alpha*k/T`` and
    ``T = alpha*k / (1/DTI_before - 1/DTI_after)`` (``k = n_before - n_after``; negative for additions).
    """
    k = n_before - n_after
    return alpha * k / (1.0 / dti_before - 1.0 / dti_after)


def predicted_dti_after_pure_fp(T: float, dti_before: float, k_removed: int, alpha: float = 0.2) -> float:
    """DTI after removing ``k_removed`` pure-FP dots (negative ``k`` adds them), given credit ``T``."""
    d_before = T / dti_before
    return T / (d_before - alpha * k_removed)
