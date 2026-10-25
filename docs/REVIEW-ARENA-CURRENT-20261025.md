# GEMSDOE91 current review — 2026-10-25

## Decision at a glance

- **Current research download:** [`gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif`](downloads/gems91-s16-pc91-20261025T051716Z-9c6f182a-zeros.tif). Its SHA-256 is `dfee391717d1b89e9e179ec2d0ba00096ec40d5963d841670c2e9a4eea4f9df6`.
- **Automated verdict: OK TO DOWNLOAD — YES, for research; OK TO SUBMIT — NO.** This is a previously generated unique research artifact, surfaced here as the latest candidate; this review did **not** generate another raster or spend a submission slot.
- **Reason:** delivered E1 is `0.123600 HOLDOUT-DTI`, below the comparable `0.262209 HOLDOUT-DTI` prior best on the same evaluator. E3 was stopped before writing after a literal 3-px registry duplicate. Do not upload this TIFF.
- **New experiment this review:** zero. The protocol's exact single-method paragraph/lane is not identified, `data/` is absent, and all three experiments in the prior S16-PC91 run card are already consumed. Rebuilding or privately substituting the shared model/evaluator would violate the requested rules.
- **Slot use:** zero. `ORGANIZER-CONFIRMED: null`.

## Review findings

1. **The public landing page was stale.** `docs/index.html`, `docs/executive-summary.html`, and `docs/current-run.json` pointed at S16-PGRD even though S16-PC91 is later, has its own range-safe TIFF, and is explicitly negative. The PGRD duplicate-stop result is legitimate history, but not the current research candidate. The Pages renderer also rewrote those stale paths on every build. This review changes the renderer to rebuild the S16-PC91 audit and route public entry points to it.
2. **The S16-PC91 executive summary could be read as an upload instruction despite saying “do not submit.”** It gave a competition upload workflow and claimed a live `0.4413` high without an organizer receipt. The guide now says not to upload this negative and labels the reported `0.2778`, `0.3195`, and `0.4413` as conflicting, unverified claims.
3. **“Unique” was too broad.** The delivered E1 candidate passed the recorded uniqueness gate against 33 pinned registry rasters, not a complete universe of private or unlinked files. The audit now states the tested scope. Its run card still reports E3 as a duplicate, and that stop remains binding for E3.
4. **No local competition data.** `data/` has zero files. Therefore the current checkout cannot re-run training, holdout, cached-stack feature extraction, full input/grid comparison, or a fresh catalogue-distance check. Prior run-card receipts are explicitly distinguished from fresh file-byte checks.
5. **The historical “top score” is not a verified target.** The user-supplied `0.2778` for GEMSDOE32 and prompt values `0.3195` and `0.4413` are not organizer receipts in this checkout. The file-level audit supports an emission/sparsification explanation, not a causal claim about the score or a geothermal discovery claim.

## What the reported 0.2778 might mean — and what it does not establish

The plausible mechanism is the competition's saturating, spatially weighted DTI combined with sparse unit-mass emission. Once a prediction has supplied most of the local credit to a truth pixel under a 300 m triangular kernel, nearby additional prediction mass can add little or no credit while still paying false-positive cost. Removing redundant or low-marginal-credit cells—particularly cells close to the known-fault exclusion/catalogue collar if those cells do not score—can increase DTI without improving the underlying geological ranking surface. The repo's forensic note also records that the R0 dot set is a pruned subset of its 40,199-dot base, not a new independent detector.

That is a **mechanistic hypothesis**, not a proven cause of a score. A single owner-site value does not identify its evaluator, split, receipt, ablation, or causal edit. A credible attribution would require a matched emission ablation (same surface, labels, evaluation split, evaluator and budget) plus an organizer receipt for the actual score. A high catalogue-recovery DTI is not proof of blind-fault or geothermal-vent discovery. The present results do not demonstrate a route above 0.2778.

## Candidate hypotheses for a future, correctly assigned lane

These are proposals, not measured results. Ranking reflects mechanistic potential relative to implementation cost, not a numeric score forecast. Repository novelty is provisional: the specified operator must be checked against all code and the fleet registry before implementation. None is authorized for this session because the exact lane paragraph is absent and the local data stack is not present.

