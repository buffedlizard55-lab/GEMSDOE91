#!/usr/bin/env python3
"""SSHAC lane driver — seismo-strain hydrothermal alteration corridor.

Preregistration: docs/HYPOTHESES_SSHAC.md (frozen 2026-10-24 before any SSHAC number).

Instrument: evaluate_holdout.build_segment_buffered_folds (bridge 3, buffer 10),
4 quadrants, pooled DTI alpha 0.2 beta 0.8 R 3px, block-bootstrap 5km CI.

Budget: exactly 3 experiments (E1, E2, E3) on identical folds.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import dti as D  # noqa: E402
import evaluate_holdout as EH  # noqa: E402
from gems91 import ss_hac as SSH  # noqa: E402
from gems91 import io as GIO  # noqa: E402
from gems91 import denovo as DN  # reuse disk_offsets, greedy_spaced

FEATS = ROOT / "data/bridge/gems-geodawn-numerical-features.tif"
SAMPLE = ROOT / "data/official/sample_submission.tif"
CAT = ROOT / "data/official/existing_faults.tif"
DATE = "20261024"
SEED = 20261024
N_DOTS = 37654
SPACING = 2.8

# reuse HGB hyperparams from build_denovo
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

HGB_PARAMS = dict(
    max_iter=300,
    learning_rate=0.06,
    max_leaf_nodes=63,
    min_samples_leaf=40,
    l2_regularization=1.0,
    early_stopping=False,
    random_state=SEED,
)


def read1(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        return s.read(1)


def footprint_arr() -> np.ndarray:
    return np.isfinite(read1(SAMPLE))


def load_bands(fp: np.ndarray):
    # read all 19 bands needed for SSH
    need = sorted(set(SSH.BANDS.values()))
    inv = {v: k for k, v in SSH.BANDS.items()}
    bands: dict[str, np.ndarray] = {}
    with rasterio.open(FEATS) as src:
        for b in need:
            bands[inv[b]] = src.read(b)
    return bands


def fold_setup_cat():
    cat = (np.nan_to_num(read1(CAT), nan=0.0) > 0) & footprint_arr()
    fp = footprint_arr()
    folds = EH.build_segment_buffered_folds(cat, fp, bridge_px=3, buffer_px=10.0)
    return cat, fp, folds


def train_hgb(X_train: np.ndarray, y_train: np.ndarray) -> HistGradientBoostingClassifier:
    clf = HistGradientBoostingClassifier(**HGB_PARAMS)
    clf.fit(X_train, y_train)
    return clf


def prepare_training_data_for_fold(
    fold: EH.HoldoutFold,
    X_fp: np.ndarray,
    fp_idx: np.ndarray,
    cat: np.ndarray,
    fp: np.ndarray,
):
    # Visible faults are training positives (masked exactly, no buffer bleed)
    # Negatives sampled >5px from visible faults, 3x positives, seed per fold
    # Using same logic as build_denovo but with segment-buffered folds.
    # For each fold, training domain = footprint excluding buffer & withheld & visible? Actually positives are visible_faults
    # Negatives drawn from footprint where dist to visible >5px.
    n_pos = int(fold.visible_faults.sum())
    if n_pos == 0:
        raise RuntimeError(f"fold {fold.name} has 0 visible positives")
    dist_to_visible = ndi.distance_transform_edt(~fold.visible_faults)
    neg_mask = fp & (~fold.visible_faults) & (~fold.buffer_mask) & (~fold.withheld_faults) & (dist_to_visible > 5.0)
    # Exclude training outside domain? Keep disjoint but for HGB training we use global neg sampling as in denovo: whole footprint negatives >5px off visible.
    # To avoid leakage across folds' withheld regions, ensure negatives not inside withheld or buffer (already)
    neg_pool = np.flatnonzero(neg_mask)
    pos_idx = np.flatnonzero(fold.visible_faults)
    # Need to map to fp indices for y
    # Build y for training: we need X rows for pos + neg sampled
    rng = np.random.default_rng(SEED + fold.fold_id * 11 + 7)
    n_neg = min(len(neg_pool), n_pos * 3)
    # Sample negatives
    neg_sample = rng.choice(neg_pool, size=n_neg, replace=False)
    train_pixels = np.concatenate([pos_idx, neg_sample])
    # Map to fp row indices
    # fp_idx is 2D array of fp linear index -> row in X_fp
    fp_linear = np.ravel_multi_index(np.nonzero(fp), fp.shape)  # not needed
    # Instead build mapping from pixel flat index to fp row
    # Use fp_idx 2D: contains row id for each (y,x) in fp, -1 otherwise
    train_rows = fp_idx.flat[train_pixels]  # flat index = y*W + x
    # Need to convert 2D flat? Simpler: create flat fp_idx
    # Actually fp_idx is 2D; we can use unravel
    # Let's recompute: we need mapping from flat pixel idx (y*W+x) to X row
    # We'll create dict via fp positions
    y_train = np.zeros(len(train_pixels), dtype=np.int8)
    y_train[: len(pos_idx)] = 1
    X_train = X_fp[train_rows]
    return X_train, y_train, len(pos_idx), len(neg_sample)


def score_surface_on_folds(
    folds: list[EH.HoldoutFold],
    cat: np.ndarray,
    fp: np.ndarray,
    X_fp: np.ndarray,
    models: dict[int, HistGradientBoostingClassifier],
    feature_transform=None,
):
    # Predict per-fold surface then score via EH.score_pooled_holdout
    # feature_transform is optional smoothing of surface before scoring (for E2)
    # Build per-fold predictions dict
    fp_idx_map = np.full(fp.shape, -1, dtype=np.int32)
    fp_idx_map[fp] = np.arange(int(fp.sum()), dtype=np.int32)
    # For each fold, predict over whole footprint then mask to domain
    fold_preds: dict[int, np.ndarray] = {}
    for f in folds:
        clf = models[f.fold_id]
        proba = clf.predict_proba(X_fp)[:, 1].astype(np.float32)  # over fp
        surface = np.zeros(fp.shape, dtype=np.float32)
        surface[fp] = proba
        if feature_transform is not None:
            surface = feature_transform(surface, fp)
        # Eligible mask for scoring is handled inside EH.score_pooled_holdout via active_domain
        # But we must zero visible faults & buffer inside prediction before scoring (protocol)
        # EH does masking internally, but we also need to ensure emission respects >3px from visible catalogue
        # For scoring, we score the continuous surface (not dots) — protocol says mask visible faults pixel-exactly
        # So we zero those in surface before scoring? EH.score_pooled_holdout masks active_domain which excludes visible+buffer, so zeroing is implicit.
        # We will zero explicitly to be safe.
        surface[f.visible_faults | f.buffer_mask] = 0.0
        surface[~fp] = 0.0
        fold_preds[f.fold_id] = surface
    result = EH.score_pooled_holdout(fold_preds, folds, fp)
    return result, fold_preds


def canary_report(X_fp, feature_names, folds, fp):
    # Use shared leakage canary
    return EH.run_leakage_canary(X_fp, feature_names, folds, fp, fold_specific_features=None)


def emission_from_surface(surface: np.ndarray, fp: np.ndarray, cat: np.ndarray, n_dots: int, spacing: float, mask: np.ndarray | None = None):
    # Greedy spaced dots; mask = eligible (fp & dcat>3)
    if mask is None:
        dcat = ndi.distance_transform_edt(~cat)
        mask = fp & (dcat > 3.0)
    else:
        mask = mask & fp
    dots = DN.greedy_spaced(surface, mask, n_dots, spacing_px=spacing)
    assert int(dots.sum()) == n_dots or int(dots.sum()) < n_dots and mask.sum() < n_dots * 2, f"dots {dots.sum()} != {n_dots}"
    # fallback: if not enough dots due to spacing, reduce spacing slightly or assert
    if int(dots.sum()) != n_dots:
        # Try to widen pool (greedy_spaced already does fallback)
        pass
    return dots


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["canary", "holdout", "build"], default="holdout")
    ap.add_argument("--spacing", type=float, default=SPACING)
    ap.add_argument("--n-dots", type=int, default=N_DOTS)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    fp = footprint_arr()
    cat_full = (np.nan_to_num(read1(CAT), nan=0.0) > 0) & fp
    cat, fp2, folds = fold_setup_cat()
    assert np.array_equal(fp, fp2)
    print(f"folds: {[f.name+':'+str(f.n_withheld) for f in folds]} total {sum(f.n_withheld for f in folds)}")
    bands = load_bands(fp)
    X_fp, feat_names, audit = SSH.build_features(bands, fp)
    print(f"features: {X_fp.shape[1]} {feat_names[:3]}...")
    print(f"audit: {audit['n_features']} features, n_fp {audit['n_footprint']}")

    if args.mode == "canary":
        rep = canary_report(X_fp, feat_names, folds, fp)
        print(json.dumps(rep, indent=2))
        Path("evidence/sshac_canary.json").write_text(json.dumps(rep, indent=2))
        return

    # Train per-fold HGB
    # Prepare mappings
    fp_idx_2d = np.full(fp.shape, -1, dtype=np.int32)
    fp_idx_2d[fp] = np.arange(int(fp.sum()), dtype=np.int32)
    # For training we need flat pixel indices mapping; create flat array
    # Use 1D flat index: pixel_flat = y*W + x
    h, w = fp.shape
    # Build array from flat pixel index to X row: we have fp_idx_2d, so flat->row via unravel
    # Simpler: in prepare_training, we will use pos_idx flat pixels and lookup via 2D index
    # Let's make helper to get row from (y,x)
    models: dict[int, HistGradientBoostingClassifier] = {}
    for f in folds:
        # Build X_train, y_train for this fold
        # Re-implement sampling using 2D index lookup
        n_pos = int(f.visible_faults.sum())
        dist_to_visible = ndi.distance_transform_edt(~f.visible_faults)
        neg_mask = fp & (~f.visible_faults) & (~f.buffer_mask) & (~f.withheld_faults) & (dist_to_visible > 5.0)
        pos_ys, pos_xs = np.nonzero(f.visible_faults)
        pos_rows = fp_idx_2d[pos_ys, pos_xs]
        neg_ys, neg_xs = np.nonzero(neg_mask)
        neg_flat_idx = np.arange(len(neg_ys))
        rng = np.random.default_rng(SEED + f.fold_id * 11 + 7)
        n_neg = min(len(neg_ys), n_pos * 3)
        sel = rng.choice(len(neg_ys), size=n_neg, replace=False)
        neg_rows = fp_idx_2d[neg_ys[sel], neg_xs[sel]]
        train_rows = np.concatenate([pos_rows, neg_rows])
        y_train = np.concatenate([np.ones(len(pos_rows), dtype=np.int8), np.zeros(len(neg_rows), dtype=np.int8)])
        X_train = X_fp[train_rows]
        print(f"fold {f.name} train pos {len(pos_rows)} neg {len(neg_rows)} X_train {X_train.shape}")
        clf = train_hgb(X_train, y_train)
        models[f.fold_id] = clf

    # E1 scoring
    from gems91.fuse91 import scatter_smooth, tiered_greedy_spaced  # reuse

    print("=== E1 sharp ===")
    res_e1, preds_e1 = score_surface_on_folds(folds, cat_full, fp, X_fp, models, feature_transform=None)
    print(f"E1 pooled DTI {res_e1['holdout_dti']} CI {res_e1['ci_95']} T {res_e1['pooled_T']} S {res_e1['pooled_S']}")

    # E2 scatter
    def smooth_transform(surf, fp_mask):
        return scatter_smooth(surf, fp_mask, sigma=1.85)

    print("=== E2 scatter sigma1.85 ===")
    res_e2, preds_e2 = score_surface_on_folds(folds, cat_full, fp, X_fp, models, feature_transform=smooth_transform)
    print(f"E2 pooled DTI {res_e2['holdout_dti']} CI {res_e2['ci_95']}")

    # E3: winner + ring — need to evaluate emission-level difference, not just surface smoothing.
    # For holdout evaluation of ring, we need to generate dots per fold and score dots, not continuous surface.
    # We'll score dots via EH.score_pooled_holdout as well (since it accepts any prediction grid, binary dots work)
    # Determine winner surface for E3 base
    winner = "e1" if res_e1["holdout_dti"] >= res_e2["holdout_dti"] else "e2"
    print(f"winner surface for E3: {winner}")
    preds_winner = preds_e1 if winner == "e1" else preds_e2
    # Generate per-fold dots with tiered emission (2-3px ring cap 6%)
    dots_per_fold = {}
    for f in folds:
        surf = preds_winner[f.fold_id]
        dcat_visible = ndi.distance_transform_edt(~f.visible_faults) if f.visible_faults.any() else np.full(fp.shape, 1e6)
        # Final build will use dcat_full>3, but holdout must use visible catalogue distance
        # Tier mask: 2 < d <=3
        tier_mask = fp & (dcat_visible > 2.0) & (dcat_visible <= 3.0)
        main_mask = fp & (dcat_visible > 3.0)
        # Cap 6% per fold budget proportional to footprint share
        fold_budget = int(round(N_DOTS * (f.region_mask.sum() / fp.sum())))
        # Ensure sum across folds = N_DOTS (adjust last)
        # For pooled scoring, per-fold budget split by region share is standard; we will compute exact later for final build.
        # For holdout dots scoring, we use per-fold budget as above and let EH pool.
        # Use tier cap
        cap = int(round(fold_budget * 0.06))
        dots = tiered_greedy_spaced(surf, tier_mask, main_mask, fold_budget, tier_cap=cap, spacing_px=SPACING)
        dots_per_fold[f.fold_id] = dots.astype(np.float32)
        print(f"fold {f.name} dots {int(dots.sum())} cap {cap} budget {fold_budget} tier {int((dots & tier_mask).sum())}")
    res_e3 = EH.score_pooled_holdout(dots_per_fold, folds, fp)
    print(f"E3 pooled DTI {res_e3['holdout_dti']} CI {res_e3['ci_95']}")

    # Canary
    canary = canary_report(X_fp, feat_names, folds, fp)
    print(f"canary worst {canary['worst_feature']} {canary['worst_symmetric_auc']} all_pass {canary['all_pass']}")

    # Emit final build surface (train on full catalogue)
    if args.mode == "build":
        # Train final model on full catalogue (visible = full catalogue, no withheld)
        # For final build, we train on full catalogue positives vs negatives >5px off full catalogue
        dist_to_full = ndi.distance_transform_edt(~cat_full)
        pos_ys, pos_xs = np.nonzero(cat_full)
        pos_rows_full = fp_idx_2d[pos_ys, pos_xs]
        neg_mask_full = fp & (~cat_full) & (dist_to_full > 5.0)
        neg_ys, neg_xs = np.nonzero(neg_mask_full)
        rng = np.random.default_rng(SEED + 99)
        n_neg_full = min(len(neg_ys), len(pos_ys) * 3)
        sel = rng.choice(len(neg_ys), size=n_neg_full, replace=False)
        neg_rows_full = fp_idx_2d[neg_ys[sel], neg_xs[sel]]
        X_train_full = X_fp[np.concatenate([pos_rows_full, neg_rows_full])]
        y_train_full = np.concatenate([np.ones(len(pos_rows_full), dtype=np.int8), np.zeros(len(neg_rows_full), dtype=np.int8)])
        print(f"final train pos {len(pos_rows_full)} neg {len(neg_rows_full)}")
        clf_full = train_hgb(X_train_full, y_train_full)
        proba_full = clf_full.predict_proba(X_fp)[:, 1].astype(np.float32)
        surface_full = np.zeros(fp.shape, dtype=np.float32)
        surface_full[fp] = proba_full
        surface_full[~fp] = 0.0
        surface_full[cat_full] = 0.0  # zero catalogue exactly for emission (collar will be handled via mask)
        # Choose winner surface transform for final emission
        if winner == "e2":
            surface_full = scatter_smooth(surface_full, fp, sigma=1.85)
        # Generate final dots
        dcat_full = ndi.distance_transform_edt(~cat_full)
        if args.out and "ring" in args.out or winner == "e1" and res_e3["holdout_dti"] > max(res_e1["holdout_dti"], res_e2["holdout_dti"]):
            # Use tiered if E3 won
            use_ring = res_e3["holdout_dti"] > max(res_e1["holdout_dti"], res_e2["holdout_dti"])
        else:
            use_ring = False
        # For final build we will emit winner's method; by default E1 unless ring beat
        if res_e3["holdout_dti"] > max(res_e1["holdout_dti"], res_e2["holdout_dti"]):
            print("E3 wins, using tiered emission for final build")
            tier_mask = fp & (dcat_full > 2.0) & (dcat_full <= 3.0)
            main_mask = fp & (dcat_full > 3.0)
            cap = int(round(N_DOTS * 0.06))
            dots_final = tiered_greedy_spaced(surface_full, tier_mask, main_mask, N_DOTS, tier_cap=cap, spacing_px=SPACING)
        else:
            if winner == "e2":
                print("E2 wins, using scatter smooth + standard emission")
            else:
                print("E1 wins, using sharp + standard emission")
            mask = fp & (dcat_full > 3.0)
            dots_final = DN.greedy_spaced(surface_full, mask, N_DOTS, spacing_px=SPACING)
        print(f"final dots {int(dots_final.sum())} spacing {SPACING}")
        # Write via submission_writer
        from scripts.submission_writer import write_validated_submission_bundle

        # Need template path, catalogue path
        out_stem = Path(args.out).stem if args.out else f"gems91-sshac-e1-{DATE}"
        bundle = write_validated_submission_bundle(
            dots_final.astype(np.float32),
            stem_prefix=out_stem,
            date_tag=DATE,
            template_path=SAMPLE,
            catalogue_path=CAT,
            ledger_path=ROOT / "ledger/submissions.csv",
            downloads_dir=ROOT / "docs/downloads",
        )
        print(json.dumps(bundle, indent=2))
        # Save holdout reports
        evidence = {
            "e1": res_e1,
            "e2": res_e2,
            "e3": res_e3,
            "winner": winner,
            "canary": canary,
            "final": bundle,
            "audit": audit,
            "feature_names": feat_names,
        }
        Path("evidence/sshac_holdout.json").write_text(json.dumps(evidence, indent=2))
        print("wrote evidence/sshac_holdout.json")

    else:
        # Just write holdout evidence for review
        ev = {"e1": res_e1, "e2": res_e2, "e3": res_e3, "canary": canary, "audit": audit}
        Path("evidence/sshac_holdout.json").write_text(json.dumps(ev, indent=2))
        print("wrote evidence/sshac_holdout.json (holdout only)")


if __name__ == "__main__":
    main()
