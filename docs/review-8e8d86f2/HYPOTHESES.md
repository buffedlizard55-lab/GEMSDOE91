# Preregistered research shortlist — 2026-10-27

**No method was assigned in the supplied parallel-run prompt.** The prompt says
“the single method paragraph below,” but does not contain one. These are
ranked proposals, not an assignment, results, or permission to bypass the
existing experiment preflight. No geological experiment has been run in this
review. Each proposal is a distinct exact combination not found as an
implementation in the inspected repository; prior proposals, parallel work,
and private work may overlap. Qualitative rank expresses judgment, **not a
numerical score forecast**.

| Rank / expected benefit, cost | Specific layers and testable physical signature | Why an unmapped fault might be found; non-fault mimic | Difference from inspected implementation / access |
|---|---|---|---|
| 1 · uncertain, lower cost | Cached B14 total magnetic intensity and B13 isostatic gravity anomaly. Compare the **fourth central moment (local kurtosis) of background-removed magnetic texture on opposite sides of a gravity-normal contact**. | Displacement could place differently textured magnetic rocks adjacent beneath cover where no surface scarp was mapped. Intrusive/volcanic contacts and survey seams can produce the same pattern. | S22 OMTJ implemented a *third* moment edge; S19 used second-moment/semivariogram texture. This paired kurtosis contrast was proposed, not found implemented. Cached bands restored from a team mirror; verify masks, source identity, and rights before use. |
| 2 · uncertain, moderate cost | Cached B12 detrended elevation and B19 detrended-elevation slope. Compare oriented multiscale **morphological-granulometry spectra** on the two sides of a persistent local slope break. | Different sediment-fan texture and elevation fabric across a buried or subdued scarp could expose a missed trace. Paleoshorelines, fan margins and roads are mimics. | Existing slope, curvature, ridge, and drainage features do not establish this specific paired orientation-dependent granulometry test. No new external data; mirror provenance and finite-NoData policy remain blockers. |
| 3 · uncertain, higher cost | Cached B13 gravity and B14 magnetic field. Estimate localized **cross-spectral phase slope/lag**, across wavelengths and directions, only where each band has support. | A buried, offset density–magnetization contact could yield coherent cross-band displacement despite weak surface relief. Unfaulted dipping contacts, varying flight height and flight-line artifacts can mimic it. | Existing PDWC matched waveforms and S22 aligned gradient magnitudes are not this specific local cross-spectrum lag. No new data; verify FFT edge and missing-data effects. |
| 4 · uncertain, very high cost / conditional | USGS 3DEP 1 m bare-earth DEM: identify **simultaneous drainage-direction discontinuity and persistent break-in-slope** across fan surfaces, before aggregation to the competition grid. | Subtle young scarps can be missed by regional catalogues; distributary fans, roads, pluvial shorelines and culverts are mimics. | More specific than existing broad scarp/relief detectors; implementation was not found in inspected sources. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) says products are free without use restrictions, but individual tiles and study-area coverage are **not obtained/verified here**. This option is not yet viable in the restricted bulk-download environment. |

The proposed transforms are hypotheses. [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
identifies acquisition line spacing, varying terrain clearance, and the
relevance of magnetics to subsurface geology; it does not validate the proposed
operators. [USGS Southern Gabbs Valley](https://www.usgs.gov/publications/discovery-a-blind-geothermal-system-southern-gabbs-valley-western-nevada-through)
describes a blind geothermal discovery using multiple independent evidence
sources, not the proof that a magnetic edge is a vent. The competition target
is faults, not direct proof of temperature, fluid flow, permeability, a vent,
or a productive reservoir.

## Frozen promotion requirements for any later assigned run

Before placement, apply a declared input missing-data policy based on raster
masks and run a per-feature leakage canary on spatially blocked holdouts. Use
whole-component hide-and-recover, derive every catalogue feature from visible
faults only, pixel-exactly mask visible faults, use the shared
`vendor/gems57/evaluate_holdout.py` and `submission_writer.py`, and compare to
a **recomputed, same-fold, same-budget incumbent** with paired block bootstrap
uncertainty. Check every available registry raster both before and after dot
placement; any threshold violation means stop. Report missing registry
references and the source/rights uncertainty. Do not infer hidden-leaderboard
performance from the holdout. A separate selector decides any real slot.

The current no-assignment and fixed-budget impossibility gates are recorded in
`experiment-preflight.json`; no parameter, count, or masked subset may be
chosen merely to evade a dense reference. Three experiments and two hours are
upper limits, not a requirement to run when the preflight blocks.
