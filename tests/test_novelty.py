import numpy as np
import pytest
from src.gems91.novelty import surface_check, dot_check, combine_final_checks


def test_monotonic_duplicate():
    x = np.arange(100.).reshape(10, 10)
    assert surface_check(x, x ** 2, np.ones_like(x, bool))['status'] == 'DUPLICATE'
    inverted = surface_check(x, -x, np.ones_like(x, bool))
    assert inverted['rank_correlation'] == pytest.approx(-1.0)
    assert inverted['status'] == 'DUPLICATE'


@pytest.mark.parametrize(('rank', 'dots', 'expected'), [
    ('PASS', 'PASS', 'PASS'),
    ('DUPLICATE', 'PASS', 'DUPLICATE'),
    ('PASS', 'DUPLICATE', 'DUPLICATE'),
    ('DUPLICATE', 'UNVERIFIED', 'DUPLICATE'),
    ('UNVERIFIED', 'PASS', 'UNVERIFIED'),
    ('PASS', 'UNVERIFIED', 'UNVERIFIED'),
    ('PASS', 'MALFORMED', 'UNVERIFIED'),
])
def test_final_checks_cannot_overwrite_a_failure(rank, dots, expected):
    assert combine_final_checks({'status': rank}, {'status': dots}) == expected


def test_final_instruments_are_independent_when_one_errors(monkeypatch):
    from src.gems91 import novelty

    class RankDuplicate:
        def compare(self, reference):
            return {'status': 'DUPLICATE', 'rank_correlation': 0.99}

    def bad_dots(*args):
        raise ValueError('dot instrument unavailable')

    monkeypatch.setattr(novelty, 'dot_check', bad_dots)
    rank, dots, verdict = novelty.check_final_pair(RankDuplicate(), None, None, None)
    assert rank['status'] == 'DUPLICATE' and dots['status'] == 'UNVERIFIED'
    assert verdict == 'DUPLICATE'


def test_final_dot_duplicate_survives_rank_error():
    from src.gems91 import novelty

    class BadRank:
        def compare(self, reference):
            raise ValueError('rank instrument unavailable')

    a = np.eye(5, dtype=np.float32)
    rank, dots, verdict = novelty.check_final_pair(BadRank(), a, a, np.ones_like(a, bool))
    assert rank['status'] == 'UNVERIFIED' and dots['status'] == 'DUPLICATE'
    assert verdict == 'DUPLICATE'


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
