# GEMSDOE91 repository review — Arena branch 6fedef59 (2026-10-25 UTC)

## Outcome

**Negative / research-only. No new experiment was run, no new TIFF was generated, and no competition slot was used.** This is the protocol-compliant outcome, not a claim that the existing candidate is competitive. The lane in the canonical `docs/run-card.json` is explicitly `assigned: false`. Required data are absent (`data/` does not exist) and Python cannot import NumPy, so the shared cached-feature holdout, feature-alone canaries, fresh raster validation, and complete-registry uniqueness scan cannot be rerun in this checkout. Do not infer a lane from artifacts made in other sessions.

A pre-existing, distinctly named TIFF is available for **research download only**: [gems91-unique-offcatalogue-damagezone…-zeros.tif](downloads/gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119-zeros.tif). It is **NOT CLEARED TO SUBMIT**. Its own historical card labels it negative (`HOLDOUT-DTI=0.0`) and says only one registry raster was checked; thus the card's “uniqueness pass” does not establish uniqueness against the full authorized registry. File existence and a unique filename are not a new experiment or evidence of score improvement.

## Why not create another raster now

The user-provided run protocol is binding: one assigned method lane; cached stack + shared holdout/writer; pre-placement and final-dot registry tests; stop on rank correlation >0.90 or >70% within 3 px; no more than three experiments/two hours; no slot absent better comparable holdout. The canonical run card has no assigned lane. No local `data/` or NumPy is present, so new values could not be derived and audited from required inputs. Re-emitting, perturbing, or renaming an old raster would not meet the unique-new-submission requirement and could constitute protocol gaming. Therefore no fresh TIF is represented as generated or validated here.

The requested 0.2778, 0.3195, and 0.4413 are conflicting user-supplied reports, not copied submission receipts in this checkout. They are **not ORGANIZER-CONFIRMED** and are not comparable without the official receipt, exact evaluator, and split. A score from an official leaderboard is also not causal evidence about a particular model's mechanism.

## Scientific interpretation and hypotheses

A plausible explanation for a high sparse-dot result such as the reported GEMSDOE32 0.2778 is that sparse emission reduces false-positive mass while retaining useful distance-weighted coverage under a spatial Tversky/DTI objective. That is a hypothesis, not a demonstrated explanation. Causality requires a same-surface, same-fold, same-evaluator ablation ladder that varies only pruning/dot density. Catalogue collars may also suppress predictions near visible faults, but can inadvertently eliminate useful fault extensions. No score projection is made.

The target is fault mapping relevant to geothermal exploration; a catalogue hide-and-recover score does not establish discovery of blind faults or geothermal vents. Vent discovery needs independent geothermal evidence/labels. Faults may provide permeability, but are not themselves vent labels.

Ranked proposals below are **not run**. Novelty statements are provisional because similar components already exist in this extensive repository and companion GEMSDOE repositories. The first two need no new external data but are currently blocked on local competition inputs and explicit lane assignment. No proposed experiment may exceed the experiment/time cap.

| Rank | Hypothesis; layers/signature | Why it could recover faults absent from catalogue | Difference to check against repository | Expected DTI gain / cost | Data and viability |
|---|---|---|---|---|---|
| 1 | **MFTA — multi-scale fault-tip termination asymmetry:** existing magnetic, gravity and DEM gradient/curvature bands; paired ridge endpoints, directional gradient rotation and relay-tip geometry at roughly 0.5–2 km. | Targets unmapped splays/stepovers and trace terminations rather than merely scoring the mapped fault centreline. | Existing code already contains ridge, edge, relay/context and step features. Only a preregistered tip-topology statistic with matched controls would be distinct; verify by source/code search before implementation. | Medium but uncertain / low-medium cost. | Existing cached layers should suffice in principle; `data/` and cache unavailable, so not runnable now. No new external source needed. |
| 2 | **SACR — survey-artifact coherence rejection:** GeoDAWN magnetic/radiometric channels; directional spectral power and cross-sensor coherence to reject flightline-periodic seams. | Survey stripes/levelling seams mimic lineaments; cross-direction geological continuity may distinguish true structures. | Existing seam controls and cross-physics fusion are present. Must show a new fold-safe nuisance model and explicit stripe negative controls, not rename prior seam work. | Low-medium / medium cost. | Sponsor layers in principle; exact local grids absent. Not runnable now. |
| 3 | **LCMD — lithology-conditioned magnetic–gravity displacement:** geophysical edge bands plus mapped geologic-unit boundaries; signed offset conditional on unit. | A fault may displace property boundaries within a unit; conditioning may distinguish that from ordinary lithologic contacts. | CED91 already studies global magnetic/gravity centroid displacement; only unit-conditional testing and contact controls might be new. | Medium / medium-high cost. | Requires official USGS SGMC data. Source record for manual review: https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a . Availability/download/licensing not verified here; **not currently viable**. |
| 4 | **BFT — blind-fault transfer by geomorphic domain:** DEM/geophysical layers; report range-front, piedmont, basin performance with visible-fault-only catalogue features. | Exposed and buried faults may differ in observability; domain shift can expose generalization failure. | Changes evaluation design more than predictor; must also report the common holdout for comparability. | Diagnostic potential, no assumed gain / medium-high cost. | Existing layers in principle; new evaluator protocol and lane approval required. |
| 5 | **ODSA — 1 m DEM scarp asymmetry:** official 1 m DEM tiles; scarp-face asymmetry, local relief and slope-break orientation aggregated to template scale. | Fine-scale scarps can be lost in 100 m terrain derivatives. | LiDAR/scarp methods already exist; novelty requires fresh, provenance-tracked 1 m inputs and fold-safe fusion. | Uncertain / high cost. | Competition data tab's `1m_DEM_links.csv` is login-gated; official 3DEP source: https://www.usgs.gov/3d-elevation-program . Tile access not obtained/verified, so **not viable yet**. |

