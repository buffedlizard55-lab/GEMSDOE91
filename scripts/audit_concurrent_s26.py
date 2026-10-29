#!/usr/bin/env python3
"""Reread concurrent S26 research artifacts against a pinned lattice witness.

No experiments, placement or score estimation. Stop each file at its first
lattice duplicate. Footprint evidence is conditional on the mirrored sample,
whose origin is not authenticated and whose semantics are in conflict.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from gems91.novelty import SurfaceProbe
from scripts.audit_priority_snapshot import checked, compare, digest, inspect_raster, read_grid

FILES = (
    'gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros',
    'gems91-s26-fabric-emit-10pxcap-22163dots-20261029T143240Z-e7724d8c-zeros',
    'gems91-s26-fabric-emit-10pxcap-37654dots-20261029T143324Z-28228279-zeros',
)
WITNESS = 'data/fleet_registry/calib_r13lattice_00904.tif'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=ROOT / 'docs/review-4239f6e5/concurrent-s26-audit.json')
    args = ap.parse_args()
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    inputs = {row['id']: row for row in manifest['files']}
    paths = {}
    for name in ('sample_submission', 'existing_faults'):
        row = inputs[name]
        paths[name] = ROOT / 'data' / row['local_subpath']
        checked(paths[name], row['sha256'], row['bytes'])
    witness_row = next(row for row in json.loads((ROOT / 'registry/comparison_inventory.json').read_text())['files']
                       if row['path'] == WITNESS)
    witness = ROOT / WITNESS
    checked(witness, witness_row['sha256'], witness_row['bytes'])
    with rasterio.open(paths['sample_submission']) as ds:
        footprint = np.isfinite(ds.read(1)) & (ds.read_masks(1) > 0)
        grid = (ds.count, ds.shape, ds.crs, ds.transform)
    if not footprint.any():
        raise ValueError('empty sample footprint')
    raw_catalogue, _ = read_grid(paths['existing_faults'], grid)
    catalogue = (raw_catalogue > 0) & footprint
    lattice, _ = read_grid(witness, grid)
    if not np.isfinite(lattice[footprint]).all() or not np.isin(lattice[footprint], [0, 1]).all():
        raise ValueError('lattice contains nonbinary or nonfinite cells in footprint')
    rows = []
    for stem in FILES:
        tif = ROOT / 'docs/downloads' / (stem + '.tif')
        zip_path = tif.with_suffix('.zip')
        sidecar = json.loads(tif.with_suffix('.json').read_text())
        if sidecar['file'] != tif.name or sidecar['zip_file'] != zip_path.name:
            raise ValueError(f'{stem}: sidecar path mismatch')
        checked(tif, sidecar['sha256'], sidecar['bytes'])
        checked(zip_path, sidecar['zip_sha256'])
        with zipfile.ZipFile(zip_path) as archive:
            members = archive.namelist()
            if len(members) != 1 or members[0] != tif.name or archive.read(members[0]) != tif.read_bytes():
                raise ValueError(f'{stem}: ZIP does not contain exactly the same TIFF bytes')
        validation = inspect_raster(tif.read_bytes(), grid, footprint, catalogue)
        if validation['status'] != 'PASS':
            raise ValueError(f'{stem}: local technical validation failed')
        candidate, _ = read_grid(tif, grid)
        result = compare(SurfaceProbe(candidate, footprint), candidate, lattice, footprint)
        if result['reference_positive_outside_footprint'] or ((candidate > 0) & ~footprint).any():
            raise ValueError(f'{stem}: positive support outside mirrored footprint')
        rows.append({
            'name': stem, 'tif': str(tif.relative_to(ROOT)), 'tif_sha256': digest(tif),
            'zip': str(zip_path.relative_to(ROOT)), 'zip_sha256': digest(zip_path),
            'candidate_dots': int(((candidate > 0) & footprint).sum()),
            'validator_output': validation,
            'witness': WITNESS, 'witness_sha256': witness_row['sha256'],
            'final_dot_comparison': result,
            'surface_before_placement': 'NOT_RECHECKED',
            'other_references_after_witness': 'NOT_CHECKED (stop at first duplicate)',
            'submission_ready': False,
        })
        print(f'{stem}: {result["dot_status"]} lattice overlap={result["directed_overlap_within_3px"]:.6f}')
        if result['dot_status'] != 'DUPLICATE':
            raise ValueError(f'{stem}: expected first duplicate not observed; re-evaluate report, do not promote')
    report = {
        'schema': 'gems91.concurrent-s26-lattice-recheck.v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'source_main_commit': '740ca18cf426e5098814f2c1d9aaa7d0dc7c5b7f',
        'implementation_sha256': digest(Path(__file__)),
        'shared_audit_sha256': digest(ROOT / 'scripts/audit_priority_snapshot.py'),
        'validator_implementation_sha256': digest(ROOT / 'scripts/audit_downloads.py'),
        'scope': 'Three already-existing research artifacts from concurrent merges; no new experiment or slot.',
        'sample_sha256': inputs['sample_submission']['sha256'],
        'catalogue_sha256': inputs['existing_faults']['sha256'],
        'qualification': 'Mirrored sample is not authenticated and conflicts with the public sample description; local checks do not establish server acceptance. Outside is zero, not organizer-specified null/NaN.',
        'results': rows,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
