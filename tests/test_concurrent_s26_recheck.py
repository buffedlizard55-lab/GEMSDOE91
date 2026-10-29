"""Concurrent historical outputs stay byte-bound, non-promoted and non-runnable."""
import copy
import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts import render_priority_review, run_s26_emit, run_s26_lidarrad

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s26_recheck_binds_each_research_pair_and_stops_at_lattice():
    report = json.loads((ROOT / 'docs/review-4239f6e5/concurrent-s26-audit.json').read_text())
    assert sha(ROOT / 'scripts/audit_concurrent_s26.py') == report['implementation_sha256']
    assert sha(ROOT / 'scripts/audit_priority_snapshot.py') == report['shared_audit_sha256']
    assert sha(ROOT / 'scripts/audit_downloads.py') == report['validator_implementation_sha256']
    assert len(report['results']) == 3
    for r in report['results']:
        tif, archive = ROOT / r['tif'], ROOT / r['zip']
        assert sha(tif) == r['tif_sha256'] and sha(archive) == r['zip_sha256']
        with zipfile.ZipFile(archive) as z:
            assert z.namelist() == [tif.name] and z.read(tif.name) == tif.read_bytes()
        assert r['validator_output']['status'] == 'PASS' and r['submission_ready'] is False
        assert r['surface_before_placement'] == 'NOT_RECHECKED'
        assert r['final_dot_comparison']['dot_status'] == 'DUPLICATE'
        assert r['final_dot_comparison']['directed_overlap_within_3px'] > .70
    assert [r['candidate_dots'] for r in report['results']] == [37654, 22163, 37654]
    assert report['results'][0]['final_dot_comparison']['directed_overlap_within_3px'] == pytest.approx(.9923248526053009)


def test_original_runners_are_preserved_but_disabled():
    saved = ROOT / 'evidence/concurrent-s26-20261029'
    assert sha(saved / 'run_s26_emit-original.py.txt') == 'd376f79e2b763616e9090e4226e15d813eca001e7c6a4a72e2d85acf59b54137'
    assert sha(saved / 'run_s26_lidarrad-original.py.txt') == '671af14586794708308924467ed93d269ccaf1ece9bfcc203f57753dc3da6a35'
    with pytest.raises(RuntimeError, match='disabled'):
        run_s26_emit.main()
    with pytest.raises(RuntimeError, match='disabled'):
        run_s26_emit.write_candidate(22163, 10, 'test', 'test')
    with pytest.raises(RuntimeError, match='disabled'):
        run_s26_lidarrad.main()


def test_corrected_cards_do_not_transfer_holdout_or_canary():
    emitter = json.loads((ROOT / 'docs/s26/run-card.json').read_text())
    lidar = json.loads((ROOT / 'docs/run-card-S26.json').read_text())
    assert emitter['ok_to_submit'] is False and emitter['verdict'] == 'negative'
    assert 'not measured for the S26' in emitter['holdout']['label']
    assert emitter['leakage_canary']['pass'] is None
    assert emitter['correlation_overlap_vs_registry']['largest_feasible_budget'] is None
    assert lidar['ok_to_submit'] is False and lidar['verdict'] == 'negative'
    assert lidar['holdout']['canary_pass'] is None
    assert lidar['review_correction']['lattice_status'] == 'DUPLICATE'


def test_renderer_refuses_forged_concurrent_clearance(monkeypatch):
    original = render_priority_review.load
    def mutated(path):
        data = copy.deepcopy(original(path))
        if path.endswith('/concurrent-s26-audit.json'):
            data['results'][0]['submission_ready'] = True
        return data
    monkeypatch.setattr(render_priority_review, 'load', mutated)
    with pytest.raises(ValueError, match='inconsistent'):
        render_priority_review.render()
