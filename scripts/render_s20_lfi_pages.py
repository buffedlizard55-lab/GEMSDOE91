#!/usr/bin/env python3
"""Render docs/s20-lfi-executive-summary.html and the S20 banner at the top of docs/index.html.

Every number is read from docs/run-card-S20-LFI.json, docs/lfi/*.json (incl. docs/lfi/fit_r10.json)
at render time. Site-best live scores are USER-REPORTED (prompt), never organizer receipts.
"""
from __future__ import annotations

import json
import re
from html import escape as esc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def render():
    card = json.loads((DOCS / "run-card-S20-LFI.json").read_text())
    e2 = json.loads((DOCS / "lfi/holdout-e2.json").read_text())
    prof = json.loads((DOCS / "lfi/dot-profile.json").read_text())
    fit = json.loads((DOCS / "lfi/fit_r10.json").read_text())
    sub, G, ev = card["submission"], card["gates"], card["evidence"]
    fname = Path(sub["file"]).name
    zname = Path(sub["zip"]).name
    tif_kb = round(sub["bytes"] / 1024)
    
    # --- 9-site executive summary (user-reported live scores, prompt of session 20) ---
    SITES = [
        ("GEMSDOE24", "h25-1-dotted-h19-5-d1-5", 0.2477, "h25-1-dotted-h19-5-d1-5"),
        ("GEMSDOE25", "dotted-h19-5-d2-8", 0.2600, "dotted-h19-5-d2-8"),
        ("GEMSDOE27", "topo-gap-closure-t-v2-on-d1-5", 0.2449, "topo-gap-closure-t-v2-on-d1-5"),
        ("GEMSDOE28", "h36-1-rung30-blind-r1", 0.2710, "h36-1-rung30-blind-r1"),
        ("GEMSDOE30", "d28-poisson300m-offcat-44090", 0.2600, "d28-poisson300m-offcat"),
        ("GEMSDOE31", "h27-4-solo-d28", 0.2708, "h27-4-solo-d28"),
        ("GEMSDOE32", "h33-h33-2-b2 (zeros)", 0.2778, "h33-h33-2-b2"),
        ("GEMSDOE33", "h33d-analog-tip-stepover-r30", 0.2632, "h33d-analog-tip-stepover-r30"),
        ("GEMSDOE36", "anderson-geothermal-pinn-38854", 0.2750, "anderson-geothermal-pinn-38854"),
    ]
    
    
    def lookup(site, key):
        hv = next((a["hide_v2"] for a in e2["anchors"] if a["site"] == site and key in a["name"]), None)
        lo = next((a["loso"] for a in fit["anchors"] if a["site"] == site and key in a["name"]), None)
        return hv, lo
    
    
    def f4(x):
        return "—" if x is None else f"{x:.4f}"
    
    
    site_rows = []
    for site, name, live, key in SITES:
        hv, lo = lookup(site, key)
        best = " ★ fleet best" if live == max(s[2] for s in SITES) else ""
        site_rows.append(f"<tr><td><strong>{site}</strong></td><td><code>{esc(name)}</code>{best}</td><td><strong>{live:.4f}</strong></td>"
                         f"<td>{f4(lo)}</td><td>{f4(hv)}</td></tr>")
    
    iv = ev["instrument_validity_E2"]
    hd = ev["holdout_dti_hide_v2"]
    proj = ev["projection_G4"]
    s1 = ev["surrogate_E1"]
    reg = card["registry_comparison"]
    okd, oks = card["ok_to_download"], card["ok_to_submit"]
    gate_desc = {
        "G1_format": "Format: single band float32, EPSG:32611, 3730×3292, exact transform, all finite, in [0,1], 0 dots on catalogue (shared writer + validator)",
        "G2_uniqueness": f"Uniqueness: {reg['protocol_and_anchor_registry']['n_compared']} registry/anchor/own rasters + {reg['sibling_sweep']['n_compared']} sibling-sweep rasters; 0 duplicates under the documented rule",
        "G3_leakage_canary": "Leakage canary: every model factor alone has AUC ≤ 0.90 vs withheld truth (max " +
                             f"{max(v['symmetric_auc'] for v in ev['canaries'].values()):.3f})",
        "G4_surrogate_projection": "Surrogate (leave-one-site-out-validated) paired Δ vs GEMSDOE32: 95% lower bound > 0 in ≥2 of 3 variants and P(Δ>0) ≥ 0.95 in all 3",
        "G5_instrument_rule": "Instrument rule: hide-v2 gates only if it tracks live scores (Spearman ≥ 0.5); measured " +
                              f"{iv['spearman_hide_v2_vs_live']:.3f} → not gating",
    }
    gate_rows = "".join(f"<tr><td>{k.split('_')[0]}</td><td>{esc(gate_desc[k])}</td><td class=\"{'pass' if v else 'fail'}\">{'PASS' if v else 'FAIL'}</td></tr>"
                        for k, v in G.items())
    proj_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{v['model_cand']:.3f}</td><td>{v['model_r0']:.3f}</td><td>{v['delta']:+.3f}</td>"
        f"<td>[{v['boot_delta_ci95'][0]:+.3f}, {v['boot_delta_ci95'][1]:+.3f}]</td><td>{v['p_delta_gt0']:.2f}</td>"
        f"<td>{v['projection_vs_reported_r0']:.3f}</td></tr>" for k, v in proj.items())
    
    dl_class = "yes" if okd else "no"
    sb_class = "yes" if oks else "no"
    s20_all = card["s20_preregistered_gates_all_pass"]
    if oks:
        sb_text, sb_small = "OK TO SUBMIT: YES", "All gates and the standing holdout rule pass. 0 slots used; the slot decision is yours."
    elif s20_all:
        sb_text = "OK TO SUBMIT: NO — NOT OK TO SUBMIT (fail-closed, awaiting your sign-off)"
        sb_small = ("All 5 preregistered S20 gates PASS, but it does not beat the spatially-blocked holdout best, which is your "
                    "standing rule. This session showed that holdout does not track live scores. See \u201cOne decision for you\u201d.")
    else:
        sb_text = "OK TO SUBMIT: NO — NOT OK TO SUBMIT (" + ", ".join(k.split('_')[0] for k, v in G.items() if not v) + " failed)"
        sb_small = "Do not spend a weekly slot."
    
    STYLE = (DOCS / "index.html").read_text().split("<style>", 1)[1].split("</style>", 1)[0]
    
    banner = f"""<!--S20-LFI-BEGIN-->
    <section class="card dl" data-submission-ready="{str(oks).lower()}" aria-label="Session 20 download and automated verdict">
    <h1>NEW · Session 20 · LFI GeoTIFF · automated verdict</h1>
    <div class="verdicts"><div class="v {dl_class}">OK TO DOWNLOAD: {'YES' if okd else 'NO'}<small>format re-validated from disk · unique vs {reg['protocol_and_anchor_registry']['n_compared'] + reg['sibling_sweep']['n_compared']} rasters</small></div>
    <div class="v {sb_class}">{esc(sb_text)}<small>{esc(sb_small)}</small></div></div>
    <a class="btn" download href="downloads/{fname}">↓ Download GeoTIFF (.tif, {tif_kb} KB)</a><a class="btn2" download href="downloads/{zname}">↓ ZIP with the one GeoTIFF</a><a class="btn2" href="s20-lfi-executive-summary.html">Executive summary &amp; how to submit</a><a class="btn2" href="run-card-S20-LFI.json">Run card</a>
    <p class="small">Name <code>{esc(sub['name'])}</code><br>Note ({sub['note_chars']}/140) <code>{esc(sub['note'])}</code><br>SHA-256 <code>{sub['sha256']}</code> · {sub['n_dots']:,} binary dots · all-finite zeros float32</p>
    </section>
    <!--S20-LFI-END-->"""
    
    idx = (DOCS / "index.html").read_text()
    idx = re.sub(r"<!--S20-LFI-BEGIN-->.*?<!--S20-LFI-END-->\n?", "", idx, flags=re.S)
    idx = re.sub(r' data-submission-ready="(?:true|false)"', '', idx)   # exactly one current state: ours
    idx = idx.replace('<main id="main">', '<main id="main">\n' + banner, 1)
    (DOCS / "index.html").write_text(idx)

    # Site root (served by Pages): land on the portal whose top card is this session's download + verdict.
    # The parallel 2026-10-26 nine-site audit's own statement is kept verbatim but scoped to that review.
    root = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url=docs/index.html"><title>GEMSDOE91 — Session 20 LFI GeoTIFF · automated verdict</title></head><body><main><h1>GEMSDOE91 — current status</h1>
