"""S28-VFCD: vent-field (GDR) and cross-lineage consensus features.

Lane H1/H2 of docs/HYPOTHESES_S28_VFCD.md; formulas frozen in
docs/s28-vfcd/preregistration.md.  New-in-repo detector features derived from the
pinned GDR well/spring geochemistry CSV (registry id ``gdr_wellspring_in_footprint``)
and the pinned anc lineage rasters.  The GDR file was previously only used as a 1 km
block prior (``gems91.prior``) for dot reallocation; nothing here reads its
catalogue-derived column ``dist_known_fault_px``.

Hide-and-recover safety: catalogue-linked features are computed PER FOLD from the
caller's ``visible`` catalogue only (protocol Rule 2: catalogue-derived features come
from visible faults, never the withheld truth).  The CSV reader only touches physical
columns (row/col, temperature, geothermometer chemistry, thermal class).

Named non-fault mimics (documented, not removed): groundwater discharge on permeable
ash-flow tuffs / carbonate contact karst; basin-margin fan springs; duplicate GDR well
pads (de-duplicated here by pixel cell).
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree

VENT_BASE_NAMES: tuple[str, ...] = (
    "vf_hot_kernel",
    "vf_warm_kernel",
    "vf_geotherm_kernel",
    "vf_hot_dist",
    "vf_hight_dist",
    "vf_seg_hot_density",
    "vf_seg_hight_density",
    "vf_seg_geot_density",
)

VENT_LINKED_NAMES: tuple[str, ...] = (
    "vf_hot_kernel_offcat",
    "vf_seg_offcat_density",
    "vf_sgmc_off_kernel",
    "vf_sgmc_off_x_discharge",
)

VENT_FEATURE_NAMES: tuple[str, ...] = VENT_BASE_NAMES + VENT_LINKED_NAMES

CONS_FEATURE_NAMES: tuple[str, ...] = (
    "cf_h195_rank",
    "cf_multi_rank",
    "cf_anc_count_p85",
)

SIGMA_HOT_PX = 12.0
SIGMA_WARM_PX = 25.0
SIGMA_GEOT_PX = 12.0
SIGMA_SGMC_PX = 8.0
SEG_MAX_LEN_PX = 40.0
SEG_KNN = 3
OFFCAT_PX = 8.0
HIGHT_TEMP_C = 100.0
HIGHT_GEOT_C = 150.0


def load_vent_cells(csv_path: str | Path) -> dict:
    """De-duplicate the GDR records by pixel cell; physical columns only."""
    cells: dict[tuple[int, int], dict] = {}
    with Path(csv_path).open(newline="") as fh:
        for rec in csv.DictReader(fh):
            try:
                row = int(rec["row"])
                col = int(rec["col"])
            except (TypeError, ValueError, KeyError):
                continue
            tc = (rec.get("temp_c") or "").strip()
            try:
                t = float(tc) if tc else None
            except ValueError:
                t = None
            geos = []
            for key in ("geothermquartz_c", "geothermchalc_c", "geothermcat_c"):
                raw = (rec.get(key) or "").strip()
                if raw:
                    try:
                        geos.append(float(raw))
                    except ValueError:
                        pass
            geo = max(geos) if geos else None
            cls = (rec.get("thermalclass") or "").strip().lower()
            cell = cells.setdefault(
                (row, col), {"t_max": None, "geo_max": None, "hot": False, "warm": False}
            )
            if t is not None:
                cell["t_max"] = t if cell["t_max"] is None else max(cell["t_max"], t)
            if geo is not None:
                cell["geo_max"] = geo if cell["geo_max"] is None else max(cell["geo_max"], geo)
            if cls == "hot" or (t is not None and t >= 60.0):
                cell["hot"] = True
            if cls == "warm" or (t is not None and 30.0 <= t < 60.0):
                cell["warm"] = True

    rows, cols, w_hot, w_geot, is_hot, is_warm, is_hight = [], [], [], [], [], [], []
    for (row, col), cell in sorted(cells.items()):
        t = cell["t_max"]
        geo = cell["geo_max"]
        t_eff = max([v for v in (t, geo) if v is not None], default=60.0)
        rows.append(row)
        cols.append(col)
        w_hot.append(0.5 + 0.5 * min(max(t_eff - 60.0, 0.0), 140.0) / 140.0)
        w_geot.append(
            (0.5 + 0.5 * min(max(geo, 0.0), 250.0) / 250.0) if geo is not None else 0.0
        )
        is_hot.append(bool(cell["hot"]))
        is_warm.append(bool(cell["warm"]))
        is_hight.append(
            (t is not None and t >= HIGHT_TEMP_C) or (geo is not None and geo >= HIGHT_GEOT_C)
        )
    return {
        "rows": np.asarray(rows, np.int64),
        "cols": np.asarray(cols, np.int64),
        "w_hot": np.asarray(w_hot, np.float64),
        "w_geot": np.asarray(w_geot, np.float64),
        "is_hot": np.asarray(is_hot, bool),
        "is_warm": np.asarray(is_warm, bool),
        "is_hight": np.asarray(is_hight, bool),
    }


def _exp_kernel(sigma: float, truncate: float = 4.0) -> np.ndarray:
    r = int(np.ceil(truncate * sigma))
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    d = np.hypot(yy, xx)
    k = np.exp(-d / sigma)
    k[d > truncate * sigma] = 0.0
    return k.astype(np.float64)


def _spike_grid(shape: tuple[int, int], rows: np.ndarray, cols: np.ndarray, weights: np.ndarray) -> np.ndarray:
    g = np.zeros(shape, np.float64)
    h, w = shape
    keep = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w) & (weights > 0)
    np.add.at(g, (rows[keep], cols[keep]), weights[keep])
    return g


def _kernel_sum(spike: np.ndarray, sigma: float) -> np.ndarray:
    if not spike.any():
        return np.zeros(spike.shape, np.float32)
    out = fftconvolve(spike, _exp_kernel(sigma), mode="same")
    return np.asarray(np.clip(out, 0.0, None), np.float32)


def _segment_density(
    shape: tuple[int, int],
    rows: np.ndarray,
    cols: np.ndarray,
    w: np.ndarray,
    max_len: float = SEG_MAX_LEN_PX,
    knn: int = SEG_KNN,
    keep_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Density of straight vent-to-vent corridor sample points (0.5 px step).

    ``keep_mask`` (bool, (H, W)) optionally drops sample points (used for the
    off-catalogue variant, computed from the fold-visible catalogue).
    """
    dens = np.zeros(shape, np.float64)
    if len(rows) < 2:
        return dens
    pts = np.stack([rows.astype(np.float64), cols.astype(np.float64)], axis=1)
    tree = cKDTree(pts)
    k = min(knn + 1, len(pts))
    dists, idxs = tree.query(pts, k=k)
    seen: set[tuple[int, int]] = set()
    h, w_shape = shape
    for i in range(len(pts)):
        for j_slot in range(1, k):
            j = int(idxs[i, j_slot])
            if j == i or not np.isfinite(dists[i, j_slot]) or dists[i, j_slot] > max_len:
                continue
            key = (min(i, j), max(i, j))
            if key in seen:
                continue
            seen.add(key)
            y0, x0 = pts[i]
            y1, x1 = pts[j]
            n_steps = max(int(np.hypot(y1 - y0, x1 - x0) * 2.0), 1)
            ts = np.linspace(0.0, 1.0, n_steps + 1)
            ys = np.rint(y0 + (y1 - y0) * ts).astype(np.int64)
            xs = np.rint(x0 + (x1 - x0) * ts).astype(np.int64)
            ok = (ys >= 0) & (ys < h) & (xs >= 0) & (xs < w_shape)
            if keep_mask is not None:
                ok &= keep_mask[ys, xs]
            np.add.at(dens, (ys[ok], xs[ok]), 0.5 * (w[i] + w[j]))
    return dens


