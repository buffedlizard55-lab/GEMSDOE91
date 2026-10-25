"""Current review deliverables must remain explicit, measured and fail-closed."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_current_review_card_is_a_negative_without_fabricated_new_score_or_raster():
    card = load("docs/run-card-ARENA-4F073E28.json")
    assert card["review_status"] == "BLOCKED_BEFORE_EXPERIMENT"
    assert card["lane"]["assigned"] is False
    assert card["experiments_run"] == 0
    assert card["raster_sha256"] is None
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["status"] == "NOT_RUN_IN_THIS_REVIEW"
    assert card["holdout_dti"]["value"] is None
    assert card["organizer_confirmed"] is None
    assert card["selector_approval"] is False
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert 0 < len(card["submission_note"]) <= 140
    assert card["submission_note_length"] == len(card["submission_note"])
    assert card["historical_research_artifact"]["freshly_generated"] is False
    assert len(card["ranked_shortlist"]) == 4
    assert [h["rank"] for h in card["ranked_shortlist"]] == [1, 2, 3, 4]
    assert all(h["status"].endswith("NOT_RUN") for h in card["ranked_shortlist"])
    assert all(h["named_non_fault_mimic"] for h in card["ranked_shortlist"])


def test_pinned_registry_revalidation_matches_the_card_and_stops_on_overlap():
    card = load("docs/run-card-ARENA-4F073E28.json")
    report = load("docs/registry-revalidation-4F073E28.json")
    assert report["ok_to_submit"] is False
    assert report["verdict"] == "negative"
    assert report["frozen_inventory"]["complete_universal_registry"] is False
    assert len(report["historical_artifacts"]) == 3
    assert report["r13_reference"]["dots_in_footprint"] == 206895
    assert report["r13_reference"]["cells_more_than_3px_from_dots"] == 6649
    assert report["fixed_budget_capacity_bound"]["feasible"] is False
    assert report["fixed_budget_capacity_bound"]["minimum_overlap_with_r13"] > 0.70
    current = card["registry_correlation_overlap"]["historical_artifact_rechecks"]
    assert len(current) == len(report["historical_artifacts"])
    for a, b in zip(current, report["historical_artifacts"]):
        assert a["artifact"] == b["artifact"]
        assert a["sha256"] == b["sha256"]
        assert a["candidate_dots"] == b["candidate_dots"]
        assert a["candidate_dots_within_3px"] == b["candidate_dots_within_3px"]
        assert a["overlap_within_3px"] == b["overlap_within_3px"]
        assert a["final_dot_spearman"] == b["final_dot_spearman"]
        assert b["status"] == "DUPLICATE"


def test_download_audit_cannot_promote_on_technical_format_pass_alone():
    audit = load("docs/download-audit.json")
    assert audit["files_checked"] == 62
    assert audit["format_pass"] == 54
    assert audit["format_fail"] == 8
    assert audit["ok_to_submit"] is False
    card = load("docs/run-card-ARENA-4F073E28.json")
    assert card["historical_research_artifact"]["technical_validation"]["status"] == "PASS"
    assert card["historical_research_artifact"]["ok_to_submit"] is False


def test_review_portal_renderer_is_deterministic_and_publishes_no_new_raster():
    page_paths = [
        ROOT / "docs/index.html",
        ROOT / "docs/executive-summary.html",
        ROOT / "docs/research.html",
        ROOT / "docs/current-run.json",
    ]
    before = [p.read_bytes() for p in page_paths]
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/render_geo91_portal.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert before == [p.read_bytes() for p in page_paths]
    current = load("docs/current-run.json")
    assert current["fresh_candidate_generated"] is False
    assert current["raster_sha256"] is None
    assert current["ok_to_submit"] is False


@pytest.mark.skipif(
    not (ROOT / "data/official/sample_submission.tif").is_file()
    or not (ROOT / "data/fleet_registry/r13_lattice_s5_00904.tif").is_file(),
    reason="Pinned ignored rasters are optional in source-only CI",
)
def test_dense_registry_audit_recomputes_from_hash_pinned_rasters():
    from audit_dense_registry_conflict import audit
    regenerated = audit()
    saved = load("docs/registry-revalidation-4F073E28.json")
    assert regenerated == saved
