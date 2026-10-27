"""Current checkout front door must stay consistent with the negative run card."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_review_card_is_negative_and_note_is_within_limit():
    card = json.loads((ROOT / "docs/run-card-ARENA-35E82D42-20261027.json").read_text())
    assert card["experiment_performed_this_review"] is False
    assert card["verdict"] == "negative"
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["organizer_confirmed_score"] is None
    assert card["estimated_leaderboard_score"] is None
    assert card["prior_experiment_evidence"]["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["prior_experiment_evidence"]["holdout"]["withheld_positive_pixels"] == 60988
    assert 0 < len(card["submission_note"]) <= 140
    assert card["submission_note_character_count"] == len(card["submission_note"])


def test_current_portal_and_executive_summary_do_not_advertise_submission_approval():
    pointer = json.loads((ROOT / "docs/current-run.json").read_text())
    assert pointer["ok_to_download"] is True
    assert pointer["ok_to_submit"] is False
    for name in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / name).read_text()
        assert "OK TO SUBMIT: NO" in text
        assert "OK TO DOWNLOAD: YES" in text
        assert "NOT OK TO SUBMIT" in text
        assert "research" in text.lower()
        assert "82.34%" in text
        assert "capacity-preflight.json" in text
    assert "No calibrated estimate or receipt" in (ROOT / "docs/executive-summary.html").read_text()


def test_nine_focus_site_values_are_user_claims_and_all_fail_peer_uniqueness():
    audit = json.loads((ROOT / "docs/s22-xb/nine-sites.json").read_text())
    expected = {
        "GEMSDOE24": 0.2477,
        "GEMSDOE25": 0.2600,
        "GEMSDOE27": 0.2449,
        "GEMSDOE28": 0.2710,
        "GEMSDOE30": 0.2600,
        "GEMSDOE31": 0.2708,
        "GEMSDOE32": 0.2778,
        "GEMSDOE33": 0.2632,
        "GEMSDOE36": 0.2750,
    }
    assert {row["site"]: row["user_reported_public_dti"] for row in audit["rows"]} == expected
    assert all(row["evidence_class"] == "USER-REPORTED" for row in audit["rows"])
    assert set(audit["uniqueness_among_nine"]) == set(expected)
    assert all(row["share_within_3px_of_any_other_of_the_nine"] > 0.70
               for row in audit["uniqueness_among_nine"].values())


def test_capacity_bound_matches_frozen_registry_and_is_not_a_score():
    capacity = json.loads((ROOT / "docs/s22/capacity-preflight.json").read_text())
    cap = capacity["capacity"]
    inventory = json.loads((ROOT / "registry/comparison_inventory.json").read_text())
    witness = next(row for row in inventory["files"] if row["path"] == cap["reference_path"])
    manifest = json.loads((ROOT / "registry/data_manifest.json").read_text())
    sample = next(row for row in manifest["files"] if row["id"] == "sample_submission")
    assert capacity["status"] == "BLOCKED"
    assert capacity["candidate_generated"] is False
    assert cap["evidence_class"] == "GEOMETRIC_CAPACITY_BOUND_NOT_A_SCORE"
    assert cap["reference_sha256"] == witness["sha256"]
    assert cap["sample_sha256"] == sample["sha256"]
    assert cap["complete_registry_check"] is False
    assert cap["candidate_budget"] == 37654
    assert cap["overlap_lower_bound"] > cap["threshold"] == 0.70
    assert cap["feasible_by_capacity_only"] is False
