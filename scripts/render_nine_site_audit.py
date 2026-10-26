#!/usr/bin/env python3
"""Render the pinned nine-site audit as a self-contained, fail-closed Pages report."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/research/nine-site-audit-20261026.json"
OUTPUT = ROOT / "docs/nine-site-audit-20261026.html"

CSS = """
:root{--ink:#17312e;--muted:#596c68;--paper:#f5f5ee;--card:#fff;--line:#d7dfd8;--accent:#17644e;--soft:#e7f0e8;--warn:#8d351f;--warnbg:#fff0e9;--blue:#245c81}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--accent);text-underline-offset:3px}a:hover{color:var(--blue)}.wrap{width:min(1180px,calc(100% - 40px));margin:auto}.top{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:22px 0;border-bottom:1px solid var(--line)}.brand{font-weight:800;text-decoration:none;color:var(--ink)}nav{display:flex;flex-wrap:wrap;gap:18px}nav a{font-size:13px;text-decoration:none;color:var(--muted)}main{padding:24px 0 44px}h1{font-size:clamp(30px,4vw,48px);line-height:1.12;letter-spacing:-1px;margin:.2em 0 .4em}h2{font-size:24px;line-height:1.25;margin:0 0 12px}h3{font-size:18px;margin:0 0 9px}.eyebrow{font-size:11px;font-weight:800;letter-spacing:1.6px;text-transform:uppercase;color:var(--accent)}.lead{font-size:18px;color:var(--muted);max-width:900px}.warn{border:2px solid #d99b7d;border-left:7px solid var(--warn);background:var(--warnbg);padding:20px 24px;border-radius:9px;margin:18px 0}.warn strong{color:var(--warn)}.badges{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.badge{display:inline-block;padding:5px 10px;border-radius:5px;background:var(--soft);font-size:12px;font-weight:800}.badge.bad{background:var(--warnbg);color:var(--warn)}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:24px;margin:20px 0}.small{font-size:13px;color:var(--muted)}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#edf1ea;font-size:11px;text-transform:uppercase;letter-spacing:.6px}td.score{white-space:nowrap;font-weight:800}.mono,code{font:12px ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.callout{background:#eef5ef;border-left:4px solid var(--accent);padding:14px 18px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.source-list li{margin:7px 0}footer{border-top:1px solid var(--line);padding:22px 0 38px;color:var(--muted);font-size:12px}@media(max-width:820px){.grid{grid-template-columns:1fr}.top{align-items:flex-start;flex-direction:column}.wrap{width:calc(100% - 28px)}th,td{padding:9px;font-size:13px}}
"""


def render() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    rows = []
    for repo in data["repositories"]:
        best = repo["strongest_supplied"]
        first_source = repo["snapshot_sources"][0]
        rows.append(
            "<tr>"
            f"<td><strong>{escape(repo['site'])}</strong><br><a href=\"{escape(first_source['url'], quote=True)}\">Pinned source</a>"
            f"<br><span class=\"mono\">{escape(repo['commit'][:12])}</span></td>"
            f"<td><code>{escape(best['name'])}</code></td>"
            f"<td class=\"score\">{best['score']:.4f}</td>"
            f"<td>{escape(best['method'])}</td>"
            f"<td>{escape(best['evidence_status'])}<br><br><span class=\"small\">{escape(best['current_site_status'])}</span></td>"
            "</tr>"
        )

    current = data["current_checkout"]
    local_candidate_rows = []
    for candidate in current["existing_research_files"]:
        holdout = candidate["holdout_dti"]
        if holdout is None:
            score_label = "NOT RUN"
        else:
            score_label = (
                f"{holdout['value']:.6f} HOLDOUT-DTI<br>"
                f'<span class="small">{escape(holdout["evaluator_version"])}; '
                f"{holdout['withheld_positives']:,} withheld; 95% CI "
                f"[{holdout['ci95'][0]:.6f}, {holdout['ci95'][1]:.6f}]</span>"
            )
        file_href = candidate["file"].removeprefix("docs/")
        card_href = candidate["run_card"].removeprefix("docs/")
        local_candidate_rows.append(
            "<tr>"
            f"<td><strong>{escape(candidate['label'])}</strong><br>"
            f'<a href="{escape(file_href, quote=True)}">Research file</a> · '
            f'<a href="{escape(card_href, quote=True)}">run card</a></td>'
            f"<td>{score_label}</td><td>{escape(candidate['status'])}</td></tr>"
        )
    current_status = (
        "<section class=\"warn\" role=\"status\" aria-label=\"Current review decision\">"
        "<div class=\"eyebrow\">GEMSDOE91 · CURRENT REVIEW · 2026-10-26</div>"
        "<h2>NO NEW TIFF FROM THIS REVIEW</h2>"
        "<div class=\"badges\"><span class=\"badge bad\">OK TO DOWNLOAD: NO NEW TIFF</span>"
        "<span class=\"badge bad\">OK TO SUBMIT: NO</span></div>"
        "<p>No candidate was generated, no score was measured, and no slot was selected. The older ISO91 download elsewhere on the site is a prior research artifact, not this review's output or an approved submission.</p>"
        "<p><a href=\"REVIEW-SITE-AUDIT-20261026.md\">Three-pass review</a> · "
        "<a href=\"run-card-SITE-AUDIT-20261026.json\">No-run JSON card</a> · "
        "<a href=\"research/nine-site-audit-20261026.json\">Pinned evidence register</a></p>"
        "</section>"
    )

    leader = data["leaderboard_claims"]
    source_links = []
    for repo in data["repositories"]:
        for source in repo["snapshot_sources"]:
            source_links.append(
                f"<li><a href=\"{escape(source['url'], quote=True)}\">{escape(repo['site'])}: {escape(source['path'])}</a>"
                f" <span class=\"small\">(commit {escape(repo['commit'][:12])})</span></li>"
            )

    official = [
        ("DrivenData problem description", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"),
        ("DrivenData rules", "https://www.drivendata.org/competitions/306/competition-doe-gems/"),
        ("DrivenData data portal (login required)", "https://www.drivendata.org/competitions/306/competition-doe-gems/data/"),
        ("DrivenData public leaderboard (not refreshed in this audit)", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"),
        ("USGS 3DEP", "https://www.usgs.gov/3d-elevation-program"),
        ("USGS GeMS/SGMC 2026", "https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous"),
        ("USGS ComCat", "https://earthquake.usgs.gov/data/comcat/"),
        ("USGS Landsat Collection 2 surface temperature", "https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature"),
        ("DOE/NLR competition report", "https://docs.nlr.gov/docs/fy26osti/96647.pdf"),
    ]
    official_html = "\n".join(
        f"<li><a href=\"{escape(url, quote=True)}\">{escape(title)}</a></li>" for title, url in official
    )

    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nine-site score audit · GEMSDOE91</title><meta name="description" content="Commit-pinned review of nine GEMSDOE owner-reported submissions, score provenance, current research statuses and a no-run decision.">
<style>{CSS}</style></head><body><div class="wrap">
<header class="top"><a class="brand" href="nine-site-audit-20261026.html">GEMSDOE91 · DOE GEMS research</a><nav aria-label="Main"><a href="nine-site-audit-20261026.html">Current status</a><a href="index.html">Prior research portal</a><a href="executive-summary.html">Submission guide</a><a href="REVIEW-SITE-AUDIT-20261026.md">Three-pass review</a><a href="run-card-SITE-AUDIT-20261026.json">Run card</a></nav></header>
<main id="main" data-submission-ready="false">
{current_status}
<div class="eyebrow">Pinned owner-repository snapshot · {escape(data['review_date_utc'])} · all sites</div>
<h1>What the nine reported scores do—and do not—show</h1>
<p class="lead">The strongest value in the supplied list is GEMSDOE32 <code>h33-h33-2-b2</code> at <strong>0.2778</strong>. The available records do not verify an organizer receipt tying that value to the exact TIFF. The table below summarizes the reported method, evidence status and current site notice for each supplied highest entry.</p>
<div class="callout"><strong>Evidence rule:</strong> “owner-reported,” “USER-REPORTED,” “task statement only,” and “HOLDOUT-DTI” are not interchangeable with <code>ORGANIZER-CONFIRMED</code>. No receipt was verified here. A format-valid or unique research raster is not automatically approved to upload.</div>
<section class="card"><h2>Highest supplied entry per site</h2><div class="scroll"><table><thead><tr><th>Site / pinned evidence</th><th>Reported entry</th><th>Claim</th><th>Method as described by owner records</th><th>Evidence and current-site status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="small">“Highest supplied” means highest among the nine entries provided in the task, not necessarily a complete history of each site. Pinned source commits are linked in the first column and fully enumerated below.</p></section>
<section class="card"><h2>Why GEMSDOE32's 0.2778 may be high</h2>
<p>The plausible explanation is metric-aware thinning, not proof of a new geological detector: the owner-maintained lineage describes H19-5 ridge pixels thinned to roughly 2.8-pixel spacing, followed by catalogue-flank deletions. If close-by predictions have overlapping 300 m kernel credit, while each prediction still adds false-positive mass, pruning low-yield pixels can improve a distance-weighted Tversky-style score. A public/private evaluation that masks already-mapped catalogue pixels could make the near-catalogue ring especially inefficient.</p>
<p><strong>What is not proved:</strong> the reported score has no verified receipt-to-byte association in the audited records; the rasters were not re-evaluated under a shared controlled experiment here; and “zero-credit” is not established for hidden truth. The mechanism is plausible, not causal attribution. The score is not evidence of geothermal-vent discovery.</p>
<p><strong>Can it be beaten?</strong> Possible in principle; no evidence from this checkout that it can. No new candidate was authorized or tested. The best file to submit from this review is <strong>none</strong>.</p></section>
<section class="card"><h2>Conflicting public-leader claims</h2>
<p>The task supplies both <code>{leader['user_supplied_values_conflict'][0]:.4f}</code> and <code>{leader['user_supplied_values_conflict'][1]:.4f}</code> as “current” highs. They are not merged. The last in-repository official-board observation is recorded as <strong>{leader['last_recorded_official_public_snapshot_in_this_checkout']['score']:.4f}</strong> on <strong>{escape(leader['last_recorded_official_public_snapshot_in_this_checkout']['as_of_utc'])}</strong> by a prior GEMSDOE91 review; it was not refreshed on 2026-10-26. The owner snapshot places 0.3195 on 2026-10-03. Neither is a receipt for a file in this audit.</p>
<p><a href="REVIEW-ACTIVE-E649E460-20261025.md">Prior dated leaderboard/source review</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Official public leaderboard (manual check)</a></p></section>
<section class="card"><h2>Existing GEMSDOE91 research files — not produced by this review</h2>
<p>The front-door current-run pointer still identifies ISO91, while the site also links prior parallel research artifacts. These files are not current submissions, and a run card's internal status does not grant a selector decision. The HOLDOUT-DTI results below use research holdouts, not organizer receipts, and are not directly comparable to the user/owner-reported 0.2778 claim.</p>
<div class="scroll"><table><thead><tr><th>Existing artifact</th><th>Measured holdout</th><th>Evidence and status</th></tr></thead><tbody>{''.join(local_candidate_rows)}</tbody></table></div>
<p>ISO91, S19-SVHF, S18-HGBR and S18-UNIQUE were generated by earlier sessions or separate branches; none was generated or newly validated by this audit. The separate S18-HGBR card's internal “promote” verdict is not a live slot selection: its recorded literal overlap with the synthetic lattice is 99.843% and its own <code>live_slot_decision</code> says <code>DO_NOT_SPEND_WEEKLY_SLOT_AUTOMATICALLY</code>. No file is recommended to submit.</p>
<p><a href="REVIEW-SITE-AUDIT-20261026.md#current-owner-site-research-files-are-not-a-submission-recommendation">Open the nine-site current-status table</a>. The GEMSDOE32 page has an older submit-yes callout that conflicts with its newer strict DO-NOT-SUBMIT banner; the strict notice is the safe interpretation. No selector approval is inferred from any owner page.</p></section>
<section class="card"><h2>Ranked hypotheses (proposals only)</h2>
<ol><li><strong>Dipping-contact waveform matched-filter bank</strong> — B02/B13/B14, with B15 for depth context. Buried faulted contacts may preserve asymmetric multi-field step waveforms; mimic: unfaulted dipping contacts, dykes or plutons. Qualitative expected DTI upside: medium, unquantified; high compute cost. Stack missing and no lane assigned. Previously proposed in H17-2, not run.</li>
<li><strong>Repeatable same-age alluvial-fan displacement</strong> — B12/B19 plus official USGS 3DEP 1 m DEM, optionally unit-age context. Repeated same-sign deformation across adjacent fans may identify concealed faults; mimics include depositional lobes, debris-flow levees and roads. Qualitative expected DTI upside: potentially high if complementary coverage exists, unquantified; high external-data/coverage cost. Not viable until exact data coverage is verified.</li>
<li><strong>Focal-mechanism orientation coherence with geodetic strain</strong> — B07/B08/B10/B16/B02/B13 plus USGS ComCat focal-mechanism products where available. Coherent fault-plane/strain alignment may identify active concealed structures; mimics include volcanic/aftershock swarms and sparse network geometry. Qualitative expected DTI upside: low-to-medium and uncertain, unquantified; high data/QC cost. No local catalog and coverage unverified.</li></ol>
<p class="small">No numerical DTI improvement is projected. None is the assigned method for this branch. The top candidate was not tested because the lane, data and shared prerequisites are missing. Full mechanisms, code differences, sources and risk notes are in the <a href="REVIEW-SITE-AUDIT-20261026.md#ranked-hypotheses-proposals-not-results">review</a>.</p></section>
<section class="card"><h2>Manual-review source snapshot</h2><p class="small">Each owner-repository link below is commit-pinned. Pages may move later; the JSON register preserves this audit's commit identifiers. Official links are provided for manual review and were not fetched in this 2026-10-26 pass.</p><ul class="source-list">{''.join(source_links)}</ul>
<h3>Official source pages</h3><ul class="source-list">{official_html}</ul></section>
<section class="card"><h2>Three-pass review and machine-readable status</h2><p>Pass 1 inspected the branch, lane, data and source snapshots. Pass 2 checked score provenance, duplicates, conflicting badges and unsupported causal language. Pass 3 added the user-facing report, exact commit register, and automated regression checks. No experiment or TIFF was produced.</p>
<p><a href="REVIEW-SITE-AUDIT-20261026.md">Three-pass review</a> · <a href="run-card-SITE-AUDIT-20261026.json">No-run JSON card</a> · <a href="research/nine-site-audit-20261026.json">Source-of-truth JSON register</a></p>
<p class="small">Current status: lane assigned = {str(current['lane_assigned']).lower()}, data directory present = {str(current['data_directory_present']).lower()}, experiments run = 0, new TIFF generated = {str(current['new_tiff_generated']).lower()}, organizer-confirmed score = null, OK TO SUBMIT = NO.</p></section>
</main><footer>GEMSDOE91 · No automatic competition uploads. No credentials stored. A public-source link is not a claim that its contents were fetched in this audit.</footer>
</div></body></html>'''
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Rendered {OUTPUT.relative_to(ROOT)} from {DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    render()
