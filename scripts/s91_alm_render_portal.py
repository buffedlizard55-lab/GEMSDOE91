"""S91-ALM front-door banner renderer.

The active front door is owned by S28 (``scripts/s28_render_portal.py``) and
re-applied by ``scripts/front_door.py`` after every legacy renderer.  This
renderer runs LAST in ``scripts/render_portal.py``'s chain and adds the S91-ALM
candidate banner **in parallel**: it inserts ahead of the first status note and
never deletes the S28 banner or any historical note, so both certified unique
candidates stay one click away from the deployed Pages site.

It only ever writes banners/links; it does not republish a verdict for any other
lane and it does not touch ``docs/current-review.json`` (owned by S28).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S91_DIR = ROOT / "docs" / "s91-alm"
CAND = "gems91-s91-alm-alteration-halo-20261031T010114Z-5834ff6c"


def banner() -> str:
    return (
        '<div class="note" role="status" style="border-left:6px solid #12503f;background:#e9f7ee">'
        '<strong>S91-ALM · 2026-10-31: NEW UNIQUE SUBMISSION · OK TO DOWNLOAD: YES · '
        'OK TO SUBMIT: NO (selector step pending).</strong> '
        'A second certified unique candidate, from the alteration-magnetic-low concealed-fault prior: '
        '37,654 binary dots, at most 23.8% 3-px overlap with any of the nine focus-site leaders, all '
        'pixels finite in [0, 1]. It is a negative holdout by design (HOLDOUT-DTI 0.0), so no leaderboard '
        'score is estimated. '
        f'<a class="button" download href="downloads/{CAND}-zeros.tif">Download the GeoTIFF</a> '
        '<a href="s91-alm/executive-summary.html">Executive summary, nine-site table and submission guide</a> · '
        '<a href="s91-alm/REVIEW.md">Technical review</a> · <a href="s91-alm/run-card.json">Run card</a> · '
        '<a href="s91-alm/HYPOTHESES.md">Hypotheses</a> · '
        '<a href="s91-alm/nine-leader-overlap.json">nine-leader overlap receipt</a>.'
        '</div>'
    )


def _patch(path: Path) -> bool:
    """Insert the S91-ALM banner ahead of the first status note (idempotent)."""
    if not path.is_file():
        return False
    src = path.read_text(encoding="utf-8")
    new = banner()
    if new in src:
        return False
    m = re.search(r'<div class="note" role="status"[^>]*>.*?</div>', src, re.S)
    if m:
        src = src[:m.start()] + new + src[m.start():]
    else:
        anchor = re.search(r'<(body|main)[^>]*>', src)
        if not anchor:
            return False
        src = src[:anchor.end()] + new + src[anchor.end():]
    path.write_text(src, encoding="utf-8")
    return True


def patch_portal_pages(root: Path = ROOT) -> list:
    """Add the S91-ALM banner to the two portal pages (idempotent).

    Called both by ``scripts/render_portal.py`` (last in the chain) and by
    ``scripts/render_olc91_portal.render()`` (which rebuilds these two pages from
    its own templates and would otherwise drop the banner).
    """
    changed = []
    for name in ("docs/index.html", "docs/executive-summary.html"):
        if _patch(root / name):
            changed.append(name)
    return changed


def render(root: Path = ROOT) -> None:
    changed = patch_portal_pages(root)
    # The S91-ALM executive summary subpage is this lane's own record.
    from scripts.render_s91_alm_summary import render as render_summary

    render_summary(root)
    print("s91-alm front-door banner added to:", ", ".join(changed) if changed else "(already present)")


if __name__ == "__main__":
    render(ROOT)
