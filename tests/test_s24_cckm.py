"""Synthetic tests for the S24-CCKM masked kurtosis instrument.

These test the *instrument* on invented fields, never a competition claim:
no pinned data is required and nothing here is a score.
"""
import numpy as np
import pytest

from gems91 import cckm24


def _fields(seed=7):
    rng = np.random.default_rng(seed)
    h, w = 140, 180
    fp = np.ones((h, w), bool)
    # Left: Gaussian texture (excess kurtosis ~ 0). Right: sparse spikes
    # (heavy tails, high kurtosis). Boundary at x=90.
    tmi = rng.normal(0.0, 1.0, (h, w))
    spikes = (rng.random((h, w)) < 0.02) * rng.choice([-12.0, 12.0], (h, w))
    tmi[:, 90:] = spikes[:, 90:] + rng.normal(0.0, 0.1, (h, w - 90))
    # Gravity ramp along x -> gradient normal is +/- x everywhere.
    gravity = np.tile(np.linspace(-10.0, 10.0, w), (h, 1))
    return tmi, gravity, fp


def test_contrast_peaks_at_texture_boundary():
    tmi, gravity, fp = _fields()
    feats, support, meta = cckm24.features(tmi, gravity, fp)
    contrast = feats["kurtosis_contrast_rank"]
    rows = slice(30, 110)
    near = contrast[rows, 78:102][support[rows, 78:102]].mean()
    far_left = contrast[rows, 20:50][support[rows, 20:50]].mean()
    far_right = contrast[rows, 130:160][support[rows, 130:160]].mean()
    assert near > far_left
    assert near > far_right
    assert meta["surface_support_pixels"] > 0


def test_outputs_finite_in_range_and_zero_outside_footprint():
    tmi, gravity, fp = _fields()
    fp[:10, :] = False
    feats, support, _ = cckm24.features(tmi, gravity, fp)
    for arr in feats.values():
        assert np.isfinite(arr).all()
    surf = feats["surface"]
    assert surf.min() >= 0.0 and surf.max() <= 1.0
    assert (surf[~fp] == 0).all()
    assert not support[~fp].any()


def test_sentinel_is_excluded_not_averaged():
    tmi, gravity, fp = _fields()
    poisoned = tmi.copy()
    poisoned[::17, ::13] = -3.4028234663852886e38
    gravity_p = gravity.copy()
    gravity_p[::23, ::11] = np.nan
    _, _, clean_meta = cckm24.features(tmi, gravity, fp)
    feats, support, meta = cckm24.features(poisoned, gravity_p, fp)
    for arr in feats.values():
        assert np.isfinite(arr).all()
    # A sentinel read as data would dominate any statistic. Excluding ~0.5%
    # poisoned cells must leave the median windowed kurtosis close to clean.
    p50_clean = clean_meta["kurtosis_raw_percentiles_on_support"]["p50"]
    p50_poisoned = meta["kurtosis_raw_percentiles_on_support"]["p50"]
    assert abs(p50_poisoned - p50_clean) < 0.35 * (abs(p50_clean) + 1.0)
    assert meta["tmi_invalid_inside_footprint"] > 0
    assert meta["gravity_invalid_inside_footprint"] > 0
    assert (feats["tmi_input"][::17, ::13] == 0).all()


def test_constant_field_has_no_support():
    fp = np.ones((60, 60), bool)
    tmi = np.full((60, 60), 3.0)
    gravity = np.tile(np.linspace(0, 1, 60), (60, 1))
    feats, support, _ = cckm24.features(tmi, gravity, fp)
    assert not support.any()
    assert (feats["surface"] == 0).all()


def test_shape_mismatch_rejected():
    with pytest.raises(ValueError):
        cckm24.features(np.zeros((10, 10)), np.zeros((10, 9)), np.ones((10, 10), bool))
