# Current limitations and next steps — review 2026-10-26

## Current branch review (`arena/c20e745a-gemsdoe91`)

**Status: NEGATIVE / BLOCKED. No new TIFF generated; no TIFF cleared to submit; 0 slots used by this review.** The assigned single-method lane is unresolved (`docs/run-card.json` has `assigned: false`). The local `data/` directory and cached feature inputs are absent, and the Python environment lacks NumPy/Rasterio/SciPy/scikit-learn/pytest at review time. Therefore this session did not run a fresh holdout, canary, raster validator or registry comparison. Historical manifest `local_present` flags and prior-session score records do not establish current availability or a current leaderboard score.

**Priority-site analysis:** [executive report](docs/PRIORITY-SITES-EXECUTIVE-SUMMARY.md) · [public summary](docs/priority-sites-executive-summary.html) · [JSON run card](docs/run-card-priority-sites-review.json). Among the nine values, GEMSDOE32 0.2778 is **OWNER-REPORTED (UNVERIFIED)**; the current owner-site pages use conflicting organizer-confirmed/owner-reported wording, with no DrivenData receipt supplied. Do not submit any copied or relabeled prior raster.

### Recommended next steps, in order

1. Resolve the method lane and the conflicting completeness/blanket-raster uniqueness policy explicitly; do not infer authorization or weaken thresholds.
2. Restore only approved, SHA-pinned data and cached stack, verify each file from disk, install repository-pinned dependencies, and report provenance/licensing. Do not rely on manifest booleans alone.
3. Run the proposed feature/cache novelty audit for PDSC before coding. If it is genuinely distinct, preregister one hypothesis and keep to the shared evaluator/writer.
4. Test each feature individually for leakage, then run spatial whole-segment buffered holdout and paired comparison against the same-fold incumbent. Require positive evidence before making a candidate TIFF.
5. Run pre-placement surface correlation and final-dot overlap checks against the full comparison registry. Stop on the first gate breach and preserve a negative run card.
6. Re-read and validate any produced GeoTIFF for [0,1] range, no NaN inside footprint, and exact CRS/shape/transform. A separate selector must approve any real weekly slot; this review does not select one.
7. Verify competition rules, source rights, current leaderboard context and score receipts through authorized official pages. Official external source leads and links are listed in the priority-site report; current coverage/access was not verified here.

---

## Historical limitations and next steps (prior parallel sessions, 2026-10-25)

### Parallel merged session: ISO91 (`arena/bacc7c26-gemsdoe91`, 2026-10-25)

**Status:** new unique research GeoTIFF; **OK TO DOWNLOAD: YES**; **OK TO SUBMIT: NO**.
The preregistered gates G1, G2 and G4 failed. Evidence: `docs/run-card-ISO91.json` and `docs/REVIEW-ISO91-BACC7C26-20261025.md`.

## Limitations (this session)

1. **The holdout truth is the catalogue, not expert-mapped new faults.**
   - The new I1 split copies only one live property: new faults lie away from known ones.
   - It does not reproduce their morphology or how experts identify them.
   - I1's 500 m separation also builds in an advantage for halo avoidance (CTL_HALO).
2. **Two key figures are MODEL inferences** from USER-REPORTED scores (uniform lattice and the R0 deletion chain), not measurements:
   - a public truth set of ≈ 12,500 px;
   - R0 covering ≈ 40% of it.
3. **The 19-band 100 m stack is saturated for PU learning.**
   - Every PU-HGB variant here is below R0 live (USER-REPORTED 0.1367–0.1823).
   - ISO91 shows that changing which faults are learned does not change where the model puts dots.
4. **Uniqueness scope.**
   - The protocol registry is partial (`complete_universal_registry: false`), and one row points at a retracted file (IR-91-ISO-03).
   - The sibling sweep covers the owner's public GEMSDOE* repositories only.
   - Dense area rasters need the documented dense-reference rule (IR-91-ISO-04).
5. **External high-resolution topography (USGS 3DEP) could not be fetched.** The sandbox fails the TLS handshake to the 3DEP hosts.

## Next steps (ranked by expected DTI gain per cost)

