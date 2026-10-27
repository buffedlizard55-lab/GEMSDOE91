#!/usr/bin/env python3
"""Render the START HERE executive summary to root index.html (the GitHub Pages entry point).

Every number is read from disk at render time:
  - evidence/nine-site-leader-check.json   byte-level check (scripts/verify_nine_site_leaders.py):
                                           SHA-256, format, 3-px dot overlap, pairwise
  - docs/run-card-S22-XB.json, run-card-S18-UNIQUE.json, run-card-S20-LFI.json
                                           holdout (HOLDOUT-DTI), gates, projections, submission identity
  - evidence/public-leaderboard-2026-10-27.json   public leaderboard observation (dated)

It never writes a score. User-supplied scores are labelled USER CLAIM; surrogate outputs are labelled
PROJECTION; catalogue-recovery numbers are labelled HOLDOUT-DTI.
Usage: python3 scripts/render_start_here.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NINE = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
        "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
# Best score per site as supplied in the prompt. USER CLAIM only; no organizer receipt exists for any of them.
USER_CLAIM = {"GEMSDOE24": "0.2477", "GEMSDOE25": "0.2600", "GEMSDOE27": "0.2449",
              "GEMSDOE28": "0.2710", "GEMSDOE30": "0.2600", "GEMSDOE31": "0.2708",
              "GEMSDOE32": "0.2778", "GEMSDOE33": "0.2632", "GEMSDOE36": "0.2750"}
ORDER = sorted(NINE, key=lambda s: -float(USER_CLAIM[s]))


def e(x) -> str:
    return html.escape(str(x))


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def load(rel: str):
    return json.loads((ROOT / rel).read_text())


def cand_key(leaders: dict, needle: str) -> str:
    hits = [k for k in leaders["files"] if k.startswith("CANDIDATE:") and needle in k]
    if len(hits) != 1:
        raise SystemExit(f"candidate {needle!r} not found exactly once in leader check")
    return hits[0]


def max_vs_nine(leaders: dict, key: str) -> float:
    return max(leaders["overlap_pairs"][f"{key} -> {s}"] for s in NINE)


def main() -> int:
    leaders = load("evidence/nine-site-leader-check.json")
    board = load("evidence/public-leaderboard-2026-10-27.json")
    xb = load("docs/run-card-S22-XB.json")
    s18 = load("docs/run-card-S18-UNIQUE.json")
    lfi = load("docs/run-card-S20-LFI.json")

    ref = leaders["files"]["GEMSDOE32"]
    for k, f in leaders["files"].items():
        if f["crs"] != "EPSG:32611" or f["shape"] != [3730, 3292] or f["transform"] != ref["transform"]:
            raise SystemExit(f"grid mismatch: {k}")
        if not f["in_0_1"] or f["dtype"] != "float32":
            raise SystemExit(f"value-range/dtype failure: {k}")

    xb_key = cand_key(leaders, "gems91-s22-xbreed")
    s18_key = cand_key(leaders, "gems91-S18-UNIQUE")
    lfi_key = cand_key(leaders, "gems91-s20-lfi")
    xb_f, s18_f, lfi_f = leaders["files"][xb_key], leaders["files"][s18_key], leaders["files"][lfi_key]

    # --- shared numbers, all read from the cards ---------------------------------
    xb_h = xb["holdout"]
    xb_proj = xb["lfi_projection"]["all"]["S22-XB (this file)"]["r10"]
    xb_loso = xb_proj["loso_rmse"]
    xb_g4 = xb["gates"]["G4_holdout_paired"]["paired_C_minus_A_capped_celf"]
    xb_r0_proj = xb["lfi_projection"]["all"]["GEMSDOE32 R0 (USER-REPORTED 0.2778)"]["r10"]["projected"]
    s18_h = s18["holdout"]
    s18_uniq = s18["registry_uniqueness"]
    lfi_h = lfi["evidence"]["holdout_dti_hide_v2"]["candidate"]
    lfi_proj = lfi["evidence"]["projection_G4"]["ridge1"]
    lfi_proj10 = lfi["evidence"]["projection_G4"]["ridge10"]
    lfi_loso = lfi["evidence"]["surrogate_E1"]["loso_rmse"]
    lfi_val = lfi["evidence"]["instrument_validity_E2"]
    lb_top = board["rows"][0]["best_public_dw_tversky"]
    lb22 = next(r for r in board["rows"] if r["rank"] == 22)["best_public_dw_tversky"]

    # --- rows -------------------------------------------------------------------
    cand_rows = f"""
