"""Hard gates (brief section 6). A release that fails any of these is not shipped."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
import rasterio

from . import io


def _read_ledger(path: Path) -> dict[str, str]:
    """sha256 -> id, for the session ledger."""
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return {(r.get("sha256") or "").strip(): (r.get("id") or "").strip()
                for r in csv.DictReader(fh) if (r.get("sha256") or "").strip()}


def validate_release(path: str | Path, *, template: str | Path, catalogue: np.ndarray,
                     ledger: str | Path | None = None, encoding: str = "nan",
                     floor_px: float = 2.0, expect_dots: int | None = None,
                     own_id: str | None = None) -> dict:
    """Re-read from disk and check every MUST gate. Returns a report dict."""
    path = Path(path)
    checks: dict[str, object] = {}
    arr = io.read_grid(path)                       # gate: re-read from disk after writing
    dot = io.dot_mask(arr)
    cat = np.nan_to_num(catalogue, nan=0.0) > 0

    with rasterio.open(str(path)) as src, rasterio.open(str(template)) as tpl:
        checks["crs_matches_template"] = str(src.crs) == str(tpl.crs)
        checks["shape_matches_template"] = (src.height, src.width) == (tpl.height, tpl.width)
        checks["transform_matches_template"] = tuple(src.transform)[:6] == tuple(tpl.transform)[:6]
        checks["single_band"] = src.count == 1 == tpl.count
        checks["dtype_float32"] = src.dtypes[0] == "float32"
        footprint = np.isfinite(tpl.read(1))

    finite = np.isfinite(arr)
    inside = arr[footprint]
    checks["no_nan_inside_footprint"] = bool(np.isfinite(inside).all())
    if encoding == "nan":
        checks["nan_outside_footprint"] = bool((~finite & ~footprint).sum() == (~footprint).sum())
    else:
        checks["zeros_outside_footprint"] = bool(
            ((arr == 0) | ~finite)[~footprint].all())
    vals = arr[finite]
    checks["values_within_0_1"] = bool(vals.size and vals.min() >= 0.0 and vals.max() <= 1.0)
    checks["unit_mass_dots"] = bool(set(np.unique(vals)) <= {0.0, 1.0})
    checks["zero_catalogue_mass"] = bool((dot & cat).sum() == 0)

    from scipy import ndimage as ndi
    dcat = ndi.distance_transform_edt(~cat)
    checks["min_catalogue_distance_px"] = float(dcat[dot].min()) if dot.any() else None
    checks["catalogue_floor_respected"] = bool(dcat[dot].min() > floor_px)

    sha = io.sha256_file(path)
    checks["sha256"] = sha
    checks["dot_set_digest"] = io.dot_digest(dot)
    checks["n_dots"] = int(dot.sum())
    if expect_dots is not None:
        checks["count_matches_parent"] = checks["n_dots"] == expect_dots
    if ledger is not None:
        # A NEW build must not reuse a hash already recorded. Re-validating a
        # file that is itself registered under `own_id` is not a duplicate.
        registered = _read_ledger(Path(ledger))
        checks["sha256_not_in_ledger"] = sha not in registered or registered[sha] == (own_id or "")

    must = [k for k, v in checks.items() if isinstance(v, bool)]
    checks["PASS"] = all(checks[k] for k in must)
    checks["failed"] = [k for k in must if not checks[k]]
    return checks


def parent_diff(parent_dots: np.ndarray, child_dots: np.ndarray) -> dict:
    added = int((child_dots & ~parent_dots).sum())
    removed = int((parent_dots & ~child_dots).sum())
    return {
        "n_dots_parent": int(parent_dots.sum()),
        "n_dots_child": int(child_dots.sum()),
        "added": added,
        "removed": removed,
        "changed": added + removed,
        "pct_changed_of_parent": round(100.0 * (added + removed) / max(1, int(parent_dots.sum())), 4),
    }
