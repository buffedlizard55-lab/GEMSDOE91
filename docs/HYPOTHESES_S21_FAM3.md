# Session 21 — S21-FAM3: hypotheses, lane, and preregistered gates

Branch `arena/11ddffe8-gemsdoe91`. Date 2026-10-26 (user-local).
Written **before** any S21 fit, holdout score, uniqueness check, or GeoTIFF.
Budget (protocol rule 6): at most 3 experiments; 0 weekly submission slots used by this run.

Every number in this session is labelled exactly one of:
`HOLDOUT-DTI` (evaluator version, withheld-positive count, 95% CI) ·
`MODEL / PROJECTION` (fitted to USER-REPORTED scores; never a score) ·
`USER-REPORTED` (copied from the session prompt; not an organizer receipt) ·
`ORGANIZER-CONFIRMED` (none exist in this repo; `null`).

Official facts used (verified 2026-10-26 from DrivenData competition 306, page 967,
https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/):
test truth = expert-mapped faults **not** in the public USGS catalogue; GeoDAWN region is
chunked into public/private test sets; one selected submission is scored in both prize
rounds; metric = distance-weighted Tversky, alpha 0.2 (FP), beta 0.8 (FN), triangular
kernel R = 300 m = 3 px at 100 m; submission = single-band float32 GeoTIFF, EPSG:32611,
values in [0,1]. Reference solution: https://github.com/drivendataorg/gems-prize-reference-solution

## 0. What the nine focus sites prove (all scores USER-REPORTED)

| Site | Best named submission | USER-REPORTED |
|---|---|---:|
| GEMSDOE24 | h25-1-dotted-h19-5-d1-5 | 0.2477 |
| GEMSDOE25 | dotted-h19-5-d2-8 (44,090 dots) | 0.2600 |
| GEMSDOE27 | topo-gap-closure-t-v2-on-d1-5 | 0.2449 |
| GEMSDOE28 | h36-1-rung30-blind-r1 (cluster: 0.2707–0.2710) | 0.2710 |
| GEMSDOE30 | d28-poisson300m-offcat-44090 | 0.2600 |
| GEMSDOE31 | h27-4-solo-d28 (40,199 dots) | 0.2708 |
| GEMSDOE32 | h33-h33-2-b2 zeros (37,654 dots) | 0.2778 |
| GEMSDOE33 | h33d-analog-tip-stepover-r30 | 0.2632 |
| GEMSDOE36 | anderson-geothermal-pinn-38854 | 0.2750 |

Repo forensics already in evidence (`docs/s16/gems32-forensics.json`,
`registry/r0_verification.json`, `docs/run-card-S20-LFI.json`):
the 24/25/27/28/30/31/32 lineage is **one family** — the catalogue-blind h19-5 ridge
network (121,131 support px, 0.1922) progressively **dotted** (d1.5 → 0.2477; d2.8,
44,090 dots → 0.2600), **solo-filtered** (40,199 → 0.2708) and **collar-pruned**
(delete dots ≤2 px from the mapped catalogue, 37,654 → 0.2778, byte-rebuild verified).
GEMSDOE27 gap-closure on the same base *lowered* the score (0.2477 → 0.2449).
GEMSDOE33 (analog tip/stepover geometry) and GEMSDOE36 (Andersonian geothermal PINN)
are the only two **independent families** in the nine; both land far from the catalogue
(hide-v2 HOLDOUT-DTI 0.0864 and 0.0069 in S20 E2) yet score 0.2632 / 0.2750 live.

Why R0 (GEMSDOE32) is fleet-best, mechanistically: with a 3-px max-kernel, dense ridge
pixels after the first earn no extra TP_w (max saturates) but each still pays
FP_w = 1 − own credit; 2.8-px dotting removes that redundancy. Truth pixels are new
faults disjoint from the catalogue, so catalogue-adjacent dots sit in the most
truth-depleted band (S20 LFI fit, MODEL: log-density −0.76 at 200–300 m from catalogue
vs +1.78 beyond 4 km); deleting them trades ~zero TP_w for real FP_w savings.
Both effects are emission geometry, not a better detector — which is why 20+ PU/HGB
detector variants in this repo (live 0.13–0.18 USER-REPORTED family) never beat it.

Instrument fact that constrains every gate below (S20 E2, `docs/lfi/holdout-e2.json`):
on 112 fleet rasters, Spearman(`gems57-pooled-hide-v2` HOLDOUT-DTI, live) = 0.105.
Hide-and-recover withholds *catalogued* pixels; live truth excludes the catalogue.
The two tasks are antagonistic (best hide-v2 files are catalogue-recoverers scoring
0.02–0.16 live). Hide-v2 is therefore reported in full but cannot be the promotion
instrument; gating on it is the documented defect this session must not repeat.
This deviation from "beat the spatially-blocked holdout best" is flagged in
IRREGULARITIES.md (IR-S21-01) with the S20 measurements as evidence.

## 1. Candidate geological hypotheses (ranked by expected DTI gain ÷ cost)

