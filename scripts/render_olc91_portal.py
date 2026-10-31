#!/usr/bin/env python3
"""Render the fail-closed current review and its historical S22 download.

The review is generated from current audit receipts; S22 remains the historical
research-file pointer for compatibility. ``front_door`` checks that its TIFF,
ZIP, card, and registered hashes agree before any entry page is published.
The renderer never grants permission to submit.
"""
import hashlib
from html import escape as esc
import json
import sys
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CURRENT = {
    "run_card": "run-card-S28-VFCD.json",
    "index_src": "review-8e8d86f2-index-src.html",
    "exec_src": "review-8e8d86f2-exec-src.html",
    "previous_run_cards": [
        "run-card-S22-OMTJ.json",
        "run-card-S20-RHTW.json",
        "run-card-ISO91.json",
        "run-card-OLC91.json",
        "run-card-XG91.json",
        "run-card-GEO91.json",
    ],
}


def front_door(root=ROOT):
    from scripts.render_geo91_portal import _registered_pair
    docs = root / "docs"
    card = json.loads((docs / CURRENT["run_card"]).read_text(encoding="utf-8"))
    verdict = card.get("verdict") if isinstance(card, dict) else None
    if not isinstance(verdict, dict) or card.get("ok_to_submit") is not False \
            or card.get("submission_ready") is not False or card.get("result") != "negative" \
            or verdict.get("promote") is not False or verdict.get("OK_TO_SUBMIT") != "NO":
        raise ValueError("Front door requires an explicitly negative research card")
    tif, zipped, hashes = _registered_pair(root, card["raster_path"], card["raster_sha256"])
    return {
        "run_card": CURRENT["run_card"],
        "ok_to_download": True,
        "ok_to_submit": False,
        "scope": "Historical published research artifact; format pass is not submission approval",
        "raster_sha256": hashes[".tif"],
        "tif": tif.relative_to(docs.resolve()).as_posix(),
        "zip": zipped.relative_to(docs.resolve()).as_posix(),
        "zip_sha256": hashes[".zip"],
        "verdict": "negative",
        "previous_run_cards": list(CURRENT["previous_run_cards"]),
        "note": "Renderer never sets ok_to_submit true.",
    }


def parallel_s18_callout(root=ROOT) -> str:
    """Render the separate S18 download only after rechecking bytes and fail-closed status."""
    docs = root / "docs"
    card_path = docs / "run-card-S18-UNIQUE.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("submission_ready") is not False:
        raise ValueError("S18-UNIQUE must remain explicitly not approved for submission")
    raster = card.get("raster", {})
    paths = {}
    for key in ("path", "zip"):
        value = raster.get(key)
        if not isinstance(value, str):
            raise ValueError(f"S18-UNIQUE run card missing {key} path")
        path = (root / value).resolve()
        if not path.is_relative_to((docs / "downloads").resolve()):
            raise ValueError(f"S18-UNIQUE {key} path escapes docs/downloads")
        paths[key] = path
    tif, archive_path = paths["path"], paths["zip"]
    tif_bytes, zip_bytes = tif.read_bytes(), archive_path.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != raster.get("sha256"):
        raise ValueError("S18-UNIQUE TIFF hash mismatch")
    if hashlib.sha256(zip_bytes).hexdigest() != raster.get("zip_sha256"):
        raise ValueError("S18-UNIQUE ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S18-UNIQUE ZIP must contain exactly its TIFF bytes")
    import numpy as np
    import rasterio
    with rasterio.open(tif) as ds:
        values = ds.read(1)
        metadata_ok = (
            ds.count == 1 and ds.dtypes[0] == "float32"
            and str(ds.crs) == card["validator"]["crs"]
            and list(ds.shape) == card["validator"]["shape"]
            and list(ds.transform)[:6] == card["validator"]["transform"]
            and ds.nodata is None
        )
    if (not metadata_ok or not np.isfinite(values).all()
            or float(values.min()) < 0 or float(values.max()) > 1
            or not np.isin(values, (0.0, 1.0)).all()
            or int((values > 0).sum()) != raster.get("n_dots")):
        raise ValueError("S18-UNIQUE TIFF failed front-door format checks")
    note = card.get("submission_note")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S18-UNIQUE note must contain 1–140 characters")
    name = card["submission_name"]
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    return f'''<section class="card" style="border:2px solid #17644e;background:#f0faf5" aria-label="S18 parallel research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — HISTORICAL RESEARCH</span> <span class="badge bad">OK TO SUBMIT: NO — DUPLICATE STOP</span></p>
<h2>S18-UNIQUE · Basin-stripped Bouguer curvature × RTP gradient · 20,000 dots</h2>
<p>This historical GeoTIFF was generated on a separate branch, not by the current session. Its format and bytes were checked, but 99.605% of its dots overlap a pinned lattice within 3 px: it is a duplicate. These engineering checks do not establish uniqueness or scientific improvement.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">↓ Download research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s18-unique-executive-summary.html">Submission-format guide</a> · <a href="run-card-S18-UNIQUE.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(raster["sha256"])}</code> · name <code>{esc(name)}</code> · note ({len(note)}/140): <code>{esc(note)}</code><br>Its historical run card checked only two registry references; the later <a href="review-8e8d86f2/s18-witness.json">99.605% lattice witness</a> supersedes its uniqueness PASS. Research download only; not cleared for a weekly slot.</p>
</section>'''


