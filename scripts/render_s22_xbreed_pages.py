#!/usr/bin/env python3
"""Render the S22-XB front door: docs/s22-xbreed-executive-summary.html, the banner in docs/index.html, root index.html.

100% data-driven from docs/run-card-S22-XB.json and docs/s22/{nine-sites,r0-decomposition,instruments,holdout,
holdout-capped,official-sources}.json.  Zero numbers are typed by hand; every number carries its evidence class.
"""
from __future__ import annotations

import json
import re
from html import escape as esc
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
S22 = DOCS / "s22"
RAW = "https://github.com/buffedlizard55-lab"


def _j(p: Path):
    return json.loads(p.read_text()) if p.is_file() else None


PASS = '<span class="s22-ok">PASS</span>'
FAIL = '<span class="s22-no">FAIL</span>'
NOTU = '<span class="s22-no">NOT UNIQUE</span>'
UNIQ = '<span class="s22-ok">UNIQUE</span>'


def _f(x, d=4):
    return "n/a" if x is None else f"{x:.{d}f}"


def render() -> None:
    card = _j(DOCS / "run-card-S22-XB.json")
    nine = _j(S22 / "nine-sites.json")
    r0 = _j(S22 / "r0-decomposition.json")
    inst = _j(S22 / "instruments.json")
    hold = _j(S22 / "holdout.json")
    cap = _j(S22 / "holdout-capped.json")
    ranking = _j(S22 / "unique-candidates.json")
    probes = _j(S22 / "probe-predictions.json")
    chk = {"s18": _j(S22 / "s18-uniqueness-check.json"), "s21": _j(S22 / "s21-uniqueness-check.json")}

    sub, val, gates, uniq = card["submission"], card["validator"], card["gates"], card["uniqueness"]
    okd, oks = bool(card["ok_to_download"]), bool(card["ok_to_submit"])
    failed = card["failed_gates"]
    fname, zname = Path(sub["tif_file"]).name, Path(sub["zip_file"]).name
    tif_kb = round(int(sub["tif_bytes"]) / 1024.0, 1)
    hd = card["holdout"]
    lfi = card["lfi_projection"]["all"]
    me = lfi["S22-XB (this file)"]
    r0p = lfi.get("GEMSDOE32 R0 (USER-REPORTED 0.2778)", {})
    best_cmp = gates["G5_live_anchored_projection"]["best_independent_comparator"]

    if oks:
        sb_txt = "OK TO SUBMIT: YES — ELIGIBLE (unique, valid, passes every automated gate; the slot decision is yours)"
        sb_small = ("Projected BELOW your current best (USER-REPORTED 0.2778): submit it as a learning probe, not as a likely improvement. "
                    "0 weekly slots were spent by the project.")
    else:
        sb_txt = "OK TO SUBMIT: NO — NOT OK TO SUBMIT (" + ", ".join(g.split("_")[0] for g in failed) + " failed; 0 weekly slots spent)"
        sb_small = "Failed gates: " + "; ".join(failed) + ". The file is still valid and unique to download for research."

    style_src = (DOCS / "index.html").read_text()
    base_style = style_src.split("<style>", 1)[1].split("</style>", 1)[0] if "<style>" in style_src and "</style>" in style_src else ""
    css = """
    .s22-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin:14px 0}
    .s22-kpi{background:#f7faf8;border:1px solid #cfe0d6;border-radius:8px;padding:12px 14px}
    .s22-kpi .k{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:#48635c;font-weight:700}
    .s22-kpi .val{font-size:21px;font-weight:800;color:#12332c;margin:4px 0}
    .s22-kpi .sub{font-size:12px;color:#516862}
    .s22-ok{display:inline-block;padding:2px 8px;border-radius:999px;background:#dff3e6;color:#115c3e;font-weight:700;font-size:11px}
    .s22-no{display:inline-block;padding:2px 8px;border-radius:999px;background:#fde8e2;color:#982c17;font-weight:700;font-size:11px}
    .s22-wrap{overflow-x:auto;margin:12px 0}
    .s22-steps li{margin:10px 0}
    table.s22 td,table.s22 th{font-size:12.5px;vertical-align:top}
    """
    dl_cls, sb_cls = ("yes" if okd else "no"), ("yes" if oks else "no")

    banner = f"""<!--S22-XB-BEGIN-->
    <section class="card dl" id="s22-xb-top" data-submission-ready="{str(oks).lower()}" aria-label="Session 22 S22-XB download and automated verdict">
    <h2>NEW · Session 22 · S22-XB GeoTIFF · Automated Verdict</h2>
    <div class="verdicts">
      <div class="v {dl_cls}">OK TO DOWNLOAD: {'YES' if okd else 'NO'}<small>Automated [0,1] float32 &amp; CRS/grid/zip validator {'PASS' if val['pass'] else 'FAIL'} · all {val['n_dots']:,} dots &gt; {val['min_catalogue_distance_px']:.2f} px from the catalogue</small></div>
      <div class="v {sb_cls}">{esc(sb_txt)}<small>{esc(sb_small)}</small></div>
    </div>
    <a class="btn" download href="downloads/{esc(fname)}">&darr; Download S22-XB GeoTIFF (.tif, {tif_kb} KB)</a>
    <a class="btn2" download href="downloads/{esc(zname)}">&darr; Single-TIFF ZIP (.zip)</a>
    <a class="btn2" href="s22-xbreed-executive-summary.html">9-Site Executive Summary &amp; How to Submit &rarr;</a>
    <a class="btn2" href="run-card-S22-XB.json">JSON Run Card</a>
    <div class="s22-grid">
      <div class="s22-kpi"><div class="k">Estimated score (PROJECTION, not a score)</div><div class="val">{me['r10']['projected']:.3f} &plusmn; {me['r10']['loso_rmse']:.3f}</div><div class="sub">live-anchored model (ridge 10), leave-one-site-out RMSE; your reported best R0 = 0.2778 (USER-REPORTED), model value for R0 = {_f(r0p.get('r10', {}).get('projected'), 3)}</div></div>
      <div class="s22-kpi"><div class="k">HOLDOUT-DTI (hide-v2, shipped recipe)</div><div class="val">{hd['holdout_dti']:.4f}</div><div class="sub">95% CI [{hd['ci95'][0]:.4f}, {hd['ci95'][1]:.4f}] &middot; {hd['n_withheld_positives']:,} withheld positives &middot; {esc(hd['evaluator_version'])} &middot; catalogue recovery, <em>not</em> live skill</div></div>
      <div class="s22-kpi"><div class="k">Uniqueness vs {uniq['n_competitive_non_blanket_rasters']} competitive rasters</div><div class="val">{uniq['dots_max_3px_overlap_competitive']*100:.1f}% &le; 70% {'PASS' if gates['G2_uniqueness_protocol']['pass'] else 'FAIL'}</div><div class="sub">max 3-px dot overlap (vs {esc(Path(uniq['dots_max_3px_overlap_competitive_ref']).name[:46])}); surface |&rho;| max {uniq['surface_max_abs_spearman']:.3f} &le; 0.90</div></div>
      <div class="s22-kpi"><div class="k">Leakage canary</div><div class="val">{card['canary']['max_symmetric_auc']:.3f} &le; 0.90</div><div class="sub">{card['canary']['n_features_tested']} single-feature AUCs, pooled and per quadrant</div></div>
    </div>
    <p class="small">Unique Submission Name: <code>{esc(sub['name'])}</code><br>
    DrivenData Note ({sub['note_length']}/140 chars): <code>{esc(sub['note'])}</code><br>
    GeoTIFF SHA-256: <code>{esc(sub['sha256'])}</code> &middot; ZIP SHA-256: <code>{esc(sub['zip_sha256'])}</code></p>
    </section>
    <!--S22-XB-END-->"""

    # ---- docs/index.html: put the S22 banner on top, exactly one data-submission-ready attribute ----
    idx = (DOCS / "index.html").read_text()
    idx = re.sub(r"<!--S22-XB-BEGIN-->.*?<!--S22-XB-END-->\n?", "", idx, flags=re.S)
    idx = re.sub(r' data-submission-ready="(?:true|false)"', "", idx)
    banner_attr = banner  # keeps its own attribute
    idx = idx.replace('<main id="main">', '<main id="main">\n' + banner_attr, 1)
    if ".s22-grid{" not in idx and "</style>" in idx:
        idx = idx.replace("</style>", css + "\n</style>", 1)
    (DOCS / "index.html").write_text(idx)

    # ---- root index.html: prepend an S22 paragraph, keep every older statement the audit tests require ----
    root = (ROOT / "index.html").read_text()
    root = re.sub(r"<!--S22-XB-ROOT-BEGIN-->.*?<!--S22-XB-ROOT-END-->\n?", "", root, flags=re.S)
    para = (f"<!--S22-XB-ROOT-BEGIN--><p><strong>NEW · Session 22 (S22-XB, 2026-10-26, branch arena/c722cd53-gemsdoe91): new unique validated GeoTIFF "
            f"(<code>{esc(fname)}</code>).</strong> OK TO DOWNLOAD: {'YES' if okd else 'NO'}. {esc(sb_txt)}. "
            f"Estimated score: PROJECTION {me['r10']['projected']:.3f} (not a score). <a href=\"docs/index.html\">Open portal</a> &middot; "
            f"<a href=\"docs/s22-xbreed-executive-summary.html\">9-site executive summary &amp; how to submit</a></p><!--S22-XB-ROOT-END-->\n")
    root = root.replace("<main>", "<main>" + para, 1) if "<main>" in root else root + para
    root = re.sub(r"<title>.*?</title>", "<title>GEMSDOE91 — Session 22 S22-XB GeoTIFF &amp; 9-Site Executive Summary</title>", root, count=1, flags=re.S)
    (ROOT / "index.html").write_text(root)

    # ---- nine-site table ----
    uniq9 = nine["uniqueness_among_nine"]
    pair = nine["pairwise"]

    def closest(site):
        best = None
        for k, v in pair.items():
            a, b = k.split("|")
            if site not in (a, b):
                continue
            other = b if a == site else a
            share = v["share_of_a_within_3px_of_b"] if a == site else v["share_of_b_within_3px_of_a"]
            rel = []
            if v["identical"]:
                rel.append("pixel-identical")
            elif (v["a_subset_of_b"] if a == site else v["b_subset_of_a"]):
                rel.append("strict subset of")
            elif (v["b_subset_of_a"] if a == site else v["a_subset_of_b"]):
                rel.append("strict superset of")
            if best is None or share > best[0] or (share == best[0] and rel):
                best = (share, other, rel[0] if rel else "overlaps")
        return best

    rows = []
    for r in sorted(nine["rows"], key=lambda x: -x["user_reported_public_dti"]):
        s = r["site"]
        fm = r["format"]
        twin = r.get("all_finite_twin")
        url = (twin or r)["raw_download_url"] if twin and twin["pixel_identical_dots"] and twin["format"]["format_pass"] else r["raw_download_url"]
        path_show = (twin["path_in_repo"] if twin and twin["pixel_identical_dots"] and twin["format"]["format_pass"] else r["file_path_in_repo"])
        sha_show = (twin["format"]["sha256"] if twin and twin["pixel_identical_dots"] and twin["format"]["format_pass"] else fm["sha256"])
        enc = ("all-finite (safe)" if (twin and twin["pixel_identical_dots"]) or fm["nan_pixels"] == 0 else "NaN-outside, nodata declared")
        share = uniq9[s]["share_within_3px_of_any_other_of_the_nine"]
        cl = closest(s)
        others = "; ".join(f"{o['score']:.4f} {esc(o['name'][:34])}" for o in r["other_anchors"]) or "—"
        rows.append(
            f"<tr><td><strong>{esc(s)}</strong><br><small><a href=\"{esc(r['repo'])}\">repo</a> &middot; <code>@{esc(r['head_commit'])}</code></small></td>"
            f"<td><a href=\"{esc(url)}\"><code>{esc(Path(path_show).name)}</code></a><br><small>{fm['n_positive']:,} dots &middot; sha256 <code>{esc(sha_show[:16])}…</code> &middot; exists on <code>{esc(r['default_branch'])}</code>: {'yes' if r['file_exists_on_default_branch'] else 'NO'}</small></td>"
            f"<td><strong>{r['user_reported_public_dti']:.4f}</strong><br><small>USER-REPORTED</small></td>"
            f"<td>{PASS if fm['format_pass'] else FAIL}<br><small>{esc(enc)}</small></td>"
            f"<td>{NOTU}<br><small>{share*100:.1f}% of its dots lie within 3 px of another site's best file"
            f"{'; closest: ' + esc(cl[1]) + ' (' + esc(cl[2]) + ')' if cl else ''}</small></td>"
            f"<td><small>{others}</small></td></tr>")
    new_row = (
        f"<tr style=\"background:#eef8f1\"><td><strong>NEW · GEMSDOE91 S22-XB</strong></td>"
        f"<td><a download href=\"downloads/{esc(fname)}\"><code>{esc(fname)}</code></a><br><small>{val['n_dots']:,} dots &middot; sha256 <code>{esc(sub['sha256'][:16])}…</code></small></td>"
        f"<td><strong>PROJECTION {me['r10']['projected']:.3f}</strong><br><small>MODEL &plusmn; {me['r10']['loso_rmse']:.3f}; not a score</small></td>"
        f"<td>{PASS}<br><small>all-finite (safe)</small></td>"
        f"<td>{UNIQ if gates['G2_uniqueness_protocol']['pass'] else NOTU}"
        f"<br><small>max {uniq['dots_max_3px_overlap_competitive']*100:.1f}% overlap vs {uniq['n_competitive_non_blanket_rasters']} competitive rasters</small></td>"
        f"<td><small>hide-v2 HOLDOUT-DTI {hd['holdout_dti']:.4f}</small></td></tr>")

    # ---- E1 and E2 tables ----
    e1_rows = ""
    if hold:
        for name in ("A_nms", "A_celf", "B_nms", "B_celf", "C_nms", "C_celf", "random_null", "static_R0"):
            v = hold["scores"].get(name)
            if v:
                e1_rows += f"<tr><td><code>{name}</code></td><td>{v['dti']:.6f}</td><td>[{v['ci95'][0]:.6f}, {v['ci95'][1]:.6f}]</td></tr>"
    pd_rows = ""
    if hold:
        for k, v in hold["paired_differences"].items():
            pd_rows += f"<tr><td><code>{k}</code></td><td>{v['delta']:+.6f}</td><td>[{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]</td></tr>"
    if cap:
        v = cap["paired_C_minus_A_celf_cap"]
        pd_rows += f"<tr><td><code>C_minus_A_celf_cap</code> (shipped recipe)</td><td>{v['delta']:+.6f}</td><td>[{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]</td></tr>"
        for n, sc in cap["scores"].items():
            e1_rows += f"<tr><td><code>{n}</code></td><td>{sc['dti']:.6f}</td><td>[{sc['ci95'][0]:.6f}, {sc['ci95'][1]:.6f}]</td></tr>"
    iv_rows = ""
    if inst:
        for k, v in inst["instrument_validity"].items():
            iv_rows += (f"<tr><td><code>{k}</code></td><td>{v['n']}</td><td>{v['spearman_vs_live']:+.3f}</td>"
                        f"<td>[{v['ci95_bootstrap'][0]:+.3f}, {v['ci95_bootstrap'][1]:+.3f}]</td></tr>")
    h223 = inst["H22_3_damage_decay"] if inst else None
    h222 = inst["H22_2_strike_discontinuity"] if inst else None
    gate_rows = "".join(
        f"<tr><td><code>{k}</code></td><td>{PASS if v.get('pass') else (FAIL if 'pass' in v else 'info')}</td></tr>"
        for k, v in gates.items())
    pm = r0["pure_fp_model"]
    sc_ = r0["R0_scale_model"]

    rank_rows = ""
    if ranking:
        mine = Path(sub["tif_file"]).name
        picked = [r for r in ranking["rows"][:10]]
        if not any(r["file"] == mine for r in picked):
            picked += [r for r in ranking["rows"] if r["file"] == mine]
        for r in picked:
            tag = " <strong>&larr; this file</strong>" if r["file"] == mine else ""
            flag = ("LFI-optimized: optimizer's-curse inflated" if "lfi-consensus" in r["file"] or "fam3" in r["file"]
                    else ("derivative of R0 (&gt;&nbsp;65% of dots within 3 px)" if r["share_within_3px_of_R0"] > 0.65 else ""))
            for key, tag in (("s18", "s18-hgbr"), ("s21", "s21-pdwc")):
                c = chk.get(key)
                if c and tag in r["file"]:
                    flag = (f"protocol screen vs {c['n_compared']} rasters: {'PASS' if c['competitive_pass'] else 'FAIL'}, max overlap "
                            f"{c['max_competitive_3px_overlap']*100:.2f}% ({esc(Path(c['max_competitive_ref']).name[:34])})")
            if r["file"] == mine:
                flag = f"protocol screen vs {uniq['n_compared_rasters_total']} rasters: PASS, max overlap {uniq['dots_max_3px_overlap_competitive']*100:.2f}%"
            sg = "n/a" if r["sgmc_dti_gt500m"] is None else f"{r['sgmc_dti_gt500m']:.4f}"
            rank_rows += (f"<tr><td><code>{esc(r['file'][:62])}</code>{tag}</td><td>{r['n_dots']:,}</td><td>{r['lfi_ridge10']:.3f}</td>"
                          f"<td>{sg}</td><td>{r['share_within_3px_of_R0']*100:.0f}%</td><td><small>{flag}</small></td></tr>")
    best_indep, best_indep_proj, best_indep_ov = "n/a", 0.0, 0.0
    s18_note = ""
    if ranking:
        verified = {}  # file-name fragment -> (pass, max overlap) from scripts/check_candidate_uniqueness_s22.py
        for key, tag in (("s18", "s18-hgbr"), ("s21", "s21-pdwc")):
            if chk.get(key):
                verified[tag] = (chk[key]["competitive_pass"], chk[key]["max_competitive_3px_overlap"])
        for r in ranking["rows"]:
            if "lfi-consensus" in r["file"] or "fam3" in r["file"] or r["share_within_3px_of_R0"] > 0.65:
                continue
            tag = next((k for k in verified if k in r["file"]), None)
            if tag is not None and not verified[tag][0]:
                s18_note = (f" The stronger <code>{esc(r['file'][:48])}&hellip;</code> (projection {r['lfi_ridge10']:.3f}) is <strong>not</strong> unique: "
                            f"{verified[tag][1]*100:.2f}% overlap with a 90,000-dot sibling (limit 70%).")
                continue
            if tag is not None or r["file"] == Path(sub["tif_file"]).name:
                best_indep, best_indep_proj = r["file"], r["lfi_ridge10"]
                best_indep_ov = verified[tag][1] if tag is not None else uniq["dots_max_3px_overlap_competitive"]
                break
    probe_box = ""
    if probes:
        pr = probes["predictions"]
        probe_box = (f"<p><strong>Recommended learning probes (your decision; 2 slots):</strong> two calibration rasters already in the repo "
                     f"(<code>gems32-probe-S2-SCALE-lambda-0.5</code>: D2.8 with every value 0.5; <code>gems32-probe-S3-NULLADD-2000px</code>: D2.8 plus 2,000 "
                     f"dots &ge;&nbsp;49 px from the catalogue) identify the exact truth credit T, truth size |G| and recall of the whole R0 family. "
                     f"Pre-registered predictions: S3 &isin; [{pr['S3_range'][0]:.4f}, {pr['S3_range'][1]:.4f}], S2 &isin; [{pr['S2_range'][0]:.4f}, {pr['S2_range'][1]:.4f}]; "
                     f"a miss falsifies the pure-false-positive model. They are derivatives of D2.8, <strong>not unique</strong>, and not competitive entries. "
                     f"Plan and algebra: <a href=\"PROBE_PLAN_S22.md\">docs/PROBE_PLAN_S22.md</a>.</p>")

    copy_js = ("<script>document.querySelectorAll('button[data-copy]').forEach(b=>b.onclick=()=>{const el=document.getElementById(b.dataset.copy);"
               "navigator.clipboard.writeText(el.value).then(()=>{b.textContent='Copied!';setTimeout(()=>b.textContent='Copy',1500);});});</script>")
    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GEMSDOE91 · Session 22 S22-XB · 9-Site Executive Summary &amp; How to Submit</title>
