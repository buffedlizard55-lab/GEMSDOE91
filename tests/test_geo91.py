"""GEO91 lane unit tests: emission geometry invariants on synthetic grids."""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_geo91_lane import COLLAR_PX, emit, surface  # noqa: E402


def _synthetic():
    rng = np.random.default_rng(0)
    footprint = np.ones((200, 200), bool)
    F = np.zeros((200, 200), bool)
    F[50, 20:120] = True          # horizontal fault with two tips
    F[80:160, 150] = True         # vertical fault
    return F, footprint, rng


def test_surface_finite_unit_range():
    F, footprint, rng = _synthetic()
    surf, feats, _dist = surface(F, footprint, rng)
    assert np.isfinite(surf).all()
    assert 0.0 <= float(surf.min()) and float(surf.max()) <= 1.0
    assert set(feats) == {"tip_extension", "relay_gap",
                          "nearfield_band_x_density", "fault_density_3km"}
    assert float(surf[F].max()) == 0.0  # never scores the catalogue itself


def test_emit_collar_count_binary():
    F, footprint, rng = _synthetic()
    surf, _feats, dist = surface(F, footprint, rng)
    dots = emit(surf, dist, footprint, F, n=300)
    assert int((dots > 0).sum()) == 300
    assert set(np.unique(dots)) == {0.0, 1.0}
    assert int(((dots > 0) & F).sum()) == 0
    d = ndi.distance_transform_edt(~F)
    assert float(d[dots > 0].min()) > COLLAR_PX


def test_tip_extension_scores_beyond_tip():
    F, footprint, rng = _synthetic()
    _surf, feats, _dist = surface(F, footprint, rng)
    # pixels just beyond the right tip of the horizontal fault (row 50, col>120)
    assert float(feats["tip_extension"][50, 124:132].max()) > 0.0
