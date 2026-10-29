"""Session 27 (`S27-CVDC`): Rule-of-V Contour-Potential Discordance, Hydrothermal
Magnetite-Destruction Baffle, Multi-Valley Knickzone Alignment & Stitched-OOF
Submodular Uniqueness-Capped Emission.

Preregistered in docs/s27/preregistration.md before code execution:
  1. Zero fault coordinates enter any static or Stage-2 feature.
  2. Declared-NoData sentinels (|value| >= 1e30 or non-finite) are excluded via
     normalized masked convolution (shared with gems91.cckm24); retained feature
     supports are eroded beyond operator footprints so no sentinel bleeds into
     any finite feature cell.
  3. B06 ('tc') is excluded from magnetic tilt calculations (verified r=0.99699
     with radiometric Total Count, IR-8E8-09); (B18, B11) are treated strictly
     as signed horizontal derivatives (dx B13, dy B13) per label-blind audit.
  4. Pure-Subsurface specialist features (17 static + 6 Stage-2 = 23 features)
     have bitwise 0.0 dependence on B12 (det_elev) and B19 (det_elev_slope).
  5. Exact 300 m triangular-kernel CELF submodular emitter supports soft
     near-catalogue halo relief and hard per-reference <= 64% 3-px uniqueness
     caps across all competitive non-blanket reference rasters.

Named non-fault mimics: discordant igneous dikes/pluton margins, remanently
magnetized volcanic flow margins, Lake Lahontan pluvial shoreline terraces,
resistant dipping tuff beds, clay-filled paleochannels, and GeoDAWN 90-deg E-W
flight-line drape clearance variations. Fault predictions are structural only,
not direct proof of geothermal heat, permeability, or active venting.
"""
from __future__ import annotations

import gc
import heapq
import math
from typing import Callable

import numpy as np
from scipy import ndimage as ndi

from gems91 import cckm24

GRAD_SIGMA = 2.0
GRAD_ERODE_PX = 3
CVDC_ERODE_PX = 16
VCTK_ERODE_PX = 16
EPS = 1.0e-6

BASE_FEATURES: tuple[str, ...] = (
    "base_grad_b02",
    "base_grad_b12",
    "base_grad_b13",
    "base_grad_b14",
    "base_slope_b05",
    "base_slope_b19",
)

CVDC_FEATURES: tuple[str, ...] = (
    "cvdc_sin2_grav_elev_s2",
    "cvdc_sin2_grav_elev_s5",
    "cvdc_sin2_rtp_elev_s2",
    "cvdc_sin2_rtp_elev_s5",
    "cvdc_pot_align_discord",
    "cvdc_grav_lap_abs_s2",
    "cvdc_grav_lap_abs_s5",
    "cvdc_grav_crest_s2",
    "cvdc_grav_crest_s4",
    "cvdc_mag_tilt_abs",
    "cvdc_mag_tilt_grad",
    "cvdc_mag_crest_s2",
    "pmdb_mag_trough_15px",
    "pmdb_baffle_grav_trough",
    "pmdb_cond_b15_resid",
    "pmdb_claycap_step_gate",
    "pmdb_transtension_index",
    "pmdb_ns_ew_seam_guard",
)

VCTK_FEATURES: tuple[str, ...] = (
    "vctk_valley_concav_s2",
    "vctk_valley_concav_s4",
    "vctk_trans_slope_jump",
    "vctk_thalweg_knick",
    "vctk_bilat_align_700m",
    "vctk_bilat_align_1300m",
    "vctk_slope_crest_s15",
    "vctk_slope_crest_s35",
    "vctk_scarp_prominence",
    "vctk_cover_regime_b15",
)

ALL_STATIC_FEATURES: tuple[str, ...] = BASE_FEATURES + CVDC_FEATURES + VCTK_FEATURES

PURE_SUBSURFACE_STATIC_FEATURES: tuple[str, ...] = (
    "base_grad_b02",
    "base_grad_b13",
    "base_grad_b14",
    "base_slope_b05",
    "cvdc_grav_lap_abs_s2",
    "cvdc_grav_lap_abs_s5",
    "cvdc_grav_crest_s2",
    "cvdc_grav_crest_s4",
    "cvdc_mag_tilt_abs",
    "cvdc_mag_tilt_grad",
    "cvdc_mag_crest_s2",
    "pmdb_mag_trough_15px",
    "pmdb_baffle_grav_trough",
    "pmdb_cond_b15_resid",
    "pmdb_claycap_step_gate",
    "pmdb_transtension_index",
    "pmdb_ns_ew_seam_guard",
)

