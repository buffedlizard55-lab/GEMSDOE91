"""S25-FABRIC receipt consistency: cards must never over-claim what was run."""
import hashlib
import json
from pathlib import Path

from scripts.run_s25_fabric import allocate

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    return json.loads((ROOT / rel).read_text())


def test_allocate_sums_to_budget():
    for total, areas in [(37_654, [10, 20, 30, 40]), (37_654, [1, 1, 1, 1]), (7, [3, 3, 3, 3])]:
        out = allocate(total, areas)
        assert sum(out) == total and len(out) == len(areas) and all(v >= 0 for v in out)


def test_run_card_fail_closed_and_matches_bytes():
    card = _load("docs/s25/run-card.json")
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["organizer_confirmed_score"] is None
    assert card["estimated_leaderboard_score"] is None
    assert card["submission_slots_used"] == 0
    # Recorded value is the packaged-experiment index (2); the correction
    # receipt documents that 3 preregistered experiments actually ran.
    assert card["experiments_run"] == 2 and card["max_experiments"] == 3
    corr = _load("docs/s25/run-card-correction.json")
    assert corr["experiments_run_total"] == 3
    assert set(card["holdout"]["experiments_summary"]) == {"e1", "e2", "e3"}
    assert len(card["submission_note"]) <= 140
    h = card["holdout"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["split_version"] == "label-blind-quadrants-v3-feature-buffered"
    assert h["n_withheld_positives"] == 60_988
    assert h["beats_best_matched_control_ci95"] is True
    tif = ROOT / card["artifact"]["tif"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert card["artifact"]["n_dots"] == 37_654
    c = card["correlation_overlap_vs_registry"]
    # Nine-site uniqueness passes; literal/competitive failures stay visible.
    assert c["final_dot_pass_nine_le_0.70"] is True
    assert c["final_dot_pass_competitive_le_0.70"] is False
    assert c["final_dot_pass_all_incl_blankets_le_0.70"] is False
    assert c["final_dot_max_overlap_all"] > 0.70
    assert c["surface_pass_le_0.90"] is True
    # Preregistration hash pinned in the card must match the committed file.
    assert hashlib.sha256((ROOT / "docs/s25/preregistration.md").read_bytes()).hexdigest() \
        == card["preregistration"]["sha256"]


def test_selection_rule_picked_highest_candidate():
    d = {}
    for exp, arm in (("e1", "fabric_e1_oof_new"), ("e2", "fabric_e2_oof_full"),
                     ("e3", "fabric_e3_oof_bagged")):
        d[exp] = _load(f"docs/s25/{exp}/holdout.json")["scores"][arm]["dti"]
    assert d["e2"] == max(d.values())
    card = _load("docs/s25/run-card.json")
    assert card["holdout"]["dti"] == d["e2"]


def test_diagnostics_are_labelled_models_not_scores():
    diag = _load("docs/s25/diagnostics.json")
    assert diag["lfi"]["label_class"] == "MODEL_PROJECTION_NOT_A_SCORE"
    assert diag["candidate"]["organizer_confirmed_score"] is None
    cand = [r for r in diag["lfi"]["rows"] if r["name"] == "s25_fabric_e2_candidate"][0]
    assert cand["sha256"] == _load("docs/s25/run-card.json")["raster_sha256"]
    assert diag["lfi"]["anchor_set"]["set_sha256"]


def test_executive_summary_and_front_door_never_say_submit_yes():
    for rel in ("docs/s25/executive-summary.html", "docs/index.html"):
        page = (ROOT / rel).read_text()
        assert "OK TO SUBMIT: NO" in page, rel
        assert "OK TO SUBMIT: YES" not in page, rel
    page = (ROOT / "docs/s25/executive-summary.html").read_text()
    assert _load("docs/s25/run-card.json")["artifact"]["tif"].split("/")[-1] in page
    assert "MODEL_PROJECTION_NOT_A_SCORE" not in page or "not a score" in page


def test_canaries_pass_recorded():
    can = _load("docs/s25/canaries.json")
    assert can["all_pass"] is True
    assert can["max_symmetric_auc"] <= 0.90
    assert can["split_version"] == "label-blind-quadrants-v3-feature-buffered"
