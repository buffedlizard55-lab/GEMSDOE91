# Session 18 (`S18-CWGR`) Three-Pass Scientific & Engineering Review (2026-10-25)

- **Branch:** `arena/892fab6a-gemsdoe91`
- **Declared Lane:** `S18-CWGR` (*Completeness-Weighted Steerable Quadrature & Byerlee–Sibson Fault-Valve Tri-Specialist Hierarchy*)
- **Frozen Preregistration:** `docs/HYPOTHESES_S18_CWGR.md` (`sha256: c6d217d6711bdbbfb34540df7618effeff0522a7b9f5424abcd93424d6432eba`)
- **Deliverable GeoTIFF:** `docs/downloads/gems91-s18-cwgr-e1-20261025T193926Z-5be5918b5733-zeros.tif` (`145,655 B`, `sha256: 5bbc888008da8bb08d07c48fcae4ee3eea395119a8f2728a1874ddf800608d56`)
- **Single-TIFF ZIP:** `docs/downloads/gems91-s18-cwgr-e1-20261025T193926Z-5be5918b5733-zeros.zip` (`112,059 B`, `sha256: 442094745e83418dd79eb69ee370f4287a96d43f3fd08728cdf8729cd8219403`)
- **Machine Run Card:** `docs/run-card-S18-CWGR.json`
- **Automated Verdict:** **`OK TO DOWNLOAD: YES — RESEARCH ONLY` · `OK TO SUBMIT: NO` (`verdict: negative`, `slots_used: 0`)**

---

## 1. Forensic Diagnosis of `GEMSDOE32` (`0.2778` USER-REPORTED CLAIM) & Leaderboard Gap

1. **Evidence hygiene:** `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`0.2778` `USER-REPORTED CLAIM`; `GEMSDOE32`'s own site labels the file `UNSCORED` with a `0.2747` model projection; `ORGANIZER-CONFIRMED: null`) sits below the public DrivenData #306 leaderboard rank #1 (`xiaofanhu = 0.4413`, observed 2026-10-25, superseding an earlier `0.3195` snapshot).
2. **Four-step physical & geometric mechanism:**
   - **`h16-1 -> h19-5` (`0.1855 -> 0.1922` USER-REPORTED):** Catalogue-blind multi-physics Hessian/tilt crest network (`121,131` px across `26,645` segments, `70.0%` of mass `> 1 km` from `existing_faults.tif`, achieving **`0.088516 BLIND-SGMC-CONTROL-DTI`** on `56,822` off-catalogue USGS DS-1052 bedrock faults).
   - **`d2-8` (`0.1922 -> 0.2600`, `+0.0678` USER-REPORTED):** Greedy `2.8 px` (`280 m`) Poisson-disk thinning (`121,131 -> 44,090` binary dots) cuts false-positive mass (`α = 0.2`) by `63.6%` while retaining `> 93%` of `300 m` triangular kernel coverage (`β = 0.8`).
   - **`solo -> h33-2-b2` (`0.2600 -> 0.2708 -> 0.2778`, `+0.0178` USER-REPORTED):** Deleting `3,891` dots at `d = 1.0 px` and `2,545` dots at `√2 <= d <= 2.0 px` from `existing_faults.tif` leaves **`37,654` binary dots**, purging dead-weight FP mass inside the unrewarded digitization halo of masked known faults.
3. **Can `0.2778` (and `0.4413`) be beaten?** Algebraic Tversky inversion shows `GEMSDOE32 R0` achieves `~0.38` weighted recall of unmapped expert faults at `~2.4x` FP-to-truth ratio, whereas `0.4413` requires `~0.62` weighted recall at the same budget. Beating both requires improving subsurface blind-fault localization precision while preserving regional tectonic extension prevalence — not emitter spacing tuning alone.

---

## 2. Three-Pass Audit Summary

### Pass 1 — Preregistration, Implementation & Execution
- Froze `registry/s18_comparison_inventory.json` (`108` SHA-256-verified rasters, `99` unique SHA-256, `0` missing on disk) and `docs/HYPOTHESES_S18_CWGR.md` (`H18-1`..`H18-4`) before writing code.
- Implemented `src/gems91/cwgr18.py` (`18` novel features, streaming `<3.50 GB` peak RSS inside the `3.8 GiB` / `0 B` swap sandbox) and verified `0.0` bitwise perturbation invariance to zeroing topographic Bands 12 & 19 across all 15 subsurface columns (`0..14`).
- Scored all 8 primary arms (`gravity_control`, `s16_pgrd`, `ced91`, `incumbent_ptac_lb`, `cpad_e1`, `cwgr_e1`, `cwgr_e2`, `cwgr_e3`) + 3 fixed `37,654` area-quota controls (`IR-91-S18-02`) on unchanged `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `60,988` withheld positives), `174 x 4` leakage canaries (`max pooled symmetric AUC = 0.688170 <= 0.90`), `BLIND-SGMC-CONTROL-DTI` (`56,822` px), and `108`-raster novelty; wrote `gems91-s18-cwgr-e1-20261025T193926Z-5be5918b5733-zeros.{tif,zip}` via unchanged `vendor/gems57/submission_writer.py`.

### Pass 2 — Code, Math, Edge-Case & Governance Bug Fixes
1. **Steerable quadrature step-crest phase fix:** Replaced `(G_2, √0.4·G_3)` with Freeman–Adelson odd/even `(G_1^\phi, 0.78·G_2^\phi)` quadrature because `G_2(0) = 0` vanishes at odd step inflections.
2. **Outside-`predict_mask` residual odds leak fix:** Explicitly zeroed `cal_surf[~predict_mask] = 0.0` after `calibrate_reference_odds_surface` so `1e-6 * odds_mult` background floors never leak outside target fold regions; verified `S17-CGRD`'s cross-fold `val_mask` leak (`IR-91-S18-01`) cannot occur.
3. **Submodular centerline kernel & `3.8 GiB` RAM streaming fixes:** Set `K_anchor[3, 3] = 2.35 > 1.0` so oblique (`N18E`) ridges peak strictly on fault centerlines (`mean offset < 0.75 px`), streamed single bands into `X_cwgr.f32.mmap`, cached per-fold emitted dots, and reused `pre_reg["comparisons"]` in `compute_exhaustive_diagnostic_overlaps`.
4. **Run-card & schema consistency fixes:** Corrected Stage-2 column description (`174-col` Full + `129-col` Pure-Subsurface + `28-col` Topology) to match `docs/s18/features.json` and `174` canaries; added `raster_path` and `result` for `test_s16_integrity.py` and `_registered_pair`; updated `docs/sources.json` dead branch URLs to `main`; logged `IR-91-S18-01`..`04` in `IRREGULARITIES.md`; added 5 Pass-2 regression & constant/empty-quadrant edge-case tests to `tests/test_s18_cwgr.py`.

### Pass 3 — End-to-End Independent Verification
- Re-verified `gems91-s18-cwgr-e1-20261025T193926Z-5be5918b5733-zeros.{tif,zip}` via `scripts/verify_s18.py --with-data`, `generate_submission.py --with-data`, `scripts/audit_downloads.py`, `scripts/check_artifact_policy.py`, full `pytest` suite, and real headless Chromium `153.0.8010.0` `tools/browser/smoke.cjs` (`0` HTTP/console errors, `0` WCAG 2.1 AA violations across 26 pages, `0` mobile overflow at `390×844`).
