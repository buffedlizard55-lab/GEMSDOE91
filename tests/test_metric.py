import numpy as np
import pytest

from gems91.metric import (ALPHA, dti, components, marginal_gain, _shift,
                           isolated_truth_pays, triangular_kernel)


def blank(n=9):
    return np.zeros((n, n)), np.zeros((n, n), dtype=bool)


def test_kernel_is_triangular_and_zero_at_radius():
    assert triangular_kernel(0.0) == pytest.approx(1.0)
    assert triangular_kernel(1.5) == pytest.approx(0.5)
    assert triangular_kernel(3.0) == pytest.approx(0.0)
    assert triangular_kernel(10.0) == 0.0


def test_isolated_perfect_dot_scores_one():
    pred, truth = blank()
    pred[4, 4], truth[4, 4] = 1.0, True
    parts = components(pred, truth)
    assert parts.T == pytest.approx(1.0)
    assert parts.S == pytest.approx(1.0)
    assert parts.M == pytest.approx(1.0)
    assert dti(pred, truth) == pytest.approx(1.0)


def test_unmatched_mass_strictly_lowers_score():
    pred, truth = blank()
    truth[4, 4] = True
    pred[4, 4] = 1.0
    base = dti(pred, truth)
    pred2 = pred.copy()
    pred2[0, 0] = 1.0  # > R away from any truth pixel
    assert dti(pred2, truth) < base


def test_matched_mass_costs_nothing_in_denominator():
    pred, truth = blank()
    pred[4, 4], truth[4, 4] = 1.0, True
    parts = components(pred, truth)
    assert parts.S - parts.M == pytest.approx(0.0)


def test_shallow_credit_is_partial():
    pred, truth = blank()
    truth[4, 4] = True
    pred[4, 6] = 1.0  # 2 px away -> k = 1/3
    parts = components(pred, truth)
    assert parts.T == pytest.approx(1.0 / 3.0)
    assert parts.M == pytest.approx(1.0 / 3.0)


def test_shift_direction():
    a = np.zeros((5, 5))
    a[2, 2] = 1.0
    shifted = _shift(a, 1, 0)  # out[r,c] = a[r-1,c]
    assert shifted[3, 2] == 1.0


def test_marginal_gain_equals_full_recompute():
    rng = np.random.default_rng(7)
    pred = rng.random((12, 12))
    pred[pred < 0.85] = 0.0
    truth = rng.random((12, 12)) > 0.9
    r, c = 5, 6
    fast = marginal_gain(pred, truth, r, c, p=1.0)
    after = pred.copy()
    after[r, c] += 1.0
    slow = dti(after, truth) - dti(pred, truth)
    assert fast == pytest.approx(slow, abs=1e-12)


def test_marginal_gain_negative_off_truth_mass():
    pred, truth = blank()
    truth[4, 4] = True
    pred[4, 4] = 1.0
    # a dot 4 px away earns no credit and adds unmatched mass
    assert marginal_gain(pred, truth, 4, 8) < 0


def test_marginal_gain_positive_on_uncovered_truth():
    pred, truth = blank()
    truth[4, 4] = True
    truth[1, 1] = True
    pred[4, 4] = 1.0
    assert marginal_gain(pred, truth, 1, 1) > 0


def test_rule_of_thumb_threshold_at_028():
    # brief section 2: 0.2 * 0.28 = 0.056
    assert isolated_truth_pays(0.055, 0.28) is False
    assert isolated_truth_pays(0.057, 0.28) is True
    assert ALPHA * 0.28 == pytest.approx(0.056)


def test_empty_truth_raises():
    pred, truth = blank()
    with pytest.raises(ValueError):
        dti(pred, truth)


def test_negative_mass_rejected():
    pred, truth = blank()
    truth[4, 4] = True
    pred[0, 0] = -1.0
    with pytest.raises(ValueError):
        dti(pred, truth)


def test_dense_coverage_scores_exactly_one():
    """Official TPw is a per-truth-pixel MAX, capped at 1 per truth pixel:
    a prediction covering every truth pixel at p=1 has TPw=|G|, FPw=FNw=0,
    so DTI == 1, never above. (Before 2026-10-24 this module summed p*k and
    this test asserted DTI > 1 — that was the IR-91-37 bug.)"""
    n = 40
    pred = np.zeros((n, n))
    truth = np.zeros((n, n), dtype=bool)
    truth[5:35, 20] = True
    pred[5:35, 20] = 1.0
    parts = components(pred, truth)
    assert parts.T == pytest.approx(30.0)  # capped: one credit per truth pixel
    assert dti(pred, truth) == pytest.approx(1.0)


def test_official_algebra_matches_tpw_fpw_fnw():
    """DTI == TPw/(TPw + 0.2*FPw + 0.8*FNw) with FNw=|G|-TPw, FPw=S-M,
    and the organiser's worked example TPw=3.00 FPw=1.89 FNw=2.00 -> 0.60
    (DrivenData #306 problem page, verified 2026-10-24)."""
    assert 3.00 / (3.00 + 0.2 * 1.89 + 0.8 * 2.00) == pytest.approx(0.60, abs=0.005)
    rng = np.random.default_rng(11)
    pred = (rng.random((15, 15)) > 0.8).astype(float)
    truth = rng.random((15, 15)) > 0.85
    parts = components(pred, truth)
    tpw, fpw = parts.T, parts.S - parts.M
    fnw = parts.n_truth - parts.T
    assert parts.dti() == pytest.approx(tpw / (tpw + 0.2 * fpw + 0.8 * fnw))
    assert 0.0 <= parts.dti() <= 1.0


def test_sparse_dot_field_on_long_truth_is_small():
    """Few dots against a long truth line is the realistic regime (< 0.5)."""
    n = 60
    pred = np.zeros((n, n))
    truth = np.zeros((n, n), dtype=bool)
    truth[:, 20] = True            # 60 px of truth
    truth[30, :] = True            # crossing line, 60 px
    pred[0:10, 20] = 1.0           # 10 dots on 10% of one arm
    val = dti(pred, truth)
    assert 0.0 < val < 0.5
