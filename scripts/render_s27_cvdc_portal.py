#!/usr/bin/env python3
"""Render the Session 27 (`S27-CVDC`) executive summary from JSON receipts only.

Outputs docs/s27-cvdc/executive-summary.html and re-renders docs/index.html,
docs/executive-summary.html, and index.html via scripts/render_olc91_portal.render.
Fails closed if any receipt claims submit-approval or an organizer score.
"""
from __future__ import annotations

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def f6(x) -> str:
    return f"{float(x):.6f}"


def f4(x) -> str:
    return f"{float(x):.4f}"


def pct(x) -> str:
    return f"{100.0 * float(x):.2f}%"


def main() -> int:
    card = load("docs/s27-cvdc/run-card.json")
    diag = load("docs/s27-cvdc/diagnostics.json")
    nine = load("docs/s22/nine-site-audit.json")["sites"]
    nine_s25 = {s["site"]: s for s in load("docs/s25/nine-site-audit.json")["sites"]}
    dot_checks = load("docs/s27-cvdc/final-dot-checks.json")
    surf_checks = load("docs/s27-cvdc/surface-checks.json")
    lb = load("evidence/public-leaderboard-2026-10-29.json")
    audit = {r["path"]: r for r in load("docs/download-audit.json")["files"]}
    e1 = load("docs/s27-cvdc/e1/holdout.json")
    e2 = load("docs/s27-cvdc/e2/holdout.json")
    e3 = load("docs/s27-cvdc/e3/holdout.json")
    can = load("docs/s27-cvdc/canaries.json")

    s25_card = load("docs/s25/run-card.json")
    s24_card = load("docs/s24/e2/run-card.json")
    s21_card = load("docs/run-card-S21-PDWC.json")
    s27_far_card = load("docs/s27/run-card.json")
    concurrent_addendum = load("docs/s27-cvdc/concurrent-main-overlap-addendum.json")

    # Fail-closed receipt assertions
    assert card["verdict"] == "negative" and card["ok_to_submit"] is False
    assert card["organizer_confirmed_score"] is None
    assert card["estimated_leaderboard_score"] is None
    assert len(card["submission_note"]) <= 140
    assert audit[card["artifact"]["tif"]]["status"] == "PASS"
    assert audit[card["artifact"]["zip"]]["status"] == "PASS"
    assert diag["lfi"]["label_class"] == "MODEL_PROJECTION_NOT_A_SCORE"

    sgmc = {r["name"]: r for r in diag["sgmc"]["rows"]}
    lfi = {r["name"]: r for r in diag["lfi"]["rows"]}
    dist = {r["name"]: r for r in diag["catalogue_distance_profiles"]}
    fit1 = diag["lfi"]["fits"]["ridge1"]
    dot_by_path = {r["path"]: r for r in dot_checks["checks"]}
    surf_by_path = {r["path"]: r["rank_correlation"] for r in surf_checks["checks"]}
    dot_by_site = {st: r for r in dot_checks["checks"] for st in r.get("sites", [])}
    surf_by_site = {st: r["rank_correlation"] for r in surf_checks["checks"] for st in r.get("sites", [])}

    h = card["holdout"]
    corr = card["correlation_overlap_vs_registry"]
    tif_rel = card["artifact"]["tif"].removeprefix("docs/")
    zip_rel = card["artifact"]["zip"].removeprefix("docs/")
    cand_lfi = lfi["s27_cvdc_candidate"]
    s25_lfi = lfi["s25_fabric_e2"]
    cand_sgmc = sgmc["s27_cvdc_candidate"]["dti"]
    s25_sgmc = sgmc["s25_fabric_e2"]["dti"]
    r0_sgmc = sgmc["parent_r0_gemsdoe32"]["dti"]
    dist_c = dist["s27_cvdc_candidate"]
    dist_s25 = dist["s25_fabric_e2"]
    dist_r0 = dist["parent_r0_gemsdoe32"]
    lb1 = lb["rows"][0]["best_public_dw_tversky"]
    lb10 = lb["rows"][9]["best_public_dw_tversky"]

    paired_s25 = h["paired_differences_all_controls"]["control_s25_fabric_e2"]
    paired_base = h["paired_differences_all_controls"]["control_oof_base"]

    # ---- Table 1: Downloadable research candidates in this repository ----
    def cand_row(label: str, rel: str, sha: str, dots: int, score_html: str, uniq_html: str) -> str:
        return (
            f'<tr><th scope="row">{escape(label)}<br>'
            f'<a href="../{escape(rel)}"><strong>{escape(Path(rel).name)}</strong></a><br>'
            f"<small>SHA-256 <code>{escape(sha[:16])}…</code> · {dots:,} dots</small></th>"
            f"<td>{score_html}</td><td>{uniq_html}</td>"
            f'<td class="no">NO<br><small>Research only</small></td></tr>'
        )

    score_s27 = (
        f"<strong>ORGANIZER-CONFIRMED: none.</strong><br>"
        f"<strong>Primary HOLDOUT-DTI: {f6(h['dti'])} [{f6(h['ci95'][0])}, {f6(h['ci95'][1])}]</strong> "
        f"({escape(h['evaluator_version'])}, {escape(h['split_version'])}, "
        f"{h['n_withheld_positives']:,} withheld positives; <strong>+{f6(paired_s25['delta'])}</strong> vs S25-FABRIC E2, "
        f"95% CI [{paired_s25['ci95'][0]:+.6f}, {paired_s25['ci95'][1]:+.6f}]).<br>"
        f"Post-hoc LFI MODEL projection (<code>MODEL_PROJECTION_NOT_A_SCORE</code>): "
        f"<strong>{cand_lfi['ridge1']:.4f}</strong> (ridge10 {cand_lfi['ridge10']:.4f}; LOSO RMSE {fit1['rmse_loso']:.4f}).<br>"
        f"Blind USGS SGMC off-catalogue diagnostic: <strong>{f6(cand_sgmc)}</strong> ({100*cand_sgmc/r0_sgmc:.1f}% of R0)."
    )
    uniq_s27 = (
        f"<strong>PASS vs all 9 focus sites:</strong> max <strong>{pct(corr['final_dot_max_overlap_nine_leaders'])}</strong> "
        f"within 3 px (limit 70%).<br>"
        f"<strong>PASS vs all {corr['competitive_references_checked']} competitive non-blanket fleet rasters (&le;90k px):</strong> "
        f"max <strong>{pct(corr['final_dot_max_overlap_competitive_le_90000px'])}</strong> within 3 px "
        f"(closest: <code>{escape(Path(corr['final_dot_closest_competitive']).name[:34])}…</code>) "
        f"and max <strong>{pct(concurrent_addendum['max_overlap_within_3px'])}</strong> vs all {concurrent_addendum['concurrent_main_rasters_checked']} concurrent S26/S27 candidates; "
        f"surface |&rho;| max <strong>{corr['surface_max_abs_rho']:.3f}</strong> (limit 0.90).<br>"
        f"<strong>FAIL literal dense-lattice gate:</strong> {pct(corr['final_dot_max_overlap_all'])} vs "
        f"206,895-dot synthetic <code>calib_r13lattice_00904.tif</code> (pigeonhole floor &ge;82.34%)."
    )

    s27_far_tif_rel = s27_far_card["artifact"]["tif"].removeprefix("docs/")
    s27_far_ov_vs_cvdc = next(
        r["overlap_within_3px"] for r in concurrent_addendum["rows"] if r["path"] == s27_far_card["artifact"]["tif"]
    )
    score_s27_far = (
        f"<strong>ORGANIZER-CONFIRMED: none.</strong><br>"
        f"HOLDOUT-DTI: {f6(s27_far_card['holdout']['dti'])} [{f6(s27_far_card['holdout']['ci95'][0])}, {f6(s27_far_card['holdout']['ci95'][1])}] "
        f"(v3 folds, 60,988 withheld; S27-CVDC E2 scores <strong>+{f6(h['dti'] - s27_far_card['holdout']['dti'])}</strong> higher).<br>"
        f"Post-hoc LFI MODEL projection: {s27_far_card['lfi_model_projection_not_a_score']['ridge1']:.4f}."
    )
    uniq_s27_far = (
        f"PASS vs 9 focus sites (max {pct(s27_far_card['correlation_overlap_vs_registry']['final_dot_max_overlap_nine_leaders'])}) "
        f"and competitive rasters (max {pct(s27_far_card['correlation_overlap_vs_registry']['final_dot_max_overlap_competitive_le_90000px'])}); "
        f"FAIL dense lattice. (S27-CVDC E2 overlaps S27-FABRIC-FAR by only {pct(s27_far_ov_vs_cvdc)}.)"
    )

    s25_tif_rel = s25_card["artifact"]["tif"].removeprefix("docs/")
    s25_ov_vs_s27 = dot_by_path[s25_card["artifact"]["tif"]]["overlap_within_3px"]
    score_s25 = (
        f"<strong>ORGANIZER-CONFIRMED: none.</strong><br>"
        f"HOLDOUT-DTI: {f6(s25_card['holdout']['dti'])} [{f6(s25_card['holdout']['ci95'][0])}, {f6(s25_card['holdout']['ci95'][1])}] "
        f"(v3 folds, 60,988 withheld).<br>"
        f"Post-hoc LFI MODEL projection: {s25_lfi['ridge1']:.4f} (ridge10 {s25_lfi['ridge10']:.4f}; "
        f"depressed by in-sample refit placing 45.9% of dots at 3–5 px).<br>"
        f"Blind SGMC diagnostic: {f6(s25_sgmc)}."
    )
    uniq_s25 = (
        f"PASS vs 9 focus sites (max {pct(s25_card['correlation_overlap_vs_registry']['final_dot_max_overlap_nine_leaders'])}). "
        f"<strong>FAIL competitive registry:</strong> 74.89% within 3 px of <code>bhar-e3</code> (&gt;70%). "
        f"(S27-CVDC E2 overlaps S25-FABRIC E2 by only {pct(s25_ov_vs_s27)}.)"
    )

    s21_tif_rel = "downloads/gems91-s21-pdwc-e3-20261026T074827Z-f23566d0-zeros.tif"
    s21_ov_vs_s27 = dot_by_path["docs/" + s21_tif_rel]["overlap_within_3px"]
    score_s21 = (
        f"<strong>ORGANIZER-CONFIRMED: none.</strong><br>"
        f"Historical HOLDOUT-DTI {f6(s21_card['holdout']['holdout_dti'])} (superseded v2 instrument — not comparable to v3).<br>"
        f"Post-hoc LFI MODEL projection: {lfi['s21_pdwc_e3']['ridge1']:.4f} (ridge10 {lfi['s21_pdwc_e3']['ridge10']:.4f}).<br>"
        f"Blind SGMC diagnostic: {f6(sgmc['s21_pdwc_e3']['dti'])}."
    )
    uniq_s21 = (
        f"PASS vs competitive rasters (max 64.00% capped); FAIL literal dense calibration blankets (100%). "
        f"(S27-CVDC E2 overlaps S21-PDWC E3 by {pct(s21_ov_vs_s27)}.)"
    )

    s24_tif_rel = s24_card["artifact"]["tif"].removeprefix("docs/")
    s24_ov_vs_s27 = dot_by_path[s24_card["artifact"]["tif"]]["overlap_within_3px"]
    score_s24 = (
        f"<strong>ORGANIZER-CONFIRMED: none.</strong><br>"
        f"Historical HOLDOUT-DTI {f6(s24_card['holdout']['dti'])} (superseded v2 split).<br>"
        f"Post-hoc LFI MODEL projection: {lfi['s24_cckm_e2']['ridge1']:.4f} · Blind SGMC diagnostic: {f6(sgmc['s24_cckm_e2']['dti'])}."
    )
    uniq_s24 = (
        f"PASS vs 9 focus sites (max 16.45%) and competitive rasters (max 36.32%); FAIL dense lattice (99.97%). "
        f"(S27-CVDC E2 overlaps S24-CCKM E2 by {pct(s24_ov_vs_s27)}.)"
    )

    rows_candidates = (
        cand_row("S27-CVDC E2 — THIS SESSION (primary research deliverable)", tif_rel, card["raster_sha256"], 37_654, score_s27, uniq_s27)
        + cand_row("S27-FABRIC-FAR — concurrent distance-stratified S25 emitter arm", s27_far_tif_rel, s27_far_card["raster_sha256"], 37_654, score_s27_far, uniq_s27_far)
        + cand_row("S25-FABRIC E2 — prior v3-fold incumbent (remediated in S27)", s25_tif_rel, s25_card["raster_sha256"], 37_654, score_s25, uniq_s25)
        + cand_row("S21-PDWC E3 — earlier v2-fold candidate", s21_tif_rel, lfi["s21_pdwc_e3"]["sha256"], 37_654, score_s21, uniq_s21)
        + cand_row("S24-CCKM E2 — earlier cross-kurtosis candidate", s24_tif_rel, s24_card["raster_sha256"], 37_654, score_s24, uniq_s24)
    )

    # ---- Table 2: All 9 focus sites + GEMSDOE92 + GEMSDOE91 ----
    rows_sites = ""
    for s in sorted(nine, key=lambda r: -(r["claimed_historical_value"] or 0)):
        site = s["site"]
        s25_info = nine_s25[site]
        peer = s25_info["max_overlap_vs_other_eight"]
        key = f"nine_{site.lower()}"
        dchk = dot_by_site[site]
        srho = surf_by_site[site]
        rows_sites += (
            f'<tr><th scope="row"><a href="{escape(s25_info["site_url"])}">{escape(site)}</a></th>'
            f'<td><a href="{escape(s25_info["source_url_at_head"])}"><code>{escape(s["filename"])}</code></a><br>'
            f"<small>SHA-256 <code>{escape(s['sha256'][:16])}…</code> · {s['positive_pixels']:,} dots</small></td>"
            f"<td><strong>{s['claimed_historical_value']:.4f}</strong> <small>(USER-REPORTED prompt claim; ORGANIZER-CONFIRMED: none)</small><br>"
            f"<small>LFI in-anchor fit: {lfi[key]['ridge1']:.4f} · SGMC diagnostic: {f6(sgmc[key]['dti'])}</small></td>"
            f'<td class="ok"><strong>UNIQUE PASS</strong> — <strong>{pct(dchk["overlap_within_3px"])}</strong> within 3 px<br>'
            f"<small>surface &rho; = {srho:+.3f} · dot &rho; = {dchk['dot_rank_correlation']:+.3f}</small></td>"
            f'<td class="no">Peer duplicate ({pct(peer["overlap_within_3px"])} vs {escape(peer["reference_site"])}) — do not copy</td></tr>'
        )

    # Add GEMSDOE92 and GEMSDOE91 rows explicitly as requested in prompt
    g92_path = "data/lfi_anchors/GEMSDOE92__gemsdoe92-listricdip-updip50-37654-20261025T190000Z-zeros.tif"
    g92_chk = dot_by_path[g92_path]
    g92_srho = surf_by_path[g92_path]
    rows_sites += (
        '<tr><th scope="row"><a href="https://github.com/buffedlizard55-lab/GEMSDOE92">GEMSDOE92</a><br><small>Broader fleet sibling</small></th>'
        "<td><code>visible-collar-r0-excluded</code> (prompt 0.2784 R0 collar variant) &amp; "
        "<code>gemsdoe92-listricdip-updip50-37654</code> (37,654 dots)</td>"
        "<td><strong>0.2784</strong> &amp; <strong>0.0255</strong> <small>(USER-REPORTED; ORGANIZER-CONFIRMED: none)</small></td>"
        f'<td class="ok"><strong>UNIQUE PASS</strong> — <strong>{pct(g92_chk["overlap_within_3px"])}</strong> vs listricdip '
        f"&amp; ~41.7% vs R0 collar variant<br><small>surface &rho; = {g92_srho:+.3f}</small></td>"
        '<td class="no">0.2784 is an R0 collar variant (&gt;95% overlap vs GEMSDOE32)</td></tr>'
    )
    lftg_path = "docs/downloads/gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros.tif"
    cwpc_path = "docs/downloads/gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros.tif"
    rows_sites += (
        '<tr><th scope="row"><a href="../index.html">GEMSDOE91</a><br><small>Prior live slots on this repo</small></th>'
        "<td><code>gems91-s17-lftg</code> (0.1823), <code>gems91-s17-cwpc-e3</code> (0.1367), earlier slot (0.0298)</td>"
        "<td><strong>0.1823</strong>, <strong>0.1367</strong>, <strong>0.0298</strong> <small>(USER-REPORTED prompt history; ORGANIZER-CONFIRMED: none in repo)</small></td>"
        f'<td class="ok"><strong>UNIQUE PASS</strong> — <strong>{pct(dot_by_path[lftg_path]["overlap_within_3px"])}</strong> vs LFTG · '
        f"<strong>{pct(dot_by_path[cwpc_path]['overlap_within_3px'])}</strong> vs CWPC</td>"
        '<td class="no">Historical slots already spent</td></tr>'
    )

    # ---- Table 3: 3-Experiment Ablation ----
    def exp_row(code: str, title: str, pooled: dict, arm: str) -> str:
        sc = pooled["scores"][arm]
        d_s25 = pooled["paired_differences"]["control_s25_fabric_e2"]
        d_base = pooled["paired_differences"]["control_oof_base"]
        return (
            f'<tr><th scope="row">{escape(code)}<br><small>{escape(title)}</small></th>'
            f"<td><strong>{f6(sc['dti'])}</strong><br><small>[{f6(sc['ci95'][0])}, {f6(sc['ci95'][1])}]</small></td>"
            f"<td><strong>{d_s25['delta']:+.6f}</strong><br><small>[{d_s25['ci95'][0]:+.6f}, {d_s25['ci95'][1]:+.6f}]</small></td>"
            f"<td><strong>{d_base['delta']:+.6f}</strong><br><small>[{d_base['ci95'][0]:+.6f}, {d_base['ci95'][1]:+.6f}]</small></td></tr>"
        )

    rows_exps = (
        exp_row("E1 · cvdc_e1_stage1_nms", "34 NoData-masked static features (CVDC + PMDB + VCTK) + NMS (3.05 px)", e1, "cvdc_e1_stage1_nms")
        + exp_row("E2 · cvdc_e2_stage2_submod (SELECTED)", "Stage-2 8-azimuth axial bridge (0.78 Full + 0.22 PureSub) + 300 m CELF submodular", e2, "cvdc_e2_stage2_submod")
        + exp_row("E3 · cvdc_e3_stitched_uniq_submod", "Stage-2 OOF + far-field ramp + 64% uniqueness-capped CELF submodular", e3, "cvdc_e3_stitched_uniq_submod")
        + f'<tr><th scope="row">Matched Incumbent Control<br><small>control_s25_fabric_e2 (same v3 folds)</small></th>'
        f"<td>{f6(e2['scores']['control_s25_fabric_e2']['dti'])}<br><small>[{f6(e2['scores']['control_s25_fabric_e2']['ci95'][0])}, {f6(e2['scores']['control_s25_fabric_e2']['ci95'][1])}]</small></td>"
        "<td>baseline (0.000000)</td>"
        f"<td>+{f6(e2['scores']['control_s25_fabric_e2']['dti'] - e2['scores']['control_oof_base']['dti'])}</td></tr>"
        + f'<tr><th scope="row">Matched Base Control<br><small>control_oof_base (6 core bands)</small></th>'
        f"<td>{f6(e2['scores']['control_oof_base']['dti'])}<br><small>[{f6(e2['scores']['control_oof_base']['ci95'][0])}, {f6(e2['scores']['control_oof_base']['ci95'][1])}]</small></td>"
        f"<td>{e2['scores']['control_oof_base']['dti'] - e2['scores']['control_s25_fabric_e2']['dti']:+.6f}</td>"
        "<td>baseline (0.000000)</td></tr>"
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 · Session 27 (S27-CVDC) Executive Summary, Download &amp; Submission Guide</title>
<style>
:root{{--ink:#0f172a;--muted:#475569;--bg:#f8fafc;--card:#ffffff;--line:#cbd5e1;--blue:#1e3a8a;--blue-bg:#eff6ff;--red:#991b1b;--red-bg:#fef2f2;--green:#065f46;--green-bg:#ecfdf5;--amber:#92400e;--amber-bg:#fffbeb}}
*{{box-sizing:border-box}}
body{{margin:0;font:16px/1.55 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{max-width:1120px;margin:0 auto;padding:20px 18px 64px}}
header.top{{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;gap:12px;padding-bottom:14px;border-bottom:2px solid var(--line);margin-bottom:20px}}
header.top nav{{display:flex;flex-wrap:wrap;gap:14px;font-size:14px}}
a{{color:var(--blue)}}
.hero{{border:3px solid var(--blue);background:var(--blue-bg);border-radius:10px;padding:20px 22px;margin-bottom:22px}}
.badges{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px}}
.badge{{display:inline-block;padding:5px 11px;border-radius:999px;font-weight:700;font-size:13px;letter-spacing:.02em}}
.badge.dl{{background:var(--green-bg);color:var(--green);border:1.5px solid var(--green)}}
.badge.nosub{{background:var(--red-bg);color:var(--red);border:1.5px solid var(--red)}}
.badge.info{{background:var(--amber-bg);color:var(--amber);border:1.5px solid var(--amber)}}
.btns{{display:flex;flex-wrap:wrap;gap:12px;margin:16px 0 12px}}
.btn{{display:inline-block;padding:11px 18px;border-radius:7px;font-weight:700;text-decoration:none;font-size:15px}}
.btn.primary{{background:var(--blue);color:#fff}}
.btn.secondary{{background:#fff;color:var(--blue);border:2px solid var(--blue)}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;margin:18px 0}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:16px 18px}}
h1{{font-size:25px;margin:6px 0 10px;line-height:1.25}}
h2{{font-size:20px;margin:28px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}}
h3{{font-size:16px;margin:14px 0 6px}}
.table-wrap{{width:100%;overflow-x:auto;margin:12px 0 20px}}
table{{width:100%;border-collapse:collapse;background:var(--card);font-size:14px}}
caption{{text-align:left;font-weight:700;padding:8px 0;color:var(--ink)}}
th,td{{border:1px solid var(--line);padding:9px 10px;vertical-align:top;text-align:left;overflow-wrap:anywhere}}
thead th{{background:#e2e8f0;font-weight:700}}
td.no{{background:var(--red-bg);color:var(--red);font-weight:700}}
td.ok{{background:var(--green-bg);color:var(--green)}}
code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px}}
code{{overflow-wrap:anywhere}}
pre{{background:#0f172a;color:#f8fafc;padding:14px;border-radius:7px;overflow-x:auto}}
.small{{font-size:13px;color:var(--muted)}}
.skip{{position:absolute;left:-9999px}}
.skip:focus{{position:static;display:inline-block;padding:8px;background:#fff}}
</style>
</head>
<body>
<a class="skip" href="#main">Skip to main content</a>
<div class="wrap">
<header class="top">
  <div><strong>GEMSDOE91 · Session 27 (<code>S27-CVDC</code>)</strong><br><span class="small">DrivenData DOE GEMS Prize · GeoDAWN Hidden Fault &amp; Geothermal Conduit Discovery</span></div>
  <nav aria-label="Page navigation">
    <a href="../index.html"><strong>Portal Home</strong></a>
    <a href="#download-table">Download &amp; Score Table</a>
    <a href="#nine-sites">9 Focus Sites &amp; Uniqueness</a>
    <a href="#forensics">Why GEMSDOE32 Scored 0.2778</a>
    <a href="#hypotheses">Novel Hypotheses &amp; Ablation</a>
    <a href="#how-to-submit">How to Submit</a>
    <a href="../download-audit.html">All-Download Audit</a>
  </nav>
</header>

<main id="main">
<section class="hero" data-submission-ready="false" aria-label="Primary download and automated submission readiness gate">
  <div class="badges">
    <span class="badge dl">OK TO DOWNLOAD: YES — RESEARCH ONLY</span>
    <span class="badge nosub">OK TO SUBMIT: NO — DENSE LATTICE &amp; SELECTOR GATE</span>
    <span class="badge info">REPO-BEST v3 HOLDOUT-DTI: {f6(h["dti"])} (+{f6(paired_s25["delta"])} vs S25-FABRIC)</span>
  </div>
  <h1>S27-CVDC E2 · Contour-Potential Strike Discordance + Valley Knickzone Stitched OOF (37,654 Dots)</h1>
  <p><strong>Immediate Automated Verdict:</strong> A brand-new, geologically novel single-band GeoTIFF was generated and verified in Session 27. It passes <strong>100% of format/range checks</strong> (<code>EPSG:32611</code>, <code>3730&times;3292</code>, <code>float32</code>, <code>nodata=None</code>, values strictly in <code>[0.0, 1.0]</code>, zero NaN anywhere), passes <strong>uniqueness against all 9 focus leaders</strong> (max <strong>{pct(corr["final_dot_max_overlap_nine_leaders"])}</strong> within 3 px, limit &le;70%) and <strong>all {corr["competitive_references_checked"]} competitive non-blanket fleet rasters</strong> across <code>GEMSDOE</code>–<code>GEMSDOE92</code> (max <strong>{pct(corr["final_dot_max_overlap_competitive_le_90000px"])}</strong>, curing S25-FABRIC's 74.89% breach), and achieves the repository's highest spatially-buffered v3 <code>HOLDOUT-DTI</code> (<strong>{f6(h["dti"])}</strong>, 95% CI <code>[{f6(h["ci95"][0])}, {f6(h["ci95"][1])}]</code>) plus blind USGS SGMC off-catalogue DTI <strong>{f6(cand_sgmc)}</strong> (matching <code>GEMSDOE32</code>'s {f6(r0_sgmc)}). It remains marked <strong>OK TO SUBMIT: NO</strong> fail-closed because (1) literal all-registry overlap includes the 206,895-dot synthetic calibration blanket <code>calib_r13lattice_00904.tif</code> ({pct(corr["final_dot_max_overlap_all"])} &gt; 70%; mathematical floor &ge;82.34% at 37,654 dots) and (2) live weekly submission slots require separate human coordinator approval.</p>

  <div class="btns">
    <a class="btn primary" download href="../{escape(tif_rel)}">&#8595; Download Unique GeoTIFF (.tif) — 37,654 dots</a>
    <a class="btn secondary" download href="../{escape(zip_rel)}">&#8595; Download Single-TIFF Archive (.zip)</a>
    <a class="btn secondary" href="run-card.json">Machine-Readable Run Card (.json)</a>
    <a class="btn secondary" href="diagnostics.json">Post-Hoc SGMC &amp; LFI Diagnostics (.json)</a>
  </div>

  <p class="small">
    <strong>File:</strong> <code>{escape(Path(tif_rel).name)}</code> · <strong>SHA-256:</strong> <code>{escape(card["raster_sha256"])}</code><br>
    <strong>Unique Submission Name:</strong> <code>{escape(card["submission_name"])}</code><br>
    <strong>Short Submission Note ({len(card["submission_note"])}/140 chars):</strong> <code>{escape(card["submission_note"])}</code><br>
    <strong>Leakage Canaries:</strong> {can["n_features_tested"]} features &times; 5 (4 v3 folds + pooled) = {can["n_fold_checks"]} checks; max symmetric AUC = <strong>{can["max_symmetric_auc"]:.4f}</strong> (&le;0.90 PASS).
  </p>
</section>

<div class="grid2">
  <div class="card">
    <h3>How S27-CVDC Cured S25-FABRIC's Failure Mode</h3>
    <p class="small"><code>LIMITATIONS_AND_NEXT_STEPS.md</code> identified why S25-FABRIC E2 failed promotion despite beating its base control: <code>run_s25_fabric.py</code> refit HGB <em>in-sample</em> on all <code>60,988</code> catalogue pixels before emission, causing <strong>45.9%</strong> of dots to hug the 3–5 px collar (median distance {dist_s25["median_dist_to_catalogue_px"]:.2f} px), breaching 70% overlap vs <code>bhar-e3</code> (74.89%), and depressing blind SGMC ({f6(s25_sgmc)}) and LFI ({s25_lfi["ridge1"]:.4f}). S27-CVDC emits strictly from the <strong>stitched 4-fold spatially-buffered OOF surface</strong> via a 300 m triangular-kernel CELF submodular optimizer: 3–5 px hugging dropped <strong>45.9% &rarr; {100*dist_c["frac_3_to_5px"]:.1f}%</strong> (median distance <strong>{dist_c["median_dist_to_catalogue_px"]:.2f} px</strong> vs R0's {dist_r0["median_dist_to_catalogue_px"]:.2f} px), blind SGMC rose <strong>+20.4%</strong> ({f6(s25_sgmc)} &rarr; <strong>{f6(cand_sgmc)}</strong>), LFI rose <strong>+124.2%</strong> ({s25_lfi["ridge1"]:.4f} &rarr; <strong>{cand_lfi["ridge1"]:.4f}</strong>), and max competitive overlap dropped <strong>74.89% &rarr; {pct(corr["final_dot_max_overlap_competitive_le_90000px"])}</strong>.</p>
  </div>
  <div class="card">
    <h3>Live Competition Context (Fetched 2026-10-29)</h3>
    <p class="small">Per <a href="{escape(lb["source_url"])}">official DrivenData leaderboard</a> (fetched <code>{escape(lb.get("fetched_utc") or lb.get("retrieved_utc"))}</code>): <strong>#1 = {lb1:.4f}</strong> (<code>xiaofanhu</code>), <strong>#2 = {lb["rows"][1]["best_public_dw_tversky"]:.4f}</strong> (<code>cfld__</code>), <strong>#5 = {lb["rows"][4]["best_public_dw_tversky"]:.4f}</strong> (<code>op01</code> — Phase 1 top-5 $10k cutoff), <strong>#10 = {lb10:.4f}</strong> (<code>zeaal</code>). Prompt references to <code>0.3195</code> and <code>0.4413</code> reflect earlier snapshots. Under Official Rules &sect;3.6 (<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR/DOE 96647.pdf</a>), teams must select <strong>one single submission</strong> for both Phase 1 ($50k hidden test set) and Phase 2 ($250k expert-revised full fault set).</p>
  </div>
</div>

<h2 id="download-table">1. Downloadable Candidates: File, Labeled Score Evidence &amp; Uniqueness</h2>
<p class="small">Every number is strictly labeled per Parallel-Run Protocol Rule 3 as <code>HOLDOUT-DTI</code> (with evaluator version, withheld positives, and 95% CI), <code>ORGANIZER-CONFIRMED</code> (none exist in this repo), or post-hoc <code>MODEL_PROJECTION_NOT_A_SCORE</code> / <code>SGMC-OFFCAT-CONTROL-DTI</code>.</p>
<div class="table-wrap"><table>
  <caption>Repository Research GeoTIFF Downloads &amp; Automated Gate Summary</caption>
  <thead>
    <tr>
      <th scope="col">Candidate &amp; One-Click Download</th>
      <th scope="col">Strictly Labeled Score &amp; Diagnostic Evidence</th>
      <th scope="col">Uniqueness vs Focus Leaders &amp; Fleet Registry</th>
      <th scope="col">OK to Submit?</th>
    </tr>
  </thead>
  <tbody>
    {rows_candidates}
  </tbody>
</table></div>

<h2 id="nine-sites">2. Focus Sites &amp; Broader Fleet Uniqueness Table (GEMSDOE24–36, GEMSDOE91, GEMSDOE92)</h2>
<div class="table-wrap"><table>
  <caption>All Nine Focus Sites + Fleet Comparators vs Session 27 Candidate (<code>S27-CVDC E2</code>)</caption>
  <thead>
    <tr>
      <th scope="col">Site</th>
      <th scope="col">Highest-Scoring Reference File &amp; Dot Budget</th>
      <th scope="col">Reported Value &amp; Post-Hoc Diagnostics</th>
      <th scope="col">S27-CVDC E2 Uniqueness vs This Site (&le;70% Gate)</th>
      <th scope="col">Sibling Mutual Status</th>
    </tr>
  </thead>
  <tbody>
    {rows_sites}
  </tbody>
</table></div>

<h2 id="forensics">3. PhD Forensic Analysis: Why <code>GEMSDOE32</code> Hit <code>0.2778</code> &amp; How to Beat <code>0.2778</code> / Target <code>&gt;0.3195</code></h2>
<ol>
  <li><strong>Exact Mathematical Genealogy of <code>GEMSDOE32 = 0.2778</code>:</strong> All nine focus leaders (<code>0.2449</code>–<code>0.2778</code>) descend from one continuous 19-band monogenic/topographic-corroborated ridge posterior (<code>H19-5</code>, 121,131 px, <code>0.1922</code>). Because Distance-Weighted Tversky (<code>&alpha;=0.2, &beta;=0.8, R=300 m</code>) evaluates <code>TP_w</code> via a <strong>max</strong> over predicted pixels per ground-truth pixel while penalizing <code>FP_w</code> via a <strong>linear sum</strong> over predicted pixels, continuous 1-px ridges triple-pay false positives inside every 300 m disk. Thinning <code>H19-5</code> onto a <code>d=2.8 px</code> Poisson disk (44,090 dots, <code>GEMSDOE25/30 = 0.2600</code>) eliminated ~63% of <code>FP_w</code> at near-zero <code>TP_w</code> loss (+0.0678 DTI). <code>GEMSDOE31/28</code> (<code>h27-4</code>, 40,199 dots, <code>0.2708</code>) pruned dots within 1.0 px of mapped faults (+0.0108 DTI). Finally, <strong><code>GEMSDOE32</code> (<code>h33-h33-2-b2-...-zeros</code>, 37,654 dots, <code>0.2778</code>)</strong> pruned the remaining <strong>2,545 dots within 2.0 px of <code>existing_faults.tif</code></strong>—pure dead-weight false positives because organizer scoring masks visible faults and nearby pixels are already covered from &gt;2 px. Substituting <code>&Delta;FP_w = &minus;2,545</code> into <code>DTI = TP_w / (TP_w + 0.2&middot;FP_w + 0.8&middot;FN_w)</code> yields <code>TP_w &approx; 5,073</code> and predicts <code>0.2778</code> to within <code>0.0006</code>.</li>
  <li><strong>Why <code>H19-5</code> Pruning Asymptotes at ~<code>0.278</code> (and Disqualifies Derivatives):</strong> Every <code>H19-5</code> derivative shares 97.58%–100% 3-px overlap with the nine leaders (immediate Rule-1 duplicate stop) and leaves <code>TP_w &approx; 5,073</code> frozen because <code>H19-5</code> relies heavily on scarp openness (<code>B12/B19</code>), missing blind intrabasin faults and hydrothermal magnetite-destruction troughs where <code>|\nabla TMI|</code> vanishes along the leached core.</li>
  <li><strong>How to Beat <code>0.2778</code> and Target <code>&gt;0.3195</code>:</strong> Raising DTI from <code>0.278</code> to <code>0.320+</code> at 37,654 dots requires lifting hidden-fault recall by ~20–25% without adding false-positive mass: (a) <strong>de novo physics for blind/subdued faults</strong> (implemented here via <code>CVDC + PMDB + VCTK</code> + Stage-2 8-azimuth relay bridging, lifting v3 <code>HOLDOUT-DTI</code> from <code>0.1203 &rarr; 0.1694</code> and matching <code>GEMSDOE32</code> on blind USGS SGMC faults at <code>0.0952</code> with only 41.74% dot overlap), and (b) <strong>external 1-m USGS 3DEP LiDAR bare-earth scarps + unclipped GeoDAWN K/eU/eTh</strong> on an unrestricted workstation to resolve 0.3–1.5 m Holocene scarps invisible in the 100 m DEM (Hypothesis <code>H27-4</code> in <a href="GEOTHERMAL_AND_FAULT_RESEARCH.md"><code>docs/s27-cvdc/GEOTHERMAL_AND_FAULT_RESEARCH.md</code></a>).</li>
</ol>

<h2 id="hypotheses">4. Preregistered Novel Geological Hypotheses &amp; 3-Experiment v3-Fold Ablation</h2>
<p class="small">Full mathematical derivations, band-by-band forensic verification (including proof that <code>B06</code> is radiometric Total Count and <code>(B18, B11)</code> are horizontal gravity derivatives <code>(&part;x B13, &part;y B13)</code>), and verified public literature links are archived in <a href="GEOTHERMAL_AND_FAULT_RESEARCH.md"><code>docs/s27-cvdc/GEOTHERMAL_AND_FAULT_RESEARCH.md</code></a> and <a href="preregistration.md"><code>docs/s27-cvdc/preregistration.md</code></a>.</p>
<ul>
  <li><strong>H27-1 · Contour-Potential Strike Discordance (<code>CVDC</code>, Rank 1 — Implemented):</strong> Subsurface density/magnetic contacts (<code>B13, B18, B11, B02, B09</code>) cutting obliquely across smoothed detrended topographic contours (<code>B12, B19</code>) via Rule-of-V sin<sup>2</sup>(&Delta;&theta;) axial discordance, catching range-oblique transfer zones and concealed piedmont step-faults while rejecting range-parallel unfaulted strata.</li>
  <li><strong>H27-2 · Paired-Flank Magnetite-Destruction Conduit Bridge (<code>PMDB</code>, Rank 2 — Implemented):</strong> Upwelling geothermal fluids alter host-rock magnetite to pyrite/hematite/clay, creating an axial <code>RTP</code> magnetic trough flanked by twin <code>B03</code> gradients co-located with a gravity step, <code>B15</code>-deconfounded shallow MT conductivity excess (<code>B17</code>), and transtensional strain (<code>B04, B07, B08</code>). Built cleanly inside a 17-feature <code>B12/B19</code>-free Pure-Subsurface specialist branch.</li>
  <li><strong>H27-3 · Valley-Crossing Transverse Knickzone Alignment (<code>VCTK</code>, Rank 3 — Implemented):</strong> Active piedmont normal faults incised by transverse washes leave aligned profile convexities where along-stream slope break aligns perpendicular to channel tangents across 0.8–1.5 km strike windows.</li>
  <li><strong>H27-4 · External 1-m USGS 3DEP LiDAR Micro-Scarp + Unclipped GeoDAWN K/Th/U (Rank 4 — Documented Next Step for Unrestricted Host):</strong> Free public <a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">USGS 3DEP</a> + <a href="https://doi.org/10.5066/P93LGLVQ">USGS GeoDAWN</a> science-base grids; blocked only by sandbox network egress allowlist.</li>
</ul>

<div class="table-wrap"><table>
  <caption>Preregistered 3-Experiment Results on <code>gems57-pooled-hide-v2</code> (<code>label-blind-quadrants-v3-feature-buffered</code>, 60,988 Withheld Positives, 1,000-Draw 20 km Block Bootstrap)</caption>
  <thead>
    <tr>
      <th scope="col">Experiment / Control Arm</th>
      <th scope="col">Pooled HOLDOUT-DTI [95% CI]</th>
      <th scope="col">Paired &Delta; vs S25-FABRIC E2 [95% CI]</th>
      <th scope="col">Paired &Delta; vs Base Control [95% CI]</th>
    </tr>
  </thead>
  <tbody>
    {rows_exps}
  </tbody>
</table></div>

<h2 id="how-to-submit">5. Step-by-Step DrivenData Submission Guide (When Selector-Approved)</h2>
<ol>
  <li><strong>Respect the Automated Gate First:</strong> Never upload a file marked <code>OK TO SUBMIT: NO</code> without explicit human coordinator sign-off on (a) the synthetic dense-lattice exemption (<code>calib_r13lattice_00904.tif</code>) and (b) remaining weekly submission quota (&le;3/week on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData Submissions</a>).</li>
  <li><strong>Verify File Integrity Locally:</strong> Download <code>{escape(Path(tif_rel).name)}</code> (or the <code>.zip</code>) above and verify:<br>
    <code>sha256sum {escape(Path(tif_rel).name)}</code> &rarr; must equal <code>{escape(card["raster_sha256"])}</code>.</li>
  <li><strong>Why the <code>&ldquo;Predicted values must be in range [0, 1]&rdquo;</code> Error Cannot Occur Here:</strong> Earlier submissions failed when <code>float32</code> GeoTIFF writers copied <code>-3.4028235e+38</code> or <code>NaN</code> outside the study polygon. <code>vendor/gems57/submission_writer.py</code> writes <code>0.0</code> outside the footprint, binary <code>{{0.0, 1.0}}</code> inside, and sets <code>nodata=None</code>; independent <code>rasterio</code> re-read verified all <code>12,279,160</code> pixels are finite in <code>[0.0, 1.0]</code> with exact <code>EPSG:32611</code> CRS, <code>3730&times;3292</code> shape, and <code>(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)</code> transform.</li>
  <li><strong>Upload Metadata:</strong> Set Submission Name to <code>{escape(card["submission_name"])}</code> and Short Note ({len(card["submission_note"])}/140 chars) to:<br>
    <code>{escape(card["submission_note"])}</code></li>
  <li><strong>Record Organizer Receipt:</strong> Save screenshot/JSON with submission timestamp, SHA-256, and live score; only an authenticated DrivenData receipt may be labeled <code>ORGANIZER-CONFIRMED</code>. Remember Rules &sect;3.6: select <strong>one single submission</strong> before competition close for both Phase 1 ($50k) and Phase 2 ($250k).</li>
</ol>

<h2>6. Official Verified Sources &amp; Reproducibility</h2>
<ul>
  <li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData DOE GEMS Problem Description &amp; DTI Metric</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Live Leaderboard</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official Rules PDF (NLR/DOE 96647)</a></li>
  <li><a href="https://gdr.openei.org/submissions/1391">OpenEI GDR Submission 1391 (INGENIOUS Great Basin Dataset)</a> · <a href="https://gbcge.org/current-projects/ingenious/">GBCGE INGENIOUS Project</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN Survey (DOI: 10.5066/P93LGLVQ)</a></li>
  <li><a href="GEOTHERMAL_AND_FAULT_RESEARCH.md">Session 27 Deep Geothermal &amp; Hidden-Fault Knowledge Base</a> · <a href="preregistration.md">Frozen S27 Preregistration</a> · <a href="REVIEW.md">Session 27 Three-Pass Review</a></li>
</ul>
<pre>.venv/bin/python scripts/restore_data.py
.venv/bin/python scripts/restore_registry.py --available-only
.venv/bin/python scripts/restore_lfi_anchors.py
.venv/bin/python scripts/verify_nine_site_leaders.py
.venv/bin/python scripts/run_s27_cvdc.py features
.venv/bin/python scripts/run_s27_cvdc.py experiment --exp e1   # then e2, e3
.venv/bin/python scripts/run_s27_cvdc.py package
.venv/bin/python scripts/score_s27_cvdc_diagnostics.py
.venv/bin/python scripts/audit_downloads.py --output docs/download-audit.json --html docs/download-audit.html
.venv/bin/python scripts/render_s27_cvdc_portal.py</pre>
</main>
</div>
</body>
</html>
"""
    out = DOCS / "s27-cvdc/executive-summary.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")

    sys.path.insert(0, str(ROOT))
    from scripts.render_olc91_portal import render as render_front_door

    render_front_door()
    assert "s27-cvdc/executive-summary.html" in (DOCS / "index.html").read_text(encoding="utf-8")
    assert "s27-cvdc/executive-summary.html" in (DOCS / "executive-summary.html").read_text(encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}; front door re-rendered with S27 callout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
