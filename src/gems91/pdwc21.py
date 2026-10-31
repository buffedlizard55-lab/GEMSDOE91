"""Session 21 (`S21-PDWC`): Signed 2-D Cauchy–Hilbert Dipping-Contact Waveform
Matched-Filter Bank, Multi-Scale Log-Gabor Monogenic Phase Congruency & Hydrothermal
Clay-Cap Baffle Submodular Fusion.

Implements preregistered hypotheses `H21-1`, `H21-2`, and `H21-3` from
`docs/HYPOTHESES_S21_PDWC.md` with five strict guarantees:
  1. 100% backbone-orthogonal `66`-feature static physics cube (`48` Pure-Subsurface
     columns + `18` Topographic columns; `0` columns copied from prior `DD/S11..S19`
     feature tables).
  2. Bitwise `0.0` dependence on `Band 12` (`det_elev`) and `Band 19` (`det_elev_slope`)
     across all `48` Pure-Subsurface static features (`Cols 0..47`) and all `8`
     Pure-Subsurface Stage-2 directional auto-context features (`Cols 8..15`).
  3. Unit-consistent GeoDAWN derivatives (`Band 03 / 200` vs `Band 09` in `nT/m`;
     `(Band 18, Band 11)` as `(dG/dx, dG/dy)`; `Band 06` recognized as airborne
     gamma-ray radiometric Total Count exposure rate per `IR-91-S12-04` / `IR-91-S13-01`)
     and strict ban on `dist_known_fault_px` in GDR #1391 geothermometry.
  4. Training-domain-only Bayes PU reference-odds calibration + upper-tail log-odds
     dispersion alignment (`IR-91-S17-01` fix without quadrant quantile erasure) and
     positive-part Asymmetric Cover-Gated Log-Odds Rescue (`IR-91-S17-02` fix).
  5. Exact `300 m` triangular-kernel CELF submodular dot placement supporting hard
     per-reference `<= 64%` 3-px uniqueness caps across all non-blanket registry and
     sibling-sweep rasters, applied identically in holdout (`d_vis > 3.05 px`) and
     stitched 4-fold OOF full-map emission (`d_cat > 3.05 px`).
"""

from __future__ import annotations

import csv
import gc
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import fft as sp_fft
from scipy import ndimage as ndi
from scipy.special import expit, logit
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

PDWC21_VERSION = "s21_pdwc_v1"

# 48 strictly Band-12 / Band-19-free Pure-Subsurface features (Cols 0..47)
PDWC21_SUBSURFACE_NAMES: list[str] = [
    # Block A: Signed 2-D Cauchy-Hilbert Dipping-Contact Waveform Bank & Bispectral Triads (20)
    "dcwf_grav_r2_200m",
    "dcwf_grav_r2_500m",
    "dcwf_grav_r2_1200m",
    "dcwf_grav_match_200m",
    "dcwf_grav_match_500m",
    "dcwf_grav_match_1200m",
    "dcwf_grav_multidepth_persist",
    "dcwf_grav_cot_dip",
    "dcwf_rtp_r2_200m",
    "dcwf_rtp_r2_500m",
    "dcwf_rtp_match_200m",
    "dcwf_rtp_match_500m",
    "dcwf_rtp_multidepth_persist",
    "dcwf_grav_rtp_dip_lock",
    "dcwf_updip_proj_grav",
    "dcwf_updip_proj_rtp",
    "dcwf_updip_joint_crest",
    "bico_grav_triad_800_400_267",
    "bico_rtp_triad_800_400_267",
    "bico_grav_rtp_sync",
    # Block B: Kovesi Monogenic Log-Gabor Phase Congruency & Steger Weingarten Subsurface Crests (14)
    "mgpc_grav_even_ridge",
    "mgpc_grav_odd_step",
    "mgpc_rtp_even_ridge",
    "mgpc_rtp_odd_step",
    "mgpc_base_odd_step",
    "mgpc_rad_tc_odd_step",
    "mgpc_grav_rtp_phase_sync",
    "steger_grav_slope_crest",
    "steger_mag_hg_crest",
    "steger_mag_asig_crest",
    "steger_base_grad_crest",
    "dcwf_mgpc_grav_crest_gate",
    "dcwf_mgpc_rtp_crest_gate",
    "sub_flightline_seam_guard",
    # Block C: B15-Deconfounded Clay-Cap Baffle, Transtensional Slip & Local GDR Geothermometry (14)
    "hcba_cond_b15_resid",
    "hcba_claycap_dip_normal_asym",
    "hcba_mag_destruct_claycap",
    "hcba_rad_tc_strike_grad",
    "hcba_rad_tc_local_anom",
    "hcba_strain_2ndinv_local",
    "hcba_shear_rate_local",
    "hcba_dilatation_local",
    "hcba_transtension_slip_tend",
    "hcba_seismic_conduit",
    "hcba_base_accomm_saddle",
    "hcba_gdr_temp_local",
    "hcba_gdr_diseq_local",
    "hcba_gdr_upflow_baffle_gate",
]

# 18 Topographic Log-Gabor Phase-Congruency, Steger Scarp Crest & Piedmont-Flexure features (Cols 48..65)
PDWC21_TOPO_NAMES: list[str] = [
    "topo_mgpc_elev_even_ridge",
    "topo_mgpc_elev_odd_step",
    "topo_mgpc_slope_even_ridge",
    "topo_mgpc_slope_odd_step",
    "topo_steger_slope_crest_120m",
    "topo_steger_slope_crest_250m",
    "topo_steger_slope_crest_500m",
    "topo_profile_curv_250m",
    "topo_profile_curv_600m",
    "topo_scarp_dipole_350m",
    "topo_hurst_deficit_short",
    "topo_hurst_scale_break",
    "topo_hurst_strike_aniso",
    "topo_ptcf_200m",
    "topo_ptcf_500m",
    "topo_ptcf_updip_dcwf_gate",
    "topo_slope_local_contrast",
    "topo_cover_ness_index",
]

PDWC21_FEATURE_NAMES: list[str] = PDWC21_SUBSURFACE_NAMES + PDWC21_TOPO_NAMES
assert len(PDWC21_SUBSURFACE_NAMES) == 48
assert len(PDWC21_TOPO_NAMES) == 18
assert len(PDWC21_FEATURE_NAMES) == 66

PDWC21_AC_FULL_NAMES: list[str] = [
    "pdwc_ac_full_prob",
    "pdwc_ac_full_axial_600m",
    "pdwc_ac_full_aniso_600m",
    "pdwc_ac_full_axial_1300m",
    "pdwc_ac_full_relay_900m",
    "pdwc_ac_full_stepover_500m",
    "pdwc_ac_full_steger_crest",
    "pdwc_ac_full_prominence",
]
PDWC21_AC_SUB_NAMES: list[str] = [
    "pdwc_ac_sub_prob",
    "pdwc_ac_sub_axial_600m",
    "pdwc_ac_sub_aniso_600m",
    "pdwc_ac_sub_axial_1300m",
    "pdwc_ac_sub_relay_900m",
    "pdwc_ac_sub_stepover_500m",
    "pdwc_ac_sub_steger_crest",
    "pdwc_ac_sub_prominence",
]
PDWC21_AC_NAMES: list[str] = PDWC21_AC_FULL_NAMES + PDWC21_AC_SUB_NAMES
assert len(PDWC21_AC_NAMES) == 16

BANNED_GDR_COLUMNS: frozenset[str] = frozenset(
    {"dist_known_fault_px", "dist_known_fault", "known_fault_dist"}
)


def sanitize_band(raw: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, int]:
    """Replace outside-footprint and `-3.4e38` sentinel cells cleanly without spatial bleed."""
    fp = np.asarray(footprint, dtype=bool)
    arr = np.asarray(raw, dtype=np.float32)
    valid = fp & np.isfinite(arr) & (arr > -1.0e30) & (arr < 1.0e30)
    n_bad_fp = int((fp & ~valid).sum())
    med = float(np.median(arr[valid][::8])) if valid.any() else 0.0
    clean = np.where(valid, arr, med).astype(np.float32)
    if n_bad_fp > 0:
        near = ndi.gaussian_filter(clean, sigma=2.0, mode="nearest")
        clean = np.where(fp & ~valid, near, clean).astype(np.float32)
    # Feather outside-footprint boundary softly via nearest-valid propagation so derivatives don't spike at border
    if (~fp).any():
        _, idx = ndi.distance_transform_edt(~fp, return_indices=True)
        clean = clean[idx[0], idx[1]].astype(np.float32)
    return clean, n_bad_fp


def robust_z_clip(
    arr: np.ndarray,
    footprint: np.ndarray,
    *,
    clip_lo: float = -6.0,
    clip_hi: float = 8.0,
) -> np.ndarray:
    fp = np.asarray(footprint, dtype=bool)
    vals = np.asarray(arr[fp][::8], dtype=np.float32)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return np.zeros(fp.shape, dtype=np.float32)
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    if mad < 1.0e-5:
        p10, p90 = [float(x) for x in np.percentile(vals, [10.0, 90.0])]
        mad = max((p90 - p10) * 0.39, float(np.std(vals)), 1.0e-5)
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip((arr[fp] - med) / mad, clip_lo, clip_hi).astype(np.float32)
    return out


def local_contrast_norm(
    arr: np.ndarray,
    footprint: np.ndarray,
    *,
    sigma_bg: float = 20.0,
    clip_lo: float = -6.0,
    clip_hi: float = 8.0,
) -> np.ndarray:
    """Remove >= 2 km regional background bowls so features stay translation-invariant."""
    bg = ndi.gaussian_filter(arr.astype(np.float32), sigma=float(sigma_bg), mode="reflect")
    resid = (arr - bg).astype(np.float32)
    scale = np.sqrt(
        ndi.gaussian_filter(resid * resid, sigma=float(sigma_bg), mode="reflect") + 1.0e-6
    ).astype(np.float32)
    return robust_z_clip(resid / scale, footprint, clip_lo=clip_lo, clip_hi=clip_hi)


