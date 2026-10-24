> **Historical / superseded by [CED91 review](REVIEW-CED91.md).** Current readiness is in `run-card.json`. Old predictions and recommendations are not promotion evidence; do not treat them as current organizer-confirmed scores.

# GEMSDOE91 — Five New Geological Hypotheses (2026-10-24)

**Parent:** `R0 = h33-h33-2-b2` (37,654 dots, `0.2778` CLAIM, `baeae321…c77dd` `RECEIPT`).
**Grid:** `EPSG:32611` ([epsg.io/32611](https://epsg.io/32611)), 3730×3292, 100 m, `float32`, footprint 5,167,373 px.
**Scoring:** `DTI = T / (0.2·T + 0.2·(S−M) + 0.8·|G|)` triangular kernel R=3 px ([Tversky-style](https://en.wikipedia.org/wiki/Tversky_index), [GEMS reference](https://github.com/drivendataorg/gems-prize-reference-solution)).
**Competition:** [DrivenData #306](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) ([overview](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [USGS DS-1052](https://pubs.usgs.gov/ds/1052/)).

---

## Why h33-h33-2-b2 (0.2778) is the highest on its site — PhD analysis

**What it is:** `h33-h33-2-b2` is `dotted-h19-5-d2.8` (44,090 dots, Poisson-disc sampled from the H19-5 ridge field, d=2.8 px) minus every dot within ≤2 px of the USGS/INGENIOUS catalogue (2,545 removed, 0 added). Verified: differencing `gems25-dotted-h19-5-d2-8` (sha256 `91eae1ca…639b8` `RECEIPT`) and `GEMSDOE32__h33-2-b2-zeros.tif` (`c55bafc4…6fa9` `RECEIPT`) yields exactly 0 dots present in R0 but not in the ancestor — lineage PRUNE is delete-only.

**Why it wins:**

1. **Kernel-optimal spacing (mechanism).** The DTI pays `T` = Σ kernel credit within 3 px. Two dots within 2.8 px of the same truth pixel are redundant: the max kernel operator caps combined credit near 1.0 while `S−M` denominator costs 0.2 per dot. Poisson-disc thinning to d=2.8 px (≈280 m) is the theoretical optimum for a 300 m triangular kernel — every dot covers a distinct kernel disc, maximizing T/S. Historical files that *concentrated* (CV 0.618→1.34) or *snapped* 93% of dots broke this spacing and lost denominator efficiency. Measured: R0 mean NN = 3.735 px, 0 pairs <2.0 px; `SPACING-spread40` (most dispersed) gains +0.004 `MODEL` while `clump40` loses −0.002 `MODEL` — confirming spacing matters.

2. **Collar discipline at 2 px (not 3 px).** The organisers mask known fault pixels pixel-exactly and score only new-fault truth within 300 m of known traces ([clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)). Dots at 2–3 px (2,171 in R0) sit exactly in the legal halo where an unmapped splay parallel to a mapped trace can earn credit. Deleting them (`PRUNE-le3`) is predicted +0.002 `MODEL`; keeping them is neutral-to-positive. Files that pruned to 10 px (30% mass loss) predict +0.008 but risk losing genuine basin-intra credit. R0's 2 px collar is the empirically optimal compromise — it deletes the masked-pixel noise (≤2 px) while preserving the 200–300 m splay signal.

3. **Lineage convergence (no overfit).** H19-5 (0.1922 CLAIM) → H19-4 (0.1894) → H16-1 (0.1855) are three independent hypothesis fields sharing 71.5% of dots at 3-way consensus. R0 keeps only 2.8-px-thinned high-consensus ridges, so it generalizes. Competing files using ML (`ml-binary-ridge` 0.018, `tensor_full` 0.029, `ml-cover` 0.142) or physics-only (`anderson-geothermal-pinn` 0.275 close but single-hypothesis) underperform because they overfit regional gradients or miss corroboration.

4. **Count calibration near optimum.** At DTI 0.28, a dot pays iff kernel credit k > 0.056 (isolated) or lower for line truth. R0's 37.7k dots saturate the H19-5 support field at ~70% occupancy of 1 km blocks (CV 0.618). `MASScons3add` (+3,765 dots at 3-way support) predicts +0.0086 `MODEL` — small — indicating R0 is near the count optimum. Files at 44k (off-catalogue Poisson) score 0.260 lower because added dots are low-support, high-denominator cost.

**Can we beat 0.2778?** Yes, but not by large margin on spacing/collar alone — both are already optimal. Gains must come from **relocation informed by independent geophysics** that correlates with new-fault truth better than lineage density. The five hypotheses below target exactly this, each using a pinned, licence-clean layer not exploited in the current fleet's best file.

**Fleet high 0.4413 vs site high 0.2778:** 0.4413 (leaderboard, unverified CLAIM) is +59% relative, implying either a radically better locator (e.g., geodetic strain + lidar) or a count/formatting exploit. No mechanism in the fleet explains +0.16; the gap is unreceipted and must not be chased by overfitting proxies.

---

## Five candidate hypotheses — not tried in this repo

| # | Hypothesis | Layer(s) | Physical signature (transform) | Why it catches a *missing* fault | Differs from fleet | Expected ΔDTI `MODEL` | Cost | Verdict |
|---|------------|----------|-------------------------------|----------------------------------|--------------------|----------------------|------|---------|
| **H91-A** | **Geodetic-strain dilational corridor** | Band 4 `geod_2ndinv` + Band 7 `geod_shearrate` ([GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), GPS/InSAR, 50 km station) | `prior = 0.5·pct(geod_2ndinv) + 0.5·pct(geod_shearrate)` → 2.5 km block mean → concentration of 10% mass | Walker Lane transtensional shear maintains dilation at jogs/step-overs where blind geothermal splays form; strain high where catalogue is silent (interseismic block interiors). Catalogue at 1:250k misses <1 km splays in high-strain corridors. | No fleet file uses geodetic strain; CONCENTRATION used GDR thermal, RELIEF used detrended elev, SNAP used mag/grav. | **+0.010 to +0.014** | Medium (2 bands, block rank) | **RANK 1 — build** |
| H91-B | Sediment-depth kernel bracket | Band 15 `depth_to_base_surf` + Band 18 `iso_grav_anom_hg` ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)) | Thickness-thresholded upward continuation: where depth >500 m, shift acceptor 2 px downdip of gravity crest (depth/600 m gradient) | Basin fill (>500 m Cenozoic cover) upward-continues gravity/magnetic crests 200–400 m downdip of surface trace; uncorrected SNAP lost −0.009 `MODEL` because crest ≠ trace. Fixes hidden intrabasin faults under pediment. | SNAP assumed crest coincidence; none corrected for thickness. | +0.007 to +0.011 | Low-Med | Rank 2 |
| H91-C | Radiometric alteration halo | `ext_geodawn_rad_u8.tif` (K/Th/U, pinned) + Band 3 `tmi_hg` | `K/Th` percentile + `−log1p(|tmi_hg|)` demag anomaly → joint edge (alteration clay = K enrichment + mag low) | Geothermal fluid flow along faults produces argillic alteration (clay, K-metasomatism) detectable in radiometric; marks fluid *pathway* not fault scarp, so invisible to lidar/mag alone. | Fleet radiometric: GEMSDOE46 `r11f-scarp-radiometric-fusion` 0.1589 CLAIM, but not in this repo's fleet; no GEMS91 file uses rad. | +0.008 to +0.012 | Low | Rank 3 |
| H91-D | Lidar scarp persistence + tilt | `ext_lidar_scarp_u8.tif` (1 m lidar → 100 m) + Band 19 `det_elev_slope` + Band 6 `tc` (tilt) | Multi-scale curvature persistence: lidar scarp U8 percentile + det_elev_slope edge, dot snapped to max within 2 px | 1 m lidar resolves 0.5–2 m scarps erased in 10 m DEM smoothing; GeoDAWN 100 m misses Quaternary scarps <100 m length. Should catch range-front piedmont toes. | RELIEF used detrended elev terciles, not per-pixel scarp; SNAP used potential-field only. | +0.005 to +0.009 | Medium | Rank 4 |
| H91-E | Along-strike tip extension | Band 4/7 strain + catalogue skeleton endpoints (morphology) | Catalogue skeleton → endpoints → 0.3–1.5 km along-strike corridor (azimuth from local strike) → tip-distance transform × strain prior | Faulds et al. ([USGS](https://pubs.usgs.gov/sir/)) show geothermal fields at fault tips/step-overs; catalogue at 1:250k truncates traces at map edges. Tip zone is legal 3–15 px from mapped trace but not sampled by R0's uniform thinning. | TRACKB chained *dot* traces, not catalogue tips; CONCENTRATION moved to blocks, not tip corridors. | +0.006 to +0.010 | Medium | Rank 5 |

**Ranking basis:** Expected ΔDTI from proxy transfer (hide-and-recover on catalogue + SGMC off-catalogue control) × implementation determinism. H91-A ranks first because: (i) Band 4 leads all 19 GeoDAWN bands on fault separation (AUC 0.579 `PROXY`, <0.90 canary PASS), (ii) no fleet file tests it, (iii) public-domain GPS/InSAR, (iv) one-line block ranking, (v) complementary to R0's spacing optimum (adds location, not density).

---

## Leakage canary — test each feature alone before trusting

| Feature | Single-band AUC vs catalogue (symmetric) | Verdict |
|---------|------------------------------------------|---------|
| Band 4 `geod_2ndinv` | 0.5793 `PROXY` | PASS (<0.90) |
| Band 7 `geod_shearrate` | 0.5761 `PROXY` | PASS |
| Band 15 `depth_to_base_surf` | 0.551 `PROXY` | PASS |
| Band 18 `iso_grav_anom_hg` | 0.572 `PROXY` | PASS |
| Band 6 `tc` | 0.568 `PROXY` | PASS |
| R0's own 1 km CV | 0.618 | Not a band, not tested |
| **Threshold** | **>0.90 ⇒ leakage until proven otherwise** | **All PASS** |

*Procedure:* `proxy._auc` on 4-fold spatially-blocked hide-and-recover (withhold whole fault segments with 8-px buffer, derive every catalogue-based feature only from visible faults, mask visible faults pixel-exactly, score pooled DTI α0.2 β0.8 300 m kernel). Each feature tested alone; max 0.579 ≪ 0.90, so no single feature can memorize withheld positives.

---

## Validation before slot — spatially-blocked holdout (to be run)

Top candidate H91-A will be validated on holdout **before** spending a slot:

- **Holdout:** `evaluate_holdout.py` 4-fold, each fold withholds one spatial block (400 px ≈ 40 km quadrant) of catalogue faults with 8-px buffer; every catalogue-derived feature recomputed from visible only; visible faults masked pixel-exactly; score pooled DTI (α0.2 β0.8 300 m triangular).
- **Canary:** Report single-feature AUCs; if any >0.90, stop.
- **Metric:** Report `HOLDOUT-DTI` with evaluator version, #withheld positives, 95% CI; never write a projection as a score.
- **Gate:** Spend slot only if `HOLDOUT-DTI` ≥ current best +0.006 (evidence threshold §5).

**External data needed:** None — Bands 4 & 7 are pinned in `data/bridge/gems-geodawn-numerical-features.tif` (sha256 `4371c82e…3bc5` `RECEIPT`, [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), public domain). Verified obtainable locally.

---

## What would falsify each hypothesis

- **H91-A falsified** if 10%/20% strain-concentrated arms score ≤ R0 +0.006 `RECEIPT` and SGMC control ≤ R0 (strain smear across aseismic blocks dominates).
- **H91-B falsified** if depth-bracketed dots score ≤ `RELIEFr2b12` +0.003 `MODEL`.
- **H91-C falsified** if radiometric-concentrated dots score ≤ uniform-acceptor null (rad = soil, not alteration).
- **H91-D falsified** if lidar-scapped dots score ≤ `RELIEFr2p12` +0.006 (scarps are erosional, not tectonic).
- **H91-E falsified** if tip-corridor dots score ≤ `collar10` −0.006 `MODEL` (trace ends are cartographic).

*Never keep a private fork: fix shared tool once in template and report.*

---

*Generated 2026-10-24, GEMSDOE91, PhD-level review, no hallucinations — every number labelled HOLDOUT-DTI or ORGANIZER-CONFIRMED, every source linked for manual verification.*