def parallel_s19_svhf_callout(root=ROOT) -> str:
    """Render the S19-SVHF parallel research download only after rechecking bytes and fail-closed status."""
    docs = root / "docs"
    card_path = docs / "run-card-S19-SVHF.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("submission_ready") is not False or card.get("verdict") != "negative":
        raise ValueError("S19-SVHF must remain explicitly not approved for submission")
    art = card.get("artifact", {})
    tif = (docs / art["file"]).resolve()
    archive_path = (docs / art["zip"]).resolve()
    if not tif.is_relative_to((docs / "downloads").resolve()) or not archive_path.is_relative_to((docs / "downloads").resolve()):
        raise ValueError("S19-SVHF artifact path escapes docs/downloads")
    tif_bytes, zip_bytes = tif.read_bytes(), archive_path.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != card.get("raster_sha256"):
        raise ValueError("S19-SVHF TIFF hash mismatch")
    if hashlib.sha256(zip_bytes).hexdigest() != art.get("zip_sha256"):
        raise ValueError("S19-SVHF ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S19-SVHF ZIP must contain exactly its TIFF bytes")
    note = card.get("note", "")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S19-SVHF note must contain 1–140 characters")
    name = card["submission_name"]
    h = card["holdout_dti"]
    sgmc = card["blind_sgmc_diagnostic"]
    reg = card["registry_comparison"]
    return f'''<section class="card" style="border:2px solid #17644e;background:#eef6f1" aria-label="S19-SVHF parallel research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — 18/18 DUAL-DECODER CERTIFIED</span> <span class="badge bad">OK TO SUBMIT: NO — NOT OK TO SUBMIT (0 SLOTS SPENT)</span></p>
<h2>S19-SVHF E3 · Stitched-OOF Semivariogram, Multi-Scale Hurst &amp; Piedmont Flexure · 37,654 dots</h2>
<p>100% backbone-orthogonal 58-feature PU hierarchy cross-fitted across 3 nested spatial OOF levels and emitted strictly from the stitched 4-fold OOF surface. Passes <strong>90/90 preregistered competitive (&lt;=80k-dot) rasters</strong> (max 3-px dot overlap <code>{reg["max_competitive_le_80k_3px_overlap"]*100:.2f}% &lt;= 70%</code>; post-merge also passes S18-HGBR <code>46.71%</code>, ISO91 <code>27.31%</code>, S18-UNIQUE <code>13.84%</code>) and lifts blind off-catalogue USGS SGMC discovery to <code>{sgmc["sgmc_gt_300m_dti"]:.6f}</code> (&gt;300 m) / <code>{sgmc["sgmc_gt_500m_dti"]:.6f}</code> (&gt;500 m, <code>{sgmc["dots_gt_10px_farfield_share"]*100:.1f}%</code> &gt;1 km). On <code>{esc(h["evaluator_version"])}</code> (60,988 positives): <code>{h["value"]:.6f} HOLDOUT-DTI</code> [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] (trails S18-HGBR/S17-CPAD; synthetic lattice witness <code>99.85% &gt; 70%</code>).</p>
<p><a class="button" download href="{esc(art["file"], quote=True)}">↓ Download S19-SVHF GeoTIFF</a> <a class="button outline" download href="{esc(art["zip"], quote=True)}">↓ S19-SVHF Single-TIFF ZIP</a> <a href="s19-svhf.html">Full S19-SVHF Audit</a> · <a href="s19-svhf-executive-summary.html">S19-SVHF DrivenData Guide</a> · <a href="run-card-S19-SVHF.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · ZIP SHA-256 <code>{esc(art["zip_sha256"])}</code> · name <code>{esc(name)}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


def s24_callout(root=ROOT) -> str:
    """Latest-session (S24-CCKM) research download, re-verified fail-closed.

    Reads only the committed E2 run card and the bytes on disk; raises rather
    than publishing a stale or submit-positive callout. Returns a banner that
    links the generated executive summary with the obvious download decision.
    """
    docs = root / "docs"
    card_path = docs / "s24/e2/run-card.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        raise ValueError("S24-CCKM must remain explicitly not approved for submission")
    if card.get("organizer_confirmed_score") is not None or card.get("estimated_leaderboard_score") is not None:
        raise ValueError("S24-CCKM must not claim an organizer score or leaderboard estimate")
    art = card.get("artifact", {})
    tif = (root / art["tif"]).resolve()
    archive_path = (root / art["zip"]).resolve()
    downloads = (docs / "downloads").resolve()
    if not tif.is_relative_to(downloads) or not archive_path.is_relative_to(downloads):
        raise ValueError("S24-CCKM artifact path escapes docs/downloads")
    tif_bytes = tif.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != card.get("raster_sha256"):
        raise ValueError("S24-CCKM TIFF hash mismatch")
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != art.get("zip_sha256"):
        raise ValueError("S24-CCKM ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if not n.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S24-CCKM ZIP must contain exactly its TIFF bytes")
    note = card.get("submission_note", "")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S24-CCKM note must contain 1-140 characters")
    h = card["holdout"]
    nine_max = card["correlation_overlap_vs_registry"]["final_dot_max_overlap_nine_leaders"]
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    return f'''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="S24-CCKM latest research artifact; not approved for submission">
<p><strong>Historical banner (superseded): 2026-10-28 current review: no new candidate; OK TO SUBMIT: NO.</strong> <a href="review-68881914-20261028.md">Current review and next steps</a> · <a href="run-card-20261028.json">Current run card</a></p>
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S24-CCKM E2 · Cross-contact kurtosis (B14&thinsp;&times;&thinsp;B13) · 37,654 dots · prior session 2026-10-27</h2>
<p>A research TIF was generated in the prior S24 session: unique vs the nine focus leaders (max {100*nine_max:.2f}% of dots within 3 px), HOLDOUT-DTI {h["dti"]:.6f} [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, {h["n_withheld_positives"]:,} withheld — not a leaderboard score). The historical v2 holdout is not matched to the corrected v3 context-buffer instrument. Verdict negative: its paired improvement over the gravity-gradient control is not established and fails the literal dense-lattice registry rule, so it must not be submitted. Full evidence, the nine-site table, and the future-submission guide: <a href="s24/executive-summary.html">S24 executive summary</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S24 research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s24/REVIEW.md">Session review</a> · <a href="s24/e2/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(card["submission_name"])}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


