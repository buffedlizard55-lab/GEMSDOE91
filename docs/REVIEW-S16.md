# S16 review — measured deliverable, not an invented success

Date: 2026-10-25. Branch: `arena/400a3f1a-gemsdoe91`.
The current result and readiness come from `run-card-S16.json`; archived pages are
not authority for submission permission. Full brief: `SESSION_BRIEF_S16.md` and
the root README. This review explicitly distinguishes implemented requirements
from constraints that could not honestly be satisfied.

## Pass 1 — audit, implementation and measured result

- Restored and SHA-256 checked the real sample, catalogue and 19-band feature
  stack using the existing mirror manifest. The old missing-data note was stale.
- Read pinned official DrivenData reference-notebook bytes and owner GEMSDOE32
  source/geometry. The notebook validates loss weights, not the distance-weighted
  scorer; official web pages and external geological leads were not freshly
  fetched/authenticated in this source audit.
- Refreshed the full 92-repository source feed; a missing page remains explicit.
  Stored supplied result claims separately, never as organizer receipts.
- Registered four ranked hypotheses within one provisional magnetic–gravity
  transfer-residual lane before implementation. The prompt's assigned-method
  paragraph is missing. The top candidate needs no new external data.
- Implemented PGRD from B02/B13, with no catalogue or prior-submission feature.
  Reused cached-feature helpers, deterministic placement, exact registry probes,
  and the unchanged pinned template evaluator/writer. Whole segments hidden;
  fixed, label-blind quadrants; training buffer; visible faults masked exactly.
- One candidate experiment: **0.069397 HOLDOUT-DTI**, 95% CI
  **[0.057510, 0.081676]**, **gems57-pooled-hide-v2**, **60,988 withheld positives**.
  Paired delta against gravity-only control: **−0.004626 HOLDOUT-DTI**,
  95% CI **[−0.010725, +0.001161]**, same version/population. No improvement.
- All 16 candidate-field and one control canaries ran in each of four quadrants.
  Max symmetric feature-alone AUC 0.576053 (not a DTI score).
- Produced a fresh, all-finite TIFF and actual single-TIFF ZIP. No prior
  submission used as a starting raster. On-disk range/grid/spacing checks passed.
- Preplacement attempted 89 indexed references with missing files UNVERIFIED.
  Final dots hit 100% directed overlap with the frozen lattice at reference 27;
  stopped immediately. No further experiment and no competition upload.
- Proved the fixed-budget uniqueness conflict: only 6,649 uncovered footprint
  cells force overlap ≥82.34% for 37,654 binary dots, above the 70% rule.

## Pass 2 — code, evidence and edge-case review

Corrections implemented (engineering checks do not rerun the geological search):

1. **Dangerous synthetic-label overwrite removed.** The old root generator opened
   `data/official/existing_faults.tif` for writing and substituted a mock fault
   before generating smooth noise. It now wraps the real-data run/verification
   path and has no import-time writes. Synthetic fixtures stay under test paths.
2. **Fabricated recovery evidence blocked.** `scripts/recover_geod_light.py`
   contained handwritten/placeholder holdout, registry and projection numbers.
   It now exits without writing. Historical numbers are not validated evidence.
3. **Legacy evaluator default corrected once.** `scripts/evaluate_holdout.py`
   now defaults to no halo deletion; historical v1.0 requires explicit
   `mask_buffer_predictions=True`. Added fail-closed input checks for predictions,
   canaries and missing/wrong-grid registry inputs. The actual S16 experiment
   uses the already-correct pinned `vendor/gems57` implementation unchanged.
4. **Full affine check fixed.** The legacy status-board reader checked only x
   scale and origin, overlooking y scale and rotation. It now checks all six
   coefficients and the no-nodata policy.
5. **Artifact-policy omissions repaired.** Three inherited S15 raster/ZIP files
   were absent from the publication allowlist. They are now hash-registered as
   quarantined research, not approved submissions.
6. **Partial-data test setup fixed.** S15's integration test previously assumed
   all optional layers existed if just the sample TIFF existed. It now skips
   explicitly when any required optional input is absent; unit tests still run.
7. **Current versus historical status disentangled.** Root and `/docs/` now lead
   to one evidence-derived candidate. Archive pages are labelled historical.
   The unsafe DZ-EDGE “submit YES (format only)” claim is revoked. No manual
   image inspection is a validation gate.
8. **Independent replay validation.** Re-read the published TIFF with tifffile
   as well as rasterio; verify the exact ZIP member; replay stored block terms,
   bootstrap, feature canaries and registry accounting without another fit or
   candidate search. A validation PASS is expressly not a promotion.

## Pass 3 — requirement and final-delivery recheck

