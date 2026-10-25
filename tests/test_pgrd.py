"""Analytic/engineering fixtures, not extra geological experiments."""
import inspect
import numpy as np
import pytest

from gems91 import pgrd


def test_constructor_cannot_read_faults_or_prior_submissions():
    assert list(inspect.signature(pgrd.features).parameters) == ['rtp', 'gravity', 'footprint']


def test_bandpass_integrates_a_single_fourier_mode_by_inverse_wavenumber():
    n, mode = 128, 8
    x = np.arange(n)[None, :]
    field = np.broadcast_to(np.cos(2 * np.pi * mode * x / n), (64, n)).astype(np.float32)
    raw = pgrd.bandpass(field, pad=0)
    integrated = pgrd.bandpass(field, integrate=True, pad=0)
    np.testing.assert_allclose(integrated, raw / (2 * np.pi * mode / n), rtol=3e-5, atol=2e-6)
    assert abs(float(integrated.mean())) < 1e-6


def test_dc_and_constant_fields_do_not_produce_a_fake_fault_surface():
    fp = np.ones((40, 48), bool)
    fields = pgrd.features(np.ones(fp.shape), 2 * np.ones(fp.shape), fp)
    assert not fields['surface'].any()
    np.testing.assert_allclose(pgrd.bandpass(np.ones(fp.shape), integrate=True), 0, atol=1e-6)


def test_feature_outputs_are_finite_normalized_and_footprint_bounded():
    y, x = np.mgrid[:65, :65]
    fp = np.ones((65, 65), bool); fp[:4] = False
    m = np.tanh((x - 30) / 3).astype(np.float32)
    g = (np.tanh((x - 32) / 4) + .2 * np.sin(y / 3)).astype(np.float32)
    m[20, 20] = -3.4e38
    fields = pgrd.features(m, g, fp)
    assert len(fields) == 16
    assert fields['surface'].max() > 0
    assert fields['input_support'][20, 20] == 0
    for field in fields.values():
        assert field.dtype == np.float32
        assert np.isfinite(field).all()
        assert (field >= 0).all() and (field <= 1).all()
        assert (field[~fp] == 0).all()


def test_same_source_transfer_has_near_perfect_local_correlation():
    rng = np.random.default_rng(16)
    p = rng.normal(size=(80, 80)).astype(np.float32)
    residual, discordance, slope = pgrd.local_transfer(p, 2 * p + 4, np.ones(p.shape, bool), sigma=5)
    assert float(discordance.mean()) < 1e-5
    assert np.mean(np.abs(residual)) < .1
    assert 1.85 < float(np.median(slope)) < 2.0


@pytest.mark.parametrize('kwargs', [{'sigmas': (3, 2)}, {'pad': -1}])
def test_bad_operator_settings_fail_closed(kwargs):
    with pytest.raises(ValueError):
        pgrd.bandpass(np.ones((12, 12)), **kwargs)


def test_missing_input_is_not_fabricated():
    with pytest.raises(ValueError):
        pgrd.features(np.full((12, 12), np.nan), np.ones((12, 12)), np.ones((12, 12), bool))
