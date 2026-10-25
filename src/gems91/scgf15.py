"""S15-SCGF: Structural-Complexity Junctions, Multi-Wavelength Salem Attenuation,
Aquifer-Baffle Hydrothermal Physics & Dual-Specialist Auto-Context Discovery.

100% licence-clean (official 19-band GeoDAWN feature cube + public-domain DOE GDR-1391
well/spring compilation; `dist_known_fault_px` strictly untouched). Reuses shared
evaluator (`scripts/evaluate_holdout.py`), Dinkelbach submodular emitter (`gems91.ptha`),
and validated GeoTIFF/ZIP writer (`scripts/submission_writer.py`).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from gems91 import dd_vtc_pu as DD
from gems91 import ptha as PTHA
from gems91 import spac_coda as SC

FeatureBlock = tuple[np.ndarray, Sequence[int]]

H15_1_SCIF_NAMES: list[str] = [
    "s15_sub_forstner_junction",
    "s15_grav_mag_strike_cross",
    "s15_drape_rad_strike_cross",
    "s15_sub_ridge_tip_grad",
    "s15_strikeslip_lat_juxtapose",
    "s15_enechelon_strand_1p2km",
]

H15_2_STDA_NAMES: list[str] = [
    "s15_salem_tilt_crest_400m",
    "s15_salem_vs_b15_shallowing",
    "s15_rtp_worm_persist_150_900m",
    "s15_grav_worm_persist_200_1km",
    "s15_worm_dip_migration_vec",
    "s15_deep_basement_pinchout",
]

H15_3_HFPA_NAMES: list[str] = [
    "s15_cond_b15_deconf_resid",
    "s15_aquifer_baffle_step",
    "s15_alteration_triplet_sub",
    "s15_gdr_strike_plume_sub",
    "s15_cond_playa_elev_resid",
    "s15_gdr_upgradient_conduit",
]

S15_SCGF_FEATURE_NAMES: list[str] = H15_1_SCIF_NAMES + H15_2_STDA_NAMES + H15_3_HFPA_NAMES

S15_SUB_AUTOCONTEXT_NAMES: list[str] = [
    "ac_sub_raw",
    "ac_sub_ray1p5km_max",
    "ac_sub_wash_bridge_1p6km",
    "ac_sub_corridor_2km",
]

S15_DUAL_AUTOCONTEXT_NAMES: list[str] = (
    list(SC.S12_AUTOCONTEXT_FEATURE_NAMES) + S15_SUB_AUTOCONTEXT_NAMES
)

# Exhaustive audit of EVERY column across Static(49) + S11(16) + S12(20) + PTHA(20)
# + S15(18) + DualAC(14) that touches Band 12 (`det_elev`) or Band 19 (`det_elev_slope`)
# directly or indirectly (remediating IR-91-S15-05).
STRICT_TOPO_FEATURE_NAMES: frozenset[str] = frozenset(
    {
        # Static (13 of 49)
        "b12_det_elev",
        "b19_det_elev_slope",
        "e1_lrm_300m",
        "e1_lrm_1km",
        "e1_topo_openness_lap",
        "e1_slope_hp_600m",
        "e1_topo_coherence",
        "e2_axial_ridge_max",
        "e2_axial_ridge_anisotropy",
        "e2_anderson_slip_dilation",
        "e2_multiphysics_coincidence",
        "e2_gdr_upslope_conduit_align",
        "e2_piedmont_concealment_idx",
        # S11 (3 of 16)
        "s11_topo_grav_cos_align",
        "s11_topo_profile_curv",
        "s11_ctx1km_topo_slope",
        # S12 (3 of 20)
        "s12_frangi_topo_s1p5",
        "s12_frangi_topo_s4p0",
        "s12_crossfault_dipole_600m",
        # PTHA (7 of 20 — cross-strike steps in ptha.py orient along the combined B12+B13+B02 tensor)
        "ptha_multiphys_strike_coh",
        "ptha_step_elev_abs",
        "ptha_step_grav_abs",
        "ptha_step_rtp_abs",
        "ptha_step_depth_abs",
        "ptha_step_rad_tc_abs",
        "ptha_step_normal_concordance",
        # S15 (2 of 18)
        "s15_cond_playa_elev_resid",
        "s15_gdr_upgradient_conduit",
        # Stage-1 Full Auto-Context (10 of 14)
        *SC.S12_AUTOCONTEXT_FEATURE_NAMES,
    }
)


def _robust_z_2d(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = arr[footprint]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826 + 1e-5
    out = np.zeros(arr.shape, dtype=np.float32)
    out[footprint] = np.clip((vals - med) / mad, -8.0, 8.0).astype(np.float32)
    return out


def _robust_z_fp(vals_fp: np.ndarray) -> np.ndarray:
    med = float(np.median(vals_fp))
    mad = float(np.median(np.abs(vals_fp - med))) * 1.4826 + 1e-5
    return np.clip((vals_fp - med) / mad, -8.0, 8.0).astype(np.float32)


def _structure_tensor_2d(
    field: np.ndarray,
    footprint: np.ndarray,
    *,
    grad_sigma: float = 1.5,
    tensor_sigma: float = 3.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return `(jxx, jyy, jxy, coherence, strike_theta)` for a scalar 2-D field."""
    sm = ndi.gaussian_filter(field.astype(np.float32), sigma=grad_sigma)
    gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
    gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
    del sm

    gmag_fp = np.hypot(gy[footprint], gx[footprint])
    scale = float(np.percentile(gmag_fp, 90.0)) + 1e-5
    gy /= scale
    gx /= scale

    jxx = ndi.gaussian_filter(gx * gx, sigma=tensor_sigma).astype(np.float32)
    jyy = ndi.gaussian_filter(gy * gy, sigma=tensor_sigma).astype(np.float32)
    jxy = ndi.gaussian_filter(gx * gy, sigma=tensor_sigma).astype(np.float32)
    del gx, gy

    tr = jxx + jyy
    disc = np.hypot(jxx - jyy, 2.0 * jxy).astype(np.float32)
    coh = (disc / (tr + np.float32(1e-4))).astype(np.float32)
    grad_theta = (0.5 * np.arctan2(2.0 * jxy, jxx - jyy)).astype(np.float32)
    strike_theta = (grad_theta + np.float32(0.5 * np.pi)).astype(np.float32)
    return jxx, jyy, jxy, coh, strike_theta


