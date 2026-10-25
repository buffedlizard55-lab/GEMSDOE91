"""S17-LFTG: 3-D Laplace Full-Tensor Gravity, Azimuthal Seam-Free Magnetics/Radiometrics,
Accommodation-Zone Dip-Reversal & Prior-Calibrated Dual-Specialist Auto-Context.

Implements preregistered hypotheses H17-1 (LFTG), H17-2 (SACR), H17-3 (CRBZ), and
H17-4 (PCAC) from `docs/HYPOTHESES_S17.md`:
  - All 20 `S17_LFTG_FEATURE_NAMES` columns are strictly local (`<= 1.4 km` operators
    with spectral regional-bowl removal `lambda <= 24 km`), 100% licence-clean, and
    100% bitwise independent of `Band 12` (`det_elev`) and `Band 19` (`det_elev_slope`).
  - Uses single-precision (`float32` / `complex64`) `scipy.fft.rfft2` with reflective
    padding so peak memory remains well inside the 3.8 GiB sandbox budget.
  - Contains no holdout labels, registry rasters, prior-submission pixels, or private
    metric fork; delegates scoring and GeoTIFF/ZIP writing to shared repo modules.
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import fft as sfft
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from gems91 import dd_vtc_pu as DD
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import scgf15 as SCGF
from gems91 import spac_coda as SC

FeatureBlock = tuple[np.ndarray, Sequence[int]]

PIXEL_M: float = 100.0
PRIOR_PI0: float = 0.022

H17_1_LFTG_NAMES: list[str] = [
    "lftg17_grav_gz_200m",
    "lftg17_grav_gzz_250m",
    "lftg17_wijns_cos_theta_200m",
    "lftg17_wijns_cos_theta_600m",
    "lftg17_cooper_hyperbolic_tilt",
    "lftg17_pedersen_q2d_purity",
    "lftg17_listric_dip_asymmetry",
    "lftg17_theta_worm_persist",
]

H17_2_SACR_NAMES: list[str] = [
    "lftg17_rtp_destriped_tilt",
    "lftg17_rtp_destriped_cos_theta",
    "lftg17_tmi_drape_destriped_grad",
    "lftg17_rad_tc_destriped_grad",
    "lftg17_mag_seam_noise_ratio",
    "lftg17_grav_mag_destriped_concord",
]

H17_3_CRBZ_NAMES: list[str] = [
    "lftg17_accomm_grav_dip_reversal",
    "lftg17_accomm_b15_hinge_reversal",
    "lftg17_seamfree_mag_destruction",
    "lftg17_subsurface_clay_dipole",
    "lftg17_swarm_dilatation_conduit",
    "lftg17_deep_cover_concealed_crest",
]

S17_LFTG_FEATURE_NAMES: list[str] = (
    H17_1_LFTG_NAMES + H17_2_SACR_NAMES + H17_3_CRBZ_NAMES
)

# Clean local columns from cached Static (49), S11 (16), and PTHA (20):
# Excludes legacy S10 approximations X_static[24..30, 32], regional bowls X_static[34..43],
# and B10 sign-inverted columns X_static[47] & X_ptha[16, 18, 19] (IR-91-S14-01 / IR-91-S15-07).
CLEAN_STATIC_COLS: list[int] = list(range(24)) + [31, 33, 44, 45, 46, 48]
CLEAN_S11_COLS: list[int] = list(range(16))
CLEAN_PTHA_COLS: list[int] = list(range(16)) + [17]
ALL_LFTG17_COLS: list[int] = list(range(len(S17_LFTG_FEATURE_NAMES)))


def select_subsurface_cols(col_indices: Sequence[int], all_names: Sequence[str]) -> list[int]:
    """Filter `col_indices` to columns strictly absent from `SCGF.STRICT_TOPO_FEATURE_NAMES`."""
    return [int(c) for c in col_indices if all_names[int(c)] not in SCGF.STRICT_TOPO_FEATURE_NAMES]


def _robust_z_fp(vals_fp: np.ndarray) -> np.ndarray:
    med = float(np.median(vals_fp))
    mad = float(np.median(np.abs(vals_fp - med))) * 1.4826 + 1e-5
    return np.clip((vals_fp - med) / mad, -8.0, 8.0).astype(np.float32)


def _robust_pos_01_2d(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = arr[footprint]
    p50 = float(np.percentile(vals, 50.0))
    p98 = float(np.percentile(vals, 98.0))
    scale = max(p98 - p50, 1e-5)
    out = np.zeros(arr.shape, dtype=np.float32)
    out[footprint] = np.clip((vals - p50) / scale, 0.0, 2.5).astype(np.float32) / np.float32(2.5)
    return out


def _fft_pad_grid(
    field_2d: np.ndarray, pad: int = 96, workers: int = 2
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, int], tuple[int, int], int]:
    """Reflect-pad a float32 2-D grid and return single-precision rfft2 + `(ky, kx)` grids in rad/m."""
    arr = np.asarray(field_2d, dtype=np.float32)
    h, w = arr.shape
    ap = np.pad(arr, pad, mode="reflect")
    ph, pw = ap.shape
    nh = int(sfft.next_fast_len(ph))
    nw = int(sfft.next_fast_len(pw))
    spec = sfft.rfft2(ap, s=(nh, nw), workers=workers)
    del ap
    ky = (2.0 * np.pi * sfft.fftfreq(nh, d=PIXEL_M)).astype(np.float32)[:, None]
    kx = (2.0 * np.pi * sfft.rfftfreq(nw, d=PIXEL_M)).astype(np.float32)[None, :]
    return spec, ky, kx, (nh, nw), (ph, pw), pad


def _ifft_unpad(
    spec: np.ndarray,
    fft_shape: tuple[int, int],
    pad_shape: tuple[int, int],
    orig_shape: tuple[int, int],
    pad: int,
    workers: int = 2,
) -> np.ndarray:
    """Invert single-precision rfft2 and crop back to `orig_shape` as float32."""
    rec = sfft.irfft2(spec, s=fft_shape, workers=workers)
    ph, pw = pad_shape
    h, w = orig_shape
    out = np.ascontiguousarray(rec[:ph, :pw][pad : pad + h, pad : pad + w], dtype=np.float32)
    del rec
    return out


def compute_laplace_full_tensor_gravity(
    grav_2d: np.ndarray,
    footprint: np.ndarray,
    *,
    z_shallow_m: float = 200.0,
    z_mid_m: float = 450.0,
    z_deep_m: float = 800.0,
    hp_wavelength_m: float = 24_000.0,
    pad: int = 96,
    workers: int = 2,
) -> dict[str, np.ndarray]:
    """Compute exact 3-D Laplace Full-Tensor Gravity (`Gamma_ij`), Wijns Theta-Map,
    Cooper-Cowan Hyperbolic Tilt, and Pedersen-Rasmussen 2D Purity (`Q_2D = 1 - |I|`).

    Because gravitational potential `U` satisfies `nabla^2 U = 0` in the source-free
    upper half-space (`z <= 0`), the vertical gravity derivative `G_z = dG/dz` and
    full symmetric trace-free 3x3 Eötvös tensor `Gamma_ij` are exact spectral operators
    of `G = dU/dz` (`Band 13 iso_grav_anom`).
    """
    orig_shape = grav_2d.shape
    spec, ky, kx, fft_shape, pad_shape, p = _fft_pad_grid(grav_2d, pad=pad, workers=workers)
    kr = np.hypot(ky, kx).astype(np.float32)

    # Smooth Gaussian high-pass taper removes >24 km regional Moho/isostatic bowls
    k_cut = np.float32(2.0 * np.pi / max(hp_wavelength_m, 1000.0))
    hp = (1.0 - np.exp(-((kr / k_cut) ** 2))).astype(np.float32)
    hp[0, 0] = 0.0

    att_s = (hp * np.exp(-kr * np.float32(z_shallow_m))).astype(np.float32)
    att_m = (hp * np.exp(-kr * np.float32(z_mid_m))).astype(np.float32)
    att_d = (hp * np.exp(-kr * np.float32(z_deep_m))).astype(np.float32)
    del hp

    # First derivatives at z_shallow_m: G_x, G_y, G_z
    gx_s = _ifft_unpad(spec * (1j * kx * att_s), fft_shape, pad_shape, orig_shape, p, workers)
    gy_s = _ifft_unpad(spec * (1j * ky * att_s), fft_shape, pad_shape, orig_shape, p, workers)
    gz_s = _ifft_unpad(spec * (kr * att_s), fft_shape, pad_shape, orig_shape, p, workers)
    gh_s = np.hypot(gx_s, gy_s).astype(np.float32)

    eps_s = np.float32(float(np.percentile(gh_s[footprint], 20.0)) * 0.25 + 1e-6)
    cos_theta_s = (gh_s / np.sqrt(gh_s * gh_s + gz_s * gz_s + eps_s * eps_s)).astype(np.float32)
    strike_psi_g = np.arctan2(-gx_s, gy_s).astype(np.float32)

    # Listric dip-migration asymmetry along -grad_H G / ||grad_H G|| (+/- 3 px = +/- 300 m)
    gh_norm = np.maximum(gh_s, eps_s)
    ux = (-gx_s / gh_norm).astype(np.float32)
    uy = (-gy_s / gh_norm).astype(np.float32)
    del gx_s, gy_s, gh_norm
    rr, cc = np.indices(orig_shape, dtype=np.float32)
    gz_abs = np.abs(gz_s).astype(np.float32)
    up_coords = np.array(
        [
            np.clip(rr + np.float32(3.0) * uy, 0, orig_shape[0] - 1),
            np.clip(cc + np.float32(3.0) * ux, 0, orig_shape[1] - 1),
        ],
        dtype=np.float32,
    )
    dn_coords = np.array(
        [
            np.clip(rr - np.float32(3.0) * uy, 0, orig_shape[0] - 1),
            np.clip(cc - np.float32(3.0) * ux, 0, orig_shape[1] - 1),
        ],
        dtype=np.float32,
    )
    del rr, cc, ux, uy
    gz_up = ndi.map_coordinates(gz_abs, up_coords, order=1, mode="nearest").astype(np.float32)
    gz_dn = ndi.map_coordinates(gz_abs, dn_coords, order=1, mode="nearest").astype(np.float32)
    listric_asym = (np.abs(gz_up - gz_dn) / (gz_up + gz_dn + eps_s) * cos_theta_s).astype(np.float32)
    del gz_abs, up_coords, dn_coords, gz_up, gz_dn

    # Full symmetric trace-free 3x3 Eötvös tensor Gamma_ij at z_shallow_m + 50 m smoothing
    att_t = (att_s * np.exp(-kr * np.float32(50.0))).astype(np.float32)
    gxx = _ifft_unpad(spec * (-(kx * kx) * att_t), fft_shape, pad_shape, orig_shape, p, workers)
    gyy = _ifft_unpad(spec * (-(ky * ky) * att_t), fft_shape, pad_shape, orig_shape, p, workers)
    gxy = _ifft_unpad(spec * (-(kx * ky) * att_t), fft_shape, pad_shape, orig_shape, p, workers)
    gxz = _ifft_unpad(spec * (1j * kx * kr * att_t), fft_shape, pad_shape, orig_shape, p, workers)
    gyz = _ifft_unpad(spec * (1j * ky * kr * att_t), fft_shape, pad_shape, orig_shape, p, workers)
    del att_s, att_t
    # Exact Laplace trace-free identity: Gamma_zz = -(Gamma_xx + Gamma_yy)
    gzz = (-(gxx + gyy)).astype(np.float32)

    # Cooper & Cowan (2006) stabilized hyperbolic tilt
    gv_shear = np.hypot(gxz, gyz).astype(np.float32)
    shear_scale = np.float32(float(np.percentile(gv_shear[footprint], 50.0)) * 0.35 + 1e-7)
    hyperbolic_tilt = np.arcsinh(gzz / (gv_shear + shear_scale)).astype(np.float32)
    del gv_shear

    # Pedersen & Rasmussen (1990) 3-D tensor invariants I_1, I_2, and quasi-2D purity Q_2D = 1 - |I|
    # Perform determinant/invariant math in float64 per-chunk or float32 normalized by local Frobenius norm
    frob = np.sqrt(
        gxx * gxx
        + gyy * gyy
        + gzz * gzz
        + np.float32(2.0) * (gxy * gxy + gxz * gxz + gyz * gyz)
    ).astype(np.float32)
    f_floor = np.float32(float(np.percentile(frob[footprint], 25.0)) * 0.25 + 1e-9)
    fn = np.maximum(frob, f_floor)
    nxx = (gxx / fn).astype(np.float32)
    nyy = (gyy / fn).astype(np.float32)
    nzz = (gzz / fn).astype(np.float32)
    nxy = (gxy / fn).astype(np.float32)
    nxz = (gxz / fn).astype(np.float32)
    nyz = (gyz / fn).astype(np.float32)
    del gxx, gyy, gxy, gxz, gyz, frob, fn

    i1 = (
        nxx * nyy
        + nyy * nzz
        + nxx * nzz
        - nxy * nxy
        - nxz * nxz
        - nyz * nyz
    ).astype(np.float32)
    det_g = (
        nxx * (nyy * nzz - nyz * nyz)
        - nxy * (nxy * nzz - nyz * nxz)
        + nxz * (nxy * nyz - nyy * nxz)
    ).astype(np.float32)
    del nxx, nyy, nzz, nxy, nxz, nyz
    denom_i = np.float32(2.0) * np.power(
        np.maximum(-i1 / np.float32(3.0), np.float32(1e-6)), np.float32(1.5)
    )
    abs_dim_i = np.clip(np.abs(det_g) / denom_i, 0.0, 1.0).astype(np.float32)
    q2d_purity = ((np.float32(1.0) - abs_dim_i) * cos_theta_s).astype(np.float32)
    del i1, det_g, denom_i, abs_dim_i

    # Mid & deep upward-continued Wijns 3-D gravity theta-maps (450 m & 800 m)
    gx_m = _ifft_unpad(spec * (1j * kx * att_m), fft_shape, pad_shape, orig_shape, p, workers)
    gy_m = _ifft_unpad(spec * (1j * ky * att_m), fft_shape, pad_shape, orig_shape, p, workers)
    gz_m = _ifft_unpad(spec * (kr * att_m), fft_shape, pad_shape, orig_shape, p, workers)
    gh_m = np.hypot(gx_m, gy_m).astype(np.float32)
    eps_m = np.float32(float(np.percentile(gh_m[footprint], 20.0)) * 0.25 + 1e-6)
    cos_theta_m = (gh_m / np.sqrt(gh_m * gh_m + gz_m * gz_m + eps_m * eps_m)).astype(np.float32)
    del gx_m, gy_m, gz_m, gh_m, att_m

    gx_d = _ifft_unpad(spec * (1j * kx * att_d), fft_shape, pad_shape, orig_shape, p, workers)
    gy_d = _ifft_unpad(spec * (1j * ky * att_d), fft_shape, pad_shape, orig_shape, p, workers)
    gz_d = _ifft_unpad(spec * (kr * att_d), fft_shape, pad_shape, orig_shape, p, workers)
    gh_d = np.hypot(gx_d, gy_d).astype(np.float32)
    eps_d = np.float32(float(np.percentile(gh_d[footprint], 20.0)) * 0.25 + 1e-6)
    cos_theta_d = (gh_d / np.sqrt(gh_d * gh_d + gz_d * gz_d + eps_d * eps_d)).astype(np.float32)
    del spec, ky, kx, kr, gx_d, gy_d, gz_d, gh_d, att_d

    # Multi-altitude 1-D directional theta-worm persistence
    r_s = PTHA._detect_1d_directional_ridge(cos_theta_s, span=1).astype(np.float32) * cos_theta_s
    r_m = PTHA._detect_1d_directional_ridge(cos_theta_m, span=1).astype(np.float32) * cos_theta_m
    r_d = PTHA._detect_1d_directional_ridge(cos_theta_d, span=2).astype(np.float32) * cos_theta_d
    worm_persist = (
        np.float32(0.40) * ndi.gaussian_filter(r_s, sigma=0.9)
        + np.float32(0.35) * ndi.gaussian_filter(r_m, sigma=1.2)
        + np.float32(0.25) * ndi.gaussian_filter(r_d, sigma=1.6)
    ).astype(np.float32)
    del gh_s, cos_theta_m, r_s, r_m, r_d

    return {
        "gz_200m": gz_s,
        "gzz_250m": gzz,
        "cos_theta_200m": cos_theta_s,
        "cos_theta_600m": cos_theta_d,
        "hyperbolic_tilt": hyperbolic_tilt,
        "q2d_purity": q2d_purity,
        "listric_asym": listric_asym,
        "worm_persist": worm_persist,
        "strike_psi_g": strike_psi_g,
    }


def destripe_cardinal_flightlines(
    field_2d: np.ndarray,
    *,
    min_wavelength_m: float = 200.0,
    max_wavelength_m: float = 4_500.0,
    wedge_sigma_rad: float = 0.055,
    pad: int = 96,
    workers: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Remove E-W and N-S airborne survey flight-line/tie-line leveling stripes (`SACR`).

    Applies a smooth angular Gaussian notch around `kx = 0` and `ky = 0` strictly
    within the stripe passband `[2*pi/max_wavelength_m, 2*pi/min_wavelength_m]`,
    preserving long-wavelength regional fields (`DC` & `>4.5 km`) and all oblique
    geological strike orientations (`NNE`, `NW` Walker Lane, `NE` Humboldt).
    Returns `(clean_field_2d, stripe_residual_2d)` in float32.
    """
    orig_shape = field_2d.shape
    spec, ky, kx, fft_shape, pad_shape, p = _fft_pad_grid(field_2d, pad=pad, workers=workers)
    kr = np.hypot(ky, kx).astype(np.float32)
    kr_safe = np.maximum(kr, np.float32(1e-7))

    # Angular distance from nearest cardinal axis (kx=0 or ky=0)
    sin_cardinal = (np.minimum(np.abs(kx), np.abs(ky)) / kr_safe).astype(np.float32)
    ang_notch = (1.0 - np.exp(-((sin_cardinal / np.float32(wedge_sigma_rad)) ** 2))).astype(
        np.float32
    )

    k_low = np.float32(2.0 * np.pi / max(max_wavelength_m, 500.0))
    k_high = np.float32(2.0 * np.pi / max(min_wavelength_m, 200.0))
    band_gate = (
        (1.0 - np.exp(-((kr / k_low) ** 2))) * np.exp(-((kr / (k_high * np.float32(1.6))) ** 4))
    ).astype(np.float32)
    band_gate[0, 0] = 0.0

    filt = (1.0 - band_gate * (1.0 - ang_notch)).astype(np.float32)
    clean = _ifft_unpad(spec * filt, fft_shape, pad_shape, orig_shape, p, workers)
    stripe = (np.asarray(field_2d, dtype=np.float32) - clean).astype(np.float32)
    del spec, ky, kx, kr, kr_safe, sin_cardinal, ang_notch, band_gate, filt
    return clean, stripe


