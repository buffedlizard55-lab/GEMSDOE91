"""S25-FABRIC features: oriented granulometry contrast + cross-spectral lag.

Single-method lane preregistered in docs/s25/preregistration.md. Catalogue
independent: no fault coordinates enter any feature. Declared-NoData sentinels
(|value| >= 1e30 or non-finite) are excluded from every statistic via masked
normalised convolution (shared with gems91.cckm24); features are NaN outside
supports eroded beyond each feature's maximum influence radius, so no filled
value can influence a retained feature.

Named non-fault mimics: unfaulted dipping lithologic contacts, remanent
magnetization offsets, alluvial-fan lobe / shoreline fabrics, GeoDAWN
flight-line seams. Nothing here measures geothermal heat or permeability.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from gems91 import cckm24

# Frozen constants (docs/s25/preregistration.md)
GRAD_SIGMA = 2.0
GRAD_ERODE_PX = 3
ELEV_SMOOTH_SIGMA = 1.5
OGC_LENGTHS = (5, 11)
OGC_ORIENTATIONS_DEG = (0, 45, 90, 135)
OGC_ENERGY_WINDOW = 15
OGC_OFFSET_PX = 7.0
OGC_ERODE_PX = 20
CSPL_BG_SIGMA = 6.0
CSPL_TILE = 64
CSPL_STRIDE = 32
CSPL_MAX_LAG = 8
CSPL_MIN_VALID_FRAC = 0.8
CSPL_SMOOTH_SIGMA = 8.0
CSPL_OFFSET_PX = 7.0
CSPL_ERODE_PX = 10
EPS = 1e-12

BASE_GRAD_BANDS = (2, 12, 13, 14)


def _eroded(valid: np.ndarray, px: float) -> np.ndarray:
    """Pixels whose Euclidean distance to the nearest invalid cell exceeds px."""
    return ndi.distance_transform_edt(np.asarray(valid, dtype=bool)) > float(px)


def _as_feature(values: np.ndarray, support: np.ndarray) -> np.ndarray:
    out = np.where(support, np.asarray(values, dtype=np.float64), np.nan).astype(np.float32)
    return out


def _line_footprint(length: int, angle_deg: int) -> np.ndarray:
    """Odd-sized binary line structuring element of the given length/angle."""
    if length % 2 == 0 or length < 3:
        raise ValueError("length must be odd and >= 3")
    fp = np.zeros((length, length), dtype=bool)
    c = length // 2
    if angle_deg == 0:
        fp[c, :] = True
    elif angle_deg == 90:
        fp[:, c] = True
    elif angle_deg == 45:
        np.fill_diagonal(fp, True)
    elif angle_deg == 135:
        for k in range(length):
            fp[k, length - 1 - k] = True
    else:
        raise ValueError(f"unsupported orientation {angle_deg}")
    return fp


def _oriented_tophat_energies(field_filled: np.ndarray, lengths, orientations):
    """Local 15-px mean |field - opening(field)| per (length, orientation)."""
    f = np.asarray(field_filled, dtype=np.float32)
    energies = {}
    for length in lengths:
        for ang in orientations:
            opened = ndi.grey_opening(f, footprint=_line_footprint(length, ang), mode="nearest")
            resid = np.clip(f - opened, 0.0, None)
            del opened
            energies[(length, ang)] = ndi.uniform_filter(
                resid, size=OGC_ENERGY_WINDOW, mode="nearest")
            del resid
    return energies


def _unit_normal(smooth_field: np.ndarray, valid: np.ndarray):
    gy, gx = np.gradient(np.asarray(smooth_field, dtype=np.float64))
    mag = np.hypot(gy, gx)
    has = valid & (mag > 0)
    uy = np.divide(gy, mag, out=np.zeros_like(mag), where=has)
    ux = np.divide(gx, mag, out=np.zeros_like(mag), where=has)
    return uy, ux, mag, has


def _contrast(field: np.ndarray, uy, ux, offset: float) -> np.ndarray:
    plus = cckm24._sample_offset(np.asarray(field, dtype=np.float64), uy, ux, offset)
    minus = cckm24._sample_offset(np.asarray(field, dtype=np.float64), uy, ux, -offset)
    return np.abs(plus - minus)


def ogc_features(elev_raw, slope_raw, footprint):
    """Oriented granulometry contrast features from B12 (+ B19 energies)."""
    fp = np.asarray(footprint, dtype=bool)
    v_e = cckm24.valid_mask(elev_raw, fp)
    v_s = cckm24.valid_mask(slope_raw, fp)
    support = _eroded(v_e & v_s, OGC_ERODE_PX)

    elev = cckm24._masked_blur(elev_raw, v_e, ELEV_SMOOTH_SIGMA)
    slope_f = cckm24._masked_blur(slope_raw, v_s, ELEV_SMOOTH_SIGMA)
    energies = _oriented_tophat_energies(elev, OGC_LENGTHS, OGC_ORIENTATIONS_DEG)
    slope_energies = _oriented_tophat_energies(slope_f, (11,), OGC_ORIENTATIONS_DEG)
    del slope_f

    feats = {}
    emax = {}
    for length in OGC_LENGTHS:
        stack = np.stack([energies[(length, a)] for a in OGC_ORIENTATIONS_DEG])
        mx = stack.max(axis=0)
        mn = stack.min(axis=0)
        del stack
        emax[length] = mx
        feats[f"ogc_emax_l{length}"] = _as_feature(np.log1p(np.clip(mx, 0, None)), support)
        aniso = np.divide(mx - mn, mx + mn + EPS, out=np.zeros_like(mx), where=(mx + mn) > 0)
        feats[f"ogc_aniso_l{length}"] = _as_feature(aniso, support)
        if length == 11:
            aniso11 = aniso
        del mn, aniso
    feats["ogc_scale_ratio"] = _as_feature(
        np.clip(np.divide(emax[11], emax[5] + EPS, out=np.zeros_like(emax[11]),
                          where=emax[5] > 0), 0.0, 5.0), support)
    slope_max = np.stack([slope_energies[(11, a)] for a in OGC_ORIENTATIONS_DEG]).max(axis=0)
    feats["ogc_slope_emax_l11"] = _as_feature(np.log1p(np.clip(slope_max, 0, None)), support)
    del slope_max, energies, slope_energies

    # Across-break contrasts along the gradient normal of the slope magnitude.
    gy, gx = np.gradient(elev)
    slope_mag = np.hypot(gy, gx)
    del gy, gx, elev
    slope_smooth = cckm24._masked_blur(slope_mag, v_e, 3.0)
    del slope_mag
    uy, ux, _mag, _has = _unit_normal(slope_smooth, v_e)
    del slope_smooth
    feats["ogc_contrast_energy"] = _as_feature(
        np.log1p(np.clip(_contrast(emax[11], uy, ux, OGC_OFFSET_PX), 0, None)), support)
    feats["ogc_contrast_aniso"] = _as_feature(
        _contrast(aniso11, uy, ux, OGC_OFFSET_PX), support)
    return feats, support


def _phase_correlation_lag(a: np.ndarray, b: np.ndarray, max_lag: int):
    """Integer lag of b relative to a (phase correlation) + coherence."""
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    fa = np.fft.fft2(a * win)
    fb = np.fft.fft2(b * win)
    cross = fa * np.conj(fb)
    denom = np.abs(cross)
    r = np.fft.ifft2(np.divide(cross, denom, out=np.zeros_like(cross),
                                where=denom > 0)).real
    n0, n1 = r.shape
    # Allowed wrapped lags: 0..max_lag and n-max_lag..n-1 in each axis.
    allowed = np.zeros_like(r, dtype=bool)
    allowed[: max_lag + 1, : max_lag + 1] = True
    allowed[: max_lag + 1, n1 - max_lag:] = True
    allowed[n0 - max_lag:, : max_lag + 1] = True
    allowed[n0 - max_lag:, n1 - max_lag:] = True
    masked = np.where(allowed, r, -np.inf)
    py, px = np.unravel_index(int(np.argmax(masked)), r.shape)
    peak = float(r[py, px])
    dy = py if py <= max_lag else py - n0
    dx = px if px <= max_lag else px - n1
    coherence = peak / (float(np.median(np.abs(r))) + EPS)
    # Sign verified synthetically (tests/test_fabric25.py): the raw peak sits
    # at -(shift of b relative to a), so negate to match the docstring.
    return float(-dy), float(-dx), float(np.clip(coherence, 0.0, 50.0))


def cspl_features(grav_raw, tmi_raw, footprint):
    """Cross-spectral phase-lag features between B13 (gravity) and B14 (TMI)."""
    fp = np.asarray(footprint, dtype=bool)
    v_g = cckm24.valid_mask(grav_raw, fp)
    v_t = cckm24.valid_mask(tmi_raw, fp)
    joint = v_g & v_t
    h, w = fp.shape

    def residual(raw, valid):
        bg = cckm24._masked_blur(raw, valid, CSPL_BG_SIGMA)
        vals = np.where(valid, np.asarray(raw, dtype=np.float64), 0.0)
        return np.where(valid, vals - bg, 0.0)

    res_g = residual(grav_raw, v_g).astype(np.float32)
    res_t = residual(tmi_raw, v_t).astype(np.float32)

    pad = CSPL_TILE
    pg = np.pad(res_g, pad, mode="reflect")
    pt = np.pad(res_t, pad, mode="reflect")
    del res_g, res_t
    # Integral image of the joint-valid mask for per-tile valid fractions.
    pv = np.pad(joint.astype(np.float64), pad, mode="edge")
    integral = np.zeros((pv.shape[0] + 1, pv.shape[1] + 1), dtype=np.float64)
    integral[1:, 1:] = pv.cumsum(axis=0).cumsum(axis=1)
    del pv

    acc = {k: np.zeros((h, w), dtype=np.float64) for k in ("dy", "dx", "coh", "w", "n")}
    tile_area = float(CSPL_TILE * CSPL_TILE)
    n_tiles = n_used = 0
    for y0 in range(0, h, CSPL_STRIDE):
        for x0 in range(0, w, CSPL_STRIDE):
            n_tiles += 1
            py0, px0 = y0 + pad - CSPL_TILE // 2, x0 + pad - CSPL_TILE // 2
            valid_count = (integral[py0 + CSPL_TILE, px0 + CSPL_TILE]
                           - integral[py0, px0 + CSPL_TILE]
                           - integral[py0 + CSPL_TILE, px0]
                           + integral[py0, px0])
            if valid_count / tile_area < CSPL_MIN_VALID_FRAC:
                continue
            ta = pg[py0: py0 + CSPL_TILE, px0: px0 + CSPL_TILE]
            tb = pt[py0: py0 + CSPL_TILE, px0: px0 + CSPL_TILE]
            if float(ta.std()) <= 0 or float(tb.std()) <= 0:
                continue
            dy, dx, coh = _phase_correlation_lag(tb, ta, CSPL_MAX_LAG)
            n_used += 1
            ys, ye = max(y0 - CSPL_TILE // 2, 0), min(y0 + CSPL_TILE // 2, h)
            xs, xe = max(x0 - CSPL_TILE // 2, 0), min(x0 + CSPL_TILE // 2, w)
            acc["dy"][ys:ye, xs:xe] += dy * coh
            acc["dx"][ys:ye, xs:xe] += dx * coh
            acc["coh"][ys:ye, xs:xe] += coh
            acc["w"][ys:ye, xs:xe] += coh
            acc["n"][ys:ye, xs:xe] += 1.0
    del pg, pt, integral

    covered = acc["w"] > 0
    support = _eroded(joint & covered, CSPL_ERODE_PX)

    def smoo(field):
        return cckm24._masked_blur(field, covered & joint, CSPL_SMOOTH_SIGMA)

    lag_dy = smoo(np.divide(acc["dy"], acc["w"], out=np.zeros((h, w)), where=covered))
    lag_dx = smoo(np.divide(acc["dx"], acc["w"], out=np.zeros((h, w)), where=covered))
    coh_mean = smoo(np.divide(acc["coh"], np.maximum(acc["w"] / np.maximum(acc["coh"], EPS), 1.0),
                              out=np.zeros((h, w)), where=covered))
    # coh_mean above divides accumulated coh by accumulated count (w/coh per tile is 1 per
    # contributing tile only when coh>0); recompute cleanly as smoothed accumulated mean:
    coh_mean = smoo(np.divide(acc["coh"], np.maximum(acc["w"], EPS) /
                              np.maximum(np.divide(acc["coh"], np.maximum(acc["w"], EPS),
                                                   out=np.ones((h, w)), where=covered), EPS),
                              out=np.zeros((h, w)), where=covered))
    del acc
    lag_mag = np.hypot(lag_dy, lag_dx)
    coh_log = np.log1p(np.clip(coh_mean, 0.0, None))
    prod = lag_mag * coh_log

    g_smooth = cckm24._masked_blur(grav_raw, v_g, 3.0)
    uy, ux, _m, _has = _unit_normal(g_smooth, v_g)
    del g_smooth
    contrast = _contrast(prod, uy, ux, CSPL_OFFSET_PX)

    feats = {
        "cspl_lag_dy": _as_feature(lag_dy, support),
        "cspl_lag_dx": _as_feature(lag_dx, support),
        "cspl_lag_mag": _as_feature(lag_mag, support),
        "cspl_coherence_log": _as_feature(coh_log, support),
        "cspl_lag_x_coh": _as_feature(prod, support),
        "cspl_contrast_prod": _as_feature(contrast, support),
    }
    meta = {"tiles_total": int(n_tiles), "tiles_used": int(n_used)}
    return feats, support, meta


def build_all(read_band, footprint, save):
    """Build every S25 feature/surface, calling save(name, float32 2D) per array.

    read_band(i) -> raw 2D band i (1-based). Returns (groups, meta) where
    groups = {"base": [...names], "new": [...names], "surfaces": [...names]}.
    Feature arrays carry NaN outside support; surfaces are finite in [0,1].
    """
    fp = np.asarray(footprint, dtype=bool)
    base, new, surfaces = [], [], []
    meta = {"constants": {
        "grad_sigma": GRAD_SIGMA, "grad_erode_px": GRAD_ERODE_PX,
        "ogc_lengths": list(OGC_LENGTHS), "ogc_orientations_deg": list(OGC_ORIENTATIONS_DEG),
        "ogc_energy_window": OGC_ENERGY_WINDOW, "ogc_offset_px": OGC_OFFSET_PX,
        "ogc_erode_px": OGC_ERODE_PX, "cspl_bg_sigma": CSPL_BG_SIGMA,
        "cspl_tile": CSPL_TILE, "cspl_stride": CSPL_STRIDE, "cspl_max_lag": CSPL_MAX_LAG,
        "cspl_min_valid_frac": CSPL_MIN_VALID_FRAC, "cspl_smooth_sigma": CSPL_SMOOTH_SIGMA,
        "cspl_offset_px": CSPL_OFFSET_PX, "cspl_erode_px": CSPL_ERODE_PX},
        "band_valid_pixels": {}}

    # No band cache: each band is read at most twice and a 19-band float32
    # cache would cost ~0.9 GB of the sandbox's RAM.
    def band(i):
        return read_band(i)

    # Base: raw bands.
    for i in range(1, 20):
        a = band(i)
        v = cckm24.valid_mask(a, fp)
        meta["band_valid_pixels"][f"B{i:02d}"] = int(v.sum())
        name = f"band{i:02d}"
        save(name, _as_feature(np.asarray(a, dtype=np.float64), v))
        base.append(name)
    # Base: gradient magnitudes.
    grad13 = None
    for i in BASE_GRAD_BANDS:
        a = band(i)
        v = cckm24.valid_mask(a, fp)
        smoo = cckm24._masked_blur(a, v, GRAD_SIGMA)
        gy, gx = np.gradient(smoo)
        del smoo
        mag = np.hypot(gy, gx)
        del gy, gx
        name = f"gradmag{i:02d}"
        save(name, _as_feature(mag, _eroded(v, GRAD_ERODE_PX)))
        base.append(name)
        if i == 13:
            grad13 = (mag, _eroded(v, GRAD_ERODE_PX))
        else:
            del mag

    # New families.
    ogc, ogc_support = ogc_features(band(12), band(19), fp)
    for name, arr in ogc.items():
        save(name, arr)
        new.append(name)
    cspl, cspl_support, cspl_meta = cspl_features(band(13), band(14), fp)
    for name, arr in cspl.items():
        save(name, arr)
        new.append(name)
    meta["cspl"] = cspl_meta
    meta["ogc_support_pixels"] = int(ogc_support.sum())
    meta["cspl_support_pixels"] = int(cspl_support.sum())
    meta["footprint_pixels"] = int(fp.sum())

    # Standalone surfaces (finite [0,1]).
    joint = np.isfinite(ogc["ogc_contrast_energy"]) & np.isfinite(cspl["cspl_lag_x_coh"]) & fp
    r1 = cckm24._rank01(np.nan_to_num(ogc["ogc_contrast_energy"]), joint)
    r2 = cckm24._rank01(np.nan_to_num(cspl["cspl_lag_x_coh"]), joint)
    new_surface = np.where(joint, np.sqrt(np.clip(
        r1.astype(np.float64) * r2.astype(np.float64), 0.0, 1.0)), 0.0).astype(np.float32)
    del r1, r2
    save("surface_new_standalone", new_surface)
    surfaces.append("surface_new_standalone")
    mag, sup = grad13
    gg = cckm24._rank01(mag, sup & fp)
    del mag
    save("surface_gravgrad", gg)
    surfaces.append("surface_gravgrad")
    for s in (new_surface, gg):
        if not np.isfinite(s).all() or float(s.min()) < 0.0 or float(s.max()) > 1.0:
            raise ValueError("standalone surface not finite in [0,1]")
    groups = {"base": base, "new": new, "surfaces": surfaces}
    meta["groups"] = groups
    meta["nodata_policy"] = ("exclude non-finite or |value| >= 1e30 cells via masked "
                             "normalised convolution; supports eroded beyond each feature's "
                             "influence radius; features NaN outside support")
    return groups, meta
