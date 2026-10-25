"""Session 14 (`S14-UCSD`): Upward-Continued Subsurface Dip-Migration, Multi-Physics
8-Field Odd-Parity Step Synthesis, Leak-Free Two-Stage Steerable Radon Wash-Bridge
Auto-Context, and Regime-Coupled Dinkelbach Expected-DTI Submodular Allocation.

Implements the pre-registered Session 14 hypotheses (`docs/HYPOTHESES_S14.md`):
- `H14-1` (`cols 0..11`): 2-D Fourier upward-continued gravity & RTP magnetic
  horizontal-gradient persistence and signed hanging-wall downdip migration
  (`z in {200, 1200, 1500} m`), Bouguer-stripped intra-basement gravity
  (`B13 perp B15`), and depth/elevation-deconfounded electrical conductivity
  clay-cap residual (`B17 perp B15, B12`) + potassic radiometric halo (`B06`).
- `H14-2` (`cols 12..19`): Multi-scale contour-tangent planform drainage-deflection
  curvature (`|kappa_t|` at 150 m & 350 m), scarp-toe profile concavity (`250 m`),
  strike-resolved Great Basin Coulomb slip tendency (`B04, B07, B08`), coupled
  earthquake swarm conduit (`B10, B16`), and 8-field odd-parity cross-fault step
  synthesis adding Bouguer-stripped gravity and shallow 2021-2022 GeoDAWN draped
  magnetic residual (`B14 - B01`).
- `H14-3`: Prior-invariant flank-buffered (`d_vis > 3.5 px`) 4-specialist ensemble
  with a 100% Topography-Blind Subsurface Specialist (`HGB-Sub`), Leak-Free
  Two-Stage Steerable Radon Wash-Bridge Auto-Context, and Regime-Coupled
  Fold-Independent Dinkelbach Expected-DTI Submodular Allocation.
"""

from __future__ import annotations

import gc
import json
import mmap
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage
from scipy.special import expit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import RobustScaler

from gems91 import dd_vtc_pu as DD
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import spac_coda as SC

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
FEATURES_TIF = DATA_DIR / "bridge" / "gems-geodawn-numerical-features.tif"
TEMPLATE_TIF = DATA_DIR / "official" / "sample_submission.tif"
GDR_CSV = DATA_DIR / "external" / "gdr_wellspring_in_footprint.csv"
DERIVED_DIR = DATA_DIR / "derived"
S14_MEMMAP_PATH = DERIVED_DIR / "s14_ucsd_features_v1.dat"
S14_META_PATH = DERIVED_DIR / "s14_ucsd_features_v1.json"

H14_1_FEATURE_NAMES: list[str] = [
    "ucsd_upward_grav_persist_1500m",
    "ucsd_upward_grav_downdip_shift",
    "ucsd_upward_mag_persist_1500m",
    "ucsd_upward_mag_downdip_shift",
    "ucsd_bouguer_strip_res",
    "ucsd_bouguer_strip_grad",
    "ucsd_bouguer_hess_crest",
    "ucsd_cond_deconf_res",
    "ucsd_cond_deconf_ridge",
    "ucsd_rad_tc_potassic_halo",
    "ucsd_basement_hinge_dot",
    "ucsd_upward_joint_conduit",
]

H14_2_FEATURE_NAMES: list[str] = [
    "ucsd_planform_curv_150m",
    "ucsd_planform_curv_350m",
    "ucsd_scarp_toe_concav_250m",
    "ucsd_coulomb_slip_tendency",
    "ucsd_swarm_transtens_conduit",
    "ucsd_step_bouguer_abs",
    "ucsd_step_shallow_mag_abs",
    "ucsd_multifield_step_synergy",
]

S14_FEATURE_NAMES: list[str] = H14_1_FEATURE_NAMES + H14_2_FEATURE_NAMES

BASE_STATIC_COLS: list[int] = list(range(34)) + [44, 45, 46, 47, 48]


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


def upward_continue_2d_fft(
    field_2d: np.ndarray,
    footprint: np.ndarray,
    heights_m: tuple[float, ...],
    *,
    pixel_size_m: float = 100.0,
    pad_px: int = 48,
) -> dict[float, np.ndarray]:
    """Exact 2-D Fourier potential-field upward continuation U(k, z) = U(k, 0) exp(-z |k|).

    Fills exterior footprint pixels via nearest-neighbor EDT before reflective padding
    so footprint boundary steps do not ring into the interior.
    """
    arr = DD._clean_band_edt(field_2d, footprint).astype(np.float32)
    med = float(np.median(arr[footprint]))
    arr_centered = (arr - med).astype(np.float32)
    padded = np.pad(arr_centered, pad_px, mode="reflect")
    hp, wp = padded.shape

    ky = 2.0 * np.pi * np.fft.fftfreq(hp, d=pixel_size_m).astype(np.float32)
    kx = 2.0 * np.pi * np.fft.rfftfreq(wp, d=pixel_size_m).astype(np.float32)
    k_rad = np.hypot(ky[:, None], kx[None, :]).astype(np.float32)

    spec = np.fft.rfft2(padded)
    out: dict[float, np.ndarray] = {}
    for z in heights_m:
        att = np.exp(-float(z) * k_rad).astype(np.float32)
        rec = np.fft.irfft2(spec * att, s=(hp, wp)).astype(np.float32)
        crop = rec[pad_px : pad_px + field_2d.shape[0], pad_px : pad_px + field_2d.shape[1]] + med
        crop[~footprint] = 0.0
        out[float(z)] = crop.astype(np.float32)
    return out


def compute_downdip_migration_fp(
    grad_shallow_2d: np.ndarray,
    grad_deep_2d: np.ndarray,
    fp_r: np.ndarray,
    fp_c: np.ndarray,
    ny_fp: np.ndarray,
    nx_fp: np.ndarray,
    *,
    shift_px: float = 3.0,
) -> np.ndarray:
    """Measure signed hanging-wall downdip shift of potential-field gradient crest."""
    h, w = grad_shallow_2d.shape
    r0 = fp_r.astype(np.float32)
    c0 = fp_c.astype(np.float32)

    coords = np.empty((2, fp_r.size), dtype=np.float32)
    coords[0] = np.clip(r0 + shift_px * ny_fp, 0.0, float(h - 1))
    coords[1] = np.clip(c0 + shift_px * nx_fp, 0.0, float(w - 1))
    deep_hw = ndimage.map_coordinates(
        grad_deep_2d, coords, order=1, mode="nearest", prefilter=False
    ).astype(np.float32)

    coords[0] = np.clip(r0 - shift_px * ny_fp, 0.0, float(h - 1))
    coords[1] = np.clip(c0 - shift_px * nx_fp, 0.0, float(w - 1))
    deep_fw = ndimage.map_coordinates(
        grad_deep_2d, coords, order=1, mode="nearest", prefilter=False
    ).astype(np.float32)
    del coords

    shallow_0 = grad_shallow_2d[fp_r, fp_c].astype(np.float32)
    asym = (deep_hw - deep_fw) * np.sqrt(np.maximum(shallow_0, 0.0) + 1e-4)
    return _robust_z_fp(asym.astype(np.float32))


