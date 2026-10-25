# Repository review — active branch `arena/bb16b6ae-gemsdoe91` (2026-10-25)

## Verdict

**Negative for promotion; no new TIFF was generated in this review.** The checkout contains the historical S15-HCPA GeoTIFF below, which is a distinct artifact and is technically suitable for **research download only**. It is **not approved to submit**. Creating a new raster by editing or re-encoding that prior artifact would violate the uniqueness requirement and would not amount to a scientifically evaluated candidate.

The required source rasters and cached features are absent from this checkout. `python scripts/preflight.py` reports `BUILD BLOCKED`; it cannot reproduce the candidate, run a new holdout, or compare against a complete registry. No weekly submission slot was used. This is an intentional stop, not a claim that the requested new submission has been generated in this turn.

## The supplied S15 lane and the competition objective

The lane paragraph recorded in `docs/run-card-S15.json` is S15-HCPA: combine conductivity plume features, basement/gravity concordance, thermal springs, kinematic dilation/slip, radiometric alteration and microtopographic features, then emit a sparse, far-field-biased DTI raster. We stayed within that lane; the three-experiment budget for that historical run is already consumed.

The official competition description says the prediction target is **geological faults indicative of geothermal resources**, not geothermal vents directly. The test set is described as expert-labeled faults missing from the existing public USGS database. Accordingly, a conductivity, spring or alteration anomaly is a *fault-discovery proxy*, not a vent label or proof of a geothermal system. [Official problem description and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

## Why the reported 0.2778 is plausible—and what is not proven

The official DTI definition is `TPw / (TPw + 0.2 FPw + 0.8 FNw)`, with a linear triangular distance kernel of 300 m support (3 pixels at the stated 100 m resolution). Per-truth-pixel credit is a maximum over nearby predictions, so adding a second prediction that supplies no higher kernel-weighted credit can increase false-positive mass without increasing true-positive credit. This makes sparse, spatially efficient emission a plausible explanation for why a thinned raster can outperform a dense one.

That is a **metric-based mechanism, not a demonstrated causal explanation for the site-reported 0.2778**. More importantly, the fetched GEMSDOE32 page identifies the same named artifact as `UNSCORED` and explicitly says **“NO ORGANISER SCORE EXISTS”** for its artifacts; its nearby 0.2747 is explicitly called a projection/model, not a score. The supplied 0.2778 claim therefore conflicts with the project's own currently published evidence and has no submission-page receipt in this checkout. The candidate lineage and before/after comparison are also not a controlled experiment changing only dot density. We cannot determine from these sources whether 0.2778 came from an old stale result, local proxy, or misattribution. We do not claim that thinning caused it or that S15 will beat it. The official public leaderboard page fetched in this review displays 0.4413 at rank 1; that leaderboard snapshot is not a copied receipt for our submission. The prompt's 0.3195 value is not the current rank-1 value on the fetched page. Only a copied submission-page receipt is ORGANIZER-CONFIRMED under this project's run-card convention.

## Historical candidate audit (not a new build)

- Artifact: [`gems91-s15-hcpa-e3-20261025T030000Z-7f01c717-zeros.tif`](downloads/gems91-s15-hcpa-e3-20261025T030000Z-7f01c717-zeros.tif) and [single-TIFF ZIP](downloads/gems91-s15-hcpa-e3-20261025T030000Z-7f01c717-zeros.zip).
- Name: `gems91-s15-hcpa-e3-20261025T030000Z-7f01c717`.
- SHA-256 (recomputed from bytes): `b7ab738f8e0311db9a481a4f16f5bc30583855537b3083144080d7b88157fb1a`.
- On-disk checks re-run in this review: one band; float32; shape 3730×3292; EPSG:32611; transform `(100, 0, 243350, 0, -100, 4508550)`; nodata tag absent; 12,279,160 finite values; zero NaN/Inf; minimum 0; maximum 1; 37,654 positive pixels. The ZIP passed integrity check and contains exactly one TIFF. Exact-byte SHA-256 duplicate search across `docs/downloads/*.tif` found none.
- Since every cell is finite, there can be no NaN inside the footprint. The current checkout does not contain `data/official/sample_submission.tif`; therefore the reference-pixel footprint and official transform comparison could not be re-run against the sample raster. Metadata matches the recorded grid in the candidate audit card and the official page's EPSG/resolution requirements.
- The file is suitable to **download for research**, not automatically safe to submit: format checks do not establish scientific performance, data-use eligibility, completeness of novelty checks, or organizer acceptance.

### Historical holdout and a material validation mismatch

`evidence/s15_run_card.json` records these historical results as HOLDOUT-DTI, evaluator `gems91-hide-recover-v1.0`, 60,988 withheld positives:

- E1: 0.055484; 95% CI [0.041258, 0.064337].
- E2: 0.091399; 95% CI [0.083166, 0.099501].
- E3 budget sweep: 30,000 dots 0.080066 [0.072873, 0.089213]; 37,654 dots 0.091399 [0.083166, 0.099501]; 44,000 dots 0.100218 [0.089696, 0.108654].

These are historical run-card numbers, **not re-run in this review**. The selected final-map emitter in `scripts/run_s15_lane.py` uses `emit_capped_quota()` to impose a far-field/halo quota, while `emit_and_score()` uses a different unconstrained greedy selector for the holdout sweep. Therefore the 0.091399 result does **not** validate the exact final 37,654-dot emission policy. That mismatch must be fixed in the shared runner and the exact policy scored on blocked folds before any future promotion. The historical score is also well below the run card's own comparable prior holdout baseline of 0.206406, and below later site-reported S14 results; it fails the promotion bar irrespective of the mismatch. In this review, the shared S15 runner was corrected to apply the same far-field/halo quota policy in holdout folds and final-map emission, to refill unused halo allocation from far-field, and to reject legacy score caches without a matching selector/evaluator/schema fingerprint. **The historical score above predates that correction and remains unvalidated under the corrected policy; no new holdout score is claimed.**

The run card reports pre-placement maximum absolute Spearman correlation 0.06501 and final directed overlap 0.30650 against 8 canonical rasters; its in-repository sibling comparison reports 0.40596 against 15 rasters. Those numbers are historical and scoped to these listed files. They do **not** demonstrate uniqueness against every public GEMSDOE site or every registry raster named in the user request. The run card's `complete_universal_registry: true` overstates what the 8-raster check establishes; treat complete-registry uniqueness as **unverified** until the registry is enumerated and checked.

A further terminology correction: the frozen S15 method paragraph calls the selection “exact,” but the implementation calls `PTHA._lazy_greedy_submodular_select` with spacing constraints. It is a greedy selection heuristic, not an exact proof of globally optimal DTI placement. The updated run-card mechanism now describes that honestly; the original preregistration was not rewritten post-result.

The historical card also contains selector fields asserting the weekly cap/slot state was verified and that no human intervention was needed. Those assertions cannot be established by the local raster run and must not be treated as a submission-page receipt or selector approval.

## Candidate hypotheses for a future authorized experiment

These are *ablation proposals within S15-HCPA*, not results and not claims that the ideas are unused across all parallel sites. The historical S15 experiments combine the feature families; the repository does not show standalone, feature-family holdout comparisons for these precise contrasts. No candidate is validated here because source data are missing and the lane's three-experiment budget has been consumed.

| Rank | Hypothesis and stack layers | Physical signature and off-catalogue rationale | Difference from implemented S15 features | Named non-fault mimic | Qualitative potential / cost |
|---|---|---|---|---|---|
| 1 | Depth-conditioned conductivity residual × basement/gravity edge alignment. Use conductivity, depth-to-conductive-base, gravity vertical/horizontal gradients. | A localized conductivity residual with a co-oriented buried basement edge may trace a fluid conduit below cover, rather than simply restating an exposed mapped scarp. | Replace raw conductivity ratio/excess and scalar gradient magnitudes with depth-conditioned residuals and an explicit orientation interaction. | Saline basin fill or a lithologic contact. | Highest expected information value within the lane; medium implementation cost. Not a score projection. |
| 2 | Strain-tensor resolved opening/shear at a basement-edge normal. Use geodetic dilatation, shear, second invariant, gravity gradients and basement depth. | A buried fault can concentrate directional strain even where the topographic scarp is muted. | Current S15 resolves strain tendency against LiDAR strike; this proposal resolves the geodetic tensor against a gravity/basement-derived edge normal. | Interpolation artifacts or broad regional strain gradients. | Medium-high qualitative value; medium/high validation cost due to orientation uncertainty. |
| 3 | Signed cross-edge K/Th alteration polarity jointly with magnetic vertical-gradient sign. Use radiometric K and Th plus magnetic vertical gradient. | A narrow alteration boundary or magnetite-destructive zone could mark a concealed conduit away from catalogued traces. | Current S15 uses K/Th magnitude/step and a one-sided magnetic factor; test signed cross-edge polarity and orientation consistency. | Felsic plutons, soil/cover variation, or survey seams. | Medium value; low/medium cost using existing stack. |
| 4 | Springs-to-conductive-corridor cost distance, gated by basement step and strain connectivity. Use the existing well/spring points, conductivity and basement/strain features. | A fluid pathway may connect known thermal manifestations to a concealed fault continuation not in the catalogue. | Current `hcpa_thermal_flux` is an isotropic Euclidean distance decay; this tests anisotropic, geophysically constrained connectivity. | Roads/sample clustering, isolated spring sources, or hydrologic flow not controlled by faults. | Medium value; medium cost; leakage and spatial sampling bias are critical. |
| 5 | Multi-scale detrended-elevation curvature asymmetry × deep structural concordance. Use detrended elevation and slope plus existing scarp/step fields. | Degraded subtle scarps may survive as asymmetric curvature signatures where ordinary slope thresholds fail. | Current S15 includes a LiDAR asymmetry feature, not a tested multiscale curvature-asymmetry interaction with basement structure. | Shorelines, fan margins, and erosional breaks in slope. | Lower/medium value; medium cost and greater geomorphic confounding. |

All five can be computed from the competition feature stack plus sources already named in the historical S15 preregistration; no additional external dataset is proposed. The official overview confirms the competition provides conductivity, depth-to-base, strain, gravity and magnetic layers. The actual local files are absent, so current obtainability in this sandbox is **not verified**; the competition data page is the required source and is described by the project as login-gated. [Competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/).

**Proposed validation order, if a future lane authorizes an experiment:** first test candidate 1 as one pre-registered ablation using the shared cached stack and `scripts/evaluate_holdout.py`; run each constituent feature's leakage canary alone; use whole-segment buffered hide-and-recover; derive catalogue features from visible faults only; mask visible pixels exactly; score pooled DTI with α=0.2, β=0.8 and 300 m kernel; compute spatial 95% CI. Reuse the *same far-field/halo quota selector* on validation folds and final map. Stop after three experiments/two hours, and do not select a weekly slot unless it beats the strongest comparable holdout, passes complete-registry surface and final-dot uniqueness, and all technical checks. This review did not execute that plan.

## Checks, passes, and source review

1. **Pass 1 — repository review:** read README, current S15 preregistration/card, runner, writer/validator, historical status page and data preflight. Identified missing current inputs, stale branch attribution, candidate/holdout emission mismatch and overbroad novelty/selector claims.
2. **Pass 2 — implementation and artifact review:** corrected `scripts/run_s15_lane.py` so holdout and final emission share the same far-field/halo policy, any unused halo quota is refilled from far-field, stale scoring caches are rejected, and automated code no longer fabricates selector/slot approval or universal-registry completeness. Added a focused runner test. Independently re-read the historical TIFF and ZIP and recomputed hash, ranges, cell counts, metadata, member count and exact-byte duplicates. `python scripts/preflight.py` still reports BUILD BLOCKED due missing inputs.
3. **Pass 3 — regression review:** `.venv/bin/pytest -o addopts='' --disable-warnings` → **387 passed, 8 skipped**. The skips are data-dependent integration checks because pinned inputs are absent. No new scientific holdout or final raster was generated; tests verify code behavior, not scientific performance or complete-registry uniqueness.

Official sources reviewed:

- [DrivenData problem description, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — specifies fault prediction, incomplete labels, 300 m triangular kernel, α/β, EPSG:32611, 100 m, float32 [0,1], one layer, and null/NaN outside bounds.
- [DrivenData data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — fetched during review and redirected to the DrivenData login page; this confirms the data tab is not anonymously accessible here. The required local files are also absent.
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — baseline code and instructions say to obtain challenge data from the competition site.
- [EPSG:32611](https://epsg.io/32611) — CRS reference.
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) and [INGENIOUS](https://gbcge.org/current-projects/ingenious/) — source programs linked by the competition overview.
- [GEMSDOE32 site](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html) — explicitly labels the named `h33-...-zeros.tif` candidate UNSCORED and says no organizer score exists; it labels its 0.2747 value a projection/model. The prompt's 0.2778 cannot be reconciled from the page and needs a receipt to substantiate.
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — fetched on 2026-10-25; displayed rank 1 at 0.4413. This is a public-leaderboard snapshot, not a submission receipt for this project's raster.

## Required remediation

1. Restore authorized official input rasters under `data/`, verify hashes/provenance, and run preflight.
2. **Implemented in this branch:** the S15 blocked-fold selector now shares the far-field/halo policy with final emission, fills unused halo allowance from far-field, invalidates old selector/evaluator caches, and has a unit test. Remaining: restore inputs and rerun the preregistered candidate under a valid lane/budget; no new score is yet available.
3. Replace `complete_universal_registry` with precise checked-scope metadata; enumerate available fleet rasters and rerun both surface and directed dot overlap checks. Missing sites mean uniqueness is not proven.
4. Remove automated assertions about weekly slot availability, selector approval and human eligibility. Only a real selector decision and copied organizer receipt can establish them.
5. Re-render the site from validated source cards. Keep the existing TIF available only with the research-only status; do not use it for a submission slot.

## Review run card

```json
{
  "hypothesis": "Historical S15-HCPA HCPA/kinematic multiphysics surface; no new hypothesis was run in this review.",
  "mechanism": "Historical model combined conductivity, basement/gravity, thermal spring, strain, radiometric and scarp features; final candidate used 37,654 sparse unit dots and far-field/halo quotas.",
  "named_non_fault_process": "Saline basin fill and lithologic contacts can mimic conductive or basement-edge signatures.",
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": "gems91-hide-recover-v1.0",
    "withheld_positives": 60988,
    "value": 0.091399,
    "ci95": [0.083166, 0.099501],
    "evidence_status": "historical S15 run-card value; not rerun in this review; final emission geometry differs from the scored holdout selector"
  },
  "correlation_overlap_vs_registry": {
    "historical_scope_only": true,
    "canonical_rasters_checked": 8,
    "surface_max_abs_spearman": 0.06501,
    "final_candidate_directed_overlap_within_3px": 0.3065,
    "in_repo_sibling_rasters_checked": 15,
    "sibling_max_directed_overlap_within_3px": 0.40596,
    "complete_public_registry_verified": false
  },
  "raster_sha256": "b7ab738f8e0311db9a481a4f16f5bc30583855537b3083144080d7b88157fb1a",
  "validator_output": {
    "validation_scope": "re-read of historical TIFF bytes; sample raster absent from this checkout",
    "single_band_float32": true,
    "no_nan_inside_footprint": true,
    "all_cells_finite": true,
    "values_in_0_1": true,
    "crs": "EPSG:32611",
    "shape": [3730, 3292],
    "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
    "matches_recorded_grid": true,
    "sample_reference_available": false,
    "matches_sample_raster_rerun": null,
    "zip_single_tiff_integrity": true
  },
  "submission_name": "gems91-s15-hcpa-e3-20261025T030000Z-7f01c717",
  "submission_note": "S15-HCPA research only; final emission not holdout-matched; do not submit.",
  "new_tif_generated_in_review": false,
  "ok_to_download": "YES — existing historical file, research only",
  "ok_to_submit": "NO",
  "verdict": "negative"
}
```
