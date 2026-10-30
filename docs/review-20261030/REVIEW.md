# Three-pass repository review — 2026-10-30

**Branch:** `arena/83350cee-gemsdoe91`<br>
**Verdict:** **BLOCKED / NO CANDIDATE / OK TO SUBMIT: NO.** No method lane was authorized, the 15 pinned manifest inputs are absent, and `data/official/sample_submission.tif` is absent. No experiment was launched, no new GeoTIFF was generated, and no score was measured. There is **no defensible leaderboard-score estimate** and no organizer receipt.

**Deliverables:** [Executive summary, nine-site table and submission guide](executive-summary.html) · [untested hypotheses](HYPOTHESES.md) · [negative run card](run-card.json) · [commit-pinned nine-site evidence snapshot](nine-site-snapshot.json) · [official source checks](sources.json).

This is the current review for this checkout. Historical TIFFs linked in the nine-site table are repository-hosted prior research artifacts, provided only for provenance and inspection. Those links are **not** a new candidate, do not imply competition-slot approval, and must not be submitted as this review's work.

## Executive decision

| Question | Finding |
|---|---|
| New unique TIFF created? | **No.** No candidate path, hash, name, or note exists. |
| OK to download a new candidate? | **No candidate exists.** The table's pinned historical files are available as research references only. |
| OK to submit? | **No.** No authorized lane, no verified input stack/sample, no current holdout, no full-registry clearance, no selector decision, and no receipt. |
| HOLDOUT-DTI measured by this review? | **None.** `holdout_dti.value`, evaluator, withheld-positive count, and CI are null in the run card. |
| ORGANIZER-CONFIRMED score? | **None.** No submission receipt was available or created. |
| Leaderboard score estimate? | **None.** No projection or unverified public claim is treated as an estimate. |
| Experiments / slots used? | **0 / 0.** |

### Blocking evidence

1. `registry/experiment_plan.json` explicitly has `lane: null`; its note says no assignment paragraph/source was supplied. An idea in this review, a prior branch's lane, or a historical result is not an assignment.
2. `scripts/restore_data.py --check` reported **15/15** pinned inputs missing. The experiment preflight also failed to find `data/official/sample_submission.tif`. It returned `BLOCKED`, zero experiments, no candidate, and `ok_to_submit: false`.
3. The README and Pages source previously presented a different branch's 2026-10-29 candidate/status as current. This review installs a durable 2026-10-30 status renderer and preserves the older material as history; the `docs/current-run.json` legacy artifact pointer is explicitly distinguished from the active no-candidate review.
4. The stored 2026-10-29 capacity calculation relies on a sample/reference mirror whose authenticity and sample semantics were not established. Its overlap lower bound is **conditional historical evidence**, not a verified impossibility proof. This review does not use it to authorize, constrain, or guide placement.
5. Prior repository records (`IR-S26-05`, `IR-91-09`) flag the rights/terms status of public GitHub mirrors of competition data as unresolved. This review did not restore from or use those mirrors and makes no rights determination. Any future data restoration must use an authorized source.

## Nine requested sites: files, reported values, and peer uniqueness