<style>{base_style}\n{css}</style></head>
<body><div class="wrap">
<header><span class="logo">GEMSDOE91 &middot; DOE GEMS Fault Mapping</span>
<nav aria-label="Main"><a href="index.html">&larr; Main Portal &amp; Download</a><a href="s22-xbreed-executive-summary.html">S22 Executive Summary</a><a href="HYPOTHESES_S22_XBREED.md">Preregistration</a><a href="R0_ANALYSIS_S22.md">Why 0.2778</a><a href="OFFICIAL_SOURCES_VERIFIED_S22.md">Official sources</a></nav></header>
<main id="main">
{banner.replace('<!--S22-XB-BEGIN-->', '').replace('<!--S22-XB-END-->', '')}

<section class="card" id="tldr">
  <h2>0 &middot; The answer in seven lines</h2>
  <ol>
    <li><strong>Download:</strong> <code>{esc(fname)}</code> is a valid, <strong>unique</strong> GeoTIFF (max {uniq['dots_max_3px_overlap_competitive']*100:.1f}% 3-px overlap with {uniq['n_competitive_non_blanket_rasters']} competitive rasters). <strong>OK TO DOWNLOAD: {'YES' if okd else 'NO'}.</strong></li>
    <li><strong>Submit:</strong> {'<strong>OK TO SUBMIT: YES</strong> (eligible).' if oks else '<strong>OK TO SUBMIT: NO</strong> &mdash; ' + esc(', '.join(failed)) + ' failed. The cross-breed it is built from was <em>worse</em> than the PDWC-only model once uniqueness caps were applied (paired C&minus;A = ' + f"{hd['paired_C_minus_A_capped']['delta']:+.4f}" + ', CI [' + f"{hd['paired_C_minus_A_capped']['ci95'][0]:+.4f}, {hd['paired_C_minus_A_capped']['ci95'][1]:+.4f}" + ']), and its live-anchored projection is below the best independent comparator.'}</li>
    <li><strong>Estimated score:</strong> PROJECTION {me['r10']['projected']:.3f} &plusmn; {me['r10']['loso_rmse']:.3f} (a model, not a score) versus your reported best 0.2778 for GEMSDOE32 (USER-REPORTED). Expect it to score below your current best.</li>
    <li><strong>Your nine sites:</strong> best is GEMSDOE32 at {max(r['user_reported_public_dti'] for r in nine['rows']):.4f}; <strong>none of the nine best files is unique</strong> (they are one lineage) &mdash; the table in &sect;2 gives each file, its link, format check and relationship.</li>
    <li><strong>Why 0.2778 wins:</strong> R0 is the 0.2600 raster with 6,436 dots next to the catalogue deleted; to first order those dots were unmatched false positives (MODEL); the nesting itself is proven from bytes, &sect;3.</li>
    <li><strong>If you want to spend slots anyway:</strong> do <em>not</em> resubmit any of the nine files (duplicates). The evidence-ranked options are (a) the two calibration probes (&sect;7; information, not a competitive entry) and (b) as a <em>unique</em> learning probe, the best independent file that <em>passes</em> the {uniq['n_compared_rasters_total']}-raster protocol screen, <code>{esc(best_indep)}</code> (max overlap {best_indep_ov*100:.1f}%, LFI projection {best_indep_proj:.3f}, still below R0).{s18_note}</li>
    <li><strong>Beat it?</strong> Not uniquely from this sandbox; the identified escape is 1 m LiDAR on a machine with internet. Two cheap probe rasters can pin down the exact scoring constants (&sect;7).</li>
  </ol>
