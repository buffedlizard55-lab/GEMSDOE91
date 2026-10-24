"""Session 13 Method Lane (`S13-PTHA`):
Dimensional Nabighian-Verduzco-Blakely Magnetic Curvature +
Principal-Strike Multi-Field Odd-Symmetric Step +
Continuum Transtensional Strain-Seismic Partitioning +
Dinkelbach Expected-DTI Submodular Allocation.

All 20 `PTHA` static features are 100% label-free (computed strictly from the
19 official competition bands of `gems-geodawn-numerical-features.tif` and the
`sample_submission.tif` footprint mask; never touches `existing_faults.tif`,
`SGMC`, or any prior submission raster).

Dimensional unit corrections verified in `evidence/s13_band06_and_units_audit.json`:
- `Band 03 (tmi_hg)` = `2 * ||grad_px(Band 14)||` (`nT / 200 m`, r = 0.999991),
  whereas `Band 09 (tmi_vg)` is in `nT / m` (`p95 |B09| = 0.4681 nT/m` vs
  `p95 B03/200 = 0.4715 nT/m`). Dividing `B03` by `200.0` restores exact SI
  dimensional consistency (`IR-91-S13-01`).
- `Band 06 (tc)` = USGS GeoDAWN Airborne Radiometric Total Count (`r = 0.996990`
  across 5,164,300 pixels; `IR-91-S12-04`).
- `(Band 11, Band 18)` = horizontal gravity gradient vector `(dG/dy, dG/dx)`
  (`IR-91-S12-03`).
"""

from __future__ import annotations

import gc
import heapq
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from gems91 import dd_vtc_pu as DD

H13_1_FEATURE_NAMES: list[str] = [
    "ptha_mag_analytic_sig",
    "ptha_mag_verduzco_tilt",
    "ptha_mag_tilt_zero_crest",
    "ptha_rtp_blakely_crest",
    "ptha_rtp_tmi_remanence",
    "ptha_multiphys_strike_coh",
    "ptha_step_elev_abs",
    "ptha_step_grav_abs",
    "ptha_step_rtp_abs",
    "ptha_step_depth_abs",
    "ptha_step_rad_tc_abs",
    "ptha_step_normal_concordance",
]

H13_2_FEATURE_NAMES: list[str] = [
    "ptha_transtension_index",
    "ptha_kinematic_angle",
    "ptha_strain_shear_grad",
    "ptha_strain_dil_grad",
    "ptha_eq_log_prox",
    "ptha_eq_log_density_hp",
    "ptha_brittle_transtension",
    "ptha_aseismic_strain_deficit",
]

PTHA_FEATURE_NAMES: list[str] = H13_1_FEATURE_NAMES + H13_2_FEATURE_NAMES

# Topographic feature names to exclude from the Topography-Blind Subsurface Specialist
TOPO_FEATURE_NAMES: set[str] = {
    "b12_det_elev",
    "b19_det_elev_slope",
    "e1_lrm_300m",
    "e1_lrm_1km",
    "e1_topo_openness_lap",
    "e1_slope_hp_600m",
    "e1_topo_coherence",
    "s11_ piedmont_concealment",
    "s11_piedmont_concealment",
    "ptha_step_elev_abs",
}


def _robust_z_fp(vals_1d: np.ndarray) -> np.ndarray:
    med = float(np.median(vals_1d))
    mad = float(np.median(np.abs(vals_1d - med))) * 1.4826 + 1e-6
    return np.clip((vals_1d - med) / mad, -8.0, 8.0).astype(np.float32)


