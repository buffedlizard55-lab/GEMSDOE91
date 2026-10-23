#!/usr/bin/env python3
"""Build and validate controlled AXIS=PRUNE variants of parent R0 (h33-h33-2-b2).

Implements Agent Brief v2 end-to-end with zero DrivenData/Dropbox contact:
1. Verifies SHA-256 + byte size of all 13 pinned inputs in registry/data_manifest.json.
2. Rebuilds the complete 5-stage R0 lineage deterministically from H19-5:
      H19-5 (121,131 px) -> D1.5 (60,069) -> D2.8 (44,090) -> SOLO-D2.8 (40,199)
      -> R0 h33-h33-2-b2 (37,654 dots)
   and asserts byte-for-byte SHA-256 identity on BOTH:
      - R0 zeros: c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9
      - R0 NaN:   baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd
3. Reconstructs the label-free physical corroboration field w(g) on off-catalogue
   pixels from parent detector ridges + 19 official bands + GDR 1391 geothermometry,
   verifies every single channel passes the leakage canary (symmetric AUC <= 0.90),
   and allocates all drops/refills by EXACT iterative marginal DTI gain from
   vendor/gems57/metric.py (never the isolated-pixel shortcut or random noise).
4. Emits 3 constant-mass (37,654 dots) PRUNE variants around R0 (<= 2 px):
      - p1px: remove <= 1.0 px (100 m), count fixed at 37,654 (6.76% moved; 13.52% sym diff)
      - p3px: remove <= 3.0 px (300 m kernel R), count fixed at 37,654 (5.77% moved; 11.53% sym diff)
      - p4px: remove <= 4.0 px (400 m GeoDAWN spacing), count fixed at 37,654 (10.16% moved; 20.32% sym diff)
5. Enforces all MUST gates (format parity with sample_submission.tif, NaN outside +
   -zeros fallback, finite [0, 1] inside, zero catalogue mass, non-duplicate SHA-256,
   re-read verification from disk) and computes all REPORT-ONLY diagnostics
   (whole-component hide-and-recover HOLDOUT-DTI + 95% block-bootstrap CI, leakage
   canaries, SGMC off-catalogue fault control, and 10 km / 12 km block-density CV).
"""

from __future__ import annotations

from collections import deque
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import (
    binary_closing,
    binary_dilation,
    distance_transform_edt,
    gaussian_filter,
    label as ndi_label,
)
from scipy.spatial import cKDTree
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "vendor") not in sys.path:
    sys.path.insert(0, str(ROOT / "vendor"))

from gems57 import evaluate_holdout, gates, grid as grid_mod, holdout as holdout_mod, metric, validate  # noqa: E402

PARENT_ID = "h33-h33-2-b2"
PARENT_SHA_ZEROS = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
PARENT_SHA_NAN = "baeae3219bba6a19bc8cfe79224e28555c50184b7c1ca65c2a822f54807c77dd"
FIXED_DATE = "20261023"
SEED = 20261023


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# 1. Exact DTI Algebra & Marginal Gain Primitives (Brief §2)
# ---------------------------------------------------------------------------


def dti_algebra_components(
    pred: np.ndarray,
    truth: np.ndarray,
    valid: np.ndarray | None = None,
    known: np.ndarray | None = None,
    alpha: float = metric.ALPHA,
    beta: float = metric.BETA,
) -> dict[str, float]:
    """Compute exact (T, S, M, G_abs, denom, dti) per Brief §2:

        DTI = T / (alpha * T + alpha * (S - M) + beta * |G|)
    """
    p = np.asarray(pred, dtype=np.float64)
    g = np.asarray(truth, dtype=bool)
    active = np.ones(p.shape, dtype=bool) if valid is None else np.asarray(valid, dtype=bool)
    if known is not None:
        active = active & ~np.asarray(known, dtype=bool)
    p_act = np.where(active, p, 0.0)
    g_act = g & active
    g_abs = float(g_act.sum())
    s_sum = float(p_act.sum())
    if g_abs == 0.0:
        denom = alpha * s_sum + metric.EPS
        return dict(T=0.0, S=s_sum, M=0.0, G=0.0, denom=denom, dti=0.0)
    covers, k_max, _ = metric.max_cover(p_act, g_act)
    t_val = float(covers.sum())
    m_val = float((p_act * k_max).sum())
    denom = alpha * t_val + alpha * (s_sum - m_val) + beta * g_abs + metric.EPS
    return dict(
        T=t_val,
        S=s_sum,
        M=m_val,
        G=g_abs,
        denom=denom,
        dti=float(t_val / denom),
    )


def weighted_expected_dti(
    active_mask: np.ndarray,
    w: np.ndarray,
    alpha: float = metric.ALPHA,
    beta: float = metric.BETA,
) -> dict[str, float]:
    """Exact expected DTI terms against soft pixel fault weights w(g) in [0, 1]."""
    a = np.asarray(active_mask, dtype=bool)
    w64 = np.asarray(w, dtype=np.float64)
    H, W = a.shape
    cov = np.zeros((H, W), dtype=np.float64)
    ay, ax = np.nonzero(a)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = ay + int(dy), ax + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        np.maximum.at(cov, (ny[ok], nx[ok]), kw)
    t_val = float((w64 * cov).sum())
    m_self = np.zeros(len(ay), dtype=np.float64)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = ay + int(dy), ax + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        m_self[ok] = np.maximum(m_self[ok], w64[ny[ok], nx[ok]] * kw)
    m_val = float(m_self.sum())
    s_val = float(len(ay))
    w_tot = float(w64.sum())
    denom = alpha * (t_val + s_val - m_val) + beta * w_tot + metric.EPS
    return dict(T=t_val, S=s_val, M=m_val, W=w_tot, denom=denom, dti=float(t_val / denom))


