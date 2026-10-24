#!/usr/bin/env python3
"""Run the single preregistered CED91 research experiment, never a submission.

Shared template metric/splits/evaluator/writer are imported, not reimplemented.
A duplicate stops the experiment; invalid/missing evidence cannot promote it.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from gems91 import ced, novelty
from gems91.io import sha256_file, dot_digest
from vendor.gems57 import evaluate_holdout as evaluator, spatial
from vendor.gems57.submission_writer import write_submission

SAMPLE = ROOT / 'data/official/sample_submission.tif'
CATALOGUE = ROOT / 'data/official/existing_faults.tif'
STACK = ROOT / 'data/bridge/gems-geodawn-numerical-features.tif'
REPORT = ROOT / 'docs/run-card.json'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    def normalize(x):
        if isinstance(x, np.generic): return x.item()
        raise TypeError(type(x).__name__)
    text = json.dumps(value, indent=2, allow_nan=False, default=normalize) + '\n'
    tmp = path.with_suffix(path.suffix + '.part'); tmp.write_text(text); tmp.replace(path)


def verify_inputs():
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    wanted = {'sample_submission', 'existing_faults', 'training_features'}
    result = {}
    for entry in manifest['files']:
        if entry['id'] not in wanted: continue
        p = ROOT / 'data' / entry['local_subpath']
        if not p.is_file(): raise FileNotFoundError(p)
        digest = sha256_file(p)
        if digest != entry['sha256'] or p.stat().st_size != entry['bytes']:
            raise ValueError(f"Pinned input mismatch: {entry['id']}")
        result[entry['id']] = dict(sha256=digest, bytes=p.stat().st_size)
    pins = json.loads((ROOT / 'registry/template_pin.json').read_text())
    for name, digest in pins['sha256'].items():
        if sha256_file(ROOT / 'vendor/gems57' / name) != digest:
            raise ValueError(f'Shared template drift: {name}')
    return result


def load_features(fp, inputs):
    code = sha256_file(ROOT / 'src/gems91/ced.py')
    key = hashlib.sha256(json.dumps(dict(inputs=inputs, code=code), sort_keys=True).encode()).hexdigest()
    directory = ROOT / 'data/ced91' / key[:16]
    receipt = directory / 'cache.json'
    if receipt.is_file():
        info = json.loads(receipt.read_text())
        if info['cache_key'] != key: raise ValueError('feature cache key mismatch')
        arrays = {}
        for name, digest in info['files'].items():
            p = directory / (name + '.npy')
            if sha256_file(p) != digest: raise ValueError('feature cache content mismatch')
            arrays[name] = np.load(p, mmap_mode='r')
        return arrays, info
    with rasterio.open(STACK) as src, rasterio.open(SAMPLE) as sample:
        if src.shape != sample.shape or src.crs != sample.crs or src.transform != sample.transform:
            raise ValueError('cached feature grid does not match sample')
        m, g = src.read(1), src.read(13)
        info = dict(cache_key=key, code_sha256=code, inputs=inputs,
                    bands={str(i): dict(description=src.descriptions[i-1], tags=src.tags(i)) for i in (1, 13)},
                    usable_input_pixels={str(i): int((fp & np.isfinite(a) & (a > -1e30)).sum()) for i, a in ((1, m), (13, g))},
                    catalogue_features=[], fitted_parameters=False, files={})
    print('Building label-blind CED features from pinned cached stack.', flush=True)
    fields = ced.features(m, g, fp)
    directory.mkdir(parents=True, exist_ok=True)
    for name, value in fields.items():
        path = directory / (name + '.npy'); np.save(path, value, allow_pickle=False)
        info['files'][name] = sha256_file(path)
    dump(receipt, info)
    del fields, m, g; gc.collect()
    return {name: np.load(directory / (name + '.npy'), mmap_mode='r') for name in info['files']}, info


def registry_phase(surface, fp, inventory, sample_meta, dots=None):
    """Check all indexed files, stopping exactly at the first duplicate."""
    probe = novelty.SurfaceProbe(surface if dots is None else dots, fp)
    reports, by_hash = [], {}
    for index, entry in enumerate(inventory['files']):
        row = dict(file=entry['path'], sha256=entry['sha256'])
        try:
            if entry['sha256'] in by_hash:
                row.update(by_hash[entry['sha256']])
            else:
                path = ROOT / entry['path']
                if sha256_file(path) != entry['sha256']: raise ValueError('registry hash mismatch')
                with rasterio.open(path) as src:
                    if (src.count, src.shape, src.crs, src.transform) != sample_meta:
                        raise ValueError('registry band/grid mismatch')
                    a = src.read(1)
                checks = dict(surface=probe.compare(a))
                if dots is not None: checks['dots'] = novelty.dot_check(dots, a, fp)
                checks['status'] = ('DUPLICATE' if any(v['status']=='DUPLICATE' for v in checks.values()) else
                                    'UNVERIFIED' if any(v['status']=='UNVERIFIED' for v in checks.values()) else 'PASS')
                row.update(checks); by_hash[entry['sha256']] = checks
                del a
        except (OSError, ValueError, rasterio.errors.RasterioError) as exc:
            row.update(status='UNVERIFIED', reason=str(exc))
        reports.append(row)
        print(f"Registry {'surface' if dots is None else 'final'} {index+1}/{len(inventory['files'])}: {row['status']} {Path(entry['path']).name}", flush=True)
        if row['status'] == 'DUPLICATE':
            return dict(status='DUPLICATE', stopped_on=row, checked=len(reports),
                        not_checked_after_stop=len(inventory['files'])-len(reports), comparisons=reports)
    return dict(status='UNVERIFIED' if any(r['status']=='UNVERIFIED' for r in reports) else 'PASS_WITHIN_INDEXED_SCOPE',
                checked=len(reports), not_checked_after_stop=0, comparisons=reports)


def stop_card(card, reason):
    card.update(verdict='negative', verdict_reason=reason, submission_ready=False,
                completed_utc=datetime.now(timezone.utc).isoformat())
    dump(REPORT, card)
    print(reason, flush=True)
    return card


def run():
    if (ROOT / 'docs/ced-experiment.json').exists():
        raise FileExistsError('This preregistered experiment is already recorded. Verify it; do not silently run another experiment.')
    inputs = verify_inputs()
    inventory = json.loads((ROOT / 'registry/comparison_inventory.json').read_text())
    with rasterio.open(SAMPLE) as src:
        fp = np.isfinite(src.read(1)); shape = src.shape
        sample_meta = (src.count, src.shape, src.crs, src.transform)
    with rasterio.open(CATALOGUE) as src:
        if (src.count, src.shape, src.crs, src.transform) != sample_meta:
            raise ValueError('catalogue grid mismatch')
        catalogue = (src.read(1) > 0) & fp
    card = dict(schema='gems91.run-card.v2', run_id='CED91-v1-20261024',
                started_utc=datetime.now(timezone.utc).isoformat(),
                hypothesis='Stable cross-scale magnetic–gravity edge-centroid displacement can reveal concealed fault contacts.',
                mechanism='Parent-free edge persistence, axial gradient alignment and signed displacement consistency; fixed-density separated dots.',
                non_fault_mimic='Intrusive lithological contact; survey flight-line seam is a second control concern.',
                lane=dict(name='CED91', assigned=False, status='PROVISIONAL_RESEARCH_ONLY', reason='No single assigned method paragraph supplied.'),
                experiments_run=1, budget=dict(max_experiments=3, max_seconds=7200),
                holdout_dti=dict(label='HOLDOUT-DTI', value=None, evaluator_version=evaluator.VERSION,
                                 withheld_positives=None, ci95=None, status='NOT_RUN'),
                registry_comparison=dict(scope=inventory['scope'], complete_universal_registry=False,
                                         missing_scope=inventory['missing_scope']),
                raster_sha256=None, validator_output=dict(status='NOT_RUN'),
                submission_name=None, note='CED91 research only; parent-free magnetic/gravity centroid displacement. Not approved for a competition slot.',
                verdict='negative', submission_ready=False, organizer_confirmed=None,
                slots_used=0, selector_approval=False, comparable_prior_holdout_best=None,
                inputs=inputs, evidence_class='HOLDOUT-DTI')
    dump(REPORT, card)
    fields, feature_info = load_features(fp, inputs)
    dump(ROOT / 'docs/ced-feature-receipt.json', feature_info)
    card['feature_cache_key'] = feature_info['cache_key']
    # Since the transformation has no fitted/catalogue-derived parameters, each
    # pixel has the same feature value when its whole component is hidden.
    # The union of the four disjoint held-out quadrants is the exact footprint.
    canaries = {name: ced.auc_canary(field, catalogue, fp) for name, field in fields.items()}
    canary_report = dict(evidence_class='HOLDOUT-DTI', evaluator_version=evaluator.VERSION,
                         split='label-blind-quadrants-v2', withheld_positive_pixels=int(catalogue.sum()),
                         interpretation='Pooled feature-alone AUROC over union of disjoint held-out quadrants; no label-fitted feature.',
                         features=canaries)
    dump(ROOT / 'docs/ced-canaries.json', canary_report)
    card['canaries'] = dict(status='PASS' if all(c['status']=='PASS' for c in canaries.values()) else 'LEAKAGE_SUSPECTED',
                            max_symmetric_auc=max(c['symmetric_auc'] for c in canaries.values()), file='ced-canaries.json')
    if card['canaries']['status'] != 'PASS':
        return stop_card(card, 'Leakage canary failed: no placement, no promotion.')
    before = registry_phase(fields['surface'], fp, inventory, sample_meta)
    dump(ROOT / 'docs/ced-registry-surface.json', before)
    card['registry_comparison']['preplacement'] = {k:v for k,v in before.items() if k != 'comparisons'}
    if before['status'] == 'DUPLICATE':
        return stop_card(card, 'Pre-placement surface duplicated a registry raster; stopped before dot placement.')
    gc.collect()
    nblocks = ((shape[0]+199)//200) * ((shape[1]+199)//200)
    terms = {n: np.zeros((nblocks, 4), np.float64) for n in ('ced', 'magnetic_control')}
    receipts = []
    for fold in spatial.folds(catalogue, fp, buffer_px=80):
        ys, xs = np.nonzero(fold['region'])
        if not len(ys): raise ValueError('empty spatial quadrant')
        sl = (slice(int(ys.min()), int(ys.max())+1), slice(int(xs.min()), int(xs.max())+1))
        # Independent fixed density; rounding is geometry-only, not truth-dependent.
        budget = int(round(ced.DOT_BUDGET * int(fold['region'].sum()) / int(fp.sum())))
        small = {key: fold[key][sl] for key in ('region', 'visible', 'truth')}
        result = dict(receipt=fold['receipt'], budget=budget, arms={})
        for name, feature in (('ced', 'surface'), ('magnetic_control', 'magnetic_persistence')):
            p = ced.place(fields[feature][sl], small['region'] & ~small['visible'], budget)
            score, block_terms = evaluator.evaluate(p.astype(np.float32), small, fp[sl],
                            origin=(sl[0].start, sl[1].start), global_shape=shape)
            terms[name] += block_terms
            result['arms'][name] = score
            del p, block_terms
        receipts.append(result)
        print('Completed whole-component fold', fold['fold'], 'withheld positives', int(fold['truth'].sum()), flush=True)
    summary = evaluator.pooled_summary(terms, draws=1000, seed=520810, candidate='ced')
    dump(ROOT / 'docs/ced-holdout.json', dict(summary=summary, folds=receipts,
        scope='Known-catalogue hide-and-recover, not hidden competition faults or vents.',
        legacy_r0_not_comparable='R0 was built with the full catalogue and is not an independent fold-regenerated baseline.'))
    score = summary['scores']['ced']
    card['holdout_dti'].update(value=score['dti'], ci95=score['ci95'],
                              withheld_positives=score['withheld_positive_pixels'], status='COMPLETED',
                              paired_control=summary['paired_differences']['magnetic_control'], file='ced-holdout.json')
    del fold, small, terms; gc.collect()
    dots = ced.place(fields['surface'], fp & ~catalogue, ced.DOT_BUDGET)
    digest = dot_digest(dots)
    name = 'gems91-ced-v1-20261024-' + digest[:12]
    path = ROOT / 'docs/downloads' / (name + '.tif')
    receipt = write_submission(path, dots.astype(np.float32), SAMPLE, fp,
        name=name, note=card['note'], catalogue=catalogue,
        metadata=dict(run_id=card['run_id'], dot_digest=digest,
                      research_only=True, feature_cache_key=feature_info['cache_key']))
    # The file is exported as a research artifact before the post-placement gate.
    # A duplicate is still a negative deliverable, never a promotion exemption.
    card.update(submission_name=name, raster_sha256=receipt['sha256'],
                artifact=dict(file='downloads/' + path.name, zip='downloads/' + path.with_suffix('.zip').name,
                              receipt='downloads/' + path.with_suffix('.json').name,
                              bytes=receipt['bytes'], dot_digest=digest, dots=int(dots.sum())),
                validator_output=dict(status='PASS' if receipt['validator']['all_checks_passed'] else 'FAIL',
                    no_nan_inside_footprint=receipt['validator']['checks']['in_footprint_all_finite'],
                    values_in_0_1=receipt['validator']['checks']['range_0_1_guaranteed'],
                    crs_shape_transform_match=receipt['template_report']['ok'],
                    checks=receipt['validator']['checks']))
    final = registry_phase(dots, fp, inventory, sample_meta, dots=dots)
    dump(ROOT / 'docs/ced-registry-final.json', final)
    card['registry_comparison']['final'] = {k:v for k,v in final.items() if k != 'comparisons'}
    correlations = [r['surface']['rank_correlation'] for r in before['comparisons']
                    if r.get('surface', {}).get('rank_correlation') is not None]
    overlaps = [r['dots']['overlap_within_3px'] for r in final['comparisons']
                if r.get('dots', {}).get('overlap_within_3px') is not None]
    card['registry_comparison'].update(max_measured_surface_rank_correlation=max(correlations) if correlations else None,
                                      max_measured_final_dot_overlap_within_3px=max(overlaps) if overlaps else None)
    if final['status'] == 'DUPLICATE':
        reason = 'Final dots exceeded a literal registry duplicate threshold; experiment stopped. Download for research only; NOT OK TO SUBMIT.'
    else:
        reason = 'Research artifact only: assigned lane, universal registry completeness, comparable prior holdout best and separate selector approval remain unverified.'
    stop_card(card, reason)
    dump(ROOT / 'docs/ced-experiment.json', dict(run_id=card['run_id'], experiments_run=1,
                 completed_utc=card['completed_utc'], raster_sha256=card['raster_sha256'], verdict=card['verdict']))
    return card


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true', help='Run the one preregistered experiment; no weekly slot is used')
    args = ap.parse_args()
    if not args.run:
        print('Read docs/HYPOTHESES_CED.md, then --run. This never uploads or selects a competition submission.')
        return
    run()


if __name__ == '__main__': main()
