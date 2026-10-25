"""Tiny file fixtures exercise pin, grid and nodata handling without real data."""
import hashlib
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts.experiment_preflight import inspect_witness


def fixture(root, *, bad_grid=False, value=1):
    (root / 'data').mkdir()
    (root / 'registry').mkdir()
    base = dict(driver='GTiff', count=1, height=8, width=8, dtype='float32',
                crs='EPSG:32611', transform=from_origin(243350, 4508550, 100, 100))
    a = np.zeros((8, 8), np.float32)
    with rasterio.open(root / 'data/sample.tif', 'w', **base) as s:
        s.write(a, 1)
    a[0, 0] = value
    if bad_grid:
        base['transform'] = from_origin(243351, 4508550, 100, 100)
    with rasterio.open(root / 'data/witness.tif', 'w', **base) as s:
        s.write(a, 1)
    def pin(path):
        b = (root / path).read_bytes()
        return dict(path=path, sha256=hashlib.sha256(b).hexdigest(), bytes=len(b))
    sample = pin('data/sample.tif')
    sample.update(id='sample_submission', local_subpath='sample.tif')
    (root / 'registry/data_manifest.json').write_text(json.dumps({'files': [sample]}))
    (root / 'registry/comparison_inventory.json').write_text(json.dumps({'files': [pin('data/witness.tif')]}))


def test_valid_witness_reads_actual_pixels(tmp_path):
    fixture(tmp_path)
    r = inspect_witness(tmp_path, 'data/witness.tif', 10)
    # Quarter disk around corner: 11 integer-coordinate sites within r <= 3.
    assert r['uncovered_pixels'] == 64 - 11
    assert r['complete_registry_check'] is False
    assert len(r['reference_sha256']) == 64


def test_shifted_grid_fails_even_with_valid_hash(tmp_path):
    fixture(tmp_path, bad_grid=True)
    with pytest.raises(ValueError, match='grid'):
        inspect_witness(tmp_path, 'data/witness.tif', 10)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), .5, -1])
def test_nonbinary_or_nonfinite_witness_fails(tmp_path, value):
    fixture(tmp_path, value=value)
    with pytest.raises(ValueError, match='finite binary'):
        inspect_witness(tmp_path, 'data/witness.tif', 10)


def test_unindexed_witness_never_relaxes_rule(tmp_path):
    fixture(tmp_path)
    with pytest.raises(ValueError, match='exactly once'):
        inspect_witness(tmp_path, 'data/unindexed.tif', 10)


def test_altered_witness_blocked(tmp_path):
    fixture(tmp_path)
    with (tmp_path / 'data/witness.tif').open('ab') as f:
        f.write(b'changed')
    with pytest.raises(ValueError, match='SHA256'):
        inspect_witness(tmp_path, 'data/witness.tif', 10)
