"""Session 18 CWGR: Completeness-Weighted Freeman-Adelson Steerable Quadrature-Ridge
& Spatially Varying Byerlee-Sibson Fault-Valve Tri-Specialist (`S18-CWGR`).

Preregistered in `docs/HYPOTHESES_S18_CWGR.md` prior to model fitting.

Scientific & architectural advances over `S17-CPAD`:
1. Freeman & Adelson (1991) 2-D separable steerable `G1/G2` odd-step / even-ridge
   quadrature filter bank (`c = 0.78 in (1/sqrt(3), 1)` guaranteeing strict unimodal
   energy crests at `x = 0` on BOTH step contacts `c^2 - 1 < 0` and trough/ridge
   impulses `1 - 3c^2 < 0`, 8 azimuths, multi-scale supremum, Morrone-Burr local RMS
   normalization, and sub-pixel directional non-maxima crest skeletonization).
2. Spatially varying Basin-and-Range <-> Walker Lane geodetic kinematic-regime
   Byerlee-Morris slip/dilation tendency + Sibson (1996) swarm/geothermometer
   pore-fluid fault-valve reactivation + Athy (1930) compaction gravity stripping.
3. Quadrant-invariant empirical mid-rank probit-logistic auto-context standardization
   (`IR-91-S17-01`), eliminating 2/3/4-quadrant distribution shift prior to
   `spac_coda` axial structural integration with zero label usage.
4. Dedicated Stage-2 Structural-Topology & Quadrature-Crest Specialist (`IR-91-S17-02`)
   pooled in log-odds space with Full and Pure-Subsurface Specialists.
5. Selected-At-Random (SAR; Bekker & Davis 2019) surface-mapper propensity modeling,
   mean-preserving inverse-propensity positive sample weights (`E2`), and analytical
   unmapped-fault posterior Bayes factor `P(Y=1 | S=0, x)` (`E3`).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Sequence

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter, gaussian_filter1d, map_coordinates
from scipy.special import expit, logit, ndtri
from scipy.stats import rankdata
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from gems91.cpad17 import (
    BANNED_GDR_COLUMNS,
    STRICT_TOPO_FEATURE_NAMES,
    calibrate_reference_odds_surface,
    emit_global_dots_submodular,
    extract_gdr_disequilibrium_impulses,
)
from gems91.dd_vtc_pu import _clean_band_edt

CWGR_SUBSURFACE_FEATURE_NAMES: tuple[str, ...] = (
    # Group A: Freeman-Adelson Steerable Quadrature & Phase Symmetry (7 DEM-free)
    "cwgr_quad_grav_odd_step",
    "cwgr_quad_grav_crest",
    "cwgr_quad_mag_demag_trough",
    "cwgr_quad_rtp_odd_step",
    "cwgr_quad_basement_step_crest",
    "cwgr_quad_rad_cond_alteration",
    "cwgr_quad_cross_physics_lock",
    # Group B: Kinematic Byerlee-Morris & Sibson Fault-Valve Continuum (5 DEM-free)
    "cwgr_kinematic_regime_index",
    "cwgr_byerlee_adaptive_slip_tendency",
    "cwgr_sibson_fault_valve_overpressure",
    "cwgr_kostrov_aseismic_strain_deficit",
    "cwgr_en_echelon_quadrature_relay",
    # Group C1: Athy Compaction Silicification & Salem Intrabasinal Crest (3 DEM-free)
    "cwgr_athy_silicification_excess",
    "cwgr_salem_intrabasinal_ratio",
    "cwgr_subsurface_crest_skeleton",
)

CWGR_TOPO_ONLY_NAMES: tuple[str, ...] = (
    # Group C2: Piedmont Micro-Scarp Quadrature, Pluvial Deconfounder & Mapper Exposure (3 topo)
    "cwgr_piedmont_microscarp_quad",
    "cwgr_pluvial_contour_orthogonality",
    "cwgr_mapper_visibility_index",
)

CWGR_FEATURE_NAMES: tuple[str, ...] = CWGR_SUBSURFACE_FEATURE_NAMES + CWGR_TOPO_ONLY_NAMES

CWGR_STRICT_TOPO_FEATURE_NAMES: frozenset[str] = (
    STRICT_TOPO_FEATURE_NAMES | frozenset(CWGR_TOPO_ONLY_NAMES)
)

# Exact unimodal step + impulse quadrature balance c = 0.78 in (1/sqrt(3), 1):
# Step curvature at x=0 is proportional to (c^2 - 1) = -0.3916 < 0 (unimodal peak);
# Ridge/trough impulse curvature at x=0 is proportional to (1 - 3c^2) = -0.8252 < 0 (unimodal peak).
_KAPPA_G2 = np.float32(0.78)


def _robust_pos_unit(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    """Map non-negative physical response smoothly into `[0, 1]` using 98.5th-percentile scale."""
    fp = np.asarray(footprint, dtype=bool)
    pos = np.maximum(np.nan_to_num(np.asarray(arr, dtype=np.float32), nan=0.0), 0.0)
    vals = pos[fp]
    if vals.size == 0:
        return np.zeros(pos.shape, dtype=np.float32)
    scale = float(np.percentile(vals[::8] if vals.size > 4096 else vals, 98.5))
    scale = max(scale, 1e-6)
    r = pos / np.float32(scale)
    unit = (r / np.sqrt(np.float32(1.0) + r * r)).astype(np.float32)
    unit[~fp] = 0.0
    return unit


def _shift_2d_clamped(arr: np.ndarray, dy: np.ndarray, dx: np.ndarray) -> np.ndarray:
    """Bilinearly sample `arr` at `(y + dy, x + dx)` clamped to image bounds."""
    h, w = arr.shape
    yy, xx = np.meshgrid(
        np.arange(h, dtype=np.float32),
        np.arange(w, dtype=np.float32),
        indexing="ij",
    )
    coords = np.array(
        [np.clip(yy + dy, 0.0, h - 1.0), np.clip(xx + dx, 0.0, w - 1.0)],
        dtype=np.float32,
    )
    return map_coordinates(arr, coords, order=1, mode="nearest").astype(np.float32)


def steerable_g2h2_quadrature(
    field_2d: np.ndarray,
    footprint: np.ndarray,
    sigmas: Sequence[float] = (1.8, 4.2),
    n_angles: int = 8,
    norm_sigma: float = 9.0,
    crest_step_px: float = 1.35,
    already_clean: bool = False,
) -> dict[str, np.ndarray]:
    """Compute multi-scale Freeman-Adelson (1991) steerable odd/even quadrature invariants.

    Uses separable 1-D Gaussian basis passes (`G1` odd step + `G2` even trough/ridge
    with unimodal balance `c = 0.78`) streamed across `n_angles` orientations in-place.

    Returns dict of `(H, W)` float32 arrays (0.0 outside `footprint`):
      - `energy`: local-RMS-normalized multi-scale quadrature energy in `[0, 1]`
      - `odd_step`: anisotropic odd-symmetry contact step energy in `[0, 1]`
      - `even_trough`: anisotropic positive G2 trough response (local minimum corridor) in `[0, 1]`
      - `even_peak`: anisotropic negative G2 peak response (local maximum corridor) in `[0, 1]`
      - `aniso`: azimuthal tubular elongation `(E_max - E_min) / (E_max + E_min + eps)` in `[0, 1]`
      - `crest`: sub-pixel directional non-maxima quadrature crestness in `[0, 1]`
      - `normal_phi`: dominant strike-normal angle in `[0, pi)` (x=east, y=south)
    """
    fp = np.asarray(footprint, dtype=bool)
    if already_clean:
        clean = np.asarray(field_2d, dtype=np.float32)
    else:
        clean = _clean_band_edt(np.asarray(field_2d, dtype=np.float32), fp)
    h, w = clean.shape

    best_energy = np.zeros((h, w), dtype=np.float32)
    best_odd = np.zeros((h, w), dtype=np.float32)
    best_trough = np.zeros((h, w), dtype=np.float32)
    best_peak = np.zeros((h, w), dtype=np.float32)
    best_aniso = np.zeros((h, w), dtype=np.float32)
    best_crest = np.zeros((h, w), dtype=np.float32)
    best_phi = np.zeros((h, w), dtype=np.float32)

    yy, xx = np.meshgrid(
        np.arange(h, dtype=np.float32),
        np.arange(w, dtype=np.float32),
        indexing="ij",
    )
    angles = np.linspace(0.0, np.pi, int(n_angles), endpoint=False, dtype=np.float32)

    for sigma in sigmas:
        s = float(sigma)
        s1 = np.float32(s)
        s2 = np.float32(s * s)

        g0y = gaussian_filter1d(clean, sigma=s, axis=0, order=0, mode="nearest")
        g1y = gaussian_filter1d(clean, sigma=s, axis=0, order=1, mode="nearest")
        g2y = gaussian_filter1d(clean, sigma=s, axis=0, order=2, mode="nearest")

        u_x = (gaussian_filter1d(g0y, sigma=s, axis=1, order=1, mode="nearest") * s1).astype(
            np.float32
        )
        u_y = (gaussian_filter1d(g1y, sigma=s, axis=1, order=0, mode="nearest") * s1).astype(
            np.float32
        )
        u_xx = (gaussian_filter1d(g0y, sigma=s, axis=1, order=2, mode="nearest") * s2).astype(
            np.float32
        )
        u_xy = (gaussian_filter1d(g1y, sigma=s, axis=1, order=1, mode="nearest") * s2).astype(
            np.float32
        )
        u_yy = (gaussian_filter1d(g2y, sigma=s, axis=1, order=0, mode="nearest") * s2).astype(
            np.float32
        )
        del g0y, g1y, g2y

        e_max = np.full((h, w), -1.0, dtype=np.float32)
        e_min = np.full((h, w), np.inf, dtype=np.float32)
        phi_star = np.zeros((h, w), dtype=np.float32)
        g1_star = np.zeros((h, w), dtype=np.float32)
        g2_star = np.zeros((h, w), dtype=np.float32)

        for phi in angles:
            c = np.float32(np.cos(phi))
            sn = np.float32(np.sin(phi))
            g1 = c * u_x + sn * u_y
            g2 = (c * c) * u_xx + (np.float32(2.0) * c * sn) * u_xy + (sn * sn) * u_yy
            energy = np.hypot(g1, _KAPPA_G2 * g2).astype(np.float32)
            upd = energy > e_max
            e_max = np.where(upd, energy, e_max)
            e_min = np.minimum(e_min, energy)
            phi_star = np.where(upd, phi, phi_star)
            g1_star = np.where(upd, g1, g1_star)
            g2_star = np.where(upd, g2, g2_star)

        del u_x, u_y, u_xx, u_xy, u_yy

        fp_vals = e_max[fp]
        eps_floor = float(np.percentile(fp_vals, 55.0)) if fp_vals.size else 1e-4
        eps_floor = max(eps_floor * 0.35, 1e-5)

        local_ms = gaussian_filter(e_max * e_max, sigma=float(norm_sigma), mode="nearest")
        e_rms = np.sqrt(np.maximum(local_ms, 0.0) + np.float32(eps_floor * eps_floor)).astype(
            np.float32
        )

        e_norm_raw = e_max / (e_rms + np.float32(1e-6))
        e_norm = (e_norm_raw / np.sqrt(np.float32(1.0) + e_norm_raw * e_norm_raw)).astype(
            np.float32
        )

        aniso = np.clip(
            (e_max - e_min) / (e_max + e_min + np.float32(eps_floor * 0.25 + 1e-6)),
            0.0,
            1.0,
        ).astype(np.float32)

        odd_raw = (np.abs(g1_star) / (e_rms + np.float32(1e-6))) * (
            np.float32(0.30) + np.float32(0.70) * aniso
        )
        odd_norm = (odd_raw / np.sqrt(np.float32(1.0) + odd_raw * odd_raw)).astype(np.float32)

        trough_raw = ((_KAPPA_G2 * np.maximum(g2_star, 0.0)) / (e_rms + np.float32(1e-6))) * (
            np.float32(0.30) + np.float32(0.70) * aniso
        )
        trough_norm = (
            trough_raw / np.sqrt(np.float32(1.0) + trough_raw * trough_raw)
        ).astype(np.float32)

        peak_raw = ((_KAPPA_G2 * np.maximum(-g2_star, 0.0)) / (e_rms + np.float32(1e-6))) * (
            np.float32(0.30) + np.float32(0.70) * aniso
        )
        peak_norm = (peak_raw / np.sqrt(np.float32(1.0) + peak_raw * peak_raw)).astype(
            np.float32
        )

        # Sub-pixel directional non-maxima crestness along +/- step * normal
        step = np.float32(crest_step_px * max(1.0, 0.75 * s))
        dy = step * np.sin(phi_star)
        dx = step * np.cos(phi_star)
        coords_plus = np.array(
            [np.clip(yy + dy, 0.0, h - 1.0), np.clip(xx + dx, 0.0, w - 1.0)],
            dtype=np.float32,
        )
        coords_minus = np.array(
            [np.clip(yy - dy, 0.0, h - 1.0), np.clip(xx - dx, 0.0, w - 1.0)],
            dtype=np.float32,
        )
        e_plus = map_coordinates(e_max, coords_plus, order=1, mode="nearest")
        e_minus = map_coordinates(e_max, coords_minus, order=1, mode="nearest")
        del coords_plus, coords_minus

        curv_prom = np.clip(
            (e_max - np.float32(0.5) * (e_plus + e_minus))
            / (np.float32(0.35) * e_max + np.float32(eps_floor * 0.20 + 1e-6)),
            0.0,
            1.0,
        )
        ridge_dom = np.clip(
            (e_max - np.maximum(e_plus, e_minus) + np.float32(0.08) * e_max)
            / (np.float32(0.18) * e_max + np.float32(eps_floor * 0.20 + 1e-6)),
            0.0,
            1.0,
        )
        crest = np.clip(
            e_norm * (np.float32(0.25) + np.float32(0.75) * aniso) * np.sqrt(curv_prom * ridge_dom),
            0.0,
            1.0,
        ).astype(np.float32)

        win = e_norm >= best_energy
        best_energy = np.where(win, e_norm, best_energy)
        best_odd = np.where(win, odd_norm, best_odd)
        best_trough = np.where(win, trough_norm, best_trough)
        best_peak = np.where(win, peak_norm, best_peak)
        best_aniso = np.where(win, aniso, best_aniso)
        best_crest = np.maximum(best_crest, crest)
        best_phi = np.where(win, phi_star, best_phi)

    del yy, xx
    return {
        "energy": np.where(fp, best_energy, 0.0).astype(np.float32),
        "odd_step": np.where(fp, best_odd, 0.0).astype(np.float32),
        "even_trough": np.where(fp, best_trough, 0.0).astype(np.float32),
        "even_peak": np.where(fp, best_peak, 0.0).astype(np.float32),
        "aniso": np.where(fp, best_aniso, 0.0).astype(np.float32),
        "crest": np.where(fp, best_crest, 0.0).astype(np.float32),
        "normal_phi": np.where(fp, best_phi, 0.0).astype(np.float32),
    }


def athy_strip_gravity(
    b13_grav: np.ndarray,
    b15_depth: np.ndarray,
    footprint: np.ndarray,
    fit_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Strip Athy (1930) exponential basin-compaction gravity deficit from `Band 13`."""
    fp = np.asarray(footprint, dtype=bool)
    mask = fp if fit_mask is None else (fp & np.asarray(fit_mask, dtype=bool))
    g = _clean_band_edt(np.asarray(b13_grav, dtype=np.float32), fp)
    z = np.maximum(_clean_band_edt(np.asarray(b15_depth, dtype=np.float32), fp), 0.0)

    athy_term = (1.0 - np.exp(-z / 600.0)).astype(np.float32)
    log_term = np.log1p(z).astype(np.float32)

    Design = np.column_stack(
        [
            np.ones(int(mask.sum()), dtype=np.float64),
            athy_term[mask].astype(np.float64),
            log_term[mask].astype(np.float64),
        ]
    )
    coef, *_ = np.linalg.lstsq(Design, g[mask].astype(np.float64), rcond=None)
    pred = (
        float(coef[0])
        + float(coef[1]) * athy_term.astype(np.float64)
        + float(coef[2]) * log_term.astype(np.float64)
    ).astype(np.float32)
    stripped = (g - pred).astype(np.float32)
    stripped_clean = _clean_band_edt(stripped, fp)

    hp = stripped_clean - gaussian_filter(stripped_clean, sigma=12.0, mode="nearest")
    cover_weight = np.clip(z / (z + np.float32(120.0)), 0.15, 1.0)
    silic_raw = np.maximum(hp, 0.0) * cover_weight
    silic = _robust_pos_unit(silic_raw, fp)
    return np.where(fp, stripped_clean, 0.0).astype(np.float32), silic


