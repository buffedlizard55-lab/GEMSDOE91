# Repository review and next-step decision — 2026-10-24

## Decision / current status

**No new TIFF was generated in this review. No competition submission is approved.** The user brief's required lane-identifying method paragraph is absent, so an experiment cannot be assigned without violating the parallel-run protocol. The available CED91 run card is a historical negative result, not permission to select another lane or slot. Do not represent any downloaded research TIFF as an approved competition entry.

The shared evaluator/writer is present in `vendor/gems57/`; its provenance and hashes are pinned in `registry/template_pin.json`. The data files were absent at checkout, then four manifest-pinned inputs (`sample_submission`, `existing_faults`, `training_features`, and `parent_r0_nan`) were restored to the ignored `data/` tree and checked against this repository's SHA-256 and byte-count pins. They came from public sibling-repository mirrors, not an authenticated DrivenData download. This establishes identity to the local pins only; it does not establish organizer origin, license, or redistribution permission (see `IRREGULARITIES.md` and `LIMITATIONS.md`). The data are not committed. The refreshed `registry/preflight.json` reports `PRUNE`, `SNAP`, `CONCENTRATION` and `TRACKB` as locally build-ready; `MASS` and `RELIEF` remain blocked by three absent ancestor rasters. Mechanical axis readiness does not supply the missing assigned scientific lane, resolve provenance, authorize an experiment, or approve a submission.

The existing CED91 artifact (`docs/downloads/gems91-ced-v1-20261024-d35670b28c81.tif`) revalidated from disk against the restored sample and catalogue: one float32 band; 3730×3292; EPSG:32611; exact sample affine transform; no non-finite values; values in [0,1]; no positive catalogue mass. Its receipt/run card says **NOT OK TO SUBMIT** because its final dots trip the registered duplicate-overlap rule. Passing format checks does not reverse that verdict. It is an earlier artifact, not a new deliverable of this review.

No new holdout, canary, or registry placement experiment was run. No live organizer receipt, weekly-cap check, or complete fleet-wide novelty scan was obtained. An organizer score cannot be inferred from the reported GEMSDOE32 site value.

## Findings from the code review

1. `scripts/verify_current_artifact.py --with-data` raised an uncaught `FileNotFoundError` when ignored reference rasters were absent. That obscured the useful status and left callers with a traceback. It now emits structured JSON with `status: BLOCKED`, `submission_ready: false`, the error, and a non-zero exit code.
2. `scripts/preflight.py` printed `BUILD ALLOWED` when its two global minimum files existed even if every concrete axis was missing another required input. It also wrote a hard-coded historical check date. The global verdict now follows actual per-axis readiness and the report date is generated in UTC.
3. Tests were added for both fail-closed cases. They test reporting/policy only; they do not rerun scientific experiments.
4. The web portal and artifact policy clearly distinguish `OK TO DOWNLOAD` from `OK TO SUBMIT`. The CED91 raster is explicitly research-only. The README also contains the user's full standing brief; retain it and read it before each project session.
5. Historical sections in README and session reports refer to other branches and past artifacts. Their old results are not the current checkout's organizer confirmations. The inserted README status banner names the authoritative current run card and review.
6. `scripts/validate_raster.py` defaults to requiring NaNs outside the footprint, while the shared writer and active portal-range policy use finite zeros outside to avoid non-finite prediction values. The script has an explicit `--allow-zeros-outside` mode; with that option, the pinned sample, catalogue, parent and ledger, every MUST gate for the existing CED research artifact passed. Without that option, the report flags outside-footprint NaNs as a failure. This is a validator-policy mismatch, not proof of organizer acceptance; the run card still says NOT OK TO SUBMIT due to duplicate dots. See `IRREGULARITIES.md` entry `IR-91-REVIEW-01`.

## Candidate hypotheses: research queue, not an experiment authorization

These four cached-layer ideas were preregistered in `docs/HYPOTHESES_CED.md` before CED91; CED91 (magnetic–gravity edge-centroid displacement) was the only hypothesis tested in that lane. The remaining three are not validated, and qualitative rank is a prioritization judgment—not a numeric DTI forecast. All are subject to lane assignment, canaries on every input/transform, pre-placement registry-surface comparison, and holdout validation before any selection.

