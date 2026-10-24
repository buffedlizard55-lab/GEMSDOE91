"""Session 12 (`S12-SPID`): Laplace-Fourier Source Parameter Imaging (`SPI`),
Multiscale Upward-Continued Potential-Field Worms, Exact 3-D Roest Magnetic
Analytic Signal, Depth-Deconfounded Electrical Conductivity Clay-Cap Residual,
Co-Aligned Buried Basement-Step Hinge, Weingarten Principal Scarp-Toe Curvature,
Regime-Conditioned Mixture-of-Experts, and Self-Credit Bayes-Dinkelbach 300 m
Submodular DTI Pipeline.

Pre-registered in `docs/HYPOTHESES_S12.md` prior to executing the 3-experiment
holdout budget under `PARALLEL-RUN PROTOCOL`.

Addresses four measured physical & algorithmic deficits in prior candidates:
  1. `IR-91-S12-01`: Fixes the 100x unit mismatch & inclined-TMI vs pole-reduced
     RTP phase mixing in `rtp_tilt` by computing exact Laplace-wavenumber
     vertical derivatives `dz(RTP)` and `dz(G)` in SI units (`nT/m`, `mGal/m`),
     plus inclination/remanence-invariant 3-D Roest Analytic Signal `|A_TMI|`.
  2. `IR-91-S12-02`: Computes Thurston & Smith (1997) SPI contact wavenumbers
     `kappa_G = ||grad theta_G||`, Shallow-Break Ratio `log1p(B15 * kappa_G)`
     separating basin-cutting faults from passive basement contacts, and
     `z = {100, 400, 1200} m` upward-continued potential-field worm persistence.
  3. Subsurface Deconfounding & Weingarten Geometry: Regresses out basin-depth
     and elevation trends from `Band 17 (cond_surf)` to isolate linear smectite/
     illite fault-gouge ridges from saline playas, pairs `grad(B15)` with `-g_H`
     for buried basement-step hinges, and extracts 2x2 Weingarten principal
     concave-toe (`250 m`, `500 m`) and slope-ridge (`150 m`, `400 m`) eigenvalues.
  4. Regime-Conditioned Mixture-of-Experts + Self-Credit Bayes-Dinkelbach
     Submodular DTI Solver: Prevents steep mountain bedrock (`Band 19`) from
     starving concealed piedmont/intrabasinal faults (`46.4%` of catalogue faults
     have `slope < 5 deg`), sharpens `< 200 m` axial localization via off-kernel
     flank negatives (`4.2 <= d_vis <= 11.0 px`), steers strike continuation
     along local Hessian tangents, and optimizes expected DTI marginal gain
     including noisy-OR 300 m self-credit `m_hat(x)`.
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
from sklearn.preprocessing import StandardScaler

from . import dd_vtc_pu as DD

# 100% official `training_features.tif` static columns from H91 (excludes cols 38..42 GDR external CSV)
OFFICIAL_H91_STATIC_INDICES: list[int] = [
    i for i in range(len(DD.ALL_STATIC_FEATURE_NAMES)) if i not in (38, 39, 40, 41, 42)
]

# H12-3 Subsurface-First + Weingarten Scarp-Toe MoE feature subsets (100% official GeoDAWN):
# Drops H91's first-order LRM/openness scarp cols (19..23, which clone calib_h28ridge & S11),
# H91's buggy pseudo-tilts (24..32, IR-91-S12-01), H91's topo-dominated axial/Andersonian cols (34..37),
# and S11's raw topographic profile/slope cols (6, 7, 14).
SUBSURF_H91_COLS: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 33, 44, 45, 47, 48]
SUBSURF_S11_COLS: list[int] = [0, 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 15]
SUBSURF_S12_COLS: list[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 20, 22, 24]

WEINGARTEN_MP_H91_COLS: list[int] = SUBSURF_H91_COLS + [11, 18, 43]
WEINGARTEN_MP_S11_COLS: list[int] = SUBSURF_S11_COLS
WEINGARTEN_MP_S12_COLS: list[int] = list(range(25))

S12_SPID_FEATURE_NAMES: list[str] = [
    # Group A (H12-1, cols 0..9): Laplace-Fourier SPI, Upward Worms, & 3-D Roest Magnetics
    "s12_grav_dz_lap150",
    "s12_grav_true_tilt",
    "s12_grav_spi_k",
    "s12_spi_shallow_break",
    "s12_grav_worm_persist",
    "s12_grav_worm_dip_shift",
    "s12_roest_tmi_as3d",
    "s12_rtp_true_tilt",
    "s12_rtp_spi_k",
    "s12_remanence_phase_disc",
    # Group B (H12-2, cols 10..24): Depth-Conditioned Conductivity, Basement Hinge, Weingarten & Context
    "s12_cond_depth_res",
    "s12_cond_res_grad",
    "s12_cond_res_ridge",
    "s12_base_step_grad",
    "s12_base_grav_coalign",
    "s12_base_hinge_joint",
    "s12_weingarten_toe_250m",
    "s12_weingarten_toe_500m",
    "s12_slp_hess_ridge_150m",
    "s12_slp_hess_ridge_400m",
    "s12_transtens_partition",
    "s12_ctx400m_toe_hinge",
    "s12_ctx1p2km_spi_worm",
    "s12_ctx2p5km_multiphys",
    "s12_strike_tangent_sin2",
]


def _hessian_ridge_and_tangent(
    arr: np.ndarray,
    sigma: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute 2x2 Weingarten / Hessian principal ridge strength `(disc - tr)/2`,
    anisotropy, and principal ridge strike angle `theta in [0, pi)` (radians
    clockwise from North / row-upward axis).
    """
    sm = ndi.gaussian_filter(arr, sigma=sigma) if sigma > 0 else arr
    gy, gx = np.gradient(sm)
    hyy = np.gradient(gy, axis=0).astype(np.float32)
    hxx = np.gradient(gx, axis=1).astype(np.float32)
    hxy = (0.5 * (np.gradient(gy, axis=1) + np.gradient(gx, axis=0))).astype(np.float32)

    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, 2.0 * hxy).astype(np.float32)
    lam_ridge = (0.5 * (disc - tr)).astype(np.float32)
    aniso = (disc / (np.abs(tr) + disc + 1e-5)).astype(np.float32)

    # Normal to ridge is eigenvector of most negative Hessian eigenvalue `0.5*(tr - disc)`:
    # angle of normal `phi = 0.5 * arctan2(2*hxy, hxx - hyy)` in (x, y) coords;
    # tangent along ridge is perpendicular to normal. Convert to azimuth in [0, pi).
    normal_xy = 0.5 * np.arctan2(-2.0 * hxy, -(hxx - hyy) + 1e-12)
    # Tangent vector in (row=y, col=x): (-cos(normal_xy), sin(normal_xy))
    ty = -np.cos(normal_xy)
    tx = np.sin(normal_xy)
    strike_rad = (np.arctan2(tx, -ty) % math.pi).astype(np.float32)
    return lam_ridge, aniso, strike_rad