def concurrent_s26_callout(root=ROOT) -> str:
    """Link concurrent research without implying it was generated here."""
    report = json.loads((root / 'docs/review-4239f6e5/concurrent-s26-audit.json').read_text())
    rows = report.get('results', [])
    if (len(rows) != 3 or any(row.get('submission_ready') is not False
            or row.get('final_dot_comparison', {}).get('dot_status') != 'DUPLICATE' for row in rows)):
        raise ValueError('S26 callout requires three research-only duplicate stops')
    return '''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="Concurrent S26 research artifacts; not approved for submission">
<p><span class="badge">DOWNLOADS: RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>Concurrent S26 research · independently rechecked</h2><p>Three existing S26 TIFFs landed from other branches. Each exceeds the literal 70% duplicate threshold against the pinned lattice (98.14%–99.23%); the earlier narrower uniqueness claim is superseded. No new leaderboard estimate is defensible. Format checks depend on an unauthenticated sample mirror.</p>
<p><a href="s26/executive-summary.html">S26 downloads and gate table</a> · <a href="review-4239f6e5/concurrent-s26-audit.json">Byte and lattice recheck</a> · <a href="review-4239f6e5/executive-summary.html">Full comparison</a></p></section>'''


def s25_callout(root=ROOT) -> str:
    """Latest-session (S25-FABRIC) research download, re-verified fail-closed.

    Reads only the committed S25 run card and the bytes on disk; raises rather
    than publishing a stale or submit-positive callout.
    """
    docs = root / "docs"
    card_path = docs / "s25/run-card.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        raise ValueError("S25-FABRIC must remain explicitly not approved for submission")
    if card.get("organizer_confirmed_score") is not None or card.get("estimated_leaderboard_score") is not None:
        raise ValueError("S25-FABRIC must not claim an organizer score or leaderboard estimate")
    art = card.get("artifact", {})
    tif = (root / art["tif"]).resolve()
    archive_path = (root / art["zip"]).resolve()
    downloads = (docs / "downloads").resolve()
    if not tif.is_relative_to(downloads) or not archive_path.is_relative_to(downloads):
        raise ValueError("S25-FABRIC artifact path escapes docs/downloads")
    tif_bytes = tif.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != card.get("raster_sha256"):
        raise ValueError("S25-FABRIC TIFF hash mismatch")
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != art.get("zip_sha256"):
        raise ValueError("S25-FABRIC ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if not n.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S25-FABRIC ZIP must contain exactly its TIFF bytes")
    note = card.get("submission_note", "")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S25-FABRIC note must contain 1-140 characters")
    h = card["holdout"]
    corr = card["correlation_overlap_vs_registry"]
    nine_max = corr["final_dot_max_overlap_nine_leaders"]
    comp_max = corr["final_dot_max_overlap_competitive_le_90000px"]
    fresh = json.loads((docs / "review-4239f6e5/historical-s25-audit.json").read_text())
    witness = fresh["comparisons"]["frozen lattice"]
    if (fresh["raster"]["sha256"] != card["raster_sha256"] or fresh["ok_to_submit"] is not False
            or witness["dot_status"] != "DUPLICATE"):
        raise ValueError("S25 recheck contradicts the historical research artifact")
    lattice_overlap = witness["directed_overlap_within_3px"]
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    return f'''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="S25-FABRIC historical research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S25-FABRIC E2 · historical research artifact · 2026-10-28</h2>
<p>This is not a new TIFF from the current review. Its final dots overlap at most {100*nine_max:.2f}% within 3 px of the nine listed leaders, but a fresh recheck found {100*lattice_overlap:.2f}% overlap with the frozen lattice. Its earlier fold-local HOLDOUT-DTI {h["dti"]:.6f} [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, v3 folds, {h["n_withheld_positives"]:,} withheld) exceeded one matched control; it is not a measurement of the final static TIFF or a leaderboard score. No improvement over GEMSDOE32 is demonstrated. Verdict negative: do not submit. <a href="review-4239f6e5/historical-s25-audit.json">Recheck receipt</a> · <a href="review-4239f6e5/executive-summary.html">Current comparison</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S25 research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s25/REVIEW.md">Session review</a> · <a href="s25/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(card["submission_name"])}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''



def s27_osdr_callout(root=ROOT) -> str:
    """Latest de novo session (S27-OSDR) research download, re-verified fail-closed."""
    docs = root / "docs"
    card_path = docs / "s27-osdr/run-card.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        raise ValueError("S27-OSDR must remain explicitly not approved for submission")
    if card.get("organizer_confirmed", {}).get("score") is not None:
        raise ValueError("S27-OSDR must not claim an organizer score")
    diag = json.loads((docs / "s27-osdr/diagnostics.json").read_text(encoding="utf-8"))
    if diag.get("candidate", {}).get("sha256") != card.get("raster_sha256"):
        raise ValueError("S27-OSDR diagnostics do not describe the run-card raster")
    tif = (root / card["raster_file"]).resolve()
    archive_path = (root / card["zip_file"]).resolve()
    downloads = (docs / "downloads").resolve()
    if not tif.is_relative_to(downloads) or not archive_path.is_relative_to(downloads):
        raise ValueError("S27-OSDR artifact path escapes docs/downloads")
    tif_bytes = tif.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != card.get("raster_sha256"):
        raise ValueError("S27-OSDR TIFF hash mismatch")
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != card.get("zip_sha256"):
        raise ValueError("S27-OSDR ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if not n.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S27-OSDR ZIP must contain exactly its TIFF bytes")
    note = card.get("submission_note", "")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S27-OSDR note must contain 1-140 characters")
    h = card["holdout"]
    u = card["uniqueness"]
    d = h["paired_vs_incumbent_s25_fabric_e2"]
    sgmc = next(r for r in diag["sgmc"]["rows"] if r["name"] == "s27_cvdc_e2_candidate")
    lfi = next(r for r in diag["lfi"]["rows"] if r["name"] == "s27_cvdc_e2_candidate")
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    sub_name = tif.stem
    return f'''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="S27-OSDR latest de novo research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S27-OSDR · Contour–Potential V-Discordance + Sign-Locked Odd-Symmetric Dip-Reversal Stitched OOF · 37,654 dots · 2026-10-29</h2>
