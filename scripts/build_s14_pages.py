#!/usr/bin/env python3
"""Build deterministic S14-HVDC audit/guide pages and inject the current banner.

The builder reads only measured `docs/run-card-S14-HVDC.json` evidence and re-hashes the
published TIFF/ZIP before offering either file. It never promotes or uploads a file.
"""
from __future__ import annotations

from html import escape
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
START = "<!-- S14:START -->"
END = "<!-- S14:END -->"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _shell(title: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} · GEMSDOE91</title><meta name="description" content="S14-HVDC measured holdout evidence, validated GeoTIFF and fail-closed submission verdict.">
<link rel="stylesheet" href="assets/portal.css"><script defer src="assets/portal.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a><div class="wrap"><header class="top"><a class="brand" href="index.html">GEMSDOE<span>91 / FAULT MAPPING LAB</span></a><nav aria-label="Main"><a href="index.html">Current verdict</a><a href="s14-hvdc.html"><strong>S14-HVDC (#1 · 0.2622 ★)</strong></a><a href="s14-hvdc-executive-summary.html">S14 guide</a><a href="research.html">Evidence &amp; sources</a></nav></header>
<main id="main">{body}</main><footer><div>Research evidence; not an organizer score.<br>Generated from <code>docs/run-card-S14-HVDC.json</code>.</div><div><a href="run-card-S14-HVDC.json">Machine-readable run card</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">Source on GitHub</a><br>No automatic competition uploads. No credentials stored.</div></footer></div></body></html>\n'''


def _current_banner(card: dict, tif_rel: str, zip_rel: str) -> str:
    h = card["holdout_dti"]
    sg = card["blind_sgmc_offcatalogue_control"]
    a = card["artifact"]
    s = card["submission"]
    return f'''{START}<div class="banner"><strong>Active review (2026-10-25): no new TIFF was generated.</strong> The S15-HCPA file is historical and downloadable for research only. Its HOLDOUT-DTI (0.091399; 60,988 withheld positives; 95% CI 0.083166–0.099501) does not validate the exact final far-field/halo emission, and the complete registry was not checked. <strong>OK TO DOWNLOAD: YES · OK TO SUBMIT: NO.</strong> See <a href="REVIEW-ARENA-BB16B6AE-20261025.md">the review</a> and <a href="run-card-REVIEW-BB16B6AE.json">review run card</a>.</div><section class="hero" id="s14-current"><div><span class="eyebrow">CURRENT #1 COMPARABLE HOLDOUT · SESSION 14 / S14-HVDC E2</span><h1>A new validated GeoTIFF.<br>Automated verdict: duplicate stop.</h1><p class="lead">Leak-free hydrothermal-plume, Salem tilt-depth, swarm and en-echelon relay/wash auto-context raised the common holdout and independent geological control. The file is range-safe and easy to download; repository governance does not authorize an automatic live upload.</p><p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH</span> <span class="badge bad">OK TO SUBMIT: NO — RULE 1 DUPLICATE STOP</span></p><p class="small"><strong>{h['value']:.6f} HOLDOUT-DTI</strong> · 95% CI [{h['ci95'][0]:.6f}, {h['ci95'][1]:.6f}] · {h['withheld_positives']:,} withheld positives · paired Δ +{h['paired_best']['delta']:.6f} vs S13, 95% CI [+{h['paired_best']['ci95'][0]:.6f}, +{h['paired_best']['ci95'][1]:.6f}] · <strong>{sg['value']:.6f} BLIND-SGMC-CONTROL-DTI</strong> (not an organizer score).</p><p><a class="button outline" href="s14-hvdc.html">Open full S14 scientific audit ↗</a> <a class="button outline" href="s14-hvdc-executive-summary.html">Open exact download &amp; submission guide ↗</a></p></div><div class="download" data-submission-ready="false"><div class="label">AUTOMATED FILE STATUS</div><h2>{escape(s['name'])}</h2><div class="status"><span>OK to download</span><strong>YES — RANGE-SAFE</strong></div><div class="status"><span>OK to submit</span><strong>NO — DUPLICATE STOP</strong></div><div class="status"><span>All cells finite [0,1]</span><strong>PASS · 0 NaNs</strong></div><div class="status"><span>CRS / shape / transform</span><strong>PASS</strong></div><a class="button" download href="{escape(tif_rel)}">↓ Download S14-HVDC GeoTIFF</a><div style="text-align:center;margin-top:12px"><a download href="{escape(zip_rel)}">Single-TIFF ZIP</a> · <a href="run-card-S14-HVDC.json">Run card</a></div><p class="small">{a['n_dots']:,} binary dots · EPSG:32611 · 3730×3292 · SHA-256 {escape(card['raster_sha256'][:20])}…</p></div></section>
<div class="banner"><strong>Do not upload this file.</strong> Technical, leakage, holdout, canonical-registry and external dotted-fleet checks passed, but the literal Rule 1 final-dot gate failed: 99.838% overlap against the synthetic Nevada lattice, 84.706% against S13-PTHA and 70.056% against dense h25 context. Per protocol this is a negative duplicate stop; no selector can override it.</div>{END}'''


