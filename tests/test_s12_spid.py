"""Unit, mathematical, and protocol-certification tests for Session 12 (`S12-SPID`)."""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems91 import spid_dinkelbach as SD
from scripts import dti as D

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def test_dti_dinkelbach_coordinate_wise_convexity_binary_vertex():
    """Verify the Session 12 Theorem (`docs/HYPOTHESES_S12.md` §1.2): for any
    lambda in [0, 1] and any ground-truth fault mask G, the exact Dinkelbach
    DTI objective L_lambda(p) = T(p) - lambda * (0.2*(T(p) + S(p) - M(p)) + 0.8*|G|)
    is coordinate-wise convex along every pixel p_i in [0, 1], so the maximum
    over [0, 1] is attained at an extreme point p_i in {0, 1}.
    """
    rng = np.random.default_rng(9112)
    h, w = 16, 16
    fp = np.ones((h, w), dtype=bool)
    g = rng.random((h, w)) < 0.08
    g[8, 4:12] = True
    p_base = (rng.random((h, w)) * 0.4).astype(np.float32)
    lam = 0.25

    def _L_lam(p_arr: np.ndarray) -> float:
        res = D.components(p_arr, g)
        T, S, M, G_cnt = res.T, res.S, res.M, float(res.G)
        denom = D.ALPHA * T + D.ALPHA * (S - M) + D.BETA * G_cnt
        return float(T - lam * denom)

    for r, c in [(8, 7), (7, 7), (3, 3), (12, 10)]:
        vals = {}
        for v in (0.0, 0.25, 0.5, 0.75, 1.0):
            p_try = p_base.copy()
            p_try[r, c] = v
            vals[v] = _L_lam(p_try)
        # Midpoint convexity: L(0.5) <= 0.5 * (L(0) + L(1)) + 1e-9
        assert vals[0.5] <= 0.5 * (vals[0.0] + vals[1.0]) + 1e-8
        assert max(vals[0.0], vals[1.0]) >= max(vals[0.25], vals[0.5], vals[0.75]) - 1e-8


