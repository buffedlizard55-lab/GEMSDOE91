#!/usr/bin/env python3
"""Check a pinned impossibility witness before spending an experiment.

No network, training, placement, registry changes, or slot selection. Exit 1
means blocked; 0 means only NOT_RULED_OUT, never approval to submit. A plan's
assignment metadata is recorded, not authenticated by this tool.

  python scripts/restore_data.py --only sample_submission
  # Restore the frozen registry with scripts/restore_registry.py if needed.
  python scripts/experiment_preflight.py --output work/experiment-preflight.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems91.capacity import capacity_bound  # noqa: E402


def pinned_path(root: Path, relative: str, digest: str, size: int) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('reference path escapes repository')
    data = path.read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError(f'Pinned SHA256/length mismatch: {relative}')
    return path


def inspect_witness(root: Path, witness_path: str, budget: int) -> dict:
    import numpy as np
    import rasterio

    manifest = json.loads((root / 'registry/data_manifest.json').read_text())
    row = next(r for r in manifest['files'] if r['id'] == 'sample_submission')
    sample = pinned_path(root, 'data/' + row['local_subpath'], row['sha256'], row['bytes'])
    inventory = root / 'registry/comparison_inventory.json'
    rows = json.loads(inventory.read_text())['files']
    matches = [r for r in rows if r['path'] == witness_path]
    if len(matches) != 1:
        raise ValueError('Witness must occur exactly once in the unchanged frozen inventory')
    ref = matches[0]
    reference = pinned_path(root, ref['path'], ref['sha256'], ref['bytes'])
    with rasterio.open(sample) as src:
        grid = (src.count, src.shape, src.crs, src.transform)
        fp = np.isfinite(src.read(1)) & (src.read_masks(1) > 0)
    with rasterio.open(reference) as src:
        if src.count != 1 or (src.count, src.shape, src.crs, src.transform) != grid:
            raise ValueError('Witness grid differs from pinned sample')
        a = src.read(1)
        if not np.isfinite(a[fp]).all() or not np.isin(a[fp], [0, 1]).all():
            raise ValueError('Witness must be a finite binary-dot raster inside footprint')
        # All positive reference cells count, even outside the footprint. Never
        # top-K a dense witness or silently drop dots to relax the literal rule.
        support = np.isfinite(a) & (a > 0)
    result = capacity_bound(fp, support, budget)
    result.update(reference_path=ref['path'], reference_sha256=ref['sha256'],
                  reference_source_url=ref.get('source_url'), sample_sha256=row['sha256'],
                  inventory_sha256=hashlib.sha256(inventory.read_bytes()).hexdigest(),
                  complete_registry_check=False)
    return result


def evaluate(root: Path, plan: dict) -> dict:
    if not isinstance(plan, dict):
        raise ValueError('Plan must be a JSON object')
    reasons = []
    lane = plan.get('lane')
    lane_present = (isinstance(lane, dict) and
                    all(isinstance(lane.get(k), str) and lane[k].strip()
                        for k in ('method', 'assignment_source')))
    if not lane_present:
        reasons.append('No assigned single-method paragraph and assignment source')
    experiments = plan.get('experiments_used')
    minutes = plan.get('elapsed_minutes')
    if type(experiments) is not int or not 0 <= experiments < 3:
        reasons.append('Experiment budget exhausted or invalid (must be below 3)')
    if type(minutes) not in (int, float) or not 0 <= minutes < 120:
        reasons.append('Time budget exhausted or invalid (must be below 120 minutes)')
    try:
        capacity = inspect_witness(root, plan['registry_witness'], plan['dot_budget'])
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        capacity = {'status': 'UNVERIFIED', 'error': str(exc)}
        reasons.append('Capacity witness unavailable or invalid; no fallback to archived constants')
    else:
        if not capacity['feasible_by_capacity_only']:
            reasons.append('Literal registry overlap is mathematically impossible at this dot budget')
    return {
        'schema': 'gems91.experiment-preflight.v1',
        'status': 'BLOCKED' if reasons else 'NOT_RULED_OUT',
        'assignment_metadata_present': bool(lane_present),
        'assignment_authenticated': False,
        'reasons': reasons,
        'capacity': capacity,
        'experiments_run_by_this_command': 0,
        'candidate_generated': False,
        'ok_to_submit': False,
        'scope': 'Necessary pre-experiment checks only; feature canaries, both registry phases, matched holdout and separate selector still required.',
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, default=ROOT / 'registry/experiment_plan.json')
    ap.add_argument('--output', type=Path)
    args = ap.parse_args(argv)
    try:
        report = evaluate(ROOT, json.loads(args.plan.read_text()))
    except (OSError, ValueError, TypeError) as exc:
        report = {'status': 'BLOCKED', 'ok_to_submit': False, 'error': str(exc)}
    text = json.dumps(report, indent=2, allow_nan=False) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end='')
    return 1 if report['status'] == 'BLOCKED' else 0


if __name__ == '__main__':
    raise SystemExit(main())
