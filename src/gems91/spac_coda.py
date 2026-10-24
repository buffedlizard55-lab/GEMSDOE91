"""Session 12 (`S12-SPAC`): Dimensionally-Calibrated 3-D Magnetic Analytic Signal &
Thurston-Smith (1997) Source Parameter Imaging (`SPI`) + Shallow GeoDAWN Residual +
Multi-Scale Frangi Hessian Vesselness + Kreemer Kinematic Strain/Swarm Conduit +
Fold-Safe Two-Stage Steerable Radon Auto-Context + Three-Regime 300 m Submodular DTI.

Grounded in four Session 12 forensic discoveries (`docs/HYPOTHESES_S12.md`):
  1. `IR-91-S12-01`: `Band 03 (tmi_hg)` equals `200.0 * ||grad_H(Band 14 tmi)||_(nT/m)`
     (`r = 0.99992`), while `Band 09 (tmi_vg)` is the true vertical derivative
     `d(TMI)/dz` in `nT/m` (`r = 0.98851` with FFT `dz(B14)`). Reconciling units
     (`h_tmi = B03 / 200.0`, `v_tmi = B09`) unlocks the true inclination- and
     remanence-invariant 3-D Analytic Signal `|A_TMI|` and Thurston-Smith (1997)
     `SPI` local wavenumber `k_SPI = ||grad_H(arctan2(v_tmi, h_tmi))||_2`.
  2. `IR-91-S12-02`: `Band 14 (tmi)` (`hf_ratio = 0.1000`) minus `Band 01 (mag_anom)`
     (`hf_ratio = 0.0099`) isolates shallow upper-crustal brittle volcanic and
     intrabasinal fault offsets newly acquired by the 2021-2022 GeoDAWN drape.
  3. `IR-91-S12-03`: Official DOE GDR #1391 proves `Band 10 (deq_n100a15)` is
     Dependent (Swarm/Aftershock) Earthquake Density (`r = +0.7354` with `log1p(B16)`),
     NOT distance to earthquake, restoring Walker Lane fluid-swarm & kinematic
     transtensional (`W_k`) fault localization.
  4. `IR-91-S12-04`: Locking a prior-invariant negative-to-positive sampling ratio
     (`3.65 : 1`) across pairwise inner sub-folds, 3-quadrant holdout folds, and
     the 4-quadrant full fit enables leak-free Two-Stage Steerable Radon Auto-Context
     (`900 m` & `2.0 km` collinear rays + two-sided alluvial wash-gap bridging).
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

from . import dd_vtc_pu as DD
from . import mhtr_coda as MC

S12_SPAC_STATIC_FEATURE_NAMES = [
    # Group A (H12-1): True 3-D Analytic Signal, SPI Wavenumber, Shallow GeoDAWN Residual,
    # Multi-Scale Frangi Hessian Vesselness, & Cross-Fault Block Dipole (12 cols)
    "s12_tmi_asig_log",
    "s12_tmi_tilt_true",
    "s12_spi_local_wavenum",
    "s12_updip_spi_wavenum",
    "s12_geodawn_shallow_res",
    "s12_geodawn_shallow_grad",
    "s12_remanent_rtp_disc",
    "s12_frangi_topo_s1p5",
    "s12_frangi_topo_s4p0",
    "s12_frangi_asig_s2p0",
    "s12_frangi_marussi_s2p5",
    "s12_crossfault_dipole_600m",
    # Group B (H12-2): True Dependent Swarm Seismicity, Kreemer Strain Kinematic Style,
    # & Shallow GeoDAWN Hydrothermal Demagnetization-Alteration Joint (8 cols)
    "s12_seis_dep_swarm_log",
    "s12_seis_ind_main_log",
    "s12_seis_swarm_excess",
    "s12_seis_swarm_grad",
    "s12_kreemer_kinematic_w",
    "s12_strain_tensor_excess",
    "s12_transtens_work_rate",
    "s12_hydro_demag_alter_joint",
]

S12_AUTOCONTEXT_FEATURE_NAMES = [
    "ac_p1_raw",
    "ac_p1_sm2",
    "ac_ray900m_max",
    "ac_ray2km_max",
    "ac_wash_bridge_1km",
    "ac_wash_bridge_2km",
    "ac_transverse_sharpness",
    "ac_strike_anisotropy",
    "ac_corridor_1p2km",
    "ac_corridor_3km",
]


def _frangi_ridge_2d(
    field: np.ndarray,
    footprint: np.ndarray,
    *,
    sigma: float,
    beta_f: float = 0.55,
    return_normal: bool = False,
) -> np.ndarray | tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute 2-D Frangi/Sato Hessian tubular ridge vesselness in `[0, 1]` for
    bright 1-D curvilinear ridges on `field` at Gaussian scale `sigma` (in pixels).

    Suppresses isotropic circular blobs/plugs (`|lambda_2 / lambda_1| -> 1`) while
    enhancing elongated 1-D fault traces (`|lambda_2 / lambda_1| -> 0`, `lambda_1 < 0`).
    """
    s2 = float(sigma * sigma)
    hxx = (ndi.gaussian_filter(field, sigma=sigma, order=(0, 2)) * s2).astype(np.float32)
    hyy = (ndi.gaussian_filter(field, sigma=sigma, order=(2, 0)) * s2).astype(np.float32)
    hxy = (ndi.gaussian_filter(field, sigma=sigma, order=(1, 1)) * s2).astype(np.float32)

    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    e_minus = 0.5 * (tr - disc)  # Most negative curvature (across bright ridge)
    e_plus = 0.5 * (tr + disc)   # Along-ridge curvature

    abs_1 = np.maximum(np.abs(e_minus), np.abs(e_plus))
    abs_2 = np.minimum(np.abs(e_minus), np.abs(e_plus))
    rb = abs_2 / (abs_1 + 1e-6)
    s_frob = np.hypot(e_minus, e_plus)

    s_sub = s_frob[footprint][::20]
    c_scale = max(float(np.percentile(s_sub, 85)), 1e-5)

    vess = np.where(
        e_minus < 0.0,
        np.exp(-(rb * rb) / (2.0 * beta_f * beta_f))
        * (1.0 - np.exp(-(s_frob * s_frob) / (2.0 * c_scale * c_scale))),
        0.0,
    ).astype(np.float32)

    if not return_normal:
        return vess

    # Unit normal perpendicular to ridge axis (eigenvector of `e_minus`)
    ang = 0.5 * np.arctan2(2.0 * hxy, hxx - hyy)
    ny = np.cos(ang).astype(np.float32)
    nx = (-np.sin(ang)).astype(np.float32)
    return vess, ny, nx


