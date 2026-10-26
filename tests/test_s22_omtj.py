"""Synthetic calculations are unit tests, not geological score evidence."""
import json
from pathlib import Path
import numpy as np
import pytest
from gems91.omtj22 import features, fill_band


def test_constant_inputs_produce_zero_signal_not_nan():
    fp = np.ones((32, 40), bool)
    out, meta = features(np.ones(fp.shape), np.ones(fp.shape), fp)
    assert np.count_nonzero(out['surface']) == 0
    assert all(np.isfinite(a).all() for a in out.values())
    assert meta['catalogue_features'] is False


def test_outside_nodata_cannot_create_a_boundary_step():
    fp = np.zeros((32, 40), bool); fp[4:-4, 5:-5] = True
    a = np.full(fp.shape, np.nan); a[fp] = 7
    assert np.all(fill_band(a, fp) == 7)
    out, _ = features(a, a, fp)
    assert (out['surface'] == 0).all()


def test_inside_nodata_fails_closed():
    fp = np.ones((16, 20), bool)
    a = np.ones(fp.shape); a[4, 5] = np.nan
    with pytest.raises(ValueError, match='nonfinite'):
        features(a, np.ones(fp.shape), fp)


def test_repeatable_bounded_and_no_catalogue_input():
    rng = np.random.default_rng(22)
    fp = np.ones((48, 56), bool)
    a, b = rng.normal(size=fp.shape), rng.normal(size=fp.shape)
    out, _ = features(a, b, fp)
    repeat, _ = features(a, b, fp)
    assert np.array_equal(out['surface'], repeat['surface'])
    assert out['surface'].min() >= 0 and out['surface'].max() <= 1
    assert np.ptp(out['surface']) > 0


def test_polarity_and_dc_offset_do_not_change_surface():
    rng = np.random.default_rng(2)
    fp = np.ones((64, 72), bool)
    a, b = rng.normal(size=fp.shape), rng.normal(size=fp.shape)
    one, _ = features(a, b, fp)
    two, _ = features(-a + 10, -b + 10, fp)
    np.testing.assert_allclose(one['surface'], two['surface'], atol=5e-5)


def test_negative_published_run_never_claims_a_leaderboard_estimate():
    path = Path(__file__).resolve().parents[1] / 'docs/s22/run-card.json'
    if not path.exists():
        pytest.skip('experiment not run yet')
    c = json.loads(path.read_text())
    assert c['verdict'] == 'negative'
    assert c['ok_to_submit'] is False
    assert c['organizer_confirmed_score'] is None
    assert c['leaderboard_score_estimate'] is None
    assert c['submission_slots_used'] == 0
    assert c['registry_scope']['dense_exemptions'] is False
    assert c['experiments_run'] <= 3
    assert len(c['submission_note']) <= 140


def test_stopped_evidence_is_internally_consistent_without_rerun():
    from scripts.verify_s22 import verify
    result = verify()
    assert result['status'] == 'PASS'
    assert result['ok_to_submit'] is False
    assert result['holdout_dot_count'] == 37438
    assert result['final_dot_count'] == 37654


def test_current_portal_render_keeps_archived_xbreed_out_of_current_status():
    """The renderer must not reintroduce an obsolete parallel-lane recommendation."""
    from scripts.render_olc91_portal import render
    render()
    docs = Path(__file__).resolve().parents[1] / 'docs'
    pointer = json.loads((docs / 'current-run.json').read_text())
    assert pointer['run_card'] == 'run-card-S22-OMTJ.json'
    for filename in ('index.html', 'executive-summary.html'):
        page = (docs / filename).read_text()
        assert 'OMTJ' in page and 'OK TO SUBMIT: NO' in page
        assert 's22-xb-parallel' not in page
        assert 'gems91-s22-xbreed-c-37654dots' not in page
    assert (docs / 's22-xbreed-executive-summary.html').is_file()


@pytest.mark.parametrize('mutation', ['promote', 'projection', 'pooled_score', 'canary', 'continue_after_stop'])
def test_s22_evidence_tampering_fails_closed(monkeypatch, mutation):
    import copy
    from scripts import verify_s22 as verifier
    original = verifier.load
    def changed(path):
        obj = copy.deepcopy(original(path))
        if path == 'docs/s22/run-card.json':
            if mutation == 'promote': obj['ok_to_submit'] = True
            if mutation == 'projection': obj['leaderboard_score_estimate'] = .5
            if mutation == 'pooled_score': obj['holdout']['dti'] = .5
        if mutation == 'canary' and path == 'docs/s22/canaries.json': obj.pop()
        if mutation == 'continue_after_stop' and path == 'docs/s22/final-dot-checks.json':
            obj.append(copy.deepcopy(obj[-1]))
        return obj
    monkeypatch.setattr(verifier, 'load', changed)
    with pytest.raises((ValueError, AssertionError)):
        verifier.verify()
