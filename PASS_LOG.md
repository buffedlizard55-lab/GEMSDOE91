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
- [x] **Fixed `IR-91-S17-01` (PR #95 & PR #96 portal/policy regression):** Updated `scripts/render_geo91_portal.py` so `scripts/render_portal.py` no longer overwrites `docs/index.html` and `docs/executive-summary.html`, registered the 3 unregistered PR #96 artifacts plus the 2 new `S17-CGRD E2` artifacts in `registry/artifact_policy.json`, and regenerated `docs/download-audit.{json,html}` (`64` files audited).

### Pass 3 — End-to-End Re-Verification Against All Requirements (COMPLETED)
- [x] Full pytest suite: `.venv/bin/pytest -q -rs` -> **475 passed, 0 failed, 0 skipped**.
- [x] Artifact policy & download audit: `.venv/bin/python scripts/check_artifact_policy.py` (`PASS: 64 explicitly registered prediction artifacts`) & `.venv/bin/python scripts/audit_downloads.py` (`status: "PASS"` on both `gems91-s17-cgrd-e2-20261025T141828Z-7979e44f-zeros.tif` and `.zip`).
- [x] S16/current evidence verifiers: `.venv/bin/python scripts/verify_s16.py`, `.venv/bin/python scripts/verify_evidence.py`, `.venv/bin/python scripts/verify_current_artifact.py` -> all `PASS`.
- [x] Headless Chromium + axe-core WCAG 2.1 AA + mobile `390x844` overflow + SHA-256 download check: `node tools/browser/smoke.cjs` -> `status: "PASS"`, `0` console/HTTP errors, `0` mobile overflow, `0` WCAG violations across 21 pages.

---

# GEMSDOE91 — Unique TIF submission pass log (Prior Session `arena/e6fdea6b-gemsdoe91`)

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