def _min_dist_grid(shape: tuple[int, int], rows: np.ndarray, cols: np.ndarray, cap: float = 50.0) -> np.ndarray:
    spike = np.zeros(shape, bool)
    if len(rows):
        spike[rows, cols] = True
    if not spike.any():
        return np.full(shape, cap, np.float32)
    d = ndi.distance_transform_edt(~spike)
    return np.minimum(d, cap).astype(np.float32)


def compute_vent_base_features(csv_path: str | Path, shape: tuple[int, int]) -> tuple[dict[str, np.ndarray], dict]:
    """Catalogue-free VENT features T1-T8 (float32 (H, W))."""
    cells = load_vent_cells(csv_path)
    rows, cols = cells["rows"], cells["cols"]
    hot_sel = cells["is_hot"] | cells["is_warm"]
    geot_sel = cells["w_geot"] > 0

    feats: dict[str, np.ndarray] = {
        "vf_hot_kernel": _kernel_sum(
            _spike_grid(shape, rows[hot_sel], cols[hot_sel], cells["w_hot"][hot_sel]), SIGMA_HOT_PX
        ),
        "vf_warm_kernel": _kernel_sum(
            _spike_grid(shape, rows[hot_sel], cols[hot_sel], np.ones(int(hot_sel.sum()))), SIGMA_WARM_PX
        ),
        "vf_geotherm_kernel": _kernel_sum(
            _spike_grid(shape, rows[geot_sel], cols[geot_sel], cells["w_geot"][geot_sel]), SIGMA_GEOT_PX
        ),
        "vf_hot_dist": _min_dist_grid(shape, rows[hot_sel], cols[hot_sel]),
        "vf_hight_dist": _min_dist_grid(shape, rows[cells["is_hight"]], cols[cells["is_hight"]]),
    }
    receipt = {
        "n_cells": int(len(rows)),
        "n_hot_warm": int(hot_sel.sum()),
        "n_hight": int(cells["is_hight"].sum()),
        "n_geothermometer": int(geot_sel.sum()),
        "columns_read": ["row", "col", "temp_c", "thermalclass", "geothermquartz_c", "geothermchalc_c", "geothermcat_c"],
        "catalogue_columns_read": [],
    }
    # Segment densities (hot / high-T / geothermometer-weighted).
    feats["vf_seg_hot_density"] = np.asarray(
        _segment_density(shape, rows[hot_sel], cols[hot_sel], cells["w_hot"][hot_sel]), np.float32
    )
    feats["vf_seg_hight_density"] = np.asarray(
        _segment_density(shape, rows[cells["is_hight"]], cols[cells["is_hight"]], np.ones(int(cells["is_hight"].sum()))),
        np.float32,
    )
    feats["vf_seg_geot_density"] = np.asarray(
        _segment_density(shape, rows[geot_sel], cols[geot_sel], cells["w_geot"][geot_sel]), np.float32
    )
    receipt["segments"] = {
        "hot": float(feats["vf_seg_hot_density"].max()),
        "hight": float(feats["vf_seg_hight_density"].max()),
        "geot": float(feats["vf_seg_geot_density"].max()),
    }
    return feats, receipt


