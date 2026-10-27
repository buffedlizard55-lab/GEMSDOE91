#!/usr/bin/env python3
"""Refresh the nine focus-repository source inventory, not a score feed.

Reads immutable GitHub snapshots via the shared fleet auditor. Page text is
owner-supplied and never becomes an organizer-confirmed result. Network errors
are preserved as explicit failures; no model experiment or upload is run.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.audit_fleet import audit  # noqa: E402

FOCUS = (24, 25, 27, 28, 30, 31, 32, 33, 36)


def capture(workers=3):
    if not 1 <= workers <= 6:
        raise ValueError('workers must be in 1..6')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(audit, FOCUS))
    return {
        'schema': 'gems91.focus-source-inventory.v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'GitHub repository main snapshots, not competition receipts or a leaderboard feed',
        'complete_universal_registry': False,
        'geological_experiments_run': 0,
        'rows': rows,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workers', type=int, default=3)
    p.add_argument('--output', type=Path, default=ROOT/'docs/review-8e8d86f2/focus-inventory.json')
    args = p.parse_args(argv)
    result = capture(args.workers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    n = sum(r['status'] == 'FETCHED_GITHUB_SNAPSHOT' and not r.get('tree_truncated') for r in result['rows'])
    print(f"Focus inventory: {n}/{len(FOCUS)} nontruncated GitHub snapshots fetched; no scores verified.")
    return 0 if n == len(FOCUS) else 1


if __name__ == '__main__':
    raise SystemExit(main())
