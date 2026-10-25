# Session 14 Pre-Registered Hypotheses (`S14-LSRG`, 2026-10-24)

> **Later protocol correction (2026-10-25):** S14-LSRG-FF is a negative research result, not a promotion. Its strict sibling final-dot overlap is 82.759% within 3 px of S12-SPAC (>70% limit), so it is a duplicate and must stop under the current parallel-run protocol. It also trails the comparable S13-PTHA holdout best and has unassigned-lane / data-rights blockers. See `docs/REVIEW-ARENA-72CF-20261025.md` and IR-91-72CF-01. The experimental preregistration and results below are retained as historical record.

**Status:** Frozen *prior* to computing any Session 14 holdout score or emitting any candidate GeoTIFF.
**Branch:** `arena/eeaf78c1-gemsdoe91`
**Lane (self-declared; no external selector paragraph was supplied — standing `IR-91-S12-01`):**
*LiDAR-Scarp + Radiometric-Ratio + Spring-Geometry surface with Winner-Economics Dinkelbach emission (`S14-LSRG`).*

---

## 0. Why did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` score 0.2778? (Measured answer)

Measured 2026-10-24 in this sandbox with the shared evaluator (`scripts/evaluate_holdout.py`)
on sha256-pinned rasters (`registry/data_manifest.json`, all 15 entries re-verified after
`scripts/restore_data.py`). Raw evidence: `evidence/s14_winner_forensics.json`
(script: `scripts/s14_forensics.py`). Organizer scores below are **CLAIM-USER-REPORTED**
(session prompt; no DrivenData receipt is pinned in this repo).

| Raster | CLAIM organizer | dots | med. NN spacing | % dots >10 px from catalogue | SGMC control (measured) | HOLDOUT v1.1 full-map (measured) |
|---|---:|---:|---:|---:|---:|---:|
| h16-1 (dense) | 0.1855 | 123,939 | 1.00 px | 59.2% | 0.1113 | 0.1622 |
| h19-4 (dense) | 0.1894 | 123,779 | 1.00 px | 59.1% | 0.1052 | 0.1628 |
| h19-5 (dense) | 0.1922 | 121,131 | 1.00 px | 58.9% | 0.0992 | 0.1617 |
| h19-5 dotted d1.5 | 0.2477 | 60,069 | 2.24 px | 59.3% | 0.0999 | 0.1672 |
| h19-5 dotted d2.8 | 0.2600 | 44,090 | 3.16 px | 59.6% | 0.0942 | 0.1573 |
| solo d2.8 | 0.2708 | 40,199 | 3.00 px | 65.4% | 0.0953 | 0.0478 |
| **R0 = h33-2-b2** | **0.2778** | **37,654** | **3.16 px** | **69.8%** | 0.0954 | 0.0066 |

Spearman ρ vs CLAIM organizer score (n=7): **n_dots ρ = −1.000 (p<0.001)**;
median spacing ρ = +0.898 (p=0.006); share of dots >1 km from catalogue ρ = +0.857 (p=0.014);
SGMC control ρ = −0.821 (p=0.023); HOLDOUT v1.1 ρ = −0.750 (p=0.052).

**Mechanism (three additive effects):**

1. **Metric economics of the max-kernel.** DTI = T / (0.2·T + 0.2·(S−M) + 0.8·|G|) with
   T = Σ_truth max_j p_j·k(‖j−g‖), triangular k, R = 300 m (`scripts/dti.py`). Once a truth
   pixel is covered at k≈1 by one dot, every additional dot on the same line adds ≈0 to T
   but full price to the 0.2·(S−M) term. Thinning a continuous line to dots spaced ≈3 px
   (the kernel radius) therefore keeps T and cuts S by ≈3.3×. The fleet's own ladder is a
   controlled experiment on one surface: 0.1922 → 0.2477 → 0.2600 → 0.2708 → 0.2778 as
   dots fall 121k → 37.6k. **Emission geometry, not surface geology, explains most of the
   0.19 → 0.28 climb.**
2. **Far-field targeting.** The hidden test faults are absent from the catalogue *by
   construction*; the catalogue's own 300 m halo is the most thoroughly mapped ground in
   the area, so mass spent there has near-zero expected yield (ρ = −0.68 for halo share).
   R0 spends 69.8% of its dots >1 km from any catalogued fault — the highest of the seven.
