#!/usr/bin/env python3
"""Current, evidence-derived S16 portal. Historical research is not the homepage.

Called last by the shared renderer so daily feed refreshes cannot restore a
stale 'submit YES' banner. The template verification is automated, not visual.
"""
from __future__ import annotations
from html import escape as esc
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.verify_s16 import verify
from gems91.readiness import gates

CSS = '''
.s16-top{display:flex;justify-content:space-between;align-items:center;padding:27px 0;border-bottom:1px solid var(--line);gap:22px}.s16-logo{display:flex;gap:12px;align-items:center;text-decoration:none;color:var(--ink);font-weight:760}.s16-monogram{background:var(--ink);color:#d5efda;border-radius:9px;width:43px;height:43px;display:grid;place-items:center;font-size:21px}.s16-logo small{display:block;font-size:10px;letter-spacing:2px;font-weight:500;color:var(--muted)}.s16-top nav{gap:22px}.s16-hero{padding:54px 0 25px;display:grid;grid-template-columns:1.15fr 1fr;gap:55px;align-items:center}.s16-hero h1{font-size:clamp(38px,5vw,58px);line-height:1.12}.s16-hero .lead{font-size:17px}.s16-card{border-radius:12px;padding:28px;background:white;border:1px solid var(--line);min-width:0}.s16-download{background:#17312e;color:#fff;box-shadow:0 18px 32px #17312e12}.s16-download h2{color:white;font-size:28px}.s16-download .eyebrow{color:#bbd4c7}.s16-download .small{color:#c3d8d0}.s16-download a{color:#def1e3}.s16-download .button{width:100%;text-align:center;margin-top:18px}.s16-status{display:flex;justify-content:space-between;gap:15px;padding:12px 0;border-bottom:1px solid #ffffff27;font-size:13px}.s16-status strong{color:#d1eecf}.s16-status .warn{color:#ffccb4}.s16-badges{display:flex;gap:10px;flex-wrap:wrap;margin:23px 0 10px}.s16-mini{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);font-weight:750}.s16-metric{font-size:34px;line-height:1.3;letter-spacing:-1px;font-weight:650;margin:10px 0}.s16-note{padding:18px 22px;margin:12px 0 26px;border:1px solid #ddcbbb;border-left:4px solid var(--warn);border-radius:7px;background:#fff4eb;font-size:14px}.s16-section{padding:35px 0}.s16-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.s16-split{display:grid;grid-template-columns:1fr 1fr;gap:24px}.s16-figure{margin:0;background:#e8eee8;border:1px solid var(--line);padding:15px;border-radius:12px;text-align:center}.s16-figure img{max-width:100%;height:auto;max-height:430px;object-fit:contain}.s16-figure figcaption{font-size:12px;color:var(--muted);padding:10px 5px}.s16-step{padding:20px 0;border-bottom:1px solid var(--line)}.s16-step h3{font-size:18px}.s16-pill{border:1px solid var(--line);background:white;padding:5px 12px;border-radius:99px;font-size:12px;display:inline-block;margin:3px}.s16-hero>div,.s16-split>div,.s16-split>figure{min-width:0;overflow-wrap:anywhere}.s16-foot{margin-top:30px;border-top:1px solid var(--line)}.s16-details{border:1px solid var(--line);border-radius:8px;padding:18px;margin:20px 0}.s16-details summary{cursor:pointer;font-weight:700}.copyrow button{white-space:nowrap;flex:0 0 auto}.copyrow textarea{min-width:0}.s16-subtitle{font-size:13px;color:var(--muted)}.s16-buttons{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-top:14px;font-size:13px}.s16-live{display:inline-flex;align-items:center;gap:7px;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted)}.s16-live:before{content:'';display:block;width:6px;height:6px;border-radius:50%;background:#4e8763}tbody .bad{white-space:nowrap}@media(max-width:800px){.s16-hero,.s16-split,.s16-grid{grid-template-columns:1fr}.s16-hero{padding-top:35px;gap:25px}.s16-top{align-items:flex-start;flex-direction:column}.s16-top nav{gap:18px}.s16-card{padding:23px}.s16-metric{font-size:32px}.s16-figure img{max-height:350px}}
'''


def load(name):
    return json.loads((ROOT / 'docs' / name).read_text())


