"""Diagnostic audit must not turn incomplete evidence into a uniqueness pass."""
import json

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts import nine_site_leaders_20261028 as audit


def test_empty_overlap_is_unverified_not_zero():
    empty = np.zeros((5, 5))
    one = empty.copy(); one[2, 2] = 1
    with pytest.raises(ValueError, match='unverified'):
        audit.overlap_within(empty, one)
    with pytest.raises(ValueError, match='unverified'):
        audit.overlap_within(one, empty)


def test_constant_and_missing_spearman_are_unverified():
    assert audit.spearman_sample(np.zeros((3, 3)), np.ones((3, 3))) is None
    assert audit.spearman_sample(np.full((3, 3), np.nan), np.ones((3, 3))) is None


def test_same_shape_different_crs_or_transform_is_not_same_grid():
    a = dict(count=1, crs='EPSG:32611', shape=[5, 5], transform=[1, 0, 0, 0, -1, 0])
    for key, value in [('crs', 'EPSG:32612'), ('count', 2),
                       ('transform', [1, 0, 1, 0, -1, 0]), ('shape', [5, 6])]:
        assert not audit.same_grid(a, dict(a, **{key: value}))
    assert audit.same_grid(a, dict(a))


def test_nan_and_infinite_footprint_cannot_be_declared_valid():
    info = dict(count=1, dtype='float32', crs='EPSG:32611', res=[100., 100.])
    for arr in (np.full((3, 3), np.nan), np.array([[0, np.inf]])):
        result = audit.format_checks(arr, info)
        assert not result['finite_in_0_1']
        assert result['footprint_verified'] is False


def test_nan_nodata_serializes_as_strict_json(tmp_path):
    p = tmp_path / 'fixture.tif'
    with rasterio.open(p, 'w', driver='GTiff', height=2, width=2, count=1,
                       dtype='float32', crs='EPSG:32611', nodata=np.nan,
                       transform=from_origin(0, 200, 100, 100)) as dst:
        dst.write(np.array([[1, 0], [np.nan, 0]], dtype='float32'), 1)
    _, info = audit.load(p.read_bytes())
    assert info['nodata'] == 'nan'
    json.dumps(info, allow_nan=False)
