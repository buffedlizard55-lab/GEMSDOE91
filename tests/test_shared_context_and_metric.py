"""Synthetic safety checks; these are not geological experiments or scores."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage as ndi

from vendor.gems57 import evaluate_holdout, holdout, metric, spatial
from gems91.readiness import gates


def test_fold_buffers_catalogue_features_without_unmasking_known_pixels():
    cat = np.zeros((40, 40), bool)
    cat[10:15, 19] = True            # NW component, withheld whole
    cat[12, 21] = True               # disconnected, 2 px away in NE
    cat[6, 35] = True                # truly visible, outside 3 px
    fp = np.ones_like(cat)
    f = list(spatial.folds(cat, fp, buffer_px=3))[0]

    assert f['truth'][10:15, 19].all()
    assert not f['visible'][12, 21]
    assert f['masked_known'][12, 21]  # excluded from features, NOT a new negative
    assert f['visible'][6, 35]
    assert not (f['held_all'] & f['visible']).any()
    assert f['receipt']['feature_context_catalogue_pixels_removed'] == 1
    assert f['receipt']['nearest_visible_to_held_px'] > 3
    assert f['receipt']['split_version'] == 'label-blind-quadrants-v3-feature-buffered'
    distance = ndi.distance_transform_edt(~f['held_all'])
    assert (distance[f['visible']] > 3).all()
    assert (distance[f['train']] > 3).all()

    # Exercise the shared evaluator's separate pixel-exact scoring mask.
    # The sole prediction is on a known pixel removed from feature context.
    fold = {**f, 'region': fp}
    pred = np.zeros_like(cat, dtype=float)
    pred[12, 21] = 1
    result, _ = evaluate_holdout.evaluate(pred, fold, fp, block_side=10)
    assert result['n_emitted'] == 0
    assert result['fpw'] == 0
    assert result['tpw'] == 0


def test_actual_fold_receipts_satisfy_buffered_readiness_structure():
    cat = np.zeros((40, 40), bool)
    for y, x in ((5, 5), (5, 34), (34, 5), (34, 34)):
        cat[y, x] = True
    folds = list(spatial.folds(cat, np.ones_like(cat), buffer_px=3))
    receipts = [f['receipt'] for f in folds]
    assert gates({'holdout_dti': {'fold_receipts': receipts,
                                  'withheld_positives': sum(r['truth_px'] for r in receipts)}})['buffered_context']


def test_shared_evaluators_refuse_implicit_visible_as_known():
    pred = np.zeros((4, 4))
    cat = np.zeros((4, 4), bool); cat[1, 1] = True
    fold = {'truth': cat, 'region': np.ones_like(cat), 'visible': ~cat}
    with pytest.raises(ValueError, match='masked_known'):
        evaluate_holdout.evaluate(pred, fold, np.ones_like(cat))
    with pytest.raises(ValueError, match='masked_known'):
        holdout.score(pred, fold, np.ones_like(cat))


def test_legacy_unbuffered_instruments_block_by_default():
    with pytest.raises(RuntimeError, match='Legacy unbuffered'):
        holdout.build_holdout(None)
    cat = np.zeros((4, 4), bool)
    with pytest.raises(RuntimeError, match='Legacy truth-shaped'):
        list(spatial.legacy_component_tail_folds(cat, ~cat))


def test_no_held_component_does_not_use_implicit_edt_exterior():
    cat = np.zeros((20, 20), bool)
    cat[2, 2] = True
    fp = np.ones_like(cat)
    # Empty SE quadrant: all catalogue context remains visible.
    f = list(spatial.folds(cat, fp, buffer_px=3))[3]
    np.testing.assert_array_equal(f['visible'], cat)
    assert f['receipt']['nearest_visible_to_held_px'] is None
    assert f['receipt']['feature_context_catalogue_pixels_removed'] == 0


@pytest.mark.parametrize('buffer', [-1, float('nan'), float('inf'), True, '3'])
def test_context_rejects_invalid_buffer(buffer):
    with pytest.raises(ValueError, match='buffer_px'):
        list(spatial.folds(np.ones((5, 5), bool), np.ones((5, 5), bool), buffer))


def test_context_rejects_nonboolean_or_misaligned_masks():
    with pytest.raises(ValueError, match='boolean masks'):
        list(spatial.folds(np.ones((5, 5)), np.ones((5, 5), bool)))
    with pytest.raises(ValueError, match='boolean masks'):
        list(spatial.folds(np.ones((5, 5), bool), np.ones((5, 1), bool)))


def test_truth_side_gain_can_exceed_self_credit_for_one_new_dot():
    truth = np.zeros((7, 7), bool)
    truth[3, 3:5] = True
    p = np.zeros(truth.shape)
    p[3, 3] = 1
    credit, kernel_credit, _ = metric.max_cover(p, truth)
    assert credit.sum() == pytest.approx(1 + 2 / 3)
    assert kernel_credit[3, 3] == 1
    assert credit.sum() > kernel_credit[3, 3]  # even with no prior prediction


@pytest.mark.parametrize(('alpha', 'beta'), [(0.2, 0.8), (0.6, 0.2), (0.1, 0.4), (0.9, 0.9)])
def test_marginal_accept_matches_full_recompute_with_arbitrary_weights(alpha, beta):
    rng = np.random.default_rng(917)
    for _ in range(20):
        truth = rng.random((7, 7)) < .2
        truth[3, 3] = True
        p = rng.random((7, 7)) < .12
        empty = np.argwhere(~p)
        y, x = empty[rng.integers(len(empty))]
        T, q, _ = metric.max_cover(p.astype(float), truth)
        M, n, K = float(q[p].sum()), int(p.sum()), int(truth.sum())
        new_p = p.copy(); new_p[y, x] = True
        T1, _, _ = metric.max_cover(new_p.astype(float), truth)
        before = metric.dti_exact(p.astype(float), truth, alpha=alpha, beta=beta)['dti']
        after = metric.dti_exact(new_p.astype(float), truth, alpha=alpha, beta=beta)['dti']
        if abs(after - before) > 1e-12:
            assert metric.marginal_accept(float(T1.sum() - T.sum()), float(q[y, x]),
                                          float(T.sum()), M, n, K, alpha, beta) == (after > before)


@pytest.mark.parametrize('fn', [metric.dti_binary, metric.dti_exact])
def test_metric_rejects_broadcast_masks_and_non_2d_inputs(fn):
    p = np.zeros((4, 4)); g = np.zeros((4, 4), bool)
    with pytest.raises(ValueError, match='2-D'):
        fn(p, g, known=np.zeros((1, 4), bool))
    with pytest.raises(ValueError, match='2-D'):
        fn(p, g, valid=np.ones((4, 1), bool))
    with pytest.raises(ValueError, match='2-D'):
        fn(p.ravel(), g.ravel())


def test_historical_s22_runner_remains_blocked_when_receipts_are_missing():
    from scripts import run_s22_omtj
    with pytest.raises(RuntimeError, match='frozen, duplicate-stopped'):
        run_s22_omtj.run()
