# S26 LiDAR/radiometric research — corrected 2026-10-29

**OK TO SUBMIT: NO.** This is a concurrent, previously generated research artifact, not a candidate created by the current review. The earlier claim that it was unique is superseded: its exact 37,654 final dots overlap the pinned lattice within 3 pixels **99.2325%**, above the literal 70% stop. The earlier 40.82% figure covered only eight restored references and cannot establish complete-registry uniqueness. The new recheck stops at the lattice; pre-placement surface and other references were not rechecked.

| Field | Evidence |
|---|---|
| Research TIFF | [gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.tif](../downloads/gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.tif) · [single-TIFF ZIP](../downloads/gems91-s26-lidarrad-37654dots-20261029-e9ffee0b60-zeros.zip) |
| TIFF SHA-256 | `957a1865781cfd537ecb197fce4d6a931564558ac0c97d8c5a0bf9dad932f35d` |
| Historical research holdout | **HOLDOUT-DTI 0.133242 [0.111054, 0.155289]**, `gems57-pooled-hide-v2`, 60,988 withheld positive pixels, label-blind-quadrants-v3. This is the prior reported holdout, not a leaderboard or static-TIFF score. |
| Holdout limitations | Feature canary code reported the maximum of **mean per-fold AUCs**, not the maximum of each feature and each fold; a high individual fold could be hidden. Source masks/NoData and full data provenance were not independently verified here. A strict matched holdout and canary pass are not established. |
| Format checks | Local single-band float32, [0,1], CRS/shape/transform and catalogue checks pass **against the mirrored sample**. That sample conflicts with the organizer’s public blank-sample description; outside-footprint zero is not proof of compliance with the official null/NaN requirement or server acceptance. |
| Leaderboard estimate | Unavailable. No organizer-confirmed submission receipt or verified score for this artifact. |
| Submission readiness | **NO** — duplicate, data provenance and scientific gates unresolved. |

The S26-FABRIC emitter artifacts are separate; their changed proxy surface and collar were not assessed by the S25 holdout. See the [complete executive comparison](../review-4239f6e5/executive-summary.html), [independent three-file recheck](../review-4239f6e5/concurrent-s26-audit.json), [current review](../review-4239f6e5/REVIEW.md), and [reported holdout](holdout.json). Original run-card and runner bytes are archived in `evidence/concurrent-s26-20261029/`; the unsafe runner entry points are disabled pending a properly assigned and gated experiment.

GEMSDOE32's 0.2778 remains **USER-REPORTED**, not a file-linked organizer receipt. Its possible precision–coverage benefit from thinning redundant dots is a hypothesis, not proof of causation or improvement; nearby new faults can still count.