def _fft_potential_operators(
    arr: np.ndarray,
    footprint: np.ndarray,
    *,
    z_dz_m: float,
    upward_heights_m: tuple[float, ...] = (),
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Apply exact 2-D Laplace wavenumber operators `|k| exp(-z_dz |k|)` (1st
    vertical derivative in `unit / m`) and `exp(-z_up |k|)` (upward continuation)
    with reflect-padded edges to suppress periodic wrap-around artifacts.
    """
    pad = 48
    med = float(np.median(arr[footprint]))
    centered = (arr - med).astype(np.float32)
    padded = np.pad(centered, pad, mode="reflect")
    hp, wp = padded.shape

    ky = (2.0 * math.pi * np.fft.fftfreq(hp, d=100.0)).astype(np.float32)
    kx = (2.0 * math.pi * np.fft.rfftfreq(wp, d=100.0)).astype(np.float32)
    kk = np.hypot(ky[:, None], kx[None, :])

    spec = np.fft.rfft2(padded)
    dz_pad = np.fft.irfft2(spec * (kk * np.exp(-float(z_dz_m) * kk)), s=(hp, wp)).astype(np.float32)
    dz_out = dz_pad[pad : pad + arr.shape[0], pad : pad + arr.shape[1]].copy()

    up_outs: list[np.ndarray] = []
    for z_u in upward_heights_m:
        u_pad = np.fft.irfft2(spec * np.exp(-float(z_u) * kk), s=(hp, wp)).astype(np.float32)
        up_outs.append(u_pad[pad : pad + arr.shape[0], pad : pad + arr.shape[1]].copy())

    del spec, padded, kk
    return dz_out, up_outs


def build_or_load_s12_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed float32 Session 12 feature matrix `(N_fp, 25)`.

    100.0% derived from the official competition `training_features.tif` raster
    with zero fault-label input and < 900 MB transient RAM.
    """
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s12_spid_features_v1.dat"
    meta_path = cache_p / "s12_spid_features_v1.json"

    n_fp = int(footprint.sum())
    n_cols = len(S12_SPID_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == S12_SPID_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S12_SPID_FEATURE_NAMES), meta

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    # --- Pass 1: Gravity & Basement Potential-Field SPI + Multiscale Worms ---
    with rasterio.open(features_tif) as fsrc:
        b11 = DD._clean_band_edt(fsrc.read(11), footprint)
        b13 = DD._clean_band_edt(fsrc.read(13), footprint)
        b15 = np.maximum(DD._clean_band_edt(fsrc.read(15), footprint), 0.0)
        b18 = DD._clean_band_edt(fsrc.read(18), footprint)

    grav_dz, grav_ups = _fft_potential_operators(
        b13,
        footprint,
        z_dz_m=150.0,
        upward_heights_m=(100.0, 400.0, 1200.0),
    )
    gy13, gx13 = np.gradient(ndi.gaussian_filter(b13, sigma=1.2), 100.0)
    gh13 = (np.hypot(gy13, gx13) + 1e-6).astype(np.float32)
    del gy13, gx13, b13

    grav_true_tilt = np.arctan2(grav_dz, gh13).astype(np.float32)
    tgy, tgx = np.gradient(ndi.gaussian_filter(grav_true_tilt, sigma=0.8), 100.0)
    grav_spi_k = np.hypot(tgy, tgx).astype(np.float32)
    del tgy, tgx, gh13

    spi_shallow_break = np.log1p(b15 * grav_spi_k).astype(np.float32)

    worm_z_layers = []
    for gu in grav_ups:
        uy, ux = np.gradient(gu, 100.0)
        uh = np.hypot(uy, ux).astype(np.float32)
        worm_z_layers.append(DD._robust_z(uh, footprint))
    del grav_ups
    grav_worm_persist = ((worm_z_layers[0] + worm_z_layers[1] + worm_z_layers[2]) / 3.0).astype(np.float32)
    grav_worm_dip_shift = (worm_z_layers[0] - worm_z_layers[2]).astype(np.float32)
    del worm_z_layers

    # Basement-Step Hinge co-aligned with negative horizontal gravity gradient (-B11, -B18)
    b15_sm = ndi.gaussian_filter(b15, sigma=1.8)
    d15y, d15x = np.gradient(b15_sm, 100.0)
    d15_mag_m = np.hypot(d15y, d15x).astype(np.float32)
    base_step_grad = np.log1p(d15_mag_m * 100.0).astype(np.float32)
    gnorm = np.hypot(b11, b18) + 1e-5
    base_grav_coalign = ((d15y * (-b11) + d15x * (-b18)) / ((d15_mag_m + 1e-5) * gnorm)).astype(np.float32)
    base_hinge_joint = (np.maximum(base_grav_coalign, 0.0) * base_step_grad).astype(np.float32)

    # Marussi Eotvos summary for 2.5km corridor context
    b11_s = ndi.gaussian_filter(b11, sigma=1.2)
    b18_s = ndi.gaussian_filter(b18, sigma=1.2)
    eotvos_local = np.hypot(
        np.gradient(b18_s, axis=1) - np.gradient(b11_s, axis=0),
        np.gradient(b11_s, axis=1) + np.gradient(b18_s, axis=0),
    ).astype(np.float32)
    del b11, b18, b11_s, b18_s, b15_sm, d15y, d15x, d15_mag_m, gnorm

    mm[:, 0] = grav_dz[footprint]
    mm[:, 1] = grav_true_tilt[footprint]
    mm[:, 2] = grav_spi_k[footprint]
    mm[:, 3] = spi_shallow_break[footprint]
    mm[:, 4] = grav_worm_persist[footprint]
    mm[:, 5] = grav_worm_dip_shift[footprint]
    mm[:, 13] = base_step_grad[footprint]
    mm[:, 14] = base_grav_coalign[footprint]
    mm[:, 15] = base_hinge_joint[footprint]
    del grav_dz, grav_true_tilt, spi_shallow_break, grav_worm_dip_shift, base_grav_coalign
    gc.collect()

    # --- Pass 2: Exact 3-D Roest TMI Analytic Signal & True Pole-Reduced RTP SPI ---
    with rasterio.open(features_tif) as fsrc:
        b2 = DD._clean_band_edt(fsrc.read(2), footprint)
        b9 = DD._clean_band_edt(fsrc.read(9), footprint)
        b14 = DD._clean_band_edt(fsrc.read(14), footprint)

    gy14, gx14 = np.gradient(ndi.gaussian_filter(b14, sigma=1.0), 100.0)  # nT/m
    roest_tmi_as3d = np.sqrt(gx14 * gx14 + gy14 * gy14 + b9 * b9).astype(np.float32)  # exact nT/m!
    del gy14, gx14, b9, b14

    rtp_dz, _ = _fft_potential_operators(b2, footprint, z_dz_m=120.0)
    gy2, gx2 = np.gradient(ndi.gaussian_filter(b2, sigma=1.0), 100.0)  # nT/m
    gh2 = (np.hypot(gy2, gx2) + 1e-5).astype(np.float32)
    del gy2, gx2, b2

    rtp_true_tilt = np.arctan2(rtp_dz, gh2).astype(np.float32)
    rgy, rgx = np.gradient(ndi.gaussian_filter(rtp_true_tilt, sigma=0.8), 100.0)
    rtp_spi_k = np.hypot(rgy, rgx).astype(np.float32)
    remanence_phase_disc = np.abs(
        DD._robust_z(np.log1p(roest_tmi_as3d * 100.0), footprint)
        - DD._robust_z(np.log1p(gh2 * 100.0), footprint)
    ).astype(np.float32)
    del rtp_dz, gh2, rgy, rgx

    mm[:, 6] = np.log1p(roest_tmi_as3d * 100.0)[footprint]
    mm[:, 7] = rtp_true_tilt[footprint]
    mm[:, 8] = rtp_spi_k[footprint]
    mm[:, 9] = remanence_phase_disc[footprint]
    del roest_tmi_as3d, rtp_true_tilt, rtp_spi_k, remanence_phase_disc
    gc.collect()

    # --- Pass 3: Depth-Conditioned Conductivity Residual, Weingarten Curvatures & Strain ---
    with rasterio.open(features_tif) as fsrc:
        b4 = np.maximum(DD._clean_band_edt(fsrc.read(4), footprint), 0.0)
        b7 = np.maximum(DD._clean_band_edt(fsrc.read(7), footprint), 0.0)
        b8 = DD._clean_band_edt(fsrc.read(8), footprint)
        b12 = DD._clean_band_edt(fsrc.read(12), footprint)
        b17 = DD._clean_band_edt(fsrc.read(17), footprint)
        b19 = np.maximum(DD._clean_band_edt(fsrc.read(19), footprint), 0.0)

    # Unsupervised physical deconfounding of Band 17 on log1p(B15), log1p(B15)^2, and B12
    ld = np.log1p(b15[footprint]).astype(np.float64)
    el = (b12[footprint] / 500.0).astype(np.float64)
    design_sub = np.column_stack([
        np.ones(ld[::16].size, dtype=np.float64),
        ld[::16],
        ld[::16] ** 2,
        el[::16],
        ld[::16] * el[::16],
    ])
    coef, *_ = np.linalg.lstsq(design_sub, b17[footprint][::16].astype(np.float64), rcond=None)
    pred_cond_fp = (
        coef[0]
        + coef[1] * ld
        + coef[2] * (ld * ld)
        + coef[3] * el
        + coef[4] * (ld * el)
    ).astype(np.float32)
    del ld, el, design_sub, b15

    cond_res = np.zeros(footprint.shape, dtype=np.float32)
    cond_res[footprint] = b17[footprint] - pred_cond_fp
    cond_res = DD._clean_band_edt(cond_res, footprint)
    del pred_cond_fp, b17

    cond_res_grad = DD._grad_mag(cond_res, sigma=1.5)
    cond_res_ridge, _, _ = _hessian_ridge_and_tangent(cond_res, sigma=2.0)

    weingarten_toe_250m, _, strike_toe = _hessian_ridge_and_tangent(-b12, sigma=2.5)
    weingarten_toe_500m, _, _ = _hessian_ridge_and_tangent(-b12, sigma=5.0)
    del b12

    ls = np.log1p(b19)
    slp_hess_ridge_150m, _, strike_slp = _hessian_ridge_and_tangent(ls, sigma=1.5)
    slp_hess_ridge_400m, _, _ = _hessian_ridge_and_tangent(ls, sigma=4.0)
    del ls

    transtens_partition = (b7 * np.maximum(b8, 0.0) / (b4 + 1.0)).astype(np.float32)
    del b4, b7, b8

    # Multi-scale corridor envelopes (400 m, 1.2 km, 2.5 km)
    ctx400m_toe = ndi.gaussian_filter(np.maximum(weingarten_toe_250m, 0.0), sigma=4.0).astype(np.float32)
    spi_worm_combo = (
        0.55 * np.maximum(grav_worm_persist, 0.0)
        + 0.45 * np.maximum(DD._robust_z(grav_spi_k, footprint), 0.0)
    ).astype(np.float32)
    ctx1p2km_spi_worm = ndi.gaussian_filter(spi_worm_combo, sigma=12.0).astype(np.float32)

    mp_combo = (
        0.35 * np.maximum(DD._robust_z(eotvos_local, footprint), 0.0)
        + 0.35 * spi_worm_combo
        + 0.30 * np.maximum(DD._robust_z(base_hinge_joint, footprint), 0.0)
    ).astype(np.float32)
    ctx2p5km_multiphys = ndi.gaussian_filter(mp_combo, sigma=25.0).astype(np.float32)

    # Blend strike orientation between slope-ridge (where slope >= 4.5 deg) and toe-flexure
    strike_comb = np.where(b19 >= 4.5, strike_slp, strike_toe).astype(np.float32)
    # Encode periodic strike smoothly as sin(2*theta) in [-1, 1] for tree safety;
    # keep angle helper via `compute_spid_subsurface_and_strike` when steering.
    strike_sin2 = np.sin(2.0 * strike_comb).astype(np.float32)
    del b19, eotvos_local, grav_spi_k, grav_worm_persist, base_hinge_joint, base_step_grad
    del spi_worm_combo, mp_combo, strike_slp, strike_toe, strike_comb
    gc.collect()

    mm[:, 10] = cond_res[footprint]
    mm[:, 11] = cond_res_grad[footprint]
    mm[:, 12] = cond_res_ridge[footprint]
    mm[:, 16] = weingarten_toe_250m[footprint]
    mm[:, 17] = weingarten_toe_500m[footprint]
    mm[:, 18] = slp_hess_ridge_150m[footprint]
    mm[:, 19] = slp_hess_ridge_400m[footprint]
    mm[:, 20] = transtens_partition[footprint]
    mm[:, 21] = ctx400m_toe[footprint]
    mm[:, 22] = ctx1p2km_spi_worm[footprint]
    mm[:, 23] = ctx2p5km_multiphys[footprint]
    mm[:, 24] = strike_sin2[footprint]
    mm.flush()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": S12_SPID_FEATURE_NAMES,
        "licence_clean_100pct": True,
        "official_geodawn_only": True,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S12_SPID_FEATURE_NAMES), meta


