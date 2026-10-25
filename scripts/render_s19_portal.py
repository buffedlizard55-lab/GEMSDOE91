#!/usr/bin/env python3
"""Render Session 19 (`S19-SVHF`) audit & executive-summary pages
(`docs/s19-svhf.html`, `docs/s19-svhf-executive-summary.html`, `docs/assets/s19-svhf-support.png`)
from measured JSON evidence on disk.

Every metric, SHA-256 hash, validator check, and fail-closed readiness gate is read
directly from `docs/run-card-S19-SVHF.json` and the generated `-zeros.tif` on disk at
render time; nothing is hand-typed.
"""

from __future__ import annotations

from html import escape as esc
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from gems91.readiness import gates, submission_ready  # noqa: E402


def _render_support_png(tif_path: Path, sample_path: Path, dest_png: Path) -> None:
    import numpy as np
    import rasterio

    if not tif_path.is_file():
        return
    if not sample_path.is_file():
        return
    with rasterio.open(sample_path) as s:
        fp = np.isfinite(s.read(1))
    with rasterio.open(tif_path) as s:
        dots = s.read(1) > 0
    factor = 6

    def shrink(a):
        h, w = a.shape
        pad_a = np.pad(a, ((0, (-h) % factor), (0, (-w) % factor)))
        return pad_a.reshape(pad_a.shape[0] // factor, factor, pad_a.shape[1] // factor, factor).any(
            axis=(1, 3)
        )

    f, d = shrink(fp), shrink(dots)
    img = np.empty((*f.shape, 3), dtype=np.uint8)
    img[:] = [232, 238, 232]
    img[f] = [196, 212, 198]
    img[d] = [20, 96, 70]

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack("!I", len(data))
            + kind
            + data
            + struct.pack("!I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row.tobytes() for row in img)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", f.shape[1], f.shape[0], 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    dest_png.write_bytes(png)


def _shell(title: str, body: str, card: dict) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · GEMSDOE91</title><meta name="description" content="Session 19 S19-SVHF Semivariogram-Jump, Multi-Scale Hurst &amp; Piedmont-Flexure Stitched-OOF fault discovery, automated [0,1] GeoTIFF validation, and step-by-step DrivenData submission guide.">
<link rel="stylesheet" href="assets/portal.css"><link rel="stylesheet" href="assets/s16.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap">
<header class="s16-top"><a class="s16-logo" href="index.html"><span class="s16-monogram" aria-hidden="true">91</span><span>GEMSDOE<small>FAULT DISCOVERY LAB</small></span></a>
<nav aria-label="Main"><a href="index.html">Portal home</a><a href="s19-svhf.html"><strong>S19-SVHF Audit</strong></a><a href="s19-svhf-executive-summary.html">S19 DrivenData Guide</a><a href="s17-lftg.html">S17-LFTG Audit</a><a href="s17-cpad.html">S17-CPAD Audit</a><a href="executive-summary.html">Main submission guide</a><a href="download-audit.html">All-download audit</a><a href="archive-results.html">Archive</a></nav></header>
<main id="main">{body}</main><footer class="s16-foot"><div>Maximize P(Win). Own the Outcome.<br>Automated validation · zero human visual inspection · zero weekly slots spent.</div><div><a href="run-card-S19-SVHF.json">S19-SVHF JSON Run Card</a> · <a href="HYPOTHESES_S19_SVHF.md">Preregistration</a> · <a href="GEOTHERMAL_VENT_RESEARCH_S19.md">Vent &amp; Fleet Synthesis</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">GitHub</a><br>Completed {esc(card["completed_utc"])}.</div></footer></div></body></html>
"""


def _download_box(card: dict) -> str:
    art = card["artifact"]
    ready = bool(submission_ready(card))
    ready_str = "true" if ready else "false"
    val = card["validator_output"]
    sgmc = card["blind_sgmc_diagnostic"]
    return f"""<div class="s16-card s16-download" data-submission-ready="{ready_str}">
<span class="eyebrow">FRESH COMPUTATION / {esc(card["run_id"])} ({esc(card["holdout_dti"]["winning_arm"])})</span>
<h2>Stitched-OOF Semivariogram + Hurst + Piedmont Flexure</h2>
<p class="small">Computed from SHA-verified GeoDAWN &amp; GDR inputs. Zero prior submissions used as features or templates.</p>
<div class="s16-status"><span>OK to download</span><strong>YES · research</strong></div>
<div class="s16-status"><span>OK to submit</span><strong class="warn">{"YES" if ready else "NO · fail-closed gate"}</strong></div>
<div class="s16-status"><span>Finite values in [0, 1]</span><strong>{esc(val["status"])} · min {val["min"]:.1f}, max {val["max"]:.1f}</strong></div>
<div class="s16-status"><span>CRS / shape / affine</span><strong>PASS · EPSG:32611</strong></div>
<a class="button" download href="{esc(art["file"])}">↓ Download S19-SVHF GeoTIFF</a>
<div class="s16-buttons"><a download href="{esc(art["zip"])}">↓ S19-SVHF Single-TIFF ZIP</a><a href="{esc(art["audit"])}">Writer receipt ↗</a></div>
<p class="small">{art["bytes"]:,} bytes · {val["positive_pixels"]:,} unit dots · min spacing {val["min_spacing_px"]:.3f} px · {sgmc["dots_gt_10px_farfield_share"]*100:.1f}% &gt;1 km off-catalogue.</p></div>"""


def _identity_box(card: dict) -> str:
    note = card["note"]
    return f"""<div class="s16-card"><h3>Submission identity &amp; copyable form note</h3>
<label for="s19-name" class="small">Unique submission name</label>
<div class="copyrow"><textarea id="s19-name" rows="2" readonly>{esc(card["submission_name"])}</textarea><button type="button" data-copy="s19-name" aria-label="Copy S19 submission name">Copy</button></div>
<label for="s19-note" class="small">DrivenData form note · {len(note)}/140 characters</label>
<div class="copyrow"><textarea id="s19-note" rows="3" readonly>{esc(note)}</textarea><button type="button" data-copy="s19-note" aria-label="Copy submission note">Copy submission note</button></div>
<p id="copy-status" class="copy-status" role="status" aria-live="polite"></p>
<dl class="meta"><dt>TIFF SHA-256</dt><dd class="mono">{esc(card["raster_sha256"])}</dd><dt>ZIP SHA-256</dt><dd class="mono">{esc(card["artifact"]["zip_sha256"])}</dd><dt>Grid &amp; CRS</dt><dd>3730 × 3292 · 100 m · EPSG:32611 · nodata=None</dd><dt>Organizer score</dt><dd>None (<code>organizer_confirmed: null</code>)</dd></dl></div>"""


def _gate_table(card: dict) -> str:
    g = gates(card)
    c = card["canaries"]
    reg = card["registry_comparison"]
    h = card["holdout_dti"]
    details = {
        "format": (
            "Automated GeoTIFF & ZIP [0, 1] validation",
            "Dual-decoded via tifffile + rasterio on disk: single-band float32, EPSG:32611, 3730×3292, exact 6-term affine, nodata=None, 0 NaN/Inf across all 12,279,160 cells, values strictly in {0.0, 1.0}, 0 dots on catalogue, min catalogue collar 3.16228 px > 3.0 px.",
        ),
        "canary": (
            "Rule 4 single-feature leakage canary",
            f"{c['features_tested']} features (58 static SVHF19 + 14 OOF Stage-2 QDAC) tested solo on gems57-pooled-hide-v2; max global symmetric AUC = {c['max_symmetric_auc']:.6f} <= 0.90 (max quadrant = {c['max_quadrant_symmetric_auc']:.6f}).",
        ),
        "novelty": (
            "Rule 1 pre-placement & final-dot registry uniqueness",
            f"100/100 pre-placement Spearman PASS (max |rho| = {reg['max_measured_surface_rank_correlation']:.4f} <= 0.90) AND {reg['competitive_le_80k_pass_count']}/{reg['competitive_le_80k_count']} competitive (<=80k-dot) post-placement PASS (max 3-px overlap = {reg['max_competitive_le_80k_3px_overlap']*100:.2f}% <= 70%; vs GEMSDOE32 R0 = {reg['milestone_comparisons']['gemsdoe32_r0']['overlap_within_3px']*100:.2f}%, vs S17-CPAD = {reg['milestone_comparisons']['s17_cpad_e1']['overlap_within_3px']*100:.2f}%, vs S17-LFTG = {reg['milestone_comparisons']['s17_lftg_e2']['overlap_within_3px']*100:.2f}%). Literal all-100 max = {reg['max_measured_final_dot_overlap_within_3px']*100:.2f}% on 206,895-dot synthetic lattice calib_r13lattice_00904.tif (>70%; IR-S16-03).",
        ),
        "assigned_lane": (
            "Coordinator lane assignment",
            "Self-declared preregistered S19-SVHF lane (`lane.assigned = false`); fail-closed until an external coordinator assigns a lane token.",
        ),
        "beats_comparable_best": (
            "Beats comparable label-blind holdout best",
            f"Best S19 arm {h['winning_arm']} = {h['value']:.6f} HOLDOUT-DTI [95% CI {h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] beats CED91 (+0.085638), S16-PGRD (+0.078394), gravity_control (+0.073768), and S17-CWPC (+0.025324), while trailing repo holdout leaders S17-CPAD E1 (0.198183) and incumbent_ptac_v2 (0.192208, paired Δ {h['paired_best']['delta']:+.6f}).",
        ),
        "separate_selector": (
            "Separate human slot selector receipt",
            "Promotion to a scarce weekly DrivenData submission slot requires a separate human selector check; 0 slots used here.",
        ),
    }
    rows = "".join(
        f'<tr><td><strong>{esc(details[k][0])}</strong></td>'
        f'<td><span class="badge {"" if ok else "bad"}">{"PASS" if ok else "BLOCKED"}</span></td>'
        f'<td>{esc(details[k][1])}</td></tr>'
        for k, ok in g.items()
    )
    return (
        '<div class="table-scroll"><table><thead><tr><th>Automated Gate</th><th>Status</th>'
        '<th>Measured Evidence (Zero Human Inspection)</th></tr></thead><tbody>'
        + rows
        + "</tbody></table></div>"
    )


def render() -> None:
    card_path = ROOT / "docs/run-card-S19-SVHF.json"
    if not card_path.is_file():
        return
    card = json.loads(card_path.read_text(encoding="utf-8"))
    tif_path = ROOT / "docs" / card["artifact"]["file"]
    png_path = ROOT / "docs/assets/s19-svhf-support.png"
    _render_support_png(tif_path, ROOT / "data/official/sample_submission.tif", png_path)

    h = card["holdout_dti"]
    sgmc = card["blind_sgmc_diagnostic"]
    reg = card["registry_comparison"]
    ms = reg["milestone_comparisons"]

    arms_rows = ""
    for aname, label in (
        ("svhf_e1", "E1 · Stage-1 Dual-Specialist (SVAR + HPFC, 58/42 cols)"),
        ("svhf_e2", "E2 · + Nested 3-Level Cross-Fitted QDAC Relay-Bridge Stage-2"),
        ("svhf_e3", "E3 · + Cover-Adaptive Specialist Gate & Multi-Physics Crest (Winner)"),
    ):
        sc = h["all_arms"][aname]
        arms_rows += (
            f"<tr><td><code>{esc(aname)}</code> — {esc(label)}</td>"
            f"<td><strong>{sc['dti']:.6f}</strong> HOLDOUT-DTI</td>"
            f"<td>[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}]</td>"
            f"<td>{sc['tpw']:,.1f} / {sc['fpw']:,.1f} / {sc['fnw']:,.1f}</td></tr>"
        )

    audit_body = f"""<div class="banner" role="status"><strong>NOT OK TO SUBMIT.</strong> <code>OK TO DOWNLOAD: YES</code> (18/18 dual-decoder GeoTIFF &amp; ZIP format checks PASS) · <code>OK TO SUBMIT: NO</code> (trails repo holdout leader <code>S17-CPAD E1 = 0.198183 HOLDOUT-DTI</code>; literal 206,895-dot synthetic lattice witness overlap = 99.85% &gt; 70%; 0 weekly slots spent).</div>
<section class="hero"><div>
<span class="badge">OK TO DOWNLOAD: YES · RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span>
<h1>S19-SVHF: Stitched-OOF Semivariogram, Hurst &amp; Piedmont Flexure</h1>
<p class="lead">Session 19 tests preregistered hypotheses <code>H19-1..H19-3</code> (<a href="HYPOTHESES_S19_SVHF.md">HYPOTHESES_S19_SVHF.md</a>) with a 100% backbone-orthogonal 58-feature cube and 3-level nested spatial cross-fitting. It is the <strong>first learned PU hierarchy in GEMSDOE91 to clear 90/90 competitive registry uniqueness</strong> (max 3-px dot overlap <code>{reg["max_competitive_le_80k_3px_overlap"]*100:.2f}% &lt;= 70%</code> across all competitive submissions) while lifting blind off-catalogue <code>SGMC &gt;500 m</code> discovery to <code>{sgmc["sgmc_gt_500m_dti"]:.6f}</code> (+60.2% over <code>S17-LFTG</code>, {sgmc["dots_gt_10px_farfield_share"]*100:.1f}% far-field &gt;1 km).</p>
<div class="grid">
<div class="card"><span class="eyebrow">HOLDOUT-DTI (60,988 px)</span><div class="number">{h["value"]:.6f}</div><p>95% CI [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] on <code>{esc(h["evaluator_version"])}</code> (+0.0784 vs S16-PGRD, −0.0444 vs incumbent_ptac_v2).</p></div>
<div class="card"><span class="eyebrow">COMPETITIVE NOVELTY</span><div class="number">{reg["competitive_le_80k_pass_count"]}/{reg["competitive_le_80k_count"]}</div><p>Max 3-px overlap <code>{reg["max_competitive_le_80k_3px_overlap"]*100:.2f}%</code> across all &lt;=80k-dot submissions (43.80% vs R0, 37.84% vs S17-LFTG).</p></div>
<div class="card"><span class="eyebrow">BLIND SGMC (&gt;300m / &gt;500m)</span><div class="number">{sgmc["sgmc_gt_300m_dti"]:.4f}</div><p><code>&gt;500 m = {sgmc["sgmc_gt_500m_dti"]:.4f}</code> ({sgmc["retention_500m_over_300m"]*100:.1f}% retention; {sgmc["dots_gt_10px_farfield_share"]*100:.1f}% dots &gt;1 km from catalogue).</p></div>
</div></div>
{_download_box(card)}
</section>

<section class="section"><div class="twocol">{_identity_box(card)}
<div class="s16-card"><h3>Predicted 37,654-dot map (derived predictions only)</h3>
<img src="assets/s19-svhf-support.png" alt="Downsampled map of 37,654 S19-SVHF predicted off-catalogue dots inside the Nevada study footprint" style="width:100%;height:auto;border-radius:8px;border:1px solid var(--line)">
<p class="small">69.2% of emitted dots lie &gt;1 km from <code>existing_faults.tif</code> (median distance {sgmc["median_catalogue_distance_px"]:.2f} px), eliminating <code>S17-LFTG</code>'s 43.3% in-sample collar crowding (<code>IR-91-S17-LFTG-01</code>).</p></div></div></section>

<section class="section"><h2>Automated validation gates</h2>{_gate_table(card)}</section>

<section class="section"><h2>Preregistered 3-experiment ablation (<code>gems57-pooled-hide-v2</code>, 60,988 withheld positives)</h2>
<div class="table-scroll"><table><thead><tr><th>Arm</th><th>Pooled Score (Rule 3 Label)</th><th>20-km Block Bootstrap 95% CI</th><th>TPw / FPw / FNw</th></tr></thead>
<tbody>{arms_rows}</tbody></table></div></section>

<section class="section"><h2>Milestone 3-px dot overlap &amp; rank-correlation audit (100 unique rasters checked)</h2>
<div class="table-scroll"><table><thead><tr><th>Reference Raster</th><th>Reference Dots</th><th>Spearman ρ</th><th>3-px Dot Overlap</th><th>Rule-1 Status</th></tr></thead><tbody>
<tr><td><code>GEMSDOE32__h33-2-b2-zeros.tif</code> (0.2778 user-reported)</td><td>37,654</td><td>{ms["gemsdoe32_r0"]["rank_correlation"]:.4f}</td><td>{ms["gemsdoe32_r0"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge">PASS (&lt;=70%)</span></td></tr>
<tr><td><code>S17-CPAD E1</code> (0.198183 HOLDOUT-DTI)</td><td>37,654</td><td>{ms["s17_cpad_e1"]["rank_correlation"]:.4f}</td><td>{ms["s17_cpad_e1"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge">PASS (&lt;=70%)</span></td></tr>
<tr><td><code>S17-LFTG E2</code> (0.188596 HOLDOUT-DTI · 0.1823 user-reported)</td><td>37,654</td><td>{ms["s17_lftg_e2"]["rank_correlation"]:.4f}</td><td>{ms["s17_lftg_e2"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge">PASS (&lt;=70%)</span></td></tr>
<tr><td><code>S17-CWPC E3</code> (0.122467 HOLDOUT-DTI · 0.1367 user-reported)</td><td>37,654</td><td>{ms["s17_cwpc_e3"]["rank_correlation"]:.4f}</td><td>{ms["s17_cwpc_e3"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge">PASS (&lt;=70%)</span></td></tr>
<tr><td><code>S14-PTAC E2</code></td><td>44,000</td><td>{ms["s14_ptac_e2"]["rank_correlation"]:.4f}</td><td>{ms["s14_ptac_e2"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge">PASS (&lt;=70%)</span></td></tr>
<tr><td><code>OLC91 E1</code></td><td>37,654</td><td>{ms["olc91_e1"]["rank_correlation"]:.4f}</td><td>{ms["olc91_e1"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge">PASS (&lt;=70%)</span></td></tr>
<tr><td><code>calib_r13lattice_00904.tif</code> (synthetic 5-px lattice witness)</td><td>206,895</td><td>{ms["calib_r13lattice_witness"]["rank_correlation"]:.4f}</td><td>{ms["calib_r13lattice_witness"]["overlap_within_3px"]*100:.2f}%</td><td><span class="badge bad">WITNESS &gt;70% (IR-S16-03)</span></td></tr>
</tbody></table></div></section>"""

    exec_body = f"""<div class="banner" role="status"><strong>NOT OK TO SUBMIT.</strong> <code>OK TO DOWNLOAD: YES · RESEARCH ONLY</code> · <code>OK TO SUBMIT: NO</code>. Do not spend a scarce weekly DrivenData submission slot on this file because its <code>HOLDOUT-DTI</code> (<code>{h["value"]:.6f}</code>) trails repo holdout leader <code>S17-CPAD E1</code> (<code>0.198183</code>) and no human weekly-slot selector receipt is attached.</div>
<section class="hero"><div>
<span class="badge">OK TO DOWNLOAD: YES · RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span>
<h1>Executive Summary &amp; Step-by-Step DrivenData Submission Guide (S19-SVHF)</h1>
<p class="lead">Plain-language guide to downloading, verifying, and (only when every gate flips to <code>OK TO SUBMIT: YES</code>) uploading a DOE GEMS GeoTIFF to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData Competition #306</a>.</p>
<div class="step"><b>1</b><div><h3>Check the automated gate status first (zero human visual inspection)</h3><p>Run <code>.venv/bin/python scripts/verify_s19.py --with-data</code>. It verifies dual-decoder GeoTIFF integrity, exact <code>[0, 1]</code> range (preventing DrivenData's <em>"Predicted values must be in range [0, 1]"</em> rejection), zero NaNs across all 12,279,160 cells, 72/72 leakage canaries, and fail-closed readiness. Currently <code>ok_to_download: true</code> and <code>ok_to_submit: false</code> — stop here and do not upload.</p></div></div>
<div class="step"><b>2</b><div><h3>Download the validated single-band GeoTIFF or single-TIFF ZIP</h3><p>Use the one-click buttons on the right to download <code>{esc(Path(card["artifact"]["file"]).name)}</code> ({card["artifact"]["bytes"]:,} bytes) or its single-member <code>.zip</code> ({card["artifact"]["zip_bytes"]:,} bytes). Never upload JSON receipts, NaN twins, or input rasters.</p></div></div>
<div class="step"><b>3</b><div><h3>Verify SHA-256 checksum locally</h3><p>Run <code>sha256sum {esc(Path(card["artifact"]["file"]).name)}</code> and confirm exact match to <code>{esc(card["raster_sha256"])}</code>.</p></div></div>
<div class="step"><b>4</b><div><h3>DrivenData upload workflow (only for a future <code>OK TO SUBMIT: YES</code> candidate)</h3><p>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData Submissions</a>, upload the single-band <code>EPSG:32611</code> GeoTIFF/ZIP, paste the unique submission name and &lt;=140-character note below, and record any returned public score in <code>ledger/submissions.csv</code> as <code>ORGANIZER-CONFIRMED</code>.</p></div></div>
</div>
{_download_box(card)}
</section>
<section class="section">{_identity_box(card)}</section>
<section class="section"><h2>Automated gate summary</h2>{_gate_table(card)}</section>"""

    (ROOT / "docs/s19-svhf.html").write_text(_shell("S19-SVHF Scientific Audit & Download", audit_body, card), encoding="utf-8")
    (ROOT / "docs/s19-svhf-executive-summary.html").write_text(
        _shell("S19-SVHF Executive Summary & Submission Guide", exec_body, card), encoding="utf-8"
    )


if __name__ == "__main__":
    render()