def _deconfound_2d_quantile(
    target: np.ndarray,
    cov_a: np.ndarray,
    cov_b: np.ndarray,
    footprint: np.ndarray,
    *,
    n_bins: int = 8,
) -> np.ndarray:
    """Label-free 2-D quantile-binned smoothed median background residual on `footprint`."""
    t_fp = target[footprint].astype(np.float32)
    a_fp = cov_a[footprint].astype(np.float32)
    b_fp = cov_b[footprint].astype(np.float32)

    qs = np.linspace(0.0, 100.0, n_bins + 1)[1:-1]
    edges_a = np.percentile(a_fp, qs)
    edges_b = np.percentile(b_fp, qs)
    ia = np.digitize(a_fp, edges_a)
    ib = np.digitize(b_fp, edges_b)

    global_med = float(np.median(t_fp))
    grid = np.full((n_bins, n_bins), global_med, dtype=np.float32)
    for r in range(n_bins):
        mr = ia == r
        if not np.any(mr):
            continue
        for c in range(n_bins):
            m = mr & (ib == c)
            if int(m.sum()) >= 32:
                grid[r, c] = float(np.median(t_fp[m]))
    grid_sm = ndi.gaussian_filter(grid, sigma=0.85, mode="nearest").astype(np.float32)

    out = np.zeros(target.shape, dtype=np.float32)
    out[footprint] = (t_fp - grid_sm[ia, ib]).astype(np.float32)
    return out


