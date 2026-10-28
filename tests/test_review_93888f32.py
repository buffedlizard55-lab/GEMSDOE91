import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/downloads/gems91-s25-tlf-60000dots-20261028T120039Z-zeros.tif"
ZIP = ARTIFACT.with_suffix(".zip")


def test_current_status_is_fail_closed_and_has_a_machine_card():
    readme = (ROOT / "README.md").read_text()
    page = (ROOT / "docs/index.html").read_text()
    review = (ROOT / "docs/review-93888f32-20261028.md").read_text()
    card = json.loads((ROOT / "docs/run-card-93888f32-20261028.json").read_text())

    assert readme.startswith("# GEMSDOE91 — Current review: blocked, research only")
    assert "OK to submit: NO" in readme
    assert "no new candidate" in page.lower()
    assert "ok to submit: no" in page.lower()
    assert "0.36 projection" in review and "withdrawn" in review
    assert card["experiments_run"] == 0
    assert card["weekly_submission_slots_used"] == 0
    assert card["ok_to_submit"] is False
    assert card["estimated_leaderboard_score"] is None
    assert card["holdout_dti"]["dti"] is None
    assert card["validator_output"]["crs_shape_transform_match_to_official_sample"] is None


def test_historical_tif_local_integrity_and_range_are_verified():
    sidecar = json.loads(ARTIFACT.with_suffix(".json").read_text())
    digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
    assert digest == sidecar["sha256"]

    with rasterio.open(ARTIFACT) as src:
        arr = src.read(1)
        assert src.count == 1
        assert src.dtypes == ("float32",)
        assert src.crs.to_string() == "EPSG:32611"
        assert src.shape == (3730, 3292)
        assert tuple(src.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
        assert np.isfinite(arr).all()
        assert arr.min() >= 0.0 and arr.max() <= 1.0
        assert int(np.count_nonzero(arr > 0)) == 60000

    with zipfile.ZipFile(ZIP) as zf:
        assert len(zf.namelist()) == 1
        assert hashlib.sha256(zf.read(zf.namelist()[0])).hexdigest() == digest


def test_tlf_page_generator_cannot_reapprove_the_historical_artifact():
    source = (ROOT / "scripts/render_s25tlf_portal.py").read_text()
    assert "OK TO SUBMIT: NO" in source
    assert "HISTORICAL RESEARCH FILE" in source
    assert "do not submit" in source.lower()
    assert "cleared to download and submit" not in source.lower()