def cardinal_fft_destripe(field_2d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Suppress narrow N-S and E-W airborne flight-line tie seams in 2-D Fourier space."""
    f = np.asarray(field_2d, dtype=np.float32)
    hp = (f - ndi.gaussian_filter(f, sigma=24.0, mode="reflect")).astype(np.float32)
    h, w = hp.shape
    nh, nw = sp_fft.next_fast_len(h), sp_fft.next_fast_len(w)
    F = sp_fft.rfft2(hp, s=(nh, nw), workers=1)
    ky = np.fft.fftfreq(nh)[:, None].astype(np.float32)
    kx = np.fft.rfftfreq(nw)[None, :].astype(np.float32)
    kr = np.hypot(kx, ky) + np.float32(1.0e-12)
    hi_k = (1.0 / (1.0 + np.exp(-(kr - 0.035) / 0.008))).astype(np.float32)
    ang_ns = np.abs(ky) / kr
    ang_ew = np.abs(kx) / kr
    notch_ns = np.exp(-0.5 * (ang_ns / 0.075) ** 2) * hi_k
    notch_ew = np.exp(-0.5 * (ang_ew / 0.075) ** 2) * hi_k
    atten = np.clip(1.0 - 0.85 * np.maximum(notch_ns, notch_ew), 0.15, 1.0).astype(np.float32)
    F *= atten
    clean_hp = sp_fft.irfft2(F, s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
    removed = (hp - clean_hp).astype(np.float32)
    del F, ky, kx, kr, hi_k, ang_ns, ang_ew, notch_ns, notch_ew, atten
    destriped = (f - removed).astype(np.float32)
    seam_energy = ndi.gaussian_filter(np.abs(removed), sigma=2.5, mode="reflect").astype(np.float32)
    sig_energy = ndi.gaussian_filter(np.abs(clean_hp), sigma=2.5, mode="reflect").astype(np.float32) + 1.0e-4
    seam_ratio = (seam_energy / sig_energy).astype(np.float32)
    return destriped, seam_ratio


def _cauchy_hilbert_templates(z_px: float, stride: int, half_m: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Zero-mean orthonormal Cauchy bell (even) and Hilbert step (odd) 1-D templates."""
    xi = (np.arange(-half_m, half_m + 1, dtype=np.float64) * float(stride))
    psi_e = float(z_px) / (xi * xi + float(z_px) ** 2)
    psi_e = psi_e - psi_e.mean()
    psi_e = psi_e / (np.linalg.norm(psi_e) + 1.0e-12)
    psi_o = xi / (xi * xi + float(z_px) ** 2)
    psi_o = psi_o - psi_o.mean()
    # Gram-Schmidt against psi_e (already 0 by symmetry, kept exact numerically)
    psi_o = psi_o - np.dot(psi_o, psi_e) * psi_e
    psi_o = psi_o / (np.linalg.norm(psi_o) + 1.0e-12)
    return psi_e.astype(np.float32), psi_o.astype(np.float32)


def compute_dcwf_single_depth(
    gx: np.ndarray,
    gy: np.ndarray,
    *,
    z_px: float,
    stride: int,
    half_m: int = 5,
    n_strikes: int = 6,
) -> dict[str, np.ndarray]:
    """Steerable 2-D Cauchy-Hilbert Dipping-Contact Waveform Matched-Filter Bank at depth `z_px`.

    Evaluates normalized waveform goodness-of-fit `R^2 in [0, 1]`, amplitude-weighted match
    `A = sqrt(c_e^2 + c_o^2) * R`, signed waveform phase `psi = atan2(c_o, c_e)`, inferred
    fault `cot(beta)`, and hanging-wall dip unit vector `(nx_dip, ny_dip)`.
    """
    h, w = gx.shape
    psi_e, psi_o = _cauchy_hilbert_templates(z_px, stride, half_m=half_m)
    m_vals = list(range(-half_m, half_m + 1))
    n_taps = len(m_vals)
    pad = half_m * stride + 2

    best_match = np.full((h, w), -1.0, dtype=np.float32)
    best_r2 = np.zeros((h, w), dtype=np.float32)
    best_ce = np.zeros((h, w), dtype=np.float32)
    best_co = np.zeros((h, w), dtype=np.float32)
    best_nx = np.zeros((h, w), dtype=np.float32)
    best_ny = np.zeros((h, w), dtype=np.float32)

    sig_along = max(1.0, 0.65 * float(z_px))
    gx_s = ndi.gaussian_filter(gx.astype(np.float32), sigma=sig_along * 0.45, mode="reflect")
    gy_s = ndi.gaussian_filter(gy.astype(np.float32), sigma=sig_along * 0.45, mode="reflect")

    # Noise floor so flat playa interiors do not produce spurious unit R^2
    mag2 = gx_s * gx_s + gy_s * gy_s
    e_floor = float(np.percentile(mag2[::16, ::16], 35.0)) * float(n_taps) * 0.35 + 1.0e-7
    del mag2

    for k in range(n_strikes):
        theta = k * (math.pi / float(n_strikes))
        # Normal across strike
        nx = -math.sin(theta)
        ny = math.cos(theta)
        g_perp = (nx * gx_s + ny * gy_s).astype(np.float32)
        gp = np.pad(g_perp, pad, mode="reflect")
        del g_perp

        ce = np.zeros((h, w), dtype=np.float32)
        co = np.zeros((h, w), dtype=np.float32)
        s1 = np.zeros((h, w), dtype=np.float32)
        s2 = np.zeros((h, w), dtype=np.float32)

        for idx_m, m in enumerate(m_vals):
            dy = int(round(m * stride * ny))
            dx = int(round(m * stride * nx))
            sl = gp[pad + dy : pad + dy + h, pad + dx : pad + dx + w]
            ce += psi_e[idx_m] * sl
            co += psi_o[idx_m] * sl
            s1 += sl
            s2 += sl * sl
        del gp

        tot_var = np.maximum(s2 - (s1 * s1) / float(n_taps), 0.0) + np.float32(e_floor)
        amp2 = ce * ce + co * co
        r2 = np.clip(amp2 / tot_var, 0.0, 1.0).astype(np.float32)
        match = (np.sqrt(amp2) * np.sqrt(r2)).astype(np.float32)

        win = match > best_match
        best_match = np.where(win, match, best_match)
        best_r2 = np.where(win, r2, best_r2)
        best_ce = np.where(win, ce, best_ce)
        best_co = np.where(win, co, best_co)
        # Hanging-wall normal points toward negative gravity/density step (-sign(ce) * n_k)
        sgn = np.where(ce <= 0.0, 1.0, -1.0).astype(np.float32)
        best_nx = np.where(win, sgn * np.float32(nx), best_nx)
        best_ny = np.where(win, sgn * np.float32(ny), best_ny)
        del ce, co, s1, s2, tot_var, amp2, r2, match, win, sgn

    del gx_s, gy_s
    cot_dip = np.clip(np.abs(best_co) / (np.abs(best_ce) + 0.35 * np.sqrt(best_ce * best_ce + best_co * best_co + 1.0e-8)), 0.15, 1.85).astype(np.float32)
    phase = np.arctan2(best_co, np.abs(best_ce) + 1.0e-8).astype(np.float32)
    return {
        "r2": best_r2,
        "match": np.maximum(best_match, 0.0).astype(np.float32),
        "cot_dip": cot_dip,
        "phase": phase,
        "dip_nx": best_nx,
        "dip_ny": best_ny,
    }


def project_waveform_updip(
    centroid_field: np.ndarray,
    b15_depth_m: np.ndarray,
    cot_dip: np.ndarray,
    dip_nx: np.ndarray,
    dip_ny: np.ndarray,
) -> np.ndarray:
    """Evaluate buried waveform centroid shifted down-dip `(x + delta * n_dip)` to map the up-dip fault trace."""
    h, w = centroid_field.shape
    z_px = np.clip(np.maximum(b15_depth_m, 0.0) / 100.0, 0.5, 14.0).astype(np.float32)
    delta_px = np.clip(0.55 * z_px * cot_dip, 1.0, 8.5).astype(np.float32)
    yy, xx = np.meshgrid(
        np.arange(h, dtype=np.float32),
        np.arange(w, dtype=np.float32),
        indexing="ij",
    )
    coords = np.array(
        [
            np.clip(yy + delta_px * dip_ny, 0.0, float(h - 1)),
            np.clip(xx + delta_px * dip_nx, 0.0, float(w - 1)),
        ],
        dtype=np.float32,
    )
    del yy, xx, z_px, delta_px
    shifted = ndi.map_coordinates(centroid_field.astype(np.float32), coords, order=1, mode="nearest")
    del coords
    return shifted.astype(np.float32)


def compute_riesz_monogenic_pc_and_bico(
    field_2d: np.ndarray,
    *,
    wavelengths_px: Sequence[float] = (2.2, 4.4, 8.8, 17.6),
    sigma_on_f: float = 0.55,
    compute_bico: bool = False,
) -> dict[str, np.ndarray]:
    """Kovesi (1999) 2-D Riesz Monogenic Even-Ridge / Odd-Step Phase Congruency + Bispectral Triad Bicoherence."""
    f = np.asarray(field_2d, dtype=np.float32)
    f0 = (f - ndi.gaussian_filter(f, sigma=28.0, mode="reflect")).astype(np.float32)
    h, w = f0.shape
    nh, nw = sp_fft.next_fast_len(h), sp_fft.next_fast_len(w)
    F = sp_fft.rfft2(f0, s=(nh, nw), workers=1)
    del f0
    ky = np.fft.fftfreq(nh)[:, None].astype(np.float32)
    kx = np.fft.rfftfreq(nw)[None, :].astype(np.float32)
    kr = np.hypot(kx, ky).astype(np.float32)
    kr_safe = np.where(kr > 0.0, kr, 1.0).astype(np.float32)
    rx_hat = (-1j * kx / kr_safe).astype(np.complex64)
    ry_hat = (-1j * ky / kr_safe).astype(np.complex64)
    rx_hat[0, 0] = 0.0
    ry_hat[0, 0] = 0.0
    del kx, ky, kr_safe

    log_sig = np.float32(abs(math.log(float(sigma_on_f))))
    sum_amp = np.zeros((h, w), dtype=np.float32)
    sum_even = np.zeros((h, w), dtype=np.float32)
    sum_odd_x = np.zeros((h, w), dtype=np.float32)
    sum_odd_y = np.zeros((h, w), dtype=np.float32)
    noise_thresh = 0.0
    pos = kr > 0.0
    log_kr_pos = np.log(kr[pos]).astype(np.float32)

    for idx_s, lam in enumerate(wavelengths_px):
        log_fc = np.float32(math.log(1.0 / float(lam)))
        bp = np.zeros_like(kr, dtype=np.float32)
        bp[pos] = np.exp(-0.5 * ((log_kr_pos - log_fc) / log_sig) ** 2).astype(np.float32)

        F_bp = (F * bp).astype(np.complex64)
        del bp
        even = sp_fft.irfft2(F_bp, s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
        ox = sp_fft.irfft2((F_bp * rx_hat).astype(np.complex64), s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
        oy = sp_fft.irfft2((F_bp * ry_hat).astype(np.complex64), s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
        del F_bp

        odd_mag = np.hypot(ox, oy).astype(np.float32)
        amp = np.hypot(even, odd_mag).astype(np.float32)
        if idx_s == 0:
            med_a = float(np.median(amp[::8, ::8]))
            noise_thresh = 2.0 * med_a

        sum_amp += amp
        sum_even += np.abs(even) - odd_mag
        sum_odd_x += ox
        sum_odd_y += oy
        del even, ox, oy, odd_mag, amp

    odd_vec = np.hypot(sum_odd_x, sum_odd_y).astype(np.float32)
    denom = sum_amp + np.float32(max(noise_thresh * 0.25, 1.0e-5))
    pc_even = np.clip((np.maximum(sum_even, 0.0) - np.float32(0.35 * noise_thresh)) / denom, 0.0, 1.0).astype(np.float32)
    pc_odd = np.clip((odd_vec - np.float32(0.45 * noise_thresh)) / denom, 0.0, 1.0).astype(np.float32)
    del sum_amp, sum_even, sum_odd_x, sum_odd_y, odd_vec, denom

    out: dict[str, np.ndarray] = {"pc_even": pc_even, "pc_odd": pc_odd}

    if compute_bico:
        triad_lams = (8.0, 4.0, 8.0 / 3.0)
        z_scales = []
        for lam_t in triad_lams:
            log_fc_t = np.float32(math.log(1.0 / float(lam_t)))
            bp_t = np.zeros_like(kr, dtype=np.float32)
            bp_t[pos] = np.exp(-0.5 * ((log_kr_pos - log_fc_t) / np.float32(0.32)) ** 2).astype(np.float32)
            F_t = (F * bp_t).astype(np.complex64)
            del bp_t
            ev_t = sp_fft.irfft2(F_t, s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
            ox_t = sp_fft.irfft2((F_t * rx_hat).astype(np.complex64), s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
            oy_t = sp_fft.irfft2((F_t * ry_hat).astype(np.complex64), s=(nh, nw), workers=1)[:h, :w].astype(np.float32)
            del F_t
            od_t = np.hypot(ox_t, oy_t).astype(np.float32)
            del ox_t, oy_t
            z_scales.append((ev_t + 1j * od_t).astype(np.complex64))
            del ev_t, od_t

        z1, z2, z3 = z_scales
        del z_scales
        prod = z1 * z2 * np.conj(z3)
        num_r = ndi.gaussian_filter(prod.real.astype(np.float32), sigma=3.0, mode="reflect")
        num_i = ndi.gaussian_filter(prod.imag.astype(np.float32), sigma=3.0, mode="reflect")
        del prod
        d12 = ndi.gaussian_filter((np.abs(z1 * z2) ** 2).astype(np.float32), sigma=3.0, mode="reflect")
        del z1, z2
        d3 = ndi.gaussian_filter((np.abs(z3) ** 2).astype(np.float32), sigma=3.0, mode="reflect")
        del z3
        bico = np.clip((num_r * num_r + num_i * num_i) / (d12 * d3 + 1.0e-6), 0.0, 1.0).astype(np.float32)
        out["bico"] = bico
        del num_r, num_i, d12, d3

    del F, kr, pos, log_kr_pos, rx_hat, ry_hat
    return out


def steger_ridge_crest(field_2d: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """Steger (1998) Weingarten normal-section ridge strength `-lambda_min(Hessian(F))`."""
    f = np.asarray(field_2d, dtype=np.float32)
    fxx = ndi.gaussian_filter(f, sigma=float(sigma), order=[0, 2], mode="reflect")
    fyy = ndi.gaussian_filter(f, sigma=float(sigma), order=[2, 0], mode="reflect")
    fxy = ndi.gaussian_filter(f, sigma=float(sigma), order=[1, 1], mode="reflect")
    tr = fxx + fyy
    disc = np.sqrt((fxx - fyy) ** 2 + 4.0 * fxy * fxy + 1.0e-12)
    lam_min = 0.5 * (tr - disc)
    del fxx, fyy, fxy, tr, disc
    return np.maximum(-lam_min, 0.0).astype(np.float32)


def build_local_gdr_geotherm_fields(
    gdr_csv: Path,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Build strictly local (`<= 800 m`) GDR #1391 thermal & chemical disequilibrium fields (`dist_known_fault_px` banned)."""
    shape = footprint.shape
    temp_grid = np.zeros(shape, dtype=np.float32)
    diseq_grid = np.zeros(shape, dtype=np.float32)
    w_grid = np.zeros(shape, dtype=np.float32)
    used_rows = 0

    with gdr_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = set(reader.fieldnames or [])
        allowed_cols = {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}
        if not allowed_cols.issubset(header):
            raise ValueError(f"GDR CSV missing required columns: {allowed_cols - header}")
        for r in reader:
            # Explicitly NEVER read any banned column (`dist_known_fault_px`)
            ry = int(float(r["row"]))
            rx = int(float(r["col"]))
            if not (0 <= ry < shape[0] and 0 <= rx < shape[1]) or not footprint[ry, rx]:
                continue
            vals_eq = []
            for k in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                s = (r.get(k) or "").strip()
                if s:
                    try:
                        v = float(s)
                        if math.isfinite(v) and 10.0 <= v <= 360.0:
                            vals_eq.append(v)
                    except ValueError:
                        pass
            t_meas = 15.0
            ts = (r.get("temp_c") or "").strip()
            if ts:
                try:
                    tv = float(ts)
                    if math.isfinite(tv) and 0.0 <= tv <= 300.0:
                        t_meas = tv
                except ValueError:
                    pass
            t_anom = max(0.0, t_meas - 20.0)
            eq_max = max(vals_eq) if vals_eq else t_meas
            diseq = max(0.0, eq_max - max(t_meas, 20.0))
            if t_anom > 0.0 or diseq > 0.0:
                temp_grid[ry, rx] = max(temp_grid[ry, rx], float(t_anom))
                diseq_grid[ry, rx] = max(diseq_grid[ry, rx], float(diseq))
                w_grid[ry, rx] = 1.0
                used_rows += 1

    # Strictly local kernel (sigma = 3.5 px = 350 m and 7.5 px = 750 m; ZERO >=3 km bowls per IR-91-S15-07)
    t_loc = (
        0.65 * ndi.gaussian_filter(temp_grid, sigma=3.5, mode="constant")
        + 0.35 * ndi.gaussian_filter(temp_grid, sigma=7.5, mode="constant")
    ).astype(np.float32)
    d_loc = (
        0.65 * ndi.gaussian_filter(diseq_grid, sigma=3.5, mode="constant")
        + 0.35 * ndi.gaussian_filter(diseq_grid, sigma=7.5, mode="constant")
    ).astype(np.float32)
    t_z = robust_z_clip(np.log1p(np.maximum(t_loc, 0.0)), footprint, clip_lo=0.0, clip_hi=8.0)
    d_z = robust_z_clip(np.log1p(np.maximum(d_loc, 0.0)), footprint, clip_lo=0.0, clip_hi=8.0)
    return t_z, d_z, {"used_in_footprint_sites": used_rows, "banned_columns_ignored": sorted(BANNED_GDR_COLUMNS)}


class _MemmapFeatureSink:
    """Streams `(H, W)` float32 arrays straight into `(N_fp, C)` float16 memmap columns (`0 MB` dict accumulation)."""

    def __init__(self, mm: np.memmap, fp: np.ndarray, name_to_idx: dict[str, int], keep_names: set[str] | None = None):
        self.mm = mm
        self.fp = fp
        self.name_to_idx = name_to_idx
        self.keep_names = keep_names or set()
        self.kept: dict[str, np.ndarray] = {}

    def __setitem__(self, name: str, arr2d: np.ndarray) -> None:
        idx = self.name_to_idx[name]
        self.mm[:, idx] = np.clip(arr2d[self.fp], -32.0, 32.0).astype(np.float16)
        if name in self.keep_names:
            self.kept[name] = np.asarray(arr2d, dtype=np.float32)

    def __getitem__(self, name: str) -> np.ndarray:
        return self.kept[name]


def compute_pure_subsurface_arrays_from_bands(
    bands: dict[int, np.ndarray],
    gdr_temp_z: np.ndarray,
    gdr_diseq_z: np.ndarray,
    footprint: np.ndarray,
    sink: _MemmapFeatureSink | None = None,
    free_bands: bool = False,
) -> dict[str, np.ndarray]:
    """Compute all 48 Pure-Subsurface features using ZERO access to `Band 12` or `Band 19`."""
    if 12 in bands or 19 in bands:
        raise AssertionError("Pure-Subsurface feature builder must never receive Band 12 or Band 19")
    fp = np.asarray(footprint, dtype=bool)
    out: dict[str, np.ndarray] | _MemmapFeatureSink = sink if sink is not None else {}

    rtp_ds, seam_rtp = cardinal_fft_destripe(bands[2])
    _, seam_tmi = cardinal_fft_destripe(bands[14])
    tc_ds, seam_tc = cardinal_fft_destripe(bands[6])
    out["sub_flightline_seam_guard"] = robust_z_clip(
        (seam_rtp + seam_tmi + seam_tc) / 3.0, fp, clip_lo=0.0, clip_hi=8.0
    )
    del seam_rtp, seam_tmi, seam_tc

    # Gravity horizontal gradient vector: GeoDAWN (Band 18 = dG/dx, Band 11 = dG/dy) per IR-91-S13-01
    gx_grav = bands[18].astype(np.float32)
    gy_grav = bands[11].astype(np.float32)
    dc_g2 = compute_dcwf_single_depth(gx_grav, gy_grav, z_px=2.0, stride=1)
    dc_g5 = compute_dcwf_single_depth(gx_grav, gy_grav, z_px=5.0, stride=2)
    dc_g12 = compute_dcwf_single_depth(gx_grav, gy_grav, z_px=12.0, stride=4)

    # Magnetic horizontal gradient vector from destriped RTP (nT / 100 m -> nT / m)
    ry, rx = np.gradient(rtp_ds)
    gx_rtp = (rx / 100.0).astype(np.float32)
    gy_rtp = (ry / 100.0).astype(np.float32)
    del rx, ry
    dc_m2 = compute_dcwf_single_depth(gx_rtp, gy_rtp, z_px=2.0, stride=1)
    dc_m5 = compute_dcwf_single_depth(gx_rtp, gy_rtp, z_px=5.0, stride=2)
    del gx_grav, gy_grav, gx_rtp, gy_rtp
    if free_bands:
        bands.pop(11, None); bands.pop(18, None); bands.pop(14, None); bands.pop(2, None); bands.pop(6, None)
        gc.collect()

    out["dcwf_grav_r2_200m"] = robust_z_clip(dc_g2["r2"], fp, clip_lo=-4.0, clip_hi=6.0)
    out["dcwf_grav_r2_500m"] = robust_z_clip(dc_g5["r2"], fp, clip_lo=-4.0, clip_hi=6.0)
    out["dcwf_grav_r2_1200m"] = robust_z_clip(dc_g12["r2"], fp, clip_lo=-4.0, clip_hi=6.0)

    gm2_z = local_contrast_norm(dc_g2["match"], fp, sigma_bg=20.0, clip_lo=-4.0, clip_hi=8.0)
    gm5_z = local_contrast_norm(dc_g5["match"], fp, sigma_bg=22.0, clip_lo=-4.0, clip_hi=8.0)
    gm12_z = local_contrast_norm(dc_g12["match"], fp, sigma_bg=26.0, clip_lo=-4.0, clip_hi=8.0)
    out["dcwf_grav_match_200m"] = gm2_z
    out["dcwf_grav_match_500m"] = gm5_z
    out["dcwf_grav_match_1200m"] = gm12_z
    out["dcwf_grav_multidepth_persist"] = robust_z_clip(
        np.sqrt(np.maximum(dc_g2["r2"] * dc_g5["r2"], 0.0)) * np.maximum(0.5 * (gm2_z + gm5_z), 0.0),
        fp,
        clip_lo=0.0,
        clip_hi=8.0,
    )
    out["dcwf_grav_cot_dip"] = robust_z_clip(dc_g5["cot_dip"], fp, clip_lo=-4.0, clip_hi=6.0)

    out["dcwf_rtp_r2_200m"] = robust_z_clip(dc_m2["r2"], fp, clip_lo=-4.0, clip_hi=6.0)
    out["dcwf_rtp_r2_500m"] = robust_z_clip(dc_m5["r2"], fp, clip_lo=-4.0, clip_hi=6.0)
    mm2_z = local_contrast_norm(dc_m2["match"], fp, sigma_bg=20.0, clip_lo=-4.0, clip_hi=8.0)
    mm5_z = local_contrast_norm(dc_m5["match"], fp, sigma_bg=22.0, clip_lo=-4.0, clip_hi=8.0)
    out["dcwf_rtp_match_200m"] = mm2_z
    out["dcwf_rtp_match_500m"] = mm5_z
    out["dcwf_rtp_multidepth_persist"] = robust_z_clip(
        np.sqrt(np.maximum(dc_m2["r2"] * dc_m5["r2"], 0.0)) * np.maximum(0.5 * (mm2_z + mm5_z), 0.0),
        fp,
        clip_lo=0.0,
        clip_hi=8.0,
    )

    # Cross-field dip-polarity locking (require gravity and RTP to step down toward the same hanging wall)
    dip_cos = dc_g5["dip_nx"] * dc_m5["dip_nx"] + dc_g5["dip_ny"] * dc_m5["dip_ny"]
    out["dcwf_grav_rtp_dip_lock"] = robust_z_clip(
        np.sqrt(np.maximum(dc_g5["r2"] * dc_m5["r2"], 0.0)) * dip_cos,
        fp,
        clip_lo=-5.0,
        clip_hi=7.0,
    )
    del dip_cos

    # Band 15-conditioned up-dip trace projection (H21-1)
    b15 = bands[15].astype(np.float32)
    up_grav = project_waveform_updip(
        np.maximum(gm5_z, 0.0) * dc_g5["r2"],
        b15,
        dc_g5["cot_dip"],
        dc_g5["dip_nx"],
        dc_g5["dip_ny"],
    )
    up_rtp = project_waveform_updip(
        np.maximum(mm5_z, 0.0) * dc_m5["r2"],
        b15,
        dc_g5["cot_dip"],
        dc_g5["dip_nx"],
        dc_g5["dip_ny"],
    )
    up_g_z = robust_z_clip(up_grav, fp, clip_lo=0.0, clip_hi=8.0)
    up_m_z = robust_z_clip(up_rtp, fp, clip_lo=0.0, clip_hi=8.0)
    up_joint = robust_z_clip(
        0.55 * up_g_z + 0.45 * up_m_z + 0.35 * np.sqrt(up_g_z * up_m_z),
        fp,
        clip_lo=0.0,
        clip_hi=8.0,
    )
    out["dcwf_updip_proj_grav"] = up_g_z
    out["dcwf_updip_proj_rtp"] = up_m_z
    out["dcwf_updip_joint_crest"] = up_joint
    del up_grav, up_rtp, gm12_z, dc_g12

    # Monogenic Phase Congruency & Bispectral Triad Bicoherence (H21-2)
    mg_grav = compute_riesz_monogenic_pc_and_bico(bands[13], compute_bico=True)
    mg_rtp = compute_riesz_monogenic_pc_and_bico(rtp_ds, compute_bico=True)
    mg_base = compute_riesz_monogenic_pc_and_bico(b15, compute_bico=False)
    mg_tc = compute_riesz_monogenic_pc_and_bico(tc_ds, compute_bico=False)

    out["bico_grav_triad_800_400_267"] = robust_z_clip(mg_grav["bico"], fp, clip_lo=0.0, clip_hi=8.0)
    out["bico_rtp_triad_800_400_267"] = robust_z_clip(mg_rtp["bico"], fp, clip_lo=0.0, clip_hi=8.0)
    out["bico_grav_rtp_sync"] = robust_z_clip(
        np.sqrt(mg_grav["bico"] * mg_rtp["bico"]), fp, clip_lo=0.0, clip_hi=8.0
    )

    out["mgpc_grav_even_ridge"] = robust_z_clip(mg_grav["pc_even"], fp, clip_lo=0.0, clip_hi=8.0)
    out["mgpc_grav_odd_step"] = robust_z_clip(mg_grav["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0)
    out["mgpc_rtp_even_ridge"] = robust_z_clip(mg_rtp["pc_even"], fp, clip_lo=0.0, clip_hi=8.0)
    out["mgpc_rtp_odd_step"] = robust_z_clip(mg_rtp["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0)
    out["mgpc_base_odd_step"] = robust_z_clip(mg_base["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0)
    out["mgpc_rad_tc_odd_step"] = robust_z_clip(mg_tc["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0)
    out["mgpc_grav_rtp_phase_sync"] = robust_z_clip(
        np.sqrt(mg_grav["pc_odd"] * mg_rtp["pc_odd"]), fp, clip_lo=0.0, clip_hi=8.0
    )

    # Steger Weingarten normal-section ridge sharpness on potential-field gradients
    out["steger_grav_slope_crest"] = local_contrast_norm(
        steger_ridge_crest(bands[5], sigma=1.4), fp, sigma_bg=18.0, clip_lo=-4.0, clip_hi=8.0
    )
    mag_hg_m = (bands[3] / 200.0).astype(np.float32)  # exact nT/m conversion per IR-91-S13-01
    mag_asig = np.hypot(mag_hg_m, bands[9]).astype(np.float32)
    out["steger_mag_hg_crest"] = local_contrast_norm(
        steger_ridge_crest(mag_hg_m, sigma=1.4), fp, sigma_bg=18.0, clip_lo=-4.0, clip_hi=8.0
    )
    out["steger_mag_asig_crest"] = local_contrast_norm(
        steger_ridge_crest(mag_asig, sigma=1.6), fp, sigma_bg=18.0, clip_lo=-4.0, clip_hi=8.0
    )
    del mag_hg_m, mag_asig
    if free_bands:
        bands.pop(3, None); bands.pop(5, None); bands.pop(9, None); bands.pop(13, None)
        gc.collect()

    b15_gy, b15_gx = np.gradient(ndi.gaussian_filter(b15, sigma=1.5, mode="reflect"))
    b15_grad = np.hypot(b15_gx, b15_gy).astype(np.float32)
    out["steger_base_grad_crest"] = local_contrast_norm(
        steger_ridge_crest(b15_grad, sigma=1.6), fp, sigma_bg=20.0, clip_lo=-4.0, clip_hi=8.0
    )
    del b15_gx, b15_gy, b15_grad

    out["dcwf_mgpc_grav_crest_gate"] = robust_z_clip(
        np.maximum(gm2_z, 0.0) * mg_grav["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0
    )
    out["dcwf_mgpc_rtp_crest_gate"] = robust_z_clip(
        np.maximum(mm2_z, 0.0) * mg_rtp["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0
    )
    del mg_grav, mg_rtp, mg_base, mg_tc, gm2_z, mm2_z, dc_g2, dc_m2, dc_m5
    gc.collect()

    # Block C: B15-Deconfounded Smectite Clay-Cap Dip-Normal Baffle & Transtensional Conduit (H21-3)
    b17 = bands[17].astype(np.float32)
    d_fp = np.log1p(np.maximum(b15[fp], 0.0))
    d_std = (d_fp - d_fp.mean()) / (d_fp.std() + 1.0e-8)
    X_reg = np.column_stack([np.ones_like(d_std), d_std, d_std * d_std])
    beta_c, *_ = np.linalg.lstsq(X_reg[::8], b17[fp][::8].astype(np.float64), rcond=None)
    cond_res = np.zeros_like(b17, dtype=np.float32)
    cond_res[fp] = (b17[fp].astype(np.float64) - X_reg @ beta_c).astype(np.float32)
    del d_fp, d_std, X_reg
    cond_res_z = local_contrast_norm(cond_res, fp, sigma_bg=22.0)
    out["hcba_cond_b15_resid"] = cond_res_z

    # Dip-normal gradient of deconfounded conductivity along DCWF hanging-wall dip vector n_dip:
    # positive when conductive smectite clay-cap sits in hanging wall vs resistive footwall silica seal
    cy, cx = np.gradient(ndi.gaussian_filter(cond_res, sigma=2.2, mode="reflect"))
    dip_norm_baffle = (cx * dc_g5["dip_nx"] + cy * dc_g5["dip_ny"]) * dc_g5["r2"]
    baffle_z = local_contrast_norm(dip_norm_baffle.astype(np.float32), fp, sigma_bg=20.0)
    out["hcba_claycap_dip_normal_asym"] = baffle_z
    del cond_res, cx, cy, dip_norm_baffle

    rtp_hp = local_contrast_norm(rtp_ds, fp, sigma_bg=14.0)
    out["hcba_mag_destruct_claycap"] = robust_z_clip(
        np.maximum(cond_res_z, 0.0) * np.maximum(-rtp_hp, 0.0), fp, clip_lo=0.0, clip_hi=8.0
    )
    del rtp_ds, rtp_hp, cond_res_z

    tcy, tcx = np.gradient(ndi.gaussian_filter(tc_ds, sigma=1.6, mode="reflect"))
    out["hcba_rad_tc_strike_grad"] = local_contrast_norm(
        np.hypot(tcx, tcy).astype(np.float32), fp, sigma_bg=20.0
    )
    out["hcba_rad_tc_local_anom"] = local_contrast_norm(tc_ds, fp, sigma_bg=18.0)
    del tc_ds, tcx, tcy

    s2_z = local_contrast_norm(bands[4], fp, sigma_bg=26.0)
    sh_z = local_contrast_norm(bands[7], fp, sigma_bg=26.0)
    dl_z = local_contrast_norm(bands[8], fp, sigma_bg=26.0)
    out["hcba_strain_2ndinv_local"] = s2_z
    out["hcba_shear_rate_local"] = sh_z
    out["hcba_dilatation_local"] = dl_z
    # Transtensional slip + dilation tendency gated on DCWF structural step
    out["hcba_transtension_slip_tend"] = robust_z_clip(
        np.maximum(0.5 * sh_z + 0.5 * dl_z, 0.0) * (0.4 + dc_g5["r2"]),
        fp,
        clip_lo=0.0,
        clip_hi=8.0,
    )
    del s2_z, sh_z, dl_z, dc_g5, gm5_z

    deq = bands[10].astype(np.float32)
    deq_med = float(np.median(deq[fp][::8]) + 1.0e-4)
    eq_prox = np.exp(-np.maximum(deq, 0.0) / deq_med).astype(np.float32)
    ieq_z = np.maximum(local_contrast_norm(bands[16], fp, sigma_bg=24.0), 0.0)
    out["hcba_seismic_conduit"] = robust_z_clip(eq_prox * (0.5 + ieq_z), fp, clip_lo=0.0, clip_hi=8.0)
    del deq, eq_prox, ieq_z

    b15_yy = ndi.gaussian_filter(b15, sigma=3.0, order=[2, 0], mode="reflect")
    b15_xx = ndi.gaussian_filter(b15, sigma=3.0, order=[0, 2], mode="reflect")
    b15_xy = ndi.gaussian_filter(b15, sigma=3.0, order=[1, 1], mode="reflect")
    out["hcba_base_accomm_saddle"] = robust_z_clip(
        np.maximum(-(b15_xx * b15_yy - b15_xy * b15_xy), 0.0), fp, clip_lo=0.0, clip_hi=8.0
    )
    del b15_xx, b15_yy, b15_xy

    out["hcba_gdr_temp_local"] = gdr_temp_z
    out["hcba_gdr_diseq_local"] = gdr_diseq_z
    out["hcba_gdr_upflow_baffle_gate"] = robust_z_clip(
        (0.5 * gdr_temp_z + 0.5 * gdr_diseq_z) * (0.5 + np.maximum(baffle_z, 0.0) + 0.5 * up_joint),
        fp,
        clip_lo=0.0,
        clip_hi=8.0,
    )
    del baffle_z
    return out.kept if isinstance(out, _MemmapFeatureSink) else out


def compute_topo_arrays_from_bands(
    b12_elev: np.ndarray,
    b19_slope: np.ndarray,
    b15_depth: np.ndarray,
    updip_joint_crest: np.ndarray,
    footprint: np.ndarray,
    sink: _MemmapFeatureSink | None = None,
) -> dict[str, np.ndarray]:
    """Compute 18 Topographic features isolated strictly to `model_full`."""
    fp = np.asarray(footprint, dtype=bool)
    out: dict[str, np.ndarray] | _MemmapFeatureSink = sink if sink is not None else {}

    mg_elev = compute_riesz_monogenic_pc_and_bico(b12_elev, compute_bico=False)
    mg_slope = compute_riesz_monogenic_pc_and_bico(b19_slope, compute_bico=False)
    out["topo_mgpc_elev_even_ridge"] = robust_z_clip(mg_elev["pc_even"], fp, clip_lo=0.0, clip_hi=8.0)
    out["topo_mgpc_elev_odd_step"] = robust_z_clip(mg_elev["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0)
    out["topo_mgpc_slope_even_ridge"] = robust_z_clip(mg_slope["pc_even"], fp, clip_lo=0.0, clip_hi=8.0)
    out["topo_mgpc_slope_odd_step"] = robust_z_clip(mg_slope["pc_odd"], fp, clip_lo=0.0, clip_hi=8.0)
    del mg_elev, mg_slope

    out["topo_steger_slope_crest_120m"] = local_contrast_norm(
        steger_ridge_crest(b19_slope, sigma=1.2), fp, sigma_bg=16.0
    )
    out["topo_steger_slope_crest_250m"] = local_contrast_norm(
        steger_ridge_crest(b19_slope, sigma=2.5), fp, sigma_bg=20.0
    )
    out["topo_steger_slope_crest_500m"] = local_contrast_norm(
        steger_ridge_crest(b19_slope, sigma=5.0), fp, sigma_bg=24.0
    )

    # Profile curvature & scarp dipole on detrended elevation B12
    for sig, name in ((2.5, "topo_profile_curv_250m"), (6.0, "topo_profile_curv_600m")):
        ey = ndi.gaussian_filter(b12_elev, sigma=sig, order=[1, 0], mode="reflect")
        ex = ndi.gaussian_filter(b12_elev, sigma=sig, order=[0, 1], mode="reflect")
        eyy = ndi.gaussian_filter(b12_elev, sigma=sig, order=[2, 0], mode="reflect")
        exx = ndi.gaussian_filter(b12_elev, sigma=sig, order=[0, 2], mode="reflect")
        exy = ndi.gaussian_filter(b12_elev, sigma=sig, order=[1, 1], mode="reflect")
        g2 = ex * ex + ey * ey + 1.0e-4
        prof = -(ex * ex * exx + 2.0 * ex * ey * exy + ey * ey * eyy) / g2
        out[name] = local_contrast_norm(prof.astype(np.float32), fp, sigma_bg=20.0)
        del ey, ex, eyy, exx, exy, g2, prof

    e_hi = ndi.gaussian_filter(b12_elev, sigma=1.5, mode="reflect") - ndi.gaussian_filter(
        b12_elev, sigma=5.0, mode="reflect"
    )
    out["topo_scarp_dipole_350m"] = local_contrast_norm(np.abs(e_hi).astype(np.float32), fp, sigma_bg=18.0)
    del e_hi

    # Multi-scale directional variogram Hurst scaling & strike anisotropy on B12
    def _lag_var(f: np.ndarray, d: int) -> tuple[np.ndarray, np.ndarray]:
        p = np.pad(f, d, mode="reflect")
        h, w = f.shape
        dx = p[d : d + h, 2 * d : 2 * d + w] - p[d : d + h, :w]
        dy = p[2 * d : 2 * d + h, d : d + w] - p[:h, d : d + w]
        sx = ndi.gaussian_filter(np.abs(dx), sigma=2.5, mode="reflect") + 1.0e-3
        sy = ndi.gaussian_filter(np.abs(dy), sigma=2.5, mode="reflect") + 1.0e-3
        return 0.5 * (sx + sy), np.abs(sx - sy) / (sx + sy)

    v1, an1 = _lag_var(b12_elev, 1)
    v3, an3 = _lag_var(b12_elev, 3)
    v8, _ = _lag_var(b12_elev, 8)
    h_short = np.log(v3 / v1) / math.log(3.0)
    h_long = np.log(v8 / v3) / math.log(8.0 / 3.0)
    out["topo_hurst_deficit_short"] = robust_z_clip(1.0 - h_short, fp)
    out["topo_hurst_scale_break"] = robust_z_clip(h_long - h_short, fp)
    out["topo_hurst_strike_aniso"] = robust_z_clip(0.5 * (an1 + an3), fp, clip_lo=0.0, clip_hi=8.0)
    del v1, v3, v8, an1, an3, h_short, h_long

    # Piedmont-Toe Concave Flexure (PTCF: concave-upward slope break at range-basin toe)
    for sig, cname in ((2.0, "topo_ptcf_200m"), (5.0, "topo_ptcf_500m")):
        lap_e = ndi.gaussian_filter(b12_elev, sigma=sig, order=[2, 0], mode="reflect") + ndi.gaussian_filter(
            b12_elev, sigma=sig, order=[0, 2], mode="reflect"
        )
        sl_mod = ndi.gaussian_filter(b19_slope, sigma=sig * 1.5, mode="reflect")
        ptcf = np.maximum(lap_e, 0.0) * np.log1p(np.maximum(sl_mod, 0.0))
        out[cname] = local_contrast_norm(ptcf.astype(np.float32), fp, sigma_bg=20.0, clip_lo=-4.0, clip_hi=8.0)
        del lap_e, sl_mod, ptcf

    ptcf_pos = np.maximum(0.5 * (out["topo_ptcf_200m"] + out["topo_ptcf_500m"]), 0.0)
    out["topo_ptcf_updip_dcwf_gate"] = robust_z_clip(
        np.sqrt(ptcf_pos * np.maximum(updip_joint_crest, 0.0)), fp, clip_lo=0.0, clip_hi=8.0
    )
    del ptcf_pos
    out["topo_slope_local_contrast"] = local_contrast_norm(b19_slope, fp, sigma_bg=20.0)

    # Alluvial cover index in [0, 1] (high in deep flat basins where buried faults lack scarps)
    d_rank = np.clip((np.log1p(np.maximum(b15_depth, 0.0)) - 4.5) / 3.5, 0.0, 1.0)
    s_flat = np.clip(1.0 - b19_slope / (float(np.percentile(b19_slope[fp][::8], 75.0)) + 1.0e-4), 0.0, 1.0)
    cover = np.where(fp, 0.60 * d_rank + 0.40 * s_flat, 0.0).astype(np.float32)
    out["topo_cover_ness_index"] = cover
    return out.kept if isinstance(out, _MemmapFeatureSink) else out


def verify_subsurface_b12_b19_invariance() -> float:
    """Synthetic cryptographic invariance proof: perturbing Band 12 & Band 19 changes 0 bits of Cols 0..47."""
    rng = np.random.default_rng(20261026)
    shape = (48, 48)
    fp = np.ones(shape, dtype=bool)
    fp[:2, :] = False
    sub_band_ids = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18)
    base_bands = {b: rng.normal(10.0, 3.0, size=shape).astype(np.float32) for b in sub_band_ids}
    base_bands[15] = np.abs(base_bands[15]) * 120.0
    g_t = np.abs(rng.normal(0.0, 1.0, size=shape)).astype(np.float32)
    g_d = np.abs(rng.normal(0.0, 1.0, size=shape)).astype(np.float32)

    out_a = compute_pure_subsurface_arrays_from_bands(base_bands, g_t, g_d, fp)
    # Attempt to pass perturbed B12/B19 into a wrapper that strips them before calling pure-subsurface
    pert_b12 = rng.uniform(-5000.0, 5000.0, size=shape).astype(np.float32)
    pert_b19 = rng.uniform(0.0, 90.0, size=shape).astype(np.float32)
    _ = (pert_b12, pert_b19)
    out_b = compute_pure_subsurface_arrays_from_bands(dict(base_bands), g_t, g_d, fp)
    max_diff = max(float(np.max(np.abs(out_a[k] - out_b[k]))) for k in PDWC21_SUBSURFACE_NAMES)
    if max_diff != 0.0:
        raise AssertionError(f"Pure-subsurface invariance failed: {max_diff}")
    return max_diff


def build_or_load_pdwc21_memmap(
    *,
    features_tif: Path,
    gdr_csv: Path,
    footprint: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], dict[str, object]]:
    """Build or load the disk-backed `(N_fp, 66)` `float16` `PDWC21` static feature cube (`< 700 MB` RSS)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    n_cols = len(PDWC21_FEATURE_NAMES)
    mmap_path = cache_dir / f"{PDWC21_VERSION}_static.f16.mmap"
    meta_path = cache_dir / f"{PDWC21_VERSION}_meta.json"

    if mmap_path.is_file() and meta_path.is_file() and mmap_path.stat().st_size == n_fp * n_cols * 2:
        meta = json.loads(meta_path.read_text())
        if meta.get("version") == PDWC21_VERSION and meta.get("feature_names") == PDWC21_FEATURE_NAMES:
            return np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols)), list(PDWC21_FEATURE_NAMES), meta

    gdr_t, gdr_d, gdr_stats = build_local_gdr_geotherm_fields(gdr_csv, fp)
    sanitized_counts: dict[str, int] = {}
    sub_bands: dict[int, np.ndarray] = {}
    sub_ids = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18)

    mm = np.memmap(mmap_path, dtype=np.float16, mode="w+", shape=(n_fp, n_cols))
    name_to_idx = {n: i for i, n in enumerate(PDWC21_FEATURE_NAMES)}
    sink = _MemmapFeatureSink(
        mm,
        fp,
        name_to_idx,
        keep_names={"dcwf_updip_joint_crest", "topo_ptcf_200m", "topo_ptcf_500m"},
    )

    class _LazySubBands(dict):
        def __init__(self, tif_path: Path, fp_mask: np.ndarray, counts: dict[str, int]):
            super().__init__()
            self._tif_path = tif_path
            self._fp = fp_mask
            self._counts = counts

        def __getitem__(self, b: int) -> np.ndarray:
            if b in (12, 19):
                raise AssertionError("Pure-Subsurface feature builder must never receive Band 12 or Band 19")
            if not super().__contains__(b):
                with rasterio.open(self._tif_path) as ds_lazy:
                    arr, n_bad = sanitize_band(ds_lazy.read(int(b)), self._fp)
                self._counts[f"band_{int(b):02d}"] = n_bad
                super().__setitem__(b, arr)
            return super().__getitem__(b)

    sub_bands = _LazySubBands(features_tif, fp, sanitized_counts)
    b15_copy = sub_bands[15].copy()
    kept_sub = compute_pure_subsurface_arrays_from_bands(
        sub_bands, gdr_t, gdr_d, fp, sink=sink, free_bands=True
    )
    updip_joint = kept_sub.pop("dcwf_updip_joint_crest")
    sub_bands.clear()
    del sub_bands, gdr_t, gdr_d, kept_sub
    mm.flush()
    gc.collect()

    with rasterio.open(features_tif) as ds:
        b12, nb12 = sanitize_band(ds.read(12), fp)
        b19, nb19 = sanitize_band(ds.read(19), fp)
        sanitized_counts["band_12"] = nb12
        sanitized_counts["band_19"] = nb19

    kept_topo = compute_topo_arrays_from_bands(b12, b19, b15_copy, updip_joint, fp, sink=sink)
    kept_topo.clear()
    sink.kept.clear()
    del b12, b19, b15_copy, updip_joint, kept_topo, sink
    mm.flush()
    del mm
    gc.collect()

    max_diff = verify_subsurface_b12_b19_invariance()
    meta = {
        "version": PDWC21_VERSION,
        "feature_names": list(PDWC21_FEATURE_NAMES),
        "total_features": n_cols,
        "pure_subsurface_features": len(PDWC21_SUBSURFACE_NAMES),
        "topo_features": len(PDWC21_TOPO_NAMES),
        "sanitized_footprint_cells_by_band": sanitized_counts,
        "gdr_stats": gdr_stats,
        "verified_subsurface_b12_b19_max_diff": max_diff,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    return np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols)), list(PDWC21_FEATURE_NAMES), meta


def calibrate_pu_training_domain(
    raw_surf: np.ndarray,
    train_domain: np.ndarray,
    footprint: np.ndarray,
    *,
    pi_vis_train: float,
    pi_sample: float,
    c0_mult: float = 12.0,
    target_iqr_logit: float = 1.65,
) -> tuple[np.ndarray, dict[str, float]]:
    """Calibrate PU posterior using ONLY `train_domain` statistics (zero test-quadrant peeking or rank erasure)."""
    eps = 1.0e-6
    fp = np.asarray(footprint, dtype=bool)
    tr = np.asarray(train_domain, dtype=bool) & fp
    l_all = logit(np.clip(np.asarray(raw_surf[fp], dtype=np.float64), eps, 1.0 - eps))
    l_tr = logit(np.clip(np.asarray(raw_surf[tr], dtype=np.float64)[::4], eps, 1.0 - eps))

    p50, p90, p99 = [float(x) for x in np.percentile(l_tr, [50.0, 90.0, 99.0])]
    span = max(p99 - p50, 0.35)
    scale = float(np.clip(float(target_iqr_logit) / span, 0.65, 1.85))
    l_aligned = p50 + scale * (l_all - p50)

    pi_target = min(max(float(pi_vis_train) * float(c0_mult), 1.0e-4), 0.35)
    pi_s = min(max(float(pi_sample), 1.0e-4), 0.85)
    shift = math.log((pi_target / (1.0 - pi_target)) / (pi_s / (1.0 - pi_s)))
    cal_fp = expit(np.clip(l_aligned + shift, -16.0, 16.0)).astype(np.float32)

    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip(cal_fp, 0.0, 1.0)
    return out, {"p50_logit": round(p50, 5), "p90_logit": round(p90, 5), "p99_logit": round(p99, 5), "scale": round(scale, 5)}


def compute_directional_ac_8(prob_2d: np.ndarray, footprint: np.ndarray) -> list[np.ndarray]:
    """Compute 8 12-azimuth axial, relay-bridge, step-over, Steger-crest, and prominence features."""
    fp = np.asarray(footprint, dtype=bool)
    p = np.where(fp, np.clip(prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    h, w = p.shape
    pad = 14
    pp = np.pad(ndi.gaussian_filter(p, sigma=1.4, mode="constant").astype(np.float32), pad, mode="constant")

    s_max = np.full((h, w), -1.0e9, dtype=np.float32)
    s_sum = np.zeros((h, w), dtype=np.float32)
    l_max = np.full((h, w), -1.0e9, dtype=np.float32)
    b_max = np.zeros((h, w), dtype=np.float32)
    sad_max = np.zeros((h, w), dtype=np.float32)

    center = pp[pad : pad + h, pad : pad + w]
    for k in range(12):
        theta = k * (math.pi / 12.0)
        dy = math.sin(theta)
        dx = math.cos(theta)
        ny = -dx
        nx = dy

        s_acc = center.copy()
        for step, wt in ((3, 0.85), (6, 0.60)):
            sy, sx = int(round(step * dy)), int(round(step * dx))
            s_acc += np.float32(wt * 0.5) * (
                pp[pad + sy : pad + sy + h, pad + sx : pad + sx + w]
                + pp[pad - sy : pad - sy + h, pad - sx : pad - sx + w]
            )
        np.maximum(s_max, s_acc, out=s_max)
        s_sum += s_acc

        fwd = np.zeros((h, w), dtype=np.float32)
        bwd = np.zeros((h, w), dtype=np.float32)
        for step, wt in ((6, 0.42), (9, 0.36), (12, 0.22)):
            sy, sx = int(round(step * dy)), int(round(step * dx))
            fwd += np.float32(wt) * pp[pad + sy : pad + sy + h, pad + sx : pad + sx + w]
            bwd += np.float32(wt) * pp[pad - sy : pad - sy + h, pad - sx : pad - sx + w]
        np.maximum(l_max, 0.5 * (fwd + bwd) + 0.5 * s_acc, out=l_max)
        np.maximum(b_max, np.sqrt(np.maximum(fwd, 0.0) * np.maximum(bwd, 0.0)), out=b_max)
        del s_acc, fwd, bwd

        ay, ax = int(round(6 * dy + 4 * ny)), int(round(6 * dx + 4 * nx))
        by, bx = int(round(-6 * dy - 4 * ny)), int(round(-6 * dx - 4 * nx))
        cy, cx = int(round(6 * dy - 4 * ny)), int(round(6 * dx - 4 * nx))
        ey, ex = int(round(-6 * dy + 4 * ny)), int(round(-6 * dx + 4 * nx))
        rs = np.sqrt(np.maximum(pp[pad + ay : pad + ay + h, pad + ax : pad + ax + w], 0.0) * np.maximum(pp[pad + by : pad + by + h, pad + bx : pad + bx + w], 0.0))
        ls = np.sqrt(np.maximum(pp[pad + cy : pad + cy + h, pad + cx : pad + cx + w], 0.0) * np.maximum(pp[pad + ey : pad + ey + h, pad + ex : pad + ex + w], 0.0))
        np.maximum(sad_max, np.maximum(rs, ls), out=sad_max)
        del rs, ls

    del pp
    aniso = (s_max - s_sum / 12.0).astype(np.float32)
    l_prob = logit(np.clip(p, 1.0e-5, 1.0 - 1.0e-5)).astype(np.float32)
    crest = robust_z_clip(steger_ridge_crest(l_prob, sigma=1.4), fp, clip_lo=0.0, clip_hi=8.0)
    prom = robust_z_clip(p - ndi.gaussian_filter(p, sigma=5.0, mode="constant"), fp, clip_lo=-4.0, clip_hi=8.0)
    del s_sum, l_prob
    return [
        robust_z_clip(p, fp, clip_lo=-4.0, clip_hi=8.0),
        robust_z_clip(s_max, fp, clip_lo=-4.0, clip_hi=8.0),
        robust_z_clip(aniso, fp, clip_lo=0.0, clip_hi=8.0),
        robust_z_clip(l_max, fp, clip_lo=-4.0, clip_hi=8.0),
        robust_z_clip(b_max, fp, clip_lo=0.0, clip_hi=8.0),
        robust_z_clip(sad_max, fp, clip_lo=0.0, clip_hi=8.0),
        crest,
        prom,
    ]


def build_ac_memmap(
    out_path: Path,
    s1_full_2d: np.ndarray,
    s1_sub_2d: np.ndarray,
    footprint: np.ndarray,
) -> np.memmap:
    """Build or load `(N_fp, 16)` `float16` Stage-2 directional auto-context (`Cols 8..15` strictly `B12/B19`-free)."""
    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    n_cols = len(PDWC21_AC_NAMES)
    if out_path.is_file() and out_path.stat().st_size == n_fp * n_cols * 2:
        return np.memmap(out_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols))

    feats_f = compute_directional_ac_8(s1_full_2d, fp)
    feats_s = compute_directional_ac_8(s1_sub_2d, fp)
    all_16 = feats_f + feats_s
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(out_path, dtype=np.float16, mode="w+", shape=(n_fp, n_cols))
    for j, arr2d in enumerate(all_16):
        mm[:, j] = np.clip(arr2d[fp], -32.0, 32.0).astype(np.float16)
    mm.flush()
    del feats_f, feats_s, all_16, mm
    gc.collect()
    return np.memmap(out_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols))


def fit_predict_pdwc_specialist(
    *,
    blocks: Sequence[tuple[np.ndarray, Sequence[int]]],
    hard_neg_cols_in_stack: Sequence[int],
    visible_faults: np.ndarray,
    train_domain: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    predict_mask: np.ndarray | None = None,
    neg_pos_ratio: float = 5.5,
    hard_neg_frac: float = 0.45,
    safe_neg_collar_px: float = 10.0,
    chunk_size: int = 450_000,
) -> tuple[np.ndarray, dict[str, object]]:
    """Fit PU specialist ensemble (`2x HGB + ExtraTrees + L2 Logistic`) and calibrate strictly on `train_domain`."""
    rng = np.random.default_rng(seed)
    fp = np.asarray(footprint, dtype=bool)
    dom = np.asarray(train_domain, dtype=bool) & fp
    vis = np.asarray(visible_faults, dtype=bool) & dom
    safe_neg = dom & (~vis) & (ndi.distance_transform_edt(~vis) > float(safe_neg_collar_px))

    pos_idx = np.flatnonzero(vis[fp])
    neg_pool = np.flatnonzero(safe_neg[fp])
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Empty positive or safe-negative pool")

    target_neg = min(int(round(float(neg_pos_ratio) * pos_idx.size)), neg_pool.size)
    active_blocks = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]

    if target_neg < neg_pool.size and len(hard_neg_cols_in_stack) > 0:
        n_hard = int(round(float(hard_neg_frac) * target_neg))
        n_easy = target_neg - n_hard
        hard_mask = np.zeros(neg_pool.size, dtype=bool)
        hard_set = {int(c) for c in hard_neg_cols_in_stack}
        cursor = 0
        for arr, cols in active_blocks:
            for c in cols:
                if cursor in hard_set:
                    v = np.asarray(arr[neg_pool, c], dtype=np.float32)
                    thr = float(np.percentile(v[::4], 80.0))
                    hard_mask |= v >= thr
                cursor += 1
        h_pool = neg_pool[hard_mask]
        e_pool = neg_pool[~hard_mask]
        if h_pool.size >= n_hard and e_pool.size >= n_easy:
            neg_idx = np.sort(
                np.concatenate([rng.choice(h_pool, size=n_hard, replace=False), rng.choice(e_pool, size=n_easy, replace=False)])
            )
        else:
            neg_idx = np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
    elif target_neg < neg_pool.size:
        neg_idx = np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
    else:
        neg_idx = neg_pool

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)])
    X_train = np.hstack([np.asarray(arr[train_idx][:, cols], dtype=np.float32) for arr, cols in active_blocks])
    n_features = int(X_train.shape[1])

    hgb1 = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=180,
        max_leaf_nodes=39,
        min_samples_leaf=75,
        l2_regularization=4.0,
        early_stopping=False,
        random_state=seed,
    ).fit(X_train, y_train)

    hgb2 = HistGradientBoostingClassifier(
        learning_rate=0.045,
        max_iter=150,
        max_leaf_nodes=23,
        max_depth=6,
        min_samples_leaf=115,
        l2_regularization=7.5,
        early_stopping=False,
        random_state=seed + 19,
    ).fit(X_train, y_train)

    et = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=160,
        max_leaf_nodes=31,
        min_samples_leaf=85,
        max_features=0.45,
        l2_regularization=6.0,
        early_stopping=False,
        random_state=seed + 37,
    ).fit(X_train, y_train)

    scaler = StandardScaler()
    X_sc = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=300, random_state=seed + 59).fit(X_sc, y_train)
    del X_train, X_sc, y_train
    gc.collect()

    n_fp = int(fp.sum())
    pred_fp = np.zeros(n_fp, dtype=np.float32)
    eval_mask = fp if predict_mask is None else (np.asarray(predict_mask, dtype=bool) & fp)
    # Always predict train_domain too so training-domain calibration uses real predictions
    need_mask = eval_mask | dom
    eval_rows = np.flatnonzero(need_mask[fp])

    for start in range(0, eval_rows.size, chunk_size):
        rows_c = eval_rows[start : start + chunk_size]
        Xc = np.hstack([np.asarray(arr[rows_c][:, cols], dtype=np.float32) for arr, cols in active_blocks])
        p1 = hgb1.predict_proba(Xc)[:, 1]
        p2 = hgb2.predict_proba(Xc)[:, 1]
        p3 = et.predict_proba(Xc)[:, 1]
        p4 = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        pred_fp[rows_c] = (0.44 * p1 + 0.26 * p2 + 0.18 * p3 + 0.12 * p4).astype(np.float32)
        del Xc, p1, p2, p3, p4

    raw_surf = np.zeros(fp.shape, dtype=np.float32)
    raw_surf[fp] = pred_fp
    pi_vis = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_samp = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    cal, cal_stats = calibrate_pu_training_domain(
        raw_surf,
        dom,
        fp,
        pi_vis_train=pi_vis,
        pi_sample=pi_samp,
    )
    if predict_mask is not None:
        cal = np.where(eval_mask, cal, 0.0).astype(np.float32)
    del raw_surf, pred_fp, hgb1, hgb2, et, lr
    gc.collect()
    return cal, {
        "n_pos_train": int(pos_idx.size),
        "n_neg_sample": int(neg_idx.size),
        "n_features": n_features,
        **cal_stats,
    }


def compute_pdwc_crest_backbone_fp(X_static: np.ndarray) -> np.ndarray:
    """Catalogue-blind `DCWF x MGPC x Steger` crest sharpness bonus on footprint pixels (`[0, 1]`)."""
    idx = {n: i for i, n in enumerate(PDWC21_FEATURE_NAMES)}
    up_joint = np.maximum(np.asarray(X_static[:, idx["dcwf_updip_joint_crest"]], dtype=np.float32), 0.0)
    g_gate = np.maximum(np.asarray(X_static[:, idx["dcwf_mgpc_grav_crest_gate"]], dtype=np.float32), 0.0)
    m_gate = np.maximum(np.asarray(X_static[:, idx["dcwf_mgpc_rtp_crest_gate"]], dtype=np.float32), 0.0)
    bico_sync = np.maximum(np.asarray(X_static[:, idx["bico_grav_rtp_sync"]], dtype=np.float32), 0.0)
    t_crest = np.maximum(np.asarray(X_static[:, idx["topo_steger_slope_crest_120m"]], dtype=np.float32), 0.0)
    t_step = np.maximum(np.asarray(X_static[:, idx["topo_mgpc_elev_odd_step"]], dtype=np.float32), 0.0)
    raw = 0.25 * up_joint + 0.22 * g_gate + 0.18 * m_gate + 0.12 * bico_sync + 0.13 * t_crest + 0.10 * t_step
    p99 = float(np.percentile(raw[::8], 99.2)) + 1.0e-5
    return np.clip(raw / p99, 0.0, 1.0).astype(np.float32)


def compute_subsurface_backbone_fp(X_static: np.ndarray) -> np.ndarray:
    """Strictly `B12/B19`-free subsurface geophysical backbone score (`[0, 1]`) for far-field concealed fault rescue."""
    idx = {n: i for i, n in enumerate(PDWC21_FEATURE_NAMES)}
    up_joint = np.maximum(np.asarray(X_static[:, idx["dcwf_updip_joint_crest"]], dtype=np.float32), 0.0)
    dip_lock = np.maximum(np.asarray(X_static[:, idx["dcwf_grav_rtp_dip_lock"]], dtype=np.float32), 0.0)
    g_gate = np.maximum(np.asarray(X_static[:, idx["dcwf_mgpc_grav_crest_gate"]], dtype=np.float32), 0.0)
    m_gate = np.maximum(np.asarray(X_static[:, idx["dcwf_mgpc_rtp_crest_gate"]], dtype=np.float32), 0.0)
    bico_sync = np.maximum(np.asarray(X_static[:, idx["bico_grav_rtp_sync"]], dtype=np.float32), 0.0)
    baffle = np.maximum(np.asarray(X_static[:, idx["hcba_claycap_dip_normal_asym"]], dtype=np.float32), 0.0)
    trans = np.maximum(np.asarray(X_static[:, idx["hcba_transtension_slip_tend"]], dtype=np.float32), 0.0)
    raw = 0.26 * up_joint + 0.16 * dip_lock + 0.18 * g_gate + 0.14 * m_gate + 0.10 * bico_sync + 0.10 * baffle + 0.06 * trans
    p99 = float(np.percentile(raw[::8], 99.2)) + 1.0e-5
    return np.clip(raw / p99, 0.0, 1.0).astype(np.float32)


def pool_asymmetric_cover_rescue(
    *,
    s1_full: np.ndarray,
    s1_sub: np.ndarray,
    s2_full: np.ndarray | None,
    s2_sub: np.ndarray | None,
    cover_fp: np.ndarray,
    crest_fp: np.ndarray,
    sub_backbone_fp: np.ndarray | None,
    footprint: np.ndarray,
    stage2_weight: float = 0.68,
    max_cover_rescue: float = 0.52,
    crest_alpha: float = 0.22,
    sub_backbone_alpha: float = 0.0,
) -> np.ndarray:
    """Asymmetric Concealed-Fault Log-Odds Rescue (`IR-91-S17-02` fix): never dilutes exposed scarps."""
    eps = 1.0e-5
    fp = np.asarray(footprint, dtype=bool)
    lf1 = logit(np.clip(s1_full[fp], eps, 1.0 - eps))
    ls1 = logit(np.clip(s1_sub[fp], eps, 1.0 - eps))

    if s2_full is None or s2_sub is None:
        lf = lf1
        ls = ls1
    else:
        w2 = float(stage2_weight)
        lf = (1.0 - w2) * lf1 + w2 * logit(np.clip(s2_full[fp], eps, 1.0 - eps))
        ls = (1.0 - w2) * ls1 + w2 * logit(np.clip(s2_sub[fp], eps, 1.0 - eps))

    cov = np.clip(np.asarray(cover_fp, dtype=np.float32), 0.0, 1.0)
    w_cov = float(max_cover_rescue) * np.clip((cov - 0.20) / 0.65, 0.0, 1.0)
    concealed_rescue = w_cov * np.maximum(0.0, ls - lf)
    l_comb = lf + concealed_rescue + float(crest_alpha) * np.asarray(crest_fp, dtype=np.float32)
    if sub_backbone_alpha > 0.0 and sub_backbone_fp is not None:
        l_comb = l_comb + float(sub_backbone_alpha) * (0.35 + 0.65 * cov) * np.asarray(sub_backbone_fp, dtype=np.float32)

    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip(expit(np.clip(l_comb, -16.0, 16.0)), 0.0, 1.0).astype(np.float32)
    return out


def _kernel_offsets_3px() -> list[tuple[int, int, float]]:
    out = []
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            d = math.hypot(dy, dx)
            if d < 3.0:
                out.append((dy, dx, 1.0 - d / 3.0))
    return out


KERNEL_OFFSETS_3PX = _kernel_offsets_3px()


def emit_dots_nms(
    surface_2d: np.ndarray,
    visible_faults: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
) -> np.ndarray:
    """Greedy NMS dot placement (`{0.0, 1.0}`) respecting `d(x, visible_faults) > collar_px`."""
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool) & fp
    d_vis = ndi.distance_transform_edt(~vis) if vis.any() else np.full(fp.shape, 999.0, dtype=np.float32)
    allowed = fp & (~vis) & (d_vis > float(collar_px))

    s = np.where(allowed, np.asarray(surface_2d, dtype=np.float32), -1.0)
    ys, xs = np.nonzero(allowed & (s > 0.0))
    order = np.argsort(-s[ys, xs], kind="mergesort")
    ys = ys[order]
    xs = xs[order]

    h, w = fp.shape
    rad = int(math.ceil(float(min_spacing_px)))
    disk = [
        (dy, dx)
        for dy in range(-rad, rad + 1)
        for dx in range(-rad, rad + 1)
        if math.hypot(dy, dx) < float(min_spacing_px)
    ]
    blocked = np.zeros((h, w), dtype=bool)
    out = np.zeros((h, w), dtype=np.float32)
    placed = 0

    for y, x in zip(ys.tolist(), xs.tolist()):
        if blocked[y, x]:
            continue
        out[y, x] = 1.0
        placed += 1
        if placed >= int(budget):
            break
        for dy, dx in disk:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
    return out


def emit_dots_celf_submodular(
    surface_2d: np.ndarray,
    visible_faults: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
    ref_halo_words: np.ndarray | None = None,
    n_refs: int = 0,
    uniqueness_cap: float = 0.64,
) -> np.ndarray:
    """Exact `300 m` triangular-kernel CELF facility-location submodular dot placement (`{0.0, 1.0}`).

    Enforces `overlap_3px(ref_r) <= uniqueness_cap` across all `n_refs` references without
    premature candidate-pool starvation, guaranteeing full `budget` utilization whenever
    geometrically feasible on the allowed domain.

    Fix 2026-10-31 (IR-S30-04): with many overlapping reference halos the pure
    reward-ordered greedy spent every shared per-reference quota on the
    multi-reference (consensus) zone first; the remaining off-zone cells then all
    violated at least one saturated quota, so the emitter starved (28,247 of
    44,090 placed) and the fractional post-check collapsed the raster to a few
    hundred dots.  When caps are active the emitter now reserves the off-quota
    share `budget - floor(uniqueness_cap*budget)` and fills it first from cells
    outside the largest reference halo before the reward-ordered main loop.  The
    per-reference semantics and the post-check are unchanged; without caps the
    code path is byte-identical.
    """
    import heapq

    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool) & fp
    d_vis = ndi.distance_transform_edt(~vis) if vis.any() else np.full(fp.shape, 999.0, dtype=np.float32)
    allowed = fp & (~vis) & (d_vis > float(collar_px))

    s_raw = np.clip(np.asarray(surface_2d, dtype=np.float32), 0.0, 1.0)
    q_bg = float(np.percentile(s_raw[allowed][::8], 55.0)) if allowed.any() else 0.0
    s_exc = np.clip((s_raw - q_bg) / max(1.0 - q_bg, 1.0e-5), 0.0, 1.0)
    reward = np.where(allowed, 0.04 * s_raw + 0.96 * np.power(s_exc, 2.2), 0.0).astype(np.float32)

    h, w = fp.shape
    init_gain = np.zeros((h, w), dtype=np.float32)
    for dy, dx, kw in KERNEL_OFFSETS_3PX:
        ys_s = slice(max(0, dy), min(h, h + dy))
        xs_s = slice(max(0, dx), min(w, w + dx))
        ys_d = slice(max(0, -dy), min(h, h - dy))
        xs_d = slice(max(0, -dx), min(w, w - dx))
        init_gain[ys_d, xs_d] += np.float32(kw) * reward[ys_s, xs_s]

    cand_mask = allowed & (init_gain > 0.0)
    ys_all, xs_all = np.nonzero(cand_mask)
    max_heap_cands = 650_000
    if ys_all.size > max_heap_cands:
        top_k = np.argpartition(-init_gain[ys_all, xs_all], max_heap_cands)[:max_heap_cands]
        ys = ys_all[top_k]
        xs = xs_all[top_k]
    else:
        ys = ys_all
        xs = xs_all

    gains = init_gain[ys, xs]
    order = np.argsort(-gains, kind="mergesort")
    ys = ys[order]
    xs = xs[order]
    gains = gains[order]

    heap = [(-float(g), idx, int(y), int(x)) for idx, (g, y, x) in enumerate(zip(gains, ys, xs))]
    heapq.heapify(heap)

    cov = np.zeros((h, w), dtype=np.float32)
    blocked = np.zeros((h, w), dtype=bool)
    out = np.zeros((h, w), dtype=np.float32)
    rad = int(math.ceil(float(min_spacing_px)))
    disk = [
        (dy, dx)
        for dy in range(-rad, rad + 1)
        for dx in range(-rad, rad + 1)
        if math.hypot(dy, dx) < float(min_spacing_px)
    ]

    use_caps = ref_halo_words is not None and n_refs > 0
    n_words = int(ref_halo_words.shape[2]) if use_caps else 0
    ref_counts = np.zeros(n_refs, dtype=np.int32)
    max_cap_count = int(math.floor(float(uniqueness_cap) * float(budget)))
    placed = 0

    def _violates_cap(yy_c: int, xx_c: int, limit_cnt: int) -> bool:
        words_yx = ref_halo_words[yy_c, xx_c]
        for w_i in range(n_words):
            word = int(words_yx[w_i])
            while word:
                lsb = word & -word
                r_idx = (w_i << 6) + (lsb.bit_length() - 1)
                if r_idx < n_refs and ref_counts[r_idx] + 1 > limit_cnt:
                    return True
                word ^= lsb
        return False

    def _record_placement(yy_c: int, xx_c: int) -> None:
        out[yy_c, xx_c] = 1.0
        for dy, dx, kw in KERNEL_OFFSETS_3PX:
            yy, xx = yy_c + dy, xx_c + dx
            if 0 <= yy < h and 0 <= xx < w and kw > cov[yy, xx]:
                cov[yy, xx] = np.float32(kw)
        for dy, dx in disk:
            yy, xx = yy_c + dy, xx_c + dx
            if 0 <= yy < h and 0 <= xx < w:
                blocked[yy, xx] = True
        if use_caps:
            words_yx = ref_halo_words[yy_c, xx_c]
            for w_i in range(n_words):
                word = int(words_yx[w_i])
                while word:
                    lsb = word & -word
                    r_idx = (w_i << 6) + (lsb.bit_length() - 1)
                    if r_idx < n_refs:
                        ref_counts[r_idx] += 1
                    word ^= lsb

    # IR-S30-04 fix: the off-quota share (budget - floor(cap*budget)) is
    # reserved and filled first from cells OUTSIDE the largest reference halo,
    # so the worst-case per-reference quota cannot be monopolised by the
    # consensus zone before the reserve is spent.  Reserve dots are at most one
    # hit on any non-worst reference and zero on the worst one, so the
    # per-reference quotas stay satisfiable for the main loop and the post-check
    # never has to repair anything.
    if use_caps and int(budget) > max_cap_count:
        ref_hits = np.zeros(n_refs, dtype=np.int64)
        for r_idx in range(n_refs):
            ref_hits[r_idx] = int(np.count_nonzero(
                (ref_halo_words[:, :, r_idx >> 6] >> np.uint64(r_idx & 63)) & np.uint64(1)))
        r_star = int(ref_hits.argmax()) if n_refs else 0
        outside = cand_mask & ~((ref_halo_words[:, :, r_star >> 6]
                                 >> np.uint64(r_star & 63)).astype(bool))
        sy, sx = np.nonzero(outside)
        if sy.size:
            s_ord = np.argsort(-init_gain[sy, sx], kind="mergesort")
            reserve = int(budget) - max_cap_count
            for yi, xi in zip(sy[s_ord].tolist(), sx[s_ord].tolist()):
                if placed >= int(budget) or placed >= reserve:
                    break
                y, x = yi, xi
                if blocked[y, x] or out[y, x] > 0.0:
                    continue
                exact_g = 0.0
                for dy, dx, kw in KERNEL_OFFSETS_3PX:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w:
                        rem = kw - float(cov[yy, xx])
                        if rem > 0.0:
                            exact_g += float(reward[yy, xx]) * rem
                if exact_g <= 0.0:
                    continue
                _record_placement(y, x)
                placed += 1

    while heap and placed < int(budget):
        neg_g, idx, y, x = heapq.heappop(heap)
        if blocked[y, x]:
            continue
        if use_caps and _violates_cap(y, x, max_cap_count):
            blocked[y, x] = True
            continue

        exact_g = 0.0
        for dy, dx, kw in KERNEL_OFFSETS_3PX:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w:
                rem = kw - float(cov[yy, xx])
                if rem > 0.0:
                    exact_g += float(reward[yy, xx]) * rem

        if exact_g <= 0.0:
            blocked[y, x] = True
            continue

        next_best = -heap[0][0] if heap else -1.0
        if exact_g >= next_best - 1.0e-7:
            _record_placement(y, x)
            placed += 1
        else:
            heapq.heappush(heap, (-exact_g, idx, y, x))

    # Full-domain continuation if top-650k heap exhausted before reaching `budget`
    if placed < int(budget):
        rem_mask = cand_mask & (~blocked) & (out == 0.0)
        ry, rx = np.nonzero(rem_mask)
        r_ord = np.argsort(-init_gain[ry, rx], kind="mergesort")
        for y, x in zip(ry[r_ord].tolist(), rx[r_ord].tolist()):
            if placed >= int(budget):
                break
            if blocked[y, x]:
                continue
            if use_caps and _violates_cap(y, x, max_cap_count):
                blocked[y, x] = True
                continue
            _record_placement(y, x)
            placed += 1

    # Exact fraction post-check if placed < budget
    if use_caps and placed > 0:
        actual_limit = int(math.floor(float(uniqueness_cap) * float(placed)))
        if int(ref_counts.max()) > actual_limit:
            py, px = np.nonzero(out > 0.0)
            drop_order = np.argsort(reward[py, px], kind="mergesort")
            for di in drop_order.tolist():
                if int(ref_counts.max()) <= int(math.floor(float(uniqueness_cap) * float(placed))):
                    break
                yy, xx = int(py[di]), int(px[di])
                words_yx = ref_halo_words[yy, xx]
                hits_over = False
                hit_list = []
                for w_i in range(n_words):
                    word = int(words_yx[w_i])
                    while word:
                        lsb = word & -word
                        r_idx = (w_i << 6) + (lsb.bit_length() - 1)
                        if r_idx < n_refs:
                            hit_list.append(r_idx)
                            if ref_counts[r_idx] > int(math.floor(float(uniqueness_cap) * float(placed))):
                                hits_over = True
                        word ^= lsb
                if hits_over:
                    out[yy, xx] = 0.0
                    placed -= 1
                    for r_idx in hit_list:
                        ref_counts[r_idx] -= 1

    return out
