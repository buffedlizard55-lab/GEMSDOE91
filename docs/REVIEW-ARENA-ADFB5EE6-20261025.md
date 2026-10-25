# Active-checkout review — Arena lane `adfb5ee6` (2026-10-25 UTC)

## Executive outcome

**No new scientific experiment was run. No new TIFF was generated. No artifact is approved for competition submission.** This is the correct fail-closed result, not a missing deliverable disguised as success.

The active checkout has no assigned single-method lane (`docs/run-card.json`, `lane.assigned: false`), no local `data/` directory, and the preflight has no ready axis. In particular, `sample_submission.tif`, the pinned parent reference and the cached competition feature stack are unavailable locally. Without those inputs, it is impossible to run the required feature-alone leakage canaries, spatial hide-and-recover holdout, surface-before-placement registry test, final-dot registry test, or exact-format validation. A method selected from an older report would not constitute the lane assignment required by the parallel-run protocol.

This checkout already contains many downloadable historical TIFFs under `docs/downloads/`. Their presence is not evidence that this session generated a unique file, that they pass the current lane's uniqueness test, or that any is approved to upload. **Do not submit one based on this review.** No weekly slot was used.

## What was checked, and what the checks establish

| Check | Result | Scope / limitation |
|---|---|---|
| Branch and worktree | `arena/adfb5ee6-gemsdoe91`, initially clean | Active branch confirmed; no branch switch or commit. |
| Local data and cache | `data/` absent | Directly observed. The `local_present` fields in the manifest are historical metadata, not proof that files exist now. |
| `scripts/preflight.py` | **BUILD BLOCKED**; 0 ready axes | Explicitly reported missing `sample_submission` and `parent_r0_nan`; every configured axis also lacks other requirements. This preflight's current axis list is PRUNE/MASS/SNAP/CONCENTRATION/RELIEF/TRACKB; it does not assign a new lane. |
| `scripts/verify_evidence.py` | PASS for its stated bookkeeping scope; `geological_experiments_rerun: 0`, `submission_ready: false` | This validates internal consistency of selected historical evidence, not fresh scientific scores or the live organizer state. |
| Artifact policy | PASS: 55 registered prediction artifacts; no raw raster/archive tracked | Repository policy only; does not certify all historical TIFFs for upload. |
| Tests | `.venv/bin/python -m pytest -q`: **PASS**, with 6 skips and Rasterio `PendingDeprecationWarning`s | Pinned `requirements.txt` installed into ignored `.venv/`; tests are local software tests, not a holdout experiment. |
| Template | Manifest pin declares `vendor/gems57/` byte-identical to pinned source | Hashes are recorded in `registry/template_pin.json`; no evaluator run occurred in this review. |
| Registry uniqueness | **NOT RUN** | No candidate surface/dots and no local full registry. Prior feasibility/duplicate receipts are historical and must not be presented as a fresh comparison. |

Commands: `python scripts/preflight.py`; `.venv/bin/python scripts/verify_evidence.py`; `.venv/bin/python scripts/check_artifact_policy.py`; `.venv/bin/python -m pytest -q`. All completed without source-code or tracked-evidence changes.

## GEMSDOE32 claim: what is and is not supported

The prompt's **0.2778 for `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` is not authenticated here by a DrivenData submission receipt**. In-repo reviews and the GEMSDOE32 page audit describe it as an owner-reported/unscored artifact. Do not label it `ORGANIZER-CONFIRMED` based on a project page or filename. Similarly, the prompt's 0.3195 and 0.4413 statements are not live-rechecked by this review. The official competition problem page is the authority for current scoring and submission rules, not the supplied list of scores.

The official metric description says the competition rewards pixelwise fault-probability predictions using distance-weighted Tversky with alpha 0.2, beta 0.8, and a 300 m triangular support. At 100 m resolution, this makes missing truth weight relatively expensive while predictions still incur false-positive cost. A sparse, spaced point pattern can therefore outperform a dense score surface **if** it keeps predictions close enough to many true faults while removing low-value mass. Known-fault masking/collars can also reduce mass that is ineligible or unhelpful under the task's target definition. This is a plausible explanation for why the repo's reported R0 sparse-dot lineage did better than some denser fleet variants; it is not causal proof of the claimed 0.2778. Establishing causality needs matched ablations on the same fold/evaluator and, for the leaderboard number, an organizer receipt.

The published official description further says the Final Prize Round uses an expanded fault label set after an expert panel reviews team submissions. Automated project gates can eliminate format errors and screen research candidates; they cannot autonomously certify an unmapped geological feature as a fault or replace the organizer's final expert process. This is an important boundary on the request for a fully automatic inspection system.

