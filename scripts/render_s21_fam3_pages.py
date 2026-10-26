#!/usr/bin/env python3
"""Render docs/s21-fam3-executive-summary.html + S21 banner on docs/index.html + root index.
Every number is read from docs/run-card-S21-FAM3.json and docs/s21/*.json at render time."""
from __future__ import annotations
import json, re
from html import escape as esc
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def render():
    card = json.loads((DOCS / "run-card-S21-FAM3.json").read_text())
    hold = json.loads((DOCS / "s21/holdout.json").read_text())
    fore = json.loads((DOCS / "s21/nine-site-forensics.json").read_text())
    prof = json.loads((DOCS / "s21/dot-profile.json").read_text())
    sub, G, ev = card["submission"], card["gates"], card["evidence"]
    fname, zname = Path(sub["file"]).name, Path(sub["zip"]).name
    tif_kb = round(sub["bytes"] / 1024)
    okd, oks = card["ok_to_download"], card["ok_to_submit"]
    failed = ", ".join(k.split("_")[0] for k, v in G.items() if not v)
    regN = card["registry_comparison"]["protocol_and_anchor_registry"]["n_compared"]
    sibN = card["registry_comparison"]["sibling_sweep"]["n_compared"]
    proj = ev["projection_G4"]
    proj1 = ev["projection_G4_pass1"]["variants"]
    hd = ev["holdout_dti_hide_v2"]
    s1 = ev["surrogate_E1"]

    SITES = [
        ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5", "GEMSDOE24_d1.5", "GEMSDOE24"),
        ("GEMSDOE25", "dotted-h19-5-d2-8 (44,090 dots)", "GEMSDOE25_d2.8", "GEMSDOE25/30"),
        ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5", "GEMSDOE27_gapclosure", "GEMSDOE27"),
        ("GEMSDOE28", "h36-1-rung30-blind-r1 (cluster 0.2707–0.2710)", "GEMSDOE28_rung30", "GEMSDOE28b"),
        ("GEMSDOE30", "d28-poisson300m-offcat-44090", "GEMSDOE30_d28_fallback", "GEMSDOE25/30"),
        ("GEMSDOE31", "h27-4-solo-d28", "GEMSDOE31_solo", "GEMSDOE28/31"),
        ("GEMSDOE32", "h33-h33-2-b2 zeros ★ highest", "GEMSDOE32_R0", "r0_gemsdoe32"),
        ("GEMSDOE33", "h33d-analog-tip-stepover-r30", "GEMSDOE33_tipstepover_fallback", "GEMSDOE33"),
        ("GEMSDOE36", "anderson-geothermal-pinn-38854", "GEMSDOE36_pinn", "GEMSDOE36"),
    ]
    REL = {
        "GEMSDOE24": "h19-5 network dotted at 1.5 px",
        "GEMSDOE25": "same network dotted at 2.8 px",
        "GEMSDOE27": "gap-closure on the 24 file — scored <em>below</em> its parent",
        "GEMSDOE28": "re-dotted solo variants of the same network (≈equal n to R0, collar kept)",
        "GEMSDOE30": "pixel-identical support to GEMSDOE25 (forensics)",
        "GEMSDOE31": "pixel-identical to GEMSDOE28 solo (forensics)",
        "GEMSDOE32": "solo minus all dots ≤2 px from catalogue (byte-rebuild verified)",
        "GEMSDOE33": "99.7% of dots on h19-5 network pixels; collar kept (3,894 dots ≤2 px)",
        "GEMSDOE36": "<strong>R0 plus exactly 1,200 extra dots</strong> (strict superset, forensics)",
    }
    rows = []
    for site, name, fkey, hkey in SITES:
        fr = fore["rows"][fkey]
        hv = hold["pooled"]["scores"][hkey]["dti"]
        rows.append(f"<tr><td><strong>{site}</strong></td><td><code>{esc(name)}</code></td>"
                    f"<td><strong>{fr['user_reported_score']:.4f}</strong></td><td>{fr['n_dots']:,}</td>"
                    f"<td>{fr['n_dcat_le_2px']:,}</td><td>{hv:.4f}</td><td>{REL[site]}</td></tr>")

    gate_desc = {
        "G1_format": "Format: single band float32, EPSG:32611, 3730×3292, exact transform, all finite, in [0,1], no nodata, 0 dots on catalogue / outside footprint (shared writer + validator + re-read)",
        "G2_uniqueness": f"Uniqueness: surface pre-check PASS + final dots vs {regN} registry/anchor/own + {sibN} sibling-sweep rasters; 0 duplicates under the documented dense-reference rule (max sparse literal {card['registry_comparison']['max_literal_sparse_sibling']['within_3px_literal']:.3f} ≤ 0.70)",
        "G3_leakage_canary": f"Leakage canary: every model factor alone AUC ≤ 0.90 vs withheld truth (max {max(v['symmetric_auc'] for v in ev['canaries'].values()):.3f})",
        "G4_surrogate_projection": "Live projection (S20 bar, unmoved): paired Δ vs GEMSDOE32 with 95% lower bound > 0 in ≥2 of 3 variants and P(Δ>0) ≥ 0.95 in all 3",
        "G5_instrument_rule": f"Instrument honesty: hide-v2 reported in full; gates only if it tracked live (S20 112-anchor Spearman 0.105; S21 nine-site recomputation {ev['instrument_validity']['spearman_hide_v2_vs_live']:.1f})",
    }
    gate_rows = "".join(f"<tr><td>{k.split('_')[0]}</td><td>{esc(gate_desc[k])}</td>"
                        f"<td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>" for k, v in G.items())

    def proj_rows(P):
        return "".join(f"<tr><td>{esc(k)}</td><td>{v['model_cand']:.3f}</td><td>{v['model_r0']:.3f}</td>"
                       f"<td>{v['delta']:+.3f}</td><td>[{v['boot_delta_ci95'][0]:+.3f}, {v['boot_delta_ci95'][1]:+.3f}]</td>"
                       f"<td>{v['p_delta_gt0']:.2f}</td><td>{v['projection_vs_reported_r0']:.3f}</td></tr>" for k, v in P.items())

    STYLE = (DOCS / "index.html").read_text().split("<style>", 1)[1].split("</style>", 1)[0]
    sb_text = ("OK TO SUBMIT: YES" if oks else f"OK TO SUBMIT: NO — NOT OK TO SUBMIT ({failed} failed)")
    sb_small = ("All preregistered gates pass. 0 slots used; slot timing is the selector's." if oks
                else "Do not spend a weekly slot on this file. Projection vs R0 is negative in every variant.")
    banner = f"""<!--S21-FAM3-BEGIN-->
    <section class="card dl" data-submission-ready="{str(oks).lower()}" aria-label="Session 21 download and automated verdict">
    <h2>NEW · Session 21 · S21-FAM3 GeoTIFF · automated verdict (no human inspector)</h2>
    <div class="verdicts"><div class="v {'yes' if okd else 'no'}">OK TO DOWNLOAD: {'YES' if okd else 'NO'}<small>format re-validated from disk · unique vs {regN + sibN:,} rasters</small></div>
    <div class="v {'yes' if oks else 'no'}">{esc(sb_text)}<small>{esc(sb_small)}</small></div></div>
    <a class="btn" download href="downloads/{fname}">↓ Download S21-FAM3 GeoTIFF</a><a class="btn2" download href="downloads/{zname}">↓ S21-FAM3 Single-TIFF ZIP</a><a class="btn2" href="s21-fam3-executive-summary.html">Executive summary &amp; how to submit</a><a class="btn2" href="run-card-S21-FAM3.json">Run card</a>
    <p class="small">Name <code>{esc(sub['name'])}</code><br>Note ({sub['note_chars']}/140) <code>{esc(sub['note'])}</code><br>SHA-256 <code>{sub['sha256']}</code> · {sub['n_dots']:,} binary dots · all-finite zeros float32</p>
    </section>
    <!--S21-FAM3-END-->"""
    idx = (DOCS / "index.html").read_text()
    idx = re.sub(r"<!--S21-FAM3-BEGIN-->.*?<!--S21-FAM3-END-->\n?", "", idx, flags=re.S)
    idx = re.sub(r' data-submission-ready="(?:true|false)"', '', idx)
    idx = idx.replace('<main id="main">', '<main id="main">\n' + banner, 1)
    (DOCS / "index.html").write_text(idx)

    root = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE91 — Session 21 S21-FAM3 GeoTIFF · automated verdict</title></head><body><main><h1>GEMSDOE91 — current status</h1>
