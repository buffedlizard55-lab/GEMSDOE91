"""Unit & integration tests for S17-CGRD (Cooper-Cowan Theta/HTD, Geothermometer
Disequilibrium Plumes, B12/B19 Bitwise Invariance, Prior-Shift-Calibrated
Auto-Context & Run Card / Artifact Integrity).
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems91 import cgrd17 as CGRD
from gems91 import readiness as RD

ROOT = Path(__file__).resolve().parents[1]


def test_cooper_cowan_theta_peaks_on_step_and_is_amplitude_invariant() -> None:
    h, w = 96, 96
    fp = np.ones((h, w), dtype=bool)
    yy, xx = np.mgrid[0:h, 0:w]
    step = np.tanh((xx - 48.0) / 2.0).astype(np.float32)

    cc_1 = CGRD.cooper_cowan_theta_and_htd(step, fp, pad=16)
    cc_10 = CGRD.cooper_cowan_theta_and_htd(step * 10.0, fp, pad=16)

    assert float(cc_1["raw_theta_600m"][:, 47:50].mean()) > float(
        cc_1["raw_theta_600m"][:, 12:20].mean()
    )
    np.testing.assert_allclose(
        cc_1["raw_theta_600m"], cc_10["raw_theta_600m"], rtol=1e-4, atol=1e-4
    )
    for k, arr in cc_1.items():
        assert np.isfinite(arr).all(), f"Non-finite in {k}"


def test_geothermometer_disequilibrium_ignores_forbidden_dist_column(tmp_path: Path) -> None:
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    cos2 = np.ones((h, w), dtype=np.float32)
    sin2 = np.zeros((h, w), dtype=np.float32)

    csv_a = tmp_path / "gdr_a.csv"
    csv_b = tmp_path / "gdr_b.csv"
    header = "layer,name,thermalclass,row,col,utm_x,utm_y,dist_known_fault_px,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c\n"
    row_a = "spring,TestSpring,Warm,32,32,300000,4400000,0.0,35.0,185.0,160.0,195.0\n"
    row_b = "spring,TestSpring,Warm,32,32,300000,4400000,9999999.0,35.0,185.0,160.0,195.0\n"
    csv_a.write_text(header + row_a, encoding="utf-8")
    csv_b.write_text(header + row_b, encoding="utf-8")

    d400_a, d1200_a, r800_a, rec_a = CGRD.geothermometer_disequilibrium_plumes(
        csv_a, cos2, sin2, fp
    )
    d400_b, d1200_b, r800_b, rec_b = CGRD.geothermometer_disequilibrium_plumes(
        csv_b, cos2, sin2, fp
    )

    assert rec_a["n_disequilibrium_sites"] == 1
    assert rec_a["forbidden_columns_accessed"] == []
    np.testing.assert_array_equal(d400_a, d400_b)
    np.testing.assert_array_equal(d1200_a, d1200_b)
    np.testing.assert_array_equal(r800_a, r800_b)
    assert float(d400_a[32, 32]) > float(d400_a[5, 5])


def test_cgrd_subsurface_features_bitwise_invariant_to_b12_and_b19(tmp_path: Path) -> None:
    h, w = 48, 48
    fp = np.ones((h, w), dtype=bool)
    fp[:4, :] = False
    rng = np.random.default_rng(42)

    tif_path = tmp_path / "features.tif"
    transform = from_origin(243350.0, 4508550.0, 100.0, 100.0)
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=h,
        width=w,
        count=19,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
    ) as dst:
        for b in range(1, 20):
            dst.write(rng.standard_normal((h, w), dtype=np.float32), b)

    csv_path = tmp_path / "gdr.csv"
    csv_path.write_text(
        "layer,name,thermalclass,row,col,utm_x,utm_y,dist_known_fault_px,temp_c,geothermquartz_c,geothermchalc_c,geothermcat_c\n"
        "spring,S1,Hot,24,24,245750,4506150,50.0,65.0,190.0,170.0,205.0\n",
        encoding="utf-8",
    )

    X1, names1, aux1, rec1 = CGRD.build_cgrd17_subsurface_features(tif_path, csv_path, fp)

    with rasterio.open(tif_path, "r+") as dst:
        dst.write(rng.uniform(-1e5, 1e5, size=(h, w)).astype(np.float32), 12)
        dst.write(rng.uniform(-1e5, 1e5, size=(h, w)).astype(np.float32), 19)

    X2, names2, aux2, _ = CGRD.build_cgrd17_subsurface_features(tif_path, csv_path, fp)

    assert names1 == names2 == CGRD.CGRD_SUBSURFACE_FEATURE_NAMES
    assert X1.shape == (int(fp.sum()), 26)
    assert np.isfinite(X1).all()
    np.testing.assert_array_equal(X1, X2)
    np.testing.assert_array_equal(aux1["joint_theta_raw"], aux2["joint_theta_raw"])
    assert 12 not in rec1["bands_read"] and 19 not in rec1["bands_read"]


def test_calibrated_autocontext_and_fitter_finite_unit_range() -> None:
    h, w = 48, 48
    fp = np.ones((h, w), dtype=bool)
    rng = np.random.default_rng(7)
    n_fp = int(fp.sum())

    X_base = rng.standard_normal((n_fp, 10), dtype=np.float32)
    vis = np.zeros((h, w), dtype=bool)
    vis[16:32, 24] = True
    excl = np.zeros((h, w), dtype=bool)
    excl[:6, :] = True

    cal_2d, meta = CGRD.fit_predict_calibrated_cgrd(
        X_train_blocks=[X_base],
        X_infer_blocks=[X_base],
        visible_faults=vis,
        exclude_mask=excl,
        footprint=fp,
        seed=17,
    )
    assert cal_2d.shape == (h, w)
    assert np.isfinite(cal_2d).all()
    assert 0.0 <= float(cal_2d.min()) and float(cal_2d.max()) <= 1.0
    assert meta["mean_calibrated_prob"] < meta["mean_raw_prob"]

    ac = CGRD.extract_calibrated_subsurface_autocontext(
        cal_2d,
        np.full((h, w), 0.5, dtype=np.float32),
        np.full((h, w), 0.2, dtype=np.float32),
        fp,
    )
    assert ac.shape == (n_fp, len(CGRD.CGRD_AUTOCONTEXT_FEATURE_NAMES))
    assert np.isfinite(ac).all()


def test_s17_cgrd_run_card_artifact_and_portal_integrity() -> None:
    rc_path = ROOT / "docs" / "run-card-S17-CGRD.json"
    ev_path = ROOT / "evidence" / "s17_cgrd_20261025.json"
    assert rc_path.is_file() and ev_path.is_file()
    rc = json.loads(rc_path.read_text(encoding="utf-8"))
    ev = json.loads(ev_path.read_text(encoding="utf-8"))
    assert rc == ev

    # Fail-closed readiness and protocol contracts
    assert RD.submission_ready(rc) is False
    assert rc["automated_gates"]["format"] is True
    assert rc["automated_gates"]["canary"] is True
    assert rc["ok_to_download"] is True
    assert rc["ok_to_submit"] is False
    assert rc["submission_ready"] is False
    assert rc["verdict"] == "negative"
    assert rc["slots_used"] == 0
    assert rc["experiments_run"] == 3
    assert len(rc["note"]) <= 140

    # E2 improves strictly over E1 after prior-shift calibration (IR-91-S15-06 fix)
    e1 = rc["experiments"]["E1_cgrd_pure_subsurface_26col"]["v10"]["holdout_dti"]
    e2 = rc["experiments"]["E2_cgrd_calibrated_autocontext_34col"]["v10"]["holdout_dti"]
    assert e2 > e1 > 0.08

    # Real-registry uniqueness passes (<= 0.70 3-px overlap, <= 0.90 rank corr)
    assert rc["registry_comparison"]["max_measured_final_dot_overlap_within_3px"] <= 0.70
    assert rc["registry_comparison"]["max_measured_surface_rank_correlation"] <= 0.90
    assert rc["registry_comparison"]["max_measured_final_dot_rank_correlation"] <= 0.90

    # Verify GeoTIFF and ZIP bytes on disk
    tif_path = ROOT / rc["artifact"]["primary_zeros_tif"]
    zip_path = ROOT / rc["artifact"]["zip_bundle"]
    assert tif_path.is_file() and zip_path.is_file()
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == rc["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == rc["artifact"]["zip_sha256"]

    with rasterio.open(tif_path) as src:
        arr = src.read(1)
        assert src.count == 1
        assert (src.height, src.width) == (3730, 3292)
        assert str(src.crs) == "EPSG:32611"
        assert src.nodata is None
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == 37654

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert zf.read(names[0]) == tif_path.read_bytes()

    # Portal pages expose S17-CGRD E2 and fail-closed status
    for page_name in (
        "s17-cgrd.html",
        "s17-cgrd-executive-summary.html",
    ):
        html = (ROOT / "docs" / page_name).read_text(encoding="utf-8")
        assert tif_path.name in html
        assert "NOT OK TO SUBMIT" in html
        assert html.count('data-submission-ready="false"') == 1
