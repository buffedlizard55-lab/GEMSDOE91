# S30-VCE preregistration — Vent-Concordant Emission (frozen before experiments)

**Lane (single method paragraph).** Build a label-blind *vent-concordant* fault-probability
surface from the pinned DOE-GDR wellspring/geochemistry catalogue (`gdr_wellspring_in_footprint.csv`,
[DOE GDR #1391](https://gdr.openei.org/submissions/1391): hot/warm springs and wells with
quartz–chalcedony–cation geothermometry), the GeoDAWN radiometric K–Th–U–TC stack
(`data/external/geodawn_rad_u8.tif`) for hydrothermal alteration textures, the supplied
conductivity / strain / earthquake-density GeoDAWN bands (`training_features.tif` bands
`cond_surf`, `geod_2ndinv`, `deq_n100a15`) and LiDAR scarp persistence
(`data/external/lidar_scarp_features_u8.tif`) as subpixel corroboration; then emit
**37,654** binary `{0,1}` dots with **2.8 px** minimum spacing and a **3.05 px**
catalogue collar by greedy NMS on the surface, and score with the shared hide-and-recover
pooled DTI instrument (`vendor/gems57`, `gems57-pooled-hide-v2`, v3 label-blind-quadrant
folds with 80 px feature-context buffers, `alpha=0.2`, `beta=0.8`, 300 m triangular kernel).

**Hypothesis (H-VCE-1).** Hidden faults in the GEMS test set are the structures that host
or steer geothermal upflow. Surface manifestations of that upflow — hot springs, high
geothermometry temperatures, K-depletion/uranium-mobility alteration halos, conductive
clay caps, and localized seismicity/strain — therefore mark the *test* class of faults
(expert-identified, geothermal-indicative, absent from the USGS/INGENIOUS catalogue)
better than they mark catalogue faults. Emission restricted to vent-concordant corridors
should cover withheld fault segments at least as well as potential-field lineament ridges
while spending less mass far from truth.

**Named non-fault mimic.** Basin-fill saline groundwater (playa/lacustrine conductors) and
pediment weathering K-depletion can produce the alteration/conductivity signatures with no
fault control; volcanic-hydrothermal alteration centers are not Quaternary faults. Negative
control arm `ctrl_ventblind` (identical blend with vent/alteration/corridor terms removed)
measures the vent-lane increment directly.

**What is NOT used.** The leaky `dist_known_fault_px` column (IR-H91-03) is never read.
No catalogue-derived feature enters a static surface; the E3 supervised arm re-derives its
catalogue-context features per fold from `visible` faults only.

## Feature set (label-blind, computed once; percentile-ranked on the footprint)

| name | source | direction (fixed a priori) |
|---|---|---|
| `vent_kde` | GDR sites, weight `log1p(T_eff)`, σ=8 px | high T near ⇒ positive |
| `vent_geo_kde` | GDR sites with T_eff ≥ 150 °C, σ=12 px | positive |
| `vent_corridor` | 3-nearest-neighbor segments (≤40 px) between vent sites, σ=2 px | positive |
| `alter_kdep` | local K depression (31 px mean) × TC percentile, rad u8 | depletion ⇒ positive |
| `alter_uelev` | clip(U − Th) radiometric mobility | positive |
| `cond_cap` | `cond_surf` (B17) | high conductivity ⇒ positive |
| `strain2` | `geod_2ndinv` (B4) | high strain-rate invariant ⇒ positive |
| `eq_near` | 1 − rank(`deq_n100a15` B10) | near seismicity ⇒ positive |
| `scarp` | lidar `ex_max`/`coh100` where `valid`, neutral 0.5 elsewhere | positive |

Fold-local features for the E3 supervised arm only: `d_vis_rank` (distance to `visible`
catalogue) and `tip_kde` (visible fault-endpoint density), recomputed per fold.

## Arms, controls, and the three experiments

* **E1 (static)** `S1 = 0.30·vent_kde + 0.26·vent_corridor + 0.10·vent_geo_kde + 0.14·alter + 0.12·strain2 + 0.08·cond_cap`,
  `alter = 0.6·alter_kdep + 0.4·alter_uelev`.
* **E2 (static + scarp)** same weights renormalized to include `0.14·scarp` (E1 terms × 0.86).
* **E3 (supervised OOF)** HistGradientBoosting (S25 params: 300 iters, lr 0.06, 63 leaves,
  min_leaf 40, l2 1.0, 4 negatives per positive, seed 520810) on all nine label-blind
  features + the two fold-local catalogue features; stitched 4-fold OOF surface; final
  surface refit on the full catalogue at packaging.
* **Controls** (scored on identical folds, never selected): `ctrl_ventblind`
  (static `0.45·strain2 + 0.25·cond_cap + 0.30·scarp`) and `ctrl_champion_fixed`
  (the pinned GEMSDOE32 `h33-h33-2-b2` dots scored as a fixed raster — **not fold-fair**,
  labelled `REFERENCE-ONLY` because its surface saw the full catalogue).

Emission per fold: `gems91.pdwc21.emit_dots_nms` with fold-area-proportional budgets,
`collar_px=3.05`, `min_spacing_px=2.8`, domain `footprint & fold.region`, collar vs
`fold.visible` only. Identical emission for every arm.

## Gates (all automated; no human inspection)

1. **Leakage canary:** each feature alone vs withheld truth on each fold;
   fail-closed if any symmetric AUC > 0.90.
2. **Lane drift (Rule 1):** surface Spearman |ρ| ≤ 0.90 vs every registry raster
   (fleet registry + pinned + prior downloads + GEMSDOE32 H46-TRHV/H51-EWSP) **before**
   placement, and ≤ 70 % of final dots within 3 px of any registry raster's dots **after**.
3. **Validation:** all-finite float32 in [0, 1], zeros outside the footprint, zero mass on
   the catalogue, CRS `EPSG:32611`, shape 3730×3292, transform pinned — the all-finite
   `-zeros` encoding is the primary download (the 2026-10-31 portal error
   “Predicted values must be in range [0, 1]” is treated as a NaN/out-of-range hazard).
4. **Estimate discipline:** HOLDOUT-DTI (evaluator version, 60,988 withheld positives,
   95 % paired bootstrap CI) is the only promotion number; SGMC off-catalogue DTI is a
   blind diagnostic; any leaderboard-scale number is `MODEL_PROJECTION_NOT_A_SCORE`.

## Selection and stop rule

Select the arm with the highest pooled HOLDOUT-DTI. `promote` requires: canary pass,
surface and dot uniqueness pass, validator pass, and a paired 95 % CI above zero versus
the best control **on the same folds**. Budget: 3 experiments (E1–E3) or 2 hours,
whichever first. Promotion to a live weekly slot remains a separate selector step; zero
slots are spent by this run.

**Frozen:** 2026-10-31 (this document's sha256 is recorded in the run card).
