#!/usr/bin/env python3
"""Build a UNIQUE, format-valid GeoTIFF submission for the GEMS-DOE competition.

Method (preregistered here, implemented once): damage-zone annulus lattice.

Hypothesis: geothermal permeability is hosted in fault DAMAGE ZONES and at
off-fault stepovers rather than exactly on the mapped catalogue traces.  Known
catalogue faults (existing_faults.tif) are already "found"; this candidate
searches the damage-zone annulus 300 m - 1 km off the catalogue, which no prior
fleet submission targets at fixed systematic density.

Mechanism:
  1. Footprint = non-null pixels of the pinned sample_submission.tif.
  2. Catalogue mask = positive pixels of pinned existing_faults.tif.
  3. Euclidean distance transform from the catalogue.
  4. Candidate pixels = footprint AND (3.0 px < d_catalogue <= 10.0 px):
     strictly outside the 3 px (300 m) catalogue collar (gate) but still
     fault-associated (damage zone).
  5. Regular lattice sub-sampling (fixed 1 km / 10 px step on both axes,
     deterministic offset) for a controlled, spatially balanced dot count.
  6. Emitted value = 1.0 at dots, 0.0 elsewhere inside footprint, NaN outside.
     => single-band float32, all values in [0,1], no NaN inside footprint.

Named non-fault mimic: unaltered lithologic contacts and survey flight-line seams
can also produce off-fault edge/damage-zone-like responses; this candidate uses
only the catalogue + footprint, so it cannot fit those, which is exactly why it
is a clean, testable, unique negative-control design rather than a leaked fit.

This is experiment 1 of 3 (budget). It does not consume a competition slot and
does not upload anywhere. It writes a -nan.tif (spec primary) and a -zeros.tif
fallback twin plus a single-member ZIP and browser bundle via the shared
scripts/submission_writer.py, then re-reads from disk and runs the triple gate
suite (gems91.gates, release_gates, validate_raster).
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from submission_writer import write_validated_submission_bundle  # noqa: E402

TEMPLATE = ROOT / "data" / "official" / "sample_submission.tif"
CATALOGUE = ROOT / "data" / "official" / "existing_faults.tif"
LEDGER = ROOT / "ledger" / "submissions.csv"

# Damage-zone annulus (px): strictly outside the 3 px collar, fault-associated.
DCAT_LO = 3.0
DCAT_HI = 10.0
LATTICE_STEP = 10  # px = 1 km


def build_grid():
    with rasterio.open(TEMPLATE) as src:
        profile = src.profile
        footprint = np.isfinite(src.read(1))
    with rasterio.open(CATALOGUE) as src:
        cat = src.read(1) > 0
    cat = cat & footprint

    # Exact Euclidean distance to nearest catalogue pixel.
    dcat = ndi.distance_transform_edt(~cat)

    annulus = footprint & (dcat > DCAT_LO) & (dcat <= DCAT_HI)
    ys, xs = np.nonzero(annulus)

    # Deterministic lattice: keep points on the LATTICE_STEP grid with a fixed
    # phase, then de-duplicate to one dot per lattice cell.
    keep = (ys % LATTICE_STEP == 0) & (xs % LATTICE_STEP == 0)
    ys, xs = ys[keep], xs[keep]

    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[ys, xs] = np.float32(1.0)

    meta = {
        "footprint_px": int(footprint.sum()),
        "catalogue_px": int(cat.sum()),
        "annulus_candidate_px": int(annulus.sum()),
        "lattice_step_px": int(LATTICE_STEP),
        "n_dots": int((grid > 0).sum()),
        "dcat_min_dot_px": float(ndi.distance_transform_edt(~cat)[grid > 0].min()) if (grid > 0).any() else None,
        "dcat_max_dot_px": float(ndi.distance_transform_edt(~cat)[grid > 0].max()) if (grid > 0).any() else None,
    }
    return grid, footprint, meta


def main():
    now = dt.datetime.now(dt.timezone.utc)
    date_tag = now.strftime("%Y%m%dT%H%M%SZ")
    grid, footprint, meta = build_grid()

    if meta["n_dots"] == 0:
        raise SystemExit("no dots emitted - annulus empty; widen DCAT_HI or shrink LATTICE_STEP")

    print("build meta:", meta)

    audit = write_validated_submission_bundle(
        grid,
        stem_prefix="gems91-unique-offcatalogue-damagezone",
        date_tag=date_tag,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=LEDGER,
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs" / "downloads",
        floor_px=3.0,
        bundle_js_filename="unique_offcatalogue_damagezone_submission_bundle.js",
    )

    audit["method"] = "damage-zone annulus lattice"
    audit["hypothesis"] = ("geothermal permeability hosted in fault damage zones "
                           "300 m-1 km off the mapped catalogue; off-catalogue, "
                           "off-collar, fixed systematic density")
    audit["named_non_fault_mimic"] = "unaltered lithologic contact; survey flight-line seam"
    audit["experiment"] = 1
    audit["budget_max_experiments"] = 3
    audit["grid_meta"] = meta
    audit["generated_utc"] = now.isoformat()

    audit_path = ROOT / "docs" / "downloads" / f"{audit['candidate_id']}-audit.json"
    audit_path.write_text(__import__("json").dumps(audit, indent=2) + "\n", encoding="utf-8")

    print("\n=== UNIQUE SUBMISSION BUILT AND GATE-VALIDATED ===")
    print("candidate_id:", audit["candidate_id"])
    print("primary:", audit["primary_zeros_tif"]["filename"])
    print("sha256:", audit["primary_zeros_tif"]["sha256"])
    print("dots:", audit["dots"]["n_dots"], "min catalogue dist px:",
          audit["dots"]["min_catalogue_distance_px"])
    print("range [0,1]:", audit["validators"]["range_0_1_portal_safe"])
    print("gates verdict:", audit["validators"]["gems91_gates_verdict"])
    print("audit:", audit_path)
    return audit


if __name__ == "__main__":
    main()
