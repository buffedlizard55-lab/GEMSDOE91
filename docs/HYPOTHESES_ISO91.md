# ISO91 preregistration: five untried hypotheses, ranked, with one lane chosen

Session `arena/bacc7c26-gemsdoe91` · written **2026-10-25, before any ISO91 experiment ran**
(git history shows this file committed before `docs/iso91/*.json` existed).

Evidence labels used here:

- **HOLDOUT-DTI** (evaluator version, number of withheld positives, 95% CI).
- **USER-REPORTED**: a score the repository owner typed into the brief. These are not organizer receipts.
- **PUBLIC-LEADERBOARD**: read from the official page.

No number in this file is ORGANIZER-CONFIRMED.

## 1. What the evidence already says

| # | Observation | Class / source |
|---|---|---|
| F1 | Dotting the same ridge network raised the score from 0.1922 (121,131 px) to 0.2600 (44,090 dots) | USER-REPORTED, GEMSDOE25/19 |
| F2 | Deleting the 3,891 dots at 1 px from the catalogue gave 0.2708; deleting 2,545 more at √2–2 px gave 0.2778 (R0). Both are consistent with ≈0 credit for those dots | USER-REPORTED, GEMSDOE28/32 |
| F3 | R0 has 69.8% of its dots more than 1 km from the catalogue. Refitted PU models put only 31.5% there, crowding the 300 m–1 km halo | pixel-measured, S17-LFTG review |
| F4 | GEMSDOE91's own PU-HGB lanes scored 0.1823 (S17-LFTG) and 0.1367 (S17-CWPC), far below R0 | USER-REPORTED |
| F5 | In the legacy hide-and-recover split, ~55% of withheld truth lies within 1 km of visible faults | measured, OLC91 |
| F6 | The catalogue has 3,199 8-connected components (median 12 px). 655 of them (13,372 px, 21.9%) have no other component within 5 px (500 m) | measured this session |
| F7 | Descriptive diagnostic: 77% of catalogue pixels lie downslope of the local B19 slope maximum (random pixels: 70%), with a broad −10…0 px offset. The B13 gradient maximum lies a median +2 px down-gravity, also broad | measured this session, full catalogue, descriptive only |

**Reading.** The live truth is new faults that are depleted near the known catalogue (F2, F3). The legacy
holdout instead rewards the halo where its hidden truth lives (F5). That mismatch explains why holdout winners
(PU-HGB) lose live to R0 (F4).

## 2. Hypotheses not yet tried in this repository (ranked)

Expected gain is relative to the incumbent PU-HGB (E0) on a live-aligned holdout. It is a prior judgement, not a score.

