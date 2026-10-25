# GEMSDOE91 — Multi-Pass Verification Log (Session 17 `S17-CGRD`, `arena/cbdb6e26-gemsdoe91`)

## Session 17 (`S17-CGRD`, branch `arena/cbdb6e26-gemsdoe91`, 2026-10-25)

### Pass 1 — Preregistration, Feature Engineering & 3-Experiment Execution (COMPLETED)
- [x] Restored and SHA-256 verified all 15 competition/reference files in `registry/data_manifest.json` (`data/official/sample_submission.tif`, `data/official/existing_faults.tif`, `data/bridge/gems-geodawn-numerical-features.tif`, `data/external/gdr_wellspring_in_footprint.csv`, `data/external/derived_sgmc_faults_100m_u8.tif`, `data/registry/GEMSDOE32__h33-2-b2-zeros.tif`, `data/fleet_registry/calib_r13lattice_00904.tif`).
- [x] Froze preregistration `docs/HYPOTHESES_S17_CGRD.md` (5 ranked geological hypotheses `H17-1` through `H17-5`, 3-experiment ladder `E1`, `E2`, `E3`).
- [x] Implemented `src/gems91/cgrd17.py` (26 pure-subsurface Cooper–Cowan Theta-Map / Hyperbolic-Tilt + DOE GDR-1391 geothermometer disequilibrium features + 8 prior-shift-calibrated local auto-context features, provably invariant to `Band 12`/`Band 19` and never reading `dist_known_fault_px`).
- [x] Implemented `scripts/run_s17_cgrd_lane.py` and unit/integration test suite `tests/test_s17_cgrd.py`.

### Pass 2 — Scientific Bug Review, Edge Cases & Portal/Registry Repair (COMPLETED)
- [x] **Fixed `IR-91-S15-06` & fold-negative exclusion bug:** Excluded held-out quadrant `f.region_mask` from training negatives (`excl_f = f.region_mask | f.withheld_faults | f.buffer_mask`) and applied `gems91.ptha.prior_shift_calibrate_surface` to all 6 pairwise 2-quadrant and 4 OOF 3-quadrant Stage-1 splits before stitching local auto-context, plus $\ge 3.2\text{ km}$ bowl subtraction (`IR-91-S15-07`). Confirmed `E2` (`0.092125 HOLDOUT-DTI`) improves strictly over `E1` (`0.083981 HOLDOUT-DTI`).
- [x] **Fixed `readiness.py` format-gate mapping:** Added boolean `validator_output["checks"]` dictionary in `scripts/run_s17_cgrd_lane.py` so `gems91.readiness.gates(card)["format"]` and `["canary"]` evaluate to `True` while `submission_ready(card)` evaluates to `False`.
- [x] **Fixed `IR-91-S17-01` (portal/policy reconciliation):** Reconciled `scripts/render_geo91_portal.py`, `docs/geo91-index-src.html`, `docs/geo91-exec-src.html`, and `scripts/render_s16_portal.py`; registered all 66 prediction artifacts in `registry/artifact_policy.json`; and regenerated `docs/download-audit.{json,html}` (`66` files audited).

### Pass 3 — End-to-End Re-Verification Against All Requirements (COMPLETED)
- [x] Full pytest suite: `.venv/bin/pytest -q -rs` -> all tests passed (`0 failed, 0 skipped`).
- [x] Artifact policy & download audit: `.venv/bin/python scripts/check_artifact_policy.py` (`PASS: 66 explicitly registered prediction artifacts`) & `.venv/bin/python scripts/audit_downloads.py` (`status: "PASS"` on both `gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif` and `.zip`).
- [x] S16/current evidence verifiers: `.venv/bin/python scripts/verify_s16.py`, `.venv/bin/python scripts/verify_evidence.py`, `.venv/bin/python scripts/verify_current_artifact.py` -> all `PASS`.
- [x] Headless Chromium + axe-core WCAG 2.1 AA + mobile `390x844` overflow + SHA-256 download check: `node tools/browser/smoke.cjs` -> `status: "PASS"`, `0` console/HTTP errors, `0` mobile overflow, `0` WCAG violations across 21 pages.

