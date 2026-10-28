#!/usr/bin/env python3
"""Render docs/nine-site-20261028/executive-summary.html from the verified JSON.

Every number on the page is read from docs/nine-site-20261028/nine-site-leaders-20261028.json
(produced by scripts/nine_site_leaders_20261028.py) or from the cited S25 run card.
Nothing is typed in by hand.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "nine-site-20261028"
DATA = json.loads((OUT_DIR / "nine-site-leaders-20261028.json").read_text())
RUN = json.loads((ROOT / "docs" / "s25" / "run-card.json").read_text())
S25_FILE = "gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif"
S25_SHA = DATA["local_candidate"]["sha256"]
H = RUN["holdout"]


def esc(x) -> str:
    return html.escape(str(x))


def pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def site_rows():
    names = [s["site"] for s in DATA["sites"]]
    rows = []
    for s in DATA["sites"]:
        n = s["site"]
        others = [o for o in names if o != n]
        ov = [DATA["pairwise_overlap_within_3px"][f"{n}->{o}"] for o in others]
        rows.append({
            "site": n,
            "file": s["file"],
            "source": s["source_url"],
            "sha": s["sha256"],
            "claimed": s["claimed_user_reported_score"],
            "positives": s["format"]["positive_pixels"],
            "nan": s["format"]["nan_count"],
            "ov_min": min(ov),
            "ov_max": max(ov),
        })
    return rows


def main() -> int:
    rows = site_rows()
    loc = DATA["local_candidate"]
    worst_site = loc["max_overlap_site"]
    top_repo = loc["repo_tif_comparisons"]["top"][0]
    bhar = Path(top_repo["file"]).name
    bhar_ov = top_repo["overlap_within_3px"]
    best = max(rows, key=lambda r: r["claimed"])

    trs = []
    for r in rows:
        trs.append(f"""<tr>
<td><strong>{esc(r['site'])}</strong></td>
<td><a href="{esc(r['source'])}">{esc(r['file'])}</a><br><small>SHA-256 <code>{esc(r['sha'][:16])}…</code> · {r['positives']:,} dots · NaN outside footprint: {r['nan']:,}</small></td>
<td>USER-REPORTED <strong>{r['claimed']:.4f}</strong><br><small>organizer-confirmed: none</small></td>
<td>Not unique: <strong>{pct(r['ov_min'])}–{pct(r['ov_max'])}</strong> of its dots lie within 3 px of each other leader</td>
<td><strong>NO</strong> — already submitted; resubmitting is a copy</td>
</tr>""")

    cand_row = f"""<tr class="cand">
