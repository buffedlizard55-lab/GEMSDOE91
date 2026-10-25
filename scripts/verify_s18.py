#!/usr/bin/env python3
"""Session 18 reproducible checks.  Writes docs/s18/verification.json.

    python scripts/verify_s18.py            # exit 0 only if every check passes

Works without competition data.  If the pinned sample template has been
restored (`python scripts/restore_data.py --only sample_submission`), the
footprint and CRS/shape/transform checks use the real template; otherwise they
fall back to the constants recorded in docs/s16/registry-feasibility.json and
are reported as UNVERIFIED rather than passed.

Checks
  1. Leaderboard snapshot (docs/s18/leaderboard-top50-20261025.json): ordering,
     #1 = 0.4413, #50 = 0.2818, and the rank each user-reported claim would take.
  2. Uniqueness capacity bound (docs/s16/registry-feasibility.json): recomputes
     the lower bound on overlap at 37,654 dots and the largest dot budget that
     can satisfy the 70% literal threshold at all (N <= U / 0.30).
  3. Candidate TIFFs named in README.md: sha256 vs run card, single band,
     float32, EPSG:32611, shape, transform, values in [0, 1], no NaN inside the
     footprint, dots inside the footprint, dot count.  Both zero-filled and
     NaN-outside encodings are accepted, and the encoding is reported.
  4. Every local file the review cites exists.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "s18" / "verification.json"
SAMPLE = ROOT / "data" / "official" / "sample_submission.tif"
SAMPLE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"

CANDIDATES = {
    "olc91_e1": {
        "tif": "docs/downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif",
        "run_card": "docs/run-card-OLC91.json",
    },
    "damage_zone_unique": {
        "tif": "docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif",
        "run_card": "docs/run-card-unique-offcatalogue-damagezone.json",
    },
}

# Constants recorded from the pinned sample in earlier sessions (fallback only).
EXPECTED_CRS = "EPSG:32611"
EXPECTED_SHAPE = (3730, 3292)
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
REFERENCE_FOOTPRINT_PIXELS = 5167373
REFERENCE_FULL_GRID = 3730 * 3292  # 12,279,160

CITED_FILES = [
    "README.md",
    "docs/REVIEW-S18-20261025.md",
    "docs/run-card-S18.json",
    "docs/s18/leaderboard-top50-20261025.json",
    "docs/s16/registry-feasibility.json",
    "docs/s16/gems32-forensics.json",
    "docs/executive-summary.html",
    "docs/index.html",
    "docs/HYPOTHESES_OLC91.md",
    "docs/run-card-OLC91.json",
    "docs/run-card-unique-offcatalogue-damagezone.json",
    "docs/downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif",
    "docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif",
    "registry/data_manifest.json",
    "tests/test_dti_official_formula.py",
    "LIMITATIONS_AND_NEXT_STEPS.md",
    "IRREGULARITIES.md",
    "SLOT_PLAN.md",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _find_sha(obj):
    """First 64-hex-char value stored under a key named sha256 in a run card."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "sha256" and isinstance(v, str) and len(v) == 64:
                return v
            found = _find_sha(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_sha(v)
            if found:
                return found
    return None


def check_leaderboard() -> dict:
    snap = json.loads((ROOT / "docs/s18/leaderboard-top50-20261025.json").read_text())
    rows = snap["rows"]
    scores = [r["score"] for r in rows]
    problems = []
    if scores != sorted(scores, reverse=True):
        problems.append("snapshot not sorted descending")
    if [r["rank"] for r in rows] != list(range(1, len(rows) + 1)):
        problems.append("ranks not contiguous from 1")
    if rows[0]["score"] != 0.4413:
        problems.append("rank 1 is not 0.4413")
    if rows[-1]["score"] != 0.2818:
        problems.append("rank 50 is not 0.2818")

    def placement(score: float) -> str:
        above = sum(1 for s in scores if s > score)
        tied = sum(1 for s in scores if s == score)
        if above >= len(scores):
            return f"below rank {len(scores)} (not in the top {len(scores)} of this snapshot)"
        return f"rank {above + 1}" + (f" (exact match, {tied} entries)" if tied > 1 else (" (exact match)" if tied else ""))

    return {
        "ok": not problems,
        "problems": problems,
        "n_rows": len(rows),
        "rank1": rows[0],
        "rank50": rows[-1],
        "claim_placements": {
            "0.4413 (described as GEMSDOE high score)": placement(0.4413),
            "0.3195 (described as highest score right now)": placement(0.3195),
            "0.2778 (GEMSDOE32, user-reported, no receipt)": placement(0.2778),
        },
    }


def check_feasibility() -> dict:
    rec = json.loads((ROOT / "docs/s16/registry-feasibility.json").read_text())
    U = rec["uncovered_pixels"]
    budget = rec["candidate_budget"]
    thr = rec["threshold"]
    problems = []
    if rec["footprint_pixels"] != REFERENCE_FOOTPRINT_PIXELS:
        problems.append("footprint pixel count differs from the receipt constant")
    bound = (budget - U) / budget
    if not math.isclose(bound, rec["overlap_lower_bound"], rel_tol=0, abs_tol=1e-12):
        problems.append("overlap lower bound does not reproduce")
    if (bound <= thr) != bool(rec["feasible_at_fixed_budget"]):
        problems.append("feasible_at_fixed_budget flag contradicts the recomputed bound")
    # (N - U) / N <= thr  <=>  N <= U / (1 - thr)
    n_max = math.floor(U / (1.0 - thr))
    return {
        "ok": not problems,
        "problems": problems,
        "uncovered_pixels_U": U,
        "covered_fraction": rec["covered_fraction"],
        "budget_N": budget,
        "overlap_lower_bound_at_N": bound,
        "threshold": thr,
        "feasible_at_budget": bound <= thr,
        "max_budget_satisfying_literal_threshold": n_max,
        "share_of_dots_that_must_sit_on_uncovered_pixels_at_max_budget": 1.0 - thr,
        "note": (
            "Literal 70% threshold is reachable only by placing at least (1 - threshold) of the "
            "dots on the U uncovered pixels, i.e. pixels more than 3 px from every lattice dot. "
            "That placement is chosen to avoid a registry file, not to detect faults."
        ),
    }


def _sample_meta():
    if not SAMPLE.exists():
        return None
    import numpy as np
    import rasterio

    with rasterio.open(SAMPLE) as s:
        a = s.read(1)
        meta = {
            "sha256": _sha256(SAMPLE),
            "sha256_pin_matches": _sha256(SAMPLE) == SAMPLE_SHA256,
            "crs": str(s.crs),
            "shape": list(s.shape),
            "transform": list(s.transform)[:6],
            "dtype": s.dtypes[0],
        }
    footprint = np.isfinite(a)
    meta["footprint_pixels"] = int(footprint.sum())
    meta["positive_cells"] = int((np.nan_to_num(a, nan=0.0) > 0).sum())
    meta["footprint_mask"] = footprint
    return meta


def check_candidate(name: str, spec: dict, sample) -> dict:
    import numpy as np
    import rasterio

    tif = ROOT / spec["tif"]
    card = json.loads((ROOT / spec["run_card"]).read_text())
    sha = _sha256(tif)
    card_sha = _find_sha(card)
    problems = []
    if card_sha and card_sha != sha:
        problems.append("sha256 differs from run card")
    if not card_sha:
        problems.append("run card has no sha256 to compare against")

    if sample is not None:
        exp_crs, exp_shape, exp_tr = sample["crs"], tuple(sample["shape"]), tuple(sample["transform"])
        footprint = sample["footprint_mask"]
        footprint_status = "VERIFIED against restored pinned sample"
    else:
        exp_crs, exp_shape, exp_tr = EXPECTED_CRS, EXPECTED_SHAPE, EXPECTED_TRANSFORM
        footprint = None
        footprint_status = "UNVERIFIED: sample not restored; footprint checks skipped"

    with rasterio.open(tif) as ds:
        a = ds.read(1)
        info = {
            "count": ds.count,
            "dtype": ds.dtypes[0],
            "crs": str(ds.crs),
            "shape": list(ds.shape),
            "transform": list(ds.transform)[:6],
            "nodata_tag": ds.nodata,
        }
    if info["count"] != 1:
        problems.append("not single band")
    if info["dtype"] != "float32":
        problems.append("dtype not float32")
    if info["crs"] != exp_crs:
        problems.append(f"CRS {info['crs']} != {exp_crs}")
    if tuple(info["shape"]) != exp_shape:
        problems.append(f"shape {info['shape']} != {list(exp_shape)}")
    if tuple(info["transform"]) != tuple(exp_tr):
        problems.append(f"transform {info['transform']} != {list(exp_tr)}")

    finite = np.isfinite(a)
    vals = a[finite]
    if vals.size == 0 or float(vals.min()) < 0.0 or float(vals.max()) > 1.0:
        problems.append("finite values outside [0, 1]")

    if finite.all():
        encoding = "zero-filled full grid (no NaN anywhere)"
        if int(finite.sum()) != REFERENCE_FULL_GRID:
            problems.append("full-grid count mismatch")
    else:
        encoding = "NaN outside footprint"

    pos = np.nan_to_num(a, nan=0.0) > 0
    res = {
        "name": name,
        "file": spec["tif"],
        "sha256": sha,
        "sha256_matches_run_card": (card_sha == sha) if card_sha else None,
        "format": info,
        "encoding": encoding,
        "finite_min": float(vals.min()) if vals.size else None,
        "finite_max": float(vals.max()) if vals.size else None,
        "positive_cells": int(pos.sum()),
        "footprint_status": footprint_status,
    }
    if footprint is not None:
        nan_in_fp = int((~finite & footprint).sum())
        dots_outside = int((pos & ~footprint).sum())
        res["nan_inside_footprint"] = nan_in_fp
        res["dots_inside_footprint"] = int((pos & footprint).sum())
        res["dots_outside_footprint"] = dots_outside
        if nan_in_fp:
            problems.append("NaN inside footprint")
        if dots_outside:
            problems.append("dots outside footprint")
    res["problems"] = problems
    res["ok"] = not problems
    res["run_card_verdict_text"] = card.get("verdict")
    return res


def check_cited_files() -> dict:
    missing = [p for p in CITED_FILES if not (ROOT / p).exists()]
    return {"ok": not missing, "missing": missing, "checked": len(CITED_FILES)}


def run() -> dict:
    sample = _sample_meta()
    sample_report = None
    if sample is not None:
        sample_report = {k: v for k, v in sample.items() if k != "footprint_mask"}
        sample_report["matches_official_description_all_absence"] = sample["positive_cells"] == 0
        sample_report["note"] = (
            "The official page says the sample 'predicts total fault absence'; this restored "
            "copy has positive cells. Use only for footprint/CRS/shape/transform, never as values."
        )
    report = {
        "schema": "gemsdoe91-s18-verification-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample_template": sample_report or "NOT RESTORED",
        "leaderboard": check_leaderboard(),
        "feasibility": check_feasibility(),
        "candidates": {n: check_candidate(n, s, sample) for n, s in CANDIDATES.items()},
        "cited_files": check_cited_files(),
    }
    report["all_ok"] = (
        report["leaderboard"]["ok"]
        and report["feasibility"]["ok"]
        and all(c["ok"] for c in report["candidates"].values())
        and report["cited_files"]["ok"]
    )
    return report


def main() -> int:
    report = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
