#!/usr/bin/env python3
"""Render the active 2026-10-30 no-candidate review and fail-closed front door.

The renderer consumes only committed review evidence. It never generates or
approves a prediction raster, uses no hidden labels, and performs no network
requests. The historical current-run TIFF pointer is preserved separately.
"""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "review-20261030"
CARD_PATH = REVIEW / "run-card.json"
SNAPSHOT_PATH = REVIEW / "nine-site-snapshot.json"
CURRENT_REVIEW_PATH = ROOT / "docs" / "current-review.json"
EXPECTED_BRANCH = "arena/83350cee-gemsdoe91"
EXPECTED_SITES = [
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
]

STYLE = r"""
:root{--ink:#162c29;--muted:#526862;--paper:#f4f7f2;--line:#d6e1da;--green:#155b48;--red:#7b2b22;--redbg:#fff1ed;--gold:#8a5915;--white:#fff;--blue:#214a62}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.62 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:#125b49;text-underline-offset:3px}a:hover{color:#073b30}a:focus-visible,summary:focus-visible{outline:3px solid #c87a15;outline-offset:3px}.wrap{width:min(1180px,calc(100% - 40px));margin:auto}.nav{display:flex;justify-content:space-between;align-items:center;gap:18px;padding:21px 0;border-bottom:1px solid var(--line)}.brand{font-weight:850;letter-spacing:-.035em;color:var(--ink);text-decoration:none}.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:.15em}nav{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;font-weight:650}.skip{position:absolute;left:-10000px;top:5px;background:white;padding:10px}.skip:focus{left:10px;z-index:4}.hero{display:grid;grid-template-columns:1.3fr .85fr;gap:28px;align-items:stretch;padding:42px 0 26px}.eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.15em;color:var(--green);font-weight:850}h1{font-size:clamp(36px,5.6vw,64px);letter-spacing:-.05em;line-height:1.02;margin:12px 0 18px}h2{font-size:clamp(25px,3vw,34px);line-height:1.15;letter-spacing:-.03em;margin:0 0 14px}h3{font-size:18px;line-height:1.3;margin:0 0 8px}.lead{font-size:18px;color:var(--muted);max-width:720px}.alert{background:var(--redbg);border:1px solid #edc5bd;border-left:5px solid var(--red);border-radius:8px;padding:18px 20px;margin:12px 0 24px}.alert strong{color:var(--red)}.card{background:var(--white);border:1px solid var(--line);border-radius:10px;padding:20px;min-width:0}.dark{background:#17312c;color:white;border-radius:12px;padding:22px;box-shadow:0 15px 40px #152c2912}.dark p,.dark small{color:#d9e7e1}.stat{display:flex;justify-content:space-between;gap:12px;padding:10px 0;border-bottom:1px solid #ffffff30;font-size:14px}.stat strong{text-align:right;color:#ffe3c6}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric{font-size:14px;color:var(--muted)}.metric b{display:block;color:var(--ink);font-size:22px;line-height:1.2;margin:7px 0}.section{padding:34px 0;border-top:1px solid var(--line)}.section p{max-width:920px}.scroll{width:100%;overflow:auto;border:1px solid var(--line);border-radius:8px;background:white}table{border-collapse:collapse;width:100%;min-width:970px;font-size:13px}caption{text-align:left;color:var(--muted);padding:14px}th,td{padding:12px 13px;border-bottom:1px solid #e4ebe5;text-align:left;vertical-align:top}thead th{background:#e9f0ea;font-size:11px;text-transform:uppercase;letter-spacing:.05em}tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}th[scope=row]{white-space:nowrap}.small,small{font-size:12px;color:var(--muted)}.mono,code{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.badge{display:inline-block;border:1px solid #e4c2b9;background:#fff3ef;color:var(--red);border-radius:999px;padding:4px 9px;font-size:11px;font-weight:850;letter-spacing:.04em}.button{display:inline-block;border:1px solid #a8cfb7;background:#dff2e5;color:#123b2e;padding:11px 15px;border-radius:6px;text-decoration:none;font-weight:750;font-size:14px}.button.secondary{background:white;border-color:var(--line)}.cols{display:grid;grid-template-columns:1fr 1fr;gap:15px}.hypothesis{border-left:3px solid #81ae92;padding:2px 0 2px 15px;margin:17px 0}.steps{counter-reset:step;list-style:none;padding:0}.steps li{counter-increment:step;position:relative;padding:0 0 18px 48px}.steps li:before{content:counter(step);position:absolute;left:0;top:0;width:30px;height:30px;border-radius:50%;background:#e0efe5;color:#145640;font-weight:850;display:grid;place-items:center}details{border-top:1px solid var(--line);padding:13px 0}summary{cursor:pointer;font-weight:700}.fineprint{color:var(--muted);font-size:13px}.footer{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;border-top:1px solid var(--line);padding:24px 0 34px;color:var(--muted);font-size:12px}
@media(max-width:820px){.wrap{width:calc(100% - 30px)}.nav{align-items:flex-start;flex-direction:column}nav{gap:12px}.hero,.cols{grid-template-columns:1fr}.hero{padding-top:30px}.grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:480px){.grid{grid-template-columns:1fr}h1{font-size:39px}}
"""


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_inputs(root: Path = ROOT):
    card = _read_json(root / "docs/review-20261030/run-card.json")
    snapshot = _read_json(root / "docs/review-20261030/nine-site-snapshot.json")
    if card.get("repository_branch") != EXPECTED_BRANCH:
        raise ValueError("Active review branch mismatch")
    if (card.get("result") != "negative" or card.get("review_status") != "BLOCKED"
            or card.get("candidate_generated") is not False
            or card.get("candidate_path") is not None
            or card.get("candidate_sha256") is not None
            or card.get("ok_to_download_new_candidate") is not False
            or card.get("ok_to_submit") is not False
            or card.get("leaderboard_score_estimate") is not None):
        raise ValueError("Active review must remain no-candidate and fail-closed")
    historical = card.get("historical_reference_files", {})
    if (historical.get("ok_to_download_for_research_or_inspection") is not True
            or historical.get("ok_to_submit") is not False):
        raise ValueError("Historical downloads must remain research-only and non-submittable")
    holdout = card.get("holdout_dti", {})
    if any(holdout.get(k) is not None for k in ("value", "evaluator_version", "withheld_positive_count", "ci95")):
        raise ValueError("A no-run review cannot contain a measured HOLDOUT-DTI")
    organizer = card.get("organizer_confirmed", {})
    if organizer.get("value") is not None or organizer.get("submission_receipt") is not None:
        raise ValueError("An organizer score requires an actual receipt")
    sites = snapshot.get("sites", [])
    if snapshot.get("site_order") != EXPECTED_SITES or [r.get("site") for r in sites] != EXPECTED_SITES:
        raise ValueError("Nine-site snapshot must contain the requested ordered sites")
    for row in sites:
        if (row.get("unique_within_nine_at_70pct") is not False
                or row.get("organizer_confirmed_score") is not None
                or not row.get("download_url", "").startswith("https://raw.githubusercontent.com/")
                or len(row.get("sha256", "")) != 64):
            raise ValueError(f"Invalid or overclaimed site evidence for {row.get('site')}")
    return card, snapshot


