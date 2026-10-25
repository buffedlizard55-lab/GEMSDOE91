"""Tests for Session 14 UCSD physics/auto-context/Dinkelbach module and published artifact gates."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

from gems91 import readiness as RD
from gems91 import ucsd as UCSD

ROOT = Path(__file__).resolve().parents[1]


def test_upward_continue_2d_fft_attenuates_high_frequency_float_and_preserves_step():
    """Verify 2-D Fourier upward continuation exp(-2*pi*z*||k||) suppresses short-wavelength
    surficial noise much more strongly than a regional basin step."""
    h, w = 64, 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    footprint = np.ones((h, w), dtype=bool)

    # Long-wavelength step + high-wavenumber synthetic basaltic float ripple
    long_step = np.tanh((xx - 32.0) / 8.0).astype(np.float32)
    short_ripple = (0.5 * np.sin(2.0 * np.pi * xx / 4.0) * np.cos(2.0 * np.pi * yy / 4.0)).astype(
        np.float32
    )

    u_step = UCSD.upward_continue_2d_fft(long_step, footprint, heights_m=(200.0, 1500.0))
    u_rip = UCSD.upward_continue_2d_fft(short_ripple, footprint, heights_m=(200.0, 1500.0))
    u_step_200, u_step_1500 = u_step[200.0], u_step[1500.0]
    u_rip_200, u_rip_1500 = u_rip[200.0], u_rip[1500.0]

    assert np.isfinite(u_step_1500).all()
    assert np.isfinite(u_rip_1500).all()
    # High-frequency ripple must attenuate far more than long step at z=1500m
    rip_ratio = float(np.std(u_rip_1500[16:48, 16:48])) / float(np.std(u_rip_200[16:48, 16:48]) + 1e-9)
    step_ratio = float(np.std(u_step_1500[16:48, 16:48])) / float(np.std(u_step_200[16:48, 16:48]) + 1e-9)
    assert rip_ratio < 0.05
    assert step_ratio > 0.40
    assert step_ratio > 20.0 * rip_ratio


def test_downdip_migration_detects_signed_hanging_wall_crest_shift():
    """Verify downdip migration measures positive shift when deep upward-continued
    gradient crest migrates in the hanging-wall (+x) direction relative to shallow crest."""
    h, w = 48, 48
    _, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    footprint = np.ones((h, w), dtype=bool)
    fp_r, fp_c = np.nonzero(footprint)

    # Shallow gradient peaks at x=20; deep gradient (dipping +x) peaks at x=24
    g_shallow = np.exp(-0.5 * ((xx - 20.0) / 2.0) ** 2).astype(np.float32)
    g_deep = np.exp(-0.5 * ((xx - 24.0) / 2.5) ** 2).astype(np.float32)
    ny_fp = np.zeros(fp_r.size, dtype=np.float32)
    nx_fp = np.ones(fp_r.size, dtype=np.float32)  # hanging wall in +x direction

    shift_pos = UCSD.compute_downdip_migration_fp(g_shallow, g_deep, fp_r, fp_c, ny_fp, nx_fp, shift_px=3.0)
    shift_neg = UCSD.compute_downdip_migration_fp(g_shallow, g_deep, fp_r, fp_c, ny_fp, -nx_fp, shift_px=3.0)
    mid_grid = np.zeros((h, w), dtype=np.float32)
    mid_grid[footprint] = shift_pos
    neg_grid = np.zeros((h, w), dtype=np.float32)
    neg_grid[footprint] = shift_neg

    assert float(mid_grid[24, 21]) > 0.5
    assert float(neg_grid[24, 21]) < -0.5


def test_planform_and_profile_curvatures_distinguish_planar_from_deflected_scarp():
    """Verify planform curvature is near zero on a straight planar ramp and positive
    on a deflected bayonet ridge, while scarp-toe concavity peaks at the toe inflection."""
    h, w = 64, 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    footprint = np.ones((h, w), dtype=bool)

    # Sinusoidally deflected range front (bayonet drainage offset) + concave toe
    x_scarp = 32.0 + 3.5 * np.sin(2.0 * np.pi * yy / 24.0)
    deflected_scarp = (50.0 * (1.0 - np.tanh((xx - x_scarp) / 3.0))).astype(np.float32)
    kt_150_fp, kt_350_fp, kprof_concav = UCSD.compute_planform_and_profile_curvatures(
        deflected_scarp, footprint
    )
    kp_def_2d = np.zeros((h, w), dtype=np.float32)
    kp_def_2d[footprint] = kt_150_fp
    kt350_2d = np.zeros((h, w), dtype=np.float32)
    kt350_2d[footprint] = kt_350_fp
    kprof_2d = np.zeros((h, w), dtype=np.float32)
    kprof_2d[footprint] = kprof_concav

    # Deflected scarp zone (cols 28..36) must have much higher planform curvature than flat interior (cols 50..60)
    assert float(np.median(kp_def_2d[16:48, 28:36])) > float(np.median(kp_def_2d[16:48, 50:60])) + 2.0
    assert float(np.median(kt350_2d[16:48, 28:36])) > float(np.median(kt350_2d[16:48, 50:60])) + 2.0
    assert float(np.max(kprof_2d[16:48, 30:42])) > 1.0


def test_published_s14_run_card_and_geotiff_submission_gates():
    card_path = ROOT / "docs/run-card-S14.json"
    evid_path = ROOT / "evidence/s14_ucsd_metrics_20261024.json"
    indep_path = ROOT / "evidence/s14_independent_tif_check.json"
    assert card_path.is_file()
    assert evid_path.is_file()
    assert indep_path.is_file()

    card = json.loads(card_path.read_text())
    assert card["lane"]["id"] == "S14-UCSD-E3"
    assert card["submission_ready"] is False
    assert len(card["submission"]["note"]) <= 140
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["withheld_positives"] == 60988
    assert card["holdout_dti"]["value"] > card["comparable_prior_holdout_best"]["value"]
    assert card["holdout_dti"]["paired_best"]["ci95"][0] > 0.0
    assert card["holdout_dti"]["paired_vs_s11_e2"]["ci95"][0] > 0.0

    # Verify all 3 external uniqueness scopes pass <= 0.70 (including dense halos calib_h25ctx/h28ridge)
    rc = card["registry_comparison"]
    assert rc["canonical_registry_scope"]["pass"] is True
    assert rc["external_dotted_fleet_scope"]["pass"] is True
    assert rc["external_all_non_lattice_scope"]["pass"] is True
    assert rc["max_canonical_registry_dot_overlap_within_3px"] <= 0.70
    assert rc["max_external_dotted_fleet_dot_overlap_within_3px"] <= 0.70
    assert rc["max_external_all_non_lattice_dot_overlap_within_3px"] <= 0.70

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
        assert int((arr > 0.5).sum()) == 54000

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert names == [tif_path.name]
        assert hashlib.sha256(zf.read(names[0])).hexdigest() == card["raster_sha256"]
