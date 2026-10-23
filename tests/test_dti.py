"""Tests for the DTI algebra. No competition data: truth masks are synthetic.

    python -m pytest tests -q
"""

from __future__ import annotations

import numpy as np
import pytest

from tools import dti


def test_kernel_is_triangular_and_zero_beyond_radius():
    assert dti.triangular_weight(0.0) == pytest.approx(1.0)
    assert dti.triangular_weight(1.5) == pytest.approx(0.5)
    assert dti.triangular_weight(3.0) == pytest.approx(0.0)
    assert dti.triangular_weight(4.0) == pytest.approx(0.0)
    # negative distances are not physically meaningful but must not blow up
    assert dti.triangular_weight(-1.0) == pytest.approx(4.0 / 3.0)


def test_offsets_respect_radius():
    rr, cc, w = dti.window_offsets()
    assert np.all(np.hypot(rr, cc) < dti.RADIUS_PX)
    assert np.all(w > 0)
    assert len(rr) == 25  # integer offsets strictly inside a 3 px disc (dr,dc in -2..2)


def test_credit_map_single_dot_known_values():
    shape = (9, 9)
    cm = dti.credit_map(shape, np.array([[4.0, 4.0]]))
    assert cm[4, 4] == pytest.approx(1.0)
    assert cm[4, 5] == pytest.approx(1 - 1 / 3)
    assert cm[4, 7] == pytest.approx(0.0)       # exactly at the radius
    total = sum(dti.triangular_weight(np.hypot(dr, dc))
                for dr in range(-2, 3) for dc in range(-2, 3))
    assert cm.sum() == pytest.approx(total)


def test_credit_map_is_linear_in_dots():
    shape = (11, 11)
    a = dti.credit_map(shape, np.array([[5.0, 5.0]]))
    b = dti.credit_map(shape, np.array([[5.0, 6.0]]))
    both = dti.credit_map(shape, np.array([[5.0, 5.0], [5.0, 6.0]]))
    assert np.allclose(a + b, both)


def test_credit_map_ignores_pixels_outside_shape():
    cm = dti.credit_map((5, 5), np.array([[0.0, 0.0]]))
    assert cm.shape == (5, 5)
    assert cm[0, 0] == pytest.approx(1.0)
    assert cm[4, 4] == 0.0  # hypot(4,4) > 3


def test_credit_map_masks_to_footprint():
    footprint = np.zeros((9, 9), bool)
    footprint[4, 4:] = True
    cm = dti.credit_map((9, 9), np.array([[4.0, 4.0]]), shape_mask=footprint)
    assert cm[4, 3] == 0.0
    assert cm[4, 4] == pytest.approx(1.0)


def test_dti_formula_round_trip():
    T, S, M, G = 1.0, 20.0, 1.0, 5.0
    expect = T / (0.2 * T + 0.2 * (S - M) + 0.8 * abs(G))
    assert dti.dti(T, S, M, G) == pytest.approx(expect)
    assert dti.dti(0.0, 1.0, 0.0, 0.0) == 0.0


def test_pay_threshold_matches_derivation():
    # For a fixed configuration with DTI = d, one extra unit-mass dot pays iff
    # its credit c > 0.2*d, because the denominator grows by exactly 0.2.
    for d in (0.19, 0.28, 0.40):
        thr = dti.pay_threshold(d)
        assert thr == pytest.approx(0.2 * d)
    assert dti.pay_threshold(0.28) == pytest.approx(0.056)


@pytest.mark.parametrize("d_target", [0.20, 0.28, 0.35])
def test_threshold_is_exact_under_stated_assumptions(d_target):
    """Numerically locate the break-even credit and compare with 0.2*DTI."""
    T, G = 1.0, 0.2
    den = T / d_target
    S_minus_M = (den - 0.2 * T - 0.8 * abs(G)) / 0.2   # (S - M) that realises d_target
    S = S_minus_M + T
    assert dti.dti(T, S, T, G) == pytest.approx(d_target)

    thr = dti.pay_threshold(d_target)
    # a dot with credit c: dT = c, dS = 1, dM = c
    for c, sign in [(thr * 0.9, -1), (thr * 1.1, +1)]:
        gain = dti._gain(T, S, T, G, dT=c, dS=1.0, dM=c)
        assert np.sign(gain) == sign, f"c={c} thr={thr} gain={gain}"