<p><strong>#1 blind off-catalogue USGS SGMC recall (<code>{sgmc["dti"]:.6f}</code>, &gt;500 m <code>{sgmc["dti_gt500m"]:.6f}</code>)</strong> and highest current S27 post-hoc LFI <code>MODEL_PROJECTION_NOT_A_SCORE</code> (<code>{lfi["ridge1"]:.5f}</code>, ridge=10 <code>{lfi["ridge10"]:.5f}</code>), with <code>HOLDOUT-DTI</code> <strong>{h["dti"]:.6f}</strong> [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, {h["n_withheld_positives"]:,} withheld; paired <code>&Delta;DTI = {d["delta"]:+.6f}</code> [{d["ci95"][0]:+.6f}, {d["ci95"][1]:+.6f}] vs S25-FABRIC E2). Unique vs all 9 focus leaders (max {100*u["dot_3px_max_nine_focus_leaders"]:.2f}% within 3 px), vs <code>GEMSDOE92 lbmc1</code> ({100*u["dot_3px_gemsdoe92_lbmc1"]:.2f}%), vs all 181 competitive sparse rasters &le;90k px (max {100*u["dot_3px_max_competitive_le_90000px"]:.2f}% &le; 70%), and vs all 5 concurrent S26/S27 candidates (max {100*u["concurrent_main_max_dot_3px"]:.2f}% &le; 70%). Fails literal synthetic 5-px lattice (<code>calib_r13lattice_00904.tif</code>, {100*u["dot_3px_max_frozen_64_all"]:.2f}%) &rarr; verdict <strong>negative</strong>; must not be uploaded to DrivenData. Full evidence, nine-site + GEMSDOE92 table, 5 hypotheses &amp; submission guide: <a href="s27-osdr/executive-summary.html">S27-OSDR executive summary</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S27-OSDR research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s27-osdr/REVIEW.md">Session review</a> · <a href="s27-osdr/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(sub_name)}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


