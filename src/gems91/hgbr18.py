"""Session 18 (`S18-HGBR`): Multi-Scale Anisotropic Hurst-Exponent / Variogram-Slope
Break, Up-Dip Listric Fault-Trace Migration & Asymmetric Cover-Gated Dual-Specialist.

Implements preregistered hypotheses `H18-1`, `H18-2`, and `H18-3` (`docs/HYPOTHESES_S18_HGBR.md`)
while resolving the technical blockers documented in `LIMITATIONS_AND_NEXT_STEPS.md`:
  1. `H18-1` (`S18-HGBR`): 16 strictly local (`<= 1.2 km`), translation-invariant,
     100% label-blind multi-scale variogram / Hurst-exponent scaling break, directional
     Hurst anisotropy (`H_parallel - H_perp`), up-dip listric potential-field trace
     migration, and geothermometer-strain features (`cols 0..13` are 100% `Band 12` /
     `Band 19` free; `cols 14..15` are topographic scarp Hurst features isolated in
     `STRICT_TOPO_FEATURE_NAMES`).
  2. `IR-91-S17-01`: Upper-tail log-odds dispersion alignment (`align_stage1_log_odds_dispersion`)
     plus exact training-domain Bayes reference-odds calibration (`c0 = 12.0`) before
     computing `spac_coda` multi-scale spatial auto-context.
  3. `IR-91-S17-02`: Asymmetric Concealed-Fault Log-Odds Rescue (`pool_asymmetric_cover_specialists`)
     that promotes buried faults detected by the `Band 12 / Band 19`-free Pure-Subsurface
     Specialist under deep alluvial/playa cover without ever diluting or vetoing exposed
     range-front fault scarps detected by the Full Specialist.
  4. `IR-91-S17-LFTG-01`: Out-of-Fold (`OOF`) stitched full-map emission with smooth
     visible-catalogue halo de-crowding (`stitch_oof_full_map_surface`), eliminating
     in-sample `existing_faults.tif` halo memorization and restoring far-field (`> 1 km`)
     off-catalogue fault discovery.
"""

from __future__ import annotations

import gc
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import ndimage as ndi

from . import cpad17 as CPAD
from . import dd_vtc_pu as DD
from . import lftg17 as L17
from . import ptac14 as PTAC

HGBR_CACHE_VERSION = "s18_hgbr_features_v1"

# 16 novel Session 18 multi-scale Hurst / variogram-slope break & listric migration features.
# Cols 0..13 (14 features) are strictly Band-12 (`det_elev`) and Band-19 (`det_elev_slope`) free.
# Cols 14..15 (2 features) measure topographic scarp Hurst scaling and belong to
# STRICT_TOPO_FEATURE_NAMES (excluded from the Pure-Subsurface Specialist).
HGBR_FEATURE_NAMES: list[str] = [
    # Group A (Subsurface Hurst Scaling & Directional Anisotropy, cols 0..4)
    "hgbr18_grav_hurst_deficit",
    "hgbr18_rtp_hurst_deficit",
    "hgbr18_grav_hurst_anisotropy",
    "hgbr18_rtp_hurst_anisotropy",
    "hgbr18_grav_rtp_hurst_sync",
    # Group B (Potential-Field Curvature-Bridge & Subsurface Baffles, cols 5..8)
    "hgbr18_basement_hurst_step",
    "hgbr18_tensor_theta_hurst_crest",
    "hgbr18_cond_hurst_baffle",
    "hgbr18_radiometric_k_th_fault_leak",
    # Group C (Geodetic-Seismic Partitioning, Up-Dip Listric Shift & Geotherm Conduit, cols 9..13)
    "hgbr18_strain_potency_partition",
    "hgbr18_transtensional_coulomb_focus",
    "hgbr18_updip_listric_trace_shift",
    "hgbr18_geotherm_hurst_conduit",
    "hgbr18_tri_modal_concealed_ridge",
    # Topographic Scarp Hurst Scaling (cols 14..15 — Full Specialist ONLY)
    "hgbr18_elev_hurst_break",
    "hgbr18_slope_variogram_step",
]

# Complete local column selections (retaining GDR thermal columns 38..43 in X_static and col 3 in X_hvdc
# that boosted Fold 0/1 in INCUMBENT-PTAC-LB, while excluding >=2.5 km coordinate bowls 34..37).
STATIC_LOCAL_COLS: list[int] = list(range(34)) + list(range(38, 49))  # 45 cols
S11_LOCAL_COLS: list[int] = list(CPAD.S11_LOCAL_COLS)  # 16 cols
S12_LOCAL_COLS: list[int] = list(CPAD.S12_LOCAL_COLS)  # 20 cols
PTHA_LOCAL_COLS: list[int] = list(CPAD.PTHA_LOCAL_COLS)  # 20 cols
HVDC_LOCAL_COLS: list[int] = list(range(18))  # 18 cols
CPAD_LOCAL_COLS: list[int] = list(CPAD.CPAD_LOCAL_COLS)  # 16 cols
HGBR_LOCAL_COLS: list[int] = list(range(len(HGBR_FEATURE_NAMES)))  # 16 cols

