from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

def test_site_distinguishes_prior_artifact_from_earlier_no_run():
    for page in ("docs/index.html", "docs/executive-summary.html"):
        text = (ROOT / page).read_text()
        assert "prior S24 session" in text
        assert "NO NEW TIFF IN THIS EARLIER REVIEW" in text
        assert "OK TO SUBMIT: NO" in text
        assert "S24 subsequently tested the first proposal" in text

def test_negative_card_never_implies_candidate_or_score():
    card = json.loads((ROOT / "docs/run-card-review-20261028.json").read_text())
    assert card["verdict"] == "negative"
    assert all(card[key] is None for key in ("holdout_dti", "raster_sha256", "submission_name"))
