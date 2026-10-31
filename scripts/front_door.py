"""Single owner for the public front door.

This repository accumulated at least six renderers that all wrote
``docs/index.html`` or the root ``index.html``.  After a session generated a
certified candidate, any of them running later silently reinstated a
superseded "no candidate / do not submit" banner on the deployed Pages site —
a real production bug, not just a test-order artefact.

``enforce()`` re-applies the ACTIVE front door after any legacy renderer.
Active owner from 2026-10-31 (ladder, newest first): **S28-PUCC**
(arena/db03647e; unique TIF, promoted to selector), previously **S30-VCSE**
(arena/681fc5eb; holdout-gated HOLD) and **S30-VCE** (arena/c2ae33eb).
Canonical sources live under ``docs/s28-pucc/page-*.html`` and
``docs/s28-pucc/page-current-review.json`` (landing page, submission guide,
executive summary, active-review pointer) plus the active banner
injected/replaced on the legacy-built portal pages.  S30-VCSE, S30-VCE, S28,
S28-VSD, S28-VFCD, S91-ALM and the geothermal-blind lane are preserved as
concurrent session records inside the
pages; legacy renderers keep their own dated pages and simply stop owning the
status banner.

Future sessions: point ``active()`` at your canonical pages, update the notice
in ``render_review_20261030._active_notice`` (kept there for the banner-merge
helpers), and keep every other lane as a concurrent record.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent


def active() -> bool:
    return (ROOT / "docs" / "s28-pucc" / "page-landing.html").is_file()


def enforce() -> bool:
    """Re-stamp the active S28-PUCC front door. Returns True if a candidate exists."""
    if not active():
        return False
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import importlib

    import render_review_20261030 as rr  # noqa: PLC0415

    importlib.reload(rr)

    docs = ROOT / "docs"
    lane = docs / "s28-pucc"
    # The S28-VSD status block is a pinned, idempotent additive record inside
    # docs/index.html (newest-first ordering); keep it present across rebuilds.
    try:
        import render_s28_portal as vsd  # noqa: PLC0415
        vsd.main()
    except Exception:  # noqa: BLE001 - the record block must never break the front door
        pass
    guide_src = (lane / "page-submission-guide.html").read_text(encoding="utf-8")
    (docs / "submission-guide.html").write_text(guide_src + "\n", encoding="utf-8")
    pointer = (lane / "page-current-review.json").read_text(encoding="utf-8")
    (docs / "current-review.json").write_text(pointer, encoding="utf-8")
    notice = rr._active_notice()
    for name in ("index.html", "executive-summary.html"):
        path = docs / name
        if not path.is_file():
            raise FileNotFoundError(path)
        source = path.read_text(encoding="utf-8")
        source = rr._replace_current_notice(source, notice)
        path.write_text(source, encoding="utf-8")
    root_html = (lane / "page-landing.html").read_text(encoding="utf-8")
    (ROOT / "index.html").write_text(root_html, encoding="utf-8")
    return True


if __name__ == "__main__":
    print("active front door enforced:", enforce())
