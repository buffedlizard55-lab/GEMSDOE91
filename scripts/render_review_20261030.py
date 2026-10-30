#!/usr/bin/env python3
"""Render the 2026-10-30 blocked review from frozen evidence; never create a TIFF."""
from __future__ import annotations

from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REVIEW = DOCS / "review-20261030"
AUDIT = DOCS / "s27-osdr" / "nine-site-audit.json"
EXPECTED_SITES = {
    "GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
    "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36",
}

CSS = r"""
:root{color-scheme:light;--ink:#172c2a;--muted:#536661;--paper:#f4f7f3;--line:#d6e1d9;--teal:#135c4b;--alert:#8c2f23;--alert-bg:#fff0e9;--soft:#e9f2eb;--white:#fff;--gold:#805400}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}a{color:#0b5b49;text-underline-offset:3px}a:hover{color:#073c31}a:focus-visible{outline:3px solid #cf8b1a;outline-offset:3px}.skip{position:absolute;left:-9999px}.skip:focus{left:10px;top:10px;background:white;padding:8px;z-index:4}.wrap{width:min(1240px,calc(100% - 40px));margin:auto}.nav{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:22px 0;border-bottom:1px solid var(--line)}.brand{font-weight:850;color:var(--ink);text-decoration:none;letter-spacing:-.03em}.brand small{display:block;color:var(--muted);font-size:10px;letter-spacing:.16em}nav{display:flex;flex-wrap:wrap;gap:17px;font-size:13px;font-weight:700}.eyebrow{text-transform:uppercase;letter-spacing:.13em;font-size:11px;color:var(--teal);font-weight:800}.hero{padding:44px 0 18px;display:grid;grid-template-columns:1.2fr .8fr;gap:26px;align-items:start}h1{font-size:clamp(34px,5vw,58px);letter-spacing:-.045em;line-height:1.04;margin:12px 0 16px}h2{font-size:clamp(23px,3vw,32px);letter-spacing:-.03em;line-height:1.2;margin:0 0 13px}h3{font-size:18px;line-height:1.25;margin:0 0 9px}.lead{font-size:18px;color:var(--muted);max-width:760px}.verdict{background:var(--alert-bg);border:2px solid #d8a28d;border-left:8px solid var(--alert);border-radius:8px;padding:22px}.verdict strong{color:var(--alert)}.verdict p:last-child{margin-bottom:0}.card{background:var(--white);border:1px solid var(--line);border-radius:9px;padding:22px;min-width:0}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:18px 0}.stat{background:var(--soft);border-radius:7px;padding:14px}.stat b{display:block;font-size:24px;line-height:1.2}.stat small{display:block;color:var(--muted);font-size:12px}.section{padding:30px 0;border-bottom:1px solid var(--line)}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}.table-scroll{overflow:auto;background:white;border:1px solid var(--line);border-radius:8px}table{border-collapse:collapse;width:100%;min-width:1120px;font-size:13px}caption{text-align:left;padding:14px;color:var(--muted)}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #e4ebe5;padding:12px}thead th{background:#e8f0e9;text-transform:uppercase;font-size:10px;letter-spacing:.07em;position:sticky;top:0}th[scope=row]{white-space:nowrap}td.filename{max-width:310px;overflow-wrap:anywhere}td.filename code{font-size:11px}.tag{display:inline-block;border-radius:100px;padding:3px 8px;font-size:11px;font-weight:800;background:#f5ead3;color:#563c08}.tag.bad{background:#fae1d9;color:#762819}.tag.neutral{background:#e9edf1;color:#3d4a52}.note{border-left:4px solid #b17b19;background:#fff8e8;padding:15px 18px;border-radius:4px}.callout{padding:17px 18px;border-radius:8px;background:var(--soft);border:1px solid var(--line)}.subtle{font-size:13px;color:var(--muted)}code{font:12px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}.hypo-table{min-width:1020px}.no{font-weight:850;color:var(--alert)}.yes{font-weight:800;color:var(--teal)}ol,ul{padding-left:22px}li{margin:8px 0}details{margin:12px 0;border-top:1px solid var(--line);padding:14px 0}summary{cursor:pointer;font-weight:750}footer{padding:26px 0 38px;color:var(--muted);font-size:12px;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}.button{display:inline-block;background:var(--teal);color:white!important;border-radius:6px;padding:10px 14px;text-decoration:none;font-weight:750}.button:hover{background:#0c4639}
@media(max-width:800px){.wrap{width:calc(100% - 28px)}.nav{align-items:flex-start;flex-direction:column}.hero,.grid2{grid-template-columns:1fr}.hero{padding-top:30px}.stats{grid-template-columns:1fr}.section{padding:25px 0}}
"""

