#!/usr/bin/env python3
"""Build a UNIQUE far-field hexagonal-lattice GeoTIFF (HEXFAR91).

LANE (this session only): hexagonal stagger lattice in the 18–35 px
(1.8–3.5 km) far-field halo of existing_faults.tif.

This is NOT the 3–10 px 1 km square lattice of unique-offcatalogue-damagezone
and NOT a ridge / HGB / Euler / drainage fusion.

Hypothesis: unmapped geothermal-hosting structures sit at basin-scale
step-overs and relay ramps 1.8–3.5 km off the mapped USGS/INGENIOUS traces,
not in the 300 m–1 km damage collar already searched.

Mechanism:
  1. Footprint = finite pixels of pinned sample_submission.tif.
  2. Catalogue = existing_faults.tif > 0 inside footprint.
  3. Euclidean distance to catalogue.
  4. Keep footprint pixels with 18 < d <= 35 px.
  5. Hexagonal lattice: step 13 px in y; even rows x % 13 == 0, odd rows
     x % 13 == 6 (half-step stagger). Deterministic, no labels.
  6. Value 1.0 at dots, 0.0 elsewhere in footprint (zeros twin is the
     portal-safe file).

Named non-fault mimic: range-front pediment breaks and playa shorelines
at similar kilometre offsets from mapped range-bounding faults.

Experiment 1 of 3. Zero competition slots.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]

from submission_writer import write_validated_submission_bundle  # noqa: E402

TEMPLATE = ROOT / "data" / "official" / "sample_submission.tif"
CATALOGUE = ROOT / "data" / "official" / "existing_faults.tif"

DCAT_LO = 18.0
DCAT_HI = 35.0
STEP = 13  # px ≈ 1.3 km
STAGGER = 6


def build_grid():
    with rasterio.open(TEMPLATE) as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE) as src:
        cat = (src.read(1) > 0) & footprint
    dcat = ndi.distance_transform_edt(~cat)
    halo = footprint & (dcat > DCAT_LO) & (dcat <= DCAT_HI)
    ys, xs = np.nonzero(halo)
    even = (ys % STEP == 0) & (xs % STEP == 0)
    odd = (ys % STEP == STEP // 2) & ((xs + STAGGER) % STEP == 0)
    keep = even | odd
    ys, xs = ys[keep], xs[keep]
    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[ys, xs] = np.float32(1.0)
    meta = {
        "footprint_px": int(footprint.sum()),
        "catalogue_px": int(cat.sum()),
        "halo_px": int(halo.sum()),
        "n_dots": int((grid > 0).sum()),
        "dcat_lo": DCAT_LO,
        "dcat_hi": DCAT_HI,
        "step_px": STEP,
        "stagger_px": STAGGER,
        "dcat_min_dot_px": float(dcat[grid > 0].min()) if (grid > 0).any() else None,
        "dcat_max_dot_px": float(dcat[grid > 0].max()) if (grid > 0).any() else None,
    }
    return grid, footprint, meta


def main():
    now = dt.datetime.now(dt.timezone.utc)
    date_tag = now.strftime("%Y%m%dT%H%M%SZ")
    grid, footprint, meta = build_grid()
    if meta["n_dots"] == 0:
        raise SystemExit("empty hexfar lattice")
    print("build meta:", meta)
    audit = write_validated_submission_bundle(
        grid,
        stem_prefix="gems91-hexfar-stagger-18-35",
        date_tag=date_tag,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=ROOT / "ledger" / "submissions.csv",
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs" / "downloads",
        floor_px=3.0,
        bundle_js_filename="hexfar_submission_bundle.js",
    )
    audit["method"] = "hexagonal far-field 18-35 px stagger lattice"
    audit["hypothesis"] = (
        "unmapped geothermal-hosting step-overs at 1.8-3.5 km off catalogue"
    )
    audit["named_non_fault_mimic"] = "range-front pediment break; playa shoreline"
    audit["experiment"] = 1
    audit["budget_max_experiments"] = 3
    audit["grid_meta"] = meta
    audit["generated_utc"] = now.isoformat()
    audit_path = ROOT / "docs" / "downloads" / f"{audit['candidate_id']}-audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print("candidate_id:", audit["candidate_id"])
    print("sha256:", audit["primary_zeros_tif"]["sha256"])
    print("dots:", audit["dots"]["n_dots"])
    print("gates:", audit["validators"]["gems91_gates_verdict"])
    print("audit:", audit_path)
    return audit


if __name__ == "__main__":
    main()
