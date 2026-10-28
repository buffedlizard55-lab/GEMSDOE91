#!/usr/bin/env python3
"""Recheck S25-TLF delivery bytes without selecting or uploading a submission.

Archived scientific measurements are attributed, not silently rerun. Missing
sample/catalogue and full registry mean submission readiness is unverified.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def audit(root=ROOT):
    import numpy as np
    import rasterio
    card = json.loads((root / 'docs/s25-tlf/run-card.json').read_text())
    artifact = card['artifact']
    tif = root / artifact['tif']
    checks = {}
    errors = []
    try:
        checks['tif_sha256'] = hashlib.sha256(tif.read_bytes()).hexdigest() == artifact['sha256']
        with rasterio.open(tif) as src:
            a = src.read(1)
            checks.update(single_band=src.count == 1, float32=src.dtypes == ('float32',),
                          crs=str(src.crs) == 'EPSG:32611', shape=src.shape == (3730, 3292),
                          transform=tuple(src.transform)[:6] == (100., 0., 243350., 0., -100., 4508550.),
                          no_nan_or_inf=bool(np.isfinite(a).all()),
                          range_0_1=bool(np.isfinite(a).all() and a.min() >= 0 and a.max() <= 1),
                          dots=int((a > 0).sum()) == card['emission']['dots'])
        zpath = root / artifact['zip']
        checks['zip_sha256'] = hashlib.sha256(zpath.read_bytes()).hexdigest() == artifact['zip_sha256']
        with zipfile.ZipFile(zpath) as z:
            checks['zip_single_exact_tif'] = z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes()
    except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
        errors.append(str(exc))
    reference = {'status': 'NOT_CHECKED'}
    try:
        from scripts.audit_downloads import inspect_raster
        from scripts.experiment_preflight import pinned_path
        manifest = json.loads((root / 'registry/data_manifest.json').read_text())
        paths = {}
        for key in ('sample_submission', 'existing_faults'):
            row = next(r for r in manifest['files'] if r['id'] == key)
            paths[key] = pinned_path(root, 'data/' + row['local_subpath'], row['sha256'], row['bytes'])
        with rasterio.open(paths['sample_submission']) as src:
            grid = (src.count, src.shape, src.crs, src.transform)
            footprint = np.isfinite(src.read(1)) & (src.read_masks(1) > 0)
        with rasterio.open(paths['existing_faults']) as src:
            if (src.count, src.shape, src.crs, src.transform) != grid:
                raise ValueError('Pinned catalogue grid mismatch')
            catalogue = (src.read(1) > 0) & footprint
        reference = inspect_raster(tif.read_bytes(), grid, footprint, catalogue)
        checks['shared_reference_validator'] = all(reference['checks'].values())
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        reference = {'status': 'NOT_CHECKED', 'error': str(exc)}
    return {
        'schema': 'gems91.tlf-release-review.v1',
        'format_ok': bool(checks) and all(checks.values()) and not errors,
        'checks': checks, 'errors': errors,
        'reference_comparison': reference,
        'full_registry_uniqueness': 'UNVERIFIED: only nine leaders and local downloads were checked historically',
        'surface_rank_method': 'INVALID FOR TIES: historical double argsort ranks ties by pixel order; not Spearman midranks',
        'holdout_best_gate': 'NOT PASSED: review explicitly reports 0.120456 below historical best 0.2678; matched rerun required',
        'estimated_leaderboard_score': None,
        'organizer_confirmed_score': None,
        'ok_to_submit': False,
        'verdict': 'negative',
        'reason': 'Format integrity is not full-registry uniqueness, holdout-best improvement, or selector approval.',
    }


def main():
    result = audit()
    out = ROOT / 'docs/review-de9d7d75/delivery-audit.json'
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['format_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
