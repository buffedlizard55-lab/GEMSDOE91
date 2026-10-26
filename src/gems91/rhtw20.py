"""Session 20 (`S20-RHTW`): Riesz-Harmonic Native Gravity-Magnetic Tensor Worm,
Strike-Guided Hydrothermal Geothermometer Upflow & Pluvial-Decontaminated
Dual-Specialist OOF Submodular Hierarchy.

Implements preregistered hypotheses `H20-1`, `H20-2`, `H20-3`, and `H20-4` (`FTRS`)
frozen in `docs/HYPOTHESES_S20_RHTW.md`:
  1. `H20-1` (`RHTW`): Reconstructs the exact 3D harmonic vertical gravity derivative
     `G_z(x, y; z)` and upward-continued Cooper-Miller tilt worms (`z in {0, 300, 900} m`)
     from the native pre-interpolated 2D horizontal gravity gradient vector
     `(Band 18 = dG/dx, Band 11 = dG/dy)` via the 2D Riesz wavenumber operator,
     extracts the Horizontal Marussi Curvature Tensor principal ridge, corrects the
     200x `Band 03 (tmi_hg)` vs `Band 09 (tmi_vg)` unit mismatch (`IR-91-S13-01`),
     destripes E-W flight-line corrugation in `Band 02 (rtp)`, and avoids the
     `hgbr18.py:302-306` band-semantic regression (`IR-91-S20-01`).
  2. `H20-2` (`HSGD`): Rasterizes label-blind GDR 1391 spring/well excess outflow
     temperature and silica/cation reservoir disequilibrium (`dist_known_fault_px`
     strictly banned in code) and diffuses them anisotropically along local subsurface
     geophysical strike gated by transtensional Coulomb strain potency and `Band 17`
     (`cond_surf`) clay-cap edges.
  3. `H20-3` (`PDOS`): Computes multi-scale Topographic Openness (`Phi_+ - Phi_-`),
     Local Relief Model (`LRM`) breaklines, and Pluvial Paleoshoreline Decontamination
     (normal-projected subsurface gravity/basement throw distinguishing tectonic fault
     scarps from zero-throw Lake Lahontan/Bonneville wave-cut benches), strictly
     isolated to `M_full` so `M_sub` retains bitwise `0.0` dependence on `Band 12`
     and `Band 19`.
  4. `H20-4` (`FTRS`): Fold-safe visible-only fracture-mechanics fault-tip wing-crack
     lobes and en-echelon relay step-over bridges (`>2.5 px` collar guard), never
     touching withheld `truth` pixels.
"""

from __future__ import annotations

import csv
import gc
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.signal import fftconvolve

from vendor.gems57 import network as v57_net

from .dd_vtc_pu import _clean_band_edt

RHTW_CACHE_VERSION = "s20_rhtw_v1"

# Strict column layout of the 72 static features:
#   Cols 0..43  (44 features): H20-1 + subsurface physics (100% Band 12 / Band 19 FREE)
#   Cols 44..51 ( 8 features): H20-2 strike-guided hydrothermal geothermometry (100% Band 12 / Band 19 FREE)
#   Cols 52..71 (20 features): H20-3 topographic openness, LRM & pluvial-shoreline decontamination (M_full ONLY)
SUBSURFACE_BASE_NAMES: list[str] = [
    # Group A: Riesz-Harmonic Native Gravity Vector & Basement Physics (22 cols: 0..21)
    "rhtw_g_hgm_0m",
    "rhtw_g_hgm_300m",
    "rhtw_g_hgm_900m",
    "rhtw_g_riesz_gz_0m",
    "rhtw_g_riesz_gz_300m",
    "rhtw_g_riesz_tilt_0m",
    "rhtw_g_riesz_tilt_300m",
    "rhtw_g_riesz_tilt_900m",
    "rhtw_g_worm_cos_0m",
    "rhtw_g_worm_cos_300m",
    "rhtw_g_worm_persist",
    "rhtw_g_marussi_ridge",
    "rhtw_g_marussi_det",
    "rhtw_g_gzz_div",
    "rhtw_g_updip_listric_worm",
    "rhtw_b13_resid_s8",
    "rhtw_b13_resid_s24",
    "rhtw_b05_grav_slope",
    "rhtw_b15_log_depth",
    "rhtw_b15_grad_step",
    "rhtw_b15_hinge_curv",
    "rhtw_b15_grav_step_sync",
    # Group B: Destriped RTP & Unit-Calibrated Verduzco Magnetic Worms + Nematic Order (16 cols: 22..37)
    "rhtw_rtp_local_s16",
    "rhtw_rtp_hgm_150m",
    "rhtw_rtp_tilt_150m",
    "rhtw_rtp_worm_150m",
    "rhtw_rtp_worm_600m",
    "rhtw_rtp_worm_persist",
    "rhtw_tmi_hgm_nt_m",
    "rhtw_tmi_vg_nt_m",
    "rhtw_tmi_analytic_sig",
    "rhtw_tmi_verduzco_tilt",
    "rhtw_tmi_verduzco_worm",
    "rhtw_b01_mag_local_s16",
    "rhtw_b14_tmi_local_s16",
    "rhtw_nematic_order_gmb",
    "rhtw_grav_rtp_worm_sync",
    "rhtw_tri_subsurface_crest",
    # Group C: Subsurface Conductivity, GeoDAWN Radiometric TC, Geodetic Strain & Seismicity (6 cols: 38..43)
    "rhtw_b17_cond_local",
    "rhtw_b17_cond_edge",
    "rhtw_b06_rad_tc_local",
    "rhtw_b06_rad_tc_edge",
    "rhtw_transtensional_coulomb",
    "rhtw_seismic_corridor",
]

HYDROTHERMAL_NAMES: list[str] = [
    # Group D: H20-2 Strike-Guided GDR 1391 Geothermometer & Outflow Conduits (8 cols: 44..51)
    "hsgd_outflow_strike_near",
    "hsgd_outflow_strike_reg",
    "hsgd_reservoir_temp_strike",
    "hsgd_diseq_blind_conduit",
    "hsgd_well_strike_aniso",
    "hsgd_diseq_x_worm",
    "hsgd_diseq_x_transtension",
    "hsgd_cond_claycap_seal",
]

TOPO_OPENNESS_NAMES: list[str] = [
    # Group E: H20-3 Openness, LRM Breaklines & Pluvial Shoreline Decontamination (20 cols: 52..71)
    "pdos_b12_det_elev",
    "pdos_b19_slope",
    "pdos_b19_slope_local_z",
    "pdos_openness_diff_r3",
    "pdos_openness_diff_r7",
    "pdos_openness_diff_r14",
    "pdos_openness_toe_r5",
    "pdos_lrm_s4",
    "pdos_lrm_s10",
    "pdos_lrm_s22",
    "pdos_scarp_crest_toe_dipole",
    "pdos_slope_hessian_ridge_s2",
    "pdos_slope_hessian_ridge_s5",
    "pdos_slope_line_coh_11px",
    "pdos_piedmont_hinge_flexure",
    "pdos_scarp_normal_grav_throw",
    "pdos_scarp_normal_base_throw",
    "pdos_pluvial_shoreline_mimic",
    "pdos_tectonic_scarp_purity",
    "pdos_cover_burial_index",
]

