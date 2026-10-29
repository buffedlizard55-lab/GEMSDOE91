#!/usr/bin/env python3
"""Render the 2026-10-29 priority table from saved, fail-closed evidence."""
from __future__ import annotations
import hashlib
from html import escape as esc
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.render_review_8e8d86f2 import STYLE  # noqa: E402
from scripts.verify_nine_site_leaders import LEADERS  # noqa: E402


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def render():
    base = 'docs/review-4239f6e5/'
    card = load(base + 'run-card.json')
    pre = load(base + 'experiment-preflight.json')
    focus = load(base + 'nine-site-leaders.json')
    s25 = load(base + 'historical-s25-audit.json')
    concurrent = load(base + 'concurrent-s26-audit.json')
    old = load('docs/s22/nine-site-audit.json')
    rows = {x['site']: x for x in old['sites']}
    if (card['verdict'] != 'negative' or card['ok_to_submit'] is not False
            or card['candidate_generated'] is not False or card['raster_sha256'] is not None
            or card['leaderboard_score_estimate'] is not None or card['organizer_confirmed_score'] is not None
            or pre['status'] != 'BLOCKED' or pre['ok_to_submit'] is not False
            or pre['capacity']['sample_semantics']['status'] != 'CONFLICT_WITH_ORGANIZER_DESCRIPTION'
            or focus['sample_sha256'] != pre['capacity']['sample_sha256']
            or s25['ok_to_submit'] is not False or s25['verdict'] != 'negative'
            or s25['nine_site_report_sha256'] != hashlib.sha256((ROOT / base / 'nine-site-leaders.json').read_bytes()).hexdigest()
            or s25['implementation_sha256'] != hashlib.sha256((ROOT / 'scripts/audit_priority_snapshot.py').read_bytes()).hexdigest()
            or s25['validator_implementation_sha256'] != hashlib.sha256((ROOT / 'scripts/audit_downloads.py').read_bytes()).hexdigest()
            or s25['stopped_at'] != 'frozen lattice'
            or s25['comparisons']['frozen lattice']['dot_status'] != 'DUPLICATE'
            or set(rows) != set(LEADERS)):
        raise ValueError('2026-10-29 evidence inconsistent; refusing to render')
    historical = card['historical_research_only']
    tif = ROOT / historical['raster_path']
    archive = ROOT / historical['zip_path']
    if (hashlib.sha256(tif.read_bytes()).hexdigest() != historical['raster_sha256']
            or hashlib.sha256(archive.read_bytes()).hexdigest() != historical['zip_sha256']
            or s25['raster']['sha256'] != historical['raster_sha256']):
        raise ValueError('S25 byte identity mismatch')
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError('S25 archive is not the expected single TIFF')
    table = []
    for site in LEADERS:
        r = rows[site]
        fresh = focus['files'][site]
        overlap = focus['max_overlap_into_any_other_leader'][site]
        if (fresh['sha256'] != r['sha256'] or fresh['footprint_checked'] is not True
                or fresh['positive_outside_footprint'] != 0
                or overlap <= .70 or abs(overlap - r['max_overlap_vs_other_eight']['overlap_within_3px']) > 1e-12):
            raise ValueError(f'{site}: old and new evidence disagree')
        # Frozen commit URL is convenient in a browser; SHA-256 is the byte identity.
        blob_url = r['source_url']
        raw_url = blob_url.replace('/blob/', '/raw/', 1)
        table.append(f'''<tr><th scope="row">{esc(site)}</th>
<td class="file"><a href="{esc(raw_url,quote=True)}">{esc(r['filename'])}</a><small class="block">SHA-256 {esc(r['sha256'][:16])}… · <a href="{esc(blob_url,quote=True)}">pinned source</a></small></td>
<td>{esc(fresh['score_user_cited'])}<small class="block">USER-REPORTED</small></td><td>Unavailable<small class="block">no receipt / calibration</small></td>
<td class="fail">No<small class="block">{overlap:.2%} vs a peer</small></td><td class="fail">NO<small class="block">historical reference</small></td></tr>''')
    overlap = s25['comparisons']['frozen lattice']['directed_overlap_within_3px']
    nine = max(s25['comparisons'][site]['directed_overlap_within_3px'] for site in LEADERS)
    h = historical['holdout_evidence']
    capacity = pre['capacity']
    table.append(f'''<tr><th scope="row">S25-FABRIC E2</th><td class="file"><a download href="../downloads/{esc(tif.name,quote=True)}">{esc(tif.name)}</a><small class="block">SHA-256 {esc(historical['raster_sha256'][:16])}… · <a download href="../downloads/{esc(archive.name,quote=True)}">one-TIFF ZIP</a></small></td><td>None<small class="block">prior research</small></td><td>Unavailable</td><td class="fail">No<small class="block">{overlap:.2%} vs lattice; {nine:.2%} max vs nine leaders</small></td><td class="fail">NO<small class="block">duplicate stop</small></td></tr>''')
    expected_s26 = {
        'gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros': 'S26 LiDAR / radiometrics',
        'gems91-s26-fabric-emit-10pxcap-22163dots-20261029T143240Z-e7724d8c-zeros': 'S26 emitter · 22,163',
        'gems91-s26-fabric-emit-10pxcap-37654dots-20261029T143324Z-28228279-zeros': 'S26 emitter · 37,654',
    }
    results = concurrent['results']
    s26_table = []
    card_s26 = {row['raster_path']: row for row in card['concurrent_research_only']['results']}
    if ({row['name'] for row in results} != set(expected_s26) or len(results) != len(expected_s26)
            or set(card_s26) != {row['tif'] for row in results}
            or card['concurrent_research_only']['this_review_generated_these'] is not False
            or concurrent['sample_sha256'] != pre['capacity']['sample_sha256']
            or concurrent['implementation_sha256'] != hashlib.sha256((ROOT / 'scripts/audit_concurrent_s26.py').read_bytes()).hexdigest()
            or concurrent['shared_audit_sha256'] != s25['implementation_sha256']
            or concurrent['validator_implementation_sha256'] != s25['validator_implementation_sha256']):
        raise ValueError('concurrent S26 evidence incomplete or mismatched')
    for result in results:
        tif_path = ROOT / result['tif']
        zip_path = ROOT / result['zip']
        if (not tif_path.resolve().is_relative_to((ROOT / 'docs/downloads').resolve())
                or not zip_path.resolve().is_relative_to((ROOT / 'docs/downloads').resolve())
                or hashlib.sha256(tif_path.read_bytes()).hexdigest() != result['tif_sha256']
                or hashlib.sha256(zip_path.read_bytes()).hexdigest() != result['zip_sha256']
                or result['submission_ready'] is not False or result['validator_output']['status'] != 'PASS'
                or card_s26[result['tif']]['sha256'] != result['tif_sha256']
                or card_s26[result['tif']]['verdict'] != 'negative' or card_s26[result['tif']]['ok_to_submit'] is not False
                or card_s26[result['tif']]['overlap_vs_lattice'] != result['final_dot_comparison']['directed_overlap_within_3px']
                or result['final_dot_comparison']['dot_status'] != 'DUPLICATE'
                or result['final_dot_comparison']['directed_overlap_within_3px'] <= .70):
            raise ValueError('concurrent S26 evidence or bytes inconsistent')
        with zipfile.ZipFile(zip_path) as z:
            if z.namelist() != [tif_path.name] or z.read(tif_path.name) != tif_path.read_bytes():
                raise ValueError('concurrent S26 ZIP mismatch')
        label = expected_s26[result['name']]
        pct = result['final_dot_comparison']['directed_overlap_within_3px']
        prior = ('Historical HOLDOUT-DTI 0.133242 [0.111054, 0.155289]; 60,988 withheld, '
                 'gems57-pooled-hide-v2; canary and input-mask review unresolved' if 'lidarrad' in result['name']
                 else 'S26 proxy/placement holdout not measured; S25 holdout does not apply')
        row = f'''<tr><th scope="row">{esc(label)}</th><td class="file"><a download href="../downloads/{esc(tif_path.name,quote=True)}">{esc(tif_path.name)}</a><small class="block">SHA-256 {esc(result['tif_sha256'][:16])}… · <a download href="../downloads/{esc(zip_path.name,quote=True)}">one-TIFF ZIP</a></small></td><td>None<small class="block">concurrent research</small></td><td>Unavailable<small class="block">{esc(prior)}</small></td><td class="fail">No<small class="block">{pct:.2%} vs lattice</small></td><td class="fail">NO<small class="block">duplicate stop</small></td></tr>'''
        table.append(row)
        s26_table.append(row)
    text = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Priority review · GEMSDOE91</title><style>{STYLE}</style></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap"><header class="nav"><a class="brand" href="../index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a><nav aria-label="Main navigation"><a href="../index.html">Home</a><a href="#table">Nine-site table</a><a href="#research">Research</a><a href="../submission-guide.html">Submission guide</a></nav></header>
