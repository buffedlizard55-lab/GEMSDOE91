"""Independent footprint layer reuses, but does not rewrite, the historical checker."""
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from scripts import verify_priority_nine as audit


def test_footprint_checks_nonfinite_outside_positive_and_grid(tmp_path):
    path = tmp_path / 'fixture.tif'
    footprint = np.zeros((5, 5), dtype=bool)
    footprint[1:4, 1:4] = True
    grid = dict(crs='EPSG:32611', shape=[5, 5], transform=[100., 0., 0., 0., -100., 500.])
    def write(a):
        with rasterio.open(path, 'w', driver='GTiff', height=5, width=5, count=1,
                           dtype='float32', crs=grid['crs'],
                           transform=from_origin(0, 500, 100, 100)) as dst:
            dst.write(a.astype('float32'), 1)
    a = np.zeros((5, 5), dtype=np.float32); a[2, 2] = 1
    a[0, 0] = np.nan; write(a)
    points, meta = audit.checked_dots(path, footprint, grid)
    assert len(points) == 1 and meta['footprint_checked']
    assert meta['positive_outside_footprint'] == 0
    a[0, 0] = 1; write(a)
    with pytest.raises(ValueError, match='outside footprint'):
        audit.checked_dots(path, footprint, grid)
    a[0, 0] = 0; a[1, 1] = np.nan; write(a)
    with pytest.raises(ValueError, match='inside footprint'):
        audit.checked_dots(path, footprint, grid)
    a[1, 1] = 0; write(a)
    with pytest.raises(ValueError, match='grid mismatch'):
        audit.checked_dots(path, footprint, dict(grid, crs='EPSG:32612'))
