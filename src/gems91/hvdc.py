"""Session 14 (`S14-HVDC`): Hydrothermal-Vent Plume Back-Projection, Playa/Basin
Deconfounding, Salem Tilt-Depth, Leak-Free En-Echelon Relay-Ramp Auto-Context,
and Self-Credit-Exact (`M`-Term) Continuous-Crest Dinkelbach Optimization.

Implements the three frozen pre-registered hypotheses in `docs/HYPOTHESES_S14.md`:
  - `H14-1` (`E1`): Up-gradient (`+grad G_6(B12)`) enthalpy-weighted hydrothermal &
    blind geothermometric plume back-projection (`dist_known_fault_px` strictly banned),
    playa-deconfounded shallow conductivity (`B17 ~ (B12, B19)`), fold-safe Cenozoic
    basin-depth gravity stripping (`B13 ~ B15`), Salem et al. (2007) magnetic tilt-depth
    vs gravity basement ratio, multi-scale Frangi tubular vesselness, and corrected
    positive Ruhl et al. (2022) dependent earthquake swarm excess (`IR-91-S14-01`).
  - `H14-2` (`E2`): Leak-free 6-pair inner-OOF Two-Stage Structural Auto-Context
    capturing both collinear alluvial-wash bridges (`0.4-2.4 km`) and anti-symmetric
    en-echelon relay-ramp lateral step-overs (`250-500 m`, Faulds & Hinz Setting #1),
    plus conjugate Walker-Lane fault intersections (`Setting #3`).
  - `H14-3` (`E3`): Continuous structure-tensor gradient-normal crest localization
    (Steger 1998) paired with exact `M`-term self-credit `(1 - m_hat_j)` Dinkelbach
    fractional programming calibrated strictly on each fold's training domain.
"""

from __future__ import annotations

import csv
import gc
import heapq
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from gems91 import dd_vtc_pu as DD
from gems91 import ptha as PTHA

HVDC_CACHE_VERSION = "s14_hvdc_features_v1"

HVDC_FEATURE_NAMES: list[str] = [
    # Group 1: Up-gradient hydrothermal & blind geothermometric feeder back-projection (6)
    "hvdc_therm_enthalpy_local",
    "hvdc_blind_geotherm_excess",
    "hvdc_upgrad_feeder_1p2km",
    "hvdc_upgrad_feeder_2p8km",
    "hvdc_feeder_step_coupling",
    "hvdc_hydro_mag_destruct_clay",
    # Group 2: Playa/basin deconfounded gradients & Salem intrabasinal tilt-depth (6)
    "hvdc_cond_playa_res_grad",
    "hvdc_grav_res_step_600m",
    "hvdc_salem_tilt_depth_log",
    "hvdc_intrabasin_mag_ratio",
    "hvdc_geodawn_drape_diff",
    "hvdc_geodawn_drape_grad",
    # Group 3: Multi-scale Frangi tubular vesselness & corrected Ruhl swarm conduit (6)
    "hvdc_frangi_subsurface_joint",
    "hvdc_frangi_topo_multiscale",
    "hvdc_swarm_dep_log",
    "hvdc_swarm_clustering_excess",
    "hvdc_swarm_transtension_conduit",
    "hvdc_remanent_rtp_phase_disc",
]

FOLD_DECONFOUND_NAMES: list[str] = [
    "hvdc_cond_playa_residual_fold",
    "hvdc_grav_depth_residual_fold",
]

STAGE2_CONTEXT_NAMES: list[str] = [
    "ctx_s1_prob",
    "ctx_s1_logit",
    "ctx_collinear_max_1p2km",
    "ctx_wash_bridge_short",
    "ctx_wash_bridge_long",
    "ctx_relay_ramp_250m",
    "ctx_relay_ramp_500m",
    "ctx_cross_strike_contrast",
    "ctx_strike_anisotropy",
    "ctx_gap_infill_surplus",
    "ctx_horst_intersection",
    "ctx_regional_corridor_3km",
]

# Surface topographic feature names excluded ONLY inside Model C (Topography-Blind
# Subsurface, Hydrothermal & Swarm Specialist) so eroded scarps do not veto buried faults.
TOPO_SURFACE_FEATURE_NAMES: frozenset[str] = frozenset({
    "b12_det_elev",
    "b19_det_elev_slope",
    "e1_lrm_300m",
    "e1_lrm_1km",
    "e1_topo_openness_lap",
    "e1_slope_hp_600m",
    "e1_topo_coherence",
    "e2_gdr_upslope_conduit_align",
    "e2_piedmont_concealment_idx",
    "s11_topo_grav_cos_align",
    "s11_topo_profile_curv",
    "s11_ctx1km_topo_slope",
    "ptha_step_elev_abs",
    "ptha_step_normal_concordance",
    "hvdc_frangi_topo_multiscale",
})


def _robust_z_pos(arr: np.ndarray, footprint: np.ndarray) -> np.ndarray:
    return np.maximum(DD._robust_z(arr, footprint), 0.0).astype(np.float32)


def _frangi_tubular_2d(
    field: np.ndarray,
    sigma: float,
    *,
    beta: float = 0.55,
    footprint: np.ndarray,
) -> np.ndarray:
    """2-D Frangi (1998) Hessian tubular ridge/step vesselness suppressing circular blobs."""
    sm = ndi.gaussian_filter(field.astype(np.float32), sigma=sigma)
    scale2 = float(sigma * sigma)
    gy = ndi.sobel(sm, axis=0) / 8.0
    gx = ndi.sobel(sm, axis=1) / 8.0
    hyy = (ndi.sobel(gy, axis=0) / 8.0) * scale2
    hxx = (ndi.sobel(gx, axis=1) / 8.0) * scale2
    hxy = (0.5 * (ndi.sobel(gy, axis=1) + ndi.sobel(gx, axis=0)) / 8.0) * scale2
    del sm, gy, gx

    tr = hxx + hyy
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    lam1 = 0.5 * (tr + disc)
    lam2 = 0.5 * (tr - disc)
    swap = np.abs(lam2) > np.abs(lam1)
    l_dom = np.where(swap, lam2, lam1)
    l_sub = np.where(swap, lam1, lam2)
    del hxx, hyy, hxy, tr, disc, lam1, lam2, swap

    rb = np.abs(l_sub) / (np.abs(l_dom) + 1e-6)
    s2 = l_dom * l_dom + l_sub * l_sub
    s_med = float(np.median(s2[footprint])) + 1e-6
    c2 = 2.0 * s_med
    vess = np.exp(-(rb * rb) / (2.0 * beta * beta)) * (1.0 - np.exp(-s2 / c2))
    vess = np.where(footprint, vess, 0.0).astype(np.float32)
    return vess