def compute_laplace_tilt_and_theta(
    clean_field_2d: np.ndarray,
    footprint: np.ndarray,
    *,
    z_up_m: float = 150.0,
    hp_wavelength_m: float = 18_000.0,
    pad: int = 96,
    workers: int = 2,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return `(verduzco_tilt, cos_theta, strike_psi)` for a seam-cleaned potential field."""
    orig_shape = clean_field_2d.shape
    spec, ky, kx, fft_shape, pad_shape, p = _fft_pad_grid(clean_field_2d, pad=pad, workers=workers)
    kr = np.hypot(ky, kx).astype(np.float32)
    k_cut = np.float32(2.0 * np.pi / max(hp_wavelength_m, 1000.0))
    att = ((1.0 - np.exp(-((kr / k_cut) ** 2))) * np.exp(-kr * np.float32(z_up_m))).astype(
        np.float32
    )
    att[0, 0] = 0.0
    fx = _ifft_unpad(spec * (1j * kx * att), fft_shape, pad_shape, orig_shape, p, workers)
    fy = _ifft_unpad(spec * (1j * ky * att), fft_shape, pad_shape, orig_shape, p, workers)
    fz = _ifft_unpad(spec * (kr * att), fft_shape, pad_shape, orig_shape, p, workers)
    del spec, ky, kx, kr, att

    fh = np.hypot(fx, fy).astype(np.float32)
    eps = np.float32(float(np.percentile(fh[footprint], 20.0)) * 0.25 + 1e-6)
    tilt = np.arctan2(fz, fh + eps).astype(np.float32)
    cos_theta = (fh / np.sqrt(fh * fh + fz * fz + eps * eps)).astype(np.float32)
    psi = np.arctan2(-fx, fy).astype(np.float32)
    del fx, fy, fz, fh
    return tilt, cos_theta, psi


def compute_accomm_dip_reversal(
    field_2d: np.ndarray,
    footprint: np.ndarray,
    *,
    hp_sigma: float = 12.0,
    grad_sigma: float = 2.0,
    tensor_sigma: float = 5.0,
) -> np.ndarray:
    """Measure along-strike dip-polarity reversal across concealed accommodation zones (`CRBZ`).

    Estimates local structural strike `(tx, ty)` from the gradient structure tensor of
    high-pass `field_2d`, projects the signed cross-strike gradient `g_perp` onto the
    normal `(nx, ny)`, smooths polarity via `tanh(g_perp / sigma)`, and measures the
    magnitude of its along-strike derivative `|t . nabla tanh(g_perp / sigma)|`.
    """
    hp = (field_2d - ndi.gaussian_filter(field_2d, sigma=hp_sigma)).astype(np.float32)
    sm = ndi.gaussian_filter(hp, sigma=grad_sigma).astype(np.float32)
    gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
    gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
    del hp, sm

    jxx = ndi.gaussian_filter(gx * gx, sigma=tensor_sigma).astype(np.float32)
    jyy = ndi.gaussian_filter(gy * gy, sigma=tensor_sigma).astype(np.float32)
    jxy = ndi.gaussian_filter(gx * gy, sigma=tensor_sigma).astype(np.float32)
    # Principal gradient normal angle phi (pointing along +/- grad)
    phi = np.float32(0.5) * np.arctan2(np.float32(2.0) * jxy, jxx - jyy + np.float32(1e-12))
    del jxx, jyy, jxy

    nx = np.cos(phi).astype(np.float32)
    ny = np.sin(phi).astype(np.float32)
    # Strike unit vector t = (-ny, nx)
    tx = (-ny).astype(np.float32)
    ty = nx

    g_perp = (gx * nx + gy * ny).astype(np.float32)
    del gx, gy, phi, nx, ny
    scale = np.float32(float(np.percentile(np.abs(g_perp[footprint]), 75.0)) + 1e-5)
    pol = np.tanh(g_perp / scale).astype(np.float32)
    del g_perp

    py = (ndi.sobel(ndi.gaussian_filter(pol, sigma=2.5), axis=0) / 8.0).astype(np.float32)
    px = (ndi.sobel(ndi.gaussian_filter(pol, sigma=2.5), axis=1) / 8.0).astype(np.float32)
    reversal = np.abs(px * tx + py * ty).astype(np.float32)
    del pol, px, py, tx, ty
    return reversal


def build_or_load_lftg17_feature_memmap(
    *,
    features_tif: Path,
    footprint: np.ndarray,
    cache_dir: Path,
    workers: int = 2,
) -> tuple[np.memmap, list[str], Path]:
    """Build or load the 20-column `S17-LFTG` float32 footprint memmap (`~413 MB`).

    Strictly touches ONLY subsurface/airborne/geodetic/seismic bands:
    `B01, B02, B06, B07, B08, B10, B13, B14, B15, B16, B17`.
    `Band 12` (`det_elev`) and `Band 19` (`det_elev_slope`) are NEVER read!
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_fp = int(footprint.sum())
    n_cols = len(S17_LFTG_FEATURE_NAMES)
    mm_path = cache_dir / "s17_lftg_features_v1.dat"
    meta_path = cache_dir / "s17_lftg_features_v1.json"

    if mm_path.is_file() and meta_path.is_file() and mm_path.stat().st_size == n_fp * n_cols * 4:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("feature_names") == S17_LFTG_FEATURE_NAMES and meta.get("n_fp") == n_fp:
            mm = np.memmap(mm_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S17_LFTG_FEATURE_NAMES), mm_path

    mm_w = np.memmap(mm_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    def _read_clean(src: rasterio.DatasetReader, band_1idx: int) -> np.ndarray:
        raw = src.read(band_1idx).astype(np.float32)
        return DD._clean_band_edt(raw, footprint)

    with rasterio.open(features_tif) as src:
        b13 = _read_clean(src, 13)  # iso_grav_anom
        b15 = np.maximum(_read_clean(src, 15), 0.0).astype(np.float32)  # depth_to_base_surf

    # --- H17-1: 3-D Laplace Full-Tensor Gravity (cols 0..7) ---
    grav = compute_laplace_full_tensor_gravity(b13, footprint, workers=workers)
    mm_w[:, 0] = _robust_z_fp(grav["gz_200m"][footprint])
    mm_w[:, 1] = _robust_z_fp(grav["gzz_250m"][footprint])
    mm_w[:, 2] = _robust_z_fp(grav["cos_theta_200m"][footprint])
    mm_w[:, 3] = _robust_z_fp(grav["cos_theta_600m"][footprint])
    mm_w[:, 4] = _robust_z_fp(grav["hyperbolic_tilt"][footprint])
    mm_w[:, 5] = _robust_z_fp(grav["q2d_purity"][footprint])
    mm_w[:, 6] = _robust_z_fp(grav["listric_asym"][footprint])
    mm_w[:, 7] = _robust_z_fp(grav["worm_persist"][footprint])

    cos_theta_g = grav["cos_theta_200m"]
    cos_theta_g_deep = grav["cos_theta_600m"]
    q2d_g = grav["q2d_purity"]
    psi_g = grav["strike_psi_g"]
    del grav
    gc.collect()

    # --- H17-2: Flight-Line Notch-Destriped Magnetics & Radiometrics (cols 8..13) ---
    with rasterio.open(features_tif) as src:
        b02 = _read_clean(src, 2)   # rtp
        b14 = _read_clean(src, 14)  # tmi (draped GeoDAWN)
        b06 = _read_clean(src, 6)   # tc (airborne radiometric Total Count)

    b02_clean, _ = destripe_cardinal_flightlines(b02, workers=workers)
    del b02
    rtp_tilt, rtp_cos_theta, psi_m = compute_laplace_tilt_and_theta(
        b02_clean, footprint, z_up_m=150.0, workers=workers
    )
    del b02_clean
    mm_w[:, 8] = _robust_z_fp(rtp_tilt[footprint])
    mm_w[:, 9] = _robust_z_fp(rtp_cos_theta[footprint])
    del rtp_tilt

    b14_clean, b14_stripe = destripe_cardinal_flightlines(b14, workers=workers)
    del b14
    b14_sm = ndi.gaussian_filter(b14_clean, sigma=1.1).astype(np.float32)
    b14_gh = (
        np.hypot(ndi.sobel(b14_sm, axis=0) / 8.0, ndi.sobel(b14_sm, axis=1) / 8.0)
        / np.float32(PIXEL_M)
    ).astype(np.float32)
    del b14_sm
    mm_w[:, 10] = _robust_z_fp(np.log1p(b14_gh[footprint] * np.float32(50.0)))

    stripe_energy = ndi.gaussian_filter(np.abs(b14_stripe), sigma=4.0).astype(np.float32)
    sig_energy = ndi.gaussian_filter(b14_gh * np.float32(PIXEL_M), sigma=4.0).astype(np.float32)
    seam_ratio = (np.log1p(stripe_energy) - np.log1p(sig_energy)).astype(np.float32)
    mm_w[:, 12] = _robust_z_fp(seam_ratio[footprint])
    del b14_stripe, b14_gh, stripe_energy, sig_energy, seam_ratio

    b06_clean, _ = destripe_cardinal_flightlines(b06, workers=workers)
    del b06
    b06_sm = ndi.gaussian_filter(b06_clean, sigma=1.4).astype(np.float32)
    b06_gh = np.hypot(ndi.sobel(b06_sm, axis=0) / 8.0, ndi.sobel(b06_sm, axis=1) / 8.0).astype(
        np.float32
    )
    mm_w[:, 11] = _robust_z_fp(np.log1p(b06_gh[footprint]))
    del b06_clean, b06_sm, b06_gh

    strike_align = (np.cos(psi_g - psi_m) ** 2).astype(np.float32)
    concord = (strike_align * np.sqrt(np.maximum(cos_theta_g * rtp_cos_theta, 0.0))).astype(
        np.float32
    )
    mm_w[:, 13] = _robust_z_fp(concord[footprint])
    del rtp_cos_theta, psi_g, psi_m, strike_align, concord
    gc.collect()

    # --- H17-3: Concealed Accommodation-Zone Reversal & Alteration Dipole (cols 14..19) ---
    accomm_grav = compute_accomm_dip_reversal(b13, footprint)
    mm_w[:, 14] = _robust_z_fp((accomm_grav * cos_theta_g)[footprint])
    del accomm_grav, b13

    accomm_b15 = compute_accomm_dip_reversal(np.log1p(b15), footprint)
    mm_w[:, 15] = _robust_z_fp((accomm_b15 * cos_theta_g_deep)[footprint])
    del accomm_b15

    with rasterio.open(features_tif) as src:
        b01 = _read_clean(src, 1)   # regional mag_anom
        b17 = np.maximum(_read_clean(src, 17), 0.0).astype(np.float32)  # cond_surf
        b07 = _read_clean(src, 7)   # geod_shearrate
        b08 = _read_clean(src, 8)   # geod_dilaterate
        b10 = np.maximum(_read_clean(src, 10), 0.0).astype(np.float32)  # deq_n100a15
        b16 = np.maximum(_read_clean(src, 16), 0.0).astype(np.float32)  # ieq_n100a15

    drape_diff = (b14_clean - b01).astype(np.float32)
    del b14_clean, b01
    mag_destruct = np.maximum(
        ndi.gaussian_filter(drape_diff, sigma=10.0) - ndi.gaussian_filter(drape_diff, sigma=1.5),
        0.0,
    ).astype(np.float32)
    del drape_diff
    mag_destruct_step = (np.log1p(mag_destruct) * cos_theta_g).astype(np.float32)
    mm_w[:, 16] = _robust_z_fp(mag_destruct_step[footprint])

    # Subsurface-only (B15-deconfounded, zero B12/B19!) conductivity local gradient
    l17 = np.log1p(b17).astype(np.float32)
    l15 = np.log1p(b15).astype(np.float32)
    del b17
    x15 = l15[footprint].astype(np.float64)
    y17 = l17[footprint].astype(np.float64)
    A = np.column_stack([np.ones_like(x15), x15, x15 * x15])
    beta_c, *_ = np.linalg.lstsq(A, y17, rcond=None)
    cond_res = np.zeros(footprint.shape, dtype=np.float32)
    cond_res[footprint] = (y17 - A @ beta_c).astype(np.float32)
    del l17, l15, x15, y17, A
    cond_sm = ndi.gaussian_filter(cond_res, sigma=1.8).astype(np.float32)
    cond_grad = np.hypot(ndi.sobel(cond_sm, axis=0) / 8.0, ndi.sobel(cond_sm, axis=1) / 8.0).astype(
        np.float32
    )
    clay_dipole = (
        np.maximum(cond_res, 0.0) * cond_grad * np.log1p(mag_destruct)
    ).astype(np.float32)
    mm_w[:, 17] = _robust_z_fp(clay_dipole[footprint])
    del cond_res, cond_sm, cond_grad, mag_destruct, mag_destruct_step, clay_dipole

    # Positive dependent swarm excess (IR-91-S14-01 corrected) x local transtensional work
    swarm_exc = np.maximum(np.log1p(b10) - np.float32(0.85) * np.log1p(b16), 0.0).astype(np.float32)
    swarm_local = np.maximum(
        swarm_exc - ndi.gaussian_filter(swarm_exc, sigma=18.0), 0.0
    ).astype(np.float32)
    del b10, b16, swarm_exc
    s7_med = float(np.percentile(np.abs(b07[footprint]), 50.0)) + 1e-6
    transtens = np.sqrt(
        np.maximum(b07 / np.float32(s7_med), 0.0)
        * np.maximum(np.float32(0.5) + b08 / np.float32(s7_med), 0.0)
    ).astype(np.float32)
    del b07, b08
    swarm_conduit = (swarm_local * (np.float32(0.5) + transtens) * cos_theta_g).astype(np.float32)
    mm_w[:, 18] = _robust_z_fp(swarm_conduit[footprint])
    del swarm_local, transtens, swarm_conduit

    # Deep-cover (>350 m alluvial fill) concealed 2-D Laplace-tensor crest
    cover_gate = np.tanh(b15 / np.float32(400.0)).astype(np.float32)
    deep_concealed = (cover_gate * cos_theta_g_deep * q2d_g).astype(np.float32)
    mm_w[:, 19] = _robust_z_fp(deep_concealed[footprint])
    del b15, cover_gate, cos_theta_g, cos_theta_g_deep, q2d_g, deep_concealed

    mm_w.flush()
    if not np.isfinite(mm_w).all():
        raise RuntimeError("Non-finite values detected in S17-LFTG feature memmap")

    meta_path.write_text(
        json.dumps(
            {
                "schema": "gems91.s17_lftg_features.v1",
                "n_fp": n_fp,
                "n_cols": n_cols,
                "feature_names": S17_LFTG_FEATURE_NAMES,
                "b12_b19_touched": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    del mm_w
    gc.collect()
    mm_r = np.memmap(mm_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_r, list(S17_LFTG_FEATURE_NAMES), mm_path


def build_lftg17_structural_crest(
    base_ptha_crest: np.ndarray,
    X_lftg: np.ndarray,
    footprint: np.ndarray,
    *,
    deep_cover_weight: float = 0.0,
) -> np.ndarray:
    """Build hybrid multi-physics + 3-D Laplace Full-Tensor Gravity structural crest in `[0, 1]`."""
    def _col2d(idx: int) -> np.ndarray:
        arr = np.zeros(footprint.shape, dtype=np.float32)
        arr[footprint] = X_lftg[:, idx]
        return _robust_pos_01_2d(arr, footprint)

    c_theta = _col2d(2)     # lftg17_wijns_cos_theta_200m
    c_q2d = _col2d(5)       # lftg17_pedersen_q2d_purity
    c_worm = _col2d(7)      # lftg17_theta_worm_persist
    c_mag = _col2d(10)      # lftg17_tmi_drape_destriped_grad
    c_concord = _col2d(13)  # lftg17_grav_mag_destriped_concord
    c_accomm = _col2d(14)   # lftg17_accomm_grav_dip_reversal

    lftg_crest = (
        np.float32(0.28) * c_worm
        + np.float32(0.22) * c_q2d
        + np.float32(0.18) * c_theta
        + np.float32(0.14) * c_concord
        + np.float32(0.10) * c_mag
        + np.float32(0.08) * c_accomm
    ).astype(np.float32)
    del c_theta, c_q2d, c_worm, c_mag, c_concord, c_accomm

    if deep_cover_weight > 0.0:
        c_deep = _col2d(19)  # lftg17_deep_cover_concealed_crest
        lftg_crest = np.clip(
            (np.float32(1.0 - deep_cover_weight) * lftg_crest)
            + np.float32(deep_cover_weight) * c_deep,
            0.0,
            1.0,
        ).astype(np.float32)
        del c_deep

    out = np.clip(
        np.float32(0.56) * base_ptha_crest.astype(np.float32) + np.float32(0.44) * lftg_crest,
        0.0,
        1.0,
    ).astype(np.float32)
    out[~footprint] = 0.0
    return out


def compute_subsurface_autocontext(prob_sub_cal_2d: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Compute 4-column `100%` DEM-free subsurface topological auto-context (`ac_sub_*`).

    Expects `prob_sub_cal_2d` ALREADY prior-shift calibrated to `PRIOR_PI0` so stitched
    1-quad, 2-quad, and 3-quad OOF predictions share an identical probability scale
    (`IR-91-S15-06` fix).
    """
    p = np.clip(prob_sub_cal_2d, 0.0, 1.0).astype(np.float32)
    p[~footprint] = 0.0
    n_fp = int(footprint.sum())
    out = np.zeros((n_fp, 4), dtype=np.float32)
    out[:, 0] = p[footprint]

    # Multi-azimuth 1.5 km directional ray max + wash bridge across 1.6 km alluvial gaps
    angles = np.deg2rad([0.0, 30.0, 60.0, 90.0, 120.0, 150.0])
    ray_max = np.zeros_like(p)
    bridge_max = np.zeros_like(p)
    rr, cc = np.indices(p.shape, dtype=np.float32)
    p_sm = ndi.gaussian_filter(p, sigma=1.2).astype(np.float32)
    for ang in angles:
        dy = np.float32(np.sin(ang))
        dx = np.float32(np.cos(ang))
        pos8 = ndi.map_coordinates(
            p_sm,
            np.array(
                [
                    np.clip(rr + np.float32(8.0) * dy, 0, p.shape[0] - 1),
                    np.clip(cc + np.float32(8.0) * dx, 0, p.shape[1] - 1),
                ],
                dtype=np.float32,
            ),
            order=1,
            mode="nearest",
        ).astype(np.float32)
        neg8 = ndi.map_coordinates(
            p_sm,
            np.array(
                [
                    np.clip(rr - np.float32(8.0) * dy, 0, p.shape[0] - 1),
                    np.clip(cc - np.float32(8.0) * dx, 0, p.shape[1] - 1),
                ],
                dtype=np.float32,
            ),
            order=1,
            mode="nearest",
        ).astype(np.float32)
        ray_max = np.maximum(ray_max, np.float32(0.5) * (pos8 + neg8))
        bridge_max = np.maximum(bridge_max, np.sqrt(np.maximum(pos8 * neg8, 0.0)))
        del pos8, neg8
    del rr, cc, p_sm

    corridor_2km = ndi.gaussian_filter(p, sigma=10.0).astype(np.float32)
    out[:, 1] = ray_max[footprint]
    out[:, 2] = bridge_max[footprint]
    out[:, 3] = corridor_2km[footprint]
    del ray_max, bridge_max, corridor_2km
    return out


def _stack_rows(blocks: Sequence[FeatureBlock], rows: np.ndarray) -> np.ndarray:
    active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    if not active:
        raise ValueError("At least one non-empty feature block is required")
    return np.hstack([np.asarray(arr[rows][:, cols], dtype=np.float32) for arr, cols in active])


def _stack_slice(blocks: Sequence[FeatureBlock], start: int, end: int) -> np.ndarray:
    active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    if not active:
        raise ValueError("At least one non-empty feature block is required")
    return np.hstack([np.asarray(arr[start:end][:, cols], dtype=np.float32) for arr, cols in active])


def fit_predict_calibrated_specialist(
    *,
    train_blocks: Sequence[FeatureBlock],
    infer_blocks: Sequence[FeatureBlock],
    train_mask: np.ndarray,
    visible_faults: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    pi_target: float = PRIOR_PI0,
    neg_pos_ratio: float = 3.8,
    chunk_size: int = 450_000,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Fit HGB_deep + HGB_shallow + LogisticRegression on `train_mask` and return a
    footprint surface IMMEDIATELY calibrated to `pi_target` via exact Bayes prior shift.
    """
    rng = np.random.default_rng(seed)
    tr_fp = np.asarray(train_mask, dtype=bool)[footprint]
    vis_fp = (np.asarray(visible_faults, dtype=bool) & footprint)[footprint]
    d_vis = ndi.distance_transform_edt(~(np.asarray(visible_faults, dtype=bool) & footprint))
    d_vis_fp = d_vis[footprint]
    del d_vis

    pos_idx = np.flatnonzero(tr_fp & vis_fp)
    neg_pool = np.flatnonzero(tr_fp & (~vis_fp) & (d_vis_fp > 3.5))
    del d_vis_fp
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Specialist training requires non-empty positive and safe-negative sets")

    target_neg = min(int(round(neg_pos_ratio * pos_idx.size)), int(neg_pool.size))
    neg_idx = (
        np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
        if target_neg < neg_pool.size
        else neg_pool
    )
    pi_sample = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    pi_vis_train = float(pos_idx.size) / float(max(int(tr_fp.sum()), 1))

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate(
        [np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)]
    )
    X_tr = _stack_rows(train_blocks, train_idx)

    hgb_deep = HistGradientBoostingClassifier(
        learning_rate=0.052,
        max_iter=195,
        max_leaf_nodes=39,
        min_samples_leaf=75,
        l2_regularization=3.5,
        early_stopping=False,
        random_state=seed,
    ).fit(X_tr, y_train)

    hgb_shallow = HistGradientBoostingClassifier(
        learning_rate=0.048,
        max_iter=165,
        max_leaf_nodes=23,
        max_depth=6,
        min_samples_leaf=115,
        l2_regularization=6.5,
        early_stopping=False,
        random_state=seed + 17,
    ).fit(X_tr, y_train)

    scaler = StandardScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr), -6.0, 6.0)
    lr = LogisticRegression(C=0.22, max_iter=250, random_state=seed + 31).fit(X_tr_sc, y_train)
    del X_tr, X_tr_sc, y_train

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    for start in range(0, n_fp, chunk_size):
        end = min(start + chunk_size, n_fp)
        X_ch = _stack_slice(infer_blocks, start, end)
        p1 = hgb_deep.predict_proba(X_ch)[:, 1]
        p2 = hgb_shallow.predict_proba(X_ch)[:, 1]
        p3 = lr.predict_proba(np.clip(scaler.transform(X_ch), -6.0, 6.0))[:, 1]
        pred_fp[start:end] = (0.50 * p1 + 0.34 * p2 + 0.16 * p3).astype(np.float32)
        del X_ch

    raw_2d = np.zeros(footprint.shape, dtype=np.float32)
    raw_2d[footprint] = pred_fp
    del pred_fp

    cal_2d = PTHA.prior_shift_calibrate_surface(
        raw_2d, footprint, pi_true=float(pi_target), pi_sample=pi_sample
    )
    del raw_2d
    gc.collect()
    return cal_2d, {
        "n_pos": int(pos_idx.size),
        "n_neg": int(neg_idx.size),
        "pi_sample": round(pi_sample, 6),
        "pi_vis_train": round(pi_vis_train, 6),
        "pi_target": round(float(pi_target), 6),
    }


def blend_dual_specialists(
    prob_full_cal: np.ndarray,
    prob_sub_cal: np.ndarray,
    piedmont_mask: np.ndarray,
    b15_fp: np.ndarray,
    footprint: np.ndarray,
    *,
    base_sub_weight: float = 0.24,
    piedmont_sub_weight: float = 0.40,
    deep_cover_sub_weight: float | None = None,
) -> np.ndarray:
    """Blend calibrated `Full` and `100% DEM-free Pure-Subsurface` posteriors.

    In `E1`/`E2`, `deep_cover_sub_weight=None` uses the standard piedmont/scarp routing.
    In `E3`, thick Quaternary cover (`B15 > 350 m` inside low-relief piedmont/basins)
    shifts weight up to `deep_cover_sub_weight` (`0.58`) toward the DEM-free specialist.
    """
    w_sub = np.where(
        piedmont_mask, np.float32(piedmont_sub_weight), np.float32(base_sub_weight)
    ).astype(np.float32)
    if deep_cover_sub_weight is not None:
        b15_2d = np.zeros(footprint.shape, dtype=np.float32)
        b15_2d[footprint] = b15_fp
        deep_gate = np.clip((b15_2d - np.float32(200.0)) / np.float32(450.0), 0.0, 1.0).astype(
            np.float32
        )
        w_target = np.where(
            piedmont_mask,
            w_sub + deep_gate * np.float32(deep_cover_sub_weight - piedmont_sub_weight),
            w_sub + np.float32(0.5) * deep_gate * np.float32(max(deep_cover_sub_weight - 0.30, 0.0)),
        ).astype(np.float32)
        w_sub = np.clip(w_target, 0.0, 0.80)
        del b15_2d, deep_gate, w_target

    out = ((np.float32(1.0) - w_sub) * prob_full_cal + w_sub * prob_sub_cal).astype(np.float32)
    out[~footprint] = 0.0
    return np.clip(out, 0.0, 1.0)


def emit_global_label_blind_dinkelbach(
    prob_cal_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    visible_faults: np.ndarray,
    footprint: np.ndarray,
    n_dots: int = 37_654,
    collar_px: float = 2.25,
    min_spacing_px: float = 2.82,
) -> tuple[np.ndarray, float]:
    """Label-blind global-budget submodular Dinkelbach emitter.

    Receives ONLY `visible_faults` (`fold['visible']` in holdout, `cat` in full-map
    inference) and `footprint` — NEVER `fold['region']`, `fold['truth']`, or `fold['train']`.
    Because `prob_cal_2d` is already Bayes-calibrated to `PRIOR_PI0` (`0.022`), we pass
    `pi_true = pi_sample = PRIOR_PI0` (identity calibration).
    """
    vis = np.asarray(visible_faults, dtype=bool) & footprint
    d_vis = ndi.distance_transform_edt(~vis)
    eligible = footprint & (~vis) & (d_vis > float(collar_px))
    del d_vis
    return PTHA.dinkelbach_full_map_emit(
        prob_cal_2d,
        crest_2d,
        piedmont_mask,
        footprint=footprint,
        full_eligible_mask=eligible,
        pi_true=PRIOR_PI0,
        pi_sample=PRIOR_PI0,
        n_dots=int(n_dots),
        min_spacing_px=float(min_spacing_px),
    )
