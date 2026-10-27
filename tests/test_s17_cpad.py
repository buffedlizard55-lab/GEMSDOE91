"""Unit, invariance, gate, and published-artifact contract tests for Session 17 (S17-CPAD)."""
from __future__ import annotations

import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt as edt
from scipy.spatial import cKDTree

from gems91 import cpad17
from gems91.readiness import gates, submission_ready
from scripts.verify_s17 import verify

ROOT = Path(__file__).resolve().parents[1]


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.states = []
        self.downloads = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag in ("a", "link") and "href" in a:
            self.links.append(a["href"])
        if tag in ("script", "img") and a.get("src"):
            self.links.append(a["src"])
        if tag == "a" and "download" in a:
            self.downloads.append(a.get("href"))
        if "data-submission-ready" in a:
            self.states.append(a["data-submission-ready"])

    def handle_data(self, data):
        self.text.append(data)


def test_cpad_subsurface_columns_are_bitwise_band12_band19_invariant(tmp_path):
    rng = np.random.default_rng(1701)
    h, w = 36, 36
    fp = np.ones((h, w), dtype=bool)
    fp[:2, :] = False
    bands_a = {b: rng.normal(0.0, 1.0, size=(h, w)).astype(np.float32) for b in range(1, 21)}
    bands_a[15] = np.abs(bands_a[15]) * 1200.0 + 100.0  # positive depth-to-basement
    bands_b = {b: arr.copy() for b, arr in bands_a.items()}
    bands_b[12] = bands_b[12] * -13.0 + 1000.0  # Band 12 detrended elevation perturbed
    bands_b[19] = np.abs(bands_b[19]) * 50.0 + 250.0  # Band 19 elevation slope perturbed

    gdr_csv = tmp_path / "gdr.csv"
    with gdr_csv.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["row", "col", "temp_c", "geothermquartz_c", "geothermchalc_c", "geothermcat_c", "thermalclass", "dist_known_fault_px"],
        )
        writer.writeheader()
        writer.writerow({"row": "18", "col": "18", "temp_c": "45.0", "geothermquartz_c": "115.0", "geothermchalc_c": "85.0", "geothermcat_c": "135.0", "thermalclass": "hot", "dist_known_fault_px": "0.5"})

    fa, meta = cpad17.compute_cpad_arrays_from_bands(bands_a, fp, gdr_csv=gdr_csv)
    fb, _ = cpad17.compute_cpad_arrays_from_bands(bands_b, fp, gdr_csv=gdr_csv)
    assert fa.shape == (int(fp.sum()), 16)
    assert np.isfinite(fa).all() and np.isfinite(fb).all()
    sub_cols = list(meta["dem_free_cols"])
    topo_cols = list(meta["topo_conditioned_cols"])
    assert sub_cols == list(range(14)) and topo_cols == [14, 15]
    max_sub_diff = float(np.max(np.abs(fa[:, sub_cols] - fb[:, sub_cols])))
    assert max_sub_diff == 0.0
    # Topographic cover columns (14, 15) SHOULD respond to Band 12 / Band 19 changes
    assert float(np.max(np.abs(fa[:, topo_cols] - fb[:, topo_cols]))) > 0.0


def test_strict_topo_exclusion_strips_all_dem_and_lidar_features():
    feat = json.loads((ROOT / "docs/s17/features.json").read_text())
    sub_names = set(feat["stage1_pure_subsurface_features"])
    assert len(feat["stage1_full_features"]) == 128
    assert len(sub_names) == 100
    assert sub_names.isdisjoint(cpad17.STRICT_TOPO_FEATURE_NAMES)
    for forbidden_prefix in ("b12_", "b19_", "lidar_", "e1_lrm_", "e1_topo_", "e1_slope_", "ptha_scarp_"):
        assert not any(n.startswith(forbidden_prefix) for n in sub_names), forbidden_prefix


