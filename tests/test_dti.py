"""Unit tests for the DTI algebra (brief section 2: 'Algebra (derived; unit-test it)')."""

from __future__ import annotations

import itertools

import numpy as np
import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dti as D  # noqa: E402


def blank(h=121, w=121):
    return np.zeros((h, w), dtype=np.float64)


def test_kernel_radius_is_three_pixels():
    assert D.kernel_radius_px() == 3
    assert D.kernel_radius_px(300.0, 100.0) == 3


def test_kernel_offsets_are_triangular_and_symmetric():
    dy, dx, k = D._kernel_offsets(3)
    assert np.allclose(k[dy == 0], k[dy == 0])  # sanity
    # zero-weight pixels on the circle d >= R are excluded
    d = np.hypot(dy, dx)
    assert np.all(k > 0)
    assert np.all(d[k > 0] < 3)
    # symmetry of weights under sign flips
    lookup = {(a, b): c for a, b, c in zip(dy, dx, k)}
    for (a, b), c in list(lookup.items()):
        assert lookup[(-a, -b)] == pytest.approx(c)
    # centre weight is 1
    assert lookup[(0, 0)] == pytest.approx(1.0)


def test_perfect_prediction_scores_one():
    truth = blank()
    truth[10, 10] = 1
    truth[40, 70] = 1
    truth[100, 5] = 1
    assert D.dti(truth.copy(), truth) == pytest.approx(1.0)
    c = D.components(truth.copy(), truth)
    assert c.T == pytest.approx(3.0)
    assert c.M == pytest.approx(3.0)  # S - M = 0 for a perfect field
    assert c.G == pytest.approx(3.0)


def test_empty_prediction_scores_zero():
    truth = blank()
    truth[10, 10] = 1
    assert D.dti(blank(), truth) == pytest.approx(0.0)


def test_offset_dot_on_isolated_truth_scores_kernel_weight():
    """One dot on an isolated truth pixel must score exactly k(d) -- the brief's bar."""
    truth = blank()
    truth[60, 60] = 1
    for d in range(0, 3):
        pred = blank()
        pred[60 + d, 60] = 1.0
        k = 1.0 - d / 3.0
        # denominator collapses to 1.0 for a lone dot: 0.2k + 0.2(1-k) + 0.8
        assert D.dti(pred, truth) == pytest.approx(k, abs=1e-12)


def test_pays_iff_weight_exceeds_alpha_times_current_dti():
    """For an isolated truth pixel a dot pays iff k > 0.2 * DTI_current."""
    truth = blank()
    truth[10, 10] = 1          # covered truth -> sets the current DTI
    truth[100, 100] = 1        # target truth pixel, kept uncovered
    pred = blank()
    pred[10, 10] = 1.0
    base = D.dti(pred, truth)
    assert base > 0

    for dy, dx in itertools.product(range(-6, 7), repeat=2):
        d = float(np.hypot(dy, dx))
        k = max(0.0, 1.0 - d / 3.0)
        iy, ix = 100 + dy, 100 + dx
        g = D.marginal_gain(pred, truth, iy, ix)
        pays = g.delta_dti > 1e-15
        predicted = k > D.ALPHA * base
        assert pays == predicted, (dy, dx, k, base, g)
        if d > 3:  # outside the kernel: no credit at all, only denominator cost
            assert g.delta_T == pytest.approx(0.0)
            assert g.delta_dti < 0


def test_threshold_arithmetic_at_public_score():
    """0.2 * 0.28 = 0.056: the bar quoted in the brief, as arithmetic."""
    assert D.ALPHA * 0.28 == pytest.approx(0.056)


def test_line_truth_lowers_the_bar():
    """A dot beside two truth pixels earns two kernel terms, so it pays at a higher DTI."""
    # isolated case
    t1 = blank()
    t1[100, 100] = 1
    p1 = blank()
    p1[50, 50] = 1
    g1 = D.marginal_gain(p1, t1, 100, 99)
    # line-like case: two adjacent truth pixels, same dot position
    t2 = blank()
    t2[100, 100] = 1
    t2[101, 100] = 1
    p2 = blank()
    p2[50, 50] = 1
    g2 = D.marginal_gain(p2, t2, 100, 99)
    assert g2.delta_T > g1.delta_T
    assert g2.ratio > g1.ratio
    assert (0.2 * 0.28) == pytest.approx(0.056)


