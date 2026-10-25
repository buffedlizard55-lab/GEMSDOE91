# GEMSDOE91 repository review — `arena/bb27ae93-gemsdoe91` — 2026-10-25

## Verdict

**No new experiment or TIFF was produced. OK TO DOWNLOAD: no new file. OK TO SUBMIT: NO.** The current checkout has no `data/` directory, so it lacks the sample-submission raster needed to verify grid alignment, the official catalogue required for masking/collar checks, and the numerical feature stack required for modelling. The preflight also confirms that this request does not specify an assigned single-method lane and exits `BLOCKED`. No prior artifact was copied, renamed, regenerated, or advertised as a new submission. No submission slot was used.

This review makes no organizer-score claim. The user's cited leaderboard values are not authenticated by a submission receipt in this checkout. The prompt's claims about GEMSDOE32's score and the all-time leaderboard cannot establish a current candidate score or a scientific improvement.

## Findings

### Blocking

1. **Missing competition inputs.** `data/` is absent. Running `python generate_submission.py --preflight` reports the sample raster missing at `data/official/sample_submission.tif`; the capacity witness is consequently `UNVERIFIED`. The manifest's historical `local_present` flags do not represent this checkout's current filesystem state. Restore only the SHA-pinned inputs through the repository's approved restore path, then verify hashes before modelling. Never infer TIFF geometry or fill data from memory.
2. **No lane assignment.** `registry/experiment_plan.json` does not supply an assigned method paragraph and assignment source. The preflight correctly blocks instead of silently running one of the many historical builders. Selecting a prior session's lane would violate the request's parallel-run rule.
3. **Uniqueness is not established.** No candidate was generated, so surface rank-correlation and final-dot overlap checks are **NOT RUN**, not zero or PASS. Prior session capacity calculations are not a substitute for this checkout's pinned witness and complete registry comparison.
4. **No valid holdout result for a new candidate.** Existing historical HOLDOUT-DTI values are tied to their named evaluator versions, folds, withheld-positive counts and confidence intervals. They are not results for this review and cannot be relabeled or compared as if obtained here.
5. **External data/authenticated score access is unavailable here.** No competition account, submission receipt, weekly selector state, or official rules-page session was available in this checkout. The sandbox's network allowlist excludes Dropbox, DrivenData, USGS, GDR and NLR hosts; no claim is made that those links were fetched or checked live.

### Repository quality and maintainability

- The repository has substantial fail-closed safeguards: shared holdout/evaluation code, common submission writer and validators, checksum manifests, uniqueness checks, leakage canaries, run cards, a research-only portal label, and many focused regression tests.
- `README.md` is very large and includes extensive repeated historical session reports. This raises the risk that old branch state, metric versions, or artifact links are mistaken for the current run. Its first heading/status was stale for this checkout (`arena/19912231-gemsdoe91`); updated to distinguish current-review state from historical results.
- The README and portal describe prior generated files. They must not be interpreted as this run's deliverable; this review generated none. The portal's exact current pointer and artifact verifier remain the source to check before downloading an existing artifact.
- The required prompt is already included in the README, but repeated copies make the document difficult to audit. A future cleanup should preserve the canonical full prompt once and replace repeated status prose with linked, dated, immutable run cards.
- No concrete code defect was established in the reviewed entry points during this pass. This is not a claim that every historical builder or external source has been independently audited line-by-line.

## Candidate hypotheses already documented (not assigned or run here)

The prior review `docs/REVIEW-19912231-20261025.md` contains three conditional proposals. Repository search and its stated scope do not establish novelty across the wider fleet. Their expected score improvement is unknown; ranking below is qualitative only.

| Rank | Hypothesis / existing layers | Signature and missing-fault rationale | Difference and non-fault mimic | Cost |
|---|---|---|---|---|
| 1 | B02 RTP magnetics + B13 isostatic gravity | Directional, opposite-side local semivariograms; target anisotropy-axis and correlation-length discontinuities that could persist where absolute edges are weak. | Within-field covariance geometry rather than derivative edge strength or pairwise cross-wavelet coherence. Mimics: lithologic contacts, interpolation seams, volcanic texture. | Medium |
| 2 | B02 magnetics + B13 gravity | Third-order wavelet bicoherence/phase closure across scale triads; test non-Gaussian localized multiscale structure. | Third-order phase coupling rather than pairwise coherence. Mimics: intrusive margins, processing seams, nonstationary noise. | High |
| 3 | B02 magnetics + total-count radiometrics | Directional ordinal-pattern entropy contrast with amplitude-matched shuffled controls. | Pattern-order frequency rather than amplitude/radiometric-ratio threshold. Mimics: weathering, alluvial sorting, flight-line striping. | Medium |

None is approved for implementation here. The top option cannot be validated without restoring the SHA-pinned training stack, and no official holdout run is possible until a lane is explicitly assigned and the data are verified. Do not spend a weekly submission slot on these hypotheses absent a positive matched holdout and passing literal registry gates.

## Verification performed

- `python3 -m compileall -q scripts src tools vendor` — **PASS**.
- `.venv/bin/python -m pytest -q` using repository-pinned dependencies — **626 passed, 8 skipped**. Skips are present in the test suite; these engineering tests do not prove a geological hypothesis or submission eligibility.
- `git diff --check` — **PASS** before this review note was added.
- `.venv/bin/python generate_submission.py --preflight` — **BLOCKED**, as expected: no assigned method/source and missing sample raster. `candidate_generated: false`; no experiment executed.
- Competition data restore was not attempted. The provided sandbox restricts outbound access to GitHub, npm and Python package hosts; the linked Dropbox/DrivenData sources are not reachable through the permitted hosts.

## Next actions

1. Supply/record a verifiable lane assignment and its source in the plan; do not infer it from past sessions.
2. Restore required competition inputs only via the pinned manifests, verify SHA-256 and byte size, and confirm all files actually exist in this checkout.
3. Rerun the preflight and the existing per-feature leakage canary. Freeze the named spatial holdout and incumbent comparator before the single assigned experiment.
4. Require a positive paired HOLDOUT-DTI difference with evaluator version, withheld positives and 95% CI, then run both surface and final-dot uniqueness against the complete unchanged registry.
5. Only after the candidate clears those gates should it be passed to the separate selector step. Keep format validation, uniqueness, holdout improvement, downloadability, and organizer submission receipt as separate states.
6. Improve README navigation in a separate documentation change: one canonical project brief, a concise current-state block, and historical runs linked by dated evidence rather than duplicated inline.
