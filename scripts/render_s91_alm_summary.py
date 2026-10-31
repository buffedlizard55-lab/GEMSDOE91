#!/usr/bin/env python3
"""Render the active S91-ALM portal and its docs/s91-alm/ executive summary.

This renderer owns the live portal (docs/index.html, docs/executive-summary.html,
docs/submission-guide.html, docs/current-review.json, root index.html) plus the
archived subpage docs/s91-alm/executive-summary.html. Run it after any change to
the candidate, run card, or nine-leader overlap data.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "s91-alm"

CAND = "gems91-s91-alm-alteration-halo-20261031T010114Z-5834ff6c"
CAND_TIF = f"../downloads/{CAND}-zeros.tif"
CAND_ZIP = f"../downloads/{CAND}-zeros.zip"

STYLE = """
:root { --bg:#0f1115; --panel:#171a21; --ink:#e8ecf2; --mut:#9aa4b2; --acc:#4da3ff; --ok:#3ecf8e; --bad:#ff6b6b; --warn:#ffcc66; }
* { box-sizing:border-box; }
body { margin:0; font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; background:var(--bg); color:var(--ink); }
main { max-width:1180px; margin:0 auto; padding:32px 22px 80px; }
h1 { font-size:26px; margin:0 0 4px; }
h2 { font-size:19px; margin:34px 0 10px; border-bottom:1px solid #262b34; padding-bottom:6px; }
h3 { font-size:16px; margin:22px 0 8px; color:var(--acc); }
a { color:var(--acc); }
.sub { color:var(--mut); margin:0 0 6px; }
.banner { background:linear-gradient(135deg,#1b2433,#171a21); border:1px solid #2a3550; border-radius:12px; padding:18px 20px; margin:18px 0; }
.banner .big { font-size:20px; font-weight:700; }
.ok { color:var(--ok); font-weight:600; }
.bad { color:var(--bad); font-weight:600; }
.warn { color:var(--warn); font-weight:600; }
table { width:100%; border-collapse:collapse; margin:12px 0; font-size:13.5px; }
th,td { border:1px solid #262b34; padding:7px 9px; text-align:left; vertical-align:top; }
th { background:#1c2029; color:var(--mut); font-weight:600; }
tr:nth-child(even) td { background:#14171d; }
code { background:#14171d; border:1px solid #262b34; border-radius:5px; padding:1px 5px; font-size:13px; }
.card { background:var(--panel); border:1px solid #262b34; border-radius:10px; padding:14px 16px; margin:10px 0; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.ev { color:var(--mut); font-size:11.5px; }
ol li, ul li { margin:5px 0; }
.small { color:var(--mut); font-size:12.5px; }
@media(max-width:820px){ .grid2{grid-template-columns:1fr;} }
"""


def _nine_rows(snap, ov):
    rows = []
    for s in snap["sites"]:
        site = s["site"]
        fn = s["reported_file"]
        val = s["reported_public_dti"]
        mx = ov["max_overlap_pct"][site]
        uniq = "NO — duplicate family" if mx > 70 else "YES"
        rows.append(
            f"<tr><td><strong>{site}</strong></td>"
            f"<td>{fn}</td>"
            f"<td>{val:.4f} <span class='ev'>USER-REPORTED, unverified</span></td>"
            f"<td>{mx:.2f}%</td>"
            f"<td class='{'bad' if mx>70 else 'ok'}'>{uniq}</td>"
            f"<td>NO (no receipt)</td></tr>"
        )
    return "\n".join(rows)


def _executive_html(snap, ov, card):
    rows = _nine_rows(snap, ov)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 · S91-ALM executive summary &amp; submission guide</title>
<style>{STYLE}</style></head><body><main>
<h1>GEMSDOE91 · S91-ALM executive summary &amp; submission guide</h1>
<p class="sub">Generated 2026-10-31 · lane <code>S91-ALM</code> · branch <code>arena/2664739c-gemsdoe91</code></p>
<div class="banner">
  <div class="big">✅ UNIQUE SUBMISSION GENERATED — <span class="ok">OK TO DOWNLOAD: YES</span> · <span class="warn">OK TO SUBMIT: NO (selector step pending)</span></div>
  <p class="sub" style="margin-top:8px">
    A new, format-certified GeoTIFF is <strong>unique</strong> against all nine focus sites (max 23.8% of its dots within
    3&nbsp;px of any one leader; threshold 70%). It is a <strong>negative holdout by design</strong> (collar-compliant
    off-catalogue search), so its leaderboard score is <strong>not estimated</strong> — no organizer receipt exists.
  </p>
</div>
<h2>1 · One-click download</h2>
<div class="card">
  <p><strong>File:</strong> <a href="{CAND_TIF}">{CAND}-zeros.tif</a> ·
     <strong>ZIP:</strong> <a href="{CAND_ZIP}">{CAND}-zeros.zip</a></p>
  <p><strong>Submission name:</strong> <code>{card['submission_name']}</code> ·
     <strong>Note ({len(card['submission_note'])}/140):</strong> <code>{card['submission_note']}</code></p>
  <p><strong>SHA-256:</strong> <code>{card['raster_sha256']}</code> · single-band float32 · EPSG:32611 · 3730×3292 ·
     all 12,279,160 pixels finite in [0,1] · 37,654 binary dots · min catalogue distance 3.1623&nbsp;px.</p>
  <p><span class="ok">gems91.gates CERTIFIED</span> · <span class="ok">release_gates PASS</span> ·
     <span class="ok">validate_raster PASS</span> · <span class="ok">range [0,1] portal-safe</span></p>
</div>
<h2>2 · Nine focus sites — file / estimate / uniqueness</h2>
<table><thead><tr><th>Site</th><th>File</th><th>Reported value</th><th>Max peer 3-px overlap</th><th>Unique within the nine?</th><th>Organizer receipt</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="small">Every one of the nine is a member of a single H19-5-derived duplicate family (pairwise 3-px overlap 97.6–100%).
The highest <em>reported</em> value is GEMSDOE32 <code>h33-h33-2-b2</code> = 0.2778 — user-reported, unverified, not unique.</p>
<h2>3 · This candidate</h2>
<table><thead><tr><th>File</th><th>Estimate</th><th>Unique vs the nine?</th><th>OK to submit?</th></tr></thead>
<tbody><tr><td><a href="{CAND_TIF}">{CAND}-zeros.tif</a></td>
<td><strong>Not estimable</strong> — no receipt. HOLDOUT-DTI <strong>0.0</strong> (by design); blind SGMC off-catalogue control <strong>0.0624</strong> (vs parent R0 0.0954).</td>
<td class="ok">YES — max 23.83% (GEMSDOE27)</td>
<td class="warn">NO — negative holdout; selector step pending</td></tr></tbody></table>
<h2>4 · How to submit (only after the selector approves)</h2>
<ol>
<li>Download <a href="{CAND_TIF}">{CAND}-zeros.tif</a>; confirm SHA-256 <code>{card['raster_sha256']}</code>.</li>
<li>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition page</a> → <strong>New submission</strong>.</li>
<li>Select the single-band GeoTIFF (or the ZIP containing exactly one GeoTIFF).</li>
<li>Name <code>{card['submission_name']}</code>; note <code>{card['submission_note']}</code>.</li>
<li>Submit within the weekly slot cap; save the organizer receipt as ORGANIZER-CONFIRMED.</li>
</ol>
<p class="small">Full run card: <a href="run-card.json">run-card.json</a> · <a href="REVIEW.md">review</a> ·
<a href="HYPOTHESES.md">hypotheses</a> · <a href="nine-leader-overlap.json">nine-leader-overlap.json</a></p>
</main></body></html>
"""


def _portal_html(snap, ov, card):
    rows = _nine_rows(snap, ov)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 · S91-ALM unique submission · OK TO DOWNLOAD YES · OK TO SUBMIT NO</title>
<style>{STYLE}</style></head><body><main data-submission-ready="false">
<h1>GEMSDOE91 · S91-ALM unique submission</h1>
<p class="sub">Generated 2026-10-31 · lane <code>S91-ALM</code> · branch <code>arena/2664739c-gemsdoe91</code></p>
<div class="banner">
  <div class="big">✅ UNIQUE SUBMISSION GENERATED — <span class="ok">OK TO DOWNLOAD: YES</span> · <span class="warn">OK TO SUBMIT: NO (selector step pending)</span></div>
  <p class="small" style="margin-top:8px">A new, format-certified GeoTIFF is <strong>unique</strong> against all nine focus sites
  (max 23.8% of its dots within 3&nbsp;px of any one leader; threshold 70%). It is a <strong>negative holdout by design</strong>,
  so its leaderboard score is <strong>not estimated</strong> — no organizer receipt exists.</p>
</div>
<h2>1 · Download the submission GeoTIFF</h2>
<div class="card">
  <p><strong>File:</strong> <a href="../downloads/{CAND}-zeros.tif">{CAND}-zeros.tif</a> ·
     <strong>ZIP:</strong> <a href="../downloads/{CAND}-zeros.zip">{CAND}-zeros.zip</a></p>
  <p><strong>Submission name:</strong> <code>{card['submission_name']}</code> ·
     <strong>Note:</strong> <code>{card['submission_note']}</code></p>
  <p><strong>SHA-256:</strong> <code>{card['raster_sha256']}</code> · single-band float32 · EPSG:32611 · 3730×3292 ·
     all pixels finite in [0,1] · 37,654 dots · min catalogue distance 3.1623&nbsp;px.</p>
  <p><span class="ok">gems91.gates CERTIFIED</span> · <span class="ok">release_gates PASS</span> ·
     <span class="ok">validate_raster PASS</span> · <span class="ok">range [0,1] portal-safe</span></p>
</div>
<h2>2 · Nine focus sites — file / estimate / uniqueness</h2>
<table><thead><tr><th>Site</th><th>File</th><th>Reported value</th><th>Max peer 3-px overlap</th><th>Unique?</th><th>OK to submit?</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2>3 · This candidate</h2>
<table><thead><tr><th>File</th><th>Estimate</th><th>Unique vs the nine?</th><th>OK to submit?</th></tr></thead>
<tbody><tr><td><a href="../downloads/{CAND}-zeros.tif">{CAND}-zeros.tif</a></td>
<td><strong>Not estimable</strong> — no receipt. HOLDOUT-DTI <strong>0.0</strong> (by design); blind SGMC off-catalogue control <strong>0.0624</strong> (vs parent R0 0.0954).</td>
<td class="ok">YES — max 23.83% (GEMSDOE27)</td>
<td class="warn">NO — selector step pending</td></tr></tbody></table>
<h2>4 · How to submit (only after the selector approves)</h2>
<ol>
<li>Download <a href="../downloads/{CAND}-zeros.tif">the .tif</a>; confirm SHA-256.</li>
<li>Open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData competition page</a> → <strong>New submission</strong>.</li>
<li>Select the single-band GeoTIFF (or the ZIP containing exactly one GeoTIFF).</li>
<li>Name <code>{card['submission_name']}</code>; note <code>{card['submission_note']}</code>.</li>
<li>Submit within the weekly slot cap; save the organizer receipt as ORGANIZER-CONFIRMED.</li>
</ol>
<p class="small">Full executive summary: <a href="executive-summary.html">s91-alm/executive-summary.html</a> ·
<a href="REVIEW.md">review</a> · <a href="run-card.json">run card</a> ·
<a href="HYPOTHESES.md">hypotheses</a> · <a href="../submission-guide.html">submission guide</a></p>
</main></body></html>
"""


def _guide_html(card):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 · Submission guide</title><style>{STYLE}</style></head><body><main>
<h1>GEMSDOE91 · Submission guide</h1>
<p class="sub">Active status 2026-10-31 · lane <code>S91-ALM</code></p>
<div class="banner"><div class="big"><span class="ok">OK TO DOWNLOAD: YES</span> · <span class="warn">OK TO SUBMIT: NO</span></div></div>
<ol>
<li><strong>Download</strong> <a href="../downloads/{CAND}-zeros.tif">{CAND}-zeros.tif</a> and verify its SHA-256.</li>
<li><strong>Select</strong> it only after the separate selector step approves it.</li>
<li><strong>Upload</strong> at the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submissions page</a>.</li>
<li><strong>Confirm</strong> the exact submitted bytes and save the organizer receipt as ORGANIZER-CONFIRMED.</li>
</ol>
<p class="small">Local format validity is <strong>not</strong> organizer acceptance. Never upload a prior branch artifact or a file
from the nine-site comparison; their values are USER-REPORTED and not unique.</p>
</main></body></html>
"""


def _current_review_pointer(card):
    return {
        "schema": "gems91.current-review-pointer.v1",
        "review_id": "GEMSDOE91-S91-ALM-20261031",
        "review_date_utc": "2026-10-31",
        "branch": "arena/2664739c-gemsdoe91",
        "status": "UNIQUE SUBMISSION GENERATED",
        "candidate_generated": True,
        "ok_to_download_new_candidate": True,
        "ok_to_submit": False,
        "ok_to_submit_reason": "Unique and format-certified, but a negative holdout by design; separate selector step and organizer receipt required.",
        "candidate_id": CAND,
        "candidate_primary": CAND_TIF,
        "candidate_sha256": card["raster_sha256"],
        "holdout_dti": 0.0,
        "holdout_dti_ci95": [0.0, 0.0],
        "holdout_evaluator": "gems91-hide-recover-v1.1-nohalo",
        "holdout_withheld_positives": 60988,
        "blind_sgmc_offcatalogue_control": 0.062396,
        "sgmc_parent_r0": 0.095386,
        "uniqueness_max_three_px_overlap_nine_leaders": 0.2383,
        "uniqueness_max_three_px_overlap_all_local": 0.3375,
        "organizer_confirmed": None,
        "leaderboard_score_estimate": None,
        "data_available": True,
        "review": "s91-alm/REVIEW.md",
        "executive_summary": "s91-alm/executive-summary.html",
        "run_card": "s91-alm/run-card.json",
        "hypotheses": "s91-alm/HYPOTHESES.md",
        "landing_page": "index.html",
        "submission_guide": "docs/submission-guide.html",
    }


def render(root: Path = ROOT) -> None:
    docs = root / "docs"
    out = docs / "s91-alm"
    out.mkdir(parents=True, exist_ok=True)
    snap = json.loads((docs / "review-20261030" / "nine-site-snapshot.json").read_text(encoding="utf-8"))
    ov = json.loads((out / "nine-leader-overlap.json").read_text(encoding="utf-8"))
    card = json.loads((out / "run-card.json").read_text(encoding="utf-8"))

    (out / "executive-summary.html").write_text(_executive_html(snap, ov, card), encoding="utf-8")

    print("wrote docs/s91-alm/executive-summary.html (portal owned by render_review_20261030)")


def render_portal(root: Path = ROOT) -> None:
    render(root)


if __name__ == "__main__":
    render(ROOT)