| Rank | ID | Layers | Physical signature / transform | Why it should catch faults the USGS/INGENIOUS catalogue misses | How it differs from prior work here | Non-fault mimic | Expected gain | Cost |
|---|---|---|---|---|---|---|---|---|
| **1** | **H1 ISO91: isolation-matched PU learning** | All 19 sponsor bands + 19 gradient magnitudes (the incumbent's 38-feature stack, unchanged, so only the positive set differs) | Learns the joint signature of short, spatially **isolated** faults: subtle B12/B19 steps, local B3/B6 magnetic lineaments, short B18 gravity gradients. It does not learn the high-relief, clustered range-front signature that dominates the catalogue | Mapping completeness falls with fault length and relief, so missing faults are mostly the short, isolated tail of the power-law population. The catalogue's isolated components are the closest labelled analogue of that tail; the clustered range-front systems are already mapped | No lane selected **training positives** by component isolation. CWP91 reweighted the posterior by catalogue density after fitting; OLC91 added strike coherence; S14–S17 added auto-context. The vendor `detached` mode exists only as an evaluation mode | Lake Lahontan shorelines, lithologic contacts, incised drainages, flight-line striping | moderate | low (reuses the E0 pipeline) |
| 2 | H4 cross-modal gradient-vector alignment ridges | B12 det_elev, B13 iso_grav_anom, B15 depth_to_base_surf, B2 rtp | \|cos\| alignment of the four gradient vectors × geometric-mean magnitude, Hessian-ridge NMS, then d2.8 dotting | A range/basin-juxtaposing fault aligns independent physics even where the scarp is eroded or buried | CPAD (phase concordance) and CWPC (cross-wavelet coherence) measured spectral coherence, not gradient-vector alignment, and did not use ridge emission. Partly overlapping | Lithologic contacts without offset | low–moderate | medium |
| 3 | H2 footwall-corrected gravity/basement contact localisation | B13, B18, B15 | Track the maximum horizontal gradient, then shift toward the footwall by a dip-dependent offset (a dipping contact's maximum gradient sits over the hanging wall) | Buried basin-bounding faults have no scarp and appear only in potential fields | Prior lanes used max-gradient or tilt as features (GEMSDOE73 Blakely); none applied a footwall offset | Density contrasts inside basin fill | low (F7: the offset is broad) | low |
| 4 | H3 piedmont-junction (concave slope-break) emission localisation | B12, B19 | Move each emitted dot along steepest descent to the downslope concave break (maximum profile curvature) | Range-front faults are mapped at the mountain–piedmont junction, not mid-slope | SPID91 used toe eigenvalues only as HGB inputs; no lane relocated emitted dots | Fan-head trenching, pediment edges | low (F7: 15% vs 12% within 1 px) | low |
| 5 | H5 external high-resolution scarp morphometry | USGS 3DEP 1 m lidar DEM / 1/3 arc-second (10 m) DEM, aggregated to 100 m | Multi-scale curvature, local relief and openness at 1–10 m | Piedmont scarps under 2 m are invisible in B12/B19 at 100 m | R0's ancestor h19 used 1 m/10 m openness and LRM built off-repo; the in-repo pinned lidar u8 stack is licence-unchecked (IR-91-26) | Roads, canals, terrace risers | high | high (blocked here) |

**H5 source check.** USGS 3DEP is official and free: "All 3DEP products are available, free of charge
and without use restrictions" (<https://www.usgs.gov/3d-elevation-program/about-3dep-products-services>).
It is **not obtainable from this sandbox**: `prd-tnm.s3.amazonaws.com` and `tnmaccess.nationalmap.gov` both
failed the TLS handshake (curl exit 35) on 2026-10-25. It needs an unrestricted machine.

## 3. Chosen lane: H1 ISO91 (single method)

- **Positives.** Visible catalogue components (8-connected) with no other *visible* component within
  5 px (500 m, Euclidean). The isolation test uses only the visible catalogue.
- **Everything else is the incumbent E0, unchanged:**
  - the 38-feature stack from `scripts/run_olc91.build_features`;
  - HGB with the same hyper-parameters;
  - 3:1 negatives drawn from the training domain, excluding the visible catalogue ±3 px;
  - leave-one-quadrant-out training with a 40 px buffer;
  - `submodular_dti_emit`;
  - a budget equal to the area share of 37,654;
  - no dots within 2 px of known faults.
- **Fixed in advance:** `sep_px = 5`. No other parameter is tuned.

### Instruments

All instruments use evaluator `gems57-pooled-hide-v2` and a paired 20 km block bootstrap (1,000 draws, seed 520810).

- **I1 (primary, new): `isolated_component_draw(sep_px=5, buffer_px=3, boundary_px=12)`.**
  - It withholds every catalogue component that is isolated by more than 5 px and lies wholly inside an eroded quadrant.
  - Catalogue features use the visible faults only, and visible faults are masked pixel-exactly.
  - It follows the protocol's hide-and-recover rules: whole segments withheld, with a buffer.
  - It mimics the live property that new faults sit away from known ones (F2, F3).
  - It is added to the template `vendor/gems57/holdout.py` as an option. Existing behaviour is unchanged.
- **I2 (secondary, legacy): `buffered_component_draw(seed=20)`**, with 11,321 withheld positives.
  - This instrument holds the recorded current best: E0 0.085260 HOLDOUT-DTI and CTL 0.085723 HOLDOUT-DTI.
  - E0 must reproduce 0.085260 exactly. That is the infrastructure check.
- **Report-only:** a blind SGMC off-catalogue control (SGMC fault pixels more than 500 m from the catalogue). It is never a gate.

### Arms (same folds, same budget, same collar)

- **E0:** the incumbent (all visible positives).
- **E1:** ISO91.
- **CTL_HALO:** the E0 posterior with no dots within 5 px of visible faults. This controls for I1's construction.
- **CTL_SUB:** E0 trained on randomly drawn visible components with the same pixel count as E1's positives.
  This controls for positive-count effects.
- **RND:** uniform random dots, the floor.

### Gates (all are required for "OK TO SUBMIT: YES")

- **G1.** On I1, E1 − E0 has a paired 95% CI lower bound above 0.
- **G2.** On I1, E1 − CTL_HALO has a paired 95% CI lower bound above 0.
- **G3.** On I1, E1 − CTL_SUB has a point estimate above 0.
- **G4.** On I2, E1 is non-inferior to E0: the paired 95% CI upper bound of E1 − E0 is at least 0.
- **G5.** Leakage canary: every input feature alone has a symmetric AUC of at most 0.90 against I1 truth.
- **G6.** Uniqueness against every restored registry raster:
  - surface \|Spearman\| at most 0.90 before placement;
  - dots \|Spearman\| at most 0.90 after placement;
  - at most 70% of dots within 3 px of any single non-blanket raster's dots;
  - blanket references (3 px coverage of at least 70% of the footprint) are reported both literally and chance-corrected.
- **G7.** Format: single band, float32, EPSG:32611, 3730×3292, identical transform, every cell finite in [0, 1],
  no nodata tag, 0 dots on the catalogue. This is checked by the template validator plus an independent reread.

### Budget

At most three experiments:

1. I1 with all arms.
2. I2 with E0, E1 and RND.
3. The full-catalogue final build with registry checks and the report-only SGMC control.

A failed gate is a deliverable. The run card records it and the website shows **OK TO SUBMIT: NO**.
Slot selection is a separate selector step; this lane never selects or uploads.
