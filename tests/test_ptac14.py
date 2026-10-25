import numpy as np

from gems91.ptac14 import (
    arithmetic_probability_pool,
    bridge_concordant_crest,
    fit_predict_stage2,
    log_opinion_pool,
)


def test_probability_pools_are_bounded_and_masked():
    fp = np.array([[True, True], [True, False]])
    p1 = np.array([[0.1, 0.9], [0.4, 1.0]], dtype=np.float32)
    p2 = np.array([[0.3, 0.7], [0.6, 1.0]], dtype=np.float32)
    arithmetic = arithmetic_probability_pool(p1, p2, fp)
    opinion = log_opinion_pool(p1, p2, fp)
    assert np.isfinite(arithmetic).all() and np.isfinite(opinion).all()
    assert arithmetic.min() >= 0 and arithmetic.max() <= 1
    assert opinion.min() >= 0 and opinion.max() <= 1
    assert arithmetic[1, 1] == 0 and opinion[1, 1] == 0
    np.testing.assert_allclose(arithmetic[0, 0], 0.244, atol=1e-6)


def test_bridge_concordance_cannot_create_support_without_crest():
    fp = np.ones((5, 5), dtype=bool)
    crest = np.zeros((5, 5), dtype=np.float32)
    crest[2, 2] = 0.5
    near = np.linspace(0, 1, 25, dtype=np.float32).reshape(5, 5)
    far = near[::-1].copy()
    out = bridge_concordant_crest(crest, near, far, fp)
    assert np.count_nonzero(out) == 1
    assert 0.5 <= out[2, 2] <= 0.725


def test_stage2_train_infer_blocks_may_differ_but_width_must_match():
    rng = np.random.default_rng(4)
    fp = np.ones((20, 20), dtype=bool)
    visible = np.zeros_like(fp)
    visible[3:7, 3:7] = True
    excluded = np.zeros_like(fp)
    n = int(fp.sum())
    static = rng.normal(size=(n, 3)).astype(np.float32)
    ac_train = rng.normal(size=(n, 2)).astype(np.float32)
    ac_infer = (ac_train + 0.01).astype(np.float32)
    out, calib = fit_predict_stage2(
        train_blocks=[(static, [0, 1, 2]), (ac_train, [0, 1])],
        infer_blocks=[(static, [0, 1, 2]), (ac_infer, [0, 1])],
        visible_faults=visible,
        exclude_mask=excluded,
        footprint=fp,
        seed=7,
        neg_pos_ratio=2.0,
        chunk_size=100,
    )
    assert out.shape == fp.shape
    assert np.isfinite(out).all()
    assert 0 <= out.min() <= out.max() <= 1
    assert calib["n_features"] == 5
    assert calib["n_pos_train"] == 16
