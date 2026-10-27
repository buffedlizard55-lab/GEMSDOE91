"""Audit evidence and fail-closed UI tests; no geological experiment."""
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest
from scripts import audit_fleet, audit_focus_sites, render_review_8e8d86f2 as renderer

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/review-8e8d86f2'


def read(name):
    return json.loads((REVIEW / name).read_text())


def test_current_review_never_fabricates_new_candidate_or_score():
    card = read('run-card.json')
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    assert card['experiments_run'] == card['slots_used_this_review'] == 0
    assert card['candidate_generated'] is False
    for name in ('raster_sha256', 'validator_output', 'holdout_dti', 'holdout_ci95',
                 'submission_name', 'submission_note', 'organizer_confirmed_score', 'leaderboard_score_estimate'):
        assert card[name] is None
    assert card['correlation_overlap_vs_registry']['new_candidate_dot_overlap_within_3px'] is None


def test_receipts_explain_duplicate_and_geometric_block():
    pre = read('experiment-preflight.json')
    wit = read('s18-witness.json')
    b = pre['capacity']
    assert pre['status'] == 'BLOCKED' and pre['candidate_generated'] is False
    assert b['candidate_budget'] == 37654 and b['uncovered_pixels'] == 6649
    assert b['overlap_lower_bound'] == pytest.approx(31005 / 37654)
    assert wit['witness_sha256'] == b['reference_sha256']
    dots = wit['directed_dot_overlap']
    assert dots['candidate_dots'] == 20000 and dots['overlap_within_3px'] == pytest.approx(19921 / 20000)
    assert wit['status'] == 'DUPLICATE_STOP' and wit['complete_registry_clearance'] is False


def test_feature_receipt_is_inside_footprint_and_scientifically_invalidates_s22():
    feature = read('feature-audit.json')
    assert feature['status'] == 'FAIL_CLOSED' and feature['is_geological_experiment'] is False
    assert [b['band'] for b in feature['bands']] == [13, 14]
    assert all(b['masked_or_nonfinite_inside'] == b['finite_extreme_inside'] == 3061 for b in feature['bands'])
    assert 'INVALID_AS_GEOLOGICAL_FEATURE_TEST' in read('run-card.json')['historical_s22_research_artifact']['scientific_validity']


@pytest.mark.parametrize('mutation', ['promote', 'invent_raster', 'pass_input', 'drop_band', 'accept_receipt', 'mismatch_witness'])
def test_renderer_refuses_contradictory_evidence(monkeypatch, mutation):
    original = renderer.load
    def changed(name):
        x = copy.deepcopy(original(name))
        if name == 'review-8e8d86f2/run-card.json':
            if mutation == 'promote': x['ok_to_submit'] = True
            if mutation == 'invent_raster': x['raster_sha256'] = 'a' * 64
        if name == 'review-8e8d86f2/feature-audit.json':
            if mutation == 'pass_input': x['status'] = 'PASS'
            if mutation == 'drop_band': x['bands'].pop()
        if name == 's22/nine-site-audit.json' and mutation == 'accept_receipt':
            x['sites'][0]['organizer_confirmed_score'] = .9
        if name == 'review-8e8d86f2/s18-witness.json' and mutation == 'mismatch_witness':
            x['witness_sha256'] = 'b' * 64
        return x
    monkeypatch.setattr(renderer, 'load', changed)
    with pytest.raises(ValueError, match='inconsistent'):
        renderer.render_sources()


def test_legacy_generator_fails_closed_without_writing(tmp_path):
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/generate_unique_tif.py')],
                          cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 1
    assert json.loads(proc.stdout)['status'] == 'BLOCKED'
    assert json.loads(proc.stdout)['new_candidate_generated'] is False
    assert not list(tmp_path.iterdir())


def test_focus_inventory_exposes_failures_and_never_receipts(monkeypatch):
    def fake(number):
        return {'repository': f'buffedlizard55-lab/GEMSDOE{number}',
                'status': 'UNVERIFIED', 'organizer_confirmed_scores': [], 'error': 'offline'}
    monkeypatch.setattr(audit_focus_sites, 'audit', fake)
    out = audit_focus_sites.capture(workers=1)
    assert len(out['rows']) == 9 and out['complete_universal_registry'] is False
    assert all(x['status'] == 'UNVERIFIED' and not x['organizer_confirmed_scores'] for x in out['rows'])
    with pytest.raises(ValueError):
        audit_focus_sites.capture(workers=0)


def test_missing_github_executable_is_unverified_not_a_success(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError('gh unavailable')
    monkeypatch.setattr(audit_fleet, 'api', missing)
    result = audit_fleet.audit(24)
    assert result['status'] == 'UNVERIFIED' and 'gh unavailable' in result['error']
    assert result['organizer_confirmed_scores'] == []
