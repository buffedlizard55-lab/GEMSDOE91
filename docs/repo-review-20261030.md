# GEMSDOE91 repository review — 2026-10-30

## Executive verdict

**No TIFF is approved to submit, and this checkout did not generate a new TIFF.** This is a deliberate fail-closed result, not a missing implementation claim. The experiment plan contains `lane: null`; competition-grid inputs and the pinned reference parent are unavailable in this workspace. Running a method without the lane paragraph would violate the supplied parallel-run protocol. Historical downloadable rasters are marked research-only and must not be treated as approved submissions.

The highest supplied result for the requested nine-site set remains GEMSDOE32 `h33-h33-2-b2: 0.2778`, but the value is **USER-REPORTED**, not bound here to an organizer receipt. The requested numeric leaderboard-score forecast cannot be responsibly produced from that claim or from local diagnostics. Candidate HOLDOUT-DTI is a different evaluation quantity and must not be presented as a DrivenData score.

## Three-pass review

### Pass 1 — repository shape and request coverage

- Nine-site data, the executive summary, submission guide, provenance records, experiment plans, automated raster gates, shared holdout/evaluation components, and substantial unit tests exist.
- Research includes dated hypothesis and source notes. Previous reports cover candidate mechanisms, score interpretation, uniqueness audits, and blockers.
- The user-requested automated gates and no-manual-inspection intent are represented in code/docs; slot promotion is distinct from artifact generation.
- The README front matter had contradictory status banners: an old S27 branch/artifact banner appeared before text stating no current candidate and a null lane. Replaced the front matter with the actual current checkout status and linked the review. Old material is retained but explicitly historical.

### Pass 2 — executable checks and failure modes

Commands run from repository root on this checkout:

| Check | Result | Interpretation |
|---|---|---|
| `python scripts/preflight.py` | **BLOCKED**, exit 1; 0/2 required inputs verified | `data/official/sample_submission.tif` and pinned `data/registry/...parent...tif` are absent; all six listed build axes blocked. |
| `python scripts/verify_front_door.py` | **PASS**, exit 0 | README/site front-door consistency check passes after review update. |
| `.venv/bin/python scripts/verify_current_artifact.py --with-data` | **BLOCKED**, exit 1; `sample_submission.tif` missing | The verifier correctly fails closed before it can certify a candidate. |
| `.venv/bin/python -m pytest -q` | **PASS**, exit 0 | Full suite passed after installing the pinned `requirements.txt` in ignored `.venv`; skips are shown in pytest output. |

`preflight.py` refreshes `registry/preflight.json` as a side effect. Its generated date-only change was reverted; no experiment-plan or evidence state was changed. No competition submissions or slots were used.

### Pass 3 — request-to-repo consistency

- **Unique competition TIFF:** unavailable and not safe to fabricate: lane is unassigned, the competition grid/parent data are absent, and the required data retrieval is authenticated. Current public page correctly says no submission approved.
- **High-score gate:** no live experiment was run; no holdout result or score estimate is asserted for this review. A projected estimate must not be called an organizer score.
- **Uniqueness:** historical research artifacts and the extant registry/peer audits are not evidence that a new file is eligible. Follow the full protocol: pre-placement and final raster comparisons against registry; stop on absolute Spearman correlation >0.90 or >70% dots within 3 px. Do not weaken the rule to force a result.
- **Hypotheses:** previous research reports include candidate hypotheses, sources, and falsification plans. Do not promote one into the current experiment lane until the controlling paragraph/assignment is present and the data and evaluation inputs are verified.
- **No human-dependent validation:** the codebase has automatic format/evidence checks; the user-facing submission page distinguishes local checks from organizer validation. This review does not claim a remote submission-form range error is resolved without a receipt.

## Blockers and recommended next actions

1. Resolve the lane/registry conflict through the session's designated selector/coordinator; do not infer an assignment from a historical README paragraph.
2. On an authorized environment, obtain the official competition data through the organizer's authenticated data page. Place only the required licensed/pinned inputs in ignored `data/`; verify hashes and provenance with the repo's restore/manifest tooling.
3. Install pinned dependencies and run the whole test suite. Then inspect/fix any failures before accessing the evaluator.
4. Reconfirm competition sample CRS, dimensions, affine transform, validity mask and output range with official data. Current preflight absence means these are not independently checked in this workspace.
5. With the shared cached features/evaluator/writer, run a preregistered spatially blocked, buffered whole-fault-segment holdout; test each feature alone for leakage; report pooled DTI with evaluator version, withheld-positive count and 95% CI. Stop at three experiments or two hours.
6. Check uniqueness both before placement and on final dots. Produce the mandated JSON run card including hypothesis, mimic process, holdout result, registry overlap/correlation, raster SHA-256, validator output, name/note, and promote/negative verdict.
7. A separate selector may choose a weekly slot only after the candidate beats the current holdout incumbent and passes all gates. Organizer-confirmed scores require a submission-page receipt.

## Official/manual-review references

- [Competition overview and problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [Competition rules](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Competition data tab (authentication required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official competition leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData reference-solution repository](https://github.com/drivendataorg/gems-prize-reference-solution)
- [DOE GEMS technical report PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDawn data record](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611 definition](https://epsg.io/32611)

These are links for review, not a claim that every referenced page or dataset was re-fetched during this repo inspection. The current session had no DrivenData credentials, and this environment cannot validate organizer acceptance.
