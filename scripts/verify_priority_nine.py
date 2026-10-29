#!/usr/bin/env python3
"""Nine-leader diagnostic using the shared checker plus a pinned footprint.

Reads exact owner-GitHub leader blobs through verify_nine_site_leaders.py.
A supplied sample's footprint is necessary but does not authenticate the
sample, prove organizer acceptance, or establish a complete registry.
No experiment, candidate or weekly submission is generated or selected.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import verify_nine_site_leaders as shared  # noqa: E402


def sample_footprint(path: Path):
    with rasterio.open(path) as src:
        if src.count != 1 or src.crs is None:
            raise ValueError('sample must be a single-band georeferenced raster')
        footprint = np.isfinite(src.read(1)) & (src.read_masks(1) > 0)
        grid = {'crs': src.crs.to_string(), 'shape': list(src.shape),
                'transform': list(src.transform)[:6]}
    if not footprint.any():
        raise ValueError('sample footprint is empty')
    return footprint, grid


def checked_dots(path: Path, footprint, grid):
    points, meta = shared.dots_of(path)
    if any(meta[k] != grid[k] for k in ('crs', 'shape', 'transform')):
        raise ValueError(f'{path}: footprint grid mismatch')
    if footprint.shape != tuple(meta['shape']) or not footprint.any():
        raise ValueError(f'{path}: invalid footprint')
    with rasterio.open(path) as src:
        values = src.read(1)
    if not np.isfinite(values[footprint]).all():
        raise ValueError(f'{path}: non-finite value inside footprint')
    outside = int(((values > 0) & ~footprint).sum())
    if outside:
        raise ValueError(f'{path}: positive values outside footprint')
    meta.update(positive_outside_footprint=outside, footprint_checked=True)
    return points, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sample', type=Path, required=True)
    ap.add_argument('--cache', type=Path, default=ROOT / 'data/nine_site_leaders')
    ap.add_argument('--candidate', action='append', default=[])
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    footprint, grid = sample_footprint(args.sample)
    args.cache.mkdir(parents=True, exist_ok=True)
    files = {}
    for site, (score, token, suffix) in shared.LEADERS.items():
        entry = shared.find_tif(site, token, suffix)
        path = shared.fetch(site, entry, args.cache)
        dots, meta = checked_dots(path, footprint, grid)
        files[site] = {'score_user_cited': score, 'encoding_suffix': suffix,
                       'repo_path': entry['path'], 'blob_sha': entry['sha'],
                       'sha256': shared.sha256(path), 'dots_xy': dots, **meta}
    for relative in args.candidate:
        path = ROOT / relative
        dots, meta = checked_dots(path, footprint, grid)
        files[f'CANDIDATE:{path.name}'] = {'score_user_cited': None, 'repo_path': relative,
                                           'sha256': shared.sha256(path), 'dots_xy': dots, **meta}
    overlaps = {f'{a} -> {b}': shared.within3(files[a]['dots_xy'], files[b]['dots_xy'])
                for a in files for b in files if a != b}
    result = {
        'schema': 'nine-site-leader-check-v2',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'method': 'Git-tree-verified blob bytes; binary dots = value>0; directed A-to-B overlap uses Euclidean distance <=3 px. Footprint checked against the supplied sample; sample authenticity is unverified. No organizer receipt check.',
        'sample_sha256': shared.sha256(args.sample),
        'score_evidence': 'User-reported claims only; no organizer receipt or score estimate.',
        'files': {k: {kk: vv for kk, vv in row.items() if kk != 'dots_xy'} | {'dots': len(row['dots_xy'])}
                  for k, row in files.items()},
        'max_overlap_into_any_other_leader': shared.maximum_peer_overlaps(overlaps),
        'overlap_pairs': overlaps,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'out': str(args.out), 'max_overlap_into_any_other_leader': result['max_overlap_into_any_other_leader']}, indent=1))


if __name__ == '__main__':
    main()
