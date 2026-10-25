# Three-Pass Verification Review — Session 17 (`S17-CPAD`, 2026-10-25)

**Branch:** `arena/aecf32eb-gemsdoe91`  
**Artifact:** `docs/downloads/gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif` (`.zip`, `.json`)  
**GeoTIFF SHA-256:** `690c10998798d3abd54f6a1ec1c12e56c4243d1967ede7b63a533b9ddd628cdd`  
**Automated Verdict:** **`OK TO DOWNLOAD: YES (research / audit)`** · **`OK TO SUBMIT: NO` (`verdict: "negative"`, `slots_used: 0`)**

---

## Pass 1 — Preregistration, Forensic Repair, Implementation & End-to-End Execution

1. **Prior-session handoff priorities executed first:**
   - Restored and SHA-256 verified all 15 competition and external public inputs (`sample_submission.tif`, `existing_faults.tif`, `gems-geodawn-numerical-features.tif`, GDR #1562 WellSpring CSV, USGS DS-1052 SGMC, GeoDAWN K/U/Th radiometrics, 100 m LiDAR scarp features) plus all 95 comparison-registry rasters (`registry/s17_comparison_inventory.json`, `0` missing).
   - Refreshed the 92-repo GitHub snapshot inventory (`docs/fleet-audit.json` at `2026-10-25T13:32:27Z`; `0` organizer-confirmed receipts) and verified commit `aebe92f7` of `drivendataorg/gems-prize-reference-solution` and commit `012e17b2a1` of `buffedlizard55-lab/GEMSDOE32` (`UNSCORED`).
   - Audited legacy Sessions 13–16 line-by-line and documented three critical irregularities in `IRREGULARITIES.md`:
     - **`IR-91-S17-01`:** `scripts/run_s13_lane.py:87` (`_fold_active_and_eligible`) leaked `~fold.buffer_mask` (an 8-km oracle moat around withheld truth) into test-time dot placement, inflating `S14-PTAC E2` from `0.194221` (strict label-blind `spatial.folds`) to `0.267782`.
     - **`IR-91-S17-02`:** Hidden `Band 12`/`Band 19` topographic dependencies inside `S14-PTAC` (`ptac_playa_mask_baffle`) and `S15-SCGF` (`hvdc_playa_cap_cond` + 6 `e1_*`/`ptha_*` features) caused nonzero sensitivity in nominal "subsurface" specialists.
     - **`IR-91-S17-03`:** `gdr_wellspring_in_footprint.csv` contains a precomputed `dist_known_fault_px` column that must be programmatically banned.
2. **Preregistration before implementation (`docs/HYPOTHESES_S17_CPAD.md`):**
   - Preregistered 5 ranked geological hypotheses (`H17-1`..`H17-5`) with exact data layers, physical signatures, why missing from USGS/INGENIOUS catalogues, named non-fault mimics, distinction from prior repo methods, and expected DTI gain vs compute cost.
3. **Implementation & 3-experiment bounded run (`src/gems91/cpad17.py`, `scripts/run_s17_cpad.py`):**
   - Implemented 16 novel `CPAD` features (`14` subsurface columns verified bitwise `0.0` invariant to `Band 12`/`Band 19` perturbations + `2` exogenous cover-gating columns) and Dual-Specialist cross-fitted Auto-Context (`128` full / `100` subsurface columns) with training-domain Bayes reference-odds calibration (`c0 = 12.0`).
   - Scored all 3 preregistered arms (`cpad_e1`, `cpad_e2`, `cpad_e3`) plus `incumbent_ptac_lb`, `ced91`, `s16_pgrd`, and `gravity_control` on unchanged `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2`, `60,988` withheld positives, `80 px` buffer, `1,000` × 20-km paired block-bootstrap draws):
     - **`cpad_e1` = `0.198183 HOLDOUT-DTI` (`95% CI [0.177759, 0.217830]`)** — highest strict label-blind `gems57-pooled-hide-v2` score in `GEMSDOE91` (`+0.003962` over `incumbent_ptac_lb = 0.194221`; `+0.127296` over `ced91 = 0.070886`; `+0.128786` over `s16_pgrd = 0.069397`), plus **`0.068585 BLIND-SGMC-CONTROL-DTI`** (`+78.1%` over `s16_pgrd = 0.038501`).

---

## Pass 2 — Critical Bug, Assumption, Missing-Requirement & Edge-Case Audit

During Pass 2, every script, JSON receipt, validator, and HTML page was audited for hidden assumptions, prose/data mismatches, and edge cases:

