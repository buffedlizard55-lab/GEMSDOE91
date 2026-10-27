"""Safety contracts for the 2026-10-27 negative review; no geology is fitted."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_s18_alias_quarantined_and_claims_withdrawn():
    card = load('docs/run-card-S18-UNIQUE.json')
    witness = load('docs/review-20261027/witness-audit.json')
    old_card = ROOT / card['audit_correction']['original_card']
    assert hashlib.sha256(old_card.read_bytes()).hexdigest() == card['audit_correction']['original_card_sha256']
    assert card['ok_to_submit'] is False and card['submission_ready'] is False
    assert card['holdout']['dti'] is None and card['leakage_canary']['result'] == 'UNVERIFIED'
    assert card['registry_uniqueness']['is_duplicate'] is True
    assert card['registry_uniqueness']['final_dot_overlap_3px'] > .70
    current = witness['s18_alias']['current_path']
    prior = witness['s18_alias']['previous_path']
    assert (ROOT / current).read_bytes() == (ROOT / prior).read_bytes()
    assert sha(current) == card['raster_sha256'] == sha(prior)
    with zipfile.ZipFile(ROOT / card['raster']['zip']) as z:
        assert z.namelist() == [Path(current).name]
        assert z.read(z.namelist()[0]) == (ROOT / current).read_bytes()
    policies = {r['path']: r for r in load('registry/artifact_policy.json')['files']}
    for path in (current, prior, card['raster']['zip']):
        assert policies[path]['status'] == 'parallel_quarantined'
        assert policies[path]['sha256'] == sha(path)


def test_capacity_is_a_bound_not_a_candidate_or_score():
    card = load('docs/review-20261027/run-card.json')
    cap = card['registry']['capacity']
    assert card['verdict'] == 'negative_preflight_blocked'
    assert card['ok_to_submit'] is False and card['candidate']['name'] is None
    assert card['candidate']['raster_sha256'] is None and card['holdout']['dti'] is None
    assert card['experiments']['geological_experiments_this_review'] == 0
    assert cap['candidate_budget'] - cap['uncovered_pixels'] == cap['minimum_overlapping_dots']
    assert cap['overlap_lower_bound'] == cap['minimum_overlapping_dots'] / cap['candidate_budget']
    assert cap['overlap_lower_bound'] > .70 and not cap['feasible_by_capacity_only']
    assert not card['registry']['complete_registry_clearance']
    assert all(v['verdict'] == 'DUPLICATE' and v['overlap_within_3px'] > .70
               for v in card['registry']['existing_witnesses'].values())


def test_nine_claims_are_not_receipts_and_all_fail_peer_gate():
    audit = load('docs/review-20261027/nine-site-audit.json')
    assert len(audit['sites']) == 9 and audit['organizer_confirmed_scores'] == 0
    assert audit['estimated_leaderboard_score'] is None
    assert sum(len(r['peer_comparisons']) for r in audit['sites']) == 72
    assert all(not r['protocol_unique_among_nine'] and r['organizer_confirmed_score'] is None
               and r['max_overlap_vs_other_eight']['overlap_within_3px'] > .70
               for r in audit['sites'])


def test_current_pages_never_advertise_s18_as_unique_or_submittable():
    from scripts.render_olc91_portal import render
    render()
    for relative in ('docs/index.html', 'docs/executive-summary.html',
                     'docs/s18-unique-executive-summary.html'):
        page = (ROOT / relative).read_text()
        assert 'OK TO SUBMIT: NO' in page
        assert 'byte-identical' in page
        assert '99.605%' in page
        assert '21.44% &le; 70%' not in page
        assert 'Leakage canary PASS' not in page
    for relative in ('docs/index.html', 'docs/executive-summary.html'):
        page = (ROOT / relative).read_text()
        assert page.count('data-repository="GEMSDOE') == 9
        assert 'assets/live-source-feed.js' in page
        assert 'source activity, not a leaderboard score' in page