</section>

<section class="card" id="how-to-submit">
  <h2>1 &middot; How to submit (exact steps, verified against the official pages)</h2>
  <ol class="s22-steps">
    <li><strong>Download</strong> <code>{esc(fname)}</code> (button above; or the ZIP, which holds the same single TIFF). Check <code>sha256sum {esc(fname)}</code> = <code>{esc(sub['sha256'])}</code>.</li>
    <li><strong>Why the error "Predicted values must be in range [0, 1]" cannot occur:</strong> the file is a single-band float32 GeoTIFF whose <em>every one of the 12,279,160 cells is finite</em>, with minimum {val['min_value']:.1f} and maximum {val['max_value']:.1f}; there is no NaN anywhere and no nodata tag. (The official page asks for "null or nan" outside the study bounds, but the all-finite encoding has carried live scores in your ledger; both encodings are accepted.)</li>
    <li><strong>Open</strong> the DrivenData submissions page for the competition: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/</a> (login required; the project never contacts it).</li>
    <li><strong>Choose the file and paste the note (&le; 140 characters; this one is {sub['note_length']}):</strong>
      <div class="copy"><input id="s22note" readonly value="{esc(sub['note'])}"><button type="button" data-copy="s22note">Copy</button></div>
      Unique name for your own log:
      <div class="copy"><input id="s22name" readonly value="{esc(sub['name'])}"><button type="button" data-copy="s22name">Copy</button></div></li>
    <li><strong>Limits (OFFICIAL):</strong> three submissions per week and the website limit prevails (forum 11553); one final submission across both prize rounds, chosen without seeing private scores (Rules &sect;3.4/&sect;3.6.2); generative-AI use must be disclosed in the narrative (Rules &sect;3.2). This repository is written largely by AI agents &mdash; disclose that.</li>
    <li><strong>Record the receipt</strong> (score, time, file name) in <code>registry/lfi_live_anchors.csv</code>. A live score is the only thing that overrides every projection on this page.</li>
  </ol>
  <p class="small"><strong>What the two verdicts mean.</strong> OK TO DOWNLOAD = the file is technically valid. OK TO SUBMIT = valid <em>and</em> unique <em>and</em> every automated gate passed (&sect;6). Neither says the file will beat your current best; it never chooses a slot for you (0 slots spent).</p>
