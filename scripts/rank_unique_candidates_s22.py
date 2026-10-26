#!/usr/bin/env python3
"""Rank every GEMSDOE91 candidate raster by the two live-aligned instruments (E2 showed hide-v2 is not one).

For each ``docs/downloads/*-zeros.tif`` plus the S22 file: dot count, blind-SGMC DTI (>300 m / >500 m; Spearman vs live
+0.43 / +0.44 across 112 anchors, `docs/s22-xb/instruments.json`), the S20 live-anchored LFI projection (MODEL, LOSO RMSE
~0.02), and the share of the file's dots within 3 px of GEMSDOE32 R0 (a *derivative-of-R0* flag).  Nothing here is a score.

Output: docs/s22-xb/unique-candidates.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

import emit_s22_xbreed as E  # noqa: E402
from gems91 import xbreed22 as X  # noqa: E402


def main() -> int:
    s21 = E.load_s21()
    footprint, catalogue, _ = X.load_common()
    with rasterio.open(ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif") as ds:
        r0 = np.nan_to_num(ds.read(1), nan=0.0) > 0.5
    r0_halo = ndi.distance_transform_edt(~r0) <= 3.0
    files = sorted((ROOT / "docs/downloads").glob("*-zeros.tif"))
    paths = {p.name: p for p in files}
    ref_key = "GEMSDOE32 R0 (USER-REPORTED 0.2778)"
    proj = E.lfi_projections({**paths, ref_key: ROOT / "data/fleet_registry/GEMSDOE32__h33-2-b2-zeros.tif"}, footprint, catalogue)
    rows = []
    for name, p in paths.items():
        with rasterio.open(p) as ds:
            a = np.nan_to_num(ds.read(1), nan=0.0)
        a = np.where(footprint, a, 0.0).astype(np.float32)
        pos = a > 0
        n = int(pos.sum())
        sg = s21.evaluate_blind_sgmc_suite(a, catalogue, footprint) if 0 < n <= 130_000 else {}
        rows.append({
            "file": name, "n_dots": n, "binary": bool(np.all((a == 0) | (a == 1))),
            "sgmc_dti_gt300m": sg.get("sgmc_dti_gt300m"), "sgmc_dti_gt500m": sg.get("sgmc_dti_gt500m"),
            "lfi_ridge10": proj[name]["r10"]["projected"], "lfi_ridge1": proj[name]["r1"]["projected"],
            "share_within_3px_of_R0": round(float((pos & r0_halo).sum() / max(n, 1)), 4),
        })
        print(f"{name[:70]:70s} n={n:7d} lfi10={rows[-1]['lfi_ridge10']:.3f} sgmc500={rows[-1]['sgmc_dti_gt500m']}", flush=True)
    rows.sort(key=lambda r: -r["lfi_ridge10"])
    out = {"label": "MODEL projections and diagnostic controls - never scores", "r0_reference_lfi_ridge10":
           proj[ref_key], "rows": rows}
    (ROOT / "docs/s22-xb/unique-candidates.json").write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
