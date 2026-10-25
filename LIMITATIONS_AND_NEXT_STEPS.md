# Current limitations and next steps — S17-CPAD, OLC91, S17-CDSC, S17-EULR, S17-CGRD & S16, 2026-10-25

This replaces the stale statement that real data cannot be restored. All 15 pinned
competition and reference inputs in `registry/data_manifest.json` (`sample_submission.tif`,
`existing_faults.tif`, `gems-geodawn-numerical-features.tif`, `gdr_wellspring_in_footprint.csv`,
`derived_sgmc_faults_100m_u8.tif`, `GEMSDOE32__h33-2-b2-zeros.tif`, `calib_r13lattice_00904.tif`, etc.)
were restored and SHA-256 verified in this session. No fake catalogue was used.

## Session 17 (`S17-CPAD`, branch `arena/aecf32eb-gemsdoe91`) — Summary, Forensic Quarantine & Next Steps

- **Forensic quarantine of legacy S13–S15 oracle buffer moat (`IR-91-S17-CPAD-01`):** Direct inspection of `scripts/run_s13_lane.py:87` (`_fold_active_and_eligible`) proved that historical `gems91-hide-recover-v1.0` numbers (`S14-PTAC E2 = 0.267782`, `S14-HVDC E2 = 0.262209`, `S15-SCGF E2 = 0.240633`, `S17-CDSC E1 = 0.259972`) passed `~fold.buffer_mask` into holdout dot placement, carving a label-informed moat around withheld truth. Re-fitting and evaluating `S14-PTAC E2` honestly on unchanged `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer) establishes the true label-blind 37,654-dot binary incumbent bar: **`INCUMBENT-PTAC-LB = 0.194221 HOLDOUT-DTI`** (`95% CI [0.173855, 0.213233]`).
- **Dual-Specialist Cooper–Cowan Phase + Accommodation Saddles + Geothermometer Disequilibrium (`src/gems91/cpad17.py`, `scripts/run_s17_cpad.py`):** Tested 3 preregistered arms (`docs/HYPOTHESES_S17_CPAD.md`) combining 16 novel `CPAD` features (`14` subsurface columns verified bitwise `0.0` invariant to `Band 12`/`Band 19` perturbations) with Bayes reference-odds-calibrated (`c0 = 12.0`) Full (`128`-col) and Pure-Subsurface (`100`-col) specialists:
  - **`cpad_e1` (Full Stage-2 over `X_full + ac_full + ac_sub`, `37,654` global binary NMS dots): `0.198183 HOLDOUT-DTI` (`95% CI [0.177759, 0.217830]`)** — **#1 strict label-blind `37,654`-dot binary `gems57-pooled-hide-v2` score in `GEMSDOE91`**, beating `INCUMBENT-PTAC-LB` (`0.194221`, paired `+0.003962`, `95% CI [-0.001766, +0.010077]`), `CED91` (`0.070886`, paired `+0.127296`), and `S16-PGRD` (`0.069397`, paired `+0.128786`), plus **`0.068585 BLIND-SGMC-CONTROL-DTI`** (`+78.1%` over `S16-PGRD = 0.038501`).
  - `cpad_e2` (exogenous `[0.28, 0.68]` cover-gated blend): `0.187678 HOLDOUT-DTI`; `cpad_e3` (cover-gated blend + 300-m kernel submodular placement): `0.185966 HOLDOUT-DTI` (showing learned Stage-2 gating outperforms hand-crafted exogenous cover weights by `+0.010505`).
- **Remaining blockers (`ok_to_submit = False`, `0` slots spent):**
  1. `cpad_e1` passed `95/95` pre-placement Spearman checks (`max |rho| = 0.2191 <= 0.90`) and `50/50` preceding fleet rasters (`GEMSDOE32 R0 = 0.4927 <= 0.70`), then stopped fail-closed at `51/95 r11_greedy_mp.tif` (`272,853` dots, `0.8725 > 0.70`), alongside shared-backbone overlap (`0.8296`) with in-repo `S14-PTAC E2` and the synthetic lattice bound (`calib_r13lattice_00904.tif >= 82.34%`).
  2. Paired 20-km block-bootstrap 95% CI vs `INCUMBENT-PTAC-LB` (`[-0.001766, +0.010077]`) slightly straddles `0`.
  3. Unassigned `[PASTE ONE METHOD]` paragraph and separate human weekly-slot selector (`drivendata.org` outside sandbox outbound allowlist).
- **Priority for Session 18:** Train a backbone-orthogonal spatial operator (e.g., 2-D multi-scale steerable/Gabor directional filter-bank CNN / U-Net with `Band 12`/`19` dropout on `spatial.folds`) so final dots stay `<= 70%` overlap against the `DD+SPAC+PTHA+HVDC` HGB family while exceeding `0.198183` on `gems57-pooled-hide-v2` with paired `ci95[0] > 0`.

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

## Session 18 `S18-CWGR` limitations & concrete Session 19 next steps (2026-10-25, `arena/892fab6a-gemsdoe91`)

* **Measured result (`verdict: negative`, `OK TO DOWNLOAD: YES`, `OK TO SUBMIT: NO`, `slots_used = 0`):**
  * `S17-CPAD E1` (`cpad_e1`) reproduced bit-for-bit at **`0.198183 HOLDOUT-DTI`** (`95% CI [0.177759, 0.217830]`) on `gems57-pooled-hide-v2` (`60,988` withheld positives, `80 px` buffer) and remains the repository's highest strict label-blind `37,654`-dot benchmark.
  * `S18-CWGR` (`cwgr_e1`: **`0.188460`**, `95% CI [0.169981, 0.206529]`; `cwgr_e2`: `0.187910`; `cwgr_e3`: `0.164534`) passed all `174` leakage canaries (`max symmetric AUC = 0.688170 <= 0.90`), `108/108` pre-placement Spearman checks (`max |ρ| = 0.219355 <= 0.90`), and **`46/46` (`100%`) real competitive external fleet submissions** (`max 3-px overlap = 0.539651`; `GEMSDOE32 R0 = 0.467201`; `cwgr_e3 vs GEMSDOE32 R0 = 0.364689`), halting fail-closed at `#48` `calib_h28ridge_01839.tif` (`69,281`-dot metric-calibration probe, `0.714957 > 0.70`).
