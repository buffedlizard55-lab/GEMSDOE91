#!/usr/bin/env python3
"""Verify the actual current-run pointer, not a historical run-card schema.

This is a technical research-download check, never a promotion instrument.
Missing references, stale hashes and unsafe pointers fail closed.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_downloads import inspect_raster


def local_file(base: Path, value: str, directory: str = '') -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError('Missing local path')
    path = (base / value).resolve()
    if not path.is_relative_to((base / directory).resolve()):
        raise ValueError('Path escapes allowed directory')
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def verify(root: Path = ROOT) -> dict:
    docs = root / 'docs'
    pointer = json.loads((docs / 'current-run.json').read_text())
    # No inference from format PASS to slot authorization, even if edited by hand.
    if pointer.get('ok_to_submit') is not False or pointer.get('verdict') != 'negative':
        raise ValueError('Research frontdoor cannot authorize submission')
    if pointer.get('ok_to_download') is not True:
        raise ValueError('Current download is not advertised as available')
    card = json.loads(local_file(docs, pointer['run_card']).read_text())
    verdict = card.get('verdict')
    if not isinstance(verdict, dict) or verdict.get('promote') is not False or verdict.get('OK_TO_SUBMIT') != 'NO':
        raise ValueError('Pointer and research run-card verdict disagree')
    tif = local_file(docs, pointer['tif'], 'downloads')
    archive = local_file(docs, pointer['zip'], 'downloads')
    raster = card['raster']
    for field, expected in [('path', 'docs/' + pointer['tif']),
                            ('zip', 'docs/' + pointer['zip']),
                            ('sha256', pointer['raster_sha256']),
                            ('zip_sha256', pointer['zip_sha256'])]:
        if raster.get(field) != expected:
            raise ValueError(f'Current pointer/run-card mismatch: {field}')
    note = card['submission_note']
    if not isinstance(note, str) or not note or len(note) > 140:
        raise ValueError('Invalid submission note')
    data = tif.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    if sha != pointer['raster_sha256']:
        raise ValueError('Current TIFF SHA256 mismatch')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != pointer['zip_sha256']:
        raise ValueError('Current ZIP SHA256 mismatch')
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != data:
            raise ValueError('ZIP must contain exactly the current TIFF bytes')
    manifest = json.loads((root / 'registry/data_manifest.json').read_text())
    rows = {r['id']: r for r in manifest['files']}
    paths = {}
    for key in ('sample_submission', 'existing_faults'):
        row = rows[key]
        path = local_file(root / 'data', row['local_subpath'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError(f'Untrusted reference: {key}')
        paths[key] = path
    with rasterio.open(paths['sample_submission']) as src:
        grid = (src.count, src.shape, src.crs, src.transform)
        footprint = np.isfinite(src.read(1))
    with rasterio.open(paths['existing_faults']) as src:
        if (src.count, src.shape, src.crs, src.transform) != grid:
            raise ValueError('Catalogue grid mismatch')
        catalogue = src.read(1) > 0
    report = inspect_raster(data, grid, footprint, catalogue)
    if report['status'] != 'PASS':
        raise ValueError(f'Current TIFF technical failure: {report["checks"]}')
    return dict(status='PASS', scope='current-run.json research download only',
                tif=pointer['tif'], raster_sha256=sha, validator_output=report,
                ok_to_download=True, ok_to_submit=False)


def main() -> int:
    try:
        report = verify()
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps(dict(status='BLOCKED', ok_to_download=False,
                              ok_to_submit=False, error=str(exc)), indent=2))
        return 1
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
