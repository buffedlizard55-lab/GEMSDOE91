"""Delivery verification must never act as a scientific selector."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import rasterio

from generate_submission import RUN_CARD, verify_olc91

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def published(tmp_path):
    card = json.loads((ROOT / RUN_CARD).read_text())
    target = tmp_path / card['raster']['path']
    target.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / card['raster']['path'], target)
    card['verdict']['OK_TO_SUBMIT'] = 'YES'
    save_card(tmp_path, card)
    return tmp_path, card, target


def save_card(root, card):
    (root / RUN_CARD).write_text(json.dumps(card))


def test_valid_bytes_never_promote(published):
    root, _, _ = published
    report = verify_olc91(root)
    assert report['format_ok']
    assert report['recorded_OK_TO_SUBMIT'] == 'YES'
    assert report['OK_TO_SUBMIT'] == 'NO'
    assert report['submission_ready'] is False
    assert report['reference_checks'] == 'NOT_CHECKED'


def test_hash_drift_blocks_download_and_upload(published):
    root, card, _ = published
    card['raster']['sha256'] = '0' * 64
    save_card(root, card)
    report = verify_olc91(root)
    assert not report['format_ok']
    assert report['OK_TO_DOWNLOAD'] == 'NO'
    assert report['OK_TO_SUBMIT'] == 'NO'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -0.01, 1.01])
def test_invalid_range_even_with_updated_hash(published, value):
    root, card, target = published
    with rasterio.open(target, 'r+') as ds:
        a = ds.read(1)
        a[0, 0] = value
        ds.write(a, 1)
    card['raster']['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    save_card(root, card)
    report = verify_olc91(root)
    assert not report['format_ok']
    assert report['OK_TO_SUBMIT'] == 'NO'


def test_escape_is_rejected(published):
    root, card, _ = published
    card['raster']['path'] = '../outside.tif'
    save_card(root, card)
    with pytest.raises(ValueError, match='escapes'):
        verify_olc91(root)


def test_with_data_really_requires_references(published):
    root, _, _ = published
    with pytest.raises(FileNotFoundError):
        verify_olc91(root, with_data=True)


def test_overlong_note_fails(published):
    root, card, _ = published
    card['submission_note'] = 'x' * 141
    save_card(root, card)
    assert not verify_olc91(root)['format_ok']
