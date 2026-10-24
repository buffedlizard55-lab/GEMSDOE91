"""Synthetic receipts only: adversarial policy checks are not experiments."""
import copy
import pytest
from gems91.readiness import gates, submission_ready


@pytest.fixture
def good():
    return {
        'validator_output': {'status': 'PASS', 'checks': {'reread': True},
            'no_nan_inside_footprint': True, 'values_in_0_1': True, 'crs_shape_transform_match': True},
        'canaries': {'status': 'PASS', 'max_symmetric_auc': .7},
        'registry_comparison': {'complete_universal_registry': True,
            'preplacement': {'status': 'PASS_WITHIN_INDEXED_SCOPE', 'checked': 20, 'not_checked_after_stop': 0},
            'final': {'status': 'PASS_WITHIN_INDEXED_SCOPE', 'checked': 20, 'not_checked_after_stop': 0},
            'max_measured_surface_rank_correlation': .9,
            'max_measured_final_dot_overlap_within_3px': .7},
        'lane': {'assigned': True},
        'holdout_dti': {'status': 'COMPLETED', 'label': 'HOLDOUT-DTI', 'value': .2,
            'ci95': [.1, .3], 'withheld_positives': 100, 'split_sha256': 'synthetic',
            'evaluator_version': 'synthetic-v1', 'paired_best': {'delta': .02, 'ci95': [.01, .03]}},
        'comparable_prior_holdout_best': {'split_sha256': 'synthetic', 'evaluator_version': 'synthetic-v1'},
        'selector_approval': True, 'selector_receipt': {'weekly_cap_verified': True, 'slot_available': True}}


def test_valid_boundary(good):
    assert submission_ready(good)


@pytest.mark.parametrize('value', [None, 'PASS', [], True, float('nan'), float('inf'), 10**1000, -.1, 1.1])
def test_malformed_measurement_fails_closed(good, value):
    for section, key in [('canaries','max_symmetric_auc'),
                         ('registry_comparison','max_measured_final_dot_overlap_within_3px'),
                         ('holdout_dti','value')]:
        card = copy.deepcopy(good)
        card[section][key] = value
        assert not submission_ready(card)


@pytest.mark.parametrize('ci', [[.03,.01], [.01,float('inf')], [.01,float('nan')], ['a','b'], True, None, [.01], [-.01,.03]])
def test_invalid_paired_interval(good, ci):
    good['holdout_dti']['paired_best']['ci95'] = ci
    assert not submission_ready(good)


@pytest.mark.parametrize('value', [None, [], 'PASS', 1])
def test_invalid_sections_do_not_crash(good, value):
    assert not submission_ready(value)
    for section in good:
        card = copy.deepcopy(good)
        card[section] = value
        assert not submission_ready(card)


def test_status_cannot_override_duplicate_or_canary(good):
    good['registry_comparison']['max_measured_final_dot_overlap_within_3px'] = .700001
    assert not gates(good)['novelty']
    good['canaries']['max_symmetric_auc'] = .900001
    assert not gates(good)['canary']


def test_partial_or_empty_registry_fails(good):
    for key, value in [('checked',0), ('checked',True), ('not_checked_after_stop',1)]:
        card = copy.deepcopy(good)
        card['registry_comparison']['final'][key] = value
        assert not gates(card)['novelty']
