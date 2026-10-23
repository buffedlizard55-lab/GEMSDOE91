"""Gate checks for candidate rasters (brief section 6).

Design rule: a gate never silently passes. If an input needed to prove a gate
is missing, the gate is reported as UNVERIFIED and the file is NOT CERTIFIED.
That is deliberate: the previous lineage built 20 candidates and this session
found no way to certify the catalogue collar for 17 of them.
"""

from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import rasterio

# Grid of sample_submission.tif as inherited from the verified parent R0
# (EPSG:32611, 100 m, 3730x3292, origin 243350 / 4508550). This is a PIN, not a
# substitute for the real sample_submission.tif: when that file is present the
# validator compares against it and ignores these numbers.
PINNED_GRID = {
    "crs": "EPSG:32611",
    "height": 3730,
    "width": 3292,
    "res": (100.0, 100.0),
    "left": 243350.0,
    "top": 4508550.0,
    "dtype": "float32",
    "count": 1,
}

COLLAR_PX = 3.0  # brief constraint 4: keep >= 3 px from catalogue


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class GateReport:
    path: str
    sha256: str = ""
    gates: dict[str, str] = field(default_factory=dict)   # gate -> PASS/FAIL/UNVERIFIED
    notes: dict[str, object] = field(default_factory=dict)

    def add(self, name: str, ok: bool | None, note: object = "") -> None:
        self.gates[name] = "PASS" if ok is True else ("FAIL" if ok is False else "UNVERIFIED")
        if note != "":
            self.notes[name] = note

    @property
    def failed(self) -> list[str]:
        return [k for k, v in self.gates.items() if v == "FAIL"]

    @property
    def unverified(self) -> list[str]:
        return [k for k, v in self.gates.items() if v == "UNVERIFIED"]

    @property
    def verdict(self) -> str:
        if self.failed:
            return "NOT CERTIFIED (failed gate)"
        if self.unverified:
            return "NOT CERTIFIED (unverified gate)"
        return "CERTIFIED"

    def to_dict(self) -> dict:
        return {"path": self.path, "sha256": self.sha256, "gates": self.gates,
                "notes": self.notes, "verdict": self.verdict}


def _load(path: str | Path):
    with rasterio.open(path) as src:
        return src.read(1), {
            "crs": str(src.crs),
            "height": src.height,
            "width": src.width,
            "res": (src.res[0], src.res[1]),
            "left": src.transform.c,
            "top": src.transform.f,
            "dtype": src.dtypes[0],
            "count": src.count,
            "nodata": src.nodata,
        }


def _offset_distances(max_px: int):
    span = int(math.ceil(max_px))
    out = []
    for dr in range(-span, span + 1):
        for dc in range(-span, span + 1):
            d = math.hypot(dr, dc)
            if 0 < d <= max_px:
                out.append((dr, dc, d))
    return out


def min_distance_to_mask(mask: np.ndarray, target: np.ndarray, max_px: int = 8) -> np.ndarray:
    """Exact distance (px) from each True cell of `target` to the nearest True cell
    of `mask`, for distances <= max_px; +inf beyond. Exact within the window."""
    if not mask.any():
        raise ValueError("mask is empty (catalogue raster has no foreground)")
    dist = np.where(mask.astype(bool), 0.0, np.inf)
    mm = mask.astype(bool)
    for dr, dc, d in _offset_distances(max_px):
        dist = np.where(_has_neighbour(mm, dr, dc), np.minimum(dist, d), dist)
    # np.nonzero returns (rows, cols) in array-axis order. Naming these "cols, rows"
    # transposed the lookup: it raised IndexError whenever a row index exceeded the
    # array width (the real grid is 3730x3292, so that is a live failure) and
    # otherwise silently returned the distance at the transposed cell - i.e. the
    # collar counts were wrong on every non-square raster.
    rows, cols = np.nonzero(target)
    return dist[rows, cols]


def _has_neighbour(a: np.ndarray, dr: int, dc: int) -> np.ndarray:
    """True where a[r - dr, c - dc] is True (i.e. a True cell at that offset)."""
    h, w = a.shape
    out = np.zeros((h, w), dtype=bool)
    rs_src = slice(max(0, -dr), min(h, h - dr))
    rs_dst = slice(max(0, dr), min(h, h + dr))
    cs_src = slice(max(0, -dc), min(w, w - dc))
    cs_dst = slice(max(0, dc), min(w, w + dc))
    out[rs_dst, cs_dst] = a[rs_src, cs_src]
    return out


