"""S14-HVDC feature, evidence, artifact, portal and fail-closed policy tests."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import rasterio

from gems91 import hvdc as H
from gems91.readiness import gates, submission_ready

ROOT = Path(__file__).resolve().parents[1]


def test_gdr_enthalpy_builder_never_reads_banned_distance_column(tmp_path):
    csv_path = tmp_path / "gdr.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "row", "col", "thermalclass", "temp_c", "geothermquartz_c",
                "geothermchalc_c", "geothermcat_c", "dist_known_fault_px",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "row": 2, "col": 3, "thermalclass": "Hot", "temp_c": 80,
            "geothermquartz_c": 160, "geothermchalc_c": "", "geothermcat_c": "",
            # Deliberately invalid text: any accidental read/use must fail or alter output.
            "dist_known_fault_px": "FORBIDDEN-COLUMN-MUST-NOT-BE-READ",
        })
        writer.writerow({
            "row": 4, "col": 5, "thermalclass": "Cold", "temp_c": 20,
            "geothermquartz_c": 130, "geothermchalc_c": "", "geothermcat_c": "",
            "dist_known_fault_px": "FORBIDDEN-COLUMN-MUST-NOT-BE-READ",
        })
    fp = np.ones((8, 9), dtype=bool)
    enthalpy, blind = H.extract_gdr_enthalpy_rasters(csv_path, fp.shape, fp)
    assert enthalpy[2, 3] > 0 and enthalpy[4, 5] > 0
    assert blind[2, 3] == 0 and blind[4, 5] > 0
    assert np.isfinite(enthalpy).all() and np.isfinite(blind).all()


def test_relay_wash_context_is_finite_and_detects_two_sided_bridge():
    fp = np.ones((81, 81), dtype=bool)
    p = np.zeros(fp.shape, dtype=np.float32)
    # Two N-S segments separated by a central wash gap.
    p[8:34, 40] = 0.9
    p[47:73, 40] = 0.9
    ctx = H.compute_hvdc_relay_wash_context(p, fp)
    assert ctx.shape == (fp.size, len(H.STAGE2_CONTEXT_NAMES))
    assert np.isfinite(ctx).all()
    center = np.ravel_multi_index((40, 40), fp.shape)
    wash_short = H.STAGE2_CONTEXT_NAMES.index("ctx_wash_bridge_short")
    wash_long = H.STAGE2_CONTEXT_NAMES.index("ctx_wash_bridge_long")
    assert max(ctx[center, wash_short], ctx[center, wash_long]) > 0.05


def test_continuous_steger_mask_finds_sloping_ridge_without_filling_map():
    h, w = 101, 103
    yy, xx = np.indices((h, w))
    # A non-cardinal NNE ridge with smooth cross-strike Gaussian profile.
    distance = np.abs(xx - (0.37 * yy + 25.0)) / np.sqrt(1.0 + 0.37**2)
    q = np.exp(-0.5 * (distance / 1.4) ** 2).astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    crest = H._continuous_steger_crest_mask(q, fp)
    # Junction preservation intentionally admits low-coherence ridge neighborhoods;
    # require concentration without pretending the diagnostic mask is one-pixel thin.
    assert 50 < int(crest.sum()) < int(0.60 * fp.size)
    true_ridge = distance < 0.8
    assert float(crest[true_ridge].mean()) > 0.75
    assert float(q[crest].max()) == 1.0


def test_s14_run_card_and_published_artifact_are_byte_exact_and_fail_closed():
    card = json.loads((ROOT / "docs/run-card-S14-HVDC.json").read_text())
    tif = ROOT / card["artifact"]["primary_zeros_tif"]
    zipped = ROOT / card["artifact"]["zip_bundle"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zipped.read_bytes()).hexdigest() == card["artifact"]["zip_sha256"]
    with zipfile.ZipFile(zipped) as zf:
        assert zf.namelist() == [tif.name]
        assert zf.read(tif.name) == tif.read_bytes()
    with rasterio.open(tif) as src:
        arr = src.read(1)
        assert src.count == 1 and src.dtypes[0] == "float32"
        assert src.shape == (3730, 3292) and str(src.crs) == "EPSG:32611"
        assert src.nodata is None and np.isfinite(arr).all()
        assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == card["artifact"]["n_dots"] == 50_000
    assert card["holdout_dti"]["value"] == 0.262209
    assert card["holdout_dti"]["withheld_positives"] == 60_988
    assert card["holdout_dti"]["paired_best"]["ci95"][0] > 0
    assert card["blind_sgmc_offcatalogue_control"]["value"] == 0.110429
    assert card["canaries"]["n_features_checked"] == 101
    assert gates(card)["format"] and gates(card)["beats_comparable_best"]
    assert not submission_ready(card) and card["submission_ready"] is False
    assert card["verdict"] == "negative" and card["technical_candidate_verdict"] == "negative_duplicate_stop"
    assert card["slots_used"] == 0 and card["organizer_confirmed"] is None
    assert card["selector_approval"] is False


def test_s14_portal_makes_download_and_submit_status_unambiguous():
    for name in ("s14-hvdc.html", "s14-hvdc-executive-summary.html", "archive-results.html"):
        text = (ROOT / "docs" / name).read_text()
        assert "OK TO DOWNLOAD" in text
        assert "OK TO SUBMIT" in text
        assert "NO —" in text or "NOT OK TO SUBMIT" in text
        assert "gems91-s14-hvdc-e2-20261024T223000Z-0a0bb0cb-zeros.tif" in text
        assert "data-submission-ready=\"false\"" in text
