#!/usr/bin/env python3
"""GEO91 dedicated portal pages writer (called by scripts/render_portal.py).

Writes docs/geo91.html and docs/geo91-executive-summary.html from
docs/geo91-index-src.html and docs/geo91-exec-src.html without overwriting
the authoritative S16/S17 entry points docs/index.html and docs/executive-summary.html.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render() -> None:
    docs = ROOT / "docs"
    if (docs / "geo91-index-src.html").is_file():
        (docs / "geo91.html").write_bytes((docs / "geo91-index-src.html").read_bytes())
    if (docs / "geo91-exec-src.html").is_file():
        (docs / "geo91-executive-summary.html").write_bytes(
            (docs / "geo91-exec-src.html").read_bytes()
        )


if __name__ == "__main__":
    render()
