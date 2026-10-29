#!/usr/bin/env python3
"""Recheck the historical S25 TIFF against nine pinned leaders and one witness.

This is an audit of an existing research artifact, not a model experiment,
release, organizer acceptance or registry-wide clearance. Restore the small
sample/catalogue mirrors, one lattice witness and nine leader blobs first.
The caller provides the independently generated nine-site report and cache.
No competition data or reference TIFFs are copied into the report.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT))
from gems91.novelty import SurfaceProbe, dot_check  # noqa: E402
from scripts.audit_downloads import inspect_raster  # noqa: E402
from scripts.verify_nine_site_leaders import LEADERS  # noqa: E402


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked(path: Path, expected: str, size: int | None = None) -> None:
    if not path.is_file() or digest(path) != expected or (size is not None and path.stat().st_size != size):
        raise ValueError(f'missing or hash/length-mismatched input: {path}')


def read_grid(path: Path, expected_grid=None):
    with rasterio.open(path) as src:
        actual = (src.count, src.shape, src.crs, src.transform)
        if expected_grid is not None and actual != expected_grid:
            raise ValueError(f'grid mismatch: {path}')
        return src.read(1), actual


def verify_leader_identity(site, row, old):
    """Bind the fresh diagnostic to the earlier byte-pinned leader identity."""
    if (row.get('sha256') != old.get('sha256') or row.get('blob_sha') != old.get('artifact_git_blob')
            or row.get('repo_path') != old.get('original_path') or row.get('footprint_checked') is not True
            or row.get('positive_outside_footprint') != 0):
        raise ValueError(f'{site}: report identity or footprint evidence differs from the frozen leader')


def compare(probe, candidate, reference, footprint):
    """Check literal final dot support and exact ranks within the same footprint."""
    rank = probe.compare(reference)
    dots = dot_check(candidate, reference, footprint)
    return {
        'rank_correlation': rank['rank_correlation'],
        'rank_status': rank['status'],
        'directed_overlap_within_3px': dots['overlap_within_3px'],
        'dot_status': dots['status'],
        'reference_dots_in_footprint': dots.get('registry_dots'),
        'reference_positive_outside_footprint': int(((reference > 0) & ~footprint).sum()),
    }


def audit(nine_report: Path, cache: Path):
    report = json.loads(nine_report.read_text())
    nine = report['files']
    if not all(site in nine for site in LEADERS):
        raise ValueError('nine-site report is incomplete')
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    inputs = {row['id']: row for row in manifest['files']}
    paths = {}
    for name in ('sample_submission', 'existing_faults'):
        row = inputs[name]
        paths[name] = ROOT / 'data' / row['local_subpath']
        checked(paths[name], row['sha256'], row['bytes'])
    if report.get('sample_sha256') != inputs['sample_submission']['sha256']:
        raise ValueError('nine-site report used a different or unverified sample')
    historic_sites = {row['site']: row for row in
                      json.loads((ROOT / 'docs/s22/nine-site-audit.json').read_text())['sites']}
    with rasterio.open(paths['sample_submission']) as src:
        grid = (src.count, src.shape, src.crs, src.transform)
        sample = src.read(1)
        footprint = np.isfinite(sample) & (src.read_masks(1) > 0)
    if not footprint.any():
        raise ValueError('empty sample footprint')
    catalogue, _ = read_grid(paths['existing_faults'], grid)
    catalogue = (catalogue > 0) & footprint
    sample_support = (sample > 0) & footprint
    sample_catalogue_mismatch = int(np.count_nonzero(sample_support ^ catalogue))

    card = json.loads((ROOT / 'docs/s25/run-card.json').read_text())
    if card['verdict'] != 'negative' or card['ok_to_submit'] is not False:
        raise ValueError('historical run card is not research-only')
    tif = ROOT / card['artifact']['tif']
    archive = ROOT / card['artifact']['zip']
    checked(tif, card['raster_sha256'])
    checked(archive, card['artifact']['zip_sha256'])
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError('ZIP is not a byte-identical single-TIFF archive')
    candidate, _ = read_grid(tif, grid)
    validation = inspect_raster(tif.read_bytes(), grid, footprint, catalogue)
    if validation['status'] != 'PASS':
        raise ValueError(f'historical TIFF failed local technical checks: {validation["checks"]}')
    probe = SurfaceProbe(candidate, footprint)
    if not probe.valid:
        raise ValueError('constant historical candidate is unverified')

    references = []
    for site in LEADERS:
        row, old = nine[site], historic_sites[site]
        verify_leader_identity(site, row, old)
        path = cache / f"{site}__{Path(row['repo_path']).name}"
        checked(path, row['sha256'])
        references.append((site, path, row['sha256']))
    inventory = json.loads((ROOT / 'registry/comparison_inventory.json').read_text())['files']
    witness = next(x for x in inventory if x['path'] == 'data/fleet_registry/calib_r13lattice_00904.tif')
    wpath = ROOT / witness['path']
    checked(wpath, witness['sha256'], witness['bytes'])
    references.append(('frozen lattice', wpath, witness['sha256']))

    comparisons = {}
    stopped_at = None
    for index, (label, path, sha) in enumerate(references):
        ref, _ = read_grid(path, grid)
        if not np.isfinite(ref[footprint]).all() or not np.isin(ref[footprint], [0, 1]).all():
            raise ValueError(f'{label}: non-finite or nonbinary values inside footprint')
        result = compare(probe, candidate, ref, footprint)
        if result['reference_positive_outside_footprint']:
            raise ValueError(f'{label}: positive support outside footprint')
        result['sha256'] = sha
        comparisons[label] = result
        print(f"{label}: {result['dot_status']} overlap={result['directed_overlap_within_3px']:.6f}", flush=True)
        if result['dot_status'] != 'PASS' or result['rank_status'] != 'PASS':
            stopped_at = label
            break  # literal duplicate/undefined stop: never continue to seek a pass
    not_checked = [label for label, _, _ in references[len(comparisons):]]

    return {
        'schema': 'gems91.priority-snapshot-recheck.v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'implementation_sha256': digest(Path(__file__)),
        'scope': 'Existing S25 research TIFF vs nine leader TIFFs and one selected witness only; no experiment or slot.',
        'reference_provenance': 'SHA-pinned owner GitHub mirrors; not authenticated organizer files or proof of redistribution rights.',
        'sample_sha256': inputs['sample_submission']['sha256'],
        'catalogue_sha256': inputs['existing_faults']['sha256'],
        'sample_semantics': {
            'positive_inside_footprint': int(sample_support.sum()),
            'catalogue_positive_inside_footprint': int(catalogue.sum()),
            'positive_support_mismatch_pixels': sample_catalogue_mismatch,
            'note': 'The public description says its sample predicts total fault absence. A positive mirrored sample is not authenticated as that template.',
        },
        'nine_site_report_sha256': digest(nine_report),
        'raster': {'path': card['artifact']['tif'], 'sha256': card['raster_sha256'],
                   'zip': card['artifact']['zip'], 'zip_sha256': card['artifact']['zip_sha256'],
                   'submission_name': card['submission_name'], 'note': card['submission_note'],
                   'candidate_dots_in_footprint': int(((candidate > 0) & footprint).sum()),
                   'positive_outside_footprint': int(((candidate > 0) & ~footprint).sum()),
                   'outside_sample_footprint_values': 'all zeros; not a demonstration of organizer acceptance'},
        'validator_output': validation,
        'comparisons': comparisons,
        'stopped_at': stopped_at,
        'not_checked_after_stop': not_checked,
        'preplacement_surface_rechecked': False,
        'preplacement_note': 'Final-dot ranks cannot reconstruct or validate the original pre-placement surface.',
        'complete_registry_check': False,
        'geological_experiments': 0,
        'weekly_submission_slots_used': 0,
        'ok_to_submit': False,
        'verdict': 'negative',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nine-report', type=Path, required=True)
    p.add_argument('--cache', type=Path, default=ROOT / 'data/nine_site_leaders')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = audit(args.nine_report, args.cache)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
