# Session 17 Post-Run Technical Review — `S17-CDSC` Prevalence-Calibrated Faulds–Hinz Relay Topology, Local Subsurface-Junction Fusion & Pure-Subsurface Specialist Discovery

- **Date:** 2026-10-25 UTC
- **Branch:** `arena/1722e30a-gemsdoe91`
- **Pre-Registration:** `docs/HYPOTHESES_S17_CDSC.md` (`sha256 = a249d664b841899428b0bf20a9d1db751cba91fcc7c318f1c8ad300cd2a443e5`, frozen prior to fitting)
- **Run Card & Evidence:** `docs/run-card-S17-CDSC.json` · `evidence/s17_cdsc_20261025.json`
- **Primary All-Finite `[0, 1]` GeoTIFF:** `docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif` (`sha256 = 39aaac68e7640d9914f1f8431bab589ce30eda6bf7a59512e38699f705d21836`, `238,242` bytes, `44,000` binary `{0, 1}` dots)
- **Single-TIFF ZIP Bundle:** `docs/downloads/gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.zip` (`sha256 = fc022924ae02ee940731c43039875b2b475d0371b462a05b206822b542ba3446`, `201,696` bytes)
- **Submission Name & `<= 140`-Char Note:**
  - Name: `GEMS91-S17-CDSC-E1-6aca4066`
  - Note (`95` chars): `S17-CDSC E1 research only: HOLDOUT-DTI=0.2600; ext3px=53.2%, r13_blanket=99.83%; do not submit.`
- **Verdict:** `verdict = "negative"`, `portal_submission_verdict = "NOT_OK_TO_SUBMIT"`, `submission_ready = false` (`OK TO DOWNLOAD: YES — RESEARCH` · `OK TO SUBMIT: NO`). Zero weekly DrivenData slots spent.

---

## 1. Executive Summary of `S17-CDSC` Results

Session 17 (`S17-CDSC`) directly executed the top three remediation priorities from `LIMITATIONS_AND_NEXT_STEPS.md` and `docs/REVIEW-S15-SCGF-20261025.md`:
1. **`IR-91-S15-06` Remediation (Fold-Safe Bayes Prior-Shift Prevalence Alignment Before Auto-Context Stitching):**
   Calibrating every 2-quadrant pairwise Stage-1 sub-model `(a, b)` from its sample prevalence `pi_sample_weighted` (`0.107–0.168`) to each fold's 3-quadrant training sample prevalence (`0.150–0.179`) before stitching compressed the `Test_k / Train_k` Stage-1 scale ratio from **`1.4493x -> 1.0329x` (NW)**, **`1.5634x -> 1.0902x` (NE)**, **`1.6271x -> 1.1442x` (SW)**, and **`2.1020x -> 1.4290x` (SE)**.
   - **Direct impact on Fold 1 (`NE`):** Emitted dots recovered from `6,500` (`S15-SCGF E2`) to **`10,621` (`S17-CDSC E1`)**, and Fold 1 (`NE`) `HOLDOUT-DTI` jumped **`+0.058247` (`+5.82` DTI points)** from `0.273196` (`S15-SCGF E2`) to **`0.331443` (`S17-CDSC E1`)**!
2. **`IR-91-S15-07` Remediation (Scale Segregation — Local `75`-Feature `S13` Stage-1 + `16` Local `S15` Subsurface Features in Stage-2):**
   Keeping Stage-1 strictly on the 75 local translation-invariant `S13-PTHA` features (`0` `3 km` GDR bullseyes, `0` `15 km` `S12` regional bowls) while injecting the `16` local (`<= 1 km`) `S15` Förstner-junction, multi-wavelength (`150–900 m`) Salem tilt-depth worm, and 2-D `(B15, B12)` deconfounded aquifer-baffle features into Stage-2 lifted pooled `HOLDOUT-DTI` from `S15-SCGF E2`'s `0.240633` to **`0.259972` (`+0.019339`)**, and beat `S13-PTHA E3` (`0.244601`) by **`+0.015371` (`paired 95% CI [+0.010244, +0.021122]`, `prob_positive = 1.000`)**.
3. **`IR-91-S15-05` Remediation (`72`-Column Bitwise `B12`/`B19`-Invariant Stage-2 Pure-Subsurface Specialist):**
   Trained a dedicated `HGB-PureSubsurface` specialist (`hgb_sub`) inside Stage-2 strictly on the `72` `B12`/`B19`-free subsurface columns (`tests/test_s17_cdsc.py` verifies bitwise equality under arbitrary `B12`/`B19` noise perturbation).

---

## 2. Full 3-Experiment Ladder & Comparable Holdout Benchmark

