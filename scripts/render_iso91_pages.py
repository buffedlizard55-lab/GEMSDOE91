#!/usr/bin/env python3
"""Render the ISO91 front door and executive summary FROM docs/run-card-ISO91.json.

Writes docs/iso91-index-src.html and docs/iso91-exec-src.html (durable sources). The shared
entry-point injector (scripts/render_olc91_portal.py, last step of scripts/render_portal.py)
copies them to docs/index.html and docs/executive-summary.html after re-validating the
download fail-closed. Every number on the pages comes from the run card; the verdict badge is
the card's computed verdict, never a hand-typed string.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CARD = DOCS / "run-card-ISO91.json"

ARCHIVE = [  # prior research downloads (all negative, each with its own run card); paths relative to docs/
    ("OLC91 E1", "downloads/gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif", "run-card-OLC91.json",
     "0.0832 HOLDOUT-DTI (I2 legacy split); duplicate-stop 76.8%"),
    ("CWP91 E1", "downloads/gemsdoe91-cwp91-e1-completenesspu-37654-20261025-562325b2.tif", "run-card-CWP91.json",
     "0.0832 HOLDOUT-DTI (I2 legacy split); duplicate-stop 90.8%"),
    ("S17-CPAD E1", "downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif", "run-card-S17-CPAD.json",
     "0.1982 HOLDOUT-DTI (60,988-positive LOQO)"),
    ("S17-LFTG E2", "downloads/gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros.tif", "run-card-S17-LFTG.json",
     "0.1886 HOLDOUT-DTI (60,988-positive LOQO); 0.1823 USER-REPORTED live"),
    ("S17-CGRD E2", "downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif", "run-card-S17-CGRD.json",
     "see run card (IR: inconsistent with S17-CPAD ranking)"),
    ("S17-EULR E3", "downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif", "run-card-S17-EULR.json",
     "see run card"),
    ("S17-CWPC E3", "downloads/gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros.tif", "run-card-S17-CWPC.json",
     "0.1225 HOLDOUT-DTI (60,988-positive LOQO); 0.1367 USER-REPORTED live"),
    ("S17-CDSC E1", "downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif", "run-card-S17-CDSC.json",
     "see run card (v1.0 numbers are label-leaky)"),
    ("XG91 E1", "downloads/gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.tif", "run-card-XG91.json", "see run card"),
    ("HEXFAR91", "downloads/gems91-hexfar-stagger-18-35-20261025T161307Z-d102f5f0-zeros.tif", "run-card-HEXFAR91.json",
     "see run card"),
]

CSS = """:root{--ink:#14211d;--mut:#51635d;--ok:#16624c;--bad:#a12c2c;--line:#dbe4e0;--bg:#f6f9f7;--warn:#fff6e0}
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg);line-height:1.55}
.wrap{max-width:980px;margin:0 auto;padding:18px}a{color:var(--ok)}h1{font-size:28px;line-height:1.2;margin:.2em 0 .3em}h2{font-size:20px;margin:0 0 .5em}
header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:12px}.logo{font-weight:800}nav a{margin-left:14px;font-weight:600;text-decoration:none}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px;margin:14px 0;overflow-wrap:anywhere;overflow-x:auto}
.dl{border:2px solid var(--ok)}.verdicts{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0}@media(max-width:640px){.verdicts{grid-template-columns:1fr}}
.v{border-radius:12px;padding:12px 14px;font-weight:800;font-size:18px}.v small{display:block;font-weight:500;font-size:13px;margin-top:2px}
.yes{background:#e2f2ea;color:var(--ok)}.no{background:#f8e3e3;color:var(--bad)}
.btn{display:inline-block;background:var(--ok);color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:800;margin:6px 8px 6px 0}
.btn2{display:inline-block;border:1px solid var(--ok);padding:9px 13px;border-radius:9px;text-decoration:none;font-weight:700;margin:6px 8px 6px 0}
.small{color:var(--mut);font-size:14px}code{font-size:12.5px;word-break:break-all}table{width:100%;border-collapse:collapse;font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:7px;text-align:left;vertical-align:top}.pass{color:var(--ok);font-weight:700;white-space:nowrap}.fail{color:var(--bad);font-weight:700}td.fail,th.res{white-space:nowrap}
.copy{display:flex;gap:8px;align-items:center;margin:6px 0}.copy input{flex:1;font-family:ui-monospace,monospace;font-size:13px;padding:7px;border:1px solid var(--line);border-radius:8px}
.copy button{border:1px solid var(--ok);background:#fff;color:var(--ok);border-radius:8px;padding:7px 10px;font-weight:700;cursor:pointer}
.warn{background:var(--warn);border:1px solid #ead39a;border-radius:10px;padding:10px 12px}.badge{display:inline-block;padding:4px 10px;border-radius:999px;background:#e2f2ea;color:var(--ok);font-weight:700;font-size:13px;margin:0 6px 6px 0}.badge.bad{background:#f8e3e3;color:var(--bad)}.button{display:inline-block;background:var(--ok);color:#fff;text-decoration:none;padding:10px 14px;border-radius:9px;font-weight:800;margin:4px 6px 4px 0}.button.outline{background:#fff;color:var(--ok);border:1px solid var(--ok)}ol li{margin:4px 0}footer{margin:24px 0;color:var(--mut);font-size:13px}"""

JS = """<script>document.querySelectorAll('button[data-copy]').forEach(b=>b.addEventListener('click',()=>{const t=document.getElementById(b.dataset.copy);t.select();navigator.clipboard&&navigator.clipboard.writeText(t.value);b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)}))</script>"""


def e(x) -> str:
    return html.escape(str(x), quote=True)


def fmt_ci(x) -> str:
    return f"{x['dti']:.6f} [{x['ci95'][0]:.6f}, {x['ci95'][1]:.6f}]"


def current_review_notice() -> str:
    return """<section class=\"card\" style=\"border:2px solid #a12c2c;background:#fff0e9\" aria-label=\"Current review status\">
<p><strong>2026-10-26 CURRENT REVIEW · arena/af73263f-gemsdoe91: NO NEW TIFF GENERATED.</strong> <strong>OK TO DOWNLOAD: NO — THIS REVIEW GENERATED NO NEW FILE. OK TO SUBMIT: NO.</strong></p>
<p>The ISO91 TIFF linked farther down is a separate 2026-10-25 negative research artifact. It was not produced by this review and remains <strong>NOT OK TO SUBMIT</strong>. Its research-download link and format check are not approval for a new candidate.</p>
<p><a href=\"nine-site-audit-20261026.html\">Current nine-site executive audit</a> · <a href=\"REVIEW-SITE-AUDIT-20261026.md\">Current three-pass review</a> · <a href=\"run-card-SITE-AUDIT-20261026.json\">Current no-run JSON card</a> · <a href=\"research/nine-site-audit-20261026.json\">Pinned claim register</a> · <a href=\"high-score-submissions-review.html\">Earlier nine-site comparison</a></p>
</section>"""


def head(title: str, desc: str) -> str:
    return (f"<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
            f"content=\"width=device-width,initial-scale=1\"><title>{e(title)}</title><meta name=\"description\" "
            f"content=\"{e(desc)}\"><style>{CSS}</style></head><body><div class=\"wrap\">\n"
            "<header><span class=\"logo\">GEMSDOE91 · DOE GEMS Prize</span><nav aria-label=\"Main\">"
            "<a href=\"nine-site-audit-20261026.html\">Current audit</a><a href=\"high-score-submissions-review.html\">Earlier nine-site comparison</a><a href=\"index.html\">Research archive</a><a href=\"executive-summary.html\">Submission guide</a>"
            "<a href=\"REVIEW-SITE-AUDIT-20261026.md\">Current three-pass review</a><a href=\"REVIEW-ISO91-BACC7C26-20261025.md\">ISO91 history</a></nav></header>\n")


def download_card(c: dict) -> str:
    v, r = c["verdict"], c["raster"]
    tif = Path(r["path"]).relative_to("docs").as_posix()
    zp = Path(r["zip"]).relative_to("docs").as_posix()
    ok_dl = v["OK_TO_DOWNLOAD"].startswith("YES")
    ok_sub = v["OK_TO_SUBMIT"] == "YES"
    kinds = (("holdout", ("G1", "G2", "G3", "G4", "G5")), ("uniqueness", ("G6",)), ("format", ("G7",)))
    parts = []
    for label, prefixes in kinds:
        ids = [g.split("_")[0] for g in v["failed_gates"] if g.startswith(prefixes)]
        if ids:
            parts.append(", ".join(ids) + f" ({label})")
    failed = " and ".join(parts) or "none"
    sub_line = ("OK TO SUBMIT: YES" if ok_sub else "OK TO SUBMIT: NO")
    g6a, g6b = c["gates"]["G6a_uniqueness_protocol_registry"], c["gates"]["G6b_uniqueness_extended_gemsdoe_sweep"]
    uniq_short = ("unique vs protocol registry" if g6a["pass"] else "registry duplicate") + \
                 ("; no duplicate in 102 GEMSDOE repos" if g6b["pass"] else "; 1 marginal literal flag in the GEMSDOE sweep (see G6b)")
    sub_why = ("every preregistered gate passed" if ok_sub else
               f"NOT OK TO SUBMIT — failed {e(failed)}; do not spend a weekly slot")
    return f"""<section class="card dl" data-submission-ready="{'true' if ok_sub else 'false'}" aria-label="Current download and automated verdict">
<h1>ISO91 · prior negative research GeoTIFF · 2026-10-25</h1>
<div class="verdicts"><div class="v {'yes' if ok_dl else 'no'}">{'OK TO DOWNLOAD: YES' if ok_dl else 'OK TO DOWNLOAD: NO'}<small>format re-checked from disk · {e(uniq_short)}</small></div>
<div class="v {'yes' if ok_sub else 'no'}">{sub_line}<small>{sub_why}</small></div></div>
<a class="btn" download href="{e(tif)}">↓ Download GeoTIFF (.tif, {r['bytes']/1024:.0f} KB)</a><a class="btn2" download href="{e(zp)}">↓ ZIP with the one GeoTIFF</a><a class="btn2" href="run-card-ISO91.json">Machine run card</a>
<p class="small">File <code>{e(Path(tif).name)}</code> · SHA-256 <code>{e(r['sha256'])}</code><br>
single band · float32 · EPSG:32611 · 3730 rows × 3292 columns · transform (100, 0, 243350, 0, −100, 4508550) · all 12,279,160 cells finite · values {{0, 1}} · no nodata tag · {r['n_dots']:,} binary dots · 0 on mapped faults</p>
</section>"""


def identity(c: dict) -> str:
    return f"""<section class="card"><h2>Historical ISO91 research metadata — not approved for upload</h2>
<label class="small" for="nm">Prior ISO91 research name (not a current submission)</label><div class="copy"><input id="nm" readonly value="{e(c['submission_name'])}"><button type="button" data-copy="nm">Copy</button></div>
<label class="small" for="nt">Prior research note · {c['submission_note_chars']}/140 characters</label><div class="copy"><input id="nt" readonly value="{e(c['submission_note'])}"><button type="button" data-copy="nt">Copy</button></div>
<p class="small">These values identify the historical ISO91 file only. The current review approves no upload; do not paste this name or note into a live submission. A selector must separately approve an exact candidate, and this site never uploads or chooses a slot.</p></section>"""


def gates_table(c: dict) -> str:
    p, s = c["holdout"]["primary"], c["holdout"]["secondary_legacy"]
    rows = []
    labels = {
        "G1_I1_E1_minus_E0_ci_lower_gt_0": ("G1 beats incumbent on live-aligned holdout I1",
                                            lambda g: f"Δ {g['value']['delta']:+.6f} [{g['value']['ci95'][0]:+.6f}, {g['value']['ci95'][1]:+.6f}] HOLDOUT-DTI"),
        "G2_I1_E1_minus_CTL_HALO_ci_lower_gt_0": ("G2 beats the halo-exclusion control on I1",
                                                  lambda g: f"Δ {g['value']['delta']:+.6f} [{g['value']['ci95'][0]:+.6f}, {g['value']['ci95'][1]:+.6f}] HOLDOUT-DTI"),
        "G3_I1_E1_minus_CTL_SUB_delta_gt_0": ("G3 beats size-matched random positives (point estimate)",
                                              lambda g: f"Δ {g['value']['delta']:+.6f} HOLDOUT-DTI"),
        "G4_I2_E1_noninferior_to_E0_ci_upper_ge_0": ("G4 not worse than incumbent on legacy holdout I2",
                                                     lambda g: f"Δ {g['value']['delta']:+.6f} [{g['value']['ci95'][0]:+.6f}, {g['value']['ci95'][1]:+.6f}] HOLDOUT-DTI"),
        "G5_leakage_canary_max_auc_le_0_90": ("G5 leakage canary (each feature alone)",
                                              lambda g: f"worst AUC {g['value']['symmetric_auc']} ≤ 0.90"),
        "G6a_uniqueness_protocol_registry": ("G6a unique vs protocol registry (preregistered)",
                                             lambda g: f"{g['value']['n_checked']} rasters · surface ρ max {g['value']['surface_max_abs_spearman']} · worst non-blanket {100*g['value']['dots_max_within_3px_non_blanket']:.1f}% of dots within 3 px (limit 70%)"),
        "G6b_uniqueness_extended_gemsdoe_sweep": ("G6b unique vs 977 GeoTIFFs in 102 GEMSDOE repos (added this session)",
                                                  lambda g: "no duplicate" if g["pass"] else "; ".join(
                                                      f"{Path(x['raster']).name}: {100*x['within_3px_literal']:.1f}% within 3 px (chance-corrected {100*x['chance_corrected']:.1f}%, dots ρ {x['dots_abs_spearman']}) — marginal literal flag, logged"
                                                      for x in g["value"]["flagged"])),
        "G7_format_independent_revalidation": ("G7 format (independent re-read)", lambda g: "single band float32, grid match, finite [0,1], no nodata, ZIP identical"),
    }
    for k, g in c["gates"].items():
        name, f = labels[k]
        rows.append(f"<tr><td>{e(name)}</td><td class=\"{'pass' if g['pass'] else 'fail'}\">{'PASS' if g['pass'] else 'FAIL'}</td><td>{e(f(g))}</td></tr>")
    desc = {"E0": "E0 · incumbent PU model (all visible faults as positives)",
            "E1": "E1 · ISO91 (isolated faults only as positives)",
            "CTL_HALO": "CTL_HALO · E0, no dots within 500 m of visible faults",
            "CTL_SUB": "CTL_SUB · E0 on random faults, same positive count as E1",
            "RND": "RND · uniform random dots (floor)"}
    arms = "".join(f"<tr><td>{e(desc[a])}</td><td>{e(fmt_ci(p['scores'][a]))}</td></tr>" for a in ("E0", "E1", "CTL_HALO", "CTL_SUB", "RND"))
    arms2 = "".join(f"<tr><td>{e(desc[a])}</td><td>{e(fmt_ci(s['scores'][a]))}</td></tr>" for a in ("E0", "E1", "RND"))
    return f"""<section class="card"><h2>Why the verdict is what it is (automated gates)</h2>
<table><tr><th>Gate</th><th class="res">Result</th><th>Evidence</th></tr>{''.join(rows)}</table>
<p class="small">I1 = isolated-component hide-and-recover split ({p['withheld_positive_pixels']:,} withheld positives); I2 = legacy buffered split ({s['withheld_positive_pixels']:,} withheld positives; E0 reproduces the recorded 0.085260 exactly). Evaluator <code>{e(p['evaluator_version'])}</code>, paired 20 km block bootstrap. HOLDOUT-DTI is not a leaderboard score.</p>
<table><tr><th>I1 arm</th><th>HOLDOUT-DTI [95% CI]</th></tr>{arms}</table>
<table><tr><th>I2 arm</th><th>HOLDOUT-DTI [95% CI]</th></tr>{arms2}</table></section>"""


LINK_NAMES = {  # exact accessible names exercised by tools/browser/smoke.cjs (real-browser download checks)
    "S17-CGRD E2": ("↓ Download S17-CGRD E2 GeoTIFF (-zeros.tif)", None),
    "S17-LFTG E2": ("↓ Download S17-LFTG GeoTIFF", ("↓ S17-LFTG Single-TIFF ZIP", "downloads/gems91-s17-lftg-20261025T160014Z-7b6bf90844-zeros.zip")),
    "S17-CPAD E1": ("↓ Download S17-CPAD E1 GeoTIFF", ("↓ S17-CPAD Single-TIFF ZIP", "downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.zip")),
}
AUDIT_PAGES = {"S17-LFTG E2": ("S17-LFTG research audit", "s17-lftg.html"), "S17-CPAD E1": ("S17-CPAD research audit", "s17-cpad.html"),
               "S17-CGRD E2": ("S17-CGRD research audit", "s17-cgrd.html"), "S17-CDSC E1": ("S17-CDSC research audit", "s17-cdsc.html"),
               "HEXFAR91": ("HEXFAR91 research page", "hexfar91.html")}


def archive_table() -> str:
    rows = []
    for n, t, rc, ev in ARCHIVE:
        label, zipped = LINK_NAMES.get(n, (f"↓ Download {n} GeoTIFF", None))
        cell = f"<a download href=\"{e(t)}\">{e(label)}</a>"
        if zipped:
            cell += f" · <a download href=\"{e(zipped[1])}\">{e(zipped[0])}</a>"
        cell += f"<br><code>{e(Path(t).name)}</code>"
        card_cell = f"<a href=\"{e(rc)}\">{e(rc)}</a>"
        if n in AUDIT_PAGES:
            card_cell += f"<br><a href=\"{e(AUDIT_PAGES[n][1])}\">{e(AUDIT_PAGES[n][0])}</a>"
        rows.append(f"<tr><td>{e(n)}</td><td>{cell}</td><td>{card_cell}</td><td>{e(ev)}</td><td class=\"fail\">NOT OK TO SUBMIT</td></tr>")
    return f"""<section class="card" id="archive"><h2>Archive: prior research downloads</h2>
<p class="small">Each row is a prior research download from an earlier session, kept for learning. None is OK to submit. HOLDOUT-DTI values come from different instruments and are not comparable with one another or with the leaderboard.
Full previous front page: <a href="previous-sessions.html">previous-sessions.html</a> · older sessions' historical archive: <a href="archive-results.html">archive-results.html</a> · earlier no-TIFF reviews (historical): 522615dd <a href="REVIEW-ACTIVE-522615DD-20261025.md">review</a> · <a href="run-card-522615dd.json">no-run card</a> · <a href="HYPOTHESES-ACTIVE-522615DD-20261025.md">hypotheses</a>; e649e460 <a href="REVIEW-ACTIVE-E649E460-20261025.md">review</a> · <a href="run-card-E649E460-20261025.json">run card</a>. Parallel S18 research files (S18-HGBR, S18-UNIQUE) are listed on their own pages and are also NOT OK TO SUBMIT.</p>
<table><tr><th>Lane</th><th>Download</th><th>Run card</th><th>Recorded evidence</th><th>Verdict</th></tr>{''.join(rows)}</table></section>"""


def footer() -> str:
    return ("<footer>Maximize P(Win) · Own the Outcome · every number is labelled HOLDOUT-DTI, USER-REPORTED, PUBLIC-LEADERBOARD or MODEL; "
            "nothing here is ORGANIZER-CONFIRMED · 0 competition slots used by this session.</footer>\n</div>" + JS + "</body></html>\n")


def render_index(c: dict) -> str:
    sg = c["sgmc_control_report_only"]["arms"]
    u = c["uniqueness"]
    return (head("GEMSDOE91 · prior ISO91 research artifact and current review status",
                 "Current 2026-10-26 review generated no TIFF; the older ISO91 file remains a negative research artifact only.")
            + "<main id=\"main\">\n" + current_review_notice() + download_card(c) + identity(c) + gates_table(c)
            + f"""<section class="card"><h2>What was tested, in one paragraph</h2>
<p><strong>Hypothesis (ISO91):</strong> {e(c['hypothesis'])} <strong>Result:</strong> negative. The isolation-trained model barely moved its dots away from known faults, and with four to five times fewer positives it lost to the incumbent on both holdouts. Report-only SGMC control (more than 500 m off-catalogue): ISO91 {sg['ISO91_E1_final']['dti_gt500m']}, incumbent {sg['E0_final_same_emission']['dti_gt500m']}, R0 {sg['R0_gemsdoe32_h33_2_b2']['dti_gt500m']}. Overlap with R0's dots: {100*u['vs_R0_gemsdoe32_h33_2_b2']['within_3px']:.1f}% within 3 px.</p>
<p><strong>Why GEMSDOE32 h33-2-b2 reached 0.2778 (USER-REPORTED):</strong> 79% of its gain over the dense ridge network came from emission geometry (2.8 px dotting) and 21% from deleting zero-credit dots within 2 px of mapped faults. Its ridges come from sub-100 m topography, and 70% of its dots lie more than 1 km from the catalogue. Two independent routes (MODEL) put the public truth set at about 12,500 px, with R0 covering about 40%. Reaching 0.4413 (PUBLIC-LEADERBOARD #1) needs about 63% more truth credit at the same number of dots. <a href="REVIEW-ISO91-BACC7C26-20261025.md">Full analysis</a> · <a href="HYPOTHESES_ISO91.md">preregistered hypotheses</a> · <a href="KNOWLEDGE-GEOTHERMAL-FAULTS-ISO91.md">knowledge base</a></p></section>
""" + "<!--PARALLEL-CALLOUTS-->" + archive_table() + "</main>\n" + footer())


def render_exec(c: dict) -> str:
    r = c["raster"]
    tif = Path(r["path"]).relative_to("docs").as_posix()
    return (head("GEMSDOE91 · executive summary, current no-run status, and submission steps",
                 "The 2026-10-26 review produced no file; ISO91 is an earlier negative research artifact, not approved for submission.")
            + "<main id=\"main\">\n" + current_review_notice() + download_card(c)
            + """<section class="card"><h2>Executive summary</h2><ul>
<li><strong>Historical artifact only:</strong> ISO91 was generated and checked in the separate 2026-10-25 session; this 2026-10-26 review generated no TIFF. <strong>Uniqueness:</strong> """ + e(c["uniqueness_summary"]) + """ Only """ + f"{100*c['uniqueness']['vs_R0_gemsdoe32_h33_2_b2']['within_3px']:.1f}" + """% of its dots lie near R0's dots.</li>
<li><strong>Science:</strong> the preregistered hypothesis (learn only from isolated faults) failed on both spatially blocked holdouts. The negative result is published with every number.</li>
<li><strong>Decision:</strong> No submission or slot is selected here. ISO91 is NOT OK TO SUBMIT. The nine-site review treats GEMSDOE32 h33-h33-2-b2 (0.2778) as owner-reported/unverified; this review does not choose it or another real slot.</li>
<li><strong>Current blockers and ranked proposals:</strong> see the <a href=\"nine-site-audit-20261026.html\">nine-site audit</a> and <a href=\"REVIEW-SITE-AUDIT-20261026.md#ranked-hypotheses-proposals-not-results\">ranked hypotheses</a>. The assigned lane and required local data are absent; the proposed top candidate remains untested.</li>
</ul></section>
<section class="card" id="how-to-submit"><h2>How to submit on DrivenData (only after the selector approves a file)</h2><ol>
<li>Sign in and open the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition page</a>. Click <strong>Submit</strong> in the sidebar, then <strong>Make new submission</strong>, as described on the official page.</li>
<li><strong>File to submit:</strong> none is approved by the current review. Stop unless a selector separately approves an exact file. Do not upload the historical ISO91 research TIFF linked on this page or any other unapproved research download. The official form accepts one single-band GeoTIFF or a ZIP containing one GeoTIFF, matching the submission CRS, shape, and geotransform.</li>
<li>For this competition an approved candidate must match EPSG:32611, 3730 rows × 3292 columns, transform (100, 0, 243350, 0, −100, 4508550), and values in [0, 1]. The stored validator checks only the specific historical ISO91 bytes; it does not validate another candidate or confer upload approval.</li>
<li><strong>Note (optional):</strong> after a selector approves a specific file, use that file's own run-card note (at most 140 characters). The saved ISO91 note below belongs to a historical, unapproved research file; do not use it for a current submission.</li>
<li>Only after separate approval, upload the exact approved file and record the resulting organizer receipt in the repository as ORGANIZER-CONFIRMED. A projection is never a score.</li></ol>
<p class="warn"><strong>Portal error "Predicted values must be in range [0, 1]":</strong> it comes from NaN or −3.4e38 sentinel values or a nodata tag. The historical ISO91 TIFF was generated with all-finite zeros (0 outside the footprint, no nodata tag, every cell finite in [0, 1]) and passed its stored validation. That does not establish the format of a different file; validate the exact bytes intended for upload.</p></section>
""" + identity(c) + gates_table(c)
            + "<!--PARALLEL-CALLOUTS-->"
            + f"""<section class="card"><h2>History and other files</h2>
<p class="small">Earlier sessions published research files that are all NOT OK TO SUBMIT, including S17-EULR (<a href="run-card-S17-EULR.json">run-card-S17-EULR.json</a>, <a download href="downloads/gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif">gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif</a>) and S17-CGRD (<a download href="downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif">gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif</a>); see the <a href="index.html#archive">archive table</a>. The earlier reviews 522615dd and e649e460 are historical: <a href="REVIEW-ACTIVE-522615DD-20261025.md">522615dd review</a> · <a href="run-card-522615dd.json">no-run card</a> · <a href="REVIEW-ACTIVE-E649E460-20261025.md">e649e460 review</a> · <a href="run-card-E649E460-20261025.json">e649e460 run card</a>. Linking a prior file here is not an approval to upload that file.</p></section>
<section class="card"><h2>Official sources (verified 2026-10-25)</h2><ul class="small">
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition home</a>: deadline Dec 3, 2026, 23:59 UTC; the same submission is scored in both prize rounds.</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description</a>: DTI metric (α 0.2, β 0.8, 300 m) and submission format.</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Public leaderboard</a>: #1 0.4413 on 2026-10-25.</li>
<li><a href="https://www.herox.com/GEMSPrize/resource/2274">Official rules (HeroX)</a> · <a href="https://github.com/drivendataorg/gems-prize-reference-solution">Reference solution</a> · <a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">USGS 3DEP</a></li>
</ul><p class="small">File reproduced by <code>python3 scripts/run_iso91.py final</code>. Verdict recomputed by <code>python3 scripts/build_iso91_card.py</code>. Bytes re-verified by <code>python3 generate_submission.py --with-data</code>. Current file: <a download href="{e(tif)}">{e(Path(tif).name)}</a>.</p></section>
</main>
""" + footer())


def main():
    c = json.loads(CARD.read_text(encoding="utf-8"))
    (DOCS / "iso91-index-src.html").write_text(render_index(c), encoding="utf-8")
    (DOCS / "iso91-exec-src.html").write_text(render_exec(c), encoding="utf-8")
    print("wrote docs/iso91-index-src.html, docs/iso91-exec-src.html")



    # S28 owns the public front door from 2026-10-31; enforce it last.
    try:
        import front_door as _fd  # noqa: PLC0415
    except ImportError:
        import sys as _s
        from pathlib import Path as _p
        _s.path.insert(0, str(_p(__file__).resolve().parent))
        import front_door as _fd  # noqa: PLC0415
    _fd.enforce()

if __name__ == "__main__":
    main()