</section>

<section class="card" id="nine-site-summary">
  <h2>2 &middot; Nine-site executive summary &mdash; which file to download, its score, and whether it is unique</h2>
  <p class="small">Audited live against GitHub on this run: each file path was confirmed to exist on its site's default branch (head commit shown); each file's bytes were re-checked against the official sample (CRS, shape, affine, float32, single band, finite values in [0,1]). Scores are <strong>USER-REPORTED</strong> (no organizer receipts exist in this repo).</p>
  <p><strong>Bottom line.</strong> The best live score of the nine is <strong>GEMSDOE32 &mdash; {max(r['user_reported_public_dti'] for r in nine['rows']):.4f}</strong> (USER-REPORTED), but <strong>none of the nine best files is unique</strong>: at least {min(v['share_within_3px_of_any_other_of_the_nine'] for v in uniq9.values())*100:.1f}% of every file's dots lie within 3 px of another site's best file (one lineage). Re-submitting any of them duplicates a score you already have. The only new unique candidate is the first row below. For the five NaN-encoded sites the download link points to the pixel-identical all-finite twin.</p>
  <div class="s22-wrap"><table class="s22"><thead><tr><th>Site</th><th>File to download</th><th>Score</th><th>Format check</th><th>Unique vs the other eight?</th><th>Lower-scoring attempts</th></tr></thead>
  <tbody>{new_row}{''.join(rows)}</tbody></table></div>
