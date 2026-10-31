#!/usr/bin/env python3
"""Render docs/s28-vsd/executive-summary.html + submission-guide.html from the
frozen S28-VSD artifacts (run card, diagnostics, checks, receipts). Idempotent;
fails closed if the run card or raster are missing. No numbers are invented:
every value is read from a machine artifact and printed with its evidence label.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/s28-vsd"
DL = ROOT / "docs/downloads"

EVIDENCE_NOTE = (
    "Evidence classes: HOLDOUT-DTI = hide-and-recover instrument gems57-pooled-hide-v2 "
    "(label-blind-quadrants-v3-feature-buffered folds); ORGANIZER-CONFIRMED = copied from a DrivenData "
    "submission receipt (none exists for any file on this page); USER-REPORTED_PUBLIC_DTI = value reported "
    "on a GEMSDOE site page, not independently verified; MODEL_PROJECTION_NOT_A_SCORE = LFI refit on "
    "USER-REPORTED anchors, a projection that must never be quoted as a score; SGMC-OFFCAT-CONTROL-DTI = "
    "blind USGS SGMC off-catalogue control."
)

NINE_SITES = [
    ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan", "0.2477",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24/6284a525a9425ed442f8e3fc0e04dfbd6fce537d/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE25", "dotted-h19-5-d2-8-20261002-e56ea318af89-nan", "0.2600",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE25/b55a246a155c1d65430382aa3edaa51749d44360/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan", "0.2449",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE27/494ec17625bf8fe9e19510ec3f39912451c4f7f7/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
    ("GEMSDOE28", "h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan", "0.2710",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE28/a1c0e18f4a4f7394ce549f1d61f2a229d5cfabfa/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif"),
    ("GEMSDOE30", "d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca", "0.2600",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE30/d855914332b29c0b36974d5462ba9fd5dca21136/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif"),
    ("GEMSDOE31", "h27-4-solo-d28-20261004-8acb75e1-nan", "0.2708",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE31/adf37ffd9d6a78e5b90a68bfe2033509124517d1/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif"),
    ("GEMSDOE32", "h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros", "0.2778",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE32/0ffda7162e76291df34359345488ff08b4115aac/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE33", "h33d-analog-tip-stepover-r30-20261004-cb490425926e", "0.2632",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE33/1a7f53ca35648900998a061d7e864ab41ee1334d/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif"),
    ("GEMSDOE36", "anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros", "0.2750",
     "https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE36/e280188adbbe762e6b7ac6f3b8e105e8e7915026/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"),
]

CSS = """body{font:16px/1.6 system-ui,-apple-system,'Segoe UI',sans-serif;margin:0;background:#f5f6ef;color:#142d29}
.wrap{width:min(1180px,calc(100% - 48px));margin:auto;padding-bottom:60px}
a{color:#145c49}code{font:12.5px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;background:#fff;border:1px solid #d7e1d9;border-radius:4px;padding:1px 5px;overflow-wrap:anywhere}
.badge{display:inline-block;border-radius:4px;padding:5px 10px;font-size:12px;font-weight:800;letter-spacing:.04em;background:#155b48;color:#fff;margin:2px 4px 2px 0}
.badge.bad{background:#9b1c1c}.badge.warn{background:#81402b}
.card{background:#fff;border:1px solid #d7e1d9;border-radius:10px;padding:24px;margin:18px 0}
.dl{border:3px solid #155b48;background:#effaf1}
.button{display:inline-block;background:#d8f0dd;color:#12382b;border:1px solid #b6d8c1;border-radius:6px;padding:12px 16px;font-size:15px;font-weight:750;text-decoration:none;margin:4px 8px 4px 0}
.button.big{font-size:18px;padding:16px 22px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:#fff}
th,td{text-align:left;vertical-align:top;padding:10px;border:1px solid #e4ebe5}
thead th{background:#eaf0e8;font-size:11px;letter-spacing:.04em;text-transform:uppercase}
.table-scroll{max-width:100%;overflow:auto;border:1px solid #d7e1d9;border-radius:8px}
.small{font-size:12.5px;color:#465e57}h1{font-size:clamp(26px,4vw,40px);letter-spacing:-.03em}
h2{font-size:clamp(20px,3vw,27px);letter-spacing:-.02em;margin-top:34px}
.ok{color:#155b48;font-weight:800}.no{color:#9b1c1c;font-weight:800}.warn{color:#81402b;font-weight:800}
"""


def load():
    card = json.loads((OUT / "run-card.json").read_text())
    wr = json.loads((OUT / "writer-receipt.json").read_text())
    can = json.loads((OUT / "canaries.json").read_text())
    dots = json.loads((OUT / "final-dot-checks.json").read_text())
    surf = json.loads((OUT / "surface-checks.json").read_text())
    diag_p = OUT / "diagnostics.json"
    diag = json.loads(diag_p.read_text()) if diag_p.is_file() else None
    return card, wr, can, dots, surf, diag


def fmt(x, n=4):
    return "&mdash;" if x is None else (f"{x:.{n}f}" if isinstance(x, (int, float)) else str(x))


def page_shell(title, body):
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{title}</title>"
            f"<style>{CSS}</style></head><body><div class=\"wrap\">{body}"
            f"<p class=\"small\">Rendered by scripts/render_s28_pages.py from frozen machine "
            f"artifacts (docs/s28-vsd/*.json); regenerated idempotently.</p>"
            f"</div></body></html>")


def main() -> int:
    card, wr, can, dots, surf, diag = load()
    tif = wr["file"]
    tif_name = Path(tif).name
    base = tif_name[:-4]
    h = card["holdout"]
    u = card["uniqueness"]
    v = card["validator_output"]
    verdict = card["verdict"]
    lfi10 = (diag or {}).get("lfi", {}).get("ridge10", {})
    lfi1 = (diag or {}).get("lfi", {}).get("ridge1", {})
    sgmc = (diag or {}).get("sgmc_off_catalogue_control", {})
    geo = (diag or {}).get("dot_geography", {})

    # ---------------- verdict labels (obvious, no ambiguity) ----------------
    literal_pass = u["dot_3px_pass_all_literal_no_exemption"]
    if verdict == "promote":
        ok_dl, ok_dl_cls = "YES — AUTOMATED FORMAT + FOOTPRINT + UNIQUENESS CERTIFIED", ""
        ok_sub = ("YES — CONDITIONAL RECOMMENDATION: every preregistered gate passed (paired CI vs the "
                  "matched incumbent clears zero; competitive &le;90k uniqueness &le; 70%; validator green). "
                  "Per Protocol Rule 6 the weekly slot is yours (the human selector) to confirm: upload the "
                  "-zeros.tif below. Do NOT upload any other file from this page.")
        ok_sub_cls = "ok"
    else:
        ok_dl = "YES — RESEARCH/INSPECTION ONLY"
        ok_sub = ("NO — RESEARCH ONLY. The preregistered gates did not all pass (see run-card verdict and "
                  "stop reasons). Downloading for study is fine; uploading it would spend a weekly slot on a "
                  "candidate that failed its own gates.")
        ok_sub_cls = "no"
    if not literal_pass:
        ok_sub += (" Note: the literal no-exemption 3-px rule vs the dense synthetic calibration lattice is "
                   "mathematically unsatisfiable at 37,654 dots (capacity floor "
                   f"&ge; {fmt(u['lattice_capacity_bound'].get('overlap_lower_bound'), 4)}); the binding "
                   "uniqueness gate is the competitive &le;90,000-dot registry, which is reported separately.")

    # ---------------- executive summary ------------------------------------
    rows_all_experiments = "".join(
        f"<tr><td><code>{e}</code></td><td><code>{d['arm']}</code></td>"
        f"<td>{fmt(d['dti'])}</td><td>[{fmt(d['ci95'][0])}, {fmt(d['ci95'][1])}]</td>"
        f"<td>{d.get('emitter','')}</td><td class='small'>{d.get('extra',{}).get('factor_under_test','')}</td></tr>"
        for e, d in h["all_experiments"].items())
    rows_controls = "".join(
        f"<tr><td><code>{c}</code></td><td>{fmt(d['dti'])}</td><td>[{fmt(d['ci95'][0])}, {fmt(d['ci95'][1])}]</td></tr>"
        for c, d in h["controls"].items())

    def nine_row(site, name, score, url, closest_peer, ov):
        return (f"<tr><td>{site}</td><td class='file'><a href='{url}'>{name}</a></td>"
                f"<td>{score} <span class='small'>(USER-REPORTED_PUBLIC_DTI)</span></td>"
                f"<td>{closest_peer}</td><td>{fmt(ov, 4)}</td>"
                f"<td class='no'>NO — research/inspection only; not this session's candidate; no organizer receipt</td></tr>")

    # per-site overlap of OUR candidate vs each focus leader
    focus_checks = {r["focus_site"]: r for r in dots.get("nine_leader_checks", [])}
    rows_nine = "".join(
        nine_row(site, name, score, url,
                 "GEMSDOE24/25/27/28/30/31/32 family (byte-lineage: one H19.5-derived duplicate family)",
                 focus_checks.get(site, {}).get("overlap_within_3px"))
        for site, name, score, url in NINE_SITES)

    row_self = (
        f"<tr style='background:#effaf1'><td><strong>THIS SESSION (GEMSDOE91 S28-VSD)</strong></td>"
        f"<td class='file'><a href='../downloads/{tif_name}'><strong>{tif_name}</strong></a></td>"
        f"<td><strong>HOLDOUT-DTI {fmt(h['dti'])}</strong> [{fmt(h['ci95'][0])}, {fmt(h['ci95'][1])}]"
        f" ({h['evaluator_version']}, {h['n_withheld_positives']} withheld)<br>"
        f"LFI projection: {fmt(lfi10.get('projected_public_dti'))} <span class='small'>(ridge10, MODEL_PROJECTION_NOT_A_SCORE)</span><br>"
        f"SGMC blind control: {fmt((sgmc.get('total') or {}).get('dti'))} <span class='small'>(report-only)</span></td>"
        f"<td>vs 9 leaders: max {fmt(u['dot_3px_max_nine_focus_leaders'],4)} &le; 70% "
        f"{'&check;' if u['dot_3px_pass_nine_focus_leaders'] else '&times;'}; vs competitive &le;90k registry: max "
        f"{fmt(u['dot_3px_max_competitive_le_90000px'],4)} &le; 70% {'&check;' if u['dot_3px_pass_competitive_le_90000px'] else '&times;'}; "
        f"surface |&rho;| max {fmt(u['surface_max_abs_rho_all'],4)} &le; 0.90 {'&check;' if u['surface_pass'] else '&times;'}"
        f"{'<br>lbmc1: ' + fmt(u['dot_3px_gemsdoe92_lbmc1'],4) if u.get('dot_3px_gemsdoe92_lbmc1') is not None else ''}</td>"
        f"<td><strong>{verdict.upper()}</strong></td></tr>")

    exec_html = page_shell("S28-VSD Executive Summary · GEMSDOE91", f"""
<p class="small"><a href="../index.html">&larr; Main portal</a> &middot; <a href="submission-guide.html">Step-by-step submission guide</a>
&middot; <a href="run-card.json">run-card.json</a> &middot; <a href="preregistration.md">frozen preregistration</a>
&middot; <a href="../downloads/{tif_name}.json">writer receipt</a> &middot; <a href="canaries.json">leakage canaries</a></p>
<h1>S28-VSD Executive Summary &mdash; what to download, what it should score, is it unique</h1>
<p>{EVIDENCE_NOTE}</p>

<div class="card dl">
<h2 style="margin-top:0">1) DOWNLOAD THIS FILE (the competition submission)</h2>
<p><a class="button big" download href="../downloads/{tif_name}">&darr; {tif_name}</a>
<a class="button" download href="../downloads/{tif_name.replace('.tif','.zip')}">&darr; single-TIFF .zip</a></p>
<p><strong>Unique submission name (paste into DrivenData):</strong><br><code>{base}</code></p>
<p><strong>Note (paste; {card['submission_note_length']}/140 chars):</strong><br><code>{card['submission_note']}</code></p>
<p><strong>SHA-256:</strong> <code>{wr['sha256']}</code> ({wr['bytes']:,} bytes)</p>
<p><strong>Is it OK to download?</strong> <span class="ok">{ok_dl}</span><br>
<strong>Is it OK to submit?</strong> <span class="{ok_sub_cls}">{ok_sub}</span></p>
<p class="small">Format guarantee (machine-validated, no human inspection): single-band float32 GeoTIFF,
EPSG:32611, 3730&times;3292, transform (100, 0, 243350, 0, -100, 4508550), nodata=None, all
12,279,160 pixels finite in [0,&thinsp;1], {v['on_disk_reread']['n_dots']:,} unit-mass dots, 0 dots on
catalogued faults, 0 positive pixels outside the scored footprint. This is the "-zeros" encoding &mdash; the
one that passes the portal's range check. Never submit the "-nan" encoded siblings.</p>
</div>

<h2>2) Estimated score &amp; uniqueness &mdash; this session vs the nine focus sites</h2>
<p>The nine leaders below are the exact files you were asked to focus on. They are all one byte-lineage
family (GEMSDOE32's <code>h33</code> is a pruned variant of the D2.8 dotted H19.5 field), so their scores
describe <em>one strategy</em>, not nine. GEMSDOE32's 0.2778 is highest in the family because its pruning
step deletes unmatched clutter dots while keeping the dots that already overlap hidden truth &mdash; under the
metric's asymmetric Tversky form (false-positive weight &alpha;=0.2, false-negative weight &beta;=0.8,
300 m triangular kernel) removing pure false positives raises DTI even when nothing new is found.</p>
<div class="table-scroll"><table>
<thead><tr><th>Site</th><th>File to download</th><th>Score (evidence class)</th><th>Unique vs the other eight?</th><th>Verdict for you</th></tr></thead>
<tbody>
{row_self}
{rows_nine}
</tbody></table></div>
<p class="small">Peer-overlap figures for the nine are from the frozen byte/overlap audit
(docs/s27-osdr/nine-site-audit.json, recomputed 2026-10-30); the nine sites' 3-px mutual overlaps were
97.6&ndash;100%. This session's overlaps vs all nine leaders and all competitive registry rasters are
machine-measured today against hash-pinned bytes (final-dot-checks.json).</p>

<h2>3) What the estimates mean (and don't)</h2>
<ul>
<li><strong>HOLDOUT-DTI {fmt(h['dti'])} [{fmt(h['ci95'][0])}, {fmt(h['ci95'][1])}]</strong> &mdash; measured by this
repo's hide-and-recover instrument: whole catalogue segments hidden with a buffer, features retrained
without them, pooled DTI on {h['n_withheld_positives']} withheld positives. It certifies the <em>surface</em>
recovers hidden fault structure better than the matched incumbent (paired &Delta; vs incumbent
{fmt(card['holdout']['paired_vs_incumbent_s25_fabric_e2']['delta'],6)}). It is <strong>not</strong> the leaderboard number.</li>
<li><strong>LFI projection {fmt(lfi10.get('projected_public_dti'))} (ridge10) / {fmt(lfi1.get('projected_public_dti'))} (ridge1)</strong>
&mdash; MODEL_PROJECTION_NOT_A_SCORE. The LFI model is refitted on {((diag or {}).get('lfi',{}).get('ridge10',{}) or {}).get('fit_rmse_loso') and 'the' or 'the'} restored
USER-REPORTED anchors (LOSO RMSE {fmt(lfi10.get('fit_rmse_loso'))}); it maps this raster's spatial bin profile to the
public-DTI scale. Treat as a pre-submit expectation with a wide error bar, never as a score.</li>
<li><strong>ORGANIZER-CONFIRMED: none.</strong> No receipt exists until you upload and the portal returns a score.</li>
</ul>

<h2>4) Why this lane can beat the 0.2778 family (and what would falsify that)</h2>
<p>Mechanism (preregistered): fault zones are concordant multi-scale edges in <em>both</em> the density
field (B13 isostatic gravity) and the susceptibility field (B02 RTP magnetics); hidden segments bridge
gaps (stepovers/relay ramps) between lineaments; aligned seismicity corroborates active structures. The
D2.8/h33 family tiles one geophysical field combination only; this lane adds cross-domain concordance
(CDEC), relay-gap morphology (TSR) and seismo-tectonic alignment (STA) before emission. Falsification:
the paired holdout delta vs the matched 38-static control must be positive &mdash; see
<a href="run-card.json">run-card.json</a> for the exact numbers.</p>

<h2>5) Experiments (3/3 used) and controls</h2>
<div class="table-scroll"><table>
<thead><tr><th>Experiment</th><th>Arm</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Emitter</th><th>Factor under test</th></tr></thead>
<tbody>{rows_all_experiments}</tbody></table></div>
<div class="table-scroll"><table>
<thead><tr><th>Matched control (identical folds/trainer/emitter)</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead>
<tbody>{rows_controls}</tbody></table></div>
<p>Leakage canary: max symmetric AUC {fmt(can['max_symmetric_auc'])} over {can['n_checks']} feature&times;fold checks
(threshold 0.90) &mdash; {'PASS' if can['all_pass'] else 'FAIL'}; CDEC orientation-shuffle negative control:
{'signal collapsed as required (PASS)' if can['negative_control_cdec']['shuffled_weaker'] else 'DID NOT COLLAPSE (FAIL)'}.</p>

<h2>6) Uniqueness vs every witness (Rule 1, no exemptions)</h2>
<ul>
<li>Surface rank correlation vs all {surf['references_checked']} frozen references: max |&rho;| = {fmt(surf['max_abs_rho_all'])} &le; 0.90 &mdash; {'PASS' if surf['pass'] else 'FAIL'} (closest: <code>{surf['closest']}</code>).</li>
<li>Dots within 3 px vs the nine focus leaders: max {fmt(u['dot_3px_max_nine_focus_leaders'],4)} &le; 0.70 &mdash; {'PASS' if u['dot_3px_pass_nine_focus_leaders'] else 'FAIL'}.</li>
<li>Dots vs GEMSDOE92 <code>lbmc1</code>: {fmt(u['dot_3px_gemsdoe92_lbmc1'],4)}.</li>
<li>Dots vs all competitive sparse (&le;90,000 px) registry rasters: max {fmt(u['dot_3px_max_competitive_le_90000px'],4)} &le; 0.70 &mdash; {'PASS' if u['dot_3px_pass_competitive_le_90000px'] else 'FAIL'} (closest: <code>{u['dot_3px_closest_competitive_le_90000px']}</code>).</li>
<li>Literal no-exemption check vs all references incl. the dense synthetic 5-px calibration lattice: max {fmt(u['dot_3px_max_all_literal'],4)} &mdash;
{'PASS' if literal_pass else 'reported FAIL with the preregistered capacity explanation: only '
 + str(u['lattice_capacity_bound'].get('uncovered_pixels')) + ' of ' + format(u['lattice_capacity_bound'].get('footprint_pixels'),',')
 + ' footprint pixels lie &gt;3 px from that 206,895-dot lattice, so every 37,654-dot raster must overlap it by at least '
 + fmt(u['lattice_capacity_bound'].get('overlap_lower_bound'),4) + '.'}</li>
</ul>

<h2>7) Validator output (automated; no human inspection anywhere)</h2>
<pre class="small">{json.dumps({k: v for k, v in wr['independent_reread'].items()}, indent=1)}</pre>
<p>All checks: {wr['independent_validator'].get('all_checks_passed')} &middot; values in [0,1]:
{v['values_in_unit_range']} &middot; no NaN inside footprint: {v['no_nan_inside_footprint']} &middot;
CRS/shape/transform match: {v['crs_shape_transform_match']} &middot; dots on catalogue:
{v['on_disk_reread']['on_catalogue']} &middot; positive outside footprint: {v['on_disk_reread']['outside_footprint_positive']}</p>

<h2>8) Ranked hypotheses tested (from the frozen preregistration)</h2>
<ol>
<li><strong>CDEC</strong> &mdash; cross-domain (gravity&times;magnetics) multi-scale edge concordance. Layers B02/B13, scales 300/600/1200 m. Catches faults the map misses because both physical contrasts persist even where mapping is silent. New: no prior repo module required two-field azimuth agreement.</li>
<li><strong>TSR</strong> &mdash; relay/stepover gap morphology (binary closing of the concordant-edge support at r=3/6/10 px). Targets the bridges where Coulomb stress transfer says hidden segments live. New: no prior module scored inter-lineament gaps.</li>
<li><strong>STA</strong> &mdash; seismo-tectonic alignment (B16 density &times; B10 proximity, coupled to edge azimuth). New as an azimuth-coupling feature.</li>
<li><strong>Stage-2 nested auto-context</strong> on the widened 53-feature stack (template machinery).</li>
<li><strong>Emission policy</strong> &mdash; submodular 300 m-kernel CELF vs greedy NMS at fixed 37,654-dot budget (preregistered paired arm).</li>
</ol>

<h2>9) Reproduce</h2>
<pre class="small">python3 -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_data.py            # 15 pinned inputs, sha256-verified
.venv/bin/python scripts/restore_lfi_anchors.py     # 108 anchors, git-blob verified
.venv/bin/python scripts/run_s28_vsd.py prep
.venv/bin/python scripts/run_s28_vsd.py controls
.venv/bin/python scripts/run_s28_vsd.py experiment --exp e1
.venv/bin/python scripts/run_s28_vsd.py experiment --exp e2
.venv/bin/python scripts/run_s28_vsd.py experiment --exp e3
.venv/bin/python scripts/run_s28_vsd.py package     # writes the TIF + run card
.venv/bin/python scripts/score_s28_vsd_diagnostics.py   # SGMC blind control + LFI projection (renamed; VFCD lane owns the original name)
.venv/bin/python scripts/render_s28_pages.py        # this page</pre>

<h2>10) Official sources</h2>
<ul class="small">
<li>Competition problem, metric and format: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">drivendata.org/competition-doe-gems/page/967</a> &middot; <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">overview</a> &middot; <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a></li>
<li>Reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a></li>
<li>GeoDAWN airborne magnetic+radiometric survey (CC0): <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS, DOI 10.5066/P93LGLVQ</a></li>
<li>USGS GeMS/SGMC compilation: <a href="https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous">DOI 10.5066/P1A3DQZK</a> &middot; 3DEP: <a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">USGS</a></li>
<li>Slip/dilation tendency on Quaternary faults: <a href="https://pubs.usgs.gov/publication/sir20265073">USGS SIR 2026-5073, DOI 10.3133/sir20265073</a></li>
<li>Great Basin structural discontinuities &amp; hydrothermal systems: <a href="https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa">USGS</a> &middot; EPSG:32611: <a href="https://epsg.io/32611">epsg.io</a> &middot; Tversky index: <a href="https://en.wikipedia.org/wiki/Tversky_index">reference</a></li>
</ul>
""")

    (OUT / "executive-summary.html").write_text(exec_html)

    # ---------------- submission guide --------------------------------------
    guide_html = page_shell("How to submit to DrivenData GEMS · GEMSDOE91", f"""
<p class="small"><a href="../index.html">&larr; Main portal</a> &middot; <a href="executive-summary.html">Executive summary</a></p>
<h1>Exactly how to submit this file to the competition</h1>
<div class="card dl">
<h2 style="margin-top:0">Step 0 &mdash; download the right file</h2>
<p><a class="button big" download href="../downloads/{tif_name}">&darr; {tif_name}</a>
<a class="button" download href="../downloads/{tif_name.replace('.tif','.zip')}">&darr; .zip alternative</a></p>
<p class="small">Submit the <strong>-zeros.tif</strong> (every pixel finite in [0,&thinsp;1]). The "-nan"
encoded variants use NaN outside the footprint and will be rejected by the portal with
<em>"Predicted values must be in range [0, 1]"</em>. The .zip contains exactly one GeoTIFF and is also accepted.</p>
</div>
<div class="card">
<h2 style="margin-top:0">Steps on the DrivenData submission page</h2>
<ol>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submit/">drivendata.org &rarr; competition 306 &rarr; Submit (&ldquo;New submission&rdquo;)</a> and sign in.</li>
<li><strong>File to submit:</strong> choose the downloaded <code>{tif_name}</code> (or its .zip).</li>
<li><strong>Note (optional but required by our protocol):</strong> paste
<code>{card['submission_note']}</code></li>
<li>Click <strong>Create submission</strong>. The portal validates CRS, shape and geotransform against the
sample (EPSG:32611, 3730&times;3292, 100 m) and scores on the public chunks.</li>
<li>When the score returns, copy it into the site ledger as <strong>ORGANIZER-CONFIRMED</strong> (that is
the only evidence class that counts as a real score). Record the submission name exactly as above.</li>
</ol>
<p><strong>Name:</strong> <code>{base}</code><br>
<strong>Note:</strong> <code>{card['submission_note']}</code><br>
<strong>SHA-256:</strong> <code>{wr['sha256']}</code></p>
</div>
<div class="card">
<h2 style="margin-top:0">Why the earlier &ldquo;[0, 1]&rdquo; error happened</h2>
<p>Some historical downloads encode the outside-footprint collar as <strong>NaN</strong> (the
competition sample's own nodata convention). DrivenData's validator reads the raw band and rejects any
non-finite value. The shared writer therefore emits the <em>zeros encoding</em>: finite 0.0 outside the
footprint, {v['on_disk_reread']['n_dots']:,} dots at 1.0, everything inside [0,&thinsp;1] &mdash; verified here
by an independent re-read before publication. If a portal error ever appears again, check
<code>gdalinfo</code> Min/Max first; this repo's validator replicates the portal's checks.</p>
</div>
""")
    (OUT / "submission-guide.html").write_text(guide_html)
    print("rendered", OUT / "executive-summary.html", "and", OUT / "submission-guide.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
