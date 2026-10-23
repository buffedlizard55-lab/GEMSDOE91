#!/usr/bin/env python3
"""Independent offline validation of this session's ledger and local PRUNE TIFFs."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import build_prune_variants as bpv  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    manifest = ROOT / "registry" / "data_manifest.json"
    verified = bpv.verify_manifest(manifest)
    lineage = bpv.rebuild_r0_from_lineage(verified)
    r0 = lineage["r0"]
    foot = lineage["foot"]
    cat = lineage["catalogue"]
    d_cat = distance_transform_edt(~cat)

    ledger_path = ROOT / "ledger" / "submissions.csv"
    with ledger_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1, f"expected one unique variant row, got {len(rows)}"
    row = rows[0]
    assert (row["parent"], row["axis"], row["value"]) == ("h33-h33-2-b2", "PRUNE", "p2p6")
    assert row["status"] == "BUILT" and row["receipt_score"] == "" and row["date"] == ""

    rec_path = ROOT / "releases" / f"{row['id']}.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    primary_path = ROOT / rec["file_nan"]
    fallback_path = ROOT / rec["file_zeros"]
    assert sha256(primary_path) == row["sha256"] == rec["sha256"]
    assert sha256(fallback_path) == rec["sha256_zeros"]
    assert row["sha256"] not in {lineage["rebuilt_zeros_sha256"], lineage["rebuilt_nan_sha256"]}

    with rasterio.open(verified["sample_submission"]) as sample:
        ref = (sample.shape, sample.crs, sample.transform, sample.count, sample.dtypes[0])
    with rasterio.open(primary_path) as ds:
        a = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform, ds.count, ds.dtypes[0]) == ref
        assert ds.dtypes[0] == "float32" and ds.count == 1 and str(ds.crs) == "EPSG:32611"
        assert np.isfinite(a[foot]).all() and np.isnan(a[~foot]).all()
        assert np.all((a[foot] == 0.0) | (a[foot] == 1.0))
        assert not np.any(a[cat] > 0.0)
        mask = a > 0.5
    with rasterio.open(fallback_path) as ds:
        z = ds.read(1)
        assert (ds.shape, ds.crs, ds.transform, ds.count, ds.dtypes[0]) == ref
        assert np.isfinite(z).all() and np.all(z[~foot] == 0.0)
        assert np.all((z[foot] == 0.0) | (z[foot] == 1.0))
        assert not np.any(z[cat] > 0.0)
        assert np.array_equal(mask, z > 0.5)

    n = int(mask.sum())
    added = int((mask & ~r0).sum())
    removed = int((r0 & ~mask).sum())
    pct = 100.0 * removed / int(r0.sum())
    assert n == int(r0.sum()) == 37_654
    assert added == removed == 941
    assert 1.0 <= pct <= 50.0
    assert np.array_equal(mask, np.isfinite(a) & (a > 0.5))
    assert abs(pct - float(row["pct_changed"])) < 0.01
    assert float(d_cat[mask].min()) >= 2.6
    assert row["sha256"][:8] in row["id"]
    assert len(rec["form_note"]) <= 140
    print(json.dumps({
        "ok": True,
        "id": row["id"],
        "nan_sha256": row["sha256"],
        "zeros_sha256": rec["sha256_zeros"],
        "dots": n,
        "added": added,
        "removed": removed,
        "pct_changed": round(pct, 4),
        "min_d_cat_px": round(float(d_cat[mask].min()), 4),
        "primary": "format/hash/value/outside-footprint/catalogue checks PASS",
        "fallback": "format/hash/value/outside-footprint/catalogue checks PASS",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
