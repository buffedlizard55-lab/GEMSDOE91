"""Session 12: check scripts/dti.py against a LITERAL brute-force transcription of
the organizer's metric (DrivenData competition page 967, "Mathematical representation").

Official definitions, with d = Euclidean distance in pixels (100 m), R = 3 px, k(d) = max(1 - d/R, 0):

    TP_w = sum_{g in G} max_{x: d(x,g) <= R} p(x) k(d(x,g))
    FP_w = sum_{x: p(x) > 0} p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) k(d(x,g))]
    DTI  = TP_w / (TP_w + alpha FP_w + beta FN_w)          alpha = 0.2, beta = 0.8

Source: https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
(fetched 2026-10-24).  The brute force below uses no shortcut; if dti.py disagrees
with it, dti.py is wrong and the scores in the repo are suspect.

Also checks the identity TP_w + FN_w = |G| that the closed form relies on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import dti as D  # noqa: E402

R_PX = 3.0
ALPHA = 0.2
BETA = 0.8


def _k(d: float) -> float:
    return max(1.0 - d / R_PX, 0.0)


def official_dti_bruteforce(p: np.ndarray, g: np.ndarray):
    """Literal transcription of the organizer's definitions. Returns (DTI, TP, FP, FN)."""
    h, w = p.shape
    truth = [(y, x) for y in range(h) for x in range(w) if g[y, x] > 0]
    pred = [(y, x) for y in range(h) for x in range(w) if p[y, x] > 0]

    def dist(a, b):
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))

    tp = 0.0
    fn = 0.0
    for gy, gx in truth:
        best = 0.0
        for y in range(h):
            for x in range(w):
                d = dist((y, x), (gy, gx))
                if d <= R_PX:
                    best = max(best, p[y, x] * _k(d))
        tp += best
        fn += 1.0 - best

    fp = 0.0
    for y, x in pred:
        nearest_k = max((_k(dist((y, x), t)) for t in truth), default=0.0)
        fp += p[y, x] * (1.0 - nearest_k)

    den = tp + ALPHA * fp + BETA * fn
    score = tp / den if den > 0 else 0.0
    return score, tp, fp, fn


def _random_case(rng: np.random.Generator, n: int = 9):
    g = np.zeros((n, n))
    k = int(rng.integers(1, 6))
    for _ in range(k):
        g[rng.integers(0, n), rng.integers(0, n)] = 1.0
    p = np.zeros((n, n))
    mask = rng.random((n, n)) < 0.35
    p[mask] = rng.random(mask.sum())
    return p, g


@pytest.mark.parametrize("seed", list(range(40)))
def test_repo_dti_matches_literal_official_formula(seed):
    rng = np.random.default_rng(1000 + seed)
    p, g = _random_case(rng)
    score_ref, tp_ref, fp_ref, fn_ref = official_dti_bruteforce(p, g)
    # TP_w + FN_w = |G| exactly, by construction of the two sums.
    assert tp_ref + fn_ref == pytest.approx(float((g > 0).sum()), abs=1e-9)
    comp = D.components(p, g)
    assert comp.T == pytest.approx(tp_ref, abs=1e-9)
    # repo's FP term is S - M, the official FP_w
    assert comp.S - comp.M == pytest.approx(fp_ref, abs=1e-9)
    assert comp.score == pytest.approx(score_ref, abs=1e-9)


def test_closed_form_identity_used_in_reports():
    """DTI = T / (0.2 (T + FP_w) + 0.8 |G|) because TP_w + FN_w = |G| and alpha + beta = 1."""
    rng = np.random.default_rng(7)
    for _ in range(10):
        p, g = _random_case(rng)
        score, tp, fp, _ = official_dti_bruteforce(p, g)
        G = float((g > 0).sum())
        closed = tp / (0.2 * (tp + fp) + 0.8 * G)
        assert closed == pytest.approx(score, abs=1e-9)


def test_perfect_and_empty_predictions_against_literal_formula():
    g = np.zeros((7, 7))
    g[3, 1] = 1
    g[3, 5] = 1
    assert official_dti_bruteforce(g.copy(), g)[0] == pytest.approx(1.0)
    assert official_dti_bruteforce(np.zeros((7, 7)), g)[0] == pytest.approx(0.0)
    assert D.dti(g.copy(), g) == pytest.approx(1.0)