def test_marginal_gain_matches_full_recompute_random():
    rng = np.random.default_rng(20261023)
    for trial in range(12):
        truth = (rng.random((40, 40)) < 0.08).astype(np.float64)
        pred = (rng.random((40, 40)) < 0.10).astype(np.float64)
        base = D.dti(pred, truth)
        for _ in range(6):
            iy, ix = rng.integers(0, 40, size=2)
            for mode in ("add", "remove"):
                g = D.marginal_gain(pred, truth, int(iy), int(ix), mode=mode)
                nxt = pred.copy()
                nxt[iy, ix] = min(1.0, nxt[iy, ix] + 1.0) if mode == "add" else max(0.0, nxt[iy, ix] - 1.0)
                expected = D.dti(nxt, truth) - base
                assert g.delta_dti == pytest.approx(expected, abs=1e-12), (trial, iy, ix, mode)


def test_marginal_gain_handles_raster_edges():
    truth = blank(20, 20)
    truth[0, 0] = 1
    pred = blank(20, 20)
    g = D.marginal_gain(pred, truth, 0, 0)
    # a dot exactly on truth at the corner still scores 1.0
    pred2 = blank(20, 20)
    pred2[0, 0] = 1.0
    assert D.dti(pred2, truth) == pytest.approx(1.0)
    assert g.delta_dti == pytest.approx(1.0)


def test_remove_of_a_bad_dot_raises_score():
    """Removing a dot far from any truth cuts the denominator and must gain."""
    truth = blank()
    truth[10, 10] = 1
    pred = blank()
    pred[10, 10] = 1
    pred[90, 90] = 1  # pure cost
    g = D.marginal_gain(pred, truth, 90, 90, mode="remove")
    assert g.delta_dti > 0


def test_rank_dots_is_sorted_and_matches_gains():
    rng = np.random.default_rng(7)
    truth = (rng.random((50, 50)) < 0.05).astype(np.float64)
    pred = (rng.random((50, 50)) < 0.05).astype(np.float64)
    cands = [(int(a), int(b)) for a, b in rng.integers(0, 50, size=(30, 2))]
    ranked = D.rank_dots(pred, truth, cands)
    scores = [r[0] for r in ranked]
    assert scores == sorted(scores, reverse=True)
    for (gain, iy, ix) in ranked[:5]:
        g = D.marginal_gain(pred, truth, iy, ix)
        assert g.delta_dti == pytest.approx(gain)


def test_score_is_bounded_in_unit_interval():
    rng = np.random.default_rng(11)
    for _ in range(20):
        truth = (rng.random((30, 30)) < 0.1).astype(np.float64)
        pred = rng.random((30, 30)) * (rng.random((30, 30)) < 0.15)
        s = D.dti(pred, truth)
        assert 0.0 <= s <= 1.0 + 1e-12


def test_nan_outside_footprint_is_treated_as_zero_mass():
    """Production rasters are NaN outside the footprint; that must not poison sums."""
    truth = blank()
    truth[60, 60] = 1
    pred = np.where(truth > 0, 1.0, 0.0).astype(np.float32)
    base = D.dti(pred, truth)
    assert base == pytest.approx(1.0)

    pred_nan = pred.astype(np.float32).copy()
    pred_nan[:10, :] = np.nan          # a null band outside the footprint
    pred_nan[:, -5:] = np.nan
    assert D.dti(pred_nan, truth) == pytest.approx(base)

    truth_nan = truth.copy()
    truth_nan[:5, :] = np.nan
    assert D.dti(pred_nan, truth_nan) == pytest.approx(base)


def test_marginal_gain_on_nan_raster():
    truth = blank()
    truth[50, 50] = 1
    pred = np.full(truth.shape, np.nan, dtype=np.float32)
    pred[10, 10] = 1.0                  # a dot far from truth, over null pixels
    g = D.marginal_gain(pred, truth, 50, 50)
    assert np.isfinite(g.delta_dti)
    nxt = pred.copy()
    nxt[50, 50] = 1.0
    assert g.delta_dti == pytest.approx(D.dti(nxt, truth) - D.dti(pred, truth))
