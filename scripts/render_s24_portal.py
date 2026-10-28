#!/usr/bin/env python3
"""Render the S24 executive summary from JSON receipts only (no typed scores).

Outputs docs/s24/executive-summary.html and inserts one idempotent banner
linking to it at the top of docs/index.html. Fails closed if any receipt
claims submit-approval, an organizer score, or a leaderboard estimate.
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(rel):
    return json.loads((ROOT / rel).read_text())


def f6(x):
    return f"{float(x):.6f}"


def pct(x):
    return f"{100.0 * float(x):.2f}%"


def spearman(a, b):
    ra, rb = rankdata(a), rankdata(b)
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> int:
    e1 = load("docs/s24/run-card.json")
    e2 = load("docs/s24/e2/run-card.json")
    sgmc = {r["name"]: r for r in load("docs/s24/sgmc-diagnostic.json")["rows"]}
    nine = load("docs/s22/nine-site-audit.json")["sites"]
    audit = {r["path"]: r for r in load("docs/download-audit.json")["files"]}
    for card in (e1, e2):
        assert card["verdict"] == "negative" and card["ok_to_submit"] is False
        assert card["organizer_confirmed_score"] is None
        assert card["estimated_leaderboard_score"] is None
        assert len(card["submission_note"]) <= 140
        assert audit[card["artifact"]["tif"]]["status"] == "PASS"
        assert audit[card["artifact"]["zip"]]["status"] == "PASS"

    dots = [s["positive_pixels"] for s in nine]
    claims = [s["claimed_historical_value"] for s in nine]
    rho_dots_claim = spearman(dots, claims)

    def h1_holdout(card):
        h = card["holdout"]
        return (f"HOLDOUT-DTI {f6(h['dti'])} [{f6(h['ci95'][0])}, {f6(h['ci95'][1])}] "
                f"({h['evaluator_version']}, {h['n_withheld_positives']:,} withheld)")

    def nine_max(card):
        return card["correlation_overlap_vs_registry"]["final_dot_max_overlap_nine_leaders"]

    e2rel = e2["artifact"]["tif"].removeprefix("docs/")
    e2zip = e2["artifact"]["zip"].removeprefix("docs/")
    e1rel = e1["artifact"]["tif"].removeprefix("docs/")
    r0 = sgmc["parent_r0_gemsdoe32_h33_2_b2"]
    ratio_e2 = sgmc["s24_cckm_e2_37654"]["dti"] / r0["dti"]

    rows_s24 = ""
    for label, card, rel, sgmc_key in (
        ("S24-CCKM E2 — download this one for research", e2, e2rel, "s24_cckm_e2_37654"),
        ("S24-CCKM E1 — superseded by E2 at the fleet budget", e1, e1rel, "s24_cckm_e1_20000"),
    ):
        h = card["holdout"]
        rows_s24 += (
            f'<tr><th scope="row">{escape(label)}<br><a href="../{escape(rel)}">{escape(Path(rel).name)}</a>'
            f'<br><small>SHA-256 {escape(card["raster_sha256"][:16])}… · {card["artifact"]["n_dots"]:,} dots</small></th>'
            f"<td><strong>Unavailable.</strong> No authenticated receipt and no validated calibration. "
            f"{escape(h1_holdout(card))}; SGMC off-catalogue diagnostic {f6(sgmc[sgmc_key]['dti'])} "
            f"(report-only). Neither is a leaderboard score.</td>"
            f"<td><strong>YES vs the nine</strong> — max {pct(nine_max(card))} of dots within 3 px of any "
            f"one of the nine leaders (limit 70%); surface |&rho;| max "
            f"{card['correlation_overlap_vs_registry']['surface_max_abs_rho']:.3f}. "
            f"<strong>NO under the literal full-registry rule</strong> — 100% vs the dense calibration lattice.</td>"
            f'<td class="no">NO</td></tr>'
        )

    rows_nine = ""
    for s in sorted(nine, key=lambda s: -s["claimed_historical_value"]):
        peer = max(c["overlap_within_3px"] for c in s["peer_comparisons"])
        sg = sgmc.get(f"nine_{s['site'].lower()}", {})
        rows_nine += (
            f'<tr><th scope="row">{escape(s["site"])}</th>'
            f'<td><a href="{escape(s["source_url"])}">{escape(s["filename"])}</a>'
            f'<br><small>SHA-256 {escape(s["sha256"][:16])}… · {s["positive_pixels"]:,} positive px</small></td>'
            f"<td>{s['claimed_historical_value']:.4f} <small>USER-REPORTED, not organizer-confirmed; "
            f"defensible estimate unavailable</small><br><small>SGMC diagnostic {f6(sg.get('dti', float('nan')))}</small></td>"
            f'<td class="no">NO — {pct(peer)} vs its closest peer</td>'
            f'<td class="no">NO as a new unique submission</td></tr>'
        )

    def gates(card, sgmc_key):
        h, c = card["holdout"], card["correlation_overlap_vs_registry"]
        items = [
            ("Leakage canary (every feature alone, symmetric AUC &le; 0.90)",
             card["leakage_canary"]["pass"],
             f"max {card['leakage_canary']['max_symmetric_auc']:.3f} ({escape(card['leakage_canary']['worst'])})"),
            ("Surface uniqueness |&rho;| &le; 0.90 vs frozen registry", c["surface_pass_le_0.90"],
             f"max {c['surface_max_abs_rho']:.3f}"),
            ("Final dots &le; 70% within 3 px — nine focus leaders", c["final_dot_pass_nine_le_0.70"],
             f"max {pct(nine_max(card))}"),
            ("Final dots &le; 70% within 3 px — literal all references incl. dense lattice",
             c["final_dot_pass_all_incl_lattice_le_0.70"], f"max {pct(c['final_dot_max_overlap_all'])}"),
            ("Paired holdout beats best matched control (95% CI excludes 0)",
             h["beats_best_matched_control_ci95"],
             f"&Delta; {h['paired_difference_vs_best_control']['delta']:+.6f} vs {escape(h['best_matched_control'])}"),
            ("Format / range [0,1] validator + independent download audit",
             card["validator_output"]["pass"], "all-finite float32, EPSG:32611, 3730&times;3292"),
            ("SGMC off-catalogue diagnostic at least the GEMSDOE32 R0 reference (report-only check)",
             sgmc[sgmc_key]["dti"] >= r0["dti"],
             f"{f6(sgmc[sgmc_key]['dti'])} vs R0 {f6(r0['dti'])}"),
        ]
        return "".join(
            f'<tr><td>{name}</td><td class="{"yes" if ok else "no"}">{"PASS" if ok else "FAIL"}</td><td>{detail}</td></tr>'
            for name, ok, detail in items
        )

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S24-CCKM executive summary · GEMSDOE91</title>
<link rel="stylesheet" href="../assets/portal.css">
<style>.no{{color:#9b1c1c;font-weight:700}}.yes{{color:#14532d;font-weight:700}}
.decision{{border:3px solid #9b1c1c;padding:1rem 1.2rem;border-radius:8px;background:#fff7ed}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d1d5db;padding:.5rem;vertical-align:top;text-align:left}}
.table-scroll{{overflow-x:auto}}code{{word-break:break-all}}</style></head>
<body><div class="wrap"><main id="main">
<p><a href="../index.html">&larr; Current portal</a> · <a href="preregistration.md">Preregistration</a> ·
<a href="run-card.json">E1 run card</a> · <a href="e2/run-card.json">E2 run card</a> ·
<a href="REVIEW.md">Full session review</a></p>
<h1>S24-CCKM — executive summary (2026-10-27)</h1>
<div class="decision">
<p style="font-size:1.25rem;margin:.2rem 0"><strong>Historical research TIF generated 2026-10-27: YES</strong> (vs the nine focus sites).<br>
<strong>OK TO DOWNLOAD: YES — RESEARCH ONLY.</strong><br>
<strong>OK TO SUBMIT: NO.</strong> Do not upload it as a high-score attempt.</p>
<p><strong>File to download:</strong> <a href="../{escape(e2rel)}">{escape(Path(e2rel).name)}</a>
(<a href="../{escape(e2zip)}">single-TIFF ZIP</a>)<br>
SHA-256 <code>{escape(e2["raster_sha256"])}</code> · {e2["artifact"]["n_dots"]:,} dots ·
{h1_holdout(e2)}.</p>
<p>Why not OK to submit: (1) it does not significantly beat its own gravity-gradient control in paired
holdout; (2) on the external SGMC off-catalogue diagnostic it reaches {f6(sgmc["s24_cckm_e2_37654"]["dti"])},
only {100*ratio_e2:.1f}% of the GEMSDOE32 reference raster's {f6(r0["dti"])} at the same budget, so beating the
user-reported 0.2778 is not expected (expert judgement, not an estimated score); (3) under the literal
full-registry duplicate rule it is 100% within 3 px of the dense calibration lattice, which only 6,649 of
5,167,373 footprint pixels escape; (4) promotion needs a separate selector decision and a live weekly-cap
check that no script here can perform. Maximizing P(Win) means not spending a slot here.</p>
</div>

<h2>The table the project asked for</h2>
<p>Every score is labelled. <strong>HOLDOUT-DTI</strong> measures recovery of withheld <em>catalogue</em> faults
with the shared evaluator; it is never a leaderboard score. <strong>USER-REPORTED</strong> values come from the
session prompt with no authenticated receipt; none is ORGANIZER-CONFIRMED. The fetched public leaderboard on
2026-10-27 stood at #1 = 0.4544 (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">DrivenData</a>);
the prompt's 0.4413 / 0.3195 values are stale.</p>
<div class="table-scroll"><table>
<caption>Historical S24 research files (not new this session)</caption>
<thead><tr><th scope="col">File to download</th><th scope="col">Estimated leaderboard score</th>
<th scope="col">Unique vs the other GEMSDOE sites?</th><th scope="col">OK to submit?</th></tr></thead>
<tbody>{rows_s24}</tbody></table></div>
<div class="table-scroll"><table>
<caption>Best historical file per focus site (GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36)</caption>
<thead><tr><th scope="col">Site</th><th scope="col">Best claimed file</th><th scope="col">Score evidence</th>
<th scope="col">Unique among the nine?</th><th scope="col">OK to submit?</th></tr></thead>
<tbody>{rows_nine}</tbody></table></div>
<p><strong>Clear answer, per site:</strong> the highest claim overall is GEMSDOE32
<code>h33-h33-2-b2…-zeros</code> at 0.2778 (user-reported). It is also <em>not</em> a file to submit as a
&ldquo;new unique&rdquo; attempt: all nine files are one duplicate family (every leader has &ge; 93% of its
dots within 3 px of a peer; GEMSDOE25 and GEMSDOE30 have identical positive support). Resubmitting any of
them spends a slot re-measuring the same rasters.</p>

<h2>Validation gates — E2 (E1 in its run card)</h2>
<div class="table-scroll"><table><thead><tr><th scope="col">Gate</th><th scope="col">Result</th>
<th scope="col">Measured detail</th></tr></thead><tbody>{gates(e2, "s24_cckm_e2_37654")}</tbody></table></div>

<h2>Why the GEMSDOE32 claim (0.2778) is the family&rsquo;s highest — and its limits</h2>
<p>Across the nine byte-identical-audited leaders, claimed values rise as positive-pixel count falls from
&asymp;60k toward &asymp;37.6k (Spearman &rho;(dots, claim) = {rho_dots_claim:+.3f} over these nine
<em>non-independent</em> files). That is consistent with the official metric
(<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a>:
&alpha;=0.2, &beta;=0.8, 300 m triangular kernel): within one shared support, pruning/redundantly spaced
dots removes false-positive weight while neighbours within 300 m keep covering the same truth pixels.
<strong>Causality is not proven</strong> — the claims have no receipts, the files overlap by
&ge;93&ndash;100%, and one score cannot separate TP/FP/FN. In a separate paired holdout, raising the CCKM budget from 20,000 to 37,654 gained
+{e2["holdout"]["paired_difference_vs_extra_budget_arm"]["delta"]:.6f} HOLDOUT-DTI
(95% CI [{e2["holdout"]["paired_difference_vs_extra_budget_arm"]["ci95"][0]:.6f},
{e2["holdout"]["paired_difference_vs_extra_budget_arm"]["ci95"][1]:.6f}]). More coverage may have contributed; the comparison does not identify the cause.</p>
<p><strong>Can this lane beat 0.2778?</strong> This has not been established: at the identical 37,654-dot budget
the CCKM surface reaches {100*ratio_e2:.1f}% of the GEMSDOE32 raster on the SGMC off-catalogue diagnostic
and adds nothing significant over a plain gravity-gradient ranking in paired holdout. Beating 0.2778 likely
requires a materially better <em>surface</em> (supervised multi-band mapping, the official 1 m DEM links,
diverse ensembling) validated on a live-analogue instrument — not another emission edit of this surface.
That is an expert judgement from the two labelled diagnostics, not an estimated score.</p>

<h2>How a future, selector-approved submission would be made</h2>
<ol>
<li>Pass every gate above, then obtain a <em>separate selector</em> decision (this page cannot grant one)
and check the remaining weekly quota on the authenticated
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">submission page</a>
(the website limit prevails over the rules PDF).</li>
<li>Download the approved <code>-zeros.tif</code> (or its one-TIFF ZIP) and verify its SHA-256 locally
(<code>sha256sum file.tif</code> on Linux, <code>Get-FileHash file.tif</code> in PowerShell) against the
run card before uploading. All-finite values in [0,1] address one possible cause of the portal error
&ldquo;Predicted values must be in range [0, 1]&rdquo;: the writer rejects sentinels such as
-3.4028235e+38 instead of copying them. This does not establish organizer acceptance or explain a specific past rejection.</li>
<li>Upload the single-band GeoTIFF (EPSG:32611, float32, same shape/transform as the sample), set the
submission name and an optional note of at most 140 characters (E2&rsquo;s recorded note, for provenance
only: &ldquo;{escape(e2["submission_note"])}&rdquo;), and create the submission.</li>
<li>Save the submission ID, timestamp, uploaded-file SHA-256, and resulting score together. Only that
receipt may later be labelled ORGANIZER-CONFIRMED. Known irregularity: the official text says data
outside bounds should be null/NaN, while the fleet&rsquo;s scored &ldquo;-zeros&rdquo; files use 0 outside
with <code>nodata=None</code>; server behaviour is unverified from here, so the selector must make the
final encoding call explicitly.</li>
</ol>

<h2>Method in one paragraph</h2>
<p>CCKM (bands B14 total magnetic intensity + B13 isostatic gravity only): masked 15-pixel-window excess
kurtosis of the B14 high-pass residual, sampled &plusmn;9 px across the B13 gradient normal and gated by
|&nabla;B13| — a change in magnetic texture tail-weight across a density contact, targeting faults buried
under cover with no mapped scarp. Named mimics: unfaulted intrusive/volcanic contacts, lava-flow margins,
survey seams. Declared-NoData cells (3,061 per band) are <em>excluded</em> from every statistic
(masked normalised convolution) — the repair of the S22 failure mode. Band identities are internally
corroborated label-blind (B03 vs |&nabla;B14|: r&nbsp;=&nbsp;1.000000 on
5,135,228 eroded-valid pixels; <a href="band-identity.json">receipt</a>). A fault map is not evidence of a
geothermal vent or reservoir.</p>

<h2>Historical reproduction — do not rerun without preflight</h2>
<p>The E1 and E2 run cards document an earlier self-assigned research run. The lane was not coordinator-assigned,
and the dense-registry duplicate gate failed. The historical v2 holdout is not a matched evaluation under the
corrected v3 context-buffer split. Do not repeat the archived commands or use these results for promotion.
First establish an assigned lane, authorized pinned inputs, a complete registry and a passing preflight;
then recompute both candidate and incumbent using the corrected evaluator. See
<a href="../review-20261028.md">current review</a>.</p>
<p>Maximize P(Win) · Own the Outcome. Negative results are deliverables; 2 of 3 budgeted experiments used,
0 weekly slots used.</p>
</main></div></body></html>
"""
    out = DOCS / "s24/executive-summary.html"
    out.write_text(html)

    # The front door has a single owner (render_olc91_portal.render, which now
    # carries the fail-closed s24_callout). Delegate to it instead of patching
    # generated HTML, which test re-renders would wipe.
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.render_olc91_portal import render as render_front_door
    render_front_door()
    assert "s24/executive-summary.html" in (DOCS / "index.html").read_text()
    print(f"wrote {out.relative_to(ROOT)}; front door re-rendered with S24 callout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
