"""Session 15 Method Lane (`S15-HCPA`):
Hydrothermal Convective Plume & Kinematic Dilatancy Architecture.

Pre-registration: `docs/HYPOTHESES_S15.md` (frozen prior to holdout scoring).
Protocol compliance:
- Rule 1 (Lane): S15-HCPA. Surface rank correlation <= 0.90, final dots <= 70% within 3 px of registry rasters.
- Rule 2 (Reuse): Shared holdout evaluator and submission writer reused without private forks.
- Rule 3 (Label): Every score labelled as HOLDOUT-DTI or ORGANIZER-CONFIRMED.
- Rule 4 (Leakage Canary): Every new feature tested alone on holdout (AUC <= 0.90).
- Rule 5 (Run Card): JSON run card produced with all verified fields.
- Rule 6 (Budget): 3 experiments (E1 surface, E2 corroboration, E3 winner geometry emission).
"""

from __future__ import annotations

import csv
import gc
import json
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

HCPA_FEATURE_NAMES: list[str] = [
    # Hydrothermal convective plume features
    "hcpa_cond_depth_ratio",
    "hcpa_cond_gradient",
    "hcpa_cond_plume_excess",
    "hcpa_basement_step",
    "hcpa_basement_grav_alignment",
    "hcpa_thermal_flux",
    # Tectonic kinematic dilatancy features
    "hcpa_dilation_tendency",
    "hcpa_slip_tendency",
    "hcpa_coulomb_crit_permeability",
    # Radiometric alteration & magnetic leaching
    "hcpa_rad_k_metasomatism",
    "hcpa_rad_k_th_step",
    # LiDAR microtopographic scarp asymmetry
    "hcpa_lidar_scarp_asym",
    # Multi-physics convective corridor concordance
    "hcpa_multiphys_convective_concordance",
]