def compute_vent_linked_features(
    base: dict[str, np.ndarray],
    csv_path: str | Path,
    shape: tuple[int, int],
    visible: np.ndarray,
    sgmc_bool: np.ndarray | None,
) -> dict[str, np.ndarray]:
    """Fold-safe catalogue-linked VENT features T9-T12 from ``visible`` only."""
    vis = np.asarray(visible, bool)
    if vis.shape != tuple(shape):
        raise ValueError("visible shape mismatch")
    d_vis = ndi.distance_transform_edt(~vis) if vis.any() else np.full(shape, np.inf)
    off8 = d_vis > OFFCAT_PX

    cells = load_vent_cells(csv_path)
    rows, cols = cells["rows"], cells["cols"]
    hot_sel = cells["is_hot"] | cells["is_warm"]

    out: dict[str, np.ndarray] = {
        "vf_hot_kernel_offcat": (base["vf_hot_kernel"] * off8).astype(np.float32),
        "vf_seg_offcat_density": np.asarray(
            _segment_density(
                shape,
                rows[hot_sel],
                cols[hot_sel],
                cells["w_hot"][hot_sel],
                keep_mask=off8,
            ),
            np.float32,
        ),
    }
    if sgmc_bool is not None:
        sg = np.asarray(sgmc_bool, bool) & (d_vis > 3.0)
        sg_rows, sg_cols = np.nonzero(sg)
        spike = _spike_grid(shape, sg_rows, sg_cols, np.ones(len(sg_rows)))
        k8 = _kernel_sum(spike, SIGMA_SGMC_PX)
        out["vf_sgmc_off_kernel"] = k8
        warm_max = float(base["vf_warm_kernel"].max()) or 1.0
        out["vf_sgmc_off_x_discharge"] = (k8 * (base["vf_warm_kernel"] / warm_max)).astype(np.float32)
    else:
        out["vf_sgmc_off_kernel"] = np.zeros(shape, np.float32)
        out["vf_sgmc_off_x_discharge"] = np.zeros(shape, np.float32)
    return out


def compute_consensus_features(anc: dict[str, np.ndarray], footprint: np.ndarray) -> dict[str, np.ndarray]:
    """Cross-lineage consensus features cf1-cf3 from the pinned anc rasters."""
    from scipy.stats import rankdata

    fp = np.asarray(footprint, bool)
    shape = fp.shape

    def _rank01(a: np.ndarray) -> np.ndarray:
        v = np.nan_to_num(np.asarray(a, np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        out = np.zeros(shape, np.float32)
        x = v[fp]
        if x.size and np.ptp(x) > 0:
            out[fp] = rankdata(x, method="average").astype(np.float32) / (x.size + 1.0)
        return out

    ranks = {name: _rank01(arr) for name, arr in anc.items()}
    cf1 = ranks.get("anc_h19_5", np.zeros(shape, np.float32))
    pair = [ranks[n] for n in ("anc_h19_4", "anc_h16_1") if n in ranks]
    cf2 = (sum(pair) / len(pair)).astype(np.float32) if pair else np.zeros(shape, np.float32)
    count = np.zeros(shape, np.float32)
    for name, r in ranks.items():
        thr = float(np.quantile(r[fp], 0.85)) if fp.any() else 1.0
        count += (r >= thr).astype(np.float32)
    return {"cf_h195_rank": cf1, "cf_multi_rank": cf2, "cf_anc_count_p85": count}
