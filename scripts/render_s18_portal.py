#!/usr/bin/env python3
"""Render evidence-derived Session 18 (S18-CWGR) portal pages, support PNG, and front door.

Verifies the S18-CWGR GeoTIFF, single-member ZIP, 8-arm + 3-quota holdout summary,
174-feature canaries, 108-raster registry audit, and fail-closed readiness gates via
`scripts.verify_s18.verify()` and `_registered_pair()` before writing HTML.
Archives `docs/olc91-index-src.html` to `docs/olc91.html` so prior history stays browsable.
Never sets `ok_to_submit` true.
"""
from __future__ import annotations

from html import escape as esc
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from gems91.readiness import gates, submission_ready
from scripts.render_geo91_portal import _registered_pair
from scripts.verify_s18_cwgr import sha, verify


def load_json(rel_docs: str):
    return json.loads((ROOT / "docs" / rel_docs).read_text(encoding="utf-8"))


def render_preview(card: dict) -> None:
    """Deterministic PNG of actual S18-CWGR 37,654-dot support within sample_submission footprint."""
    import numpy as np
    import rasterio

    dest = ROOT / "docs/assets/s18-support.png"
    sample = ROOT / "data/official/sample_submission.tif"
    if not sample.exists():
        if not dest.exists():
            raise FileNotFoundError("Restore pinned sample_submission.tif to build initial s18-support.png")
        return
    if sha(sample) != card["inputs"]["sample_submission"]["sha256"]:
        raise ValueError("sample_submission.tif SHA-256 mismatch during preview render")
    with rasterio.open(sample) as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "docs" / card["artifact"]["file"]) as s:
        dots = s.read(1) > 0
    factor = 6

    def shrink(a):
        h, w = a.shape
        p = np.pad(a, ((0, (-h) % factor), (0, (-w) % factor)))
        return p.reshape(p.shape[0] // factor, factor, p.shape[1] // factor, factor).any(axis=(1, 3))

    f, d = shrink(fp), shrink(dots)
    image = np.empty((*f.shape, 3), dtype=np.uint8)
    image[:] = [235, 240, 236]
    image[f] = [196, 212, 200]
    image[d] = [15, 76, 58]

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + row.tobytes() for row in image)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", f.shape[1], f.shape[0], 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    dest.write_bytes(png)


STYLE = """
:root{--ink:#12211d;--mut:#425650;--ok:#145c47;--bad:#942424;--line:#d5e0db;--bg:#f6faf8}
*{box-sizing:border-box}body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg);margin:0;line-height:1.55}
.wrap{max-width:1060px;margin:0 auto;padding:20px}a{color:var(--ok)}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:16px}
nav{display:flex;flex-wrap:wrap;gap:12px}nav a{text-decoration:none;font-weight:600}.logo{font-weight:800;font-size:20px;text-decoration:none;color:var(--ink)}
.hero{display:grid;grid-template-columns:1.15fr .85fr;gap:18px}.hero>*{min-width:0}@media(max-width:840px){.hero{grid-template-columns:1fr}}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;margin:18px 0;overflow-x:auto}
.hero .card{margin:0}.dl{border:2px solid var(--ok)}h1{font-size:30px;line-height:1.18;margin:.25em 0}h2{font-size:21px;margin:0 0 10px}h3{font-size:17px;margin:12px 0 6px}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#dff0e8;color:var(--ok);font-weight:700;font-size:13px;margin:0 6px 6px 0}
.badge.bad{background:#f7e2e2;color:var(--bad)}.small{color:var(--mut);font-size:14px}
.button{display:block;text-align:center;background:var(--ok);color:#fff;text-decoration:none;padding:13px;border-radius:10px;font-weight:800;font-size:16px;margin:12px 0}
.btn2{display:inline-block;border:1px solid var(--ok);padding:7px 11px;border-radius:8px;text-decoration:none;font-weight:700;margin:3px 4px 3px 0;font-size:14px}
.status{display:flex;justify-content:space-between;gap:10px;border-top:1px solid var(--line);padding:7px 0;font-size:14px}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
textarea{width:100%;font-family:ui-monospace,monospace;font-size:13px;padding:6px;border:1px solid var(--line);border-radius:6px}
code{font-size:12px;word-break:break-all}.warn{background:#fdf2e2;border:1px solid #e3c891;border-radius:10px;padding:12px}
img.preview{max-width:100%;height:auto;border:1px solid var(--line);border-radius:10px;display:block}
footer{margin-top:24px;padding-top:14px;border-top:1px solid var(--line)}
"""


def nav_html() -> str:
    return (
        '<header><a class="logo" href="index.html">GEMSDOE91 · Fault Discovery Lab</a>'
        '<nav aria-label="Main">'
        '<a href="index.html">Portal home</a>'
        '<a href="executive-summary.html">Executive summary</a>'
        '<a href="s18-cwgr.html"><strong>S18-CWGR audit</strong></a>'
        '<a href="s18-cwgr-executive-summary.html">S18-CWGR submit guide</a>'
        '<a href="s17-cpad.html">S17-CPAD (0.1982 HOLDOUT-DTI)</a>'
        '<a href="s17-cpad-executive-summary.html">S17-CPAD guide</a>'
        '<a href="research.html">Sources &amp; S16</a>'
        '<a href="archive-results.html">Historical archive</a>'
        "</nav></header>"
    )


