# GEMSDOE91 — Unique TIF submission pass log

## Active checkout review — `arena/85ad3c12-gemsdoe91` (2026-10-25)

This section records the current checkout and supersedes neither the historical session record below nor its artifacts. The historical context below names `arena/e6fdea6b-gemsdoe91` and reports locally restored inputs; those statements do not describe this checkout.

- No assigned single-method paragraph (`docs/run-card.json`: `lane.assigned: false`); no lane inferred.
- `data/` and `.venv/` are absent. `python scripts/preflight.py` exits 1 with `BUILD BLOCKED`, missing `sample_submission` and `parent_r0_nan`; no feature stack or complete registry is available to run the protocol.
- Base Python initially lacked the pinned packages; installed `requirements.txt` into ignored `.venv/`. The first suite run found three portal/run-card mismatch failures; repaired the GEO91 source templates, renderer pointer, and test contract. Full pytest suite now passes (with six skips and Affine deprecation warnings). A standard-library syntax compilation of 185 Python source/test files found zero syntax errors.
- No new experiment or TIFF, submission, or weekly slot was used. Holdout and registry uniqueness values for this review are NOT RUN, not zero. A pre-existing historical damage-zone artifact has a separately documented HOLDOUT-DTI 0.0 negative; it was not rerun.
- Pass 2 found the artifact-policy CI check omitted three already tracked historical files. Added their current byte hashes and do-not-submit status to `registry/artifact_policy.json`; `python scripts/check_artifact_policy.py` now passes for 62 artifacts. This does not upgrade their eligibility.
- Review: `docs/REVIEW-ACTIVE-85AD3C12-20261025.md`; run card: `docs/run-card-85ad3c12.json`.

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