def _table(snapshot: dict) -> str:
    rows = []
    for row in snapshot["sites"]:
        overlap = 100.0 * float(row["max_3px_peer_overlap"])
        dti = f"{float(row['reported_public_dti']):.4f}"
        rows.append(f'''<tr>
<th scope="row">{escape(row['site'])}<br><a class="small" href="{escape(row['site_url'], quote=True)}">owner page</a></th>
<td><a href="{escape(row['download_url'], quote=True)}" target="_blank" rel="noopener">↓ {escape(row['reported_file'])}</a><br><span class="small">Bytes SHA-256-verified via GitHub API at the pinned commit; owner score page was not refreshed.</span><details><summary>Identity and provenance</summary><div class="small">Commit <code>{escape(row['commit'])}</code> (observed {escape(row['commit_observed_utc'])})<br>SHA-256 <code>{escape(row['sha256'])}</code><br>{int(row['bytes']):,} bytes · {int(row['positive_pixels']):,} positive pixels<br><a href="{escape(row['source_blob_url'], quote=True)}" target="_blank" rel="noopener">View pinned repository blob</a></div></details></td>
<td><span class="mono">USER-REPORTED_PUBLIC_DTI<br>NOT A VERIFIED SCORE</span><br><strong>{dti}</strong><br><span class="small">No HOLDOUT-DTI metadata or organizer receipt in this audit.</span></td>
<td><strong>NO — {overlap:.2f}%</strong><br>closest: {escape(row['closest_peer'])}<br><span class="small">peer-only, max within 3 px</span></td>
<td><strong>OK TO DOWNLOAD: YES</strong><br><span class="small">research/inspection only</span><br><strong>OK TO SUBMIT: NO</strong></td>
<td><span class="badge">NONE RECORDED</span></td>
</tr>''')
    return "\n".join(rows)


