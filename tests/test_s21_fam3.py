"""S21-FAM3 invariants: downloaded bytes, verdict derived from gates, uniqueness evidence,
instrument recomputation, portal verdict strings."""
import hashlib, json, zipfile
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "docs/run-card-S21-FAM3.json").read_text())
SUB = CARD["submission"]


def test_tiff_bytes_values_and_zip():
    tif = ROOT / SUB["file"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == SUB["sha256"] == CARD["raster_sha256"]
    with tifffile.TiffFile(tif) as tf:
        page = tf.pages[0]
        a = page.asarray()
        assert tf.geotiff_metadata["GTCitationGeoKey"] == "WGS 84 / UTM zone 11N"
    assert a.shape == (3730, 3292) and a.dtype == np.float32
    assert np.isfinite(a).all() and set(np.unique(a).tolist()) <= {0.0, 1.0}
    assert int((a > 0).sum()) == SUB["n_dots"]
    with zipfile.ZipFile(ROOT / SUB["zip"]) as z:
        (m,) = z.infolist()
        assert z.read(m) == tif.read_bytes()
    assert len(SUB["note"]) == SUB["note_chars"] <= 140
    assert CARD["validator_output"]["all_checks_passed"] is True


def test_verdict_derived_from_gates_not_hand_set():
    G = CARD["gates"]
    assert CARD["ok_to_download"] == (G["G1_format"] and G["G2_uniqueness"])
    assert CARD["ok_to_submit"] == all(G.values())
    assert CARD["verdict"] == ("promote" if CARD["ok_to_submit"] else "negative")
    assert CARD["s21_preregistered_gates_all_pass"] == CARD["ok_to_submit"]
    assert CARD["organizer_confirmed"] is None and CARD["slots_used"] == 0
    # measured outcome: exactly G4 fails
    assert [k for k, v in G.items() if not v] == ["G4_surrogate_projection"]


def test_g4_rule_recomputed_from_evidence():
    proj = CARD["evidence"]["projection_G4"]
    assert sum(v["boot_delta_ci95"][0] > 0 for v in proj.values()) == 0
    assert not all(v["p_delta_gt0"] >= 0.95 for v in proj.values())
    assert CARD["gates"]["G4_surrogate_projection"] is False
    p1 = CARD["evidence"]["projection_G4_pass1"]["variants"]
    assert sum(v["boot_delta_ci95"][0] > 0 for v in p1.values()) >= 2
    assert all(v["p_delta_gt0"] >= 0.95 for v in p1.values())
    # pass-1 projections are strictly above final in every variant: caps cost skill
    assert all(p1[k]["delta"] > proj[k]["delta"] for k in proj)


def test_uniqueness_evidence_matches_file():
    for name in ("docs/s21/registry-check.json", "docs/s21/sibling-check.json"):
        r = json.loads((ROOT / name).read_text())
        assert r["candidate_sha256"] == SUB["sha256"] and r["verdict"] == "UNIQUE" and r["duplicates"] == []
        assert r["max_literal_sparse"]["within_3px_literal"] is not None
    p1 = json.loads((ROOT / "docs/s21/pass1-sibling-check.json").read_text())
    assert p1["verdict"] == "DUPLICATE-STOP" and len(p1["duplicates"]) == 7
    surf = json.loads((ROOT / "docs/s21/surface-precheck.json").read_text())
    assert surf["verdict"] == "PASS" and surf["max_surface_abs_spearman"] <= 0.90


def test_holdout_zero_is_structural_and_canaries_pass():
    h = CARD["evidence"]["holdout_dti_hide_v2"]
    assert h["candidate"]["tpw"] == 0.0 and h["candidate"]["dti"] == 0.0
    assert h["candidate"]["fpw"] == SUB["n_dots"]
    assert h["withheld_positives"] == 60_988 and h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert max(v["symmetric_auc"] for v in CARD["evidence"]["canaries"].values()) <= 0.90
    iv = CARD["evidence"]["instrument_validity"]
    assert iv["split_matches_s20"] is True and iv["spearman_hide_v2_vs_live"] == -1.0


def test_negative_design_component_disclosed():
    e1 = CARD["evidence"]["surrogate_E1"]
    assert e1["ridge10"]["loso_rmse"] > e1["s20_design_stored"]["loso_rmse"]
    assert e1["ridge10"]["loso_spearman"] < e1["s20_design_stored"]["loso_spearman"]


def test_portal_banner_and_summary_match_card():
    page = (ROOT / "docs/index.html").read_text()
    assert Path(SUB["file"]).name in page and SUB["sha256"] in page and SUB["name"] in page
    assert f'data-submission-ready="{str(CARD["ok_to_submit"]).lower()}"' in page
    assert "OK TO SUBMIT: NO" in page and "S21-FAM3" in page
    guide = (ROOT / "docs/s21-fam3-executive-summary.html").read_text()
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"):
        assert site in guide
    assert "0.2778" in guide and "HOLDOUT-DTI" in guide and "PROJECTION" in guide


def test_forensics_key_relations():
    f = json.loads((ROOT / "docs/s21/nine-site-forensics.json").read_text())
    rel = f["relations"]
    assert rel["GEMSDOE36_extra_dots_over_R0"] == 1200 and rel["GEMSDOE36_is_superset_of_R0"] is True
    n33 = f["rows"]["GEMSDOE33_tipstepover_fallback"]["n_dots"]
    assert rel["GEMSDOE33_dots_on_h19_5_network_px"] / n33 > 0.99
    assert rel["R0_equals_solo_with_dcat_gt_2px"] is True
