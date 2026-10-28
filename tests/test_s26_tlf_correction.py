"""No scientific experiment: frozen correction contract and renderer safety."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_tlf_approval_is_retracted():
    card = json.loads((ROOT / 'docs/s25-tlf/run-card.json').read_text())
    assert card['verdict'] == 'negative'
    assert card['ok_to_submit'] is False
    report = json.loads((ROOT / 'docs/s26/tlf-protocol-audit.json').read_text())
    assert report['references_checked'] == 62
    assert len(report['missing']) == 2
    assert report['literal_pass'] is False
    assert max(r['overlap_within_3px'] for r in report['comparisons']) > .99
    assert report['validator_output']['status'] == 'PASS'
    assert report['leaderboard_estimate'] is None


def test_corrective_renderer_never_restores_approval():
    from scripts.render_s25tlf_portal import render
    render()
    page = ROOT / 'docs/s25-tlf/executive-summary.html'
    before = page.read_bytes()
    render()
    assert before == page.read_bytes()
    text = before.decode()
    assert 'OK TO SUBMIT: NO' in text
    assert 'withdrawn' in text
    for site in (24, 25, 27, 28, 30, 31, 32, 33, 36):
        assert f'GEMSDOE{site}' in text
    for rel in ('index.html', 'docs/index.html'):
        text = (ROOT / rel).read_text()
        assert 'OK TO SUBMIT: NO' in text
        assert 'CLEARED TO SUBMIT' not in text
        assert 'OK to download and OK to submit.' not in text


def test_legacy_tlf_runner_cannot_regenerate():
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_s25_tlf.py')],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'BLOCKED' in result.stdout + result.stderr
