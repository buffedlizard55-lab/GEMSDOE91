"""S17-EULR: Euler deconvolution source-geometry features (preregistered).

Lane frozen in ``docs/HYPOTHESES_S17.md`` before any fit. Windowed Euler
deconvolution (Thompson 1982; Reid et al. 1990, *Geophysics* 55, 80-91,
DOI 10.1190/1.1442774) on the pinned sponsor stack only:

- magnetic: F = B14 ``tmi``, Fx/Fy Gaussian derivatives (sigma 1.2 px),
  Fz = B09 ``tmi_vg`` * 100 (verified dz(B14) in nT/m, r=+0.98919 on an
  interior crop this session; see preregistration S2.2);
- gravity: F = B13 ``iso_grav_anom``, Fx/Fy Gaussian derivatives (sigma
  1.5 px), Fz = FFT |k| vertical derivative of B13 (B11/B18 are measured
  horizontal components, not a vertical derivative; preregistration S2.2).

Euler homogeneity in depth coordinates (zeta down +, observation zeta=0,
source depth d>0), window-centred offsets (u=col-xc, v=row-yc), unknowns
(dx0, dy0, d[, B]):

    Fx*dx0 + Fy*dy0 + Fz*d + N*B = u*Fx + v*Fy + N*F

solved per 11x11 px window for structural indices N in {0, 1} (N=0 drops B).
The fast solver evaluates normal-equation sums by box filtering of
absolute-coordinate fields and transforms to window-centred form; it is
unit-tested against a brute-force per-window solver and against exact
Euler-homogeneous synthetic fields (``tests/test_eulr17.py``).

100% label-free: the catalogue never enters feature construction, so the
identical columns are used in holdout and full-map inference. Scoring,
canaries, registry gates and writing remain in the shared tools
(``scripts/evaluate_holdout.py``, ``scripts/submission_writer.py``).
"""

from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

from gems91.dd_vtc_pu import _clean_band_edt

WINDOW_PX = 11
MAG_SIGMA = 1.2
GRAV_SIGMA = 1.5
INTERIOR_CLEARANCE_PX = 8.0
AMP_GATE_PERCENTILE = 40.0
DEPTH_MIN_PX = 0.5
DEPTH_MAX_PX = 25.0
OFFSET_MAX_PX = 8.0
REL_UNC_MAX = 0.20
SLAB_ROWS = 256

EULR_FEATURE_NAMES: list[str] = [
    "s17_eulr_mag0_dens",
    "s17_eulr_mag0_depth",
    "s17_eulr_mag0_unc",
    "s17_eulr_mag1_dens",
    "s17_eulr_mag1_depth",
    "s17_eulr_mag1_unc",
    "s17_eulr_grav0_dens",
    "s17_eulr_grav0_depth",
    "s17_eulr_grav0_unc",
    "s17_eulr_grav1_dens",
    "s17_eulr_grav1_depth",
    "s17_eulr_grav1_unc",
    "s17_eulr_joint_dens",
    "s17_eulr_mag0_b15_agree",
]
_COMBOS = (("mag", 0), ("mag", 1), ("grav", 0), ("grav", 1))


# --------------------------------------------------------------------------
# Reference (brute-force) solver: tests only, tiny grids.
# --------------------------------------------------------------------------
def euler_window_solve_bruteforce(
    F: np.ndarray,
    Fx: np.ndarray,
    Fy: np.ndarray,
    Fz: np.ndarray,
    *,
    structural_index: float,
    window_px: int = WINDOW_PX,
) -> dict[str, np.ndarray]:
    """Per-window least-squares Euler solution by explicit loops.

    Returns full grids (NaN outside the valid centre region):
    ``dx0, dy0, depth, rel_unc`` where (dx0, dy0) are source offsets in
    (col, row) pixels from the window centre and ``rel_unc`` is
    sqrt(cov_dd)/d with cov = s^2 (A^T A)^-1, s^2 = RSS/(n-p).
    """
    F = np.asarray(F, dtype=np.float64)
    Fx = np.asarray(Fx, dtype=np.float64)
    Fy = np.asarray(Fy, dtype=np.float64)
    Fz = np.asarray(Fz, dtype=np.float64)
    h, w = F.shape
    half = window_px // 2
    N = float(structural_index)
    offs = np.arange(-half, half + 1, dtype=np.float64)
    UU, VV = np.meshgrid(offs, offs)  # UU: col offset u, VV: row offset v
    out = {k: np.full((h, w), np.nan) for k in ("dx0", "dy0", "depth", "rel_unc")}
    p = 3 if N == 0.0 else 4
    for yc in range(half, h - half):
        for xc in range(half, w - half):
            sl = (slice(yc - half, yc + half + 1), slice(xc - half, xc + half + 1))
            ax = Fx[sl].ravel()
            ay = Fy[sl].ravel()
            az = Fz[sl].ravel()
            b = (UU.ravel() * ax + VV.ravel() * ay + N * F[sl].ravel())
            cols = [ax, ay, az] + ([np.full(ax.size, N)] if p == 4 else [])
            A = np.column_stack(cols)
            sol, *_ = np.linalg.lstsq(A, b, rcond=None)
            resid = b - A @ sol
            dof = max(A.shape[0] - p, 1)
            s2 = float(resid @ resid) / dof
            try:
                cov = s2 * np.linalg.inv(A.T @ A)
                rel = float(np.sqrt(max(cov[2, 2], 0.0)) / sol[2]) if sol[2] != 0 else np.inf
            except np.linalg.LinAlgError:
                rel = np.inf
            out["dx0"][yc, xc] = sol[0]
            out["dy0"][yc, xc] = sol[1]
            out["depth"][yc, xc] = sol[2]
            out["rel_unc"][yc, xc] = rel
    return out


