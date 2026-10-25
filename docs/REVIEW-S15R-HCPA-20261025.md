# S15R-HCPA corrected revalidation — negative result, no submission

**Date:** 2026-10-25 UTC

**Status:** **OK TO DOWNLOAD: NO · OK TO SUBMIT: NO · no new candidate TIFF exists**

**Machine-readable record:** [`run-card-S15R-HCPA-20261025.json`](run-card-S15R-HCPA-20261025.json)
**Available-fleet novelty evidence (Pages mirror):** [`data/s15_revalidation_registry_20261025.json`](data/s15_revalidation_registry_20261025.json)

This is a corrected, isolated revalidation of the historical `S15-HCPA` lane. It is not a new lane, a submission, a leaderboard estimate, or permission to use a competition slot. The only replay TIFFs live outside this checkout in a quarantine directory and must not be copied into `docs/downloads/`.

## Executive decision

| Gate | Measured result | Decision |
|---|---:|---|
| Feature-alone leakage canary | worst symmetric AUC = **0.5932** (`hcpa_lidar_scarp_asym`; threshold 0.90) | PASS, but only a leakage screen |
| Best corrected holdout | **E2 = 0.084995 HOLDOUT-DTI**; 95% CI **[0.075507, 0.094735]** | FAIL versus current comparable internal quality bar **0.267782** |
| Final-dot novelty, 62 available frozen references | **99.599%** of 37,654 dots within 3 px of `calib_r13lattice_00904.tif`; limit 70% | DUPLICATE / FAIL |
| Frozen inventory completeness | **62 / 64** references available | UNVERIFIED / FAIL-CLOSED |
| Raster bundle | isolated writer refused an absent SHA ledger | no release receipt; not publishable |

The surface rank result is not a loophole: maximum absolute rank correlation was only **0.15881** (versus 0.90) against `calib_hedgev2_01563_sample.tif`, but Rule 1 requires *both* a non-duplicate surface and non-duplicate final dots. The final-dot check is decisive.

## What was corrected

The historical S15 record evaluated a selector that did not exactly reproduce its far-field/halo final emitter. The revalidation used the corrected selector policy, `farfield75-halo25-visible-catalogue-v2-refill`, in the same spatially blocked hide-and-recover protocol used for evaluation:

- whole fault segments withheld with a buffer;
- catalogue-derived features formed only from visible faults;
- visible fault pixels masked exactly;
- pooled DTI using the 300 m (3-pixel) triangular kernel with `alpha=0.2`, `beta=0.8`;
- evaluator `gems91-hide-recover-v1.0`; **60,988 withheld positives**.

The full scientific-input stack had been restored and SHA/size verified before the isolated replay. This corrects selector comparability; it does **not** make the historical artifact novel or organizer-scored.

## Results — every value is HOLDOUT-DTI, not an organizer score

| Experiment | Interpretation | HOLDOUT-DTI | 95% CI | Emission count in pooled evaluation |
|---|---|---:|---:|---:|
| E1 | HCPA surface | 0.053350 | [0.043133, 0.060825] | 11,292 |
| E2 | HCPA multiphysics corroboration gate | **0.084995** | **[0.075507, 0.094735]** | 28,568 |
| E3 | E2 geometry, 30,000-dot diagnostic | 0.073231 | [0.063916, 0.080307] | 30,000 |
| E3 | E2 geometry, frozen 37,654-dot diagnostic | 0.084995 | [0.075507, 0.094735] | 37,654 |
| E3 | E2 geometry, 44,000-dot diagnostic | 0.094359 | [0.085239, 0.103018] | 44,000 |

The E2 surface was the frozen winner. E3 is a budget diagnostic, not a post-hoc license to choose the largest displayed value; none of its budgets approaches the current comparable internal bar, `S14-PTAC E2 = 0.267782 HOLDOUT-DTI` (95% CI [0.253687, 0.281135], same evaluator and withheld-positive count). That internal bar is **not** a live leaderboard score and is itself a duplicate-negative final artifact. It is used only as a conservative no-regression quality gate.

No `ORGANIZER-CONFIRMED` score exists for S15R. The reported GEMSDOE32 `h33-h33-2-b2` value `0.2778` remains an unverified owner-reported claim in this checkout, not an organizer receipt and not a target passed by this result.

## Geological interpretation: a plausible mechanism that failed empirical discrimination

### The hypothesis

HCPA combined a conductivity/depth proxy, basement-step agreement, thermal-field information, and extensional kinematic context. In an extensional geothermal system, a permeable fault can couple a deep fluid pathway, alteration-related conductivity contrast, a buried structural offset, and focused heat/fluid flow. Such a conjunction is scientifically reasonable for concealed fault targeting because a fault under alluvium can lack a visible scarp.

But the relevant scientific question is not whether that story is plausible. It is whether the chosen proxies rank **withheld fault segments** more effectively than competing surfaces after visible faults and their buffer are removed. The result says no for this implementation.

### Why this can fail even if the geology is real