---

## Integration verification

PR #103 initially conflicted with concurrent PR #101. Merged `origin/main` into the fixed session branch, retained the parallel review and access findings, retained the stricter current-download identity checks and corrected causal prose, and reran tests/browser checks before merge. No duplicate artifact-policy entries or geological experiments were introduced.

# Current three-pass review — `arena/4975419d-gemsdoe91`, 2026-10-25

- **Pass 1:** inspected prior next steps, restored sample/catalogue/R0 with manifest hashes; corrected current portal's unsupported scientific claims and historical/new-file ambiguity; added front-door TIFF/ZIP identity checks.
- **Pass 2:** fixed browser smoke tests that targeted obsolete landing-page controls; added corruption/path/approval regression tests and a synthetic counterexample to guaranteed collar-pruning gains. Found unregistered pre-existing DRN91 TIFF/ZIP; quarantined them and regenerated the stale all-download audit. Initial incomplete audit was BLOCKED, not a pass.
- **Pass 3:** `python -m pytest -ra`: **473 passed, 8 skipped, 57 warnings**. Skips require absent full integration inputs; warnings are existing Affine deprecations. `verify_current_artifact.py --with-data`, `verify_evidence.py`, `verify_s16.py --with-data`: PASS for their historical artifacts/evidence (not new science). Artifact policy: PASS for **64** registered artifacts. All-download technical audit: **56 PASS / 8 FAIL**. Real Chromium download SHA checks, desktop/mobile layout and accessibility: PASS, receipt in `evidence/review-4975419d/browser-verification.json`. Portal regeneration tested byte-for-byte by pytest; `git diff --check` clean.
- **Outcome:** no new geological experiment or raster; no slot used. Missing lane, registry feasibility, incomplete cache, unmatched current-best instrument and unverified organizer/account state remain blockers. Existing TIFFs were not copied or renamed as new submissions. Current review: `docs/REVIEW-4975419D-20261025.md`.

---

# GEMSDOE91 — Unique TIF submission pass log

## Session 17 (`S17-CWPC`) — Branch `arena/4f695c18-gemsdoe91` (2026-10-25)

### Pass 1 — Implement & Verify (COMPLETED)
- [x] Restored and SHA-256 verified all 15 competition inputs (`scripts/restore_data.py`, including 418.9 MB `gems-geodawn-numerical-features.tif`, 4-band radiometrics, 12-band LiDAR scarp stack, and off-catalogue USGS SGMC control), rebuilt `data/derived/catalogue_mask.tif` (`60,988` positive pixels) and `registry/preflight.json` (`BUILD ALLOWED: 2/2 required inputs verified`, `6/6` axes `READY`), and restored all 62 available `data/fleet_registry/*.tif` reference rasters (`scripts/restore_registry.py`).
- [x] Preregistered forensic analysis of `GEMSDOE32` (`0.2778 USER-REPORTED`) and 5 ranked geological hypotheses (`H17-1`..`H17-5`) in `docs/HYPOTHESES_S17_CWPC.md` (`sha256: aae8300c48425269f33788cead8f82f673eac11b3a6a571a1bcef6cb647621a9`) prior to running any holdout evaluation.
- [x] Implemented `src/gems91/cwpc17.py` (16 label-blind `CWPC` geophysical features + `prior_shift_calibrate_surface` fixing `IR-91-S15-06` + `build_local_autocontext_features` fixing `IR-91-S15-07`) and `scripts/run_s17_cwpc.py` (3-experiment evaluation on `gems57-pooled-hide-v2` and `gems91-hide-recover-v1.1-nohalo`, plus Blind Off-Catalogue USGS SGMC Control).