### H1 — Three-family complementarity inversion (TOP; this lane)
- **Layers:** distance to the three independent nine-site family networks
  (h19-5 ridge support; GEMSDOE33 tip-stepover support; GEMSDOE36 Anderson-PINN
  support), distance to mapped catalogue, GeoDAWN stack bands B12 (detrended
  elevation), B15 (depth to basement), B19 (detrended-elevation slope), and the
  **spatial gradient magnitude of B15** derived from the pinned stack.
- **Physical signature:** a buried basin-bounding normal fault offsets basement,
  producing a lateral *step* in depth-to-basement (|∇B15| high) where surface
  topography may show no ridge/scarp; stepover/relay damage zones (33's analog
  model) and optimally-oriented Andersonian failure planes (36's PINN) locate
  structures a topographic ridge detector cannot see.
- **Why catalogue-missing:** USGS/INGENIOUS mapping requires surface expression;
  faults under piedmont/basin fill keep a basement step and a favourable stress
  orientation but lose their scarp — exactly the population expert re-mapping adds.
- **Different from repo work:** |∇B15| and the 33/36 surfaces have been used as
  PU/HGB *features* (live 0.13–0.18 family); they have never been used as
  **aggregate-inversion design factors** weighted by live scores. S20-LFI used a
  10-anchor consensus-vote covariate and B15 *value* terciles; S21 has **no
  consensus covariate**, uses two named family-sensor distances, and adds |∇B15|.
  Weights come only from the exact-DTI inversion of USER-REPORTED live scores,
  never from catalogue labels.
- **Cost:** low–medium (reuse `src/gems91/lfi.py`, `lfi_emit.py`, vendor writer/evaluator).

### H2 — Upward-continuation persistence of potential-field worms
- **Layers:** B02 RTP magnetics, B13 isostatic gravity; multi-altitude horizontal-gradient
  maxima (worms) tracked across upward continuation.
- **Signature:** deep basement faults persist to large continuation heights; surficial
  magnetic noise / flow-top texture dies quickly.
- **Why catalogue-missing:** deep-seated structures under cover have no mapped trace.
- **Different:** fleet tried single-altitude tilt/worm ranking (USER-REPORTED 0.2343–0.2560)
  and this repo used worms as PU features; a persistence-*lifetime* surface as the
  sole emission ranker was not completed in GEMSDOE91. **Cost: medium. Rank 2** —
  expected gain below H1 because its two best fleet relatives already plateau ≤0.2560.

### H3 — Piedmont χ / channel-steepness discontinuity lines
- **Layers:** competition 1 m DEM links (official, login-gated) or USGS 3DEP
  (https://www.usgs.gov/3d-elevation-program/about-3dep-products-services, free/public domain).
- **Signature:** strike-consistent channel deflections and χ-plot slope breaks across a
  concealed range-front structure.
- **Why catalogue-missing:** low-relief piedmont scarps < 1 m are invisible at 100 m.
- **Different:** no χ-based experiment exists in this repo (DRN91 used generic routing).
  **Not viable this session:** sandbox cannot reach 3DEP tile hosts (documented S19/ISO91)
  and DrivenData DEM links need login. Named, not proposed as runnable. **Rank 3.**

### H4 — Third-order wavelet bicoherence of B02 × B13
- **Layers:** B02 RTP + B13 gravity; local bispectral phase coupling with
  phase-randomised surrogates.
- **Signature:** multi-scale damage-zone texture without a single-band edge.
- **Why catalogue-missing:** distributed fracturing around a buried fault.
- **Different:** no bispectral estimator exists in repo (backlog only, S18-UNIQUE).
  **Cost: high, calibration risk high. Rank 4.**

## 2. Lane (single method paragraph)

**S21-FAM3.** Fit E[G_pub(x)] = exp(θ·φ(x)) by the exact-DTI aggregate inversion of
S20 (`src/gems91/lfi.py`, unchanged) to the 112 USER-REPORTED live scores in
`registry/lfi_live_anchors.csv`, where φ = distance-to-catalogue (9 bands),
distance-to-h19-5-ridge (6 bands), distance-to-GEMSDOE33-support (3 bands:
≤1 px, ≤3 px, >3 px), distance-to-GEMSDOE36-support (3 bands), and footprint
terciles of B19, B15, B12 and |∇B15| (Sobel gradient magnitude of the pinned
B15 band, computed label-blind). No consensus covariate, no spatial/chunk factor
(private chunks differ), no catalogue label is ever a training target.
Emit binary dots by the shared coverage-aware greedy maximising expected DTI
(`src/gems91/lfi_emit.py`, unchanged) on the fitted q-map, restricted to the
footprint with catalogue distance > 3.01 px (strict ≥3 px collar — one step
beyond R0's proven >2 px), under hard 65% within-3-px caps against every sparse
binding reference (all 112 anchors + own downloads incl. the S20 candidate +
fleet registry). Write with `vendor/gems57/submission_writer.py` (unchanged)
as all-finite zeros float32 (the encoding that cannot trip the portal's
"Predicted values must be in range [0, 1]" check on NaN).

Non-fault mimic (named, protocol rule 5): **lithologic contacts / intrusive
margins and volcanic flow lobes** also step basement depth and align with
potential-field edges; erosional ridge crests mimic the h19-5 sensor. The
inversion can only down-weight these to the extent live scores penalise them.

## 3. Experiments (max 3)

- **E1 (inversion validity):** aggregate all usable anchors on the S21 design;
  fit ridge 1 and ridge 10; leave-one-site-out RMSE/Spearman/Pearson; per-factor
  leakage canaries are *not* in E1 (they need the holdout, E2).
- **E2 (holdout + canaries):** score candidate dots, R0, and the nine-site bests
  on the unchanged `gems57-pooled-hide-v2` evaluator
  (`vendor/gems57/evaluate_holdout.py` + `spatial.folds`, buffer 80 px);
  pooled HOLDOUT-DTI with paired spatial-cluster bootstrap 95% CIs;
  single-factor AUC canaries vs withheld truth (catalogue-derived factors
  recomputed from visible faults only). Surface (q-map) uniqueness pre-check
  (protocol rule 1, before placement) also belongs to E2.
- **E3 (emission + gates):** final dots, shared writer, vendor validator,
  final-dot uniqueness vs the registry set, paired site-bootstrap projection
  vs R0 in three variants (ridge10 primary, ridge1, ridge1 blinded to all
  nine focus sites' scores).

## 4. Preregistered automated gates (no human inspector)

- **G1 Format:** single band float32, EPSG:32611, 3730×3292, exact transform
  (100, 0, 243350, 0, −100, 4508550), all finite, values in [0,1], no nodata tag,
  0 dots on catalogue, 0 dots outside footprint. Shared writer + vendor validator
  + independent re-read must all pass.
- **G2 Uniqueness (protocol rule 1):** surface **and** final dots.
  Sparse references (≤3× candidate dots): ≤70% of candidate dots within 3 px.
  Dense references: judged by the repo's documented rule (matched-budget dots +
  |Spearman| ≤ 0.90), literal readings always reported. Set = fleet registry +
  112 LFI anchors + all `docs/downloads/*.tif` (incl. S20). Any duplicate → stop.
- **G3 Leakage canary (rule 4):** every φ factor alone: symmetric AUC ≤ 0.90
  against hide-v2 withheld truth.
- **G4 Live projection (the S20 bar, unmoved):** paired Δ(candidate − R0) > 0
  with site-bootstrap 95% lower bound > 0 in ≥2 of 3 variants **and**
  P(Δ > 0) ≥ 0.95 in all 3 (ridge10, ridge1, ridge1-nine-site-blind).
- **G5 Instrument honesty:** hide-v2 HOLDOUT-DTI + CI vs R0 is reported in the
  run card whatever it shows; it does not gate, per §0 evidence. If S21's own
  recomputation contradicted S20 (Spearman ≥ 0.5 on the anchors scored in E2),
  G5 fails closed and hide-v2 would gate — preregistered here so the rule
  cannot be chosen after seeing the candidate's number.

**Verdict mapping (obvious on the site):**
`OK TO DOWNLOAD: YES` iff G1 ∧ G2. `PROMOTE / OK TO SUBMIT: YES` iff all of
G1–G5 pass (selector still owns slot timing within the weekly cap; this run
uses 0 slots and cannot upload — no DrivenData auth in sandbox). Otherwise
`NOT OK TO SUBMIT` with the failed gate named. Negative is a deliverable.

## 4b. Pre-fit forensic addendum (added before E1, after restoring rasters)

`scripts/forensics_s21_nine_sites.py` → `docs/s21/nine-site-forensics.json` proves
§0's "independent families" wording too strong at pixel level, and the lane's
geological reading is corrected here **before any fit** (design and gates unchanged):

- GEMSDOE36 (38,854 dots, 0.2750) is a **strict superset of R0**: R0's 37,654 dots
  plus exactly 1,200 extra dots. Those 1,200 dots coincide with a −0.0028
  USER-REPORTED difference — the fleet's cleanest marginal-dot measurement.
- GEMSDOE33 dots sit 99.7% on h19-5 network pixels (31,614 exact R0 overlaps);
  GEMSDOE30 fallback support is byte-identical to GEMSDOE25 d2.8; GEMSDOE31 solo
  is identical to GEMSDOE28 solo; R0 = solo ∩ {dcat > 2 px} exactly.
- Therefore d33/d36 design factors test **residual emission differences on one
  shared network**, not independent detectors. Expected LOSO gain from them is
  small; the |∇B15| factor and the >3 px collar carry the geological novelty.
  If E1 shows no LOSO improvement over the S20 design's stored numbers, that is
  the preregistered negative-result reading for H1's family-sensor component.

## 5. Data (all SHA-pinned, restored from GitHub mirrors; no new external data)

`registry/data_manifest.json` (sample, catalogue, 19-band stack, R0),
`registry/comparison_inventory.json` (fleet registry incl. h19-5 + GEMSDOE33
fallback), `registry/lfi_anchor_matches.json` (112 anchors by git blob).
GEMSDOE36 support comes from its matched anchor raster. If any pin fails to
restore or hash-verify, the affected experiment stops; nothing is fabricated.
