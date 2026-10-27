#!/usr/bin/env python3
"""Cross-check measured JSON evidence without rerunning the stopped experiment."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.source_integrity import verify_historical_source  # noqa: E402


def load(name):
    return json.loads((ROOT / name).read_text())


def close(a, b):
    if not math.isfinite(float(a)) or not math.isfinite(float(b)) or not math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-9):
        raise ValueError(f'Evidence arithmetic drift: {a} != {b}')


def verify():
    card = load('docs/run-card.json')
    experiment = load('docs/ced-experiment.json')
    inputs = {r['id']: r for r in load('registry/data_manifest.json')['files']}
    template = load('registry/template_pin.json')
    for name, digest in template['sha256'].items():
        if hashlib.sha256((ROOT/'vendor/gems57'/name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Shared source changed: {name}')
    if hashlib.sha256((ROOT/'scripts/run_ced.py').read_bytes()).hexdigest() != experiment['runner_sha256']:
        raise ValueError('Measured experiment runner changed; do not silently rewrite provenance')
    feature = load('docs/ced-feature-receipt.json')
    if hashlib.sha256((ROOT/'src/gems91/ced.py').read_bytes()).hexdigest() != feature['code_sha256']:
        raise ValueError('Measured scientific feature code changed')
    for name, pin in card['inputs'].items():
        if any(pin[key] != inputs[name][key] for key in ('sha256','bytes')):
            raise ValueError('Run-card input pin mismatch')
    if card['inputs'] != feature['inputs']:
        raise ValueError('Feature/run-card input identity mismatch')
    if feature['catalogue_features'] or feature['fitted_parameters']:
        raise ValueError('This preregistered CED surface must be label-blind')
    holdout = load('docs/ced-holdout.json')
    summary = holdout['summary']
    if summary['evaluator_version'] != card['holdout_dti']['evaluator_version']:
        raise ValueError('Evaluator version mismatch')
    n = sum(f['receipt']['truth_px'] for f in holdout['folds'])
    if len(holdout['folds']) != 4 or n != card['holdout_dti']['withheld_positives']:
        raise ValueError('Fold/pooled withheld-positive mismatch')
    if sum(f['budget'] for f in holdout['folds']) != card['artifact']['dots']:
        raise ValueError('Geometry-only budgets do not pool to the final budget')
    for fold in holdout['folds']:
        receipt = fold['receipt']
        if not receipt['evaluation_region_label_blind'] or receipt['shared_train_truth_components']:
            raise ValueError('Unsafe split receipt')
        if receipt['buffer_px'] != 80:
            raise ValueError('Buffer drift')
        minimum = receipt['nearest_training_to_region_px']
        if minimum is not None and minimum <= receipt['buffer_px']:
            raise ValueError('Training buffer violated')
    for name, score in summary['scores'].items():
        for key in ('tpw','fpw','fnw'):
            close(sum(f['arms'][name][key] for f in holdout['folds']), score[key])
        close(score['tpw']+score['fnw'], n)
        close(score['tpw']/(score['tpw']+.2*score['fpw']+.8*score['fnw']+1e-12), score['dti'])
        if score['withheld_positive_pixels'] != n or not (0<=score['ci95'][0]<=score['ci95'][1]<=1):
            raise ValueError('Invalid score count/CI')
    candidate = summary['scores']['ced']
    close(candidate['dti'], card['holdout_dti']['value'])
    if candidate['ci95'] != card['holdout_dti']['ci95']:
        raise ValueError('Run-card confidence interval drift')
    if summary['paired_differences']['magnetic_control'] != card['holdout_dti']['paired_control']:
        raise ValueError('Run-card paired comparison drift')
    for name, digest in summary['implementation_sha256'].items():
        verify_historical_source(ROOT, 'vendor/gems57/' + name, digest)
    canary = load('docs/ced-canaries.json')
    if set(canary['features']) != set(feature['files']):
        raise ValueError('A raw/transformed feature is missing its single-feature canary')
    for result in canary['features'].values():
        if result['withheld_positive_pixels'] != n or result['symmetric_auc'] > .90 or result['status'] != 'PASS':
            raise ValueError('Canary mismatch or leakage')
    inventory = load('registry/comparison_inventory.json')
    for phase, filename in (('preplacement','docs/ced-registry-surface.json'),('final','docs/ced-registry-final.json')):
        report = load(filename)
        if len(report['comparisons']) != report['checked'] or report['checked']+report['not_checked_after_stop'] != len(inventory['files']):
            raise ValueError('Registry accounting mismatch')
        for got, expected in zip(report['comparisons'],inventory['files']):
            if got['file'] != expected['path'] or got['sha256'] != expected['sha256']:
                raise ValueError('Registry ordering/identity drift')
        if {k:v for k,v in report.items() if k!='comparisons'} != card['registry_comparison'][phase]:
            raise ValueError('Run-card registry phase drift')
    final = load('docs/ced-registry-final.json')
    if final['status'] != 'DUPLICATE' or final['stopped_on'] != final['comparisons'][-1]:
        raise ValueError('Duplicate must be the stop, not an ignored warning')
    if final['stopped_on']['dots']['overlap_within_3px'] <= .70:
        raise ValueError('Reported duplicate does not exceed threshold')
    if any(r['status']=='DUPLICATE' for r in final['comparisons'][:-1]):
        raise ValueError('The run continued after a duplicate')
    if card['verdict'] != 'negative' or card['submission_ready'] or card['slots_used'] != 0:
        raise ValueError('Negative experiment must not be promoted or use a slot')
    return dict(status='PASS', scope='Source provenance, pooled arithmetic, folds, canaries, registry stop and negative-card consistency',
                geological_experiments_rerun=0, submission_ready=False)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
