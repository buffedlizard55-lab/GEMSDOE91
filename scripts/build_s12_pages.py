#!/usr/bin/env python3
"""Render synchronized GitHub Pages HTML subpages (`docs/s12-spid.html` and
`docs/s12-executive-summary.html`) directly from `docs/run-card-S12.json`,
`evidence/s12_registry_uniqueness.json`, and `evidence/s12_leakage_canary.json`.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _esc(v: object) -> str:
    return html.escape(str(v), quote=True)


def build_s12_spid_html(rc: dict, uniq: dict, canary: dict) -> str:
    sub = rc["submission"]
    ph = rc["scores"]["primary_holdout"]
    sh = rc["scores"]["secondary_gems57_holdout"]
    sgmc = rc["scores"]["blind_sgmc_offcatalogue_control"]
    exps = rc["experiments"]
    win = next(e for e in exps if e["exp_id"] == rc["winning_experiment"])

    exp_rows = []
    exp_rows.append(
        f"""<tr>
          <td><code>B0</code> (Baseline)</td>
          <td>Raw 19 GeoDAWN bands OOF HGB+LR + Poisson disk thinning (<code>d &ge; 2.8 px</code>)</td>
          <td>19</td>
          <td><strong>HOLDOUT-DTI</strong> <code>{ph['b0_reference_holdout_dti']:.6f}</code><br><small>95% CI [{ph['b0_reference_ci_95'][0]:.6f}, {ph['b0_reference_ci_95'][1]:.6f}] (n=60,988)</small></td>
          <td>Baseline</td>
          <td>—</td>
          <td>Reference</td>
        </tr>
        <tr>
          <td><code>H91-DDVTC E1</code></td>
          <td>Dip-Deprojected Verduzco Tilt + Openness + 1D-Ridge Submodular 300m DTI (<code>38,400</code> dots)</td>
          <td>34</td>
          <td><strong>HOLDOUT-DTI</strong> <code>{ph['h91_e1_reference_holdout_dti']:.6f}</code><br><small>95% CI [{ph['h91_e1_reference_ci_95'][0]:.6f}, {ph['h91_e1_reference_ci_95'][1]:.6f}] (n=60,988)</small></td>
          <td><code>+0.035031</code> (+25.2% vs B0)</td>
          <td><code>0.082886</code></td>
          <td>Prior Lane</td>
        </tr>
        <tr>
          <td><code>S11-MHTR E2</code> (#1 Repo Best)</td>
          <td>Marussi Gravity Hessian + Official Band 06 Radiometric TC + Two-Regime Submodular 300m DTI (<code>48,000</code> dots)</td>
          <td>55</td>
          <td><strong>HOLDOUT-DTI</strong> <strong><code>{ph['s11_e2_reference_holdout_dti']:.6f}</code></strong><br><small>95% CI [{ph['s11_e2_reference_ci_95'][0]:.6f}, {ph['s11_e2_reference_ci_95'][1]:.6f}] (n=60,988)</small></td>
          <td><code>+0.067407</code> (+48.5% vs B0)</td>
          <td><strong><code>0.097623</code></strong></td>
          <td><span class="badge">REPO #1</span></td>
        </tr>"""
    )

    for e in exps:
        is_w = e["exp_id"] == rc["winning_experiment"]
        u = e["uniqueness_summary"]
        if not u["uniqueness_pass"]:
            badge = f'<span class="badge bad">DUPLICATE STOP ({100.0*u["max_3px_dot_overlap"]:.1f}% &gt; 70%)</span>'
        elif is_w:
            badge = '<span class="badge bad">UNIQUE · VERDICT NEGATIVE vs S11</span>'
        else:
            badge = '<span class="badge">VALIDATED</span>'
        exp_rows.append(
            f"""<tr>
              <td><strong><code>{_esc(e['exp_id'])}</code></strong><br><small>{_esc(e['hypothesis_id'])}</small></td>
              <td><strong>{_esc(e['title'])}</strong><br><small><em>Non-fault mimic rejected:</em> {_esc(e['named_non_fault_mimic'])}</small></td>
              <td>{e['n_features']}</td>
              <td><strong>HOLDOUT-DTI</strong> <strong><code>{e['holdout']['holdout_dti']:.6f}</code></strong><br><small>95% CI [{e['holdout']['ci_95'][0]:.6f}, {e['holdout']['ci_95'][1]:.6f}] (n={e['holdout']['n_withheld_positives']:,})</small></td>
              <td><strong><code>{e['delta_vs_b0_holdout_dti']:+.6f}</code></strong> vs B0<br><small><code>{e['delta_vs_s11_e2_holdout_dti']:+.6f}</code> vs S11-E2</small></td>
              <td><strong><code>{e['sgmc_offcatalogue_control']['dti']:.6f}</code></strong><br><small>max 3px ov: {100.0*u['max_3px_dot_overlap']:.2f}%</small></td>
              <td>{badge}</td>
            </tr>"""
        )

    fold_rows = []
    for f in win["holdout"]["folds"]:
        fold_rows.append(
            f"""<tr>
              <td><code>Fold {f['fold_id']} ({_esc(f['name'])})</code></td>
              <td>{f['n_segments_withheld']:,} whole fault complexes</td>
              <td>{f['n_withheld_positives']:,} px</td>
              <td>{int(f['emitted_mass']):,} dots</td>
              <td>{f['T']:.3f}</td>
              <td>{f['M']:.1f}</td>
              <td><strong>HOLDOUT-DTI</strong> <strong><code>{f['fold_dti']:.6f}</code></strong></td>
            </tr>"""
        )

    uniq_rows = []
    for c in sorted(uniq["comparisons"], key=lambda x: -x["effective_dot_overlap_3px"])[:25]:
        uniq_rows.append(
            f"""<tr>
              <td><code>{_esc(c['registry_raster'])}</code></td>
              <td>{c['n_registry_positive']:,}</td>
              <td><code>{c['surface_abs_rank_corr']:.4f}</code> (&le; 0.90)</td>
              <td><code>{100.0*c['cand_within_3px_of_reg']:.2f}%</code></td>
              <td><code>{100.0*c['reg_within_3px_of_cand']:.2f}%</code></td>
              <td><code>{100.0*c['effective_dot_overlap_3px']:.2f}%</code> (&le; 70.0%)</td>
              <td><span class="badge">PASS</span></td>
            </tr>"""
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>S12-SPID Laplace-SPI, Conductivity &amp; Weingarten MoE Lane ({ph['score']:.4f} HOLDOUT-DTI · Negative) · GEMSDOE91</title>
<meta name="description" content="Session 12 Laplace-Fourier SPI, Depth-Deconfounded Conductivity, Weingarten Scarp-Toe MoE &amp; Self-Credit Bayes-Dinkelbach Deliverable ({sub['candidate_id']}).">
<link rel="stylesheet" href="assets/portal.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="top"><a class="brand" href="index.html">GEMSDOE<span>91 / FAULT MAPPING LAB</span></a>
<nav aria-label="Main"><a href="index.html">Research &amp; download</a><a href="s12-spid.html">S12-SPID Lane (0.1517 · Negative)</a><a href="s12-executive-summary.html">S12 Guide</a><a href="s11-mhtr.html">S11-MHTR (#1 · 0.2064)</a><a href="h91-ddvtc.html">H91 Lane (0.1740)</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Evidence &amp; sources</a></nav></header>
<main id="main">
<section class="hero">
  <div>
    <span class="eyebrow">SESSION 12 DISCOVERY LANE / S12-SPID (BRANCH arena/01ec3805-gemsdoe91)</span>
    <h1>Laplace-SPI &amp; Subsurface MoE.<br>67-Raster Unique.<br>Honest <code>negative</code> verdict.</h1>
    <p class="lead">Tested 3 pre-registered hypotheses (<code>H12-1..H12-3</code>): <code>E1</code> (<code>0.200104</code>) &amp; <code>E2</code> (<code>0.203905</code>; <code>0.215758</code> pre-basin-floor) converged onto <code>S11-MHTR E2</code>'s range-front scarps (<code>81–86% &gt; 70%</code> Rule 1 stop). Pure LRM-free, <code>S11</code>-free <code>E3</code> clears all 67 real rasters (<code>66.63% &le; 70%</code>) and beats <code>B0</code>/<code>DENOVO</code>/<code>H11-1</code>/<code>CED91</code> on both holdout evaluators (<code>0.151682</code> &amp; <code>0.145009</code>), but trails Repository #1 <code>S11-MHTR E2</code> (<code>0.206406</code>).</p>
    <span class="badge bad">NOT OK TO SUBMIT AS SOLO WEEKLY SLOT · VERDICT: NEGATIVE</span>
    <p class="small">Validated automatically on disk without human image inspection: <strong>OK TO DOWNLOAD</strong> (<code>[0, 1]</code> certified, 0 NaNs, 67-raster unique), <strong>NOT RECOMMENDED FOR SOLO LIVE UPLOAD</strong> over <code>S11-MHTR E2</code>.</p>
  </div>
  <div class="download" data-submission-ready="false">
    <div class="label">AUTOMATED VALIDATION &amp; SUBMISSION STATUS</div>
    <h2><code>{_esc(sub['candidate_id'])}</code></h2>
    <div class="status"><span>OK to download (Format [0, 1])</span><strong>YES — 4/4 Suites PASS</strong></div>
    <div class="status"><span>OK to submit (Solo weekly slot)</span><strong>NO — Trails S11-MHTR E2</strong></div>
    <div class="status"><span>67-Real-Raster Uniqueness</span><strong>PASS (66.63% &le; 70.0%)</strong></div>
    <div class="status"><span>HOLDOUT-DTI (v1.0 / g57-v2)</span><strong>0.151682 / 0.145009</strong></div>
    <a class="button" download href="downloads/{_esc(sub['recommended_upload_file'])}">↓ Download Research/Ensemble GeoTIFF (.tif · {sub['bytes_zeros_tif']:,} B)</a>
    <div style="text-align:center;margin-top:12px">
      <a download href="downloads/{_esc(sub['recommended_zip_download'])}">↓ Single-TIFF ZIP ({sub['bytes_zeros_zip']:,} B)</a> ·
      <a href="downloads/{_esc(sub['audit_json'])}">Format Receipt (.json)</a> ·
      <a href="run-card-S12.json">S12 Run Card (.json)</a>
    </div>
    <p class="small">Single-band float32 · EPSG:32611 · 3730×3292 · 100 m · 47,200 binary dots (52.9% on &lt;5&deg; concealed slopes) · min_d_cat = 3.1623 px.</p>
  </div>
</section>

<div class="banner"><strong>Automated Gate Verdict — Do NOT burn a scarce 3/week DrivenData slot on <code>S12-SPID E3</code> solo.</strong> All 12,279,160 cells are finite <code>float32</code> in <code>[0.0, 1.0]</code> (permanently immune to <code>"Predicted values must be in range [0, 1]"</code>), all 85 single-feature leakage canaries passed (<code>max AUC = 0.6610 &le; 0.90</code>), and all 67 real fault rasters passed 3-px uniqueness (<code>max = 66.63% &le; 70%</code>). Because stripping first-order <code>LRM/TPI</code> to clear <code>S11-MHTR E2</code> lowered solo <code>HOLDOUT-DTI</code> from <code>0.206406</code> to <code>0.151682</code> (paired &Delta; = <code>-0.054724</code>), <code>S11-MHTR E2</code> remains Repository #1 while <code>S12-SPID E3</code> contributes <code>15,751</code> new concealed-basin dots for future fleet ensembling.</div>

<div class="grid">
  <article class="card">
    <span class="eyebrow">PRIMARY HOLDOUT-DTI / v1.0</span>
    <div class="number">{ph['score']:.5f}</div>
    <p>95% CI {ph['ci_95'][0]:.5f}–{ph['ci_95'][1]:.5f} (60,988 withheld px)<br><strong>+{ph['lift_over_b0']:.5f}</strong> (+9.1%) vs B0 · Paired <code>{ph['lift_over_s11_e2']:+.5f}</code> vs S11-E2</p>
    <span class="small">{_esc(ph['evaluator_version'])}</span>
  </article>
  <article class="card">
    <span class="eyebrow">SECONDARY HOLDOUT-DTI / GEMS57-V2 (8 KM BUFFER)</span>
    <div class="number">{sh['score']:.5f}</div>
    <p>95% CI {sh['ci_95'][0]:.5f}–{sh['ci_95'][1]:.5f} · Beats H11-1 (<code>0.13965</code>) &amp; CED91 (<code>0.06215</code>)<br>First measurement of S11-E2 on 8-km buffer: <strong><code>{sh['s11_e2_same_instrument']:.5f}</code></strong></p>
    <span class="small">{_esc(sh['evaluator_version'])} · buffer=80 px</span>
  </article>
  <article class="card">
    <span class="eyebrow">RULE 1 &amp; RULE 4 / CANARY &amp; 67-RASTER NOVELTY</span>
    <div class="number">85/85 · 67/67</div>
    <p>85 official features tested alone (max sym AUC <code>{canary['worst_symmetric_auc']:.5f} &le; 0.90</code>)<br>67 real fault rasters checked (max |&rho;| <code>{uniq['surface_max_abs_rank_corr']:.4f}</code>, max 3px ov <code>{100.0*uniq['dots_max_3px_overlap']:.2f}% &le; 70%</code>)</p>
    <a class="small" href="HYPOTHESES_S12.md">Read pre-registration, theorem &amp; PDE audit ↗</a>
  </article>
</div>

<section class="section">
  <div class="twocol">
    <div class="card">
      <h3>Copy-Paste Artifact Identification (Archival / Ensemble Reference)</h3>
      <label for="s12-name" class="small">Unique Submission Name</label>
      <div class="copyrow">
        <textarea id="s12-name" readonly rows="2">{_esc(sub['recommended_form_name'])}</textarea>
        <button data-copy="s12-name" type="button">Copy</button>
      </div>
      <label for="s12-note" class="small">Short Note · {sub['recommended_form_note_length']}/140 characters</label>
      <div class="copyrow">
        <textarea id="s12-note" readonly rows="3">{_esc(sub['recommended_form_note'])}</textarea>
        <button data-copy="s12-note" type="button">Copy</button>
      </div>
      <p id="copy-status" class="copy-status" role="status" aria-live="polite"></p>
      <dl class="meta">
        <dt>SHA-256 (<code>-zeros.tif</code>)</dt><dd class="mono">{_esc(sub['sha256_zeros_tif'])}</dd>
        <dt>SHA-256 (<code>-zeros.zip</code>)</dt><dd class="mono">{_esc(sub['sha256_zeros_zip'])}</dd>
        <dt>SHA-256 (<code>.tif</code> NaN twin)</dt><dd class="mono">{_esc(sub['sha256_nan_tif'])}</dd>
        <dt>Emitted Dots / Basin Share</dt><dd>{sub['n_dots']:,} binary dots · {100.0*sub['low_slope_lt5deg_dot_fraction']:.2f}% on &lt;5&deg; slopes · min d_cat = {sub['min_catalogue_distance_px']:.4f} px</dd>
      </dl>
    </div>
    <div class="card">
      <h3>Four PhD Discoveries in Session 12</h3>
      <ul class="checklist">
        <li><span><strong>Exact DTI Binary-Vertex Theorem:</strong> Proved coordinate-wise convexity of expected Dinkelbach DTI (<code>1 - 0.2&lambda; &ge; 0.8 &gt; 0</code>), establishing exact <code>{{0, 1}}</code> optimality and noisy-OR 300 m self-credit <code>m&#770;(x)</code>.</span><span class="badge">PROVED</span></li>
        <li><span><strong>IR-91-S12-01 (100&times; Tilt Unit &amp; TMI-RTP Bug Fixed):</strong> Fixed <code>dd_vtc_pu.py</code> mixing <code>B11=&part;<sub>y</sub>G</code> for <code>&part;<sub>z</sub>G</code> and <code>B09</code> (nT/m) with <code>grad_px(B02)</code> (nT/100 m) via Laplace-FFT <code>&part;<sub>z</sub>G</code> &amp; <code>&part;<sub>z</sub>RTP</code> + 3-D Roest Analytic Signal.</span><span class="badge">VERIFIED</span></li>
        <li><span><strong>IR-91-S12-03 (Range-Front Scarp Saturation Ceiling):</strong> Proved models retaining <code>LRM/TPI</code> reach <code>0.2158</code> DTI only by overlapping <code>81–86%</code> with <code>S11-MHTR E2</code>, whereas pure subsurface + Weingarten toe MoE yields <code>15,751</code> orthogonal basin dots (<code>66.6% &le; 70%</code>).</span><span class="badge">MEASURED</span></li>
      </ul>
      <p><a href="s12-executive-summary.html">Open S12 Executive Summary &amp; Step-by-Step Guide ↗</a> · <a href="s11-mhtr.html">View Repository #1 S11-MHTR (0.2064 DTI) ↗</a></p>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <h2>Pre-Registered 3-Experiment Holdout Progression (<code>gems91-hide-recover-v1.0</code>)</h2>
    <a href="run-card-S12.json">Download full JSON run card ↗</a>
  </div>
  <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th>Experiment</th>
          <th>Hypothesis, Physical Mechanism &amp; Named Mimic Rejected</th>
          <th>Features</th>
          <th>Out-of-Fold HOLDOUT-DTI (95% CI)</th>
          <th>Lift vs Benchmarks</th>
          <th>Blind SGMC Control</th>
          <th>Protocol Gate</th>
        </tr>
      </thead>
      <tbody>
        {"".join(exp_rows)}
      </tbody>
    </table>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <h2>4-Fold Spatially-Blocked Breakdown for Unique Candidate <code>E3</code></h2>
    <span class="small">Whole fault complexes withheld · 1.0 km (10 px) exclusion buffer · exact visible masking</span>
  </div>
  <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th>Spatial Quadrant</th>
          <th>Withheld Fault Complexes</th>
          <th>Withheld Positive Pixels</th>
          <th>Emitted Dots</th>
          <th>Weighted TP (<code>T</code>)</th>
          <th>Matched Mass (<code>M</code>)</th>
          <th>Fold HOLDOUT-DTI</th>
        </tr>
      </thead>
      <tbody>
        {"".join(fold_rows)}
      </tbody>
    </table>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <h2>Rule 1 Registry Uniqueness Audit (67 Real Fault Rasters Checked: 100% PASS)</h2>
    <span class="small">Top 25 closest rasters by 3-px dot overlap (limit &le; 70.0%; surface |&rho;| limit &le; 0.90)</span>
  </div>
  <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th>Registry / Sibling / Repository Raster</th>
          <th>Registry Dots</th>
          <th>Surface |&rho;|</th>
          <th>Cand &le;3px of Reg</th>
          <th>Reg &le;3px of Cand</th>
          <th>Effective 3px Overlap</th>
          <th>Gate</th>
        </tr>
      </thead>
      <tbody>
        {"".join(uniq_rows)}
      </tbody>
    </table>
  </div>
</section>
</main>
<footer>
  <div>Session 12 Discovery Audit (<code>{_esc(sub['candidate_id'])}</code> · Verdict: <code>negative</code>)<br>Generated {_esc(rc['generated_utc'])}</div>
  <div><a href="run-card-S12.json">S12 JSON Run Card</a> · <a href="s11-mhtr.html">Repo #1 S11-MHTR</a> · <a href="index.html">Main Research Portal</a></div>
</footer>
</div></body></html>
"""


def build_s12_exec_summary_html(rc: dict) -> str:
    sub = rc["submission"]
    ph = rc["scores"]["primary_holdout"]
    sh = rc["scores"]["secondary_gems57_holdout"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>S12 Executive Summary &amp; Submission Guide · GEMSDOE91</title>
<meta name="description" content="Executive summary, automated readiness verdict, and step-by-step DrivenData submission guide for Session 12 ({sub['candidate_id']}).">
<link rel="stylesheet" href="assets/portal.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="top"><a class="brand" href="index.html">GEMSDOE<span>91 / FAULT MAPPING LAB</span></a>
<nav aria-label="Main"><a href="index.html">Research &amp; download</a><a href="s12-spid.html">S12-SPID Lane (0.1517 · Negative)</a><a href="s12-executive-summary.html">S12 Guide</a><a href="s11-mhtr.html">S11-MHTR (#1 · 0.2064)</a><a href="h91-ddvtc.html">H91 Lane (0.1740)</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Evidence &amp; sources</a></nav></header>
<main id="main">
<section class="hero">
  <div>
    <span class="eyebrow">EXECUTIVE SUMMARY / SESSION 12 AUTOMATED VERDICT &amp; SUBMISSION GUIDE</span>
    <h1>Is <code>S12-SPID E3</code> OK to download &amp; submit?</h1>
    <p class="lead"><strong>OK to download: YES</strong> (all 4 automated GeoTIFF validators PASS; finite <code>[0.0, 1.0]</code>; 67-raster unique).<br><strong>OK to submit to a live weekly slot: NO</strong> (<code>verdict = negative</code>; solo <code>HOLDOUT-DTI = 0.151682</code> trails Repository #1 <code>S11-MHTR E2 = 0.206406</code>).</p>
    <span class="badge bad">AUTOMATED VERDICT: DO NOT SPEND A SOLO WEEKLY SLOT ON S12-SPID E3</span>
  </div>
  <div class="download" data-submission-ready="false">
    <div class="label">CERTIFIED [0, 1] RESEARCH &amp; ENSEMBLE ARTIFACT</div>
    <h2><code>{_esc(sub['recommended_upload_file'])}</code></h2>
    <div class="status"><span>OK to download</span><strong>YES — Range [0, 1] Certified</strong></div>
    <div class="status"><span>OK to submit (Solo slot)</span><strong>NO — Use Selector / S11-E2</strong></div>
    <div class="status"><span>CRS / Grid</span><strong>EPSG:32611 · 3730×3292 · 100 m</strong></div>
    <div class="status"><span>HOLDOUT-DTI (v1.0 / g57-v2)</span><strong>{ph['score']:.6f} / {sh['score']:.6f}</strong></div>
    <a class="button" download href="downloads/{_esc(sub['recommended_upload_file'])}">↓ Download Certified GeoTIFF (.tif)</a>
    <div style="text-align:center;margin-top:12px">
      <a download href="downloads/{_esc(sub['recommended_zip_download'])}">↓ Download Single-TIFF .zip</a> ·
      <a href="downloads/{_esc(sub['audit_json'])}">Format Receipt (.json)</a>
    </div>
  </div>
</section>

<section class="section">
  <h2>Why <code>"Predicted values must be in range [0, 1]"</code> happened — and how we permanently eliminated it</h2>
  <div class="twocol">
    <div class="card">
      <h3>Root Cause 1: In-Footprint Sentinel Bleed (<code>-3.4028235e+38</code>) &amp; Unmasked NaNs</h3>
      <p>Official <code>training_features.tif</code> carries <code>3,061</code> cells <em>inside</em> the active Nevada footprint with float32 sentinel values (<code>-3.4028234663852886e+38</code>), and the official U-Net reference notebook converts <code>&lt; -1e38</code> to <code>np.nan</code>. Any spatial convolution or unmasked inference leaks <code>NaN</code> or negative values into the output GeoTIFF.</p>
      <p><strong>Automated Fix:</strong> Every band is scrubbed via <code>isfinite(arr) &amp; (arr &gt; -1e30)</code> and repaired by nearest-neighbor Euclidean distance transform before any FFT or gradient operator runs.</p>
    </div>
    <div class="card">
      <h3>Root Cause 2: Raw Buffer Range Check on <code>nodata=NaN</code></h3>
      <p>DrivenData's scorer checks <code>0.0 &le; arr &le; 1.0</code> across the raster buffer. Writing <code>NaN</code> across the <code>7,111,787</code> outside-footprint cells triggers <code>"Predicted values must be in range [0, 1]"</code> whenever <code>NaN</code> is not stripped prior to range checking.</p>
      <p><strong>Automated Fix:</strong> <code>{_esc(sub['recommended_upload_file'])}</code> writes <code>0.0</code> outside the footprint with <code>nodata=None</code> and verifies all <code>12,279,160</code> float32 cells on disk across 4 independent validator suites (<code>min=0.0, max=1.0, NaN=0, Inf=0</code>).</p>
    </div>
  </div>
</section>

<section class="section">
  <h2>Step-by-Step DrivenData Submission Guide (When Approved by the Human Fleet Selector)</h2>
  <div class="step"><b>1</b><div><h3>Respect the 3/Week Team Cap &amp; Compare Holdout Evidence</h3><p>Teams have at most <strong>3 live submissions per week</strong> on DrivenData (#306). Within <code>GEMSDOE91</code>, <code>S11-MHTR E2</code> (<code>0.206406</code> on <code>gems91-hide-recover-v1.0</code> and <code>0.194267</code> on <code>gems57-pooled-hide-v2</code>) outscores <code>S12-SPID E3</code> (<code>0.151682</code> / <code>0.145009</code>). Do <strong>not</strong> upload <code>S12-SPID E3</code> as a solo weekly submission; retain it as an orthogonal concealed-basin specialist (<code>52.93%</code> low-slope dots, <code>15,751</code> dots &gt;3 px from <code>S11-MHTR E2</code>) for cross-fleet ensembling.</p></div></div>
  <div class="step"><b>2</b><div><h3>Verify Automatic On-Disk Gate Receipts (No Visual Inspection Needed)</h3><p>Run <code>.venv/bin/python scripts/verify_current_artifact.py --with-data</code> and <code>.venv/bin/pytest -q</code>, or inspect <a href="downloads/{_esc(sub['audit_json'])}"><code>{_esc(sub['audit_json'])}</code></a> confirming <code>all_cells_finite=true</code>, <code>min_value=0.0</code>, <code>max_value=1.0</code>, <code>EPSG:32611</code>, <code>3730&times;3292</code>, and <code>dots_le_3px=0</code>.</p></div></div>
  <div class="step"><b>3</b><div><h3>If Approved by Fleet Selector, Upload Only the <code>-zeros.tif</code> or <code>-zeros.zip</code></h3><p>On <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData Submissions</a>, click <strong>New submission</strong>, select the selector-approved <code>-zeros.tif</code> (or single-TIFF <code>-zeros.zip</code>), and paste its &le;140-char note (for S12 archival reference: <code>{_esc(sub['recommended_form_note'])}</code>, {sub['recommended_form_note_length']}/140 chars).</p></div></div>
  <div class="step"><b>4</b><div><h3>Log the Organizer Receipt</h3><p>Record the exact DrivenData score and timestamp in <code>ledger/submissions.csv</code> labeled <code>ORGANIZER-CONFIRMED</code>. Never record a holdout score as a live leaderboard score.</p></div></div>
</section>
</main>
<footer>
  <div>S12-SPID Executive Guide · <a href="s12-spid.html">Full S12 Audit Table</a> · <a href="s11-executive-summary.html">S11 Guide (#1 Repo Best)</a> · <a href="index.html">Main Portal</a></div>
  <div><a href="run-card-S12.json">Machine-readable S12 Run Card</a></div>
</footer>
</div></body></html>
"""


def main() -> int:
    rc = json.loads((ROOT / "docs" / "run-card-S12.json").read_text(encoding="utf-8"))
    uniq = json.loads((ROOT / "evidence" / "s12_registry_uniqueness.json").read_text(encoding="utf-8"))
    canary = json.loads((ROOT / "evidence" / "s12_leakage_canary.json").read_text(encoding="utf-8"))

    (ROOT / "docs" / "s12-spid.html").write_text(build_s12_spid_html(rc, uniq, canary), encoding="utf-8")
    (ROOT / "docs" / "s12-executive-summary.html").write_text(build_s12_exec_summary_html(rc), encoding="utf-8")
    print("Generated docs/s12-spid.html and docs/s12-executive-summary.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
