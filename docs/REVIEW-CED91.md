# CED91 review — 2026-10-24

## Executive verdict

**OK to download the newly generated research TIFF. NOT OK TO SUBMIT it.**
The project has completed its inspection automatically; no human inspector is needed to determine this negative verdict. A competition-approved, protocol-unique submission has **not** been achieved. No weekly slot was selected or used.

- File: `downloads/gems91-ced-v1-20261024-d35670b28c81.tif` (120,391 bytes).
- SHA256: `a29e79d400d0fb26ebcbc0be6b1dcf66b17dfedf9ded1ef8c9a53678c16553ee`.
- Fixed method: [parent-free CED91 preregistration](HYPOTHESES_CED.md).
- **HOLDOUT-DTI** (`gems57-pooled-hide-v2`, 60,988 withheld positive pixels): **0.062153**, 95% CI **[0.049910, 0.075115]**.
- **HOLDOUT-DTI paired candidate minus magnetic-only control** (same evaluator and positives): **+0.010775**, 95% CI **[−0.004310, +0.026597]**. The interval crosses zero. This is not evidence of a resolved improvement.
- Engineering validation: one float32 band; every pixel finite and in [0,1]; no nodata sentinel; exact sample CRS/shape/transform; zero outside-footprint and catalogue mass; single-TIFF ZIP round trip. These are engineering observations, not scores.

## Why the experiment stopped

The pre-placement continuous surface cleared all **64 indexed raster** comparisons, maximum measured full-footprint Spearman **0.024291** (engineering novelty statistic, not DTI).

The final dots were checked against the same ordered index. At reference **27**, `calib_r13lattice_00904.tif`, the directed candidate-dot overlap within 3 pixels was **0.999125**, exceeding the literal **0.70** limit. Its final dot-raster rank correlation was approximately **−0.000091**. Thus overlap and rank correlation measure different things: low rank correlation cannot override the overlap rule. The runner logged **DUPLICATE**, stopped immediately, and left the remaining **37** final comparisons untested. No second geological experiment was run.

[Forensic diagnostic](parent-forensics.json): that lattice has 206,895 positive pixels and its 3-pixel cover reaches 5,160,724 of 5,167,373 footprint cells (**99.8713%**). This is a near-universal geometric-cover reference. It can mark unrelated predictions duplicate under the literal rule. It is **not proof that CED copied its geological method**. Nevertheless, no saturated-reference exemption, >0.5 support threshold, registry deletion, or threshold adjustment was authorized or applied. The result remains negative. Resolving this protocol conflict belongs to the fleet owner/shared selector, not post-result private gate changes.

The exported pixels were generated from two cached input bands. No previous submission raster enters CED feature construction or dot placement. The new file hash differs from the indexed files, but **byte uniqueness is not protocol uniqueness**.

## Holdout and leakage audit

- Shared source: `GEMSDOE78@30f1ab9400f92036b0bc613425f1b5b6046f3897/vendor/gems57`; modules copied **byte-for-byte**, pins in `registry/template_pin.json`. There is no private evaluator/writer or scoring fork.
- Canonical `spatial.folds`: four fixed, label-blind quadrants. All original 8-connected fault components touching each evaluation quadrant are withheld completely from its visible catalogue, including tails in other quadrants. Training excludes the evaluation quadrant and whole held components plus an 80-pixel buffer. No component reaches training.
- The CED surface is entirely label-blind: no trained coefficients, catalogue distances, parent dots or catalogue-derived features. It therefore needs no per-fold label-feature cache invalidation. Only the visible-fault mask is used in placement. Known faults are masked pixel-exactly in scoring.
- Every raw and transformed feature, plus the final continuous surface, has a feature-alone AUROC canary over the union of the disjoint held-out quadrants. Max symmetric **single-feature leakage-canary AUROC** is **0.540922** (AUROC, not DTI; same evaluator context and 60,988 withheld positives). Passing does not prove no leakage; catalogue-zero cells are unlabeled proxies, not verified fault absence.
- Candidate and magnetic-only control use the same geometry-only emission density and deterministic spacing rule. Budgets do not depend on truth counts. Geometry-only fold budgets are 15,166 / 8,462 / 3,494 / 4,878, totaling the preregistered 32,000 dots, as does the final full-footprint artifact. No count was tuned to results.
- Pooled additive TP/FP/FN components precede DTI. The confidence interval is a paired physical **20 km spatial-cluster percentile bootstrap**, not a mean of fold DTIs or a CI from repeated overlapping pixel draws. Its conditional nature is stated in the evidence.
- The old R0 artifact is **not** an independent comparable baseline: it was built using the full catalogue. No compliant historical best with matching splits is recorded. This independently blocks promotion.

## What the previous reported best actually establishes

