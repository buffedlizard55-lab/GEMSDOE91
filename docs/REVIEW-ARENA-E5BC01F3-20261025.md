# Repository review — Arena session E5BC01F3 — 2026-10-25

**Outcome: NEGATIVE / BLOCKED. No new TIFF, holdout score, candidate, or competition slot.** This is not a claim of scientific failure: an experiment did not start. [Run card](run-card-ARENA-E5BC01F3-20261025.json) is the authoritative machine-readable result for this session. Existing downloads in the site remain prior research artifacts and are **not** approved for this session's submission.

## Pass 1 — inspect repo and the stated target

- Read the standing brief in [`README.md`](../README.md), current run/experiment plan, existing review, shared evaluation and writer sources under `vendor/gems57/`, registry manifests, candidate hypotheses, download pages, and relevant tests.
- Confirmed this checkout has no local `data/` tree. A fresh `.venv` preflight reports the pinned sample raster missing. The merged `registry/preflight.json` snapshot from another session says `INPUTS AVAILABLE`; it is stale for this checkout and conflicts with the actual filesystem plus fresh preflight. Do not treat that cached snapshot, GitHub copies, or historical branch inputs as present local data.
- The user asks this lane to be the single method paragraph “below,” but the message contains no assigned method paragraph. Existing hypotheses in this repo are proposals/results from other sessions and are not an assignment. Accordingly no method was inferred or run.
- The configured 37,654-dot proposal has a previously documented registry-capacity conflict: a prior branch's pinned witness bounded 3-px overlap at 82.34% for that budget. This is a **GEOMETRIC CAPACITY BOUND, NOT A SCORE, not this session's candidate comparison, and not a complete registry test**. The current checkout cannot freshly recompute it because its referenced data are absent. The literal uniqueness condition therefore remains a blocker, not permission to lower the budget or alter the registry.
- Re-running the entry point before the fix exposed an engineering defect: `python generate_submission.py --preflight` crashed at import time when NumPy was absent, instead of returning machine-readable `BLOCKED` output. The capacity module imported NumPy/SciPy eagerly, and preflight did not catch an import failure.

### Three conditional, repository-novel transform hypotheses

A text search in current `src/`, `scripts/`, and hypothesis docs found no implementation of the named transforms below. This only supports code-level non-implementation in this checkout; it is not proof of conceptual novelty across all GEMSDOE sites. All use already-named competition bands, so no new external dataset is required to test the signal. However, none can be validated until the cached stack is restored, a lane is assigned, and registry feasibility is resolved. No unverified external source is being proposed as viable.

Rank is a qualitative priority, **not a projected score or DTI gain**.

| Rank | Layers and physical signature | Why it might find a missing fault; difference in this repo | Main non-fault mimic | Cost |
|---|---|---|---|---|
| 1 | B02 reduced-to-pole magnetics (`rtp`) and B13 isostatic gravity (`iso_grav_anom`): directional semivariograms on opposite sides of a candidate strike; measure discontinuity in normalized anisotropy/correlation length. | A buried basement displacement could alter spatial covariance without a sharp amplitude edge. Current edge/gradient and CWPC methods use local derivatives or pairwise cross-field phase/coherence, not within-field covariance discontinuities. | Lithologic contact, survey interpolation boundary, or volcanic-flow texture. | Medium; highest qualitative priority. |
| 2 | B02 `rtp` and B13 `iso_grav_anom`: localized third-order wavelet bicoherence/phase closure across scale triads, benchmarked against phase-randomized surrogates. | Could detect multiscale non-Gaussian organization missed by second-order coherence; no third-order phase-closure implementation found in this checkout. The proposed fault connection is explicitly unproven. | Intrusive margin, processing seam, or nonstationary noise. | High; high variance. |
| 3 | B02 `rtp` and B06 total-count radiometrics (`tc`): directional ordinal-pattern entropy contrasts across a putative strike, with amplitude-matched shuffled controls. | Could detect changes in ordered field texture not expressed as large derivatives; unlike amplitude/ratio gating already present, it measures local order-pattern frequencies. | Weathering, alluvial sorting, or acquisition striping. | Medium; weakest geological specificity. |