STAGE2_FULL_FEATURES: tuple[str, ...] = (
    "s2_full_prob",
    "s2_full_axial_600m",
    "s2_full_aniso_600m",
    "s2_full_relay_900m",
    "s2_full_crest",
    "s2_full_prom",
)

STAGE2_SUB_FEATURES: tuple[str, ...] = (
    "s2_sub_prob",
    "s2_sub_axial_600m",
    "s2_sub_aniso_600m",
    "s2_sub_relay_900m",
    "s2_sub_crest",
    "s2_sub_prom",
)

STAGE2_ALL_FEATURES: tuple[str, ...] = STAGE2_FULL_FEATURES + STAGE2_SUB_FEATURES

assert len(BASE_FEATURES) == 6
assert len(CVDC_FEATURES) == 18
assert len(VCTK_FEATURES) == 10
assert len(ALL_STATIC_FEATURES) == 34
assert len(PURE_SUBSURFACE_STATIC_FEATURES) == 17
assert len(STAGE2_ALL_FEATURES) == 12


def _eroded(valid: np.ndarray, px: float) -> np.ndarray:
    """Cells whose Euclidean distance to any invalid cell exceeds ``px``."""
    v = np.asarray(valid, dtype=bool)
    if not v.any():
        return np.zeros_like(v, dtype=bool)
    if v.all():
        return np.ones_like(v, dtype=bool)
    return ndi.distance_transform_edt(v) > float(px)


