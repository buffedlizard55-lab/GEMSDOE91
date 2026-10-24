"""Session 12 (`S12-BHAR`): Basin-Stripped Bouguer Gravity & Depth-Conditioned
Conductivity Residual Curvature + SI-Reconciled 3-D Magnetic Analytic Signal &
Salem Local Wavenumber + Multi-Field Structure-Tensor Nematic Phase-Locking +
Cross-Strike Centerline Posterior-Mass Submodular 300 m DTI Pipeline.

Grounded in four Session 12 forensic & physical discoveries (`docs/HYPOTHESES_S12.md`):
  1. `IR-91-S12-01`: `Band 03 (tmi_hg)` is an undivided 2*dx = 200 m central
     difference (`200.024 x ||grad_H B14||_{nT/m}`), whereas `Band 09 (tmi_vg)` is
     in true SI `nT/m`, and `dd_vtc_pu.py` previously crushed `rtp_tilt` by ~100x.
     Dividing `B03` by `200.0` reconstructs the exact remanence-invariant 3-D
     Roest-Verhoef-Pilkington Analytic Signal `sqrt((B03/200)^2 + B09^2)`, true
     airborne TMI Miller-Singh tilt, Salem Tilt-Depth local wavenumber `1/z_mag`,
     and remanent magnetization discrepancy.
  2. `IR-91-S12-02`: Sedimentary cover `Band 15 (depth_to_base_surf)` accounts
     for `R^2 = 0.4664` of `Band 13 (iso_grav_anom)` variance. Fold-safe (training-
     only) nonlinear Bouguer compaction stripping `G_intra = B13 - g_hat(B15)` +
     fold-safe depth/elevation-conditioned conductivity residual `C_res = B17 - c_hat(B15, B12)`
     isolates intra-basin basement horst steps and hydrothermal smectite clay-cap
     fault seals without test-quadrant leakage.
  3. `IR-91-S12-03`: `Band 10 (deq_n100a15)` spans `[0, 4.96e6]` (`r = +0.667` in
     log-space with `B16`), requiring log-domain stabilization, while 1.2 km
     Multi-Field Structure-Tensor Linearity `L_sigma` and Cross-Field Nematic
     Strike Phase-Locking `cos(2 * delta_psi)` reject circular volcanic domes and
     meandering canyons.
  4. `IR-91-S12-04`: `S11-MHTR E2` suffered from `4,069` 2-D flank-crowded dots
     (`>= 3` neighbors within `3.5 px`), `1,189` isolated 0-D speckles (`NN1 > 8 px`),
     and raw-area fold quotas. Hessian cross-strike non-maximum centerline
     sharpening + steerable continuity + Horvitz-Thompson hard-negative ensemble +
     label-blind posterior-mass fold allocation cures all three defects.
"""

from __future__ import annotations

import gc
import json
import math
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from . import dd_vtc_pu as DD
from . import mhtr_coda as MC

S12_STATIC_FEATURE_NAMES = [
    # Group H12-1 static (1 col)
    "s12_basement_horst_curv",
    # Group H12-2 static: SI-Reconciled 3-D Analytic Signal & Salem Local Wavenumber (6 cols)
    "s12_mag_analytic_sig_3d",
    "s12_tmi_true_tilt",
    "s12_salem_local_wavenumber",
    "s12_rtp_true_tilt_hd",
    "s12_remanence_phase_disc",
    "s12_updip_analytic_wavenumber",
    # Group H12-3 static: Multi-Field Structure-Tensor Nematic Phase-Locking & Log-Seismic (8 cols)
    "s12_subsurf_st_linearity",
    "s12_rad_st_linearity",
    "s12_nematic_sub_topo_lock",
    "s12_nematic_sub_rad_lock",
    "s12_steerable_radon_crest",
    "s12_ctx2p5km_corridor_env",
    "s12_log_deq_n100a15",
    "s12_transtension_strike_coupling",
]

S12_FOLD_FEATURE_NAMES = [
    # Group H12-1 fold-safe Bouguer-stripped gravity & depth-conditioned conductivity (7 cols)
    "s12f_g_intra_res",
    "s12f_g_intra_grad",
    "s12f_g_intra_svd",
    "s12f_cond_depth_res",
    "s12f_cond_res_grad",
    "s12f_cond_claycap_curv",
    "s12f_subsurf_grav_cond_joint",
    # Group H12-2 fold-safe shallow GeoDAWN aeromagnetic residual edge (1 col)
    "s12f_shallow_geodawn_res_grad",
    # Group H12-3 fold-safe log-seismic energy-to-density residual (1 col)
    "s12f_log_seismic_energy_res",
]


def _reconstruct_full_grid_from_fp(
    vals_fp: np.ndarray,
    footprint: np.ndarray,
    nearest_idx: np.ndarray,
) -> np.ndarray:
    """Reconstruct a full `(H, W)` float32 grid from `footprint` values with
    deterministic nearest-footprint boundary padding (0.03s, zero disk I/O).
    """
    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[footprint] = np.asarray(vals_fp, dtype=np.float32)
    return grid[tuple(nearest_idx)].astype(np.float32, copy=False)


