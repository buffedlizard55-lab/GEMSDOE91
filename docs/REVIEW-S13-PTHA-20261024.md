# Three-Pass Audit Record — Session 13 (`S13-PTHA`, 2026-10-24, `arena/6a62c2ab-gemsdoe91`)

## Pass 1 — Complete Implementation, Pre-Registration, Validation & Portal Build

- **Prior-Session Action Items Executed First:**
  - Resolved `IR-91-S12-04` via label-blind `scripts/verify_band06_and_units.py` (`evidence/s13_band06_and_units_audit.json`): `Band 06 (tc)` = GeoDAWN Radiometric `TC` (`r = 0.996990` across `5,164,300` footprint pixels).
  - Discovered and fixed `IR-91-PTHA-01`: `Band 03 (tmi_hg)` is `2 * ||grad_px(Band 14)||` in `nT/200m` (`r = 0.999991`) vs `Band 09 (tmi_vg)` in `nT/m` (`200×` scaling mismatch).
  - Fixed `IR-91-S12-05` (`scripts/run_h91_lane.py` `CLAIM` labelling), `IR-91-S12-07`, and `IR-91-S12-12` (`scripts/run_s11_lane.py` fallback memmap & collision-safe `s11_submission_bundle.js`).
- **Pre-Registration & 3-Experiment Execution (`docs/HYPOTHESES_S13.md`, `scripts/run_s13_lane.py`):**
  - Ranked 5 novel hypotheses (`H13-1`..`H13-5`) before running any holdout experiment; froze `E1`, `E2`, `E3` (`sha256=505e45d1b668eb5c27f241024ad83a5c429f5d986e6743d230473c2d515810dc`).
  - Verified all 75 features pass single-feature leakage canary (`max symmetric AUC = 0.66470 ≤ 0.90`).
  - Evaluated `E1 = 0.197522`, `E2 = 0.198407`, and **`E3 = 0.244601 HOLDOUT-DTI`** (`95% CI [0.230592, 0.257058]`, paired delta `+0.038195` vs `S11-MHTR E2 = 0.206406`, `95% CI [+0.029931, +0.046719]`, `400/400` positive draws; also `+0.007014` above concurrent `S12-SPAC E3 = 0.237587`) plus **`0.100815` Blind Off-Catalogue USGS SGMC DTI** (`#2` in repo behind `S12-SPAC E3 = 0.107938`, ahead of `S12-BHAR = 0.100094`, `S11-MHTR = 0.097623`, and `R0 = 0.095386`).
  - Generated `docs/downloads/gems91-s13-ptha-e3-20261024T201500Z-660d645d-zeros.tif` (`235,134 B`, `44,000` dots, `[0, 1]` all-finite, `nodata=None`) and `.zip` (`199,478 B`).

## Pass 2 — Bug, Edge-Case, Accessibility, Mobile Overflow & Post-Merge Consistency Fixes

1. **`tests/test_s13_ptha.py` API alignment:** Aligned unit test calls with exact `PTHA._detect_1d_directional_ridge`, `PTHA.prior_shift_calibrate_surface`, `PTHA.dinkelbach_full_map_emit`, and `docs/run-card-S13.json` schema keys.
2. **Mobile `390×844` horizontal overflow fix (`scripts/render_portal.py`):** Headless Chromium (`tools/browser/smoke.cjs`) caught a 15-px horizontal overflow (`right = 405 px > 390 px`) on `docs/s13-ptha.html` caused by unwrapped backticked path text inside `<strong>` and grid items missing `min-width: 0`. Added `.hero>div,.twocol>div,.step>div{min-width:0;overflow-wrap:anywhere}` and `<code>evidence/s13_band06_and_units_audit.json</code>`. Re-tested: `mobile_overflow = false` across all pages.
3. **WCAG 2.1 AA form-label fix (`scripts/render_portal.py`):** `axe-core` caught a missing `<label for="s13-exec-note">` on `docs/s13-ptha-executive-summary.html`. Added explicit accessible `<label>`; re-tested: `0` WCAG 2.1 A/AA violations across all audited pages.
4. **Concurrent `origin/main` integration (`PRs #54..#59`):** Reconciled `S13-PTHA E3` cleanly with newly merged `S12-SPAC`, `S12-BHAR`, `SPID91`, `G91-COVER`, and `S13-review` without dropping any concurrent lane, measured post-merge intra-repo overlaps (`84.13%` vs `S12-SPAC`, `73.30%` vs `S12-BHAR`, `70.59%` vs `SPID91`, `53.21%` vs `G91-COVER`), updated SGMC rank text accurately (`#1 HOLDOUT-DTI = 0.244601`; `#2 Blind SGMC = 0.100815` behind `S12-SPAC = 0.107938`), and namespaced irregularity IDs to `IR-91-PTHA-01..03`.

## Pass 3 — Full Prompt & Protocol Re-Verification

- **Original user prompt stored intact in `README.md`:** Verified (`## Original user project brief (standing guidance)` preserved verbatim; `test_delivery_verification.py` PASS).
- **Unique `.tif` in `[0, 1]` with zero NaNs & matching `EPSG:32611` `(3730, 3292)` affine:** Verified across all 5 automated validator suites and real headless Chromium browser download (`sha256 = 421c589072e3b959fc0f8e71a7e879822ce8f9a81172a7f0fd24e7932eadd452`).
- **Obvious top-of-site download + automated submission verdict + executive summary step-by-step guide:** Verified on `docs/index.html`, `docs/executive-summary.html`, `docs/s13-ptha.html`, and `docs/s13-ptha-executive-summary.html` (`OK TO DOWNLOAD: YES` for research / selector review; fail-closed `NOT OK TO SUBMIT` automatically until human selector signs off).
- **Parallel-Run Protocol Rules 1–6:** All verified (`3` experiments, `240.19 s`, zero live slots spent, single JSON RUN CARD emitted).