def page(title, content, card):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · GEMSDOE91</title><meta name="description" content="A freshly generated, format-checked GeoTIFF with automated scientific gates. Research download available; not approved for competition submission.">
<link rel="stylesheet" href="assets/portal.css"><link rel="stylesheet" href="assets/s16.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="s16-top"><a class="s16-logo" href="index.html"><span class="s16-monogram" aria-hidden="true">91</span><span>GEMSDOE<small>FAULT DISCOVERY LAB</small></span></a>
<nav aria-label="Main"><a href="index.html">Current candidate</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Research &amp; sources</a><a href="archive-results.html">Archive</a></nav></header>
<main id="main">{content}</main><footer class="s16-foot"><div>Maximize P(Win). Own the outcome.<br>One measured experiment · no competition slot used.</div><div><a href="run-card-S16.json">JSON run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">Source code</a><br>Experiment completed {esc(card['completed_utc'][:19].replace('T', ' '))} UTC.</div></footer></div></body></html>\n'''


def download(card):
    a = card['artifact']
    return f'''<div class="s16-card s16-download" data-submission-ready="false">
<span class="eyebrow">FRESH COMPUTATION / S16-PGRD</span><h2>Magnetic–gravity residual</h2><p class="small">A new raster from pinned geophysical inputs. No prior submission used as a feature or starting point.</p>
<div class="s16-status"><span>OK to download</span><strong>YES · research</strong></div>
<div class="s16-status"><span>OK to submit</span><strong class="warn">NO · duplicate stop</strong></div>
<div class="s16-status"><span>Finite values in [0, 1]</span><strong>PASS · no NaNs</strong></div>
<div class="s16-status"><span>CRS / shape / full transform</span><strong>PASS</strong></div>
<a class="button" download href="{esc(a['file'])}">↓ Download S16 research TIFF</a><div class="s16-buttons"><a download href="{esc(a['zip'])}">Single-TIFF ZIP</a><a href="s16/verification.json">Automated audit ↗</a></div>
<p class="small">{a['bytes']:,} bytes · single band · float32 · EPSG:32611<br>Downloading does not authorize submission.</p></div>'''


def fields(card):
    return f'''<div class="s16-card"><h3>File identity &amp; short note</h3><label for="candidate-name" class="small">Unique file name, not a uniqueness clearance</label><div class="copyrow"><textarea id="candidate-name" rows="2" readonly>{esc(card['submission_name'])}</textarea><button type="button" data-copy="candidate-name" aria-label="Copy submission name">Copy</button></div>
<label for="candidate-note" class="small">Submission note · {len(card['note'])}/140 characters</label><div class="copyrow"><textarea id="candidate-note" rows="3" readonly>{esc(card['note'])}</textarea><button type="button" data-copy="candidate-note" aria-label="Copy submission note">Copy</button></div><p id="copy-status" class="copy-status" role="status" aria-live="polite"></p><dl class="meta"><dt>SHA-256</dt><dd class="mono">{esc(card['raster_sha256'])}</dd><dt>Grid</dt><dd>3730 × 3292 · 100 m · EPSG:32611</dd><dt>Transform</dt><dd class="mono">(100, 0, 243350, 0, -100, 4508550)</dd><dt>Organizer receipt</dt><dd>None. No score claimed.</dd></dl></div>'''


def gate_table(card):
    explanations = {
        'format': ('File format', 'Reopened TIFF and ZIP; no NaN/Inf, all values [0,1], one band, exact grid, zero outside footprint and on mapped faults.'),
        'canary': ('Feature-alone canaries', f"{card['canaries']['features_tested']} features/control fields × four held-out quadrants; maximum symmetric AUC {card['canaries']['max_symmetric_auc']:.6f}. Passing is not proof of no leakage."),
        'novelty': ('Literal registry uniqueness', 'All final dots fall within 3 px of a frozen registry lattice. The 70% rule fails. Two preplacement registry records were unavailable; no missing file was counted as a pass.'),
        'assigned_lane': ('Assigned method lane', 'The prompt omitted its promised single-method paragraph. This documented provisional lane cannot authorize a slot.'),
        'beats_comparable_best': ('Scientific improvement', 'No improvement established over the matched gravity-only control; no certified common-instrument current-best receipt. No score forecast.'),
        'separate_selector': ('Separate slot selection', 'No selector approval or live weekly-cap receipt. No upload attempted; format validation cannot bypass other gates.'),
    }
    rows = ''
    for key, passed in gates(card).items():
        title, explanation = explanations[key]
        rows += f'<tr><td><strong>{esc(title)}</strong></td><td><span class="badge {"" if passed else "bad"}">{"PASS" if passed else "BLOCKED"}</span></td><td>{esc(explanation)}</td></tr>'
    return '<div class="table-scroll"><table><thead><tr><th>Automatic gate</th><th>Verdict</th><th>Evidence / limitation</th></tr></thead><tbody>' + rows + '</tbody></table></div>'