def build_or_load_s12_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed float32 Session 12 static feature matrix `(N_fp, 20)`.

    100% derived from the official competition `training_features.tif` raster with
    strictly bounded transient RAM (< 950 MB).
    """
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s12_spac_features_v1.dat"
    meta_path = cache_p / "s12_spac_features_v1.json"

    n_fp = int(footprint.sum())
    n_cols = len(S12_SPAC_STATIC_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == S12_SPAC_STATIC_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S12_SPAC_STATIC_FEATURE_NAMES), meta

    h, w = footprint.shape
    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    # --- Pass A: Magnetics (B01, B02, B03, B09, B14) + Basement Updip (B11, B15, B18) ---
    with rasterio.open(features_tif) as fsrc:
        b1 = DD._clean_band_edt(fsrc.read(1), footprint)
        b2 = DD._clean_band_edt(fsrc.read(2), footprint)
        b3 = np.maximum(DD._clean_band_edt(fsrc.read(3), footprint), 0.0)
        b9 = DD._clean_band_edt(fsrc.read(9), footprint)
        b11 = DD._clean_band_edt(fsrc.read(11), footprint)
        b14 = DD._clean_band_edt(fsrc.read(14), footprint)
        b15 = np.maximum(DD._clean_band_edt(fsrc.read(15), footprint), 0.0)
        b18 = DD._clean_band_edt(fsrc.read(18), footprint)

    # Exact unit calibration (IR-91-S12-01): B03 = 200.0 * (nT/m), B09 = 1.0 * (nT/m)
    h_tmi_ntm = (b3 / 200.0).astype(np.float32)
    del b3
    asig_ntm = np.hypot(h_tmi_ntm, b9).astype(np.float32)
    tmi_asig_log = np.log1p(100.0 * asig_ntm).astype(np.float32)
    tmi_tilt_true = np.arctan2(b9, h_tmi_ntm + 1e-4).astype(np.float32)
    del h_tmi_ntm, b9

    tilt_sm = ndi.gaussian_filter(tmi_tilt_true, sigma=1.0)
    ty_t, tx_t = np.gradient(tilt_sm)
    spi_wavenum = np.hypot(ty_t, tx_t).astype(np.float32)
    del tilt_sm, ty_t, tx_t

    # Shallow GeoDAWN draped TMI minus Regional NAMAG/INGENIOUS anomaly (IR-91-S12-02)
    shallow_diff = (b14 - b1).astype(np.float32)
    del b1, b14
    geodawn_shallow_res = DD._robust_z(shallow_diff, footprint)
    geodawn_shallow_grad = DD._grad_mag(shallow_diff, sigma=1.2)

    # Remanent / reversed-polarity volcanic contact discrepancy: 3-D Analytic Signal vs RTP grad
    rtp_grad = DD._grad_mag(b2, sigma=1.0)
    del b2
    remanent_disc = (DD._robust_z(asig_ntm, footprint) - DD._robust_z(rtp_grad, footprint)).astype(np.float32)
    del asig_ntm, rtp_grad

    # Updip deprojection of SPI wavenumber & Marussi Eotvos curvature
    b11_s = ndi.gaussian_filter(b11, sigma=1.2)
    b18_s = ndi.gaussian_filter(b18, sigma=1.2)
    del b11, b18
    hyy = np.gradient(b11_s, axis=0).astype(np.float32)
    hxx = np.gradient(b18_s, axis=1).astype(np.float32)
    hxy = (0.5 * (np.gradient(b11_s, axis=1) + np.gradient(b18_s, axis=0))).astype(np.float32)
    eotvos_curv = np.hypot(hxx - hyy, 2.0 * hxy).astype(np.float32)
    del hyy, hxx, hxy

    gnorm = np.hypot(b11_s, b18_s) + 1e-4
    dy_up = (-b11_s / gnorm).astype(np.float32)
    dx_up = (-b18_s / gnorm).astype(np.float32)
    del b11_s, b18_s, gnorm

    offset_px = np.clip((b15 * 0.7002075) / 100.0, 0.0, 10.0).astype(np.float32)
    yy_base, xx_base = np.indices((h, w), dtype=np.float32)
    coords_up = np.array([
        np.clip(yy_base + offset_px * dy_up, 0.0, h - 1.0),
        np.clip(xx_base + offset_px * dx_up, 0.0, w - 1.0),
    ])
    del dy_up, dx_up, offset_px
    updip_spi = ndi.map_coordinates(spi_wavenum, coords_up, order=1, mode="nearest").astype(np.float32)
    del coords_up

    frangi_asig_s2p0 = _frangi_ridge_2d(tmi_asig_log, footprint, sigma=2.0)
    frangi_marussi_s2p5 = _frangi_ridge_2d(eotvos_curv, footprint, sigma=2.5)
    del eotvos_curv

    mm[:, 0] = tmi_asig_log[footprint]
    mm[:, 1] = tmi_tilt_true[footprint]
    mm[:, 2] = spi_wavenum[footprint]
    mm[:, 3] = updip_spi[footprint]
    mm[:, 4] = geodawn_shallow_res[footprint]
    mm[:, 5] = geodawn_shallow_grad[footprint]
    mm[:, 6] = remanent_disc[footprint]
    mm[:, 9] = frangi_asig_s2p0[footprint]
    mm[:, 10] = frangi_marussi_s2p5[footprint]
    del tmi_asig_log, tmi_tilt_true, spi_wavenum, updip_spi, geodawn_shallow_res
    del geodawn_shallow_grad, remanent_disc, frangi_asig_s2p0, frangi_marussi_s2p5
    gc.collect()

    # --- Pass B: Topographic Multi-Scale Frangi Vesselness & +-600m Cross-Fault Block Dipole ---
    with rasterio.open(features_tif) as fsrc:
        b12 = DD._clean_band_edt(fsrc.read(12), footprint)
        b19 = np.maximum(DD._clean_band_edt(fsrc.read(19), footprint), 0.0)

    log_slope = np.log1p(b19).astype(np.float32)
    del b19
    frangi_topo_s1p5 = _frangi_ridge_2d(log_slope, footprint, sigma=1.5)
    frangi_topo_s4p0, ny_r, nx_r = _frangi_ridge_2d(log_slope, footprint, sigma=4.0, return_normal=True)
    del log_slope

    # Sample detrended elevation (B12) and basement depth (B15) at +-6 px (+-600 m) across ridge normal
    coords_plus = np.array([
        np.clip(yy_base + 6.0 * ny_r, 0.0, h - 1.0),
        np.clip(xx_base + 6.0 * nx_r, 0.0, w - 1.0),
    ])
    coords_minus = np.array([
        np.clip(yy_base - 6.0 * ny_r, 0.0, h - 1.0),
        np.clip(xx_base - 6.0 * nx_r, 0.0, w - 1.0),
    ])
    del yy_base, xx_base, ny_r, nx_r

    b12_step = np.abs(
        ndi.map_coordinates(b12, coords_plus, order=1, mode="nearest")
        - ndi.map_coordinates(b12, coords_minus, order=1, mode="nearest")
    ).astype(np.float32)
    b15_step = np.abs(
        ndi.map_coordinates(b15, coords_plus, order=1, mode="nearest")
        - ndi.map_coordinates(b15, coords_minus, order=1, mode="nearest")
    ).astype(np.float32)
    del coords_plus, coords_minus, b12, b15

    crossfault_dipole = (
        0.55 * np.maximum(DD._robust_z(b12_step, footprint), -2.0)
        + 0.45 * np.maximum(DD._robust_z(b15_step, footprint), -2.0)
    ).astype(np.float32)
    del b12_step, b15_step

    mm[:, 7] = frangi_topo_s1p5[footprint]
    mm[:, 8] = frangi_topo_s4p0[footprint]
    mm[:, 11] = crossfault_dipole[footprint]
    del frangi_topo_s1p5, frangi_topo_s4p0, crossfault_dipole
    gc.collect()

    # --- Pass C: Group B (Seismicity Swarm B10/B16, Strain Tensor B04/B07/B08, Alteration B06/B17) ---
    with rasterio.open(features_tif) as fsrc:
        b4 = np.maximum(DD._clean_band_edt(fsrc.read(4), footprint), 0.0)
        b6 = DD._clean_band_edt(fsrc.read(6), footprint)
        b7 = np.maximum(DD._clean_band_edt(fsrc.read(7), footprint), 0.0)
        b8 = DD._clean_band_edt(fsrc.read(8), footprint)
        b10 = np.maximum(DD._clean_band_edt(fsrc.read(10), footprint), 0.0)
        b16 = np.maximum(DD._clean_band_edt(fsrc.read(16), footprint), 0.0)
        b17 = DD._clean_band_edt(fsrc.read(17), footprint)

    seis_dep_log = np.log1p(b10).astype(np.float32)
    seis_ind_log = np.log1p(b16).astype(np.float32)
    seis_swarm_excess = (seis_dep_log - seis_ind_log).astype(np.float32)
    seis_swarm_grad = DD._grad_mag(seis_dep_log, sigma=3.0)
    del b10, b16

    kinematic_w = (b8 / np.sqrt(b8 * b8 + 4.0 * b7 * b7 + 1e-4)).astype(np.float32)
    tensor_excess = (b4 - np.sqrt(0.5 * b8 * b8 + 2.0 * b7 * b7)).astype(np.float32)
    transtens_work = np.log1p(b7 * np.maximum(b8 + 5.0, 0.0)).astype(np.float32)
    del b4, b7, b8

    shallow_trough = (ndi.gaussian_filter(shallow_diff, sigma=8.0) - ndi.gaussian_filter(shallow_diff, sigma=1.5)).astype(np.float32)
    del shallow_diff
    cond_edge = DD._grad_mag(b17, sigma=1.5)
    rad_edge = DD._grad_mag(b6, sigma=1.5)
    del b6, b17
    hydro_demag_joint = (
        np.maximum(DD._robust_z(shallow_trough, footprint), 0.0)
        * np.maximum(DD._robust_z(cond_edge, footprint) + 0.5 * DD._robust_z(rad_edge, footprint), 0.0)
    ).astype(np.float32)
    del shallow_trough, cond_edge, rad_edge

    mm[:, 12] = seis_dep_log[footprint]
    mm[:, 13] = seis_ind_log[footprint]
    mm[:, 14] = seis_swarm_excess[footprint]
    mm[:, 15] = seis_swarm_grad[footprint]
    mm[:, 16] = kinematic_w[footprint]
    mm[:, 17] = tensor_excess[footprint]
    mm[:, 18] = transtens_work[footprint]
    mm[:, 19] = hydro_demag_joint[footprint]
    del seis_dep_log, seis_ind_log, seis_swarm_excess, seis_swarm_grad
    del kinematic_w, tensor_excess, transtens_work, hydro_demag_joint
    mm.flush()
    gc.collect()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": S12_SPAC_STATIC_FEATURE_NAMES,
        "licence_clean_100pct": True,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S12_SPAC_STATIC_FEATURE_NAMES), meta


def _shift_2d(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Fast edge-clamped 2-D integer pixel shift with zero wrap-around."""
    h, w = arr.shape
    src_y = np.clip(np.arange(h) + dy, 0, h - 1)
    src_x = np.clip(np.arange(w) + dx, 0, w - 1)
    return arr[np.ix_(src_y, src_x)]