1. **Caught & fixed post-stop prose inaccuracy in `scripts/run_s17_cpad.py` (`verdict_reason` & `byte_identity_caveat`):**
   - *Finding:* The initial template string assumed any `final_reg` `DUPLICATE` stop had occurred on a `calib_*` synthetic lattice after passing all 86 non-calibration files. Direct inspection of `docs/s17/registry-final.json` revealed `final_reg` actually passed rows `1..50` (`max 3-px overlap = 0.6168 <= 0.70`; `GEMSDOE32 R0 = 0.4927`) and stopped fail-closed at row **`51/95` (`data/fleet_registry/r11_greedy_mp.tif`, `272,853` positive pixels, `0.8725 > 0.70`)**, and diagnostic post-stop checks showed `0.8296` 3-px overlap with in-repo `S14-PTAC E2` (`0.1496` on `S16-PGRD`, `0.1353` on `CED91`).
   - *Fix:* Replaced the template string with exact computed counts (`passed_before_stop_count = 50`, `max_passed_overlap = 0.6168`, exact stopped filename/dot count/overlap, plus explicit `diagnostic_post_stop_3px_overlap` on milestone rows) without running a 4th experiment.
2. **Caught & fixed crop-slice indexing & `validate_raster` ledger argument:**
   - *Finding:* `vendor/gems57/spatial.folds` yields dicts with `'region'` boolean masks (no `'slice'` key), and `scripts/validate_raster.py` marks `sha_unseen` as `UNVERIFIED` when `ledger_csv=None`.
   - *Fix:* Computed bounding slices directly via `np.nonzero(fold['region'])` and passed `ledger_csv=ROOT / "ledger/submissions.csv"` so all three independent validator suites (`vendor/gems57/submission_writer`, `release_gates`, `validate_raster`) run cleanly.
3. **Caught CI static-build requirement for `s17-support.png` and `verify_s17.py`:**
   - *Finding:* `.github/workflows/pages.yml` runs `scripts/verify_s17.py` and `scripts/render_portal.py` without restoring gitignored `data/official/` or `data/fleet_registry/`.
   - *Fix:* Built `scripts/verify_s17.py` to verify all GeoTIFF/ZIP bytes, `tifffile`+`rasterio` grids, 7-arm holdout formulas, `148×4` canaries, and `95`-entry registry hashes in static mode (while supporting `--with-data` in `ci.yml`), and guarded `render_s17_portal.py:render_preview` so committed `docs/assets/s17-support.png` renders cleanly without `data/`.
4. **Added edge-case unit tests (`tests/test_s17_cpad.py`):**
   - Verified `NaN` / `+Inf` / `-Inf` / negative-value and `budget=0` sanitization in `emit_global_dots_nms` and `emit_global_dots_submodular`, bitwise `0.0` `Band 12`/`Band 19` invariance, `dist_known_fault_px` ban + row-order invariance, Bayes reference-odds cancellation, tamper-rejection in `verify_s17.py`, and preservation of `<a id="full-project-brief"></a>` in `README.md`.

---

## Pass 3 — End-to-End Re-Verification Against Standing Prompt

All acceptance criteria from the user prompt and `PARALLEL-RUN PROTOCOL` Rules 1–6 were re-verified from scratch:

- **Unique, competition-valid GeoTIFF in `[0, 1]` without human visual inspection:** `gems91-s17-cpad-e1-20261025T152830Z-0230f7494eeb-zeros.tif` (`145,258` bytes, single-band `float32`, `EPSG:32611`, `3730×3292`, affine `(100, 0, 243350, 0, -100, 4508550)`, `nodata=None`, `0` NaN/Inf across all `12,279,160` cells, values strictly `{0.0, 1.0} ⊂ [0, 1]`, `37,654` dots, `0` on catalogue, `72,590` pixels changed vs `GEMSDOE32 R0`, `min_spacing = 3.16228 px > 3.0`, `min_catalogue_distance = 3.16228 px > 3.0`) + byte-verified single-member `.zip`.
- **Protocol Rules 1–6:** 1 lane (`S17-CPAD`); shared `vendor/gems57` tools untouched (`test_shared_template_is_unmodified` PASS); strict `HOLDOUT-DTI` vs `ORGANIZER-CONFIRMED: null` / `CLAIM` labelling; `148/148` leakage canaries `<= 0.90` (`max = 0.677910`); complete JSON run card (`docs/run-card-S17-CPAD.json`); `3` experiments in `< 36` cumulative compute minutes (`< 2h` cap); `0` live slots spent.
- **Automated test, policy, & real-browser delivery suites (post-merge with `origin/main` `f006bf8`):**
  - `pytest` (full merged repository suite including `test_s17_cpad.py`, `test_s16_integrity.py`, `test_submission_portal.py`, `test_olc91.py`, `test_s17_eulr_integrity.py`, `test_s17_cdsc.py`, `test_s17_cgrd.py`, `test_xg91.py`, `test_geo91.py`, `test_drn91.py`, `test_download_audit.py`, `test_ced.py`): **PASS**.
  - `verify_current_artifact.py --with-data`, `verify_evidence.py`, `verify_s16.py --with-data`, `verify_s17.py --with-data`: **PASS**.
  - `audit_downloads.py` (`79` artifacts checked, `diff -u` clean against `docs/download-audit.{json,html}`) & `check_artifact_policy.py` (`79` registered artifacts, `0` raw data/caches tracked): **PASS**.
  - Real Chromium (`tools/browser/smoke.cjs` + `axe-core` WCAG 2.1 AA across `23` pages + `390×844` mobile overflow + SHA-256 one-click download checks, including fixing a latent `PR #109` link-text mismatch on `olc91-index-src.html` and CSS grid `min-width: 0` mobile overflow): **PASS (`0` violations, `0` HTTP/console errors)**.

