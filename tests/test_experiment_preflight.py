"""Capacity proof tests are synthetic mathematics, not geological experiments."""
from __future__ import annotations

import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from gems91.capacity import capacity_bound
from scripts import experiment_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]


def test_exact_threshold_and_integer_capacity():
    fp = np.ones((1, 10), bool)
    ref = np.zeros_like(fp)
    ref[0, 3] = True  # indices 0..6 are within 3px; 7..9 are not
    r = capacity_bound(fp, ref, 10)
    assert r['minimum_overlapping_dots'] == 7
    assert r['overlap_lower_bound'] == .7
    assert r['status'] == 'NOT_RULED_OUT'  # equality is allowed
    assert r['largest_budget_by_capacity_only'] == 10


def test_empty_reference_does_not_use_edt_exterior():
    fp = np.ones((2, 3), bool)
    r = capacity_bound(fp, np.zeros_like(fp), 6)
    assert r['uncovered_pixels'] == 6
    assert r['overlap_lower_bound'] == 0


def test_saturated_reference_is_impossible():
    fp = np.ones((6, 6), bool)
    r = capacity_bound(fp, fp, 1)
    assert r['status'] == 'IMPOSSIBLE_AT_BUDGET'
    assert r['largest_budget_by_capacity_only'] == 0


def test_bound_matches_exhaustive_placement_and_euclidean_radius():
    fp = np.zeros((8, 8), bool)
    points = [(0, 0), (3, 0), (3, 1), (3, 3), (4, 0), (7, 7)]
    for p in points:
        fp[p] = True
    ref = np.zeros_like(fp)
    ref[0, 0] = True
    for budget in range(1, len(points) + 1):
        best = min(sum(np.hypot(*p) <= 3 for p in combo)
                   for combo in itertools.combinations(points, budget))
        result = capacity_bound(fp, ref, budget)
        assert result['minimum_overlapping_dots'] == best
        assert result['feasible_by_capacity_only'] == (10 * best <= 7 * budget)


@pytest.mark.parametrize('budget', [0, -1, True, 1.0, 10, None])
def test_invalid_budgets(budget):
    with pytest.raises(ValueError, match='budget'):
        capacity_bound(np.ones((2, 2), bool), np.zeros((2, 2), bool), budget)


def test_bad_masks():
    with pytest.raises(ValueError, match='boolean'):
        capacity_bound(np.ones((2, 2)), np.zeros((2, 2), bool), 1)
    with pytest.raises(ValueError):
        capacity_bound(np.ones((2, 2), bool), np.zeros((3, 2), bool), 1)
    with pytest.raises(ValueError):
        capacity_bound(np.zeros((2, 2), bool), np.zeros((2, 2), bool), 1)


def plan():
    return {'lane': {'method': 'Synthetic unit-test method', 'assignment_source': 'unit test only'},
            'dot_budget': 10, 'registry_witness': 'test.tif',
            'experiments_used': 0, 'elapsed_minutes': 0}


def test_no_candidate_or_approval_even_when_not_ruled_out(monkeypatch):
    monkeypatch.setattr(preflight, 'inspect_witness', lambda *_: {'feasible_by_capacity_only': True, 'sample_semantics': {'status': 'CONSISTENT_NOT_AUTHENTICATED'}})
    r = preflight.evaluate(ROOT, plan())
    assert r['status'] == 'NOT_RULED_OUT'
    assert r['assignment_authenticated'] is False
    assert r['ok_to_submit'] is False
    assert r['candidate_generated'] is False


@pytest.mark.parametrize(('key', 'value'), [('lane', None), ('experiments_used', 3),
    ('experiments_used', True), ('elapsed_minutes', 120), ('elapsed_minutes', float('nan')),
    ('elapsed_minutes', float('inf')), ('elapsed_minutes', -1), ('elapsed_minutes', True)])
def test_plan_blocks_invalid_or_exhausted_budget(monkeypatch, key, value):
    monkeypatch.setattr(preflight, 'inspect_witness', lambda *_: {'feasible_by_capacity_only': True, 'sample_semantics': {'status': 'CONSISTENT_NOT_AUTHENTICATED'}})
    p = plan(); p[key] = value
    assert preflight.evaluate(ROOT, p)['status'] == 'BLOCKED'


