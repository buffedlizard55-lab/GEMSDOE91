"""MTD91 unit checks — no holdout, no network."""
import json
from pathlib import Path

import numpy as np
from gems91.mtd import features_from_bands, surface_e1, emit_dots


ROOT = Path(__file__).resolve().parents[1]


def test_mtd_run_card_does_not_replace_shared_h91_page_data():
    shared = json.loads((ROOT / 'docs/data/run_card.json').read_text())
    evidence = json.loads((ROOT / 'evidence/run_card.json').read_text())
    mtd = json.loads((ROOT / 'docs/run-card-MTD91.json').read_text())
    assert shared == evidence
    assert mtd['run_id'] == 'MTD91-e1-20261024'
    assert mtd['verdict'] == 'negative'
    assert mtd['ok_to_submit'] is False


def test_features_finite_and_ranged():
    rng = np.random.default_rng(91)
    h, w = 64, 64
    fp = np.ones((h, w), dtype=bool)
    rtp = rng.normal(size=(h, w)).astype(np.float32)
    vg = rng.normal(size=(h, w)).astype(np.float32)
    feats = features_from_bands(rtp, vg, fp)
    for name, arr in feats.items():
        assert arr.shape == (h, w)
        assert np.isfinite(arr).all(), name
        assert arr.min() >= 0.0 and arr.max() <= 1.0, name
    surf = surface_e1(feats, fp)
    assert surf.min() >= 0.0 and surf.max() <= 1.0
    cat = np.zeros((h, w), dtype=bool)
    cat[30, 30] = True
    dots = emit_dots(surf, fp, cat, n_dots=20, spacing=2.8, collar=3.0)
    assert int(dots.sum()) == 20
    assert not dots[30, 30]
