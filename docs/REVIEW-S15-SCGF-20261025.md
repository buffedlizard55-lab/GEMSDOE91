# Session 15 Three-Pass Review & Audit (`S15-SCGF`, 2026-10-25, `arena/605655a6-gemsdoe91`)

## 1. Executive Summary & Automated Verdict

- **Primary Artifact (Range-Safe `[0, 1]` GeoTIFF):** [`docs/downloads/gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.tif`](downloads/gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.tif) (`239,912 B`, SHA-256 `0893322792aa46eaebba6f75702051d854efbe7fa5cb219e588ef863459ca3a1`)
- **Single-TIFF ZIP Archive:** [`docs/downloads/gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.zip`](downloads/gems91-s15-scgf-e2-20261025T060000Z-5b7e74e5-zeros.zip) (`205,630 B`, SHA-256 `e14e41057a58eb87807f6bdfb85bae5f4b68c96952ee3b578ba0307a7e92847f`)
- **Rule-5 JSON Run Card:** [`docs/run-card-S15.json`](run-card-S15.json) · **Evidence Bundle:** `evidence/s15_scgf_20261025.json` · **Preregistration:** [`docs/HYPOTHESES_S15.md`](HYPOTHESES_S15.md) (`sha256: 7d67810d6115b6e8a0607444a4e6e91f170c5343d0ba328f31129881f946150d`)
- **Unique Candidate Name:** `GEMS91-S15-SCGF-E2-5b7e74e5`
- **Form Note (`90/140` chars):** `S15-SCGF E2: Forstner+multi-scale Salem+baffle dual-AC; HOLDOUT-DTI=0.2406; 44k [0,1] dots`
- **Automated Gate Verdict (Zero Human Visual Inspection):**
  - **`OK TO DOWNLOAD: YES` (research & byte audit)** — All 5 GeoTIFF/ZIP format suites (`scripts/validate_raster.py`) PASS; all `12,279,160` float32 cells finite in `{0.0, 1.0}` (`nodata=None`); `EPSG:32611`, `3730×3292`, `100 m` geotransform `(100, 0, 243350, 0, -100, 4508550)` exact match to `sample_submission.tif`; `min_catalogue_distance_px = 3.1623 > 3.00 px`; `137/137` single-feature leakage canaries PASS (`max symmetric AUC = 0.72621 <= 0.90`); pre-placement surface rank correlation PASS (`max |Spearman rho| = 0.22183 <= 0.90`).
  - **`OK TO SUBMIT: NO` (`verdict: "negative"`, `submission_ready: false`)** — Shared readiness policy (`src/gems91/readiness.py`) blocks upload automatically because:
    1. `beats_comparable_best = False`: `S15-SCGF E2` scored **`0.240633 HOLDOUT-DTI`** (`95% CI [0.227931, 0.254026]`, `gems91-hide-recover-v1.0` & `v1.1-nohalo`, `60,988` withheld positives), trailing repo holdout best `S14-PTAC E2 = 0.267782` (`paired Δ = -0.027149`, `95% CI [-0.033521, -0.019924]`) and `S13-PTHA E3 = 0.244601` (`paired Δ = -0.003968`, `95% CI [-0.011639, +0.003128]`), though improving Blind Off-Catalogue USGS SGMC recovery to **`0.097940`** (`+0.002180` vs `S14-PTAC E2 = 0.095760`; `+0.002554` vs `GEMSDOE32 R0 = 0.095386`).
    2. `novelty = False` (`STOPPED_DUPLICATE` under literal all-raster Rule 1): `99.811%` of dots lie within `3 px` of synthetic whole-Nevada lattice `calib_r13lattice_00904.tif` (`206,895` dots), and `88.230%` / `83.820%` vs unsubmitted intra-repo siblings `gems91-spac-e3` / `gems91-s14-ptac-e2`. Against `GEMSDOE32 R0` (`h33-h33-2-b2`), overlap is **`44.816% <= 70%`** (`|rho| = 0.06956`); against external binary fleet rasters (`<= 50k` dots), max overlap is **`55.575% <= 70%`**.
    3. `assigned_lane = False` & `separate_selector = False`: Zero weekly DrivenData slots were spent (`slots_used = 0`).