def compute_spac_autocontext_features(
    stage1_surface: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Extract 10 directional Steerable Radon Auto-Context & Two-Sided Collinear
    Wash-Bridge features `(N_fp, 10)` strictly from an out-of-sample Stage-1
    probability surface `stage1_surface` (`(H, W)` float32).

    Evaluates 8 strike azimuths (every 22.5 deg) at +/-500 m (`near`) and
    +/-1.0 km (`far` = 2.0 km total span), plus +/-400 m cross-strike flanks:
      - `ac_wash_bridge_1km` / `ac_wash_bridge_2km` use the geometric mean
        `sqrt(R_+ * R_-)` of forward and backward collinear rays so confidence
        bridges eroded alluvial washes ONLY when fault segments align on BOTH sides,
        while staying near zero on isolated circular blobs or one-sided gullies.
    """
    p1 = np.clip(np.nan_to_num(stage1_surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    p_ray = ndi.gaussian_filter(p1, sigma=0.85).astype(np.float32)
    p_sm2 = ndi.gaussian_filter(p1, sigma=2.0).astype(np.float32)
    p_c12 = ndi.gaussian_filter(p1, sigma=12.0).astype(np.float32)
    p_c30 = ndi.gaussian_filter(p1, sigma=30.0).astype(np.float32)

    h, w = p1.shape
    max_near = np.zeros((h, w), dtype=np.float32)
    max_far = np.zeros((h, w), dtype=np.float32)
    max_bridge_1k = np.zeros((h, w), dtype=np.float32)
    max_bridge_2k = np.zeros((h, w), dtype=np.float32)
    max_sharp = np.full((h, w), -1.0, dtype=np.float32)
    sum_far = np.zeros((h, w), dtype=np.float32)
    sum_sq_far = np.zeros((h, w), dtype=np.float32)

    near_radii = (2, 3, 5)
    far_radii = (4, 7, 10)
    perp_radii = (3, 5)

    for k in range(8):
        az = math.radians(k * 22.5)
        sy, sx = -math.cos(az), math.sin(az)
        ny, nx = sx, -sy

        r_pos_near = np.zeros((h, w), dtype=np.float32)
        r_neg_near = np.zeros((h, w), dtype=np.float32)
        for r in near_radii:
            dy, dx = int(round(r * sy)), int(round(r * sx))
            r_pos_near += _shift_2d(p_ray, dy, dx)
            r_neg_near += _shift_2d(p_ray, -dy, -dx)
        r_pos_near /= float(len(near_radii))
        r_neg_near /= float(len(near_radii))

        r_pos_far = np.zeros((h, w), dtype=np.float32)
        r_neg_far = np.zeros((h, w), dtype=np.float32)
        for r in far_radii:
            dy, dx = int(round(r * sy)), int(round(r * sx))
            r_pos_far += _shift_2d(p_ray, dy, dx)
            r_neg_far += _shift_2d(p_ray, -dy, -dx)
        r_pos_far /= float(len(far_radii))
        r_neg_far /= float(len(far_radii))

        c_perp = np.zeros((h, w), dtype=np.float32)
        for r in perp_radii:
            dy, dx = int(round(r * ny)), int(round(r * nx))
            c_perp += _shift_2d(p_ray, dy, dx) + _shift_2d(p_ray, -dy, -dx)
        c_perp /= float(2 * len(perp_radii))

        mean_near = 0.5 * (r_pos_near + r_neg_near)
        mean_far = 0.5 * (r_pos_far + r_neg_far)
        br_1k = np.sqrt(np.maximum(r_pos_near * r_neg_near, 0.0))
        br_2k = np.sqrt(np.maximum(r_pos_far * r_neg_far, 0.0))
        sharp = mean_near - c_perp

        np.maximum(max_near, mean_near, out=max_near)
        np.maximum(max_far, mean_far, out=max_far)
        np.maximum(max_bridge_1k, br_1k, out=max_bridge_1k)
        np.maximum(max_bridge_2k, br_2k, out=max_bridge_2k)
        np.maximum(max_sharp, sharp, out=max_sharp)
        sum_far += mean_far
        sum_sq_far += mean_far * mean_far

    avg_far = sum_far / 8.0
    var_far = np.maximum(sum_sq_far / 8.0 - avg_far * avg_far, 0.0)
    aniso = ((max_far - avg_far) / (np.sqrt(var_far) + 1e-4)).astype(np.float32)

    n_fp = int(footprint.sum())
    out = np.empty((n_fp, len(S12_AUTOCONTEXT_FEATURE_NAMES)), dtype=np.float32)
    cols = (
        p1,
        p_sm2,
        max_near,
        max_far,
        max_bridge_1k,
        max_bridge_2k,
        max_sharp,
        aniso,
        p_c12,
        p_c30,
    )
    for j, g in enumerate(cols):
        out[:, j] = g[footprint]
    return out


def compute_spac_regime_fields(
    X_static: np.memmap | np.ndarray,
    X_s11: np.memmap | np.ndarray,
    X_s12: np.memmap | np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute label-free structural edge fields and regime masks across the footprint:
      1. `mhtr_edge`: Marussi-Hessian + Band 06 Radiometric TC + Tectonic Hinge edge (`[0, 1]`)
      2. `spi_swarm_edge`: Dimensionally-exact Thurston-Smith `SPI` wavenumber +
         Shallow GeoDAWN `B14-B01` gradient + Frangi 3-D Analytic Signal vesselness +
         Walker Lane swarm/transtensional conduit edge (`[0, 1]`)
      3. `piedmont_mask`: Concealed alluvial basin / piedmont regime (`slope < 6.2 deg`
         or `depth > 220 m` with `slope < 10.5 deg`)
      4. `spi_volcanic_mask`: Shallow volcanic / transtensional / bedrock contact regime
         (`slope < 11.5 deg` and moderate/shallow cover `depth < 650 m`)
    """
    mhtr_edge, piedmont_mask = MC.compute_mhtr_structural_edge_field(X_s11, X_static, footprint)

    def _norm01(v: np.ndarray) -> np.ndarray:
        q50 = float(np.percentile(v[::20], 50))
        q95 = float(np.percentile(v[::20], 95))
        return np.clip((v - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    up_spi = np.asarray(X_s12[:, 3], dtype=np.float32)
    sh_grd = np.asarray(X_s12[:, 5], dtype=np.float32)
    fr_asg = np.asarray(X_s12[:, 9], dtype=np.float32)
    fr_mar = np.asarray(X_s12[:, 10], dtype=np.float32)
    cf_dip = np.asarray(X_s12[:, 11], dtype=np.float32)
    sw_dep = np.asarray(X_s12[:, 12], dtype=np.float32)
    sw_grd = np.asarray(X_s12[:, 15], dtype=np.float32)
    tt_wrk = np.asarray(X_s12[:, 18], dtype=np.float32)
    hy_dmg = np.asarray(X_s12[:, 19], dtype=np.float32)

    depth_b = np.asarray(X_static[:, 14], dtype=np.float32)
    slope_b = np.asarray(X_static[:, 18], dtype=np.float32)

    s_spi_mag = 0.38 * _norm01(up_spi) + 0.34 * _norm01(sh_grd) + 0.28 * _norm01(fr_asg)
    s_struct = 0.45 * _norm01(fr_mar) + 0.35 * _norm01(cf_dip) + 0.20 * _norm01(hy_dmg)
    s_swarm = 0.40 * _norm01(sw_dep) + 0.30 * _norm01(sw_grd) + 0.30 * _norm01(tt_wrk)

    spi_fp = np.clip(0.46 * s_spi_mag + 0.32 * s_struct + 0.22 * s_swarm, 0.0, 1.0)
    spi_swarm_edge = np.zeros(footprint.shape, dtype=np.float32)
    spi_swarm_edge[footprint] = spi_fp

    volc_fp = (slope_b < 11.5) & (depth_b < 650.0) & (spi_fp >= 0.22)
    spi_volc_mask = np.zeros(footprint.shape, dtype=bool)
    spi_volc_mask[footprint] = volc_fp

    return mhtr_edge, spi_swarm_edge, piedmont_mask, spi_volc_mask


def fit_and_predict_spac_stage(
    feature_blocks: list[tuple[np.memmap | np.ndarray, list[int]]],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    seed: int = 120,
    neg_pos_ratio: float = 3.65,
    dual_hgb: bool = True,
) -> np.ndarray:
    """Train a prior-invariant (`neg_pos_ratio = 3.65 : 1`) regularized multi-model
    ensemble (`HistGB-deep` + `HistGB-shallow` + `L2-LogisticRegression`) strictly
    on `visible_faults` vs flank-buffered (`> 3.5 px`) negatives outside `exclude_mask`.

    Fixing `neg_pos_ratio` guarantees identical class-prior calibration across
    2-quadrant inner sub-folds, 3-quadrant holdout folds, and 4-quadrant full fits
    (`IR-91-S12-04`).
    """
    rng = np.random.default_rng(seed)
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis_grid = ndi.distance_transform_edt(~visible_faults)
    safe_neg_fp = (~vis_fp) & (~excl_fp) & (d_vis_grid[footprint] > 3.5)

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    if pos_idx.size == 0:
        raise ValueError("zero positive training pixels inside active training domain")

    neg_pool = np.flatnonzero(safe_neg_fp)
    target_neg = int(round(float(neg_pos_ratio) * float(pos_idx.size)))
    if neg_pool.size > target_neg:
        neg_idx = rng.choice(neg_pool, size=target_neg, replace=False)
        neg_idx.sort()
    else:
        neg_idx = neg_pool

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])

    X_tr = np.hstack([
        np.asarray(arr[train_idx][:, cols], dtype=np.float32)
        for arr, cols in feature_blocks
        if len(cols) > 0
    ])

    hgb_a = HistGradientBoostingClassifier(
        learning_rate=0.052,
        max_iter=210,
        max_leaf_nodes=41,
        min_samples_leaf=70,
        l2_regularization=3.2,
        random_state=seed,
    )
    hgb_a.fit(X_tr, y_train)

    hgb_b = None
    if dual_hgb:
        hgb_b = HistGradientBoostingClassifier(
            learning_rate=0.048,
            max_iter=180,
            max_leaf_nodes=23,
            max_depth=6,
            min_samples_leaf=110,
            l2_regularization=6.5,
            random_state=seed + 17,
        )
        hgb_b.fit(X_tr, y_train)

    scaler = StandardScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr), -6.0, 6.0)
    lr = LogisticRegression(C=0.22, max_iter=300, random_state=seed)
    lr.fit(X_tr_sc, y_train)
    del X_tr, X_tr_sc
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 450_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = np.hstack([
            np.asarray(arr[s:e][:, cols], dtype=np.float32)
            for arr, cols in feature_blocks
            if len(cols) > 0
        ])
        pa = hgb_a.predict_proba(Xc)[:, 1]
        plr = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        if hgb_b is not None:
            pb = hgb_b.predict_proba(Xc)[:, 1]
            pred_fp[s:e] = (0.50 * pa + 0.30 * pb + 0.20 * plr).astype(np.float32)
        else:
            pred_fp[s:e] = (0.78 * pa + 0.22 * plr).astype(np.float32)

    out_grid = np.zeros(footprint.shape, dtype=np.float32)
    out_grid[footprint] = pred_fp
    return out_grid