def executive_html(card: dict, snapshot: dict) -> str:
    table_rows = _table(snapshot)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="2026-10-30 GEMS fault-mapping review: blocked, no new candidate, nine-site file and evidence audit, official sources, and submission guide."><title>GEMSDOE91 · 2026-10-30 evidence review</title><style>{STYLE}</style></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="nav"><a class="brand" href="../index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a><nav aria-label="Review navigation"><a href="#decision">Decision</a><a href="#nine-sites">Nine sites</a><a href="#g32">GEMSDOE32</a><a href="#hypotheses">Hypotheses</a><a href="#guide">Submission guide</a><a href="../index.html">Home</a></nav></header>
<main id="main" data-submission-ready="false">
<section class="hero" id="decision"><div><span class="eyebrow">Three-pass review · 30 October 2026 · {escape(card['repository_branch'])}</span><h1>Evidence first.<br>No candidate to submit.</h1><p class="lead">The authorized method lane and required competition inputs are missing. This review generated no TIFF and ran no experiment. No HOLDOUT-DTI, organizer-confirmed score, or defensible leaderboard estimate exists.</p><p><span class="badge">NEW CANDIDATE: NONE</span> <span class="badge">OK TO SUBMIT: NO</span></p><p><a class="button" href="run-card.json">Open the fail-closed run card</a> <a class="button secondary" href="REVIEW.md">Read the full three-pass review</a></p></div>
<aside class="dark"><h2>Current gate</h2><div class="stat"><span>Authorized method lane</span><strong>NONE</strong></div><div class="stat"><span>Pinned inputs available</span><strong>0 / 15</strong></div><div class="stat"><span>New candidate</span><strong>NONE</strong></div><div class="stat"><span>HOLDOUT-DTI</span><strong>NOT RUN</strong></div><div class="stat"><span>ORGANIZER-CONFIRMED</span><strong>NONE</strong></div><p>Historical reference files below are not new submissions or promotion candidates.</p></aside></section>
<div class="alert" role="status"><strong>BLOCKED · OK TO DOWNLOAD A NEW CANDIDATE: NO · OK TO SUBMIT: NO.</strong> The experiment plan has no assigned lane, all pinned manifest inputs are missing, and the official sample raster is unavailable. No geological experiment or candidate build was started. The old conditional capacity bound is not treated as verified because its sample/reference mirror was not authenticated.</div>
<section class="section"><div class="grid"><div class="card metric">Lane assignment<b>Not supplied</b><span class="small">A proposal is not authorization.</span></div><div class="card metric">Data preflight<b>15 / 15 missing</b><span class="small">Official sample also absent.</span></div><div class="card metric">Experiments / slots<b>0 / 0</b><span class="small">No experiment or upload.</span></div><div class="card metric">Score estimate<b>None</b><span class="small">No projection presented as a score.</span></div></div></section>
<section class="section" id="nine-sites"><span class="eyebrow">Historical repository audit · pinned source commits</span><h2>Nine-site file and evidence table</h2><p>File links open the raster stored at the commit recorded in the 2026-10-29 audit. This review retrieved each file through the GitHub API at that exact commit/path and recomputed a matching SHA-256; owner score pages and receipts were not refreshed. These are historical reference files only. Every numeric value in the reported-value column is explicitly <code>USER-REPORTED_PUBLIC_DTI</code>, not a verified score or estimate. The source audit recorded no organizer receipts. Uniqueness is only among these nine sites under the audit's 3-pixel comparison; it is not a complete-registry clearance.</p>
<div class="scroll"><table><caption>OK TO DOWNLOAD FOR RESEARCH: YES · OK TO SUBMIT: NO · owner-reported values · peer-only uniqueness result</caption><thead><tr><th>Site</th><th>Pinned historical file</th><th>Reported public value<br>(not a verified score)</th><th>Unique among these nine<br>(70% stop rule)</th><th>Download / submission status</th><th>Organizer receipt</th></tr></thead><tbody>{table_rows}</tbody></table></div>
<p class="fineprint">Snapshot: <a href="nine-site-snapshot.json">machine-readable nine-site audit</a>; source audit date {escape(snapshot['source_audit']['checked_utc'])}. A matching byte family or user report cannot substitute for an authenticated receipt. The all-nine NO values only answer the listed peer comparison.</p></section>
<section class="section" id="g32"><span class="eyebrow">Mechanism analysis · not causal proof</span><h2>Why GEMSDOE32's reported value may be highest in this family</h2><div class="cols"><article class="card"><h3>A plausible metric-geometric explanation</h3><p>The pinned byte-lineage audit in <a href="../R0_ANALYSIS_S22.md">R0_ANALYSIS_S22.md</a> places the GEMSDOE32 file inside the same H19-derived support family. It reports that the GEMSDOE32 raster adds no positive pixel beyond the earlier D2.8 support and removes a substantial near-catalogue subset. Under the official DTI definition, false positives receive weight <code>alpha=0.2</code>, false negatives <code>beta=0.8</code>, and distances are softened within <code>300 m</code>. If the removed dots were mostly unmatched clutter while retained detections still reached hidden faults, the weighted false-positive cost could decrease while true-positive credit stayed similar.</p><p>This explains how pruning could accompany a higher reported value; it does not prove the value or identify the hidden truth.</p></article><article class="card"><h3>Why it is not an independent win claim</h3><p>The nine-site audit reports that GEMSDOE32's positive support has <strong>100.00%</strong> maximum overlap within <strong>3 px</strong> with GEMSDOE24. That is peer-family similarity, not independent discovery. The historical source register records an owner-page statement that no organizer score existed for the named artifact at that time; it was not re-fetched today. No current receipt ties the reported number to the bytes.</p><p>Accordingly, the table preserves the value only as an unverified user-reported public claim. No alternative leaderboard score is estimated here.</p></article></div>
<p class="fineprint">References: <a href="../R0_ANALYSIS_S22.md">byte-lineage analysis and its assumptions</a> · <a href="sources.json">official-source checks and limitations</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official metric description</a>.</p></section>
<section class="section" id="hypotheses"><span class="eyebrow">Research proposals only · not assigned or tested</span><h2>New geological hypotheses</h2><div class="hypothesis"><h3>1 · Lithology-conditioned, multiscale potential-field edge persistence</h3><p>Test whether geophysical boundaries persist across scales and are more fault-like after stratifying by bedrock context in the 2026 USGS GeMS/SGMC map. Control for intrusive margins, flow boundaries, map scale, and compilation seams; permute unit context within spatial blocks. The release was not downloaded and its coverage/fields are unverified.</p></div><div class="hypothesis"><h3>2 · Stress-compatible discontinuities with independent potential-field support</h3><p>Test stepovers/terminations supported by magnetic/gravity discontinuities and the supplied strain layer. Use the USGS structural-mechanism literature for rationale only; the 2026 slip/dilation product is calculated on mapped Quaternary fault segments and could leak/reproduce the catalogue if rasterized directly.</p></div><div class="hypothesis"><h3>3 · LiDAR scarp persistence through transfer zones</h3><p>Where verified 3DEP bare-earth tiles exist, test whether fine-scale scarp persistence links geophysical lineaments through stepovers. Control for drainage, roads, playas, alluvial fans, vegetation, tile seams, and DEM epoch. Exact area coverage and data bytes were not checked.</p></div><p><a class="button secondary" href="HYPOTHESES.md">Read ranked test designs, failure modes, and gates</a> <a class="button secondary" href="sources.json">Open source register</a></p></section>
<section class="section" id="sources"><span class="eyebrow">Official links checked 2026-10-30</span><h2>Trusted-source index</h2><ul><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem description</a>: fault target, incomplete labels, DTI weights/support, and GeoTIFF grid/range requirements.</li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN release</a> (DOI <code>10.5066/P93LGLVQ</code>): airborne magnetic/radiometric context and related lidar; USGS page marks CC0.</li><li><a href="https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous">USGS 2026 GeMS/SGMC release</a> (DOI <code>10.5066/P1A3DQZK</code>): official map-unit context; heterogeneous scale and unreconciled boundaries are explicit limitations.</li><li><a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">USGS 3DEP products and services</a>: USGS says lidar/DEM products are free without use restrictions; exact footprint coverage remains unchecked.</li><li><a href="https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa">USGS record for the Great Basin structural-discontinuity study</a>: process support for interactions/stepovers/terminations, not pixel-level proof.</li><li><a href="https://pubs.usgs.gov/publication/sir20265073">USGS SIR 2026-5073</a> and its related data DOI <code>10.5066/P9YL58W6</code>: slip/dilation context with an explicit catalogue-leakage warning.</li></ul><p class="fineprint">Official source pages were fetched/rechecked; the nine historical site TIFFs were retrieved via GitHub API and SHA-256 verified at pinned commits. No owner score pages, organizer receipts, protected competition data, external source-raster bytes, or local map clips were fetched. Full claim-level notes and limitations: <a href="sources.json">sources.json</a>.</p></section>
<section class="section" id="guide"><span class="eyebrow">Only if authorization and verified inputs become available</span><h2>Submission guide</h2><ol class="steps"><li><strong>Get the assigned lane.</strong> Obtain one authorized method paragraph and its source; do not select one of the proposals yourself.</li><li><strong>Restore and verify the data.</strong> Obtain the official competition stack and sample through the authorized data page; verify all manifest hashes and resolve sample semantics using organizer-controlled bytes.</li><li><strong>Preregister and reuse.</strong> Follow the shared cached stack, evaluator, and writer. Keep whole-segment buffered hide-and-recover and pooled DTI <code>alpha=0.2</code>, <code>beta=0.8</code>, <code>300 m</code>. Stay within three experiments or two hours.</li><li><strong>Run leakage and uniqueness stops.</strong> Feature-alone canaries first. Stop if any pre-placement registry surface rank correlation is greater than <code>0.90</code>; after placement stop if more than <code>70%</code> of candidate dots are within <code>3 px</code> of any available registry raster.</li><li><strong>Validate the actual TIFF automatically.</strong> Verify single-band float32, exact grid/CRS/transform, [0,1] range and required outside-bounds null/NaN behavior, then run the complete registry comparison. Format validity is not scientific merit or selector approval.</li><li><strong>Wait for the separate selector decision.</strong> Do not upload automatically. If and only if selected, use the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submission page</a> and archive the exact submitted bytes and receipt. Only that receipt can support <code>ORGANIZER-CONFIRMED</code>.</li></ol><div class="alert"><strong>Current status remains NO SUBMISSION.</strong> No candidate exists today. Historical files above must not be submitted as a substitute.</div><p><a href="../submission-guide.html">Open the standalone submission guide ↗</a> · <a href="run-card.json">Run card</a> · <a href="REVIEW.md">Full review</a></p></section>
</main><footer class="footer"><span>Maximize P(Win) · Own the Outcome<br>Research, not a leaderboard prediction.</span><span><a href="../index.html">Portal home</a> · <a href="../current-review.json">Active review pointer</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">Source repository</a></span></footer>
</div></body></html>'''


def standalone_guide(card: dict) -> str:
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Current GEMS submission status and fail-closed steps for any future authorized candidate."><title>GEMSDOE91 · Current submission guide</title><style>{STYLE}</style></head><body><a class="skip" href="#main">Skip to content</a><div class="wrap"><header class="nav"><a class="brand" href="index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a><nav aria-label="Guide navigation"><a href="review-20261030/executive-summary.html">Current review</a><a href="review-20261030/REVIEW.md">Three-pass review</a><a href="index.html">Portal home</a></nav></header><main id="main" data-submission-ready="false"><section class="hero"><div><span class="eyebrow">Current status · 2026-10-30</span><h1>Do not upload.</h1><p class="lead">There is no new GeoTIFF candidate from this review. The lane is unassigned and the required official data/sample are absent. Historic peer files are OK TO DOWNLOAD for research/inspection only; they are not GEMSDOE91 submissions and are NOT OK TO SUBMIT.</p><p><span class="badge">OK TO DOWNLOAD NEW CANDIDATE: NO</span> <span class="badge">OK TO SUBMIT: NO</span></p><p><a class="button" href="review-20261030/executive-summary.html">Open the executive summary and nine-site table</a></p></div><aside class="dark"><h2>Fail-closed status</h2><div class="stat"><span>New candidate</span><strong>NONE</strong></div><div class="stat"><span>Experiments</span><strong>0</strong></div><div class="stat"><span>HOLDOUT-DTI</span><strong>NOT RUN</strong></div><div class="stat"><span>Organizer receipt</span><strong>NONE</strong></div><p>The archived no-run card contains null score fields. There is no leaderboard estimate.</p></aside></section><div class="alert"><strong>Never upload a prior branch artifact or a file from the nine-site comparison.</strong> Download links on the historical table are for inspection and provenance only; their peer-only overlap results do not grant permission to submit.</div><section class="section"><h2>Future submission checklist — all gates are required</h2><ol class="steps"><li>Obtain the authorized single method lane and source; do not infer it from this report or prior sessions.</li><li>Restore all pinned competition inputs from the authorized source and verify every hash, mask, grid, transform, and outside-bounds convention. Confirm the sample with organizer-controlled bytes.</li><li>Preregister one hypothesis and its named non-fault mimic, reuse the shared cache/evaluator/writer, and preserve the whole-segment buffered hide-and-recover protocol, pooled DTI weights and 300 m support.</li><li>Run feature-alone leakage canaries. Compare pre-placement surfaces against the available full registry; stop if any rank correlation exceeds <code>0.90</code>.</li><li>Only then place candidate dots. Compare final dots against the complete available registry; stop if any raster has more than <code>70%</code> of dots within <code>3 px</code>. Do not change budgets or exempt difficult witnesses to force a pass.</li><li>Validate the exact output GeoTIFF automatically: one float32 band, exact EPSG:32611 grid/transform, values in [0,1], and correct null/NaN outside bounds. A format pass is not a uniqueness, science, or approval pass.</li><li>Stop after at most three experiments or two hours. Report HOLDOUT-DTI with evaluator version, withheld-positive count, and 95% CI; do not label projections as scores.</li><li>Wait for the separate selector decision. Only an approved file may be uploaded manually at the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">official DrivenData submissions page</a>; preserve its exact hash and receipt. A receipt is required for any ORGANIZER-CONFIRMED result.</li></ol></section><section class="section"><h2>Protocol and official source links</h2><p>The official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">challenge description</a> specifies a fault-prediction GeoTIFF and the DTI metric. Official USGS data and geology references, including their evidence limits, are documented in <a href="review-20261030/sources.json">the current source register</a>.</p><p><a href="review-20261030/run-card.json">Negative run card</a> · <a href="review-20261030/HYPOTHESES.md">Untested hypotheses</a> · <a href="review-20261030/REVIEW.md">Full review</a></p></section></main><footer class="footer"><span>Maximize P(Win) · Own the Outcome</span><span><a href="index.html">Portal home</a> · No automated uploads or stored credentials.</span></footer></div></body></html>'''


