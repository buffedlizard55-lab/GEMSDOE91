"""GVP91 (`arena/f9bd8a10-gemsdoe91`): 3-D Potential-Field Analytic Signal,
Salem Tilt-Depth, Poisson Magneto-Gravity Collinearity, Crustal Seismic Swarm
Excess, Hydrothermal Vent Demagnetization-Conductivity Conjunction, and
Terrain-Deconfounded Dual-View Subsurface Specialist Pipeline.

Preregistration: `docs/HYPOTHESES_GVP91.md` (frozen before any GVP91 holdout
score was computed).

Key physical & methodological advances:
  1. Exact 3-D Magnetic Analytic Signal Amplitude `hypot(B03, B09)` (Nabighian
     1972; Roest et al. 1992) & Observed-Gradient Magnetic Tilt Angle
     `arctan2(B09, B03)` (Miller & Singh 1994; Verduzco et al. 2004) built from
     the airborne horizontal (`B03`) and vertical (`B09`) magnetic gradients.
  2. Salem et al. (2007) Tilt-Depth Contact Index `||grad(theta_TMI)|| * cos(theta_TMI)`
     and Thurston & Smith (1997) Source Parameter Imaging (SPI) local wavenumber.
  3. Gallardo & Meju (2003) Poisson Magneto-Gravity Gradient Vector Collinearity
     and Structural Cross-Gradient Concordance between `(B18, B11)` and `grad(B02)`.
  4. Crustal Earthquake Swarm Excess `z(B16_ieq) - z(B10_deq)` isolating
     fluid-driven fracture swarms from declustered mainshocks.
  5. Hydrothermal Vent Demagnetization-Conductivity Conjunction, Conjugate
     Step-Intersection Complexity, and Geothermal Upflow Conduit Potential.
  6. Dual-View Terrain-Deconfounded Ensemble: fuses Full Multi-Physics HGB+LR
     (`Model A`, 91 features) with a 100% Topography-Blind Subsurface & Geothermal
     Specialist HGB+LR (`Model B`, 81 non-topographic features, excluding `B12`,
     `B19`, and all topographic derivatives).
  7. Three-Regime Submodular 300 m DTI Allocator across Primary Multi-Physics
     Core, Concealed Piedmont Step/Tilt-Depth Ridges, and Geothermal Vent /
     Seismic-Swarm / Conjugate Step-Over Corridors.
"""

from __future__ import annotations

import gc
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import asc as ASC
from . import dd_vtc_pu as DD
from . import mhtr_coda as MC

GVP91_FEATURE_NAMES = [
    "gvp_tmi_analytic_sig_3d",
    "gvp_tmi_tilt_angle",
    "gvp_salem_tilt_contact",
    "gvp_spi_local_wavenumber",
    "gvp_updip_analytic_sig",
    "gvp_poisson_mag_grav_collinear",
    "gvp_poisson_crossgrad_null",
    "gvp_seismic_swarm_excess",
    "gvp_dilatation_shear_partition",
    "gvp_vent_alteration_demag",
    "gvp_vent_structural_intersection",
    "gvp_vent_upflow_conduit",
]

# Model A (Full Multi-Physics + Step + Analytic-Signal + Geothermal view: 91 cols)
MODEL_A_STATIC_COLS = list(range(34)) + [44, 45, 46, 47, 48]  # 39 cols
MODEL_A_S11_COLS = list(range(16))                           # 16 cols
MODEL_A_FUSE_COLS = list(range(28, 52))                      # 24 cols (18 ASC + 6 DC)
MODEL_A_GVP_COLS = list(range(12))                           # 12 cols

# Model B (100% Topography-Blind Subsurface, Step, Analytic-Signal & Geothermal Specialist: 81 cols)
# Explicitly excludes B12 (col 11), B19 (col 18), e1_lrm/openness/slope/coherence (cols 19..23),
# topo-including axial ridges/upslope/piedmont/footwall (cols 34..37, 42, 43, 46),
# s11 topo_grav_cos_align/topo_profile_curv/ctx1km_topo_slope (cols 6, 7, 14),
# and ASC det_elev step cols (fuse cols 28, 33, 38).
MODEL_B_STATIC_COLS = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17,
    24, 25, 26, 27, 28, 29, 30, 31, 32, 33,
    38, 39, 40, 41, 44, 45, 47, 48,
]  # 35 cols
MODEL_B_S11_COLS = [0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 15]  # 13 cols
MODEL_B_FUSE_COLS = [
    29, 30, 31, 32,
    34, 35, 36, 37,
    39, 40, 41, 42,
    43, 44, 45,
    46, 47, 48, 49, 50, 51,
]  # 21 cols
MODEL_B_GVP_COLS = list(range(12))  # 12 cols


