# Repository review — active Arena checkout (2026-10-25 UTC)

## Executive verdict

**No new experiment or TIFF was generated, and no competition submission is approved.** This is an intentional fail-closed outcome. The parallel-run rules require an explicitly assigned single-method paragraph; the canonical card `docs/run-card.json` states `lane.assigned: false`. Required local rasters are absent (`data/` does not exist), and `scripts/preflight.py` reports every implemented axis blocked. Selecting a previously tested method or deriving a new raster from an old deliverable would violate the lane/uniqueness requirements and would not establish a fresh holdout result.

There are many previously generated TIFFs in `docs/downloads/`; their existence is not evidence that a new TIFF generated during this review is safe or eligible to submit. The current card and prior review explicitly mark prior candidates research-only / negative. Do not upload any file based on this review.

## Review checks and observed results

Commands were executed in this checkout on branch `arena/ca77aa4c-gemsdoe91`:

- `git status --short --branch` initially reported a clean worktree on the active branch.
- `ls -ld data .venv` → neither path exists. Python import probes show `numpy`, `rasterio`, `scipy`, `sklearn`, and `pytest` are not installed in the base environment.
- `python scripts/preflight.py` → **BUILD BLOCKED**. Missing: `sample_submission` and `parent_r0_nan`; all six configured axes are blocked. It writes a local preflight receipt only.
- `python scripts/verify_evidence.py` → **PASS** for its stated limited scope: source provenance, pooled arithmetic, folds, canaries, registry stop, and negative-card consistency; `geological_experiments_rerun: 0`; `submission_ready: false`. This does not freshly rerun the scientific evaluator or validate the missing competition raster.
- `python -m pytest -q` → **NOT RUN**: failed immediately because pytest is not installed. No test-suite pass is claimed.
- TIFF inventory confirms numerous historical files under `docs/downloads/`. This review did not modify or newly certify any of them.

The exact canonical run card records a historical `HOLDOUT-DTI` of `0.0621531283`, evaluator `gems57-pooled-hide-v2`, 60,988 withheld positives, 95% CI `[0.0499103, 0.0751146]`. It also records the final-dot registry duplicate stop at 99.9125% within 3 px, `verdict: negative`, `submission_ready: false`, and `organizer_confirmed: null`. These are inherited evidence in that card, **not a result generated or independently recalculated by this review**.

## Scientific and competition claims

The prompt's GEMSDOE32 `0.2778`, `0.3195`, and `0.4413` figures are user-provided reports and not authenticated submission receipts in this checkout. They must not be described as `ORGANIZER-CONFIRMED` absent a copied receipt. An internal prior review notes a discrepancy between the user-reported GEMSDOE32 score and the source page's UNSCORED language; this review did not fetch or independently verify the live pages. No causal inference about why a particular submission scored as reported is justified from a score and filename alone. In particular, sparse outputs can plausibly trade off distance-weighted matched credit against false-positive mass, but proving that effect requires matched ablations on the same truth, evaluator, split, and budget.

A catalogue hide-and-recover score evaluates recovery of withheld mapped faults under that evaluator. It is not direct validation of geothermal vents, blind fault discovery, nor future organizer test performance. Faults may be geothermal conduits, but fault detection is not itself a vent label.

## Ranked candidate hypotheses carried forward (not tested here)

These are proposals retained from earlier repo review; their novelty is not asserted across all related projects, and none may be implemented before lane assignment and full-code/registry comparison.

