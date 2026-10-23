"""Gate tests: a valid synthetic candidate passes, each broken one fails the right gate.

Synthetic fixture only (tools.make_fixture). No competition data.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from tools import make_fixture, raster_io
from tools.validate_submission import validate


@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    out = tmp_path_factory.mktemp("fixture")
    paths = make_fixture.make(out, seed=3, n_dots=600)
    return {k: Path(v) for k, v in paths.items()}


@pytest.fixture
def ledger(tmp_path):
    p = tmp_path / "submissions.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "sha256", "sha8", "status"])
        w.writeheader()
        w.writerow({"id": "old-repeat", "sha256": "deadbeef" * 8, "sha8": "deadbeef", "status": "SCORED"})
    return p


def _rep(fx, ledger, cand=None, parent=None, **kw):
    return validate(
        candidate=Path(cand or fx["parent_R0"]),
        sample=fx["sample_submission"],
        catalogue=fx["catalogue_mask"],
        ledger=ledger,
        parent=Path(parent) if parent else fx["parent_R0"],
        stacklevel_output=False,
        **kw,
    )


def test_valid_parent_passes_all_gates(fx, ledger):
    rep = _rep(fx, ledger)
    assert rep["pass"], rep["failed_gates"]
    assert rep["n_dots"] == 600
    assert rep["catalogue"]["min_dot_gap_px"] > 3.0
    assert rep["parent_diff"]["n_dots_added"] == 0


def test_bad_candidate_fails_domain_and_catalogue_gates(fx, ledger):
    rep = _rep(fx, ledger, cand=fx["bad_candidate"])
    assert not rep["pass"]
    failed = " ".join(rep["failed_gates"])
    assert "G5 outside is null" in failed or "G5 zero mass outside" in failed
    assert "G6 zero catalogue mass" in failed
    assert "G7" in failed  # the injected catalogue pixels also break the gap gate


def test_zeros_twin_is_a_distinct_file_that_also_passes(fx, ledger):
    rep = _rep(fx, ledger, cand=fx["parent_R0-zeros"])
    assert rep["pass"], rep["failed_gates"]
    a = raster_io.sha256_file(fx["parent_R0"])
    b = raster_io.sha256_file(fx["parent_R0-zeros"])
    assert a != b  # different bytes, same experiment


def test_wrong_crs_and_dtype_are_caught(fx, ledger, tmp_path):
    with rasterio.open(fx["sample_submission"]) as ds:
        prof = ds.profile.copy()
        band = ds.read(1)
    prof.update(crs="EPSG:4326", dtype="float64")
    p = tmp_path / "wrong_crs.tif"
    with rasterio.open(p, "w", **prof) as ds:
        ds.write(band.astype("float64"), 1)
    rep = _rep(fx, ledger, cand=p)
    assert "G1 CRS" in " ".join(rep["failed_gates"])
    assert "G3 dtype" in " ".join(rep["failed_gates"])


def test_wrong_transform_is_caught(fx, ledger, tmp_path):
    with rasterio.open(fx["sample_submission"]) as ds:
        prof = ds.profile.copy()
        band = ds.read(1)
    prof["transform"] = from_origin(500000.0 + 100.0, 4200000.0, 100.0, 100.0)
    p = tmp_path / "shifted.tif"
    with rasterio.open(p, "w", **prof) as ds:
        ds.write(band, 1)
    rep = _rep(fx, ledger, cand=p)
    assert "G2 transform" in " ".join(rep["failed_gates"])


def test_duplicate_hash_in_ledger_is_caught(fx, tmp_path):
    sha = raster_io.sha256_file(fx["parent_R0"])
    p = tmp_path / "subs.csv"
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "sha256", "sha8", "status"])
        w.writeheader()
        w.writerow({"id": "repeat", "sha256": sha, "sha8": sha[:8], "status": "SCORED"})
    rep = _rep(fx, p)
    assert "G8 sha256 not in ledger" in " ".join(rep["failed_gates"])


def test_gap_gate_catches_near_catalogue_dot(fx, ledger, tmp_path):
    band = raster_io.read_band(fx["parent_R0"])
    cat = raster_io.read_band(fx["catalogue_mask"]) > 0
    from scipy import ndimage

    dist = ndimage.distance_transform_edt(~cat)
    candidate_pix = np.argwhere((dist > 0.5) & (dist < 1.5))
    band[candidate_pix[0][0], candidate_pix[0][1]] = 1.0
    p = tmp_path / "near_catalogue.tif"
    with rasterio.open(fx["parent_R0"]) as ds:
        prof = ds.profile.copy()
    with rasterio.open(p, "w", **prof) as ds:
        ds.write(band.astype(np.float32), 1)
    rep = _rep(fx, ledger, cand=p)
    assert "G6 zero catalogue mass" not in " ".join(rep["failed_gates"])
    assert any(g.startswith("G7") for g in rep["failed_gates"])


def test_missing_catalogue_is_a_failure_not_a_pass(fx, ledger):
    rep = validate(candidate=fx["parent_R0"], sample=fx["sample_submission"],
                   ledger=ledger, stacklevel_output=False)
    assert not rep["pass"]
    assert any("catalogue" in g for g in rep["failed_gates"])


def test_proxy_and_canary_are_report_only(fx, ledger):
    rep = _rep(fx, ledger, proxy_truth=fx["truth_holdout"])
    ro = rep["report_only"]["hide_and_recover"]
    assert ro["label"] == "PROXY"
    assert 0.0 <= ro["hit_rate"] <= 1.0
    assert ro["ci95"][0] <= ro["hit_rate"] <= ro["ci95"][1]
    # report-only values never decide the gate result
    assert rep["pass"], rep["failed_gates"]


def test_canary_alarm_is_reported_not_enforced(fx, ledger):
    # a feature that is a copy of the truth mask trips the canary
    rep = _rep(fx, ledger, feature=fx["truth_holdout"])
    can = rep["report_only"]["leakage_canary"]
    assert can["label"] == "LEAKAGE-CANARY"
    assert can["auc"] > 0.90 and can["alarm"] is True
    assert rep["pass"], rep["failed_gates"]


def test_receipt_written_from_disk_hashes(fx, ledger, tmp_path):
    out = tmp_path / "receipt.json"
    rep = _rep(fx, ledger)
    out.write_text(json.dumps(rep, default=str))
    loaded = json.loads(out.read_text())
    assert loaded["sha256"] == raster_io.sha256_file(fx["parent_R0"])
    assert loaded["sha8"] == loaded["sha256"][:8]