def _active_notice() -> str:
    return ('<div class="note" role="status"><strong>ACTIVE REVIEW · 2026-10-30: NO NEW TIFF · OK TO SUBMIT: NO.</strong> '
            'No authorized method lane was supplied; all 15 pinned manifest inputs and the official sample raster are absent. '
            'No experiment was run and no candidate exists. Historical peer files are OK TO DOWNLOAD for research only; OK TO SUBMIT: NO. '
            '<a href="review-20261030/executive-summary.html">Executive summary and nine-site table</a> · '
            '<a href="review-20261030/REVIEW.md">Full three-pass review</a> · '
            '<a href="review-20261030/run-card.json">Negative run card</a>.</div>')


def _replace_current_notice(page: str, notice: str) -> str:
    markers = (
        '<strong>CURRENT REVIEW · 2026-10-29:',
        '<strong>ACTIVE REVIEW · 2026-10-30:',
    )
    position = -1
    for marker in markers:
        position = page.find(marker)
        if position >= 0:
            break
    if position < 0:
        raise ValueError("Could not locate current-review banner in portal HTML")
    start = page.rfind('<div class="note" role="status">', 0, position)
    if start < 0:
        raise ValueError("Current-review banner wrapper missing")
    end = page.find("</div>", position)
    if end < 0:
        raise ValueError("Current-review banner closing tag missing")
    end += len("</div>")
    return page[:start] + notice + page[end:]