# --------------------------------------------------------------------------
# Fast solver: box-filtered normal equations, slab-wise.
# --------------------------------------------------------------------------
def _box_sum(arr64: np.ndarray, window_px: int) -> np.ndarray:
    return ndi.uniform_filter(arr64, size=window_px, mode="nearest") * float(window_px * window_px)


def _solve_candidates(
    S: np.ndarray, Tloc: np.ndarray, Qloc: np.ndarray, npts: int
) -> tuple[np.ndarray, np.ndarray]:
    """Batched solve S u = Tloc; return (u, rel_unc_depth). S:(m,p,p)."""
    m, p = Tloc.shape
    u = np.full((m, p), np.nan)
    rel = np.full(m, np.inf)
    if m == 0:
        return u, rel
    # Ridge for numerical safety, scaled to each system's trace.
    trace = np.einsum("mii->m", S) / p
    S = S.copy()
    idx = np.arange(p)
    S[:, idx, idx] += (1e-10 * np.maximum(trace, 1e-300))[:, None]
    try:
        u = np.linalg.solve(S, Tloc[:, :, None])[:, :, 0]
    except np.linalg.LinAlgError:
        # Fall back per-system via lstsq on the (rare) singular subset.
        for i in range(m):
            try:
                u[i] = np.linalg.solve(S[i], Tloc[i])
            except np.linalg.LinAlgError:
                u[i], *_ = np.linalg.lstsq(S[i], Tloc[i], rcond=None)
    rss = Qloc - np.einsum("mi,mi->m", u, Tloc)
    rss = np.maximum(rss, 0.0)
    s2 = rss / max(npts - p, 1)
    depth_ok = np.isfinite(u[:, 2]) & (u[:, 2] > 0)
    if depth_ok.any():
        try:
            inv = np.linalg.inv(S[depth_ok])
            var_d = np.maximum(inv[:, 2, 2], 0.0) * s2[depth_ok]
            rel[depth_ok] = np.sqrt(var_d) / u[depth_ok, 2]
        except np.linalg.LinAlgError:
            pass
    return u, rel


