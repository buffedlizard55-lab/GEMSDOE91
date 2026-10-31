# S28-VFCD preregistration (frozen 2026-10-30, BEFORE any experiment)

Lane: **S28-VFCD — Vent-Field-Conditioned Detector** (see docs/HYPOTHESES_S28_VFCD.md;
H1 + H2 are the ranked-top hypotheses under test). This document is frozen by SHA-256
pin in `scripts/run_s28_vfcd.py`; the runner refuses to execute if it drifts.

## Instrument (unchanged, reused — Rule 2)

* Grid: pinned EPSG:32611 3730 × 3292 @ 100 m (`vendor/gems57/grid.py`).
* Holdout: `vendor/gems57.spatial.folds(catalogue, footprint, buffer_px=80)` —
  `label-blind-quadrants-v3-feature-buffered`, whole-component withholding, pixel-exact
  `masked_known` scoring mask. Evaluator `gems57-pooled-hide-v2` (pooled DTI,
  alpha=0.2, beta=0.8, 300 m triangular kernel; paired physical-20 km-block bootstrap
  CI, 1000 draws, seed 520810).
* Emitter: `gems91.pdwc21.emit_dots_celf_submodular`, budget 37,654 total (area-
  allocated across the 4 folds for holdout scoring), collar 3.05 px, min spacing 3.05 px.
* Model: `sklearn.ensemble.HistGradientBoostingClassifier` with the exact S25 params
  (max_iter=300, learning_rate=0.06, max_leaf_nodes=63, min_samples_leaf=40,
  l2_regularization=1.0, early_stopping=False), 4 positives : 1 sampled negative per
  fold, seed 520810 — the shared PU-OOF instrument of S25/S27 for matched comparison.

## Features

* **BASE** (25): the template's cached S25-FABRIC base stack (`bands 1–19` + gradient
  magnitudes), cached in `data/work/s27_cache/s25_repro_feats/` — reused, not rebuilt.
* **STATIC38** (38): the cached S27-CVDC static stack (`data/work/s27_cache/
  cvdc27_static38.f32.mmap`) — reused, not rebuilt.
* **VENT** (12, new in this lane): computed by `src/gems91/vfcd28.py` from the pinned
  GDR CSV (deduplicated by pixel cell; the catalogue-derived `dist_known_fault_px`
  column is NEVER read). T1 hot kernel (12 px, T-weighted); T2 warm kernel (25 px);
  T3 geothermometer kernel; T4 nearest hot/warm distance; T5 nearest high-T distance
  (temp ≥ 100 °C or geothermometer ≥ 150 °C); T6 hot-pair corridor density (≤ 40 px);
  T7 high-T-pair corridor density; T8 geothermometer-weighted corridor density;
  T9 hot kernel × off-catalogue (> 8 px); T10 off-catalogue corridor density;
  T11 SGMC-off-catalogue kernel (8 px, SGMC faults minus catalogue dilated 3 px);
  T12 SGMC-off × discharge concordance (T11 × footprint-normalized T2).
* **CONS** (3, new in this lane): rank of pinned `anc_h19_5`; mean rank of
  `anc_h19_4`/`anc_h16_1`; count of the 6 pinned anc rasters above their p85.

## Leakage canary (Rule 4, fail-closed)

Every feature used in any arm is tested ALONE on the holdout folds (per-fold + pooled,
symmetric ROC-AUC vs withheld positives). Any symmetric AUC > 0.90 stops the lane
(feature dropped at best; run aborted at worst). Catalogue-derived distance features
are recomputed per fold from `visible` only.

## Experiments (3 max, then stop — Rule 6)

| exp | arm name | features | surface | emitter |
|---|---|---|---|---|
| E1 | `vfcd_e1_vent_celf` | BASE + VENT | stitched 4-fold PU-OOF | CELF |
| E2 | `vfcd_e2_vent_phys_celf` | BASE + STATIC38 + VENT | stitched 4-fold PU-OOF | CELF |
| E3 | `vfcd_e3_vent_phys_cons_celf` | BASE + STATIC38 + VENT + CONS | stitched 4-fold PU-OOF | CELF |

Matched controls (all CELF): `ctrl_oof_base` (BASE only), `ctrl_oof_phys` (BASE +
STATIC38 — the E2-minus-VENT ablation, the exact marginal value of the vent stack),
and `ref_r0_dots` (the pinned GEMSDOE32 champion dots scored in-fold as an unmatched-
budget learning/education anchor — Rule: copying is allowed only for learning).

## Selection rule (frozen)

`best = argmax_{E1,E2,E3} pooled HOLDOUT-DTI`. Ties within 1e-6 go to the
lower-complexity arm (E1 < E2 < E3).

## Packaging gates (all automated — no human inspection)

1. Canary suite all-pass (max symmetric AUC ≤ 0.90).
2. Rule-1 Phase-1: surface Spearman |rho| ≤ 0.90 vs every frozen-registry reference
   (211 entries, `docs/s27-osdr/frozen-registry.json`, SHA-verified) plus every
   additional `.tif` currently in `docs/downloads/`.
3. Rule-1 Phase-2: ≤ 70 % of final dots within 3 px of any competitive (≤ 90,000
   positive px) reference raster's dots; dense/blanket references (> 90k px or
   "lattice" in name) reported separately as calibration witnesses, not lanes
   (IR-S28-01: a ≥ 206k-dot calibration lattice forces ≥ 82 % proximity for ANY
   37,654-dot raster; it is not any lane's submission and is not a previous
   submission).
4. Shared fail-closed writer (`vendor/gems57.submission_writer.write_submission`):
   single-band float32 GeoTIFF + one-TIFF ZIP; exact CRS/shape/transform; all values
   finite in [0, 1]; zero positive mass on the catalogue; zero positive mass outside
   the footprint. **Zeros encoding** (all-finite) — the `-nan` encodings are what
   triggered the organizer form error "Predicted values must be in range [0, 1]".
5. Validator receipt recorded (`vendor.gems57.validate.validate` + `assert_submittable`).

## Rule-3 labeling

Every number leaves this lane stamped `HOLDOUT-DTI (gems57-pooled-hide-v2, v3 folds,
N withheld positives, 95 % CI)` or `ORGANIZER-CONFIRMED` (submission-page receipt) or
`USER-REPORTED` (owner claim) or `MODEL_PROJECTION_NOT_A_SCORE`. Projections are never
written as scores.

## Budget

3 experiments or 2 hours, whichever first. 0 weekly submission slots spent here.
Promotion to a live slot is the separate selector step (Rule 6) within the weekly cap
on the submission page.
