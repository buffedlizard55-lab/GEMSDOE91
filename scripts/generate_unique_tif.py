#!/usr/bin/env python3
"""Fail-closed replacement for the historical S18 demo generator.

The original source is archived as inert evidence at
``evidence/s18/generate_unique_tif-original.py.txt``.  It wrote directly into
``docs/downloads`` and the historical card without the required full surface,
registry and matched holdout gates.  A previously generated file is a measured
literal duplicate.  A capacity bound is not a uniqueness certificate.

Do not run a new experiment until an authorized lane, budget, vetted inputs,
pre-placement registry check and shared evaluator/writer are available.
"""
from __future__ import annotations
import json


def main() -> int:
    print(json.dumps({
        'status': 'BLOCKED',
        'reason': 'Legacy generator cannot satisfy the required novelty and scientific gates; historical S18 is a measured duplicate.',
        'new_candidate_generated': False,
        'ok_to_submit': False,
        'evidence': 'docs/review-8e8d86f2/s18-witness.json',
        'preflight': 'scripts/experiment_preflight.py',
    }, indent=2))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