<tr class="hl"><td><strong>S22-XB</strong><br><span class="small">the only candidate that passes uniqueness and has a clean format</span></td>
<td><code>{e(xb['submission']['tif_file'].split('/')[-1])}</code><br><a href="{e(xb['submission']['tif_file'])}">Download GeoTIFF</a> · <a href="{e(xb['submission']['zip_file'])}">ZIP</a><br><span class="small">SHA-256 <code>{e(xb['submission']['sha256'][:16])}…</code> · {xb_f['dots']:,} dots</span></td>
<td>No user score (new file)</td>
<td>PROJECTION <strong>{xb_proj['projected']:.3f} ± {xb_loso:.3f}</strong> (model, not a score)<br><span class="small">HOLDOUT-DTI {xb_h['holdout_dti']:.4f} [{xb_h['ci95'][0]:.4f}, {xb_h['ci95'][1]:.4f}] · {xb_h['n_withheld_positives']:,} withheld positives · evaluator {e(xb_h['evaluator_version'])}</span></td>
<td><strong class="ok">YES</strong> · max 3-px overlap {pct(max_vs_nine(leaders, xb_key))} vs the nine (limit 70%)</td>
<td><span class="bad">NO</span> · fails G4 (holdout paired) and G5 (live projection)</td></tr>
<tr><td><strong>S18-UNIQUE</strong></td>
<td><code>{e(s18['submission_name'])}.tif</code><br><a href="docs/downloads/{e(s18['submission_name'])}.tif">Download GeoTIFF</a><br><span class="small">SHA-256 <code>{e(leaders['files'][s18_key]['sha256'][:16])}…</code> · {s18_f['dots']:,} dots</span></td>
<td>No user score</td>
<td>HOLDOUT-DTI {s18_h['dti']:.6f} [{s18_h['ci95'][0]:.6f}, {s18_h['ci95'][1]:.6f}]<br><span class="small">{s18_h['withheld_positive_pixels']:,} withheld positives · did not beat incumbent 0.066223</span></td>
<td><strong class="ok">YES</strong> · max 3-px overlap {pct(max_vs_nine(leaders, s18_key))} vs the nine · repo registry {pct(s18_uniq['dots_max_3px_overlap'])}</td>
<td><span class="bad">NO</span> · holdout far below the best; no slot spent</td></tr>
<tr><td><strong>S20-LFI</strong><br><span class="small">highest projection, but a duplicate</span></td>
<td><code>{e(lfi['submission']['name'])}.tif</code><br><a href="{e(lfi['submission']['file'])}">Download GeoTIFF</a><br><span class="small">SHA-256 <code>{e(lfi['submission']['sha256'][:16])}…</code> · {lfi_f['dots']:,} dots</span></td>
<td>No user score</td>
<td>PROJECTION {lfi_proj['model_cand']:.3f} (ridge 1) / {lfi_proj10['model_cand']:.3f} (ridge 10), LOSO RMSE {lfi_loso:.3f} (model, not a score)<br><span class="small">HOLDOUT-DTI {lfi_h['dti']:.6f} [{lfi_h['ci95'][0]:.6f}, {lfi_h['ci95'][1]:.6f}] · {lfi_h['withheld_positive_pixels']:,} withheld positives</span></td>
<td><strong class="bad">NO</strong> · {pct(max_vs_nine(leaders, lfi_key))} of its dots lie within 3 px of a leader (limit 70%). Its own card says UNIQUE; this check does not.</td>
<td><span class="bad">NOT OK TO SUBMIT</span> · G4 failed; holdout near zero</td></tr>"""

    leader_rows = "".join(f"""<tr><td><strong>{s}</strong></td>