def _as_feature(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    out = np.full(support.shape, np.nan, dtype=np.float32)
    out[support] = np.asarray(values, dtype=np.float32)[support]
    return out


def _masked_blur32(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Normalized Gaussian convolution over valid cells in float32 (zero sentinel bleed)."""
    v = np.asarray(valid, dtype=bool)
    if not v.any():
        return np.zeros(v.shape, dtype=np.float32)
    raw_v = np.asarray(field, dtype=np.float32)
    med = np.float32(np.median(raw_v[v][::16]))
    x = np.where(v, raw_v - med, np.float32(0.0))
    w = v.astype(np.float32)
    # Truncate at 3.0*sigma so maximum influence radius is strictly <= ceil(3*sigma) px!
    num = ndi.gaussian_filter(x, float(sigma), truncate=3.0, mode="constant", cval=0.0)
    den = ndi.gaussian_filter(w, float(sigma), truncate=3.0, mode="constant", cval=0.0)
    out = np.full_like(num, med, dtype=np.float32)
    good = den > np.float32(1.0e-5)
    out[good] = med + (num[good] / den[good])
    return out


def _grad_mag_and_double_angle(
    field: np.ndarray, valid: np.ndarray, sigma: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (|grad|, cos(2*theta), sin(2*theta)) with compact support <= 3*sigma + 2."""
    smooth = _masked_blur32(field, valid, sigma)
    gy, gx = np.gradient(smooth)
    del smooth
    v_g = _eroded(valid, 2.0)
    gx = np.where(v_g, gx, np.float32(0.0)).astype(np.float32)
    gy = np.where(v_g, gy, np.float32(0.0)).astype(np.float32)
    gmag = np.hypot(gy, gx).astype(np.float32)
    tau = min(float(sigma) * 1.25, 3.5)
    jxx = _masked_blur32(gx * gx, v_g, tau)
    jyy = _masked_blur32(gy * gy, v_g, tau)
    jxy = _masked_blur32(gx * gy, v_g, tau)
    del gx, gy, v_g
    u = jxx - jyy
    v = np.float32(2.0) * jxy
    del jxx, jyy, jxy
    norm = np.hypot(u, v) + np.float32(EPS)
    c2 = (u / norm).astype(np.float32)
    s2 = (v / norm).astype(np.float32)
    del u, v, norm
    return gmag, c2, s2


def _sin2_cos2_diff(
    c2_a: np.ndarray, s2_a: np.ndarray, c2_b: np.ndarray, s2_b: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """180-deg-periodic sin^2(theta_a - theta_b) and cos^2(theta_a - theta_b)."""
    cos2d = np.clip(c2_a * c2_b + s2_a * s2_b, -1.0, 1.0)
    sin2 = np.float32(0.5) * (np.float32(1.0) - cos2d)
    cos2 = np.float32(0.5) * (np.float32(1.0) + cos2d)
    return sin2.astype(np.float32), cos2.astype(np.float32)


def _ridge_crest(field: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Scale-normalized positive negative-Hessian ridge eigenvalue max(0, -sigma^2 * lambda_min)."""
    smooth = _masked_blur32(field, valid, sigma)
    gy, gx = np.gradient(smooth)
    del smooth
    hyy, hyx = np.gradient(gy)
    hxy, hxx = np.gradient(gx)
    del gx, gy
    hxy = np.float32(0.5) * (hyx + hxy)
    del hyx
    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, np.float32(2.0) * hxy)
    del hxx, hyy, hxy
    lam_min = np.float32(0.5) * (tr - disc)
    del tr, disc
    scale = np.float32(float(sigma) * float(sigma))
    return np.maximum(np.float32(0.0), -scale * lam_min).astype(np.float32)


def _sample_offset32(
    field: np.ndarray, uy: np.ndarray, ux: np.ndarray, offset: float
) -> np.ndarray:
    h, w = field.shape
    yy = np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w))
    xx = np.broadcast_to(np.arange(w, dtype=np.float32)[None, :], (h, w))
    coords = np.empty((2, h, w), dtype=np.float32)
    coords[0] = yy + np.float32(offset) * uy
    coords[1] = xx + np.float32(offset) * ux
    return ndi.map_coordinates(
        np.asarray(field, dtype=np.float32), coords, order=1, mode="nearest"
    ).astype(np.float32)


def build_all_static_features(
    read_band: Callable[[int], np.ndarray],
    footprint: np.ndarray,
    save_fn: Callable[[str, np.ndarray], None],
) -> tuple[dict[str, list[str]], dict]:
    """Stream all 34 static features + standalone control surface to disk (< 1 GiB RSS)."""
    fp = np.asarray(footprint, dtype=bool)
    meta_counts: dict[str, dict] = {}

    def emit(name: str, values: np.ndarray, support: np.ndarray) -> None:
        arr = _as_feature(values, support)
        fin = np.isfinite(arr)
        meta_counts[name] = {
            "finite_in_footprint": int((fin & fp).sum()),
            "nan_in_footprint": int((~fin & fp).sum()),
        }
        save_fn(name, arr)

    # ---- Load core bands for Base + CVDC ----
    b02 = read_band(2)
    b12 = read_band(12)
    b13 = read_band(13)
    b14 = read_band(14)
    b05 = read_band(5)
    b19 = read_band(19)

    v02 = cckm24.valid_mask(b02, fp)
    v12 = cckm24.valid_mask(b12, fp)
    v13 = cckm24.valid_mask(b13, fp)
    v14 = cckm24.valid_mask(b14, fp)
    v05 = cckm24.valid_mask(b05, fp)
    v19 = cckm24.valid_mask(b19, fp)

    # 1. Base group (6 features; each uses ONLY its own band's valid mask!)
    for b_name, raw, vm in (
        ("base_grad_b02", b02, v02),
        ("base_grad_b12", b12, v12),
        ("base_grad_b13", b13, v13),
        ("base_grad_b14", b14, v14),
    ):
        sup = _eroded(vm, GRAD_ERODE_PX)
        sm = _masked_blur32(raw, vm, GRAD_SIGMA)
        gy, gx = np.gradient(sm)
        gmag = np.hypot(gy, gx).astype(np.float32)
        del sm, gy, gx
        emit(b_name, np.log1p(np.maximum(gmag, 0.0)), sup)
        if b_name == "base_grad_b13":
            # Standalone gravity-gradient control surface in [0, 1]
            s_grav = cckm24._rank01(gmag, sup)
            save_fn("surface_gravgrad", np.where(fp, s_grav, 0.0).astype(np.float32))
            del s_grav
        del gmag

    emit("base_slope_b05", np.log1p(np.maximum(np.where(v05, b05, 0.0), 0.0)), _eroded(v05, GRAD_ERODE_PX))
    emit("base_slope_b19", np.log1p(np.maximum(np.where(v19, b19, 0.0), 0.0)), _eroded(v19, GRAD_ERODE_PX))
    del b14, v14
    gc.collect()

    # 2. CVDC Rule-of-V contour-vs-potential strike discordance (5 features)
    sup_ge = _eroded(v13 & v12, CVDC_ERODE_PX)
    sup_me = _eroded(v02 & v12, CVDC_ERODE_PX)
    sup_gme = _eroded(v13 & v02 & v12, CVDC_ERODE_PX)

    for tag, sig in (("s2", 2.0), ("s5", 5.0)):
        gg, c2g, s2g = _grad_mag_and_double_angle(b13, v13, sig)
        ge, c2e, s2e = _grad_mag_and_double_angle(b12, v12, sig)
        gm, c2m, s2m = _grad_mag_and_double_angle(b02, v02, sig)
        sin2_ge, _ = _sin2_cos2_diff(c2g, s2g, c2e, s2e)
        sin2_me, _ = _sin2_cos2_diff(c2m, s2m, c2e, s2e)
        emit(f"cvdc_sin2_grav_elev_{tag}", sin2_ge * np.log1p(gg * ge), sup_ge)
        emit(f"cvdc_sin2_rtp_elev_{tag}", sin2_me * np.log1p(gm * ge), sup_me)
        if tag == "s2":
            # Also compute 3-px joint potential-strike lock x contour discordance
            gg3, c2g3, s2g3 = _grad_mag_and_double_angle(b13, v13, 3.0)
            gm3, c2m3, s2m3 = _grad_mag_and_double_angle(b02, v02, 3.0)
            _, c2e3, s2e3 = _grad_mag_and_double_angle(b12, v12, 3.0)
            _, cos2_gm = _sin2_cos2_diff(c2g3, s2g3, c2m3, s2m3)
            sin2_ge3, _ = _sin2_cos2_diff(c2g3, s2g3, c2e3, s2e3)
            emit("cvdc_pot_align_discord", cos2_gm * sin2_ge3 * np.log1p(gg3 * gm3), sup_gme)
            del gg3, c2g3, s2g3, gm3, c2m3, s2m3, c2e3, s2e3, cos2_gm, sin2_ge3
        del gg, c2g, s2g, ge, c2e, s2e, gm, c2m, s2m, sin2_ge, sin2_me

    # Subsurface pure gravity curvature + crests + N-S/E-W seam guard (strictly B12/B19-free!)
    sup_13 = _eroded(v13, CVDC_ERODE_PX)
    for tag, sig in (("s2", 2.0), ("s5", 5.0)):
        sm13 = _masked_blur32(b13, v13, sig)
        lap13 = np.abs(ndi.laplace(sm13, mode="nearest")) * np.float32(sig * sig)
        del sm13
        emit(f"cvdc_grav_lap_abs_{tag}", np.log1p(np.maximum(lap13, 0.0)), sup_13)
        del lap13
    del b13, v13, sup_13

    sup_05 = _eroded(v05, CVDC_ERODE_PX)
    emit("cvdc_grav_crest_s2", np.log1p(10.0 * _ridge_crest(b05, v05, 2.0)), sup_05)
    emit("cvdc_grav_crest_s4", np.log1p(10.0 * _ridge_crest(b05, v05, 4.0)), sup_05)

    sup_02 = _eroded(v02, CVDC_ERODE_PX)
    sm02 = _masked_blur32(b02, v02, 2.0)
    gy02, gx02 = np.gradient(sm02)
    ax02, ay02 = np.abs(gx02), np.abs(gy02)
    seam = (ax02 - ay02) / (ax02 + ay02 + np.float32(EPS))
    emit("pmdb_ns_ew_seam_guard", seam, sup_02)
    del sm02, gy02, gx02, ax02, ay02, seam, b02, v02, sup_02
    gc.collect()

    # Subsurface magnetic tilt, crest, magnetite-destruction trough, MT residual & strain (B12/B19-free!)
    b03 = read_band(3)
    b09 = read_band(9)
    v03 = cckm24.valid_mask(b03, fp)
    v09 = cckm24.valid_mask(b09, fp)
    sup_03 = _eroded(v03, CVDC_ERODE_PX)
    sup_39 = _eroded(v03 & v09, CVDC_ERODE_PX)

    sm03 = _masked_blur32(b03, v03, 1.5)
    sm09 = _masked_blur32(b09, v09, 1.5)
    # B03 is horizontal gradient over 100 m grid; convert to nT/m (/100) to match B09 vertical gradient scale
    tilt = np.arctan2(sm09, np.maximum(sm03, 0.0) * np.float32(0.01) + np.float32(1.0e-3)).astype(np.float32)
    del sm03, sm09, b09, v09
    emit("cvdc_mag_tilt_abs", np.abs(tilt), sup_39)
    tilt_sm = _masked_blur32(tilt, sup_39, 2.0)
    tgy, tgx = np.gradient(tilt_sm)
    emit("cvdc_mag_tilt_grad", np.hypot(tgy, tgx).astype(np.float32), sup_39)
    del tilt, tilt_sm, tgy, tgx

    log_b03 = np.where(v03, np.log1p(np.maximum(np.where(v03, b03, 0.0), 0.0)), 0.0).astype(np.float32)
    emit("cvdc_mag_crest_s2", _ridge_crest(log_b03, v03, 2.0), sup_03)
    trough = np.maximum(
        np.float32(0.0),
        _masked_blur32(log_b03, v03, 12.0) - _masked_blur32(log_b03, v03, 2.0),
    )
    emit("pmdb_mag_trough_15px", trough, sup_03)
    del log_b03, b03

    sup_35 = _eroded(v03 & v05, CVDC_ERODE_PX)
    b05_pos = np.maximum(np.where(v05, b05, 0.0), 0.0).astype(np.float32)
    emit("pmdb_baffle_grav_trough", np.log1p(np.float32(10.0) * b05_pos) * trough, sup_35)

    b15 = read_band(15)
    b17 = read_band(17)
    v15 = cckm24.valid_mask(b15, fp)
    v17 = cckm24.valid_mask(b17, fp)
    v15_17 = v15 & v17
    sup_15_17 = _eroded(v15_17, CVDC_ERODE_PX)
    log_b15 = np.log1p(np.maximum(np.where(v15, b15, 0.0), 0.0)).astype(np.float32)
    # Unlabeled global OLS deconfounding of B17 on log1p(max(0, B15))
    x_fit = log_b15[v15_17].astype(np.float64)
    y_fit = np.asarray(b17[v15_17], dtype=np.float64)
    xm, ym = float(x_fit.mean()), float(y_fit.mean())
    slope_17 = float(np.dot(x_fit - xm, y_fit - ym) / (np.dot(x_fit - xm, x_fit - xm) + 1.0e-12))
    inter_17 = ym - slope_17 * xm
    del x_fit, y_fit
    cond_resid = (np.where(v15_17, b17, 0.0) - (np.float32(inter_17) + np.float32(slope_17) * log_b15)).astype(np.float32)
    emit("pmdb_cond_b15_resid", cond_resid, sup_15_17)

    sup_clay = _eroded(v15_17 & v05 & v03, CVDC_ERODE_PX)
    emit(
        "pmdb_claycap_step_gate",
        np.maximum(np.float32(0.0), cond_resid)
        * np.log1p(np.float32(10.0) * b05_pos)
        * (np.float32(1.0) + trough),
        sup_clay,
    )
    del b17, v17, v15_17, sup_15_17, sup_clay, cond_resid, trough, b05_pos, b05, v05, v03, sup_03, sup_35, sup_05
    gc.collect()

    b04 = read_band(4)
    b07 = read_band(7)
    b08 = read_band(8)
    v478 = cckm24.valid_mask(b04, fp) & cckm24.valid_mask(b07, fp) & cckm24.valid_mask(b08, fp)
    sup_478 = _eroded(v478, CVDC_ERODE_PX)
    transt = (
        np.log1p(np.maximum(np.where(v478, b07, 0.0), 0.0))
        * np.maximum(np.where(v478, b08, 0.0), 0.0)
        / (np.maximum(np.where(v478, b04, 0.0), 0.0) + np.float32(1.0))
    ).astype(np.float32)
    emit("pmdb_transtension_index", transt, sup_478)
    del b04, b07, b08, v478, sup_478, transt
    gc.collect()

    # 3. VCTK Multi-Valley Concavity-Conditioned Transverse Knickzone Alignment (10 features)
    sup_vctk = _eroded(v12 & v19, VCTK_ERODE_PX)
    sm12_2 = _masked_blur32(b12, v12, 2.0)
    sm12_4 = _masked_blur32(b12, v12, 4.0)
    concav2 = np.log1p(np.maximum(np.float32(0.0), ndi.laplace(sm12_2, mode="nearest") * np.float32(4.0)))
    concav4 = np.log1p(np.maximum(np.float32(0.0), ndi.laplace(sm12_4, mode="nearest") * np.float32(16.0)))
    del sm12_2, sm12_4
    emit("vctk_valley_concav_s2", concav2, sup_vctk)
    emit("vctk_valley_concav_s4", concav4, sup_vctk)

    sm12_10 = _masked_blur32(b12, v12, 10.0)
    gy10, gx10 = np.gradient(sm12_10)
    del sm12_10, b12
    mag10 = np.hypot(gy10, gx10) + np.float32(EPS)
    uy_e = (gy10 / mag10).astype(np.float32)
    ux_e = (gx10 / mag10).astype(np.float32)
    del gy10, gx10, mag10

    b19_clean = _masked_blur32(b19, v19, 1.2)
    s_plus = _sample_offset32(b19_clean, uy_e, ux_e, 4.0)
    s_minus = _sample_offset32(b19_clean, uy_e, ux_e, -4.0)
    slope_jump = np.log1p(np.abs(s_plus - s_minus))
    del s_plus, s_minus
    emit("vctk_trans_slope_jump", slope_jump, sup_vctk)

    knick = (concav2 * np.log1p(np.maximum(b19_clean, 0.0)) * (np.float32(1.0) + slope_jump)).astype(np.float32)
    emit("vctk_thalweg_knick", knick, sup_vctk)
    del concav2, concav4, slope_jump

    # Orthogonal contour tangent (-ux_e, uy_e) across adjacent incised washes
    ty_e, tx_e = -ux_e, uy_e
    del uy_e, ux_e
    knick_blur = _masked_blur32(knick, sup_vctk, 2.0)
    del knick
    for tag, dist_px in (("700m", 7.0), ("1300m", 13.0)):
        k_left = _sample_offset32(knick_blur, ty_e, tx_e, dist_px)
        k_right = _sample_offset32(knick_blur, ty_e, tx_e, -dist_px)
        emit(f"vctk_bilat_align_{tag}", np.minimum(k_left, k_right), sup_vctk)
        del k_left, k_right
    del knick_blur, ty_e, tx_e

    emit("vctk_slope_crest_s15", np.log1p(_ridge_crest(b19, v19, 1.5)), sup_vctk)
    emit("vctk_slope_crest_s35", np.log1p(_ridge_crest(b19, v19, 3.5)), sup_vctk)
    b19_bg = _masked_blur32(b19, v19, 12.0)
    emit("vctk_scarp_prominence", np.maximum(b19_clean, 0.0) / (np.maximum(b19_bg, 0.0) + np.float32(0.25)), sup_vctk)
    del b19, v19, b19_clean, b19_bg, sup_vctk

    sup_15 = _eroded(v15, VCTK_ERODE_PX)
    emit("vctk_cover_regime_b15", _masked_blur32(log_b15, v15, 4.0), sup_15)
    del b15, v15, log_b15, sup_15, v12
    gc.collect()

    groups = {
        "base": list(BASE_FEATURES),
        "cvdc": list(CVDC_FEATURES),
        "vctk": list(VCTK_FEATURES),
        "all_static": list(ALL_STATIC_FEATURES),
        "pure_subsurface_static": list(PURE_SUBSURFACE_STATIC_FEATURES),
        "surfaces": ["surface_gravgrad"],
    }
    meta = {
        "groups": groups,
        "feature_counts": meta_counts,
        "constants": {
            "GRAD_SIGMA": GRAD_SIGMA,
            "GRAD_ERODE_PX": GRAD_ERODE_PX,
            "CVDC_ERODE_PX": CVDC_ERODE_PX,
            "VCTK_ERODE_PX": VCTK_ERODE_PX,
            "b17_on_log1p_b15_ols": {"slope": slope_17, "intercept": inter_17},
        },
        "catalogue_used_in_features": False,
        "b06_used_in_features": False,
        "external_unverified_rasters_used": False,
    }
    return groups, meta


def _shift2d(arr: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Fast zero-padded 2-D integer slice shift without coordinate arrays."""
    h, w = arr.shape
    out = np.zeros_like(arr, dtype=np.float32)
    ys_src = slice(max(0, -dy), min(h, h - dy))
    xs_src = slice(max(0, -dx), min(w, w - dx))
    ys_dst = slice(max(0, dy), min(h, h + dy))
    xs_dst = slice(max(0, dx), min(w, w + dx))
    out[ys_dst, xs_dst] = arr[ys_src, xs_src]
    return out


_AZIMUTHS_RAD = tuple(math.radians(a) for a in (0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5))


def stage2_axial_features(prob_2d: np.ndarray, footprint: np.ndarray, prefix: str) -> dict[str, np.ndarray]:
    """Compute 6 label-blind directional axial-bridge features from a Stage-1 probability map."""
    fp = np.asarray(footprint, dtype=bool)
    p = np.where(fp & np.isfinite(prob_2d), np.clip(prob_2d, 0.0, 1.0), 0.0).astype(np.float32)

    axial_max = np.zeros_like(p)
    axial_min = np.full_like(p, np.float32(1.0e9))
    relay_max = np.zeros_like(p)

    for theta in _AZIMUTHS_RAD:
        uy, ux = math.sin(theta), math.cos(theta)
        # Axial 11-sample line mean (-5..+5 px)
        acc = p.copy()
        for k in range(1, 6):
            dy, dx = int(round(k * uy)), int(round(k * ux))
            acc += _shift2d(p, dy, dx)
            acc += _shift2d(p, -dy, -dx)
        line_mean = acc * np.float32(1.0 / 11.0)
        np.maximum(axial_max, line_mean, out=axial_max)
        np.minimum(axial_min, line_mean, out=axial_min)

        # Relay bridge across 3..9 px forward vs backward arms
        fwd = np.zeros_like(p)
        bwd = np.zeros_like(p)
        for k in range(3, 10):
            dy, dx = int(round(k * uy)), int(round(k * ux))
            fwd += _shift2d(p, dy, dx)
            bwd += _shift2d(p, -dy, -dx)
        fwd *= np.float32(1.0 / 7.0)
        bwd *= np.float32(1.0 / 7.0)
        np.maximum(relay_max, np.minimum(fwd, bwd), out=relay_max)

    crest = _ridge_crest(p, fp, 1.8)
    prom = p - _masked_blur32(p, fp, 10.0)
    sup = fp
    return {
        f"{prefix}_prob": _as_feature(p, sup),
        f"{prefix}_axial_600m": _as_feature(axial_max, sup),
        f"{prefix}_aniso_600m": _as_feature(np.maximum(0.0, axial_max - axial_min), sup),
        f"{prefix}_relay_900m": _as_feature(relay_max, sup),
        f"{prefix}_crest": _as_feature(crest, sup),
        f"{prefix}_prom": _as_feature(prom, sup),
    }


def _kernel_offsets_3px() -> list[tuple[int, int, float]]:
    out = []
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            d = math.hypot(dy, dx)
            if d < 3.0:
                out.append((dy, dx, 1.0 - d / 3.0))
    return out


KERNEL_OFFSETS_3PX = _kernel_offsets_3px()


def build_reference_halo_words(
    ref_masks: list[np.ndarray], footprint: np.ndarray, radius_px: float = 3.0
) -> np.ndarray:
    """Bit-pack <=3.0 px Euclidean halos of ``n_refs`` reference dot masks into uint64 words."""
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape
    n_refs = len(ref_masks)
    n_words = (n_refs + 63) // 64
    words = np.zeros((h, w, n_words), dtype=np.uint64)
    rad = int(math.floor(radius_px))
    yy, xx = np.mgrid[-rad : rad + 1, -rad : rad + 1]
    struct = (yy * yy + xx * xx) <= (float(radius_px) * float(radius_px) + 1.0e-9)
    for r_idx, mask in enumerate(ref_masks):
        pos = np.asarray(mask, dtype=bool) & fp
        if not pos.any():
            continue
        halo = ndi.binary_dilation(pos, structure=struct)
        w_i = r_idx >> 6
        bit = np.uint64(1) << np.uint64(r_idx & 63)
        words[halo, w_i] |= bit
    return words


def emit_dots_celf_submodular(
    surface_2d: np.ndarray,
    visible_faults: np.ndarray,
    eligible_mask: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
    farfield_ramp: bool = False,
    ref_halo_words: np.ndarray | None = None,
    n_refs: int = 0,
    uniqueness_cap: float = 0.64,
) -> np.ndarray:
    """Exact 300 m triangular-kernel CELF submodular dot placement ({0.0, 1.0}).

    Uses ONLY ``visible_faults`` (never withheld truth) for collar & far-field ramp,
    and optionally enforces ``overlap_3px(ref_r) <= uniqueness_cap`` across all
    ``n_refs`` competitive non-blanket reference rasters.
    """
    el = np.asarray(eligible_mask, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool)
    d_vis = (
        ndi.distance_transform_edt(~vis).astype(np.float32)
        if vis.any()
        else np.full(el.shape, np.float32(999.0), dtype=np.float32)
    )
    allowed = el & (~vis) & (d_vis > float(collar_px))
    if not allowed.any() or budget <= 0:
        return np.zeros(el.shape, dtype=np.float32)

    s_raw = np.where(np.isfinite(surface_2d), np.clip(surface_2d, 0.0, 1.0), 0.0).astype(np.float32)
    q_bg = float(np.percentile(s_raw[allowed][::8], 55.0))
    s_exc = np.clip((s_raw - q_bg) / max(1.0 - q_bg, 1.0e-5), 0.0, 1.0)
    reward = np.where(allowed, 0.05 * s_raw + 0.95 * np.power(s_exc, 2.1), 0.0).astype(np.float32)
    if farfield_ramp:
        w_far = np.float32(0.55) + np.float32(0.45) * np.clip(
            (d_vis - np.float32(3.05)) / np.float32(6.95), 0.0, 1.0
        )
        reward = (reward * w_far).astype(np.float32)

    h, w = el.shape
    init_gain = np.zeros((h, w), dtype=np.float32)
    for dy, dx, kw in KERNEL_OFFSETS_3PX:
        ys_s = slice(max(0, dy), min(h, h + dy))
        xs_s = slice(max(0, dx), min(w, w + dx))
        ys_d = slice(max(0, -dy), min(h, h - dy))
        xs_d = slice(max(0, -dx), min(w, w - dx))
        init_gain[ys_d, xs_d] += np.float32(kw) * reward[ys_s, xs_s]

    cand_mask = allowed & (init_gain > 0.0)
    ys_all, xs_all = np.nonzero(cand_mask)
    max_heap_cands = 500_000
    if ys_all.size > max_heap_cands:
        top_k = np.argpartition(-init_gain[ys_all, xs_all], max_heap_cands)[:max_heap_cands]
        ys, xs = ys_all[top_k], xs_all[top_k]
    else:
        ys, xs = ys_all, xs_all

    gains = init_gain[ys, xs]
    order = np.argsort(-gains, kind="mergesort")
    ys, xs, gains = ys[order], xs[order], gains[order]
    heap = [(-float(g_val), idx, int(y), int(x)) for idx, (g_val, y, x) in enumerate(zip(gains, ys, xs))]
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

    while heap and placed < int(budget):
        _neg_g, idx, y, x = heapq.heappop(heap)
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

    # Continuation fallback over remaining allowed positive-score cells if heap capped out
    if placed < int(budget):
        rem_mask = allowed & (~blocked) & (out == 0.0) & (s_raw > 0.0)
        ry, rx = np.nonzero(rem_mask)
        r_ord = np.argsort(-s_raw[ry, rx], kind="mergesort")
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

    # Strict post-check if underfill reduced denominator
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
