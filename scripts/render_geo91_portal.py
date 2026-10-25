#!/usr/bin/env python3
"""GEO91 current-entry-point injector (called last by scripts/render_portal.py).

Source of truth: docs/geo91-index-src.html + docs/geo91-exec-src.html.
Copies them verbatim to the site entry points so a fresh portal render is
reproducible (tests/test_submission_portal.py). Numbers inside derive from
docs/run-card-GEO91.json (measured 2026-10-25); update all three together.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render() -> None:
    docs = ROOT / "docs"
    (docs / "index.html").write_bytes((docs / "geo91-index-src.html").read_bytes())
    (docs / "executive-summary.html").write_bytes((docs / "geo91-exec-src.html").read_bytes())
    card = json.loads((docs / "run-card-GEO91.json").read_text(encoding="utf-8"))
    current = {
        "run_card": "run-card-GEO91.json",
        "ok_to_download": True,
        "ok_to_submit": False,
        "raster_sha256": card["e2_raster_sha256"],
    }
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
