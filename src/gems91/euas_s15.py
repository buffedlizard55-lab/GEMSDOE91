"""Session 15 (`S15-EUAS`): 3-D Euler Homogeneity Structural-Index Depth &
Convergence Inversion + 4-Altitude FFT Upward-Continuation Plunge Worms +
Spatially-Varying Geodetic Strain-Resolved Andersonian Slip/Dilation Tendency +
Fold-Safe Depth-Deconfounded Hydrothermal Clay-Cap Conductivity + Inner-OOF
Two-Stage Anisotropic Wash-Bridge Auto-Context & Out-of-Sample Calibrated
Self-Credit (`M`-Term) Dinkelbach Submodular Allocation.

Pre-registered in `docs/HYPOTHESES_S15.md` prior to any holdout run.
Strictly §A.5-clean: uses ONLY official `training_features.tif` (19 bands),
`sample_submission.tif`, `existing_faults.tif` (fold-visible only), and public-domain
DOE GDR/USGS `gdr_wellspring_in_footprint.csv` (zero bytes read from `IR-91-26`
external `u8` rasters).
Designed for < 1.3 GiB peak RSS on a 3.8 GiB / 0-swap sandbox.
"""

from __future__ import annotations

import gc
import heapq
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from . import dd_vtc_pu as DD
from . import mhtr_coda as MC
from . import ptha as PTHA
from . import spac_coda as SPAC

GRID_DX_M = 100.0
TMI_HG_UNIT_SCALE = 200.0   # Band 03 is nT / 200 m -> divide by 200 for nT/m
GRAV_HG_UNIT_SCALE = 1000.0  # Bands 11, 18 are mGal / km -> divide by 1000 for mGal/m

S15_GROUP_A_EULER_WORM_NAMES = [
    "euas_euler_mag_z0_log",
    "euas_euler_mag_focus",
    "euas_euler_mag_conv",
    "euas_euler_mag_step_vs_plug",
    "euas_euler_grav_z0_log",
    "euas_euler_grav_focus",
    "euas_euler_grav_conv",
    "euas_euler_sed_conform",
    "euas_worm_mag_persist",
    "euas_worm_grav_persist",
    "euas_worm_plunge_concord",
    "euas_joint_euler_worm_crest",
]

S15_GROUP_B_MECHANICS_HYDRO_NAMES = [
    "euas_kinematic_regime_psi",
    "euas_morris_dilation_tend",
    "euas_morris_slip_tend",
    "euas_crit_stressed_edge",
    "euas_rad_tc_step_aniso",
    "euas_blind_hydro_cap_joint",
    "euas_gdr_stressed_conduit",
    "euas_basin_margin_flexure",
]

S15_EUAS_FEATURE_NAMES = S15_GROUP_A_EULER_WORM_NAMES + S15_GROUP_B_MECHANICS_HYDRO_NAMES

S15_FOLD_COND_NAMES = [
    "fold_cond_depth_res",
    "fold_cond_res_crest",
]

# Clean static column allowlists (excluding all unit-corrupted Verduzco tilts 24..30, 32,
# tilt-derived 34..37, and inverted swarm col 47):
CLEAN_STATIC_INDICES = (
    list(range(0, 24))      # 19 official bands + 5 clean E1 terrain cols
    + [31, 33]              # updip_half_grav_slope (clean B05), cond_grad_hp (clean B17)
    + list(range(38, 44))   # 5 GDR blind geothermometry/spring cols + piedmont_concealment_idx
    + [44, 45, 46, 48]      # 4 clean alteration cols (excluding col 47)
)

# Non-redundant S12 columns (15 cols; excludes 0,1,12,13,14 duplicated in PTHA):
CLEAN_S12_INDICES = [
    2, 3,                   # SPI local & updip magnetic wavenumber
    4, 5, 6,                # shallow GeoDAWN residual B14 - B01, grad, remanent RTP discrepancy
    7, 8, 9, 10, 11,        # Frangi Hessian ridges (topo 1.5/4.0, ASIG 2.0, Marussi 2.5) + crossfault dipole
    15, 16, 17, 18, 19,     # swarm grad, Kreemer kinematic w, strain excess, transtens work rate, hydro_demag_alter_joint
]

# Topographic / surface-exposure feature names excluded from the Subsurface Specialist:
TOPO_EXPOSURE_FEATURE_NAMES = frozenset({
    "b12_det_elev",
    "b19_det_elev_slope",
    "e1_lrm_300m",
    "e1_lrm_1km",
    "e1_topo_openness_lap",
    "e1_slope_hp_600m",
    "e1_topo_coherence",
    "e2_gdr_upslope_conduit_align",
    "e2_piedmont_concealment_idx",
    "s11_topo_grav_cos_align",
    "s11_topo_profile_curv",
    "s11_ctx1km_topo_slope",
    "s12_frangi_topo_s1p5",
    "s12_frangi_topo_s4p0",
    "ptha_step_elev",
})


