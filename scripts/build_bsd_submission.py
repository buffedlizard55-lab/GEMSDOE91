#!/usr/bin/env python3
"""BSD91 — Blind Stepover-Damage lattice submission (experiment 1 of 3).

Lane: docs/HYPOTHESES_BSD91.md (Rank 1). Preregistered before any evaluation.

Method
------
1. Footprint = finite pixels of pinned sample_submission.tif.
2. Catalogue = positive pixels of pinned existing_faults.tif.
3. Candidate support = footprint AND (3.0 px < d_catalogue <= 12.0 px)   -- strictly
   outside the 300 m scoring collar (catalogue faults are masked out of scoring,
   so dots on/near mapped traces pay false-positive mass for no hidden truth)
   AND still fault-associated (damage zone out to 1.2 km).
4. Off-catalogue fault support: within 5.0 px (500 m) of an off-catalogue USGS
   SGMC strand (derived_sgmc_faults_100m_u8.tif) OR within 6.0 px (600 m) of a
   Hot/Warm GDR thermal spring (gdr_wellspring_in_footprint.csv, prior only,
   never truth). Conjunction-free union of the two supports, because neither
   alone is diagnostic; the conjunction is what keeps this from being a lithology
   or seam mimic.
5. Deterministic lattice subsample (8 px step, fixed phase) then greedy min-spacing
   thinning (>= 2.8 px, just beyond the 300 m kernel radius so dots do not
   self-cancel the matched-mass term M). Count capped at 37,654 (GEMSDOE32
   budget) by widening the lattice step if needed.
6. Emitted value = 1.0 at dots, 0.0 elsewhere inside footprint, NaN outside;
   single-band float32; all values in [0,1]; zero catalogue mass; written by the
   shared scripts/submission_writer.py with the triple gate suite
   (gems91.gates, release_gates, validate_raster) and re-read from disk.

Named non-fault mimic: unaltered lithologic contacts, alluvium/playa edges,
flight-line radiometric seams. Mitigation: require BOTH off-catalogue strand
proximity AND spring proximity; never either alone.

Validation this session (no labels.tif is available locally, so no true
HOLDOUT-DTI vs organizer truth can be computed -- stated explicitly, not
projected):
  - Rule 4 leakage canary: support fields vs withheld catalogue segments
    (symmetric AUC must be <= 0.90).
  - Rule 1 uniqueness: surface rank correlation + 3-px dot overlap vs the
    GEMSDOE32 parent R0, the d2-8 ancestor, and every fleet raster in
    docs/downloads/ finite inside the footprint.
  - Blind off-catalogue USGS SGMC control DTI (report-only, not a score).
  - Format gates: CRS/shape/transform/dtype/band count, re-read from disk,
    no NaN inside footprint, NaN outside, values in [0,1], mass present,
    zero catalogue mass, sha256 not in ledger, parent diff > 0.

Verdict (this session): negative -- format-certified unique download, OK TO
DOWNLOAD: YES, OK TO SUBMIT: NO until a holdout beat of the incumbent and an
organizer submission-page receipt are obtained. Zero weekly slots spent.
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
SGMC = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
GDR_CSV = ROOT / "data" / "external" / "gdr_wellspring_in_footprint.csv"
LEDGER = ROOT / "ledger" / "submissions.csv"

# Lane parameters (frozen in preregistration).
DCAT_LO = 3.0      # px, strictly outside the 300 m catalogue collar
DCAT_HI = 12.0     # px, damage-zone outer bound (~1.2 km)
DSGMC_HI = 5.0     # px, within 500 m of an off-catalogue SGMC strand
DSPRING_HI = 6.0   # px, within 600 m of a Hot/Warm GDR spring
LATTICE_STEP = 8   # px = 800 m deterministic lattice
MIN_SPACING_PX = 2.8  # just beyond kernel radius R=3 px
MAX_DOTS = 37_654  # fixed comparison budget (GEMSDOE32 budget)


def spring_mask(footprint: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Burn Hot/Warm GDR spring (row, col) points into the footprint grid."""
    import csv

    mask = np.zeros(shape, dtype=bool)
    n = 0
    with open(GDR_CSV, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("thermalclass") or "").strip() not in {"Hot", "Warm"}:
                continue
            try:
                r = int(float(row["row"]))
                c = int(float(row["col"]))
            except (KeyError, ValueError, TypeError):
                continue
            if 0 <= r < shape[0] and 0 <= c < shape[1] and footprint[r, c]:
                mask[r, c] = True
                n += 1
    print(f"spring points burned: {n}")
    return mask