| Rank | Layers and targeted physical signature | Why it might locate a fault absent from the catalogue | Difference from implemented methods | Named non-fault mimic | Expected improvement / cost |
|---|---|---|---|---|---|
| 1 | Bands 17 `cond_surf`, 15 `depth_to_base_surf`, 13 `iso_grav_anom`: depth-bin-conditioned conductivity residual curvature, corroborated by gravity edge | Conditioning on basement depth could suppress basin-fill conductivity trends and emphasize a local contact that has little surface relief; faults hidden by cover may be missing from surface-based catalogues | Tests residualized subsurface conductivity curvature rather than CED edge-centroid displacement, radiometric total-count plus gravity-Hessian fusion, conductivity DoG/clay-cap features, or inherited-dot concentration | Saline groundwater or clay-rich sediment | Highest *qualitative* potential among the untested cached-layer candidates; medium implementation cost. No score delta predicted. |
| 2 | Bands 8 `geod_dilaterate`, 1 `mag_anom`, 12 `det_elev`: signed, edge-normal dilatation contrast across a magnetic contact, conditional on weak topographic expression | A concealed strain-partition boundary can lack a clear scarp; the test requires a local signed contrast rather than merely high regional strain | Differs from regional strain-magnitude allocation and CED's magnetic–gravity centroid displacement; excludes dot-derived priors | Sparse-station interpolation / strain-model smoothing | Moderate qualitative potential; medium cost and high spatial-resolution risk. |
| 3 | Bands 15 `depth_to_base_surf`, 13 `iso_grav_anom`, 12 `det_elev`: paired curvature-polarity reversals along a common normal | A buried basement step could make paired gravity/depth curvature without a strong surface scarp | Uses sign and paired curvature, rather than regional relief strata, scalar edge strength, or dip-bracketed dot projection | Depositional basin margin without tectonic offset | Moderate-to-low qualitative potential; medium/high cost because derivative noise and boundary effects need controls. |
| 4 | Bands 1 `mag_anom`, 13 `iso_grav_anom`: signed cross-field edge displacement with a pre-registered scale-consistency control | A buried density/magnetization boundary can be laterally offset from the visible trace under cover | This is the CED91 hypothesis already tested, not a candidate for another experiment in this review; its local holdout did not produce promotion evidence | Intrusive/lithologic contact or survey seam | No new expected gain asserted; medium cost. Do not repeat the locked run. |

The ordering above concerns proposed information value only. It is not a DTI result, and no candidate is designated viable or promoted. Candidate 1 does not require new external data in principle, but it cannot be validated until the session has an assigned lane and the cached input's provenance/use restrictions are resolved. No third-party dataset is proposed, so no unsupported claim that an external download is obtainable is made.

## Research interpretation: the GEMSDOE32 reported `0.2778`

The repository's immutable snapshot review states that the GEMSDOE32 page itself says no organizer score exists for its artifacts and distinguishes projections from results (`docs/sources.json`; source URL is recorded there). The prompt's `0.2778` is therefore a user-reported site figure, not an `ORGANIZER-CONFIRMED` receipt available to this checkout. The mechanism cannot be uniquely inferred from a score alone. A sparse, spatially separated prediction can, in principle, avoid redundant false-positive mass under a distance-tolerant asymmetric metric; deleting dots can also erase useful coverage. This is metric-based reasoning, not a verified causal explanation of that artifact's score. No claim of beating `0.2778`, `0.3195`, or a stated leaderboard maximum is supported without the official evaluation receipt and comparable evaluation evidence.

Official review links already recorded in `docs/sources.json` include the [DrivenData problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [competition data page](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [INGENIOUS](https://gbcge.org/current-projects/ingenious/), and [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b). DrivenData, USGS, GBCGE and NLR sites were outside this session's network allowlist; use the source register's verification status and do not call these links freshly fetched here.

## Three review passes

- **Pass 1 — inspect and implement:** read the standing brief and current run card; inspect readiness, preflight, validation, artifacts, and shared evaluator presence; fix the two fail-closed operational defects and document the ranked untested ideas.
- **Pass 2 — test failure modes:** added regression tests for absent pinned files and for a global preflight that has no ready axis. Revalidated the research artifact with the restored sample/catalogue; no science was rerun.
- **Pass 3 — requirement re-check:** `python -m pytest -q` passes; `scripts/verify_evidence.py` and `scripts/check_artifact_policy.py` pass; the current artifact verifier returns `submission_ready: false`. No new TIFF, holdout value, novelty pass, organizer receipt, or slot selection is claimed.

## JSON run card for this review

```json
{
  "review_id": "ARENA-REVIEW-20261024",
  "hypothesis": "Depth-conditioned conductivity residual curvature corroborated by gravity may localize covered contacts; untested.",
  "mechanism": "Remove within-depth-bin conductivity trend and test residual curvature/edge alignment with gravity; no catalogue-derived placement feature proposed.",
  "named_non_fault_mimic": "Saline groundwater or clay-rich sediment.",
  "holdout_dti": null,
  "holdout_status": "NOT RUN: no assigned lane; no current comparable promotion baseline.",
  "registry_correlation_or_overlap": null,
  "registry_status": "NOT RUN for any new candidate; existing CED91 artifact remains duplicate per its run card.",
  "raster_sha256": null,
  "validator_output": {
    "new_artifact": "NOT GENERATED",
    "existing_ced_artifact": "FORMAT PASS against restored sample and catalogue; not approved because of duplicate gate",
    "no_nan_inside_footprint": true,
    "values_in_0_1": true,
    "crs_shape_transform_match": true
  },
  "submission_name": null,
  "submission_note": null,
  "verdict": "negative",
  "submission_ready": false,
  "experiments_run": 0,
  "weekly_slots_used": 0
}
```
