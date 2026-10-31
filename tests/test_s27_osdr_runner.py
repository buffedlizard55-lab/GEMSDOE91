"""Pass 2 & Pass 3 verification tests for S27-CVDC receipts, GeoTIFF delivery, and portal parity."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def test_s27_run_card_and_preregistration_integrity():
    card_a = json.loads((ROOT / "docs/s27-osdr/run-card.json").read_text(encoding="utf-8"))
    card_b = json.loads((ROOT / "docs/run-card-S27-OSDR.json").read_text(encoding="utf-8"))
    assert card_a == card_b

    prereg = ROOT / "docs/s27-osdr/preregistration.md"
    assert prereg.is_file()
    assert _sha256(prereg) == card_a["preregistration"]["sha256"]

    assert card_a["ok_to_download"] is True
    assert card_a["ok_to_submit"] is False
    assert card_a["verdict"] == "negative"
    assert card_a["assigned_lane"] is False
    assert card_a["experiments_run"] == 3
    assert card_a["weekly_submission_slots_used"] == 0
    assert card_a["organizer_confirmed"]["score"] is None
    assert 0 < len(card_a["submission_note"]) <= 140

    # Paired v3 holdout improvement over both S25-FABRIC E2 and control_oof_base
    h = card_a["holdout"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["split_version"] == "label-blind-quadrants-v3-feature-buffered"
    assert h["n_withheld_positives"] == 60_988
    assert h["dti"] > 0.155
    assert h["paired_vs_incumbent_s25_fabric_e2"]["ci95"][0] > 0.0
    assert h["paired_vs_control_oof_base"]["ci95"][0] > 0.0


def test_s27_canaries_and_uniqueness_gates():
    can = json.loads((ROOT / "docs/s27-osdr/canaries.json").read_text(encoding="utf-8"))
    assert can["all_pass"] is True
    assert can["max_symmetric_auc"] <= 0.90

    card = json.loads((ROOT / "docs/s27-osdr/run-card.json").read_text(encoding="utf-8"))
    u = card["uniqueness"]
    assert u["surface_pass"] is True
    assert u["surface_max_abs_rho_all_211"] <= 0.90
    assert u["dot_3px_pass_nine_focus_leaders"] is True
    assert u["dot_3px_max_nine_focus_leaders"] <= 0.70
    assert u["dot_3px_gemsdoe92_lbmc1"] <= 0.70
    assert u["dot_3px_pass_competitive_le_90000px"] is True
    assert u["dot_3px_max_competitive_le_90000px"] <= 0.70
    # Literal synthetic lattice failure must be honestly disclosed, never hidden
    assert u["dot_3px_pass_all_literal_no_exemption"] is False
    assert u["dot_3px_max_frozen_64_all"] > 0.8234


def test_s27_geotiff_and_zip_format_and_policy_registration():
    card = json.loads((ROOT / "docs/s27-osdr/run-card.json").read_text(encoding="utf-8"))
    tif_path = ROOT / card["raster_file"]
    zip_path = ROOT / card["zip_file"]
    assert tif_path.is_file() and zip_path.is_file()
    assert _sha256(tif_path) == card["raster_sha256"]
    assert _sha256(zip_path) == card["zip_sha256"]

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_path.read_bytes()

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert (ds.height, ds.width) == (3730, 3292)
        assert str(ds.crs) == "EPSG:32611"
        assert ds.dtypes[0] == "float32"
        assert ds.nodata is None
        arr = ds.read(1)

    assert np.isfinite(arr).all()
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    assert int((arr > 0).sum()) == 37_654
    assert set(np.unique(arr).tolist()).issubset({0.0, 1.0})

    pol = {r["path"]: r for r in json.loads((ROOT / "registry/artifact_policy.json").read_text())["files"]}
    assert pol[card["raster_file"]]["status"] == "current_research_only"
    assert pol[card["zip_file"]]["status"] == "current_research_only"

    dl_audit = {r["path"]: r for r in json.loads((ROOT / "docs/download-audit.json").read_text())["files"]}
    assert dl_audit[card["raster_file"]]["status"] == "PASS"
    assert dl_audit[card["zip_file"]]["status"] == "PASS"


def test_s27_pages_and_front_door_verdict_parity():
    card = json.loads((ROOT / "docs/s27-osdr/run-card.json").read_text(encoding="utf-8"))
    dti_str = f"{card['holdout']['dti']:.6f}"
    sha_prefix = card["raster_sha256"][:16]

    exec_s27 = (ROOT / "docs/s27-osdr/executive-summary.html").read_text(encoding="utf-8")
    assert 'data-submission-ready="false"' in exec_s27
    assert "OK TO DOWNLOAD: YES" in exec_s27
    assert "OK TO SUBMIT: NO" in exec_s27
    assert dti_str in exec_s27
    assert sha_prefix in exec_s27
    for site in ("GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36", "GEMSDOE92"):
        assert site in exec_s27

    for rel in (
        "docs/s27-osdr/executive-summary.html",
        "docs/s27-osdr/REVIEW.md",
    ):
        txt = (ROOT / rel).read_text(encoding="utf-8")
        assert "OK TO SUBMIT: YES" not in txt, rel
        assert "CLEARED TO SUBMIT" not in txt or "NO FILE CLEARED TO SUBMIT" in txt, rel

    # Front door now carries the S28-PUCC verdict (2026-10-31) and must stay in
    # parity with the active run card instead of denying that a candidate exists.
    for rel in (
        "docs/index.html",
        "docs/executive-summary.html",
        "index.html",
        "README.md",
    ):
        txt = (ROOT / rel).read_text(encoding="utf-8")
        assert "OK TO SUBMIT: YES" in txt, rel
        assert "gems91-s28-pucc-ee2-37654dots-20261031T013552Z-cb42d2ce-zeros" in txt or rel == "index.html", rel

    front = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert "s27-osdr/executive-summary.html" in front
    assert dti_str in front
