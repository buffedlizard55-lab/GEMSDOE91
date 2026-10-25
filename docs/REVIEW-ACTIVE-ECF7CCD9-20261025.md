# Active-branch repository review — `arena/ecf7ccd9-gemsdoe91` — 2026-10-25

> **VERDICT: NEGATIVE / BLOCKED. No experiment, no new score, no TIFF, and no weekly slot used.** The required single-method lane is not present in the prompt or `registry/experiment_plan.json`; required local competition inputs and the cached feature stack are absent. The only advertised TIFF is a prior OLC91 research artifact. **OK TO DOWNLOAD: YES — prior research artifact only. OK TO SUBMIT: NO.** No file was copied or renamed as a new submission.
>
> [Machine-readable run card](run-card-ecf7ccd9.json) · [Existing download guide](executive-summary.html) · [Earlier current review and candidate menu](REVIEW-19912231-20261025.md) · [standing brief in README](../README.md#full-project-brief)

## Executive finding

The repository is an unusually extensive, auditable research project: shared hide-and-recover evaluators, writers, registry/format gates, experiment preregistrations, a static download portal, 626 passing tests, and explicit negative outcomes are present. It is **not runnable as a fresh experiment in this checkout**. `data/official/sample_submission.tif`, the named GEMSDOE32 parent raster, and `data/bridge/gems-geodawn-numerical-features.tif` are absent. The anonymized competition-data URL resolves to DrivenData's login page. The prompt's single assigned method paragraph is absent, and the experiment plan explicitly records `lane: null`.

Therefore the requested fresh candidate cannot honestly be generated or approved here. Generating a hand-made, synthetic, copied, renamed, or registry-evading TIFF would violate the scientific and submission gates rather than satisfy the request. **There is no new file to download or submit.** The site's prior OLC91 file remains clearly research-only; its format validity does not constitute a competition submission recommendation.

## Current-source checks and score reconciliation

The following are separate evidence classes and must not be conflated:

- **PUBLIC-LEADERBOARD (live page fetched 2026-10-25): 0.4413**, rank 1 on the official DrivenData public leaderboard. This is a public-test score, not a local holdout measurement and not an organizer receipt for a file in this repository. [Official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- **0.3195** appears in the GEMSDOE32 site's historical leaderboard transcription dated 2026-10-04 as the then-reported rank 2. It is not the current official leader in the fetched page; treat it as a historical snapshot, not a current score. [GEMSDOE32 page](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html).
- **0.2778** was supplied in the prompt as the h33 artifact's score, but the GEMSDOE32 page explicitly states that no organizer score exists for its artifacts. Its page presents owner-run holdout/proxy and generative-model projections and gives distinct values for different artifacts; none is an organizer receipt. Thus **0.2778 is USER-REPORTED / UNVERIFIED here, not ORGANIZER-CONFIRMED**. Do not infer that it is an official public-leaderboard score.
- `ORGANIZER-CONFIRMED: null` for this checkout: no submission-page receipt was available or supplied.

### What may explain the supplied 0.2778 claim—without pretending to prove it

A sparse, thinned prediction can improve a distance-weighted Tversky score if it removes redundant mass while preserving enough distance-weighted coverage of target traces. GEMSDOE32 documents a sequence involving ridge-surface emission, dot thinning, and pruning near the known catalogue; it describes this as an emission-budget / spacing effect. That is a plausible metric mechanism, not proof that one specific edit caused an organizer score, not evidence of unseen-fault discovery, and not a validated recipe for exceeding today's leaderboard. The site's own later model comparisons are simulations based on an owner-derived truth prior, while its hide-and-recover uses visible catalogue faults as proxy truth. Neither can authenticate a hidden-set score or show that genuinely unmapped faults will be recovered. The public leaderboard score is also not evidence that the h33 file obtained that value.

The official problem statement says newly identified expert-labeled faults make up the initial test set; submissions are later reviewed by experts and rescored against an expanded label set for the final prize round. Consequently, mapped-fault holdout DTI is a useful development diagnostic but not an unbiased proof of hidden-fault performance or geothermal-system discovery. [Official problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

## Ranked hypotheses requested (proposals only; none implemented or evaluated)

Expected DTI improvement is **unknown**. The ordinal ranking below is a qualitative priority for information-per-effort, not a projected score. The earlier review documents the repository search, mimics, and source checks in more detail. These do not satisfy the missing lane assignment.

| Rank | Candidate; layers and signature | Why it could find a catalogue-missing fault | Difference from this repository; main mimic | Conditional cost / expectation |
|---|---|---|---|---|
| 1 | **Topographic texture / spectral-slope break:** 100 m detrended-elevation band B12, with B19 detrended-elevation-slope as a control; calculate a frozen multiscale local radial power-spectrum slope on both sides of an independent candidate line. | Fracturing or differential erosion can alter surface roughness where fault relief is weak; only applicable where a shallow fault affects surface processes. | A roughness/spectral statistic rather than another gradient, ridge, curvature, or structure-tensor score. Main mimics: lithologic contrasts, playa/alluvial-fan margins, lava-flow edges. A related hypothesis is already in the written backlog; do not call it globally novel. | Existing feature stack would make implementation relatively low-to-medium cost; cache is absent. **Best first diagnostic priority**, but gain unknown and leakage/uniqueness must be tested. |
| 2 | **Within-map-unit potential-field residual displacement:** RTP magnetics B02, isostatic gravity B13, basement depth B15; compare signed cross-boundary residual displacement only within map-unit interiors using official USGS SGMC unit polygons. | A concealed basement offset internal to a generalized unit may alter magnetic/gravity fields without a mapped surface fault or unit boundary. | Not global cross-field centroid displacement: unit-conditioned residuals with unit-boundary exclusion. Related ideas already exist in CED91/XG91 backlog, so this is a refinement rather than established novelty. Main mimics: intrusive contact/facies changes and survey seams. | Medium-to-high cost: official SGMC page/GIS resource is identified in the previous source register, but bytes, clipping and schema were not fetched in this checkout. Not viable until license/provenance and availability are checked. |
| 3 | **Seasonal Landsat thermal residuals:** USGS Landsat Collection 2 Level-2 surface-temperature scenes, conditioned on season, terrain, land cover and emissivity; require repeated narrow thermal residuals aligned with independently supported structures. | Fault-controlled shallow circulation may produce repeatable heat/moisture anomalies over an unmapped permeable structure. Many deep or inactive faults will not express a detectable surface anomaly. | New sensor/time-series family relative to the cached GEMS feature stack and existing geothermometry features. Main mimics: irrigation, vegetation, playas, moisture, emissivity, aspect and acquisition artifacts. | High cost and high uncertainty. USGS product documentation is identified, but exact suitable scenes/coverage/cloud conditions have not been queried; it is not validated as obtainable for this footprint yet. |

Official source links for review: [competition overview](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem/method and data description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [login-gated data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS 2026 SGMC](https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous), [USGS Landsat Level-2](https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products), [EPSG:32611](https://epsg.io/32611).

## Three-pass implementation/review record

### Pass 1 — inspect and check inputs

- Confirmed current branch `arena/ecf7ccd9-gemsdoe91`, clean starting worktree, and inherited HEAD `3a06228`.
- Read the README standing brief, latest prior review, plan, source register, shared evaluator/writer entry points, current portal pointer, and data manifest.
- Checked actual local paths: sample submission, GEMSDOE32 parent raster, and 19-band training-feature cache are missing. `python scripts/preflight.py` returned **BUILD BLOCKED: 0/2**; it was a read-only finding after restoring its generated tracked JSON to its original content.
- `python generate_submission.py --preflight` returned **BLOCKED**, with no assigned method and missing pinned sample; no candidate was generated. The anonymous official data URL resolves to the DrivenData login page.
- Fetched the current public leaderboard, official problem page, official reference-solution repository, and GEMSDOE32 page. The leaderboard currently displays 0.4413 at rank 1; GEMSDOE32 says no organizer score exists for its artifacts. These facts supersede neither private scores nor receipts.

### Pass 2 — protocol, science, and delivery review

- The required single-method paragraph was not supplied. No lane can be inferred from the many prior methods, the candidate menu, or the current score claims.
- The experiment plan has zero experiments and zero recorded minutes, but the runtime enforcer does not prove real elapsed time. No experiment was attempted; no holdout metric, feature canary, pre-placement correlation, or final-dot uniqueness check was fabricated.
- Existing registry capacity witness cannot be freshly verified without the pinned sample raster; its archived value is not counted as a new measurement here.
- Checked `docs/current-run.json`: it intentionally points to the previous OLC91 research-only artifact. Its submission flag is false. The portal's file can be downloaded for research, but no current-branch TIFF exists.
- The shared hide-and-recover specification remains the correct method when a permitted experiment is assigned: whole-segment buffered withholding, visible-fault-only catalogue-derived features, exact visible-fault masking, shared pooled DTI (`alpha=0.2`, `beta=0.8`, 300 m triangular kernel), per-feature leakage canary, and both phases of registry checks. No private evaluator/writer was made.

### Pass 3 — regression and final integrity

- Created an isolated `.venv` and installed the exact pinned `requirements.txt` versions; no dependency pin was changed.
- `PYTHONPATH=.:src .venv/bin/python -m pytest -o addopts='' -q`: **626 passed, 8 skipped, 87 warnings** (first run 33.93 s; repeated after the documentation edits with the same 626/8 result). The warnings are Rasterio affine `PendingDeprecationWarning`s. Skips are data-dependent; see test output with `-rs` for details.
- `python -m compileall -q scripts src tools tests`: PASS.
- `scripts/verify_front_door.py`: exit 0. `scripts/check_artifact_policy.py`: PASS, 87 explicitly registered prediction artifacts and no raw raster/archive tracked.
- `scripts/verify_current_artifact.py --with-data`: BLOCKED because the sample raster is absent; it did not silently pass format validation.
- Repository-level artifact identity tests and front-door verification do not replace sample-backed validation, a new experiment, or a submission receipt.

## Remaining blockers, next actions, and limitations

1. Assign the exact single method paragraph and its source; until then, do not run any candidate.
2. Place permitted official competition data in `data/` from an authenticated source. The data tab is login-gated. Never infer permission or data availability from sibling repository mirrors.
3. Restore and verify the cached feature stack and complete registry using pinned hashes; record rights and provenance for external sources.
4. Run the selected feature's standalone canary first. Symmetric AUC >0.90 is leakage until explained. Check surface `|Spearman| <=0.90` before placement and final-dot <=70% within 3 px after placement against each registered raster.
5. Run at most three experiments or two hours using the shared evaluator/writer. Promote only if the pre-registered candidate beats the comparable holdout best with uncertainty reported. Keep the weekly selector/slot choice separate.
6. Only then write a fresh sample-grid TIFF, independently reopen and validate no NaN inside footprint, values in `[0,1]`, and exact CRS/shape/transform. Add unique filename and <=140-character note. Report download permission separately from submission permission.
7. Record any actual competition score only from a submission-page receipt as `ORGANIZER-CONFIRMED`. Public leaderboard snapshots are a separate `PUBLIC-LEADERBOARD` evidence class; do not mislabel them as local HOLDOUT-DTI or file receipts.

**Limitations:** this sandbox has no DrivenData authentication, competition rasters, current organizer receipt, or weekly-slot state. Public web pages and an owner-controlled project page cannot reveal the private test labels. No method can be claimed to beat 0.2778 or 0.3195 based on this review. The current official public leader is 0.4413, but it is a leaderboard value rather than local validation evidence.

## Required run card

See [`run-card-ecf7ccd9.json`](run-card-ecf7ccd9.json). It records a negative no-run result with null score, registry comparison, raster hash and validator fields because no new candidate exists.