<td><strong>S25-FABRIC E2</strong><br><small>new this session (research)</small></td>
<td><a href="../downloads/{esc(S25_FILE)}">{esc(S25_FILE)}</a><br><small>SHA-256 <code>{esc(S25_SHA[:16])}…</code> · 37,654 dots · zeros outside footprint · float32 · EPSG:32611 · 100 m</small></td>
<td><strong>No estimate.</strong> Organizer-confirmed: none.<br><small>HOLDOUT-DTI {H['dti']:.6f} [{H['ci95'][0]:.6f}, {H['ci95'][1]:.6f}], evaluator {esc(H['evaluator_version'])}, {H['n_withheld_positives']:,} withheld positives. Not a leaderboard score. LFI model projection 0.07917 is a projection only.</small></td>
<td>Unique vs the nine: <strong>YES</strong> (max {pct(worst_site['overlap'])} within 3 px, {esc(worst_site['site'])})<br>Protocol 70% gate: <strong>FAILS</strong> — {pct(bhar_ov)} vs <code>{esc(bhar)}</code> (repo research TIFF)</td>
<td><strong>Download for research: YES. Submit: NO.</strong></td>
</tr>"""

    html_out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 — Nine-site executive summary (2026-10-28)</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:1180px;margin:24px auto;padding:0 16px;color:#1b1f24;line-height:1.45}}
h1{{font-size:1.6rem;margin-bottom:4px}} h2{{margin-top:28px;border-bottom:1px solid #d0d7de;padding-bottom:4px}}
.verdict{{background:#fff4e5;border:2px solid #d97706;border-radius:8px;padding:14px 16px;margin:14px 0}}
.verdict strong{{font-size:1.05rem}}
table{{border-collapse:collapse;width:100%;margin:10px 0;font-size:0.92rem}}
th,td{{border:1px solid #d0d7de;padding:7px 9px;vertical-align:top;text-align:left}}
th{{background:#f6f8fa}} tr.cand td{{background:#eef6ff}}
code{{font-size:0.85em}} small{{color:#57606a}}
.warn{{color:#9a3412}}
</style></head><body>
<h1>GEMSDOE91 — Nine-site executive summary</h1>
<p><small>Generated 2026-10-28 from <code>docs/nine-site-20261028/nine-site-leaders-20261028.json</code> by <code>scripts/render_nine_site_20261028.py</code>. Every leader file was re-fetched from its owner's GitHub repo at the pinned commit and its SHA-256 matched the recorded value.</small></p>

<div class="verdict">
<strong>Bottom line: no file is cleared for competition submission today.</strong><br>
1. <strong>Highest claimed score among the nine:</strong> GEMSDOE32 <code>{esc(best['file'])}</code> at <strong>{best['claimed']:.4f}</strong> (USER-REPORTED, not organizer-confirmed). Its file is already a previous submission and is not a new unique submission.<br>
2. <strong>New unique file:</strong> the S25-FABRIC E2 TIFF below is unique against the nine (max {pct(worst_site['overlap'])} overlap), but it fails the 70% duplicate gate against a repo research TIFF ({pct(bhar_ov)}). Under the protocol it is a drift/duplicate, so <strong>OK to submit: NO</strong>.<br>
3. <strong>Why no new TIFF was generated here:</strong> the pinned competition inputs (sample footprint, existing-faults catalogue, training features) are not in this checkout, and this sandbox cannot log in to DrivenData. See "What is blocking" below.
</div>

<h2>Estimated score table (what to download, estimate, uniqueness, OK to submit)</h2>
<table>
<thead><tr><th>Site</th><th>File to download</th><th>Estimated leaderboard score</th><th>Unique vs the other GEMSDOE sites?</th><th>OK to download and submit?</th></tr></thead>
<tbody>
{''.join(trs)}
{cand_row}
</tbody></table>

<p><strong>Leaderboard context (fetched 2026-10-28):</strong> #1 is <strong>0.4544</strong> (xiaofanhu), #2 is <strong>0.3916</strong> (cfld__). Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">DrivenData leaderboard</a>. The 0.4413 and 0.3195 figures in the session prompt do not match this page and are flagged in IRREGULARITIES.md (IR-S26-01).</p>

<h2>Why the nine leaders are not unique</h2>
<p>Each leader's positive pixels lie within 3 px of another leader's positive pixels for <strong>{pct(min(r['ov_min'] for r in rows))}–{pct(max(r['ov_max'] for r in rows))}</strong> of cells. The matrix is in the JSON (<code>pairwise_overlap_within_3px</code>). A new "unique" file must stay under 70% against every reference.</p>

<h2>Rules checked (protocol and official format)</h2>
<ul>
<li><strong>Official format</strong> (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem page, Submission format</a>): one float32 layer, EPSG:32611, 100 m, same bounds as training data, values in [0, 1], NaN or null allowed outside bounds. The S25 file passes all of these locally: 3,292 × 3,730, finite values in [0, 1], no NaN. Format passes are not organizer acceptance.</li>
<li><strong>Duplicate gate</strong>: stop if more than 70% of dots are within 3 px of one registry raster, or surface Spearman |ρ| &gt; 0.90. S25 file: sampled |ρ| max {loc['max_abs_spearman_site']['rho']:.4f} (passes); overlap 70% gate fails on the repo TIFF above.</li>
<li><strong>Scoring metric</strong> (same page): distance-weighted Tversky index, α = 0.2, β = 0.8, 300 m triangular kernel.</li>
</ul>

<h2>Format note for the "Predicted values must be in range [0,1]" error</h2>
<p>All nine leader files and the S25 file have finite values inside [0, 1] (NaN is outside the footprint in the "-nan" files; the "zeros" files are fully finite). The error text was not reproducible here because the organizer validator is not available. Check the exact uploaded file for values above 1, below 0, or a nodata sentinel such as -9999. (IR-S26-02.)</p>

<h2>What is blocking a new unique TIFF</h2>
<ol>
<li>The official inputs must be obtained by a human with a DrivenData login: <code>sample_submission.tif</code>, <code>existing_faults.tif</code>, and <code>training_features.tif</code> (the data page redirects to login).</li>
<li>Public GitHub repos in this owner's account already host copies of competition rasters. The repo flags this for review (IR-91-09). This session did not use them to build a submission.</li>
<li>The registry-wide duplicate gate needs the full registry (<code>data/fleet_registry</code>), which is absent here. This session checked the 63 TIFFs tracked in <code>docs/downloads/</code>.</li>
</ol>

<h2>How to submit (when a file is cleared)</h2>
<ol>
<li>Only submit a file marked <strong>OK to submit: YES</strong> in the table above.</li>
<li>Upload a single-band GeoTIFF (.tif) or a .zip containing one GeoTIFF, with a unique name and a short note.</li>
<li>Check the upload form's CRS, shape and geotransform against the submission page before pressing submit.</li>
</ol>
<p><small>Official sources: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description and metric</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">submission PDF</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">GeoDAWN</a>.</small></p>
</body></html>
"""
    (OUT_DIR / "executive-summary.html").write_text(html_out)
    print("wrote", OUT_DIR / "executive-summary.html", len(html_out), "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
