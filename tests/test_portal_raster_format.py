"""Small format fixtures are software tests, never competition predictions."""
import hashlib

import numpy as np
import pytest
import rasterio
from affine import Affine
from scripts import render_portal as portal


@pytest.mark.parametrize('coefficient', range(6))
def test_status_board_rejects_every_wrong_transform_coefficient(tmp_path, monkeypatch, coefficient):
    monkeypatch.setitem(portal.EXPECTED_GRID, 'shape', (4, 5))
    transform = list(portal.EXPECTED_GRID['transform'])
    transform[coefficient] += 1
    path = tmp_path / 'wrong-grid.tif'
    with rasterio.open(path, 'w', driver='GTiff', height=4, width=5,
                       count=1, dtype='float32', crs='EPSG:32611',
                       transform=Affine(*transform)) as dst:
        dst.write(np.zeros((4, 5), dtype=np.float32), 1)
    assert portal._raster_format(path)[1] is False


@pytest.mark.parametrize('bad_value', [None, np.nan, np.inf, -0.01, 1.01])
def test_status_board_checks_grid_and_range(tmp_path, monkeypatch, bad_value):
    monkeypatch.setitem(portal.EXPECTED_GRID, 'shape', (4, 5))
    path = tmp_path / 'format-fixture.tif'
    a = np.zeros((4, 5), dtype=np.float32)
    if bad_value is not None:
        a[1, 1] = bad_value
    with rasterio.open(path, 'w', driver='GTiff', height=4, width=5,
                       count=1, dtype='float32', crs='EPSG:32611',
                       transform=Affine(*portal.EXPECTED_GRID['transform'])) as dst:
        dst.write(a, 1)
    digest, ok = portal._raster_format(path)
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert ok is (bad_value is None)