ALL_STATIC_FEATURE_NAMES: list[str] = SUBSURFACE_BASE_NAMES + HYDROTHERMAL_NAMES + TOPO_OPENNESS_NAMES
STRICT_TOPO_SET: frozenset[str] = frozenset(TOPO_OPENNESS_NAMES)

SUB_E1_COLS: list[int] = list(range(0, 44))
FULL_E1_COLS: list[int] = list(range(0, 44)) + list(range(52, 72))

SUB_E2_COLS: list[int] = list(range(0, 52))
FULL_E2_COLS: list[int] = list(range(0, 72))

AUTOCONTEXT_NAMES: list[str] = [
    "ac_prob",
    "ac_logit",
    "ac_line_max_9px",
    "ac_line_ridge_9px",
    "ac_line_max_17px",
    "ac_line_ridge_17px",
    "ac_line_aniso_ratio",
    "ac_smooth_s2",
    "ac_smooth_s6",
    "ac_smooth_s15",
    "ac_dog_s2_s6",
    "ac_dog_s6_s15",
    "ac_grad_mag",
    "ac_hessian_ridge",
]

FTRS_FEATURE_NAMES: list[str] = [
    "ftrs_tip_wing_lobe",
    "ftrs_relay_stepover_bridge",
    "ftrs_sub_trunk_continuation",
]


def robust_z(arr: np.ndarray, footprint: np.ndarray, clip_lo: float = -6.0, clip_hi: float = 8.0) -> np.ndarray:
    """Footprint-normalized robust z-score with IQR/std fallback for sparse positive fields."""
    fp = np.asarray(footprint, dtype=bool)
    vals = np.asarray(arr[fp][::16], dtype=np.float32)
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    if mad < 1e-4:
        p10, p90 = [float(x) for x in np.percentile(vals, [10.0, 90.0])]
        mad = max((p90 - p10) * 0.39, float(np.std(vals)), 1e-4)
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip((arr[fp] - med) / mad, clip_lo, clip_hi).astype(np.float32)
    return out


