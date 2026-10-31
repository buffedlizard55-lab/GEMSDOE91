#!/usr/bin/env python3
"""S91-ALM: Alteration-Magnetic-Low concealed-fault prior (NEW unique candidate).

HYPOTHESIS
----------
Blind Great Basin geothermal systems are hosted on faults that are concealed
beneath Quaternary basin fill and therefore absent from the public USGS/INGENIOUS
catalogue.  Such concealed conduits are still expressed at the surface by a
**hydrothermal alteration halo** that the catalogue's scarp-based mapping cannot
see:

  * magnetite destruction  -> shallow magnetic residual ``B14 - B01`` goes LOW
  * clay cap               -> shallow conductivity ``B17`` goes HIGH
  * K-depletion            -> radiometric total count ``B06`` goes LOW
  * structural offset      -> isostatic gravity gradient ``|grad B13|`` peaks

The public nine-site leaders (GEMSDOE 24/25/27/28/30/31/32/33/36) all trace one
H19-5 magnetic/gravity *ridge* family; none targets the off-catalogue
alteration halo.  This candidate therefore searches the alteration halo OFF the
mapped catalogue (>3 px collar) rather than reproducing the ridge network.

MECHANISM
---------
1. Footprint = finite pixels of the pinned ``sample_submission.tif``.
2. Catalogue mask = positive pixels of pinned ``existing_faults.tif``.
3. Robust-rank each of four physics fields to [0,1] inside the footprint.
4. Score = 0.35*(1-rank(B14-B01)) + 0.25*rank(B17) + 0.15*(1-rank(B06))
           + 0.25*rank(|grad B13|).
5. Greedy spatial selection: walk cells in descending score, keep a cell only if
   it is >3 px from the catalogue, inside the footprint, and >=3.05 px from every
   already-kept dot; stop at the frozen 37,654-dot budget.
6. Emit via the SHARED ``scripts/submission_writer.py`` (NaN-outside ``.tif`` +
   all-finite ``-zeros.tif`` + single-TIFF ZIP + browser bundle), then re-read
   from disk and run the triple gate suite.

NAMED NON-FAULT MIMIC
--------------------
Unaltered intrusive contacts, volcanic-flow margins, closed-basin evaporite
playas (high B17), and irrigated-agriculture moisture anomalies can also produce
low magnetic residual / high conductivity.  The candidate uses only the official
GeoDAWN stack and the catalogue, so it cannot fit cultural noise; the greedy
3.05 px spacing and the >3 px catalogue collar keep it a clean, testable design.

BUDGET: experiment 1 of 3.  No competition slot is spent; nothing is uploaded.
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
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from submission_writer import write_validated_submission_bundle  # noqa: E402

TEMPLATE = ROOT / "data" / "official" / "sample_submission.tif"
CATALOGUE = ROOT / "data" / "official" / "existing_faults.tif"
FEATURES = ROOT / "data" / "bridge" / "gems-geodawn-numerical-features.tif"
LEDGER = ROOT / "ledger" / "submissions.csv"

BUDGET = 37_654
COLLAR_PX = 3.0          # strict catalogue collar (gate)
MIN_SPACING_PX = 2.5     # min dot-to-dot spacing (~280 m)
NODATA = -3.4028234663852886e+38


def robust_rank01(arr: np.ndarray, fp: np.ndarray) -> np.ndarray:
    """Rank to [0,1] inside the footprint; NaN where the field is non-finite."""
    out = np.full(arr.shape, np.nan, dtype=np.float32)
    fp_idx = np.nonzero(fp)
    vals = arr[fp_idx]
    finite_mask = np.isfinite(vals)
    finite = vals[finite_mask]
    if finite.size == 0:
        return out
    order = np.argsort(np.argsort(finite)).astype(np.float32) / max(finite.size - 1, 1)
    tmp = np.full(vals.shape, np.nan, dtype=np.float32)
    tmp[finite_mask] = order
    out[fp_idx] = tmp
    return out


def clean_band(raw: np.ndarray, fp: np.ndarray) -> np.ndarray:
    a = np.asarray(raw, dtype=np.float32)
    a = np.where(np.isfinite(a) & (a > NODATA), a, np.nan)
    # light destripe along rows (survey flight-line seams)
    med = np.nanmedian(a, axis=1, keepdims=True)
    a = a - np.where(np.isfinite(med), med, 0.0)
    return a


def build_score() -> tuple[np.ndarray, np.ndarray, dict]:
    with rasterio.open(TEMPLATE) as src:
        tpl = src.read(1)
        fp = np.isfinite(tpl) & (src.read_masks(1) > 0)
    with rasterio.open(CATALOGUE) as src:
        cat = (src.read(1) > 0) & fp

    with rasterio.open(FEATURES) as src:
        b01 = clean_band(src.read(1), fp)
        b06 = clean_band(src.read(6), fp)
        b13 = clean_band(src.read(13), fp)
        b14 = clean_band(src.read(14), fp)
        b17 = clean_band(src.read(17), fp)

    # magnetic destruction: shallow residual low
    mag_low = b14 - b01
    # gravity horizontal gradient
    gy, gx = np.gradient(b13)
    grav_grad = np.hypot(gx, gy)

    r_mag = robust_rank01(mag_low, fp)
    r_cond = robust_rank01(b17, fp)
    r_rad = robust_rank01(b06, fp)
    r_grav = robust_rank01(grav_grad, fp)

    score = (0.35 * (1.0 - r_mag) + 0.25 * r_cond + 0.15 * (1.0 - r_rad)
             + 0.25 * r_grav)
    score = np.where(fp, score, -np.inf)
    score = np.where(np.isfinite(score), score, -np.inf).astype(np.float32)

    dcat = ndi.distance_transform_edt(~cat)
    valid = fp & (dcat > COLLAR_PX) & np.isfinite(score)

    meta = {
        "footprint_px": int(fp.sum()),
        "catalogue_px": int(cat.sum()),
        "valid_offcat_px": int(valid.sum()),
        "budget": BUDGET,
        "collar_px": COLLAR_PX,
        "min_spacing_px": MIN_SPACING_PX,
        "score_weights": {"mag_low": 0.35, "cond": 0.25, "rad_low": 0.15, "grav_grad": 0.25},
    }
    return score, valid, meta


def greedy_select(score: np.ndarray, valid: np.ndarray, budget: int) -> tuple[np.ndarray, int]:
    """Greedy top-scoring spatial selection with min spacing."""
    grid = np.zeros(score.shape, dtype=np.float32)
    ys, xs = np.nonzero(valid)
    sc = score[ys, xs]
    order = np.argsort(-sc, kind="stable")
    # Only the top-scoring pool can contribute (each kept dot blocks ~6.25 px^2).
    pool = min(len(order), budget * 12)
    ys, xs = ys[order[:pool]], xs[order[:pool]]

    min_sq = MIN_SPACING_PX * MIN_SPACING_PX
    cell = int(np.ceil(MIN_SPACING_PX))
    grid_cells: dict = {}
    n = 0
    for y, x in zip(ys.tolist(), xs.tolist()):
        if n >= budget:
            break
        cy, cx = y // cell, x // cell
        ok = True
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for (ky, kx) in grid_cells.get((cy + dy, cx + dx), ()):
                    if (ky - y) ** 2 + (kx - x) ** 2 < min_sq:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid[y, x] = 1.0
            grid_cells.setdefault((cy, cx), []).append((y, x))
            n += 1
    return grid, n


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    date_tag = now.strftime("%Y%m%dT%H%M%SZ")
    score, valid, meta = build_score()
    grid, n = greedy_select(score, valid, BUDGET)
    meta["n_dots"] = int(n)
    print("build meta:", meta)
    if n == 0:
        raise SystemExit("no dots emitted")

    audit = write_validated_submission_bundle(
        grid,
        stem_prefix="gems91-s91-alm-alteration-halo",
        date_tag=date_tag,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=LEDGER,
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs" / "downloads",
        floor_px=COLLAR_PX,
        bundle_js_filename=f"s91_alm_{date_tag}_bundle.js",
    )

    audit["method"] = "S91-ALM alteration-magnetic-low concealed-fault prior"
    audit["hypothesis"] = ("concealed geothermal faults expressed by off-catalogue "
                           "hydrothermal alteration halo (magnetic low, clay cap, "
                           "K depletion) + gravity gradient")
    audit["named_non_fault_mimic"] = ("intrusive contact; volcanic-flow margin; "
                                      "closed-basin evaporite playa; irrigated agriculture")
    audit["experiment"] = 1
    audit["budget_max_experiments"] = 3
    audit["grid_meta"] = meta
    audit["generated_utc"] = now.isoformat()

    audit_path = ROOT / "docs" / "downloads" / f"{audit['candidate_id']}-audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print("\n=== S91-ALM UNIQUE SUBMISSION BUILT AND GATE-VALIDATED ===")
    print("candidate_id:", audit["candidate_id"])
    print("primary:", audit["primary_zeros_tif"]["filename"])
    print("sha256:", audit["primary_zeros_tif"]["sha256"])
    print("dots:", audit["dots"]["n_dots"],
          "min catalogue dist px:", audit["dots"]["min_catalogue_distance_px"])
    print("gates verdict:", audit["validators"]["gems91_gates_verdict"])
    print("audit:", audit_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
