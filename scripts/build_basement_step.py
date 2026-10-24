#!/usr/bin/env python3
"""Build the session-10 basement-step ridge candidate (pre-registered E1 configuration).

Writes one single-band float32 GeoTIFF on the official sample grid (EPSG:32611, 3730 x 3292,
100 m, NaN outside the footprint, values in [0, 1]) and a machine-readable run-card stub.
It NEVER submits anything.  Whether the file may be uploaded is decided by the run card's
verdict, not by this script.

Usage:
    python3 scripts/build_basement_step.py            # writes outputs/s10/ (gitignored)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import evaluate_holdout as ev  # noqa: E402  (pin verification + grid loading)
from gems91 import basement  # noqa: E402

PARENT_TAG = "s10-basement"
EXPERIMENT = "E1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def build(out_dir: Path, docs_dir: Path | None, stamp: str) -> dict:
    pins = ev.verify_inputs()
    with rasterio.open(ev.SAMPLE) as ref:
        profile = ref.profile.copy()
        footprint = np.isfinite(ref.read(1))
        transform, crs = ref.transform, ref.crs
    with rasterio.open(ev.CATALOGUE) as s:
        cat = s.read(1) == 1
    with rasterio.open(ev.FEATURES) as s:
        depth = s.read(15).astype(np.float64)

    P = basement.build_candidate(depth, footprint, visible_catalogue=cat, k=basement.K_DEFAULT)
    out = np.where(footprint, P, np.nan).astype(np.float32)
    assert np.all(out[footprint] >= 0) and np.all(out[footprint] <= 1)
    assert not np.any(out[footprint] > 1) and not np.isnan(out[footprint]).any()
    assert np.all(out[footprint & cat] == 0), "catalogue cells must carry zero mass"

    k = basement.K_DEFAULT
    name = f"gems91-s10-basementridge-K{k}-{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f"{name}.tif"
    profile.update(driver="GTiff", dtype="float32", count=1, nodata=np.nan, crs=crs,
                   transform=transform, compress="deflate", tiled=False)
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(out, 1)
    sha = sha256_file(tmp)
    final = out_dir / f"{name}-{sha[:8]}.tif"
    tmp.replace(final)
    if docs_dir is not None:
        docs_dir.mkdir(parents=True, exist_ok=True)
        dl = docs_dir / final.name
        dl.write_bytes(final.read_bytes())
    nonzero = int(np.count_nonzero(out[footprint]))
    result = {
        "file": final.name,
        "sha256": sha,
        "bytes": final.stat().st_size,
        "n_mass_cells": nonzero,
        "pins_verified": pins,
        "parent_tag": PARENT_TAG,
        "experiment": EXPERIMENT,
        "k": k,
        "mass_sum": float(out[footprint].sum(dtype=np.float64)),
        "max_value": float(np.nanmax(out)),
        "min_value": float(np.nanmin(out[footprint])),
    }
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", type=Path, default=ROOT / "outputs" / "s10")
    ap.add_argument("--docs-dir", type=Path, default=None)
    ap.add_argument("--stamp", default=dt.date(2026, 10, 24).strftime("%Y%m%d"))
    args = ap.parse_args(argv)
    res = build(args.out_dir, args.docs_dir, args.stamp)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
