#!/usr/bin/env python3
"""OLC91 current-entry-point injector (called last by scripts/render_portal.py).

Source of truth: docs/olc91-index-src.html + docs/olc91-exec-src.html. They are copied verbatim
to the site entry points so that a fresh portal render is byte-reproducible
(tests/test_submission_portal.py). Their numbers derive from docs/run-card-OLC91.json
(measured 2026-10-25), so update all three together. GEO91 sources remain as history.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render() -> None:
    docs = ROOT / "docs"
    (docs / "index.html").write_bytes((docs / "olc91-index-src.html").read_bytes())
    (docs / "executive-summary.html").write_bytes((docs / "olc91-exec-src.html").read_bytes())
    card = json.loads((docs / "run-card-OLC91.json").read_text(encoding="utf-8"))
    current = {
        "run_card": "run-card-OLC91.json",
        "ok_to_download": True,
        "ok_to_submit": card["verdict"]["OK_TO_SUBMIT"] == "YES",
        "raster_sha256": card["raster"]["sha256"],
        "previous_run_card": "run-card-GEO91.json",
    }
    (docs / "current-run.json").write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
