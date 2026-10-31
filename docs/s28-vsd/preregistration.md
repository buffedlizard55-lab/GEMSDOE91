# S28-VSD lane preregistration — 2026-10-31 (frozen BEFORE execution)

**Lane assignment.** The session prompt's PARALLEL-RUN PROTOCOL item 2 assigns this
session's single method paragraph: *"Use the template's cached feature stack,
evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover: withhold
whole fault segments with a buffer, derive every catalogue-based feature only from
the visible faults, mask visible faults pixel-exactly, score pooled DTI (alpha 0.2,
beta 0.8, 300 m triangular kernel)."* This file implements exactly that paragraph.
`assigned_lane: true` with `lane_source: "session prompt 2026-10-31, PARALLEL-RUN
PROTOCOL §2"`.

**Template reuse (Rule 2).** Feature stack = the template's cached 38-static stack
(`gems91.cvdc_osdr27.compute_cvdc27_features`, regenerated because `data/work` is
git-ignored). Evaluator = `vendor/gems57/evaluate_holdout.py`
(`gems57-pooled-hide-v2`, folds `label-blind-quadrants-v3-feature-buffered`,
`spatial.folds(catalogue, footprint, buffer_px=80)`). Writer/validator =
`vendor/gems57/submission_writer.write_submission` + `vendor/gems57/validate`.
Dot machinery = `gems91.pdwc21` (NMS, submodular CELF, `compute_directional_ac_8`,
`fit_predict_pdwc_specialist`). Nothing metric-bearing is rebuilt or forked.

## Why (the science this lane tests)

The nine focus sites' best family (GEMSDOE24/25/27/28/30/31/32/33/36 leaders,
0.2449–0.2778 USER-REPORTED) tiles a strong geophysical surface with dots and
prunes clutter. Two levers remain unexploited by anything in this repo:

1. **Cross-domain edge concordance.** No prior lane required a candidate
   structure to appear in *both* the density field (B13 isostatic gravity) and
   the susceptibility field (B02 RTP magnetics) with matching azimuth across
   multiple scales. This is the classic integrated aerogeophysical signature of
   a deep-seated fault: intrusions fail the gravity leg, basins fail the
   magnetic leg, gridding seams fail the multi-scale persistence leg.
2. **Relay/stepover gap morphology.** No prior lane treats the *gaps between
   nearby geophysical lineaments* as the target. USGS process evidence
   (structural-discontinuity study; slip/dilation SIR 2026-5073) says
   hydrothermal fluids concentrate where strain localizes at stepovers, bends,
   relay ramps and terminations — precisely where the public catalogue is
   thinnest, so hidden new faults should bridge gaps, and morphological closing
   of the concordant-edge support finds those bridges without any catalogue.

## Ranked candidate hypotheses (5)

