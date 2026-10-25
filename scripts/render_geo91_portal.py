#!/usr/bin/env python3
"""Render the current fail-closed review front door from its JSON evidence.

This module keeps the historical filename for compatibility with
``scripts/render_portal.py``. It no longer publishes the stale GEO91 candidate
as current. The current pages are a review status, because no fresh experiment
or TIF was authorized in this checkout.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs/run-card-ARENA-4F073E28.json"
AUDIT = ROOT / "docs/download-audit.json"
REVALIDATION = ROOT / "docs/registry-revalidation-4F073E28.json"
INDEX_SOURCE = ROOT / "docs/current-review-index-src.html"
EXEC_SOURCE = ROOT / "docs/current-review-exec-src.html"
RESEARCH_SOURCE = ROOT / "docs/current-review-research-src.html"


def _text(value) -> str:
    return escape(str(value), quote=True)


def _display(value: float, digits: int = 6) -> str:
    return f"{float(value):.{digits}f}"


def _render(source: Path, replacements: dict[str, str]) -> str:
    text = source.read_text(encoding="utf-8")
    for token, value in replacements.items():
        text = text.replace("{{" + token + "}}", value)
    unresolved = [token for token in text.split("{{")[1:]]
    if unresolved:
        raise ValueError(f"Unresolved template token in {source.relative_to(ROOT)}: {unresolved[:3]}")
    return text


def render() -> None:
    card = json.loads(CARD.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    registry = json.loads(REVALIDATION.read_text(encoding="utf-8"))
    old = card["historical_research_artifact"]
    holdout = old["holdout_dti"]
    best = card["comparable_prior_holdout_best"]
    inventory = card["registry_correlation_overlap"]["inventory_scope"]
    r13 = registry["r13_reference"]
    capacity = registry["fixed_budget_capacity_bound"]
    old_dots = next(
        x for x in registry["historical_artifacts"]
        if x["artifact"] == old["path"]
    )
    missing_count = len(inventory["missing_local_references"])
    audit_rows = {row["path"]: row for row in audit["files"]}
    validation = audit_rows.get(old["path"])
    if validation is None or validation["status"] != "PASS":
        raise ValueError("Historical primary download lacks a passing technical audit")
    if validation["sha256"] != old["sha256"]:
        raise ValueError("Historical primary download hash differs from the review card")
    if card["lane"]["assigned"] or card["experiments_run"] != 0 or card["ok_to_submit"]:
        raise ValueError("Current review card is not fail-closed")
    if old_dots["status"] != "DUPLICATE" or audit["ok_to_submit"]:
        raise ValueError("Current duplicate/submit verdict is inconsistent")
    if len(card["submission_note"]) > 140:
        raise ValueError("Review note exceeds the 140-character limit")

    tif_rel = old["path"].removeprefix("docs/")
    historical_card = json.loads((ROOT / "docs/run-card-unique-offcatalogue-damagezone.json").read_text(encoding="utf-8"))
    zip_path = historical_card["files"]["zip"]
    zip_rel = zip_path.removeprefix("docs/")
    common = {
        "HISTORICAL_NAME": _text(card["historical_research_artifact"]["submission_name"]),
        "HISTORICAL_TIF": _text(tif_rel),
        "HISTORICAL_ZIP": _text(zip_rel),
        "HISTORICAL_SHA": _text(old["sha256"]),
        "HISTORICAL_DOTS": str(old_dots["candidate_dots"]),
        "HISTORICAL_DTI": _display(holdout["value"]),
        "HISTORICAL_CI_LOW": _display(holdout["ci95"][0]),
        "HISTORICAL_CI_HIGH": _display(holdout["ci95"][1]),
        "HISTORICAL_EVALUATOR": _text(holdout["evaluator_version"]),
        "HISTORICAL_WITHHELD": f"{holdout['withheld_positives']:,}",
        "DAMAGEZONE_OVERLAP_PCT": _display(old_dots["overlap_within_3px"] * 100, 4),
        "MISSING_REGISTRY": str(missing_count),
        "RESTORED_REGISTRY": str(inventory["pinned_remote_rasters_restored"]),
        "R13_DOTS": f"{r13['dots_in_footprint']:,}",
        "R13_UNCOVERED": f"{r13['cells_more_than_3px_from_dots']:,}",
        "CAPACITY_BOUND_PCT": _display(capacity["minimum_overlap_with_r13"] * 100, 2),
        "BEST_HOLDOUT": _display(best["value"]),
        "BEST_CI_LOW": _display(best["ci95"][0]),
        "BEST_CI_HIGH": _display(best["ci95"][1]),
        "BEST_EVALUATOR": _text(best["evaluator_version"]),
        "BEST_WITHHELD": f"{best['withheld_positives']:,}",
        "AUDIT_FILES": str(audit["files_checked"]),
        "AUDIT_PASS": str(audit["format_pass"]),
        "AUDIT_FAIL": str(audit["format_fail"]),
    }
    (ROOT / "docs/index.html").write_text(_render(INDEX_SOURCE, common), encoding="utf-8")
    (ROOT / "docs/executive-summary.html").write_text(_render(EXEC_SOURCE, common), encoding="utf-8")
    (ROOT / "docs/research.html").write_text(_render(RESEARCH_SOURCE, {}), encoding="utf-8")
    current = {
        "run_card": CARD.name,
        "review_status": card["review_status"],
        "fresh_candidate_generated": False,
        "ok_to_download": bool(old["ok_to_download"]),
        "ok_to_submit": False,
        "raster_sha256": None,
        "historical_research_artifact": {
            "path": old["path"],
            "sha256": old["sha256"],
            "ok_to_download": bool(old["ok_to_download"]),
            "ok_to_submit": False,
        },
    }
    (ROOT / "docs/current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
