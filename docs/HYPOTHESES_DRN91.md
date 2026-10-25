# DRN91 preregistration — drainage-deflection / knickpoint lane (2026-10-25)

Lane status: PROVISIONAL — no single assigned method paragraph was supplied in this
session's prompt (flagged in README/IRREGULARITIES by prior sessions). This lane is
chosen from the repo's own ranked-but-never-implemented list (ASC91 #4, MTD91 #3,
S16PC #4).

## Why 0.2778 led (measured in-repo, not organizer-confirmed)
Prior sessions established: sparse ~37,654 unit dots at ~2.8–3 px spacing maximise
300 m triangular-kernel credit per unit mass under DTI (alpha 0.2, beta 0.8);
catalogue-proximal/continuous surfaces waste mass. The 0.2778 figure is a CLAIM
from the GEMSDOE32 page, not an organizer receipt (IR-S16-05). Leaderboard claims
0.4413 / 0.3195 in the brief are likewise unverified here.

## Five candidate hypotheses (ranked, before any DRN91 number)
| # | Layers | Signature | Why it catches catalogue-missing faults | Mimic (non-fault) | Rank/cost |
|---|---|---|---|---|---|
| 1 | B12 det_elev (+B19) | **DRN91: D8 flow routing — log flow-accumulation, channel-head proximity, flow-direction deflection angle, knickpoint (downstream slope break), convergence** as features in a cross-fitted HGB with all 19 sponsor bands | Young/active faults deflect piedmont drainages and create knickpoints even where the scarp is buried/eroded; no prior lane in this repo implemented flow routing (grep: 0 hits in src/) | Lithology-controlled knickpoints; alluvial-fan channel avulsion | 1 / medium |
| 2 | B12 only | Drainage-only HGB (ablation of #1) | Same, isolates drainage contribution | Same | 2 / low |
| 3 | B10/B16 | Seismicity-field anisotropy ridges | Microseismic alignments on blind faults | Catalogue-completeness gradients (100 km smoothing kills 3 px detail — H11-3, deferred there) | 3 / low, high mimic risk |
| 4 | external 1 m DEM | 3DEP scarp features | Expert hidden faults are geomorphic scarps | — | BLOCKED: sandbox egress cannot reach USGS; not viable this session |
| 5 | B15/B13 | Depth-conditioned paired curvature polarity | Buried basin-margin step | Depositional margin | Already covered by CED/F91 family — excluded |

## Frozen protocol
- Reuse vendor/gems57 spatial.folds (label-blind quadrants, whole components,
  buffer 80 px), evaluate_holdout.evaluate/pooled_summary (alpha .2 beta .8, 300 m).
- Every catalogue-derived feature: NONE. Model features are sponsor bands +
  drainage transforms only; per fold, training labels = visible catalogue in the
  fold's train domain only.
- Leakage canary: each feature alone, symmetric AUC > 0.90 = leakage, fail closed.
- Emission: shared submodular_dti_emit (src/gems91/dd_vtc_pu.py), zeros encoding,
  zero mass on catalogue, values in [0,1] via vendor submission_writer.
- Uniqueness: Spearman vs registry/download rasters ≤0.90 and ≤70% dots within
  3 px, checked on surface and final dots; exceedance = duplicate, stop.
- Promotion rule: verdict `promote` ONLY if pooled HOLDOUT-DTI beats the repo's
  comparable best (S14-PTAC 0.267782, gems91-hide-recover-v1.0 — note evaluator
  version differs; comparison is indicative, flagged) AND uniqueness passes.
  Otherwise verdict `negative`, file labelled RESEARCH / NOT OK TO SUBMIT.
- Budget: ≤3 experiments.
