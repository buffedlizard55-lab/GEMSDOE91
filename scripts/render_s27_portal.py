#!/usr/bin/env python3
"""Render the S27 executive summary from JSON receipts only (no typed scores).

Output: docs/s27/executive-summary.html. Fails closed if the run card claims
submit-approval or an organizer score, or if the candidate fails the
independent/format audits.
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel):
    return json.loads((ROOT / rel).read_text())


def f6(x):
    return f"{float(x):.6f}"


def pct(x):
    return f"{100.0 * float(x):.2f}%"


def main() -> int:
    card = load("docs/s27/run-card.json")
    diag = load("docs/s27/diagnostics.json")
    nine_doc = load("docs/s27/nine-site-audit.json")
    nine = nine_doc["sites"]
    holdout = load("docs/s27/holdout.json")
    can = load("docs/s27/canaries.json")
    indep = load("docs/s27/independent-tif-check.json")
    lb = load("evidence/public-leaderboard-2026-10-29.json")
    audit = {r["path"]: r for r in load("docs/download-audit.json")["files"]}
    emit = load("docs/s27/final-emission.json")
    _fdc = load("docs/s27/final-dot-checks.json")["checks"]
    s25_overlap = next(r["overlap_within_3px"] for r in _fdc
                       if r["path"].endswith("-3188f6e6-zeros.tif"))

    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["organizer_confirmed_score"] is None
    assert card["estimated_leaderboard_score"] is None
    assert len(card["submission_note"]) <= 140
    assert indep["all_pass"] is True and indep["sha256"] == card["raster_sha256"]
    assert audit[card["artifact"]["tif"]]["status"] == "PASS"
    assert audit[card["artifact"]["zip"]]["status"] == "PASS"
    assert diag["lfi"]["label_class"] == "MODEL_PROJECTION_NOT_A_SCORE"
    assert card["raster_sha256"] == diag["candidate"]["sha256"]

    h = card["holdout"]
    corr = card["correlation_overlap_vs_registry"]
    gates = card["gates_final"]
    tif_rel = card["artifact"]["tif"].removeprefix("docs/")
    zip_rel = card["artifact"]["zip"].removeprefix("docs/")
    tif_name = Path(tif_rel).name

    lfi = {r["name"]: r for r in diag["lfi"]["rows"]}
    fit1 = diag["lfi"]["fits"]["ridge1"]
    cand_lfi = lfi["s27_fabricfar_candidate"]
    s25_lfi = lfi["s25_fabric_e2_candidate"]
    r0_lfi = lfi["parent_r0_gemsdoe32"]
    pdwc_lfi = lfi["s21_pdwc_e3"]
    sgmc5 = {r["name"]: r for r in diag["sgmc"]["rows_min_cat_dist_5px"]}
    sgmc3 = {r["name"]: r for r in diag["sgmc"]["rows_min_cat_dist_3px"]}
    prof = {r["name"]: r for r in diag["dot_profile"]["rows"]}
    pc, p25, pr0 = (prof["s27_fabricfar_candidate"], prof["s25_fabric_e2_candidate"],
                    prof["parent_r0_gemsdoe32"])
    lb1 = lb["rows"][0]["best_public_dw_tversky"]
    lb2 = lb["rows"][1]["best_public_dw_tversky"]
    g5 = diag["sgmc"]["gate_G5"]

    def holdout_line():
        return (f"HOLDOUT-DTI {f6(h['dti'])} [{f6(h['ci95'][0])}, {f6(h['ci95'][1])}] "
                f"({escape(h['evaluator_version'])}, {escape(h['split_version'])}, "
                f"{h['n_withheld_positives']:,} withheld positives)")

    # ---------- Table 1: this repo's research candidates ----------
    est_s27 = (
        f"<strong>ORGANIZER-CONFIRMED: none.</strong> Estimated leaderboard score = LFI MODEL "
        f"projection <strong>{cand_lfi['ridge1']:.4f}</strong> (ridge10 {cand_lfi['ridge10']:.4f}; "
        f"leave-one-site-out RMSE {fit1['rmse_loso']:.4f}, Spearman {fit1['spearman_loso']:.3f}, "
        f"{fit1['n_anchors']} USER-REPORTED anchors) — <em>a projection, never a score</em>. "
        f"{escape(holdout_line())}; SGMC&gt;500 m diagnostic {f6(sgmc5['s27_fabricfar_candidate']['dti'])} "
        f"(report-only proxy).")
    uniq_s27 = (
        f"<strong>YES vs the nine focus sites</strong> (max {pct(corr['final_dot_max_overlap_nine_leaders'])} "
        f"within 3 px, limit 70%) and <strong>YES vs every competitive registry raster</strong> "
        f"(max {pct(corr['final_dot_max_overlap_competitive_le_90000px'])} vs "
        f"{escape(Path(corr['final_dot_closest_competitive']).name)}); surface |&rho;| max "
        f"{corr['surface_max_abs_rho']:.3f} (limit 0.90). <strong>NO in the literal all-blankets "
        f"scope</strong> ({pct(corr['final_dot_max_overlap_all'])} vs the 206,895-dot calibration "
        f"lattice; geometric capacity bound forces &ge;"
        f"{100*corr['lattice_capacity_bound_at_budget']['overlap_lower_bound']:.1f}% at this budget "
        f"for any raster — coordinator policy decision, never evaded).")

    def research_row(label, rel, sha, dots, est_html, uniq_html):
        return (f'<tr><th scope="row">{escape(label)}<br><a href="../{escape(rel)}">'
                f"{escape(Path(rel).name)}</a><br><small>SHA-256 {escape(sha[:16])}… · "
                f"{dots:,} dots</small></th><td>{est_html}</td><td>{uniq_html}</td>"
                f'<td class="no">NO</td></tr>')

    rows_research = (
        research_row("★ S27-FABRIC-FAR — THIS SESSION: download this one (research)",
                     tif_rel, card["raster_sha256"], card["artifact"]["n_dots"],
                     est_s27, uniq_s27)
        + research_row(
            "S25-FABRIC E2 — previous session (parent surface, catalogue-hugging emission)",
            "downloads/gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif",
            s25_lfi["sha256"], 37_654,
            f"<strong>ORGANIZER-CONFIRMED: none.</strong> LFI MODEL projection "
            f"<strong>{s25_lfi['ridge1']:.4f}</strong> (ridge10 {s25_lfi['ridge10']:.4f}). "
            f"SGMC&gt;500 m {f6(sgmc5['s25_fabric_e2_candidate']['dti'])}.",
            "YES vs the nine (max 40.19%); NO vs closest competitive reference (74.89%) "
            "per its own S25 receipts.")
        + research_row(
            "S21-PDWC E3 — earlier session (highest LFI-projected unsubmitted candidate in repo)",
            "downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif",
            pdwc_lfi["sha256"], 37_654,
            f"<strong>ORGANIZER-CONFIRMED: none.</strong> LFI MODEL projection "
            f"<strong>{pdwc_lfi['ridge1']:.4f}</strong> (ridge10 {pdwc_lfi['ridge10']:.4f}). "
            f"SGMC&gt;500 m {f6(sgmc5['s21_pdwc_e3']['dti'])}.",
            "Per its S21 run card: PASS vs competitive rasters (≤64% capped); literal "
            "all-blankets scope fails. Its own verdict: negative."))

    # ---------- Table 2: nine focus sites ----------
    rows_nine = ""
    for s in sorted(nine, key=lambda s: -(s["claimed_value_user_reported"] or 0)):
        key = f"nine_{s['site'].lower()}"
        peer = s["max_overlap_vs_other_eight"]
        cand_ov = s["s27_candidate_overlap_vs_this_leader"]["overlap_within_3px"]
        rows_nine += (
            f'<tr><th scope="row"><a href="{escape(s["site_url"])}">{escape(s["site"])}</a>'
            f"<br><small>main HEAD {escape(s['current_main_head'][:10])}… (2026-10-29, ls-remote)</small></th>"
            f"<td>{escape(s['best_claimed_file'])}<br><small>SHA-256 {escape(s['sha256'][:16])}… · "
            f"{s['positive_pixels']:,} dots</small></td>"
            f"<td><strong>{s['claimed_value_user_reported']:.4f}</strong> <small>USER-REPORTED "
            f"(prompt), NOT ORGANIZER-CONFIRMED</small><br><small>LFI MODEL projection "
            f"{lfi[key]['ridge1']:.4f} (in-anchor-set) · SGMC&gt;500 m {f6(sgmc5[key]['dti'])}</small></td>"
            f'<td class="no">NO — {pct(peer["overlap_within_3px"])} vs {escape(peer["reference_site"])}</td>'
            f"<td><strong>YES</strong> — S27 file is {pct(cand_ov)} vs this leader</td>"
            f'<td class="no">NO — historical duplicate; do not re-submit</td></tr>')

    # ---------- Experiments ----------
    rows_exp = ""
    labels = {"ctrl_collar3": "CTRL · collar 3.05 px (= S25 emission; matched incumbent)",
              "e1_collar10": "E1 · collar 10 px (ablation)",
              "e2_stratified": "E2 · distance-stratified quotas (candidate arm)"}
    for arm in ("ctrl_collar3", "e1_collar10", "e2_stratified"):
        sc = holdout["scores"][arm]
        rows_exp += (f'<tr><th scope="row">{escape(labels[arm])}</th>'
                     f"<td>{f6(sc['dti'])} [{f6(sc['ci95'][0])}, {f6(sc['ci95'][1])}]</td></tr>")

    # ---------- Gates ----------
    capb = corr["lattice_capacity_bound_at_budget"]
    gate_items = [
        ("G1 · Leakage canary — every feature alone, symmetric AUC ≤ 0.90",
         gates["G1_canary"],
         f"max {can['max_symmetric_auc']:.4f} ({escape(can['worst'])}) over "
         f"{len(can['canaries'])} feature-fold tests — exact reproduction of S25's canary"),
        ("G2 · Surface uniqueness |ρ| ≤ 0.90 before placement",
         gates["G2_surface"],
         f"max {corr['surface_max_abs_rho']:.4f} vs {escape(Path(corr['surface_closest']).name)}"),
        ("G3 · Final dots ≤ 70% within 3 px — nine focus leaders",
         gates["G3_dots_nine"], f"max {pct(corr['final_dot_max_overlap_nine_leaders'])}"),
        ("G3 · Final dots ≤ 70% within 3 px — competitive references (≤90,000 px)",
         gates["G3_dots_competitive"],
         f"max {pct(corr['final_dot_max_overlap_competitive_le_90000px'])} vs "
         f"{escape(Path(corr['final_dot_closest_competitive']).name)} "
         f"(S25 failed this at 74.89%)"),
        ("G3 · Final dots ≤ 70% — literal all references incl. dense calibration blankets",
         gates["G3_dots_all_incl_blankets"],
         f"max {pct(corr['final_dot_max_overlap_all'])}; capacity bound forces ≥"
         f"{100*capb['overlap_lower_bound']:.2f}% at {capb['candidate_budget']:,} dots "
         f"(only {capb['uncovered_pixels']:,} of {capb['footprint_pixels']:,} footprint cells are "
         f">3 px from the lattice) — geometrically impossible; policy decision needed"),
        ("G4 · Paired HOLDOUT-DTI beats matched incumbent, 95% CI lower bound > 0",
         gates["G4_holdout_beats_ctrl_ci95"],
         f"Δ exactly +0.000000 [0.000000, 0.000000] — by instrument construction: every v3 test "
         f"quadrant contains zero visible catalogue pixels (median distance-to-visible "
         f"234–808 px), so collar/quota rules cannot act in-fold. The holdout cannot measure "
         f"emission geography; it measures only surface ranking (identical surface ⇒ identical dots)"),
        ("G5 · SGMC off-catalogue (>500 m from catalogue) DTI exceeds R0 at identical setting",
         gates["G5_sgmc"],
         f"candidate {f6(g5['candidate_dti_5px'])} vs R0 {f6(g5['r0_dti_5px'])} "
         f"(S25 candidate was {f6(sgmc5['s25_fabric_e2_candidate']['dti'])}: stratification "
         f"improved it, not past R0)"),
        ("G6 · Format — single-band float32, all-finite [0,1], EPSG:32611, 3730×3292, pinned transform",
         gates["G6_format"],
         "shared writer + validator + independent tifffile re-read + all-download audit PASS "
         "(binary {0.0,1.0} on all-finite zeros ⇒ the reported portal "
         "“Predicted values must be in range [0, 1]” error class cannot occur)"),
        ("Selector decision + live weekly-cap check (protocol rule 6)",
         False, "not performed here and never by a lane session; 0 slots used"),
    ]
    rows_gates = "".join(
        f'<tr><td>{escape(name)}</td><td class="{"yes" if ok else "no"}">'
        f'{"PASS" if ok else "FAIL"}</td><td>{detail}</td></tr>'
        for name, ok, detail in gate_items)

    note = escape(card["submission_note"])
    name = escape(card["submission_name"])
    shares = emit["band_shares_final"]

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S27-FABRIC-FAR executive summary · GEMSDOE91</title>
<link rel="stylesheet" href="../assets/portal.css">
<style>.no{{color:#9b1c1c;font-weight:700}}.yes{{color:#14532d;font-weight:700}}
.decision{{border:3px solid #9b1c1c;padding:1rem 1.2rem;border-radius:8px;background:#fff7ed}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d1d5db;padding:.5rem;vertical-align:top;text-align:left}}
.table-scroll{{overflow-x:auto}}code{{word-break:break-all}}</style></head>
<body><div class="wrap"><main id="main">
<p><a href="../index.html">&larr; Portal home</a> · <a href="preregistration.md">Preregistration (frozen before results)</a> ·
<a href="run-card.json">Run card (JSON)</a> · <a href="diagnostics.json">Diagnostics: SGMC + LFI model + dot profile</a> ·
<a href="nine-site-audit.json">Nine-site audit (JSON)</a> · <a href="holdout.json">Holdout receipt</a> ·
<a href="REVIEW.md">Full session review</a></p>

<h1>S27-FABRIC-FAR — executive summary (2026-10-29)</h1>

<div class="decision">
<p style="font-size:1.3rem;margin:.2rem 0"><strong>NEW UNIQUE TIF GENERATED: YES.</strong><br>
<strong>OK TO DOWNLOAD: YES — RESEARCH / SELECTOR REVIEW.</strong><br>
<strong>OK TO SUBMIT: NO — DO NOT UPLOAD THIS FILE YET.</strong></p>

<p><strong>⬇ File to download:</strong> <a href="../{escape(tif_rel)}"><strong>{escape(tif_name)}</strong></a>
(<a href="../{escape(zip_rel)}">single-TIFF ZIP for the submission form</a>)<br>
SHA-256 <code>{escape(card["raster_sha256"])}</code> · {card["artifact"]["n_dots"]:,} dots · binary {{0.0, 1.0}} ·
all-finite zeros · EPSG:32611 · 3730×3292 · independently re-validated from bytes (<a href="independent-tif-check.json">check</a>).</p>

<p><strong>Estimated leaderboard score: {cand_lfi['ridge1']:.4f}</strong> — an <em>LFI model projection, not a score</em>
(ridge10 {cand_lfi['ridge10']:.4f}; leave-one-site-out RMSE {fit1['rmse_loso']:.4f} on {fit1['n_anchors']} user-reported anchors).
The same model projects the GEMSDOE32 reference raster at {r0_lfi['ridge1']:.4f} (user-reported live claim 0.2778), so on the best
live-anchored estimator available <strong>this file is projected <em>below</em> 0.2778</strong>.
ORGANIZER-CONFIRMED score for any file on this page: <strong>none</strong>.
{escape(holdout_line())} (a catalogue-recovery measurement, never a leaderboard number).
Official public leaderboard re-fetched 2026-10-29: <strong>#1 = {lb1:.4f}, #2 = {lb2:.4f}</strong>
(<a href="{escape(lb['source_url'])}">DrivenData</a>); the figures 0.4413 and 0.3195 circulating in the project prompt are stale.</p>

<p><strong>Unique?</strong> <strong>YES vs all nine focus sites</strong> (max {pct(corr['final_dot_max_overlap_nine_leaders'])}
of its dots lie within 3 px of any one leader; protocol limit 70%) and <strong>YES vs every competitive (≤90,000-dot)
registry raster</strong> (max {pct(corr['final_dot_max_overlap_competitive_le_90000px'])} — the gate S25 failed at 74.89%).
It is not a copy of any previous submission: new stratified emission of a validated surface; only
{pct(s25_overlap)} of its dots fall within 3 px of even its own parent S25 candidate.
Literal all-raster scope (including a 206,895-dot calibration lattice covering 99.87% of the footprint within 3 px)
remains capacity-impossible for <em>any</em> 37,654-dot raster and needs a coordinator scope ruling.</p>

<p><strong>Why OK TO SUBMIT = NO (all automated — no human inspection anywhere in this pipeline):</strong>
(1) <em>Holdout gate G4 fails by construction:</em> the shared v3 holdout contains zero visible catalogue pixels inside
every test quadrant, so distance-based emission rules are mathematically inert in-fold (Δ = 0.000000 exactly);
the instrument cannot certify an emission-geometry lane, and the preregistered rule says no slot without beating the matched incumbent.
(2) <em>SGMC gate G5 fails:</em> far-field proxy DTI {f6(g5['candidate_dti_5px'])} &lt; R0's {f6(g5['r0_dti_5px'])} — stratification
improved S25's far-field standing by +55% relative ({f6(sgmc5['s25_fabric_e2_candidate']['dti'])} → {f6(g5['candidate_dti_5px'])})
but the fabric surface's rankings far from the catalogue still trail the R0 family.
(3) <em>Selector step</em> (protocol rule 6) has not been performed; 0 weekly slots were used.
<strong>Maximize P(Win):</strong> present this file to the selector only as an information probe candidate, or hold it for the
final-round single-submission choice if its novel-coverage profile is valued there; do not expect it to beat 0.2778 on the public board.</p>
</div>

<h2>The required table — file to download · estimated score · unique? · OK to submit?</h2>
<p>Every number is labelled: <strong>ORGANIZER-CONFIRMED</strong> (receipt only — none exist here) ·
<strong>HOLDOUT-DTI</strong> (shared evaluator, withheld catalogue faults — never a leaderboard score) ·
<strong>LFI MODEL_PROJECTION_NOT_A_SCORE</strong> (refitted 2026-10-29 on user-reported anchors) ·
<strong>USER-REPORTED</strong> (prompt/site claim, no receipt) · <strong>SGMC diagnostic</strong> (report-only proxy truth).</p>
<div class="table-scroll"><table>
<caption>Research candidates generated in <em>this</em> repository (★ = this session's file)</caption>
<thead><tr><th scope="col">File to download</th><th scope="col">Estimated leaderboard score (labelled)</th>
<th scope="col">Unique vs GEMSDOE24/25/27/28/30/31/32/33/36 + registry?</th><th scope="col">OK to submit?</th></tr></thead>
<tbody>{rows_research}</tbody></table></div>

<div class="table-scroll"><table>
<caption>Best historical file on each focus site (bytes re-hashed 2026-10-29; 72 directed peer overlaps recomputed today)</caption>
<thead><tr><th scope="col">Site</th><th scope="col">Best submission on that site</th><th scope="col">Score evidence</th>
<th scope="col">Unique among the nine?</th><th scope="col">S27 file unique vs it?</th><th scope="col">Submit it?</th></tr></thead>
<tbody>{rows_nine}</tbody></table></div>

<p><strong>Obvious answer, site by site:</strong> the best-scoring historical file per site is the one named in its row;
the highest claim among the nine is <strong>GEMSDOE32 · <code>h33-h33-2-b2…-zeros</code> · 0.2778 (USER-REPORTED)</strong>.
(Note: outside the nine, the same prompt also lists a GEMSDOE92 file at 0.2784 — a higher <em>claim</em>, likewise unreceipted
and with no pinned raster in this repo; flagged in <a href="REVIEW.md">REVIEW.md</a>.)
But <strong>not one of the nine is unique</strong> — each has 97.6–100% of its dots within 3 px of another leader (recomputed today);
they are pruning descendants of a single H19-5 ridge-network raster. Downloading and re-uploading any of them buys a duplicate,
not a new attempt. The only new file that is unique against all nine <em>and</em> the competitive registry is the ★ S27 download
above — research/selector use only, for the three reasons in the decision box.</p>

<h2>Why did GEMSDOE32's 0.2778 beat its siblings — and can a unique file beat it?</h2>
<p><strong>Why (mechanism, proven from bytes in S22/S25 and consistent with today's diagnostics).</strong>
The metric is DTI = T<sub>w</sub> / (T<sub>w</sub> + 0.2·FP<sub>w</sub> + 0.8·FN<sub>w</sub> + ε) with a 300 m triangular kernel
(<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official description</a>):
each truth pixel credits only the <em>best</em> nearby prediction, while every predicted dot pays FP weight for the share of its
kernel covering no truth. All nine leaders share one H19-5-derived ridge network; R0's edge is <em>emission economics</em>:
dotting that network at ~2.8 px spacing, then deleting dots within 1–2 px of the mapped catalogue (6,436 dots that were nearly
pure FP cost, because mapped pixels are masked from scoring while kernels keep covering the same nearby truth). Dot count
anti-correlates with claimed score across the family; the pure-FP-deletion model reproduces the family's score ladder
(0.1922 → 0.2600 → 0.2708 → 0.2778) within ~0.001. R0 also sits where independent methods agree: {pct(pr0['cons_votes_hist']['>=3'])}
of its dots are in ≥3-anchor consensus zones (the single strongest live-truth concentration signal in the inversion, θ ≈ +2.97),
at a median {pr0['dcat_px_median']:.1f} px from the catalogue.</p>
<p><strong>Can a unique file beat it? In principle, yes; on today's evidence, not yet.</strong> S27 tested the strongest available
lever honestly: keep S25's independently-validated detector (the only recent feature family to beat its matched holdout control
with CI excluding zero) and fix its one measured defect — dot geography. Stratified emission moved median distance-to-catalogue
from {p25['dcat_px_median']:.1f} px to {pc['dcat_px_median']:.1f} px with exact preregistered band shares
({shares[0]*100:.0f}/{shares[1]*100:.0f}/{shares[2]*100:.0f}/{shares[3]*100:.0f}/{shares[4]*100:.0f}%), lifted the live-anchored
projection from {s25_lfi['ridge1']:.4f} to {cand_lfi['ridge1']:.4f} and the far-field SGMC proxy by +55% relative — yet both still
trail R0. The residual gap is information, not geometry: only {pct(pc['cons_votes_hist']['>=3'])} of S27's dots sit in ≥3-anchor
consensus zones vs R0's {pct(pr0['cons_votes_hist']['>=3'])}; forced far-field dots are ranked by a surface trained on catalogue
labels, so its far-field ordering is extrapolation. A &gt;0.2778 unique file therefore needs either a detector whose <em>far-field</em>
ranking is trained/validated specifically on isolated (catalogue-distant) faults, or genuinely new information — above all the
1 m USGS 3DEP DEM lane (free/public-domain at
<a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">usgs.gov/3dep</a>, not fetchable from this
sandbox's network allowlist). Anyone claiming a present-day projection above 0.2778 for a unique raster on this 100 m stack
should be required to show the same five receipts as this page.</p>

<h2>Experiments (2 of 3 budget; paired arms on one OOF surface, identical v3 folds/budgets)</h2>
<div class="table-scroll"><table><thead><tr><th scope="col">Arm</th>
<th scope="col">HOLDOUT-DTI ({escape(h['evaluator_version'])}, {escape(h['split_version'])}, {h['n_withheld_positives']:,} withheld) [95% CI]</th></tr></thead>
<tbody>{rows_exp}</tbody></table></div>
<p>All three arms return the <em>identical</em> number because, inside every v3 test quadrant, the visible catalogue is empty
(whole intersecting components are withheld with an 80 px feature buffer): distance-to-visible has median 234–808 px there,
vs 23.1 px on the full map. Collar and distance quotas therefore cannot bind in-fold, and E2's two-pass quota+redistribution
greedy provably returns the CTRL dot set. This is a finding about the instrument, recorded as an irregularity:
<strong>holdout-DTI on v3 folds certifies surface ranking only; emission-geometry lanes must be arbitrated by independent
far-field evidence (SGMC/LFI), which is exactly what gates G5 + the estimate table did.</strong>
CTRL's {f6(h['matched_incumbent_dti'])} vs S25's 0.147741 for the identical recipe is a cross-session reproduction drift
(fold 0 bitwise-identical term-for-term; folds 1–3 differ slightly — HGB fit nondeterminism across sessions; within CI).</p>

<h2>Automated validation gates (no human inspection anywhere)</h2>
<div class="table-scroll"><table><thead><tr><th scope="col">Gate</th><th scope="col">Result</th>
<th scope="col">Measured detail</th></tr></thead><tbody>{rows_gates}</tbody></table></div>

<h2>Exactly how a submission would be made (only after selector approval of some future file)</h2>
<ol>
<li>Download the selector-approved file and verify its SHA-256 against the run card
(this session's research file: <code>{escape(card["raster_sha256"])}</code> — <strong>not approved</strong>).</li>
<li>Go to the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData
submissions page</a> (signed in) → “New submission”.</li>
<li>Upload either the single-band GeoTIFF (<code>{escape(tif_name)}</code>) or the supplied one-TIFF ZIP.
Format is pre-validated: float32, all values finite and in [0, 1] (binary 0.0/1.0 — the
“Predicted values must be in range [0, 1]” portal error cannot occur), EPSG:32611, 3730×3292 @ 100 m,
CRS/shape/geotransform identical to <code>sample_submission.tif</code>.</li>
<li><strong>Submission name:</strong> <code>{name}</code><br>
<strong>Note ({card["submission_note_chars"]}/140 chars):</strong> <code>{note}</code></li>
<li>Only after the portal returns a score + submission ID is any number ORGANIZER-CONFIRMED — record ID, timestamp,
score and SHA-256 in <code>registry/lfi_live_anchors.csv</code> and refit. Remember both prize rounds score the
<em>single selected</em> submission (<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official structure</a>);
check the live weekly cap on the submission page itself before spending a slot.</li>
</ol>

<h2>Method in one paragraph &amp; what was ruled out</h2>
<p>Detector (frozen from S25, rebuilt bit-reproducibly — canary repeats exactly): oriented morphological granulometry of
detrended elevation/slope (B12/B19) + gravity↔magnetics cross-spectral phase lag (B13/B14) + 23 base band/gradient features →
spatially cross-fitted histogram gradient boosting on whole-component buffered quadrants. Emission (new in S27, preregistered):
greedy surface-descending placement at 3.05 px spacing with distance-to-catalogue band quotas
(5/15/25/25/30% over (3,5], (5,10], (10,20], (20,40], (40,∞) px) and ≤65% within-3-px caps against 26 frozen references
(the caps turned out non-binding: stratification alone delivered the uniqueness). Ruled out this session: that emission geometry
was the <em>only</em> thing separating the fabric detector from R0-level live performance — it was necessary, not sufficient.
Non-fault mimics that can produce the same signatures: unfaulted dipping lithologic contacts, remanent-magnetization offsets,
fan-lobe/shoreline fabrics, flight-line seams. A fault prediction is not evidence of a geothermal vent or reservoir.</p>

<h2>Receipts &amp; official sources for manual review</h2>
<ul>
<li>Preregistration (hashed before any result): <a href="preregistration.md">docs/s27/preregistration.md</a> ·
Run card: <a href="run-card.json">docs/s27/run-card.json</a> ·
Holdout: <a href="holdout.json">docs/s27/holdout.json</a> ·
Canaries: <a href="canaries.json">docs/s27/canaries.json</a> ·
Surface/dot checks: <a href="surface-checks.json">surface</a> / <a href="final-dot-checks.json">dots</a> ·
Emission: <a href="final-emission.json">final-emission.json</a> ·
Diagnostics: <a href="diagnostics.json">diagnostics.json</a> ·
Nine sites: <a href="nine-site-audit.json">nine-site-audit.json</a></li>
<li>Competition problem, metric &amp; format: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">drivendata.org/competitions/306/…/page/967</a> ·
About/references: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">page/968</a> ·
Leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a> ·
Reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">github.com/drivendataorg/gems-prize-reference-solution</a> ·
Official rules PDF (NLR): <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">docs.nlr.gov/docs/fy26osti/96647.pdf</a></li>
<li>GeoDAWN surveys (USGS): <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">usgs.gov</a> ·
INGENIOUS (GBCGE): <a href="https://gbcge.org/current-projects/ingenious/">gbcge.org</a> ·
EPSG:32611: <a href="https://epsg.io/32611">epsg.io/32611</a> ·
Tversky index: <a href="https://en.wikipedia.org/wiki/Tversky_index">en.wikipedia.org</a> ·
USGS 3DEP (next lane's free data): <a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">usgs.gov/3dep</a></li>
<li>Reproduce: <code>python -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt &amp;&amp;
.venv/bin/python scripts/restore_data.py &amp;&amp; PYTHONPATH=src:. .venv/bin/python scripts/run_s27_far.py features &amp;&amp;
PYTHONPATH=src:. .venv/bin/python scripts/run_s27_far.py experiment &amp;&amp;
PYTHONPATH=src:. .venv/bin/python scripts/run_s27_far.py package</code> (runners refuse implicit reruns over recorded receipts).</li>
</ul>

<p><strong>Maximize P(Win) · Own the Outcome.</strong> Negative results are deliverables: this session spent 2 of 3
preregistered experiments and 0 submission slots, fixed competitive-scope uniqueness, and measured — rather than guessed —
the remaining gap to 0.2778.</p>
</main></div></body></html>
"""
    out = ROOT / "docs/s27/executive-summary.html"
    out.write_text(html)
    print("wrote", out)
    # Front door has a single shared owner; re-render it (S27 callout is
    # injected there, fail-closed) so docs/index.html stays reproducible.
    sys.path.insert(0, str(ROOT))
    from scripts.render_olc91_portal import render as render_front_door
    render_front_door()
    print("front door re-rendered via scripts/render_olc91_portal.render")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
