"""Tests for Session 13 PTHA physics/Dinkelbach module and published artifact gates."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems91 import ptha as PTHA
from gems91 import readiness as RD

ROOT = Path(__file__).resolve().parents[1]


def test_directional_1d_ridge_rejects_broad_uniform_slope_interior():
    """Verify IR-91-S13-02 fix: 1-D cross-strike crest detection rejects planar slopes
    while preserving genuine fault-like 1-D crests."""
    rows = np.arange(32, dtype=np.float32)[:, None]
    cols = np.arange(32, dtype=np.float32)[None, :]
    # Strict interior planar ramp has no 1-D cross-strike crest
    planar_ramp = 0.02 * rows + 0.013 * cols + 0.1
    crest_ramp = PTHA._detect_1d_directional_ridge(planar_ramp, span=2)
    assert int(crest_ramp[6:26, 6:26].sum()) == 0

    # Sharp N-S fault ridge at col=16 must be detected cleanly along its spine
    fault_ridge = np.exp(-0.5 * ((cols - 16.0) / 1.2) ** 2) * (1.0 + 0.005 * rows)
    crest_fault = PTHA._detect_1d_directional_ridge(fault_ridge, span=2)
    assert bool(crest_fault[16, 16])
    assert int(crest_fault[6:26, 16].sum()) == 20
    assert int(crest_fault[6:26, 10].sum()) == 0


def test_prior_shift_calibrate_surface_monotonic_and_bounded():
    prob_2d = np.array(
        [[0.0, 0.05, 0.20], [0.50, 0.85, 1.0]],
        dtype=np.float32,
    )
    fp = np.array([[False, True, True], [True, True, True]], dtype=bool)
    q = PTHA.prior_shift_calibrate_surface(
        prob_2d,
        fp,
        pi_true=0.012,
        pi_sample=0.25,
    )
    assert q.shape == prob_2d.shape
    assert float(q[0, 0]) == 0.0
    vals = q[fp]
    assert np.all(np.isfinite(vals))
    assert np.all((vals > 0.0) & (vals < 1.0))
    assert np.all(np.diff(vals) > 0.0)
    assert float(q[1, 0]) < float(prob_2d[1, 0])


def test_dinkelbach_full_map_emit_binary_spacing_and_collar():
    h, w = 64, 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    footprint = np.ones((h, w), dtype=bool)
    trace1 = 0.48 * np.exp(-0.5 * ((xx - 18.0) / 1.1) ** 2)
    trace2 = 0.42 * np.exp(-0.5 * ((yy - 44.0) / 1.1) ** 2)
    prob_2d = np.clip(0.01 + trace1 + trace2, 0.0, 0.99).astype(np.float32)
    crest_2d = np.clip(trace1 + trace2, 0.0, 1.0).astype(np.float32)
    piedmont = (yy > 30).astype(bool)

    # Known fault at (10, 18) -> 3.0 px collar forbids dots within <= 3.0 px
    dist_known = np.hypot(yy - 10.0, xx - 18.0).astype(np.float32)
    eligible = footprint & (dist_known > 3.0)

    out, last_gain = PTHA.dinkelbach_full_map_emit(
        prob_2d,
        crest_2d,
        piedmont,
        footprint=footprint,
        full_eligible_mask=eligible,
        pi_true=0.02,
        pi_sample=0.20,
        n_dots=25,
        min_spacing_px=2.8,
    )
    assert out.shape == (h, w)
    assert out.dtype == np.float32
    assert set(np.unique(out).tolist()).issubset({0.0, 1.0})
    assert last_gain > 0.0
    rs, cs = np.nonzero(out > 0.5)
    assert 5 <= rs.size <= 25
    assert np.all(dist_known[rs, cs] > 3.0)
    if rs.size >= 2:
        dr = rs[:, None].astype(np.float64) - rs[None, :].astype(np.float64)
        dc = cs[:, None].astype(np.float64) - cs[None, :].astype(np.float64)
        dmat = np.hypot(dr, dc) + np.eye(rs.size) * 999.0
        assert float(dmat.min()) >= 2.8 - 1e-5


def test_published_s13_run_card_and_geotiff_submission_gates():
    card_path = ROOT / "docs/run-card-S13.json"
    assert card_path.is_file()
    card = json.loads(card_path.read_text())

    assert card["lane"]["id"] == "S13-PTHA-E3"
    assert card["submission_ready"] is False
    assert len(card["submission"]["note"]) <= 140
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["withheld_positives"] == 60988
    assert card["holdout_dti"]["value"] > card["comparable_prior_holdout_best"]["value"]
    assert card["holdout_dti"]["paired_best"]["ci95"][0] > 0.0

    # Shared readiness gates: format/canary/beats_comparable_best pass, fail-closed submission_ready=False
    g = RD.gates(card)
    assert g["format"] is True
    assert g["canary"] is True
    assert g["beats_comparable_best"] is True
    assert RD.submission_ready(card) is False

    # Verify on-disk GeoTIFF & single-TIFF ZIP hashes and [0, 1] compliance
    tif_path = ROOT / card["artifact"]["primary_zeros_tif"]
    zip_path = ROOT / card["artifact"]["zip_bundle"]
    assert tif_path.is_file() and zip_path.is_file()
    assert hashlib.sha256(tif_path.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["artifact"]["zip_sha256"]

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.dtypes == ("float32",)
        assert ds.nodata is None
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) >= 0.0
        assert float(arr.max()) <= 1.0
        assert int((arr > 0.5).sum()) == 44000

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert hashlib.sha256(zf.read(names[0])).hexdigest() == card["raster_sha256"]