def _get_band_clean(bands_or_src, band_idx0: int, fp: np.ndarray, nonneg: bool = False) -> np.ndarray:
    """Read and EDT-clean a single 0-indexed band from `(19,H,W)` ndarray or open `rasterio` Dataset."""
    if isinstance(bands_or_src, np.ndarray):
        raw = np.asarray(bands_or_src[band_idx0], dtype=np.float32)
    else:
        raw = bands_or_src.read(int(band_idx0) + 1).astype(np.float32)
    cleaned = _clean_band_edt(raw, fp)
    del raw
    if nonneg:
        np.maximum(cleaned, 0.0, out=cleaned)
    return cleaned


def _compute_cwgr_columns(
    bands_or_src,
    footprint: np.ndarray,
    col_sink,
    gdr_csv_path: Path | None = None,
) -> None:
    """Stream all 18 `CWGR` features into `col_sink(col_idx, arr_2d)` in `< 650 MB` peak RAM."""
    fp = np.asarray(footprint, dtype=bool)
    h, w = fp.shape

    # 1. Gravity + Basement Depth (Cols 0, 1, 4, 12)
    b13 = _get_band_clean(bands_or_src, 12, fp)
    b15 = _get_band_clean(bands_or_src, 14, fp, nonneg=True)
    grav_stripped, athy_silic = athy_strip_gravity(b13, b15, fp)
    del b13
    col_sink(12, athy_silic)
    del athy_silic

    q_grav = steerable_g2h2_quadrature(grav_stripped, fp, sigmas=(1.8, 4.2))
    del grav_stripped
    col_sink(0, q_grav["odd_step"])
    col_sink(1, q_grav["crest"])
    grav_crest = q_grav["crest"]
    grav_phi = q_grav["normal_phi"]
    grav_energy = q_grav["energy"]
    grav_aniso = q_grav["aniso"]
    del q_grav
    gc.collect()

    log_b15 = np.log1p(b15).astype(np.float32)
    q_base = steerable_g2h2_quadrature(log_b15, fp, sigmas=(2.0, 4.5))
    del log_b15
    base_crest = q_base["crest"]
    base_phi = q_base["normal_phi"]
    col_sink(4, base_crest)
    del q_base
    gc.collect()

    # 2. Draped Demagnetization Residual Band 14 - Band 01 (Col 2)
    b01 = _get_band_clean(bands_or_src, 0, fp)
    b14 = _get_band_clean(bands_or_src, 13, fp)
    diff14_01 = b14 - b01
    del b01, b14
    drape_diff = diff14_01 - gaussian_filter(diff14_01, sigma=18.0, mode="nearest")
    del diff14_01
    q_demag = steerable_g2h2_quadrature(drape_diff, fp, sigmas=(1.6, 3.6))
    del drape_diff
    demag_col2 = np.clip(
        np.float32(0.68) * q_demag["even_trough"] + np.float32(0.32) * q_demag["crest"],
        0.0,
        1.0,
    ).astype(np.float32)
    demag_phi = q_demag["normal_phi"]
    col_sink(2, demag_col2)
    del q_demag
    gc.collect()

    # 3. RTP Magnetics + Salem Tilt-Depth + Cross-Physics Lock (Cols 3, 6, 13)
    b02 = _get_band_clean(bands_or_src, 1, fp)
    q_rtp = steerable_g2h2_quadrature(b02, fp, sigmas=(1.8, 4.2))
    col_sink(3, q_rtp["odd_step"])
    rtp_crest = q_rtp["crest"]
    rtp_phi = q_rtp["normal_phi"]
    rtp_energy = q_rtp["energy"]
    rtp_aniso = q_rtp["aniso"]
    del q_rtp

    rtp_s = gaussian_filter(b02, sigma=2.0, mode="nearest")
    del b02
    ry = gaussian_filter1d(rtp_s, sigma=1.0, axis=0, order=1, mode="nearest") / np.float32(100.0)
    rx = gaussian_filter1d(rtp_s, sigma=1.0, axis=1, order=1, mode="nearest") / np.float32(100.0)
    rz = (rtp_s - gaussian_filter(rtp_s, sigma=5.0, mode="nearest")) / np.float32(350.0)
    del rtp_s
    tilt = np.arctan2(rz, np.hypot(rx, ry) + np.float32(1e-6))
    del rx, ry, rz
    ty = gaussian_filter1d(tilt, sigma=1.5, axis=0, order=1, mode="nearest") / np.float32(100.0)
    tx = gaussian_filter1d(tilt, sigma=1.5, axis=1, order=1, mode="nearest") / np.float32(100.0)
    del tilt
    z_salem_m = np.clip(1.0 / (np.hypot(tx, ty) + np.float32(2.5e-4)), 25.0, 4000.0).astype(
        np.float32
    )
    del tx, ty
    intrabasinal_gate = expit(((np.float32(0.65) * b15 - z_salem_m) / np.float32(120.0))).astype(
        np.float32
    ) * np.clip(b15 / (b15 + np.float32(150.0)), 0.0, 1.0)
    del z_salem_m
    col_sink(13, np.where(fp, np.clip(intrabasinal_gate * rtp_energy, 0.0, 1.0), 0.0))
    del intrabasinal_gate

    mag_comb_crest = np.maximum(demag_col2, np.float32(0.85) * rtp_crest)
    phi_mag = np.where(demag_col2 >= np.float32(0.85) * rtp_crest, demag_phi, rtp_phi)
    del rtp_crest, demag_phi
    align_gm = np.square(np.cos(grav_phi - phi_mag)).astype(np.float32)
    align_gb = np.square(np.cos(grav_phi - base_phi)).astype(np.float32)
    del phi_mag, base_phi
    cross_lock = _robust_pos_unit(
        np.power(
            np.maximum(grav_crest, np.float32(0.02))
            * np.maximum(mag_comb_crest, np.float32(0.02))
            * np.maximum(base_crest, np.float32(0.02)),
            np.float32(1.0 / 3.0),
        )
        * (np.float32(0.30) + np.float32(0.40) * align_gm + np.float32(0.30) * align_gb),
        fp,
    )
    del mag_comb_crest, align_gm, align_gb
    col_sink(6, cross_lock)

    phi_sub = np.where(grav_energy >= rtp_energy, grav_phi, rtp_phi)
    del grav_energy, rtp_energy, grav_phi, rtp_phi
    sub_aniso = np.maximum(grav_aniso, rtp_aniso)
    del grav_aniso, rtp_aniso
    gc.collect()

    # 4. Radiometric TC + Shallow Conductivity Alteration (Col 5)
    b06 = _get_band_clean(bands_or_src, 5, fp)
    q_rad = steerable_g2h2_quadrature(b06, fp, sigmas=(2.0, 4.5))
    del b06
    rad_e, rad_p = q_rad["energy"], q_rad["normal_phi"]
    del q_rad

    b17 = _get_band_clean(bands_or_src, 16, fp, nonneg=True)
    q_cond = steerable_g2h2_quadrature(np.log1p(b17), fp, sigmas=(2.2, 5.0))
    del b17
    align_rc = np.square(np.cos(rad_p - q_cond["normal_phi"])).astype(np.float32)
    col_sink(
        5,
        _robust_pos_unit(
            np.sqrt(
                np.maximum(
                    rad_e
                    * (
                        np.float32(0.5) * q_cond["energy"]
                        + np.float32(0.5) * q_cond["even_peak"]
                    ),
                    0.0,
                )
            )
            * (np.float32(0.35) + np.float32(0.65) * align_rc),
            fp,
        ),
    )
    del rad_e, rad_p, q_cond, align_rc
    gc.collect()

    # 5. Group B: Kinematic Byerlee-Morris & Sibson Fault-Valve + Relay + Skeleton (Cols 7..11, 14)
    nx = np.cos(phi_sub).astype(np.float32)
    ny_south = np.sin(phi_sub).astype(np.float32)
    del phi_sub
    strike_az = np.arctan2(ny_south, nx).astype(np.float32)

    b04 = _get_band_clean(bands_or_src, 3, fp, nonneg=True)
    b07 = _get_band_clean(bands_or_src, 6, fp, nonneg=True)
    b08 = _get_band_clean(bands_or_src, 7, fp)

    strain_denom = np.hypot(b07, b08) + np.float32(0.5)
    r_kin = np.clip(b08 / strain_denom, -1.0, 1.0).astype(np.float32)
    del b08
    col_sink(7, np.where(fp, np.float32(0.5) * (r_kin + np.float32(1.0)), 0.0))

    opt_bnr = np.square(np.cos(strike_az - np.deg2rad(15.0))).astype(np.float32)
    opt_wl = np.maximum(
        np.square(np.cos(strike_az - np.deg2rad(-32.0))),
        np.float32(0.85) * np.square(np.cos(strike_az - np.deg2rad(38.0))),
    ).astype(np.float32)
    del strike_az
    w_ext = np.clip(np.float32(0.5) + np.float32(0.8) * r_kin, 0.0, 1.0)
    w_shear = np.clip(b07 / strain_denom, 0.0, 1.0)
    del b07, strain_denom, r_kin
    byerlee_opt = (w_ext * opt_bnr + w_shear * opt_wl) / (w_ext + w_shear + np.float32(1e-5))
    del opt_bnr, opt_wl, w_ext, w_shear
    col_sink(8, _robust_pos_unit(byerlee_opt * sub_aniso * np.log1p(b04), fp))
    del byerlee_opt

    b10 = _get_band_clean(bands_or_src, 9, fp, nonneg=True)
    b16 = _get_band_clean(bands_or_src, 15, fp, nonneg=True)
    swarm_excess = np.maximum(np.log1p(b10) - np.float32(0.85) * np.log1p(b16), 0.0)
    del b10
    if gdr_csv_path is not None and Path(gdr_csv_path).exists():
        diseq_imp, enth_imp, _ = extract_gdr_disequilibrium_impulses(
            Path(gdr_csv_path), (h, w), fp
        )
        gdr_diseq = _robust_pos_unit(gaussian_filter(diseq_imp, sigma=7.0, mode="constant"), fp)
        gdr_t = _robust_pos_unit(gaussian_filter(enth_imp, sigma=7.0, mode="constant"), fp)
        fluid_drive = _robust_pos_unit(swarm_excess, fp) + np.float32(0.65) * np.maximum(
            gdr_diseq, np.float32(0.6) * gdr_t
        )
        del diseq_imp, enth_imp, gdr_diseq, gdr_t
    else:
        fluid_drive = _robust_pos_unit(swarm_excess, fp)
    del swarm_excess

    sub_crest_base = np.maximum.reduce([grav_crest, demag_col2, base_crest])
    col_sink(
        9,
        _robust_pos_unit(
            fluid_drive * (np.float32(0.25) + np.float32(0.75) * sub_crest_base), fp
        ),
    )
    del fluid_drive

    kostrov = (
        np.log1p(b04)
        / (np.float32(1.0) + np.float32(0.45) * np.log1p(np.float32(0.05) * b16))
    ) * sub_aniso
    del b04, b16, sub_aniso
    col_sink(10, _robust_pos_unit(kostrov, fp))
    del kostrov

    sx = (-ny_south).astype(np.float32)
    sy = nx.astype(np.float32)
    relay_acc = np.zeros((h, w), dtype=np.float32)
    for delta, along in ((4.0, 5.0), (8.0, 7.0)):
        for sgn in (1.0, -1.0):
            p1 = _shift_2d_clamped(
                sub_crest_base,
                delta * ny_south + sgn * along * sy,
                delta * nx + sgn * along * sx,
            )
            p2 = _shift_2d_clamped(
                sub_crest_base,
                -delta * ny_south - sgn * along * sy,
                -delta * nx - sgn * along * sx,
            )
            relay_acc = np.maximum(relay_acc, np.sqrt(np.maximum(p1 * p2, 0.0)))
    del sx, sy, sub_crest_base
    relay_unit = _robust_pos_unit(relay_acc, fp)
    del relay_acc
    col_sink(11, relay_unit)

    skel_raw = (
        np.float32(0.30) * grav_crest
        + np.float32(0.24) * demag_col2
        + np.float32(0.20) * base_crest
        + np.float32(0.16) * cross_lock
        + np.float32(0.10) * relay_unit
    )
    del grav_crest, demag_col2, base_crest, cross_lock, relay_unit
    col_sink(14, _robust_pos_unit(skel_raw, fp))
    del skel_raw
    gc.collect()

    # 6. Group C2: Topographic / Piedmont / Mapper Visibility (Cols 15..17 ONLY)
    b12 = _get_band_clean(bands_or_src, 11, fp)
    b19 = _get_band_clean(bands_or_src, 18, fp, nonneg=True)

    q_pied = steerable_g2h2_quadrature(b12, fp, sigmas=(1.5, 3.2), norm_sigma=10.0)
    reg_slope = gaussian_filter(b19, sigma=7.0, mode="nearest")
    s_p85 = float(np.percentile(reg_slope[fp], 85.0)) if fp.any() else 10.0
    piedmont_taper = np.clip(
        np.float32(1.15) - np.float32(0.55) * (reg_slope / max(s_p85, 1e-3)), 0.35, 1.0
    )
    col_sink(
        15,
        np.where(
            fp,
            np.clip(
                q_pied["crest"] * q_pied["odd_step"] * piedmont_taper * np.float32(1.45),
                0.0,
                1.0,
            ),
            0.0,
        ),
    )
    del q_pied, piedmont_taper

    elev_reg = gaussian_filter(b12, sigma=8.0, mode="nearest")
    del b12
    ey = gaussian_filter1d(elev_reg, sigma=1.5, axis=0, order=1, mode="nearest")
    ex = gaussian_filter1d(elev_reg, sigma=1.5, axis=1, order=1, mode="nearest")
    del elev_reg
    enorm = np.hypot(ex, ey) + np.float32(1e-5)
    cross_sin = np.abs(nx * (ey / enorm) - ny_south * (ex / enorm)).astype(np.float32)
    del ex, ey, enorm, nx, ny_south
    col_sink(16, np.where(fp, np.clip(cross_sin, 0.0, 1.0), 0.0))
    del cross_sin

    slope_unit = _robust_pos_unit(reg_slope, fp)
    del reg_slope
    bedrock_exp = np.exp(-b15 / np.float32(160.0)).astype(np.float32)
    del b15
    scarp_vis = _robust_pos_unit(b19, fp)
    del b19
    vis = np.clip(
        np.float32(0.45) * slope_unit
        + np.float32(0.30) * scarp_vis
        + np.float32(0.25) * bedrock_exp,
        0.0,
        1.0,
    )
    del slope_unit, scarp_vis, bedrock_exp
    col_sink(17, np.where(fp, vis, 0.0))
    del vis
    gc.collect()