def test_missing_reference_never_uses_archived_count(monkeypatch):
    def missing(*_):
        raise FileNotFoundError('missing witness')
    monkeypatch.setattr(preflight, 'inspect_witness', missing)
    r = preflight.evaluate(ROOT, plan())
    assert r['status'] == 'BLOCKED'
    assert r['capacity']['status'] == 'UNVERIFIED'
    assert 'uncovered_pixels' not in r['capacity']


def test_missing_runtime_dependency_is_machine_readable_block(monkeypatch):
    def unavailable(*_):
        raise ModuleNotFoundError("No module named 'numpy'")
    monkeypatch.setattr(preflight, 'inspect_witness', unavailable)
    result = preflight.evaluate(ROOT, plan())
    assert result['status'] == 'BLOCKED'
    assert result['capacity'] == {
        'status': 'UNVERIFIED', 'error': "No module named 'numpy'"}
    assert result['ok_to_submit'] is False
    assert result['candidate_generated'] is False


def test_pin_rejects_modified_bytes_and_path_escape(tmp_path):
    p = tmp_path / 'a'; p.write_bytes(b'changed')
    with pytest.raises(ValueError, match='SHA256'):
        preflight.pinned_path(tmp_path, 'a', '0' * 64, 7)
    with pytest.raises(ValueError, match='escapes'):
        preflight.pinned_path(tmp_path, '../outside', '0' * 64, 0)


def test_cli_missing_plan_is_machine_readable_and_nonzero(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/experiment_preflight.py'),
                             '--plan', str(tmp_path / 'absent.json')], capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)['status'] == 'BLOCKED'


def test_repository_plan_does_not_invent_assignment():
    p = json.loads((ROOT / 'registry/experiment_plan.json').read_text())
    assert p['lane'] is None
    assert p['dot_budget'] == 37654


def test_reference_dots_outside_footprint_do_not_tighten_bound(tmp_path):
    import hashlib
    import rasterio
    from rasterio.transform import from_origin

    root = tmp_path
    sample_path = root / 'data/official/sample_submission.tif'
    ref_path = root / 'data/fleet_registry/calib_r13lattice_00904.tif'
    sample_path.parent.mkdir(parents=True)
    ref_path.parent.mkdir(parents=True)
    (root / 'registry').mkdir()
    sample = np.full((6, 6), np.nan, np.float32)
    sample[1:5, 1:5] = 0
    reference = np.zeros((6, 6), np.float32)
    reference[0, 0] = reference[0, -1] = 1  # outside footprint
    for path, arr in [(sample_path, sample), (ref_path, reference)]:
        with rasterio.open(path, 'w', driver='GTiff', height=6, width=6,
                           count=1, dtype='float32', crs='EPSG:32611',
                           transform=from_origin(0, 600, 100, 100)) as dst:
            dst.write(arr, 1)
    def pin(path):
        return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'bytes': path.stat().st_size}
    (root / 'registry/data_manifest.json').write_text(json.dumps({'files': [
        {'id': 'sample_submission', 'local_subpath': 'official/sample_submission.tif', **pin(sample_path)}]}))
    (root / 'registry/comparison_inventory.json').write_text(json.dumps({'files': [
        {'path': 'data/fleet_registry/calib_r13lattice_00904.tif', **pin(ref_path)}]}))
    got = preflight.inspect_witness(root, 'data/fleet_registry/calib_r13lattice_00904.tif', 10)
    assert got['reference_dots'] == 0
    assert got['overlap_lower_bound'] == 0.0
    assert got['status'] == 'NOT_RULED_OUT'


def test_sample_conflict_or_absent_semantics_blocks_preflight(monkeypatch):
    for semantics in ({'status': 'CONFLICT_WITH_ORGANIZER_DESCRIPTION', 'nonzero_inside_footprint': 1}, None):
        witness = {'feasible_by_capacity_only': True}
        if semantics is not None:
            witness['sample_semantics'] = semantics
        monkeypatch.setattr(preflight, 'inspect_witness', lambda *_, w=witness: w)
        result = preflight.evaluate(ROOT, plan())
        assert result['status'] == 'BLOCKED'
        assert any('Sample semantics' in reason for reason in result['reasons'])
        assert not result['ok_to_submit']