def test_hessian_strike_and_steerable_tangent_continuation():
    h, w = 81, 81
    yy, xx = (np.mgrid[0:h, 0:w] - 40).astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    for az in (0, 30, 60, 90, 120, 150):
        rad = math.radians(az)
        sy, sx = -math.cos(rad), math.sin(rad)
        ny, nx = sx, -sy
        n_c = yy * ny + xx * nx
        s_c = yy * sy + xx * sx
        ridge = np.exp(-0.5 * (n_c / 2.0) ** 2).astype(np.float32)
        _, _, est_rad = SD._hessian_ridge_and_tangent(ridge, sigma=1.5)
        est_deg = float(np.degrees(est_rad[40, 40]))
        diff = min(abs(est_deg - az), 180.0 - abs(est_deg - az))
        assert diff <= 2.0, f"expected {az}, got {est_deg}"

        gapped = (ridge * np.where(np.abs(s_c) < 2.0, 0.2, 1.0)).astype(np.float32)
        sbin = np.full((h, w), (az // 30) % 6, dtype=np.int8)
        steered = SD.steerable_tangent_continuation(gapped, sbin, fp, blend=0.5)
        assert steered.shape == (h, w)
        assert float(steered.min()) >= 0.0 and float(steered.max()) <= 1.0
        assert float(steered[40, 40]) > float(gapped[40, 40]) + 0.10


def test_fft_potential_operators_monotonic_upward_smoothing():
    h, w = 96, 96
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    fp[:5, :] = False
    rng = np.random.default_rng(42)
    grav = (np.tanh((xx - 48.0) / 2.5) + 0.25 * rng.standard_normal((h, w))).astype(np.float32)
    dz, ups = SD._fft_potential_operators(
        grav, fp, z_dz_m=150.0, upward_heights_m=(100.0, 400.0, 1200.0)
    )
    assert np.isfinite(dz).all()
    assert len(ups) == 3 and all(np.isfinite(u).all() for u in ups)
    v100 = float(np.var(np.gradient(ups[0])[1][20:76, 20:76]))
    v400 = float(np.var(np.gradient(ups[1])[1][20:76, 20:76]))
    v1200 = float(np.var(np.gradient(ups[2])[1][20:76, 20:76]))
    assert v1200 < v400 < v100


def test_noisy_or_self_credit_and_submodular_emitter_determinism():
    h, w = 80, 80
    _, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    surf = (0.75 * np.exp(-((xx - 20.0) ** 2) / 3.0) + 0.30 * np.exp(-((xx - 58.0) ** 2) / 3.5)).astype(np.float32)
    spid = (0.90 * np.exp(-((xx - 58.0) ** 2) / 2.5)).astype(np.float32)
    pied = xx >= 40
    m = SD.compute_noisy_or_self_credit(surf * 0.5, radius_px=3.0)
    assert m.shape == (h, w) and float(m.min()) >= 0.0 and float(m.max()) <= 1.0
    assert float(m[40, 20]) > float(m[40, 40])

    sbin = np.zeros((h, w), dtype=np.int8)
    d1 = SD.spid_dinkelbach_submodular_emit(
        surf, spid, pied, strike_bin_grid=sbin, eligible_mask=fp,
        max_dots=28, piedmont_quota_frac=0.45, tangent_steer_blend=0.25, min_spacing_px=2.6
    )
    d2 = SD.spid_dinkelbach_submodular_emit(
        surf, spid, pied, strike_bin_grid=sbin, eligible_mask=fp,
        max_dots=28, piedmont_quota_frac=0.45, tangent_steer_blend=0.25, min_spacing_px=2.6
    )
    assert np.array_equal(d1, d2)
    assert set(np.unique(d1)).issubset({0.0, 1.0})
    assert int((d1[:, :40] > 0).sum()) >= 10
    assert int((d1[:, 40:] > 0).sum()) >= 8


def test_s12_run_card_and_certified_artifacts():
    rc_path = ROOT / "docs" / "run-card-S12.json"
    ev_rc_path = ROOT / "evidence" / "s12_run_card.json"
    assert rc_path.is_file() and ev_rc_path.is_file()
    rc = json.loads(rc_path.read_text(encoding="utf-8"))
    assert rc == json.loads(ev_rc_path.read_text(encoding="utf-8"))

    # Rule 5 & Rule 6 checks
    assert rc["session"] == "S12-SPID"
    assert rc["verdict"] == "negative"
    assert rc["submission_ready_pending_selector"] is False
    assert rc["budget"]["experiments_run"] == 3
    assert rc["budget"]["max_experiments"] == 3
    assert rc["budget"]["wall_clock_seconds"] <= 7200
    assert len(rc["note"]) <= 140
    assert rc["leakage_canary"]["all_pass"] is True
    assert rc["leakage_canary"]["n_features_tested"] == 85
    assert rc["leakage_canary"]["worst_symmetric_auc"] <= 0.90

    # Rule 1 two-phase uniqueness across 67 real fault rasters
    ru = rc["registry_uniqueness"]
    assert ru["uniqueness_pass"] is True
    assert ru["rasters_checked"] >= 65
    assert ru["max_surface_abs_rank_corr"] <= 0.90
    assert ru["max_3px_dot_overlap"] <= 0.70

    # Certified GeoTIFF & single-TIFF ZIP checks (`[0, 1]` range guaranteed)
    sub = rc["submission"]
    tif_path = ROOT / "docs" / "downloads" / sub["recommended_upload_file"]
    zip_path = ROOT / "docs" / "downloads" / sub["recommended_zip_download"]
    audit_path = ROOT / "docs" / "downloads" / sub["audit_json"]
    assert tif_path.is_file() and zip_path.is_file() and audit_path.is_file()
    assert _sha256(tif_path) == rc["raster_sha256"] == sub["sha256_zeros_tif"]
    assert _sha256(zip_path) == sub["sha256_zeros_zip"]

    with rasterio.open(tif_path) as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert (src.height, src.width) == (3730, 3292)
        assert str(src.crs) == "EPSG:32611"
        assert src.nodata is None
        arr = src.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == sub["n_dots"] == 47200

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert names == [sub["recommended_upload_file"]]
        assert hashlib.sha256(zf.read(names[0])).hexdigest() == rc["raster_sha256"]

    # Portal HTML pages exist and expose unmistakable automated status
    for page_name in ("s12-spid.html", "s12-executive-summary.html"):
        html_txt = (ROOT / "docs" / page_name).read_text(encoding="utf-8")
        assert sub["recommended_upload_file"] in html_txt
        assert rc["raster_sha256"] in html_txt or page_name == "s12-executive-summary.html"
        assert 'data-submission-ready="false"' in html_txt
