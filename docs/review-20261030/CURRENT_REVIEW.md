# Current repository review — 2026-10-30

**Branch:** `arena/828b6720-gemsdoe91` · **base:** `8c52ba3` (`main` at session start)

**Decision:** **No new TIFF generated. `OK TO DOWNLOAD: NO new candidate. OK TO SUBMIT: NO`.** Existing historical research artifacts remain historical/research-only; none is endorsed or selected by this review.

**Experiments:** 0 of the allowed 3 · **elapsed experiment time:** 0 minutes of the 120-minute cap · **weekly submission slots used:** 0.

**Current holdout result / candidate score estimate / organizer-confirmed score:** none.

Machine-readable record: [negative run card](run-card.json). Related reports: [preflight](experiment-preflight.json), [input availability](data-availability.json), [nine-site audit snapshot](../s27-osdr/nine-site-audit.json), and [ranked hypotheses](HYPOTHESES.md). Open the [executive summary and site table](executive-summary.html), [current limitations](../../LIMITATIONS_AND_NEXT_STEPS.md), and [irregularities](../../IRREGULARITIES.md).

## Executive decision

The prompt's highest claim **within the nine requested sites** is GEMSDOE32's reported `0.2778` for `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`. This value is **USER-REPORTED**, not copied from an organizer submission-page receipt. All nine entries in the latest pinned peer audit are also USER-REPORTED and have `organizer_confirmed_score: null`. The byte audit was explicitly incomplete with respect to the organizer's full registry. “Highest among these nine” is therefore a ranking of supplied claims, not a confirmed leaderboard fact.

The last local peer-only audit records each of the nine historical leader rasters with more than 70% of its dots within 3 pixels of at least one other raster in that peer set. That means **none is unique against the other eight under the stated rule**. It does **not** establish the complete-registry result. A new candidate's surface correlation and final-dot overlap against the full registry are both **NOT RUN** because no candidate exists and the complete organizer registry is unavailable.

The top-ranked proposed test is an SGMC map-unit-conditioned magnetic/gravity residual-break detector; it was **not implemented or validated**. `registry/experiment_plan.json` has `lane: null`, and the verifier/preflight does not authorize a substitute lane. `scripts/experiment_preflight.py` returned **BLOCKED**. The verification-only `scripts/restore_data.py --check` found **all 15 pinned inputs missing**, including the official sample raster, known-fault catalogue, training features, historical parent rasters, external control data, and lidar/radiometric layers. No data were restored and no experiment was launched. The stale `local_present` flags in `registry/data_manifest.json` are not evidence of current files.

## Nine-site snapshot: best historical claim, evidence, and peer uniqueness

The HTML table is generated from `docs/s27-osdr/nine-site-audit.json`, the pinned audit checked on 2026-10-29. It lists the last byte-audited best-claimed file for each requested site and immutable source links. The owner-maintained pages were rechecked on 2026-10-30; the reviewed pages do not authorize a new submission. Historical filenames are links for inspection, **not recommended downloads**. Current candidate download: **none**. Current new-file score forecast: **not estimable** for every site.

All peer-overlap percentages are the audit's directed measure: the fraction of that site's dots within 3 pixels of its closest peer's dots. It is a pairwise peer-set diagnostic, not a score and not a full-registry clearance.

