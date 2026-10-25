#!/usr/bin/env python3
"""One preregistered S16-PGRD research experiment. No selector or upload.

Template scoring/writing and existing cached-feature/novelty primitives are
reused. The first duplicate ends scientific work; a negative is still published.
"""
from __future__ import annotations

from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
import numpy as np
import rasterio
from scipy.spatial import cKDTree
from gems91 import ced, pgrd, readiness
from gems91.io import sha256_file
from scripts import run_ced
from vendor.gems57 import evaluate_holdout as evaluator, spatial
from vendor.gems57.submission_writer import write_submission

SAMPLE = ROOT / 'data/official/sample_submission.tif'
CATALOGUE = ROOT / 'data/official/existing_faults.tif'
STACK = ROOT / 'data/bridge/gems-geodawn-numerical-features.tif'
PREREG = ROOT / 'docs/HYPOTHESES_S16.md'
CARD = ROOT / 'docs/run-card-S16.json'
OUT = ROOT / 'docs/s16'


def dump(path, obj):
    run_ced.dump(path, obj)


def log(text):
    print(f'[{datetime.now(timezone.utc).isoformat()}] {text}', flush=True)


def cached_features(fp, inputs):
    identity = dict(inputs=inputs, code_sha256=sha256_file(ROOT / 'src/gems91/pgrd.py'),
                    shared_primitives_sha256=sha256_file(ROOT / 'src/gems91/ced.py'))
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    cache = ROOT / 'data/derived/pgrd' / key
    receipt = cache / 'cache.json'
    if receipt.is_file():
        info = json.loads(receipt.read_text())
        if info['cache_key'] != key:
            raise ValueError('cache identity mismatch')
        for name, digest in info['files'].items():
            if sha256_file(cache / (name + '.npy')) != digest:
                raise ValueError('feature-cache bytes changed')
    else:
        with rasterio.open(STACK) as ds, rasterio.open(SAMPLE) as s:
            if (ds.shape, ds.crs, ds.transform) != (s.shape, s.crs, s.transform):
                raise ValueError('feature/template grid mismatch')
            if ds.tags(2).get('band_name') != 'rtp' or ds.tags(13).get('band_name') != 'iso_grav_anom':
                raise ValueError('unexpected input band identities')
            m, g = ds.read(2), ds.read(13)
            info = dict(cache_key=key, **identity, catalogue_features=[], reference_rasters_used=False,
                        band_tags={str(i): ds.tags(i) for i in (2, 13)}, files={},
                        feature_model='label-blind; no supervised or catalogue fit')
        fields = pgrd.features(m, g, fp)
        cache.mkdir(parents=True, exist_ok=True)
        for name, field in fields.items():
            path = cache / (name + '.npy')
            np.save(path, field, allow_pickle=False)
            info['files'][name] = sha256_file(path)
        dump(receipt, info)
        del fields, m, g
        gc.collect()
    return {n: np.load(cache / (n + '.npy'), mmap_mode='r') for n in info['files']}, info


def freeze_inventory():
    """Extend, never shrink, the historical index before generating a candidate.

    Missing old entries remain visible. This frozen per-run snapshot is not a
    universal fleet inventory; a source-page feed is not a raster comparison.
    """
    inv = json.loads((ROOT / 'registry/comparison_inventory.json').read_text())
    rows = list(inv['files'])
    paths = {r['path'] for r in rows}
    for p in sorted((ROOT / 'docs/downloads').glob('*.tif')):
        rel = p.relative_to(ROOT).as_posix()
        if rel not in paths:
            rows.append(dict(path=rel, sha256=sha256_file(p), bytes=p.stat().st_size,
                             source_url='inherited checkout prediction; frozen before S16 generation'))
            paths.add(rel)
    # Preserve the frozen original ordering (in particular, dense references).
    inv.update(files=rows, scope=inv['scope'] + '; plus every inherited docs/downloads/*.tif',
               complete_universal_registry=False)
    dump(ROOT / 'registry/s16_comparison_inventory.json', inv)
    return inv


def phase_summary(report):
    return {k: v for k, v in report.items() if k != 'comparisons'}


def stop(card, reason, started):
    card.update(verdict='negative', verdict_reason=reason, submission_ready=False,
                completed_utc=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=round(time.monotonic() - started, 3))
    card['automated_gates'] = readiness.gates(card)
    card['ok_to_download'] = card.get('validator_output', {}).get('status') == 'PASS'
    card['ok_to_submit'] = readiness.submission_ready(card)
    dump(CARD, card)
    log(reason)
    return card


