"""Session 17 (S17-CGRD): Cooper-Cowan Multi-Altitude Theta-Map / Hyperbolic-Tilt
Edge Invariants + DOE GDR-1391 Chemical Geothermometer Disequilibrium Upflow Plumes
+ Prior-Shift-Calibrated Subsurface Auto-Context (`IR-91-S15-06` & `IR-91-S15-07` Fix).

Every feature in the 26-column subsurface & hydrothermal core (`CGRD_SUBSURFACE_FEATURE_NAMES`)
is computed strictly from non-topographic subsurface geophysical fields (`B01`, `B02`, `B03`,
`B04`, `B05`, `B07`, `B08`, `B09`, `B10`, `B11`, `B13`, `B15`, `B16`, `B17`, `B18`) plus
geothermometer columns (`temp_c`, `geothermquartz_c`, `geothermchalc_c`, `geothermcat_c`)
from `data/external/gdr_wellspring_in_footprint.csv`.

Strict Leakage & Invariance Guarantees:
1. Topographic bands `Band 12` (`det_elev`) and `Band 19` (`det_elev_slope`) are NEVER read
   by `build_cgrd17_subsurface_features()`.
2. The leakage-prone column `dist_known_fault_px` in `gdr_wellspring_in_footprint.csv` is
   NEVER read or referenced.
3. Pairwise 2-quadrant Stage-1 sub-fold predictions are prior-shift calibrated via
   `gems91.ptha.prior_shift_calibrate_surface` BEFORE stitching the Stage-1 training
   auto-context grid (`IR-91-S15-06` remediation), and regional smoothed auto-context bowls
   (`>= 3 km`) are subtracted (`IR-91-S15-07` remediation).
"""

from __future__ import annotations

import csv
import gc
from pathlib import Path

import numpy as np
import rasterio
from scipy import fft as sp_fft
from scipy import ndimage as ndi
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression

from gems91 import ptha as PTHA

FORBIDDEN_TOPO_BANDS: frozenset[int] = frozenset({12, 19})
FORBIDDEN_CSV_COLUMNS: frozenset[str] = frozenset({"dist_known_fault_px"})

CGRD_SUBSURFACE_FEATURE_NAMES: list[str] = [
    # H17-1: Cooper-Cowan Multi-Altitude Theta-Map & Hyperbolic-Tilt (10 cols)
    "cgrd01_rtp_theta_200m",
    "cgrd02_rtp_theta_600m",
    "cgrd03_rtp_theta_1500m",
    "cgrd04_rtp_htd_600m",
    "cgrd05_rtp_dip_migration_200_1500m",
    "cgrd06_grv_theta_200m",
    "cgrd07_grv_theta_600m",
    "cgrd08_grv_theta_1500m",
    "cgrd09_grv_htd_600m",
    "cgrd10_grv_dip_migration_200_1500m",
    # H17-3: Cross-Potential Joint Theta & Strike Tensor Coherence (4 cols)
    "cgrd11_joint_theta_crest_600m",
    "cgrd12_joint_htd_product_600m",
    "cgrd13_subsurface_strike_coherence",
    "cgrd14_basin_neck_gradient_ratio",
    # H17-2: DOE GDR-1391 Chemical Geothermometer Disequilibrium Plumes (4 cols)
    "cgrd15_geotherm_diseq_plume_400m",
    "cgrd16_geotherm_diseq_plume_1p2km_local",
    "cgrd17_geotherm_diseq_x_theta_crest",
    "cgrd18_geotherm_cat_qtz_ratio_plume",
    # H17-4: Magnetite-Destruction Trough x B15-Deconfounded Clay Cap (4 cols)
    "cgrd19_mag_destruction_trough",
    "cgrd20_cond_b15_deconfounded",
    "cgrd21_alteration_conduit_index",
    "cgrd22_alteration_x_diseq_plume",
    # Subsurface strain / seismic / basement context (4 cols, no B12/B19)
    "cgrd23_strain_shear_dilatation_product",
    "cgrd24_seismic_ieq_deq_log_sum",
    "cgrd25_basement_depth_z",
    "cgrd26_rtp_grv_analytic_signal_ratio",
]