def robust_pos_z(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    return robust_z(arr, footprint, clip_lo=0.0, clip_hi=8.0)


def local_contrast(arr: np.ndarray, footprint: np.ndarray, sigma_bg: float = 20.0) -> np.ndarray:
    bg = ndi.gaussian_filter(np.asarray(arr, dtype=np.float32), sigma=sigma_bg)
    return robust_z(arr - bg, footprint)


def grad_xy(arr: np.ndarray, sigma: float = 1.2) -> tuple[np.ndarray, np.ndarray]:
    sm = ndi.gaussian_filter(np.asarray(arr, dtype=np.float32), sigma=sigma) if sigma > 0 else np.asarray(arr, dtype=np.float32)
    gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
    gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
    return gy, gx


def hessian_ridge_both_polarities(arr: np.ndarray, sigma: float = 2.0) -> tuple[np.ndarray, np.ndarray]:
    """Scale-normalized Hessian max principal curvature magnitude (both crest and trough) + strike angle."""
    sm = ndi.gaussian_filter(np.asarray(arr, dtype=np.float32), sigma=sigma)
    gy, gx = np.gradient(sm)
    gyy, gyx = np.gradient(gy)
    gxy, gxx = np.gradient(gx)
    s2 = float(sigma * sigma)
    hxx = gxx * s2
    hyy = gyy * s2
    hxy = 0.5 * (gxy + gyx) * s2
    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    l1 = 0.5 * (tr + disc)
    l2 = 0.5 * (tr - disc)
    ridge = np.maximum(np.abs(l1), np.abs(l2)).astype(np.float32)
    # Normal direction of strongest principal curvature; strike is perpendicular (+pi/2)
    use_l1 = np.abs(l1) >= np.abs(l2)
    nx_dir = np.where(use_l1, l1 - hyy, l2 - hyy)
    ny_dir = hxy
    normal_theta = np.arctan2(ny_dir, nx_dir + 1e-12)
    strike_psi = np.mod(normal_theta + 0.5 * math.pi, math.pi).astype(np.float32)
    return ridge, strike_psi


def destripe_ew_flightlines(field: np.ndarray) -> np.ndarray:
    """Suppress E-W airborne flight-line corrugation (high ky, near-zero kx) in GeoDAWN magnetics."""
    h, w = field.shape
    pad = 48
    fp_arr = np.pad(np.asarray(field, dtype=np.float32), pad, mode="reflect")
    hp, wp = fp_arr.shape
    F = np.fft.rfft2(fp_arr)
    ky = np.fft.fftfreq(hp)[:, None]
    kx = np.fft.rfftfreq(wp)[None, :]
    kr = np.hypot(ky, kx)
    # Flight lines run E-W (corrugation wavevector along N-S, i.e., |ky| >> |kx| at λ ~ 200-600 m -> kr >= 0.14)
    aniso = (kx / (np.abs(ky) + 1e-6)) ** 2
    high_k = 1.0 / (1.0 + (0.14 / (kr + 1e-6)) ** 4)
    notch = 1.0 - 0.85 * high_k * np.exp(-aniso / 0.03)
    cleaned = np.fft.irfft2(F * notch, s=(hp, wp)).astype(np.float32)
    return cleaned[pad : pad + h, pad : pad + w]


def riesz_harmonic_gravity_worms(
    gx_b18: np.ndarray,
    gy_b11: np.ndarray,
    footprint: np.ndarray,
) -> dict[str, np.ndarray]:
    """Reconstruct exact 3D harmonic vertical gravity derivative G_z and upward-continued
    Cooper-Miller tilt worms from the native horizontal gradient vector (Band 18, Band 11)."""
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    pad = 96
    gx_p = np.pad(np.asarray(gx_b18, dtype=np.float32), pad, mode="reflect")
    gy_p = np.pad(np.asarray(gy_b11, dtype=np.float32), pad, mode="reflect")
    hp, wp = gx_p.shape

    Fx = np.fft.rfft2(gx_p)
    Fy = np.fft.rfft2(gy_p)
    # Wavenumbers in radians per 100 m pixel
    ky = (2.0 * math.pi * np.fft.fftfreq(hp))[:, None].astype(np.float32)
    kx = (2.0 * math.pi * np.fft.rfftfreq(wp))[None, :].astype(np.float32)
    k_mag = np.hypot(ky, kx).astype(np.float32)
    inv_k = np.where(k_mag > 1e-6, 1.0 / np.maximum(k_mag, 1e-6), 0.0).astype(np.float32)

    # Harmonic Riesz relation: F{dG/dx} = i*kx*F{G}, F{dG/dy} = i*ky*F{G}, F{dG/dz} = |k|*F{G}
    # => F{dG/dz} = (-i*kx*Fx - i*ky*Fy) / |k|
    F_gz0 = (-1j * kx * Fx - 1j * ky * Fy) * inv_k
    F_gz0[0, 0] = 0.0

    out: dict[str, np.ndarray] = {}
    for z_m, tag in ((0.0, "0m"), (300.0, "300m"), (900.0, "900m")):
        z_px = float(z_m) / 100.0
        att = np.exp(-k_mag * z_px).astype(np.float32)
        # Mild anti-ringing taper near Nyquist for z=0
        if z_px < 0.5:
            att = att * np.exp(-0.35 * (k_mag / math.pi) ** 2).astype(np.float32)
        gx_z = np.fft.irfft2(Fx * att, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        gy_z = np.fft.irfft2(Fy * att, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        gz_z = np.fft.irfft2(F_gz0 * att, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        hgm_z = np.hypot(gx_z, gy_z).astype(np.float32)
        eps = float(np.percentile(hgm_z[fp][::16], 15)) * 0.25 + 1e-4
        tilt_z = np.arctan2(gz_z, hgm_z + eps).astype(np.float32)
        # Cooper-Miller contact worm peaks at tilt = 0 (cos(tilt) = 1) where horizontal gradient is active
        amp_gate = np.log1p(robust_pos_z(hgm_z, fp))
        worm_z = (np.cos(tilt_z) ** 2 * amp_gate).astype(np.float32)
        out[f"hgm_{tag}"] = hgm_z
        out[f"tilt_{tag}"] = tilt_z
        out[f"worm_{tag}"] = worm_z
        if tag in ("0m", "300m"):
            out[f"gz_{tag}"] = gz_z
        if tag == "300m":
            # Gravity fault strike is perpendicular to horizontal gradient vector (gx, gy)
            out["strike_psi_g"] = np.mod(np.arctan2(gy_z, gx_z + 1e-12) + 0.5 * math.pi, math.pi).astype(
                np.float32
            )
    return out


def riesz_harmonic_rtp_worms(rtp_clean: np.ndarray, footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Compute upward-continued harmonic RTP magnetic tilt worms at z = 150 m and 600 m."""
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    pad = 80
    rp = np.pad(np.asarray(rtp_clean, dtype=np.float32), pad, mode="reflect")
    hp, wp = rp.shape
    Fr = np.fft.rfft2(rp)
    ky = (2.0 * math.pi * np.fft.fftfreq(hp))[:, None].astype(np.float32)
    kx = (2.0 * math.pi * np.fft.rfftfreq(wp))[None, :].astype(np.float32)
    k_mag = np.hypot(ky, kx).astype(np.float32)

    out: dict[str, np.ndarray] = {}
    for z_m, tag in ((150.0, "150m"), (600.0, "600m")):
        z_px = float(z_m) / 100.0
        att = np.exp(-k_mag * z_px).astype(np.float32)
        rx = np.fft.irfft2(1j * kx * Fr * att, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        ry = np.fft.irfft2(1j * ky * Fr * att, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        rz = np.fft.irfft2(k_mag * Fr * att, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        hgm = np.hypot(rx, ry).astype(np.float32)
        eps = float(np.percentile(hgm[fp][::16], 15)) * 0.25 + 1e-4
        tilt = np.arctan2(rz, hgm + eps).astype(np.float32)
        ty, tx = grad_xy(tilt, sigma=1.2)
        worm = (np.hypot(ty, tx) * np.cos(tilt) * np.log1p(robust_pos_z(hgm, fp))).astype(np.float32)
        out[f"hgm_{tag}"] = hgm
        out[f"tilt_{tag}"] = tilt
        out[f"worm_{tag}"] = worm
        if tag == "150m":
            out["strike_psi_m"] = np.mod(np.arctan2(ry, rx + 1e-12) + 0.5 * math.pi, math.pi).astype(
                np.float32
            )
    return out


def oriented_gaussian_kernel(sigma_par: float, sigma_perp: float, psi_rad: float) -> np.ndarray:
    """Build a 2D anisotropic Gaussian kernel elongated along strike `psi_rad` (measured from +x col axis)."""
    half = int(min(max(math.ceil(2.6 * sigma_par), 4), 28))
    ax = np.arange(-half, half + 1, dtype=np.float32)
    yy, xx = np.meshgrid(ax, ax, indexing="ij")
    c, s = math.cos(psi_rad), math.sin(psi_rad)
    # Strike vector in (row, col): (sin(psi), cos(psi)) or (-sin, cos); match arctan2(dy, dx) + pi/2
    # Note: in riesz_harmonic_gravity_worms, strike_psi = mod(arctan2(gy, gx) + pi/2, pi),
    # so unit strike vector in (col=x, row=y) is (cos(psi), sin(psi))!
    u_par = xx * c + yy * s
    u_perp = -xx * s + yy * c
    k = np.exp(-0.5 * ((u_par / sigma_par) ** 2 + (u_perp / sigma_perp) ** 2)).astype(np.float32)
    k /= float(k.sum()) + 1e-12
    return k


def strike_steered_diffusion(
    source_grid: np.ndarray,
    strike_psi: np.ndarray,
    sigma_par: float,
    sigma_perp: float,
    n_bins: int = 6,
) -> np.ndarray:
    """Steer sparse hydrothermal point anomalies along the local subsurface structural strike `strike_psi`."""
    out = np.zeros(source_grid.shape, dtype=np.float32)
    src = np.asarray(source_grid, dtype=np.float32)
    for b in range(n_bins):
        psi_b = math.pi * b / n_bins
        kern = oriented_gaussian_kernel(sigma_par, sigma_perp, psi_b)
        resp = fftconvolve(src, kern, mode="same").astype(np.float32)
        # Smooth angular interpolation weight cos^4(psi - psi_b)
        dpsi = strike_psi - psi_b
        w = (np.cos(dpsi) ** 4).astype(np.float32)
        out += w * resp
    # Normalize by sum_b cos^4(psi - psi_b) = 3/8 * n_bins = 2.25 for n_bins=6
    out /= (0.375 * n_bins)
    return np.maximum(out, 0.0).astype(np.float32)


def compute_hydrothermal_features(
    gdr_csv: Path,
    strike_psi: np.ndarray,
    worm_backbone: np.ndarray,
    transtension_z: np.ndarray,
    cond_edge_z: np.ndarray,
    footprint: np.ndarray,
) -> list[np.ndarray]:
    """Compute the 8 label-blind `H20-2` strike-guided GDR 1391 geothermometer features.

    Strictly forbids reading `dist_known_fault_px`.
    """
    fp = np.asarray(footprint, dtype=bool)
    shape = fp.shape
    outflow_src = np.zeros(shape, dtype=np.float32)
    res_src = np.zeros(shape, dtype=np.float32)
    diseq_src = np.zeros(shape, dtype=np.float32)
    well_presence = np.zeros(shape, dtype=np.float32)

    allowed_cols = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
    with gdr_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None
        if not allowed_cols.issubset(set(reader.fieldnames)):
            raise ValueError(f"Missing required GDR columns in {gdr_csv}")
        for rec in reader:
            # Explicitly touch ONLY allowed_cols; dist_known_fault_px is NEVER read!
            r = int(rec["row"])
            c = int(rec["col"])
            if not (0 <= r < shape[0] and 0 <= c < shape[1]) or not fp[r, c]:
                continue

            def _f(key: str) -> float:
                s = rec[key].strip()
                if not s:
                    return float("nan")
                try:
                    return float(s)
                except ValueError:
                    return float("nan")

            t_meas = _f("temp_c")
            t_qtz = _f("geothermquartz_c")
            t_ch = _f("geothermchalc_c")
            t_cat = _f("geothermcat_c")

            well_presence[r, c] = min(well_presence[r, c] + 1.0, 4.0)
            if math.isfinite(t_meas) and 0.0 <= t_meas <= 250.0:
                excess = max(0.0, t_meas - 16.0)
                if excess > outflow_src[r, c]:
                    outflow_src[r, c] = excess

            res_candidates = []
            if math.isfinite(t_qtz) and 20.0 <= t_qtz <= 320.0:
                res_candidates.append(t_qtz)
            if math.isfinite(t_ch) and 20.0 <= t_ch <= 320.0:
                res_candidates.append(t_ch)
            if math.isfinite(t_cat) and 20.0 <= t_cat <= 340.0:
                # Discount Na-K-Ca by 25 C to temper saline playa evaporite artifacts
                res_candidates.append(max(0.0, t_cat - 25.0))

            if res_candidates:
                t_res = max(res_candidates)
                res_excess = max(0.0, t_res - 55.0)
                if res_excess > res_src[r, c]:
                    res_src[r, c] = res_excess
                t_ref = t_meas if (math.isfinite(t_meas) and 0.0 <= t_meas <= 250.0) else 18.0
                diseq = max(0.0, t_res - max(t_ref, 16.0) - 20.0)
                if diseq > diseq_src[r, c]:
                    diseq_src[r, c] = diseq

    # Log-compress point amplitudes before strike-guided diffusion so single extreme wells don't dominate
    outflow_log = np.log1p(outflow_src).astype(np.float32)
    res_log = np.log1p(res_src).astype(np.float32)
    diseq_log = np.log1p(diseq_src).astype(np.float32)

    out_near = robust_pos_z(strike_steered_diffusion(outflow_log, strike_psi, 8.0, 2.2), fp)
    out_reg = robust_pos_z(strike_steered_diffusion(outflow_log, strike_psi, 18.0, 4.5), fp)
    res_str = robust_pos_z(strike_steered_diffusion(res_log, strike_psi, 14.0, 3.5), fp)
    diseq_str = robust_pos_z(strike_steered_diffusion(diseq_log, strike_psi, 14.0, 3.5), fp)

    # Compare strike-aligned well corridor vs isotropic blob to isolate fault-controlled spring alignments
    well_str = strike_steered_diffusion(well_presence, strike_psi, 12.0, 2.5)
    well_iso = ndi.gaussian_filter(well_presence, sigma=6.5).astype(np.float32)
    well_aniso = robust_pos_z(np.maximum(well_str - 0.85 * well_iso, 0.0), fp)

    diseq_worm = robust_pos_z((0.6 * diseq_str + 0.4 * out_near) * np.log1p(worm_backbone), fp)
    diseq_trans = robust_pos_z((0.6 * diseq_str + 0.4 * res_str) * np.log1p(transtension_z), fp)
    clay_seal = robust_pos_z((0.5 * diseq_str + 0.5 * out_reg) * np.log1p(cond_edge_z), fp)

    return [out_near, out_reg, res_str, diseq_str, well_aniso, diseq_worm, diseq_trans, clay_seal]


def topographic_openness_differential(elev: np.ndarray, radius_px: int) -> tuple[np.ndarray, np.ndarray]:
    """8-azimuth Topographic Openness differential (Phi_+ - Phi_-; Yokoyama et al. 2002) at `radius_px`."""
    z = np.asarray(elev, dtype=np.float32)
    h, w = z.shape
    dirs = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    r_max = max(int(radius_px), 2)
    pad = r_max + 1
    zp = np.pad(z, pad, mode="reflect")
    z0 = zp[pad : pad + h, pad : pad + w]

    # Sample 3 radial steps up to radius_px per azimuth to capture true horizon angle
    steps = sorted({max(1, r_max // 3), max(1, (2 * r_max) // 3), r_max})
    sum_pos = np.zeros((h, w), dtype=np.float32)
    sum_neg = np.zeros((h, w), dtype=np.float32)

    for dy, dx in dirs:
        max_slope = np.full((h, w), -1e6, dtype=np.float32)
        min_slope = np.full((h, w), 1e6, dtype=np.float32)
        step_len_m = 100.0 * math.hypot(dy, dx)
        for s in steps:
            zy = pad + dy * s
            zx = pad + dx * s
            dz = zp[zy : zy + h, zx : zx + w] - z0
            slope = dz / (s * step_len_m)
            np.maximum(max_slope, slope, out=max_slope)
            np.minimum(min_slope, slope, out=min_slope)
        # Zenith openness Phi_+ = pi/2 - atan(max_slope); Nadir openness Phi_- = pi/2 + atan(min_slope)
        phi_pos = 0.5 * math.pi - np.arctan(max_slope)
        phi_neg = 0.5 * math.pi + np.arctan(min_slope)
        sum_pos += phi_pos
        sum_neg += phi_neg

    phi_p = sum_pos / 8.0
    phi_n = sum_neg / 8.0
    # Differential openness (Phi_+ - Phi_-) highlights convex scarp crests (>0) and concave scarp toes (<0)
    diff = (phi_p - phi_n).astype(np.float32)
    concave_toe = (0.5 * math.pi - phi_n).astype(np.float32)
    return diff, concave_toe


def line_kernels(length: int, n_theta: int = 12) -> list[np.ndarray]:
    r = (length - 1) / 2.0
    size = length + 2
    c = size // 2
    ks: list[np.ndarray] = []
    for i in range(n_theta):
        th = math.pi * i / n_theta
        k = np.zeros((size, size), dtype=np.float64)
        for t in np.linspace(-r, r, 8 * length):
            y = c - t * math.sin(th)
            x = c + t * math.cos(th)
            y0, x0 = int(math.floor(y)), int(math.floor(x))
            fy, fx = y - y0, x - x0
            k[y0, x0] += (1.0 - fy) * (1.0 - fx)
            k[y0, x0 + 1] += (1.0 - fy) * fx
            k[y0 + 1, x0] += fy * (1.0 - fx)
            k[y0 + 1, x0 + 1] += fy * fx
        ks.append((k / k.sum()).astype(np.float32))
    return ks


def oriented_line_stats(field: np.ndarray, length: int, n_theta: int = 12) -> tuple[np.ndarray, np.ndarray]:
    """Compute max along-strike line mean and strike-vs-orthogonal ridge sharpness (`C_max - C_orth`)
    via fast direct spatial tap accumulation (zero 2D complex FFT overhead, <150 MB RAM)."""
    half_n = n_theta // 2
    r = (length - 1) // 2
    pad = r + 2
    src = np.asarray(field, dtype=np.float32)
    h, w = src.shape
    sp = np.pad(src, pad, mode="edge")
    n_taps = min(int(length), 9)
    t_vals = np.linspace(-float(r), float(r), n_taps, dtype=np.float32)
    inv_L = np.float32(1.0 / float(n_taps))

    def _line_mean(th: float) -> np.ndarray:
        acc = np.zeros((h, w), dtype=np.float32)
        st, ct = math.sin(th), math.cos(th)
        for t in t_vals:
            dy = -float(t) * st
            dx = float(t) * ct
            y0 = int(math.floor(dy))
            x0 = int(math.floor(dx))
            fy = np.float32(dy - y0)
            fx = np.float32(dx - x0)
            py = pad + y0
            px = pad + x0
            acc += (np.float32(1.0) - fy) * (np.float32(1.0) - fx) * sp[py : py + h, px : px + w]
            acc += (np.float32(1.0) - fy) * fx * sp[py : py + h, px + 1 : px + 1 + w]
            acc += fy * (np.float32(1.0) - fx) * sp[py + 1 : py + 1 + h, px : px + w]
            acc += fy * fx * sp[py + 1 : py + 1 + h, px + 1 : px + 1 + w]
        acc *= inv_L
        return acc

    c_max = np.full((h, w), -1e30, dtype=np.float32)
    c_orth_at_best = np.zeros((h, w), dtype=np.float32)
    for i in range(half_n):
        ri = _line_mean(math.pi * i / n_theta)
        ro = _line_mean(math.pi * (i + half_n) / n_theta)
        m1 = ri > c_max
        c_max = np.where(m1, ri, c_max)
        c_orth_at_best = np.where(m1, ro, c_orth_at_best)
        m2 = ro > c_max
        c_max = np.where(m2, ro, c_max)
        c_orth_at_best = np.where(m2, ri, c_orth_at_best)
        del ri, ro, m1, m2
    del sp
    ridge = np.maximum(c_max - c_orth_at_best, 0.0).astype(np.float32)
    del c_orth_at_best
    return c_max, ridge


def build_or_load_s20_features(
    features_tif: Path,
    gdr_csv: Path,
    footprint: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], np.ndarray]:
    """Build or load the 72-column `float16` memmap `(N_fp, 72)` + worm crest bonus `(N_fp,)`."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    x_path = cache_dir / f"X_{RHTW_CACHE_VERSION}_f16.npy"
    meta_path = cache_dir / f"X_{RHTW_CACHE_VERSION}_meta.json"
    worm_path = cache_dir / f"worm_bonus_{RHTW_CACHE_VERSION}_f32.npy"

    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    n_cols = len(ALL_STATIC_FEATURE_NAMES)

    if x_path.is_file() and meta_path.is_file() and worm_path.is_file():
        meta = json.loads(meta_path.read_text())
        if meta.get("names") == ALL_STATIC_FEATURE_NAMES and meta.get("n_fp") == n_fp:
            return (
                np.load(x_path, mmap_mode="r"),
                list(ALL_STATIC_FEATURE_NAMES),
                np.load(worm_path).astype(np.float32),
            )

    tmp_x = cache_dir / f"X_{RHTW_CACHE_VERSION}_f16.tmp.npy"
    X = np.lib.format.open_memmap(tmp_x, mode="w+", dtype=np.float16, shape=(n_fp, n_cols))

    def _put(col_idx: int, grid_2d: np.ndarray) -> None:
        vals = np.clip(np.asarray(grid_2d[fp], dtype=np.float32), -30.0, 30.0)
        X[:, col_idx] = vals.astype(np.float16)

    with rasterio.open(features_tif) as src:
        def _rc(b1: int) -> np.ndarray:
            return _clean_band_edt(src.read(b1).astype(np.float32), fp)

        b01 = _rc(1)   # mag_anom (nT)
        b02 = _rc(2)   # rtp (nT)
        b03 = np.maximum(_rc(3), 0.0).astype(np.float32)  # tmi_hg (nT / 200 m)
        b04 = np.maximum(_rc(4), 0.0).astype(np.float32)  # geod_2ndinv
        b05 = np.maximum(_rc(5), 0.0).astype(np.float32)  # iso_grav_anom_slope (deg)
        b06 = np.maximum(_rc(6), 0.0).astype(np.float32)  # GeoDAWN radiometric Total Count (nGy/h)
        b07 = np.maximum(_rc(7), 0.0).astype(np.float32)  # geod_shearrate
        b08 = _rc(8)                                      # geod_dilaterate
        b09 = _rc(9)                                      # tmi_vg (nT / m)
        b10 = np.maximum(_rc(10), 0.0).astype(np.float32) # deq_n100a15
        b11 = _rc(11)                                     # iso_grav_anom_vg = dG/dy (mGal / km)
        b13 = _rc(13)                                     # iso_grav_anom (mGal)
        b14 = _rc(14)                                     # tmi (nT)
        b15 = np.maximum(_rc(15), 0.0).astype(np.float32) # depth_to_base_surf (m)
        b16 = np.maximum(_rc(16), 0.0).astype(np.float32) # ieq_n100a15
        b17 = np.maximum(_rc(17), 0.0).astype(np.float32) # cond_surf
        b18 = _rc(18)                                     # iso_grav_anom_hg = dG/dx (mGal / km)

    # --- Group A (cols 0..21): Riesz-Harmonic Native Gravity Vector & Basement Physics ---
    gw = riesz_harmonic_gravity_worms(b18, b11, fp)
    _put(0, robust_pos_z(gw["hgm_0m"], fp))
    _put(1, robust_pos_z(gw["hgm_300m"], fp))
    _put(2, robust_pos_z(gw["hgm_900m"], fp))
    _put(3, robust_z(gw["gz_0m"], fp))
    _put(4, robust_z(gw["gz_300m"], fp))
    _put(5, robust_z(gw["tilt_0m"], fp))
    _put(6, robust_z(gw["tilt_300m"], fp))
    _put(7, robust_z(gw["tilt_900m"], fp))

    g_w0 = robust_pos_z(gw["worm_0m"], fp)
    g_w3 = robust_pos_z(gw["worm_300m"], fp)
    g_w9 = robust_pos_z(gw["worm_900m"], fp)
    g_persist = robust_pos_z(np.cbrt(np.maximum(g_w0 * g_w3 * g_w9, 0.0)), fp)
    _put(8, g_w0)
    _put(9, g_w3)
    _put(10, g_persist)
    psi_g = gw["strike_psi_g"]

    # Horizontal Marussi Tensor from native (B18 = dG/dx, B11 = dG/dy)
    gy_b18, gx_b18 = grad_xy(b18, sigma=1.6)
    gy_b11, gx_b11 = grad_xy(b11, sigma=1.6)
    m_xx = gx_b18
    m_yy = gy_b11
    m_xy = 0.5 * (gy_b18 + gx_b11)
    tr_m = m_xx + m_yy
    disc_m = np.hypot(m_xx - m_yy, 2.0 * m_xy)
    l1_m = 0.5 * (tr_m + disc_m)
    l2_m = 0.5 * (tr_m - disc_m)
    marussi_ridge = np.maximum(np.abs(l1_m), np.abs(l2_m)).astype(np.float32)
    marussi_det = (l1_m * l2_m).astype(np.float32)
    gzz_div = -(m_xx + m_yy)
    _put(11, robust_pos_z(marussi_ridge, fp))
    _put(12, robust_z(marussi_det, fp))
    _put(13, robust_z(gzz_div, fp))
    del gy_b18, gx_b18, gy_b11, gx_b11, m_xx, m_yy, m_xy, tr_m, disc_m, l1_m, l2_m, marussi_det, gzz_div

    # Up-dip listric migration of 900 m gravity worm toward footwall sub-crop along -grad(B15)
    by15, bx15 = grad_xy(np.log1p(b15), sigma=2.2)
    bmag15 = np.hypot(by15, bx15) + 1e-6
    uy15 = (by15 / bmag15).astype(np.float32)
    ux15 = (bx15 / bmag15).astype(np.float32)
    shift_px = np.clip(b15 * 0.0055, 0.0, 4.5).astype(np.float32)
    yy, xx = np.indices(fp.shape, dtype=np.float32)
    mig_w9 = ndi.map_coordinates(
        gw["worm_900m"],
        [np.clip(yy + uy15 * shift_px, 0.0, fp.shape[0] - 1.0), np.clip(xx + ux15 * shift_px, 0.0, fp.shape[1] - 1.0)],
        order=1,
        mode="nearest",
    ).astype(np.float32)
    _put(14, robust_pos_z(np.sqrt(np.maximum(mig_w9 * gw["worm_0m"], 0.0)), fp))
    del yy, xx, uy15, ux15, shift_px, mig_w9

    _put(15, local_contrast(b13, fp, sigma_bg=8.0))
    _put(16, local_contrast(b13, fp, sigma_bg=24.0))
    _put(17, robust_pos_z(b05, fp))
    del b13, b05

    l15 = np.log1p(b15).astype(np.float32)
    psi_b = np.mod(np.arctan2(by15, bx15 + 1e-12) + 0.5 * math.pi, math.pi).astype(np.float32)
    b15_step_z = robust_pos_z(bmag15, fp)
    b15_hinge, _ = hessian_ridge_both_polarities(l15, sigma=2.5)
    _put(18, robust_z(l15, fp))
    _put(19, b15_step_z)
    _put(20, robust_pos_z(b15_hinge, fp))
    _put(21, robust_pos_z(np.sqrt(np.maximum(b15_step_z * g_w3, 0.0)) * (np.cos(psi_b - psi_g) ** 2), fp))
    del gw, b15_hinge, by15, bx15, bmag15
    gc.collect()

    # --- Group B (cols 22..37): Destriped RTP & Unit-Calibrated Verduzco Magnetic Worms ---
    rtp_clean = destripe_ew_flightlines(b02)
    del b02
    mw = riesz_harmonic_rtp_worms(rtp_clean, fp)
    _put(22, local_contrast(rtp_clean, fp, sigma_bg=16.0))
    del rtp_clean
    _put(23, robust_pos_z(mw["hgm_150m"], fp))
    _put(24, robust_z(mw["tilt_150m"], fp))
    m_w15 = robust_pos_z(mw["worm_150m"], fp)
    m_w60 = robust_pos_z(mw["worm_600m"], fp)
    m_persist = robust_pos_z(np.sqrt(np.maximum(m_w15 * m_w60, 0.0)), fp)
    _put(25, m_w15)
    _put(26, m_w60)
    _put(27, m_persist)
    psi_m = mw["strike_psi_m"]
    del mw

    # Unit-calibrated TMI derivatives: Band 03 (nT / 200 m) / 200 -> nT / m matching Band 09 (nT / m)!
    tmi_hg_m = (b03 / 200.0).astype(np.float32)
    del b03
    asig = np.hypot(tmi_hg_m, b09).astype(np.float32)
    v_tilt = np.arctan2(b09, tmi_hg_m + 0.02).astype(np.float32)
    vty, vtx = grad_xy(v_tilt, sigma=1.2)
    v_worm = robust_pos_z(np.hypot(vty, vtx) * np.cos(v_tilt) * np.log1p(robust_pos_z(asig, fp)), fp)
    _put(28, robust_pos_z(np.log1p(tmi_hg_m * 10.0), fp))
    _put(29, robust_z(b09, fp))
    _put(30, robust_pos_z(np.log1p(asig * 10.0), fp))
    _put(31, robust_z(v_tilt, fp))
    _put(32, v_worm)
    del tmi_hg_m, b09, asig, v_tilt, vty, vtx

    _put(33, local_contrast(b01, fp, sigma_bg=16.0))
    _put(34, local_contrast(b14, fp, sigma_bg=16.0))
    del b01, b14

    # 2nd-order nematic strike-order parameter R_nem = |sum_p w_p exp(2i psi_p)| / sum_p w_p
    wg = g_persist + 0.15
    wm = m_persist + 0.15
    wb = b15_step_z + 0.15
    w_tot = wg + wm + wb
    re_2 = wg * np.cos(2.0 * psi_g) + wm * np.cos(2.0 * psi_m) + wb * np.cos(2.0 * psi_b)
    im_2 = wg * np.sin(2.0 * psi_g) + wm * np.sin(2.0 * psi_m) + wb * np.sin(2.0 * psi_b)
    r_nem = (np.hypot(re_2, im_2) / w_tot).astype(np.float32)
    _put(35, robust_pos_z(r_nem * np.log1p(g_persist + m_persist + b15_step_z), fp))
    grav_rtp_sync = robust_pos_z(np.sqrt(np.maximum(g_persist * m_persist, 0.0)) * (np.cos(psi_g - psi_m) ** 2), fp)
    _put(36, grav_rtp_sync)
    worm_backbone = robust_pos_z(0.42 * g_persist + 0.30 * m_persist + 0.16 * v_worm + 0.12 * b15_step_z, fp)
    _put(37, worm_backbone)
    # Composite subsurface strike angle weighted by local gravity vs magnetic worm strength
    psi_struct = (0.5 * np.mod(np.arctan2(im_2, re_2 + 1e-12), 2.0 * math.pi)).astype(np.float32)
    del wg, wm, wb, w_tot, re_2, im_2, r_nem, psi_m, psi_b, g_w0, g_w9, m_w15, m_w60, v_worm
    gc.collect()

    # --- Group C (cols 38..43): Conductivity, Radiometric TC, Geodetic Strain & Seismicity ---
    _put(38, local_contrast(b17, fp, sigma_bg=18.0))
    cy17, cx17 = grad_xy(b17, sigma=1.6)
    cond_edge_z = robust_pos_z(np.hypot(cy17, cx17), fp)
    _put(39, cond_edge_z)
    del b17, cy17, cx17

    _put(40, local_contrast(b06, fp, sigma_bg=18.0))
    cy06, cx06 = grad_xy(b06, sigma=1.6)
    _put(41, robust_pos_z(np.hypot(cy06, cx06), fp))
    del b06, cy06, cx06

    z_shear = robust_pos_z(local_contrast(b07, fp, sigma_bg=28.0), fp)
    z_dilat = robust_pos_z(np.maximum(b08, 0.0), fp)
    z_2nd = robust_pos_z(local_contrast(b04, fp, sigma_bg=28.0), fp)
    transtension_z = robust_pos_z(0.45 * np.sqrt(z_shear * z_dilat) + 0.35 * z_shear + 0.20 * z_2nd, fp)
    _put(42, transtension_z)
    del b04, b07, b08, z_shear, z_dilat, z_2nd

    seis_z = robust_pos_z(
        0.55 * local_contrast(np.log1p(b10), fp, sigma_bg=24.0) + 0.45 * local_contrast(b16, fp, sigma_bg=24.0),
        fp,
    )
    _put(43, seis_z)
    del b10, b16, seis_z
    gc.collect()

    # --- Group D (cols 44..51): H20-2 Strike-Guided Hydrothermal Geothermometer Conduits ---
    hyd_grids = compute_hydrothermal_features(
        gdr_csv=gdr_csv,
        strike_psi=psi_struct,
        worm_backbone=worm_backbone,
        transtension_z=transtension_z,
        cond_edge_z=cond_edge_z,
        footprint=fp,
    )
    for k_idx, hg in enumerate(hyd_grids):
        _put(44 + k_idx, hg)
    del hyd_grids, transtension_z, cond_edge_z
    gc.collect()

    # --- Group E (cols 52..71): H20-3 Openness, LRM & Pluvial Shoreline Decontamination (M_full ONLY!) ---
    with rasterio.open(features_tif) as src:
        b12 = _clean_band_edt(src.read(12).astype(np.float32), fp)  # det_elev (m)
        b19 = np.maximum(_clean_band_edt(src.read(19).astype(np.float32), fp), 0.0).astype(np.float32)  # det_elev_slope

    _put(52, robust_z(b12, fp))
    _put(53, robust_pos_z(np.log1p(b19), fp))
    slope_loc_z = local_contrast(np.log1p(b19), fp, sigma_bg=16.0)
    _put(54, slope_loc_z)

    op_diff3, _ = topographic_openness_differential(b12, 3)
    op_diff7, op_toe7 = topographic_openness_differential(b12, 7)
    op_diff14, _ = topographic_openness_differential(b12, 14)
    _, op_toe5 = topographic_openness_differential(b12, 5)
    _put(55, robust_z(op_diff3, fp))
    _put(56, robust_z(op_diff7, fp))
    _put(57, robust_z(op_diff14, fp))
    _put(58, robust_pos_z(op_toe5, fp))

    lrm4 = b12 - ndi.gaussian_filter(b12, sigma=4.0)
    lrm10 = b12 - ndi.gaussian_filter(b12, sigma=10.0)
    lrm22 = b12 - ndi.gaussian_filter(b12, sigma=22.0)
    _put(59, robust_z(lrm4, fp))
    _put(60, robust_z(lrm10, fp))
    _put(61, robust_z(lrm22, fp))
    # Scarp crest-toe dipole: rapid sign reversal of LRM across a steep slope breakline
    ly4, lx4 = grad_xy(lrm4, sigma=1.0)
    dipole = robust_pos_z(np.hypot(ly4, lx4) * np.log1p(robust_pos_z(np.abs(op_diff3) + op_toe7, fp)), fp)
    _put(62, dipole)
    del op_diff3, op_diff7, op_diff14, op_toe7, op_toe5, lrm4, lrm10, lrm22, ly4, lx4, dipole

    hr2, psi_topo = hessian_ridge_both_polarities(b19, sigma=2.0)
    hr5, _ = hessian_ridge_both_polarities(b19, sigma=5.0)
    _put(63, robust_pos_z(hr2, fp))
    _put(64, robust_pos_z(hr5, fp))
    sl_coh11, sl_ridge11 = oriented_line_stats(robust_pos_z(b19, fp), length=11, n_theta=12)
    _put(65, robust_pos_z(sl_ridge11, fp))
    del hr2, hr5

    # Piedmont range-front flexure: scarp slope break right at shallow alluvial apron (30 m < B15 < 650 m)
    apron_gate = np.exp(-0.5 * ((l15 - math.log1p(180.0)) / 1.15) ** 2).astype(np.float32)
    _put(66, robust_pos_z(np.maximum(slope_loc_z, 0.0) * apron_gate * (1.0 + 0.4 * b15_step_z), fp))

    # Pluvial Lake Lahontan / Bonneville Wave-Cut Paleoshoreline Decontamination:
    # Unit scarp-normal vector n_topo = grad(B12) / ||grad(B12)||
    ey12, ex12 = grad_xy(b12, sigma=1.5)
    emag12 = np.hypot(ey12, ex12) + 1e-5
    ny12 = (ey12 / emag12).astype(np.float32)
    nx12 = (ex12 / emag12).astype(np.float32)
    # Normal-projected subsurface gravity throw |(B18, B11) . n_topo| and basement step
    grav_throw_norm = robust_pos_z(np.abs(b18 * nx12 + b11 * ny12), fp)
    by15_raw, bx15_raw = grad_xy(l15, sigma=2.0)
    base_throw_norm = robust_pos_z(np.abs(bx15_raw * nx12 + by15_raw * ny12), fp)
    _put(67, grav_throw_norm)
    _put(68, base_throw_norm)

    # Pluvial shoreline mimic peaks on basin-margin benches (-340 m < B12 < -10 m) with line continuity
    # along contours and near-zero cross-scarp subsurface gravity/basement throw
    basin_bench_band = np.exp(-0.5 * ((b12 - (-165.0)) / 135.0) ** 2).astype(np.float32)
    throw_support = 0.60 * grav_throw_norm + 0.40 * base_throw_norm
    zero_throw_factor = (1.0 / (1.0 + 1.25 * throw_support)).astype(np.float32)
    shoreline_mimic = robust_pos_z(sl_coh11 * basin_bench_band * zero_throw_factor, fp)
    tectonic_scarp_purity = robust_pos_z(
        sl_ridge11 * (throw_support / (throw_support + 0.65)) * (0.5 + 0.5 * (np.cos(psi_topo - psi_g) ** 2)),
        fp,
    )
    _put(69, shoreline_mimic)
    _put(70, tectonic_scarp_purity)

    # Smooth [0, 1] alluvial/playa burial index (high B15 depth + low B19 surface slope)
    depth_sig = (1.0 / (1.0 + np.exp(-(l15 - math.log1p(220.0)) / 0.85))).astype(np.float32)
    flat_sig = (1.0 / (1.0 + np.exp((b19 - 3.2) / 1.4))).astype(np.float32)
    cover_idx = np.clip(depth_sig * flat_sig, 0.0, 1.0).astype(np.float32)
    _put(71, cover_idx)

    # Bounded [0, 1] multi-physics worm crest bonus on footprint
    wb_fp = worm_backbone[fp]
    lo_w, hi_w = [float(x) for x in np.percentile(wb_fp[::16], [20.0, 98.5])]
    worm_bonus_fp = np.clip((wb_fp - lo_w) / max(hi_w - lo_w, 1e-5), 0.0, 1.0).astype(np.float32)

    X.flush()
    del X
    tmp_x.replace(x_path)
    np.save(worm_path, worm_bonus_fp)
    meta_path.write_text(
        json.dumps(
            {
                "version": RHTW_CACHE_VERSION,
                "n_fp": n_fp,
                "n_cols": n_cols,
                "names": ALL_STATIC_FEATURE_NAMES,
                "sub_e1_cols": SUB_E1_COLS,
                "full_e1_cols": FULL_E1_COLS,
                "sub_e2_cols": SUB_E2_COLS,
                "full_e2_cols": FULL_E2_COLS,
            },
            indent=2,
        )
        + "\n"
    )
    gc.collect()
    return np.load(x_path, mmap_mode="r"), list(ALL_STATIC_FEATURE_NAMES), worm_bonus_fp


def compute_stage2_autocontext(prob_2d: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Compute the 14-column Stage-2 oriented line-integral & multi-scale auto-context `(N_fp, 14)` in `float16`."""
    fp = np.asarray(footprint, dtype=bool)
    p = np.where(fp, np.clip(prob_2d, 1e-5, 1.0 - 1e-5), 0.0).astype(np.float32)
    logit = np.where(fp, np.log(np.clip(p, 1e-5, 1.0 - 1e-5) / np.clip(1.0 - p, 1e-5, 1.0)), -6.0).astype(np.float32)

    c9_max, c9_ridge = oriented_line_stats(p, length=9, n_theta=12)
    c17_max, c17_ridge = oriented_line_stats(p, length=17, n_theta=12)

    s2 = ndi.gaussian_filter(p, sigma=2.0).astype(np.float32)
    s6 = ndi.gaussian_filter(p, sigma=6.0).astype(np.float32)
    s15 = ndi.gaussian_filter(p, sigma=15.0).astype(np.float32)

    gy, gx = grad_xy(s2, sigma=0.8)
    gmag = np.hypot(gy, gx).astype(np.float32)
    hr, _ = hessian_ridge_both_polarities(s2, sigma=2.0)

    cols = [
        robust_z(p, fp),
        robust_z(logit, fp),
        robust_pos_z(c9_max, fp),
        robust_pos_z(c9_ridge, fp),
        robust_pos_z(c17_max, fp),
        robust_pos_z(c17_ridge, fp),
        robust_pos_z(c17_max / (s6 + 0.02), fp),
        robust_z(s2, fp),
        robust_z(s6, fp),
        robust_z(s15, fp),
        robust_z(s2 - s6, fp),
        robust_z(s6 - s15, fp),
        robust_pos_z(gmag, fp),
        robust_pos_z(hr, fp),
    ]
    out = np.empty((int(fp.sum()), len(AUTOCONTEXT_NAMES)), dtype=np.float16)
    for j, g in enumerate(cols):
        out[:, j] = np.clip(g[fp], -30.0, 30.0).astype(np.float16)
    return out


def compute_fold_safe_visible_ftrs(
    visible_mask: np.ndarray,
    subsurface_prob_2d: np.ndarray,
    footprint: np.ndarray,
    collar_guard_px: float = 2.5,
) -> np.ndarray:
    """Compute the 3 fold-safe visible-only fracture-mechanics tip/stepover features `(N_fp, 3)`.

    Strictly consumes ONLY `visible_mask` (never touching withheld `truth` pixels!) and zeroes
    all responses within `collar_guard_px` of `visible_mask` so zero weight ever crowds the
    dead digitization collar.
    """
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_mask, dtype=bool) & fp
    shape = fp.shape
    n_fp = int(fp.sum())
    if not vis.any():
        return np.zeros((n_fp, 3), dtype=np.float32)

    d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
    collar_ok = fp & (d_vis > float(collar_guard_px))

    # 1. Reuse vendor.gems57.network (`local_strike` + `nearest_frame` + `offset_components`)
    # to resolve exact along-strike tip continuation (`|d_par| >> d_perp`) and step-over bridges!
    comp, n_comp = ndi.label(vis, structure=v57_net.STRUCT3)
    sizes = np.bincount(comp.ravel(), minlength=n_comp + 1)
    keep_vis = vis & (sizes[comp] >= 4)
    if not keep_vis.any():
        return np.zeros((n_fp, 3), dtype=np.float32)

    strike_deg, coh = v57_net.local_strike(keep_vis, smooth_px=3.0)
    d_keep, iy, ix = v57_net.nearest_frame(keep_vis)
    yy, xx = np.indices(shape, dtype=np.float32)
    dy = yy - iy.astype(np.float32)
    dx = xx - ix.astype(np.float32)

    anchor_strike = np.where(np.isfinite(strike_deg[iy, ix]), strike_deg[iy, ix], 0.0).astype(np.float32)
    anchor_coh = coh[iy, ix].astype(np.float32)
    anchor_len = np.minimum(sizes[comp[iy, ix]].astype(np.float32), 140.0)

    d_par, d_perp, _ = v57_net.offset_components(dy, dx, anchor_strike)
    abs_par = np.abs(d_par).astype(np.float32)
    d_perp = d_perp.astype(np.float32)

    # Points ahead of a visible termination tip have |d_par| > 2.2 px while d_perp stays small!
    tip_cone = (
        (abs_par > 2.0)
        * np.exp(-0.5 * ((abs_par - 6.5) / 7.5) ** 2)
        * np.exp(-0.5 * (d_perp / 3.0) ** 2)
        * anchor_coh
        * np.log1p(anchor_len)
    ).astype(np.float32)
    tip_field = ndi.gaussian_filter(np.where(collar_ok, tip_cone, 0.0), sigma=1.2).astype(np.float32)
    tip_field = np.where(collar_ok, tip_field, 0.0).astype(np.float32)

    # 2. En-echelon relay-ramp / step-over bridge between TWO DISTINCT visible fault components!
    nearest_cid = comp[iy, ix]
    diff_y = (nearest_cid[1:, :] != nearest_cid[:-1, :])
    diff_x = (nearest_cid[:, 1:] != nearest_cid[:, :-1])
    voronoi_seam = np.zeros(shape, dtype=bool)
    voronoi_seam[:-1, :] |= diff_y
    voronoi_seam[1:, :] |= diff_y
    voronoi_seam[:, :-1] |= diff_x
    voronoi_seam[:, 1:] |= diff_x
    seam_active = voronoi_seam & collar_ok & (d_keep <= 16.0)
    seam_strength = np.where(
        seam_active,
        np.exp(-0.5 * ((d_keep - 6.0) / 4.5) ** 2) * (0.4 + 0.6 * anchor_coh),
        0.0,
    ).astype(np.float32)
    relay_field = ndi.gaussian_filter(seam_strength, sigma=2.4).astype(np.float32)
    relay_field = np.where(collar_ok, relay_field, 0.0).astype(np.float32)

    # 3. Subsurface-corroborated continuation: tip + relay gated by independent OOF subsurface probability
    sub_p = np.clip(np.asarray(subsurface_prob_2d, dtype=np.float32), 0.0, 1.0)
    sub_gate = np.sqrt(sub_p)
    corroborated = ((0.62 * tip_field + 0.38 * relay_field * 3.5) * sub_gate).astype(np.float32)

    out = np.zeros((n_fp, 3), dtype=np.float32)
    out[:, 0] = robust_pos_z(tip_field, fp)[fp]
    out[:, 1] = robust_pos_z(relay_field, fp)[fp]
    out[:, 2] = robust_pos_z(corroborated, fp)[fp]
    return out