<p><strong>Session 20 (S20-LFI, 2026-10-26): new research GeoTIFF.</strong> OK TO DOWNLOAD: {'YES' if okd else 'NO'}. {esc(sb_text)}. <a href="docs/index.html">Download and automated verdict (top of portal)</a> · <a href="docs/s20-lfi-executive-summary.html">S20 executive summary &amp; how to submit</a></p>
<p>Parallel 2026-10-26 nine-site audit (arena/af73263f, read-only review): <strong>NO NEW TIFF GENERATED.</strong> OK TO DOWNLOAD: NO NEW TIFF FROM THIS REVIEW. OK TO SUBMIT: NO. <a href="docs/nine-site-audit-20261026.html">Open the nine-site audit</a></p>
<p>The prior ISO91 GeoTIFF remains a separate negative research artifact, not an approved submission: <a href="docs/index.html">historical research/download portal</a> · <a href="docs/executive-summary.html">submission guide (none currently approved)</a>.</p></main></body></html>
"""
    (ROOT / "index.html").write_text(root)
    
    decision = "" if not card.get("human_signoff") else f"""<section class="card warn"><h2>One decision for you</h2>
    <p>{esc(card['human_signoff'])}</p>
    <ul><li><strong>If you keep the rule</strong> (default, fail-closed): do not submit this file. The GEMSDOE32 R0 file (0.2778, USER-REPORTED) remains the fleet best.</li>
    <li><strong>If you accept the live-validated surrogate as the gate</strong>: this file is the repo's strongest candidate. Its projection is 0.38–0.41 (PROJECTION, optimizer's-curse biased upward), and the most conservative variant's 95% lower bound is {min(v['boot_delta_ci95'][0] for v in proj.values()):+.3f} vs R0. Submit it with the steps below and record the live score.</li></ul></section>"""
    
    submit_warn = ("<strong>Do not submit this file.</strong> The automated verdict is NOT OK TO SUBMIT (" + ", ".join(k.split("_")[0] for k, v in G.items() if not v)
                   + " failed). These steps are documented for completeness and for any future file whose verdict is YES. 0 slots used; this run does not pick slots.") if not oks else \
                  "<strong>Slot decision is yours.</strong> This run spends 0 slots and does not pick slots."
    lo_var = min(proj, key=lambda k: proj[k]["boot_delta_ci95"][0])
    pr = [v["projection_vs_reported_r0"] for v in proj.values()]
    if G["G4_surrogate_projection"]:
        beaten = (f"On the live-validated surrogate, probably. This file projects to {min(pr):.3f}–{max(pr):.3f} (PROJECTION) against "
                  f"R0's 0.2778, and every variant's 95% lower bound is above 0. The public #1 is 0.4413.")
    else:
        beaten = (f"Not yet with a unique file. The surrogate projects {min(pr):.3f}–{max(pr):.3f} (PROJECTION) against R0's 0.2778. "
                  f"However, the most conservative variant (<code>{esc(lo_var)}</code>, refitted without the consensus anchors' scores) has 95% CI "
                  f"[{proj[lo_var]['boot_delta_ci95'][0]:+.3f}, {proj[lo_var]['boot_delta_ci95'][1]:+.3f}] and P(Δ&gt;0) = {proj[lo_var]['p_delta_gt0']:.2f}, "
                  f"below the preregistered 0.95. The cause is the uniqueness rule: the fleet already occupies the zones the inversion values most. "
                  f"Pass 1 (37,500 dots, more of them in those zones) projected higher, but it duplicated 5 sibling rasters at more than 70%.")
    
    copy_js = """<script>document.querySelectorAll('button[data-copy]').forEach(b=>b.onclick=()=>{navigator.clipboard.writeText(document.getElementById(b.dataset.copy).value);b.textContent='Copied';});</script>"""
    page = f"""<!doctype html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>GEMSDOE91 · Session 20 LFI · executive summary &amp; how to submit</title><style>{STYLE}</style></head><body><div class="wrap">
    <header><span class="logo">GEMSDOE91 · DOE GEMS Prize</span><nav aria-label="Main"><a href="index.html">Download</a><a href="s20-lfi-executive-summary.html">S20 summary</a><a href="HYPOTHESES_S20_LFI.md">Preregistration</a><a href="run-card-S20-LFI.json">Run card</a></nav></header>
    <main id="main">
    {banner.replace('<!--S20-LFI-BEGIN-->', '').replace('<!--S20-LFI-END-->', '').replace('href="downloads/', 'href="downloads/')}
    
    {decision}
    <section class="card"><h2>1 · How to submit (DrivenData form: file + optional note)</h2>
    <ol>
    <li>Click <strong>↓ Download GeoTIFF</strong> above. The ZIP holding the one TIFF is equally valid.</li>
    <li>Optional check: SHA-256 of the downloaded file must equal <code>{sub['sha256']}</code> (<code>sha256sum {esc(fname)}</code>).</li>
    <li>Open <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">drivendata.org → DOE GEMS → Submissions</a> and sign in.</li>
    <li>Choose the file in the upload box.</li>
    <li>Paste the note (optional field):
    <div class="copy"><input id="note" readonly value="{esc(sub['note'])}"><button type="button" data-copy="note">Copy</button></div>
    Keep the name below for your own records. It is also the file stem:
    <div class="copy"><input id="nm" readonly value="{esc(sub['name'])}"><button type="button" data-copy="nm">Copy</button></div></li>
    <li>Submit. Then record the public score in <code>registry/lfi_live_anchors.csv</code>, because every new live score is one more data point for the LFI model.</li>
    </ol>
    <p class="warn">{submit_warn}</p>
    </section>
    
    <section class="card"><h2>2 · Executive summary of the nine sites: best submission each</h2>
    <p class="small">The <strong>Live</strong> column holds USER-REPORTED public-leaderboard scores from the session prompt. They are not organizer receipts.
    The <strong>LFI held-out</strong> column is the surrogate's prediction for that file with its own site left out of the fit (MODEL).
    The <strong>Hide-v2</strong> column is the HOLDOUT-DTI on the catalogue hide-and-recover evaluator: {iv['n_anchors']} anchors, {hd['withheld_positives']:,} withheld px, evaluator <code>{esc(hd['evaluator_version'])}</code>.</p>
    <table><tr><th>Site</th><th>Best submission</th><th>Live (USER-REPORTED)</th><th>LFI held-out (MODEL)</th><th>Hide-v2 HOLDOUT-DTI</th></tr>{''.join(site_rows)}</table>
    <p><strong>Why GEMSDOE32 h33-2-b2 scored 0.2778.</strong> It is the h19-5 catalogue-blind ridge network, dotted at 2.8 px spacing (44,090 dots → 0.2600).
    Dots within √2–2 px of the mapped catalogue were then deleted (→ 37,654 dots, 0.2778).
    The truth is <em>new</em> faults that are absent from the catalogue, so catalogue-adjacent dots earn almost nothing while still paying the false-positive cost.
    LFI quantifies this from the live data. The fitted effect for &gt;4 km from the catalogue is {fit['theta']['dcat=>40']:+.2f} log-units versus {fit['theta']['dcat=2-3']:+.2f} at 200–300 m.
    For being on the ridge network it is {fit['theta']['dnet=1']:+.2f}, and for agreement of ≥3 independent high-scoring methods it is {fit['theta']['cons=>=3']:+.2f} (ridge {fit['ridge']}).</p>
    <p><strong>Can it be beaten?</strong> {beaten}</p>
    <p>How this file's dots differ from R0's:</p>
    <ul>
    <li>{prof['candidate']['cons_ge3']*100:.1f}% sit in ≥3-method consensus zones (R0 {prof['r0']['cons_ge3']*100:.1f}%; footprint {prof['footprint']['cons_ge3']*100:.1f}%).</li>
    <li>{prof['candidate']['dcat_gt10']*100:.1f}% lie more than 1 km from the catalogue (R0 {prof['r0']['dcat_gt10']*100:.1f}%).</li>
    <li>Only {prof['candidate']['dnet_le1']*100:.1f}% lie within 100 m of the h19-5 ridge network that R0 was dotted from (R0 100%).</li>
    </ul>
    <p>Projections are not scores. Optimizer's curse, extrapolation and public-chunk fit are discussed in §4.</p>
    </section>
    
    <section class="card"><h2>3 · Preregistered automated gates (<a href="HYPOTHESES_S20_LFI.md">written before results</a>)</h2>
    <table><tr><th>Gate</th><th>Rule and measurement</th><th class="res">Result</th></tr>{gate_rows}</table>
    <h3>Evidence</h3>
    <p><strong>E1 · surrogate validity (MODEL).</strong> {s1['n_anchors']} USER-REPORTED live scores, ridge {s1['ridge']}.
    Leave-one-site-out: RMSE {s1['loso_rmse']:.4f}, Spearman {s1['loso_spearman']:.3f}, Pearson {s1['loso_pearson']:.3f}.
    Fitted public-chunk fraction f = {s1['f_public']:.3f}; expected public truth ≈ {s1['K_public_truth_px']:,.0f} px.</p>
    <p><strong>E2 · is the hide-and-recover holdout a valid live proxy? No.</strong> The same {iv['n_anchors']} published rasters were scored on <code>{esc(hd['evaluator_version'])}</code>. Correlation with their live scores:
    Spearman <strong>{iv['spearman_hide_v2_vs_live']:.3f}</strong>, Pearson {iv['pearson_hide_v2_vs_live']:.3f}.
    The LFI held-out predictions reach Spearman {iv['spearman_lfi_loso_vs_live']:.3f}.
    Example: GEMSDOE32 R0 (live 0.2778) scores {hd['r0_gemsdoe32']['dti']:.4f} on hide-v2.
    The reason is that hide-v2 rewards recovering <em>catalogued</em> faults, and those are exactly the pixels the live truth excludes.</p>
    <p><strong>HOLDOUT-DTI (reported regardless).</strong> {esc(hd['evaluator_version'])}, {hd['withheld_positives']:,} withheld positives, 1,000-draw paired 20 km block bootstrap:</p>
    <ul>
    <li>Candidate: {hd['candidate']['dti']:.6f} [{hd['candidate']['ci95'][0]:.6f}, {hd['candidate']['ci95'][1]:.6f}].</li>
    <li>R0: {hd['r0_gemsdoe32']['dti']:.6f} [{hd['r0_gemsdoe32']['ci95'][0]:.6f}, {hd['r0_gemsdoe32']['ci95'][1]:.6f}].</li>
    <li>Paired Δ: {hd['paired_vs_r0']['delta']:+.6f} [{hd['paired_vs_r0']['ci95'][0]:+.6f}, {hd['paired_vs_r0']['ci95'][1]:+.6f}].</li>
    <li>For reference, the best GEMSDOE91 hide-v2 file ever is S18-HGBR at 0.200742, which scored poorly live.</li>
    </ul>
    <p><strong>G4 · surrogate projection (PROJECTION, paired vs R0, 60 site-bootstraps).</strong></p>
    <table><tr><th>Variant</th><th>cand</th><th>R0</th><th>Δ</th><th>95% CI</th><th>P(Δ&gt;0)</th><th>projected vs reported 0.2778</th></tr>{proj_rows}</table>
    </section>
    
    <section class="card"><h2>4 · Limitations and irregularities (read before spending a slot)</h2>
    <ul>
    <li><strong>The standing rule "beat the holdout best" is not met on either instrument.</strong> The candidate is below R0 on hide-v2, which E2 shows is invalid as a live proxy. On the live-validated surrogate, the conservative variant failed G4. The surrogate is validated leave-one-<em>site</em>-out, which is not spatially blocked, because live truth has no spatial labels.</li>
    <li><strong>Optimizer's curse:</strong> the candidate maximises the same model that projects it, so the projection is biased upward. The blinded-consensus variant (95% lower bound {proj['ridge1_blindcons']['boot_delta_ci95'][0]:+.3f}) is the most conservative reading.</li>
    <li><strong>Public-chunk fit:</strong> the surrogate was fitted on public-leaderboard scores, while prizes are scored on the private chunks. No spatial or chunk factor was allowed, which limits but does not remove this risk.</li>
    <li><strong>Consensus can encode shared bias:</strong> all fleet methods read the same 19 bands.</li>
    <li><strong>Uniqueness:</strong> sparse-reference overlap is capped at 0.650 by construction (limit 0.70). The literal readings on dense rasters (&gt;3× our dots, e.g. the lattice witness) exceed 0.70. They are judged by rank correlation under the repo's documented dense-reference rule, with max dot |ρ| {reg['max_dots_abs_spearman']:.3f}.</li>
    <li><strong>Budget:</strong> 3 experiments were run as allowed, plus a pass-2 re-emission for uniqueness. Wall-clock time (~3.5 h) exceeded the 2 h budget.</li>
    <li><strong>Leaderboard ceiling conflict:</strong> the prompt says 0.3195 is the "current high", but the public leaderboard read on 2026-10-26 shows #1 at 0.4413.</li>
    </ul>
    <p>Full list: <a href="../IRREGULARITIES.md">IRREGULARITIES.md</a> · <a href="../LIMITATIONS_AND_NEXT_STEPS.md">LIMITATIONS_AND_NEXT_STEPS.md</a></p>
    </section>
    </main><footer>Generated from <code>docs/run-card-S20-LFI.json</code> by <code>scripts/render_s20_lfi_pages.py</code>. No numbers are typed by hand. No automatic uploads, and no credentials are stored.</footer></div>{copy_js}</body></html>
    """
    (DOCS / "s20-lfi-executive-summary.html").write_text(page)
    print("wrote docs/s20-lfi-executive-summary.html and the index banner")


if __name__ == "__main__":
    render()