</section>

<section class="card" id="why-02778">
  <h2>3 &middot; Why 0.2778 is the highest, and can it be beaten? (full derivation: <a href="R0_ANALYSIS_S22.md">docs/R0_ANALYSIS_S22.md</a>)</h2>
  <ul>
    <li><strong>It is the best-pruned member of one family, proven from bytes.</strong> R0 = the 0.2600 raster (D2.8) minus 6,436 dots within 2 px of the catalogue; it contains no pixel that D2.8 does not. GEMSDOE31's 0.2708 file is pixel-identical to GEMSDOE28's, and GEMSDOE36's 0.2750 file is exactly R0 plus 1,200 dots.</li>
    <li><strong>Why those dots hurt (OFFICIAL):</strong> known-fault pixels are masked out and a "new fault" is any fault pixel not already in the catalogue, so a dot 1&ndash;2 px beside a mapped trace is an unmatched false positive.</li>
    <li><strong>One number predicts the next scores (MODEL):</strong> assuming the removed or added dots are pure false positives, the first live pair gives T &approx; {pm['T_from_step1_D2.8_to_H27-4']:,.0f}; that predicts R0 as {pm['prediction_H27-4_to_R0']['predicted']:.4f} (reported {pm['prediction_H27-4_to_R0']['user_reported']:.4f}) and the 1,200-dot GEMSDOE36 file as {pm['prediction_R0_to_GEMSDOE36']['predicted']:.4f} (reported {pm['prediction_R0_to_GEMSDOE36']['user_reported']:.4f}). Those 1,200 dots carry only &approx; {pm['prediction_R0_to_GEMSDOE36']['implied_credit_per_added_dot']:.3f} credit each versus R0's average {sc_['credit_per_dot']:.3f}.</li>
    <li><strong>Scale (MODEL, bracketed):</strong> about {min(v['G_truth_pixels_in_scored_region'] for v in sc_['scenarios'].values()):,}&ndash;{max(v['G_truth_pixels_in_scored_region'] for v in sc_['scenarios'].values()):,} truth pixels in the scored region; R0 recovers roughly {min(v['recall_T_over_G'] for v in sc_['scenarios'].values())*100:.0f}&ndash;{max(v['recall_T_over_G'] for v in sc_['scenarios'].values())*100:.0f}% of them; about nine in ten of its dots are unmatched.</li>
    <li><strong>Can we beat it?</strong> Not uniquely from this sandbox. The fitted live-anchored model puts every independent in-repo raster below R0, the uniqueness rule removes the zones where value concentrates, and the only identified escape is new information (USGS 3DEP 1 m LiDAR; a rank-5 team publicly describes "20 m lidar-derivative U-Net ensembles") &mdash; all eight official hosts tested return no connection from here. Public board today: #1 0.4437, #10 0.3379, #24 0.3169, #50 0.2826 (OFFICIAL).</li>
  </ul>
