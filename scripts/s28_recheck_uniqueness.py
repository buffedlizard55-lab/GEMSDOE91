"""Recompute the S28 candidate's uniqueness block from the bytes on disk.

Run after any change to the set of prior rasters in ``docs/downloads`` or after
deleting a superseded variant, so ``docs/s28/candidate.json`` never reports a
prior that no longer exists (or misses one that does).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
OUT = ROOT / "docs" / "s28"
STOP = 0.70


def main() -> int:
    cand = json.loads((OUT / "candidate.json").read_text())
    tif = ROOT / cand["tif"]
    with rasterio.open(tif) as ds:
        a = ds.read(1)
    yy, xx = np.nonzero(a > 0)
    mine = np.column_stack([yy, xx]).astype(np.float32)

    priors = sorted({p for p in list((ROOT / "docs/downloads").glob("*.tif"))
                     + list((ROOT / "data/nine_site_raster").glob("*.tif"))})
    rows = []
    for p in priors:
        if p.resolve() == tif.resolve():
            continue
        with rasterio.open(p) as ds:
            b = ds.read(1)
        pyy, pxx = np.nonzero(np.asarray(b) > 0)
        if pyy.size == 0:
            continue
        theirs = np.column_stack([pyy, pxx]).astype(np.float32)
        d1 = cKDTree(theirs).query(mine, k=1)[0]
        d2 = cKDTree(mine).query(theirs, k=1)[0]
        rows.append(dict(prior=p.name, mine_within_3px=float((d1 <= 3).mean()),
                         theirs_within_3px=float((d2 <= 3).mean()), prior_dots=int(pyy.size)))
    rows.sort(key=lambda r: -r["mine_within_3px"])
    worst = rows[0]
    cand["uniqueness"] = dict(
        n_priors_compared=len(rows), worst=worst,
        unique_at_70pct=bool(worst["mine_within_3px"] < STOP),
        registry_scope=("local docs/downloads (this repository, after deleting the lane's superseded "
                        "variant) + the nine focus-site rasters; NOT the full fleet"),
        top10=rows[:10])
    (OUT / "candidate.json").write_text(json.dumps(cand, indent=1, default=float))
    print(json.dumps({"n_priors": len(rows), "worst": worst}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
