"""Default CLI must inspect the same bytes the user downloads, never a sibling."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.verify_front_door import verify

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def published(tmp_path):
    pointer = json.loads((ROOT / 'docs/current-run.json').read_text())
    paths = ['docs/current-run.json', 'docs/' + pointer['run_card'],
             'registry/artifact_policy.json', 'docs/' + pointer['tif'], 'docs/' + pointer['zip']]
    for name in paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return tmp_path, pointer


def test_current_download_is_verified(published):
    root, pointer = published
    report = verify(root)
    assert report['file'] == 'docs/' + pointer['tif']
    assert report['sha256'] == pointer['raster_sha256']
    assert report['format_ok']
    assert report['reference_checks'] == 'NOT_CHECKED'
    assert report['OK_TO_SUBMIT'] == 'NO'


@pytest.mark.parametrize('mutation', ['tif', 'zip', 'pointer', 'approval', 'card_path', 'note'])
def test_corruption_and_pointer_drift_fail_closed(published, mutation):
    root, pointer = published
    if mutation in ('tif', 'zip'):
        (root / 'docs' / pointer[mutation]).write_bytes(b'corrupt')
    elif mutation in ('pointer', 'approval', 'card_path'):
        field, value = {'pointer': ('raster_sha256', '0' * 64),
                        'approval': ('ok_to_submit', True),
                        'card_path': ('run_card', '../outside.json')}[mutation]
        pointer[field] = value
        (root / 'docs/current-run.json').write_text(json.dumps(pointer))
    else:
        path = root / 'docs' / pointer['run_card']
        card = json.loads(path.read_text())
        card['submission_note'] = 'x' * 141
        path.write_text(json.dumps(card))
        report = verify(root)
        assert not report['format_ok']
        assert report['OK_TO_DOWNLOAD'] == 'NO'
        assert report['OK_TO_SUBMIT'] == 'NO'
        return
    with pytest.raises(ValueError):
        verify(root)


def test_reference_check_does_not_silently_skip_missing_data(published):
    with pytest.raises(FileNotFoundError):
        verify(published[0], with_data=True)


def test_default_cli_matches_current_manifest():
    result = subprocess.run([sys.executable, 'generate_submission.py'], cwd=ROOT,
                            capture_output=True, text=True, check=True)
    report = json.loads(result.stdout)
    pointer = json.loads((ROOT / 'docs/current-run.json').read_text())
    assert report['file'] == 'docs/' + pointer['tif']
    assert report['OK_TO_SUBMIT'] == 'NO'


def test_run_never_silently_executes_unassigned_legacy_builder():
    result = subprocess.run([sys.executable, 'generate_submission.py', '--run'], cwd=ROOT,
                            capture_output=True, text=True)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report['status'] == 'BLOCKED'
    assert report['OK_TO_SUBMIT'] == 'NO'
    assert 'assigned method lane' in report['error']


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -0.01, 1.01])
def test_invalid_values_fail_even_after_repinning_all_hashes(published, value):
    import hashlib
    import zipfile
    import rasterio
    root, pointer = published
    tif = root / 'docs' / pointer['tif']
    zipped = root / 'docs' / pointer['zip']
    with rasterio.open(tif, 'r+') as src:
        values = src.read(1)
        values[0, 0] = value
        src.write(values, 1)
    with zipfile.ZipFile(zipped, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(tif, arcname=tif.name)
    hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (tif, zipped)}
    pointer['raster_sha256'] = hashes[tif]
    pointer['zip_sha256'] = hashes[zipped]
    (root / 'docs/current-run.json').write_text(json.dumps(pointer))
    path = root / 'docs' / pointer['run_card']
    card = json.loads(path.read_text())
    card['raster_sha256'] = hashes[tif]
    path.write_text(json.dumps(card))
    path = root / 'registry/artifact_policy.json'
    policy = json.loads(path.read_text())
    for row in policy['files']:
        for p, digest in hashes.items():
            if row['path'] == p.relative_to(root).as_posix():
                row['sha256'] = digest
    path.write_text(json.dumps(policy))
    report = verify(root)
    assert report['OK_TO_DOWNLOAD'] == 'NO'
    assert not report['format_ok']
    assert report['OK_TO_SUBMIT'] == 'NO'
