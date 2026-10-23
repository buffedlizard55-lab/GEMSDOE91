"""Unit tests for the GDR-derived prior and the CONCENTRATION axis helpers.

No competition data is needed: the CSV is synthesised in-memory, the grids are 12x14.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from gems91 import metric, prior as priors  # noqa: E402

CSV_BODY = """layer,name,thermalclass,row,col,utm_x,utm_y,dist_known_fault_px
spring_features_20220808,A Hot,Hot,2,3,0,0,1.0
spring_features_20220808,A Hot again,Hot,2,3,0,0,1.0
well_features_20220808,B Warm,,,9,0,0,1.0
well_features_20220808,B Warm dup,Warm,9,10,0,0,1.0
well_features_20220808,C Cold,Cold,5,5,0,0,1.0
well_features_20220808,D unknown,NULL,6,6,0,0,1.0
well_features_20220808,E empty,,7,7,0,0,1.0
"""


def _module():
    spec = importlib.util.spec_from_file_location("build_conc", ROOT / "scripts" / "build_concentration.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_read_features_dedupes_cells_and_keeps_only_thermal():
    feats = priors.read_features(_write(CSV_BODY))
    assert feats["n_rows"] == 7
    assert feats["n_thermal_rows"] == 3           # two Hot rows + one Warm row
    cells = {tuple(c) for c in feats["cells"].tolist()}
    assert cells == {(2, 3), (9, 10)}             # duplicates collapse; cold/NULL dropped


def test_distance_prior_is_monotone_bounded_and_deterministic():
    footprint = np.ones((12, 14), dtype=bool)
    footprint[:2, :] = False                      # a hole outside the "footprint"
    cells = np.array([[6, 7]])
    a = priors.distance_prior(footprint.shape, cells, footprint, sigma_px=3.0)
    b = priors.distance_prior(footprint.shape, cells, footprint, sigma_px=3.0)
    assert np.isfinite(a[6, 7]) and a[6, 7] == pytest.approx(1.0, abs=1e-6)
    assert np.isnan(a[~footprint]).all()
    assert np.all(np.isfinite(a[footprint]))
    # farther from the feature is never a higher prior
    assert a[6, 6] > a[6, 4] > a[6, 0]
    assert priors.array_digest(a) == priors.array_digest(b)


def test_distance_prior_refuses_an_empty_feature_set():
    footprint = np.ones((6, 6), dtype=bool)
    with pytest.raises(ValueError):
        priors.distance_prior((6, 6), np.zeros((0, 2), dtype=np.int64), footprint)


def test_keep_remote_respects_the_catalogue_floor():
    cells = np.array([[1, 1], [1, 5], [5, 5]])
    dcat = np.full((8, 8), 20.0)
    dcat[1, 1] = 2.0
    kept = priors.keep_remote(cells, dcat, min_px=8.0)
    assert {tuple(c) for c in kept.tolist()} == {(1, 5), (5, 5)}


def test_fast_dti_parts_match_the_reference_implementation():
    mod = _module()
    rng = np.random.default_rng(0)
    pred = (rng.random((24, 26)) > 0.985).astype(np.float32)
    truth = (rng.random((24, 26)) > 0.97)
    ref = metric.components(pred.astype(np.float64), truth)
    fast = mod.dti_parts_f32(pred, truth)
    assert fast.n_truth == ref.n_truth
    for got, want in ((fast.T, ref.T), (fast.S, ref.S), (fast.M, ref.M)):
        assert got == pytest.approx(want, rel=1e-5, abs=1e-5)
    assert fast.dti() == pytest.approx(ref.dti(), rel=1e-5)


def test_prediction_is_labelled_model_and_scales_with_the_effect():
    mod = _module()
    d, band, basis = mod.prediction(0.04, 0.048, -0.006, -0.022)
    assert d > 0
    assert band[0] == -0.022            # the worse measured alternative sets the floor
    assert band[1] == pytest.approx(3 * d, abs=1e-3)
    assert "surrogate-truth rel change +0.200" in basis
    assert "noise-truth -0.0060" in basis and "lineage-mask -0.0220" in basis
    # a tenth of the span times a 20 % relative improvement
    assert d == pytest.approx(round(0.1 * mod.LIVE_SPAN * 0.2, 4))
    flipped, _, _ = mod.prediction(0.04, 0.032, -0.006, -0.022)
    assert flipped < 0
    zero, band0, _ = mod.prediction(0.0, 0.5, 0.0, 0.0, "undefined")
    assert zero == 0.0 and band0 == [0.0, mod.BAND]


def test_arms_are_matched_on_dose_and_seed():
    mod = _module()
    assert {a["block_px"] for a in mod.ARMS.values()} == {10, 25}
    assert len({a["prior"] for a in mod.ARMS.values()}) == 2
    assert mod.FRAC == 0.10 and 0 < mod.MIN_GAP_PX <= 3.0
    assert mod.PARENT_MIN_SEP_PX == 2.0   # R0 has no dot pair closer than 2 px


def _write(body: str) -> Path:
    p = Path(__file__).parent / "_tmp" / "gdr_snippet.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8-sig")
    return p