def render_preview(card):
    """PNG of actual prediction support; no generated terrain or invented truth."""
    import numpy as np
    import rasterio
    # Use only the published raster for dots. The verified footprint is optional
    # during static CI; a previously generated footprint preview remains fixed.
    dest = ROOT / 'docs/assets/s16-support.png'
    sample = ROOT / 'data/official/sample_submission.tif'
    if not sample.exists():
        if not dest.exists():
            raise FileNotFoundError('Restore pinned sample to build initial preview')
        return
    from scripts.verify_s16 import sha
    if sha(sample) != card['inputs']['sample_submission']['sha256']:
        raise ValueError('preview sample pin mismatch')
    with rasterio.open(sample) as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(ROOT / 'docs' / card['artifact']['file']) as s:
        dots = s.read(1) > 0
    factor = 6
    def shrink(a):
        h, w = a.shape
        p = np.pad(a, ((0, (-h) % factor), (0, (-w) % factor)))
        return p.reshape(p.shape[0] // factor, factor, p.shape[1] // factor, factor).any(axis=(1, 3))
    f, d = shrink(fp), shrink(dots)
    image = np.empty((*f.shape, 3), dtype=np.uint8)
    image[:] = [232, 238, 232]
    image[f] = [194, 210, 194]
    image[d] = [24, 91, 65]
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    raw = b''.join(b'\x00' + row.tobytes() for row in image)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', f.shape[1], f.shape[0], 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    dest.write_bytes(png)


def render(archive_legacy=False):
    card = load('run-card-S16.json')
    verify()  # Never trust a typed-in approval flag or a cached validation badge.
    if archive_legacy:
        for current, archived in [('index.html', 'archive-results.html'), ('executive-summary.html', 'archive-guide.html'), ('research.html', 'archive-research.html')]:
            text = (ROOT / 'docs' / current).read_text()
            notice = '<div class="banner"><strong>HISTORICAL RESEARCH ARCHIVE — NOT A CURRENT SUBMISSION RECOMMENDATION.</strong> Scores and claims below use multiple, sometimes flawed instruments. See the <a href="index.html">current measured candidate and automatic verdict</a>; no historical approval claim overrides it.</div>'
            text = text.replace('<main id="main">', '<main id="main">' + notice, 1)
            (ROOT / 'docs' / archived).write_text(text)
    render_preview(card)
    h = card['holdout_dti']; registry = card['registry_comparison']
    feed = load('fleet-audit.json'); sources = load('s16/sources.json')['sources']
    feas = load('s16/registry-feasibility.json'); forensic = load('s16/gems32-forensics.json')
    stats = load('s16/holdout.json')['summary']['scores']
    measured = f"{h['value']:.6f} HOLDOUT-DTI"
    ci = f"[{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]"
    science_note = f"95% CI {ci} · {h['withheld_positives']:,} withheld positives · {h['evaluator_version']}"
    intro = f'''<section class="s16-hero"><div><span class="eyebrow">SESSION 16 / A MEASURED NEGATIVE RESULT</span><h1>A new GeoTIFF.<br>An honest verdict.</h1><p class="lead">Fresh geophysical predictions, automatically checked from the written bytes. The file is downloadable; the scientific and uniqueness gates do not clear it for a competition slot.</p><div class="s16-badges"><span class="badge">OK TO DOWNLOAD: YES</span><span class="badge bad">OK TO SUBMIT: NO</span></div><p class="s16-subtitle">No human image inspection required. No prior submission copied. No leaderboard improvement claimed.</p></div>{download(card)}</section>'''
    home = intro + f'''<div class="s16-note"><strong>NOT OK TO SUBMIT</strong> — the literal registry-overlap gate failed, and this hypothesis did not establish an improvement over its control. The run stopped after one candidate experiment. No weekly submission slot was selected or spent.</div>
<section class="s16-grid" aria-label="Measured result summary"><div class="s16-card"><span class="s16-mini">HOLDOUT-DTI · NOT A LIVE SCORE</span><div class="s16-metric">{h['value']:.6f}</div><p class="small">{esc(science_note)}</p></div><div class="s16-card"><span class="s16-mini">FORMAT-VALID NEW COMPUTATION</span><div class="s16-metric">37,654 <small style="font-size:16px">dots</small></div><p class="small">Every cell finite in [0,1]. Different bytes do not establish protocol uniqueness.</p></div><div class="s16-card"><span class="s16-mini">BUDGET &amp; STOP RULE</span><div class="s16-metric">1 / 3</div><p class="small">Candidate experiments used. Duplicate stop honored; no further emission tuning. Zero competition uploads.</p></div></section>
<section class="s16-section"><div class="section-head"><h2>Submission readiness, without guesswork.</h2><a href="s16/verification.json">Read the machine audit ↗</a></div>{gate_table(card)}</section>
<section class="s16-section s16-split"><div><span class="eyebrow">THE SCIENTIFIC TEST</span><h2>Look for a density boundary<br>the magnetic field cannot explain.</h2><p>We tested local gravity–pseudogravity residual edges using two pinned competition layers: reduced-to-pole magnetics and isostatic gravity. This targets a possible altered or concealed contact rather than relocating a previous submission’s dots.</p><p>An unaltered granite–carbonate contact, reversed-polarity lava, or survey seam could mimic the signature. These dots are <strong>not confirmed faults or geothermal vents</strong>.</p><p><strong>{measured}</strong><br><span class="small">{esc(science_note)}</span></p><p>The matched gravity-only control performed better in the pooled estimate; the paired improvement interval includes zero. This hypothesis is a negative, not a reason to spend a slot.</p><a class="button outline" href="research.html">Read the hypothesis &amp; result →</a></div><figure class="s16-figure"><img src="assets/s16-support.png" width="549" height="622" alt="Actual S16 predicted dot support within the competition footprint; not a ground-truth or geothermal-vent map"><figcaption>Actual generated prediction support. Dots enlarged by block aggregation for visibility. No truth labels or terrain are implied.</figcaption></figure></section>
<section class="s16-section"><div class="section-head"><h2>Why the reported 0.2778 matters—and what it does not prove.</h2><a href="research.html#forensics">Read the forensic audit ↗</a></div><p>The reference file is exactly its 40,199-dot base with 2,545 dots within 200 m of mapped faults removed. Under max-kernel DTI, removing low-credit unmatched mass can improve the metric. That is a plausible mechanism, <strong>not proof of the hidden-score cause</strong>.</p><p><strong>0.2778 is user-reported, not ORGANIZER-CONFIRMED here.</strong> The pinned GEMSDOE32 page itself says no organizer score exists. Neither 0.4413 nor 0.3195 from the prompt is presented as a freshly verified leaderboard high.</p></section>
<section class="s16-section s16-split">{fields(card)}<div class="s16-card"><span class="s16-live">Bounded source feed</span><h3>Fleet inventory, not score authentication.</h3><p>{sum(r['status']=='FETCHED_GITHUB_SNAPSHOT' for r in feed['rows'])} of {len(feed['rows'])} repository pages fetched from pinned GitHub snapshots.</p><p class="small">Refreshed {esc(feed['checked_utc'][:19].replace('T', ' '))} UTC. Daily refresh checks public source pages; it does not log in to DrivenData or verify scores.</p><p><a href="fleet-audit.csv">Download source inventory CSV</a><br><a href="reported-results.csv">Supplied results, labelled unverified</a><br><a href="executive-summary.html">Exactly how a future cleared file is submitted</a></p><div class="s16-note">The next step is to resolve the registry conflict and establish a reliable common benchmark—not weaken a failed gate.</div></div></section>'''
    guide = f'''<section class="s16-hero"><div><span class="eyebrow">EXECUTIVE SUMMARY / SUBMISSION GUIDE</span><h1>Download is ready.<br>Submission is blocked.</h1><p class="lead">This distinction is enforced by code. No manual visual inspection is needed, and a format pass does not mean “submit anyway.”</p><p><span class="badge">OK TO DOWNLOAD: YES</span> <span class="badge bad">OK TO SUBMIT: NO</span></p><p><strong>NOT OK TO SUBMIT</strong> — negative research result, literal registry duplicate. A selector cannot override this failure.</p></div>{download(card)}</section>
<section class="s16-section"><h2>How a submission works—only after every gate passes.</h2>
<div class="s16-step"><h3>1 · Obtain the correct file</h3><p>Use the downloadable <code>-zeros.tif</code> or the ZIP containing exactly that one TIFF. Do not upload the audit JSON, HTML page, preview PNG, feature raster, or fault catalogue. The current file may be downloaded for research only.</p></div>
<div class="s16-step"><h3>2 · Let the project validate it</h3><p>Run <code>python generate_submission.py --with-data</code> in the project’s pinned environment. It checks the exact bytes, one-band float32 grid, finite [0,1] range, footprint and catalogue zeros, ZIP contents, recorded holdout arithmetic, canaries, and gate consistency.</p><p>Exit success means the negative deliverable is verified. Read <code>ok_to_submit</code> separately: it is <strong>false</strong>. No eyeballing or discretionary override is part of validation.</p></div>
<div class="s16-step"><h3>3 · Require a separate selector receipt</h3><p>A future candidate must beat the comparable holdout best with paired evidence, pass the agreed complete registry, and have an assigned lane. A separate selector must verify the current account’s weekly allowance and rule/data-use eligibility against the official submission page. That authenticated state is unavailable here; the previously quoted weekly cap is not re-verified.</p></div>
<div class="s16-step"><h3>4 · Upload only a genuinely cleared candidate</h3><p><strong>Not this file.</strong> For a future candidate whose gates all pass, open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → New submission</a>, choose its TIFF or single-TIFF ZIP, and paste its recorded short note. The name and note below identify this research negative, not an approved slot.</p></div>
<div class="s16-step"><h3>5 · Preserve the organizer receipt</h3><p>Record the exact submitted file’s SHA-256, organizer submission identifier, timestamp and score from the submission-page receipt. Only then label that result ORGANIZER-CONFIRMED. A local HOLDOUT-DTI value or an owner website claim is not such a receipt.</p></div></section>
<section class="s16-section s16-split">{fields(card)}<div class="s16-card"><h3>About the range error</h3><p>The new TIFF has no NaNs or infinities anywhere, no negative sentinel, no nodata tag, and only values 0 and 1. Both rasterio and an independent TIFF decoder check its bytes; the ZIP is unpacked and compared byte-for-byte.</p><p>The exact cause of your earlier portal error was not established. These checks address range/encoding failures; they cannot guarantee organizer acceptance if the portal’s rules or parser differ.</p><p><a href="s16/writer-receipt.json">Writer receipt</a> · <a href="s16/verification.json">Independent verification</a></p></div></section><section class="s16-section"><h2>Current automated decision</h2>{gate_table(card)}</section>'''
    score_rows = ''
    for name, label in [('pgrd','S16-PGRD candidate'), ('gravity_control','Matched gravity-only control'), ('ced_benchmark','CED91 reproduced benchmark; historical budget')]:
        v = stats[name]
        score_rows += f'<tr><td>{label}</td><td>{v["dti"]:.6f} HOLDOUT-DTI</td><td>[{v["ci95"][0]:.6f}, {v["ci95"][1]:.6f}]</td></tr>'
    source_rows = ''.join(f'<tr><td>{esc(s["claim"])}</td><td>{esc(s["classification"])}</td><td><a href="{esc(s["url"])}">Review source ↗</a><br>{esc(s["verification"])}</td></tr>' for s in sources)
    control = h['paired_controls']['gravity_control']
    research = f'''<section class="s16-section"><span class="eyebrow">RESEARCH / EXPLICIT EVIDENCE BOUNDARIES</span><h1>A plausible mechanism.<br>A negative test.</h1><p class="lead">The target is missing fault structure, not a directly observed geothermal vent. Scientific novelty is not demonstrated by a new filename, and a successful canary is not proof that a geological interpretation is correct.</p><p><a class="button outline" href="HYPOTHESES_S16.md">Four ranked, preregistered hypotheses</a> <a class="button outline" href="REVIEW-S16.md">Three-pass repository review</a></p></section>
<section class="s16-section"><h2>One lane. One candidate. No post-result search.</h2><p>Ranked before implementation: local transfer residual; transfer-slope reversal; cross-scale transfer breakdown; residual endpoint pairing. Only the first was tested. All use the already restored B02/B13 stack; no inaccessible external dataset was called viable.</p><p>The implemented operator band-limits RTP magnetics, integrates by <code>1/|k|</code> with zero DC, fits a regularized local gravity relationship and ranks coherent residual edges. It assumes a relationship between density and magnetization that real lithology can violate. <strong>Non-fault mimic:</strong> an unaltered nonmagnetic granite–carbonate contact.</p><p>No previous submission, thermal well label or global catalogue-distance feature enters the prediction surface.</p></section>
<section class="s16-section"><h2>Hide-and-recover result</h2><p>Fixed label-blind quadrants; whole intersecting fault segments withheld; 8 km training exclusion. Predictions mask visible faults pixel-exactly, not a halo around hidden truth. The candidate uses the same global dot budget and placement function during holdout and full inference.</p><p><code>{esc(h['evaluator_version'])}</code> · {h['withheld_positives']:,} withheld positives · pooled DTI alpha 0.2 / beta 0.8 / 300 m triangular kernel · 95% confidence intervals from 1,000 paired physical 20 km block resamples.</p><div class="table-scroll"><table><thead><tr><th>Arm</th><th>Measured result</th><th>95% CI</th></tr></thead><tbody>{score_rows}</tbody></table></div><p>Paired candidate minus gravity control: <strong>{control['delta']:+.6f} HOLDOUT-DTI</strong>, 95% CI [{control['ci95'][0]:+.6f}, {control['ci95'][1]:+.6f}], same evaluator and positive population. This does not establish improvement. CED’s prior pooled point estimate reproduced exactly; its CI here uses the shared paired resample.</p><p class="small">Intervals are conditional on the catalogue, fixed model and split—not leaderboard intervals. Catalogue-zero pixels are unlabeled, not verified absences. Repeated historical use of these holdouts risks selection overfitting; a common, frozen benchmark remains necessary.</p><p><a href="s16/holdout.json">Per-fold and pooled evidence</a> · <a href="s16/canaries.json">Every feature canary</a> · <a href="s16/provenance.json">Code and input provenance</a></p></section>
<section class="s16-section" id="registry"><h2>The uniqueness conflict is mathematical.</h2><p>The frozen lattice covers {100*feas['covered_fraction']:.4f}% of the footprint within 3 px. Only {feas['uncovered_pixels']:,} cells remain. With 37,654 distinct binary dots, even the best possible placement has overlap at least <strong>{100*feas['overlap_lower_bound']:.2f}%</strong>—above 70%. Spacing only makes the bound stricter.</p><p>The candidate’s surface had maximum measured absolute Spearman {registry['max_measured_surface_rank_correlation']:.6f}; {registry['preplacement']['checked']} indexed entries were attempted, with missing entries marked UNVERIFIED. Final-dot testing stopped at reference {registry['final']['checked']} on <strong>100% overlap</strong>; {registry['final']['not_checked_after_stop']} entries were deliberately not checked afterward. This is not universal uniqueness.</p><p>No dense reference was removed, thresholded or replaced with symmetric overlap. The freshly computed TIFF has a new pixel digest, but <strong>fails the user’s actual uniqueness rule</strong>.</p><p><a href="s16/registry-feasibility.json">Capacity-bound proof</a> · <a href="s16/registry-surface.json">Preplacement checks</a> · <a href="s16/registry-final.json">Literal duplicate stop</a></p></section>
<section class="s16-section" id="forensics"><h2>Why might GEMSDOE32’s reported 0.2778 have worked?</h2><p><strong>The report is not authenticated.</strong> The commit-pinned GEMSDOE32 page calls the artifact UNSCORED and says no organizer score exists. The supplied 0.2778 is preserved as an unverified user claim, never an ORGANIZER-CONFIRMED result.</p><p>What is byte-verifiable: its 37,654 dots are exactly the 40,199-dot base with {forensic['r0_removed_vs_base']:,} dots at catalogue distance ≤2 px removed. There are zero added dots. Minimum nearest-neighbor spacing is {forensic['r0_nearest_neighbor_px']['min']:.3f} px and median spacing is {forensic['r0_nearest_neighbor_px']['median']:.1f} px—not evidence that a fixed dot count or a 300 m catalogue collar is universally optimal.</p><p><span class="s16-pill">121,131 support pixels</span> → <span class="s16-pill">44,090 dots</span> → <span class="s16-pill">40,199 dots</span> → <span class="s16-pill">37,654 dots</span><br><span class="small">Local geometry audit, not newly verified score measurements.</span></p><div class="diagram"><code>DTI = T / [0.2T + 0.2(S − M) + 0.8|G|]</code><p>T is best triangular-kernel credit summed over truth; S is emitted mass; M is prediction-weighted match to truth. T and M are not interchangeable. A dot may cover multiple truth pixels.</p></div><p>Removing unmatched or redundant low-credit mass may reduce false-positive cost while retaining truth coverage. It does <em>not</em> follow that every redundant dot costs exactly 0.2, that thinner always wins, or that this explains the entire reported score. The needed causal evidence—organizer truth or controlled organizer receipts—is unavailable.</p><p>Could a distinct method score higher? In principle, yes, by earning more new kernel credit per unmatched mass. This test does not demonstrate it. The historical website’s ZIP was also malformed: {forensic['advertised_zip']['bytes']} bytes containing an empty ZIP member, not a TIFF. Our new ZIP’s member and exact TIFF bytes are automatically checked.</p><p><a href="s16/gems32-forensics.json">Measured parent and ZIP audit</a></p></section>
<section class="s16-section" id="sources"><h2>Source register: fetched, measured, or unavailable.</h2><div class="table-scroll"><table><thead><tr><th>Claim / scope</th><th>Authority</th><th>Source &amp; verification boundary</th></tr></thead><tbody>{source_rows}</tbody></table></div><p><a href="s16/sources.json">Machine-readable source register</a> · <a href="fleet-audit.csv">Full fleet-source inventory</a> · <a href="reported-results.csv">Supplied results, unverified</a></p></section>
<section class="s16-section"><h2>Highest-value next steps</h2><ol><li>Resolve the blanket-lattice registry contradiction through an explicit, versioned protocol decision. Do not game it with anti-registry noise.</li><li>Use one label-blind whole-segment benchmark and re-evaluate the strongest eligible incumbent under the same population, emission procedure and paired uncertainty. Old halo-deletion scores cannot serve as interchangeable promotion bars.</li><li>Authenticate current official rules, data rights, weekly allowance and organizer receipts. GitHub mirror hashes establish identity, not legal permission or live score accuracy.</li><li>Reserve a genuinely untouched spatial or geological control before another hypothesis search. Do not repeat PGRD variants merely to mine this holdout.</li></ol><p>Verification limits: no authenticated DrivenData session, official live leaderboard receipt or complete private shared registry is in this audit. The real competition inputs were restored from existing hash-pinned mirrors; a GPU is not required for this completed experiment.</p></section>'''
    for name, title, content in [('index.html','Current GeoTIFF & automated verdict',home), ('executive-summary.html','Executive summary & exact submission guide',guide), ('research.html','Scientific test, registry proof & verified sources',research)]:
        (ROOT / 'docs' / name).write_text(page(title, content, card))
    (ROOT / 'docs/assets/s16.css').write_text(CSS.strip() + '\n')
    (ROOT / 'docs/current-run.json').write_text(json.dumps(dict(run_card='run-card-S16.json', ok_to_download=True, ok_to_submit=False, raster_sha256=card['raster_sha256']), indent=2) + '\n')
    (ROOT / 'index.html').write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE91 — research TIFF, automated verdict</title></head><body><main><h1>GEMSDOE91</h1><p><a href="docs/index.html">Open the current candidate and download</a></p><p>OK TO DOWNLOAD: YES — RESEARCH. OK TO SUBMIT: NO — duplicate stop. Validation is automatic; no weekly slot was used.</p><p><a href="docs/executive-summary.html">Executive summary and submission guide</a></p></main></body></html>\n''')
    print('Current S16 portal rendered from reverified bytes; download YES, submit NO.')


if __name__ == '__main__':
    render()
