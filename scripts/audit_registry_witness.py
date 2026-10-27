#!/usr/bin/env python3
"""Compare an existing binary TIFF to one pinned registry witness.

This is an immutable-artifact audit, not a model run and not a complete registry
clearance. Exit 1 on a duplicate, missing input, mismatched grid, or ambiguity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from gems91.novelty import SurfaceProbe, dot_check  # noqa: E402
from scripts.experiment_preflight import pinned_path  # noqa: E402

WITNESS = 'data/fleet_registry/calib_r13lattice_00904.tif'


def audit(candidate: Path, root: Path = ROOT) -> dict:
    manifest = json.loads((root / 'registry/data_manifest.json').read_text())
    row = next(r for r in manifest['files'] if r['id'] == 'sample_submission')
    sample = pinned_path(root, 'data/' + row['local_subpath'], row['sha256'], row['bytes'])
    refs = json.loads((root / 'registry/comparison_inventory.json').read_text())['files']
    matches = [r for r in refs if r['path'] == WITNESS]
    if len(matches) != 1:
        raise ValueError('witness must be unique in pinned inventory')
    ref_row = matches[0]
    reference = pinned_path(root, WITNESS, ref_row['sha256'], ref_row['bytes'])
    candidate = candidate.resolve()
    if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
        raise ValueError('candidate must be a file within the repository')
    with rasterio.open(sample) as src:
        grid = (src.shape, src.crs, src.transform)
        fp = np.isfinite(src.read(1)) & (src.read_masks(1) != 0)
    arrays = []
    for path in (candidate, reference):
        with rasterio.open(path) as src:
            if src.count != 1 or (src.shape, src.crs, src.transform) != grid:
                raise ValueError(f'grid mismatch: {path.name}')
            values = src.read(1)
        if not np.isfinite(values[fp]).all() or np.any((values[fp] < 0) | (values[fp] > 1)):
            raise ValueError(f'nonfinite or out-of-range in-footprint values: {path.name}')
        arrays.append(np.where(fp, values, 0).astype(np.float32))
    pred, ref = arrays
    overlap = dot_check(pred, ref, fp)
    rho = SurfaceProbe(pred, fp).compare(ref)
    duplicate = overlap['status'] == 'DUPLICATE' or rho['status'] == 'DUPLICATE'
    verified = overlap['status'] != 'UNVERIFIED' and rho['status'] != 'UNVERIFIED'
    return {
        'schema': 'gems91.registry-witness-audit.v1',
        'candidate_path': str(candidate.relative_to(root.resolve())),
        'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
        'witness_path': WITNESS, 'witness_sha256': ref_row['sha256'],
        'witness_source_url': ref_row.get('source_url'),
        'sample_sha256': row['sha256'],
        'surface_correlation': rho,
        'directed_dot_overlap': overlap,
        'status': 'DUPLICATE_STOP' if duplicate else ('ONE_WITNESS_PASS' if verified else 'UNVERIFIED'),
        'complete_registry_clearance': False,
        'geological_experiments_run': 0,
        'scope': 'One pinned witness only. Does not compare a pre-placement surface or establish complete registry uniqueness.',
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('candidate', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args(argv)
    try:
        result = audit(args.candidate)
    except (OSError, ValueError, KeyError, StopIteration, rasterio.errors.RasterioError) as exc:
        result = {'schema': 'gems91.registry-witness-audit.v1', 'status': 'BLOCKED', 'error': str(exc),
                  'complete_registry_clearance': False, 'geological_experiments_run': 0}
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if result['status'] == 'ONE_WITNESS_PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
