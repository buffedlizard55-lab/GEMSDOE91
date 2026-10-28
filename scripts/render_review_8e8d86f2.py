#!/usr/bin/env python3
"""Render current review pages from pinned evidence, never from a score projection."""
from __future__ import annotations
from html import escape as esc
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'

STYLE = '''
:root{--ink:#142d29;--muted:#465e57;--paper:#f5f6ef;--line:#d7e1d9;--green:#155b48;--amber:#81402b;--soft:#fff0e8;--white:#fff}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:#145c49;text-underline-offset:3px}a:hover{color:#073d30}a:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #ac6900;outline-offset:3px}.skip{position:fixed;left:10px;top:-100px;z-index:5;background:white;padding:10px}.skip:focus{top:10px}.wrap{width:min(1180px,calc(100% - 48px));margin:auto}.nav{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:23px 0;border-bottom:1px solid var(--line)}.brand{font-weight:800;letter-spacing:-.03em;color:var(--ink);text-decoration:none}.brand small{display:block;font-size:10px;letter-spacing:.15em;color:var(--muted)}nav{display:flex;flex-wrap:wrap;gap:20px;font-size:13px;font-weight:650}main{padding-bottom:40px}.hero{display:grid;grid-template-columns:1.25fr .9fr;gap:40px;align-items:start;padding:55px 0 28px}.eyebrow{text-transform:uppercase;letter-spacing:.14em;color:var(--green);font-size:11px;font-weight:800}h1{font-size:clamp(36px,5vw,62px);letter-spacing:-.045em;line-height:1.06;margin:16px 0 20px}h2{font-size:clamp(24px,3vw,33px);line-height:1.2;letter-spacing:-.025em;margin:0 0 16px}h3{font-size:18px;line-height:1.3;margin:0 0 10px}.lead{font-size:18px;max-width:650px;color:var(--muted)}.verdict{display:inline-block;background:var(--soft);color:#742f1e;border:1px solid #eccab8;border-radius:4px;padding:6px 10px;font-size:12px;font-weight:800;letter-spacing:.04em}.dark{background:var(--ink);color:white;border-radius:12px;padding:28px;overflow-wrap:anywhere;box-shadow:0 15px 40px #1a342510}.dark p,.dark small{color:#d4e2dc}.dark a{color:#d9f4e3}.dark h2{font-size:24px}.statline{display:flex;justify-content:space-between;gap:15px;padding:11px 0;border-bottom:1px solid #ffffff25;font-size:14px}.statline strong{color:#f6cfb4;text-align:right}.button{display:inline-block;border:1px solid #b6d8c1;background:#d8f0dd;color:#12382b!important;border-radius:6px;padding:12px 16px;font-size:14px;font-weight:750;text-decoration:none;cursor:pointer}.button.secondary{background:transparent;color:inherit!important;border-color:currentColor}.button:hover{filter:brightness(.96)}.button+.button{margin-left:8px}.subtle{color:var(--muted);font-size:13px}.note{background:#fff4ec;border:1px solid #eed6c6;border-left:4px solid #a45731;padding:18px 20px;border-radius:5px;margin:12px 0 28px}.section{padding:36px 0;border-bottom:1px solid var(--line)}.section-title{display:flex;justify-content:space-between;gap:20px;align-items:baseline}.section-title p{margin:0;color:var(--muted);font-size:14px}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.card{background:var(--white);border:1px solid var(--line);border-radius:9px;padding:22px;min-width:0;overflow-wrap:anywhere}.card .metric{font-size:34px;font-weight:750;line-height:1.2;letter-spacing:-.04em;margin:13px 0}.card p{font-size:14px;color:var(--muted)}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.table-scroll{max-width:100%;overflow:auto;border:1px solid var(--line);border-radius:8px;background:white}table{border-collapse:collapse;width:100%;font-size:13px;min-width:820px}caption{text-align:left;padding:15px;color:var(--muted)}th,td{text-align:left;vertical-align:top;padding:13px;border-bottom:1px solid #e4ebe5}thead th{background:#eaf0e8;font-size:11px;letter-spacing:.04em;text-transform:uppercase}th[scope=row]{white-space:nowrap}td.file{max-width:350px;overflow-wrap:anywhere}.fail{color:#803722;font-weight:750}.block{display:block}.small,small{font-size:12px;color:var(--muted)}code{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.dark code{color:white}ul,ol{padding-left:22px}li{margin:9px 0}details{border-top:1px solid var(--line);padding:14px 0}summary{cursor:pointer;font-weight:700}.feed-list{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;list-style:none;padding:0}.feed-list li{margin:0;background:white;border:1px solid var(--line);border-radius:6px;padding:10px;font-size:13px;overflow-wrap:anywhere}.feed-list small{display:block}.feed-status{min-height:1.6em;font-size:13px;color:var(--muted)}button.refresh{border:1px solid var(--green);background:white;color:var(--green);border-radius:6px;padding:10px 14px;font:inherit;font-size:14px;font-weight:700;cursor:pointer}button:disabled{opacity:.65;cursor:wait}footer{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;color:var(--muted);font-size:12px;padding:28px 0 38px}.no-margin{margin:0}.status-label{font-weight:750;color:#762e1c}
@media(max-width:780px){.wrap{width:calc(100% - 32px)}.nav{align-items:flex-start;flex-direction:column}nav{gap:15px}.hero,.grid2{grid-template-columns:1fr;gap:22px}.hero{padding-top:38px}.cards,.feed-list{grid-template-columns:1fr}.section-title{display:block}.section-title p{margin-bottom:15px}.button+.button{margin-left:0;margin-top:8px}.section{padding:28px 0}}
'''