---

## 2. Primary-Source Forensic Audit of `0.2778` (`GEMSDOE32`) & Prior-Session Irregularities Fixed First

### 2.1 Primary-Source Verification of `GEMSDOE32` (`0.2778` `CLAIM`)
1. Direct GitHub API inspection of [`buffedlizard55-lab/GEMSDOE32`](https://github.com/buffedlizard55-lab/GEMSDOE32) (`docs/index.html`) verified its explicit primary-source disclaimer: *"Nothing in this repo is an organizer-issued score receipt... Values such as `0.2778` and `0.4413` appear only in unverified narrative/configuration files and are reported below as claims, never as confirmed scores."* Likewise [`buffedlizard55-lab/GEMSDOE36`](https://github.com/buffedlizard55-lab/GEMSDOE36) records `0.2750` on `calib_h33thin_02585` (`h33-s2p8-zeros`) as user-reported. Every occurrence of `0.2778`, `0.2750`, `0.3195`, and `0.4413` is strictly stamped `CLAIM-USER-REPORTED` (`ORGANIZER-CONFIRMED: null`).
2. Direct inspection of the official scorer ([`drivendataorg/gems-prize-reference-solution`](https://github.com/drivendataorg/gems-prize-reference-solution), `scoring.py`) confirms `DTI = T / (T + 0.2*(S - M) + 0.8*(|G| - T))` under a `300 m` (`3 px`) separable triangular max-kernel (`[0, 1/3, 2/3, 1, 2/3, 1/3, 0]`). Because `T` uses pixel-wise `max` while `S = sum(P)` sums predicted mass linearly:
   - Any fractional non-zero prediction strictly loses to a `{0, 1}` binary vertex (`IR-91-SPID-02`).
   - Continuous ridges pack `7–15` pixels inside one `7×7` kernel footprint; `2.8 px` greedy spacing (`121k -> 44,090` dots) preserved `T` while cutting `0.2*S` by `~64%` (`0.1922 -> 0.2708` `CLAIM`), and `B=200 m` catalogue-collar pruning (`44,090 -> 37,654` dots) cut `6,436` near-catalogue false positives (`0.2708 -> 0.2778` `CLAIM`).
   - Algebraic inversion against the `206,895`-dot whole-Nevada lattice implies `|G_hidden| ≈ 12,350` hidden fault pixels (`~3.4%` of the known `365,610`-pixel catalogue). Surpassing `0.2778` toward `0.3195–0.4413` requires higher precision on **concealed off-catalogue subsurface faults**, not re-spacing the same range-front scarps.

### 2.2 Prior-Session Irregularities Audited & Repaired Before Launching `S15-SCGF`
- **`IR-91-S15-01` (PR #66 `generate_submission.py` / `run_card_synthetic.json`):** Quarantined synthetic Gaussian-noise placeholder script and explicitly stamped `"verdict": "negative"`, `"ok_to_submit": false`, `"submission_ready": false`.
- **`IR-91-S15-02` (PR #68 `docs/downloads/h91_submission_bundle.js` corruption):** Restored authentic `771,920`-byte `docs/downloads/h91_submission_bundle.js` (`sha256: 5e68e0329b2c88ce0086bf9fd996300a943059735a8744342a68247b2c56cd73`) from `GEMSDOE91@f2ae9964a3` after PR #68 had overwritten it with an incompatible `DZEDGE` payload.
- **`IR-91-S15-03` (PR #68 false `"ok_to_submit": true` / `"verdict": "promote"` on `HOLDOUT-DTI = 0.0`):** Quarantined `docs/run-card-gems91-dzedge-v2-20261025.json`, `docs/submission-guide.html`, `docs/dzedge-executive-summary.html`, `index.html`, and `README.md` lines 57–61 (`ok_to_submit: false`, `verdict: "negative"`).
- **`IR-91-S15-04` (Tracked raw NaN GeoTIFF & unregistered downloads):** Removed `docs/downloads/GEMS91-DZEDGE-20261025T021110Z-6b819d00.tif` (`7,114,860` NaNs) via `git rm -f` and registered all valid downloads in `registry/artifact_policy.json` (`scripts/check_artifact_policy.py` PASS).
- **`IR-91-S15-05` (`src/gems91/ptha.py` leaky `TOPO_FEATURE_NAMES`):** Empirical perturbation of `Band 12 (Elevation)` and `Band 19 (1m LiDAR scarp)` proved `17` DEM-dependent columns leaked into `S13-PTHA`'s "subsurface" specialist (including `b06_slope_resid`, `weingarten_*`, `tpi_*`, `lidar_*`, and `s12_basin_mask`-coupled columns), while `S14-PTAC` had zero Stage-2 subsurface specialist. Fixed in `src/gems91/scgf15.py` (`28` `STRICT_TOPO_FEATURE_NAMES`), verified bitwise by `tests/test_s15_scgf.py`.
- **`IR-91-S15-08` (`scripts/render_portal.py` stale `g91_hero` text & `LIMITATIONS_AND_NEXT_STEPS.md`):** Fixed contradictory `"OK to submit: YES — this file only"` text on the historical `G91-COVER` card in `scripts/render_portal.py` and replaced PR #66's inaccurate `LIMITATIONS_AND_NEXT_STEPS.md` (which falsely claimed `existing_faults.tif` could not be restored).

---

## 3. Session 15 Method & Measured Results (`S15-SCGF`)

All 3 experiments were pre-registered in `docs/HYPOTHESES_S15.md` (`sha256: 7d67810d6115b6e8a0607444a4e6e91f170c5343d0ba328f31129881f946150d`) prior to fitting:

| Arm | Mechanism Tested | `HOLDOUT-DTI` (`v1.0` = `v1.1`, `60,988` px) | 95% Block-Bootstrap CI | Paired Δ vs `S14-PTAC E2` (`0.267782`) | Paired Δ vs `S13-PTHA E3` (`0.244601`) |
| --- | --- | --- | --- | --- | --- |
| `S13-PTHA E3` (frozen baseline) | 75-feat Stage-1 MoE + PTHA Dinkelbach | `0.244601` | — | `-0.023181` | `0.000000` |
| `S14-PTAC E2` (frozen repo best) | 119-feat 2-Stage Auto-Context (`S13` Stage-1) | `0.267782` | — | `0.000000` | `+0.023181` |
| **`S15-SCGF E1`** | 137-feat Dual-Specialist Auto-Context (`99`-col Pure-Subsurface + `137`-col Full) + `ptha_crest` | `0.235089` | `[0.221533, 0.250959]` | `-0.032693` (`[-0.040199, -0.025973]`) | `-0.009512` (`[-0.017504, -0.002011]`) |
| **`S15-SCGF E2` (S15 winner)** | `E1` + Dual-Regime Förstner-Junction / Multi-Scale Salem / Aquifer-Baffle Crest × Dual Wash-Bridge Concordance | **`0.240633`** | **`[0.227931, 0.254026]`** | `-0.027149` (`[-0.033521, -0.019924]`) | `-0.003968` (`[-0.011639, +0.003128]`) |
| **`S15-SCGF E3`** | `E2` + SAR-PU Concealed-Basin Fairway Reweighting | `0.232708` | `[0.221622, 0.247771]` | `-0.035074` (`[-0.041925, -0.027556]`) | `-0.011893` (`[-0.020329, -0.004094]`) |

- **Per-Fold `E2` `HOLDOUT-DTI`:** `NW = 0.255360`, `NE = 0.273176`, `SW = 0.181317`, `SE = 0.277717`.
- **Blind Off-Catalogue USGS SGMC Control (`62,122` off-catalogue bedrock/concealed fault pixels `>300 m` from `existing_faults.tif`):**
  - **`S15-SCGF E2`: `0.097940`** (`+0.002180` over `S14-PTAC E2 = 0.095760`; `+0.002554` over `GEMSDOE32 R0 = 0.095386`).
- **Bitwise Determinism Check (Pass 2/3):** Re-running `scripts/run_s15_lane.py --phase eval_and_emit` reproduced identical `HOLDOUT-DTI` (`0.235089 / 0.240633 / 0.232708`), `SGMC` (`0.097940`), and identical SHA-256 digests (`08933227...` `.tif`, `e14e4105...` `.zip`).

---

## 4. Pass-2 Root-Cause Diagnosis (`IR-91-S15-06` & `IR-91-S15-07`) & Session-16 Roadmap

1. **`IR-91-S15-06` — Uncalibrated Sub-Fold vs OOF Prior-Shift Mismatch in Cross-Fitted Auto-Context:**
   - Inside each training fold `Train_k` (`3` quadrants), Stage-2 auto-context stitches `2`-quadrant pairwise sub-model predictions (`pi_sample ~ 0.13`) across quadrants, whereas on held-out `Test_k` it evaluates the `3`-quadrant OOF model (`pi_sample ~ 0.18`). Without prior-shift calibration (`prior_shift_calibrate_surface`) on each Stage-1 split before stitching, `mean(ac_p1_raw | Test_k) / mean(ac_p1_raw | Train_k)` drifted to **`1.385×` (NW), `0.823×` (NE), `1.666×` (SW), and `1.556×` (SE)**.
   - In Fold 1 (`NE`), `0.823×` compression starved `dinkelbach_fold_independent_emit` (`tau_train = 11.092` vs `last_test_gain = 1.545`), forcing `NE` onto `min_fold_dots = 6,500` (`NE` dropped from `0.3388` in `S14-PTAC` to `0.2732` in `S15-SCGF E2`, accounting for almost the entire `-0.0271` pooled gap, while `SE` rose to `0.2777`).
2. **`IR-91-S15-07` — Regional Smooth Bowl Overfitting Across Quadrant Boundaries:**
   - Restoring `3 km` GDR kernels and `15 km` `S12` regional bowls into Stage-1 caused Stage-1 OOF `HOLDOUT-DTI` to drop `0.244601 -> 0.220480` across spatially blocked quadrants, even though full-map training on all 4 quadrants lifted Blind Off-Catalogue USGS SGMC recovery (`0.097940` vs `0.095760`).
3. **High-Leverage Session-16 Action Items:**
   - Apply `prior_shift_calibrate_surface(..., pi_true_prior=0.022)` to **every** pairwise `(a, b)` and OOF Stage-1 split *before* constructing `ac_*` features, eliminating cross-quadrant scale drift.
   - Keep Stage-1 restricted to translation-invariant local derivatives (`<= 900 m`, including `S15`'s validated Förstner junction, multi-scale Salem, and aquifer-baffle physics which lifted `E2` `+0.005544` over `E1`), excluding `>= 3 km` GDR/regional bowls.
   - Replace `tau_train` transfer in `dinkelbach_fold_independent_emit` with area-proportional Dinkelbach quota calibrated at `37,654` dots (`B = 300 m` collar).

---

## 5. Three-Pass Verification Summary

- **Pass 1 (Implementation & Execution):** Repaired PR #66/#68 defects, preregistered `docs/HYPOTHESES_S15.md`, implemented `src/gems91/scgf15.py` + `scripts/run_s15_lane.py`, executed 137-feature canary + 3 holdout arms + full-map Blind SGMC + validated `.tif`/`.zip` emission (`exit_code: 0`).
- **Pass 2 (Bug Hunting, Diagnostics & Remediation):** Diagnosed `IR-91-S15-06` and `IR-91-S15-07`, expanded `SYNTHETIC_BLANKET_NAMES` + `R0` novelty disaggregation in `scripts/run_s15_lane.py` and re-verified bitwise identical `.tif`/`.zip` hashes, fixed `README.md` PR #68 `OK TO SUBMIT: YES` text, fixed `scripts/render_portal.py` stale `G91-COVER` `OK to submit: YES` text (`IR-91-S15-08`), replaced inaccurate `LIMITATIONS_AND_NEXT_STEPS.md`, and updated `IRREGULARITIES.md` & `SLOT_PLAN.md`.
- **Pass 3 (End-to-End Clean-Slate Re-Verification):** Verified `render_portal.py` reproducibility, `check_artifact_policy.py`, `verify_evidence.py`, `validate_raster.py`, `verify_current_artifact.py`, and full `pytest` suite (`0` failures).
