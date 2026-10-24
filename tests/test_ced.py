"""Scientific/infrastructure checks use synthetic data, never hidden truth."""
import hashlib
import inspect
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from gems91 import ced, novelty
from vendor.gems57 import evaluate_holdout as ev, metric, spatial
from vendor.gems57.submission_writer import write_submission

ROOT = Path(__file__).resolve().parents[1]


def test_shared_template_is_unmodified():
    manifest = json.loads((ROOT / 'registry/template_pin.json').read_text())
    for name, digest in manifest['sha256'].items():
        assert hashlib.sha256((ROOT / 'vendor/gems57' / name).read_bytes()).hexdigest() == digest


def test_exact_rank_percentiles_and_constant():
    a = np.array([[1., 3.], [3., 5.]])
    np.testing.assert_allclose(ced.percentiles(a, np.ones_like(a, bool)), [[.2, .5], [.5, .8]])
    assert np.all(ced.percentiles(np.ones((5, 5)), np.ones((5, 5), bool)) == .5)


def test_nearest_fill_does_not_treat_sentinels_as_data():
    a = np.ones((12, 12), np.float32); a[0, 0] = -3.4e38
    result = ced.fill_input(a, np.ones_like(a, bool))
    assert np.isfinite(result).all()
    assert np.ptp(result) == 0
    with pytest.raises(ValueError): ced.fill_input(np.full((5, 5), np.nan), np.ones((5, 5), bool))


def test_centroid_shift_has_correct_axis_and_sign():
    a = np.zeros((45, 45), np.float32); a[20, 20] = 1
    sx, sy = ced.centroid_shift(a)
    assert sx[22, 19] == pytest.approx(1.0, abs=1e-6)
    assert sy[22, 19] == pytest.approx(-2.0, abs=1e-6)


def test_feature_constructor_cannot_receive_catalogue_or_parent():
    assert list(inspect.signature(ced.features).parameters) == ['magnetic', 'gravity', 'footprint']
    y, x = np.mgrid[:32, :40]
    fp = np.ones((32, 40), bool); fp[:2] = False
    fields = ced.features(np.tanh((x-20)/3).astype(np.float32),
                          np.tanh((x-22)/5).astype(np.float32), fp)
    for name, a in fields.items():
        assert a.dtype == np.float32
        assert np.isfinite(a).all()
        assert np.all(a[~fp] == 0)
        if not name.startswith('signed_'): assert a.min() >= 0 and a.max() <= 1


def test_feature_alone_canary_catches_direct_and_inverse_labels():
    truth = np.zeros((15, 15), bool); truth[5, 5] = True
    mask = np.ones_like(truth)
    for a in (truth.astype(float), ~truth):
        result = ced.auc_canary(a, truth, mask)
        assert result['status'] == 'LEAKAGE_SUSPECTED'
        assert result['symmetric_auc'] == 1
    assert ced.auc_canary(np.ones_like(truth), truth, mask)['auc'] == .5


def test_placement_is_new_deterministic_and_strictly_separated():
    s = np.ones((40, 40), np.float32); e = np.ones_like(s, bool); e[0, 0] = False
    dots = ced.place(s, e, 40)
    np.testing.assert_equal(dots, ced.place(s, e, 40))
    assert dots.sum() == 40 and not dots[0, 0] and dots[0, 1]
    distances = cKDTree(np.argwhere(dots)).query(np.argwhere(dots), k=2)[0][:, 1]
    assert distances.min() > 3
    with pytest.raises(ValueError, match='capacity'):
        ced.place(s, e, 1600)


@pytest.mark.parametrize('binary', [False, True])
def test_cached_spearman_is_exact(binary):
    rng = np.random.default_rng(91)
    a = rng.normal(size=(30, 30)); b = rng.normal(size=a.shape)
    if binary: b = b > 0
    fp = rng.random(a.shape) > .1
    result = novelty.SurfaceProbe(a, fp).compare(b)
    assert result['rank_correlation'] == pytest.approx(spearmanr(a[fp], b[fp]).statistic, abs=1e-12)


def test_dense_soft_registry_has_no_threshold_exemption():
    p = np.zeros((20, 20), bool); p[10, 10] = True
    reference = np.full(p.shape, .001)
    result = novelty.dot_check(p, reference, np.ones_like(p))
    assert result['status'] == 'DUPLICATE'
    assert result['overlap_within_3px'] == 1


def test_spatial_folds_hide_whole_components_and_do_not_shape_domain_from_truth():
    cat = np.zeros((100, 100), bool); cat[40:65, 40] = True; cat[15:20, 80] = True
    eligible = np.ones_like(cat)
    for f in spatial.folds(cat, eligible, buffer_px=3):
        assert not (f['visible'] & f['held_all']).any()
        # First component crosses the fixed north/south boundary and must vanish
        # completely from visibility in each affected fold.
        if f['truth'][40:65, 40].any(): assert not f['visible'][40:65, 40].any()
        assert not (f['train'] & f['region']).any()
        np.testing.assert_equal(f['region'], f['quadrant'] & eligible)
        assert f['receipt']['shared_train_truth_components'] == 0


def test_canonical_evaluator_matches_literal_oracle_and_masks_exact_pixels():
    p = np.zeros((15, 20)); t = np.zeros_like(p, bool); t[5, 5] = True; t[10, 10] = True
    p[5, 5] = .7; p[8, 10] = 1; p[1, 1] = 1
    known = np.zeros_like(t); known[1, 1] = True
    f = dict(region=np.ones_like(t), visible=known, truth=t)
    got, terms = ev.evaluate(p, f, np.ones_like(t), block_side=5)
    p[known] = 0
    expected = metric.dti_bruteforce(p, t)
    assert got['dti'] == pytest.approx(expected['dti'])
    assert terms[:, 3].sum() == 2
    summary = ev.pooled_summary({'ced': terms, 'control': terms}, candidate='ced', draws=30)
    assert summary['paired_differences']['control']['delta'] == 0
    assert summary['paired_differences']['control']['ci95'] == [0, 0]


@pytest.mark.parametrize('value', [np.nan, np.inf, -1., 1.01])
def test_shared_writer_refuses_invalid_output_without_artifacts(tmp_path, value):
    p = np.zeros((5, 5)); p[0, 0] = value
    target = tmp_path / 'invalid.tif'
    with pytest.raises(ValueError):
        write_submission(target, p, tmp_path / 'sample.tif', np.ones_like(p, bool),
                         note='Research only', name='test')
    assert not list(tmp_path.iterdir())


def test_shared_metric_dense_perfect_is_one_not_greater():
    p = np.zeros((20, 20)); p[:, 10] = 1
    assert metric.dti_exact(p, p.astype(bool))['dti'] == pytest.approx(1)