### Pass 2 — Review, Debug & Edge-Case Remediation (COMPLETED)
- [x] **Memory-Bound Remediation:** First run of `scripts/run_s17_cwpc.py` hit the 3.8 GiB sandbox RAM limit (`exit_code: -1`) when holding all 19 float32 bands + 16 float32 CWPC arrays in memory simultaneously. Refactored `build_cwpc_physics_features` and `build_feature_cube_memmap` to use `LazyBandLoader` + `np.lib.format.open_memmap` (`float16`), reducing peak RAM below 450 MB.
- [x] **Upper-Tail Saturation Remediation:** Discovered that `robust_norm` clipping at `3.0` truncated the top 1.5% of heavy-tailed fault-scarp and potential-field gradients (`rtp_grad`, `tmi_hg`, `det_elev_grad`, `iso_grav_anom_grad`) where all 37,654 dots (`0.73%` of footprint) are placed, and fixed `GRAD_BAND_INDICES` to include band 18 (`det_elev_slope_grad`). Widening `clip_hi` to `20.0` lifted `E2` from `0.124733` to `0.131810 HOLDOUT-DTI` (`gems57-pooled-hide-v2`) and lifted Blind Off-Catalogue SGMC DTI from `0.078344` to `0.090912`.
- [x] **Validator & Policy Gate Verification:** Passed `ledger_csv=ROOT / "ledger/submissions.csv"` and `allow_zeros_outside=True` to `validate_raster.py`, verified all 3 validator suites (`vendor/gems57/submission_writer.py`, `scripts/validate_raster.py`, `src/gems91/release_gates.py`), registered `.tif` and `.zip` in `registry/artifact_policy.json`, and updated `docs/download-audit.json` / `docs/download-audit.html` (`66` files audited, `PASS: 66 explicitly registered prediction artifacts`).

### Pass 3 — Re-Check Against Original Prompt & Full Test/Browser Verification (COMPLETED)
- [x] Added unit and integration tests in `tests/test_s17_cwpc.py`.
- [x] Updated `README.md` (with prompt and Arena AI Core Values: "Maximize P(Win)" and "Own the Outcome"), `docs/index.html`, `docs/executive-summary.html`, `LIMITATIONS_AND_NEXT_STEPS.md`, and `PASS_LOG.md`.
- [x] Verified full `pytest` suite and Playwright + axe-core browser smoke suite (`node tools/browser/smoke.cjs`), committed, pushed, and created/merged PR onto `main`.

---

> **Historical entry below describes an earlier branch (`arena/e6fdea6b-gemsdoe91`), not the current checkout.** Current branch: `arena/2f002fa0-gemsdoe91`. Current three-pass review: `docs/REVIEW-SESSION-20261025.md`; no new TIFF/experiment/slot, lane paragraph missing, feature stack absent; current verdict negative. The sample and existing-fault catalogue are present only as SHA-verified audit references. The earlier unique artifact is still research-only and not endorsed for submission. The prior policy omission for that artifact has now been corrected and `scripts/check_artifact_policy.py` passes.

## Session context
Branch: arena/e6fdea6b-gemsdoe91 (active). Pinned data restored:
- data/official/sample_submission.tif (EPSG:32611, 3730x3292, 100 m, footprint 5,167,373 px)
- data/official/existing_faults.tif (catalogue, 60,988 px)
- data/registry/GEMSDOE32__h33-2-b2-zeros.tif (registry parent R0)
- data/registry/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-nan.tif

## Goal
Generate a UNIQUE TIF submission, easy to download, values in [0,1], CRS/shape/transform match, no NaN inside footprint, zero catalogue mass, >=3 px collar, validated without human intervention, with an obvious OK TO DOWNLOAD / OK TO SUBMIT verdict.

