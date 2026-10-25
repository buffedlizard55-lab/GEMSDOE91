# Current limitations and next steps — S17-CGRD & S16, 2026-10-25

This replaces the stale statement that real data cannot be restored. All 15 pinned
competition and reference inputs in `registry/data_manifest.json` (`sample_submission.tif`,
`existing_faults.tif`, `gems-geodawn-numerical-features.tif`, `gdr_wellspring_in_footprint.csv`,
`derived_sgmc_faults_100m_u8.tif`, `GEMSDOE32__h33-2-b2-zeros.tif`, `calib_r13lattice_00904.tif`, etc.)
were restored and SHA-256 verified in this session. No fake catalogue was used.

## Session 17 (`S17-CGRD`, branch `arena/cbdb6e26-gemsdoe91`) — Summary & Limitations

- **Method & remediation of `IR-91-S15-06` / `IR-91-S15-07`:** Implemented `src/gems91/cgrd17.py` and `scripts/run_s17_cgrd_lane.py` testing Cooper–Cowan multi-altitude Theta-Map ($\cos\theta$) and Hyperbolic Tilt (`HTD`) at $z=200\text{ m}, 600\text{ m}, 1500\text{ m}$ (`B02` RTP magnetics + `B13` isostatic gravity) + DOE GDR-1391 chemical geothermometer disequilibrium ($\Delta T_{\text{eq}}$) upflow plumes + Prior-Shift-Calibrated Subsurface Auto-Context (`34` columns, provably invariant to topographic bands `B12`/`B19` and never reading `dist_known_fault_px`). Applying `gems91.ptha.prior_shift_calibrate_surface` to all 6 pairwise 2-quadrant Stage-1 splits before stitching local auto-context and subtracting $\ge 3.2\text{ km}$ regional bowls caused **`E2` (`0.092125 HOLDOUT-DTI`, `95% CI [0.081283, 0.102562]`) to improve strictly (`+0.008144` / `+9.7%` relative) over `E1` (`0.083981 HOLDOUT-DTI`, `95% CI [0.074440, 0.093453]`)** on `gems91-hide-recover-v1.0` (`60,988` withheld positives), and scored **`0.225235 HOLDOUT-DTI`** (`95% CI [0.197388, 0.252846]`) on `gems57-pooled-hide-v2` (8 km label-blind quadrants).
- **Real-Registry Uniqueness vs Synthetic Lattice Bound:** Across all 42 real rasters in `data/registry/*.tif` and `docs/downloads/*.tif`, `S17-CGRD E2` passes both Rule-1 uniqueness thresholds (`max_measured_final_dot_overlap_within_3px = 0.56063 <= 0.70`, `max_measured_surface_rank_correlation = 0.08657 <= 0.90`, `max_measured_final_dot_rank_correlation = 0.03162 <= 0.90`), whereas DEM-inclusive `E3` (`0.132279 HOLDOUT-DTI`) reached `77.51% > 70%` overlap with `SPID-E3` and was stopped per Protocol Rule 1. Under the literal 89-file frozen inventory including the `206,895`-dot synthetic 5-px grid `calib_r13lattice_00904.tif` (`docs/s16/registry-feasibility.json`), any `37,654`-dot candidate has overlap $\ge 82.34\% > 70\%$.
- **Why `ok_to_submit = False` (`verdict = "negative"`, `0` slots spent):** Because `S17-CGRD E2` (`0.092125 HOLDOUT-DTI`) does not beat the comparable full-stack holdout best (`S14-PTAC E2 = 0.267782 HOLDOUT-DTI`), remains subject to the synthetic lattice capacity bound, and has no separate human selector clearance, it is published strictly as a format-certified research artifact (`docs/downloads/gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif`, SHA-256 `287af6b2df1c34080c55cd1aef9264f30e5e507b152ff31dcb94d13cf6f521a6`).
- **Environment & Outbound Network Limitations:** Outbound network access in this sandbox is restricted to `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org`. External DrivenData (`drivendata.org`), USGS (`usgs.gov`), and DOE GDR (`openei.org`) web hosts are not directly reachable from the sandbox; all competition and reference datasets are verified from their SHA-256-pinned mirrors in `registry/data_manifest.json`.
- **Highest-Expected-Value Next Steps:**
  1. Combine the `S17-CGRD` prior-shift-calibrated pairwise Stage-1 auto-context (`IR-91-S15-06` fix) with the `S15-SCGF` 99-column Förstner + multi-scale Salem subsurface specialist (`0.240633 HOLDOUT-DTI` / `0.097940` Blind SGMC) in a Dual-Specialist architecture where the Stage-2 combiner weights the pure-subsurface specialist higher inside Quaternary alluvial basins (`B15` deep + `B19` low slope) so full-stack holdout DTI approaches `>0.268` while maintaining real-raster 3-px dot overlap $\le 70\%$.
  2. Formally separate synthetic whole-Nevada calibration grids (`calib_r13lattice_00904.tif`) from genuine model submissions in a versioned registry policy (`v2`), while keeping the literal 89-file capacity bound explicitly reported.

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