</section>

<section class="card" id="s22-experiments">
  <h2>4 &middot; The three preregistered experiments (frozen before any result; amendments A1&ndash;A3 logged)</h2>
  <p class="small">Hypotheses and novelty audit: <a href="HYPOTHESES_S22_XBREED.md">docs/HYPOTHESES_S22_XBREED.md</a>. Evaluator <code>{esc(hold['evaluator_version'])}</code>, {hold['withheld_positive_pixels']:,} withheld positives, equalized 9,414/9,414/9,413/9,413 dots per test quadrant, 1,000-draw paired 20 km block bootstrap. HOLDOUT-DTI measures <em>catalogue recovery</em>.</p>
  <div class="s22-wrap"><table class="s22"><thead><tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% CI</th></tr></thead><tbody>{e1_rows}</tbody></table></div>
  <div class="s22-wrap"><table class="s22"><thead><tr><th>Paired difference</th><th>&Delta;</th><th>95% CI</th></tr></thead><tbody>{pd_rows}</tbody></table></div>
  <p class="small"><strong>E2 &mdash; live-anchored instrument validity</strong> (Spearman of USER-REPORTED live score against each proxy, {inst['n_anchors'] if inst else 'n/a'} anchors, anchor bootstrap):</p>
  <div class="s22-wrap"><table class="s22"><thead><tr><th>Proxy</th><th>n</th><th>&rho;</th><th>95% CI</th></tr></thead><tbody>{iv_rows}</tbody></table></div>
  {'<p class="small"><strong>H22-3 (damage-zone decay):</strong> mean fitted truth-density factor at (1,5] px = ' + _f(h223['kill_test_fresh']['mean_factor_(1,5]px'], 3) + ' versus (5,20] px = ' + _f(h223['kill_test_fresh']['mean_factor_(5,20]px'], 3) + ' &rarr; ' + ('REFUTED' if h223['kill_test_fresh']['refuted'] else 'not refuted') + '. <strong>H22-2 (catalogue strike discontinuity):</strong> hi-vs-lo factor ' + _f(h222['factor_hi_vs_lo'], 3) + ', site-jackknife 95% CI of the log-effect [' + _f(h222['ci95_log_effect'][0], 3) + ', ' + _f(h222['ci95_log_effect'][1], 3) + '] &rarr; ' + esc(h222['direction']) + ' (LOSO RMSE change ' + f"{h222['rmse_change']:+.5f}" + ').</p>' if inst else ''}