def run():
    start = time.monotonic()
    if CARD.exists():
        raise FileExistsError('S16 experiment already recorded; do not silently rerun or tune it')
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = run_ced.verify_inputs()
    inventory = freeze_inventory()
    with rasterio.open(SAMPLE) as s:
        fp = np.isfinite(s.read(1)); shape = s.shape
        meta = (s.count, s.shape, s.crs, s.transform)
    with rasterio.open(CATALOGUE) as s:
        if (s.count, s.shape, s.crs, s.transform) != meta:
            raise ValueError('catalogue/template grid mismatch')
        cat = (s.read(1) > 0) & fp
    card = dict(schema_version='gems91.s16-pgrd.v1', branch='arena/400a3f1a-gemsdoe91',
        started_utc=datetime.now(timezone.utc).isoformat(),
        preregistration=dict(path='docs/HYPOTHESES_S16.md', sha256=sha256_file(PREREG)),
        lane=dict(name='S16-PGRD', assigned=False, status='PROVISIONAL_RESEARCH_ONLY',
                  reason='No single-method assignment paragraph in user message.'),
        hypothesis='Coherent gravity edges unexplained by locally proportional band-limited RTP pseudogravity may locate concealed altered contacts.',
        mechanism='Label-blind 1/|k| magnetic integration, local ridge transfer residual, two-scale residual/gravity edge persistence and residual coherence.',
        named_non_fault_mimic_process='Unaltered nonmagnetic granite-carbonate contact; reversed-polarity lava and survey-line seams also mimic the signal.',
        experiments_run=1, budget=dict(max_experiments=3, planned_candidates=1, max_seconds=7200),
        holdout_dti=dict(label='HOLDOUT-DTI', evaluator_version=evaluator.VERSION,
                         value=None, ci95=None, withheld_positives=None, status='NOT_RUN'),
        comparable_prior_holdout_best=None, organizer_confirmed=None,
        selector_approval=False, selector_receipt=None, slots_used=0,
        registry_comparison=dict(scope=inventory['scope'], complete_universal_registry=False,
                                 inventory='registry/s16_comparison_inventory.json',
                                 missing_scope=inventory['missing_scope']),
        inputs=inputs, raster_sha256=None, validator_output=dict(status='NOT_RUN'),
        submission_name=None, note='S16-PGRD: magnetic-gravity transfer residual; 37654 new dots. Research negative; do not submit.',
        verdict='negative', submission_ready=False)
    dump(CARD, card)  # fail closed even if interrupted
    log('Building hash-addressed PGRD features from pinned competition stack')
    fields, feature_receipt = cached_features(fp, inputs)
    dump(OUT / 'features.json', feature_receipt)
    card['features'] = dict(file='s16/features.json', cache_key=feature_receipt['cache_key'], count=len(fields))
    # Reuse the historical cached feature implementation, not its emitted TIFF.
    ced_fields, ced_receipt = run_ced.load_features(fp, inputs)
    dump(OUT / 'control-features.json', ced_receipt)
    log('Per-feature, per-fixed-quadrant leakage canaries')
    canaries = {}
    split_digest = hashlib.sha256()
    fold_receipts = []
    for fold in spatial.folds(cat, fp, buffer_px=80):
        fold_receipts.append(fold['receipt'])
        for key in ('region', 'truth', 'train', 'visible'):
            split_digest.update(np.packbits(fold[key]).tobytes())
        active = fold['region'] & ~fold['visible']
        for name, field in {**fields, 'ced_control_surface': ced_fields['surface']}.items():
            check = ced.auc_canary(field, fold['truth'], active)
            canaries.setdefault(name, []).append(check)
    canary_report = dict(label='HOLDOUT-DTI', statistic='feature-alone symmetric AUROC, not a DTI score',
                        evaluator_version=evaluator.VERSION, split_sha256=split_digest.hexdigest(),
                        withheld_positives=int(cat.sum()), features=canaries,
                        threshold=.90, passing_is_not_proof_of_no_leakage=True)
    dump(OUT / 'canaries.json', canary_report)
    worst = max(c['symmetric_auc'] for cc in canaries.values() for c in cc)
    passed = all(c['status'] == 'PASS' for cc in canaries.values() for c in cc)
    card['canaries'] = dict(status='PASS' if passed else 'LEAKAGE_SUSPECTED', max_symmetric_auc=worst,
                           features_tested=len(canaries), file='s16/canaries.json')
    if not passed:
        return stop(card, 'Canary failed. No placement or scientific continuation.', start)
    log('Full-footprint exact-rank pre-placement check')
    before = run_ced.registry_phase(fields['surface'], fp, inventory, meta)
    dump(OUT / 'registry-surface.json', before)
    card['registry_comparison']['preplacement'] = phase_summary(before)
    card['registry_comparison']['max_measured_surface_rank_correlation'] = max(
        (abs(r.get('surface', {}).get('rank_correlation') or 0) for r in before['comparisons']), default=None)
    if before['status'] == 'DUPLICATE':
        return stop(card, 'Surface duplicated registry; stopped before any dot placement.', start)
    if time.monotonic() - start > 6500:
        return stop(card, 'Wall-clock guard stopped before scoring/placement.', start)
    log('One candidate experiment, matched gravity ablation and frozen CED benchmark')
    nblocks = ((shape[0] + 199) // 200) * ((shape[1] + 199) // 200)
    terms = {n: np.zeros((nblocks, 4), np.float64) for n in ('pgrd', 'gravity_control', 'ced_benchmark')}
    fold_results = []
    for fold in spatial.folds(cat, fp, buffer_px=80):
        ys, xs = np.nonzero(fold['region'])
        sl = (slice(int(ys.min()), int(ys.max()) + 1), slice(int(xs.min()), int(xs.max()) + 1))
        small = {k: fold[k][sl] for k in ('region', 'visible', 'truth')}
        row = dict(receipt=fold['receipt'], arms={})
        for name, feature in (('pgrd', 'surface'), ('gravity_control', 'gravity_persistence'),
                              ('ced_benchmark', 'surface')):
            if name == 'ced_benchmark':
                quota = int(round(ced.DOT_BUDGET * int(fold['region'].sum()) / int(fp.sum())))
                dots = ced.place(ced_fields[feature][sl], small['region'] & ~small['visible'], quota)
            else:
                # Critical: neither region, truth, buffer nor all-catalogue are passed to placement.
                global_dots = ced.place(fields[feature], fp & ~fold['visible'], pgrd.DOT_BUDGET)
                dots = global_dots[sl]
            result, block_terms = evaluator.evaluate(dots.astype(np.float32), small, fp[sl],
                origin=(sl[0].start, sl[1].start), global_shape=shape)
            terms[name] += block_terms
            row['arms'][name] = result
            log(f"Fold {fold['fold']} {name}: {result['dti']:.6f} HOLDOUT-DTI; n={result['n_truth']} (CI pooled below)")
            del dots, block_terms
            if name != 'ced_benchmark':
                del global_dots
        fold_results.append(row)
        gc.collect()
    summary = evaluator.pooled_summary(terms, draws=1000, seed=160025, candidate='pgrd')
    for name, arr in terms.items():
        dump(OUT / (name + '-block-terms.json'), arr.tolist())
    dump(OUT / 'holdout.json', dict(summary=summary, folds=fold_results, split_sha256=split_digest.hexdigest()))
    h = summary['scores']['pgrd']
    card['holdout_dti'] = dict(label='HOLDOUT-DTI', evaluator_version=evaluator.VERSION,
        split_sha256=split_digest.hexdigest(), value=h['dti'], ci95=h['ci95'],
        withheld_positives=h['withheld_positive_pixels'], status='COMPLETED', file='s16/holdout.json',
        paired_controls=summary['paired_differences'],
        ci_method='1000 paired 20km physical-block resamples; conditional on catalogue and fixed design, not leaderboard uncertainty')
    expected_ced = json.loads((ROOT / 'docs/ced-holdout.json').read_text())['summary']['scores']['ced']['dti']
    measured_ced = summary['scores']['ced_benchmark']['dti']
    if not np.isclose(expected_ced, measured_ced, rtol=0, atol=1e-10):
        return stop(card, 'Historical CED benchmark did not reproduce; scientific gate failed.', start)
    card['benchmark_integrity'] = dict(ced_reproduced=True, absolute_difference=abs(expected_ced - measured_ced),
        note='CED is a reproduced comparator, not a certified repository-wide current best. Other historical instruments are not comparable.')
    log(f"Pooled {h['dti']:.6f} HOLDOUT-DTI, CI {h['ci95']}")
    # Full inference uses the same emitter and global budget as each OOF prediction.
    final = ced.place(fields['surface'], fp & ~cat, pgrd.DOT_BUDGET)
    digest = hashlib.sha256(final.astype(np.uint8).tobytes()).hexdigest()
    tag = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name = f'gems91-s16-pgrd-{tag}-{digest[:12]}'
    path = ROOT / 'docs/downloads' / (name + '-zeros.tif')
    receipt = write_submission(path, final.astype(np.float32), SAMPLE, fp, note=card['note'], name=name,
        catalogue=cat, metadata=dict(lane='S16-PGRD', hypothesis_prereg_sha256=card['preregistration']['sha256'],
                                   negative_research_only=True, no_prior_submission_used=True))
    dump(OUT / 'writer-receipt.json', receipt)
    points = np.argwhere(final)
    minimum_spacing = float(cKDTree(points).query(points, k=2)[0][:, 1].min())
    with rasterio.open(path) as s:
        arr = s.read(1)
        checks = dict(single_band=s.count == 1, float32=s.dtypes == ('float32',),
            crs_match=s.crs == meta[2], shape_match=s.shape == shape, transform_match=s.transform == meta[3],
            all_cells_finite=bool(np.isfinite(arr).all()), range_0_1=bool((arr >= 0).all() and (arr <= 1).all()),
            zero_outside=bool((arr[~fp] == 0).all()), zero_on_catalogue=bool((arr[cat] == 0).all()),
            no_nodata_tag=s.nodata is None, exact_dot_count=int((arr > 0).sum()) == pgrd.DOT_BUDGET,
            spacing_strictly_over_3px=minimum_spacing > 3,
            identity_new_vs_frozen_hashes=receipt['sha256'] not in {x['sha256'] for x in inventory['files']})
        validator = dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
            no_nan_inside_footprint=bool(np.isfinite(arr[fp]).all()), values_in_0_1=checks['range_0_1'],
            crs_shape_transform_match=checks['crs_match'] and checks['shape_match'] and checks['transform_match'],
            crs=str(s.crs), shape=list(s.shape), transform=list(s.transform)[:6],
            min=float(arr.min()), max=float(arr.max()), nan_inside=int(np.isnan(arr[fp]).sum()),
            nan_anywhere=int(np.isnan(arr).sum()), positive_pixels=int(final.sum()), min_spacing_px=minimum_spacing,
            source='Reopened generated TIFF; shared writer also reopens ZIP and verifies its exact TIFF bytes.')
    del arr
    card.update(submission_name=name, raster_sha256=receipt['sha256'], raster_pixel_sha256=digest,
                validator_output=validator,
                artifact=dict(file='downloads/' + path.name, zip='downloads/' + receipt['zip_file'],
                              bytes=path.stat().st_size, zip_sha256=receipt['zip_sha256'],
                              audit='s16/writer-receipt.json'),
                byte_identity_unique=True,
                byte_identity_caveat='Different bytes are not a protocol uniqueness pass.')
    if not all(checks.values()):
        return stop(card, 'Re-read output validator failed; no submission.', start)
    # Final scientific operation: stop at first literal overlap/rank duplicate.
    after = run_ced.registry_phase(fields['surface'], fp, inventory, meta, dots=final)
    dump(OUT / 'registry-final.json', after)
    card['registry_comparison']['final'] = phase_summary(after)
    card['registry_comparison']['max_measured_final_dot_overlap_within_3px'] = max(
        (r.get('dots', {}).get('overlap_within_3px') or 0 for r in after['comparisons']), default=None)
    card['registry_comparison']['max_measured_final_dot_rank_correlation'] = max(
        (abs(r.get('surface', {}).get('rank_correlation') or 0) for r in after['comparisons']), default=None)
    reason = ('Literal Rule 1 duplicate stop. New computation and byte identity do not establish protocol uniqueness; no further experiments.'
              if after['status'] == 'DUPLICATE' else
              'Negative: novelty completeness, assigned lane, comparable-best and separate selector evidence are not established.')
    # Publication policy records a negative, not a new approved slot.
    policy_path = ROOT / 'registry/artifact_policy.json'
    policy = json.loads(policy_path.read_text())
    for p in (path, path.with_suffix('.zip')):
        policy['files'].append(dict(path=p.relative_to(ROOT).as_posix(), sha256=sha256_file(p),
            status='current_research_only', reason='S16 fresh computation; format PASS, literal registry duplicate; NOT OK TO SUBMIT.'))
    dump(policy_path, policy)
    return stop(card, reason, start)


if __name__ == '__main__':
    run()
