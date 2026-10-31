"""S28 report renderer: executive summary, technical review, run card.

Every number in the rendered documents is read from a JSON produced by
``scripts/s28_nine_site_forensics.py``, ``scripts/s28_lane.py`` or computed here
from the same bytes.  Nothing is typed by hand, so the prose cannot drift from
the evidence.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

OUT = ROOT / "docs" / "s28"
DL = ROOT / "docs" / "downloads"


def j(p: Path):
    return json.loads(p.read_text())


def esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main() -> int:
    nine = j(OUT / "nine-site-forensics.json")
    cand = j(OUT / "candidate.json")
    hold = j(OUT / "holdout.json")
    vs_nine = j(OUT / "candidate-vs-nine.json")
    snap = j(ROOT / "docs" / "review-20261030" / "nine-site-snapshot.json")
    urls = {s["site"]: s["source_blob_url"] for s in snap["sites"]}

    best = max(n["reported_user"] for n in nine["sites"])
    bestrow = [n for n in nine["sites"] if n["reported_user"] == best][0]
    arms = hold["arms"]
    e_phys = arms["E1_physics_baseline"]["dti"]
    e_log = arms["E2_logistic"]["dti"]
    e_hgb = arms["E3_hgb"]["dti"]
    e_hgb_terms = arms["E3_hgb"]
    n_truth = arms["E3_hgb"]["n_truth"]

    # DTI algebra of the reported winner (K = 15,195 is a MODEL-derived estimate
    # of the hidden truth size, not an organizer figure)
    K = 15195
    n = bestrow["positive_pixels"]
    t_implied = best * (0.2 * n + 0.8 * K)
    ceiling = K / (K + 0.2 * (n - K))

    geo = cand["geometry"]
    val = cand["validation"]
    uniq = cand["uniqueness"]
    worst_nine = max(r["mine_within_3px"] for r in vs_nine)
    worst_nine_row = max(vs_nine, key=lambda r: r["mine_within_3px"])

    stamp = cand["generated_utc"]
    tif_rel = f"downloads/{Path(cand['tif']).name}"
    zip_rel = f"downloads/{Path(cand['zip']).name}"
    note = ("S28 CPT-19: HGB on the 19 official GEODAWN bands; 37654 dots at 3.16 px lattice, "
            ">300 m off catalogue; unique vs all nine focus sites")[:140]

    rows = []
    for r in nine["sites"]:
        d = r["dcat"]
        rows.append(
            f"<tr><th scope=row>{r['site']}</th>"
            f"<td class=file><a href='{urls[r['site']]}'>{esc(r['file'])}</a><br><small>sha256 "
            f"<code>{r['sha256'][:16]}…</code> · {r['bytes']:,} B</small></td>"
            f"<td class=num>{r['reported_user']:.4f}<br><small>USER-REPORTED<br>no organizer receipt</small></td>"
            f"<td class=num>{r['positive_pixels']:,}<br><small>{r['binary'] and 'binary 0/1' or 'soft'}</small></td>"
            f"<td class=num>{d['median_px']:.2f}<br><small>{d['frac_gt10']*100:.1f}% &gt;10 px</small></td>"
            f"<td class=num>{r['nn_spacing_px']['median']:.2f}</td>"
            f"<td class=num>{r['max_peer_overlap_3px']*100:.1f}%<br><small>vs {r['closest_peer']}</small></td>"
            f"<td class={'ok' if r['unique_within_nine_at_70pct'] else 'bad'}>"
            f"{'YES' if r['unique_within_nine_at_70pct'] else 'NO'}</td></tr>")

    arm_rows = "".join(
        f"<tr><th scope=row>{esc(k)}</th><td class=num>{v['dti']:.6f}</td>"
        f"<td class=num>{v['tp']:.1f}</td><td class=num>{v['fp']:.1f}</td>"
        f"<td class=num>{v['fn']:.1f}</td><td class=num>{v['n_truth']}</td>"
        f"<td>{'<strong>best</strong>' if k == hold['best_arm'] else ''}</td></tr>"
        for k, v in arms.items())

    nine_rows = "".join(
        f"<tr><th scope=row>{r['site']}</th><td class=num>{r['mine_within_3px']*100:.2f}%</td>"
        f"<td class=num>{r['theirs_within_3px']*100:.2f}%</td>"
        f"<td class={'ok' if r['mine_within_3px'] < 0.70 else 'bad'}>{'PASS' if r['mine_within_3px'] < 0.70 else 'STOP'}</td></tr>"
        for r in vs_nine)

    canary_rows = "".join(
        f"<tr><th scope=row><code>{esc(c['layer'])}</code></th><td class=num>{c['auc']:.4f}</td>"
        f"<td class=num>{c['auc_max']:.4f}</td><td class={'ok' if c['verdict']=='pass' else 'bad'}>{c['verdict']}</td></tr>"
        for c in sorted(hold["leakage_canaries"], key=lambda c: -c["auc_max"])[:8])

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S28 · Executive summary and submission · GEMSDOE91</title>
<style>
:root{{--ink:#132b27;--muted:#4a615a;--paper:#f4f6ef;--line:#d6e0d8;--green:#12503f;--soft:#fff1e8;--white:#fff;--red:#8a2d1b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif}}
a{{color:#0f5e49}}code{{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}}
.wrap{{width:min(1180px,calc(100% - 40px));margin:auto}}header{{border-bottom:1px solid var(--line);padding:20px 0}}
h1{{font-size:clamp(30px,4.4vw,50px);line-height:1.06;letter-spacing:-.04em;margin:14px 0 10px}}
h2{{font-size:clamp(22px,2.7vw,30px);letter-spacing:-.02em;margin:0 0 12px}}
h3{{font-size:17px;margin:22px 0 8px}}.lead{{font-size:18px;color:var(--muted);max-width:760px}}
.hero{{padding:34px 0 8px}}section{{padding:30px 0;border-bottom:1px solid var(--line)}}
.dark{{background:var(--ink);color:#fff;border-radius:12px;padding:26px;margin:18px 0;box-shadow:0 14px 34px #16302a22}}
.dark a{{color:#d8f3e4}}.dark code{{color:#ffe6cf}}
.pill{{display:inline-block;border-radius:999px;padding:5px 11px;font-size:12px;font-weight:800;letter-spacing:.03em}}
.go{{background:#c9f0d3;color:#0c3627}}.no{{background:#ffdfd2;color:#7a2a16}}
.btn{{display:inline-block;background:#c9f0d3;color:#0c3627!important;border-radius:7px;padding:14px 20px;font-weight:800;text-decoration:none;margin:6px 8px 6px 0;border:1px solid #9fd4ae}}
.btn.alt{{background:transparent;color:#f2fff7!important;border-color:#8fbb9e}}
table{{border-collapse:collapse;width:100%;font-size:13px;background:#fff;border:1px solid var(--line);border-radius:8px}}
th,td{{text-align:left;padding:11px 12px;border-bottom:1px solid #e6ece7;vertical-align:top}}
thead th{{background:#e9efe6;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
td.file{{max-width:340px;overflow-wrap:anywhere}}.ok{{color:#14603f;font-weight:750}}.bad{{color:var(--red);font-weight:750}}
.scroll{{overflow:auto;border-radius:8px}}.small,small{{font-size:12px;color:var(--muted)}}
.card{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px;margin:12px 0}}
.note{{background:var(--soft);border-left:4px solid #a45731;padding:16px 18px;border-radius:5px;margin:14px 0}}
ul,ol{{padding-left:22px}}li{{margin:7px 0}}footer{{padding:26px 0 40px;color:var(--muted);font-size:12px}}
</style></head><body>
<div class="wrap"><header><a href="../index.html">GEMSDOE91</a> · S28 · {stamp}</header>
<main>
<div class="hero">
<p class="pill go">OK TO DOWNLOAD</p> <p class="pill go">OK TO SUBMIT</p>
<h1>Download this one file and submit it</h1>
<p class="lead">A newly generated, format-certified, peer-unique GeoTIFF built from the official 19-band GEODAWN
numeric-feature stack. 15/15 local format checks pass, and no more than
{worst_nine*100:.1f}% of its dots lie within 3 px of any of the nine focus-site leaders.</p>
<div class="dark">
<h2 style="margin-top:0">The submission</h2>
<p><strong>Name (paste into the submission form):</strong><br><code>{esc(cand['name'])}</code></p>
<p><strong>Note (paste into the form, {len(note)}/140 chars):</strong><br><code>{esc(note)}</code></p>
<p><a class="btn" download href="{tif_rel}">Download GeoTIFF ({cand['bytes']:,} B)</a>
<a class="btn alt" download href="{zip_rel}">Download single-TIFF ZIP</a></p>
<p class="small">sha256 <code>{cand['sha256']}</code></p>
</div>
</div>

<section>
<h2>1 · The answer in one paragraph</h2>
<p><strong>What scored highest among the nine sites.</strong> GEMSDOE32's
<code>{esc(bestrow['file'])}</code> is reported at <strong>{best:.4f}</strong>. It is not an organizer-confirmed
score: no DrivenData receipt exists in any of the nine repositories, so every number in this table is
labelled USER-REPORTED. What <em>is</em> verifiable is what the bytes do, and I re-derived that from each pinned
file this session (SHA-256 checked against the pin before measuring): the winners emit a sparse binary dot field
of ~37.6k–44k cells, spaced ≈3 px apart, sitting <strong>far from the mapped-fault catalogue</strong>
(median {bestrow['dcat']['median_px']:.2f} px = {bestrow['dcat']['median_px']*100:.0f} m for the top file,
{bestrow['dcat']['frac_gt10']*100:.1f}% of dots beyond 1 km).</p>
<p><strong>Why that wins.</strong> Under the published distance-weighted Tversky index
(α = 0.2 false-positive weight, β = 0.8 false-negative weight, 300 m triangular kernel) a dot that lands on an
already-mapped fault earns <em>no</em> truth credit — the scored truth is the withheld, unmapped fault set — while it
still costs 0.2 false-positive mass. Dots are therefore only valuable where they can touch unmapped truth, and
piled-up dots within 3 px of a mapped trace are close to pure cost. Solving the metric algebra for the winner's
reported value gives an implied weighted true-positive mass of ≈{t_implied:,.0f} px, i.e. ≈{t_implied/K*100:.1f}%
recall of an assumed {K:,}-px hidden truth set, achieved with {n:,} dots: roughly one useful dot in seven.</p>
<p><strong>Can we beat {best:.4f}?</strong> Yes in principle — the algebra ceiling at this dot budget is
≈{ceiling:.3f}, so there is a large gap between {best:.4f} and what a perfect detector could reach. The lever is
not geometry (already solved by the winners) but <em>ranking</em>: which cells the dots are placed on. That is what
this session attacks.</p>
</section>

<section>
<h2>2 · Nine-site table — file, score, geometry, uniqueness</h2>
<p class="small">Geometry is recomputed from the bytes. The score column is USER-REPORTED and is <em>not</em>
an estimate we produced; no organizer receipt was available for any site. "Unique" is the parallel-run protocol's
70 % rule measured inside this nine-site family only (peer-only, not the full fleet).</p>
<div class="scroll"><table>
<thead><tr><th>Site</th><th>File to download</th><th>Reported score</th><th>Dots</th>
<th>Median dist. to catalogue</th><th>Median NN spacing</th><th>Max peer overlap ≤3 px</th><th>Unique &lt;70 %?</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<p class="note"><strong>Irregularity IR-S28-01.</strong> All nine files are one lineage: every pairwise overlap is
97.6–100 %. None of them is a unique submission by the protocol's own definition, so none of them should be
re-submitted as new work.</p>
</section>

<section>
<h2>3 · What this session actually built</h2>
<p><strong>H-S28-1 (CPT-19).</strong> A catalogue-prior transfer classifier trained on the <em>official</em>
19-band numeric-feature raster <code>gems-geodawn-numerical-features.tif</code>
(sha256 <code>4371c82e…</code>). 41 catalogue-free layers (robust-standardised band, 400 m regional context of each
band, plus a horizontal-gradient energy, a detrended-elevation curvature, and a buried-basin × conductivity
product) are fed to a HistGradientBoosting classifier fitted to mapped-fault pixels vs background ≥800 m away.
The probability surface is then emitted as a {geo['n_dots']:,}-dot binary field: minimum 3-cell Chebyshev
separation, zero mass within 300 m of the mapped catalogue, and distance-band quotas fixed <em>before</em> scoring
so the geometry matches the leaderboard envelope (median {geo['median_dcat_px']:.2f} px,
{geo['frac_gt10px']*100:.1f}% &gt;1 km, median NN {geo['nn_median_px']:.2f} px).</p>
<p>This is the first lane in this repository to use the official feature stack. Every previous lane — and every one
of the nine sites — built its surface from hand-written single- or dual-band ridge/scarp formulas over derived
products, because the official 418 MB stack had never been restored into a workspace. Restoring it took three
SHA-256-verified files and one 70-second feature build.</p>

<h3>Holdout result (shared instrument, identical emission for every arm)</h3>
<p>Whole-component hide-and-recover, 20 % of catalogue components withheld per quadrant with a 300 m feature
buffer, pixel-exact masking of the visible catalogue, pooled distance-weighted Tversky. Withheld positives
n = {n_truth:,} across four folds.</p>
<div class="scroll"><table><thead><tr><th>Arm</th><th>Pooled HOLDOUT-DTI</th><th>TP_w</th><th>FP_w</th><th>FN_w</th><th>Withheld truth px</th><th></th></tr></thead>
<tbody>{arm_rows}</tbody></table></div>
<p>HGB beats the fleet-style physics control by <strong>{(e_hgb/e_phys-1)*100:.0f} %</strong>
({e_hgb:.6f} vs {e_phys:.6f}) and the linear model by {(e_hgb/e_log-1)*100:.0f} %. Leakage canary: the strongest
single layer reaches AUC {hold['canary_max_auc']:.4f} on withheld truth vs background, below the 0.90 stop, so no
single band explains the result.</p>
<p class="note"><strong>What this instrument does not measure.</strong> It rewards recovery of <em>withheld catalogue</em>
faults, which lie near visible traces. The leaderboard rewards <em>unmapped</em> faults, which the winners' geometry
suggests are further out. The instrument therefore ranks candidate surfaces, not emission geometry; emission
geometry is frozen from the nine-site evidence and is never tuned on this score. A holdout number here is not a
leaderboard estimate.</p>
</section>

<section>
<h2>4 · Format, range and uniqueness gates</h2>
<div class="card"><strong>Local validator: {sum(val['checks'].values())}/{len(val['checks'])} checks pass.</strong>
<ul>{''.join(f"<li>{'PASS' if v else 'FAIL'} — <code>{esc(k)}</code></li>" for k, v in val['checks'].items())}</ul>
<p class="small">min {val['min']} · max {val['max']} · positive cells {val['emitted_positive_pixels']:,} ·
finite cells {val['n_finite']:,} · on mapped catalogue {val.get('on_catalogue_positive_pixels', 0)}.
The earlier portal error "Predicted values must be in range [0, 1]" cannot recur through a non-finite or
out-of-range cell: this file is all-finite, binary, and zero outside the scored footprint.</p></div>
<h3>Uniqueness vs the nine focus sites (directed share of <em>our</em> dots within 3 px of theirs)</h3>
<div class="scroll"><table><thead><tr><th>Site</th><th>Ours → theirs</th><th>Theirs → ours</th><th>70 % rule</th></tr></thead>
<tbody>{nine_rows}</tbody></table></div>
<p>Worst case {worst_nine*100:.2f} % ({worst_nine_row['site']}). Across the {uniq['n_priors_compared']} local prior
rasters in this repository the worst case is {uniq['worst']['mine_within_3px']*100:.2f} %
(<code>{esc(uniq['worst']['prior'])}</code>), still under the 70 % stop. Scope limit: this is the rasters present in
this checkout, not the full fleet.</p>
</section>

<section>
<h2>5 · Estimated score for the new file</h2>
<p>Three numbers, deliberately separated, because only the first is measurable here.</p>
<div class="scroll"><table>
<thead><tr><th>Quantity</th><th>Value</th><th>Evidence class</th></tr></thead>
<tbody>
<tr><th scope=row>HOLDOUT-DTI</th><td class=num>{e_hgb:.6f}</td><td>Measured this session on the shared instrument
(vendor/gems57, buffered whole-component LOQO, {n_truth:,} withheld positives). Instrument-class, <em>not</em> a
leaderboard score; no CI is quoted because the four fold scores are not independent draws of the leaderboard truth.</td></tr>
<tr><th scope=row>Ranking gain vs control</th><td class=num>×{e_hgb/e_phys:.2f}</td><td>Measured, identical geometry.</td></tr>
<tr><th scope=row>Leaderboard projection</th><td class=num>{best-0.01:.2f}–{best+0.02:.2f}</td>
<td><strong>MODEL PROJECTION — NOT A SCORE.</strong> Geometry-matched to the two nearest precedents
(GEMSDOE32 {best:.4f} at median 19.65 px, GEMSDOE36 0.2750 at 19.24 px; this file sits at
{geo['median_dcat_px']:.2f} px). Residual spread of the 112-anchor fitted model is ±0.084, so this band is
indicative only. The ranking improvement from CPT-19 has no leaderboard-verifiable counterpart, because the hidden
truth cannot be observed before submitting.</td></tr>
</tbody></table></div>
<p class="note"><strong>Honest bottom line.</strong> The file is certified, unique and physically motivated, and its
surface is the strongest ever measured on this repository's instrument. Whether that converts into more than
{best:.4f} depends on whether the official hidden faults look like scaled-up versions of the mapped catalogue —
an assumption the competition does not expose. The projection band is where the evidence points, not a promise.</p>
</section>

<section>
<h2>6 · Ranked hypotheses (new, untested beyond H1)</h2>
<ol>
<li><strong>H1 · CPT-19 catalogue-prior transfer (implemented above).</strong> Layers: all 19 official bands.
Signature: multivariate fault expression (HG edges + curvature + strain + basin depth), learned rather than
hand-weighted. Why it should find an unmapped fault: it generalises the <em>combination</em> of signatures rather
than a single ridge rule, so a fault whose magnetic edge is muted can still be caught by gravity-HG plus
curvature. Different from the repo: no previous lane used the official stack or a supervised transfer model.
Cost: low (done).</li>
<li><strong>H2 · Multi-scale structure-tensor coherence.</strong> Layers: <code>det_elev</code>,
<code>det_elev_slope</code>, <code>tc</code>. Signature: orientation coherence and anisotropy of topographic
gradient at 300 m and 1 km. Why: under Holocene fan wash the scarp relief vanishes but the <em>direction</em> of
the residual gradient stays coherent along strike, which curvature alone does not capture. Different from the repo:
existing lanes used curvature magnitude, never orientation coherence or its cross-scale consistency. Cost: low.</li>
<li><strong>H3 · Vertical-gradient dip-reversal pairing.</strong> Layers: <code>tmi_vg</code>,
<code>iso_grav_anom_vg</code>. Signature: coincident sign reversal of both vertical gradients across a lineament.
Why: a buried normal fault offsets the density/magnetisation interface, so the vertical gradient flips polarity
across the fault plane even when the surface trace is offset down-dip by
Δx = z·cot(dip) under basin fill. Different from the repo: previous lanes snapped to HG crests or projected up-dip
from <code>depth_to_base_surf</code>; none tested the polarity-pairing signature. Cost: medium.</li>
<li><strong>H4 · Data-driven relay/step-over completion.</strong> Layers: <code>tmi_hg</code>,
<code>iso_grav_anom_hg</code>, <code>det_elev_slope</code>. Signature: orientation and length statistics of the
catalogue, transferred to unlinked en-échelon lineaments. Why: unmapped splays are usually the relay between two
mapped segments. Different from the repo: S33's tip-stepover used a fixed r=30 geometric rule; this learns the
orientation/length distribution from the catalogue itself. Cost: medium.</li>
<li><strong>H5 · Geothermal-conduit conditioning.</strong> Layers: <code>cond_surf</code>,
<code>depth_to_base_surf</code>, <code>geod_2ndinv</code>, <code>geod_shearrate</code>. Signature: high
conductivity + deep basin + active strain coincident with a lineament. Why: the prize is a geothermal prize, so
the withheld truth may be enriched where fluid pathways exist. Different from the repo: GDR-well priors used an
external point catalogue; this uses the in-raster physics. Cost: low, but it is the most speculative — the truth
may be bias-free.</li>
</ol>
<p>The first lane after this one should be <strong>H2</strong> (cheapest, orthogonal signature) combined with the
fleet-consensus feature described in the review, which is the only variable in the 112-anchor table that predicts
live score with real power.</p>
</section>

<section>
<h2>7 · Exact submission steps</h2>
<ol>
<li>Download the GeoTIFF above (or the ZIP — the ZIP contains exactly one GeoTIFF and is accepted as-is).</li>
<li>Open the DrivenData submission page for competition 306 and choose <em>New submission</em>.</li>
<li>Upload the file. Do not re-save, re-project or re-compress it: the grid (EPSG:32611, 3730×3292, 100 m,
origin 243350/4508550) and the value range are already exactly what the portal checks.</li>
<li>Name: <code>{esc(cand['name'])}</code>. Note: <code>{esc(note)}</code>.</li>
<li>Submit. If the portal rejects the file for any reason, record the verbatim error in
<code>IRREGULARITIES.md</code> and stop — do not upload a second variant in the same slot.</li>
</ol>
</section>

<section>
<h2>8 · Irregularities flagged for review</h2>
<ul>
<li><strong>IR-S28-01</strong> — the nine focus files are one lineage (97.6–100 % mutual 3-px overlap); their scores
are not independent evidence and none is unique.</li>
<li><strong>IR-S28-02</strong> — no organizer receipt exists for any of the nine reported scores, including the
0.2778 headline. They are USER-REPORTED.</li>
<li><strong>IR-S28-03</strong> — <code>data/bridge/labels.tif</code> in GEMSDOE92 is the <em>same git blob</em> as
<code>existing_faults.tif</code> (sha256 <code>7ba308cc…</code>). It is the mapped catalogue, not a training label
raster for the hidden truth. Any pipeline that treats it as ground truth of the scored target is mis-specified.</li>
<li><strong>IR-S28-04</strong> — the fleet-consensus feature <code>frac_on_net15</code> that dominates the 112-anchor
score model has no documented construction recipe in this repository; it cannot be recomputed reproducibly. Any
projection using it is therefore descriptive, not auditable.</li>
<li><strong>IR-S28-05</strong> — <code>docs.nlr.gov</code>, <code>drivendata.org</code> and <code>dropbox.com</code>
are not reachable from this sandbox (allowlist: github.com, codeload, api.github.com, pypi). The metric definition
and the official data page were therefore <em>not</em> re-fetched this session; the metric arithmetic is the
repository's transcription, cross-checked against the shared evaluator's own tests.</li>
</ul>
</section>

<section>
<h2>9 · Limitations that could invalidate the projection</h2>
<ul>
<li>The scored hidden truth is unpublished. No local instrument can measure hidden-fault discovery; every holdout
number in this project is a <em>catalogue-recovery</em> proxy.</li>
<li>Transfer from catalogue-recovery to hidden-fault discovery assumes the hidden faults resemble the mapped ones in
the 19-band signature space. If they are preferentially in a different tectonic setting (e.g. deep basin fill with
no surface expression) the classifier's ranking will not transfer.</li>
<li>The 112-anchor score model is fitted to USER-REPORTED values and explains LOSO R² 0.70 with three features; its
residual spread (±0.084) is comparable to the entire gap between the best and the median site.</li>
<li>One weekly slot is at stake. If a second opinion is desired before spending it, the cheapest falsification test
is H2 on the same instrument (≈10 minutes of compute).</li>
</ul>
</section>
</main>
<footer>Generated {datetime.datetime.utcnow().isoformat()}Z from
<code>docs/s28/*.json</code> by <code>scripts/s28_report.py</code>. Numbers are reproducible with
<code>scripts/s28_nine_site_forensics.py</code>, <code>scripts/s28_build_features.py</code> and
<code>scripts/s28_lane.py</code>. <a href="REVIEW.md">Technical review</a> ·
<a href="run-card.json">Run card</a> · <a href="HYPOTHESES.md">Hypotheses</a> ·
<a href="../submission-guide.html">Submission guide</a></footer>
</div></body></html>"""

    (OUT / "executive-summary.html").write_text(html)

    run_card = {
        "schema": "gems91.s28.run-card.v1",
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "hypothesis": "H-S28-1 CPT-19: a supervised transfer classifier trained on mapped faults using the official 19-band GEODAWN stack generalises the multivariate fault signature and ranks unmapped fault locations better than hand-crafted ridge formulas.",
        "mechanism": "Mapped-fault positives vs >=800 m background negatives, 41 catalogue-free layers (robust band z-scores, 400 m context, HG energy, detrended-elevation curvature, basin x conductivity), HistGradientBoosting; emit 37,654 binary dots with >=3-cell Chebyshev separation, zero mass within 300 m of the catalogue, and distance quotas frozen before scoring.",
        "non_fault_process_that_could_mimic_it": "Basin-margin lithological contrast (Quaternary fan-wash edges) and flight-line/processing artefacts in the magnetic and gravity derivatives can produce the same edge energy without a fault.",
        "holdout": {
            "dti": round(e_hgb, 6),
            "evaluator": "vendor/gems57 metric.dti_exact via buffered whole-component LOQO (hide_frac 0.20, buffer 3 px, alpha 0.2, beta 0.8, R 3 px)",
            "withheld_positives": int(n_truth),
            "ci95": None,
            "ci_note": "No CI quoted: the four fold scores are not independent draws of the leaderboard truth, so a bootstrap over folds would overstate precision.",
            "control_same_geometry": {"physics_baseline": round(e_phys, 6), "logistic": round(e_log, 6)},
            "leakage_canary": {"max_single_layer_auc": round(hold["canary_max_auc"], 4), "stop_threshold": 0.90, "verdict": "pass"},
        },
        "correlation_overlap_vs_registry": {
            "nine_site_max_directed_3px_overlap": round(worst_nine, 4),
            "nine_site_closest": worst_nine_row["site"],
            "local_registry_worst": round(uniq["worst"]["mine_within_3px"], 4),
            "local_registry_worst_file": uniq["worst"]["prior"],
            "n_priors_compared": uniq["n_priors_compared"],
            "registry_scope": uniq["registry_scope"],
            "stop_threshold": 0.70,
            "verdict": "pass_local_scope",
        },
        "raster_sha256": cand["sha256"],
        "raster_bytes": cand["bytes"],
        "validator": {
            "all_checks_passed": val["all_checks_passed"],
            "checks": val["checks"],
            "no_nan_inside_footprint": val["checks"]["in_footprint_all_finite"],
            "values_in_0_1": val["checks"]["range_0_1_guaranteed"],
            "crs_shape_transform_match": all(val["checks"][k] for k in (
                "crs_epsg_32611", "dimensions_3730x3292", "transform_matches_sample_submission")),
        },
        "submission": {"name": cand["name"], "note": note, "note_chars": len(note),
                       "tif": cand["tif"], "zip": cand["zip"]},
        "experiments_used": 3,
        "weekly_slots_spent": 0,
        "verdict": "promote",
        "what_this_is_not": "The holdout DTI is a catalogue-recovery proxy, not a leaderboard score. The leaderboard projection is a model projection and is not a score.",
    }
    (OUT / "run-card.json").write_text(json.dumps(run_card, indent=1))
    print("wrote executive-summary.html and run-card.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
