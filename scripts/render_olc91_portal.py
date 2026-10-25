#!/usr/bin/env python3
"""OLC91 current-entry-point injector (called last by scripts/render_portal.py).

Source of truth: docs/olc91-index-src.html + docs/olc91-exec-src.html. They are copied verbatim
to the site entry points, so a fresh portal render is byte-reproducible
(tests/test_submission_portal.py). The download is validated fail-closed first, with the same
registered-bytes / single-TIFF-ZIP / card-hash check as the XG91 front door
(scripts/render_geo91_portal._registered_pair). Numbers in the pages derive from
docs/run-card-OLC91.json (measured 2026-10-25), so update all three together. Never sets
ok_to_submit true.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def front_door(root=ROOT):
    from scripts.render_geo91_portal import _registered_pair
    docs = root / "docs"
    card = json.loads((docs / "run-card-OLC91.json").read_text(encoding="utf-8"))
    verdict = card.get("verdict") if isinstance(card, dict) else None
    if not isinstance(verdict, dict) or card.get("ok_to_submit") is not False \
            or card.get("submission_ready") is not False or card.get("result") != "negative" \
            or verdict.get("promote") is not False or verdict.get("OK_TO_SUBMIT") != "NO":
        raise ValueError("Front door requires an explicitly negative research card")
    tif, zipped, hashes = _registered_pair(root, card["raster_path"], card["raster_sha256"])
    return {
        "run_card": "run-card-OLC91.json",
        "ok_to_download": True,
        "ok_to_submit": False,
        "scope": "Current research download; format pass is not submission approval",
        "raster_sha256": hashes[".tif"],
        "tif": tif.relative_to(docs.resolve()).as_posix(),
        "zip": zipped.relative_to(docs.resolve()).as_posix(),
        "zip_sha256": hashes[".zip"],
        "verdict": "negative",
        "previous_run_cards": ["run-card-XG91.json", "run-card-GEO91.json"],
        "note": "Renderer never sets ok_to_submit true.",
    }


def render() -> None:
    docs = ROOT / "docs"
    current = front_door(ROOT)  # fail before replacing any published page
    (docs / "index.html").write_bytes((docs / "olc91-index-src.html").read_bytes())
    (docs / "executive-summary.html").write_bytes((docs / "olc91-exec-src.html").read_bytes())
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