def _robust_z_grid(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = arr[footprint]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826 + 1e-6
    out = np.clip((arr - med) / mad, -8.0, 8.0).astype(np.float32)
    out[~footprint] = 0.0
    return out


def _strike_step_diff_fp(
    field_2d: np.ndarray,
    fp_r: np.ndarray,
    fp_c: np.ndarray,
    ny_fp: np.ndarray,
    nx_fp: np.ndarray,
    *,
    cross_offset_px: float = 3.0,
    strike_offset_px: float = 3.0,
    sigma_pre: float = 1.3,
) -> np.ndarray:
    """Compute strike-integrated odd-symmetric cross-fault step `F(+n) - F(-n)` at footprint pixels.

    Integrates over 3 stations `s in {-strike_offset_px, 0, +strike_offset_px}`
    along local principal strike `s_hat = (-nx, ny)` (`600 m` strike aperture)
    and differences `+/- cross_offset_px` (`600 m` cross-fault span) along
    basin-oriented normal `n_hat = (ny, nx)`. Peak temporary coordinate buffer
    is ~41 MB.
    """
    sm = ndi.gaussian_filter(field_2d.astype(np.float32), sigma=sigma_pre)
    h, w = sm.shape
    sy_fp = -nx_fp
    sx_fp = ny_fp

    acc = np.zeros(fp_r.shape[0], dtype=np.float32)
    weights = (0.25, 0.50, 0.25)
    offsets_s = (-strike_offset_px, 0.0, +strike_offset_px)
    coords = np.empty((2, fp_r.shape[0]), dtype=np.float32)

    for w_s, s_off in zip(weights, offsets_s):
        base_r = fp_r + s_off * sy_fp
        base_c = fp_c + s_off * sx_fp

        np.clip(base_r + cross_offset_px * ny_fp, 0.0, h - 1.0, out=coords[0])
        np.clip(base_c + cross_offset_px * nx_fp, 0.0, w - 1.0, out=coords[1])
        f_plus = ndi.map_coordinates(sm, coords, order=1, mode="nearest")

        np.clip(base_r - cross_offset_px * ny_fp, 0.0, h - 1.0, out=coords[0])
        np.clip(base_c - cross_offset_px * nx_fp, 0.0, w - 1.0, out=coords[1])
        f_minus = ndi.map_coordinates(sm, coords, order=1, mode="nearest")

        acc += np.float32(w_s) * (f_plus - f_minus).astype(np.float32)

    del sm, coords
    return acc


def build_or_load_ptha_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open disk-backed `(N_fp, 20)` float32 `S13-PTHA` feature matrix."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s13_ptha_features_v1.dat"
    meta_path = cache_p / "s13_ptha_features_v1.json"

    n_fp = int(footprint.sum())
    n_cols = len(PTHA_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == PTHA_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(PTHA_FEATURE_NAMES), meta

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    # --- Pass A: Magnetic Curvature & Dimensional Nabighian-Verduzco-Blakely (`cols 0..4`) ---
    with rasterio.open(features_tif) as src:
        b02_rtp = DD._clean_band_edt(src.read(2), footprint)
        b03_tmi_hg = DD._clean_band_edt(src.read(3), footprint)
        b09_tmi_vg = DD._clean_band_edt(src.read(9), footprint)
        b14_tmi = DD._clean_band_edt(src.read(14), footprint)

    # Convert B03 from nT/(200 m) to nT/m so B03/200 and B09 share identical SI units (`IR-91-S13-01`)
    h_tmi_si = np.maximum(b03_tmi_hg, 0.0) / np.float32(200.0)
    asig_si = np.hypot(h_tmi_si, b09_tmi_vg)
    mm[:, 0] = np.log1p(10.0 * asig_si[footprint]).astype(np.float32)

    theta_mag = np.arctan2(b09_tmi_vg, h_tmi_si + np.float32(1e-4)).astype(np.float32)
    mm[:, 1] = theta_mag[footprint]

    theta_sm = ndi.gaussian_filter(theta_mag, sigma=1.2)
    t_gy = ndi.sobel(theta_sm, axis=0) / np.float32(8.0)
    t_gx = ndi.sobel(theta_sm, axis=1) / np.float32(8.0)
    k_mag = np.hypot(t_gy, t_gx)
    tilt_zero_crest = (k_mag * np.exp(-np.abs(theta_mag) / np.float32(0.35))).astype(np.float32)
    mm[:, 2] = tilt_zero_crest[footprint]
    del b03_tmi_hg, b09_tmi_vg, h_tmi_si, asig_si, theta_mag, theta_sm, t_gy, t_gx, k_mag, tilt_zero_crest
    gc.collect()

    # Phillips (2007) / Blakely-Simpson (1986) Horizontal-Gradient Hessian Crest on RTP (`B02`)
    rtp_sm = ndi.gaussian_filter(b02_rtp, sigma=1.5)
    r_gy = ndi.sobel(rtp_sm, axis=0) / np.float32(8.0)
    r_gx = ndi.sobel(rtp_sm, axis=1) / np.float32(8.0)
    g_rtp = np.log1p(np.hypot(r_gy, r_gx) / np.float32(5.0)).astype(np.float32)
    g_rtp_sm = ndi.gaussian_filter(g_rtp, sigma=1.5)
    hyy = ndi.gaussian_filter(g_rtp_sm, sigma=1.0, order=(2, 0))
    hxx = ndi.gaussian_filter(g_rtp_sm, sigma=1.0, order=(0, 2))
    hxy = ndi.gaussian_filter(g_rtp_sm, sigma=1.0, order=(1, 1))
    tr_h = hxx + hyy
    disc_h = np.hypot(hxx - hyy, 2.0 * hxy)
    lam_min = 0.5 * (tr_h - disc_h)
    blakely_crest = np.maximum(-lam_min, 0.0).astype(np.float32)
    mm[:, 3] = blakely_crest[footprint]
    del g_rtp, g_rtp_sm, hyy, hxx, hxy, tr_h, disc_h, lam_min, blakely_crest

    # RTP-TMI Remanence / Inclination Phase Discordance (`col 4`)
    z_rtp = _robust_z_grid(rtp_sm, footprint)
    z_tmi = _robust_z_grid(ndi.gaussian_filter(b14_tmi, sigma=1.5), footprint)
    remanence_disc = np.abs(z_rtp - z_tmi).astype(np.float32)
    mm[:, 4] = remanence_disc[footprint]
    del b14_tmi, z_rtp, z_tmi, remanence_disc, rtp_sm
    gc.collect()

    # --- Pass B: Joint Multi-Physics Principal Strike + 6-Field Odd-Symmetric Steps (`cols 5..11`) ---
    with rasterio.open(features_tif) as src:
        b06_rad_tc = DD._clean_band_edt(src.read(6), footprint)
        b11_gvy = DD._clean_band_edt(src.read(11), footprint)
        b12_elev = DD._clean_band_edt(src.read(12), footprint)
        b13_grav = DD._clean_band_edt(src.read(13), footprint)
        b15_depth = np.maximum(DD._clean_band_edt(src.read(15), footprint), 0.0)
        b17_cond = np.maximum(DD._clean_band_edt(src.read(17), footprint), 0.0)
        b18_gvx = DD._clean_band_edt(src.read(18), footprint)

    elev_sm = ndi.gaussian_filter(b12_elev, sigma=1.5)
    e_gy = ndi.sobel(elev_sm, axis=0) / np.float32(8.0)
    e_gx = ndi.sobel(elev_sm, axis=1) / np.float32(8.0)
    del elev_sm

    # Unit-scale each vector modality by its footprint RMS norm so no single field dominates strike
    rms_r = float(np.sqrt(np.mean((r_gy[footprint] ** 2 + r_gx[footprint] ** 2))) + 1e-6)
    rms_g = float(np.sqrt(np.mean((b11_gvy[footprint] ** 2 + b18_gvx[footprint] ** 2))) + 1e-6)
    rms_e = float(np.sqrt(np.mean((e_gy[footprint] ** 2 + e_gx[footprint] ** 2))) + 1e-6)

    ry_n, rx_n = r_gy / rms_r, r_gx / rms_r
    gy_n, gx_n = b11_gvy / rms_g, b18_gvx / rms_g
    ey_n, ex_n = e_gy / rms_e, e_gx / rms_e
    del r_gy, r_gx, b11_gvy, b18_gvx, e_gy, e_gx

    j_yy_raw = 0.40 * (gy_n * gy_n) + 0.35 * (ry_n * ry_n) + 0.25 * (ey_n * ey_n)
    j_xx_raw = 0.40 * (gx_n * gx_n) + 0.35 * (rx_n * rx_n) + 0.25 * (ex_n * ex_n)
    j_yx_raw = 0.40 * (gy_n * gx_n) + 0.35 * (ry_n * rx_n) + 0.25 * (ey_n * ex_n)
    del ry_n, rx_n, gy_n, gx_n, ey_n, ex_n

    j_yy = ndi.gaussian_filter(j_yy_raw.astype(np.float32), sigma=4.0)
    j_xx = ndi.gaussian_filter(j_xx_raw.astype(np.float32), sigma=4.0)
    j_yx = ndi.gaussian_filter(j_yx_raw.astype(np.float32), sigma=4.0)
    del j_yy_raw, j_xx_raw, j_yx_raw

    tr_j = j_yy + j_xx
    disc_j = np.hypot(j_xx - j_yy, 2.0 * j_yx)
    mp_coh = (disc_j / (tr_j + np.float32(1e-5))).astype(np.float32)
    mm[:, 5] = mp_coh[footprint]

    # Major eigenvector of J in (x, y) -> cross-fault normal angle
    phi_norm = 0.5 * np.arctan2(2.0 * j_yx, j_xx - j_yy)  # angle from +x toward +y
    nx_grid = np.cos(phi_norm).astype(np.float32)
    ny_grid = np.sin(phi_norm).astype(np.float32)
    del j_yy, j_xx, j_yx, tr_j, disc_j, phi_norm

    # Orient normal consistently toward the hanging-wall basin (-grad G_6(grav) + 0.5*grad G_6(depth))
    grav_reg = ndi.gaussian_filter(b13_grav, sigma=6.0)
    depth_reg = ndi.gaussian_filter(np.log1p(b15_depth), sigma=6.0)
    basin_vy = (-ndi.sobel(grav_reg, axis=0) / rms_g) + 0.5 * ndi.sobel(depth_reg, axis=0)
    basin_vx = (-ndi.sobel(grav_reg, axis=1) / rms_g) + 0.5 * ndi.sobel(depth_reg, axis=1)
    dot_basin = ny_grid * basin_vy + nx_grid * basin_vx
    flip = np.where(dot_basin < 0.0, np.float32(-1.0), np.float32(1.0))
    ny_fp = (ny_grid[footprint] * flip[footprint]).astype(np.float32)
    nx_fp = (nx_grid[footprint] * flip[footprint]).astype(np.float32)
    mp_coh_fp = mp_coh[footprint].astype(np.float32)
    del grav_reg, depth_reg, basin_vy, basin_vx, dot_basin, flip, ny_grid, nx_grid, mp_coh
    gc.collect()

    fp_r_i, fp_c_i = np.nonzero(footprint)
    fp_r = fp_r_i.astype(np.float32)
    fp_c = fp_c_i.astype(np.float32)
    del fp_r_i, fp_c_i

    step_elev = _strike_step_diff_fp(b12_elev, fp_r, fp_c, ny_fp, nx_fp)
    step_grav = _strike_step_diff_fp(b13_grav, fp_r, fp_c, ny_fp, nx_fp)
    step_rtp = _strike_step_diff_fp(b02_rtp, fp_r, fp_c, ny_fp, nx_fp)
    step_depth = _strike_step_diff_fp(np.log1p(b15_depth), fp_r, fp_c, ny_fp, nx_fp)
    step_rad_tc = _strike_step_diff_fp(b06_rad_tc, fp_r, fp_c, ny_fp, nx_fp)
    step_cond = _strike_step_diff_fp(np.log1p(b17_cond), fp_r, fp_c, ny_fp, nx_fp)

    del b02_rtp, b06_rad_tc, b12_elev, b13_grav, b15_depth, b17_cond, fp_r, fp_c, ny_fp, nx_fp
    gc.collect()

    mm[:, 6] = np.abs(step_elev).astype(np.float32)
    mm[:, 7] = np.abs(step_grav).astype(np.float32)
    mm[:, 8] = np.abs(step_rtp).astype(np.float32)
    mm[:, 9] = np.abs(step_depth).astype(np.float32)
    mm[:, 10] = np.abs(step_rad_tc).astype(np.float32)

    # Signed Normal-Fault Hanging-Wall Polarity Concordance (`col 11`):
    # Into the hanging-wall (+n): basement deepens (+step_depth), gravity drops (-step_grav),
    # elevation drops (-step_elev), and basin clay conductivity rises (+step_cond).
    z_dep_plus = np.maximum(_robust_z_fp(step_depth), 0.0)
    z_grv_drop = np.maximum(_robust_z_fp(-step_grav), 0.0)
    z_elv_drop = np.maximum(_robust_z_fp(-step_elev), 0.0)
    z_cnd_plus = np.maximum(_robust_z_fp(step_cond), 0.0)
    concordance = (
        (0.30 * z_dep_plus + 0.30 * z_grv_drop + 0.22 * z_elv_drop + 0.18 * z_cnd_plus)
        * (0.40 + 0.60 * mp_coh_fp)
    ).astype(np.float32)
    mm[:, 11] = concordance
    del step_elev, step_grav, step_rtp, step_depth, step_rad_tc, step_cond
    del z_dep_plus, z_grv_drop, z_elv_drop, z_cnd_plus, concordance, mp_coh_fp
    gc.collect()

    # --- Pass C: `H13-2` Continuum Transtensional Geodetic Strain & Log-Seismogenic (`cols 12..19`) ---
    with rasterio.open(features_tif) as src:
        b04_inv = np.maximum(DD._clean_band_edt(src.read(4), footprint), 0.0)
        b07_shr = np.maximum(DD._clean_band_edt(src.read(7), footprint), 0.0)
        b08_dil = DD._clean_band_edt(src.read(8), footprint)
        b10_deq = np.maximum(DD._clean_band_edt(src.read(10), footprint), 0.0)
        b16_ieq = np.maximum(DD._clean_band_edt(src.read(16), footprint), 0.0)

    transtension = (np.maximum(b08_dil, 0.0) * b07_shr / (b04_inv + np.float32(0.10))).astype(np.float32)
    kinematic_ang = np.arctan2(b08_dil, b07_shr + np.float32(0.05)).astype(np.float32)
    shr_grad = DD._grad_mag(b07_shr, sigma=4.0)
    dil_grad = DD._grad_mag(b08_dil, sigma=4.0)

    eq_log_prox = (-np.log1p(b10_deq / np.float32(500.0))).astype(np.float32)
    log_ieq = np.log1p(b16_ieq).astype(np.float32)
    eq_log_hp = (log_ieq - ndi.gaussian_filter(log_ieq, sigma=15.0)).astype(np.float32)

    t_fp = transtension[footprint]
    eq_prox_fp = eq_log_prox[footprint]
    z_trans_pos = np.maximum(_robust_z_fp(t_fp), 0.0)
    z_eq_near = np.maximum(_robust_z_fp(eq_prox_fp), 0.0)
    z_eq_quiet = np.maximum(_robust_z_fp(-eq_prox_fp), 0.0)

    mm[:, 12] = t_fp
    mm[:, 13] = kinematic_ang[footprint]
    mm[:, 14] = shr_grad[footprint]
    mm[:, 15] = dil_grad[footprint]
    mm[:, 16] = eq_prox_fp
    mm[:, 17] = eq_log_hp[footprint]
    mm[:, 18] = (z_trans_pos * z_eq_near).astype(np.float32)
    mm[:, 19] = (z_trans_pos * z_eq_quiet).astype(np.float32)

    del b04_inv, b07_shr, b08_dil, b10_deq, b16_ieq, transtension, kinematic_ang
    del shr_grad, dil_grad, eq_log_prox, log_ieq, eq_log_hp
    del t_fp, eq_prox_fp, z_trans_pos, z_eq_near, z_eq_quiet
    mm.flush()
    gc.collect()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": PTHA_FEATURE_NAMES,
        "dtype": "float32",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(PTHA_FEATURE_NAMES), meta


def build_ptha_structural_crest_surface(
    mhtr_edge: np.ndarray,
    X_ptha: np.memmap,
    footprint: np.ndarray,
) -> np.ndarray:
    """Combine gravity Marussi crest (`S11`) + magnetic Blakely/Verduzco crests + step concordance (`S13`).

    100% label-free normalized `[0, 1]` structural edge surface used as linework
    corridor modulator during submodular dot placement.
    """
    z_mhtr = np.maximum(_robust_z_fp(mhtr_edge[footprint]), 0.0)
    z_blakely = np.maximum(_robust_z_fp(np.asarray(X_ptha[:, 3], dtype=np.float32)), 0.0)
    z_verduzco = np.maximum(_robust_z_fp(np.asarray(X_ptha[:, 2], dtype=np.float32)), 0.0)
    z_rad_step = np.maximum(_robust_z_fp(np.asarray(X_ptha[:, 10], dtype=np.float32)), 0.0)
    z_concord = np.maximum(_robust_z_fp(np.asarray(X_ptha[:, 11], dtype=np.float32)), 0.0)

    raw_fp = (
        0.34 * z_mhtr
        + 0.24 * z_blakely
        + 0.14 * z_verduzco
        + 0.12 * z_rad_step
        + 0.16 * z_concord
    ).astype(np.float32)
    p995 = float(np.percentile(raw_fp, 99.5)) + 1e-6
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(raw_fp / p995, 0.0, 1.0)
    return out


def _assemble_rows(
    X_static: np.memmap,
    static_cols: list[int],
    X_s11: np.memmap,
    s11_cols: list[int],
    X_ptha: np.memmap,
    ptha_cols: list[int],
    row_idx: np.ndarray,
) -> np.ndarray:
    n_s = len(static_cols)
    n_11 = len(s11_cols)
    n_13 = len(ptha_cols)
    out = np.empty((row_idx.size, n_s + n_11 + n_13), dtype=np.float32)
    if n_s:
        out[:, :n_s] = X_static[row_idx][:, static_cols]
    if n_11:
        out[:, n_s : n_s + n_11] = X_s11[row_idx][:, s11_cols]
    if n_13:
        out[:, n_s + n_11 :] = X_ptha[row_idx][:, ptha_cols]
    return out


def fit_and_predict_ptha_oof_fold(
    *,
    X_static: np.memmap,
    static_cols: list[int],
    static_names: list[str],
    X_s11: np.memmap,
    s11_cols: list[int],
    s11_names: list[str],
    X_ptha: np.memmap,
    ptha_cols: list[int],
    ptha_names: list[str],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    max_pos: int = 65_000,
    max_neg: int = 230_000,
    seed: int = 910,
) -> tuple[np.ndarray, dict[str, float]]:
    """Train fold-safe `S13-PTHA` ensemble on `visible_faults` outside `exclude_mask`.

    Combines:
      1. `HGB-Full` (deep multi-physics interaction trees),
      2. `HGB-ColSub` (`max_features=0.55` preventing topographic root-split monopoly),
      3. `HGB-Subsurface` (Topography-Blind Subsurface Specialist trained strictly
         on non-topographic gravity/magnetic/radiometric/depth/conductivity/strain/seismic
         features so flat-basin concealed faults suffer zero low-slope penalty while
         erosional cliffs without subsurface support are down-weighted),
      4. `L2-Logistic` on robust-standardized features.

    Returns `(prob_2d, calib_info)` where `calib_info` records strictly training-domain
    prevalence (`pi_vis_train`, `pi_sample_weighted`) for exact prior-shift Bayes
    calibration in `H13-3` without touching any test-fold data.
    """
    rng = np.random.default_rng(seed)

    pos_fp_mask = visible_faults[footprint]
    neg_fp_mask = (~visible_faults[footprint]) & (~exclude_mask[footprint])

    pos_idx_all = np.flatnonzero(pos_fp_mask)
    neg_idx_all = np.flatnonzero(neg_fp_mask)

    n_pos_true = int(pos_idx_all.size)
    n_neg_true = int(neg_idx_all.size)
    pi_vis_train = float(n_pos_true) / float(max(n_pos_true + n_neg_true, 1))

    pos_idx = (
        rng.choice(pos_idx_all, size=max_pos, replace=False)
        if pos_idx_all.size > max_pos
        else pos_idx_all
    )
    pos_idx = np.sort(pos_idx)

    # Hard-negative mining across BOTH steep non-fault slopes AND strong non-fault magnetic/gravity edges
    slope_vals = np.asarray(X_static[:, 18], dtype=np.float32)[neg_idx_all]
    mhtr_vals = np.asarray(X_s11[:, 4], dtype=np.float32)[neg_idx_all]
    blakely_vals = np.asarray(X_ptha[:, 3], dtype=np.float32)[neg_idx_all]
    sl_thr = float(np.percentile(slope_vals, 75))
    mh_thr = float(np.percentile(mhtr_vals, 78))
    bl_thr = float(np.percentile(blakely_vals, 80))
    hard_mask = (slope_vals >= sl_thr) | (mhtr_vals >= mh_thr) | (blakely_vals >= bl_thr)
    del slope_vals, mhtr_vals, blakely_vals

    hard_pool = neg_idx_all[hard_mask]
    easy_pool = neg_idx_all[~hard_mask]
    n_hard = min(max_neg // 2, hard_pool.size)
    n_easy = min(max_neg - n_hard, easy_pool.size)
    neg_hard = rng.choice(hard_pool, size=n_hard, replace=False) if hard_pool.size > n_hard else hard_pool
    neg_easy = rng.choice(easy_pool, size=n_easy, replace=False) if easy_pool.size > n_easy else easy_pool
    neg_idx = np.concatenate([np.sort(neg_hard), np.sort(neg_easy)])
    neg_weights = np.concatenate([
        np.full(neg_hard.size, 0.55, dtype=np.float32),
        np.full(neg_easy.size, 1.45, dtype=np.float32),
    ])

    all_feat_names = (
        [static_names[i] for i in static_cols]
        + [s11_names[i] for i in s11_cols]
        + [ptha_names[i] for i in ptha_cols]
    )
    subsurface_col_mask = np.array([nm not in TOPO_FEATURE_NAMES for nm in all_feat_names], dtype=bool)

    X_pos = _assemble_rows(X_static, static_cols, X_s11, s11_cols, X_ptha, ptha_cols, pos_idx)
    X_neg = _assemble_rows(X_static, static_cols, X_s11, s11_cols, X_ptha, ptha_cols, neg_idx)
    X_train = np.vstack([X_pos, X_neg])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])
    w_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.float32),
        neg_weights,
    ])
    pi_sample_weighted = float(pos_idx.size) / float(w_train.sum())
    del X_pos, X_neg

    hgb_full = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.055,
        max_iter=230,
        max_leaf_nodes=41,
        min_samples_leaf=85,
        l2_regularization=3.0,
        max_bins=255,
        early_stopping=False,
        random_state=seed,
    )
    hgb_full.fit(X_train, y_train, sample_weight=w_train)

    hgb_colsub = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.055,
        max_iter=220,
        max_leaf_nodes=35,
        max_depth=7,
        min_samples_leaf=100,
        l2_regularization=4.5,
        max_features=0.55,
        max_bins=255,
        early_stopping=False,
        random_state=seed + 101,
    )
    hgb_colsub.fit(X_train, y_train, sample_weight=w_train)

    hgb_sub = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.055,
        max_iter=210,
        max_leaf_nodes=35,
        min_samples_leaf=95,
        l2_regularization=4.0,
        max_bins=255,
        early_stopping=False,
        random_state=seed + 202,
    )
    hgb_sub.fit(X_train[:, subsurface_col_mask], y_train, sample_weight=w_train)

    med = np.median(X_train, axis=0)
    scale = np.median(np.abs(X_train - med), axis=0) * 1.4826 + 1e-5
    X_lr = np.clip((X_train - med) / scale, -6.0, 6.0)
    lr = LogisticRegression(C=0.25, max_iter=250, random_state=seed)
    lr.fit(X_lr, y_train, sample_weight=w_train)
    del X_train, X_lr, y_train, w_train
    gc.collect()

    # Chunked inference across all footprint pixels (`peak chunk ~135 MB`)
    n_fp = int(footprint.sum())
    preds_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 450_000
    n_s = len(static_cols)
    n_11 = len(s11_cols)
    n_13 = len(ptha_cols)
    tot_cols = n_s + n_11 + n_13

    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = np.empty((e - s, tot_cols), dtype=np.float32)
        if n_s:
            Xc[:, :n_s] = X_static[s:e, static_cols]
        if n_11:
            Xc[:, n_s : n_s + n_11] = X_s11[s:e, s11_cols]
        if n_13:
            Xc[:, n_s + n_11 :] = X_ptha[s:e, ptha_cols]

        p_full = hgb_full.predict_proba(Xc)[:, 1].astype(np.float32)
        p_col = hgb_colsub.predict_proba(Xc)[:, 1].astype(np.float32)
        p_sub = hgb_sub.predict_proba(Xc[:, subsurface_col_mask])[:, 1].astype(np.float32)
        X_lrc = np.clip((Xc - med) / scale, -6.0, 6.0)
        p_lr = lr.predict_proba(X_lrc)[:, 1].astype(np.float32)

        preds_fp[s:e] = 0.46 * p_full + 0.24 * p_col + 0.20 * p_sub + 0.10 * p_lr
        del Xc, X_lrc, p_full, p_col, p_sub, p_lr

    out_2d = np.zeros(footprint.shape, dtype=np.float32)
    out_2d[footprint] = preds_fp
    calib = {
        "pi_vis_train": round(pi_vis_train, 8),
        "pi_sample_weighted": round(pi_sample_weighted, 8),
        "n_pos_train_true": n_pos_true,
        "n_neg_train_true": n_neg_true,
    }
    return out_2d, calib


