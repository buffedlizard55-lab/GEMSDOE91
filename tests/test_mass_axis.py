"""Unit tests for the MASS builder's pure parts. No competition data needed.

These do not prove a score. They pin the two things a later session could silently
change: the ranking must be a deterministic function of the pinned field, and the
prediction algebra must move in the direction the mechanism cards claim.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import build_mass as B  # noqa: E402


def test_rank_is_deterministic_and_order_preserving():
    field = np.zeros((40, 40), dtype=bool)
    field[5:30, 10] = True          # a long trace
    field[20, 20] = True            # an isolated speck
    r1 = B.field_rank(field)
    r2 = B.field_rank(field)
    assert np.array_equal(r1, r2)
    assert r1[15, 10] > r1[20, 20]  # centre of a trace outranks an isolated pixel


def _ridge_field(seed=0, size=80, lines=25):
    """Irregular random-walk ridges: the geometry a real structural field has."""
    rng = np.random.default_rng(seed)
    f = np.zeros((size, size), dtype=bool)
    for _ in range(lines):
        y, x = rng.integers(5, size - 5, 2)
        ang = rng.uniform(0, 2 * np.pi)
        for _ in range(int(rng.integers(15, 40))):
            f[int(y) % size, int(x) % size] = True
            ang += rng.normal(0, 0.4)
            y += np.sin(ang)
            x += np.cos(ang)
    return ndi.binary_dilation(f, iterations=1)


def _tri_support(field, radius=3):
    k = np.zeros((2 * radius + 1,) * 2, dtype=np.float32)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            k[dy + radius, dx + radius] = max(0.0, 1.0 - np.hypot(dy, dx) / radius)
    return ndi.convolve(field.astype(np.float32), k, mode="constant")


def test_rank_is_near_tie_free_and_finer_than_kernel_support():
    """The first draft tied 4,849 R0 dots at triangular support 1.0, so row order
    decided the drop. The gaussian rank must be much finer on the same geometry."""
    field = _ridge_field()
    gauss = B.field_rank(field)[field]
    tri = np.round(_tri_support(field)[field], 6)
    _, cg = np.unique(np.round(gauss, 9), return_counts=True)
    _, ct = np.unique(tri, return_counts=True)
    assert cg.max() / len(gauss) <= 0.01          # no tie group above 1 %
    assert len(np.unique(np.round(gauss, 9))) > 4 * len(np.unique(tri))


def test_prediction_sign_follows_the_break_even_rule():
    """A removed dot pays only if its credit is below 0.2 * DTI."""
    below = B.predict_from_instrument({"dT": -10.0, "dS_minus_M": -1000.0, "dden": -202.0})
    above = B.predict_from_instrument({"dT": -300.0, "dS_minus_M": -1000.0, "dden": -260.0})
    assert below["central"] > 0 > above["central"]


def test_prediction_range_brackets_the_central_value():
    p = B.predict_from_instrument({"dT": -500.0, "dS_minus_M": -4000.0, "dden": -900.0})
    assert p["range"][0] <= p["central"] <= p["range"][1]


def test_no_added_dot_breaks_the_suppression_radius():
    parent = np.zeros((20, 20), dtype=bool)
    parent[10, 10] = True
    field = np.zeros((20, 20), dtype=bool)
    field[3:17, 9:12] = True
    rank = B.field_rank(field)
    dcat = np.full((20, 20), 50.0)
    B.ARMS["_test_add"] = dict(kind="add", n=6, label="test")
    try:
        built = B.build_arm("_test_add", parent, dcat, rank, field)
    finally:
        B.ARMS.pop("_test_add", None)
    ys, xs = np.nonzero(built["dots"])
    pts = np.c_[ys, xs]
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    np.fill_diagonal(d, np.inf)
    assert d.min() >= B.MIN_DOT_SEPARATION_PX - 1e-9


def test_arm_dose_is_inside_the_brief_band():
    for key, cfg in B.ARMS.items():
        assert 0.01 * B.PARENT_DOTS <= cfg["n"] <= 0.50 * B.PARENT_DOTS, key
