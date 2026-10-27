"""Synthetic checks for the concurrent nine-site diagnostic; no experiments."""
import hashlib

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from gems91.novelty import dot_check
from scripts import verify_nine_site_leaders as checker


def test_euclidean_distance_matches_shared_novelty_gate_and_excludes_diagonal_corner():
    pred = np.zeros((8, 8), np.float32)
    ref = np.zeros_like(pred)
    pred[0, 3] = pred[3, 3] = 1
    ref[0, 0] = 1
    mask = np.ones_like(pred, dtype=bool)
    result = checker.within3(np.argwhere(pred), np.argwhere(ref))
    assert result == .5  # (0,3) is in; (3,3) is out under Euclidean distance
    assert result == dot_check(pred, ref, mask)['overlap_within_3px']


def test_empty_support_cannot_be_mistaken_for_a_pass():
    with pytest.raises(ValueError, match='unverified'):
        checker.within3(np.empty((0, 2)), np.array([[0, 0]]))


def test_binary_input_is_required_and_nan_is_not_a_dot(tmp_path):
    path = tmp_path / 'dot.tif'
    def write(a):
        with rasterio.open(path, 'w', driver='GTiff', height=2, width=2, count=1,
                           dtype='float32', crs='EPSG:32611',
                           transform=from_origin(0, 200, 100, 100)) as dst:
            dst.write(np.array(a, np.float32), 1)
    write([[1, 0], [np.nan, 0]])
    points, meta = checker.dots_of(path)
    assert points.tolist() == [[0, 0]] and meta['nan_pixels'] == 1
    write([[1, .2], [0, 0]])
    with pytest.raises(ValueError, match='binary'):
        checker.dots_of(path)
    write([[1, np.inf], [0, 0]])
    with pytest.raises(ValueError, match='infinite'):
        checker.dots_of(path)


def test_cached_blob_must_match_tree_identity(tmp_path, monkeypatch):
    content = b'correct historical blob'
    sha = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
    entry = {'path': 'docs/leader.tif', 'sha': sha}
    dest = tmp_path / 'GEMSDOE24__leader.tif'
    dest.write_bytes(content)
    monkeypatch.setattr(checker, 'gh', lambda *_: pytest.fail('cache should be used'))
    assert checker.fetch('GEMSDOE24', entry, tmp_path) == dest
    dest.write_bytes(b'stale or tampered')
    with pytest.raises(ValueError, match='differs from the selected tree'):
        checker.fetch('GEMSDOE24', entry, tmp_path)


def test_truncated_source_tree_is_not_a_complete_inventory(monkeypatch):
    monkeypatch.setattr(checker, 'gh', lambda *_: b'{"truncated": true, "tree": []}')
    with pytest.raises(ValueError, match='truncated'):
        checker.find_tif('GEMSDOE24', 'hash', '-nan')
