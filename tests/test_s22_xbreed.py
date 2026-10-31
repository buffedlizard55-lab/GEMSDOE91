"""Session 22 (S22-XB) integrity suite: artifacts, verdict logic, evidence JSONs, pages, README and the preregistration chain.

Everything here is recomputed from files on disk; nothing is asserted from memory.  Data-dependent checks skip cleanly when
the git-ignored competition inputs are absent (fresh CI checkouts).
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

import numpy as np
import pytest
import rasterio
import tifffile

from gems91 import xbreed22 as X

ROOT = Path(__file__).resolve().parents[1]
CARD = json.loads((ROOT / "docs/run-card-S22-XB.json").read_text())
S22 = ROOT / "docs/s22-xb"
SUB = CARD["submission"]
HAVE_DATA = (ROOT / "data/official/existing_faults.tif").is_file() and (ROOT / "data/official/sample_submission.tif").is_file()


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.states, self.downloads, self.text = [], set(), [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if "download" in a:
                self.downloads.append(a["href"])
        if "data-submission-ready" in a:
            self.states.append(a["data-submission-ready"])

    def handle_data(self, d):
        self.text.append(d)


def _page(rel: str) -> _Page:
    p = _Page()
    p.feed((ROOT / rel).read_text())
    return p


# ---------------------------------------------------------------- artifact
def test_artifact_hashes_names_and_note_limits():
    tif, zp = ROOT / SUB["tif_file"], ROOT / SUB["zip_file"]
    assert sha256(tif) == SUB["sha256"] == CARD["raster_sha256"]
    assert sha256(zp) == SUB["zip_sha256"]
    assert tif.stat().st_size == SUB["tif_bytes"] and zp.stat().st_size == SUB["zip_bytes"]
    assert 0 < len(SUB["name"]) <= 140 and 0 < len(SUB["note"]) <= 140 and len(SUB["note"]) == SUB["note_length"]
    assert SUB["name"] == tif.stem


def test_geotiff_is_all_finite_binary_single_band_and_matches_official_grid():
    tif = ROOT / SUB["tif_file"]
    a = tifffile.imread(tif)
    assert a.shape == (3730, 3292) and a.dtype == np.float32
    assert np.isfinite(a).all() and float(a.min()) == 0.0 and float(a.max()) == 1.0
    assert set(np.unique(a).tolist()) == {0.0, 1.0}
    assert int((a > 0).sum()) == CARD["validator"]["n_dots"] == X.DOT_BUDGET
    with rasterio.open(tif) as ds:
        assert ds.count == 1 and ds.dtypes[0] == "float32" and ds.nodata is None
        assert str(ds.crs) == "EPSG:32611"
        assert tuple(ds.transform)[:6] == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    with zipfile.ZipFile(ROOT / SUB["zip_file"]) as zf:
        assert zf.namelist() == [tif.name] and zf.testzip() is None
        assert zf.read(tif.name) == tif.read_bytes()


@pytest.mark.skipif(not HAVE_DATA, reason="competition inputs are git-ignored; restore with scripts/restore_data.py")
def test_zero_mass_on_catalogue_inside_footprint_and_collar_and_equalized_quadrants():
    from scipy import ndimage as ndi

    a = tifffile.imread(ROOT / SUB["tif_file"])
    with rasterio.open(ROOT / "data/official/existing_faults.tif") as ds:
        cat = ds.read(1) == 1
    with rasterio.open(ROOT / "data/official/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    pos = a > 0
    assert not (pos & cat).any() and not (pos & ~fp).any()
    d = ndi.distance_transform_edt(~cat)
    assert float(d[pos].min()) > 3.0
    assert CARD["quadrant_dot_counts"] == list(X.QUAD_BUDGETS)
    assert CARD["validator"]["min_inter_dot_distance_px"] >= 2.0


def test_validator_block_passes_and_is_automated():
    v = CARD["validator"]
    assert v["automated_without_human_intervention"] is True and v["pass"] is True
    assert v["nan_or_inf_pixels"] == 0 and v["positives_on_catalogue"] == 0 and v["positives_outside_footprint"] == 0
    assert v["zip_single_tif_member"] and v["zip_crc_ok"] and v["crs_shape_transform_match_sample"]


# ---------------------------------------------------------------- verdict logic
def test_verdict_is_a_pure_function_of_the_gates_and_no_slot_is_spent():
    g = CARD["gates"]
    required = ("G1_format", "G2_uniqueness_protocol", "G3_leakage_canary", "G4_holdout_paired", "G5_live_anchored_projection")
    assert CARD["ok_to_download"] == g["G1_format"]["pass"]
    assert CARD["ok_to_submit"] == all(g[k]["pass"] for k in required)
    assert CARD["failed_gates"] == [k for k in required if not g[k]["pass"]]
    assert CARD["verdict"] == ("promote" if CARD["ok_to_submit"] else "negative")
    assert CARD["slots_used"] == 0 and CARD["organizer_confirmed_score"] is None


def test_g4_requires_paired_interval_above_zero_under_both_recipes_and_matches_stored_numbers():
    g4 = CARD["gates"]["G4_holdout_paired"]
    unc, cap = g4["paired_C_minus_A_uncapped_celf"], g4["paired_C_minus_A_capped_celf"]
    hold = json.loads((S22 / "holdout.json").read_text())
    capped = json.loads((S22 / "holdout-capped.json").read_text())
    assert unc == hold["paired_differences"]["C_minus_A_celf"] and cap == capped["paired_C_minus_A_celf_cap"]
    assert g4["pass"] == (CARD["selected_arm"] == "C" and unc["ci95"][0] > 0 and cap["ci95"][0] > 0)
    # measured facts recorded in the docs (a change here must be a conscious update of the narrative)
    assert unc["delta"] == pytest.approx(0.004378, abs=1e-6) and cap["delta"] < 0
    assert hold["scores"]["static_R0"]["dti"] == pytest.approx(0.006697, abs=1e-6)  # reproduces S21's collar-paradox value


def test_holdout_split_and_evaluator_are_the_pinned_ones():
    hold = json.loads((S22 / "holdout.json").read_text())
    assert hold["evaluator_version"] == "gems57-pooled-hide-v2"
    assert hold["split_sha256"] == X.EXPECTED_SPLIT_SHA256 == CARD["holdout"]["split_sha256"]
    assert hold["withheld_positive_pixels"] == 60988
    from scripts.source_integrity import verify_historical_source
    pin = json.loads((ROOT / "registry/template_pin.json").read_text())
    for fname, sha in pin["sha256"].items():
        rel = pin.get("source_path", "vendor/gems57/") + fname
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == sha
        verify_historical_source(ROOT, rel, CARD["template_pins_verified"][rel])


@pytest.mark.skipif(subprocess.run(["git", "cat-file", "-e", "53ddff6"], cwd=ROOT, capture_output=True).returncode != 0,
                    reason="git history of the preregistration commit not available")
def test_preregistration_hash_chain_matches_git_history():
    first = subprocess.run(["git", "show", "53ddff6:docs/HYPOTHESES_S22_XBREED.md"], cwd=ROOT, capture_output=True, check=True).stdout
    assert hashlib.sha256(first).hexdigest() == CARD["preregistration"]["sha256_before_experiments"]
    now = (ROOT / "docs/HYPOTHESES_S22_XBREED.md").read_text()
    for tag in ("Amendment A1", "Amendment A2", "Amendment A3"):
        assert tag in now
    assert now.encode().startswith(first.rstrip(b"\n"))  # the whole frozen text is a prefix: amendments and outcomes only append


# ---------------------------------------------------------------- evidence JSONs
def test_nine_site_audit_is_complete_verified_and_shows_one_lineage():
    d = json.loads((S22 / "nine-sites.json").read_text())
    sites = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    assert {r["site"] for r in d["rows"]} == sites
    import csv

    anchors = {(r["site"], r["submission_name"]): float(r["user_reported_public_dti"])
               for r in csv.DictReader(open(ROOT / "registry/lfi_live_anchors.csv"))}
    for r in d["rows"]:
        assert anchors[(r["site"], r["best_submission_name"])] == r["user_reported_public_dti"]
        assert r["evidence_class"] == "USER-REPORTED"
        assert r["file_exists_on_default_branch"] is True and r["checked_bytes_are_this_repo_file"] is True
        assert r["format"]["format_pass"] is True and r["format"]["nan_inside_footprint"] == 0
        assert r["raw_download_url"].startswith("https://github.com/buffedlizard55-lab/")
        if r["format"]["nan_pixels"] > 0:  # NaN-encoded best files must offer a verified all-finite twin
            t = r["all_finite_twin"]
            assert t and t["pixel_identical_dots"] and t["format"]["format_pass"] and t["format"]["nan_pixels"] == 0
    best = max(d["rows"], key=lambda r: r["user_reported_public_dti"])
    assert best["site"] == "GEMSDOE32" and best["user_reported_public_dti"] == pytest.approx(0.2778)
    assert min(v["share_within_3px_of_any_other_of_the_nine"] for v in d["uniqueness_among_nine"].values()) > 0.97
    assert d["pairwise"]["GEMSDOE25|GEMSDOE30"]["identical"] is True


def test_r0_decomposition_claims_hold_and_algebra_is_self_consistent():
    d = json.loads((S22 / "r0-decomposition.json").read_text())
    n = d["nesting_exact"]
    assert n["R0 subset of H27-4"] and n["H27-4 subset of D2.8"] and n["D2.8 subset of H19-5 network"] and n["R0 subset of GEMSDOE36 file"]
    ds = d["difference_sets"]
    assert (ds["D2.8 minus H27-4"]["n"], ds["H27-4 minus R0"]["n"], ds["GEMSDOE36 minus R0"]["n"]) == (3891, 2545, 1200)
    assert ds["D2.8 minus H27-4"]["max_distance_to_catalogue_px"] <= 1.0 + 1e-9 and ds["H27-4 minus R0"]["max_distance_to_catalogue_px"] <= 2.0 + 1e-9
    assert d["replicate_check"]["GEMSDOE31 raster pixel-identical to GEMSDOE28 H27-4"] and d["replicate_check"]["scores equal"]
    s = d["live_scores_user_reported"]
    T = X.credit_from_pure_fp_step(44090, 40199, s["D2.8"], s["H27-4 (GEMSDOE28)"])
    assert T == pytest.approx(d["pure_fp_model"]["T_from_step1_D2.8_to_H27-4"], abs=0.1)
    assert X.predicted_dti_after_pure_fp(T, s["H27-4 (GEMSDOE28)"], 2545) == pytest.approx(d["pure_fp_model"]["prediction_H27-4_to_R0"]["predicted"], abs=1e-4)
    assert abs(d["pure_fp_model"]["prediction_H27-4_to_R0"]["residual"]) < 0.001 and abs(d["pure_fp_model"]["prediction_R0_to_GEMSDOE36"]["residual"]) < 0.001


def test_instrument_validity_and_hypothesis_tests_are_recorded_with_the_s20_baseline_reproduced():
    d = json.loads((S22 / "instruments.json").read_text())
    assert d["n_anchors"] == 112 and d["ridge"] == 10.0
    assert d["baseline_refit"]["loso_rmse"] == pytest.approx(0.019816, abs=2e-4)
    assert d["baseline_refit"]["loso_spearman"] == pytest.approx(0.957, abs=2e-3)
    iv = d["instrument_validity"]
    assert iv["hide_v2"]["spearman_vs_live"] == pytest.approx(0.105, abs=0.002) and iv["hide_v2"]["ci95_bootstrap"][0] < 0 < iv["hide_v2"]["ci95_bootstrap"][1]
    assert iv["sgmc_dti_gt500m"]["ci95_bootstrap"][0] > 0.2          # moderate and significantly positive, contra the n=7 claim
    assert iv["lfi_loso"]["spearman_vs_live"] > 0.95
    assert d["H22_3_damage_decay"]["kill_test_fresh"]["refuted"] is True
    assert d["H22_2_strike_discontinuity"]["direction"].startswith("contradicts") and d["H22_2_strike_discontinuity"]["accepted"] is False


def test_uniqueness_screen_is_wide_and_literal_blanket_overlap_is_disclosed():
    u = CARD["uniqueness"]
    assert u["n_compared_rasters_total"] > 1000 and u["n_competitive_non_blanket_rasters"] > 900
    assert u["dots_max_3px_overlap_competitive"] <= 0.70 and u["surface_max_abs_spearman"] <= 0.90 and u["competitive_unique_pass"]
    assert u["literal_all_raster_max_3px_overlap"] > 0.70          # synthetic blankets: disclosed, never hidden
    pass1 = json.loads((S22 / "registry-screen-pass1.json").read_text())
    assert pass1["dots_phase_competitive"]["max_3px_overlap_all_competitive"] > 0.70   # why amendment A3 was needed


def test_probe_predictions_match_the_forward_model_and_precede_any_score():
    p = json.loads((S22 / "probe-predictions.json").read_text())
    assert p["preregistered"].startswith("yes") and p["slots_needed"] == 2
    dti1 = p["base"]["user_reported"]
    for r in p["predictions"]["grid"]:
        F = (r["T"] / dti1 - 0.2 * r["T"] - 0.8 * r["G"]) / 0.2
        f = X.predict_probe_scores(r["T"], r["G"], F, lam=0.5, k_null=2000)
        assert f["S3"] == pytest.approx(r["S3_pred"], abs=2e-4) and f["S2"] == pytest.approx(r["S2_pred"], abs=2e-4)
    assert 0.254 < p["predictions"]["S3_range"][0] <= p["predictions"]["S3_range"][1] < 0.256


def test_official_sources_record_urls_and_the_sandbox_reachability_test():
    d = json.loads((S22 / "official-sources.json").read_text())
    assert d["retrieved_utc"] == "2026-10-26"
    assert all(f["url"].startswith("https://") for f in d["facts"])
    assert {"A4", "A5", "A6", "A9", "A10", "A11"} <= {f["id"] for f in d["facts"]}
    assert set(d["sandbox_reachability_curl_http_code"].values()) == {"000"}


def test_artifact_policy_registers_the_s22_files_as_research_only():
    pol = {e["path"]: e for e in json.loads((ROOT / "registry/artifact_policy.json").read_text())["files"]}
    assert pol[SUB["tif_file"]]["sha256"] == SUB["sha256"] and pol[SUB["tif_file"]]["status"] == "current_research_only"
    assert pol[SUB["zip_file"]]["sha256"] == SUB["zip_sha256"]


# ---------------------------------------------------------------- pages and README
def _check_links(rel: str, page: _Page):
    base = (ROOT / rel).parent
    for href in page.links:
        u = urlsplit(href)
        if u.scheme or u.netloc:
            continue
        target = (base / unquote(u.path)).resolve() if u.path else (ROOT / rel)
        assert target.is_file(), f"broken link in {rel}: {href}"
        assert target.is_relative_to(ROOT)
        if u.fragment and target.suffix == ".html":
            other = _Page()
            other.feed(target.read_text())
            assert u.fragment in other.ids, f"missing #{u.fragment} in {target}"


def test_own_executive_summary_states_the_same_verdict_as_the_run_card():
    rel = "docs/s22-xbreed-executive-summary.html"
    page = _page(rel)
    txt = " ".join(page.text)
    assert page.states == [str(CARD["ok_to_submit"]).lower()], "exactly one data-submission-ready, equal to the card"
    assert f"downloads/{Path(SUB['tif_file']).name}" in page.downloads and f"downloads/{Path(SUB['zip_file']).name}" in page.downloads
    assert ("OK TO DOWNLOAD: YES" in txt) == CARD["ok_to_download"]
    assert ("NOT OK TO SUBMIT" in txt) == (not CARD["ok_to_submit"])
    raw = (ROOT / rel).read_text()
    assert SUB["note"] in raw and SUB["name"] in raw and SUB["sha256"] in txt
    _check_links(rel, page)


@pytest.mark.parametrize("rel", ["docs/index.html", "docs/executive-summary.html"])
def test_current_lane_entry_pages_do_not_surface_archived_xbreed_as_current(rel):
    """Only the current pointer may recommend a lane; XB remains reachable in its own archive page."""
    raw = (ROOT / rel).read_text()
    assert 'id="s22-xb-parallel"' not in raw
    assert "S22-XB GeoTIFF" not in raw
    assert "gems91-s22-xbreed-c-37654dots" not in raw
    assert "s22-xbreed-executive-summary.html" not in raw
    assert "OMTJ" in raw and "OK TO SUBMIT: NO" in raw
    page = _page(rel)
    assert len(page.states) == 1
    _check_links(rel, page)


def test_executive_summary_contains_every_requested_element_and_all_nine_sites():
    t = (ROOT / "docs/s22-xbreed-executive-summary.html").read_text()
    for needle in ("How to submit", "Predicted values must be in range [0, 1]", "140", "USER-REPORTED", "PROJECTION", "NOT UNIQUE",
                   "Why 0.2778", "preregistered", "Limitations and the access needed", "learning probes", "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"):
        assert needle in t, needle
    nine = json.loads((S22 / "nine-sites.json").read_text())
    for r in nine["rows"]:
        tw = r.get("all_finite_twin")
        shown = tw["path_in_repo"] if tw and tw["pixel_identical_dots"] and tw["format"]["format_pass"] else r["file_path_in_repo"]
        assert r["site"] in t and Path(shown).name in t, r["site"]
    assert "PROJECTION" in t and "ORGANIZER-CONFIRMED" not in t.replace("no organizer receipts", "")


def test_readme_and_governance_files_mention_the_file_keep_the_brief_and_do_not_displace_the_current_lane():
    readme = (ROOT / "README.md").read_text()
    assert "<!--S22-README-BEGIN-->" in readme and "<!--S22-README-END-->" in readme
    block = readme[readme.index("<!--S22-README-BEGIN-->"):readme.index("<!--S22-README-END-->")]
    assert Path(SUB["tif_file"]).name in block and SUB["sha256"] in block and "Parallel Session 22 lane" in block
    assert readme.index("<details>") < readme.index("<!--S22-README-BEGIN-->")  # older lane is now explicitly historical
    assert readme.startswith("# GEMSDOE91 — ACTIVE: 2026-10-31")    assert "S22-XB lane (claims, not receipts)" in readme and "Session 20 Standing Prompt Addendum" in readme and "full-project-brief" in readme
    for f, tag in (("IRREGULARITIES.md", "IR-S22XB-01"), ("LIMITATIONS_AND_NEXT_STEPS.md", "parallel lane `S22-XB`"),
                   ("SLOT_PLAN.md", "SESSION 22 BANNER"), ("AI_USE.md", "Session 22"), ("PASS_LOG.md", "parallel lane `S22-XB`")):
        assert tag in (ROOT / f).read_text(), f
    irr = (ROOT / "IRREGULARITIES.md").read_text()
    assert "IR-S22-01" in irr and "IR-S22XB-13" in irr          # both parallel lanes' registers coexist without ID collision