def validate(path: str | Path,
             sample_submission: str | Path | None = None,
             catalogue: str | Path | None = None,
             ledger_csv: str | Path | None = None,
             axis: str | None = None,
             reread: bool = True) -> GateReport:
    """Run every MUST gate from brief section 6 that the available inputs allow."""
    path = Path(path)
    rep = GateReport(path=str(path))
    if not path.exists():
        rep.add("file_exists", False)
        return rep
    rep.add("file_exists", True)
    rep.sha256 = sha256_file(path)

    arr, meta = _load(path)

    # --- geometry / format -------------------------------------------------
    ref = dict(PINNED_GRID)
    if sample_submission is not None and Path(sample_submission).exists():
        _, smeta = _load(sample_submission)
        ref.update({k: smeta[k] for k in ("crs", "height", "width", "res", "left", "top")})
        rep.notes["grid_source"] = str(sample_submission)
    else:
        rep.notes["grid_source"] = "PINNED_GRID (sample_submission.tif absent - unpinned)"

    rep.add("crs", meta["crs"] == ref["crs"], meta["crs"])
    rep.add("shape", (meta["height"], meta["width"]) == (ref["height"], ref["width"]),
            f"{meta['height']}x{meta['width']}")
    rep.add("transform", (meta["res"], meta["left"], meta["top"]) ==
            (ref["res"], ref["left"], ref["top"]),
            f"res={meta['res']} left={meta['left']} top={meta['top']}")
    rep.add("dtype", meta["dtype"] == ref["dtype"], meta["dtype"])
    rep.add("band_count", meta["count"] == ref["count"], meta["count"])

    finite = np.isfinite(arr)
    rep.add("values_in_0_1", bool(np.all(arr[finite] >= 0) and np.all(arr[finite] <= 1)),
            f"min={float(arr[finite].min()) if finite.any() else None} "
            f"max={float(arr[finite].max()) if finite.any() else None}")

    # --- footprint ---------------------------------------------------------
    footprint = None
    if sample_submission is not None and Path(sample_submission).exists():
        sm, _ = _load(sample_submission)
        footprint = np.isfinite(sm)
        rep.notes["footprint_source"] = str(sample_submission)
    if footprint is not None:
        inside_nan = bool(np.any(~finite & footprint))
        outside_live = bool(np.any(finite & ~footprint))
        rep.add("no_nan_inside_footprint", not inside_nan, int(np.sum(~finite & footprint)))
        rep.add("nan_outside_footprint", not outside_live, int(np.sum(finite & ~footprint)))
    else:
        rep.add("no_nan_inside_footprint", None, "sample_submission.tif absent")
        rep.add("nan_outside_footprint", None, "sample_submission.tif absent")

    pos = arr > 0
    n_dots = int(pos.sum())
    rep.notes["n_dots"] = n_dots
    rep.notes["positive_values"] = sorted(float(v) for v in np.unique(arr[pos]))[:10]

    # --- catalogue collar (constraint 4) -----------------------------------
    if catalogue is not None and Path(catalogue).exists():
        cat, _ = _load(catalogue)
        catmask = cat > 0
        on_cat = int(np.sum(pos & catmask))
        rep.add("zero_catalogue_mass", on_cat == 0, f"{on_cat} dots on catalogue")
        d = min_distance_to_mask(catmask, pos, max_px=8)
        rep.notes["dots_le_1px"] = int(np.sum(d <= 1.0 + 1e-9))
        rep.notes["dots_le_2px"] = int(np.sum(d <= 2.0 + 1e-9))
        rep.notes["dots_le_3px"] = int(np.sum(d <= 3.0 + 1e-9))
        rep.notes["dots_le_4px"] = int(np.sum(d <= 4.0 + 1e-9))
        rep.notes["min_dist_catalogue_px"] = float(np.min(d)) if d.size else None
        if axis == "PRUNE":
            rep.add("collar_ge_3px", True, "exempt: AXIS=PRUNE")
        else:
            rep.add("collar_ge_3px", rep.notes["dots_le_3px"] == 0,
                    f"{rep.notes['dots_le_3px']} dots within 3 px")
    else:
        rep.add("zero_catalogue_mass", None, "existing_faults.tif absent")
        rep.add("collar_ge_3px", None, "existing_faults.tif absent")

    # --- ledger dedupe -----------------------------------------------------
    if ledger_csv is not None and Path(ledger_csv).exists():
        rows = list(csv.DictReader(open(ledger_csv, newline="", encoding="utf-8")))
        rep.add("sha_unseen", rep.sha256 not in {r.get("sha256", "") for r in rows},
                f"{len(rows)} ledger rows scanned")
        rep.add("sha_unseen_zeros", rep.sha256 not in {r.get("sha256_zeros", "") for r in rows})
    else:
        rep.add("sha_unseen", None, "ledger absent")

    # --- re-read from disk ------------------------------------------------
    if reread:
        arr2, _ = _load(path)
        same = bool(np.array_equal(arr, arr2, equal_nan=True)) and sha256_file(path) == rep.sha256
        rep.add("reread_from_disk", same)
    return rep