def load(name):
    return json.loads((DOCS / name).read_text(encoding='utf-8'))


def render_sources():
    card = load('review-8e8d86f2/run-card.json')  # historical review; never rewritten
    current = load('review-ad43b4e5/run-card.json')
    context = load('review-ad43b4e5/context-buffer-audit.json')
    recheck = load('review-ad43b4e5/nine-site-recheck.json')
    lineage = load('review-ad43b4e5/nine-site-lineage.json')
    pre = load('review-ad43b4e5/experiment-preflight.json')
    feature = load('review-8e8d86f2/feature-audit.json')
    s18 = load('review-8e8d86f2/s18-witness.json')
    s23 = load('review-8e8d86f2/s23-witness.json')
    s23_inputs = load('review-8e8d86f2/s23-input-audit.json')
    s23_semantics = load('review-8e8d86f2/s23-band-semantics.json')
    s23_prior = load('s23/run-card.json')
    prior = load('s22/run-card.json')
    audit = load('s22/nine-site-audit.json')
    focus = load('review-8e8d86f2/focus-inventory.json')
    official = load('review-8e8d86f2/official-observation.json')
    focus_sites = {24, 25, 27, 28, 30, 31, 32, 33, 36}
    if (current['verdict'] != 'negative' or current['ok_to_submit'] is not False
            or current['candidate_generated'] is not False or current['raster_sha256'] is not None
            or current['holdout_dti'] is not None or current['leaderboard_score_estimate'] is not None
            or context['candidate_generated'] is not False or context['ok_to_submit'] is not False
            or context['corrected_split_version'] != 'label-blind-quadrants-v3-feature-buffered'
            or not (lineage['25_and_30_identical_support'] and lineage['31_subset_of_25']
                    and lineage['32_subset_of_31'] and lineage['32_subset_of_36'])
            or len(context['rows']) != 4
            or any(not row['corrected_known_pixel_mask_preserved'] or not row['evaluation_geometry_unchanged']
                   or row['corrected_nearest_visible_to_any_held_component_px'] <= context['buffer_px']
                   for row in context['rows'])
            or card['verdict'] != 'negative' or card['ok_to_submit'] is not False
            or card['candidate_generated'] is not False or card['raster_sha256'] is not None
            or pre['status'] != 'BLOCKED' or pre['ok_to_submit'] is not False
            or pre['capacity']['feasible_by_capacity_only'] is not False
            or feature['status'] != 'FAIL_CLOSED'
            or [b['band'] for b in feature['bands']] != [13, 14]
            or any(b['status'] != 'FAIL_CLOSED' for b in feature['bands'])
            or s18['status'] != 'DUPLICATE_STOP' or s18['complete_registry_clearance'] is not False
            or s18['witness_sha256'] != pre['capacity']['reference_sha256']
            or s23['status'] != 'DUPLICATE_STOP' or s23['complete_registry_clearance'] is not False
            or s23['witness_sha256'] != pre['capacity']['reference_sha256']
            or s23['candidate_sha256'] != s23_prior['raster_sha256']
            or s23['candidate_sha256'] != card['concurrent_s23_historical_result']['sha256']
            or s23['directed_dot_overlap']['overlap_within_3px'] <= 0.70
            or s23_prior['ok_to_submit'] is not False
            or s23_inputs['status'] != 'FAIL_CLOSED'
            or [b['band'] for b in s23_inputs['bands']] != [6, 18]
            or s23_inputs['features_sha256'] != feature['features_sha256']
            or s23_semantics['input_sha256']['training_features_sha256'] != feature['features_sha256']
            or s23_semantics['band_06']['pearson_r_vs_mirror_bands']['band_4_TC'] < 0.99
            or prior['ok_to_submit'] is not False
            or len(audit['sites']) != 9
            or {r['site'] for r in audit['sites']} != {f'GEMSDOE{i}' for i in focus_sites}
            or any(r['protocol_unique_among_nine'] or r['organizer_confirmed_score'] is not None
                   or r['estimated_leaderboard_score'] is not None for r in audit['sites'])
            or official['is_submission_receipt'] is not False):
        raise ValueError('Current review evidence inconsistent; refusing to render')
    art, hold = prior['artifact'], prior['holdout']
    tif, zipped = art['tif'].removeprefix('docs/'), art['zip'].removeprefix('docs/')
    rows = []
    for r in sorted(audit['sites'], key=lambda row: -row['claimed_historical_value']):
        witness = r['max_overlap_vs_other_eight']
        if (recheck['files'][r['site']]['sha256'] != r['sha256']
                or abs(recheck['max_overlap_into_any_other_leader'][r['site']]
                       - witness['overlap_within_3px']) > 1e-12):
            raise ValueError('Corrected peer-only recheck differs from frozen evidence')
        rows.append(f'''<tr><th scope="row">{esc(r['site'])}</th><td class="file"><a href="{esc(r['source_url'],quote=True)}">{esc(r['filename'])}</a><small class="block">SHA-256 {esc(r['sha256'][:16])}…</small></td><td>{r['claimed_historical_value']:.4f}<small class="block">user-reported</small></td><td>Unavailable<small class="block">no receipt / calibration</small></td><td class="fail">NO<small class="block">{witness['overlap_within_3px']:.2%} vs {esc(witness['reference_site'])}</small></td></tr>''')
    feed_rows = []
    seen_focus = set()
    for r in focus['rows']:
        number = r['repository'].removeprefix('buffedlizard55-lab/GEMSDOE')
        site = 'GEMSDOE' + number
        if not number.isdigit() or int(number) in seen_focus:
            raise ValueError('Unexpected or duplicate focus repository')
        seen_focus.add(int(number))
        if r['status'] == 'FETCHED_GITHUB_SNAPSHOT' and not r.get('tree_truncated'):
            link = f'<a data-focus-link href="{esc(r["page_url"],quote=True)}">{esc(r["snapshot_commit"][:12])}</a>'
            detail = 'snapshot page'
        else:
            link = '<span data-focus-link>Unavailable</span>'
            detail = 'fetch incomplete'
        feed_rows.append(f'<li data-focus-site="{esc(number)}"><strong>{esc(site)}</strong> · {link}<small data-focus-detail>{detail}</small></li>')
    if seen_focus != focus_sites:
        raise ValueError('Focus feed must contain exactly the nine named sites')
    missing = feature['bands'][0]['masked_or_nonfinite_inside']
    if any(b['masked_or_nonfinite_inside'] != missing for b in feature['bands']):
        raise ValueError('Feature audit changed: review displayed count')
    bound = pre['capacity']['overlap_lower_bound']
    overlap = s18['directed_dot_overlap']['overlap_within_3px']
    hci = hold['ci95']
    body = f'''<section class="hero" data-submission-ready="false"><div>
<p class="eyebrow">GEMSDOE91 / HISTORICAL REVIEW · 27 OCTOBER 2026</p><h1>A clear stop,<br>backed by evidence.</h1>
<p class="lead">This earlier review generated no new candidate. The later S24 research artifact is shown above; neither review authorizes a submission.</p>
<p><span class="verdict">NOT OK TO SUBMIT · NO NEW TIFF IN THIS EARLIER REVIEW</span></p><p><a href="review-ad43b4e5/REVIEW.md">Read the earlier review ↗</a> · <a href="review-ad43b4e5/run-card.json" download>Download the JSON run card ↓</a> · <a href="submission-guide.html">Submission guide ↗</a></p></div>
<aside class="dark" aria-label="Current verdict"><p class="eyebrow" style="color:#b9ddc6">DECISION / FAIL CLOSED</p><h2>Research available.<br>Submission blocked.</h2>
<div class="statline"><span>Experiments in this earlier review</span><strong>0</strong></div><div class="statline"><span>Candidate from this earlier review</span><strong>NO</strong></div><div class="statline"><span>Weekly slots used in this review</span><strong>0</strong></div>
<p>The method paragraph is missing, and the frozen dot budget cannot pass the literal overlap rule. A separate selector would be required even for a future validated file.</p></aside></section>
<div class="note"><strong>Historical S22 OMTJ is scientifically compromised.</strong> Finite NoData cells entered both of its input bands. Its local format check is not scientific validation or organizer acceptance. <a href="review-8e8d86f2/feature-audit.json">See the input audit</a>.</div>
<div class="note"><strong>Holdout feature context was not buffered in the old shared split.</strong> We corrected the shared split and retained a separate pixel-exact scoring mask. Historical scores are not matched to the new instrument; no corrected geological score has been measured. <a href="review-ad43b4e5/context-buffer-audit.json">Geometry audit ↗</a>.</div>
<div class="note"><strong>Concurrent S23 research is also duplicate-stopped.</strong> Its saved dots overlap the pinned lattice by {s23['directed_dot_overlap']['overlap_within_3px']:.3%}; a band-identity conflict prevents validating the stated magnetic-tilt mechanism. This separate historical run is not a new candidate from this review. <a href="s23/executive-summary.html">S23 correction and evidence</a>.</div>
<section class="section" id="evidence"><div class="section-title"><h2>Three reasons to stop</h2><p>Each number is tied to reproducible evidence.</p></div><div class="cards">
<article class="card"><span class="eyebrow">FIXED PLAN / NECESSARY BOUND</span><div class="metric">{bound:.2%}</div><h3>Unavoidable overlap</h3><p>At 37,654 dots, at least this share lies within 3 px of the pinned lattice; the protocol stops above 70%. This is not a score or a uniqueness pass.</p><a href="review-8e8d86f2/experiment-preflight.json">Preflight receipt ↗</a></article>
<article class="card"><span class="eyebrow">S18 / DIRECT COMPARISON</span><div class="metric">{overlap:.3%}</div><h3>Overlap with the lattice</h3><p>{s18['directed_dot_overlap']['candidate_dots']:,} historical S18 dots were checked; the prior two-reference uniqueness claim is superseded.</p><a href="review-8e8d86f2/s18-witness.json">Duplicate witness ↗</a></article>
<article class="card"><span class="eyebrow">S22 / INPUT QUALITY</span><div class="metric">{missing:,}</div><h3>Missing cells per band</h3><p>In-footprint finite NoData sentinels in bands 13 and 14 contaminated the historical OMTJ feature calculation. No corrected run has been made.</p><a href="review-8e8d86f2/source-correction.json">Source correction ↗</a></article></div></section>
<section class="section" id="download"><div class="grid2"><div><span class="eyebrow">HISTORICAL DOWNLOAD / NOT A NEW CANDIDATE</span><h2>Inspect the artifact,<br>not a submission.</h2>
<p>The earlier S22 OMTJ raster remains available to reproduce the audit. It is a duplicate under the literal registry rule and its feature inputs are compromised. <strong>Do not upload the S22 file.</strong> This research download is not an approval to upload that file.</p>
<p>Historical <strong>HOLDOUT-DTI {hold['dti']:.6f}</strong>, 95% CI [{hci[0]:.6f}, {hci[1]:.6f}], {esc(hold['evaluator_version'])}, {hold['withheld_positive_pixels']:,} withheld positives: arithmetic retained for provenance only, not a valid test of the intended geology and not a leaderboard estimate.</p>
<p><a href="s22/run-card.json">Historical run receipt ↗</a> · <a href="run-card-S22-OMTJ.json">Historical compatibility card ↗</a> · <a href="s22-executive-summary.html">S22 archive ↗</a> · <a href="s18-unique-executive-summary.html">S18 correction ↗</a></p></div>
<div class="dark"><h3>OK TO DOWNLOAD: YES · RESEARCH ONLY</h3><p class="status-label" style="color:#ffcfb6">OK TO SUBMIT: NO</p><p>Single-band float32 GeoTIFF and one-file ZIP. Local re-read: finite [0,1] and pinned grid. Official acceptance is unknown.</p>
<a class="button" download href="{esc(tif,quote=True)}">Download historical TIFF ↓</a><a class="button secondary" download href="{esc(zipped,quote=True)}">Single-TIFF ZIP ↓</a>
<details><summary>Historical file identity</summary><p>Name: <code>{esc(prior['submission_name'])}</code><br>SHA-256: <code>{esc(prior['raster_sha256'])}</code></p><p>Historical note ({len(prior['submission_note'])}/140): <code>{esc(prior['submission_note'])}</code></p></details></div></div></section>
<section class="section" id="nine-sites"><div class="section-title"><h2>Nine historical leaders</h2><p>Claims, not organizer-confirmed results.</p></div><p>The user-reported GEMSDOE32 claim is highest among the nine supplied values; none of the nine files is unique against all eight peers. No defensible leaderboard estimate or file-linked receipt is available. Overlap is directional within 3 px.</p>
<div class="table-scroll"><table><caption>Exact historical files · 26 October raster audit · do not upload these references</caption><thead><tr><th scope="col">Site</th><th scope="col">Historical TIFF / source</th><th scope="col">Reported claim</th><th scope="col">Estimated score</th><th scope="col">Unique among peers?</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="subtle">Full SHA-256s and 72 directed comparisons: <a href="s22/nine-site-audit.json">original nine-site audit</a> and <a href="review-ad43b4e5/nine-site-recheck.json">corrected peer-only recheck</a>. GEMSDOE25 and GEMSDOE30 have identical positive support despite different bytes.</p></section>
<section class="section" id="research"><div class="grid2"><article class="card"><span class="eyebrow">WHAT 0.2778 MAY MEAN</span><h2>Coverage is plausible. Causality is not proven.</h2><p>GEMSDOE32 retains the GEMSDOE31 support after removing {lineage['31_minus_32']['pixels']:,} near-catalogue dots; GEMSDOE36 adds {lineage['36_minus_32']['pixels']:,} to it. Reducing redundant predictions may improve the coverage–false-positive trade-off, but new faults may also be nearby. The 0.2778 claim lacks a receipt, and file geometry cannot prove a score or causality. <a href="review-ad43b4e5/nine-site-lineage.json">Lineage audit ↗</a></p><p>The public rank-one observation was {official['public_rank_1_score']:.4f} on {esc(official['observed_date_utc'])} UTC; it can change and is not a file receipt.</p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Current official leaderboard ↗</a></article>
<article class="card"><span class="eyebrow">GEOLOGY / NEXT RESEARCH</span><h2>Four proposals from an earlier review.</h2><p>Ranked proposals considered cross-contact magnetic kurtosis, oriented terrain granulometry, cross-spectral lag, and conditional 3DEP terrain. S24 subsequently tested the first proposal; its result is negative. Volcanic contacts, survey seams, roads and fan margins can mimic faults.</p><p>A fault prediction is not proof of heat, permeability, a vent or a productive reservoir.</p><a href="review-8e8d86f2/HYPOTHESES.md">Layers, sources and falsification ↗</a></article></div></section>
<section class="section" id="how-to-submit"><span class="eyebrow">FUTURE APPROVED FILES ONLY</span><h2>What would have to happen before an upload?</h2><ol><li>Resolve the assigned method and frozen-plan conflict. Audit input masks and source rights; do not silently relax the registry rule.</li><li>Pass feature canaries, buffered whole-segment holdout and both registry phases, using the shared evaluator and writer. Compare against a matched incumbent with uncertainty.</li><li>Obtain a separate selector decision and check the authenticated competition page for current quota. The <a href="https://community.drivendata.org/t/submission-amount-question/11553/2">website limit prevails</a> over the rules’ parenthetical.</li><li>Only for an approved future file, verify its hash and upload the TIFF or one-TIFF ZIP on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData</a>. Record its receipt, timestamp, ID, score and hash; only a receipt supports ORGANIZER-CONFIRMED.</li></ol>
<p class="note">The all-finite local writer avoids numeric sentinels in [0,1], but the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official description</a> says null/NaN outside bounds. The user-reported range error is not proven resolved on the organizer server.</p></section>
<section class="section" id="feed"><span class="eyebrow">AUDITABLE SOURCE FEED / NO ORGANIZER SCORES</span><h2>Track the nine source repositories</h2><p>Frozen page inventory checked <strong>{esc(focus['checked_utc'])}</strong>. The page automatically checks public GitHub main commit heads on load; the button retries. It does not fetch rasters, scores or private receipts. Rate limits or network failures leave the dated snapshot visible.</p>
<button type="button" class="refresh" id="refresh-focus">Check live GitHub heads</button><p id="focus-status" class="feed-status" role="status" aria-live="polite">Showing saved GitHub page snapshots.</p><ul class="feed-list">{''.join(feed_rows)}</ul>
<p class="subtle"><a href="review-8e8d86f2/focus-inventory.json">Full saved inventory</a> · <a href="fleet-audit.json">Broader scheduled fleet inventory</a> · <a href="review-ad43b4e5/REVIEW.md">Official source and limitations ledger</a>. Daily Actions refreshes are automatically published only when Pages uses workflow deployment; branch-based Pages may show an older saved snapshot. No credentials are requested.</p><noscript><p>Live head checks require JavaScript; the dated inventory remains available above.</p></noscript></section>
<section class="section" id="archive"><span class="eyebrow">HISTORICAL EVIDENCE</span><h2>Earlier research, clearly archived</h2><p><a href="review-8e8d86f2/REVIEW.md">Previous review and full nine-site table</a> · <a href="archive-results.html">Historical experiment archive</a> · <a href="s23/executive-summary.html">S23 parallel research correction</a> · <a href="REVIEW-ARENA-52711765-20261027.md">Concurrent no-run review</a> · <a href="s17-lftg.html">S17-LFTG research audit</a> · <a href="s17-cpad.html">S17-CPAD research audit</a> · <a href="REVIEW-ACTIVE-E649E460-20261025.md">Earlier safety review</a> · <a href="run-card-E649E460-20261025.json">Earlier review card</a></p></section>'''
    guide = '''<section class="hero" data-submission-ready="false"><div><p class="eyebrow">SUBMISSION GUIDE / FUTURE APPROVED FILES ONLY</p><h1>Not ready to upload.</h1><p class="lead">No new TIFF was generated or approved in this review. Historical research downloads are not competition submissions.</p><p><a href="index.html">← Back to the executive review</a></p></div><aside class="dark"><h2>Current decision</h2><div class="statline"><span>New file</span><strong>NONE</strong></div><div class="statline"><span>Submission approval</span><strong>NO</strong></div><div class="statline"><span>Weekly slots used</span><strong>0</strong></div><p>No score estimate or file-specific organizer receipt is available.</p></aside></section>
<section class="section"><h2>Before a future candidate is eligible</h2><ol><li>Obtain an assigned method and a coordinated resolution of the frozen plan’s duplicate conflict. Do not evade the registry gate by silently changing the budget or omitting dense references.</li><li>Verify rights, masks and alignment of each input. Build all catalogue-derived features from buffered visible faults only; preserve the separate pixel-exact known-fault scoring mask.</li><li>Run feature-alone leakage canaries, stop on a suspicious AUC above 0.90, and compare both pre-placement surface and final dots against the full available frozen registry. A duplicate stop or missing coverage is not a pass.</li><li>Recompute both candidate and current best on the corrected matched whole-component holdout with the shared pooled DTI evaluator; report the version, positive count, 95% interval and paired comparison. A projection is not a score.</li><li>Reopen the written file using the shared validator: one float32 GeoTIFF, exact sample dimensions, transform and EPSG:32611, no NaN inside the footprint, values in [0,1]. Confirm the organizer’s current outside-bounds encoding before upload.</li><li>A separate selector must confirm approval and the live authenticated weekly allowance. Only then upload an approved future file via the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">official submissions page</a>, preserving its byte hash and organizer receipt.</li></ol>
<p class="note">The <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official description</a> says outside-bounds values are null/NaN; the historical all-finite file passed local checks only. We do not know whether that encoding is accepted by the organizer or what caused the prior range error.</p>
<p><a href="review-ad43b4e5/run-card.json" download>Download the negative JSON run card ↓</a> · <a href="review-ad43b4e5/REVIEW.md">Review and sources ↗</a></p></section>'''

    def shell(title, page_body=body):
        return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · GEMSDOE91</title><meta name="description" content="A fail-closed GEMS fault-mapping audit, nine-site evidence and research-only GeoTIFF download."><style>{STYLE}</style><script defer src="assets/focus-feed.js"></script></head><body><a class="skip" href="#main">Skip to content</a><div class="wrap"><header class="nav"><a class="brand" href="index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a><nav aria-label="Main navigation"><a href="index.html#evidence">Evidence</a><a href="index.html#nine-sites">Nine sites</a><a href="submission-guide.html">Submission guide</a><a href="index.html#feed">Source feed</a></nav></header><main id="main">{page_body}</main><footer><span>Maximize P(Win) · Own the Outcome<br>Research, not a leaderboard prediction.</span><span><a href="review-ad43b4e5/run-card.json">Current run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">Source repository</a><br>No automatic competition uploads or stored credentials.</span></footer></div></body></html>\n'''
    (DOCS / 'review-8e8d86f2-index-src.html').write_text(shell('Current research verdict'), encoding='utf-8')
    (DOCS / 'review-8e8d86f2-exec-src.html').write_text(shell('Executive review and submission guidance'), encoding='utf-8')
    (DOCS / 'submission-guide.html').write_text(shell('Future submission guide', guide), encoding='utf-8')


if __name__ == '__main__':
    render_sources()