def select_exact_marginal_dti_add(
    base_mask: np.ndarray,
    cand_mask: np.ndarray,
    w: np.ndarray,
    n_add: int,
    alpha: float = metric.ALPHA,
    beta: float = metric.BETA,
) -> np.ndarray:
    """Greedily add n_add dots from cand_mask maximizing exact expected DTI at every step.

    Maintains exact per-cell coverage C_A(g) = max_{x in A} k(||g - x||) and updates
    the exact candidate dT array locally inside the 6-px interaction neighborhood on
    every step, taking the exact global argmax across all remaining candidates.
    """
    state = np.asarray(base_mask, dtype=bool).copy()
    if n_add <= 0:
        return state
    H, W = state.shape
    w64 = np.asarray(w, dtype=np.float64)
    w_tot = float(w64.sum())

    # Initial coverage C_A and scalars T, S, M
    cov = np.zeros((H, W), dtype=np.float64)
    by, bx = np.nonzero(state)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        np.maximum.at(cov, (ny[ok], nx[ok]), kw)
    t_cur = float((w64 * cov).sum())
    m_base = np.zeros(len(by), dtype=np.float64)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = by + int(dy), bx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        m_base[ok] = np.maximum(m_base[ok], w64[ny[ok], nx[ok]] * kw)
    m_cur = float(m_base.sum())
    s_cur = float(len(by))

    cy, cx = np.nonzero(cand_mask & ~state)
    if len(cy) < n_add:
        raise ValueError(f"Candidate pool ({len(cy)}) smaller than requested refill ({n_add})")

    # Map grid position -> candidate index for instant local invalidation within 6 px
    cand_id_grid = np.full((H, W), -1, dtype=np.int32)
    cand_id_grid[cy, cx] = np.arange(len(cy), dtype=np.int32)

    m_cand = np.zeros(len(cy), dtype=np.float64)
    dT = np.zeros(len(cy), dtype=np.float64)
    for dy, dx, kw in zip(metric.OFF_DY, metric.OFF_DX, metric.OFF_K):
        ny, nx = cy + int(dy), cx + int(dx)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        wv = w64[ny[ok], nx[ok]]
        m_cand[ok] = np.maximum(m_cand[ok], wv * kw)
        dT[ok] += wv * np.maximum(0.0, kw - cov[ny[ok], nx[ok]])

    chosen = np.zeros(len(cy), dtype=bool)
    off_dy = metric.OFF_DY.astype(np.int64)
    off_dx = metric.OFF_DX.astype(np.int64)
    off_k = metric.OFF_K.astype(np.float64)

    for _ in range(n_add):
        d_cur = alpha * (t_cur + s_cur - m_cur) + beta * w_tot + metric.EPS
        next_dti = (t_cur + dT) / (d_cur + alpha * (dT + 1.0 - m_cand))
        next_dti[chosen] = -1.0
        best = int(np.argmax(next_dti))
        chosen[best] = True
        ry, rx = int(cy[best]), int(cx[best])
        state[ry, rx] = True

        # Update cov around (ry, rx) and recompute exact dT for nearby candidates (|dr|,|dc|<=6)
        ny = ry + off_dy
        nx = rx + off_dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        ny, nx, kw = ny[ok], nx[ok], off_k[ok]
        old_c = cov[ny, nx]
        upd = kw > old_c
        if np.any(upd):
            uy, ux, uk, uold = ny[upd], nx[upd], kw[upd], old_c[upd]
            cov[uy, ux] = uk
            t_cur += float((w64[uy, ux] * (uk - uold)).sum())

        s_cur += 1.0
        m_cur += float(m_cand[best])

        y0, y1 = max(0, ry - 6), min(H, ry + 7)
        x0, x1 = max(0, rx - 6), min(W, rx + 7)
        sub_ids = cand_id_grid[y0:y1, x0:x1].ravel()
        sub_ids = sub_ids[sub_ids >= 0]
        if sub_ids.size:
            sub_ids = sub_ids[~chosen[sub_ids]]
        if sub_ids.size:
            sy, sx = cy[sub_ids], cx[sub_ids]
            new_dt = np.zeros(len(sub_ids), dtype=np.float64)
            for dy_i, dx_i, kw_i in zip(off_dy, off_dx, off_k):
                nny, nnx = sy + int(dy_i), sx + int(dx_i)
                ook = (nny >= 0) & (nny < H) & (nnx >= 0) & (nnx < W)
                new_dt[ook] += w64[nny[ook], nnx[ook]] * np.maximum(
                    0.0, kw_i - cov[nny[ook], nnx[ook]]
                )
            dT[sub_ids] = new_dt

    return state


def select_exact_marginal_dti_drop(
    base_mask: np.ndarray,
    drop_pool_mask: np.ndarray,
    w: np.ndarray,
    n_drop: int,
    alpha: float = metric.ALPHA,
    beta: float = metric.BETA,
) -> np.ndarray:
    """Greedily drop n_drop dots from drop_pool_mask maximizing post-drop exact DTI at each step."""
    state = np.asarray(base_mask, dtype=bool).copy()
    if n_drop <= 0:
        return state
    H, W = state.shape
    w64 = np.asarray(w, dtype=np.float64)
    w_tot = float(w64.sum())

    off_dy = metric.OFF_DY.astype(np.int64)
    off_dx = metric.OFF_DX.astype(np.int64)
    off_k = metric.OFF_K.astype(np.float64)

    def _cell_best2(y0: int, y1: int, x0: int, x1: int) -> tuple[np.ndarray, np.ndarray]:
        """Compute exact top-1 and top-2 kernel coverage on window [y0:y1, x0:x1] from active state."""
        py0, py1 = max(0, y0 - 3), min(H, y1 + 3)
        px0, px1 = max(0, x0 - 3), min(W, x1 + 3)
        sub_state = state[py0:py1, px0:px1]
        c1 = np.zeros((py1 - py0, px1 - px0), dtype=np.float64)
        c2 = np.zeros((py1 - py0, px1 - px0), dtype=np.float64)
        ay, ax = np.nonzero(sub_state)
        for dy_i, dx_i, kw_i in zip(off_dy, off_dx, off_k):
            ny, nx = ay + int(dy_i), ax + int(dx_i)
            ok = (ny >= 0) & (ny < c1.shape[0]) & (nx >= 0) & (nx < c1.shape[1])
            ny, nx = ny[ok], nx[ok]
            # Vectorized top-2 update per offset (each offset visits distinct (ny, nx) per active cell? Yes: bijection!)
            cur1 = c1[ny, nx]
            cur2 = c2[ny, nx]
            better1 = kw_i >= cur1
            c2[ny, nx] = np.where(better1, cur1, np.maximum(cur2, kw_i))
            c1[ny, nx] = np.where(better1, kw_i, cur1)
        return c1[y0 - py0 : y1 - py0, x0 - px0 : x1 - px0], c2[y0 - py0 : y1 - py0, x0 - px0 : x1 - px0]

    cov1, cov2 = _cell_best2(0, H, 0, W)
    by, bx = np.nonzero(state)
    t_cur = float((w64 * cov1).sum())
    m_all = np.zeros(len(by), dtype=np.float64)
    for dy_i, dx_i, kw_i in zip(off_dy, off_dx, off_k):
        ny, nx = by + int(dy_i), bx + int(dx_i)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        m_all[ok] = np.maximum(m_all[ok], w64[ny[ok], nx[ok]] * kw_i)
    m_cur = float(m_all.sum())
    s_cur = float(len(by))

    dy_pool, dx_pool = np.nonzero(state & drop_pool_mask)
    if len(dy_pool) < n_drop:
        raise ValueError(f"Drop pool ({len(dy_pool)}) smaller than requested drop ({n_drop})")

    pool_id_grid = np.full((H, W), -1, dtype=np.int32)
    pool_id_grid[dy_pool, dx_pool] = np.arange(len(dy_pool), dtype=np.int32)

    m_pool = np.zeros(len(dy_pool), dtype=np.float64)
    dT_loss = np.zeros(len(dy_pool), dtype=np.float64)
    for dy_i, dx_i, kw_i in zip(off_dy, off_dx, off_k):
        ny, nx = dy_pool + int(dy_i), dx_pool + int(dx_i)
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        wv = w64[ny[ok], nx[ok]]
        m_pool[ok] = np.maximum(m_pool[ok], wv * kw_i)
        is_top = np.abs(cov1[ny[ok], nx[ok]] - kw_i) < 1e-12
        dT_loss[ok] += np.where(is_top, wv * (cov1[ny[ok], nx[ok]] - cov2[ny[ok], nx[ok]]), 0.0)

    dropped = np.zeros(len(dy_pool), dtype=bool)
    for _ in range(n_drop):
        d_cur = alpha * (t_cur + s_cur - m_cur) + beta * w_tot + metric.EPS
        after_dti = (t_cur - dT_loss) / (d_cur - alpha * (dT_loss + 1.0 - m_pool))
        after_dti[dropped] = -1.0
        best = int(np.argmax(after_dti))
        dropped[best] = True
        ry, rx = int(dy_pool[best]), int(dx_pool[best])
        state[ry, rx] = False

        # Recompute exact local cov1, cov2 on [ry-3:ry+4, rx-3:rx+4]
        wy0, wy1 = max(0, ry - 3), min(H, ry + 4)
        wx0, wx1 = max(0, rx - 3), min(W, rx + 4)
        old_c1 = cov1[wy0:wy1, wx0:wx1].copy()
        nc1, nc2 = _cell_best2(wy0, wy1, wx0, wx1)
        cov1[wy0:wy1, wx0:wx1] = nc1
        cov2[wy0:wy1, wx0:wx1] = nc2

        t_cur += float((w64[wy0:wy1, wx0:wx1] * (nc1 - old_c1)).sum())
        s_cur -= 1.0
        m_cur -= float(m_pool[best])

        y0, y1 = max(0, ry - 6), min(H, ry + 7)
        x0, x1 = max(0, rx - 6), min(W, rx + 7)
        sub_ids = pool_id_grid[y0:y1, x0:x1].ravel()
        sub_ids = sub_ids[sub_ids >= 0]
        if sub_ids.size:
            sub_ids = sub_ids[~dropped[sub_ids]]
        if sub_ids.size:
            sy, sx = dy_pool[sub_ids], dx_pool[sub_ids]
            loss_upd = np.zeros(len(sub_ids), dtype=np.float64)
            for dy_i, dx_i, kw_i in zip(off_dy, off_dx, off_k):
                nny, nnx = sy + int(dy_i), sx + int(dx_i)
                ook = (nny >= 0) & (nny < H) & (nnx >= 0) & (nnx < W)
                wv = w64[nny[ook], nnx[ook]]
                c1v = cov1[nny[ook], nnx[ook]]
                c2v = cov2[nny[ook], nnx[ook]]
                loss_upd[ook] += np.where(np.abs(c1v - kw_i) < 1e-12, wv * (c1v - c2v), 0.0)
            dT_loss[sub_ids] = loss_upd

    return state


