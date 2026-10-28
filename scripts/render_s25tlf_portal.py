#!/usr/bin/env python3
"""Render corrected S25-TLF guidance from receipts; never select a slot.

Historical renderer archived in evidence/review-de9d7d75/originals/.
No inferred leaderboard estimate or subset-registry approval is published.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    card = json.loads((ROOT / 'docs/s25-tlf/run-card.json').read_text())
    audit = json.loads((ROOT / 'docs/review-de9d7d75/delivery-audit.json').read_text())
    rows = json.loads((ROOT / 'docs/s25-tlf/nine-site-table.json').read_text())['rows']
    esc = html.escape
    art = card['artifact']
    table = ''.join('<tr><td><a href="' + esc(r['site_url']) + '">' + esc(r['site']) +
                    '</a></td><td><code>' + esc(r['file']) + '</code></td><td>' + esc(r['claim']) +
                    ' USER-REPORTED; no organizer receipt</td><td>Unavailable</td>' +
                    '<td>NO — historical peer-overlap breach</td><td>NO</td></tr>' for r in rows)
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>GEMSDOE91 — corrected executive summary</title>
<style>body{font:17px/1.6 system-ui,sans-serif;max-width:1200px;margin:40px auto;padding:0 24px;color:#17312c;background:#f7faf8}h1,h2{line-height:1.2}a{color:#075b92}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #b6c9c0;padding:12px;text-align:left;vertical-align:top}code{overflow-wrap:anywhere}.scroll{overflow:auto}.status{padding:24px;border:3px solid #934126;background:#fff1e9}.button{display:inline-block;padding:12px;background:#173f36;color:white;margin:8px 8px 8px 0;border-radius:6px}</style></head><body><main>
<p>GEMSDOE91 / evidence review / 2026-10-28</p><h1>Research download available.<br>No file cleared for competition submission.</h1>
<section class="status"><strong>OK TO DOWNLOAD: YES — RESEARCH ONLY · OK TO SUBMIT: NO</strong>
<p>No new candidate generated in this review; zero experiments and zero competition slots used.
The earlier S25-TLF approval and 0.36 projection are withdrawn. The frozen registry lattice audit found 99.6017% of dots within 3 pixels, exceeding the 70% duplicate limit. A valid TIFF is not evidence of a high score.</p>'''
    if not audit['format_ok']:
        page = page.replace('OK TO DOWNLOAD: YES', 'OK TO DOWNLOAD: NO')
    if audit['format_ok']:
        for key, label in [('tif', 'Download research TIFF'), ('zip', 'Download single-TIFF research ZIP')]:
            page += f'<a class="button" download href="../downloads/{esc(Path(art[key]).name)}">{label}</a>'
    page += f'''<p>Name: <code>{esc(art['submission_name'])}</code><br>Note (research): <code>{esc(art['note'])}</code><br>SHA-256: <code>{art['sha256']}</code></p></section>
<h2>Current candidate decision</h2><div class="scroll"><table><thead><tr><th>File</th><th>Estimated leaderboard score</th><th>Holdout evidence</th><th>Uniqueness</th><th>Submit?</th></tr></thead><tbody><tr>
<td>{esc(Path(art['tif']).name)}</td><td>Unavailable; no calibrated estimate or organizer receipt</td>
<td>Historical HOLDOUT-DTI 0.120456; 95% CI [0.105729, 0.134593]; evaluator gems57-pooled-hide-v2; 60,988 withheld positives. Not rerun here; not a demonstrated best-incumbent win.</td>
<td>FAIL: 99.6017% directed overlap with frozen lattice (&gt;70%). Pre-placement and full-registry checks remain incomplete; historical rank computation mishandled ties.</td><td>NO</td></tr></tbody></table></div>
<h2>Nine-site executive comparison</h2><p>Best historical claim per site, transcribed from the existing nine-site receipt. Not independently refreshed today. Filenames identify historical artifacts, not recommended new attempts. Do not resubmit these as unique work.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>Historical file</th><th>Reported result</th><th>New score estimate</th><th>Unique?</th><th>Submit as new?</th></tr></thead><tbody>{table}</tbody></table></div>
<h2>Why GEMSDOE32 might have performed better</h2><p>The nine historical leaders share extensive dot support. Reducing redundant predicted dots can reduce false-positive cost while retaining proximity coverage under DTI. This is a plausible explanation for the reported ordering, not a causal finding. No hidden labels or organizer receipt establish why 0.2778 occurred. A larger score cannot be promised.</p>
<h2>Automated gates, then a separate selector</h2><ol><li>Assigned single-method lane and unexhausted experiment/time budget.</li><li>Pinned sample, features, catalogue and complete unchanged registry; verify rights and masks.</li><li>Per-feature canaries; buffered whole-segment hide-and-recover using only visible catalogue context; pooled DTI with α 0.2, β 0.8 and 300 m triangular kernel.</li><li>Beat the current matched holdout incumbent, including paired uncertainty—not merely random dots.</li><li>Check pre-placement surface and final dots against every registry raster. Unknown references block clearance.</li><li>Shared writer and on-disk validator: one band, finite [0,1], matching CRS/shape/transform and footprint.</li><li>A separate selector checks the authenticated weekly cap before approval. This review does not use a slot.</li></ol>
<h2>Exact submission procedure — only after approval</h2><p>Do not upload this research file now. Once a future candidate passes every gate and the selector approves it: download that approved TIFF, select it on the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">competition submission page</a>, copy its unique name and ≤140-character note, submit within the account's displayed cap, and store the organizer receipt. Local range validation checks this file, but cannot establish the cause of the earlier [0,1] error or guarantee organizer acceptance.</p>
<h2>Evidence and limits</h2><p><a href="AUDIT-20261028.md">Witness audit and limitations</a> · <a href="witness-audit-20261028.json">Witness receipt</a> · <a href="../review-de9d7d75/REVIEW.md">Parallel three-pass review</a> · <a href="../review-de9d7d75/HYPOTHESES.md">Ranked hypotheses</a> · <a href="../review-de9d7d75/delivery-audit.json">Fresh byte audit</a> · <a href="run-card.json">Corrected historical run card</a> · <a href="nine-site-table.json">Historical nine-site receipt</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution</a></p>
<p>Pinned sample and catalogue restored through the existing SHA-pinned GitHub mirror; shared footprint/catalogue checks PASS. Full features and registry are still absent. Direct DrivenData, USGS, NLR and Dropbox access is outside this sandbox's allowed network hosts. No current leaderboard, weekly cap, account receipt or new official external dataset was verified today. Competition targets fault predictions; these are not verified geothermal vents or productive reservoirs.</p></main></body></html>'''
    (ROOT / 'docs/s25-tlf/executive-summary.html').write_text(page)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
