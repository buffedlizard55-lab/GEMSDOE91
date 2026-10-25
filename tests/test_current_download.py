"""The actual front-door download, not an older card, must be byte-pinned."""
import json
from pathlib import Path
import shutil

import pytest
from scripts.render_geo91_portal import current_download

ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path):
    card = json.loads((ROOT / 'docs/run-card-GEO91.json').read_text())
    tif = Path(card['e2_raster_path'])
    for path in (Path('docs/run-card-GEO91.json'), Path('registry/artifact_policy.json'), tif, tif.with_suffix('.zip')):
        dest = tmp_path / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, dest)
    return card


def test_actual_front_door_bytes(tmp_path):
    fixture(tmp_path)
    result = current_download(tmp_path)
    assert result['ok_to_download'] is True
    assert result['ok_to_submit'] is False
    assert result['tif'].endswith('-zeros.tif')
    assert result['zip_sha256']


@pytest.mark.parametrize('mutation', ['tif', 'zip', 'card_hash', 'approval', 'escape', 'unregistered'])
def test_front_door_fails_closed(tmp_path, mutation):
    card = fixture(tmp_path)
    if mutation in ('tif', 'zip'):
        path = tmp_path / card['e2_raster_path']
        if mutation == 'zip':
            path = path.with_suffix('.zip')
        path.write_bytes(b'corrupt')
    elif mutation == 'card_hash':
        card['e2_raster_sha256'] = '0' * 64
    elif mutation == 'approval':
        card['submission_ready'] = True
    elif mutation == 'escape':
        card['e2_raster_path'] = '../outside.tif'
    else:
        path = tmp_path / 'registry/artifact_policy.json'
        policy = json.loads(path.read_text())
        policy['files'] = [r for r in policy['files'] if r['path'] != card['e2_raster_path']]
        path.write_text(json.dumps(policy))
    (tmp_path / 'docs/run-card-GEO91.json').write_text(json.dumps(card))
    with pytest.raises(ValueError):
        current_download(tmp_path)


def test_portal_does_not_claim_hidden_score_causality():
    for page in ('geo91-index-src.html', 'geo91-exec-src.html'):
        text = (ROOT / 'docs' / page).read_text()
        for unsupported in ('pure DTI penalty', 'mechanically lifts the score', 'verified mechanism', 'One fresh, unique file'):
            assert unsupported not in text
        assert 'historical' in text.lower()
