#!/usr/bin/env python3
"""Current-entry-point injector (called last by scripts/render_portal.py).

Historical module name (introduced by OLC91); it now serves whichever lane is configured in
``CURRENT`` below. Only that one dict changes when a new measured lane becomes the current file.
Since session bacc7c26 the current lane is ISO91.

Source of truth: ``CURRENT['index_src']`` and ``CURRENT['exec_src']``, rendered from the run card by
scripts/render_iso91_pages.py. They are copied verbatim to the site entry points, so a fresh portal render
is byte-reproducible (tests/test_submission_portal.py). The download is validated fail-closed first,
with the same registered-bytes / single-TIFF-ZIP / card-hash check as the XG91 front door
(scripts/render_geo91_portal._registered_pair). The renderer never sets ok_to_submit true: a card
that is not an explicitly negative research card is refused.

Parallel-branch callouts (currently S18-UNIQUE, added on main) are re-verified fail-closed by
``parallel_s18_callout`` and inserted at the ``<!--PARALLEL-CALLOUTS-->`` marker of the current sources,
i.e. after the current file's download and verdict, so they never displace the current download from
the top of the page. Sources without the marker fall back to insertion right after ``<main id="main">``.
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
    "run_card": "run-card-ISO91.json",
    "index_src": "iso91-index-src.html",
    "exec_src": "iso91-exec-src.html",
    "previous_run_cards": ["run-card-OLC91.json", "run-card-XG91.json", "run-card-GEO91.json"],
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
        "scope": "Current research download; format pass is not submission approval",
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
<p><span class="badge">OK TO DOWNLOAD: YES — FORMAT-CHECKED RESEARCH</span> <span class="badge bad">OK TO SUBMIT: NO — HOLDOUT / CANARY / FULL REGISTRY PENDING</span></p>
<h2>S18-UNIQUE · Basin-stripped Bouguer curvature × RTP gradient · 20,000 dots</h2>
<p>This GeoTIFF was generated on a separate parallel branch, not by the current session. The front-door renderer rechecked its SHA-256, TIFF metadata, finite binary [0,1] values, dot count, and single-TIFF ZIP byte identity. These engineering checks do not establish a full-registry uniqueness pass or scientific improvement.</p>
<p><a class="button" download href="{esc(tif_href, quote=True)}">↓ Download research GeoTIFF</a> <a class="button outline" download href="{esc(zip_href, quote=True)}">Single-TIFF ZIP</a> <a href="s18-unique-executive-summary.html">Submission-format guide</a> · <a href="run-card-S18-UNIQUE.json">Run card</a></p>
<p class="small">SHA-256 <code>{esc(raster["sha256"])}</code> · name <code>{esc(name)}</code> · note ({len(note)}/140): <code>{esc(note)}</code><br>Its run card records HOLDOUT-DTI NOT RUN, canary pending, and full-registry novelty pending. Research download only; not cleared for a weekly slot.</p>
</section>'''


def render() -> None:
    docs = ROOT / "docs"
    current = front_door(ROOT)  # fail before replacing any published page
    parallel_card = parallel_s18_callout(ROOT)
    for source_name, target_name in ((CURRENT["index_src"], "index.html"),
                                     (CURRENT["exec_src"], "executive-summary.html")):
        source = (docs / source_name).read_text(encoding="utf-8")
        marker, fallback = "<!--PARALLEL-CALLOUTS-->", '<main id="main">'
        if marker in source:
            page = source.replace(marker, parallel_card, 1)
        elif fallback in source:
            page = source.replace(fallback, fallback + parallel_card, 1)
        else:
            raise ValueError(f"Missing insertion point in {source_name}")
        (docs / target_name).write_text(page, encoding="utf-8")
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    render()
