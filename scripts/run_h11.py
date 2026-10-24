#!/usr/bin/env python3
"""Run the single preregistered H11-1 experiment (docs/HYPOTHESES_H11.md). Never uploads.

Shared template evaluator, fold generator, placement geometry and registry gate are
imported from the existing harness (scripts/run_ced.py and vendor/gems57), not
reimplemented. Arms: h11 (candidate), gradient_control (slope magnitude only),
random_null (seeded random separated dots at equal per-fold mass).
Outputs are written to the gitignored outputs/h11/ first; publication is a separate decision.
"""
from __future__ import annotations

import argparse
import gc
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
import numpy as np
import rasterio
from gems91 import ced, h11
from gems91.io import sha256_file, dot_digest
from vendor.gems57 import evaluate_holdout as evaluator, spatial
from vendor.gems57.submission_writer import write_submission
from run_ced import registry_phase, dump  # shared registry gate; does NOT touch the CED run card

SAMPLE = ROOT / 'data/official/sample_submission.tif'
CATALOGUE = ROOT / 'data/official/existing_faults.tif'
STACK = ROOT / 'data/bridge/gems-geodawn-numerical-features.tif'
LOCK = ROOT / 'docs/h11-experiment.json'
CARD = ROOT / 'docs/run-card-H11.json'
OUT = ROOT / 'outputs/h11'
NOTE = 'H11-1 structure-tensor lineament coherence; research only, not approved for a slot.'


def verify_inputs():
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    wanted = {'sample_submission', 'existing_faults', 'training_features'}
    result = {}
    for entry in manifest['files']:
        if entry['id'] not in wanted:
            continue
        p = ROOT / 'data' / entry['local_subpath']
        digest = sha256_file(p)
        if digest != entry['sha256'] or p.stat().st_size != entry['bytes']:
            raise ValueError(f"Pinned input mismatch: {entry['id']}")
        result[entry['id']] = dict(sha256=digest, bytes=p.stat().st_size)
    pins = json.loads((ROOT / 'registry/template_pin.json').read_text())
    for name, digest in pins['sha256'].items():
        if sha256_file(ROOT / 'vendor/gems57' / name) != digest:
            raise ValueError(f'Shared template drift: {name}')
    return result


