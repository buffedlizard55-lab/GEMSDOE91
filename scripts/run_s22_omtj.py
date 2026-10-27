#!/usr/bin/env python3
"""Fail-closed entry point for the completed, duplicate-stopped S22 run.

The historical runner is archived under evidence/s22. It used compromised
finite-NoData inputs, and its final combined rank/overlap branch did not stop
on negative rank correlation below -0.90. A missing receipt must not re-enable
it. A later, separately assigned experiment needs a fresh preregistration,
buffered shared folds, both novelty phases, and a matched incumbent.
"""
from __future__ import annotations

import json


def run() -> None:
    raise RuntimeError(
        'S22-OMTJ is a frozen, duplicate-stopped historical experiment; '
        'its feature inputs were contaminated and the old runner is unsafe. '
        'A new assigned lane and full preflight are required. See '
        'docs/review-ad43b4e5/REVIEW.md.'
    )


def main() -> int:
    try:
        run()
    except RuntimeError as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc),
                          'candidate_generated': False, 'ok_to_submit': False}, indent=2))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
