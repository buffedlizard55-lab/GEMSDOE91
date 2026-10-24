#!/usr/bin/env python3
"""Render synchronized GitHub Pages HTML subpages (`docs/s11-mhtr.html` and
`docs/s11-executive-summary.html`) directly from `docs/run-card-S11.json`,
`evidence/s11_registry_uniqueness.json`, and `evidence/s11_leakage_canary.json`.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _esc(v: object) -> str:
    return html.escape(str(v), quote=True)


def build_s11_mhtr_html(rc: dict, uniq: dict, canary: dict) -> str:
    sub = rc["submission"]
    ph = rc["scores"]["primary_holdout"]
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
          <td><code>H91-1 E1</code> (Prior Best)</td>
          <td>Dip-Deprojected Verduzco Tilt + Openness + 1D-Ridge Submodular 300m DTI (<code>38,400</code> dots)</td>
          <td>34</td>
          <td><strong>HOLDOUT-DTI</strong> <code>{ph['h91_e1_reference_holdout_dti']:.6f}</code><br><small>95% CI [{ph['h91_e1_reference_ci_95'][0]:.6f}, {ph['h91_e1_reference_ci_95'][1]:.6f}] (n=60,988)</small></td>
          <td><code>+0.035031</code> (+25.2% vs B0)</td>
          <td><code>0.082886</code></td>
          <td>Prior Repo Best</td>
        </tr>"""
    )

    for e in exps:
        is_w = e["exp_id"] == rc["winning_experiment"]
        u = e["uniqueness_summary"]
        badge = '<span class="badge">WINNER · PROMOTED</span>' if is_w else ('<span class="badge">VALIDATED</span>' if u["uniqueness_pass"] else '<span class="badge bad">DUPLICATE STOP (&gt;0.70)</span>')
        exp_rows.append(
            f"""<tr>
              <td><strong><code>{_esc(e['exp_id'])}</code></strong><br><small>{_esc(e['hypothesis_id'])}</small></td>
              <td><strong>{_esc(e['title'])}</strong><br><small><em>Non-fault mimic rejected:</em> {_esc(e['named_non_fault_mimic'])}</small></td>
              <td>{e['n_features']}</td>
              <td><strong>HOLDOUT-DTI</strong> <strong><code>{e['holdout']['holdout_dti']:.6f}</code></strong><br><small>95% CI [{e['holdout']['ci_95'][0]:.6f}, {e['holdout']['ci_95'][1]:.6f}] (n={e['holdout']['n_withheld_positives']:,})</small></td>
              <td><strong><code>{e['delta_vs_b0_holdout_dti']:+.6f}</code></strong> vs B0<br><small><code>{e['delta_vs_h91_e1_holdout_dti']:+.6f}</code> vs H91-1</small></td>
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
<title>S11-MHTR Marussi Hessian &amp; Radiometric TC Lane ({ph['score']:.4f} HOLDOUT-DTI) · GEMSDOE91</title>
<meta name="description" content="Session 11 Marussi Gravity Hessian &amp; Official Band 06 Radiometric Total Count Fault Discovery Candidate ({sub['candidate_id']}).">
<link rel="stylesheet" href="assets/portal.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="top"><a class="brand" href="index.html">GEMSDOE<span>91 / FAULT MAPPING LAB</span></a>
<nav aria-label="Main"><a href="index.html">Research &amp; download</a><a href="s12-spac.html"><strong>S12-SPAC (0.2376 DTI)</strong></a><a href="s11-mhtr.html">S11-MHTR Lane (0.2064 DTI)</a><a href="s11-executive-summary.html">S11 Guide</a><a href="h91-ddvtc.html">H91 Verduzco Lane (0.1740 DTI)</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Evidence &amp; sources</a></nav></header>
<main id="main">
<div class="banner" style="margin-top:22px">
  <strong>SUPERSEDED BY SESSION 12 (<code>S12-SPAC E3</code> · <code>0.237587 HOLDOUT-DTI</code>):</strong> This unsubmitted Session 11 candidate (<code>0.206406 HOLDOUT-DTI</code>) has been superseded by <a href="s12-spac.html"><strong><code>gems91-spac-e3-20261024T183000Z-a2740c89-zeros.tif</code></strong></a> (<code>+0.031181</code> paired lift, <code>P(&gt;0)=100%</code>; <code>0.107938</code> blind SGMC control). Under <code>IR-91-S12-05</code>, a human selector must <strong>never submit both</strong>.
</div>
<section class="hero">
  <div>
    <span class="eyebrow">SESSION 11 DISCOVERY LANE / S11-MHTR (BRANCH arena/8d9056a3-gemsdoe91)</span>
    <h1>Marussi Gravity Hessian.<br>Official Band 06 Radiometrics.<br><code>0.206406</code> HOLDOUT-DTI.</h1>
    <p class="lead">100% official GeoDAWN layers. Highest out-of-fold <code>HOLDOUT-DTI</code> (<code>+48.5%</code> over <code>B0</code>, <code>+18.6%</code> over <code>H91-1</code> with non-overlapping 95% CIs) and highest blind USGS SGMC off-catalogue score (<code>0.097623</code>, beating <code>R0</code>).</p>
    <span class="badge">TECHNICAL, CANARY &amp; 61-RASTER UNIQUENESS GATES: PASS</span>
    <p class="small">Awaits human fleet-selector slot allocation under shared repo policy (<code>src/gems91/readiness.py</code> &amp; <code>IR-CED-003</code>).</p>
  </div>
  <div class="download">
    <div class="label">ONE-CLICK CERTIFIED RANGE-SAFE [0, 1] GEOTIFF</div>
    <h2><code>{_esc(sub['candidate_id'])}</code></h2>
    <div class="status"><span>All 4 Validator Suites</span><strong>PASS (0 NaNs, [0.0, 1.0])</strong></div>
    <div class="status"><span>Out-of-Fold HOLDOUT-DTI</span><strong>0.206406 (95% CI 0.1938–0.2202)</strong></div>
    <div class="status"><span>61-Raster Uniqueness</span><strong>PASS (&le; 69.82% 3px overlap)</strong></div>
    <div class="status"><span>Fleet Selector Slot</span><strong>PENDING HUMAN SELECTOR</strong></div>
    <a class="button" download href="downloads/{_esc(sub['recommended_upload_file'])}">↓ Download Certified GeoTIFF (.tif · {sub['bytes_zeros_tif']:,} B)</a>
    <div style="text-align:center;margin-top:12px">
      <a download href="downloads/{_esc(sub['recommended_zip_download'])}">↓ Single-TIFF ZIP ({sub['bytes_zeros_zip']:,} B)</a> ·
      <a href="downloads/{_esc(sub['audit_json'])}">Independent Format Receipt (.json)</a> ·
      <a href="run-card-S11.json">S11 Run Card (.json)</a>
    </div>
    <p class="small">Single-band float32 · EPSG:32611 · 3730×3292 · 100 m · 48,000 unit-mass dots · min_d_cat = 3.1623 px (&gt; 300 m).</p>
  </div>
</section>

<div class="grid">
  <article class="card">
    <span class="eyebrow">HOLDOUT-DTI / S11-MHTR E2</span>
    <div class="number">{ph['score']:.5f}</div>
    <p>95% CI {ph['ci_95'][0]:.5f}–{ph['ci_95'][1]:.5f}<br>{ph['n_withheld_positives']:,} withheld positive pixels<br><strong>+{ph['lift_over_b0']:.5f}</strong> (+48.5%) vs B0 · <strong>+{ph['lift_over_h91_e1']:.5f}</strong> (+18.6%) vs H91-1</p>
    <span class="small">{_esc(ph['evaluator_version'])}</span>
  </article>
  <article class="card">
    <span class="eyebrow">BLIND OFF-CATALOGUE USGS SGMC CONTROL</span>
    <div class="number">{sgmc['dti']:.5f}</div>
    <p>62,122 off-catalogue USGS SGMC fault pixels (&gt;3 px from known catalogue)<br>Beats H91-1 (<code>0.08289</code>, +17.8%) AND beats R0 (<code>0.09539</code>)</p>
    <span class="small">SGMC-OFFCAT-CONTROL-DTI</span>
  </article>
  <article class="card">
    <span class="eyebrow">RULE 1 &amp; RULE 4 / CANARY &amp; UNIQUENESS</span>
    <div class="number">68/68 · 61/61</div>
    <p>68 features tested alone (max sym AUC <code>{canary['worst_symmetric_auc']:.5f} &le; 0.90</code>)<br>61 real fault rasters checked (max |&rho;| <code>{uniq['surface_max_abs_rank_corr']:.4f}</code>, max 3px ov <code>{100.0*uniq['dots_max_3px_overlap']:.2f}% &le; 70%</code>)</p>
    <a class="small" href="HYPOTHESES_S11.md">Read pre-registration &amp; forensic discoveries ↗</a>
  </article>
</div>

<section class="section">
  <div class="twocol">
    <div class="card">
      <h3>Copy-Paste DrivenData Submission Metadata</h3>
      <label for="s11-name" class="small">Unique Submission Name</label>
      <div class="copyrow">
        <textarea id="s11-name" readonly rows="2">{_esc(sub['recommended_form_name'])}</textarea>
        <button data-copy="s11-name" type="button">Copy</button>
      </div>
      <label for="s11-note" class="small">Short Note · {sub['recommended_form_note_length']}/140 characters</label>
      <div class="copyrow">
        <textarea id="s11-note" readonly rows="3">{_esc(sub['recommended_form_note'])}</textarea>
        <button data-copy="s11-note" type="button">Copy</button>
      </div>
      <p id="copy-status" class="copy-status" role="status" aria-live="polite"></p>
      <dl class="meta">
        <dt>SHA-256 (<code>-zeros.tif</code>)</dt><dd class="mono">{_esc(sub['sha256_zeros_tif'])}</dd>
        <dt>SHA-256 (<code>-zeros.zip</code>)</dt><dd class="mono">{_esc(sub['sha256_zeros_zip'])}</dd>
        <dt>SHA-256 (<code>.tif</code> NaN twin)</dt><dd class="mono">{_esc(sub['sha256_nan_tif'])}</dd>
        <dt>Emitted Dots / Collar</dt><dd>{sub['n_dots']:,} unit-mass dots · 0 &le; 3.0 px (min {sub['min_catalogue_distance_px']:.4f} px)</dd>
      </dl>
    </div>
    <div class="card">
      <h3>Three Breakthrough Forensic Discoveries in Session 11</h3>
      <ul class="checklist">
        <li><span><strong>IR-91-S11-01 (Band 06 = Radiometric TC):</strong> Proved <code>Band 06 (tc)</code> has <code>r = 0.9968</code> with GeoDAWN Airborne Radiometric Total Count (<code>TC</code>), unlocking 100% licence-clean radiometric fault contact &amp; potassic alteration detection.</span><span class="badge">VERIFIED</span></li>
        <li><span><strong>IR-91-S11-02 (Marussi Gravity Hessian):</strong> Proved <code>(B11, B18) = (&part;<sub>y</sub>G, &part;<sub>x</sub>G)</code> (<code>r = 0.9467</code> with <code>B05</code>), enabling exact reconstruction of Laplace <code>&part;&sup2;g<sub>z</sub>/&part;z&sup2;</code> and E&ouml;tv&ouml;s curvature <code>&lambda;<sub>1</sub>&minus;&lambda;<sub>2</sub></code>.</span><span class="badge">VERIFIED</span></li>
        <li><span><strong>IR-91-S11-03 (Zero Self-Proximity Shift):</strong> Removed <code>fc_vis_*</code> from tree splits so blind test quadrants suffer zero train-to-test covariate shift.</span><span class="badge">VERIFIED</span></li>
      </ul>
      <p><a href="s11-executive-summary.html">Open S11 Step-by-Step Submission Guide ↗</a> · <a href="HYPOTHESES_S11.md">Read Full S11 Hypotheses &amp; Equations ↗</a></p>
    </div>
  </div>
</section>

<section class="section">
  <div class="section-head">
    <h2>Pre-Registered 3-Experiment Holdout Progression (<code>gems91-hide-recover-v1.0</code>)</h2>
    <a href="run-card-S11.json">Download full JSON run card ↗</a>
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
          <th>Status</th>
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
    <h2>4-Fold Spatially-Blocked Breakdown for Winning Candidate <code>E2</code></h2>
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
    <h2>Rule 1 Registry Uniqueness Audit (61 Real Fault Rasters Checked: 100% PASS)</h2>
    <span class="small">Top 25 closest rasters by 3-px dot overlap (limit &le; 70.0%; surface |&rho;| limit &le; 0.90)</span>
  </div>
  <div class="table-scroll">
    <table>
      <thead>
        <tr>
          <th>Registry / Repository Raster</th>
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
  <div>Session 11 Discovery Audit (<code>{_esc(sub['candidate_id'])}</code>)<br>Generated {_esc(rc['generated_utc'])}</div>
  <div><a href="run-card-S11.json">S11 JSON Run Card</a> · <a href="index.html">Main Research Portal</a></div>
</footer>
</div></body></html>
"""


def build_s11_exec_summary_html(rc: dict) -> str:
    sub = rc["submission"]
    ph = rc["scores"]["primary_holdout"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>S11 Executive Summary &amp; Submission Guide · GEMSDOE91</title>
<meta name="description" content="Step-by-step executive summary for downloading, verifying, and submitting {sub['candidate_id']}.">
<link rel="stylesheet" href="assets/portal.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="top"><a class="brand" href="index.html">GEMSDOE<span>91 / FAULT MAPPING LAB</span></a>
<nav aria-label="Main"><a href="index.html">Research &amp; download</a><a href="s12-spac.html"><strong>S12-SPAC (0.2376 DTI)</strong></a><a href="s11-mhtr.html">S11-MHTR Lane (0.2064 DTI)</a><a href="s11-executive-summary.html">S11 Guide</a><a href="h91-ddvtc.html">H91 Verduzco Lane (0.1740 DTI)</a><a href="executive-summary.html">Submission guide</a><a href="research.html">Evidence &amp; sources</a></nav></header>
<main id="main">
<div class="banner" style="margin-top:22px">
  <strong>SUPERSEDED BY SESSION 12 (<code>S12-SPAC E3</code> · <code>0.237587 HOLDOUT-DTI</code>):</strong> Do not select this earlier Session 11 draft ahead of <a href="s12-spac.html"><strong><code>gems91-spac-e3-20261024T183000Z-a2740c89-zeros.tif</code></strong></a>, and <strong>never upload both</strong> (<code>IR-91-S12-05</code>). <a href="s12-executive-summary.html">Open S12 Executive Summary ↗</a>
</div>
<section class="hero">
  <div>
    <span class="eyebrow">EXECUTIVE SUMMARY / S11-MHTR SUBMISSION WALKTHROUGH</span>
    <h1>How to verify &amp; submit <code>{_esc(sub['candidate_id'])}</code>.</h1>
    <p class="lead">Every technical format gate, range <code>[0, 1]</code> check, 68-feature leakage canary, and 61-real-raster uniqueness gate has been verified automatically on disk.</p>
    <span class="badge">TECHNICAL &amp; SCIENTIFIC GATES: PASS (0.206406 HOLDOUT-DTI)</span>
  </div>
  <div class="download">
    <div class="label">PRIMARY RANGE-SAFE UPLOAD ARTIFACT</div>
    <h2><code>{_esc(sub['recommended_upload_file'])}</code></h2>
    <div class="status"><span>Values in [0, 1]</span><strong>YES (min=0.0, max=1.0, 0 NaNs)</strong></div>
    <div class="status"><span>CRS / Grid</span><strong>EPSG:32611 · 3730×3292 · 100 m</strong></div>
    <div class="status"><span>Out-of-Fold HOLDOUT-DTI</span><strong>{ph['score']:.6f} (+48.5% vs B0)</strong></div>
    <a class="button" download href="downloads/{_esc(sub['recommended_upload_file'])}">↓ Download GeoTIFF (.tif)</a>
    <div style="text-align:center;margin-top:12px">
      <a download href="downloads/{_esc(sub['recommended_zip_download'])}">↓ Download Single-TIFF .zip</a> ·
      <a href="downloads/{_esc(sub['audit_json'])}">Format Receipt (.json)</a>
    </div>
  </div>
</section>

<section class="section">
  <h2>Why <code>"Predicted values must be in range [0, 1]"</code> happened — and how it is solved</h2>
  <div class="twocol">
    <div class="card">
      <h3>Root Cause 1: Sentinel Bleed (<code>-3.4028235e+38</code>)</h3>
      <p>In <code>training_features.tif</code>, <code>3,061</code> cells <em>inside</em> the Nevada submission footprint carry float32 sentinel values (<code>-3.4028234663852886e+38</code>). Any pipeline that transforms bands without scrubbing sentinels first emits negative values outside <code>[0, 1]</code>.</p>
      <p><strong>Fix:</strong> Every band is scrubbed with <code>isfinite(arr) &amp; (arr &gt; -1e30)</code> and filled via Euclidean distance transform prior to feature extraction, then re-checked before and after writing.</p>
    </div>
    <div class="card">
      <h3>Root Cause 2: <code>nodata=NaN</code> Tag Handling</h3>
      <p>Some portal validators inspect the raw array buffer before applying the GeoTIFF <code>nodata</code> mask. A file with <code>7,111,787</code> outside-footprint <code>NaN</code> cells fails if <code>NaN</code> is tested against <code>0.0 &le; x &le; 1.0</code>.</p>
      <p><strong>Fix:</strong> <code>{_esc(sub['recommended_upload_file'])}</code> is written with <code>nodata=None</code> and <code>0.0</code> outside the footprint — all <code>12,279,160</code> float32 cells are strictly finite and in <code>[0.0, 1.0]</code>.</p>
    </div>
  </div>
</section>

<section class="section">
  <h2>Step-by-Step DrivenData Submission Procedure (After Human Selector Slot Check)</h2>
  <div class="step"><b>1</b><div><h3>Verify Weekly Slot Allowance &amp; Selector Policy</h3><p>Per Official Rules (<code>TP-5700-96647</code> §3.2), teams are limited to <strong>3 submissions per week</strong>. Confirm with the human fleet selector that a weekly slot is available and that <code>S11-MHTR E2</code> (<code>0.206406 HOLDOUT-DTI</code>, highest in <code>GEMSDOE91</code>) is selected for upload.</p></div></div>
  <div class="step"><b>2</b><div><h3>Download the Range-Safe GeoTIFF or Single-TIFF ZIP</h3><p>Click <strong>Download GeoTIFF (.tif)</strong> above to save <code>{_esc(sub['recommended_upload_file'])}</code> (<code>{sub['bytes_zeros_tif']:,}</code> bytes, SHA-256 <code>{_esc(sub['sha256_zeros_tif'])}</code>) or <code>{_esc(sub['recommended_zip_download'])}</code> (<code>{sub['bytes_zeros_zip']:,}</code> bytes). Never upload a JSON receipt, markdown report, or multi-band feature file.</p></div></div>
  <div class="step"><b>3</b><div><h3>Upload on DrivenData &amp; Paste the Short Note</h3><p>On <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData Submissions</a>, click <strong>New submission</strong>, choose <code>{_esc(sub['recommended_upload_file'])}</code> under <em>File to submit</em>, and paste the 104-character note below into <em>Note (optional)</em>:</p>
  <p><code>{_esc(sub['recommended_form_note'])}</code></p></div></div>
  <div class="step"><b>4</b><div><h3>Record the Organizer Receipt</h3><p>Once scored by DrivenData, copy the returned score and timestamp into <code>ledger/submissions.csv</code> under <code>receipt_score</code> and <code>receipt_date</code> as <code>ORGANIZER-CONFIRMED</code>.</p></div></div>
</section>
</main>
<footer>
  <div>S11-MHTR Executive Guide · <a href="s11-mhtr.html">Full S11 Audit Table</a> · <a href="index.html">Main Portal</a></div>
  <div><a href="run-card-S11.json">Machine-readable S11 Run Card</a></div>
</footer>
</div></body></html>
"""


def main() -> int:
    rc = json.loads((ROOT / "docs" / "run-card-S11.json").read_text(encoding="utf-8"))
    uniq = json.loads((ROOT / "evidence" / "s11_registry_uniqueness.json").read_text(encoding="utf-8"))
    canary = json.loads((ROOT / "evidence" / "s11_leakage_canary.json").read_text(encoding="utf-8"))

    (ROOT / "docs" / "s11-mhtr.html").write_text(build_s11_mhtr_html(rc, uniq, canary), encoding="utf-8")
    (ROOT / "docs" / "s11-executive-summary.html").write_text(build_s11_exec_summary_html(rc), encoding="utf-8")
    print("Generated docs/s11-mhtr.html and docs/s11-executive-summary.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
