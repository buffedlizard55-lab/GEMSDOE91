"""S28-VSD lane deliverable guards: pages render idempotently, carry the exact
download, evidence labels, and fail-closed status strings; the raster and its
ZIP hash-match the writer receipt; the portal card insertion is non-destructive
to the pinned 2026-10-30 banner markers."""
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
S28 = ROOT / "docs" / "s28-vsd"


@pytest.fixture(scope="module")
def card():
    return json.loads((S28 / "run-card.json").read_text())


def test_run_card_verdict_and_evidence_fields(card):
    assert card["schema"] == "gems-parallel-run-card-v1"
    assert card["assigned_lane"] is True
    assert card["budget_cap_experiments"] == 3 and card["experiments_run"] <= 3
    assert card["weekly_submission_slots_used"] == 0
    assert card["verdict"] in {"promote", "negative"}
    h = card["holdout"]
    assert h["label"] == "HOLDOUT-DTI" and h["n_withheld_positives"] > 0
    assert len(h["ci95"]) == 2 and h["ci95"][0] <= h["dti"] <= h["ci95"][1]
    assert card["organizer_confirmed"]["score"] is None
    assert len(card["submission_note"]) <= 140
    v = card["validator_output"]
    assert v["values_in_unit_range"] and v["no_nan_inside_footprint"] and v["crs_shape_transform_match"]


def test_raster_bytes_match_receipt(card):
    receipt = json.loads((S28 / "writer-receipt.json").read_text())
    tif = ROOT / receipt["file"]
    zipped = ROOT / receipt["zip"]
    assert tif.is_file() and zipped.is_file()
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(tif) == receipt["sha256"] == card["raster_sha256"]
    assert sha(zipped) == receipt["zip_sha256"]


def test_executive_summary_is_download_first_and_labeled():
    page = (S28 / "executive-summary.html").read_text(encoding="utf-8")
    assert "DOWNLOAD THIS FILE" in page
    assert 'href="../downloads/gems91-s28-vsd-e3-37654dots' in page  # relative links from docs/s28-vsd/
    for label in ("HOLDOUT-DTI", "USER-REPORTED_PUBLIC_DTI", "MODEL_PROJECTION_NOT_A_SCORE",
                  "ORGANIZER-CONFIRMED", "SGMC-OFFCAT-CONTROL-DTI"):
        assert label in page
    assert "Predicted values must be in range" not in page  # guide covers the error, summary must not trigger it
    low = page.lower()
    assert "ok to submit" in low and "ok to download" in low


def test_submission_guide_has_name_note_and_nan_warning():
    guide = (S28 / "submission-guide.html").read_text(encoding="utf-8")
    card = json.loads((S28 / "run-card.json").read_text())
    assert card["submission_note"] in guide
    assert "-zeros" in guide and "nan" in guide
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/submit/" in guide


def _ensure_portal_state():
    """Re-establish the current lane's portal state before asserting on it.

    Historical tests legitimately rewrite docs/index.html from their own frozen
    templates; render_portal.py restores the pinned 2026-10-30 banner and
    re-inserts the S28-VSD status block deterministically.
    """
    import subprocess
    import sys
    subprocess.run([sys.executable, str(ROOT / "scripts" / "render_portal.py")], check=True, cwd=ROOT)


def test_portal_insertion_preserves_pinned_banner():
    _ensure_portal_state()
    index = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "ACTIVE REVIEW · 2026-10-30" in index  # pinned marker must survive
    assert "ACTIVE STATUS · 2026-10-31" in index
    assert "review-20261030/run-card.json" in index
    assert "gems91-s28-vsd-e3-37654dots" in index


def test_s28_renderer_is_idempotent():
    import subprocess
    import sys
    _ensure_portal_state()  # normalize state that earlier test files may have rewritten
    paths = [S28 / "executive-summary.html", S28 / "submission-guide.html", ROOT / "docs" / "index.html"]
    before = {p: p.read_bytes() for p in paths}
    for script in ("scripts/render_s28_pages.py", "scripts/render_s28_portal.py"):
        subprocess.run([sys.executable, str(ROOT / script)], check=True, cwd=ROOT)
    assert before == {p: p.read_bytes() for p in paths}


def test_session_prompt_preserved():
    prompt = (ROOT / "docs" / "SESSION_PROMPT_20261031.md").read_text(encoding="utf-8")
    assert "PARALLEL-RUN PROTOCOL" in prompt
    assert "MUST GENERATE A UNIQUE TIF SUBMISSION" in prompt
    assert "0.2778" in prompt and "0.2710" in prompt and "0.2750" in prompt
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/SESSION_PROMPT_20261031.md" in readme
    assert "ACTIVE BRANCH: `arena/e5d5b72d-gemsdoe91`" in readme
    assert "ACTIVE BRANCH: `arena/83350cee-gemsdoe91`" in readme  # historical banner retained
