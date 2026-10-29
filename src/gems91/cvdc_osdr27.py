"""S27-CVDC: Rule-of-V Contour–Potential-Field Tangent Discordance (CVDC),
Odd-Symmetric Cross-Strike Dip-Reversal (OSDR), and Multi-Valley Scarp-Strain
Coupling (MVSD).

Preregistered in docs/s27/preregistration.md BEFORE execution:
  * 100% catalogue-independent: zero fault coordinates enter any feature.
  * Declared-NoData sentinels (non-finite or |value| >= 1e30) are excluded
    from every filter via masked normalised convolution (gems91.cckm24) and
    morphological support erosion beyond each operator's spatial radius.
  * Band 06 ('tc') is treated strictly as GeoDAWN airborne radiometric Total
    Count exposure (IR-91-S12-04; pixel range [2.953, 88.57]), NEVER as a
    magnetic tilt angle.
  * Band 15 ('depth_to_base_surf') is treated strictly as DrivenData's depth
    to conductive base, NEVER as drill-confirmed crystalline basement depth.
  * All 26 Pure-Subsurface static features have bitwise 0.0 dependence on
    Band 12 ('det_elev') and Band 19 ('det_elev_slope').

Named non-fault mimics: discordant volcanic feeder dikes / pluton walls (CVDC),
unfaulted dipping ash-flow tuff contacts and GeoDAWN survey seams (OSDR), and
Pleistocene Lake Lahontan wave-cut shorelines / coalescing fan toes (MVSD).
Nothing here directly observes geothermal vents or productive reservoirs.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window
from scipy import ndimage as ndi

from gems91.cckm24 import EXTREME_CUTOFF, _masked_blur, _rank01, _sample_offset, valid_mask

# 1-based band indices -> 0-based array indices
SUBSURFACE_BANDS_1BASED: tuple[tuple[int, str], ...] = (
    (1, "raw_B01_tile"),
    (2, "raw_B02_rtp"),
    (3, "raw_B03_thd"),
    (4, "raw_B04_maxshear"),
    (5, "raw_B05_si"),
    (6, "raw_B06_rad_tc"),
    (7, "raw_B07_ss_maxshear"),
    (8, "raw_B08_dilatation"),
    (9, "raw_B09_mag_density"),
    (10, "raw_B10_eq_w"),
    (11, "raw_B11_grav_vg"),
    (13, "raw_B13_grav_iso"),
    (14, "raw_B14_tmi"),
    (15, "raw_B15_cond_base_depth"),
    (16, "raw_B16_eq_uw"),
    (17, "raw_B17_cond_surf"),
    (18, "raw_B18_grav_hg"),
)

PURE_SUBSURFACE_NAMES: tuple[str, ...] = tuple(name for _, name in SUBSURFACE_BANDS_1BASED) + (
    "sub_grad_rtp_b02",
    "sub_grad_grav_b13",
    "sub_grad_tmi_b14",
    "osdr_grav_step_w5",
    "osdr_rtp_step_w5",
    "osdr_grav_rtp_sign_lock",
    "osdr_b15_hangingwall_align",
    "osdr_cond_b15_resid_step",
    "osdr_transtension_conduit",
)

TOPO_DISCORDANCE_NAMES: tuple[str, ...] = (
    "raw_B12_det_elev",
    "raw_B19_det_slope",
    "topo_grad_elev_b12",
    "cvdc_sin2_elev_grav_s1p5",
    "cvdc_sin2_elev_grav_s3p5",
    "cvdc_sin2_elev_rtp_s3p5",
    "cvdc_multiscale_persist",
    "cvdc_transverse_slope_jump",
    "mvsd_strike_persist_l9",
    "mvsd_strike_persist_l17",
    "mvsd_valley_bridge_product",
    "mvsd_cover_index",
)

ALL_STATIC_NAMES: tuple[str, ...] = PURE_SUBSURFACE_NAMES + TOPO_DISCORDANCE_NAMES
PURE_SUBSURFACE_INDICES: tuple[int, ...] = tuple(range(len(PURE_SUBSURFACE_NAMES)))
COVER_INDEX_COL: int = ALL_STATIC_NAMES.index("mvsd_cover_index")


def _norm_p99(vec: np.ndarray) -> np.ndarray:
    v = np.maximum(np.asarray(vec, dtype=np.float32), 0.0)
    p99 = float(np.percentile(v[::8], 99.2)) if v.size >= 16 else float(v.max(initial=0.0))
    return np.clip(v / (p99 + 1e-5), 0.0, 1.0).astype(np.float32)


def compute_cvdc_crest_fp(X_static: np.ndarray) -> np.ndarray:
    """Catalogue-blind CVDC + OSDR + MVSD crest sharpness score in [0, 1] on footprint."""
    idx = {n: i for i, n in enumerate(ALL_STATIC_NAMES)}
    c_pers = _norm_p99(X_static[:, idx["cvdc_multiscale_persist"]])
    c_jump = _norm_p99(X_static[:, idx["cvdc_transverse_slope_jump"]])
    o_grav = _norm_p99(X_static[:, idx["osdr_grav_step_w5"]])
    o_rtp = _norm_p99(X_static[:, idx["osdr_rtp_step_w5"]])
    m_l17 = _norm_p99(X_static[:, idx["mvsd_strike_persist_l17"]])
    m_brg = _norm_p99(X_static[:, idx["mvsd_valley_bridge_product"]])
    raw = 0.24 * c_pers + 0.16 * c_jump + 0.22 * o_grav + 0.14 * o_rtp + 0.14 * m_l17 + 0.10 * m_brg
    return np.clip(raw, 0.0, 1.0).astype(np.float32)


def compute_osdr_sub_backbone_fp(X_static: np.ndarray) -> np.ndarray:
    """Strictly B12/B19-free Pure-Subsurface OSDR backbone score in [0, 1] on footprint."""
    idx = {n: i for i, n in enumerate(ALL_STATIC_NAMES)}
    o_grav = _norm_p99(X_static[:, idx["osdr_grav_step_w5"]])
    o_rtp = _norm_p99(X_static[:, idx["osdr_rtp_step_w5"]])
    o_lock = _norm_p99(X_static[:, idx["osdr_grav_rtp_sign_lock"]])
    o_hw = _norm_p99(X_static[:, idx["osdr_b15_hangingwall_align"]])
    o_cnd = _norm_p99(X_static[:, idx["osdr_cond_b15_resid_step"]])
    o_trn = _norm_p99(X_static[:, idx["osdr_transtension_conduit"]])
    raw = 0.28 * o_grav + 0.20 * o_rtp + 0.18 * o_lock + 0.14 * o_hw + 0.12 * o_cnd + 0.08 * o_trn
    return np.clip(raw, 0.0, 1.0).astype(np.float32)


def _erode_valid(valid: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0:
        return np.asarray(valid, dtype=bool)
    r = int(radius_px)
    yy, xx = np.ogrid[-r : r + 1, -r : r + 1]
    disk = (yy * yy + xx * xx) <= r * r
    return ndi.binary_erosion(valid, structure=disk, border_value=0)


def _masked_grad_unit(field: np.ndarray, valid: np.ndarray, sigma_px: float, erode_px: int):
    """Return (grad_mag, uy, ux, eroded_support) using valid-only normalised blur."""
    sm = _masked_blur(field, valid, sigma_px)
    gy, gx = np.gradient(sm)
    del sm
    mag = np.hypot(gy, gx)
    sup = _erode_valid(valid, erode_px)
    has_dir = sup & (mag > 1e-9)
    uy = np.divide(gy, mag, out=np.zeros_like(mag), where=has_dir)
    ux = np.divide(gx, mag, out=np.zeros_like(mag), where=has_dir)
    mag_safe = np.where(sup, mag, 0.0).astype(np.float32)
    return mag_safe, uy.astype(np.float32), ux.astype(np.float32), has_dir


def _odd_step_crested(
    sm_field: np.ndarray,
    grad_mag: np.ndarray,
    uy: np.ndarray,
    ux: np.ndarray,
    has_dir: np.ndarray,
    width_px: float,
    erode_px: int,
    valid: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Odd-symmetric cross-strike step gated by central gradient cresting.

    Returns (crested_abs_step, signed_step) as float32 arrays, 0 outside eroded support.
    """
    sup = _erode_valid(valid, erode_px) & has_dir
    f_plus = _sample_offset(sm_field, uy, ux, width_px)
    f_minus = _sample_offset(sm_field, uy, ux, -width_px)
    g_plus = _sample_offset(grad_mag, uy, ux, width_px)
    g_minus = _sample_offset(grad_mag, uy, ux, -width_px)
    signed = np.where(sup, f_plus - f_minus, 0.0)
    flank_g = 0.5 * (np.abs(g_plus) + np.abs(g_minus))
    crest_ratio = np.clip(grad_mag / (flank_g + 1e-5), 0.0, 4.0) / 4.0
    crested = np.where(sup, np.abs(signed) * crest_ratio, 0.0)
    return crested.astype(np.float32), signed.astype(np.float32)