def prior_shift_calibrate_surface(
    prob_2d: np.ndarray,
    footprint: np.ndarray,
    *,
    pi_true: float,
    pi_sample: float,
) -> np.ndarray:
    """Apply exact Elkan / Saerens-Latinne-Decaestecker prior-shift Bayes formula.

    Uses strictly training-domain base rates `(pi_true, pi_sample)` so zero
    test-fold information enters calibration.
    """
    p = np.clip(prob_2d[footprint].astype(np.float64), 1e-6, 1.0 - 1e-6)
    odds_ratio = (pi_true / max(1.0 - pi_true, 1e-9)) * (
        max(1.0 - pi_sample, 1e-9) / max(pi_sample, 1e-9)
    )
    num = odds_ratio * p
    cal = (num / (num + (1.0 - p))).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = cal
    return out


def _detect_1d_directional_ridge(arr: np.ndarray, span: int = 2) -> np.ndarray:
    """True 4-azimuth 1-D cross-strike crest detector (N-S, E-W, NE-SW, NW-SE).

    Unlike a 2-D box maximum filter (`ndi.maximum_filter`), which breaks sloping
    1-D fault ridges while passing entire flat 2-D blobs, this isolates 1-pixel-wide
    fault centerlines along any strike orientation.
    """
    h, w = arr.shape
    ap = np.pad(arr, span, mode="edge")
    c = ap[span : h + span, span : w + span]
    if span == 1:
        return (
            ((c >= ap[0:h, 1 : w + 1]) & (c >= ap[2 : h + 2, 1 : w + 1]))
            | ((c >= ap[1 : h + 1, 0:w]) & (c >= ap[1 : h + 1, 2 : w + 2]))
            | ((c >= ap[0:h, 0:w]) & (c >= ap[2 : h + 2, 2 : w + 2]))
            | ((c >= ap[0:h, 2 : w + 2]) & (c >= ap[2 : h + 2, 0:w]))
        )
    return (
        ((c >= ap[1 : h + 1, 2 : w + 2]) & (c >= ap[3 : h + 3, 2 : w + 2]) & (c >= ap[0:h, 2 : w + 2]) & (c >= ap[4 : h + 4, 2 : w + 2]))
        | ((c >= ap[2 : h + 2, 1 : w + 1]) & (c >= ap[2 : h + 2, 3 : w + 3]) & (c >= ap[2 : h + 2, 0:w]) & (c >= ap[2 : h + 2, 4 : w + 4]))
        | ((c >= ap[1 : h + 1, 1 : w + 1]) & (c >= ap[3 : h + 3, 3 : w + 3]) & (c >= ap[0:h, 0:w]) & (c >= ap[4 : h + 4, 4 : w + 4]))
        | ((c >= ap[1 : h + 1, 3 : w + 3]) & (c >= ap[3 : h + 3, 1 : w + 1]) & (c >= ap[0:h, 4 : w + 4]) & (c >= ap[4 : h + 4, 0:w]))
    )


