"""Synthetic tests; these do not run a geological experiment."""
from pathlib import Path
import json
import subprocess
import sys

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from scripts.audit_feature_nodata import audit


def write(path, array, nodata=None, crs='EPSG:32611'):
    array = np.asarray(array, dtype=np.float32)
    with rasterio.open(path, 'w', driver='GTiff', height=array.shape[0], width=array.shape[1],
                       count=1, dtype='float32', crs=crs, transform=from_origin(0, 400, 100, 100),
                       nodata=nodata) as dst:
        dst.write(array, 1)


def fixture(tmp_path):
    sample = np.zeros((4, 5), np.float32)
    sample[0, 0] = np.nan
    sample_path = tmp_path / 'sample.tif'
    write(sample_path, sample, np.nan)
    return sample_path, sample


def test_declared_finite_nodata_inside_is_not_a_measurement(tmp_path):
    sample, _ = fixture(tmp_path)
    feature = np.arange(20, dtype=np.float32).reshape(4, 5)
    feature[0, 0] = np.finfo(np.float32).min  # outside footprint: ignored
    feature[2, 3] = np.finfo(np.float32).min  # within: fatal
    path = tmp_path / 'features.tif'
    write(path, feature, float(np.finfo(np.float32).min))
    report = audit(path, sample, [1])
    b = report['bands'][0]
    assert report['status'] == b['status'] == 'FAIL_CLOSED'
    assert b['footprint_pixels'] == 19 and b['masked_or_nonfinite_inside'] == 1
    assert b['finite_extreme_inside'] == 1 and b['usable_pixels'] == 18
    assert b['usable_min'] == 1 and b['usable_max'] == 19


def test_undeclared_extreme_and_nonfinite_are_caught(tmp_path):
    sample, _ = fixture(tmp_path)
    feature = np.ones((4, 5), np.float32)
    feature[1, 1] = np.finfo(np.float32).min
    feature[1, 2] = np.nan
    path = tmp_path / 'features.tif'
    write(path, feature)
    b = audit(path, sample, [1])['bands'][0]
    assert b['masked_or_nonfinite_inside'] == 1 and b['finite_extreme_inside'] == 1
    assert b['usable_pixels'] == 17 and b['status'] == 'FAIL_CLOSED'


def test_outside_nodata_is_allowed_and_grid_mismatch_rejected(tmp_path):
    sample, _ = fixture(tmp_path)
    feature = np.ones((4, 5), np.float32)
    feature[0, 0] = np.finfo(np.float32).min
    path = tmp_path / 'features.tif'
    write(path, feature, float(np.finfo(np.float32).min))
    assert audit(path, sample, [1])['status'] == 'PASS'
    write(path, feature, crs='EPSG:4326')
    with pytest.raises(ValueError, match='grid does not match'):
        audit(path, sample, [1])
    with pytest.raises(ValueError, match='bands must be unique'):
        audit(path, sample, [1, 1])


def test_cli_fails_closed_on_unpinned_data(tmp_path):
    sample, _ = fixture(tmp_path)
    path = tmp_path / 'features.tif'
    write(path, np.ones((4, 5)))
    script = Path(__file__).resolve().parents[1] / 'scripts/audit_feature_nodata.py'
    args = [sys.executable, str(script), '--features', str(path), '--sample', str(sample), '--bands', '1']
    denied = subprocess.run(args, capture_output=True, text=True, check=False)
    assert denied.returncode == 1 and json.loads(denied.stdout)['status'] == 'BLOCKED'
    permitted = subprocess.run(args + ['--allow-unpinned'], capture_output=True, text=True, check=False)
    assert permitted.returncode == 0 and json.loads(permitted.stdout)['status'] == 'PASS'
