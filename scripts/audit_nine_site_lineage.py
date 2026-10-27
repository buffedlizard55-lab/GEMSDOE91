#!/usr/bin/env python3
"""Recheck pixel-exact historical support relationships, not geological skill.

Uses SHA-256-pinned local mirror bytes and the already-frozen nine-site audit.
Does not fit a model, score a candidate, generate a TIFF or use a slot.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def audit(cache):
    source = json.loads((ROOT / 'docs/s22/nine-site-audit.json').read_text())
    references = {r['site']: r for r in source['sites']}
    data = {r['id']: r for r in json.loads((ROOT / 'registry/data_manifest.json').read_text())['files']}
    inputs = {}
    paths = {}
    for name in ('sample_submission', 'existing_faults'):
        row = data[name]
        path = ROOT / 'data' / row['local_subpath']
        if sha(path) != row['sha256']:
            raise ValueError('Pinned reference mismatch: ' + name)
        paths[name] = path
    with rasterio.open(paths['sample_submission']) as ds:
        shape, crs, transform = ds.shape, ds.crs, ds.transform
        footprint = np.isfinite(ds.read(1))
    with rasterio.open(paths['existing_faults']) as ds:
        if (ds.shape, ds.crs, ds.transform) != (shape, crs, transform):
            raise ValueError('Catalogue grid mismatch')
        cat = (ds.read(1) > 0) & footprint
    arrays = {}
    for site in ('GEMSDOE25', 'GEMSDOE30', 'GEMSDOE31', 'GEMSDOE32', 'GEMSDOE36'):
        paths_for_site = list(Path(cache).glob(site + '__*.tif'))
        if len(paths_for_site) != 1:
            raise ValueError('Need exactly one cached pinned raster: ' + site)
        path = paths_for_site[0]
        if sha(path) != references[site]['sha256']:
            raise ValueError('Historical raster hash mismatch: ' + site)
        with rasterio.open(path) as ds:
            if ds.count != 1 or (ds.shape, ds.crs, ds.transform) != (shape, crs, transform):
                raise ValueError('Historical raster grid mismatch: ' + site)
            values = ds.read(1)
        if not np.isfinite(values[footprint]).all() or not np.isin(values[footprint], (0, 1)).all():
            raise ValueError('Historical support is not finite binary in the footprint: ' + site)
        arrays[site] = (values > 0) & footprint
        inputs[site] = {'sha256': sha(path), 'positive_pixels': int(arrays[site].sum())}
    p25, p30, p31, p32, p36 = (arrays[f'GEMSDOE{i}'] for i in (25, 30, 31, 32, 36))
    dist = ndi.distance_transform_edt(~cat)

    def diff(a, b):
        d = a & ~b
        distances = dist[d]
        return {'pixels': int(d.sum()),
                'min_distance_to_catalogue_px': float(distances.min()) if distances.size else None,
                'max_distance_to_catalogue_px': float(distances.max()) if distances.size else None,
                'median_distance_to_catalogue_px': float(np.median(distances)) if distances.size else None}

    return {'schema': 'gems91.nine-site-lineage-audit.v1',
            'evidence_class': 'HISTORICAL_SUPPORT_GEOMETRY_NOT_A_SCORE',
            'input_provenance': 'hash-pinned community mirror; organizer origin not independently verified',
            'sample_sha256': data['sample_submission']['sha256'],
            'catalogue_sha256': data['existing_faults']['sha256'],
            'files': inputs,
            '25_and_30_identical_support': bool(np.array_equal(p25, p30)),
            '31_subset_of_25': bool(not (p31 & ~p25).any()),
            '32_subset_of_31': bool(not (p32 & ~p31).any()),
            '32_subset_of_36': bool(not (p32 & ~p36).any()),
            '25_minus_31': diff(p25, p31), '31_minus_32': diff(p31, p32),
            '36_minus_32': diff(p36, p32),
            'scope': 'Support relationships only; user-reported scores have no authenticated receipts and causal improvement is not established.',
            'geological_experiments_run': 0, 'candidate_generated': False,
            'competition_slots_used': 0, 'ok_to_submit': False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cache', type=Path, default=ROOT / 'data/nine_site_euclidean')
    ap.add_argument('--output', type=Path, default=ROOT / 'work/nine-site-lineage.json')
    args = ap.parse_args(argv)
    result = audit(args.cache)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