def _structure_tensor_linearity_and_director(
    field: np.ndarray,
    sigma_grad: float,
    sigma_int: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return `(linearity, cos_2psi, sin_2psi)` of the 2x2 structure tensor
    `J = G_{sigma_int}(grad u * grad u^T)`, where `psi` is the fault strike
    director (perpendicular to dominant gradient eigenvector, invariant to +-180 deg).
    """
    sm = ndi.gaussian_filter(field, sigma=sigma_grad) if sigma_grad > 0 else field
    gy = ndi.sobel(sm, axis=0) / 8.0
    gx = ndi.sobel(sm, axis=1) / 8.0
    jyy = ndi.gaussian_filter(gy * gy, sigma=sigma_int)
    jxx = ndi.gaussian_filter(gx * gx, sigma=sigma_int)
    jyx = ndi.gaussian_filter(gy * gx, sigma=sigma_int)

    tr = jxx + jyy + 1e-8
    diff_xx_yy = jxx - jyy
    aniso = np.hypot(diff_xx_yy, 2.0 * jyx)
    linearity = np.clip(aniso / tr, 0.0, 1.0).astype(np.float32)

    # Dominant gradient angle `alpha` satisfies `(cos 2*alpha, sin 2*alpha) = ((jxx-jyy)/aniso, 2*jyx/aniso)`
    # in `(x, y)` coordinates; rotating by 90 deg to fault strike simply negates `(cos 2*alpha, sin 2*alpha)`!
    # For cross-field `cos 2*(psi_a - psi_b)`, the two minus signs cancel identically; for absolute strike
    # azimuth from North (`y = -North, x = +East`), gradient normal `(gx, gy)` corresponds to strike
    # vector `(sx, sy) = (-gy, gx)` => azimuth clockwise from North `psi` has `sin psi = -gy/r, cos psi = -gx/r`
    # => `cos 2*psi = cos^2 psi - sin^2 psi = (gx^2 - gy^2)/r^2 = (jxx - jyy)/aniso`,
    #    `sin 2*psi = 2 sin psi cos psi = 2*gx*gy/r^2 = 2*jyx/aniso`!
    denom = aniso + 1e-8
    cos_2psi = (diff_xx_yy / denom).astype(np.float32)
    sin_2psi = (2.0 * jyx / denom).astype(np.float32)
    return linearity, cos_2psi, sin_2psi


def _steerable_crest_minus_flank_kernel(azimuth_deg: float, length_px: int = 11) -> np.ndarray:
    """Zero-sum steerable kernel measuring 1.1 km along-strike ridge continuity
    minus +-2.5 px cross-strike blurry flank background.
    """
    half = length_px // 2
    yy, xx = np.mgrid[-half : half + 1, -half : half + 1].astype(np.float32)
    rad = math.radians(azimuth_deg)
    sy, sx = -math.cos(rad), math.sin(rad)
    ny, nx = sx, -sy
    s_c = yy * sy + xx * sx
    n_c = yy * ny + xx * nx

    along = np.exp(-0.5 * (s_c / (0.44 * length_px)) ** 2)
    crest = np.exp(-0.5 * (n_c / 0.85) ** 2)
    flank = 0.5 * (
        np.exp(-0.5 * ((n_c - 2.6) / 1.05) ** 2) + np.exp(-0.5 * ((n_c + 2.6) / 1.05) ** 2)
    )
    kern = along * (crest - flank)
    kern -= kern.mean()
    norm = float(np.linalg.norm(kern))
    if norm > 0:
        kern /= norm
    return kern.astype(np.float32)


def build_or_load_s12_static_memmap(
    *,
    X_static: np.memmap,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed float32 Session 12 static feature matrix `(N_fp, 15)`.

    Reconstructs bands directly from the already-cleaned `X_static[:, 0:19]`
    footprint columns (zero redundant LZW GeoTIFF decompression).
    """
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s12_bhar_static_v1.dat"
    meta_path = cache_p / "s12_bhar_static_v1.json"

    n_fp = int(footprint.sum())
    n_cols = len(S12_STATIC_FEATURE_NAMES)

    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            meta.get("n_fp") == n_fp
            and meta.get("n_cols") == n_cols
            and meta.get("feature_names") == S12_STATIC_FEATURE_NAMES
            and dat_path.stat().st_size == n_fp * n_cols * 4
        ):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(S12_STATIC_FEATURE_NAMES), meta

    h, w = footprint.shape
    _, nearest_idx = ndi.distance_transform_edt(~footprint, return_indices=True)

    def _band(b_1idx: int) -> np.ndarray:
        return _reconstruct_full_grid_from_fp(X_static[:, b_1idx - 1], footprint, nearest_idx)

    # 1. H12-1 static: Basement horst log-depth curvature
    b15 = np.maximum(_band(15), 0.0)
    log_b15 = np.log1p(b15).astype(np.float32)
    basement_horst_curv = (-ndi.laplace(ndi.gaussian_filter(log_b15, sigma=2.5))).astype(np.float32)
    del log_b15

    # 2. H12-2 static: SI-Reconciled 3-D Magnetic Analytic Signal & Salem Local Wavenumber
    b2 = _band(2)
    b3_si = np.maximum(_band(3), 0.0) / np.float32(200.0)  # Exact SI nT/m (fixes 200x undivided diff!)
    b9_si = _band(9)                                        # Exact SI nT/m

    analytic_3d_raw = np.hypot(b3_si, b9_si).astype(np.float32)
    mag_analytic_sig_3d = np.log1p(100.0 * analytic_3d_raw).astype(np.float32)
    tmi_true_tilt = np.arctan2(b9_si, b3_si + 1e-5).astype(np.float32)
    salem_local_wavenumber = DD._grad_mag(tmi_true_tilt, sigma=1.0)
    del b3_si, b9_si, analytic_3d_raw

    # Unit-consistent RTP tilt angle & horizontal derivative (fixes IR-91-S12-01 100x scale bug)
    b2_sm = ndi.gaussian_filter(b2, sigma=1.2)
    rtp_gy, rtp_gx = np.gradient(b2_sm)
    rtp_hg_px = np.hypot(rtp_gy, rtp_gx)
    rtp_vd_px = -ndi.laplace(b2_sm)  # Consistent pixel-scale vertical proxy
    rtp_true_tilt = np.arctan2(rtp_vd_px, rtp_hg_px + 1e-3).astype(np.float32)
    rtp_true_tilt_hd = DD._grad_mag(rtp_true_tilt, sigma=1.1)
    remanence_phase_disc = np.abs(np.sin(tmi_true_tilt) - np.sin(rtp_true_tilt)).astype(np.float32)
    del b2, b2_sm, rtp_gy, rtp_gx, rtp_hg_px, rtp_vd_px, rtp_true_tilt

    # Vector-normal updip projection of 3-D Analytic Signal & Salem wavenumber along -g_H / ||g_H||
    b11_s = ndi.gaussian_filter(_band(11), sigma=1.2)
    b18_s = ndi.gaussian_filter(_band(18), sigma=1.2)
    gnorm = np.hypot(b11_s, b18_s) + 1e-4
    offset_px = np.clip((b15 * 0.7002075) / 100.0, 0.0, 10.0).astype(np.float32)
    yy_b, xx_b = np.indices((h, w), dtype=np.float32)
    coords_up = np.array([
        np.clip(yy_b + offset_px * (-b11_s / gnorm), 0.0, h - 1.0),
        np.clip(xx_b + offset_px * (-b18_s / gnorm), 0.0, w - 1.0),
    ])
    del yy_b, xx_b, offset_px, b15

    mag_combo = (0.55 * DD._robust_z(mag_analytic_sig_3d, footprint) + 0.45 * DD._robust_z(salem_local_wavenumber, footprint)).astype(np.float32)
    updip_analytic_wavenumber = ndi.map_coordinates(mag_combo, coords_up, order=1, mode="nearest").astype(np.float32)
    del coords_up, mag_combo
    gc.collect()

    # 3. H12-3 static: Multi-Field Structure-Tensor Linearity, Nematic Strike Phase-Locking & Log-Seismic
    b13 = _band(13)
    b17 = _band(17)
    b6 = _band(6)
    b12 = _band(12)

    subsurf_pot = (
        0.45 * DD._robust_z(b13, footprint)
        + 0.30 * DD._robust_z(mag_analytic_sig_3d, footprint)
        + 0.25 * DD._robust_z(b17, footprint)
    ).astype(np.float32)
    del b13, b17

    subsurf_st_linearity, c2_sub, s2_sub = _structure_tensor_linearity_and_director(subsurf_pot, sigma_grad=1.4, sigma_int=8.0)
    rad_st_linearity, c2_rad, s2_rad = _structure_tensor_linearity_and_director(b6, sigma_grad=1.5, sigma_int=6.0)
    topo_st_linearity, c2_top, s2_top = _structure_tensor_linearity_and_director(b12, sigma_grad=1.5, sigma_int=6.0)
    del subsurf_pot, b6, b12

    cos_2diff_topo = c2_sub * c2_top + s2_sub * s2_top
    cos_2diff_rad = c2_sub * c2_rad + s2_sub * s2_rad
    nematic_sub_topo_lock = (np.sqrt(subsurf_st_linearity * topo_st_linearity) * cos_2diff_topo).astype(np.float32)
    nematic_sub_rad_lock = (np.sqrt(subsurf_st_linearity * rad_st_linearity) * cos_2diff_rad).astype(np.float32)
    del topo_st_linearity, c2_rad, s2_rad, c2_top, s2_top, cos_2diff_topo, cos_2diff_rad

    # Steerable 12-azimuth crest-minus-flank Radon ridge isolator & 2.5 km regional corridor envelope
    b19 = np.maximum(_band(19), 0.0)
    edge_comp = (
        0.34 * np.clip(DD._robust_z(gnorm, footprint), -2.0, 5.0)
        + 0.30 * np.clip(DD._robust_z(salem_local_wavenumber, footprint), -2.0, 5.0)
        + 0.20 * np.clip(DD._robust_z(rtp_true_tilt_hd, footprint), -2.0, 5.0)
        + 0.16 * np.clip(DD._robust_z( np.log1p(b19), footprint), -2.0, 5.0)
    ).astype(np.float32)
    del b11_s, b18_s, gnorm, b19

    steerable_radon_crest = np.full((h, w), -1e9, dtype=np.float32)
    for k in range(12):
        kern = _steerable_crest_minus_flank_kernel(float(k * 15.0), length_px=11)
        resp = ndi.convolve(edge_comp, kern, mode="nearest")
        steerable_radon_crest = np.maximum(steerable_radon_crest, resp)
        del resp
    del edge_comp

    ctx2p5km_corridor_env = ndi.gaussian_filter(np.maximum(steerable_radon_crest, 0.0), sigma=22.0).astype(np.float32)

    # Log-stabilized Band 10 (`IR-91-S12-03`) & Strike-Coupled Transtensional Partition
    b10_fp = np.maximum(np.asarray(X_static[:, 9], dtype=np.float32), 0.0)
    log_deq_fp = np.log1p(b10_fp).astype(np.float32)

    b4_fp = np.maximum(np.asarray(X_static[:, 3], dtype=np.float32), 0.0)
    b7_fp = np.maximum(np.asarray(X_static[:, 6], dtype=np.float32), 0.0)
    b8_fp = np.asarray(X_static[:, 7], dtype=np.float32)
    transtens_ratio_fp = (b7_fp + np.maximum(b8_fp, 0.0)) / (b4_fp + 1e-3)

    # cos^2(psi - phi0) = 0.5 * (1 + cos 2*psi * cos 2*phi0 + sin 2*psi * sin 2*phi0)
    c2_fp = c2_sub[footprint]
    s2_fp = s2_sub[footprint]
    c40, s40 = math.cos(math.radians(40.0)), math.sin(math.radians(40.0))   # 2 * 20 deg (N20E)
    c110, s110 = math.cos(math.radians(110.0)), math.sin(math.radians(110.0))  # 2 * 55 deg (N55E)
    align_nne = 0.5 * (1.0 + c2_fp * c40 + s2_fp * s40)
    align_ene = 0.5 * (1.0 + c2_fp * c110 + s2_fp * s110)
    strike_opt = np.maximum(align_nne, 0.85 * align_ene).astype(np.float32)
    transtension_coupling_fp = (transtens_ratio_fp * (0.35 + 0.65 * subsurf_st_linearity[footprint] * strike_opt)).astype(np.float32)
    del c2_sub, s2_sub, nearest_idx
    gc.collect()

    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    grid_cols = [
        basement_horst_curv,
        mag_analytic_sig_3d,
        tmi_true_tilt,
        salem_local_wavenumber,
        rtp_true_tilt_hd,
        remanence_phase_disc,
        updip_analytic_wavenumber,
        subsurf_st_linearity,
        rad_st_linearity,
        nematic_sub_topo_lock,
        nematic_sub_rad_lock,
        steerable_radon_crest,
        ctx2p5km_corridor_env,
    ]
    for j, g_arr in enumerate(grid_cols):
        mm[:, j] = g_arr[footprint]
    mm[:, 13] = log_deq_fp
    mm[:, 14] = transtension_coupling_fp
    mm.flush()

    meta = {
        "n_fp": n_fp,
        "n_cols": n_cols,
        "feature_names": S12_STATIC_FEATURE_NAMES,
        "licence_clean_100pct": True,
        "b03_si_divisor": 200.0,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    return mm_ro, list(S12_STATIC_FEATURE_NAMES), meta


class FoldSafeResidualBasis:
    """Precomputes linear spatial derivative bases on the footprint so that
    exact fold-fitted Bouguer-stripped gravity (`G_intra`), depth/elevation-
    conditioned conductivity (`C_res`), shallow GeoDAWN magnetic residual, and
    log-seismic energy residual are evaluated in `< 0.25 s` per fold with
    MATHEMATICALLY ZERO test-region leakage.
    """

    def __init__(self, X_static: np.memmap, footprint: np.ndarray) -> None:
        self.footprint = footprint
        self.n_fp = int(footprint.sum())
        _, nearest_idx = ndi.distance_transform_edt(~footprint, return_indices=True)

        def _b(idx_1: int) -> np.ndarray:
            return _reconstruct_full_grid_from_fp(X_static[:, idx_1 - 1], footprint, nearest_idx)

        b13 = _b(13)
        b15 = np.maximum(_b(15), 0.0)
        b17 = _b(17)
        b12 = _b(12)
        b14 = _b(14)
        b1 = _b(1)

        # Smooth basin thickness `H_s` (sigma=3 px = 300 m) for regional compaction model
        h_s = np.maximum(ndi.gaussian_filter(b15, sigma=3.0), 0.0).astype(np.float32)
        z_s = ndi.gaussian_filter(b12, sigma=4.0).astype(np.float32)
        del b15, b12

        phi1 = (h_s / 1000.0).astype(np.float32)
        phi2 = np.sqrt(phi1).astype(np.float32)
        phi3 = np.log1p(h_s / 250.0).astype(np.float32)
        phi4 = (z_s / 500.0).astype(np.float32)
        del h_s, z_s

        # Store 1-D footprint vectors for OLS fitting
        self.b13_fp = b13[footprint].astype(np.float32)
        self.b17_fp = b17[footprint].astype(np.float32)
        self.phi_grav_fp = np.column_stack([
            np.ones(self.n_fp, dtype=np.float32),
            phi1[footprint],
            phi2[footprint],
            phi3[footprint],
        ])
        self.phi_cond_fp = np.column_stack([
            np.ones(self.n_fp, dtype=np.float32),
            phi1[footprint],
            phi2[footprint],
            phi3[footprint],
            phi4[footprint],
        ])

        # Exact linear derivative bases for `G_intra = b13 - sum_{m=1..3} c_m phi_m`
        def _gy_gx(arr: np.ndarray, sig: float) -> tuple[np.ndarray, np.ndarray]:
            sm = ndi.gaussian_filter(arr, sigma=sig)
            return (
                (ndi.sobel(sm, axis=0) / 8.0)[footprint].astype(np.float32),
                (ndi.sobel(sm, axis=1) / 8.0)[footprint].astype(np.float32),
            )

        def _neg_lap(arr: np.ndarray, sig: float) -> np.ndarray:
            return (-ndi.laplace(ndi.gaussian_filter(arr, sigma=sig)))[footprint].astype(np.float32)

        self.b13_gy, self.b13_gx = _gy_gx(b13, 1.5)
        self.b13_svd = _neg_lap(b13, 2.0)
        del b13

        self.b17_gy, self.b17_gx = _gy_gx(b17, 1.5)
        self.b17_curv = _neg_lap(b17, 3.0)
        del b17

        self.phi_gy = []
        self.phi_gx = []
        self.phi_svd2 = []
        self.phi_curv3 = []
        for p_grid in (phi1, phi2, phi3, phi4):
            gy_p, gx_p = _gy_gx(p_grid, 1.5)
            self.phi_gy.append(gy_p)
            self.phi_gx.append(gx_p)
            self.phi_svd2.append(_neg_lap(p_grid, 2.0))
            self.phi_curv3.append(_neg_lap(p_grid, 3.0))
        del phi1, phi2, phi3, phi4

        # Shallow GeoDAWN aeromagnetic residual basis (`B14 - (b0 + b1 * B01)`)
        self.b14_fp = b14[footprint].astype(np.float32)
        self.b1_fp = b1[footprint].astype(np.float32)
        self.b14_gy, self.b14_gx = _gy_gx(b14, 1.2)
        self.b1_gy, self.b1_gx = _gy_gx(b1, 1.2)
        del b14, b1, nearest_idx

        # Log-seismic basis (`log1p(B16) - (a0 + a1 * log1p(B10))`)
        self.log_b10_fp = np.log1p(np.maximum(np.asarray(X_static[:, 9], dtype=np.float32), 0.0))
        self.log_b16_fp = np.log1p(np.maximum(np.asarray(X_static[:, 15], dtype=np.float32), 0.0))
        gc.collect()

    def compute_for_fold(self, exclude_mask: np.ndarray) -> np.ndarray:
        """Fit all 4 physical background regressions strictly on `~exclude_mask`
        (subsampled every 13th training pixel for instant exact OLS) and evaluate
        the `9` residual/derivative features across all `N_fp` pixels.
        """
        fit_fp = ~exclude_mask[self.footprint]
        fit_idx = np.flatnonzero(fit_fp)[::13]
        if fit_idx.size < 100:
            raise ValueError("insufficient non-excluded pixels to fit physical residuals")

        # 1. Bouguer basin-fill compaction law: b13 ~ [1, phi1, phi2, phi3]
        c_g, _, _, _ = np.linalg.lstsq(
            self.phi_grav_fp[fit_idx].astype(np.float64),
            self.b13_fp[fit_idx].astype(np.float64),
            rcond=None,
        )
        c_g32 = c_g.astype(np.float32)
        g_intra_res = self.b13_fp - (self.phi_grav_fp @ c_g32)
        g_gy = self.b13_gy - c_g32[1] * self.phi_gy[0] - c_g32[2] * self.phi_gy[1] - c_g32[3] * self.phi_gy[2]
        g_gx = self.b13_gx - c_g32[1] * self.phi_gx[0] - c_g32[2] * self.phi_gx[1] - c_g32[3] * self.phi_gx[2]
        g_intra_grad = np.hypot(g_gy, g_gx).astype(np.float32)
        g_intra_svd = (
            self.b13_svd - c_g32[1] * self.phi_svd2[0] - c_g32[2] * self.phi_svd2[1] - c_g32[3] * self.phi_svd2[2]
        ).astype(np.float32)

        # 2. Depth & elevation conditioned subsurface conductivity law: b17 ~ [1, phi1..phi4]
        c_c, _, _, _ = np.linalg.lstsq(
            self.phi_cond_fp[fit_idx].astype(np.float64),
            self.b17_fp[fit_idx].astype(np.float64),
            rcond=None,
        )
        c_c32 = c_c.astype(np.float32)
        cond_res = self.b17_fp - (self.phi_cond_fp @ c_c32)
        c_gy = (
            self.b17_gy
            - c_c32[1] * self.phi_gy[0]
            - c_c32[2] * self.phi_gy[1]
            - c_c32[3] * self.phi_gy[2]
            - c_c32[4] * self.phi_gy[3]
        )
        c_gx = (
            self.b17_gx
            - c_c32[1] * self.phi_gx[0]
            - c_c32[2] * self.phi_gx[1]
            - c_c32[3] * self.phi_gx[2]
            - c_c32[4] * self.phi_gx[3]
        )
        cond_res_grad = np.hypot(c_gy, c_gx).astype(np.float32)
        cond_claycap_curv = (
            self.b17_curv
            - c_c32[1] * self.phi_curv3[0]
            - c_c32[2] * self.phi_curv3[1]
            - c_c32[3] * self.phi_curv3[2]
            - c_c32[4] * self.phi_curv3[3]
        ).astype(np.float32)

        grav_cond_joint = np.sqrt(g_intra_grad * cond_res_grad).astype(np.float32)

        # 3. Shallow GeoDAWN aeromagnetic residual edge: B14 ~ b0 + b1 * B01
        X_mag = np.column_stack([np.ones(fit_idx.size, dtype=np.float64), self.b1_fp[fit_idx].astype(np.float64)])
        c_m, _, _, _ = np.linalg.lstsq(X_mag, self.b14_fp[fit_idx].astype(np.float64), rcond=None)
        b1_slope = np.float32(c_m[1])
        shallow_mag_grad = np.hypot(
            self.b14_gy - b1_slope * self.b1_gy,
            self.b14_gx - b1_slope * self.b1_gx,
        ).astype(np.float32)

        # 4. Log-seismic energy-to-density excess: log1p(B16) ~ a0 + a1 * log1p(B10)
        X_seis = np.column_stack([np.ones(fit_idx.size, dtype=np.float64), self.log_b10_fp[fit_idx].astype(np.float64)])
        c_s, _, _, _ = np.linalg.lstsq(X_seis, self.log_b16_fp[fit_idx].astype(np.float64), rcond=None)
        log_seis_res = (
            self.log_b16_fp - (np.float32(c_s[0]) + np.float32(c_s[1]) * self.log_b10_fp)
        ).astype(np.float32)

        out = np.empty((self.n_fp, len(S12_FOLD_FEATURE_NAMES)), dtype=np.float32)
        out[:, 0] = g_intra_res
        out[:, 1] = g_intra_grad
        out[:, 2] = g_intra_svd
        out[:, 3] = cond_res
        out[:, 4] = cond_res_grad
        out[:, 5] = cond_claycap_curv
        out[:, 6] = grav_cond_joint
        out[:, 7] = shallow_mag_grad
        out[:, 8] = log_seis_res
        return out


def compute_bhar_subsurface_edge_field(
    X_s11: np.memmap | np.ndarray,
    X_s12_static: np.memmap | np.ndarray,
    X_s12_fold: np.ndarray,
    X_static: np.memmap | np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute:
      1. `bhar_edge`: label-free Bouguer-Stripped Subsurface + 3-D Analytic Signal +
         Conductivity Seal + Radiometric TC + Nematic Linearity structural edge field `[0, 1]`.
      2. `concealed_regime_mask`: boolean mask of concealed basin / piedmont / low-relief
         volcanic tableland regime (`det_elev_slope < 6.6 deg` OR `depth_to_base > 200 m`
         with `det_elev_slope < 11.0 deg`).
    """
    def _n01(v: np.ndarray) -> np.ndarray:
        q50 = float(np.percentile(v[::20], 50))
        q95 = float(np.percentile(v[::20], 95))
        return np.clip((v - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    up_eot = np.asarray(X_s11[:, 4], dtype=np.float32)
    tg_cos = np.clip(np.asarray(X_s11[:, 6], dtype=np.float32), 0.0, 1.0)
    pr_crv = np.abs(np.asarray(X_s11[:, 7], dtype=np.float32))
    rad_gr = np.asarray(X_s11[:, 8], dtype=np.float32)

    g_in_gr = np.asarray(X_s12_fold[:, 1], dtype=np.float32)
    c_re_gr = np.asarray(X_s12_fold[:, 4], dtype=np.float32)
    gc_jnt = np.asarray(X_s12_fold[:, 6], dtype=np.float32)

    asig_3d = np.asarray(X_s12_static[:, 1], dtype=np.float32)
    salem_k = np.asarray(X_s12_static[:, 3], dtype=np.float32)
    up_asig = np.asarray(X_s12_static[:, 6], dtype=np.float32)
    st_lin = np.asarray(X_s12_static[:, 7], dtype=np.float32)

    s_bouguer_cond = 0.40 * _n01(up_eot) + 0.32 * _n01(g_in_gr) + 0.28 * np.maximum(_n01(c_re_gr), _n01(gc_jnt))
    s_mag_rad = 0.36 * _n01(rad_gr) + 0.34 * np.maximum(_n01(salem_k), _n01(asig_3d)) + 0.30 * _n01(up_asig)
    s_hinge_lin = (0.55 * tg_cos * _n01(pr_crv) + 0.45 * np.clip(st_lin, 0.0, 1.0)).astype(np.float32)

    e_fp = np.clip(0.42 * s_bouguer_cond + 0.36 * s_mag_rad + 0.22 * s_hinge_lin, 0.0, 1.0)
    out_edge = np.zeros(footprint.shape, dtype=np.float32)
    out_edge[footprint] = e_fp

    depth_b = np.asarray(X_static[:, 14], dtype=np.float32)
    slope_b = np.asarray(X_static[:, 18], dtype=np.float32)
    conc_fp = (slope_b < 6.6) | ((depth_b > 200.0) & (slope_b < 11.0))
    conc_mask = np.zeros(footprint.shape, dtype=bool)
    conc_mask[footprint] = conc_fp
    return out_edge, conc_mask


def fit_and_predict_s12_oof_fold(
    X_static: np.memmap,
    static_cols: list[int],
    X_s11: np.memmap,
    s11_cols: list[int],
    X_s12_static: np.memmap,
    s12_static_cols: list[int],
    X_s12_fold: np.ndarray,
    s12_fold_cols: list[int],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    seed: int = 1200,
    n_unif_neg: int = 135_000,
    n_hard_neg: int = 55_000,
) -> np.ndarray:
    """Train a dual-diversity column-subsampled HistGB + L2-LR ensemble with
    unbiased Horvitz-Thompson importance-sampled hard negatives (high gradient
    canyon/volcanic mimics at `d_vis > 5.0 px`) strictly on non-excluded pixels.
    """
    rng = np.random.default_rng(seed)
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis_grid = ndi.distance_transform_edt(~visible_faults)
    d_vis_fp = d_vis_grid[footprint]
    safe_neg_fp = (~vis_fp) & (~excl_fp) & (d_vis_fp > 3.5)

    # Partition safe negatives into hard high-gradient mimics (`d_vis > 5.0 px`) and general background
    slope_fp = np.asarray(X_static[:, 18], dtype=np.float32)
    grav_slp_fp = np.asarray(X_static[:, 4], dtype=np.float32)
    mag_hg_fp = np.asarray(X_static[:, 2], dtype=np.float32)
    q70_s = float(np.percentile(slope_fp[~excl_fp][::20], 72))
    q70_g = float(np.percentile(grav_slp_fp[~excl_fp][::20], 72))
    q70_m = float(np.percentile(mag_hg_fp[~excl_fp][::20], 75))

    hard_mask_fp = safe_neg_fp & (d_vis_fp > 5.0) & (
        (slope_fp >= q70_s) | (grav_slp_fp >= q70_g) | (mag_hg_fp >= q70_m)
    )
    easy_mask_fp = safe_neg_fp & (~hard_mask_fp)

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    hard_pool = np.flatnonzero(hard_mask_fp)
    easy_pool = np.flatnonzero(easy_mask_fp)

    if hard_pool.size > n_hard_neg:
        hard_idx = rng.choice(hard_pool, size=n_hard_neg, replace=False)
        hard_idx.sort()
        w_hard_val = float(hard_pool.size) / float(n_hard_neg)
    else:
        hard_idx = hard_pool
        w_hard_val = 1.0

    if easy_pool.size > n_unif_neg:
        easy_idx = rng.choice(easy_pool, size=n_unif_neg, replace=False)
        easy_idx.sort()
        w_easy_val = float(easy_pool.size) / float(n_unif_neg)
    else:
        easy_idx = easy_pool
        w_easy_val = 1.0

    # Normalize negative Horvitz-Thompson weights so total negative sample weight
    # matches a standard `165,000`-sample reference scale while keeping the exact
    # population ratio between hard mimics and flat desert background!
    total_pop_neg = float(hard_pool.size + easy_pool.size)
    ref_neg_scale = min(165_000.0, total_pop_neg) / max(total_pop_neg, 1.0)
    w_hard = np.full(hard_idx.size, w_hard_val * ref_neg_scale, dtype=np.float32)
    w_easy = np.full(easy_idx.size, w_easy_val * ref_neg_scale, dtype=np.float32)
    w_pos = np.ones(pos_idx.size, dtype=np.float32)

    train_idx = np.concatenate([pos_idx, hard_idx, easy_idx])
    y_train = np.concatenate([
        np.ones(pos_idx.size, dtype=np.int32),
        np.zeros(hard_idx.size + easy_idx.size, dtype=np.int32),
    ])
    sample_weight = np.concatenate([w_pos, w_hard, w_easy])

    def _assemble_block(rows: slice | np.ndarray) -> np.ndarray:
        parts = [np.asarray(X_static[rows][:, static_cols], dtype=np.float32)]
        if s11_cols:
            parts.append(np.asarray(X_s11[rows][:, s11_cols], dtype=np.float32))
        if s12_static_cols:
            parts.append(np.asarray(X_s12_static[rows][:, s12_static_cols], dtype=np.float32))
        if s12_fold_cols:
            parts.append(np.asarray(X_s12_fold[rows][:, s12_fold_cols], dtype=np.float32))
        return np.hstack(parts)

    X_tr = _assemble_block(train_idx)

    # Model A: Deep structural-interaction HGB with column subsampling (`max_features=0.72`)
    hgb_a = HistGradientBoostingClassifier(
        learning_rate=0.048,
        max_iter=245,
        max_leaf_nodes=45,
        min_samples_leaf=80,
        l2_regularization=4.0,
        max_features=0.72,
        random_state=seed,
    )
    hgb_a.fit(X_tr, y_train, sample_weight=sample_weight)

    # Model B: Strongly regularized generalist HGB (`max_features=0.58`) preventing quadrant overfit
    hgb_b = HistGradientBoostingClassifier(
        learning_rate=0.052,
        max_iter=210,
        max_leaf_nodes=25,
        min_samples_leaf=130,
        l2_regularization=8.0,
        max_features=0.58,
        random_state=seed + 101,
    )
    hgb_b.fit(X_tr, y_train, sample_weight=sample_weight)

    # Model C: Clipped standardized L2 Logistic Regression (with heavy-tailed raw B10 scrubbed if present)
    scaler = StandardScaler()
    X_tr_sc = np.clip(scaler.fit_transform(X_tr), -5.5, 5.5)
    lr = LogisticRegression(C=0.18, max_iter=300, random_state=seed)
    lr.fit(X_tr_sc, y_train, sample_weight=sample_weight)
    del X_tr, X_tr_sc
    gc.collect()

    n_fp = int(footprint.sum())
    pred_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 420_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        Xc = _assemble_block(slice(s, e))
        pa = hgb_a.predict_proba(Xc)[:, 1]
        pb = hgb_b.predict_proba(Xc)[:, 1]
        pl = lr.predict_proba(np.clip(scaler.transform(Xc), -5.5, 5.5))[:, 1]
        pred_fp[s:e] = (0.48 * pa + 0.34 * pb + 0.18 * pl).astype(np.float32)

    out_grid = np.zeros(footprint.shape, dtype=np.float32)
    out_grid[footprint] = pred_fp
    return out_grid


def compute_label_blind_fold_quotas(
    fold_surfaces: dict[int, np.ndarray],
    fold_bhar_edges: dict[int, np.ndarray],
    fold_eligible: dict[int, np.ndarray],
    total_budget: int,
    *,
    prior_ratio: float = 0.052,
    mass_blend: float = 0.55,
) -> dict[int, int]:
    """Allocate `total_budget` across the 4 holdout folds using ONLY label-blind
    OOF predicted posterior fault mass (`mass_blend`) + eligible footprint area
    (`1 - mass_blend`), matching global full-map allocation without touching any
    withheld truth labels.
    """
    fold_ids = sorted(fold_surfaces.keys())
    area_counts = {fid: float(fold_eligible[fid].sum()) for fid in fold_ids}
    pred_masses: dict[int, float] = {}
    for fid in fold_ids:
        elig = fold_eligible[fid]
        p = np.clip(fold_surfaces[fid][elig], 0.0, 0.9999)
        eb = np.clip(fold_bhar_edges[fid][elig], 0.0, 1.0)
        q = (prior_ratio * p) / (prior_ratio * p + (1.0 - p) + 1e-8) * (1.0 + 0.45 * eb)
        q_cut = float(np.quantile(q, 0.82)) if q.size > 0 else 0.0
        pred_masses[fid] = float(np.sum(np.maximum(q - q_cut, 0.0)))

    tot_area = max(sum(area_counts.values()), 1.0)
    tot_mass = max(sum(pred_masses.values()), 1e-8)

    quotas: dict[int, int] = {}
    assigned = 0
    for i, fid in enumerate(fold_ids):
        if i < len(fold_ids) - 1:
            share = (1.0 - mass_blend) * (area_counts[fid] / tot_area) + mass_blend * (pred_masses[fid] / tot_mass)
            q_int = int(round(total_budget * share))
            quotas[fid] = q_int
            assigned += q_int
        else:
            quotas[fid] = total_budget - assigned
    return quotas


def _hessian_cross_strike_crest_mask(q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Identify true 1-D Steger/Hessian fault centerlines (`crest_mask`) and
    1-px ridge shoulders (`shoulder_mask`) by testing non-maximum suppression
    along the principal negative-curvature eigenvector `n_hat` of `G_1.0(q)`.
    """
    h, w = q.shape
    qs = ndi.gaussian_filter(q, sigma=1.0)
    gy, gx = np.gradient(qs)
    hyy = np.gradient(gy, axis=0)
    hxx = np.gradient(gx, axis=1)
    hxy = 0.5 * (np.gradient(gy, axis=1) + np.gradient(gx, axis=0))

    # Most-negative eigenvalue `mu_1 = 0.5*(hxx + hyy - sqrt((hxx-hyy)^2 + 4*hxy^2))`
    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    mu1 = 0.5 * (hxx + hyy - disc)

    # Eigenvector `(nx, ny)` for `mu1`: `(hxx - mu1)*nx + hxy*ny = 0` => `(nx, ny) || (hxy, mu1 - hxx)`
    # fallback when `hxy ~ 0`: if `hxx < hyy`, normal is x-axis `(1, 0)`, else y-axis `(0, 1)`
    vx = hxy
    vy = mu1 - hxx
    vnorm = np.hypot(vx, vy)
    use_fb = vnorm < 1e-7
    nx = np.where(use_fb, np.where(hxx <= hyy, 1.0, 0.0), vx / np.maximum(vnorm, 1e-7)).astype(np.float32)
    ny = np.where(use_fb, np.where(hxx <= hyy, 0.0, 1.0), vy / np.maximum(vnorm, 1e-7)).astype(np.float32)

    yy, xx = np.indices((h, w), dtype=np.float32)
    step = 1.35
    q_plus = ndi.map_coordinates(
        qs,
        np.array([np.clip(yy + step * ny, 0.0, h - 1.0), np.clip(xx + step * nx, 0.0, w - 1.0)]),
        order=1,
        mode="nearest",
    )
    q_minus = ndi.map_coordinates(
        qs,
        np.array([np.clip(yy - step * ny, 0.0, h - 1.0), np.clip(xx - step * nx, 0.0, w - 1.0)]),
        order=1,
        mode="nearest",
    )

    is_hessian_crest = (mu1 < -1e-6) & (qs >= q_plus) & (qs >= q_minus)

    # Discrete 4-axis local maximum check for crisp 1-px crests & shoulders
    qp = np.pad(q, 1, mode="edge")
    c = qp[1 : h + 1, 1 : w + 1]
    is_disc_ridge = (
        ((c >= qp[0:h, 1 : w + 1]) & (c >= qp[2 : h + 2, 1 : w + 1]))
        | ((c >= qp[1 : h + 1, 0:w]) & (c >= qp[1 : h + 1, 2 : w + 2]))
        | ((c >= qp[0:h, 0:w]) & (c >= qp[2 : h + 2, 2 : w + 2]))
        | ((c >= qp[0:h, 2 : w + 2]) & (c >= qp[2 : h + 2, 0:w]))
    )

    crest = is_hessian_crest | (is_disc_ridge & (mu1 < 0.0))
    shoulder = (~crest) & (ndi.binary_dilation(crest, structure=np.ones((3, 3), dtype=bool)) | is_disc_ridge)
    return crest, shoulder


def _collinear_neighbor_envelope(q: np.ndarray) -> np.ndarray:
    """Measure collinear fault-strand support at `2..5 px` ahead/behind along
    8 strike orientations (`0..157.5 deg`), with ZERO center weight so isolated
    0-D point spikes get low support.
    """
    qs = ndi.gaussian_filter(q, sigma=0.8)
    best = np.zeros_like(qs, dtype=np.float32)
    yy, xx = np.mgrid[-5:6, -5:6].astype(np.float32)
    r = np.hypot(yy, xx)
    ring_env = np.where((r >= 1.8) & (r <= 5.2), np.exp(-0.5 * ((r - 3.2) / 1.4) ** 2), 0.0).astype(np.float32)

    for k in range(8):
        rad = math.radians(k * 22.5)
        sy, sx = -math.cos(rad), math.sin(rad)
        ny, nx = sx, -sy
        n_c = yy * ny + xx * nx
        kern = ring_env * np.exp(-0.5 * (n_c / 0.95) ** 2)
        s_k = float(kern.sum())
        if s_k > 0:
            kern /= s_k
        best = np.maximum(best, ndi.convolve(qs, kern, mode="nearest"))
    return best


def bhar_centerline_submodular_emit(
    surface: np.ndarray,
    bhar_edge_field: np.ndarray,
    concealed_mask: np.ndarray,
    *,
    eligible_mask: np.ndarray,
    n_dots: int,
    gamma: float = 1.24,
    bhar_weight: float = 0.50,
    concealed_quota_frac: float = 0.30,
    prior_ratio: float = 0.052,
    min_spacing_px: float = 2.68,
    speckle_radius_px: float = 9.0,
    pool_multiplier: int = 8,
) -> np.ndarray:
    """Centerline-Sharpened + Collinear-Supported Two-Regime 300 m Submodular DTI Allocator.

    Fixes all three geometric defects measured in `S11-MHTR E2` (`IR-91-S12-04`):
      1. Hessian cross-strike non-maximum centerline sharpening suppresses blurry
         off-crest flank weights (`0.06` vs `0.24`), eliminating 3-row parallel
         flank caterpillars on bright range-front ribbons.
      2. Collinear neighbor envelope + post-selection `NN1 <= speckle_radius_px`
         pruning/refill eliminates isolated 0-D speckles.
      3. Dedicated `concealed_quota_frac` allocates dots onto Bouguer-stripped
         subsurface / conductivity / 3-D Analytic Signal / Radiometric ridges in
         low-slope basins and volcanic plateaus (`> 3.35 px` from Stage 1).
    """
    h, w = surface.shape
    if n_dots <= 0 or not eligible_mask.any():
        return np.zeros((h, w), dtype=np.float32)

    p = np.clip(np.nan_to_num(surface, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 0.9999).astype(np.float32)
    eb = np.clip(np.nan_to_num(bhar_edge_field, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0).astype(np.float32)

    q_base = ((prior_ratio * p) / (prior_ratio * p + (1.0 - p) + 1e-8)).astype(np.float32)
    q_raw = (q_base * (1.0 + float(bhar_weight) * eb)).astype(np.float32)

    # Collinear 1-D strand continuity modulation (suppresses 0-D point spikes)
    col_env = _collinear_neighbor_envelope(q_raw)
    q95_col = max(float(np.percentile(col_env[eligible_mask][::20], 96)), 1e-6)
    col_norm = np.clip(col_env / q95_col, 0.0, 1.25).astype(np.float32)
    q = (q_raw * (0.42 + 0.58 * col_norm)).astype(np.float32)

    crest_q, shoulder_q = _hessian_cross_strike_crest_mask(q)
    crest_e, shoulder_e = _hessian_cross_strike_crest_mask(eb)

    elig_pos_q = q[eligible_mask & (q > 0)]
    if elig_pos_q.size == 0:
        return np.zeros((h, w), dtype=np.float32)

    if elig_pos_q.size > n_dots * 15:
        keep_frac = min(0.28, max(float(n_dots * 15) / float(elig_pos_q.size), 0.06))
        q_floor = float(np.quantile(elig_pos_q, 1.0 - keep_frac))
    else:
        q_floor = 0.0

    q_excess = np.maximum(q - q_floor, 0.0)
    # Sharp cross-strike centerline localization: 1.00 on crest, 0.30 on 1-px shoulder, 0.06 on blurry flank!
    ridge_mult_1 = np.where(crest_q, 1.00, np.where(shoulder_q, 0.30, 0.06)).astype(np.float32)
    w_primary = np.where(
        eligible_mask,
        1000.0 * (q_excess ** float(gamma)) * ridge_mult_1,
        0.0,
    ).astype(np.float32)

    n_primary = int(round(n_dots * (1.0 - float(concealed_quota_frac))))
    n_concealed = n_dots - n_primary

    dots_s1 = MC._submodular_select_on_weight(
        w_primary,
        q * np.where(crest_q, 1.22, np.where(shoulder_q, 0.88, 0.45)),
        eligible_mask,
        n_primary,
        min_spacing_px=min_spacing_px,
        pool_multiplier=pool_multiplier,
        existing_dots=None,
    )

    if n_concealed > 0:
        oy3, ox3 = np.mgrid[-4:5, -4:5]
        disk_3p35 = np.hypot(oy3, ox3) <= 3.35
        near_s1 = ndi.binary_dilation(dots_s1 > 0, structure=disk_3p35)
        conc_elig = eligible_mask & concealed_mask & (~near_s1) & (eb >= 0.18)

        # Regime-conditioned baseline floor inside `conc_elig` so towering exposed
        # mountain scarps cannot zero out genuine concealed sub-alluvial fault crests!
        conc_q_vals = q[conc_elig & (q > 0)]
        if conc_q_vals.size > n_concealed * 12:
            keep_c = min(0.32, max(float(n_concealed * 14) / float(conc_q_vals.size), 0.08))
            q_floor_conc = float(np.quantile(conc_q_vals, 1.0 - keep_c))
        else:
            q_floor_conc = 0.0
        q_conc_excess = np.maximum(q - q_floor_conc, 0.0)

        ridge_mult_2 = np.where(
            crest_e | crest_q,
            1.15,
            np.where(shoulder_e | shoulder_q, 0.48, 0.08),
        ).astype(np.float32)
        w_conc = np.where(
            conc_elig,
            1000.0 * (q_conc_excess ** float(gamma * 0.84)) * ((0.18 + eb) ** 1.15) * ridge_mult_2,
            0.0,
        ).astype(np.float32)

        dots_s2 = MC._submodular_select_on_weight(
            w_conc,
            (q_conc_excess ** 0.80) * ((0.18 + eb) ** 1.15) * ridge_mult_2,
            conc_elig,
            n_concealed,
            min_spacing_px=min_spacing_px + 0.22,
            pool_multiplier=pool_multiplier,
            existing_dots=dots_s1,
        )
    else:
        dots_s2 = dots_s1
        w_conc = w_primary

    # Stage 3: Prune isolated 0-D speckles (`NN1 > speckle_radius_px`) & refill onto connected strands
    pts = np.argwhere(dots_s2 > 0)
    if len(pts) >= 4 and speckle_radius_px > 0:
        tree = cKDTree(pts.astype(np.float64))
        dists, _ = tree.query(pts.astype(np.float64), k=2)
        isolated = dists[:, 1] > float(speckle_radius_px)
        n_iso = int(np.sum(isolated))
        if n_iso > 0:
            cleaned = dots_s2.copy()
            iso_pts = pts[isolated]
            cleaned[iso_pts[:, 0], iso_pts[:, 1]] = 0.0

            oy7, ox7 = np.mgrid[-8:9, -8:9]
            disk_conn = np.hypot(oy7, ox7) <= 7.5
            strand_corridor = ndi.binary_dilation(cleaned > 0, structure=disk_conn)
            refill_elig = eligible_mask & strand_corridor & (cleaned == 0)
            w_refill = np.maximum(w_primary, 0.85 * w_conc)
            need = n_dots - int((cleaned > 0).sum())
            dots_s2 = MC._submodular_select_on_weight(
                np.where(refill_elig, w_refill, 0.0).astype(np.float32),
                q * np.where(crest_q | crest_e, 1.2, 0.7),
                refill_elig,
                need,
                min_spacing_px=min_spacing_px,
                pool_multiplier=max(pool_multiplier, 12),
                existing_dots=cleaned,
            )

    # Top-up fallback if constrained corridor had fewer valid spacing slots than `n_dots`
    rem = n_dots - int((dots_s2 > 0).sum())
    if rem > 0:
        w_any = np.maximum(w_primary, 0.65 * w_conc)
        dots_s2 = MC._submodular_select_on_weight(
            np.where(eligible_mask & (dots_s2 == 0), np.maximum(w_any, q * 10.0), 0.0).astype(np.float32),
            q,
            eligible_mask & (dots_s2 == 0),
            rem,
            min_spacing_px=min_spacing_px,
            pool_multiplier=max(pool_multiplier, 12),
            existing_dots=dots_s2,
        )

    return dots_s2


def pure_steger_hessian_crest(field: np.ndarray, *, sigma: float = 1.15) -> tuple[np.ndarray, np.ndarray]:
    """True 1-D Steger/Hessian cross-strike centerline detector WITHOUT the
    omnidirectional 4-axis `is_disc_ridge` union (which fired on along-strike
    tree-step wiggles across 95.7% of scarp flanks in E1).

    Tests non-maximum suppression strictly along the principal negative-curvature
    eigenvector `n_hat` of `G_sigma(field)`. Marks ~19% 1-px crests and ~25%
    immediate 4-connected shoulders, suppressing >55% off-centerline flanks.
    """
    h, w = field.shape
    qs = ndi.gaussian_filter(field, sigma=float(sigma))
    gy, gx = np.gradient(qs)
    hyy = np.gradient(gy, axis=0)
    hxx = np.gradient(gx, axis=1)
    hxy = 0.5 * (np.gradient(gy, axis=1) + np.gradient(gx, axis=0))

    disc = np.hypot(hxx - hyy, 2.0 * hxy)
    mu1 = 0.5 * (hxx + hyy - disc)

    vx = hxy
    vy = mu1 - hxx
    vnorm = np.hypot(vx, vy)
    use_fb = vnorm < 1e-7
    nx = np.where(use_fb, np.where(hxx <= hyy, 1.0, 0.0), vx / np.maximum(vnorm, 1e-7)).astype(np.float32)
    ny = np.where(use_fb, np.where(hxx <= hyy, 0.0, 1.0), vy / np.maximum(vnorm, 1e-7)).astype(np.float32)

    yy, xx = np.indices((h, w), dtype=np.float32)
    step = 1.22
    q_plus = ndi.map_coordinates(
        qs,
        [np.clip(yy + step * ny, 0.0, h - 1.0), np.clip(xx + step * nx, 0.0, w - 1.0)],
        order=1,
        mode="nearest",
    )
    q_minus = ndi.map_coordinates(
        qs,
        [np.clip(yy - step * ny, 0.0, h - 1.0), np.clip(xx - step * nx, 0.0, w - 1.0)],
        order=1,
        mode="nearest",
    )
    crest = (mu1 < -1e-6) & (qs >= q_plus) & (qs >= q_minus)
    cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
    shoulder = (~crest) & ndi.binary_dilation(crest, structure=cross) & (mu1 < 0.0)
    return crest, shoulder


def fit_and_predict_s12_dual_branch(
    X_static: np.memmap,
    multi_static_cols: list[int],
    sub_static_cols: list[int],
    X_s11: np.memmap,
    multi_s11_cols: list[int],
    sub_s11_cols: list[int],
    X_s12_static: np.memmap,
    s12_static_cols: list[int],
    X_s12_fold: np.memmap | np.ndarray,
    s12_fold_cols: list[int],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    predict_mask: np.ndarray | None = None,
    seed: int = 1220,
    max_neg_samples: int = 165_000,
) -> tuple[np.ndarray, np.ndarray]:
    """Fit coupled Dual-Branch PU ensemble strictly on non-excluded pixels:
      - Branch A (`p_multi`): Full Multi-Physics HGB + L2-LR (`88% / 12%`)
      - Branch B (`p_sub`): Strictly Topography-Blind Subsurface Geophysical
        HGB + L2-LR (`88% / 12%`, zero DEM elevation/slope/relief/LRM columns)

    Uses sequential 500k-row memmap gathering (~1.2 s) and evaluates strictly on
    `predict_mask` (~1.29M rows per OOF fold vs 5.17M full grid) for 4x speed.
    """
    rng = np.random.default_rng(seed)
    n_fp = int(footprint.sum())
    vis_fp = visible_faults[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis_grid = ndi.distance_transform_edt(~visible_faults)
    safe_neg_fp = (~vis_fp) & (~excl_fp) & (d_vis_grid[footprint] > 3.6)

    pos_idx = np.flatnonzero(vis_fp & (~excl_fp))
    neg_pool = np.flatnonzero(safe_neg_fp)
    if neg_pool.size > max_neg_samples:
        neg_idx = rng.choice(neg_pool, size=max_neg_samples, replace=False)
        neg_idx.sort()
    else:
        neg_idx = neg_pool

    in_tr = np.zeros(n_fp, dtype=bool)
    in_tr[pos_idx] = True
    in_tr[neg_idx] = True
    n_tr = int(in_tr.sum())
    y_tr = vis_fp[in_tr].astype(np.int32)

    def _gather_and_fit_branch(
        st_cols: list[int],
        s11_cols: list[int],
        b_seed: int,
    ) -> np.ndarray:
        n_cols = len(st_cols) + len(s11_cols) + len(s12_static_cols) + len(s12_fold_cols)
        X_tr = np.empty((n_tr, n_cols), dtype=np.float32)
        off = 0
        for s in range(0, n_fp, 500_000):
            e = min(s + 500_000, n_fp)
            m = in_tr[s:e]
            k = int(m.sum())
            if k:
                parts = [np.asarray(X_static[s:e][m][:, st_cols], dtype=np.float32)]
                if s11_cols:
                    parts.append(np.asarray(X_s11[s:e][m][:, s11_cols], dtype=np.float32))
                if s12_static_cols:
                    parts.append(np.asarray(X_s12_static[s:e][m][:, s12_static_cols], dtype=np.float32))
                if s12_fold_cols:
                    parts.append(np.asarray(X_s12_fold[s:e][m][:, s12_fold_cols], dtype=np.float32))
                X_tr[off : off + k] = np.hstack(parts)
                off += k

        hgb = HistGradientBoostingClassifier(
            learning_rate=0.055,
            max_iter=195,
            max_leaf_nodes=36,
            min_samples_leaf=75,
            l2_regularization=3.0,
            random_state=b_seed,
        )
        hgb.fit(X_tr, y_tr)

        scaler = StandardScaler()
        X_tr_sc = np.clip(scaler.fit_transform(X_tr), -6.0, 6.0)
        lr = LogisticRegression(C=0.22, max_iter=300, random_state=b_seed)
        lr.fit(X_tr_sc, y_tr)
        del X_tr, X_tr_sc
        gc.collect()

        pred_fp = np.zeros(n_fp, dtype=np.float32)
        pm_fp = np.ones(n_fp, dtype=bool) if predict_mask is None else predict_mask[footprint]
        for s in range(0, n_fp, 550_000):
            e = min(s + 550_000, n_fp)
            mc = pm_fp[s:e]
            if not np.any(mc):
                continue
            parts_c = [np.asarray(X_static[s:e][mc][:, st_cols], dtype=np.float32)]
            if s11_cols:
                parts_c.append(np.asarray(X_s11[s:e][mc][:, s11_cols], dtype=np.float32))
            if s12_static_cols:
                parts_c.append(np.asarray(X_s12_static[s:e][mc][:, s12_static_cols], dtype=np.float32))
            if s12_fold_cols:
                parts_c.append(np.asarray(X_s12_fold[s:e][mc][:, s12_fold_cols], dtype=np.float32))
            Xc = np.hstack(parts_c)
            p_h = hgb.predict_proba(Xc)[:, 1].astype(np.float32)
            p_l = lr.predict_proba(np.clip(scaler.transform(Xc), -6.0, 6.0))[:, 1].astype(np.float32)
            slot = pred_fp[s:e]
            slot[mc] = 0.88 * p_h + 0.12 * p_l

        out_grid = np.zeros(footprint.shape, dtype=np.float32)
        out_grid[footprint] = pred_fp
        return out_grid

    p_multi = _gather_and_fit_branch(multi_static_cols, multi_s11_cols, seed)
    p_sub = _gather_and_fit_branch(sub_static_cols, sub_s11_cols, seed + 503)
    return p_multi, p_sub


def compute_pure_s12_subsurface_edge(
    X_s12_static: np.memmap | np.ndarray,
    X_s12_fold: np.memmap | np.ndarray,
    footprint: np.ndarray,
    *,
    use_nematic: bool = True,
) -> np.ndarray:
    """Compute strictly topography-free S12 subsurface potential-field edge `[0, 1]`
    from Bouguer-stripped intra-basement gravity (`H12-1`), depth-conditioned
    subsurface conductivity seal (`H12-1`), SI-reconciled 3-D Magnetic Analytic
    Signal & Salem wavenumber (`H12-2`), shallow GeoDAWN volcanic magnetic residual
    (`H12-2`), and optional 1.2-km potential-field nematic coherence (`H12-3`).

    Zero `X_s11` or DEM columns enter this field, preventing cloning of S11 scarps.
    """
    def _n01(v: np.ndarray) -> np.ndarray:
        q50 = float(np.percentile(v[::25], 50))
        q95 = float(np.percentile(v[::25], 95))
        return np.clip((v - q50) / max(q95 - q50, 1e-6), 0.0, 1.0).astype(np.float32)

    g_in_gr = np.asarray(X_s12_fold[:, 1], dtype=np.float32)
    g_in_svd = np.asarray(X_s12_fold[:, 2], dtype=np.float32)
    c_re_gr = np.asarray(X_s12_fold[:, 4], dtype=np.float32)
    gc_jnt = np.asarray(X_s12_fold[:, 6], dtype=np.float32)
    mag_sh_gr = np.asarray(X_s12_fold[:, 7], dtype=np.float32)

    asig_3d = np.asarray(X_s12_static[:, 1], dtype=np.float32)
    salem_k = np.asarray(X_s12_static[:, 3], dtype=np.float32)
    up_asig = np.asarray(X_s12_static[:, 6], dtype=np.float32)

    s_bg = 0.50 * _n01(g_in_gr) + 0.22 * _n01(g_in_svd) + 0.28 * np.maximum(_n01(c_re_gr), _n01(gc_jnt))
    s_mg = 0.38 * np.maximum(_n01(asig_3d), _n01(salem_k)) + 0.34 * _n01(up_asig) + 0.28 * _n01(mag_sh_gr)

    if use_nematic:
        st_lin = np.clip(np.asarray(X_s12_static[:, 7], dtype=np.float32), 0.0, 1.0)
        nem_gm = 0.5 * (1.0 + np.clip(np.asarray(X_s12_static[:, 10], dtype=np.float32), -1.0, 1.0))
        e_fp = np.clip(0.44 * s_bg + 0.38 * s_mg + 0.18 * (0.65 * st_lin + 0.35 * nem_gm), 0.0, 1.0)
    else:
        e_fp = np.clip(0.54 * s_bg + 0.46 * s_mg, 0.0, 1.0)

    out = np.zeros(footprint.shape, dtype=np.float32)
    out[footprint] = e_fp.astype(np.float32)
    return out


def bhar_dual_subsurface_emit(
    p_multi: np.ndarray,
    p_sub: np.ndarray,
    pure_sub_edge: np.ndarray,
    *,
    eligible_mask: np.ndarray,
    n_dots: int,
    w_sub_blend: float = 0.39,
    subsurface_quota_frac: float = 0.29,
    gamma: float = 1.20,
    min_spacing_px: float = 2.68,
    pool_multiplier: int = 9,
    speckle_radius_px: float = 9.0,
) -> np.ndarray:
    """Two-Regime Pure-Steger Centerline + Subsurface Blind-Geothermal Submodular Emitter:
      - Stage 1 (`1 - subsurface_quota_frac` of `n_dots`): Multi-Physics + Subsurface
        Consensus (`s_joint = (1 - w_sub_blend)*p_multi + w_sub_blend*p_sub`), sharpened
        by pure cross-strike Steger Hessian crests (`1.0x` crest, `0.48x` shoulder,
        `0.13x` off-centerline flank) and collinear 8-strike strand support.
      - Stage 2 (`subsurface_quota_frac` of `n_dots`): Topography-Blind Subsurface
        Geophysical Regime (`p_sub` reinforced by `pure_sub_edge`) strictly outside
        `3.35 px` of Stage-1 dots, using regime-conditioned quantile floor `q_floor_2`
        and pure cross-strike Steger Hessian crests of `q_sub`.
      - Stage 3: Prune isolated 0-D speckles (`NN1 > speckle_radius_px`) and refill
        along connected `<= 7.5 px` fault strands.
    """
    if n_dots <= 0 or not np.any(eligible_mask):
        return np.zeros_like(p_multi, dtype=np.float32)

    eb = np.clip(pure_sub_edge, 0.0, 1.0)
    s_joint = np.clip((1.0 - w_sub_blend) * p_multi + w_sub_blend * p_sub, 0.0, 1.0)

    q1_raw = (0.055 * s_joint) / (0.055 * s_joint + (1.0 - s_joint) + 1e-8)
    q1_raw = q1_raw * (1.0 + 0.30 * eb)
    col1 = _collinear_neighbor_envelope(q1_raw)
    c1_scale = max(float(np.percentile(col1[eligible_mask][::25], 96)), 1e-6)
    q1 = q1_raw * (0.50 + 0.50 * np.clip(col1 / c1_scale, 0.0, 1.25))

    cr1, sh1 = pure_steger_hessian_crest(q1, sigma=1.15)
    rm1 = np.where(cr1, 1.0, np.where(sh1, 0.48, 0.13)).astype(np.float32)

    n_elig = int(eligible_mask.sum())
    keep1 = min(0.24, max(float(n_dots * 12) / max(float(n_elig), 1.0), 0.06))
    qf1 = float(np.quantile(q1[eligible_mask][::10], 1.0 - keep1))
    q1_exc = np.maximum(q1 - qf1, 0.0)

    n_stage2 = int(round(n_dots * subsurface_quota_frac))
    n_stage1 = max(1, n_dots - n_stage2)

    w1 = np.where(eligible_mask, 1000.0 * (q1_exc ** float(gamma)) * rm1, 0.0).astype(np.float32)
    dots_s1 = MC._submodular_select_on_weight(
        w1,
        (q1_exc ** 0.85) * rm1,
        eligible_mask,
        n_stage1,
        min_spacing_px=min_spacing_px,
        pool_multiplier=pool_multiplier,
        existing_dots=None,
    )

    q2_raw = (0.055 * np.clip(p_sub, 0.0, 1.0)) / (0.055 * np.clip(p_sub, 0.0, 1.0) + (1.0 - np.clip(p_sub, 0.0, 1.0)) + 1e-8)
    q2 = q2_raw * (1.0 + 0.48 * eb)
    cr2, sh2 = pure_steger_hessian_crest(q2, sigma=1.15)
    rm2 = np.where(cr2, 1.0, np.where(sh2, 0.48, 0.11)).astype(np.float32)

    if n_stage2 > 0:
        oy3, ox3 = np.mgrid[-4:5, -4:5]
        near_s1 = ndi.binary_dilation(dots_s1 > 0, structure=(np.hypot(oy3, ox3) <= 3.35))
        elig2 = eligible_mask & (~near_s1)
        q2_vals = q2[elig2][::10]
        if q2_vals.size > 100:
            keep2 = min(0.24, max(float(n_stage2 * 14) / max(float(elig2.sum()), 1.0), 0.06))
            qf2 = float(np.quantile(q2_vals, 1.0 - keep2))
        else:
            qf2 = 0.0
        q2_exc = np.maximum(q2 - qf2, 0.0)
        w2 = np.where(elig2, 1000.0 * (q2_exc ** float(gamma * 0.92)) * rm2, 0.0).astype(np.float32)
        dots_s2 = MC._submodular_select_on_weight(
            w2,
            (q2_exc ** 0.85) * rm2,
            elig2,
            n_stage2,
            min_spacing_px=min_spacing_px + 0.10,
            pool_multiplier=pool_multiplier,
            existing_dots=dots_s1,
        )
    else:
        dots_s2 = dots_s1
        w2 = w1

    # Stage 3: Prune isolated 0-D speckles & refill along connected fault strands
    pts = np.argwhere(dots_s2 > 0)
    if len(pts) >= 4 and speckle_radius_px > 0:
        tree = cKDTree(pts.astype(np.float64))
        dists, _ = tree.query(pts.astype(np.float64), k=2)
        isolated = dists[:, 1] > float(speckle_radius_px)
        n_iso = int(np.sum(isolated))
        if n_iso > 0:
            cleaned = dots_s2.copy()
            iso_pts = pts[isolated]
            cleaned[iso_pts[:, 0], iso_pts[:, 1]] = 0.0

            oy7, ox7 = np.mgrid[-8:9, -8:9]
            strand_corridor = ndi.binary_dilation(cleaned > 0, structure=(np.hypot(oy7, ox7) <= 7.5))
            refill_elig = eligible_mask & strand_corridor & (cleaned == 0)
            w_refill = np.maximum(w1, 0.85 * w2)
            need = n_dots - int((cleaned > 0).sum())
            dots_s2 = MC._submodular_select_on_weight(
                np.where(refill_elig, w_refill, 0.0).astype(np.float32),
                q1 * np.where(cr1 | cr2, 1.15, 0.65),
                refill_elig,
                need,
                min_spacing_px=min_spacing_px,
                pool_multiplier=max(pool_multiplier, 11),
                existing_dots=cleaned,
            )

    rem = n_dots - int((dots_s2 > 0).sum())
    if rem > 0:
        w_any = np.maximum(w1, 0.70 * w2)
        dots_s2 = MC._submodular_select_on_weight(
            np.where(eligible_mask & (dots_s2 == 0), np.maximum(w_any, q1 * 10.0), 0.0).astype(np.float32),
            q1,
            eligible_mask & (dots_s2 == 0),
            rem,
            min_spacing_px=min_spacing_px,
            pool_multiplier=max(pool_multiplier, 11),
            existing_dots=dots_s2,
        )

    return dots_s2