def test_gdr_disequilibrium_excludes_banned_fault_distance_and_is_row_order_invariant(tmp_path):
    fp = np.ones((20, 20), dtype=bool)
    rows = [
        {
            "row": "7",
            "col": "9",
            "temp_c": "45.0",
            "geothermcat_c": "135.0",
            "geothermquartz_c": "110.0",
            "geothermchalc_c": "85.0",
            "thermalclass": "warm",
            "dist_known_fault_px": "0.1",
        },
        {
            "row": "7",
            "col": "9",
            "temp_c": "60.0",
            "geothermcat_c": "95.0",
            "geothermquartz_c": "120.0",
            "geothermchalc_c": "80.0",
            "thermalclass": "hot",
            "dist_known_fault_px": "999.0",
        },
    ]
    csv_a = tmp_path / "a.csv"
    csv_b = tmp_path / "b.csv"
    fieldnames = list(rows[0].keys())
    with csv_a.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    # Reverse row order AND mutate banned dist_known_fault_px by +1,000,000
    mutated = [dict(r, dist_known_fault_px="1000000.0") for r in reversed(rows)]
    with csv_b.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(mutated)

    diseq_a, enth_a, stats_a = cpad17.extract_gdr_disequilibrium_impulses(csv_a, fp.shape, fp)
    diseq_b, enth_b, stats_b = cpad17.extract_gdr_disequilibrium_impulses(csv_b, fp.shape, fp)
    assert np.array_equal(diseq_a, diseq_b) and np.array_equal(enth_a, enth_b)
    assert stats_a["cells_populated"] == 1 and stats_b["cells_populated"] == 1
    assert "dist_known_fault_px" in cpad17.BANNED_GDR_COLUMNS
    assert float(diseq_a.max()) > 0.0


def test_bayes_reference_odds_calibration_cancels_negative_subsample_ratio():
    pi_true = 0.0118
    p_true = 0.02
    odds_true = p_true / (1.0 - p_true)
    fp = np.ones((1, 1), dtype=bool)
    calibrated = []
    for pi_sample in (0.05, 0.18, 0.33):
        odds_raw = odds_true * ((pi_sample / (1.0 - pi_sample)) / (pi_true / (1.0 - pi_true)))
        p_raw = np.array([[odds_raw / (1.0 + odds_raw)]], dtype=np.float32)
        cal = cpad17.calibrate_reference_odds_surface(
            p_raw,
            fp,
            pi_vis_train=pi_true,
            pi_sample_weighted=pi_sample,
            c0_multiplier=12.0,
        )
        calibrated.append(float(cal[0, 0]))
    assert np.allclose(calibrated[0], calibrated[1], atol=1e-6)
    assert np.allclose(calibrated[1], calibrated[2], atol=1e-6)
    assert 0.10 < calibrated[0] < 0.30


def test_global_nms_and_submodular_emitters_enforce_collar_spacing_and_range():
    rng = np.random.default_rng(42)
    h, w = 60, 60
    fp = np.ones((h, w), dtype=bool)
    fp[:3, :] = False
    vis = np.zeros((h, w), dtype=bool)
    vis[30, 20:40] = True
    score = rng.uniform(0.01, 0.99, size=(h, w)).astype(np.float32)

    for out in (
        cpad17.emit_global_dots_nms(score, vis, fp, budget=40, collar_px=3.05, min_spacing_px=3.05),
        cpad17.emit_global_dots_submodular(score, vis, fp, budget=40, collar_px=3.05, min_spacing_px=3.05),
    ):
        assert out.dtype == np.float32 and out.shape == (h, w)
        assert np.isfinite(out).all()
        assert np.isin(out, [0.0, 1.0]).all()
        assert int((out > 0).sum()) == 40
        assert (out[~fp] == 0.0).all()
        assert float(edt(~vis)[out > 0].min()) > 3.0
        pts = np.argwhere(out > 0)
        assert float(cKDTree(pts).query(pts, k=2)[0][:, 1].min()) > 3.0


