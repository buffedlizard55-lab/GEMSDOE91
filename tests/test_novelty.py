import numpy as np
import pytest
from src.gems91.novelty import surface_check, dot_check


def test_shared_surface_measurement_uses_absolute_rank_correlation():
    x = np.arange(100.).reshape(10, 10)
    assert surface_check(x, x ** 2, np.ones_like(x, bool))['status'] == 'DUPLICATE'
    # The pinned shared gate treats |rho| > 0.90 as a duplicate in either direction.
    assert surface_check(x, -x, np.ones_like(x, bool))['status'] == 'DUPLICATE'


def test_constant_not_pass():
    x = np.ones((4, 4))
    assert surface_check(x, x, x.astype(bool))['status'] == 'UNVERIFIED'


def test_inclusive_distance_strict_overlap():
    a = np.zeros((20, 60)); b = a.copy(); mask = np.ones_like(a, bool)
    a[5, ::6] = 1
    b[8, :42:6] = 1  # exactly 70% at exactly 3px
    assert dot_check(a, b, mask)['status'] == 'PASS'
    b[8, 42] = 1
    assert dot_check(a, b, mask)['status'] == 'DUPLICATE'


def test_invalid_and_empty():
    a = np.zeros((5, 5)); mask = np.ones_like(a, bool)
    assert dot_check(a, a, mask)['status'] == 'UNVERIFIED'
    a[0, 0] = np.nan
    with pytest.raises(ValueError):
        surface_check(a, a, mask)
    with pytest.raises(ValueError):
        dot_check(np.ones((2, 2)), a, mask)
    with pytest.raises(ValueError):
        surface_check(a, a, mask.astype(int))


def test_outside_footprint_ignored():
    a = np.arange(25.).reshape(5, 5); b = a.copy()
    mask = np.ones_like(a, bool); mask[0] = False
    b[0] = np.nan
    assert surface_check(a, b, mask)['status'] == 'DUPLICATE'