def s27_cvdc_callout(root=ROOT) -> str:
    """Latest de novo session (S27-CVDC) research download, re-verified fail-closed."""
    docs = root / "docs"
    card_path = docs / "s27-cvdc/run-card.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        raise ValueError("S27-CVDC must remain explicitly not approved for submission")
    if card.get("organizer_confirmed_score") is not None or card.get("estimated_leaderboard_score") is not None:
        raise ValueError("S27-CVDC must not claim an organizer score or leaderboard estimate")
    diag = json.loads((docs / "s27-cvdc/diagnostics.json").read_text(encoding="utf-8"))
    if diag.get("candidate", {}).get("sha256") != card.get("raster_sha256"):
        raise ValueError("S27-CVDC diagnostics do not describe the run-card raster")
    art = card.get("artifact", {})
    tif = (root / art["tif"]).resolve()
    archive_path = (root / art["zip"]).resolve()
    downloads = (docs / "downloads").resolve()
    if not tif.is_relative_to(downloads) or not archive_path.is_relative_to(downloads):
        raise ValueError("S27-CVDC artifact path escapes docs/downloads")
    tif_bytes = tif.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != card.get("raster_sha256"):
        raise ValueError("S27-CVDC TIFF hash mismatch")
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != art.get("zip_sha256"):
        raise ValueError("S27-CVDC ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if not n.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S27-CVDC ZIP must contain exactly its TIFF bytes")
    note = card.get("submission_note", "")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S27-CVDC note must contain 1-140 characters")
    h = card["holdout"]
    corr = card["correlation_overlap_vs_registry"]
    d = h["paired_differences_all_controls"]["control_s25_fabric_e2"]
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    return f'''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="S27-CVDC latest de novo research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S27-CVDC · Contour-Potential Discordance + Valley-Floor Knickzone Stitched OOF Submodular Surface · 37,654 dots · 2026-10-29</h2>
<p>Highest de novo <code>HOLDOUT-DTI</code> in GEMSDOE91: <strong>{h["dti"]:.6f}</strong> [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, {h["n_withheld_positives"]:,} withheld; paired <code>&Delta;DTI = {d["delta"]:+.6f}</code> [{d["ci95"][0]:+.6f}, {d["ci95"][1]:+.6f}] vs S25-FABRIC control, and <code>+0.024184</code> above S27-FABRIC-FAR). Unique vs all 9 focus leaders (max {100*corr["final_dot_max_overlap_nine_leaders"]:.2f}% within 3 px) and vs every competitive registry raster &le;90,000 px (max {100*corr["final_dot_max_overlap_competitive_le_90000px"]:.2f}% &le; 70%, plus 19.34%&ndash;37.58% vs concurrent S26/S27 candidates). Fails literal blanket lattice raster (<code>calib_r13lattice_00904.tif</code>, 206,895 px, {100*corr["final_dot_max_overlap_all"]:.2f}%) &rarr; verdict <strong>negative</strong>; must not be uploaded to DrivenData. Full evidence, nine-site forensics, and submission guide: <a href="s27-cvdc/executive-summary.html">S27-CVDC executive summary</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S27-CVDC research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s27-cvdc/REVIEW.md">Session review</a> · <a href="s27-cvdc/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(card["submission_name"])}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


def s27_callout(root=ROOT) -> str:
    """Latest-session (S27-FABRIC-FAR) research download, re-verified fail-closed.

    Reads only the committed S27 run card + diagnostics and the bytes on disk;
    raises rather than publishing a stale or submit-positive callout.
    """
    docs = root / "docs"
    card_path = docs / "s27/run-card.json"
    if not card_path.is_file():
        return ""
    card = json.loads(card_path.read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("verdict") != "negative":
        raise ValueError("S27-FABRIC-FAR must remain explicitly not approved for submission")
    if card.get("organizer_confirmed_score") is not None or card.get("estimated_leaderboard_score") is not None:
        raise ValueError("S27-FABRIC-FAR must not claim an organizer score or leaderboard estimate")
    diag = json.loads((docs / "s27/diagnostics.json").read_text(encoding="utf-8"))
    if diag.get("candidate", {}).get("sha256") != card.get("raster_sha256"):
        raise ValueError("S27 diagnostics do not describe the run-card raster")
    art = card.get("artifact", {})
    tif = (root / art["tif"]).resolve()
    archive_path = (root / art["zip"]).resolve()
    downloads = (docs / "downloads").resolve()
    if not tif.is_relative_to(downloads) or not archive_path.is_relative_to(downloads):
        raise ValueError("S27-FABRIC-FAR artifact path escapes docs/downloads")
    tif_bytes = tif.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != card.get("raster_sha256"):
        raise ValueError("S27-FABRIC-FAR TIFF hash mismatch")
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != art.get("zip_sha256"):
        raise ValueError("S27-FABRIC-FAR ZIP hash mismatch")
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if not n.endswith("/")]
        if members != [tif.name] or archive.read(members[0]) != tif_bytes:
            raise ValueError("S27-FABRIC-FAR ZIP must contain exactly its TIFF bytes")
    note = card.get("submission_note", "")
    if not isinstance(note, str) or not 0 < len(note) <= 140:
        raise ValueError("S27-FABRIC-FAR note must contain 1-140 characters")
    h = card["holdout"]
    corr = card["correlation_overlap_vs_registry"]
    lfi = card.get("lfi_model_projection_not_a_score", {})
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    return f'''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="S27-FABRIC-FAR latest research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S27-FABRIC-FAR · Distance-stratified uniqueness-capped emission on the S25 fabric surface · 37,654 dots · latest session 2026-10-29</h2>
<p>A new TIF was generated this session: unique vs the nine focus leaders (max {100*corr["final_dot_max_overlap_nine_leaders"]:.2f}% of dots within 3 px) and vs every competitive registry raster (max {100*corr["final_dot_max_overlap_competitive_le_90000px"]:.2f}%, the gate S25 failed at 74.89%). Distance quotas moved the median dot from 5.8 px to 21.5 px from the catalogue; the labelled LFI model projection (not a score) rose from S25's 0.07917 to {lfi.get("ridge1", 0):.4f}, still below R0's projection (0.27342). HOLDOUT-DTI {h["dti"]:.6f} [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, v3 folds, {h["n_withheld_positives"]:,} withheld — not a leaderboard score); paired delta vs the matched incumbent is exactly 0 by fold construction (zero visible catalogue pixels inside every test quadrant). Verdict negative (gates G4/G5 fail), so it must not be submitted. Full evidence, file/estimate/uniqueness table, nine-site table and submission guide: <a href="s27/executive-summary.html">S27 executive summary</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S27 research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s27/REVIEW.md">Session review</a> · <a href="s27/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(card["submission_name"])}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