[Immutable GEMSDOE32 snapshot](https://github.com/buffedlizard55-lab/GEMSDOE32/blob/078f3cea1bc75d15beb81b095ab488a912327a5d/docs/index.html) explicitly says no organizer score exists there. The user-reported benchmark is not ORGANIZER-CONFIRMED here; no live leaderboard maximum is asserted.

[Hash-pinned raster forensics](parent-forensics.json) verifies:

- R0 has 37,654 dots and no positive pixels on the mapped catalogue.
- From the 44,090-dot `anc_d2_8`, the same parent is obtained by deleting 6,436 dots at distance ≤2 pixels, adding none.
- From the 40,199-dot `anc_solo_d2_8`, it deletes 2,545 dots, adding none.
- The previous prose mixed these ancestor counts. Both recipes reproduce the same parent; the deletion counts are different.

Under the shared metric, truth credit is a **maximum**, not a sum. Write `DTI = T / D` with `D = 0.2(T + S − M) + 0.8|G|`. Removing one unit dot loses marginal truth credit `dT` and self-match credit `m`. Its removal improves DTI only when

`0.2 * DTI * (dT + 1 − m) > dT`.

An unmatched redundant dot can therefore cost mass without useful credit. Deleting it may help. Conversely a near-catalogue dot can cover a genuine missing continuation, so removal can hurt. A particular 280 m spacing is **not a universal theoretical optimum**; truth geometry, masking, density and overlap matter. The available evidence does not identify the cause of a reported live improvement, prove R0 near-optimal, or establish that a new file will exceed any stated benchmark.

## Three-pass review record

### Pass 1 — implemented and exercised

Recovered all input pins autonomously; found and pinned the actual shared template; preregistered four hypotheses; executed one CED candidate and its instruments; stopped on a duplicate; produced a real, range-safe research TIFF and a one-TIFF ZIP. Audited GitHub snapshots of all 92 supplied fleet repositories, preserving source commits, page hashes, download links and failures. Rebuilt the portal around the measured run card rather than manually typed readiness claims.

### Pass 2 — bugs, assumptions and edge cases

Corrected the legacy local metric's summed truth credit by making it an adapter to the shared max-credit metric, and removed the two private summed-credit fast paths. Added dense-perfect regression coverage: a perfect dense field is one, not greater than one. Fixed boolean-raster Spearman handling and proved cached exact ranks agree with SciPy; preserved strict thresholds, inclusive 3-pixel distance, soft positive support and dense-reference behavior. Added fail-closed readiness, path containment, artifact SHA/ZIP checks, note limits and full on-disk revalidation. Historical forecasts that used different/wrong instruments are withdrawn from active submission advice.

### Pass 3 — original-request and delivery audit

The active site distinguishes “OK to download” from “OK to submit,” links the real TIFF at the top, includes an executive submission subpage, and never promotes a projection or format PASS. Negative downloadable artifacts are tested rather than prohibited or mislabeled. Official links carry fetched/unfetched status. The complete original brief is embedded in the README as the starting point for future sessions. CI checks the actual published bytes and source policy; The Pages workflow is configured to refresh the fleet feed without running new experiments or spending slots. Exact verification results and PR/deployment outcomes are recorded separately; no remote success is claimed merely because a workflow was created.

## Remaining blockers and limitations

1. **Protocol-unique artifact:** not achieved because final overlap failed. Do not upload the research file.
2. **Assigned lane:** no single method paragraph was present. CED is a provisional research lane, not a claim of fleet assignment.
3. **Full registry:** the pinned comparison index is partial relative to the fleet. The page audit enumerated thousands of rasters, but did not download/evaluate every one. No universal novelty clearance.
4. **Comparable holdout best:** absent; paired-control improvement is unresolved. No evidence of beating the prior best.
5. **Official web access:** only GitHub/npm/Python hosts are reachable. No live organizer form, weekly cap, deadline, leaderboard, rules PDF, USGS/INGENIOUS page or new literature was independently fetched. Free-source leads are not falsely described as obtainable/verified dependencies.
6. **Mirror data permission:** hashes prove identity to existing pins, not organizer authentication or distribution rights. Raw data stay ignored; inherited publicly mirrored data exposure remains flagged.
7. **Target:** faults for geothermal exploration, not directly validated geothermal vents.
8. **Promotion:** a separate selector step with verified current allowance is still required. No slot is selected here.

## Observed local verification (2026-10-24; no new geological experiments)

- Full suite: **226 passed, 1 explicitly skipped** (absent historical release),
  24 upstream Rasterio/Affine pending-deprecation warnings. The current published
  artifact is not the skipped legacy release: it has independent on-disk tests.
- `verify_current_artifact.py --with-data`: all 15 checks PASS and ZIP member/hash
  identity PASS; sample, footprint and catalogue restored and re-read.
- `verify_evidence.py`: shared source hashes, unchanged scientific code, input
  identity, pooled arithmetic, split/buffer receipts, canary coverage and the exact
  final duplicate stop agree with the run card. No science is re-executed.
- Frozen registry restore/check never globs current downloads or self-indexes the
  candidate. The 64-file evidence index is preserved byte-for-byte.
- Rendering itself also revalidates the actual TIFF/ZIP before exposing a download;
  it cannot publish a fake link based only on a stale flag. Synthetic `make demo`
  no longer masks validator failures. CI avoids duplicate feature-push/PR runs.
- Artifact policy: four allowed TIFF/ZIP files; no raw/cache raster newly tracked.
- Synthetic `make demo`: build/write/validation interface CERTIFIED. Not CED,
  not another geological experiment and not a submission promotion.
- Real Chromium: actual advertised TIFF download hash verified; desktop 1440px
  and mobile 390px checked; no document overflow, page errors or HTTP errors;
  no automated WCAG A/AA violations found on the three main pages. Clipboard
  denial correctly falls back to selected text. This does not prove exhaustive
  accessibility or every browser. See [browser receipt](browser-verification.json).

The actual CED computation lasted 45.87 seconds; it was the only geological
candidate. The completed-run lock is regression-tested. The runner's
`--max-seconds` field records a budget, not an internal watchdog: before any
future authorized *new* experiment, add an externally enforced wall-clock limit
and early-failure attempt accounting in the shared orchestration layer. This
session stayed inside the user budget and did not quietly retry after a stop.

Remote CI, Pages configuration and PR merge require observed GitHub results;
creating these workflows is not evidence that they have run successfully.