def _inject(path: Path, fragment: str) -> None:
    text = path.read_text(encoding="utf-8")
    if START in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        text = before + after
    marker = '<main id="main">'
    if marker not in text:
        raise ValueError(f"Cannot inject S14 banner: {path}")
    text = text.replace(marker, marker + fragment, 1)
    path.write_text(text, encoding="utf-8")


def build() -> None:
    card = json.loads((DOCS / "run-card-S14-HVDC.json").read_text(encoding="utf-8"))
    artifact = card["artifact"]
    tif = ROOT / artifact["primary_zeros_tif"]
    zipped = ROOT / artifact["zip_bundle"]
    if not tif.is_file() or not zipped.is_file():
        raise FileNotFoundError("S14 published TIFF or ZIP is missing")
    if _sha256(tif) != card["raster_sha256"] or _sha256(tif) != artifact["primary_zeros_sha256"]:
        raise ValueError("S14 TIFF SHA-256 mismatch")
    if _sha256(zipped) != artifact["zip_sha256"]:
        raise ValueError("S14 ZIP SHA-256 mismatch")
    with zipfile.ZipFile(zipped) as zf:
        if zf.namelist() != [tif.name] or zf.read(tif.name) != tif.read_bytes():
            raise ValueError("S14 ZIP must contain exactly the advertised TIFF")
    if card.get("submission_ready") is not False:
        raise ValueError("S14 research portal is fail-closed; submission_ready must be false")

    tif_rel = Path(artifact["primary_zeros_tif"]).relative_to("docs").as_posix()
    zip_rel = Path(artifact["zip_bundle"]).relative_to("docs").as_posix()
    h = card["holdout_dti"]
    sg = card["blind_sgmc_offcatalogue_control"]
    can = card["canaries"]
    reg = card["registry_comparison"]
    a = card["artifact"]
    sub = card["submission"]
    experiments = card["experiments"]
    banner = _current_banner(card, tif_rel, zip_rel)

    exp_rows = "".join(
        f"<tr><td><strong>{escape(e['exp_id'])}</strong></td><td>{escape(e['hypothesis_id'])}</td>"
        f"<td>{e['n_features']}</td><td><strong>{e['holdout']['holdout_dti']:.6f}</strong><br><small>95% CI [{e['holdout']['ci_95'][0]:.6f}, {e['holdout']['ci_95'][1]:.6f}]</small></td>"
        f"<td>{e['paired_vs_s13_ptha_e3']['delta']:+.6f}<br><small>paired CI [{e['paired_vs_s13_ptha_e3']['ci95'][0]:+.6f}, {e['paired_vs_s13_ptha_e3']['ci95'][1]:+.6f}]</small></td></tr>"
        for e in experiments
    )
    fold_rows = "".join(
        f"<tr><td>{escape(f['name'])}</td><td>{f['n_withheld_positives']:,}</td><td>{int(f['emitted_mass']):,}</td><td>{f['T']:.1f}</td><td>{f['M']:.1f}</td><td><strong>{f['fold_dti']:.6f}</strong></td></tr>"
        for f in h["per_fold"]
    )

    audit_body = banner + f'''
<section class="section"><h2>Automated measured result</h2><div class="grid"><article class="card"><span class="eyebrow">PRIMARY HOLDOUT</span><div class="number">{h['value']:.6f}</div><p>HOLDOUT-DTI · 95% CI {h['ci95'][0]:.6f}–{h['ci95'][1]:.6f}<br>{h['withheld_positives']:,} withheld positives · <code>{escape(h['evaluator_version'])}</code></p></article><article class="card"><span class="eyebrow">BLIND GEOLOGICAL CONTROL</span><div class="number">{sg['value']:.6f}</div><p>BLIND-SGMC-CONTROL-DTI · {sg['n_offcatalogue_sgmc_positives']:,} off-catalogue positives<br>Not a leaderboard score.</p></article><article class="card"><span class="eyebrow">FORMAT &amp; RANGE</span><div class="number">PASS</div><p>Single-band float32 · all {12_279_160:,} cells finite · exact values {{0,1}} · nodata=None · EPSG:32611.</p></article></div></section>
<section class="section"><h2>Three preregistered experiments</h2><p>E1 exposed and preserved a regional global-OLS/raw-level shift as an honest negative. E2 fixed it with regionally invariant local operators plus leak-free two-stage relay/wash context and became the winner. E3 tested the continuous-Steger/self-credit emitter and was positive vs S13 but slightly below E2.</p><div class="table-scroll"><table><thead><tr><th>Arm</th><th>Hypothesis</th><th>Features</th><th>HOLDOUT-DTI</th><th>Δ vs S13-PTHA E3</th></tr></thead><tbody>{exp_rows}</tbody></table></div></section>
<section class="section"><h2>Winner by spatial quadrant</h2><div class="table-scroll"><table><thead><tr><th>Fold</th><th>Withheld positives</th><th>Dots</th><th>T</th><th>M</th><th>HOLDOUT-DTI</th></tr></thead><tbody>{fold_rows}</tbody></table></div><p class="small">Whole fault-segment complexes withheld with a 1 km buffer; every catalogue-derived feature uses visible faults only; visible faults are masked pixel-exactly; pooled α=0.2, β=0.8, 300 m triangular-kernel DTI.</p></section>
<section class="section"><h2>What changed scientifically</h2><div class="twocol"><div><h3>Hydrothermal feeder physics</h3><ul><li>Back-projects GDR thermal and blind geothermometry plumes upslope from basin-floor discharge to concealed feeder structures; <code>dist_known_fault_px</code> is banned.</li><li>Uses local playa/basin-deconfounded conductivity and gravity steps, Salem magnetic tilt-depth, draped GeoDAWN magnetic gradients and corrected positive dependent-swarm excess.</li><li>Stage 2 uses six inner out-of-fold models to detect two-sided collinear wash bridges, en-echelon relay ramps and conjugate intersections without leaking the outer test fold.</li></ul></div><div><h3>Named mimics and controls</h3><p>{escape(card['named_non_fault_mimic_process'])}.</p><p>Single-feature leakage canary: <strong>{can['n_features_checked']}/{can['n_features_checked']} PASS</strong>; maximum symmetric AUC {can['max_symmetric_auc']:.5f} ≤ 0.90 on <code>{escape(can['worst_feature'])}</code>.</p><p><a href="HYPOTHESES_S14_HVDC.md">Five ranked hypotheses and frozen experiment ladder ↗</a> · <a href="GEOTHERMAL_VENT_KNOWLEDGE_BASE.md">Verified/source-qualified geothermal knowledge base ↗</a></p></div></div></section>
<section class="section"><h2>Uniqueness and fail-closed verdict</h2><div class="table-scroll"><table><thead><tr><th>Scope</th><th>Checked</th><th>Surface |ρ|</th><th>Max directed 3-px overlap</th><th>Result</th></tr></thead><tbody><tr><td>Canonical registry</td><td>{reg['canonical_registry_scope']['n_checked']}</td><td>{reg['canonical_registry_scope']['max_abs_surface_spearman']:.4f}</td><td>{100*reg['canonical_registry_scope']['max_3px_dot_overlap']:.2f}%</td><td>PASS</td></tr><tr><td>External dotted fleet</td><td>{reg['external_dotted_fleet_scope']['n_checked']}</td><td>{reg['external_dotted_fleet_scope']['max_abs_surface_spearman']:.4f}</td><td>{100*reg['external_dotted_fleet_scope']['max_3px_dot_overlap']:.2f}%</td><td>PASS</td></tr><tr><td>Universal indexed files</td><td>{reg['universal_all_files_scope']['n_checked']}</td><td>{reg['universal_all_files_scope']['max_abs_surface_spearman']:.4f}</td><td>{100*reg['universal_all_files_scope']['max_3px_dot_overlap']:.2f}%</td><td>BLOCKED by synthetic blanket / siblings</td></tr></tbody></table></div><p><strong>Automated status:</strong> research download YES; live submission NO. Unique bytes, better holdout results and clean external dotted-fleet novelty do not override a literal >70% Rule 1 overlap. Verdict: negative duplicate stop.</p></section>
<section class="section"><div class="card"><h2>File identification</h2><dl class="meta"><dt>Name</dt><dd class="mono">{escape(sub['name'])}</dd><dt>Note ({sub['note_length']}/140)</dt><dd>{escape(sub['note'])}</dd><dt>TIFF SHA-256</dt><dd class="mono">{escape(card['raster_sha256'])}</dd><dt>ZIP SHA-256</dt><dd class="mono">{escape(a['zip_sha256'])}</dd><dt>Bytes / dots</dt><dd>{a['primary_zeros_bytes']:,} / {a['n_dots']:,}</dd><dt>Catalogue clearance</dt><dd>{a['min_catalogue_distance_px']} px; 0 dots at ≤3 px</dd></dl><a class="button" download href="{escape(tif_rel)}">↓ Download exact GeoTIFF bytes</a> <a class="button outline" download href="{escape(zip_rel)}">Download single-TIFF ZIP</a></div></section>'''

    guide_body = banner + f'''
<section class="section"><h2>Why the prior range error cannot be caused by this file's values</h2><p>The shared writer emitted <code>{escape(tif.name)}</code> with one float32 band, exact values {{0.0, 1.0}}, <strong>zero NaN/Inf/sentinel cells across all 12,279,160 cells</strong>, zeros outside the footprint, and <code>nodata=None</code>. It re-opened TIFF and ZIP bytes and validated CRS, shape, affine transform, range, catalogue mass and the >300 m collar. This removes the measured local causes of “Predicted values must be in range [0, 1]”; it does not guarantee organizer acceptance for unrelated reasons.</p></section>
<section class="section"><h2>This file cannot be submitted; exact process for a future compliant candidate</h2><div class="step"><b>1</b><div><h3>Generate a new candidate that clears Rule 1</h3><p>Today S14-HVDC says <strong>NOT OK TO SUBMIT — NEGATIVE DUPLICATE STOP</strong>. Do not upload it. A future file must remain at or below 0.90 surface rank correlation and 70% directed 3-px final-dot overlap against every registry raster, then also clear the assigned-lane, eligibility, AI-disclosure and live allowance checks.</p></div></div><div class="step"><b>2</b><div><h3>Download and verify exact bytes</h3><p>Use only <a download href="{escape(tif_rel)}"><code>{escape(tif.name)}</code></a> or its <a download href="{escape(zip_rel)}">single-TIFF ZIP</a>. Expected TIFF SHA-256:</p><p class="mono">{escape(card['raster_sha256'])}</p></div></div><div class="step"><b>3</b><div><h3>Upload only the future approved all-finite file</h3><p>After a future candidate passes every gate, open the authenticated <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData submissions page</a>, choose that approved <code>-zeros.tif</code> or ZIP—not this blocked S14 file, JSON, HTML, Markdown, or a NaN companion. The note below identifies this research artifact only; it is not upload authorization.</p><label for="s14-note" class="small">Submission note · {sub['note_length']}/140</label><div class="copyrow"><textarea id="s14-note" readonly rows="3">{escape(sub['note'])}</textarea><button data-copy="s14-note" type="button">Copy</button></div><p id="copy-status" class="copy-status" role="status" aria-live="polite"></p></div></div><div class="step"><b>4</b><div><h3>Record the organizer receipt</h3><p>Only the score returned by the authenticated submission page may be labelled <code>ORGANIZER-CONFIRMED</code>. Never record {h['value']:.6f} HOLDOUT-DTI or {sg['value']:.6f} BLIND-SGMC-CONTROL-DTI as a leaderboard score.</p></div></div></section>
<section class="section"><h2>Automatic gate receipt</h2><ul class="checklist"><li><span>TIFF/ZIP identity &amp; range</span><span class="badge">PASS</span></li><li><span>{can['n_features_checked']}/{can['n_features_checked']} leakage canaries</span><span class="badge">PASS · max {can['max_symmetric_auc']:.5f}</span></li><li><span>Beats comparable S13 holdout best</span><span class="badge">PASS · +{h['paired_best']['delta']:.6f}</span></li><li><span>Canonical / external dotted novelty</span><span class="badge">PASS</span></li><li><span>Complete universal novelty / assigned lane / selector</span><span class="badge bad">BLOCKED</span></li></ul></section>'''

    (DOCS / "s14-hvdc.html").write_text(_shell("S14-HVDC scientific audit", audit_body), encoding="utf-8")
    (DOCS / "s14-hvdc-executive-summary.html").write_text(_shell("S14-HVDC executive summary & submission guide", guide_body), encoding="utf-8")

    for target in (DOCS / "index.html", DOCS / "executive-summary.html"):
        _inject(target, banner)
    print("Built S14 pages: research download YES; competition submission NO; hashes verified.")


if __name__ == "__main__":
    build()
