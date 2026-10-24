#!/usr/bin/env python3
"""Verify the published research TIFF/ZIP from disk; never promotes a candidate.

Without sample/catalogue inputs, checks only pinned-grid format plus identity.
With --with-data, also verifies the pinned sample, footprint and catalogue.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from gems91.readiness import submission_ready
from vendor.gems57 import gates
from vendor.gems57.validate import validate


def published_path(relative):
    if not isinstance(relative, str): raise ValueError('artifact path must be a string')
    p = (ROOT / 'docs' / relative).resolve()
    if not p.is_relative_to((ROOT / 'docs/downloads').resolve()):
        raise ValueError('artifact path escapes the downloads directory')
    if not p.is_file(): raise FileNotFoundError(p)
    return p


def verify(with_data=False):
    card = json.loads((ROOT / 'docs/run-card.json').read_text())
    if card.get('submission_ready') is not submission_ready(card):
        raise ValueError('readiness flag contradicts shared policy')
    artifact = card.get('artifact')
    if artifact is None:
        if card.get('raster_sha256') is not None: raise ValueError('hash without an artifact')
        return dict(status='NO_ARTIFACT', submission_ready=False)
    path = published_path(artifact['file']); zipped = published_path(artifact['zip'])
    receipt_path = published_path(artifact['receipt'])
    receipt = json.loads(receipt_path.read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != card['raster_sha256'] or digest != receipt['sha256']:
        raise ValueError('advertised TIFF hash does not match bytes')
    if path.stat().st_size != artifact['bytes'] or path.stat().st_size != receipt['bytes']:
        raise ValueError('advertised TIFF byte count mismatch')
    if receipt['submission_name'] != card['submission_name'] or receipt['note'] != card['note']:
        raise ValueError('name/note drift between run card and file receipt')
    if not card['note'] or len(card['note']) > 140: raise ValueError('invalid short note')
    if not card['submission_name'] or len(card['submission_name']) > 140: raise ValueError('invalid name')
    if hashlib.sha256(zipped.read_bytes()).hexdigest() != receipt['zip_sha256']:
        raise ValueError('ZIP SHA256 mismatch')
    with zipfile.ZipFile(zipped) as z:
        if z.namelist() != [path.name] or z.read(path.name) != path.read_bytes():
            raise ValueError('ZIP must contain exactly the advertised TIFF, without extra files')
    fp = cat = None
    if with_data:
        paths = {'sample_submission': ROOT/'data/official/sample_submission.tif',
                 'existing_faults': ROOT/'data/official/existing_faults.tif'}
        for name, p in paths.items():
            pin = card['inputs'][name]
            if hashlib.sha256(p.read_bytes()).hexdigest() != pin['sha256'] or p.stat().st_size != pin['bytes']:
                raise ValueError(f'{name} input pin mismatch')
        with rasterio.open(paths['sample_submission']) as src: fp = np.isfinite(src.read(1))
        with rasterio.open(paths['existing_faults']) as src: cat = src.read(1)>0
    result = validate(path, footprint=fp, catalogue=cat)
    if not result['all_checks_passed']: raise ValueError(result['checks'])
    if result['emitted_positive_pixels'] != artifact['dots']: raise ValueError('dot count mismatch')
    if with_data:
        report = gates.format_report(path, paths['sample_submission'], footprint=fp)
        if not report['ok']: raise ValueError(report['problems'])
        if result['checks'] != card['validator_output']['checks']:
            raise ValueError('committed validation checks differ from actual re-validation')
    return dict(status='PASS', sha256=digest, bytes=path.stat().st_size,
                checks=result['checks'], scope='sample + footprint + catalogue' if with_data else 'identity + pinned grid + all-finite range',
                submission_ready=submission_ready(card),
                caveat='Format validation cannot override science, novelty or selector gates.')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--with-data', action='store_true')
    args = ap.parse_args(); print(json.dumps(verify(args.with_data), indent=2, allow_nan=False))


if __name__ == '__main__': main()