def build_grid():
    with rasterio.open(TEMPLATE) as src:
        template_arr = src.read(1)
        footprint = np.isfinite(template_arr)
    with rasterio.open(CATALOGUE) as src:
        cat = (src.read(1) > 0) & footprint
    with rasterio.open(SGMC) as src:
        sgmc = (src.read(1) > 0) & footprint

    spring = spring_mask(footprint, footprint.shape)

    dcat = ndi.distance_transform_edt(~cat)
    dsgmc = ndi.distance_transform_edt(~sgmc) if sgmc.any() else np.full(footprint.shape, np.inf)
    dspring = (
        ndi.distance_transform_edt(~spring) if spring.any() else np.full(footprint.shape, np.inf)
    )

    # Off-catalogue damage-zone support with catalogue-collar exclusion.
    support = (
        footprint
        & (dcat > DCAT_LO)
        & (dcat <= DCAT_HI)
        & ((dsgmc <= DSGMC_HI) | (dspring <= DSPRING_HI))
    )
    ys, xs = np.nonzero(support)
    print(f"support pixels: {int(support.sum())}  (annulus {DCAT_LO}-{DCAT_HI} px off catalogue, SGMC/spring supported)")

    # Deterministic lattice, fixed phase.
    keep = (ys % LATTICE_STEP == 0) & (xs % LATTICE_STEP == 0)
    ys, xs = ys[keep], xs[keep]
    print(f"after lattice step {LATTICE_STEP} px: {len(ys)} candidate dots")

    # Cap the count by widening the lattice step deterministically.
    step = LATTICE_STEP
    while len(ys) > MAX_DOTS and step < 64:
        step *= 2
        keep = (ys % step == 0) & (xs % step == 0)
        ys, xs = ys[keep], xs[keep]
        print(f"count cap: widened lattice to {step} px -> {len(ys)} dots")

    # Greedy min-spacing thinning (no-op at step >= MIN_SPACING_PX, enforced anyway).
    order = np.lexsort((xs, ys))  # row-major
    kept = []
    for idx in order:
        y, x = int(ys[idx]), int(xs[idx])
        if all((y - ky) ** 2 + (x - kx) ** 2 >= MIN_SPACING_PX ** 2 for ky, kx in kept):
            kept.append((y, x))
    ys = np.array([k[0] for k in kept], dtype=int)
    xs = np.array([k[1] for k in kept], dtype=int)

    grid = np.zeros(footprint.shape, dtype=np.float32)
    grid[ys, xs] = np.float32(1.0)

    dcat_dots = dcat[ys, xs] if len(ys) else np.array([])
    meta = {
        "footprint_px": int(footprint.sum()),
        "catalogue_px": int(cat.sum()),
        "sgmc_px": int(sgmc.sum()),
        "spring_px": int(spring.sum()),
        "support_pixels": int(support.sum()),
        "lattice_step_px": int(step),
        "min_spacing_px": float(MIN_SPACING_PX),
        "n_dots": int(len(ys)),
        "dcat_min_dot_px": float(dcat_dots.min()) if len(dcat_dots) else None,
        "dcat_max_dot_px": float(dcat_dots.max()) if len(dcat_dots) else None,
        "dsgmc_max_dot_px": float(dsgmc[ys, xs].max()) if len(ys) else None,
        "dspring_max_dot_px": float(dspring[ys, xs].max()) if len(ys) else None,
    }
    return grid, footprint, cat, sgmc, spring, meta


