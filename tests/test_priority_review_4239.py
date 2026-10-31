"""Current review must stay research-only and bind claims to saved evidence."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from gems91.novelty import SurfaceProbe
from scripts import audit_priority_snapshot, render_priority_review, render_review_20261030

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/review-4239f6e5'


def read(name):
    return json.loads((BASE / name).read_text())


def test_negative_card_distinguishes_new_candidate_from_historical_raster():
    card = read('run-card.json')
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert card['candidate_generated'] is False and card['raster_sha256'] is None
    assert card['holdout_dti'] is None and card['holdout_ci95'] is None
    assert card['leaderboard_score_estimate'] is None and card['organizer_confirmed_score'] is None
    assert card['unique_submission_name'] is None and card['submission_note'] is None
    assert card['experiments_this_review'] == card['weekly_slots_used_this_review'] == 0
    historical = card['historical_research_only']
    assert historical['ok_to_submit'] is False
    assert hashlib.sha256((ROOT / historical['raster_path']).read_bytes()).hexdigest() == historical['raster_sha256']
    assert len(historical['historical_note']) <= 140
    assert historical['holdout_evidence']['label'] == 'HOLDOUT-DTI'
    assert 'not the final static TIFF' in historical['holdout_evidence']['scope']


def test_fresh_reports_bind_sample_duplicate_and_nine_peer_values():
    pre, nine, s25, card = (read(x) for x in ('experiment-preflight.json',
                                'nine-site-leaders.json', 'historical-s25-audit.json', 'run-card.json'))
    assert pre['status'] == 'BLOCKED' and not pre['ok_to_submit']
    assert pre['capacity']['sample_semantics']['status'] == 'CONFLICT_WITH_ORGANIZER_DESCRIPTION'
    assert pre['capacity']['sample_semantics']['nonzero_inside_footprint'] == 60988
    assert pre['capacity']['overlap_lower_bound'] == pytest.approx(31005 / 37654)
    assert nine['sample_sha256'] == pre['capacity']['sample_sha256']
    assert all(nine['files'][site]['footprint_checked'] for site in nine['max_overlap_into_any_other_leader'])
    assert all(v > .70 for v in nine['max_overlap_into_any_other_leader'].values())
    assert s25['stopped_at'] == 'frozen lattice'
    assert s25['implementation_sha256'] == hashlib.sha256((ROOT / 'scripts/audit_priority_snapshot.py').read_bytes()).hexdigest()
    assert s25['validator_implementation_sha256'] == hashlib.sha256((ROOT / 'scripts/audit_downloads.py').read_bytes()).hexdigest()
    assert s25['comparisons']['frozen lattice']['dot_status'] == 'DUPLICATE'
    assert s25['comparisons']['frozen lattice']['directed_overlap_within_3px'] == pytest.approx(
        card['correlation_overlap_vs_registry']['historical_s25_final_dot_overlap_vs_lattice'])
    assert s25['complete_registry_check'] is False and s25['preplacement_surface_rechecked'] is False
    assert s25['sample_semantics']['positive_support_mismatch_pixels'] == 0


def test_shared_exact_overlap_comparison_fails_closed_on_duplicate_and_empty():
    fp = np.ones((12, 12), bool)
    candidate = np.zeros_like(fp, dtype=np.float32); candidate[4, 4] = 1
    probe = SurfaceProbe(candidate, fp)
    duplicate = audit_priority_snapshot.compare(probe, candidate, candidate, fp)
    assert duplicate['dot_status'] == duplicate['rank_status'] == 'DUPLICATE'
    empty = audit_priority_snapshot.compare(probe, candidate, np.zeros_like(candidate), fp)
    assert empty['dot_status'] == empty['rank_status'] == 'UNVERIFIED'


def test_renderer_refuses_a_promote_flag(monkeypatch):
    original = render_priority_review.load
    def mutated(path):
        data = copy.deepcopy(original(path))
        if path.endswith('/run-card.json'):
            data['ok_to_submit'] = True
        return data
    monkeypatch.setattr(render_priority_review, 'load', mutated)
    with pytest.raises(ValueError, match='inconsistent'):
        render_priority_review.render()


def test_public_frontdoor_and_guide_show_current_stop():
    # Rebuild the final active-review view after this module's historical renderer checks.
    render_review_20261030.render(ROOT)
    index = (ROOT / 'docs/index.html').read_text()
    guide = (ROOT / 'docs/submission-guide.html').read_text()
    table = (BASE / 'executive-summary.html').read_text()
    assert 'ACTIVE · 2026-10-31 (S30-VCE)' in index
    assert 'downloads/gems91-s30-vce-e2-37654dots-20261031T012142Z-0e833d44-zeros.tif' in index
    assert 's30-vce/run-card.json' in guide
    assert 'Predicted values must be in range [0, 1]' in guide
    assert '0.2778' in table and 'USER-REPORTED' in table
    assert 'No improvement' not in table or 'unproven' in table
    assert 'OK TO SUBMIT: NO' in table and 'data-submission-ready="true"' not in table
    for site in ('24', '25', '27', '28', '30', '31', '32', '33', '36'):
        assert 'GEMSDOE' + site in table


@pytest.mark.parametrize('field', ['sha256', 'blob_sha', 'repo_path',
                                    'footprint_checked', 'positive_outside_footprint'])
def test_audit_rejects_leader_report_identity_drift(field):
    nine = read('nine-site-leaders.json')['files']['GEMSDOE24']
    old = next(x for x in json.loads((ROOT / 'docs/s22/nine-site-audit.json').read_text())['sites']
               if x['site'] == 'GEMSDOE24')
    audit_priority_snapshot.verify_leader_identity('GEMSDOE24', nine, old)
    changed = dict(nine, **{field: 'forged'})
    with pytest.raises(ValueError, match='differs from the frozen leader'):
        audit_priority_snapshot.verify_leader_identity('GEMSDOE24', changed, old)
