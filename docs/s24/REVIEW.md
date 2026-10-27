# S24-CCKM session review — 2026-10-27

Branch `arena/61b1192a-gemsdoe91`. Experiments used: **2 of 3**. Weekly
submission slots used: **0**. Values: **Maximize P(Win)** — do not spend a slot
on a surface that does not beat its own control; **Own the Outcome** — the
negative result, its receipts and its failure modes are preserved and linked.

## Executive verdict

**A new, unique-vs-the-nine, format-valid TIF was generated. OK TO DOWNLOAD:
YES (research only). OK TO SUBMIT: NO.**

| File to download (research) | Estimated leaderboard score | Unique vs GEMSDOE24/25/27/28/30/31/32/33/36? | OK to submit? |
|---|---|---|---|
| [`gems91-s24-cckm-e2-37654dots-20261027T190354Z-d69650bd-zeros.tif`](../downloads/gems91-s24-cckm-e2-37654dots-20261027T190354Z-d69650bd-zeros.tif) (SHA-256 `aba3fb405cfa…`) | **Unavailable** — no receipt, no validated calibration. HOLDOUT-DTI 0.075896 [0.065569, 0.086758] (`gems57-pooled-hide-v2`, 60,988 withheld) and SGMC-offcat diagnostic 0.054493 are labelled diagnostics, not estimates | **YES vs the nine** — max 18.76% of dots within 3 px of any single leader; surface \|ρ\|max 0.104. **NO vs the literal full registry** — 100% vs the 206,895-dot calibration lattice | **NO** |
| [`gems91-s24-cckm-e1-20000dots-20261027T185803Z-fcbfbe32-zeros.tif`](../downloads/gems91-s24-cckm-e1-20000dots-20261027T185803Z-fcbfbe32-zeros.tif) | Unavailable. HOLDOUT-DTI 0.045952 [0.037996, 0.054356], same evaluator/count | YES vs nine (max 19.24%); NO literal (lattice 100%) | NO |

Front door with the generated table: [`executive-summary.html`](executive-summary.html)
(rendered from JSON receipts by `scripts/render_s24_portal.py`, never hand-typed scores).

## Per focus-site answer (highest supplied claim → best file → uniqueness)

Claims are **USER-REPORTED in the session prompt, not ORGANIZER-CONFIRMED**; no
receipt linking any score to any TIFF exists in this repo. "Best file" is the
SHA-pinned file in `docs/s22/nine-site-audit.json`; runner-up claims in the
prompt are all lower (checked line by line: 24→0.0859, 25→0.0742,
27→0.2250/0.2190, 28→0.2708/0.2707/0.2649 then 0.0217/0.0206, 30→0.1462,
33→0.0963, 36→0.1647).

| Site | Best claimed file | Claim | Unique among the nine? | Submit as new? |
|---|---|---:|---|---|
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (`c55bafc4…`, 37,654 px) | 0.2778 | No (100% vs GEMSDOE24-directed audits; ≥93% class) | No |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-…-zeros.tif` (`e1589102…`) | 0.2750 | No — 97.58% vs 27 | No |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-…-nan.tif` (`5556aa14…`) | 0.2710 | No — 100% vs 24 | No |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-…-nan.tif` (`07b6db44…`) | 0.2708 | No — 100% vs 24 | No |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-….tif` (`87f857d5…`) | 0.2632 | No — 99.71% vs 27 | No |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-…-nan.tif` (`91eae1ca…`) | 0.2600 | No — identical support to 30 | No |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-….tif` (`8cf893ea…`) | 0.2600 | No — identical support to 25 | No |
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-…-nan.tif` (`68d0e2e4…`) | 0.2477 | No — 100% vs 25 | No |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-…-nan.tif` (`33003374…`) | 0.2449 | No — 98.02% vs 24 | No |

