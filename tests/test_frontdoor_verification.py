"""Tiny synthetic fixtures exercise pointer validation; never geological scores."""
import hashlib
import json
from pathlib import Path
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.verify_frontdoor import verify


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def site(tmp_path):
    docs = tmp_path / 'docs'
    downloads = docs / 'downloads'
    downloads.mkdir(parents=True)
    profile = dict(driver='GTiff', height=5, width=5, count=1, dtype='float32',
                   crs='EPSG:32611', transform=from_origin(243350, 4508550, 100, 100))
    files = []
    for key, array in [('sample_submission', np.ones((5, 5), dtype='float32')),
                       ('existing_faults', np.zeros((5, 5), dtype='float32'))]:
        p = tmp_path / 'data' / (key + '.tif')
        p.parent.mkdir(exist_ok=True)
        with rasterio.open(p, 'w', **profile) as dst:
            dst.write(array, 1)
        files.append(dict(id=key, local_subpath=p.name, sha256=digest(p)))
    tif = downloads / 'candidate.tif'
    with rasterio.open(tif, 'w', **profile) as dst:
        dst.write(np.zeros((5, 5), dtype='float32'), 1)
    archive = tif.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w') as z:
        z.write(tif, tif.name)
    pointer = dict(run_card='card.json', ok_to_download=True, ok_to_submit=False,
                   verdict='negative', tif='downloads/candidate.tif',
                   zip='downloads/candidate.zip', raster_sha256=digest(tif),
                   zip_sha256=digest(archive))
    card = dict(verdict=dict(promote=False, OK_TO_SUBMIT='NO'),
                submission_note='Synthetic validation fixture; not for submission',
                raster=dict(path='docs/' + pointer['tif'], zip='docs/' + pointer['zip'],
                            sha256=pointer['raster_sha256'], zip_sha256=pointer['zip_sha256']))
    dump(docs / 'card.json', card)
    dump(docs / 'current-run.json', pointer)
    dump(tmp_path / 'registry/data_manifest.json', dict(files=files))
    return tmp_path


def test_actual_pointer_passes_without_legacy_run_card(site):
    report = verify(site)
    assert report['status'] == 'PASS'
    assert report['ok_to_submit'] is False
    assert report['validator_output']['checks']['crs_shape_transform_match'] is True
    assert not (site / 'docs/run-card.json').exists()


@pytest.mark.parametrize('field,value', [
    ('ok_to_submit', True), ('ok_to_submit', 'false'), ('ok_to_download', False),
    ('verdict', 'promote'), ('raster_sha256', '0' * 64),
    ('zip_sha256', '0' * 64), ('tif', '../outside.tif'),
    ('run_card', '../outside.json'),
])
def test_pointer_tampering_fails_closed(site, field, value):
    path = site / 'docs/current-run.json'
    pointer = json.loads(path.read_text()); pointer[field] = value; dump(path, pointer)
    with pytest.raises((ValueError, FileNotFoundError)):
        verify(site)


def test_missing_pinned_reference_is_not_a_pass(site):
    (site / 'data/sample_submission.tif').unlink()
    with pytest.raises(FileNotFoundError):
        verify(site)


def test_stale_card_fails_even_if_pointer_hash_is_correct(site):
    path = site / 'docs/card.json'
    card = json.loads(path.read_text()); card['raster']['sha256'] = '0' * 64
    dump(path, card)
    with pytest.raises(ValueError, match='pointer/run-card mismatch'):
        verify(site)


def test_extra_zip_member_fails_even_with_updated_hashes(site):
    archive = site / 'docs/downloads/candidate.zip'
    with zipfile.ZipFile(archive, 'a') as z:
        z.writestr('extra.txt', 'unexpected')
    for path, field in [(site / 'docs/current-run.json', 'zip_sha256'),
                        (site / 'docs/card.json', 'raster')]:
        obj = json.loads(path.read_text())
        if field == 'raster': obj[field]['zip_sha256'] = digest(archive)
        else: obj[field] = digest(archive)
        dump(path, obj)
    with pytest.raises(ValueError, match='exactly the current TIFF'):
        verify(site)


def test_frontdoor_does_not_mislabel_holdout_as_leaderboard():
    root = Path(__file__).resolve().parents[1]
    for name in ('docs/olc91-index-src.html', 'scripts/render_s17_portal.py'):
        assert 'LB-DTI' not in (root / name).read_text()


@pytest.mark.parametrize('bad_value', [float('nan'), float('inf'), -0.1, 1.01])
def test_invalid_pixels_fail_even_after_repinning_identity(site, bad_value):
    tif = site / 'docs/downloads/candidate.tif'
    with rasterio.open(tif, 'r+') as dst:
        values = dst.read(1); values[2, 2] = bad_value; dst.write(values, 1)
    archive = tif.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w') as z:
        z.write(tif, tif.name)
    p = site / 'docs/current-run.json'
    pointer = json.loads(p.read_text())
    pointer.update(raster_sha256=digest(tif), zip_sha256=digest(archive)); dump(p, pointer)
    c = site / 'docs/card.json'; card = json.loads(c.read_text())
    card['raster'].update(sha256=digest(tif), zip_sha256=digest(archive)); dump(c, card)
    with pytest.raises(ValueError, match='technical failure'):
        verify(site)