**Local post-integration result:** 431 tests passed, 2 explicit data-dependent
skips; 30 dependency deprecation warnings. Automated Chromium delivery checks
passed for root redirect, exact TIFF/ZIP download hashes, copy fallback, mobile
layout and accessibility on 17 current/archive pages. No visual approval was
required. All three remote CI jobs also passed ([run 40162592115](https://github.com/buffedlizard55-lab/GEMSDOE91/actions/runs/40162592115)); later publication receipts are recorded on [PR #79](https://github.com/buffedlizard55-lab/GEMSDOE91/pull/79). Independent byte/evidence verification and all 51 artifact-policy
entries passed. Synthetic end-to-end legacy fixture checks also passed; these
are not scientific experiments or performance evidence.

The final check record is maintained in `s16/verification.json` and
`s16/engineering-checks.json`. The latter records tests and browser delivery,
not scientific scores. Source and data verification boundaries are in
`s16/sources.json`; exact code/input identities are in `s16/provenance.json`.

| Requirement | Result |
|---|---|
| New, non-copied TIFF | Generated from B02/B13; byte hash differs from frozen indexed hashes; pixel digest recorded, not a universal final-raster novelty check |
| Genuine protocol uniqueness | **FAILED** — duplicate stop, not renamed or waived |
| Obvious download/submit statuses | Download YES; submit NO at the top of both entry points and executive guide |
| Automated format/score gates | Implemented; no human visual inspection or typed approval flag |
| High-scoring validation before slot | No comparable-best improvement; no slot selected or consumed |
| Whole-segment hide-and-recover | Template fixed quadrants, whole intersecting components hidden, buffer, visible masking only |
| Per-feature leakage tests | Every candidate field and control, all four held-out quadrants |
| Shared evaluator and writer | Reused unchanged pinned template; no private metric fork |
| 3–5 hypotheses before code | Four ranked hypotheses; only rank one tested |
| Stop budget | One candidate, approximately 116 seconds; final duplicate stopped scientific work |
| Source register / full feed | Pinned fetched sources and unfetched official leads labelled; 92-source inventory |
| Exact submission instructions | Executive subpage; current file clearly prohibited from upload |
| Full prompt in README | Full standing version preserved with supplied GEMSDOE89/90 updates; latest-message byte identity not established |
| Organizer-confirmed improvement | **NOT AVAILABLE** — no organizer receipt or account session |
| Unique name and ≤140-char note | Recorded in run card, writer receipt and copy controls |
| Pull request / merge | Recorded in the final response and GitHub PR, after verification |

### Publication boundary

GitHub denied changing Pages from legacy main-root mode to workflow mode
(HTTP 403, Resource not accessible by integration). The committed portal can
still publish through the existing legacy mechanism; scheduled refreshed
source-feed artifacts do not automatically update the live snapshot. This
permission limitation is now explicit on the site and in the README. No live
publication is claimed before a successful deployment receipt.

### Concurrent main integration

Integrated `347ecb4`, the subsequent `911b6a9` DZ-EDGE correction, and
`332d72a` full-grid validator/prerequisite review, and `def38f0` CED91
portal review, plus `1053028` DZ-EDGE builder retirement and `5146eb9` parallel H1 artifacts from main while remaining on the assigned S16 branch.
Preserved the S15 selector/cache/readiness fixes, focused regression test,
corrected historical cards and both dated review records. Regenerated pages
from the combined renderer rather than discarding concurrent source changes.
Preserved the later CED review under a dated archive, avoiding both a second
“current” candidate and its nested-document-shell regression. The CI merge-marker
check now matches an exact seven-equals separator rather than mistaking pytest
log headings for unresolved conflicts.
The other review’s external-page observations remain secondary provenance;
S16 did not independently fetch/authenticate those official pages. The later H1
artifacts are hash-registered as quarantined research, not added to frozen S16
comparisons after its duplicate stop. Its prior landing is preserved as a dated
archive, not silently discarded or presented as an S16 experiment. Its absent-
input state is a dated snapshot, not the current restored S16 data state.

## Findings that must not be concealed

- The S15 card inherited at session start reports a negative paired delta with an entirely positive
  CI. That is internally inconsistent; no fresh paired-best claim is derived
  from it. Some historical cards label different split populations with the same
  evaluator string, which does not establish comparability.
- The advertised GEMSDOE32 ZIP at the pinned snapshot is 216 bytes and contains
  an empty ZIP member rather than a TIFF. Its real TIFF is readable. Its exact
  geometry is a 2 px catalogue-flank prune, not a universal 3 px collar.
- The user-supplied 0.2778 is not authenticated; the pinned source page says
  UNSCORED. Conflicting supplied leaderboard values 0.4413/0.3195 remain
  unverified here. No model projection is a score.
- Max-kernel saturation explains a possible advantage of pruning, not proof of
  why a particular hidden score occurred. A dot can credit multiple truth cells;
  T and M are not identical and redundant dots do not universally cost 0.2.
- The geological hypothesis is non-unique: lithological contacts, remanence and
  survey seams can mimic it. No geothermal vent, reservoir or economic resource
  was discovered or independently verified in this session.
- The experiment is a useful negative, but **does not fully satisfy the requested
  protocol-unique, high-scoring, submission-approved outcome**. Claiming otherwise
  would contradict the measured evidence and the user's stop rule.
