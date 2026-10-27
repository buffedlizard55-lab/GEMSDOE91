"""S24-CCKM receipt consistency: cards must never over-claim what was run."""
import hashlib
import json
from pathlib import Path

from scripts.run_s24_cckm import allocate

ROOT = Path(__file__).resolve().parents[1]


def _load(rel):
    return json.loads((ROOT / rel).read_text())


def test_allocate_sums_to_budget_and_is_nonnegative():
    for total, areas in [(20_000, [10, 20, 30, 40]), (37_654, [1, 1, 1, 1]), (7, [3, 3, 3, 3])]:
        out = allocate(total, areas)
        assert sum(out) == total
        assert len(out) == len(areas)
        assert all(v >= 0 for v in out)


def test_run_cards_are_negative_fail_closed_and_match_bytes():
    for rel in ("docs/s24/run-card.json", "docs/s24/e2/run-card.json"):
        card = _load(rel)
        assert card["verdict"] == "negative"
        assert card["ok_to_submit"] is False
        assert card["organizer_confirmed_score"] is None
        assert card["estimated_leaderboard_score"] is None
        assert card["submission_slots_used"] == 0
        assert len(card["submission_note"]) <= 140
        h = card["holdout"]
        assert h["label"] == "HOLDOUT-DTI"
        assert h["evaluator_version"] == "gems57-pooled-hide-v2"
        assert h["n_withheld_positives"] == 60_988
        tif = ROOT / card["artifact"]["tif"]
        assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
        # Literal-registry failure must stay visible, never edited away.
        c = card["correlation_overlap_vs_registry"]
        assert c["final_dot_pass_all_incl_lattice_le_0.70"] is False
        assert c["final_dot_max_overlap_all"] > 0.70
        assert c["final_dot_pass_nine_le_0.70"] is True


def test_e2_reproduced_e1_at_20000_and_kept_selection_honest():
    e1, e2 = _load("docs/s24/run-card.json"), _load("docs/s24/e2/run-card.json")
    assert e2["holdout"]["extra_budget_arm_dti"] == e1["holdout"]["dti"]
    assert e2["experiments_run"] == 2 and e2["max_experiments"] == 3
    assert set(e2["preregistration"]["sha256"]) == {"preregistration.md", "preregistration-e2.md"}


def test_executive_summary_never_says_submit_yes():
    page = (ROOT / "docs/s24/executive-summary.html").read_text()
    assert "OK TO SUBMIT: NO" in page
    assert "OK TO SUBMIT: YES" not in page
    assert _load("docs/s24/e2/run-card.json")["artifact"]["tif"].split("/")[-1] in page
