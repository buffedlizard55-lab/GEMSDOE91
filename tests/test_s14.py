"""S14-LSRG tests: new-feature schema, gate math, evaluator v1.1 semantics,
and the delivered run card / raster contract (no competition data needed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems91 import s14 as S14  # noqa: E402


def test_s14_feature_names_unique_and_prefixed():
    names = S14.S14_FEATURE_NAMES
    assert len(names) == 23 and len(set(names)) == 23
    assert all(n.startswith("s14_") for n in names)
    assert "s14_lid_step_x_coh" in names and "s14_rad_log_th_k" in names


def test_rank_pct_ties_and_bounds():
    r = S14.rank_pct_fp(np.array([3.0, 1.0, 2.0, 2.0], dtype=np.float32))
    assert r.min() == 0.0 and r.max() == 1.0
    assert r[2] == r[3] == pytest.approx(0.5)


def test_corroboration_gate_scales_down_only():
    fp = np.ones((4, 4), bool)
    prob = np.full((4, 4), 0.5, np.float32)
    fam = [np.arange(16, dtype=np.float32).reshape(4, 4)]
    out = S14.corroboration_gate(prob, fam, fp, floor=0.3)
    assert out.min() >= 0.3 * 0.5 - 1e-6 and out.max() <= 0.5 + 1e-6
    assert out[3, 3] >= out[0, 0]  # stronger family support -> less damping


def test_evaluator_v11_nohalo_vs_v10():
    """A dot 2 px from a withheld fault (inside the 1 km buffer) earns kernel
    credit under v1.1-nohalo but is deleted under v1.0 (IR-91-S14-01)."""
    import evaluate_holdout as EH

    fp = np.ones((60, 60), bool)
    cat = np.zeros((60, 60), np.float32)
    cat[8:16, 8] = 1.0     # NW
    cat[8:16, 48] = 1.0    # NE
    cat[44:52, 8] = 1.0    # SW
    cat[44:52, 48] = 1.0   # SE
    folds = EH.build_segment_buffered_folds(cat, fp, bridge_px=3, buffer_px=10.0)
    pred = {}
    for f in folds:
        p = np.zeros((60, 60), np.float32)
        ys, xs = np.nonzero(f.withheld_faults)
        if ys.size:
            p[ys[0], xs[0] + 2] = 1.0  # near-miss dot inside buffer halo
        pred[f.fold_id] = p
    v10 = EH.score_pooled_holdout(pred, folds, fp, n_boot=10, mask_buffer_predictions=True)
    v11 = EH.score_pooled_holdout(pred, folds, fp, n_boot=10)
    assert v10["evaluator_version"] == EH.EVALUATOR_VERSION
    assert v11["evaluator_version"] == EH.EVALUATOR_VERSION_V11
    assert v10["holdout_dti"] == 0.0
    assert v11["holdout_dti"] > 0.0


def test_s14_run_card_contract():
    card_p = ROOT / "docs/run-card-S14.json"
    if not card_p.is_file():
        pytest.skip("S14 run card not present")
    card = json.loads(card_p.read_text())
    assert card["organizer_confirmed"] is None
    assert card["submission_ready"] is False
    assert len(card["note"]) <= 140
    assert card["holdout_dti"]["label"] == "HOLDOUT-DTI"
    assert card["holdout_dti"]["withheld_positives"] == 60988
    sys.path.insert(0, str(ROOT / "src"))
    from gems91.readiness import gates, submission_ready
    g = gates(card)
    assert g["format"] is True and g["canary"] is True
    assert submission_ready(card) is False  # fail-closed until human selector


def test_s14_ff_raster_contract():
    rasterio = pytest.importorskip("rasterio")
    tif = ROOT / "docs/downloads/gems91-s14-lsrg-ff-20261025T004500Z-1fcf17ee-zeros.tif"
    if not tif.is_file():
        pytest.skip("S14-FF raster not present")
    import hashlib
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == \
        "09f9ca2acdca7c6616df329aad7d0c8d73dec2626b04e6d8619d2b1452ea7359"
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        assert ds.count == 1 and ds.dtypes[0] == "float32"
        assert str(ds.crs) == "EPSG:32611" and ds.shape == (3730, 3292)
        assert ds.nodata is None
    assert np.isfinite(a).all() and a.min() >= 0.0 and a.max() <= 1.0
    assert int((a > 0).sum()) == 37654 and float(a.sum()) == 37654.0
