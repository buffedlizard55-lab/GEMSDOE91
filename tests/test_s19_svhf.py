from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gems91 import readiness, svhf19  # noqa: E402


def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_svhf19_feature_counts_and_banned_columns():
    assert len(svhf19.SVHF19_FEATURE_NAMES) == 58
    assert len(svhf19.SVHF19_SUBSURFACE_NAMES) == 42
    assert len(svhf19.SVHF19_TOPO_NAMES) == 16
    assert len(svhf19.QDAC_FEATURE_NAMES) == 14
    assert "dist_known_fault_px" in svhf19.BANNED_GDR_COLUMNS
    for name in svhf19.SVHF19_FEATURE_NAMES + svhf19.QDAC_FEATURE_NAMES:
        assert "dist_known_fault" not in name
        assert "cat_dist" not in name


def test_sanitize_and_destripe_remove_sentinels_and_flightline_stripes():
    fp = np.ones((64, 64), dtype=bool)
    fp[:4, :] = False
    raw = np.zeros((64, 64), dtype=np.float32)
    raw[10, 10] = np.nan
    raw[12, 12] = -3.4e38
    raw[20:40, 20:40] = 5.0
    clean, n_bad = svhf19.sanitize_band(raw, fp)
    assert n_bad == 2
    assert np.isfinite(clean).all()

    yy, xx = np.mgrid[:64, :64].astype(np.float32)
    smooth = 0.05 * yy + 0.03 * xx
    # Cardinal E-W survey leveling stripe with period 10 px (kx = 0.10 > 0.030, ky = 0)
    striped = smooth + 3.0 * np.cos(2.0 * np.pi * xx / 10.0).astype(np.float32)
    destriped, stripe_resid = svhf19.destripe_cardinal_fft(striped)
    err_before = float(np.std((striped - smooth)[12:52, 12:52]))
    err_after = float(np.std((destriped - smooth)[12:52, 12:52]))
    assert err_after < 0.35 * err_before
    assert np.allclose(destriped + stripe_resid, striped, atol=1e-4)


def test_cross_strike_semivariogram_and_laplace_tensor_detect_step_and_roughness_breaks():
    rng = np.random.default_rng(19)
    fp = np.ones((96, 96), dtype=bool)
    rough_right = np.zeros((96, 96), dtype=np.float32)
    rough_right[:, :48] = 0.08 * rng.normal(size=(96, 48)).astype(np.float32)
    rough_right[:, 48:] = 3.50 * rng.normal(size=(96, 48)).astype(np.float32)
    aniso, hurst, sill_jump, hurst_step = svhf19.compute_directional_semivariogram_features(rough_right, fp)
    for arr in (aniso, hurst, sill_jump, hurst_step):
        assert np.isfinite(arr).all()
    # Half-plane sill jump must peak along the col=48 juxtaposition relative to uniform interiors
    boundary_jump = float(np.mean(sill_jump[20:76, 46:50]))
    interior_jump = float(np.mean(sill_jump[20:76, 16:28]))
    assert boundary_jump > interior_jump + 0.75

    step = np.zeros((96, 96), dtype=np.float32)
    step[:, 48:] = 10.0
    tens = svhf19.compute_laplace_tensor_features(step, step, fp, pad=16)
    assert len(tens) == 10
    assert all(np.isfinite(t).all() for t in tens)


def test_clean_celf_submodular_dots_enforces_spacing_and_catalogue_collar():
    fp = np.ones((48, 48), dtype=bool)
    cat = np.zeros((48, 48), dtype=bool)
    cat[24, 12:36] = True
    yy, xx = np.mgrid[:48, :48].astype(np.float32)
    surf = np.exp(-((yy - 12.0) ** 2 + (xx - 24.0) ** 2) / 90.0).astype(np.float32)
    out = svhf19.emit_clean_celf_submodular_dots(
        surf, cat, fp, budget=10, collar_px=3.05, min_spacing_px=3.10
    )
    assert out.dtype == np.float32
    assert set(np.unique(out)).issubset({0.0, 1.0})
    pts = np.argwhere(out > 0)
    assert len(pts) == 10
    dists = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(axis=-1))
    np.fill_diagonal(dists, 999.0)
    assert float(dists.min()) > 3.0
    cat_pts = np.argwhere(cat)
    cat_dists = np.sqrt(((pts[:, None, :] - cat_pts[None, :, :]) ** 2).sum(axis=-1))
    assert float(cat_dists.min()) > 3.0


def test_verify_s19_passes_and_enforces_fail_closed_governance():
    verify_mod = _load_module("verify_s19", "scripts/verify_s19.py")
    res_no_data = verify_mod.verify(with_data=False)
    assert res_no_data["status"] == "PASS"
    assert res_no_data["ok_to_download"] is True
    assert res_no_data["ok_to_submit"] is False
    assert res_no_data["competitive_le_80k_pass"] == "90/90"
    assert res_no_data["max_competitive_3px_overlap"] <= 0.70

    sample_tif = ROOT / "data/official/sample_submission.tif"
    faults_tif = ROOT / "data/official/existing_faults.tif"
    if sample_tif.is_file() and faults_tif.is_file():
        res_data = verify_mod.verify(with_data=True)
        assert res_data["status"] == "PASS"
        assert res_data["with_data"] is True