| Rank | Hypothesis / physical target | Why it could find unmapped structures | Difference to verify | Expected benefit / cost |
|---|---|---|---|---|
| 1 | Multi-scale fault-tip termination asymmetry: directional gradient rotation, ridge-end pairing and relay-tip geometry at 0.5–2 km. | Targets termination/stepover geometry that may extend beyond mapped traces rather than simply reward the mapped line. | Existing code includes ridge, edge, relay/context and step features; verify a preregistered topology statistic is truly absent. | Medium, uncertain / low–medium. Existing sponsor bands suffice in principle; local inputs/cache unavailable. |
| 2 | Survey-artifact coherence rejection: directional spectral power and cross-sensor coherence to identify flightline-periodic striping. | Separates acquisition/levelling seams from cross-direction geological discontinuities. | Existing seam controls and multisensor fusion exist; distinctness would require a fold-safe explicit nuisance model and negative controls. | Low–medium / medium; existing sponsor bands in principle. |
| 3 | Lithology-conditioned magnetic–gravity displacement using official geologic units. | Unit-conditioned boundary offsets may identify fault displacement while rejecting ordinary lithologic contacts. | Global magnetic/gravity displacement already exists; incremental claim is conditional within-unit behavior. | Medium / medium–high. Requires USGS SGMC polygons; local availability and retrieval were not checked in this review, so not currently viable. |
| 4 | Geomorphic-domain transfer audit (range-front vs piedmont vs basin). | Exposed range-front and buried basin structures may have different observability; measures failure under domain shift. | Primarily a stricter evaluation design, not a new prediction surface. | Diagnostic / medium–high; needs evaluator review and available labels. |
| 5 | Official 1 m DEM scarp asymmetry and slope-break aggregation. | Fine-resolution relief may retain geomorphic evidence lost at 100 m. | Earlier scarp/LiDAR experiments exist; must demonstrate new fold-safe provenance and fusion, not rename an existing detector. | Potentially high ceiling / high cost. Depends on the login-gated competition tile index and official USGS 3DEP tiles; acquisition not verified here. |

Top candidate is not validated. The requirements for its validation—assigned method paragraph, cached stack, sample raster, catalogue, registry set, and shared holdout/writer dependencies—are not satisfied in this checkout. Do not substitute external data opportunistically.

## Existing safeguards and limitations

The repository contains a substantial fail-closed workflow: shared `vendor/gems57` evaluation/writer components, preflight, per-feature canaries in experiment drivers, run cards, registry scans, format validators, artifact policy checks, and a submission-readiness gate. The exact execution path varies by older lane, so each experiment must be checked to ensure it actually uses the required common evaluator and complete registry scope. `verify_evidence.py` is an evidence consistency audit; it is not a replacement for fresh holdout validation or full tests.

Current blockers / risks:

1. No assigned single-method lane in the canonical card.
2. Required data and cached feature stack absent locally; no fresh spatial holdout, leak canary, or surface/final-dot registry comparison is possible.
3. No current test-suite result because dependencies/pytest are absent.
4. The registry/protocol history itself documents a geometric feasibility conflict: the canonical README describes a registry lattice whose coverage makes the ≤70% dot-overlap rule infeasible at the fixed dot budget. Recompute against the complete authorized registry before claiming any candidate can pass; do not weaken the threshold or alter outputs to game uniqueness.
5. No organizer receipt or authenticated live weekly allowance/selector approval was available in this review.

## Required next steps

1. Keep this session's lane unassigned until the exact method paragraph is supplied through the authorized parallel-run coordination process; do not infer it from an old method list.
2. Restore hash-pinned, permitted inputs and cached stack through the repository's documented process; preserve provenance and rerun preflight.
3. Install pinned dependencies and run the full test suite; resolve failures before scientific work.
4. Preregister 3–5 genuinely distinct hypotheses, with layers, mechanism, named non-fault mimic, novelty check, and external-data source/availability where needed. Choose only an assigned candidate.
5. Use the shared hide-and-recover evaluator and writer. Run feature-alone leakage canaries and the complete pre-placement registry surface check before any placement; evaluate final dots too. Stop at three experiments or two hours.
6. Generate and certify a new uniquely named TIFF only after a fresh candidate beats the comparable holdout best with uncertainty and passes every scientific, technical, lane, registry, and separate selector gate. Mark every output clearly **OK TO DOWNLOAD** versus **OK TO SUBMIT**. Do not use a weekly slot until the independent selector step approves it.

## Run card — this review

```json
{
  "hypothesis": "No new hypothesis was experimentally tested: the assigned lane and required local inputs are absent.",
  "mechanism": "No new raster mechanism was implemented; no holdout or submission writer was run.",
  "named_non_fault_mimic": "Granite-carbonate lithologic contact; not evaluated in this review.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_status": "NOT RUN: no assigned lane and no local data/cache",
  "registry_correlation_overlap": "NOT RUN; inherited canonical card records an earlier duplicate stop, not a fresh review comparison",
  "raster_sha256": null,
  "validator_output": "NO NEW RASTER; prior artifacts not freshly validated; required sample raster absent",
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative"
}
```