def test_clustered_truth_lowers_the_geometric_bar():
    """Brief section 2: "line-like truth lowers that bar".

    The bar is a threshold on CREDIT, not on distance. Where truth pixels stack up
    (a trace, and more so a junction), one dot at the same geometric offset earns
    much more credit, so it still pays at an offset that would be worthless against
    an isolated truth pixel. Measured here at a fixed 2.9 px offset:
      isolated pixel      -> credit ~0.033  (< 0.056 bar) -> negative gain
      junction/stack      -> credit ~0.33   (> bar)       -> positive gain
    A lone straight line at 2.9 px is NOT enough to clear the bar, because its
    along-strike neighbours fall outside the 3 px radius; this is why the effect the
    brief describes is really about truth DENSITY (junction, step-over, dense trace),
    not about straightness. Recorded in docs/MECHANISMS.md.
    """
    d_target = 0.28
    T, G = 1.0, 0.2
    S_minus_M = (T / d_target - 0.2 * T - 0.8 * abs(G)) / 0.2
    S = S_minus_M + T
    thr = dti.pay_threshold(d_target)

    iso = np.zeros((15, 15), bool)
    iso[7, 7] = True
    junction = np.zeros((15, 15), bool)
    junction[7, 7] = True
    junction[6, 7] = junction[8, 7] = junction[7, 6] = junction[7, 8] = True

    dot = np.array([[9.9, 7.0]])            # 2.9 px below the truth pixel above
    c_iso = float(dti.credit_map(iso.shape, dot)[iso].sum())
    c_junc = float(dti.credit_map(junction.shape, dot)[junction].sum())
    assert c_iso < thr < c_junc, (c_iso, thr, c_junc)

    g_iso = dti._gain(T, S, T, G, dT=c_iso, dS=1.0, dM=1 - 2.9 / 3)
    g_junc = dti._gain(T, S, T, G, dT=c_junc, dS=1.0, dM=0.3)
    assert g_iso < 0 < g_junc


def test_duplicate_dot_is_exactly_neutral_not_negative():
    """A unit of mass that lands entirely on already-covered truth is FREE in this
    algebra: dS = +1 is cancelled by dM = +1, so (S - M) is unchanged. Wasted mass
    only costs when it lands where truth is not (dM = 0). This is the arithmetic
    reason PRUNE (which removes mass that M already credits) is a small-effect axis
    and SNAP (which raises dT without raising dS) is the cleaner lever."""
    truth = np.zeros((11, 11), bool)
    truth[5, 5] = True
    dots = np.array([[5.0, 5.0]])
    credit = dti.credit_map(truth.shape, dots)
    T = float(np.minimum(1.0, credit)[truth].sum())
    m = dti.score_additions(truth, np.array([[5.0, 5.0]]), credit=credit, T=T, M=T)[0]
    assert m.delta_t == pytest.approx(0.0)
    assert m.gain == pytest.approx(0.0, abs=1e-12)

    # mass far from truth does cost: dS only
    far = dti.score_additions(truth, np.array([[0.0, 0.0]]), credit=credit, T=T, M=T)[0]
    assert far.delta_t == 0.0 and far.delta_m == 0.0
    assert far.gain < 0.0


def test_score_additions_ranks_near_over_far():
    truth = np.zeros((21, 21), bool)
    truth[10, 10] = True
    cand = np.array([[10.0, 10.0], [10.0, 11.0], [10.0, 12.0], [13.0, 13.0]])
    ms = dti.score_additions(truth, cand, T=0.0, M=0.0, G=1.0)
    gains = [m.gain for m in ms]
    assert gains[0] > gains[1] > gains[2] > gains[3]
    assert gains[3] == pytest.approx(0.0)  # outside the radius: dT = dM = 0, dS = 0 here
    # with a non-empty existing dot set the same far dot is a net cost
    far_with_mass = dti.score_additions(truth, cand[3:], T=0.5, M=0.5, G=1.0)[0]
    assert far_with_mass.gain < 0.0


def test_greedy_select_avoids_double_counting():
    truth = np.zeros((15, 15), bool)
    truth[7, 5:12] = True
    cand = np.array([[7.0, 7.0], [7.0, 7.0], [7.0, 7.0]])  # three identical candidates
    chosen = dti.greedy_select(truth, cand, k=3, G=float(truth.sum()))
    assert len(chosen) == 3
    assert chosen[0].gain > chosen[1].gain  # the second duplicate is worth less
    assert chosen[2].gain <= chosen[1].gain


def test_greedy_select_matches_credit_after_commit():
    """Two dots that both cover the same single truth pixel: the second earns only
    the remainder allowed by the cap, not the same credit as the first."""
    truth = np.zeros((15, 15), bool)
    truth[8, 7] = True
    cand = np.array([[7.0, 7.0], [9.0, 7.0]])   # both 1 px from the truth pixel
    chosen = dti.greedy_select(truth, cand, k=2, G=1.0)
    assert chosen[0].index == 0
    assert chosen[0].delta_t == pytest.approx(2 / 3)
    assert chosen[1].delta_t == pytest.approx(1 / 3)


def test_constant_G_assumption_is_documented():
    """Guard: if the official metric lets |G| shrink, the bar moves. Both readings
    must bracket the number quoted to the human, and the docstring must say so."""
    d = 0.28
    bar_constant_G = dti.pay_threshold(d)
    bar_shrinking_G = 0.2 * d / (1 + 0.8 * d)
    assert bar_constant_G == pytest.approx(0.056)
    assert bar_shrinking_G == pytest.approx(0.04575, abs=1e-4)
    assert "ASSUMPTIONS" in dti.__doc__
