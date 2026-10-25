"""S17-EULR fail-closed integrity: the negative verdict and published bytes
must stay consistent with docs/run-card-S17-EULR.json forever."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "docs/run-card-S17-EULR.json").read_text(encoding="utf-8"))
TIF = ROOT / CARD["artifact"]["primary_zeros_tif"]
ZIP = ROOT / CARD["artifact"]["zip_bundle"]


def test_artifact_bytes_match_card_and_policy():
    data = TIF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == CARD["raster_sha256"]
    assert len(data) == CARD["artifact"]["primary_zeros_bytes"]
    zdata = ZIP.read_bytes()
    assert hashlib.sha256(zdata).hexdigest() == CARD["artifact"]["zip_sha256"]
    with zipfile.ZipFile(ZIP) as z:
        assert len(z.namelist()) == 1 and z.testzip() is None
        assert hashlib.sha256(z.read(z.namelist()[0])).hexdigest() == CARD["raster_sha256"]
    policy = json.loads((ROOT / "registry/artifact_policy.json").read_text(encoding="utf-8"))
    reg = {r["path"]: r["sha256"] for r in policy["files"]}
    assert reg[CARD["artifact"]["primary_zeros_tif"]] == CARD["raster_sha256"]
    assert reg[CARD["artifact"]["zip_bundle"]] == CARD["artifact"]["zip_sha256"]


def test_verdict_stays_negative_and_gates_honest():
    assert CARD["technical_candidate_verdict"] == "negative"
    assert CARD["ok_to_submit"] == "NO"
    assert CARD["submission_ready"] is False
    g = CARD["readiness_gates"]
    assert g["format"] is True and g["canary"] is True
    assert g["novelty"] is False and g["assigned_lane"] is False
    assert g["beats_comparable_best"] is False and g["separate_selector"] is False
    # The Euler ablation CI includes zero: the null result is the deliverable.
    ab = CARD["scientific_readout_euler_ablation"]["paired_e2_minus_e1"]
    assert ab["ci95"][0] < 0 < ab["ci95"][1]
    assert CARD["holdout_dti"]["value"] < CARD["comparable_prior_holdout_best"]["value"]
    assert CARD["holdout_dti"]["evaluator_version"] == "gems91-hide-recover-v1.0"
    assert CARD["holdout_dti"]["withheld_positives"] == 60_988
    assert CARD["registry_comparison"]["complete_universal_registry"] is False
    assert CARD["registry_comparison"]["final"]["summary"]["vs_r0_claim_leader"]["cand_within_3px_of_reg"] < 0.70
    assert len(CARD["submission"]["note"]) <= 140


def test_site_shows_s17_with_no_submit_verdict():
    for name in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "S17-EULR" in text and "NOT OK TO SUBMIT" in text
        assert CARD["artifact"]["primary_zeros_tif"].split("/")[-1] in text
        assert "run-card-S17-EULR.json" in text
        assert "OK TO SUBMIT: YES" not in text
