# Session 27 (`S27-CVDC`) Three-Pass Review Report

- **Branch:** `arena/2d335bdc-gemsdoe91`
- **Date (UTC):** `2026-10-29`
- **Preregistered Lane:** `S27-CVDC` (`docs/s27/preregistration.md`)
- **Primary Artifact:** `docs/downloads/gems91-s27-cvdc-e2-37654dots-20261029T153044Z-c9ef43d5-zeros.tif`
  - **SHA-256:** `fc77890797ae076d5e9be023bd1405541b4d4c0b2fc3754e07da5c45d11554a0`
  - **Single-TIFF ZIP SHA-256:** `532dc4d52f57508a615463fed0ae3a42f5c94fe095dd99dfba850f11781521cb`
- **Automated Verdict:** `OK TO DOWNLOAD: YES — RESEARCH ONLY` · `OK TO SUBMIT: NO` (`verdict: "negative"`, `0` live submission slots used, `3` of `3` budgeted experiments executed)

---

## Pass 1 — End-to-End Research, Implementation & Verification

1. **Prior-Session Next Steps Completed First (`LIMITATIONS_AND_NEXT_STEPS.md`):**
   - Diagnosed why `S25-FABRIC E2` (`0.147741` v3 `HOLDOUT-DTI`) suffered `45.9%` 3–5 px catalogue collar hugging, `74.89%` competitive overlap vs `bhar-e3`, depressed blind SGMC (`0.079042`), and depressed post-hoc LFI (`0.07917`): `scripts/run_s25_fabric.py` refit HGB *in-sample* on all `60,988` pixels of `existing_faults.tif` (`final_surface()`) and used simple greedy NMS instead of `300 m` triangular-kernel submodular optimization.
   - Remediated both defects in `S27-CVDC` by emitting **strictly from the stitched 4-fold spatially-buffered `v3` OOF surface** (zero in-sample catalogue refitting) through a `300 m` triangular-kernel CELF submodular emitter (`cvdc27.emit_dots_celf_submodular`).
2. **Official Literature & Data Verification (`docs/s27/GEOTHERMAL_AND_FAULT_RESEARCH.md`):**
   - Fetched live DrivenData public leaderboard (`2026-10-29`: `#1 = 0.4544` `xiaofanhu`, `#2 = 0.3916` `cfld__`, `#5 = 0.3642` `op01`, `#10 = 0.3405` `zeaal`), official problem/metric pages, Official Rules PDF (`NLR/DOE 96647.pdf`), USGS GeoDAWN (`10.5066/P93LGLVQ`), OpenEI GDR 1391 (`10.15121/1881483`), and GBCGE INGENIOUS documentation.
   - Conducted label-blind finite-difference verification of all 19 bands (`docs/s27/band-identity.json`): verified `B06` exclusion (`IR-8E8-09` radiometric Total Count), `(B18, B11)` as horizontal gravity derivatives `(dx B13, dy B13)` (`r = +0.9481`, `+0.9380`), and `B15` as depth to MT conductive base (`IR-S22-09`).
   - Delivered PhD forensic proof of `GEMSDOE32 = 0.2778` (`H19-5` continuous posterior -> `d2.8` Poisson thinning -> `2.0 px` visible-fault collar pruning removing `2,545` pure `FP_w` dots at `TP_w ≈ 5,073`) and proposed 4 ranked novel geological hypotheses (`H27-1 CVDC`, `H27-2 PMDB`, `H27-3 VCTK`, `H27-4 External 1-m USGS 3DEP LiDAR`).
