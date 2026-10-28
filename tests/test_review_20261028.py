"""Current review stays fail-closed; old artifacts are not current candidates."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_current_run_card_records_absence_not_a_claimed_score():
    card = json.loads((ROOT / 'docs/run-card-20261028.json').read_text())
    assert card['verdict'] == 'negative'
    assert card['ok_to_submit'] is False
    assert card['experiments_run'] == 0
    assert card['raster_sha256'] is None
    assert card['holdout']['dti'] is None
    assert card['estimated_leaderboard_score'] is None


def test_entry_points_do_not_present_historical_result_as_current():
    site = (ROOT / 'docs/index.html').read_text()
    page = (ROOT / 'docs/s24/executive-summary.html').read_text()
    assert '2026-10-28 current review: no new candidate' in site
    assert 'generated in the 2026-10-27 session' in site
    assert 'not a matched evaluation under the' in page
    assert 'do not rerun without preflight' in page
    assert 'python scripts/run_s24_cckm.py' not in page