<td><code>{e(leaders['files'][s]['repo_path'].split('/')[-1])}</code><br><a href="https://github.com/buffedlizard55-lab/{s}/raw/main/{e(leaders['files'][s]['repo_path'])}">Download from the {s} repo</a><br><span class="small">SHA-256 <code>{e(leaders['files'][s]['sha256'][:16])}…</code></span></td>
<td>{USER_CLAIM[s]}<br><span class="small">USER CLAIM · not ORGANIZER-CONFIRMED</span></td>
<td>Not estimable (no organizer receipt)</td>
<td><strong class="bad">NO</strong> · {pct(leaders['max_overlap_into_any_other_leader'][s])} of its dots lie within 3 px of another leader</td>
<td><span class="bad">NOT OK TO SUBMIT</span> · duplicate of the nine-site family</td></tr>""" for s in ORDER)

    board_items = "".join(f"<li>{e(x)}</li>" for x in board["notes"])

    body = f"""
<header class="hero"><p class="eyebrow">GEMSDOE91 · START HERE · evidence checked {e(board['retrieved_utc'])}</p>
<h1>Download the unique file. Do not submit it yet.</h1>
<p class="lead">The best unique file in this repository is <strong>S22-XB</strong>. It is distinct from the nine top GEMSDOE sites, but it has <strong>not</strong> passed the project's holdout and projection gates, so it is not cleared for submission. No file in this repository is cleared.</p>
<div class="verdict"><div><span>OK TO DOWNLOAD: YES</span><strong class="ok">research file only</strong></div>
<div><span>OK TO SUBMIT: NO</span><strong class="bad">no file cleared</strong></div>
<div><span>Weekly slots used by this session</span><strong>0</strong></div></div>
<p><a class="btn" href="{e(xb['submission']['tif_file'])}">Download the S22-XB GeoTIFF</a> <a class="btn alt" href="docs/executive-summary.html">Nine-site detail</a> <a class="btn alt" href="docs/run-card-S22-XB.json">Run card</a></p>
</header>

<section><h2>1 · Which file to download, and may it be submitted?</h2>
<table><thead><tr><th>Site</th><th>File to download</th><th>Reported score</th><th>Estimated leaderboard score</th><th>Unique vs the other GEMSDOE sites?</th><th>OK to submit?</th></tr></thead>
<tbody>{cand_rows}{leader_rows}</tbody></table>
<p class="small">Format check for every row, computed from the bytes: EPSG:32611, 3,730 × 3,292, float32, the same geotransform as the nine leaders, all finite values in [0, 1]. Uniqueness uses the project's rule (more than 70% of a file's dots within 3 px of another file's dots = duplicate). A projection or holdout value is never a leaderboard score.</p>
</section>

<section><h2>2 · Unique name and note for the submission form</h2>
<dl class="meta"><dt>File name</dt><dd><code>{e(xb['submission']['name'])}</code></dd>
<dt>Note ({len(xb['submission']['note'])}/140)</dt><dd><code>{e(xb['submission']['note'])}</code></dd>
<dt>When to upload</dt><dd>Only after G4 and G5 pass. Until then, keep it as research.</dd></dl></section>

<section><h2>3 · Why S22-XB is not cleared</h2>
<ul>
<li><strong>G4 holdout (fails):</strong> the shipped capped recipe is {xb_g4['delta']:+.4f} against the uncapped baseline (95% CI {xb_g4['ci95'][0]:+.4f} to {xb_g4['ci95'][1]:+.4f}).</li>
<li><strong>G5 live projection (fails):</strong> the same surrogate projects the GEMSDOE32 R0 file at {xb_r0_proj:.3f}, while the file's own projection is {xb_proj['projected']:.3f}. Both are model outputs, not scores.</li>
<li><strong>Uniqueness (passes):</strong> max 3-px overlap {pct(xb['uniqueness']['dots_max_3px_overlap_competitive'])} against {xb['uniqueness']['n_competitive_non_blanket_rasters']} competitive rasters in the repo's registry screen; {pct(max_vs_nine(leaders, xb_key))} against the nine leaders in the direct check.</li>
</ul></section>

<section><h2>4 · Why the nine top sites are one family</h2>
<p>Pairwise measurement of the exact leader bytes: every leader has at least {pct(min(leaders['max_overlap_into_any_other_leader'][s] for s in NINE))} of its dots within 3 px of another leader's dots. None of the nine files is unique under the 70% rule. The best-scoring nine are one submission family in different wrappers, not nine independent methods.</p></section>