def _root_verdict() -> str:
    """Fail-closed redirect stub; S28-VFCD is the current advertised download."""
    return (
        "<p><strong>Current download: one NEW unique GeoTIFF (S28-VFCD, 2026-10-30).</strong> "
        "OK TO DOWNLOAD: YES &mdash; all automated gates PASS. "
        "OK TO SUBMIT: NO &mdash; NOT OK TO SUBMIT until the separate selector step approves a weekly slot "
        "(estimated score &asymp; 0.11, below the 0.2778 incumbent). Earlier reviews generated NO NEW TIFF; "
        "historical downloads remain research only.</p>"
        "<p><a href=\"docs/index.html\">Open current download and automated verdict</a></p>"
    )

def render() -> None:
    from scripts.render_s22_pages import render_sources as render_s22_sources
    from scripts.render_review_8e8d86f2 import render_sources as render_review_sources
    render_s22_sources()
    render_review_sources()
    from scripts.render_priority_review import render as render_priority_review
    render_priority_review()
    docs = ROOT / "docs"
    current = front_door(ROOT)  # fail before replacing any published page
    # The S22-XB artifact is a historical research run, not the current lane.
    # Keep it on its dedicated archive page; never inject its projection or
    # download callout into OMTJ's current entry points. This prevents two
    # incompatible run cards from appearing to be the current recommendation.
    parallel_card = (s27_osdr_callout(ROOT) + s27_cvdc_callout(ROOT) + s27_callout(ROOT)
                     + concurrent_s26_callout(ROOT) + s25_callout(ROOT)
                     + s24_callout(ROOT))
    for source_name, target_name in ((CURRENT['index_src'], "index.html"),
                                     (CURRENT['exec_src'], "executive-summary.html")):
        source = (docs / source_name).read_text(encoding="utf-8")
        marker, fallback = "<!--PARALLEL-CALLOUTS-->", '<main id="main">'
        if marker in source:
            page = source.replace(marker, parallel_card, 1)
        elif fallback in source:
            page = source.replace(fallback, fallback + parallel_card, 1)
        else:
            raise ValueError(f"Missing insertion point in {source_name}")
        # Release audit is a hard stop, not an optional positive banner.
        audit_path = docs / "s25-tlf/witness-audit-20261028.json"
        card_path = docs / "s25-tlf/run-card.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        tlf = json.loads(card_path.read_text(encoding="utf-8"))
        if audit.get("status") != "DUPLICATE_STOP" or tlf.get("ok_to_submit") is not False:
            raise ValueError("S25-TLF release state inconsistent with duplicate audit")
        notice = ('<div class="note" role="status"><strong>2026-10-28 AUDIT: DO NOT SUBMIT S25-TLF.</strong> '
                  'The previous approval was incorrect. The file is a duplicate under the required registry rule '
                  '(99.6017% of dots within 3 pixels of the pinned lattice). The previous 0.36 projection is withdrawn; '
                  'no leaderboard estimate or new candidate is available. '
                  '<a href="s25-tlf/executive-summary.html">Executive summary, research download and submission guide</a> · '
                  '<a href="s25-tlf/witness-audit-20261028.json">Measured audit</a>.</div>')
        page = page.replace('<main id="main">', '<main id="main">' + notice, 1)
        latest_card = json.loads((docs / "review-4239f6e5/run-card.json").read_text())
        latest_pre = json.loads((docs / "review-4239f6e5/experiment-preflight.json").read_text())
        capacity = latest_pre["capacity"]
        if (latest_card.get("verdict") != "negative" or latest_card.get("ok_to_submit") is not False
                or latest_card.get("candidate_generated") is not False or latest_card.get("raster_sha256") is not None
                or latest_pre.get("status") != "BLOCKED" or latest_pre.get("ok_to_submit") is not False
                or capacity["sample_semantics"]["status"] != "CONFLICT_WITH_ORGANIZER_DESCRIPTION"):
            raise ValueError("Latest review evidence inconsistent; refusing to render")
        current_notice = (
            '<div class="note" role="status"><strong>S28-VFCD · 2026-10-30: ONE NEW UNIQUE TIFF · '
            'OK TO DOWNLOAD: YES · OK TO SUBMIT: NO-BY-POLICY (selector step).</strong> '
            'Vent-field-conditioned PU-OOF detector with geothermometer-gated discharge-conduit and '
            'SGMC-off concordance features; 37,654 zeros-encoded dots via 300 m CELF. All automated gates PASS '
            '(format, [0,1], NaN-free, grid, catalogue-free; unique vs the nine leaders max 35.73% and vs 192 '
            'competitive registry rasters max 50.11%; surface max |&rho;| 0.150). Evidence-labeled estimate ≈ 0.11 '
            '(HOLDOUT-DTI 0.107918 [0.093351, 0.123297]; LFI MODEL projection 0.108&ndash;0.114) &mdash; below the '
            '0.2778 incumbent, so the science verdict is negative. '
            '<a href="s28-vfcd/executive-summary.html">Executive summary, nine-site table and submission guide</a> · '
            '<a href="run-card-S28-VFCD.json">Run card</a> · '
            '<a href="s28-vfcd/run-card.json">protocol run card</a> · '
            '<a download href="downloads/gems91-s28-vfcd_e3_vent_phys_cons_celf-37654dots-20261031T001943Z-13949183-zeros.tif">Download the unique TIF</a> · '
            '<a download href="downloads/gems91-s28-vfcd_e3_vent_phys_cons_celf-37654dots-20261031T001943Z-13949183-zeros.zip">Single-TIFF ZIP</a> '
            '(SHA-256 d7843af990f1530a7eb1be2302b545eea592c09f00469371eef1334f61897bc7). '
            'The local gates above are not an approval to upload that file: NOT OK TO SUBMIT until the '
            'separate selector step approves a weekly slot. OK TO SUBMIT: NO-BY-POLICY.</div>')
        previous_notice = (
            f'<div class="note" role="status"><strong>CURRENT REVIEW · 2026-10-29: NO NEW TIFF IN THIS REVIEW · OK TO SUBMIT: NO.</strong> '
            f'The method lane was unassigned. At the frozen budget, the measured mirrored-footprint capacity forces at least '
            f'{capacity["overlap_lower_bound"]:.2%} overlap with the lattice, above 70%. '
            f'The sample mirror has {capacity["sample_semantics"]["nonzero_inside_footprint"]:,} nonzero cells despite the organizer describing an all-zero sample; authenticity is unverified. '
            '<a href="review-4239f6e5/executive-summary.html">Executive table and research downloads</a> · '
            '<a href="review-4239f6e5/REVIEW.md">Full review</a> · '
            '<a href="review-4239f6e5/run-card.json">Negative run card</a>.</div>')
        page = page.replace('<main id="main">', '<main id="main">' + current_notice + previous_notice, 1)
        (docs / target_name).write_text(page, encoding="utf-8")
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    (ROOT / 'index.html').write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=docs/index.html">'
        '<title>GEMSDOE91 — current download and verdict</title></head><body><main>'
        '<h1>GEMSDOE91 · Current download</h1>' + _root_verdict() + 
        '<p><a href="docs/index.html">Open current download and automated verdict</a> · '
        '<a href="docs/s28-vfcd/executive-summary.html">Executive summary, nine-site table and submission guide</a> · '
        '<a href="docs/executive-summary.html">Portal submission guide</a> · '
        '<a href="docs/s28-vfcd/run-card.json">Run card</a> · '
        '<a href="docs/R0_ANALYSIS_S22.md">Why 0.2778</a> · '
        '<a href="docs/s27-osdr/executive-summary.html">S27-OSDR research candidate (#1 blind SGMC)</a></p>'
        '</main></body></html>\n', encoding='utf-8')

    from scripts.render_s25tlf_portal import render as render_correction
    render_correction()

if __name__ == "__main__":
    render()
