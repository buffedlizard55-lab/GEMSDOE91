#!/usr/bin/env python3
"""CWP91 namespaced-page builder (parallel session; NOT the front door).

At merge time the session was integrated beside the then-current HEXFAR91/OLC91
front door, following the repo's parallel-session convention (cf. s17-cdsc.html):
this script copies docs/cwp91-index-src.html -> docs/cwp91.html and
docs/cwp91-exec-src.html -> docs/cwp91-executive-summary.html after fail-closed
validation of the registered download bytes (same _registered_pair check as the
front doors). It never writes docs/index.html, docs/executive-summary.html or
docs/current-run.json, and scripts/render_portal.py deliberately does not call it,
so a fresh portal render reproduces the committed entry points byte-for-byte.
Numbers in the pages derive from docs/run-card-CWP91.json (measured 2026-10-25).
Never sets ok_to_submit true.

    python scripts/render_cwp91_portal.py   # rebuild the two namespaced pages
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def registered_download(root=ROOT):
    from scripts.render_geo91_portal import _registered_pair
    docs = root / "docs"
    card = json.loads((docs / "run-card-CWP91.json").read_text(encoding="utf-8"))
    if card.get("ok_to_submit") is not False or card.get("result") != "negative" \
            or card["verdict"].get("OK_TO_SUBMIT") != "NO":
        raise ValueError("CWP91 pages require an explicitly negative research card")
    tif, zipped, hashes = _registered_pair(root, card["raster_path"], card["raster_sha256"])
    return {
        "run_card": "run-card-CWP91.json",
        "ok_to_download": True,
        "ok_to_submit": False,
        "scope": "Namespaced parallel-session research download; format pass is not submission approval",
        "raster_sha256": hashes[".tif"],
        "tif": tif.relative_to(docs.resolve()).as_posix(),
        "zip": zipped.relative_to(docs.resolve()).as_posix(),
        "zip_sha256": hashes[".zip"],
        "verdict": "negative",
    }


def render() -> None:
    docs = ROOT / "docs"
    registered_download(ROOT)  # fail before replacing any published page
    (docs / "cwp91.html").write_bytes((docs / "cwp91-index-src.html").read_bytes())
    (docs / "cwp91-executive-summary.html").write_bytes((docs / "cwp91-exec-src.html").read_bytes())


if __name__ == "__main__":
    render()