def clean_band(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Zero outside footprint and scrub sentinel values."""
    out = arr.copy().astype(np.float32)
    out[~footprint] = 0.0
    out[out < -1e30] = 0.0
    out = np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)
    return out


def build_or_load_s15_feature_memmap(
    features_tif: Path,
    gdr_csv: Path,
    lidar_tif: Path,
    rad_tif: Path,
    footprint: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], dict]:
    """Build or load memory-mapped S15 HCPA feature array of shape (n_fp, 13)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_fp = int(footprint.sum())
    dat_path = cache_dir / "s15_hcpa_features_v1.dat"
    meta_path = cache_dir / "s15_hcpa_features_v1.json"

    if dat_path.is_file() and meta_path.is_file():
        expected_bytes = n_fp * len(HCPA_FEATURE_NAMES) * 4
        if dat_path.stat().st_size == expected_bytes:
            meta = json.loads(meta_path.read_text())
            mmap = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, len(HCPA_FEATURE_NAMES)))
            return mmap, HCPA_FEATURE_NAMES, meta

    t0 = time.perf_counter()
    H, W = footprint.shape

    # 1. Read required competition bands
    with rasterio.open(features_tif) as ds:
        tmi_hg = clean_band(ds.read(3), footprint) / 200.0  # SI unit fix
        geod_2nd = clean_band(ds.read(4), footprint)
        geod_shear = clean_band(ds.read(7), footprint)
        geod_dil = clean_band(ds.read(8), footprint)
        tmi_vg = clean_band(ds.read(9), footprint)
        grav_vg = clean_band(ds.read(11), footprint)
        depth_base = clean_band(ds.read(15), footprint)
        cond = clean_band(ds.read(17), footprint)
        grav_hg = clean_band(ds.read(18), footprint)

    # 2. Read LiDAR scarp stack
    with rasterio.open(lidar_tif) as ds:
        lid_step = clean_band(ds.read(3) / 255.0, footprint)
        lid_down = clean_band(ds.read(6) / 255.0, footprint)
        lid_up = clean_band(ds.read(7) / 255.0, footprint)
        lid_strike_u8 = ds.read(11)
        lid_strike_rad = (lid_strike_u8.astype(np.float32) / 255.0) * np.pi
        lid_strike_rad[~footprint] = 0.0

    # 3. Read Radiometrics
    with rasterio.open(rad_tif) as ds:
        rad_k = clean_band(ds.read(1) / 255.0, footprint)
        rad_th = clean_band(ds.read(2) / 255.0, footprint)

    # 4. Thermal springs rasterization
    spring_grid = np.zeros((H, W), dtype=np.float32)
    with gdr_csv.open("r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                r, c = int(float(row["row"])), int(float(row["col"]))
                if 0 <= r < H and 0 <= c < W and footprint[r, c]:
                    temp = float(row["temp_c"]) if row.get("temp_c") else 25.0
                    is_hot = row.get("thermalclass") in ("Hot", "Warm") or temp >= 30.0
                    if is_hot:
                        spring_grid[r, c] = max(spring_grid[r, c], max(temp - 20.0, 10.0))
            except (ValueError, KeyError):
                continue

    spring_mask = spring_grid > 0
    if spring_mask.any():
        d_spring = ndi.distance_transform_edt(~spring_mask)
        thermal_flux = np.exp(-d_spring / 50.0).astype(np.float32)
    else:
        thermal_flux = np.zeros((H, W), dtype=np.float32)
    thermal_flux[~footprint] = 0.0

    # 5. Compute feature fields
    cond_depth_ratio = cond / (1.0 + np.maximum(depth_base, 0.0) / 500.0)
    cond_dy = ndi.sobel(cond, axis=0) / 8.0
    cond_dx = ndi.sobel(cond, axis=1) / 8.0
    cond_grad = np.hypot(cond_dy, cond_dx).astype(np.float32)

    cond_lowpass = ndi.gaussian_filter(cond, sigma=15.0)
    cond_excess = np.maximum(cond - cond_lowpass, 0.0).astype(np.float32)

    depth_dy = ndi.sobel(depth_base, axis=0) / 8.0
    depth_dx = ndi.sobel(depth_base, axis=1) / 8.0
    basement_step = np.hypot(depth_dy, depth_dx).astype(np.float32)

    grav_dy = grav_vg
    grav_dx = grav_hg
    norm_base = basement_step + 1e-4
    norm_grav = np.hypot(grav_dy, grav_dx) + 1e-4
    grav_base_dot = (depth_dy * grav_dy + depth_dx * grav_dx) / (norm_base * norm_grav)
    basement_grav_alignment = np.clip(grav_base_dot, -1.0, 1.0).astype(np.float32)

    theta_ext = 1.8326
    delta_theta = lid_strike_rad - theta_ext
    dil_tendency = np.sin(delta_theta) ** 2
    slip_tendency = np.abs(np.sin(2.0 * delta_theta))

    dilation_field = (dil_tendency * np.maximum(geod_dil, 0.0)).astype(np.float32)
    slip_field = (slip_tendency * np.maximum(geod_shear, 0.0)).astype(np.float32)
    coulomb_crit = (0.6 * slip_field + 0.4 * dilation_field).astype(np.float32)

    k_over_th = rad_k / (rad_th + 0.05)
    rad_metasomatism = (k_over_th * np.maximum(-tmi_vg, 0.0)).astype(np.float32)

    log_k_th = np.log((rad_k + 0.01) / (rad_th + 0.01))
    kth_dy = ndi.sobel(log_k_th, axis=0) / 8.0
    kth_dx = ndi.sobel(log_k_th, axis=1) / 8.0
    k_th_step = np.hypot(kth_dy, kth_dx).astype(np.float32)

    lidar_asym = (np.abs(lid_down - lid_up) * lid_step).astype(np.float32)

    p_norm = cond_excess / (np.percentile(cond_excess[footprint], 95) + 1e-6)
    c_norm = coulomb_crit / (np.percentile(coulomb_crit[footprint], 95) + 1e-6)
    b_norm = basement_step / (np.percentile(basement_step[footprint], 95) + 1e-6)
    concordance = np.clip(p_norm * c_norm * b_norm, 0.0, 10.0).astype(np.float32)

    feature_arrays = [
        cond_depth_ratio,
        cond_grad,
        cond_excess,
        basement_step,
        basement_grav_alignment,
        thermal_flux,
        dilation_field,
        slip_field,
        coulomb_crit,
        rad_metasomatism,
        k_th_step,
        lidar_asym,
        concordance,
    ]

    dat_tmp = dat_path.with_suffix(".tmp")
    mmap_out = np.memmap(dat_tmp, dtype=np.float32, mode="w+", shape=(n_fp, len(HCPA_FEATURE_NAMES)))
    for idx, f_arr in enumerate(feature_arrays):
        f_arr[~footprint] = 0.0
        f_arr = np.nan_to_num(f_arr, nan=0.0, posinf=0.0, neginf=0.0)
        mmap_out[:, idx] = f_arr[footprint]
    mmap_out.flush()
    del mmap_out
    dat_tmp.replace(dat_path)

    meta = {
        "created_utc": time.strftime("%Y%m%d_%H%M%S"),
        "n_footprint_pixels": n_fp,
        "n_features": len(HCPA_FEATURE_NAMES),
        "feature_names": HCPA_FEATURE_NAMES,
        "elapsed_seconds": round(time.perf_counter() - t0, 2),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    mmap = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, len(HCPA_FEATURE_NAMES)))
    return mmap, HCPA_FEATURE_NAMES, meta


