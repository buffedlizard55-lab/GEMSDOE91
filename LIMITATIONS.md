# GEMSDOE91 limitations and blockers — 2026-10-24

## Current decision

**NOT APPROVED — no TIFF is available to download or submit.** The current run was blocked before experiment. This does not falsify any geological hypothesis and is not a HOLDOUT-DTI result.

## Hard blockers

1. **No assigned lane paragraph.** The user prompt refers to one unique method paragraph but does not include it. Picking a lane autonomously would violate the parallel-run protocol.
2. **No shared evaluator or writer.** `evaluate_holdout.py`, `submission_writer.py`, and the template path are absent from this checkout. The local `src/gems91/proxy.py` does not meet the prescribed whole-segment-buffered, fold-specific, pooled-DTI design; it must not be described as HOLDOUT-DTI or forked privately as a substitute.
3. **Competition files are not local.** `python scripts/restore_data.py --check` reports all 15 pinned entries missing under `data/`. The official data page redirects to login; the entrant must be registered to access the official data. Public GitHub mirrors are recorded in the repository, but their provenance/permission is not re-established by their existence. No data were downloaded in this review.
4. **No compliant baseline or segment geometry.** There is no compliant HOLDOUT-DTI best in this checkout, no evaluator-versioned segment-level CI, and no local vector fault-segment file for buffered whole-segment folds. Without these, neither validation nor a promotion decision is possible.
5. **Local DTI implementations disagree.** The official problem page defines per-truth-pixel TP credit as the maximum probability × kernel contribution. `scripts/dti.py` uses a max; `src/gems91/metric.py` sums all nearby contributions. They are not interchangeable, and neither is the absent shared `evaluate_holdout.py`. This review does not choose or silently patch a private evaluator; no local metric output is accepted as HOLDOUT-DTI.
6. **The prior GEOD candidate trips the protocol stop.** Its prior page reported 93.2% final-dot overlap within 3 px of the parent, above the 70% duplicate threshold. The input needed to reproduce the percentage is absent; because the recorded value exceeds the hard limit, the project fails closed and treats it as a duplicate-risk stop.
7. **No upload receipt.** This repository has no organizer submission-page receipt for a GEMSDOE91 candidate. The reported `0.2778` for H33-2-B2 is an unverified site/user claim; the current GEMSDOE32 page says no organizer score exists for its artifacts. The public leaderboard's `0.4413` at rank 1 is a PUBLIC-LEADERBOARD OBSERVATION only; neither HOLDOUT-DTI nor ORGANIZER-CONFIRMED for this project.

## Format and range-error caveat

The official problem page requires a single float32 band, EPSG:32611, 100 m resolution, matching bounds, values in `[0,1]`, and null/NaN outside bounds. The old NaN-outside artifact's reread values were {0,1} in its finite cells, while its old zeros-outside twin had finite values outside the footprint and is not an acceptable substitute for the official outside-bounds rule. The user's historical range error cannot be diagnosed without the exact uploaded file and organizer-side validation output. No current file is approved.

## External-source and research limits

The five current hypotheses use layer families described by the official competition page and require no new external dataset. Their local files are absent. If a later idea needs new LiDAR or another source, it must name the exact free official source, check actual access and usage rights, and add the provenance before it is called viable. The [official source register](docs/SOURCES.md) records which pages were fetched and where access failed.

The public leaderboard can be checked through the official page, but no submission-site API or entrant session is available in this environment. A live public leaderboard observation cannot reveal private-test performance or replace the entrant's submission receipt.

## Operational limits

- No competition login, credential handling, upload, or slot selection occurs here.
- The official rules require the registered entrant to disclose generative-AI use in the narrative where applicable and remain responsible for accuracy and authorship.
- A separate selector must authorize any candidate promotion within the live weekly cap; no candidate is currently selected.
- Current run card: [`docs/run-card.json`](docs/run-card.json). Current slot status: [`SLOT_PLAN.md`](SLOT_PLAN.md).