def compute_spid_subsurface_and_strike_fields(
    X_static: np.memmap | np.ndarray,
    X_s11: np.memmap | np.ndarray,
    X_s12: np.memmap | np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute:
      1. `spid_edge`: label-free Subsurface SPI + Multiscale Worm + Depth-Deconfounded
         Conductivity + Basement-Step Hinge + Radiometric-TC + Weingarten Toe-Hinge
         structural field in `[0, 1]`.
      2. `piedmont_basin_mask`: concealed / low-slope piedmont & basin regime
         (`det_elev_slope < 6.0 deg` OR (`depth_to_base > 220 m` & `slope < 10.0 deg`)).
      3. `strike_bin_grid`: integer azimuth bin `0..5` (`0, 30, 60, 90, 120, 150 deg`)
         aligned with the local multi-physics structural tangent for steerable
         anisotropic strike continuation.
    """
    def _norm01(v: np.ndarray) -> np.ndarray:
        q45 = float(np.percentile(v[::20], 45))
        q95 = float(np.percentile(v[::20], 95))
        return np.clip((v - q45) / max(q95 - q45, 1e-6), 0.0, 1.0).astype(np.float32)

    # Pure S12 SPI + Upward Worm + 3D Roest + Depth-Conditioned Conductivity + Basement Hinge + Weingarten Toe
    spi_g = np.asarray(X_s12[:, 2], dtype=np.float32)
    spi_sb = np.asarray(X_s12[:, 3], dtype=np.float32)
    worm_g = np.asarray(X_s12[:, 4], dtype=np.float32)
    roest3 = np.asarray(X_s12[:, 6], dtype=np.float32)
    rtp_spi = np.asarray(X_s12[:, 8], dtype=np.float32)
    cnd_gr = np.asarray(X_s12[:, 11], dtype=np.float32)
    cnd_rg = np.asarray(X_s12[:, 12], dtype=np.float32)
    b_co = np.clip(np.asarray(X_s12[:, 14], dtype=np.float32), 0.0, None)
    b_hng = np.asarray(X_s12[:, 15], dtype=np.float32)
    w_toe = np.asarray(X_s12[:, 16], dtype=np.float32)
    tr_idx = np.asarray(X_s12[:, 20], dtype=np.float32)

    depth_b = np.asarray(X_static[:, 14], dtype=np.float32)
    slope_b = np.asarray(X_static[:, 18], dtype=np.float32)

    s_pot_spi = (
        0.42 * _norm01(worm_g)
        + 0.38 * np.maximum(_norm01(spi_g), _norm01(spi_sb))
        + 0.20 * _norm01(rtp_spi)
    )
    s_subsurf_em_mag = (
        0.52 * np.maximum(_norm01(cnd_rg), _norm01(cnd_gr))
        + 0.33 * _norm01(roest3)
        + 0.15 * _norm01(tr_idx)
    )
    s_hinge_toe = (
        0.46 * _norm01(b_hng)
        + 0.24 * _norm01(b_co)
        + 0.30 * _norm01(w_toe)
    )

    e_fp = np.clip(0.38 * s_pot_spi + 0.34 * s_subsurf_em_mag + 0.28 * s_hinge_toe, 0.0, 1.0)
    spid_edge = np.zeros(footprint.shape, dtype=np.float32)
    spid_edge[footprint] = e_fp

    pied_fp = (slope_b < 6.0) | ((depth_b > 220.0) & (slope_b < 10.0))
    pied_mask = np.zeros(footprint.shape, dtype=bool)
    pied_mask[footprint] = pied_fp

    # Compute 6-bin strike tangent orientation directly on `spid_edge + 0.5*norm_slope`
    slope_grid = np.zeros(footprint.shape, dtype=np.float32)
    slope_grid[footprint] = _norm01(slope_b)
    guide = (0.60 * spid_edge + 0.40 * slope_grid).astype(np.float32)
    _, _, strike_rad = _hessian_ridge_and_tangent(guide, sigma=1.6)
    strike_bin = (np.floor(((np.degrees(strike_rad) + 15.0) % 180.0) / 30.0).astype(np.int8)) % 6
    return spid_edge, pied_mask, strike_bin


def steerable_tangent_continuation(
    prob_grid: np.ndarray,
    strike_bin_grid: np.ndarray,
    footprint: np.ndarray,
    *,
    blend: float = 0.34,
    length_px: int = 7,
    sigma_along: float = 2.4,
    sigma_perp: float = 0.58,
) -> np.ndarray:
    """Smooth `prob_grid` ONLY along the local 1-D structural strike tangent
    `strike_bin_grid in {0..5}`, bridging 200-500 m alluvial washouts along concealed
    strands without blurring perpendicular to the fault axis.
    """
    if blend <= 0.0:
        return prob_grid.astype(np.float32, copy=True)

    half = length_px // 2
    yy, xx = np.mgrid[-half : half + 1, -half : half + 1].astype(np.float32)
    steered = np.zeros_like(prob_grid, dtype=np.float32)

    for b_idx in range(6):
        az_deg = float(b_idx * 30)
        rad = math.radians(az_deg)
        sy, sx = -math.cos(rad), math.sin(rad)
        ny, nx = sx, -sy
        s_c = yy * sy + xx * sx
        n_c = yy * ny + xx * nx
        kern = np.exp(-0.5 * ((s_c / sigma_along) ** 2 + (n_c / sigma_perp) ** 2)).astype(np.float32)
        kern /= float(kern.sum())
        resp = ndi.convolve(prob_grid, kern, mode="nearest")
        mask_b = strike_bin_grid == b_idx
        steered[mask_b] = resp[mask_b]

    out = ((1.0 - float(blend)) * prob_grid + float(blend) * steered).astype(np.float32)
    out[~footprint] = 0.0
    return np.clip(out, 0.0, 0.9999)


def fit_and_predict_s12_oof_fold(
    X_static: np.memmap,
    static_cols: list[int],
    X_s11: np.memmap,
    s11_cols: list[int],
    X_s12: np.memmap,
    s12_cols: list[int],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    use_basin_moe: bool = False,
    flank_neg_frac: float = 0.22,
    seed: int = 120,
    max_neg_samples: int = 180_000,
) -> np.ndarray:
    """Train out-of-fold multi-physics fault probability model strictly on
    `visible_faults` vs safe buffered negatives outside `exclude_mask`:
      - Samples `(1 - flank_neg_frac)` uniform background negatives (`d_vis > 3.5 px`)
        plus `flank_neg_frac` off-kernel near-flank negatives (`4.2 <= d_vis <= 11.0 px`,
        weighted at `0.68`) to sharpen sub-300 m axial localization.
      - When `use_basin_moe=True` (`H12-3`), fits a dedicated **Slope-Deconfounded
        Subsurface Basin Expert** strictly on low-slope/basin terrain (`slope < 7.5 deg`
        OR `depth > 250 m`) with raw topographic slope/scarp columns removed, blended
        via prior-normalized log-odds with the global multi-physics ensemble.
    """
    rng = np.random.default_rng(seed)
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis_grid = ndi.distance_transform_edt(~visible_faults)
    d_vis_fp = d_vis_grid[footprint]
    del d_vis_grid

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    flank_pool = np.flatnonzero((~vis_fp) & (~excl_fp) & (d_vis_fp >= 4.2) & (d_vis_fp <= 11.0))
    far_pool = np.flatnonzero((~vis_fp) & (~excl_fp) & (d_vis_fp > 11.0))

    n_flank_target = int(round(max_neg_samples * float(flank_neg_frac)))
    n_far_target = max_neg_samples - n_flank_target

    if flank_pool.size > n_flank_target and n_flank_target > 0:
        flank_idx = np.sort(rng.choice(flank_pool, size=n_flank_target, replace=False))
    else:
        flank_idx = flank_pool

    rem_needed = max_neg_samples - flank_idx.size
    if far_pool.size > rem_needed:
        far_idx = np.sort(rng.choice(far_pool, size=rem_needed, replace=False))
    else:
        far_idx = far_pool

    train_idx = np.concatenate([pos_idx, flank_idx, far_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(flank_idx.size + far_idx.size, dtype=np.int32),
    ])
    sample_w = np.concatenate([
        np.ones(pos_idx.size, dtype=np.float32),
        np.full(flank_idx.size, 0.68, dtype=np.float32),
        np.ones(far_idx.size, dtype=np.float32),
    ])

    def _assemble_rows(idx_or_slice) -> np.ndarray:
        parts = []
        if static_cols:
            parts.append(np.asarray(X_static[idx_or_slice][:, static_cols], dtype=np.float32))
        if s11_cols:
            parts.append(np.asarray(X_s11[idx_or_slice][:, s11_cols], dtype=np.float32))
        if s12_cols:
            parts.append(np.asarray(X_s12[idx_or_slice][:, s12_cols], dtype=np.float32))
        return np.hstack(parts)

    X_tr = _assemble_rows(train_idx)

    hgb_deep = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=220,
        max_leaf_nodes=43,
        min_samples_leaf=70,
        l2_regularization=3.2,
        random_state=seed,
    )
    hgb_deep.fit(X_tr, y_train, sample_weight=sample_w)

    hgb_reg = HistGradientBoostingClassifier(
        learning_rate=0.045,
        max_iter=210,
        max_leaf_nodes=27,
        min_samples_leaf=130,
        l2_regularization=6.0,
        random_state=seed + 17,
    )
    hgb_reg.fit(X_tr, y_train, sample_weight=sample_w)

    scaler_g = StandardScaler()
    X_tr_sc = np.clip(scaler_g.fit_transform(X_tr), -6.0, 6.0)
    lr_g = LogisticRegression(C=0.20, max_iter=300, random_state=seed)
    lr_g.fit(X_tr_sc, y_train, sample_weight=sample_w)
    pi_global = float(np.average(y_train, weights=sample_w))
    del X_tr, X_tr_sc
    gc.collect()

    # Optional H12-3 Subsurface-First + Weingarten Scarp-Toe Mixture-of-Experts
    basin_models = None
    if use_basin_moe:
        col_meta = (
            [("h91", c) for c in static_cols]
            + [("s11", c) for c in s11_cols]
            + [("s12", c) for c in s12_cols]
        )
        sub_allowed = (
            {("h91", c) for c in SUBSURF_H91_COLS}
            | {("s11", c) for c in SUBSURF_S11_COLS}
            | {("s12", c) for c in SUBSURF_S12_COLS}
        )
        sub_keep = [j for j, tag in enumerate(col_meta) if tag in sub_allowed]

        # Expert 1a: Full-domain pure slope-free, elevation-free subsurface HGB + LR
        X_sub_all = _assemble_rows(train_idx)[:, sub_keep]
        hgb_sub_all = HistGradientBoostingClassifier(
            learning_rate=0.048,
            max_iter=215,
            max_leaf_nodes=37,
            min_samples_leaf=85,
            l2_regularization=4.0,
            random_state=seed + 31,
        )
        hgb_sub_all.fit(X_sub_all, y_train, sample_weight=sample_w)
        scaler_sub = StandardScaler()
        X_sub_sc = np.clip(scaler_sub.fit_transform(X_sub_all), -6.0, 6.0)
        lr_sub = LogisticRegression(C=0.18, max_iter=300, random_state=seed + 31)
        lr_sub.fit(X_sub_sc, y_train, sample_weight=sample_w)
        pi_sub = float(np.average(y_train, weights=sample_w))
        del X_sub_all, X_sub_sc
        gc.collect()

        # Expert 1b: Concealed-basin specialized slope-free HGB (`slope < 6.5 deg` or `B15 > 220 m`)
        slope_all_fp = np.asarray(X_static[:, 18], dtype=np.float32)
        depth_all_fp = np.asarray(X_static[:, 14], dtype=np.float32)
        in_basin_tr = (slope_all_fp[train_idx] < 6.5) | (depth_all_fp[train_idx] > 220.0)
        b_tr_idx = train_idx[in_basin_tr]
        y_b = y_train[in_basin_tr]
        w_b = sample_w[in_basin_tr]
        hgb_basin = None
        if int((y_b == 1).sum()) >= 500 and int((y_b == 0).sum()) >= 2_000:
            X_b = _assemble_rows(b_tr_idx)[:, sub_keep]
            hgb_basin = HistGradientBoostingClassifier(
                learning_rate=0.045,
                max_iter=200,
                max_leaf_nodes=31,
                min_samples_leaf=95,
                l2_regularization=4.5,
                random_state=seed + 41,
            )
            hgb_basin.fit(X_b, y_b, sample_weight=w_b)
            del X_b
            gc.collect()
        basin_models = (hgb_sub_all, scaler_sub, lr_sub, hgb_basin, sub_keep, pi_sub)

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 400_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = _assemble_rows(slice(s, e))
        p1 = hgb_deep.predict_proba(Xc)[:, 1]
        p2 = hgb_reg.predict_proba(Xc)[:, 1]
        p3 = lr_g.predict_proba(np.clip(scaler_g.transform(Xc), -6.0, 6.0))[:, 1]
        p_glob = np.clip(0.46 * p1 + 0.36 * p2 + 0.18 * p3, 1e-6, 1.0 - 1e-6)

        if basin_models is not None:
            hgb_sa, sc_s, lr_s, hgb_b, sub_keep, pi_s = basin_models
            Xcb = Xc[:, sub_keep]
            ps1 = hgb_sa.predict_proba(Xcb)[:, 1]
            ps2 = lr_s.predict_proba(np.clip(sc_s.transform(Xcb), -6.0, 6.0))[:, 1]
            if hgb_b is not None:
                ps3 = hgb_b.predict_proba(Xcb)[:, 1]
                p_sub = np.clip(0.48 * ps1 + 0.34 * ps3 + 0.18 * ps2, 1e-6, 1.0 - 1e-6)
            else:
                p_sub = np.clip(0.80 * ps1 + 0.20 * ps2, 1e-6, 1.0 - 1e-6)

            # Regime-conditioned log-odds gating: 0.42 subsurface corroboration on steep range
            # fronts, rising smoothly to 0.78 pure subsurface authority on flat basins (< 5 deg)
            slp_c = np.asarray(X_static[s:e, 18], dtype=np.float32)
            gate_sub = 0.42 + 0.36 / (1.0 + np.exp((slp_c - 5.2) / 1.4))

            lo_g = np.log(p_glob / (1.0 - p_glob)) - math.log(pi_global / (1.0 - pi_global))
            lo_s = np.log(p_sub / (1.0 - p_sub)) - math.log(pi_s / (1.0 - pi_s))
            lo_mix = (1.0 - gate_sub) * lo_g + gate_sub * lo_s + math.log(pi_global / (1.0 - pi_global))
            p_final = 1.0 / (1.0 + np.exp(-np.clip(lo_mix, -12.0, 12.0)))
            pred_fp[s:e] = p_final.astype(np.float32)
        else:
            pred_fp[s:e] = p_glob.astype(np.float32)

    out_grid = np.zeros(footprint.shape, dtype=np.float32)
    out_grid[footprint] = pred_fp
    return out_grid


def compute_noisy_or_self_credit(
    q_cal: np.ndarray,
    radius_px: float = 3.0,
) -> np.ndarray:
    """Compute exact 300 m triangular-kernel noisy-OR expected self-credit:
        `m_hat(x) = 1 - prod_{d <= 3} (1 - q_cal(x + d) * k(d))`
    representing `E[max_{g in G} k(d(x, g))]` in the DTI denominator
    `0.2 * (T + S - M) + 0.8 * |G|`.
    """
    r = int(round(radius_px))
    h, w = q_cal.shape
    q_pad = np.pad(np.clip(q_cal, 0.0, 0.95), r, mode="constant", constant_values=0.0)
    log_miss = np.zeros((h, w), dtype=np.float32)

    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            dist = math.hypot(dy, dx)
            if dist >= radius_px:
                continue
            kv = float(1.0 - dist / radius_px)
            sub = q_pad[r + dy : r + dy + h, r + dx : r + dx + w]
            log_miss += np.log1p(-np.clip(sub * kv, 0.0, 0.99)).astype(np.float32)

    return (1.0 - np.exp(log_miss)).astype(np.float32)


def _dinkelbach_submodular_select(
    truth_weight: np.ndarray,
    fp_cost: np.ndarray,
    cand_rank: np.ndarray,
    eligible_mask: np.ndarray,
    n_dots: int,
    *,
    min_spacing_px: float = 2.60,
    pool_multiplier: int = 8,
    existing_dots: np.ndarray | None = None,
) -> np.ndarray:
    """Minoux (1978) CELF lazy-greedy submodular optimization of the exact
    linearized Bayes-Dinkelbach DTI objective:
        `gain(x | S) = sum_{y in B_3(x)} W(y) * max(0, k(x,y) - C_S(y)) - fp_cost(x)`
    stopping either when `n_dots` are emitted OR when marginal `gain(x | S) <= 0`.
    """
    h, w = truth_weight.shape
    if n_dots <= 0:
        return np.zeros((h, w), dtype=np.float32) if existing_dots is None else existing_dots.copy()

    elig_flat = np.flatnonzero(eligible_mask & (truth_weight > 0))
    if elig_flat.size == 0:
        return np.zeros((h, w), dtype=np.float32) if existing_dots is None else existing_dots.copy()

    m_pool = min(elig_flat.size, max(n_dots * pool_multiplier, n_dots + 2_500))
    ranks_sub = cand_rank.ravel()[elig_flat]
    if elig_flat.size > m_pool:
        top_part = np.argpartition(-ranks_sub, m_pool - 1)[:m_pool]
        cand_flat = elig_flat[top_part]
    else:
        cand_flat = elig_flat

    yy, xx = np.mgrid[-3:4, -3:4]
    K = np.clip(1.0 - np.hypot(yy, xx) / 3.0, 0.0, None).astype(np.float32)
    nz_k = K > 0
    ky, kx, kv = yy[nz_k] + 3, xx[nz_k] + 3, K[nz_k]

    W_pad = np.pad(truth_weight, 3, mode="constant", constant_values=0.0).astype(np.float32)
    cy = (cand_flat // w).astype(np.int32)
    cx = (cand_flat % w).astype(np.int32)
    f_pen = fp_cost.ravel()[cand_flat].astype(np.float32)

    cand_init = (W_pad[cy[:, None] + ky[None, :], cx[:, None] + kx[None, :]] @ kv) - f_pen
    keep = cand_init > 0.0
    if not keep.any():
        return np.zeros((h, w), dtype=np.float32) if existing_dots is None else existing_dots.copy()

    cand_flat = cand_flat[keep]
    cand_init = cand_init[keep]
    cy = cy[keep]
    cx = cx[keep]
    f_pen = f_pen[keep]

    order = np.lexsort((cand_flat, -cand_init))
    cand_flat = cand_flat[order]
    cand_init = cand_init[order]
    cy = cy[order]
    cx = cx[order]
    f_pen = f_pen[order]

    cov_pad = np.zeros((h + 6, w + 6), dtype=np.float32)
    rad = int(math.ceil(min_spacing_px))
    oy, ox = np.mgrid[-rad : rad + 1, -rad : rad + 1]
    disk = np.hypot(oy, ox) < float(min_spacing_px)
    blocked = np.zeros((h + 2 * rad, w + 2 * rad), dtype=bool)

    out = np.zeros((h, w), dtype=np.float32)
    if existing_dots is not None:
        out[:] = existing_dots
        ey, ex = np.nonzero(existing_dots > 0)
        for y0, x0 in zip(ey, ex):
            y, x = int(y0), int(x0)
            np.maximum(cov_pad[y : y + 7, x : x + 7], K, out=cov_pad[y : y + 7, x : x + 7])
            blocked[y : y + 2 * rad + 1, x : x + 2 * rad + 1] |= disk

    heap: list[tuple[float, int, int]] = [
        (-float(cand_init[i]), int(cand_flat[i]), i) for i in range(cand_flat.size)
    ]
    heapq.heapify(heap)

    picked = 0
    while picked < n_dots and heap:
        neg_ub, f_idx, i = heapq.heappop(heap)
        if -neg_ub <= 0.0:
            break
        y, x = int(cy[i]), int(cx[i])
        if blocked[y + rad, x + rad]:
            continue
        c_view = cov_pad[y : y + 7, x : x + 7]
        gain = float(np.sum(W_pad[y : y + 7, x : x + 7] * np.maximum(K - c_view, 0.0))) - float(f_pen[i])
        if gain <= 0.0:
            continue
        if not heap or (-gain <= heap[0][0] + 1e-6):
            np.maximum(c_view, K, out=c_view)
            blocked[y : y + 2 * rad + 1, x : x + 2 * rad + 1] |= disk
            out[y, x] = 1.0
            picked += 1
        else:
            heapq.heappush(heap, (-gain, f_idx, i))

    return out


def spid_dinkelbach_submodular_emit(
    surface: np.ndarray,
    spid_edge_field: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    strike_bin_grid: np.ndarray | None = None,
    eligible_mask: np.ndarray,
    max_dots: int = 47_500,
    gamma: float = 1.18,
    spid_weight: float = 0.50,
    piedmont_quota_frac: float = 0.34,
    prior_ratio: float = 0.052,
    dinkelbach_fp_lambda: float = 0.035,
    min_spacing_px: float = 2.55,
    tangent_steer_blend: float = 0.0,
    pool_multiplier: int = 8,
) -> np.ndarray:
    """Two-Regime Self-Credit Bayes-Dinkelbach 300 m Submodular DTI Allocator:
      1. Optional steerable tangent continuation along local structural strike
         (`tangent_steer_blend > 0`).
      2. Exact 300 m noisy-OR self-credit `m_hat(x)` reducing false-positive
         penalty `(1 - m_hat(x))` on coherent multi-pixel fault corridors relative
         to isolated point anomalies.
      3. Balanced Range-Front + Concealed-Piedmont/Basin allocation (`piedmont_quota_frac`)
         ensuring sub-alluvial SPI/Conductivity/Basement-Hinge corridors are covered
         rather than drowned out by steep mountain scarps.
    """
    h, w = surface.shape
    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 0.9999).astype(np.float32)
    if tangent_steer_blend > 0.0 and strike_bin_grid is not None:
        fp_infer = (p > 0) | eligible_mask
        p = steerable_tangent_continuation(p, strike_bin_grid, fp_infer, blend=tangent_steer_blend)

    e_spid = np.clip(np.nan_to_num(spid_edge_field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    q_base = ((prior_ratio * p) / (prior_ratio * p + (1.0 - p) + 1e-8)).astype(np.float32)
    q = np.clip(q_base * (1.0 + float(spid_weight) * e_spid), 0.0, 0.95).astype(np.float32)

    # 1-D directional ridge masks on `q` and on `e_spid`
    qp = np.pad(q, 2, mode="edge")
    c = qp[2 : h + 2, 2 : w + 2]
    is_q_ridge = (
        ((c >= qp[1 : h + 1, 2 : w + 2]) & (c >= qp[3 : h + 3, 2 : w + 2]) & (c >= qp[0:h, 2 : w + 2]) & (c >= qp[4 : h + 4, 2 : w + 2]))
        | ((c >= qp[2 : h + 2, 1 : w + 1]) & (c >= qp[2 : h + 2, 3 : w + 3]) & (c >= qp[2 : h + 2, 0:w]) & (c >= qp[2 : h + 2, 4 : w + 4]))
        | ((c >= qp[1 : h + 1, 1 : w + 1]) & (c >= qp[3 : h + 3, 3 : w + 3]) & (c >= qp[0:h, 0:w]) & (c >= qp[4 : h + 4, 4 : w + 4]))
        | ((c >= qp[1 : h + 1, 3 : w + 3]) & (c >= qp[3 : h + 3, 1 : w + 1]) & (c >= qp[0:h, 4 : w + 4]) & (c >= qp[4 : h + 4, 0:w]))
    )

    ep = np.pad(e_spid, 1, mode="edge")
    ec = ep[1 : h + 1, 1 : w + 1]
    is_spid_ridge = (
        ((ec >= ep[0:h, 1 : w + 1]) & (ec >= ep[2 : h + 2, 1 : w + 1]))
        | ((ec >= ep[1 : h + 1, 0:w]) & (ec >= ep[1 : h + 1, 2 : w + 2]))
        | ((ec >= ep[0:h, 0:w]) & (ec >= ep[2 : h + 2, 2 : w + 2]))
        | ((ec >= ep[0:h, 2 : w + 2]) & (ec >= ep[2 : h + 2, 0:w]))
    )

    elig_pos_q = q[eligible_mask & (q > 0)]
    if elig_pos_q.size == 0 or max_dots <= 0:
        return np.zeros((h, w), dtype=np.float32)

    if elig_pos_q.size > max_dots * 15:
        keep_frac = min(0.32, max(float(max_dots * 17) / float(elig_pos_q.size), 0.06))
        q_floor = float(np.quantile(elig_pos_q, 1.0 - keep_frac))
    else:
        q_floor = 0.0

    q_excess = np.maximum(q - q_floor, 0.0)
    m_self = compute_noisy_or_self_credit(q * 0.45, radius_px=3.0)

    ridge_mult_1 = np.where(is_q_ridge, 1.0, 0.30).astype(np.float32)
    w_primary = np.where(
        eligible_mask,
        1000.0 * (q_excess ** float(gamma)) * ridge_mult_1,
        0.0,
    ).astype(np.float32)

    # Scale Dinkelbach FP penalty consistently with `1000 * q_excess^gamma` units
    w_pos_vals = w_primary[w_primary > 0]
    med_w = float(np.percentile(w_pos_vals[::10], 60)) if w_pos_vals.size > 20 else 0.0
    fp_cost_1 = (float(dinkelbach_fp_lambda) * med_w * (1.0 - m_self)).astype(np.float32)

    n_primary = int(round(max_dots * (1.0 - float(piedmont_quota_frac))))
    n_piedmont = max_dots - n_primary

    dots_stage1 = _dinkelbach_submodular_select(
        w_primary,
        fp_cost_1,
        q * np.where(is_q_ridge, 1.18, 0.85) * (0.65 + 0.35 * m_self),
        eligible_mask,
        n_primary,
        min_spacing_px=min_spacing_px,
        pool_multiplier=pool_multiplier,
        existing_dots=None,
    )

    if n_piedmont <= 0:
        return dots_stage1

    oy3, ox3 = np.mgrid[-4:5, -4:5]
    disk_3p3 = np.hypot(oy3, ox3) <= 3.30
    near_stage1 = ndi.binary_dilation(dots_stage1 > 0, structure=disk_3p3)
    pied_elig = eligible_mask & piedmont_mask & (~near_stage1) & (e_spid >= 0.20)

    # Regime-local quantile floor inside `pied_elig` so steep mountain-front tails
    # do not zero out genuine concealed intrabasinal SPI / conductivity / hinge corridors!
    pied_q_vals = q[pied_elig & (q > 0)]
    if pied_q_vals.size > n_piedmont * 10:
        pied_keep = min(0.40, max(float(n_piedmont * 14) / float(pied_q_vals.size), 0.10))
        q_floor_pied = float(np.quantile(pied_q_vals, 1.0 - pied_keep))
    else:
        q_floor_pied = 0.0
    q_excess_pied = np.maximum(q - q_floor_pied, 0.0)

    ridge_mult_2 = np.where(is_spid_ridge, 1.22, np.where(is_q_ridge, 0.88, 0.24)).astype(np.float32)
    w_piedmont = np.where(
        pied_elig,
        1000.0 * (q_excess_pied ** float(gamma * 0.84)) * ((0.20 + e_spid) ** 1.18) * ridge_mult_2,
        0.0,
    ).astype(np.float32)

    wp_vals = w_piedmont[w_piedmont > 0]
    med_wp = float(np.percentile(wp_vals[::10], 55)) if wp_vals.size > 20 else 0.0
    fp_cost_2 = (float(dinkelbach_fp_lambda) * 0.85 * med_wp * (1.0 - m_self)).astype(np.float32)

    dots_final = _dinkelbach_submodular_select(
        w_piedmont,
        fp_cost_2,
        (q_excess_pied ** 0.80) * ((0.20 + e_spid) ** 1.18) * ridge_mult_2 * (0.65 + 0.35 * m_self),
        pied_elig,
        n_piedmont,
        min_spacing_px=min_spacing_px + 0.25,
        pool_multiplier=pool_multiplier,
        existing_dots=dots_stage1,
    )
    return dots_final
