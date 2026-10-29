#!/usr/bin/env python3
"""Session 27 (`S27-CVDC`) lane runner (preregistered in docs/s27-cvdc/preregistration.md).

Subcommands:
  features    verify SHA-256 inputs, freeze 210+ reference rasters, verify 19-band
              derivative identities, build & cache static + Stage-2 OOF features,
              and run per-quadrant Rule-4 leakage canaries.
  experiment  --exp e1|e2|e3 : evaluate candidate arm + matched controls
              (including incumbent control_s25_fabric_e2) on vendor/gems57 v3 folds.
  package     apply preregistered selection rule across {e1, e2, e3}, run Rule-1
              pre-placement surface & final-dot checks across all frozen references,
              write GeoTIFF + single-TIFF ZIP via shared writer, and emit run card.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")

import argparse
import gc
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from gems91 import cvdc27, fabric25
from gems91.capacity import capacity_bound
from gems91.io import dot_digest
from gems91.novelty import SurfaceProbe, dot_check
from gems91.pdwc21 import emit_dots_nms
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57 import grid, spatial
from vendor.gems57.submission_writer import write_submission
from vendor.gems57.validate import assert_submittable, validate

OUT = ROOT / "docs/s27-cvdc"
WORK = ROOT / "work/s27"
FEAT = WORK / "features"
S25_FEAT = WORK / "s25_features"
OOFD = WORK / "oof"

BUDGET = 37_654
SPACING_PX = 3.05
COLLAR_PX = 3.05
UNIQUENESS_CAP = 0.64
SEED = 20261029
OUTER_SEEDS = (SEED, SEED + 1, SEED + 2)
S25_SEED = 520810

HGB_PARAMS = dict(
    max_iter=220,
    learning_rate=0.055,
    max_leaf_nodes=31,
    min_samples_leaf=80,
    l2_regularization=2.0,
    early_stopping=False,
)
NEG_PER_POS = 6

S25_HGB_PARAMS = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=40,
    l2_regularization=1.0,
    early_stopping=False,
)
S25_NEG_PER_POS = 4

STAGE2_FULL_WEIGHT = 0.78
STAGE2_SUB_WEIGHT = 0.22

NOTE = "S27 CVDC contour-potential discordance+valley knickzone stitched OOF 37654 dots; research only, check run-card"
assert len(NOTE) <= 140, len(NOTE)

CONTROLS = ["control_s25_fabric_e2", "control_oof_base", "control_gravgrad"]
EXPERIMENTS = {
    "e1": "cvdc_e1_stage1_nms",
    "e2": "cvdc_e2_stage2_submod",
    "e3": "cvdc_e3_stitched_uniq_submod",
}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)


def allocate(total_budget: int, areas: list[int]) -> list[int]:
    budgets, remaining = [], int(total_budget)
    total_area = sum(areas)
    for i, a in enumerate(areas):
        q = int(round(total_budget * a / total_area)) if i < len(areas) - 1 else remaining
        budgets.append(q)
        remaining -= q
    return budgets


def verify_pinned_inputs() -> dict:
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    checked = {}
    for row in manifest["files"]:
        if row["id"] in {
            "sample_submission",
            "existing_faults",
            "training_features",
            "parent_r0_zeros",
            "sgmc_faults_control",
        }:
            p = ROOT / "data" / row["local_subpath"]
            if not p.is_file() or sha(p) != row["sha256"] or p.stat().st_size != row["bytes"]:
                raise ValueError(f"pinned input absent or drifted: {row['id']}")
            checked[row["id"]] = {
                "path": "data/" + row["local_subpath"],
                "sha256": row["sha256"],
                "bytes": row["bytes"],
            }
    return checked


def freeze_references(g) -> dict:
    """Pin all available comparison rasters by SHA-256 before candidate generation."""
    entries, missing = {}, []

    def add(path_rel: str, expected_sha: str | None, expected_bytes: int | None, tag: str, site: str | None = None):
        p = ROOT / path_rel
        if not p.is_file():
            missing.append({"path": path_rel, "tag": tag})
            return
        got = sha(p)
        if expected_sha is not None and (got != expected_sha or p.stat().st_size != expected_bytes):
            raise ValueError(f"registry bytes drift: {path_rel}")
        e = entries.setdefault(
            got,
            {"path": path_rel, "sha256": got, "bytes": p.stat().st_size, "tags": [], "sites": []},
        )
        if tag not in e["tags"]:
            e["tags"].append(tag)
        if site and site not in e["sites"]:
            e["sites"].append(site)

    inv = json.loads((ROOT / "registry/comparison_inventory.json").read_text())["files"]
    for r in inv:
        add(r["path"], r["sha256"], r["bytes"], "frozen_registry")

    nine = json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]
    for s in nine:
        add(s["local_path"], s["sha256"], s["bytes"], "nine_leader", site=s["site"])

    for p in sorted((ROOT / "docs/downloads").glob("*.tif")):
        add(str(p.relative_to(ROOT)), None, None, "prior_download")

    # Also include all restored sibling-fleet rasters from data/lfi_anchors/ (without reading scores!)
    skipped_grid_mismatch = []
    for p in sorted((ROOT / "data/lfi_anchors").glob("*.tif")):
        with rasterio.open(p) as ds:
            if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform or ds.count != 1:
                skipped_grid_mismatch.append(
                    {
                        "path": str(p.relative_to(ROOT)),
                        "shape": list(ds.shape),
                        "crs": str(ds.crs),
                        "transform": list(ds.transform)[:6],
                    }
                )
                continue
        add(str(p.relative_to(ROOT)), None, None, "fleet_anchor_raster")

    refs = sorted(entries.values(), key=lambda e: e["path"])
    for e in refs:
        arr = reference_array(e, g)
        npos = int(((arr > 0) & g.footprint).sum())
        e["positive_pixels_in_footprint"] = npos
        e["is_dense_lattice_name"] = "lattice" in Path(e["path"]).name.lower()
        e["is_dense_blanket"] = bool(npos > 90_000 or e["is_dense_lattice_name"])
        del arr

    result = {
        "frozen_before_candidate": True,
        "unique_byte_references": len(refs),
        "competitive_non_blanket_references": sum(1 for e in refs if not e["is_dense_blanket"]),
        "dense_blanket_references": sum(1 for e in refs if e["is_dense_blanket"]),
        "missing": missing,
        "skipped_grid_mismatch": skipped_grid_mismatch,
        "organizer_complete_registry": False,
        "dense_reference_exemptions_in_data": False,
        "files": refs,
    }
    dump(OUT / "frozen-registry.json", result)
    return result


def load_frozen_references() -> dict:
    result = json.loads((OUT / "frozen-registry.json").read_text())
    for e in result["files"]:
        p = ROOT / e["path"]
        if not p.is_file() or sha(p) != e["sha256"]:
            raise ValueError(f"frozen reference drifted since freeze: {e['path']}")
    return result


def reference_array(entry: dict, g) -> np.ndarray:
    with rasterio.open(ROOT / entry["path"]) as ds:
        if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform or ds.count != 1:
            raise ValueError(f"grid mismatch: {entry['path']}")
        a = ds.read(1)
    if not np.isfinite(a[g.footprint]).all():
        raise ValueError(f"non-finite inside footprint: {entry['path']}")
    if (a[g.footprint] < 0).any() or (a[g.footprint] > 1).any():
        raise ValueError(f"values outside [0,1] inside footprint: {entry['path']}")
    return np.where(g.footprint, a, 0.0).astype(np.float32)


def band_identity(ds, fp: np.ndarray) -> dict:
    """Label-blind forensic verification of all 19 bands and derivative relationships."""
    def valid(a):
        return fp & np.isfinite(a) & (np.abs(a.astype(np.float64)) < 1e30)

    b03 = ds.read(3)
    b05 = ds.read(5)
    b06 = ds.read(6)
    b09 = ds.read(9)
    b11 = ds.read(11)
    b13 = ds.read(13)
    b14 = ds.read(14)
    b18 = ds.read(18)
    b12 = ds.read(12)
    b19 = ds.read(19)

    v = valid(b03) & valid(b05) & valid(b09) & valid(b11) & valid(b13) & valid(b14) & valid(b18) & valid(b12) & valid(b19)
    ve = ndi.binary_erosion(v, iterations=3)

    gy13, gx13 = np.gradient(np.where(v, b13.astype(np.float64), 0.0))
    gy14, gx14 = np.gradient(np.where(v, b14.astype(np.float64), 0.0))
    gy12, gx12 = np.gradient(np.where(v, b12.astype(np.float64), 0.0))
    lap14 = -ndi.laplace(np.where(v, b14.astype(np.float64), 0.0))

    v6 = valid(b06)
    b6_vals = b06[v6].astype(np.float64)

    report = {
        "descriptions": {str(i): ds.descriptions[i - 1] for i in range(1, 20)},
        "nodata_tag": repr(ds.nodata),
        "corr_B03_vs_hypot_grad_B14": float(np.corrcoef(b03[ve], np.hypot(gx14[ve], gy14[ve]))[0, 1]),
        "corr_B09_vs_neg_laplace_B14": float(np.corrcoef(b09[ve], lap14[ve])[0, 1]),
        "corr_B18_vs_dx_B13": float(np.corrcoef(b18[ve], gx13[ve])[0, 1]),
        "corr_B18_vs_dy_B13": float(np.corrcoef(b18[ve], gy13[ve])[0, 1]),
        "corr_B11_vs_dx_B13": float(np.corrcoef(b11[ve], gx13[ve])[0, 1]),
        "corr_B11_vs_dy_B13": float(np.corrcoef(b11[ve], gy13[ve])[0, 1]),
        "corr_hypot_B18_B11_vs_B05": float(np.corrcoef(np.hypot(b18[ve], b11[ve]), b05[ve])[0, 1]),
        "corr_B19_vs_hypot_grad_B12": float(np.corrcoef(b19[ve], np.hypot(gx12[ve], gy12[ve]))[0, 1]),
        "B06_summary": {
            "valid_in_footprint": int(v6.sum()),
            "invalid_in_footprint": int((fp & ~v6).sum()),
            "min": float(b6_vals.min()),
            "median": float(np.median(b6_vals)),
            "max": float(b6_vals.max()),
            "excluded_from_s27_features": True,
            "reason": "Strictly positive [2.95, 88.57]; verified r=0.99699 with radiometric Total Count (IR-8E8-09), not magnetic tilt angle.",
        },
        "B18_B11_forensic_note": (
            "(B18, B11) correlate r=0.9481 and r=0.9380 with (dx B13, dy B13) despite "
            "header tags naming B11 'iso_grav_anom_vg'; S27 uses masked Laplacian of B13 "
            "for vertical gravity curvature."
        ),
        "eroded_comparison_pixels": int(ve.sum()),
    }
    dump(OUT / "band-identity.json", report)
    return report


def feat_path(name: str, folder: Path = FEAT) -> Path:
    return folder / f"{name}.npy"


def load_feat(name: str, folder: Path = FEAT, mmap: bool = True) -> np.ndarray:
    return np.load(feat_path(name, folder), mmap_mode="r" if mmap else None)


def _gather(names: list[str], flat_idx: np.ndarray, folder: Path = FEAT, extra: dict[str, np.ndarray] | None = None) -> np.ndarray:
    X = np.empty((len(flat_idx), len(names)), dtype=np.float32)
    for j, n in enumerate(names):
        if extra is not None and n in extra:
            X[:, j] = extra[n].ravel()[flat_idx]
        else:
            X[:, j] = load_feat(n, folder=folder).ravel()[flat_idx]
    return X


def _train_one(
    names: list[str],
    train_mask: np.ndarray,
    catalogue: np.ndarray,
    seed: int,
    *,
    hgb_params: dict,
    neg_per_pos: int,
    folder: Path = FEAT,
    extra: dict[str, np.ndarray] | None = None,
):
    flat_cat = catalogue.ravel()
    flat_train = train_mask.ravel()
    pos = np.flatnonzero(flat_train & flat_cat)
    pool = np.flatnonzero(flat_train & ~flat_cat)
    rng = np.random.default_rng(seed)
    neg = rng.choice(pool, size=min(neg_per_pos * len(pos), len(pool)), replace=False)
    idx = np.concatenate([pos, neg])
    y = np.concatenate([np.ones(len(pos), np.int8), np.zeros(len(neg), np.int8)])
    X = _gather(names, idx, folder=folder, extra=extra)
    model = HistGradientBoostingClassifier(random_state=seed, **hgb_params)
    model.fit(X, y)
    return model, {"n_positive": int(len(pos)), "n_negative": int(len(neg)), "seed": int(seed)}


def _predict_into(
    model,
    names: list[str],
    pred_mask: np.ndarray,
    out_flat: np.ndarray,
    *,
    folder: Path = FEAT,
    extra: dict[str, np.ndarray] | None = None,
) -> np.ndarray:
    idx = np.flatnonzero(pred_mask.ravel())
    for lo in range(0, len(idx), 250_000):
        chunk = idx[lo : lo + 250_000]
        out_flat[chunk] += model.predict_proba(_gather(names, chunk, folder=folder, extra=extra))[:, 1].astype(np.float64)
    return out_flat


def build_stage1_and_stage2_oof(g, folds) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    """Build cached Stage-1 OOF surface, Stage-2 nested OOF surface, and stitched Stage-2 feature maps."""
    OOFD.mkdir(parents=True, exist_ok=True)
    p1_cache = OOFD / "cvdc_stage1_oof.npy"
    p2_cache = OOFD / "cvdc_stage2_oof.npy"
    s2_feat_dir = WORK / "s2_oof_features"
    s2_feat_dir.mkdir(parents=True, exist_ok=True)

    full_static = list(cvdc27.ALL_STATIC_FEATURES)
    sub_static = list(cvdc27.PURE_SUBSURFACE_STATIC_FEATURES)
    s2_full_names = list(cvdc27.STAGE2_FULL_FEATURES)
    s2_sub_names = list(cvdc27.STAGE2_SUB_FEATURES)
    s2_all_names = list(cvdc27.STAGE2_ALL_FEATURES)

    if p1_cache.is_file() and p2_cache.is_file() and all((s2_feat_dir / f"{n}.npy").is_file() for n in s2_all_names):
        log("Stage-1 & Stage-2 OOF surfaces cached")
        s2_maps = {n: np.load(s2_feat_dir / f"{n}.npy", mmap_mode="r") for n in s2_all_names}
        return np.load(p1_cache), np.load(p2_cache), s2_maps

    h, w = g.shape
    yy, xx = np.indices((h, w), dtype=np.int32)
    inner_block = ((yy // 60) + (xx // 60)) % 3
    del yy, xx

    stitched_p1 = np.zeros((h, w), dtype=np.float64)
    stitched_p2 = np.zeros((h, w), dtype=np.float64)
    stitched_s2_feats = {n: np.full((h, w), np.nan, dtype=np.float32) for n in s2_all_names}
    receipts = []

    for fidx, fold in enumerate(folds):
        t0 = time.monotonic()
        train_mask = fold["train"]
        reg_mask = fold["region"]

        # 1. Outer Stage-1 Full (3 seeds) & Pure-Subsurface (3 seeds) -> predict on fold["region"]
        reg_p1_full_flat = np.zeros(h * w, dtype=np.float64)
        reg_p1_sub_flat = np.zeros(h * w, dtype=np.float64)
        for seed in OUTER_SEEDS:
            m_full, r_f = _train_one(full_static, train_mask, g.catalogue, seed, hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS)
            _predict_into(m_full, full_static, reg_mask, reg_p1_full_flat)
            del m_full
            m_sub, r_s = _train_one(sub_static, train_mask, g.catalogue, seed, hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS)
            _predict_into(m_sub, sub_static, reg_mask, reg_p1_sub_flat)
            del m_sub
            receipts.append({"fold": fidx, "stage": "outer_s1", "seed": seed, "full": r_f, "sub": r_s})

        reg_p1_full = (reg_p1_full_flat / len(OUTER_SEEDS)).reshape((h, w)).astype(np.float32)
        reg_p1_sub = (reg_p1_sub_flat / len(OUTER_SEEDS)).reshape((h, w)).astype(np.float32)
        del reg_p1_full_flat, reg_p1_sub_flat
        stitched_p1[reg_mask] = reg_p1_full[reg_mask]

        # 2. Inner 3-fold spatial block Stage-1 OOF on fold["train"] -> zero Stage-1 overfitting!
        tr_p1_full_flat = np.zeros(h * w, dtype=np.float64)
        tr_p1_sub_flat = np.zeros(h * w, dtype=np.float64)
        for ib in range(3):
            in_val = train_mask & (inner_block == ib)
            in_tr = train_mask & (inner_block != ib)
            m_if, _ = _train_one(full_static, in_tr, g.catalogue, SEED + ib, hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS)
            _predict_into(m_if, full_static, in_val, tr_p1_full_flat)
            del m_if
            m_is, _ = _train_one(sub_static, in_tr, g.catalogue, SEED + ib, hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS)
            _predict_into(m_is, sub_static, in_val, tr_p1_sub_flat)
            del m_is

        tr_p1_full = tr_p1_full_flat.reshape((h, w)).astype(np.float32)
        tr_p1_sub = tr_p1_sub_flat.reshape((h, w)).astype(np.float32)
        del tr_p1_full_flat, tr_p1_sub_flat

        # 3. Compute directional axial-bridge Stage-2 features separately on train canvas & region canvas!
        tr_s2 = {}
        tr_s2.update(cvdc27.stage2_axial_features(tr_p1_full, train_mask, "s2_full"))
        tr_s2.update(cvdc27.stage2_axial_features(tr_p1_sub, train_mask, "s2_sub"))
        del tr_p1_full, tr_p1_sub

        reg_s2 = {}
        reg_s2.update(cvdc27.stage2_axial_features(reg_p1_full, g.footprint & reg_mask, "s2_full"))
        reg_s2.update(cvdc27.stage2_axial_features(reg_p1_sub, g.footprint & reg_mask, "s2_sub"))
        del reg_p1_full, reg_p1_sub

        for n in s2_all_names:
            stitched_s2_feats[n][reg_mask] = reg_s2[n][reg_mask]

        # 4. Fit Outer Stage-2 Full (46 features) & Pure-Subsurface (23 B12/B19-free features)
        s2_model_full_cols = full_static + s2_all_names
        s2_model_sub_cols = sub_static + s2_sub_names

        reg_p2_full_flat = np.zeros(h * w, dtype=np.float64)
        reg_p2_sub_flat = np.zeros(h * w, dtype=np.float64)
        for seed in OUTER_SEEDS:
            m2_f, r2_f = _train_one(
                s2_model_full_cols, train_mask, g.catalogue, seed + 100,
                hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS, extra=tr_s2
            )
            _predict_into(m2_f, s2_model_full_cols, reg_mask, reg_p2_full_flat, extra=reg_s2)
            del m2_f

            m2_s, r2_s = _train_one(
                s2_model_sub_cols, train_mask, g.catalogue, seed + 200,
                hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS, extra=tr_s2
            )
            _predict_into(m2_s, s2_model_sub_cols, reg_mask, reg_p2_sub_flat, extra=reg_s2)
            del m2_s
            receipts.append({"fold": fidx, "stage": "outer_s2", "seed": seed, "full": r2_f, "sub": r2_s})

        p2_blend = (
            STAGE2_FULL_WEIGHT * (reg_p2_full_flat / len(OUTER_SEEDS))
            + STAGE2_SUB_WEIGHT * (reg_p2_sub_flat / len(OUTER_SEEDS))
        ).reshape((h, w))
        stitched_p2[reg_mask] = p2_blend[reg_mask]
        del tr_s2, reg_s2, reg_p2_full_flat, reg_p2_sub_flat, p2_blend
        gc.collect()
        log(f"  Stage-1+Stage-2 fold{fidx} completed in {time.monotonic()-t0:.1f}s")

    surf_p1 = np.where(g.footprint, np.clip(stitched_p1, 0.0, 1.0), 0.0).astype(np.float32)
    surf_p2 = np.where(g.footprint, np.clip(stitched_p2, 0.0, 1.0), 0.0).astype(np.float32)
    if not np.isfinite(surf_p1).all() or not np.isfinite(surf_p2).all():
        raise ValueError("non-finite OOF surface")
    np.save(p1_cache, surf_p1)
    np.save(p2_cache, surf_p2)
    for n, arr in stitched_s2_feats.items():
        np.save(s2_feat_dir / f"{n}.npy", arr)
    dump(
        OUT / "oof-stage1-stage2-receipt.json",
        {
            "outer_seeds": list(OUTER_SEEDS),
            "hgb_params": HGB_PARAMS,
            "neg_per_pos": NEG_PER_POS,
            "stage2_blend": {"full": STAGE2_FULL_WEIGHT, "pure_subsurface": STAGE2_SUB_WEIGHT},
            "folds": receipts,
        },
    )
    s2_maps = {n: np.load(s2_feat_dir / f"{n}.npy", mmap_mode="r") for n in s2_all_names}
    return surf_p1, surf_p2, s2_maps


def oof_control_base(g, folds) -> np.ndarray:
    OOFD.mkdir(parents=True, exist_ok=True)
    cache = OOFD / "control_oof_base.npy"
    if cache.is_file():
        return np.load(cache)
    names = list(cvdc27.BASE_FEATURES)
    out = np.zeros(g.shape, dtype=np.float64)
    for fidx, fold in enumerate(folds):
        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        for seed in OUTER_SEEDS:
            m, _ = _train_one(names, fold["train"], g.catalogue, seed, hgb_params=HGB_PARAMS, neg_per_pos=NEG_PER_POS)
            _predict_into(m, names, fold["region"], acc)
            del m
        out += (acc / len(OUTER_SEEDS)).reshape(g.shape)
        del acc
        log(f"  control_oof_base fold{fidx} done")
    surf = np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)
    np.save(cache, surf)
    return surf


def oof_control_s25_fabric_e2(g, folds) -> np.ndarray:
    """Reproduce incumbent S25-FABRIC E2 OOF surface on identical v3 folds."""
    OOFD.mkdir(parents=True, exist_ok=True)
    cache = OOFD / "control_s25_fabric_e2.npy"
    if cache.is_file():
        return np.load(cache)
    S25_FEAT.mkdir(parents=True, exist_ok=True)
    s25_meta_path = WORK / "s25_feature_groups.json"
    if not s25_meta_path.is_file():
        log("building S25-FABRIC incumbent features for matched v3 control")
        with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
            gr25, _ = fabric25.build_all(
                lambda i: ds.read(i),
                g.footprint,
                lambda name, arr: np.save(feat_path(name, S25_FEAT), arr),
            )
        dump(s25_meta_path, gr25)
    gr25 = json.loads(s25_meta_path.read_text())
    names25 = list(gr25["base"]) + list(gr25["new"])
    out = np.zeros(g.shape, dtype=np.float64)
    for fidx, fold in enumerate(folds):
        acc = np.zeros(g.shape[0] * g.shape[1], dtype=np.float64)
        m, _ = _train_one(
            names25, fold["train"], g.catalogue, S25_SEED,
            hgb_params=S25_HGB_PARAMS, neg_per_pos=S25_NEG_PER_POS, folder=S25_FEAT
        )
        _predict_into(m, names25, fold["region"], acc, folder=S25_FEAT)
        del m
        out += acc.reshape(g.shape)
        del acc
        log(f"  control_s25_fabric_e2 fold{fidx} done")
    surf = np.where(g.footprint, np.clip(out, 0.0, 1.0), 0.0).astype(np.float32)
    np.save(cache, surf)
    return surf


def competitive_halo_words(g) -> tuple[np.ndarray, int]:
    cache = WORK / "comp_halo_words.npy"
    refs = load_frozen_references()
    comp_entries = [e for e in refs["files"] if not e["is_dense_blanket"]]
    if cache.is_file():
        words = np.load(cache)
        return words, len(comp_entries)
    log(f"building <=3.0 px bit-packed halo matrix across {len(comp_entries)} competitive rasters")
    masks = [(reference_array(e, g) > 0) & g.footprint for e in comp_entries]
    words = cvdc27.build_reference_halo_words(masks, g.footprint, radius_px=3.0)
    del masks
    gc.collect()
    np.save(cache, words)
    return words, len(comp_entries)


# ---------------------------------------------------------------- subcommands
def cmd_features(_args) -> int:
    start = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    FEAT.mkdir(parents=True, exist_ok=True)
    if (OUT / "feature-receipt.json").exists():
        raise RuntimeError("S27 features already recorded; no implicit rebuild")

    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    log("freezing all registry, nine-leader, download, and anchor rasters")
    freeze_references(g)

    with rasterio.open(ROOT / "data/bridge/gems-geodawn-numerical-features.tif") as ds:
        if ds.shape != g.shape or str(ds.crs) != str(g.crs) or ds.transform != g.transform:
            raise ValueError("feature grid mismatch")
        log("verifying 19-band derivative identities (label-blind)")
        band_identity(ds, g.footprint)
        log("building 34 static S27-CVDC features")
        groups, meta = cvdc27.build_all_static_features(
            lambda i: ds.read(i),
            g.footprint,
            lambda name, arr: np.save(feat_path(name, FEAT), arr),
        )

    meta["inputs_verified"] = inputs
    meta["preregistration"] = {
        "path": "docs/s27-cvdc/preregistration.md",
        "sha256": sha(ROOT / "docs/s27-cvdc/preregistration.md"),
    }
    dump(OUT / "feature-receipt.json", meta)
    log(f"static features built in {time.monotonic()-start:.1f}s; building Stage-1 & Stage-2 OOF surfaces")

    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    _, _, s2_maps = build_stage1_and_stage2_oof(g, folds)

    log("running Rule-4 per-quadrant leakage canaries on all 34 static + 12 Stage-2 + surface features")
    canaries, max_sym, worst = [], 0.0, None
    static_names = groups["all_static"] + groups["surfaces"]
    for name in static_names + list(cvdc27.STAGE2_ALL_FEATURES):
        arr = s2_maps[name] if name in s2_maps else load_feat(name, FEAT)
        pooled_pos_parts, pooled_neg_parts = [], []
        for fidx, fold in enumerate(folds):
            valid = g.footprint & fold["region"] & ~fold["visible"]
            pos_v = np.asarray(arr[fold["truth"] & valid], dtype=np.float64)
            neg_all = np.nonzero(~fold["truth"] & valid)
            sel = np.arange(len(neg_all[0]))[::4]
            neg_v = np.asarray(arr[neg_all[0][sel], neg_all[1][sel]], dtype=np.float64)
            pos_v = pos_v[np.isfinite(pos_v)]
            neg_v = neg_v[np.isfinite(neg_v)]
            pooled_pos_parts.append(pos_v)
            pooled_neg_parts.append(neg_v)
            row = {
                "feature": name,
                "fold": fidx,
                "n_positive_finite": int(len(pos_v)),
                "n_negative_finite": int(len(neg_v)),
            }
            if len(pos_v) >= 10 and len(neg_v) >= 10:
                y = np.concatenate([np.ones(len(pos_v)), np.zeros(len(neg_v))])
                s = np.concatenate([pos_v, neg_v])
                auc = float(roc_auc_score(y, s))
                sym = max(auc, 1.0 - auc)
                row.update({"auc": auc, "symmetric_auc": sym, "status": "MEASURED"})
                if sym > max_sym:
                    max_sym, worst = sym, f"{name} fold{fidx}"
            else:
                row.update({"auc": None, "symmetric_auc": None, "status": "UNVERIFIED_TOO_FEW_FINITE"})
            canaries.append(row)
        p_pos = np.concatenate(pooled_pos_parts)
        p_neg = np.concatenate(pooled_neg_parts)
        p_row = {
            "feature": name,
            "fold": "pooled",
            "n_positive_finite": int(len(p_pos)),
            "n_negative_finite": int(len(p_neg)),
        }
        if len(p_pos) >= 10 and len(p_neg) >= 10:
            yp = np.concatenate([np.ones(len(p_pos)), np.zeros(len(p_neg))])
            sp = np.concatenate([p_pos, p_neg])
            p_auc = float(roc_auc_score(yp, sp))
            p_sym = max(p_auc, 1.0 - p_auc)
            p_row.update({"auc": p_auc, "symmetric_auc": p_sym, "status": "MEASURED"})
            if p_sym > max_sym:
                max_sym, worst = p_sym, f"{name} pooled"
        else:
            p_row.update({"auc": None, "symmetric_auc": None, "status": "UNVERIFIED_TOO_FEW_FINITE"})
        canaries.append(p_row)
        del arr

    canary_pass = bool(max_sym <= 0.90 and all(r["status"] == "MEASURED" for r in canaries))
    dump(
        OUT / "canaries.json",
        {
            "max_symmetric_auc": float(max_sym),
            "worst": worst,
            "all_pass": canary_pass,
            "n_features_tested": len(static_names) + len(cvdc27.STAGE2_ALL_FEATURES),
            "n_fold_checks": len(canaries),
            "threshold": 0.90,
            "evaluator_version": EH.VERSION,
            "split_version": folds[0]["receipt"]["split_version"],
            "canaries": canaries,
        },
    )
    log(f"canaries: max symmetric AUC {max_sym:.4f} ({worst}) pass={canary_pass}")
    if not canary_pass:
        dump(
            OUT / "run-card.json",
            {
                "schema": "gems-parallel-run-card-v1",
                "lane": "S27-CVDC (self-assigned)",
                "verdict": "negative",
                "stop_reason": "leakage canary > 0.90 or unverified feature",
                "ok_to_submit": False,
                "ok_to_download": False,
                "raster_sha256": None,
                "leakage_canary": {"max_symmetric_auc": float(max_sym), "worst": worst},
            },
        )
        return 2
    return 0


def _arm_oof_surface_and_emitter(arm: str, g, folds):
    surf_p1, surf_p2, _ = build_stage1_and_stage2_oof(g, folds)
    if arm == "cvdc_e1_stage1_nms":
        return surf_p1, "nms", False, False
    if arm == "cvdc_e2_stage2_submod":
        return surf_p2, "submod", False, False
    if arm == "cvdc_e3_stitched_uniq_submod":
        return surf_p2, "submod", True, True
    if arm == "control_s25_fabric_e2":
        return oof_control_s25_fabric_e2(g, folds), "nms", False, False
    if arm == "control_oof_base":
        return oof_control_base(g, folds), "nms", False, False
    if arm == "control_gravgrad":
        return np.asarray(load_feat("surface_gravgrad", FEAT, mmap=False), dtype=np.float32), "nms", False, False
    raise ValueError(f"unknown arm: {arm}")


def emit_for_arm(
    arm: str,
    surf: np.ndarray,
    visible_faults: np.ndarray,
    eligible_mask: np.ndarray,
    budget: int,
    *,
    halo_words: np.ndarray | None = None,
    n_refs: int = 0,
) -> np.ndarray:
    if arm in ("cvdc_e1_stage1_nms", "control_s25_fabric_e2", "control_oof_base", "control_gravgrad"):
        return emit_dots_nms(
            surf, visible_faults, eligible_mask,
            budget=budget, collar_px=COLLAR_PX, min_spacing_px=SPACING_PX
        )
    if arm == "cvdc_e2_stage2_submod":
        return cvdc27.emit_dots_celf_submodular(
            surf, visible_faults, eligible_mask,
            budget=budget, collar_px=COLLAR_PX, min_spacing_px=SPACING_PX,
            farfield_ramp=False, ref_halo_words=None, n_refs=0
        )
    if arm == "cvdc_e3_stitched_uniq_submod":
        return cvdc27.emit_dots_celf_submodular(
            surf, visible_faults, eligible_mask,
            budget=budget, collar_px=COLLAR_PX, min_spacing_px=SPACING_PX,
            farfield_ramp=True, ref_halo_words=halo_words, n_refs=n_refs,
            uniqueness_cap=UNIQUENESS_CAP
        )
    raise ValueError(f"unknown arm: {arm}")


def cmd_experiment(args) -> int:
    start = time.monotonic()
    exp = args.exp
    outdir = OUT / exp
    outdir.mkdir(parents=True, exist_ok=True)
    if (outdir / "holdout.json").exists():
        raise RuntimeError(f"{exp} already recorded; no implicit rerun")
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("leakage canary failed; lane stopped")

    verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    fold_receipts = [f["receipt"] for f in folds]
    cand = EXPERIMENTS[exp]
    arms = [cand] + CONTROLS
    areas = [int((g.footprint & f["region"]).sum()) for f in folds]
    budgets = allocate(BUDGET, areas)

    WORK.mkdir(parents=True, exist_ok=True)
    terms_file = WORK / "holdout-terms.npz"
    per_fold_cache_file = WORK / "per-fold-cache.json"
    terms_by_arm = {}
    per_fold_cache = {}
    if terms_file.is_file():
        with np.load(terms_file) as z:
            terms_by_arm = {k: z[k] for k in z.files}
    if per_fold_cache_file.is_file():
        per_fold_cache = json.loads(per_fold_cache_file.read_text())

    halo_words, n_refs = (competitive_halo_words(g) if cand == "cvdc_e3_stitched_uniq_submod" else (None, 0))

    for arm in arms:
        if arm in terms_by_arm and arm in per_fold_cache:
            log(f"holdout terms cached: {arm}")
            continue
        surf, _em_type, _ff, _uc = _arm_oof_surface_and_emitter(arm, g, folds)
        total_terms = None
        arm_rows = []
        for fidx, fold in enumerate(folds):
            pred = emit_for_arm(
                arm,
                surf,
                fold["visible"],
                g.footprint & fold["region"],
                budgets[fidx],
                halo_words=halo_words if arm == "cvdc_e3_stitched_uniq_submod" else None,
                n_refs=n_refs if arm == "cvdc_e3_stitched_uniq_submod" else 0,
            )
            res, terms = EH.evaluate(pred, fold, g.footprint, block_side=200, origin=(0, 0), global_shape=g.shape)
            total_terms = terms if total_terms is None else total_terms + terms
            arm_rows.append(
                {
                    "arm": arm,
                    "fold": fidx,
                    "budget": budgets[fidx],
                    "n_truth": int(res["n_truth"]),
                    "n_emitted": int(res["n_emitted"]),
                    "dti": float(res["dti"]),
                    "tpw": float(res["tpw"]),
                    "fpw": float(res["fpw"]),
                    "fnw": float(res["fnw"]),
                }
            )
            log(f"  scored {arm} fold{fidx}: dti={res['dti']:.6f} emitted={res['n_emitted']}")
        terms_by_arm[arm] = total_terms
        per_fold_cache[arm] = arm_rows
        np.savez_compressed(terms_file, **terms_by_arm)
        dump(per_fold_cache_file, per_fold_cache)
        del surf
        gc.collect()

    del halo_words
    gc.collect()

    sub = {a: terms_by_arm[a] for a in arms}
    pooled = EH.pooled_summary(sub, draws=1000, seed=SEED, candidate=cand)
    pooled["per_fold"] = [row for a in arms for row in per_fold_cache[a]]
    pooled["fold_receipts"] = fold_receipts
    pooled["matched_controls"] = CONTROLS
    pooled["budget_total"] = BUDGET
    pooled["elapsed_seconds"] = float(time.monotonic() - start)
    dump(outdir / "holdout.json", pooled)
    for a in arms:
        s = pooled["scores"][a]
        log(f"{a}: HOLDOUT-DTI {s['dti']:.6f} [{s['ci95'][0]:.6f}, {s['ci95'][1]:.6f}]")
    for c in CONTROLS:
        d = pooled["paired_differences"][c]
        log(f"  delta vs {c}: {d['delta']:+.6f} [{d['ci95'][0]:+.6f}, {d['ci95'][1]:+.6f}]")
    return 0


def _evaluate_uniqueness_for_candidate(surf: np.ndarray, final: np.ndarray, refs: dict, g):
    probe = SurfaceProbe(surf, g.footprint)
    final_probe = SurfaceProbe(final, g.footprint)
    surface_checks, max_rho, max_rho_path = [], 0.0, None
    dot_checks, max_ov, max_ov_path = [], 0.0, None
    max_dot_rho, max_dot_rho_path = 0.0, None

    for entry in refs["files"]:
        ref = reference_array(entry, g)
        s_res = probe.compare(ref)
        rho = s_res.get("rank_correlation")
        if rho is not None and abs(rho) > max_rho:
            max_rho, max_rho_path = abs(rho), entry["path"]
        surface_checks.append(
            {"path": entry["path"], "tags": entry["tags"], "sites": entry["sites"], **s_res}
        )

        d_rho_res = final_probe.compare(ref)
        d_rho = d_rho_res.get("rank_correlation")
        if d_rho is not None and abs(d_rho) > max_dot_rho:
            max_dot_rho, max_dot_rho_path = abs(d_rho), entry["path"]

        d_res = dot_check(final, ref, g.footprint)
        del ref
        ov = d_res.get("overlap_within_3px")
        if ov is not None and ov > max_ov:
            max_ov, max_ov_path = float(ov), entry["path"]
        dot_checks.append(
            {
                "path": entry["path"],
                "tags": entry["tags"],
                "sites": entry["sites"],
                "reference_positive_pixels": entry["positive_pixels_in_footprint"],
                "is_dense_blanket": entry["is_dense_blanket"],
                "is_dense_lattice_name": entry["is_dense_lattice_name"],
                "dot_rank_correlation": d_rho,
                **{k: (float(v) if isinstance(v, float) else v) for k, v in d_res.items()},
            }
        )

    nine_checks = [r for r in dot_checks if r["sites"]]
    comp_checks = [
        r for r in dot_checks if r.get("overlap_within_3px") is not None and not r["is_dense_blanket"]
    ]
    dense_checks = [r for r in dot_checks if r["is_dense_blanket"]]
    nine_max = max((r["overlap_within_3px"] for r in nine_checks if r.get("overlap_within_3px") is not None), default=None)
    comp_max = max((r["overlap_within_3px"] for r in comp_checks), default=None)
    comp_closest = max(comp_checks, key=lambda r: r["overlap_within_3px"])["path"] if comp_checks else None

    return {
        "surface_checks": surface_checks,
        "surface_max_abs_rho": float(max_rho),
        "surface_closest": max_rho_path,
        "surface_pass": bool(max_rho <= 0.90),
        "dot_checks": dot_checks,
        "final_dot_max_abs_rho": float(max_dot_rho),
        "final_dot_rho_closest": max_dot_rho_path,
        "final_dot_rho_pass": bool(max_dot_rho <= 0.90),
        "max_ov_all": float(max_ov),
        "closest_all": max_ov_path,
        "nine_max": nine_max,
        "comp_max": comp_max,
        "comp_closest": comp_closest,
        "nine_checks": nine_checks,
        "dense_checks": dense_checks,
    }


def cmd_package(_args) -> int:
    start = time.monotonic()
    if (OUT / "run-card.json").exists():
        raise RuntimeError("run card already recorded; no implicit rerun")
    can = json.loads((OUT / "canaries.json").read_text())
    if not can["all_pass"]:
        raise RuntimeError("canaries did not pass")
    inputs = verify_pinned_inputs()
    g = grid.load_grid(ROOT / "data/official")
    folds = list(spatial.folds(g.catalogue, g.footprint, buffer_px=80))
    refs = load_frozen_references()
    halo_words, n_refs = competitive_halo_words(g)

    # Evaluate preregistered selection rule across {e1, e2, e3}
    exp_records = {}
    for exp, arm in EXPERIMENTS.items():
        hp = OUT / exp / "holdout.json"
        if not hp.is_file():
            raise RuntimeError(f"missing experiment receipt: {hp}")
        hh = json.loads(hp.read_text())
        best_c = hh["best_comparable_control"]
        paired_c = hh["paired_differences"][best_c]
        exp_records[exp] = {
            "exp": exp,
            "arm": arm,
            "holdout": hh,
            "dti": float(hh["scores"][arm]["dti"]),
            "ci95": hh["scores"][arm]["ci95"],
            "beats_best_control": bool(paired_c["ci95"][0] > 0.0),
        }

    # Order arms by descending HOLDOUT-DTI among those beating best_comparable_control,
    # selecting the highest-HOLDOUT-DTI arm whose stitched-OOF emission passes competitive <=0.70 uniqueness.
    ordered_exps = sorted(
        exp_records.keys(),
        key=lambda e: (1 if exp_records[e]["beats_best_control"] else 0, exp_records[e]["dti"]),
        reverse=True,
    )

    chosen_exp = None
    chosen_surf = None
    chosen_final = None
    chosen_uniq = None
    selection_trace = []

    for exp in ordered_exps:
        arm = EXPERIMENTS[exp]
        log(f"screening stitched-OOF full-footprint emission for {exp} ({arm})")
        surf, _, _, _ = _arm_oof_surface_and_emitter(arm, g, folds)
        final = emit_for_arm(
            arm,
            surf,
            g.catalogue,
            g.footprint,
            BUDGET,
            halo_words=halo_words if arm == "cvdc_e3_stitched_uniq_submod" else None,
            n_refs=n_refs if arm == "cvdc_e3_stitched_uniq_submod" else 0,
        )
        n_final = int((final > 0).sum())
        if n_final != BUDGET:
            raise RuntimeError(f"{arm}: final dot count {n_final} != {BUDGET}")
        uniq = _evaluate_uniqueness_for_candidate(surf, final, refs, g)
        comp_pass = bool(
            uniq["surface_pass"]
            and uniq["final_dot_rho_pass"]
            and uniq["comp_max"] is not None
            and uniq["comp_max"] <= 0.70
        )
        selection_trace.append(
            {
                "exp": exp,
                "arm": arm,
                "holdout_dti": exp_records[exp]["dti"],
                "beats_best_control_ci95": exp_records[exp]["beats_best_control"],
                "surface_max_abs_rho": uniq["surface_max_abs_rho"],
                "final_dot_max_abs_rho": uniq["final_dot_max_abs_rho"],
                "nine_leaders_max_3px_overlap": uniq["nine_max"],
                "competitive_max_3px_overlap": uniq["comp_max"],
                "competitive_closest": uniq["comp_closest"],
                "all_refs_max_3px_overlap": uniq["max_ov_all"],
                "passes_competitive_uniqueness": comp_pass,
            }
        )
        log(
            f"  {exp} ({arm}): holdout={exp_records[exp]['dti']:.6f} | "
            f"nine_max={uniq['nine_max']:.4f} | comp_max={uniq['comp_max']:.4f} | "
            f"all_max={uniq['max_ov_all']:.4f} | comp_pass={comp_pass}"
        )
        if comp_pass and exp_records[exp]["beats_best_control"]:
            chosen_exp, chosen_surf, chosen_final, chosen_uniq = exp, surf, final, uniq
            break
        if chosen_exp is None:
            # Keep highest-HOLDOUT fallback if none passes competitive uniqueness
            chosen_exp, chosen_surf, chosen_final, chosen_uniq = exp, surf, final, uniq

    del halo_words
    gc.collect()

    assert chosen_exp is not None and chosen_final is not None and chosen_uniq is not None
    exp = chosen_exp
    arm = EXPERIMENTS[exp]
    pooled = exp_records[exp]["holdout"]
    uniq = chosen_uniq
    final = chosen_final

    dump(
        OUT / "surface-checks.json",
        {
            "selected_exp": exp,
            "selected_arm": arm,
            "max_abs_rho": uniq["surface_max_abs_rho"],
            "closest": uniq["surface_closest"],
            "pass": uniq["surface_pass"],
            "references_checked": len(uniq["surface_checks"]),
            "checks": uniq["surface_checks"],
        },
    )
    dump(
        OUT / "final-dot-checks.json",
        {
            "selected_exp": exp,
            "selected_arm": arm,
            "selection_trace": selection_trace,
            "max_3px_overlap_all_references": uniq["max_ov_all"],
            "closest_all": uniq["closest_all"],
            "max_3px_overlap_nine_leaders": uniq["nine_max"],
            "max_3px_overlap_competitive_le_90000px": uniq["comp_max"],
            "closest_competitive": uniq["comp_closest"],
            "final_dot_max_abs_rho": uniq["final_dot_max_abs_rho"],
            "final_dot_rho_closest": uniq["final_dot_rho_closest"],
            "dense_blanket_checks": uniq["dense_checks"],
            "nine_leader_checks": uniq["nine_checks"],
            "references_checked": len(uniq["dot_checks"]),
            "checks": uniq["dot_checks"],
        },
    )

    if not uniq["surface_pass"] or not uniq["final_dot_rho_pass"]:
        dump(
            OUT / "run-card.json",
            {
                "schema": "gems-parallel-run-card-v1",
                "lane": "S27-CVDC",
                "verdict": "negative",
                "stop_reason": "rank correlation > 0.90",
                "ok_to_submit": False,
                "ok_to_download": False,
                "raster_sha256": None,
            },
        )
        return 3

    capacity = None
    lat_path = ROOT / "data/fleet_registry/calib_r13lattice_00904.tif"
    if lat_path.is_file():
        with rasterio.open(lat_path) as ds:
            la = ds.read(1)
            lat = np.isfinite(la) & (la > 0) & g.footprint
        capacity = capacity_bound(g.footprint, lat, BUDGET)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    short = dot_digest(final > 0)[:8]
    tif_name = f"gems91-s27-cvdc-{exp}-{BUDGET}dots-{stamp}-{short}-zeros.tif"
    out_tif = ROOT / "docs/downloads" / tif_name
    receipt = write_submission(
        out_tif,
        final.astype(np.float32),
        ROOT / "data/official/sample_submission.tif",
        g.footprint,
        note=NOTE,
        name=tif_name[:-4],
        catalogue=g.catalogue,
    )
    zip_path = out_tif.with_suffix(".zip")
    sidecar_path = out_tif.with_suffix(".json")
    for p_chmod in (out_tif, zip_path, sidecar_path):
        if p_chmod.is_file():
            os.chmod(p_chmod, 0o644)

    local_validation = validate(out_tif, g.footprint, g.catalogue)
    assert_submittable(local_validation)
    with rasterio.open(out_tif) as ds:
        disk = ds.read(1)
        reread = {
            "crs": str(ds.crs),
            "shape": [ds.height, ds.width],
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "transform": list(ds.transform)[:6],
            "nodata": ds.nodata,
            "nodata_is_none": ds.nodata is None,
        }
    if not np.array_equal(disk > 0, final > 0):
        raise RuntimeError("on-disk support differs from in-memory final dots")
    reread.update(
        {
            "all_finite": bool(np.isfinite(disk).all()),
            "no_nan_inside_footprint": bool(np.isfinite(disk[g.footprint]).all()),
            "values_in_0_1": bool(float(disk.min()) >= 0.0 and float(disk.max()) <= 1.0),
            "crs_shape_transform_match": bool(
                reread["crs"] == "EPSG:32611"
                and reread["shape"] == [3730, 3292]
                and reread["transform"] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
            ),
            "min": float(disk.min()),
            "max": float(disk.max()),
            "n_dots": int((disk > 0).sum()),
            "on_catalogue": int((disk[g.catalogue] > 0).sum()),
            "outside_footprint_positive": int((disk[~g.footprint] > 0).sum()),
        }
    )
    tif_sha = sha(out_tif)
    writer_receipt = {
        "file": str(out_tif.relative_to(ROOT)),
        "sha256": tif_sha,
        "bytes": out_tif.stat().st_size,
        "zip": str(zip_path.relative_to(ROOT)),
        "zip_sha256": sha(zip_path),
        "support_dot_digest": dot_digest(final > 0),
        "writer_receipt": receipt,
        "independent_validator": local_validation,
        "independent_reread": reread,
    }
    dump(OUT / "writer-receipt.json", writer_receipt)

    scores = pooled["scores"]
    best_control = pooled["best_comparable_control"]
    paired = pooled["paired_differences"][best_control]
    beats_control = bool(paired["ci95"][0] > 0.0)
    cand_score = scores[arm]

    canary_pass = bool(can["all_pass"])
    dots_pass_all = bool(uniq["max_ov_all"] <= 0.70)
    dots_pass_nine = bool(uniq["nine_max"] is not None and uniq["nine_max"] <= 0.70)
    dots_pass_competitive = bool(uniq["comp_max"] is not None and uniq["comp_max"] <= 0.70)
    validator_pass = bool(
        local_validation["all_checks_passed"]
        and reread["all_finite"]
        and reread["values_in_0_1"]
        and reread["crs_shape_transform_match"]
        and reread["on_catalogue"] == 0
        and reread["outside_footprint_positive"] == 0
    )
    # Fail-closed per Protocol Rule 1 & S26 governance: literal all-raster check
    # includes calib_r13lattice_00904.tif (>=82.34% at 37,654 dots), keeping
    # ok_to_submit False until coordinator policy & authenticated quota review.
    promote = bool(
        canary_pass
        and uniq["surface_pass"]
        and uniq["final_dot_rho_pass"]
        and dots_pass_all
        and beats_control
        and validator_pass
    )
    identity = json.loads((OUT / "band-identity.json").read_text())
    experiments_summary = {
        e: {
            "candidate_arm": rec["arm"],
            "holdout_dti": rec["dti"],
            "ci95": rec["ci95"],
            "beats_best_control_ci95": rec["beats_best_control"],
        }
        for e, rec in exp_records.items()
    }

    run_card = {
        "schema": "gems-parallel-run-card-v1",
        "lane": "S27-CVDC (preregistered in docs/s27-cvdc/preregistration.md)",
        "branch": "arena/2d335bdc-gemsdoe91",
        "preregistration": {
            "path": "docs/s27-cvdc/preregistration.md",
            "sha256": sha(ROOT / "docs/s27-cvdc/preregistration.md"),
        },
        "hypothesis": (
            "Catalogue-missing blind and subdued Basin-and-Range faults exhibit (1) Rule-of-V "
            "strike discordance where subsurface gravity/RTP-magnetic boundaries cut obliquely "
            "across detrended topographic contours, (2) localized hydrothermal magnetite-destruction "
            "troughs co-located with gravity steps, B15-deconfounded MT conductivity residuals, and "
            "transtensional strain, and (3) multi-valley aligned knickzones across adjacent incised "
            "piedmont washes."
        ),
        "mechanism": (
            f"34 NoData-masked static physics features (6 base + 18 CVDC-PMDB + 10 VCTK; B06 excluded) "
            f"+ 12 nested cross-fitted Stage-2 directional axial-bridge features (0.78 Full + 0.22 "
            f"Pure-Subsurface B12/B19-free HGB blend) -> stitched 4-fold spatially-blocked OOF surface "
            f"(zero in-sample catalogue refitting) -> {BUDGET:,} binary [0,1] dots via 300 m CELF "
            f"submodular emitter ({arm})."
        ),
        "named_non_fault_mimic": (
            "Unfaulted discordant igneous dikes/pluton margins, remanently magnetized lava flow edges, "
            "Pleistocene Lake Lahontan pluvial shoreline terraces, resistant dipping tuff beds, "
            "clay-filled paleochannels, and GeoDAWN 90-deg E-W flight-line drape variations."
        ),
        "holdout": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": EH.VERSION,
            "split_version": pooled["fold_receipts"][0]["split_version"],
            "implementation_sha256": pooled.get("implementation_sha256"),
            "selected_experiment": exp,
            "selected_arm": arm,
            "dti": cand_score["dti"],
            "ci95": cand_score["ci95"],
            "n_withheld_positives": cand_score["withheld_positive_pixels"],
            "best_matched_control": best_control,
            "best_matched_control_dti": scores[best_control]["dti"],
            "paired_difference_vs_best_control": paired,
            "paired_differences_all_controls": pooled["paired_differences"],
            "beats_best_matched_control_ci95": beats_control,
            "all_arm_scores": {a: scores[a]["dti"] for a in scores},
            "experiments_summary": experiments_summary,
            "selection_trace": selection_trace,
        },
        "leakage_canary": {
            "max_symmetric_auc": can["max_symmetric_auc"],
            "worst": can["worst"],
            "n_features_tested": can["n_features_tested"],
            "pass": canary_pass,
        },
        "correlation_overlap_vs_registry": {
            "surface_max_abs_rho": uniq["surface_max_abs_rho"],
            "surface_closest": uniq["surface_closest"],
            "surface_pass_le_0.90": uniq["surface_pass"],
            "final_dot_max_abs_rho": uniq["final_dot_max_abs_rho"],
            "final_dot_rho_closest": uniq["final_dot_rho_closest"],
            "final_dot_rho_pass_le_0.90": uniq["final_dot_rho_pass"],
            "final_dot_max_overlap_all": uniq["max_ov_all"],
            "final_dot_closest_all": uniq["closest_all"],
            "final_dot_max_overlap_nine_leaders": uniq["nine_max"],
            "final_dot_max_overlap_competitive_le_90000px": uniq["comp_max"],
            "final_dot_closest_competitive": uniq["comp_closest"],
            "final_dot_pass_nine_le_0.70": dots_pass_nine,
            "final_dot_pass_competitive_le_0.70": dots_pass_competitive,
            "final_dot_pass_all_incl_blankets_le_0.70": dots_pass_all,
            "competitive_references_checked": sum(1 for e in refs["files"] if not e["is_dense_blanket"]),
            "dense_blankets": [
                {
                    "path": r["path"],
                    "reference_positive_pixels": r.get("reference_positive_pixels"),
                    "overlap_within_3px": r.get("overlap_within_3px"),
                }
                for r in uniq["dense_checks"]
            ],
            "lattice_capacity_bound_at_budget": capacity,
            "references_unique_bytes": len(refs["files"]),
            "references_missing": refs["missing"],
            "organizer_complete_registry": False,
        },
        "band_identity": identity,
        "validator_output": {
            "no_nan_inside_footprint": reread["no_nan_inside_footprint"],
            "values_in_0_1": reread["values_in_0_1"],
            "crs_shape_transform_match": reread["crs_shape_transform_match"],
            "local": local_validation,
            "independent_reread": reread,
            "pass": validator_pass,
            "scope": "local [0,1]/CRS/shape/transform preflight; not organizer acceptance",
        },
        "raster_sha256": tif_sha,
        "submission_name": tif_name[:-4],
        "submission_note": NOTE,
        "submission_note_chars": len(NOTE),
        "artifact": {
            "tif": str(out_tif.relative_to(ROOT)),
            "zip": str(zip_path.relative_to(ROOT)),
            "zip_sha256": writer_receipt["zip_sha256"],
            "n_dots": int(reread["n_dots"]),
        },
        "organizer_confirmed_score": None,
        "estimated_leaderboard_score": None,
        "estimated_leaderboard_score_reason": (
            "No authenticated organizer receipt exists. Post-hoc LFI MODEL projection "
            "(MODEL_PROJECTION_NOT_A_SCORE) and blind USGS SGMC diagnostic are recorded "
            "separately in docs/s27-cvdc/diagnostics.json."
        ),
        "post_hoc_diagnostics_file": "docs/s27-cvdc/diagnostics.json",
        "experiments_run": len(exp_records),
        "max_experiments": 3,
        "elapsed_seconds_package": float(time.monotonic() - start),
        "submission_slots_used": 0,
        "ok_to_download": bool(validator_pass),
        "ok_to_download_scope": "research only" if validator_pass else "none",
        "ok_to_submit": bool(promote),
        "selector_review_required": True,
        "verdict": "promote" if promote else "negative",
        "inputs_verified": inputs,
    }
    dump(OUT / "run-card.json", run_card)
    dump(ROOT / "docs/run-card-S27-CVDC.json", run_card)
    log(
        f"verdict={run_card['verdict']} ok_to_submit={run_card['ok_to_submit']} "
        f"tif={tif_name} sha={tif_sha[:16]}"
    )
    print(
        json.dumps(
            {
                k: run_card[k]
                for k in (
                    "verdict",
                    "ok_to_download",
                    "ok_to_submit",
                    "raster_sha256",
                    "submission_name",
                    "submission_note",
                    "artifact",
                )
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("features")
    pe = sub.add_parser("experiment")
    pe.add_argument("--exp", required=True, choices=sorted(EXPERIMENTS))
    sub.add_parser("package")
    args = ap.parse_args()
    if args.cmd == "features":
        return cmd_features(args)
    if args.cmd == "experiment":
        return cmd_experiment(args)
    return cmd_package(args)


if __name__ == "__main__":
    raise SystemExit(main())
