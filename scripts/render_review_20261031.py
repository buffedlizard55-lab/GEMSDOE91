#!/usr/bin/env python3
"""Render the active 2026-10-31 S30-VCSE review overlay.

Runs after every legacy renderer (including `render_review_20261030`) inside
`scripts.render_olc91_portal.render()`.  Consumes only committed review
evidence and fails closed: if the run card, receipt, verdict, or uniqueness
gates disagree, nothing is published.  The renderer never grants permission to
submit and never uploads.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_CARD = ROOT / "docs/s30-vcse/run-card.json"
RECEIPT = ROOT / ("docs/downloads/gems91-s30-vcse-e3-44090dots-"
                  "20261031T021738Z-d23f1602-zeros.json")
HIST_CARD = ROOT / "docs/review-20261030/run-card.json"
EXPECT_NAME = "gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros"
EXPECT_SHA = "a5993d3a520aa280ce70744ad2dd772090d54cd248e1d6fdc9d1950fdc8e83ae"
MY_NOTICE_MARKER = "<strong>CURRENT REVIEW · 2026-10-31:"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_inputs(root: Path = ROOT) -> tuple[dict, dict]:
    card = _read_json(RUN_CARD)
    receipt = _read_json(RECEIPT)
    if card.get("verdict") != "negative":
        raise ValueError("S30 run card must remain negative until the holdout gate passes")
    if card.get("submission", {}).get("name") != EXPECT_NAME:
        raise ValueError("Submission name drift")
    if card.get("raster_sha256") != EXPECT_SHA or receipt.get("sha256") != EXPECT_SHA:
        raise ValueError("Candidate raster digest drift")
    if not receipt.get("validator", {}).get("all_checks_passed"):
        raise ValueError("Validator receipt is not a pass")
    note = card.get("submission", {}).get("note", "")
    if not (0 < len(note) <= 140):
        raise ValueError("Submission note must fit the 140-char limit")
    hg = card.get("holdout_gate", {})
    if hg.get("pass") is not False or card.get("g5_blind_sgmc_pass") is not True:
        raise ValueError("Verdict inputs drifted; keep G5 pass + holdout fail visible")
    uniq = card.get("registry_uniqueness", {})
    max_ov = float(uniq.get("dot_max_overlap_within_3px", 1.0))
    if max_ov > 0.70:
        raise ValueError("Duplicate stop: dot overlap above 70%")
    return card, receipt


def _notice() -> str:
    return (
        '<div class="note" role="status"><strong>CURRENT REVIEW · 2026-10-31: '
        'NEW UNIQUE TIF GENERATED · OK-TO-DOWNLOAD: YES · OK-TO-SUBMIT: NO — HOLD '
        '(supersedes the 2026-10-30 review below).</strong> '
        'S30-VCSE vent-concordance lane: 44,090 dots, validator 13/13, values in [0, 1], '
        'max 3-px overlap 13.54% vs any listed site/registry raster (unique), surface |&rho;| max 0.0286. '
        'HOLDOUT-DTI 0.052966 [0.046011, 0.060650] (gems57-pooled-hide-v2, 60,988 withheld) does not '
        'beat the registered best 0.159482 &rarr; preregistered verdict <strong>negative</strong>, '
        '0 weekly slots spent. '
        '<a href="downloads/gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros.tif">Download TIF</a> · '
        '<a href="downloads/gems91-s30-vcse-e3-44090dots-20261031T021738Z-d23f1602-zeros.zip">ZIP</a> · '
        '<a href="executive-summary.md">Executive summary</a> · '
        '<a href="s30-vcse/run-card.json">Run card</a> · '
        '<a href="s30-vcse/hypotheses.md">Ranked hypotheses</a>.</div>'
    )


def _insert_notice(page: str) -> str:
    if MY_NOTICE_MARKER in page:
        return page
    marker = '<strong>ACTIVE REVIEW · 2026-10-30:'
    position = page.find(marker)
    if position < 0:
        raise ValueError("Could not locate the 2026-10-30 banner to precede")
    start = page.rfind('<div class="note" role="status">', 0, position)
    if start < 0:
        raise ValueError("2026-10-30 banner wrapper missing")
    return page[:start] + _notice() + page[start:]


def guide_html(card: dict, hist_guide_html: str) -> str:
    note = card["submission"]["note"]
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="GEMSDOE91 submission guide: S30-VCSE candidate, verdicts and fail-closed steps.">
<title>GEMSDOE91 · Current submission guide</title><style>{_STYLE}</style></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="nav"><a class="brand" href="index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a>
<nav aria-label="Guide navigation"><a href="index.html">Portal home</a><a href="executive-summary.md">Executive summary</a><a href="s30-vcse/run-card.json">Run card</a></nav></header>
<main id="main" data-submission-ready="false">
<section class="hero"><div><span class="eyebrow">Current status · 2026-10-31 · S30-VCSE</span>
<h1>Download yes.<br>Submitting this week: no.</h1>
<p class="lead">A new, unique GeoTIFF candidate was generated and passes every technical gate.
The preregistered holdout gate was not cleared, so the standing rule holds the weekly
submission slot. This page is not an approval to upload.</p>
<p><span class="badge">OK-TO-DOWNLOAD: YES</span> <span class="badge">OK-TO-SUBMIT: NO — HOLD</span></p>
<p><a class="button" href="downloads/{EXPECT_NAME}.tif">Download the TIF</a>
<a class="button secondary" href="downloads/{EXPECT_NAME}.zip">Single-TIFF ZIP</a>
<a class="button secondary" href="executive-summary.md">Executive summary</a></p></div>
<aside class="dark"><h2>Candidate at a glance</h2>
<div class="stat"><span>Dots</span><strong>44,090</strong></div>
<div class="stat"><span>Validator</span><strong>13 / 13 PASS</strong></div>
<div class="stat"><span>Max 3-px overlap</span><strong>13.54% &le; 70%</strong></div>
<div class="stat"><span>HOLDOUT-DTI</span><strong>0.052966 [0.046011, 0.060650]</strong></div>
<div class="stat"><span>Organizer receipt</span><strong>NONE (0 slots)</strong></div>
<p class="small">HOLDOUT-DTI = gems57-pooled-hide-v2, 60,988 withheld positives, 95% CI. Not a leaderboard score.</p></aside></section>

<section class="section"><h2>Identity — use exactly these strings if a future selector ever clears a slot</h2>
<div class="card"><p class="mono">submission name: {EXPECT_NAME}<br>
note ({len(note)}/140 chars): {note}<br>
sha256: {EXPECT_SHA}</p></div></section>

<section class="section"><h2>Why HOLD</h2>
<p>The standing protocol promotes a candidate to a weekly submission slot only if its pooled
HOLDOUT-DTI beats the registered holdout best <strong>0.159482</strong> (S27-OSDR E2, same instrument).
The candidate measures <strong>0.052966 [0.046011, 0.060650]</strong> — below the bar (and below the
matched random-NMS control 0.070228–0.080091). The blind SGMC off-catalogue control did pass
(0.113455 vs parent R0 0.088516), and the evidence is preserved for a future cycle.
Do not spend a weekly submission slot on this candidate.</p></section>

<section class="section"><h2>Future submission checklist — all gates are required</h2>
<ol class="steps">
<li>Selector decision first: only a candidate that beats the registered holdout best is eligible.</li>
<li>Download the exact TIF above and verify its SHA-256 against the run card.</li>
<li>Upload manually at the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">official DrivenData submissions page</a> with the exact name and note strings above.</li>
<li>File the submission receipt into <code>ledger/submissions.csv</code>; only that receipt can support ORGANIZER-CONFIRMED.</li>
</ol></section>

<section class="section"><h2>Guide archive — 2026-10-30 fail-closed guide (superseded; retained as historical evidence)</h2>
<details><summary>Open the 2026-10-30 guide</summary><div class="card">{hist_guide_html}</div></details>
</section>
</main><footer class="footer"><span>Maximize P(Win) · Own the Outcome</span>
<span><a href="index.html">Portal home</a> · No automated uploads or stored credentials.</span></footer>
</div></body></html>
'''


_STYLE = ""  # populated at import time to keep the template above readable

def _load_style() -> None:
    global _STYLE
    from scripts.render_review_20261030 import STYLE
    _STYLE = STYLE


def render(root: Path = ROOT) -> None:
    _load_style()
    from scripts.render_review_20261030 import standalone_guide as historical_guide
    card, receipt = validate_inputs(root)
    docs = root / "docs"

    hist_card = _read_json(HIST_CARD)
    hist_guide = historical_guide(hist_card)
    guide = guide_html(card, hist_guide)
    (docs / "submission-guide.html").write_text(guide, encoding="utf-8")

    for name in ("index.html", "executive-summary.html"):
        path = docs / name
        if not path.is_file():
            raise FileNotFoundError(path)
        page = path.read_text(encoding="utf-8")
        path.write_text(_insert_notice(page), encoding="utf-8")

    pointer = {
        "schema": "gems91.current-review-pointer.v1",
        "review_id": "GEMSDOE91-REVIEW-20261031",
        "review_date_utc": "2026-10-31",
        "branch": "arena/681fc5eb-gemsdoe91",
        "status": "COMPLETE",
        "candidate_generated": True,
        "ok_to_download_new_candidate": True,
        "ok_to_submit": False,
        "holdout_dti": {"value": 0.052966, "ci95": [0.046011, 0.060650],
                        "evaluator_version": "gems57-pooled-hide-v2",
                        "withheld_positive_count": 60988},
        "organizer_confirmed": None,
        "leaderboard_score_estimate": None,
        "verdict": "negative (holdout gate not cleared; hold the weekly slot)",
        "candidate": {"name": EXPECT_NAME,
                      "tif": f"downloads/{EXPECT_NAME}.tif", "sha256": EXPECT_SHA},
        "review": "executive-summary.md",
        "run_card": "s30-vcse/run-card.json",
        "historical_reviews": ["review-20261030/REVIEW.md",
                               "review-4239f6e5/REVIEW.md"],
    }
    (docs / "current-review.json").write_text(
        json.dumps(pointer, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")

    root_html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=docs/index.html">'
        '<meta name="description" content="Current GEMSDOE91 review: unique TIF generated; OK to download; submission on hold.">'
        '<title>GEMSDOE91 · Active review and verdict</title></head><body><main>'
        '<h1>GEMSDOE91 · Active review · 2026-10-31</h1>'
        '<p><strong>NEW UNIQUE TIF GENERATED. OK TO DOWNLOAD: YES. OK TO SUBMIT: NO — HOLD.</strong> '
        'S30-VCSE candidate: 44,090 dots, validator 13/13, unique vs every listed site '
        '(max 3-px overlap 13.54%). HOLDOUT-DTI 0.052966 &lt; registered best 0.159482 &rarr; '
        '0 weekly slots spent. (Supersedes the 2026-10-30 review: NO NEW TIFF · OK TO SUBMIT: NO. '
        'Historical files remain OK TO DOWNLOAD for research/inspection only; OK TO SUBMIT: NO.)</p>'
        '<p><a href="docs/index.html">Open the portal and active status</a> · '
        f'<a href="docs/downloads/{EXPECT_NAME}.tif">Download the candidate TIF</a> · '
        '<a href="docs/executive-summary.md">Executive summary</a> · '
        '<a href="docs/s30-vcse/run-card.json">Run card</a> · '
        '<a href="docs/review-20261030/executive-summary.html">2026-10-30 review (historical)</a></p>'
        '</main></body></html>\n')
    (root / "index.html").write_text(root_html, encoding="utf-8")


if __name__ == "__main__":
    render()
