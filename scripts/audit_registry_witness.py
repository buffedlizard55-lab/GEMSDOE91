#!/usr/bin/env python3
"""Audit existing TIFFs against one pinned registry witness; never build or submit.

Restores are separate. This is a negative witness, not a complete registry scan
or a geological experiment. Inputs must match the existing SHA/size manifest.

    python scripts/restore_data.py --only sample_submission,existing_faults,parent_r0_zeros,anc_d2_8,anc_solo_d2_8
    # Restore the lattice blob and optional KPL36 file as described in the review.
    python scripts/audit_registry_witness.py --output work/witness-audit.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt
from gems91.capacity import capacity_bound
from gems91.novelty import SurfaceProbe, dot_check, combine_final_checks
from scripts.audit_downloads import inspect_raster


S18 = 'docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261026T213155Z-29db2405.tif'
S18_OLD = 'docs/downloads/gems91-S18-UNIQUE-curvtilt-20000dots-20261025T182858Z-29db2405.tif'
OMTJ = 'docs/downloads/gems91-s22-omtj-e1-20261026-a99b8923f0-zeros.tif'
KPL = 'data/KPL36_20261026.tif'
KPL_SHA = '86fc8243ad573bcdbfac8b432daf0ec5b6800b991b2c3278706358be7eb9922d'
WITNESS = 'data/fleet_registry/calib_r13lattice_00904.tif'


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def pinned(root: Path, relative: str, digest: str, size: int | None = None) -> Path:
    p = (root / relative).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():
        raise ValueError(f'missing or unsafe pinned input: {relative}')
    if (size is not None and p.stat().st_size != size) or file_sha(p) != digest:
        raise ValueError(f'pin mismatch: {relative}')
    return p


def run(root: Path = ROOT, include_kpl: bool = False) -> dict:
    rows = {x['id']: x for x in json.loads((root / 'registry/data_manifest.json').read_text())['files']}
    refs = {k: pinned(root, 'data/' + rows[k]['local_subpath'], rows[k]['sha256'], rows[k]['bytes'])
            for k in ('sample_submission', 'existing_faults', 'parent_r0_zeros', 'anc_d2_8', 'anc_solo_d2_8')}
    inv_path = root / 'registry/comparison_inventory.json'
    inv = json.loads(inv_path.read_text())
    witnesses = [x for x in inv['files'] if x['path'] == WITNESS]
    if len(witnesses) != 1:
        raise ValueError('lattice witness must occur exactly once in frozen inventory')
    witness = witnesses[0]
    wpath = pinned(root, WITNESS, witness['sha256'], witness['bytes'])

    with rasterio.open(refs['sample_submission']) as s:
        template = (s.count, s.shape, s.crs, s.transform)
        sample = s.read(1)
        footprint = np.isfinite(sample) & (s.read_masks(1) > 0)
    with rasterio.open(refs['existing_faults']) as s:
        if (s.count, s.shape, s.crs, s.transform) != template:
            raise ValueError('sample/catalogue grid mismatch')
        catalogue = (s.read(1) > 0) & footprint
    with rasterio.open(wpath) as s:
        if (s.count, s.shape, s.crs, s.transform) != template:
            raise ValueError('lattice grid mismatch')
        reference = s.read(1)
    if not np.isfinite(reference[footprint]).all() or not np.isin(reference[footprint], [0, 1]).all():
        raise ValueError('lattice must be binary and finite inside footprint')
    # This frozen witness has NaN outside its footprint. Keep every valid
    # positive cell on the whole grid, consistent with the capacity preflight.
    reference_dots = np.isfinite(reference) & (reference > 0)
    if np.any(reference_dots & ~footprint):
        raise ValueError('witness has outside-footprint positives; shared dot-check scope needs review')

    candidates = [('s18_current', S18, 'af01bc7190ce736d2ea7eb28a6e0b9ccd238dd616f41644ba4d8bc5a4f892bb6'),
                  ('omtj', OMTJ, 'f12f03a27585b1a9c89108970775d7b44e532c3238a8f387552f1103d7317042')]
    if include_kpl:
        candidates.append(('gems36_kpl', KPL, KPL_SHA))
    results = {}
    for label, relative, expected in candidates:
        path = pinned(root, relative, expected)
        raster_bytes = path.read_bytes()
        validation = inspect_raster(raster_bytes, template, footprint, catalogue)
        if validation['status'] != 'PASS':
            raise ValueError(f'{label} is not locally range/grid valid: {validation["checks"]}')
        with rasterio.open(path) as s:
            prediction = s.read(1)
        # The metric here is rank/overlap, not a holdout or leaderboard score.
        rank = SurfaceProbe(prediction, footprint).compare(reference)
        dots = dot_check(prediction, reference, footprint)
        verdict = combine_final_checks(rank, dots)
        z = None
        if label != 'gems36_kpl':
            zip_path = path.with_suffix('.zip')
            with zipfile.ZipFile(zip_path) as archive:
                z = {'sha256': file_sha(zip_path), 'single_tiff_identical':
                     archive.namelist() == [path.name] and archive.read(path.name) == raster_bytes}
            if not z['single_tiff_identical']:
                raise ValueError(f'{label} ZIP does not match TIFF')
        results[label] = {'path': relative, 'sha256': expected, 'validator': validation,
                          'final_rank': rank, 'final_dots': dots, 'final_verdict': verdict,
                          'zip': z, 'ok_to_submit': False}
        if label == 'gems36_kpl':
            results[label]['source'] = {
                'original_filename': 'gemsdoe36-kpl36-exp3-20261026-fc869911e88c-zeros.tif',
                'git_blob': '933a7a65eab0193e806f86d24c07f7af96bfbe03',
                'owner_page': 'https://buffedlizard55-lab.github.io/GEMSDOE36/docs/',
            }

    old_path = pinned(root, S18_OLD, results['s18_current']['sha256'])
    alias = {'previous_path': S18_OLD, 'current_path': S18,
             'previous_sha256': file_sha(old_path),
             'byte_identical': old_path.read_bytes() == (root / S18).read_bytes(),
             'conclusion': 'Different names do not make new prediction bytes.'}
    if not alias['byte_identical']:
        raise ValueError('Unexpected S18 historical-alias drift')

    support = {}
    for key in ('anc_d2_8', 'anc_solo_d2_8', 'parent_r0_zeros'):
        with rasterio.open(refs[key]) as src:
            if (src.count, src.shape, src.crs, src.transform) != template:
                raise ValueError('forensic reference grid mismatch: ' + key)
            support[key] = (src.read(1) > 0) & footprint
    a, b, c = (support[k] for k in ('anc_d2_8', 'anc_solo_d2_8', 'parent_r0_zeros'))
    distance = distance_transform_edt(~catalogue)
    ab, bc = a & ~b, b & ~c
    lineage = {'d28_dots': int(a.sum()), 'h27_dots': int(b.sum()), 'r0_dots': int(c.sum()),
               'h27_is_d28_subset': bool(np.all(~b | a)), 'r0_is_h27_subset': bool(np.all(~c | b)),
               'd28_minus_h27': int(ab.sum()), 'd28_minus_h27_within_1px': int((ab & (distance <= 1)).sum()),
               'h27_minus_r0': int(bc.sum()),
               'h27_minus_r0_between_1_and_2px': int((bc & (distance > 1) & (distance <= 2)).sum()),
               'interpretation': 'Exact mask nesting only; the hidden truth and the cause of a reported score remain unknown.'}
    return {
        'schema': 'gems91.registry-witness-audit.v1',
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Existing artifacts only; one witness is enough to disprove uniqueness, never to prove it.',
        'references': {'sample_sha256': rows['sample_submission']['sha256'],
                       'catalogue_sha256': rows['existing_faults']['sha256'],
                       'witness_path': WITNESS, 'witness_sha256': witness['sha256'],
                       'witness_source_url': witness['source_url'],
                       'inventory_sha256': file_sha(inv_path), 'organizer_complete_registry': False},
        'sample_provenance_irregularity': {
            'sample_positive_pixels': int(((sample > 0) & footprint).sum()),
            'catalogue_positive_pixels': int(catalogue.sum()),
            'sample_positive_support_equals_catalogue': bool(np.array_equal((sample > 0) & footprint, catalogue)),
            'reason': 'Pinned mirror has positive sample values although official page describes total fault absence; organizer origin unverified.'},
        'capacity_37654': capacity_bound(footprint, reference_dots, 37654),
        'capacity_20000': capacity_bound(footprint, reference_dots, 20000),
        'existing_candidates': results,
        's18_alias': alias,
        'r0_lineage': lineage,
        'new_experiments': 0, 'new_tiff_created': False, 'weekly_slots_used': 0,
        'leaderboard_estimate': None, 'organizer_confirmed_score': None,
        'ok_to_submit': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-kpl', action='store_true', help='Also check the separately restored, pinned GEMSDOE36 KPL TIFF')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        report = run(include_kpl=args.include_kpl)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps({'status': 'BLOCKED', 'ok_to_submit': False, 'error': str(exc)}))
        return 1
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