All experiments were evaluated on the identical 4-quadrant spatially-blocked segment-buffered holdout (`split_sha256 = 0f874367d8d34964c9b8802d3d67d348f68ade1f9fbc4301bffc5eafcb524db8`, `60,988` withheld fault pixels):

| Experiment / Baseline | Features | `HOLDOUT-DTI` (`v1.0`, `60,988` pos) | 95% Block-Bootstrap CI | `HOLDOUT-DTI` (`v1.1-nohalo`) | Paired $\Delta$ vs `S14-PTAC E2` (`0.267782`) | Paired $\Delta$ vs `S13-PTHA E3` (`0.244601`) | Fold DTI (`NW` / `NE` / `SW` / `SE`) | Pooled OOF Dots |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| **`S14-PTAC E2` (Repo Holdout Best)** | `85` | **`0.267782`** (`HOLDOUT-DTI`) | `[0.253687, 0.281135]` | `0.267782` | `0.000000` (reference) | `+0.023181` `[+0.018573, +0.028159]` | `0.2683` / `0.3365` / `0.1826` / `0.3139` | `43,633` |
| `S14-HVDC E2` | `86` | `0.262209` (`HOLDOUT-DTI`) | `[0.248940, 0.275209]` | `0.262209` | `-0.005573` | `+0.017608` `[+0.014308, +0.021163]` | `0.2554` / `0.3347` / `0.1753` / `0.3133` | `42,272` |
| **`S17-CDSC E1` (`H17-1 + H17-2`, S17 Winner)** | **`105`** | **`0.259972`** (`HOLDOUT-DTI`) | **`[0.244333, 0.275361]`** | **`0.259972`** | **`-0.007810` `[-0.011847, -0.003430]`** | **`+0.015371` `[+0.010244, +0.021122]`** | **`0.2651` / `0.3314` / `0.1712` / `0.3062`** | **`40,122`** |
| **`S17-CDSC E2` (`E1 + H17-3` Relay/Salem Crest)** | `105` | `0.259854` (`HOLDOUT-DTI`) | `[0.245717, 0.272312]` | `0.259854` | `-0.007928` `[-0.011433, -0.004251]` | `+0.015253` `[+0.010562, +0.019935]` | `0.2633` / `0.3326` / `0.1705` / `0.3065` | `39,586` |
| **`S17-CDSC E3` (`E2 + H17-4` Pure-Sub Pool)** | `105` | `0.252062` (`HOLDOUT-DTI`) | `[0.236185, 0.267198]` | `0.252062` | `-0.015720` `[-0.019605, -0.012662]` | `+0.007461` `[+0.001785, +0.012993]` | `0.2602` / `0.3266` / `0.1604` / `0.2969` | `38,096` |
| `S13-PTHA E3` (Stage-1 Local Base) | `75` | `0.244601` (`HOLDOUT-DTI`) | `[0.230592, 0.257058]` | `0.244601` | `-0.023181` | `0.000000` (reference) | `0.2439` / `0.3125` / `0.1615` / `0.2923` | `43,190` |
| `S15-SCGF E2` (Prior Dual-Specialist Lane) | `137` | `0.240633` (`HOLDOUT-DTI`) | `[0.227931, 0.254026]` | `0.240633` | `-0.027149` `[-0.032879, -0.021164]` | `-0.003968` `[-0.009911, +0.002292]` | `0.2542` / `0.2732` / `0.1695` / `0.2899` | `39,540` |

---

## 3. Root-Cause Diagnosis: Why `S17-CDSC E1` (`0.259972`) Jumped `+0.019339` Over `S15-SCGF` Yet Trailed `S14-PTAC E2` (`0.267782`) by `-0.007810`

1. **Why `S17-CDSC E1` Beat `S15-SCGF E2` by `+0.019339` and `S13-PTHA E3` by `+0.015371`:**
   - Removing the `3 km` GDR kernels and `15 km` `S12` regional bowls from Stage-1 restored Stage-1 OOF from `0.220480` (`S15-SCGF`) to `0.244601` (`S13-PTHA`).
   - Calibrating the 2-quadrant pairwise sub-models (`pi_sample ~ 0.107–0.168`) to each fold's 3-quadrant training sample prevalence (`0.150–0.179`) before stitching eliminated the `NE` fold starvation (`6,500 -> 10,621` dots; `NE` fold DTI `0.2732 -> 0.3314`).
