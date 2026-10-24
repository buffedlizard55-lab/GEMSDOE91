"""One fail-closed policy for portal, CI and run cards; no human inspector gate."""
from __future__ import annotations


def gates(card):
    v = card.get('validator_output', {})
    registry = card.get('registry_comparison', {})
    holdout = card.get('holdout_dti', {})
    best = card.get('comparable_prior_holdout_best')
    paired = holdout.get('paired_best') or {}
    checks = v.get('checks') or {}
    ci = paired.get('ci95') or []
    comparable = (isinstance(best, dict) and best.get('split_sha256')
                  and best.get('split_sha256') == holdout.get('split_sha256')
                  and best.get('evaluator_version') == holdout.get('evaluator_version'))
    selector = card.get('selector_receipt') or {}
    return {
        'format': v.get('status') == 'PASS' and bool(checks) and all(x is True for x in checks.values())
                  and all(v.get(k) is True for k in ('no_nan_inside_footprint','values_in_0_1','crs_shape_transform_match')),
        'canary': card.get('canaries', {}).get('status') == 'PASS',
        'novelty': registry.get('complete_universal_registry') is True
                   and all(registry.get(k, {}).get('status') == 'PASS_WITHIN_INDEXED_SCOPE' for k in ('preplacement','final')),
        'assigned_lane': card.get('lane', {}).get('assigned') is True,
        'beats_comparable_best': bool(comparable and holdout.get('status') == 'COMPLETED'
                                     and paired.get('delta', 0) > 0 and len(ci) == 2 and ci[0] > 0),
        'separate_selector': card.get('selector_approval') is True
                             and selector.get('weekly_cap_verified') is True
                             and selector.get('slot_available') is True,
    }


def submission_ready(card):
    return all(gates(card).values())
