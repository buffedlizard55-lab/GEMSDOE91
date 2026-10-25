# Current limitations and next steps — S16, 2026-10-25

This replaces the stale statement that real data cannot be restored. The pinned
competition feature stack, sample grid and existing-fault raster were restored
and SHA-256 verified in this session. No fake catalogue was used. The old
`generate_submission.py` path that overwrote that catalogue has been removed.

## Blocking an approved competition submission

1. **Literal uniqueness is infeasible at the fixed comparison budget.** The frozen
   lattice leaves only 6,649 footprint cells more than 3 px from its support.
   Any 37,654-dot binary result overlaps it by at least 82.34%, above the 70% cap.
   S16 measured 100% and stopped. An explicit, versioned registry/protocol decision
   is required; do not drop dense references, use symmetric overlap, or generate
   anti-registry noise. See `docs/s16/registry-feasibility.json`.
2. **No scientific improvement established.** S16 = 0.069397 HOLDOUT-DTI, 95% CI
   [0.057510, 0.081676], `gems57-pooled-hide-v2`, 60,988 withheld positives.
   Paired delta vs the matched gravity control = −0.004626 HOLDOUT-DTI, 95% CI
   [−0.010725, +0.001161], same evaluator/population. Negative result; no slot.
3. **No assigned single-method paragraph.** The prompt omits the lane assignment.
   PGRD was documented as provisional research, never falsely assigned.
4. **Registry coverage is incomplete.** 89 frozen entries attempted before
   placement, including two unavailable historical files; final checks stopped
   at reference 27. The public fleet feed is not a complete raster registry.
5. **No common certified current-best benchmark.** Historical scores mix
   checkerboards, quadrants, label-informed placement and hidden-truth halo
   deletion. CED's point estimate reproduced exactly; it is not a universal best.
   Repeated adaptive use of these holdouts also risks overfitting.
6. **Official account/rules state is unverified.** The official DrivenData web
   pages and external geological source leads were not fetched/authenticated
   in the recorded source audit. No authenticated fresh leaderboard, weekly-cap
   receipt or eligibility/data-rights attestation is available. Existing GitHub mirror hashes prove identity, not
   official endorsement or redistribution permission. No raw data are published.

## What works autonomously

- Fresh TIFF and single-TIFF ZIP under `docs/downloads/`, not copied from a prior
  prediction. Shape/CRS/full affine and all-finite [0,1] checks pass from disk.
- `python generate_submission.py --with-data` validates bytes, recorded evidence
  and the fail-closed verdict; a zero exit code is **not** slot approval.
- Candidate and control canaries, paired metric terms, provenance, registry stop,
  code hashes and source snapshots are stored for audit.
- A clean current Pages landing page, executive guide, research/source page and
  explicit historical archive. No human visual inspection requirement.
- A scheduled bounded GitHub source-feed check saved as an Actions artifact.
  It does not authenticate organizer scores or launch scientific experiments.
  **Publication limit:** Pages remains in legacy main-root mode. GitHub denied
  the publisher-mode update with HTTP 403 (Resource not accessible by integration).
  Committed snapshots can publish; scheduled refreshed artifacts cannot yet
  update the live feed. Pages-settings permission is required to enable that.

## Priority order for the next session

1. Resolve the registry feasibility conflict and lane assignment through explicit
   orchestration policy. Preserve today's negative evidence unchanged.
2. When running any future two-stage cross-fitted auto-context lane (following
   `S14-PTAC = 0.267782`, `S14-HVDC = 0.262209`, and `S15-SCGF = 0.240633`
   `HOLDOUT-DTI` / `0.097940` Blind SGMC), apply `prior_shift_calibrate_surface`
   to every `2`-quadrant sub-fold and `3`-quadrant OOF Stage-1 split *before*
   stitching `ac_*` features (`IR-91-S15-06`), exclude `>= 3 km` GDR/regional
   smooth bowls from Stage-1 (`IR-91-S15-07`), and retain `S15-SCGF`'s bitwise
   `B12`/`B19`-invariant Pure-Subsurface specialist (`IR-91-S15-05`) and local
   Förstner/Salem/aquifer-baffle crest concordance (`+0.005544` over `E1`).
2. Freeze a genuinely untouched control and evaluate the strongest permissible
   incumbent on the same label-blind whole-segment instrument, using paired CIs.
3. Verify official rules, input rights, account allowance and organizer receipts
   through authorized access. Never ask for credentials in chat.
4. Only then preregister a new bounded experiment; do not continue S16's variants
   after its duplicate stop. More complex physics is not automatically better.

The submitted-score ceiling is **unknown**. The user's 0.2778, 0.3195 and 0.4413
are not reclassified as ORGANIZER-CONFIRMED without a submission-page receipt.

## OLC91 session (2026-10-25, `arena/3444a6d3-gemsdoe91`)

* **Result:** negative. E1 OLC 0.0832 vs E0 0.0853 HOLDOUT-DTI (`gems57-pooled-hide-v2`, seed 20,
  11,321 withheld px); Δ −0.0021 [−0.0045, +0.0002]. The final file is DUPLICATE-STOP (76.8% of
  dots within 3 px of `gems91-bhar-e3`). OK TO SUBMIT: NO. 0 slots used; 1 of 3 experiments used.
* **Limitation: instrument mismatch.** On hide-and-recover, 55% of the withheld truth lies within 1 km
  of visible faults. Live evidence (proximity lanes below random; ≈0 credit for dots 1–2 px from the
  catalogue) says new faults are depleted there. No offline instrument is calibrated to the live board.
* **Limitation: convergence on one stack.** PU-HGB on the 19 official bands converges on the same
  15–25% of the footprint. Eleven earlier rasters overlap this file by more than 70%, so further
  models on this stack will keep tripping the dot-overlap rule.
* **Limitation: data provenance.** The pinned lidar-scarp and radiometric stacks are marked
  "licence unchecked" in `registry/data_manifest.json` and were not used. Getting a verified
  external source (3DEP 1 m DEM, GNSS strain tensors) requires hosts this sandbox cannot reach.
* **Next 1:** H2, completeness-weighted PU, with a *hole-shuffled control*. Compute ĉ after
  removing an equal pixel mass of random **visible** components, so that a gain caused only by
  holdout-made catalogue holes cancels out.
* **Next 2:** live-proxy calibration. Score the 13 owner-reported anchors in
  60GEMSDOE `registry/calibration_manifest.json` on the off-catalogue SGMC control, and report
  Spearman ρ against their live scores before using any proxy as evidence.
* **Next 3:** for the selector, not this lane. Pruning R0 to a 3–5 px collar is a cheap live test,
  because R0 still shows 2.1× and 1.75× area-lift at (2,3] and (3,5] px. It would be an
  R0-derivative and not unique, so it belongs to R0's owner, not this lane.
