#!/usr/bin/env python3
"""Render the S28-PUCC CANDIDATE_READY front door (2026-10-31).

This is the newest overlay in the legacy portal pipeline
(`scripts/render_olc91_portal.py::render` calls it last). It runs after every
historical renderer so the active verdict can never be silently reverted:

  docs/executive-summary.html   - full S28-PUCC executive summary (download first)
  docs/submission-guide.html    - paste-ready submission guide
  docs/current-review.json      - machine-readable active pointer
  index.html                    - root landing with the one-click TIF
  docs/index.html               - current-notice swap on the historical portal

The inputs are frozen committed artifacts under docs/s28-pucc/ and
docs/downloads/ (no network, no competition data). Deterministic and
idempotent: running it twice produces identical bytes.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

CANDIDATE_TIF = "downloads/gems91-s28-pucc-ee2-37654dots-20261031T013552Z-cb42d2ce-zeros.tif"
CANDIDATE_ZIP = "downloads/gems91-s28-pucc-ee2-37654dots-20261031T013552Z-cb42d2ce-zeros.zip"
CANDIDATE_NAME = "gems91-s28-pucc-ee2-37654dots-20261031T013552Z-cb42d2ce-zeros"
CANDIDATE_SHA = "8d75b2d1c6891bee275cf3e0aa6065568e5cabe7626528c068b09f81562f656f"
NOTE = "S28 PUCC SGMC-off+vent+OSDR+lidar corridor consensus, B2 flank, CELF 37654d; see run-card"

NOTICE = (
    '<div class="note" role="status"><strong>ACTIVE REVIEW · 2026-10-31: S28-PUCC candidate READY · '
    'OK TO DOWNLOAD: YES · OK TO SUBMIT: YES (automated gates pass; 0 weekly slots spent).</strong> '
    f'New unique TIF <code>{CANDIDATE_NAME}.tif</code> — '
    'HOLDOUT-DTI 0.12797 [0.10998, 0.14618] (gems57-pooled-hide-v2); '
    'MODEL_PROJECTION_NOT_A_SCORE 0.222 [0.163, 0.280] (LOW). '
    '<a href="executive-summary.html">Executive summary, download button, and nine-site table</a> · '
    '<a href="submission-guide.html">Submission guide</a> · '
    '<a href="s28-pucc/run-card.json">Run card</a> · '
    '<a href="review-20261030/executive-summary.html">2026-10-30 no-candidate review (history)</a> · '
    '<a href="review-20261030/run-card.json">its run card</a>. '
    'Superseded verdicts (S25-TLF revoke, earlier research downloads) '
    'remain below as history — their “OK TO SUBMIT: NO” labels apply to those artifacts only.</div>'
)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _swap_notice(page: str) -> str:
    """Replace the first current-notice block in the historical portal."""
    start = page.find('<div class="note" role="status">')
    if start < 0:
        raise ValueError("current-notice wrapper missing in portal HTML")
    end = page.find("</div>", start)
    if end < 0:
        raise ValueError("current-notice closing tag missing")
    return page[:start] + NOTICE + page[end + len("</div>"):]


def render(root: Path = ROOT) -> None:
    docs = root / "docs"

    # 1. Full executive summary (canonical user page, links relative to docs/).
    (docs / "executive-summary.html").write_text(_read("docs/s28-pucc/page-executive-summary.html"), encoding="utf-8")

    # 2. Submission guide.
    (docs / "submission-guide.html").write_text(_read("docs/s28-pucc/page-submission-guide.html"), encoding="utf-8")

    # 3. Root landing with the one-click TIF.
    (root / "index.html").write_text(_read("docs/s28-pucc/page-landing.html"), encoding="utf-8")

    # 4. Machine-readable active pointer.
    pointer = {
        "schema": "gems91.current-review-pointer.v1",
        "review_id": "s28-pucc-20261031",
        "review_date_utc": "2026-10-31",
        "branch": "arena/db03647e-gemsdoe91",
        "status": "CANDIDATE_READY",
        "candidate_generated": True,
        "candidate_file": CANDIDATE_TIF,
        "candidate_sha256": CANDIDATE_SHA,
        "candidate_submission_name": CANDIDATE_NAME,
        "ok_to_download_new_candidate": True,
        "ok_to_submit": True,
        "ok_to_submit_conditions": (
            "All automated gates pass (format all-finite [0,1], catalogue mask, leakage canary, "
            "uniqueness vs nine sites and 78 registry rasters, budget 3/3 experiments, 0 weekly slots "
            "spent). Upload remains a separate manual selector decision. IR-S28-ANTILIVE-01 caveat "
            "applies: do not claim the file beats 0.2778."
        ),
        "holdout_dti": {
            "evidence_class": "HOLDOUT-DTI",
            "value": 0.12797373836871026,
            "ci95": [0.10997924835638555, 0.14618368646331334],
            "evaluator_version": "gems57-pooled-hide-v2",
            "withheld_positive_count": 60988,
        },
        "leaderboard_score_estimate": {
            "evidence_class": "MODEL_PROJECTION_NOT_A_SCORE",
            "value": 0.22155,
            "ci95": [0.1633, 0.2798],
            "reliability": "LOW",
            "method": ("cohort bracket over owner-reported non-family matched-budget submissions; "
                       "in-hull regression retained as audit only"),
        },
        "organizer_confirmed": {
            "evidence_class": "ORGANIZER-CONFIRMED",
            "value": None,
            "submission_receipt": None,
        },
        "review": "s28-pucc/run-card.json",
        "executive_summary": "executive-summary.html",
        "submission_guide": "submission-guide.html",
        "run_card": "s28-pucc/run-card.json",
        "score_estimate": "s28-pucc/score-estimate.json",
        "historical_artifact_pointer": {
            "path": "current-run.json",
            "meaning": ("Legacy pointer to run-card-522615dd.json-era artifacts (currently "
                        "run-card-S22-OMTJ.json). Superseded by this pointer; retained for audit "
                        "continuity."),
        },
    }
    (docs / "current-review.json").write_text(
        json.dumps(pointer, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")

    # 5. Current-notice swap on the historical mega-portal (history stays below).
    portal = docs / "index.html"
    portal.write_text(_swap_notice(portal.read_text(encoding="utf-8")), encoding="utf-8")


if __name__ == "__main__":
    render()
