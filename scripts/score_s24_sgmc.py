#!/usr/bin/env python3
"""Report-only SGMC off-catalogue diagnostic for existing S24/fleet rasters.

Scores files already on disk with the shared
``scripts/evaluate_holdout.score_off_catalogue_sgmc`` (USGS SGMC faults
strictly >3 px from the competition catalogue as proxy truth). This creates
no candidate and is not an experiment, a gate, or a leaderboard estimate:
SGMC is a mixed-scale map compilation, and agreement with it measures
agreement with another map, not with the hidden competition labels.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

import numpy as np
import rasterio

from evaluate_holdout import score_off_catalogue_sgmc


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    man = {r["id"]: r for r in json.loads((ROOT / "registry/data_manifest.json").read_text())["files"]}
    for rid in ("sample_submission", "existing_faults", "sgmc_faults_control", "parent_r0_zeros"):
        p = ROOT / "data" / man[rid]["local_subpath"]
        if sha(p) != man[rid]["sha256"]:
            raise ValueError(f"pinned input drift: {rid}")
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        catalogue = ds.read(1)
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as ds:
        sgmc = ds.read(1)

    e1 = json.loads((ROOT / "docs/s24/run-card.json").read_text())
    e2 = json.loads((ROOT / "docs/s24/e2/run-card.json").read_text())
    targets = [
        ("s24_cckm_e1_20000", e1["artifact"]["tif"]),
        ("s24_cckm_e2_37654", e2["artifact"]["tif"]),
        ("parent_r0_gemsdoe32_h33_2_b2", "data/" + man["parent_r0_zeros"]["local_subpath"]),
    ]
    nine = json.loads((ROOT / "docs/s22/nine-site-audit.json").read_text())["sites"]
    for s in nine:
        if sha(ROOT / s["local_path"]) != s["sha256"]:
            raise ValueError(f"nine-leader bytes drift: {s['site']}")
        targets.append((f"nine_{s['site'].lower()}", s["local_path"]))

    rows = []
    for name, rel in targets:
        with rasterio.open(ROOT / rel) as ds:
            if ds.shape != footprint.shape or str(ds.crs) != "EPSG:32611":
                raise ValueError(f"grid mismatch: {rel}")
            pred = ds.read(1)
        finite = np.isfinite(pred[footprint]).all() and (pred[footprint] >= 0).all() and (pred[footprint] <= 1).all()
        res = score_off_catalogue_sgmc(pred, sgmc, catalogue, footprint)
        rows.append({"name": name, "path": rel, "sha256": sha(ROOT / rel),
                     "finite_values_in_0_1_inside_footprint": bool(finite),
                     "n_positive_pixels_inside": int(((pred > 0) & footprint).sum()), **res})
    out = {
        "label": "SGMC-OFFCAT-CONTROL-DTI (report-only; not HOLDOUT-DTI, not a leaderboard estimate)",
        "evaluator": "scripts/evaluate_holdout.score_off_catalogue_sgmc -> scripts/dti.components "
                     "(alpha 0.2, beta 0.8, 300 m triangular kernel)",
        "sgmc_input": {"path": "data/" + man["sgmc_faults_control"]["local_subpath"],
                       "sha256": man["sgmc_faults_control"]["sha256"]},
        "caveats": [
            "SGMC is an external mixed-scale USGS map compilation; its off-catalogue faults are "
            "proxy truth, not the hidden competition labels.",
            "Files with a full-catalogue emission collar are not handicapped here the way they "
            "are on catalogue hide-and-recover, because SGMC positives are >3 px off-catalogue.",
            "No score on this diagnostic may be converted into a leaderboard estimate.",
        ],
        "rows": sorted(rows, key=lambda r: -r["dti"]),
    }
    p = ROOT / "docs/s24/sgmc-diagnostic.json"
    p.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    for r in out["rows"]:
        print(f"{r['dti']:.6f}  {r['name']:<34} n_pos={r['n_positive_pixels_inside']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
