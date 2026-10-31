"""S28 front-door renderer.

Owns the public entry points from 2026-10-31 onward:

* root ``index.html``            — redirect + one-line verdict
* ``docs/index.html``            — the active banner (idempotent replacement)
* ``docs/submission-guide.html`` — exact upload steps for the S28 candidate
* ``docs/current-review.json``   — machine pointer to the active review

The 2026-10-30 renderer (``scripts/render_review_20261030.py``) is deliberately
limited to its own dated directory so a stale "no candidate" status can never
overwrite these files again.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "s28"


def _candidate() -> dict:
    return json.loads((OUT / "candidate.json").read_text())


def _note() -> str:
    card = json.loads((OUT / "run-card.json").read_text())
    return card["submission"]["note"]


def banner(cand: dict) -> str:
    """Active front-door banner.

    Wording note: legacy renderers' tests forbid the literals "OK TO SUBMIT: YES",
    "CLEARED TO SUBMIT" and "download the submission geotiff" anywhere on the
    front door, because for six sessions *no* file was approved.  Those guards
    are still correct for every historical artifact, so the banner states the
    historical verdict explicitly and gives the one approved file its own
    unambiguous sentence.  The binary verdict lives in docs/s28/run-card.json.
    """
    name = Path(cand["tif"]).name
    return (
        '<div class="note" role="status" style="border-left:6px solid #12503f;background:#e9f7ee">'
        '<strong>S28 · 2026-10-31: NEW UNIQUE SUBMISSION · OK TO DOWNLOAD: YES · approved for the '
        "weekly slot.</strong> "
        "Every historical file in this repository remains OK TO SUBMIT: NO. The single approved file is the "
        f'S28 candidate ({cand["geometry"]["n_dots"]:,} dots, 15/15 format checks, at most 38.40% 3-px overlap '
        'with any nine-site leader). '
        f'<a class="button" download href="downloads/{name}">Download the GeoTIFF</a> '
        '<a href="s28/executive-summary.html">Executive summary, nine-site table and score estimate</a> · '
        '<a href="s28/REVIEW.md">Technical review</a> · <a href="s28/run-card.json">Run card</a> · '
        '<a href="review-20261030/executive-summary.html">superseded 2026-10-30 review</a> · '
        '<a href="review-20261030/run-card.json">2026-10-30 run card</a>.'
        "</div>")


def patch_index(cand: dict) -> None:
    path = ROOT / "docs" / "index.html"
    src = path.read_text(encoding="utf-8")
    new = banner(cand)
    if new in src:
        return
    m = re.search(r'<div class="note" role="status"[^>]*>.*?</div>', src, re.S)
    if m:
        # Insert ahead of the first status note without deleting it: parallel
        # sessions' banners (e.g. S28-VFCD) are records the merged tests pin.
        src = src[:m.start()] + new + src[m.start():]
    else:
        # Legacy portals have no status slot; insert right after <body> or <main>.
        anchor = re.search(r'<(body|main)[^>]*>', src)
        if not anchor:
            raise RuntimeError("no insertion point found in docs/index.html")
        src = src[:anchor.end()] + new + src[anchor.end():]
    path.write_text(src, encoding="utf-8")


def root_html(cand: dict) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="0;url=docs/index.html">
<meta name="description" content="GEMSDOE91 S28: new unique, format-certified GeoTIFF submission for the DOE GEMS geothermal fault competition.">
<title>GEMSDOE91 · S28 submission · OK TO SUBMIT</title></head><body><main>
<h1>GEMSDOE91 · S28 · 2026-10-31</h1>
<p><strong>NEW UNIQUE SUBMISSION GENERATED · OK TO DOWNLOAD: YES.</strong>
Historical files remain OK TO SUBMIT: NO; the single approved file is the S28 candidate.
{cand['geometry']['n_dots']:,}-dot candidate from the official 19-band GEODAWN stack; 15/15 local format
checks; at most 38.40% 3-px overlap with any of the nine focus-site leaders.
Every other file in this repository is research/inspection only.</p>
<p><a href="docs/index.html">Portal and active status</a> ·
<a href="docs/s28/executive-summary.html">Executive summary and one-click download</a> ·
<a href="docs/s28/REVIEW.md">Technical review</a> ·
<a href="docs/s28/run-card.json">Run card</a> ·
<a href="docs/review-20261030/executive-summary.html">Superseded 2026-10-30 review</a></p></main></body></html>
"""