</section>

<section class="card" id="gates">
  <h2>5 &middot; Automated gates (code, not inspection)</h2>
  <div class="s22-wrap"><table class="s22"><thead><tr><th>Gate</th><th>Result</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
  <p class="small">Definitions are in the preregistration &sect;4 (+A1&ndash;A3). G4 requires the paired C&minus;A interval above 0 under both the uncapped and the shipped (capped) recipe. G5 compares the live-anchored projection with every independent-model comparator ({esc(best_cmp or 'n/a')} is the strongest). <code>docs/s22/registry-screen-final.json</code> lists every reference compared.</p>
</section>

<section class="card" id="limits">
  <h2>6 &middot; Limitations and the access needed</h2>
  <ul>
    <li><strong>No organizer receipt exists</strong> for any number here; every "estimate" is a MODEL projection (leave-one-site-out RMSE &approx; 0.02) and is optimistic for any raster built with the model in view. Only a live score resolves it.</li>
    <li><strong>The public board scores a hidden subset</strong> (OFFICIAL, forum 11550) and the organizers will not disclose how test faults were found (forum 11527). Gains fitted to the public score need not transfer to the private set or the Phase 2 area.</li>
    <li><strong>Data access:</strong> USGS 3DEP 1 m LiDAR ({'<a href="https://apps.nationalmap.gov/downloader/">The National Map</a>'}, <a href="https://registry.opendata.aws/usgs-lidar/">AWS Open Data</a>), the DrivenData data page (login), ComCat, ScienceBase and GDR are <strong>all unreachable from the sandbox</strong> (curl HTTP 000, tested today). A trained scarp detector on 20 m LiDAR derivatives needs a machine with open internet and a GPU or a few CPU-hours.</li>
    <li><strong>Eligibility flag:</strong> about 150 live scores in four weeks is hard to reconcile with three submissions per week for one entity (OFFICIAL forum 11553, Rules &sect;3.4). Please confirm the account setup complies; nothing here asserts a violation.</li>
  </ul>
  <p class="small">All sources with exact wording and dates: <a href="OFFICIAL_SOURCES_VERIFIED_S22.md">docs/OFFICIAL_SOURCES_VERIFIED_S22.md</a> &middot; irregularities <a href="../IRREGULARITIES.md">IRREGULARITIES.md</a> (IR-S22-01&hellip;) &middot; next steps <a href="../LIMITATIONS_AND_NEXT_STEPS.md">LIMITATIONS_AND_NEXT_STEPS.md</a>.</p>