---

## Post-Merge Cross-Lane Novelty Audit vs Incoming `origin/main` (`f006bf8`) Downloads

Post-merge comparison of `S17-CPAD E1` (`37,654` binary dots) against the parallel-session `docs/downloads/*.tif` rasters integrated from `origin/main` (`PRs #90..#109`, evaluated over off-catalogue footprint cells `fp & ~cat`):

| Incoming parallel lane | Dots | 3-px dot overlap (`<= 0.70`) | Final Spearman `rho` (`\|rho\| <= 0.90`) | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `OLC91 E1` (`gemsdoe91-olc91-e1-strikecoherent-37654-20261025-62d03e67.tif`) | `37,654` | `54.89%` (PASS) | `+0.0367` (PASS) | Distinct from catalogue-blind strike-coherent network |
| `DRN91 E2` (`gems91-drn91-e2-37654dots-20261025T134012Z-4a2e588a-zeros.tif`) | `37,654` | `56.07%` (PASS) | `+0.0302` (PASS) | Distinct from drainage-anisotropy lane |
| `GEO91 tiprelay` (`gems91-geo91-tiprelay-collar3-20261025T132242Z-zeros.tif`) | `37,654` | `44.08%` (PASS) | `+0.0213` (PASS) | Distinct from analytical tip-relay lane |
| `S17-CGRD E2` (`gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif`) | `37,654` | `37.94%` (PASS) | `+0.0234` (PASS) | Distinct from continuous gravity-dislocation dots (`0.092125` binary vs `0.198183` `S17-CPAD E1`) |
| `GEO91 E2 stratcover` (`gems91-geo91e2-stratcover-collar3-20261025T132527Z-zeros.tif`) | `37,654` | `31.87%` (PASS) | `+0.0146` (PASS) | Distinct from strat-cover collar lane |
| `DZEDGE` (`GEMS91-DZEDGE-20261025T021110Z-6b819d00-zeros.tif`) | `37,654` | `26.62%` (PASS) | `+0.0121` (PASS) | Distinct from damage-zone edge lane |
| `XG91 E1` (`gems91-xg91-e1-20261025T145301Z-3c1b8f6a-zeros.tif`) | `37,654` | `18.20%` (PASS) | `+0.0023` (PASS) | Distinct from cross-gradient lane |
| `Off-catalogue damagezone` (`gems91-unique-offcatalogue-damagezone-20261025T144238Z-b9acc119-zeros.tif`) | `8,718` | `12.55%` (PASS) | `+0.0079` (PASS) | Distinct from sparse off-catalogue damage zone |
| `H1-blind-damage-zone` (`GEMS91-H1-blind-damage-zone-20261025T000000Z-8626b7d4-zeros.tif`) | `37,654` | `6.67%` (PASS) | `+0.0261` (PASS) | Distinct from blind damage-zone lane |
| `S17-EULR E3` (`gems91-s17-eulr-e3-20261025T160000Z-76cc8d1a-zeros.tif`) | `44,000` | `74.73%` (STOP) | `+0.1215` (PASS) | Expected `S14`-proximity-corridor overlap (`44,000`-dot tip/relay family; reinforces `OK TO SUBMIT: NO`) |
| `S17-CDSC E1` (`gems91-s17-cdsc-e1-20261025T163000Z-500d26dd-zeros.tif`) | `44,000` | `82.26%` (STOP) | `+0.1509` (PASS) | Expected `S14`-proximity-corridor overlap (`44,000`-dot tip/relay family; reinforces `OK TO SUBMIT: NO`) |
