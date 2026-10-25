"""Unit tests for S15 HCPA feature extraction and modeling."""
from pathlib import Path
import numpy as np
import pytest

from gems91 import hcpa_s15 as S15

DATA = Path("data")


def test_clean_band():
    fp = np.zeros((10, 10), dtype=bool)
    fp[2:8, 2:8] = True
    arr = np.full((10, 10), -3.4e38, dtype=np.float32)
    arr[3:7, 3:7] = 42.0
    arr[4, 4] = np.nan
    cleaned = S15.clean_band(arr, fp)
    assert np.all(np.isfinite(cleaned))
    assert cleaned[~fp].max() == 0.0
    assert cleaned[4, 4] == 0.0
    assert cleaned[3, 3] == 42.0


def test_hcpa_feature_names():
    assert len(S15.HCPA_FEATURE_NAMES) == 13
    assert "hcpa_cond_depth_ratio" in S15.HCPA_FEATURE_NAMES
    assert "hcpa_slip_tendency" in S15.HCPA_FEATURE_NAMES
    assert "hcpa_coulomb_crit_permeability" in S15.HCPA_FEATURE_NAMES


@pytest.mark.skipif(not Path("data/official/sample_submission.tif").is_file(), reason="data not restored")
def test_build_or_load_s15_memmap(tmp_path):
    import rasterio
    with rasterio.open("data/official/sample_submission.tif") as ds:
        fp = np.isfinite(ds.read(1))
    mmap, names, meta = S15.build_or_load_s15_feature_memmap(
        features_tif=DATA / "bridge/gems-geodawn-numerical-features.tif",
        gdr_csv=DATA / "external/gdr_wellspring_in_footprint.csv",
        lidar_tif=DATA / "external/lidar_scarp_features_u8.tif",
        rad_tif=DATA / "external/geodawn_rad_u8.tif",
        footprint=fp,
        cache_dir=tmp_path,
    )
    assert mmap.shape == (int(fp.sum()), 13)
    assert names == S15.HCPA_FEATURE_NAMES
    assert np.all(np.isfinite(mmap))