The [HTML executive table](executive-summary.html#nine-sites) gives all nine rows, including a direct commit-pinned file link, the repository blob link, SHA-256, byte count, positive-pixel count, reported-value evidence class, closest peer, measured maximum 3-px overlap, uniqueness result, and an explicit organizer-receipt column. The compact snapshot is in [`nine-site-snapshot.json`](nine-site-snapshot.json).

**Evidence warning:** the values below are preserved as `USER-REPORTED_PUBLIC_DTI` in the dated 2026-10-29 repository audit. They are **not** verified scores and are not performance estimates. The audit recorded no organizer-confirmed score/receipt for any site. On 2026-10-30, each TIFF was retrieved through GitHub's API at the recorded commit and path, then its byte count and SHA-256 were independently checked against the snapshot. This verifies file identity only; owner score pages and organizer receipts were not refreshed. The uniqueness column is a **peer-only** 3-px comparison among the nine listed sites—not a complete-registry pass.

| Site | Historical file | Reported value (unverified claim; not a verified score) | Closest peer | Max peer overlap within 3 px | Unique among these nine at 70%? | Download / submission status | Organizer receipt? |
|---|---|---:|---|---:|---|---|
| GEMSDOE24 | [`gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24/6284a525a9425ed442f8e3fc0e04dfbd6fce537d/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2477` | GEMSDOE25 | 100.00% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE25 | [`gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE25/b55a246a155c1d65430382aa3edaa51749d44360/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2600` | GEMSDOE24 | 100.00% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE27 | [`gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE27/494ec17625bf8fe9e19510ec3f39912451c4f7f7/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2449` | GEMSDOE24 | 98.0188% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE28 | [`gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE28/a1c0e18f4a4f7394ce549f1d61f2a229d5cfabfa/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2710` | GEMSDOE24 | 100.00% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE30 | [`gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE30/d855914332b29c0b36974d5462ba9fd5dca21136/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2600` | GEMSDOE24 | 100.00% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE31 | [`gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE31/adf37ffd9d6a78e5b90a68bfe2033509124517d1/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2708` | GEMSDOE24 | 100.00% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE32 | [`gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE32/0ffda7162e76291df34359345488ff08b4115aac/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2778` | GEMSDOE24 | 100.00% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE33 | [`GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE33/1a7f53ca35648900998a061d7e864ab41ee1334d/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2632` | GEMSDOE27 | 99.7086% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |
| GEMSDOE36 | [`gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif`](https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE36/e280188adbbe762e6b7ac6f3b8e105e8e7915026/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | `USER-REPORTED_PUBLIC_DTI: 0.2750` | GEMSDOE27 | 97.5781% | **No** | **OK TO DOWNLOAD: YES (research/inspection only); OK TO SUBMIT: NO** | None recorded |

The reported value column intentionally does **not** label these as `HOLDOUT-DTI` or `ORGANIZER-CONFIRMED`: neither evidence class is supported by the frozen nine-site audit. This is not a current leaderboard table. There is no defensible score estimate for any of these files in this review.

## Why GEMSDOE32's `0.2778` was reported highest in this nine-site family

The byte-lineage analysis in [`docs/R0_ANALYSIS_S22.md`](../R0_ANALYSIS_S22.md) gives a plausible **metric-geometric** explanation, not proof of causality and not an organizer result:

- Its pinned file is a member of one highly related H19-derived family. The byte audit reports that GEMSDOE32/R0 adds no new pixel relative to the earlier D2.8 support; relative to D2.8, it deletes 6,436 pixels, including a 2,545-pixel final pruning step from the H27-4 support. GEMSDOE28 and GEMSDOE31 also share identical positive support in that lineage analysis.
- The organizer's published DTI penalizes false positives with `alpha=0.2`, false negatives with `beta=0.8`, and linearly weights distance to truth within a 300 m radius. If a deletion removes mostly unmatched clutter while retaining detections that overlap the hidden new-fault truth, the false-positive term can shrink while true-positive credit is retained. That is a plausible reason a more sparsely pruned member could receive the highest reported value in the family.
- The repository audit's peer comparison finds complete within-3-px support overlap with GEMSDOE24 for GEMSDOE32; this is evidence of family similarity, not independent geological discovery. The bytes do not identify which removed dots were scored false positives, and the hidden labels/organizer receipt are unavailable.
- The local source register records that the GEMSDOE32 owner page, when checked on 2026-10-25, said no organizer score existed for those artifacts and described a separate modeled value as a projection. That is a dated owner-page observation, not a 2026-10-30 re-fetch. The present review therefore keeps `0.2778` as an unverified reported claim.

**Bottom line:** the pruning explanation is consistent with the published asymmetric metric and the historical raster lineage; it does not establish that the reported value is authentic, that pruning caused it, or that a new candidate would reproduce or exceed it. No projection is offered as a score. The user-supplied comparison values `0.3195` and `0.4413` were not reverified here and are not used for estimates.

## Sources and new geological hypotheses

Official problem, data, and research sources were checked on 2026-10-30. See [`sources.json`](sources.json) for the claim-by-claim provenance and limitations. Key references:

- [DrivenData official problem description, metric, and file requirements](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — DOI `10.5066/P93LGLVQ`; its page marks the release CC0.
- [USGS 2026 GeMS/SGMC release](https://www.usgs.gov/data/geologic-map-schema-gems-version-state-geologic-map-compilation-sgmc-geodatabase-conterminous) — DOI `10.5066/P1A3DQZK`; CC0, but map-unit scales vary and units are unreconciled across state boundaries.
- [USGS 3DEP products and services](https://www.usgs.gov/3d-elevation-program/about-3dep-products-services) — USGS says its lidar/DEM products are free of charge and without use restrictions; exact footprint coverage remains unchecked.
- [USGS-recorded Great Basin structural-discontinuity study](https://www.usgs.gov/publications/structural-discontinuities-and-their-control-hydrothermal-systems-great-basin-usa) — process evidence for fault interactions, stepovers, and terminations, not proof for a particular pixel.
- [USGS Scientific Investigations Report 2026-5073 on slip and dilation tendency](https://pubs.usgs.gov/publication/sir20265073) — DOI `10.3133/sir20265073`; related data DOI `10.5066/P9YL58W6`. Its attributes are calculated on Quaternary fault segments, creating a serious catalogue-leakage risk if used directly.

Three untested, ranked hypotheses and their null controls are in [`HYPOTHESES.md`](HYPOTHESES.md). They center on map-unit-conditioned potential-field edge persistence, stress-compatible structural discontinuities with independent geophysical support, and LiDAR scarp persistence. All are proposals, not an assigned lane. No source dataset was downloaded and no experiment was run.

## Submission guide — current status and future gates

### Today: do not submit

There is no new TIFF to download or submit. The historic peer files above are not GEMSDOE91 candidates. Do not copy, rename, or upload them. The existing GEMSDOE91 research artifacts elsewhere in `docs/downloads/` also have historical negative verdicts; a format check or one peer-only uniqueness comparison is not submission clearance.

### Only after the blockers are resolved

1. Obtain an authenticated method-lane assignment containing exactly one method paragraph and its source. Do not self-assign from `HYPOTHESES.md` or a historical branch.
2. Restore the pinned official stack and sample through the authorized data path. Verify every manifest hash, CRS, transform, nodata/footprint semantics, and provenance. Reconcile the known mismatch between an unauthenticated sample mirror and the organizer's published sample description before using it.
3. Preregister the assigned hypothesis, named non-fault mimic, controls, and a maximum of three experiments/two hours. Reuse the shared cached feature stack, evaluator, and writer. Do not rebuild the metric or alter the method lane.
4. Preserve whole-segment buffered hide-and-recover and pooled DTI (`alpha=0.2`, `beta=0.8`, 300 m support). Run feature-alone leakage canaries before the holdout. Report any `HOLDOUT-DTI` with the exact evaluator version, withheld-positive count, and 95% CI.
5. Before placement, compare candidate surfaces against the registry and stop if **any** rank correlation exceeds `0.90`. After placement, compare final dots against the complete available registry and stop if **more than 70%** of candidate dots are within 3 px of any raster. Do not omit or exempt a witness to obtain a pass.
6. Run automated GeoTIFF validators for single-band `float32`, the exact EPSG:32611 grid/transform, `[0,1]` values, required outside-bound null/NaN semantics, and no invalid cells. Format-valid does not mean scientifically useful or unique.
7. A separate selector must approve promotion to a competition slot. Never upload automatically. Record a leaderboard result as `ORGANIZER-CONFIRMED` only when copied from an organizer submission receipt, and retain that receipt.

## Three-pass record

### Pass 1 — repository and evidence review

Confirmed the active branch, inspected the experiment plan, registry manifest, preflight, render chain, current front door, run cards, previous review, nine-site audit, and R0 byte-lineage analysis. The lane is unassigned; all pinned inputs and the official sample are absent; no new candidate can be built safely. The previous checkout's timestamp-only `registry/preflight.json` edit was reverted.

### Pass 2 — independent challenge / bug and assumption review

Found that the README's top banner and Pages renderer advertised a different checkout and stale date; the public current-run artifact pointer and older general run card were also easy to mistake for the active review. Corrected this by adding an explicit active-review card and idempotent current-status rendering while retaining historical artifact pointers with clear scope. Also rejected the 2026-10-29 conditional capacity lower bound as proof, because its sample/reference mirror was not authenticated. Verified all nine site TIFF bytes through GitHub's API at the recorded commit/path and recomputed matching SHA-256 values. Kept the audit date and owner-reported score evidence class; no owner page or receipt was refreshed.

### Pass 3 — requirement-by-requirement verification

Regenerated the portal after the final active-review hook and explicit historical-download policy changes; `.venv/bin/python scripts/render_portal.py` completed successfully. The review renderer's idempotence and the new review/guide local links are covered by regression tests. The full suite passed: **946 passed, 11 skipped** (all skips require unavailable pinned inputs or history), with 152 Rasterio deprecation warnings. `git diff --check` passed after whitespace cleanup. The final card, branch, snapshot, and no-candidate state were rechecked; no experiment, TIFF, HOLDOUT-DTI, organizer receipt, upload, or leaderboard estimate was introduced. See the active record in [`PASS_LOG.md`](../../PASS_LOG.md).

## Remaining work / limitations

- **Authorization:** obtain the single-lane method paragraph and source. This is not something the agent may invent.
- **Data:** restore and verify the 15 pinned manifest inputs, particularly the missing sample, existing-fault catalogue, training features, labels, and DEM metadata/links. The authenticated source is outside this environment's available outbound hosts.
- **Sample semantics:** verify the competition's actual sample and bounds with organizer-controlled bytes; do not assume a historical mirror is authentic.
- **Candidate validation:** no new experiment, TIFF, HOLDOUT-DTI, full-registry result, selector clearance, or organizer receipt exists.
- **External geology layers:** the new official sources are documented, but GeMS/SGMC fields/coverage, 3DEP tile coverage, and the SIR data contents were not downloaded or matched to the study footprint. Licensing claims are source-page metadata, not per-file license manifests.
- **Score evidence:** the site values are unverified owner-reported historical claims; a dated public leaderboard snapshot is not a receipt for any file. No estimate is offered.

**Maximize P(Win) · Own the Outcome.** Protect the slot from unsupported or duplicate files; preserve evidence and report the block honestly.
