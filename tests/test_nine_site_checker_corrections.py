"""Regression tests for the nine-site source audit, using synthetic points."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from scripts import verify_nine_site_leaders as checker


def test_optional_candidate_does_not_change_leader_to_leader_maximum():
    peers = {f'{site} -> {other}': .25
             for site in checker.LEADERS for other in checker.LEADERS if site != other}
    peers['GEMSDOE24 -> CANDIDATE:dense.tif'] = 1.0
    assert checker.maximum_peer_overlaps(peers)['GEMSDOE24'] == .25
    del peers['GEMSDOE24 -> GEMSDOE25']
    with pytest.raises(KeyError):
        checker.maximum_peer_overlaps(peers)


def test_overlap_receipt_keeps_precision_at_strict_boundary():
    near = np.column_stack([np.arange(7001) * 10, np.zeros(7001)])
    far = np.column_stack([np.arange(2999) * 10, np.full(2999, 100)])
    fraction = checker.within3(np.vstack([near, far]), near)
    assert fraction == 7001 / 10000
    assert fraction > .70


def test_nan_metadata_is_json_safe(tmp_path):
    path = tmp_path / 'leader.tif'
    with rasterio.open(path, 'w', driver='GTiff', height=2, width=2,
                       count=1, dtype='float32', crs='EPSG:32611',
                       transform=from_origin(0, 200, 100, 100), nodata=float('nan')) as dst:
        dst.write(np.array([[1, 0], [np.nan, 0]], np.float32), 1)
    _, meta = checker.dots_of(path)
    assert meta['nodata'] == 'nan'
    import json
    json.dumps(meta, allow_nan=False)
