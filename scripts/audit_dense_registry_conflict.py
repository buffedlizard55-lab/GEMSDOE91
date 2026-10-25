#!/usr/bin/env python3
"""Recheck inherited candidate dots against the pinned dense R13 registry raster.

This is a post-hoc, label-free registry audit only. It does not make a surface,
place dots, score a holdout, write a TIFF, or clear a competition submission.
It deliberately reports the incomplete registry scope and fails closed when any
pinned input, candidate byte hash, or grid is missing or changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "docs/run-card-ARENA-4F073E28.json"
MANIFEST_PATH = ROOT / "registry/data_manifest.json"
INVENTORY_PATH = ROOT / "registry/comparison_inventory.json"
OUTPUT_PATH = ROOT / "docs/registry-revalidation-4F073E28.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_verified(path: Path, expected_sha: str):
    if not path.is_file():
        raise FileNotFoundError(f"Missing pinned audit input: {path.relative_to(ROOT)}")
    actual = sha256(path)
    if actual != expected_sha:
        raise ValueError(f"SHA-256 mismatch for {path.relative_to(ROOT)}: {actual}")
    with rasterio.open(path) as src:
        return src.read(1), (src.count, src.shape, src.crs, src.transform)


def binary_spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Exact Spearman correlation for two binary arrays (ties are averaged).

    For a non-constant binary variable, average-rank transformation is affine
    in its 0/1 values, so Spearman equals the Pearson correlation of the masks.
    """
    if not x.any() or x.all() or not y.any() or y.all():
        return 0.0
    return float(np.corrcoef(x.astype(np.float64), y.astype(np.float64))[0, 1])


def audit() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in manifest["files"]}
    sample_row = by_id["sample_submission"]
    sample_path = ROOT / "data" / sample_row["local_subpath"]
    sample, meta = load_verified(sample_path, sample_row["sha256"])
    footprint = np.isfinite(sample)

    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    reference_row = next(
        (row for row in inventory["files"]
         if row["path"] == "data/fleet_registry/r13_lattice_s5_00904.tif"),
        None,
    )
    if reference_row is None:
        raise ValueError("Pinned R13 reference is absent from the frozen inventory")
    reference_path = ROOT / reference_row["path"]
    reference_values, ref_meta = load_verified(reference_path, reference_row["sha256"])
    if ref_meta != meta:
        raise ValueError("R13 reference grid does not match sample_submission")
    reference_dots = (reference_values > 0) & footprint
    reference_count = int(reference_dots.sum())
    if reference_count == 0:
        raise ValueError("Pinned R13 reference has no dots in the valid footprint")

    distance = distance_transform_edt(~reference_dots)
    uncovered = footprint & (distance > 3.0)
    observed = []
    for item in json.loads(CARD_PATH.read_text(encoding="utf-8"))["registry_correlation_overlap"]["historical_artifact_rechecks"]:
        path = ROOT / item["artifact"]
        values, candidate_meta = load_verified(path, item["sha256"])
        if candidate_meta != meta:
            raise ValueError(f"Grid mismatch for {item['artifact']}")
        if not np.isfinite(values[footprint]).all():
            raise ValueError(f"Nonfinite candidate values inside footprint: {item['artifact']}")
        dots = (values > 0) & footprint
        n = int(dots.sum())
        if n != item["candidate_dots"]:
            raise ValueError(f"Dot count mismatch for {item['artifact']}: {n}")
        within = int((dots & (distance <= 3.0)).sum())
        overlap = within / n if n else 0.0
        dot_corr = binary_spearman(dots[footprint], reference_dots[footprint])
        status = "DUPLICATE" if (abs(dot_corr) > 0.90 or overlap > 0.70) else "PASS_WITHIN_THIS_REFERENCE"
        observed.append(dict(
            artifact=item["artifact"],
            sha256=item["sha256"],
            candidate_dots=n,
            reference_dots=reference_count,
            candidate_dots_within_3px=within,
            overlap_within_3px=overlap,
            final_dot_spearman=dot_corr,
            surface_rank_correlation=None,
            status=status,
        ))

    budget = 37654
    lower_bound = max(0, budget - int(uncovered.sum())) / budget
    missing = [row["path"] for row in inventory["files"] if not (ROOT / row["path"]).is_file()]
    return dict(
        schema_version="gems91.registry-revalidation.v1",
        purpose="Post-hoc directed dot comparison only; not a new experiment or universal registry clearance.",
        pinned_inputs={
            "sample_submission_sha256": sample_row["sha256"],
            "r13_path": reference_row["path"],
            "r13_sha256": reference_row["sha256"],
        },
        grid=dict(bands=meta[0], shape=list(meta[1]), crs=str(meta[2]), transform=list(meta[3])[:6]),
        r13_reference=dict(
            dots_in_footprint=reference_count,
            footprint_pixels=int(footprint.sum()),
            cells_more_than_3px_from_dots=int(uncovered.sum()),
            covered_fraction_within_3px=1.0 - int(uncovered.sum()) / int(footprint.sum()),
        ),
        historical_artifacts=observed,
        fixed_budget_capacity_bound=dict(
            candidate_budget=budget,
            minimum_overlap_with_r13=lower_bound,
            duplicate_threshold=0.70,
            feasible=False if lower_bound > 0.70 else None,
            derivation="At most one dot per uncovered cell; spacing can only increase overlap.",
        ),
        frozen_inventory=dict(
            rows=len(inventory["files"]),
            complete_universal_registry=bool(inventory.get("complete_universal_registry", False)),
            missing_references=missing,
            not_universal=True,
        ),
        verdict="negative",
        ok_to_submit=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    report = audit()
    destination = args.output if args.output.is_absolute() else ROOT / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS: audit completed; duplicate results are expected negative findings",
        "output": destination.relative_to(ROOT).as_posix(),
        "artifacts_checked": len(report["historical_artifacts"]),
        "duplicate_count": sum(x["status"] == "DUPLICATE" for x in report["historical_artifacts"]),
        "registry_complete": report["frozen_inventory"]["complete_universal_registry"],
    }, indent=2))


if __name__ == "__main__":
    main()