The bands and their names are recorded in the repo's [`S17-LFTG research synthesis`](GEOTHERMAL_VENT_RESEARCH_S17_LFTG.md) and [`S17-CWPC hypotheses`](HYPOTHESES_S17_CWPC.md). Those files are prior project records, not newly fetched external verification. Official/manual-review links remain in the standing brief and project source pages. Current network policy does not permit fetching the DrivenData, USGS, DOE/NLR, GDR, or other supplied public web hosts in this environment; we therefore do not claim fresh verification of their live contents.

**Required next experiment, only after blockers resolve:** freeze a spatially blocked whole-segment hide-and-recover split and incumbent; derive catalogue features only from visible faults; mask visible faults pixel-exactly; test each feature alone for leakage; score using the unchanged shared evaluator (pooled DTI, alpha 0.2, beta 0.8, 300 m triangular kernel); record withheld count and 95% CI. Compare candidate and incumbent on identical folds and budget. Run literal surface checks before placement and final dot checks afterward. The preplacement rank-correlation threshold is 0.90; final 3-px overlap must not exceed 70%. Stop on either duplicate threshold. Do not send anything to a weekly slot without a separate selector decision.

## Score interpretation: the GEMSDOE32 “0.2778” claim

- `0.2778` and the later `0.3195` in the supplied prompt are user/team-reported values, not an organizer-page receipt in this session. The prompt also gives `0.4413` as a current top value; these numbers are inconsistent in time/scope and the live leaderboard is not accessible here. None is reported as this session's HOLDOUT-DTI.
- A higher score for a sparse/pruned fault raster is mechanically plausible if the competition evaluator rewards spatially distributed coverage around target traces: removing redundant neighboring predictions can reduce false-positive mass while preserving covered neighborhoods. That explanation is a testable metric mechanism, **not** proof that the GEMSDOE32 raster is geologically better or that it caused an organizer score.
- Existing repo review notes describe the GEMSDOE32 page as saying “NO ORGANISER SCORE EXISTS” for its artifact. This session did not fetch that page; its contents and the 0.2778 figure remain **unverified here**. An organizer-confirmed score requires a copied submission-page receipt.
- Thus no evidence here supports a claim that a new method would beat 0.2778, 0.3195, or 0.4413. A fault-probability surface is not a geothermal vent/reservoir detector by itself; it does not establish heat, fluid, permeability, connectivity, or productivity.

## Pass 2 — engineering review and repair

Fixed the preflight import failure without changing the shared evaluator or writer:

1. `src/gems91/capacity.py` now imports NumPy/SciPy inside the actual capacity calculation. Importing the CLI no longer requires numerical packages before it can report readiness.
2. `scripts/experiment_preflight.py` now catches missing dependency imports with other evidence/readiness failures and returns `BLOCKED`, not an uncaught traceback.
3. Added a focused regression test ensuring missing runtime dependencies yield a machine-readable negative result and never authorize a submission.
4. Integrated the newly merged parallel-branch S18 research TIFF into the final portal renderer instead of leaving a hand-edited banner that failed `test_portal_render_is_reproducible`. The renderer checks pinned TIFF/ZIP hashes, one-member ZIP byte identity, one-band float32 metadata, recorded CRS/shape/transform, finite binary [0,1] values and dot count, and rejects any run card that sets `ok_to_submit` or `submission_ready` true. The front door and executive guide label the S18 artifact as research-only with holdout/full-registry checks pending; they do not set a submission-ready flag.

This is a shared project fix; no private evaluator or writer fork was made. It is not a geological experiment and does not relax any gate. The default system Python still lacks NumPy, so its post-fix run produced a machine-readable `BLOCKED` JSON (`capacity.status=UNVERIFIED`, missing NumPy) and exit code 1. A local ignored `.venv` was created from the pinned `requirements.txt`; running there produced a machine-readable `BLOCKED` JSON because `data/official/sample_submission.tif` is absent and no lane assignment is present.

## Pass 3 — requirement audit, state, and remaining work