def extract_cwgr_features(
    bands: np.ndarray,
    footprint: np.ndarray,
    gdr_csv_path: Path | None = None,
    gdr_transform=None,
) -> np.ndarray:
    """Compute all 18 `CWGR` features `(18, H, W)` float32, finite, 0 outside footprint."""
    assert bands.ndim == 3 and bands.shape[0] == 19, f"Expected (19,H,W), got {bands.shape}"
    fp = np.asarray(footprint, dtype=bool)
    _, h, w = bands.shape
    out = np.zeros((len(CWGR_FEATURE_NAMES), h, w), dtype=np.float32)

    def _sink(col_idx: int, arr_2d: np.ndarray) -> None:
        a = np.nan_to_num(np.asarray(arr_2d, dtype=np.float32), nan=0.0, posinf=1.0, neginf=0.0)
        a[~fp] = 0.0
        out[col_idx] = a

    _compute_cwgr_columns(bands, fp, _sink, gdr_csv_path=gdr_csv_path)
    return out


def build_or_load_cwgr_memmap(
    cache_dir: str | Path,
    geodawn_path: str | Path,
    gdr_csv: str | Path,
    footprint: np.ndarray,
) -> tuple[np.memmap, list[str], dict[str, object]]:
    """Stream footprint-indexed `(n_fp, 18)` `float32` memmap directly to disk (`< 700 MB` RAM)."""
    cdir = Path(cache_dir)
    cdir.mkdir(parents=True, exist_ok=True)
    dat_path = cdir / "X_cwgr.f32.mmap"
    meta_path = cdir / "X_cwgr.meta.json"
    fp = np.asarray(footprint, dtype=bool)
    n_fp = int(fp.sum())
    n_cols = len(CWGR_FEATURE_NAMES)

    if dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == list(CWGR_FEATURE_NAMES)
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(CWGR_FEATURE_NAMES), meta

    mm_w = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    def _mmap_sink(col_idx: int, arr_2d: np.ndarray) -> None:
        vals = np.nan_to_num(
            np.asarray(arr_2d, dtype=np.float32)[fp], nan=0.0, posinf=1.0, neginf=0.0
        )
        mm_w[:, col_idx] = vals
        mm_w.flush()

    with rasterio.open(geodawn_path) as src:
        _compute_cwgr_columns(src, fp, _mmap_sink, gdr_csv_path=Path(gdr_csv))

    mm_w.flush()
    del mm_w
    gc.collect()

    meta = {
        "schema_version": "gems91.cwgr18.features.v1",
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": list(CWGR_FEATURE_NAMES),
        "subsurface_cols": list(range(len(CWGR_SUBSURFACE_FEATURE_NAMES))),
        "topo_cols": list(range(len(CWGR_SUBSURFACE_FEATURE_NAMES), n_cols)),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(CWGR_FEATURE_NAMES), meta


def rank_logit_standardize_per_quadrant(
    surface_2d: np.ndarray,
    folds: Sequence[dict],
    footprint: np.ndarray,
    mu0: float = -2.4,
    tau0: float = 0.85,
) -> np.ndarray:
    """Standardize `surface_2d` identically within each quadrant `folds[q]['region']` (`IR-91-S17-01`)."""
    fp = np.asarray(footprint, dtype=bool)
    surf = np.asarray(surface_2d, dtype=np.float64)
    out = np.zeros(surf.shape, dtype=np.float32)

    covered = np.zeros(surf.shape, dtype=bool)
    for fold in folds:
        reg = np.asarray(fold["region"], dtype=bool) & fp
        n = int(reg.sum())
        if n == 0:
            continue
        covered |= reg
        vals = np.nan_to_num(surf[reg], nan=0.0, posinf=1.0, neginf=0.0)
        ranks = rankdata(vals, method="average")
        u = np.clip((ranks - 0.5) / float(n), 1e-6, 1.0 - 1e-6)
        mapped = expit(float(mu0) + float(tau0) * ndtri(u))
        out[reg] = mapped.astype(np.float32)

    rem = fp & (~covered)
    if rem.any():
        n = int(rem.sum())
        vals = np.nan_to_num(surf[rem], nan=0.0, posinf=1.0, neginf=0.0)
        ranks = rankdata(vals, method="average")
        u = np.clip((ranks - 0.5) / float(n), 1e-6, 1.0 - 1e-6)
        out[rem] = expit(float(mu0) + float(tau0) * ndtri(u)).astype(np.float32)

    out[~fp] = 0.0
    return out


def estimate_sar_propensity(
    visibility_flat: np.ndarray,
    footprint_flat: np.ndarray,
    train_domain_flat: np.ndarray,
    train_pos_flat: np.ndarray,
    power: float = 0.50,
    w_min: float = 0.78,
    w_max: float = 2.50,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Fit monotonic SAR mapper propensity `e_hat(x)` strictly on `train_domain_flat` (`Bekker & Davis 2019`)."""
    fp_f = np.asarray(footprint_flat, dtype=bool)
    dom_f = np.asarray(train_domain_flat, dtype=bool) & fp_f
    pos_f = np.asarray(train_pos_flat, dtype=bool) & dom_f
    v = np.clip(np.nan_to_num(np.asarray(visibility_flat, dtype=np.float64), nan=0.0), 0.0, 1.0)

    dom_idx = np.flatnonzero(dom_f)
    pos_idx = np.flatnonzero(pos_f)
    if pos_idx.size < 20 or dom_idx.size <= pos_idx.size:
        e_default = np.where(fp_f, 0.50, 0.0).astype(np.float32)
        w_default = np.ones(v.shape[0], dtype=np.float32)
        return e_default, w_default, {"beta1": 0.0, "e_min": 0.5, "e_max": 0.5, "pos_weight_mean": 1.0}

    rng = np.random.default_rng(20261025 + int(pos_idx.size))
    bg_pool = np.flatnonzero(dom_f & (~pos_f))
    n_bg = min(int(bg_pool.size), max(40000, 3 * int(pos_idx.size)))
    bg_idx = rng.choice(bg_pool, size=n_bg, replace=False) if bg_pool.size > n_bg else bg_pool

    x_fit = np.concatenate([v[pos_idx], v[bg_idx]])[:, None]
    y_fit = np.concatenate(
        [np.ones(pos_idx.size, dtype=np.int32), np.zeros(bg_idx.size, dtype=np.int32)]
    )
    lr = LogisticRegression(C=1.0, max_iter=300, random_state=20261025)
    lr.fit(x_fit, y_fit)
    b0 = float(lr.intercept_[0])
    b1 = max(0.0, float(lr.coef_[0, 0]))

    raw_s = expit(b0 + b1 * v)
    anchor_hi = float(np.percentile(raw_s[dom_idx], 98.5))
    anchor_lo = float(np.percentile(raw_s[dom_idx], 2.0))
    span = max(anchor_hi - anchor_lo, 1e-6)
    e_unit = np.clip((raw_s - anchor_lo) / span, 0.0, 1.0)
    e_hat = np.where(fp_f, 0.16 + 0.68 * e_unit, 0.0).astype(np.float32)

    e_pos_ref = float(np.median(e_hat[pos_idx]))
    w_raw = np.clip(np.power(e_pos_ref / np.maximum(e_hat, 0.16), float(power)), w_min, w_max)
    mean_pos_w = float(np.mean(w_raw[pos_idx]))
    w_norm = np.clip(w_raw / max(mean_pos_w, 1e-6), w_min, w_max).astype(np.float32)
    w_norm = (w_norm / max(float(np.mean(w_norm[pos_idx])), 1e-6)).astype(np.float32)

    diag = {
        "beta1": round(b1, 5),
        "e_hat_p10": round(float(np.percentile(e_hat[dom_idx], 10.0)), 5),
        "e_hat_p90": round(float(np.percentile(e_hat[dom_idx], 90.0)), 5),
        "pos_weight_min": round(float(w_norm[pos_idx].min()), 5),
        "pos_weight_max": round(float(w_norm[pos_idx].max()), 5),
        "pos_weight_mean": round(float(np.mean(w_norm[pos_idx].mean())), 6),
    }
    return e_hat, w_norm, diag


def compute_unmapped_fault_posterior(
    prob_2d: np.ndarray,
    propensity_2d: np.ndarray,
    footprint: np.ndarray,
    lambda_e: float = 0.65,
) -> np.ndarray:
    """Compute exact Bekker-Davis SAR unmapped-fault posterior `P(Y=1 | S=0, x)`."""
    fp = np.asarray(footprint, dtype=bool)
    p = np.clip(np.nan_to_num(np.asarray(prob_2d, dtype=np.float64), nan=0.0), 0.0, 1.0 - 1e-6)
    e = np.clip(np.nan_to_num(np.asarray(propensity_2d, dtype=np.float64), nan=0.0), 0.0, 0.95)
    le = np.clip(float(lambda_e) * e, 0.0, 0.92)
    num = (1.0 - le) * p
    den = np.maximum(1.0 - le * p, 1e-6)
    post = np.clip(num / den, 0.0, 1.0).astype(np.float32)
    post[~fp] = 0.0
    return post


def fit_predict_specialist_cwgr(
    *,
    blocks: Sequence[tuple[np.ndarray, Sequence[int]]],
    hard_neg_cols_in_stack: Sequence[int],
    visible_faults: np.ndarray,
    train_domain: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    pos_weights_fp: np.ndarray | None = None,
    topology_mode: bool = False,
    neg_pos_ratio: float = 3.65,
    hard_neg_frac: float = 0.35,
    chunk_size: int = 350_000,
    predict_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, float | int | bool]]:
    """Footprint-indexed HGB-deep + HGB-shallow + Logistic specialist with optional SAR weights.

    Preserves safe damage-zone negative exclusion (`d_vis > 3.5 px`), specialist-internal
    hard-negative mining, and training-domain reference-odds calibration (`c0 = 12.0`).
    """
    rng = np.random.default_rng(seed)
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_faults, dtype=bool) & np.asarray(train_domain, dtype=bool) & fp
    dom = np.asarray(train_domain, dtype=bool) & fp

    d_vis = ndi.distance_transform_edt(~vis)
    pos_fp = vis[fp]
    neg_fp = dom[fp] & (~vis[fp]) & (d_vis[fp] > 3.5)
    pos_idx = np.flatnonzero(pos_fp)
    neg_pool = np.flatnonzero(neg_fp)
    if pos_idx.size == 0 or neg_pool.size == 0:
        raise ValueError("Specialist training requires non-empty positive and safe-negative sets")

    active_blocks = [(arr, list(cols)) for arr, cols in blocks if len(cols) > 0]
    target_neg = min(int(round(float(neg_pos_ratio) * pos_idx.size)), neg_pool.size)
    if target_neg < neg_pool.size and len(hard_neg_cols_in_stack) > 0:
        n_hard_target = int(round(float(hard_neg_frac) * target_neg))
        n_rand_target = target_neg - n_hard_target
        col_cursor = 0
        hard_mask = np.zeros(neg_pool.size, dtype=bool)
        hard_set = {int(c) for c in hard_neg_cols_in_stack}
        for arr, cols in active_blocks:
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

    sample_weight = None
    pos_mass = float(pos_idx.size)
    if pos_weights_fp is not None:
        pw = np.asarray(pos_weights_fp[pos_idx], dtype=np.float32)
        pos_mass = float(pw.sum())
        sample_weight = np.concatenate([pw, np.ones(neg_idx.size, dtype=np.float32)])

    X_train = np.hstack(
        [np.asarray(arr[train_idx][:, cols], dtype=np.float32) for arr, cols in active_blocks]
    )
    np.nan_to_num(X_train, copy=False, nan=0.0, posinf=0.0, neginf=0.0)

    if topology_mode:
        hgb_deep = HistGradientBoostingClassifier(
            learning_rate=0.050,
            max_iter=150,
            max_leaf_nodes=25,
            min_samples_leaf=110,
            l2_regularization=5.0,
            early_stopping=False,
            random_state=seed,
        ).fit(X_train, y_train, sample_weight=sample_weight)
        hgb_shallow = HistGradientBoostingClassifier(
            learning_rate=0.045,
            max_iter=125,
            max_leaf_nodes=17,
            max_depth=5,
            min_samples_leaf=150,
            l2_regularization=8.0,
            early_stopping=False,
            random_state=seed + 19,
        ).fit(X_train, y_train, sample_weight=sample_weight)
        w1, w2, w3 = 0.42, 0.34, 0.24
    else:
        hgb_deep = HistGradientBoostingClassifier(
            learning_rate=0.055,
            max_iter=175,
            max_leaf_nodes=37,
            min_samples_leaf=75,
            l2_regularization=3.5,
            early_stopping=False,
            random_state=seed,
        ).fit(X_train, y_train, sample_weight=sample_weight)
        hgb_shallow = HistGradientBoostingClassifier(
            learning_rate=0.050,
            max_iter=145,
            max_leaf_nodes=23,
            max_depth=6,
            min_samples_leaf=115,
            l2_regularization=6.8,
            early_stopping=False,
            random_state=seed + 19,
        ).fit(X_train, y_train, sample_weight=sample_weight)
        w1, w2, w3 = 0.50, 0.32, 0.18

    scaler = StandardScaler()
    X_sc = np.clip(scaler.fit_transform(X_train), -6.0, 6.0)
    lr = LogisticRegression(C=0.20, max_iter=300, random_state=seed + 37)
    lr.fit(X_sc, y_train, sample_weight=sample_weight)

    n_features = int(X_train.shape[1])
    del X_train, X_sc, y_train
    gc.collect()

    n_fp = int(fp.sum())
    if predict_mask is None:
        pred_fp = np.empty(n_fp, dtype=np.float32)
        for start in range(0, n_fp, chunk_size):
            end = min(start + chunk_size, n_fp)
            Xc = np.hstack(
                [np.asarray(arr[start:end][:, cols], dtype=np.float32) for arr, cols in active_blocks]
            )
            np.nan_to_num(Xc, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
            p1 = hgb_deep.predict_proba(Xc)[:, 1]
            p2 = hgb_shallow.predict_proba(Xc)[:, 1]
            p3 = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
            pred_fp[start:end] = (w1 * p1 + w2 * p2 + w3 * p3).astype(np.float32)
            del Xc, p1, p2, p3
    else:
        pred_fp = np.zeros(n_fp, dtype=np.float32)
        eval_rows = np.flatnonzero(np.asarray(predict_mask, dtype=bool)[fp])
        for start in range(0, eval_rows.size, chunk_size):
            rows_chunk = eval_rows[start : start + chunk_size]
            Xc = np.hstack(
                [np.asarray(arr[rows_chunk][:, cols], dtype=np.float32) for arr, cols in active_blocks]
            )
            np.nan_to_num(Xc, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
            p1 = hgb_deep.predict_proba(Xc)[:, 1]
            p2 = hgb_shallow.predict_proba(Xc)[:, 1]
            p3 = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1]
            pred_fp[rows_chunk] = (w1 * p1 + w2 * p2 + w3 * p3).astype(np.float32)
            del Xc, p1, p2, p3

    raw_surf = np.zeros(fp.shape, dtype=np.float32)
    raw_surf[fp] = pred_fp
    pi_vis = float(pos_idx.size) / float(pos_idx.size + neg_pool.size)
    pi_samp = float(pos_mass) / float(pos_mass + neg_idx.size)
    cal_surf = calibrate_reference_odds_surface(
        raw_surf,
        fp,
        pi_vis_train=pi_vis,
        pi_sample_weighted=pi_samp,
        c0_multiplier=12.0,
    )
    if predict_mask is not None:
        cal_surf[~np.asarray(predict_mask, dtype=bool)] = 0.0
    del raw_surf, pred_fp
    gc.collect()

    return cal_surf, {
        "pi_vis_train": round(pi_vis, 8),
        "pi_sample_weighted": round(pi_samp, 8),
        "n_pos_train": int(pos_idx.size),
        "n_neg_train": int(neg_idx.size),
        "n_features": n_features,
        "weighted": bool(pos_weights_fp is not None),
        "topology_mode": bool(topology_mode),
    }


def pool_tri_specialists_logit(
    p_full_2d: np.ndarray,
    p_sub_2d: np.ndarray,
    p_topo_2d: np.ndarray,
    p_s1_2d: np.ndarray,
    footprint: np.ndarray,
    w_full: float = 0.44,
    w_sub: float = 0.22,
    w_topo: float = 0.20,
    w_s1: float = 0.14,
    crest_fp: np.ndarray | None = None,
    crest_gain: float = 0.16,
) -> np.ndarray:
    """Combine Full, Pure-Subsurface, Topology, and Stage-1 specialists in log-odds space."""
    fp = np.asarray(footprint, dtype=bool)
    eps = 1e-5
    lf = logit(np.clip(np.nan_to_num(p_full_2d, nan=eps), eps, 1.0 - eps))
    ls = logit(np.clip(np.nan_to_num(p_sub_2d, nan=eps), eps, 1.0 - eps))
    lt = logit(np.clip(np.nan_to_num(p_topo_2d, nan=eps), eps, 1.0 - eps))
    l1 = logit(np.clip(np.nan_to_num(p_s1_2d, nan=eps), eps, 1.0 - eps))
    w_tot = float(w_full + w_sub + w_topo + w_s1)
    l_pool = (float(w_full) * lf + float(w_sub) * ls + float(w_topo) * lt + float(w_s1) * l1) / max(
        w_tot, 1e-6
    )
    if crest_fp is not None and float(crest_gain) != 0.0:
        crest_2d = np.zeros(fp.shape, dtype=np.float32)
        crest_2d[fp] = np.clip(np.asarray(crest_fp, dtype=np.float32), 0.0, 1.0)
        l_pool = l_pool + float(crest_gain) * (crest_2d - 0.30)
    comb = expit(np.clip(l_pool, -18.0, 18.0)).astype(np.float32)
    comb[~fp] = 0.0
    return comb


def compute_fold_area_quotas(
    folds: Sequence[dict],
    footprint: np.ndarray,
    total_budget: int = 37_654,
) -> list[int]:
    """Allocate `total_budget` across folds strictly proportional to quadrant footprint area (`IR-91-S18-02`)."""
    fp = np.asarray(footprint, dtype=bool)
    counts = [int((np.asarray(f["region"], dtype=bool) & fp).sum()) for f in folds]
    tot = sum(counts)
    if tot <= 0:
        raise ValueError("Empty footprint in compute_fold_area_quotas.")
    exact = [total_budget * (c / float(tot)) for c in counts]
    floors = [int(np.floor(x)) for x in exact]
    rem = int(total_budget - sum(floors))
    order = sorted(
        range(len(folds)), key=lambda i: (exact[i] - floors[i], counts[i]), reverse=True
    )
    for idx in order[:rem]:
        floors[idx] += 1
    assert sum(floors) == int(total_budget)
    return floors


def emit_cwgr_submodular_skeleton(
    surface: np.ndarray,
    visible_catalogue: np.ndarray,
    footprint: np.ndarray,
    *,
    budget: int = 37_654,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
    gamma: float = 1.55,
    pool_multiplier: int = 12,
) -> np.ndarray:
    """Rotation-invariant centerline-anchored 300-m submodular DTI dot emitter (`S18-CWGR`).

    Eliminates two defects found in `S17-CPAD`'s `emit_global_dots_submodular`:
      1. Replaces the 4-axis (`0/45/90/135 deg`) grid check — which penalized N15E Basin-and-Range
         and N32W Walker Lane oblique fault traces by `0.36x` — with 8-orientation steerable
         `G1/G2` crest localization directly on the probability surface.
      2. Concentrates submodular target mass (`gamma = 1.55` + steerable crest weighting) onto
         the 1-px fault axis so the 300-m (`R = 3 px`) triangular coverage kernel never drifts
         1-2 px into diffuse off-fault flanks while still preventing junction crowding.
    """
    import heapq
    import math
    from gems91 import mhtr_coda as MC

    h, w = surface.shape
    fp = np.asarray(footprint, dtype=bool)
    vis = np.asarray(visible_catalogue, dtype=bool) & fp
    elig = fp & (~vis) & (ndi.distance_transform_edt(~vis) > float(collar_px))

    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(
        np.float32
    )
    elig_vals = p[elig & (p > 0.0)]
    if elig_vals.size == 0 or budget <= 0:
        return np.zeros((h, w), dtype=np.float32)

    if elig_vals.size > budget * 14:
        keep_frac = min(0.26, max(float(budget * 14) / float(elig_vals.size), 0.05))
        p_floor = float(np.quantile(elig_vals, 1.0 - keep_frac))
    else:
        p_floor = 0.0

    q_p = steerable_g2h2_quadrature(
        p, fp, sigmas=(1.15,), n_angles=8, norm_sigma=7.0, crest_step_px=1.1, already_clean=True
    )
    ridge_mult = (np.float32(0.52) + np.float32(0.48) * q_p["crest"]) * (
        np.float32(0.70) + np.float32(0.30) * q_p["aniso"]
    )
    del q_p

    p_excess = np.maximum(p - np.float32(p_floor), 0.0)
    # Centerline-concentrated submodular target mass (zero on visible catalogue & outside footprint)
    weight = np.where(
        fp & (~vis),
        1000.0 * np.power(p_excess, np.float32(gamma)) * ridge_mult,
        0.0,
    ).astype(np.float32)

    # Anchor candidate ranking & center kernel peak so selected dot stays on ridge centerline
    cand_rank = (p * ridge_mult).astype(np.float32)

    elig_flat = np.flatnonzero(elig & (weight > 0))
    if elig_flat.size == 0:
        return np.zeros((h, w), dtype=np.float32)

    m_pool = min(elig_flat.size, max(int(budget) * int(pool_multiplier), int(budget) + 5_000))
    ranks_sub = cand_rank.ravel()[elig_flat]
    if elig_flat.size > m_pool:
        top_part = np.argpartition(-ranks_sub, m_pool - 1)[:m_pool]
        cand_flat = elig_flat[top_part]
    else:
        cand_flat = elig_flat

    yy, xx = np.mgrid[-3:4, -3:4]
    K = np.clip(1.0 - np.hypot(yy, xx) / 3.0, 0.0, None).astype(np.float32)
    # Add centerline impulse bonus at (0,0) so flank pixels never outscore the ridge axis
    K_anchor = K.copy()
    K_anchor[3, 3] = np.float32(2.35)
    nz_k = K_anchor > 0
    ky, kx, kv = yy[nz_k] + 3, xx[nz_k] + 3, K_anchor[nz_k]

    W_pad = np.pad(weight, 3, mode="constant", constant_values=0.0).astype(np.float32)
    cy = (cand_flat // w).astype(np.int32)
    cx = (cand_flat % w).astype(np.int32)
    cand_init = W_pad[cy[:, None] + ky[None, :], cx[:, None] + kx[None, :]] @ kv

    order = np.lexsort((cand_flat, -cand_init))
    cand_flat = cand_flat[order]
    cand_init = cand_init[order]
    cy = cy[order]
    cx = cx[order]

    cov_pad = np.zeros((h + 6, w + 6), dtype=np.float32)
    rad = int(math.ceil(min_spacing_px))
    oy, ox = np.mgrid[-rad : rad + 1, -rad : rad + 1]
    disk = np.hypot(oy, ox) < float(min_spacing_px)
    blocked = np.zeros((h + 2 * rad, w + 2 * rad), dtype=bool)
    out = np.zeros((h, w), dtype=np.float32)

    heap: list[tuple[float, int, int]] = [
        (-float(cand_init[i]), int(cand_flat[i]), i) for i in range(cand_flat.size)
    ]
    heapq.heapify(heap)

    picked = 0
    while picked < int(budget) and heap:
        neg_ub, f_idx, i = heapq.heappop(heap)
        if -neg_ub <= 0.0:
            break
        y, x = int(cy[i]), int(cx[i])
        if blocked[y + rad, x + rad]:
            continue
        c_view = cov_pad[y : y + 7, x : x + 7]
        gain = float(np.sum(W_pad[y : y + 7, x : x + 7] * np.maximum(K_anchor - c_view, 0.0)))
        if gain <= 0.0:
            continue
        if not heap or (-gain <= heap[0][0] + 1e-6):
            np.maximum(c_view, K_anchor, out=c_view)
            blocked[y : y + 2 * rad + 1, x : x + 2 * rad + 1] |= disk
            out[y, x] = 1.0
            picked += 1
        else:
            heapq.heappush(heap, (-gain, f_idx, i))

    return out


def emit_fold_quota_dots_submodular(
    prob_2d: np.ndarray,
    footprint: np.ndarray,
    visible_catalogue: np.ndarray,
    fold_region: np.ndarray,
    quota_dots: int,
    collar_px: float = 3.05,
    min_spacing_px: float = 3.05,
) -> np.ndarray:
    """Emit `quota_dots` binary dots restricted to `fold_region & footprint` (`IR-91-S18-02` control)."""
    fp_fold = np.asarray(footprint, dtype=bool) & np.asarray(fold_region, dtype=bool)
    surf_fold = np.where(fp_fold, np.asarray(prob_2d, dtype=np.float32), 0.0)
    return emit_cwgr_submodular_skeleton(
        surf_fold,
        visible_catalogue,
        fp_fold,
        budget=int(quota_dots),
        collar_px=float(collar_px),
        min_spacing_px=float(min_spacing_px),
    )
