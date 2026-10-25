#!/usr/bin/env python3
"""Generate the preregistered real-data candidate once, or verify its download.

Never create mock labels in data/official, read another submission as a feature,
or describe random noise as a competition candidate. Tests use tools/make_fixture.py.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Run the frozen S16 experiment once; never uploads or selects a slot')
    parser.add_argument('--with-data', action='store_true', help='Also verify the pinned sample/footprint/catalogue')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    sys.path[:0] = [str(root), str(root / 'src')]
    if args.run:
        from scripts.run_s16_pgrd import run
        try:
            run()
        except FileExistsError as exc:
            parser.exit(1, f'{exc}\nUse this command without --run to verify the existing result.\n')
    from scripts.verify_s16 import verify
    try:
        report = verify(with_data=args.with_data)
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'ok_to_submit': False, 'error': str(exc)}))
        return 1
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
