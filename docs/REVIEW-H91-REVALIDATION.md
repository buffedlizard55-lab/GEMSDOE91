# H91 post-hoc revalidation — three review passes

**Review date:** 2026-10-24 UTC
**Workspace branch:** `arena/8ac4c974-gemsdoe91`
**Scope:** inspect prior H91/CED claims, compare the stored H91 artifact to a newly fetched pinned registry witness, repair the shared uniqueness module/pinning and stale readiness claims. **No geological experiment, holdout evaluation, candidate generation, competition submission, or slot use occurred during this review.**

## Executive verdict

**H91 E1: negative. OK to download for research; NOT OK to submit.** Its stored `-zeros.tif` is technically valid under local format/range checks, but **38,302 of 38,400 dots (99.74479167%)** are within 3 pixels of the pinned `calib_r13lattice_00904.tif` raster. The literal strict duplicate threshold is >70%. The earlier 20-raster “pass” was not valid clearance: its checker omitted `data/fleet_registry`, sampled surface ranks, and substituted symmetric F1 for directed overlap against dense references.

**CED91 is also negative** under the same literal witness: 31,972/32,000 dots, or **99.9125%**, overlap within 3 pixels. Both artifacts pass local format validation; neither is submission-cleared.

The H91 continuous surface was not retained, so its full-footprint surface rank correlation against this lattice is **unverified**. The final-dot raster's Spearman value (`-0.00047682895378441`) is a separate diagnostic and is not substituted for the missing surface measurement. Final-dot overlap alone establishes the duplicate.

## Pass 1 — provenance and bytes

- Restored `vendor/gems57/uniqueness.py` byte-for-byte from `buffedlizard55-lab/GEMSDOE78@30f1ab9400f92036b0bc613425f1b5b6046f3897`; verified Git blob `478c9001dc9c323cd50ba820f53c71dc2f80f221` and SHA256 `9b3b9863dd8b74a2e3a338604aba7e26631a2cfbf7428d45595088d7260e5eef`. Added this previously omitted module to `registry/template_pin.json`; the full shared source check passes.
- Retrieved `calib_r13lattice_00904.tif` from `buffedlizard55-lab/60GEMSDOE@02563d07fb85d2f4d35887503d380d34d4017197`. Git blob `81c802618e6d46c6d62289d856ae74439439bbc6`; 1,706,456 bytes; SHA256 `b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2`.
- This is a pinned public sibling-repository witness, **not an organizer-authenticated source**. `registry/comparison_inventory.json` is explicitly not universal; private, unlinked, inaccessible, and later entries may be missing.
- Re-read H91 and CED TIFF bytes. Both are single-band float32, EPSG:32611, 3730×3292, the pinned 100 m transform, finite `[0,1]`, and have zero mapped-catalogue pixels. Their research ZIPs each contain only the byte-identical TIFF. H91 SHA256: `0c11eaab094064841c2635bc302e9604a61fc96f257430cb8b22fae6a6a04119`; CED SHA256: `a29e79d400d0fb26ebcbc0be6b1dcf66b17dfedf9ded1ef8c9a53678c16553ee`.

## Pass 2 — implementation and threshold audit

### Defects found

1. `scripts/evaluate_holdout.py::check_registry_uniqueness` used a symmetric-F1 exception when a reference had more than 1.5 times the candidate's positive count. The required stop rule is directed candidate-dot overlap; reference density does not remove a comparison.
2. Its default inventory only scanned `data/registry` and `data/registry_siblings`, not `data/fleet_registry`, where this lattice witness resides.
3. Its surface Spearman was computed on every fifth flattened footprint value, not the exact full footprint.
4. `src/gems91/novelty.py` carried another local implementation while `vendor/gems57/gates.py` imported the missing shared module.
5. The H91 run card, page, and artifact policy called the 20-raster subset a uniqueness pass and treated the old result as promote/selector review.

### Repairs

- The local H91 measurement adapter now calls the restored `vendor.gems57.uniqueness.compare_array_to_registry`; symmetric F1 is not a binding threshold, and a path-only inventory is incomplete and cannot pass. `data/fleet_registry` is included in local diagnostics.
- The H91 runner stops on a measured duplicate or incomplete inventory and has explicit blockers for the lane-local evaluator/writer, unassigned lane, incomparable best, and absent selector receipt. It cannot turn the old partial pass into promotion.
- `src/gems91/novelty.py` is now a thin wrapper around shared `surface_rho` and `dot_overlap`; tests pin the same absolute rank-correlation and strict directed-overlap decisions.
- The holdout adapter now presents shared measurements by protocol phase: continuous-surface Spearman is a surface gate; directed 3-pixel overlap is a final-dot gate. The other metric in each phase is explicitly diagnostic, avoiding a generic roll-up from falsely treating a broad-valued surface as a dot mask. Undefined rank/overlap measurements are recorded as unverified and cannot clear uniqueness; the historical runner stops on that condition too.
- Direct shared-template remeasurement reproduced the previously calculated overlaps exactly and flagged both artifacts as duplicates. Full machine measurements and validation receipts are in [`evidence/h91_lattice_reaudit_20261024.json`](../evidence/h91_lattice_reaudit_20261024.json).

### Exact H91 witness result

| Measurement | Result | Rule / meaning |
|---|---:|---|
| Candidate dots | 38,400 | Stored H91 `-zeros.tif` |
| Candidate dots within 3 px of lattice | 38,302 | Directed count; denominator is candidate dots |
| Directed overlap | 0.9974479166666667 (99.7448%) | Duplicate if >0.70 |
| Final-dot raster Spearman | −0.00047682895378441 | Diagnostic; not continuous-surface Spearman |
| Reverse overlap | 0.14788177577998501 | Diagnostic only; does not replace directed overlap |
| Jaccard | 0.006136202363422327 | Diagnostic only; not a clearance rule |
| 3 px lattice halo coverage | 0.9987132726822701 | Context only; direct candidate comparison is decisive |
| Registry completeness | `false` | One direct witness plus prior partial set; not universal scope |

