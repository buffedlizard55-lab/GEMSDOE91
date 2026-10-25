# Project Limitations & Next Steps (`GEMSDOE91` — Updated 2026-10-25, Session 15)

## Current Scientific, Protocol & Engineering Limitations

1. **No Authenticated Organizer Score Receipt in Repository (`IR-91-S10-05`, `IR-91-PTAC-02`):**
   - Neither `GEMSDOE91` nor upstream [`buffedlizard55-lab/GEMSDOE32`](https://github.com/buffedlizard55-lab/GEMSDOE32) / [`GEMSDOE36`](https://github.com/buffedlizard55-lab/GEMSDOE36) contains an organizer-issued submission receipt. All external benchmark figures (`0.2778` on `h33-h33-2-b2`, `0.2750` on `h33-s2p8-zeros`, `0.3195`, `0.4413`) remain **`CLAIM-USER-REPORTED`** (`ORGANIZER-CONFIRMED: null`), and outbound network access from this sandbox is restricted to `github.com`, `npmjs.org`, and `pypi.org`.
2. **Uncalibrated Stage-1 Sub-Fold vs OOF Prior-Shift Drift (`IR-91-S15-06`):**
   - Cross-fitted auto-context stitches `2`-quadrant pairwise sub-models (`pi_sample ~ 0.13`) inside `Train_k` against `3`-quadrant OOF models (`pi_sample ~ 0.18`) on `Test_k`. Without per-split `prior_shift_calibrate_surface` before stitching, Fold-1 (`NE`) auto-context compressed to `0.823×` while `SW` inflated to `1.666×`, starving `NE` Dinkelbach emission onto `min_fold_dots = 6,500` and costing `S15-SCGF E2` (`0.240633 HOLDOUT-DTI`) ~`0.027` against `S14-PTAC E2` (`0.267782`).
3. **Regional Smooth Bowl Overfitting Under Spatially Blocked Quadrant Holdout (`IR-91-S15-07`):**
   - `>= 3 km` GDR kernels and `15 km` `S12` regional bowls memorize quadrant coordinates under `4`-quadrant spatial blocking (dropping Stage-1 OOF `HOLDOUT-DTI` `0.244601 -> 0.220480`), even though full-map fitting on all 4 quadrants lifts Blind Off-Catalogue USGS SGMC recovery (`S15-SCGF E2 = 0.097940` vs `S14-PTAC E2 = 0.095760` and `GEMSDOE32 R0 = 0.095386`).
4. **Literal All-Raster 3-px Overlap Ceiling (`IR-CED-003`, `IR-91-PTAC-03`):**
   - `data/fleet_registry/calib_r13lattice_00904.tif` (`206,895` synthetic 5-px lattice dots) blankets `99.87%` of the entire Nevada study footprint within `3 px`, forcing every valid `37k–54k`-dot candidate (`S14-PTAC E2 = 99.852%`, `S13-PTHA E3 = 99.84%`, `S15-SCGF E2 = 99.811%`) to fail the literal single-raster `<= 70%` check in `src/gems91/readiness.py` even when external discrete-fleet overlap (`<= 55.58%`) and `GEMSDOE32 R0` overlap (`44.82%`) pass cleanly.
5. **External Derivative Licence Provenance (`IR-91-26`, `IR-91-S14-02`):**
   - `data/external/lidar_scarp_features_u8.tif` and `data/external/geodawn_rad_u8.tif` are restored deterministically with verified SHA-256 via `scripts/restore_data.py`, but before any live DrivenData upload a human selector must confirm [Official Rules §A.5](https://docs.nlr.gov/docs/fy26osti/96647.pdf) open-data compliance (USGS 3DEP / USGS GeoDAWN public domain).
6. **Sandbox Compute Envelope (`3.8 GiB` RAM, `0 B` swap, `1` physical Xeon core):**
   - All `12.28M`-pixel feature tables (`123–137` float32 cols) must stream via out-of-repo `/tmp` `np.memmap` tiles (`<= 2.2 GB` RSS) to prevent OOM kills and stay under the `128 MB` turn-snapshot cap.

---

## High-Priority Next Steps for Session 16

1. **Prior-Calibrated Local-Physics Dual-Specialist Auto-Context (`S16` Hypothesis #1):**
   - Apply `prior_shift_calibrate_surface(..., pi_true_prior=0.022)` to **every** pairwise `(a, b)` and `3`-quadrant OOF Stage-1 prediction *before* computing `ac_full_*` and `ac_sub_*` (`IR-91-S15-06` fix), and strip `>= 3 km` GDR/regional bowl columns (`cols 65..92`) from Stage-1 while keeping `S13-PTHA`'s 75 local features + `S15-SCGF`'s 18 local Förstner/Salem/aquifer-baffle columns (`93` strictly local cols; `IR-91-S15-07` fix).
2. **Quota-Calibrated `E2` Crest × Dual Wash-Bridge Dinkelbach Emitter at `37,654` Dots:**
   - Retain `S15-SCGF E2`'s validated multi-scale Salem + Förstner junction + aquifer-baffle crest concordance (`+0.005544 HOLDOUT-DTI` over `E1` and `0.097940` Blind SGMC), replace `tau_train` transfer with area-proportional Dinkelbach quota (`IR-91-S14-04` / `IR-91-S15-06`), and benchmark directly against `S14-PTAC E2` (`0.267782 HOLDOUT-DTI`) on `gems91-hide-recover-v1.0` & `v1.1-nohalo`.
3. **Human Selector Governance Decision on `S14-PTAC E2` (`0.267782`) & Synthetic Blanket Scope:**
   - Currently **zero weekly DrivenData slots have been spent (`slots_used = 0`)**. If a human selector chooses to spend 1 of the 3 weekly DrivenData slots to obtain the repository's first true `ORGANIZER-CONFIRMED` score receipt, `S14-PTAC E2` (`0.267782 HOLDOUT-DTI`, `41.15%` 3-px overlap vs `R0`) is the highest-scoring holdout candidate in `GEMSDOE91` (mutually exclusive with `S13-PTHA`, `S12-SPAC`, and `S15-SCGF`).
