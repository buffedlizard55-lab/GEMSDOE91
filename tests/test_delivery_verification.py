"""No scientific reruns: test source/evidence consistency and restore failures."""
import hashlib
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


def test_registry_restore_reports_all_unrecoverable_pins(tmp_path, monkeypatch, capsys):
    """A partial restore must name every missing pin, never stop at the first."""
    restore = module('restore_registry')
    (tmp_path/'registry').mkdir()
    (tmp_path/'docs').mkdir()
    (tmp_path/'docs'/'run-card.json').write_text(json.dumps({'raster_sha256': 'candidate'}))
    rows = [
        {'path': 'docs/downloads/a.tif', 'sha256': 'a', 'bytes': 1},
        {'path': 'docs/downloads/b.tif', 'sha256': 'b', 'bytes': 1},
    ]
    (tmp_path/'registry'/'comparison_inventory.json').write_text(json.dumps({'files': rows}))
    monkeypatch.setattr(restore, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['restore_registry.py', '--check'])
    assert restore.main() == 1
    output = capsys.readouterr().out
    assert 'docs/downloads/a.tif' in output
    assert 'docs/downloads/b.tif' in output
    assert 'Verified 0/2' in output


def test_frozen_registry_helper_reports_partial_scope(tmp_path, monkeypatch):
    from scripts import evaluate_holdout as evaluator

    (tmp_path/'registry').mkdir()
    good = tmp_path/'data'/'fleet_registry'/'good.tif'
    good.parent.mkdir(parents=True)
    good.write_bytes(b'good')
    digest = hashlib.sha256(b'good').hexdigest()
    inventory = {
        'complete_universal_registry': False,
        'files': [
            {'path': 'data/fleet_registry/good.tif', 'sha256': digest},
            {'path': 'docs/downloads/missing.tif', 'sha256': '0' * 64},
        ],
    }
    (tmp_path/'registry'/'comparison_inventory.json').write_text(json.dumps(inventory))
    monkeypatch.setattr(evaluator, 'ROOT', tmp_path)
    paths, status = evaluator.frozen_registry_paths()
    assert paths == [good]
    assert status['n_declared'] == 2
    assert status['n_verified'] == 1
    assert status['missing'] == ['docs/downloads/missing.tif']
    assert not status['complete_inventory']
    assert not status['complete_universal_registry']


def test_renderer_refuses_an_unverified_download(monkeypatch):
    renderer = module('render_portal')
    monkeypatch.setattr(renderer, 'verify_artifact', lambda: {'status':'NO_ARTIFACT'})
    with pytest.raises(ValueError, match='unverified or missing download'):
        renderer.render()


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
