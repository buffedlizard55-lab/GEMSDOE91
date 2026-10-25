from __future__ import annotations

import numpy as np
import pytest

from gems91 import dd_vtc_pu as DD
from gems91 import euas_s15 as EUAS
from gems91 import mhtr_coda as MC
from gems91 import ptha as PTHA
from gems91 import spac_coda as SPAC


def test_euler_3d_recovers_depth_convergence_and_step_vs_plug() -> None:
    """Analytical verification of 3-D Euler Homogeneity (`Reid et al. 1990`) sign,
    depth `z0 > 0` (+z downward), ray convergence, and structural-index discrimination.
    """
    h, w = 81, 81
    dx = 100.0
    yy, xx = np.indices((h, w), dtype=np.float64)
    y_m = (yy - 40.0) * dx
    x_m = (xx - 40.0) * dx
    z_true = 500.0  # meters depth (+z downward)

    # Case 1: 3-D point/plug source (structural index N = 2.0): F = C / r^2
    c_amp = 1.0e8
    r2_3d = x_m * x_m + y_m * y_m + z_true * z_true
    r_3d = np.sqrt(r2_3d)
    f_plug = (c_amp / r2_3d + 250.0).astype(np.float32)  # + constant regional background!
    fx_plug = (-2.0 * c_amp * x_m / (r2_3d ** 2)).astype(np.float32)
    fy_plug = (-2.0 * c_amp * y_m / (r2_3d ** 2)).astype(np.float32)
    fz_plug = (+2.0 * c_amp * z_true / (r2_3d ** 2)).astype(np.float32)  # dF/dz_down > 0 at apex!

    z0_p, _, _, step_vs_plug_on_plug = EUAS.solve_windowed_euler_3d(
        f_plug, fx_plug, fy_plug, fz_plug, win=7, dx_m=dx, n_step=0.5, n_plug=2.0
    )
    # Using n_step=2.0 directly should recover z_true ~ 500 m at (40, 40):
    z0_2, focus_2, conv_2, _ = EUAS.solve_windowed_euler_3d(
        f_plug, fx_plug, fy_plug, fz_plug, win=7, dx_m=dx, n_step=2.0, n_plug=0.5
    )
    assert 460.0 <= float(z0_2[40, 40]) <= 540.0
    assert float(focus_2[40, 40]) > 0.90
    assert float(conv_2[40, 40]) > 0.50
    # On a true N=2.0 plug, step_vs_plug is strongly negative across the plug core!
    assert float(step_vs_plug_on_plug[40, 40]) < -0.50
    assert float(step_vs_plug_on_plug[40, 39]) < -0.20

    # Case 2: Linear N-S striking source with N = 0.5 along x_m = 0 at depth z_true = 500 m
    # (plus weak N-S modulation so 3-D window is full-rank, mimicking real along-strike variation):
    r2_lin = x_m * x_m + 0.02 * (y_m * y_m) + z_true * z_true
    f_lin = (1.0e5 * (r2_lin ** -0.25) + 120.0).astype(np.float32)
    fx_lin = (-0.5 * 1.0e5 * x_m * (r2_lin ** -1.25)).astype(np.float32)
    fy_lin = (-0.5 * 1.0e5 * 0.02 * y_m * (r2_lin ** -1.25)).astype(np.float32)
    fz_lin = (+0.5 * 1.0e5 * z_true * (r2_lin ** -1.25)).astype(np.float32)

    z0_s, focus_s, conv_s, step_vs_plug_on_step = EUAS.solve_windowed_euler_3d(
        f_lin, fx_lin, fy_lin, fz_lin, win=7, dx_m=dx, n_step=0.5, n_plug=2.0
    )
    assert 440.0 <= float(z0_s[40, 40]) <= 560.0
    assert float(focus_s[40, 40]) > 0.85
    assert float(focus_s[40, 40]) > float(focus_s[40, 32])
    assert float(conv_s[40, 40]) > 0.25
    assert float(step_vs_plug_on_step[40, 40]) > 0.0
    assert float(step_vs_plug_on_step[40, 37]) > 0.002