<main id="main"><section class="hero" data-submission-ready="false"><div><p class="eyebrow">CURRENT REVIEW / 29 OCTOBER 2026</p><h1>Evidence first.<br>Submission blocked.</h1><p class="lead">This review generated no GeoTIFF. Historical and concurrent research files are available to inspect; none is cleared for a weekly slot.</p><p><a class="button" href="run-card.json" download>Download the negative run card</a> <a href="REVIEW.md">Full review ↗</a></p></div>
<aside class="dark"><p class="eyebrow" style="color:#b9ddc6">DECISION / FAIL CLOSED</p><h2>OK TO SUBMIT: NO</h2><div class="statline"><span>New candidate</span><strong>NONE</strong></div><div class="statline"><span>Experiments / slots used</span><strong>0 / 0</strong></div><div class="statline"><span>Forced lattice overlap</span><strong>≥ {capacity['overlap_lower_bound']:.2%}</strong></div><p>Necessary geometric bound at the frozen budget, conditional on the mirrored sample; not a score or registry-wide uniqueness test.</p></aside></section>
<div class="note"><strong>Template provenance conflict.</strong> The pinned sample mirror contains {capacity['sample_semantics']['nonzero_inside_footprint']:,} nonzero cells inside its footprint; the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">organizer describes its sample as predicting total absence</a>. Mirror hashes verify identity, not authenticity or use rights. Confirm the official sample before any release.</div>
<section class="section" id="table"><div class="section-title"><h2>Executive file comparison</h2><p>Actual bytes checked · no new leaderboard estimate</p></div><p>Score values are <strong>USER-REPORTED</strong>, not ORGANIZER-CONFIRMED. A score receipt tied to the file was not available. “No” under unique means the strict directed 3-pixel overlap rule fails; overlap is not a score.</p><div class="table-scroll"><table><caption>Nine user-named historical leaders, S25, and three concurrent S26 research files. All are unapproved for upload.</caption><thead><tr><th scope="col">File source</th><th scope="col">Download / byte identity</th><th scope="col">Reported value</th><th scope="col">Defensible estimate</th><th scope="col">Unique?</th><th scope="col">Submit?</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p class="subtle">Peer overlap is directed and computed from the exact binary TIFFs against the supplied mirrored footprint. The nine checks cover only those nine leaders; S25 final-dot checks do not reconstruct its pre-placement surface. S26 checks stop at the first lattice duplicate; pre-placement surfaces were not rechecked. Full registry coverage and sample authenticity are unverified. <a href="nine-site-leaders.json">Nine-site receipt</a> · <a href="historical-s25-audit.json">S25 recheck</a> · <a href="concurrent-s26-audit.json">S26 recheck</a>.</p></section>
<section class="section" id="research"><div class="grid2"><article class="card"><span class="eyebrow">THE GEMSDOE32 CLAIM</span><h2>Why might 0.2778 have worked?</h2><p>It is the highest <strong>user-reported</strong> value in the nine-site list, not a verified organizer receipt. With the organizer’s distance-weighted metric, thinning redundant dots might reduce false-positive mass while preserving coverage; it can also discard real fault evidence. Hidden labels and the score-to-file receipt are unavailable, so causality and improvement over GEMSDOE32 are unproven.</p><a href="../review-ad43b4e5/nine-site-lineage.json">Historical support geometry ↗</a></article>
<article class="card"><span class="eyebrow">PRIOR HOLDOUT / NOT THIS TIFF’S SCORE</span><h2>S25 is not a promotion.</h2><p>Its prior fold-local <strong>{esc(h['label'])} {h['value']:.6f}</strong>, 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}], {esc(h['evaluator_version'])}, {h['withheld_positive_pixels']:,} withheld positives, exceeded one matched control. That is not a direct measurement of the final static TIFF, nor a leaderboard score. The final dots fail the lattice rule.</p><a href="HYPOTHESES.md">Three ranked, untested hypotheses ↗</a></article></div></section>
<section class="section"><h2>What would change the decision?</h2><ol><li>Resolve the single assigned lane and the literal lattice/budget conflict without self-exemption.</li><li>Obtain and verify the authentic sample, catalogue, feature stack, rights and full frozen registry.</li><li>Run feature-alone leakage canaries and the shared buffered, whole-segment matched holdout; check pre-placement surfaces and final dots against every reference.</li><li>Use the shared writer and an independent selector. Only an authenticated organizer receipt can confirm a score or current weekly allowance.</li></ol><p><a href="../submission-guide.html">Detailed future submission guide ↗</a> · <a href="../index.html#feed">GitHub source feed ↗</a> · <a href="REVIEW.md">Sources and limitations ↗</a></p></section></main>
<footer><span>Maximize P(Win) · Own the Outcome<br>Research, not a leaderboard projection.</span><span><a href="run-card.json">Run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">Source repository</a></span></footer></div></body></html>\n'''
    (ROOT / base / 'executive-summary.html').write_text(text, encoding='utf-8')
    # Supersede the concurrent S26 page's unsupported uniqueness and score
    # claims while retaining the research downloads and the original history.
    s26_html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>S26 research recheck · GEMSDOE91</title><style>{STYLE}</style></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap"><header class="nav"><a class="brand" href="../index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a><nav aria-label="Main navigation"><a href="../index.html">Home</a><a href="../review-4239f6e5/executive-summary.html">Complete table</a><a href="../submission-guide.html">Submission guide</a></nav></header><main id="main">
