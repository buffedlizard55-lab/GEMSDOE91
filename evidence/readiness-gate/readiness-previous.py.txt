"""Fail-closed policy for portal/CI. Status labels never override measurements.

This validates receipt structure, not receipt authenticity; byte/provenance
verification remains the responsibility of verify_evidence/current_artifact.
"""
from __future__ import annotations

import math


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _number(value, low, high):
    return (type(value) in (int, float) and low <= value <= high
            and math.isfinite(value))


def _interval(value, low, high):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(_number(v, low, high) for v in value)
            and value[0] <= value[1])


def gates(card):
    card = _mapping(card)
    v = _mapping(card.get('validator_output'))
    registry = _mapping(card.get('registry_comparison'))
    holdout = _mapping(card.get('holdout_dti'))
    best = _mapping(card.get('comparable_prior_holdout_best'))
    paired = _mapping(holdout.get('paired_best'))
    checks = _mapping(v.get('checks'))
    ci = paired.get('ci95')
    split = best.get('split_sha256')
    version = best.get('evaluator_version')
    comparable = (isinstance(split, str) and bool(split)
                  and split == holdout.get('split_sha256')
                  and isinstance(version, str) and bool(version)
                  and version == holdout.get('evaluator_version'))
    # A positive paired claim alone is not evidence of beating a baseline.
    # Require the same population and coherent pooled-score arithmetic. This
    # checks structure, not provenance; verify_evidence still authenticates bytes.
    measured_improvement = (
        _number(best.get('value'), 0, 1)
        and _interval(best.get('ci95'), 0, 1)
        and type(best.get('withheld_positives')) is int
        and best['withheld_positives'] > 0
        and best['withheld_positives'] == holdout.get('withheld_positives')
        and _number(holdout.get('value'), 0, 1)
        and _number(paired.get('delta'), 0, 1)
        and math.isclose(holdout['value'] - best['value'], paired['delta'],
                         rel_tol=1e-6, abs_tol=1e-9)
        and _interval(ci, -1, 1)
        and ci[0] <= paired['delta'] <= ci[1]
    )
    selector = _mapping(card.get('selector_receipt'))
    canary = _mapping(card.get('canaries'))
    phases = [_mapping(registry.get(k)) for k in ('preplacement', 'final')]
    count = holdout.get('withheld_positives')
    return {
        'format': v.get('status') == 'PASS' and bool(checks) and all(x is True for x in checks.values())
                  and all(v.get(k) is True for k in ('no_nan_inside_footprint','values_in_0_1','crs_shape_transform_match')),
        'canary': canary.get('status') == 'PASS'
                  and _number(canary.get('max_symmetric_auc'), .5, .90),
        'novelty': registry.get('complete_universal_registry') is True
                   and all(p.get('status') == 'PASS_WITHIN_INDEXED_SCOPE'
                           and type(p.get('checked')) is int and p['checked'] > 0
                           and type(p.get('not_checked_after_stop')) is int
                           and p['not_checked_after_stop'] == 0 for p in phases)
                   and phases[0].get('checked') == phases[1].get('checked')
                   and _number(registry.get('max_measured_surface_rank_correlation'), -.90, .90)
                   and _number(registry.get('max_measured_final_dot_rank_correlation'), -.90, .90)
                   and _number(registry.get('max_measured_final_dot_overlap_within_3px'), 0, .70),
        'assigned_lane': _mapping(card.get('lane')).get('assigned') is True,
        'beats_comparable_best': bool(comparable and measured_improvement
                                     and holdout.get('status') == 'COMPLETED'
                                     and holdout.get('label') == 'HOLDOUT-DTI'
                                     and type(count) is int and count > 0
                                     and _number(holdout.get('value'), 0, 1)
                                     and _interval(holdout.get('ci95'), 0, 1)
                                     and _number(paired.get('delta'), 0, 1)
                                     and paired['delta'] > 0
                                     and _interval(ci, -1, 1) and ci[0] > 0),
        'separate_selector': card.get('selector_approval') is True
                             and selector.get('weekly_cap_verified') is True
                             and selector.get('slot_available') is True,
    }


def submission_ready(card):
    return all(gates(card).values())
