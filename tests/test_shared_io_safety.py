"""Low-level encoder must not repair invalid model output."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from gems91 import io


@pytest.fixture
def template(tmp_path):
    p = tmp_path / 'template.tif'
    arr = np.zeros((8, 8), dtype='float32'); arr[0, :] = np.nan
    with rasterio.open(p, 'w', driver='GTiff', count=1, height=8, width=8,
                       dtype='float32', crs='EPSG:32611', nodata=np.nan,
                       transform=from_origin(0, 800, 100, 100)) as dst:
        dst.write(arr, 1)
    return p


@pytest.mark.parametrize('value', [np.nan, np.inf, -np.inf, -1., 1.000000000001, 1e-100])
@pytest.mark.parametrize('encoding', ['nan', 'zeros'])
def test_invalid_values_never_written(template, tmp_path, value, encoding):
    a = np.zeros((8, 8), dtype='float64'); a[2, 2] = value
    dest = tmp_path / 'bad.tif'
    with pytest.raises(ValueError):
        io.write_float32(dest, a, encoding=encoding, template=template)
    assert not dest.exists()


def test_only_outside_nan_can_be_converted_and_support_preserved(template, tmp_path):
    a = np.zeros((8, 8), dtype='float64'); a[0, :] = np.nan; a[3, 3] = 1
    for encoding in ('nan', 'zeros'):
        dest = tmp_path / f'{encoding}.tif'
        io.write_float32(dest, a, encoding=encoding, template=template)
        with rasterio.open(dest) as src:
            out = src.read(1)
        assert out[3, 3] == 1
        assert np.isnan(out[0]).all() if encoding == 'nan' else (out[0] == 0).all()


def test_masked_prediction_is_not_silently_unmasked(template, tmp_path):
    a = np.ma.array(np.zeros((8, 8), dtype=np.float32), mask=np.eye(8, dtype=bool))
    with pytest.raises(ValueError, match='masked'):
        io.write_float32(tmp_path / 'masked.tif', a, encoding='zeros', template=template)
    assert not (tmp_path / 'masked.tif').exists()
