# Submission safety audit — 2026-10-24

**Download: existing research artifacts only. Submission: NOT OK. No new TIFF was generated.**
This is an infrastructure negative, not a new geological result. No slots used.
The requested unique eligible submission remains unfulfilled; making a new byte
hash or weakening a duplicate rule would not satisfy it.

## Pass 1: implementation and observed evidence

Read README, current CED run card/review, S10/H91 hypothesis records, shared
holdout and writer interfaces, canonical evidence verifier, Pages workflows,
and readiness tests. This was a targeted review, **not** a line-by-line audit of
every historical file or every external site.

The assigned single-method paragraph is absent from this prompt. The historical
CED lane is explicitly unassigned and stopped on a duplicate; S10 exhausted its
budget. H91 uses a different evaluator and excludes a dense lattice from some
novelty claims. None authorizes silently adopting another parallel lane.

Re-downloaded the two small pinned format inputs through `restore_data.py`
from the existing immutable GitHub mirror. Both SHA256 and byte lengths match
`registry/data_manifest.json`. Re-read the actual CED TIFF and ZIP using
`verify_current_artifact.py --with-data`: all format checks PASS, including
finite values, [0,1], sample CRS/shape/transform and zero catalogue mass.
This verifies mirror identity, **not** organizer authentication or data-use rights.
The feature stack was not downloaded and no geological experiment was run.

`verify_evidence.py` PASS: canonical source pins, pooled arithmetic, fold
receipts, feature canaries and duplicate-stop accounting remain consistent.
It does not rerun the model or turn historical holdout scores into live scores.

### Shared gate fixed, no private evaluator fork

`src/gems91/readiness.py` previously accepted a positive paired delta with an
inverted or nonfinite confidence interval, and accepted novelty/canary PASS
labels without testing recorded measurements. It now checks finite bounded
numbers, ordered intervals, withheld-positive count, nonempty evaluator/split
identity, canary threshold, both registry measurements, nonempty/equal completed
comparison counts, and typed receipt sections. Missing or malformed evidence
fails closed rather than raising or approving. Receipt authenticity still needs
the separate byte/provenance verifier; a fabricated self-consistent JSON is not
scientific evidence. Neither shared evaluator nor writer was privately forked.

## Why GEMSDOE32 might have improved — not a score forecast

Fetched the [GEMSDOE32 page source at current commit
098f3af9508a135277ef4d1bf2266e2e448be814](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/098f3af9508a135277ef4d1bf2266e2e448be814/docs/index.html).
It describes removing dots within two pixels of the catalogue, and explicitly
states **“NO ORGANISER SCORE EXISTS for this or any artifact in this repository.”**
That source cannot authenticate the user-reported benchmark. No current
leaderboard score or submission receipt was fetched in this run.

Mechanistic reasoning: pruning a prediction improves DTI only when its removal
saves enough false-positive contribution relative to the lost truth coverage.
Near-catalogue pruning can remove redundant mass, but can also erase useful
continuations into hidden segments. The reported improvement is not proof of
causality: ancestor changes, calibration selection and hidden-truth distribution
are alternative explanations. Sparse placement may be metric-efficient without
being a better geological detector. An exact receipt tied to bytes, a controlled
ablation on identical buffered folds, and independent validation are needed.
There is **no defensible numerical forecast** of beating the reported benchmark.

## Ranked future hypotheses (not an assigned lane)

Qualitative ordering by potential information gain / expected DTI benefit, then
cost. These are falsifiable proposals, not established geology or measured
improvements. Novelty is relative to the inspected implementations, not proven
fleet-wide. Layer meanings/units must be checked against the pinned feature
metadata before any execution. None requires proposed external acquisitions.

| Priority | Layer and transform | Why potentially off-catalogue | Difference from inspected work | Named non-fault mimic | Cost |
|---|---|---|---|---|---|
| First | Detrended elevation + gravity: paired valley-floor longitudinal-profile change points across a gravity edge, with downstream/upstream symmetry control | Repeated drainage offsets may expose subtle buried range-front displacement without a mapped scarp | Tests paired drainage profiles, not CED centroids, S10 basement gradients or H91 tilt deprojection | Alluvial-fan avulsion | High; coarse elevation may not resolve channels |
| Second | RTP + gravity: along-edge change in local cross-spectrum phase, conditioning on cross-edge amplitude | Fault juxtaposition may interrupt a lithological boundary rather than create the strongest new edge | Tests along-contact discontinuity, not edge intensity or cross-field centroid separation | Intrusive facies transition | Medium |
| Third | Conductivity + basement depth: paired opposite-sign conductivity residual lobes across depth-edge normals, after spatially cross-fitted basin-depth trend removal | Compartmentalized fluid pathways may create local discontinuities beneath cover | Tests antisymmetric residuals, not conductivity ridges or clay-cap intersections | Playa salinity gradient | Medium |

These proposals are **not cleared as viable**: there is no assigned lane, full
registry clearance or comparable-best receipt. Before implementing one, freeze
one method and baseline; use the shared cache/evaluator/writer; run each feature
alone as a leakage canary; check continuous-surface novelty before placement and
both tests on final dots; stop on the literal duplicate thresholds. No new
candidate should be tuned against historical leaderboard reports.

## Pass 2: adversarial review

Added synthetic policy tests for NaN, infinity, giant integers, booleans, strings,
null sections, reversed/invalid intervals, exact threshold boundaries, canary
violations, duplicate measurements despite PASS labels, and partial registry
coverage. These are engineering tests, not geological experiments. Existing
portal reproducibility, local links, artifact identity and evidence tests run
alongside them. No historical measurement or canonical run card was overwritten.

## Pass 3: original-request reconciliation

- Automated format validation and easy research download already exist and were
  rechecked. This run does not claim a new eligible TIFF.
- The README now starts with this review's actual status; older session blocks
  remain historical. The operating brief remains a restatement, not a verbatim
  archive of the long prompt.
- “ORGANIZER-CONFIRMED” must mean a submission-page receipt for a score, not a
  public leaderboard scrape. Older S10 wording uses this label more broadly;
  do not use it to authenticate this project's submissions.
- The full-source research request is limited by outbound hosts: GitHub and
  package registries only. DrivenData, USGS, DOE/NLR, Dropbox and literature
  hosts were not fetched this run. Prior-session claims are not re-verification.
- No selector step or weekly submission occurred. Legal eligibility and signed
  attestations cannot be truthfully automated on behalf of the competitor.

## Verified links and next work

| Link | Verification in this run |
|---|---|
| [Official reference repository](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b) | GitHub HEAD identity retrieved; not a complete notebook audit |
| [GEMSDOE32 source](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/098f3af9508a135277ef4d1bf2266e2e448be814/docs/index.html) | Page source fetched and quoted above; not an organizer source |
| [Official data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) | Not accessed; requires authorized access for provenance confirmation |
| [Official problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) | Not accessed this run |
| [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) | Not accessed this run |

Next session: resolve the assigned lane and frozen registry definition without
silently exempting dense references; authenticate input provenance; establish a
shared-split best baseline and evaluator equivalence tests; then run at most the
budgeted experiments. Keep scientific promotion separate from slot allocation.
