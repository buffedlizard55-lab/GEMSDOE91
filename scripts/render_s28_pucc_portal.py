#!/usr/bin/env python3
"""S28-PUCC lane pages + hand-over to the single-owner front door.

Canonical lane sources live here (``docs/s28-pucc/page-*.html``,
``docs/s28-pucc/page-current-review.json``).  The public front door (root
``index.html``, ``docs/index.html`` banner, ``docs/submission-guide.html``,
``docs/current-review.json``) is owned by ``scripts/front_door.py`` and stamped
by ``front_door.enforce()``; this renderer only writes the lane's own pages and
then calls the enforcer, so legacy renderers can never leave a superseded
status on the door (the single-owner rule introduced on main).

Also renders the full S28-PUCC executive summary to
``docs/s28-pucc/executive-summary.html`` (links relative to that directory).
Deterministic and idempotent.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LANE = DOCS / "s28-pucc"


def _lane_copy(html: str) -> str:
    """Rewrite docs-relative links for use inside docs/s28-pucc/."""
    pairs = [
        ('href="downloads/', 'href="../downloads/'),
        ('href="s28-pucc/', 'href="'),
        ('href="submission-guide.html"', 'href="../submission-guide.html"'),
        ('href="index.html"', 'href="../index.html"'),
        ('href="R0_ANALYSIS_S22.md"', 'href="../R0_ANALYSIS_S22.md"'),
        ('href="../IRREGULARITIES.md"', 'href="../../IRREGULARITIES.md"'),
        ('href="../scripts/', 'href="../../scripts/'),
        ('href="review-20261030/', 'href="../review-20261030/'),
        ('href="s27-cvdc/', 'href="../s27-cvdc/'),
        ('href="s27-osdr/', 'href="../s27-osdr/'),
    ]
    for old, new in pairs:
        html = html.replace(old, new)
    return html


def render(root: Path = ROOT) -> None:
    docs = root / "docs"
    lane = docs / "s28-pucc"

    # Full executive summary, links relative to docs/s28-pucc/.
    exec_html = (lane / "page-executive-summary.html").read_text(encoding="utf-8")
    (lane / "executive-summary.html").write_text(_lane_copy(exec_html), encoding="utf-8")

    # Single-owner front door: stamp the active S28-PUCC state.
    import sys
    if str(root / "scripts") not in sys.path:
        sys.path.insert(0, str(root / "scripts"))
    import front_door as _fd
    if not _fd.enforce():
        raise RuntimeError("front_door.enforce() found no active candidate pages")


if __name__ == "__main__":
    render()