def euler_solve_fast(
    F: np.ndarray,
    Fx: np.ndarray,
    Fy: np.ndarray,
    Fz: np.ndarray,
    *,
    structural_index: float,
    window_px: int = WINDOW_PX,
    candidate_mask: np.ndarray | None = None,
    slab_rows: int = SLAB_ROWS,
) -> dict[str, np.ndarray]:
    """Fast Euler solutions on ``candidate_mask`` centres (default: all
    centres at least half a window from the array edge).

    Returns float32 grids ``dx0, dy0, depth, rel_unc`` (NaN where not a
    candidate or solve failed). Algebra identical to the brute-force
    reference; see module docstring for the centred-transform derivation.
    """
    F32 = np.asarray(F, dtype=np.float32)
    Fx32 = np.asarray(Fx, dtype=np.float32)
    Fy32 = np.asarray(Fy, dtype=np.float32)
    Fz32 = np.asarray(Fz, dtype=np.float32)
    h, w = F32.shape
    half = window_px // 2
    N = float(structural_index)
    p = 3 if N == 0.0 else 4
    npts = window_px * window_px
    if candidate_mask is None:
        candidate_mask = np.zeros((h, w), dtype=bool)
        candidate_mask[half:h - half, half:w - half] = True
    out = {k: np.full((h, w), np.nan, dtype=np.float32) for k in ("dx0", "dy0", "depth", "rel_unc")}

    for r0 in range(0, h, slab_rows):
        r1 = min(r0 + slab_rows, h)
        cand_slab = candidate_mask[r0:r1]
        if not cand_slab.any():
            continue
        s0, s1 = max(r0 - half, 0), min(r1 + half, h)
        pad_top, pad_bot = r0 - s0, s1 - r1  # rows of context above r0 / below r1

        def slab(a: np.ndarray) -> np.ndarray:
            blk = a[s0:s1].astype(np.float64)
            if pad_top < half or pad_bot < half:
                blk = np.pad(blk, ((half - pad_top, half - pad_bot), (0, 0)), mode="edge")
            return blk

        fx, fy, fz, ff = slab(Fx32), slab(Fy32), slab(Fz32), slab(F32)
        rows_g, cols_g = np.mgrid[s0 - (half - pad_top): s1 + (half - pad_bot), 0:w]
        # Absolute-coordinate field C = X*Fx + Y*Fy (X=col, Y=row).
        C = cols_g * fx + rows_g * fy
        # Box sums over the window, centre rows [half : half+(r1-r0)).
        def S_(prod: np.ndarray) -> np.ndarray:
            return _box_sum(prod, window_px)[half: half + (r1 - r0)]

        s11, s12, s13 = S_(fx * fx), S_(fx * fy), S_(fx * fz)
        s22, s23, s33 = S_(fy * fy), S_(fy * fz), S_(fz * fz)
        sum_fx, sum_fy, sum_fz, sum_f = S_(fx), S_(fy), S_(fz), S_(ff)
        uc1, uc2, uc3 = S_(fx * C), S_(fy * C), S_(fz * C)
        uf1, uf2, uf3 = S_(fx * ff), S_(fy * ff), S_(fz * ff)
        sum_c, sum_cc, sum_cf, sum_ff2 = S_(C), S_(C * C), S_(C * ff), S_(ff * ff)
        del fx, fy, fz, ff, C, rows_g, cols_g

        # Absolute-system RHS sums for b_abs = C + N*F.
        U1, U2, U3 = uc1 + N * uf1, uc2 + N * uf2, uc3 + N * uf3
        Qabs = sum_cc + 2.0 * N * sum_cf + N * N * sum_ff2
        del uc1, uc2, uc3, uf1, uf2, uf3, sum_cc, sum_cf, sum_ff2

        cy_idx, cx_idx = np.nonzero(cand_slab)
        if cy_idx.size == 0:
            continue
        xc = cx_idx.astype(np.float64)
        yc = (cy_idx + r0).astype(np.float64)

        def g(a: np.ndarray) -> np.ndarray:
            return a[cy_idx, cx_idx]

        S = np.empty((cy_idx.size, p, p), dtype=np.float64)
        S[:, 0, 0], S[:, 0, 1], S[:, 0, 2] = g(s11), g(s12), g(s13)
        S[:, 1, 0], S[:, 1, 1], S[:, 1, 2] = g(s12), g(s22), g(s23)
        S[:, 2, 0], S[:, 2, 1], S[:, 2, 2] = g(s13), g(s23), g(s33)
        U = [g(U1), g(U2), g(U3)]
        if p == 4:
            S[:, 0, 3] = S[:, 3, 0] = N * g(sum_fx)
            S[:, 1, 3] = S[:, 3, 1] = N * g(sum_fy)
            S[:, 2, 3] = S[:, 3, 2] = N * g(sum_fz)
            S[:, 3, 3] = N * N * npts
            U.append(N * (g(sum_c) + N * g(sum_f)))
        U = np.column_stack(U)
        # Centre transform: Tloc_i = U_i - xc*S_i1 - yc*S_i2 (S_i. = row i).
        Tloc = U - xc[:, None] * S[:, :, 0] - yc[:, None] * S[:, :, 1]
        Qloc = (g(Qabs) - 2.0 * xc * U[:, 0] - 2.0 * yc * U[:, 1]
                + xc * xc * S[:, 0, 0] + 2.0 * xc * yc * S[:, 0, 1] + yc * yc * S[:, 1, 1])
        del U, Qabs, s11, s12, s13, s22, s23, s33, sum_fx, sum_fy, sum_fz, sum_f, sum_c

        # Solve in sub-chunks to bound the batched-inverse memory.
        sub = 200_000
        sol = np.full((cy_idx.size, p), np.nan)
        rel = np.full(cy_idx.size, np.inf)
        for a in range(0, cy_idx.size, sub):
            b = min(a + sub, cy_idx.size)
            sol[a:b], rel[a:b] = _solve_candidates(S[a:b], Tloc[a:b], Qloc[a:b], npts)
        del S, Tloc, Qloc
        gy = cy_idx + r0
        out["dx0"][gy, cx_idx] = sol[:, 0]
        out["dy0"][gy, cx_idx] = sol[:, 1]
        out["depth"][gy, cx_idx] = sol[:, 2]
        out["rel_unc"][gy, cx_idx] = rel
        del sol, rel
        gc.collect()
    return out


