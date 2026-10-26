"""Unit tests for the S22-XB library (no data files needed): exact DTI algebra, budgets, global-collar emission."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import ndimage as ndi

from gems91 import xbreed22 as X
from vendor.gems57 import metric as M


def test_quadrant_budgets_sum_to_the_competition_dot_budget_and_are_equalized():
    assert sum(X.QUAD_BUDGETS) == X.DOT_BUDGET == 37_654
    assert max(X.QUAD_BUDGETS) - min(X.QUAD_BUDGETS) <= 1


def test_nested_step_algebra_is_exact_for_synthetic_pure_false_positive_removal():
    """Build a truth set, a dot set with known credit, and add/remove pure-FP dots: the identified T must be exact."""
    rng = np.random.default_rng(22)
    h = w = 160
    truth = np.zeros((h, w), bool)
    truth[40, 20:140] = True
    truth[100:140, 60] = True
    dots = np.zeros((h, w), bool)
    dots[40, 22:140:3] = True            # dots sitting on a truth line
    dots[100:140:3, 60] = True
    # pure false positives: far (> 3 px kernel) from all truth pixels
    far = ndi.distance_transform_edt(~truth) > 6.0
    ys, xs = np.nonzero(far & ~dots)
    pick = rng.choice(len(ys), size=300, replace=False)
    fp_set = np.zeros_like(dots)
    fp_set[ys[pick], xs[pick]] = True

    full = dots | fp_set
    s_full = M.dti_binary(full, truth)
    s_base = M.dti_binary(dots, truth)
    T_true = s_base["tp"]
    T_hat = X.credit_from_pure_fp_step(int(full.sum()), int(dots.sum()), s_full["dti"], s_base["dti"])
    assert T_hat == pytest.approx(T_true, rel=1e-9)
    # and the forward model predicts the larger raster's score from the smaller one
    pred = X.predicted_dti_after_pure_fp(T_true, s_base["dti"], -int(fp_set.sum()))
    assert pred == pytest.approx(s_full["dti"], rel=1e-9)


def test_forward_and_inverse_helpers_are_mutually_consistent():
    T = X.credit_from_pure_fp_step(44090, 40199, 0.2600, 0.2708)
    assert X.predicted_dti_after_pure_fp(T, 0.2600, 44090 - 40199) == pytest.approx(0.2708, rel=1e-12)


def test_final_emission_respects_the_global_catalogue_collar_across_quadrant_borders():
    """A catalogue trace running along a quadrant border must keep dots >COLLAR_PX away on BOTH sides."""
    h, w = 120, 120
    fp = np.ones((h, w), bool)
    cat = np.zeros((h, w), bool)
    cat[:, 60] = True                      # vertical catalogue trace exactly on the border x = 60
    d_cat = ndi.distance_transform_edt(~cat).astype(np.float32)
    surf = np.zeros((h, w), np.float32)
    surf[:, 56:65] = 0.9                   # the surface is hottest right beside the trace
    surf += np.random.default_rng(1).uniform(0, 0.1, size=surf.shape).astype(np.float32)
    left = np.zeros((h, w), bool)
    left[:, :60] = True
    right = ~left
    for region in (left, right):
        old = X.QUAD_BUDGETS
        try:
            X.QUAD_BUDGETS = (50, 50, 50, 50)
            dots = X.emit_quadrant_final(surf, cat, fp, region, d_cat, 0, "celf")
        finally:
            X.QUAD_BUDGETS = old
        assert int((dots > 0).sum()) == 50
        assert float(d_cat[dots > 0].min()) > X.COLLAR_PX
        assert not (dots > 0)[~region].any()
        assert not (dots > 0)[cat].any()


def test_arm_definitions_share_pdwc_columns_and_keep_the_pure_subsurface_submodel_free_of_topo_columns():
    n_p, n_psub, n_h, n_hsub = X.feature_counts()
    assert (n_p, n_psub, n_h, n_hsub) == (66, 48, 16, 14)
    full_c, sub_c = X.arm_blocks("C")
    assert full_c[0] == ("P", list(range(66))) and full_c[1] == ("H", list(range(16)))
    # the sub-model uses only the 48 subsurface PDWC columns and the 14 subsurface-only HGBR columns (not B12/B19-dependent 14,15)
    assert sub_c[0] == ("P", list(range(48))) and sub_c[1] == ("H", list(range(14)))
    full_a, sub_a = X.arm_blocks("A")
    assert full_a == [full_c[0]] and sub_a == [sub_c[0]]
    full_b, sub_b = X.arm_blocks("B")
    assert full_b == [("H", list(range(16)))] and sub_b == [("H", list(range(14)))]
