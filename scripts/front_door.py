"""Single owner for the public front door.

This repository accumulated at least six renderers that all wrote
``docs/index.html`` or the root ``index.html``.  After S28 generated a certified
candidate, any of them running later silently reinstated a superseded
"no candidate / do not submit" banner on the deployed Pages site — a real
production bug, not just a test-order artefact.

``enforce()`` re-applies the active S28 front door after any legacy renderer.
Legacy renderers keep their own dated pages; they simply stop owning the status
banner.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent


def active() -> bool:
    return (ROOT / "docs" / "s28" / "candidate.json").is_file()


def enforce() -> bool:
    """Re-render the S28 front door. Returns True if a candidate exists."""
    if not active():
        return False
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import importlib

    import s28_render_portal  # noqa: PLC0415

    importlib.reload(s28_render_portal)
    s28_render_portal.render()
    return True


if __name__ == "__main__":
    print("s28 front door enforced:", enforce())