def accept_euler_solutions(sol: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Apply preregistered acceptance gates (depth/offset/uncertainty).

    Returns (src_row, src_col, depth_px, rel_unc) for accepted solutions,
    with sub-pixel source positions rounded to the nearest pixel.
    """
    dx0, dy0, d, rel = sol["dx0"], sol["dy0"], sol["depth"], sol["rel_unc"]
    ok = (np.isfinite(dx0) & np.isfinite(dy0) & np.isfinite(d) & np.isfinite(rel)
          & (d >= DEPTH_MIN_PX) & (d <= DEPTH_MAX_PX)
          & (np.abs(dx0) <= OFFSET_MAX_PX) & (np.abs(dy0) <= OFFSET_MAX_PX)
          & (rel <= REL_UNC_MAX))
    cy, cx = np.nonzero(ok)
    sr = np.clip(np.rint(cy + dy0[cy, cx]).astype(np.int64), 0, d.shape[0] - 1)
    sc = np.clip(np.rint(cx + dx0[cy, cx]).astype(np.int64), 0, d.shape[1] - 1)
    return sr, sc, d[cy, cx].astype(np.float64), rel[cy, cx].astype(np.float64)


def rasterize_solutions(
    shape: tuple[int, int], sr: np.ndarray, sc: np.ndarray,
    depth: np.ndarray, rel: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Splat accepted solutions -> (dens_log, depth_mean, unc_mean, defined)."""
    count = np.zeros(shape, dtype=np.float64)
    dsum = np.zeros(shape, dtype=np.float64)
    usum = np.zeros(shape, dtype=np.float64)
    np.add.at(count, (sr, sc), 1.0)
    np.add.at(dsum, (sr, sc), depth)
    np.add.at(usum, (sr, sc), rel)
    dens = np.log1p(ndi.gaussian_filter(count, sigma=2.0)).astype(np.float32)
    wgt = ndi.gaussian_filter(count, sigma=3.0)
    defined = wgt > 0.05
    depth_mean = np.zeros(shape, dtype=np.float32)
    unc_mean = np.zeros(shape, dtype=np.float32)
    depth_mean[defined] = (ndi.gaussian_filter(dsum, sigma=3.0)[defined] / wgt[defined]).astype(np.float32)
    unc_mean[defined] = (ndi.gaussian_filter(usum, sigma=3.0)[defined] / wgt[defined]).astype(np.float32)
    return dens, depth_mean, unc_mean, defined


# --------------------------------------------------------------------------
# Field preparation + feature memmap builder.
# --------------------------------------------------------------------------
def _fft_vertical_derivative_perpx(field: np.ndarray, pad: int = 64) -> np.ndarray:
    """Vertical derivative (depth-positive, +|k|) per pixel via rFFT."""
    f = np.asarray(field, dtype=np.float64)
    f = f - float(f.mean())
    fp = np.pad(f, pad, mode="reflect")
    del f
    h, w = fp.shape
    fy = np.fft.fftfreq(h)
    fx = np.fft.rfftfreq(w)
    K = 2.0 * np.pi * np.hypot(fy[:, None], fx[None, :])
    spec = np.fft.rfft2(fp)
    del fp
    spec *= K
    del K
    dz = np.fft.irfft2(spec, s=(h, w))
    del spec
    gc.collect()
    return dz[pad:h - pad, pad:w - pad].astype(np.float32)


def _gaussian_derivatives(field: np.ndarray, sigma: float) -> tuple[np.ndarray, np.ndarray]:
    fy = ndi.gaussian_filter1d(field, sigma, axis=0, order=1, mode="nearest").astype(np.float32)
    fx = ndi.gaussian_filter1d(field, sigma, axis=1, order=1, mode="nearest").astype(np.float32)
    return fx, fy


def _robust_z_fp(vals: np.ndarray) -> np.ndarray:
    med = float(np.median(vals))
    mad = float(np.median(np.abs(vals - med))) * 1.4826 + 1e-6
    return np.clip((vals - med) / mad, -8.0, 8.0).astype(np.float32)


def _combo_grids(
    F: np.ndarray, Fx: np.ndarray, Fy: np.ndarray, Fz: np.ndarray,
    interior: np.ndarray, N: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    amp = np.sqrt(Fx.astype(np.float64) ** 2 + Fy.astype(np.float64) ** 2 + Fz.astype(np.float64) ** 2)
    amp_win = ndi.uniform_filter(amp.astype(np.float32), size=WINDOW_PX, mode="nearest")
    del amp
    thr = float(np.percentile(amp_win[interior], AMP_GATE_PERCENTILE)) if interior.any() else np.inf
    cand = interior & (amp_win >= thr)
    # Never centre a window that would touch array-edge padding/replication.
    cand[:WINDOW_PX, :] = False
    cand[-WINDOW_PX:, :] = False
    cand[:, :WINDOW_PX] = False
    cand[:, -WINDOW_PX:] = False
    del amp_win
    sol = euler_solve_fast(F, Fx, Fy, Fz, structural_index=N, candidate_mask=cand)
    sr, sc, dep, rel = accept_euler_solutions(sol)
    stats = {
        "n_candidates": int(cand.sum()),
        "n_accepted": int(sr.size),
        "amp_gate_threshold": thr,
        "depth_px_median_accepted": float(np.median(dep)) if dep.size else None,
    }
    del sol, cand
    gc.collect()
    dens, depth_mean, unc_mean, defined = rasterize_solutions(F.shape, sr, sc, dep, rel)
    return dens, depth_mean, unc_mean, defined, stats


def build_or_load_eulr_feature_memmap(
    *,
    features_tif: str | Path,
    footprint: np.ndarray,
    cache_dir: str | Path,
    force_rebuild: bool = False,
) -> tuple[np.memmap, list[str], dict]:
    """Build or open the disk-backed ``(N_fp, 14)`` float32 S17 Euler matrix."""
    cache_p = Path(cache_dir)
    cache_p.mkdir(parents=True, exist_ok=True)
    dat_path = cache_p / "s17_eulr_features_v1.dat"
    meta_path = cache_p / "s17_eulr_features_v1.json"
    n_fp = int(footprint.sum())
    n_cols = len(EULR_FEATURE_NAMES)
    if not force_rebuild and dat_path.is_file() and meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if (meta.get("n_fp") == n_fp and meta.get("feature_names") == EULR_FEATURE_NAMES
                and dat_path.stat().st_size == n_fp * n_cols * 4):
            mm = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
            return mm, list(EULR_FEATURE_NAMES), meta

    def read_band(n: int) -> np.ndarray:
        with rasterio.open(features_tif) as src:
            return src.read(n)

    def valid_mask(*bands: np.ndarray) -> np.ndarray:
        m = footprint.copy()
        for b in bands:
            m &= np.isfinite(b) & (b > -1.0e30)
        return m

    def interior_of(valid: np.ndarray) -> np.ndarray:
        return ndi.distance_transform_edt(valid) >= INTERIOR_CLEARANCE_PX

    raw: dict[tuple[str, int], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    combo_stats: dict[str, dict] = {}

    # ---- magnetic (B14 field, B09 vertical derivative) ----
    b14_raw, b09_raw = read_band(14), read_band(9)
    mag_interior = interior_of(valid_mask(b14_raw, b09_raw))
    b14 = _clean_band_edt(b14_raw, footprint)
    b09 = _clean_band_edt(b09_raw, footprint)
    del b14_raw, b09_raw
    F_mag = ndi.gaussian_filter(b14, sigma=MAG_SIGMA).astype(np.float32)
    Fx_mag, Fy_mag = _gaussian_derivatives(b14, MAG_SIGMA)
    Fz_mag = ndi.gaussian_filter((b09 * np.float32(100.0)).astype(np.float32), sigma=MAG_SIGMA).astype(np.float32)
    del b14, b09
    gc.collect()
    for N in (0, 1):
        dens, dep, unc, defined, st = _combo_grids(F_mag, Fx_mag, Fy_mag, Fz_mag, mag_interior, float(N))
        raw[("mag", N)] = (dens, dep, unc, defined)
        combo_stats[f"mag{N}"] = st
    del F_mag, Fx_mag, Fy_mag, Fz_mag, mag_interior
    gc.collect()

    # ---- gravity (B13 field, FFT vertical derivative) ----
    b13_raw = read_band(13)
    grav_interior = interior_of(valid_mask(b13_raw))
    b13 = _clean_band_edt(b13_raw, footprint)
    del b13_raw
    F_grav = ndi.gaussian_filter(b13, sigma=GRAV_SIGMA).astype(np.float32)
    Fx_grav, Fy_grav = _gaussian_derivatives(b13, GRAV_SIGMA)
    Fz_grav = ndi.gaussian_filter(_fft_vertical_derivative_perpx(b13), sigma=GRAV_SIGMA).astype(np.float32)
    del b13
    gc.collect()
    for N in (0, 1):
        dens, dep, unc, defined, st = _combo_grids(F_grav, Fx_grav, Fy_grav, Fz_grav, grav_interior, float(N))
        raw[("grav", N)] = (dens, dep, unc, defined)
        combo_stats[f"grav{N}"] = st
    del F_grav, Fx_grav, Fy_grav, Fz_grav, grav_interior
    gc.collect()

    # ---- assemble footprint matrix (robust-z; undefined depth/unc -> median) ----
    mm = np.memmap(dat_path, dtype=np.float32, mode="w+", shape=(n_fp, n_cols))
    fill_frac: dict[str, float] = {}
    col = 0
    for key in _COMBOS:
        dens, dep, unc, defined = raw[key]
        for grid, is_defined_limited in ((dens, False), (dep, True), (unc, True)):
            vals = grid[footprint].astype(np.float32)
            if is_defined_limited:
                ok = defined[footprint]
                fill_frac[EULR_FEATURE_NAMES[col]] = float(1.0 - ok.mean())
                if ok.any():
                    vals = vals.copy()
                    vals[~ok] = float(np.median(vals[ok]))
            mm[:, col] = _robust_z_fp(vals)
            col += 1
    # joint density (geometric-mean in log-density space: mag0 x grav1)
    joint = 0.5 * (raw[("mag", 0)][0][footprint] + raw[("grav", 1)][0][footprint])
    mm[:, col] = _robust_z_fp(joint.astype(np.float32))
    col += 1
    # mag0 depth vs B15 agreement
    b15 = _clean_band_edt(read_band(15), footprint)
    dep0, def0 = raw[("mag", 0)][1], raw[("mag", 0)][3]
    agree = np.clip(-np.abs(dep0 * np.float32(100.0) - b15) / np.float32(1000.0), -5.0, 0.0)
    vals = agree[footprint].astype(np.float32)
    ok = def0[footprint]
    fill_frac[EULR_FEATURE_NAMES[col]] = float(1.0 - ok.mean())
    if ok.any():
        vals = vals.copy()
        vals[~ok] = float(np.median(vals[ok]))
    mm[:, col] = _robust_z_fp(vals)
    col += 1
    del b15, raw, joint, agree, vals
    assert col == n_cols, (col, n_cols)
    if not np.isfinite(np.asarray(mm[::9973])).all():
        raise RuntimeError("nonfinite S17 Euler features (strided check)")
    mm.flush()
    meta = {
        "feature_names": EULR_FEATURE_NAMES,
        "n_fp": n_fp,
        "window_px": WINDOW_PX,
        "mag_sigma": MAG_SIGMA,
        "grav_sigma": GRAV_SIGMA,
        "interior_clearance_px": INTERIOR_CLEARANCE_PX,
        "amp_gate_percentile": AMP_GATE_PERCENTILE,
        "depth_range_px": [DEPTH_MIN_PX, DEPTH_MAX_PX],
        "offset_max_px": OFFSET_MAX_PX,
        "rel_unc_max": REL_UNC_MAX,
        "combo_stats": combo_stats,
        "undefined_fill_fraction": fill_frac,
        "label_free": True,
        "catalogue_used_in_construction": False,
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    del mm
    gc.collect()
    mm_ro = np.memmap(dat_path, dtype=np.float32, mode="r", shape=(n_fp, n_cols))
    # Full finiteness verification on the written bytes (chunked).
    for s in range(0, n_fp, 500_000):
        if not np.isfinite(np.asarray(mm_ro[s:s + 500_000])).all():
            raise RuntimeError("nonfinite S17 Euler features on disk")
    return mm_ro, list(EULR_FEATURE_NAMES), meta
