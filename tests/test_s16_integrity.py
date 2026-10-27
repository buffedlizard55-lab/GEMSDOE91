"""Pass-2/3 regressions: actual bytes, honest gates, no synthetic real labels."""
from __future__ import annotations
import hashlib
from html.parser import HTMLParser
import inspect
import json
from pathlib import Path
import runpy
import subprocess
import sys
from urllib.parse import unquote, urlsplit

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import evaluate_holdout as EH
from scripts.verify_s16 import verify
from scripts import render_portal


class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.ids = set(); self.states = []; self.text = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        if tag == 'a' and 'href' in a: self.links.append(a['href'])
        if tag in ('script', 'img') and a.get('src'): self.links.append(a['src'])
        if tag == 'link' and a.get('href'): self.links.append(a['href'])
        if 'data-submission-ready' in a: self.states.append(a['data-submission-ready'])
    def handle_data(self, data):
        self.text.append(data)


def test_current_real_tiff_and_measured_evidence_verify_without_data_download():
    result = verify()
    assert result['status'] == 'PASS'
    assert result['ok_to_download'] is True
    assert result['ok_to_submit'] is False
    assert result['geological_experiments_rerun'] == 0


def test_root_and_docs_expose_one_current_negative_not_legacy_format_only_approval():
    current = json.loads((ROOT / 'docs/current-run.json').read_text())
    # The current run card rotates per session; the safety contract below does not.
    assert current['run_card'].startswith('run-card-') and current['ok_to_submit'] is False
    card = json.loads((ROOT / 'docs' / current['run_card']).read_text())
    current_tif = Path(card['raster_path']).name
    assert current['raster_sha256'] == card['raster_sha256']
    assert card['ok_to_submit'] is False
    for name in ('docs/index.html', 'docs/executive-summary.html'):
        p = Page(); p.feed((ROOT / name).read_text())
        text = ' '.join(p.text)
        assert 'OK TO DOWNLOAD: YES' in text and 'OK TO SUBMIT: NO' in text
        assert 'NOT OK TO SUBMIT' in text
        assert p.states == ['false']
        assert current['run_card'] in p.links
        assert any(link.endswith(current_tif) for link in p.links)
        assert 'OK TO SUBMIT: YES' not in text
    assert 'OK TO SUBMIT: YES' not in (ROOT / 'index.html').read_text()


def test_new_primary_pages_have_no_broken_local_targets_or_fragments():
    for name in ('index.html', 'executive-summary.html', 'research.html', 'dzedge-executive-summary.html'):
        path = ROOT / 'docs' / name
        p = Page(); p.feed(path.read_text())
        for href in p.links:
            u = urlsplit(href)
            if u.scheme or u.netloc: continue
            target = (path.parent / unquote(u.path)).resolve() if u.path else path
            assert target.is_relative_to(ROOT) and target.is_file(), (name, href)
            if u.fragment and target.suffix == '.html':
                q = Page(); q.feed(target.read_text()); assert u.fragment in q.ids


def test_generator_import_has_no_catalogue_or_filesystem_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(ROOT / 'generate_submission.py'), run_name='import_safety_test')
    assert list(tmp_path.iterdir()) == []


