# Repository review — `arena/9971ddbb-gemsdoe91` — 2026-10-24

## Decision

**No new experiment or TIFF was generated in this review. No artifact is approved for competition submission.** The user-specified parallel-run protocol makes the lane an explicit prerequisite, but the supplied method paragraph is absent. The repository records the same lane ambiguity in prior review material. Choosing one of the numerous extant method implementations would violate the instruction to stay in the assigned lane. No weekly slot was used.

There are already downloadable TIFFs in `docs/downloads/`; they are prior research artifacts, not output newly generated here. The TIFFs are not interchangeable with submission approval. In particular, the current root `docs/run-card.json` is CED91 and says `verdict: negative`, `submission_ready: false`, final dots `DUPLICATE`, and organizer receipt `null`. Its matching [`docs/REVIEW-CED91.md`](REVIEW-CED91.md) says its TIFF may be downloaded for research but **must not be submitted**. The root README also contains historical session blocks from other branch checkouts; these are not current branch evidence. Do not rely on their old promotion language.

## What the repository contains

- A static Pages site under `docs/`, engineering validators and raster writers in `scripts/`, scientific methods under `src/gems91/`, and a vendored shared evaluator/writer under `vendor/gems57/`.
- Multiple historical TIFF/ZIP releases in `docs/downloads/`. A file hash or distinct filename establishes byte-level distinction only; it does not establish a distinct method or fleet-wide uniqueness.
- Run cards and evidence for multiple lanes (including CED91, H11, S11-MHTR, and ASC91). These must be interpreted according to the current root run card and explicit review status, not by selecting the most favorable historical run card.
- The current root CED91 record reports **HOLDOUT-DTI** `0.062153` (evaluator `gems57-pooled-hide-v2`, 60,988 withheld positives, 95% CI `[0.049910, 0.075115]`). This is a catalogue hide-and-recover measurement, not an organizer score. The CED report records format checks passing but final-dot duplication against the indexed lattice at 99.9125%; that failure blocks submission regardless of format validation.
- Organizer score receipt: none in the current root run card. The user-provided GEMSDOE32 value `0.2778` cannot be explained causally from a score alone. A sparse-dot deletion may reduce uncredited false-positive mass under a distance-tolerant metric, but can also remove useful coverage. This is metric-based reasoning, not evidence that it caused that reported value. No claim of beating it is justified by this checkout's current evidence.

## Protocol and candidate ideas

The prescribed lane paragraph is missing. Therefore the following are **research proposals only**, not authorization to experiment, expected score gains, or results. Candidate layer names are taken from the repository's documented feature vocabulary; source semantics and official provenance must be checked before use. Relative priority and cost are qualitative.

| Rank | Cached layers / signature | Why it could find off-catalogue faults | Difference from reviewed local methods | Named non-fault mimic | Cost |
|---|---|---|---|---|---|
| 1 | Conductivity `cond_surf`, basement depth `depth_to_base_surf`, isostatic gravity `iso_grav_anom`: within-depth-bin conductivity residual curvature corroborated by gravity edge | Could suppress broad basin-depth effects and identify covered basement discontinuities with weak surface expression | Residualized conductivity conditional on basement depth; not CED magnetic–gravity displacement, radiometric TC/Hessian, or inherited-dot placement | Saline groundwater or clay-rich basin fill | Medium |
| 2 | Geodetic dilatation `geod_dilaterate`, magnetic anomaly `mag_anom`, detrended elevation `det_elev`: signed cross-edge dilatation contrast aligned to a magnetic boundary, prioritized in weak-relief terrain | A buried deformation boundary may not produce an obvious scarp | Local signed contrast, rather than regional strain magnitude or edge-centroid displacement | Sparse station interpolation or strain-model smoothing | Medium; resolution risk |
| 3 | Basement depth, isostatic gravity, detrended elevation: paired curvature-polarity reversal along a common edge normal | Could target buried basement steps with little surface relief | Paired signed curvature test rather than scalar edge strength or regional relief ranking | Non-tectonic depositional basin margin | Medium/high; derivative noise risk |
| 4 | Magnetic anomaly plus radiometric potassium/thorium channels: scale-persistent spectral break with cross-channel disagreement | Juxtaposed units can create different surface and subsurface responses | Disagreement detector rather than simple radiometric concordance or dot propagation | Flight-line seam or lithologic contact | High |

