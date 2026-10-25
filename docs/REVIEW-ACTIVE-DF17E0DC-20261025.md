# Active-branch repository review — 2026-10-25

Branch: `arena/df17e0dc-gemsdoe91`  
Base: `b387d293f411110c04b4e20cdb56c088a4bd0d02`  
Review type: read-only review; no scientific experiment or submission-slot action.

## Executive result

The checkout already contains an extensive evidence-led workflow and prior generated research TIFFs. Its current root README clearly labels the latest displayed candidate **OK TO DOWNLOAD: YES — RESEARCH; OK TO SUBMIT: NO**. That distinction should remain: the recorded candidate failed a required registry-overlap uniqueness gate and did not beat its stated comparable holdout baseline. A format-valid file is not evidence of a competitive score or submission approval.

**No new candidate TIFF was generated in this review.** The parallel-run protocol says the lane is the single method paragraph “below,” but the supplied prompt contains no such method paragraph. Choosing or inventing a lane would violate the explicit instruction to stay within it. Also, `data/` is absent in this checkout, so the cached raster inputs needed to reproduce the holdout are not present. Do not label an existing artifact as newly generated or claim a fresh holdout result.

## Findings and verification

1. **Branch and working tree:** current branch is `arena/df17e0dc-gemsdoe91`; the working tree was clean at review start. HEAD is `b387d29` (`Merge pull request #86 ...`).
2. **Honest submission state:** README top-level status marks research download allowed and competition submission not approved. Existing run cards and session reviews describe prior research candidates; those are not organizer receipts.
3. **Lane ambiguity (blocking):** `docs/SESSION_BRIEF_S16.md` explicitly records that the required assigned-method paragraph is missing. The prompt included in this session has the same omission. No candidate strategy can be responsibly selected under this protocol until the lane is specified. This is a prompt-level conflict, not a reason to silently loosen duplicate thresholds.
4. **Data/reproduction (blocking):** `data/` does not exist. A local fresh experiment, holdout score, feature canaries, and surface/final registry duplicate checks cannot be rerun from this checkout without restoring the exact pinned inputs and dependencies. Existing logged values remain historical run evidence, not independently reproduced in this review.
5. **Test execution:** both `pytest -q` and `python -m pytest -q` were attempted. They did not execute tests because `pytest` is not installed (`pytest: command not found`; `No module named pytest`). Consequently this review makes no current all-tests-pass claim. The documented prior test results are historical records.
6. **Existing artifact availability:** previously generated TIFFs and ZIPs are present in `docs/downloads/`; their presence does not supersede the root submit-status warning. Users should follow the linked current run card and audit, not infer permission from a download button.
7. **Official score/source claims:** the user-supplied GEMSDOE32 score and current leaderboard values are not organizer-confirmed by the local evidence. Do not treat them as verified leaderboard results or use them as proof that a new model beats the reference.

## Required next steps, ordered

1. Make the assigned single-method paragraph explicit in the session brief; until then, do not launch an experiment or claim lane uniqueness.
2. Restore only manifest-pinned competition inputs and the pinned Python environment, then run the shared cached-feature, holdout evaluator, feature-alone leakage canaries, and submission writer; preserve hashes and exact evaluator version.
3. Before placement and on final dots, compare against the full available registry under the stated rank-correlation and directed 3-px overlap thresholds. Any missing registry entry remains UNVERIFIED; missing coverage cannot be converted into a uniqueness pass.
4. Require a predeclared comparable holdout incumbent and confidence interval before considering promotion. A separate authorized selector must check weekly allowance; this review does not select a slot.
5. Keep generated file status explicit: “OK TO DOWNLOAD — RESEARCH” may coexist with “OK TO SUBMIT — NO.” Change the latter only on complete automated evidence, not a manual toggle or format-only validation.
6. Install project dependencies and run the full test suite and artifact-policy checks before merging any code-changing PR. This review itself made documentation-only changes and did not alter implementation.

## Limitations and irregularities

- The requested lane paragraph is absent; this prevents scientifically compliant candidate selection.
- The raster inputs are not restored locally, and the test dependency is missing; fresh numerical verification was not feasible.
- A public repository page or locally reported score is not an organizer submission receipt.
- Existing TIFF files are useful research artifacts but are not approved entries under the current status; do not submit them based on file validity alone.
- No new external data was proposed, so no claim of source availability or external-data validation is made.