(Directed overlap percentages are the frozen nine-site audit's; fresh SGMC
diagnostics for the same bytes are in
[`sgmc-diagnostic.json`](sgmc-diagnostic.json): the family clusters at
0.093356–0.101163, R0 = 0.095386 — reproducing the earlier fleet receipt
`r0_02778_dti 0.095386` exactly.)

## Why 0.2778, and can this approach beat it? (evidence + judgement)

Measured facts: the nine files' claims anti-correlate with dot count
(60,069→0.2477 and 61,328→0.2449 at the low end; 37,654→0.2778 and
38,854→0.2750 at the top; the generated page computes the Spearman value from
the audit JSON). With the official DTI (α=0.2, β=0.8, 300 m triangular
kernel; [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)),
dots spaced so their 300 m kernels tile truth instead of stacking on it remove
false-positive weight almost for free — a plausible mechanism for the pruning
ladder h19-5 → dotted → b2. **Not proven**: no receipts, ≥93–100% shared
support (these are edits of one raster family, not nine experiments), and a
single score cannot identify TPw/FPw/FNw separately.

Our paired evidence says the CCKM surface is not the way past 0.2778:

- E2 vs `control_gravgrad` (same 37,654 budget/folds): Δ HOLDOUT-DTI
  +0.004766, 95% CI [−0.003627, +0.012584] — the kurtosis contrast adds nothing
  established over plain |∇B13| ranking.
- SGMC off-catalogue diagnostic at the same budget: E2 0.054493 vs R0
  0.095386 (57%). SGMC is proxy truth, but a 43% deficit on the only
  live-analogue check available makes "likely beats 0.2778" indefensible.
- Budget *does* matter paired: 20k→37,654 on the identical surface gained
  +0.029944 [0.026266, 0.033683] HOLDOUT-DTI. Emission economics are real;
  surface quality is the binding constraint.
- Instrument bias warning: on `spatial.folds` hide-and-recover the R0 raster
  scores 0.006697 because its emission collar used the *full* catalogue,
  including segments this instrument withholds — recovery is then nearly
  impossible by construction. That number says nothing about R0's claimed
  live behaviour, where hidden faults are off-catalogue, and it is why no
  holdout→leaderboard conversion is offered. Hide-and-recover tests
  rediscovery of *known* traces; the live target is *expert-mapped new*
  faults (problem description) — a distribution shift every estimate must
  survive, and none here does.

The fetched public leaderboard on 2026-10-27 was #1 = 0.4544, #2 = 0.3916,
#22 = 0.3261 ([leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/));
the prompt's 0.4413 and 0.3195 are stale. How the 0.4544 entry was made is not
knowable from here and is not guessed.

## What was actually done (three passes)

**Pass 1 — implement + verify.** Restored SHA-pinned inputs (419 MB feature
stack re-hashed), 62/64 frozen registry rasters and all nine leaders
(re-hashed). Label-blind band checks: B03 vs |∇B14| r = 1.000000
(5,135,228 eroded-valid px), B05 vs |∇B13| r = 0.961918, B18 vs ∂xB13
r = 0.948155. Preregistered five ranked hypotheses
([preregistration](preregistration.md)); implemented the rank-1 CCKM surface
(`src/gems91/cckm24.py`, masked kurtosis — NoData *excluded*, never filled)
with synthetic tests; ran E1 via shared folds/evaluator/writer.

**Pass 2 — adversarial review.** Found and recorded: (a) E1 does not beat its
gravity-gradient control; (b) the R0 holdout arm is structurally handicapped
(above); (c) literal-registry failure is driven by three dense references
(206,895 / 192,231 / 272,853 positive px) — against competitive-density
single-submission rasters the max directed overlap is 53.1% (our own E1
subset) and ≤36.4% for all others at E1; (d) a parallel-edit race in the
runner refactor briefly left undefined names — caught by `--help` failure,
fixed sequentially, re-verified; (e) new artifacts now registered in
`registry/artifact_policy.json` and the independent download audit re-run
(117 files, ours PASS). Then E2 under a written
[amendment](preregistration-e2.md): identical surface, fleet budget,
recomputed 20k arm reproduced E1 to all printed digits
(0.04595216362196115), proving determinism.

