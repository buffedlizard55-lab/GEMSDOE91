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
    "run_card": "run-card-S22-OMTJ.json",
    "index_src": "review-8e8d86f2-index-src.html",
    "exec_src": "review-8e8d86f2-exec-src.html",
    "previous_run_cards": [
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
<p><strong>2026-10-28 current review: no new candidate; OK TO SUBMIT: NO.</strong> <a href="review-68881914-20261028.md">Current review and next steps</a> · <a href="run-card-20261028.json">Current run card</a></p>
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S24-CCKM E2 · Cross-contact kurtosis (B14&thinsp;&times;&thinsp;B13) · 37,654 dots · prior session 2026-10-27</h2>
<p>A research TIF was generated in the prior S24 session: unique vs the nine focus leaders (max {100*nine_max:.2f}% of dots within 3 px), HOLDOUT-DTI {h["dti"]:.6f} [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, {h["n_withheld_positives"]:,} withheld — not a leaderboard score). The historical v2 holdout is not matched to the corrected v3 context-buffer instrument. Verdict negative: its paired improvement over the gravity-gradient control is not established and fails the literal dense-lattice registry rule, so it must not be submitted. Full evidence, the nine-site table, and the future-submission guide: <a href="s24/executive-summary.html">S24 executive summary</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S24 research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s24/REVIEW.md">Session review</a> · <a href="s24/e2/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(card["submission_name"])}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


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
    tif_href = tif.relative_to(docs.resolve()).as_posix()
    zip_href = archive_path.relative_to(docs.resolve()).as_posix()
    return f'''<section class="card" style="border:3px solid #9b1c1c;background:#fff7ed" aria-label="S25-FABRIC latest research artifact; not approved for submission">
<p><span class="badge">OK TO DOWNLOAD: YES — RESEARCH ONLY</span> <span class="badge bad">OK TO SUBMIT: NO</span></p>
<h2>S25-FABRIC E2 · Granulometry + gravity–magnetic phase-lag spatial OOF · 37,654 dots · latest session 2026-10-28</h2>
<p>A new TIF was generated this session: unique vs the nine focus leaders (max {100*nine_max:.2f}% of dots within 3 px), HOLDOUT-DTI {h["dti"]:.6f} [{h["ci95"][0]:.6f}, {h["ci95"][1]:.6f}] ({esc(h["evaluator_version"])}, v3 folds, {h["n_withheld_positives"]:,} withheld — not a leaderboard score), beating its best matched control in paired holdout. Verdict negative: final dots reach {100*comp_max:.2f}% within 3 px of one competitive registry raster (limit 70%), and the labelled LFI model projection is low because its dots hug the mapped catalogue (median 5.8 px), so it must not be submitted. Full evidence, the nine-site table, estimated-score table and submission guide: <a href="s25/executive-summary.html">S25 executive summary</a>.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">Download S25 research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s25/REVIEW.md">Session review</a> · <a href="s25/run-card.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · name <code>{esc(card["submission_name"])}</code> · note ({len(note)}/140): <code>{esc(note)}</code></p>
</section>'''


def render() -> None:
    from scripts.render_s22_pages import render_sources as render_s22_sources
    from scripts.render_review_8e8d86f2 import render_sources as render_review_sources
    render_s22_sources()
    render_review_sources()
    docs = ROOT / "docs"
    current = front_door(ROOT)  # fail before replacing any published page
    # The S22-XB artifact is a historical research run, not the current lane.
    # Keep it on its dedicated archive page; never inject its projection or
    # download callout into OMTJ's current entry points. This prevents two
    # incompatible run cards from appearing to be the current recommendation.
    parallel_card = s25_callout(ROOT) + s24_callout(ROOT)
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
        if target_name == "index.html":
            notice = ('<div class="note" role="status"><strong>2026-10-28 current review: NO NEW TIFF · NOT OK TO SUBMIT.</strong> '
                      'The assigned method is missing and the current checkout has no data directory. S24 below is a previous research-only artifact, not a submission recommendation. '
                      '<a href="review-20261028/REVIEW.md">Current review and next steps</a> · <a href="review-20261028/run-card.json">Run card</a>.</div>')
            page = page.replace('<main id="main">', '<main id="main">' + notice, 1)
        (docs / target_name).write_text(page, encoding="utf-8")
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    (ROOT / 'index.html').write_text(
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="refresh" content="0;url=docs/index.html">'
        '<title>GEMSDOE91 — current download and verdict</title></head><body><main>'
        '<h1>GEMSDOE91 · Current review</h1><p>Historical review: NO NEW TIFF; S22 OMTJ research only. '
        'Prior S24-CCKM: research TIF generated (unique vs the nine focus sites), OK TO DOWNLOAD: YES — research only. '
        '<strong>OK TO SUBMIT: NO — NOT OK TO SUBMIT.</strong></p>'
        '<p><a href="docs/index.html">Open current download and automated verdict</a> · '
        '<a href="docs/s24/executive-summary.html">S24 executive summary, nine-site table and submission guide</a> · '
        '<a href="docs/executive-summary.html">Previous nine-site executive summary</a></p>'
        '</main></body></html>\n', encoding='utf-8')

if __name__ == "__main__":
    render()
