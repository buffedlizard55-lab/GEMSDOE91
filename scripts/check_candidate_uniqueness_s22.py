#!/usr/bin/env python3
"""Protocol uniqueness screen of an existing candidate raster against every other raster (same code as the S21/S22 screen).

Usage: python3 scripts/check_candidate_uniqueness_s22.py docs/downloads/<file>-zeros.tif docs/s22/<out>.json
The candidate's dots stand in for its surface in the Spearman phase (conservative: dots are rougher than a surface).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "vendor"), str(ROOT / "scripts")]

import numpy as np  # noqa: E402
import rasterio  # noqa: E402

import emit_s22_xbreed as E  # noqa: E402
from gems91 import xbreed22 as X  # noqa: E402


def main() -> int:
    cand, out = Path(sys.argv[1]), Path(sys.argv[2])
    s21 = E.load_s21()
    footprint, catalogue, _ = X.load_common()
    with rasterio.open(ROOT / cand) as ds:
        a = np.nan_to_num(ds.read(1), nan=0.0).astype(np.float32)
    a = np.where(footprint, a, 0.0)
    refs = [r for r in s21.collect_all_reference_rasters() if Path(r["path"]).name != Path(cand).name]
    screen, _ = s21.screen_against_references(a, a, footprint, refs, active_cap_select_thresh=0.9, max_cap_refs=1)
    comp = screen["dots_phase_competitive"]
    res = {"candidate": str(cand), "n_dots": int((a > 0).sum()), "n_compared": screen["n_compared_rasters"],
           "n_competitive": screen["n_competitive_non_blanket_rasters"],
           "max_competitive_3px_overlap": comp["max_3px_overlap_all_competitive"],
           "max_competitive_ref": comp["max_3px_overlap_all_competitive_ref"],
           "competitive_pass": bool(comp["pass_competitive_uniqueness"]),
           "top5": comp["top_20_competitive_by_3px_overlap"][:5],
           "max_abs_surface_spearman_dots_as_surface": screen["surface_phase"]["max_abs_spearman_all_1100plus"]}
    (ROOT / out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "top5"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
