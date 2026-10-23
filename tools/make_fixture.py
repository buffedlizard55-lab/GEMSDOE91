"""Synthetic fixture rasters for testing the gates and the axis builders.

No competition data is used, stored or approximated here. The fixture only mimics
the *format*: float32, one band, EPSG:32611, 100 m pixels, a rectangular footprint,
a plausible dot density, an exclusion buffer and a km-scale prior field.

    python -m tools.make_fixture --out tests/_tmp/fixture [--seed 0]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

CRS = "EPSG:32611"
RES = 100.0
ORIGIN = (500000.0, 4200000.0)
SHAPE = (120, 160)  # rows, cols


def _profile(shape=SHAPE, nodata=None) -> dict:
    return {
        "driver": "GTiff", "height": shape[0], "width": shape[1], "count": 1,
        "dtype": "float32", "crs": CRS,
        "transform": from_origin(ORIGIN[0], ORIGIN[1], RES, RES),
        "nodata": nodata,
    }


def make(out: Path, seed: int = 0, n_dots: int = 900) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    nrow, ncol = SHAPE

    # footprint: rectangle inset by 4 px, so "outside" is unambiguous
    footprint = np.zeros(SHAPE, bool)
    footprint[4:-4, 6:-6] = True

    # two linear catalogue traces (what the exclusion buffer protects)
    catalogue = np.zeros(SHAPE, bool)
    for c in range(ncol):
        r = int(20 + 0.35 * c)
        if 0 <= r < nrow:
            catalogue[r, c] = True
    catalogue[70:95, 100:118] = True

    # km-scale prior: two gradient blocks plus noise (blocks are 50 px = 5 km)
    yy, xx = np.mgrid[0:nrow, 0:ncol]
    prior = 0.5 + 0.4 * np.sin(xx / 22.0) * np.cos(yy / 30.0)
    prior = np.clip(prior + rng.normal(0, 0.05, SHAPE), 0, 1)

    # dots: draw from the prior, keep away from the catalogue and outside the buffer
    from scipy import ndimage

    dist = ndimage.distance_transform_edt(~catalogue)
    ok = footprint & (dist > 3.5)
    w = (prior ** 3) * ok
    flat = rng.choice(np.arange(w.size), size=min(n_dots, int(ok.sum())), replace=False, p=(w / w.sum()).ravel())
    parent = np.full(SHAPE, np.nan, np.float32)
    parent[footprint] = 0.0
    parent.ravel()[flat] = 1.0

    sample = np.full(SHAPE, np.nan, np.float32)  # sample_submission-like: null outside footprint
    sample[footprint] = 0.05

    paths = {}
    for name, band, nodata in [
        ("sample_submission", sample, np.nan),
        ("footprint_mask", footprint.astype(np.float32), None),
        ("catalogue_mask", catalogue.astype(np.float32), None),
        ("prior_kmscale", prior.astype(np.float32), None),
        ("parent_R0", parent, np.nan),
        ("parent_R0-zeros", np.where(footprint, np.nan_to_num(parent, nan=0.0), 0.0).astype(np.float32), 0.0),
        ("truth_holdout", (catalogue & (xx > 90)).astype(np.float32), None),
    ]:
        p = out / f"{name}.tif"
        with rasterio.open(p, "w", **_profile(nodata=nodata)) as ds:
            ds.write(band.astype(np.float32), 1)
        paths[name] = str(p)

    # a deliberately broken candidate: values outside the footprint, mass on the catalogue
    bad = parent.copy()
    bad[0, 0] = 0.5
    bad[catalogue] = 1.0
    p = out / "bad_candidate.tif"
    with rasterio.open(p, "w", **_profile(nodata=np.nan)) as ds:
        ds.write(bad.astype(np.float32), 1)
    paths["bad_candidate"] = str(p)
    return paths


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("tests/_tmp/fixture"))
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-dots", type=int, default=900)
    args = ap.parse_args(argv)
    paths = make(args.out, seed=args.seed, n_dots=args.n_dots)
    for k, v in paths.items():
        print(f"{k:22s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
