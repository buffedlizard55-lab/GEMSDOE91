# Three-pass review — S22 OMTJ

Branch: `arena/a3f85c97-gemsdoe91`. Date: 2026-10-26.

## Outcome first

**OK TO DOWNLOAD: YES, research only. OK TO SUBMIT: NO. Verdict: negative.**

One fresh geophysics-derived TIFF was generated, not copied from a historical raster. Its file SHA256 is new in the frozen indexed scope. This is **not** a full scientific uniqueness certificate: its final dots fail the literal registry gate (98.565889% within 3 pixels of the registered calibration lattice). The run stopped immediately on that witness; 26 previous final comparisons passed, 85 later comparisons were not run. No density exception, no perturbation to evade the gate, no second experiment, no submission slots.

HOLDOUT-DTI: **0.06622318062610064**, 95% CI **[0.0480153209879553, 0.0868031263517965]**, `gems57-pooled-hide-v2`, **60,988 withheld positive pixels**, pooled 20 km block bootstrap (1,000 draws). This is not a leaderboard estimate. The scientific prerequisite of beating the current best with a matched comparison is not satisfied.

## Pass 1 — implement and measure

- Read standing README brief, previous-session next steps, source modules, shared template, registry policy and historical forensic evidence.
- Restored SHA-pinned sample, catalogue and full 19-band feature stack from the repository's existing immutable mirrors; verified hashes and byte sizes. No raw input raster added to Git.
- Restored 62/64 frozen references; the two missing quarantined local artifacts remain explicitly unverified. Added all pre-existing local TIFFs and exact nine-site leader artifacts to a frozen deduplicated 112-file experiment index.
- Preregistered four geological hypotheses and one fixed OMTJ experiment; used only B14 TMI and B13 isostatic gravity, avoiding disputed band semantics.
- Reused shared spatial folds, canary logic via tie-aware AUC, `evaluate_holdout.py`, existing NMS emitter and `submission_writer.py`. No private metric or writer fork.
- Tested seven raw/derived feature channels separately in each fold. Maximum symmetric AUC 0.577448; all 28 canaries pass the .90 trigger.
- Checked all 112 pre-placement surfaces with exact in-footprint Spearman; max positive correlation 0.050118. No surface duplicate.
- Produced the holdout, serialized TIFF and single-TIFF ZIP, re-read actual bytes, then stopped at the first final-dot duplicate as preregistered. Run time in the experiment receipt is 53.88 seconds; one experiment.
- Re-fetched all nine prompt-named historical leader blobs; verified file hashes and all 72 directed peer overlaps. All nine fail uniqueness against another member of the set; GEMSDOE25/GEMSDOE30 have exactly equal positive support. Scores remain unverified claims.
- Retrieved all chunks of the official rules PDF, both problem-description chunks, USGS GeoDAWN and geothermal context, GDR 1391 metadata, official reference notebook, and the public leaderboard. Fresh leaderboard observation is 0.4437, not a receipt for these files.

## Pass 2 — bugs, edge cases and historical contradictions

- Replaced contradictory stacked “current” banners with one canonical front-door pointer and two source-rendered pages. Preserved versioned historical pages; did not rewrite their measured evidence.
- Found historical tests hard-coded to require multiple past candidates simultaneously on the current page. Retargeted historical delivery checks to their versioned pages; retained current-byte, negative-status, tamper and missing-data tests against the actual current pointer.
- Updated browser delivery checks to navigate archived candidate pages before testing their historical downloads, instead of requiring the current page to expose every old file.
- Prevented historic renderers from borrowing CSS from the new current page and mutating old reports. The current renderer dispatch leaves archive bytes unchanged.
- Fixed table anchors to route to actual site sections on the executive page.
- Retained local format checks separate from official acceptance. Official outside-boundary null/NaN wording and the repository all-finite zeros encoding are both disclosed.
- Disclosed holdout allocation shortfall: planned budgets [17,846, 9,957, 4,111, 5,740]; emitted counts [17,846, 9,957, 4,111, 5,524]. **37,438 holdout dots**, not 37,654; the final full-grid TIFF does contain 37,654. No refill or retest after the stop. This further prevents treating a historical scalar as a matched budget comparison.
- A passing AUC canary is not proof of no leakage; hash equality to a team mirror is not independent official provenance authentication; fresh file bytes are not proof of geometric uniqueness.

## Pass 3 — final verification checklist

The checked commands and final outcomes are recorded in `verification.json`: 689 Python tests passed, 8 legacy integration tests skipped; real Chromium delivery and accessibility passed on 27 pages, with zero violations, HTTP/console errors or mobile overflow. Current TIFF/ZIP SHA256s matched downloaded bytes. The checks cover the full Python suite, current TIFF/ZIP re-reading against restored references, shared-template integrity, all-download policy/range audit, deterministic renderer output, browser download SHA256, desktop/mobile overflow and accessibility. Skipped legacy integration tests must remain disclosed rather than counted as passed.

No claim is made that this session achieved a higher leaderboard result or fulfilled the requested promote-ready unique submission. Those objectives remain blocked by the negative scientific result, literal duplicate failure, incomplete registry, absence of comparable incumbent predictions and lack of authenticated score/quota evidence.

## Exact reproducibility and stopping behavior

On a fresh checkout, install `requirements.txt`, run:

```bash
python scripts/restore_data.py --only sample_submission,existing_faults,training_features,parent_r0_zeros
python scripts/restore_registry.py --available-only
python scripts/audit_s22_sites.py
```

The measured run is immutable: `python scripts/run_s22_omtj.py` refuses to overwrite its existing `docs/s22/run-card.json`. Reproduction should take place in a **separate approved experimental workspace**, preserving the original card and frozen registry; it is not another authorized experiment in this stopped lane. Re-validating published bytes is safe:

```bash
python generate_submission.py --with-data
python scripts/verify_s22.py
python scripts/check_artifact_policy.py
python scripts/render_portal.py
python -m pytest -ra
```

Do not rerun current upstream source discovery and claim it reproduces the earlier frozen index. The old inventory is pinned in `frozen-registry.json`, and the source commit/blob identifiers are recorded in the nine-site audit.

## Next session

First resolve literal registry feasibility with its coordinator; do not silently remove the dense witness. Then establish a matched incumbent replay and an actually obtainable independent data source. The request's missing method paragraph was explicitly treated as a self-assigned research lane, not coordinator authorization. All technical inspection here is automated; the separate selector is still required by the user's protocol.
