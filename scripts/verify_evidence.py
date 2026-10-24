#!/usr/bin/env python3
"""Cross-check measured JSON evidence without rerunning the stopped experiment."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


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
    uniqueness_bytes = (ROOT/'vendor/gems57/uniqueness.py').read_bytes()
    uniqueness_blob = hashlib.sha1(
        b'blob ' + str(len(uniqueness_bytes)).encode('ascii') + b'\0' + uniqueness_bytes
    ).hexdigest()
    if uniqueness_blob != template.get('git_blob_sha1', {}).get('uniqueness.py'):
        raise ValueError('Pinned shared uniqueness Git blob mismatch')
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
    if summary['implementation_sha256'] != {name:template['sha256'][name] for name in summary['implementation_sha256']}:
        raise ValueError('Evaluator implementation provenance drift')
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

    # Post-hoc H91 audit is measurement-only: bind the corrected card to its
    # actual TIFF hashes and the independently pinned direct lattice witness.
    h91 = load('evidence/run_card.json')
    h91_audit = load('evidence/h91_lattice_reaudit_20261024.json')
    h91_registry = load('evidence/registry_uniqueness.json')
    if h91.get('verdict') != 'negative' or h91.get('ok_to_submit') is not False:
        raise ValueError('H91 is not explicitly negative')
    if h91.get('ok_to_download_and_submit') is not False or h91.get('ok_to_download_for_research') is not True:
        raise ValueError('H91 research/download status drift')
    if not h91.get('submission_action', '').startswith('NOT OK TO SUBMIT;'):
        raise ValueError('H91 action verdict is missing or unsafe')
    witness = h91['registry_uniqueness']['direct_lattice_witness']
    if h91_registry.get('uniqueness_pass') is not False or h91_registry.get('is_duplicate') is not True:
        raise ValueError('H91 registry summary must be negative')
    if h91_registry.get('complete_accessible_scan') is not False:
        raise ValueError('H91 partial registry must not claim completeness')
    summary_witness = h91_registry.get('h91_literal_lattice_witness', {})
    if summary_witness.get('continuous_surface_spearman_full_footprint') is not None or summary_witness.get('continuous_surface_correlation_status') != 'UNVERIFIED':
        raise ValueError('H91 registry summary must explicitly preserve the missing surface measurement')
    if witness['candidate_dots_within_3px'] != 38302 or witness['candidate_dots'] != 38400:
        raise ValueError('H91 direct lattice count drift')
    close(witness['directed_overlap'], witness['candidate_dots_within_3px'] / witness['candidate_dots'])
    if witness['directed_overlap'] <= .70 or witness['duplicate_by_overlap'] is not True:
        raise ValueError('H91 literal overlap duplicate is missing')
    if witness.get('continuous_surface_spearman_full_footprint') is not None or witness.get('continuous_surface_correlation_status') != 'UNVERIFIED':
        raise ValueError('H91 continuous-surface comparison must remain explicitly unverified')
    if h91['submission']['submission_note_length'] != len(h91['submission']['submission_note']) or len(h91['submission']['submission_note']) > 140:
        raise ValueError('H91 historical note length drift')
    if h91['scores']['primary_holdout']['label'] != 'HOLDOUT-DTI' or h91['scores']['primary_holdout']['n_withheld_positives'] != 60988:
        raise ValueError('H91 score evidence class/count drift')
    h91_record = next(a for a in h91_audit['artifacts'] if a['label'] == 'H91-E1')
    if h91_record['candidate_sha256'] != h91['submission']['sha256_tif']:
        raise ValueError('H91 re-audit candidate hash drift')
    if h91_record['witness_comparison'].get('continuous_surface_spearman_full_footprint') is not None:
        raise ValueError('H91 re-audit must not invent a missing continuous-surface correlation')
    close(h91_record['witness_comparison']['directed_overlap'], witness['directed_overlap'])
    tif_path = ROOT / 'docs/downloads' / h91['submission']['research_tif']
    tif_bytes = tif_path.read_bytes()
    if hashlib.sha256(tif_bytes).hexdigest() != h91['submission']['sha256_tif']:
        raise ValueError('H91 research TIFF bytes do not match the run card')
    if len(tif_bytes) != h91['submission']['bytes_tif']:
        raise ValueError('H91 research TIFF byte-count drift')
    zip_path = ROOT / 'docs/downloads' / h91['submission']['research_zip']
    if hashlib.sha256(zip_path.read_bytes()).hexdigest() != h91['submission']['sha256_zip']:
        raise ValueError('H91 research ZIP bytes do not match the run card')
    with zipfile.ZipFile(zip_path) as archive:
        if archive.namelist() != [tif_path.name] or archive.read(tif_path.name) != tif_bytes:
            raise ValueError('H91 ZIP must contain only the byte-identical advertised TIFF')
    if h91_audit['registry_witness']['sha256'] != witness['registry_sha256']:
        raise ValueError('H91 registry-witness SHA mismatch')
    lattice_blob = h91_audit['registry_witness']['git_blob_sha1']
    if lattice_blob != '81c802618e6d46c6d62289d856ae74439439bbc6':
        raise ValueError('H91 lattice Git blob pin drift')
    if h91_audit['method_source']['git_blob_sha1'] != template.get('git_blob_sha1', {}).get('uniqueness.py', '478c9001dc9c323cd50ba820f53c71dc2f80f221'):
        raise ValueError('H91 shared uniqueness source blob drift')
    for result in h91_audit['artifacts']:
        if result['local_validation']['format_report_ok'] is not True or result['local_validation']['vendor_template_validate_all_checks_passed'] is not True:
            raise ValueError('H91/CED local format evidence must pass but not imply submission readiness')
        if result['witness_comparison']['duplicate_by_overlap'] is not True:
            raise ValueError('H91/CED direct duplicate result is missing')
    return dict(status='PASS', scope='Source provenance, pooled arithmetic, folds, canaries, CED registry stop, H91/CED direct lattice measurements, and negative-card consistency',
                geological_experiments_rerun=0, h91_posthoc_experiments=0,
                h91_submission_ready=False, submission_ready=False)


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