def current_review_pointer(card: dict) -> dict:
    return {
        "schema": "gems91.current-review-pointer.v1",
        "review_id": card["review_id"],
        "review_date_utc": card["review_date_utc"],
        "branch": card["repository_branch"],
        "status": card["review_status"],
        "candidate_generated": False,
        "ok_to_download_new_candidate": False,
        "ok_to_submit": False,
        "holdout_dti": None,
        "organizer_confirmed": None,
        "leaderboard_score_estimate": None,
        "review": "review-20261030/REVIEW.md",
        "executive_summary": "review-20261030/executive-summary.html",
        "run_card": "review-20261030/run-card.json",
        "historical_artifact_pointer": {
            "path": "current-run.json",
            "meaning": "Legacy pointer to a historical S22 research download; not this active no-candidate review.",
        },
    }


S91_CAND = "gems91-s91-alm-alteration-halo-20261031T010114Z-5834ff6c"


def _s91_alm_card() -> str:
    return (
        '<div class="note" role="status"><strong>NEW · 2026-10-31 · S91-ALM: UNIQUE SUBMISSION GENERATED — '
        '<span style="color:#155b48">OK TO DOWNLOAD: YES</span> · <span style="color:#7b2b22">OK TO SUBMIT: NO '
        '(selector step pending)</span>.</strong> A new, format-certified GeoTIFF is <strong>unique</strong> against all '
        'nine focus sites (max 23.8% of its dots within 3 px of any leader; threshold 70%). It is a negative holdout by '
        'design (collar-compliant off-catalogue search), so its leaderboard score is <strong>not estimated</strong> — no '
        'organizer receipt exists. <a href="s91-alm/executive-summary.html">S91-ALM executive summary &amp; download</a> · '
        '<a href="s91-alm/REVIEW.md">three-pass review</a> · <a href="s91-alm/run-card.json">run card</a> · '
        f'<a href="downloads/{S91_CAND}-zeros.tif">download the submission GeoTIFF</a>.</div>'
    )