- **Unique TIFF:** not produced. A synthetic file, renamed prior raster, or output lacking the required input grid/feature evidence would not be an honest competition submission. **OK TO DOWNLOAD: NO new TIFF. OK TO SUBMIT: NO.**
- **Preplacement/final uniqueness:** NOT RUN; there is no candidate. Do not represent the old capacity bound as a measured candidate result.
- **Leakage canaries and HOLDOUT-DTI:** NOT RUN; there is no assigned lane and no experiment. No score or CI is fabricated.
- **Format validator:** NOT RUN for this session; no raster exists. Prior downloads can remain accessible as clearly labeled research artifacts only.
- **No-human-inspection goal:** repository validators/preflight can make structural and evidentiary checks automatic, but cannot substitute for missing lane authorization, authorized data, genuine held-out truth, live organizer receipt, or the separate selector. Automated failure is sufficient to block; passing format alone is not approval.
- **Prompt in README:** this review is linked from the README session-start notice and its current supplied requirements are recorded as a dated addendum. The long repeated results list is retained as user-supplied claims; it is not endorsed as verified scores.
- **Concurrent-main integration (PR #130):** while this PR was open, `main` advanced with an S18-UNIQUE research TIFF from branch `arena/2f1f074c-gemsdoe91`. It is not this session's experiment, lane, or candidate. Independently re-read its TIFF: SHA-256 `af01bc7190ce736d2ea7eb28a6e0b9ccd238dd616f41644ba4d8bc5a4f892bb6`, 257,856 bytes, one float32 band, EPSG:32611, shape 3730×3292, recorded transform `(100, 0, 243350, 0, -100, 4508550)`, nodata null, all values finite within [0,1], 20,000 positive cells. Its ZIP passes `unzip -t` and contains one TIFF. These checks establish file integrity/format properties only. Its own run card marks hide-and-recover HOLDOUT-DTI NOT RUN, canary pending, and full-registry uniqueness pending; therefore **OK TO DOWNLOAD: research only, OK TO SUBMIT: NO**. No claim that it meets this session's lane or full uniqueness requirement is made.

### Next steps

1. Obtain a valid single-method lane assignment in the governing project workflow; do not select one of the proposals ourselves.
2. Make the pinned sample, R0/registry reference set, catalogue, and cached feature stack available locally through the authorized source path, with hashes and eligibility recorded. Do not silently substitute mirrors or example TIFFs for competition inputs.
3. Resolve the registry definition and dense-raster feasibility conflict explicitly before choosing a dot budget. Do not weaken the 70% rule or drop references to force a pass.
4. Install the pinned Python dependencies; re-run the machine-readable preflight and full test suite.
5. Only if preflight is not ruled out: preregister the top candidate against a matched current incumbent; conduct feature-only leakage tests, the exact shared blocked holdout, and both registry phases within the three-experiment/two-hour cap.
6. Verify actual submission-form requirements and weekly cap via authorized competition access; preserve an organizer receipt before labeling a leaderboard value confirmed. A separate selector, not this research run, decides whether to use a slot.
7. Publish only the current verified status in the front door. The 92-page repository feed described by historical reviews is not a live organizer leaderboard or score feed.

## Machine verification status

- Pre-fix default-Python `generate_submission.py --preflight`: uncaught `ModuleNotFoundError: numpy` (defect reproduced).
- Post-fix default-Python preflight: JSON `BLOCKED`, exit 1, missing NumPy recorded under `capacity.error` (fail-closed behavior reproduced).
- Post-fix preflight in `.venv` built from pinned `requirements.txt`: JSON `BLOCKED`, exit 1, missing pinned `data/official/sample_submission.tif`; assignment is also absent.
- Focused tests: `tests/test_experiment_preflight.py tests/test_entrypoint_safety.py` passed (34 tests).
- Full suite: **627 passed, 8 skipped, 87 rasterio pending-deprecation warnings** (`.venv/bin/python -m pytest -o addopts='' -q`). Skips are not scientific results; no geological experiment was executed.
- `git diff --check`: PASS.

Do not treat a skipped test or dependency/data-blocked report as a scientific PASS. The run card records every scientific result field as NOT RUN/null.
