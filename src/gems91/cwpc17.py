"""Session 17 (`S17-CWPC`): Multi-Scale Complex Cross-Wavelet Phase-Lag &
Quadrature Coherence, Cover-Conditioned Upward-Continuation Attenuation,
Coulomb Strain-Strike Slip-Tendency, and Prior-Shift-Calibrated Local Auto-Context.

Preregistration: `docs/HYPOTHESES_S17_CWPC.md` (frozen before any S17 holdout run).
All feature constructors in `build_cwpc_physics_features` are 100% label-blind:
neither `existing_faults.tif` nor any prior submission raster enters feature
construction. Designed for strict memory safety (< 450 MB RSS on a 3.8 GiB sandbox).
"""

from __future__ import annotations

import gc
from typing import Any
import numpy as np
from scipy import ndimage as ndi

CWPC_PHYSICS_FEATURE_NAMES: list[str] = [
    # Group A: Multi-Scale Complex Cross-Wavelet Phase-Lag & Quadrature Coherence (H17-1)
    "cwpc_rtp_tc_coh",
    "cwpc_rtp_tc_quad",
    "cwpc_rtp_grav_coh",
    "cwpc_rtp_grav_quad",
    "cwpc_grav_cond_coh",
    "cwpc_grav_cond_quad",
    "cwpc_phase_stability",
    "cwpc_tri_modal_sync",
    # Group B: Cover-Conditioned Upward-Continuation Attenuation & SI Tilt (H17-2)
    "uc_mag_struct_idx",
    "uc_grav_struct_idx",
    "si_verduzco_tilt",
    "si_salem_wavenumber",
    # Group C: Coulomb Strain-Strike Slip-Tendency, Flight-Line Oblique & Within-Unit Edge (H17-3..H17-5)
    "cfs_slip_tendency",
    "cfs_seismic_coupling",
    "flightline_oblique_mag",
    "within_unit_edge_z",
]

AUTOCONTEXT_FEATURE_NAMES: list[str] = [
    "ac_p1_cal",
    "ac_mean_300m",
    "ac_max_300m",
    "ac_mean_600m",
    "ac_dog_300_900m",
    "ac_axial_aniso_500m",
    "ac_cwpc_crest_prod",
]

# Topographic band names that must NEVER enter the Pure-Subsurface specialist (IR-91-S15-05)
TOPO_DEPENDENT_FEATURE_NAMES: frozenset[str] = frozenset({
    "det_elev",
    "det_elev_slope",
    "det_elev_grad",
    "det_elev_slope_grad",
})


def robust_norm(arr: np.ndarray, footprint: np.ndarray, clip_hi: float = 20.0) -> np.ndarray:
    """Footprint-normalized float32 field preserving extreme upper fault-core tails, zero outside footprint."""
    fp = np.asarray(footprint, dtype=bool)
    x = np.asarray(arr, dtype=np.float32)
    valid = fp & np.isfinite(x)
    if not valid.any():
        return np.zeros(fp.shape, dtype=np.float32)
    lo, hi = np.nanpercentile(x[valid], [1.0, 99.0])
    scale = max(float(hi - lo), 1e-6)
    med = float(np.nanmedian(x[valid]))
    filled = np.where(valid, x, med)
    out = np.clip((filled - float(lo)) / scale, -5.0, float(clip_hi)).astype(np.float32)
    out[~fp] = 0.0
    return out