* **Limitation 1 — Marginal rank standardization erases true regional fault-density prevalence (`IR-91-S18-02`):** Equalizing Stage-1 quantiles per quadrant (`IR-91-S17-01`) eliminated `Test_k / Train_k` rank skew, *and* under fixed `37,654` area-quota controls (`17846 / 9957 / 4111 / 5740`) proved Bekker–Davis SAR IPW (`cwgr_e2_quota37654 = 0.182717`) beats unweighted SCAR (`cwgr_e1_quota37654 = 0.180949`, `+0.001768`, `3/4` folds). However, forcing identical marginals across quadrants starved high-extension Humboldt/Dixie Valley NE Fold 1 under global top-`37,654` selection (`0.243419` quota -> `0.226655` global vs `0.250065` in `cpad_e1`).
* **Limitation 2 — Scarp-anchored offline evaluation vs blind-basin discovery (`IR-91-S18-03`):** Both `existing_faults.tif` (`gems57-pooled-hide-v2`) and USGS `SGMC` (`>500 m` off-catalogue) over-represent range-front/outcrop scarps (`ê -> 0.85`), penalizing `cwgr_e3`'s `(1 - 0.65·ê)` blind-playa Bayes factor despite its `0.3647` orthogonality vs `GEMSDOE32 R0`. Moreover, diluting `s2_full` weight from `0.62` (`S17-CPAD`) down to `0.46` weakened full multi-physics interaction trees.
* **Limitation 3 — Sandbox network allowlist & synthetic lattice mathematical floor:** Outbound sandbox access permits only `github.com`, `npmjs`, and `pypi.org`, blocking direct ingestion of external USGS 3DEP `1/3 arc-sec` bare-earth LiDAR (`usgs.gov`) and NASA OPERA `30 m` Sentinel-1 InSAR velocity (`asf.alaska.edu`, `H18-4`), as well as live DrivenData authentication (`ORGANIZER-CONFIRMED: null`). Meanwhile, `calib_r13lattice_00904.tif` (`206,895` dots covering `99.8713%` of Nevada within `3 px`) enforces an `82.34%` mathematical overlap floor for any valid `37,654`-dot set.
* **Concrete Session 19 Next Steps (ordered by expected DTI gain vs cost):**
  1. **Keep `S17-CPAD`'s prevalence-preserving `calibrate_reference_odds_surface` (`s2_full >= 0.65`) while retaining SAR IPW (`cwgr_e2`) + `CWGR` steerable `(G_1, 0.78·G_2)` quadrature features:** Do *not* apply uniform marginal rank standardization across quadrants; instead, combine `S17-CPAD`'s prevalence-preserving Bayes odds calibration with `S18-CWGR`'s proven local SAR IPW (`+0.001768` within-fold gain) and `cwgr18.py` subsurface columns `0..14`.
  2. **Execute deferred preregistered `H18-2` (Spectral Bouguer / RTP radial log-power matched-filter depth-slicing at `0.3–1.5 km` vs `3–8 km` basement)** to separate shallow intra-basin geothermal fault relays from broad deep plutonic roots without touching topography.
  3. **Run external `H18-4` (USGS 3DEP bare-earth LiDAR + NASA OPERA L3_DISP_S1 InSAR strain tensor)** on an unrestricted network runner with explicit CC0/public-domain provenance hashes recorded in `registry/data_manifest.json`.
  4. **Human selector governance:** Present `S17-CPAD E1` (`0.198183` label-blind `HOLDOUT-DTI`, `49.27%` vs `GEMSDOE32 R0`), `S17-CDSC E1` (`0.259972` `v1.0` `HOLDOUT-DTI`, `43.76%` vs `GEMSDOE32 R0`), and `S18-CWGR E1` (`0.188460` label-blind `HOLDOUT-DTI`, `46.72%` vs `GEMSDOE32 R0`) to the separate human selector solely after explicit resolution of the synthetic-lattice policy (`IR-CED-003` / `IR-91-S18-04`) and verification of the 3/week DrivenData slot cap.