def compute_gvp91_features_from_grids(
    *,
    b02_rtp: np.ndarray,
    b03_tmi_hg: np.ndarray,
    b06_tc: np.ndarray,
    b07_shear: np.ndarray,
    b08_dilat: np.ndarray,
    b09_tmi_vg: np.ndarray,
    b10_deq: np.ndarray,
    b11_gvy: np.ndarray,
    b15_depth: np.ndarray,
    b16_ieq: np.ndarray,
    b18_gvx: np.ndarray,
    eotvos_fp: np.ndarray,
    gdr_hw12_fp: np.ndarray,
    gdr_bg12_fp: np.ndarray,
    asc_subsurface_aniso_fp: np.ndarray,
    asc_az_agree_fp: np.ndarray,
    dc_cond_resid_fp: np.ndarray,
    dc_cond_grad_fp: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Compute the 12 label-free GVP91 features on `footprint` (`(N_fp, 12)` float32).

    Every feature is derived strictly from physical sensor fields and public-domain
    GDR thermal records; zero fault-catalogue information is used anywhere.
    """
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    n_fp = int(fp.sum())

    b03_pos = np.maximum(b03_tmi_hg.astype(np.float32), 0.0)
    b09_f = b09_tmi_vg.astype(np.float32)

    # 1. Exact 3-D Magnetic Analytic Signal Amplitude (Nabighian 1972; Roest et al. 1992)
    asig_3d = np.hypot(b03_pos, b09_f).astype(np.float32)
    f_asig_pct = ASC.percentile_grid(asig_3d, fp)[fp]

    # 2. Exact Observed-Gradient Magnetic Tilt Angle (Miller & Singh 1994; Verduzco et al. 2004)
    theta_tmi = np.arctan2(b09_f, b03_pos + 1e-3).astype(np.float32)
    f_tilt_angle = (theta_tmi[fp] / (0.5 * math.pi)).astype(np.float32)

    # 3. Salem et al. (2007) Tilt-Depth Contact Index: ||grad_H(theta_TMI)|| * cos(theta_TMI)
    theta_sm = ndi.gaussian_filter(theta_tmi, sigma=1.2, mode="nearest")
    tgy, tgx = np.gradient(theta_sm)
    grad_theta = np.hypot(tgx, tgy).astype(np.float32)
    salem_contact = (grad_theta * np.maximum(np.cos(theta_tmi), 0.0)).astype(np.float32)
    f_salem_pct = ASC.percentile_grid(salem_contact, fp)[fp]

    # 4. Thurston & Smith (1997) Source Parameter Imaging (SPI) local wavenumber
    spi_wn = np.log1p(grad_theta / (ndi.gaussian_filter(asig_3d, sigma=1.2, mode="nearest") + 1e-3)).astype(np.float32)
    f_spi_pct = ASC.percentile_grid(spi_wn, fp)[fp]
    del theta_sm, tgy, tgx, grad_theta, spi_wn

    # 5. Vector-normal updip-deprojected 3-D Magnetic Analytic Signal along -g_H / ||g_H||
    gvy_s = ndi.gaussian_filter(b11_gvy.astype(np.float32), sigma=1.2, mode="nearest")
    gvx_s = ndi.gaussian_filter(b18_gvx.astype(np.float32), sigma=1.2, mode="nearest")
    g_mag = np.hypot(gvx_s, gvy_s).astype(np.float32)
    gnorm = g_mag + 1e-4
    dy_up = (-gvy_s / gnorm).astype(np.float32)
    dx_up = (-gvx_s / gnorm).astype(np.float32)
    offset_px = np.clip((np.maximum(b15_depth.astype(np.float32), 0.0) * 0.7002075) / 100.0, 0.0, 10.0).astype(np.float32)
    yy_base, xx_base = np.indices((h, w), dtype=np.float32)
    coords_up = np.array([
        np.clip(yy_base + offset_px * dy_up, 0.0, h - 1.0),
        np.clip(xx_base + offset_px * dx_up, 0.0, w - 1.0),
    ])
    updip_asig = ndi.map_coordinates(asig_3d, coords_up, order=1, mode="nearest").astype(np.float32)
    f_updip_asig_pct = ASC.percentile_grid(updip_asig, fp)[fp]
    del yy_base, xx_base, dy_up, dx_up, offset_px, coords_up, updip_asig

    # 6 & 7. Gallardo & Meju (2003) Poisson Magneto-Gravity Vector Collinearity & Cross-Gradient Concordance
    rtp_sm = ndi.gaussian_filter(b02_rtp.astype(np.float32), sigma=1.5, mode="nearest")
    mgy, mgx = np.gradient(rtp_sm)
    m_mag = np.hypot(mgx, mgy).astype(np.float32)
    denom_mg = gnorm * (m_mag + 1e-4)
    cos_mg = (np.abs(gvx_s * mgx + gvy_s * mgy) / denom_mg).astype(np.float32)
    sin_mg = (np.abs(gvx_s * mgy - gvy_s * mgx) / denom_mg).astype(np.float32)
    p_gmag = ASC.percentile_grid(g_mag, fp)
    p_mmag = ASC.percentile_grid(m_mag, fp)
    joint_amp = np.sqrt(p_gmag * p_mmag).astype(np.float32)
    f_poisson_collinear = ASC.percentile_grid(joint_amp * np.clip(cos_mg, 0.0, 1.0), fp)[fp]
    f_poisson_crossnull = ASC.percentile_grid(joint_amp * np.clip(1.0 - sin_mg, 0.0, 1.0), fp)[fp]
    del rtp_sm, mgy, mgx, m_mag, denom_mg, cos_mg, sin_mg, p_mmag, joint_amp

    # 8. Crustal Earthquake Swarm Excess: z(B16_ieq) - z(B10_deq)
    z_ieq = DD._robust_z(np.maximum(b16_ieq.astype(np.float32), 0.0), fp)
    z_deq = DD._robust_z(np.maximum(b10_deq.astype(np.float32), 0.0), fp)
    swarm_grid = np.clip(z_ieq - z_deq, -5.0, 6.0).astype(np.float32)
    f_swarm_excess = swarm_grid[fp]
    del z_ieq, z_deq, swarm_grid

    # 9. Geodetic Transtensional Shear-Dilatation Partitioning
    p_shear = ASC.percentile_grid(b07_shear.astype(np.float32), fp)
    p_dilat = ASC.percentile_grid(np.abs(b08_dilat.astype(np.float32)), fp)
    f_strain_part = ASC.percentile_grid(p_shear * p_dilat * (0.35 + 0.65 * p_gmag), fp)[fp]
    del p_shear, p_dilat

    # 10. Hydrothermal Vent Demagnetization-Conductivity Conjunction
    asig_trough = (
        ndi.gaussian_filter(asig_3d, sigma=8.0, mode="nearest")
        - ndi.gaussian_filter(asig_3d, sigma=1.5, mode="nearest")
    ).astype(np.float32)
    p_asig_trough = ASC.percentile_grid(asig_trough, fp)[fp]
    p_tc = ASC.percentile_grid(b06_tc.astype(np.float32), fp)[fp]
    p_gmag_fp = p_gmag[fp]
    del asig_3d, asig_trough, p_gmag

    cond_pos = np.clip((dc_cond_resid_fp - 0.40) / 0.60, 0.0, 1.0).astype(np.float32)
    demag_raw = (
        cond_pos
        * (0.40 + 0.60 * p_tc)
        * np.clip((p_asig_trough - 0.35) / 0.65, 0.0, 1.0)
        * (0.30 + 0.70 * p_gmag_fp)
    ).astype(np.float32)
    demag_grid = np.zeros((h, w), dtype=np.float32)
    demag_grid[fp] = demag_raw
    f_vent_demag = ASC.percentile_grid(demag_grid, fp)[fp]
    del demag_grid, demag_raw, cond_pos, p_asig_trough, p_tc

    # 11. Structural Complexity & Conjugate Step-Intersection Index
    eot_grid = np.zeros((h, w), dtype=np.float32)
    eot_grid[fp] = eotvos_fp
    p_eot_fp = ASC.percentile_grid(eot_grid, fp)[fp]
    del eot_grid
    intersect_raw = (
        np.sqrt(p_eot_fp * f_salem_pct)
        * np.clip(asc_subsurface_aniso_fp, 0.0, 1.0)
        * (1.0 - 0.45 * np.clip(asc_az_agree_fp, 0.0, 1.0))
    ).astype(np.float32)
    intersect_grid = np.zeros((h, w), dtype=np.float32)
    intersect_grid[fp] = intersect_raw
    f_struct_intersect = ASC.percentile_grid(intersect_grid, fp)[fp]
    del intersect_grid, intersect_raw

    # 12. Geothermal Upflow Conduit Potential
    gdr_blend = (0.55 * np.clip(gdr_bg12_fp, 0.0, 1.0) + 0.45 * np.clip(gdr_hw12_fp, 0.0, 1.0)).astype(np.float32)
    swarm_pos = np.clip(f_swarm_excess / 3.0, 0.0, 1.5).astype(np.float32)
    upflow_raw = (
        (0.15 + 0.85 * gdr_blend)
        * (1.0 + 0.45 * swarm_pos + 0.45 * np.clip(dc_cond_grad_fp, 0.0, 1.0))
        * (0.35 + 0.65 * p_gmag_fp)
    ).astype(np.float32)
    upflow_grid = np.zeros((h, w), dtype=np.float32)
    upflow_grid[fp] = upflow_raw
    f_vent_upflow = ASC.percentile_grid(upflow_grid, fp)[fp]
    del upflow_grid, upflow_raw

    out = np.column_stack([
        f_asig_pct,
        f_tilt_angle,
        f_salem_pct,
        f_spi_pct,
        f_updip_asig_pct,
        f_poisson_collinear,
        f_poisson_crossnull,
        f_swarm_excess,
        f_strain_part,
        f_vent_demag,
        f_struct_intersect,
        f_vent_upflow,
    ]).astype(np.float32)

    assert out.shape == (n_fp, len(GVP91_FEATURE_NAMES))
    assert np.isfinite(out).all(), "non-finite values in GVP91 feature matrix"
    meta = {
        "n_fp": n_fp,
        "n_cols": len(GVP91_FEATURE_NAMES),
        "feature_names": list(GVP91_FEATURE_NAMES),
        "licence_clean_100pct": True,
        "label_free_100pct": True,
    }
    return out, meta


def build_or_load_gvp91_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    X_static: np.memmap | np.ndarray,
    X_s11: np.memmap | np.ndarray,
    X_fuse: np.memmap | np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed float32 GVP91 feature matrix `(N_fp, 12)`."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "gvp91_features_v1.dat"
    meta_path = cache_p / "gvp91_features_v1.json"

    n_fp = int(footprint.sum())
    n_cols = len(GVP91_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == GVP91_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(GVP91_FEATURE_NAMES), meta

    with rasterio.open(features_tif) as fsrc:
        b02 = DD._clean_band_edt(fsrc.read(2), footprint)
        b03 = np.maximum(DD._clean_band_edt(fsrc.read(3), footprint), 0.0)
        b06 = np.maximum(DD._clean_band_edt(fsrc.read(6), footprint), 0.0)
        b07 = np.maximum(DD._clean_band_edt(fsrc.read(7), footprint), 0.0)
        b08 = DD._clean_band_edt(fsrc.read(8), footprint)
        b09 = DD._clean_band_edt(fsrc.read(9), footprint)
        b10 = np.maximum(DD._clean_band_edt(fsrc.read(10), footprint), 0.0)
        b11 = DD._clean_band_edt(fsrc.read(11), footprint)
        b15 = np.maximum(DD._clean_band_edt(fsrc.read(15), footprint), 0.0)
        b16 = np.maximum(DD._clean_band_edt(fsrc.read(16), footprint), 0.0)
        b18 = DD._clean_band_edt(fsrc.read(18), footprint)

    asc_sub_aniso = np.mean(np.asarray(X_fuse[:, [34, 35, 36, 37]], dtype=np.float32), axis=1)
    asc_az_agree = np.asarray(X_fuse[:, 43], dtype=np.float32)
    dc_cond_resid = np.asarray(X_fuse[:, 46], dtype=np.float32)
    dc_cond_grad = np.asarray(X_fuse[:, 47], dtype=np.float32)
    eotvos_fp = np.asarray(X_s11[:, 2], dtype=np.float32)
    gdr_hw12_fp = np.asarray(X_static[:, 38], dtype=np.float32)
    gdr_bg12_fp = np.asarray(X_static[:, 40], dtype=np.float32)

    arr, meta = compute_gvp91_features_from_grids(
        b02_rtp=b02,
        b03_tmi_hg=b03,
        b06_tc=b06,
        b07_shear=b07,
        b08_dilat=b08,
        b09_tmi_vg=b09,
        b10_deq=b10,
        b11_gvy=b11,
        b15_depth=b15,
        b16_ieq=b16,
        b18_gvx=b18,
        eotvos_fp=eotvos_fp,
        gdr_hw12_fp=gdr_hw12_fp,
        gdr_bg12_fp=gdr_bg12_fp,
        asc_subsurface_aniso_fp=asc_sub_aniso,
        asc_az_agree_fp=asc_az_agree,
        dc_cond_resid_fp=dc_cond_resid,
        dc_cond_grad_fp=dc_cond_grad,
        footprint=footprint,
    )
    del b02, b03, b06, b07, b08, b09, b10, b11, b15, b16, b18
    gc.collect()

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    mm[:] = arr
    mm.flush()
    del arr, mm
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(GVP91_FEATURE_NAMES), meta


def _slice_stack(
    rows_or_slice,
    X_static: np.ndarray,
    static_cols: list[int],
    X_s11: np.ndarray,
    s11_cols: list[int],
    X_fuse: np.ndarray,
    fuse_cols: list[int],
    X_gvp: np.ndarray,
    gvp_cols: list[int],
) -> np.ndarray:
    parts = []
    if static_cols:
        parts.append(np.asarray(X_static[rows_or_slice][:, static_cols], dtype=np.float32))
    if s11_cols:
        parts.append(np.asarray(X_s11[rows_or_slice][:, s11_cols], dtype=np.float32))
    if fuse_cols:
        parts.append(np.asarray(X_fuse[rows_or_slice][:, fuse_cols], dtype=np.float32))
    if gvp_cols:
        parts.append(np.asarray(X_gvp[rows_or_slice][:, gvp_cols], dtype=np.float32))
    return np.hstack(parts)


def fit_and_predict_view_oof(
    *,
    X_static: np.ndarray,
    static_cols: list[int],
    X_s11: np.ndarray,
    s11_cols: list[int],
    X_fuse: np.ndarray,
    fuse_cols: list[int],
    X_gvp: np.ndarray,
    gvp_cols: list[int],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    seed: int = 910,
    max_neg_samples: int = 165_000,
) -> np.ndarray:
    """Train regularized HGB + L2-LR ensemble on the specified column view."""
    rng = np.random.default_rng(seed)
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis_grid = ndi.distance_transform_edt(~visible_faults)
    safe_neg_fp = (~vis_fp) & (~excl_fp) & (d_vis_grid[footprint] > 3.5)

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    neg_pool = np.flatnonzero(safe_neg_fp)
    if neg_pool.size > max_neg_samples:
        neg_idx = rng.choice(neg_pool, size=max_neg_samples, replace=False)
        neg_idx.sort()
    else:
        neg_idx = neg_pool

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])

    X_tr = _slice_stack(
        train_idx,
        X_static, static_cols,
        X_s11, s11_cols,
        X_fuse, fuse_cols,
        X_gvp, gvp_cols,
    )

    hgb = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=195,
        max_leaf_nodes=35,
        min_samples_leaf=75,
        l2_regularization=3.0,
        random_state=seed,
    )
    hgb.fit(X_tr, y_train)

    scaler = StandardScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=300, random_state=seed)
    lr.fit(X_tr_sc, y_train)
    del X_tr, X_tr_sc
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 400_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = _slice_stack(
            slice(s, e),
            X_static, static_cols,
            X_s11, s11_cols,
            X_fuse, fuse_cols,
            X_gvp, gvp_cols,
        )
        p_hgb = hgb.predict_proba(Xc)[:, 1]
        p_lr = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        pred_fp[s:e] = (0.78 * p_hgb + 0.22 * p_lr).astype(np.float32)

    out_grid = np.zeros(footprint.shape, dtype=np.float32)
    out_grid[footprint] = pred_fp
    return out_grid


def blend_terrain_deconfounded_views(
    surf_full: np.ndarray,
    surf_subsurface: np.ndarray,
    X_static: np.ndarray,
    footprint: np.ndarray,
    *,
    base_sub_weight: float = 0.20,
    concealed_sub_boost: float = 0.26,
    slope_scale_deg: float = 6.0,
) -> np.ndarray:
    """Fuse Full Multi-Physics `surf_full` (`Model A`) with 100% Topography-Blind
    Subsurface & Geothermal Specialist `surf_subsurface` (`Model B`) using
    terrain-regime adaptive weighting:

        alpha_sub(x) = base_sub_weight + concealed_sub_boost * exp(-slope(x) / slope_scale_deg)
    """
    slope_fp = np.maximum(np.asarray(X_static[:, 18], dtype=np.float32), 0.0)
    alpha_fp = np.clip(
        float(base_sub_weight) + float(concealed_sub_boost) * np.exp(-slope_fp / float(slope_scale_deg)),
        0.0,
        0.65,
    ).astype(np.float32)
    p_a = surf_full[footprint]
    p_b = surf_subsurface[footprint]
    blended_fp = ((1.0 - alpha_fp) * p_a + alpha_fp * p_b).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(blended_fp, 0.0, 0.9999)
    return out


def apply_gvp_upflow_and_relay_modulation(
    surface: np.ndarray,
    X_gvp: np.ndarray,
    X_fold_cat: np.ndarray | None,
    footprint: np.ndarray,
    *,
    upflow_strength: float = 0.14,
    relay_strength: float = 0.12,
) -> np.ndarray:
    """Gentle fold-safe post-OOF modulation boosting Geothermal Upflow Conduits,
    Seismic Swarm Excess, Conjugate Step Intersections, and visible-catalogue
    fault-tip/step-over relay zones where local subsurface evidence is present.
    """
    p_fp = surface[footprint].astype(np.float32)
    swarm_pos = np.clip(np.asarray(X_gvp[:, 7], dtype=np.float32) / 3.0, 0.0, 1.0)
    demag = np.clip(np.asarray(X_gvp[:, 9], dtype=np.float32), 0.0, 1.0)
    inter = np.clip(np.asarray(X_gvp[:, 10], dtype=np.float32), 0.0, 1.0)
    upflow = np.clip(np.asarray(X_gvp[:, 11], dtype=np.float32), 0.0, 1.0)

    vent_score = (0.40 * upflow + 0.25 * inter + 0.20 * demag + 0.15 * swarm_pos).astype(np.float32)
    mult = 1.0 + float(upflow_strength) * vent_score

    if X_fold_cat is not None and relay_strength > 0.0:
        tip = np.clip(np.asarray(X_fold_cat[:, 0], dtype=np.float32), 0.0, 1.0)
        step = np.clip(np.asarray(X_fold_cat[:, 1], dtype=np.float32), 0.0, 1.0)
        cont = np.clip(np.asarray(X_fold_cat[:, 2], dtype=np.float32), 0.0, 1.0)
        relay = (0.45 * tip + 0.35 * step + 0.20 * cont).astype(np.float32)
        mult = mult * (1.0 + float(relay_strength) * relay)

    p_adj = (p_fp * mult) / (p_fp * mult + (1.0 - p_fp) + 1e-8)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(p_adj, 0.0, 0.9999)
    return out


def compute_gvp_structural_and_vent_fields(
    X_static: np.ndarray,
    X_s11: np.ndarray,
    X_fuse: np.ndarray,
    X_gvp: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute:
      1. `gvp_edge_field`: label-free structural contact & step edge field in `[0, 1]`
         combining Marussi Eotvos/SVD, Salem Tilt-Depth, Updip 3-D Analytic Signal,
         ASC Odd-Symmetric Subsurface Steps, Depth-Conditioned Conductivity Residual
         Gradient, and Band 06 Radiometric TC Contact.
      2. `gvp_vent_field`: label-free geothermal upflow, seismic-swarm, Poisson
         magneto-gravity collinearity, and conjugate step-intersection field in `[0, 1]`.
      3. `piedmont_mask`: boolean mask of concealed piedmont / basin-floor / step-over
         terrain (`slope < 6.4 deg` OR `depth_to_base > 210 m` with `slope < 10.8 deg`).
    """
    mhtr_edge, _ = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)
    e_mhtr_fp = mhtr_edge[footprint]

    salem_fp = np.clip(np.asarray(X_gvp[:, 2], dtype=np.float32), 0.0, 1.0)
    up_asig_fp = np.clip(np.asarray(X_gvp[:, 4], dtype=np.float32), 0.0, 1.0)
    collin_fp = np.clip(np.asarray(X_gvp[:, 5], dtype=np.float32), 0.0, 1.0)
    asc_step_fp = np.mean(np.asarray(X_fuse[:, [29, 30, 31, 32]], dtype=np.float32), axis=1)
    asc_aniso_fp = np.mean(np.asarray(X_fuse[:, [34, 35, 36, 37]], dtype=np.float32), axis=1)
    dc_grad_fp = np.clip(np.asarray(X_fuse[:, 47], dtype=np.float32), 0.0, 1.0)

    e_gvp_fp = np.clip(
        0.42 * e_mhtr_fp
        + 0.22 * (0.55 * salem_fp + 0.45 * up_asig_fp)
        + 0.22 * (0.60 * asc_step_fp + 0.40 * asc_aniso_fp)
        + 0.14 * (0.55 * dc_grad_fp + 0.45 * collin_fp),
        0.0,
        1.0,
    ).astype(np.float32)

    swarm_pos = np.clip(np.asarray(X_gvp[:, 7], dtype=np.float32) / 3.0, 0.0, 1.0)
    strain_fp = np.clip(np.asarray(X_gvp[:, 8], dtype=np.float32), 0.0, 1.0)
    demag_fp = np.clip(np.asarray(X_gvp[:, 9], dtype=np.float32), 0.0, 1.0)
    inter_fp = np.clip(np.asarray(X_gvp[:, 10], dtype=np.float32), 0.0, 1.0)
    upflow_fp = np.clip(np.asarray(X_gvp[:, 11], dtype=np.float32), 0.0, 1.0)

    v_gvp_fp = np.clip(
        0.30 * upflow_fp
        + 0.26 * inter_fp
        + 0.18 * demag_fp
        + 0.14 * collin_fp
        + 0.12 * (0.55 * swarm_pos + 0.45 * strain_fp),
        0.0,
        1.0,
    ).astype(np.float32)

    depth_b = np.asarray(X_static[:, 14], dtype=np.float32)
    slope_b = np.asarray(X_static[:, 18], dtype=np.float32)
    pied_fp = (slope_b < 6.4) | ((depth_b > 210.0) & (slope_b < 10.8))

    out_edge = np.zeros(footprint.shape, dtype=np.float32)
    out_edge[footprint] = e_gvp_fp
    out_vent = np.zeros(footprint.shape, dtype=np.float32)
    out_vent[footprint] = v_gvp_fp
    pied_mask = np.zeros(footprint.shape, dtype=bool)
    pied_mask[footprint] = pied_fp
    return out_edge, out_vent, pied_mask


