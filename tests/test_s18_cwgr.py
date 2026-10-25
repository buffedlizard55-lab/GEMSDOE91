"""Unit and physics-invariance tests for Session 18 `S18-CWGR` (`src/gems91/cwgr18.py`)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from affine import Affine

from gems91.cwgr18 import (
    CWGR_FEATURE_NAMES,
    CWGR_STRICT_TOPO_FEATURE_NAMES,
    CWGR_SUBSURFACE_FEATURE_NAMES,
    CWGR_TOPO_ONLY_NAMES,
    athy_strip_gravity,
    compute_fold_area_quotas,
    compute_unmapped_fault_posterior,
    emit_cwgr_submodular_skeleton,
    emit_fold_quota_dots_submodular,
    estimate_sar_propensity,
    extract_cwgr_features,
    fit_predict_specialist_cwgr,
    pool_tri_specialists_logit,
    rank_logit_standardize_per_quadrant,
    steerable_g2h2_quadrature,
)


def _synthetic_footprint(h: int = 96, w: int = 96) -> np.ndarray:
    fp = np.zeros((h, w), dtype=bool)
    fp[8 : h - 8, 8 : w - 8] = True
    return fp


def test_steerable_g2h2_separates_step_trough_and_circular_mimic() -> None:
    h, w = 96, 96
    fp = _synthetic_footprint(h, w)
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")

    # 1. Sharp N-S fault step contact at x = 48 with -3.4e38 sentinels outside footprint
    step_field = np.tanh((xx - 48.0) / 1.5).astype(np.float32)
    step_field[~fp] = np.float32(-3.4028235e38)
    q_step = steerable_g2h2_quadrature(step_field, fp, sigmas=(1.8, 3.6))
    for k, arr in q_step.items():
        assert arr.dtype == np.float32
        assert np.all(np.isfinite(arr)), f"Non-finite in {k}"
        assert np.all(arr[~fp] == 0.0), f"Non-zero outside footprint in {k}"

    # Step contact at x=48 should peak in odd_step & crest, exceeding off-fault background
    assert float(q_step["odd_step"][48, 48]) > float(q_step["odd_step"][48, 24]) + 0.25
    assert float(q_step["crest"][48, 48]) > float(q_step["crest"][48, 24]) + 0.20

    # 2. Linear hydrothermal demagnetization trough (local minimum corridor along x = 48)
    trough_field = (-np.exp(-0.5 * ((xx - 48.0) / 2.0) ** 2)).astype(np.float32)
    trough_field[~fp] = np.float32(-3.4028235e38)
    q_trough = steerable_g2h2_quadrature(trough_field, fp, sigmas=(1.8, 3.6))
    assert float(q_trough["even_trough"][48, 48]) > float(q_trough["even_peak"][48, 48]) + 0.35

    # 3. Circular volcanic plug center should have much lower tubular anisotropy than linear step
    plug_field = np.exp(-0.5 * (((xx - 48.0) ** 2 + (yy - 48.0) ** 2) / (5.0**2))).astype(np.float32)
    q_plug = steerable_g2h2_quadrature(plug_field, fp, sigmas=(1.8, 3.6))
    assert float(q_step["aniso"][48, 48]) > float(q_plug["aniso"][48, 48]) + 0.45


def test_cwgr_subsurface_columns_are_bitwise_band12_band19_invariant(tmp_path: Path) -> None:
    rng = np.random.default_rng(1801)
    h, w = 72, 76
    fp = _synthetic_footprint(h, w)
    bands_a = rng.normal(0.0, 1.0, size=(19, h, w)).astype(np.float32)
    bands_a[14] = np.abs(bands_a[14]) * 400.0  # depth_to_base_surf (m)
    bands_a[:, ~fp] = np.float32(-3.4028235e38)

    # Create GDR CSV including a banned dist_known_fault_px column to verify safe exclusion
    gdr_csv = tmp_path / "gdr_sample.csv"
    gdr_csv.write_text(
        "row,col,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c,thermalclass,dist_known_fault_px\n"
        "35,35,62.0,165.0,145.0,185.0,hot,0.0\n"
        "40,42,48.0,140.0,130.0,170.0,warm,999.0\n"
    )
    transform = Affine(100.0, 0.0, 0.0, 0.0, -100.0, 7200.0)

    feat_a = extract_cwgr_features(bands_a, fp, gdr_csv_path=gdr_csv, gdr_transform=transform)
    assert feat_a.shape == (18, h, w)
    assert len(CWGR_FEATURE_NAMES) == 18
    assert len(CWGR_SUBSURFACE_FEATURE_NAMES) == 15
    assert len(CWGR_TOPO_ONLY_NAMES) == 3
    assert set(CWGR_TOPO_ONLY_NAMES).issubset(CWGR_STRICT_TOPO_FEATURE_NAMES)
    assert np.all(np.isfinite(feat_a))
    assert float(feat_a.min()) >= 0.0
    assert float(feat_a.max()) <= 1.0
    assert np.all(feat_a[:, ~fp] == 0.0)

    # Corrupt Band 12 (idx 11) and Band 19 (idx 18) with huge perturbations
    bands_b = bands_a.copy()
    bands_b[11] = rng.uniform(-5000.0, 5000.0, size=(h, w)).astype(np.float32)
    bands_b[18] = rng.uniform(0.0, 85.0, size=(h, w)).astype(np.float32)
    feat_b = extract_cwgr_features(bands_b, fp, gdr_csv_path=gdr_csv, gdr_transform=transform)

    # Exact 0.0 bitwise difference on all 15 subsurface columns (0..14)
    max_sub_diff = float(np.max(np.abs(feat_a[:15] - feat_b[:15])))
    assert max_sub_diff == 0.0
    # Topographic columns (15..17) DO respond to Band 12 / Band 19
    assert float(np.max(np.abs(feat_a[15:] - feat_b[15:]))) > 0.05


def test_rank_logit_standardization_equalizes_skewed_quadrants() -> None:
    rng = np.random.default_rng(42)
    h, w = 80, 80
    fp = _synthetic_footprint(h, w)
    q0 = np.zeros((h, w), dtype=bool); q0[:40, :40] = True
    q1 = np.zeros((h, w), dtype=bool); q1[:40, 40:] = True
    q2 = np.zeros((h, w), dtype=bool); q2[40:, :40] = True
    q3 = np.zeros((h, w), dtype=bool); q3[40:, 40:] = True
    folds = [{"region": q & fp} for q in (q0, q1, q2, q3)]

    base = rng.uniform(0.01, 0.99, size=(h, w)).astype(np.float32)
    # Apply severe quadrant-specific monotone calibration distortions
    skewed = base.copy()
    skewed[q0] = 0.15 * base[q0]
    skewed[q1] = np.power(base[q1], 3.0)
    skewed[q2] = np.sqrt(base[q2])
    skewed[q3] = 0.50 + 0.45 * base[q3]
    skewed[~fp] = 0.0

    std = rank_logit_standardize_per_quadrant(skewed, folds, fp)
    assert std.dtype == np.float32
    assert np.all(std[~fp] == 0.0)
    means = [float(std[f["region"]].mean()) for f in folds]
    p95s = [float(np.percentile(std[f["region"]], 95.0)) for f in folds]
    assert max(means) - min(means) < 1e-4
    assert max(p95s) - min(p95s) < 2e-3


def test_sar_propensity_and_unmapped_posterior_monotonicity() -> None:
    rng = np.random.default_rng(99)
    n = 5000
    fp = np.ones(n, dtype=bool)
    fp[:100] = False
    train_dom = fp.copy()
    train_dom[3500:] = False  # held-out fold

    vis = rng.uniform(0.0, 1.0, size=n).astype(np.float32)
    # Simulate SAR mapper bias: positives observed more frequently when vis is high
    true_fault = rng.uniform(0.0, 1.0, size=n) < 0.15
    observed_s = true_fault & (rng.uniform(0.0, 1.0, size=n) < (0.20 + 0.70 * vis))

    # Corrupt held-out labels to prove estimate_sar_propensity ignores holdout labels
    obs_corrupted = observed_s.copy()
    obs_corrupted[~train_dom] = True

    e1, w1, diag1 = estimate_sar_propensity(vis, fp, train_dom, observed_s)
    e2, w2, _ = estimate_sar_propensity(vis, fp, train_dom, obs_corrupted)

    assert np.allclose(e1, e2)
    assert np.allclose(w1, w2)
    assert diag1["beta1"] > 0.0
    assert abs(diag1["pos_weight_mean"] - 1.0) < 1e-4
    assert np.all(e1[~fp] == 0.0)

    # At equal raw probability p = 0.35, low-visibility concealed pixel has higher P(Y=1|S=0,x)
    prob_2d = np.full((10, 10), 0.35, dtype=np.float32)
    prop_2d = np.linspace(0.16, 0.84, 100, dtype=np.float32).reshape(10, 10)
    fp_2d = np.ones((10, 10), dtype=bool)
    post = compute_unmapped_fault_posterior(prob_2d, prop_2d, fp_2d, lambda_e=0.65)
    assert np.all(np.isfinite(post))
    assert float(post[0, 0]) > float(post[-1, -1]) + 0.08
    assert float(post.min()) >= 0.0 and float(post.max()) <= 1.0


def test_fold_area_quotas_and_quota_emission_invariants() -> None:
    h, w = 80, 80
    fp = _synthetic_footprint(h, w)
    folds = [
        {"region": (np.arange(h)[:, None] < 45) & (np.arange(w)[None, :] < 50) & fp},
        {"region": (np.arange(h)[:, None] < 45) & (np.arange(w)[None, :] >= 50) & fp},
        {"region": (np.arange(h)[:, None] >= 45) & (np.arange(w)[None, :] < 50) & fp},
        {"region": (np.arange(h)[:, None] >= 45) & (np.arange(w)[None, :] >= 50) & fp},
    ]
    quotas = compute_fold_area_quotas(folds, fp, total_budget=240)
    assert sum(quotas) == 240
    assert quotas[0] > quotas[3]

    rng = np.random.default_rng(7)
    prob = rng.uniform(0.05, 0.95, size=(h, w)).astype(np.float32)
    vis_cat = np.zeros((h, w), dtype=bool)
    vis_cat[20, 20:35] = True

    emitted = emit_fold_quota_dots_submodular(
        prob_2d=prob,
        footprint=fp,
        visible_catalogue=vis_cat,
        fold_region=folds[0]["region"],
        quota_dots=quotas[0],
        collar_px=3.05,
        min_spacing_px=3.05,
    )
    assert emitted.dtype == np.float32
    assert set(np.unique(emitted)).issubset({0.0, 1.0})
    assert np.all(emitted[~folds[0]["region"]] == 0.0)
    assert np.all(emitted[vis_cat] == 0.0)


def test_athy_strip_and_tri_pool_bounds() -> None:
    rng = np.random.default_rng(123)
    h, w = 64, 64
    fp = _synthetic_footprint(h, w)
    b15 = rng.uniform(0.0, 1800.0, size=(h, w)).astype(np.float32)
    b13 = (-14.0 * (1.0 - np.exp(-b15 / 600.0)) + rng.normal(0.0, 0.4, size=(h, w))).astype(np.float32)
    stripped, silic = athy_strip_gravity(b13, b15, fp)
    assert np.all(np.isfinite(stripped)) and np.all(np.isfinite(silic))
    assert float(silic.min()) >= 0.0 and float(silic.max()) <= 1.0

    p1 = rng.uniform(0.01, 0.90, size=(h, w)).astype(np.float32)
    p2 = rng.uniform(0.01, 0.90, size=(h, w)).astype(np.float32)
    p3 = rng.uniform(0.01, 0.90, size=(h, w)).astype(np.float32)
    p4 = rng.uniform(0.01, 0.90, size=(h, w)).astype(np.float32)
    pooled = pool_tri_specialists_logit(p1, p2, p3, p4, fp)
    assert pooled.dtype == np.float32
    assert np.all(pooled[~fp] == 0.0)
    assert float(pooled.min()) >= 0.0 and float(pooled.max()) <= 1.0


def test_fit_predict_specialist_cwgr_weighted_and_topology_modes() -> None:
    rng = np.random.default_rng(2026)
    h, w = 60, 60
    fp = _synthetic_footprint(h, w)
    n_fp = int(fp.sum())
    X = rng.normal(0.0, 1.0, size=(n_fp, 8)).astype(np.float32)

    vis = np.zeros((h, w), dtype=bool)
    vis[15:45, 30] = True
    # Inject synthetic signal on visible fault pixels
    vis_fp = vis[fp]
    X[vis_fp, 0] += 2.2
    X[vis_fp, 1] += 1.5

    train_dom = fp.copy()
    train_dom[42:, :] = False
    pred_mask = fp & (~train_dom)

    pos_w = rng.uniform(0.8, 2.0, size=n_fp).astype(np.float32)
    pos_w /= float(pos_w[vis_fp].mean())

    s_unw, m_unw = fit_predict_specialist_cwgr(
        blocks=[(X, list(range(8)))],
        hard_neg_cols_in_stack=[0, 1],
        visible_faults=vis,
        train_domain=train_dom,
        footprint=fp,
        seed=11,
        predict_mask=pred_mask,
    )
    s_sar, m_sar = fit_predict_specialist_cwgr(
        blocks=[(X, list(range(8)))],
        hard_neg_cols_in_stack=[0, 1],
        visible_faults=vis,
        train_domain=train_dom,
        footprint=fp,
        seed=11,
        pos_weights_fp=pos_w,
        topology_mode=True,
        predict_mask=pred_mask,
    )
    assert np.all(np.isfinite(s_unw)) and np.all(np.isfinite(s_sar))
    assert np.all(s_unw[~pred_mask] == 0.0) and np.all(s_sar[~pred_mask] == 0.0)
    assert m_unw["weighted"] is False and m_sar["weighted"] is True
    assert m_sar["topology_mode"] is True
    # Held-out fault line (x=30, rows 42..44) should score above held-out background
    assert float(s_sar[42:45, 30].mean()) > float(s_sar[42:45, 15].mean())


def test_emit_cwgr_submodular_skeleton_centers_on_oblique_n18e_fault() -> None:
    from scipy.ndimage import distance_transform_edt
    from scipy.spatial import cKDTree

    h, w = 96, 96
    fp = _synthetic_footprint(h, w)
    yy, xx = np.meshgrid(np.arange(h, dtype=np.float32), np.arange(w, dtype=np.float32), indexing="ij")

    # Oblique N18E fault trace: x = 48 - 0.325 * (y - 48)
    dist_fault = np.abs(xx - (48.0 - 0.325 * (yy - 48.0))) / np.hypot(1.0, 0.325)
    surf = (0.75 * np.exp(-0.5 * (dist_fault / 1.4) ** 2)).astype(np.float32)
    surf[~fp] = 0.0
    vis = np.zeros((h, w), dtype=bool)
    vis[10:22, 58:62] = True

    dots = emit_cwgr_submodular_skeleton(
        surf, vis, fp, budget=18, collar_px=3.05, min_spacing_px=3.05
    )
    pts = np.argwhere(dots > 0)
    assert len(pts) == 18
    min_sp = float(cKDTree(pts).query(pts, k=2)[0][:, 1].min())
    min_cat = float(distance_transform_edt(~vis)[dots > 0].min())
    assert min_sp > 3.0
    assert min_cat > 3.0
    assert float(dist_fault[dots > 0].mean()) < 0.75


def test_rank_logit_standardization_constant_and_empty_quadrant_edge_cases() -> None:
    h, w = 32, 32
    fp = _synthetic_footprint(h, w)
    empty_q = np.zeros((h, w), dtype=bool)
    const_q = fp.copy()
    folds = [{"region": empty_q}, {"region": const_q}]
    const_prob = np.full((h, w), 0.42, dtype=np.float32)
    const_prob[~fp] = 0.0

    std = rank_logit_standardize_per_quadrant(const_prob, folds, fp)
    assert std.dtype == np.float32
    assert np.all(np.isfinite(std))
    assert np.all(std[~fp] == 0.0)
    assert float(np.std(std[fp])) < 1e-6
    assert 0.05 < float(std[fp].mean()) < 0.15


def test_published_s18_cwgr_artifact_and_evidence_verify_without_data() -> None:
    import generate_submission as gs
    from scripts.verify_s18 import verify

    root = Path(__file__).resolve().parents[1]
    rep = verify(with_data=False)
    assert rep["status"] == "PASS"
    assert rep["ok_to_download"] is True
    assert rep["ok_to_submit"] is False
    assert rep["geological_experiments_rerun"] == 0

    cli_rep = gs.verify_s18_cwgr(root, with_data=False)
    assert cli_rep["format_ok"] is True
    assert cli_rep["OK_TO_DOWNLOAD"] == "YES"
    assert cli_rep["OK_TO_SUBMIT"] == "NO"
    assert cli_rep["ok_to_submit"] is False
    assert 0 < len(cli_rep["submission_note"]) <= 140
    assert 0 < len(cli_rep["submission_name"]) <= 140


def test_s18_cwgr_quota_diagnostic_proves_local_sar_ipw_gain_and_prevalence_erasure() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    holdout = json.loads((root / "docs/s18/holdout.json").read_text())
    q_scores = holdout["quota_diagnostic_summary_ir91_s18_02"]["scores"]
    g_scores = holdout["summary_all_arms"]["scores"]

    # IR-91-S18-02 Discovery 1: Under fixed area quotas, SAR IPW (E2) beats unweighted SCAR (E1)
    assert q_scores["cwgr_e2_quota37654"]["dti"] > q_scores["cwgr_e1_quota37654"]["dti"]
    wins = sum(
        f["quota_diagnostic_arms"]["cwgr_e2_quota37654"]["dti"]
        > f["quota_diagnostic_arms"]["cwgr_e1_quota37654"]["dti"]
        for f in holdout["folds"]
    )
    assert wins >= 3

    # IR-91-S18-02 Discovery 2: Marginal rank standardization starved dense NE Fold 1 under global pooling
    ne_fold = holdout["folds"][1]
    assert (
        ne_fold["quota_diagnostic_arms"]["cwgr_e1_quota37654"]["dti"]
        > ne_fold["arms"]["cwgr_e1"]["dti"] + 0.015
    )
    assert g_scores["cpad_e1"]["dti"] > g_scores["cwgr_e1"]["dti"]


def test_s18_cwgr_milestone_novelty_passes_all_46_non_calib_external_fleet_submissions() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    card = json.loads((root / "docs/run-card-S18-CWGR.json").read_text())
    novelty = json.loads((root / "docs/s18/milestone-novelty.json").read_text())

    ext = novelty["category_summary"]["preceding_fleet_submission"]
    assert ext["non_calib_count"] == 46
    assert ext["non_calib_pass_le_70pct"] == 46
    assert ext["non_calib_max_overlap_within_3px"] <= 0.70
    assert card["registry_comparison"]["gemsdoe32_r0_3px_overlap"] <= 0.70
    assert card["registry_comparison"]["e3_orthogonality_diagnostic"]["cwgr_e3_vs_gemsdoe32_r0_3px_overlap"] < 0.40
    assert card["registry_comparison"]["preplacement"]["checked"] == 108
    assert card["registry_comparison"]["final"]["status"] == "DUPLICATE"
    assert card["ok_to_submit"] is False and card["submission_ready"] is False and card["slots_used"] == 0


def test_s18_cwgr_portal_pages_expose_fail_closed_verdict_and_verified_downloads() -> None:
    import json

    root = Path(__file__).resolve().parents[1]
    card = json.loads((root / "docs/run-card-S18-CWGR.json").read_text())
    tif_rel = card["artifact"]["file"]
    zip_rel = card["artifact"]["zip"]

    for page_name in (
        "docs/index.html",
        "docs/executive-summary.html",
        "docs/s18-cwgr.html",
        "docs/s18-cwgr-executive-summary.html",
    ):
        html = (root / page_name).read_text(encoding="utf-8")
        assert "OK TO DOWNLOAD: YES" in html
        assert "OK TO SUBMIT: NO" in html
        assert "NOT OK TO SUBMIT" in html
        assert "OK TO SUBMIT: YES" not in html
        assert 'data-submission-ready="false"' in html
        assert 'data-submission-ready="true"' not in html
        assert tif_rel in html
        assert zip_rel in html
        assert card["raster_sha256"] in html