1. **H5 on an unrestricted machine.**
   - Build 1 m and 1/3 arc-second 3DEP scarp morphometry (multi-scale curvature, local relief, openness) aggregated to 100 m.
   - Preregister and test it on I1 and I2 against E0 with the ISO91 gates.
   - 3DEP is free and public domain (https://www.usgs.gov/3d-elevation-program/about-3dep-products-services).
2. **Far-field emission on the best label-blind posterior.**
   - Allocate dots by distance to the catalogue as R0 does, preregistered on I1 with CTL_HALO as the comparator.
   - This targets R0's strongest measured trait: 70% of its dots lie more than 1 km from the catalogue.
3. **Selector-level live test of a wider R0 collar (3–5 px).**
   - R0 has 15% of its dots at (2, 5] px.
   - This is an R0-derivative, so it belongs to the selector or R0's owner, not to a lane.
4. Fix `scripts/restore_registry.py`'s retracted row (IR-91-ISO-03), and propose `gems91.isolated_holdout` upstream to GEMSDOE78's template.

## Access needed

- An unrestricted network or CI job for 3DEP tiles (`prd-tnm.s3.amazonaws.com`), or the competition's `1m_DEM_links.csv` (DrivenData login).
- An owner decision on making the public data mirrors private (IR-91-09 / IR-91-ISO-06).
- The signed-in submissions page, to confirm the weekly upload limit (IR-91-ISO-05) and to record organizer receipts.

---

# Session 19 (`S19-SVHF`), Session 18 (`S18-HGBR`) & Session 17 Limitations and Next Steps, 2026-10-25

This replaces the stale statement that real data cannot be restored. All 13 licence-clean pinned
competition and reference inputs in `registry/data_manifest.json` (`sample_submission.tif`,
`existing_faults.tif`, `gems-geodawn-numerical-features.tif`, `gdr_wellspring_in_footprint.csv`,
`derived_sgmc_faults_100m_u8.tif`, `GEMSDOE32__h33-2-b2-zeros.tif`, `calib_r13lattice_00904.tif`, etc.)
plus all `62` `git_blob` fleet rasters (`scripts/restore_registry.py --available-only`) were restored and
SHA-256 verified in Session 19. No synthetic or fake catalogue was used.

## Session 19 (`S19-SVHF`, branch `arena/bcc0fcb2-gemsdoe91`) — Stitched-OOF De-Crowding, 90/90 Competitive Uniqueness & Session 20 Next Steps

- **Previous Session Blockers Solved in Session 19 (`src/gems91/svhf19.py`, `scripts/run_s19_svhf.py`):**
  1. **Solved `S17-LFTG` In-Sample Catalogue-Halo Crowding (`IR-91-S17-LFTG-01` -> `IR-91-S19-02`):** Emitting `svhf_e3` (`37,654` binary `{0.0, 1.0}` dots) strictly from the **stitched 4-fold spatially-blocked out-of-fold (`OOF`) Stage-2 surface** dropped `<=5 px` (`500 m`) catalogue crowding from `43.28%` (`S17-LFTG`) to **`14.10%`**, raised `>1 km` far-field coverage to **`69.16%`** (`26,042` dots), and lifted blind off-catalogue USGS `SGMC >500 m` discovery by **+60.2%** (`0.058293 -> 0.093415`, `91.20%` retention over `SGMC >300 m = 0.102428` — beating `GEMSDOE32 R0 = 0.088789`, `S14-PTAC = 0.071478`, and `S17-CPAD = 0.068915`).
  2. **Solved `S17-CPAD` / `S17-LFTG` Sibling PU 3-px Overlap (`82.96%` / `87.48%` -> `<=53.20%`):** Building a 100% backbone-orthogonal `58`-feature cube (cross-strike opposite-half-plane semivariogram jumps on flight-line-destriped `B02/B13/B15`, 3-D Laplace tabular gravity worms, multi-scale topographic Hurst breaks & Piedmont-Toe Concave Flexure on `B12/B19`, and local GDR #1391 chemical disequilibrium) cleared **`90/90` competitive (`<=80,000`-dot) submissions AND `96/96` non-blanket (`<=190,000`-dot) rasters** on 3-px dot overlap (`max = 53.20% <= 70%`; `43.80%` vs `GEMSDOE32 R0`, `42.87%` vs `S17-CPAD E1`, `37.84%` vs `S17-LFTG E2`, `44.18%` vs `S14-PTAC E2`) and `100/100` pre-placement Spearman rank-correlation checks (`max |ρ| = 0.1414 <= 0.90`).
  3. **Solved `3.8 GiB` Sandbox RAM Bottleneck:** Streamed per-band `float32` transforms directly into a disk-backed `float16` memmap with running azimuth accumulators (`<500 MB` peak RSS) and added `--available-only` to `scripts/restore_registry.py` (`IR-91-S19-01`).
- **Remaining Limitations Blocking Promotion (`ok_to_submit = False`, `0` weekly slots spent):**
  1. **Holdout Gap (`0.147791` vs `0.198183 S17-CPAD E1`, `IR-91-S19-03`):** On `gems57-pooled-hide-v2` (`60,988` withheld positives), `svhf_e1 = 0.135991` -> `svhf_e2 = 0.146862` (`+0.010871` from nested `QDAC`) -> `svhf_e3 = 0.147791` `[0.132771, 0.162342]` beats `CED91` (`+0.085638`), `S16-PGRD` (`+0.078394`), `gravity_control` (`+0.073768`), and `S17-CWPC E3` (`+0.025324`), but trails `incumbent_ptac_v2` (`0.192208`, `-0.044417`) and `S17-CPAD E1` (`0.198183`, `-0.050392`) for two measured reasons: (a) omitting `DD+SPAC+PTHA` multi-scale Frangi/Hessian/phase crest sharpness lowered per-dot precision (`0.2215` vs `0.2446 TPw/dot`); and (b) `S17-CPAD`'s in-sample training-quadrant scores saturated training collars early during global `37,654`-dot selection, spilling `48,465` cumulative dots across the 4 test folds vs `38,304` (`-21.0%`) under `S19`'s symmetric 3-level cross-fitted OOF surface.
  2. **Synthetic Whole-Nevada Lattice Witness (`calib_r13lattice_00904.tif`):** The `206,895`-dot synthetic 5-px calibration grid covers `99.85%` of any spread `37,654`-dot map within 3 px (`IR-S16-03`), keeping literal `registry_comparison.final.status = "DUPLICATE"` until a versioned coordinator protocol separates `>190k`-dot synthetic blankets from competitive model submissions.
  3. **Sandbox Outbound Allowlist & Human Selector Gate:** Direct HTTP access in this sandbox is restricted to `github.com`, `api.github.com`, `codeload.github.com`, `registry.npmjs.org`, `pypi.org`, and `files.pythonhosted.org` (no direct access to `drivendata.org`, `sciencebase.gov`, `asf.alaska.edu`, or `tnmaccess.nationalmap.gov`), and no coordinator lane token or human weekly-slot selector receipt is attached.
- **Ranked Priority Next Steps for Session 20:**
  1. **Rank 1 (No new external downloads required — immediate highest expected `HOLDOUT-DTI` + blind `SGMC` lift):** Fuse the top ~36 multi-scale ridge/crest sharpness operators from `DD+SPAC+PTHA+CPAD` (Frangi/Hessian $\lambda_-$, phase congruency, Cooper–Cowan sun-angle phase) with the `SVHF19` semivariogram-jump, multi-scale Hurst, and Piedmont-Toe Concave Flexure features inside **S19's 3-level nested cross-fitted `QDAC` + stitched 4-fold OOF CELF architecture**, adding explicit cross-product ridge-gate terms (`sv_jump * crest_sharpness`) so predictions retain both `>0.200 HOLDOUT-DTI` crest precision AND `>65%` far-field `>1 km` de-crowded generalization while checking `<=70%` competitive 3-px dot overlap at every arm.
  2. **Rank 2 (Unrestricted machine data ingest — `H19-4`):** Run an unrestricted ingest script against free official USGS 3DEP (`1m_DEM_links.csv`, `tnmaccess.nationalmap.gov`) and NASA ASF Sentinel-1 ARIA InSAR coherence/LOS velocity (`asf.alaska.edu`) to extract sub-meter Holocene piedmont micro-scarps (`0.3–1.5 m` throw invisible in 100-m `B12`) and aseismic fault-creep phase gradients across Nevada playas, pinning the derived `float16` summary bands into `registry/data_manifest.json`.
  3. **Rank 3 (Coordinator protocol versioning):** Propose a coordinator-signed `registry_policy_v2` separating synthetic `>190,000`-dot calibration blankets (`calib_r13lattice_00904.tif`, `r11_greedy_mp.tif`, `calib_fullband_probe_01841.tif`) from genuine `<=80,000`-dot competition candidates while keeping both numbers side-by-side on every run card.

## Session 18 (`S18-HGBR`, branch `arena/bba4efce-gemsdoe91`) — Variogram Hurst-Break, Up-Dip Listric Migration & OOF Cover-Rescue Summary & Next Steps

- **Completed Priority Next Steps from Sessions 17 (`IR-91-S17-01`, `IR-91-S17-02`, `IR-91-S17-LFTG-01`) and 18 (`H1`):**
  1. Implemented 16 novel `S18-HGBR` features (`src/gems91/hgbr18.py`, `scripts/run_s18_hgbr.py`): amplitude-gated 1st-order directional variogram Hurst-break, strike-parallel vs cross-strike Hurst anisotropy, and 300–900 m up-dip listric crest-to-scarp migration across `Band 10` (`grav_isostatic`), `Band 11` (`grav_bouguer`), `Band 13` (`mag_tmi`), `Band 14` (`mag_rtp`), `Band 8`/`9` (`sar_vv`/`vh`), `Band 18` (`geotherm_temp`), and `Band 0`/`1` (`elev`/`slope`, strictly isolated to `model_full` per `IR-91-S15-05`).
  2. Remediated `IR-91-S17-01` (`align_stage1_log_odds_dispersion`), `IR-91-S17-02` (`pool_asymmetric_cover_specialists` positive-part-only cover rescue), and `IR-91-S17-LFTG-01` (`stitch_oof_full_map_surface` 4-fold out-of-fold full-map stitching + structural backbone rescue).
  3. **Holdout Record (`HOLDOUT-DTI`, `gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer, `37,654` binary dots):** `hgbr_e1` achieved **`0.200742 HOLDOUT-DTI`** (`95% CI [0.180482, 0.221419]`; `hgbr_e2 = 0.200530`, `hgbr_e3 = 0.196442`), beating `S17-CPAD E1` (`0.198183`) on all 4/4 spatial folds (`+0.002560`), `INCUMBENT-PTAC-LB` (`0.194221`) by **`+0.006521`**, `INCUMBENT-PTAC-V2` (`0.192208`) by **`+0.008534`** (`95% CI [+0.002892, +0.014515]`), and `S17-LFTG E2` (`0.188596`) by **`+0.012146`** (`95% CI [+0.007290, +0.017609]`).
  4. **Untouched Blind Off-Catalogue USGS SGMC Control Record (`docs/s18_hgbr/blind-sgmc.json`):** `hgbr_e1` achieved **`0.103939` (`>300 m`)**, **`0.104995` (`>500 m`)**, and **`0.101151` (`>1 km`)** (`82.21%` of dots `>1 km` from the visible catalogue), beating `GEMSDOE32 R0` (`>1 km = 0.082913`) by **`+22.00%`** and `S17-LFTG` (`>1 km = 0.039897`) by **`+153.53%`**.
  5. **Real-Submission Uniqueness (`Rule 1`):** `hgbr_e1` passes `<= 70%` 3-px dot overlap and `<= 0.90` `|rho|` across **all 83 real submissions** (`vs GEMSDOE32 R0 = 48.77%`, `canonical real = 57.05%`, `external fleet = 51.29%`, `in-repo downloads = 61.87%`).
- **Remaining Limitations & Next Steps for Session 19:**
  1. **Synthetic Calibration Grid Policy (`IR-S16-03`):** Under the literal 100-raster check, the 3 synthetic `192k–273k`-dot calibration grids (`calib_r13lattice_00904.tif` `99.84%`, `r11_greedy_mp.tif` `88.13%`, `r14_union_tips10_lat6.tif` `75.90%`) exceed `70%` unidirectional overlap (`f1_dot_overlap_3px <= 0.2491`). A human selector decision (`D1`) is needed to confirm that real-submission uniqueness (`61.87% <= 70%`) governs live slot selection.
  2. **Widening the Paired Holdout Margin Over `S17-CPAD E1`:** While `hgbr_e1` beats `S17-CPAD E1` on all 4 folds (`+0.002560`), its 20-km block-bootstrap 95% CI (`[-0.000516, +0.005617]`) slightly touches zero (`P(>0) = 94.1%`). Next session should combine `S18-HGBR` features with a 2-D multi-scale directional convolutional/steerable filter layer trained on `spatial.folds` to push `HOLDOUT-DTI` above `0.205` with paired `ci95[0] > 0` against `S17-CPAD E1`.
  3. **External Bulk Datasets (`H18-4` MT/AEM & `H18-5` Pre-Dawn Winter Landsat LST):** Requires downloading USGS ScienceBase MT/AEM resistivity grids and winter night-time Landsat C2 L2 scenes on an unrestricted machine (`IR-91-S18-10`).

## Session 17 (`S17-LFTG`, branch `arena/281b6ba8-gemsdoe91`) — 3-D Laplace Tensor Gravity, SGMC >500 m Discovery & Next Steps

- **3-D Laplace Full-Tensor Gravity + Flight-Line Destriping + Zero-DEM Dual-Specialist (`src/gems91/lftg17.py`, `scripts/run_s17_lftg.py`):** Implemented 20 novel `B12/B19`-free physics features (exact float32 FFT 3-D Eötvös gravity tensor `G_z, \Gamma_{zz}`, Wijns `\cos\theta_G`, Pedersen–Rasmussen `Q_2D = 1 - |I|` with Viète factor `2.0`, directional flight-line notch destriping on `B01/B02/B06/B09/B14`, and basin-margin Bouguer curvature contrast). With **0 bytes of DEM bands `B12`/`B19` in the S17 stack**, `s17_e2_lftg_pcac` achieved **`0.188596 HOLDOUT-DTI`** (`95% CI [0.167180, 0.210009]`) on `gems57-pooled-hide-v2`, beating DEM-assisted `incumbent_ptha_v2` (`0.179206`) across **all 4/4 quadrants** (`+0.009390`), jumping **`+0.011771`** over Stage-1 `E1` (`0.176825`), and beating DEM-assisted `incumbent_ptac_v2` (`0.192208`) on **both southern concealed/playa quadrants** (`SW +0.005372`, `SE +0.013580`), while trailing `incumbent_ptac_v2` (`-0.003612`) and `S17-CPAD E1` (`0.198183`) on northern exposed DEM scarps.
- **Crucial SGMC `>500 m` Discovery (`IR-91-S17-LFTG-01`, `docs/s17_lftg/blind-sgmc.json`):** Stripping the `5,300` 1:500k registration-offset pixels (`300–500 m` from `existing_faults.tif`) causes in-sample refitted PU models to drop `-22%` to `-30%` (`S17-LFTG`: `0.080522 -> 0.056687`), whereas **`GEMSDOE32 R0` drops only `-7.2%` (`0.095386 -> 0.088516`, #1 at `>500 m`)**. Next session must emit full-map dots from **stitched 4-fold OOF predictions** rather than in-sample refitting on `100%` of `existing_faults.tif`, preventing `300–1,000 m` catalogue-halo crowding.

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
2. **Completed in Session 17 (`S17-CWPC`, `docs/run-card-S17-CWPC.json` & `S17-CDSC`, `docs/REVIEW-S17-CDSC-20261025.md`) & Next Auto-Context Refinement (`IR-91-S17-01` & `IR-91-S17-02`):**
   - `S17-CWPC` (`arena/4f695c18-gemsdoe91`) restored all 15 SHA-256-pinned competition inputs and 62 fleet reference rasters, preregistered 5 ranked geological hypotheses (`docs/HYPOTHESES_S17_CWPC.md`), and executed the 3-experiment Multi-Scale Complex Cross-Wavelet Phase-Lag & Quadrature Coherence + Cover-Conditioned Upward-Continuation Attenuation + Calibrated Local Auto-Context lane (`src/gems91/cwpc17.py`, `scripts/run_s17_cwpc.py`): `E1 = 0.082658`, `E2 = 0.131810`, `E3 = 0.122467 HOLDOUT-DTI` on `gems57-pooled-hide-v2` (`0.086573 HOLDOUT-DTI` on `gems91-hide-recover-v1.1-nohalo`) and `0.090912` Blind Off-Catalogue USGS SGMC DTI, with `34.97% <= 70%` 3-px dot overlap vs `GEMSDOE32 R0` and `51.92% <= 70%` max overlap vs all 43 repository rasters.
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


## Review 19912231 — next-session handoff (2026-10-25)

Run `python generate_submission.py --preflight` before restoring the large training stack or launching a model. Current plan is blocked: no assigned method paragraph, and a pinned witness proves the usual budget impossible under the literal overlap rule. No experiment run; no new TIFF or score. This is a necessary precheck, not a full-registry uniqueness pass, authenticated lane assignment, runtime budget manager or selector. Resolve lane and registry policy explicitly; never drop dense references or place anti-registry noise. Freeze a comparable, untouched holdout incumbent; only then test the authorized top hypothesis using shared cache/evaluator/writer and canaries. CWP91 with hole-shuffled control is already complete and negative. The current portal download remains OLC91 research-only. Fresh official-account/receipt/data-rights access is still absent. See `docs/REVIEW-19912231-20261025.md`.