## Ranked candidate hypotheses — screening proposals, not results

These four are ranked by qualitative expected usefulness for the repository's **fault-recovery proxy**, not by a projected leaderboard score. No number below is a projection or HOLDOUT-DTI. Each uses the competition-provided feature stack in principle, so no new external layer is a prerequisite. The stack is absent in this checkout; exact band tags and support must be rechecked after restore. A grep/source review found no exact cross-wavelet phase-lag implementation, but the repo contains extensive multi-physics fusion, magnetic/gravity operators, strain, radiometrics, DEM transforms and lineament/context methods. Thus “distinct formulation” is supportable; fleet-wide novelty and lack of close analogues are **not proven**.

| Rank | Hypothesis and layers | Physical signature / why a missing fault might be found | Non-fault mimic | Difference from code already present | Expected DTI improvement / implementation cost |
|---:|---|---|---|---|---|
| 1 | **Cross-wavelet phase-lag coherence**, GeoDAWN B02 RTP magnetics + B06 radiometric total count (band names are described in repo evidence; validate actual tags after restore) | At wavelengths of roughly 0.3–1.5 km, estimate localized cross-wavelet coherence and signed phase lag between subsurface magnetic structure and surface radiometric boundaries. A fault-related juxtaposition may generate persistent, spatially displaced or aligned responses across the two physical systems even where either single-layer edge is weak. Score stable cross-scale lag structure, not simply the union of strong edges. | GeoDAWN flight-line/tie-line levelling seams; un-faulted lithologic contacts and soil-moisture/radon variation | Existing lanes use radiometric and magnetic features, coincident edges and cross-layer fusion; the exact *localized cross-wavelet phase-lag statistic* was not found in the repository scan. | **Low–medium, high uncertainty**; medium-high cost (FFT/filter-bank, careful footprint/support handling, canaries). Best first test only after lane authorization. |
| 2 | **Scale-conditioned sign consistency of conductivity–gravity boundaries**, B17 conductivity + B13 isostatic gravity + B15 depth to basin fill | Test whether a shallow conductivity boundary and gravity residual boundary maintain a consistent signed offset/strike over multiple scales at basin margins. A buried fault may juxtapose conductive alteration/fill and basement-density contrast despite little topographic expression. | Saline playa margins, un-faulted basin-fill facies boundaries, clay-rich drainage deposits | Existing basin-fill stripping, conductivity residuals, and multi-physics fusion occur in BHAR/S15 work; this proposal is specifically a fold-safe signed *boundary-offset* statistic, not a new broad fusion model. Novelty is tentative and requires a code-level comparison before preregistration. | **Low–medium**; medium cost; susceptible to close prior-art overlap. |
| 3 | **Magnetic-source depth uncertainty as a confidence penalty**, B02 RTP + B10/B16 derivatives and B13 gravity | Estimate whether candidate magnetic edges are stable under modest upward continuation and derivative-scale changes; retain only edges whose gravity corroboration is consistent with a deeper source. Could demote shallow volcanic noise while preserving covered basement faults. | Young volcanic flows, remanent magnetization, survey seams, and unrelated shallow intrusions | Continuation/depth and magnetic destruction features already exist; the novelty would be a calibrated stability/uncertainty score rather than another depth estimate. Full prior-code audit needed. | **Low–medium**; medium cost; likely lower incremental benefit given existing continuation lanes. |
| 4 | **Acquisition-domain nuisance model for GeoDAWN area seams**, B02/B06 survey rasters plus footprint and published survey block geometry | Estimate fixed-orientation stripe spectra and block-transition discontinuities, then remove only the nuisance component while preserving cross-sensor, non-flightline geological structures. This may improve off-catalogue precision by suppressing artificial linear edges, rather than adding another fault detector. | The flightline/tie-line artifacts themselves are the named mimic; genuine faults parallel to flight direction are the principal risk. | Repo reports seam controls and source cleaning, but this proposal asks for a spatially explicit flight-geometry nuisance fit with held-out-area diagnostics; exact implementation status is uncertain. | **Potentially useful as a precision safeguard**, not a new positive detector; medium cost, high risk of removing true parallel structures. |

**Top candidate: rank 1.** It is scientifically motivated, uses existing competition layers, and has a falsifiable signal plus named mimics. It is **not validated**. No holdout value, CI, or canary result can be responsibly reported because the feature cache/data are absent and the lane is unassigned. It must not be run or promoted until an authorized lane is supplied, the pinned stack is restored, its actual band metadata are checked, and the complete frozen registry is available. If the feature-alone AUC exceeds 0.90, treat that as leakage until explained; if the surface or final dots cross either duplicate threshold, stop and record the duplicate.

