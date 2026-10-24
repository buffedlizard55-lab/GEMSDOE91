# Parent-free hypothesis preregistration — CED91, 2026-10-24

Read [the project brief](../README.md) first. This supersedes the unsupported forecasts in `HYPOTHESES_G91.md`; that document is historical, not validation evidence.

## Scope, evidence, and lane

The prompt supplies no single assigned method paragraph. To make autonomous progress, this run preregisters a **provisional research lane**, not an assertion of an assigned fleet lane. Lane assignment remains UNVERIFIED and blocks promotion. No weekly slot is selected or used.

**CED91 lane:** build a parent-free surface from magnetic anomaly (cached band 1) and isostatic gravity anomaly (cached band 13). Measure the signed displacement of their local edge-strength centroids along the magnetic normal at two scales; prefer a stable displacement with cross-field normal alignment and persistent edges. Place new dots from this surface, never from R0 or another submission. No strain, thermal, radiometric, catalogue-distance, or inherited-dot prior enters the surface. Mapped faults are used only for visible-pixel masking and hide-and-recover evaluation.

These are falsifiable geological hypotheses, **not established discoveries or score projections**. The cached TIFF describes the two selected bands; its immutable mirror and SHA256 verify identity to the project's pin, not independent organizer authentication. The official reference notebook supports the raster workflow and false-negative-weighted Tversky loss, not the causal geological explanations below. No new external data are required by any proposal.

## Ranked hypotheses not implemented in the reviewed local builders

Ordering is qualitative expected recovery benefit relative to cost, not a forecast of DTI. Only the first is authorized for this run. Existing SNAP follows local gradient crests; RELIEF/GEOD reallocate parent dots; TRACKB chains parent dots. A proposal is not a claim of novelty across inaccessible/private repositories.

| Rank | Hypothesis and specific cached layers | Physical signature / why an unmapped fault might appear | Difference from existing code | Named non-fault mimic | Cost |
|---|---|---|---|---|---|
| First | **CED: stable magnetic–gravity edge displacement**, bands 1 `mag_anom` and 13 `iso_grav_anom` | A buried offset in density and magnetization could produce nearby, aligned but noncoincident edges. Consistent signed centroid displacement at two scales distinguishes this from simply adding gradient magnitudes. Cover may suppress a visible scarp, so catalogue absence is plausible, not guaranteed. | New parent-free two-scale displacement statistic; no crest snapping, copied dots, or catalogue-distance field. | Intrusive/lithologic contact, or a survey seam | Medium; two input bands, CPU derivatives |
| Second | **Compensated conductivity contact**, bands 17 `cond_surf`, 15 `depth_to_base_surf`, 13 `iso_grav_anom` | Residual conductivity curvature, after within-depth-bin detrending, paired with a gravity discontinuity could indicate a permeable buried contact rather than just conductive basin fill. | Conditional conductivity residual, not the previous thermal/concentration or MT-bridge proposals. | Saline groundwater or clay-rich sediment | Medium; no new acquisition |
| Third | **Cross-edge signed dilatation contrast**, bands 8 `geod_dilaterate`, 1 `mag_anom`, 12 `det_elev` | An edge-normal change in dilatation sign, corroborated by a local magnetic edge but not a topographic break, could flag a concealed strain-partitioning boundary. Coarse strain cannot locate a narrow fault alone. | GEOD used regional strain magnitude allocation; this uses a local signed contrast with explicit missing-topographic-expression control. | Interpolation of sparse geodetic observations | Medium; resolution limits may make the test negative |
| Fourth | **Depth-conditioned paired curvature polarity**, bands 15 `depth_to_base_surf`, 13 `iso_grav_anom`, 12 `det_elev` | Opposite signed curvatures across a buried basin margin, with consistent normals but low surface relief, could reveal a concealed basement step. | Tests curvature polarity, not relief terciles, uniform lateral brackets, or catalogue-tip extrapolation. | Depositional basin margin without fault displacement | Medium/high; derivative noise is the main risk |

## Fixed experiment design (one candidate, one matched single-view control)

