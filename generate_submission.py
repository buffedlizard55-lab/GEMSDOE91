#!/usr/bin/env python3
"""Deprecated PR66 synthetic smoke script — disabled fail-closed (`IR-91-S15-01`).

Previous version fabricated a 1-pixel mock `data/official/existing_faults.tif`
and overwrote `docs/downloads/h91_submission_bundle.js` with random Gaussian
noise. Real builds must restore SHA-256 pinned official inputs via
`python3 scripts/restore_data.py` and run a pre-registered scientific lane
(e.g., `python3 scripts/run_s15_lane.py`).
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "BLOCKED (IR-91-S15-01): synthetic random-noise generation is never an "
        "approved competition submission and must never overwrite "
        "data/official/existing_faults.tif or h91_submission_bundle.js. "
        "Run `python3 scripts/restore_data.py` followed by "
        "`python3 scripts/run_s15_lane.py`.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
