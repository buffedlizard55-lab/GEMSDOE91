"""Unit tests for src/gems91/relief.py (no competition data required)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import dti as dti_mod  # noqa: E402
from gems91 import relief  # noqa: E402


def _synthetic_relief_stack(h: int = 90, w: int = 120):
    rng = np.random.default_rng(42)
    footprint = np.ones((h, w), dtype=bool)
    footprint[:4, :] = False
    footprint[:, -5:] = False

    # Rows 0..29 = basin (low elev, low slope), 30..59 = piedmont, 60..89 = range
    yy, xx = np.mgrid[0:h, 0:w]
    det_elev = (yy - 45.0) * 8.0 + rng.normal(0.0, 2.0, size=(h, w))
    det_slope = np.clip((yy / h) * 18.0 + rng.uniform(0.0, 1.5, size=(h, w)), 0.01, 45.0)
    # Inject nodata sentinels inside footprint along edge to test nearest-neighbour fill
    det_elev[5, 5:10] = -3.4028235e38
    det_slope[5, 5:10] = -3.4028235e38

    cat = np.zeros((h, w), dtype=bool)
    cat[45, 20:50] = True
    dcat = ndi.distance_transform_edt(~cat)

    # Lineage ridges spaced across all three terciles
    h195 = np.zeros((h, w), dtype=bool)
    h194 = np.zeros((h, w), dtype=bool)
    h161 = np.zeros((h, w), dtype=bool)
    for r in range(8, h - 4, 4):
        h195[r, 6 : w - 8] = True
        if r % 8 == 0:
            h194[r, 6 : w - 8] = True
            h161[r, 6 : w - 8] = True
    for r in range(10, h - 4, 4):
        h194[r, 6 : w - 8] = True

    # Parent dots: sparse d>=3 subset of h195 off-collar + 3 inherited collar dots at 2 < d <= 3
    parent = np.zeros((h, w), dtype=bool)
    for r in range(8, h - 4, 4):
        for c in range(8, w - 10, 4):
            if footprint[r, c] and dcat[r, c] > 3.0:
                parent[r, c] = True
    # Add 2 inherited R0-like collar dots at d == 3.0 (must never be touched!)
    collar_candidates = np.argwhere(footprint & (dcat > 2.0) & (dcat <= 3.0))
    for r, c in collar_candidates[:2]:
        parent[r, c] = True

    tmi_hg = rng.uniform(0.1, 100.0, size=(h, w))
    grav_slope = rng.uniform(0.01, 1.0, size=(h, w))
    grav_hg = rng.normal(0.0, 3.0, size=(h, w))
    tc = rng.uniform(5.0, 50.0, size=(h, w))
    return {
        "footprint": footprint,
        "det_elev": det_elev,
        "det_slope": det_slope,
        "cat": cat,
        "dcat": dcat,
        "h195": h195,
        "h194": h194,
        "h161": h161,
        "parent": parent,
        "tmi_hg": tmi_hg,
        "grav_slope": grav_slope,
        "grav_hg": grav_hg,
        "tc": tc,
    }


def test_terciles_partition_footprint_cleanly():
    st = _synthetic_relief_stack()
    r_idx, terciles, meta = relief.compute_relief_terciles(
        st["det_elev"], st["det_slope"], st["footprint"]
    )
    assert np.isfinite(r_idx[st["footprint"]]).all()
    union = terciles["basin"] | terciles["pied"] | terciles["range"]
    assert np.array_equal(union, st["footprint"])
    assert not (terciles["basin"] & terciles["pied"]).any()
    assert not (terciles["pied"] & terciles["range"]).any()
    assert not (terciles["basin"] & terciles["range"]).any()
    for key in ("basin", "pied", "range"):
        assert 32.5 <= meta["terciles"][key]["footprint_pct"] <= 34.0
    assert (
        meta["terciles"]["basin"]["median_det_elev_m"]
        < meta["terciles"]["pied"]["median_det_elev_m"]
        < meta["terciles"]["range"]["median_det_elev_m"]
    )


def test_shift_preserves_count_collar_and_donor_twin_identity():
    st = _synthetic_relief_stack()
    _, terciles, _ = relief.compute_relief_terciles(
        st["det_elev"], st["det_slope"], st["footprint"]
    )
    s_struct, pot_crest = relief.compute_structural_score(
        st["tmi_hg"],
        st["grav_slope"],
        st["grav_hg"],
        st["tc"],
        st["h195"],
        st["h194"],
        st["h161"],
        st["footprint"],
    )
    lineage = (st["h195"] | st["h194"] | st["h161"]) & st["footprint"]

    r2p = relief.shift_relief_mass(
        st["parent"],
        terciles,
        st["dcat"],
        s_struct,
        lineage,
        pot_crest,
        donor_key="range",
        recipient_key="pied",
        frac=0.12,
    )
    r2b = relief.shift_relief_mass(
        st["parent"],
        terciles,
        st["dcat"],
        s_struct,
        lineage,
        pot_crest,
        donor_key="range",
        recipient_key="basin",
        frac=0.12,
    )
    b2r = relief.shift_relief_mass(
        st["parent"],
        terciles,
        st["dcat"],
        s_struct,
        lineage,
        pot_crest,
        donor_key="basin",
        recipient_key="range",
        frac=0.12,
    )

    for res in (r2p, r2b, b2r):
        assert res["n_dots"] == int(st["parent"].sum())
        assert res["added_dots_le3px"] == 0
        assert res["collar_le3px_before"] == res["collar_le3px_after"] == 2
        assert not (res["dots"] & st["cat"]).any()
        assert not (res["dots"] & ~st["footprint"]).any()

    # Donor-set identity: r2p and r2b must drop the exact same range dots
    assert np.array_equal(st["parent"] & ~r2p["dots"], st["parent"] & ~r2b["dots"])


def test_shift_rejects_out_of_band_fraction():
    st = _synthetic_relief_stack()
    _, terciles, _ = relief.compute_relief_terciles(
        st["det_elev"], st["det_slope"], st["footprint"]
    )
    s_struct, pot_crest = relief.compute_structural_score(
        st["tmi_hg"],
        st["grav_slope"],
        st["grav_hg"],
        st["tc"],
        st["h195"],
        st["h194"],
        st["h161"],
        st["footprint"],
    )
    lineage = st["h195"] | st["h194"] | st["h161"]
    with pytest.raises(ValueError):
        relief.shift_relief_mass(
            st["parent"],
            terciles,
            st["dcat"],
            s_struct,
            lineage,
            pot_crest,
            donor_key="range",
            recipient_key="pied",
            frac=0.05,
        )
    with pytest.raises(ValueError):
        relief.shift_relief_mass(
            st["parent"],
            terciles,
            st["dcat"],
            st["s_struct"] if "s_struct" in st else s_struct,
            lineage,
            pot_crest,
            donor_key="range",
            recipient_key="range",
            frac=0.12,
        )


def test_fast_binary_dti_matches_exact_dti_algebra():
    rng = np.random.default_rng(91)
    pred = rng.random((45, 55)) < 0.04
    truth = rng.random((45, 55)) < 0.05
    exact = dti_mod.components(pred.astype(np.float32), truth.astype(np.uint8))
    fast = relief.fast_binary_dti(pred, truth)
    assert fast["T"] == pytest.approx(exact.T, abs=1e-10)
    assert fast["M"] == pytest.approx(exact.M, abs=1e-10)
    assert fast["S"] == pytest.approx(exact.S, abs=1e-10)
    assert fast["G"] == pytest.approx(exact.G, abs=1e-10)
    assert fast["dti"] == pytest.approx(exact.score, abs=1e-12)
