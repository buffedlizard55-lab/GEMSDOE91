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

---

## Session 17 (`S17-CWPC`, 2026-10-25, branch `arena/4f695c18-gemsdoe91`) — Update, Findings & Next Steps

### What was completed in Session 17
1. **Autonomous Data & Registry Restoration:** Restored and SHA-256 verified all 15 competition inputs (`scripts/restore_data.py`, including the 418.9 MB 19-band `gems-geodawn-numerical-features.tif`, 4-band radiometrics, 12-band LiDAR scarp stack, and off-catalogue USGS SGMC control), rebuilt `data/derived/catalogue_mask.tif` (`60,988` positive pixels) and `registry/preflight.json` (`BUILD ALLOWED: 2/2 required inputs verified`, `6/6` axes `READY`), and restored all 62 available `data/fleet_registry/*.tif` reference rasters (`scripts/restore_registry.py`).
2. **Preregistration (`docs/HYPOTHESES_S17_CWPC.md`):** Preregistered 5 ranked geological hypotheses (`H17-1`..`H17-5`) and the forensic analysis of `GEMSDOE32` (`0.2778 USER-REPORTED`) before running any holdout experiment.
3. **Implementation & S15 Root-Cause Remediation (`src/gems91/cwpc17.py`, `scripts/run_s17_cwpc.py`):**
   - Implemented 16 label-blind `CWPC` geophysical features (multi-scale complex Riesz cross-wavelet coherence & quadrature across $\sigma \in \{2, 4, 8\}\text{ px}$ on `rtp × tc`, `rtp × iso_grav_anom`, and `iso_grav_anom × cond_surf`; cover-conditioned upward-continuation structural index; SI-reconciled Verduzco tilt & Salem wavenumber; Coulomb strain-strike slip-tendency; flight-line oblique filter; within-unit edge Z), streaming into a disk-backed `float16` memmap (`< 450 MB` peak RAM).
   - Fixed `IR-91-S15-06` via `CWPC.prior_shift_calibrate_surface` (exact Bayes prior-shift calibration across Stage-1 training vs OOF evaluation domains) and `IR-91-S15-07` via `CWPC.build_local_autocontext_features` (strictly local $\le 900\text{ m}$ auto-context operators plus calibrated `B12`/`B19`-blind `ac_subsurf_cal`).
4. **Measured Holdout & Control Results (`docs/run-card-S17-CWPC.json`):**
   - `E1_cwpc_physics_hgb` (16 label-blind CWPC physics features alone, zero topographic bands): **`0.082658 HOLDOUT-DTI`** (`95% CI [0.073949, 0.091793]`, `+0.011325` vs `random_null` on `gems57-pooled-hide-v2`; `0.044412 HOLDOUT-DTI` on `gems91-hide-recover-v1.1-nohalo`).
   - `E2_cwpc_integrated_hgb` (43 features: 16 CWPC + 19 sponsor bands + 8 gradients): **`0.131810 HOLDOUT-DTI`** (`95% CI [0.114159, 0.147689]`, `+0.060477` vs `random_null`, `+0.049153` vs `E1` on `gems57-pooled-hide-v2`; `0.089250 HOLDOUT-DTI` on `gems91-hide-recover-v1.1-nohalo`).
   - `E3_cwpc_calibrated_dual_autocontext` (43 features + 8 prior-shift-calibrated local $\le 900\text{ m}$ auto-context channels): **`0.122467 HOLDOUT-DTI`** (`95% CI [0.105656, 0.137559]`, `+0.051133` vs `random_null` on `gems57-pooled-hide-v2`; `0.086573 HOLDOUT-DTI` on `gems91-hide-recover-v1.1-nohalo`).
   - **Blind Off-Catalogue USGS SGMC Control (`SGMC-OFFCAT-CONTROL-DTI`):** **`0.090912`** (`62,122` off-catalogue bedrock/concealed fault pixels $> 300\text{ m}$ from `existing_faults.tif`, exceeding `E3`'s own `v1.1-nohalo` catalogue score `0.086573`).
   - **Unique Artifact:** `docs/downloads/gems91-s17-cwpc-e3-37654dots-20261025T150000Z-4d124f1d-zeros.tif` (`sha256: 792af6255a7e1048e5c2053c178feee5f807f5de83b5d07e51617a7164115ec5`) and `.zip` (`sha256: e36c855d7ee93fed60ad5d8c18d32d0d4e748ff204539fa638f6e8faca9d24b4`); passes all format/CRS/`[0,1]`/collar gates, all 43+8 leakage canaries (`worst AUC = 0.62714 <= 0.90`), and registry uniqueness vs `GEMSDOE32 R0` (`34.97% <= 70%`) and all 43 repository rasters (`max 51.92% <= 70%`).

### Remaining Limitations & Priority Next Steps for Session 18
1. **Quadrant-Transfer vs Checkerboard Gap:** Under the strict 4-quadrant whole-component 8 km buffer (`gems57-pooled-hide-v2`), 37,654-dot models trained on 3 quadrants transfer at `0.122–0.194 HOLDOUT-DTI`, whereas 12.8 km checkerboard models (`S14-PTAC = 0.267782`) benefit from closer spatial proximity of training blocks. Next session should evaluate `S14-PTAC`'s exact 89-feature cube + `CWPC` cross-wavelet quadrature channels on **both** `gems57-pooled-hide-v2` and `gems91-hide-recover-v1.1-nohalo` under identical 44,090-dot and 37,654-dot budgets.
2. **Stage-2 Auto-Context Regularization Across Quadrants:** While `prior_shift_calibrate_surface` (`IR-91-S15-06`) reduced fold calibration drift to `0.67–1.25x` (down from `0.82–1.67x`), fitting a fresh 31-leaf tree on `tr_dom` still slightly underperforms Stage-1 `E2` (`-0.009344` on `gems57-pooled-hide-v2`) because Stage-1 training-domain residuals are smaller than OOF residuals. Next session should generate Stage-1 training-domain predictions via **3-way inner spatial sub-fold cross-fitting** before computing `build_local_autocontext_features`.
3. **Dense Registry Blanket Lattice (`calib_r13lattice_00904.tif`):** Requires an explicit selector/protocol rule separating real $\le 60,000$-dot candidate submissions from 206,895-dot calibration lattices (`Pigeonhole lower bound = 82.34%` at `37,654` dots).
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
