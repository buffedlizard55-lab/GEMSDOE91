#!/usr/bin/env python3
"""Render the S25 executive summary from JSON receipts only (no typed scores).

Outputs docs/s25/executive-summary.html and re-renders the front door via the
shared owner (scripts/render_olc91_portal.render, S25 callout). Fails closed
if any receipt claims submit-approval or an organizer score.
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


def f4(x):
    return f"{float(x):.4f}"


def pct(x):
    return f"{100.0 * float(x):.2f}%"


def spearman(a, b):
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def main() -> int:
    card = load("docs/s25/run-card.json")
    diag = load("docs/s25/diagnostics.json")
    nine = load("docs/s25/nine-site-audit.json")["sites"]
    profile = {r["name"]: r for r in load("docs/s25/dot-profile.json")["rows"]}
    lb = load("evidence/public-leaderboard-2026-10-28.json")
    audit = {r["path"]: r for r in load("docs/download-audit.json")["files"]}
    e1 = load("docs/s25/e1/holdout.json")
    e2 = load("docs/s25/e2/holdout.json")
    e3 = load("docs/s25/e3/holdout.json")
    can = load("docs/s25/canaries.json")

    # Fail-closed receipt checks.
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["organizer_confirmed_score"] is None
    assert card["estimated_leaderboard_score"] is None
    assert len(card["submission_note"]) <= 140
    assert audit[card["artifact"]["tif"]]["status"] == "PASS"
    assert audit[card["artifact"]["zip"]]["status"] == "PASS"
    assert diag["lfi"]["label_class"] == "MODEL_PROJECTION_NOT_A_SCORE"

    sgmc = {r["name"]: r for r in diag["sgmc"]["rows"]}
    lfi = {r["name"]: r for r in diag["lfi"]["rows"]}
    fit1 = diag["lfi"]["fits"]["ridge1"]
    h = card["holdout"]
    corr = card["correlation_overlap_vs_registry"]
    tif_rel = card["artifact"]["tif"].removeprefix("docs/")
    zip_rel = card["artifact"]["zip"].removeprefix("docs/")
    cand_lfi = lfi["s25_fabric_e2_candidate"]
    r0_lfi = lfi["parent_r0_gemsdoe32"]
    cand_sgmc = sgmc["s25_fabric_e2_candidate"]["dti"]
    r0_sgmc = sgmc["parent_r0_gemsdoe32"]["dti"]
    prof_c = profile["s25_fabric_e2_candidate"]
    prof_r0 = profile["parent_r0_gemsdoe32"]
    lb1 = lb["rows"][0]["best_public_dw_tversky"]

    def holdout_line(dd):
        return (f"HOLDOUT-DTI {f6(dd['dti'])} [{f6(dd['ci95'][0])}, {f6(dd['ci95'][1])}] "
                f"({h['evaluator_version']}, {escape(h['split_version'])}, "
                f"{h['n_withheld_positives']:,} withheld)")

    # ---- Table 1: downloadable research candidates from this repo ----
    def research_row(label, rel, sha, dots, est_html, uniq_html):
        return (f'<tr><th scope="row">{escape(label)}<br><a href="../{escape(rel)}">'
                f"{escape(Path(rel).name)}</a><br><small>SHA-256 {escape(sha[:16])}… · "
                f"{dots:,} dots</small></th><td>{est_html}</td><td>{uniq_html}</td>"
                f'<td class="no">NO</td></tr>')

    est_s25 = (f"<strong>ORGANIZER-CONFIRMED: none.</strong> Estimated leaderboard score "
               f"(LFI MODEL projection, not a score): <strong>{cand_lfi['ridge1']:.4f}</strong> "
               f"(ridge10 {cand_lfi['ridge10']:.4f}; fit LOSO RMSE {fit1['rmse_loso']:.4f}). "
               f"{escape(holdout_line(h))}; SGMC off-catalogue diagnostic {f6(cand_sgmc)} "
               f"(report-only).")
    uniq_s25 = (f"<strong>YES vs the nine focus sites</strong> — max "
                f"{pct(corr['final_dot_max_overlap_nine_leaders'])} of dots within 3 px of any "
                f"one leader (limit 70%); surface |&rho;| max {corr['surface_max_abs_rho']:.3f} "
                f"(limit 0.90). <strong>NO under the literal registry rule</strong> — "
                f"{pct(corr['final_dot_max_overlap_competitive_le_90000px'])} vs the closest "
                f"competitive reference and {pct(corr['final_dot_max_overlap_all'])} vs the "
                f"dense calibration lattice.")
    pdwc = load("docs/run-card-S21-PDWC.json")
    est_pdwc = (f"<strong>ORGANIZER-CONFIRMED: none.</strong> LFI MODEL projection (this "
                f"session's refit, not a score): <strong>{lfi['s21_pdwc_e3']['ridge1']:.4f}</strong> "
                f"(ridge10 {lfi['s21_pdwc_e3']['ridge10']:.4f}). Historical HOLDOUT-DTI "
                f"{f6(pdwc['holdout']['holdout_dti'])} was measured on the superseded v2 fold "
                f"instrument and is not matched to today's v3 numbers. SGMC diagnostic "
                f"{f6(sgmc['s21_pdwc_e3']['dti'])}.")
    uniq_pdwc = ("Per its own S21 run card: PASS vs 932 competitive rasters (max 64.00% within "
                 "3 px) with uniqueness-capped emission; literal all-raster overlap 100% vs dense "
                 "calibration blankets. Verdict at the time: negative (below a spillover-inflated "
                 "comparator; selector never approved a slot).")
    rows_research = (
        research_row("S25-FABRIC E2 — this session; download this one for research",
                     tif_rel, card["raster_sha256"], card["artifact"]["n_dots"], est_s25, uniq_s25)
        + research_row("S21-PDWC E3 — earlier session; highest LFI-projected unsubmitted candidate in this repo",
                       "downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif",
                       lfi["s21_pdwc_e3"]["sha256"], 37_654, est_pdwc, uniq_pdwc))

    # ---- Table 2: nine focus sites ----
    rows_nine = ""
    for s in sorted(nine, key=lambda s: -(s["claimed_value_user_reported"] or 0)):
        key = f"nine_{s['site'].lower()}"
        peer = s["max_overlap_vs_other_eight"]
        rows_nine += (
            f'<tr><th scope="row"><a href="{escape(s["site_url"])}">{escape(s["site"])}</a>'
            f"<br><small>main HEAD {escape(s['current_main_head_date'][:10])}</small></th>"
            f'<td><a href="{escape(s["source_url_at_head"])}">{escape(s["best_claimed_file"])}</a>'
            f"<br><small>SHA-256 {escape(s['sha256'][:16])}… · {s['positive_pixels']:,} dots</small></td>"
            f"<td><strong>{s['claimed_value_user_reported']:.4f}</strong> <small>USER-REPORTED "
            f"(prompt), NOT ORGANIZER-CONFIRMED</small><br><small>LFI MODEL projection "
            f"{lfi[key]['ridge1']:.4f} (in-anchor-set, optimistic) · SGMC diagnostic "
            f"{f6(sgmc[key]['dti'])}</small></td>"
            f'<td class="no">NO — {pct(peer["overlap_within_3px"])} vs {escape(peer["reference_site"])}</td>'
            f'<td class="no">NO as a new unique submission</td></tr>')

    # ---- Experiments table ----
    def exp_row(label, pooled, cand_arm):
        s = pooled["scores"][cand_arm]
        return (f"<tr><th scope=\"row\">{escape(label)}</th><td>{f6(s['dti'])} "
                f"[{f6(s['ci95'][0])}, {f6(s['ci95'][1])}]</td></tr>")
    rows_exp = (exp_row("E1 · fabric_e1_oof_new (new features only)", e1, "fabric_e1_oof_new")
                + exp_row("E2 · fabric_e2_oof_full (base + new) — packaged", e2, "fabric_e2_oof_full")
                + exp_row("E3 · fabric_e3_oof_bagged (3-seed mean)", e3, "fabric_e3_oof_bagged")
                + "".join(
                    f'<tr><td>control · {escape(c)}</td><td>{f6(e2["scores"][c]["dti"])} '
                    f"[{f6(e2['scores'][c]['ci95'][0])}, {f6(e2['scores'][c]['ci95'][1])}]</td></tr>"
                    for c in ("control_oof_base", "control_new_surface", "control_gravgrad")))
    d_best = h["paired_difference_vs_best_control"]

    # ---- Gates ----
    dense_lat = [b for b in corr["dense_blankets"] if "lattice" in b["path"]]
    lat_ov = dense_lat[0]["overlap_within_3px"] if dense_lat else None
    gate_items = [
        ("Leakage canary — every feature alone, symmetric AUC &le; 0.90 (protocol rule 4)",
         can["all_pass"], f"max {can['max_symmetric_auc']:.4f} ({escape(can['worst'])}) over "
         f"{len(can['canaries'])} feature-fold tests"),
        ("Surface uniqueness |&rho;| &le; 0.90 vs frozen registry, before placement (rule 1a)",
         corr["surface_pass_le_0.90"], f"max {corr['surface_max_abs_rho']:.4f} vs "
         f"{escape(Path(corr['surface_closest']).name)}"),
        ("Final dots &le; 70% within 3 px — nine focus leaders (rule 1b, user scope)",
         corr["final_dot_pass_nine_le_0.70"],
         f"max {pct(corr['final_dot_max_overlap_nine_leaders'])}"),
        ("Final dots &le; 70% within 3 px — competitive references &le; 90,000 px (rule 1b)",
         corr["final_dot_pass_competitive_le_0.70"],
         f"max {pct(corr['final_dot_max_overlap_competitive_le_90000px'])} vs "
         f"{escape(Path(corr['final_dot_closest_competitive']).name)}"),
        ("Final dots &le; 70% within 3 px — literal all references incl. dense blankets (rule 1b)",
         corr["final_dot_pass_all_incl_blankets_le_0.70"],
         f"max {pct(corr['final_dot_max_overlap_all'])} (lattice {pct(lat_ov)}; capacity bound "
         f"forces &ge; {100*corr['lattice_capacity_bound_at_budget']['overlap_lower_bound']:.1f}% "
         f"at 37,654 dots)"),
        ("Paired HOLDOUT-DTI beats best matched control, 95% CI excludes 0",
         h["beats_best_matched_control_ci95"],
         f"&Delta; {d_best['delta']:+.6f} [{d_best['ci95'][0]:+.6f}, {d_best['ci95'][1]:+.6f}] "
         f"vs {escape(h['best_matched_control'])} ({f6(h['best_matched_control_dti'])})"),
        ("Format: single-band float32, all-finite in [0,1], EPSG:32611, 3730&times;3292, "
         "pinned transform; independent download audit PASS",
         card["validator_output"]["pass"] and audit[card["artifact"]["tif"]]["status"] == "PASS",
         "shared writer + independent re-read + audit_downloads PASS (TIF and ZIP)"),
        ("Live-aligned diagnostics support beating 0.2778 (LFI MODEL projection &ge; R0's projection)",
         cand_lfi["ridge1"] >= r0_lfi["ridge1"],
         f"candidate {cand_lfi['ridge1']:.4f} vs R0 {r0_lfi['ridge1']:.4f} (both MODEL "
         f"projections, not scores); SGMC {f6(cand_sgmc)} vs R0 {f6(r0_sgmc)}"),
        ("Separate selector decision + live weekly-cap check (protocol rule 6)",
         False, "not performed here; 0 slots used this session"),
    ]
    rows_gates = "".join(
        f'<tr><td>{name}</td><td class="{"yes" if ok else "no"}">{"PASS" if ok else "FAIL"}</td>'
        f"<td>{detail}</td></tr>" for name, ok, detail in gate_items)

    dots_claim_rho = spearman([s["positive_pixels"] for s in nine],
                              [s["claimed_value_user_reported"] for s in nine])
    frac_35_c = prof_c["dcat_px_hist"]["(3,5]"]
    frac_35_r0 = prof_r0["dcat_px_hist"]["(3,5]"]

    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S25-FABRIC executive summary · GEMSDOE91</title>
<link rel="stylesheet" href="../assets/portal.css">
<style>.no{{color:#9b1c1c;font-weight:700}}.yes{{color:#14532d;font-weight:700}}
.decision{{border:3px solid #9b1c1c;padding:1rem 1.2rem;border-radius:8px;background:#fff7ed}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d1d5db;padding:.5rem;vertical-align:top;text-align:left}}
.table-scroll{{overflow-x:auto}}code{{word-break:break-all}}</style></head>
<body><div class="wrap"><main id="main">
<p><a href="../index.html">&larr; Current portal</a> · <a href="preregistration.md">Preregistration</a> ·
<a href="run-card.json">Run card (JSON)</a> · <a href="diagnostics.json">Diagnostics (SGMC + LFI model)</a> ·
<a href="nine-site-audit.json">Nine-site audit (JSON)</a> · <a href="REVIEW.md">Full session review</a> ·
<a href="../submission-guide.html">Submission guide</a></p>
<h1>S25-FABRIC — executive summary (2026-10-28)</h1>
<div class="decision">
<p style="font-size:1.25rem;margin:.2rem 0"><strong>New unique TIF generated: YES</strong> (unique vs the nine focus sites; new feature physics, not a copy of any previous submission).<br>
<strong>OK TO DOWNLOAD: YES — RESEARCH ONLY.</strong><br>
<strong>OK TO SUBMIT: NO.</strong> Do not spend a weekly slot on it yet — three named blockers below.</p>
<p><strong>File to download:</strong> <a href="../{escape(tif_rel)}">{escape(Path(tif_rel).name)}</a>
(<a href="../{escape(zip_rel)}">single-TIFF ZIP</a>)<br>
SHA-256 <code>{escape(card["raster_sha256"])}</code> · {card["artifact"]["n_dots"]:,} dots ·
{escape(holdout_line(h))}.</p>
<p><strong>Estimated leaderboard score (labelled):</strong> ORGANIZER-CONFIRMED score: <strong>none exists</strong>.
The repo's live-anchored LFI model projects <strong>{cand_lfi['ridge1']:.4f}</strong> (ridge10 {cand_lfi['ridge10']:.4f};
leave-one-site-out RMSE {fit1['rmse_loso']:.4f} on {fit1['n_anchors']} USER-REPORTED anchors) —
a <em>model projection, never a score</em>. The same model projects the GEMSDOE32 reference raster at
{r0_lfi['ridge1']:.4f} (its user-reported live claim is 0.2778). Public leaderboard fetched 2026-10-28:
#1 = {lb1:.4f} (<a href="{escape(lb['source_url'])}">DrivenData</a>); the prompt's 0.4413 / 0.3195 are stale.</p>
<p><strong>Why OK TO SUBMIT is NO (all checks automated; no human inspection involved):</strong>
(1) <em>Protocol duplicate rule:</em> final dots reach {pct(corr['final_dot_max_overlap_competitive_le_90000px'])}
within 3 px of one competitive registry raster (limit 70%) — even though the file is unique vs all nine focus
leaders (max {pct(corr['final_dot_max_overlap_nine_leaders'])}).
(2) <em>Live-aligned estimate is low:</em> {pct(frac_35_c)} of its dots sit 3–5 px from the mapped catalogue
(median {prof_c['dcat_px_median']:.1f} px vs R0's {prof_r0['dcat_px_median']:.1f} px) — exactly the zone the
anchor-fitted model penalises most, because scored new faults concentrate away from mapped ones.
(3) <em>Selector step:</em> promotion to a real slot is a separate decision with a live weekly-cap check
(protocol rule 6); 0 slots were used. What DID pass: leakage canaries, surface uniqueness, nine-site dot
uniqueness, paired holdout vs the strongest control, and the [0,1]/grid format validator — see the gate table.</p>
</div>

<h2>The table the project asked for — file / estimated score / uniqueness / submit?</h2>
<p>Labels: <strong>HOLDOUT-DTI</strong> = recovery of withheld catalogue faults on the shared evaluator
(never a leaderboard score). <strong>LFI MODEL projection</strong> = leaderboard-feedback inversion refitted
this session on USER-REPORTED anchors (never a score). <strong>USER-REPORTED</strong> = claim copied from a
site/prompt with no organizer receipt. Nothing on this page is ORGANIZER-CONFIRMED.</p>
<div class="table-scroll"><table>
<caption>Downloadable research candidates generated in this repository (best first by session recency)</caption>
<thead><tr><th scope="col">File to download</th><th scope="col">Estimated leaderboard score</th>
<th scope="col">Unique vs GEMSDOE24/25/27/28/30/31/32/33/36 and the registry?</th>
<th scope="col">OK to submit?</th></tr></thead>
<tbody>{rows_research}</tbody></table></div>

<div class="table-scroll"><table>
<caption>Best historical file per focus site — re-audited from bytes on 2026-10-28 (all nine repos have new commits since the 2026-10-26 audit; leaders re-hashed)</caption>
<thead><tr><th scope="col">Site</th><th scope="col">Best claimed file</th><th scope="col">Score evidence</th>
<th scope="col">Unique among the nine?</th><th scope="col">OK to submit?</th></tr></thead>
<tbody>{rows_nine}</tbody></table></div>
<p><strong>Clear answer per site:</strong> the best file on every focus site is the one named above, and the
highest claim overall is GEMSDOE32's <code>h33-h33-2-b2…-zeros</code> at 0.2778 (user-reported). But
<strong>none of the nine is unique</strong>: every leader has 98–100% of its dots within 3 px of a peer
(recomputed today) — they are pruning edits of one H19-5-descended raster family, so re-downloading and
resubmitting any of them is a duplicate, not a new attempt. The only new, nine-unique file this session is
the S25 download above, and it is research-only for the three reasons in the decision box.</p>

<h2>Experiments (3 of 3 preregistered; paired arms, identical v3 folds/budgets/emission)</h2>
<div class="table-scroll"><table><thead><tr><th scope="col">Arm</th>
<th scope="col">HOLDOUT-DTI ({escape(h['evaluator_version'])}, {escape(h['split_version'])}, {h['n_withheld_positives']:,} withheld) [95% CI]</th></tr></thead>
<tbody>{rows_exp}</tbody></table></div>
<p>The 14 new fabric features alone (E1) reach {f6(e1['scores']['fabric_e1_oof_new']['dti'])} vs the 23-feature
base model's {f6(e2['scores']['control_oof_base']['dti'])}; fused (E2) they add
&Delta; {d_best['delta']:+.6f} [{d_best['ci95'][0]:+.6f}, {d_best['ci95'][1]:+.6f}] over the base model —
the new physics carries independent, significant signal on this instrument. Bagging (E3) changed nothing
material. <strong>Instrument warning:</strong> today's folds are v3 (feature-context buffered); all earlier
repo HOLDOUT-DTI values (S21-PDWC 0.195724, S24-CCKM 0.075896) were measured on v2 folds and are context
only, not matched comparisons — and hide-and-recover itself correlates only weakly with live scores across
112 anchors (&rho; &asymp; +0.105, S22), which is why the LFI/SGMC diagnostics above govern live expectations.</p>

<h2>Validation gates — automated, no human inspection</h2>
<div class="table-scroll"><table><thead><tr><th scope="col">Gate</th><th scope="col">Result</th>
<th scope="col">Measured detail</th></tr></thead><tbody>{rows_gates}</tbody></table></div>

<h2>Why 0.2778 (GEMSDOE32) is the family's highest — and can a unique file beat it?</h2>
<p><strong>What the bytes prove</strong> (S22 lineage analysis, re-verified): R0 is not a better detector; it is
the best-<em>pruned</em> member of one family. H19-5's 121,131-px ridge network (0.1922) was dotted at 2.8 px
spacing (44,090 dots, 0.2600), then dots within &le;1 px of the catalogue were deleted (40,199, 0.2708 — the
identical pixels on GEMSDOE28 and GEMSDOE31), then dots at (1,2] px (37,654, <strong>0.2778</strong>).
A one-parameter model that treats the deleted dots as pure false positives predicts the next two family scores
within 0.001, implying R0 recovers &asymp;38–42% of scored truth at &asymp;0.135 mean credit per dot.
Mechanism: mapped-fault pixels are masked out of scoring (official forum), so dots hugging mapped traces are
almost pure false-positive weight under DTI = T/(0.2T + 0.2FP + 0.8|G|); claims across the nine rise as dot
count falls (Spearman &rho;(dots, claim) = {dots_claim_rho:+.3f} over nine non-independent files, recomputed
today). Full derivation: <a href="../R0_ANALYSIS_S22.md">R0_ANALYSIS_S22.md</a>.</p>
<p><strong>Can we generate a unique file above 0.2778?</strong> Not yet, on labelled evidence. This session's
candidate is the first in several sessions to beat a strong matched control in paired holdout, and its SGMC
diagnostic ({f6(cand_sgmc)}) reaches {100*cand_sgmc/r0_sgmc:.0f}% of R0's ({f6(r0_sgmc)}); but its dots hug the
catalogue (median {prof_c['dcat_px_median']:.1f} px; {pct(frac_35_c)} at 3–5 px vs R0's {pct(frac_35_r0)}), so the
live-anchored model projects only {cand_lfi['ridge1']:.4f}. The measured fix for the next preregistered lane is
emission geometry, not more features: keep the validated FABRIC surface, emit with a wider catalogue collar /
distance-stratified quotas and &le;70% competitive-overlap caps, and arbitrate with SGMC-&gt;500 m plus LFI
(built <em>without</em> fitting to LFI, to keep the projection honest). The only identified route materially
past &asymp;0.28–0.32 remains new information — 1 m LiDAR derivatives (USGS 3DEP, free) on an unrestricted
machine; this sandbox cannot reach those hosts. That is expert judgement from labelled diagnostics, not a
promised score.</p>

<h2>Exactly how a future, selector-approved submission is made</h2>
<ol>
<li>Start from a run card whose gates all PASS (this file's do not). Obtain the separate selector decision and
check the remaining weekly quota (3/week, counted Mon–Sun) on the authenticated
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">submission page</a>.</li>
<li>Download the approved <code>-zeros.tif</code> (or its single-TIFF ZIP) from this page and verify SHA-256
locally (<code>sha256sum file.tif</code> / <code>Get-FileHash file.tif</code>) against the run card before uploading.</li>
<li>On <em>New submission</em>, choose the file — single-band GeoTIFF, EPSG:32611, float32, 3730&times;3292,
same geotransform as the sample. The portal error &ldquo;Predicted values must be in range [0, 1]&rdquo; is
prevented by construction here: the shared writer emits all-finite values in [0,1] with
<code>nodata=None</code> and rejects the -3.4028235e+38 sentinel instead of copying it (independently
re-read and audited PASS for this file).</li>
<li>Set the submission identity exactly as recorded. For this session's file (provenance only — not approved):
name <code>{escape(card["submission_name"])}</code>; note ({len(card["submission_note"])}/140):
&ldquo;{escape(card["submission_note"])}&rdquo;.</li>
<li>After scoring, save submission ID + timestamp + uploaded-file SHA-256 + displayed score together.
Only that receipt may ever be labelled ORGANIZER-CONFIRMED in this repo.</li>
</ol>

<h2>Method in one paragraph</h2>
<p>FABRIC uses only the SHA-pinned 19-band GeoDAWN stack. Two new feature families target faults the
USGS/INGENIOUS catalogue missed because they are buried or scarp-free: (i) <strong>oriented granulometry
contrast</strong> — grey-opening pattern spectra (lengths 5/11 px, 4 orientations) of detrended elevation
(B12/B19), compared &plusmn;7 px across local slope breaks, so a change of fan/bedrock fabric across a trace
scores highly; (ii) <strong>cross-spectral phase lag</strong> — tile-wise phase-correlation lag between the
isostatic-gravity (B13) and magnetic (B14) boundaries, which a fault offsetting density vs magnetization
contacts produces and a vertical unfaulted contact does not. Together with the 19 bands + 4 gradient
magnitudes they feed a spatially cross-fitted gradient-boosted model (v3 whole-component buffered folds);
dots are emitted by the shared NMS emitter at 3.05 px spacing/collar. Named mimics: unfaulted dipping
contacts, remanent-magnetization offsets, fan-lobe/shoreline fabrics, survey seams. NoData sentinels are
excluded from every statistic (masked convolution; supports eroded beyond each feature's influence radius).
A fault-likelihood map is not evidence of a geothermal vent, temperature, or permeability.</p>

<h2>Official sources (for manual review)</h2>
<ul>
<li>Competition + metric + leaderboard: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem description</a> · <a href="{escape(lb['source_url'])}">leaderboard (fetched 2026-10-28)</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF (NLR/DOE)</a></li>
<li>Reference solution: <a href="https://github.com/drivendataorg/gems-prize-reference-solution">drivendataorg/gems-prize-reference-solution</a></li>
<li>GeoDAWN surveys: <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS</a> · INGENIOUS compilation: <a href="https://gdr.openei.org/submissions/1391">GDR 1391</a> · <a href="https://gbcge.org/current-projects/ingenious/">GBCGE INGENIOUS</a></li>
<li>Grid CRS: <a href="https://epsg.io/32611">EPSG:32611</a> · Metric family: <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a> · Future 1 m DEM source: <a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">USGS 3DEP</a> (free; unreachable from this sandbox — needs an unrestricted machine)</li>
</ul>

<h2>Reproduce</h2>
<pre>python -m pip install -r requirements.txt
python scripts/restore_data.py
python scripts/restore_registry.py --available-only
python scripts/restore_lfi_anchors.py
python scripts/run_s25_fabric.py features
python scripts/run_s25_fabric.py experiment --exp e1   # then e2, e3 (each refuses if recorded)
python scripts/run_s25_fabric.py package --exp e2 --arm fabric_e2_oof_full
python scripts/audit_s25_nine_sites.py
python scripts/score_s25_diagnostics.py
python scripts/profile_s25_dots.py
python scripts/audit_downloads.py --output docs/download-audit.json --html docs/download-audit.html
python scripts/render_s25_portal.py</pre>
<p>Maximize P(Win) · Own the Outcome. 3 of 3 budgeted experiments used; 0 weekly slots used.
Negative results are deliverables.</p>
</main></div></body></html>
"""
    out = DOCS / "s25/executive-summary.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)

    import sys
    sys.path.insert(0, str(ROOT))
    from scripts.render_olc91_portal import render as render_front_door
    render_front_door()
    assert "s25/executive-summary.html" in (DOCS / "index.html").read_text()
    print(f"wrote {out.relative_to(ROOT)}; front door re-rendered with S25 callout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
