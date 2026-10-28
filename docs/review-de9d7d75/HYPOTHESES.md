# Ranked research shortlist — proposals, not authorized experiments

The supplied parallel-run prompt has no assigned method paragraph. No hypothesis
below was implemented, tested or selected in this review. These exact composite
tests were not established as completed runs in the inspected S22–S25 receipts;
this is **not** a verified claim of novelty across all parallel sessions. Reserve
and deduplicate a lane before implementation. Qualitative expected utility is
scientific judgment, not an estimated score. Expected DTI improvement is unknown.

| Priority / expected utility / cost | Layers and precise proposed transform | Why an uncatalogued fault might respond; named mimic | Difference from inspected prior work and feasibility |
|---|---|---|---|
| 1 / uncertain, potentially useful / moderate | Cached B13 gravity and B14 magnetic intensity: fit *translated signed cross-contact profiles*, requiring a common lateral offset to explain multiple parallel transects; compare against a lithologic-contact null with independent offsets. | A buried displacement boundary may be coherent across adjacent transects despite no mapped surface scarp. An unfaulted dipping intrusive contact can mimic it. | S22 third-moment and S24 kurtosis contrast detect distribution changes; S25-FABRIC phase-lag and S19 waveform methods overlap conceptually. The proposed repeated-profile shared-offset **null comparison**, not generic profile matching, is the untested distinction. Needs restored pinned feature stack; no new external data. |
| 2 / uncertain / moderate | B12 detrended elevation and B19 slope: pair opposite-facing breaks across a narrow trough; test consistent trough width across scale and reject single edges. | A small graben could be missed in regional mapping where individual scarps are discontinuous. An erosional valley or road cutting is the mimic. | S25-TLF weights single lineaments; S25-FABRIC uses granulometry. This is an explicit paired trough-geometry likelihood ratio, not a new claim that all paired-scarp detection is novel. Cached feature stack needed. |
| 3 / uncertain, precision-oriented / low–moderate | B12/B19 topography plus B13/B14: a **constant-elevation contour-alignment veto**, retaining lineaments only when their cross-field evidence exceeds matched contour segments in the same local relief class. | Remove paleoshoreline edges while retaining covered structures with independent potential-field support; thus fewer false positives rather than a promise of new recall. Volcanic contacts and real shoreline-coincident faults can mimic or be wrongly vetoed. | Prior topographic lanes list shoreline mimics but their inspected receipts do not report this explicit relief-matched contour null. Not permission to choose a veto after looking at scored truth. No new external data. |
| 4 / uncertain, high variance / high | B13/B14: compare polarity-consistent termination of one magnetic texture domain across a gravity edge against *phase-randomized local surrogates* preserving each band's power spectrum. | A buried truncation could lack a mapped surface expression; primary depositional contacts and acquisition seams can also truncate textures. | Goes beyond S24 moments and S25 phase-lag by testing a directional truncation statistic against a spatial-spectrum-preserving null. Related to existing texture lanes; exact novelty not certified. Existing stack sufficient but costly, with edge/missing-data artifacts requiring tests. |

## Frozen test requirements if a method is later assigned

1. Restore cached feature stack, mask finite NoData values and verify band identity
   and source rights. Do not download or reconstruct a private replacement stack.
2. Use shared `vendor/gems57/evaluate_holdout.py`, buffered v3 folds, whole-segment
   hiding, visible-only catalogue features and pixel-exact visible masks. Test each
   feature alone; AUC above 0.90 is leakage until resolved.
3. Freeze a genuinely comparable incumbent before testing. Use pooled HOLDOUT-DTI
   (alpha 0.2, beta 0.8, 300 m triangular kernel), withheld-positive count,
   evaluator hash/version and paired spatial-block 95% CI. No claim of improvement
   without a matched win. Never replace the incumbent with random dots to pass.
4. Check the **pre-placement** surface and final dots against every unchanged
   registry entry. Use tie-correct midranks on a declared common footprint. Any
   threshold breach stops the run; missing entries block clearance. Do not exempt
   a lattice or tune dots to avoid the registry.
5. Shared writer, fresh on-disk template/footprint/catalogue validator, unique
   descriptive name and at most 140-character note; maximum three experiments or
   two hours. Separate selector only after all gates, never automatic upload.

## Data and official references

No proposal above depends on unverified new external data. None is presently
executable with this checkout's missing feature cache and registry. Additional
USGS 3DEP 1 m DEM or Quaternary Faults data remain **conditional**, not viable new
inputs verified here: direct USGS hosts are blocked by this environment.

- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution): fetched via GitHub API in this review; README and commit receipt archived under `evidence/review-de9d7d75/`. It supports CPU-only execution; a GPU is not an absolute prerequisite.
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and): official acquisition context, not fetched today; not proof of these hypotheses.
- [USGS 3DEP](https://www.usgs.gov/3d-elevation-program): official potential source, study-area tiles not verified obtainable today.
- [Competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): manual-review link, not fetched today.

A fault-prediction raster is not evidence of geothermal fluid, temperature,
permeability or an economically productive reservoir. Geological mechanisms above
are falsifiable hypotheses, not source-verified discoveries.
