"""The repository carries two implementations of the DTI numerator T. They disagree.

`gems91.metric.components` sums the kernel credit of *every* dot into each truth
cell, so a cluster of dots around one truth cell keeps raising T (and DTI with it,
above 1 if the cluster is dense enough).
`gems91.relief.fast_binary_dti` gives each truth cell the credit of its *nearest*
dot, so T <= |G| and DTI <= 1.  A [0,1] raster cannot stack two dots on one cell,
so the disagreement is about *nearby* dots sharing a truth cell's kernel - which
is exactly what R0 has (11,415 of its 37,654 dots have a neighbour < 2.83 px).

Both are used in production code (the first for marginal-gain ranking and the
session-3/4 predictions, the second for every SGMC and lineage-mask control).
IR-91-33 records the disagreement. These tests pin it, so that neither convention
can drift silently.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems91 import metric, relief  # noqa: E402


def _one_truth_cell(shape=(9, 9)):
    truth = np.zeros(shape, dtype=bool)
    truth[4, 4] = True
    return truth


def _dots(cells, shape=(9, 9)):
    pred = np.zeros(shape, dtype=np.float32)
    for r, c in cells:
        pred[r, c] = 1.0
    return pred


def test_single_dot_on_isolated_truth_is_perfect_under_both_conventions():
    truth = _one_truth_cell()
    pred = _dots([(4, 4)])
    assert metric.dti(pred, truth) == 1.0
    assert relief.fast_binary_dti(pred.astype(bool), truth)["dti"] == 1.0


def test_two_dots_in_one_kernel_split_the_conventions():
    """Dots at d=0 and d=1 from one truth cell: sum 1.389 (above 1), per-cell 0.938."""
    truth = _one_truth_cell()
    pred = _dots([(4, 4), (4, 5)])
    assert round(float(metric.dti(pred, truth)), 6) == 1.388889
    assert round(float(relief.fast_binary_dti(pred.astype(bool), truth)["dti"]), 6) == 0.9375
    assert metric.dti(pred, truth) > 1.0 > relief.fast_binary_dti(pred.astype(bool), truth)["dti"]


def test_dataclass_components_match_the_bounded_convention_on_separated_truth():
    """When no truth cell is double-covered, both conventions agree exactly."""
    truth = np.zeros((12, 12), dtype=bool)
    truth[2, 2] = truth[9, 9] = True
    pred = _dots([(2, 2), (9, 9)], shape=(12, 12))
    assert np.isclose(metric.dti(pred, truth), relief.fast_binary_dti(pred.astype(bool), truth)["dti"])


def test_convention_gap_grows_with_redundancy():
    truth = _one_truth_cell()
    gaps = []
    for cells in ([(4, 4)], [(4, 4), (4, 5)], [(4, 4), (4, 5), (4, 3)]):
        pred = _dots(cells)
        gaps.append(metric.dti(pred, truth) - relief.fast_binary_dti(pred.astype(bool), truth)["dti"])
    assert gaps[0] == 0.0
    assert gaps[0] < gaps[1] < gaps[2]