1. **Conductivity is not a unique fault tracer.** Saline groundwater, clay-rich basin fill, and playa sediment can yield conductivity anomalies without a fault conduit. A conductivity/depth ratio may therefore identify hydrologic or lithologic basin architecture rather than fault permeability.
2. **Basement gradients have non-fault explanations.** Gravity-derived or depth-to-basement transitions can track depositional basin margins, intrusive contacts, interpolation structure, and broad flexure as well as fault steps.
3. **Thermal points are sparse and conditional.** Springs/wells may respond to permeability, recharge, drilling access, and regional heat flow. They cannot independently prove a mapped pixel is a geothermal fault.
4. **Kinematic fields are regional, whereas DTI rewards local placement.** Broad extensional dilation can supply a tectonic prior without localizing a 100–300 m fault trace. The triangular DTI kernel gives limited credit for a broad but displaced anomaly.
5. **Topographic/scarp features can be inherited.** Roads, drainage, alluvial-channel edges, lake shorelines, and erosional contacts can mimic lineaments; the canary only rules out obvious single-feature leakage, not physically plausible confounding.

The corrected score pattern is consistent with a surface that contains broad regional plausibility but little out-of-fold localization of withheld fault geometry. It does *not* prove HCPA physics false; it rejects this feature construction, classifier/emitter combination, and evidence level as a competitive detector.

## Metric reasoning: why sparse geometry did not rescue the surface

For binary emitted mass, the project uses the max-credit DTI form

\[
\mathrm{DTI}=\frac{T}{0.2T+0.2(S-M)+0.8|G|},
\]

where `T` is triangular-kernel truth credit, `S` emitted mass, `M` kernel-matched emitted mass, and `|G|` withheld truth mass. The 300 m triangular kernel saturates locally: multiple nearby dots can consume `S` with little additional `T`. This makes sparse, well-spaced emission a defensible *budgeting* choice, not evidence that a sparse pattern has found faults.

That distinction matters here:

- E3's 44,000-dot diagnostic rose modestly above the frozen 37,654-dot diagnostic, showing that this revalidation did not establish a universal fixed dot count.
- Every tested budget remained far below the comparable holdout bar, so changing geometry cannot repair the principal defect: poor out-of-fold ranking/localization.
- The final 37,654-dot replay is nearly fully covered by the calibration lattice at the 3-pixel metric scale. Even a byte-distinct TIFF with a low surface correlation fails the project's literal directed-overlap rule.

Thus, the metric does not validate a `0.2778` explanation, a live-score projection, or an emission-only route to winning. A future lane must improve spatial discrimination before it can rationally spend a dot budget.

## Registry and quarantine evidence

The available-fleet comparison deliberately used all **62 locally recovered** frozen references, not the old eight-raster convenience directory. Two pins remain unavailable:

- `docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21-zeros.tif`
- `docs/downloads/h33-h33-2-b2-GEOD25m10-20261024-bff9fd21.tif`

Consequently, “universal registry clearance” cannot be claimed. Within the available fleet, the replay's surface passed its rank threshold but final dots failed the directed overlap test:

```text
surface max |rho| = 0.15881, closest = calib_hedgev2_01563_sample.tif
final directed 3-px overlap = 0.99599, closest = calib_r13lattice_00904.tif
```

The all-finite replay twin has SHA-256 `9c6e99c0e8c37a83d8d7d287d0cfb253defa797a8e4f80cf670bac90b156225f`, solely to identify the quarantined negative artifact. Its isolated writer refused final SHA-ledger certification. Neither its format status nor its hash authorizes a download, upload, or inclusion in a public release.

## Source and review boundary

- [DrivenData GEMS competition page](https://www.drivendata.org/competitions/306/competition-doe-gems/) — official competition landing page; live eligibility, slots, deadline, and submission receipt remain human-controlled and were not automated.
- [DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — code/reference context; does not certify this local experiment.
- [DOE GDR submission 1391](https://gdr.openei.org/submissions/1391) — source link retained for manual provenance review of geothermal data context; no claim in this report depends on a newly fetched record.
- [`docs/HYPOTHESES_S15.md`](HYPOTHESES_S15.md) — original pre-registration. Some historical wording there treated the owner-reported `0.2778` too strongly; this corrected review and run card control current status.

## Three-pass implementation and review record

1. **Implementation / verification pass.** Added a shared frozen-inventory reader to `scripts/evaluate_holdout.py`, expanded default local discovery to include `data/fleet_registry/`, reran the available-fleet comparison, and made `scripts/restore_registry.py` report every missing immutable pin. Targeted tests exercise partial inventory reporting and aggregate restoration failure.
2. **Bug / edge-case pass.** Made `scripts/submission_writer.py` transactional from a caller's perspective: a failure after TIFF write, ZIP creation, browser-payload creation, or audit persistence removes every newly-created bundle file. A regression test injects a late audit write failure. The deliberate no-ledger format-test mode is retained but its audit states `TEST_ONLY_NO_LEDGER` and `writer_certifiable: false`.
3. **Final requirements / quality pass.** `scripts/run_s15_lane.py` now completes a hash-verified full-frozen-registry preflight, hard-stops before full-map emission when the comparable holdout loses or the inventory is incomplete, checks the surface before dot placement, and checks final dots before invoking the writer. The README, Pages portal, executive status page, limitations, irregularity register, review, and JSON run card all label this lane negative and offer no new download.

## Required next action

**Stop this lane.** Do not tune the HCPA weights, move dots around the lattice, recreate the quarantined TIFF, or use a partial registry as a pass. Shared code now stops S15 before full-map output if it does not beat the current comparable holdout bar or if the frozen registry inventory is incomplete. A future scientific lane must be separately preregistered, leakage-screened, evaluated, novelty-checked before and after placement, and written only after all gates clear.

This is “Maximize P(Win)” by avoiding a low-evidence slot, and “Own the Outcome” by preserving a falsified result rather than repackaging it as a submission.