def test_s17_verifier_provenance_and_portal_contract():
    res = verify(with_data=False)
    assert res["status"] == "PASS"
    assert res["ok_to_download"] is True
    assert res["ok_to_submit"] is False
    assert res["geological_experiments_rerun"] == 0

    card = json.loads((ROOT / "docs/run-card-S17-CPAD.json").read_text())
    assert gates(card) == {
        "format": True,
        "canary": True,
        "novelty": False,
        "assigned_lane": False,
        "beats_comparable_best": False,
        "separate_selector": False,
    }
    assert submission_ready(card) is False

    prov = json.loads((ROOT / "docs/s17/provenance.json").read_text())
    assert hashlib.sha256((ROOT / prov["preregistration"]["path"]).read_bytes()).hexdigest() == prov["preregistration"]["sha256"]
    from src.gems91.provenance import verify_recorded_source
    for rel, digest in prov["code_sha256"].items():
        assert verify_recorded_source(ROOT, rel, digest) in ('UNCHANGED', 'ARCHIVED_ORIGINAL_AND_PINNED_CORRECTION'), rel

    tif_rel = card["artifact"]["file"]
    zip_rel = card["artifact"]["zip"]
    for page_rel in ("docs/s17-cpad.html", "docs/s17-cpad-executive-summary.html"):
        path = ROOT / page_rel
        p = _Page()
        p.feed(path.read_text())
        txt = " ".join(p.text)
        assert p.states == ["false"]
        assert "OK TO DOWNLOAD: YES" in txt and "OK TO SUBMIT: NO" in txt
        assert "NOT OK TO SUBMIT" in txt
        assert tif_rel in p.downloads and zip_rel in p.downloads
        for href in p.links:
            u = urlsplit(href)
            if u.scheme or u.netloc:
                continue
            target = (path.parent / unquote(u.path)).resolve() if u.path else path
            assert target.is_relative_to(ROOT) and target.is_file(), (page_rel, href)
            if u.fragment and target.suffix == ".html":
                q = _Page()
                q.feed(target.read_text())
                assert u.fragment in q.ids, (page_rel, href)


def test_emitters_handle_nan_inf_negative_surfaces_and_zero_budget_safely():
    h, w = 40, 40
    fp = np.ones((h, w), dtype=bool)
    vis = np.zeros((h, w), dtype=bool)
    dirty = np.full((h, w), -5.0, dtype=np.float32)
    dirty[5, 5] = np.nan
    dirty[6, 6] = np.inf
    dirty[7, 7] = -np.inf
    dirty[20, 20] = 0.85

    for fn in (cpad17.emit_global_dots_nms, cpad17.emit_global_dots_submodular):
        zero_out = fn(dirty, vis, fp, budget=0)
        assert np.isfinite(zero_out).all() and int((zero_out > 0).sum()) == 0
        dirty_out = fn(dirty, vis, fp, budget=5)
        assert np.isfinite(dirty_out).all()
        assert np.isin(dirty_out, [0.0, 1.0]).all()
        assert int((dirty_out > 0).sum()) == 1
        assert dirty_out[20, 20] == 1.0


def test_verify_s17_rejects_tampered_card(monkeypatch):
    import scripts.verify_s17 as vs17

    orig_read = vs17.read_json

    def tampered_read(rel):
        data = orig_read(rel)
        if rel == "docs/run-card-S17-CPAD.json":
            data = dict(data, ok_to_submit=True)
        return data

    monkeypatch.setattr(vs17, "read_json", tampered_read)
    try:
        vs17.verify(with_data=False)
        assert False, "Expected ValueError on tampered ok_to_submit=True"
    except ValueError as exc:
        assert "Negative candidate promoted" in str(exc)


def test_readme_preserves_full_project_brief_and_review_link():
    readme = (ROOT / "README.md").read_text()
    assert '<a id="full-project-brief"></a>' in readme
    assert "PARALLEL-RUN PROTOCOL — read first." in readme
    assert (ROOT / "docs/REVIEW-S17-CPAD-20261025.md").is_file()