| Site | Best historical file claim | Supplied score evidence | Closest peer / 3-px dot overlap | Unique vs other eight? | New score estimate / download |
|---|---|---|---:|---|---|
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` | `0.2778` — USER-REPORTED; no receipt | GEMSDOE24 / 100.00% | **NO** | Not estimable; no current candidate |
| GEMSDOE36 | `gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif` | `0.2750` — USER-REPORTED; no receipt | GEMSDOE27 / 97.58% | **NO** | Not estimable; no current candidate |
| GEMSDOE28 | `gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif` | `0.2710` — USER-REPORTED; no receipt | GEMSDOE24 / 100.00% | **NO** | Not estimable; no current candidate |
| GEMSDOE31 | `gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif` | `0.2708` — USER-REPORTED; no receipt | GEMSDOE24 / 100.00% | **NO** | Not estimable; no current candidate |
| GEMSDOE33 | `GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif` | `0.2632` — USER-REPORTED; no receipt | GEMSDOE27 / 99.71% | **NO** | Not estimable; no current candidate |
| GEMSDOE25 | `gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif` | `0.2600` — USER-REPORTED; no receipt | GEMSDOE24 / 100.00% | **NO** | Not estimable; no current candidate |
| GEMSDOE30 | `gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif` | `0.2600` — USER-REPORTED; no receipt | GEMSDOE24 / 100.00% | **NO** | Not estimable; no current candidate |
| GEMSDOE24 | `gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif` | `0.2477` — USER-REPORTED; no receipt | GEMSDOE25 / 100.00% | **NO** | Not estimable; no current candidate |
| GEMSDOE27 | `gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif` | `0.2449` — USER-REPORTED; no receipt | GEMSDOE24 / 98.02% | **NO** | Not estimable; no current candidate |

**GEMSDOE28 claim distinction:** the table's `0.2710` claim is attached to the separate H36-1 file shown in that row. The earlier R0 lineage report's `0.2708` claim is for the H27-4 file, also recorded as pixel-identical across GEMSDOE28 and GEMSDOE31. These are different named files, not interchangeable score labels; both values are USER-REPORTED and neither has an organizer receipt. This review preserves both rather than choosing one as the other's correction.

**Audit boundary:** these values are taken from the 2026-10-29 pinned owner/source audit. No peer raster was re-downloaded or byte-rechecked from the missing competition-data directory during this review. The source page and immutable file link are shown per row. The complete organizer registry remains unavailable; no statement here labels a site file “globally unique.” `GEMSDOE92`'s separate `0.2784` claim is outside the nine-site scope and is also USER-REPORTED; it is not used to change the requested table.

## Why GEMSDOE32's `0.2778` claim is the highest of the nine

The explanation below is an **evidence-labeled interpretation**, not a reproduced score. The claim has no organizer submission-page receipt in the repository, and the GEMSDOE32 TIFF is absent from this checkout. `docs/R0_ANALYSIS_S22.md` and `docs/s22-xb/r0-decomposition.json` preserve an earlier SHA-pinned byte-lineage analysis; this review read those records but could not re-hash the missing source TIFFs.

1. **It appears to be the best-pruned member of a shared raster family, rather than an independent detector.** The prior byte audit records D2.8 (`GEMSDOE25`, 44,090 dots) as a subset of H19-5; H27-4 (`GEMSDOE28/31`, 40,199 dots) as D2.8 minus 3,891 dots within 1 pixel of the catalogue; and R0 (`GEMSDOE32`, 37,654 dots) as H27-4 minus another 2,545 dots 1–2 pixels from the catalogue. The resulting historical claims rise from `0.2600` to `0.2708` to `0.2778` (all **USER-REPORTED**). Thus the reported R0 support contains no pixel outside the earlier D2.8 support; its reported advantage is consistent with pruning.
2. **Pruning can help this metric if the removed pixels carry little hidden-new-fault credit.** The official distance-weighted Tversky uses `alpha = 0.2` for false positives, `beta = 0.8` for false negatives, and a 300 m triangular kernel. If predictions removed near the known-fault catalogue are not near a hidden new fault, the false-positive term can shrink while much of the true positive mass remains. That is a plausible mechanism for a higher public score, not proof that each removed dot was false or that the file finds new geology.
3. **The same lineage audit is consistent with diminishing value from additions.** It records GEMSDOE36 as R0 plus 1,200 dots, with a reported value of `0.2750`; this is again a user report, not a receipt. The same report notes the H27-4 raster was pixel-identical across GEMSDOE28 and GEMSDOE31, both with a `0.2708` claim. These replications are suggestive of deterministic scoring and shared lineage, but they do not authenticate the claims.
4. **The project holdout answers a different question.** Whole-segment hide-and-recover uses the known catalogue as the proxy truth. A map deliberately stripped close to known faults can perform poorly on that proxy even if its author-reported score against newly identified faults is higher. A holdout result cannot be inferred from the reported public score, and neither is a guarantee of private-phase or Phase 2 performance.

**Can `0.2778` be beaten?** The available evidence does not support a numerical forecast. The official public leaderboard page snapshot fetched on 2026-10-30 showed a rank-one public observation of `0.4544`; that is a dated **PUBLIC-LEADERBOARD SNAPSHOT**, not a receipt tied to any of these files and not the final private/updated-label result. It is possible for a new, compliant method to score above `0.2778`; this checkout has not demonstrated that it can. The sensible result of this review is “not estimable,” not a projected DTI.

## Sources, task framing, and eligibility

- The [official DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) defines the fault-prediction task, distance-weighted Tversky metric, and GeoTIFF requirements. The target is **fault prediction** supporting geothermal and critical-mineral studies; it is not direct geothermal-vent detection.
- The [September 2026 NLR / DOE Official Rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) distinguish the public leaderboard from private testing and the later expert-revised Phase 2 evaluation. They state that submissions are chosen for both phases, allow up to three submissions per week under the competition platform rules, and require a narrative disclosure of any generative-AI use and its extent. Generative AI is allowed; the entrant remains responsible for accuracy and authorship representations.
- The rules do not make an Arena agent itself an eligible competitor. Section 1.3 lists eligible individuals, teams, and U.S.-based entities and their conditions; an authorized representative must certify eligibility. No person's or entity's eligibility can be determined from this repository. This agent did not register, submit, or certify anything.
- The [official public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) is a changeable public observation only. It cannot prove a score for a raster without a matching organizer submission-page receipt.
- Official external-data checks are documented in [HYPOTHESES.md](HYPOTHESES.md): the USGS SGMC GeMS GIS download listing is public, ComCat returned regional events for a broad bbox query, Landsat surface-temperature products are described as generally available, and USGS 3DEP products are free. None of the associated study-area data bytes were ingested or validated here.

## Three-pass review record

### Pass 1 — Build and source check

- Re-read the standing requirements and checked `registry/experiment_plan.json`: `lane: null`, experiment counter zero. No method was self-assigned.
- Ran `.venv/bin/python scripts/experiment_preflight.py --output docs/review-20261030/experiment-preflight.json`: **BLOCKED** on missing lane and absent sample-submission witness. It reports zero experiments, no candidate, and `ok_to_submit: false`.
- Ran `.venv/bin/python scripts/restore_data.py --check`: verification-only exit 1; **15/15** pinned inputs are missing. See [data-availability.json](data-availability.json). This is not a restore, and no data were downloaded.
- Fetched the official competition problem description, rules PDF, live public leaderboard, USGS SGMC release/DOI page, Landsat ST product page, USGS 3DEP products page, and a regional USGS ComCat API query. Source-page reachability is not a substitute for data bytes, exact footprint coverage, or organizer permission.
- Audited `scripts/`, `src/`, and historical hypothesis records for overlap. The four ranked proposals disclose adjacent implemented and previously written approaches; they are not represented as universally novel.

### Pass 2 — Independent challenge and corrections

- Kept the nine-site values explicitly **USER-REPORTED** and the rank-one public leaderboard value explicitly a dated public snapshot; no number was relabeled as an organizer receipt or a holdout score.
- Limited the uniqueness statement to the prior nine-site directed dot-overlap audit. No new candidate surface or final dots exist, so both required registry phases remain unmeasured; the organizer-complete registry is unavailable.
- Revisited the GEMSDOE32 explanation against the prior byte-lineage report and official metric. The pruning mechanism is plausible but relies on assumptions about hidden-fault credit. The previous analysis is not a new experiment, score reproduction, or proof of why the organizer assigned a score.
- Corrected the interpretation of “human-only”: the official rules enumerate eligible people and entities, require an authorized representative's certification, and allow generative AI with disclosure. This agent is not an entrant and cannot certify an account's eligibility.
- Did not reuse the 2026-10-29 lattice capacity figure as a current result: it depended on an unauthenticated sample mirror. The 2026-10-30 preflight cannot inspect the sample at all.

### Pass 3 — Re-check against the request

- Nine rows, best claimed file, evidence-labeled score, peer overlap/uniqueness, unavailable new-file estimate, and no-current-download status are on the linked executive page.
- Four ranked hypotheses identify named layers, physical signatures, missed-fault rationale, repository implementation comparison, a named non-fault mimic, qualitative expected benefit/cost, and official-source availability limits.
- The top proposal was **not holdout-validated** because the lane and inputs are missing. This is a blocker, not a pass; the run card keeps every unmeasured holdout, CI, registry comparison, raster hash, and validator field `null`.
- No TIFF was copied, renamed, written, or approved. No live submission decision or slot selection was made. The next viable step is to obtain the missing assigned method paragraph and authentic data access; until then the correct verdict remains negative.

## Remaining limitations / next steps

1. Resolve the assigned method-lane paragraph and its source; do not infer it from a previous branch or this proposal list.
2. Restore and verify the 15 pinned inputs through an authorized route, resolve stale manifest availability flags, and independently authenticate the sample and data-use rights.
3. Before any experiment, run the shared pre-placement rank-correlation screen (`|rho| > 0.90` is a duplicate stop). After placement, check final dots against the complete registry and stop if more than 70% are within 3 pixels of any registry raster. Check both phases and log a negative if either fails.
4. Only then, and only inside the assigned lane, test the top hypothesis with the shared cached stack where applicable, `evaluate_holdout.py`, whole-segment buffered hide/recover, exact visible-fault masks, feature-alone leakage canaries, pooled DTI (`alpha=.2`, `beta=.8`, 300 m triangular kernel), withheld count, evaluator version, and a 95% CI. Reuse shared tools; do not fork them.
5. Validate any future candidate automatically for in-footprint NaNs, `[0,1]` range, CRS/shape/transform, hashes, and allowed output format. A passing format check is not science, uniqueness, selection, or submission approval.
6. Obtain a separate selector decision within the live weekly allowance. Preserve a submission-page receipt binding the exact raster hash to any organizer score. Disclose generative-AI use in the required narrative if a submission is ever made.

**Maximize P(Win) · Own the Outcome.** A negative and bounded review is preferable to an unsupported score estimate or an unauthorized upload.
