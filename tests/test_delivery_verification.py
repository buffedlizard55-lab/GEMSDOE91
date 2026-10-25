"""No scientific reruns: test source/evidence consistency and restore failures."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result)
    return result


def test_measured_evidence_cross_checks_without_any_rerun():
    report = module('verify_evidence').verify()
    assert report['status'] == 'PASS'
    assert report['geological_experiments_rerun'] == 0
    assert not report['submission_ready']


@pytest.mark.parametrize('builder', ['build_concentration', 'build_geod'])
def test_both_legacy_fast_paths_use_shared_max_truth_credit(builder):
    p = np.zeros((20, 20), np.float32); p[:, 10] = 1
    parts = module(builder).dti_parts_f32(p, p > 0)
    assert parts.T == pytest.approx(20)
    assert parts.dti() == pytest.approx(1)


@pytest.mark.parametrize('ids', ['', 'not-a-pin', 'sample_submission,not-a-pin'])
def test_restore_rejects_empty_and_unknown_selection(ids):
    result = subprocess.run([sys.executable, 'scripts/restore_data.py', '--check', '--only', ids],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert 'must name existing pinned IDs' in result.stderr


def test_missing_mirror_is_not_reported_as_verified(tmp_path, monkeypatch, capsys):
    restore = module('restore_data')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'files':[{'id':'missing','local_subpath':'absent.tif','mirror':None}]}))
    monkeypatch.setattr(restore, 'ROOT', tmp_path)
    monkeypatch.setattr(restore, 'MANIFEST', manifest)
    monkeypatch.setattr(sys, 'argv', ['restore_data.py','--check'])
    assert restore.main() == 1
    text = capsys.readouterr().out
    assert 'MISSING' in text and 'selected pinned inputs verified' not in text


def test_stopped_experiment_cannot_be_silently_rerun():
    result = subprocess.run([sys.executable, 'scripts/run_ced.py', '--run'], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'already recorded' in result.stderr


def test_readme_contains_full_starting_brief_and_visible_negative_download():
    text = (ROOT/'README.md').read_text()
    assert 'OK TO DOWNLOAD: YES' in text and 'OK TO SUBMIT: NO' in text
    brief = text.split('## Original user project brief',1)[1]
    for number in range(1,93):
        # The canonical source names are also explicitly preserved by the feed.
        # Every prompt-listed repository must remain discoverable in this README.
        rows=json.loads((ROOT/'docs/fleet-audit.json').read_text())['rows']
        name=rows[number-1]['repository'].split('/')[-1]
        assert f'github.io/{name}/' in brief, name
    for requirement in ('PARALLEL-RUN PROTOCOL','LEAKAGE CANARY','RUN CARD','Pass 1:',
                        'Pass 2:','Pass 3:','Own the Outcome','Maximize P(Win)',
                        'Predicted values must be in range [0, 1]'):
        assert requirement in brief


def test_artifact_verifier_reports_missing_inputs_as_blocked_json(monkeypatch, capsys):
    verifier = module('verify_current_artifact')
    monkeypatch.setattr(verifier, 'verify', lambda _with_data: (_ for _ in ()).throw(
        FileNotFoundError('missing pinned sample')))
    monkeypatch.setattr(sys, 'argv', ['verify_current_artifact.py', '--with-data'])
    assert verifier.main() == 1
    report = json.loads(capsys.readouterr().out)
    assert report == {'status': 'BLOCKED', 'submission_ready': False,
                      'error': 'missing pinned sample'}


def test_preflight_global_verdict_uses_axis_readiness_and_current_date(monkeypatch, tmp_path, capsys):
    preflight = module('preflight')
    entries = [{'id': 'sample_submission'}, {'id': 'parent_r0_nan'}, {'id': 'extra'}]
    monkeypatch.setattr(preflight, 'load_manifest', lambda: {
        'files': entries,
        'axis_requirements': {'AXIS': ['sample_submission', 'parent_r0_nan', 'extra']},
    })
    monkeypatch.setattr(preflight, 'local_path_for', lambda _entry, _root: tmp_path/'unused')
    monkeypatch.setattr(preflight, 'verify_entry', lambda entry, _path:
                        (entry['id'] != 'extra', 'pinned' if entry['id'] != 'extra' else 'missing'))
    monkeypatch.chdir(tmp_path)
    assert preflight.main() == 1
    text = capsys.readouterr().out
    assert 'BUILD BLOCKED' in text
    saved = json.loads((tmp_path/'registry/preflight.json').read_text())
    assert saved['verdict'] == 'BUILD BLOCKED'
    assert saved['checked_utc'] == preflight.datetime.now(preflight.timezone.utc).date().isoformat()


def test_registry_cannot_self_index_candidate_or_escape_repository():
    restore = module('restore_registry')
    with pytest.raises(ValueError, match='self-comparison'):
        restore.validate_rows([{'path':'docs/downloads/self.tif','sha256':'candidate'}], 'candidate')
    with pytest.raises(ValueError):
        restore.validate_rows([{'path':'../escape.tif','sha256':'other'}], 'candidate')


def test_registry_check_preserves_frozen_inventory():
    # Cached references are intentionally optional in a cold CI checkout; the
    # script still cannot rebuild/expand the evidence index in their absence.
    before = (ROOT/'registry/comparison_inventory.json').read_bytes()
    restore = module('restore_registry')
    rows = json.loads(before)['files']
    restore.validate_rows(rows, json.loads((ROOT/'docs/run-card.json').read_text())['raster_sha256'])
    assert len(rows) == 64
    assert (ROOT/'registry/comparison_inventory.json').read_bytes() == before


def test_current_review_renderer_fails_closed_without_consulting_legacy_artifact(monkeypatch):
    renderer = module('render_portal')
    def legacy_must_not_be_consulted():
        raise AssertionError('the current review has no candidate and must not inspect a legacy download')
    monkeypatch.setattr(renderer, 'verify_artifact', legacy_must_not_be_consulted)
    renderer.render()
    page = (ROOT/'docs/index.html').read_text()
    assert 'OK TO DOWNLOAD: NO — NO CURRENT CANDIDATE' in page
    assert 'OK TO SUBMIT: NO' in page
    assert 'No candidate, filename, checksum, or direct download link exists' in page
    assert 'downloads/' not in page
    archive = (ROOT/'docs/s14-lsrg.html').read_text()
    assert 'HISTORICAL ARCHIVE — NOT CURRENT APPROVAL' in archive
    assert 'OK TO DOWNLOAD: NO — no current candidate' in archive
    assert 'user-reported and not organizer-confirmed' in archive


def test_current_review_card_has_no_claimed_experiment_or_submission():
    card = json.loads((ROOT/'docs/run-card-REVIEW-AE77BA5B.json').read_text())
    assert card['lane']['experiments_run'] == 0 and card['slots_used'] == 0
    assert card['gemsdoe32_claim']['evidence_class'] == 'USER-REPORTED CLAIM'
    assert card['gemsdoe32_claim']['organizer_confirmed'] is False
    assert card['holdout_dti']['status'].startswith('NOT RUN')
    assert card['raster_sha256'] is None and card['new_tif_generated_in_review'] is False
    assert card['ok_to_download'].startswith('NO') and card['ok_to_submit'].startswith('NO')
    assert card['submission_name'] is None and card['submission_note'] is None


def test_manifest_distinguishes_current_missing_files_from_historical_verification():
    manifest = json.loads((ROOT/'registry/data_manifest.json').read_text())
    observation = manifest['current_workspace_observation']
    assert observation['manifest_files'] == 15 and observation['present_files'] == 0
    assert observation['mirror_restore_performed'] is False
    assert all(row['local_present'] is False and row['verified_here'] is False
               for row in manifest['files'])
    assert all(row['historical_local_present_2026-10-23'] is True
               for row in manifest['files'])
    assert 'do not establish contest-use' in manifest['policy']


def test_prompt_stub_points_to_canonical_readme_brief():
    stub = (ROOT/'prompt_to_add.txt').read_text()
    assert 'full preserved original GEMSDOE user project brief is in `README.md`' in stub
    assert 'omitted-content placeholder' not in stub
    assert 'do not use as the project brief' in stub


def test_evidence_rejects_nonpooled_score_and_omitted_canary(monkeypatch):
    for mutation in ('score','canary'):
        evidence = module('verify_evidence')
        original = evidence.load
        def altered(name):
            data = original(name)
            if name == 'docs/ced-holdout.json' and mutation == 'score':
                data['summary']['scores']['ced']['dti'] += .01
            if name == 'docs/ced-canaries.json' and mutation == 'canary':
                data['features'].pop(next(iter(data['features'])))
            return data
        monkeypatch.setattr(evidence, 'load', altered)
        with pytest.raises(ValueError):
            evidence.verify()