def _robust_z_tanh(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Bounded odd sign-preserving standardized score in [-1, 1] over mask."""
    out = np.zeros_like(values, dtype=np.float32)
    if not mask.any():
        return out
    v = np.asarray(values, dtype=np.float64)[mask]
    scale = float(np.percentile(np.abs(v), 75))
    if scale <= 1e-9:
        scale = float(np.std(v))
    if scale <= 1e-9:
        return out
    out[mask] = np.tanh(v / (1.5 * scale)).astype(np.float32)
    return out


def _tangent_discordance(
    elev: np.ndarray,
    v_elev: np.ndarray,
    pot: np.ndarray,
    v_pot: np.ndarray,
    sigma_px: float,
    fp: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rule-of-V contour–potential-field tangent discordance in [0, 1].

    Because tangent vectors are 90-degree rotations of normal vectors in 2-D,
    sin^2(angle(t_elev, t_pot)) == sin^2(angle(n_elev, n_pot)) == 1 - (n_e . n_p)^2.
    Weighted by sqrt(rank01(|grad elev|) * rank01(|grad pot|)) on eroded support.
    Returns (weighted_discordance, raw_sin2, joint_support).
    """
    erode_px = int(np.ceil(2.5 * sigma_px)) + 1
    ge, uey, uex, he = _masked_grad_unit(elev, v_elev, sigma_px, erode_px)
    gp, upy, upx, hp = _masked_grad_unit(pot, v_pot, sigma_px, erode_px)
    sup = fp & he & hp
    dot = np.clip(uey.astype(np.float64) * upy.astype(np.float64) + uex.astype(np.float64) * upx.astype(np.float64), -1.0, 1.0)
    sin2 = np.where(sup, np.clip(1.0 - dot * dot, 0.0, 1.0), 0.0).astype(np.float32)
    re = _rank01(ge, sup)
    rp = _rank01(gp, sup)
    weight = np.sqrt(np.clip(re.astype(np.float64) * rp.astype(np.float64), 0.0, 1.0)).astype(np.float32)
    return (sin2 * weight).astype(np.float32), sin2, sup


def _line_kernel(length_px: int, theta_rad: float) -> np.ndarray:
    half = length_px // 2
    k = np.zeros((length_px, length_px), dtype=np.float32)
    cy = cx = float(half)
    dy = float(np.sin(theta_rad))
    dx = float(np.cos(theta_rad))
    samples = np.linspace(-half, half, num=2 * length_px + 1)
    for t in samples:
        ry = int(round(cy + t * dy))
        rx = int(round(cx + t * dx))
        if 0 <= ry < length_px and 0 <= rx < length_px:
            k[ry, rx] += 1.0
    s = float(k.sum())
    return k / max(s, 1.0)


def _directional_line_persistence(field: np.ndarray, valid: np.ndarray, length_px: int) -> np.ndarray:
    """Max over 8 strike azimuths of masked line average minus isotropic box average."""
    x = np.where(valid, np.asarray(field, dtype=np.float32), 0.0)
    w = valid.astype(np.float32)
    sup = _erode_valid(valid, length_px // 2 + 1)

    box_num = ndi.uniform_filter(x, size=length_px, mode="constant", cval=0.0)
    box_den = ndi.uniform_filter(w, size=length_px, mode="constant", cval=0.0)
    iso = np.divide(box_num, box_den, out=np.zeros_like(box_num), where=box_den > 1e-6)

    best = np.zeros_like(x, dtype=np.float32)
    for k_idx in range(8):
        theta = k_idx * (np.pi / 8.0)
        kern = _line_kernel(length_px, theta)
        l_num = ndi.convolve(x, kern, mode="constant", cval=0.0)
        l_den = ndi.convolve(w, kern, mode="constant", cval=0.0)
        l_avg = np.divide(l_num, l_den, out=np.zeros_like(l_num), where=l_den > 0.65)
        diff = np.maximum(l_avg - iso, 0.0)
        best = np.maximum(best, diff)
    return np.where(sup, best, 0.0).astype(np.float32)


def _valley_bridge_product(field: np.ndarray, valid: np.ndarray, bridge_px: float = 8.0) -> np.ndarray:
    """Bidirectional strike-bridge geometric mean across alluvial washes (2*bridge_px)."""
    x = np.where(valid, np.maximum(np.asarray(field, dtype=np.float64), 0.0), 0.0)
    sup = _erode_valid(valid, int(np.ceil(bridge_px)) + 1)
    h, w = x.shape
    yy, xx = np.indices((h, w), dtype=np.float64)
    best = np.zeros((h, w), dtype=np.float32)
    for k_idx in range(8):
        theta = k_idx * (np.pi / 8.0)
        dy = float(np.sin(theta))
        dx = float(np.cos(theta))
        f_plus = ndi.map_coordinates(x, [yy + bridge_px * dy, xx + bridge_px * dx], order=1, mode="nearest")
        f_minus = ndi.map_coordinates(x, [yy - bridge_px * dy, xx - bridge_px * dx], order=1, mode="nearest")
        prod = np.sqrt(np.maximum(f_plus, 0.0) * np.maximum(f_minus, 0.0)).astype(np.float32)
        best = np.maximum(best, prod)
    return np.where(sup, best, 0.0).astype(np.float32)


def ensure_raw19_memmap(stack_tif_path: Path, raw_mmap_path: Path) -> np.memmap:
    """Unpack pixel-interleaved LZW 19-band stack once into a fast float32 memmap."""
    raw_mmap_path = Path(raw_mmap_path)
    with rasterio.open(stack_tif_path) as ds:
        shape = (ds.count, ds.height, ds.width)
        expected_bytes = int(np.prod(shape)) * 4
        if raw_mmap_path.is_file() and raw_mmap_path.stat().st_size == expected_bytes:
            return np.memmap(raw_mmap_path, dtype="float32", mode="r", shape=shape)
        raw_mmap_path.parent.mkdir(parents=True, exist_ok=True)
        mm = np.memmap(raw_mmap_path, dtype="float32", mode="w+", shape=shape)
        with rasterio.Env(GDAL_CACHEMAX=134217728):
            step = 128
            for r0 in range(0, ds.height, step):
                h = min(step, ds.height - r0)
                mm[:, r0 : r0 + h, :] = ds.read(window=Window(0, r0, ds.width, h))
        mm.flush()
    return np.memmap(raw_mmap_path, dtype="float32", mode="r", shape=shape)


def compute_cvdc27_features(
    bands_19: np.ndarray,
    footprint: np.ndarray,
    *,
    out_fp_matrix: np.ndarray | None = None,
) -> tuple[np.ndarray, dict[str, np.ndarray], dict]:
    """Compute all 38 S27-CVDC static features over footprint cells.

    Parameters
    ----------
    bands_19 : array-like of shape (19, H, W)
        19-band GEMS numerical stack (0-indexed: B01 is bands_19[0], B19 is bands_19[18]).
    footprint : bool array of shape (H, W)
        Official scored study-area footprint (finite sample_submission cells).
    out_fp_matrix : optional writable array/memmap of shape (N_fp, 38), float32
        Destination buffer so full-grid runs stay strictly memory-bounded.

    Returns
    -------
    fp_matrix : (N_fp, 38) float32 array/memmap
    surfaces : dict with 'control_cvdc_surface' and 'control_gravgrad' ((H, W) float32 in [0, 1])
    receipt : dict of audit statistics & band semantics
    """
    fp = np.asarray(footprint, dtype=bool)
    if bands_19.ndim != 3 or bands_19.shape[0] != 19 or bands_19.shape[1:] != fp.shape:
        raise ValueError(f"Expected (19, {fp.shape[0]}, {fp.shape[1]}), got {bands_19.shape}")

    n_fp = int(fp.sum())
    n_feat = len(ALL_STATIC_NAMES)
    if out_fp_matrix is None:
        X = np.zeros((n_fp, n_feat), dtype=np.float32)
    else:
        if out_fp_matrix.shape != (n_fp, n_feat):
            raise ValueError(f"out_fp_matrix shape {out_fp_matrix.shape} != {(n_fp, n_feat)}")
        X = out_fp_matrix

    col_idx = {name: i for i, name in enumerate(ALL_STATIC_NAMES)}
    invalid_counts: dict[str, int] = {}

    def _write_col(name: str, grid_arr: np.ndarray) -> None:
        vals = np.asarray(grid_arr, dtype=np.float32)[fp]
        if not np.isfinite(vals).all():
            raise ValueError(f"Non-finite values in feature {name}")
        X[:, col_idx[name]] = vals

    # --- 1. Pure-Subsurface Block (Cols 0..25: ZERO dependence on B12 or B19) ---
    for b_1based, fname in SUBSURFACE_BANDS_1BASED:
        raw = np.asarray(bands_19[b_1based - 1], dtype=np.float32)
        vm = valid_mask(raw, fp)
        invalid_counts[f"B{b_1based:02d}"] = int((fp & ~vm).sum())
        _write_col(fname, np.where(vm, raw, 0.0))

    b02 = np.asarray(bands_19[1], dtype=np.float32)
    v02 = valid_mask(b02, fp)
    b13 = np.asarray(bands_19[12], dtype=np.float32)
    v13 = valid_mask(b13, fp)
    b14 = np.asarray(bands_19[13], dtype=np.float32)
    v14 = valid_mask(b14, fp)

    g02, u02y, u02x, h02 = _masked_grad_unit(b02, v02, sigma_px=2.0, erode_px=3)
    g13, u13y, u13x, h13 = _masked_grad_unit(b13, v13, sigma_px=2.0, erode_px=3)
    g14, _, _, _ = _masked_grad_unit(b14, v14, sigma_px=2.0, erode_px=3)
    del b14, v14

    _write_col("sub_grad_rtp_b02", g02)
    _write_col("sub_grad_grav_b13", g13)
    _write_col("sub_grad_tmi_b14", g14)
    del g14

    sm13 = _masked_blur(b13, v13, 2.0).astype(np.float32)
    sm02 = _masked_blur(b02, v02, 2.0).astype(np.float32)

    osdr_g_w5, signed_g_w5 = _odd_step_crested(sm13, g13, u13y, u13x, h13, width_px=5.0, erode_px=7, valid=v13)
    osdr_r_w5, _ = _odd_step_crested(sm02, g02, u02y, u02x, h02, width_px=5.0, erode_px=7, valid=v02)
    del u02y, u02x, h02, g02
    _write_col("osdr_grav_step_w5", osdr_g_w5)
    _write_col("osdr_rtp_step_w5", osdr_r_w5)

    # Multi-width (2, 5, 10 px) sign-locked step coherence along gravity normal u13
    sup_lock = _erode_valid(v13 & v02, 12) & h13
    lock_acc = np.zeros(fp.shape, dtype=np.float32)
    for w_px in (2.0, 5.0, 10.0):
        dg = _sample_offset(sm13, u13y, u13x, w_px) - _sample_offset(sm13, u13y, u13x, -w_px)
        dr = _sample_offset(sm02, u13y, u13x, w_px) - _sample_offset(sm02, u13y, u13x, -w_px)
        zg = _robust_z_tanh(dg, sup_lock)
        zr = _robust_z_tanh(dr, sup_lock)
        lock_acc += zg * zr
    sign_lock = np.where(sup_lock, np.abs(lock_acc / 3.0), 0.0).astype(np.float32)
    _write_col("osdr_grav_rtp_sign_lock", sign_lock)
    del sm13, sm02, signed_g_w5, lock_acc, sign_lock, sup_lock

    # B15 hanging-wall deepening alignment (-grad(B15) . u_grav)
    b15 = np.asarray(bands_19[14], dtype=np.float32)
    v15 = valid_mask(b15, fp)
    sm15 = _masked_blur(b15, v15, 2.5)
    g15y, g15x = np.gradient(sm15)
    del sm15
    sup_15 = _erode_valid(v13 & v15, 5) & h13
    hw_align = np.where(
        sup_15,
        -(g15y.astype(np.float64) * u13y.astype(np.float64) + g15x.astype(np.float64) * u13x.astype(np.float64)),
        0.0,
    ).astype(np.float32)
    _write_col("osdr_b15_hangingwall_align", hw_align)
    del g15y, g15x, hw_align, sup_15

    # Unsupervised B15-deconfounded B17 surface conductivity odd step
    b17 = np.asarray(bands_19[16], dtype=np.float32)
    v17 = valid_mask(b17, fp)
    v15_17 = v15 & v17
    resid17 = np.zeros(fp.shape, dtype=np.float32)
    if int(v15_17.sum()) >= 16:
        u_cov = np.log1p(np.maximum(b15[v15_17].astype(np.float64), 0.0))
        y_cond = np.log1p(np.maximum(b17[v15_17].astype(np.float64), 0.0))
        A = np.column_stack([np.ones_like(u_cov), u_cov, u_cov * u_cov])
        coef, *_ = np.linalg.lstsq(A, y_cond, rcond=None)
        resid17[v15_17] = (y_cond - A @ coef).astype(np.float32)
    sm_r17 = _masked_blur(resid17, v15_17, 1.5)
    sup_r17 = _erode_valid(v15_17 & v13, 6) & h13
    r17_step = np.where(
        sup_r17,
        np.abs(_sample_offset(sm_r17, u13y, u13x, 4.0) - _sample_offset(sm_r17, u13y, u13x, -4.0)),
        0.0,
    ).astype(np.float32)
    _write_col("osdr_cond_b15_resid_step", r17_step)
    del b17, v17, v15_17, resid17, sm_r17, sup_r17, r17_step

    # Geodetic transtension * unweighted microseismicity conduit index
    b04 = np.asarray(bands_19[3], dtype=np.float32)
    b07 = np.asarray(bands_19[6], dtype=np.float32)
    b08 = np.asarray(bands_19[7], dtype=np.float32)
    b16 = np.asarray(bands_19[15], dtype=np.float32)
    v_tt = valid_mask(b04, fp) & valid_mask(b07, fp) & valid_mask(b08, fp) & valid_mask(b16, fp)
    tt_val = np.where(
        v_tt,
        (np.maximum(b07, 0.0) * np.maximum(b08, 0.0) / np.maximum(b04, 1e-4))
        * np.log1p(np.maximum(b16, 0.0)),
        0.0,
    ).astype(np.float32)
    _write_col("osdr_transtension_conduit", tt_val)
    del b04, b07, b08, b16, v_tt, tt_val

    # --- 2. Topographic & Cross-Modal Discordance Block (Cols 26..37) ---
    b12 = np.asarray(bands_19[11], dtype=np.float32)
    v12 = valid_mask(b12, fp)
    b19 = np.asarray(bands_19[18], dtype=np.float32)
    v19 = valid_mask(b19, fp)
    invalid_counts["B12"] = int((fp & ~v12).sum())
    invalid_counts["B19"] = int((fp & ~v19).sum())

    _write_col("raw_B12_det_elev", np.where(v12, b12, 0.0))
    _write_col("raw_B19_det_slope", np.where(v19, b19, 0.0))
    g12, _, _, _ = _masked_grad_unit(b12, v12, sigma_px=2.0, erode_px=3)
    _write_col("topo_grad_elev_b12", g12)
    del g12

    cvdc_eg_1p5, _, _ = _tangent_discordance(b12, v12, b13, v13, sigma_px=1.5, fp=fp)
    cvdc_eg_3p5, sin2_3p5, sup_3p5 = _tangent_discordance(b12, v12, b13, v13, sigma_px=3.5, fp=fp)
    cvdc_er_3p5, _, _ = _tangent_discordance(b12, v12, b02, v02, sigma_px=3.5, fp=fp)
    cvdc_eg_7p0, _, _ = _tangent_discordance(b12, v12, b13, v13, sigma_px=7.0, fp=fp)
    del b02, v02, b12, v12

    cvdc_persist = np.sqrt(np.maximum(cvdc_eg_1p5, 0.0) * np.maximum(cvdc_eg_7p0, 0.0)).astype(np.float32)
    _write_col("cvdc_sin2_elev_grav_s1p5", cvdc_eg_1p5)
    _write_col("cvdc_sin2_elev_grav_s3p5", cvdc_eg_3p5)
    _write_col("cvdc_sin2_elev_rtp_s3p5", cvdc_er_3p5)
    _write_col("cvdc_multiscale_persist", cvdc_persist)
    del cvdc_eg_1p5, cvdc_eg_3p5, cvdc_er_3p5, cvdc_eg_7p0

    sm19 = _masked_blur(b19, v19, 1.0)
    sup_tsj = _erode_valid(v19 & v13, 6) & sup_3p5 & h13
    tsj = np.where(
        sup_tsj,
        np.abs(_sample_offset(sm19, u13y, u13x, 3.0) - _sample_offset(sm19, u13y, u13x, -3.0)) * sin2_3p5,
        0.0,
    ).astype(np.float32)
    _write_col("cvdc_transverse_slope_jump", tsj)
    del sin2_3p5, sup_3p5, sup_tsj, tsj, u13y, u13x, h13

    # MVSD multi-valley scarp inflection persistence & valley-gap bridge
    i_y, i_x = np.gradient(sm19)
    del sm19
    v_inf = _erode_valid(v19, 2)
    scarp_inf = np.where(v_inf, np.hypot(i_y, i_x), 0.0).astype(np.float32)
    del i_y, i_x

    mvsd_l9 = _directional_line_persistence(scarp_inf, v_inf, length_px=9)
    mvsd_l17 = _directional_line_persistence(scarp_inf, v_inf, length_px=17)
    mvsd_bridge = _valley_bridge_product(scarp_inf, v_inf, bridge_px=8.0)
    del scarp_inf, v_inf

    _write_col("mvsd_strike_persist_l9", mvsd_l9)
    _write_col("mvsd_strike_persist_l17", mvsd_l17)
    _write_col("mvsd_valley_bridge_product", mvsd_bridge)
    del mvsd_l9, mvsd_l17, mvsd_bridge

    # Continuous basin-cover index in [0, 1] (high B15 conductive-base depth + low B19 slope)
    v_cov = v15 & v19
    cov_idx = np.where(
        v_cov,
        0.5 * _rank01(b15, v_cov) + 0.5 * (1.0 - _rank01(b19, v_cov)),
        0.0,
    ).astype(np.float32)
    _write_col("mvsd_cover_index", cov_idx)
    del b15, v15, b19, v19, v_cov, cov_idx

    # Unsupervised standalone controls in [0, 1]
    sup_ctrl = fp & (cvdc_persist > 0) & ((osdr_g_w5 + osdr_r_w5) > 0)
    r_cvdc = _rank01(cvdc_persist, sup_ctrl)
    r_osdr = _rank01(osdr_g_w5 + osdr_r_w5, sup_ctrl)
    control_cvdc_surface = np.where(
        sup_ctrl,
        np.sqrt(np.clip(r_cvdc.astype(np.float64) * r_osdr.astype(np.float64), 0.0, 1.0)),
        0.0,
    ).astype(np.float32)
    control_gravgrad = _rank01(g13, _erode_valid(v13, 3))

    if hasattr(X, "flush"):
        X.flush()

    receipt = {
        "schema": "s27-cvdc-features-v1",
        "catalogue_features_used": False,
        "footprint_pixels": n_fp,
        "total_static_features": n_feat,
        "pure_subsurface_feature_count": len(PURE_SUBSURFACE_NAMES),
        "topo_discordance_feature_count": len(TOPO_DISCORDANCE_NAMES),
        "pure_subsurface_names": list(PURE_SUBSURFACE_NAMES),
        "topo_discordance_names": list(TOPO_DISCORDANCE_NAMES),
        "band_06_semantics": "airborne gamma-ray radiometric Total Count exposure (IR-91-S12-04; NOT magnetic tilt)",
        "band_15_semantics": "DrivenData depth to conductive base (NOT drill-confirmed crystalline basement)",
        "nodata_policy": f"exclude non-finite and |value| >= {EXTREME_CUTOFF:.0e} via masked normalised convolution + morphological support erosion",
        "invalid_pixels_inside_footprint": invalid_counts,
        "control_cvdc_support_pixels": int(sup_ctrl.sum()),
    }
    return X, {"control_cvdc_surface": control_cvdc_surface, "control_gravgrad": control_gravgrad}, receipt