def test_legacy_fabricated_recovery_cannot_write(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/recover_geod_light.py')], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0 and 'BLOCKED' in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_legacy_hidden_truth_halo_is_now_explicit_opt_in():
    assert inspect.signature(EH.score_pooled_holdout).parameters['mask_buffer_predictions'].default is False


def test_empty_or_missing_registry_never_passes(tmp_path):
    fp = np.ones((10, 10), bool)
    surface = np.arange(100, dtype=float)
    dots = np.zeros(fp.shape); dots[2, 2] = 1
    for paths, error in [([], ValueError), ([tmp_path / 'missing.tif'], FileNotFoundError)]:
        with pytest.raises(error): EH.check_registry_surface_uniqueness(surface, fp, paths)
        with pytest.raises(error): EH.check_registry_uniqueness(surface, dots, fp, paths)


def test_nonfinite_canary_input_fails_instead_of_passing_as_auc_half():
    fp = np.ones((24, 24), bool)
    cat = np.zeros_like(fp); cat[4, 4] = cat[4, 20] = cat[20, 4] = cat[20, 20] = True
    folds = EH.build_segment_buffered_folds(cat, fp, bridge_px=0, buffer_px=1)
    x = np.zeros((int(fp.sum()), 1)); x[0, 0] = np.nan
    with pytest.raises(ValueError, match='finite'):
        EH.run_leakage_canary(x, ['invalid'], folds, fp)
    pred = {f.fold_id: np.zeros(fp.shape) for f in folds}
    pred[0][0, 0] = np.inf
    with pytest.raises(ValueError, match='finite'):
        EH.score_pooled_holdout(pred, folds, fp, n_boot=10)


def test_legacy_status_board_checks_rotations_and_y_scale(tmp_path, monkeypatch):
    monkeypatch.setitem(render_portal.EXPECTED_GRID, 'shape', (2, 2))
    good = Affine(100, 0, 243350, 0, -100, 4508550)
    for i, transform in enumerate((good, Affine(100, 1, 243350, 0, -100, 4508550), Affine(100, 0, 243350, 0, 100, 4508550))):
        path = tmp_path / f'{i}.tif'
        with rasterio.open(path, 'w', driver='GTiff', height=2, width=2, count=1, dtype='float32', crs='EPSG:32611', transform=transform, nodata=None) as ds:
            ds.write(np.zeros((2, 2), np.float32), 1)
        _, ok = render_portal._raster_format(path)
        assert ok is (i == 0)


def test_recorded_registry_feasibility_bound_and_score_evidence_are_honest():
    d = json.loads((ROOT / 'docs/s16/registry-feasibility.json').read_text())
    assert d['overlap_lower_bound'] == 1 - d['uncovered_pixels'] / d['candidate_budget']
    assert d['overlap_lower_bound'] > d['threshold'] and d['feasible_at_fixed_budget'] is False
    source = json.loads((ROOT / 'docs/s16/sources.json').read_text())
    assert not source['organizer_confirmed_scores']
    assert all(s['organizer_receipt'] is False for s in source['sources'])
    forensic = json.loads((ROOT / 'docs/s16/gems32-forensics.json').read_text())
    assert forensic['score_receipt'] is None
    assert forensic['r0_is_exact_base_with_distance_gt_2']
    assert not forensic['advertised_zip']['single_nonempty_tif']


def test_scientific_provenance_remains_frozen_after_duplicate_stop():
    p = json.loads((ROOT / 'docs/s16/provenance.json').read_text())
    from src.gems91.provenance import verify_recorded_source
    for name, digest in p['code_sha256'].items():
        assert verify_recorded_source(ROOT, name, digest) in ('UNCHANGED', 'ARCHIVED_ORIGINAL_AND_PINNED_CORRECTION')
    card = json.loads((ROOT / 'docs/run-card-S16.json').read_text())
    assert card['verdict'] == 'negative' and card['experiments_run'] == 1
    assert card['registry_comparison']['final']['not_checked_after_stop'] > 0


def test_dzedge_format_only_approval_is_revoked():
    card = json.loads((ROOT / 'docs/run-card-gems91-dzedge-v2-20261025.json').read_text())
    assert card['ok_to_submit'] is False and card['submission_ready'] is False
    assert 'OK TO SUBMIT: YES' not in (ROOT / 'docs/dzedge-executive-summary.html').read_text()
    assert 'NOT CLEARED' in card['ok_to_submit_why']


@pytest.mark.parametrize('reference_value', [0, 1])
def test_undefined_registry_rank_is_null_not_a_perfect_diversity_pass(tmp_path, reference_value):
    fp = np.ones((10, 10), bool)
    path = tmp_path / 'constant.tif'
    with rasterio.open(path, 'w', driver='GTiff', height=10, width=10, count=1, dtype='float32', crs='EPSG:32611', transform=Affine(100, 0, 243350, 0, -100, 4508550)) as ds:
        ds.write(np.full(fp.shape, reference_value, np.float32), 1)
    surface = np.arange(fp.sum(), dtype=float)
    dots = np.zeros(fp.shape); dots[2, 2] = 1
    result = EH.check_registry_uniqueness(surface, dots, fp, [path], corr_stride=1)
    assert result['uniqueness_pass'] is False
    assert result['rank_comparison_complete'] is False
    assert result['surface_max_abs_rank_corr'] is None
    assert result['dots_max_abs_rank_corr'] is None
    # A dense-reference overlap remains a conclusive duplicate even when rank is undefined.
    assert result['is_duplicate'] is bool(reference_value)
    assert result['dots_max_3px_overlap'] == reference_value
    with pytest.raises(ValueError, match='undefined'):
        EH.check_registry_surface_uniqueness(surface, fp, [path], corr_stride=1)
    dots[1, 1] = np.nan
    with pytest.raises(ValueError, match='finite'):
        EH.check_registry_uniqueness(surface, dots, fp, [path], corr_stride=1)


def test_artifact_policy_rejects_duplicate_rows_after_concurrent_merges(tmp_path, monkeypatch):
    from scripts import check_artifact_policy as policy
    monkeypatch.setattr(policy, 'ROOT', tmp_path)
    (tmp_path / 'registry').mkdir()
    (tmp_path / 'registry/artifact_policy.json').write_text(json.dumps({'files': [{'path': 'repeated'}, {'path': 'repeated'}]}))
    with pytest.raises(ValueError, match='Duplicate artifact-policy'):
        policy.main()


def test_current_and_preserved_review_pages_have_one_document_not_nested_shells():
    for name in ['index.html', 'executive-summary.html', 'research.html', 'archive-results.html', 'review-0a96aa96-home.html', 'active-executive-summary.html']:
        text = (ROOT / 'docs' / name).read_text().lower()
        assert text.count('<!doctype html>') == 1, name
        assert text.count('<main ') == 1, name
        if 'review-0a96' in name or 'active-exec' in name:
            assert 'historical' in text