def run():
    if LOCK.exists():
        raise FileExistsError('H11-1 is already recorded (docs/h11-experiment.json). Do not silently rerun.')
    inputs = verify_inputs()
    inventory = json.loads((ROOT / 'registry/comparison_inventory.json').read_text())
    with rasterio.open(SAMPLE) as src:
        fp = np.isfinite(src.read(1)); shape = src.shape
        sample_meta = (src.count, src.shape, src.crs, src.transform)
    with rasterio.open(CATALOGUE) as src:
        if (src.count, src.shape, src.crs, src.transform) != sample_meta:
            raise ValueError('catalogue grid mismatch')
        catalogue = (src.read(1) > 0) & fp
    with rasterio.open(STACK) as src:
        if (src.shape, src.crs, src.transform) != (sample_meta[1], sample_meta[2], sample_meta[3]):
            raise ValueError('feature grid mismatch')
        assert src.descriptions[11].startswith('det_elev '), src.descriptions[11]
        elev = src.read(12)
    card = dict(schema='gems91.run-card.v2', run_id='H11-1-v1-20261024',
                started_utc=datetime.now(timezone.utc).isoformat(),
                hypothesis='Coherent, oriented elevation-gradient lineaments (structure-tensor anisotropy of detrended elevation) mark concealed or unmapped fault scarps.',
                mechanism='Anisotropic structure tensor at 3 and 6 px windows, geometric mean with gradient magnitude; fixed-density separated dots.',
                non_fault_mimic='Bedrock ridge or drainage fabric aligned with regional structure; cultural linear features; sub-100 m scarps unresolved at 100 m.',
                lane=dict(name='H11-1', assigned=False, status='PROVISIONAL_RESEARCH_ONLY',
                          reason='No single assigned method paragraph was supplied in the session brief.'),
                experiments_run=1, budget=dict(max_experiments=3, max_seconds=7200),
                holdout_dti=dict(label='HOLDOUT-DTI', value=None, evaluator_version=evaluator.VERSION,
                                 withheld_positives=None, ci95=None, status='NOT_RUN'),
                registry_comparison=dict(scope=inventory['scope'], complete_universal_registry=False,
                                         missing_scope=inventory['missing_scope']),
                raster_sha256=None, validator_output=dict(status='NOT_RUN'), submission_name=None,
                note=NOTE, verdict='negative', submission_ready=False, organizer_confirmed=None,
                slots_used=0, selector_approval=False, comparable_prior_holdout_best=None,
                inputs=inputs, evidence_class='HOLDOUT-DTI')
    dump(CARD, card)
    fields = h11.features(elev, fp)
    del elev; gc.collect()
    catalogue_check = dict(evidence_class='HOLDOUT-DTI', evaluator_version=evaluator.VERSION,
                           split='feature-alone AUROC over all catalogue pixels vs eligible non-catalogue pixels',
                           withheld_positive_pixels=int(catalogue.sum()),
                           features={n: ced.auc_canary(f, catalogue, fp) for n, f in fields.items() if n != 'raw_elevation'})
    dump(ROOT / 'docs/h11-canaries.json', catalogue_check)
    card['canaries'] = dict(status='PASS' if all(c['status'] == 'PASS' for c in catalogue_check['features'].values()) else 'LEAKAGE_SUSPECTED',
                            max_symmetric_auc=max(c['symmetric_auc'] for c in catalogue_check['features'].values()),
                            file='h11-canaries.json')
    if card['canaries']['status'] != 'PASS':
        return stop(card, 'Leakage canary failed (AUROC > 0.90): no placement, no promotion.')
    before = registry_phase(fields['surface'], fp, inventory, sample_meta)
    dump(ROOT / 'docs/h11-registry-surface.json', before)
    card['registry_comparison']['preplacement'] = {k: v for k, v in before.items() if k != 'comparisons'}
    if before['status'] == 'DUPLICATE':
        return stop(card, 'Pre-placement surface duplicated a registry raster; stopped before dot placement.')
    nblocks = ((shape[0] + 199) // 200) * ((shape[1] + 199) // 200)
    arms = ('h11', 'gradient_control', 'random_null')
    terms = {n: np.zeros((nblocks, 4), np.float64) for n in arms}
    receipts = []
    for fold_index, fold in enumerate(spatial.folds(catalogue, fp, buffer_px=80)):
        ys, xs = np.nonzero(fold['region'])
        if not len(ys):
            raise ValueError('empty spatial quadrant')
        sl = (slice(int(ys.min()), int(ys.max()) + 1), slice(int(xs.min()), int(xs.max()) + 1))
        budget = int(round(ced.DOT_BUDGET * int(fold['region'].sum()) / int(fp.sum())))
        small = {key: fold[key][sl] for key in ('region', 'visible', 'truth')}
        eligible = small['region'] & ~small['visible']
        rng = np.random.default_rng(1101 + fold_index)
        surfaces = {'h11': fields['surface'][sl], 'gradient_control': fields['gradient_control'][sl],
                    'random_null': rng.random(eligible.shape)}
        result = dict(receipt=fold['receipt'], budget=budget, arms={})
        for name in arms:
            p = ced.place(surfaces[name], eligible, budget)
            score, block_terms = evaluator.evaluate(p.astype(np.float32), small, fp[sl],
                                                    origin=(sl[0].start, sl[1].start), global_shape=shape)
            terms[name] += block_terms
            result['arms'][name] = score
            del p, block_terms
        receipts.append(result)
        print('Completed whole-component fold', fold['fold'], 'withheld positives', int(fold['truth'].sum()), flush=True)
    summary = evaluator.pooled_summary(terms, draws=1000, seed=520811, candidate='h11')
    dump(ROOT / 'docs/h11-holdout.json', dict(summary=summary, folds=receipts,
         scope='Known-catalogue hide-and-recover (catalogue recovery), not the hidden competition faults.'))
    score = summary['scores']['h11']
    card['holdout_dti'].update(value=score['dti'], ci95=score['ci95'],
                               withheld_positives=score['withheld_positive_pixels'], status='COMPLETED',
                               paired_controls=summary['paired_differences'], file='h11-holdout.json',
                               random_null=summary['scores']['random_null'])
    del terms; gc.collect()
    dots = ced.place(fields['surface'], fp & ~catalogue, ced.DOT_BUDGET)
    digest = dot_digest(dots)
    name = 'gems91-h11-v1-20261024-' + digest[:12]
    path = OUT / (name + '.tif')
    receipt = write_submission(path, dots.astype(np.float32), SAMPLE, fp, name=name, note=NOTE,
                               catalogue=catalogue,
                               metadata=dict(run_id=card['run_id'], dot_digest=digest, research_only=True))
    card.update(submission_name=name, raster_sha256=receipt['sha256'],
                artifact=dict(local_only='outputs/h11/' + path.name, bytes=receipt['bytes'],
                              dot_digest=digest, dots=int(dots.sum())),
                validator_output=dict(status='PASS' if receipt['validator']['all_checks_passed'] else 'FAIL',
                                      no_nan_inside_footprint=receipt['validator']['checks']['in_footprint_all_finite'],
                                      values_in_0_1=receipt['validator']['checks']['range_0_1_guaranteed'],
                                      crs_shape_transform_match=receipt['template_report']['ok'],
                                      checks=receipt['validator']['checks']))
    final = registry_phase(dots, fp, inventory, sample_meta, dots=dots)
    dump(ROOT / 'docs/h11-registry-final.json', final)
    card['registry_comparison']['final'] = {k: v for k, v in final.items() if k != 'comparisons'}
    correlations = [r['surface']['rank_correlation'] for r in before['comparisons'] if r.get('surface', {}).get('rank_correlation') is not None]
    overlaps = [r['dots']['overlap_within_3px'] for r in final['comparisons'] if r.get('dots', {}).get('overlap_within_3px') is not None]
    card['registry_comparison'].update(max_measured_surface_rank_correlation=max(correlations) if correlations else None,
                                       max_measured_final_dot_overlap_within_3px=max(overlaps) if overlaps else None)
    reason = ('Final dots exceeded a registry duplicate threshold; NOT OK TO SUBMIT.' if final['status'] == 'DUPLICATE'
              else 'Research artifact only: assigned lane, complete universal registry, comparable prior holdout best and selector approval remain unverified.')
    stop(card, reason)
    dump(LOCK, dict(run_id=card['run_id'], experiments_run=1, completed_utc=card['completed_utc'],
                    raster_sha256=card['raster_sha256'], verdict=card['verdict']))
    return card


def stop(card, reason):
    card.update(verdict='negative', verdict_reason=reason, submission_ready=False,
                completed_utc=datetime.now(timezone.utc).isoformat())
    dump(CARD, card)
    print(reason, flush=True)
    return card


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true', help='Run the one preregistered H11-1 experiment')
    args = ap.parse_args()
    if not args.run:
        print('Read docs/HYPOTHESES_H11.md, then --run. This never uploads or selects a competition submission.')
        return
    run()


if __name__ == '__main__':
    main()