def test_fft_upward_worms_dip_migration_direction() -> None:
    """Over an eastward-dipping normal fault step (+x hanging wall), upward continuation
    shifts the horizontal-gradient maximum toward +x (`mig_dx > 0` along the surface trace).
    """
    h, w = 128, 128
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.indices((h, w), dtype=np.float32)
    # Superpose shallow step at x=60 and deeper downdip extension at x=68 (dipping East +x):
    shallow = -np.tanh((xx - 60.0) / 1.5)
    deep = -1.6 * np.tanh((xx - 68.0) / 8.0)
    field = (shallow + deep).astype(np.float32)

    dz_down, persist, _, mig_dx = EUAS.fft_laplace_vertical_derivative_and_worms(field, fp, dx_m=100.0)
    assert dz_down.shape == (h, w)
    assert np.all(np.isfinite(persist))
    # Persistence peaks near the fault zone rather than far away at x=20:
    assert float(persist[64, 61]) > float(persist[64, 20])
    # Along the shallow trace x=60, the 800m crest lies eastward (+x), so mig_dx > 0:
    assert float(mig_dx[64, 60]) > 0.0


def test_fold_depth_deconfounded_conductivity_zero_test_leakage() -> None:
    """Perturbing `B17` wildly on the test quadrant MUST NOT alter `fold_cond_depth_res`
    on the training quadrant.
    """
    h, w = 40, 40
    fp = np.ones((h, w), dtype=bool)
    n_fp = h * w
    rng = np.random.default_rng(42)

    X_static = np.zeros((n_fp, len(DD.ALL_STATIC_FEATURE_NAMES)), dtype=np.float32)
    depth_m = rng.uniform(0.0, 2500.0, size=n_fp).astype(np.float32)
    elev_m = rng.normal(0.0, 150.0, size=n_fp).astype(np.float32)
    X_static[:, 14] = depth_m
    X_static[:, 11] = elev_m
    # Conductivity driven by basin depth + localized hydrothermal anomaly:
    X_static[:, 16] = np.expm1(0.6 * (depth_m / 1000.0) + rng.normal(0.0, 0.05, size=n_fp)).astype(np.float32)

    train_2d = np.zeros((h, w), dtype=bool)
    train_2d[:20, :] = True
    train_fp = train_2d[fp]

    res_a = EUAS.compute_fold_depth_deconfounded_conductivity(X_static, fp, train_fp)

    X_corrupt = X_static.copy()
    X_corrupt[~train_fp, 16] = 1.0e6  # extreme perturbation strictly in test region!
    res_b = EUAS.compute_fold_depth_deconfounded_conductivity(X_corrupt, fp, train_fp)

    # Exact equality on the standardized residual column (`col 0`) inside training region:
    np.testing.assert_allclose(res_a[train_fp, 0], res_b[train_fp, 0], rtol=0.0, atol=1e-6)


