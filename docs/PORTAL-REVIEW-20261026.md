# Portal consistency review — 2026-10-26

## Finding

The authoritative current pointer in `docs/current-run.json` selects **S22-OMTJ** (`run-card-S22-OMTJ.json`). However, the shared current-page renderer also injected a parallel **S22-XB** callout into both the homepage and executive summary. The callout contained a different raster, a score projection, a second historical run verdict, and language calling that artifact unique. This contradicted the OMTJ-only current pointer and could mislead a visitor about which downloadable file was current. The dedicated `s22-xbreed-executive-summary.html` remains an archived S22-XB report and is not deleted or relabelled.

## Change

- Current entry points now render only the OMTJ run-card status and downloads.
- S22-XB remains available on its own historical executive-summary page.
- The renderer no longer imports or injects the S22-XB parallel callout when rendering current pages.
- Regression coverage checks the generated pages and re-runs the current renderer to prevent this stale callout from returning.

## Verification

- `python scripts/render_portal.py`: PASS; generated current pages identify OMTJ and do not surface S22-XB as current.
- Restored the SHA-pinned sample grid and existing-fault raster from the repository's immutable GitHub mirror, verified both hashes and byte counts, and kept them in ignored `data/` (not Git). Provenance is still a team mirror, not an organizer-authenticated fetch.
- `python scripts/render_portal.py`: PASS; generated current pages identify OMTJ and do not surface S22-XB as current.
- `python generate_submission.py --with-data`: PASS for actual downloaded TIFF/ZIP identity, sample grid, footprint, range and catalogue masking; reference checks `PASS`, `OK_TO_DOWNLOAD=YES`, `OK_TO_SUBMIT=NO`.
- `python scripts/check_artifact_policy.py`: PASS; 109 registered prediction artifacts, no raw raster/archive tracked.
- Focused current-page and OMTJ/XB tests: PASS. Full suite: **719 passed, 11 skipped**; skips are integration checks requiring additional competition inputs or unavailable Git history, not passes.
- Note: `scripts/verify_current_artifact.py` is explicitly a legacy verifier for the older `docs/run-card.json` CED91 artifact. The current OMTJ page is verified through `generate_submission.py`, which follows `docs/current-run.json`; do not treat that legacy verifier's different SHA as the current download.
- `docs/s22/run-card.json` remains negative: one experiment; HOLDOUT-DTI 0.066223 (95% CI [0.048015, 0.086803], evaluator `gems57-pooled-hide-v2`, 60,988 withheld positives); final dot overlap 98.57% with the preregistered calibration-lattice witness. No new experiment, TIFF, score projection, or weekly slot was created by this portal-only correction.

## Scope and decision

This is a documentation/rendering correction, not a scientific result or submission approval. The current OMTJ TIFF is a negative research artifact: its values/grid pass local validation, but the strict final-dot uniqueness rule fails. Its estimated leaderboard score is **not estimable**. Do not upload it. No exact score can be inferred for the nine historical submissions without authenticated organizer receipts and a defensible calibration set.
