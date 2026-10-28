#!/usr/bin/env python3
"""Corrected historical TLF page from frozen audit receipts; never promotes."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    audit = json.loads((ROOT / 'docs/s26/tlf-protocol-audit.json').read_text())
    card = json.loads((ROOT / 'docs/s25-tlf/run-card.json').read_text())
    nine = json.loads((ROOT / 'docs/s22/nine-site-audit.json').read_text())['sites']
    art = card['artifact']
    rows = ''.join('<tr><td>' + html.escape(s['site']) + '</td><td>' + html.escape(s['filename']) +
                   '</td><td>' + str(s['claimed_historical_value']) +
                   ' USER-REPORTED</td><td>Unavailable</td><td>NO</td></tr>' for s in nine)
    bad = max(audit['comparisons'], key=lambda r: r['overlap_within_3px'])
    h = card['holdout']['scores']['tlf25']
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>TLF correction · research only</title>
<style>body{{font:16px/1.6 system-ui;margin:2rem auto;padding:0 1rem;max-width:1100px;color:#18342c;background:#f5f6ef}}a{{color:#145b48}}.warning{{border:3px solid #84351e;padding:1rem;background:#fff1e8}}.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.7rem;border:1px solid #bac8c1;text-align:left;overflow-wrap:anywhere}}code{{overflow-wrap:anywhere}}h1{{line-height:1.2}}</style></head><body><main data-submission-ready="false">
<p><a href="../index.html">Project home</a> · <a href="../submission-guide.html">Submission guide</a></p>
<h1>Approval retracted: S25-TLF is research only</h1>
<div class="warning"><strong>OK TO DOWNLOAD: YES — RESEARCH ONLY. OK TO SUBMIT: NO.</strong>
<p>Exact frozen-registry check: {100*bad['overlap_within_3px']:.6f}% within 3 px of <code>{html.escape(bad['path'])}</code>. Your rule stops above 70%. Checked {audit['references_checked']}/64 references; two missing references remain unverified. No dense-reference exemptions.</p>
<p>The earlier 0.36 (0.28–0.44) projection is withdrawn: it was a ceiling-clipped midpoint, not a calibrated estimate or confidence interval. SGMC helped choose weights and budget, so it is not an independent blind test. The eight spatial slices were not out-of-fold fitting.</p></div>
<h2>Download and status</h2><div class="scroll"><table><thead><tr><th>File</th><th>Estimated leaderboard score</th><th>Unique?</th><th>Submit?</th></tr></thead><tbody><tr><td><a download href="../downloads/{html.escape(Path(art['tif']).name)}">Download historical TLF TIFF</a> · <a download href="../downloads/{html.escape(Path(art['zip']).name)}">Single-TIFF ZIP</a></td><td>Unavailable; no ORGANIZER-CONFIRMED receipt</td><td>Nine-leader dot screen passed historically; full registry FAIL; original pre-placement surface not saved</td><td>NO</td></tr></tbody></table></div>
<p>SHA-256 <code>{audit['raster_sha256']}</code>. Existing bytes unchanged; not a newly generated submission. Automated technical validator: {audit['validator_output']['status']} (finite [0,1], no NaN inside footprint, pinned CRS/shape/transform). Technical PASS is not upload approval.</p>
<p>Historical HOLDOUT-DTI {h['dti']:.6f}, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], {h['withheld_positive_pixels']:,} withheld positives, {h['evaluator_version']}. Retained arithmetic, not a new result or leaderboard score. Feature canaries were tested on SGMC, not the required holdout; no retrospective canary clearance.</p>
<h2>Nine-site executive summary</h2><p>Best supplied historical claim: GEMSDOE32 0.2778. All nine leaders duplicate at least one peer under the 70% rule. These claims have no file-linked organizer receipts; no new estimate can be justified. Full filenames below, not instructions to re-upload.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>Historical best claimed file</th><th>Supplied result</th><th>Estimate</th><th>Unique / new upload?</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Why 0.2778?</h2><p>Byte lineage shows shared ridge support with thinning and catalogue-proximal deletions. Removing redundant prediction mass can improve DTI if little truth coverage is lost. That is a conditional explanation, not proof of the hidden score's cause: truth-side credit T and prediction-side credit M are different. No evidence here guarantees a unique file will beat it.</p>
<h2>Submission steps — future gate-passing files only</h2><ol><li>Pass assigned-lane, per-feature holdout canaries, matched buffered holdout, pre-placement surface and final-dot checks against the frozen registry, plus source-rights checks.</li><li>Validate actual TIFF and one-TIFF ZIP; require one float32 band, [0,1], matching CRS/shape/geotransform, and no NaN inside footprint.</li><li>A separate selector checks current authenticated quota; no slot is selected by this review.</li><li>Only after approval, upload that exact file at DrivenData; use its recorded name and note (≤140 characters). Store receipt, timestamp, score and uploaded SHA-256.</li></ol>
<p>Historical name: <code>{html.escape(art['submission_name'])}</code><br>Historical note: <code>{html.escape(art['note'])}</code> — do not use as slot authorization.</p>
<p><a href="../s26/REVIEW.md">Three-pass review and next steps</a> · <a href="../s26/tlf-protocol-audit.json">Exact comparison receipt</a> · <a href="../s26/preregistration.md">Four deferred hypotheses and official sources</a> · <a href="../s26/run-card.json">Review run card</a></p>
<p>Official metric and format: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData</a>. Known-mask clarification: <a href="https://community.drivendata.org/t/11516/4">DrivenData staff</a>. Local all-finite encoding does not resolve official outside-bounds null/NaN wording.</p>
</main></body></html>'''
    (ROOT / 'docs/s25-tlf/executive-summary.html').write_text(page + '\n')
    # Correct active front-door assertions without changing historical scientific receipts.
    for rel in ('docs/index.html', 'index.html'):
        p = ROOT / rel
        text = p.read_text()
        replacements = {
            'CLEARED TO SUBMIT': 'NOT OK TO SUBMIT — APPROVAL RETRACTED',
            'cleared to submit': 'NOT approved to submit (approval retracted)',
            'A unique TIF is ready: OK to download and OK to submit.': 'TLF research download only: NOT OK TO SUBMIT.',
            'estimated score 0.36 (range 0.28&ndash;0.44), a PROJECTION': 'earlier projection withdrawn; no calibrated leaderboard estimate',
            'Estimated leaderboard score 0.36 (range 0.28&ndash;0.44) &mdash; a PROJECTION, not a score.': 'Earlier 0.36 projection WITHDRAWN; full-registry overlap is 99.60%, so do not submit.',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        marker = 'id="s26-correction"'
        if marker not in text:
            banner = '<section id="s26-correction" style="border:3px solid #84351e;padding:20px;background:#fff1e8"><h2>Current decision: NOT OK TO SUBMIT</h2><p>TLF approval retracted: 99.601667% registered-lattice overlap, above your 70% stop rule. Earlier 0.36 projection withdrawn. NO NEW TIFF; research only. OK TO SUBMIT: NO. No experiments or slots in this review.</p><a href="' + ('s25-tlf/executive-summary.html' if rel.startswith('docs/') else 'docs/s25-tlf/executive-summary.html') + '">Corrected nine-site executive summary, research download and submission gates</a></section>'
            pos = text.find('<main')
            if pos >= 0:
                end = text.index('>', pos) + 1
                text = text[:end] + banner + text[end:]
        p.write_text(text)


def main():
    render()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
