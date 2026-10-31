"""Independent review receipts and safety invariants; no model or slot run."""
import hashlib
import json
from pathlib import Path

import pytest

from gems91.readiness import gates, submission_ready
from scripts.source_integrity import verify_historical_source
from scripts import render_review_20261030

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/review-ad43b4e5'


def read(name):
    # Reject JavaScript-only NaN/Infinity tokens as well as invalid JSON.
    def bad(token):
        raise ValueError('non-standard JSON token: ' + token)
    return json.loads((REVIEW / name).read_text(), parse_constant=bad)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_current_negative_run_card_never_conflates_historical_file_with_candidate():
    card = read('run-card.json')
    assert card['verdict'] == 'negative'
    assert card['candidate_generated'] is False and card['ok_to_submit'] is False
    assert card['experiments_run'] == 0 and card['slots_used_this_review'] == 0
    for key in ('raster_sha256', 'validator_output', 'holdout_dti', 'holdout_ci95',
                'submission_name', 'submission_note', 'leaderboard_score_estimate'):
        assert card[key] is None
    assert not submission_ready(card) and not gates(card)['buffered_context']
    old = card['historical_s22_research_artifact']
    assert old['not_created_in_this_review'] and old['ok_to_submit'] is False
    assert old['sha256'] == digest(ROOT / old['tif'])
    assert old['validation']['status'] == 'PASS'
    assert old['duplicate_stop_witness'] == 'DUPLICATE_STOP'


def test_context_diagnostic_matches_current_and_archived_hashes():
    audit = read('context-buffer-audit.json')
    pins = json.loads((ROOT / 'registry/template_pin.json').read_text())
    assert audit['historical_spatial_sha256'] == pins['upstream_sha256']['spatial.py']
    assert audit['corrected_spatial_sha256'] == pins['sha256']['spatial.py']
    assert audit['geological_experiments_run'] == 0
    assert [row['historical_withheld_pixels_with_visible_within_buffer'] for row in audit['rows']] == [2240, 911, 1908, 1516]
    assert all(row['corrected_nearest_visible_to_any_held_component_px'] > audit['buffer_px']
               and row['corrected_known_pixel_mask_preserved']
               and row['evaluation_geometry_unchanged'] for row in audit['rows'])


def test_corrected_source_manifest_authenticates_both_versions():
    manifest = read('source-corrections.json')
    for name, entry in manifest['files'].items():
        assert digest(ROOT / name) == entry['current_sha256']
        assert digest(ROOT / entry['historical_source_archive']) == entry['historical_sha256']
    for name in ('src/gems91/readiness.py', 'scripts/run_s22_omtj.py'):
        entry = manifest['files'][name]
        verify_historical_source(ROOT, name, entry['historical_sha256'])


def test_lineage_and_peer_recheck_are_separate_from_score_claims():
    lineage = read('nine-site-lineage.json')
    assert lineage['evidence_class'] == 'HISTORICAL_SUPPORT_GEOMETRY_NOT_A_SCORE'
    assert lineage['25_and_30_identical_support']
    assert lineage['31_subset_of_25'] and lineage['32_subset_of_31'] and lineage['32_subset_of_36']
    assert [lineage[k]['pixels'] for k in ('25_minus_31', '31_minus_32', '36_minus_32')] == [3891, 2545, 1200]
    peers = read('nine-site-recheck.json')
    names = set(peers['max_overlap_into_any_other_leader'])
    assert len(names) == 9
    for site in names:
        recomputed = max(peers['overlap_pairs'][f'{site} -> {other}'] for other in names - {site})
        assert peers['max_overlap_into_any_other_leader'][site] == pytest.approx(recomputed, abs=1e-15)
        assert recomputed > .70
    assert all(peers['files'][site]['sha256'] == row['sha256']
               for site, row in lineage['files'].items())


def test_portal_and_guide_link_to_current_active_run_card():
    render_review_20261030.render(ROOT)
    for filename in ('index.html', 'executive-summary.html', 'submission-guide.html'):
        html = (ROOT / 'docs' / filename).read_text()
        assert 's30-vce/run-card.json' in html
        assert 'data-submission-ready="true"' not in html
    html = (ROOT / 'docs/submission-guide.html').read_text()
    assert 'Predicted values must be in range [0, 1]' in html
    assert 'outside the survey footprint' in html