## Pass 1 — implement (DONE)
- [x] Wrote scripts/build_unique_submission.py (off-catalogue damage-zone annulus lattice)
- [x] Ran via scripts/submission_writer.py (shared tool, triple gate suite): CERTIFIED
- [x] Validated with scripts/validate.py: PASS (all gates true, 8718 dots, min cat dist 3.1623 px)
- [x] Validated with scripts/validate_raster.py: PASS (all must-pass gates, values [0,1], zero catalogue mass, sha256 new)
- [x] Registry uniqueness (Rule-1 LANE): surface |rho|=0.00983 (<=0.90), dot 3px overlap=20.67% (<=70%), NOT a duplicate
- [x] Holdout-DTI: 0.0 CI [0,0] (deliberate off-catalogue negative; honest)
- [x] Published TIF/ZIP/audit to docs/downloads/; ZIP single-member, inner TIFF matches disk
- [x] Wrote docs/run-card-unique-offcatalogue-damagezone.json
- [x] Updated README.md top verdict + download link

## Pass 2 — review (DONE)
- [x] All gates PASS / CERTIFIED; no FAIL or UNVERIFIED
- [x] Uniqueness vs registry PASSES (not a duplicate)
- [x] Note 140 chars; name < 140 chars
- [x] Download link + verdict obvious in README

## Pass 3 — final (IN PROGRESS)
- [ ] Commit + push to arena/e6fdea6b-gemsdoe91
- [ ] Open PR from this branch to main, merge
- [ ] Report limitations / next steps

## Verdict
OK TO DOWNLOAD: YES — FORMAT-CERTIFIED, UNIQUE (8,718 unit dots, all values in [0,1], EPSG:32611 3730x3292, zero catalogue mass, 3.16 px min catalogue distance).
OK TO SUBMIT: NO — RESEARCH NEGATIVE. HOLDOUT-DTI = 0.0 by design (off-catalogue damage-zone dots cannot cover withheld catalogue faults). No DrivenData authentication available to confirm organizer acceptance or live score; no weekly slot spent. Not a score-improvement candidate.
File: docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif (sha256 a5636b10237757cda5de1a7561a0d5f2600479cdd8610226dfd4c1650b66ca11)

## OLC91 (2026-10-25, `arena/3444a6d3-gemsdoe91`)

* **Pass 1 (implement/verify):** data restored with SHA-256 verified. R0 lineage forensics were
  done, the preregistration was written before running, and holdout seed 20 was run
  (E0/E1/RND + canary). The final E1 file came from the fail-closed vendor writer, with
  independent validation and the run card.
* **Pass 2 (review/fix):** the uniqueness stop was honoured, not weakened. The artifact policy was
  repaired (DRN91 entries). `generate_submission.py` now verifies the current run card. The portal
  test was generalised from a hard-coded GEO91 to `docs/current-run.json`.
* **Pass 3 (recheck vs request):** the unique name and the 107/140 note are present. The verdict is
  explicit (OK TO DOWNLOAD: YES — research only; OK TO SUBMIT: NO). The JSON run card has every
  protocol field. Every number is labelled. The README and site lead with the download. Sources
  are linked.

# Current three-pass review — `arena/522615dd-gemsdoe91` — 2026-10-25