CGRD_AUTOCONTEXT_FEATURE_NAMES: list[str] = [
    # H17-5: Prior-Shift-Calibrated Subsurface Auto-Context (8 cols)
    "cgrd_ac01_cal_stage1_prob",
    "cgrd_ac02_cal_local_excess_300m",
    "cgrd_ac03_cal_local_excess_800m",
    "cgrd_ac04_cal_aniso_along_strike_600m",
    "cgrd_ac05_cal_aniso_along_strike_1200m",
    "cgrd_ac06_cal_ridge_laplacian_400m",
    "cgrd_ac07_cal_wash_bridge_product",
    "cgrd_ac08_cal_x_geotherm_diseq",
]


def _robust_z_footprint(
    arr: np.ndarray,
    footprint: np.ndarray,
    clip: float = 8.0,
) -> np.ndarray:
    """Median/IQR normalize inside footprint and zero outside footprint."""
    vals = arr[footprint].astype(np.float64, copy=False)
    med = float(np.median(vals))
    q25, q75 = np.percentile(vals, [25.0, 75.0])
    iqr = float(q75 - q25)
    if iqr < 1e-9:
        iqr = float(np.std(vals)) or 1.0
    out = np.zeros(arr.shape, dtype=np.float32)
    out[footprint] = np.clip((vals - med) / iqr, -clip, clip).astype(np.float32)
    return out


def _clean_subsurface_band(
    src: rasterio.DatasetReader,
    band_idx: int,
    footprint: np.ndarray,
) -> np.ndarray:
    """Read a subsurface band, enforcing the strict ban on topographic bands B12 and B19."""
    if band_idx in FORBIDDEN_TOPO_BANDS:
        raise PermissionError(
            f"Band {band_idx} is a forbidden topographic band in CGRD subsurface lane."
        )
    raw = src.read(band_idx).astype(np.float32, copy=False)
    valid = np.isfinite(raw) & (np.abs(raw) < 1e30) & footprint
    out = np.zeros(raw.shape, dtype=np.float32)
    if not np.any(valid):
        return out
    med = float(np.median(raw[valid]))
    out[valid] = raw[valid]
    missing = footprint & (~valid)
    if np.any(missing):
        _, idx = ndi.distance_transform_edt(~valid, return_indices=True)
        out[missing] = out[idx[0][missing], idx[1][missing]]
    out[~footprint] = med
    return out


def cooper_cowan_theta_and_htd(
    field: np.ndarray,
    footprint: np.ndarray,
    *,
    pixel_size_m: float = 100.0,
    altitudes_m: tuple[float, float, float] = (200.0, 600.0, 1500.0),
    pad: int = 64,
) -> dict[str, np.ndarray]:
    """Compute Cooper-Cowan (2006, 2008) multi-altitude Theta-Map (`cos(theta)`)
    and Hyperbolic Tilt Derivative (`HTD`) plus cross-altitude dip migration
    using native single-precision (`float32`/`complex64`) FFTs.
    """
    z_in = _robust_z_footprint(field, footprint)
    padded = np.pad(z_in, pad, mode="reflect").astype(np.float32, copy=False)
    del z_in
    hp, wp = padded.shape

    wy = np.sin(np.linspace(0.0, np.pi, hp, dtype=np.float32)) ** 2
    wx = np.sin(np.linspace(0.0, np.pi, wp, dtype=np.float32)) ** 2
    windowed = (padded - np.float32(padded.mean())) * wy[:, None] * wx[None, :]
    del padded

    # Single-precision 2D real FFT (complex64)
    F0 = sp_fft.rfft2(windowed, workers=2)
    del windowed
    ky = (2.0 * np.pi * np.fft.fftfreq(hp, d=pixel_size_m)).astype(np.float32)[:, None]
    kx = (2.0 * np.pi * np.fft.rfftfreq(wp, d=pixel_size_m)).astype(np.float32)[None, :]
    k = np.hypot(kx, ky).astype(np.float32)

    eps = np.float32(1e-6)
    theta_raw_list: list[np.ndarray] = []
    out: dict[str, np.ndarray] = {}

    for z_m in altitudes_m:
        att = np.exp(-k * np.float32(z_m)).astype(np.float32)
        Fz = F0 * att
        del att
        fx = sp_fft.irfft2(Fz * (1j * kx), s=(hp, wp), workers=2)[
            pad : hp - pad, pad : wp - pad
        ]
        fy = sp_fft.irfft2(Fz * (1j * ky), s=(hp, wp), workers=2)[
            pad : hp - pad, pad : wp - pad
        ]
        fz = sp_fft.irfft2(Fz * k, s=(hp, wp), workers=2)[
            pad : hp - pad, pad : wp - pad
        ]
        del Fz

        thg = np.hypot(fx, fy)
        del fx, fy
        analytic_amp = np.sqrt(thg * thg + fz * fz + eps)
        cos_theta = (thg / analytic_amp).astype(np.float32)
        cos_theta[~footprint] = 0.0
        theta_raw_list.append(cos_theta)

        tag = f"{int(round(z_m))}m"
        out[f"theta_{tag}"] = _robust_z_footprint(cos_theta, footprint)
        out[f"raw_theta_{tag}"] = cos_theta

        if int(round(z_m)) == 600:
            ratio = np.clip(fz / (thg + eps), -0.98, 0.98)
            htd_raw = np.arctanh(ratio).astype(np.float32)
            del ratio
            htd_edges = np.exp(-np.square(htd_raw / np.float32(0.45))).astype(np.float32)
            del htd_raw
            htd_edges[~footprint] = 0.0
            out["htd_600m"] = _robust_z_footprint(htd_edges, footprint)
            out["raw_htd_600m"] = htd_edges
            out["raw_analytic_600m"] = analytic_amp
        else:
            del analytic_amp
        del thg, fz

    del F0, kx, ky, k
    dip_mig = np.abs(theta_raw_list[0] - theta_raw_list[2]).astype(np.float32)
    dip_mig_smooth = ndi.gaussian_filter(dip_mig, sigma=2.5).astype(np.float32)
    del dip_mig, theta_raw_list
    out["dip_migration"] = _robust_z_footprint(dip_mig_smooth, footprint)
    del dip_mig_smooth
    return out