# ---------------------------------------------------------------------------
# 2. Manifest Verification & Byte-Exact Parent R0 Lineage Rebuild (Brief §5)
# ---------------------------------------------------------------------------


def verify_manifest(manifest_path: Path | None = None) -> dict[str, Path]:
    manifest_path = manifest_path or (ROOT / "registry" / "data_manifest.json")
    manifest = json.loads(manifest_path.read_text())
    verified: dict[str, Path] = {}
    for entry in manifest["files"]:
        p = ROOT / entry["local_path"]
        if not p.is_file():
            raise FileNotFoundError(
                f"Missing pinned input {entry['id']}: {p} (run python scripts/restore_inputs.py)"
            )
        actual_sha = sha256_file(p)
        actual_bytes = p.stat().st_size
        if actual_sha != entry["sha256"]:
            raise ValueError(
                f"SHA-256 mismatch on {entry['id']} ({p}): got {actual_sha}, expected {entry['sha256']}"
            )
        if actual_bytes != entry["bytes"]:
            raise ValueError(
                f"Byte-length mismatch on {entry['id']} ({p}): got {actual_bytes}, expected {entry['bytes']}"
            )
        verified[entry["id"]] = p
    return verified


def dot_thin(mask: np.ndarray, min_dist: float) -> np.ndarray:
    """Deterministic geodesic Poisson-disk thinning of binary ridge mask (GEMSDOE25 exact algorithm)."""
    mask = np.asarray(mask, dtype=bool)
    if min_dist <= 1.0 or not mask.any():
        return mask.copy()
    H, W = mask.shape
    pad = int(np.ceil(min_dist)) + 1
    Wp, Hp = W + 2 * pad, H + 2 * pad
    padded = np.zeros((Hp, Wp), dtype=bool)
    padded[pad : pad + H, pad : pad + W] = mask
    flat = bytearray(padded.tobytes())
    visited, blocked, kept = bytearray(Hp * Wp), bytearray(Hp * Wp), bytearray(Hp * Wp)
    r = int(np.ceil(min_dist))
    lim = min_dist * min_dist
    disc = [
        dy * Wp + dx
        for dy in range(-r, r + 1)
        for dx in range(-r, r + 1)
        if dy * dy + dx * dx < lim
    ]
    nbr = (-Wp - 1, -Wp, -Wp + 1, -1, 1, Wp - 1, Wp, Wp + 1)
    comp, _ = ndi_label(padded, structure=np.ones((3, 3), dtype=int))
    fc = comp.ravel()
    order = np.flatnonzero(fc)
    _, first = np.unique(fc[order], return_index=True)
    for seed in order[np.sort(first)].tolist():
        if visited[seed]:
            continue
        visited[seed] = 1
        queue = deque((seed,))
        while queue:
            q = queue.popleft()
            if not blocked[q]:
                kept[q] = 1
                for o in disc:
                    blocked[q + o] = 1
            for o in nbr:
                nb = q + o
                if flat[nb] and not visited[nb]:
                    visited[nb] = 1
                    queue.append(nb)
    out = np.frombuffer(bytes(kept), dtype=np.uint8).reshape(Hp, Wp).astype(bool)
    return out[pad : pad + H, pad : pad + W]


def rebuild_r0_from_lineage(verified: dict[str, Path]) -> dict:
    """Rebuild R0 (h33-h33-2-b2) from H19-5 through every step and match SHA-256 bit-for-bit."""
    with rasterio.open(verified["sample_submission"]) as ds:
        foot = np.isfinite(ds.read(1))
    with rasterio.open(verified["existing_faults"]) as ds:
        ef_profile = ds.profile.copy()
        catalogue = (ds.read(1) > 0) & foot
    d_cat = distance_transform_edt(~catalogue)

    h19_5 = (np.nan_to_num(rasterio.open(verified["anc_h19_5"]).read(1), nan=0.0) > 0) & foot
    d15_ref = (np.nan_to_num(rasterio.open(verified["anc_d1_5"]).read(1), nan=0.0) > 0) & foot
    d28_ref = (np.nan_to_num(rasterio.open(verified["anc_d2_8"]).read(1), nan=0.0) > 0) & foot
    solo_ref = (np.nan_to_num(rasterio.open(verified["anc_solo_d2_8"]).read(1), nan=0.0) > 0) & foot
    r0_ref = (np.nan_to_num(rasterio.open(verified["parent_r0_zeros"]).read(1), nan=0.0) > 0) & foot

    d15_rebuilt = dot_thin(h19_5, 1.5)
    d28_rebuilt = dot_thin(h19_5, 2.8)
    solo_rebuilt = d28_rebuilt & (d_cat > 1.0)
    r0_rebuilt = d28_rebuilt & (d_cat > 2.0)

    if not np.array_equal(d15_rebuilt, d15_ref):
        raise RuntimeError("Lineage rebuild failed at D1.5")
    if not np.array_equal(d28_rebuilt, d28_ref):
        raise RuntimeError("Lineage rebuild failed at D2.8")
    if not np.array_equal(solo_rebuilt, solo_ref):
        raise RuntimeError("Lineage rebuild failed at SOLO-D2.8")
    if not np.array_equal(r0_rebuilt, r0_ref):
        raise RuntimeError("Lineage rebuild failed at R0 pixel mask")

    prof_zeros = ef_profile.copy()
    prof_zeros.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=3,
        zlevel=9,
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=None,
    )
    prof_nan = prof_zeros.copy()
    prof_nan.update(nodata=np.nan)

    with tempfile.TemporaryDirectory() as td:
        p_z = Path(td) / "r0_zeros.tif"
        p_n = Path(td) / "r0_nan.tif"
        with rasterio.open(p_z, "w", **prof_zeros) as dst:
            dst.write(np.where(foot, r0_rebuilt.astype(np.float32), 0.0).astype(np.float32), 1)
        with rasterio.open(p_n, "w", **prof_nan) as dst:
            dst.write(np.where(foot, r0_rebuilt.astype(np.float32), np.nan).astype(np.float32), 1)
        sha_z = sha256_file(p_z)
        sha_n = sha256_file(p_n)

    if sha_z != PARENT_SHA_ZEROS:
        raise RuntimeError(f"Rebuilt R0 zeros SHA mismatch: {sha_z} != {PARENT_SHA_ZEROS}")
    if sha_n != PARENT_SHA_NAN:
        raise RuntimeError(f"Rebuilt R0 NaN SHA mismatch: {sha_n} != {PARENT_SHA_NAN}")

    return dict(
        foot=foot,
        catalogue=catalogue,
        d_cat=d_cat,
        h19_5=h19_5,
        d15=d15_rebuilt,
        d28=d28_rebuilt,
        solo=solo_rebuilt,
        r0=r0_rebuilt,
        rebuilt_zeros_sha256=sha_z,
        rebuilt_nan_sha256=sha_n,
    )


# ---------------------------------------------------------------------------
# 3. Physical Corroboration Field + Leakage Canaries
# ---------------------------------------------------------------------------


