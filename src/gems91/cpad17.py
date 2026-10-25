"""Session 17 (`S17-CPAD`): Cover-Adaptive Potential-Phase, Accommodation-Saddle &
Hydrothermal-Disequilibrium Dual-Specialist for Blind Geothermal Fault Mapping.

Implements preregistered hypothesis `H17-1` (`docs/HYPOTHESES_S17.md`) while fixing
all four structural failure modes audited across Sessions 13–16:
  1. `IR-91-S17-01`: Strictly label-blind global-footprint dot placement conditioned
     ONLY on `(surface, visible_catalogue, footprint)` — zero access to `region`,
     `truth`, `held_all`, or `buffer`.
  2. `IR-91-S15-05`: Programmatically verified `STRICT_TOPO_FEATURE_NAMES` so both
     Stage-1 and Stage-2 Pure-Subsurface Specialists have bitwise `0.0` dependence
     on `Band 12` (`det_elev`) and `Band 19` (`det_elev_slope`) — in features,
     structure tensors, deconfounding residuals, and hard-negative mining.
  3. `IR-91-S15-06`: Exact training-domain Bayes reference-odds calibration
     (`c0 = 12.0`) applied identically across 2-quadrant pairwise sub-models,
     3-quadrant OOF models, and 4-quadrant full models BEFORE computing `spac_coda`
     axial structural auto-context, cancelling sample-prevalence drift algebraically
     while preserving full dynamic range across histogram bins.
  4. `IR-91-S15-07`: Exclusively local (`<= 1.2 km`) translation-invariant geophysical
     and chemical-geothermometer operators (`0` regional coordinate bowls).
"""

from __future__ import annotations

import csv
import gc
import heapq
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import dd_vtc_pu as DD
from . import hvdc as HVDC
from . import mhtr_coda as MC
from . import ptha as PTHA
from . import spac_coda as SC

CPAD_CACHE_VERSION = "s17_cpad_features_v1"

# 16 novel Session 17 blind-geothermal & structural-accommodation features.
# Cols 0..13 (14 features) are strictly Band-12 / Band-19 free.
# Cols 14..15 (2 features) explicitly incorporate cover/playa geometry and belong
# to STRICT_TOPO_FEATURE_NAMES (excluded from the Pure-Subsurface Specialist).
CPAD_FEATURE_NAMES: list[str] = [
    # Group A: Cooper-Cowan (2006) Normalized Potential-Field Edge Phase & Poisson Demagnetization (5)
    "cpad_cooper_theta_grav",
    "cpad_cooper_theta_rtp",
    "cpad_theta_phase_concordance",
    "cpad_poisson_demag_deficit",
    "cpad_grav_second_deriv_zero_crest",
    # Group B: Faulds & Hinz (2015) Accommodation Saddles, Inflections & Riedel Transtension (6)
    "cpad_grav_accommodation_saddle",
    "cpad_basement_accommodation_saddle",
    "cpad_basement_inflection_worm",
    "cpad_riedel_synthetic_dilation",
    "cpad_conjugate_intersection_mesh",
    "cpad_seismic_aseismic_transition",
    # Group C: Sibson (1996) Chemical Geothermometer Disequilibrium & Deconfounded Clay-Cap Baffles (5)
    "cpad_geotherm_disequilibrium_local",
    "cpad_diseq_strike_conduit",
    "cpad_claycap_subsurface_baffle",
    "cpad_claycap_playa_baffle",
    "cpad_cover_concealment_prior",
]

# Translation-invariant local subsets of cached repo feature tables (excluding >= 2.5 km bowls/halos).
STATIC_LOCAL_COLS: list[int] = list(range(34)) + [44, 45, 46, 47, 48]  # 39 cols
S11_LOCAL_COLS: list[int] = list(range(len(MC.S11_MHTR_FEATURE_NAMES)))  # 16 cols
S12_LOCAL_COLS: list[int] = list(range(len(SC.S12_SPAC_STATIC_FEATURE_NAMES)))  # 20 cols
PTHA_LOCAL_COLS: list[int] = list(range(len(PTHA.PTHA_FEATURE_NAMES)))  # 20 cols
HVDC_LOCAL_COLS: list[int] = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]  # 17 cols
CPAD_LOCAL_COLS: list[int] = list(range(len(CPAD_FEATURE_NAMES)))  # 16 cols

# Complete, line-by-line audited set of ALL features across every module that depend directly
# or indirectly on Band 12 (`det_elev`) or Band 19 (`det_elev_slope`).
STRICT_TOPO_FEATURE_NAMES: frozenset[str] = frozenset(
    {
        # dd_vtc_pu (X_static)
        "b12_det_elev",
        "b19_det_elev_slope",
        "e1_lrm_300m",
        "e1_lrm_1km",
        "e1_topo_openness_lap",
        "e1_slope_hp_600m",
        "e1_topo_coherence",
        "e2_axial_ridge_max",
        "e2_axial_ridge_anisotropy",
        "e2_anderson_slip_dilation",
        "e2_multiphysics_coincidence",
        "e2_gdr_upslope_conduit_align",
        "e2_piedmont_concealment_idx",
        # mhtr_coda (X_s11)
        "s11_topo_grav_cos_align",
        "s11_topo_profile_curv",
        "s11_ctx1km_topo_slope",
        # spac_coda (X_s12)
        "s12_frangi_topo_s1p5",
        "s12_frangi_topo_s4p0",
        "s12_crossfault_dipole_600m",
        # ptha (X_ptha: structure tensor mixed sobel(b12_elev) in cols 5..11)
        "ptha_multiphys_strike_coh",
        "ptha_step_elev_abs",
        "ptha_step_grav_abs",
        "ptha_step_rtp_abs",
        "ptha_step_depth_abs",
        "ptha_step_rad_tc_abs",
        "ptha_step_normal_concordance",
        # hvdc (X_hvdc: upslope head, playa_penalty, DEM-mixed strike tensor, frangi_topo)
        "hvdc_upgrad_feeder_1p2km",
        "hvdc_upgrad_feeder_2p8km",
        "hvdc_feeder_step_coupling",
        "hvdc_hydro_mag_destruct_clay",
        "hvdc_cond_playa_res_grad",
        "hvdc_grav_res_step_600m",
        "hvdc_frangi_topo_multiscale",
        "hvdc_cond_playa_residual_fold",
        # cpad17 (X_cpad: only the 2 cover-conditioned features)
        "cpad_claycap_playa_baffle",
        "cpad_cover_concealment_prior",
    }
)