<section><h2>5 · Public leaderboard (fetched {e(board['retrieved_utc'])})</h2>
<p>Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">DrivenData leaderboard</a>. #1 = {lb_top:.4f}; #22 = {lb22:.4f}. These are public values, not organizer receipts for any TIFF in this repository.</p>
<ul>{board_items}</ul></section>

<section><h2>6 · Irregularities flagged for review</h2>
<ul>
<li>The prompt gives #1 as 0.4413 and also 0.3195 in different places. The repo recorded 0.4437 on 2026-10-26. The DrivenData page fetched on {e(board['retrieved_utc'])} shows {lb_top:.4f}. Use the dated fetch, and re-fetch before you quote it.</li>
<li>The nine leader scores are user claims. No organizer receipt links a score to a file, so no leaderboard estimate can be calibrated for any of them.</li>
<li>S20-LFI's card says UNIQUE, but this direct check finds {pct(max_vs_nine(leaders, lfi_key))} overlap with a leader, above the 70% limit. The card's registry scope does not explain this here; the cause is not established. Treat its uniqueness claim as disproved until it is re-run against the nine leaders.</li>
<li>The holdout measures recovery of known catalogue faults. The repo's instrument-validity check (S20-LFI card) finds Spearman {lfi_val['spearman_hide_v2_vs_live']:+.3f} between the holdout and the {lfi_val['n_anchors']} live scores, and marks it "valid as live proxy: {str(lfi_val['hide_v2_valid_as_live_proxy']).lower()}". The holdout is therefore not a reliable live proxy.</li>
<li>The projection surrogate is fitted to those same {lfi_val['n_anchors']} user-supplied live scores. Its leave-one-site-out Spearman ({lfi_val['spearman_lfi_loso_vs_live']:+.3f}) is an in-sample-family check, not an independent validation on new leaderboard data.</li>
<li>Projections come from a model fitted to the user-supplied live scores. They are never scores.</li>
</ul></section>

<footer class="small">Research, not a leaderboard prediction. No automatic uploads. No credentials stored.
Machine evidence: <a href="evidence/nine-site-leader-check.json">nine-site check</a> · <a href="evidence/public-leaderboard-2026-10-27.json">leaderboard fetch</a> · <a href="https://github.com/buffedlizard55-lab/GEMSDOE91">Source repo</a></footer>
"""
    css = """body{margin:0;font:16px/1.6 system-ui,Segoe UI,sans-serif;color:#17312e;background:#f6f6f0}
main{max-width:1120px;margin:auto;padding:28px 22px}section{background:#fff;border:1px solid #d7dfd8;border-radius:10px;padding:22px 24px;margin:18px 0}
h1{font-size:34px;line-height:1.15;margin:8px 0 14px}h2{font-size:21px;margin:0 0 12px}.eyebrow{font:700 12px/1 system-ui;letter-spacing:2px;text-transform:uppercase;color:#17644e}
.lead{max-width:840px;font-size:17px;color:#40524e}.verdict{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}
.verdict div{background:#fff;border:1px solid #d7dfd8;border-radius:8px;padding:14px}.verdict span{display:block;font-size:12px;color:#596c68;text-transform:uppercase;letter-spacing:1px}
.verdict strong{font-size:17px}.ok{color:#17644e}.bad{color:#9c3d25}.btn{display:inline-block;background:#17312e;color:#fff;text-decoration:none;padding:12px 16px;border-radius:6px;margin:4px 6px 4px 0;font-weight:650}
.btn.alt{background:#e7f0e8;color:#17312e}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;vertical-align:top;padding:9px;border-bottom:1px solid #d7dfd8}
th{background:#edf1ea;font-size:11px;text-transform:uppercase;letter-spacing:.5px}tr.hl td{background:#e9f6ee}.small{font-size:12px;color:#596c68}code{font:12px ui-monospace,monospace;overflow-wrap:anywhere}
.meta{display:grid;grid-template-columns:150px 1fr;gap:8px}.meta dt{color:#596c68}.meta dd{margin:0;overflow-wrap:anywhere}footer{color:#596c68;padding:10px 4px}
@media(max-width:800px){.verdict{grid-template-columns:1fr}table{font-size:12px}}"""
    page = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>START HERE · GEMSDOE91 submission decision</title><style>{css}</style></head><body><main>{body}</main></body></html>\n')
    (ROOT / "index.html").write_text(page)
    print("wrote index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