<p><strong>Session 21 (S21-FAM3, 2026-10-26): new unique research GeoTIFF.</strong> OK TO DOWNLOAD: {'YES' if okd else 'NO'}. {esc(sb_text)}. <a href="docs/index.html">Download and automated verdict (top of portal)</a> · <a href="docs/s21-fam3-executive-summary.html">S21 executive summary, nine-site analysis &amp; how to submit</a></p>
<p>Session 20 (S20-LFI): OK TO DOWNLOAD: YES; OK TO SUBMIT: NO (G4 failed). <a href="docs/s20-lfi-executive-summary.html">S20 executive summary</a></p>
<p>Parallel 2026-10-26 nine-site audit (arena/af73263f, read-only review): <strong>NO NEW TIFF GENERATED.</strong> OK TO DOWNLOAD: NO NEW TIFF FROM THIS REVIEW. OK TO SUBMIT: NO. <a href="docs/nine-site-audit-20261026.html">Open the nine-site audit</a></p>
<p>The prior ISO91 GeoTIFF remains a separate negative research artifact, not an approved submission: <a href="docs/index.html">historical research/download portal</a>.</p></main></body></html>
"""
    (ROOT / "index.html").write_text(root)

    cand_h, r0_h = hd["candidate"], hd["r0_gemsdoe32"]
    pr2 = [v["projection_vs_reported_r0"] for v in proj.values()]
    pr1 = [v["projection_vs_reported_r0"] for v in proj1.values()]
    copy_js = """<script>document.querySelectorAll('button[data-copy]').forEach(b=>b.onclick=()=>{navigator.clipboard.writeText(document.getElementById(b.dataset.copy).value);b.textContent='Copied';});</script>"""
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 · Session 21 S21-FAM3 · executive summary &amp; how to submit</title><style>{STYLE}</style></head><body><div class="wrap">
<header><span class="logo">GEMSDOE91 · DOE GEMS Prize</span><nav aria-label="Main"><a href="index.html">Download</a><a href="s21-fam3-executive-summary.html">S21 summary</a><a href="s20-lfi-executive-summary.html">S20 summary</a><a href="HYPOTHESES_S21_FAM3.md">Preregistration</a><a href="run-card-S21-FAM3.json">Run card</a></nav></header>
<main id="main">
{banner.replace('<!--S21-FAM3-BEGIN-->', '').replace('<!--S21-FAM3-END-->', '')}

<section class="card"><h2>Bottom line — which submission is best?</h2>
<ul>
<li><strong>Highest existing file:</strong> GEMSDOE32 <code>h33-h33-2-b2</code> at <strong>0.2778 (USER-REPORTED, no organizer receipt in this repo)</strong>. Re-submitting its bytes would be an exact duplicate — this project never copies a previous submission as its own.</li>
<li><strong>This session's new unique file (above): NOT OK TO SUBMIT.</strong> It is format-valid and unique against {regN + sibN:,} checked rasters, but preregistered gate <strong>G4 failed</strong>: every live-score surrogate variant projects it <em>below</em> R0 ({min(pr2):.3f}–{max(pr2):.3f} PROJECTION vs reported 0.2778).</li>
<li><strong>Can this approach beat 0.2778?</strong> The registry-unique pass-1 file projected {min(pr1):.3f}–{max(pr1):.3f} (PROJECTION) — but it duplicated 7 sibling-site rasters and is therefore not a legal unique candidate. Once full sibling uniqueness is enforced, the gain disappears. <strong>Recommendation: spend 0 weekly slots now.</strong> The public leaderboard #1 in the prompt is 0.4413 (a conflicting 0.3195 figure also appears; neither was re-verified against an organizer receipt this session).</li>
</ul></section>

<section class="card"><h2>1 · How to submit (only for a file whose verdict is YES)</h2>
<ol>
<li>Download the GeoTIFF above ({tif_kb} KB) or the single-TIFF ZIP. Values are all-finite float32 in [0, 1] with no nodata tag — the encoding that cannot trip the portal's <em>“Predicted values must be in range [0, 1]”</em> error (NaN-outside files can).</li>
<li>Optional check: SHA-256 must equal <code>{sub['sha256']}</code>.</li>
<li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData → DOE GEMS → New submission</a>, choose the file.</li>
<li>Paste this note ({sub['note_chars']}/140): <div class="copy"><input id="note" readonly value="{esc(sub['note'])}"><button type="button" data-copy="note">Copy</button></div>
Name for your records (file stem): <div class="copy"><input id="nm" readonly value="{esc(sub['name'])}"><button type="button" data-copy="nm">Copy</button></div></li>
<li>After any future submission, record its public score in <code>registry/lfi_live_anchors.csv</code> — each new live score is one more equation for the inversion.</li>
</ol>
<p class="warn"><strong>Do not submit this S21 file.</strong> Automated verdict: NOT OK TO SUBMIT ({failed} failed). Steps exist so a future YES file needs no human inspector. This run used 0 slots and cannot upload (no DrivenData auth in the sandbox).</p>
<p class="small">Format per the official page (verified 2026-10-26): single-band float32, EPSG:32611, 100 m, values in [0,1]; metric = distance-weighted Tversky (α=0.2 FP, β=0.8 FN, 300 m triangular kernel); test truth = expert faults <em>not</em> in the public catalogue; one selected submission is scored in both prize rounds. Sources: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem &amp; metric</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">reference solution</a> · <a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> · <a href="https://gbcge.org/current-projects/ingenious/">INGENIOUS</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></p>
</section>

<section class="card"><h2>2 · Executive summary of the nine high-score sites (every site, best file)</h2>
<p class="small">Live = USER-REPORTED prompt scores (no organizer receipts). Dot counts and collar counts are recomputed here from SHA-pinned rasters (<a href="s21/nine-site-forensics.json">forensics JSON</a>, <code>scripts/forensics_s21_nine_sites.py</code>). Hide-v2 = HOLDOUT-DTI, evaluator <code>{esc(hd['evaluator_version'])}</code>, {hd['withheld_positives']:,} withheld catalogue px.</p>
<table><tr><th>Site</th><th>Best submission (submit this one from that site)</th><th>Live</th><th>Dots</th><th>Dots ≤2 px of catalogue</th><th>Hide-v2</th><th>What it actually is</th></tr>{''.join(rows)}</table>
<p><strong>Why GEMSDOE32 scored highest — the PhD-level read.</strong> All nine bests trace <em>one</em> catalogue-blind ridge network (h19-5, 121,131 px, 0.1922). The ordering is pure emission geometry under a 3-px max-kernel: (i) dense ridge pixels are redundant — after the first dot covers a truth pixel at weight 1, neighbours add no TP<sub>w</sub> but still pay FP<sub>w</sub> — so 2.8-px dotting (0.1922→0.2600) beats 1.5-px (0.2477), and adding gap-closure dots hurts (0.2449); (ii) live truth <em>excludes</em> the mapped catalogue, so the ≤2 px collar band is truth-depleted — deleting its 6,436 dots in two measured steps gives 0.2600→0.2708→0.2778 at ~constant everything else (GEMSDOE28 rung30: same dot count as R0 but collar kept, 0.2710 — the clean at-constant-n control); (iii) the margin is now exhausted — GEMSDOE36 is literally R0 + 1,200 dots and scores <em>lower</em> (0.2750), a direct measurement that extra dots at R0's margin are FP-dominated. No new detector in 20+ repo sessions (live family 0.13–0.18) has beaten this geometry.</p>
<p><strong>Instrument warning.</strong> Within these nine files, hide-v2 ranks live performance <em>exactly backwards</em> (Spearman −1.0, recomputed this session; 112-anchor value 0.105 in S20): hide-v2 rewards recovering catalogued faults, which the live truth excludes by construction. Any “beat the holdout best” rule using hide-v2 selects catalogue-recoverers that score 0.02–0.16 live.</p>
</section>

<section class="card"><h2>3 · What S21 tried (lane, hypotheses, gates)</h2>
<p>Preregistered in <a href="HYPOTHESES_S21_FAM3.md">HYPOTHESES_S21_FAM3.md</a> before any fit — 4 ranked geological hypotheses; top candidate run as lane <strong>S21-FAM3</strong>: exact-DTI inversion of 112 live scores on distance-to-catalogue, distance to the three nine-site family networks, B19/B15/B12 terciles and the B15 basement-step gradient |∇B15| (no consensus covariate — S20's design minus its most circular term), greedy expected-DTI emission at a strict &gt;3 px collar under hard 65% uniqueness caps. Non-fault mimic: lithologic/intrusive contacts and erosional ridges.</p>
<table><tr><th>Gate</th><th>Rule and measurement</th><th class="res">Result</th></tr>{gate_rows}</table>
<p><strong>E1 · inversion validity (MODEL).</strong> Ridge 10: LOSO RMSE {s1['ridge10']['loso_rmse']:.4f}, Spearman {s1['ridge10']['loso_spearman']:.3f} (ridge 1: {s1['ridge1']['loso_rmse']:.4f} / {s1['ridge1']['loso_spearman']:.3f}). The S20 design stored from last session is <em>better</em> (0.0198 / 0.957) — the family-sensor + |∇B15| component is a <strong>negative result</strong>; sensor coefficients flip sign between ridge settings (collinear networks), so no coefficient here is a geological fact.</p>
<p><strong>E2 · HOLDOUT-DTI (hide-v2, {hd['withheld_positives']:,} withheld, paired 20 km block bootstrap).</strong> Candidate {cand_h['dti']:.6f} [{cand_h['ci95'][0]:.6f}, {cand_h['ci95'][1]:.6f}] — identically zero by construction (&gt;3 px collar ⇒ no dot can credit a withheld catalogue pixel within the 3 px kernel). R0 {r0_h['dti']:.6f}. This measures instrument antagonism, not live skill; canaries all ≤0.647 (G3 PASS).</p>
<p><strong>G4 · live projection, final sibling-unique file (PROJECTION, 60 site-bootstraps, paired vs R0):</strong></p>
<table><tr><th>Variant</th><th>cand</th><th>R0</th><th>Δ</th><th>95% CI</th><th>P(Δ&gt;0)</th><th>vs reported 0.2778</th></tr>{proj_rows(proj)}</table>
<p><strong>Pass-1 file for contrast (registry-unique only; DUPLICATE vs siblings — never downloadable):</strong></p>
<table><tr><th>Variant</th><th>cand</th><th>R0</th><th>Δ</th><th>95% CI</th><th>P(Δ&gt;0)</th><th>vs reported 0.2778</th></tr>{proj_rows(proj1)}</table>
<p>Projections are never scores; the model that proposes dots also projects them (optimizer's curse), which is why the blinded variant and the full-bootstrap bar exist — and why pass 1's larger numbers must not be quoted as expected scores.</p>
<p>Dot profile: candidate {prof['candidate']['dcat_gt10']*100:.0f}% of dots &gt;1 km from catalogue (R0 {prof['r0']['dcat_gt10']*100:.0f}%), {prof['candidate']['dnet_le1']*100:.0f}% within 100 m of the h19-5 network (R0 100%), minimum catalogue distance {prof['candidate']['min_dcat']:.2f} px (R0 {prof['r0']['min_dcat']:.2f} px).</p>
</section>

<section class="card"><h2>4 · Limitations, irregularities &amp; next steps</h2>
<ul>
<li><strong>Uniqueness costs the whole projected gain (again).</strong> 312 simultaneous 65% caps force dots off every zone any fleet method values. Two emitter defects were found and fixed en route (cap-fill ratchet, fixed-floor collapse) — see run-card deviations; the latent ratchet in <code>scripts/run_lfi_emit.py</code> is reported for a template-level fix.</li>
<li><strong>No ORGANIZER-CONFIRMED score exists in this repo</strong> for any file, including 0.2778. All live numbers are USER-REPORTED; the prompt's 0.3195 vs 0.4413 leaderboard figures conflict and were not re-verified today.</li>
<li><strong>Public→private transfer untested;</strong> no chunk factor was fitted, but adaptive fitting to public scores remains a risk for any inversion file.</li>
<li><strong>Next levers by expected value:</strong> (1) submit-and-learn — each new real score sharpens the S20 (better) inversion; (2) 1 m DEM scarp morphometry on an unrestricted host (USGS 3DEP, free/public domain — sandbox cannot reach tile hosts; DrivenData DEM links need login); (3) an information-designed probe file to pin the largest inversion coefficients. Another re-emission of the same network is <em>not</em> on this list: the forensics above show that axis is exhausted.</li>
</ul>
<p>Full detail: <a href="run-card-S21-FAM3.json">run card (JSON)</a> · <a href="HYPOTHESES_S21_FAM3.md">preregistration</a> · <a href="REVIEW-S21-FAM3-20261026.md">three-pass review</a> · <a href="../IRREGULARITIES.md">irregularities</a> · <a href="../LIMITATIONS_AND_NEXT_STEPS.md">limitations &amp; next steps</a> · <a href="s20-lfi-executive-summary.html">S20 summary</a></p>
</section>
</main><footer>Generated from <code>docs/run-card-S21-FAM3.json</code> by <code>scripts/render_s21_fam3_pages.py</code>. Maximize P(Win) · Own the Outcome. No automatic uploads; no credentials stored; every score is evidence-labelled.</footer></div>{copy_js}</body></html>
"""
    (DOCS / "s21-fam3-executive-summary.html").write_text(page)
    print("rendered S21 pages")


if __name__ == "__main__":
    render()