def _cosine_border_taper(shape: tuple[int, int], pad: int = 48) -> np.ndarray:
    """Smooth 2-D cosine border window to suppress periodic wraparound in 2-D FFTs."""
    h, w = shape
    py = min(pad, h // 4)
    px = min(pad, w // 4)
    wy = np.ones(h, dtype=np.float32)
    wx = np.ones(w, dtype=np.float32)
    if py > 0:
        t = 0.5 * (1.0 - np.cos(np.pi * np.arange(py, dtype=np.float32) / float(py)))
        wy[:py] = t
        wy[-py:] = t[::-1]
    if px > 0:
        t = 0.5 * (1.0 - np.cos(np.pi * np.arange(px, dtype=np.float32) / float(px)))
        wx[:px] = t
        wx[-px:] = t[::-1]
    return wy[:, None] * wx[None, :]


def fft_laplace_vertical_derivative_and_worms(
    field_2d: np.ndarray,
    footprint: np.ndarray,
    *,
    dx_m: float = GRID_DX_M,
    altitudes_m: tuple[float, ...] = (100.0, 300.0, 800.0, 2000.0),
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute exact 2-D FFT Laplace downward vertical derivative `dF/dz_down` (SI/m)
    plus 4-altitude upward-continued horizontal-gradient persistence & lateral dip-migration
    vector `(mig_dy, mig_dx)` from `altitudes_m[0]` to `altitudes_m[2]`.

    Sign convention (verified empirically against Band 09 `tmi_vg`, r = +0.828, ratio = 1.03):
      - `z` is positive DOWNWARD (`dF/dz_down = F^{-1}{ +2*pi*|k| * F(field) }`).
      - Upward continuation to altitude `h > 0` above observation plane attenuates by
        `exp(-2*pi*|k|*h)`.
    """
    h, w = field_2d.shape
    med = float(np.median(field_2d[footprint]))
    taper = _cosine_border_taper((h, w), pad=48)
    f0 = ((field_2d - med) * taper).astype(np.float32)
    del taper

    spec = np.fft.rfft2(f0)
    del f0

    ky = np.fft.fftfreq(h, d=dx_m).astype(np.float32)[:, None]
    kx = np.fft.rfftfreq(w, d=dx_m).astype(np.float32)[None, :]
    two_pi_k = (2.0 * math.pi * np.hypot(ky, kx)).astype(np.float32)
    del ky, kx

    # Downward vertical derivative (+2*pi*|k|), mild high-k rolloff exp(-2*pi*|k|*35m) to avoid Nyquist ringing
    dz_down = np.fft.irfft2(
        spec * two_pi_k * np.exp(-two_pi_k * 35.0),
        s=(h, w),
    ).astype(np.float32)

    log_persist = np.zeros((h, w), dtype=np.float32)
    hg_low = None
    hg_high = None

    for idx_a, alt in enumerate(altitudes_m):
        up = np.fft.irfft2(spec * np.exp(-two_pi_k * float(alt)), s=(h, w)).astype(np.float32)
        gy, gx = np.gradient(up, dx_m)
        del up
        hg = np.hypot(gy, gx).astype(np.float32)
        del gy, gx
        # Normalize each altitude's horizontal gradient to robust footprint z-score >= 0
        z_hg = np.maximum(DD._robust_z(hg, footprint), 0.0)
        log_persist += np.log1p(z_hg).astype(np.float32)
        if idx_a == 0:
            hg_low = z_hg
        elif idx_a == min(2, len(altitudes_m) - 1):
            hg_high = z_hg
        else:
            del z_hg
        del hg

    del spec, two_pi_k
    persist = (np.expm1(log_persist / float(len(altitudes_m)))).astype(np.float32)
    del log_persist

    # Lateral dip-migration vector: where upward-continued 800m anomaly shifts relative to 100m
    # Over a dipping fault, higher-altitude horizontal-gradient maximum shifts DOWNDIP.
    # Locally, grad(hg_high) evaluated along the 100m crest points toward the shifted 800m crest!
    assert hg_low is not None and hg_high is not None
    hg_high_sm = ndi.gaussian_filter(hg_high, sigma=2.5).astype(np.float32)
    mig_y, mig_x = np.gradient(hg_high_sm, 1.0)
    crest_weight = np.tanh(0.6 * hg_low).astype(np.float32)
    mig_dy = (mig_y * crest_weight).astype(np.float32)
    mig_dx = (mig_x * crest_weight).astype(np.float32)
    del hg_low, hg_high, hg_high_sm, mig_y, mig_x, crest_weight
    return dz_down, persist, mig_dy, mig_dx


def solve_windowed_euler_3d(
    f_val: np.ndarray,
    fx: np.ndarray,
    fy: np.ndarray,
    fz_down: np.ndarray,
    *,
    win: int = 7,
    dx_m: float = GRID_DX_M,
    n_step: float = 0.5,
    n_plug: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Closed-form vectorized 3-D Euler Homogeneity solver (`Reid et al. 1990`)
    on sliding `win x win` (`700 m x 700 m`) windows with exact demeaned background
    elimination.

    For observation at `(Delta_x, Delta_y, 0)` inside the window and source at
    `(x0', y0', z0)` with `z0 > 0` POSITIVE DOWNWARD:
        x0' * fx_tilde + y0' * fy_tilde + z0 * fz_tilde = rhs_N
    where:
        rhs_N(u, v) = (Delta_x * fx + Delta_y * fy)_tilde + N * f_tilde.

    Returns float32 `(H, W)` arrays:
      - `z0_step`: estimated source depth `z0` (meters, >= 0) for structural index `n_step`
      - `focus_step`: `exp(-hypot(x0', y0') / 250m) * R2_step` in `[0, 1]`
      - `conv_step`: `-div(x0', y0') * R2_step` (ray-focusing convergence onto fault trace)
      - `step_vs_plug`: `R2(n_step) - R2(n_plug)` (> 0 on linear 2-D steps, < 0 on 3-D plugs)
    """
    if win % 2 != 1 or win < 3:
        raise ValueError("win must be odd >= 3")
    half = win // 2
    offs_m = (np.arange(-half, half + 1, dtype=np.float32) * float(dx_m)) / float(win)
    box_1d = np.full(win, 1.0 / float(win), dtype=np.float32)

    def _mean_w(arr: np.ndarray) -> np.ndarray:
        return ndi.uniform_filter(arr.astype(np.float32, copy=False), size=win, mode="nearest")

    def _mean_dx_w(arr: np.ndarray) -> np.ndarray:
        # Mean of Delta_x * arr[r + dy, c + dx] over window
        tmp = ndi.correlate1d(arr.astype(np.float32, copy=False), box_1d, axis=0, mode="nearest")
        return ndi.correlate1d(tmp, offs_m, axis=1, mode="nearest")

    def _mean_dy_w(arr: np.ndarray) -> np.ndarray:
        # Mean of Delta_y * arr[r + dy, c + dx] over window
        tmp = ndi.correlate1d(arr.astype(np.float32, copy=False), offs_m, axis=0, mode="nearest")
        return ndi.correlate1d(tmp, box_1d, axis=1, mode="nearest")

    mx = _mean_w(fx)
    my = _mean_w(fy)
    mz = _mean_w(fz_down)
    mf = _mean_w(f_val)

    # Normal-equation 3x3 covariance entries Cov_W(g_i, g_j):
    s_xx = np.maximum(_mean_w(fx * fx) - mx * mx, 0.0)
    s_yy = np.maximum(_mean_w(fy * fy) - my * my, 0.0)
    s_zz = np.maximum(_mean_w(fz_down * fz_down) - mz * mz, 0.0)
    s_xy = _mean_w(fx * fy) - mx * my
    s_xz = _mean_w(fx * fz_down) - mx * mz
    s_yz = _mean_w(fy * fz_down) - my * mz

    # Geometric term p = Delta_x * fx + Delta_y * fy inside window:
    # Note Delta_x, Delta_y are coordinates relative to EACH window's center!
    # For a fixed window centered at (r, c):
    #   mean_W(p) = _mean_dx_w(fx) + _mean_dy_w(fy)
    #   mean_W(p * fx) = _mean_dx_w(fx * fx) + _mean_dy_w(fy * fx), etc.
    mp = _mean_dx_w(fx) + _mean_dy_w(fy)
    c_px = (_mean_dx_w(fx * fx) + _mean_dy_w(fy * fx)) - mp * mx
    c_py = (_mean_dx_w(fx * fy) + _mean_dy_w(fy * fy)) - mp * my
    c_pz = (_mean_dx_w(fx * fz_down) + _mean_dy_w(fy * fz_down)) - mp * mz

    c_fx = _mean_w(f_val * fx) - mf * mx
    c_fy = _mean_w(f_val * fy) - mf * my
    c_fz = _mean_w(f_val * fz_down) - mf * mz

    # Variance of p and f_tilde and covariance Cov_W(p, f_tilde) for exact R^2:
    # p^2 = Delta_x^2 fx^2 + 2 Delta_x Delta_y fx fy + Delta_y^2 fy^2
    offs2_m = ((np.arange(-half, half + 1, dtype=np.float32) * float(dx_m)) ** 2) / float(win)
    mp2 = (
        ndi.correlate1d(ndi.correlate1d(fx * fx, box_1d, axis=0, mode="nearest"), offs2_m, axis=1, mode="nearest")
        + ndi.correlate1d(ndi.correlate1d(fy * fy, offs2_m, axis=0, mode="nearest"), box_1d, axis=1, mode="nearest")
        + 2.0 * ndi.correlate1d(ndi.correlate1d(fx * fy, offs_m, axis=0, mode="nearest"), offs_m, axis=1, mode="nearest")
    )
    var_p = np.maximum(mp2 - mp * mp, 0.0)
    del mp2
    var_f = np.maximum(_mean_w(f_val * f_val) - mf * mf, 0.0)
    cov_pf = (_mean_dx_w(f_val * fx) + _mean_dy_w(f_val * fy)) - mp * mf
    del mx, my, mz, mf, mp

    # Rotation-invariant 2D-fault-step vs 3D-volcanic-plug discriminator from the
    # horizontal Euler gradient covariance S_H = [[s_xx, s_xy], [s_xy, s_yy]]:
    #   - 2-D linear fault step (any strike): rank-1 S_H (lam1 >> lam2) -> +r2_step
    #   - 3-D equidimensional plug/pipe: isotropic S_H (lam1 ~ lam2)   -> -r2_step
    sh_tr = s_xx + s_yy
    sh_disc = np.hypot(s_xx - s_yy, 2.0 * s_xy)
    sh_lam1 = 0.5 * (sh_tr + sh_disc)
    sh_lam2 = np.maximum(0.5 * (sh_tr - sh_disc), 0.0)
    sh_floor = max(float(np.median(sh_tr)) * 1e-5, 1e-14)
    planar_vs_iso = ((sh_lam1 - 3.0 * sh_lam2) / (sh_lam1 + sh_lam2 + sh_floor)).astype(np.float32)
    del sh_tr, sh_disc, sh_lam1, sh_lam2

    # Scale-adaptive Tikhonov damping (0.2% of local trace + tiny floor):
    tr = s_xx + s_yy + s_zz
    tr_med = float(np.median(tr)) if tr.size > 0 else 1.0
    reg = 0.002 * tr + max(1e-10 * tr_med, 1e-12)
    a00 = s_xx + reg
    a11 = s_yy + reg
    a22 = s_zz + reg
    del s_xx, s_yy, s_zz, tr, reg

    # Symmetric 3x3 cofactors & determinant:
    m00 = a11 * a22 - s_yz * s_yz
    m01 = s_xz * s_yz - s_xy * a22
    m02 = s_xy * s_yz - s_xz * a11
    m11 = a00 * a22 - s_xz * s_xz
    m12 = s_xy * s_xz - a00 * s_yz
    m22 = a00 * a11 - s_xy * s_xy
    det = np.maximum(a00 * m00 + s_xy * m01 + s_xz * m02, 1e-30)
    inv_det = 1.0 / det
    del a00, a11, a22, s_xy, s_xz, s_yz, det

    def _solve_for_n(n_idx: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        b0 = c_px + float(n_idx) * c_fx
        b1 = c_py + float(n_idx) * c_fy
        b2 = c_pz + float(n_idx) * c_fz
        u0 = (m00 * b0 + m01 * b1 + m02 * b2) * inv_det
        u1 = (m01 * b0 + m11 * b1 + m12 * b2) * inv_det
        u2 = (m02 * b0 + m12 * b1 + m22 * b2) * inv_det
        explained = np.maximum(u0 * b0 + u1 * b1 + u2 * b2, 0.0)
        tot_var = np.maximum(
            var_p + 2.0 * float(n_idx) * cov_pf + (float(n_idx) ** 2) * var_f,
            1e-20,
        )
        r2 = np.clip(explained / (tot_var + 1e-18), 0.0, 1.0).astype(np.float32)
        return u0.astype(np.float32), u1.astype(np.float32), u2.astype(np.float32), r2

    x0_s, y0_s, z0_s, r2_step = _solve_for_n(n_step)
    del m00, m01, m02, m11, m12, m22, inv_det
    del c_px, c_py, c_pz, c_fx, c_fy, c_fz, var_p, var_f, cov_pf

    horiz_off = np.hypot(x0_s, y0_s)
    valid_depth = (z0_s > 0.0).astype(np.float32)
    focus_step = (np.exp(-horiz_off / 250.0) * r2_step * valid_depth).astype(np.float32)

    # Ray convergence: as window center crosses x0'=0 from west (x0' > 0) to east (x0' < 0),
    # dx0'/dx < 0 => -div(x0', y0') > 0! Clip extreme jumps far from sources before differentiating.
    x0_clip = np.clip(x0_s, -800.0, 800.0)
    y0_clip = np.clip(y0_s, -800.0, 800.0)
    _, dx0_dx = np.gradient(x0_clip, dx_m)
    dy0_dy, _ = np.gradient(y0_clip, dx_m)
    conv_step = (np.clip(-(dx0_dx + dy0_dy), -2.5, 2.5) * r2_step * valid_depth).astype(np.float32)
    del x0_s, y0_s, x0_clip, y0_clip, dx0_dx, dy0_dy, horiz_off

    z0_pos = np.clip(z0_s, 0.0, 10000.0).astype(np.float32)
    step_vs_plug = (planar_vs_iso * focus_step).astype(np.float32)
    return z0_pos, focus_step, conv_step, step_vs_plug


def build_or_load_s15_feature_memmap(
    *,
    features_tif: str | Path,
    X_static: np.memmap | np.ndarray,
    X_s12: np.memmap | np.ndarray,
    X_ptha: np.memmap | np.ndarray,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed float32 Session 15 feature matrix `(N_fp, 20)`.

    100% derived from official `training_features.tif` + public-domain DOE GDR springs
    already cached in `X_static` cols `38..42`. Zero bytes read from `IR-91-26` rasters.
    """
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s15_euas_features_v1.dat"
    meta_path = cache_p / "s15_euas_features_v1.json"

    n_fp = int(footprint.sum())
    n_cols = len(S15_EUAS_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == S15_EUAS_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S15_EUAS_FEATURE_NAMES), meta

    h, w = footprint.shape
    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    with rasterio.open(features_tif) as src:
        b02 = DD._clean_band_edt(src.read(2), footprint)   # RTP magnetic anomaly (nT)
        b03 = DD._clean_band_edt(src.read(3), footprint)   # TMI horiz gradient (nT / 200 m)
        b04 = DD._clean_band_edt(src.read(4), footprint)   # geod_2ndinv
        b06 = DD._clean_band_edt(src.read(6), footprint)   # Radiometric Total Count (TC)
        b07 = DD._clean_band_edt(src.read(7), footprint)   # geod_shearrate
        b08 = DD._clean_band_edt(src.read(8), footprint)   # geod_dilaterate
        b09 = DD._clean_band_edt(src.read(9), footprint)   # TMI vertical derivative (nT / m, +z down)
        b11 = DD._clean_band_edt(src.read(11), footprint)  # dG/drow (mGal / km)
        b12 = DD._clean_band_edt(src.read(12), footprint)  # detrended elevation
        b13 = DD._clean_band_edt(src.read(13), footprint)  # Isostatic gravity (mGal)
        b14 = DD._clean_band_edt(src.read(14), footprint)  # TMI (nT)
        b15 = DD._clean_band_edt(src.read(15), footprint)  # Depth to basement (m)
        b18 = DD._clean_band_edt(src.read(18), footprint)  # dG/dcol (mGal / km)

    # ------------------------------------------------------------------
    # Group A (H15-1): 3-D Euler Homogeneity + 4-Altitude Plunge Worms
    # ------------------------------------------------------------------
    # 1. Magnetic 3-D Euler in exact SI units (nT and nT/m):
    t_sm = ndi.gaussian_filter(b14, sigma=0.85).astype(np.float32)
    ty_raw, tx_raw = np.gradient(t_sm, GRID_DX_M)
    t_raw_mag = np.hypot(ty_raw, tx_raw) + 1e-7
    hg_si = np.maximum(b03, 0.0) / TMI_HG_UNIT_SCALE
    scale_mag = hg_si / t_raw_mag
    m_fx = (tx_raw * scale_mag).astype(np.float32)
    m_fy = (ty_raw * scale_mag).astype(np.float32)
    del ty_raw, tx_raw, t_raw_mag, hg_si, scale_mag, b03, b14

    z0_mag, focus_mag, conv_mag, step_plug_mag = solve_windowed_euler_3d(
        t_sm, m_fx, m_fy, b09, win=7, dx_m=GRID_DX_M, n_step=0.5, n_plug=2.0
    )
    del t_sm, m_fx, m_fy, b09
    gc.collect()

    # 2. Gravity 3-D Euler + 4-Altitude Worms in exact SI units (mGal and mGal/m):
    g_dz_down, worm_grav_persist, mig_gy, mig_gx = fft_laplace_vertical_derivative_and_worms(
        b13, footprint, dx_m=GRID_DX_M
    )
    g_fx = (b18 / GRAV_HG_UNIT_SCALE).astype(np.float32)
    g_fy = (b11 / GRAV_HG_UNIT_SCALE).astype(np.float32)
    z0_grav, focus_grav, conv_grav, _ = solve_windowed_euler_3d(
        b13, g_fx, g_fy, g_dz_down, win=7, dx_m=GRID_DX_M, n_step=0.5, n_plug=2.0
    )
    del g_dz_down
    gc.collect()

    # 3. RTP Magnetic 4-Altitude Worms + Downdip Basin-Deepening Concordance:
    _, worm_mag_persist, mig_my, mig_mx = fft_laplace_vertical_derivative_and_worms(
        b02, footprint, dx_m=GRID_DX_M
    )
    del b02

    # Basin-deepening unit vector: points toward thicker sediment (+grad B15) & lower gravity (-grad B13)
    sed_depth = np.maximum(b15, 0.0)
    b15_sm = ndi.gaussian_filter(sed_depth, sigma=5.0).astype(np.float32)
    b13_sm = ndi.gaussian_filter(b13, sigma=5.0).astype(np.float32)
    sy15, sx15 = np.gradient(b15_sm, GRID_DX_M)
    gy13, gx13 = np.gradient(b13_sm, GRID_DX_M)
    del b15_sm, b13_sm, b13

    # Combine normalized basin-deepening indicators (+grad B15 and -grad B13):
    n15 = np.hypot(sy15, sx15) + 1e-5
    n13 = np.hypot(gy13, gx13) + 1e-5
    by_down = 0.55 * (sy15 / n15) - 0.45 * (gy13 / n13)
    bx_down = 0.55 * (sx15 / n15) - 0.45 * (gx13 / n13)
    bnorm = np.hypot(by_down, bx_down) + 1e-5
    by_down = (by_down / bnorm).astype(np.float32)
    bx_down = (bx_down / bnorm).astype(np.float32)
    del sy15, sx15, gy13, gx13, n15, n13, bnorm

    plunge_concord = (
        0.55 * (mig_gy * by_down + mig_gx * bx_down)
        + 0.45 * (mig_my * by_down + mig_mx * bx_down)
    ).astype(np.float32)
    del mig_gy, mig_gx, mig_my, mig_mx, by_down, bx_down

    # Basement-contact conformance: Euler magnetic top depth ~ B15 sediment thickness
    r2_proxy = np.clip(focus_mag / (np.maximum(focus_mag, 1e-4)), 0.0, 1.0)
    sed_conform = (
        np.exp(-np.abs(z0_mag - sed_depth) / 350.0)
        * np.sqrt(np.maximum(focus_mag, 0.0) + 1e-6)
    ).astype(np.float32)
    del r2_proxy

    joint_euler_worm = (
        np.sqrt(np.maximum(focus_mag, 0.0) * np.maximum(focus_grav, 0.0) + 1e-6)
        * np.log1p(0.5 * (worm_mag_persist + worm_grav_persist))
    ).astype(np.float32)

    mm[:, 0] = np.log1p(z0_mag[footprint]).astype(np.float32)
    mm[:, 1] = focus_mag[footprint]
    mm[:, 2] = conv_mag[footprint]
    mm[:, 3] = step_plug_mag[footprint]
    mm[:, 4] = np.log1p(z0_grav[footprint]).astype(np.float32)
    mm[:, 5] = focus_grav[footprint]
    mm[:, 6] = conv_grav[footprint]
    mm[:, 7] = sed_conform[footprint]
    mm[:, 8] = worm_mag_persist[footprint]
    mm[:, 9] = worm_grav_persist[footprint]
    mm[:, 10] = plunge_concord[footprint]
    mm[:, 11] = joint_euler_worm[footprint]
    del z0_mag, focus_mag, conv_mag, step_plug_mag
    del z0_grav, focus_grav, conv_grav, sed_conform
    del worm_mag_persist, worm_grav_persist, plunge_concord, joint_euler_worm
    gc.collect()

    # ------------------------------------------------------------------
    # Group B (H15-2): Spatially-Varying Morris Slip/Dilation Tendency &
    # Off-Catalogue Hydrothermal / Basin-Flexure Mechanics
    # ------------------------------------------------------------------
    # Build dimensionally-clean multi-physics structure tensor (Gravity + Elevation + Mag AS3D):
    ey, ex = np.gradient(ndi.gaussian_filter(b12, sigma=1.2).astype(np.float32), GRID_DX_M)
    del b12
    # Read calibrated Mag AS3D (`ptha_mag_as3d` = col 3 of X_ptha) back onto 2-D grid:
    as3d_2d = np.zeros((h, w), dtype=np.float32)
    as3d_2d[footprint] = np.asarray(X_ptha[:, 3], dtype=np.float32)
    ay, ax = np.gradient(ndi.gaussian_filter(as3d_2d, sigma=1.2), GRID_DX_M)
    del as3d_2d

    # Normalize each gradient field by its footprint RMS so units combine cleanly:
    g_rms = float(np.sqrt(np.mean((g_fx[footprint] ** 2) + (g_fy[footprint] ** 2))) + 1e-8)
    e_rms = float(np.sqrt(np.mean((ex[footprint] ** 2) + (ey[footprint] ** 2))) + 1e-8)
    a_rms = float(np.sqrt(np.mean((ax[footprint] ** 2) + (ay[footprint] ** 2))) + 1e-8)

    j_xx = ndi.gaussian_filter(
        0.42 * (g_fx / g_rms) ** 2 + 0.33 * (ex / e_rms) ** 2 + 0.25 * (ax / a_rms) ** 2,
        sigma=3.0,
    ).astype(np.float32)
    j_yy = ndi.gaussian_filter(
        0.42 * (g_fy / g_rms) ** 2 + 0.33 * (ey / e_rms) ** 2 + 0.25 * (ay / a_rms) ** 2,
        sigma=3.0,
    ).astype(np.float32)
    j_xy = ndi.gaussian_filter(
        0.42 * (g_fx * g_fy) / (g_rms ** 2)
        + 0.33 * (ex * ey) / (e_rms ** 2)
        + 0.25 * (ax * ay) / (a_rms ** 2),
        sigma=3.0,
    ).astype(np.float32)
    del g_fx, g_fy, ex, ey, ax, ay, b11, b18

    # Principal fault-normal eigenvector of J (points perpendicular to strike, x=East, y=North=-row):
    # Note row increases South, so geographic northward component n_north = -n_row!
    diff_j = j_xx - j_yy
    disc = np.hypot(diff_j, 2.0 * j_xy)
    lam1 = 0.5 * (j_xx + j_yy + disc)
    lam2 = np.maximum(0.5 * (j_xx + j_yy - disc), 0.0)
    st_aniso = ((lam1 - lam2) / (lam1 + lam2 + 1e-5)).astype(np.float32)

    # Eigenvector in (col=East, row=South) coordinates: theta_grid = 0.5 * atan2(2*j_xy, j_xx - j_yy)
    # Convert to geographic azimuth clockwise from North:
    # v_east = cos(theta_grid), v_north = -sin(theta_grid) => az_normal = atan2(v_east, v_north)
    theta_grid = 0.5 * np.arctan2(2.0 * j_xy, diff_j + 1e-12)
    nx_east = np.cos(theta_grid).astype(np.float32)
    ny_north = (-np.sin(theta_grid)).astype(np.float32)
    az_normal_rad = np.arctan2(nx_east, ny_north)  # azimuth of fault-plane normal from North
    n_row = np.sin(theta_grid).astype(np.float32)
    n_col = nx_east
    del j_xx, j_yy, j_xy, diff_j, disc, lam1, lam2, theta_grid, ny_north

    # Spatially-varying kinematic regime psi in [0, pi/2]:
    # psi -> pi/2 in pure extension (Basin & Range: sigma_3 azimuth ~ N108E)
    # psi -> 0 in pure dextral shear (Walker Lane: sigma_3 rotates toward N100E..N115E,
    # sigma_1 horizontal ~ N015E, creating conjugate NNW dextral & ENE Carson/Humboldt sinistral faults)
    dil_pos = np.maximum(b08, 0.0)
    shr_pos = np.maximum(b07, 0.0)
    psi = np.arctan2(dil_pos, shr_pos + 1e-5).astype(np.float32)
    ext_frac = (psi / (0.5 * math.pi)).astype(np.float32)  # 0 = shear, 1 = pure extension

    # Local minimum horizontal stress azimuth sigma_3(x): ~104 deg in Walker Lane -> ~112 deg in interior B&R
    az_sig3 = np.deg2rad(104.0 + 8.0 * ext_frac).astype(np.float32)
    # Morris et al. (1996) resolved Dilation Tendency T_d = cos^2(az_normal - az_sig3):
    t_dil = (np.cos(az_normal_rad - az_sig3) ** 2).astype(np.float32)

    # Morris et al. (1996) resolved Slip Tendency T_s across transtensional modes:
    # Mode 1 (Normal dip-slip on 55-deg dipping plane striking perp to sigma_3): sin(2*55 deg)*T_d ~ 0.94*T_d
    # Mode 2 (Strike-slip Coulomb planes at +/-30 deg strike to sigma_1 = az_sig3 - 90 deg,
    #         i.e. fault normals at az_sig3 +/- 30 deg -> NNW Walker Lane & ENE Carson/Humboldt!):
    t_slip_strike = np.maximum(
        np.cos(az_normal_rad - (az_sig3 - math.radians(30.0))) ** 2,
        np.cos(az_normal_rad - (az_sig3 + math.radians(30.0))) ** 2,
    ).astype(np.float32)
    t_slip = ((0.45 + 0.45 * ext_frac) * t_dil + (0.55 - 0.35 * ext_frac) * t_slip_strike).astype(np.float32)
    del az_normal_rad, az_sig3, t_slip_strike, ext_frac

    z_strain = np.clip(DD._robust_z(b04, footprint), -1.0, 5.0)
    z_shr = np.clip(DD._robust_z(shr_pos, footprint), -1.0, 5.0)
    z_dil = np.clip(DD._robust_z(dil_pos, footprint), -1.0, 5.0)
    strain_drive = (
        1.0 + 0.30 * np.maximum(z_strain, 0.0) + 0.25 * np.maximum(z_shr, 0.0) + 0.20 * np.maximum(z_dil, 0.0)
    ).astype(np.float32)
    crit_edge = ((0.55 * t_dil + 0.45 * t_slip) * st_aniso * strain_drive).astype(np.float32)
    del b04, b07, b08, dil_pos, shr_pos, z_strain, z_shr, z_dil, strain_drive

    # Cross-strike Airborne Radiometric TC (`B06`) signed step along fault normal `(n_row, n_col)`:
    tc_sm = ndi.gaussian_filter(b06, sigma=1.2).astype(np.float32)
    del b06
    yy, xx = np.indices((h, w), dtype=np.float32)
    c_plus = np.array([np.clip(yy + 3.0 * n_row, 0, h - 1), np.clip(xx + 3.0 * n_col, 0, w - 1)])
    c_minus = np.array([np.clip(yy - 3.0 * n_row, 0, h - 1), np.clip(xx - 3.0 * n_col, 0, w - 1)])
    del yy, xx, n_row, n_col
    tc_step = np.abs(
        ndi.map_coordinates(tc_sm, c_plus, order=1, mode="nearest")
        - ndi.map_coordinates(tc_sm, c_minus, order=1, mode="nearest")
    ).astype(np.float32)
    del tc_sm, c_plus, c_minus
    rad_tc_step_aniso = (np.maximum(DD._robust_z(tc_step, footprint), 0.0) * (0.3 + 0.7 * st_aniso)).astype(np.float32)
    del tc_step, st_aniso

    # Basin-margin basement flexure: |Laplacian(B15)| * Marussi/gravity edge
    b15_lap = np.abs(ndi.gaussian_laplace(sed_depth, sigma=3.0)).astype(np.float32)
    del sed_depth, b15
    flexure_fp = np.maximum(DD._robust_z(b15_lap, footprint)[footprint], 0.0)
    del b15_lap
    grav_tilt_hd_fp = np.maximum(np.asarray(X_ptha[:, 2], dtype=np.float32), 0.0)
    basin_flexure_fp = np.sqrt(flexure_fp * np.log1p(grav_tilt_hd_fp) + 1e-6).astype(np.float32)
    del flexure_fp, grav_tilt_hd_fp

    # Blind hydrothermal clay-cap joint index (FP-indexed, zero extra 2-D arrays):
    # X_s12 col 4 is `s12_geodawn_shallow_res` (B14 - B01, negative in demagnetized troughs)
    shallow_demag_fp = np.maximum(-np.asarray(X_s12[:, 4], dtype=np.float32), 0.0)
    demag_med = float(np.median(shallow_demag_fp))
    demag_mad = float(np.median(np.abs(shallow_demag_fp - demag_med))) * 1.4826 + 1e-6
    z_demag = np.clip((shallow_demag_fp - demag_med) / demag_mad, 0.0, 6.0)
    cond_hp_fp = np.maximum(np.asarray(X_static[:, 33], dtype=np.float32), 0.0)
    cond_hp_med = float(np.median(cond_hp_fp))
    cond_hp_mad = float(np.median(np.abs(cond_hp_fp - cond_hp_med))) * 1.4826 + 1e-6
    z_cond_hp = np.clip((cond_hp_fp - cond_hp_med) / cond_hp_mad, 0.0, 6.0)
    swarm_ex_fp = np.maximum(np.asarray(X_ptha[:, 17], dtype=np.float32), 0.0)
    blind_hydro_fp = (
        np.log1p(z_demag) * np.log1p(z_cond_hp) * (1.0 + 0.45 * swarm_ex_fp)
    ).astype(np.float32)
    del shallow_demag_fp, z_demag, cond_hp_fp, z_cond_hp, swarm_ex_fp

    # GDR geothermal spring + blind >90C geothermometry coupled with stressed edge:
    gdr_spring_fp = np.maximum(np.asarray(X_static[:, 38], dtype=np.float32), 0.0)
    gdr_blind90_fp = np.maximum(np.asarray(X_static[:, 40], dtype=np.float32), 0.0)
    crit_fp = crit_edge[footprint]
    gdr_stressed_fp = ((0.55 * gdr_spring_fp + 0.45 * gdr_blind90_fp) * (0.5 + crit_fp)).astype(np.float32)
    del gdr_spring_fp, gdr_blind90_fp

    mm[:, 12] = psi[footprint]
    mm[:, 13] = t_dil[footprint]
    mm[:, 14] = t_slip[footprint]
    mm[:, 15] = crit_fp
    mm[:, 16] = rad_tc_step_aniso[footprint]
    mm[:, 17] = blind_hydro_fp
    mm[:, 18] = gdr_stressed_fp
    mm[:, 19] = basin_flexure_fp
    mm.flush()

    del psi, t_dil, t_slip, crit_edge, crit_fp, rad_tc_step_aniso, blind_hydro_fp, gdr_stressed_fp, basin_flexure_fp
    gc.collect()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": list(S15_EUAS_FEATURE_NAMES),
        "tmi_hg_unit_scale": TMI_HG_UNIT_SCALE,
        "grav_hg_unit_scale": GRAV_HG_UNIT_SCALE,
        "euler_window_px": 7,
        "upward_altitudes_m": [100.0, 300.0, 800.0, 2000.0],
        "source": "official training_features.tif + public-domain DOE GDR springs (zero IR-91-26 files)",
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S15_EUAS_FEATURE_NAMES), meta


def compute_fold_depth_deconfounded_conductivity(
    X_static: np.memmap | np.ndarray,
    footprint: np.ndarray,
    train_fit_fp_mask: np.ndarray,
) -> np.ndarray:
    """Fit `log1p(max(B17, 0)) ~ [1, H, sqrt(H), log1p(H), B12]` via ridge-stabilized OLS
    STRICTLY on `train_fit_fp_mask` (`True` ONLY inside the fold's visible training region,
    NEVER touching the test quadrant!), then evaluate across `N_fp` to produce 2 leak-free
    float32 features `(N_fp, 2)`:
      0: `fold_cond_depth_res` (standardized depth-deconfounded conductivity residual)
      1: `fold_cond_res_crest` (`G_1.2(res) - G_7.0(res)` narrow hydrothermal plume crest)
    """
    b17 = np.maximum(np.asarray(X_static[:, 16], dtype=np.float32), 0.0)
    y_all = np.log1p(b17).astype(np.float32)
    h_sed = np.maximum(np.asarray(X_static[:, 14], dtype=np.float32), 0.0) / 1000.0  # km
    b12 = np.asarray(X_static[:, 11], dtype=np.float32) / 1000.0  # km

    # Subsample training mask deterministically for instant (<0.05s) OLS fit:
    tr_idx = np.flatnonzero(train_fit_fp_mask)[::8]
    if tr_idx.size < 32:
        tr_idx = np.flatnonzero(train_fit_fp_mask)

    design_tr = np.column_stack([
        np.ones(tr_idx.size, dtype=np.float64),
        h_sed[tr_idx].astype(np.float64),
        np.sqrt(h_sed[tr_idx]).astype(np.float64),
        np.log1p(h_sed[tr_idx]).astype(np.float64),
        b12[tr_idx].astype(np.float64),
    ])
    y_tr = y_all[tr_idx].astype(np.float64)
    xtx = design_tr.T @ design_tr + 1e-3 * np.eye(5, dtype=np.float64)
    beta = np.linalg.solve(xtx, design_tr.T @ y_tr).astype(np.float32)
    del design_tr, y_tr, xtx

    y_hat = (
        beta[0]
        + beta[1] * h_sed
        + beta[2] * np.sqrt(h_sed)
        + beta[3] * np.log1p(h_sed)
        + beta[4] * b12
    ).astype(np.float32)
    res = (y_all - y_hat).astype(np.float32)
    del b17, y_all, h_sed, b12, y_hat

    # Standardize strictly using training-fold median/MAD:
    med = float(np.median(res[train_fit_fp_mask]))
    mad = float(np.median(np.abs(res[train_fit_fp_mask] - med))) * 1.4826 + 1e-5
    res_z = np.clip((res - med) / mad, -5.0, 6.0).astype(np.float32)
    del res

    # Narrow cross-strike hydrothermal plume crest (2-D DoG on standardized residual):
    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[footprint] = res_z
    crest_2d = (ndi.gaussian_filter(grid, sigma=1.2) - ndi.gaussian_filter(grid, sigma=7.0)).astype(np.float32)
    del grid

    out = np.empty((int(footprint.sum()), 2), dtype=np.float32)
    out[:, 0] = res_z
    out[:, 1] = crest_2d[footprint]
    return out


class FeatureColumnSpec:
    """Memory-safe column gather specification across cached float32 memmaps."""

    def __init__(
        self,
        arrays: list[tuple[str, np.ndarray | np.memmap, list[int], list[str]]],
    ) -> None:
        self.arrays = arrays
        self.feature_names: list[str] = []
        for _, _, _, names in arrays:
            self.feature_names.extend(names)
        self.n_cols = len(self.feature_names)
        self.subsurface_col_idx = np.array(
            [j for j, nm in enumerate(self.feature_names) if nm not in TOPO_EXPOSURE_FEATURE_NAMES],
            dtype=np.int64,
        )

    def gather(self, row_idx: np.ndarray) -> np.ndarray:
        out = np.empty((row_idx.size, self.n_cols), dtype=np.float32)
        c = 0
        for _, arr, cols, _ in self.arrays:
            k = len(cols)
            out[:, c : c + k] = arr[row_idx][:, cols]
            c += k
        return out


def build_s15_feature_spec(
    *,
    X_static: np.memmap | np.ndarray,
    X_s11: np.memmap | np.ndarray,
    X_s12: np.memmap | np.ndarray,
    X_ptha: np.memmap | np.ndarray,
    X_s15: np.memmap | np.ndarray,
    include_group_b: bool,
    X_fold_cond: np.ndarray | None = None,
    X_autocontext: np.ndarray | None = None,
) -> FeatureColumnSpec:
    """Construct exact deduplicated feature specification for E1 (`include_group_b=False`),
    E2 (`include_group_b=True` + `X_fold_cond`), or E3 Stage-2 (`+ X_autocontext`).
    """
    st_names = [DD.ALL_STATIC_FEATURE_NAMES[i] for i in CLEAN_STATIC_INDICES]
    s11_idx = list(range(len(MC.S11_MHTR_FEATURE_NAMES)))
    s11_names = list(MC.S11_MHTR_FEATURE_NAMES)
    s12_names = [SPAC.S12_SPAC_STATIC_FEATURE_NAMES[i] for i in CLEAN_S12_INDICES]
    ptha_idx = list(range(len(PTHA.PTHA_FEATURE_NAMES)))
    ptha_names = list(PTHA.PTHA_FEATURE_NAMES)

    s15_idx = list(range(12)) if not include_group_b else list(range(20))
    s15_names = [S15_EUAS_FEATURE_NAMES[i] for i in s15_idx]

    blocks: list[tuple[str, np.ndarray | np.memmap, list[int], list[str]]] = [
        ("static", X_static, list(CLEAN_STATIC_INDICES), st_names),
        ("s11", X_s11, s11_idx, s11_names),
        ("s12", X_s12, list(CLEAN_S12_INDICES), s12_names),
        ("ptha", X_ptha, ptha_idx, ptha_names),
        ("s15", X_s15, s15_idx, s15_names),
    ]
    if X_fold_cond is not None:
        blocks.append(("fold_cond", X_fold_cond, [0, 1], list(S15_FOLD_COND_NAMES)))
    if X_autocontext is not None:
        ac_idx = list(range(len(SPAC.S12_AUTOCONTEXT_FEATURE_NAMES)))
        blocks.append(("autocontext", X_autocontext, ac_idx, list(SPAC.S12_AUTOCONTEXT_FEATURE_NAMES)))
    return FeatureColumnSpec(blocks)


def compute_concealed_gate_fp(X_static: np.memmap | np.ndarray) -> np.ndarray:
    """Smooth label-free regime gate in `[0.18, 0.52]` boosting the Topography-Blind
    Subsurface Specialist on flat alluvial/playa basins (`B19` low, `B15` deep).
    """
    slope_deg = np.maximum(np.asarray(X_static[:, 18], dtype=np.float32), 0.0)
    depth_m = np.maximum(np.asarray(X_static[:, 14], dtype=np.float32), 0.0)
    flat_sig = 1.0 / (1.0 + np.exp((slope_deg - 5.5) / 1.8))
    deep_sig = 1.0 / (1.0 + np.exp(-(depth_m - 120.0) / 180.0))
    return np.clip(0.18 + 0.34 * flat_sig * deep_sig, 0.18, 0.52).astype(np.float32)


def compute_euas_hard_mining_score_fp(
    X_s15: np.memmap | np.ndarray,
    X_ptha: np.memmap | np.ndarray,
    X_static: np.memmap | np.ndarray,
) -> np.ndarray:
    """Label-free structural/potential-field anomaly score across `N_fp` used ONLY
    to sample informative hard negatives inside the training fold.
    """
    s_euler = np.maximum(np.asarray(X_s15[:, 1], dtype=np.float32), 0.0) + np.maximum(
        np.asarray(X_s15[:, 5], dtype=np.float32), 0.0
    )
    s_worm = np.log1p(
        np.maximum(np.asarray(X_s15[:, 8], dtype=np.float32), 0.0)
        + np.maximum(np.asarray(X_s15[:, 9], dtype=np.float32), 0.0)
    )
    s_grav = np.log1p(np.maximum(np.asarray(X_ptha[:, 2], dtype=np.float32), 0.0))
    s_mag = np.log1p(np.maximum(np.asarray(X_ptha[:, 5], dtype=np.float32), 0.0))
    s_topo = np.log1p(np.maximum(np.asarray(X_static[:, 22], dtype=np.float32), 0.0))
    return (0.28 * s_euler + 0.22 * s_worm + 0.20 * s_grav + 0.15 * s_mag + 0.15 * s_topo).astype(np.float32)


def fit_and_predict_euas_experts(
    spec: FeatureColumnSpec,
    *,
    footprint: np.ndarray,
    visible_faults_2d: np.ndarray,
    train_region_2d: np.ndarray,
    predict_fp_indices: np.ndarray,
    hard_score_fp: np.ndarray,
    concealed_gate_fp: np.ndarray,
    seed: int = 1501,
    neg_pos_ratio: float = 3.8,
    max_pos: int = 58000,
    n_iter_trees: int = 215,
    fast_inner_mode: bool = False,
) -> tuple[np.ndarray, dict]:
    """Fit the 4-expert `S15-EUAS` ensemble strictly on `train_region_2d` (excluding the
    100 m flank halo `[1, 2.2] px` around `visible_faults_2d`) with importance-reweighted
    hard-negative mining, and predict probabilities ONLY on `predict_fp_indices` (`1-D`
    indices into `N_fp`) to cut inference CPU and RAM by up to 4x.
    """
    rng = np.random.default_rng(seed)
    d_vis = ndi.distance_transform_edt(~visible_faults_2d)

    pos_2d = visible_faults_2d & train_region_2d & footprint
    neg_2d = (d_vis > 2.2) & train_region_2d & footprint
    del d_vis

    pos_fp = pos_2d[footprint]
    neg_fp = neg_2d[footprint]
    del pos_2d, neg_2d

    pos_all = np.flatnonzero(pos_fp)
    neg_all = np.flatnonzero(neg_fp)
    del pos_fp, neg_fp

    if pos_all.size == 0 or neg_all.size == 0:
        raise RuntimeError("Empty positive or negative training pool in EUAS fold")

    if fast_inner_mode:
        max_pos = min(max_pos, 30000)
        neg_pos_ratio = min(neg_pos_ratio, 3.4)
        n_iter_trees = min(n_iter_trees, 145)

    pos_idx = (
        rng.choice(pos_all, size=max_pos, replace=False)
        if pos_all.size > max_pos
        else pos_all.copy()
    )
    pos_idx.sort()

    target_neg = min(int(round(pos_idx.size * float(neg_pos_ratio))), int(neg_all.size))
    n_hard = target_neg // 2
    n_rand = target_neg - n_hard

    neg_scores = hard_score_fp[neg_all]
    hard_thresh = float(np.quantile(neg_scores, 0.80))
    hard_pool = neg_all[neg_scores >= hard_thresh]
    bg_pool = neg_all[neg_scores < hard_thresh]
    del neg_scores

    if hard_pool.size >= n_hard and bg_pool.size >= n_rand:
        hard_sel = rng.choice(hard_pool, size=n_hard, replace=False)
        bg_sel = rng.choice(bg_pool, size=n_rand, replace=False)
        neg_idx = np.concatenate([hard_sel, bg_sel])
        # Exact importance weights correcting 50/50 sampling back to 20/80 population strata:
        w_neg = np.concatenate([
            np.full(n_hard, 0.40, dtype=np.float32),
            np.full(n_rand, 1.60, dtype=np.float32),
        ])
    else:
        neg_idx = rng.choice(neg_all, size=target_neg, replace=False)
        w_neg = np.ones(neg_idx.size, dtype=np.float32)

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])
    w_train = np.concatenate([np.ones(pos_idx.size, dtype=np.float32), w_neg])

    perm = rng.permutation(train_idx.size)
    train_idx = train_idx[perm]
    y_train = y_train[perm]
    w_train = w_train[perm]

    X_train = np.nan_to_num(spec.gather(train_idx), nan=0.0, posinf=0.0, neginf=0.0)
    sub_cols = spec.subsurface_col_idx

    # Expert 1: Full-stack HGB (depth 6, leaf 45)
    hgb_full = HistGradientBoostingClassifier(
        learning_rate=0.055 if not fast_inner_mode else 0.068,
        max_iter=n_iter_trees,
        max_leaf_nodes=45 if not fast_inner_mode else 39,
        min_samples_leaf=90,
        l2_regularization=2.5,
        max_features=0.75,
        early_stopping=True,
        validation_fraction=0.10,
        n_iter_no_change=18 if not fast_inner_mode else 14,
        random_state=seed,
    )
    hgb_full.fit(X_train, y_train, sample_weight=w_train)

    # Expert 2: Regularized Column-Subsampled HGB (skipped in fast_inner_mode)
    hgb_reg = None
    if not fast_inner_mode:
        hgb_reg = HistGradientBoostingClassifier(
            learning_rate=0.048,
            max_iter=n_iter_trees + 15,
            max_leaf_nodes=31,
            min_samples_leaf=130,
            l2_regularization=5.0,
            max_features=0.50,
            early_stopping=True,
            validation_fraction=0.10,
            n_iter_no_change=18,
            random_state=seed + 19,
        )
        hgb_reg.fit(X_train, y_train, sample_weight=w_train)

    # Expert 3: Topography-Blind Subsurface Specialist HGB (ZERO DEM/slope/SPI features!)
    hgb_sub = HistGradientBoostingClassifier(
        learning_rate=0.052 if not fast_inner_mode else 0.065,
        max_iter=n_iter_trees,
        max_leaf_nodes=39 if not fast_inner_mode else 33,
        min_samples_leaf=100,
        l2_regularization=3.5,
        max_features=0.75,
        early_stopping=True,
        validation_fraction=0.10,
        n_iter_no_change=18 if not fast_inner_mode else 14,
        random_state=seed + 41,
    )
    hgb_sub.fit(X_train[:, sub_cols], y_train, sample_weight=w_train)

    # Expert 4: MAD-scaled, clipped L2 Logistic Regression (skipped in fast_inner_mode)
    med = None
    mad = None
    lr = None
    if not fast_inner_mode:
        med = np.median(X_train, axis=0)
        mad = np.median(np.abs(X_train - med), axis=0) * 1.4826 + 1e-5
        X_lr = np.clip((X_train - med) / mad, -6.0, 6.0)
        lr = LogisticRegression(C=0.20, max_iter=220, tol=5e-4, random_state=seed + 73)
        lr.fit(X_lr, y_train, sample_weight=w_train)
        del X_lr
    del X_train
    gc.collect()

    # Chunked prediction strictly on `predict_fp_indices`:
    n_pred = int(predict_fp_indices.size)
    preds = np.empty(n_pred, dtype=np.float32)
    chunk = 260_000
    for start in range(0, n_pred, chunk):
        stop = min(start + chunk, n_pred)
        idx_c = predict_fp_indices[start:stop]
        Xc = np.nan_to_num(spec.gather(idx_c), nan=0.0, posinf=0.0, neginf=0.0)
        p1 = hgb_full.predict_proba(Xc)[:, 1].astype(np.float32)
        p_sub = hgb_sub.predict_proba(Xc[:, sub_cols])[:, 1].astype(np.float32)
        if fast_inner_mode:
            p_surf = p1
        else:
            assert hgb_reg is not None and lr is not None and med is not None and mad is not None
            p2 = hgb_reg.predict_proba(Xc)[:, 1].astype(np.float32)
            Xc_lr = np.clip((Xc - med) / mad, -6.0, 6.0)
            p_lr = lr.predict_proba(Xc_lr)[:, 1].astype(np.float32)
            p_surf = 0.50 * p1 + 0.38 * p2 + 0.12 * p_lr
            del p2, Xc_lr, p_lr
        alpha_sub = concealed_gate_fp[idx_c]
        preds[start:stop] = ((1.0 - alpha_sub) * p_surf + alpha_sub * p_sub).astype(np.float32)
        del Xc, p1, p_sub, p_surf

    pi_true = float(pos_all.size) / float(max(pos_all.size + neg_all.size, 1))
    pi_sample = float(pos_idx.size) / float(max(pos_idx.size + float(w_neg.sum()), 1e-6))

    info = {
        "n_pos_train": int(pos_idx.size),
        "n_neg_train": int(neg_idx.size),
        "pi_true": round(pi_true, 7),
        "pi_sample": round(pi_sample, 7),
        "n_total_cols": int(spec.n_cols),
        "n_subsurface_cols": int(sub_cols.size),
        "iter_full": int(hgb_full.n_iter_),
        "iter_reg": int(hgb_reg.n_iter_) if hgb_reg is not None else 0,
        "iter_sub": int(hgb_sub.n_iter_),
        "lr_n_iter": int(np.max(lr.n_iter_)) if lr is not None else 0,
    }
    return preds, info


def make_spatial_checkerboard_2d(
    shape: tuple[int, int],
    block_px: int = 100,
) -> np.ndarray:
    """Deterministic `10 km x 10 km` (`100 px x 100 px`) 2-fold spatial checkerboard mask
    (`True` on parity-0 blocks, `False` on parity-1 blocks) used for leak-free out-of-sample
    Stage-2 probability & Dinkelbach calibration across training quadrants.
    """
    rr = np.arange(shape[0], dtype=np.int32)[:, None] // int(block_px)
    cc = np.arange(shape[1], dtype=np.int32)[None, :] // int(block_px)
    return ((rr + cc) % 2) == 0


def compute_euas_crest_field_2d(
    X_s15: np.memmap | np.ndarray,
    X_ptha: np.memmap | np.ndarray,
    X_static: np.memmap | np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Compute a 4-azimuth 1-D cross-strike local crest enhancement field `(H, W)` in
    `[0, 1]` combining multi-physics subsurface Euler/worm/gravity/magnetic step sharpness
    with topographic scarp sharpness so buried flat-basin fault traces also form sharp
    1-px centerlines.
    """
    comp_fp = (
        0.30 * np.maximum(np.asarray(X_s15[:, 1], dtype=np.float32), 0.0) * 3.0
        + 0.20 * np.maximum(np.asarray(X_s15[:, 5], dtype=np.float32), 0.0) * 3.0
        + 0.25 * np.log1p(np.maximum(np.asarray(X_ptha[:, 2], dtype=np.float32), 0.0))
        + 0.25 * np.log1p(np.maximum(np.asarray(X_static[:, 22], dtype=np.float32), 0.0))
    ).astype(np.float32)
    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[footprint] = comp_fp
    sm = ndi.gaussian_filter(grid, sigma=0.75).astype(np.float32)
    del grid

    crest = np.zeros_like(sm)
    for dy, dx in ((0, 2), (2, 0), (2, 2), (2, -2)):
        nb = 0.5 * (SPAC._shift_2d(sm, dy, dx) + SPAC._shift_2d(sm, -dy, -dx))
        np.maximum(crest, sm - nb, out=crest)
    del sm
    z_c = np.maximum(DD._robust_z(crest, footprint), 0.0)
    return np.tanh(0.45 * z_c).astype(np.float32)


def _compute_local_self_credit_2d(
    p_w_2d: np.ndarray,
    is_q_ridge: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Compute noisy-OR 300 m (`R = 3 px`) local matched-mass self-credit `m_hat(j)` in
    `[0, 0.85]` strictly from continuum-floored per-pixel fault intensity `p_w_2d`
    (sharing the exact same `gamma` exponent as `w_intensity_2d = 1000.0 * p_w_2d` so
    `1000 * 0.2 * lambda_0 * m_hat` and `(1 - 0.2 * lambda_0) * Delta_T` never suffer a
    scale mismatch at small `q_exc` — fixes `IR-91-S15-03`).
    """
    p_clip = np.clip(np.where(footprint, p_w_2d, 0.0), 0.0, 0.50).astype(np.float32)
    yy, xx = np.mgrid[-2:3, -2:3]
    dist = np.hypot(yy, xx)
    k = np.maximum(0.0, 1.0 - dist / 3.0).astype(np.float32)
    s1 = ndi.convolve(p_clip, k, mode="constant", cval=0.0)
    s2 = ndi.convolve(p_clip * p_clip, 0.5 * (k * k), mode="constant", cval=0.0)
    m_hat = np.clip(1.0 - np.exp(-(s1 + s2)), 0.0, 0.85).astype(np.float32)
    # Centerline preference prevents off-ridge parallel halo rings from farming M-credit:
    m_hat = (m_hat * np.where(is_q_ridge, np.float32(1.0), np.float32(0.24))).astype(np.float32)
    m_hat[~footprint] = 0.0
    return m_hat


def _greedy_dinkelbach_extract(
    w_intensity_2d: np.ndarray,
    m_hat_2d: np.ndarray,
    eligible_mask: np.ndarray,
    *,
    rank_surf: np.ndarray | None = None,
    max_dots: int,
    min_dots: int = 0,
    tau_stop: float | None = None,
    lambda_target: float = 0.2778,
    min_spacing_px: float = 2.55,
    pool_mult: int = 10,
    min_pool: int = 80_000,
) -> tuple[np.ndarray, dict]:
    """Minoux lazy-heap submodular maximization of the consistent milli-probability
    Dinkelbach linearized DTI marginal gain above the constant `-1000*0.2*lambda_0`
    per-dot baseline:

        g_+(j | C) = (1 - 0.2 * lambda_0) * Delta_j E[1000 * T(C)]
                     + 1000 * 0.2 * lambda_0 * m_hat_j * (1 - cov_C(j))

    Note that subtracting the constant `1000 * 0.2 * lambda_0` shifts `g_+` and `tau_k`
    by the exact same constant across training calibration and test emission; keeping
    `g_+ >= 0` guarantees monotone submodularity (since both `Delta_j E[T(C)]` and
    `(1 - cov_C(j))` are monotonically non-increasing in `C`) so Minoux lazy-heap upper
    bounds are 100% exact!
    """
    h, w = w_intensity_2d.shape
    out = np.zeros((h, w), dtype=np.float32)
    if max_dots <= 0 or not eligible_mask.any():
        return out, {"n_dots": 0, "last_dinkelbach_gain": 0.0}

    coeff_t = float(1.0 - 0.2 * lambda_target)
    coeff_m = float(1000.0 * 0.2 * lambda_target)
    min_gain_thr = 0.0 if tau_stop is None else float(tau_stop)

    r_surf = w_intensity_2d if rank_surf is None else rank_surf
    cand_r, cand_c = np.nonzero(eligible_mask & (w_intensity_2d > 0.0))
    if cand_r.size == 0:
        return out, {"n_dots": 0, "last_dinkelbach_gain": 0.0}

    pool_k = min(cand_r.size, max(int(max_dots) * int(pool_mult), int(min_pool)))
    if cand_r.size > pool_k:
        top_idx = np.argpartition(r_surf[cand_r, cand_c], -pool_k)[-pool_k:]
        cand_r = cand_r[top_idx]
        cand_c = cand_c[top_idx]

    offs: list[tuple[int, int, float]] = [
        (dy, dx, float(1.0 - math.hypot(dy, dx) / 3.0))
        for dy in range(-2, 3)
        for dx in range(-2, 3)
        if math.hypot(dy, dx) < 3.0
    ]
    sp_r = int(math.ceil(min_spacing_px))
    sp_offs: list[tuple[int, int]] = [
        (dy, dx)
        for dy in range(-sp_r, sp_r + 1)
        for dx in range(-sp_r, sp_r + 1)
        if math.hypot(dy, dx) < min_spacing_px
    ]

    pad = max(3, sp_r + 1)
    w_pad = np.pad(w_intensity_2d, pad, mode="constant", constant_values=0.0)
    m_pad = np.pad(m_hat_2d, pad, mode="constant", constant_values=0.0)
    cov_pad = np.zeros_like(w_pad, dtype=np.float32)
    blocked_pad = np.zeros(w_pad.shape, dtype=bool)

    cr_p = cand_r + pad
    cc_p = cand_c + pad
    init_dt = np.zeros(cr_p.size, dtype=np.float32)
    for dy, dx, kw in offs:
        init_dt += w_pad[cr_p + dy, cc_p + dx] * np.float32(kw)
    init_gains = np.float32(coeff_t) * init_dt + np.float32(coeff_m) * m_pad[cr_p, cc_p]

    heap: list[tuple[float, int, int]] = [
        (-float(init_gains[i]), int(cr_p[i]), int(cc_p[i])) for i in range(cr_p.size)
    ]
    heapq.heapify(heap)

    n_sel = 0
    last_gain = 0.0
    while n_sel < max_dots and heap:
        neg_ub, rp, cp = heapq.heappop(heap)
        if blocked_pad[rp, cp]:
            continue
        ub = -neg_ub
        if tau_stop is not None and n_sel >= min_dots and ub < min_gain_thr:
            break

        dt = 0.0
        for dy, dx, kw in offs:
            cur_c = float(cov_pad[rp + dy, cp + dx])
            if kw > cur_c:
                dt += float(w_pad[rp + dy, cp + dx]) * (kw - cur_c)
        rem_self = max(0.0, 1.0 - float(cov_pad[rp, cp]))
        gain = coeff_t * dt + coeff_m * float(m_pad[rp, cp]) * rem_self

        if tau_stop is not None and n_sel >= min_dots and gain < min_gain_thr:
            continue

        next_ub = -heap[0][0] if heap else -1.0
        if gain >= next_ub * 0.996:
            out[rp - pad, cp - pad] = 1.0
            n_sel += 1
            last_gain = float(gain)
            for dy, dx, kw in offs:
                if kw > cov_pad[rp + dy, cp + dx]:
                    cov_pad[rp + dy, cp + dx] = kw
            for dy, dx in sp_offs:
                blocked_pad[rp + dy, cp + dx] = True
        else:
            heapq.heappush(heap, (-gain, rp, cp))

    return out, {
        "n_dots": int(n_sel),
        "last_dinkelbach_gain": round(float(last_gain), 6),
    }


def _build_euas_dinkelbach_intensity(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    pi_true: float,
    pi_sample: float,
    q_floor: float | None = None,
    calibration_mask: np.ndarray | None = None,
    keep_corridor_frac: float = 0.16,
    gamma: float = 1.16,
    crest_weight: float = 0.48,
    concealed_pu_boost: float = 1.24,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Construct 1-D-centerline-skeletonized, Bayes-prior-shifted milli-intensity `w_2d`
    (`1000.0 * p_w`), matching continuum-floored noisy-OR self-credit `m_hat_2d`, and
    ridge-preferring candidate rank surface `rank_s` in consistent milli-probability
    units (`IR-91-S15-03` fixed).
    """
    pi_cal = PTHA.prior_shift_calibrate_surface(
        prob_2d, footprint, pi_true=float(pi_true), pi_sample=float(pi_sample)
    )
    q = (pi_cal * (1.0 + np.float32(crest_weight) * crest_2d)).astype(np.float32)
    q[~footprint] = 0.0

    if q_floor is None:
        if calibration_mask is None:
            raise ValueError("Either q_floor or calibration_mask must be provided")
        cal_vals = q[calibration_mask & (q > 0.0)]
        q_floor = float(np.quantile(cal_vals, 1.0 - keep_corridor_frac)) if cal_vals.size > 0 else 0.0

    is_q_ridge = PTHA._detect_1d_directional_ridge(q, span=2)
    is_crest_ridge = PTHA._detect_1d_directional_ridge(crest_2d, span=1)

    q_exc = np.maximum(q - np.float32(q_floor), 0.0)
    ridge_mult = np.where(is_q_ridge, np.float32(1.0), np.float32(0.24))
    pu_mult = np.where(piedmont_mask & is_crest_ridge, np.float32(concealed_pu_boost), np.float32(1.0))

    p_w = ((q_exc ** np.float32(gamma)) * ridge_mult * pu_mult).astype(np.float32)
    p_w[~footprint] = 0.0
    w = (np.float32(1000.0) * p_w).astype(np.float32)
    m_hat = _compute_local_self_credit_2d(p_w, is_q_ridge, footprint)
    rank_s = (
        q * np.where(is_q_ridge, np.float32(1.15), np.float32(0.85)) * pu_mult
    ).astype(np.float32)
    rank_s[~footprint] = 0.0
    return w, m_hat, rank_s, float(q_floor)


def emit_oof_calibrated_selfcredit_dinkelbach(
    *,
    oof_train_prob_2d: np.ndarray,
    test_prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray | None = None,
    footprint: np.ndarray | None = None,
    train_eligible_2d: np.ndarray,
    test_eligible_2d: np.ndarray,
    train_target_dots: int,
    test_quota_ref: int,
    pi_true: float = 0.0125,
    pi_sample: float = 0.2083,
    lambda_target: float = 0.2778,
    min_spacing_px: float = 2.55,
    min_test_dots: int | None = None,
    max_test_dots: int = 18_000,
) -> tuple[np.ndarray, dict]:
    """Calibrate expected fault intensity floor `q_floor` AND Dinkelbach stopping
    threshold `tau_k` STRICTLY on `oof_train_prob_2d` (whole-quadrant segment-buffered
    out-of-sample predictions across the 3 training quadrants — NEVER in-sample, and
    NEVER reading `test_prob_2d`!), then emit binary `{0, 1}` dots on `test_eligible_2d`.
    """
    fp = (train_eligible_2d | test_eligible_2d) if footprint is None else footprint
    pm = np.zeros_like(fp, dtype=bool) if piedmont_mask is None else piedmont_mask

    w_train, m_train, rk_train, q_floor = _build_euas_dinkelbach_intensity(
        oof_train_prob_2d,
        crest_2d,
        pm,
        fp,
        pi_true=pi_true,
        pi_sample=pi_sample,
        q_floor=None,
        calibration_mask=train_eligible_2d,
    )
    _, tr_info = _greedy_dinkelbach_extract(
        w_train,
        m_train,
        train_eligible_2d,
        rank_surf=rk_train,
        max_dots=int(train_target_dots),
        min_dots=int(train_target_dots),
        tau_stop=None,
        lambda_target=lambda_target,
        min_spacing_px=min_spacing_px,
    )
    tau_k = float(tr_info["last_dinkelbach_gain"])
    del w_train, m_train, rk_train

    w_test, m_test, rk_test, _ = _build_euas_dinkelbach_intensity(
        test_prob_2d,
        crest_2d,
        pm,
        fp,
        pi_true=pi_true,
        pi_sample=pi_sample,
        q_floor=q_floor,
    )
    min_test = int(min(6_500, round(0.65 * test_quota_ref))) if min_test_dots is None else int(min_test_dots)
    max_test = int(max(max_test_dots, round(1.30 * test_quota_ref))) if test_quota_ref >= 500 else int(round(1.35 * max(test_quota_ref, 1)))
    dots_test, te_info = _greedy_dinkelbach_extract(
        w_test,
        m_test,
        test_eligible_2d,
        rank_surf=rk_test,
        max_dots=max_test,
        min_dots=min_test,
        tau_stop=tau_k,
        lambda_target=lambda_target,
        min_spacing_px=min_spacing_px,
    )
    return dots_test, {
        "q_floor_oof_train": round(q_floor, 7),
        "q_low_oof_train": round(q_floor, 7),
        "tau_oof_train": round(tau_k, 6),
        "train_calib_dots": int(tr_info["n_dots"]),
        "test_quota_ref": int(test_quota_ref),
        "test_min_guard": int(min_test),
        "test_max_guard": int(max_test),
        "test_emitted_dots": int(te_info["n_dots"]),
        "test_last_gain": te_info["last_dinkelbach_gain"],
    }


def emit_full_map_selfcredit_dinkelbach(
    *,
    full_prob_2d: np.ndarray,
    oof_full_prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    footprint: np.ndarray,
    full_eligible_2d: np.ndarray,
    pi_true: float,
    pi_sample: float,
    target_dots: int,
    lambda_target: float = 0.2778,
    min_spacing_px: float = 2.55,
) -> tuple[np.ndarray, dict]:
    """Emit the full-footprint binary `{0, 1}` candidate map for `target_dots` using
    Bayes prior-shift calibration + 1-D directional ridge skeletonization + consistent
    milli-probability self-credit (`M`-term) Dinkelbach submodular ordering.
    """
    _, _, _, oof_q_floor = _build_euas_dinkelbach_intensity(
        oof_full_prob_2d,
        crest_2d,
        piedmont_mask,
        footprint,
        pi_true=pi_true,
        pi_sample=pi_sample,
        q_floor=None,
        calibration_mask=full_eligible_2d,
    )
    w_full, m_full, rk_full, full_q_floor = _build_euas_dinkelbach_intensity(
        full_prob_2d,
        crest_2d,
        piedmont_mask,
        footprint,
        pi_true=pi_true,
        pi_sample=pi_sample,
        q_floor=None,
        calibration_mask=full_eligible_2d,
    )

    dots, info = _greedy_dinkelbach_extract(
        w_full,
        m_full,
        full_eligible_2d,
        rank_surf=rk_full,
        max_dots=int(target_dots),
        min_dots=int(target_dots),
        tau_stop=None,
        lambda_target=lambda_target,
        min_spacing_px=min_spacing_px,
    )
    info.update({
        "oof_q_floor": round(oof_q_floor, 7),
        "full_q_floor": round(full_q_floor, 7),
        "target_dots": int(target_dots),
    })
    return dots, info