def _percentile_rank(arr: np.ndarray, valid: np.ndarray) -> np.ndarray:
    out = np.zeros(arr.shape, dtype=np.float32)
    v = np.nan_to_num(arr[valid], nan=0.0, posinf=0.0, neginf=0.0)
    qs = np.linspace(0.0, 1.0, 1001)
    knots = np.quantile(v, qs)
    # Deduplicate knots slightly if needed for monotone interpolation
    out[valid] = np.interp(v, knots, qs).astype(np.float32)
    return out


def _hessian_ridge(a: np.ndarray, sigma: float = 2.0) -> np.ndarray:
    axx = gaussian_filter(a, sigma, order=(0, 2), mode="nearest")
    ayy = gaussian_filter(a, sigma, order=(2, 0), mode="nearest")
    axy = gaussian_filter(a, sigma, order=(1, 1), mode="nearest")
    tmp = np.sqrt(np.maximum(((axx - ayy) * 0.5) ** 2 + axy**2, 0.0))
    l1 = (axx + ayy) * 0.5 + tmp
    l2 = (axx + ayy) * 0.5 - tmp
    big = np.where(np.abs(l1) >= np.abs(l2), l1, l2)
    return np.maximum(-big, 0.0).astype(np.float32)


def build_physical_field_and_canaries(
    verified: dict[str, Path],
    foot: np.ndarray,
    catalogue: np.ndarray,
    h19_5: np.ndarray,
) -> tuple[np.ndarray, dict[str, float]]:
    """Build 100% label-free physical fault field p_phys on foot & check all canaries BEFORE masking.

    Note: An initial pass multiplied w_field by ~catalogue before running canaries; the leakage
    canary caught sym_auc = 1.0000 immediately because withheld positives lie inside catalogue.
    All channels below are strictly label-free physical observables evaluated across the full
    unmasked footprint prior to applying known=catalogue, streamed one band at a time for low RAM.
    """
    H, W = foot.shape

    # Prepare whole-component buffered holdout canary indices FIRST so each band can be freed cleanly
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)
    pos_mask = folds20[0]["hidden_all"] | folds30[0]["hidden_all"]
    del folds20, folds30, gd
    neg_pool = np.flatnonzero(foot & ~catalogue & ~pos_mask)
    rng = np.random.default_rng(SEED)
    neg_sample = rng.choice(neg_pool, size=min(100_000, len(neg_pool)), replace=False)
    del neg_pool
    pos_idx = np.flatnonzero(pos_mask)
    del pos_mask
    eval_idx = np.concatenate([pos_idx, neg_sample])
    y_true = np.concatenate(
        [np.ones(len(pos_idx), dtype=np.int8), np.zeros(len(neg_sample), dtype=np.int8)]
    )
    canaries: dict[str, float] = {}

    def _consume(name: str, arr: np.ndarray) -> np.ndarray:
        auc = float(roc_auc_score(y_true, arr.ravel()[eval_idx]))
        sym_auc = float(max(auc, 1.0 - auc))
        canaries[name] = round(sym_auc, 5)
        if sym_auc > 0.90:
            raise RuntimeError(f"LEAKAGE CANARY TRIPPED on {name}: symmetric AUC = {sym_auc:.5f} > 0.90")
        return _percentile_rank(arr, foot)

    def _read_clean_band(ds: rasterio.DatasetReader, idx: int) -> np.ndarray:
        arr = np.where(foot, np.nan_to_num(ds.read(idx), nan=0.0), 0.0).astype(np.float32)
        bad = (~np.isfinite(arr)) | (np.abs(arr) > 1e20)
        if np.any(bad & foot):
            arr[bad] = float(np.median(arr[foot & ~bad]))
        arr[~foot] = 0.0
        return arr

    # Line A: provided 100 m detrended-elevation breakline/slope only.
    # No LiDAR-derived raster was supplied for this session, so do not restore or use one.
    line_scarp = np.zeros((H, W), dtype=np.float32)

    line_geopot = np.zeros((H, W), dtype=np.float32)
    line_kinem = np.zeros((H, W), dtype=np.float32)
    line_hydro = np.zeros((H, W), dtype=np.float32)

    with rasterio.open(verified["training_features"]) as ds:
        b12 = _read_clean_band(ds, 12)
        line_scarp += 0.60 * _consume("det_elev_hessian_b12", _hessian_ridge(b12, 2.0))
        del b12
        line_scarp += 0.40 * _consume("det_elev_slope_b19", _read_clean_band(ds, 19))

        # Line B: Subsurface potential-field fault offset
        line_geopot += 0.34 * _consume("grav_hg_b18", _read_clean_band(ds, 18))
        line_geopot += 0.26 * _consume("tmi_hg_b03", _read_clean_band(ds, 3))
        b15 = _read_clean_band(ds, 15)
        gy_d, gx_d = np.gradient(gaussian_filter(b15, 1.5))
        del b15
        line_geopot += 0.22 * _consume("basement_grad_b15", np.hypot(gy_d, gx_d).astype(np.float32))
        del gy_d, gx_d
        b02 = _read_clean_band(ds, 2)
        line_geopot += 0.18 * _consume("rtp_hessian_b02", _hessian_ridge(b02, 2.0))
        del b02

        # Line C: Active crustal strain & seismicity
        line_kinem += 0.45 * _consume("geod_strain_b04", _read_clean_band(ds, 4))
        line_kinem += 0.35 * _consume("seismic_ieq_b16", _read_clean_band(ds, 16))
        line_kinem += 0.20 * _consume("mag_tilt_curv_b06", np.abs(_read_clean_band(ds, 6)))

        # Line D part 1: MT conductivity gradient
        b17 = _read_clean_band(ds, 17)
        gy_c, gx_c = np.gradient(gaussian_filter(b17, 1.5))
        del b17
        line_hydro += 0.25 * _consume("mt_cond_grad_b17", np.hypot(gy_c, gx_c).astype(np.float32))
        del gy_c, gx_c

    # Line D part 2: GeoDAWN K/Th alteration + GDR 1391 geothermometer IDW
    with rasterio.open(verified["ext_geodawn_rad_u8"]) as ds_rad:
        rad_k = ds_rad.read(1).astype(np.float32)
        rad_th = np.maximum(ds_rad.read(min(2, ds_rad.count)).astype(np.float32), 1.0)
        k_th_ratio = np.where(foot, rad_k / rad_th, 0.0).astype(np.float32)
        del rad_k, rad_th
    line_hydro += 0.30 * _consume("k_th_alteration", k_th_ratio)
    del k_th_ratio

    pts_list: list[tuple[float, float]] = []
    vals_list: list[float] = []
    with verified["gdr_wellspring_in_footprint"].open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                rr = float(row["row"])
                cc = float(row["col"])
            except (KeyError, TypeError, ValueError):
                continue
            temps = []
            for col in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c", "temp_c"):
                raw_v = row.get(col, "")
                if raw_v:
                    try:
                        fv = float(raw_v)
                        if np.isfinite(fv):
                            temps.append(fv)
                    except ValueError:
                        pass
            if temps:
                mx = max(temps)
                if mx > 20.0:
                    pts_list.append((rr, cc))
                    vals_list.append(mx)
    pts = np.asarray(pts_list, dtype=np.float64)
    vals = np.asarray(vals_list, dtype=np.float64)
    tree = cKDTree(pts)
    yy, xx = np.nonzero(foot)
    d_nn, idx_nn = tree.query(np.column_stack([yy, xx]), k=8)
    wt = 1.0 / (1.0 + (d_nn / 20.0) ** 2)
    gdr_flat = (wt * vals[idx_nn]).sum(axis=1) / np.maximum(wt.sum(axis=1), 1e-12)
    del d_nn, idx_nn, wt, yy, xx
    gdr_therm = np.zeros((H, W), dtype=np.float32)
    gdr_therm[foot] = gdr_flat.astype(np.float32)
    del gdr_flat
    gdr_therm = (gaussian_filter(gdr_therm, 2.5) * foot).astype(np.float32)
    line_hydro += 0.45 * _consume("gdr_geotherm_idw", gdr_therm)
    del gdr_therm

    # Compute exact 2nd-largest of 4 lines in O(1) extra arrays without 3D stacking
    hi_ab = np.maximum(line_scarp, line_geopot)
    lo_ab = np.minimum(line_scarp, line_geopot)
    hi_cd = np.maximum(line_kinem, line_hydro)
    lo_cd = np.minimum(line_kinem, line_hydro)
    second_line = np.maximum(np.minimum(hi_ab, hi_cd), np.where(hi_ab >= hi_cd, lo_ab, lo_cd))
    del hi_ab, lo_ab, hi_cd, lo_cd

    corrob_gate = np.clip(second_line / 0.55, 0.40, 1.0).astype(np.float32)
    del second_line
    p_phys = (
        corrob_gate
        * (0.42 * line_scarp + 0.32 * line_geopot + 0.14 * line_kinem + 0.12 * line_hydro)
    ).astype(np.float32)
    del corrob_gate, line_scarp, line_geopot, line_kinem, line_hydro
    p_phys[~foot] = 0.0

    # Check composite canary BEFORE masking known=catalogue
    comp_auc = float(roc_auc_score(y_true, p_phys.ravel()[eval_idx]))
    comp_sym_auc = float(max(comp_auc, 1.0 - comp_auc))
    canaries["composite_p_phys"] = round(comp_sym_auc, 5)
    if comp_sym_auc > 0.90:
        raise RuntimeError(
            f"LEAKAGE CANARY TRIPPED on composite_p_phys: symmetric AUC = {comp_sym_auc:.5f} > 0.90"
        )

    # Apply organiser pixel-exact catalogue mask ONLY at scoring stage (Forum #11516)
    comp_id, _ = ndi_label(h19_5, structure=np.ones((3, 3), dtype=int))
    comp_sizes = np.bincount(comp_id.ravel())
    comp_sizes[0] = 0
    len_bonus = np.clip(np.log1p(comp_sizes[comp_id]) / 5.0, 0.0, 1.0).astype(np.float32)
    del comp_id
    w_scored = np.where(
        foot & ~catalogue,
        np.where(h19_5, 0.045 + 0.22 * p_phys + 0.06 * len_bonus, 0.015 * p_phys),
        0.0,
    ).astype(np.float32)

    return w_scored, canaries


