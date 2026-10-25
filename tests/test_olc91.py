"""OLC91 unit and integrity tests (no competition data required)."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "vendor"), str(ROOT / "src")]
import run_olc91 as R  # noqa: E402


def test_line_kernels_are_normalised_and_oriented():
    ks = R.line_kernels(11, 12)
    assert len(ks) == 12
    for k in ks:
        assert abs(float(k.sum()) - 1.0) < 1e-5 and (k >= 0).all()
    c = ks[0].shape[0] // 2
    assert ks[0][c, :].sum() > 0.95          # azimuth 0 -> horizontal line
    assert ks[6][:, c].sum() > 0.95          # azimuth 90 -> vertical line


def test_olc_prefers_a_line_over_a_blob_of_equal_mass():
    p = np.zeros((80, 80), np.float32)
    p[20, 10:31] = 0.6                        # 21-px line
    p[55:60, 50:54] = 0.63                    # compact blob, same total mass
    s, c = R.olc_surface(p, np.ones_like(p, bool))
    assert c[20, 20] > c[57, 52]
    assert s[20, 20] > s[57, 52]
    assert np.isfinite(s).all() and s.min() >= 0 and s.max() <= 1


def test_run_card_verdict_is_explicit_and_consistent():
    card = json.loads((ROOT / "docs/run-card-OLC91.json").read_text())
    v = card["verdict"]
    assert v["OK_TO_SUBMIT"] == "NO" and v["promote"] is False
    assert v["OK_TO_DOWNLOAD"].startswith("YES")
    assert len(card["submission_note"]) <= 140 and len(card["submission_name"]) <= 140
    h = card["holdout"]
    assert h["evidence_class"] == "HOLDOUT-DTI" and h["evaluator_version"] == "gems57-pooled-hide-v2"
    assert h["delta_E1_minus_E0"]["ci95"][0] <= 0          # negative stays negative
    assert card["organizer_confirmed_scores"] is None
    tif = ROOT / card["raster"]["path"]
    assert hashlib.sha256(tif.read_bytes()).hexdigest() == card["raster"]["sha256"]
