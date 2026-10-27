#!/usr/bin/env python3
"""One preregistered OMTJ experiment; reuse shared metric, emitter and writer.

Duplicate => stop, never reinterpret a dense reference or tune around it.
Data restoration is separate and hash checked before any feature computation.
"""
from __future__ import annotations
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
os.environ.setdefault('OMP_NUM_THREADS', '2')
import hashlib
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
import numpy as np
import rasterio
from sklearn.metrics import roc_auc_score
from gems91.omtj22 import features
from gems91.novelty import SurfaceProbe, check_final_pair
from gems91.pdwc21 import emit_dots_nms
from vendor.gems57 import grid, spatial, evaluate_holdout as EH
from vendor.gems57.submission_writer import write_submission
from scripts.experiment_preflight import evaluate as evaluate_preflight

OUT = ROOT / 'docs/s22'
WORK = ROOT / 'work/s22'
BUDGET = 37654


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def dump(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def freeze_references():
    rows = json.loads((ROOT / 'registry/comparison_inventory.json').read_text())['files']
    rows = [dict(r) for r in rows]
    for p in sorted((ROOT / 'docs/downloads').glob('*.tif')):
        rows.append(dict(path=str(p.relative_to(ROOT)), sha256=sha(p), bytes=p.stat().st_size))
    # Include the exact nine-site pinned artifacts, not similarly named ancestors.
    for r in json.loads((OUT / 'nine-site-audit.json').read_text())['sites']:
        rows.append(dict(path=r['local_path'], sha256=r['sha256'], bytes=r['bytes']))
    present, missing, seen = [], [], set()
    for r in rows:
        p = ROOT / r['path']
        if not p.is_file():
            missing.append(r); continue
        if sha(p) != r['sha256'] or p.stat().st_size != r['bytes']:
            raise ValueError(f'Registry bytes drift: {p}')
        if r['sha256'] in seen:
            continue
        seen.add(r['sha256']); present.append(r)
    result = dict(files=present, missing=missing, organizer_complete_registry=False,
                  dense_reference_exemptions=False)
    dump(OUT / 'frozen-registry.json', result)
    return result


def reference_array(row, g):
    with rasterio.open(ROOT / row['path']) as ds:
        if ds.shape != g.shape or ds.crs != g.crs or ds.transform != g.transform or ds.count != 1:
            raise ValueError('registry grid mismatch: ' + row['path'])
        a = ds.read(1)
    if not np.isfinite(a[g.footprint]).all() or (a[g.footprint] < 0).any() or (a[g.footprint] > 1).any():
        raise ValueError('invalid registry values inside footprint: ' + row['path'])
    # Outside-footprint encodings are not predictions. Do not alter valid pixels.
    return np.where(g.footprint, a, 0).astype(np.float32)


def run():
    start = time.monotonic()
    if (OUT / 'run-card.json').exists():
        raise RuntimeError('Recorded experiment already exists; no implicit rerun or tuning')
    plan = json.loads((ROOT / 'registry/experiment_plan.json').read_text())
    if plan.get('dot_budget') != BUDGET:
        raise RuntimeError('The frozen runner budget differs from its preflight; do not tune around a registry witness')
    preflight = evaluate_preflight(ROOT, plan)
    if preflight['status'] != 'NOT_RULED_OUT' or not preflight['assignment_authenticated']:
        raise RuntimeError('Experiment preflight blocked or method assignment not authenticated; no experiment launched')
    OUT.mkdir(parents=True, exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    prereg_hash = sha(OUT / 'preregistration.md')
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    for row in manifest['files']:
        if row['id'] in {'sample_submission', 'existing_faults', 'training_features'}:
            p = ROOT / 'data' / row['local_subpath']
            if sha(p) != row['sha256'] or p.stat().st_size != row['bytes']:
                raise ValueError('Input identity mismatch: ' + row['id'])
    refs = freeze_references()
    if refs['missing']:
        raise RuntimeError('Frozen registry references missing; refuse to place or evaluate any candidate')
    g = grid.load_grid(ROOT / 'data/official')
    with rasterio.open(ROOT / 'data/bridge/gems-geodawn-numerical-features.tif') as ds:
        if ds.shape != g.shape or ds.crs != g.crs or ds.transform != g.transform:
            raise ValueError('feature grid mismatch')
        raw_m, raw_g = ds.read(14), ds.read(13)
    feat, meta = features(raw_m, raw_g, g.footprint)
    del raw_m, raw_g
    surface = feat['surface']
    np.save(WORK / 'surface.npy', surface)
    dump(OUT / 'feature-receipt.json', dict(**meta, surface_array_sha256=sha(WORK / 'surface.npy'),
                                         preregistration_sha256=prereg_hash))
    print('Features built; catalogue never supplied to feature function', flush=True)
    card = dict(schema_version='gems-s22-run-card-v1', lane='S22-OMTJ',
        hypothesis='Concealed displacement juxtaposes magnetic texture with different signed third moments.',
        mechanism='B14 local skewness boundary aligned with the smoothed B13 gravity gradient.',
        named_non_fault_mimic='Unfaulted volcanic flow margin or intrusive lithologic contact',
        verdict='negative', ok_to_submit=False, organizer_confirmed_score=None,
        leaderboard_score_estimate=None, submission_slots_used=0,
        preregistration_sha256=prereg_hash, experiments_run=1, budget_max_experiments=3,
        registry_scope=dict(available_unique_bytes=len(refs['files']), missing=len(refs['missing']),
                            organizer_complete=False, dense_exemptions=False),
        holdout=None, raster_sha256=None, validator_output=None,
        submission_name=None, submission_note=None, artifact=None)

    def finish(reason):
        card['stop_reason'] = reason
        card['elapsed_seconds'] = round(time.monotonic() - start, 2)
        card['within_two_hour_budget'] = card['elapsed_seconds'] <= 7200
        card['generated_utc'] = datetime.now(timezone.utc).isoformat()
        dump(OUT / 'run-card.json', card)
        print(json.dumps(card, indent=2), flush=True)
        return card

    # No full catalogue collar is used here. These whole-component folds are the
    # same shared label-blind spatial instrument used by prior comparable runs.
    terms = None
    fold_results, canaries, folds = [], [], []
    for f in spatial.folds(g.catalogue, g.footprint, buffer_px=80):
        active = f['region'] & g.footprint & ~f['visible']
        flat = np.flatnonzero(active)
        truth = f['truth'].ravel()[flat]
        keep = truth | (np.arange(len(flat)) % 4 == 0)
        idx, y = flat[keep], truth[keep]
        for name, a in feat.items():
            auc = float(roc_auc_score(y, a.ravel()[idx]))
            canaries.append(dict(feature=name, fold=int(f['fold']), auc=auc,
                symmetric_auc=max(auc, 1 - auc), positives=int(y.sum()), negatives=int((~y).sum())))
        folds.append(f)
    dump(OUT / 'canaries.json', canaries)
    worst = max(r['symmetric_auc'] for r in canaries)
    card['leakage_canary'] = dict(max_symmetric_auc=worst, threshold=.90, passed=worst <= .90,
                                  tests=len(canaries), feature_count=len(feat))
    if worst > .90:
        return finish('LEAKAGE_CANARY_STOP')
    del feat
    print('Canaries passed; testing surface before any placement', flush=True)
    probe = SurfaceProbe(surface, g.footprint)
    surface_rows, errors = [], []
    for r in refs['files']:
        try:
            result = probe.compare(reference_array(r, g))
        except ValueError as exc:
            errors.append(dict(path=r['path'], reason=str(exc))); continue
        surface_rows.append(dict(path=r['path'], **result))
        if result['status'] == 'DUPLICATE':
            dump(OUT / 'surface-checks.json', dict(rows=surface_rows, errors=errors))
            card['correlation_overlap_vs_registry'] = dict(surface_duplicate=surface_rows[-1])
            return finish('SURFACE_DUPLICATE_STOP')
    dump(OUT / 'surface-checks.json', dict(rows=surface_rows, errors=errors))
    if not surface_rows or errors or len(surface_rows) != len(refs['files']) or any(r['status'] != 'PASS' for r in surface_rows):
        card['correlation_overlap_vs_registry'] = dict(
            surface_checked=len(surface_rows), surface_unverified=errors, final_dot_checks=None)
        return finish('SURFACE_UNVERIFIED_STOP — no placement or holdout evaluation')
    card['correlation_overlap_vs_registry'] = dict(
        surface_max_rank_correlation=max(abs(r['rank_correlation']) for r in surface_rows),
        surface_checked=len(surface_rows), surface_unverified=[],
        final_dot_checks=None)
    del probe
    for f in folds:
        if time.monotonic() - start > 6900:
            return finish('BUDGET_STOP')
        n = round(BUDGET * int(f['region'].sum()) / int(g.footprint.sum()))
        # Whole-grid visible context first; region restriction only after collar.
        # Preserve fixed domain and exact total allocation without test-domain
        # spillover: emit independently within the quadrant with global collar.
        from scipy.ndimage import distance_transform_edt
        allowed = f['region'] & (distance_transform_edt(~f['visible']) > 3.05)
        pred = emit_dots_nms(surface, np.zeros_like(allowed), allowed, budget=n,
                            collar_px=0, min_spacing_px=3.05)
        result, t = EH.evaluate(pred, f, g.footprint)
        terms = t if terms is None else terms + t
        fold_results.append(dict(**result, fold=int(f['fold']), budget=n, split=f['receipt']))
        print('Evaluated fold', f['fold'], result['dti'], flush=True)
    holdout = EH.pooled_summary({'omtj_e1': terms}, candidate='omtj_e1')
    holdout['per_fold'] = fold_results
    holdout['allocation'] = 'Fixed quadrant area share; no spillover. No paired incumbent available.'
    dump(OUT / 'holdout.json', holdout)
    card['holdout'] = holdout['scores']['omtj_e1']
    del folds, terms
    pred = emit_dots_nms(surface, g.catalogue, g.footprint, budget=BUDGET,
                         collar_px=3.05, min_spacing_px=3.05)
    support_hash = hashlib.sha256(np.packbits(pred > 0).tobytes()).hexdigest()
    name = f'gems91-s22-omtj-e1-20261026-{support_hash[:10]}-zeros'
    note = 'S22 OMTJ E1: magnetic third-moment boundary x gravity normal; research only; not approved for submission.'
    tif = ROOT / 'docs/downloads' / (name + '.tif')
    receipt = write_submission(tif, pred, ROOT / 'data/official/sample_submission.tif', g.footprint,
        note=note, name=name, catalogue=g.catalogue,
        metadata=dict(lane='S22-OMTJ', preregistration_sha256=prereg_hash, research_only=True))
    dump(OUT / 'writer-receipt.json', receipt)
    card.update(raster_sha256=receipt['sha256'], validator_output=receipt['validator'],
        submission_name=name, submission_note=note,
        artifact=dict(tif=str(tif.relative_to(ROOT)), zip=str(tif.with_suffix('.zip').relative_to(ROOT)),
                      zip_sha256=receipt['zip_sha256'], support_sha256=support_hash),
        exact_file_hash_unseen_in_frozen_registry=receipt['sha256'] not in {r['sha256'] for r in refs['files']},
        ok_to_download=True, download_scope='Negative research artifact; not a protocol-unique competition submission')
    # Persist the valid research artifact in the explicit public prediction policy.
    policy_path = ROOT / 'registry/artifact_policy.json'
    policy = json.loads(policy_path.read_text())
    for p, digest in [(tif, receipt['sha256']), (tif.with_suffix('.zip'), receipt['zip_sha256'])]:
        policy['files'].append(dict(path=str(p.relative_to(ROOT)), sha256=digest,
            status='current_research_only', reason='S22 OMTJ negative experiment; no submission authorization.'))
    dump(policy_path, policy)
    final_rows = []
    probe = SurfaceProbe(pred, g.footprint)
    for r in refs['files']:
        try:
            a = reference_array(r, g)
            rank_result, dots_result, verdict = check_final_pair(probe, pred, a, g.footprint)
            result = {**rank_result, **dots_result,
                      'rank_status': rank_result['status'], 'dot_status': dots_result['status'],
                      'rank_reason': rank_result.get('reason'), 'dot_reason': dots_result.get('reason'),
                      'status': verdict}
            duplicate = result['status'] == 'DUPLICATE'
        except ValueError as exc:
            final_rows.append(dict(path=r['path'], status='UNVERIFIED', reason=str(exc))); continue
        final_rows.append(dict(path=r['path'], **result))
        if duplicate:
            dump(OUT / 'final-dot-checks.json', final_rows)
            card['correlation_overlap_vs_registry']['final_dot_checks'] = dict(
                checked_before_stop=len(final_rows), duplicate=final_rows[-1], registry_clearance=False)
            return finish('FINAL_DOTS_DUPLICATE_STOP — no dense-raster exception; no more experiments')
    dump(OUT / 'final-dot-checks.json', final_rows)
    card['correlation_overlap_vs_registry']['final_dot_checks'] = dict(checked=len(final_rows), registry_clearance=False)
    return finish('NOT_PROMOTED — missing registry references and no paired incumbent / selector receipt')


if __name__ == '__main__':
    run()
