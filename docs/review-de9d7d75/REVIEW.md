# Three-pass repository review — 2026-10-28

Branch: `arena/de9d7d75-gemsdoe91`. **NO NEW TIFF. OK TO SUBMIT: NO.**
Zero geological experiments, zero competition slots, no upload. This negative
review is intentional: the prompt requires an assigned lane and a holdout-best
win, neither established for the latest proposed release.

## Pass 1 — inspect and verify

Read the README and standing project brief, experiment plan, prior S25-TLF and
S25-FABRIC cards, shared preflight, runner, portal renderer, and nine-site table.
The standing prompt is already preserved under README's Full Project Brief;
the current review links it as required rather than duplicating it yet again.

- Shared experiment preflight blocks: no assigned method paragraph; complete
  capacity/registry evidence unavailable. See `preflight.json` (before restoring
  small format inputs). This is not an authenticated lane assignment.
- Existing S25-TLF TIFF and ZIP have matching archived hashes. Fresh rasterio
  checks confirm one float32 band, expected fixed grid, all finite values in
  [0,1], and 60,000 positive cells. ZIP contains exactly those TIFF bytes.
- Restored the two small sample/catalogue inputs via the existing
  `scripts/restore_data.py --only sample_submission,existing_faults`, verified
  their pinned SHA-256, and reused `scripts.audit_downloads.inspect_raster`.
  Fresh reference checks PASS: CRS/shape/transform, finite [0,1], no NaN inside
  footprint, zero outside, and pixel-exact catalogue masking. These are local
  checks against hash-pinned mirrored data, not organizer acceptance.
- Fetched the official reference repository README and HEAD commit through
  GitHub API. Archived source and commit receipt in `evidence/review-de9d7d75/`.
  Its CPU-only environment contradicts the old claim that training absolutely
  requires a GPU. Training speed and data availability remain separate issues.

## Pass 2 — adversarial review and fixes

1. **Unsupported promotion.** The S25-TLF run card unconditionally wrote
   `verdict: promote` and `ok_to_submit: true`. Its review admits it did not beat
   the historical holdout best and used a self-assigned lane. Corrected to
   negative; unchanged numerical history and original card archived.
2. **Incomplete registry.** Nine leaders plus local downloads do not constitute
   the unchanged full registry. Missing synthetic references cannot be exempted
   silently. Pre-placement surface checks were not established. No global
   uniqueness clearance is supported.
3. **Incorrect rank statistic.** Runner used `argsort(argsort(x))`, which assigns
   arbitrary distinct ranks to ties. It is not Spearman's average-rank statistic,
   especially for large constant/background regions. Historical correlations
   remain archived but do not validate a lane. Source now uses average ranks;
   no corrected numerical correlations are invented or reported as rerun.
4. **Uncalibrated estimate.** Prior 0.36 was the midpoint of two assumptions,
   bounded by a user-reported leaderboard figure. It was not cross-validated
   calibration or a predictive interval. Withdrawn from current guidance; score
   estimate and organizer-confirmed result are null.
5. **Unsafe renderer.** Root renderer previously interpreted one mutable card
   boolean as clearance and used alternate wording to bypass a literal-text
   safety test. It now always distinguishes research availability from slot
   approval. Corrected dedicated renderer uses archived measurements, names
   uncertainty, lists all nine sites, and never prints upload approval.
6. **Experiment budget.** Historical S25-TLF already consumed 3/3 experiments.
   Its command now exits blocked before reading inputs or generating artifacts;
   changing sessions must not reset a historical experiment budget.

## Pass 3 — original requirements and remaining gaps

The executive summary has a direct research TIFF and ZIP download, name, short
note, SHA-256, nine-site file/score/uniqueness table, unambiguous submit verdict,
and exact conditional submission steps. No human visual inspection is required
for local checks. No local format result is mislabelled as scientific approval.
New regression tests cover byte integrity, corrected-vs-original card lineage,
mutable flag rejection, and deterministic summary rendering.

Four ranked, explicit geological proposals are in `HYPOTHESES.md`. They are not
authorization to leave the unspecified lane, proven novel across all parallel
work, or promised score improvements. They require restored feature cache,
full registry and a frozen comparable incumbent. No extra external dataset is
assumed obtainable. The existing shared metric and writer are not forked.

### What can and cannot be concluded about the leaders

The nine-site table is historical repository evidence, not a live refresh. All
named scores remain **USER-REPORTED** until an organizer submission-page receipt
is supplied; none is ORGANIZER-CONFIRMED. GEMSDOE32 has the largest reported
score among these nine. Shared support and dot thinning plausibly explain some
ordering through false-positive economics, but do not prove causal attribution
or that a unique candidate can exceed 0.2778. Claims of 0.3195, 0.4413 and 0.4544
refer to different reported dates/sources; this review verifies no current board.

Historical S25-TLF **HOLDOUT-DTI** = 0.120456, 95% CI [0.105729, 0.134593],
`gems57-pooled-hide-v2`, 60,988 withheld positives. This is attributed to its
saved receipt, not recomputed here. Its reported historical best of 0.2678 lacks
a freshly matched comparison here; no conclusion of a best-incumbent win is
supported. Winning against random dots is insufficient under the request.

### Next steps, in order

1. Obtain an explicit single-method assignment and frozen complete registry
   policy without exempting inconvenient references. Do not request credentials.
2. Restore pinned feature cache, provenance/rights and full registry through
   existing tooling. Re-run capacity preflight before expensive work.
3. Freeze same-fold/same-budget incumbent and untouched evaluation plan; check
   each feature canary, both uniqueness phases and paired HOLDOUT-DTI improvement.
4. Only if every gate passes, shared writer generates a new unique TIFF and
   machine validation receipt. Separate selector checks authenticated weekly cap.
5. Archive an organizer receipt after an approved submission; then calibrate
   estimates with genuinely independent anchors, not midpoint assumptions.

### Access limits

This sandbox allows GitHub and package registries, not direct DrivenData, USGS,
NLR, OpenEI or Dropbox downloads. Existing mirrored sample/catalogue were
obtainable; full training features and registry were not restored because no
experiment is authorized. No authenticated DrivenData account, live weekly-cap
check, hidden labels or submission receipt is available. Official external links
in the shortlist are labelled as manual-review links, not fetched evidence.
The target is faults; a predicted fault does not establish geothermal vents.

Verification command results are recorded in `verification.json`. Originals are
retained for audit, not as current recommendations. **Maximize P(Win)** means
not wasting a slot; **Own the Outcome** means correcting the unsafe claim.
