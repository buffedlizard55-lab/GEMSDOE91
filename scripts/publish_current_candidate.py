#!/usr/bin/env python3
"""Route the public portal to the most recent fail-closed candidate.

The historical S16-PGRD renderer remains for reproducibility, but S16-PC91 is
newer and has its own run card, audit and research-only TIFF. This router runs
last in the Pages build so old content cannot accidentally be presented as the
current candidate or imply upload approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def main() -> int:
    card_path = DOCS / "run-card-S16PC.json"
    card = json.loads(card_path.read_text(encoding="utf-8"))
    artifact = DOCS / "downloads" / f"{card['submission_name']}-zeros.tif"
    if not artifact.is_file():
        raise SystemExit(f"Current candidate is missing: {artifact}")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest != card.get("raster_sha256"):
        raise SystemExit(f"Current candidate SHA-256 mismatch: {digest}")
    if not card.get("ok_to_download") or card.get("ok_to_submit"):
        raise SystemExit("Refusing to publish: S16-PC91 must be download=yes, submit=no")

    (DOCS / "index.html").write_text("""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta http-equiv=\"refresh\" content=\"0;url=s16-pc91.html\"><title>GEMSDOE91 — current research candidate</title></head>
<body><main data-submission-ready=\"false\"><h1>OK TO DOWNLOAD: YES — RESEARCH · OK TO SUBMIT: NO</h1>
<p><strong>NOT OK TO SUBMIT.</strong> This is a research-only GeoTIFF. Its holdout result trails the comparable best and a later experiment variant hit the duplicate-stop rule.</p>
<p><a href=\"downloads/gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif\" download>Download the range-checked research TIFF</a></p>
<p><a href=\"run-card-S16PC.json\">Run card</a> · <a href=\"s16-pc91.html\">Open the full audit</a> · <a href=\"s16-executive-summary.html\">Executive summary and submission guidance</a> · <a href=\"archive-results.html\">Historical results archive</a></p></main></body></html>\n""", encoding="utf-8")
    (DOCS / "executive-summary.html").write_text("""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<meta http-equiv=\"refresh\" content=\"0;url=s16-executive-summary.html\"><title>Executive summary · GEMSDOE91</title></head>
<body><main data-submission-ready=\"false\"><h1>OK TO DOWNLOAD: YES — RESEARCH. OK TO SUBMIT: NO.</h1><p><strong>NOT OK TO SUBMIT.</strong> This candidate is a measured negative; do not upload it.</p><p><a href=\"downloads/gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif\" download>Download the research-only TIFF</a></p><p><a href=\"run-card-S16PC.json\">Run card</a> · <a href=\"s16-executive-summary.html\">Open the current executive summary and future submission guidance</a></p></main></body></html>\n""", encoding="utf-8")
    (DOCS / "current-run.json").write_text(json.dumps({
        "run_card": "run-card-S16PC.json",
        "candidate": card["submission_name"],
        "ok_to_download": True,
        "ok_to_submit": False,
        "verdict": "negative",
        "raster_sha256": digest,
        "holdout_dti": card["scores"]["primary_holdout"],
        "registry_scope": card["uniqueness"]["final_dots"].get("n_registry_rasters_checked"),
        "generated_by": "scripts/publish_current_candidate.py",
    }, indent=2) + "\n", encoding="utf-8")
    (ROOT / "index.html").write_text("""<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"refresh\" content=\"0;url=docs/index.html\"><title>GEMSDOE91 — research GeoTIFF</title></head><body><main><h1>GEMSDOE91</h1><p>Current automated verdict: OK TO DOWNLOAD — RESEARCH; OK TO SUBMIT — NO.</p><p><a href=\"docs/index.html\">Open the current candidate, download, and audit</a></p></main></body></html>\n""", encoding="utf-8")
    print(f"Published {card['submission_name']}: download YES, submit NO; sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