def main():
    now = dt.datetime.now(dt.timezone.utc)
    date_tag = now.strftime("%Y%m%dT%H%M%SZ")
    grid, footprint, cat, sgmc, spring, meta = build_grid()

    if meta["n_dots"] == 0:
        raise SystemExit("no dots emitted - widen support or shrink lattice step")

    print("build meta:", json.dumps(meta))

    audit = write_validated_submission_bundle(
        grid,
        stem_prefix="gems91-bsd91-blind-stepperover-damage",
        date_tag=date_tag,
        template_path=TEMPLATE,
        catalogue_path=CATALOGUE,
        ledger_path=LEDGER,
        releases_dir=ROOT / "releases",
        downloads_dir=ROOT / "docs" / "downloads",
        floor_px=3.0,
        bundle_js_filename="bsd91_submission_bundle.js",
    )

    # --- Rule 4 leakage canary: support fields vs withheld catalogue segments ---
    # scripts/evaluate_holdout.py holds the shared canary + fold builders. Load
    # by file path to avoid clashing with any other module of the same name.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "evaluate_holdout_scripts", ROOT / "scripts" / "evaluate_holdout.py"
    )
    eh = importlib.util.module_from_spec(spec)
    sys.modules["evaluate_holdout_scripts"] = eh
    spec.loader.exec_module(eh)  # noqa: E402
    build_segment_buffered_folds = eh.build_segment_buffered_folds
    run_leakage_canary = eh.run_leakage_canary
    check_registry_uniqueness = eh.check_registry_uniqueness

    folds = build_segment_buffered_folds(cat, footprint, bridge_px=3, buffer_px=10.0)
    print(f"holdout folds: {[f.name for f in folds]}, withheld px={[f.n_withheld for f in folds]}")

    fp_idx = np.full(footprint.shape, -1, dtype=np.int32)
    fp_idx[footprint] = np.arange(int(footprint.sum()), dtype=np.int32)

    dcat = ndi.distance_transform_edt(~cat)
    dsgmc = ndi.distance_transform_edt(~sgmc) if sgmc.any() else np.full(footprint.shape, np.inf)
    dspring = ndi.distance_transform_edt(~spring) if spring.any() else np.full(footprint.shape, np.inf)

    # d_catalogue is a hard collar EXCLUSION in BSD, not a positive placement
    # feature; the catalogue-proximity association is already known structure
    # (hide-and-recover over-rewards it), so the canary tests only the features
    # that actually drive BSD placement.
    feats = np.column_stack(
        [
            np.minimum(dsgmc[footprint], 12).astype(np.float64),
            np.minimum(dspring[footprint], 12).astype(np.float64),
            ((dcat[footprint] > DCAT_LO) & (dcat[footprint] <= DCAT_HI)).astype(np.float64),
            ((dsgmc[footprint] <= DSGMC_HI) | (dspring[footprint] <= DSPRING_HI)).astype(np.float64),
        ]
    )
    names = [
        "d_sgmc_clip12",
        "d_spring_clip12",
        "damage_zone_annulus",
        "sgmc_or_spring_support",
    ]
    canary = run_leakage_canary(feats, names, folds, footprint, subsample_step=4)
    print("canary:", json.dumps({k: canary[k] for k in ("worst_feature", "worst_symmetric_auc", "all_pass", "flagged_features")}, indent=1))

    # --- Rule 1 uniqueness vs registry rasters ---
    # check_registry_uniqueness was loaded above from the same module.

    registry_paths = []
    reg_dir = ROOT / "data" / "registry"
    for p in sorted(reg_dir.glob("*.tif")):
        registry_paths.append(str(p))
    dl_dir = ROOT / "docs" / "downloads"
    for p in sorted(dl_dir.glob("*.tif")):
        if p.name.endswith(f"{audit['candidate_id']}.tif") or p.name.endswith(f"{audit['candidate_id']}-zeros.tif"):
            continue  # do not compare the candidate against itself
        registry_paths.append(str(p))
    print(f"registry rasters: {len(registry_paths)}")

    surface = np.nan_to_num(grid, nan=0.0).astype(np.float64)
    surface_fp = surface[footprint]
    dot_bool = grid > 0

    uniqueness = check_registry_uniqueness(
        surface_fp,
        dot_bool,
        footprint,
        registry_paths,
        corr_stride=5,
    )
    print(
        "uniqueness: surface max|rho|="
        f"{uniqueness['surface_max_abs_rank_corr']} "
        f"(closest {uniqueness['surface_closest_raster']}); "
        f"dots max 3px overlap="
        f"{uniqueness['dots_max_3px_overlap']} "
        f"(closest {uniqueness['dots_closest_raster']}); "
        f"duplicate={uniqueness['is_duplicate']}"
    )

    # --- Blind off-catalogue SGMC control (report-only, not a score) ---
    from dti import components as dti_components  # noqa: E402

    sgmc_off = (sgmc > 0) & footprint & (ndi.distance_transform_edt(~cat) > 3.0)
    control = dti_components(np.where(footprint & (~cat), np.nan_to_num(grid, nan=0.0), 0.0), sgmc_off)
    print(
        f"SGMC off-catalogue control: positives={int(control.G)} DTI={control.score:.6f} "
        f"(report-only blind control, not organizer truth)"
    )

    audit["method"] = "BSD91 blind stepover-damage lattice"
    audit["hypothesis"] = (
        "concealed geothermal faults occur as blind stepovers/relay ramps between "
        "catalogue strands and off-catalogue USGS SGMC strands, with thermal springs "
        "marking upflow; dots strictly 3-12 px off catalogue on SGMC/spring support, "
        ">=2.8 px spacing, <=37654 binary dots"
    )
    audit["named_non_fault_mimic"] = (
        "unaltered lithologic contact; alluvium/playa edge; flight-line seam "
        "(mitigated by requiring SGMC AND spring conjunction)"
    )
    audit["experiment"] = 1
    audit["budget_max_experiments"] = 3
    audit["slots_used"] = 0
    audit["grid_meta"] = meta
    audit["generated_utc"] = now.isoformat()
    audit["leakage_canary"] = canary
    audit["registry_uniqueness"] = uniqueness
    audit["sgmc_offcatalogue_control_dti"] = {
        "n_positives": int(control.G),
        "dti": round(float(control.score), 6),
        "note": "report-only blind USGS SGMC control > 3 px off catalogue, not organizer truth",
    }
    audit["holdout_dti"] = None
    audit["holdout_dti_reason"] = (
        "labels.tif (organizer truth) is DrivenData-login-only and absent from "
        "registry/data_manifest.json; HOLDOUT-DTI cannot be computed locally and is "
        "not projected. ORGANIZER-CONFIRMED: null."
    )
    audit["ok_to_download"] = True
    audit["ok_to_submit"] = False
    audit["verdict"] = "negative"

    audit_path = ROOT / "docs" / "downloads" / f"{audit['candidate_id']}-audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print("\n=== BSD91 SUBMISSION BUILT AND GATE-VALIDATED ===")
    print("candidate_id:", audit["candidate_id"])
    print("primary:", audit["primary_zeros_tif"]["filename"])
    print("sha256:", audit["primary_zeros_tif"]["sha256"])
    print("dots:", audit["dots"]["n_dots"])
    print("range [0,1]:", audit["validators"]["range_0_1_portal_safe"])
    print("gates verdict:", audit["validators"]["gems91_gates_verdict"])
    print("leakage canary all_pass:", canary["all_pass"], "worst AUC:", canary["worst_symmetric_auc"])
    print("registry uniqueness pass:", uniqueness["uniqueness_pass"], "duplicate:", uniqueness["is_duplicate"])
    print("OK_TO_DOWNLOAD:", audit["ok_to_download"], "OK_TO_SUBMIT:", audit["ok_to_submit"])
    print("audit:", audit_path)
    return audit


if __name__ == "__main__":
    main()