3. **Precision of the ancestor surface.** All top scores descend from the h19-5
   "multi-line corroborated" surface: independent lineament families must agree before a
   pixel earns mass. Agreement-gating trades recall for precision, which is what the
   β = 0.8 denominator rewards.

**Corollary (why our holdout misled emission design) — `IR-91-S14-01`:** the shared
evaluator v1.0 deletes every prediction inside the 1 km buffer around a withheld segment
("halo deletion"). With a 3 px kernel this makes HOLDOUT-DTI ≡ 0 for *every* real
submission raster (all carry zero mass exactly on catalogue pixels — measured), while
OOF fold predictions are allowed to sit on withheld pixels. v1.0 remains the frozen
comparator for surface ranking; `gems91-hide-recover-v1.1-nohalo` (added 2026-10-24,
`mask_buffer_predictions=False`) restores leaderboard geometry for emission tuning.
Both holdout flavours *anti-correlate* with the organizer score across the fleet
(ρ = −0.75) because recovering catalogued faults is the opposite allocation from
discovering uncatalogued ones. HOLDOUT-DTI is therefore used here only as a
*surface sanity gate* (must not collapse), never as the emission objective.

**Can we beat 0.2778?** The remaining headroom is (a) a *better surface* at winner
emission economics — R0's surface never saw the 1 m LiDAR scarp stack or per-element
radiometrics, both pinned in this repo and used by **no** prior lane (verified by grep,
2026-10-24); and (b) *exact* expected-DTI emission (Dinkelbach stopping at λ₀ ≈ target
score) instead of fixed-spacing thinning, which is provably suboptimal wherever the
posterior is heterogeneous. Leaderboard best 0.4413 (CLAIM-USER-REPORTED) implies the
hidden truth is substantially recoverable; 0.2778 is not a ceiling.

---

## 1. Five ranked candidate hypotheses

| Rank | ID | Layer(s) | Physical signature | Why it catches *uncatalogued* faults | Named non-fault mimic → rejection | Difference vs everything in this repo | Expected gain / cost |
|---:|---|---|---|---|---|---|---|
| 1 | **H14-1 LiDAR scarp direct detection** | `data/external/lidar_scarp_features_u8.tif` (12 bands: ex_max/mean, step_max, lap±, down/upface, cross_max, relief, coh100, strike, valid), aggregated from 1 m DEMs | Signed cross-strike elevation step + laplacian crest + 100 m strike coherence at 100 m cells | Holocene scarps <2 m high are invisible in the 19-band 100 m stack (B12/B19 are smooth) and too subtle for 1:250k catalogue mapping, but are the *direct* surface rupture record | Lake Lahontan shoreline benches, road cuts, dune slipfaces → require corroboration (H14-5 gate) + coh100 strike persistence | No lane in GEMSDOE91 reads this file (grep-verified); prior fleet lidar lanes used raw slope, not this scarp-decomposed stack | High / Low (file pinned, sha256-verified) |
| 2 | **H14-2 Radiometric ratio alteration** | `data/external/geodawn_rad_u8.tif` bands K, Th, U, TC (USGS GeoDAWN) | Th/K depression (K-metasomatism), U/K enrichment, and their cross-strike steps along lineaments | Hydrothermal fluids rise along permeable *hidden* faults and potassically alter wall rock; alteration is a fluid-pathway tracer independent of scarp preservation | Felsic plutons (high K) → ratio must be *linear* (lineament-coincident), not blob-like; TC level alone excluded as evidence | Only TC (Band 06) was ever used; K/Th/U separately never enter any model here | Medium / Low |
| 3 | **H14-3 Spring-anchored blind-fault habitat** | GDR well/spring inventory (`gdr_wellspring_in_footprint.csv`, 27,092 records) via existing `e2_gdr_*` static cols (excluded by S12/S13!) + new distance-to-hot-spring field | Thermal springs (temp/geothermometry) cluster where fault permeability taps deep circulation; a hot spring >300 m from catalogue is positive evidence of a blind structure | Springs are *effects* of the hidden faults the contest targets, not of mapping effort | Basin-margin artesian springs, springs on mapped faults (collar-excluded anyway) → used only as habitat multiplier on lineament support | Features exist in the static memmap but S12-SPAC and S13-PTHA dropped cols 34–43; no winning-lineage model uses them | Medium / Low |
| 4 | **H14-4 Fold-safe tip/stepover geometry** | `existing_faults.tif` via `dd_vtc_pu.compute_fold_safe_catalogue_features` (tip prox, relay stepover, strike continuation), visible-faults-only per fold | Fault growth by tip propagation and relay-ramp linkage concentrates *unmapped* segments in 0.3–3 km tip/stepover corridors (NOT in the 300 m halo) | Catalogue segments end where mapping stopped, not where the fault ends; stepovers are the classic blind-geothermal play | Random lineament crossings → bounded multiplicative boost (≤1.28×) on physical support only | Implemented for H91 but absent from S11/S12/S13 winners; combined here with far-field emission instead of halo-hugging | Medium / Low |
| 5 | **H14-5 Multi-family corroboration + winner-economics emission** | OOF posterior × independent crest families (PTHA crest, lidar coh100, rad-ratio step) → Dinkelbach greedy (`ptha.dinkelbach_*`) | A pixel earns a dot only if ≥2 physically independent families agree AND its exact marginal expected-DTI gain at λ₀ = 0.28 is positive under the 300 m max-kernel | This is the measured winning mechanism (§0): precision-gating + kernel-saturating unit dots at ≈3 px spacing, far-field weighted | Correlated artefacts (flight-line seams appear in mag *and* rad) → families chosen from independent sensors (lidar vs airborne gamma vs magnetics) | S13 used Dinkelbach on a single-physics-blend surface with λ₀ = 0.206 (its own holdout); here λ₀ is set from the *organizer* frontier (0.28) and tuned on v1.1-nohalo | High / Medium |

