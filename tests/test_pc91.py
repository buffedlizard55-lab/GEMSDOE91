"""PC91 unit tests: phase congruency must fire on a step edge invariantly to
contrast amplitude and sign, and stay low on smooth noise (synthetic only)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gems91.pc91 import phase_congruency_features


def _step(amp: float, n: int = 256) -> np.ndarray:
    f = np.zeros((n, n), dtype=np.float64)
    f[:, n // 2:] = amp
    return f


def _pc_at_edge(f: np.ndarray) -> float:
    pc = phase_congruency_features(f)["pc"]
    n = f.shape[1]
    # median PC within +-1 px of the step, away from borders
    return float(np.median(pc[32:-32, n // 2 - 1: n // 2 + 2]))


def test_pc_fires_on_step():
    assert _pc_at_edge(_step(1.0)) > 0.5


def test_pc_contrast_invariant():
    a = _pc_at_edge(_step(1.0))
    b = _pc_at_edge(_step(100.0))
    c = _pc_at_edge(_step(-37.5))
    assert abs(a - b) < 0.05, (a, b)
    assert abs(a - c) < 0.05, (a, c)


def test_pc_low_on_smooth_field():
    rng = np.random.default_rng(0)
    from scipy import ndimage as ndi
    smooth = ndi.gaussian_filter(rng.standard_normal((256, 256)), 8.0)
    pc = phase_congruency_features(smooth)["pc"]
    assert float(np.median(pc[32:-32, 32:-32])) < 0.45


def test_pc_bounds_and_shapes():
    feats = phase_congruency_features(_step(3.0, 128))
    for k, v in feats.items():
        assert v.shape == (128, 128), k
        assert np.isfinite(v).all(), k
    assert feats["pc"].min() >= 0.0 and feats["pc"].max() <= 1.0
    assert feats["coh"].min() >= 0.0 and feats["coh"].max() <= 1.0