def subsurface_strike_tensor(
    rtp: np.ndarray,
    grv: np.ndarray,
    bsm: np.ndarray,
    footprint: np.ndarray,
    sigma_grad: float = 2.0,
    sigma_tensor: float = 5.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute dominant subsurface fault strike director `(cos 2*theta, sin 2*theta)`
    and structural coherence from RTP magnetics (`B02`), isostatic gravity (`B13`),
    and depth-to-basement (`B15`) — strictly excluding topographic bands `B12`/`B19`.
    """
    jxx = np.zeros(rtp.shape, dtype=np.float32)
    jyy = np.zeros(rtp.shape, dtype=np.float32)
    jxy = np.zeros(rtp.shape, dtype=np.float32)

    for fld, w in ((rtp, 0.40), (grv, 0.40), (bsm, 0.20)):
        zf = _robust_z_footprint(fld, footprint)
        gy = ndi.gaussian_filter(zf, sigma=sigma_grad, order=[1, 0])
        gx = ndi.gaussian_filter(zf, sigma=sigma_grad, order=[0, 1])
        del zf
        jxx += np.float32(w) * (gx * gx)
        jyy += np.float32(w) * (gy * gy)
        jxy += np.float32(w) * (gx * gy)
        del gx, gy

    jxx = ndi.gaussian_filter(jxx, sigma=sigma_tensor)
    jyy = ndi.gaussian_filter(jyy, sigma=sigma_tensor)
    jxy = ndi.gaussian_filter(jxy, sigma=sigma_tensor)

    diff = jxx - jyy
    two_jxy = 2.0 * jxy
    norm = np.hypot(diff, two_jxy) + np.float32(1e-6)
    tr = jxx + jyy + np.float32(1e-6)
    del jxx, jyy, jxy
    coherence = np.clip(norm / tr, 0.0, 1.0).astype(np.float32)
    del tr

    cos2_strike = (-diff / norm).astype(np.float32)
    sin2_strike = (-two_jxy / norm).astype(np.float32)
    del diff, two_jxy, norm
    coherence[~footprint] = 0.0
    cos2_strike[~footprint] = 0.0
    sin2_strike[~footprint] = 0.0
    return cos2_strike, sin2_strike, coherence


def _anisotropic_strike_plume(
    impulse: np.ndarray,
    cos2_strike: np.ndarray,
    sin2_strike: np.ndarray,
    footprint: np.ndarray,
    sigma_along_px: float,
    sigma_cross_px: float = 2.0,
) -> np.ndarray:
    """Steered anisotropic smoothing along the subsurface strike tensor."""
    base = ndi.gaussian_filter(impulse, sigma=sigma_cross_px)
    c0 = ndi.gaussian_filter(base, sigma=(sigma_cross_px, sigma_along_px))
    c90 = ndi.gaussian_filter(base, sigma=(sigma_along_px, sigma_cross_px))
    f1 = ndi.gaussian_filter(base, sigma=sigma_along_px * 0.72)
    del base
    c45 = 0.5 * (
        np.roll(np.roll(f1, 2, axis=0), 2, axis=1)
        + np.roll(np.roll(f1, -2, axis=0), -2, axis=1)
    )
    c135 = 0.5 * (
        np.roll(np.roll(f1, 2, axis=0), -2, axis=1)
        + np.roll(np.roll(f1, -2, axis=0), 2, axis=1)
    )
    del f1
    iso = 0.5 * (c0 + c90)
    aniso = (
        iso
        + 0.5 * cos2_strike * (c0 - c90)
        + 0.5 * sin2_strike * (c45 - c135)
    ).astype(np.float32)
    del c0, c90, c45, c135, iso
    aniso[~footprint] = 0.0
    return aniso


def geothermometer_disequilibrium_plumes(
    gdr_csv_path: str | Path,
    cos2_strike: np.ndarray,
    sin2_strike: np.ndarray,
    footprint: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Build local anisotropic chemical geothermometer disequilibrium (`Delta_T_eq`)
    upflow plumes from `data/external/gdr_wellspring_in_footprint.csv`.

    Strictly ignores `dist_known_fault_px` (`FORBIDDEN_CSV_COLUMNS`).
    """
    h, w = footprint.shape
    diseq_imp = np.zeros((h, w), dtype=np.float32)
    ratio_imp = np.zeros((h, w), dtype=np.float32)

    allowed_cols = (
        "row",
        "col",
        "temp_c",
        "geothermquartz_c",
        "geothermchalc_c",
        "geothermcat_c",
    )
    n_rows_total = 0
    n_diseq_sites = 0

    with Path(gdr_csv_path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            n_rows_total += 1
            r = int(float(row["row"]))
            c = int(float(row["col"]))
            if not (0 <= r < h and 0 <= c < w and footprint[r, c]):
                continue

            def _parse_temp(key: str) -> float:
                if key in FORBIDDEN_CSV_COLUMNS:
                    raise PermissionError(f"Forbidden column {key}")
                val_s = (row.get(key) or "").strip()
                if not val_s:
                    return np.nan
                try:
                    val = float(val_s)
                except ValueError:
                    return np.nan
                return val if (0.0 < val < 450.0) else np.nan

            t_surf = _parse_temp("temp_c")
            t_qtz = _parse_temp("geothermquartz_c")
            t_chc = _parse_temp("geothermchalc_c")
            t_cat = _parse_temp("geothermcat_c")

            chem_temps = [t for t in (t_qtz, t_chc, t_cat) if np.isfinite(t)]
            if not chem_temps:
                if np.isfinite(t_surf) and t_surf > 30.0:
                    delta_t = max(t_surf - 20.0, 0.0)
                else:
                    continue
            else:
                t_res = max(chem_temps)
                base_t = t_surf if np.isfinite(t_surf) else 15.0
                delta_t = max(t_res - base_t, 0.0) + 0.35 * max(t_res - 50.0, 0.0)

            if delta_t > 5.0:
                n_diseq_sites += 1
                amp = float(np.log1p(delta_t))
                if amp > diseq_imp[r, c]:
                    diseq_imp[r, c] = np.float32(amp)

            if np.isfinite(t_cat) and np.isfinite(t_qtz) and t_qtz > 25.0:
                rat = float(np.clip((t_cat - t_qtz) / 50.0 + 1.0, 0.1, 4.0))
                if rat > ratio_imp[r, c]:
                    ratio_imp[r, c] = np.float32(rat)

    plume_400m = _anisotropic_strike_plume(
        diseq_imp, cos2_strike, sin2_strike, footprint, sigma_along_px=4.0, sigma_cross_px=1.8
    )
    plume_1p2km_raw = _anisotropic_strike_plume(
        diseq_imp, cos2_strike, sin2_strike, footprint, sigma_along_px=12.0, sigma_cross_px=3.5
    )
    del diseq_imp
    regional_bowl_3p6km = ndi.gaussian_filter(plume_1p2km_raw, sigma=36.0)
    plume_1p2km_local = np.maximum(
        plume_1p2km_raw - 0.85 * regional_bowl_3p6km, 0.0
    ).astype(np.float32)
    del plume_1p2km_raw, regional_bowl_3p6km
    plume_1p2km_local[~footprint] = 0.0

    ratio_plume = _anisotropic_strike_plume(
        ratio_imp, cos2_strike, sin2_strike, footprint, sigma_along_px=8.0, sigma_cross_px=2.5
    )
    del ratio_imp
    ratio_bowl = ndi.gaussian_filter(ratio_plume, sigma=30.0)
    ratio_local = np.maximum(ratio_plume - 0.80 * ratio_bowl, 0.0).astype(np.float32)
    del ratio_plume, ratio_bowl
    ratio_local[~footprint] = 0.0

    receipt = {
        "csv_rows_scanned": n_rows_total,
        "n_disequilibrium_sites": n_diseq_sites,
        "columns_accessed": list(allowed_cols),
        "forbidden_columns_accessed": [],
    }
    return (
        _robust_z_footprint(plume_400m, footprint),
        _robust_z_footprint(plume_1p2km_local, footprint),
        _robust_z_footprint(ratio_local, footprint),
        receipt,
    )


def build_cgrd17_subsurface_features(
    features_tif_path: str | Path,
    gdr_csv_path: str | Path,
    footprint: np.ndarray,
    out_matrix: np.ndarray | None = None,
) -> tuple[np.ndarray, list[str], dict[str, np.ndarray], dict]:
    """Build the 26-column S17-CGRD pure-subsurface + geothermometer-plume feature matrix
    (`n_footprint, 26`) in float32 with a small peak memory footprint (<1.2 GB).

    Strictly reads ONLY subsurface bands `{1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 15, 16, 17, 18}`
    and NEVER touches `Band 12` (`det_elev`) or `Band 19` (`det_elev_slope`).
    """
    n_fp = int(footprint.sum())
    X = (
        out_matrix
        if out_matrix is not None
        else np.empty((n_fp, len(CGRD_SUBSURFACE_FEATURE_NAMES)), dtype=np.float32)
    )
    bands_read: list[int] = []

    with rasterio.open(features_tif_path) as src:
        def _get(b: int) -> np.ndarray:
            bands_read.append(b)
            return _clean_subsurface_band(src, b, footprint)

        b02_rtp = _get(2)
        b13_grv = _get(13)
        b15_bsm = _get(15)

        # 1. H17-1: Cooper-Cowan Multi-Altitude Theta-Map & HTD on B02 (RTP)
        cc_rtp = cooper_cowan_theta_and_htd(b02_rtp, footprint)
        X[:, 0] = cc_rtp["theta_200m"][footprint]
        X[:, 1] = cc_rtp["theta_600m"][footprint]
        X[:, 2] = cc_rtp["theta_1500m"][footprint]
        X[:, 3] = cc_rtp["htd_600m"][footprint]
        X[:, 4] = cc_rtp["dip_migration"][footprint]
        rtp_raw_theta_600 = cc_rtp["raw_theta_600m"]
        rtp_raw_htd_600 = cc_rtp["raw_htd_600m"]
        rtp_raw_analytic_600 = cc_rtp["raw_analytic_600m"]
        del cc_rtp
        gc.collect()

        # Cooper-Cowan Multi-Altitude Theta-Map & HTD on B13 (Isostatic Gravity)
        cc_grv = cooper_cowan_theta_and_htd(b13_grv, footprint)
        X[:, 5] = cc_grv["theta_200m"][footprint]
        X[:, 6] = cc_grv["theta_600m"][footprint]
        X[:, 7] = cc_grv["theta_1500m"][footprint]
        X[:, 8] = cc_grv["htd_600m"][footprint]
        X[:, 9] = cc_grv["dip_migration"][footprint]
        grv_raw_theta_600 = cc_grv["raw_theta_600m"]
        grv_raw_htd_600 = cc_grv["raw_htd_600m"]
        grv_raw_analytic_600 = cc_grv["raw_analytic_600m"]
        del cc_grv
        gc.collect()

        # 2. H17-3: Cross-Potential Joint Theta Crest & Subsurface Strike Tensor
        joint_theta_raw = np.sqrt(
            np.clip(rtp_raw_theta_600 * grv_raw_theta_600, 0.0, 1.0)
        ).astype(np.float32)
        del rtp_raw_theta_600, grv_raw_theta_600
        joint_htd_raw = (rtp_raw_htd_600 * grv_raw_htd_600).astype(np.float32)
        del rtp_raw_htd_600, grv_raw_htd_600

        X[:, 10] = _robust_z_footprint(joint_theta_raw, footprint)[footprint]
        X[:, 11] = _robust_z_footprint(joint_htd_raw, footprint)[footprint]
        del joint_htd_raw

        cos2_strike, sin2_strike, strike_coh = subsurface_strike_tensor(
            b02_rtp, b13_grv, b15_bsm, footprint
        )
        del b13_grv
        X[:, 12] = _robust_z_footprint(strike_coh, footprint)[footprint]
        del strike_coh

        # Basin-neck gradient ratio: B15 gradient vs B18 gravity horizontal gradient
        b18_grv_hg = _get(18)
        bsm_z = _robust_z_footprint(b15_bsm, footprint)
        bsm_gy = ndi.gaussian_filter(bsm_z, sigma=2.0, order=[1, 0])
        bsm_gx = ndi.gaussian_filter(bsm_z, sigma=2.0, order=[0, 1])
        bsm_grad = np.hypot(bsm_gx, bsm_gy).astype(np.float32)
        del bsm_gx, bsm_gy
        grv_hg_pos = np.maximum(_robust_z_footprint(b18_grv_hg, footprint) + 1.5, 0.0)
        del b18_grv_hg
        X[:, 13] = _robust_z_footprint(
            np.sqrt(bsm_grad * grv_hg_pos), footprint
        )[footprint]
        del bsm_grad, grv_hg_pos
        X[:, 24] = bsm_z[footprint]

        # Analytic signal ratio (B02 vs B13 at 600 m)
        as_ratio = np.log1p(rtp_raw_analytic_600) - np.log1p(grv_raw_analytic_600)
        del rtp_raw_analytic_600, grv_raw_analytic_600
        X[:, 25] = _robust_z_footprint(as_ratio, footprint)[footprint]
        del as_ratio
        gc.collect()

        # 3. H17-2: DOE GDR-1391 Chemical Geothermometer Disequilibrium Plumes
        diseq_400m_z, diseq_1p2km_z, ratio_800m_z, gdr_receipt = (
            geothermometer_disequilibrium_plumes(
                gdr_csv_path, cos2_strike, sin2_strike, footprint
            )
        )
        del cos2_strike, sin2_strike
        X[:, 14] = diseq_400m_z[footprint]
        del diseq_400m_z
        X[:, 15] = diseq_1p2km_z[footprint]
        X[:, 17] = ratio_800m_z[footprint]
        del ratio_800m_z

        diseq_pos = np.maximum(diseq_1p2km_z, 0.0).astype(np.float32)
        del diseq_1p2km_z
        X[:, 16] = _robust_z_footprint(
            diseq_pos * joint_theta_raw, footprint
        )[footprint]

        # 4. H17-4: Magnetite-Destruction Trough x B15-Deconfounded B17 Clay Cap
        b03_tmi_hg = _get(3)
        b17_cond = _get(17)
        rtp_local_bg = ndi.gaussian_filter(b02_rtp, sigma=7.0)
        mag_trough_raw = np.maximum(rtp_local_bg - b02_rtp, 0.0)
        del b02_rtp, rtp_local_bg
        tmi_hg_pos = np.maximum(_robust_z_footprint(b03_tmi_hg, footprint) + 1.0, 0.1)
        del b03_tmi_hg
        mag_destruction_z = _robust_z_footprint(
            mag_trough_raw * np.sqrt(tmi_hg_pos), footprint
        )
        del mag_trough_raw, tmi_hg_pos
        X[:, 18] = mag_destruction_z[footprint]

        cond_z = _robust_z_footprint(b17_cond, footprint)
        del b17_cond, b15_bsm
        fp_b = bsm_z[footprint].astype(np.float64)
        fp_c = cond_z[footprint].astype(np.float64)
        del bsm_z
        slope_cb = float(np.cov(fp_b, fp_c)[0, 1] / (np.var(fp_b) + 1e-6))
        cond_resid = np.zeros(footprint.shape, dtype=np.float32)
        cond_resid[footprint] = (
            fp_c - ( fp_c.mean() + slope_cb * (fp_b - fp_b.mean()) )
        ).astype(np.float32)
        del fp_b, fp_c, cond_z
        cond_deconf_z = _robust_z_footprint(cond_resid, footprint)
        del cond_resid
        X[:, 19] = cond_deconf_z[footprint]

        alt_conduit_raw = (
            np.maximum(mag_destruction_z, 0.0)
            * np.maximum(cond_deconf_z, 0.0)
            * joint_theta_raw
        ).astype(np.float32)
        del mag_destruction_z, cond_deconf_z
        alt_conduit_z = _robust_z_footprint(alt_conduit_raw, footprint)
        del alt_conduit_raw
        X[:, 20] = alt_conduit_z[footprint]
        X[:, 21] = _robust_z_footprint(
            np.maximum(alt_conduit_z, 0.0) * (0.25 + diseq_pos), footprint
        )[footprint]
        del alt_conduit_z
        gc.collect()

        # 5. Subsurface strain & seismicity context (no B12/B19)
        b04_2ndinv = _get(4)
        b07_shear = _get(7)
        b08_dilate = _get(8)
        strain_prod = (
            _robust_z_footprint(b04_2ndinv, footprint)
            + 0.5 * _robust_z_footprint(b07_shear, footprint)
            + 0.5 * np.abs(_robust_z_footprint(b08_dilate, footprint))
        ).astype(np.float32)
        del b04_2ndinv, b07_shear, b08_dilate
        X[:, 22] = _robust_z_footprint(strain_prod, footprint)[footprint]
        del strain_prod

        b10_deq = _get(10)
        b16_ieq = _get(16)
        seis_sum = (
            _robust_z_footprint(np.log1p(np.maximum(b10_deq, 0.0)), footprint)
            + _robust_z_footprint(np.log1p(np.maximum(b16_ieq, 0.0)), footprint)
        ).astype(np.float32)
        del b10_deq, b16_ieq
        X[:, 23] = _robust_z_footprint(seis_sum, footprint)[footprint]
        del seis_sum
        gc.collect()

    assert set(bands_read).isdisjoint(FORBIDDEN_TOPO_BANDS), (
        f"Forbidden topographic bands read: {set(bands_read) & FORBIDDEN_TOPO_BANDS}"
    )
    if isinstance(X, np.memmap):
        X.flush()

    aux = {
        "joint_theta_raw": joint_theta_raw,
        "diseq_1p2km_pos": diseq_pos,
    }
    receipt = {
        "n_features": len(CGRD_SUBSURFACE_FEATURE_NAMES),
        "feature_names": list(CGRD_SUBSURFACE_FEATURE_NAMES),
        "bands_read": sorted(set(bands_read)),
        "forbidden_topo_bands_excluded": sorted(FORBIDDEN_TOPO_BANDS),
        "gdr_receipt": gdr_receipt,
    }
    return X, list(CGRD_SUBSURFACE_FEATURE_NAMES), aux, receipt


def extract_calibrated_subsurface_autocontext(
    calibrated_stage1_2d: np.ndarray,
    joint_theta_raw: np.ndarray,
    diseq_1p2km_pos: np.ndarray,
    footprint: np.ndarray,
) -> np.ndarray:
    """Extract 8 local (`<= 1.8 km`) auto-context bridge features from a
    PRIOR-SHIFT-CALIBRATED Stage-1 subsurface probability surface (`IR-91-S15-06`
    and `IR-91-S15-07` remediation).
    """
    p = np.where(footprint, np.clip(calibrated_stage1_2d, 0.0, 1.0), 0.0).astype(
        np.float32
    )
    s_300m = ndi.gaussian_filter(p, sigma=3.0)
    s_800m = ndi.gaussian_filter(p, sigma=8.0)
    bowl_3p2km = ndi.gaussian_filter(p, sigma=32.0)

    local_300m = np.maximum(s_300m - 0.85 * bowl_3p2km, 0.0).astype(np.float32)
    local_800m = np.maximum(s_800m - 0.90 * bowl_3p2km, 0.0).astype(np.float32)
    del s_800m, bowl_3p2km

    c0_6 = ndi.gaussian_filter(p, sigma=(1.5, 6.0))
    c90_6 = ndi.gaussian_filter(p, sigma=(6.0, 1.5))
    aniso_600m = np.maximum(c0_6, c90_6) - 0.5 * (c0_6 + c90_6)
    del c0_6, c90_6

    c0_12 = ndi.gaussian_filter(p, sigma=(2.0, 12.0))
    c90_12 = ndi.gaussian_filter(p, sigma=(12.0, 2.0))
    aniso_1200m = np.maximum(c0_12, c90_12) - 0.5 * (c0_12 + c90_12)
    del c0_12, c90_12

    ridge_lap = np.maximum(
        -ndi.gaussian_laplace(s_300m, sigma=2.5), 0.0
    ).astype(np.float32)
    del s_300m
    wash_bridge = (aniso_1200m * joint_theta_raw).astype(np.float32)
    ac_x_diseq = (local_800m * (0.20 + diseq_1p2km_pos)).astype(np.float32)

    n_fp = int(footprint.sum())
    X_ac = np.empty((n_fp, len(CGRD_AUTOCONTEXT_FEATURE_NAMES)), dtype=np.float32)
    for idx, g in enumerate(
        (
            p,
            local_300m,
            local_800m,
            aniso_600m,
            aniso_1200m,
            ridge_lap,
            wash_bridge,
            ac_x_diseq,
        )
    ):
        X_ac[:, idx] = _robust_z_footprint(g, footprint)[footprint]
    return X_ac


def fit_predict_calibrated_cgrd(
    X_train_blocks: list[np.ndarray],
    X_infer_blocks: list[np.ndarray],
    visible_faults: np.ndarray,
    exclude_mask: np.ndarray,
    footprint: np.ndarray,
    *,
    neg_Pos_ratio: int = 5,
    safe_neg_collar_px: float = 3.5,
    seed: int = 9117,
) -> tuple[np.ndarray, dict[str, float]]:
    """Train a fold-safe HGB + L2 Logistic Regression ensemble on `visible_faults`
    outside `exclude_mask`, predict across `footprint`, and immediately apply
    Elkan-Noto / Bayes prior-shift calibration (`PTHA.prior_shift_calibrate_surface`)
    to maps from the `1:neg_Pos_ratio` training sample prior to the true spatial prior.
    """
    rng = np.random.default_rng(seed)
    vis_fp = (visible_faults & (~exclude_mask))[footprint]
    excl_fp = exclude_mask[footprint]

    d_vis = ndi.distance_transform_edt(~visible_faults)
    safe_neg_fp = ((d_vis > safe_neg_collar_px) & (~exclude_mask) & footprint)[footprint]
    del d_vis

    pos_idx = np.flatnonzero(vis_fp)
    neg_pool = np.flatnonzero(safe_neg_fp)
    n_pos = int(pos_idx.size)
    n_neg = min(int(neg_pool.size), max(n_pos * neg_Pos_ratio, 1000))
    neg_idx = rng.choice(neg_pool, size=n_neg, replace=False)

    tr_idx = np.concatenate([pos_idx, neg_idx])
    y_tr = np.concatenate(
        [np.ones(n_pos, dtype=np.int32), np.zeros(n_neg, dtype=np.int32)]
    )
    perm = rng.permutation(tr_idx.size)
    tr_idx = tr_idx[perm]
    y_tr = y_tr[perm]

    X_tr = np.hstack([blk[tr_idx] for blk in X_train_blocks]).astype(
        np.float32, copy=False
    )

    hgb = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.06,
        max_leaf_nodes=31,
        min_samples_leaf=80,
        l2_regularization=3.0,
        random_state=seed,
    )
    hgb.fit(X_tr, y_tr)

    lr = LogisticRegression(C=0.20, max_iter=250, random_state=seed)
    lr.fit(X_tr, y_tr)
    del X_tr

    n_fp = int(footprint.sum())
    raw_prob_fp = np.empty(n_fp, dtype=np.float32)
    chunk = 450_000
    for s in range(0, n_fp, chunk):
        e = min(s + chunk, n_fp)
        X_ch = np.hstack([blk[s:e] for blk in X_infer_blocks]).astype(
            np.float32, copy=False
        )
        p_hgb = hgb.predict_proba(X_ch)[:, 1]
        p_lr = lr.predict_proba(X_ch)[:, 1]
        raw_prob_fp[s:e] = (0.78 * p_hgb + 0.22 * p_lr).astype(np.float32)

    raw_2d = np.zeros(footprint.shape, dtype=np.float32)
    raw_2d[footprint] = raw_prob_fp

    n_active_domain = max(int((~excl_fp).sum()), 1)
    pi_true = float(np.clip(n_pos / n_active_domain, 0.002, 0.05))
    pi_sample = float(n_pos / max(n_pos + n_neg, 1))

    cal_2d = PTHA.prior_shift_calibrate_surface(
        raw_2d,
        footprint,
        pi_sample=pi_sample,
        pi_true=pi_true,
    )
    meta = {
        "n_pos": float(n_pos),
        "n_neg": float(n_neg),
        "pi_sample": round(pi_sample, 6),
        "pi_true": round(pi_true, 6),
        "mean_raw_prob": round(float(raw_2d[footprint].mean()), 6),
        "mean_calibrated_prob": round(float(cal_2d[footprint].mean()), 6),
    }
    return cal_2d, meta
