"""Session 19 (`S19-SVHF`): Semivariogram-Jump, Multi-Scale Hurst & Piedmont-Flexure
Stitched-OOF Submodular Hierarchy for Blind Geothermal Fault Discovery.

Implements preregistered hypotheses `H19-1` (`SVAR`), `H19-2` (`HPFC`), and `H19-3`
(`QDAC`) from `docs/HYPOTHESES_S19_SVHF.md` with four strict structural guarantees:
  1. Backbone-orthogonal 58-feature static stack (`0` reused `DD/SPAC/PTHA/HVDC` cols).
  2. Bitwise `0.0` dependence on `Band 12` (`det_elev`) and `Band 19` (`det_elev_slope`)
     across all 42 Pure-Subsurface static features (`Cols 0..41`) and all 7 Pure-Subsurface
     Stage-2 `QDAC` features (`Cols 7..13`).
  3. 3-level nested spatial cross-fitting (`1-quadrant -> 2-quadrant -> 3-quadrant`) so
     neither holdout competition quadrants nor the stitched 4-fold OOF full-footprint
     GeoTIFF ever suffer in-sample catalogue-halo score inflation (`IR-91-S17-LFTG-01`
     & `IR-91-S19-03` remediations).
  4. Clean 300-m triangular-kernel CELF submodular dot allocation with zero reward inside
     the `d_vis <= collar_px` known-fault collar and no off-crest probability distortion.
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
from scipy import ndimage as ndi
from scipy.special import logit, expit
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import mhtr_coda as MC

SVHF19_VERSION = "s19_svhf_v1"

# 42 strictly Band-12 / Band-19-free subsurface features (Cols 0..41)
SVHF19_SUBSURFACE_NAMES: list[str] = [
    # Block A1: Airborne flight-line destriped anomalies & seam diagnostic (4)
    "svar_rtp_destriped_hp",
    "svar_tmi_destriped_hp",
    "svar_tc_destriped_hp",
    "svar_flightline_seam_ratio",
    # Block A2: Cross-strike directional semivariograms on destriped B02 RTP (4)
    "svar_rtp_aniso_200m",
    "svar_rtp_hurst_exp",
    "svar_rtp_halfplane_sill_jump",
    "svar_rtp_hurst_step",
    # Block A3: Cross-strike directional semivariograms on B13 Isostatic Gravity (4)
    "svar_grav_aniso_200m",
    "svar_grav_hurst_exp",
    "svar_grav_halfplane_sill_jump",
    "svar_grav_hurst_step",
    # Block A4: Cross-strike directional semivariograms on B15 Depth-to-Basement (4)
    "svar_base_aniso_200m",
    "svar_base_hurst_exp",
    "svar_base_halfplane_sill_jump",
    "svar_base_hurst_step",
    # Block B: 3-D Laplace Spectral Gravity/Magnetic Tensor & Tabular Fault Phase (10)
    "tens_grav_cos_theta_200m",
    "tens_grav_cos_theta_600m",
    "tens_grav_worm_200m",
    "tens_grav_worm_600m",
    "tens_grav_worm_persist",
    "tens_grav_pedersen_q2d",
    "tens_grav_tabular_worm",
    "tens_rtp_cos_theta_250m",
    "tens_rtp_worm_250m",
    "tens_grav_mag_worm_concord",
    # Block C: Hydrothermal Disequilibrium, Clay-Cap Alteration & Crustal Strain (16)
    "hyd_geotherm_diseq_local",
    "hyd_thermal_upflow_local",
    "hyd_claycap_cond_resid",
    "hyd_mag_destruction_claycap",
    "hyd_rad_k_alteration_grad",
    "hyd_transtension_index",
    "hyd_shear_strain_local",
    "hyd_dilatation_local",
    "hyd_seismic_conduit_index",
    "hyd_basement_grad_worm",
    "hyd_basement_accommodation_saddle",
    "sub_b03_tmi_hg_local",
    "sub_b05_grav_slope_local",
    "sub_b09_tmi_vg_local",
    "sub_b11_grav_vg_local",
    "sub_b18_grav_hg_local",
]

# 16 Topographic Hurst-Exponent & Piedmont-Toe Concave Flexure features (Cols 42..57)
SVHF19_TOPO_NAMES: list[str] = [
    "hpfc_hurst_short_150_450",
    "hpfc_hurst_meso_450_1200",
    "hpfc_hurst_scale_break",
    "hpfc_hurst_step_grad",
    "hpfc_ptcf_150m",
    "hpfc_ptcf_400m",
    "hpfc_ptcf_900m",
    "hpfc_convex_crest_300m",
    "hpfc_scarp_dipole_400m",
    "hpfc_slope_local_100m",
    "hpfc_slope_ridge_coherence",
    "hpfc_elev_local_300m",
    "hpfc_elev_local_1200m",
    "hpfc_profile_curv_400m",
    "hpfc_subsurf_corrob_ptcf",
    "hpfc_cover_ness_index",
]

SVHF19_FEATURE_NAMES: list[str] = SVHF19_SUBSURFACE_NAMES + SVHF19_TOPO_NAMES
assert len(SVHF19_SUBSURFACE_NAMES) == 42
assert len(SVHF19_TOPO_NAMES) == 16
assert len(SVHF19_FEATURE_NAMES) == 58

QDAC_FULL_NAMES: list[str] = [
    "qdac_full_std_prob",
    "qdac_full_axial_max_600m",
    "qdac_full_axial_runnerup_600m",
    "qdac_full_axial_coherence_600m",
    "qdac_full_axial_persist_1300m",
    "qdac_full_relay_bridge_900m",
    "qdac_full_stepover_saddle_500m",
]
QDAC_SUB_NAMES: list[str] = [
    "qdac_sub_std_prob",
    "qdac_sub_axial_max_600m",
    "qdac_sub_axial_runnerup_600m",
    "qdac_sub_axial_coherence_600m",
    "qdac_sub_axial_persist_1300m",
    "qdac_sub_relay_bridge_900m",
    "qdac_sub_stepover_saddle_500m",
]
QDAC_FEATURE_NAMES: list[str] = QDAC_FULL_NAMES + QDAC_SUB_NAMES
assert len(QDAC_FEATURE_NAMES) == 14

BANNED_GDR_COLUMNS: frozenset[str] = frozenset(
    {"dist_known_fault_px", "dist_known_fault", "known_fault_dist"}
)


def sanitize_band(raw: np.ndarray, footprint: np.ndarray) -> tuple[np.ndarray, int]:
    """Sanitize NaN and finite float32 nodata sentinels (`|x| >= 1e15`) via EDT nearest fill."""
    arr = np.asarray(raw, dtype=np.float32)
    fp = np.asarray(footprint, dtype=bool)
    valid = fp & np.isfinite(arr) & (np.abs(arr) < 1.0e15)
    n_bad_fp = int((fp & ~valid).sum())
    if not valid.any():
        return np.zeros_like(arr, dtype=np.float32), n_bad_fp
    if not valid.all():
        idx = ndi.distance_transform_edt(~valid, return_distances=False, return_indices=True)
        filled = arr[tuple(idx)].astype(np.float32, copy=False)
    else:
        filled = arr.copy()
    return filled, n_bad_fp


def robust_z_clip(arr: np.ndarray, footprint: np.ndarray, clip: float = 8.0) -> np.ndarray:
    """Scale array by footprint median/IQR and clip to `[-clip, clip]` (`float32`)."""
    vals = np.asarray(arr[footprint], dtype=np.float32)
    sample = vals[::8] if vals.size > 64 else vals
    q25, q50, q75 = np.percentile(sample, [25.0, 50.0, 75.0])
    scale = float(max((q75 - q25) / 1.349, float(np.std(sample)), 1.0e-6))
    out = np.clip((arr - float(q50)) / scale, -float(clip), float(clip)).astype(np.float32)
    out[~footprint] = 0.0
    return out


def local_contrast_norm(arr: np.ndarray, footprint: np.ndarray, sigma_bg: float = 24.0) -> np.ndarray:
    """Translation-invariant local anomaly `(x - G_sigma(x)) / local_RMS` without regional bowls."""
    bg = ndi.gaussian_filter(arr, sigma=float(sigma_bg), mode="reflect")
    diff = (arr - bg).astype(np.float32)
    rms = np.sqrt(ndi.gaussian_filter(diff * diff, sigma=float(sigma_bg), mode="reflect") + 1.0e-6)
    return robust_z_clip(diff / rms, footprint)


def destripe_cardinal_fft(arr: np.ndarray, pad: int = 32) -> tuple[np.ndarray, np.ndarray]:
    """Suppress narrow N-S and E-W airborne flight-line/tie-line leveling stripes in 2-D FFT."""
    p = np.pad(arr.astype(np.float32, copy=False), pad, mode="reflect")
    hp, wp = p.shape
    ky = np.fft.fftfreq(hp)[:, None].astype(np.float32)
    kx = np.fft.rfftfreq(wp)[None, :].astype(np.float32)
    kr = np.hypot(kx, ky)

    # Smooth cardinal-axis notch only at short-to-medium wavelengths (kr > 1/40 px^-1)
    high_k = 1.0 / (1.0 + np.exp(-(kr - 0.030) / 0.008))
    notch_ns = 1.0 - 0.82 * np.exp(-((ky / 0.0045) ** 2)) * high_k
    notch_ew = 1.0 - 0.82 * np.exp(-((kx / 0.0045) ** 2)) * high_k
    filt = (notch_ns * notch_ew).astype(np.float32)

    spec = np.fft.rfft2(p)
    clean_p = np.fft.irfft2(spec * filt, s=(hp, wp)).astype(np.float32)
    clean = clean_p[pad : pad + arr.shape[0], pad : pad + arr.shape[1]]
    stripe = (arr - clean).astype(np.float32)
    return clean, stripe


def _shifted_sq_diff(u: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """Symmetric half-squared lag difference `0.5 * (u(x + d) - u(x - d))^2` with edge padding."""
    h, w = u.shape
    pad = max(abs(dy), abs(dx))
    up = np.pad(u, pad, mode="reflect")
    y0, x0 = pad, pad
    fwd = up[y0 + dy : y0 + dy + h, x0 + dx : x0 + dx + w]
    bwd = up[y0 - dy : y0 - dy + h, x0 - dx : x0 - dx + w]
    diff = fwd - bwd
    return (0.5 * diff * diff).astype(np.float32)


def compute_directional_semivariogram_features(
    field: np.ndarray,
    footprint: np.ndarray,
    *,
    sigma_win: float = 3.5,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute (`aniso_200m`, `hurst_exp`, `halfplane_sill_jump`, `hurst_step`) on `field`."""
    # Locally detrend regional background (>2.5 km) so variograms measure structural roughness
    u = (field - ndi.gaussian_filter(field, sigma=25.0, mode="reflect")).astype(np.float32)
    scale = float(np.percentile(np.abs(u[footprint])[::8], 90) + 1.0e-6)
    u = u / scale

    # 4 azimuths at ~200 m lag: E-W (0,1), N-S (1,0), NW-SE (1,1), NE-SW (1,-1)
    # Diagonal unit step has lag sqrt(2) vs 1.0; normalize diagonal variance by (1 / sqrt(2))^(2*0.7) ~ 0.62
    dirs_short = [(0, 1, 1.0), (1, 0, 1.0), (1, 1, 0.62), (1, -1, 0.62)]
    dirs_long = [(0, 3, 1.0), (3, 0, 1.0), (2, 2, 1.08), (2, -2, 1.08)]

    gam_short = []
    for dy, dx, w_norm in dirs_short:
        g = ndi.gaussian_filter(_shifted_sq_diff(u, dy, dx) * np.float32(w_norm), sigma=sigma_win, mode="reflect")
        gam_short.append(g)

    gam_long = []
    for dy, dx, w_norm in dirs_long:
        g = ndi.gaussian_filter(_shifted_sq_diff(u, dy, dx) * np.float32(w_norm), sigma=sigma_win * 1.4, mode="reflect")
        gam_long.append(g)

    g_max = np.maximum.reduce(gam_short)
    g_min = np.minimum.reduce(gam_short)
    g_bar_200 = (0.25 * (gam_short[0] + gam_short[1] + gam_short[2] + gam_short[3])).astype(np.float32)
    g_bar_600 = (0.25 * (gam_long[0] + gam_long[1] + gam_long[2] + gam_long[3])).astype(np.float32)

    eps = np.float32(1.0e-5)
    aniso = ((g_max - g_min) / (g_max + g_min + eps)).astype(np.float32)
    hurst = np.clip(0.5 * np.log((g_bar_600 + eps) / (g_bar_200 + eps)) / math.log(3.0), 0.0, 1.2).astype(np.float32)

    # Opposite half-plane log-sill jump across +/- 300 m normal offsets across 4 orientations
    log_sill = np.log(g_bar_200 + eps).astype(np.float32)
    lp = np.pad(log_sill, 3, mode="reflect")
    h, w = u.shape
    jumps = [
        np.abs(lp[3 : h + 3, 6 : w + 6] - lp[3 : h + 3, 0:w]),
        np.abs(lp[6 : h + 6, 3 : w + 3] - lp[0:h, 3 : w + 3]),
        np.abs(lp[5 : h + 5, 5 : w + 5] - lp[1 : h + 1, 1 : w + 1]),
        np.abs(lp[5 : h + 5, 1 : w + 1] - lp[1 : h + 1, 5 : w + 5]),
    ]
    sill_jump = np.maximum.reduce(jumps).astype(np.float32)

    hy = ndi.gaussian_filter(hurst, sigma=1.2, order=[1, 0], mode="reflect")
    hx = ndi.gaussian_filter(hurst, sigma=1.2, order=[0, 1], mode="reflect")
    hurst_step = np.hypot(hx, hy).astype(np.float32)

    return (
        robust_z_clip(aniso, footprint),
        robust_z_clip(hurst, footprint),
        robust_z_clip(sill_jump, footprint),
        robust_z_clip(hurst_step, footprint),
    )


