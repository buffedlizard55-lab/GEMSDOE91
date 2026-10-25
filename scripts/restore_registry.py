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
RETRACTED_GEOD_BLOBS = {
    'docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21-zeros.tif': (
        'buffedlizard55-lab/GEMSDOE91',
        'ce7a7e3a6270fef922ade0b47a26f5287e16071b',
    ),
    'docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21.tif': (
        'buffedlizard55-lab/GEMSDOE91',
        '26b756e08bd365a61aa3cb22f5a87af223bc9fe5',
    ),
}


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


def restore(row, check=False):
    rel_path = row['path']
    dest = ROOT / rel_path
    retracted_info = RETRACTED_GEOD_BLOBS.get(rel_path)
    if not dest.is_file() and retracted_info is not None:
        dest = ROOT / 'data' / 'retracted_geod' / Path(rel_path).name
    git_repo = REPO
    git_blob = row.get('git_blob')
    if git_blob is None and retracted_info is not None:
        git_repo, git_blob = retracted_info

    if dest.is_file():
        data = dest.read_bytes()
    else:
        if check or git_blob is None:
            raise ValueError(f'Missing pinned reference: {row["path"]}')
        data = subprocess.check_output(['gh', 'api', f'repos/{git_repo}/git/blobs/{git_blob}',
                                       '-H', 'Accept: application/vnd.github.raw'], timeout=120)
    if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['bytes']:
        raise ValueError(f'Registry SHA256/size mismatch: {row["path"]}')
    if git_blob is not None:
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != git_blob:
            raise ValueError(f'Registry Git blob mismatch: {row["path"]}')
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_suffix(dest.suffix+'.part')
        temp.write_bytes(data); temp.replace(dest)
    return row['path']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='Verify existing files; no network')
    args = ap.parse_args()
    inventory = ROOT/'registry/comparison_inventory.json'
    if not inventory.is_file():
        raise SystemExit('Frozen index missing. Obtain its pinned source; do not rebuild it from current downloads.')
    rows = json.loads(inventory.read_text())['files']
    candidate = json.loads((ROOT/'docs/run-card.json').read_text()).get('raster_sha256')
    validate_rows(rows, candidate)
    before = inventory.read_bytes()
    with ThreadPoolExecutor(max_workers=4) as pool:
        restored = list(pool.map(lambda row: restore(row, args.check), rows))
    if before != inventory.read_bytes():
        raise RuntimeError('Frozen registry was unexpectedly modified')
    print(f'Verified {len(restored)} frozen references; inventory unchanged; completeness UNVERIFIED; no experiment run.')


if __name__ == '__main__':
    main()
