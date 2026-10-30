# Current checkout review — 2026-10-30

## Decision

**Negative / blocked. No TIFF was generated in this review; no file is approved to download as a competition submission or to submit.** This is an intentional fail-closed outcome, not a claim that no historical research rasters exist.

The current branch is `arena/f36b3e21-gemsdoe91`. The method paragraph that is supposed to define this parallel session's lane is absent from the supplied prompt. `registry/experiment_plan.json` independently records `lane: null`; therefore this review did not select a candidate or run an experiment. The three-experiment / two-hour limits are ceilings, not authorization to invent a lane.

## Evidence checked

- `python scripts/restore_data.py --check` returned exit 1 and reported **15/15 pinned inputs missing** (including official sample template, existing-faults mask, training feature stack and comparison/auxiliary rasters). There is no `data/` directory in this checkout. Inputs cannot be validated, masked, or compared against this checkout's official grid.
- The pinned-lattice uniqueness calculation in the historical S27-OSDR run card is explicitly only a **geometric capacity bound**, not a score or uniqueness pass: at the recorded 37,654-dot budget, the bound is 82.34% overlap, greater than the protocol's 70% stop threshold. That historical card also states `assigned_lane: false`, `complete_organizer_registry: false`, `ok_to_submit: false`. It is not evidence for a new candidate in this checkout.
- `pytest -q` using the repository-pinned environment: **899 passed, 10 skipped**. (Pytest summary reported 909 collected tests.) This validates the current code suite, not missing data, external organizer acceptance, a leaderboard score, or any historical experiment's scientific validity.
- No organizer receipt is present for a new submission; no organizer-confirmed score can be stated. User-supplied score claims, including GEMSDOE32's 0.2778, remain **USER-REPORTED** here. They must not be called an estimated/confirmed score without reproducible matched holdout evidence or an organizer receipt.

## Nine-site decision table

The site-specific historical numbers supplied in the prompt can be summarized, but they are not fresh evaluations, are not verified receipts in this checkout, and several are related/near-duplicate lineages. The supplied best values are listed as **USER-REPORTED**, not as estimates of a new file's leaderboard score. The reproducible audit and executive table already in the repository is [`docs/executive-summary.html`](executive-summary.html) and the deeper review is [`docs/review-93888f32-20261028.md`](review-93888f32-20261028.md).

| Site | Best value provided in prompt | Evidence class here | Unique/new file cleared? |
|---|---:|---|---|
| GEMSDOE24 | 0.2477 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE25 | 0.2600 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE27 | 0.2449 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE28 | 0.2710 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE30 | 0.2600 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE31 | 0.2708 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE32 | 0.2778 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE33 | 0.2632 | USER-REPORTED | No — historical only; no current registry/input verification |
| GEMSDOE36 | 0.2750 | USER-REPORTED | No — historical only; no current registry/input verification |

**Best historical claim in this set:** GEMSDOE32, 0.2778 (USER-REPORTED). It is not evidence that a new candidate will exceed 0.2778; the leaderboard figure 0.3195 / 0.4413 in the prompt is also a time-sensitive user claim, not verified in this review. Do not extrapolate from model outputs or holdout DTI to leaderboard DTI.

## Candidate hypotheses for a future authorized lane (not run)

These are hypotheses to preregister only after the coordinator assigns a lane and the full feature cache is restored. The highest-ranked hypothesis below has **not** been validated and is not proposed as viable yet.