def compute_laplace_tensor_features(
    grav_b13: np.ndarray,
    rtp_clean: np.ndarray,
    footprint: np.ndarray,
    *,
    pad: int = 64,
) -> list[np.ndarray]:
    """Compute 10 spectral 3-D Laplace gravity + RTP phase/worm/Pedersen-Q2D features."""
    h, w = grav_b13.shape
    gp = np.pad(grav_b13 - ndi.gaussian_filter(grav_b13, sigma=45.0, mode="reflect"), pad, mode="reflect").astype(
        np.float32
    )
    hp, wp = gp.shape
    ky = (2.0 * math.pi * np.fft.fftfreq(hp))[:, None].astype(np.float32)
    kx = (2.0 * math.pi * np.fft.rfftfreq(wp))[None, :].astype(np.float32)
    kr = np.hypot(kx, ky).astype(np.float32)

    G_spec = np.fft.rfft2(gp)

    def _grav_tensor_at_z(z_px: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        up = np.exp(-kr * float(z_px)).astype(np.float32)
        F = G_spec * up
        txx = np.fft.irfft2(-(kx * kx) * F, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        tyy = np.fft.irfft2(-(ky * ky) * F, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        txy = np.fft.irfft2(-(kx * ky) * F, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        txz = np.fft.irfft2((1j * kx * kr) * F, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        tyz = np.fft.irfft2((1j * ky * kr) * F, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
        tzz = -(txx + tyy)  # Exact 3-D Laplace harmonicity

        eps = np.float32(1.0e-7)
        cos_theta = (-tzz / np.sqrt(txz * txz + tyz * tyz + tzz * tzz + eps)).astype(np.float32)
        cy = ndi.gaussian_filter(cos_theta, sigma=1.0, order=[1, 0], mode="reflect")
        cx = ndi.gaussian_filter(cos_theta, sigma=1.0, order=[0, 1], mode="reflect")
        worm = np.hypot(cx, cy).astype(np.float32)

        # Pedersen-Rasmussen (1990) 3-D dimensionality invariant I = -27 * det(T) / ||T||_F^3
        det_t = (
            txx * (tyy * tzz - tyz * tyz)
            - txy * (txy * tzz - tyz * txz)
            + txz * (txy * tyz - tyy * txz)
        )
        frob_sq = txx * txx + tyy * tyy + tzz * tzz + 2.0 * (txy * txy + txz * txz + tyz * tyz)
        inv_i = np.clip(-27.0 * det_t / (np.power(frob_sq + eps, 1.5)), -1.0, 1.0)
        q2d = (1.0 - np.abs(inv_i)).astype(np.float32)
        return cos_theta, worm, q2d

    cos_g200, worm_g200, q2d_g200 = _grav_tensor_at_z(2.0)
    cos_g600, worm_g600, _ = _grav_tensor_at_z(6.0)
    worm_persist = np.sqrt(np.maximum(worm_g200, 0.0) * np.maximum(worm_g600, 0.0)).astype(np.float32)
    tab_worm = (worm_persist * q2d_g200).astype(np.float32)

    # Analytical Cooper-Cowan magnetic tilt on destriped B02 RTP at z=250 m (replacing mislabeled B06!)
    mp = np.pad(rtp_clean - ndi.gaussian_filter(rtp_clean, sigma=40.0, mode="reflect"), pad, mode="reflect").astype(
        np.float32
    )
    M_spec = np.fft.rfft2(mp) * np.exp(-kr * 2.5).astype(np.float32)
    mx = np.fft.irfft2((1j * kx) * M_spec, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
    my = np.fft.irfft2((1j * ky) * M_spec, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
    mz = np.fft.irfft2(kr * M_spec, s=(hp, wp))[pad : pad + h, pad : pad + w].astype(np.float32)
    mh = np.hypot(mx, my)
    cos_m250 = np.arctan2(mz, mh + 1.0e-6).astype(np.float32)
    mcy = ndi.gaussian_filter(cos_m250, sigma=1.0, order=[1, 0], mode="reflect")
    mcx = ndi.gaussian_filter(cos_m250, sigma=1.0, order=[0, 1], mode="reflect")
    worm_m250 = np.hypot(mcx, mcy).astype(np.float32)

    concord = np.sqrt(np.maximum(worm_g200, 0.0) * np.maximum(worm_m250, 0.0)).astype(np.float32)

    return [
        robust_z_clip(cos_g200, footprint),
        robust_z_clip(cos_g600, footprint),
        robust_z_clip(worm_g200, footprint),
        robust_z_clip(worm_g600, footprint),
        robust_z_clip(worm_persist, footprint),
        robust_z_clip(q2d_g200, footprint),
        robust_z_clip(tab_worm, footprint),
        robust_z_clip(cos_m250, footprint),
        robust_z_clip(worm_m250, footprint),
        robust_z_clip(concord, footprint),
    ]


def compute_gdr_hydrothermal_features(
    gdr_csv: Path,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Compute strictly local (`<= 1.2 km`) GDR #1391 geothermometer disequilibrium & thermal upflow.

    Explicitly bans `dist_known_fault_px` (`IR-91-S17-03`).
    """
    h, w = footprint.shape
    imp_diseq = np.zeros((h, w), dtype=np.float32)
    imp_temp = np.zeros((h, w), dtype=np.float32)
    imp_cnt = np.zeros((h, w), dtype=np.float32)
    has_pt = np.zeros((h, w), dtype=bool)

    rows_used = 0
    with Path(gdr_csv).open("r", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header_cols = list(reader.fieldnames or [])
        allowed_cols = [c for c in header_cols if c not in BANNED_GDR_COLUMNS]
        for rec in reader:
            # Never inspect any banned fault-distance column
            try:
                r = int(round(float(rec["row"])))
                c = int(round(float(rec["col"])))
            except (KeyError, TypeError, ValueError):
                continue
            if not (0 <= r < h and 0 <= c < w and footprint[r, c]):
                continue
            vals_geo = []
            for gk in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                raw_v = (rec.get(gk) or "").strip()
                if raw_v:
                    try:
                        fv = float(raw_v)
                        if math.isfinite(fv) and -20.0 <= fv <= 400.0:
                            vals_geo.append(fv)
                    except ValueError:
                        pass
            t_meas = None
            raw_t = (rec.get("temp_c") or "").strip()
            if raw_t:
                try:
                    ft = float(raw_t)
                    if math.isfinite(ft) and -10.0 <= ft <= 250.0:
                        t_meas = ft
                except ValueError:
                    pass
            if t_meas is None and not vals_geo:
                continue

            t_obs = t_meas if t_meas is not None else 15.0
            t_eq = max(vals_geo) if vals_geo else t_obs
            diseq = max(0.0, min(t_eq - t_obs, 220.0))
            excess_t = max(0.0, min(t_obs - 18.0, 150.0))

            imp_diseq[r, c] += float(diseq)
            imp_temp[r, c] += float(excess_t)
            imp_cnt[r, c] += 1.0
            has_pt[r, c] = True
            rows_used += 1

    if rows_used > 0:
        d_well = ndi.distance_transform_edt(~has_pt).astype(np.float32)
        env = np.exp(-0.5 * (d_well / 8.5) ** 2).astype(np.float32)  # strictly local <= ~1.2 km envelope
        loc_d = ndi.gaussian_filter(imp_diseq, sigma=4.0, mode="constant") / (
            ndi.gaussian_filter(imp_cnt, sigma=4.0, mode="constant") + 1.0e-4
        )
        reg_d = ndi.gaussian_filter(imp_diseq, sigma=24.0, mode="constant") / (
            ndi.gaussian_filter(imp_cnt, sigma=24.0, mode="constant") + 1.0e-4
        )
        diseq_local = np.maximum(loc_d - 0.65 * reg_d, 0.0) * env

        loc_t = ndi.gaussian_filter(imp_temp, sigma=4.5, mode="constant") / (
            ndi.gaussian_filter(imp_cnt, sigma=4.5, mode="constant") + 1.0e-4
        )
        reg_t = ndi.gaussian_filter(imp_temp, sigma=26.0, mode="constant") / (
            ndi.gaussian_filter(imp_cnt, sigma=26.0, mode="constant") + 1.0e-4
        )
        temp_local = np.maximum(loc_t - 0.65 * reg_t, 0.0) * env
    else:
        diseq_local = np.zeros((h, w), dtype=np.float32)
        temp_local = np.zeros((h, w), dtype=np.float32)

    stats = {
        "rows_inside_footprint_used": rows_used,
        "header_columns": header_cols,
        "allowed_columns_read": [c for c in allowed_cols if c in {"row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"}],
        "banned_columns_excluded": sorted(BANNED_GDR_COLUMNS.intersection(header_cols)),
    }
    return robust_z_clip(diseq_local, footprint), robust_z_clip(temp_local, footprint), stats


def _directional_ridge_coherence_8az(field: np.ndarray) -> np.ndarray:
    """8-azimuth anisotropic ridge persistence `(max_theta - mean_theta) / (max_theta + eps)`."""
    pos = np.maximum(field, 0.0).astype(np.float32)
    responses = []
    for k in range(8):
        theta = k * (math.pi / 8.0)
        dy = math.sin(theta)
        dx = math.cos(theta)
        acc = pos.copy()
        for step, wt in ((2, 0.85), (4, 0.65), (6, 0.45)):
            sy = int(round(step * dy))
            sx = int(round(step * dx))
            h, w = pos.shape
            pad = max(abs(sy), abs(sx))
            pp = np.pad(pos, pad, mode="reflect")
            acc = acc + wt * (
                pp[pad + sy : pad + sy + h, pad + sx : pad + sx + w]
                + pp[pad - sy : pad - sy + h, pad - sx : pad - sx + w]
            )
        responses.append(acc)
    rmax = np.maximum.reduce(responses)
    rmean = sum(responses) / 8.0
    return ((rmax - rmean) / (rmax + 1.0e-4)).astype(np.float32)


def compute_hpfc_topo_features(
    b12_elev: np.ndarray,
    b19_slope: np.ndarray,
    b15_depth: np.ndarray,
    worm_g200_z: np.ndarray,
    svar_grav_jump_z: np.ndarray,
    footprint: np.ndarray,
) -> list[np.ndarray]:
    """Compute 16 `H19-2` Multi-Scale Topographic Hurst & Piedmont-Toe Concave Flexure features."""
    z = b12_elev.astype(np.float32, copy=False)

    def _local_var(sig: float) -> np.ndarray:
        m1 = ndi.gaussian_filter(z, sigma=sig, mode="reflect")
        m2 = ndi.gaussian_filter(z * z, sigma=sig, mode="reflect")
        return np.maximum(m2 - m1 * m1, 0.0).astype(np.float32)

    v15 = _local_var(1.5)
    v45 = _local_var(4.5)
    v120 = _local_var(12.0)
    eps = np.float32(1.0e-4)

    h_short = np.clip(0.5 * np.log((v45 + eps) / (v15 + eps)) / math.log(3.0), 0.0, 1.2).astype(np.float32)
    h_meso = np.clip(0.5 * np.log((v120 + eps) / (v45 + eps)) / math.log(12.0 / 4.5), 0.0, 1.2).astype(np.float32)
    h_break = (h_meso - h_short).astype(np.float32)
    hy = ndi.gaussian_filter(h_short, sigma=1.5, order=[1, 0], mode="reflect")
    hx = ndi.gaussian_filter(h_short, sigma=1.5, order=[0, 1], mode="reflect")
    h_step = np.hypot(hx, hy).astype(np.float32)

    # Piedmont-Toe Concave Flexure: positive concave-upward Laplacian (-nabla^2_sigma z_det > 0)
    lap15 = ndi.gaussian_laplace(z, sigma=1.5, mode="reflect").astype(np.float32)
    lap40 = ndi.gaussian_laplace(z, sigma=4.0, mode="reflect").astype(np.float32)
    lap90 = ndi.gaussian_laplace(z, sigma=9.0, mode="reflect").astype(np.float32)
    lap30 = ndi.gaussian_laplace(z, sigma=3.0, mode="reflect").astype(np.float32)

    ptcf_150 = np.maximum(-lap15, 0.0)
    ptcf_400 = np.maximum(-lap40, 0.0)
    ptcf_900 = np.maximum(-lap90, 0.0)
    conv_300 = np.maximum(+lap30, 0.0)

    # Normal-fault scarp dipole: nearby convex footwall crest paired with concave hanging-wall toe
    scarp_dipole = np.sqrt(
        ndi.gaussian_filter(conv_300, sigma=3.0, mode="reflect")
        * ndi.gaussian_filter(ptcf_400, sigma=3.0, mode="reflect")
    ).astype(np.float32)

    slope_loc = local_contrast_norm(b19_slope, footprint, sigma_bg=20.0)
    slope_coh = robust_z_clip(_directional_ridge_coherence_8az(np.maximum(slope_loc, 0.0)), footprint)

    elev_300 = (z - ndi.gaussian_filter(z, sigma=3.0, mode="reflect")).astype(np.float32)
    elev_1200 = (z - ndi.gaussian_filter(z, sigma=12.0, mode="reflect")).astype(np.float32)

    # Down-slope profile curvature along nabla z_det (sigma = 4.0 px)
    zy = ndi.gaussian_filter(z, sigma=4.0, order=[1, 0], mode="reflect")
    zx = ndi.gaussian_filter(z, sigma=4.0, order=[0, 1], mode="reflect")
    zyy = ndi.gaussian_filter(z, sigma=4.0, order=[2, 0], mode="reflect")
    zxx = ndi.gaussian_filter(z, sigma=4.0, order=[0, 2], mode="reflect")
    zxy = ndi.gaussian_filter(z, sigma=4.0, order=[1, 1], mode="reflect")
    g2 = zx * zx + zy * zy + 1.0e-5
    prof_curv = (-(zxx * zx * zx + 2.0 * zxy * zx * zy + zyy * zy * zy) / g2).astype(np.float32)

    ptcf_400_z = robust_z_clip(ptcf_400, footprint)
    sub_support = np.maximum(0.5 * np.maximum(worm_g200_z, 0.0) + 0.5 * np.maximum(svar_grav_jump_z, 0.0), 0.0)
    corrob_ptcf = robust_z_clip(np.maximum(ptcf_400_z, 0.0) * sub_support, footprint)

    # Bounded [0, 1] alluvial basin cover-ness index for E3 cover-adaptive specialist gate
    d_med, d_iqr = np.percentile(b15_depth[footprint][::8], [50.0, 75.0])
    s_med, s_iqr = np.percentile(b19_slope[footprint][::8], [50.0, 75.0])
    d_sc = (b15_depth - float(d_med)) / max(float(d_iqr - d_med), 1.0e-4)
    s_sc = (b19_slope - float(s_med)) / max(float(s_iqr - s_med), 1.0e-4)
    cover_ness = (expit(np.clip(d_sc, -6.0, 6.0)) * expit(np.clip(-s_sc, -6.0, 6.0))).astype(np.float32)
    cover_ness[~footprint] = 0.0

    return [
        robust_z_clip(h_short, footprint),
        robust_z_clip(h_meso, footprint),
        robust_z_clip(h_break, footprint),
        robust_z_clip(h_step, footprint),
        robust_z_clip(ptcf_150, footprint),
        ptcf_400_z,
        robust_z_clip(ptcf_900, footprint),
        robust_z_clip(conv_300, footprint),
        robust_z_clip(scarp_dipole, footprint),
        slope_loc,
        slope_coh,
        robust_z_clip(elev_300, footprint),
        robust_z_clip(elev_1200, footprint),
        robust_z_clip(prof_curv, footprint),
        corrob_ptcf,
        cover_ness,
    ]


def compute_svhf19_feature_dict_from_bands(
    bands_19: np.ndarray,
    footprint: np.ndarray,
    gdr_csv: Path | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    """Compute all 58 `SVHF19` 2-D arrays from `(19, H, W)` bands (used for both full stack & bitwise B12/B19 test)."""
    assert bands_19.shape[0] == 19
    fp = np.asarray(footprint, dtype=bool)
    sanitized_counts: dict[str, int] = {}

    def _b(idx0: int) -> np.ndarray:
        clean, n_bad = sanitize_band(bands_19[idx0], fp)
        sanitized_counts[f"B{idx0 + 1:02d}"] = n_bad
        return clean

    b02 = _b(1)   # rtp
    b03 = _b(2)   # tmi_hg
    b04 = _b(3)   # geod_2ndinv
    b05 = _b(4)   # iso_grav_anom_slope
    b06 = _b(5)   # tc (radiometric total count)
    b07 = _b(6)   # geod_shearrate
    b08 = _b(7)   # geod_dilaterate
    b09 = _b(8)   # tmi_vg
    b10 = _b(9)   # deq_n100a15
    b11 = _b(10)  # iso_grav_anom_vg
    b12 = _b(11)  # det_elev (TOPO ONLY)
    b13 = _b(12)  # iso_grav_anom
    b14 = _b(13)  # tmi
    b15 = _b(14)  # depth_to_base_surf
    b16 = _b(15)  # ieq_n100a15
    b17 = _b(16)  # cond_surf
    b18 = _b(17)  # iso_grav_anom_hg
    b19 = _b(18)  # det_elev_slope (TOPO ONLY)

    out: dict[str, np.ndarray] = {}

    # Block A1: Destriping
    rtp_clean, rtp_stripe = destripe_cardinal_fft(b02)
    tmi_clean, tmi_stripe = destripe_cardinal_fft(b14)
    tc_clean, tc_stripe = destripe_cardinal_fft(b06)

    out["svar_rtp_destriped_hp"] = local_contrast_norm(rtp_clean, fp, sigma_bg=16.0)
    out["svar_tmi_destriped_hp"] = local_contrast_norm(tmi_clean, fp, sigma_bg=16.0)
    out["svar_tc_destriped_hp"] = local_contrast_norm(tc_clean, fp, sigma_bg=16.0)
    seam_e = (
        ndi.gaussian_filter(rtp_stripe * rtp_stripe, sigma=4.0, mode="reflect")
        / (ndi.gaussian_filter(rtp_clean * rtp_clean, sigma=8.0, mode="reflect") + 1.0e-4)
        + ndi.gaussian_filter(tc_stripe * tc_stripe, sigma=4.0, mode="reflect")
        / (ndi.gaussian_filter(tc_clean * tc_clean, sigma=8.0, mode="reflect") + 1.0e-4)
    )
    out["svar_flightline_seam_ratio"] = robust_z_clip(seam_e.astype(np.float32), fp)

    # Block A2..A4: Cross-strike directional semivariograms
    for mod, arr in (("rtp", rtp_clean), ("grav", b13), ("base", b15)):
        aniso, hurst, sjump, hstep = compute_directional_semivariogram_features(arr, fp)
        out[f"svar_{mod}_aniso_200m"] = aniso
        out[f"svar_{mod}_hurst_exp"] = hurst
        out[f"svar_{mod}_halfplane_sill_jump"] = sjump
        out[f"svar_{mod}_hurst_step"] = hstep

    # Block B: 3-D Laplace potential-field tensor
    tens_list = compute_laplace_tensor_features(b13, rtp_clean, fp)
    tens_names = SVHF19_SUBSURFACE_NAMES[16:26]
    for k_name, arr_v in zip(tens_names, tens_list):
        out[k_name] = arr_v

    # Block C: Hydrothermal disequilibrium, clay-cap & crustal strain (strictly B12/B19-free)
    if gdr_csv is not None and Path(gdr_csv).is_file():
        diseq_z, temp_z, gdr_stats = compute_gdr_hydrothermal_features(Path(gdr_csv), fp)
    else:
        diseq_z = np.zeros_like(b13, dtype=np.float32)
        temp_z = np.zeros_like(b13, dtype=np.float32)
        gdr_stats = {"rows_inside_footprint_used": 0, "banned_columns_excluded": ["dist_known_fault_px"]}

    out["hyd_geotherm_diseq_local"] = diseq_z
    out["hyd_thermal_upflow_local"] = temp_z

    # Deconfound B17 shallow conductivity against [1, B15, B15^2] on footprint (strips closed-basin playa trend)
    d_fp = b15[fp].astype(np.float64)
    d_std = (d_fp - d_fp.mean()) / (d_fp.std() + 1.0e-8)
    X_reg = np.column_stack([np.ones_like(d_std), d_std, d_std * d_std])
    beta, *_ = np.linalg.lstsq(X_reg[::8], b17[fp][::8].astype(np.float64), rcond=None)
    cond_res = np.zeros_like(b17, dtype=np.float32)
    cond_res[fp] = (b17[fp].astype(np.float64) - X_reg @ beta).astype(np.float32)
    cond_res_z = local_contrast_norm(cond_res, fp, sigma_bg=22.0)
    out["hyd_claycap_cond_resid"] = cond_res_z
    out["hyd_mag_destruction_claycap"] = robust_z_clip(
        np.maximum(cond_res_z, 0.0) * np.maximum(-out["svar_rtp_destriped_hp"], 0.0),
        fp,
    )

    tcy = ndi.gaussian_filter(tc_clean, sigma=1.5, order=[1, 0], mode="reflect")
    tcx = ndi.gaussian_filter(tc_clean, sigma=1.5, order=[0, 1], mode="reflect")
    out["hyd_rad_k_alteration_grad"] = local_contrast_norm(np.hypot(tcx, tcy).astype(np.float32), fp, sigma_bg=20.0)

    b04_loc = local_contrast_norm(b04, fp, sigma_bg=28.0)
    b08_loc = local_contrast_norm(b08, fp, sigma_bg=28.0)
    out["hyd_transtension_index"] = robust_z_clip(
        np.maximum(b04_loc, 0.0) * np.maximum(b08_loc, 0.0), fp
    )
    out["hyd_shear_strain_local"] = local_contrast_norm(b07, fp, sigma_bg=28.0)
    out["hyd_dilatation_local"] = b08_loc

    deq_med = float(np.median(b10[fp][::8]) + 1.0e-4)
    eq_prox = np.exp(-np.maximum(b10, 0.0) / deq_med).astype(np.float32)
    ieq_loc = np.maximum(local_contrast_norm(b16, fp, sigma_bg=24.0), 0.0)
    out["hyd_seismic_conduit_index"] = robust_z_clip(eq_prox * (0.5 + ieq_loc), fp)

    by = ndi.gaussian_filter(b15, sigma=2.0, order=[1, 0], mode="reflect")
    bx = ndi.gaussian_filter(b15, sigma=2.0, order=[0, 1], mode="reflect")
    byy = ndi.gaussian_filter(b15, sigma=3.0, order=[2, 0], mode="reflect")
    bxx = ndi.gaussian_filter(b15, sigma=3.0, order=[0, 2], mode="reflect")
    bxy = ndi.gaussian_filter(b15, sigma=3.0, order=[1, 1], mode="reflect")
    out["hyd_basement_grad_worm"] = local_contrast_norm(np.hypot(bx, by).astype(np.float32), fp, sigma_bg=22.0)
    out["hyd_basement_accommodation_saddle"] = robust_z_clip(np.maximum(-(bxx * byy - bxy * bxy), 0.0), fp)

    out["sub_b03_tmi_hg_local"] = local_contrast_norm(b03, fp, sigma_bg=20.0)
    out["sub_b05_grav_slope_local"] = local_contrast_norm(b05, fp, sigma_bg=20.0)
    out["sub_b09_tmi_vg_local"] = local_contrast_norm(b09, fp, sigma_bg=20.0)
    out["sub_b11_grav_vg_local"] = local_contrast_norm(b11, fp, sigma_bg=20.0)
    out["sub_b18_grav_hg_local"] = local_contrast_norm(b18, fp, sigma_bg=20.0)

    # Block D (Cols 42..57): Topographic Hurst & Piedmont-Toe Concave Flexure
    topo_list = compute_hpfc_topo_features(
        b12_elev=b12,
        b19_slope=b19,
        b15_depth=b15,
        worm_g200_z=out["tens_grav_worm_200m"],
        svar_grav_jump_z=out["svar_grav_halfplane_sill_jump"],
        footprint=fp,
    )
    for k_name, arr_v in zip(SVHF19_TOPO_NAMES, topo_list):
        out[k_name] = arr_v

    assert list(out.keys()) == SVHF19_FEATURE_NAMES
    meta = {
        "version": SVHF19_VERSION,
        "total_features": len(SVHF19_FEATURE_NAMES),
        "pure_subsurface_features": len(SVHF19_SUBSURFACE_NAMES),
        "topo_features": len(SVHF19_TOPO_NAMES),
        "sanitized_footprint_cells_by_band": sanitized_counts,
        "gdr_stats": gdr_stats,
    }
    return out, meta


def verify_pure_subsurface_b12_b19_invariance(
    features_tif: Path,
    gdr_csv: Path,
    window_size: int = 256,
) -> float:
    """Programmatically verify bitwise `0.0` sensitivity of Cols 0..41 to `B12` and `B19`."""
    with rasterio.open(features_tif) as ds:
        r0 = (ds.height - window_size) // 2
        c0 = (ds.width - window_size) // 2
        win = rasterio.windows.Window(c0, r0, window_size, window_size)
        sub_bands = ds.read(window=win).astype(np.float32)
    fp_sub = np.isfinite(sub_bands[12]) & (np.abs(sub_bands[12]) < 1.0e15)
    if not fp_sub.any():
        fp_sub = np.ones((window_size, window_size), dtype=bool)

    d_orig, _ = compute_svhf19_feature_dict_from_bands(sub_bands, fp_sub, gdr_csv=None)
    perturbed = sub_bands.copy()
    fin12 = np.isfinite(perturbed[11]) & (np.abs(perturbed[11]) < 1.0e15)
    fin19 = np.isfinite(perturbed[18]) & (np.abs(perturbed[18]) < 1.0e15)
    perturbed[11] = np.where(fin12, perturbed[11] * -0.5 + 1250.0, perturbed[11]).astype(np.float32)
    perturbed[18] = np.where(fin19, 42.0, perturbed[18]).astype(np.float32)
    d_pert, _ = compute_svhf19_feature_dict_from_bands(perturbed, fp_sub, gdr_csv=None)

    max_diff = 0.0
    for name in SVHF19_SUBSURFACE_NAMES:
        diff = float(np.max(np.abs(d_orig[name] - d_pert[name])))
        if diff > max_diff:
            max_diff = diff
    return max_diff


def build_or_load_svhf19_memmap(
    *,
    features_tif: Path,
    gdr_csv: Path,
    footprint: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], dict[str, object]]:
    """Stream-build or load `(n_fp, 58)` `float16` feature matrix on disk (`< 500 MB` peak RAM)."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    n_cols = len(SVHF19_FEATURE_NAMES)
    mmap_path = cache_dir / f"{SVHF19_VERSION}_fp_f16.mmap"
    meta_path = cache_dir / f"{SVHF19_VERSION}_meta.json"
    expected_bytes = n_fp * n_cols * 2

    if mmap_path.is_file() and meta_path.is_file() and mmap_path.stat().st_size == expected_bytes:
        meta = json.loads(meta_path.read_text())
        if meta.get("version") == SVHF19_VERSION and meta.get("feature_names") == SVHF19_FEATURE_NAMES:
            mm = np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols))
            return mm, list(SVHF19_FEATURE_NAMES), meta

    mm = np.memmap(mmap_path, dtype=np.float16, mode="w+", shape=(n_fp, n_cols))
    col_idx = {name: j for j, name in enumerate(SVHF19_FEATURE_NAMES)}
    written: set[str] = set()
    sanitized_counts: dict[str, int] = {}

    def _put(name: str, arr2d: np.ndarray) -> None:
        mm[:, col_idx[name]] = np.clip(arr2d[fp], -32.0, 32.0).astype(np.float16)
        written.add(name)

    with rasterio.open(features_tif) as ds:
        def _read_clean(b1: int) -> np.ndarray:
            clean, n_bad = sanitize_band(ds.read(b1), fp)
            sanitized_counts[f"B{b1:02d}"] = n_bad
            return clean

        # Block A1: Destriping (B02, B14, B06)
        b02 = _read_clean(2)
        rtp_clean, rtp_stripe = destripe_cardinal_fft(b02)
        del b02
        rtp_hp = local_contrast_norm(rtp_clean, fp, sigma_bg=16.0)
        _put("svar_rtp_destriped_hp", rtp_hp)

        b14 = _read_clean(14)
        tmi_clean, _ = destripe_cardinal_fft(b14)
        del b14
        _put("svar_tmi_destriped_hp", local_contrast_norm(tmi_clean, fp, sigma_bg=16.0))
        del tmi_clean

        b06 = _read_clean(6)
        tc_clean, tc_stripe = destripe_cardinal_fft(b06)
        del b06
        _put("svar_tc_destriped_hp", local_contrast_norm(tc_clean, fp, sigma_bg=16.0))

        seam_e = (
            ndi.gaussian_filter(rtp_stripe * rtp_stripe, sigma=4.0, mode="reflect")
            / (ndi.gaussian_filter(rtp_clean * rtp_clean, sigma=8.0, mode="reflect") + 1.0e-4)
            + ndi.gaussian_filter(tc_stripe * tc_stripe, sigma=4.0, mode="reflect")
            / (ndi.gaussian_filter(tc_clean * tc_clean, sigma=8.0, mode="reflect") + 1.0e-4)
        )
        del rtp_stripe, tc_stripe
        _put("svar_flightline_seam_ratio", robust_z_clip(seam_e.astype(np.float32), fp))
        del seam_e
        gc.collect()

        # Radiometric alteration gradient while tc_clean is in RAM
        tcy = ndi.gaussian_filter(tc_clean, sigma=1.5, order=[1, 0], mode="reflect")
        tcx = ndi.gaussian_filter(tc_clean, sigma=1.5, order=[0, 1], mode="reflect")
        del tc_clean
        _put("hyd_rad_k_alteration_grad", local_contrast_norm(np.hypot(tcx, tcy).astype(np.float32), fp, sigma_bg=20.0))
        del tcx, tcy

        # Block A2: RTP semivariogram
        for suf, arr_v in zip(
            ("aniso_200m", "hurst_exp", "halfplane_sill_jump", "hurst_step"),
            compute_directional_semivariogram_features(rtp_clean, fp),
        ):
            _put(f"svar_rtp_{suf}", arr_v)

        # Read B13 (iso_grav_anom) & B15 (depth_to_base_surf)
        b13 = _read_clean(13)
        svar_grav = compute_directional_semivariogram_features(b13, fp)
        svar_grav_jump_z = svar_grav[2]
        for suf, arr_v in zip(("aniso_200m", "hurst_exp", "halfplane_sill_jump", "hurst_step"), svar_grav):
            _put(f"svar_grav_{suf}", arr_v)
        del svar_grav

        # Block B: 3-D Laplace Tensor on B13 + rtp_clean
        tens_list = compute_laplace_tensor_features(b13, rtp_clean, fp)
        del rtp_clean, b13
        worm_g200_z = tens_list[2]
        for k_name, arr_v in zip(SVHF19_SUBSURFACE_NAMES[16:26], tens_list):
            _put(k_name, arr_v)
        del tens_list
        gc.collect()

        # B15 semivariogram + basement worm/saddle + B17 claycap deconfounding
        b15 = _read_clean(15)
        for suf, arr_v in zip(
            ("aniso_200m", "hurst_exp", "halfplane_sill_jump", "hurst_step"),
            compute_directional_semivariogram_features(b15, fp),
        ):
            _put(f"svar_base_{suf}", arr_v)

        diseq_z, temp_z, gdr_stats = compute_gdr_hydrothermal_features(Path(gdr_csv), fp)
        _put("hyd_geotherm_diseq_local", diseq_z)
        _put("hyd_thermal_upflow_local", temp_z)
        del diseq_z, temp_z

        b17 = _read_clean(17)
        d_fp = b15[fp].astype(np.float64)
        d_std = (d_fp - d_fp.mean()) / (d_fp.std() + 1.0e-8)
        X_reg = np.column_stack([np.ones_like(d_std), d_std, d_std * d_std])
        beta, *_ = np.linalg.lstsq(X_reg[::8], b17[fp][::8].astype(np.float64), rcond=None)
        cond_res = np.zeros_like(b17, dtype=np.float32)
        cond_res[fp] = (b17[fp].astype(np.float64) - X_reg @ beta).astype(np.float32)
        del b17, d_fp, d_std, X_reg
        cond_res_z = local_contrast_norm(cond_res, fp, sigma_bg=22.0)
        del cond_res
        _put("hyd_claycap_cond_resid", cond_res_z)
        _put(
            "hyd_mag_destruction_claycap",
            robust_z_clip(np.maximum(cond_res_z, 0.0) * np.maximum(-rtp_hp, 0.0), fp),
        )
        del cond_res_z, rtp_hp
        gc.collect()

        b04_loc = local_contrast_norm(_read_clean(4), fp, sigma_bg=28.0)
        b08_loc = local_contrast_norm(_read_clean(8), fp, sigma_bg=28.0)
        _put("hyd_transtension_index", robust_z_clip(np.maximum(b04_loc, 0.0) * np.maximum(b08_loc, 0.0), fp))
        _put("hyd_dilatation_local", b08_loc)
        del b04_loc, b08_loc
        _put("hyd_shear_strain_local", local_contrast_norm(_read_clean(7), fp, sigma_bg=28.0))

        b10 = _read_clean(10)
        deq_med = float(np.median(b10[fp][::8]) + 1.0e-4)
        eq_prox = np.exp(-np.maximum(b10, 0.0) / deq_med).astype(np.float32)
        del b10
        ieq_loc = np.maximum(local_contrast_norm(_read_clean(16), fp, sigma_bg=24.0), 0.0)
        _put("hyd_seismic_conduit_index", robust_z_clip(eq_prox * (0.5 + ieq_loc), fp))
        del eq_prox, ieq_loc

        by = ndi.gaussian_filter(b15, sigma=2.0, order=[1, 0], mode="reflect")
        bx = ndi.gaussian_filter(b15, sigma=2.0, order=[0, 1], mode="reflect")
        _put("hyd_basement_grad_worm", local_contrast_norm(np.hypot(bx, by).astype(np.float32), fp, sigma_bg=22.0))
        del bx, by
        byy = ndi.gaussian_filter(b15, sigma=3.0, order=[2, 0], mode="reflect")
        bxx = ndi.gaussian_filter(b15, sigma=3.0, order=[0, 2], mode="reflect")
        bxy = ndi.gaussian_filter(b15, sigma=3.0, order=[1, 1], mode="reflect")
        _put("hyd_basement_accommodation_saddle", robust_z_clip(np.maximum(-(bxx * byy - bxy * bxy), 0.0), fp))
        del bxx, byy, bxy

        for b_idx, cname in (
            (3, "sub_b03_tmi_hg_local"),
            (5, "sub_b05_grav_slope_local"),
            (9, "sub_b09_tmi_vg_local"),
            (11, "sub_b11_grav_vg_local"),
            (18, "sub_b18_grav_hg_local"),
        ):
            _put(cname, local_contrast_norm(_read_clean(b_idx), fp, sigma_bg=20.0))
        gc.collect()

        # Block D (Cols 42..57): Topographic Hurst & Piedmont-Toe Concave Flexure
        b12 = _read_clean(12)
        b19 = _read_clean(19)
        topo_list = compute_hpfc_topo_features(
            b12_elev=b12,
            b19_slope=b19,
            b15_depth=b15,
            worm_g200_z=worm_g200_z,
            svar_grav_jump_z=svar_grav_jump_z,
            footprint=fp,
        )
        del b12, b19, b15, worm_g200_z, svar_grav_jump_z
        for k_name, arr_v in zip(SVHF19_TOPO_NAMES, topo_list):
            _put(k_name, arr_v)
        del topo_list

    assert written == set(SVHF19_FEATURE_NAMES), f"Missing features: {set(SVHF19_FEATURE_NAMES) - written}"
    mm.flush()
    del mm
    gc.collect()

    max_b12_b19_diff = verify_pure_subsurface_b12_b19_invariance(features_tif, gdr_csv)
    meta = {
        "version": SVHF19_VERSION,
        "feature_names": list(SVHF19_FEATURE_NAMES),
        "total_features": len(SVHF19_FEATURE_NAMES),
        "pure_subsurface_features": len(SVHF19_SUBSURFACE_NAMES),
        "topo_features": len(SVHF19_TOPO_NAMES),
        "sanitized_footprint_cells_by_band": sanitized_counts,
        "gdr_stats": gdr_stats,
        "verified_subsurface_b12_b19_max_diff": max_b12_b19_diff,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")

    mm_ro = np.memmap(mmap_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(SVHF19_FEATURE_NAMES), meta


def rank_logit_standardize_domain(
    prob_2d: np.ndarray,
    domain_mask: np.ndarray,
    *,
    p_base: float = 0.012,
    slope: float = 1.15,
) -> np.ndarray:
    """Map `prob_2d[domain_mask]` via empirical ranks onto a fixed reference probability curve.

    Guarantees `1.000x` marginal invariance across 1-quadrant, 2-quadrant, and 3-quadrant
    Stage-1 models before computing `QDAC` spatial auto-context (`IR-91-S17-01` fix).
    """
    out = np.zeros_like(prob_2d, dtype=np.float32)
    dom = np.asarray(domain_mask, dtype=bool)
    vals = np.asarray(prob_2d[dom], dtype=np.float32)
    n = vals.size
    if n == 0:
        return out
    order = np.argsort(vals, kind="mergesort")
    ranks = np.empty(n, dtype=np.float32)
    ranks[order] = (np.arange(n, dtype=np.float32) + 0.5) / float(n)
    u = np.clip(ranks, 1.0e-6, 1.0 - 1.0e-6)
    base_l = float(logit(p_base))
    std_p = expit(np.clip(base_l + float(slope) * (logit(u) - logit(0.88)), -14.0, 14.0)).astype(np.float32)
    out[dom] = std_p
    return out


def _steerable_7_features(std_prob_2d: np.ndarray, footprint: np.ndarray) -> list[np.ndarray]:
    """Stream 7 12-azimuth steerable axial, relay-bridge, and step-over saddle features (`< 350 MB` RAM)."""
    p = np.where(footprint, np.clip(std_prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    h, w = p.shape

    pad = 14
    pp = np.pad(p, pad, mode="constant", constant_values=0.0)
    p_blur2 = ndi.gaussian_filter(pp, sigma=1.6, mode="constant").astype(np.float32)
    del pp

    s_max = np.full((h, w), -1.0e9, dtype=np.float32)
    s_run = np.full((h, w), -1.0e9, dtype=np.float32)
    s_sum = np.zeros((h, w), dtype=np.float32)
    l_max = np.full((h, w), -1.0e9, dtype=np.float32)
    b_max = np.zeros((h, w), dtype=np.float32)
    sad_max = np.zeros((h, w), dtype=np.float32)

    center = p_blur2[pad : pad + h, pad : pad + w]
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
                p_blur2[pad + sy : pad + sy + h, pad + sx : pad + sx + w]
                + p_blur2[pad - sy : pad - sy + h, pad - sx : pad - sx + w]
            )
        better = s_acc > s_max
        s_run = np.where(better, s_max, np.maximum(s_run, s_acc))
        s_max = np.where(better, s_acc, s_max)
        s_sum += s_acc

        fwd_lobe = np.zeros((h, w), dtype=np.float32)
        bwd_lobe = np.zeros((h, w), dtype=np.float32)
        for step, wt in ((6, 0.40), (9, 0.38), (12, 0.22)):
            sy, sx = int(round(step * dy)), int(round(step * dx))
            fwd_lobe += np.float32(wt) * p_blur2[pad + sy : pad + sy + h, pad + sx : pad + sx + w]
            bwd_lobe += np.float32(wt) * p_blur2[pad - sy : pad - sy + h, pad - sx : pad - sx + w]
        np.maximum(l_max, 0.5 * (fwd_lobe + bwd_lobe) + 0.5 * s_acc, out=l_max)
        np.maximum(b_max, np.sqrt(np.maximum(fwd_lobe, 0.0) * np.maximum(bwd_lobe, 0.0)), out=b_max)
        del s_acc, fwd_lobe, bwd_lobe

        ay, ax = int(round(6 * dy + 4 * ny)), int(round(6 * dx + 4 * nx))
        by, bx = int(round(-6 * dy - 4 * ny)), int(round(-6 * dx - 4 * nx))
        cy, cx = int(round(6 * dy - 4 * ny)), int(round(6 * dx - 4 * nx))
        ey, ex = int(round(-6 * dy + 4 * ny)), int(round(-6 * dx + 4 * nx))
        right_step = np.sqrt(
            np.maximum(p_blur2[pad + ay : pad + ay + h, pad + ax : pad + ax + w], 0.0)
            * np.maximum(p_blur2[pad + by : pad + by + h, pad + bx : pad + bx + w], 0.0)
        )
        left_step = np.sqrt(
            np.maximum(p_blur2[pad + cy : pad + cy + h, pad + cx : pad + cx + w], 0.0)
            * np.maximum(p_blur2[pad + ey : pad + ey + h, pad + ex : pad + ex + w], 0.0)
        )
        np.maximum(sad_max, np.maximum(right_step, left_step), out=sad_max)
        del right_step, left_step

    del p_blur2
    s_mean = (s_sum / 12.0).astype(np.float32)
    del s_sum
    s_coh = ((s_max - s_mean) / (s_max + 1.0e-5)).astype(np.float32)
    del s_mean

    return [
        robust_z_clip(p, footprint),
        robust_z_clip(s_max, footprint),
        robust_z_clip(s_run, footprint),
        robust_z_clip(s_coh, footprint),
        robust_z_clip(l_max, footprint),
        robust_z_clip(b_max, footprint),
        robust_z_clip(sad_max, footprint),
    ]


def compute_qdac_autocontext_memmap(
    *,
    s1_full_2d: np.ndarray,
    s1_sub_2d: np.ndarray,
    quadrant_masks: Sequence[np.ndarray],
    footprint: np.ndarray,
    out_path: Path,
) -> np.memmap:
    """Compute `(n_fp, 14)` `float16` Quantile-Standardized Dual Auto-Context (`QDAC`) memmap."""
    n_fp = int(footprint.sum())
    n_cols = len(QDAC_FEATURE_NAMES)
    expected_bytes = n_fp * n_cols * 2
    if out_path.is_file() and out_path.stat().st_size == expected_bytes:
        return np.memmap(out_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols))

    std_full = np.zeros_like(s1_full_2d, dtype=np.float32)
    std_sub = np.zeros_like(s1_sub_2d, dtype=np.float32)
    for qm in quadrant_masks:
        dom = np.asarray(qm, dtype=bool) & footprint
        std_full[dom] = rank_logit_standardize_domain(s1_full_2d, dom)[dom]
        std_sub[dom] = rank_logit_standardize_domain(s1_sub_2d, dom)[dom]

    feats_f = _steerable_7_features(std_full, footprint)
    feats_s = _steerable_7_features(std_sub, footprint)
    all_14 = feats_f + feats_s

    out_path.parent.mkdir(parents=True, exist_ok=True)
    mm = np.memmap(out_path, dtype=np.float16, mode="w+", shape=(n_fp, n_cols))
    for j, arr2d in enumerate(all_14):
        mm[:, j] = np.clip(arr2d[footprint], -32.0, 32.0).astype(np.float16)
    mm.flush()
    del std_full, std_sub, feats_f, feats_s, all_14
    gc.collect()
    return np.memmap(out_path, dtype=np.float16, mode="r", shape=(n_fp, n_cols))


def calibrate_pu_reference_odds(
    raw_surf: np.ndarray,
    footprint: np.ndarray,
    *,
    pi_vis_train: float,
    pi_sample: float,
    c0_mult: float = 11.0,
) -> np.ndarray:
    """Exact training-domain Bayes PU reference-odds calibration (`[0, 1]`, zero test peeking)."""
    eps = 1.0e-6
    p = np.clip(np.asarray(raw_surf[footprint], dtype=np.float64), eps, 1.0 - eps)
    pi_target = min(max(float(pi_vis_train) * float(c0_mult), 1.0e-4), 0.35)
    pi_s = min(max(float(pi_sample), 1.0e-4), 0.85)
    shift = math.log((pi_target / (1.0 - pi_target)) / (pi_s / (1.0 - pi_s)))
    cal = expit(np.clip(logit(p) + shift, -16.0, 16.0)).astype(np.float32)
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(cal, 0.0, 1.0)
    return out


def fit_predict_svhf_specialist(
    *,
    blocks: Sequence[tuple[np.ndarray, Sequence[int]]],
    hard_neg_cols_in_stack: Sequence[int],
    visible_faults: np.ndarray,
    train_domain: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    predict_mask: np.ndarray | None = None,
    neg_pos_ratio: float = 6.0,
    hard_neg_frac: float = 0.45,
    safe_neg_collar_px: float = 10.0,
    chunk_size: int = 400_000,
) -> tuple[np.ndarray, dict[str, object]]:
    """Fit heterogeneous PU ensemble (HGB-deep + HGB-reg + ExtraTrees + Calibrated-LR) and predict cleanly."""
    rng = np.random.default_rng(seed)
    dom = np.asarray(train_domain, dtype=bool) & footprint
    vis = np.asarray(visible_faults, dtype=bool) & dom
    safe_neg = dom & (~vis) & (ndi.distance_transform_edt(~vis) > float(safe_neg_collar_px))

    pos_idx = np.flatnonzero(vis[footprint])
    neg_pool = np.flatnonzero(safe_neg[footprint])
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Empty positive or safe-negative training pool")

    target_neg = min(int(round(float(neg_pos_ratio) * pos_idx.size)), neg_pool.size)
    active_blocks = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]

    if target_neg < neg_pool.size and len(hard_neg_cols_in_stack) > 0:
        n_hard = int(round(float(hard_neg_frac) * target_neg))
        n_easy = target_neg - n_hard
        hard_mask = np.zeros(neg_pool.size, dtype=bool)
        hard_set = set(int(c) for c in hard_neg_cols_in_stack)
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
                np.concatenate(
                    [
                        rng.choice(h_pool, size=n_hard, replace=False),
                        rng.choice(e_pool, size=n_easy, replace=False),
                    ]
                )
            )
        else:
            neg_idx = np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
    elif target_neg < neg_pool.size:
        neg_idx = np.sort(rng.choice(neg_pool, size=target_neg, replace=False))
    else:
        neg_idx = neg_pool

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate(
        [np.ones(pos_idx.size, dtype=np.int32), np.zeros(neg_idx.size, dtype=np.int32)]
    )
    X_train = np.hstack(
        [np.asarray(arr[train_idx][:, cols], dtype=np.float32) for arr, cols in active_blocks]
    )
    n_features = int(X_train.shape[1])

    hgb1 = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=165,
        max_leaf_nodes=35,
        min_samples_leaf=80,
        l2_regularization=4.0,
        early_stopping=False,
        random_state=seed,
    ).fit(X_train, y_train)

    hgb2 = HistGradientBoostingClassifier(
        learning_rate=0.048,
        max_iter=140,
        max_leaf_nodes=21,
        max_depth=6,
        min_samples_leaf=120,
        l2_regularization=7.5,
        early_stopping=False,
        random_state=seed + 17,
    ).fit(X_train, y_train)

    et = ExtraTreesClassifier(
        n_estimators=64,
        max_depth=13,
        min_samples_leaf=40,
        max_features="sqrt",
        n_jobs=2,
        random_state=seed + 31,
    ).fit(X_train, y_train)

    scaler = StandardScaler()
    X_sc = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.18, max_iter=300, random_state=seed + 53).fit(X_sc, y_train)

    del X_train, X_sc, y_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.zeros(n_fp, dtype=np.float32)
    if predict_mask is None:
        eval_rows = np.arange(n_fp, dtype=np.int64)
    else:
        eval_rows = np.flatnonzero(np.asarray(predict_mask, dtype=bool)[footprint])

    for start in range(0, eval_rows.size, chunk_size):
        rows_c = eval_rows[start : start + chunk_size]
        Xc = np.hstack(
            [np.asarray(arr[rows_c][:, cols], dtype=np.float32) for arr, cols in active_blocks]
        )
        p1 = hgb1.predict_proba(Xc)[:, 1]
        p2 = hgb2.predict_proba(Xc)[:, 1]
        p3 = et.predict_proba(Xc)[:, 1]
        p4 = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
        pred_fp[rows_c] = (0.42 * p1 + 0.26 * p2 + 0.20 * p3 + 0.12 * p4).astype(np.float32)
        del Xc, p1, p2, p3, p4

    raw_surf = np.zeros(footprint.shape, dtype=np.float32)
    raw_surf[footprint] = pred_fp
    pi_vis = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_samp = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    cal = calibrate_pu_reference_odds(
        raw_surf,
        footprint,
        pi_vis_train=pi_vis,
        pi_sample=pi_samp,
    )
    if predict_mask is not None:
        cal = np.where(predict_mask & footprint, cal, 0.0).astype(np.float32)

    del raw_surf, pred_fp, hgb1, hgb2, et, lr
    gc.collect()
    return cal, {
        "n_pos_train": int(pos_idx.size),
        "n_safe_neg_domain": int(neg_pool.size),
        "n_neg_sample": int(neg_idx.size),
        "pi_vis_train": round(pi_vis, 8),
        "pi_sample": round(pi_samp, 8),
        "n_features": n_features,
    }


def fuse_stage1_dual(
    s1_full: np.ndarray,
    s1_sub: np.ndarray,
    footprint: np.ndarray,
    *,
    w_sub: float = 0.36,
) -> np.ndarray:
    """`E1` Stage-1 Dual-Specialist log-odds + arithmetic hybrid blend in `[0, 1]`."""
    eps = 1.0e-5
    pf = np.clip(s1_full[footprint], eps, 1.0 - eps)
    ps = np.clip(s1_sub[footprint], eps, 1.0 - eps)
    p_geom = expit((1.0 - w_sub) * logit(pf) + w_sub * logit(ps))
    p_arith = (1.0 - w_sub) * pf + w_sub * ps
    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(0.55 * p_geom + 0.45 * p_arith, 0.0, 1.0).astype(np.float32)
    return out


def fuse_stage2_qdac(
    *,
    s1_full: np.ndarray,
    s1_sub: np.ndarray,
    s2_full: np.ndarray,
    s2_sub: np.ndarray,
    s2_topo: np.ndarray,
    footprint: np.ndarray,
    cover_ness_fp: np.ndarray | None = None,
    crest_bonus_fp: np.ndarray | None = None,
) -> np.ndarray:
    """Fuse Stage-1 + Stage-2 Full, Pure-Subsurface, and 14-col Topology specialists (`E2` & `E3`)."""
    eps = 1.0e-5
    lf = 0.28 * logit(np.clip(s1_full[footprint], eps, 1.0 - eps)) + 0.72 * logit(
        np.clip(s2_full[footprint], eps, 1.0 - eps)
    )
    ls = 0.26 * logit(np.clip(s1_sub[footprint], eps, 1.0 - eps)) + 0.74 * logit(
        np.clip(s2_sub[footprint], eps, 1.0 - eps)
    )
    lt = logit(np.clip(s2_topo[footprint], eps, 1.0 - eps))

    p_full_branch = expit(np.clip(0.82 * lf + 0.18 * lt, -16.0, 16.0))
    p_sub_branch = expit(np.clip(0.84 * ls + 0.16 * lt, -16.0, 16.0))

    if cover_ness_fp is None:
        # E2: fixed uniform specialist weight
        w_sub = np.float32(0.35)
    else:
        # E3: cover-adaptive specialist gate shifting up to 0.70 weight onto Pure-Subsurface in deep flat basins
        cov = np.clip(np.asarray(cover_ness_fp, dtype=np.float32), 0.0, 1.0)
        w_sub = (0.26 + 0.44 * cov).astype(np.float32)

    p_geom = expit(
        np.clip(
            (1.0 - w_sub) * logit(np.clip(p_full_branch, eps, 1.0 - eps))
            + w_sub * logit(np.clip(p_sub_branch, eps, 1.0 - eps)),
            -16.0,
            16.0,
        )
    )
    p_arith = (1.0 - w_sub) * p_full_branch + w_sub * p_sub_branch
    p_blend = (0.55 * p_geom + 0.45 * p_arith).astype(np.float32)

    if crest_bonus_fp is not None:
        crest = np.clip(np.asarray(crest_bonus_fp, dtype=np.float32), 0.0, 1.0)
        p_blend = expit(
            np.clip(logit(np.clip(p_blend, eps, 1.0 - eps)) + 0.24 * (crest - 0.35), -16.0, 16.0)
        ).astype(np.float32)

    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(p_blend, 0.0, 1.0)
    return out


def emit_clean_celf_submodular_dots(
    surface: np.ndarray,
    visible_catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.10,
    gamma: float = 1.15,
    pool_multiplier: int = 10,
) -> np.ndarray:
    """Strictly label-blind global-footprint clean 300-m CELF submodular emitter.

    Fixes both `cpad17.py` submodular bugs:
      1. Sets `weight = 0.0` everywhere inside `d_vis <= collar_px` (`elig` mask), so
         dots at `d_vis = 3.06 px` receive zero artificial bonus from covering the
         `1..3 px` collar of already-known faults.
      2. Preserves full smooth `2–3 px` fault-zone probability mass without off-crest
         `0.36` slashing, using gentle local-maximum preference only for candidate ordering.
    """
    h, w = surface.shape
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_catalogue, dtype=bool) & fp
    elig = fp & (~vis) & (ndi.distance_transform_edt(~vis) > float(collar_px))

    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    elig_vals = p[elig & (p > 0.0)]
    if elig_vals.size == 0 or budget <= 0:
        return np.zeros((h, w), dtype=np.float32)

    if elig_vals.size > budget * 16:
        keep_frac = min(0.32, max(float(budget * 16) / float(elig_vals.size), 0.06))
        p_floor = float(np.quantile(elig_vals, 1.0 - keep_frac))
    else:
        p_floor = 0.0

    p_excess = np.maximum(p - p_floor, 0.0)
    weight = np.where(elig, 1000.0 * np.power(p_excess, float(gamma)), 0.0).astype(np.float32)

    pp = np.pad(p, 1, mode="edge")
    c = pp[1 : h + 1, 1 : w + 1]
    local_crest = (
        ((c >= pp[0:h, 1 : w + 1]) & (c >= pp[2 : h + 2, 1 : w + 1]))
        | ((c >= pp[1 : h + 1, 0:w]) & (c >= pp[1 : h + 1, 2 : w + 2]))
        | ((c >= pp[0:h, 0:w]) & (c >= pp[2 : h + 2, 2 : w + 2]))
        | ((c >= pp[0:h, 2 : w + 2]) & (c >= pp[2 : h + 2, 0:w]))
    )
    cand_rank = np.where(elig, p * np.where(local_crest, 1.04, 0.97), 0.0).astype(np.float32)

    return MC._submodular_select_on_weight(
        weight,
        cand_rank,
        elig,
        int(budget),
        min_spacing_px=float(min_spacing_px),
        pool_multiplier=int(pool_multiplier),
        existing_dots=None,
    )