No candidate passed a fresh holdout. Consequently none beats a current comparable holdout best; do not spend a submission slot.

## Existing artifact notes and irregularities

- `docs/run-card.json` is the canonical run card and records `lane.assigned: false`; its CED result is historical and includes a duplicate stop. Do not treat this as current experiment output.
- `docs/run-card-unique-offcatalogue-damagezone.json` says `registry_rasters_checked` contains only `GEMSDOE32__h33-2-b2-zeros.tif`; its reported uniqueness numbers therefore cannot certify complete-fleet uniqueness. The latest report states the TIFF path and receipt, but no current execution reproduced them.
- That artifact card reports **0.0 HOLDOUT-DTI**, evaluator `gems91-hide-recover-v1.1-nohalo`, 60,988 withheld positives and CI `[0,0]`. The stated rationale (design intentionally off-catalogue) makes this a negative catalogue-recovery test, not evidence of discovery utility. It cannot be compared directly with historical scores without identical evaluator/split definitions.
- The artifact's primary zero-filled TIFF is intended to avoid the DrivenData `[0,1]` rejection; its historical audit records single-band float32, EPSG:32611, 3730×3292, and a 100 m affine. These are inherited audit claims, **not freshly rerun in this review**. The companion NaN-outside TIFF is not the safer upload choice.
- “OK to download” means only that the file is available; it does not mean organizer acceptance or submission approval. Here: **OK TO DOWNLOAD: YES (research only); OK TO SUBMIT: NO.**
- The branch-specific prior report and README contain extensive historical records. Their different branch names, run dates, data states, evaluators, and registry scopes must not be conflated with this branch's current status.

## Commands / verification

- `git status --short --branch` at review start: clean, branch `arena/6fedef59-gemsdoe91`.
- `ls data`: absent.
- Python import probe: `ModuleNotFoundError: No module named 'numpy'`.
- `scripts/check_unique_registry.py` depends on NumPy and rasterio and discovers only local `data/registry` and `data/registry_siblings`; it cannot currently establish full fleet scope here.
- Full pytest, shared holdout, canaries, validators, and TIFF readback were **not run** in this review. No pass is claimed.
- No outbound-source claims beyond the listed official links are represented as freshly checked; network restrictions and missing credentials limit retrieval.

Official/manual-review references: [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/), [problem description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [login-gated data tab](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution), [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [USGS SGMC record](https://www.sciencebase.gov/catalog/item/6312f0f2d34e36012efa234a), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), [EPSG:32611](https://epsg.io/32611), and [DrivenData leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).

## Next actions

1. Keep lane unassigned until the authorized coordination provides the exact method paragraph.
2. Restore permitted data and pinned cached feature stack; record hashes, provenance and license. Install pinned requirements and run preflight and full tests.
3. Confirm novelty versus `src/gems91/`, vendor shared template and available registry before preregistration; then run each feature-alone leakage canary.
4. Use the shared evaluator/writer and hide whole fault segments with buffer; mask visible catalogue pixels exactly. Compare against an identical-protocol holdout best with CI.
5. Run complete-scope surface rank-correlation before placement and final-dot overlap after placement; stop at protocol thresholds, including inability to establish complete scope.
6. Only then produce a newly named candidate; promote only if it improves comparable holdout and passes all gates. Weekly slot selection is separate and remains unused.

## Run card (this review)

```json
{
  "hypothesis": "No newly tested hypothesis; MFTA is the highest-ranked unrun proposal.",
  "mechanism": "No new raster or experiment; existing off-catalogue damage-zone raster is historical and research-only.",
  "named_non_fault_process": "Unaltered lithologic contact; survey flight-line seam.",
  "holdout_dti": null,
  "holdout_ci95": null,
  "holdout_status": "NOT RUN in this review; missing local data/dependencies and unassigned lane. Historical candidate card reports 0.0 HOLDOUT-DTI (gems91-hide-recover-v1.1-nohalo; 60,988 withheld positives; CI [0,0]).",
  "correlation_overlap_vs_registry": "NOT freshly measured. Historical candidate card checked one listed registry raster only; not complete-scope certification.",
  "raster_sha256": "a5636b10237757cda5de1a7561a0d5f2600479cdd8610226dfd4c1650b66ca11 (historical artifact; not generated in this review)",
  "validator_output": "Not rerun. Historical audit reports finite [0,1], no NaN, EPSG:32611, shape 3730x3292, stated transform; unverified here.",
  "submission_name": "gems91-unique-offcatalogue-damagezone-20261025T132549Z-b9acc119 (existing research download)",
  "submission_note": "Off-catalogue damage-zone lattice; negative catalogue holdout; download for research only, not approved to submit.",
  "verdict": "negative"
}
```