3. **Implementation & Experimental Results (`src/gems91/cvdc27.py`, `scripts/run_s27_cvdc.py`):**
   - `235` single-feature leakage canary checks (`47` features × `4` v3 quadrant folds + pooled): **100% PASS** (`max_symmetric_auc = 0.7403 <= 0.90`).
   - `E1` (`cvdc_e1_stage1_nms`): **`0.164007 [0.146397, 0.183228]`** (`+0.017995 [+0.003278, +0.031695]` vs `control_s25_fabric_e2`).
   - `E2` (`cvdc_e2_stage2_submod`, **selected**): **`0.169391 [0.150545, 0.188903]`** (`+0.023379 [+0.007929, +0.039110]` vs `control_s25_fabric_e2`; `+0.049118 [+0.034698, +0.063542]` vs `control_oof_base`).
   - `E3` (`cvdc_e3_stitched_uniq_submod`): **`0.168921 [0.149937, 0.188362]`** (`+0.022909 [+0.007375, +0.038851]` vs `control_s25_fabric_e2`).
   - Post-hoc diagnostics (`docs/s27/diagnostics.json`): blind USGS SGMC off-catalogue DTI **`0.095190`** (vs `S25 = 0.079042`, `+20.4%`, matching `GEMSDOE32 = 0.095386`); 3–5 px collar fraction **`9.8%`** (down from `45.9%`, `med_dcat = 21.63 px`); post-hoc LFI `MODEL_PROJECTION_NOT_A_SCORE` **`0.17747`** (`ridge1`, vs `S25 = 0.07917`, `+124.2%`).

---

## Pass 2 — Critical Review for Bugs, Edge Cases, Assumptions & Fixes

1. **Bug Found & Fixed — Floating-Point Underflow in Masked Gaussian Blur (`src/gems91/cvdc27.py`):**
   - *Issue:* Standard `gaussian_filter` on large-offset bands (`B12 ~ 1500 m`, `B14 ~ -1000 nT`) with infinite Gaussian tails leaked `~3e-4` across injected NoData boundaries due to `float32` subtraction cancellation and infinite-support boundary proximity.
   - *Fix:* Implemented median-centered `float64` normalized convolution with compact `truncate=3.0` kernel support and `ceil(3 * sigma) + 1` support erosion (`_masked_blur32`), proven bitwise invariant (`max diff = 0.0`, `equal_nan=True`) across all `34` static features under `-3.4028235e+38`, `+9.9e37`, and `NaN` sentinel injection (`tests/test_s27_cvdc_unit.py`).
2. **Irregularity Caught & Handled — `14GEMSDOE` Synthetic Geotransform (`IR-S27-01`):**
   - *Issue:* `data/lfi_anchors/14GEMSDOE__GEMS_r5-geom-horse-ensemble_...tif` carries a synthetic geotransform `[100, 0, 500000, 0, -100, 4500000]` instead of `[100, 0, 243350, 0, -100, 4508550]`.
   - *Fix:* Kept strict exact-geotransform enforcement on `reference_array` and logged `14GEMSDOE` explicitly under `skipped_grid_mismatch` in `docs/s27/frozen-registry.json` and `IRREGULARITIES.md`.
