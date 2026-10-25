#!/usr/bin/env python3
"""S16 forensics: independently re-read every downloadable TIF + pinned registry
raster from disk and measure (no trust in prior JSON claims):
  - portal safety: finite inside footprint, values in [0,1], CRS/shape/transform
    vs pinned sample_submission, dtype, band count, nodata
  - dot geometry: n_dots, value set, catalogue mass, distance-to-catalogue
    percentiles, nearest-neighbour spacing percentiles
  - Rule-1 geometry baselines: 3px-dilation coverage of each raster (the random
    baseline for the <=70% dot-overlap gate)
Writes evidence/s16_forensics.json. Read-only w.r.t. rasters.
"""
from __future__ import annotations
import glob, hashlib, json, sys
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def pct(a, qs=(0, 5, 25, 50, 75, 95, 100)):
    if a.size == 0: return {}
    return {f"p{q}": round(float(np.percentile(a, q)), 3) for q in qs}

def main() -> int:
    sample_p = ROOT / "data/official/sample_submission.tif"
    cat_p = ROOT / "data/official/existing_faults.tif"
    with rasterio.open(sample_p) as s:
        ref_arr = s.read(1); ref_crs = str(s.crs); ref_shape = tuple(s.shape)
        ref_tr = tuple(s.transform)[:6]; ref_dtype = s.dtypes[0]
    footprint = np.isfinite(ref_arr)
    with rasterio.open(cat_p) as s:
        cat = (np.nan_to_num(s.read(1), nan=0.0) > 0) & footprint
    dcat = ndi.distance_transform_edt(~cat)
    out = {"reference": {"crs": ref_crs, "shape": list(ref_shape), "transform": list(ref_tr),
                          "dtype": ref_dtype, "footprint_px": int(footprint.sum()),
                          "catalogue_px": int(cat.sum())},
           "rasters": {}}
    paths = sorted(glob.glob(str(ROOT / "docs/downloads/*.tif"))) + \
            sorted(glob.glob(str(ROOT / "data/registry/*.tif"))) + \
            sorted(glob.glob(str(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif")))
    for ps in paths:
        p = Path(ps); rel = str(p.relative_to(ROOT))
        try:
            with rasterio.open(p) as s:
                a = s.read(1); crs = str(s.crs); shape = tuple(s.shape)
                tr = tuple(s.transform)[:6]; dt = s.dtypes[0]; cnt = s.count; nd = s.nodata
        except Exception as e:
            out["rasters"][rel] = {"error": str(e)}; continue
        rec = {"sha256": sha256_file(p), "bytes": p.stat().st_size, "dtype": dt, "bands": cnt,
               "nodata": (None if nd is None else str(nd)),
               "crs_match": crs == ref_crs, "shape_match": shape == ref_shape,
               "transform_match": all(abs(x - y) <= 1e-9 for x, y in zip(tr, ref_tr))}
        if shape == ref_shape:
            af = a.astype(np.float64)
            inside = af[footprint]; fin = np.isfinite(inside)
            rec["nonfinite_inside"] = int((~fin).sum())
            v = inside[fin]
            rec["min_inside"] = float(v.min()); rec["max_inside"] = float(v.max())
            rec["range_0_1"] = bool(v.min() >= 0.0 and v.max() <= 1.0)
            rec["portal_safe_range"] = bool(rec["range_0_1"] and rec["nonfinite_inside"] == 0)
            dots = (np.nan_to_num(af, nan=0.0) > 0) & footprint
            rec["n_dots"] = int(dots.sum())
            rec["mass"] = round(float(np.nan_to_num(af, nan=0.0)[footprint].sum()), 2)
            rec["dots_on_catalogue"] = int((dots & cat).sum())
            rec["unique_positive_values_n"] = int(np.unique(v[v > 0]).size) if (v > 0).any() else 0
            if dots.any():
                ys, xs = np.nonzero(dots)
                rec["dist_to_catalogue_px"] = pct(dcat[ys, xs])
                if dots.sum() > 1:
                    tree = cKDTree(np.c_[ys, xs])
                    nn, _ = tree.query(np.c_[ys, xs], k=2)
                    rec["nn_spacing_px"] = pct(nn[:, 1])
                dil = ndi.binary_dilation(dots, structure=np.ones((7, 7), bool))  # approx r<=3 bounding; exact via EDT below
                dself = ndi.distance_transform_edt(~dots)
                rec["coverage_le3px_frac_of_footprint"] = round(float(((dself <= 3.0) & footprint).sum()) / float(footprint.sum()), 4)
        out["rasters"][rel] = rec
        print(f"{rel}: dots={rec.get('n_dots')} range01={rec.get('range_0_1')} nonfin_in={rec.get('nonfinite_inside')} oncat={rec.get('dots_on_catalogue')}")
    dest = ROOT / "evidence/s16_forensics.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"wrote {dest}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
