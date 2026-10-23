"""Km-scale priors derived deterministically from a pinned point catalogue.

Only one independent, licence-clean prior exists in this repository: the USGS/DOE
Geothermal Data Repository (GDR) well and spring inventory (`gdr_wellspring_in_footprint`,
public domain, pinned in `registry/data_manifest.json`).  Vents and springs are **not**
fault truth (manifest role: "prior layer only"): they mark fluid pathways that are
structurally controlled, which is why the brief allows them "only as a prior on
fault-interaction zones".

Design rules encoded here, each of which removes a degree of freedom from the session:

1. **Points, not records.**  The CSV has 27,092 rows but only 12,570 distinct grid cells
   (one well is repeated 52 times for its 52 measurements).  Counting rows would make the
   prior a map of *measurement effort*, so features are de-duplicated to one per cell.
2. **Thermal features only.**  `thermalclass` in {Hot, Warm}. Cold/NULL records are
   ordinary water wells and do not mark a thermal pathway.
3. **Distance transform, fixed scale.**  `prior = exp(-d / SIGMA_PX)`, d = Euclidean
   distance in cells to the nearest kept feature.  Distinct values everywhere (no ties
   for a block ranking to fall through), interpretable, and one knob (SIGMA_PX = 12 px
   = 1.2 km, the step-over/intersection length scale the Faulds inventory discusses).
4. **No label probing.**  Nothing here reads the withheld truth.  The only catalogue use
   is the *optional* `remote_min_px` filter, which keeps features further than N cells
   from the mapped traces - i.e. it deliberately asks "what do thermal features know
   that the map does not?" - and it is computed from the pinned catalogue raster that
   every gate already reads.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import numpy as np
from scipy import ndimage

SIGMA_PX = 12.0          # 1.2 km exponential decay length
THERMAL_CLASSES = ("Hot", "Warm")
REMOTE_MIN_PX = 8.0      # "not on a mapped trace" for the remote prior


def read_features(csv_path: str | Path) -> dict:
    """Parse the GDR inventory into de-duplicated thermal-feature cells.

    Returns {"cells": (N,2) int array of (row,col), "n_rows": int, "n_cells": int,
             "n_thermal_rows": int}.  Pure: no grid, no truth, no network.
    """
    rows = 0
    thermal = 0
    cells: set[tuple[int, int]] = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        for rec in csv.DictReader(fh):
            rows += 1
            cls = {c.strip() for c in (rec.get("thermalclass") or "").split(",")}
            if not (cls & set(THERMAL_CLASSES)):
                continue
            thermal += 1
            try:
                r, c = int(float(rec["row"])), int(float(rec["col"]))
            except (KeyError, TypeError, ValueError):
                continue
            cells.add((r, c))
    arr = np.array(sorted(cells), dtype=np.int64).reshape(-1, 2)
    return {"cells": arr, "n_rows": rows, "n_cells": int(arr.shape[0]),
            "n_thermal_rows": thermal}


def keep_remote(cells: np.ndarray, catalogue_dist: np.ndarray, min_px: float = REMOTE_MIN_PX) -> np.ndarray:
    """Keep only cells further than `min_px` from the mapped catalogue."""
    r = cells[:, 0]
    c = cells[:, 1]
    return cells[catalogue_dist[r, c] > float(min_px)]


def distance_prior(shape: tuple[int, int], cells: np.ndarray, footprint: np.ndarray,
                   sigma_px: float = SIGMA_PX) -> np.ndarray:
    """exp(-d/sigma) where d = distance (px) to the nearest feature cell; NaN outside footprint."""
    feats = np.zeros(shape, dtype=bool)
    if cells.size:
        ok = (cells[:, 0] >= 0) & (cells[:, 0] < shape[0]) & \
             (cells[:, 1] >= 0) & (cells[:, 1] < shape[1])
        feats[cells[ok, 0], cells[ok, 1]] = True
    if not feats.any():
        raise ValueError("no feature cells inside the grid: prior undefined")
    d = ndimage.distance_transform_edt(~feats)
    prior = np.exp(-d / float(sigma_px)).astype(np.float32)
    prior[~footprint] = np.nan
    return prior


def array_digest(arr: np.ndarray) -> str:
    """sha256 of the float32 payload (+ shape), so a derived prior can be pinned by hash."""
    a = np.ascontiguousarray(np.asarray(arr, dtype=np.float32))
    h = hashlib.sha256()
    h.update(str(a.shape).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def diagnostics(cells: np.ndarray, catalogue_dist: np.ndarray, footprint: np.ndarray,
                catalogue: np.ndarray) -> dict:
    """How much of this prior is really a re-encoding of the mapped catalogue?"""
    if cells.size == 0:
        return {"n_cells": 0}
    r, c = cells[:, 0], cells[:, 1]
    inside = footprint[r, c]
    d = catalogue_dist[r, c]
    return {
        "n_cells": int(cells.shape[0]),
        "n_cells_in_footprint": int(inside.sum()),
        "frac_le_3px_of_catalogue": round(float((d <= 3.0).mean()), 4),
        "frac_gt_8px_of_catalogue": round(float((d > 8.0).mean()), 4),
        "frac_gt_15px_of_catalogue": round(float((d > 15.0).mean()), 4),
        "median_dist_catalogue_px": round(float(np.median(d)), 3),
        "cells_on_catalogue": int((catalogue[r, c]).sum()),
    }


def write_csv_text(text: str, path: Path) -> None:  # pragma: no cover - test helper only
    Path(path).write_text(text, encoding="utf-8")


def parse_text(text: str) -> dict:  # pragma: no cover - convenience for tests
    """`read_features` on an in-memory CSV body (tests only)."""
    tmp = Path("/tmp/_gems91_prior_snippet.csv")
    tmp.write_text(text, encoding="utf-8")
    try:
        return read_features(tmp)
    finally:
        tmp.unlink(missing_ok=True)


__all__ = ["SIGMA_PX", "THERMAL_CLASSES", "REMOTE_MIN_PX", "read_features", "keep_remote",
           "distance_prior", "array_digest", "diagnostics"]
