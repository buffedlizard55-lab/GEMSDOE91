from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_s15_lane", ROOT / "scripts/run_s15_lane.py")
RUNNER = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(RUNNER)


def test_s15_promotion_guard_uses_current_same_instrument_quality_bar():
    base = {
        "evaluator_version": RUNNER.CURRENT_COMPARABLE_EVALUATOR,
        "n_withheld_positives": RUNNER.CURRENT_COMPARABLE_WITHHELD,
        "holdout_dti": RUNNER.CURRENT_COMPARABLE_HOLDOUT_BEST,
    }
    assert not RUNNER.beats_current_comparable_best(base)
    base["holdout_dti"] += 0.000001
    assert RUNNER.beats_current_comparable_best(base)
    base["evaluator_version"] = "other"
    assert not RUNNER.beats_current_comparable_best(base)


def test_s15_pre_emission_guard_blocks_losing_holdout_and_incomplete_inventory():
    winning = {
        "evaluator_version": RUNNER.CURRENT_COMPARABLE_EVALUATOR,
        "n_withheld_positives": RUNNER.CURRENT_COMPARABLE_WITHHELD,
        "holdout_dti": RUNNER.CURRENT_COMPARABLE_HOLDOUT_BEST + 0.01,
    }
    assert RUNNER.pre_emission_block_reason(winning, {"complete_inventory": True}) is None
    assert (RUNNER.pre_emission_block_reason(winning, {"complete_inventory": False})
            == "frozen_registry_inventory_incomplete")
    losing = dict(winning, holdout_dti=RUNNER.CURRENT_COMPARABLE_HOLDOUT_BEST)
    assert (RUNNER.pre_emission_block_reason(losing, {"complete_inventory": True})
            == "holdout_does_not_beat_current_comparable_best")


def test_s15_holdout_uses_same_farfield_halo_quota_policy_and_invalidates_legacy_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(RUNNER, "CACHE", tmp_path)
    cache_path = tmp_path / "s15_test_scores.json"
    # Historical caches lack the policy id and must never be silently reused.
    cache_path.write_text(json.dumps({
        "v10": {"holdout_dti": 0.999},
        "v11": {"holdout_dti": 0.999},
        "metas": {},
    }))

    shape = (8, 8)
    footprint = np.ones(shape, dtype=bool)
    zeros = np.zeros(shape, dtype=bool)
    fold = SimpleNamespace(
        fold_id=0,
        name="NW",
        region_mask=zeros.copy(),
        withheld_faults=zeros.copy(),
        buffer_mask=zeros.copy(),
        visible_faults=zeros.copy(),
    )
    eligible = np.ones(shape, dtype=bool)
    # All candidates are far from visible catalogue faults; the helper will
    # allocate 75% of the budget to this far-field domain and cap the halo.
    d_visible = np.full(shape, 11.0)
    probability = np.ones(shape, dtype=np.float32)
    calls = []

    def fake_expected_intensity(prob, crest, piedmont, footprint, calibration_mask, pi_true, pi_sample):
        return np.ones(shape, dtype=np.float32), np.ones(shape, dtype=np.float32), 1e-6

    def fake_select(w_surf, valid_mask, rank_surf, max_dots, min_gain_threshold, min_spacing_px):
        calls.append((int(valid_mask.sum()), max_dots, min_spacing_px))
        out = np.zeros(shape, dtype=np.float32)
        ys, xs = np.nonzero(valid_mask)
        take = min(max_dots, len(ys))
        out[ys[:take], xs[:take]] = 1.0
        return out, 0.0

    def fake_score(*args, **kwargs):
        return {
            "holdout_dti": 0.1,
            "ci_95": [0.08, 0.12],
            "evaluator_version": RUNNER.EH.EVALUATOR_VERSION,
            "n_withheld_positives": 10,
        }

    monkeypatch.setattr(RUNNER.PTHA, "build_dinkelbach_expected_intensity", fake_expected_intensity)
    monkeypatch.setattr(RUNNER.PTHA, "_lazy_greedy_submodular_select", fake_select)
    monkeypatch.setattr(RUNNER.EH, "score_pooled_holdout", fake_score)

    dots, v10, _v11, metas = RUNNER.emit_and_score(
        {0: probability},
        {0: {"pi_true": 0.1, "pi_sample": 0.2}},
        [fold], footprint,
        np.ones(shape), np.ones(shape),
        {0: eligible}, {0: d_visible},
        8, "s15_test",
    )

    assert v10["holdout_dti"] == 0.1
    assert int((dots[0] > 0).sum()) == 8
    # Quota split matches the final emitter: at least 6 far-field, at most 2
    # halo. Since the halo is unavailable, its unused budget is refilled far-field.
    assert [call[1] for call in calls] == [6, 2, 2]
    assert all(call[2] == 3.0 for call in calls)
    assert metas["NW"]["n_far_gt10px_of_visible_catalogue"] == 8
    assert metas["NW"]["n_halo_3to10px_of_visible_catalogue"] == 0
    assert metas["NW"]["selector_policy"] == RUNNER.HOLDOUT_SELECTOR_POLICY

    saved = json.loads(cache_path.read_text())
    assert saved["cache_schema"] == RUNNER.HOLDOUT_SCORE_CACHE_SCHEMA
    assert saved["selector_policy"] == RUNNER.HOLDOUT_SELECTOR_POLICY
    assert saved["evaluator_version"] == RUNNER.EH.EVALUATOR_VERSION
