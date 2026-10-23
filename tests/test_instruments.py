"""Unit tests for the report-only instruments and the gates' bookkeeping."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import gates, io, proxy  # noqa: E402


def test_triangular_kernel_is_one_at_the_centre_and_zero_beyond_radius():
    k = proxy._tri_kernel(3.0)
    assert k.shape == (7, 7)
    assert k[3, 3] == pytest.approx(1.0)
    # a corner is farther than the radius
    assert k[0, 0] == pytest.approx(0.0)
    assert k[3, 0] == pytest.approx(0.0)     # exactly R away -> zero


def test_auc_of_a_perfect_and_a_random_score():
    labels = np.array([0, 0, 1, 1], dtype=float)
    assert proxy._auc(np.array([0.1, 0.2, 0.8, 0.9]), labels) == pytest.approx(1.0)
    assert proxy._auc(np.array([0.9, 0.8, 0.2, 0.1]), labels) == pytest.approx(0.0)
    assert proxy._auc(np.array([0.5, 0.5, 0.5, 0.5]), labels) == pytest.approx(0.5)
    assert np.isnan(proxy._auc(np.array([0.1, 0.2]), np.array([0, 0])))


def test_uniform_truth_credit_falls_when_dots_are_stacked():
    spread = np.zeros((40, 40), dtype=bool)
    spread[20, 10] = True
    spread[20, 30] = True
    stacked = np.zeros((40, 40), dtype=bool)
    stacked[20, 10] = True
    stacked[20, 11] = True
    foot = np.ones((40, 40), dtype=bool)
    a = proxy.uniform_truth_credit(spread, foot)
    b = proxy.uniform_truth_credit(stacked, foot)
    assert a["uniform_truth_mean_credit"] > b["uniform_truth_mean_credit"]


def test_hide_and_recover_rewards_a_dot_inside_the_collar():
    cat = np.zeros((40, 40), dtype=bool)
    cat[:, 20] = True                      # a north-south trace
    foot = np.ones((40, 40), dtype=bool)
    near = np.zeros((40, 40), dtype=bool)
    near[10, 22] = True                    # 2 px from the trace
    far = np.zeros((40, 40), dtype=bool)
    far[10, 30] = True                     # 10 px from the trace
    a = proxy.hide_and_recover(near, cat, foot, draws=3)
    b = proxy.hide_and_recover(far, cat, foot, draws=3)
    assert a["proxy_mean_credit"] > b["proxy_mean_credit"]
    assert b["proxy_mean_credit"] == pytest.approx(0.0)


def test_dot_digest_depends_only_on_the_dot_set():
    a = np.zeros((5, 5), dtype=bool)
    a[1, 1] = a[2, 2] = True
    b = a.copy()
    assert io.dot_digest(a) == io.dot_digest(b)
    b[2, 2] = False
    assert io.dot_digest(a) != io.dot_digest(b)


def test_parent_diff_counts_moves_as_two_cells():
    p = np.zeros((6, 6), dtype=bool)
    p[1, 1] = p[3, 3] = True
    c = np.zeros((6, 6), dtype=bool)
    c[3, 3] = True             # this dot stays
    c[1, 2] = True             # this one relocated from (1, 1) to (1, 2)
    d = gates.parent_diff(p, c)
    assert d["added"] == 1 and d["removed"] == 1
    assert d["changed"] == 2
    assert d["pct_changed_of_parent"] == pytest.approx(100.0)