def _riesz_wavelet_components(
    field: np.ndarray, sigma: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute band-pass even response and scale-normalized Riesz gradient components at scale `sigma`."""
    s1 = float(sigma)
    s2 = float(sigma * 2.0)
    g1 = ndi.gaussian_filter(field, sigma=s1, mode="nearest")
    g2 = ndi.gaussian_filter(field, sigma=s2, mode="nearest")
    even = (g1 - g2).astype(np.float32)
    del g1, g2
    gx = (ndi.gaussian_filter(field, sigma=s1, order=(0, 1), mode="nearest") * s1).astype(np.float32)
    gy = (ndi.gaussian_filter(field, sigma=s1, order=(1, 0), mode="nearest") * s1).astype(np.float32)
    odd_mag = np.hypot(gx, gy).astype(np.float32)
    return even, gx, gy, odd_mag


def cross_wavelet_pair_metrics(
    x: np.ndarray,
    y: np.ndarray,
    footprint: np.ndarray,
    scales: tuple[float, ...] = (2.0, 4.0, 8.0),
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute multi-scale cross-wavelet coherence, quadrature (pi/2 dip-offset) energy,
    and cross-scale phase-locking stability between two 2-D geophysical fields `x` and `y`.
    """
    fp = np.asarray(footprint, dtype=bool)
    coh_acc = np.zeros(fp.shape, dtype=np.float32)
    quad_acc = np.zeros(fp.shape, dtype=np.float32)
    unit_re = np.zeros(fp.shape, dtype=np.float32)
    unit_im = np.zeros(fp.shape, dtype=np.float32)

    for sigma in scales:
        ex, gxx, gxy, ox = _riesz_wavelet_components(x, sigma)
        ey, gyx, gyy, oy = _riesz_wavelet_components(y, sigma)

        re_w = ex * ey + np.abs(gxx * gyx + gxy * gyy)
        del gxx, gxy, gyx, gyy
        im_w = ox * ey - ex * oy

        energy_x = ex * ex + ox * ox + 1e-6
        energy_y = ey * ey + oy * oy + 1e-6
        del ex, ox, ey, oy
        denom = np.sqrt(energy_x * energy_y) + 1e-6
        del energy_x, energy_y

        mag_w = np.hypot(re_w, im_w)
        coh_s = ndi.uniform_filter(mag_w, size=5) / (ndi.uniform_filter(denom, size=5) + 1e-6)
        quad_s = np.abs(im_w) / denom
        del denom

        coh_acc += coh_s.astype(np.float32)
        quad_acc += quad_s.astype(np.float32)
        unit_re += (re_w / (mag_w + 1e-6)).astype(np.float32)
        unit_im += (im_w / (mag_w + 1e-6)).astype(np.float32)
        del re_w, im_w, mag_w, coh_s, quad_s

    inv_n = 1.0 / float(len(scales))
    coh_mean = (coh_acc * inv_n).astype(np.float32)
    quad_mean = (quad_acc * inv_n).astype(np.float32)
    phase_stab = (np.hypot(unit_re, unit_im) * inv_n).astype(np.float32)
    del coh_acc, quad_acc, unit_re, unit_im

    coh_mean[~fp] = 0.0
    quad_mean[~fp] = 0.0
    phase_stab[~fp] = 0.0
    return coh_mean, quad_mean, phase_stab


def build_cwpc_physics_features(
    bands_by_name: Any,
    footprint: np.ndarray,
    out_dtype: Any = np.float32,
    out_buffer: np.ndarray | None = None,
) -> tuple[np.ndarray, list[str]]:
    """Construct the 16 label-blind `S17-CWPC` geophysical features `(16, H, W)`.

    Zero topographic bands (`det_elev`, `det_elev_slope`) are read here, making all 16
    `CWPC` features provably invariant to surface DEM perturbations (`IR-91-S15-05`).
    """
    fp = np.asarray(footprint, dtype=bool)
    out = out_buffer if out_buffer is not None else np.zeros((16, fp.shape[0], fp.shape[1]), dtype=out_dtype)

    # Pair 1: RTP x TC
    rtp = robust_norm(bands_by_name["rtp"], fp)
    tc = robust_norm(bands_by_name["tc"], fp)
    c_rt, q_rt, s_rt = cross_wavelet_pair_metrics(rtp, tc, fp, scales=(2.0, 4.0, 8.0))
    out[0] = robust_norm(c_rt, fp).astype(out_dtype)
    out[1] = robust_norm(q_rt, fp).astype(out_dtype)
    stab_acc = s_rt.astype(np.float32)
    del c_rt, q_rt, s_rt, tc
    gc.collect()

    # Pair 2: RTP x IsoGrav
    iso_grav = robust_norm(bands_by_name["iso_grav_anom"], fp)
    c_rg, q_rg, s_rg = cross_wavelet_pair_metrics(rtp, iso_grav, fp, scales=(2.0, 4.0, 8.0))
    out[2] = robust_norm(c_rg, fp).astype(out_dtype)
    out[3] = robust_norm(q_rg, fp).astype(out_dtype)
    stab_acc += s_rg
    del c_rg, q_rg, s_rg
    gc.collect()

    # Pair 3: IsoGrav x CondSurf
    cond = robust_norm(bands_by_name["cond_surf"], fp)
    c_gc, q_gc, s_gc = cross_wavelet_pair_metrics(iso_grav, cond, fp, scales=(2.0, 4.0, 8.0))
    del iso_grav, cond
    out[4] = robust_norm(c_gc, fp).astype(out_dtype)
    out[5] = robust_norm(q_gc, fp).astype(out_dtype)
    stab_acc = (stab_acc + s_gc) / 3.0
    out[6] = robust_norm(stab_acc, fp).astype(out_dtype)
    del c_gc, q_gc, s_gc, stab_acc
    gc.collect()

    # Feature 7: Tri-modal sync
    c1 = np.clip(out[2].astype(np.float32), 0.0, 3.0)
    c2 = np.clip(out[0].astype(np.float32), 0.0, 3.0)
    c3 = np.clip(out[4].astype(np.float32), 0.0, 3.0)
    tri_sync = np.cbrt(c1 * c2 * c3 + 1e-6).astype(np.float32)
    del c1, c2, c3
    out[7] = robust_norm(tri_sync, fp).astype(out_dtype)
    del tri_sync
    gc.collect()

    # Group B: Cover-Conditioned Upward-Continuation Attenuation & SI Tilt (H17-2)
    depth_base = robust_norm(bands_by_name["depth_to_base_surf"], fp)
    rtp_g2 = np.hypot(
        ndi.gaussian_filter(rtp, sigma=2.0, order=(1, 0), mode="nearest"),
        ndi.gaussian_filter(rtp, sigma=2.0, order=(0, 1), mode="nearest"),
    )
    rtp_g6 = np.hypot(
        ndi.gaussian_filter(rtp, sigma=6.0, order=(1, 0), mode="nearest"),
        ndi.gaussian_filter(rtp, sigma=6.0, order=(0, 1), mode="nearest"),
    )
    uc_mag = (np.log((rtp_g6 + 1e-3) / (rtp_g2 + 1e-3)) * (1.0 + 0.35 * np.maximum(depth_base, 0.0))).astype(np.float32)
    del rtp_g2, rtp_g6
    out[8] = robust_norm(uc_mag, fp).astype(out_dtype)
    del uc_mag

    grav_vg = robust_norm(bands_by_name["iso_grav_anom_vg"], fp)
    grav_hg = robust_norm(bands_by_name["iso_grav_anom_hg"], fp)
    grav_vec_mag = np.hypot(grav_vg, grav_hg)
    del grav_vg, grav_hg
    grav_g2 = ndi.gaussian_filter(grav_vec_mag, sigma=2.0, mode="nearest")
    grav_g6 = ndi.gaussian_filter(grav_vec_mag, sigma=6.0, mode="nearest")
    del grav_vec_mag
    uc_grav = (np.log((grav_g6 + 1e-3) / (grav_g2 + 1e-3)) * (1.0 + 0.35 * np.maximum(depth_base, 0.0))).astype(np.float32)
    del grav_g2, grav_g6, depth_base
    out[9] = robust_norm(uc_grav, fp).astype(out_dtype)
    del uc_grav
    gc.collect()

    raw_b03 = np.where(fp & np.isfinite(bands_by_name["tmi_hg"]), np.maximum(bands_by_name["tmi_hg"], 0.0), 0.0)
    raw_b09 = np.where(fp & np.isfinite(bands_by_name["tmi_vg"]), bands_by_name["tmi_vg"], 0.0)
    hg_si = raw_b03 / 200.0 + 1e-5
    del raw_b03
    tilt_rad = np.arctan2(raw_b09, hg_si).astype(np.float32)
    del raw_b09, hg_si
    si_verduzco_tilt = np.exp(-np.abs(tilt_rad) / 0.45).astype(np.float32)
    out[10] = robust_norm(si_verduzco_tilt, fp).astype(out_dtype)
    del si_verduzco_tilt
    ty, tx = np.gradient(tilt_rad)
    del tilt_rad
    si_salem_wavenumber = np.hypot(tx, ty).astype(np.float32)
    del tx, ty
    out[11] = robust_norm(si_salem_wavenumber, fp).astype(out_dtype)
    del si_salem_wavenumber
    gc.collect()

    # Group C: Coulomb Strain-Strike Slip-Tendency, Flight-Line Oblique & Within-Unit Edge (H17-3..H17-5)
    gy_r, gx_r = np.gradient(ndi.gaussian_filter(rtp, sigma=2.0, mode="nearest"))
    del rtp
    jxx = ndi.gaussian_filter(gx_r * gx_r, sigma=4.0, mode="nearest")
    jyy = ndi.gaussian_filter(gy_r * gy_r, sigma=4.0, mode="nearest")
    jxy = ndi.gaussian_filter(gx_r * gy_r, sigma=4.0, mode="nearest")
    coh_tensor = np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy) / (jxx + jyy + 1e-5)
    del jxx, jyy, jxy

    grad_sq = gx_r * gx_r + gy_r * gy_r + 1e-5
    oblique_factor = (2.0 * np.abs(gx_r * gy_r)) / grad_sq
    del gx_r, gy_r
    flightline_oblique_mag = (oblique_factor * np.sqrt(grad_sq)).astype(np.float32)
    del grad_sq, oblique_factor
    out[14] = robust_norm(flightline_oblique_mag, fp).astype(out_dtype)
    del flightline_oblique_mag

    shearrate = robust_norm(bands_by_name["geod_shearrate"], fp)
    dilaterate = robust_norm(bands_by_name["geod_dilaterate"], fp)
    cfs_raw = (np.maximum(shearrate, 0.0) + 0.60 * dilaterate) * (0.5 + coh_tensor)
    del shearrate, dilaterate, coh_tensor
    out[12] = robust_norm(cfs_raw, fp).astype(out_dtype)

    deq = robust_norm(bands_by_name["deq_n100a15"], fp)
    ieq = robust_norm(bands_by_name["ieq_n100a15"], fp)
    seismic_prox = np.maximum(ieq, 0.0) + np.maximum(1.5 - deq, 0.0)
    del deq, ieq
    cfs_seismic_coupling = (cfs_raw * (0.5 + 0.5 * seismic_prox)).astype(np.float32)
    del cfs_raw, seismic_prox
    out[13] = robust_norm(cfs_seismic_coupling, fp).astype(out_dtype)
    del cfs_seismic_coupling
    gc.collect()

    tc = robust_norm(bands_by_name["tc"], fp)
    tc_mean = ndi.uniform_filter(tc, size=9)
    tc_var = np.maximum(ndi.uniform_filter(tc * tc, size=9) - tc_mean * tc_mean, 0.0)
    del tc, tc_mean
    cond = robust_norm(bands_by_name["cond_surf"], fp)
    cond_mean = ndi.uniform_filter(cond, size=9)
    cond_var = np.maximum(ndi.uniform_filter(cond * cond, size=9) - cond_mean * cond_mean, 0.0)
    del cond, cond_mean
    province_heterogeneity = np.sqrt(tc_var + cond_var + 0.05)
    del tc_var, cond_var
    tmi_hg = robust_norm(bands_by_name["tmi_hg"], fp)
    grav_slope = robust_norm(bands_by_name["iso_grav_anom_slope"], fp)
    within_unit_edge_z = ((tmi_hg + grav_slope) / province_heterogeneity).astype(np.float32)
    del tmi_hg, grav_slope, province_heterogeneity
    out[15] = robust_norm(within_unit_edge_z, fp).astype(out_dtype)
    del within_unit_edge_z
    gc.collect()

    for ch in range(16):
        arr_ch = np.nan_to_num(out[ch], nan=0.0, posinf=0.0, neginf=0.0)
        arr_ch[~fp] = 0
        out[ch] = arr_ch
    return out, list(CWPC_PHYSICS_FEATURE_NAMES)