## 2. Experiments (budget: 3)

- **E1 (surface):** HGB ensemble on [static 49 (incl. e2 GDR) + S11 16 + PTHA 20 + **S14 new: lidar 12 + rad-ratio 6**] + fold-safe catalogue geometry (3, per-fold). Report HOLDOUT-DTI v1.0 (comparator vs S13 0.244601) **and** v1.1-nohalo, canary AUC for every new feature (fail if >0.90).
- **E2 (corroboration):** E1 posterior gated by ≥2-family agreement; same scoring. Keep whichever of E1/E2 wins v1.1 without collapsing v1.0 (>0.20 floor = surface-sanity gate).
- **E3 (emission):** Dinkelbach λ₀ ∈ {0.24, 0.28, 0.32} on OOF folds scored with v1.1-nohalo; pick λ₀, emit full-map, run all gates (format, [0,1], collar >3 px, registry uniqueness surface ρ ≤0.90 & dots ≤70% within 3 px vs every local + fleet raster, SGMC control reported for the record).

**Original experimental promotion criterion (historical):** format, novelty, v1.0 surface floor, and winner-like emission geometry. This criterion was incomplete because it did not make the comparable-best, lane-assignment, full-registry, sibling-final-dot, and derivative-rights gates conjunctive. The current shared readiness policy and task protocol supersede that draft. Under the corrected rule S14-LSRG-FF is **negative**: its 82.759% sibling overlap exceeds 70%, its HOLDOUT-DTI trails the comparable S13-PTHA result, and other gates remain unresolved. A negative is retained as a deliverable; it is not a slot recommendation.

## 3. External data check (no new data needed)

At S14 experiment time, the run log records 15/15 inputs as sha256-verified on 2026-10-24. In the current Arena checkout, `python scripts/restore_data.py --check` reports all 15 manifest inputs missing; do not treat a historical pin check as present-day local availability. The manifest includes the competition 19-band stack, `existing_faults.tif`,
`sample_submission.tif`, GeoDAWN radiometrics u8, LiDAR scarp u8, GDR springs CSV,
USGS SGMC control. Official upstreams for manual review:
DrivenData competition https://www.drivendata.org/competitions/306/competition-doe-gems/ ·
reference solution https://github.com/drivendataorg/gems-prize-reference-solution ·
GeoDAWN https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and ·
GDR #1391 https://gdr.openei.org/submissions/1391 · INGENIOUS https://gbcge.org/current-projects/ingenious/ ·
EPSG:32611 https://epsg.io/32611 · Tversky index https://en.wikipedia.org/wiki/Tversky_index ·
rules PDF https://docs.nlr.gov/docs/fy26osti/96647.pdf
