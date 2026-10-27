"""Fail-closed policy for portal/CI. Status labels never override measurements.

This validates receipt structure, not receipt authenticity; byte/provenance
verification remains the responsibility of verify_evidence/current_artifact.
"""
from __future__ import annotations

import math


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _number(value, low, high):
    if type(value) not in (int, float):
        return False
    try:
        return low <= value <= high and math.isfinite(value)
    except OverflowError:  # enormous integers are not finite receipt measurements
        return False


def _interval(value, low, high):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(_number(v, low, high) for v in value)
            and value[0] <= value[1])


# This gate is intentionally specific to the current reviewed shared split.
# A different sound instrument needs an explicit reviewed policy revision;
# a legacy result or an unrecognised split must not silently become promotion evidence.
BUFFERED_SPLIT_VERSION = 'label-blind-quadrants-v3-feature-buffered'


def _buffered_folds(value):
    """Check structure of all four shared split receipts, not their provenance."""
    if not isinstance(value, list) or len(value) != 4:
        return False
    if any(not isinstance(row, dict) for row in value):
        return False
    if any(type(row.get('fold')) is not int for row in value):
        return False
    if {row['fold'] for row in value} != {0, 1, 2, 3}:
        return False
    buffers = [row.get('feature_context_buffer_px') for row in value]
    if any(not _number(b, 0, float('inf')) or b <= 0 for b in buffers):
        return False
    if len(set(buffers)) != 1:
        return False
    return all(
        row.get('split_version') == BUFFERED_SPLIT_VERSION
        and row.get('evaluation_region_label_blind') is True
        and row.get('known_scoring_mask_pixel_exact') is True
        and type(row.get('truth_px')) is int and row['truth_px'] > 0
        and type(row.get('held_components')) is int and row['held_components'] > 0
        and type(row.get('shared_train_truth_components')) is int
        and row['shared_train_truth_components'] == 0
        and _number(row.get('nearest_visible_to_held_px'), 0, float('inf'))
        and row['nearest_visible_to_held_px'] > row['feature_context_buffer_px']
        for row in value
    )


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
                  and _number(canary.get('max_symmetric_auc'), .5, .90)
                  # If a separate per-quadrant maximum was recorded it cannot
                  # be hidden behind a lower pooled maximum.
                  and ('max_quadrant_symmetric_auc' not in canary
                       or _number(canary['max_quadrant_symmetric_auc'], .5, .90)),
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
        'buffered_context': (_buffered_folds(holdout.get('fold_receipts'))
                             and type(count) is int
                             and sum(r['truth_px'] for r in holdout['fold_receipts']) == count),
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