**Pass 3 — re-check against the request.** Executive-summary page generated
from receipts with the required *file / estimate / uniqueness* table and an
unmissable NOT-OK-TO-SUBMIT decision; submission how-to (selector, quota,
SHA check, ≤140-char note, receipt = only ORGANIZER-CONFIRMED path);
range-error mechanism addressed by the fail-closed writer (all-finite
[0,1], sentinel rejected). Full pytest suite re-run after every change.
E3 was **not** spent: H2 (granulometry) would be a second weak single-surface
test that cannot overturn the submit verdicts (literal-registry policy +
selector), so the remaining experiment is more valuable reserved for a
supervised/DEM surface with its own preregistration.

## Irregularities flagged (for the next session)

1. **Lane paragraph still missing** from the prompt; this lane is self-assigned
   from the prompt's own "validate the top candidate" instruction. Recorded in
   both preregistrations.
2. **Literal duplicate rule vs dense registry is unsatisfiable** by any
   geology-driven raster at useful budgets (6,649 uncovered px; capacity proof
   in run cards). A human policy decision (e.g., scope the registry to actual
   submissions) is required; we did not quietly exempt anything.
3. **Official format text vs fleet practice**: "data outside the bounds is
   null or nan" vs zeros/`nodata=None` files with reported scores. Unresolved
   without an organizer receipt.
4. **Inputs are community mirrors**, SHA-pinned but not authenticated
   organizer downloads; data-use terms for committing derived rasters remain
   the repo's standing assumption (IR-91-09), not re-verified here.
5. **2 of 64 frozen registry references remain missing** (quarantined GEOD
   pair); completeness is UNVERIFIED, stated in every receipt.
6. **Prompt leaderboard values stale** (0.4413/0.3195 vs fetched 0.4544).
7. **Band-06 semantics conflict** from the prior audit stands (we used only
   B13/B14, corroborated internally; external authentication still absent).

## Next steps that would actually raise P(Win)

1. Decide the registry-scope policy for dense calibration/union rasters
   (human/selector call) so "unique" is satisfiable without gaming geometry.
2. Build on the official 1 m DEM link list (data page, login-gated from this
   sandbox) + supervised multi-band surface; validate on *detached*-segment
   and SGMC-style off-catalogue instruments, not only quadrant recovery.
3. Keep the paired-control discipline: any new texture term must beat
   |∇gravity| + |∇magnetics| controls at fixed budget before it earns a surface.
4. Only after a candidate beats matched controls **and** the SGMC reference
   band (≥0.095 at fleet budget) should a selector consider a weekly slot.

## Official / trusted sources used

- DrivenData problem description & metric/format: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>
- DrivenData leaderboard (fetched 2026-10-27): <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>
- DrivenData submissions page (authenticated; not accessed by tooling): <https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/>
- Reference solution: <https://github.com/drivendataorg/gems-prize-reference-solution>
- USGS GeoDAWN (DOI 10.5066/P93LGLVQ): <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>
- INGENIOUS: <https://gbcge.org/current-projects/ingenious/> · GDR 1391: <https://gdr.openei.org/submissions/1391>
- Rules PDF: <https://docs.nlr.gov/docs/fy26osti/96647.pdf> · EPSG:32611: <https://epsg.io/32611> · Tversky index: <https://en.wikipedia.org/wiki/Tversky_index>

## Run cards

Machine-readable cards (protocol fields: hypothesis; mechanism; named mimic;
HOLDOUT-DTI + CI; correlation/overlap; raster SHA-256; validator output;
≤140-char name/note; verdict): [`run-card.json`](run-card.json) (E1),
[`e2/run-card.json`](e2/run-card.json) (E2). Both verdicts: **negative**.
