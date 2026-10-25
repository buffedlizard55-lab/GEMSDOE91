"""CWP91 unit tests (synthetic arrays only; no competition data required)."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from gems91 import cwp as C  # noqa: E402


def _synthetic():
    rng = np.random.default_rng(0)
    shape = (120, 140)
    fp = np.ones(shape, bool)
    # posterior: a broad "geology" field, high on the left half
    p = np.full(shape, 0.05, np.float32)
    p[:, :70] = 0.6
    p += (rng.random(shape) * 0.02).astype(np.float32)
    # catalogue: dense fault lines on the far left, absent on the mid-left
    cat = np.zeros(shape, bool)
    cat[10:110:7, 5:35] = True          # densely mapped zone (high p, high cat)
    # columns 40..65: high p, no catalogue  -> discovery zone
    cat[10:110:9, 90:130] = True        # sparse lines in low-p zone
    return p, cat, fp


def test_chat_is_bounded_and_high_where_mapping_is_dense():
    p, cat, fp = _synthetic()
    chat, diag = C.completeness_field(cat, p, fp, calibration_mask=fp)
    assert chat.min() >= 0.0 and chat.max() <= 1.0
    assert np.isfinite(chat).all()
    dense = chat[60, 20]       # high p, dense catalogue -> complete
    hole = chat[60, 52]        # high p, no catalogue   -> incomplete
    assert dense > hole
    assert hole < 0.05
    assert 0.0 < diag["c_bar"] <= 1.0


def test_cwp_surface_promotes_the_hole_over_the_mapped_zone():
    p, cat, fp = _synthetic()
    s, chat, _ = C.cwp_surface(p, cat, fp, calibration_mask=fp)
    assert s.min() >= 0.0 and s.max() <= 1.0 and np.isfinite(s).all()
    # equal posterior, but the unmapped zone must outrank the mapped zone
    assert s[60, 52] > s[60, 20]
    # outside-footprint pixels are exactly zero
    fp2 = fp.copy(); fp2[:5, :] = False
    s2, _, _ = C.cwp_surface(p, cat, fp2, calibration_mask=fp2)
    assert (s2[~fp2] == 0).all()


def test_shifted_catalogue_preserves_density_but_breaks_alignment():
    p, cat, fp = _synthetic()
    sh = C.shifted_catalogue(cat, fp, shift_yx=(17, -31))
    assert int(sh.sum()) == int((cat & fp).sum())      # full footprint: roll is a bijection
    assert sh.shape == cat.shape and sh.dtype == bool
    s_ctl, chat_ctl, diag = C.ctl_surface(p, cat, fp, calibration_mask=fp)
    _, chat_true, _ = C.cwp_surface(p, cat, fp, calibration_mask=fp)
    # the control's completeness at the true hole must not reproduce the true field
    assert not np.allclose(chat_ctl, chat_true)
    assert diag["shift_yx"] == [173, -211]


def test_elkan_c_bar_rejects_empty_calibration():
    p, cat, fp = _synthetic()
    try:
        C.elkan_c_bar(p, cat, np.zeros_like(fp))
    except ValueError:
        return
    raise AssertionError("empty calibration domain must fail closed")


def test_run_card_verdict_is_explicit_and_consistent():
    import hashlib
    import json
    card = json.loads((ROOT / "docs/run-card-CWP91.json").read_text())
    v = card["verdict"]
    assert v["OK_TO_SUBMIT"] == "NO" and v["promote"] is False
    assert v["OK_TO_DOWNLOAD"].startswith("YES")
    assert card["ok_to_submit"] is False and card["result"] == "negative"
    assert len(card["submission_note"]) <= 140 and len(card["submission_name"]) <= 140
    h = card["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["delta_E1_minus_E0"]["ci95"][1] < 0      # significantly negative stays negative
    assert h["delta_E1_minus_CTL"]["ci95"][1] < 0     # loses to the hole-shuffled control too
    assert card["organizer_confirmed_scores"] is None
    assert card["registry_uniqueness"]["dots_max_within_3px_non_blanket"] > 0.70  # duplicate-stop recorded
    tif = ROOT / card["raster"]["path"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster"]["sha256"]
    assert card["validator"]["all_checks_passed"] is True
