#!/usr/bin/env python3
"""Build H91 historical research pages from the corrected run card and audit.

The pages intentionally offer the existing TIFF only for research. A local
format receipt cannot override the literal duplicate result or grant upload
clearance.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOWNLOADS = DOCS / "downloads"
DATA = DOCS / "data"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def shell(title: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,follow">
  <title>{esc(title)} · GEMSDOE91</title>
  <link rel="stylesheet" href="assets/portal.css">
  <style>
    .audit-flag{{border:2px solid #9f2f2f;background:#fff1f1;color:#641d1d;padding:1rem;border-radius:.6rem}}
    .audit-good{{border:1px solid #9b7c2b;background:#fff9e9;color:#58440d;padding:1rem;border-radius:.6rem}}
    .audit-table{{width:100%;border-collapse:collapse}}
    .audit-table th,.audit-table td{{border-bottom:1px solid #ccd4dc;padding:.65rem;text-align:left;vertical-align:top}}
    .audit-mono{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}}
    .research-download{{display:inline-block;margin:.35rem .5rem .35rem 0;padding:.75rem 1rem;border:1px solid #405b70;border-radius:.4rem;text-decoration:none}}
    .small-note{{font-size:.9rem;opacity:.85}}
  </style>
</head>
<body>
<header class="top"><a class="brand" href="index.html">GEMSDOE<span>91 / FAULT MAPPING LAB</span></a>
<nav aria-label="Main"><a href="index.html">Research portal</a><a href="h91-ddvtc.html">H91 audit</a><a href="h91-executive-summary.html">H91 guide</a><a href="research.html">Evidence &amp; sources</a></nav></header>
<main id="main" class="wrap">{body}</main>
<footer class="wrap small-note">GEMSDOE91 · Historical H91 artifact review · No competition upload is performed by this site.</footer>
</body></html>\n'''


def _load() -> tuple[dict, dict, dict]:
    card = json.loads((ROOT / "evidence/run_card.json").read_text(encoding="utf-8"))
    audit = json.loads((ROOT / "evidence/h91_lattice_reaudit_20261024.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "evidence/registry_uniqueness.json").read_text(encoding="utf-8"))
    if card.get("verdict") != "negative" or card.get("ok_to_submit") is not False:
        raise ValueError("H91 page build is fail-closed: card must explicitly deny submission")
    if registry.get("uniqueness_pass") is not False or not registry.get("is_duplicate"):
        raise ValueError("H91 page build requires the literal duplicate evidence")
    witness = card["registry_uniqueness"]["direct_lattice_witness"]
    if witness["directed_overlap"] <= witness["overlap_limit_strict_greater_than"]:
        raise ValueError("H91 page build refuses a non-duplicate or missing witness")
    h91_record = next(x for x in audit["artifacts"] if x["label"] == "H91-E1")
    if h91_record["candidate_sha256"] != card["submission"]["sha256_tif"]:
        raise ValueError("H91 card and re-audit refer to different TIFF bytes")
    if h91_record["witness_comparison"]["directed_overlap"] != witness["directed_overlap"]:
        raise ValueError("H91 card and re-audit overlap measurements differ")
    tif = DOWNLOADS / card["submission"]["research_tif"]
    zipped = DOWNLOADS / card["submission"]["research_zip"]
    if hashlib.sha256(tif.read_bytes()).hexdigest() != card["submission"]["sha256_tif"]:
        raise ValueError("H91 research TIFF hash does not match the run card")
    if hashlib.sha256(zipped.read_bytes()).hexdigest() != card["submission"]["sha256_zip"]:
        raise ValueError("H91 research ZIP hash does not match the run card")
    with zipfile.ZipFile(zipped) as archive:
        if archive.namelist() != [tif.name] or archive.read(tif.name) != tif.read_bytes():
            raise ValueError("H91 research ZIP must contain only the advertised TIFF bytes")
    return card, audit, registry


def _audit_body(card: dict, audit: dict) -> str:
    sub = card["submission"]
    holdout = card["scores"]["primary_holdout"]
    witness = card["registry_uniqueness"]["direct_lattice_witness"]
    local = sub["validator_results"]
    checks = local["vendor_template_checks"]
    check_rows = "".join(
        f"<tr><td>{esc(name)}</td><td>{'PASS' if result else 'FAIL'}</td></tr>"
        for name, result in checks.items()
    )
    old_note = sub["submission_note"]
    return f'''<section class="hero">
  <div><span class="eyebrow">POST-HOC REGISTRY RE-AUDIT · {esc(card['posthoc_review']['reviewed_utc'])}</span>
  <h1>H91 E1 research artifact</h1>
  <p class="lead">The previously reported 20-raster uniqueness pass was incomplete and used the wrong overlap rule for a dense reference. The stored final TIFF has now been checked against the pinned lattice using the restored shared implementation.</p></div>
  <div class="audit-flag"><strong>OK TO DOWNLOAD FOR RESEARCH: YES</strong><br><strong>OK TO SUBMIT: NO</strong><p>{esc(card['decision_reason'])}</p></div>
</section>
<section class="section">
  <div class="audit-flag"><h2>Literal duplicate stop</h2>
  <p><strong>{witness['candidate_dots_within_3px']:,} / {witness['candidate_dots']:,} dots</strong> are within 3 pixels of <code>{esc(witness['registry_raster'])}</code>: <strong>{100*witness['directed_overlap']:.4f}%</strong>. The strict duplicate threshold is &gt;70%. Verdict: <strong>DUPLICATE</strong>.</p>
  <p>Final-dot raster Spearman against this witness: <code>{witness['final_dot_raster_spearman_full_footprint']:.8f}</code> (not the unavailable continuous H91 surface). Reverse overlap and Jaccard are diagnostics only. The continuous pre-placement H91 surface was not retained, so its rank correlation against this lattice is unverified; the final-dot overlap alone is conclusive.</p>
  <p class="small-note">Registry raster SHA-256: <code class="audit-mono">{esc(witness['registry_sha256'])}</code> · source commit <code>{esc(witness['registry_git_commit'])}</code> · registry inventory completeness: <strong>NO</strong>.</p></div>
</section>
<section class="section">
  <h2>Download the existing file for research only</h2>
  <p>The file is not a newly generated submission and has no upload clearance. Do not paste the historical name or note into a competition form.</p>
  <p><a class="research-download" download href="downloads/{esc(sub['research_tif'])}">Download research GeoTIFF</a>
  <a class="research-download" download href="downloads/{esc(sub['research_zip'])}">Download single-TIFF ZIP (research only)</a>
  <a class="research-download" href="data/h91_lattice_reaudit_20261024.json">Machine-readable re-audit</a>
  <a class="research-download" href="data/run_card.json">Corrected H91 run card</a></p>
  <table class="audit-table"><tbody>
    <tr><th>Candidate ID</th><td><code>{esc(sub['candidate_id'])}</code></td></tr>
    <tr><th>GeoTIFF SHA-256</th><td class="audit-mono">{esc(sub['sha256_tif'])}</td></tr>
    <tr><th>Size / emitted dots</th><td>{sub['bytes_tif']:,} bytes / {sub['n_dots']:,} dots</td></tr>
    <tr><th>Historical form name</th><td><code>{esc(sub['submission_name'])}</code> — traceability only; do not submit</td></tr>
    <tr><th>Historical note</th><td><code>{esc(old_note)}</code> ({sub['submission_note_length']}/140 characters) — traceability only; do not submit</td></tr>
  </tbody></table>
</section>
<section class="section">
  <h2>What the historical holdout number means</h2>
  <div class="grid">
    <article class="card"><span class="eyebrow">HOLDOUT-DTI · NOT ORGANIZER-CONFIRMED</span><div class="number">{holdout['score']:.6f}</div><p>95% CI [{holdout['ci_95'][0]:.6f}, {holdout['ci_95'][1]:.6f}]<br>{holdout['n_withheld_positives']:,} withheld positives</p><p class="small-note">Evaluator: <code>{esc(holdout['evaluator_version'])}</code></p></article>
    <article class="card"><span class="eyebrow">COMPARABILITY</span><p>{esc(holdout['comparability'])}</p><p class="small-note">A holdout estimate is not a leaderboard receipt, projected score, or authorization to submit.</p></article>
    <article class="card"><span class="eyebrow">LOCAL FILE VALIDATION</span><div class="number">{sum(bool(v) for v in checks.values())}/{len(checks)}</div><p>Shared-template format/range checks passed. This validates bytes and grid only; it does not establish novelty or organizer acceptance.</p></article>
  </div>
  <h3>On-disk checks</h3><div class="table-scroll"><table class="audit-table"><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{check_rows}</tbody></table></div>
  <p>Grid: {esc(local['crs'])}, {local['shape'][0]} × {local['shape'][1]}, {esc(local['dtype'])}, one band, transform <code>{esc(local['transform'])}</code>; values [{local['min']}, {local['max']}], {local['finite_pixels']:,} finite pixels. Mapped catalogue positives: {local['catalogue_positive_pixels']}.</p>
</section>
<section class="section">
  <h2>How the previous uniqueness claim failed</h2>
  <ul><li>The former H91 checker switched to symmetric F1 when a registry raster had more than 1.5 times as many positives as the candidate. That exception is not in the literal protocol.</li>
  <li>Its default paths omitted <code>data/fleet_registry</code>, where the pinned lattice witness resides.</li>
  <li>Its surface rank check sampled every fifth flattened footprint value. No complete, exact surface-correlation result against the lattice exists because the H91 continuous surface was not retained.</li>
  <li>The old 20-raster summary is retained as a partial diagnostic, not a uniqueness clearance. The re-audit compared the actual stored H91 TIFF to the immutable lattice bytes and found a directed overlap of {100*witness['directed_overlap']:.4f}%.</li></ul>
  <p>Shared module: <code>vendor/gems57/uniqueness.py</code>, restored byte-for-byte from <code>GEMSDOE78@30f1ab9400f92036b0bc613425f1b5b6046f3897</code>, Git blob <code>478c9001dc9c323cd50ba820f53c71dc2f80f221</code>. The exact file hash is listed in <code>registry/template_pin.json</code>.</p>
</section>
<section class="section"><h2>Evidence and limitations</h2>
  <ul><li><a href="data/h91_lattice_reaudit_20261024.json">Machine-readable re-audit evidence</a> and <a href="data/registry_uniqueness.json">registry summary</a>.</li>
  <li>The lattice comes from a pinned public sibling-repository mirror. Its hash proves identity to that source commit, not official organizer provenance or distribution permission.</li>
  <li>No official competition page, leaderboard, rules PDF, submission form, weekly allowance, or receipt was fetched in this review.</li>
  <li>No new geological experiments, holdout evaluations, submission slots, or candidate rasters were created during this re-audit.</li></ul>
</section>'''


def _guide_body(card: dict) -> str:
    sub = card["submission"]
    witness = card["registry_uniqueness"]["direct_lattice_witness"]
    return f'''<section class="hero"><div><span class="eyebrow">H91 STATUS · RESEARCH ONLY</span><h1>Do not submit this file.</h1><p class="lead">The existing H91 GeoTIFF passes local format checks but fails the literal duplicate rule.</p></div>
  <div class="audit-flag"><strong>OK TO DOWNLOAD FOR RESEARCH: YES</strong><br><strong>OK TO SUBMIT: NO</strong><p>Verdict: <strong>DUPLICATE</strong>. {witness['candidate_dots_within_3px']:,}/{witness['candidate_dots']:,} dots ({100*witness['directed_overlap']:.4f}%) overlap the pinned lattice within 3 px; the limit is &gt;70%.</p></div>
</section>
<section class="section"><h2>Current status</h2><p>There is no approved H91 submission. A format PASS does not undo a duplicate, establish a comparable holdout best, confirm a method lane, or substitute for an organizer receipt. The H91 number is a historical <strong>HOLDOUT-DTI</strong> from <code>{esc(card['scores']['primary_holdout']['evaluator_version'])}</code>, not an organizer score.</p>
<p><a class="research-download" href="h91-ddvtc.html">Read the full H91 audit</a> <a class="research-download" href="data/run_card.json">Open the machine-readable run card</a></p></section>
<section class="section"><h2>Process for a future, separately cleared candidate</h2>
<ol><li>Read the current project README and the assigned method paragraph. If no single lane is recorded, do not launch an experiment.</li>
<li>Use the pinned shared feature stack, holdout evaluator, spatial-fold utilities, and submission writer. Test each feature alone; any AUC above 0.90 is leakage until proven otherwise.</li>
<li>Hide whole fault components, buffer training from withheld segments, mask visible catalogue pixels exactly, and compute pooled HOLDOUT-DTI with the specified 300 m triangular kernel. Record evaluator, withheld-positive count, and 95% CI.</li>
<li>Run the literal registry checks on the continuous surface and the final candidate dots using a complete, hash-verified inventory. Stop on rank correlation &gt;0.90 or directed 3-pixel dot overlap &gt;70%; an incomplete scan is not a pass.</li>
<li>Re-read the written TIFF and ZIP; check the exact sample grid, one float32 band, finite [0,1] values and catalogue/footprint constraints. Format validity is not science or organizer acceptance.</li>
<li>Use a file only if the current run card explicitly says <strong>OK TO SUBMIT</strong>, every automated gate is true, and a separate selector receipt confirms current allowance. Verify the file SHA-256 before any account action.</li>
<li>After an actual organizer receipt, label its score <strong>ORGANIZER-CONFIRMED</strong> and retain the receipt, date, and file hash. Never present a projection as a score.</li></ol>
</section>
<section class="section"><h2>About the range error</h2><p>The historical H91 TIFF is one float32 band on the pinned EPSG:32611 grid, all values finite and within [0,1]. This local check does not prove why a prior organizer upload reported “Predicted values must be in range [0, 1]” and does not guarantee portal acceptance. No organizer form was accessible or exercised here.</p></section>
<section class="section"><h2>Reported leaderboard figures</h2><p>The repository has a user-reported <code>0.2778</code> comparison, but no organizer receipt or live leaderboard page was fetched during this review. Under the DTI form used by the local shared metric, unmatched prediction mass contributes false-positive cost; pruning redundant mass can plausibly help, but the files available here do not establish why a live entry scored as reported. This explanation is a mechanism hypothesis, not a confirmed causal result or score projection.</p><p>The H91 <code>0.174030</code> is a HOLDOUT-DTI estimate under its own evaluator and is not directly comparable to the current shared-template CED result. No actual score receipt exists for H91.</p></section>
<section class="section"><h2>Research download (not upload-cleared)</h2><p><a class="research-download" download href="downloads/{esc(sub['research_tif'])}">Download H91 GeoTIFF for research</a> <a class="research-download" download href="downloads/{esc(sub['research_zip'])}">Download H91 ZIP for research</a></p><p class="small-note">SHA-256: <code class="audit-mono">{esc(sub['sha256_tif'])}</code>. Do not upload this file.</p></section>'''


def render() -> None:
    card, audit, _registry = _load()
    DATA.mkdir(parents=True, exist_ok=True)
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DATA / "run_card.json").write_text(json.dumps(card, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (DATA / "run_card.js").write_text(
        "window.GEMS91_RUN_CARD = " + json.dumps(card, separators=(",", ":"), allow_nan=False) + ";\n",
        encoding="utf-8",
    )
    (DATA / "h91_lattice_reaudit_20261024.json").write_text(
        json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    registry = json.loads((ROOT / "evidence/registry_uniqueness.json").read_text(encoding="utf-8"))
    (DATA / "registry_uniqueness.json").write_text(
        json.dumps(registry, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    (DOCS / "h91-ddvtc.html").write_text(shell("H91 audit — not approved to submit", _audit_body(card, audit)), encoding="utf-8")
    (DOCS / "h91-executive-summary.html").write_text(shell("H91 research guide — do not submit", _guide_body(card)), encoding="utf-8")
    print("Rendered H91 research-only pages: download permitted for research; submission explicitly denied.")


if __name__ == "__main__":
    render()
