"""Unit tests for the fixed-count H19-5 PRUNE refill objective."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import dti as full_metric  # noqa: E402
from gems91 import prune_refill as pr  # noqa: E402


def test_best_credit_matches_full_metric_components():
    rng = np.random.default_rng(91)
    support = rng.random((24, 29)) < 0.30
    dots = support & (rng.random(support.shape) < 0.20)
    best = pr.best_credit(dots)
    expected_T = full_metric.kernel_credit(dots, support)
    assert float(best[support].sum()) == pytest.approx(expected_T, abs=1e-12)
    parts = pr.support_components(dots, support)
    assert parts["T"] == pytest.approx(expected_T, abs=1e-12)
    assert parts["S"] == parts["M"] == float(dots.sum())


def test_single_addition_matches_full_marginal_dti_recompute():
    rng = np.random.default_rng(306)
    support = rng.random((31, 27)) < 0.22
    dots = support & (rng.random(support.shape) < 0.22)
    candidates = np.argwhere(support & ~dots)
    best = pr.best_credit(dots)
    base = pr.support_components(dots, support)
    for row, col in candidates[:: max(1, len(candidates) // 12)][:12]:
        delta_T = pr.delta_support_credit(best, support, int(row), int(col))
        got = pr.exact_add_delta(base["T"], base["G"], delta_T)
        expected = full_metric.marginal_gain(dots, support, int(row), int(col), mode="add")
        assert delta_T == pytest.approx(expected.delta_T, abs=1e-12)
        assert got == pytest.approx(expected.delta_dti, abs=1e-12)


def test_greedy_sequence_matches_naive_full_metric_greedy():
    rng = np.random.default_rng(19)
    support = rng.random((19, 23)) < 0.32
    survivors = support & (rng.random(support.shape) < 0.16)
    eligible = support & ~survivors
    result = pr.greedy_support_refill(survivors, support, eligible, 4,
                                      min_separation_px=None)

    dots = survivors.copy()
    expected_sequence = []
    for _ in range(4):
        choices = []
        for row, col in np.argwhere(support & ~dots):
            gain = full_metric.marginal_gain(dots, support, int(row), int(col), mode="add")
            choices.append((-gain.delta_dti, int(row), int(col)))
        choices.sort()
        _, row, col = choices[0]
        expected_sequence.append((row, col))
        dots[row, col] = True

    got_sequence = [(s["row"], s["col"]) for s in result.selections]
    assert got_sequence == expected_sequence
    assert np.array_equal(result.added | survivors, dots)
    assert int(result.added.sum()) == 4


def test_refill_is_deterministic_and_preserves_requested_separation():
    support = np.zeros((23, 25), dtype=bool)
    support[5:18, 5:20] = True
    survivors = np.zeros_like(support)
    survivors[6, 6] = True
    survivors[16, 18] = True
    eligible = support & ~survivors
    a = pr.greedy_support_refill(survivors, support, eligible, 12,
                                 min_separation_px=2.8)
    b = pr.greedy_support_refill(survivors, support, eligible, 12,
                                 min_separation_px=2.8)
    assert np.array_equal(a.added, b.added)
    assert [(s["row"], s["col"]) for s in a.selections] == [
        (s["row"], s["col"]) for s in b.selections]
    pts = np.argwhere(a.added | survivors)
    from scipy.spatial import cKDTree
    nearest = cKDTree(pts).query(pts, k=2)[0][:, 1]
    assert nearest.min() > 2.8


def test_refill_fails_closed_when_count_or_separation_is_infeasible():
    support = np.ones((7, 7), dtype=bool)
    survivors = np.zeros_like(support)
    survivors[3, 3] = True
    eligible = support & ~survivors
    with pytest.raises(ValueError, match="feasible|only"):
        pr.greedy_support_refill(survivors, support, eligible, 5,
                                 min_separation_px=2.8)
    with pytest.raises(ValueError, match="only"):
        pr.greedy_support_refill(survivors, support, eligible, 100,
                                 min_separation_px=None)


def test_support_objective_rejects_off_support_dots():
    support = np.zeros((5, 5), dtype=bool)
    support[2, 2] = True
    dots = np.zeros_like(support)
    dots[1, 1] = True
    with pytest.raises(ValueError, match="on support"):
        pr.support_components(dots, support)