| Rank | Hypothesis and layers | Target signature / why it may recover uncatalogued structure | Difference from implemented work; mimic | Cost / blocker |
|---:|---|---|---|---|
| 1 | Two-sided texture change-point on B12 detrended elevation, with B19 slope used only to orient/check candidate traces | Persistent contrast in radial texture across a subdued linear zone can flag a damaged or juxtaposed belt without requiring a high-amplitude scarp. | Prior methods include slope, Hessian, ridge and granulometry features; repo review found no explicit radial-spectrum change-point receipt. Mimics: lithologic boundary, fan/playa edge, vegetation boundary. | Moderate CPU; cached stack missing. **Must test feature-alone leakage canaries and buffered holdout before any emission.** |
| 2 | Seismicity lineation orientation/anisotropy (authorized seismicity layer, band semantics to be verified) corroborated with B13 gravity curvature/edge | A spatially coherent event lineation plus independent potential-field boundary may reveal a blind fault absent from mapped-fault labels. | Related seismicity features have appeared in prior models; distinct test is explicit lineation/anisotropy plus independent corroboration. Mimics: volcanic swarm and monitoring-density artifact. | Low–moderate; exact layer semantics and holdout masking require verified metadata. |
| 3 | Scarp aspect/normal conditioned by regional slope direction using official LiDAR/DEM-derived inputs | Orientation-conditioned scarps may suppress terraces and geomorphic edges while retaining fault-block morphology. | Related lidar scarp fusion exists; this isolates aspect/opposition as an ablation, not a novel sensor family. Mimics: terrace risers, shorelines, road cuts. | Low compute only if official derivative identity, license and inputs are verified; not verified here. |
| 4 | Fault-normal high-resolution channel-offset/knickpoint transects from USGS 3DEP DEM and derived channels | Repeated aligned channel deflections could indicate young or eroded faults with weak continuous scarps. | Distinct from coarse-stack drainage covariates: test repeated transect-level same-sense offsets. Mimics: fan avulsion, lithologic knickpoints, roads/ditches. | High data/I/O. Free official source lead: [USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services). Specific study-area tile availability was **not checked**, so not yet viable. |

No numeric expected DTI improvement is asserted. Holdout DTI is not a leaderboard-score projection. The official competition problem page and reference code are linked below for manual source review; this session did not fetch non-allowlisted sites.

## Required next steps (fail-closed)

1. Obtain a coordinator-assigned method paragraph and resolve the registry/lattice conflict without excluding references or relaxing thresholds.
2. Restore authorized official sample, fault mask, cached feature stack and full registry artifacts, verify hashes, CRS, transform, masks, provenance and band metadata.
3. Use the shared holdout/evaluator/writer only. Withhold entire fault segments plus buffer; build catalogue-derived features only from visible faults; mask visible faults pixel-exactly. Run each feature-alone leakage canary first; stop if AUC exceeds 0.90 unless leakage is disproven.
4. Keep within three experiments/two hours. Compare paired pooled DTI with alpha 0.2, beta 0.8, 300 m triangular kernel, report evaluator version, withheld-positive count and 95% CI. Surface correlation and final-dot overlap must both be computed against every available registry raster; stop on rho >0.90 or >70% within 3 px.
5. Only after beating the matched holdout best and clearing automated format/uniqueness gates may a separate selector consider a real weekly slot. The selector step is not performed here.
6. On an approved file, verify no NaN inside footprint, values [0,1], CRS/shape/transform match, and preserve file hash plus organizer receipt. Do not say “OK to submit” before that evidence exists.

## Official references

- [DrivenData GEMS problem description and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [Organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP products/services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)

## Run card

```json
{
  "hypothesis": "No assigned-lane experiment; future ranked candidate is a two-sided B12 texture change-point, untested.",
  "mechanism": "Persistent cross-lineament radial-texture discontinuity could reveal subdued fault damage or juxtaposition not captured by scarp-only detectors.",
  "named_non_fault_mimic": "Lithologic contact or alluvial-fan/playa boundary.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_evaluator_version": null,
  "withheld_positives": null,
  "holdout_status": "NOT RUN: lane not assigned and inputs missing",
  "correlation_overlap_vs_registry": "NOT RUN for a new surface/final dots; historical S27 card records literal lattice stop bound 0.8234 at 37,654-dot budget, not a clearance.",
  "raster_sha256": null,
  "validator_output": "NOT RUN: no new raster; official sample grid missing. Must verify no NaN in footprint, values [0,1], and exact CRS/shape/transform before release.",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