The equivalent CED witness is 31,972/32,000 = 0.999125. Neither can pass by describing the lattice as “synthetic”, “dense”, or “space-filling”; that would be an unauthorized exception.

## Pass 3 — scientific claims, delivery, and readiness

- Historical H91 `0.174030` remains labelled **HOLDOUT-DTI** (evaluator `gems91-hide-recover-v1.0`, 60,988 withheld positives, 95% CI `[0.161841, 0.184791]`). The H91 script used lane-local holdout/writer code. This score is not comparable to CED's pinned `gems57-pooled-hide-v2` result and is not an organizer score.
- The cited `0.2778` GEMSDOE32 and `0.4413` public-top figures are **USER-REPORTED-UNVERIFIED** for this review. No live leaderboard, official page, rules PDF, submission form, or receipt was fetched; the host was outside the available network allowlist. A plausible DTI mechanism is that removing unmatched prediction mass can reduce false-positive cost, but that does not prove why any reported live score was obtained. No numerical projection is presented as a score.
- Existing CED hypotheses remain provisional because no single assigned method paragraph is recorded. The four proposals and their named mimics are in [`HYPOTHESES_CED.md`](HYPOTHESES_CED.md): stable magnetic–gravity edge displacement (intrusive contact/survey seam), depth-conditioned conductivity contact (saline water/clay), signed dilatation contrast (sparse-station interpolation), and depth-conditioned paired curvature (depositional basin margin). The CED E1 result (`HOLDOUT-DTI 0.062153`, 60,988 positives, 95% CI `[0.049910, 0.075115]`) is historical measured evidence; this review did not re-run it. Its candidate is also a duplicate.
- The H91 card, registry evidence, local artifact receipt, H91 pages, README, and artifact-policy reasons now agree on `negative`, `uniqueness_pass: false`, `ok_to_submit: false`, and research-only download status. The H91 form name/note remain only as machine-readable historical identifiers (note length 117/140); do not paste them into a competition form.
- PR-base sync found `main` had advanced through PR #41, whose landing page described H91 as a unique candidate using the invalid legacy clearance. That copy was removed by rebuilding from the corrected evidence. H11 records newly present on `main` were retained as historical material and were not re-audited in this H91 review.
- No human scientific review is needed to reach the negative duplicate verdict. A separate selector receipt cannot override a duplicate or incomplete inventory.

## Hypothesis scope and limits

Four distinct CED hypotheses are already preregistered, with physical mechanisms, differences from prior code, mimics, and qualitative cost in `docs/HYPOTHESES_CED.md`. Only CED E1 was tested historically. The H91 memo lists five other ideas, but H91 is not an assigned lane for this branch and its supporting scientific citations/data-license claims were not independently verified. No new proposal was promoted or validated in this review. Any future candidate must be authorized in one method paragraph and use the cached feature stack plus the pinned shared evaluator/writer, feature-alone canaries, buffered whole-component holdouts, and complete hash-verified registry scope.

## Remaining work / limitations

1. Resolve the assigned method-lane ambiguity; do not run a new experiment without it.
2. Produce a universal/complete registry inventory or retain the current fail-closed status. The witness comparison proves these duplicates; it does not prove uniqueness against all possible artifacts.
3. Re-evaluate any future candidate with the pinned shared evaluator and a comparable prior best before considering a slot. H91's lane-local DTI is not that comparison.
4. Verify organizer data provenance and redistribution rights from official sources; mirror hashes prove byte identity only.
5. Fetch current competition rules, deadline, leaderboard, upload form, allowance, and any actual score receipt only when official access is available. None is confirmed here.
6. A unique compliant TIFF was **not** produced in this review. Both stored candidate files remain research-only. No slot was spent.

## Verification record

- `git hash-object vendor/gems57/uniqueness.py` → `478c9001dc9c323cd50ba820f53c71dc2f80f221`; upstream Git blob: `478c9001dc9c323cd50ba820f53c71dc2f80f221`.
- H91 and CED direct measurements were run through the pinned shared `compare_array_to_registry`; results and per-validator checks are stored in `evidence/h91_lattice_reaudit_20261024.json`.
- `.venv/bin/python -m pytest -q -ra` — PASS; seven input-dependent tests skipped because their pinned data are absent. Rasterio emitted only pending-deprecation warnings.
- `.venv/bin/python scripts/build_pages_site.py` and `.venv/bin/python scripts/render_portal.py` — PASS; generated H91 page says research download YES / submit NO and visibly flags DUPLICATE.
- `scripts/verify_evidence.py` — PASS; source pins, CED arithmetic/folds/canaries, direct H91/CED measurements, and negative cards consistent; zero experiments rerun and both readiness flags false.
- `scripts/check_artifact_policy.py` — PASS; six registered prediction artifacts, no raw raster/archive tracked. `scripts/verify_current_artifact.py --with-data` — PASS for the existing CED research TIFF (`a29e79d400d0fb26ebcbc0be6b1dcf66b17dfedf9ded1ef8c9a53678c16553ee`), with `submission_ready: false`.
- `scripts/preflight.py` — expected `BUILD BLOCKED` (exit 1): `parent_r0_nan` is missing; all six method axes remain blocked. `compileall` and `git diff --check` — PASS.
- No scientific experiment, holdout evaluation, candidate generation, score, competition slot, or upload was run during this review.
