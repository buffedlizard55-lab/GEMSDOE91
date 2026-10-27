# S24-CCKM — preregistration (written before experimental results)

Date: 2026-10-27. Branch: `arena/61b1192a-gemsdoe91`.

## Lane status (honest statement)

The supplied prompt says "Your lane is the single method paragraph below" but contains
**no single method paragraph**, and `registry/experiment_plan.json` has `lane: null`
(verified in this checkout). The same prompt also instructs: generate 3–5 new candidate
hypotheses, rank them, and validate the top candidate on the spatially blocked holdout
before touching a submission slot. This session therefore runs the **rank-1 hypothesis
from the already-merged 2026-10-27 shortlist**
([`docs/review-8e8d86f2/HYPOTHESES.md`](../review-8e8d86f2/HYPOTHESES.md)) as a
**self-assigned narrow lane**. That is not a claimed coordinator assignment, and it is
recorded as an irregularity. No weekly submission slot is used; promotion remains a
separate selector step (protocol rule 6).

## The single method (this session's lane)

**CCKM — cross-contact kurtosis of magnetic texture across a gravity contact.**
Use only cached bands **B14 `tmi`** (total magnetic intensity) and **B13
`iso_grav_anom`** (isostatic gravity anomaly) of the SHA-pinned
`training_features` raster (`4371c82e…`, restored and re-hashed this session).
A fault can juxtapose magnetically different basement across a density contact
beneath sedimentary cover, where no scarp was mapped. The targeted signature is a
**change in the tail-weight (excess kurtosis, 4th central moment) of high-pass
magnetic texture sampled on opposite sides of the local gravity-gradient normal**,
gated by gravity-gradient strength so the contrast is measured *at* a contact:
`surface = sqrt(rank(|K(+9px) − K(−9px)|) · rank(|∇B13|))`, where `K` is the masked
15-px-window excess kurtosis of the B14 residual after a masked σ=4 px Gaussian
background removal. No catalogue-derived feature, no supervised fit, no prior
raster values are used. The catalogue is used only for the >3.05 px emission collar
and for pixel-exact evaluation masking.

**Named non-fault mimics:** unfaulted intrusive/volcanic contacts, lava-flow
margins, GeoDAWN survey seams / flight-line levelling steps, and lithologic
texture changes without displacement. A fault prediction is not evidence of a
geothermal vent, permeability, temperature, or a productive reservoir.

## Ranked hypotheses (qualitative; not score forecasts)

Searched `src/` + `scripts/` for `kurtosis|fourth moment|granulometry|phase lag|
cross-spectral|baffle|geod_2ndinv` on 2026-10-27 before ranking (hits recorded in
the session review). "Not tried" means the exact combination was not found
implemented in the inspected repository; sibling/private work is not excluded.

| Rank | Layers → signature | Why it could catch a catalogue-missing fault | Difference from inspected implementation | Expected benefit / cost; data gate |
|---|---|---|---|---|
| 1 | **B14 + B13 → cross-contact magnetic kurtosis contrast** (above) | Buried juxtaposition changes magnetic texture statistics across a gravity contact even with no surface scarp | S22-OMTJ used a 3rd-moment (skewness) *within-window* edge on compromised inputs; S19 used 2nd-moment semivariograms. A paired 4th-moment contrast across a gravity normal is not implemented | Uncertain-highest among low-cost options / ~20 min CPU. No new data |
| 2 | B12 `det_elev` + B19 `det_elev_slope` → oriented morphological-granulometry spectra compared across a persistent slope break | Different fan/elevation fabric across a subdued or buried piedmont scarp | Existing slope/curvature/ridge/drainage features do not compute paired orientation-dependent opening spectra | Uncertain / ~30 min. No new data |
| 3 | B13 + B14 → direction-resolved local cross-spectral phase slope (lag in px) as a standalone field | An offset density–magnetisation contact at depth can show coherent cross-band lag with weak relief | `cwpc17` computes cross-wavelet coherence-type features *inside an ensemble*; a standalone lag field as the primary surface was not found. Adjacent work exists → ranked below 1–2 | Uncertain / ~40 min. No new data |
| 4 | B16/B10 earthquake intensity/distance + B13 curvature → anisotropic seismicity lineation corroborated by gravity curvature | Microseismic alignment can trace a blind structure before geomorphic expression | B10/B16 appear as ensemble inputs, not as a primary anisotropic lineation detector gated by B13 curvature | Low–uncertain / ~20 min. No new data; catalogue-adjacent seismicity location bias is a leakage concern to canary |
| 5 | External USGS 3DEP 1 m DEM → scarp curvature / openness (data-gated) | Metre-scale scarps invisible at 100 m could reveal unmapped traces | Repo DEM work uses the 100 m cached bands | **Not viable yet**: local 3DEP tile coverage/quality over the footprint was not verified from the official source in this checkout ([USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services), free/unrestricted in general). Named here only with its gate; do not run until tiles are pinned |

