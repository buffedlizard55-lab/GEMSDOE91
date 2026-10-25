#!/usr/bin/env python3
"""Restore/check the frozen pre-experiment index; NEVER discover new references.

The 64-file inventory used by CED91 is evidence. Do not regenerate it by globbing
current downloads, silently self-index the candidate, remove a dense reference,
or describe this partial index as an organizer-complete registry.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
REPO = 'buffedlizard55-lab/60GEMSDOE'


def validate_rows(rows, candidate_sha):
    paths = set()
    for row in rows:
        path = ROOT / row['path']
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        if not relative.startswith(('data/fleet_registry/', 'docs/downloads/')):
            raise ValueError(f'Unexpected registry path: {relative}')
        if relative in paths or row['sha256'] == candidate_sha:
            raise ValueError('Repeated reference path or forbidden candidate self-comparison')
        paths.add(relative)


def restore(row, check=False, available_only=False):
    dest = ROOT / row['path']
    if dest.is_file():
        data = dest.read_bytes()
    else:
        if check or 'git_blob' not in row:
            if available_only and 'git_blob' not in row:
                return None
            raise ValueError(f'Missing pinned reference: {row["path"]}')
        data = subprocess.check_output(['gh', 'api', f'repos/{REPO}/git/blobs/{row["git_blob"]}',
                                       '-H', 'Accept: application/vnd.github.raw'], timeout=120)
    if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['bytes']:
        raise ValueError(f'Registry SHA256/size mismatch: {row["path"]}')
    if 'git_blob' in row:
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != row['git_blob']:
            raise ValueError(f'Registry Git blob mismatch: {row["path"]}')
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_suffix(dest.suffix+'.part')
        temp.write_bytes(data); temp.replace(dest)
    return row['path']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='Verify existing files; no network')
    ap.add_argument(
        '--available-only',
        action='store_true',
        help='Restore/verify all git_blob and present local references while reporting quarantined/removed local entries',
    )
    args = ap.parse_args()
    inventory = ROOT/'registry/comparison_inventory.json'
    if not inventory.is_file():
        raise SystemExit('Frozen index missing. Obtain its pinned source; do not rebuild it from current downloads.')
    rows = json.loads(inventory.read_text())['files']
    candidate = json.loads((ROOT/'docs/run-card.json').read_text()).get('raster_sha256')
    validate_rows(rows, candidate)
    before = inventory.read_bytes()
    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(lambda row: restore(row, args.check, args.available_only), rows))
    restored = [p for p in outcomes if p is not None]
    skipped = [row['path'] for row, p in zip(rows, outcomes) if p is None]
    if before != inventory.read_bytes():
        raise RuntimeError('Frozen registry was unexpectedly modified')
    if skipped:
        print(
            f'Verified {len(restored)}/{len(rows)} frozen references '
            f'(unavailable quarantined local entries: {skipped}); '
            'inventory unchanged; completeness UNVERIFIED; no experiment run.'
        )
    else:
        print(f'Verified {len(restored)} frozen references; inventory unchanged; completeness UNVERIFIED; no experiment run.')


if __name__ == '__main__':
    main()