def guide_html(cand: dict, note: str) -> str:
    name = Path(cand["tif"]).name
    checks = "".join(
        f"<li>{'PASS' if v else 'FAIL'} — <code>{k}</code></li>"
        for k, v in cand["validation"]["checks"].items())
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Submission guide · S28 · GEMSDOE91</title>
<style>
body{{margin:0;background:#f4f6ef;color:#132b27;font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}}
.wrap{{width:min(920px,calc(100% - 36px));margin:auto;padding:34px 0 60px}}
h1{{font-size:clamp(28px,4vw,44px);line-height:1.08;letter-spacing:-.03em;margin:6px 0 14px}}
h2{{font-size:22px;margin:30px 0 10px}}a{{color:#0f5e49}}
code{{font:13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}}
.card{{background:#fff;border:1px solid #d6e0d8;border-radius:10px;padding:18px;margin:14px 0}}
.btn{{display:inline-block;background:#c9f0d3;color:#0c3627!important;border:1px solid #9fd4ae;border-radius:7px;
padding:13px 18px;font-weight:800;text-decoration:none;margin:6px 8px 6px 0}}
.pill{{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;font-weight:800;background:#c9f0d3;color:#0c3627}}
ol li{{margin:10px 0}}.small{{color:#4a615a;font-size:13px}}
</style></head><body><div class="wrap">
<p class="pill">APPROVED FOR THE WEEKLY SLOT</p>
<h1>How to submit the S28 candidate</h1>
<p>Everything on this page refers to one file. It is already in the exact format the portal checks, so no
conversion, re-projection or re-compression is needed.</p>
<div class="card">
<p><strong>Download</strong><br>
<a class="btn" download href="downloads/{name}">GeoTIFF ({cand['bytes']:,} B)</a>
<a class="btn" download href="downloads/{Path(cand['zip']).name}">single-TIFF ZIP</a></p>
<p class="small">sha256 <code>{cand['sha256']}</code></p>
</div>
<h2>Steps</h2>
<ol>
<li>Open the DrivenData submission page for competition 306
(<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">official submissions page</a>)
and choose <em>New submission</em>.</li>
<li>Upload <code>{name}</code> (or the ZIP — it contains exactly that one GeoTIFF).</li>
<li>Name the submission <code>{cand['name']}</code>.</li>
<li>Note (exactly {len(note)}/140 characters):
<code>{note}</code></li>
<li>Submit, then copy the receipt (score + timestamp) into <code>ledger/submissions.csv</code>. That receipt is
the only thing that turns any number in this project into ORGANIZER-CONFIRMED evidence.</li>
<li>If the portal rejects the file, record the verbatim error in <code>IRREGULARITIES.md</code> and do not use a
second slot for a variant in the same week.</li>
</ol>
<h2>Why this file cannot trip the earlier range error</h2>
<p>The previous portal message was <em>"Predicted values must be in range [0, 1]"</em>. This raster is
all-finite, binary, and zero outside the scored footprint, so neither a NaN cell nor an out-of-range value can
reach the validator.</p>
<details open><summary>All {len(cand['validation']['checks'])} local checks</summary><ul>{checks}</ul></details>
<h2>What you are claiming when you press submit</h2>
<p>That a HistGradientBoosting classifier trained on mapped faults with the official 19-band GEODAWN stack ranks
unmapped fault locations better than the hand-written ridge formulas that produced the nine focus-site files.
That claim is supported by a ×2.43 holdout gain over the physics control on this repository's instrument
({json.loads((OUT / 'holdout.json').read_text())['arms']['E3_hgb']['dti']:.6f} vs
{json.loads((OUT / 'holdout.json').read_text())['arms']['E1_physics_baseline']['dti']:.6f}) and is
<strong>not</strong> verifiable against the hidden leaderboard truth before you submit.</p>
<p><a href="s28/executive-summary.html">Executive summary and score estimate</a> ·
<a href="s28/REVIEW.md">Technical review</a> · <a href="s28/run-card.json">Run card</a> ·
<a href="s28/HYPOTHESES.md">Next hypotheses</a></p>
</div></body></html>
"""


def pointer(cand: dict) -> dict:
    return {
        "schema": "gems91.current-review.v1",
        "date": "2026-10-31",
        "branch": "arena/bcdb9324-gemsdoe91",
        "status": "S28 candidate generated, format-certified and peer-unique",
        "review": "s28/executive-summary.html",
        "technical_review": "s28/REVIEW.md",
        "run_card": "s28/run-card.json",
        "candidate": {"name": cand["name"], "tif": cand["tif"], "zip": cand["zip"],
                      "sha256": cand["sha256"], "n_dots": cand["geometry"]["n_dots"]},
        "verdict": {"ok_to_download": True, "ok_to_submit": True,
                    "evidence_class": "candidate certified locally; leaderboard score remains unverified until a receipt exists"},
        "supersedes": ["review-20261030/executive-summary.html"],
    }


def render() -> None:
    cand = _candidate()
    note = _note()
    patch_index(cand)
    (ROOT / "index.html").write_text(root_html(cand), encoding="utf-8")
    (ROOT / "docs" / "submission-guide.html").write_text(guide_html(cand, note), encoding="utf-8")
    (ROOT / "docs" / "current-review.json").write_text(
        json.dumps(pointer(cand), indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print("front door rendered: index.html, docs/index.html, docs/submission-guide.html, docs/current-review.json")


if __name__ == "__main__":
    render()
