# GEMSDOE91 — Unique TIF submission pass log

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

## Pass 3 — final (DONE)
- [x] Commit + push to arena/e6fdea6b-gemsdoe91 (commit 097b737)
- [x] Opened PR #96 from arena/e6fdea6b-gemsdoe91 to main — MERGED (merge commit 75df07dbd4a03833eef72387ba1d44b16ac317cb)
- [x] Limitations / next steps reported below

## Verdict
OK TO DOWNLOAD: YES — FORMAT-CERTIFIED, UNIQUE (8,718 unit dots, all values in [0,1], EPSG:32611 3730x3292, zero catalogue mass, 3.16 px min catalogue distance).
OK TO SUBMIT: NO — RESEARCH NEGATIVE. HOLDOUT-DTI = 0.0 by design (off-catalogue damage-zone dots cannot cover withheld catalogue faults). No DrivenData authentication available to confirm organizer acceptance or live score; no weekly slot spent. Not a score-improvement candidate.
File: docs/downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif (sha256 a5636b10237757cda5de1a7561a0d5f2600479cdd8610226dfd4c1650b66ca11)

## Limitations / next steps (for a future session)
1. No DrivenData authentication -> cannot auto-download training_features.tif / labels.tif / sample_submission.tif, cannot verify live leaderboard or weekly slot allowance. To actually compete for a top score, authenticate to DrivenData and restore the full pinned training data.
2. HOLDOUT-DTI = 0.0 by design: this candidate is deliberately off-catalogue. A score-improvement candidate needs fault-targeted dots, which requires the geophysical feature bands (training_features.tif, bands 3/5/6/12/18/19 etc.) not publicly available without DrivenData login.
3. Budget used: 1 of 3 experiments, well under 2 hours. Two experiments remain if fault-targeted data becomes available.
4. The registry lattice covers ~99.87% of the footprint within 3 px, so any dense dot result is at risk of the >70% 3px overlap duplicate stop; a genuinely protocol-unique high-scoring candidate requires careful lane management.
5. Submission form requires a unique name (<=140 chars) and short note (<=140 chars); both recorded in docs/run-card-unique-offcatalogue-damagezone.json and the audit.