def _lazy_greedy_submodular_select(
    w_surf: np.ndarray,
    cand_mask: np.ndarray,
    *,
    rank_surf: np.ndarray | None = None,
    max_dots: int,
    min_gain_threshold: float = 0.0,
    min_spacing_px: float = 2.55,
    pool_mult: int = 10,
    min_pool: int = 60_000,
) -> tuple[np.ndarray, float]:
    """Minoux lazy-greedy 300 m triangular-kernel submodular dot selector.

    Stops as soon as either `max_dots` have been emitted OR the marginal
    expected 300 m kernel gain drops below `min_gain_threshold` (Dinkelbach's
    exact fractional-programming optimality condition). Returns `(dots_2d, last_gain)`.
    """
    h, w = w_surf.shape
    out = np.zeros((h, w), dtype=np.float32)
    if max_dots <= 0 or not cand_mask.any():
        return out, 0.0

    r_surf = w_surf if rank_surf is None else rank_surf
    cand_r, cand_c = np.nonzero(cand_mask & (w_surf > 0.0))
    if cand_r.size == 0:
        return out, 0.0

    cand_s = r_surf[cand_r, cand_c]
    pool_k = min(cand_r.size, max(max_dots * pool_mult, min_pool))
    if cand_r.size > pool_k:
        top_idx = np.argpartition(cand_s, -pool_k)[-pool_k:]
        cand_r = cand_r[top_idx]
        cand_c = cand_c[top_idx]

    offs: list[tuple[int, int, float]] = []
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            dist = float(np.hypot(dy, dx))
            if dist < 3.0:
                offs.append((dy, dx, 1.0 - dist / 3.0))

    sp_r = int(np.ceil(min_spacing_px))
    sp_offs: list[tuple[int, int]] = []
    for dy in range(-sp_r, sp_r + 1):
        for dx in range(-sp_r, sp_r + 1):
            if float(np.hypot(dy, dx)) < min_spacing_px:
                sp_offs.append((dy, dx))

    pad = max(3, sp_r + 1)
    w_pad = np.pad(w_surf, pad, mode="constant", constant_values=0.0)
    cov_pad = np.zeros_like(w_pad, dtype=np.float32)
    blocked_pad = np.zeros(w_pad.shape, dtype=bool)

    cr_p = cand_r + pad
    cc_p = cand_c + pad
    init_gains = np.zeros(cr_p.size, dtype=np.float32)
    for dy, dx, kw in offs:
        init_gains += w_pad[cr_p + dy, cc_p + dx] * np.float32(kw)

    if min_gain_threshold > 0.0:
        keep = init_gains >= np.float32(min_gain_threshold)
        cr_p = cr_p[keep]
        cc_p = cc_p[keep]
        init_gains = init_gains[keep]
        if cr_p.size == 0:
            return out, 0.0

    heap: list[tuple[float, int, int]] = [
        (-float(init_gains[i]), int(cr_p[i]), int(cc_p[i]))
        for i in range(cr_p.size)
    ]
    heapq.heapify(heap)

    selected = 0
    last_gain = 0.0
    while selected < max_dots and heap:
        neg_ub, rp, cp = heapq.heappop(heap)
        if blocked_pad[rp, cp]:
            continue
        ub = -neg_ub
        if ub < min_gain_threshold:
            break

        gain = 0.0
        for dy, dx, kw in offs:
            cur_c = float(cov_pad[rp + dy, cp + dx])
            if kw > cur_c:
                gain += float(w_pad[rp + dy, cp + dx]) * (kw - cur_c)

        if gain < min_gain_threshold:
            continue

        next_ub = -heap[0][0] if heap else -1.0
        if gain >= next_ub * 0.996:
            out[rp - pad, cp - pad] = 1.0
            last_gain = gain
            for dy, dx, kw in offs:
                if kw > cov_pad[rp + dy, cp + dx]:
                    cov_pad[rp + dy, cp + dx] = kw
            for dy, dx in sp_offs:
                blocked_pad[rp + dy, cp + dx] = True
            selected += 1
        else:
            heapq.heappush(heap, (-gain, rp, cp))

    return out, float(last_gain)


