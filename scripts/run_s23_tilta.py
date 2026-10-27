#!/usr/bin/env python3
"""One preregistered TILTA experiment; reuse shared metric, emitter and writer.

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
from gems91.tilta23 import features
from gems91.novelty import SurfaceProbe, dot_check
from gems91.pdwc21 import emit_dots_nms
from vendor.gems57 import grid, spatial, evaluate_holdout as EH
from vendor.gems57.submission_writer import write_submission

OUT = ROOT / 'docs/s23'
WORK = ROOT / 'work/s23'
BUDGET = 20000  # use 20k to avoid dense-lattice impossibility

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
    for np_path in (OUT / 'nine-site-audit.json', ROOT / 'docs/s22/nine-site-audit.json'):
        if np_path.exists():
            for r in json.loads(np_path.read_text()).get('sites', []):
                if 'local_path' in r and 'sha256' in r:
                    rows.append(dict(path=r['local_path'], sha256=r['sha256'], bytes=r['bytes']))
            break
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
    return np.where(g.footprint, a, 0).astype(np.float32)

def run():
    # This historical experiment's advertised magnetic-tilt interpretation is
    # contradicted by a label-blind band audit, and its saved dots are a literal
    # registry duplicate. The archived source and receipts remain intact; do not
    # allow a deleted receipt or a budget change to trigger an implicit rerun.
    raise RuntimeError(
        'S23-TILTA is a frozen, duplicate-stopped historical experiment; '
        'band identity requires independent verification and a future run '
        'requires a newly assigned lane and full preflight. See '
        'docs/review-8e8d86f2/REVIEW.md.'
    )
    start = time.monotonic()
    OUT.mkdir(exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    if (OUT / 'run-card.json').exists():
        raise RuntimeError('Recorded experiment already exists; no implicit rerun or tuning')
    prereg_hash = sha(OUT / 'preregistration.md')
    manifest = json.loads((ROOT / 'registry/data_manifest.json').read_text())
    for row in manifest['files']:
        if row['id'] in {'sample_submission', 'existing_faults', 'training_features'}:
            p = ROOT / 'data' / row['local_subpath']
            if sha(p) != row['sha256'] or p.stat().st_size != row['bytes']:
                raise ValueError('Input identity mismatch: ' + row['id'])
    refs = freeze_references()
    g = grid.load_grid(ROOT / 'data/official')
    with rasterio.open(ROOT / 'data/bridge/gems-geodawn-numerical-features.tif') as ds:
        if ds.shape != g.shape or ds.crs != g.crs or ds.transform != g.transform:
            raise ValueError('feature grid mismatch')
        # Bands are 1-indexed: B06=tc, B18=iso_grav_anom_hg
        raw_tilt = ds.read(6)
        raw_grav_hg = ds.read(18)
    feat, meta = features(raw_tilt, raw_grav_hg, g.footprint)

    # --- leakage canary + holdout prep ---
    eligible = g.footprint  # footprint where we can evaluate
    # Build folds
    folds = list(spatial.folds(g.catalogue, eligible, buffer_px=80))
    # Canary: per-feature AUC
    canaries = []
    max_auc = 0
    worst = None
    for fname, arr in feat.items():
        # include surface and components but not raw inputs? test all
        for fidx, fold in enumerate(folds):
            # Build pooled truth mask
            truth = fold['truth']
            valid = eligible & fold['region'] & ~fold['visible']
            # Use all positives and every 4th negative per fold
            pos_idx = np.where(truth & valid)
            neg_idx = np.where(~truth & valid & eligible)
            # sample negatives 1/4
            neg_y, neg_x = neg_idx
            sel = np.arange(len(neg_y))[::4]
            neg_y, neg_x = neg_y[sel], neg_x[sel]
            y_true = np.concatenate([np.ones(len(pos_idx[0])), np.zeros(len(neg_y))])
            y_score = np.concatenate([arr[pos_idx], arr[neg_y, neg_x]])
            if len(np.unique(y_true)) < 2:
                auc = 0.5
            else:
                auc = roc_auc_score(y_true, y_score)
            sym = max(auc, 1-auc)
            canaries.append(dict(feature=fname, fold=fidx, auc=float(auc), sym_auc=float(sym)))
            if sym > max_auc:
                max_auc = sym
                worst = f"{fname} fold{fidx} auc={auc:.4f}"
            # also pooled handled separately? we just track max
    # Surface uniqueness pre-placement
    probe = SurfaceProbe(feat['surface'], g.footprint)
    surface_checks = []
    max_rho = 0
    max_rho_path = None
    for row in refs['files']:
        ref_arr = reference_array(row, g)
        res = probe.compare(ref_arr)
        rho = res['rank_correlation']
        if rho is None:
            continue
        surface_checks.append(dict(path=row['path'], rho=float(rho), status=res['status']))
        if abs(rho) > max_rho:
            max_rho = abs(rho)
            max_rho_path = row['path']
    # Also check against local downloads already (included via freeze)
    dump(OUT / 'surface-checks.json', dict(max_abs_rho=float(max_rho), closest=max_rho_path, checks=surface_checks))
    dump(OUT / 'canaries.json', dict(max_sym_auc=float(max_auc), worst=worst, canaries=canaries))
    dump(OUT / 'feature-receipt.json', meta)

    # Holdout evaluation: allocate budget per quadrant proportional to footprint area
    # Total budget 20k
    g_area = []
    for fold in folds:
        g_area.append(int((eligible & fold['region']).sum()))
    total_area = sum(g_area)
    results = []
    terms_all = []
    for fidx, fold in enumerate(folds):
        budget_q = int(round(BUDGET * g_area[fidx] / total_area))
        # ensure at least budget_q sum = BUDGET (adjust last)
        if fidx == len(folds)-1:
            budget_q = BUDGET - sum(int(round(BUDGET * g_area[i] / total_area)) for i in range(len(folds)-1))
        visible = fold['visible']
        pred_q = emit_dots_nms(feat['surface'], visible, eligible, budget=budget_q, collar_px=3.05, min_spacing_px=3.05)
        # Evaluate on this fold's truth within region, masking visible faults
        # Use EH.evaluate which handles active = valid & region & ~known
        valid = eligible
        # EH expects fold dict with region, visible as masked_known, truth
        # fold already has region, truth, visible, etc.
        res, terms = EH.evaluate(pred_q, fold, valid, block_side=200, origin=(0,0), global_shape=g.shape)
        results.append(dict(fold=fidx, budget=budget_q, dti=res['dti'] if 'dti' in res else res.get('dti', 0), tpw=res['tpw'], fpw=res['fpw'], fnw=res['fnw'], n_truth=res['n_truth'], n_emitted=res['n_emitted'], terms=terms.tolist() if hasattr(terms, 'tolist') else terms))
        terms_all.append(terms)
    # Pooled DTI from terms sum
    total_terms = np.sum(np.stack(terms_all), axis=0)
    totals = total_terms.sum(axis=0)
    tp, fp, fn, n_truth = totals
    pooled_dti = tp / (tp + 0.2*fp + 0.8*fn + 1e-12) if (tp+fp+fn) >0 else 0
    # Bootstrap CI via block bootstrap on terms (reuse EH logic via simple percentile)
    # We'll implement simple paired bootstrap over spatial blocks (clusters)
    clusters = len(total_terms)
    draws = 1000
    rng = np.random.default_rng(520810)
    boot = []
    for _ in range(draws):
        idx = rng.integers(0, clusters, size=clusters)
        t = total_terms[idx].sum(axis=0)
        tp_b, fp_b, fn_b = t[0], t[1], t[2]
        boot.append(tp_b / (tp_b + 0.2*fp_b + 0.8*fn_b + 1e-12))
    boot = np.array(boot)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    holdout = dict(
        evidence_class="HOLDOUT-DTI",
        evaluator_version=EH.VERSION,
        alpha=0.2, beta=0.8, triangular_radius_m=300.0, pooled=True,
        scores=dict(tilta_e1=dict(evidence_class="HOLDOUT-DTI", evaluator_version=EH.VERSION, dti=float(pooled_dti), ci95=[float(lo), float(hi)], withheld_positive_pixels=int(totals[3]), tpw=float(tp), fpw=float(fp), fnw=float(fn))),
        best_comparable_control=None,
        paired_differences={},
        bootstrap=dict(method="paired physical spatial-cluster percentile", clusters=int(clusters), draws=draws, seed=520810, confidence=0.95, caveat="Conditional on fitted folds, catalogue labels and fixed budgets; not a leaderboard interval."),
        implementation_sha256=EH.implementation_hashes(),
        per_fold=results,
    )
    dump(OUT / 'holdout.json', holdout)

    # Final full-grid emission for submission (mask full catalogue)
    final_support = emit_dots_nms(feat['surface'], g.catalogue, g.footprint, budget=BUDGET, collar_px=3.05, min_spacing_px=3.05)
    # Write submission
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    # short hash for name
    support_bytes = final_support.tobytes()
    short = hashlib.sha256(support_bytes).hexdigest()[:8]
    name = f"gems91-s23-tilta-e1-{stamp[:-1].lower() if False else ''}"
    # Use naming convention: gems91-s23-tilta-e1-<timestamp>-<short>-zeros
    # We'll generate via write_submission then rename
    out_tif = ROOT / f"docs/downloads/gems91-s23-tilta-e1-{stamp.lower()}-{short}-zeros.tif"
    # write via submission_writer (validates [0,1], CRS, footprint, catalogue)
    from vendor.gems57.grid import TRANSFORM, EPSG, HEIGHT, WIDTH
    # Use write_submission API: path, prediction, sample, footprint, note, name
    submission_name_base = f"gems91-s23-tilta-e1-{stamp}-{short}-zeros"
    # Temporarily write to final path via writer (it expects not exists)
    # Ensure output dir exists and no prior file
    if out_tif.exists():
        out_tif.unlink()
    if out_tif.with_suffix('.zip').exists():
        out_tif.with_suffix('.zip').unlink()
    if out_tif.with_suffix('.json').exists():
        out_tif.with_suffix('.json').unlink()
    result = write_submission(
        out_tif,
        final_support.astype(np.float32),
        ROOT / 'data/official/sample_submission.tif',
        g.footprint,
        note="S23 TILTA tilt x grav-HG concordance 20k dots 3.05px collar; research only",
        name=submission_name_base,
        catalogue=g.catalogue,
    )
    out_zip = out_tif.with_suffix('.zip')
    tif_sha = sha(out_tif)
    zip_sha = sha(out_zip)
    # Validate via rasterio
    with rasterio.open(out_tif) as ds:
        a = ds.read(1)
        assert ds.crs == g.crs or str(ds.crs) == f"EPSG:{EPSG}"
        assert ds.shape == (HEIGHT, WIDTH)
        assert ds.count == 1 and ds.dtypes[0] == 'float32'
        assert ds.nodata is None
        assert np.isfinite(a).all()
        assert a.min() >=0 and a.max() <=1
        assert (a[g.catalogue] == 0).all(), "dots on catalogue"
        n_dots = int((a>0).sum())
        assert n_dots == BUDGET, f"dot count {n_dots} != {BUDGET}"
        # footprint check
        footprint_finite = np.isfinite(a[g.footprint]).all()
        outside_zero = (a[~g.footprint] == 0).all()
    # Final dot uniqueness check
    # Compute dot positions
    ys, xs = np.where(final_support > 0)
    # Use dot_check utility
    final_checks = []
    max_overlap = 0
    max_overlap_path = None
    for row in refs['files']:
        with rasterio.open(ROOT / row['path']) as ds:
            ref = ds.read(1) > 0
        # directed overlap: fraction of our dots within 3px of reference
        # Use distance transform of reference
        from scipy.ndimage import distance_transform_edt
        # reference support
        ref_support = ref
        # fast check: use KDTree or distance_transform
        # Invert: distance to nearest reference dot
        dist = distance_transform_edt(~ref_support)
        within = (dist[ys, xs] <= 3.0).mean() if len(ys)>0 else 0
        final_checks.append(dict(path=row['path'], overlap=float(within)))
        if within > max_overlap:
            max_overlap = within
            max_overlap_path = row['path']
    dump(OUT / 'final-dot-checks.json', dict(max_3px_overlap=float(max_overlap), closest=max_overlap_path, checks=final_checks))

    # Writer receipt
    writer_receipt = dict(file=str(out_tif.relative_to(ROOT)), sha256=tif_sha, bytes=out_tif.stat().st_size, zip=str(out_zip.relative_to(ROOT)), zip_sha256=zip_sha, n_dots=int(BUDGET), validation=dict(crs=str(g.crs), shape=[HEIGHT, WIDTH], dtype="float32", nodata=None, n_finite=int(np.isfinite(a).sum()), min=float(a.min()), max=float(a.max()), on_catalogue=int((a[g.catalogue]>0).sum())))
    dump(OUT / 'writer-receipt.json', writer_receipt)

    run_card = dict(
        schema_version="gems-s23-run-card-v1",
        lane="S23-TILTA",
        hypothesis="Faults juxtapose magnetic basement blocks: tilt-angle derivative edge (B06) aligned with gravity HG ridge (B18) marks concealed magnetic-density contacts.",
        mechanism="Tilt-angle gradient magnitude (σ=2 px) × gravity HG magnitude (σ=2 px) × squared cosine alignment between their normals, normalized per-footprint 95th percentile; cbrt product. No catalogue features; 20,000 spaced dots, 3.05 px collar.",
        named_non_fault_mimic="Unfaulted intrusive contacts, lava-flow margins, survey seam edges, and topographic flexure — all produce isolated magnetic or gravity edges but rarely co-located aligned pair.",
        verdict="negative" if pooled_dti < 0.066223 else "promote",
        ok_to_submit=False,
        organizer_confirmed_score=None,
        leaderboard_score_estimate=None,
        submission_slots_used=0,
        preregistration_sha256=prereg_hash,
        experiments_run=1,
        budget_max_experiments=3,
        registry_scope=dict(available_unique_bytes=len(refs['files']), missing=len(refs['missing']), organizer_complete=False, dense_exemptions=False),
        holdout=dict(evidence_class="HOLDOUT-DTI", evaluator_version=EH.VERSION, dti=float(pooled_dti), ci95=[float(lo), float(hi)], withheld_positive_pixels=int(totals[3]), tpw=float(tp), fpw=float(fp), fnw=float(fn)),
        leakage_canary=dict(max_symmetric_auc=float(max_auc), worst=worst, canaries=canaries),
        surface_checks=dict(max_abs_rho=float(max_rho), closest=max_rho_path),
        final_dot_checks=dict(max_3px_overlap=float(max_overlap), closest=max_overlap_path),
        raster_sha256=tif_sha,
        validator_output=writer_receipt['validation'],
        submission_name=out_tif.stem,
        submission_note="S23 TILTA tilt x grav-HG concordance 20k dots 3.05px collar; research only",
        artifact=dict(tif=str(out_tif.relative_to(ROOT)), zip=str(out_zip.relative_to(ROOT)), zip_sha256=zip_sha, support_sha256=short),
        elapsed_seconds=float(time.monotonic()-start),
    )
    dump(OUT / 'run-card.json', run_card)
    dump(ROOT / 'docs/run-card-S23-TILTA.json', run_card)
    print(json.dumps(run_card, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(run())