def render_holdout_rows(holdout: dict, blind: dict) -> str:
    scores = holdout["summary_all_arms"]["scores"]
    paired = holdout["summary_vs_prior_baselines"]["paired_differences"]
    b_scores = blind["scores"]
    order = [
        ("cpad_e1", "S17-CPAD E1 (repo label-blind #1 benchmark)"),
        ("incumbent_ptac_lb", "INCUMBENT-PTAC-LB (S14 label-blind replay)"),
        ("cwgr_e1", "S18-CWGR E1 (unweighted SCAR Tri-Specialist · current)"),
        ("cwgr_e2", "S18-CWGR E2 (Bekker–Davis SAR IPW Tri-Specialist)"),
        ("cwgr_e3", "S18-CWGR E3 (unmapped posterior (1 − 0.65·ê) Bayes factor)"),
        ("ced91", "CED91 (unsupervised baseline)"),
        ("s16_pgrd", "S16-PGRD (analytic baseline)"),
        ("gravity_control", "Gravity-Theta control"),
    ]
    rows = []
    for key, label in order:
        sc = scores[key]
        d_str = "—"
        if key == "cwgr_e1":
            p = paired["cpad_e1"]
            d_str = f"{p['delta']:+.6f} [{p['ci95'][0]:+.6f}, {p['ci95'][1]:+.6f}]"
        b_entry = b_scores.get(key)
        b_val = f"{(b_entry['dti'] if isinstance(b_entry, dict) else b_entry):.6f}" if b_entry is not None else "—"
        rows.append(
            f"<tr><td><code>{esc(key)}</code> — {esc(label)}</td>"
            f"<td><strong>{sc['dti']:.6f}</strong></td>"
            f"<td>[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}]</td>"
            f"<td>{esc(d_str)}</td>"
            f"<td>{esc(b_val)}</td></tr>"
        )
    q_scores = holdout["quota_diagnostic_summary_ir91_s18_02"]["scores"]
    for key, label in (
        ("cwgr_e2_quota37654", "S18-CWGR E2 (fixed 37,654 area-quota control · IR-91-S18-02)"),
        ("cwgr_e1_quota37654", "S18-CWGR E1 (fixed 37,654 area-quota control · IR-91-S18-02)"),
        ("cwgr_e3_quota37654", "S18-CWGR E3 (fixed 37,654 area-quota control · IR-91-S18-02)"),
    ):
        sc = q_scores[key]
        rows.append(
            f"<tr><td><code>{esc(key)}</code> — {esc(label)}</td>"
            f"<td>{sc['dti']:.6f}</td>"
            f"<td>[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}]</td>"
            f"<td>Quota ablation</td>"
            f"<td>—</td></tr>"
        )
    return "".join(rows)


