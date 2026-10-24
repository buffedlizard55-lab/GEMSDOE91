# CCR91 preregistration — compensated-conductivity residual lane

**Date:** 2026-10-24  
**Branch:** `arena/02c6b911-gemsdoe91`  
**Budget:** at most 3 experiments or 2 hours; no competition upload  
**Evaluator:** shared `scripts/evaluate_holdout.py`, version `gems91-hide-recover-v1.0`  
**Writer:** shared `scripts/submission_writer.py`

## Protocol note and lane paragraph

The user brief says the lane is in a “single method paragraph below,” but no such assigned paragraph appears. This is a reproducible protocol irregularity, not permission to represent a method as externally assigned. Because the same brief also says not to request manual input and requires autonomous completion, this run provisionally selects the highest-ranked, previously preregistered but untested cached-data hypothesis from `docs/HYPOTHESES_CED.md`. It will be reported as **provisional CCR91**, and it cannot be promoted if any stated gate fails.

**Provisional lane — Compensated Conductivity Residual (CCR):** use only sponsor-provided `B17 cond_surf`, `B15 depth_to_base_surf`, `B13 iso_grav_anom`, `B05 iso_grav_anom_slope`, and `B19 det_elev_slope` to remove the broad conductivity trend associated with sediment/basement depth, detect the gradient and multi-scale curvature of the residual, and require alignment/corroboration with a basement gravity edge in low-relief covered terrain. The target is a narrow conductive or resistive discontinuity that remains after basin-depth compensation, rather than raw conductivity, catalogue geometry, inherited submission dots, or a generic potential-field ridge.

The named non-fault process is **saline groundwater or clay-rich basin fill**: both can be conductive without faulting. CCR rejects that mimic only probabilistically, through depth compensation, narrow residual curvature, gravity-edge corroboration, and a low-relief covered-terrain gate. It does not claim the mimic is eliminated.

## Five candidates ranked before implementation

“Expected improvement” is a qualitative ordering, **not a score projection**. All layers are already present in the SHA-256-pinned competition feature raster, so no new external data are required and availability is established locally by `scripts/restore_data.py`.

| Rank | Candidate and exact cached layers | Physical signature / transform | Why it could catch a catalogue-missing fault | Difference from implemented repo work | Named non-fault mimic | Expected DTI improvement | Cost |
|---:|---|---|---|---|---|---|---|
| 1 | **CCR compensated conductivity contact** — B17, B15, B13, B05, B19 | Robust depth-bin median regression of B17 on B15; residual gradient; 0.2–1.0 km residual DoG/curvature; residual-gradient alignment with gravity gradient; deep-cover/low-slope corroboration | A concealed fault can localize conductive hydrothermal clay or juxtapose groundwater units while lacking a mapped scarp; removing the broad depth trend is intended to retain the narrow discontinuity | `H91` uses raw conductivity gradient/clay-cap transforms; `ASC91` uses odd-symmetric steps; `CED91` uses magnetic–gravity centroid displacement. None implements conditional B17-on-B15 residualization followed by gravity-edge corroboration | Saline groundwater or clay-rich basin fill | Highest | Medium, CPU |
| 2 | **Signed strain-boundary contact** — B08 `geod_dilaterate`, B01 `mag_anom`, B12 `det_elev` | Edge-normal signed dilatation contrast aligned to a magnetic boundary, downweighted where a topographic edge is already strong | A buried strain-partitioning boundary may have a magnetic basement expression but no visible scarp | Existing strain lane allocates by regional strain magnitude; it does not use a signed local cross-edge contrast | Sparse-station interpolation / strain smoothing | Medium | Medium; coarse-resolution risk |
| 3 | **Paired basement/gravity curvature polarity** — B15, B13, B12 | Multi-scale signed Hessian eigenvalue polarity reversal on B15 and B13 along a common normal, restricted to weak B12 relief | A covered basin-margin fault may offset basement depth and density in opposite-signed curvature pairs | Basement-step and ASC methods use edge/step magnitude; this tests paired curvature polarity and normal agreement | Unfaulted depositional basin margin | Medium | Medium–high; derivative-noise risk |
| 4 | **Scale-persistent magnetic/radiometric disagreement** — B02 `rtp`, B06 `tc`, B09 `tmi_vg` | Ridge persistence across 0.2/0.5/1 km in magnetic derivatives combined with a radiometric contact that is displaced or polarity-inconsistent | Cover can shift or suppress the surface radiometric boundary relative to a subsurface magnetic contact, indicating a concealed structural contact | MHTR fuses coincident TC and potential-field evidence; this explicitly models cross-layer displacement/disagreement | Flight-line seam or unfaulted lithologic contact | Medium–low | High |
| 5 | **Contextual heteroscedastic residual edge** — B03, B05, B12, B15, B17 | Predict each high-resolution edge response from 2–5 km context, then detect spatially coherent high-variance residuals across at least two physics | A fault absent from mapping can be a local discontinuity unexplained by regional geology/context | HGB-CTX predicts labels from context; this predicts the feature background and uses its residual, with no catalogue feature in the transform | Survey noise or processing seam | Medium–low | High |

