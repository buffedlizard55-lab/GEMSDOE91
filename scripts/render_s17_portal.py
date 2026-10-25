#!/usr/bin/env python3
"""Render evidence-derived Session 17 (S17-CPAD) research portal pages and support PNG.

Verifies the S17-CPAD GeoTIFF, single-member ZIP, 7-arm holdout summary, 148-feature
canaries, 95-raster registry audit, and fail-closed readiness gates via
`scripts.verify_s17.verify()` before writing HTML. Never overrides `ok_to_submit`.
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
from scripts.verify_s17 import sha, verify


def load_json(rel_docs: str):
    return json.loads((ROOT / "docs" / rel_docs).read_text())


def render_preview(card: dict) -> None:
    """Deterministic PNG of actual S17-CPAD 37,654-dot support within sample_submission footprint."""
    import numpy as np
    import rasterio

    dest = ROOT / "docs/assets/s17-support.png"
    sample = ROOT / "data/official/sample_submission.tif"
    if not sample.exists():
        if not dest.exists():
            raise FileNotFoundError("Restore pinned sample_submission.tif to build initial s17-support.png")
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
    image[:] = [232, 238, 232]
    image[f] = [194, 210, 194]
    image[d] = [18, 78, 58]

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


def page_shell(title: str, content: str, card: dict) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · GEMSDOE91</title>
<meta name="description" content="S17-CPAD freshly computed single-band [0, 1] GeoTIFF with automated validation and fail-closed submission gates.">
<link rel="stylesheet" href="assets/portal.css"><link rel="stylesheet" href="assets/s16.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="s16-top"><a class="s16-logo" href="index.html"><span class="s16-monogram" aria-hidden="true">91</span><span>GEMSDOE<small>FAULT DISCOVERY LAB</small></span></a>
<nav aria-label="Main"><a href="index.html">Home &amp; verdicts</a><a href="s17-cpad.html"><strong>S17-CPAD · holdout audit</strong></a><a href="s17-cpad-executive-summary.html">S17 submission guide</a><a href="s15-scgf.html">S15-SCGF</a><a href="executive-summary.html">General guide</a><a href="research.html">S16 &amp; sources</a><a href="archive-results.html">Archive</a></nav></header>
<main id="main">{content}</main>
<footer class="s16-foot"><div>Maximize P(Win). Own the outcome.<br>3 preregistered S17 arms · 0 competition slots spent · 100% automated byte verification.</div>
<div><a href="run-card-S17-CPAD.json">S17 JSON run card</a> · <a href="s17/verification.json">Machine audit</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">GitHub repo</a><br>Completed {esc(card['completed_utc'][:19].replace('T', ' '))} UTC.</div></footer></div></body></html>
"""


def hero_download_card(card: dict) -> str:
    a = card["artifact"]
    v = card["validator_output"]
    return f"""<div class="s16-card s16-download" data-submission-ready="false">
<span class="eyebrow">FRESH COMPUTATION · S17-CPAD ({esc(card['holdout_dti']['winning_arm'].upper())})</span>
<h2>Cooper–Cowan Phase, Saddles &amp; Geotherm Diseq</h2>
<p class="small">Freshly computed single-band [0, 1] GeoTIFF on canonical label-blind spatial quadrants. Zero prior submission pixels used as inputs.</p>
<div class="s16-status"><span>OK to download</span><strong>YES · research / audit</strong></div>
<div class="s16-status"><span>OK to submit</span><strong class="warn">NO · fail-closed gates</strong></div>
<div class="s16-status"><span>Finite values in [0, 1]</span><strong>PASS · 0 NaN/Inf ({v['positive_pixels']:,} dots)</strong></div>
<div class="s16-status"><span>CRS / shape / transform / nodata=None</span><strong>PASS · EPSG:32611</strong></div>
<a class="button" download href="{esc(a['file'])}">↓ Download S17-CPAD E1 GeoTIFF</a>
<div class="s16-buttons"><a download href="{esc(a['zip'])}">↓ S17-CPAD Single-TIFF ZIP</a><a href="s17/verification.json">Automated verification ↗</a><a href="run-card-S17-CPAD.json">Run card JSON ↗</a></div>
<p class="small">{a['bytes']:,} bytes (.tif) · {a['zip_bytes']:,} bytes (.zip) · float32 · 3730×3292<br>Format validity does NOT authorize spending a weekly DrivenData submission slot.</p></div>"""


