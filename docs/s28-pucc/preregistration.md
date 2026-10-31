# S28-PUCC preregistration (frozen before execution) — 2026-10-31

**Branch:** `arena/db03647e-gemsdoe91` · **Lane:** S28-PUCC (self-assigned single method paragraph below)
**Budget:** ≤ 3 experiments or 2 h wall clock · **Weekly submission slots to be spent: 0** (promotion is a separate selector step)

## 1. The single method paragraph (the lane)

**PU-anchored off-catalogue corridor consensus (PUCC).** A strictly label-free rank
surface is formed as a weighted rank-geometric consensus of four independent corridor
evidence fields over the pinned 100 m GeoDAWN grid: (A) **SGMC-off corridor** —
crests of the combined TMI/gravity horizontal-gradient edge field within
`exp(-d/5 px)` of strictly off-catalogue USGS State Geologic Map Compilation
(SGMC) fault traces (`sgmc_faults_control` minus a 2 px collar of the pinned
`existing_faults` catalogue), i.e. faults present in a public state-map database
but absent from the competition Quaternary catalogue; (B) **vent-chain corridor** —
the pinned GDR hot/warm spring–well prior (`exp(-d/12 px)` on de-duplicated thermal
cells, `gems91.prior`) modulated by the same edge field; (C) **OSDR crest** — the
reused label-free odd-symmetric dip-reversal backbone
(`gems91.cvdc_osdr27.compute_osdr_sub_backbone_fp` on the cached 38-feature stack);
(D) **lidar-scarp crest** — rank product of `step_max` × `ex_max` from the pinned
12-band `lidar_scarp_features_u8`. Every catalogue-derived input (the exclusion
collar, the emission collar) is computed **fold-visibly** inside
`vendor.gems57.spatial.folds` (v3, 80 px feature-context buffer); the four
evidence fields themselves contain zero catalogue coordinates. The winning arm is
emitted as **37,654 binary dots** with the champion's B = 2 flank rule
(`d_cat > 2 px`), Poisson/NMS spacing 2.8 px, 300 m CELF facility-location
placement (`gems91.pdwc21.emit_dots_celf_submodular`) with registry-3px-halo
uniqueness caps, and packaged by the shared `vendor/gems57.submission_writer`
(finite [0, 1], zeros outside the footprint, `nodata=None`).

## 2. Hypotheses (ranked; full statement in HYPOTHESES.md)

| # | id | hypothesis | expected DTI gain | cost |
|---|----|-----------|-------------------|------|
| 1 | H28-1 | SGMC-off-catalogue corridor consensus (PUCC-A) | high | low |
| 2 | H28-2 | GDR vent-chain corridor extension (PUCC-B) | medium | low |
| 3 | H28-3 | OSDR sign-locked dip reversal, fresh consensus use (PUCC-C) | medium | low |
| 4 | H28-4 | Seismicity-gated tip-relay corridors (deferred: needs fold-visible tip geometry; see HYPOTHESES.md) | medium | medium |
| 5 | H28-5 | Buried basement-step concordance (deferred: overlaps S25/S16 basements) | low | medium |

**Top candidate = H28-1**, tested as the PUCC consensus (H28-1/2/3 + lidar crest)
inside the three preregistered arms below. The named non-fault mimic that could
imitate it: **misregistered or obsolete map contacts carried in the SGMC
compilation, and anthropogenic/geomorphic linears (canals, roads, yardangs) in
the lidar crest field.**

## 3. Experiments (frozen arms; ≤ 3)

All arms use `vendor.gems57.evaluate_holdout` (`gems57-pooled-hide-v2`) on
`vendor.gems57.spatial.folds` v3 (label-blind quadrants, whole-component,
80 px feature-context buffer). Emission inside folds: `emit_dots_nms`,
collar 2.05 px, spacing 2.8 px, budget ∝ fold area at 37,654-dot global rate.

* **E1 `pucc_consensus`** — weighted rank-geometric consensus of A–D
  (weights A 0.35, B 0.20, C 0.25, D 0.20).
* **E2 `pucc_hgb_corroboration`** — per-fold HistGradientBoosting on
  [A, B, C, D + 12 raw subsurface bands], trained on fold-**visible** catalogue
  pixels vs sampled train-domain negatives; OOF surface rank-averaged 50/50 with E1.
* **E3 `pucc_strict_corroboration`** — strict rank-geometric agreement of E1's
  four fields AND the E2 HGB surface (multiline-corroboration analogue).

Selection: highest pooled HOLDOUT-DTI; ties → lower FP weight.

## 4. Gates (all automated; no human inspection)

| gate | test | bar |
|------|------|-----|
| G1 leakage canary | single-component symmetric ROC-AUC vs withheld segments, per fold + pooled | ≤ 0.90 |
| G2 holdout superiority | pooled HOLDOUT-DTI vs matched controls (`champion_h33_2_b2`, `s27_osdr_e2`) | paired Δ CI > 0 vs champion; report vs S27 bar 0.159482 |
| G3 format | `vendor.gems57.validate` + re-read: 1-band float32, EPSG:32611, 3730×3292, all 12,279,160 px finite in [0,1], nodata None, 0 mass on catalogue, 0 mass ≤ 2 px of catalogue | all pass |
| G4 uniqueness (Rule 1) | surface Spearman \|ρ\| ≤ 0.90 vs every registry raster; ≤ 70 % of dots within 3 px of any single registry raster's dots | both pass (dense calibration rasters > 90 k dots reported separately, IR-51-LATTICE-01) |
| G5 estimate | score estimator anchored on 7 live-scored family rasters; projection labeled MODEL_PROJECTION_NOT_A_SCORE | CI reported |

**Verdict rule:** `OK TO DOWNLOAD: YES` iff G3 passes. `OK TO SUBMIT` (candidate
for a slot; the slot itself is the selector's decision) iff G1–G4 pass AND
pooled HOLDOUT-DTI beats the matched champion with paired 95 % CI excluding 0.
Any failure → `verdict = negative`, still written and logged.

## 5. Instruments and labels

* HOLDOUT-DTI: `gems57-pooled-hide-v2`, split `label-blind-quadrants-v3-feature-buffered`,
  pooled across 4 folds; n withheld positives reported per run; 95 % CI by
  paired physical 20 km block bootstrap (`EH.pooled_summary`, 1000 draws, seed 520810).
* SGMC-off diagnostic: DTI of the dot field vs the strictly-off-catalogue SGMC
  truth subset (proxy, not a score).
* ORGANIZER-CONFIRMED: none — no receipt is available in this checkout. All
  historical scores are USER-REPORTED/OWNER-REPORT.
* Projections are written as `MODEL_PROJECTION_NOT_A_SCORE`.

## 6. Known protocol irregularity (pre-declared)

IR-51-LATTICE-01 (inherited): the literal full-registry novelty rule (> 70 %
within 3 px of *any* raster) is mathematically impassable above 22,163 dots
against the 206,895-dot synthetic calibration lattice. This lane applies the
rule to every **genuine** raster (≤ 100 k dots) and reports the lattice
separately; that is the reading under which any 37,654-dot champion-family
submission could ever have been shipped.