HYPOTHESES = [
    {
        "rank": "1",
        "name": "SGMC unit-conditioned potential-field residual break",
        "layers": "USGS GeMS/SGMC bedrock unit polygons + verified magnetic/RTP and isostatic-gravity bands.",
        "signature": "Within-unit robust background residuals; persistent cross-strike residual discontinuity/truncation not explained by the mapped unit boundary.",
        "difference": "SGMC exists as a blind control in repo work; no map-unit polygon predictor/residual-break operator found in scripts/ or src/.",
        "mimic": "Unfaulted intrusive/volcanic contact or state-map compilation seam.",
        "benefit_cost": "Medium potential; medium-high cost; high uncertainty.",
        "source": '<a href="https://doi.org/10.5066/P1A3DQZK">USGS SGMC DOI / GIS listing</a>; GIS bytes and exact AOI not checked.',
        "anchor": "#1-sgmc-unit-conditioned-potential-field-residual-break",
    },
    {
        "rank": "2",
        "name": "Event-level earthquake migration and focal-mechanism lineation",
        "layers": "USGS ComCat origin time, hypocenter, magnitude, depth, review status, and available focal mechanisms.",
        "signature": "Declustered, persistent narrow strike-coherent hypocenter clusters or swarm migration; require compatible focal mechanisms when available.",
        "difference": "Repo uses static dependent/independent earthquake-density bands; no event-level migration/focal-mechanism processing found.",
        "mimic": "Geothermal/volcanic swarm, aftershock sequence, quarry blasts, or catalog-completeness change.",
        "benefit_cost": "Low-medium potential; medium-high cost; high uncertainty.",
        "source": '<a href="https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&amp;starttime=2020-01-01&amp;endtime=2026-10-30&amp;minlatitude=35&amp;maxlatitude=42&amp;minlongitude=-121&amp;maxlongitude=-114&amp;minmagnitude=2.0&amp;limit=100&amp;orderby=time">USGS ComCat query returned regional events</a>; exact AOI coverage not verified.',
        "anchor": "#2-event-level-earthquake-migration-and-focal-mechanism-lineation",
    },
    {
        "rank": "3",
        "name": "Official 1 m 3DEP drainage-offset / paired-channel test",
        "layers": "USGS 3DEP bare-earth 1 m DEM tiles plus the competition DEM for context and registration.",
        "signature": "Persistent channel-direction change plus cross-channel profile break, corroborated across adjacent valleys/terraces.",
        "difference": "Coarse drainage/scarp and LiDAR feature work exists; exact official 1 m hydrologic-network operator was not found.",
        "mimic": "Fan avulsion/lobe boundary, paleoshoreline, road/culvert, differential erosion, or lithologic contact.",
        "benefit_cost": "Medium potential if covered; high cost; high uncertainty.",
        "source": '<a href="https://www.usgs.gov/3d-elevation-program/about-3dep-products-services">USGS 3DEP</a> is free; exact AOI tile coverage not checked.',
        "anchor": "#3-official-1-m-3dep-drainage-offset-paired-channel-test",
    },
    {
        "rank": "4",
        "name": "Repeat-season Landsat surface-temperature residuals",
        "layers": "USGS Landsat Collection 2 Level-2 surface temperature, QA masks, and elevation/aspect/land-cover/emissivity context.",
        "signature": "Repeatable narrow seasonal temperature residual or seasonal-amplitude break, independently aligned with structural evidence across scenes.",
        "difference": "No Landsat temperature-scene processing found; the idea was previously written in project hypotheses but not implemented.",
        "mimic": "Irrigation/crop cycles, playa moisture, vegetation, emissivity, solar aspect, urban surfaces, or data gaps.",
        "benefit_cost": "Low-medium potential; high cost; high uncertainty.",
        "source": '<a href="https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature">USGS Landsat ST product page</a>; exact scenes/cloud-free AOI not checked.',
        "anchor": "#4-repeat-season-landsat-surface-temperature-residuals",
    },
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_inputs() -> tuple[dict, dict, dict, dict, dict, dict]:
    card = load(REVIEW / "run-card.json")
    preflight = load(REVIEW / "experiment-preflight.json")
    availability = load(REVIEW / "data-availability.json")
    observations = load(REVIEW / "source-observations.json")
    audit = load(AUDIT)
    format_audit = load(REVIEW / "tif-format-audit.json")
    plan = load(ROOT / "registry/experiment_plan.json")
    expected_reasons = {
        "No assigned single-method paragraph and assignment source",
        "Capacity witness unavailable or invalid; no fallback to archived constants",
    }
    mirror_audit = availability.get("mirror_route_audit", {})
    mirror_observation = observations.get("competition_input_mirror_audit", {})
    data_provenance = card.get("data_provenance", {})
    format_summary = format_audit.get("summary", {})
    if (plan.get("lane") is not None or plan.get("experiments_used") != 0
            or card.get("branch") != "arena/828b6720-gemsdoe91"
            or data_provenance.get("manifest_contains_github_mirror_routes") is not True
            or data_provenance.get("default_restore_path_uses_mirror_routes") is not True
            or data_provenance.get("rights_authorization_status") != "UNVERIFIED"
            or data_provenance.get("mirror_fetch_attempted_this_review") is not False
            or format_summary.get("files") != 70
            or format_summary.get("with_nan_cells") != 7
            or format_summary.get("all_finite_in_0_1") != 63
            or card.get("candidate_generated") is not False
            or card.get("ok_to_submit") is not False
            or card.get("raster_sha256") is not None
            or card.get("holdout", {}).get("value") is not None
            or card.get("estimated_leaderboard_score") is not None
            or card.get("organizer_confirmed_score") is not None
            or card.get("registry_correlation_overlap", {}).get("preplacement_surface_abs_spearman_max") is not None
            or card.get("registry_correlation_overlap", {}).get("final_dot_overlap_within_3px_max") is not None
            or card.get("validator_output", {}).get("status") != "NOT_RUN_NO_CANDIDATE"
            or preflight.get("status") != "BLOCKED"
            or preflight.get("ok_to_submit") is not False
            or preflight.get("candidate_generated") is not False
            or set(preflight.get("reasons", [])) != expected_reasons
            or availability.get("required_pinned_input_count") != 15
            or len(availability.get("missing_input_ids", [])) != 15
            or availability.get("mismatched_input_ids") != []
            or availability.get("exit_status") != 1
            or audit.get("organizer_complete_registry") is not False
            or audit.get("schema") != "s27-nine-site-plus-gems92-audit-v1"
            or observations.get("public_leaderboard", {}).get("evidence_class", "").startswith("ORGANIZER-CONFIRMED")
            or not mirror_audit.get("manifest_contains_github_mirror_routes")
            or not mirror_audit.get("default_restore_path_uses_mirror_routes")
            or mirror_audit.get("rights_authorization_status") != "UNVERIFIED"
            or mirror_audit.get("mirror_fetch_attempted_this_review") is not False
            or not mirror_observation.get("default_restore_path_fetches_from_mirrors")
            or mirror_observation.get("mirror_fetch_attempted_this_review") is not False
            or observations.get("drivendata_data_page", {}).get("status") != "LOGIN_REQUIRED"):
        raise ValueError("Current review evidence is inconsistent; refusing to render")
    rows = audit.get("nine_focus_sites", [])
    if ({r.get("site") for r in rows} != EXPECTED_SITES or len(rows) != 9
            or any(r.get("organizer_confirmed_score") is not None
                   or "USER-REPORTED" not in r.get("score_evidence_class", "")
                   or r.get("unique_within_nine_at_70pct") is not False
                   or r.get("max_3px_overlap_among_nine", 0) <= 0.70
                   for r in rows)):
        raise ValueError("Nine-site evidence is incomplete or no longer negative")
    page_checks = observations.get("focus_site_page_checks", [])
    if ({row.get("site") for row in page_checks} != EXPECTED_SITES or len(page_checks) != 9
            or any("no" not in row.get("status_observed", "").lower()
                   for row in page_checks)):
        raise ValueError("Current owner-page status snapshot is incomplete")
    claim32 = next(r for r in rows if r["site"] == "GEMSDOE32")
    if (card.get("historical_focus_site_claim", {}).get("claimed_value")
            != claim32.get("user_reported_public_dti")):
        raise ValueError("Run card historical claim differs from the pinned nine-site audit")
    claim28 = next(r for r in rows if r["site"] == "GEMSDOE28")
    claim31 = next(r for r in rows if r["site"] == "GEMSDOE31")
    if (claim28.get("best_claimed_file", "").find("h36-1") < 0
            or abs(float(claim28.get("user_reported_public_dti", 0)) - 0.2710) > 1e-9
            or claim31.get("best_claimed_file", "").find("h27-4") < 0
            or abs(float(claim31.get("user_reported_public_dti", 0)) - 0.2708) > 1e-9):
        raise ValueError("GEMSDOE28/31 separate H36-1 and H27-4 claims changed; reconcile before rendering")
    return card, preflight, availability, observations, audit, format_audit


def render_site_rows(audit: dict) -> str:
    result = []
    for row in sorted(audit["nine_focus_sites"], key=lambda x: -x["user_reported_public_dti"]):
        site = row["site"]
        page_url = row["site_url"]
        file_path = row["original_path"]
        head = row["current_main_head"]
        if not file_path or not head:
            raise ValueError(f"Missing immutable historical file identity for {site}")
        blob_url = f"https://github.com/buffedlizard55-lab/{site}/blob/{head}/{file_path}"
        file_html = (
            f'<a href="{escape(blob_url, quote=True)}">{escape(row["best_claimed_file"])}</a>'
            f'<small class="subtle"><br>Historical source commit <code>{escape(head[:12])}</code>'
            f' · SHA-256 <code>{escape(row["sha256"][:16])}…</code></small>'
        )
        overlap = 100.0 * float(row["max_3px_overlap_among_nine"])
        score = float(row["user_reported_public_dti"])
        result.append(
            "<tr>"
            f'<th scope="row"><a href="{escape(page_url, quote=True)}">{escape(site)}</a></th>'
            f'<td class="filename">{file_html}</td>'
            f'<td><strong>{score:.4f}</strong><br><span class="tag">USER-REPORTED</span>'
            '<small class="subtle"><br>no organizer receipt</small></td>'
            f'<td>{escape(row["closest_peer_among_nine"])}<br><strong>{overlap:.2f}%</strong>'
            '<small class="subtle"><br>within 3 px; peer-only audit</small></td>'
            '<td class="no">NO<br><small>exceeds 70% peer threshold</small></td>'
            '<td>Not estimable<br><small>no new candidate or holdout</small></td>'
            '<td class="no">NONE<br><small>historical source only; do not submit</small></td>'
            "</tr>"
        )
    return "\n".join(result)


def render_hypotheses() -> str:
    rows = []
    for h in HYPOTHESES:
        rows.append(
            "<tr>"
            f'<th scope="row">{h["rank"]}</th>'
            f'<td><a href="HYPOTHESES.md{h["anchor"]}"><strong>{escape(h["name"])}</strong></a>'
            f'<small class="subtle"><br>{escape(h["layers"])}</small></td>'
            f'<td>{escape(h["signature"])}</td>'
            f'<td>{escape(h["difference"])}</td>'
            f'<td>{escape(h["mimic"])}</td>'
            f'<td>{escape(h["benefit_cost"])}</td>'
            f'<td>{h["source"]}</td>'
            "</tr>"
        )
    return "\n".join(rows)


def render_page(card: dict, preflight: dict, availability: dict, observations: dict, audit: dict, format_audit: dict) -> str:
    rows = render_site_rows(audit)
    hypothesis_rows = render_hypotheses()
    claim_32 = next(r for r in audit["nine_focus_sites"] if r["site"] == "GEMSDOE32")
    public = observations["public_leaderboard"]
    format_summary = format_audit["summary"]
    missing_count = len(availability["missing_input_ids"])
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="2026-10-30 fail-closed GEMSDOE91 review: nine-site evidence, ranked hypotheses, and no new submission.">
<title>2026-10-30 Review · GEMSDOE91</title>
<style>{CSS}</style>
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
<header class="nav"><a class="brand" href="../index.html">GEMSDOE91<small>FAULT MAPPING / RESEARCH OPERATIONS</small></a>
<nav aria-label="Review navigation"><a href="#decision">Decision</a><a href="#nine-sites">Nine sites</a><a href="#r0">0.2778 analysis</a><a href="#hypotheses">Hypotheses</a><a href="#how-to-submit">Submission steps</a></nav></header>
<main id="main">
<section class="hero" id="decision"><div><span class="eyebrow">Current review · 2026-10-30 · branch arena/828b6720-gemsdoe91</span>
<h1>No new TIFF.<br>No submission approved.</h1>
<p class="lead">This review did not generate a raster, run a geological experiment, or estimate a leaderboard score. The current method lane is unassigned and the official inputs needed to validate a candidate are missing. No historic file is promoted as a current download.</p>
<div class="stats"><div class="stat"><b>0 / 3</b><small>experiments used in this review</small></div><div class="stat"><b>{missing_count} / 15</b><small>pinned inputs missing; verification-only check</small></div><div class="stat"><b>0</b><small>weekly competition slots used</small></div></div>
<p><a class="button" href="CURRENT_REVIEW.md">Read the full three-pass review</a> <a class="button" href="run-card.json">Open the negative run card</a></p>
</div><aside class="verdict" aria-label="Download and submission verdict"><span class="eyebrow">Automated current verdict</span><h2><strong>OK TO DOWNLOAD: NO new candidate</strong></h2><h2><strong>OK TO SUBMIT: NO</strong></h2><p><strong>HOLDOUT-DTI: NOT RUN</strong>; no evaluator result, withheld-positive count, or 95% CI exists. No candidate raster exists, so surface correlation, final-dot overlap, file hash, and format-validation results are also unmeasured. Existing historical artifacts, where linked elsewhere on the site, remain research-only.</p><p class="subtle">Preflight: <strong>{escape(preflight["status"])}</strong>. No slot selection was made.</p><p class="subtle"><strong>Data rights:</strong> mirror routes in the manifest are unverified; this review did not fetch them.</p></aside></section>
<section class="section"><div class="grid2"><article class="card"><span class="eyebrow">Highest supplied claim within the nine requested sites</span><h2>GEMSDOE32 — 0.2778</h2><p><strong>USER-REPORTED; not organizer-confirmed.</strong> The local audit has no DrivenData receipt binding the claim to the historical raster's SHA-256. The 0.2778 value is not a holdout result, a projection by this review, or proof of vent discovery.</p><p>Within the historical peer audit, this file has {100*claim_32["max_3px_overlap_among_nine"]:.2f}% directed 3-px overlap with its closest peer ({escape(claim_32["closest_peer_among_nine"])}). It is not unique versus the other eight under the stated 70% rule.</p></article>
<article class="card"><span class="eyebrow">Official public board observation</span><h2>{float(public["rank_one_public_score"]):.4f} — rank one</h2><p><span class="tag neutral">PUBLIC-LEADERBOARD SNAPSHOT · 2026-10-30</span></p><p>This was the public rank-one observation when the official page was fetched. It is not a submission-page receipt for any file in the table and may differ from private-phase and expert-revised Phase 2 results. No score is forecast for a new candidate.</p><a href="{escape(public["url"], quote=True)}">Open the official leaderboard</a></article></div></section>
<section class="section" id="nine-sites"><span class="eyebrow">Historical file and score evidence</span><h2>Nine-site executive table</h2>
<p>The “best file” entries below are the last pinned owner/source claims in the 2026-10-29 byte audit. Owner-maintained pages were checked again on 2026-10-30; none authorizes a new submission. File links go to immutable source commits for inspection only; they are <strong>not a recommended download</strong>. Each score is labeled USER-REPORTED, not organizer-confirmed. New-file estimates are unavailable.</p>
<div class="table-scroll"><table><caption>Peer-only directed overlap: share of the site's dots within 3 pixels of the closest other one of the nine. This is not a full-registry measurement or a score.</caption><thead><tr><th>Site / page</th><th>Best historical claimed file (source only)</th><th>Claimed score / evidence</th><th>Closest peer / overlap</th><th>Unique vs other eight?</th><th>New-file score estimate</th><th>Current download / submit</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="note"><strong>Coverage limitation:</strong> the pinned audit says the organizer-complete registry was unavailable. It records every historical leader above the 70% peer threshold, but this cannot establish overlap against every registry raster. No candidate was available for the required pre-placement |ρ| check or final-dot check.</p>
<p class="subtle"><strong>Local format-only audit (not submission approval):</strong> {format_summary["files"]} historical research TIFFs in <code>docs/downloads/</code> were inspected; {format_summary["with_nan_cells"]} contain NaN cells and {format_summary["all_finite_in_0_1"]} are all-finite within <code>[0,1]</code>. The suspected range-error cause is inference, not reproduced; none of these files is approved as a submission. <a href="tif-format-audit.json">Open the format audit</a>.</p>
<p class="note"><strong>GEMSDOE28 claim distinction:</strong> the table's <code>0.2710</code> claim belongs to the H36-1 file linked in that row. The earlier R0 lineage report's <code>0.2708</code> claim belongs to a different H27-4 file, recorded as pixel-identical across GEMSDOE28 and GEMSDOE31. Both are USER-REPORTED and neither has an organizer receipt; this review preserves both and does not treat one as a correction to the other.</p>
<p class="subtle">Audit file: <a href="../s27-osdr/nine-site-audit.json">nine-site-audit.json</a> · Source pages and immutable file commits are linked per row · <a href="../index.html#feed">owner-page / GitHub-head feed</a>. `GEMSDOE92`'s 0.2784 is outside the requested nine and remains USER-REPORTED.</p>
</section>
<section class="section" id="r0"><span class="eyebrow">Evidence-based explanation; no score reproduction</span><h2>Why is the claimed 0.2778 highest among these sites?</h2>
<p>The best-supported explanation in the repository's earlier SHA-pinned byte-lineage report is <strong>pruning within one shared raster family</strong>, not a demonstrated new fault detector. That older audit has not been re-run here because its original source TIFFs are missing locally.</p>
<div class="grid2"><article class="card"><h3>What the prior lineage record says</h3><ul>
<li>D2.8 (`GEMSDOE25`) has 44,090 dots and a `0.2600` USER-REPORTED claim.</li>
<li>H27-4 (`GEMSDOE28/31`) is recorded as 40,199 dots after removing 3,891 dots within 1 pixel of the known catalogue; the shared-file `0.2708` value is USER-REPORTED.</li>
<li>R0 (`GEMSDOE32`) is recorded as 37,654 dots after removing a further 2,545 dots 1–2 pixels from the catalogue; `0.2778` is USER-REPORTED.</li>
<li>GEMSDOE36 is recorded as R0 plus 1,200 dots with a `0.2750` USER-REPORTED claim.</li>
</ul><p>The arithmetic is consistent with selective deletion of 6,436 near-catalogue dots raising the reported value while most of the support remains. It does not prove those pixels were false positives.</p></article>
<article class="card"><h3>Why pruning can raise a fault score</h3><p>The official metric uses a distance-weighted Tversky index with α=0.2, β=0.8, and 300 m triangular distance support. False positives contribute to the denominator. If a removed dot carries little credit against a hidden new fault, removing it can reduce false-positive mass while preserving much of the matched credit.</p><p>That mechanism is conditional: a new fault may lie near a known trace, and the 300 m kernel means proximity alone is not enough to classify a dot as wrong. The score claim is unauthenticated; this review cannot infer the hidden truth or reproduce the public score.</p></article></div>
<p class="note"><strong>Could it be beaten?</strong> Possibly, but no defensible numeric forecast exists here. A fresh, unique candidate has not been generated, the assigned lane and data are unavailable, and the reported public score does not validate transfer to private or expert-revised evaluation. The answer is <em>not estimable</em>, not a projection.</p>
<p>Repository record: <a href="../R0_ANALYSIS_S22.md">R0 lineage discussion</a> · <a href="../s22-xb/r0-decomposition.json">prior byte/model decomposition</a>. These are historical analyses; their reported score inputs are USER-REPORTED and model-derived quantities are not scores.</p>
</section>
<section class="section" id="hypotheses"><span class="eyebrow">Ranked proposals · none run</span><h2>Four geological hypotheses to consider after blockers are resolved</h2>
<p>Ranks are qualitative expected information relative to cost; no DTI gain is forecast. The first proposal is top-ranked, but its required validation was blocked and must not be treated as passed.</p>
<div class="table-scroll"><table class="hypo-table"><thead><tr><th>Rank</th><th>Layers / candidate</th><th>Physical signature / missed-fault rationale</th><th>Difference from this repository</th><th>Named non-fault mimic</th><th>Qualitative benefit / cost</th><th>Official source availability check</th></tr></thead><tbody>{hypothesis_rows}</tbody></table></div>
<p><a href="HYPOTHESES.md">Full hypotheses, operator details, access limits, and novelty audit</a></p>
<div class="callout"><h3>Top idea holdout status: NOT RUN</h3><p>The top candidate is SGMC unit-conditioned potential-field residual breaks. Its source page and GIS download listing are public, but the data bytes and coverage were not obtained. More importantly, `lane: null` and 15 missing pinned inputs block any experiment. No leakage canary, buffered whole-segment holdout, pooled DTI, confidence interval, or candidate has been produced.</p></div>
</section>
<section class="section" id="how-to-submit"><span class="eyebrow">Future-only submission procedure</span><h2>What must happen before an upload?</h2>
<p class="verdict"><strong>For this review: stop here. There is no file to upload or download, no live decision, and no slot selected.</strong></p>
<ol>
<li><strong>Confirm the registered competitor and eligibility.</strong> Official Rules §1.3 names eligible individuals, teams, and U.S.-based entities with specific citizenship/work-authorization and other conditions. The authorized entrant representative—not an AI agent—must register and certify. Confirm the actual competitor's eligibility with the prize administrator; this repository cannot do that.</li>
<li><strong>Resolve the method and restore authorized data.</strong> Obtain the assigned single-method paragraph/source, authenticate the official sample and every required input, check rights/provenance, and verify the complete frozen registry. Do not substitute an unassigned proposal.</li>
<li><strong>Use the shared experiment path only.</strong> Reuse the shared feature stack, `evaluate_holdout.py`, and `submission_writer.py`. Hide/recover whole fault segments with a buffer, derive features only from visible faults, preserve the pixel-exact mask, run each-feature leakage canaries (AUC &gt; 0.90 is a leakage warning), and report pooled DTI with evaluator version, withheld-positive count, and 95% CI.</li>
<li><strong>Apply both novelty checks.</strong> Stop if pre-placement surface |ρ| exceeds 0.90 against any registry raster, or if more than 70% of final dots fall within 3 px of any registry raster. Check both phases against the complete registry; log duplicates/negative outcomes rather than shipping them.</li>
<li><strong>Validate the final artifact automatically.</strong> Confirm no NaN inside the footprint, values in [0,1], single-band float32, expected CRS/shape/transform, file and ZIP hashes, and the official single-band GeoTIFF format. A local validator pass does not prove website acceptance or authorize a submission.</li>
<li><strong>Only after independent selector approval, use the authenticated portal.</strong> The official rules/platform permit up to three submissions per week, but a separate selector chooses the single final submission for the prize phases. Record a receipt that binds the exact raster hash to any organizer score. Disclose the extent and use of generative AI in the required narrative.</li>
</ol>
<p>Official pages: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">problem, metric, and format</a> · <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">September 2026 Official Rules</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">submission portal (no upload authorized by this review)</a>.</p>
</section>
<section class="section"><span class="eyebrow">Evidence and provenance</span><h2>What was checked—and what was not</h2>
<div class="grid2"><article class="card"><h3>Verified this review</h3><ul><li>Current method assignment field is null.</li><li>Preflight status is BLOCKED; no sample witness, no candidate, zero experiments.</li><li>Verification-only restore check reports 15 missing pinned inputs and no restore.</li><li>Historical nine-site audit labels scores USER-REPORTED and records no organizer-complete registry.</li><li>Official rule/metric pages and named USGS source pages were fetched; regional ComCat query returned records.</li><li>Local format-only audit inspected 70 historical TIFFs; 7 had NaNs and 63 were finite in [0,1].</li><li>Official DrivenData data page redirects anonymous users to login.</li></ul></article><article class="card"><h3>Not verified / not claimed</h3><ul><li>No score receipt tied to any historical file hash.</li><li>No new holdout, CI, leakage test, or live score estimate.</li><li>No current full-registry surface or final-dot comparison.</li><li>No external SGMC, ComCat, 3DEP, or Landsat data bytes/footprint coverage.</li><li>No authorization/provenance for GitHub mirror routes; none were fetched.</li><li>No user's or entity's eligibility; no upload or selector decision.</li></ul></article></div>
<p class="subtle">Supporting records: <a href="run-card.json">run card</a> · <a href="experiment-preflight.json">preflight</a> · <a href="data-availability.json">input availability</a> · <a href="source-observations.json">dated source observations</a> · <a href="CURRENT_REVIEW.md">full review</a> · <a href="../../IRREGULARITIES.md">repository irregularities</a> · <a href="../../LIMITATIONS_AND_NEXT_STEPS.md">limitations and next steps</a>.</p>
</section>
</main>
<footer><span>Maximize P(Win) · Own the Outcome<br>Research review; not a leaderboard prediction.</span><span><a href="../index.html">Current portal and source feed</a><br>No automatic competition uploads or stored credentials.</span></footer>
</div>
</body>
</html>
'''


def render() -> Path:
    card, preflight, availability, observations, audit, format_audit = verify_inputs()
    REVIEW.mkdir(parents=True, exist_ok=True)
    output = REVIEW / "executive-summary.html"
    output.write_text(render_page(card, preflight, availability, observations, audit, format_audit), encoding="utf-8")
    return output


if __name__ == "__main__":
    print(render().relative_to(ROOT))
