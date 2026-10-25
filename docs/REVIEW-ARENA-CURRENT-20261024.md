# Current checkout review — 2026-10-24

## Decision

**No new TIFF was generated; no submission is approved.** Existing TIFFs are historical artifacts, not a newly validated submission for this review. The assigned method paragraph/lane is not specified in the request, current pinned competition inputs are absent, and available local test dependencies are not installed. Generating or selecting another candidate would violate the parallel-run rule and could not be safely evaluated against the required full registry and holdout.

The user's stated benchmark values (`0.2778`, `0.3195`, `0.4413`) are user-provided claims, not organizer receipts verified in this checkout. Do not report them as ORGANIZER-CONFIRMED or as comparable scores. The current machine has no DrivenData login, and no live organizer submission receipt is available.

## Inspected facts

- Branch: `arena/2c4baeee-gemsdoe91`; initial worktree clean; HEAD is the repository's supplied baseline.
- `scripts/evaluate_holdout.py` and `scripts/submission_writer.py` exist, as do extensive S13 and prior-lane artifacts. Their existence does not establish that those candidate runs are current, assigned to this lane, or valid under this request's stricter holdout requirements.
- `scripts/restore_data.py --check` reports all 15 pinned raster/data inputs missing, including sample submission, catalogue and feature stack. No data restoration was attempted.
- `python -m pytest -q` could not run: `pytest` is not installed. `verify_current_artifact.py` could not run: `numpy` is not installed. Both are environment/dependency failures; they are not test failures or passes.
- There is a material current-state inconsistency: `docs/run-card.json` is CED91 and says the lane is unassigned / provisional research-only, while the top-level `README.md` and `docs/index.html` advertise S13-PTHA as current. Their historical results, artifact links and readiness statements must not be treated as the same current run. Portal source was not regenerated or certified in this review.
- Existing prior review `docs/REVIEW-CED91.md` documents a negative research outcome and overlap duplicate against the broad-coverage lattice; it explicitly says no approval to submit. This review does not reinterpret that gate or bypass the selector.

## Why GEMSDOE32's reported 0.2778 cannot establish a causal explanation

A score by itself does not reveal which pixels were credited, how false-positive mass was penalized, which truth split was used, or whether the displayed value came from an organizer receipt or a local projection. Metric theory permits a sparse prediction to improve precision/recall tradeoffs when removed dots contributed little kernel-weighted true-positive credit; pruning can also remove valuable continuation coverage. These are conditional explanations, not a finding about that raster. The repository's earlier snapshot analysis records an explicit lack of organizer score. Accordingly, neither the causal story nor any claim of exceeding that number is verified here.

## Candidate hypotheses (ranked proposals, not executed)

All use layers already present in the cached feature-stack design; actual use is blocked until official band metadata and input availability are verified. Ranking means qualitative expected information value relative to existing methods, not predicted DTI.

| Rank | Layers / physical signature | Off-catalogue rationale | Distinction from implemented local approaches | Non-fault mimic | Cost |
|---|---|---|---|---|---|
| 1 | Conductivity (`cond_surf`), basement depth (`depth_to_base_surf`), isostatic gravity: depth-stratified conductivity residual curvature and co-located gravity edge | Could isolate covered structural contacts after removing broad basin-depth trends, unlike surface mapping | Conditional residual curvature, not CED edge-centroid displacement, radiometric/gravity fusion, or catalogue-dot propagation | Saline groundwater or clay-rich sediment | Medium |
| 2 | Geodetic dilatation, magnetic anomaly, detrended elevation: signed edge-normal dilatation contrast where relief is weak | Tests buried strain partitioning that need not create a visible scarp | Signed local contrast rather than regional strain magnitude allocation or magnetic/gravity displacement | Geodetic interpolation/smoothing artifacts | Medium; high resolution risk |
| 3 | Basement depth, gravity and detrended elevation: paired curvature-polarity reversals along a common normal | A buried basement step may yield a coupled signature without a surface scarp | Paired sign/polarity condition rather than scalar edge strength, relief strata or dot-derived prior | Depositional basin margin | Medium-high; derivative noise risk |
| 4 | Radiometric K/Th, slope/elevation: relief-conditioned cross-edge asymmetry | Alteration or juxtaposition can produce an off-catalogue geochemical boundary | Tests residual asymmetry, not total-count concordance fusion | Soil moisture, transported alluvium | Medium |

The first three were earlier documented as untested ideas; re-listing is not a new experiment. Candidate 4 is a proposal only. None is viable until the team identifies the method paragraph assigned to this parallel lane. The hypotheses do not require an external dataset in principle, so no new external source is asserted obtainable. The official competition feature metadata and actual access terms still need verification.

## Required next actions / limits

1. Reconcile README, root `docs/run-card.json`, and Pages portal so exactly one run card controls the current download/readiness statement; preserve history but mark stale material unmistakably.
2. Establish the lane's single method paragraph and shared template/evaluator version. Follow the shared template; do not fork evaluator or writer.
3. Restore authorized official inputs to ignored `data/`, then verify pinned hashes and provenance. Do not assume GitHub mirrors imply organizer permission.
4. Run only the assigned candidate, within three experiments/two hours. Apply whole-segment buffered hide-and-recover, fold-specific catalogue feature derivation, exact visible-fault masking, pooled DTI and spatial 95% CI. Run each feature-alone leakage canary before trusting it.
5. Compare pre-placement surface and final dots against the complete fixed registry. Any `rho > 0.90` or >70% 3-px dot overlap means duplicate: stop and report negative. No threshold exemptions.
6. Validate finite footprint values in `[0,1]`, CRS, shape and transform; hash the actual TIFF. A technically valid file is not automatically safe to submit. Slot promotion stays with the separate selector.
7. Install declared dependencies and run complete tests/evidence/portal checks before stating implementation passes. Check official sources and leaderboard only where authenticated access is available; do not convert projections into scores.

No weekly slot was selected or consumed. No current score, registry novelty clearance, or submission readiness is claimed.

## Run card for this review

```json
{
  "hypothesis": "No lane-authorized new hypothesis was run; the ranked proposals above are research queue only.",
  "mechanism": "No new computation or placement. Existing run-card evidence is not re-labelled as this review's result.",
  "named_non_fault_process": "Saline groundwater/clay-rich sediment for the leading conductivity proposal.",
  "holdout_dti": {
    "label": "HOLDOUT-DTI",
    "evaluator_version": null,
    "withheld_positives": null,
    "ci95": null,
    "status": "NOT RUN in this review"
  },
  "correlation_overlap_vs_registry": null,
  "raster_sha256": null,
  "validator_output": {
    "new_tif": "NOT GENERATED",
    "no_nan_inside_footprint": null,
    "values_in_0_1": null,
    "crs_shape_transform_match": null,
    "reason": "Inputs absent and no new artifact"
  },
  "submission_name": null,
  "submission_note": "No new artifact; no slot selected.",
  "verdict": "negative"
}
```
