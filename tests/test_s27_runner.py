"""Session 27 (`S27-CVDC`) receipt, GeoTIFF, portal, and link-integrity tests."""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import rasterio

from gems91.readiness import submission_ready
from scripts import render_s27_cvdc_portal, run_s27_cvdc

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for k, v in attrs:
            if k in ("href", "src") and v:
                self.hrefs.append(v)


def test_allocate_exact_budget():
    for total, areas in [(37_654, [17846, 9957, 4111, 5740]), (37_654, [1, 2, 3, 4]), (11, [1, 1, 1, 1])]:
        out = run_s27_cvdc.allocate(total, areas)
        assert sum(out) == total
        assert len(out) == len(areas)
        assert all(v >= 0 for v in out)


def test_s27_run_card_fail_closed_and_matches_artifact_bytes():
    card = _load("docs/s27-cvdc/run-card.json")
    alias = _load("docs/run-card-S27-CVDC.json")
    assert card == alias
    assert card["verdict"] == "negative"
    assert card["ok_to_submit"] is False
    assert card["ok_to_download"] is True
    assert submission_ready(card) is False
    assert card["organizer_confirmed_score"] is None
    assert card["estimated_leaderboard_score"] is None
    assert card["submission_slots_used"] == 0
    assert card["experiments_run"] == 3 and card["max_experiments"] == 3
    assert 0 < len(card["submission_note"]) <= 140

    prereg_sha = hashlib.sha256((ROOT / "docs/s27-cvdc/preregistration.md").read_bytes()).hexdigest()
    assert card["preregistration"]["sha256"] == prereg_sha

    h = card["holdout"]
    assert h["label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["split_version"] == "label-blind-quadrants-v3-feature-buffered"
    assert h["n_withheld_positives"] == 60_988
    assert h["selected_experiment"] == "e2"
    assert h["selected_arm"] == "cvdc_e2_stage2_submod"
    assert h["beats_best_matched_control_ci95"] is True
    assert h["paired_differences_all_controls"]["control_s25_fabric_e2"]["ci95"][0] > 0.0
    assert h["paired_differences_all_controls"]["control_oof_base"]["ci95"][0] > 0.0

    c = card["correlation_overlap_vs_registry"]
    assert c["surface_pass_le_0.90"] is True and c["surface_max_abs_rho"] <= 0.90
    assert c["final_dot_rho_pass_le_0.90"] is True and c["final_dot_max_abs_rho"] <= 0.90
    assert c["final_dot_pass_nine_le_0.70"] is True and c["final_dot_max_overlap_nine_leaders"] <= 0.70
    assert c["final_dot_pass_competitive_le_0.70"] is True and c["final_dot_max_overlap_competitive_le_90000px"] <= 0.70
    assert c["final_dot_pass_all_incl_blankets_le_0.70"] is False and c["final_dot_max_overlap_all"] > 0.70

    tif_path = ROOT / card["artifact"]["tif"]
    zip_path = ROOT / card["artifact"]["zip"]
    sidecar_path = tif_path.with_suffix(".json")
    assert tif_path.is_file() and zip_path.is_file() and sidecar_path.is_file()
    tif_bytes = tif_path.read_bytes()
    assert hashlib.sha256(tif_bytes).hexdigest() == card["raster_sha256"]
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == card["artifact"]["zip_sha256"]
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == tif_bytes

    with rasterio.open(tif_path) as ds:
        arr = ds.read(1)
        assert ds.count == 1
        assert ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611"
        assert (ds.height, ds.width) == (3730, 3292)
        assert list(ds.transform)[:6] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0]
        assert ds.nodata is None
    assert np.isfinite(arr).all()
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    assert np.isin(arr, (0.0, 1.0)).all()
    assert int((arr > 0).sum()) == 37_654


def test_s27_canaries_and_diagnostics_integrity():
    can = _load("docs/s27-cvdc/canaries.json")
    assert can["all_pass"] is True
    assert can["max_symmetric_auc"] <= 0.90
    assert can["n_features_tested"] == 47
    assert can["n_fold_checks"] == 47 * 5
    assert all(r["status"] == "MEASURED" and r["symmetric_auc"] <= 0.90 for r in can["canaries"])

    diag = _load("docs/s27-cvdc/diagnostics.json")
    assert diag["lfi"]["label_class"] == "MODEL_PROJECTION_NOT_A_SCORE"
    assert diag["candidate"]["organizer_confirmed_score"] is None
    assert diag["candidate"]["sha256"] == _load("docs/s27-cvdc/run-card.json")["raster_sha256"]


def test_s27_runner_refuses_implicit_overwrite():
    with pytest.raises(RuntimeError, match="already recorded"):
        run_s27_cvdc.cmd_features(SimpleNamespace())
    with pytest.raises(RuntimeError, match="already recorded"):
        run_s27_cvdc.cmd_experiment(SimpleNamespace(exp="e2"))
    with pytest.raises(RuntimeError, match="already recorded"):
        run_s27_cvdc.cmd_package(SimpleNamespace())


def test_s27_portal_idempotent_and_links_resolve():
    exec_path = ROOT / "docs/s27-cvdc/executive-summary.html"
    idx_path = ROOT / "docs/index.html"
    before_exec = exec_path.read_bytes()
    before_idx = idx_path.read_bytes()
    assert render_s27_cvdc_portal.main() == 0
    assert exec_path.read_bytes() == before_exec
    assert idx_path.read_bytes() == before_idx

    for rel in ("docs/s27-cvdc/executive-summary.html", "docs/index.html", "docs/executive-summary.html", "index.html"):
        page_path = ROOT / rel
        text = page_path.read_text(encoding="utf-8")
        assert "OK TO SUBMIT: NO" in text
        assert "OK TO SUBMIT: YES" not in text
        assert "CLEARED TO SUBMIT" not in text.upper()
        parser = _HrefParser()
        parser.feed(text)
        for href in parser.hrefs:
            if href.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
                continue
            clean = href.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            target = (page_path.parent / clean).resolve()
            assert target.exists(), f"Broken link in {rel}: {href} -> {target}"

    exec_text = exec_path.read_text(encoding="utf-8")
    for site_num in ("24", "25", "27", "28", "30", "31", "32", "33", "36", "91", "92"):
        assert f"GEMSDOE{site_num}" in exec_text

    for md_rel in ("docs/s27-cvdc/GEOTHERMAL_AND_FAULT_RESEARCH.md", "docs/s27-cvdc/preregistration.md", "docs/s27-cvdc/REVIEW.md"):
        md_path = ROOT / md_rel
        md_text = md_path.read_text(encoding="utf-8")
        for m in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", md_text):
            href = m.group(1).strip()
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean = href.split("#", 1)[0]
            if clean:
                target = (md_path.parent / clean).resolve()
                assert target.exists(), f"Broken markdown link in {md_rel}: {href}"
