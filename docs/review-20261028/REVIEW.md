# Current review — 2026-10-28

**Verdict: NEGATIVE / NOT OK TO SUBMIT.** This review generated no new TIFF,
ran no geological experiments and used no competition slots. The prompt invokes
an assigned single-method paragraph but does not provide one. Inventing an
assignment would defeat the parallel-run protocol. There is no `data/` directory
in this checkout, despite historical manifest fields that record earlier runs.
Those fields are not a live availability check. The Python environment also
lacks numpy, scipy, rasterio and pytest. This is not evidence that competition
data are unavailable everywhere.

The existing [S24 E2 research TIFF](../downloads/gems91-s24-cckm-e2-37654dots-20261027T190354Z-d69650bd-zeros.tif)
was generated in a **previous** session. This review recomputed its SHA-256:
`aba3fb405cfa3a22ffb8d7f9dbfed5b0ed71993564403517842994690f6c8b1c`.
Download is for research only. Do not submit: its historical run card reports a
literal registry duplicate and does not establish superiority over its control;
two registry files were missing. The old local format receipt is not organizer
acceptance and this review did not rerun the raster validator. The prior
HOLDOUT-DTI is **0.075896**, 95% CI **[0.065569, 0.086758]**,
`gems57-pooled-hide-v2`, 60,988 withheld positives. It is not a leaderboard
estimate; the earlier split is not directly comparable to the corrected
buffered split. [Prior card](../s24/e2/run-card.json), [split audit](../review-ad43b4e5/context-buffer-audit.json).

## Nine-site executive summary

[Historical table with exact filenames, sources and peer checks](../s24/REVIEW.md#per-focus-site-answer-highest-supplied-claim--best-file--uniqueness).
Scores below are **user-reported claims**, not organizer-confirmed receipts.
They are not estimates for a new raster. No historical file in this table is
eligible as a *new unique* submission under the directed-overlap rule.

| Site | Best reported historical claim | Unique vs peers? | New submission |
|---|---:|---|---|
| GEMSDOE24 | 0.2477 | No | No |
| GEMSDOE25 | 0.2600 | No | No |
| GEMSDOE27 | 0.2449 | No | No |
| GEMSDOE28 | 0.2710 | No | No |
| GEMSDOE30 | 0.2600 | No | No |
| GEMSDOE31 | 0.2708 | No | No |
| GEMSDOE32 | 0.2778 | No | No |
| GEMSDOE33 | 0.2632 | No | No |
| GEMSDOE36 | 0.2750 | No | No |

Among those claims, GEMSDOE32 is highest, but its score is not bound to an
organizer receipt. [Support lineage](../review-ad43b4e5/nine-site-lineage.json)
shows it is a subset of GEMSDOE31. Removing near-catalogue predictions might
improve the coverage/false-positive trade-off, but the support geometry does
not prove why the score changed or predict a higher score. Higher performance is
possible in principle, not established by these data. The supplied leaderboard
numbers conflict; no current leaderboard was independently checked in this run.

## Three passes and next actions

1. **Review:** inspected the current front door, S24 preregistration, run card,
   prior peer and capacity audits, manifest, local data directory, and environment.
   Re-hashed the S24 artifact and all files in the shared-template hash pin; all
   matched. No new experiment was authorized or performed.
2. **Adversarial check:** prior S24's self-assigned lane is explicitly not a
   coordinator assignment. Its research-only TIFF does not pass the literal
   full-registry rule. The capacity bound is conditional on the prior fixed
   budget, footprint and lattice, not proof that every possible candidate fails.
   Historical `local_present` manifest entries do not reflect this checkout.
3. **Re-check and communication:** placed this current review ahead of historical
   status on the README and Pages front door; retained historical artifacts and
   their warnings. No new validation, current leaderboard value or score is
   asserted. See [machine-readable run card](run-card.json).

The [prior ranked hypotheses](../s24/preregistration.md#ranked-hypotheses-qualitative-not-score-forecasts)
include five candidates and disclose implementation overlap, missing-data risks,
and the unverified 3DEP coverage gate. CCKM was subsequently tried and did not
pass; those rankings are historical, not a new lane assignment. A future run
needs an actual coordinator-assigned method, restored authorized hash-pinned
inputs, complete registry, the corrected shared evaluator, per-feature canaries,
matched incumbent and paired uncertainty, both duplicate checks, writer and
independent validator. A separate selector must decide any submission slot.
Network access here is restricted to GitHub and package registries, not the
DrivenData or Dropbox hosts. We have not authenticated to DrivenData or verified
its current quota. Do not infer external-data rights from a community mirror.

Official references for manual verification: [competition problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[organizer reference solution](https://github.com/drivendataorg/gems-prize-reference-solution),
[USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
[USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services).
These links are supplied for review; none was fetched independently in this run.
