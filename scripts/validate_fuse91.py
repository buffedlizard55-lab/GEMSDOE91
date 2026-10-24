#!/usr/bin/env python3
"""Independent multi-suite validation of the FUSE91 written bytes.

Re-reads the candidate from disk (never the in-memory array) and runs:
  1. scripts/validate_raster.py  (repo MUST gates, zeros-outside mode)
  2. vendor/gems57/validate.py   (shared template validator)
  3. gems91.release_gates        (session-3 release gates)
  4. raw byte checks: sha256, dot digest, single-TIFF ZIP roundtrip,
     value set, nodata tag, catalogue distance of every dot.
Writes evidence/fuse91_validation_20261024.json. Exit 0 iff all pass.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import validate_raster as vr  # noqa: E402
from gems91 import io as GIO  # noqa: E402
from gems91.release_gates import validate_release  # noqa: E402
from vendor.gems57.validate import assert_submittable, validate as v57  # noqa: E402

CAND = ROOT / "docs/downloads/gems91-fuse91-e1-37654dots-20261024T184241Z-730f6bda-zeros.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
PARENT = ROOT / "docs/downloads/gems91-denovo-hgbctx-37654dots-s2.8-20261024-7941b7ab-zeros.tif"


def read1(p: Path) -> np.ndarray:
    with rasterio.open(p) as s:
        return s.read(1)


def main() -> int:
    audit = json.loads((ROOT / "evidence/fuse91_build_20261024.json").read_text())
    fp = np.isfinite(read1(SAMPLE))
    cat_arr = read1(CAT)
    cat = cat_arr > 0
    a = read1(CAND)
    dots = a > 0
    dcat = ndi.distance_transform_edt(~cat)

    zpath = CAND.with_suffix(".zip")
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        inner_ok = names == [CAND.name] and z.read(CAND.name) == CAND.read_bytes()

    rep = vr.validate_raster(CAND, SAMPLE, catalogue=CAT,
                             ledger_csv=ROOT / "ledger/submissions.csv",
                             parent=PARENT, allow_zeros_outside=True)
    vendor = v57(str(CAND), fp, cat)
    try:
        assert_submittable(vendor)
        vendor_assert = True
    except AssertionError:
        vendor_assert = False
    rel = validate_release(CAND, template=SAMPLE, catalogue=cat_arr,
                           ledger=ROOT / "ledger/submissions.csv",
                           encoding="zeros", expect_dots=37654)

    with rasterio.open(CAND) as ds:
        meta = {"crs": str(ds.crs), "nodata": ds.nodata, "count": ds.count,
                "dtype": ds.dtypes[0], "shape": [ds.height, ds.width],
                "transform": list(tuple(ds.transform)[:6])}

    raw = {
        "sha256": GIO.sha256_file(CAND),
        "sha256_matches_audit": GIO.sha256_file(CAND) == audit["raster_sha256_RECEIPT"],
        "bytes": CAND.stat().st_size,
        "dot_digest_recomputed": GIO.dot_digest(dots),
        "dot_digest_matches_audit": GIO.dot_digest(dots) == audit["dot_set_digest"],
        "meta": meta,
        "min": float(a.min()), "max": float(a.max()),
        "n_nan": int(np.isnan(a).sum()), "n_inf": int(np.isinf(a).sum()),
        "unique_values": [float(x) for x in np.unique(a)],
        "n_dots": int(dots.sum()),
        "dots_on_catalogue": int((dots & cat).sum()),
        "min_catalogue_distance_px": round(float(dcat[dots].min()), 4),
        "dots_outside_footprint": int((dots & ~fp).sum()),
        "zip_single_tiff_inner_identical": bool(inner_ok),
        "portal_range_error_possible": bool(not (a.min() >= 0 and a.max() <= 1
                                                 and np.isfinite(a).all() and meta["nodata"] is None)),
    }
    suites = {
        "validate_raster_py": {"ok": bool(rep.ok), "text": rep.text()},
        "vendor_gems57_validate": {"all_checks_passed": bool(vendor["all_checks_passed"]),
                                   "assert_submittable": vendor_assert,
                                   "checks": vendor["checks"]},
        "gems91_release_gates": rel,
    }
    all_pass = bool(rep.ok and vendor["all_checks_passed"] and vendor_assert
                    and rel.get("PASS") and raw["sha256_matches_audit"]
                    and raw["dot_digest_matches_audit"] and inner_ok
                    and raw["n_nan"] == 0 and raw["n_inf"] == 0
                    and raw["dots_on_catalogue"] == 0 and raw["dots_outside_footprint"] == 0
                    and not raw["portal_range_error_possible"])
    out = {"candidate": str(CAND.relative_to(ROOT)), "all_format_suites_pass": all_pass,
           "raw_byte_checks_RECEIPT": raw, "suites": suites,
           "note": "Format/range validity only. Novelty and holdout gates are recorded in "
                   "evidence/fuse91_build_20261024.json and docs/run-card-F91.json."}
    p = ROOT / "evidence/fuse91_validation_20261024.json"
    p.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"all_format_suites_pass={all_pass}")
    print(rep.text())
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