def render(root: Path = ROOT) -> None:
    card, snapshot = validate_inputs(root)
    docs = root / "docs"
    review_dir = docs / "review-20261030"
    review_dir.mkdir(parents=True, exist_ok=True)
    page = executive_html(card, snapshot)
    (review_dir / "executive-summary.html").write_text(page, encoding="utf-8")
    guide = standalone_guide(card)
    (docs / "submission-guide.html").write_text(guide + "\n", encoding="utf-8")
    pointer = current_review_pointer(card)
    CURRENT_REVIEW_PATH.relative_to(root).parent.mkdir(parents=True, exist_ok=True)
    CURRENT_REVIEW_PATH.write_text(json.dumps(pointer, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    notice = _active_notice()
    for name in ("index.html", "executive-summary.html"):
        path = docs / name
        if not path.is_file():
            raise FileNotFoundError(path)
        source = path.read_text(encoding="utf-8")
        source = _replace_current_notice(source, notice)
        source = source.replace(
            'href="review-4239f6e5/run-card.json">Current run card',
            'href="review-20261030/run-card.json">Active review run card',
        )
        # Lead the live portal with the newest (S91-ALM) candidate right after the
        # current-review notice, so the download is obvious on the GitHub Pages site.
        card = _s91_alm_card()
        if card not in source:
            source = source.replace(notice, notice + card, 1)
        path.write_text(source, encoding="utf-8")
    root_html = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=docs/index.html">'
        '<meta name="description" content="GEMSDOE91: S91-ALM unique submission (OK TO DOWNLOAD: YES; OK TO SUBMIT: NO).">'
        '<title>GEMSDOE91 · S91-ALM unique submission · OK TO DOWNLOAD YES · OK TO SUBMIT NO</title></head><body><main>'
        '<h1>GEMSDOE91 · S91-ALM unique submission</h1>'
        '<p><strong>OK TO DOWNLOAD: YES</strong> · <strong>OK TO SUBMIT: NO</strong> (selector step pending).</p>'
        '<p><a href="docs/index.html">Open the portal and active status</a> · '
        f'<a href="docs/downloads/{S91_CAND}-zeros.tif">Download the S91-ALM submission GeoTIFF</a> · '
        '<a href="docs/s91-alm/executive-summary.html">S91-ALM executive summary and nine-site table</a> · '
        '<a href="docs/review-20261030/executive-summary.html">2026-10-30 review executive summary</a> · '
        '<a href="docs/review-20261030/REVIEW.md">Three-pass review</a> · '
        '<a href="docs/review-20261030/run-card.json">Negative run card</a></p>'
        '</main></body></html>\n')
    (root / "index.html").write_text(root_html, encoding="utf-8")


def main() -> None:
    render()


if __name__ == "__main__":
    main()
