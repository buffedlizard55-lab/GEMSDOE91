import numpy as np
import pytest
from gems91.omtj22 import fill_band


def test_fill_band_rejects_finite_nodata_and_masked_inside_but_not_outside():
    fp = np.ones((7, 8), bool)
    fp[0, 0] = False
    data = np.ones(fp.shape, np.float32)
    data[0, 0] = np.finfo(np.float32).min
    filled = fill_band(data, fp)
    assert np.isfinite(filled).all() and filled[0, 0] == 1
    data[3, 4] = np.finfo(np.float32).min
    with pytest.raises(ValueError, match='finite NoData sentinel'):
        fill_band(data, fp)
    data[3, 4] = 1
    masked = np.ma.array(data, mask=np.zeros(fp.shape, bool))
    masked.mask[3, 4] = True
    with pytest.raises(ValueError, match='masked geophysical'):
        fill_band(masked, fp)
    masked.mask[3, 4] = False
    masked.mask[0, 0] = True  # harmless outside; nearest extension is valid
    assert fill_band(masked, fp)[0, 0] == 1
