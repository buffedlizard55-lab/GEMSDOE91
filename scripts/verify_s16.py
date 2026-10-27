#!/usr/bin/env python3
"""Re-verify S16 published bytes and measured evidence; no scientific rerun.

Exit zero means the negative research deliverable is internally consistent and
format-valid. It NEVER means permission to submit. Read ok_to_submit separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
import tifffile
from scipy.spatial import cKDTree
from gems91.readiness import gates, submission_ready
from vendor.gems57 import evaluate_holdout as ev
from scripts.verify_current_artifact import published_path
from scripts.source_integrity import verify_historical_source


def read(relative):
    return json.loads((ROOT / relative).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(with_data=False):
    card = read('docs/run-card-S16.json')
    a = card['artifact']
    tif, zipped = published_path(a['file']), published_path(a['zip'])
    receipt = read('docs/s16/writer-receipt.json')
    require(sha(tif) == card['raster_sha256'] == receipt['sha256'], 'TIFF identity mismatch')
    require(sha(zipped) == a['zip_sha256'] == receipt['zip_sha256'], 'ZIP identity mismatch')
    require(tif.stat().st_size == a['bytes'] == receipt['bytes'], 'TIFF byte count mismatch')
    with zipfile.ZipFile(zipped) as z:
        require(z.namelist() == [tif.name], 'ZIP must contain one TIFF, not JSON, another ZIP or a folder')
        require(z.read(tif.name) == tif.read_bytes(), 'ZIP TIFF bytes differ')
    require(card['submission_name'] == receipt['submission_name'], 'name drift')
    require(card['note'] == receipt['note'] and 0 < len(card['note']) <= 140, 'note drift/length')
    require(0 < len(card['submission_name']) <= 140, 'name length')
    # Independent TIFF decoder, in addition to the writer's rasterio validation.
    arr = tifffile.imread(tif)
    require(arr.shape == (3730, 3292) and arr.dtype == np.float32, 'TIFF array shape/type mismatch')
    require(np.isfinite(arr).all() and np.isin(arr, [0, 1]).all(), 'binary artifact must be finite in [0,1]')
    require(int((arr > 0).sum()) == card['validator_output']['positive_pixels'] == 37654, 'dot count drift')
    require(hashlib.sha256(arr.astype(np.uint8).tobytes()).hexdigest() == card['raster_pixel_sha256'], 'pixel identity mismatch')
    with rasterio.open(tif) as s:
        require(s.count == 1 and s.dtypes == ('float32',) and str(s.crs) == 'EPSG:32611', 'band/type/CRS mismatch')
        require(tuple(s.transform)[:6] == (100., 0., 243350., 0., -100., 4508550.), 'affine mismatch')
        require(s.nodata is None, 'submission must not carry a sentinel nodata tag')
        actual_meta = (s.count, s.shape, s.crs, s.transform)
    pts = np.argwhere(arr > 0)
    min_dist = float(cKDTree(pts).query(pts, k=2)[0][:, 1].min())
    require(min_dist > 3 and min_dist == card['validator_output']['min_spacing_px'], 'spacing mismatch')
    if with_data:
        pin_rows = {r['id']: r for r in read('registry/data_manifest.json')['files']}
        for key in ('sample_submission', 'existing_faults'):
            path = ROOT / 'data' / pin_rows[key]['local_subpath']
            require(sha(path) == card['inputs'][key]['sha256'], f'{key} bytes do not match pinned input')
        with rasterio.open(ROOT / 'data' / pin_rows['sample_submission']['local_subpath']) as s:
            require((s.count, s.shape, s.crs, s.transform) == actual_meta, 'actual template/grid mismatch')
            fp = np.isfinite(s.read(1))
        with rasterio.open(ROOT / 'data' / pin_rows['existing_faults']['local_subpath']) as s:
            require((s.count, s.shape, s.crs, s.transform) == actual_meta, 'catalogue/grid mismatch')
            cat = (s.read(1) > 0) & fp
        require((arr[~fp] == 0).all() and (arr[cat] == 0).all(), 'footprint/catalogue masking drift')
    for name, digest in read('docs/s16/provenance.json')['code_sha256'].items():
        verify_historical_source(ROOT, name, digest)
    prereg = card['preregistration']
    require(sha(ROOT / prereg['path']) == prereg['sha256'], 'preregistration modified after experiment')
    feature = read('docs/s16/features.json')
    require(feature['code_sha256'] == sha(ROOT / 'src/gems91/pgrd.py'), 'measured scientific code changed')
    require(feature['shared_primitives_sha256'] == sha(ROOT / 'src/gems91/ced.py'), 'shared primitive drift')
    require(feature['inputs'] == card['inputs'] and not feature['catalogue_features'], 'feature provenance mismatch')
    require(feature['reference_rasters_used'] is False, 'prior submissions cannot be feature inputs')
    holdout = read('docs/s16/holdout.json')
    terms = {name: np.array(read(f'docs/s16/{name}-block-terms.json'), dtype=float)
             for name in ('pgrd', 'gravity_control', 'ced_benchmark')}
    # Replaying fixed arithmetic/bootstrap terms is validation, not another experiment.
    repeated = ev.pooled_summary(terms, draws=1000, seed=160025, candidate='pgrd')
    require(repeated == holdout['summary'], 'pooled terms/bootstrap or evaluator provenance drift')
    h = card['holdout_dti']; result = repeated['scores']['pgrd']
    require(h['label'] == 'HOLDOUT-DTI' and h['evaluator_version'] == ev.VERSION, 'metric label/version drift')
    require(h['value'] == result['dti'] and h['ci95'] == result['ci95'], 'headline metric/CI drift')
    require(h['withheld_positives'] == result['withheld_positive_pixels'] == 60988, 'positive count drift')
    require(h['split_sha256'] == holdout['split_sha256'], 'split identity drift')
    for name, scores in repeated['scores'].items():
        for key in ('tpw', 'fpw', 'fnw'):
            require(np.isclose(sum(f['arms'][name][key] for f in holdout['folds']), scores[key], rtol=1e-12), 'fold term sum mismatch')
    for fold in holdout['folds']:
        r = fold['receipt']
        require(r['evaluation_region_label_blind'] and r['shared_train_truth_components'] == 0, 'unsafe fold receipt')
        require(r['buffer_px'] == 80 and r['nearest_training_to_region_px'] > 80, 'training buffer mismatch')
    canary = read('docs/s16/canaries.json')
    require(set(canary['features']) == set(feature['files']) | {'ced_control_surface'}, 'missing feature canary')
    checks = [c for group in canary['features'].values() for c in group]
    require(len(checks) == 4 * card['canaries']['features_tested'], 'feature-fold canary count mismatch')
    require(all(c['status'] == 'PASS' and .5 <= c['symmetric_auc'] <= .90 for c in checks), 'failed or undefined canary')
    require(max(c['symmetric_auc'] for c in checks) == card['canaries']['max_symmetric_auc'], 'canary summary drift')
    inventory = read('registry/s16_comparison_inventory.json')
    for phase, filename in (('preplacement', 'surface'), ('final', 'final')):
        report = read(f'docs/s16/registry-{filename}.json')
        require(report['checked'] == len(report['comparisons']), 'registry count drift')
        require(report['checked'] + report['not_checked_after_stop'] == len(inventory['files']), 'registry scope drift')
        for expected, measured in zip(inventory['files'], report['comparisons']):
            require(expected['path'] == measured['file'] and expected['sha256'] == measured['sha256'], 'registry identity/order drift')
        require({k: v for k, v in report.items() if k != 'comparisons'} == card['registry_comparison'][phase], 'registry card drift')
    final = read('docs/s16/registry-final.json')
    require(final['status'] == 'DUPLICATE' and final['stopped_on'] == final['comparisons'][-1], 'missing literal duplicate stop')
    require(not any(r['status'] == 'DUPLICATE' for r in final['comparisons'][:-1]), 'scientific run continued past duplicate')
    require(final['stopped_on']['dots']['overlap_within_3px'] > .70, 'duplicate threshold not exceeded')
    require(card['automated_gates'] == gates(card), 'shared-gate state drift')
    require(card['submission_ready'] == card['ok_to_submit'] == submission_ready(card) is False, 'negative candidate promoted')
    require(card['verdict'] == 'negative' and card['slots_used'] == 0 and card['organizer_confirmed'] is None, 'unverified slot/score claim')
    require(card['experiments_run'] == 1 and card['elapsed_seconds'] < 7200, 'budget exceeded')
    return dict(status='PASS', scope='Artifact bytes + independent TIFF decoder + measured evidence replay',
                file=a['file'], sha256=card['raster_sha256'], zip_sha256=a['zip_sha256'],
                format_pass=True, evidence_consistent=True,
                template_and_catalogue_rechecked=with_data,
                ok_to_download=True, ok_to_submit=False,
                reason=card['verdict_reason'], geological_experiments_rerun=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--with-data', action='store_true')
    args = ap.parse_args()
    try:
        result = verify(args.with_data)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        print(json.dumps(dict(status='BLOCKED', ok_to_submit=False, error=str(exc))))
        return 1
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
