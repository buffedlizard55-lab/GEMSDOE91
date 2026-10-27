# GEMSDOE91 — independent review, 27 October 2026

## Executive decision

**NO NEW TIFF. NOT OK TO SUBMIT.** This review generated no competition
candidate, ran **zero geological experiments**, and used **zero weekly slots**.
The prompt refers to one assigned method paragraph but contains no identifiable
assignment; the frozen plan records `lane: null`. The plan's 37,654-dot
budget also cannot satisfy the literal directed-overlap rule against one pinned
registry lattice. Do not silently change the budget, omit a registry entry or
copy an earlier TIFF to get around the stop.

**Score estimate:** unavailable; no corrected matched holdout or file-specific
authenticated organizer receipt exists. The user-reported GEMSDOE32 **0.2778**
is a claim, not an `ORGANIZER-CONFIRMED` score for the audited TIFF. It is the
largest of the nine supplied claims, not verified proof of superiority. The
[public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
showed rank 1 **0.4544** on 27 October 2026; that moving public snapshot is
neither a score receipt for GEMSDOE32 nor a prediction for a future file.

[**Download the current negative JSON run card**](run-card.json) ·
[Executive summary](../executive-summary.html) · [Future submission guide](../submission-guide.html) ·
[Ranked untested hypotheses](../review-8e8d86f2/HYPOTHESES.md) ·
[Previous full nine-site table with exact names and hashes](../review-8e8d86f2/REVIEW.md#nine-historical-leaders--claims-files-and-geometric-evidence).

The [historical S22 TIFF](../downloads/gems91-s22-omtj-e1-20261026-a99b8923f0-zeros.tif)
is **downloadable for research only**, not generated in this review and not
eligible to submit. Local format/grid/range inspection passed; its dots are a
98.565889% lattice duplicate, and its geological inputs are compromised. Its
local format result is **not** organizer acceptance. [Current validator](historical-s22-validator.json) ·
[lattice witness](s22-witness.json).

## The nine supplied historical files

The [original frozen raster audit](../s22/nine-site-audit.json) links each
historical TIFF to a Git blob and SHA-256. A corrected [independent recheck](nine-site-recheck.json)
reproduces the Euclidean 3-pixel directed overlaps at full precision. Maximum
below means **the largest fraction of this row's dots within 3 px of one of the
other eight**; it is directional, not byte equality or full-registry coverage.
Every row exceeds the 70% stop. No estimated organizer score is defensible for
any row, and none of these historical files is approved to submit.

| Site | User-reported claim (unverified) | Positive pixels | Worst peer overlap | Status |
|---|---:|---:|---:|---|
| GEMSDOE32 | 0.2778 | 37,654 | 100.00% vs 24 | duplicate |
| GEMSDOE36 | 0.2750 | 38,854 | 97.58% vs 27 | duplicate |
| GEMSDOE28 | 0.2710 | 37,660 | 100.00% vs 24 | duplicate |
| GEMSDOE31 | 0.2708 | 40,199 | 100.00% vs 24 | duplicate |
| GEMSDOE33 | 0.2632 | 41,865 | 99.71% vs 27 | duplicate |
| GEMSDOE25 | 0.2600 | 44,090 | 100.00% vs 24 | duplicate |
| GEMSDOE30 | 0.2600 | 44,090 | 100.00% vs 24 | duplicate |
| GEMSDOE24 | 0.2477 | 60,069 | 100.00% vs 25 | duplicate |
| GEMSDOE27 | 0.2449 | 61,328 | 98.02% vs 24 | duplicate |

The corrected checker excludes an optional candidate from the eight-peer maxima,
uses unrounded values at the threshold and serializes NoData metadata as strict
JSON. Its predecessor's receipt remains frozen and its source archived; the
new check is a separate receipt, not a retroactive alteration.
[Correction manifest](source-corrections.json).

### What the GEMSDOE32 lineage supports — and what it cannot prove

Independent pixel-exact [lineage recheck](nine-site-lineage.json) of five
hash-pinned TIFFs finds:

* GEMSDOE25 and GEMSDOE30 have **identical positive support**, although their
  TIFF bytes and NoData encodings differ.
* GEMSDOE31 is a subset of GEMSDOE25, removing **3,891** pixels at exactly
  one pixel from the pinned catalogue. GEMSDOE32 is a subset of GEMSDOE31,
  removing **2,545** more pixels 1.414–2 pixels away.
* GEMSDOE36 contains the GEMSDOE32 support plus **1,200** pixels (median
  distance to catalogue 14.49 px); it is not an independent full support.

This geometry is consistent with sparse/pruned predictions changing the trade-off
between coverage and false-positive cost. For the official 300 m triangular
kernel, nearby predictions can compete for the *same* truth-side maximum,
whereas unsupported predictions contribute false-positive weight. But a single
new prediction can also cover **several** truth pixels; it is wrong to assume
its truth gain is bounded by its own prediction-side credit. The exact change in
DTI depends on hidden truth and both sides of the metric. The [staff clarification](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/4)
says known pixels are masked exactly, not their neighborhoods; newly mapped
faults can be nearby. Therefore we cannot call all removed dots false positives,
attribute an unverified score difference to pruning, infer hidden truth density,
or conclude a new unique method has beaten GEMSDOE32. Older inverse models and
projections remain hypotheses, not scores or validated causal explanations.

## Why the self-frozen plan stops

The [reproduced preflight](experiment-preflight.json) uses the 5,167,373-pixel
sample footprint and the pinned 206,895-dot lattice reference. Only **6,649**
footprint pixels fall outside its Euclidean three-pixel neighborhood. At a
budget of 37,654 distinct dots, at least 37,654 − 6,649 = **31,005**, or
**82.341849%**, must be near that reference, exceeding the user's >70% stop.
This is a **necessary geometric bound conditional on this footprint, reference
and frozen budget**, not a geological score, not a completeness certificate and
not a proof that every smaller budget must fail. It is not permission to seek a
smaller budget to defeat the rule. The indexed comparison inventory still has
unavailable entries; a comparison against one witness is not universal registry
clearance.

## Shared holdout correction

The historical `label-blind-quadrants-v2` split withheld connected components
and buffered the training domain, but did **not** buffer the catalogue passed
to feature constructors. The reproducible [mask geometry audit](context-buffer-audit.json)
found nearest visible catalogue distances to withheld positives of **2, 2,
3.162 and 3.162 px** across the four folds; **2,240, 911, 1,908 and 1,516**
held truth pixels respectively had visible catalogue within 80 px. Proximity is
not by itself proof that a particular model leaked, and this diagnostic is not
a holdout score.

The shared `vendor/gems57/spatial.py` now creates
`label-blind-quadrants-v3-feature-buffered` folds: whole connected components
are withheld, the training domain and **feature-visible catalogue** are
buffered, and `masked_known` remains separately pixel-exact for scoring. In the
real-data geometry audit all four corrected minima are **80.00625 px**, with
the original evaluation geometry and known-pixel mask retained. The shared
evaluator now requires `masked_known` explicitly rather than silently treating
buffered `visible` as the scoring mask. The old chunked/unbuffered holdout and
truth-shaped legacy folds require explicit legacy-reproduction opt-in. The
shared readiness gate requires all four v3 fold receipts and rejects a recorded
per-quadrant canary over 0.90 even if its pooled maximum passes; this is a
**structural check**, not independent proof of receipt authenticity or of
canary coverage. This policy intentionally recognizes only the reviewed v3
quadrant split; using another sound buffered instrument for promotion requires
a separately reviewed policy change. The pooled DTI formula
and its `gems57-pooled-hide-v2` arithmetic identifier remain unchanged;
implementation SHA-256 and split version distinguish instruments. Archived
originals and active hashes are pinned in [template_pin.json](../../registry/template_pin.json).
Historical scores must not be presented as matched v3 comparisons. No corrected
candidate or incumbent was fitted or scored.

The active shared metric's marginal test now handles nondefault α/β correctly;
the default .2/.8 arithmetic did not change. Tests exercise the generalized
formula against direct recomputation and demonstrate truth-side gain greater
than self-credit. The stopped S22 runner now fails closed even if a receipt is
deleted; its archived historical source remains authenticated. Some old
standalone scripts were built around historical masks and must not be rerun as
promotion pipelines without a fresh provenance, mask and readiness audit.

Separately, the previous input audit found **3,061 finite declared-NoData
cells inside the footprint in each of S22's B13 and B14**. Its original feature
calculation did not mask them. Its saved **HOLDOUT-DTI 0.066223**, 95% CI
**[0.048015, 0.086803]**, `gems57-pooled-hide-v2`, **60,988** withheld
positives, is preserved for arithmetic and provenance only: it is invalid as a
test of the advertised geology, not a corrected holdout or leaderboard
estimate. [Input audit](../review-8e8d86f2/feature-audit.json).
S18 (99.605% lattice overlap) and S23 (99.895%) remain duplicate-stopped;
S23 also has an unresolved band-identity conflict. They are not this review's
new outputs.

## Sources, access and next actions

1. [DrivenData problem and data description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/): new-fault target, 100 m EPSG:32611 grid, [0,1] predictions, pooled distance-weighted Tversky, α=.2, β=.8, 300 m kernel, and external-data licensing/shareability requirement. It says outside bounds should be null/NaN. The cause of the user's prior range error and organizer acceptance of an all-finite zero-outside export are **unknown**.
2. [DrivenData staff — aggregation](https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2): pool metric terms across public test pixels, then compute one index; private aggregation is analogous. [Staff — submission limit](https://community.drivendata.org/t/submission-amount-question/11553/2): website's current displayed quota takes precedence. The authenticated quota and submissions pages require login; neither was accessed.
3. [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) demonstrates a U-Net baseline; it does not establish the hidden leaders' architecture or validate a proposed feature.
4. [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) describes public-domain airborne magnetic/radiometric surveys; survey seams and terrain clearance can confound signatures. [USGS 3DEP](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) says products are free without use restrictions, but required local tile coverage is not verified. [INGENIOUS compilation](https://gdr.openei.org/submissions/1391) lists a CC BY 4.0 page licence; check each linked resource and challenge rights individually.
5. [USGS Southern Gabbs Valley case](https://www.usgs.gov/publications/discovery-a-blind-geothermal-system-southern-gabbs-valley-western-nevada-through) illustrates multiscale evidence for a blind geothermal system, not validation of our proposed raster. A mapped fault prediction is not proof of temperature, permeability, a vent, or a productive reservoir.

Community-mirror hashes verify byte identity, not organizer origin or permission
to redistribute. The current local checkout has hash-checked sample/catalogue,
parent raster, nine-site cache and lattice available for diagnostics; restored
`data/` and `.venv/` are ignored and may not persist. Competition inputs,
private receipts, remaining slots and all external-data rights were not
independently authenticated.

**Next:** obtain the actual lane assignment and a coordinated resolution of
the frozen-plan conflict; verify inputs/rights and complete registry coverage;
run a fresh canary and matched buffered candidate/incumbent holdout; check
surface and final-dot thresholds without exemptions; validate the actual
written TIFF; only a separate selector can approve a slot. Up to three
experiments or two hours is a ceiling, not an instruction to bypass a stop.
A complete, detailed reproducibility record and previous hypotheses remain in
[the prior review](../review-8e8d86f2/REVIEW.md).