| Rank | ID | Hypothesis (layers → transform) | Why it should catch faults missing from the catalogue | How it differs from everything in this repo | Expected ΔHOLDOUT-DTI | Cost |
|---|---|---|---|---|---|---|
| 1 | **CDEC** | B02 rtp × B13 iso_grav_anom → masked multi-scale (300/600/1200 m) gradient fields; geometric-mean amplitude × cos²(Δazimuth) concordance; min/mean persistence + ring contrast | A buried fault juxtaposes bodies with both density AND susceptibility contrasts; un-mapped segments still leave the double edge even where the map is silent | No prior module computes cross-field orientation-matched concordance; `fabric25` used phase-lag between B13/B14 (single scale, no azimuth agreement), `cckm24` used single-band kurtosis, `cvdc_osdr27` used contour–potential tangent discordance of different band pairs with odd-symmetric steps | +0.010…+0.030 | Low (6 gaussian/sobel passes) |
| 2 | **TSR** | CDEC 600 m support → binary closing at r=3/6/10 px; gap ranks, gap strength, tip proximity | Coulomb stress transfer concentrates dilation at stepovers/tips/relay ramps; hidden new faults bridge between mapped lineaments; the catalogue itself never marks bridges | No prior module scores inter-lineament gap morphology; `mhtr_coda`/`spac_coda` are collars/halos of catalogue lines, `lftg17` is tip-geometry of catalogue-free ridges without closing-gap semantics | +0.005…+0.020 | Low (binary closing + EDT) |
| 3 | **STA** | B16 ieq × B10 deq → smoothed density/proximity ranks; azimuth of seismicity gradient × azimuth of CDEC edge → alignment × coupling | Active geothermal-permissive faults carry aligned seismicity; alignment kills the diffuse-swarm mimic | `h19-4` used "thermal-pop" seismicity as raw corroboration; `geoms33` used seismicity standalone (0.0963 leaderboard as a solo lane); no module couples seismicity *azimuth* to edge *azimuth* | +0.003…+0.015 | Low |
| 4 | **Stage-2 nested auto-context on the widened stack** | 38 template statics + 15 VSD → nested leave-one-quadrant-out stage-1 → 8 directional AC features (template's `compute_directional_ac_8`) → PU-specialist stage-2 | Spatial context lets corroborated edges recruit neighbours along strike — where hidden segments extend beyond visible catalogued strands | Same machinery as the template lane but the AC stage has never seen CDEC/TSR/STA inputs | +0.005…+0.025 over E1 | High (16 specialist fits) |
| 5 | **DTI-aware emission (CELF vs NMS) at fixed budget** | winning surface → exact 300 m-kernel submodular CELF vs greedy NMS at 37,654 dots | The metric's triangular kernel rewards covering max-credit pixels first; greedy NMS wastes budget on redundant ridge tops | `emit_dots_celf_submodular` exists (template) but emission choice has never been a *preregistered paired arm* in this instrument | +0.000…+0.010 | Low |

Named non-fault mimics (must be stated, Rule 5): CDEC — lithologic/plutonic
contacts concordant in both fields, GeoDAWN seam/gridding artifacts (mitigated by
multi-scale min-persistence); TSR — volcanic dike step-overs and tuff-contact
bridges, braided-drainage/shoreline lineaments that nearly touch; STA —
magmatic/geothermal microseismic swarms not on faults. None of these families
observes vents or reservoirs directly.

Negative controls (predeclared): (a) CDEC with the magnetic azimuth field rotated
+90° must lose its feature-alone holdout AUC (recorded in the feature receipt);
(b) static-family surfaces are scored as matched controls and must NOT beat the
fitted arms by much — if a raw static control beats the fitted model, the fit is
suspect; (c) leakage canary threshold: any single feature with symmetric AUC
> 0.90 on the hide-and-recover folds fails the lane (Rule 4).

## Experiments (exactly 3; ≤ 2 h wall-clock; then STOP)

All arms share the identical folds, seeds, budgets, trainer family and emitter
scoring path; only the declared factor varies. Primary scoring emitter for model
arms = greedy NMS (same as the matched controls). Primary emitter for the emission
arm = submodular CELF. Every reported number is `HOLDOUT-DTI`
(`gems57-pooled-hide-v2`, 95% blockwise-bootstrap CI, n withheld positives
recorded).

- **E1 `s28_e1_stack53_hgb`** — S25-HGB trainer (matched to controls, 4:1
  negatives, seed-prescribed) on the widened 53-feature stack (38 template
  statics + 15 VSD) → stitched 4-fold OOF surface → NMS at 37,654.
  Factor under test: added VSD families vs `control_s27static38_hgb` (same
  trainer, 38 statics) — paired Δ must be positive for CDEC/TSR/STA to count.
- **E2 `s28_e2_stage2_ac_stack53`** — template nested leave-one-quadrant-out
  stage-1 + `compute_directional_ac_8` + PU-specialist stage-2 on the widened
  stack → OOF → NMS. **Wall-clock guard (predeclared):** after E1, measure the
  per-specialist-fit time; if (measured fit × 16 fits + E3 reserve 20 min)
  exceeds the remaining budget, run the preregistered fallback **E2b**: AC
  features from the *nested* stage-1 are replaced by AC features computed
  fold-locally on the E1 OOF surface restricted to each fold's region (still
  label-blind within the fold; documented as a weaker context probe), then the
  same HGB trainer refit. The trigger and which path ran are recorded in the run
  card. No third substitute exists.
- **E3 `s28_e3_celf_emission`** — winning surface of {E1, E2} (by pooled
  HOLDOUT-DTI, NMS) → submodular CELF 300 m kernel at 37,654 with
  `uniqueness_cap=0.64` vs the 181 competitive sparse references → CELF-scored
  holdout. Factor under test: emission policy at fixed budget.

**Packaging rule (predeclared):** ship the argmax primary-pooled-HOLDOUT-DTI arm;
final raster always written by the shared writer as `{0.0, 1.0}` unit-mass dots
("zeros" encoding: every pixel finite in [0,1] — this is what passes the
organizer's range check), 37,654 dots, zero dots on catalogue or outside
footprint, after Rule-1 gates (surface |ρ| ≤ 0.90 vs all 211 frozen references;
dots ≤ 70% within 3 px vs every non-dense reference). The synthetic 5-px
calibration lattice is dense-blanket; its overlap is reported with the
preregistered capacity-bound explanation, never as a silent exemption.

**Budget:** ≤ 3 experiments, ≤ 2 h, 0 weekly submission slots. A negative result
is a deliverable; the lane stops after the card is written.

## Score-estimation instruments (no projection is a score)

- `HOLDOUT-DTI` (this instrument) — measures catalogue-segment recovery, *not*
  the leaderboard.
- Blind USGS SGMC off-catalogue DTI proxy (report-only).
- LFI leaderboard-feedback-inversion projection on the final dots, refitted on
  the 108 restored USER-REPORTED anchors — labelled
  `MODEL_PROJECTION_NOT_A_SCORE`, never quoted as a score.

## Freeze

`docs/s27-osdr/frozen-registry.json` (211 references, frozen 2026-10-29 before
any S28 model execution) is reused as the complete available registry witness;
its sha256 is recorded by the runner at prep time. This file's sha256 is recorded
in the run card; any post-freeze edit invalidates the lane.