def test_feature_spec_excludes_corrupted_and_topo_columns() -> None:
    n = 64
    X_st = np.zeros((n, len(DD.ALL_STATIC_FEATURE_NAMES)), dtype=np.float32)
    X_11 = np.zeros((n, len(MC.S11_MHTR_FEATURE_NAMES)), dtype=np.float32)
    X_12 = np.zeros((n, len(SPAC.S12_SPAC_STATIC_FEATURE_NAMES)), dtype=np.float32)
    X_pt = np.zeros((n, len(PTHA.PTHA_FEATURE_NAMES)), dtype=np.float32)
    X_15 = np.zeros((n, len(EUAS.S15_EUAS_FEATURE_NAMES)), dtype=np.float32)
    X_fc = np.zeros((n, 2), dtype=np.float32)
    X_ac = np.zeros((n, len(SPAC.S12_AUTOCONTEXT_FEATURE_NAMES)), dtype=np.float32)

    spec_e1 = EUAS.build_s15_feature_spec(
        X_static=X_st, X_s11=X_11, X_s12=X_12, X_ptha=X_pt, X_s15=X_15, include_group_b=False
    )
    spec_e2 = EUAS.build_s15_feature_spec(
        X_static=X_st, X_s11=X_11, X_s12=X_12, X_ptha=X_pt, X_s15=X_15,
        include_group_b=True, X_fold_cond=X_fc
    )
    spec_e3 = EUAS.build_s15_feature_spec(
        X_static=X_st, X_s11=X_11, X_s12=X_12, X_ptha=X_pt, X_s15=X_15,
        include_group_b=True, X_fold_cond=X_fc, X_autocontext=X_ac
    )
    # 36 static + 16 s11 + 15 s12 + 20 ptha + 12 s15_A = 99
    assert spec_e1.n_cols == 99
    assert spec_e2.n_cols == 109
    assert spec_e3.n_cols == 119

    forbidden_broken = {
        "e1_grav_tilt",
        "e1_rtp_tilt",
        "e1_updip_grav_tilt_zero",
        "e1_updip_grav_tilt_hd",
        "e1_updip_rtp_tilt_hd",
        "e2_anderson_slip_dilation",
        "e3_seismic_conduit_index",
    }
    assert forbidden_broken.isdisjoint(set(spec_e3.feature_names))

    sub_names = {spec_e3.feature_names[j] for j in spec_e3.subsurface_col_idx}
    assert EUAS.TOPO_EXPOSURE_FEATURE_NAMES.isdisjoint(sub_names)
    assert "euas_euler_mag_focus" in sub_names
    assert "s12_spi_local_wavenum" in sub_names
    assert "fold_cond_depth_res" in sub_names
    assert "ac_wash_bridge_2km" in sub_names


def test_oof_dinkelbach_zero_test_leakage_and_geometry() -> None:
    h, w = 60, 60
    rng = np.random.default_rng(7)
    oof_tr = rng.uniform(0.05, 0.85, size=(h, w)).astype(np.float32)
    te_a = rng.uniform(0.05, 0.85, size=(h, w)).astype(np.float32)
    crest = rng.uniform(0.0, 1.0, size=(h, w)).astype(np.float32)

    tr_elig = np.zeros((h, w), dtype=bool)
    tr_elig[:40, :] = True
    te_elig = np.zeros((h, w), dtype=bool)
    te_elig[42:, :] = True  # sterile gap between train and test

    dots_a, info_a = EUAS.emit_oof_calibrated_selfcredit_dinkelbach(
        oof_train_prob_2d=oof_tr,
        test_prob_2d=te_a,
        crest_2d=crest,
        train_eligible_2d=tr_elig,
        test_eligible_2d=te_elig,
        train_target_dots=45,
        test_quota_ref=20,
        min_spacing_px=2.55,
    )
    te_b = te_a * 0.25 + 0.1
    _, info_b = EUAS.emit_oof_calibrated_selfcredit_dinkelbach(
        oof_train_prob_2d=oof_tr,
        test_prob_2d=te_b,
        crest_2d=crest,
        train_eligible_2d=tr_elig,
        test_eligible_2d=te_elig,
        train_target_dots=45,
        test_quota_ref=20,
        min_spacing_px=2.55,
    )
    # Calibration thresholds depend ONLY on oof_train_prob_2d and must be strictly positive (IR-91-S15-03):
    assert info_a["tau_oof_train"] > 0.0
    assert info_a["tau_oof_train"] == info_b["tau_oof_train"]
    assert info_a["q_low_oof_train"] == info_b["q_low_oof_train"]

    # Binary {0, 1}, zero outside te_elig, pairwise spacing >= 2.55 px:
    assert set(np.unique(dots_a)).issubset({0.0, 1.0})
    assert int((dots_a[~te_elig] > 0).sum()) == 0
    rr, cc = np.nonzero(dots_a > 0)
    if rr.size > 1:
        dy = rr[:, None] - rr[None, :]
        dx = cc[:, None] - cc[None, :]
        d2 = dy * dy + dx * dx + np.eye(rr.size) * 1e6
        assert float(np.sqrt(d2.min())) >= 2.55 - 1e-5
