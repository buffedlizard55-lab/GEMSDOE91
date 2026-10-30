# GEMSDOE91 repository review — 30 October 2026

## Executive decision

**No new submission was generated or approved. `OK TO SUBMIT: NO`.** The repository is healthy at the automated-test level, but the requested scientific run is correctly fail-closed: this prompt does not actually identify one assigned method paragraph/lane, and the competition grid inputs needed to validate a new raster are absent from `data/official/`. The frozen experiment preflight therefore ran zero experiments and produced no candidate. Do not upload any archived research TIFF as a substitute.

## Checks performed

- Current branch: `arena/22fcac68-gemsdoe91`; checkout was clean before this review.
- Read the current README, submission-generation entry point, limitations, and prior no-assignment review/shortlist.
- Created an ignored local `.venv` from pinned `requirements.txt` (not tracked).
- Full test suite: **passed** (`pytest -q`; all collected tests passed, with expected skips and Rasterio deprecation warnings).
- Focused entrypoint, front-door, preflight, and current-review tests: **passed**.
- `python generate_submission.py`: existing advertised historical download has technical format checks passing (`single-band float32`, EPSG:32611, expected 3730×3292 grid, finite values in [0,1], byte hash matches card). The program explicitly reports **OK_TO_SUBMIT: NO**, because no technical format check constitutes scientific validation or slot approval.
- `python generate_submission.py --preflight`: **BLOCKED**. No assigned single-method paragraph/source; `data/official/sample_submission.tif` absent, so capacity cannot be verified. Zero experiments; no candidate generated.
- No organizer submission receipt was obtained, no leaderboard estimate was made, no weekly slot was used, and no external-data source was downloaded.

## Findings and risk register

1. **No defensible score estimate.** The prompt's GEMSDOE32 `0.2778` is a user-supplied claim, not a file-bound organizer receipt. The repository explicitly labels it unverified. Do not call a model projection or historical score a future submission estimate.
2. **Historical nine-site leaders are not unique under the specified peer rule.** The latest detailed peer recheck available in-repo reports 97.58–100% directed 3-pixel overlap among these files. GEMSDOE32 is a support-pruned member of a shared family, not independent evidence that pruning caused its score. See [review and nine-file table](review-ad43b4e5/REVIEW.md) and its recheck JSON.
3. **No current candidate passes the submission bar.** The active report describes only research artifacts; some historical TIFFs can pass byte/grid/range validation but fail scientific quality, uniqueness, leakage, or selector requirements. `generate_submission.py` safely refuses to promote a download.
4. **The frozen 37,654-dot plan has a registry conflict.** The prior review computes a conditional minimum 82.341849% overlap against a pinned synthetic lattice witness, above the literal 70% stop. This is not a universal registry-completeness result and must not be evaded by changing the budget or omitting the witness.
5. **Holdout lineage matters.** The prior review records a correction from unbuffered catalogue context to feature-buffered v3 folds. Historical holdout values made with a different instrument are not valid matched comparisons; the S22 feature NoData issue is also documented. Recompute candidate and incumbent using the same approved instrument before any promotion decision.
6. **Submission instructions and public-site status can drift.** Confirm current competition rules, required outside-footprint representation, and quota on the official authenticated competition page before any real submission. Local TIFF validity is not organizer acceptance.

## Geological candidates already preregistered (not run here)

The repository already contains a ranked, literature-grounded shortlist in [`review-8e8d86f2/HYPOTHESES.md`](review-8e8d86f2/HYPOTHESES.md), so this review does not duplicate or silently substitute another lane:

1. Magnetic local-kurtosis texture contrast across gravity-normal contacts (cached B14/B13); lower implementation cost, uncertain gain. Mimics include intrusive contacts and survey seams.
2. Oriented multiscale morphological-granulometry contrast across persistent slope breaks (B12/B19); moderate cost. Mimics include fan texture, shorelines, roads.
3. Local cross-spectral magnetic/gravity phase lag (B13/B14); higher cost. Mimics include dipping contacts, flight-height and line artifacts.
4. 1 m USGS 3DEP joint drainage discontinuity + persistent break-in-slope; high cost and conditional on tile coverage/access. The prior review cites the official USGS 3DEP product page but explicitly says local study-area coverage has not been verified.

These are hypotheses, not expected leaderboard scores. Because the protocol requires a *single assigned lane*, none may be implemented until the assignment is explicit and the preflight has valid inputs and registry-capacity evidence.

## Required unblock sequence

1. Provide the missing explicit single-method paragraph and its assignment source (or have the project selector designate one lane).
2. Restore hash-pinned `sample_submission.tif`, `existing_faults.tif`, feature stack, labels, and associated manifest to `data/official/` using an authorized competition-data path; verify source identity and masks. Current network restrictions prevent fetching from non-allowlisted hosts, and DrivenData data is login-gated.
3. Resolve the frozen budget versus registry-witness collision through a documented coordinator/policy decision, not a local exemption. Establish a complete registry snapshot for both pre-placement surface and final-dot comparisons.
4. Run the selected feature alone through the leakage canary; perform whole-component buffered hide/recover via shared template evaluator/writer; compare pooled DTI to the same-fold incumbent with a 95% interval and report withheld-positive count/evaluator version.
5. Only if the scientific gate beats the current matched holdout best, all uniqueness and format gates pass, and the separate selector approves, publish a named GeoTIFF and concise note. A score estimate must remain explicitly a projection unless copied from an organizer receipt.

## Official references already recorded by the project

- [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login-gated)
- [DrivenData rules/competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
- [USGS GeoDAWN airborne survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [USGS 3DEP products and services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services)
- [USGS Southern Gabbs Valley blind geothermal-system study](https://www.usgs.gov/publications/discovery-a-blind-geothermal-system-southern-gabbs-valley-western-nevada-through)

Links above are references included in the existing project research; this review did not independently retrieve every page during this execution. See the linked prior research records for claim-level source notes.