No proposal here requires new external data, so none is being advertised as viable on the basis of an unchecked download. The official GeoDAWN release is a possible provenance check for source/band context, but the competition-provided stack should remain the model input; the USGS page is not evidence for any candidate's predictive performance.

## Three-pass review

### Pass 1 — implementation and requirements inventory

Read the current README standing brief, canonical run card, pinned template manifest, data manifest, preflight, experiment/evaluation scripts, and the latest hypothesis and review documents. Confirmed that the README already preserves the user's long-form project brief and core values; this review adds a concise current-session link rather than duplicating another copy of the huge prompt. Identified four falsifiable research candidates above. Did not build a candidate because no lane was assigned and required data are absent.

### Pass 2 — bugs, omissions and assumptions

- Found stale manifest metadata (`local_present: true`) contradicted by the real filesystem and preflight. Treat runtime file/hash verification as authoritative; never gate on that manifest boolean alone.
- Found historical README summaries reference other branches and prior-session statuses. Added a branch-specific notice so a reader does not mistake old artifacts for this session's output.
- Checked that reported scores are not silently elevated to organizer receipts; 0.2778 remains an unauthenticated project/user claim in this review.
- Checked the competition's official description for the metric and final-review process. A fully automated local validator can validate raster structure/range and reproducible holdout evidence, not geological truth or organizer acceptance.
- No source patch to the evaluator/writer was warranted by these checks. The template hash manifest passed static evidence review; no new data was available to re-exercise it end-to-end.

### Pass 3 — final re-check against the request

The repository is test-green and retains the complete prompt in README. Submission download links are already exposed near the top of the existing README/site for historical files, each with research/submission status. This review did **not** add a new TIFF because doing so from an old file, synthetic data, or an unvalidated surface would breach the explicit non-copy, holdout, lane, and registry rules. There is no fresh candidate score to compare against a current best, and no candidate is marked `OK TO SUBMIT`.

## Next actions and blockers

1. Keep this branch's method lane unassigned; do not infer one from the older S16-PGRD/S16-PC91 reports. Obtain the intended single-method paragraph through the authorized coordination process.
2. Restore the manifest-pinned inputs/cache through the documented source route, verify each SHA-256, and correct or clearly annotate stale `local_present` metadata. Do not copy another submission into a new filename.
3. Recompute complete registry inventory/feasibility with the actual authorized set. Existing reports describe a severe 3-px overlap-capacity conflict; recompute it before a candidate build and never weaken the thresholds to force a pass.
4. For an authorized candidate, preregister once; perform per-feature canaries, surface uniqueness before placement, shared whole-segment hide-and-recover holdout with visible-fault-only pixel-exact masking, pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel), and final-dot uniqueness. Stop at three experiments or two hours.
5. Only if a candidate beats the comparable holdout best with uncertainty and passes all gates should the independent selector decide whether to use a weekly slot. A format-valid TIFF is not equivalent to a scientifically promoted or organizer-confirmed submission.

## Run card (this review)

```json
{
  "hypothesis": "No experiment: top screening candidate is localized cross-wavelet phase-lag coherence between GeoDAWN magnetic B02 and radiometric B06; lane not assigned.",
  "mechanism": "Not implemented or evaluated. Proposed scale-conditioned cross-wavelet coherence and phase lag; no candidate raster emitted.",
  "named_non_fault_process": "GeoDAWN flight-line/tie-line levelling seams and un-faulted lithologic contacts.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_status": "NOT RUN; data/cache absent and lane unassigned.",
  "registry_correlation_overlap": "NOT RUN; no candidate surface/dots and no local full registry.",
  "raster_sha256": null,
  "validator_output": "NO NEW TIFF; no new raster to validate for NaN, [0,1], CRS, shape, or transform.",
  "submission_name": null,
  "submission_note": "No new artifact. Do not submit a historical TIFF based on this review.",
  "verdict": "negative"
}
```

## Official sources for manual review

- [DrivenData DOE GEMS problem description, metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official metric, 300 m support, alpha/beta weights, CRS/resolution/float32 range and expert-panel Final Prize Round process. Page content was obtained from search indexing for this review; the live page was not fetched by a direct browser session.
- [USGS GeoDAWN data release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) and [USGS ScienceBase record](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7) — official context for airborne magnetic/radiometric acquisition; the ScienceBase record gives DOI `10.5066/P93LGLVQ`. These sources support provenance/context only, not candidate performance.
- [Official competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) — login-gated competition inputs; no authentication was attempted or requested.
- [Pinned reference implementation](https://github.com/drivendataorg/gems-prize-reference-solution) — official organizer/reference project; does not by itself certify any locally implemented holdout as the organizer scorer.
