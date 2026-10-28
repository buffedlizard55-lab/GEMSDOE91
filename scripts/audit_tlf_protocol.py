#!/usr/bin/env python3
"""Verification only: audit the frozen TLF download; never train or emit."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from gems91.novelty import dot_check, SurfaceProbe
from scripts.audit_downloads import inspect_raster


def audit():
    pins = json.loads((ROOT / 'registry/data_manifest.json').read_text())['files']
    arrays = {}
    for key in ('sample_submission', 'existing_faults'):
        row = next(r for r in pins if r['id'] == key)
        p = ROOT / 'data' / row['local_subpath']
        if hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('input pin drift')
        with rasterio.open(p) as ds:
            arrays[key] = ds.read(1)
            if key == 'sample_submission':
                grid = (ds.count, ds.shape, ds.crs, ds.transform)
    fp = np.isfinite(arrays['sample_submission'])
    cat = (arrays['existing_faults'] > 0) & fp
    p = ROOT / 'docs/downloads/gems91-s25-tlf-60000dots-20261028T120039Z-zeros.tif'
    data = p.read_bytes()
    expected = '21c11e819d2877787b698deef34d16a014bbbdf7de3551bfdf4f4e1de81f8b5f'
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('TLF artifact drift')
    with rasterio.open(p) as ds:
        a = ds.read(1)
    probe = SurfaceProbe(a, fp)
    rows, missing = [], []
    inventory = json.loads((ROOT / 'registry/comparison_inventory.json').read_text())['files']
    for r in inventory:
        ref = ROOT / r['path']
        if not ref.is_file():
            missing.append(r['path'])
            continue
        raw = ref.read_bytes()
        if hashlib.sha256(raw).hexdigest() != r['sha256'] or len(raw) != r['bytes']:
            raise ValueError('registry pin drift')
        with rasterio.open(ref) as ds:
            if (ds.count, ds.shape, ds.crs, ds.transform) != grid:
                raise ValueError('registry grid mismatch')
            b = np.where(fp, ds.read(1), 0)
        rows.append(dict(path=r['path'], sha256=r['sha256'],
                         **dot_check(a, b, fp), final_dot_rank=probe.compare(b)))
    return dict(scope='Frozen registry verification of existing TLF; not a geological experiment',
                raster_sha256=expected, validator_output=inspect_raster(data, grid, fp, cat),
                references_checked=len(rows), missing=missing,
                complete_registry=False, comparisons=rows,
                literal_pass=not missing and all(r['status'] == 'PASS' for r in rows),
                verdict='negative', ok_to_submit=False, experiments_used=0, slots_used=0,
                continuous_preplacement_surface_check='UNVERIFIED: original surface was not saved; final-dot ranks are not surface ranks',
                leaderboard_estimate=None)


if __name__ == '__main__':
    result = audit()
    out = ROOT / 'docs/s26/tlf-protocol-audit.json'
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(f"Verified {result['references_checked']} references; literal pass={result['literal_pass']}")
