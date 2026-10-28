"""Release guidance must not turn a format pass or mutable flag into approval."""
import hashlib
import json
from pathlib import Path

from scripts.review_tlf_release import audit
from scripts import render_olc91_portal as portal

ROOT = Path(__file__).resolve().parents[1]


def test_fresh_delivery_integrity_never_approves_submission():
    result = audit()
    assert result['format_ok']
    assert result['ok_to_submit'] is False
    assert result['estimated_leaderboard_score'] is None
    assert result['organizer_confirmed_score'] is None


def test_corrected_card_preserves_bytes_not_promotion():
    old = json.loads((ROOT / 'evidence/review-de9d7d75/originals/run-card.json').read_text())
    new = json.loads((ROOT / 'docs/s25-tlf/run-card.json').read_text())
    assert old['verdict'] == 'promote' and new['verdict'] == 'negative'
    assert new['ok_to_submit'] is False
    assert new['artifact'] == old['artifact']
    assert new['holdout'] == old['holdout']
    assert hashlib.sha256((ROOT / new['artifact']['tif']).read_bytes()).hexdigest() == new['artifact']['sha256']
    assert new['uniqueness']['pass_vs_nine'] is None


def test_root_does_not_trust_mutable_lane_flags(tmp_path, monkeypatch):
    p = tmp_path / 'docs/s25-tlf'
    p.mkdir(parents=True)
    (p / 'run-card.json').write_text('{"ok_to_submit": true}')
    monkeypatch.setattr(portal, 'ROOT', tmp_path)
    text = portal._root_verdict()
    assert 'OK TO SUBMIT: NO' in text
    assert 'cleared to submit' not in text.lower()
    assert '0.36' not in text


def test_corrected_renderer_idempotent():
    from scripts.render_s25tlf_portal import main
    p = ROOT / 'docs/s25-tlf/executive-summary.html'
    main()
    first = p.read_bytes()
    main()
    assert p.read_bytes() == first
    text = first.decode()
    assert 'OK TO SUBMIT: NO' in text
    assert 'OK TO SUBMIT: YES' not in text
    assert 'projection are withdrawn' in text
    for site in ('24', '25', '27', '28', '30', '31', '32', '33', '36'):
        assert 'GEMSDOE' + site in text


def test_exhausted_runner_blocks_before_reading_pins(monkeypatch, capsys):
    from scripts import run_s25_tlf as runner
    def forbidden(*args, **kwargs):
        raise AssertionError('exhausted runner must not read inputs')
    monkeypatch.setattr(runner, 'verify_pins', forbidden)
    assert runner.main() == 1
    assert 'BLOCKED' in capsys.readouterr().out
