"""Unit and end-to-end verification tests for Session 11 (`S11-MHTR`)."""

from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from gems91 import mhtr_coda as MC  # noqa: E402


def test_mhtr_corridor_submodular_emit_respects_budget_and_two_regimes() -> None:
    h, w = 64, 64
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False

    # Synthetic range-front ridge at x=20 and piedmont Marussi/Radiometric ridge at x=44
    surf = (0.75 * np.exp(-((xx - 20.0) ** 2) / 3.0) + 0.45 * np.exp(-((xx - 44.0) ** 2) / 4.0)).astype(np.float32)
    mhtr_edge = (0.85 * np.exp(-((xx - 44.0) ** 2) / 2.5)).astype(np.float32)
    pied_mask = xx >= 32

    dots = MC.mhtr_corridor_submodular_emit(
        surf,
        mhtr_edge,
        pied_mask,
        eligible_mask=fp,
        n_dots=20,
        gamma=1.20,
        mhtr_weight=0.48,
        piedmont_quota_frac=0.25,
        min_spacing_px=2.5,
    )
    assert dots.shape == (h, w)
    assert dots.dtype == np.float32
    assert set(np.unique(dots)) <= {0.0, 1.0}
    assert int((dots > 0).sum()) == 20
    # Verify both range-front (x < 32) and piedmont (x >= 32) received dots
    assert int((dots[:, :32] > 0).sum()) >= 10
    assert int((dots[:, 32:] > 0).sum()) >= 5


def test_s11_run_card_and_certified_geotiff_artifacts() -> None:
    rc_docs = json.loads((ROOT / "docs" / "run-card-S11.json").read_text(encoding="utf-8"))
    rc_ev = json.loads((ROOT / "evidence" / "s11_run_card.json").read_text(encoding="utf-8"))
    assert rc_docs == rc_ev

    assert rc_docs["historical_verdict_before_directed_gate_fix"] == "promote"
    assert rc_docs["verdict"] == "negative"
    assert rc_docs["submission_ready_pending_selector"] is False
    assert rc_docs["current_policy_revalidation"]["status"] == "FAIL"
    assert rc_docs["current_policy_revalidation"]["ok_to_submit"] is False
    assert rc_docs["budget"]["experiments_run"] == 3
    assert rc_docs["budget"]["wall_clock_seconds"] <= 7200
    assert rc_docs["leakage_canary"]["all_pass"] is True
    assert rc_docs["leakage_canary"]["n_features_tested"] == 68
    assert rc_docs["leakage_canary"]["worst_symmetric_auc"] <= 0.90

    ph = rc_docs["scores"]["primary_holdout"]
    assert ph["label"] == "HOLDOUT-DTI"
    assert ph["evaluator_version"] == "gems91-hide-recover-v1.0"
    assert ph["n_withheld_positives"] == 60988
    assert ph["score"] > ph["h91_e1_reference_holdout_dti"] > ph["b0_reference_holdout_dti"]
    assert ph["ci_95"][0] > ph["h91_e1_reference_ci_95"][1]  # Non-overlapping 95% CIs!

    uniq = rc_docs["registry_uniqueness"]
    assert uniq["historical_v1_0_uniqueness_pass"] is True
    assert uniq["uniqueness_pass"] is False
    assert uniq["uniqueness_gate_version"] == "gems91-directed-registry-v1.1"
    assert uniq["rasters_checked"] >= 60
    assert uniq["max_surface_abs_rank_corr"] <= 0.90
    assert uniq["max_3px_dot_overlap"] > 0.70
    assert uniq["dots_closest_raster"] == "calib_r13lattice_00904.tif"

    sub = rc_docs["submission"]
    assert 1 <= len(sub["recommended_form_note"]) <= 140
    assert sub["recommended_form_note_length"] == len(sub["recommended_form_note"])

    tif_path = ROOT / "docs" / "downloads" / sub["recommended_upload_file"]
    zip_path = ROOT / "docs" / "downloads" / sub["recommended_zip_download"]
    audit_path = ROOT / "docs" / "downloads" / sub["audit_json"]
    assert tif_path.is_file()
    assert zip_path.is_file()
    assert audit_path.is_file()

    tif_bytes = tif_path.read_bytes()
    assert len(tif_bytes) == sub["bytes_zeros_tif"]
    assert hashlib.sha256(tif_bytes).hexdigest() == sub["sha256_zeros_tif"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == sub["sha256_zeros_zip"]

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert zf.namelist() == [sub["recommended_upload_file"]]
        assert zf.read(sub["recommended_upload_file"]) == tif_bytes

    with rasterio.open(tif_path) as ds:
        assert ds.count == 1
        assert (ds.height, ds.width) == (3730, 3292)
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert ds.nodata is None
        arr = ds.read(1)
        assert np.isfinite(arr).all()
        assert float(arr.min()) == 0.0
        assert float(arr.max()) == 1.0
        assert int((arr > 0).sum()) == sub["n_dots"]

    # Check S11 HTML pages and local links
    for html_rel in (Path("docs/s11-mhtr.html"), Path("docs/s11-executive-summary.html")):
        hp = ROOT / html_rel
        assert hp.is_file()
        txt = hp.read_text(encoding="utf-8")
        assert sub["candidate_id"] in txt
        assert sub["sha256_zeros_tif"] in txt
        assert sub["recommended_form_note"] in html.unescape(txt)
        for m in re.finditer(r'(?:href|src)="([^"]+)"', txt):
            target = m.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:", "javascript:")):
                continue
            clean_rel = target.split("#", 1)[0].split("?", 1)[0]
            if not clean_rel:
                continue
            resolved = (hp.parent / clean_rel).resolve()
            assert resolved.exists(), f"Broken link {target!r} in {html_rel}"
            rel_to_root = resolved.relative_to(ROOT)
            ign = subprocess.run(["git", "check-ignore", "-q", str(rel_to_root)], cwd=ROOT)
            assert ign.returncode != 0, f"GitHub Pages asset {rel_to_root} is gitignored!"