## Band-identity and missing-data policy (label-blind, checked before features)

Embedded descriptions are claims, not proof (S23's B06 "tilt" conflicted with a
radiometric mirror). For B13/B14 this runner first records internal consistency
checks that do not use labels: `B03 ≈ 2·|∇px B14|` and `B05 ≈ |∇B13|`,
`B18 ≈ ∂x B13` correlations. Passing supports — does not externally authenticate —
the embedded identities. Declared NoData is `-3.4028234663852886e+38`; 3,061
in-footprint cells per band carry it (re-counted, matching
`docs/review-8e8d86f2/feature-audit.json`). **Sentinels are excluded, never
filled**: all filtering uses masked (valid-only) normalised convolution; windows
with <80% valid pixels produce no support and can receive no dot. This repairs
the S22 failure mode (sentinel read as a value) without S23's unvalidated
nearest-neighbour imputation.

## Frozen experiment E1 (1 of max 3; no tuning after results)

- Constants: residual σ=4 px; kurtosis window 15 px; valid-support ≥80%;
  kurtosis clip [−2, 30] then `log1p(K+2)`; offset ±9 px along the B13 gradient
  unit normal (σ=3 px masked smoothing); surface as above, in [0,1], 0 outside support.
- Arms (one experiment, paired): `cckm_e1` (candidate), `control_gravgrad`
  (`rank|∇B13|` alone), `control_kurtcontrast` (`rank|K+−K−|` alone).
  `r0_reference_nonmatched_budget` (the pinned GEMSDOE32 R0 raster, 37,654 dots)
  is scored as an external reference only — its budget differs, so it is not a
  matched control and no paired claim is made against it.
- Holdout: shared `vendor/gems57/spatial.folds` (fixed label-blind quadrants,
  whole 8-connected components, 80 px training buffer) with shared
  `vendor/gems57/evaluate_holdout.py` pooled DTI (α=0.2, β=0.8, 300 m triangular),
  `pooled_summary` with 1,000 paired spatial-block bootstrap draws, seed 520810.
  Every number is labelled HOLDOUT-DTI with evaluator version, withheld-positive
  count and 95% CI. Per-fold emission is restricted to the fold quadrant with
  budget proportional to quadrant footprint area (total 20,000), so holdout dot
  density matches the final full-grid density — this differs from S23, which
  emitted whole-grid per fold; S23/S22 numbers are context, not paired controls.
- Emission: shared `gems91.pdwc21.emit_dots_nms`, spacing 3.05 px, catalogue
  collar >3.05 px (visible faults per fold; full catalogue for the final raster).
  Budget 20,000 because at 37,654 the literal registry rule is mathematically
  impossible against the pinned 206,895-dot lattice (≥82.34% forced overlap;
  largest capacity-feasible budget 22,163 — `experiment-preflight.json`).
- Leakage canary (rule 4): every input/derived feature and the surface, alone,
  per fold (all withheld positives + every 4th negative). Symmetric AUC >0.90
  is a hard stop. A pass does not prove absence of leakage.
- Uniqueness (rule 1), two phases, no exemptions in the data: (a) surface
  full-footprint Spearman |ρ| ≤0.90 via `gems91.novelty.SurfaceProbe` before
  placement — breach stops emission; (b) final dots ≤70% within 3 px via
  `gems91.novelty.dot_check`. References: the 62/64 restorable frozen registry
  rasters plus pre-existing `docs/downloads/*.tif`, pinned by SHA before the run.
  Reported in three scopes: the **nine focus leaders** (GEMSDOE24/25/27/28/30/31/32/33/36,
  identified by the SHAs in `docs/s22/nine-site-audit.json`), all restored
  references, and the **dense lattice pair separately** (its 3-px dilation covers
  all but 6,649 footprint pixels, so it is a near-universal blocker by geometry;
  it is reported, never deleted from the receipt).
- Packaging: shared `vendor/gems57.submission_writer.write_submission`
  (all-finite float32, values in [0,1], EPSG:32611, 3730×3292, pinned transform,
  zero outside footprint, zero on catalogue) + one-TIFF ZIP; then independent
  re-read validation. No silent clipping/repair anywhere.
- Verdict `promote` requires ALL of: canary pass; surface pass vs every restored
  reference; dot-overlap pass vs every restored reference **including the lattice**;
  candidate beats the best matched control with paired 95% CI excluding 0;
  validator pass. Anything else is `negative` — a deliverable, not a failure of
  process. Even a `promote` is not "submit it": a separate selector must still
  check the live weekly cap on the authenticated submission page.
- No leaderboard score is estimated. The repo's own calibration check found the
  hide-and-recover instrument is not a validated live-score proxy, and no
  authenticated receipt exists; a projection written as a score would be a
  hallucination. `estimated_leaderboard_score` stays `null` with the reason recorded.