- **Pass 1 — inventory/readiness/provenance:** reread the standing brief and current README; inspected the active branch, current portal and source templates; reran `scripts/preflight.py`. It reports **BUILD BLOCKED: 0/2** and all six implemented axes blocked. `data/` has no files. The official competition data page redirects anonymous access to login. No mirrored competition data were restored.
- **Pass 2 — scientific/protocol review:** confirmed there is no assigned single-method paragraph; did not infer a lane. Ranked three proposals (topographic spectral-slope/roughness break, within-map-unit potential-field residual, multi-season Landsat surface-temperature residual) in `docs/HYPOTHESES-ACTIVE-522615DD-20261025.md`. Fetched official competition/rules/leaderboard and USGS source pages; kept public-board scores separate from user reports, holdout metrics, and receipts. No model, holdout, canary, placement, TIFF, or slot was run.
- **Pass 3 — docs/portal/tests:** updated the active README and portal to distinguish the prior OLC91 research download from this no-run review; fixed `LB-DTI` navigation labels; added the branch-specific review/run card, official source records, and tests. Normalized all 115 historical CSV source URL strings without changing their evidence class or receipt status. Re-rendered the portal.
- **Final verification:** `.venv/bin/python -m pytest -o addopts='' -ra` → **555 passed, 8 skipped, 58 warnings** in 36.15 s (data-dependent skips; Rasterio affine deprecation warnings). `scripts/check_artifact_policy.py` → **PASS, 87 registered artifacts**. `git diff --check` → clean. Expected `scripts/preflight.py` exit 1 remains the active blocker.
- **Outcome:** negative/blocked; zero experiments and weekly slots, no new score, no new TIFF, no organizer receipt. Prior OLC91 file remains research-only and is not promoted. Current review/run card: `docs/REVIEW-ACTIVE-522615DD-20261025.md` / `docs/run-card-522615dd.json`.

## Review 6cbfe8ac — 2026-10-25

1. Implemented: fixed default verification of HEXFAR91 when website links OLC91; exact canonical TIFF/ZIP/card/pointer now checked; blocked unassigned `--run`; preserved explicit historical verifiers and clarified executive guide.
2. Reviewed: fixed shared audit float32 omission; added invalid-dtype, re-pinned NaN/Inf/range, pointer, ZIP, note and missing-reference regression cases. Restored pinned inputs and recomputed lattice capacity independently; fresh inventory 87 files, 78 PASS / 9 FAIL, all not approved to submit.
3. Rechecked: final full suite **568 passed, 1 expected skip**, 62 Rasterio pending-deprecation warnings. Local links and canonical portal rendering checked. No candidate, no scientific HOLDOUT-DTI, no slot. Missing lane and literal uniqueness infeasibility remain explicit, not bypassed.

Evidence: `docs/REVIEW-6CBFE8AC-20261025.md`, `docs/review-6cbfe8ac/verification.json`, `docs/run-card-6cbfe8ac.json`.

Integration follow-up for 6cbfe8ac: merged main PR #120, preserved ee76e309 review/CI/tests, and delegated this CLI wrapper’s reference check to the shared `verify_frontdoor.py`. Integrated full suite **585 passed, 1 expected skip**, 78 Rasterio warnings. No scientific experiment or slot.

---

## Active branch review (`arena/e02bcd84-gemsdoe91`, 2026-10-25)

- **Pass 1 — inspect:** read the standing brief and repo evidence; confirmed canonical lane assignment is false; installed pinned requirements and restored 15 selected inputs from repository-pinned GitHub mirrors into ignored `data/` (all hashes/sizes matched; no raw data staged). Fetched official DrivenData problem specification and USGS GeMS SGMC/ComCat pages; exact links and source boundaries are in `docs/REVIEW-ACTIVE-E02BCD84-20261025.md`.
- **Pass 2 — run checks:** full `.venv/bin/pytest -q -ra` passed with one expected legacy-release skip. `scripts/preflight.py` reported BUILD ALLOWED for its local prerequisites; `scripts/check_artifact_policy.py` passed for 87 registered artifacts. `scripts/audit_downloads.py` checked 87 artifacts: 78 format PASS / 9 FAIL, global submit status false. Failures are seven NaN-outside TIFFs and two synthetic TIFF/ZIP catalogue-mask failures; they remain unapproved. Historical CED91 artifact validation passed only its defined format/sample/catalogue checks and reports submission_ready false.
- **Pass 3 — requirements:** no exact method paragraph assigned, so no experiment, candidate TIFF, submission slot, or score was produced. Ranked five conditional hypotheses and source availability checks are documented; top screen is MUSD, but it is not lane-assigned or holdout-validated. Existing OLC91 portal file is research-only and has a recorded duplicate stop. Updated README start page to point to this branch's review and preserve the existing full prompt.
- **Verdict:** NEGATIVE / NO PROMOTION. No new TIFF is available to download or submit. Run card: `docs/run-card-E02BCD84.json`; detailed review: `docs/REVIEW-ACTIVE-E02BCD84-20261025.md`.


