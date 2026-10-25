#!/usr/bin/env python3
"""Re-run the protocol registry check for the ISO91 candidate against the CURRENT registry.

Needed after merging main: parallel sessions added new docs/downloads rasters after the final build.
Uses the shared run_olc91.registry_check unchanged; only the candidate's own bytes are excluded.
Writes docs/iso91/registry-recheck.json (consumed by scripts/build_iso91_card.py for gate G6a).
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "vendor"), str(ROOT / "src"), str(ROOT / "scripts")]
import run_olc91 as O  # noqa: E402
from gems57 import grid as G  # noqa: E402


def main():
    fin = json.loads((ROOT / "docs/iso91/final.json").read_text())
    tif = ROOT / fin["tif"]
    cand_sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    g = G.load_grid(ROOT / "data" / "official")
    fp, cat = g.footprint, g.catalogue
    with rasterio.open(tif) as ds:
        dots = (ds.read(1) > 0).astype(np.float32)
    surface = np.load(ROOT / "work/iso91/final_surface_E1.npy").astype(np.float32)
    eligible = fp & ~cat & (ndi.distance_transform_edt(~cat) > O.COLLAR_PX)
    original = O.registry_paths

    def without_candidate():
        uniq, dup = original()
        return [(p, h) for p, h in uniq if h != cand_sha], dup

    O.registry_paths = without_candidate
    reg = O.registry_check(surface, dots, fp, eligible)
    before = {r["raster"] for r in fin["registry"]["comparisons"]}
    reg["candidate_sha256"] = cand_sha
    reg["surface_source"] = "work/iso91/final_surface_E1.npy (float16 copy of the final surface)"
    reg["new_since_final_build"] = sorted(r["raster"] for r in reg["comparisons"] if r["raster"] not in before)
    out = ROOT / "docs/iso91/registry-recheck.json"
    out.write_text(json.dumps(reg, indent=2) + "\n")
    new_rows = [r for r in reg["comparisons"] if r["raster"] in reg["new_since_final_build"]]
    print(json.dumps(dict(n_checked=reg["n_unique_rasters_checked"], new=len(new_rows),
                          surface_max=reg["surface_max_abs_spearman"], non_blanket_max=reg["dots_max_within_3px_non_blanket"],
                          closest=reg["dots_closest_non_blanket"], any_dup_corrected=reg["any_duplicate_chance_corrected"],
                          new_rows=[(r["raster"], r["dots_within_3px_literal"], r["surface_abs_spearman"]) for r in new_rows]), indent=1))


if __name__ == "__main__":
    main()
