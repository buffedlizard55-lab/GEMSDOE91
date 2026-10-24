"""Unit tests for the session-10 basement-step candidate and the holdout helpers.

Synthetic arrays only: no competition raster is needed.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems91 import basement  # noqa: E402

import evaluate_holdout as ev  # shared evaluator (main); no private fork in this branch


def _step_depth(h=60, w=60, step_col=30):
    """Basement depth with a sharp 400 m step at column `step_col`."""
    d = np.full((h, w), 300.0)
    d[:, step_col:] = 700.0
    return d


def test_clean_depth_removes_sentinel_and_nonfinite():
    raw = np.array([[1.0, -3.4e38], [np.nan, np.inf]])
    out = basement.clean_depth(raw)
    assert out[0, 0] == 1.0
    assert np.isnan(out[0, 1]) and np.isnan(out[1, 0]) and np.isnan(out[1, 1])


def test_rank_ramp_is_continuous_in_unit_interval_and_respects_exclusion():
    rng = np.random.default_rng(0)
    score = rng.random((40, 40))
    exclude = np.zeros((40, 40), dtype=bool)
    exclude[:5, :] = True
    out = basement.rank_ramp(score, exclude, k=100)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert np.count_nonzero(out) == 100
    assert np.all(out[exclude] == 0.0)
    vals = np.sort(out[out > 0])[::-1]
    assert vals[0] == pytest.approx(1.0 - 0 / 101)
    assert np.all(np.diff(vals) < 0), "ramp must be strictly decreasing in rank"


def test_rank_ramp_is_deterministic():
    score = np.random.default_rng(1).random((30, 30))
    ex = np.zeros((30, 30), dtype=bool)
    a = basement.rank_ramp(score, ex, k=50)
    b = basement.rank_ramp(score, ex, k=50)
    assert np.array_equal(a, b)


def test_ridge_marks_the_step_not_the_flat_areas():
    d = _step_depth()
    fp = np.ones(d.shape, dtype=bool)
    s = basement.score_field(d, fp, use_nms=True)
    ys, xs = np.nonzero(s)
    assert xs.size > 0
    # ridge sits on the step (columns near 30), away from the flat margins
    assert np.all(np.abs(xs - 29.5) <= 3)


def test_nms_thins_the_ridge_relative_to_no_nms():
    d = _step_depth()
    fp = np.ones(d.shape, dtype=bool)
    thin = np.count_nonzero(basement.score_field(d, fp, use_nms=True))
    wide = np.count_nonzero(basement.score_field(d, fp, use_nms=False))
    assert 0 < thin < wide


def test_build_candidate_zero_on_visible_catalogue_and_outside_footprint():
    d = _step_depth()
    fp = np.ones(d.shape, dtype=bool)
    fp[:, :3] = False
    visible = np.zeros(d.shape, dtype=bool)
    visible[28:33, :] = True  # catalogue cells on the step
    out = basement.build_candidate(d, fp, visible, k=40)
    assert np.all(out[visible] == 0.0)
    assert np.all(out[~fp] == 0.0)


def test_random_placement_has_budget_and_respects_exclusion():
    fp = np.ones((50, 50), dtype=bool)
    ex = np.zeros((50, 50), dtype=bool)
    ex[0:10, :] = True
    out = basement.random_placement(fp, ex, k=77, seed=3)
    assert np.count_nonzero(out) == 77
    assert np.all(out[ex] == 0.0)
    assert np.array_equal(out, basement.random_placement(fp, ex, k=77, seed=3))


def test_auc_perfect_separation_and_ties():
    # shared evaluator's rank-based AUC: scores first, then 0/1 labels
    assert ev.fast_mann_whitney_auc(np.array([3.0, 4.0, 1.0, 2.0]), np.array([1, 1, 0, 0])) == pytest.approx(1.0)
    assert ev.fast_mann_whitney_auc(np.array([1.0, 2.0, 3.0, 4.0]), np.array([1, 1, 0, 0])) == pytest.approx(0.0)
    assert ev.fast_mann_whitney_auc(np.array([1.0, 1.0]), np.array([1, 0])) == pytest.approx(0.5)
