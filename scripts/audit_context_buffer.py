#!/usr/bin/env python3
"""Compare historical and corrected shared fold *geometry*, not model scores.

This diagnostic reads only hash-pinned sample/catalogue masks and archived
source. It never constructs geological features, places dots, spends a slot,
or claims organizer-origin authentication for the community-mirrored inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import runpy
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.source_integrity import verify_historical_source  # noqa: E402
from vendor.gems57 import grid, spatial  # noqa: E402


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def audit(root: Path = ROOT, buffer_px: int = 80) -> dict:
    root = root.resolve()
    if type(buffer_px) is not int or buffer_px < 0:
        raise ValueError('buffer_px must be a non-negative integer')
    manifest = json.loads((root / 'registry/data_manifest.json').read_text())
    by_id = {row['id']: row for row in manifest['files']}
    inputs = {}
    for key in ('sample_submission', 'existing_faults'):
        row = by_id[key]
        path = (root / 'data' / row['local_subpath']).resolve()
        if not path.is_relative_to((root / 'data').resolve()):
            raise ValueError('input path escapes data directory')
        digest = sha(path)
        if path.stat().st_size != row['bytes'] or digest != row['sha256']:
            raise ValueError(f'pinned input mismatch: {key}')
        inputs[key] = digest
    pin = json.loads((root / 'registry/template_pin.json').read_text())
    old_digest = pin['upstream_sha256']['spatial.py']
    verify_historical_source(root, 'vendor/gems57/spatial.py', old_digest)
    archived = (root / pin['historical_archives']['spatial.py']).resolve()
    old_folds = runpy.run_path(str(archived))['folds']
    g = grid.load_grid(root / 'data/official')
    rows = []
    for old, new in zip(old_folds(g.catalogue, g.footprint, buffer_px),
                        spatial.folds(g.catalogue, g.footprint, buffer_px), strict=True):
        if old['fold'] != new['fold'] or not all(
            np.array_equal(old[key], new[key]) for key in ('truth', 'held_all', 'region', 'train')
        ):
            raise ValueError('historical and corrected fold geometry unexpectedly differs')
        if not np.array_equal(new['masked_known'], g.catalogue & ~new['held_all']):
            raise ValueError('known-pixel scoring mask drift')
        if (new['visible'] & ~old['visible']).any():
            raise ValueError('corrected context unexpectedly adds visible catalogue')
        if old['visible'].any() and old['truth'].any():
            distance = ndi.distance_transform_edt(~old['visible'])[old['truth']]
            historical_min = float(distance.min())
            within3, within_buffer = int((distance <= 3).sum()), int((distance <= buffer_px).sum())
        else:
            historical_min = None
            within3 = within_buffer = 0
        r = new['receipt']
        nearest_new = r['nearest_visible_to_held_px']
        if nearest_new is not None and nearest_new <= buffer_px:
            raise ValueError('corrected feature-context buffer violated')
        rows.append({
            'fold': int(new['fold']),
            'withheld_positive_pixels_in_quadrant': int(new['truth'].sum()),
            'historical_nearest_visible_to_truth_px': historical_min,
            'historical_withheld_pixels_with_visible_within_3px': within3,
            'historical_withheld_pixels_with_visible_within_buffer': within_buffer,
            'known_catalogue_pixels_removed_from_feature_context': r['feature_context_catalogue_pixels_removed'],
            'corrected_nearest_visible_to_any_held_component_px': nearest_new,
            'corrected_known_pixel_mask_preserved': True,
            'evaluation_geometry_unchanged': True,
        })
    if len(rows) != 4:
        raise ValueError('expected exactly four quadrants')
    return {
        'schema': 'gems91.feature-context-buffer-audit.v1',
        'status': 'HISTORICAL_FEATURE_CONTEXT_UNBUFFERED_CORRECTED_IN_SHARED_TEMPLATE',
        'evidence_class': 'MASK_GEOMETRY_DIAGNOSTIC_NOT_A_SCORE',
        'geological_experiments_run': 0,
        'competition_slots_used': 0,
        'buffer_px': buffer_px,
        'input_sha256': inputs,
        'input_provenance': 'hash-pinned community mirrors; not independently authenticated organizer downloads',
        'historical_spatial_sha256': old_digest,
        'corrected_spatial_sha256': pin['sha256']['spatial.py'],
        'historical_split_version': 'label-blind-quadrants-v2',
        'corrected_split_version': 'label-blind-quadrants-v3-feature-buffered',
        'rows': rows,
        'interpretation': 'Training buffer existed, but visible catalogue context was not buffered. Proximity alone is not proof of leakage or a measured change in DTI. Context-dependent historical results are not matched to the corrected split.',
        'candidate_generated': False,
        'ok_to_submit': False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'work/context-buffer-audit.json')
    args = parser.parse_args(argv)
    try:
        report = audit()
        text = json.dumps(report, indent=2, allow_nan=False) + '\n'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
        print(text, end='')
        return 0
    except (OSError, ValueError, KeyError, ImportError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'ok_to_submit': False, 'error': str(exc)}, indent=2))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