<section class="hero" data-submission-ready="false"><div><p class="eyebrow">S26 CONCURRENT RESEARCH / 29 OCTOBER 2026</p><h1>Three downloads.<br>No submission.</h1><p class="lead">Each existing S26 raster fails the literal 70% duplicate rule against the pinned lattice. A previous narrower uniqueness claim is superseded. No new leaderboard score is estimated.</p><p><a class="button" href="../review-4239f6e5/concurrent-s26-audit.json">Independent recheck ↗</a></p></div><aside class="dark"><h2>OK TO SUBMIT: NO</h2><p>These are research-only outputs from concurrent branches, not new experiments in the current review.</p></aside></section>
<section class="section"><h2>S26 executive file comparison</h2><div class="table-scroll"><table><caption>Verified TIFF/ZIP bytes, lattice overlap and negative readiness.</caption><thead><tr><th scope="col">File source</th><th scope="col">Download / byte identity</th><th scope="col">Reported value</th><th scope="col">Defensible estimate</th><th scope="col">Unique?</th><th scope="col">Submit?</th></tr></thead><tbody>{''.join(s26_table)}</tbody></table></div></section>
<section class="section"><h2>What the numbers mean</h2><p>The LiDAR/radiometric study reported HOLDOUT-DTI 0.133242 [0.111054, 0.155289], <code>gems57-pooled-hide-v2</code>, 60,988 withheld positives. It is a historical holdout report, not an organizer score; the code averages per-fold feature canaries instead of checking each fold’s maximum, and source NoData/masks have not been independently verified here.</p><p>The emitter used a distance-to-S25-dot proxy and a different collar; S25’s earlier 0.147741 holdout is not an S26 holdout. A necessary capacity bound at 22,163 dots is not proof of a feasible, unique raster. Do not exempt the lattice or change the budget without the coordinator.</p><p>Local TIFF checks are conditional on the unauthenticated mirrored sample. Values outside its footprint are zero, not proven compliant with the organizer’s null/NaN instruction. The archived scripts are disabled pending an assigned lane, verified input masks, pre-placement surface checks and complete registry checks.</p><p><a href="../review-4239f6e5/REVIEW.md">Detailed correction and sources ↗</a> · <a href="../review-4239f6e5/HYPOTHESES.md">Untested hypotheses ↗</a></p></section></main><footer><span>Research only · No slot spent in this review</span><a href="../review-4239f6e5/run-card.json">Current run card</a></footer></div></body></html>\n'''
    (ROOT / 'docs/s26/executive-summary.html').write_text(s26_html, encoding='utf-8')


if __name__ == '__main__':
    render()
