"""Prospective guards only: these tests never re-run the recorded S22 experiment."""
import json
import pytest


def test_recorded_runner_refuses_an_unauthenticated_assignment(tmp_path, monkeypatch):
    from scripts import run_s22_omtj as runner
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'registry/experiment_plan.json').write_text(json.dumps({'dot_budget': runner.BUDGET}))
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'OUT', tmp_path / 'docs/s22')
    monkeypatch.setattr(runner, 'WORK', tmp_path / 'work/s22')
    monkeypatch.setattr(runner, 'evaluate_preflight', lambda root, plan: {
        'status': 'NOT_RULED_OUT', 'assignment_authenticated': False,
    })
    with pytest.raises(RuntimeError, match='assignment not authenticated'):
        runner.run()
    assert not (tmp_path / 'work/s22/surface.npy').exists()
    assert not (tmp_path / 'docs/s22/run-card.json').exists()


def test_recorded_runner_cannot_change_the_dot_budget_to_evade_preflight(tmp_path, monkeypatch):
    from scripts import run_s22_omtj as runner
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'registry/experiment_plan.json').write_text(json.dumps({'dot_budget': 20000}))
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'OUT', tmp_path / 'docs/s22')
    monkeypatch.setattr(runner, 'WORK', tmp_path / 'work/s22')
    with pytest.raises(RuntimeError, match='budget differs'):
        runner.run()
    assert not (tmp_path / 'work/s22/surface.npy').exists()