def extract_gdr_enthalpy_rasters(
    gdr_csv: Path,
    shape: tuple[int, int],
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Build continuous enthalpy-weighted hydrothermal & blind geothermometric rasters.

    Strictly enforces zero label leakage: `dist_known_fault_px` is explicitly checked
    and NEVER read; only physical temperature / chemical geothermometry columns are parsed.
    """
    h, w = shape
    enthalpy_grid = np.zeros((h, w), dtype=np.float32)
    blind_grid = np.zeros((h, w), dtype=np.float32)

    banned_col = "dist_known_fault_px"
    allowed_cols = {
        "row",
        "col",
        "thermalclass",
        "temp_c",
        "geothermquartz_c",
        "geothermchalc_c",
        "geothermcat_c",
    }

    def _fval(s: str | None) -> float:
        if not s:
            return float("nan")
        s = s.strip()
        if not s or s.lower() in {"nan", "none", "null", "-999", "-9999"}:
            return float("nan")
        try:
            v = float(s)
            return v if (-10.0 < v < 400.0) else float("nan")
        except ValueError:
            return float("nan")

    with gdr_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        assert reader.fieldnames is not None
        assert banned_col not in allowed_cols
        for rec in reader:
            try:
                r = int(float(rec["row"]))
                c = int(float(rec["col"]))
            except (KeyError, ValueError, TypeError):
                continue
            if not (0 <= r < h and 0 <= c < w) or not footprint[r, c]:
                continue

            t_cls = (rec.get("thermalclass") or "").strip().lower()
            is_hw = ("hot" in t_cls) or ("warm" in t_cls)
            t_meas = _fval(rec.get("temp_c"))
            t_qtz = _fval(rec.get("geothermquartz_c"))
            t_chl = _fval(rec.get("geothermchalc_c"))
            t_cat = _fval(rec.get("geothermcat_c"))

            geotherm_vals = [v for v in (t_qtz, t_chl, t_cat) if np.isfinite(v)]
            t_geo = max(geotherm_vals) if geotherm_vals else float("nan")
            all_vals = [v for v in (t_meas, t_geo) if np.isfinite(v)]
            if is_hw and not all_vals:
                t_eff = 65.0
            elif all_vals:
                t_eff = max(all_vals)
            else:
                continue

            # Normalized reservoir enthalpy excess above 40 C ambient meteoric baseline
            e_score = float(np.clip((t_eff - 40.0) / 140.0, 0.0, 2.2))
            if is_hw:
                e_score = max(e_score, 0.30)
            if e_score > enthalpy_grid[r, c]:
                enthalpy_grid[r, c] = e_score

            # Blind cryptic outflow anomaly: non-Hot/Warm well carrying >= 80 C reservoir signature
            if (not is_hw) and np.isfinite(t_geo) and t_geo >= 80.0:
                b_score = float(np.clip((t_geo - 75.0) / 115.0, 0.0, 2.2))
                if b_score > blind_grid[r, c]:
                    blind_grid[r, c] = b_score

    return enthalpy_grid, blind_grid


def fit_fold_safe_deconfounded_residuals(
    X_static: np.ndarray,
    footprint: np.ndarray,
    train_valid_mask_2d: np.ndarray,
) -> np.ndarray:
    """Fit label-free playa (`B17 ~ B12, B19`) and basin (`B13 ~ B15`) regressions
    strictly on `train_valid_mask_2d` (excluding any held-out test quadrant) and
    return `(N_fp, 2)` float32 residuals across the footprint.
    """
    tr_fp = train_valid_mask_2d[footprint]
    b12 = X_static[:, 11].astype(np.float64)  # detrended_elevation
    b13 = X_static[:, 12].astype(np.float64)  # iso_grav_anom
    b15 = np.maximum(X_static[:, 14].astype(np.float64), 0.0)  # depth_to_base_surf
    b17 = X_static[:, 16].astype(np.float64)  # cond_surf
    b19 = np.maximum(X_static[:, 18].astype(np.float64), 0.0)  # slope

    # Subsample every 8th training pixel (~480k pixels) for exact conditioned OLS
    idx_tr = np.flatnonzero(tr_fp)[::8]

    # 1. Closed-basin evaporite playa stripping: B17 ~ [1, B12_s, B12_s^2, log1p(B19), is_flat_basin]
    b12_s = b12 / 250.0
    ls19 = np.log1p(b19)
    flat_basin = np.exp(-np.maximum(b12 + 120.0, 0.0) / 120.0) * np.exp(-b19 / 1.5)
    A_playa = np.column_stack([
        np.ones_like(b12_s[idx_tr]),
        b12_s[idx_tr],
        b12_s[idx_tr] ** 2,
        ls19[idx_tr],
        flat_basin[idx_tr],
    ])
    coef_playa, *_ = np.linalg.lstsq(A_playa, b17[idx_tr], rcond=None)
    pred_playa = (
        coef_playa[0]
        + coef_playa[1] * b12_s
        + coef_playa[2] * (b12_s ** 2)
        + coef_playa[3] * ls19
        + coef_playa[4] * flat_basin
    )
    res_cond = (b17 - pred_playa).astype(np.float32)

    # 2. Cenozoic basin-fill Bouguer/isostatic gravity stripping: B13 ~ [1, H, sqrt(H), log1p(H)]
    h_km = b15 / 1000.0
    sq_h = np.sqrt(h_km)
    lg_h = np.log1p(b15 / 200.0)
    A_grav = np.column_stack([
        np.ones_like(h_km[idx_tr]),
        h_km[idx_tr],
        sq_h[idx_tr],
        lg_h[idx_tr],
    ])
    coef_grav, *_ = np.linalg.lstsq(A_grav, b13[idx_tr], rcond=None)
    pred_grav = (
        coef_grav[0]
        + coef_grav[1] * h_km
        + coef_grav[2] * sq_h
        + coef_grav[3] * lg_h
    )
    res_grav = (b13 - pred_grav).astype(np.float32)

    out = np.empty((X_static.shape[0], 2), dtype=np.float32)
    out[:, 0] = res_cond
    out[:, 1] = res_grav
    return out


def build_or_load_hvdc_feature_memmap(
    *,
    features_tif: Path,
    gdr_csv: Path,
    footprint: np.ndarray,
    cache_dir: Path,
) -> tuple[np.memmap, list[str], Path]:
    """Build or open disk-backed `(N_fp, 18)` float32 memmap for `H14-1` (`S14-HVDC`)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    dat_path = cache_dir / f"{HVDC_CACHE_VERSION}.dat"
    meta_path = cache_dir / f"{HVDC_CACHE_VERSION}.json"
    n_fp = int(footprint.sum())
    n_cols = len(HVDC_FEATURE_NAMES)
    expected_bytes = n_fp * n_cols * 4

    if dat_path.is_file() and meta_path.is_file() and dat_path.stat().st_size == expected_bytes:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("feature_names") == HVDC_FEATURE_NAMES and meta.get("n_fp") == n_fp:
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(HVDC_FEATURE_NAMES), dat_path

    h, w = footprint.shape
    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))

    with rasterio.open(features_tif) as src:
        b01_mag = DD._clean_band_edt(src.read(1), footprint)
        b02_rtp = DD._clean_band_edt(src.read(2), footprint)
        b03_thg = np.maximum(DD._clean_band_edt(src.read(3), footprint), 0.0)
        b04_str = np.maximum(DD._clean_band_edt(src.read(4), footprint), 0.0)
        b06_tc = np.maximum(DD._clean_band_edt(src.read(6), footprint), 0.0)
        b07_shr = np.maximum(DD._clean_band_edt(src.read(7), footprint), 0.0)
        b08_dil = DD._clean_band_edt(src.read(8), footprint)
        b09_tvg = DD._clean_band_edt(src.read(9), footprint)
        b10_deq = np.maximum(DD._clean_band_edt(src.read(10), footprint), 0.0)
        b11_gy = DD._clean_band_edt(src.read(11), footprint)
        b12_elev = DD._clean_band_edt(src.read(12), footprint)
        b13_grav = DD._clean_band_edt(src.read(13), footprint)
        b14_tmi = DD._clean_band_edt(src.read(14), footprint)
        b15_dbase = np.maximum(DD._clean_band_edt(src.read(15), footprint), 0.0)
        b16_ieq = np.maximum(DD._clean_band_edt(src.read(16), footprint), 0.0)
        b17_cond = DD._clean_band_edt(src.read(17), footprint)
        b18_ghg = np.maximum(DD._clean_band_edt(src.read(18), footprint), 0.0)
        b19_slp = np.maximum(DD._clean_band_edt(src.read(19), footprint), 0.0)

    # --- Principal geological strike normal (ny, nx) across RTP + gravity + DEM ---
    g1y = ndi.sobel(ndi.gaussian_filter(b02_rtp, sigma=2.0), axis=0) / 8.0
    g1x = ndi.sobel(ndi.gaussian_filter(b02_rtp, sigma=2.0), axis=1) / 8.0
    g2y = ndi.sobel(ndi.gaussian_filter(b13_grav, sigma=2.0), axis=0) / 8.0
    g2x = ndi.sobel(ndi.gaussian_filter(b13_grav, sigma=2.0), axis=1) / 8.0
    g3y = ndi.sobel(ndi.gaussian_filter(b12_elev, sigma=2.0), axis=0) / 8.0
    g3x = ndi.sobel(ndi.gaussian_filter(b12_elev, sigma=2.0), axis=1) / 8.0
    s1 = float(np.median(np.hypot(g1y, g1x)[footprint])) + 1e-5
    s2 = float(np.median(np.hypot(g2y, g2x)[footprint])) + 1e-5
    s3 = float(np.median(np.hypot(g3y, g3x)[footprint])) + 1e-5
    jyy = ndi.gaussian_filter((g1y / s1) ** 2 + (g2y / s2) ** 2 + (g3y / s3) ** 2, sigma=3.0)
    jxx = ndi.gaussian_filter((g1x / s1) ** 2 + (g2x / s2) ** 2 + (g3x / s3) ** 2, sigma=3.0)
    jxy = ndi.gaussian_filter((g1y * g1x) / (s1 * s1) + (g2y * g2x) / (s2 * s2) + (g3y * g3x) / (s3 * s3), sigma=3.0)
    phi_st = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    nx = np.cos(phi_st).astype(np.float32)
    ny = np.sin(phi_st).astype(np.float32)
    del g1y, g1x, g2y, g2x, g3y, g3x, jyy, jxx, jxy, phi_st

    # --- Group 1: Up-gradient hydrothermal & blind geothermometric back-projection ---
    enth_raw, blind_raw = extract_gdr_enthalpy_rasters(gdr_csv, (h, w), footprint)
    # Convert sparse well/spring enthalpy impulses into continuous advective plume intensity
    therm_local = (22.0 * ndi.gaussian_filter(enth_raw, sigma=5.0) + 8.0 * ndi.gaussian_filter(enth_raw, sigma=13.0)).astype(np.float32)
    blind_excess = (28.0 * ndi.gaussian_filter(blind_raw, sigma=7.0) + 10.0 * ndi.gaussian_filter(blind_raw, sigma=16.0)).astype(np.float32)
    del enth_raw, blind_raw

    # Regional hydraulic head gradient: fluids flow DOWN -grad(G_7(B12)) from feeder fault
    # at x to discharge well/spring at x_down = x - r * u_up. Thus pixel x is an UP-GRADIENT
    # feeder candidate when therm_plume(x - r * u_up) is elevated!
    elev_hyd = ndi.gaussian_filter(b12_elev, sigma=7.0)
    hy = ndi.sobel(elev_hyd, axis=0) / 8.0
    hx = ndi.sobel(elev_hyd, axis=1) / 8.0
    hmag = np.hypot(hy, hx)
    # Unit upslope vector u_up = +grad(elev_hyd) / ||grad||; x_down = x - r * u_up
    uy_up = (hy / (hmag + 0.35)).astype(np.float32)
    ux_up = (hx / (hmag + 0.35)).astype(np.float32)
    del elev_hyd, hy, hx, hmag

    plume_src = (therm_local + 0.85 * blind_excess).astype(np.float32)
    yy, xx = np.indices((h, w), dtype=np.float32)

    upgrad_1p2 = np.zeros((h, w), dtype=np.float32)
    for r_px, wt in ((6.0, 0.30), (12.0, 0.40), (18.0, 0.30)):
        cy = np.clip(yy - r_px * uy_up, 0.0, h - 1.0)
        cx = np.clip(xx - r_px * ux_up, 0.0, w - 1.0)
        upgrad_1p2 += wt * ndi.map_coordinates(plume_src, [cy, cx], order=1, mode="nearest")

    upgrad_2p8 = np.zeros((h, w), dtype=np.float32)
    for r_px, wt in ((18.0, 0.30), (25.0, 0.40), (32.0, 0.30)):
        cy = np.clip(yy - r_px * uy_up, 0.0, h - 1.0)
        cx = np.clip(xx - r_px * ux_up, 0.0, w - 1.0)
        upgrad_2p8 += wt * ndi.map_coordinates(plume_src, [cy, cx], order=1, mode="nearest")
    del uy_up, ux_up, plume_src

    # Subsurface structural step intensity (label-free gravity + TMI analytic signal + basement gradient)
    h_tmi_si = (b03_thg / 200.0).astype(np.float32)
    as_tmi = np.hypot(h_tmi_si, b09_tvg).astype(np.float32)
    db_grad = DD._grad_mag(np.log1p(b15_dbase), sigma=1.5)
    sub_step = (
        0.42 * _robust_z_pos(b18_ghg, footprint)
        + 0.33 * _robust_z_pos(as_tmi, footprint)
        + 0.25 * _robust_z_pos(db_grad, footprint)
    ).astype(np.float32)
    feeder_coupling = ((0.60 * upgrad_1p2 + 0.40 * upgrad_2p8) * np.log1p(sub_step)).astype(np.float32)
    del db_grad, sub_step

    # Local high-pass playa-deconfounded conductivity gradient & alteration dipole
    # (Strict per-fold global regression residuals are added separately via fit_fold_safe_deconfounded_residuals)
    cond_hp = (ndi.gaussian_filter(b17_cond, sigma=1.5) - ndi.gaussian_filter(b17_cond, sigma=14.0)).astype(np.float32)
    playa_penalty = (np.exp(-np.maximum(b12_elev + 120.0, 0.0) / 110.0) * np.exp(-b19_slp / 1.4)).astype(np.float32)
    cond_nonplaya = (cond_hp * (1.0 - 0.80 * playa_penalty)).astype(np.float32)
    cond_res_grad = DD._grad_mag(cond_nonplaya, sigma=1.4)

    drape_diff = (b14_tmi - b01_mag).astype(np.float32)
    drape_trough = (ndi.gaussian_filter(drape_diff, sigma=8.0) - ndi.gaussian_filter(drape_diff, sigma=1.3)).astype(np.float32)
    tc_edge = DD._grad_mag(b06_tc, sigma=1.5)
    hydro_alteration = (
        _robust_z_pos(drape_trough, footprint)
        * _robust_z_pos(cond_nonplaya, footprint)
        * (0.5 + 0.5 * np.tanh(0.5 * _robust_z_pos(tc_edge, footprint)))
    ).astype(np.float32)
    del cond_hp, playa_penalty, cond_nonplaya, drape_trough, tc_edge, b06_tc, b17_cond
    gc.collect()

    mm[:, 0] = therm_local[footprint]
    mm[:, 1] = blind_excess[footprint]
    mm[:, 2] = upgrad_1p2[footprint]
    mm[:, 3] = upgrad_2p8[footprint]
    mm[:, 4] = feeder_coupling[footprint]
    mm[:, 5] = hydro_alteration[footprint]
    del therm_local, blind_excess, upgrad_1p2, upgrad_2p8, feeder_coupling, hydro_alteration

    # --- Group 2: Local depth-stripped gravity cross-strike step & Salem (2007) tilt-depth ---
    # Local scale-separated gravity minus depth-scaled Bouguer slab (~0.012 mGal/m local contrast)
    grav_local_hp = (ndi.gaussian_filter(b13_grav, sigma=1.2) - ndi.gaussian_filter(b13_grav, sigma=15.0)).astype(np.float32)
    depth_local_hp = (ndi.gaussian_filter(b15_dbase, sigma=1.2) - ndi.gaussian_filter(b15_dbase, sigma=15.0)).astype(np.float32)
    grav_stripped_local = (grav_local_hp + 0.0085 * depth_local_hp).astype(np.float32)
    del grav_local_hp, depth_local_hp, b13_grav

    coords_p3 = np.array([np.clip(yy + 3.0 * ny, 0.0, h - 1.0), np.clip(xx + 3.0 * nx, 0.0, w - 1.0)])
    coords_m3 = np.array([np.clip(yy - 3.0 * ny, 0.0, h - 1.0), np.clip(xx - 3.0 * nx, 0.0, w - 1.0)])
    grav_res_step = np.abs(
        ndi.map_coordinates(grav_stripped_local, coords_p3, order=1, mode="nearest")
        - ndi.map_coordinates(grav_stripped_local, coords_m3, order=1, mode="nearest")
    ).astype(np.float32)
    del grav_stripped_local, coords_p3, coords_m3, yy, xx, ny, nx

    # Salem et al. (2007) Magnetic Tilt-Depth: z_c = 1 / ||grad_H(theta_TMI_SI)||_m
    tilt_tmi = np.arctan2(b09_tvg, h_tmi_si + 1e-4).astype(np.float32)
    tilt_sm = ndi.gaussian_filter(tilt_tmi, sigma=1.1)
    t_gy_m = (ndi.sobel(tilt_sm, axis=0) / 8.0) / 100.0
    t_gx_m = (ndi.sobel(tilt_sm, axis=1) / 8.0) / 100.0
    kh_tilt = np.hypot(t_gy_m, t_gx_m)
    z_salem_m = np.clip(1.0 / (kh_tilt + 1e-4), 25.0, 10000.0).astype(np.float32)
    salem_depth_log = np.log(z_salem_m).astype(np.float32)
    intrabasin_ratio = np.log((b15_dbase + 60.0) / (z_salem_m + 60.0)).astype(np.float32)
    del tilt_tmi, tilt_sm, t_gy_m, t_gx_m, kh_tilt, z_salem_m, h_tmi_si, b09_tvg, b15_dbase

    drape_grad = DD._grad_mag(drape_diff, sigma=1.2)
    remanent_disc = (DD._grad_mag(b14_tmi, sigma=1.2) - DD._grad_mag(b02_rtp, sigma=1.2)).astype(np.float32)
    del b01_mag, b02_rtp, b14_tmi, b03_thg
    gc.collect()

    mm[:, 6] = cond_res_grad[footprint]
    mm[:, 7] = grav_res_step[footprint]
    mm[:, 8] = salem_depth_log[footprint]
    mm[:, 9] = intrabasin_ratio[footprint]
    mm[:, 10] = drape_diff[footprint]
    mm[:, 11] = drape_grad[footprint]
    del cond_res_grad, grav_res_step, salem_depth_log, intrabasin_ratio, drape_diff, drape_grad

    # --- Group 3: Multi-scale Frangi tubular vesselness & corrected Ruhl swarm excess ---
    f_mag = _frangi_tubular_2d( np.log1p(as_tmi * 20.0), sigma=2.0, footprint=footprint)
    f_grav = _frangi_tubular_2d(np.log1p(b18_ghg), sigma=2.5, footprint=footprint)
    frangi_sub = np.maximum(f_mag, f_grav).astype(np.float32)
    del as_tmi, b18_ghg, b11_gy, f_mag, f_grav

    lslp = np.log1p(b19_slp).astype(np.float32)
    frangi_topo = np.maximum(
        _frangi_tubular_2d(lslp, sigma=1.5, footprint=footprint),
        _frangi_tubular_2d(lslp, sigma=3.5, footprint=footprint),
    ).astype(np.float32)
    del lslp, b19_slp, b12_elev

    # Fix IR-91-S14-01: Band 10 (`deq_n100a15`) is POSITIVE Dependent Earthquake Swarm Density!
    swarm_dep_log = np.log1p(b10_deq).astype(np.float32)
    ieq_log = np.log1p(b16_ieq).astype(np.float32)
    swarm_excess = (swarm_dep_log - 0.85 * ieq_log).astype(np.float32)
    transtension_drive = (np.maximum(b08_dil, 0.0) * b07_shr / (b04_str + 0.10)).astype(np.float32)
    swarm_conduit = (
        np.maximum(swarm_excess + 0.35 * swarm_dep_log, 0.0)
        * np.log1p(10.0 * np.maximum(transtension_drive, 0.0) + b07_shr)
    ).astype(np.float32)
    del b10_deq, b16_ieq, ieq_log, b04_str, b07_shr, b08_dil, transtension_drive

    mm[:, 12] = frangi_sub[footprint]
    mm[:, 13] = frangi_topo[footprint]
    mm[:, 14] = swarm_dep_log[footprint]
    mm[:, 15] = swarm_excess[footprint]
    mm[:, 16] = swarm_conduit[footprint]
    mm[:, 17] = remanent_disc[footprint]
    del frangi_sub, frangi_topo, swarm_dep_log, swarm_excess, swarm_conduit, remanent_disc

    mm.flush()
    gc.collect()
    meta_path.write_text(
        json.dumps(
            {
                "version": HVDC_CACHE_VERSION,
                "n_fp": n_fp,
                "n_cols": n_cols,
                "feature_names": HVDC_FEATURE_NAMES,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(HVDC_FEATURE_NAMES), dat_path


def compute_hvdc_relay_wash_context(
    stage1_cal_prob_2d: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Compute `(N_fp, 12)` `H14-2` Structural Auto-Context features from a 100%
    out-of-sample calibrated Stage-1 posterior map `stage1_cal_prob_2d`.

    Captures:
      - Two-sided collinear alluvial-wash bridges (`0.4-1.2 km` and `1.0-2.4 km`)
      - Anti-symmetric en-echelon relay-ramp step-overs (`+-250 m` and `+-500 m`,
        Faulds & Hinz Setting #1)
      - Conjugate/transverse fault intersections (`>= 67.5 deg` angular separation,
        Faulds & Hinz Setting #3)
      - Cross-strike sharpness contrast & concealed gap-infill surplus.
    """
    h, w = footprint.shape
    p = np.where(footprint, np.clip(stage1_cal_prob_2d, 0.0, 1.0), 0.0).astype(np.float32)
    p_sm = ndi.gaussian_filter(p, sigma=1.1).astype(np.float32)

    p_clip = np.clip(p, 1e-5, 1.0 - 1e-5)
    logit_p = np.log(p_clip / (1.0 - p_clip)).astype(np.float32)

    n_az = 8
    az_rads = [k * np.pi / n_az for k in range(n_az)]  # 0, 22.5, ..., 157.5 deg
    az_responses = np.empty((n_az, h, w), dtype=np.float32)

    best_collinear = np.zeros((h, w), dtype=np.float32)
    best_wash_short = np.zeros((h, w), dtype=np.float32)
    best_wash_long = np.zeros((h, w), dtype=np.float32)
    best_relay_250 = np.zeros((h, w), dtype=np.float32)
    best_relay_500 = np.zeros((h, w), dtype=np.float32)
    best_cross_contrast = np.full((h, w), -1.0, dtype=np.float32)

    def _shift_sample(arr: np.ndarray, dy: float, dx: float) -> np.ndarray:
        iy = int(round(dy))
        ix = int(round(dx))
        out = np.zeros_like(arr)
        y0_src = max(0, -iy)
        y1_src = min(h, h - iy)
        x0_src = max(0, -ix)
        x1_src = min(w, w - ix)
        out[y0_src + iy : y1_src + iy, x0_src + ix : x1_src + ix] = arr[y0_src:y1_src, x0_src:x1_src]
        return out

    for idx_a, theta in enumerate(az_rads):
        # Along-strike unit vector (sy, sx) and perpendicular normal (ny, nx)
        sy = float(np.cos(theta))
        sx = float(np.sin(theta))
        ny = -sx
        nx = sy

        # Short collinear half-rays (4..12 px = 0.4..1.2 km)
        r_pos_s = np.zeros((h, w), dtype=np.float32)
        r_neg_s = np.zeros((h, w), dtype=np.float32)
        for rad in (4.0, 6.0, 8.0, 10.0, 12.0):
            r_pos_s += 0.20 * _shift_sample(p_sm, rad * sy, rad * sx)
            r_neg_s += 0.20 * _shift_sample(p_sm, -rad * sy, -rad * sx)

        col_s = 0.5 * (r_pos_s + r_neg_s)
        az_responses[idx_a] = col_s
        best_collinear = np.maximum(best_collinear, col_s)
        best_wash_short = np.maximum(best_wash_short, np.sqrt(np.maximum(r_pos_s * r_neg_s, 0.0)))

        # Cross-strike flank suppression (3..6 px perpendicular)
        flank = 0.25 * (
            _shift_sample(p_sm, 3.5 * ny, 3.5 * nx)
            + _shift_sample(p_sm, -3.5 * ny, -3.5 * nx)
            + _shift_sample(p_sm, 6.0 * ny, 6.0 * nx)
            + _shift_sample(p_sm, -6.0 * ny, -6.0 * nx)
        )
        best_cross_contrast = np.maximum(best_cross_contrast, col_s - flank)
        del r_pos_s, r_neg_s, col_s, flank

        # Long alluvial-wash half-rays (10..22 px = 1.0..2.2 km)
        r_pos_l = np.zeros((h, w), dtype=np.float32)
        r_neg_l = np.zeros((h, w), dtype=np.float32)
        for rad in (10.0, 14.0, 18.0, 22.0):
            r_pos_l += 0.25 * _shift_sample(p_sm, rad * sy, rad * sx)
            r_neg_l += 0.25 * _shift_sample(p_sm, -rad * sy, -rad * sx)
        best_wash_long = np.maximum(best_wash_long, np.sqrt(np.maximum(r_pos_l * r_neg_l, 0.0)))
        del r_pos_l, r_neg_l

        # Anti-symmetric En-Echelon Relay-Ramp step-overs (+delta*n forward, -delta*n backward)
        for delta_px, target_buf in ((2.5, best_relay_250), (5.0, best_relay_500)):
            for sign in (-1.0, 1.0):
                dn = sign * delta_px
                e_pos = np.zeros((h, w), dtype=np.float32)
                e_neg = np.zeros((h, w), dtype=np.float32)
                for rad in (4.0, 7.0, 10.0):
                    e_pos += (1.0 / 3.0) * _shift_sample(p_sm, rad * sy + dn * ny, rad * sx + dn * nx)
                    e_neg += (1.0 / 3.0) * _shift_sample(p_sm, -rad * sy - dn * ny, -rad * sx - dn * nx)
                np.maximum(target_buf, np.sqrt(np.maximum(e_pos * e_neg, 0.0)), out=target_buf)
                del e_pos, e_neg

    mean_az = az_responses.mean(axis=0)
    std_az = az_responses.std(axis=0)
    anisotropy = ((best_collinear - mean_az) / (std_az + 1e-4)).astype(np.float32)
    del mean_az, std_az

    # Conjugate / transverse intersection (>= 67.5 deg => index distance >= 3 mod 8)
    horst_inter = np.zeros((h, w), dtype=np.float32)
    for i in range(n_az):
        for j in range(i + 3, n_az):
            if min(j - i, n_az - (j - i)) >= 3:
                np.maximum(
                    horst_inter,
                    np.sqrt(np.maximum(az_responses[i] * az_responses[j], 0.0)),
                    out=horst_inter,
                )
    del az_responses

    gap_surplus = (np.maximum(best_wash_long, best_relay_250) - p_sm).astype(np.float32)
    reg_corridor = (ndi.gaussian_filter(p, sigma=18.0) - ndi.gaussian_filter(p, sigma=45.0)).astype(np.float32)

    n_fp = int(footprint.sum())
    ctx = np.empty((n_fp, len(STAGE2_CONTEXT_NAMES)), dtype=np.float32)
    ctx[:, 0] = p[footprint]
    ctx[:, 1] = logit_p[footprint]
    ctx[:, 2] = best_collinear[footprint]
    ctx[:, 3] = best_wash_short[footprint]
    ctx[:, 4] = best_wash_long[footprint]
    ctx[:, 5] = best_relay_250[footprint]
    ctx[:, 6] = best_relay_500[footprint]
    ctx[:, 7] = best_cross_contrast[footprint]
    ctx[:, 8] = anisotropy[footprint]
    ctx[:, 9] = gap_surplus[footprint]
    ctx[:, 10] = horst_inter[footprint]
    ctx[:, 11] = reg_corridor[footprint]
    return ctx


def _dti_kernel_offsets() -> list[tuple[int, int, float]]:
    offs: list[tuple[int, int, float]] = []
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            dist = float(np.hypot(dy, dx))
            if dist < 3.0:
                offs.append((dy, dx, 1.0 - dist / 3.0))
    return offs


def _fit_and_predict_ensemble_core(
    *,
    blocks: list[tuple[np.ndarray, list[int], list[str]]],
    pred_blocks: list[tuple[np.ndarray, list[int], list[str]]] | None = None,
    predict_mask_2d: np.ndarray | None = None,
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    seed: int,
    neg_pos_ratio: float = 4.60,
) -> tuple[np.ndarray, dict[str, float], np.ndarray]:
    """Shared memory-bounded 3-expert trainer (`HGB-Full-ColSub` with `max_features=0.72`,
    `HGB-Subsurface` 100% Topography-Blind Specialist, and `L2-Logistic`) with invariant
    negative-to-positive ratio (`IR-91-SPAC-04`), playa/scarp/edge hard-negative
    mining, and exact Bayesian prior-shift posterior calibration.
    """
    rng = np.random.default_rng(seed)

    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]
    train_valid_fp = ~excl_fp

    pos_idx_all = np.flatnonzero(vis_fp & train_valid_fp)
    neg_idx_all = np.flatnonzero(train_valid_fp & (~vis_fp))

    n_pos_true = int(pos_idx_all.size)
    n_neg_true = int(neg_idx_all.size)
    pi_vis_train = float(n_pos_true) / float(max(n_pos_true + n_neg_true, 1))

    pos_idx = np.sort(pos_idx_all)
    target_neg = min(int(round(neg_pos_ratio * n_pos_true)), int(neg_idx_all.size))

    # Hard-negative mining matching S13-PTHA's regionally balanced scarp/gravity/magnetic pool
    X_stat_ref = blocks[0][0]
    X_s11_ref = blocks[1][0]
    X_ptha_ref = blocks[2][0]
    slp_v = np.asarray(X_stat_ref[:, 18], dtype=np.float32)[neg_idx_all]
    mhtr_v = np.asarray(X_s11_ref[:, 4], dtype=np.float32)[neg_idx_all]
    blakely_v = np.asarray(X_ptha_ref[:, 3], dtype=np.float32)[neg_idx_all]

    sl_thr = float(np.percentile(slp_v, 75.0))
    mh_thr = float(np.percentile(mhtr_v, 78.0))
    bl_thr = float(np.percentile(blakely_v, 80.0))
    hard_mask = (slp_v >= sl_thr) | (mhtr_v >= mh_thr) | (blakely_v >= bl_thr)
    del slp_v, mhtr_v, blakely_v

    hard_pool = neg_idx_all[hard_mask]
    easy_pool = neg_idx_all[~hard_mask]
    n_hard = min(target_neg // 2, int(hard_pool.size))
    n_easy = min(target_neg - n_hard, int(easy_pool.size))
    neg_hard = rng.choice(hard_pool, size=n_hard, replace=False) if hard_pool.size > n_hard else hard_pool
    neg_easy = rng.choice(easy_pool, size=n_easy, replace=False) if easy_pool.size > n_easy else easy_pool
    neg_idx = np.concatenate([np.sort(neg_hard), np.sort(neg_easy)])
    neg_weights = np.concatenate([
        np.full(neg_hard.size, 0.55, dtype=np.float32),
        np.full(neg_easy.size, 1.45, dtype=np.float32),
    ])
    del hard_pool, easy_pool, neg_hard, neg_easy, hard_mask

    train_idx = np.concatenate([pos_idx, neg_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(neg_idx.size, dtype=np.int32),
    ])
    w_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.float32),
        neg_weights,
    ])
    pi_sample_weighted = float(pos_idx.size) / float(max(w_train.sum(), 1.0))

    all_names: list[str] = []
    col_counts: list[int] = []
    for _, cols, names in blocks:
        all_names.extend(names)
        col_counts.append(len(cols))

    n_total = sum(col_counts)
    sub_keep = np.array([nm not in TOPO_SURFACE_FEATURE_NAMES for nm in all_names], dtype=bool)

    X_train = np.empty((train_idx.size, n_total), dtype=np.float32)
    offset = 0
    for arr, cols, _ in blocks:
        for j_loc, c_idx in enumerate(cols):
            X_train[:, offset + j_loc] = np.asarray(arr[:, c_idx], dtype=np.float32)[train_idx]
        offset += len(cols)
    del pos_idx, neg_idx, train_idx

    hgb_full = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.058,
        max_iter=215,
        max_leaf_nodes=41,
        min_samples_leaf=85,
        l2_regularization=3.0,
        max_bins=255,
        early_stopping=False,
        random_state=seed,
    )
    hgb_full.fit(X_train, y_train, sample_weight=w_train)

    hgb_sub = HistGradientBoostingClassifier(
        loss="log_loss",
        learning_rate=0.058,
        max_iter=195,
        max_leaf_nodes=35,
        min_samples_leaf=95,
        l2_regularization=4.0,
        max_bins=255,
        early_stopping=False,
        random_state=seed + 202,
    )
    hgb_sub.fit(X_train[:, sub_keep], y_train, sample_weight=w_train)

    med = np.median(X_train, axis=0)
    scale = np.median(np.abs(X_train - med), axis=0) * 1.4826 + 1e-5
    X_lr = np.clip((X_train - med) / scale, -6.0, 6.0)
    lr = LogisticRegression(C=0.25, max_iter=500, random_state=seed)
    lr.fit(X_lr, y_train, sample_weight=w_train)
    del X_train, X_lr, y_train, w_train
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.zeros(n_fp, dtype=np.float32)
    infer_blocks = blocks if pred_blocks is None else pred_blocks
    pred_fp_mask = None if predict_mask_2d is None else predict_mask_2d[footprint]

    chunk = 480_000
    buf = np.empty((chunk, n_total), dtype=np.float32)
    for s in range(0, n_fp, chunk):
        e = min(n_fp, s + chunk)
        if pred_fp_mask is not None and not pred_fp_mask[s:e].any():
            continue
        if pred_fp_mask is None or pred_fp_mask[s:e].all():
            m = e - s
            cur = buf[:m]
            offset = 0
            for arr, cols, _ in infer_blocks:
                w_b = len(cols)
                cur[:, offset : offset + w_b] = arr[s:e, cols]
                offset += w_b
            p_full = hgb_full.predict_proba(cur)[:, 1].astype(np.float32)
            p_sub = hgb_sub.predict_proba(cur[:, sub_keep])[:, 1].astype(np.float32)
            X_lrc = np.clip((cur - med) / scale, -6.0, 6.0)
            p_lr = lr.predict_proba(X_lrc)[:, 1].astype(np.float32)
            pred_fp[s:e] = 0.70 * p_full + 0.20 * p_sub + 0.10 * p_lr
            del X_lrc, p_full, p_sub, p_lr
        else:
            local_sel = np.flatnonzero(pred_fp_mask[s:e])
            m = int(local_sel.size)
            cur = buf[:m]
            offset = 0
            for arr, cols, _ in infer_blocks:
                w_b = len(cols)
                cur[:, offset : offset + w_b] = arr[s:e][local_sel][:, cols]
                offset += w_b
            p_full = hgb_full.predict_proba(cur)[:, 1].astype(np.float32)
            p_sub = hgb_sub.predict_proba(cur[:, sub_keep])[:, 1].astype(np.float32)
            X_lrc = np.clip((cur - med) / scale, -6.0, 6.0)
            p_lr = lr.predict_proba(X_lrc)[:, 1].astype(np.float32)
            pred_fp[s + local_sel] = 0.70 * p_full + 0.20 * p_sub + 0.10 * p_lr
            del X_lrc, p_full, p_sub, p_lr, local_sel

    del buf, hgb_full, hgb_sub, lr, pred_fp_mask
    gc.collect()

    raw_prob = np.zeros(footprint.shape, dtype=np.float32)
    raw_prob[footprint] = pred_fp
    cal_prob = PTHA.prior_shift_calibrate_surface(
        raw_prob,
        footprint,
        pi_true=pi_vis_train,
        pi_sample=pi_sample_weighted,
    )
    if predict_mask_2d is not None:
        cal_prob[~predict_mask_2d] = 0.0
    return raw_prob, {
        "pi_vis_train": round(pi_vis_train, 8),
        "pi_sample_weighted": round(pi_sample_weighted, 8),
        "n_pos_train_true": n_pos_true,
        "n_neg_train_true": n_neg_true,
        "n_features_total": n_total,
        "n_features_subsurface_specialist": int(sub_keep.sum()),
    }, cal_prob


def fit_and_predict_hvdc_stage1(
    *,
    X_static: np.ndarray,
    static_cols: list[int],
    static_names: list[str],
    X_s11: np.ndarray,
    s11_cols: list[int],
    s11_names: list[str],
    X_ptha: np.ndarray,
    ptha_cols: list[int],
    ptha_names: list[str],
    X_hvdc: np.ndarray,
    hvdc_cols: list[int],
    hvdc_names: list[str],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    predict_mask_2d: np.ndarray | None = None,
    include_global_ols_deconf: bool = False,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Fit `H14-1` Stage-1 ensemble. Returns `(raw_prob_2d, cal_prob_2d, cal_info)`."""
    blocks = [
        (X_static, static_cols, [static_names[i] for i in static_cols]),
        (X_s11, s11_cols, [s11_names[i] for i in s11_cols]),
        (X_ptha, ptha_cols, [ptha_names[i] for i in ptha_cols]),
        (X_hvdc, hvdc_cols, [hvdc_names[i] for i in hvdc_cols]),
    ]
    X_deconf = None
    if include_global_ols_deconf:
        train_valid_2d = footprint & (~exclude_mask)
        X_deconf = fit_fold_safe_deconfounded_residuals(X_static, footprint, train_valid_2d)
        blocks.append((X_deconf, [0, 1], list(FOLD_DECONFOUND_NAMES)))
    raw_prob, cal_info, cal_prob = _fit_and_predict_ensemble_core(
        blocks=blocks,
        predict_mask_2d=predict_mask_2d,
        visible_faults=visible_faults,
        exclude_mask=exclude_mask,
        footprint=footprint,
        seed=seed,
    )
    if X_deconf is not None:
        del X_deconf
    gc.collect()
    return raw_prob, cal_prob, cal_info


def fit_and_predict_hvdc_stage2(
    *,
    X_static: np.ndarray,
    static_cols: list[int],
    static_names: list[str],
    X_s11: np.ndarray,
    s11_cols: list[int],
    s11_names: list[str],
    X_ptha: np.ndarray,
    ptha_cols: list[int],
    ptha_names: list[str],
    X_hvdc: np.ndarray,
    hvdc_cols: list[int],
    hvdc_names: list[str],
    X_ctx_train: np.ndarray,
    X_ctx_pred: np.ndarray | None = None,
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    include_global_ols_deconf: bool = False,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Fit `H14-2` Stage-2 Relay-Ramp & Wash-Bridge Auto-Context ensemble on top
    of 100% out-of-sample Stage-1 training context `X_ctx_train` and evaluate on
    `X_ctx_pred` (or `X_ctx_train` if full-map).
    Returns `(raw_prob_2d, cal_prob_2d, cal_info)`.
    """
    ctx_cols = list(range(len(STAGE2_CONTEXT_NAMES)))
    base_blocks = [
        (X_static, static_cols, [static_names[i] for i in static_cols]),
        (X_s11, s11_cols, [s11_names[i] for i in s11_cols]),
        (X_ptha, ptha_cols, [ptha_names[i] for i in ptha_cols]),
        (X_hvdc, hvdc_cols, [hvdc_names[i] for i in hvdc_cols]),
    ]
    X_deconf = None
    if include_global_ols_deconf:
        train_valid_2d = footprint & (~exclude_mask)
        X_deconf = fit_fold_safe_deconfounded_residuals(X_static, footprint, train_valid_2d)
        base_blocks.append((X_deconf, [0, 1], list(FOLD_DECONFOUND_NAMES)))
    blocks = base_blocks + [(X_ctx_train, ctx_cols, list(STAGE2_CONTEXT_NAMES))]
    p_blocks = None if X_ctx_pred is None else (base_blocks + [(X_ctx_pred, ctx_cols, list(STAGE2_CONTEXT_NAMES))])
    raw_prob, cal_info, cal_prob = _fit_and_predict_ensemble_core(
        blocks=blocks,
        pred_blocks=p_blocks,
        visible_faults=visible_faults,
        exclude_mask=exclude_mask,
        footprint=footprint,
        seed=seed,
    )
    if X_deconf is not None:
        del X_deconf
    gc.collect()
    return raw_prob, cal_prob, cal_info


def build_hvdc_structural_crest_surface(
    ptha_crest: np.ndarray,
    X_hvdc: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Fuse `ptha_crest` with `H14-1` basin-stripped gravity step, draped GeoDAWN
    shallow magnetic gradient, subsurface Frangi vesselness, and feeder-step coupling
    without compressing `ptha_crest`'s dynamic range.
    """
    f_feeder = np.zeros(footprint.shape, dtype=np.float32)
    f_grav_step = np.zeros(footprint.shape, dtype=np.float32)
    f_drape_grad = np.zeros(footprint.shape, dtype=np.float32)
    f_frangi_sub = np.zeros(footprint.shape, dtype=np.float32)

    f_feeder[footprint] = X_hvdc[:, 4]      # hvdc_feeder_step_coupling
    f_grav_step[footprint] = X_hvdc[:, 7]   # hvdc_grav_res_step_600m
    f_drape_grad[footprint] = X_hvdc[:, 11] # hvdc_geodawn_drape_grad
    f_frangi_sub[footprint] = X_hvdc[:, 12] # hvdc_frangi_subsurface_joint

    def _pctl01(arr: np.ndarray) -> np.ndarray:
        vals = arr[footprint]
        p30 = float(np.percentile(vals, 30.0))
        p99 = float(np.percentile(vals, 99.0))
        out = np.clip((arr - p30) / (p99 - p30 + 1e-6), 0.0, 1.0)
        return np.where(footprint, out, 0.0).astype(np.float32)

    sub_boost = (
        0.38 * _pctl01(f_grav_step)
        + 0.30 * _pctl01(f_drape_grad)
        + 0.20 * _pctl01(f_frangi_sub)
        + 0.12 * _pctl01(f_feeder)
    ).astype(np.float32)
    c_hvdc = np.clip(0.84 * ptha_crest + 0.22 * np.maximum(sub_boost, ptha_crest * 0.70), 0.0, 1.0)
    return np.where(footprint, c_hvdc, 0.0).astype(np.float32)


def _continuous_steger_crest_mask(
    q_surf: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """`H14-3` Continuous gradient-normal cross-strike crest detector (Steger 1998).

    Evaluates bilinear cross-strike neighbors along the continuous structure-tensor
    normal `+-1.35 * n_hat` and `+-2.45 * n_hat` so N015-030E Basin & Range faults
    are localized without 4-axis grid staircasing, while preserving conjugate fault
    junctions where coherence drops (`coh < 0.18`).
    """
    h, w = q_surf.shape
    q_sm = ndi.gaussian_filter(q_surf.astype(np.float32), sigma=0.95)
    gy = ndi.sobel(q_sm, axis=0) / 8.0
    gx = ndi.sobel(q_sm, axis=1) / 8.0

    jyy = ndi.gaussian_filter(gy * gy, sigma=2.2)
    jxx = ndi.gaussian_filter(gx * gx, sigma=2.2)
    jxy = ndi.gaussian_filter(gy * gx, sigma=2.2)
    del gy, gx

    tr = jyy + jxx + 1e-10
    disc = np.hypot(jyy - jxx, 2.0 * jxy)
    coh = disc / tr
    # Principal gradient-normal eigenvector angle (perpendicular to ridge strike)
    phi = 0.5 * np.arctan2(2.0 * jxy, jxx - jyy)
    nx = np.cos(phi).astype(np.float32)
    ny = np.sin(phi).astype(np.float32)
    del jyy, jxx, jxy, tr, disc, phi

    yy, xx = np.indices((h, w), dtype=np.float32)
    q_p1 = ndi.map_coordinates(
        q_sm,
        [np.clip(yy + 1.35 * ny, 0.0, h - 1.0), np.clip(xx + 1.35 * nx, 0.0, w - 1.0)],
        order=1,
        mode="nearest",
    )
    q_m1 = ndi.map_coordinates(
        q_sm,
        [np.clip(yy - 1.35 * ny, 0.0, h - 1.0), np.clip(xx - 1.35 * nx, 0.0, w - 1.0)],
        order=1,
        mode="nearest",
    )
    q_p2 = ndi.map_coordinates(
        q_sm,
        [np.clip(yy + 2.45 * ny, 0.0, h - 1.0), np.clip(xx + 2.45 * nx, 0.0, w - 1.0)],
        order=1,
        mode="nearest",
    )
    q_m2 = ndi.map_coordinates(
        q_sm,
        [np.clip(yy - 2.45 * ny, 0.0, h - 1.0), np.clip(xx - 2.45 * nx, 0.0, w - 1.0)],
        order=1,
        mode="nearest",
    )
    del yy, xx, ny, nx

    # Strict cross-strike local maximum + strict prominence over +-245 m flanks
    steger_crest = (q_sm >= 0.995 * np.maximum(q_p1, q_m1)) & (q_sm > 0.515 * (q_p2 + q_m2))
    del q_p1, q_m1, q_p2, q_m2

    # At conjugate fault intersections (coh < 0.18), allow strict 2-of-4 1-D peak preservation
    c_ew = (q_sm[:, 1:-1] >= q_sm[:, :-2]) & (q_sm[:, 1:-1] >= q_sm[:, 2:])
    c_ns = (q_sm[1:-1, :] >= q_sm[:-2, :]) & (q_sm[1:-1, :] >= q_sm[2:, :])
    c_d1 = (q_sm[1:-1, 1:-1] >= q_sm[:-2, :-2]) & (q_sm[1:-1, 1:-1] >= q_sm[2:, 2:])
    c_d2 = (q_sm[1:-1, 1:-1] >= q_sm[:-2, 2:]) & (q_sm[1:-1, 1:-1] >= q_sm[2:, :-2])
    junc_count = np.zeros((h, w), dtype=np.int8)
    junc_count[:, 1:-1] += c_ew.astype(np.int8)
    junc_count[1:-1, :] += c_ns.astype(np.int8)
    junc_count[1:-1, 1:-1] += c_d1.astype(np.int8) + c_d2.astype(np.int8)
    junc_crest = (coh < 0.18) & (junc_count >= 2)

    return footprint & (steger_crest | junc_crest)


def build_hvdc_steger_expected_intensity(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    calibration_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    gamma: float = 1.18,
    crest_weight: float = 0.50,
    keep_corridor_frac: float = 0.16,
    concealed_pu_boost: float = 1.26,
    self_credit_scale: float = 0.85,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Build `H14-3` continuous-Steger-concentrated intensity `w(x)` AND pixelwise
    unmatched false-positive denominator cost `fp_cost(x) = 1.0 - m_hat(x)`.

    `q_floor` is calibrated strictly on `calibration_mask` (`train_eligible_mask`
    in OOF folds: zero test-quadrant peeking). Soft centerline concentration
    (`1.0` on continuous Steger normal crests vs `0.22` off-crest) focuses 300 m
    kernel integration onto `N015-030E` Great Basin fault centerlines without
    discarding sub-pixel digitization width.
    """
    pi_cal = PTHA.prior_shift_calibrate_surface(
        prob_2d, footprint, pi_true=pi_true, pi_sample=pi_sample
    )
    q = (pi_cal * (1.0 + np.float32(crest_weight) * crest_2d)).astype(np.float32)
    q[~footprint] = 0.0

    cal_vals = q[calibration_mask & (q > 0.0)]
    q_floor = float(np.quantile(cal_vals, 1.0 - keep_corridor_frac)) if cal_vals.size > 0 else 0.0

    is_steger_q = _continuous_steger_crest_mask(q, footprint)
    is_steger_crest = _continuous_steger_crest_mask(crest_2d, footprint)

    q_exc = np.maximum(q - np.float32(q_floor), 0.0)
    ridge_mult = np.where(is_steger_q, np.float32(1.0), np.float32(0.22))
    pu_mult = np.where(
        piedmont_mask & is_steger_crest,
        np.float32(concealed_pu_boost),
        np.float32(1.0),
    )

    w = (np.float32(1000.0) * (q_exc ** np.float32(gamma)) * ridge_mult * pu_mult).astype(np.float32)
    w[~footprint] = 0.0

    # Exact DTI M-term self-credit: expected kernel-weighted match m_hat(j) under
    # calibrated fault posterior pi_cal concentrated on continuous Steger crests.
    p_center = np.where(is_steger_q, pi_cal, 0.30 * pi_cal).astype(np.float32)
    p_pad = np.pad(p_center, 3, mode="constant", constant_values=0.0)
    h, w_dim = footprint.shape
    log_miss = np.zeros((h, w_dim), dtype=np.float32)
    for dy, dx, kw in _dti_kernel_offsets():
        sub = p_pad[3 + dy : 3 + dy + h, 3 + dx : 3 + dx + w_dim]
        p_hit = np.clip(self_credit_scale * sub * np.float32(kw), 0.0, 0.75)
        log_miss += np.log(1.0 - p_hit)
    m_hat = np.clip(1.0 - np.exp(log_miss), 0.0, 0.65).astype(np.float32)
    fp_cost = np.where(footprint, 1.0 - m_hat, 1.0).astype(np.float32)  # strictly in [0.35, 1.00]

    rank_s = (
        (q * np.where(is_steger_q, np.float32(1.18), np.float32(0.82)) * pu_mult) / fp_cost
    ).astype(np.float32)
    return w, fp_cost, rank_s, q_floor


def _lazy_greedy_self_credit_select(
    w_surf: np.ndarray,
    fp_cost_2d: np.ndarray,
    cand_mask: np.ndarray,
    *,
    rank_surf: np.ndarray | None = None,
    max_dots: int,
    min_ratio_threshold: float = 0.0,
    min_spacing_px: float = 2.50,
    pool_mult: int = 10,
    min_pool: int = 60_000,
) -> tuple[np.ndarray, float, float]:
    """Exact lazy-greedy submodular selector ranked by marginal Dinkelbach surplus
    ratio `rho(j | S) = Delta_T(j | S) / (1 - m_hat_j)`.

    Because `1 - m_hat_j >= 0.35 > 0` depends only on `j` (not `S`), `rho(j | S)` is
    monotone non-increasing in `S`, preserving exact Minoux lazy-greedy optimality.
    Returns `(dots_2d, last_ratio, mean_m_hat)`.
    """
    h, w = w_surf.shape
    out = np.zeros((h, w), dtype=np.float32)
    if max_dots <= 0 or not cand_mask.any():
        return out, 0.0, 0.0

    r_surf = w_surf if rank_surf is None else rank_surf
    cand_r, cand_c = np.nonzero(cand_mask & (w_surf > 0.0))
    if cand_r.size == 0:
        return out, 0.0, 0.0

    cand_s = r_surf[cand_r, cand_c]
    pool_k = min(cand_r.size, max(max_dots * pool_mult, min_pool))
    if cand_r.size > pool_k:
        top_idx = np.argpartition(cand_s, -pool_k)[-pool_k:]
        cand_r = cand_r[top_idx]
        cand_c = cand_c[top_idx]

    offs = _dti_kernel_offsets()
    sp_r = int(np.ceil(min_spacing_px))
    sp_offs = [
        (dy, dx)
        for dy in range(-sp_r, sp_r + 1)
        for dx in range(-sp_r, sp_r + 1)
        if float(np.hypot(dy, dx)) < min_spacing_px
    ]

    pad = max(3, sp_r + 1)
    w_pad = np.pad(w_surf, pad, mode="constant", constant_values=0.0)
    cov_pad = np.zeros_like(w_pad, dtype=np.float32)
    blocked_pad = np.zeros(w_pad.shape, dtype=bool)

    cr_p = cand_r + pad
    cc_p = cand_c + pad
    fpc = np.maximum(fp_cost_2d[cand_r, cand_c], 0.35).astype(np.float32)

    init_gains = np.zeros(cr_p.size, dtype=np.float32)
    for dy, dx, kw in offs:
        init_gains += w_pad[cr_p + dy, cc_p + dx] * np.float32(kw)
    init_ratios = init_gains / fpc

    if min_ratio_threshold > 0.0:
        keep = init_ratios >= np.float32(min_ratio_threshold)
        cr_p = cr_p[keep]
        cc_p = cc_p[keep]
        fpc = fpc[keep]
        init_ratios = init_ratios[keep]
        if cr_p.size == 0:
            return out, 0.0, 0.0

    heap: list[tuple[float, int, int, float]] = [
        (-float(init_ratios[i]), int(cr_p[i]), int(cc_p[i]), float(fpc[i]))
        for i in range(cr_p.size)
    ]
    heapq.heapify(heap)

    selected = 0
    last_ratio = 0.0
    fp_sum = 0.0
    while selected < max_dots and heap:
        neg_ub, rp, cp, c_fp = heapq.heappop(heap)
        if blocked_pad[rp, cp]:
            continue
        ub = -neg_ub
        if ub < min_ratio_threshold:
            break

        dt_gain = 0.0
        for dy, dx, kw in offs:
            cur_c = float(cov_pad[rp + dy, cp + dx])
            if kw > cur_c:
                dt_gain += float(w_pad[rp + dy, cp + dx]) * (kw - cur_c)

        cur_ratio = dt_gain / c_fp
        if cur_ratio < min_ratio_threshold:
            continue

        next_ub = -heap[0][0] if heap else -1.0
        if cur_ratio >= next_ub * 0.996:
            out[rp - pad, cp - pad] = 1.0
            last_ratio = cur_ratio
            fp_sum += c_fp
            for dy, dx, kw in offs:
                if kw > cov_pad[rp + dy, cp + dx]:
                    cov_pad[rp + dy, cp + dx] = kw
            for dy, dx in sp_offs:
                blocked_pad[rp + dy, cp + dx] = True
            selected += 1
        else:
            heapq.heappush(heap, (-cur_ratio, rp, cp, c_fp))

    mean_m_hat = float(1.0 - fp_sum / max(selected, 1)) if selected > 0 else 0.0
    return out, float(last_ratio), mean_m_hat


def hvdc_steger_dinkelbach_fold_emit(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    footprint: np.ndarray,
    train_eligible_mask: np.ndarray,
    test_eligible_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    target_pool_dots: int = 44_000,
    full_eligible_pixels: int = 4_600_000,
    min_spacing_px: float = 2.50,
    min_fold_dots: int = 6_500,
    max_fold_dots: int = 17_500,
) -> tuple[np.ndarray, dict[str, float]]:
    """`H14-3` Fold-independent Continuous-Steger + Self-Credit-Exact (`M`-Term)
    Dinkelbach Emitter. Calibrates `q_floor_k` and marginal Dinkelbach ratio `tau_k`
    strictly on `train_eligible_mask` (`Train_k`), touching zero test-fold data.
    """
    w_surf, fp_cost_2d, rank_s, q_floor_k = build_hvdc_steger_expected_intensity(
        prob_2d,
        crest_2d,
        piedmont_mask,
        footprint,
        calibration_mask=train_eligible_mask,
        pi_true=pi_true,
        pi_sample=pi_sample,
    )

    n_cal_px = int(train_eligible_mask.sum())
    n_cal_target = max(
        1_000,
        int(round(target_pool_dots * (n_cal_px / float(max(full_eligible_pixels, 1))))),
    )
    _, tau_ratio_k, train_m_hat = _lazy_greedy_self_credit_select(
        w_surf,
        fp_cost_2d,
        train_eligible_mask,
        rank_surf=rank_s,
        max_dots=n_cal_target,
        min_ratio_threshold=0.0,
        min_spacing_px=min_spacing_px,
    )

    test_dots, last_test_ratio, test_m_hat = _lazy_greedy_self_credit_select(
        w_surf,
        fp_cost_2d,
        test_eligible_mask,
        rank_surf=rank_s,
        max_dots=max_fold_dots,
        min_ratio_threshold=tau_ratio_k,
        min_spacing_px=min_spacing_px,
    )
    n_emitted = int((test_dots > 0).sum())
    if n_emitted < min_fold_dots:
        test_dots, last_test_ratio, test_m_hat = _lazy_greedy_self_credit_select(
            w_surf,
            fp_cost_2d,
            test_eligible_mask,
            rank_surf=rank_s,
            max_dots=min_fold_dots,
            min_ratio_threshold=0.0,
            min_spacing_px=min_spacing_px,
        )
        n_emitted = int((test_dots > 0).sum())

    return test_dots, {
        "q_floor_train": round(float(q_floor_k), 7),
        "tau_dinkelbach_ratio_train": round(float(tau_ratio_k), 7),
        "last_test_ratio": round(float(last_test_ratio), 7),
        "train_mean_self_credit_m_hat": round(float(train_m_hat), 5),
        "test_mean_self_credit_m_hat": round(float(test_m_hat), 5),
        "n_cal_pixels": n_cal_px,
        "n_cal_target_dots": n_cal_target,
        "n_test_emitted_dots": n_emitted,
    }


def hvdc_steger_dinkelbach_full_map_emit(
    prob_2d: np.ndarray,
    crest_2d: np.ndarray,
    piedmont_mask: np.ndarray,
    *,
    footprint: np.ndarray,
    full_eligible_mask: np.ndarray,
    pi_true: float,
    pi_sample: float,
    n_dots: int = 43_000,
    min_spacing_px: float = 2.50,
) -> tuple[np.ndarray, float, float, np.ndarray]:
    """Emit full-Nevada binary `{0.0, 1.0}` dot raster under `H14-3` Continuous Steger
    + Self-Credit-Exact (`M`-Term) Dinkelbach objective.
    Returns `(dots_2d, last_ratio, mean_m_hat, w_surf)`.
    """
    w_surf, fp_cost_2d, rank_s, _ = build_hvdc_steger_expected_intensity(
        prob_2d,
        crest_2d,
        piedmont_mask,
        footprint,
        calibration_mask=full_eligible_mask,
        pi_true=pi_true,
        pi_sample=pi_sample,
    )
    dots, last_ratio, mean_m_hat = _lazy_greedy_self_credit_select(
        w_surf,
        fp_cost_2d,
        full_eligible_mask,
        rank_surf=rank_s,
        max_dots=n_dots,
        min_ratio_threshold=0.0,
        min_spacing_px=min_spacing_px,
    )
    return dots, last_ratio, mean_m_hat, w_surf