def compute_planform_and_profile_curvatures(
    elev_2d: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute exact differential-geometry planform curvature |kappa_t| (150 m, 350 m)
    and scarp-toe profile concavity max(-kappa_p, 0) (250 m).
    """
    fp_r, fp_c = np.nonzero(footprint)

    def _planform_abs_fp(sigma: float) -> np.ndarray:
        fx = ndimage.gaussian_filter(elev_2d, sigma=sigma, order=(0, 1), mode="nearest")
        fy = ndimage.gaussian_filter(elev_2d, sigma=sigma, order=(1, 0), mode="nearest")
        fxx = ndimage.gaussian_filter(elev_2d, sigma=sigma, order=(0, 2), mode="nearest")
        fyy = ndimage.gaussian_filter(elev_2d, sigma=sigma, order=(2, 0), mode="nearest")
        fxy = ndimage.gaussian_filter(elev_2d, sigma=sigma, order=(1, 1), mode="nearest")
        p2 = fx * fx + fy * fy
        denom = np.power(p2 + 1e-3, 1.5)
        kt = np.abs(fxx * fy * fy - 2.0 * fxy * fx * fy + fyy * fx * fx) / denom
        p_mag = np.sqrt(p2)
        slope_gate = p_mag / (p_mag + float(np.median(p_mag[footprint])) + 1e-5)
        val = (kt * slope_gate)[fp_r, fp_c].astype(np.float32)
        return _robust_z_fp(np.log1p(np.maximum(val, 0.0)))

    kt_150_fp = _planform_abs_fp(1.5)
    kt_350_fp = _planform_abs_fp(3.5)

    fx = ndimage.gaussian_filter(elev_2d, sigma=2.5, order=(0, 1), mode="nearest")
    fy = ndimage.gaussian_filter(elev_2d, sigma=2.5, order=(1, 0), mode="nearest")
    fxx = ndimage.gaussian_filter(elev_2d, sigma=2.5, order=(0, 2), mode="nearest")
    fyy = ndimage.gaussian_filter(elev_2d, sigma=2.5, order=(2, 0), mode="nearest")
    fxy = ndimage.gaussian_filter(elev_2d, sigma=2.5, order=(1, 1), mode="nearest")
    p2 = fx * fx + fy * fy
    f_nn = (fxx * fx * fx + 2.0 * fxy * fx * fy + fyy * fy * fy) / (p2 + 1e-3)
    toe_concav = np.maximum(f_nn, 0.0)[fp_r, fp_c].astype(np.float32)
    toe_concav_fp = _robust_z_fp(np.log1p(toe_concav))
    return kt_150_fp, kt_350_fp, toe_concav_fp


def _compute_principal_normal_fp(
    b02_rtp: np.ndarray,
    b11_gvy: np.ndarray,
    b12_elev: np.ndarray,
    b13_grav: np.ndarray,
    b15_depth: np.ndarray,
    b18_gvx: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute unit cross-fault normal `(ny_fp, nx_fp)` oriented toward the hanging-wall basin."""
    rtp_sm = ndimage.gaussian_filter(b02_rtp, sigma=1.5)
    r_gy = ndimage.sobel(rtp_sm, axis=0) / np.float32(8.0)
    r_gx = ndimage.sobel(rtp_sm, axis=1) / np.float32(8.0)
    del rtp_sm

    elev_sm = ndimage.gaussian_filter(b12_elev, sigma=1.5)
    e_gy = ndimage.sobel(elev_sm, axis=0) / np.float32(8.0)
    e_gx = ndimage.sobel(elev_sm, axis=1) / np.float32(8.0)
    del elev_sm

    rms_r = float(np.sqrt(np.mean((r_gy[footprint] ** 2 + r_gx[footprint] ** 2))) + 1e-6)
    rms_g = float(np.sqrt(np.mean((b11_gvy[footprint] ** 2 + b18_gvx[footprint] ** 2))) + 1e-6)
    rms_e = float(np.sqrt(np.mean((e_gy[footprint] ** 2 + e_gx[footprint] ** 2))) + 1e-6)

    ry_n, rx_n = r_gy / rms_r, r_gx / rms_r
    gy_n, gx_n = b11_gvy / rms_g, b18_gvx / rms_g
    ey_n, ex_n = e_gy / rms_e, e_gx / rms_e
    del r_gy, r_gx, e_gy, e_gx

    j_yy = ndimage.gaussian_filter(
        (0.40 * gy_n * gy_n + 0.35 * ry_n * ry_n + 0.25 * ey_n * ey_n).astype(np.float32),
        sigma=4.0,
    )
    j_xx = ndimage.gaussian_filter(
        (0.40 * gx_n * gx_n + 0.35 * rx_n * rx_n + 0.25 * ex_n * ex_n).astype(np.float32),
        sigma=4.0,
    )
    j_yx = ndimage.gaussian_filter(
        (0.40 * gy_n * gx_n + 0.35 * ry_n * rx_n + 0.25 * ey_n * ex_n).astype(np.float32),
        sigma=4.0,
    )
    del ry_n, rx_n, gy_n, gx_n, ey_n, ex_n

    phi_norm = 0.5 * np.arctan2(2.0 * j_yx, j_xx - j_yy)
    nx_grid = np.cos(phi_norm).astype(np.float32)
    ny_grid = np.sin(phi_norm).astype(np.float32)
    del j_yy, j_xx, j_yx, phi_norm

    grav_reg = ndimage.gaussian_filter(b13_grav, sigma=6.0)
    depth_reg = ndimage.gaussian_filter(np.log1p(np.maximum(b15_depth, 0.0)), sigma=6.0)
    basin_vy = (-ndimage.sobel(grav_reg, axis=0) / rms_g) + 0.5 * ndimage.sobel(depth_reg, axis=0)
    basin_vx = (-ndimage.sobel(grav_reg, axis=1) / rms_g) + 0.5 * ndimage.sobel(depth_reg, axis=1)
    dot_basin = ny_grid * basin_vy + nx_grid * basin_vx
    flip = np.where(dot_basin < 0.0, np.float32(-1.0), np.float32(1.0))
    ny_fp = (ny_grid[footprint] * flip[footprint]).astype(np.float32)
    nx_fp = (nx_grid[footprint] * flip[footprint]).astype(np.float32)
    return ny_fp, nx_fp


def build_or_load_ucsd_feature_memmap(
    *,
    features_tif: str | Path = FEATURES_TIF,
    footprint: np.ndarray | None = None,
    cache_dir: str | Path = DERIVED_DIR,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open disk-backed `(N_fp, 20)` float32 `S14-UCSD` feature matrix."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s14_ucsd_features_v1.dat"
    meta_path = cache_p / "s14_ucsd_features_v1.json"

    if footprint is None:
        with rasterio.open(TEMPLATE_TIF) as src:
            footprint = np.isfinite(src.read(1))

    fp_r, fp_c = np.nonzero(footprint)
    n_fp = int(fp_r.size)
    n_cols = len(S14_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == S14_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S14_FEATURE_NAMES), meta

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    with rasterio.open(features_tif) as src:
        b01_mag = DD._clean_band_edt(src.read(1), footprint)
        b02_rtp = DD._clean_band_edt(src.read(2), footprint)
        b04_g2nd = np.maximum(DD._clean_band_edt(src.read(4), footprint), 0.0)
        b06_tc = DD._clean_band_edt(src.read(6), footprint)
        b07_gshear = np.maximum(DD._clean_band_edt(src.read(7), footprint), 0.0)
        b08_gdilat = DD._clean_band_edt(src.read(8), footprint)
        b10_deq = np.maximum(DD._clean_band_edt(src.read(10), footprint), 0.0)
        b11_gvy = DD._clean_band_edt(src.read(11), footprint)
        b12_elev = DD._clean_band_edt(src.read(12), footprint)
        b13_grav = DD._clean_band_edt(src.read(13), footprint)
        b14_tmi = DD._clean_band_edt(src.read(14), footprint)
        b15_depth = np.maximum(DD._clean_band_edt(src.read(15), footprint), 0.0)
        b16_ieq = np.maximum(DD._clean_band_edt(src.read(16), footprint), 0.0)
        b17_cond = np.maximum(DD._clean_band_edt(src.read(17), footprint), 0.0)
        b18_gvx = DD._clean_band_edt(src.read(18), footprint)

    ny_fp, nx_fp = _compute_principal_normal_fp(
        b02_rtp, b11_gvy, b12_elev, b13_grav, b15_depth, b18_gvx, footprint
    )
    del b11_gvy, b18_gvx
    gc.collect()

    # --- H14-1 (cols 0..3): 2-D Fourier Upward Continuation & Downdip Migration ---
    grav_up = upward_continue_2d_fft(b13_grav, footprint, heights_m=(200.0, 1200.0, 1500.0))
    g_grad_200 = np.hypot(
        ndimage.gaussian_filter(grav_up[200.0], sigma=1.2, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(grav_up[200.0], sigma=1.2, order=(0, 1), mode="nearest"),
    ).astype(np.float32)
    g_grad_1200 = np.hypot(
        ndimage.gaussian_filter(grav_up[1200.0], sigma=1.5, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(grav_up[1200.0], sigma=1.5, order=(0, 1), mode="nearest"),
    ).astype(np.float32)
    g_grad_1500 = np.hypot(
        ndimage.gaussian_filter(grav_up[1500.0], sigma=1.6, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(grav_up[1500.0], sigma=1.6, order=(0, 1), mode="nearest"),
    ).astype(np.float32)
    del grav_up

    upward_grav_persist_fp = _robust_z_fp(
        np.sqrt(np.maximum(g_grad_200[fp_r, fp_c] * g_grad_1500[fp_r, fp_c], 0.0))
    )
    upward_grav_shift_fp = compute_downdip_migration_fp(
        _robust_z_grid(g_grad_200, footprint),
        _robust_z_grid(g_grad_1200, footprint),
        fp_r,
        fp_c,
        ny_fp,
        nx_fp,
        shift_px=3.0,
    )
    mm[:, 0] = upward_grav_persist_fp
    mm[:, 1] = upward_grav_shift_fp
    del g_grad_200, g_grad_1200, g_grad_1500
    gc.collect()

    rtp_up = upward_continue_2d_fft(b02_rtp, footprint, heights_m=(200.0, 1200.0, 1500.0))
    m_grad_200 = np.hypot(
        ndimage.gaussian_filter(rtp_up[200.0], sigma=1.2, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(rtp_up[200.0], sigma=1.2, order=(0, 1), mode="nearest"),
    ).astype(np.float32)
    m_grad_1200 = np.hypot(
        ndimage.gaussian_filter(rtp_up[1200.0], sigma=1.5, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(rtp_up[1200.0], sigma=1.5, order=(0, 1), mode="nearest"),
    ).astype(np.float32)
    m_grad_1500 = np.hypot(
        ndimage.gaussian_filter(rtp_up[1500.0], sigma=1.6, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(rtp_up[1500.0], sigma=1.6, order=(0, 1), mode="nearest"),
    ).astype(np.float32)
    del rtp_up

    upward_mag_persist_fp = _robust_z_fp(
        np.sqrt(np.maximum(m_grad_200[fp_r, fp_c] * m_grad_1500[fp_r, fp_c], 0.0))
    )
    upward_mag_shift_fp = compute_downdip_migration_fp(
        _robust_z_grid(m_grad_200, footprint),
        _robust_z_grid(m_grad_1200, footprint),
        fp_r,
        fp_c,
        ny_fp,
        nx_fp,
        shift_px=3.0,
    )
    mm[:, 2] = upward_mag_persist_fp
    mm[:, 3] = upward_mag_shift_fp
    del m_grad_200, m_grad_1200, m_grad_1500, b02_rtp
    gc.collect()

    # --- H14-1 (cols 4..11): Bouguer-Stripped Gravity & Deconfounded Clay-Cap ---
    depth_s8 = ndimage.gaussian_filter(b15_depth, sigma=8.0, mode="nearest")
    d1 = np.log1p(np.maximum(depth_s8[fp_r, fp_c], 0.0))
    d2 = np.sqrt(np.maximum(depth_s8[fp_r, fp_c], 0.0))
    X_g = np.column_stack([np.ones_like(d1), d1, d2, d1 * d1]).astype(np.float64)
    beta_g, _, _, _ = np.linalg.lstsq(X_g, b13_grav[fp_r, fp_c].astype(np.float64), rcond=None)
    grav_strip_2d = np.zeros_like(b13_grav, dtype=np.float32)
    grav_strip_2d[fp_r, fp_c] = (
        b13_grav[fp_r, fp_c].astype(np.float64) - X_g @ beta_g
    ).astype(np.float32)
    grav_strip_2d = DD._clean_band_edt(grav_strip_2d, footprint)
    del X_g, d1, d2, depth_s8, b13_grav

    mm[:, 4] = _robust_z_fp(grav_strip_2d[fp_r, fp_c])

    gs_gy = ndimage.gaussian_filter(grav_strip_2d, sigma=1.5, order=(1, 0), mode="nearest")
    gs_gx = ndimage.gaussian_filter(grav_strip_2d, sigma=1.5, order=(0, 1), mode="nearest")
    gs_grad_2d = np.hypot(gs_gy, gs_gx).astype(np.float32)
    mm[:, 5] = _robust_z_fp(gs_grad_2d[fp_r, fp_c])

    hxx = ndimage.gaussian_filter(gs_grad_2d, sigma=1.8, order=(0, 2), mode="nearest")
    hyy = ndimage.gaussian_filter(gs_grad_2d, sigma=1.8, order=(2, 0), mode="nearest")
    hxy = ndimage.gaussian_filter(gs_grad_2d, sigma=1.8, order=(1, 1), mode="nearest")
    lam_min = 0.5 * ((hxx + hyy) - np.hypot(hxx - hyy, 2.0 * hxy))
    bouguer_crest_2d = np.maximum(-lam_min, 0.0).astype(np.float32)
    mm[:, 6] = _robust_z_fp(bouguer_crest_2d[fp_r, fp_c])
    del hxx, hyy, hxy, lam_min, gs_grad_2d, bouguer_crest_2d

    # Depth- and elevation-deconfounded electrical conductivity (B17 perp B15, B12)
    c_log = np.log1p(np.maximum(b17_cond[fp_r, fp_c], 0.0)).astype(np.float64)
    dep_l = np.log1p(np.maximum(b15_depth[fp_r, fp_c], 0.0)).astype(np.float64)
    dep_s = np.sqrt(np.maximum(b15_depth[fp_r, fp_c], 0.0)).astype(np.float64)
    el_z = ((b12_elev[fp_r, fp_c] - np.median(b12_elev[fp_r, fp_c])) / 500.0).astype(np.float64)
    X_c = np.column_stack([np.ones_like(c_log), dep_l, dep_s, el_z, dep_l * el_z])
    beta_c, _, _, _ = np.linalg.lstsq(X_c, c_log, rcond=None)
    cond_res_2d = np.zeros_like(b17_cond, dtype=np.float32)
    cond_res_2d[fp_r, fp_c] = (c_log - X_c @ beta_c).astype(np.float32)
    cond_res_2d = DD._clean_band_edt(cond_res_2d, footprint)
    del X_c, c_log, dep_l, dep_s, el_z, b17_cond

    mm[:, 7] = _robust_z_fp(cond_res_2d[fp_r, fp_c])

    c_ridge_accum = np.zeros(n_fp, dtype=np.float32)
    for sig in (1.8, 3.5):
        cxx = ndimage.gaussian_filter(cond_res_2d, sigma=sig, order=(0, 2), mode="nearest") * (sig**2)
        cyy = ndimage.gaussian_filter(cond_res_2d, sigma=sig, order=(2, 0), mode="nearest") * (sig**2)
        cxy = ndimage.gaussian_filter(cond_res_2d, sigma=sig, order=(1, 1), mode="nearest") * (sig**2)
        lmin = 0.5 * ((cxx + cyy) - np.hypot(cxx - cyy, 2.0 * cxy))
        c_ridge_accum = np.maximum(c_ridge_accum, np.maximum(-lmin[fp_r, fp_c], 0.0))
    mm[:, 8] = _robust_z_fp(c_ridge_accum)
    del cond_res_2d, c_ridge_accum

    tc_hp = b06_tc - ndimage.gaussian_filter(b06_tc, sigma=14.0, mode="nearest")
    tc_grad = np.hypot(
        ndimage.gaussian_filter(b06_tc, sigma=1.6, order=(1, 0), mode="nearest"),
        ndimage.gaussian_filter(b06_tc, sigma=1.6, order=(0, 1), mode="nearest"),
    )
    mm[:, 9] = _robust_z_fp(
        0.55 * _robust_z_fp(tc_hp[fp_r, fp_c]) + 0.45 * _robust_z_fp(tc_grad[fp_r, fp_c])
    )
    del tc_hp, tc_grad, b06_tc

    dl_2d = np.log1p(np.maximum(b15_depth, 0.0))
    dly = ndimage.gaussian_filter(dl_2d, sigma=2.0, order=(1, 0), mode="nearest")
    dlx = ndimage.gaussian_filter(dl_2d, sigma=2.0, order=(0, 1), mode="nearest")
    hinge_dot_fp = -(gs_gy[fp_r, fp_c] * dly[fp_r, fp_c] + gs_gx[fp_r, fp_c] * dlx[fp_r, fp_c])
    mm[:, 10] = _robust_z_fp(hinge_dot_fp.astype(np.float32))
    del dl_2d, dly, dlx, gs_gy, gs_gx, b15_depth

    mm[:, 11] = _robust_z_fp(
        0.32 * np.maximum(upward_grav_persist_fp, 0.0)
        + 0.25 * np.maximum(upward_mag_persist_fp, 0.0)
        + 0.23 * np.maximum(mm[:, 5], 0.0)
        + 0.20 * np.maximum(mm[:, 8], 0.0)
    )

    # --- H14-2 (cols 12..19): Planform Curvature, Slip Tendency & 8-Field Steps ---
    kt_150_fp, kt_350_fp, toe_250_fp = compute_planform_and_profile_curvatures(b12_elev, footprint)
    mm[:, 12] = kt_150_fp
    mm[:, 13] = kt_350_fp
    mm[:, 14] = toe_250_fp
    del b12_elev

    sy_fp = -nx_fp
    sx_fp = ny_fp
    az_normal_y, az_normal_x = float(np.cos(np.deg2rad(22.0))), float(np.sin(np.deg2rad(22.0)))
    az_wl_y, az_wl_x = float(np.cos(np.deg2rad(-35.0))), float(np.sin(np.deg2rad(-35.0)))
    align_norm = np.abs(sy_fp * az_normal_y + sx_fp * az_normal_x)
    align_wl = np.abs(sy_fp * az_wl_y + sx_fp * az_wl_x)

    z_sh = np.maximum(_robust_z_fp(b07_gshear[fp_r, fp_c]), -1.0)
    z_di = np.maximum(_robust_z_fp(np.abs(b08_gdilat[fp_r, fp_c])), -1.0)
    z_2nd = np.maximum(_robust_z_fp(b04_g2nd[fp_r, fp_c]), -1.0)
    slip_tend_fp = _robust_z_fp(
        (0.55 * align_norm * (0.5 * z_di + 0.5 * z_2nd) + 0.45 * align_wl * (0.6 * z_sh + 0.4 * z_2nd)).astype(
            np.float32
        )
    )
    mm[:, 15] = slip_tend_fp

    z_deq = _robust_z_fp(np.log1p(np.maximum(b10_deq[fp_r, fp_c], 0.0)))
    z_ieq = _robust_z_fp(np.log1p(np.maximum(b16_ieq[fp_r, fp_c], 0.0)))
    mm[:, 16] = _robust_z_fp(
        (0.40 * slip_tend_fp + 0.38 * z_deq + 0.22 * z_ieq).astype(np.float32)
    )
    del b04_g2nd, b07_gshear, b08_gdilat, b10_deq, b16_ieq

    fp_r_f = fp_r.astype(np.float32)
    fp_c_f = fp_c.astype(np.float32)
    step_bouguer = PTHA._strike_step_diff_fp(
        _robust_z_grid(grav_strip_2d, footprint),
        fp_r_f,
        fp_c_f,
        ny_fp,
        nx_fp,
        cross_offset_px=3.0,
        strike_offset_px=3.0,
    )
    step_bouguer_abs_fp = _robust_z_fp(np.abs(step_bouguer))
    mm[:, 17] = step_bouguer_abs_fp
    del grav_strip_2d, step_bouguer

    shallow_mag_2d = _robust_z_grid(b14_tmi, footprint) - _robust_z_grid(b01_mag, footprint)
    step_sh_mag = PTHA._strike_step_diff_fp(
        shallow_mag_2d,
        fp_r_f,
        fp_c_f,
        ny_fp,
        nx_fp,
        cross_offset_px=3.0,
        strike_offset_px=3.0,
    )
    step_sh_mag_abs_fp = _robust_z_fp(np.abs(step_sh_mag))
    mm[:, 18] = step_sh_mag_abs_fp
    del b01_mag, b14_tmi, shallow_mag_2d, step_sh_mag

    mm[:, 19] = _robust_z_fp(
        0.24 * np.maximum(step_bouguer_abs_fp, 0.0)
        + 0.22 * np.maximum(step_sh_mag_abs_fp, 0.0)
        + 0.20 * np.maximum(upward_grav_persist_fp, 0.0)
        + 0.18 * np.maximum(upward_mag_persist_fp, 0.0)
        + 0.16 * np.maximum(kt_150_fp, 0.0)
    )
    mm.flush()
    del mm
    gc.collect()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": S14_FEATURE_NAMES,
        "dtype": "float32",
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S14_FEATURE_NAMES), meta


def build_ucsd_structural_surfaces(
    X_static: np.memmap,
    X_s11: np.memmap,
    X_s12: np.memmap,
    X_ptha: np.memmap,
    X_ucsd: np.memmap,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Compute label-free structural edge fields & regime masks for `S14-UCSD`:
      - `ucsd_core_crest`: Combines `S13` PTHA odd-step/Blakely crest (`ptha_crest`) +
        `S14` 8-field step synergy (`col 19`) + `S11` Marussi crest (`mhtr_edge`).
      - `ucsd_sub_edge`: Combines `S12` `spi_swarm_edge` + `S14` upward-continued deep
        conduit (`col 11`), Bouguer Hessian crest (`col 6`), and deconfounded clay-cap
        ridge (`col 8`).
      - `piedmont_mask`: Concealed alluvial piedmont mask (`slope < 6.2 deg` or `depth > 220 m`).
      - `subsurface_mask`: Subsurface discovery regime (`spi_volc_mask` or high upward-continued
        deep conduit / Bouguer Hessian crest).
    """
    mhtr_edge, spi_swarm_edge, piedmont_mask, spi_volc_mask = SC.compute_spac_regime_fields(
        X_static, X_s11, X_s12, footprint
    )
    ptha_crest = PTHA.build_ptha_structural_crest_surface(mhtr_edge, X_ptha, footprint)

    def _norm01(v: np.ndarray) -> np.ndarray:
        q50 = float(np.percentile(v[::20], 50))
        q95 = float(np.percentile(v[::20], 95))
        return np.clip((v - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    bouguer_crest_fp = _norm01(np.asarray(X_ucsd[:, 6], dtype=np.float32))
    cond_ridge_fp = _norm01(np.asarray(X_ucsd[:, 8], dtype=np.float32))
    up_conduit_fp = _norm01(np.asarray(X_ucsd[:, 11], dtype=np.float32))
    step_syn_fp = _norm01(np.asarray(X_ucsd[:, 19], dtype=np.float32))

    ucsd_core_crest = np.zeros(footprint.shape, dtype=np.float32)
    ucsd_core_crest[footprint] = np.clip(
        0.52 * ptha_crest[footprint]
        + 0.26 * mhtr_edge[footprint]
        + 0.22 * step_syn_fp,
        0.0,
        1.0,
    )

    ucsd_sub_edge = np.zeros(footprint.shape, dtype=np.float32)
    sub_fp = np.clip(
        0.48 * spi_swarm_edge[footprint]
        + 0.22 * up_conduit_fp
        + 0.16 * bouguer_crest_fp
        + 0.14 * cond_ridge_fp,
        0.0,
        1.0,
    )
    ucsd_sub_edge[footprint] = sub_fp

    depth_b = np.asarray(X_static[:, 14], dtype=np.float32)
    slope_b = np.asarray(X_static[:, 18], dtype=np.float32)
    sub_mask_fp = spi_volc_mask[footprint] | (
        (slope_b < 8.5) & ((depth_b > 180.0) | (up_conduit_fp >= 0.35)) & (sub_fp >= 0.22)
    )
    subsurface_mask = np.zeros(footprint.shape, dtype=bool)
    subsurface_mask[footprint] = sub_mask_fp

    for mm_arr in (X_static, X_s11, X_s12, X_ptha, X_ucsd):
        if isinstance(mm_arr, np.memmap) and getattr(mm_arr, "_mmap", None) is not None:
            mm_arr._mmap.madvise(mmap.MADV_DONTNEED)

    return {
        "mhtr_edge": mhtr_edge,
        "ptha_crest": ptha_crest,
        "ucsd_core_crest": ucsd_core_crest,
        "ucsd_sub_edge": ucsd_sub_edge,
        "piedmont_mask": piedmont_mask,
        "subsurface_mask": subsurface_mask,
    }


def _assemble_blocks_rows(
    blocks: list[tuple[np.memmap | np.ndarray, list[int]]],
    row_idx: np.ndarray,
) -> np.ndarray:
    total_d = sum(len(cols) for _, cols in blocks if len(cols) > 0)
    out = np.empty((row_idx.size, total_d), dtype=np.float32)
    c0 = 0
    for arr, cols in blocks:
        if not cols:
            continue
        c1 = c0 + len(cols)
        out[:, c0:c1] = np.asarray(arr[row_idx][:, cols], dtype=np.float32)
        if isinstance(arr, np.memmap) and getattr(arr, "_mmap", None) is not None:
            arr._mmap.madvise(mmap.MADV_DONTNEED)
        c0 = c1
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def _assemble_blocks_slice(
    blocks: list[tuple[np.memmap | np.ndarray, list[int]]],
    s: int,
    e: int,
) -> np.ndarray:
    total_d = sum(len(cols) for _, cols in blocks if len(cols) > 0)
    out = np.empty((e - s, total_d), dtype=np.float32)
    c0 = 0
    for arr, cols in blocks:
        if not cols:
            continue
        c1 = c0 + len(cols)
        out[:, c0:c1] = np.asarray(arr[s:e][:, cols], dtype=np.float32)
        if isinstance(arr, np.memmap) and getattr(arr, "_mmap", None) is not None:
            arr._mmap.madvise(mmap.MADV_DONTNEED)
        c0 = c1
    return np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0)


def fit_and_predict_ucsd_stage(
    feature_blocks: list[tuple[np.memmap | np.ndarray, list[int]]],
    feature_names: list[str],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    predict_mask_2d: np.ndarray | None = None,
    seed: int = 1401,
    neg_pos_ratio: float = 3.65,
    fast_inner: bool = False,
) -> tuple[np.ndarray, dict[str, float]]:
    """Train prior-invariant (`3.65:1`), flank-buffered (`d_vis > 3.5 px`) specialist
    `S14-UCSD` ensemble with a 100% Topography-Blind Subsurface Specialist (`HGB-Sub`).

    Combines:
      1. `HGB-Full` (deep multi-physics interaction trees with `max_features=0.68`
         column subsampling so topographic features cannot monopolize root splits),
      2. `HGB-Subsurface` (trained strictly on `nm not in PTHA.TOPO_FEATURE_NAMES`),
      3. `L2-Logistic` on robust-standardized features.
    """
    rng = np.random.default_rng(seed)
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis_grid = ndimage.distance_transform_edt(~visible_faults)
    safe_neg_fp = (~vis_fp) & (~excl_fp) & (d_vis_grid[footprint] > 3.5)

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    neg_pool = np.flatnonzero(safe_neg_fp)

    n_pos_true = int(pos_idx.size)
    n_neg_true = int(np.flatnonzero((~vis_fp) & (~excl_fp)).size)
    pi_vis_train = float(n_pos_true) / float(max(n_pos_true + n_neg_true, 1))

    target_neg = int(round(float(neg_pos_ratio) * float(pos_idx.size)))
    if neg_pool.size > target_neg:
        neg_idx = rng.choice(neg_pool, size=target_neg, replace=False)
        neg_idx.sort()
    else:
        neg_idx = neg_pool

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate(
        [
            np.ones(pos_idx.size, dtype=np.int32),
            np.zeros(neg_idx.size, dtype=np.int32),
        ]
    )
    pi_sample_weighted = float(pos_idx.size) / float(max(train_idx.size, 1))

    non_topo_mask = np.array(
        [nm not in PTHA.TOPO_FEATURE_NAMES for nm in feature_names], dtype=bool
    )

    X_tr = _assemble_blocks_rows(feature_blocks, train_idx)

    hgb_full = HistGradientBoostingClassifier(
        learning_rate=0.065 if fast_inner else 0.058,
        max_iter=115 if fast_inner else 150,
        max_leaf_nodes=31 if fast_inner else 39,
        min_samples_leaf=80,
        l2_regularization=3.5,
        max_features=0.68,
        early_stopping=False,
        random_state=seed,
    )
    hgb_full.fit(X_tr, y_train)

    hgb_sub = HistGradientBoostingClassifier(
        learning_rate=0.065 if fast_inner else 0.058,
        max_iter=105 if fast_inner else 135,
        max_leaf_nodes=27 if fast_inner else 31,
        max_depth=6,
        min_samples_leaf=100,
        l2_regularization=5.0,
        max_features=0.70,
        early_stopping=False,
        random_state=seed + 73,
    )
    hgb_sub.fit(X_tr[:, non_topo_mask], y_train)

    scaler = RobustScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=250, random_state=seed + 109)
    lr.fit(X_tr_sc, y_train)
    del X_tr, X_tr_sc
    gc.collect()

    n_fp = int(footprint.sum())
    if predict_mask_2d is not None:
        pred_rows = np.flatnonzero(predict_mask_2d[footprint])
        pred_fp = np.zeros(n_fp, dtype=np.float32)
        chunk = 250_000
        for s in range(0, pred_rows.size, chunk):
            e = min(s + chunk, pred_rows.size)
            r_sub = pred_rows[s:e]
            Xc = _assemble_blocks_rows(feature_blocks, r_sub)
            p_full = hgb_full.predict_proba(Xc)[:, 1]
            p_sub = hgb_sub.predict_proba(Xc[:, non_topo_mask])[:, 1]
            X_sc = scaler.transform(Xc)
            np.clip(X_sc, -6.0, 6.0, out=X_sc)
            p_lr = lr.predict_proba(X_sc)[:, 1]
            pred_fp[r_sub] = (0.56 * p_full + 0.30 * p_sub + 0.14 * p_lr).astype(np.float32)
            del Xc, X_sc
    else:
        pred_fp = np.empty(n_fp, dtype=np.float32)
        chunk = 250_000
        for s in range(0, n_fp, chunk):
            e = min(s + chunk, n_fp)
            Xc = _assemble_blocks_slice(feature_blocks, s, e)
            p_full = hgb_full.predict_proba(Xc)[:, 1]
            p_sub = hgb_sub.predict_proba(Xc[:, non_topo_mask])[:, 1]
            X_sc = scaler.transform(Xc)
            np.clip(X_sc, -6.0, 6.0, out=X_sc)
            p_lr = lr.predict_proba(X_sc)[:, 1]
            pred_fp[s:e] = (0.56 * p_full + 0.30 * p_sub + 0.14 * p_lr).astype(np.float32)
            del Xc, X_sc

    out_grid = np.zeros(footprint.shape, dtype=np.float32)
    out_grid[footprint] = pred_fp
    calib = {
        "pi_vis_train": round(pi_vis_train, 8),
        "pi_sample_weighted": round(pi_sample_weighted, 8),
        "n_pos_train_true": n_pos_true,
        "n_neg_train_true": n_neg_true,
        "n_total_features": len(feature_names),
        "n_subsurface_features": int(non_topo_mask.sum()),
    }
    return out_grid, calib


def fit_and_predict_ucsd_two_stage_oof_fold(
    fold: Any,
    all_folds: list[Any],
    base_blocks: list[tuple[np.memmap | np.ndarray, list[int]]],
    base_names: list[str],
    footprint: np.ndarray,
    *,
    stage1_prob_f: np.ndarray | None = None,
    stage1_cal_f: dict[str, float] | None = None,
    seed: int = 1420,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Leak-Free Two-Stage Steerable Radon Wash-Bridge Auto-Context fold fit (`H14-3b`)."""
    excl_k = fold.region_mask | fold.withheld_faults | fold.buffer_mask
    if stage1_prob_f is None or stage1_cal_f is None:
        # Dilate test quadrant by 40 px so Stage-1 test-quadrant context rays are exact
        test_pred_mask = (
            ndimage.binary_dilation(fold.region_mask, iterations=40) & footprint
        )
        stage1_prob_f, stage1_cal_f = fit_and_predict_ucsd_stage(
            base_blocks,
            base_names,
            fold.visible_faults,
            excl_k,
            footprint,
            predict_mask_2d=test_pred_mask,
            seed=seed,
        )

    other_folds = [f2 for f2 in all_folds if f2.fold_id != fold.fold_id]
    oof_s1_train = np.zeros(footprint.shape, dtype=np.float32)
    for m_idx, val_sub_f in enumerate(other_folds):
        inner_excl = excl_k | val_sub_f.region_mask | val_sub_f.withheld_faults | val_sub_f.buffer_mask
        inner_vis = fold.visible_faults & (~val_sub_f.region_mask) & (~val_sub_f.buffer_mask)
        q_mask = val_sub_f.region_mask & footprint
        sub_prob, _ = fit_and_predict_ucsd_stage(
            base_blocks,
            base_names,
            inner_vis,
            inner_excl,
            footprint,
            predict_mask_2d=q_mask,
            seed=seed + 100 + fold.fold_id * 31 + m_idx * 7,
            fast_inner=True,
        )
        oof_s1_train[q_mask] = sub_prob[q_mask]
        del sub_prob
        gc.collect()

    ac_train_full = SC.compute_spac_autocontext_features(oof_s1_train, footprint)
    # Combine OOF training quadrants + Stage-1 test quadrant for full-map inference context
    s1_combined = oof_s1_train.copy()
    test_q = fold.region_mask & footprint
    s1_combined[test_q] = stage1_prob_f[test_q]
    del oof_s1_train
    gc.collect()

    s2_names = list(base_names) + list(SC.S12_AUTOCONTEXT_FEATURE_NAMES)

    rng = np.random.default_rng(seed + 500 + fold.fold_id)
    vis_fp = fold.visible_faults[footprint]
    excl_fp = excl_k[footprint]
    d_vis_grid = ndimage.distance_transform_edt(~fold.visible_faults)
    safe_neg_fp = (~vis_fp) & (~excl_fp) & (d_vis_grid[footprint] > 3.5)
    del d_vis_grid

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    neg_pool = np.flatnonzero(safe_neg_fp)
    target_neg = int(round(3.65 * float(pos_idx.size)))
    neg_idx = (
        np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
        if neg_pool.size > target_neg
        else neg_pool
    )
    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate(
        [np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)]
    )

    ac_tr_rows = np.asarray(ac_train_full[train_idx], dtype=np.float32).copy()
    del ac_train_full
    gc.collect()

    non_topo_mask = np.array(
        [nm not in PTHA.TOPO_FEATURE_NAMES for nm in s2_names], dtype=bool
    )
    X_tr_base = _assemble_blocks_rows(base_blocks, train_idx)
    X_tr_s2 = np.hstack([X_tr_base, ac_tr_rows])
    del X_tr_base, ac_tr_rows
    gc.collect()

    hgb_full = HistGradientBoostingClassifier(
        learning_rate=0.058,
        max_iter=150,
        max_leaf_nodes=39,
        min_samples_leaf=80,
        l2_regularization=3.5,
        max_features=0.68,
        early_stopping=False,
        random_state=seed + 501,
    )
    hgb_full.fit(X_tr_s2, y_train)

    hgb_sub = HistGradientBoostingClassifier(
        learning_rate=0.058,
        max_iter=135,
        max_leaf_nodes=31,
        max_depth=6,
        min_samples_leaf=100,
        l2_regularization=5.2,
        max_features=0.70,
        early_stopping=False,
        random_state=seed + 573,
    )
    hgb_sub.fit(X_tr_s2[:, non_topo_mask], y_train)

    scaler = RobustScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr_s2), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=250, random_state=seed + 609)
    lr.fit(X_tr_sc, y_train)
    del X_tr_s2, X_tr_sc
    gc.collect()

    ac_full_arr = SC.compute_spac_autocontext_features(s1_combined, footprint)
    wb_grid = np.zeros(footprint.shape, dtype=np.float32)
    wb_grid[footprint] = np.clip(
        0.55 * ac_full_arr[:, 4] + 0.45 * ac_full_arr[:, 5], 0.0, 1.0
    )
    ac_scratch_path = DERIVED_DIR / "s14_ac_scratch.dat"
    n_fp = int(footprint.sum())
    n_ac = len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)
    ac_mm = np.memmap(ac_scratch_path, dtype=np.float32, mode="w+", shape=(n_fp, n_ac))
    ac_mm[:] = ac_full_arr
    ac_mm.flush()
    del ac_full_arr
    gc.collect()

    ac_cols = list(range(n_ac))
    s2_full_blocks = list(base_blocks) + [(ac_mm, ac_cols)]
    pred_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 250_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = _assemble_blocks_slice(s2_full_blocks, s, e)
        p_full = hgb_full.predict_proba(Xc)[:, 1]
        p_sub = hgb_sub.predict_proba(Xc[:, non_topo_mask])[:, 1]
        X_sc = scaler.transform(Xc)
        np.clip(X_sc, -6.0, 6.0, out=X_sc)
        p_lr = lr.predict_proba(X_sc)[:, 1]
        pred_fp[s:e] = (0.56 * p_full + 0.30 * p_sub + 0.14 * p_lr).astype(np.float32)
        del Xc, X_sc
    del ac_mm, s2_full_blocks
    gc.collect()

    prob_s2 = np.zeros(footprint.shape, dtype=np.float32)
    prob_s2[footprint] = pred_fp
    prob_blend = (0.72 * prob_s2 + 0.28 * s1_combined).astype(np.float32)
    prob_blend[~footprint] = 0.0
    cal_out = dict(stage1_cal_f)
    cal_out["n_total_features"] = len(s2_names)
    cal_out["n_subsurface_features"] = int(non_topo_mask.sum())
    return prob_blend, wb_grid, cal_out


def fit_and_predict_ucsd_two_stage_full_map(
    base_blocks: list[tuple[np.memmap | np.ndarray, list[int]]],
    base_names: list[str],
    cat_mask: np.ndarray,
    oof_s1_full_map: np.ndarray,
    footprint: np.ndarray,
    *,
    seed: int = 1491,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Train leak-free 2-stage full-map `S14-UCSD` ensemble on 100% of catalogue faults."""
    full_excl = ~footprint
    stage1_full_prob, cal_full = fit_and_predict_ucsd_stage(
        base_blocks,
        base_names,
        cat_mask,
        full_excl,
        footprint,
        seed=seed,
    )

    ac_oof_full = SC.compute_spac_autocontext_features(oof_s1_full_map, footprint)
    s2_names = list(base_names) + list(SC.S12_AUTOCONTEXT_FEATURE_NAMES)

    rng = np.random.default_rng(seed + 500)
    vis_fp = cat_mask[footprint]
    d_vis_grid = ndimage.distance_transform_edt(~cat_mask)
    safe_neg_fp = (~vis_fp) & (d_vis_grid[footprint] > 3.5)
    del d_vis_grid

    pos_idx = np.flatnonzero(vis_fp)
    neg_pool = np.flatnonzero(safe_neg_fp)
    target_neg = int(round(3.65 * float(pos_idx.size)))
    neg_idx = (
        np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
        if neg_pool.size > target_neg
        else neg_pool
    )
    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate(
        [np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)]
    )

    ac_tr_rows = np.asarray(ac_oof_full[train_idx], dtype=np.float32).copy()
    del ac_oof_full
    gc.collect()

    non_topo_mask = np.array(
        [nm not in PTHA.TOPO_FEATURE_NAMES for nm in s2_names], dtype=bool
    )
    X_tr_base = _assemble_blocks_rows(base_blocks, train_idx)
    X_tr_s2 = np.hstack([X_tr_base, ac_tr_rows])
    del X_tr_base, ac_tr_rows
    gc.collect()

    hgb_full = HistGradientBoostingClassifier(
        learning_rate=0.058,
        max_iter=155,
        max_leaf_nodes=39,
        min_samples_leaf=80,
        l2_regularization=3.5,
        max_features=0.68,
        early_stopping=False,
        random_state=seed + 501,
    )
    hgb_full.fit(X_tr_s2, y_train)

    hgb_sub = HistGradientBoostingClassifier(
        learning_rate=0.058,
        max_iter=140,
        max_leaf_nodes=31,
        max_depth=6,
        min_samples_leaf=100,
        l2_regularization=5.2,
        max_features=0.70,
        early_stopping=False,
        random_state=seed + 573,
    )
    hgb_sub.fit(X_tr_s2[:, non_topo_mask], y_train)

    scaler = RobustScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr_s2), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=250, random_state=seed + 609)
    lr.fit(X_tr_sc, y_train)
    del X_tr_s2, X_tr_sc
    gc.collect()

    ac_full_arr = SC.compute_spac_autocontext_features(stage1_full_prob, footprint)
    wb_grid = np.zeros(footprint.shape, dtype=np.float32)
    wb_grid[footprint] = np.clip(
        0.55 * ac_full_arr[:, 4] + 0.45 * ac_full_arr[:, 5], 0.0, 1.0
    )
    ac_scratch_path = DERIVED_DIR / "s14_ac_scratch.dat"
    n_fp = int(footprint.sum())
    n_ac = len(SC.S12_AUTOCONTEXT_FEATURE_NAMES)
    ac_mm = np.memmap(ac_scratch_path, dtype=np.float32, mode="w+", shape=(n_fp, n_ac))
    ac_mm[:] = ac_full_arr
    ac_mm.flush()
    del ac_full_arr
    gc.collect()

    ac_cols = list(range(n_ac))
    s2_full_blocks = list(base_blocks) + [(ac_mm, ac_cols)]
    pred_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 250_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = _assemble_blocks_slice(s2_full_blocks, s, e)
        p_full = hgb_full.predict_proba(Xc)[:, 1]
        p_sub = hgb_sub.predict_proba(Xc[:, non_topo_mask])[:, 1]
        X_sc = scaler.transform(Xc)
        np.clip(X_sc, -6.0, 6.0, out=X_sc)
        p_lr = lr.predict_proba(X_sc)[:, 1]
        pred_fp[s:e] = (0.56 * p_full + 0.30 * p_sub + 0.14 * p_lr).astype(np.float32)
        del Xc, X_sc
    del ac_mm, s2_full_blocks
    gc.collect()

    prob_s2 = np.zeros(footprint.shape, dtype=np.float32)
    prob_s2[footprint] = pred_fp
    prob_blend = (0.72 * prob_s2 + 0.28 * stage1_full_prob).astype(np.float32)
    prob_blend[~footprint] = 0.0
    cal_out = dict(cal_full)
    cal_out["n_total_features"] = len(s2_names)
    cal_out["n_subsurface_features"] = int(non_topo_mask.sum())
    return prob_blend, wb_grid, cal_out


def dinkelbach_regime_coupled_fold_emit(
    prob_2d: np.ndarray,
    struct_surfaces: dict[str, np.ndarray],
    *,
    wash_bridge_grid: np.ndarray | None = None,
    footprint: np.ndarray,
    train_eligible_mask: np.ndarray,
    test_eligible_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    target_pool_dots: int = 48_000,
    full_eligible_pixels: int = 4_600_000,
    piedmont_quota_frac: float = 0.18,
    subsurface_quota_frac: float = 0.14,
    min_spacing_px: float = 2.50,
    min_fold_dots: int = 5_000,
    max_fold_dots: int = 19_500,
) -> tuple[np.ndarray, dict[str, float]]:
    """Regime-Coupled Fold-Independent Dinkelbach Expected-DTI Submodular Emitter (`H14-3c`).

    1. Synthesizes the multi-regime physical crest surface coupling:
       - `0.58 * ucsd_core_crest` (Core Multi-Physics, 8-Field Odd-Parity Step & Curvature),
       - `0.24 * ucsd_sub_edge` (Subsurface Upward-Continued Dip-Migration, Bouguer, Clay-Cap & `SPI`),
       - `0.18 * wash_bridge_grid` (Steerable Radon Two-Sided Collinear Alluvial Wash-Bridge),
       across the combined concealed regime mask `piedmont_mask | subsurface_mask`.
    2. Calibrates Fold `k`'s Dinkelbach expected-intensity floor `q_floor` and marginal-gain
       stopping threshold `tau_k` strictly on `train_eligible_mask` (Fold `k`'s 3 visible
       training quadrants) and emits dots on `test_eligible_mask` via lazy greedy submodular
       selection stopping at `tau_k`.
    """
    core_crest = struct_surfaces["ucsd_core_crest"]
    sub_edge = struct_surfaces["ucsd_sub_edge"]
    piedmont_mask = struct_surfaces["piedmont_mask"]
    subsurface_mask = struct_surfaces["subsurface_mask"]

    if wash_bridge_grid is not None:
        combined_crest = np.clip(
            0.58 * core_crest + 0.24 * sub_edge + 0.18 * wash_bridge_grid,
            0.0,
            1.0,
        ).astype(np.float32)
    else:
        combined_crest = np.clip(
            0.70 * core_crest + 0.30 * sub_edge,
            0.0,
            1.0,
        ).astype(np.float32)
    combined_regime = piedmont_mask | subsurface_mask

    dots_out, alloc_meta = PTHA.dinkelbach_fold_independent_emit(
        prob_2d,
        combined_crest,
        combined_regime,
        footprint=footprint,
        train_eligible_mask=train_eligible_mask,
        test_eligible_mask=test_eligible_mask,
        pi_true=pi_true,
        pi_sample=pi_sample,
        target_pool_dots=target_pool_dots,
        full_eligible_pixels=full_eligible_pixels,
        min_spacing_px=min_spacing_px,
        min_fold_dots=min_fold_dots,
        max_fold_dots=max_fold_dots,
    )
    alloc_meta["n_regime_coupled_emitted_dots"] = int((dots_out > 0).sum())
    alloc_meta["piedmont_quota_frac"] = float(piedmont_quota_frac)
    alloc_meta["subsurface_quota_frac"] = float(subsurface_quota_frac)
    return dots_out, alloc_meta


def dinkelbach_regime_coupled_full_map_emit(
    prob_2d: np.ndarray,
    struct_surfaces: dict[str, np.ndarray],
    *,
    wash_bridge_grid: np.ndarray | None = None,
    footprint: np.ndarray,
    full_eligible_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    n_dots: int = 54_000,
    piedmont_quota_frac: float = 0.22,
    subsurface_quota_frac: float = 0.18,
    min_spacing_px: float = 2.50,
) -> np.ndarray:
    """Emit full-Nevada binary `{0.0, 1.0}` dot raster under Regime-Coupled Dinkelbach allocation."""
    prior_ratio = (pi_true / max(1.0 - pi_true, 1e-9)) * (
        max(1.0 - pi_sample, 1e-9) / max(pi_sample, 1e-9)
    )
    return SC.spac_three_regime_submodular_emit(
        prob_2d,
        struct_surfaces["ucsd_core_crest"],
        struct_surfaces["ucsd_sub_edge"],
        struct_surfaces["piedmont_mask"],
        struct_surfaces["subsurface_mask"],
        wash_bridge_grid=wash_bridge_grid,
        eligible_mask=full_eligible_mask,
        n_dots=n_dots,
        gamma=1.20,
        mhtr_weight=0.44,
        spi_weight=0.34,
        bridge_weight=0.28,
        piedmont_quota_frac=piedmont_quota_frac,
        spi_quota_frac=subsurface_quota_frac,
        prior_ratio=float(prior_ratio),
        min_spacing_px=min_spacing_px,
    )