def spac_three_regime_submodular_emit(
    surface: np.ndarray,
    mhtr_edge_field: np.ndarray,
    spi_swarm_edge_field: np.ndarray,
    piedmont_mask: np.ndarray,
    spi_volc_mask: np.ndarray,
    *,
    wash_bridge_grid: np.ndarray | None = None,
    eligible_mask: np.ndarray,
    n_dots: int,
    gamma: float = 1.22,
    mhtr_weight: float = 0.42,
    spi_weight: float = 0.36,
    bridge_weight: float = 0.30,
    piedmont_quota_frac: float = 0.23,
    spi_quota_frac: float = 0.19,
    prior_ratio: float = 0.052,
    min_spacing_px: float = 2.50,
    pool_multiplier: int = 8,
) -> np.ndarray:
    """Three-Regime Source-Parameter, Auto-Context & Marussi Submodular 300 m DTI Allocator:
      1. Regime 1 (`1 - piedmont_quota_frac - spi_quota_frac` ~ 58% of budget):
         Core Multi-Physics & Collinear Auto-Context Fault Ridges (`>= min_spacing_px`).
      2. Regime 2 (`piedmont_quota_frac` ~ 23% of budget, `> 3.25 px` from Regime 1):
         Concealed Piedmont & Sub-Alluvial Wash-Bridge Marussi/Radiometric Ridges.
      3. Regime 3 (`spi_quota_frac` ~ 19% of budget, `> 3.25 px` from Regimes 1 & 2):
         Shallow GeoDAWN Magnetic `SPI` Wavenumber, Remanent Volcanic, & Walker Lane
         Transtensional Swarm Fault Ridges.
    """
    h, w = surface.shape
    if n_dots <= 0:
        return np.zeros((h, w), dtype=np.float32)

    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 0.9999).astype(np.float32)
    e_mhtr = np.clip(np.nan_to_num(mhtr_edge_field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    e_spi = np.clip(np.nan_to_num(spi_swarm_edge_field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)

    if wash_bridge_grid is not None:
        wb = np.clip(np.nan_to_num(wash_bridge_grid, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    else:
        wb = np.zeros((h, w), dtype=np.float32)

    q_base = ((prior_ratio * p) / (prior_ratio * p + (1.0 - p) + 1e-8)).astype(np.float32)
    boost = 1.0 + float(mhtr_weight) * e_mhtr + float(spi_weight) * e_spi + float(bridge_weight) * wb
    q = (q_base * boost).astype(np.float32)

    # 1-D directional ridge detectors
    qp = np.pad(q, 2, mode="edge")
    c = qp[2 : h + 2, 2 : w + 2]
    is_q_ridge = (
        ((c >= qp[1 : h + 1, 2 : w + 2]) & (c >= qp[3 : h + 3, 2 : w + 2]) & (c >= qp[0:h, 2 : w + 2]) & (c >= qp[4 : h + 4, 2 : w + 2]))
        | ((c >= qp[2 : h + 2, 1 : w + 1]) & (c >= qp[2 : h + 2, 3 : w + 3]) & (c >= qp[2 : h + 2, 0:w]) & (c >= qp[2 : h + 2, 4 : w + 4]))
        | ((c >= qp[1 : h + 1, 1 : w + 1]) & (c >= qp[3 : h + 3, 3 : w + 3]) & (c >= qp[0:h, 0:w]) & (c >= qp[4 : h + 4, 4 : w + 4]))
        | ((c >= qp[1 : h + 1, 3 : w + 3]) & (c >= qp[3 : h + 3, 1 : w + 1]) & (c >= qp[0:h, 4 : w + 4]) & (c >= qp[4 : h + 4, 0:w]))
    )

    ep = np.pad(e_mhtr, 1, mode="edge")
    ec = ep[1 : h + 1, 1 : w + 1]
    is_mhtr_ridge = (
        ((ec >= ep[0:h, 1 : w + 1]) & (ec >= ep[2 : h + 2, 1 : w + 1]))
        | ((ec >= ep[1 : h + 1, 0:w]) & (ec >= ep[1 : h + 1, 2 : w + 2]))
        | ((ec >= ep[0:h, 0:w]) & (ec >= ep[2 : h + 2, 2 : w + 2]))
        | ((ec >= ep[0:h, 2 : w + 2]) & (ec >= ep[2 : h + 2, 0:w]))
    )

    sp = np.pad(e_spi, 1, mode="edge")
    sc = sp[1 : h + 1, 1 : w + 1]
    is_spi_ridge = (
        ((sc >= sp[0:h, 1 : w + 1]) & (sc >= sp[2 : h + 2, 1 : w + 1]))
        | ((sc >= sp[1 : h + 1, 0:w]) & (sc >= sp[1 : h + 1, 2 : w + 2]))
        | ((sc >= sp[0:h, 0:w]) & (sc >= sp[2 : h + 2, 2 : w + 2]))
        | ((sc >= sp[0:h, 2 : w + 2]) & (sc >= sp[2 : h + 2, 0:w]))
    )

    elig_pos_q = q[eligible_mask & (q > 0)]
    if elig_pos_q.size == 0:
        return np.zeros((h, w), dtype=np.float32)

    if elig_pos_q.size > n_dots * 15:
        keep_frac = min(0.32, max(float(n_dots * 16) / float(elig_pos_q.size), 0.06))
        q_floor = float(np.quantile(elig_pos_q, 1.0 - keep_frac))
    else:
        q_floor = 0.0

    q_excess = np.maximum(q - q_floor, 0.0)
    ridge_mult_1 = np.where(is_q_ridge, 1.0, 0.25).astype(np.float32)
    w_primary = np.where(
        eligible_mask,
        1000.0 * (q_excess ** float(gamma)) * ridge_mult_1,
        0.0,
    ).astype(np.float32)

    n_piedmont = int(round(n_dots * float(piedmont_quota_frac)))
    n_spi = int(round(n_dots * float(spi_quota_frac)))
    n_primary = max(0, n_dots - n_piedmont - n_spi)

    dots_s1 = MC._submodular_select_on_weight(
        w_primary,
        q * np.where(is_q_ridge, 1.15, 0.85),
        eligible_mask,
        n_primary,
        min_spacing_px=min_spacing_px,
        pool_multiplier=pool_multiplier,
        existing_dots=None,
    )

    oy3, ox3 = np.mgrid[-4:5, -4:5]
    disk_3p25 = np.hypot(oy3, ox3) <= 3.25

    dots_s2 = dots_s1
    if n_piedmont > 0:
        near_s1 = ndi.binary_dilation(dots_s1 > 0, structure=disk_3p25)
        pied_elig = eligible_mask & piedmont_mask & (~near_s1) & ((e_mhtr >= 0.19) | (wb >= 0.18))
        ridge_mult_2 = np.where(is_mhtr_ridge | is_q_ridge, 1.12, 0.24).astype(np.float32)
        pied_signal = (0.20 + e_mhtr + 0.55 * wb) ** 1.08
        w_piedmont = np.where(
            pied_elig,
            1000.0 * (q_excess ** float(gamma * 0.84)) * pied_signal * ridge_mult_2,
            0.0,
        ).astype(np.float32)
        dots_s2 = MC._submodular_select_on_weight(
            w_piedmont,
            (q_excess ** 0.80) * pied_signal * ridge_mult_2,
            pied_elig,
            n_piedmont,
            min_spacing_px=min_spacing_px + 0.22,
            pool_multiplier=pool_multiplier,
            existing_dots=dots_s1,
        )

    dots_s3 = dots_s2
    if n_spi > 0:
        near_s2 = ndi.binary_dilation(dots_s2 > 0, structure=disk_3p25)
        spi_elig = eligible_mask & spi_volc_mask & (~near_s2) & (e_spi >= 0.22)
        ridge_mult_3 = np.where(is_spi_ridge | is_q_ridge, 1.15, 0.24).astype(np.float32)
        spi_signal = (0.20 + e_spi + 0.35 * wb) ** 1.12
        w_spi = np.where(
            spi_elig,
            1000.0 * (q_excess ** float(gamma * 0.82)) * spi_signal * ridge_mult_3,
            0.0,
        ).astype(np.float32)
        dots_s3 = MC._submodular_select_on_weight(
            w_spi,
            (q_excess ** 0.78) * spi_signal * ridge_mult_3,
            spi_elig,
            n_spi,
            min_spacing_px=min_spacing_px + 0.25,
            pool_multiplier=pool_multiplier,
            existing_dots=dots_s2,
        )

    # Top up any unallocated shortfall (if a sub-regime had fewer eligible peaks) on primary eligible domain
    emitted_so_far = int((dots_s3 > 0).sum())
    if emitted_so_far < n_dots:
        near_s3 = ndi.binary_dilation(dots_s3 > 0, structure=np.hypot(oy3, ox3) < min_spacing_px)
        rem_elig = eligible_mask & (~near_s3)
        dots_s3 = MC._submodular_select_on_weight(
            w_primary,
            q * np.where(is_q_ridge, 1.15, 0.85),
            rem_elig,
            n_dots - emitted_so_far,
            min_spacing_px=min_spacing_px,
            pool_multiplier=pool_multiplier,
            existing_dots=dots_s3,
        )

    return dots_s3