- Inputs: existing `registry/data_manifest.json` pins; shared template `GEMSDOE78@30f1ab9400f92036b0bc613425f1b5b6046f3897`, copied byte-for-byte into `vendor/gems57`. No private evaluator or writer.
- Edge scales: Gaussian sigma 2 and 6 pixels. Centroid window sigma 3 pixels. The Gaussian moment identity gives edge centroid shift `sigma² * grad(log(smoothed edge strength))`; project the cross-field difference onto the magnetic unit normal.
- Candidate surface: geometric mean of the four empirical edge-strength percentiles, multiplied by cross-field axial alignment and an exponential penalty for cross-scale signed-displacement disagreement. The shift is a local weighted-centroid statistic, **not a recovered fault dip or depth**.
- Output: 32,000 new binary dots, deterministic descending surface ranking, strict greater-than-3-pixel separation. Count is preregistered, not tuned to outcomes. Same density in each holdout quadrant; no truth-dependent budgets.
- Canary: raw bands and every transformed input alone on the held-out catalogue pixels versus catalogue-zero proxies; AUROC above 0.90 quarantines the run. Passing a canary is not proof of no leakage.
- Holdout: canonical `spatial.folds`, four fixed label-blind quadrants; whole 8-connected fault components touching a quadrant are removed from visibility; 80-pixel training exclusion buffer. No fitted/catalogue-based features, so no hidden catalogue enters inference. Visible faults are masked pixel-exactly.
- Metric: canonical `evaluate_holdout.py` (`gems57-pooled-hide-v2`), alpha 0.2, beta 0.8, triangular radius 300 m. Pool additive components first. Paired physical 20 km cluster bootstrap, 1,000 draws, seed 520810; report withheld positive count and 95% CI. This is HOLDOUT-DTI, not an organizer result.
- Control: magnetic-edge persistence alone, placed with the identical rule and density. R0 is a forensic comparison, **not** an independent trained baseline: it was built with the full catalogue. No prior comparable compliant best is recorded here, which independently blocks promotion.
- Novelty: full-footprint Spearman correlation before placement and on final dots; directed fraction of candidate dots within 3 pixels of any positive registry support after placement. Thresholds are strict `>0.90` / `>0.70`, without saturated-reference or continuous-support exemptions. Log a duplicate and stop this scientific experiment at the first violating raster. Missing/unreadable references are UNVERIFIED, not PASS.
- Registry scope: restore the pinned public `60GEMSDOE` raster registry plus this checkout's advertised artifacts. Audit the supplied fleet pages separately. Inaccessible artifacts, absent ledger rasters, and unindexed private files prevent a universal uniqueness claim.
- Export: canonical `submission_writer.py`, all-finite float32 in [0,1], zeros outside footprint, no nodata sentinel; exact sample CRS/shape/transform; re-read and single-TIFF ZIP validation. A format PASS does not override a negative science/novelty verdict.
- Budget: **one candidate experiment** (control and canaries are instruments), never more than three experiments or two hours. Stop if duplicate or leakage is detected. Negative and blocked results remain downloadable research deliverables, clearly not approved for competition upload.

## Promotion rule

`submission_ready` requires all format, canary, complete-scope novelty, assigned-lane, comparable-best improvement, and separate-selector gates. A missing gate is false. Even a positive local paired difference cannot authorize a weekly submission without a comparable historical best and complete scope. No value in this document is ORGANIZER-CONFIRMED.

## Official links for manual review (not falsely marked fetched)

- [Organizer reference solution, verified GitHub snapshot](https://github.com/drivendataorg/gems-prize-reference-solution/tree/aebe92f7c8a990f0e3443451b7a825d9afd6336b)
- [Problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — outside sandbox network allowlist.
- [Official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — outside sandbox network allowlist; weekly allowance and deadline not independently checked.
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and) — source lead, not fetched here.
- [INGENIOUS](https://gbcge.org/current-projects/ingenious/) and [GDR 1391](https://gdr.openei.org/submissions/1391) — context leads, not fetched here.

The objective is **fault mapping for geothermal exploration**, not direct vent classification. No vent is declared discovered by this experiment.