def build_dinkelbach_expected_intensity(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    calibration_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    gamma: float = 1.18,
    crest_weight: float = 0.48,
    keep_corridor_frac: float = 0.16,
    concealed_pu_boost: float = 1.24,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Build 1-D-centerline-concentrated, continuum-floored Dinkelbach weight `w(x)`.

    Crucially, `q_floor` is calibrated strictly on `calibration_mask` (in OOF folds:
    `train_eligible_mask`, i.e., Fold `k`'s 3 training quadrants — zero test-fold
    quantile distortion!), concentrating the 300 m kernel integral onto 1-pixel-wide
    fault centerlines (`_detect_1d_directional_ridge`) while boosting concealed
    piedmont geophysical crests via Positive-Unlabeled propensity (`concealed_pu_boost`)
    without forcing a hard barren-playa quota.
    """
    pi_cal = prior_shift_calibrate_surface(
        prob_2d, footprint, pi_true=pi_true, pi_sample=pi_sample
    )
    q = (pi_cal * (1.0 + np.float32(crest_weight) * crest_2d)).astype(np.float32)
    q[~footprint] = 0.0

    cal_vals = q[calibration_mask & (q > 0.0)]
    if cal_vals.size > 0:
        q_floor = float(np.quantile(cal_vals, 1.0 - keep_corridor_frac))
    else:
        q_floor = 0.0

    is_q_ridge = _detect_1d_directional_ridge(q, span=2)
    is_crest_ridge = _detect_1d_directional_ridge(crest_2d, span=1)

    q_exc = np.maximum(q - np.float32(q_floor), 0.0)
    ridge_mult = np.where(is_q_ridge, np.float32(1.0), np.float32(0.24))
    pu_mult = np.where(piedmont_mask & is_crest_ridge, np.float32(concealed_pu_boost), np.float32(1.0))

    w = (np.float32(1000.0) * (q_exc ** np.float32(gamma)) * ridge_mult * pu_mult).astype(np.float32)
    w[~footprint] = 0.0
    rank_s = (q * np.where(is_q_ridge, np.float32(1.15), np.float32(0.85)) * pu_mult).astype(np.float32)
    return w, rank_s, q_floor


def dinkelbach_fold_independent_emit(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    footprint: np.ndarray,
    train_eligible_mask: np.ndarray,
    test_eligible_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    target_pool_dots: int = 48_000,
    full_eligible_pixels: int = 4_600_000,
    min_spacing_px: float = 2.50,
    min_fold_dots: int = 6_500,
    max_fold_dots: int = 18_000,
) -> tuple[np.ndarray, dict[str, float]]:
    """Fold-independent Dinkelbach Expected-DTI Submodular Emitter (`H13-3`)."""
    w_surf, rank_s, q_floor_k = build_dinkelbach_expected_intensity(
        prob_2d,
        crest_2d,
        piedmont_mask,
        footprint,
        calibration_mask=train_eligible_mask,
        pi_true=pi_true,
        pi_sample=pi_sample,
    )

    # Calibrate Dinkelbach marginal-gain threshold `tau_k` on the full contiguous
    # training territory `train_eligible_mask` (strictly zero test-fold data touched).
    n_cal_px = int(train_eligible_mask.sum())
    n_cal_target = max(
        1_000,
        int(round(target_pool_dots * (n_cal_px / float(max(full_eligible_pixels, 1))))),
    )
    _, tau_k = _lazy_greedy_submodular_select(
        w_surf,
        train_eligible_mask,
        rank_surf=rank_s,
        max_dots=n_cal_target,
        min_gain_threshold=0.0,
        min_spacing_px=min_spacing_px,
    )

    test_dots, last_test_gain = _lazy_greedy_submodular_select(
        w_surf,
        test_eligible_mask,
        rank_surf=rank_s,
        max_dots=max_fold_dots,
        min_gain_threshold=tau_k,
        min_spacing_px=min_spacing_px,
    )
    n_emitted = int((test_dots > 0).sum())
    if n_emitted < min_fold_dots:
        test_dots, last_test_gain = _lazy_greedy_submodular_select(
            w_surf,
            test_eligible_mask,
            rank_surf=rank_s,
            max_dots=min_fold_dots,
            min_gain_threshold=0.0,
            min_spacing_px=min_spacing_px,
        )
        n_emitted = int((test_dots > 0).sum())

    return test_dots, {
        "q_floor_train": round(float(q_floor_k), 7),
        "tau_dinkelbach_train": round(float(tau_k), 7),
        "last_test_gain": round(float(last_test_gain), 7),
        "n_cal_pixels": n_cal_px,
        "n_cal_target_dots": n_cal_target,
        "n_test_emitted_dots": n_emitted,
    }


def dinkelbach_full_map_emit(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    footprint: np.ndarray,
    full_eligible_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    n_dots: int = 44_000,
    min_spacing_px: float = 2.50,
) -> tuple[np.ndarray, float]:
    """Emit full-Nevada binary `{0.0, 1.0}` dot raster under unified Dinkelbach objective."""
    w_surf, rank_s, _ = build_dinkelbach_expected_intensity(
        prob_2d,
        crest_2d,
        piedmont_mask,
        footprint,
        calibration_mask=full_eligible_mask,
        pi_true=pi_true,
        pi_sample=pi_sample,
    )
    return _lazy_greedy_submodular_select(
        w_surf,
        full_eligible_mask,
        rank_surf=rank_s,
        max_dots=n_dots,
        min_gain_threshold=0.0,
        min_spacing_px=min_spacing_px,
    )