def gvp_three_regime_submodular_emit(
    surface: np.ndarray,
    subsurface_surface: np.ndarray,
    gvp_edge_field: np.ndarray,
    gvp_vent_field: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    eligible_mask: np.ndarray,
    n_dots: int,
    gamma: float = 1.20,
    edge_weight: float = 0.48,
    piedmont_quota_frac: float = 0.29,
    vent_quota_frac: float = 0.49,
    stage1_excl_radius_px: float = 5.0,
    prior_ratio: float = 0.052,
    min_spacing_px: float = 2.55,
    pool_multiplier: int = 8,
) -> np.ndarray:
    """Three-Regime Geothermal & Subsurface Submodular 300 m DTI Allocator:
      - Stage 1 (`1 - piedmont_quota_frac - vent_quota_frac` ~ 22%): Primary
        Multi-Physics + Cross-Fault Step + Analytic-Signal Spine (`>= max(min_spacing_px, 2.65)`).
      - Stage 2 (`piedmont_quota_frac` ~ 29%): Concealed Piedmont & Subsurface-Specialist
        Step / Tilt-Depth Ridges strictly `> stage1_excl_radius_px` from Stage 1.
      - Stage 3 (`vent_quota_frac` ~ 49%): Geothermal Vent Upflow, Seismic-Swarm &
        Conjugate Step-Intersection Corridors strictly `> stage1_excl_radius_px` from
        Stage 1 and `> 3.60 px` from Stage 2.
    """
    h, w = surface.shape
    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 0.9999).astype(np.float32)
    p_sub = np.clip(np.nan_to_num(subsurface_surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 0.9999).astype(np.float32)
    e_gvp = np.clip(np.nan_to_num(gvp_edge_field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    v_gvp = np.clip(np.nan_to_num(gvp_vent_field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)

    q_base = ((prior_ratio * p) / (prior_ratio * p + (1.0 - p) + 1e-8)).astype(np.float32)
    q = (q_base * (1.0 + float(edge_weight) * e_gvp)).astype(np.float32)

    qp = np.pad(q, 2, mode="edge")
    c = qp[2 : h + 2, 2 : w + 2]
    is_q_ridge = (
        ((c >= qp[1 : h + 1, 2 : w + 2]) & (c >= qp[3 : h + 3, 2 : w + 2]) & (c >= qp[0:h, 2 : w + 2]) & (c >= qp[4 : h + 4, 2 : w + 2]))
        | ((c >= qp[2 : h + 2, 1 : w + 1]) & (c >= qp[2 : h + 2, 3 : w + 3]) & (c >= qp[2 : h + 2, 0:w]) & (c >= qp[2 : h + 2, 4 : w + 4]))
        | ((c >= qp[1 : h + 1, 1 : w + 1]) & (c >= qp[3 : h + 3, 3 : w + 3]) & (c >= qp[0:h, 0:w]) & (c >= qp[4 : h + 4, 4 : w + 4]))
        | ((c >= qp[1 : h + 1, 3 : w + 3]) & (c >= qp[3 : h + 3, 1 : w + 1]) & (c >= qp[0:h, 4 : w + 4]) & (c >= qp[4 : h + 4, 0:w]))
    )

    ep = np.pad(e_gvp, 1, mode="edge")
    ec = ep[1 : h + 1, 1 : w + 1]
    is_edge_ridge = (
        ((ec >= ep[0:h, 1 : w + 1]) & (ec >= ep[2 : h + 2, 1 : w + 1]))
        | ((ec >= ep[1 : h + 1, 0:w]) & (ec >= ep[1 : h + 1, 2 : w + 2]))
        | ((ec >= ep[0:h, 0:w]) & (ec >= ep[2 : h + 2, 2 : w + 2]))
        | ((ec >= ep[0:h, 2 : w + 2]) & (ec >= ep[2 : h + 2, 0:w]))
    )

    elig_pos_q = q[eligible_mask & (q > 0)]
    if elig_pos_q.size == 0 or n_dots <= 0:
        return np.zeros((h, w), dtype=np.float32)

    if elig_pos_q.size > n_dots * 15:
        keep_frac = min(0.36, max(float(n_dots * 23) / float(elig_pos_q.size), 0.06))
        q_floor = float(np.quantile(elig_pos_q, 1.0 - keep_frac))
    else:
        q_floor = 0.0

    q_excess = np.maximum(q - q_floor, 0.0)
    ridge_mult_1 = np.where(is_q_ridge, 1.0, 0.24).astype(np.float32)
    w_primary = np.where(
        eligible_mask,
        1000.0 * (q_excess ** float(gamma)) * ridge_mult_1,
        0.0,
    ).astype(np.float32)

    n_piedmont = int(round(n_dots * float(piedmont_quota_frac)))
    n_vent = int(round(n_dots * float(vent_quota_frac)))
    n_primary = max(0, n_dots - n_piedmont - n_vent)

    s1_spacing = max(float(min_spacing_px), 2.65)
    dots_stage1 = MC._submodular_select_on_weight(
        w_primary,
        q * np.where(is_q_ridge, 1.15, 0.85),
        eligible_mask,
        n_primary,
        min_spacing_px=s1_spacing,
        pool_multiplier=pool_multiplier,
        existing_dots=None,
    )

    r_int = int(math.ceil(float(stage1_excl_radius_px)))
    oy_r, ox_r = np.mgrid[-r_int : r_int + 1, -r_int : r_int + 1]
    disk_s1 = np.hypot(oy_r, ox_r) <= float(stage1_excl_radius_px)
    near_s1 = ndi.binary_dilation(dots_stage1 > 0, structure=disk_s1)
    sub_boost = (1.0 + 0.22 * p_sub).astype(np.float32)

    dots_curr = dots_stage1
    if n_piedmont > 0:
        pied_elig = eligible_mask & piedmont_mask & (~near_s1) & (e_gvp >= 0.20)
        ridge_mult_2 = np.where(is_edge_ridge, 1.15, np.where(is_q_ridge, 0.85, 0.22)).astype(np.float32)
        w_piedmont = np.where(
            pied_elig,
            1000.0 * (q_excess ** float(gamma * 0.85)) * sub_boost * ((0.20 + e_gvp) ** 1.10) * ridge_mult_2,
            0.0,
        ).astype(np.float32)
        dots_curr = MC._submodular_select_on_weight(
            w_piedmont,
            (q_excess ** 0.80) * sub_boost * ((0.20 + e_gvp) ** 1.10) * ridge_mult_2,
            pied_elig,
            n_piedmont,
            min_spacing_px=float(min_spacing_px),
            pool_multiplier=pool_multiplier,
            existing_dots=dots_curr,
        )

    if n_vent > 0:
        oy3, ox3 = np.mgrid[-4:5, -4:5]
        disk_3p60 = np.hypot(oy3, ox3) <= 3.60
        s2_only = (dots_curr > 0) & (~(dots_stage1 > 0))
        near_s2 = near_s1 | ndi.binary_dilation(s2_only, structure=disk_3p60)
        vent_elig = eligible_mask & (~near_s2) & (v_gvp >= 0.24) & (e_gvp >= 0.18)
        ridge_mult_3 = np.where(is_edge_ridge | is_q_ridge, 1.15, 0.25).astype(np.float32)
        w_vent = np.where(
            vent_elig,
            1000.0 * (q_excess ** float(gamma * 0.82)) * sub_boost * ((0.20 + v_gvp) ** 1.15) * ((0.20 + e_gvp) ** 0.90) * ridge_mult_3,
            0.0,
        ).astype(np.float32)
        dots_curr = MC._submodular_select_on_weight(
            w_vent,
            (q_excess ** 0.78) * sub_boost * ((0.20 + v_gvp) ** 1.15) * ridge_mult_3,
            vent_elig,
            n_vent,
            min_spacing_px=float(min_spacing_px),
            pool_multiplier=pool_multiplier,
            existing_dots=dots_curr,
        )

    return dots_curr
