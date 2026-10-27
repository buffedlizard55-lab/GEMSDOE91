#!/usr/bin/env python3
"""Render the quarantined S18 research page from the corrected evidence card."""
from html import escape as esc
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    docs = ROOT / 'docs'
    card = json.loads((docs / 'run-card-S18-UNIQUE.json').read_text())
    witness = json.loads((docs / 'review-20261027/witness-audit.json').read_text())
    result = witness['existing_candidates']['s18_current']
    if (card['ok_to_submit'] is not False or card['submission_ready'] is not False
            or not card['registry_uniqueness']['is_duplicate']
            or not witness['s18_alias']['byte_identical']
            or result['final_dots']['overlap_within_3px'] <= 0.70
            or card['raster_sha256'] != result['sha256']):
        raise ValueError('S18 research page requires a matching duplicate-stop receipt')
    tif = card['raster']['path'].removeprefix('docs/')
    archive = card['raster']['zip'].removeprefix('docs/')
    note = card['submission_note']
    if not 0 < len(note) <= 140:
        raise ValueError('Research note must fit the submission-note field')
    dots = result['final_dots']
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>S18 duplicate-stop review · GEMSDOE91</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f2;color:#1d302b;font:16px/1.65 system-ui,sans-serif}}
header,main,footer{{max-width:1080px;margin:auto;padding:24px}}header{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;border-bottom:1px solid #d6dfd9}}nav{{display:flex;gap:20px;flex-wrap:wrap}}a{{color:#17604a;text-underline-offset:3px}}section{{background:#fff;border:1px solid #d6dfd9;border-radius:12px;padding:30px;margin-bottom:24px}}h1{{font-size:clamp(32px,5vw,50px);line-height:1.1;margin:18px 0}}h2{{font-size:25px}}.eyebrow{{font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:#526a61}}.hero{{border-top:5px solid #b97428}}.warning{{background:#fff1df;color:#7f4312;padding:15px;border-radius:6px;font-weight:700}}.button{{display:inline-block;background:#194d3e;color:#fff;text-decoration:none;padding:12px 18px;border-radius:6px;font-weight:650;margin:5px 8px 5px 0}}.secondary{{background:#e8eeea;color:#194d3e}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:18px;margin:28px 0}}.metrics div{{border-left:2px solid #d6dfd9;padding:0 14px}}.metrics b{{display:block;font-size:26px}}.small,small{{font-size:13px;color:#526a61}}code{{overflow-wrap:anywhere;font-size:12px}}li{{margin:10px 0}}footer{{font-size:13px;color:#526a61}}@media(max-width:600px){{header,main,footer{{padding:16px}}section{{padding:20px}}}}
</style></head><body><header><b>GEMS / RESEARCH OPERATIONS</b><nav aria-label="Main navigation"><a href="index.html">Download &amp; status</a><a href="executive-summary.html">Executive summary</a><a href="executive-summary.html#how-to-submit">Submission guide</a></nav></header>
<main><section class="hero" data-submission-ready="false"><div class="eyebrow">S18-UNIQUE / CORRECTION · 27 October 2026</div><h1>A duplicate, not a new submission.</h1><p class="warning">OK TO DOWNLOAD: YES — RESEARCH ONLY<br>OK TO SUBMIT: NO — DUPLICATE STOP</p><p>The 26 October TIFF is <strong>byte-identical</strong> to the 25 October predecessor, despite its new name. Its final-dot overlap with a registered lattice is {dots['overlap_within_3px']:.3%}; the limit is 70%. The previous uniqueness PASS is withdrawn. No weekly slot should be used.</p>
<p><a class="button" download href="{esc(tif, quote=True)}">Download historical GeoTIFF ↓</a><a class="button secondary" download href="{esc(archive, quote=True)}">Single-TIFF ZIP</a></p>
<div class="metrics"><div><small>Final-dot overlap</small><b>{dots['overlap_within_3px']:.3%}</b><small>{round(dots['overlap_within_3px'] * dots['candidate_dots']):,} / {dots['candidate_dots']:,} dots</small></div><div><small>Provisional local format</small><b>PASS</b><small>Not an organizer receipt</small></div><div><small>Fold-honest holdout</small><b>UNVERIFIED</b><small>No run-specific evidence located</small></div><div><small>Live slots this review</small><b>0</b><small>None authorized</small></div></div>
<p class="small">Historical name: <code>{esc(card['submission_name'])}</code><br>SHA-256: <code>{esc(card['raster_sha256'])}</code><br>Research note ({len(note)}/140): <code>{esc(note)}</code></p></section>
<section><h2>What changed in the assessment</h2><ul><li>The earlier 21.44% figure compared only two references; it did not establish full-registry novelty. The lattice witness alone is enough to stop.</li><li>The historical holdout and per-feature canary claims lack a located, reproducible S18-specific fold-local receipt. The historical builder used a full-catalogue placement mask. Those numbers are preserved as historical claims, not validated holdout evidence.</li><li>Each file is one float32 band, EPSG:32611, 3,730 × 3,292 cells, finite within [0,1] and aligned to the hash-pinned sample mirror. The mirror is not authenticated organizer bytes. This format check is not approval or a guarantee the organizer will accept the outside-footprint encoding.</li></ul>
<p><a href="run-card-S18-UNIQUE.json">Corrected run card</a> · <a href="review-20261027/s18-card-as-received.json">Original card as received</a> · <a href="review-20261027/witness-audit.json">Exact byte and overlap audit</a> · <a href="review-20261027/review.md">Three-pass review and limitations</a></p></section>
<section><h2>Before any future upload</h2><p>A different, independently generated TIFF must pass all-registry surface and final-dot gates, independent fold-local feature canaries, buffered-segment holdout against a comparable incumbent, exact-grid validation, and a separate live-slot selector. No such file is cleared here. See the <a href="executive-summary.html#how-to-submit">future-submission guide</a> and <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#submission-format">official format</a>.</p></section></main><footer>Research evidence only · no automatic competition uploads.</footer></body></html>\n'''
    (docs / 's18-unique-executive-summary.html').write_text(html)


if __name__ == '__main__':
    render()