def _assemble_rows(blocks: list[tuple[np.memmap | np.ndarray, list[int] | None]], row_idx: np.ndarray) -> np.ndarray:
    """Extract features for specific row indices without concatenating full arrays."""
    parts = []
    for arr, cols in blocks:
        sub = np.asarray(arr[row_idx])
        if cols is not None:
            sub = sub[:, cols]
        parts.append(sub.astype(np.float32))
    return np.hstack(parts)


def fit_and_predict_s15_fold(
    *,
    blocks: list[tuple[np.memmap | np.ndarray, list[int] | None]],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    hard_neg_fp: np.ndarray | None = None,
    max_pos: int = 65_000,
    max_neg: int = 220_000,
    seed: int = 915,
) -> tuple[np.ndarray, dict]:
    """Train HGB ensemble on fold territory using memory-safe sampling and chunked prediction."""
    rng = np.random.default_rng(seed)
    pos_fp = visible_faults[footprint] & (~exclude_mask[footprint])
    neg_fp = (~visible_faults[footprint]) & (~exclude_mask[footprint])
    pos_all = np.flatnonzero(pos_fp)
    neg_all = np.flatnonzero(neg_fp)

    if pos_all.size == 0:
        raise ValueError("Fold has 0 visible training fault pixels")

    pi_true = float(pos_all.size) / float(pos_all.size + neg_all.size)

    pos_idx = np.sort(rng.choice(pos_all, size=min(max_pos, pos_all.size), replace=False))
    if hard_neg_fp is not None:
        hv = np.asarray(hard_neg_fp, dtype=np.float32)[neg_all]
        thr = float(np.percentile(hv, 75))
        hard_pool, easy_pool = neg_all[hv >= thr], neg_all[hv < thr]
        del hv
    else:
        hard_pool, easy_pool = neg_all[:0], neg_all

    n_hard = min(max_neg // 2, hard_pool.size)
    n_easy = min(max_neg - n_hard, easy_pool.size)
    neg_hard = np.sort(rng.choice(hard_pool, size=n_hard, replace=False)) if hard_pool.size > n_hard else hard_pool
    neg_easy = np.sort(rng.choice(easy_pool, size=n_easy, replace=False)) if easy_pool.size > n_easy else easy_pool
    neg_idx = np.concatenate([neg_hard, neg_easy])

    w_neg = np.concatenate([np.full(neg_hard.size, 0.60, np.float32), np.full(neg_easy.size, 1.40, np.float32)])

    X_train = np.vstack([_assemble_rows(blocks, pos_idx), _assemble_rows(blocks, neg_idx)])
    y_train = np.concatenate([np.ones(pos_idx.size, np.int32), np.zeros(neg_idx.size, np.int32)])
    w_train = np.concatenate([np.ones(pos_idx.size, np.float32), w_neg])
    pi_sample = float(pos_idx.size) / float(w_train.sum())

    clf = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.06,
        max_iter=180,
        max_leaf_nodes=35,
        min_samples_leaf=60,
        l2_regularization=2.5,
        random_state=seed,
    )
    clf.fit(X_train, y_train, sample_weight=w_train)

    del X_train, y_train, w_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.zeros(n_fp, dtype=np.float32)
    chunk = 400_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        idx = np.arange(s, e)
        Xc = _assemble_rows(blocks, idx)
        p_raw = clf.predict_proba(Xc)[:, 1]
        pred_fp[s:e] = p_raw.astype(np.float32)
        del Xc, p_raw

    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = pred_fp

    meta = {
        "n_pos_train": int(pos_all.size),
        "n_neg_train": int(neg_all.size),
        "pi_true": pi_true,
        "pi_sample": pi_sample,
    }
    return out, meta


def corroboration_gate(
    prob: np.ndarray,
    crest_families: list[np.ndarray],
    footprint: np.ndarray,
    min_families_agree: int = 2,
    percentile_thresh: float = 75.0,
) -> np.ndarray:
    """Precision-gating: pixel must exceed threshold in >= min_families independent crest fields."""
    masks = []
    for f in crest_families:
        vals = f[footprint]
        t = np.percentile(vals[vals > 0], percentile_thresh) if (vals > 0).any() else 0.0
        masks.append((f >= t) & footprint)
    agreed = np.sum(masks, axis=0) >= min_families_agree
    gated = prob.copy()
    gated[~agreed] *= 0.25
    return gated
