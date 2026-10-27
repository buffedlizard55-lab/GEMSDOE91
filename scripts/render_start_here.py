#!/usr/bin/env python3
"""Compatibility entry point: render the current fail-closed review.

The concurrent START HERE version made a narrower-scope uniqueness claim and
would overwrite the newer root verdict. Its exact source and page are archived
under evidence/parallel-start-here; invoking its old command now preserves the
current front door and historical-download distinction.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from scripts.render_olc91_portal import render
    render()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
