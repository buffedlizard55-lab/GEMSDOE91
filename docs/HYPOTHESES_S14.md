# Historical Session 14 Pre-Registered Hypotheses (`S14-LSRG`, 2026-10-24)

> **Current review supersedes this archive.** The `0.2778` GEMSDOE32 value is user-reported, not organizer-confirmed; no receipt is available. Historical local metrics and data-presence statements below are not rerun or validated in the current checkout. The official inputs are absent, preflight is blocked, and this document does not approve any TIFF for download or submission. See [current review](REVIEW-ARENA-AE77BA5B-20261025.md).

**Status:** Frozen *prior* to computing any Session 14 holdout score or emitting any candidate GeoTIFF.
**Branch:** `arena/eeaf78c1-gemsdoe91`
**Lane (self-declared; no external selector paragraph was supplied — standing `IR-91-S12-01`):**
*LiDAR-Scarp + Radiometric-Ratio + Spring-Geometry surface with Winner-Economics Dinkelbach emission (`S14-LSRG`).*

---

## 0. Evidence correction: the GEMSDOE32 `0.2778` value is unverified

The original project prompt reported `0.2778` for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros`. On 2026-10-25, the linked [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) stated “NO ORGANISER SCORE EXISTS,” marked the named H33 artifact unscored, and labelled `0.2747` a projection/model. No submission receipt was available to confirm `0.2778`. Therefore it is a **USER-REPORTED CLAIM**, not an organizer score. This historical section does not establish why that value was reported or that any listed operation caused it.

### Metric mechanism (not a causal explanation of the claim)

The official DrivenData problem description specifies a linear triangular kernel with 300 m support, `α = 0.2`, and `β = 0.8`. The repository's tested algebra is:

`DTI = T / (0.2 T + 0.2 (S − M) + 0.8 |G|)`

`T` uses maximum kernel-weighted credit per truth pixel. Once that maximum is saturated, additional prediction mass may add no truth credit while increasing the false-positive term. Sparse emission can therefore help in some configurations. It does not prove that spacing, collar deletion, far-field placement, or any other operation caused the unverified `0.2778` claim.

### File facts are not organizer score evidence

The historical local byte-lineage note describes a 37,654-dot R0 raster and deletion of 2,545 dots within two pixels of the existing-fault mask. These are file/lineage observations, not a submission receipt. Older tables that correlate morphology with the prompt's claimed values inherit that unverified label; they cannot establish a causal score change. No numerical expected score, improvement over `0.2778`, or leaderboard projection is asserted here.

The earlier S14 experiment plan and its data-availability statements refer to a prior checkout/environment. In the current checkout, official competition inputs are absent and preflight is blocked. The hypotheses below are archived preregistrations, not current data-coverage, licensing, novelty, or download approval. See the [current review](REVIEW-ARENA-AE77BA5B-20261025.md) and [current review card](run-card-REVIEW-AE77BA5B.json).
---

## 1. Five ranked candidate hypotheses

| Rank | ID | Layer(s) | Physical signature | Why it catches *uncatalogued* faults | Named non-fault mimic → rejection | Difference vs everything in this repo | Expected gain / cost |
|---:|---|---|---|---|---|---|---|
| 1 | **H14-1 LiDAR scarp direct detection** | `data/external/lidar_scarp_features_u8.tif` (12 bands: ex_max/mean, step_max, lap±, down/upface, cross_max, relief, coh100, strike, valid), aggregated from 1 m DEMs | Signed cross-strike elevation step + laplacian crest + 100 m strike coherence at 100 m cells | Holocene scarps <2 m high are invisible in the 19-band 100 m stack (B12/B19 are smooth) and too subtle for 1:250k catalogue mapping, but are the *direct* surface rupture record | Lake Lahontan shoreline benches, road cuts, dune slipfaces → require corroboration (H14-5 gate) + coh100 strike persistence | No lane in GEMSDOE91 reads this file (grep-verified); prior fleet lidar lanes used raw slope, not this scarp-decomposed stack | High / Low (historically reported as pinned; not present in current checkout) |
| 2 | **H14-2 Radiometric ratio alteration** | `data/external/geodawn_rad_u8.tif` bands K, Th, U, TC (USGS GeoDAWN) | Th/K depression (K-metasomatism), U/K enrichment, and their cross-strike steps along lineaments | Hydrothermal fluids rise along permeable *hidden* faults and potassically alter wall rock; alteration is a fluid-pathway tracer independent of scarp preservation | Felsic plutons (high K) → ratio must be *linear* (lineament-coincident), not blob-like; TC level alone excluded as evidence | Only TC (Band 06) was ever used; K/Th/U separately never enter any model here | Medium / Low |
| 3 | **H14-3 Spring-anchored blind-fault habitat** | GDR well/spring inventory (`gdr_wellspring_in_footprint.csv`, 27,092 records) via existing `e2_gdr_*` static cols (excluded by S12/S13!) + new distance-to-hot-spring field | Thermal springs (temp/geothermometry) cluster where fault permeability taps deep circulation; a hot spring >300 m from catalogue is positive evidence of a blind structure | Springs are *effects* of the hidden faults the contest targets, not of mapping effort | Basin-margin artesian springs, springs on mapped faults (collar-excluded anyway) → used only as habitat multiplier on lineament support | Features exist in the static memmap but S12-SPAC and S13-PTHA dropped cols 34–43; no winning-lineage model uses them | Medium / Low |
| 4 | **H14-4 Fold-safe tip/stepover geometry** | `existing_faults.tif` via `dd_vtc_pu.compute_fold_safe_catalogue_features` (tip prox, relay stepover, strike continuation), visible-faults-only per fold | Fault growth by tip propagation and relay-ramp linkage concentrates *unmapped* segments in 0.3–3 km tip/stepover corridors (NOT in the 300 m halo) | Catalogue segments end where mapping stopped, not where the fault ends; stepovers are the classic blind-geothermal play | Random lineament crossings → bounded multiplicative boost (≤1.28×) on physical support only | Implemented for H91 but absent from S11/S12/S13 winners; combined here with far-field emission instead of halo-hugging | Medium / Low |
| 5 | **H14-5 Multi-family corroboration + winner-economics emission** | OOF posterior × independent crest families (PTHA crest, lidar coh100, rad-ratio step) → Dinkelbach greedy (`ptha.dinkelbach_*`) | A pixel earns a dot only if ≥2 physically independent families agree AND its exact marginal expected-DTI gain at λ₀ = 0.28 is positive under the 300 m max-kernel | This is a mechanism-based design proposal (§0), not an established explanation of the unverified `0.2778` claim: precision-gating + kernel-saturating unit dots at ≈3 px spacing, far-field weighted | Correlated artefacts (flight-line seams appear in mag *and* rad) → families chosen from independent sensors (lidar vs airborne gamma vs magnetics) | S13 used Dinkelbach on a single-physics-blend surface with λ₀ = 0.206 (its own holdout); here λ₀ = 0.28 was proposed from an unverified reported value, not an organizer-confirmed frontier and tuned on v1.1-nohalo | High / Medium |

## 2. Experiments (budget: 3)

- **E1 (surface):** HGB ensemble on [static 49 (incl. e2 GDR) + S11 16 + PTHA 20 + **S14 new: lidar 12 + rad-ratio 6**] + fold-safe catalogue geometry (3, per-fold). Report HOLDOUT-DTI v1.0 (comparator vs S13 0.244601) **and** v1.1-nohalo, canary AUC for every new feature (fail if >0.90).
- **E2 (corroboration):** E1 posterior gated by ≥2-family agreement; same scoring. Keep whichever of E1/E2 wins v1.1 without collapsing v1.0 (>0.20 floor = surface-sanity gate).
- **E3 (emission):** Dinkelbach λ₀ ∈ {0.24, 0.28, 0.32} on OOF folds scored with v1.1-nohalo; pick λ₀, emit full-map, run all gates (format, [0,1], collar >3 px, registry uniqueness surface ρ ≤0.90 & dots ≤70% within 3 px vs every local + fleet raster, SGMC control reported for the record).

**Promotion rule:** candidate is labelled `promote` only if (i) all format gates pass,
(ii) uniqueness gates pass, (iii) v1.0 E-score ≥ 0.20 (surface not degenerate) and
(iv) emission geometry matches winner economics (unit dots, median spacing ≥2.8 px,
≥60% dots >10 px from catalogue OR v1.1-justified deviation logged). A candidate that
fails is still delivered as a labelled negative result. **No weekly slot is spent by
this session; slot use remains a human selector decision (`SLOT_PLAN.md`).**

## 3. Historical data-provenance notes — not current availability

The prior S14 record reported these layers as pinned and SHA-256-verified in its then-current
environment. In the current checkout, none of the 15 manifest-listed inputs is present and
preflight is blocked; no mirror restore was performed for this review. The filenames below
are historical provenance notes only and do not establish current file availability,
challenge-use clearance, or permission to redistribute/share data. Official source links
for future verification:
DrivenData competition https://www.drivendata.org/competitions/306/competition-doe-gems/ ·
reference solution https://github.com/drivendataorg/gems-prize-reference-solution ·
GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
GDR #1391 https://gdr.openei.org/submissions/1391 · INGENIOUS https://gbcge.org/current-projects/ingenious/ ·
EPSG:32611 https://epsg.io/32611 · Tversky index https://en.wikipedia.org/wiki/Tversky_index ·
rules PDF https://docs.nlr.gov/docs/fy26osti/96647.pdf