| Rank | Candidate / input and signature | Why it might find an unmapped fault | Difference from implemented work / named mimic | Improvement potential / cost / input status |
|---|---|---|---|---|
| 1 | **MFTA — multi-scale fault-tip termination asymmetry.** Existing B02 RTP magnetics, B13 isostatic gravity, and B12 DEM; paired line-ridge termination, directional-gradient rotation, and relay-tip topology at roughly 0.5–2 km scales. | Scores endpoint/relay arrangements rather than another continuous ridge centerline; could emphasize an unmapped splay or relay between traces rather than rediscover the mapped fault itself. | Existing H91 code includes tip/stepover continuation and other work includes relays, so novelty is only the explicit multi-scale endpoint-pair topology plus matched tip-pair control. **Mimic:** flight-line seam or lithologic contact creating an apparent ridge ending. | Medium potential; low–medium cost if cached inputs restored. **No new external data needed.** Best next falsifiable test, but not viable until the exact lane is assigned and cached layers/labels are restored. |
| 2 | **SACR — survey-artifact coherence rejection.** GeoDAWN magnetic/radiometric channels; local directional spectral power and cross-channel coherence to identify flightline-periodic striping. | Removes levelling seams that resemble long faults, potentially preserving cross-direction discontinuities that are more geologic. | Seam discussion and cross-physics features exist, but a fold-safe flight-azimuth nuisance model with explicit stripe negative controls is not established by those mentions alone. **Mimic/target confound:** flight-line levelling or gridding seam. | Low–medium potential; medium cost. Sponsor layers suffice in principle; local cache missing. No external source required. |
| 3 | **LCMD — lithology-conditioned magnetic–gravity contact displacement.** B02/B13 gradients plus official geologic-unit polygons; signed inter-field edge offset conditioned within each unit. | A concealed fault may offset physical-property boundaries inside a lithologic domain, whereas an ordinary rock contact is a major false positive for global edge fusion. | CED91 already tests magnetic–gravity centroid displacement; only unit-conditioned displacement with held-out contact controls may be new. **Mimic:** intrusive/stratigraphic contact and map-boundary artefact. | Medium potential; medium–high cost. Requires USGS SGMC polygons. Official record: [USGS ScienceBase SGMC item](https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a). Endpoint/data availability and licence were not checked in this environment; **not viable until obtained and verified**. |
| 4 | **BFT — blind-fault transfer across geomorphic domains.** Existing DEM/geophysical stack, evaluated separately in range-front, piedmont, and basin domains. | Exposes whether the learned signature transfers to buried basin-margin faults instead of being driven by exposed range-front examples. | Changes the validation estimand and domain-shift test rather than adding another ridge detector. Keep the shared whole-segment holdout as a comparable primary result. **Mimic:** lithology/geomorphic domain boundaries correlated with survey coverage. | High diagnostic value, uncertain DTI gain; medium–high cost. No external data in principle; requires an assigned lane and a validated domain-label protocol. |
| 5 | **ODSA — official 1 m DEM scarp-face asymmetry.** Competition 1 m DEM tiles; 10–50 m scarp relief, face asymmetry and slope-break orientation aggregated onto the 100 m grid. | Could recover a subtle surface rupture or geomorphic trace under-resolved by the sponsor's 100 m DEM. | Prior lidar/scarp features exist; it is distinct only if built from provenance-verified 1 m inputs with fold-safe fusion, not another standalone scarp emission. **Mimic:** roads, shorelines, terrace risers. | Potentially high ceiling, high cost. Specific source: login-gated competition `1m_DEM_links.csv` and linked USGS 3DEP data ([USGS 3DEP](https://www.usgs.gov/3d-elevation-program)). The competition bundle and tile availability are not present or verified here; **blocked, not viable now**. |

### Top-candidate validation status

MFTA is the best *next proposal* by cost-adjusted scientific rationale, but it cannot be tested in this checkout: no `data/`, no exact lane paragraph, and no current feature cache. The prior S16-PC91 lane did perform three experiments on the spatially blocked holdout; it is not MFTA and is not a substitute for it. Its result is a negative, so no weekly submission slot was touched. Do not create a new TIFF from MFTA until an authorized, pinned-data experiment beats the comparable current holdout best and passes all gates.

## Current artifact receipts (numbers are typed by evidence class)