def identity_fields_card(card: dict) -> str:
    return f"""<div class="s16-card"><h3>Unique artifact identity &amp; copyable note</h3>
<label for="s17-candidate-name" class="small">Unique submission identifier ({len(card['submission_name'])} chars)</label>
<div class="copyrow"><textarea id="s17-candidate-name" rows="2" readonly>{esc(card['submission_name'])}</textarea><button type="button" data-copy="s17-candidate-name" aria-label="Copy S17 submission name">Copy</button></div>
<label for="s17-candidate-note" class="small">Submission note · {len(card['note'])} / 140 characters</label>
<div class="copyrow"><textarea id="s17-candidate-note" rows="3" readonly>{esc(card['note'])}</textarea><button type="button" data-copy="s17-candidate-note" aria-label="Copy S17 submission note">Copy</button></div>
<p id="copy-status" class="copy-status" role="status" aria-live="polite"></p>
<dl class="meta">
<dt>GeoTIFF SHA-256</dt><dd class="mono">{esc(card['raster_sha256'])}</dd>
<dt>ZIP SHA-256</dt><dd class="mono">{esc(card['artifact']['zip_sha256'])}</dd>
<dt>Pixel SHA-256</dt><dd class="mono">{esc(card['raster_pixel_sha256'])}</dd>
<dt>Grid &amp; CRS</dt><dd>3730 × 3292 · 100 m · EPSG:32611 · nodata=None</dd>
<dt>Affine transform</dt><dd class="mono">(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)</dd>
<dt>Organizer receipt</dt><dd>None (ORGANIZER-CONFIRMED: null · 0 slots used)</dd>
</dl></div>"""


