# Slot selection status — 2026-10-24 UTC

## No candidate selected

**There is no active slot recommendation and no TIFF approved for submission.** This project has not selected a weekly submission slot. Promotion is a separate selector step and must remain separate from experimentation, as required by the parallel-run protocol.

The official [GEMS rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) state that competitors may make up to three scored submissions per week, subject to the live competition website, and must select one final submission across both prize phases. Final content is due by 5 p.m. ET on the submission-deadline date; the current deadline date is not verified here. Finalists must provide reproducible code assets and documentation. Check the current DrivenData page before any future selector decision.

## Why the queue is empty

- The method-lane paragraph was not supplied.
- The shared buffered-segment holdout evaluator and submission writer are not in this checkout.
- The official feature/label data and fault segments are absent locally.
- No compliant HOLDOUT-DTI baseline or candidate result with evaluator version, withheld-positive count, and 95% CI is recorded.
- The previously advertised GEOD TIFF has a historical reported dot overlap above the protocol duplicate threshold and is not eligible for promotion.

## Promotion gate for any future slot

A candidate may enter a separate selector only after it beats the current compliant HOLDOUT-DTI best using identical buffered whole-segment folds, clears the single-feature leakage canaries, passes surface and final-dot novelty checks against every registry raster, passes the exact official GeoTIFF format gate, and has an approved short note. A missing gate is not a pass. No score projection is sufficient.

Historical variant and proxy records remain in `ledger/` and `evidence/` for audit. Their `MODEL`, `PROXY`, and `CLAIM` values are not HOLDOUT-DTI or organizer receipts and do not authorize a slot.