All ideas require feature-alone holdout canaries; >0.90 AUC triggers a leakage investigation, not a pass. Use whole-segment buffered holdout, fold-specific catalogue-derived feature construction, exact visible-fault masking, pooled DTI, and a segment/spatial-cluster confidence interval. Compare with the best **compliant, same-evaluator** baseline before any promotion. The repository has many historic numbers with different evaluators; they cannot be ranked as though directly comparable. No external-data-dependent candidate is advanced here, so no new-data source is being claimed available.

## Three review passes

1. **Inspection:** checked branch, working tree, README entrypoint, current run card, CED report, registry/template pin, artifact inventory, test inventory, and historical status records. The working tree was clean at start.
2. **Risk and consistency review:** identified that README's long historic status sections can be misread as current; root run card and CED review are the relevant current negative record. Verified the TIFF files exist, but did not treat presence or prior validator receipts as approval. Confirmed current environment lacks `pytest` (`python -m pytest -q` exits with `No module named pytest`); therefore no test-suite pass is claimed.
3. **Requirement check:** retained explicit no-submit status; did not choose a lane, spend a slot, assert organizer scores, claim full fleet uniqueness, or create a replacement evaluator. Candidate proposals are clearly marked untested. A current branch-specific entrypoint notice was added to README linking this review and the existing research download.

## Limitations / follow-up

- The required assigned method paragraph is absent; this is a hard protocol stop.
- The competition inputs are not present under `data/` in this checkout. Neither `pytest` nor `numpy` is installed, so the full test suite and raster-level verification could not run here. The repository's `scripts/verify_evidence.py` and `scripts/check_artifact_policy.py` did run successfully; these are consistency/policy checks, not pixel-level validation.
- The registry comparison is incomplete by its own run-card statement; no universal fleet uniqueness claim is possible. The literal 70% directed-overlap gate is also vulnerable to near-universal lattice references; changing the threshold or excluding a reference requires shared-policy governance, not a lane-local workaround.
- No current, receipt-backed organizer score, live slot allowance, or official leaderboard confirmation was observed here.
- Public mirror hashes in prior records establish agreement with local pins, not authenticated organizer provenance or data redistribution rights.
- A high hide-and-recover score is not a validated prediction of off-catalogue geothermal exploration performance. The task's label concerns faults; it does not directly verify geothermal vents.
- The full suite and artifact revalidation need to be run in an environment with declared dependencies and the pinned data. No merge or promotion is recommended based solely on this review.

## Review run card

```json
{
  "review_id": "ARENA-REVIEW-9971DD-20261024",
  "hypothesis": "No hypothesis tested: assigned lane paragraph missing.",
  "mechanism": "Not run; preserve protocol compliance rather than select an unassigned lane.",
  "named_non_fault_mimic": "Not applicable; no experiment run.",
  "holdout_dti": null,
  "holdout_ci_95": null,
  "holdout_status": "NOT RUN in this review; current root CED91 record is a historical negative and not reinterpreted as new evidence.",
  "correlation_overlap_vs_registry": null,
  "registry_status": "No new candidate; full registry not proven complete.",
  "raster_sha256": null,
  "validator_output": {
    "new_raster": "NOT GENERATED",
    "current_root_artifact_record": "CED91 format PASS, final-dot duplicate FAIL per current run card; NOT OK TO SUBMIT",
    "no_nan_inside_footprint": "Prior recorded check only; not rerun",
    "values_in_0_1": "Prior recorded check only; not rerun",
    "crs_shape_transform_match": "Prior recorded check only; not rerun"
  },
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "ok_to_download_for_submission": false,
  "weekly_slots_used": 0
}
```
