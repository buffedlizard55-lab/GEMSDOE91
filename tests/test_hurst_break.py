"""Synthetic checks for the preregistered Hurst-like roughness-break field."""

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gems91 import hurst_break  # noqa: E402


def test_outputs_are_finite_aligned_label_free_and_zero_outside():
    rng = np.random.default_rng(4051)
    h, w = 96, 104
    footprint = np.zeros((h, w), dtype=bool)
    footprint[6:-6, 7:-7] = True
    footprint[43:48, 48:53] = False
    elev = rng.normal(size=(h, w)).astype(np.float32)
    slope = ndi.gaussian_gradient_magnitude(elev, sigma=1.0).astype(np.float32)
    elev[~footprint] = -9999.0
    slope[~footprint] = -9999.0

    fields = hurst_break.features(elev, slope, footprint)

    assert set(fields) == {
        "effective_hurst_like",
        "roughness_break",
        "gradient_control_b19",
        "surface",
    }
    for field in fields.values():
        assert field.shape == footprint.shape
        assert np.isfinite(field).all()
        assert np.all(field[~footprint] == 0.0)
    assert (fields["surface"] >= 0.0).all()
    assert (fields["surface"] <= 1.0).all()
    assert np.count_nonzero(fields["surface"]) > 100


def test_roughness_regime_boundary_has_stronger_hurst_break_than_homogeneous_areas():
    rng = np.random.default_rng(17)
    h = w = 128
    white = rng.normal(size=(h, w)).astype(np.float32)
    smooth = ndi.gaussian_filter(white, sigma=2.5, mode="reflect")
    elev = np.empty((h, w), dtype=np.float32)
    elev[:, :64] = smooth[:, :64]
    elev[:, 64:] = white[:, 64:]
    footprint = np.ones((h, w), dtype=bool)
    slope = ndi.gaussian_gradient_magnitude(elev, sigma=1.0).astype(np.float32)

    fields = hurst_break.features(elev, slope, footprint)
    seam = fields["roughness_break"][:, 59:69].mean()
    far = np.concatenate(
        (fields["roughness_break"][:, 20:45].ravel(),
         fields["roughness_break"][:, 83:108].ravel())
    ).mean()

    # This validates detection of a synthetic texture transition only; it is
    # not geological validation or an expected holdout score.
    assert seam > 3.0 * far


def test_fixed_hurst_scales_and_support_are_explicit():
    assert hurst_break.LAGS_PX == (1, 2, 4)
    assert hurst_break.WINDOW_PX == 11
    assert hurst_break.EDGE_BUFFER_PX == 8
    assert hurst_break.HURST_GRAD_SIGMA_PX == 2.0
    assert hurst_break.MIN_LOCAL_PAIR_FRACTION == 0.50


def test_recorded_experiment_evidence_is_labeled_and_fail_closed():
    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"
    card = json.loads((docs / "run-card-Hurst-Break.json").read_text())
    holdout = json.loads((docs / "hurst-break-holdout.json").read_text())
    canaries = json.loads((docs / "hurst-break-canaries.json").read_text())
    surface = json.loads((docs / "hurst-break-registry-surface.json").read_text())
    final = json.loads((docs / "hurst-break-registry-final.json").read_text())

    summary = holdout["summary"]
    assert summary["evaluator_version"] == "gems57-pooled-hide-v2"
    for score in summary["scores"].values():
        assert score["evidence_class"] == "HOLDOUT-DTI"
        assert score["evaluator_version"] == summary["evaluator_version"]
        assert score["withheld_positive_pixels"] == 60_988
        assert len(score["ci95"]) == 2
    for delta in summary["paired_differences"].values():
        assert delta["evidence_class"] == "HOLDOUT-DTI"
        assert delta["evaluator_version"] == summary["evaluator_version"]
        assert delta["withheld_positive_pixels"] == 60_988
        assert len(delta["ci95"]) == 2
    for fold in holdout["folds"]:
        assert fold["evidence_class"] == "HOLDOUT-DTI-FOLD-DIAGNOSTIC"
        assert fold["withheld_positive_pixels"] > 0
        for arm in fold["arms"].values():
            assert arm["evidence_class"] == "HOLDOUT-DTI-FOLD-DIAGNOSTIC"
            assert arm["ci95"] is None

    assert canaries["evidence_class"] == "LEAKAGE-CANARY-AUC"
    assert "evaluator_version" not in canaries
    assert all(
        feature["evidence_class"] == "LEAKAGE-CANARY-AUC"
        and "withheld_positive_pixels" not in feature
        for feature in canaries["features"].values()
    )
    assert surface["comparable_rasters"] == 92
    assert surface["unverified_rasters"] == 3
    assert final["status"] == "DUPLICATE"
    assert final["checked"] == 52 and final["not_checked_after_stop"] == 43

    assert card["holdout_dti"]["value"] == summary["scores"]["hurst_break"]["dti"]
    assert card["raster_written"] is False and card["raster_sha256"] is None
    assert card["validator_output"]["status"] == "NOT_RUN_NO_RASTER"
    assert card["submission"]["selected_for_slot"] is False
    assert card["slots_used"] == 0
    assert card["submission"]["note_chars"] == len(card["submission"]["note"]) <= 140
    assert card["current_download_status"]["ok_to_download_existing_olc91"] is True
    assert card["current_download_status"]["ok_to_download_hurst_candidate"] is False