def test_s19_run_card_cannot_flip_ready_unless_every_gate_passes():
    card = json.loads((ROOT / "docs/run-card-S19-SVHF.json").read_text())
    assert readiness.submission_ready(card) is False
    assert card["ok_to_download"] is True
    assert card["ok_to_submit"] is False
    assert card["verdict"] == "negative"
    assert len(card["note"]) <= 140

    # Construct synthetic fully-approved clone and verify each single-gate failure blocks promotion
    promoted = copy.deepcopy(card)
    promoted["registry_comparison"]["complete_universal_registry"] = True
    promoted["registry_comparison"]["preplacement"] = {
        "status": "PASS_WITHIN_INDEXED_SCOPE",
        "checked": 100,
        "not_checked_after_stop": 0,
    }
    promoted["registry_comparison"]["final"] = {
        "status": "PASS_WITHIN_INDEXED_SCOPE",
        "checked": 100,
        "not_checked_after_stop": 0,
    }
    promoted["registry_comparison"]["max_measured_final_dot_overlap_within_3px"] = 0.5320
    promoted["lane"]["assigned"] = True
    best_val = promoted["comparable_prior_holdout_best"]["value"]
    promoted["holdout_dti"]["value"] = best_val + 0.025
    promoted["holdout_dti"]["ci95"] = [best_val + 0.010, best_val + 0.040]
    promoted["holdout_dti"]["paired_best"]["delta"] = 0.025
    promoted["holdout_dti"]["paired_best"]["ci95"] = [0.010, 0.040]
    n = promoted["holdout_dti"]["withheld_positives"]
    promoted["holdout_dti"]["fold_receipts"] = [dict(
        fold=i, split_version="label-blind-quadrants-v3-feature-buffered",
        evaluation_region_label_blind=True, known_scoring_mask_pixel_exact=True,
        truth_px=n//4 if i < 3 else n-3*(n//4), held_components=1,
        shared_train_truth_components=0, feature_context_buffer_px=80,
        nearest_visible_to_held_px=80.1) for i in range(4)]
    promoted["selector_approval"] = True
    promoted["selector_receipt"] = {"weekly_cap_verified": True, "slot_available": True}
    assert readiness.submission_ready(promoted) is True

    for mutator in (
        lambda c: c["validator_output"].update(values_in_0_1=False),
        lambda c: c["validator_output"].update(no_nan_inside_footprint=False),
        lambda c: c["canaries"].update(status="FAIL"),
        lambda c: c["registry_comparison"]["preplacement"].update(status="DUPLICATE"),
        lambda c: c["registry_comparison"]["final"].update(status="DUPLICATE"),
        lambda c: c["registry_comparison"].update(max_measured_final_dot_overlap_within_3px=0.71),
        lambda c: c["lane"].update(assigned=False),
        lambda c: c["holdout_dti"]["paired_best"].update(ci95=[-0.005, 0.040]),
        lambda c: c.update(selector_approval=False),
    ):
        broken = copy.deepcopy(promoted)
        mutator(broken)
        assert readiness.submission_ready(broken) is False


def test_s19_portal_pages_have_single_fail_closed_marker_and_verified_hashes():
    card = json.loads((ROOT / "docs/run-card-S19-SVHF.json").read_text())
    for rel in ("docs/s19-svhf.html", "docs/s19-svhf-executive-summary.html"):
        html = (ROOT / rel).read_text(encoding="utf-8")
        assert html.count('data-submission-ready="false"') == 1
        assert 'data-submission-ready="true"' not in html
        assert "OK TO DOWNLOAD: YES" in html
        assert "OK TO SUBMIT: NO" in html
        assert "NOT OK TO SUBMIT" in html
        assert card["raster_sha256"] in html
        assert card["artifact"]["zip_sha256"] in html
        assert card["submission_name"] in html
        assert card["note"] in html

    for main_rel in ("docs/index.html", "docs/executive-summary.html"):
        html = (ROOT / main_rel).read_text(encoding="utf-8")
        assert html.count('data-submission-ready="false"') == 1
        current = json.loads((ROOT / "docs/current-run.json").read_text())
        assert current["raster_sha256"] in html


def test_restore_registry_available_only_skips_missing_non_blob_while_strict_raises(tmp_path, monkeypatch):
    rr = _load_module("restore_registry", "scripts/restore_registry.py")
    monkeypatch.setattr(rr, "ROOT", tmp_path)
    present_rel = "data/fleet_registry/present.tif"
    present_path = tmp_path / present_rel
    present_path.parent.mkdir(parents=True, exist_ok=True)
    raw = b"synthetic-geotiff-bytes"
    present_path.write_bytes(raw)
    row_present = {"path": present_rel, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    row_missing_local = {"path": "docs/downloads/retracted.tif", "sha256": "0" * 64, "bytes": 12}

    assert rr.restore(row_present, check=True, available_only=True) == present_rel
    assert rr.restore(row_missing_local, check=True, available_only=True) is None
    with pytest.raises(ValueError, match="Missing pinned reference"):
        rr.restore(row_missing_local, check=True, available_only=False)
