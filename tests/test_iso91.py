"""ISO91 unit and integrity tests (synthetic; no competition data required)."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "vendor"), str(ROOT / "src")]
from gems57 import holdout as H  # noqa: E402
from gems91 import isolated_holdout as IH  # noqa: E402


def _toy():
    cat = np.zeros((120, 120), bool)
    cat[20, 20:26] = True          # A  (NW)  - 5 px gap to B -> neither isolated
    cat[20, 30:34] = True          # B  (NW)  (x=25 -> x=30 is exactly 5 px)
    cat[40, 40:46] = True          # C  (NW)  isolated
    cat[30, 80:90] = True          # D  (NE)  isolated
    cat[90, 20:24] = True          # E  (SW)  isolated
    cat[88, 85:95] = True          # F  (SE)  6 px from G -> both isolated at sep 5
    cat[94, 85:95] = True          # G  (SE)
    cat[58:63, 59] = True          # H  straddles the quadrant split -> never eligible
    return cat


def test_isolated_components_respects_euclidean_separation():
    cat = _toy()
    iso, comp, ids = IH.isolated_components(cat, 5.0)
    assert not iso[20, 22] and not iso[20, 32]           # gap of exactly 5 px is "within 5 px"
    assert iso[40, 42] and iso[30, 85] and iso[90, 21]
    assert iso[88, 90] and iso[94, 90]                    # 6 px apart -> isolated at sep 5
    iso6, _, _ = IH.isolated_components(cat, 6.0)
    assert not iso6[88, 90] and not iso6[94, 90]          # ... but not at sep 6
    assert (iso <= cat).all()
    # every isolated component is whole (never partially selected)
    for lab in np.unique(comp[iso]):
        assert iso[comp == lab].all()


def test_isolated_components_empty_catalogue():
    iso, comp, ids = IH.isolated_components(np.zeros((10, 10), bool), 5.0)
    assert not iso.any() and ids.size == 0


def test_isolated_component_draw_is_per_fold_and_honours_separation():
    cat = _toy()
    grid = SimpleNamespace(footprint=np.ones_like(cat), catalogue=cat)
    folds, quad = IH.isolated_component_draw(grid, sep_px=5.0, buffer_px=3, boundary_px=4)
    assert [f["name"] for f in folds] == list(H.FOLD_NAMES)
    iso, comp, _ = IH.isolated_components(cat, 5.0)
    for f in folds:
        hidden, region = f["hidden_all"], f["region"]
        assert (hidden <= region).all() and (hidden <= iso).all()
        assert np.array_equal(f["truth"], hidden & region)
        assert not (f["visible"] & hidden).any()
        assert np.array_equal(f["masked_known"], cat & ~hidden)
        assert ndi.distance_transform_edt(~f["visible"])[hidden].min() > 5.0
        assert f["receipt"]["split_version"] == "isolated-whole-components-loqo-v1"
        assert f["receipt"]["hidden_set"] == "per-fold"
        # other quadrants' isolated components stay VISIBLE in this fold (LOQO training data)
        others = iso & ~region & (quad >= 0) & (quad != f["fold"])
        assert (f["visible"][others]).all()
    assert not folds[0]["hidden_all"][60, 59]             # straddling component never withheld
    assert folds[0]["hidden_all"][40, 42] and not folds[0]["hidden_all"][20, 22]


def test_isolated_component_draw_rejects_bad_parameters():
    grid = SimpleNamespace(footprint=np.ones((50, 50), bool), catalogue=np.zeros((50, 50), bool))
    with pytest.raises(ValueError):
        IH.isolated_component_draw(grid, sep_px=0)
    with pytest.raises(ValueError):
        IH.isolated_component_draw(grid, sep_px=5, buffer_px=3, boundary_px=2)


def test_matched_random_components_reaches_target_with_whole_components():
    import run_iso91 as R
    cat = _toy()
    dom = np.ones_like(cat)
    sub = R.matched_random_components(cat, dom, 15, seed=3)
    comp, _ = ndi.label(cat, IH.STRUCT3)
    assert sub.sum() >= 15 and (sub <= cat).all()
    for lab in np.unique(comp[sub]):
        assert sub[comp == lab].all()


def test_fit_predict_pu_equals_olc91_e0_when_exclude_is_positives():
    import run_iso91 as R
    import run_olc91 as O
    rng = np.random.default_rng(0)
    fp = np.ones((60, 60), bool)
    pos = np.zeros_like(fp)
    pos[10, 5:55] = True
    pos[40:52, 30] = True
    X = rng.normal(size=(fp.size, 4)).astype(np.float16)
    X[pos.ravel(), 0] += 2.0
    fpi = O.fp_index_grid(fp)
    a, ia = O.fit_predict(X, fpi, fp, pos, fp, fp, 2001)
    b, ib = R.fit_predict_pu(X, fpi, fp, pos, pos, fp, fp, 2001)
    assert ia == ib and np.array_equal(a, b)


def test_iso91_run_card_verdict_is_explicit_and_consistent():
    p = ROOT / "docs" / "run-card-ISO91.json"
    if not p.exists():
        pytest.skip("run card not written yet")
    card = json.loads(p.read_text())
    v = card["verdict"]
    gates = card["gates"]
    all_pass = all(g["pass"] for g in gates.values())
    assert v["OK_TO_SUBMIT"] == ("YES" if all_pass else "NO")
    assert v["promote"] is all_pass
    assert v["OK_TO_DOWNLOAD"].startswith("YES") == card["validator"]["all_checks_passed"]
    assert 0 < len(card["submission_note"]) <= 140 and 0 < len(card["submission_name"]) <= 140
    assert card["organizer_confirmed_scores"] is None
    assert card["holdout"]["primary"]["evaluator_version"] == "gems57-pooled-hide-v2"
    tif = ROOT / card["raster"]["path"]
    assert tif.resolve().is_relative_to((ROOT / "docs" / "downloads").resolve())
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster"]["sha256"]


def test_pinned_template_is_untouched_by_iso91():
    import hashlib as _h
    pin = json.loads((ROOT / "registry" / "template_pin.json").read_text())
    for name, digest in pin["sha256"].items():
        assert _h.sha256((ROOT / "vendor" / "gems57" / name).read_bytes()).hexdigest() == digest
    assert not hasattr(H, "isolated_component_draw")      # extension lives in gems91, not a template fork


def test_final_model_positive_set_reproduces_on_pinned_catalogue():
    """The final ISO91 model used 13,372 positives in 655 isolated components (docs/iso91/final.json)."""
    cat_p = ROOT / "data" / "official" / "existing_faults.tif"
    fin_p = ROOT / "docs" / "iso91" / "final.json"
    if not cat_p.exists() or not fin_p.exists():
        pytest.skip("pinned catalogue not restored (python scripts/restore_data.py --only existing_faults)")
    import rasterio
    with rasterio.open(cat_p) as ds:
        cat = ds.read(1) > 0
    iso, _, ids = IH.isolated_components(cat, 5.0)
    meta = json.loads(fin_p.read_text())["meta"]
    assert len(ids) == meta["n_isolated_components"] == 655
    assert int(iso.sum()) == meta["model"]["n_pos"] == 13372