STRICT_TOPO_FEATURE_NAMES: frozenset[str] = frozenset(
    set(CPAD.STRICT_TOPO_FEATURE_NAMES)
    | {
        "hgbr18_elev_hurst_break",
        "hgbr18_slope_variogram_step",
    }
)


def _robust_z(arr: np.ndarray, footprint: np.ndarray, clip_lo: float = -6.0, clip_hi: float = 8.0) -> np.ndarray:
    """Footprint-normalized float32 robust z-score with IQR/P90 fallback so sparse positive fields never blow up."""
    fp = np.asarray(footprint, dtype=bool)
    vals = np.asarray(arr[fp][::8], dtype=np.float32)
    if vals.size == 0:
        return np.zeros(fp.shape, dtype=np.float32)
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826
    if mad < 1e-4:
        p10, p90 = [float(x) for x in np.percentile(vals, [10.0, 90.0])]
        mad = max((p90 - p10) * 0.39, float(np.std(vals)), 1e-4)
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip((arr[fp] - med) / mad, clip_lo, clip_hi).astype(np.float32)
    return out


def _robust_pos_z(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    return _robust_z(arr, footprint, clip_lo=0.0, clip_hi=8.0)


def _first_diff_lags(
    field_2d: np.ndarray, d: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute symmetric 1st-order central increments `(F(x+d) - F(x-d))` along X, Y, and 45/135-deg diagonals."""
    f = np.asarray(field_2d, dtype=np.float32)
    h, w = f.shape
    pad = max(int(d), 1)
    fp = np.pad(f, pad, mode="reflect")

    dx1 = (fp[pad : pad + h, pad + d : pad + w + d] - fp[pad : pad + h, pad - d : pad + w - d]).astype(
        np.float32
    )
    dy1 = (fp[pad + d : pad + h + d, pad : pad + w] - fp[pad - d : pad + h - d, pad : pad + w]).astype(
        np.float32
    )
    dd = max(1, int(round(float(d) / math.sqrt(2.0))))
    dd1 = (
        fp[pad + dd : pad + h + dd, pad + dd : pad + w + dd]
        - fp[pad - dd : pad + h - dd, pad - dd : pad + w - dd]
    ).astype(np.float32)
    dd2 = (
        fp[pad + dd : pad + h + dd, pad - dd : pad + w - dd]
        - fp[pad - dd : pad + h - dd, pad + dd : pad + w + dd]
    ).astype(np.float32)
    return dx1, dy1, dd1, dd2


def compute_local_hurst_and_anisotropy(
    field_2d: np.ndarray,
    footprint: np.ndarray,
    strike_psi: np.ndarray | None = None,
    lags: tuple[int, int, int, int] = (1, 2, 4, 8),
) -> dict[str, np.ndarray]:
    """Compute amplitude-gated multi-scale 1st-order variogram Hurst deficit `(1 - H(x)) * amp`,
    directional cross-vs-along-strike variogram anisotropy, and fine-vs-coarse scaling break.

    On a smooth planar ramp `F(x) = a*x`, `|F(x+d) - F(x-d)| = 2*a*d` has Hurst slope `H = 1.0`
    (`deficit = 0`). On a localized fault step or narrow cataclastic damage corridor (`200-400 m`),
    increments jump at `d = 1..2 px` and saturate at `d = 4..8 px`, yielding low local Hurst
    exponent `H < 0.6` and high cross-strike vs along-strike variogram anisotropyRight on the fault trace!
    """
    fp = np.asarray(footprint, dtype=bool)
    f = np.asarray(field_2d, dtype=np.float32)
    shape = f.shape

    if strike_psi is None:
        sm = ndi.gaussian_filter(f, sigma=2.0).astype(np.float32)
        gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
        gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
        psi = np.arctan2(-gx, gy).astype(np.float32)
        del sm, gy, gx
    else:
        psi = np.asarray(strike_psi, dtype=np.float32)

    cos_p = np.cos(psi).astype(np.float32)
    sin_p = np.sin(psi).astype(np.float32)

    # Centered log2(lag) regression weights for lags (1, 2, 4, 8) -> x = (0, 1, 2, 3)
    ols_weights = (-0.30, -0.10, 0.10, 0.30)

    h_iso = np.zeros(shape, dtype=np.float32)
    h_par = np.zeros(shape, dtype=np.float32)
    h_per = np.zeros(shape, dtype=np.float32)
    aniso_contrast = np.zeros(shape, dtype=np.float32)
    log_s_lags: list[np.ndarray] = []
    amp_s2: np.ndarray | None = None

    for idx, d in enumerate(lags):
        dx1, dy1, dd1, dd2 = _first_diff_lags(f, int(d))
        sig_d = max(1.4, min(float(d) * 0.75, 5.5))

        e_iso = ndi.gaussian_filter(
            0.25 * (dx1 * dx1 + dy1 * dy1 + dd1 * dd1 + dd2 * dd2), sigma=sig_d
        ).astype(np.float32)
        del dd1, dd2

        # Along-strike (parallel to fault trace) vs cross-strike (fault-normal step) increments
        d_par = dx1 * cos_p + dy1 * sin_p
        d_per = -dx1 * sin_p + dy1 * cos_p
        del dx1, dy1

        e_par = ndi.gaussian_filter(d_par * d_par, sigma=sig_d).astype(np.float32)
        e_per = ndi.gaussian_filter(d_per * d_per, sigma=sig_d).astype(np.float32)
        del d_par, d_per

        eps_floor = float(np.percentile(e_iso[fp][::16], 25)) * 0.10 + 1e-8
        if idx == 1:
            amp_s2 = np.sqrt(e_iso + eps_floor).astype(np.float32)

        # Normalized cross-strike vs along-strike step energy contrast at scale d
        aniso_contrast += np.float32(0.25) * ((e_per - e_par) / (e_per + e_par + eps_floor)).astype(
            np.float32
        )

        ls_iso = (0.5 * np.log2(e_iso + eps_floor)).astype(np.float32)
        ls_par = (0.5 * np.log2(e_par + eps_floor)).astype(np.float32)
        ls_per = (0.5 * np.log2(e_per + eps_floor)).astype(np.float32)
        del e_iso, e_par, e_per

        w_k = np.float32(ols_weights[idx])
        h_iso += w_k * ls_iso
        h_par += w_k * ls_par
        h_per += w_k * ls_per
        log_s_lags.append(ls_iso)

    assert amp_s2 is not None
    amp_gate = np.log1p(_robust_pos_z(amp_s2, fp)).astype(np.float32)
    del amp_s2

    # Local Hurst deficit (1.05 - H_iso)_+ gated by local step amplitude so flat noise stays at 0
    h_iso_clamped = np.clip(h_iso, 0.05, 1.05).astype(np.float32)
    deficit = ((np.float32(1.08) - h_iso_clamped) * amp_gate).astype(np.float32)

    # Directional Hurst & variogram step anisotropy: smooth along strike (high H_par, low E_par)
    # and step-like across strike (low H_per, high E_per)
    anisotropy = ((np.maximum(aniso_contrast, 0.0) + 0.35 * np.maximum(h_par - h_per, 0.0)) * amp_gate).astype(
        np.float32
    )

    # Fine-vs-coarse variogram step break gated by amplitude
    h_fine = (log_s_lags[1] - log_s_lags[0]).astype(np.float32)
    h_coarse = (0.5 * (log_s_lags[3] - log_s_lags[1])).astype(np.float32)
    scale_break = ((np.float32(1.0) - h_coarse + 0.5 * (h_fine - h_coarse)) * amp_gate).astype(np.float32)
    del log_s_lags, h_iso, h_par, h_per, h_fine, h_coarse, aniso_contrast, amp_gate

    deficit[~fp] = 0.0
    anisotropy[~fp] = 0.0
    scale_break[~fp] = 0.0
    return {
        "deficit": deficit,
        "anisotropy": anisotropy,
        "scale_break": scale_break,
        "strike_psi": psi,
    }


def compute_updip_listric_migration(
    cos_theta_shallow: np.ndarray,
    cos_theta_deep: np.ndarray,
    q2d_purity: np.ndarray,
    b15_depth_m: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Migrate deep (`600 m`) potential-field edge phase up-dip toward the sub-alluvial fault trace (`H18-2`)."""
    fp = np.asarray(footprint, dtype=bool)
    diff = ndi.gaussian_filter(
        (cos_theta_deep - cos_theta_shallow).astype(np.float32), sigma=2.2
    ).astype(np.float32)
    gy = (ndi.sobel(diff, axis=0) / 8.0).astype(np.float32)
    gx = (ndi.sobel(diff, axis=1) / 8.0).astype(np.float32)
    gmag = np.hypot(gy, gx).astype(np.float32) + np.float32(1e-6)
    # Unit vector pointing from shallow crest toward deep hanging-wall crest
    uy = (gy / gmag).astype(np.float32)
    ux = (gx / gmag).astype(np.float32)
    del diff, gy, gx, gmag

    # Up-dip shift distance in 100-m pixels proportional to local basement depth (cot(55 deg) ~ 0.70)
    shift_px = np.clip(np.asarray(b15_depth_m, dtype=np.float32) * np.float32(0.0055), 0.0, 4.5).astype(
        np.float32
    )
    h, w = fp.shape
    yy, xx = np.meshgrid(
        np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij"
    )
    # Sample deep edge phase shifted from the hanging wall back to the footwall sub-crop
    sample_y = np.clip(yy + uy * shift_px, 0.0, float(h - 1))
    sample_x = np.clip(xx + ux * shift_px, 0.0, float(w - 1))
    del yy, xx, uy, ux, shift_px

    migrated = ndi.map_coordinates(
        np.asarray(cos_theta_deep, dtype=np.float32),
        [sample_y, sample_x],
        order=1,
        mode="nearest",
    ).astype(np.float32)
    del sample_y, sample_x

    out = (migrated * np.sqrt(np.clip(cos_theta_shallow, 0.0, 1.0)) * np.clip(q2d_purity, 0.0, 1.0)).astype(
        np.float32
    )
    out[~fp] = 0.0
    return out


def compute_hgbr_features(
    features_tif: Path,
    gdr_csv: Path,
    footprint: np.ndarray,
    workers: int = 2,
) -> np.ndarray:
    """Compute all 16 novel Session 18 (`S18-HGBR`) features on the valid footprint `(N_fp, 16)`.

    Cols `0..13` (14 features) are strictly `Band 12` / `Band 19` free.
    Cols `14..15` (2 features) read `Band 12` / `Band 19` and are isolated in
    `STRICT_TOPO_FEATURE_NAMES`.
    """
    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    X_out = np.empty((n_fp, len(HGBR_FEATURE_NAMES)), dtype=np.float32)

    def _read_clean(src: rasterio.DatasetReader, band_1idx: int) -> np.ndarray:
        raw = src.read(band_1idx).astype(np.float32)
        return DD._clean_band_edt(raw, fp)

    with rasterio.open(features_tif) as src:
        b02 = _read_clean(src, 2)   # rtp
        b04 = np.maximum(_read_clean(src, 4), 0.0).astype(np.float32)   # th
        b05 = np.maximum(_read_clean(src, 5), 0.0).astype(np.float32)   # k
        b07 = _read_clean(src, 7)   # geod_shearrate
        b08 = _read_clean(src, 8)   # geod_dilaterate
        b09 = _read_clean(src, 9)   # gdr_vital_signs
        b10 = np.maximum(_read_clean(src, 10), 0.0).astype(np.float32)  # deq_n100a15 (sign-fixed)
        b13 = _read_clean(src, 13)  # iso_grav_anom
        b15 = np.maximum(_read_clean(src, 15), 0.0).astype(np.float32)  # depth_to_base_surf
        b16 = np.maximum(_read_clean(src, 16), 0.0).astype(np.float32)  # ieq_n100a15
        b17 = np.maximum(_read_clean(src, 17), 0.0).astype(np.float32)  # cond_surf

    # --- 1. 3-D Laplace Gravity Tensor & Gravity Multi-Scale Hurst Scaling (cols 0, 2, 6, 11) ---
    grav_tensor = L17.compute_laplace_full_tensor_gravity(b13, fp, workers=workers)
    psi_g = grav_tensor["strike_psi_g"]
    cos_theta_g200 = grav_tensor["cos_theta_200m"]
    cos_theta_g600 = grav_tensor["cos_theta_600m"]
    q2d_g = grav_tensor["q2d_purity"]
    worm_g = grav_tensor["worm_persist"]
    del grav_tensor

    hurst_g = compute_local_hurst_and_anisotropy(b13, fp, strike_psi=psi_g)
    z_def_g = _robust_pos_z(hurst_g["deficit"], fp)
    z_ani_g = _robust_pos_z(hurst_g["anisotropy"], fp)
    X_out[:, 0] = z_def_g[fp]
    X_out[:, 2] = z_ani_g[fp]
    del hurst_g

    # Inflection worm crest & Laplace cos_theta concordant with Hurst anisotropy (col 6)
    cooper_g = CPAD._inflection_worm_crest(b13, fp, sigma=2.2)
    del b13
    crest_gt = (cooper_g * cos_theta_g200 * np.log1p(z_ani_g)).astype(np.float32)
    X_out[:, 6] = _robust_pos_z(crest_gt, fp)[fp]
    del cooper_g, crest_gt

    # Up-dip listric trace migration (col 11)
    updip = compute_updip_listric_migration(cos_theta_g200, cos_theta_g600, q2d_g, b15, fp)
    X_out[:, 11] = _robust_pos_z(updip, fp)[fp]
    del cos_theta_g600, updip
    gc.collect()

    # --- 2. Destriped RTP Magnetic Multi-Scale Hurst Scaling & Sync (cols 1, 3, 4) ---
    b02_clean, _ = L17.destripe_cardinal_flightlines(b02, workers=workers)
    del b02
    rtp_tilt, rtp_cos_theta, psi_m = L17.compute_laplace_tilt_and_theta(
        b02_clean, fp, z_up_m=150.0, workers=workers
    )
    hurst_m = compute_local_hurst_and_anisotropy(b02_clean, fp, strike_psi=psi_m)
    del b02_clean, rtp_tilt
    z_def_m = _robust_pos_z(hurst_m["deficit"], fp)
    z_ani_m = _robust_pos_z(hurst_m["anisotropy"], fp)
    X_out[:, 1] = z_def_m[fp]
    X_out[:, 3] = z_ani_m[fp]
    del hurst_m

    strike_sync = (np.cos(psi_g - psi_m) ** 2).astype(np.float32)
    hurst_sync = (np.sqrt(np.maximum(z_def_g * z_def_m, 0.0)) * strike_sync).astype(np.float32)
    X_out[:, 4] = _robust_pos_z(hurst_sync, fp)[fp]
    del psi_m, strike_sync
    gc.collect()

    # --- 3. Basement Hurst Step, Conductivity Hurst Baffle & Radiometric K/Th Leak (cols 5, 7, 8) ---
    l15 = np.log1p(b15).astype(np.float32)
    del b15
    hurst_b15 = compute_local_hurst_and_anisotropy(l15, fp, strike_psi=psi_g)
    b15_step = ((hurst_b15["deficit"] + np.maximum(hurst_b15["anisotropy"], 0.0)) * q2d_g).astype(np.float32)
    X_out[:, 5] = _robust_pos_z(b15_step, fp)[fp]
    del hurst_b15, b15_step

    # Band 15-deconfounded conductivity Hurst baffle (100% DEM-free!)
    l17 = np.log1p(b17).astype(np.float32)
    del b17
    x15_v = l15[fp].astype(np.float64)
    y17_v = l17[fp].astype(np.float64)
    xm = float(x15_v.mean())
    ym = float(y17_v.mean())
    slope_17_15 = float(np.dot(x15_v - xm, y17_v - ym) / (np.dot(x15_v - xm, x15_v - xm) + 1e-9))
    cond_res = np.zeros(fp.shape, dtype=np.float32)
    cond_res[fp] = (y17_v - (ym + slope_17_15 * (x15_v - xm))).astype(np.float32)
    del l15, l17, x15_v, y17_v
    hurst_cond = compute_local_hurst_and_anisotropy(cond_res, fp, strike_psi=psi_g)
    cond_baffle = (hurst_cond["deficit"] * (1.0 + hurst_cond["anisotropy"])).astype(np.float32)
    X_out[:, 7] = _robust_pos_z(cond_baffle, fp)[fp]
    del cond_res, hurst_cond, cond_baffle

    # Destriped K/Th radiometric ratio fault leakage (col 8)
    k_th_raw = np.log1p(b05 / (b04 + np.float32(0.25))).astype(np.float32)
    del b04, b05
    k_th_clean, _ = L17.destripe_cardinal_flightlines(k_th_raw, workers=workers)
    del k_th_raw
    hurst_kth = compute_local_hurst_and_anisotropy(k_th_clean, fp, strike_psi=psi_g)
    del k_th_clean
    kth_leak = (hurst_kth["deficit"] * np.sqrt(np.maximum(z_def_m, 0.0))).astype(np.float32)
    X_out[:, 8] = _robust_pos_z(kth_leak, fp)[fp]
    del hurst_kth, kth_leak, z_def_m
    gc.collect()

    # --- 4. Strain-Potency Partition, Coulomb Focus, Geotherm Conduit & Tri-Modal Ridge (cols 9, 10, 12, 13) ---
    seis_act = np.log1p(b10 + np.float32(1.5) * b16).astype(np.float32)
    del b10, b16
    geod_rate = np.hypot(b07, b08).astype(np.float32)
    z_seis = _robust_pos_z(seis_act, fp)
    z_geod = _robust_pos_z(geod_rate, fp)
    del seis_act, geod_rate

    # Kostrov seismic-geodetic strain partition gated by gravity Hurst anisotropy (col 9)
    partition = (np.abs(z_seis - z_geod) + np.sqrt(z_seis * z_geod)) * np.log1p(z_ani_g)
    X_out[:, 9] = _robust_pos_z(partition, fp)[fp]
    del partition, z_seis, z_geod

    # Transtensional Coulomb dilatational shear focus along gravity strike (col 10)
    z_sh = _robust_pos_z(np.abs(b07), fp)
    z_di = _robust_pos_z(np.maximum(b08, 0.0), fp)
    del b07, b08
    coulomb_focus = (np.sqrt(z_sh * (z_di + np.float32(0.2))) * np.log1p(z_def_g)).astype(np.float32)
    X_out[:, 10] = _robust_pos_z(coulomb_focus, fp)[fp]
    del z_sh, z_di, coulomb_focus, psi_g

    # GDR chemical geothermometer disequilibrium conduit coupled with Hurst sync (col 12)
    diseq_imp, enth_imp, _ = CPAD.extract_gdr_disequilibrium_impulses(gdr_csv, fp.shape, fp)
    diseq_2d = _robust_pos_z(
        ndi.gaussian_filter(diseq_imp + 0.5 * enth_imp, sigma=4.5).astype(np.float32), fp
    )
    del diseq_imp, enth_imp
    vital_z = _robust_pos_z(b09, fp)
    del b09
    geotherm_conduit = ((0.60 * diseq_2d + 0.40 * vital_z) * np.log1p(hurst_sync)).astype(np.float32)
    X_out[:, 12] = _robust_pos_z(geotherm_conduit, fp)[fp]
    del diseq_2d, vital_z, geotherm_conduit

    # Pure-subsurface tri-modal concealed ridge (col 13)
    tri_ridge = (
        np.cbrt(
            np.maximum(worm_g, 0.0)
            * np.maximum(rtp_cos_theta, 0.0)
            * np.maximum(hurst_sync + 0.25 * z_ani_g, 0.0)
        )
        * np.clip(q2d_g, 0.1, 1.0)
    ).astype(np.float32)
    X_out[:, 13] = _robust_pos_z(tri_ridge, fp)[fp]
    del worm_g, rtp_cos_theta, hurst_sync, z_ani_g, z_def_g, q2d_g, cos_theta_g200, tri_ridge
    gc.collect()

    # --- 5. Topographic Scarp Hurst Scaling (cols 14..15 — Full Specialist ONLY!) ---
    with rasterio.open(features_tif) as src:
        b12 = _read_clean(src, 12)  # det_elev
        b19 = np.maximum(_read_clean(src, 19), 0.0).astype(np.float32)  # det_elev_slope

    hurst_elev = compute_local_hurst_and_anisotropy(b12, fp)
    del b12
    elev_break = (np.maximum(hurst_elev["scale_break"], 0.0) * (1.0 + hurst_elev["anisotropy"])).astype(
        np.float32
    )
    X_out[:, 14] = _robust_pos_z(elev_break, fp)[fp]

    hurst_slope = compute_local_hurst_and_anisotropy(b19, fp, strike_psi=hurst_elev["strike_psi"])
    del b19, hurst_elev
    slope_step = (hurst_slope["deficit"] * (1.0 + hurst_slope["anisotropy"])).astype(np.float32)
    X_out[:, 15] = _robust_pos_z(slope_step, fp)[fp]
    del hurst_slope, elev_break, slope_step
    gc.collect()

    return np.nan_to_num(X_out, nan=0.0, posinf=8.0, neginf=-6.0).astype(np.float32)


def build_or_load_hgbr_feature_memmap(
    *,
    features_tif: Path,
    gdr_csv: Path,
    footprint: np.ndarray,
    cache_dir: Path,
    workers: int = 2,
) -> tuple[np.memmap, list[str], dict[str, object]]:
    """Build or load the cached `(N_fp, 16)` `float32` `S18-HGBR` feature table on disk."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    n_fp = int(footprint.sum())
    n_cols = len(HGBR_FEATURE_NAMES)
    mmap_path = cache_dir / f"{HGBR_CACHE_VERSION}.f32.mmap"
    meta_path = cache_dir / f"{HGBR_CACHE_VERSION}.meta.json"

    if mmap_path.is_file() and meta_path.is_file() and mmap_path.stat().st_size == n_fp * n_cols * 4:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("feature_names") == HGBR_FEATURE_NAMES and int(meta.get("n_fp", -1)) == n_fp:
            mm = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(HGBR_FEATURE_NAMES), meta

    arr = compute_hgbr_features(features_tif, gdr_csv, footprint, workers=workers)
    mm_w = np.memmap(mmap_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    mm_w[:] = arr[:]
    mm_w.flush()
    del mm_w, arr
    gc.collect()

    meta = {
        "version": HGBR_CACHE_VERSION,
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": list(HGBR_FEATURE_NAMES),
        "subsurface_only_cols": list(range(14)),
        "topo_dependent_cols": [14, 15],
        "banned_gdr_columns_excluded": list(CPAD.BANNED_GDR_COLUMNS),
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    mm_r = np.memmap(mmap_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_r, list(HGBR_FEATURE_NAMES), meta


def align_stage1_log_odds_dispersion(
    surface: np.ndarray,
    region_mask: np.ndarray,
    target_upper_span: float,
    footprint: np.ndarray,
) -> np.ndarray:
    """Align upper-tail log-odds dispersion (`p99 - p50`) of 2-quadrant pairwise Stage-1
    predictions to match 3-quadrant OOF dispersion (`IR-91-S17-01`), without altering
    regional median prevalence.
    """
    mask = np.asarray(region_mask, dtype=bool) & np.asarray(footprint, dtype=bool)
    if not mask.any() or target_upper_span <= 0.0:
        return np.asarray(surface, dtype=np.float32)

    eps = np.float32(1e-5)
    p = np.clip(np.asarray(surface[mask], dtype=np.float32), eps, 1.0 - eps)
    logit = np.log(p / (1.0 - p))
    p50, p99 = [float(x) for x in np.percentile(logit[::8], [50.0, 99.0])]
    cur_span = max(p99 - p50, 1e-4)
    # Bounded dispersion multiplier so regional base rates remain intact
    scale = float(np.clip(float(target_upper_span) / cur_span, 0.94, 1.08))
    logit_adj = np.where(logit > p50, p50 + scale * (logit - p50), logit)
    p_adj = (1.0 / (1.0 + np.exp(-np.clip(logit_adj, -16.0, 16.0)))).astype(np.float32)

    out = np.array(surface, dtype=np.float32, copy=True)
    out[mask] = p_adj
    return out


def compute_hgbr_crest_concordance_fp(
    X_hgbr: np.ndarray,
    X_cpad: np.ndarray,
    X_s11: np.ndarray,
    X_ptha: np.ndarray,
) -> np.ndarray:
    """Bounded `[0, 1]` multi-physics Hurst-Tensor-Phase crest concordance on footprint."""
    n_fp = X_hgbr.shape[0]

    def _pct01(v: np.ndarray) -> np.ndarray:
        lo = float(np.percentile(v[::16], 10))
        hi = float(np.percentile(v[::16], 96))
        return np.clip((v - lo) / (hi - lo + 1e-6), 0.0, 1.0).astype(np.float32)

    h_crest = _pct01(np.asarray(X_hgbr[:, 6], dtype=np.float32))   # tensor_theta_hurst_crest
    h_tri = _pct01(np.asarray(X_hgbr[:, 13], dtype=np.float32))    # tri_modal_concealed_ridge
    h_sync = _pct01(np.asarray(X_hgbr[:, 4], dtype=np.float32))    # grav_rtp_hurst_sync
    c_theta_g = _pct01(np.asarray(X_cpad[:, 0], dtype=np.float32)) # cooper_theta_grav
    c_worm_g = _pct01(np.asarray(X_cpad[:, 4], dtype=np.float32))  # grav_second_deriv_zero_crest
    c_worm_b = _pct01(np.asarray(X_cpad[:, 7], dtype=np.float32))  # basement_inflection_worm
    c_marussi = _pct01(np.asarray(X_s11[:, 2], dtype=np.float32))  # marussi_e1
    c_mag_crest = _pct01(np.asarray(X_ptha[:, 2], dtype=np.float32))

    crest = (
        0.18 * h_crest
        + 0.16 * h_tri
        + 0.12 * h_sync
        + 0.16 * c_theta_g
        + 0.12 * c_worm_g
        + 0.10 * c_worm_b
        + 0.08 * c_marussi
        + 0.08 * c_mag_crest
    ).astype(np.float32)
    assert crest.shape == (n_fp,)
    return np.clip(crest, 0.0, 1.0)


def pool_full_specialist_with_crest(
    s1_full: np.ndarray,
    s2_full: np.ndarray,
    crest_bonus_fp: np.ndarray,
    footprint: np.ndarray,
    *,
    stage2_weight: float = 0.66,
    crest_alpha: float = 0.18,
) -> np.ndarray:
    """Log-opinion pool of Stage-1 + Stage-2 Full Specialist with bounded Hurst-Tensor crest sharpening (`hgbr_e1`)."""
    fp = np.asarray(footprint, dtype=bool)
    pooled = PTAC.log_opinion_pool(s1_full, s2_full, fp, stage2_weight=float(stage2_weight))
    if crest_alpha <= 0.0:
        return pooled
    eps = np.float32(1e-5)
    p = np.clip(pooled[fp], eps, 1.0 - eps)
    logit = np.log(p / (1.0 - p))
    crest = np.clip(np.asarray(crest_bonus_fp, dtype=np.float32), 0.0, 1.0)
    p_adj = (1.0 / (1.0 + np.exp(-np.clip(logit + np.float32(crest_alpha) * (crest - 0.35), -18.0, 18.0)))).astype(
        np.float32
    )
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip(p_adj, 0.0, 1.0)
    return out


def pool_asymmetric_cover_specialists(
    *,
    s1_full: np.ndarray,
    s1_sub: np.ndarray,
    s2_full: np.ndarray,
    s2_sub: np.ndarray,
    cover_prior_fp: np.ndarray,
    crest_bonus_fp: np.ndarray,
    footprint: np.ndarray,
    stage2_weight: float = 0.66,
    max_cover_rescue_weight: float = 0.42,
    cover_threshold: float = 0.38,
    crest_alpha: float = 0.22,
) -> np.ndarray:
    """Asymmetric Concealed-Fault Log-Odds Rescue (`IR-91-S17-02` fix, `hgbr_e2` / `hgbr_e3`).

    Unlike symmetric linear blending `(1 - w)*l_full + w*l_sub` (which penalized exposed
    scarps when `l_sub < l_full`), this operator uses `max(0, l_sub - l_full)` gated by
    `cover_concealment_prior`:
      - On exposed range-front scarps (`l_full >= l_sub` or `cover <= cover_threshold`),
        `100%` of the Full Specialist's sharpness is preserved (`0` veto!).
      - Inside concealed alluvial basins and playas (`cover > cover_threshold` and
        `l_sub > l_full`), the strictly `Band 12 / Band 19`-free Pure-Subsurface
        Specialist rescues buried geothermal faults into the active dot budget.
    """
    fp = np.asarray(footprint, dtype=bool)
    eps = np.float32(1e-5)
    w2 = np.float32(stage2_weight)
    w1 = np.float32(1.0 - stage2_weight)

    lf1 = np.log(np.clip(s1_full[fp], eps, 1.0 - eps) / (1.0 - np.clip(s1_full[fp], eps, 1.0 - eps)))
    lf2 = np.log(np.clip(s2_full[fp], eps, 1.0 - eps) / (1.0 - np.clip(s2_full[fp], eps, 1.0 - eps)))
    l_full = (w1 * lf1 + w2 * lf2).astype(np.float32)

    ls1 = np.log(np.clip(s1_sub[fp], eps, 1.0 - eps) / (1.0 - np.clip(s1_sub[fp], eps, 1.0 - eps)))
    ls2 = np.log(np.clip(s2_sub[fp], eps, 1.0 - eps) / (1.0 - np.clip(s2_sub[fp], eps, 1.0 - eps)))
    l_sub = (w1 * ls1 + w2 * ls2).astype(np.float32)

    cov = np.clip(np.asarray(cover_prior_fp, dtype=np.float32), 0.0, 1.0)
    span = max(1.0 - float(cover_threshold), 1e-4)
    w_rescue = (
        float(max_cover_rescue_weight)
        * np.power(np.clip((cov - float(cover_threshold)) / span, 0.0, 1.0), 1.35)
    ).astype(np.float32)

    # One-sided concealed-fault rescue: never suppresses exposed scarps where l_full >= l_sub!
    sub_excess = np.maximum(l_sub - l_full, 0.0)
    crest = np.clip(np.asarray(crest_bonus_fp, dtype=np.float32), 0.0, 1.0)
    l_dual = l_full + w_rescue * sub_excess + np.float32(crest_alpha) * (crest - 0.35)

    p_final_fp = (1.0 / (1.0 + np.exp(-np.clip(l_dual, -18.0, 18.0)))).astype(np.float32)
    out = np.zeros(fp.shape, dtype=np.float32)
    out[fp] = np.clip(p_final_fp, 0.0, 1.0)
    return out


def stitch_oof_full_map_surface(
    fold_surfaces: Sequence[np.ndarray],
    folds: Sequence[dict],
    visible_catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    feather_px: float = 4.0,
    halo_radius_px: float = 9.5,
    halo_atten: float = 0.42,
) -> np.ndarray:
    """Construct the full-map inference surface from the 4 Out-of-Fold (`OOF`) quadrant
    surfaces with cosine cross-quadrant seam feathering and visible-catalogue halo
    de-crowding (`IR-91-S17-LFTG-01` fix).

    Every pixel in quadrant `q` was predicted strictly out-of-sample by models trained on
    quadrants `m != q`, eliminating in-sample memorization of `existing_faults.tif`.
    """
    fp = np.asarray(footprint, dtype=bool)
    shape = fp.shape
    num = np.zeros(shape, dtype=np.float32)
    den = np.zeros(shape, dtype=np.float32)

    for q, fold in enumerate(folds):
        reg = np.asarray(fold["region"], dtype=bool) & fp
        surf_q = np.asarray(fold_surfaces[q], dtype=np.float32)
        if feather_px > 0.0:
            # Distance inside region + soft feather across boundary
            d_out = ndi.distance_transform_edt(~reg)
            w_q = np.where(
                reg,
                1.0,
                np.where(
                    d_out <= float(feather_px),
                    0.5 * (1.0 + np.cos(np.pi * d_out / float(feather_px))),
                    0.0,
                ),
            ).astype(np.float32)
        else:
            w_q = reg.astype(np.float32)
        num += w_q * surf_q
        den += w_q

    stitched = np.zeros(shape, dtype=np.float32)
    valid = fp & (den > 1e-6)
    stitched[valid] = num[valid] / den[valid]

    # Smooth visible-catalogue halo de-crowding (depends ONLY on visible_catalogue & footprint)
    if halo_atten > 0.0 and halo_radius_px > 3.05:
        vis = np.asarray(visible_catalogue, dtype=bool) & fp
        d_vis = ndi.distance_transform_edt(~vis).astype(np.float32)
        span = max(float(halo_radius_px) - 3.05, 1.0)
        rel = np.clip((d_vis - 3.05) / span, 0.0, 1.0)
        taper = (1.0 - float(halo_atten) * (0.5 * (1.0 + np.cos(np.pi * rel)))).astype(np.float32)
        taper[d_vis > float(halo_radius_px)] = 1.0
        stitched[fp] = np.clip(stitched[fp] * taper[fp], 0.0, 1.0)

    stitched[~fp] = 0.0
    return stitched