def prior_shift_calibrate_surface(
    prob: np.ndarray,
    footprint: np.ndarray,
    *,
    pi_true: float,
    pi_sample: float,
) -> np.ndarray:
    """Exact Bayes prior-shift calibration mapping subsampled classifier probability
    `p` (trained at prevalence `pi_sample`) to true spatial prevalence `pi_true` (`IR-91-S15-06`).
    """
    fp = np.asarray(footprint, dtype=bool)
    p = np.clip(np.nan_to_num(prob, nan=0.0, posinf=0.0, neginf=0.0), 1e-6, 1.0 - 1e-6).astype(np.float32)
    pi_t = float(np.clip(pi_true, 1e-4, 0.5))
    pi_s = float(np.clip(pi_sample, 1e-4, 0.99))
    w_pos = pi_t / pi_s
    w_neg = (1.0 - pi_t) / (1.0 - pi_s)
    cal = (w_pos * p) / (w_pos * p + w_neg * (1.0 - p) + 1e-12)
    out = np.where(fp, cal, 0.0).astype(np.float32)
    return out


def build_local_autocontext_features(
    calibrated_p1: np.ndarray,
    cwpc_crest: np.ndarray,
    footprint: np.ndarray,
    out_dtype: Any = np.float32,
) -> tuple[np.ndarray, list[str]]:
    """Construct 7 translation-invariant local (`<= 900 m`) structural auto-context
    features from a prior-shift-calibrated Stage-1 surface (`IR-91-S15-06`, `IR-91-S15-07`).

    Strictly excludes `>= 3 km` regional bowls to prevent cross-quadrant overfitting.
    """
    fp = np.asarray(footprint, dtype=bool)
    p = np.where(fp, np.clip(np.nan_to_num(calibrated_p1, nan=0.0), 0.0, 1.0), 0.0).astype(np.float32)
    crest = np.where(fp, np.clip(np.nan_to_num(cwpc_crest, nan=0.0), 0.0, 3.0), 0.0).astype(np.float32)

    mean_300 = ndi.uniform_filter(p, size=3).astype(np.float32)
    max_300 = ndi.maximum_filter(p, size=3).astype(np.float32)
    mean_600 = ndi.uniform_filter(p, size=6).astype(np.float32)
    mean_900 = ndi.uniform_filter(p, size=9).astype(np.float32)
    dog_300_900 = (mean_300 - mean_900).astype(np.float32)
    del mean_900

    gy, gx = np.gradient(mean_300)
    jxx = ndi.uniform_filter(gx * gx, size=5)
    jyy = ndi.uniform_filter(gy * gy, size=5)
    jxy = ndi.uniform_filter(gx * gy, size=5)
    del gx, gy
    axial_aniso = (np.sqrt((jxx - jyy) ** 2 + 4.0 * jxy * jxy) / (jxx + jyy + 1e-6) * mean_300).astype(np.float32)
    del jxx, jyy, jxy

    crest_prod = (p * crest).astype(np.float32)

    feats = [p, mean_300, max_300, mean_600, dog_300_900, axial_aniso, crest_prod]
    stack = np.stack(feats, axis=0).astype(out_dtype)
    stack[:, ~fp] = 0
    return np.nan_to_num(stack, nan=0.0, posinf=0.0, neginf=0.0), list(AUTOCONTEXT_FEATURE_NAMES)
