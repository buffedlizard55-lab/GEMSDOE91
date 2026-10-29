"""Synthetic tests for the S27-FABRIC-FAR stratified emitter (no competition data)."""
import numpy as np
import pytest
from scipy import ndimage as ndi

from gems91 import far27 as F
from gems91.novelty import dot_check


def _grid(n=60):
    fp = np.ones((n, n), dtype=bool)
    vis = np.zeros((n, n), dtype=bool)
    vis[:, n // 2] = True  # one mapped trace down the middle
    rng = np.random.default_rng(3)
    surf = rng.random((n, n)).astype(np.float32)
    return surf, vis, fp


def test_band_quotas_sum_and_shares():
    q = F.band_quotas(37654)
    assert sum(q) == 37654
    assert len(q) == len(F.BAND_SHARES)
    for got, want in zip(q, F.BAND_SHARES):
        assert abs(got / 37654 - want) < 0.001
    assert F.band_quotas(0) == [0] * len(F.BAND_SHARES)
    with pytest.raises(ValueError):
        F.band_quotas(-1)


def test_band_index_boundaries():
    # Bands: (collar,5], (5,10], (10,20], (20,40], (40,inf)
    assert F.band_index(3.1, 3.05) == 0
    assert F.band_index(5.0, 3.05) == 0
    assert F.band_index(5.1, 3.05) == 1
    assert F.band_index(20.0, 3.05) == 2
    assert F.band_index(40.0, 3.05) == 3
    assert F.band_index(41.0, 3.05) == 4


def test_stratified_emission_respects_collar_spacing_and_quotas():
    # 140x140 so the >40 px band actually exists (60x60 caps distance at 30 px,
    # which would legitimately trigger quota redistribution instead).
    surf, vis, fp = _grid(140)
    out, info = F.emit_dots_stratified(surf, vis, fp, budget=100)
    dots = out > 0
    assert int(dots.sum()) == 100
    assert info["n_placed"] == 100
    assert sum(info["band_counts_final"]) == 100
    # Collar: every dot > 3.05 px from the visible trace.
    d = ndi.distance_transform_edt(~vis)
    assert d[dots].min() > 3.05
    # Spacing: no two dots closer than the emitter's disk rule.
    ys, xs = np.nonzero(dots)
    pts = np.column_stack([ys, xs])
    for i in range(len(pts)):
        dist = np.hypot(*(pts - pts[i]).T)
        assert (np.delete(dist, i) >= 2.0).all()
    # Quotas: with a random surface and a wide grid, pass 1 must fill every
    # band quota exactly (no redistribution needed).
    assert info["band_counts_final"] == info["band_quotas"]
    assert info["redistributed_dots"] == 0


def test_stratified_emission_never_places_on_visible_or_outside_domain():
    surf, vis, fp = _grid()
    domain = fp.copy()
    domain[:10, :] = False
    out, _ = F.emit_dots_stratified(surf, vis, domain, budget=50)
    dots = out > 0
    assert not (dots & vis).any()
    assert not (dots & ~domain).any()
    assert dots[:10, :].sum() == 0


def test_caps_are_enforced_during_placement():
    surf, vis, fp = _grid()
    # One cap reference covering the whole grid within 3 px: every accepted
    # dot overlaps it, so the cap must bind at the limit, and the emitter
    # must then be unable to place more dots (budget shortfall is reported,
    # never silently over-cap).
    ref = np.ones_like(fp)
    bits = F.pack_cap_halos([ref], fp)
    out, info = F.emit_dots_stratified(
        surf, vis, fp, budget=100, cap_bits=bits, cap_limit=40, n_cap_refs=1
    )
    assert info["cap_counts_final"] == [40]
    assert int((out > 0).sum()) == 40
    assert info["cap_max_fraction_final"] == 1.0


def test_pack_cap_halos_matches_dot_check_predicate():
    rng = np.random.default_rng(5)
    n = 40
    fp = np.ones((n, n), dtype=bool)
    ref = (rng.random((n, n)) < 0.05)
    bits = F.pack_cap_halos([ref], fp)
    halo = (bits & 1).astype(bool)
    # A candidate of single dots: within-3px membership must equal halo.
    cand = np.zeros((n, n), dtype=np.float32)
    cand[5, 5] = 1.0
    cand[30, 30] = 1.0
    res = dot_check(cand, ref.astype(np.float32), fp)
    expect = float(np.mean([halo[5, 5], halo[30, 30]]))
    assert abs(res["overlap_within_3px"] - expect) < 1e-12


def test_emitter_rejects_bad_inputs():
    surf, vis, fp = _grid(20)
    bad = surf.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        F.emit_dots_stratified(bad, vis, fp, budget=5)
    with pytest.raises(ValueError):
        F.emit_dots_stratified(surf, vis, fp, budget=0)
    with pytest.raises(ValueError):
        F.pack_cap_halos([fp] * 33, fp)
