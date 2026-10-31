"""Regression checks for the active no-lane/no-data review and portal labels."""
from __future__ import annotations

import csv
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class TextLinks(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.text: list[str] = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
    def handle_data(self, data):
        self.text.append(data)


def _json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_active_card_is_a_no_run_and_never_promotes():
    card = _json("docs/run-card-522615dd.json")
    assert card["session_branch"] == "arena/522615dd-gemsdoe91"
    assert card["status"] == "negative_blocked_no_run"
    assert card["assignment"]["single_method_paragraph_present"] is False
    assert card["assignment"]["lane_assigned"] is False
    assert card["experiment"]["started"] is False
    assert card["experiment"]["experiments_used"] == 0
    assert card["experiment"]["weekly_slots_used"] == 0
    assert card["verdict"] == "negative" and card["promote"] is False
    assert card["ok_to_submit"] is False
    assert card["organizer_confirmed_score"] is None


def test_stale_generic_current_review_card_is_not_misused():
    old = _json("docs/run-card-current-review.json")
    assert old["branch"] == "arena/2f002fa0-gemsdoe91"
    card = _json("docs/run-card-522615dd.json")
    assert card["session_branch"] == "arena/522615dd-gemsdoe91"


def test_no_run_card_does_not_turn_null_gates_into_passes():
    card = _json("docs/run-card-522615dd.json")
    assert card["data_preflight"]["verified_required_inputs"] == 0
    assert card["data_preflight"]["required_inputs"] == 2
    assert len(card["data_preflight"]["missing"]) == 2
    assert card["data_preflight"]["ready_axes"] == []
    assert len(card["data_preflight"]["blocked_axes"]) == 6
    assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
    assert card["holdout"]["status"] == "NOT_RUN"
    assert card["holdout"]["dti"] is None and card["holdout"]["ci95"] is None
    assert card["holdout"]["evaluator_version"] is None
    assert card["holdout"]["withheld_positive_count"] is None
    assert card["leakage_canary"]["status"] == "NOT_RUN"
    assert card["registry_correlation_overlap"]["status"] == "NOT_RUN"
    assert card["registry_correlation_overlap"]["surface_max_abs_spearman"] is None
    assert card["registry_correlation_overlap"]["final_dot_overlap_within_3px"] is None
    assert card["raster"]["created"] is False and card["raster"]["sha256"] is None
    assert card["raster"]["validator_output"]["status"] == "NOT_RUN_NO_NEW_RASTER"
    assert card["submission"]["name"] is None and card["submission"]["note"] is None
    assert card["submission"]["note_char_limit"] == 140
    assert card["submission"]["ok_to_download"] == "NO NEW TIFF"
    assert card["submission"]["ok_to_submit"] == "NO"


def test_prior_artifact_score_is_labeled_and_separate_from_active_no_run():
    card = _json("docs/run-card-522615dd.json")
    prior = card["existing_front_door_artifact"]["prior_result"]
    assert prior["evidence_class"] == "HOLDOUT-DTI"
    assert prior["status"] == "PRIOR_SESSION_RESULT_NOT_RERUN_IN_THIS_REVIEW"
    assert prior["evaluator_version"] == "gems57-pooled-hide-v2"
    assert prior["withheld_positive_count"] == 11321
    assert prior["ci95"][0] < prior["dti"] < prior["ci95"][1]
    existing = card["existing_front_door_artifact"]
    assert existing["revalidated_in_this_review"] is False
    assert existing["registered_tiff_zip_byte_identity_rechecked_in_this_review"] is True
    assert existing["format_rechecked_against_official_sample_in_this_review"] is False
    assert existing["recorded_submit_status"] == "NO"


def test_hypothesis_menu_is_ranked_proposal_not_lane_assignment():
    card = _json("docs/run-card-522615dd.json")
    text = (DOCS / "HYPOTHESES-ACTIVE-522615DD-20261025.md").read_text(encoding="utf-8")
    assert card["hypothesis"]["selected"] is None
    assert card["hypothesis"]["status"] == "PROPOSED_MENU_ONLY_NOT_ASSIGNED"
    assert "Topographic texture / spectral-slope break" in text
    assert "Within-map-unit potential-field residual displacement" in text
    assert "Seasonal Landsat surface-temperature residuals" in text
    assert "Named non-fault mimic" in text
    assert "expected numerical gain is projected" in text.lower()
    assert "not a lane assignment" in text.lower()
    assert "HOLDOUT-DTI" in text and "0.90" in text and "70%" in text


def test_official_source_register_has_provenance_and_availability_limits():
    sources = _json("docs/sources.json")
    urls = {row["url"] for row in sources}
    assert "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/" in urls
    assert "https://docs.nlr.gov/docs/fy26osti/96647.pdf" in urls
    assert "https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous" in urls
    assert "https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature" in urls
    assert "https://www.usgs.gov/3d-elevation-program/about-3dep-products-services" in urls
    sgmc = next(x for x in sources if x.get("url", "").endswith("sgmc-geodatabase-conterminous"))
    assert "CC0" in sgmc["verification"]
    assert "not downloaded" in sgmc["verification"].lower()
    rules = next(x for x in sources if x["url"] == "https://docs.nlr.gov/docs/fy26osti/96647.pdf")
    assert "narrative disclosure" in rules["verification"]


def test_reported_results_source_urls_are_well_formed_but_remain_unverified():
    with (DOCS / "reported-results.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 115
    assert all(urlsplit(r["source_url"]).scheme in {"http", "https"} for r in rows)
    assert all(urlsplit(r["source_url"]).netloc for r in rows)
    assert all(r["evidence_class"] == "USER_REPORTED_UNVERIFIED" for r in rows)
    assert all(r["organizer_receipt"] == "NOT_AVAILABLE" for r in rows)
    r0 = next(r for r in rows if r["reported_value"] == "0.2778")
    assert "GEMSDOE32" in r0["source_url"]


def test_current_portal_preserves_historical_review_and_research_labels():
    page = TextLinks()
    page.feed((DOCS / "index.html").read_text(encoding="utf-8"))
    text = " ".join(page.text)
    assert "REVIEW-ACTIVE-E649E460-20261025.md" in page.links
    assert "run-card-E649E460-20261025.json" in page.links
    assert "historical" in text.lower() and "research" in text.lower()
    assert "OK TO SUBMIT: NO" in text
    # Navigation uses research labels, not context-free rounded scores.
    assert "S17-LFTG research audit" in text and "S17-CPAD research audit" in text
    assert "LB-DTI" not in text
    assert "LB HOLDOUT-DTI" not in text
    research = TextLinks()
    research.feed((DOCS / "research.html").read_text(encoding="utf-8"))
    assert "LB HOLDOUT-DTI" not in " ".join(research.text)
    assert "Why 0.2778 leads" not in text


def test_executive_guide_distinguishes_projection_from_receipt_and_names_the_candidate():
    # Superseded 2026-10-31: docs/s28-pucc/executive-summary.html is the active
    # lane page (docs/executive-summary.html is the banner-stamped legacy portal).
    # The guard keeps its purpose — the guide must never let a projection masquerade
    # as an organizer score — but now also pins the validated candidate it approves.
    page = TextLinks()
    page.feed((DOCS / "s28-pucc" / "executive-summary.html").read_text(encoding="utf-8"))
    text = " ".join(page.text)
    assert "run-card.json" in page.links
    assert "../downloads/gems91-s28-pucc-ee2-37654dots-20261031T013552Z-cb42d2ce-zeros.tif" in page.links
    assert "MODEL_PROJECTION_NOT_A_SCORE" in text
    assert "ORGANIZER-CONFIRMED" in text
    assert "does not claim to beat 0.2778" in text
    assert "SUBMISSION APPROVED" in text
    # the pre-restoration review remains committed and keep its fail-closed wording
    old = (DOCS / "REVIEW-ACTIVE-E649E460-20261025.md").read_text(encoding="utf-8")
    assert "not an approval to upload" in old.lower() or "OK TO SUBMIT: NO" in old


def test_current_file_pointer_remains_prior_olc91_not_a_fabricated_new_result():
    # Session 522615dd produced no TIFF, so it could not move the pointer. A LATER session may move it
    # only to a measured lane card whose holdout evidence is committed (ISO91, session bacc7c26; S20-RHTW, session 06420fd7;
    # S28-VFCD, branch arena/ef686adc-gemsdoe91).
    current = _json("docs/current-run.json")
    assert current["run_card"] in ("run-card-OLC91.json", "run-card-ISO91.json", "run-card-S20-RHTW.json",
                                   "run-card-S22-OMTJ.json", "run-card-S28-VFCD.json")
    if current["run_card"] == "run-card-ISO91.json":
        card = _json("docs/run-card-ISO91.json")
        assert card["session"] != "arena/522615dd-gemsdoe91"
        for name in ("holdout-I1.json", "holdout-I2.json", "final.json"):
            assert (DOCS / "iso91" / name).is_file()
        assert card["holdout"]["primary"]["evidence_class"] == "HOLDOUT-DTI"
        assert card["organizer_confirmed_scores"] is None
    elif current["run_card"] == "run-card-S20-RHTW.json":
        card = _json("docs/run-card-S20-RHTW.json")
        assert card["session"] != "arena/522615dd-gemsdoe91"
        for name in ("holdout-i2.json", "holdout-i1-isolated.json", "canaries.json", "registry-audit.json", "blind-sgmc.json"):
            assert (DOCS / "s20_rhtw" / name).is_file()
        assert card["holdout"]["primary_i2"]["evidence_class"] == "HOLDOUT-DTI"
        assert card["organizer_confirmed_scores"] is None
    elif current["run_card"] == "run-card-S22-OMTJ.json":
        card = _json("docs/s22/run-card.json")
        assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
        assert card["organizer_confirmed_score"] is None
        assert card["correlation_overlap_vs_registry"]["final_dot_checks"]["registry_clearance"] is False
        assert card["raster_sha256"] == current["raster_sha256"]
    elif current["run_card"] == "run-card-S28-VFCD.json":
        card = _json("docs/run-card-S28-VFCD.json")
        assert card["holdout"]["evidence_class"] == "HOLDOUT-DTI"
        assert card["holdout"]["evaluator_version"] == "gems57-pooled-hide-v2"
        assert card["organizer_confirmed_score"] is None
        assert card["correlation_overlap_vs_registry"]["surface_pass"] is True
        assert card["correlation_overlap_vs_registry"]["dots_competitive_pass"] is True
        assert card["raster_sha256"] == current["raster_sha256"]
        assert card["verdict"]["promote"] is False and card["verdict"]["OK_TO_SUBMIT"] == "NO"
        for name in ("canaries.json", "surface-checks.json", "final-dot-checks.json",
                     "e3/holdout.json", "diagnostics.json", "run-card.json"):
            assert (DOCS / "s28-vfcd" / name).is_file(), name
    assert current["ok_to_download"] is True
    assert current["ok_to_submit"] is False
    review = (DOCS / "REVIEW-ACTIVE-522615DD-20261025.md").read_text(encoding="utf-8")
    assert "not an output of this review" in review
    assert "ORGANIZER-CONFIRMED: null" in review
    assert "no TIFF" in review
