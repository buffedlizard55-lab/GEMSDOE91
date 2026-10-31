"""Regression tests for the S25-TLF duplicate-stop release correction."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_audit_and_release_states_are_consistent():
    audit = json.loads((ROOT / 'docs/s25-tlf/witness-audit-20261028.json').read_text())
    card = json.loads((ROOT / 'docs/s25-tlf/run-card.json').read_text())
    policy = json.loads((ROOT / 'registry/artifact_policy.json').read_text())
    assert audit['status'] == 'DUPLICATE_STOP'
    assert audit['directed_dot_overlap']['overlap_within_3px'] > .70
    assert audit['candidate_sha256'] == card['artifact']['sha256']
    assert card['verdict'] == 'negative' and card['ok_to_submit'] is False
    matches = [f for f in policy['files'] if 'gems91-s25-tlf-60000dots-' in f['path']]
    assert len(matches) == 2 and all(f['status'] == 'current_research_only' for f in matches)


def test_public_entry_points_are_fail_closed():
    index = (ROOT / 'docs/index.html').read_text()
    summary = (ROOT / 'docs/s25-tlf/executive-summary.html').read_text()
    assert 'DO NOT SUBMIT S25-TLF' in index
    assert 'No file cleared for competition submission' in summary
    assert '99.6017%' in summary and '0.36 projection' in summary
    assert 'OK TO SUBMIT: NO' in summary
    assert 'cleared to submit' not in index.lower()
    assert 'ok to submit.' not in index.lower()
    assert 'gems91-s25-tlf-60000dots' not in index.lower()
    assert 'id="s25tlf-verdict"' not in index


def test_exhausted_runner_blocks_before_writes(monkeypatch):
    from scripts import run_s25_tlf as runner
    def forbidden(*args, **kwargs):
        raise AssertionError('runner must stop before input reads')
    monkeypatch.setattr(runner, 'verify_pins', forbidden)
    assert runner.main() == 1
