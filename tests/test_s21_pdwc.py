"""Automated regression and integrity suite for Session 21 (`S21-PDWC`).

Verifies on-disk GeoTIFF/ZIP format & [0,1] range without human intervention,
run-card protocol compliance, 9-site executive summary completeness, portal HTML
link/state invariants, and core `gems91.pdwc21` physics & uniqueness-capped CELF math.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import zipfile

import numpy as np
import tifffile

from gems91 import pdwc21 as P

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "docs/run-card-S21-PDWC.json").read_text())
NINE = json.loads((ROOT / "docs/nine-site-executive-summary-s21.json").read_text())


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.states: list[str] = []
        self.downloads: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(str(a["id"]))
        if tag in ("a", "link") and a.get("href"):
            self.links.append(str(a["href"]))
        if tag == "a" and "download" in a and a.get("href"):
            self.downloads.append(str(a["href"]))
        if "data-submission-ready" in a and a["data-submission-ready"] is not None:
            self.states.append(str(a["data-submission-ready"]))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def test_s21_geotiff_and_zip_are_valid_in_0_1_and_match_run_card() -> None:
    sub = CARD["submission"]
    val = CARD["validator"]
    tif_path = ROOT / sub["tif_file"]
    zip_path = ROOT / sub["zip_file"]
    assert tif_path.is_file() and zip_path.is_file()

    raw_tif = tif_path.read_bytes()
    raw_zip = zip_path.read_bytes()
    assert len(raw_tif) == sub["tif_bytes"]
    assert len(raw_zip) == sub["zip_bytes"]
    assert hashlib.sha256(raw_tif).hexdigest() == sub["sha256"] == CARD["raster_sha256"]
    assert hashlib.sha256(raw_zip).hexdigest() == sub["zip_sha256"]

    with tifffile.TiffFile(tif_path) as tf:
        assert len(tf.pages) == 1
        arr = tf.pages[0].asarray()
        tags = {t.name: t.value for t in tf.pages[0].tags.values()}

    assert arr.dtype == np.float32
    assert arr.shape == (3730, 3292)
    assert np.isfinite(arr).all(), "GeoTIFF must have zero NaN and zero Inf cells"
    assert float(arr.min()) == 0.0 and float(arr.max()) == 1.0
    uniq_vals = set(np.unique(arr).tolist())
    assert uniq_vals == {0.0, 1.0}, f"Expected binary {{0.0, 1.0}} dots, got {uniq_vals}"
    assert int((arr > 0).sum()) == val["n_dots"] == 37_654
    assert "GDAL_NODATA" not in tags
    assert tuple(tags["ModelTiepointTag"])[3:5] == (243350.0, 4508550.0)
    assert tuple(tags["ModelPixelScaleTag"])[:2] == (100.0, 100.0)

    with zipfile.ZipFile(zip_path) as zf:
        assert zf.namelist() == [tif_path.name]
        assert zf.read(tif_path.name) == raw_tif

    assert 0 < len(sub["note"]) <= 140
    assert sub["note_length"] == len(sub["note"])


def test_s21_run_card_protocol_fields_and_fail_closed_verdict() -> None:
    for req in (
        "hypothesis",
        "mechanism",
        "named_non_fault_mimic",
        "holdout",
        "canary",
        "uniqueness",
        "raster_sha256",
        "validator",
        "submission",
        "verdict",
    ):
        assert req in CARD and CARD[req] is not None

    assert CARD["verdict"] == "negative"
    assert CARD["ok_to_download"] is True
    assert CARD["ok_to_submit"] is False
    assert CARD["organizer_confirmed_score"] is None
    assert CARD["preregistration"]["experiments_run"] <= 3
    assert CARD["preregistration"]["within_2h_budget"] is True

    prereg_sha = hashlib.sha256((ROOT / CARD["preregistration"]["path"]).read_bytes()).hexdigest()
    assert prereg_sha == CARD["preregistration"]["sha256_before_experiments"]

    h = CARD["holdout"]
    assert h["score_label"] == "HOLDOUT-DTI"
    assert h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["n_withheld_positives"] == 60_988
    assert h["ci95"][0] < h["holdout_dti"] < h["ci95"][1]
    assert h["beats_s19_svhf_0147791"] is True
    assert h["beats_s18_hgbr_0200742"] is False

    can = CARD["canary"]
    assert can["n_features_tested"] == 82
    assert can["max_symmetric_auc"] <= 0.90
    assert can["subsurface_b12_b19_max_diff"] == 0.0
    assert can["pass"] is True

    uniq = CARD["uniqueness"]
    assert uniq["n_compared_rasters_total"] >= 1000
    assert uniq["n_competitive_non_blanket_rasters"] >= 900
    assert uniq["surface_max_abs_spearman"] <= 0.90
    assert uniq["dots_max_abs_spearman"] <= 0.90
    assert uniq["dots_max_3px_overlap_competitive"] <= 0.70
    assert uniq["competitive_unique_pass"] is True

    lfi = CARD["lfi_surrogate_projection"]
    assert lfi["label_class"] == "MODEL_PROJECTION_NOT_A_SCORE"
    assert 0.10 < lfi["ridge1"]["projected_value_model_only"] < 0.30

    pins = json.loads((ROOT / "registry/template_pin.json").read_text())["sha256"]
    for fname, expected_sha in pins.items():
        rel_path = f"vendor/gems57/{fname}"
        actual_sha = hashlib.sha256((ROOT / rel_path).read_bytes()).hexdigest()
        assert actual_sha == expected_sha == CARD["template_pins_verified"][rel_path]


def test_nine_site_executive_summary_covers_all_requested_sites() -> None:
    expected_sites = {
        "GEMSDOE24",
        "GEMSDOE25",
        "GEMSDOE27",
        "GEMSDOE28",
        "GEMSDOE30",
        "GEMSDOE31",
        "GEMSDOE32",
        "GEMSDOE33",
        "GEMSDOE36",
    }
    found = {r["site"] for r in NINE["sites"]}
    assert found == expected_sites
    assert NINE["overall_best_across_nine_sites"]["site"] == "GEMSDOE32"
    assert abs(NINE["overall_best_across_nine_sites"]["score"] - 0.2778) < 1e-9
    for r in NINE["sites"]:
        assert len(r["main_head_sha_20261026"]) == 40
        assert r["best_score_evidence_class"] == "USER-REPORTED"


def test_s21_pages_and_readme_links_and_verdict_are_consistent() -> None:
    tif_name = Path(CARD["submission"]["tif_file"]).name
    zip_name = Path(CARD["submission"]["zip_file"]).name
    for rel in ("docs/index.html", "docs/s21-pdwc-executive-summary.html", "docs/s21-pdwc.html"):
        page_path = ROOT / rel
        assert page_path.is_file()
        p = _LinkParser()
        p.feed(page_path.read_text())
        txt = " ".join(p.text)
        assert p.states == ["false"], f"{rel} must have exactly one data-submission-ready='false'"
        assert f"downloads/{tif_name}" in p.downloads
        assert f"downloads/{zip_name}" in p.downloads
        assert "OK TO DOWNLOAD: YES" in txt
        assert "NOT OK TO SUBMIT" in txt
        assert CARD["submission"]["note"] in page_path.read_text()
        for href in p.links:
            u = urlsplit(href)
            if u.scheme or u.netloc:
                continue
            target = (page_path.parent / unquote(u.path)).resolve() if u.path else page_path
            assert target.is_file(), f"Broken link in {rel}: {href}"
            assert target.is_relative_to(ROOT)
            if u.fragment and target.suffix == ".html":
                other = _LinkParser()
                other.feed(target.read_text())
                assert u.fragment in other.ids, f"Missing fragment #{u.fragment} in {target}"

    readme = (ROOT / "README.md").read_text()
    assert tif_name in readme and CARD["raster_sha256"] in readme
    assert "full-project-brief" in readme


def test_pdwc21_celf_uniqueness_cap_is_strict_on_synthetic_grid() -> None:
    rng = np.random.default_rng(21)
    h, w = 80, 80
    fp = np.ones((h, w), dtype=bool)
    cat = np.zeros((h, w), dtype=bool)
    cat[40, 10:70] = True
    surf = rng.uniform(0.05, 0.95, size=(h, w)).astype(np.float32)

    # Create a reference halo covering top half of grid
    ref_halo = np.zeros((h, w), dtype=bool)
    ref_halo[:45, :] = True
    words = np.zeros((h, w, 1), dtype=np.uint64)
    words[ref_halo, 0] = np.uint64(1)

    dots = P.emit_dots_celf_submodular(
        surf,
        cat,
        fp,
        budget=120,
        collar_px=2.5,
        min_spacing_px=2.5,
        ref_halo_words=words,
        n_refs=1,
        uniqueness_cap=0.50,
    )
    assert dots.dtype == np.float32
    assert int((dots > 0).sum()) == 120
    assert int((dots[cat] > 0).sum()) == 0
    overlap_frac = float((dots[ref_halo] > 0).sum()) / 120.0
    assert overlap_frac <= 0.50 + 1e-9
