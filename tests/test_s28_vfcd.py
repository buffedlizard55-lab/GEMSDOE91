"""S28-VFCD deliverable checks: unique TIF, automated verdict, run card, labels."""
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _card():
    return json.loads((DOCS / "run-card-S28-VFCD.json").read_text())


def _tifs():
    card = _card()
    return ROOT / card["raster_path"], ROOT / card["zip_path"]


def test_run_card_has_every_protocol_field_and_fail_closed_verdict():
    card = _card()
    for key in ("hypothesis", "mechanism", "named_non_fault_mimic", "holdout",
                "correlation_overlap_vs_registry", "raster_sha256", "validator_output",
                "submission_name", "submission_note"):
        assert card.get(key), key
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
    assert card["holdout"]["split_version"] == "label-blind-quadrants-v3-feature-buffered"
    assert card["holdout"]["n_withheld_positives"] == 60988
    ci = card["holdout"]["scores"]["vfcd_e3_vent_phys_cons_celf"]["ci95"]
    assert 0.0 < ci[0] < card["holdout"]["scores"]["vfcd_e3_vent_phys_cons_celf"]["dti"] < ci[1]
    assert card["leaderboard_score_estimate"]["LFI_MODEL_projection_not_a_score"]["evidence_class"] == "MODEL_PROJECTION_NOT_A_SCORE"
    assert card["organizer_confirmed_score"] is None
    assert card["verdict"]["promote"] is False
    assert card["verdict"]["OK_TO_SUBMIT"] == "NO"
    assert card["ok_to_submit"] is False and card["submission_ready"] is False
    assert card["submission_slots_used"] == 0
    assert len(card["submission_note"]) <= 140


def test_tif_is_zeros_encoded_valid_grid_and_matches_card_hash():
    import hashlib
    card = _card()
    tif, zipped = _tifs()
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zipped.read_bytes()).hexdigest() == card["zip_sha256"]
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
    assert np.isfinite(arr).all()
    assert float(arr.min()) >= 0.0 and float(arr.max()) <= 1.0
    values = np.unique(arr)
    assert set(np.round(values, 6)) <= {0.0, 1.0}
    assert int((arr > 0).sum()) == 37654
    with zipfile.ZipFile(zipped) as z:
        assert z.namelist() == [tif.name]
        assert z.read(tif.name) == tif.read_bytes()


def test_uniqueness_gates_pass_and_lattice_irregularity_is_flagged_not_dropped():
    card = _card()
    u = card["correlation_overlap_vs_registry"]
    assert u["surface_pass"] is True and u["surface_max_abs_spearman"] <= 0.90
    assert u["dots_competitive_pass"] is True and u["dots_max_3px_overlap_competitive"] <= 0.70
    assert u["dots_nine_leaders_max_3px"] <= 0.70
    assert u["dense_blanket_calibration_max_3px"] > 0.70  # reported openly
    assert "IR-S28-01" in u["irregularity"]
    final = json.loads((DOCS / "s28-vfcd/final-dot-checks.json").read_text())
    assert final["competitive_pass"] is True
    assert final["references_checked"] >= 211


def test_leakage_canary_and_preregistration_pin():
    can = json.loads((DOCS / "s28-vfcd/canaries.json").read_text())
    assert can["all_pass"] is True
    assert can["max_symmetric_auc"] <= 0.90
    assert can["threshold"] == 0.90
    assert can["n_checks"] >= 100
    import hashlib
    pre = (DOCS / "s28-vfcd/preregistration.md").read_bytes()
    assert hashlib.sha256(pre).hexdigest() == "152f1d5577256adcba9fa75488276436bf003160f902715ae587967a6763abee"


def test_experiments_used_budget_and_negative_result_recorded():
    e3 = json.loads((DOCS / "s28-vfcd/e3/holdout.json").read_text())
    names = sorted(e3["scores"])
    assert "vfcd_e3_vent_phys_cons_celf" in names and "ctrl_oof_phys" in names
    # The hypothesis lost to both controls (paired CIs strictly negative) — recorded, not hidden.
    for ctrl in ("ctrl_oof_base", "ctrl_oof_phys"):
        diff = e3["paired_differences"][ctrl]
        assert diff["ci95"][1] < 0.0
    card = _card()
    assert card["experiments_run"] == 3 and card["budget_max_experiments"] == 3
    assert card["verdict"]["protocol_verdict"] == "negative"


def test_executive_summary_states_obvious_verdict_labels_and_howto():
    page = (DOCS / "s28-vfcd/executive-summary.html").read_text()
    text = page.lower()
    for needle in ("ok to download: yes", "ok to submit", "unique", "how to submit",
                   "predicted values must be in range", "user-reported", "holdout-dti",
                   "model — not a score", "why 0.2778", "organizer-confirmed",
                   "selector step", "gemsdoe32"):
        assert needle in text, needle
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                 "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in page, site
    assert "d7843af990f1530a7eb1be2302b545eea592c09f00469371eef1334f61897bc7" in page
    assert 'href="../downloads/gems91-s28-vfcd_e3_vent_phys_cons_celf-37654dots-20261031T001943Z-13949183-zeros.tif"' in page


def test_no_projection_is_labeled_as_a_score_on_the_s28_page():
    page = (DOCS / "s28-vfcd/executive-summary.html").read_text().lower()
    # Any mention of the LFI projection must carry the not-a-score label nearby.
    assert "lfi" in page and "not a score" in page
    card = _card()
    assert card["leaderboard_score_estimate"]["HOLDOUT-DTI"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["leaderboard_score_estimate"]["LFI_MODEL_projection_not_a_score"]["evidence_class"] == "MODEL_PROJECTION_NOT_A_SCORE"


def test_artifact_policy_registers_the_new_pair_as_research_only():
    pol = json.loads((ROOT / "registry/artifact_policy.json").read_text())
    card = _card()
    rows = {r["path"]: r for r in pol["files"]}
    for rel, digest in ((card["raster_path"], card["raster_sha256"]),
                        (card["zip_path"], card["zip_sha256"])):
        assert rel in rows
        assert rows[rel]["sha256"] == digest
        assert rows[rel]["status"] == "current_research_only"