2. **Why `S17-CDSC E1` (`0.259972`) Finished `-0.007810` Below `S14-PTAC E2` (`0.267782`) (`IR-91-S17-01` & `IR-91-S17-02`):**
   - **`IR-91-S17-01` (Upward Training-Canvas Calibration Tightens Training-Calibrated $\lambda^*(\text{Train}_q)$):**
     In `S14-PTAC`, the 2-quadrant training sub-models `pairs[tp]` were left uncalibrated (`pi_2quad < pi_3quad`), so at Stage-2 test time `s13_oof[q]` (`pi_3quad`) was slightly warmer than `Train_q`, allowing `43,633` OOF dots to pass $\lambda^*(\text{Train}_q)$. In `S17-CDSC`, calibrating `pairs[tp]` *upward* to `pi_3quad` warmed `Train_q`'s auto-context features while `Test_q` stayed fixed; because Stage-2 is fitted on `Train_q`, its in-sample predictions on `Train_q` rose slightly relative to `Test_q`, raising $\lambda^*(\text{Train}_q)$ and pruning `3,511` valid marginal dots (`43,633 -> 40,122`, including `-1,839` dots in `SW`). Moreover, `SE` still exhibited a `1.4290x` `Test/Train` ratio due to heterogeneous quadrant fault density (`NW=10,757`, `NE=12,051`, `SW=20,541`, `SE=17,639`). **Remediation for next session:** apply per-quadrant empirical quantile / rank-logit standardization to `stitch_p1` inside each quadrant `m` before running `compute_spac_autocontext_features`, guaranteeing exact `1.000x` `Test_k / Train_k` distribution equality across all 4 quadrants.
   - **`IR-91-S17-02` (Stage-2 Feature-Width Dilution in Fixed-Leaf Trees):**
     Adding `+20` columns to Stage-2 (`85 -> 105` features) while holding `max_leaf_nodes = 41` (`hgb_deep`) and `23` (`hgb_shallow`) fixed diluted root splits on `ac_wash_bridge_1km`, `ac_wash_bridge_2km`, and `ac_corridor_1p2km`. **Remediation for next session:** train a dedicated 14-column Stage-2 **Topology Specialist** (`hgb_topo`) solely on `S17_AUTOCONTEXT_NAMES` + `ptha_crest` and pool its calibrated log-odds with `PTAC`'s 85-feature Stage-2 ensemble.

---

## 4. Rule 1 Uniqueness, Rule 4 Canary & Automated Validator Audit

| Gate / Check | Measured Value | Threshold / Contract | Status |
|---|---|---|---|
| **Rule 4 Single-Feature Leakage Canary (`105` features)** | `max symmetric AUC = 0.74521` (`ac_p1_raw`) | `<= 0.90` on all 105 features | **PASS** |
| **Pre-Placement Continuous Surface Spearman `|\rho|` (`85` rasters)** | `0.22274` (`calib_hedgev2_01563_sample.tif`) | `<= 0.90` | **PASS** |
| **Final 3-px Dot Overlap vs `GEMSDOE32` `R0` (`h33-2-b2`)** | `0.43761` (`43.76%` directed; `45.18%` F1; Spearman `0.06672`) | `<= 0.70` | **PASS** |
| **Final 3-px Dot Overlap vs All `48` External Non-Calibration Fleet Submissions** | `0.53164` (`53.16%` vs `19GEMSDOE__h19-4`; Spearman `0.14944`) | `<= 0.70` | **PASS** |
| **Final 3-px Dot Overlap vs Prior `GEMSDOE91` `S14-PTAC E2` (`docs/downloads`)** | `0.95198` (`95.20%` — shared `S13` Stage-1 base) | `<= 0.70` | **FAIL (Internal Sibling)** |
| **Literal All-Indexed 3-px Dot Overlap (`85` rasters, zero exemptions)** | `0.99834` (`99.834%` vs `calib_r13lattice_00904.tif`, `206,895` dots covering `99.87%` of Nevada) | `<= 0.70` | **FAIL-CLOSED (`STOPPED_DUPLICATE`)** |
| **Grid, CRS, Transform, `float32`, `[0, 1]`, `nodata=None`, `0` NaNs (`12,279,160` cells)** | `EPSG:32611`, `(3730, 3292)`, `(100, 0, 243350, 0, -100, 4508550)`, `[0.0, 1.0]`, `44,000` dots, `min_cat_dist = 3.1623 px` | 5 independent validator suites (`gems91.gates`, `release_gates`, `validate_raster`, `gems57`, `tifffile`) | **PASS (`CERTIFIED`)** |
| **Blind Off-Catalogue USGS SGMC Control (`62,122` positives)** | `0.093019` (`E1`), `0.093008` (`E3`), `0.081861` (`Pure-Subsurface Specialist alone`) | Diagnostic control (never leaderboard) | **RECORDED** |
