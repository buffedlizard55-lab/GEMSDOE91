#!/usr/bin/env python3
"""Verify stopped S22 evidence and published bytes; never rerun or promote."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import rasterio
from vendor.gems57 import evaluate_holdout as EH
from vendor.gems57.validate import validate, assert_submittable
from scripts.source_integrity import verify_historical_source


def load(path):
    return json.loads((ROOT / path).read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify(with_data=False):
    c = load('docs/s22/run-card.json')
    h = load('docs/s22/holdout.json')
    refs = load('docs/s22/frozen-registry.json')
    surface = load('docs/s22/surface-checks.json')
    final = load('docs/s22/final-dot-checks.json')
    canaries = load('docs/s22/canaries.json')
    receipt = load('docs/s22/writer-receipt.json')
    if c['verdict'] != 'negative' or c['ok_to_submit'] is not False or c['submission_slots_used'] != 0:
        raise ValueError('Stopped experiment cannot promote')
    if c['leaderboard_score_estimate'] is not None or c['organizer_confirmed_score'] is not None:
        raise ValueError('No organizer receipt/calibration was measured')
    if c['experiments_run'] != 1 or not c['within_two_hour_budget']:
        raise ValueError('Budget receipt changed')
    if c['preregistration_sha256'] != sha(ROOT / 'docs/s22/preregistration.md'):
        raise ValueError('Preregistration changed after measurement')
    provenance = load('docs/s22/source-integrity.json')
    for name, digest in provenance['implementation_sha256'].items():
        verify_historical_source(ROOT, name, digest)
    if h['implementation_sha256'] != EH.implementation_hashes():
        raise ValueError('Shared evaluator implementation drift')
    rows = h['per_fold']
    values = np.array([[r['tpw'], r['fpw'], r['fnw'], r['n_truth']] for r in rows])
    pooled = h['scores']['omtj_e1']
    if c['holdout'] != pooled or pooled['evaluator_version'] != EH.VERSION:
        raise ValueError('Holdout card/receipt mismatch')
    np.testing.assert_allclose(values.sum(axis=0), [pooled[k] for k in ('tpw', 'fpw', 'fnw', 'withheld_positive_pixels')], atol=1e-8)
    np.testing.assert_allclose(EH.from_terms(values.sum(axis=0)), pooled['dti'], atol=1e-12)
    if not 0 <= pooled['ci95'][0] <= pooled['dti'] <= pooled['ci95'][1] <= 1:
        raise ValueError('Invalid holdout confidence interval')
    if len(canaries) != 28 or max(r['symmetric_auc'] for r in canaries) != c['leakage_canary']['max_symmetric_auc']:
        raise ValueError('Missing/drifted feature canary')
    if {(r['feature'], r['fold']) for r in canaries} != {(r['feature'], f) for r in canaries for f in range(4)}:
        raise ValueError('Feature/fold canary coverage incomplete')
    if any(r['symmetric_auc'] > .90 for r in canaries):
        raise ValueError('Canary should have stopped before placement')
    if len(surface['rows']) != len(refs['files']) or surface['errors']:
        raise ValueError('Surface registry coverage mismatch')
    if any(r['status'] != 'PASS' or abs(r['rank_correlation']) > .90 for r in surface['rows']):
        raise ValueError('Surface should have stopped before placement')
    if any(abs(r['rank_correlation']) > .90 for r in final[:-1]):
        raise ValueError('Final rank correlation should have caused an earlier stop')
    if any(r['status'] == 'DUPLICATE' for r in final[:-1]) or final[-1]['status'] != 'DUPLICATE':
        raise ValueError('Experiment did not stop on first duplicate')
    if final[-1]['overlap_within_3px'] <= .70:
        raise ValueError('Missing literal duplicate witness')
    if len(final) != c['correlation_overlap_vs_registry']['final_dot_checks']['checked_before_stop']:
        raise ValueError('Final check count changed')
    if c['registry_scope']['dense_exemptions'] or c['registry_scope']['organizer_complete']:
        raise ValueError('Registry scope cannot be broadened after the stop')
    tif = ROOT / c['artifact']['tif']; zipped = ROOT / c['artifact']['zip']
    if sha(tif) != c['raster_sha256'] or sha(tif) != receipt['sha256'] or sha(zipped) != c['artifact']['zip_sha256']:
        raise ValueError('Published byte drift')
    with zipfile.ZipFile(zipped) as z:
        if z.namelist() != [tif.name] or z.read(tif.name) != tif.read_bytes():
            raise ValueError('ZIP must contain exactly the published TIFF')
    with rasterio.open(tif) as ds:
        arr = ds.read(1)
    if hashlib.sha256(np.packbits(arr > 0).tobytes()).hexdigest() != c['artifact']['support_sha256']:
        raise ValueError('Prediction support drift')
    fp = cat = None
    if with_data:
        inputs = {r['id']: r for r in load('registry/data_manifest.json')['files']}
        arrays = {}
        for key in ('sample_submission', 'existing_faults'):
            row = inputs[key]; p = ROOT / 'data' / row['local_subpath']
            if sha(p) != row['sha256']:
                raise ValueError('Reference input hash mismatch')
            with rasterio.open(p) as ds:
                arrays[key] = ds.read(1)
        fp = np.isfinite(arrays['sample_submission'])
        cat = (arrays['existing_faults'] > 0) & fp
    validation = validate(tif, fp, cat)
    assert_submittable(validation)  # local numeric/grid check, never slot approval
    if validation['emitted_positive_pixels'] != 37654:
        raise ValueError('Final dot count drift')
    audit = load('docs/s22/nine-site-audit.json')
    if len(audit['sites']) != 9 or any(r['protocol_unique_among_nine'] or r['organizer_confirmed_score'] is not None for r in audit['sites']):
        raise ValueError('Nine-site historical evidence changed')
    return dict(status='PASS', scope='Historical bookkeeping and technical download only; not scientific approval',
        scientific_validity='INVALID: historical feature input included finite NoData sentinels',
        correction='docs/review-8e8d86f2/source-correction.json',
        raster_sha256=c['raster_sha256'], ok_to_submit=False,
        holdout_dot_count=int(sum(r['n_emitted'] for r in rows)), final_dot_count=validation['emitted_positive_pixels'],
        reference_checks='sample + catalogue' if with_data else 'pinned constants; source inputs not checked',
        tests='pooled arithmetic, recorded canary coverage, first duplicate stop, historical and corrected source hashes, TIFF/ZIP identity and range')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--with-data', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.with_data), indent=2, allow_nan=False))