def build_or_load_s15_feature_memmap(
    *,
    features_tif: str | Path,
    gdr_csv: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed float32 S15-SCGF feature matrix `(N_fp, 18)`.

    Strictly label-free and 100% licence-clean. Columns `0..15` have zero mathematical
    dependence on `Band 12` (`det_elev`) or `Band 19` (`det_elev_slope`); columns
    `16..17` explicitly incorporate `Band 12` and are registered in `STRICT_TOPO_FEATURE_NAMES`.
    """
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s15_scgf_features_v1.dat"
    meta_path = cache_p / "s15_scgf_features_v1.json"

    h, w = footprint.shape
    n_fp = int(footprint.sum())
    n_cols = len(S15_SCGF_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == S15_SCGF_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S15_SCGF_FEATURE_NAMES), meta

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    # --- Block 1: H15-1 Pure-Subsurface Junctions, Strike Crossing & Lateral Step (cols 0..5)
    with rasterio.open(features_tif) as src:
        b01_mag = DD._clean_band_edt(src.read(1), footprint)
        b02_rtp = DD._clean_band_edt(src.read(2), footprint)
        b06_tc = DD._clean_band_edt(src.read(6), footprint)
        b13_grav = DD._clean_band_edt(src.read(13), footprint)
        b14_tmi = DD._clean_band_edt(src.read(14), footprint)
        b15_depth = np.maximum(DD._clean_band_edt(src.read(15), footprint), 0.0)

    drape_res = (b01_mag - b14_tmi).astype(np.float32)
    del b01_mag, b14_tmi

    jg_xx, jg_yy, jg_xy, coh_g, th_g = _structure_tensor_2d(b13_grav, footprint)
    jm_xx, jm_yy, jm_xy, coh_m, th_m = _structure_tensor_2d(b02_rtp, footprint)
    js_xx = (0.5 * (jg_xx + jm_xx)).astype(np.float32)
    js_yy = (0.5 * (jg_yy + jm_yy)).astype(np.float32)
    js_xy = (0.5 * (jg_xy + jm_xy)).astype(np.float32)
    del jg_xx, jg_yy, jg_xy, jm_xx, jm_yy, jm_xy

    tr_sub = (js_xx + js_yy).astype(np.float32)
    disc_sub = np.hypot(js_xx - js_yy, 2.0 * js_xy).astype(np.float32)
    lam2_sub = np.maximum(0.5 * (tr_sub - disc_sub), 0.0).astype(np.float32)
    forstner_junc = np.log1p(12.0 * lam2_sub).astype(np.float32)

    grad_th_sub = (0.5 * np.arctan2(2.0 * js_xy, js_xx - js_yy)).astype(np.float32)
    ny = np.sin(grad_th_sub).astype(np.float32)
    nx = np.cos(grad_th_sub).astype(np.float32)
    sy = (-nx).astype(np.float32)
    sx = ny.astype(np.float32)
    del js_xx, js_yy, js_xy, disc_sub, lam2_sub, grad_th_sub

    grav_mag_cross = (coh_g * coh_m * (np.sin(th_g - th_m) ** 2)).astype(np.float32)
    del coh_g, coh_m, th_g, th_m

    _, _, _, coh_d, th_d = _structure_tensor_2d(drape_res, footprint, grad_sigma=1.3, tensor_sigma=3.0)
    _, _, _, coh_r, th_r = _structure_tensor_2d(b06_tc, footprint, grad_sigma=1.3, tensor_sigma=3.0)
    drape_rad_cross = (coh_d * coh_r * (np.sin(th_d - th_r) ** 2)).astype(np.float32)
    del coh_d, coh_r, th_d, th_r

    e_sub = np.sqrt(np.maximum(tr_sub, 0.0)).astype(np.float32)
    ey = (ndi.sobel(ndi.gaussian_filter(e_sub, sigma=1.5), axis=0) / 8.0).astype(np.float32)
    ex = (ndi.sobel(ndi.gaussian_filter(e_sub, sigma=1.5), axis=1) / 8.0).astype(np.float32)
    ridge_tip = (np.abs(ey * sy + ex * sx) * np.sqrt(e_sub + 1e-4)).astype(np.float32)
    del tr_sub, ey, ex

    yy_fp, xx_fp = np.nonzero(footprint)
    yy_f = yy_fp.astype(np.float32)
    xx_f = xx_fp.astype(np.float32)
    ny_fp = ny[footprint]
    nx_fp = nx[footprint]

    def _cross_step_fp(arr2d: np.ndarray, dist_px: float = 3.0) -> np.ndarray:
        sm = ndi.gaussian_filter(arr2d, sigma=1.2).astype(np.float32)
        cp = np.vstack([
            np.clip(yy_f + dist_px * ny_fp, 0.0, h - 1.0),
            np.clip(xx_f + dist_px * nx_fp, 0.0, w - 1.0),
        ])
        cm = np.vstack([
            np.clip(yy_f - dist_px * ny_fp, 0.0, h - 1.0),
            np.clip(xx_f - dist_px * nx_fp, 0.0, w - 1.0),
        ])
        vp = ndi.map_coordinates(sm, cp, order=1, mode="nearest")
        vm = ndi.map_coordinates(sm, cm, order=1, mode="nearest")
        return (vp - vm).astype(np.float32)

    step_rtp = np.abs(_cross_step_fp(b02_rtp, 3.0))
    step_drape = np.abs(_cross_step_fp(drape_res, 3.0))
    step_tc = np.abs(_cross_step_fp(b06_tc, 3.0))
    step_b15 = np.abs(_cross_step_fp(b15_depth, 3.0))
    lat_step_z = (
        0.42 * np.maximum(_robust_z_fp(step_rtp), 0.0)
        + 0.33 * np.maximum(_robust_z_fp(step_drape), 0.0)
        + 0.25 * np.maximum(_robust_z_fp(step_tc), 0.0)
    )
    strikeslip_fp = (lat_step_z * np.exp(-step_b15 / np.float32(260.0))).astype(np.float32)
    del step_rtp, step_drape, step_tc, step_b15, lat_step_z, drape_res

    cp12 = np.vstack([
        np.clip(yy_f + 12.0 * ny_fp, 0.0, h - 1.0),
        np.clip(xx_f + 12.0 * nx_fp, 0.0, w - 1.0),
    ])
    cm12 = np.vstack([
        np.clip(yy_f - 12.0 * ny_fp, 0.0, h - 1.0),
        np.clip(xx_f - 12.0 * nx_fp, 0.0, w - 1.0),
    ])
    ep12 = ndi.map_coordinates(e_sub, cp12, order=1, mode="nearest")
    em12 = ndi.map_coordinates(e_sub, cm12, order=1, mode="nearest")
    enechelon_fp = np.sqrt(np.maximum(ep12, 0.0) * np.maximum(em12, 0.0)).astype(np.float32)
    del cp12, cm12, ep12, em12, e_sub

    mm[:, 0] = forstner_junc[footprint]
    mm[:, 1] = grav_mag_cross[footprint]
    mm[:, 2] = drape_rad_cross[footprint]
    mm[:, 3] = ridge_tip[footprint]
    mm[:, 4] = strikeslip_fp
    mm[:, 5] = enechelon_fp
    del forstner_junc, grav_mag_cross, drape_rad_cross, ridge_tip, strikeslip_fp, enechelon_fp
    gc.collect()

    # --- Block 2: H15-2 Multi-Wavelength Salem Tilt-Depth & Worm Persistence (cols 6..11)
    with rasterio.open(features_tif) as src:
        b18_ghg = np.abs(DD._clean_band_edt(src.read(18), footprint)).astype(np.float32)

    def _rtp_tilt_at_sigma(rtp: np.ndarray, sig: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        sm = ndi.gaussian_filter(rtp, sigma=sig).astype(np.float32)
        gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
        gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
        hg = np.hypot(gy, gx).astype(np.float32)
        vg = (-float(sig) * ndi.laplace(sm)).astype(np.float32)
        tilt = np.arctan2(vg, hg + np.float32(1e-3)).astype(np.float32)
        crest = np.exp(-np.abs(tilt) / np.float32(0.32)).astype(np.float32)
        return tilt, crest, hg

    t15, c15, _ = _rtp_tilt_at_sigma(b02_rtp, 1.5)
    t40, c40, _ = _rtp_tilt_at_sigma(b02_rtp, 4.0)
    _, c45, h45 = _rtp_tilt_at_sigma(b02_rtp, 4.5)
    t90, c90, _ = _rtp_tilt_at_sigma(b02_rtp, 9.0)

    t40_gy = (ndi.sobel(t40, axis=0) / 8.0).astype(np.float32)
    t40_gx = (ndi.sobel(t40, axis=1) / 8.0).astype(np.float32)
    grad_t40_px = np.hypot(t40_gy, t40_gx).astype(np.float32)  # radians per 100m pixel
    del t40, t40_gy, t40_gx

    salem_crest_400m = (c40 * np.log1p(6.0 * grad_t40_px)).astype(np.float32)
    z_salem_m = (np.float32(100.0) / (grad_t40_px + np.float32(0.05))).astype(np.float32)
    salem_shallowing = np.log((b15_depth + np.float32(100.0)) / (z_salem_m + np.float32(100.0))).astype(np.float32)
    del c40, grad_t40_px, z_salem_m

    rtp_worm_persist = (
        np.cbrt(np.maximum(c15 * c45 * c90, 0.0)) * np.log1p(h45)
    ).astype(np.float32)
    worm_dip_mig = (np.abs(t90 - t15) * c45).astype(np.float32)
    del t15, c15, c45, h45, t90, c90

    def _grav_hg_norm(grav: np.ndarray, sig: float) -> np.ndarray:
        sm = ndi.gaussian_filter(grav, sigma=sig).astype(np.float32)
        gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
        gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
        hg = np.hypot(gy, gx).astype(np.float32)
        p95 = float(np.percentile(hg[footprint], 95.0)) + 1e-5
        return np.clip(hg / p95, 0.0, 2.5).astype(np.float32)

    g20 = _grav_hg_norm(b13_grav, 2.0)
    g50 = _grav_hg_norm(b13_grav, 5.0)
    g100 = _grav_hg_norm(b13_grav, 10.0)
    grav_worm_persist = np.cbrt(np.maximum(g20 * g50 * g100, 0.0)).astype(np.float32)
    del g20, g50, g100

    b15_sm2 = ndi.gaussian_filter(b15_depth, sigma=2.0).astype(np.float32)
    b15_grad = np.hypot(
        ndi.sobel(b15_sm2, axis=0) / 8.0,
        ndi.sobel(b15_sm2, axis=1) / 8.0,
    ).astype(np.float32)
    deep_pinchout = (
        (b15_grad / (b15_depth + np.float32(150.0))) * np.log1p(b18_ghg)
    ).astype(np.float32)
    del b15_sm2, b15_grad, b18_ghg

    mm[:, 6] = salem_crest_400m[footprint]
    mm[:, 7] = salem_shallowing[footprint]
    mm[:, 8] = rtp_worm_persist[footprint]
    mm[:, 9] = grav_worm_persist[footprint]
    mm[:, 10] = worm_dip_mig[footprint]
    mm[:, 11] = deep_pinchout[footprint]
    del salem_crest_400m, salem_shallowing, rtp_worm_persist
    del grav_worm_persist, worm_dip_mig, deep_pinchout
    gc.collect()

    # --- Block 3: H15-3 Deconfounded Aquifer-Baffle, Alteration Triplet & GDR Conduit (cols 12..17)
    with rasterio.open(features_tif) as src:
        b07_shr = np.maximum(DD._clean_band_edt(src.read(7), footprint), 0.0)
        b08_dil = DD._clean_band_edt(src.read(8), footprint)
        b12_elev = DD._clean_band_edt(src.read(12), footprint)
        b17_cond = np.maximum(DD._clean_band_edt(src.read(17), footprint), 0.0)

    log_cond = np.log1p(b17_cond).astype(np.float32)
    del b17_cond

    # Purely subsurface 2-D deconfounding `(B15 depth_to_base, B13 iso_grav_anom)`
    cond_b15_resid = _deconfound_2d_quantile(log_cond, b15_depth, b13_grav, footprint, n_bins=8)
    baffle_step_fp = np.abs(_cross_step_fp(cond_b15_resid, 3.0))

    rtp_trough = (
        ndi.gaussian_filter(b02_rtp, sigma=8.0) - ndi.gaussian_filter(b02_rtp, sigma=1.5)
    ).astype(np.float32)
    tc_hp = (
        ndi.gaussian_filter(b06_tc, sigma=1.2) - ndi.gaussian_filter(b06_tc, sigma=8.0)
    ).astype(np.float32)
    del b02_rtp, b06_tc, b13_grav

    z_trough = np.maximum(_robust_z_fp(rtp_trough[footprint]), 0.0)
    z_cond_res = np.maximum(_robust_z_fp(cond_b15_resid[footprint]), 0.0)
    z_tc_hp = np.maximum(_robust_z_fp(tc_hp[footprint]), 0.0)
    alteration_triplet_fp = np.cbrt(z_trough * z_cond_res * z_tc_hp).astype(np.float32)
    del rtp_trough, tc_hp, z_trough, z_cond_res, z_tc_hp

    gdr_masks = DD.extract_gdr_blind_and_thermal_cells(gdr_csv, (h, w))
    thermal_src = (
        gdr_masks["hot_warm"].astype(np.float32)
        + np.float32(0.85) * gdr_masks["blind_geotherm90"].astype(np.float32)
    )
    plume_iso = ndi.gaussian_filter(thermal_src, sigma=14.0).astype(np.float32)
    sy_fp = sy[footprint]
    sx_fp = sx[footprint]
    cp_s10 = np.vstack([
        np.clip(yy_f + 10.0 * sy_fp, 0.0, h - 1.0),
        np.clip(xx_f + 10.0 * sx_fp, 0.0, w - 1.0),
    ])
    cm_s10 = np.vstack([
        np.clip(yy_f - 10.0 * sy_fp, 0.0, h - 1.0),
        np.clip(xx_f - 10.0 * sx_fp, 0.0, w - 1.0),
    ])
    plume_along = (
        0.5 * ndi.map_coordinates(plume_iso, cp_s10, order=1, mode="nearest")
        + 0.5 * ndi.map_coordinates(plume_iso, cm_s10, order=1, mode="nearest")
    ).astype(np.float32)
    strain_drive = (
        1.0
        + 0.35 * np.maximum(_robust_z_fp(b07_shr[footprint]), 0.0)
        + 0.35 * np.maximum(_robust_z_fp(b08_dil[footprint]), 0.0)
    ).astype(np.float32)
    gdr_strike_plume_fp = (np.log1p(40.0 * (0.5 * plume_iso[footprint] + 0.5 * plume_along)) * strain_drive).astype(np.float32)
    del cp_s10, cm_s10, plume_along, strain_drive, b07_shr, b08_dil, ny, nx, sy, sx, ny_fp, nx_fp, sy_fp, sx_fp

    # Hydro-topographic features (cols 16..17, registered in STRICT_TOPO_FEATURE_NAMES)
    cond_playa_resid = _deconfound_2d_quantile(log_cond, b15_depth, b12_elev, footprint, n_bins=8)
    del log_cond, b15_depth

    elev_sm5 = ndi.gaussian_filter(b12_elev, sigma=5.0).astype(np.float32)
    egy = (ndi.sobel(elev_sm5, axis=0) / 8.0).astype(np.float32)
    egx = (ndi.sobel(elev_sm5, axis=1) / 8.0).astype(np.float32)
    enorm = np.hypot(egy, egx) + np.float32(1e-4)
    # To credit UP-GRADIENT feeder faults (`+grad elev`) of down-slope thermal wells,
    # each candidate fault pixel looks DOWN-SLOPE (`-grad elev`) for outflow thermal anomalies!
    uy_fp = (-egy / enorm)[footprint]
    ux_fp = (-egx / enorm)[footprint]
    del b12_elev, elev_sm5, egy, egx, enorm

    cp_d10 = np.vstack([
        np.clip(yy_f + 10.0 * uy_fp, 0.0, h - 1.0),
        np.clip(xx_f + 10.0 * ux_fp, 0.0, w - 1.0),
    ])
    cp_d18 = np.vstack([
        np.clip(yy_f + 18.0 * uy_fp, 0.0, h - 1.0),
        np.clip(xx_f + 18.0 * ux_fp, 0.0, w - 1.0),
    ])
    outflow_10 = ndi.map_coordinates(plume_iso, cp_d10, order=1, mode="nearest")
    outflow_18 = ndi.map_coordinates(plume_iso, cp_d18, order=1, mode="nearest")
    upgrad_conduit_fp = np.log1p(
        45.0 * (0.55 * outflow_10 + 0.45 * outflow_18)
    ).astype(np.float32)
    del plume_iso, thermal_src, cp_d10, cp_d18, outflow_10, outflow_18, uy_fp, ux_fp, yy_f, xx_f

    mm[:, 12] = cond_b15_resid[footprint]
    mm[:, 13] = baffle_step_fp
    mm[:, 14] = alteration_triplet_fp
    mm[:, 15] = gdr_strike_plume_fp
    mm[:, 16] = cond_playa_resid[footprint]
    mm[:, 17] = upgrad_conduit_fp
    del cond_b15_resid, baffle_step_fp, alteration_triplet_fp
    del gdr_strike_plume_fp, cond_playa_resid, upgrad_conduit_fp
    mm.flush()
    gc.collect()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": S15_SCGF_FEATURE_NAMES,
        "pure_subsurface_cols": list(range(16)),
        "topo_dependent_cols": [16, 17],
        "licence_clean_100pct": True,
        "dtype": "float32",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S15_SCGF_FEATURE_NAMES), meta


def compute_pure_subsurface_autocontext(
    p_sub_2d: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Extract 4 strictly topography-free topology features `(N_fp, 4)` from `p_sub_2d`."""
    p = np.where(footprint, np.clip(p_sub_2d.astype(np.float32), 0.0, 1.0), 0.0)
    n_fp = int(footprint.sum())
    out = np.empty((n_fp, 4), dtype=np.float32)
    out[:, 0] = p[footprint]

    max_ray = np.zeros_like(p, dtype=np.float32)
    max_bridge = np.zeros_like(p, dtype=np.float32)
    for az_deg in (0.0, 30.0, 60.0, 90.0, 120.0, 150.0):
        k_full = DD._oriented_line_kernel(az_deg, length_px=15, sigma_perp=1.25)
        ray = ndi.convolve(p, k_full, mode="nearest")
        np.maximum(max_ray, ray, out=max_ray)

        # Two-sided wash bridge: minimum of forward and backward half-rays (`1.6 km` total span)
        rad = np.deg2rad(az_deg)
        dy = -float(np.cos(rad))
        dx = float(np.sin(rad))
        p_sm = ndi.gaussian_filter(p, sigma=1.4).astype(np.float32)
        fwd = np.zeros_like(p, dtype=np.float32)
        bwd = np.zeros_like(p, dtype=np.float32)
        for step in (4, 8, 12, 16):
            s_y = int(round(step * dy))
            s_x = int(round(step * dx))
            fwd += np.float32(0.25) * np.roll(np.roll(p_sm, -s_y, axis=0), -s_x, axis=1)
            bwd += np.float32(0.25) * np.roll(np.roll(p_sm, s_y, axis=0), s_x, axis=1)
        bridge = np.sqrt(np.maximum(fwd, 0.0) * np.maximum(bwd, 0.0)).astype(np.float32)
        np.maximum(max_bridge, bridge, out=max_bridge)
        del ray, p_sm, fwd, bwd, bridge

    corridor_2km = ndi.gaussian_filter(p, sigma=20.0).astype(np.float32)
    out[:, 1] = max_ray[footprint]
    out[:, 2] = max_bridge[footprint]
    out[:, 3] = corridor_2km[footprint]
    return out


def compute_dual_autocontext_features(
    p_full_2d: np.ndarray,
    p_sub_2d: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Build `(N_fp, 14)` cross-fitted dual-specialist topology matrix (`10` full + `4` pure-sub)."""
    ac_full = SC.compute_spac_autocontext_features(p_full_2d, footprint)
    ac_sub = compute_pure_subsurface_autocontext(p_sub_2d, footprint)
    out = np.hstack([ac_full, ac_sub]).astype(np.float32)
    del ac_full, ac_sub
    gc.collect()
    return out


def _stack_rows(blocks: Sequence[FeatureBlock], rows: np.ndarray) -> np.ndarray:
    active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    return np.hstack(
        [np.asarray(arr[rows][:, cols], dtype=np.float32) for arr, cols in active]
    )


def _stack_slice(blocks: Sequence[FeatureBlock], start: int, end: int) -> np.ndarray:
    active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    return np.hstack(
        [np.asarray(arr[start:end][:, cols], dtype=np.float32) for arr, cols in active]
    )


def fit_and_predict_s15_stage1(
    *,
    blocks: Sequence[FeatureBlock],
    feature_names: Sequence[str],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    predict_mask: np.ndarray | None = None,
    seed: int = 1500,
    max_pos: int = 62_000,
    max_neg: int = 210_000,
    chunk_size: int = 420_000,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    """Fit fold-safe Dual-Specialist Stage-1 (`p1_full_2d`, `p1_sub_2d`, `calib_meta`).

    `p1_sub_2d` is predicted strictly from columns NOT in `STRICT_TOPO_FEATURE_NAMES`
    (`0` dependence on `Band 12` or `Band 19`), guaranteeing unbiased subsurface fault
    posteriors across zero-slope playas, alluvial fans, and active washes.
    If `predict_mask` is supplied (e.g. complementary quadrants on pairwise sub-folds),
    inference runs strictly on `footprint & predict_mask` for zero wasted CPU cycles.
    """
    rng = np.random.default_rng(seed)
    sub_mask = np.array([nm not in STRICT_TOPO_FEATURE_NAMES for nm in feature_names], dtype=bool)
    if not np.any(sub_mask):
        raise ValueError("Pure-subsurface feature mask is empty")

    pos_fp = visible_faults[footprint] & (~exclude_mask[footprint])
    neg_fp = (~visible_faults[footprint]) & (~exclude_mask[footprint])
    pos_all = np.flatnonzero(pos_fp)
    neg_all = np.flatnonzero(neg_fp)
    n_pos_true = int(pos_all.size)
    n_neg_true = int(neg_all.size)
    pi_vis_train = float(n_pos_true) / float(max(n_pos_true + n_neg_true, 1))

    pos_idx = (
        np.sort(rng.choice(pos_all, size=max_pos, replace=False))
        if pos_all.size > max_pos
        else pos_all
    )

    # Importance-weighted hard-negative mining (steep non-fault slopes + strong potential-field edges)
    X_static_arr = blocks[0][0]
    slope_neg = np.asarray(X_static_arr[:, 18], dtype=np.float32)[neg_all]
    grav_neg = np.asarray(X_static_arr[:, 17], dtype=np.float32)[neg_all]
    mag_neg = np.asarray(X_static_arr[:, 2], dtype=np.float32)[neg_all]
    hard_flag = (
        (slope_neg >= float(np.percentile(slope_neg, 76.0)))
        | (np.abs(grav_neg) >= float(np.percentile(np.abs(grav_neg), 78.0)))
        | (mag_neg >= float(np.percentile(mag_neg, 80.0)))
    )
    del slope_neg, grav_neg, mag_neg

    hard_pool = neg_all[hard_flag]
    easy_pool = neg_all[~hard_flag]
    n_hard = min(max_neg // 2, hard_pool.size)
    n_easy = min(max_neg - n_hard, easy_pool.size)
    neg_hard = np.sort(rng.choice(hard_pool, size=n_hard, replace=False)) if hard_pool.size > n_hard else hard_pool
    neg_easy = np.sort(rng.choice(easy_pool, size=n_easy, replace=False)) if easy_pool.size > n_easy else easy_pool
    neg_idx = np.concatenate([neg_hard, neg_easy])
    neg_w = np.concatenate([
        np.full(neg_hard.size, 0.55, dtype=np.float32),
        np.full(neg_easy.size, 1.45, dtype=np.float32),
    ])

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])
    w_train = np.concatenate([np.ones(pos_idx.size, dtype=np.float32), neg_w])
    pi_sample_weighted = float(pos_idx.size) / float(w_train.sum())

    X_train = _stack_rows(blocks, train_idx)
    X_train_sub = X_train[:, sub_mask]

    hgb_full = HistGradientBoostingClassifier(
        learning_rate=0.060,
        max_iter=185,
        max_leaf_nodes=41,
        min_samples_leaf=85,
        l2_regularization=3.4,
        max_features=0.72,
        early_stopping=False,
        random_state=seed,
    ).fit(X_train, y_train, sample_weight=w_train)

    hgb_sub = HistGradientBoostingClassifier(
        learning_rate=0.058,
        max_iter=175,
        max_leaf_nodes=35,
        min_samples_leaf=95,
        l2_regularization=4.2,
        max_features=0.65,
        early_stopping=False,
        random_state=seed + 202,
    ).fit(X_train_sub, y_train, sample_weight=w_train)

    med = np.median(X_train, axis=0)
    scale = np.median(np.abs(X_train - med), axis=0) * 1.4826 + 1e-5
    X_lr = np.clip((X_train - med) / scale, -6.0, 6.0)
    lr = LogisticRegression(C=0.22, max_iter=500, random_state=seed + 404)
    lr.fit(X_lr, y_train, sample_weight=w_train)
    del X_train, X_train_sub, X_lr, y_train, w_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_full_fp = np.zeros(n_fp, dtype=np.float32)
    pred_sub_fp = np.zeros(n_fp, dtype=np.float32)

    if predict_mask is None:
        target_rows = np.arange(n_fp, dtype=np.int64)
    else:
        target_rows = np.flatnonzero(predict_mask[footprint])

    for s in range(0, target_rows.size, chunk_size):
        e = min(s + chunk_size, target_rows.size)
        rows = target_rows[s:e]
        Xc = (
            _stack_slice(blocks, int(rows[0]), int(rows[-1]) + 1)
            if (rows.size > 0 and int(rows[-1]) - int(rows[0]) + 1 == rows.size)
            else _stack_rows(blocks, rows)
        )
        Xc_sub = Xc[:, sub_mask]
        pf = hgb_full.predict_proba(Xc)[:, 1].astype(np.float32)
        psub = hgb_sub.predict_proba(Xc_sub)[:, 1].astype(np.float32)
        plr = lr.predict_proba(np.clip((Xc - med) / scale, -6.0, 6.0))[:, 1].astype(np.float32)

        pred_sub_fp[rows] = psub
        pred_full_fp[rows] = (0.62 * pf + 0.26 * psub + 0.12 * plr).astype(np.float32)
        del Xc, Xc_sub, pf, psub, plr

    out_full = np.zeros(footprint.shape, dtype=np.float32)
    out_sub = np.zeros(footprint.shape, dtype=np.float32)
    out_full[footprint] = pred_full_fp
    out_sub[footprint] = pred_sub_fp
    meta = {
        "pi_vis_train": round(pi_vis_train, 8),
        "pi_sample_weighted": round(pi_sample_weighted, 8),
        "n_pos_train": int(pos_idx.size),
        "n_neg_train": int(neg_idx.size),
        "n_total_features": int(len(feature_names)),
        "n_pure_subsurface_features": int(sub_mask.sum()),
    }
    return out_full, out_sub, meta


def fit_and_predict_s15_stage2(
    *,
    train_blocks: Sequence[FeatureBlock],
    infer_blocks: Sequence[FeatureBlock],
    feature_names: Sequence[str],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    predict_mask: np.ndarray | None = None,
    seed: int = 1550,
    neg_pos_ratio: float = 3.75,
    chunk_size: int = 420_000,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    """Fit Dual-Specialist Stage-2 (`p2_full_2d`, `p2_sub_2d`, `meta`) on `137` features.

    Includes a dedicated Stage-2 Pure-Subsurface Specialist trained strictly on the
    `99` non-topographic columns (`95` static + `4` `ac_sub_*`), preserving blind
    intrabasin fault sensitivity across alluvial cover while sharpening exposed traces.
    """
    sub_mask = np.array([nm not in STRICT_TOPO_FEATURE_NAMES for nm in feature_names], dtype=bool)
    rng = np.random.default_rng(seed)

    visible = np.asarray(visible_faults, dtype=bool) & footprint
    excluded = np.asarray(exclude_mask, dtype=bool) | (~footprint)
    d_vis = ndi.distance_transform_edt(~visible)

    pos_fp = visible[footprint] & (~excluded[footprint])
    neg_fp = (~visible[footprint]) & (~excluded[footprint]) & (d_vis[footprint] > 3.5)
    pos_idx = np.flatnonzero(pos_fp)
    neg_pool = np.flatnonzero(neg_fp)
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Stage-2 training requires positive and safe-negative pixels")

    target_neg = min(int(round(float(neg_pos_ratio) * pos_idx.size)), neg_pool.size)
    neg_idx = (
        np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
        if target_neg < neg_pool.size
        else neg_pool
    )
    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])

    X_train = _stack_rows(train_blocks, train_idx)
    X_train_sub = X_train[:, sub_mask]

    hgb_deep = HistGradientBoostingClassifier(
        learning_rate=0.056,
        max_iter=195,
        max_leaf_nodes=41,
        min_samples_leaf=75,
        l2_regularization=3.4,
        max_features=0.72,
        early_stopping=False,
        random_state=seed,
    ).fit(X_train, y_train)

    hgb_sub2 = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=175,
        max_leaf_nodes=33,
        min_samples_leaf=95,
        l2_regularization=4.6,
        max_features=0.65,
        early_stopping=False,
        random_state=seed + 37,
    ).fit(X_train_sub, y_train)

    scaler = StandardScaler()
    X_scaled = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=500, random_state=seed + 53)
    lr.fit(X_scaled, y_train)
    del X_train, X_train_sub, X_scaled, y_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_full_fp = np.zeros(n_fp, dtype=np.float32)
    pred_sub_fp = np.zeros(n_fp, dtype=np.float32)

    if predict_mask is None:
        target_rows = np.arange(n_fp, dtype=np.int64)
    else:
        target_rows = np.flatnonzero(predict_mask[footprint])

    for s in range(0, target_rows.size, chunk_size):
        e = min(s + chunk_size, target_rows.size)
        rows = target_rows[s:e]
        Xc = (
            _stack_slice(infer_blocks, int(rows[0]), int(rows[-1]) + 1)
            if (rows.size > 0 and int(rows[-1]) - int(rows[0]) + 1 == rows.size)
            else _stack_rows(infer_blocks, rows)
        )
        p_deep = hgb_deep.predict_proba(Xc)[:, 1].astype(np.float32)
        p_sub = hgb_sub2.predict_proba(Xc[:, sub_mask])[:, 1].astype(np.float32)
        p_lr = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1].astype(np.float32)
        pred_sub_fp[rows] = p_sub
        pred_full_fp[rows] = (
            0.60 * p_deep + 0.24 * p_sub + 0.16 * p_lr
        ).astype(np.float32)
        del Xc, p_deep, p_sub, p_lr

    out_full = np.zeros(footprint.shape, dtype=np.float32)
    out_sub = np.zeros(footprint.shape, dtype=np.float32)
    out_full[footprint] = pred_full_fp
    out_sub[footprint] = pred_sub_fp
    pi_true = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_sample = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    return out_full, out_sub, {
        "pi_vis_train": round(pi_true, 8),
        "pi_sample_weighted": round(pi_sample, 8),
        "n_pos_train": int(pos_idx.size),
        "n_safe_neg_domain": int(neg_pool.size),
        "n_neg_sample": int(neg_idx.size),
        "n_features": int(len(feature_names)),
        "n_pure_subsurface_features": int(sub_mask.sum()),
    }


def build_s15_subsurface_crest_surface(
    ptha_crest: np.ndarray,
    X_s15: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Combine `ptha_crest` with `S15` Förstner junction, strike-slip step, Salem 400m crest,
    multi-scale RTP/gravity worms, and deconfounded aquifer-baffle step (`[0, 1]`).
    """
    z_junc = np.maximum(_robust_z_fp(np.asarray(X_s15[:, 0], dtype=np.float32)), 0.0)
    z_ss = np.maximum(_robust_z_fp(np.asarray(X_s15[:, 4], dtype=np.float32)), 0.0)
    z_salem = np.maximum(_robust_z_fp(np.asarray(X_s15[:, 6], dtype=np.float32)), 0.0)
    z_mworm = np.maximum(_robust_z_fp(np.asarray(X_s15[:, 8], dtype=np.float32)), 0.0)
    z_gworm = np.maximum(_robust_z_fp(np.asarray(X_s15[:, 9], dtype=np.float32)), 0.0)
    z_baffle = np.maximum(_robust_z_fp(np.asarray(X_s15[:, 13], dtype=np.float32)), 0.0)

    raw_s15 = (
        0.18 * z_junc
        + 0.18 * z_ss
        + 0.22 * z_salem
        + 0.16 * z_mworm
        + 0.14 * z_gworm
        + 0.12 * z_baffle
    ).astype(np.float32)
    p995 = float(np.percentile(raw_s15, 99.5)) + 1e-6
    s15_norm = np.zeros(footprint.shape, dtype=np.float32)
    s15_norm[footprint] = np.clip(raw_s15 / p995, 0.0, 1.0)

    out = np.clip(0.64 * ptha_crest + 0.36 * s15_norm, 0.0, 1.0).astype(np.float32)
    out[~footprint] = 0.0
    return out


def build_dual_bridge_concordant_crest(
    base_crest: np.ndarray,
    ac_matrix_fp: np.ndarray,
    footprint: np.ndarray,
    *,
    full_bridge_weight: float = 0.42,
    sub_bridge_weight: float = 0.26,
) -> np.ndarray:
    """E2: boost physical multi-scale crest where full OR pure-subsurface wash-bridges persist."""
    base = np.clip(base_crest.astype(np.float32), 0.0, 1.0)
    b_full_fp = np.sqrt(
        np.maximum(np.asarray(ac_matrix_fp[:, 4], dtype=np.float32), 0.0)
        * np.maximum(np.asarray(ac_matrix_fp[:, 5], dtype=np.float32), 0.0)
    )
    b_sub_fp = np.sqrt(
        np.maximum(np.asarray(ac_matrix_fp[:, 11], dtype=np.float32), 0.0)
        * np.maximum(np.asarray(ac_matrix_fp[:, 12], dtype=np.float32), 0.0)
    )

    def _norm_q50_95(v: np.ndarray) -> np.ndarray:
        if v.size == 0:
            return v
        q50 = float(np.percentile(v, 50.0))
        q95 = float(np.percentile(v, 95.0))
        return np.clip((v - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    mult_fp = (
        1.0
        + float(full_bridge_weight) * _norm_q50_95(b_full_fp)
        + float(sub_bridge_weight) * _norm_q50_95(b_sub_fp)
    ).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(base[footprint] * mult_fp, 0.0, 1.0)
    return out


def apply_sar_pu_concealed_fairway_adjustment(
    p_pool_cal: np.ndarray,
    p_sub_cal: np.ndarray,
    X_static: np.ndarray,
    X_ptha: np.ndarray,
    X_s15: np.ndarray,
    footprint: np.ndarray,
    *,
    pu_gain: float = 0.28,
) -> np.ndarray:
    """E3 (`H15-4`): SAR-PU observability propensity adjustment in concealed & Walker Lane fairways.

    Where surficial slope (`B19`) is muted over finite basin cover (`B15`) OR transtensional /
    Förstner-junction kinematics peak, geological mapping observability `e(x)` drops. When the
    strictly 100%-topography-free specialist `p_sub_cal` exceeds exposed-biased `p_pool_cal`,
    up-weight along confirmed subsurface structural corridors without inventing signal in empty
    playas (`max(p_sub_cal - 0.55 * p_pool_cal, 0)` gated by `p_sub_cal`).
    """
    slope_fp = np.maximum(np.asarray(X_static[:, 18], dtype=np.float32), 0.0)
    depth_fp = np.maximum(np.asarray(X_static[:, 14], dtype=np.float32), 0.0)
    transtens_z = np.clip(_robust_z_fp(np.asarray(X_ptha[:, 12], dtype=np.float32)) / 3.0, 0.0, 1.0)
    junc_z = np.clip(_robust_z_fp(np.asarray(X_s15[:, 0], dtype=np.float32)) / 3.0, 0.0, 1.0)
    ss_z = np.clip(_robust_z_fp(np.asarray(X_s15[:, 4], dtype=np.float32)) / 3.0, 0.0, 1.0)

    cover_concealment = (
        np.exp(-slope_fp / np.float32(7.0))
        * (np.float32(1.0) - np.exp(-depth_fp / np.float32(120.0)))
    ).astype(np.float32)
    kinematic_fairway = (0.45 * transtens_z + 0.30 * junc_z + 0.25 * ss_z).astype(np.float32)
    fairway = np.clip(0.60 * cover_concealment + 0.40 * kinematic_fairway, 0.0, 1.0)

    pf = p_pool_cal[footprint].astype(np.float32)
    ps = p_sub_cal[footprint].astype(np.float32)
    sub_excess = np.maximum(ps - np.float32(0.55) * pf, 0.0)
    adj_fp = np.clip(pf + np.float32(pu_gain) * fairway * sub_excess, 0.0, 1.0)

    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = adj_fp
    return out
