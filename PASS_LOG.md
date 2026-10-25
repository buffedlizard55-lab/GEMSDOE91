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