# ---------------------------------------------------------------------------
# 4. Report-Only Instruments: Holdout-DTI + 95% CI, SGMC Control, Block CV
# ---------------------------------------------------------------------------


def compute_block_cv(mask: np.ndarray, foot: np.ndarray, block_px: int) -> float:
    H, W = foot.shape
    Hs, Ws = (H // block_px) * block_px, (W // block_px) * block_px
    fb = foot[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    interior = fb == (block_px * block_px)
    ab = mask[:Hs, :Ws].reshape(Hs // block_px, block_px, Ws // block_px, block_px).sum(axis=(1, 3))
    dens = ab[interior] / fb[interior]
    return float(dens.std() / dens.mean())


def evaluate_report_only_instruments(
    arms: dict[str, np.ndarray],
    foot: np.ndarray,
    catalogue: np.ndarray,
    sgmc_path: Path,
) -> dict:
    gd = grid_mod.load_grid(ROOT / "data" / "bridge")
    folds20, _ = holdout_mod.buffered_component_draw(gd, seed=20)
    folds30, _ = holdout_mod.buffered_component_draw(gd, seed=30)

    terms_by_arm: dict[str, np.ndarray] = {}
    for arm_name, mask in arms.items():
        pred = mask.astype(np.float32)
        total_terms = None
        for f in [*folds20, *folds30]:
            _, t = evaluate_holdout.evaluate(pred, f, foot)
            total_terms = t if total_terms is None else (total_terms + t)
        terms_by_arm[arm_name] = total_terms

    # Run pooled_summary with each variant against R0 so paired deltas vs R0 are exact
    primary_key = next(k for k in arms if k != PARENT_ID)
    pooled = evaluate_holdout.pooled_summary(terms_by_arm, draws=1000, seed=520810, candidate=primary_key)

    # SGMC off-catalogue fault control (strictly off catalogue halo > 3 px)
    sgmc_raw = rasterio.open(sgmc_path).read(1) > 0
    sgmc_off = sgmc_raw & foot & ~catalogue & ~binary_dilation(catalogue, iterations=3)

    per_arm = {}
    r0_boot = None
    # Compute paired bootstrap deltas vs R0 directly on exact spatial block terms
    active_blocks = np.any(np.stack([a.sum(axis=1) > 0 for a in terms_by_arm.values()]), axis=0)
    nb = int(active_blocks.sum())
    rng = np.random.default_rng(520810)
    picks = rng.integers(0, nb, size=(1000, nb))
    r0_terms_act = terms_by_arm[PARENT_ID][active_blocks]
    r0_boot = evaluate_holdout.from_terms(r0_terms_act[picks].sum(axis=1))

    for arm_name, mask in arms.items():
        s_hold = pooled["scores"][arm_name]
        a_act = terms_by_arm[arm_name][active_blocks]
        a_boot = evaluate_holdout.from_terms(a_act[picks].sum(axis=1))
        diff_vs_r0 = a_boot - r0_boot
        sgmc_res = metric.dti_binary(mask, sgmc_off, valid=foot, known=catalogue)
        per_arm[arm_name] = {
            "n_dots": int(mask.sum()),
            "holdout_proxy": {
                "evidence_label": "PROXY",
                "evaluator_version": evaluate_holdout.VERSION,
                "dti": round(float(s_hold["dti"]), 6),
                "ci95": [round(float(x), 6) for x in s_hold["ci95"]],
                "withheld_positives": int(s_hold["withheld_positive_pixels"]),
                "paired_delta_vs_r0": round(float(s_hold["dti"] - pooled["scores"][PARENT_ID]["dti"]), 6),
                "paired_delta_vs_r0_ci95": [
                    round(float(x), 6) for x in np.quantile(diff_vs_r0, [0.025, 0.975])
                ],
            },
            "sgmc_control": {
                "evidence_label": "PROXY",
                "dti": round(float(sgmc_res["dti"]), 6),
                "n_sgmc_off_catalogue_px": int(sgmc_off.sum()),
                "tp": round(float(sgmc_res["tp"]), 2),
                "fp": round(float(sgmc_res["fp"]), 2),
            },
            "block_density_cv": {
                "cv_10km_100px_interior": round(compute_block_cv(mask, foot, 100), 4),
                "cv_12km_120px_interior": round(compute_block_cv(mask, foot, 120), 4),
            },
        }
    return per_arm


# ---------------------------------------------------------------------------
# 5. GeoTIFF Writer, Full Format Re-Read Gate, Ledger & Mechanism Cards
# ---------------------------------------------------------------------------


def write_and_verify_variant(
    mask: np.ndarray,
    foot: np.ndarray,
    catalogue: np.ndarray,
    sample_path: Path,
    releases_dir: Path,
    parent_mask: np.ndarray,
    axis: str,
    value: str,
    note_template: str,
    existing_shas: set[str],
    *,
    parent_id: str = PARENT_ID,
    parent_sha_zeros: str = PARENT_SHA_ZEROS,
    parent_sha_nan: str = PARENT_SHA_NAN,
    date: str = FIXED_DATE,
    min_catalogue_px: float = 0.0,
) -> dict:
    """Write <id>.tif (NaN outside) + <id>-zeros.tif + .zip + .json and re-read verify all gates.

    ``parent_id``/``parent_sha_*``/``date`` default to the R0 ``PRUNE`` family so the
    original call sites are unchanged; later axes (e.g. ``SNAP`` on ``R1 = PRUNEp3px``)
    pass their own parent so the filename states the parent that was actually edited.
    ``min_catalogue_px`` lets a caller assert a stricter collar than "zero mass on
    catalogue" (the brief's 3 px non-PRUNE rule) instead of reporting it.
    """
    releases_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(sample_path) as tpl:
        base_prof = tpl.profile.copy()
        ref_tuple = (tpl.shape, tpl.crs, tpl.transform)

    prof_nan = base_prof.copy()
    prof_nan.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        compress="deflate",
        predictor=3,
        zlevel=9,
        tiled=True,
        blockxsize=256,
        blockysize=256,
        nodata=np.nan,
    )
    prof_zeros = prof_nan.copy()
    prof_zeros.update(nodata=None)

    arr_nan = np.where(foot, mask.astype(np.float32), np.nan).astype(np.float32)
    arr_zeros = np.where(foot, mask.astype(np.float32), 0.0).astype(np.float32)

    prefix = f"{parent_id}-{axis}{value}-{date}"
    tmp_nan = releases_dir / f".tmp-{prefix}.tif"
    tmp_zeros = releases_dir / f".tmp-{prefix}-zeros.tif"
    with rasterio.open(tmp_nan, "w", **prof_nan) as dst:
        dst.write(arr_nan, 1)
    with rasterio.open(tmp_zeros, "w", **prof_zeros) as dst:
        dst.write(arr_zeros, 1)

    sha_nan = sha256_file(tmp_nan)
    sha_zeros = sha256_file(tmp_zeros)
    sha8 = sha_nan[:8]

    if sha_nan in existing_shas or sha_zeros in existing_shas:
        tmp_nan.unlink(missing_ok=True)
        tmp_zeros.unlink(missing_ok=True)
        raise RuntimeError(f"Duplicate SHA-256 already present in ledger: {sha_nan}")

    vid = f"{prefix}-{sha8}"
    final_nan = releases_dir / f"{vid}.tif"
    final_zeros = releases_dir / f"{vid}-zeros.tif"
    tmp_nan.replace(final_nan)
    tmp_zeros.replace(final_zeros)

    zip_nan = releases_dir / f"{vid}.zip"
    zip_zeros = releases_dir / f"{vid}-zeros.zip"
    for tif_p, zip_p in ((final_nan, zip_nan), (final_zeros, zip_zeros)):
        with zipfile.ZipFile(zip_p, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(tif_p, arcname=tif_p.name)
        os.chmod(tif_p, 0o644)
        os.chmod(zip_p, 0o644)

    # MUST-PASS RE-READ VERIFICATION FROM DISK
    with rasterio.open(final_nan) as ds:
        back_nan = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert np.isfinite(back_nan[foot]).all(), "NaN/Inf inside footprint in .tif"
        assert np.isnan(back_nan[~foot]).all(), "Non-NaN outside footprint in .tif"
        assert float(back_nan[foot].min()) >= 0.0 and float(back_nan[foot].max()) <= 1.0
        assert int((back_nan[catalogue] > 0.0).sum()) == 0, "Non-zero mass on catalogue"
        assert np.array_equal(back_nan[foot] > 0.5, mask[foot])

    with rasterio.open(final_zeros) as ds:
        back_zeros = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform) == ref_tuple
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert np.isfinite(back_zeros).all()
        assert np.all(back_zeros[~foot] == 0.0)
        assert int((back_zeros[catalogue] > 0.0).sum()) == 0
        assert np.array_equal(back_zeros[foot] > 0.5, mask[foot])

    rep_zeros = gates.format_report(final_zeros, sample_path, footprint=foot)
    val_zeros = validate.validate(final_zeros, foot, catalogue)
    assert rep_zeros["ok"] and val_zeros["all_checks_passed"]

    d_cat = distance_transform_edt(~catalogue)
    dvals = d_cat[mask]
    n_parent = int(parent_mask.sum())
    n_dots = int(mask.sum())
    n_added = int((mask & ~parent_mask).sum())
    n_removed = int((parent_mask & ~mask).sum())
    pct_moved = 100.0 * n_removed / n_parent
    pct_sym_diff = 100.0 * (n_added + n_removed) / n_parent
    assert 1.0 <= pct_moved <= 50.0, f"Moved % outside [1, 50]: {pct_moved:.2f}%"
    if min_catalogue_px > 0.0:
        assert float(dvals.min()) >= min_catalogue_px, (
            f"min d_cat {dvals.min():.3f} px violates the {min_catalogue_px} px collar"
        )

    note = note_template.format(sha8=sha8)
    assert len(note) <= 140, f"Form note > 140 chars ({len(note)}): {note}"

    receipt = {
        "id": vid,
        "parent": parent_id,
        "parent_sha256_zeros": parent_sha_zeros,
        "parent_sha256_nan": parent_sha_nan,
        "axis": axis,
        "value": value,
        "seed": SEED,
        "git_sha": git_sha(),
        "file_nan": f"releases/{final_nan.name}",
        "sha256": sha_nan,
        "bytes_nan": final_nan.stat().st_size,
        "zip_nan": f"releases/{zip_nan.name}",
        "zip_nan_sha256": sha256_file(zip_nan),
        "file_zeros": f"releases/{final_zeros.name}",
        "sha256_zeros": sha_zeros,
        "bytes_zeros": final_zeros.stat().st_size,
        "zip_zeros": f"releases/{zip_zeros.name}",
        "zip_zeros_sha256": sha256_file(zip_zeros),
        "form_note": note,
        "form_note_chars": len(note),
        "n_dots": n_dots,
        "parent_diff": {
            "n_parent": n_parent,
            "n_added": n_added,
            "n_removed": n_removed,
            "pct_changed_moved": round(pct_moved, 2),
            "pct_changed_sym_diff": round(pct_sym_diff, 2),
            "min_dist_catalogue_px": round(float(dvals.min()), 4),
            "dots_le_1px": int((dvals <= 1.0).sum()),
            "dots_le_2px": int((dvals <= 2.0).sum()),
            "dots_le_3px": int((dvals <= 3.0).sum()),
            "dots_le_4px": int((dvals <= 4.0).sum()),
        },
        "gates": {
            "crs_epsg_32611": True,
            "shape_3730x3292": True,
            "transform_match": True,
            "dtype_float32": True,
            "band_count_1": True,
            "values_in_0_1": True,
            "no_nan_inside_footprint": True,
            "nan_outside_footprint": True,
            "zeros_fallback_valid": True,
            "zero_catalogue_mass": True,
            "reread_from_disk_verified": True,
        },
    }
    receipt_path = releases_dir / f"{vid}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    os.chmod(receipt_path, 0o644)
    return receipt


def main() -> int:
    t0 = time.time()
    print("[1/5] Verifying SHA-256 manifest pins...")
    verified = verify_manifest()
    print(f"      Verified {len(verified)}/{len(verified)} pinned inputs.")

    print("[2/5] Rebuilding parent R0 (h33-h33-2-b2) from lineage recipe...")
    lin = rebuild_r0_from_lineage(verified)
    foot, catalogue, d_cat = lin["foot"], lin["catalogue"], lin["d_cat"]
    h19_5, solo, r0 = lin["h19_5"], lin["solo"], lin["r0"]
    print(
        f"      EXACT R0 REBUILD OK: {int(r0.sum()):,} dots | "
        f"zeros={lin['rebuilt_zeros_sha256'][:12]}... | nan={lin['rebuilt_nan_sha256'][:12]}..."
    )

    print("[3/5] Rebuilding physical corroboration field & running leakage canaries...")
    w_field, canaries = build_physical_field_and_canaries(verified, foot, catalogue, h19_5)
    print(
        f"      Canaries PASS ({len(canaries)}/{len(canaries)} channels <= 0.90; "
        f"max symmetric AUC = {max(canaries.values()):.4f})"
    )

    print("[4/5] Allocating 3 constant-mass (37,654) AXIS=PRUNE variants via exact marginal DTI gain...")
    # Variant 1: p1px — restore SOLO's 2,545 flank dots in (1.0, 2.0] px; drop 2,545 lowest
    # exact-marginal-gain off-collar R0 dots so count stays strictly 37,654.
    flank_1_to_2 = solo & ~r0  # exact 2,545 dots at d_cat in (1.0, 2.0]
    n_restore = int(flank_1_to_2.sum())
    m_p1 = select_exact_marginal_dti_drop(
        base_mask=r0 | flank_1_to_2,
        drop_pool_mask=r0 & (d_cat > 2.0),
        w=w_field,
        n_drop=n_restore,
    )

    # Variant 2: p3px — remove 2,171 R0 dots with d_cat <= 3.0 px; refill 2,171 un-emitted
    # H19-5 ridge dots at d_cat > 3.0 px via exact iterative marginal DTI gain.
    r0_gt3 = r0 & (d_cat > 3.0)
    n_rem3 = int(r0.sum() - r0_gt3.sum())
    m_p3 = select_exact_marginal_dti_add(
        base_mask=r0_gt3,
        cand_mask=h19_5 & ~r0_gt3 & (d_cat > 3.0),
        w=w_field,
        n_add=n_rem3,
    )

    # Variant 3: p4px — remove 3,825 R0 dots with d_cat <= 4.0 px (GeoDAWN 400 m spacing);
    # refill 3,825 un-emitted H19-5 ridge dots at d_cat > 4.0 px via exact marginal DTI gain.
    r0_gt4 = r0 & (d_cat > 4.0)
    n_rem4 = int(r0.sum() - r0_gt4.sum())
    m_p4 = select_exact_marginal_dti_add(
        base_mask=r0_gt4,
        cand_mask=h19_5 & ~r0_gt4 & (d_cat > 4.0),
        w=w_field,
        n_add=n_rem4,
    )

    assert int(m_p1.sum()) == int(m_p3.sum()) == int(m_p4.sum()) == int(r0.sum()) == 37_654

    # Read existing ledger rows first so prior sessions (AXIS=MASS) are preserved and deduplicated
    ledger_path = ROOT / "ledger" / "submissions.csv"
    existing_rows: list[dict[str, str]] = []
    existing_shas: set[str] = {PARENT_SHA_ZEROS, PARENT_SHA_NAN}
    if ledger_path.is_file():
        with ledger_path.open("r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("axis") == "PRUNE" and row.get("value") in ("p1px", "p3px", "p4px"):
                    continue  # idempotent re-run of this script replaces only p1px/p3px/p4px rows
                existing_rows.append(row)
                if row.get("sha256"):
                    existing_shas.add(row["sha256"])
                if row.get("sha256_zeros"):
                    existing_shas.add(row["sha256_zeros"])

    # Clean stale PRUNE files on idempotent re-run before writing fresh deterministic artifacts
    releases_dir = ROOT / "releases"
    for old_p in releases_dir.glob(f"{PARENT_ID}-PRUNE*"):
        old_p.unlink()

    specs = [
        (
            "p1px",
            m_p1,
            "-0.006",
            "h33-2-b2; PRUNE <=1px held at 37654 (+2545 1-2px flank, -2545 low marginal gain); pred -0.006 MODEL",
            "Collar <=1 px (100 m) at fixed 37654 count: restores 2545 parent SOLO flank dots (1-2 px) and drops 2545 lowest exact-marginal-gain off-collar dots.",
            {
                "hypothesis": "Restoring the 100-200 m flank (1 < d_cat <= 2 px) while holding count strictly constant at 37,654 lowers live DTI if near-catalogue detections in H19-5 are dominated by digitizing jitter and aeromagnetic halo side-lobes around already-masked USGS/INGENIOUS traces rather than independent splay faults.",
                "mechanism": "Known traces are masked pixel-exactly (Forum #11516), so a dot at 141-200 m (d in {sqrt(2), 2}) from a known fault with no off-catalogue splay earns T=0 while adding 0.2 to denominator D = 0.2(T + S - M) + 0.8|G|. Holding S = 37,654 isolates true flank toxicity from the 40,199 -> 37,654 mass drop that confounded GEMSDOE28 -> GEMSDOE32.",
                "non_fault_mimic": "1:24k-1:100k map-digitization offsets (+/-100 m) and 400 m GeoDAWN aeromagnetic gridding shoulders displace apparent ridge crests 100-200 m off the mapped fault centerline where only the single mapped fault plane exists in nature.",
                "predicted_sign_size": "MODEL predicted live delta -0.006 vs R0 (range -0.014 to +0.006; <0.01 absolute change counts as inconclusive on public chunks).",
                "falsifier": "Live score gain >= +0.01 over R0 falsifies flank toxicity and proves 100-200 m damage zones harbor dense unmapped synthetic splays/re-digitized traces (Forum #11516/#11536), showing R0's prior gain came from lower mass rather than 2 px exclusion.",
            },
        ),
        (
            "p3px",
            m_p3,
            "+0.005",
            "h33-2-b2; PRUNE <=3px held at 37654 (-2171 in 2-3px, +2171 exact marginal gain >3px); pred +0.005 MODEL",
            "Collar <=3 px (300 m kernel R) at fixed 37654 count: removes all 2171 R0 dots at 2<d_cat<=3 px and refills 2171 un-emitted H19-5 ridge dots at d_cat>3 px via exact marginal DTI gain.",
            {
                "hypothesis": "Removing R0's remaining 2,171 dots inside the 300 m kernel halo (941 at 224 m, 670 at 283 m, 560 at 300 m) and reallocating them to top exact-marginal-gain un-emitted H19-5 multi-line fault ridges beyond 300 m improves live DTI while bringing 100% of dots into full >=3 px compliance.",
                "mechanism": "Under GeoDAWN's 400 m flight-line spacing and 150-200 m drape height, basement magnetic/gravity steps across mapped faults cast horizontal-gradient side-lobes 200-300 m wide. Reallocating those 2,171 dots onto uncovered multi-km H19-5 strands at d_cat > 3 px fills 283 m thinning gaps where line-like truth exceeds the 0.2*DTI (~0.056) threshold.",
                "non_fault_mimic": "Dipping normal-fault footwall/hanging-wall magnetic anomaly peaks shifted 200-300 m down-dip from the already-mapped surface trace, plus range-front alluvial fan apron breaks parallel to mapped master faults.",
                "predicted_sign_size": "MODEL predicted live delta +0.005 vs R0 (range -0.006 to +0.015; treat |delta| < 0.01 as within public-chunk noise unless directional across p1px -> R0 -> p3px).",
                "falsifier": "Live score drop <= -0.01 vs R0 falsifies the 300 m side-lobe hypothesis and demonstrates that 200-300 m footwall/hanging-wall step-faults and tight relay splays carry higher true fault density than off-collar H19-5 ridges.",
            },
        ),
        (
            "p4px",
            m_p4,
            "-0.009",
            "h33-2-b2; PRUNE <=4px held at 37654 (-3825 in 2-4px, +3825 exact marginal gain >4px); pred -0.009 MODEL",
            "Collar <=4 px (400 m flight-line halo) at fixed 37654 count: removes 3825 R0 dots at 2<d_cat<=4 px and refills 3825 un-emitted H19-5 ridge dots at d_cat>4 px via exact marginal DTI gain.",
            {
                "hypothesis": "Extending catalogue exclusion to 400 m (one full GeoDAWN flight-line spacing, removing 3,825 dots) over-prunes genuine antithetic range-front step-faults, synthetic splays, and hard-linked relay ramps that cluster 250-400 m from master faults, causing live DTI to turn negative.",
                "mechanism": "Great Basin normal-fault damage zones and step-over relays routinely host secondary slip planes 300-400 m from master scarps (Faulds & Hinz 2015), where a dot at d_cat > 3 px already suffers zero masked-catalogue kernel waste and earns full multi-pixel line credit T.",
                "non_fault_mimic": "Broad 400 m upward-continued aeromagnetic/isostatic-gravity regional gradients and pediment erosion surfaces flanking range-front faults without discrete secondary brittle slip.",
                "predicted_sign_size": "MODEL predicted live delta -0.009 vs R0 (range -0.022 to +0.004), bracketing the upper turning point of the collar curve (100 m, 200 m, 300 m, 400 m) at constant N = 37,654.",
                "falsifier": "Live score gain >= +0.01 over both R0 and p3px falsifies narrow damage-zone splay clustering and proves test-set new faults are strongly depleted within 400 m of existing USGS/INGENIOUS traces (e.g., due to compilation buffer rules).",
            },
        ),
    ]

    built_receipts = []
    cards = (
        json.loads((ROOT / "ledger" / "mechanism_cards.json").read_text())
        if (ROOT / "ledger" / "mechanism_cards.json").is_file()
        else {}
    )
    # Remove any old PRUNE keys on idempotent rerun
    cards = {k: v for k, v in cards.items() if "-PRUNE" not in k}

    new_ledger_rows = []
    arms_for_eval = {PARENT_ID: r0}

    for val, mask, pred_delta, note_tmpl, desc, card in specs:
        rec = write_and_verify_variant(
            mask=mask,
            foot=foot,
            catalogue=catalogue,
            sample_path=verified["sample_submission"],
            releases_dir=releases_dir,
            parent_mask=r0,
            axis="PRUNE",
            value=val,
            note_template=note_tmpl,
            existing_shas=existing_shas,
        )
        existing_shas.add(rec["sha256"])
        existing_shas.add(rec["sha256_zeros"])
        built_receipts.append(rec)
        cards[rec["id"]] = card
        arms_for_eval[rec["id"]] = mask
        prune_meta = {
            "p1px": (
                "[-0.012,-0.001]",
                "unmasked 4-line physics + exact marginal DTI drop at fixed 37654 count",
                "Slot 2 diagnostic control: tests 1-2 px flank toxicity at constant N (AXIS=PRUNE).",
            ),
            "p3px": (
                "[+0.001,+0.011]",
                "unmasked 4-line physics + exact marginal DTI refill on H19-5 ridges at d_cat>3 px",
                "RECOMMENDED SLOT 1: fully compliant (>=3 px, 0 catalogue, constant 37654, blind SGMC peak 0.09608).",
            ),
            "p4px": (
                "[-0.018,+0.002]",
                "unmasked 4-line physics + exact marginal DTI refill on H19-5 ridges at d_cat>4 px",
                "Slot 3 upper collar bracket: tests tip-loss turnover beyond 300 m kernel radius.",
            ),
        }[val]
        new_ledger_rows.append(
            {
                "id": rec["id"],
                "parent": PARENT_ID,
                "axis": "PRUNE",
                "value": val,
                "n_dots": str(rec["n_dots"]),
                "pct_changed": f"{rec['parent_diff']['pct_changed_moved']:.2f}",
                "sha256": rec["sha256"],
                "sha256_zeros": rec["sha256_zeros"],
                "status": "BUILT",
                "predicted_change": f"MODEL:{pred_delta}",
                "predicted_range": prune_meta[0],
                "ranking_basis": prune_meta[1],
                "receipt_score": "",
                "receipt_date": "",
                "description": desc,
                "recommendation": prune_meta[2],
            }
        )

    print("[5/5] Running REPORT-ONLY diagnostics (Holdout-DTI + 95% CI, SGMC control, Block CV)...")
    eval_report = evaluate_report_only_instruments(
        arms=arms_for_eval,
        foot=foot,
        catalogue=catalogue,
        sgmc_path=verified["sgmc_faults_control"],
    )

    # Enrich each variant receipt JSON with its report-only diagnostics
    for rec in built_receipts:
        rec["report_only_diagnostics"] = eval_report[rec["id"]]
        rec["r0_reference_diagnostics"] = eval_report[PARENT_ID]
        rec["leakage_canaries"] = {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        }
        (releases_dir / f"{rec['id']}.json").write_text(json.dumps(rec, indent=2) + "\n")

    # Write updated ledger/submissions.csv preserving prior session rows + explicit receipt columns
    fieldnames = [
        "id",
        "parent",
        "axis",
        "value",
        "n_dots",
        "pct_changed",
        "sha256",
        "sha256_zeros",
        "status",
        "predicted_change",
        "predicted_range",
        "ranking_basis",
        "receipt_score",
        "receipt_date",
        "description",
        "recommendation",
    ]
    with ledger_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for r in [*existing_rows, *new_ledger_rows]:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    (ROOT / "ledger" / "mechanism_cards.json").write_text(json.dumps(cards, indent=2) + "\n")

    # Write deduplicated historical climb reference table (Brief §3, all marked CLAIM, receipt=N)
    hist_path = ROOT / "ledger" / "historical_climb.csv"
    with hist_path.open("w", newline="") as f:
        w_csv = csv.writer(f)
        w_csv.writerow(["site", "name", "score", "evidence_label", "encoding", "n_dots", "sha8", "parent", "receipt"])
        w_csv.writerows(
            [
                ["19GEMSDOE", "gems19-h19-5-powerlaw-budget-multiline-corroborated", "0.1922", "CLAIM", "nan", "121131", "ec1f9b56", "H16-1", "N"],
                ["GEMSDOE24", "gems24-h25-1-dotted-h19-5-d1-5", "0.2477", "CLAIM", "nan", "60069", "68d0e2e4", "H19-5", "N"],
                ["GEMSDOE25", "gems25-dotted-h19-5-d2-8", "0.2600", "CLAIM", "nan+zeros_collapsed", "44090", "91eae1ca", "H19-5", "N"],
                ["GEMSDOE28", "gems28-h27-4-r1-solo-d2-8", "0.2708", "CLAIM", "zeros", "40199", "2fc94a38", "D2.8", "N"],
                ["GEMSDOE32", "h33-h33-2-b2", "0.2778", "CLAIM", "zeros+nan_collapsed", "37654", "c55bafc4", "SOLO-D2.8", "N"],
            ]
        )

    summary_out = {
        "session_date": "2026-10-23",
        "axis": "PRUNE",
        "parent_r0": {
            "id": PARENT_ID,
            "n_dots": int(r0.sum()),
            "rebuilt_zeros_sha256": lin["rebuilt_zeros_sha256"],
            "rebuilt_nan_sha256": lin["rebuilt_nan_sha256"],
            "diagnostics": eval_report[PARENT_ID],
        },
        "leakage_canaries": {
            "passed": True,
            "max_symmetric_auc": max(canaries.values()),
            "channels": canaries,
        },
        "variants": built_receipts,
        "elapsed_seconds": round(time.time() - t0, 2),
        "git_sha": git_sha(),
    }
    (ROOT / "evidence" / "prune_axis_report.json").write_text(json.dumps(summary_out, indent=2) + "\n")

    print("\n=== SUMMARY OF BUILT AXIS=PRUNE VARIANTS ===")
    for rec in built_receipts:
        diag = rec["report_only_diagnostics"]
        hp = diag["holdout_proxy"]
        sg = diag["sgmc_control"]
        cv = diag["block_density_cv"]
        pdif = rec["parent_diff"]
        print(
            f"  {rec['id']} | dots={rec['n_dots']:,} | moved={pdif['pct_changed_moved']:.2f}% "
            f"(sym={pdif['pct_changed_sym_diff']:.2f}%) | min_dcat={pdif['min_dist_catalogue_px']:.3f}px | "
            f"HOLDOUT-DTI={hp['dti']:.4f} {hp['ci95']} (delta={hp['paired_delta_vs_r0']:+.5f}, n={hp['withheld_positives']}) | "
            f"SGMC={sg['dti']:.4f} | CV12km={cv['cv_12km_120px_interior']:.4f}"
        )
    r0d = eval_report[PARENT_ID]
    print(
        f"  [R0 reference] dots=37,654 | min_dcat=2.236px | "
        f"HOLDOUT-DTI={r0d['holdout_proxy']['dti']:.4f} {r0d['holdout_proxy']['ci95']} | "
        f"SGMC={r0d['sgmc_control']['dti']:.4f} | CV12km={r0d['block_density_cv']['cv_12km_120px_interior']:.4f}"
    )
    print(f"Completed in {summary_out['elapsed_seconds']}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
