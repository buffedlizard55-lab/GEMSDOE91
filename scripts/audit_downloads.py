#!/usr/bin/env python3
"""Inspect every registered download against pinned local references; never promote.

Exit 0 means the audit completed, NOT that all historical artifacts are valid.
Exit 1 means missing/untrusted references or an incomplete inventory. Invalid
legacy downloads stay visible in the report rather than being silently repaired.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
from rasterio.io import MemoryFile

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def inspect_raster(data, reference, footprint, catalogue):
    with MemoryFile(data) as mem, mem.open() as src:
        grid = (src.count, src.shape, src.crs, src.transform)
        same_grid = grid == reference
        checks = {'single_band': src.count == 1,
                  'crs_shape_transform_match': same_grid,
                  'no_nodata_tag': src.nodata is None}
        values = src.read(1)
        finite = np.isfinite(values)
        checks['all_cells_finite'] = bool(finite.all())
        checks['values_in_0_1'] = bool((finite & (values >= 0) & (values <= 1)).all())
        # Do not index with a footprint from a different grid.
        checks['no_nan_inside_footprint'] = bool(finite[footprint].all()) if same_grid else False
        checks['zero_outside_footprint'] = bool((values[~footprint] == 0).all()) if same_grid else False
        checks['visible_catalogue_masked'] = bool((values[catalogue] == 0).all()) if same_grid else False
        return {'status': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
                'nonfinite_cells': int((~finite).sum()),
                'out_of_range_finite_cells': int((finite & ((values < 0) | (values > 1))).sum()),
                'ok_to_submit': False,
                'reason': 'Technical inspection only; no scientific, uniqueness or selector approval.'}


def audit(root=ROOT):
    manifest = json.loads((root / 'registry/data_manifest.json').read_text())
    rows = {r['id']: r for r in manifest['files']}
    paths = {}
    for key in ('sample_submission', 'existing_faults'):
        row = rows[key]
        path = root / 'data' / row['local_subpath']
        if digest(path.read_bytes()) != row['sha256']:
            raise ValueError(f'Untrusted reference: {key}')
        paths[key] = path
    with rasterio.open(paths['sample_submission']) as src:
        reference = (src.count, src.shape, src.crs, src.transform)
        footprint = np.isfinite(src.read(1))
    with rasterio.open(paths['existing_faults']) as src:
        if (src.count, src.shape, src.crs, src.transform) != reference:
            raise ValueError('Catalogue reference grid mismatch')
        catalogue = (src.read(1) > 0) & footprint
    policy = json.loads((root / 'registry/artifact_policy.json').read_text())['files']
    indexed = {r['path']: r for r in policy}
    if len(indexed) != len(policy):
        raise ValueError('Duplicate policy entry')
    actual = {p.relative_to(root).as_posix() for p in (root / 'docs/downloads').iterdir()
              if p.suffix.lower() in ('.tif', '.tiff', '.zip')}
    if actual != set(indexed):
        raise ValueError(f'Incomplete inventory: {sorted(actual ^ set(indexed))}')
    results = []
    for name, row in sorted(indexed.items()):
        result = {'path': name, 'policy_status': row['status'], 'ok_to_submit': False}
        try:
            data = (root / name).read_bytes()
            result['sha256'] = digest(data)
            if result['sha256'] != row['sha256']:
                raise ValueError('Policy SHA-256 mismatch')
            if name.lower().endswith('.zip'):
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    members = archive.infolist()
                    if len(members) != 1 or members[0].is_dir() or Path(members[0].filename).name != members[0].filename:
                        raise ValueError('ZIP must contain exactly one root-level TIFF')
                    member = members[0]
                    target = 'docs/downloads/' + member.filename
                    if target not in indexed or not target.lower().endswith(('.tif', '.tiff')):
                        raise ValueError('ZIP member is not a registered TIFF')
                    if member.file_size > 128 * 1024 * 1024:
                        raise ValueError('ZIP member exceeds audit memory budget')
                    data = archive.read(member)
                    if digest(data) != indexed[target]['sha256']:
                        raise ValueError('ZIP member differs from registered TIFF')
                    result['zip_member'] = member.filename
            result.update(inspect_raster(data, reference, footprint, catalogue))
        except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
            result.update(status='FAIL', error=str(exc))
        results.append(result)
    return {'schema_version': 'gems91.download-audit.v1', 'audit_completed': True,
            'scope': 'Pinned-reference technical checks only; historical artifacts are not new experiments.',
            'references': {k: rows[k]['sha256'] for k in paths},
            'files_checked': len(results), 'format_pass': sum(r['status'] == 'PASS' for r in results),
            'format_fail': sum(r['status'] == 'FAIL' for r in results),
            'ok_to_submit': False, 'files': results}


def render_html(report):
    from html import escape
    rows = []
    for row in report['files']:
        failures = row.get('error') or ', '.join(k for k, v in row.get('checks', {}).items() if not v) or 'All technical checks pass'
        rows.append('<tr><td><a href="' + escape(row['path'].removeprefix('docs/')) + '">' +
                    escape(Path(row['path']).name) + '</a></td><td>' + row['status'] +
                    '</td><td>' + escape(failures) + '</td><td>NO</td></tr>')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>All-download safety audit · GEMSDOE91</title>
<link rel="stylesheet" href="assets/portal.css"></head><body><div class="wrap"><main id="main">
<p><a href="index.html">← Current safety verdict</a> · <a href="executive-summary.html">Submission instructions</a></p>
<h1>All-download safety audit</h1><p><strong>OK TO SUBMIT: NO — for every file listed here.</strong></p>
<p>Research downloads are available. PASS means technical checks only, not unique science, improved holdout performance, or competition approval.
FAIL means at least one strict range-safe delivery or masking check failed. Historical files are preserved, not repaired into a new submission.</p>
<p>Any file failing finite-range checks must not be used as a range-safe upload.
Synthetic fixtures are never scientific submissions, even if their technical format passes.</p>
<p>Inspected against hash-verified sample and catalogue references. ZIPs must contain exactly one registered, byte-identical TIFF.
This is a committed snapshot, not a live organizer acceptance receipt.</p><p><a href="download-audit.json">Machine-readable evidence and reference hashes</a></p>
<div class="table-scroll"><table><caption>''' + str(report['files_checked']) + ' downloads: ' + str(report['format_pass']) + ' technical PASS; ' + str(report['format_fail']) + ''' FAIL</caption>
<thead><tr><th scope="col">Download (research only)</th><th scope="col">Technical status</th><th scope="col">Details</th><th scope="col">Submit?</th></tr></thead><tbody>''' + ''.join(rows) + '</tbody></table></div></main></div></body></html>\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--html', type=Path, help='Write a research-only download inventory page')
    args = parser.parse_args()
    try:
        report = audit()
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'audit_completed': False, 'ok_to_submit': False, 'error': str(exc)}))
        return 1
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    if args.html:
        args.html.parent.mkdir(parents=True, exist_ok=True)
        args.html.write_text(render_html(report))
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