# Forbidden CSV columns that must never be read during GDR feature construction.
BANNED_GDR_COLUMNS: frozenset[str] = frozenset({"dist_known_fault_px"})


def _robust_z_pos(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    vals = arr[footprint][::8]
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826 + 1e-6
    z = np.clip((arr - med) / mad, 0.0, 8.0).astype(np.float32)
    z[~footprint] = 0.0
    return z


def _grad_components(arr: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sm = ndi.gaussian_filter(arr.astype(np.float32, copy=False), sigma=float(sigma))
    gy = (ndi.sobel(sm, axis=0) / 8.0).astype(np.float32)
    gx = (ndi.sobel(sm, axis=1) / 8.0).astype(np.float32)
    mag = np.hypot(gy, gx).astype(np.float32)
    return gy, gx, mag


def _hyperbolic_saddle_index(arr: np.ndarray, footprint: np.ndarray, sigma: float) -> np.ndarray:
    """Principal Hessian hyperbolic saddle index `max(0, -k1 * k2) / (k1^2 + k2^2 + eps)`.

    Strictly positive ONLY at structural saddles / relay ramps (`k1` and `k2` have opposite signs),
    vanishing on isotropic bowls, domes, and uniform planes.
    """
    f = arr.astype(np.float32, copy=False)
    s2 = float(sigma * sigma)
    hxx = (ndi.gaussian_filter(f, sigma=sigma, order=(0, 2)) * s2).astype(np.float32)
    hyy = (ndi.gaussian_filter(f, sigma=sigma, order=(2, 0)) * s2).astype(np.float32)
    hxy = (ndi.gaussian_filter(f, sigma=sigma, order=(1, 1)) * s2).astype(np.float32)
    det_h = hxx * hyy - hxy * hxy  # k1 * k2
    frob_sq = hxx * hxx + hyy * hyy + 2.0 * hxy * hxy  # k1^2 + k2^2
    scale_floor = float(np.percentile(frob_sq[footprint][::16], 50)) * 0.15 + 1e-8
    saddle = (np.maximum(-det_h, 0.0) / (frob_sq + scale_floor)).astype(np.float32)
    saddle[~footprint] = 0.0
    return saddle


def _inflection_worm_crest(arr: np.ndarray, footprint: np.ndarray, sigma: float) -> np.ndarray:
    """Gradient-normal second-derivative zero-crossing worm `||grad F|| * exp(-|d_nn F| / s_nn)`.

    Localizes the steepest subsurface fault-plane inflection rather than offset basin minima.
    """
    f = arr.astype(np.float32, copy=False)
    gy = ndi.gaussian_filter(f, sigma=sigma, order=(1, 0)).astype(np.float32)
    gx = ndi.gaussian_filter(f, sigma=sigma, order=(0, 1)).astype(np.float32)
    gmag = np.hypot(gy, gx).astype(np.float32)
    ny = gy / (gmag + 1e-6)
    nx = gx / (gmag + 1e-6)
    hyy = ndi.gaussian_filter(f, sigma=sigma, order=(2, 0)).astype(np.float32)
    hxx = ndi.gaussian_filter(f, sigma=sigma, order=(0, 2)).astype(np.float32)
    hxy = ndi.gaussian_filter(f, sigma=sigma, order=(1, 1)).astype(np.float32)
    d_nn = np.abs(ny * ny * hyy + 2.0 * ny * nx * hxy + nx * nx * hxx)
    s_nn = float(np.percentile(d_nn[footprint][::16], 60)) + 1e-6
    worm = (_robust_z_pos(gmag, footprint) * np.exp(-d_nn / s_nn)).astype(np.float32)
    worm[~footprint] = 0.0
    return worm


def _deconfound_2d_binned_residual_grad(
    target: np.ndarray,
    cov1: np.ndarray,
    cov2: np.ndarray,
    footprint: np.ndarray,
    *,
    n_bins: int = 12,
    grad_sigma: float = 1.4,
) -> np.ndarray:
    """Nonparametric 2-D quantile-binned median residual lateral gradient `||grad(target - med(target | cov1, cov2))||`.

    Removes smooth lithologic / basin-depth / playa background conductivity while sharpening
    fault-bounded lateral smectite clay-cap and aquifer-compartmentalization steps.
    """
    t_fp = target[footprint]
    c1_fp = cov1[footprint]
    c2_fp = cov2[footprint]
    q_edges = np.linspace(0.0, 100.0, n_bins + 1)
    e1 = np.unique(np.percentile(c1_fp[::8], q_edges))
    e2 = np.unique(np.percentile(c2_fp[::8], q_edges))
    b1 = np.clip(np.digitize(c1_fp, e1[1:-1]), 0, max(len(e1) - 2, 0))
    b2 = np.clip(np.digitize(c2_fp, e2[1:-1]), 0, max(len(e2) - 2, 0))
    nb2 = max(int(b2.max()) + 1, 1)
    cell_id = b1 * nb2 + b2
    n_cells = int(cell_id.max()) + 1

    global_med = float(np.median(t_fp[::8]))
    # Compute cell means/medians robustly via Winsorized cell mean around global median
    t_clip = np.clip(t_fp, np.percentile(t_fp[::8], 2), np.percentile(t_fp[::8], 98))
    counts = np.bincount(cell_id, minlength=n_cells).astype(np.float32)
    sums = np.bincount(cell_id, weights=t_clip, minlength=n_cells).astype(np.float32)
    expected_cell = np.where(counts >= 25.0, sums / np.maximum(counts, 1.0), global_med)

    res_grid = np.zeros(footprint.shape, dtype=np.float32)
    res_grid[footprint] = (t_fp - expected_cell[cell_id]).astype(np.float32)
    # Smooth cell-boundary discretization slightly before lateral gradient extraction
    _, _, grad = _grad_components(res_grid, sigma=grad_sigma)
    return _robust_z_pos(grad, footprint)


def extract_gdr_disequilibrium_impulses(
    gdr_csv: str | Path,
    shape: tuple[int, int],
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """Extract per-cell maximum chemical-vs-outflow thermal disequilibrium & enthalpy impulses.

    Strictly forbids reading `dist_known_fault_px` (`BANNED_GDR_COLUMNS`). Uses `np.maximum.at`
    so multi-sampled hot springs do not receive sample-count inflation over single-measurement
    blind thermal wells.
    """
    h, w = shape
    diseq_imp = np.zeros((h, w), dtype=np.float32)
    enth_imp = np.zeros((h, w), dtype=np.float32)

    allowed_cols = (
        "row",
        "col",
        "temp_c",
        "geothermquartz_c",
        "geothermchalc_c",
        "geothermcat_c",
        "thermalclass",
    )
    rows_read = 0
    cells_populated = 0

    def _parse_float(val: str | None) -> float:
        if val is None:
            return math.nan
        s = val.strip()
        if not s or s.upper() == "NULL":
            return math.nan
        try:
            v = float(s)
            return v if math.isfinite(v) else math.nan
        except ValueError:
            return math.nan

    with open(gdr_csv, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Empty GDR CSV: {gdr_csv}")
        # Project only allowed physical columns; never access `dist_known_fault_px`.
        for raw_row in reader:
            rec = {k: raw_row.get(k, "") for k in allowed_cols}
            assert not (set(rec.keys()) & BANNED_GDR_COLUMNS)
            rows_read += 1
            try:
                r = int(float(rec["row"]))
                c = int(float(rec["col"]))
            except (TypeError, ValueError):
                continue
            if not (0 <= r < h and 0 <= c < w) or not footprint[r, c]:
                continue

            t_meas = _parse_float(rec["temp_c"])
            t_qtz = _parse_float(rec["geothermquartz_c"])
            t_chl = _parse_float(rec["geothermchalc_c"])
            t_cat = _parse_float(rec["geothermcat_c"])
            chem_vals = [v for v in (t_qtz, t_chl, t_cat) if math.isfinite(v) and 20.0 <= v <= 360.0]
            t_chem = max(chem_vals) if chem_vals else math.nan

            t_outflow = t_meas if (math.isfinite(t_meas) and -5.0 <= t_meas <= 250.0) else 15.0
            if math.isfinite(t_chem):
                # Blind disequilibrium: high chemical equilibrium reservoir T above cooled shallow outflow
                delta_diseq = max(0.0, t_chem - max(t_outflow, 15.0))
                val_d = min(delta_diseq / 120.0, 2.5)
                if val_d > diseq_imp[r, c]:
                    diseq_imp[r, c] = np.float32(val_d)

            t_cls = (rec["thermalclass"] or "").strip().lower()
            cls_bonus = 0.65 if t_cls == "hot" else (0.35 if t_cls == "warm" else 0.0)
            meas_excess = max(0.0, t_outflow - 20.0) / 70.0 if math.isfinite(t_meas) else 0.0
            chem_excess = max(0.0, (t_chem - 75.0) / 130.0) if math.isfinite(t_chem) else 0.0
            val_e = min(max(meas_excess, 0.80 * chem_excess) + cls_bonus, 2.5)
            if val_e > enth_imp[r, c]:
                enth_imp[r, c] = np.float32(val_e)

    cells_populated = int(((diseq_imp > 0) | (enth_imp > 0)).sum())
    return diseq_imp, enth_imp, {
        "rows_read": rows_read,
        "cells_populated": cells_populated,
        "banned_columns_excluded": sorted(BANNED_GDR_COLUMNS),
    }


def compute_cpad_arrays_from_bands(
    bands: dict[int, np.ndarray],
    footprint: np.ndarray,
    *,
    gdr_csv: str | Path,
) -> tuple[np.ndarray, dict]:
    """Compute all 16 `CPAD` features `(N_fp, 16)` from cleaned 1-indexed bands + GDR CSV.

    Exposed directly so unit tests can perturb `bands[12]` and `bands[19]` in memory and
    verify bitwise `0.0` change across columns `0..13`.
    """
    h, w = footprint.shape
    n_fp = int(footprint.sum())
    out = np.empty((n_fp, len(CPAD_FEATURE_NAMES)), dtype=np.float32)

    b02 = bands[2].astype(np.float32, copy=False)
    b03_si = (np.maximum(bands[3], 0.0) / 200.0).astype(np.float32)
    b04 = np.maximum(bands[4], 0.0).astype(np.float32)
    b06 = bands[6].astype(np.float32, copy=False)
    b07 = np.maximum(bands[7], 0.0).astype(np.float32)
    b08 = bands[8].astype(np.float32, copy=False)
    b09 = bands[9].astype(np.float32, copy=False)
    b10 = np.maximum(bands[10], 0.0).astype(np.float32)
    b11 = bands[11].astype(np.float32, copy=False)
    b12 = bands[12].astype(np.float32, copy=False)
    b13 = bands[13].astype(np.float32, copy=False)
    b15 = np.maximum(bands[15], 0.0).astype(np.float32)
    b16 = np.maximum(bands[16], 0.0).astype(np.float32)
    b17 = bands[17].astype(np.float32, copy=False)
    b18 = np.maximum(bands[18], 0.0).astype(np.float32)
    b19 = np.maximum(bands[19], 0.0).astype(np.float32)

    # --- Group A: Cooper-Cowan Normalized Potential Phase & Poisson Demagnetization ---
    gy_g, gx_g, hg_loc = _grad_components(b13, sigma=1.5)
    hg_mix = (0.65 * hg_loc + 0.35 * b18 * float(np.median(hg_loc[footprint][::16]) / (np.median(b18[footprint][::16]) + 1e-6))).astype(np.float32)
    vg_scale = float(np.std(hg_mix[footprint][::16]) / (np.std(b11[footprint][::16]) + 1e-6))
    amp_g_rms = np.sqrt(ndi.gaussian_filter(hg_mix * hg_mix + (b11 * vg_scale) ** 2, sigma=8.0) + 1e-10).astype(np.float32)
    cos_theta_g = (hg_mix / (hg_mix + 0.38 * amp_g_rms + 1e-6)).astype(np.float32)
    cos_theta_g[~footprint] = 0.0

    gy_m, gx_m, hm_rtp = _grad_components(b02, sigma=1.5)
    hm_mix = (0.60 * hm_rtp + 0.40 * b03_si * float(np.median(hm_rtp[footprint][::16]) / (np.median(b03_si[footprint][::16]) + 1e-6))).astype(np.float32)
    vm_scale = float(np.std(hm_mix[footprint][::16]) / (np.std(b09[footprint][::16]) + 1e-6))
    amp_m_rms = np.sqrt(ndi.gaussian_filter(hm_mix * hm_mix + (b09 * vm_scale) ** 2, sigma=8.0) + 1e-10).astype(np.float32)
    cos_theta_m = (hm_mix / (hm_mix + 0.38 * amp_m_rms + 1e-6)).astype(np.float32)
    cos_theta_m[~footprint] = 0.0

    dot_gm = np.abs(gy_g * gy_m + gx_g * gx_m) / (hg_loc * hm_rtp + 1e-6)
    theta_concord = (np.sqrt(np.maximum(cos_theta_g * cos_theta_m, 0.0)) * dot_gm).astype(np.float32)
    theta_concord[~footprint] = 0.0

    # Hydrothermal magnetite destruction: strong gravity phase inside magnetic country rock
    # where local magnetic edge phase drops sharply relative to 600 m surroundings.
    mag_bg_600m = ndi.gaussian_filter(cos_theta_m, sigma=6.0).astype(np.float32)
    demag_trough = np.maximum(mag_bg_600m - cos_theta_m, 0.0)
    poisson_demag = (cos_theta_g * demag_trough * (0.5 + 0.5 * mag_bg_600m)).astype(np.float32)
    poisson_demag[~footprint] = 0.0

    grav_worm = _inflection_worm_crest(b13, footprint, sigma=2.0)

    out[:, 0] = cos_theta_g[footprint]
    out[:, 1] = cos_theta_m[footprint]
    out[:, 2] = theta_concord[footprint]
    out[:, 3] = _robust_z_pos(poisson_demag, footprint)[footprint]
    out[:, 4] = grav_worm[footprint]
    del amp_g_rms, amp_m_rms, dot_gm, theta_concord, mag_bg_600m, demag_trough, poisson_demag, grav_worm

    # --- Pure Subsurface Structure Tensor (100% Band 12 / Band 19 invariant!) ---
    sg = float(np.median(hg_loc[footprint][::16])) + 1e-6
    sm = float(np.median(hm_rtp[footprint][::16])) + 1e-6
    jyy = ndi.gaussian_filter((gy_g / sg) ** 2 + (gy_m / sm) ** 2, sigma=3.0).astype(np.float32)
    jxx = ndi.gaussian_filter((gx_g / sg) ** 2 + (gx_m / sm) ** 2, sigma=3.0).astype(np.float32)
    jxy = ndi.gaussian_filter((gy_g * gx_g) / (sg * sg) + (gy_m * gx_m) / (sm * sm), sigma=3.0).astype(np.float32)
    # Normal direction phi_n (in row-south y, col-east x coordinates); strike vector s = (-ny, nx)
    phi_n = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    nx_sub = np.cos(phi_n).astype(np.float32)
    ny_sub = np.sin(phi_n).astype(np.float32)
    sx_sub = (-ny_sub).astype(np.float32)  # strike east component
    sy_sub = nx_sub.astype(np.float32)     # strike south component (-north)
    del gy_g, gx_g, hg_loc, gy_m, gx_m, hm_rtp, jyy, jxx, jxy, phi_n

    # --- Group B: Faulds & Hinz Accommodation Saddles, Inflections & Riedel Transtension ---
    grav_saddle = _hyperbolic_saddle_index(b13, footprint, sigma=3.0)
    db_log = np.log1p(b15).astype(np.float32)
    base_sad_3p5 = _hyperbolic_saddle_index(db_log, footprint, sigma=3.5)
    base_sad_6p0 = _hyperbolic_saddle_index(db_log, footprint, sigma=6.0)
    base_saddle = np.sqrt(np.maximum(base_sad_3p5 * base_sad_6p0, 0.0)).astype(np.float32)
    base_worm = (
        0.55 * _inflection_worm_crest(db_log, footprint, sigma=2.0)
        + 0.45 * _inflection_worm_crest(db_log, footprint, sigma=4.5)
    ).astype(np.float32)
    del base_sad_3p5, base_sad_6p0, db_log

    # Strike azimuth E of N: north = -sy_sub, east = sx_sub => az = atan2(sx_sub, -sy_sub)
    strike_az_rad = np.arctan2(sx_sub, -sy_sub).astype(np.float32)
    # Great Basin WNW extension (~105 deg E of N):
    #   - Optimal pure normal dilation strike: 15 deg E of N (N15E)
    #   - Optimal Walker Lane dextral synthetic Riedel strike: 330 deg (-30 deg, N30W)
    align_nne_norm = np.cos(strike_az_rad - math.radians(15.0)) ** 2
    align_nw_riedel = np.cos(strike_az_rad - math.radians(-30.0)) ** 2
    dil_pos = np.maximum(b08, 0.0)
    riedel_dilation = (
        (align_nne_norm * _robust_z_pos(dil_pos, footprint) + align_nw_riedel * _robust_z_pos(b07, footprint))
        * (0.35 + 0.65 * cos_theta_g)
    ).astype(np.float32)
    riedel_dilation[~footprint] = 0.0

    # Conjugate fault intersection mesh: simultaneous NNE-striking AND WNW/ENE-striking potential edges
    pot_joint = (0.55 * cos_theta_g + 0.45 * cos_theta_m).astype(np.float32)
    nne_field = ndi.gaussian_filter(pot_joint * align_nne_norm, sigma=3.5).astype(np.float32)
    wnw_align = np.cos(strike_az_rad - math.radians(75.0)) ** 2 + 0.5 * align_nw_riedel
    wnw_field = ndi.gaussian_filter(pot_joint * np.clip(wnw_align, 0.0, 1.0), sigma=3.5).astype(np.float32)
    conj_mesh = (np.sqrt(np.maximum(nne_field * wnw_field, 0.0)) * np.log1p(b04)).astype(np.float32)
    conj_mesh[~footprint] = 0.0
    del strike_az_rad, align_nne_norm, align_nw_riedel, dil_pos, pot_joint, nne_field, wnw_align, wnw_field

    # Microseismic swarm-boundary / locked-to-creeping permeability gradient
    seis_comp = np.log1p(0.65 * b10 + 0.35 * b16).astype(np.float32)
    _, _, seis_grad = _grad_components(seis_comp, sigma=4.0)
    seis_transition = (_robust_z_pos(seis_grad, footprint) * np.log1p(b04 + 0.5 * b07)).astype(np.float32)
    seis_transition[~footprint] = 0.0
    del seis_comp, seis_grad

    out[:, 5] = grav_saddle[footprint]
    out[:, 6] = base_saddle[footprint]
    out[:, 7] = base_worm[footprint]
    out[:, 8] = riedel_dilation[footprint]
    out[:, 9] = _robust_z_pos(conj_mesh, footprint)[footprint]
    out[:, 10] = seis_transition[footprint]
    del grav_saddle, base_saddle, base_worm, riedel_dilation, conj_mesh, seis_transition, cos_theta_m
    gc.collect()

    # --- Group C: Chemical Geothermometer Disequilibrium & Deconfounded Clay-Cap Baffles ---
    diseq_imp, enth_imp, gdr_stats = extract_gdr_disequilibrium_impulses(gdr_csv, (h, w), footprint)
    # Strictly local (< 1.2 km: sigma = 5.5 px = 550 m and sigma = 11.0 px = 1.1 km)
    diseq_local = (
        26.0 * ndi.gaussian_filter(diseq_imp, sigma=5.5)
        + 10.0 * ndi.gaussian_filter(diseq_imp, sigma=11.0)
    ).astype(np.float32)
    diseq_local[~footprint] = 0.0

    plume_joint = (
        diseq_local
        + 14.0 * ndi.gaussian_filter(enth_imp, sigma=6.0)
    ).astype(np.float32)
    del diseq_imp, enth_imp

    # Strike-anisotropic blind conduit projection strictly along subsurface strike (sy_sub, sx_sub)
    yy, xx = np.indices((h, w), dtype=np.float32)
    strike_conduit = plume_joint.copy()
    for dist_px, wt in ((4.0, 0.35), (8.0, 0.28), (12.0, 0.18)):
        for sign in (-1.0, 1.0):
            cy = np.clip(yy + sign * dist_px * sy_sub, 0.0, h - 1.0)
            cx = np.clip(xx + sign * dist_px * sx_sub, 0.0, w - 1.0)
            strike_conduit = np.maximum(
                strike_conduit,
                wt * ndi.map_coordinates(plume_joint, [cy, cx], order=1, mode="nearest"),
            )
    diseq_conduit = (strike_conduit * (0.30 + 0.70 * cos_theta_g)).astype(np.float32)
    diseq_conduit[~footprint] = 0.0
    del yy, xx, sy_sub, sx_sub, nx_sub, ny_sub, plume_joint, strike_conduit, cos_theta_g

    # Col 13 (DEM-free!): Band 17 conductivity lateral step deconfounded for (Band 15 depth, Band 06 radiometrics)
    clay_sub_baffle = _deconfound_2d_binned_residual_grad(
        b17, np.log1p(b15), b06, footprint, n_bins=12, grad_sigma=1.4
    )
    # Col 14 (Cover-conditioned -> STRICT_TOPO_FEATURE_NAMES): Band 17 lateral step deconfounded for (Band 12 elev, Band 15 depth)
    clay_playa_baffle = _deconfound_2d_binned_residual_grad(
        b17, b12, np.log1p(b15), footprint, n_bins=12, grad_sigma=1.4
    )
    # Col 15 (Cover-conditioned -> STRICT_TOPO_FEATURE_NAMES): Smooth Concealed-Basin / Piedmont Cover Prior in [0, 1]
    slp_reg = ndi.gaussian_filter(b19, sigma=7.0).astype(np.float32)
    cover_prior = (
        np.exp(-slp_reg / 3.2) * (1.0 - 0.55 * np.exp(-b15 / 140.0))
    ).astype(np.float32)
    cover_prior = np.clip(cover_prior, 0.0, 1.0)
    cover_prior[~footprint] = 0.0

    out[:, 11] = _robust_z_pos(diseq_local, footprint)[footprint]
    out[:, 12] = _robust_z_pos(diseq_conduit, footprint)[footprint]
    out[:, 13] = clay_sub_baffle[footprint]
    out[:, 14] = clay_playa_baffle[footprint]
    out[:, 15] = cover_prior[footprint]

    if not np.isfinite(out).all():
        raise RuntimeError("Non-finite values encountered in CPAD feature matrix")

    return out, {
        "version": CPAD_CACHE_VERSION,
        "n_fp": n_fp,
        "n_cols": len(CPAD_FEATURE_NAMES),
        "feature_names": list(CPAD_FEATURE_NAMES),
        "dem_free_cols": list(range(14)),
        "topo_conditioned_cols": [14, 15],
        "gdr_stats": gdr_stats,
    }


def build_or_load_cpad_feature_memmap(
    *,
    features_tif: str | Path,
    gdr_csv: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open disk-backed float32 `(N_fp, 16)` `CPAD` feature table."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / f"{CPAD_CACHE_VERSION}.dat"
    meta_path = cache_p / f"{CPAD_CACHE_VERSION}.json"

    n_fp = int(footprint.sum())
    n_cols = len(CPAD_FEATURE_NAMES)
    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("version") == CPAD_CACHE_VERSION
            and meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == CPAD_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(CPAD_FEATURE_NAMES), meta

    needed = (2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19)
    bands: dict[int, np.ndarray] = {}
    with rasterio.open(features_tif) as src:
        for b in needed:
            bands[b] = DD._clean_band_edt(src.read(b), footprint)

    arr, meta = compute_cpad_arrays_from_bands(bands, footprint, gdr_csv=gdr_csv)
    del bands
    gc.collect()

    mm_w = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    mm_w[:] = arr
    mm_w.flush()
    del mm_w, arr
    gc.collect()

    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(CPAD_FEATURE_NAMES), meta


def calibrate_reference_odds_surface(
    prob_surface: np.ndarray,
    footprint: np.ndarray,
    *,
    pi_vis_train: float,
    pi_sample_weighted: float,
    c0_multiplier: float = 12.0,
) -> np.ndarray:
    """Exact training-domain Bayes reference-odds calibration (`IR-91-S15-06` fix).

    Maps raw subsampled posterior `p_raw` (`P(Y=1 | X, sampled)`) to a split-invariant
    reference odds scale `pi_ref = min(0.45, c0_multiplier * pi_vis_train)` using ONLY
    training-domain quantities `(pi_vis_train, pi_sample_weighted)`.

    Cancels `pi_sample_weighted` algebraically across 2-quadrant pairwise splits,
    3-quadrant OOF splits, and 4-quadrant full splits while keeping values near `~0.13`
    so `spac_coda` variance normalization (`+ 1e-4` floor) and 255-bin HGB splits retain
    full dynamic resolution.
    """
    pi_ref = min(0.45, max(1e-4, float(c0_multiplier) * float(pi_vis_train)))
    pi_s = min(0.999, max(1e-5, float(pi_sample_weighted)))
    odds_mult = np.float32((pi_ref / (1.0 - pi_ref)) / (pi_s / (1.0 - pi_s)))
    p = np.clip(np.asarray(prob_surface, dtype=np.float32), 1e-6, 1.0 - 1e-6)
    num = odds_mult * p
    cal = (num / (num + (1.0 - p))).astype(np.float32)
    cal[~footprint] = 0.0
    return np.clip(cal, 0.0, 1.0)


def fit_predict_specialist(
    *,
    blocks: Sequence[tuple[np.ndarray, Sequence[int]]],
    hard_neg_cols_in_stack: Sequence[int],
    visible_faults: np.ndarray,
    train_domain: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    neg_pos_ratio: float = 3.65,
    hard_neg_frac: float = 0.35,
    chunk_size: int = 600_000,
    predict_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Fit a regularized HGB-deep + HGB-shallow + L2-Logistic specialist strictly on `train_domain`.

    Hard-negative mining uses ONLY `hard_neg_cols_in_stack` (columns already inside the
    specialist's own feature stack!), guaranteeing that the Pure-Subsurface Specialist
    never consults `Band 12` or `Band 19` even during negative sampling.
    """
    rng = np.random.default_rng(seed)
    vis = np.asarray(visible_faults, dtype=bool) & np.asarray(train_domain, dtype=bool) & footprint
    dom = np.asarray(train_domain, dtype=bool) & footprint

    d_vis = ndi.distance_transform_edt(~vis)
    pos_fp = vis[footprint]
    neg_fp = dom[footprint] & (~vis[footprint]) & (d_vis[footprint] > 3.5)
    pos_idx = np.flatnonzero(pos_fp)
    neg_pool = np.flatnonzero(neg_fp)
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Specialist training requires non-empty positive and safe-negative sets")

    target_neg = min(int(round(float(neg_pos_ratio) * pos_idx.size)), neg_pool.size)
    if target_neg < neg_pool.size and len(hard_neg_cols_in_stack) > 0:
        # Mine hard negatives strictly from strong edges within the specialist's own stack
        n_hard_target = int(round(float(hard_neg_frac) * target_neg))
        n_rand_target = target_neg - n_hard_target
        # Score neg_pool using max robust percentile across designated edge columns
        active = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
        col_cursor = 0
        hard_mask = np.zeros(neg_pool.size, dtype=bool)
        hard_set = set(int(c) for c in hard_neg_cols_in_stack)
        for arr, cols in active:
            for c in cols:
                if col_cursor in hard_set:
                    vals = np.asarray(arr[neg_pool, c], dtype=np.float32)
                    thr = float(np.percentile(vals[::4], 78))
                    hard_mask |= vals >= thr
                col_cursor += 1
        hard_pool = neg_pool[hard_mask]
        easy_pool = neg_pool[~hard_mask]
        if hard_pool.size >= n_hard_target and easy_pool.size >= n_rand_target:
            neg_idx = np.sort(
                np.concatenate(
                    [
                        rng.choice(hard_pool, size=n_hard_target, replace=False),
                        rng.choice(easy_pool, size=n_rand_target, replace=False),
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

    active_blocks = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    X_train = np.hstack(
        [np.asarray(arr[train_idx][:, cols], dtype=np.float32) for arr, cols in active_blocks]
    )

    hgb_deep = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=175,
        max_leaf_nodes=37,
        min_samples_leaf=75,
        l2_regularization=3.5,
        early_stopping=False,
        random_state=seed,
    ).fit(X_train, y_train)

    hgb_shallow = HistGradientBoostingClassifier(
        learning_rate=0.050,
        max_iter=145,
        max_leaf_nodes=23,
        max_depth=6,
        min_samples_leaf=115,
        l2_regularization=6.8,
        early_stopping=False,
        random_state=seed + 19,
    ).fit(X_train, y_train)

    scaler = StandardScaler()
    X_sc = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=300, random_state=seed + 37)
    lr.fit(X_sc, y_train)

    n_features = int(X_train.shape[1])
    del X_train, X_sc, y_train
    gc.collect()

    n_fp = int(footprint.sum())
    if predict_mask is None:
        pred_fp = np.empty(n_fp, dtype=np.float32)
        for start in range(0, n_fp, chunk_size):
            end = min(start + chunk_size, n_fp)
            Xc = np.hstack(
                [np.asarray(arr[start:end][:, cols], dtype=np.float32) for arr, cols in active_blocks]
            )
            p1 = hgb_deep.predict_proba(Xc)[:, 1]
            p2 = hgb_shallow.predict_proba(Xc)[:, 1]
            p3 = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
            pred_fp[start:end] = (0.50 * p1 + 0.32 * p2 + 0.18 * p3).astype(np.float32)
            del Xc, p1, p2, p3
    else:
        pred_fp = np.zeros(n_fp, dtype=np.float32)
        eval_rows = np.flatnonzero(np.asarray(predict_mask, dtype=bool)[footprint])
        for start in range(0, eval_rows.size, chunk_size):
            rows_chunk = eval_rows[start : start + chunk_size]
            Xc = np.hstack(
                [np.asarray(arr[rows_chunk][:, cols], dtype=np.float32) for arr, cols in active_blocks]
            )
            p1 = hgb_deep.predict_proba(Xc)[:, 1]
            p2 = hgb_shallow.predict_proba(Xc)[:, 1]
            p3 = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
            pred_fp[rows_chunk] = (0.50 * p1 + 0.32 * p2 + 0.18 * p3).astype(np.float32)
            del Xc, p1, p2, p3

    raw_surf = np.zeros(footprint.shape, dtype=np.float32)
    raw_surf[footprint] = pred_fp
    pi_vis = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_samp = float(pos_idx.size) / float(pos_idx.size + neg_idx.size)
    cal_surf = calibrate_reference_odds_surface(
        raw_surf,
        footprint,
        pi_vis_train=pi_vis,
        pi_sample_weighted=pi_samp,
        c0_multiplier=12.0,
    )
    del raw_surf, pred_fp
    gc.collect()

    return cal_surf, {
        "pi_vis_train": round(pi_vis, 8),
        "pi_sample_weighted": round(pi_samp, 8),
        "n_pos_train": int(pos_idx.size),
        "n_safe_neg_domain": int(neg_pool.size),
        "n_neg_sample": int(neg_idx.size),
        "n_features": n_features,
    }


def blend_cover_gated_specialists(
    *,
    s1_full: np.ndarray,
    s1_sub: np.ndarray,
    s2_full: np.ndarray,
    s2_sub: np.ndarray,
    cover_prior_fp: np.ndarray,
    crest_bonus_fp: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Cover-Adaptive Stage-1 + Stage-2 Dual-Specialist Blend (`H17-1 E2`).

    In exposed range fronts (`cover_prior ~ 0`), retains `72%` Full specialist + `28%`
    Pure-Subsurface specialist so high-relief scarps remain sharp. In concealed alluvial
    basins and playas (`cover_prior -> 1`), shifts up to `68%` weight onto the strictly
    `Band 12 / Band 19`-invariant Pure-Subsurface Stage-1 + Stage-2 hierarchy so flat
    topography never vetoes buried geothermal faults, then applies bounded multi-physics
    accommodation crest sharpening (`[0, 1]`).
    """
    eps = np.float32(1e-5)
    # Log-opinion pool within each specialist branch (Stage-2 weight 0.66, Stage-1 weight 0.34)
    lf1 = np.log(np.clip(s1_full[footprint], eps, 1.0 - eps) / (1.0 - np.clip(s1_full[footprint], eps, 1.0 - eps)))
    lf2 = np.log(np.clip(s2_full[footprint], eps, 1.0 - eps) / (1.0 - np.clip(s2_full[footprint], eps, 1.0 - eps)))
    p_full = 1.0 / (1.0 + np.exp(-np.clip(0.34 * lf1 + 0.66 * lf2, -18.0, 18.0)))

    ls1 = np.log(np.clip(s1_sub[footprint], eps, 1.0 - eps) / (1.0 - np.clip(s1_sub[footprint], eps, 1.0 - eps)))
    ls2 = np.log(np.clip(s2_sub[footprint], eps, 1.0 - eps) / (1.0 - np.clip(s2_sub[footprint], eps, 1.0 - eps)))
    p_sub = 1.0 / (1.0 + np.exp(-np.clip(0.32 * ls1 + 0.68 * ls2, -18.0, 18.0)))

    # Smooth cover-adaptive weight w_sub in [0.28, 0.68]
    cov = np.clip(np.asarray(cover_prior_fp, dtype=np.float32), 0.0, 1.0)
    w_sub = (0.28 + 0.40 * cov).astype(np.float32)

    # Geometric-arithmetic hybrid blend so concealed subsurface ridges survive even when p_full is suppressed
    p_arith = (1.0 - w_sub) * p_full + w_sub * p_sub
    l_full = np.log(np.clip(p_full, eps, 1.0 - eps) / (1.0 - np.clip(p_full, eps, 1.0 - eps)))
    l_sub = np.log(np.clip(p_sub, eps, 1.0 - eps) / (1.0 - np.clip(p_sub, eps, 1.0 - eps)))
    p_geom = 1.0 / (1.0 + np.exp(-np.clip((1.0 - w_sub) * l_full + w_sub * l_sub, -18.0, 18.0)))
    p_blend = (0.55 * p_geom + 0.45 * p_arith).astype(np.float32)

    # Bounded multi-physics crest localization multiplier mapped strictly into [0, 1]
    crest = np.clip(np.asarray(crest_bonus_fp, dtype=np.float32), 0.0, 1.0)
    l_blend = np.log(np.clip(p_blend, eps, 1.0 - eps) / (1.0 - np.clip(p_blend, eps, 1.0 - eps)))
    p_final_fp = (1.0 / (1.0 + np.exp(-np.clip(l_blend + 0.30 * (crest - 0.35), -18.0, 18.0)))).astype(np.float32)

    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = np.clip(p_final_fp, 0.0, 1.0)
    return out


def emit_global_dots_nms(
    surface: np.ndarray,
    visible_catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
) -> np.ndarray:
    """Strictly label-blind global-footprint greedy NMS dot emitter (`IR-91-S17-01` compliant).

    Depends ONLY on `(surface, visible_catalogue, footprint)`. Never accepts or inspects
    `region`, `truth`, `held_all`, or `buffer`. Enforces `d(visible_catalogue) > collar_px`
    and `d_interdot >= min_spacing_px` (`> 3.0 px` for all three repo validator suites).
    """
    h, w = surface.shape
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_catalogue, dtype=bool) & fp
    elig = fp & (~vis) & (ndi.distance_transform_edt(~vis) > float(collar_px))

    p = np.where(elig, np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0).astype(np.float32)
    flat_elig = np.flatnonzero(elig & (p > 0.0))
    if flat_elig.size == 0 or budget <= 0:
        return np.zeros((h, w), dtype=np.float32)

    # Restrict candidate sort pool to top 18 * budget eligible cells for speed
    pool_cap = min(flat_elig.size, max(int(budget) * 18, int(budget) + 10_000))
    vals = p.ravel()[flat_elig]
    if flat_elig.size > pool_cap:
        part = np.argpartition(-vals, pool_cap - 1)[:pool_cap]
        cand_flat = flat_elig[part]
        vals = vals[part]
    else:
        cand_flat = flat_elig

    order = np.lexsort((cand_flat, -vals))
    cand_flat = cand_flat[order]

    rad = int(math.ceil(min_spacing_px))
    oy, ox = np.mgrid[-rad : rad + 1, -rad : rad + 1]
    disk = np.hypot(oy, ox) < float(min_spacing_px)
    blocked = np.zeros((h + 2 * rad, w + 2 * rad), dtype=bool)
    out = np.zeros((h, w), dtype=np.float32)

    picked = 0
    for f_idx in cand_flat:
        y = int(f_idx // w)
        x = int(f_idx % w)
        if blocked[y + rad, x + rad]:
            continue
        blocked[y : y + 2 * rad + 1, x : x + 2 * rad + 1] |= disk
        out[y, x] = 1.0
        picked += 1
        if picked >= budget:
            break
    return out


def emit_global_dots_submodular(
    surface: np.ndarray,
    visible_catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
    gamma: float = 1.30,
    pool_multiplier: int = 10,
) -> np.ndarray:
    """Strictly label-blind global-footprint lazy-greedy submodular 300-m triangular-kernel emitter (`H17-1 E3`).

    Maximizes expected `R = 300 m` (`3 px`) triangular-kernel coverage of ridge-enhanced
    excess posterior probability subject to `d(visible_catalogue) > collar_px` and
    `d_interdot >= min_spacing_px`. Identical functional call in holdout and full inference;
    never accepts `region`, `truth`, `held_all`, or `buffer`.
    """
    h, w = surface.shape
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_catalogue, dtype=bool) & fp
    elig = fp & (~vis) & (ndi.distance_transform_edt(~vis) > float(collar_px))

    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)
    elig_vals = p[elig & (p > 0.0)]
    if elig_vals.size == 0 or budget <= 0:
        return np.zeros((h, w), dtype=np.float32)

    # Adaptive background floor so submodular coverage concentrates on genuine linear fault ridges
    if elig_vals.size > budget * 14:
        keep_frac = min(0.28, max(float(budget * 14) / float(elig_vals.size), 0.05))
        p_floor = float(np.quantile(elig_vals, 1.0 - keep_frac))
    else:
        p_floor = 0.0

    # 4-azimuth 1-D curvilinear ridge enhancement on `p`
    pp = np.pad(p, 2, mode="edge")
    c = pp[2 : h + 2, 2 : w + 2]
    is_ridge = (
        ((c >= pp[1 : h + 1, 2 : w + 2]) & (c >= pp[3 : h + 3, 2 : w + 2]) & (c >= pp[0:h, 2 : w + 2]) & (c >= pp[4 : h + 4, 2 : w + 2]))
        | ((c >= pp[2 : h + 2, 1 : w + 1]) & (c >= pp[2 : h + 2, 3 : w + 3]) & (c >= pp[2 : h + 2, 0:w]) & (c >= pp[2 : h + 2, 4 : w + 4]))
        | ((c >= pp[1 : h + 1, 1 : w + 1]) & (c >= pp[3 : h + 3, 3 : w + 3]) & (c >= pp[0:h, 0:w]) & (c >= pp[4 : h + 4, 4 : w + 4]))
        | ((c >= pp[1 : h + 1, 3 : w + 3]) & (c >= pp[3 : h + 3, 1 : w + 1]) & (c >= pp[0:h, 4 : w + 4]) & (c >= pp[4 : h + 4, 0:w]))
    )
    ridge_mult = np.where(is_ridge, 1.08, 0.36).astype(np.float32)
    p_excess = np.maximum(p - p_floor, 0.0)
    #Zero weight on visible catalogue and outside footprint so already-known faults receive zero reward
    weight = np.where(
        fp & (~vis),
        1000.0 * (p_excess ** float(gamma)) * ridge_mult,
        0.0,
    ).astype(np.float32)
    cand_rank = (p * np.where(is_ridge, 1.12, 0.88)).astype(np.float32)

    return MC._submodular_select_on_weight(
        weight,
        cand_rank,
        elig,
        int(budget),
        min_spacing_px=float(min_spacing_px),
        pool_multiplier=int(pool_multiplier),
        existing_dots=None,
    )