3. **Path Split Caught & Resolved — Nine-Site Restore Path (`IR-S27-02`):**
   - *Issue:* `verify_nine_site_leaders.py` restores the nine focus leaders to `data/nine_site_leaders/GEMSDOE{XX}__*.tif`, whereas `docs/s22/nine-site-audit.json` references `data/s22-nine-sites/GEMSDOE{XX}.tif` (which caused `S25`'s `freeze_references` to miss the `local_path` entries unless separately copied).
   - *Fix:* Populated `data/s22-nine-sites/` with SHA-256 verification and indexed `render_s27_portal.py` by `site` tag across deduplicated SHA-256 reference records so all nine leaders (`GEMSDOE24`–`GEMSDOE36`) are verified byte-by-byte (`0` missing nine-leader entries).
4. **Accessibility & Mobile Overflow Hardening (`scripts/render_s27_portal.py`, `tools/browser/smoke.cjs`):**
   - *Issue:* Long SHA-256 hashes and filenames inside `<table>` cells can cause horizontal overflow on `390 x 844` mobile viewports, and `s27/executive-summary.html` was not yet in the `axe-core` WCAG 2.1 AA scan loop.
   - *Fix:* Added `.table-wrap { overflow-x: auto }` and `overflow-wrap: anywhere` on `td`/`code`, and added `'s27/executive-summary.html'` to the `axe-core` WCAG 2.1 AA audit, mobile `390 x 844` overflow check, and real Chromium click-download SHA-256 verification in `tools/browser/smoke.cjs`.
5. **File Mode Hardening (`IR-91-S17-LFTG-02`):**
   - *Issue:* `vendor/gems57/submission_writer.py` stages files via `tempfile.mkstemp` (`0600` mode), which breaks static HTTP serving if left `0600`.
   - *Fix:* `scripts/run_s27_cvdc.py::cmd_package` explicitly sets `0o644` on `.tif`, `.zip`, and `.json` immediately after writing; verified `-rw-r--r--` on disk and via real Chromium download.

---

## Pass 3 — Full Re-Check Against User Prompt & Verification Suite

| Prompt Requirement | Deliverable & Verification Status |
|---|---|
| Work on previous sessions' next steps first | Remediated `S25-FABRIC` in-sample refit & emission geometry (`45.9% -> 9.8%` 3–5 px hugging; `74.89% -> 56.81%` competitive overlap; `+0.023379` paired `HOLDOUT-DTI` gain). |
| Focus on 9 target sites (`GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36`) + fleet (`GEMSDOE91`, `GEMSDOE92`) | Byte-verified all 9 leaders + `GEMSDOE91`/`92` (`docs/s27/executive-summary.html` Table 2, `README.md`, `docs/s27/final-dot-checks.json`). |
| PhD-level explanation of why `GEMSDOE32` hit `0.2778` & how to beat `0.2778` / `>0.3195` | Derived mathematically in `docs/s27/GEOTHERMAL_AND_FAULT_RESEARCH.md` §2 and `docs/s27/executive-summary.html` §3 (`ΔFP_w = -2,545`, `TP_w ≈ 5,073`). |
| Deep scientific research on geothermal vents & hidden faults with verified links | Stored in `docs/s27/GEOTHERMAL_AND_FAULT_RESEARCH.md` with verified USGS, OpenEI GDR, NLR/DOE, GBCGE, and peer-reviewed DOIs. |
| 3–5 novel untried geological hypotheses ranked by expected DTI gain & cost | `4` ranked hypotheses (`H27-1 CVDC`, `H27-2 PMDB`, `H27-3 VCTK`, `H27-4 USGS 3DEP 1-m LiDAR`) in `docs/s27/GEOTHERMAL_AND_FAULT_RESEARCH.md` §4 and `docs/s27/preregistration.md`. |
| Generate a **unique** `[0, 1]` `.tif` matching `sample_submission.tif` (`EPSG:32611`), unique name, `<=140`-char note | `gems91-s27-cvdc-e2-37654dots-20261029T153044Z-c9ef43d5-zeros.tif` (`138 KB`, `EPSG:32611`, `3730x3292`, `[0,1]`, `0` NaN, note `110/140` chars, `44.37%` max vs 9 leaders, `56.81%` max vs 180 competitive rasters). |
| Automated validation without human inspector; obvious top-of-site download & status + submission guide | Automated gates in `run_s27_cvdc.py`, `audit_downloads.py`, `check_artifact_policy.py`, `verify_frontdoor.py`, `smoke.cjs`; prominent top callout on `docs/index.html`, `docs/executive-summary.html`, and `docs/s27/executive-summary.html`. |
| Parallel-Run Protocol (Rule 1 duplicate gate, Rule 2 shared tools, Rule 3 strict score labels, Rule 4 canaries `<=0.90`, Rule 5 JSON Run Card, Rule 6 `<=3` exps / 0 slots) | Verified end-to-end (`docs/s27/run-card.json`, `docs/s27/canaries.json`, `vendor/gems57` unmodified). |
| Put prompt into `README.md` for future sessions | Preserved under `#full-project-brief` with `2026-10-29` Session 27 delta appended. |
| 3 passes, PR + merge to `main`, document remaining limitations & next steps | Documented in `docs/s27/REVIEW.md` and `LIMITATIONS_AND_NEXT_STEPS.md`. |
