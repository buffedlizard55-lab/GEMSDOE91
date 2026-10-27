#!/usr/bin/env python3
"""Audit raster feature coverage using GDAL masks, not ``isfinite`` alone.

A finite NoData sentinel is not a measurement.  This command is a preflight:
missing interior data is reported and results in a nonzero exit, rather than
silently filled or used for feature calculations. It never runs an experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES = ROOT / 'data/bridge/gems-geodawn-numerical-features.tif'
DEFAULT_SAMPLE = ROOT / 'data/official/sample_submission.tif'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def audit(features: Path, sample: Path, bands: list[int]) -> dict:
    if not bands or len(set(bands)) != len(bands) or any(type(b) is not int or b < 1 for b in bands):
        raise ValueError('bands must be unique positive integers')
    with rasterio.open(sample) as template:
        if template.count != 1 or template.crs is None:
            raise ValueError('sample must be a georeferenced single-band raster')
        template_grid = (template.shape, template.crs, template.transform)
        sample_values = template.read(1)
        fp = np.isfinite(sample_values) & (template.read_masks(1) != 0)
    if not fp.any():
        raise ValueError('empty sample footprint')
    rows = []
    with rasterio.open(features) as src:
        if (src.shape, src.crs, src.transform) != template_grid:
            raise ValueError('feature raster grid does not match sample')
        if max(bands) > src.count:
            raise ValueError('requested feature band does not exist')
        for band in bands:
            values = src.read(band)
            mask_valid = src.read_masks(band) != 0
            finite = np.isfinite(values)
            missing = fp & ~(mask_valid & finite)
            # Detect the conventional float32-min sentinel even if a broken
            # file forgot to declare it as NoData in its GDAL metadata.
            extreme = fp & finite & (np.abs(values.astype(np.float64)) >= 1e30)
            usable = fp & mask_valid & finite & ~extreme
            n = int(usable.sum())
            rows.append({
                'band': band,
                'description': src.descriptions[band - 1],
                'footprint_pixels': int(fp.sum()),
                'masked_or_nonfinite_inside': int(missing.sum()),
                'finite_extreme_inside': int(extreme.sum()),
                'usable_pixels': n,
                'usable_min': float(values[usable].min()) if n else None,
                'usable_max': float(values[usable].max()) if n else None,
                'status': 'PASS' if not missing.any() and not extreme.any() else 'FAIL_CLOSED',
            })
        nodata = src.nodata
        nodata_repr = repr(nodata)
    good = all(r['status'] == 'PASS' for r in rows)
    def display_path(path: Path) -> str:
        resolved = path.resolve()
        return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(resolved)
    return {
        'schema': 'gems91.feature-nodata-audit.v1',
        'status': 'PASS' if good else 'FAIL_CLOSED',
        'is_geological_experiment': False,
        'features_path': display_path(features), 'features_sha256': sha256(features),
        'sample_path': display_path(sample), 'sample_sha256': sha256(sample),
        'nodata_tag_repr': nodata_repr,
        'grid_matches_sample': True,
        'bands': rows,
        'limitation': 'Metadata masks and extreme-value checks cannot detect every undocumented missing-value code or authenticate a mirror.',
    }


def verify_default_pins(features: Path, sample: Path) -> None:
    rows = {r['id']: r for r in json.loads((ROOT / 'registry/data_manifest.json').read_text())['files']}
    for name, path in [('training_features', features), ('sample_submission', sample)]:
        row = rows[name]
        if sha256(path) != row['sha256'] or path.stat().st_size != row['bytes']:
            raise ValueError(f'{name}: pinned SHA256/size mismatch')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, default=DEFAULT_FEATURES)
    parser.add_argument('--sample', type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument('--bands', type=int, nargs='+', default=[13, 14])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--allow-unpinned', action='store_true',
                        help='Explicitly permit non-pinned diagnostic inputs; never a promotion check')
    args = parser.parse_args(argv)
    try:
        if not args.allow_unpinned:
            verify_default_pins(args.features, args.sample)
        report = audit(args.features, args.sample, args.bands)
    except (OSError, ValueError, KeyError, rasterio.errors.RasterioError) as exc:
        report = {'schema': 'gems91.feature-nodata-audit.v1', 'status': 'BLOCKED',
                  'is_geological_experiment': False, 'error': str(exc)}
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
