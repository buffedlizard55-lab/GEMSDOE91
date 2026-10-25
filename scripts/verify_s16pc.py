#!/usr/bin/env python3
"""Independent re-read verification of the S16 delivered TIF (trusts nothing the
writer claimed): sha vs run card, CRS/shape/transform vs pinned sample,
all-finite [0,1], dot count/values, catalogue mass + min distance, ZIP inner
bytes. Writes evidence/s16_independent_check.json; exit 1 on any failure.
"""
from __future__ import annotations
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main() -> int:
    card = json.loads((ROOT / "docs/run-card-S16PC.json").read_text())
    cand = card["submission_name"]
    zp = ROOT / f"docs/downloads/{cand}-zeros.tif"
    checks = {}
    disk_sha = sha(zp)
    checks["sha_disk_equals_run_card"] = bool(disk_sha == card["raster_sha256"])
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as s:
        ref = s.read(1); rcrs, rtr, rshape = str(s.crs), tuple(s.transform)[:6], tuple(s.shape)
    fp = np.isfinite(ref)
    with rasterio.open(zp) as s:
        a = s.read(1)
        checks["crs_match"] = bool(str(s.crs) == rcrs)
        checks["shape_match"] = bool(tuple(s.shape) == rshape)
        checks["transform_match"] = bool(tuple(s.transform)[:6] == rtr)
        checks["dtype_float32"] = bool(s.dtypes[0] == "float32")
        checks["one_band"] = bool(s.count == 1)
        checks["nodata_none"] = bool(s.nodata is None)
    checks["all_cells_finite"] = bool(np.isfinite(a).all())
    checks["values_in_0_1"] = bool(float(a.min()) >= 0.0 and float(a.max()) <= 1.0)
    checks["nan_cells"] = int(np.isnan(a).sum())
    dots = (a > 0) & fp
    checks["n_dots"] = int(dots.sum())
    checks["binary_unit_dots"] = bool(np.array_equal(np.unique(a[a > 0]), np.array([1.0], dtype=a.dtype)))
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as s:
        cat = (np.nan_to_num(s.read(1), nan=0.0) > 0) & fp
    d = ndi.distance_transform_edt(~cat)
    ys, xs = np.nonzero(dots)
    checks["dots_on_catalogue"] = int((dots & cat).sum())
    checks["min_catalogue_distance_px"] = round(float(d[ys, xs].min()), 4)
    zf = zipfile.ZipFile(ROOT / f"docs/downloads/{cand}-zeros.zip")
    names = zf.namelist()
    checks["zip_single_member"] = bool(len(names) == 1)
    checks["zip_inner_sha_match"] = bool(hashlib.sha256(zf.read(names[0])).hexdigest() == disk_sha)
    ok = bool(checks["sha_disk_equals_run_card"] and checks["crs_match"] and checks["shape_match"]
              and checks["transform_match"] and checks["dtype_float32"] and checks["one_band"]
              and checks["nodata_none"] and checks["all_cells_finite"] and checks["values_in_0_1"]
              and checks["nan_cells"] == 0 and checks["dots_on_catalogue"] == 0
              and checks["min_catalogue_distance_px"] > 3.0 and checks["zip_single_member"]
              and checks["zip_inner_sha_match"] and checks["binary_unit_dots"])
    out = {"candidate": cand, "sha256": disk_sha, "checks": checks, "all_pass": ok,
           "verdict": card["verdict"], "ok_to_submit": card["ok_to_submit"]}
    (ROOT / "evidence/s16_independent_check.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