- **HOLDOUT-DTI `0.123600`**, evaluator `gems91-hide-recover-v1.0`, **60,988 withheld positives**, 95% CI **[0.114867, 0.133738]**: delivered S16-PC91 E1 artifact; recorded in `docs/run-card-S16PC.json`. The companion v1.1-nohalo record is also labelled HOLDOUT-DTI, same withheld population, `0.123600`, 95% CI `[0.114544, 0.132318]`.
- **HOLDOUT-DTI `0.262209`**, evaluator `gems91-hide-recover-v1.0`, **60,988 withheld positives**, 95% CI **[0.248940, 0.275209]**: comparable prior best S14-HVDC E2 in the same S16-PC91 run card; its receipt status is not organizer-confirmed.
- E2 and E3 values from the preceding PC91 run are experiment diagnostics, not scores for the downloadable E1 TIFF. E3 `0.174120 HOLDOUT-DTI` (same v1.0/60,988; 95% CI `[0.161022, 0.187392]`) was not delivered because final dots had 85.999% directed 3-px overlap with DDVTC. The duplicate stop is retained.
- **Registry uniqueness, recorded scope only:** delivered E1 preplacement max absolute Spearman `0.15005` vs `calib_h194_01894.tif`; final maximum directed dot overlap `0.48215` vs `calib_h161_01855.tif`. The recorded comparison covers **33 pinned rasters**, not every private, inaccessible, or unlinked artifact. E3 is separately a duplicate as above.
- **Fresh TIFF byte check in this review:** SHA-256 as above; 1 band, float32, shape `3730×3292`, EPSG:32611, transform `(100,0,243350,0,-100,4508550)`, all 12,279,160 cells finite, min 0, max 1, 37,654 positive cells, all positive values exactly `1`, no nodata tag. ZIP has one member whose uncompressed bytes match the TIF hash.
- **Grid match limitation:** CRS/shape/transform matched `sample_submission.tif` in the committed PC91 validator receipt. That reference file is absent now, so this review cannot recheck equality. Do not interpret a TIFF byte/range check as a fresh grid-equality certification.
- `ORGANIZER-CONFIRMED: null`; weekly slots used: `0`.

## Three-pass review and verification

### Pass 1 — inspect and implement

Read README standing brief and current run cards, inspected the PC91 feature preregistration, shared holdout/evaluator/writer references, readiness gates, published HTML, Pages workflow, and repository/data layout. Found the stale PGRD landing page and misleading PC91 upload instruction. Implemented a single final Pages routing step to regenerate PC91 pages from its card and expose only the current negative verdict. No model code or shared evaluator was changed.

### Pass 2 — hunt for regressions and incorrect assumptions

Found two further risks during review: the PC91 audit implied global uniqueness from 33 rasters, and its summary repeated the unverified `0.4413` leaderboard value as current. Tightened both scope and wording, removed instruction to upload a negative, and changed current-page labels to explicitly distinguish download permission from submit approval. Added fail-closed routing checks for TIF presence, SHA identity, and `ok_to_download=true` / `ok_to_submit=false`.

### Pass 3 — re-run checks against the request

- `.venv/bin/python -m pytest -q`: **PASS** for the complete suite after the current-page regression tests and renderer integration; previously marked skips remain skipped. Rasterio emitted only its existing `PendingDeprecationWarning`.
- `.venv/bin/python scripts/verify_evidence.py`: **PASS**, arithmetic/provenance/canaries/negative status; zero experiments rerun.
- `.venv/bin/python scripts/check_artifact_policy.py`: **PASS**, 55 prediction artifacts explicitly registered; no raw raster/archive tracked.
- `.venv/bin/python scripts/preflight.py`: **BUILD BLOCKED** as expected, exit 1; `sample_submission` and parent reference are missing, and all build axes lack inputs.
- Re-read PC91 download TIFF with Rasterio: all file values are in `[0,1]`, no NaN/Inf, correct one-band float32 metadata; ZIP member hash matches. Sample grid and catalogue cannot be freshly compared with missing data.
- This turn did not run any geological experiment, did not alter the shared template, did not select or use a slot, and did not generate a new raster.

## Official review links / limitations

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/) · [problem/metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) · [login-gated data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) · [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) · [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) · [USGS SGMC record](https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a) · [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) · [EPSG:32611](https://epsg.io/32611) · [GDR submission 1391](https://gdr.openei.org/submissions/1391)
- Source link presence is verified in repository text; external-page freshness, availability, licensing, and current organizer scores were **not** verified from the restricted environment in this review.

## Run card

See [`run-card-ARENA-CURRENT-20261025.json`](run-card-ARENA-CURRENT-20261025.json). It records a negative result and references the existing research-only TIFF; it does not claim a new experiment or organizer submission.