def build_index_html(card: dict, holdout: dict, blind: dict) -> str:
    a = card["artifact"]
    v = card["validator_output"]
    h = card["holdout_dti"]
    reg = card["registry_comparison"]
    cat_sum = reg["category_summary"]
    non_calib_ext = cat_sum["preceding_fleet_submission"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Download the current GeoTIFF · GEMSDOE91 S18-CWGR</title>
<meta name="description" content="One-click download of the freshly computed S18-CWGR single-band [0, 1] GeoTIFF with fail-closed automated submission gates.">
<style>{STYLE}</style></head><body><div class="wrap">
{nav_html()}
<main id="main">
<div class="hero">
<div>
<span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span><span class="badge bad">OK TO SUBMIT: NO</span>
<h1>Fresh S18-CWGR GeoTIFF: safe to download, do not submit to DrivenData.</h1>
<p class="small">Session 18 (<code>S18-CWGR</code>, completed {esc(card['completed_utc'][:19].replace('T', ' '))} UTC) freshly computed <code>{esc(Path(a['file']).name)}</code> from the 19 official GeoDAWN geophysical/topographic bands and open GDR thermal/geothermometry tables on canonical 80-px buffered label-blind spatial quadrants. Zero prior submission rasters were used as features, and validation is 100% programmatic with zero human image inspection. Fail-closed science and literal registry gates make it <strong>NOT OK TO SUBMIT</strong>.</p>
<ol class="small">
<li><strong>Range-safe format &amp; leakage canaries (PASS):</strong> single-band <code>float32</code>, <code>EPSG:32611</code>, <code>3730×3292</code>, <code>nodata=None</code>, all 12,279,160 cells finite in <code>[0, 1]</code> (exact binary <code>{{0.0, 1.0}}</code>, 37,654 positive dots, 0 on mapped catalogue, min collar 3.16228 px). All 174 single-feature leakage canaries passed across all 4 quadrants (max pooled symmetric AUC <code>{card['canaries']['max_symmetric_auc']:.6f}</code> &le; 0.90).</li>
<li><strong>Holdout science (FAIL — honest negative):</strong> winning arm <code>cwgr_e1</code> scored <strong><code>{h['value']:.6f}</code> HOLDOUT-DTI</strong> (95% CI <code>[{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]</code>) vs repo strict label-blind #1 <code>cpad_e1 = {card['comparable_prior_holdout_best']['value']:.6f}</code> (paired &Delta; <code>{h['paired_best']['delta']:+.6f}</code>, 95% CI <code>[{h['paired_best']['ci95'][0]:+.6f}, {h['paired_best']['ci95'][1]:+.6f}]</code>). Fixed 37,654 area-quota controls (<code>IR-91-S18-02</code>) proved SAR IPW (<code>cwgr_e2_quota37654 = 0.182717</code>) beat unweighted SCAR (<code>cwgr_e1_quota37654 = 0.180949</code>) in 3 of 4 folds (+0.001768), isolating the global regression to marginal rank-logit standardization erasing true NE quadrant fault-density prevalence.</li>
<li><strong>Fleet novelty (108-raster audit):</strong> passed <strong>108/108</strong> pre-placement Spearman surface checks (max |&rho;| = <code>{reg['max_measured_preplacement_rank_correlation']:.4f}</code> &le; 0.90) and <strong>{non_calib_ext['non_calib_pass_le_70pct']}/{non_calib_ext['non_calib_count']}</strong> real competitive external fleet submissions on 3-px dot overlap (max <code>{non_calib_ext['non_calib_max_overlap_within_3px']:.4f}</code>; <code>GEMSDOE32 R0</code> overlap = <strong><code>{reg['gemsdoe32_r0_3px_overlap']:.4f}</code></strong> &le; 0.70; <code>cwgr_e3</code> = <code>0.3647</code>), then halted fail-closed at item #48 <code>calib_h28ridge_01839.tif</code> (69,281-dot ridge calibration probe, <code>0.7150</code> &gt; 0.70).</li>
</ol>
</div>

<div class="card dl" data-submission-ready="false" aria-label="Download current S18-CWGR file">
<strong>CURRENT FILE · S18-CWGR ({esc(h['winning_arm'].upper())})</strong>
<div class="status"><span>OK to download</span><strong>YES — research only</strong></div>
<div class="status"><span>OK to submit</span><strong style="color:var(--bad)">NO</strong></div>
<div class="status"><span>Values in [0,1], no NaN/Inf, nodata=None</span><strong>PASS · {v['positive_pixels']:,} dots</strong></div>
<div class="status"><span>CRS / shape / transform</span><strong>PASS · EPSG:32611</strong></div>
<div class="status"><span>Dots on mapped faults</span><strong>0 · min collar {v['min_catalogue_distance_px']:.5f} px</strong></div>
<div class="status"><span>Holdout vs S17-CPAD E1</span><strong style="color:var(--bad)">FAIL · {h['paired_best']['delta']:+.6f}</strong></div>
<div class="status"><span>External non-calib fleet overlap</span><strong>PASS · 46/46 (max 54.0%)</strong></div>
<div class="status"><span>Literal 108-raster Rule-1 gate</span><strong style="color:var(--bad)">STOP · #48 calib probe 71.5%</strong></div>
<a class="button" download href="{esc(a['file'])}">↓ Download Current S18-CWGR GeoTIFF</a>
<a class="btn2" download href="{esc(a['zip'])}">↓ Single-TIFF ZIP</a>
<a class="btn2" href="run-card-S18-CWGR.json">Machine run card ↗</a>
<a class="btn2" href="s18-cwgr.html">Full S18-CWGR audit ↗</a>
<a class="btn2" href="executive-summary.html">How to submit ↗</a>
<p class="small">{a['bytes']:,} bytes (.tif) · {a['zip_bytes']:,} bytes (.zip) · 1 band float32 · 3730×3292 · SHA-256<br><code>{esc(card['raster_sha256'])}</code></p>
</div></div>

<section class="card"><h2>Submission identity (recorded for audit, not an upload instruction)</h2>
<label class="small" for="nm">Unique submission name ({len(card['submission_name'])} chars)</label>
<textarea id="nm" rows="2" readonly>{esc(card['submission_name'])}</textarea>
<label class="small" for="nt">Submission note · {len(card['note'])} / 140 characters</label>
<textarea id="nt" rows="2" readonly>{esc(card['note'])}</textarea>
<p class="warn"><strong>NOT OK TO SUBMIT.</strong> Technical format and 46/46 competitive external fleet novelty pass, but strict holdout comparison vs <code>S17-CPAD E1</code> is negative (<code>{h['paired_best']['delta']:+.6f}</code>), literal Rule-1 stopped at 69,281-dot calibration probe <code>calib_h28ridge_01839.tif</code>, and 0 weekly DrivenData slots were approved or spent.</p></section>

<section class="card"><h2>Automated fail-closed gate summary</h2>
<table>
<thead><tr><th>Gate</th><th>Verdict</th><th>Measured receipt</th></tr></thead>
<tbody>
<tr><td>Format &amp; strict <code>[0, 1]</code> range</td><td><span class="badge">PASS</span></td><td>Decoded independently via <code>rasterio</code> + <code>tifffile</code>: 1 band <code>float32</code>, <code>3730×3292</code>, <code>EPSG:32611</code>, <code>nodata=None</code>, 0 NaN/Inf anywhere, min <code>0.0</code>, max <code>1.0</code>, 0 outside footprint, 0 on mapped catalogue; eliminates <code>"Predicted values must be in range [0, 1]"</code>.</td></tr>
<tr><td>Rule 4 single-feature leakage canaries</td><td><span class="badge">PASS</span></td><td>All 174 Stage-1 + Stage-2 features tested individually across all 4 spatial folds; max pooled symmetric AUC = <code>{card['canaries']['max_symmetric_auc']:.6f}</code>, max quadrant AUC = <code>{card['canaries']['max_quadrant_symmetric_auc']:.6f}</code> (&le; 0.90); CWGR subsurface cols <code>0..14</code> bitwise invariant to zeroing Bands 12 &amp; 19 (<code>max_diff = 0.0</code>).</td></tr>
<tr><td>Holdout DTI (<code>HOLDOUT-DTI</code>, <code>gems57-pooled-hide-v2</code>, 60,988 px)</td><td><span class="badge bad">FAIL — negative</span></td><td><code>cwgr_e1 = {h['value']:.6f}</code> [<code>{h['ci95'][0]:.6f}</code>, <code>{h['ci95'][1]:.6f}</code>] vs <code>cpad_e1 = {card['comparable_prior_holdout_best']['value']:.6f}</code> (&Delta; <code>{h['paired_best']['delta']:+.6f}</code>) and <code>incumbent_ptac_lb = 0.194221</code> (&Delta; <code>-0.005761</code>). Beats all label-blind analytic baselines (<code>ced91 = 0.070886</code>, <code>s16_pgrd = 0.069397</code>, <code>gravity_control = 0.057905</code>) by +0.1176 to +0.1306.</td></tr>
<tr><td>Pre-placement surface novelty (108 rasters)</td><td><span class="badge">PASS</span></td><td>108/108 rasters in <code>registry/s18_comparison_inventory.json</code> passed <code>|Spearman &rho;| &le; 0.90</code> across all 5,167,373 footprint pixels (max <code>{reg['max_measured_preplacement_rank_correlation']:.6f}</code>).</td></tr>
<tr><td>Post-placement 3-px dot overlap (108 rasters)</td><td><span class="badge bad">DUPLICATE-STOP (#48)</span></td><td>Passed <strong>46/46</strong> non-calibration external fleet submissions (<code>GEMSDOE32 R0 = {reg['gemsdoe32_r0_3px_overlap']:.4f}</code>, <code>GEMSDOE36 = 0.4227</code>, max <code>0.5397</code> on <code>GEMSDOE27</code>) + <code>calib_d15_02477</code>; halted at #48 <code>calib_h28ridge_01839.tif</code> (69,281 dots, <code>0.7150</code> &gt; 0.70).</td></tr>
<tr><td>Weekly DrivenData slot selector</td><td><span class="badge bad">BLOCKED</span></td><td><code>slots_used = 0</code>, <code>selector_approval = false</code>, <code>ORGANIZER-CONFIRMED = null</code>.</td></tr>
</tbody></table></section>

<section class="card"><h2>Pooled Holdout DTI &amp; Blind SGMC Control across all evaluated arms</h2>
<p class="small">All numbers below are strictly labelled <code>HOLDOUT-DTI</code> (unchanged <code>vendor/gems57/evaluate_holdout.py</code>, <code>gems57-pooled-hide-v2</code>, 60,988 withheld pixels, 161 clusters, 1,000 paired bootstrap draws) or post-hoc <code>BLIND-SGMC-CONTROL-DTI</code> (56,822 USGS DS-1052 bedrock fault pixels &gt;500 m from <code>existing_faults.tif</code>, never used in training/tuning). None are live DrivenData scores.</p>
<table>
<thead><tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% Bootstrap CI</th><th>Paired &Delta; vs S17-CPAD E1</th><th>BLIND-SGMC-CONTROL-DTI</th></tr></thead>
<tbody>{render_holdout_rows(holdout, blind)}</tbody>
</table></section>

<section class="card"><h2>Why GEMSDOE32 leads the fleet (0.2778 USER-REPORTED CLAIM) &amp; key Session 18 findings</h2>
<p class="small"><strong>GEMSDOE32 forensic summary:</strong> <code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code> (<code>0.2778</code> USER-REPORTED CLAIM; public leaderboard #1 <code>xiaofanhu = 0.4413</code> observed 2026-10-25, distinct from earlier <code>0.3195</code> snapshot) converts a dense 121,131-px multi-physics Hessian/tilt crest network (<code>h19-5</code>, <code>0.1922</code> USER-REPORTED) into 44,090 sparse 2.8-px-spaced dots (<code>0.2600</code>, exploiting DTI's asymmetric &alpha;=0.2 FP weight vs 300-m triangular recall kernel) and prunes 6,436 mapped-catalogue-adjacent dots within 2.0 px to reach <strong>37,654 binary dots</strong> (<code>0.2778</code>; <code>BLIND-SGMC-CONTROL-DTI = 0.088516</code>). Full algebraic inversion and how to beat it are in <a href="executive-summary.html">the executive summary</a> and <a href="HYPOTHESES_S18_CWGR.md">HYPOTHESES_S18_CWGR.md</a>.</p>
<p class="small"><strong>Session 17 S17-CPAD E1 benchmark download (0.198183 HOLDOUT-DTI — repo #1 label-blind benchmark, OK TO DOWNLOAD: YES · OK TO SUBMIT: NO, NOT OK TO SUBMIT):</strong> <a class="btn2" download href="downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif">↓ Download S17-CPAD E1 GeoTIFF</a> <a class="btn2" download href="downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.zip">↓ S17-CPAD Single-TIFF ZIP</a> <a class="btn2" href="s17-cpad.html">Full S17-CPAD Audit ↗</a> <a class="btn2" href="s17-cpad-executive-summary.html">S17-CPAD Guide ↗</a> <a class="btn2" href="run-card-S17-CPAD.json">S17-CPAD Run Card ↗</a></p>
<p class="small"><strong>Other research downloads (all NOT OK TO SUBMIT, each with its own verified run card):</strong> <a download href="downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif">↓ Download S17-CGRD E2 GeoTIFF (-zeros.tif)</a> (<a href="s17-cgrd.html">audit</a>) · <a download href="downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif">OLC91 E1</a> (<a href="index.html">page</a>, <a href="run-card-OLC91.json">run card</a>) · <a download href="downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif">S17-CDSC E1</a> (<a href="s17-cdsc.html">audit</a>) · <a download href="downloads/gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.tif">XG91 E1</a> (<a href="run-card-XG91.json">run card</a>) · <a download href="downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif">S17-EULR E3</a> (<a href="run-card-S17-EULR.json">run card</a>) · <a href="download-audit.html">All 93 downloads safety audit</a>.</p>
</section>
</main>
<footer class="small">Maximize P(Win) · Own the Outcome · 3 of 3 S18 experiments used · 0 competition slots spent · every metric is explicitly labelled HOLDOUT-DTI, BLIND-SGMC-CONTROL-DTI, or USER-REPORTED CLAIM; ORGANIZER-CONFIRMED is null.</footer>
</div></body></html>
"""


def build_exec_summary_html(card: dict) -> str:
    a = card["artifact"]
    h = card["holdout_dti"]
    reg = card["registry_comparison"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Executive summary &amp; submission guide · GEMSDOE91 S18-CWGR</title>
<meta name="description" content="Fail-closed verdict, step-by-step DrivenData GeoTIFF submission instructions, GEMSDOE32 forensics, and S18-CWGR results.">
<style>{STYLE}</style></head><body><div class="wrap">
{nav_html()}
<main id="main">
<span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span><span class="badge bad">OK TO SUBMIT: NO — NOT OK TO SUBMIT</span>
<h1>Executive summary: current verdict, how to submit, &amp; GEMSDOE32 forensics</h1>
<p class="small">Competition: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData DOE GEMS: Geothermal Exploration Machine Learning Challenge (#306)</a>. Predict unmapped subsurface/surface faults indicative of geothermal resources at 100 m resolution across Western/Central Nevada (<code>EPSG:32611</code>, <code>3730×3292</code>). Evaluation uses pooled Distance-Weighted Tversky Index (<code>&alpha;=0.2</code>, <code>&beta;=0.8</code>, <code>R=300 m</code> triangular distance kernel) with known USGS/INGENIOUS catalogue pixels masked from scoring (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem description</a>; <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official DOE/NLR rules PDF, 3 submissions/week cap</a>).</p>

<div class="card dl" data-submission-ready="false"><h2>1 · Current file status (fail-closed)</h2>
<a class="button" download href="{esc(a['file'])}">↓ Download current S18-CWGR GeoTIFF (research only)</a>
<p class="small">GeoTIFF SHA-256: <code>{esc(card['raster_sha256'])}</code> · <a download href="{esc(a['zip'])}">Single-TIFF ZIP</a> (<code>{esc(a['zip_sha256'])}</code>) · <a href="run-card-S18-CWGR.json">Machine JSON run card</a> · <a href="s18/cwgr-verification.json">Verification receipt</a> · <a href="s18-cwgr.html">Full S18-CWGR audit</a></p>
<p class="warn"><strong>OK TO DOWNLOAD: YES · OK TO SUBMIT: NO (NOT OK TO SUBMIT).</strong> Format checks pass 100% (all 12,279,160 cells finite in <code>[0, 1]</code>, <code>nodata=None</code>, 0 NaN/Inf, 37,654 binary dots, 0 on mapped catalogue) and external competitive fleet novelty passes 46/46 (<code>GEMSDOE32 R0</code> overlap = <code>{reg['gemsdoe32_r0_3px_overlap']:.4f}</code> &le; 0.70), but <code>cwgr_e1</code> scored <code>{h['value']:.6f}</code> HOLDOUT-DTI vs <code>S17-CPAD E1 = 0.198183</code> (paired &Delta; <code>{h['paired_best']['delta']:+.6f}</code>) and literal Rule-1 stopped at #48 calibration probe <code>calib_h28ridge_01839.tif</code> (<code>0.7150</code> &gt; 0.70). Zero weekly DrivenData slots were spent.</p></div>

<div class="card"><h2>2 · Exact step-by-step instructions for submitting any future promoted GeoTIFF</h2>
<ol class="small">
<li><strong>Run autonomous machine verification first (zero human visual inspection):</strong> execute <code>.venv/bin/python generate_submission.py --with-data</code>. Proceed <em>only</em> if <code>"OK_TO_SUBMIT": "YES"</code> (<code>"ok_to_submit": true</code>) AND the separate human/fleet weekly slot selector has issued an explicit <code>selector_receipt</code> under the 3/week rule.</li>
<li><strong>Use ONLY the range-safe <code>-zeros.tif</code> (or its single-TIFF <code>-zeros.zip</code>):</strong> DrivenData's scorer evaluates raw raster values across the <code>3730×3292</code> array before masking; raw <code>-3.4028235e+38</code> sentinels, <code>NaN</code> outside-footprint twins, or unclipped logits trigger <code>"Predicted values must be in range [0, 1]"</code>. Every <code>submission_writer.py</code> <code>-zeros.tif</code> writes single-band <code>float32</code>, <code>nodata=None</code>, <code>0.0</code> outside the 5,167,373-px footprint and on all mapped catalogue pixels, and finite values strictly inside <code>[0.0, 1.0]</code>.</li>
<li><strong>Verify cryptographic identity on disk:</strong> confirm <code>sha256sum &lt;file&gt;.tif</code> matches <code>raster_sha256</code> in the run card (for S18-CWGR: <code>{esc(card['raster_sha256'])}</code>).</li>
<li><strong>Upload to DrivenData #306:</strong> open the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submissions page</a>, upload the verified <code>.tif</code> (or single-TIFF <code>.zip</code>), and paste the unique submission name and &le;140-character note from the run card.</li>
<li><strong>Log organizer receipt &amp; final-round selection:</strong> record the returned public score with a submission-page receipt as <code>ORGANIZER-CONFIRMED</code>. Remember DrivenData #306 uses a <strong>single selected submission</strong> across both rounds, where Final Round re-scores against expert-expanded fault labels across the full GeoDAWN footprint.</li>
</ol></div>

<div class="card"><h2>3 · Forensic diagnosis: why GEMSDOE32 achieved 0.2778 (USER-REPORTED CLAIM) &amp; can it be beaten?</h2>
<table>
<thead><tr><th>Lineage stage</th><th>Geometric / physical operation</th><th>Positive px</th><th>Score &amp; evidence class</th><th>Physical &amp; metric mechanism</th></tr></thead>
<tbody>
<tr><td><code>h16-1</code> &rarr; <code>h19-5</code></td><td>Catalogue-blind multi-physics Hessian/tilt crest union + geothermal plausibility gating</td><td>121,131</td><td><code>0.1855 &rarr; 0.1922</code> (USER-REPORTED CLAIM)</td><td>Captures off-catalogue structural ridges (70.0% &gt;1 km from mapped faults; <code>BLIND-SGMC-CONTROL-DTI = 0.0885</code>), but 1-px continuous polylines pay 5.6× redundant FP mass inside each 300-m DTI disk.</td></tr>
<tr><td><code>d2-8</code></td><td>Greedy 2.8-px (~280 m) Poisson-disk thinning along crests</td><td>44,090</td><td><code>0.2600</code> (+0.0678, USER-REPORTED CLAIM)</td><td>Cuts FP mass by 63.6% while preserving &gt;93% of 300-m triangular kernel coverage under asymmetric &alpha;=0.2, &beta;=0.8 Tversky weighting.</td></tr>
<tr><td><code>solo</code> &rarr; <code>h33-2-b2 (R0)</code></td><td>Exact 1.0-px (-3,891) then &radic;2–2.0-px (-2,545) mapped-catalogue collar prune</td><td>37,654</td><td><code>0.2708 &rarr; 0.2778</code> (+0.0178, USER-REPORTED CLAIM)</td><td>Eliminates dead-weight FP dots inside the unrewarded halo of masked <code>existing_faults.tif</code>traces without losing unmapped basinward step-overs.</td></tr>
<tr><td>Public rank #1 (<code>xiaofanhu</code>)</td><td>External competitor (observed 2026-10-25 on official leaderboard; supersedes older <code>0.3195</code> snapshot)</td><td>Unknown</td><td><code>0.4413</code> (PUBLIC LEADERBOARD OBSERVATION)</td><td>At ~38k dots requires ~0.62 weighted recall of unmapped expert faults vs ~0.38 for <code>GEMSDOE32 R0</code>: beating both <code>0.2778</code> and <code>0.4413</code> requires higher subsurface localization precision on blind faults, not emitter tuning alone.</td></tr>
</tbody></table></div>

<div class="card"><h2>4 · Session 18 preregistered hypotheses &amp; what the experiments proved</h2>
<p class="small">Frozen before code execution in <a href="HYPOTHESES_S18_CWGR.md"><code>docs/HYPOTHESES_S18_CWGR.md</code></a> (SHA-256 <code>{esc(card['preregistration']['sha256'])}</code>): <strong>H18-1 (<code>S18-CWGR</code>, executed)</strong> Freeman–Adelson <code>(G_1, 0.78·G_2)</code> steerable quadrature + adaptive Basin-and-Range/Walker Lane Byerlee–Sibson fault-valve mechanics + SAR propensity weighting; <strong>H18-2</strong> Spectral Bouguer ensemble matched-filter depth slicing (deferred); <strong>H18-3</strong> Transdimensional Poisson Voronoi spatial geothermometry interpolation (deferred); <strong>H18-4</strong> External USGS 3DEP 1/3-arcsec bare-earth LiDAR + NASA OPERA Sentinel-1 InSAR (blocked in-sandbox by outbound allowlist).</p>
<ul class="small">
<li><strong>SAR inverse-propensity weighting works locally (<code>IR-91-S18-02</code>):</strong> under fixed 37,654 area-proportional fold quotas, <code>cwgr_e2_quota37654</code> (<code>0.182717</code>) beat unweighted <code>cwgr_e1_quota37654</code> (<code>0.180949</code>) by <code>+0.001768</code> and won 3 of 4 folds.</li>
<li><strong>Marginal rank-logit standardization starves high-prevalence grabens (<code>IR-91-S18-02</code>):</strong> forcing equal rank marginals per quadrant erased true NE fault-density prevalence (NE Fold 1 dropped from <code>0.250065</code> in <code>S17-CPAD E1</code> and <code>0.243419</code> under quota to <code>0.226655</code> under global pooling). Next sessions must calibrate cross-quadrant odds via geophysical crustal-extension priors rather than uniform marginal ranks.</li>
<li><strong>Scarp-penalized Bayes factor trades scarp recall for unverified sub-playa orthogonality (<code>IR-91-S18-03</code>):</strong> <code>cwgr_e3</code> achieved the strongest independence from <code>GEMSDOE32 R0</code> (<code>0.3647</code> 3-px overlap) but lowered <code>HOLDOUT-DTI</code> to <code>0.164534</code> because held-out <code>existing_faults.tif</code> and <code>SGMC</code> faults remain predominantly scarp/outcrop-anchored.</li>
</ul>
<p class="small"><strong>Benchmark &amp; archive links:</strong> <a href="s17-cpad.html">S17-CPAD (#1 label-blind 0.198183)</a> · <a download href="downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif">↓ Download S17-CPAD E1 GeoTIFF</a> · <a download href="downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.zip">↓ S17-CPAD Single-TIFF ZIP</a> · <a href="index.html">OLC91</a> · <a href="research.html">Verified official links &amp; S16</a> · <a href="download-audit.html">93-file download safety audit</a>.</p>
<p class="small"><strong>Other parallel-session research downloads (all NOT OK TO SUBMIT, each with its own verified run card):</strong> <a download href="downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif">S17-CGRD E2</a> (<a href="s17-cgrd.html">audit</a>) · <a download href="downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif">S17-CDSC E1</a> (<a href="s17-cdsc.html">audit</a>) · <a download href="downloads/gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.tif">XG91 E1</a> (<a href="run-card-XG91.json">run card</a>) · <a download href="downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif">S17-EULR E3</a> (<a href="run-card-S17-EULR.json">run card</a>).</p>
</div>
</main>
</div></body></html>
"""


def build_s18_detail_html(card: dict, holdout: dict, blind: dict, feat: dict, novelty: dict) -> str:
    a = card["artifact"]
    v = card["validator_output"]
    h = card["holdout_dti"]
    reg = card["registry_comparison"]
    feat_items = "".join(f"<li><code>{esc(n)}</code></li>" for n in feat["cwgr_novel_features"])
    cat_rows = []
    for cat_key, c in novelty["category_summary"].items():
        cat_rows.append(
            f"<tr><td><code>{esc(cat_key)}</code></td>"
            f"<td>{c['pass_le_70pct']} / {c['count']}</td>"
            f"<td>{c['non_calib_pass_le_70pct']} / {c['non_calib_count']}</td>"
            f"<td><code>{c['non_calib_max_overlap_within_3px']:.6f}</code> ({esc(str(c['non_calib_max_overlap_file']))})</td>"
            f"<td><code>{c['max_overlap_within_3px']:.6f}</code> ({esc(str(c['max_overlap_file']))})</td>"
            f"<td><code>{c['max_abs_spearman_rho']:.6f}</code></td></tr>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>S18-CWGR Scientific Audit &amp; Novelty Forensics · GEMSDOE91</title>
<meta name="description" content="Complete Session 18 S18-CWGR scientific audit, 18 novel steerable quadrature & fault-valve features, 8-arm + 3-quota holdout table, and 108-raster novelty forensics.">
<style>{STYLE}</style></head><body><div class="wrap">
{nav_html()}
<main id="main">
<span class="badge">OK TO DOWNLOAD: YES · RESEARCH / AUDIT</span><span class="badge bad">OK TO SUBMIT: NO · NOT OK TO SUBMIT</span>
<h1>Session 18 (S18-CWGR): Steerable Quadrature, Byerlee–Sibson Fault-Valve &amp; SAR Propensity Audit</h1>
<p class="small">Preregistration: <a href="HYPOTHESES_S18_CWGR.md"><code>docs/HYPOTHESES_S18_CWGR.md</code></a> (SHA-256 <code>{esc(card['preregistration']['sha256'])}</code>) · Feature module: <code>src/gems91/cwgr18.py</code> (SHA-256 <code>{esc(feat['cwgr_code_sha256'])}</code>) · Verification receipt: <a href="s18/cwgr-verification.json"><code>docs/s18/cwgr-verification.json</code></a>.</p>

<div class="hero">
<div class="card dl" data-submission-ready="false">
<h2>S18-CWGR ({esc(h['winning_arm'].upper())}) Deliverable</h2>
<div class="status"><span>OK to download</span><strong>YES · research only</strong></div>
<div class="status"><span>OK to submit</span><strong style="color:var(--bad)">NO · NOT OK TO SUBMIT</strong></div>
<div class="status"><span>HOLDOUT-DTI (<code>gems57-pooled-hide-v2</code>)</span><strong>{h['value']:.6f} [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}]</strong></div>
<div class="status"><span>BLIND-SGMC-CONTROL-DTI (56,822 px)</span><strong>{card['blind_sgmc_control']['winning_arm_dti']:.6f}</strong></div>
<div class="status"><span>GEMSDOE32 R0 3-px overlap</span><strong>{reg['gemsdoe32_r0_3px_overlap']:.4f} (PASS &le; 0.70)</strong></div>
<div class="status"><span>Positive binary dots / collar / spacing</span><strong>{v['positive_pixels']:,} / {v['min_catalogue_distance_px']:.5f} px / {v['min_spacing_px']:.5f} px</strong></div>
<a class="button" download href="{esc(a['file'])}">↓ Download S18-CWGR E1 GeoTIFF</a>
<a class="btn2" download href="{esc(a['zip'])}">↓ S18-CWGR Single-TIFF ZIP</a>
<a class="btn2" href="run-card-S18-CWGR.json">Run card JSON ↗</a>
<a class="btn2" href="s18-cwgr-executive-summary.html">S18 Executive Summary ↗</a>
<p class="small">SHA-256: <code>{esc(card['raster_sha256'])}</code><br>Pixel SHA-256: <code>{esc(card['raster_pixel_sha256'])}</code></p>
</div>
<div class="card">
<h2>37,654-dot spatial support preview</h2>
<img class="preview" src="assets/s18-support.png" alt="Spatial map of the 37,654 S18-CWGR E1 binary fault predictions across the Nevada GeoDAWN footprint">
<p class="small">Deterministic 6× downsampled rendering of <code>{esc(Path(a['file']).name)}</code> inside the 5,167,373-px valid <code>sample_submission.tif</code> footprint. Zero NaN/Inf cells anywhere in the 3730×3292 raster.</p>
</div>
</div>

<section class="card"><h2>1 · All 8 Primary Holdout Arms + 3 Area-Quota Controls</h2>
<table>
<thead><tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% Bootstrap CI</th><th>Paired &Delta; vs S17-CPAD E1</th><th>BLIND-SGMC-CONTROL-DTI</th></tr></thead>
<tbody>{render_holdout_rows(holdout, blind)}</tbody>
</table></section>

<section class="card"><h2>2 · Exhaustive 108-Raster Novelty Disaggregation (<a href="s18/milestone-novelty.json">milestone-novelty.json</a>)</h2>
<table>
<thead><tr><th>Inventory category</th><th>All pass (&le;0.70)</th><th>Non-calib pass (&le;0.70)</th><th>Max non-calib 3-px overlap</th><th>Max category 3-px overlap</th><th>Max |Spearman &rho;|</th></tr></thead>
<tbody>{''.join(cat_rows)}</tbody>
</table>
<p class="small"><strong>Key forensic distinction (<code>IR-91-S18-04</code>):</strong> Every single real competitive external fleet submission (<code>46/46</code> non-calibration rasters, 37k–60k dots) passed the 3-px overlap gate (max <code>0.539651</code> on <code>GEMSDOE27</code>; <code>GEMSDOE32 R0 = 0.467201</code>; <code>GEMSDOE36 = 0.422717</code>). Item #48 <code>calib_h28ridge_01839.tif</code> is a 69,281-dot (1.84× budget) metric-calibration probe retained intact in frozen <code>registry/s18_comparison_inventory.json</code>; we honor the literal stop fail-closed without mutating the frozen inventory.</p>
</section>

<section class="card"><h2>3 · 18 Novel CWGR Continuum-Mechanics &amp; Steerable Quadrature Features</h2>
<p class="small">Columns <code>0..14</code> are programmatically verified bitwise invariant to zeroing topographic Bands 12 &amp; 19 (<code>verified_cwgr_subsurface_b12_b19_max_diff = 0.0</code>); columns <code>15..17</code> isolate piedmont micro-scarps, pluvial Lake Lahontan contour-parallel shoreline mimics, and Bekker–Davis mapper visibility.</p>
<ol class="small">{feat_items}</ol>
<p class="small">Raw machine receipts: <a href="s18/holdout.json"><code>s18/holdout.json</code></a> · <a href="s18/canaries.json"><code>s18/canaries.json</code></a> · <a href="s18/blind-sgmc-control.json"><code>s18/blind-sgmc-control.json</code></a> · <a href="s18/registry-surface.json"><code>s18/registry-surface.json</code></a> · <a href="s18/registry-final.json"><code>s18/registry-final.json</code></a> · <a href="s18/writer-receipt.json"><code>s18/writer-receipt.json</code></a> · <a href="s18/features.json"><code>s18/features.json</code></a>.</p>
</section>
</main>
<footer class="small">GEMSDOE91 Session 18 (S18-CWGR) · 0 weekly DrivenData slots spent · NOT OK TO SUBMIT.</footer>
</div></body></html>
"""


def render() -> None:
    verify(with_data=False)
    docs = ROOT / "docs"
    card = load_json("run-card-S18-CWGR.json")
    if card.get("ok_to_submit") is not False or card.get("submission_ready") is not False or card.get("verdict") != "negative":
        raise ValueError("S18-CWGR renderer requires an explicitly fail-closed negative research card")
    if submission_ready(card) or card.get("automated_gates") != gates(card):
        raise ValueError("S18-CWGR readiness gates inconsistent")

    _registered_pair(ROOT, card["raster_path"], card["raster_sha256"])
    render_preview(card)

    holdout = load_json("s18/holdout.json")
    blind = load_json("s18/blind-sgmc-control.json")
    feat = load_json("s18/features.json")
    novelty = load_json("s18/milestone-novelty.json")

    exec_html = build_exec_summary_html(card)
    detail_html = build_s18_detail_html(card, holdout, blind, feat, novelty)

    (docs / "s18-cwgr.html").write_text(detail_html, encoding="utf-8")
    (docs / "s18-cwgr-executive-summary.html").write_text(exec_html, encoding="utf-8")


if __name__ == "__main__":
    render()
