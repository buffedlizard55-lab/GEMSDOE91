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
2. **Completed in Session 17 (`S17-CDSC`, `docs/REVIEW-S17-CDSC-20261025.md`) & Next Auto-Context Refinement (`IR-91-S17-01` & `IR-91-S17-02`):**
   - `S17-CDSC` executed the three `S15-SCGF` remediations (`IR-91-S15-06` Bayes prior-shift calibration of 2-quadrant pairwise Stage-1 sub-models to 3-quadrant training sample prevalence before stitching, `IR-91-S15-07` excluding `>= 3 km` GDR/S12 regional bowls from Stage-1 while keeping `16` local `S15` subsurface features in Stage-2, and `IR-91-S15-05` `72`-col bitwise `B12`/`B19`-invariant Pure-Subsurface specialist), recovering Fold 1 (`NE`) by **`+0.058247`** (`0.273196 -> 0.331443`) and lifting pooled `HOLDOUT-DTI` to **`0.259972`** (`+0.019339` over `S15-SCGF E2 = 0.240633`, `+0.015371` over `S13-PTHA E3 = 0.244601`).
   - Next-session priorities to close the remaining `-0.007810` gap to `S14-PTAC E2` (`0.267782`):
     1) **`IR-91-S17-01`:** Replace global sample-prevalence scaling of `stitch_p1` with per-quadrant empirical quantile / rank-logit standardization before running `compute_spac_autocontext_features`, ensuring exact `1.000x` `Test_k / Train_k` distribution equality across all 4 quadrants (eliminating the residual `1.429x` `SE` and `1.144x` `SW` spatial fault-density drift and preventing `Train_k` upward calibration from tightening $\lambda^*(\text{Train}_k)$).
     2) **`IR-91-S17-02`:** Train a dedicated 14-column Stage-2 **Topology Specialist** (`hgb_topo`) solely on `S17_AUTOCONTEXT_NAMES` + `ptha_crest` and pool its calibrated log-odds with `PTAC`'s 85-feature Stage-2 ensemble so adding local subsurface features does not dilute root splits on `ac_wash_bridge_1km` and `ac_wash_bridge_2km`.
3. Freeze a genuinely untouched control and evaluate the strongest permissible
   incumbent on the same label-blind whole-segment instrument, using paired CIs.
4. Verify official rules, input rights, account allowance and organizer receipts
   through authorized access. Never ask for credentials in chat.
5. Only then preregister a new bounded experiment; do not continue S16's variants
   after its duplicate stop. More complex physics is not automatically better.

The submitted-score ceiling is **unknown**. The user's 0.2778, 0.3195 and 0.4413
are not reclassified as ORGANIZER-CONFIRMED without a submission-page receipt.