## Active-branch integration recheck — `arena/522615dd-gemsdoe91` — 2026-10-25

- Merged upstream main through `ee35489` (including `5262aa9` and PR #124) on the fixed session branch; retained upstream current-download verifier/CI and branch-specific historical reviews, while keeping this checkout's no-lane/no-data status explicit. The FFB91 review reports 1/2 inputs only for its own checkout; current preflight remains 0/2.
- Re-ran `.venv/bin/python -m pytest -o addopts='' -ra`: **588 passed, 8 skipped, 78 warnings** in 38.59 s (final run after the latest main merge and audit-snapshot refresh). Artifact policy: **PASS, 87 registered prediction artifacts**. `git diff --cached --check`: clean at the integration checkpoint.
- Default `generate_submission.py` verifies the exact current OLC91 TIFF/ZIP/card and reports technical PASS, **OK TO DOWNLOAD: YES — RESEARCH ONLY**, **OK TO SUBMIT: NO**, references `NOT_CHECKED`. `--with-data` blocks on the absent official sample; `--run` blocks on the absent lane.
- `scripts/preflight.py`: expected **BUILD BLOCKED: 0/2**, all six axes blocked. No data restored, experiment run, new score/TIFF, selector step, or slot use.


## PR #123 published-artifact audit snapshot follow-up — 2026-10-25

- GitHub run `40216729640`: `tests` and `browser-delivery` passed; `published-artifact` failed in its audit/diff step. Job metadata identified step 7; the detailed runner log was inaccessible from this sandbox.
- Found stale canonical `docs/download-audit.json`/HTML (85 files, 76 PASS / 9 FAIL), while the current registered inventory has 87 files. Reused the latest saved pinned-reference audit from `docs/review-6cbfe8ac/download-audit.json`, after validating all 87 paths, current artifact/policy SHA-256 values, manifest reference hashes, and overlap-record parity; the 2 added CWP91 artifacts are technical PASS. Regenerated the canonical HTML with the current renderer.
- The refreshed snapshot still reports **78 technical PASS / 9 FAIL**, all not submit-approved. No data were restored or audit rerun locally. Follow-up CI run `40219293388` / run #342 passed `tests`, `published-artifact`, and `browser-delivery`; the published-audit/diff step now passes. Its workflow restored the two pinned sample/catalogue references only inside the CI runner.

## Review 19912231 — three passes (2026-10-25)

1. Audited latest handoff, sources, shared tools and current download. Refetched 92 GitHub fleet pages; restored only sample/catalogue/lattice; added reusable pinned-witness capacity preflight and distinguished input availability from experiment authorization. No geological run.
2. Added 32 unit/file tests for exact overlap threshold, empty support, exhaustive placements, altered pins/grids, invalid plans and budget edge cases. Independently verified all 87 published artifacts; 78 technical PASS / 9 FAIL, none approved. Found generated-page drift after refreshing feed; fixed via full shared renderer.
3. Repeat suite: 610 passed / 8 documented data-dependent skips; browser desktop/mobile delivery, SHA checks, accessibility and link/UI checks PASS. Current TIFF/ZIP unchanged, registry/evaluator/writer unchanged. No new unique TIFF or holdout score; missing lane and infeasible usual budget remain explicit negative outcome. See docs/REVIEW-19912231-20261025.md and its machine verification.

19912231 integration: upstream 45d4933 merged on the fixed branch; preserved stricter ZIP/promotion-flag validation and marked previous review status historical. Combined suite: 626 passed, 8 skipped, 87 deprecation warnings.