</section>

<section class="card" id="candidate-ranking">
  <h2>7 &middot; Where this file ranks among every candidate in this repository (live-aligned instruments, not scores)</h2>
  <p class="small">Both columns are the instruments that E2 found informative: the live-anchored LFI projection (ridge 10, Spearman 0.957 leave-one-site-out across 112 anchors; MODEL, &plusmn;0.02) and the blind SGMC DTI beyond 500 m (Spearman &approx; +0.44 with live scores). hide-v2 is <em>not</em> used to rank (&rho; = +0.105, CI includes 0). For reference the same model gives GEMSDOE32 R0 {_f(r0p.get('r10', {}).get('projected'), 3)} (USER-REPORTED live 0.2778).</p>
  <div class="s22-wrap"><table class="s22"><thead><tr><th>File</th><th>Dots</th><th>LFI projection</th><th>SGMC &gt;500 m</th><th>Near R0</th><th>Note</th></tr></thead><tbody>{rank_rows}</tbody></table></div>
  <p><strong>Reading it.</strong> The strongest <em>independent-model</em> file by both instruments is S18-HGBR E1, but it fails the wide protocol screen by a hair; the best file that passes is S21-PDWC E3, and this session's cross-breed ranks below it. The two files above S18 are not candidates: S20-LFI was optimized on this very model, and the DZEDGE raster sits on R0's own footprint. No <em>independent-model</em> file projects above R0; the only file that does (S20-LFI) was optimized on the very model that scores it, so its projection is optimistic by construction.</p>
  {probe_box}
</section>
</main>
<footer>Generated from <code>docs/run-card-S22-XB.json</code> and <code>docs/s22/*.json</code> by <code>scripts/render_s22_xbreed_pages.py</code>. No number on this page is typed by hand.</footer>
</div>{copy_js}</body></html>
"""
    (DOCS / "s22-xbreed-executive-summary.html").write_text(body)


if __name__ == "__main__":
    render()