def gate_table(card: dict) -> str:
    reg = card["registry_comparison"]
    pb = card["holdout_dti"]["paired_best"]
    explanations = {
        "format": (
            "100% automated GeoTIFF & ZIP check",
            "Reopened by both rasterio and tifffile: 1 band, float32, EPSG:32611, 3730×3292, exact affine transform, nodata=None, 0 NaN/Inf across all 12,279,160 cells, values strictly in {0.0, 1.0} ⊂ [0, 1], 0 on mapped faults, min spacing 3.16228 px > 3.0 px.",
        ),
        "canary": (
            "Rule 4 single-feature leakage canaries",
            f"All {card['canaries']['features_tested']} features (128 static + 20 OOF auto-context) tested individually on 60,988 withheld positives across 4 quadrants: max pooled symmetric AUC {card['canaries']['max_symmetric_auc']:.6f} <= 0.90 (max quadrant {card['canaries']['max_quadrant_symmetric_auc']:.6f}).",
        ),
        "novelty": (
            "Rule 1 pre-placement & final 3-px registry overlap",
            f"Pre-placement Spearman PASS across all 95/95 rasters (max |rho| = {reg['max_measured_surface_rank_correlation']:.4f} <= 0.90). Final 3-px dot overlap PASS across rows 1..50 (max {reg['max_passed_before_stop_3px_overlap']:.4f} <= 0.70; GEMSDOE32 R0 = 0.4927), then stopped fail-closed at 51/95 r11_greedy_mp.tif (272,853 dots, 0.8725 > 0.70); diagnostic post-stop overlap with in-repo S14-PTAC E2 is 0.8296.",
        ),
        "assigned_lane": (
            "Explicit human lane assignment",
            "Session 17 executed one preregistered provisional lane (S17-CPAD) because the standing prompt leaves the lane paragraph blank (`[PASTE ONE METHOD]`). Provisional lanes remain fail-closed until explicitly assigned.",
        ),
        "beats_comparable_best": (
            "Paired holdout improvement (95% CI > 0)",
            f"Point estimate 0.198183 HOLDOUT-DTI beats all comparable label-blind baselines on gems57-pooled-hide-v2 (INCUMBENT-PTAC-LB 0.194221, S16-PGRD 0.069397, CED91 0.070886), but paired 20-km block-bootstrap 95% CI vs INCUMBENT-PTAC-LB is [{pb['ci95'][0]:+.6f}, {pb['ci95'][1]:+.6f}] (lower bound slightly < 0).",
        ),
        "separate_selector": (
            "Separate human weekly-slot selector",
            "Per Protocol Rule 6, research runs never spend live weekly slots (`slots_used = 0`). Promotion requires an external selector receipt verifying live weekly allowance and organizer eligibility.",
        ),
    }
    rows = ""
    for key, passed in gates(card).items():
        title, desc = explanations[key]
        rows += (
            f'<tr><td><strong>{esc(title)}</strong></td>'
            f'<td><span class="badge {"" if passed else "bad"}">{"PASS" if passed else "BLOCKED"}</span></td>'
            f"<td>{esc(desc)}</td></tr>"
        )
    return (
        '<div class="table-scroll"><table><thead><tr><th>Automated gate</th><th>Status</th>'
        f"<th>Measured evidence &amp; boundary</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def render() -> None:
    card = load_json("run-card-S17-CPAD.json")
    verify()
    if submission_ready(card) or card["ok_to_submit"]:
        raise ValueError("S17-CPAD must remain fail-closed (ok_to_submit=False)")
    render_preview(card)

    holdout = load_json("s17/holdout.json")
    sgmc = load_json("s17/blind-sgmc-control.json")
    milestones = load_json("s17/milestone-novelty.json")["milestones"]
    sources = load_json("s17/sources.json")["sources"]
    fleet = load_json("fleet-audit.json")

    h = card["holdout_dti"]
    scores = holdout["summary_all_arms"]["scores"]
    arm_labels = [
        ("cpad_e1", "S17-CPAD E1 (Winning arm: Full Stage-2 over X_full + ac_full + ac_sub, 37,654 NMS dots)"),
        ("incumbent_ptac_lb", "INCUMBENT-PTAC-LB (S14-PTAC E2 re-evaluated strictly label-blind without IR-91-S17-01 moat)"),
        ("cpad_e2", "S17-CPAD E2 (Exogenous [0.28, 0.68] cover-gated blend + 37,654 NMS dots)"),
        ("cpad_e3", "S17-CPAD E3 (Cover-gated blend + 300 m kernel submodular greedy placement)"),
        ("ced91", "CED91 (Potential-field tilt-crest baseline at matched 37,654 global blind budget)"),
        ("s16_pgrd", "S16-PGRD (Session 16 magnetic-gravity pseudogravity residual edges, 37,654 dots)"),
        ("gravity_control", "Matched Gravity-Theta Phase Control (Cooper-Cowan gravity theta only, 37,654 dots)"),
    ]
    arm_rows = ""
    for key, label in arm_labels:
        sc = scores[key]
        arm_rows += (
            f"<tr><td><strong>{esc(label)}</strong></td>"
            f"<td>{sc['dti']:.6f} HOLDOUT-DTI</td>"
            f"<td>[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}]</td>"
            f"<td>{sc['tpw']:,.1f} / {sc['fpw']:,.1f} / {sc['fnw']:,.1f}</td></tr>"
        )

    ms_rows = ""
    for m in milestones:
        ov = m["final_3px_dot_overlap"]
        diag_ov = m.get("diagnostic_post_stop_3px_overlap")
        if ov is not None:
            ov_txt = f"{100.0 * ov:.2f}% (measured before stop)"
        elif diag_ov is not None:
            ov_txt = f"{100.0 * diag_ov:.2f}% (diagnostic post-stop)"
        else:
            ov_txt = "Not checked after stop"
        ms_rows += (
            f"<tr><td><strong>{esc(m['label'])}</strong><br><span class='small mono'>{esc(m['file'])}</span></td>"
            f"<td>{m['preplacement_spearman_rho']:+.4f} (PASS)</td>"
            f"<td>{esc(ov_txt)}</td></tr>"
        )

    src_rows = ""
    for s in sources:
        src_rows += (
            f"<tr><td>{esc(s['claim'])}</td>"
            f"<td><code>{esc(s['classification'])}</code></td>"
            f"<td><a href=\"{esc(s['url'])}\">Official / source link ↗</a><br><span class=\"small\">{esc(s['verification'])}</span></td></tr>"
        )

    audit_body = f"""
<section class="s16-hero">
<div>
<span class="eyebrow">SESSION 17 · S17-CPAD · HIGHEST LABEL-BLIND HOLDOUT-DTI IN GEMSDOE91</span>
<h1>0.198183 HOLDOUT-DTI.<br>Honest fail-closed gates.</h1>
<p class="lead">S17-CPAD tests Cooper–Cowan sun-angle potential-field phase concordance, basement/gravity accommodation-zone Gaussian-curvature saddles (<code>det(H)&lt;0</code>), and GDR #1562 chemical-vs-measured geothermometer disequilibrium conduits inside a provably <code>Band 12</code>/<code>Band 19</code>-invariant Dual-Specialist architecture.</p>
<div class="s16-badges"><span class="badge">OK TO DOWNLOAD: YES (RESEARCH)</span><span class="badge bad">OK TO SUBMIT: NO</span></div>
<p class="s16-subtitle">100% automated GeoTIFF &amp; ZIP byte verification · 0 NaN/Inf · [0, 1] certified · 3 / 3 experiments · 0 slots spent.</p>
</div>
{hero_download_card(card)}
</section>

<div class="s16-note"><strong>NOT OK TO SUBMIT</strong> — While <code>cpad_e1</code> achieves the highest strict label-blind <code>gems57-pooled-hide-v2</code> score measured in this repository (<strong>0.198183 HOLDOUT-DTI</strong> vs <code>INCUMBENT-PTAC-LB</code> 0.194221 and <code>S16-PGRD</code> 0.069397) and passes 95/95 pre-placement Spearman checks plus the first 50/50 fleet rasters (<code>GEMSDOE32 R0 = 49.27%</code>), it stops fail-closed at reference 51/95 <code>r11_greedy_mp.tif</code> (272,853 dots, 87.25% &gt; 70%), shares 82.96% 3-px dot overlap with in-repo <code>S14-PTAC E2</code>, and its paired 95% CI vs <code>INCUMBENT-PTAC-LB</code> (<code>[-0.001766, +0.010077]</code>) straddles zero.</div>

<section class="s16-grid" aria-label="S17-CPAD key metrics">
<div class="s16-card"><span class="s16-mini">HOLDOUT-DTI · GEMS57-POOLED-HIDE-V2</span><div class="s16-metric">{h['value']:.6f}</div><p class="small">95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] · 60,988 withheld positives · +0.128786 over S16-PGRD · +0.003962 over INCUMBENT-PTAC-LB.</p></div>
<div class="s16-card"><span class="s16-mini">BLIND-SGMC-CONTROL-DTI (AUXILIARY)</span><div class="s16-metric">{card['blind_sgmc_control']['scores']['cpad_e1']:.6f}</div><p class="small">56,822 off-catalogue USGS DS-1052 SGMC pixels (&gt;500 m from catalogue) · +78.1% over S16-PGRD (0.038501).</p></div>
<div class="s16-card"><span class="s16-mini">PROTOCOL BUDGET &amp; CANARIES</span><div class="s16-metric">3 / 3 <small style="font-size:16px">arms</small></div><p class="small">148 / 148 single-feature canaries PASS (max AUC 0.6779 &le; 0.90) · 0 live slots used.</p></div>
</section>

<section class="s16-section"><div class="section-head"><h2>Automated submission-readiness gates</h2><a href="s17/verification.json">Machine verification JSON ↗</a></div>{gate_table(card)}</section>

<section class="s16-section s16-split">
<div>
<span class="eyebrow">PREREGISTERED HYPOTHESES (H17-1 .. H17-5)</span>
<h2>Why blind accommodation zones &amp; hydrothermal conduits vanish from surface maps.</h2>
<p>Before writing feature code, <a href="HYPOTHESES_S17_CPAD.md"><code>docs/HYPOTHESES_S17_CPAD.md</code></a> preregistered five ranked geological hypotheses and implemented the top three orthogonal subsurface mechanisms inside a 16-feature stack (<code>src/gems91/cpad17.py</code>):</p>
<ul>
<li><strong>H17-1 · Cooper–Cowan Potential-Field Phase Concordance &amp; Poisson Demagnetization Deficit:</strong> Amplitude-normalized upward-continued sun-angle phase concordance between isostatic gravity and RTP magnetics, plus gravity-crest survival where hydrothermal magnetite->pyrite/clay alteration destroys RTP susceptibility. <em>Mimic:</em> unaltered non-magnetic pluton margin.</li>
<li><strong>H17-2 · Accommodation-Zone Saddle Curvature &amp; Synthetic Riedel Mesh:</strong> Hyperbolic Hessian saddles (<code>det(H)&lt;0</code>) of Band-15 depth-to-basement and Band-13 gravity, paired with synthetic Riedel shear orientation alignment (~15° to geodetic principal shear). <em>Mimic:</em> paleovalley thalweg constriction.</li>
<li><strong>H17-3 · Geothermometer Disequilibrium Upflow Conduits (GDR #1562):</strong> Positive disequilibrium excess (<code>max(T_Na-K-Ca, T_Quartz, T_Chalcedony) - T_measured</code>) from deep rapid fault-conduit ascent, strictly excluding <code>dist_known_fault_px</code> and suppressed over flat conductive playa clay-caps. <em>Mimic:</em> lateral outflow plume in alluvial fan gravels.</li>
</ul>
<p class="small">Bitwise audit: perturbing <code>Band 12</code> (detrended elevation) +1,000 m and <code>Band 19</code> (elevation slope) ×50 produces <strong>0.0000000 max absolute difference</strong> across all 14 subsurface CPAD columns.</p>
</div>
<figure class="s16-figure"><img src="assets/s17-support.png" width="549" height="622" alt="Actual S17-CPAD E1 37,654-dot binary prediction support within the DOE GEMS footprint"><figcaption>Actual <code>cpad_e1</code> 37,654-dot support (<code>min_spacing = 3.162 px</code>, <code>collar &gt; 3.05 px</code>). Block-aggregated 6× for legibility; no ground-truth labels shown.</figcaption></figure>
</section>

<section class="s16-section">
<div class="section-head"><h2>Strict label-blind holdout benchmark (<code>gems57-pooled-hide-v2</code>)</h2><a href="s17/holdout.json">Full fold &amp; bootstrap JSON ↗</a></div>
<p>During Session 17 forensics (<a href="https://github.com/buffedlizard55-lab/GEMSDOE91/blob/main/IRREGULARITIES.md"><code>IR-91-S17-01..03</code></a>), we discovered that legacy Sessions 13–15 inflated their holdout scores (~0.2406–0.2678) by passing <code>~fold.buffer_mask</code> into test-time dot placement (an 8-km oracle moat around withheld truth!). Re-evaluating <code>S14-PTAC E2</code> honestly on canonical label-blind <code>spatial.folds</code> establishes the true incumbent bar: <strong>0.194221 HOLDOUT-DTI</strong>. All seven arms below were scored on the identical unchanged <code>vendor/gems57/evaluate_holdout.py</code> evaluator (60,988 withheld positives, 80-px buffer, 1,000 × 20-km paired block-bootstrap draws):</p>
<div class="table-scroll"><table><thead><tr><th>Evaluated arm</th><th>Measured score</th><th>95% block-bootstrap CI</th><th>Pooled TPw / FPw / FNw</th></tr></thead><tbody>{arm_rows}</tbody></table></div>
</section>

<section class="s16-section" id="forensics">
<h2>PhD forensic synthesis: GEMSDOE32 (0.2778 claim) &amp; 92-repo fleet audit</h2>
<p><strong>1. Status of external scores (`0.2778`, `0.4413`, `0.3195`):</strong> Live GitHub snapshot inspection across all {len(fleet['rows'])} fleet repositories (refreshed {esc(fleet['checked_utc'][:19].replace('T', ' '))} UTC; <code>0</code> organizer-confirmed receipts) and commit <code>012e17b2a1</code> of <code>GEMSDOE32</code> confirms that <code>gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif</code> is explicitly labelled <code>UNSCORED</code> on its own portal (“<em>NO ORGANISER SCORE EXISTS for this or any artifact in this repository</em>”). Accordingly, <code>0.2778</code>, <code>0.4413</code>, and <code>0.3195</code> are strictly classified as unverified <code>CLAIM</code>s, never <code>ORGANIZER-CONFIRMED</code>.</p>
<p><strong>2. Exact mathematical mechanism of GEMSDOE32 R0:</strong> Byte-level comparison proves <code>GEMSDOE32 R0</code> (37,654 binary dots) is strictly its 40,199-dot parent minus the 2,545 dots at Euclidean distance &le;2 px (200 m) from mapped catalogue faults. Under asymmetric Tversky DTI (<code>alpha=0.2</code> FP weight, <code>beta=0.8</code> FN weight, 300 m triangular kernel), mapped catalogue pixels are masked to zero in both truth and prediction; dots placed within 0–300 m of a mapped fault pay full <code>0.2</code> unmatched FP penalty on their catalogue-facing half-kernel while harvesting credit only if an unmapped splay branches immediately off the trace. Enforcing a <code>&gt;3.05 px</code> (&gt;305 m) label-blind collar plus <code>&gt;3.05 px</code> inter-dot spacing eliminates kernel self-cannibalization without peeking at hidden truth.</p>
<p><strong>3. Registry novelty &amp; milestone comparisons:</strong> Across the 95-raster comparison inventory (<a href="s17/registry-surface.json"><code>s17/registry-surface.json</code></a>, <a href="s17/registry-final.json"><code>s17/registry-final.json</code></a>):</p>
<div class="table-scroll"><table><thead><tr><th>Reference milestone</th><th>Pre-placement Spearman &rho;</th><th>Final 3-px dot overlap</th></tr></thead><tbody>{ms_rows}</tbody></table></div>
</section>

<section class="s16-section s16-split">{identity_fields_card(card)}
<div class="s16-card">
<span class="s16-live">Verified Official Sources</span>
<h3>Audit &amp; provenance artifacts</h3>
<p>Every scientific claim, external public dataset, and gate decision in Session 17 is backed by SHA-256-pinned files and machine-checkable JSON receipts:</p>
<ul>
<li><a href="HYPOTHESES_S17_CPAD.md">Preregistered hypotheses (<code>HYPOTHESES_S17_CPAD.md</code>)</a></li>
<li><a href="run-card-S17-CPAD.json">Complete S17 JSON run card</a></li>
<li><a href="s17/canaries.json">148-feature leakage canary report</a></li>
<li><a href="s17/blind-sgmc-control.json">Blind USGS SGMC auxiliary DTI report</a></li>
<li><a href="s17/provenance.json">Code &amp; package SHA-256 provenance</a></li>
<li><a href="s17-cpad-executive-summary.html">Exact DrivenData submission guide →</a></li>
</ul>
</div></section>

<section class="s16-section" id="sources">
<h2>Auditable external &amp; official source register</h2>
<div class="table-scroll"><table><thead><tr><th>Claim &amp; scope</th><th>Classification</th><th>Link &amp; verification boundary</th></tr></thead><tbody>{src_rows}</tbody></table></div>
</section>
"""

    guide_body = f"""
<section class="s16-hero">
<div>
<span class="eyebrow">S17-CPAD EXECUTIVE SUMMARY &amp; SUBMISSION GUIDE</span>
<h1>OK to download: YES.<br>OK to submit: NO.</h1>
<p class="lead"><code>gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif</code> is 100% competition-format valid (single-band float32, EPSG:32611, 3730×3292, nodata=None, 0 NaN/Inf, values strictly in {{0.0, 1.0}} &sub; [0, 1]), verified automatically without human visual inspection—and <strong>blocked from live DrivenData upload</strong> by fail-closed novelty, paired-CI, lane, and selector gates.</p>
<div class="s16-badges"><span class="badge">OK TO DOWNLOAD: YES (RESEARCH)</span><span class="badge bad">OK TO SUBMIT: NO</span></div>
</div>
{hero_download_card(card)}
</section>

<div class="s16-note"><strong>NOT OK TO SUBMIT</strong> — Do not spend a weekly DrivenData submission slot on this file. Download it freely for GIS/scientific inspection, reproducibility checks, or ensemble diagnostics. Zero competition slots have been used (<code>slots_used = 0</code>).</div>

<section class="s16-section">
<h2>Exact step-by-step DrivenData submission procedure (only when a future candidate clears all 6 gates)</h2>
<div class="s16-step"><h3>Step 1 · Verify all six automated gates in code (no visual eyeballing)</h3>
<p>Run <code>.venv/bin/python scripts/verify_s17.py --with-data</code>. Confirm both <code>"status": "PASS"</code> (file format, finite <code>[0, 1]</code> values, exact EPSG:32611 grid, single-TIFF ZIP byte identity, 148 canaries &le;0.90) <strong>and</strong> check <code>"ok_to_submit"</code>. For S17-CPAD, <code>"ok_to_submit"</code> is <code>false</code>, so stop here and do not upload.</p></div>
<div class="s16-step"><h3>Step 2 · Why DrivenData's <code>"Predicted values must be in range [0, 1]"</code> error cannot occur on certified <code>-zeros.tif</code> files</h3>
<p>Legacy NaN-masked rasters or rasters carrying sentinel <code>nodata = -9999</code> fail strict array parsers. Our shared writer emits <code>nodata = None</code>, zeros every outside-footprint and catalogue-fault pixel, clips/checks all 12,279,160 <code>float32</code> cells into <code>[0.0, 1.0]</code> with <code>0</code> NaN/Inf, and verifies exact byte equality with both <code>rasterio</code> and <code>tifffile</code> plus unpacked <code>.zip</code> comparison.</p></div>
<div class="s16-step"><h3>Step 3 · Separate human selector check against the weekly cap</h3>
<p>Before any live upload of a future <code>ok_to_submit: true</code> candidate, a human selector must log into <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → DOE GEMS → Submissions</a>, confirm remaining weekly submission allowance (3/week cap), verify external data eligibility under official competition rules, and confirm the candidate beat the current holdout best with a strictly positive paired 95% confidence interval.</p></div>
<div class="s16-step"><h3>Step 4 · Upload exact <code>-zeros.tif</code> (or single-member <code>-zeros.zip</code>) &amp; paste &le;140-char note</h3>
<p>On the DrivenData submission form, upload either the standalone <code>-zeros.tif</code> or its single-member <code>-zeros.zip</code> (never upload JSON run cards or multi-file archives) and paste the recorded &le;140-character submission note.</p></div>
<div class="s16-step"><h3>Step 5 · Record the organizer receipt</h3>
<p>Only after DrivenData returns a scored submission receipt may a number be recorded in <code>ledger/submissions.csv</code> as <code>ORGANIZER-CONFIRMED</code> alongside its timestamp, submission ID, and exact SHA-256.</p></div>
</section>

<section class="s16-section s16-split">{identity_fields_card(card)}
<div class="s16-card"><h3>Quick verification commands</h3>
<pre class="mono" style="white-space:pre-wrap;font-size:12px;background:#f4f7f4;padding:14px;border-radius:8px;border:1px solid var(--line)">.venv/bin/python scripts/verify_s17.py --with-data
.venv/bin/python scripts/check_artifact_policy.py
.venv/bin/python -m pytest -q</pre>
<p class="small">All three checks run 100% offline/locally without human visual inspection.</p>
<p><a href="s17-cpad.html">← Full S17-CPAD scientific &amp; forensic audit</a></p>
</div></section>

<section class="s16-section"><h2>Gate-by-gate status for S17-CPAD</h2>{gate_table(card)}</section>
"""

    (ROOT / "docs/s17-cpad.html").write_text(
        page_shell("S17-CPAD GeoTIFF, 0.198183 HOLDOUT-DTI & Forensic Audit", audit_body, card)
    )
    (ROOT / "docs/s17-cpad-executive-summary.html").write_text(
        page_shell("S17-CPAD Executive Summary & Submission Guide", guide_body, card)
    )
    print("Rendered docs/s17-cpad.html, docs/s17-cpad-executive-summary.html, and docs/assets/s17-support.png.")


if __name__ == "__main__":
    render()