## Frozen experiment plan

1. **E1 / CCR-joint:** add six CCR features to the previously measured S11-E2 feature/model/emitter configuration without changing its placement hyperparameters. This isolates feature value. This is the top candidate required by the brief.
2. **E2 / CCR-gated:** only if E1 completes without lane drift, apply a preregistered mild CCR corroboration gate (`0.12` strength) to the E1 surface before the unchanged emitter.
3. **E3 / CCR-parsimonious:** only if E1 and E2 complete without lane drift, use the S11-E2 stack plus the three primitive CCR residual features, excluding joint/gated features, to test whether any improvement is robust rather than due to feature proliferation.

Every CCR feature is tested alone by the shared symmetric-AUC canary before E1. AUC above 0.90 stops the run as leakage. Whole fault complexes are withheld with the shared 10-pixel buffer; all catalogue-derived inputs, if any, must be rebuilt from visible faults, though CCR itself is catalogue-free. Visible faults are masked pixel-exactly. Pooled `HOLDOUT-DTI` uses α=0.2, β=0.8, and the 3-pixel (300 m) triangular kernel; the run reports the shared spatial-block bootstrap 95% CI and all 60,988 withheld positives.

Before placement, the full continuous surface is compared to every available pinned registry raster and must have absolute Spearman rank correlation ≤0.90. After placement, no more than 70% of candidate dots may be within 3 pixels of any one available registry raster. The frozen 64-row registry currently restores only 62 rows; the two missing `GEOD25m10` references remain an explicit completeness failure. The dense `r13_lattice_s5_00904.tif` is not exempted from the literal user rule.

## Promotion rule

Promotion requires all of the following: E1/E2/E3 winner exceeds the current same-evaluator best `0.206406 HOLDOUT-DTI` (version `gems91-hide-recover-v1.0`, 60,988 withheld positives, historical 95% CI `[0.193796, 0.220176]`); leakage canary passes; both registry gates pass within the explicitly incomplete available scope; writer/validator checks pass; and a separate selector later approves a live slot. No holdout result is an organizer score or leaderboard prediction.

## Sources and verification boundary

- Competition reference implementation (official DrivenData GitHub organization): <https://github.com/drivendataorg/gems-prize-reference-solution>. Repository metadata and README were fetched on 2026-10-24; it instructs entrants to download competition data and generate their own model output.
- Competition problem/metric manual-review link: <https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>. This host is outside the current sandbox allowlist; metric details used here are inherited from the pinned shared evaluator and must not be described as freshly fetched in this run.
- Official USGS GeoDAWN source lead: <https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and>. Outside the allowlist in this run; no new file was fetched from it.
- Historical R0 source and downloadable bytes: <https://github.com/buffedlizard55-lab/GEMSDOE32>. Repository tree and artifact availability were fetched through GitHub on 2026-10-24. The reported `0.2778` remains a claim without a submission-page receipt in this checkout.
- Local input identity: `registry/data_manifest.json`; all 15 pins were restored and SHA-256/byte-length verified before this experiment. Pin equality establishes equality to the mirror, not organizer authentication or redistribution permission.
