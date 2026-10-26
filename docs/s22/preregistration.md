# S22-OMTJ — preregistered before experimental results

Date: 2026-10-26. Branch: `arena/a3f85c97-gemsdoe91`.

## Lane interpretation
The request refers to a single method paragraph but supplies none. This is a self-assigned narrow lane, not a claimed coordinator assignment. **Odd-moment texture juxtaposition (OMTJ):** use only cached B14 total magnetic intensity and B13 isostatic gravity anomaly. Remove the B14 broad background (Gaussian sigma 12 pixels), compute local central third moment / variance^(3/2) (sigma 3), and target spatial changes in its signed skewness aligned with the B13 gradient (sigma 3). Multiply robust nonnegative skewness-edge strength, gravity-gradient strength and squared gradient alignment. No catalogue features, old raster values, predicted coordinates, supervised fitting, jitter, or leaderboard-score inversion. Fault displacement can juxtapose differently magnetized packages under cover; this is a hypothesis, not proof of geothermal permeability. Non-fault mimic: an unfaulted volcanic flow margin or intrusive lithologic contact.

## Ranked hypotheses (qualitative expected benefit, not projected scores)

| Rank | Hypothesis / specific cached layers | Physical signature; missing-fault rationale | Difference from inspected implementation | Expected benefit / cost |
|---|---|---|---|---|
| 1 | OMTJ, B14 + B13 | Bilateral change in signed magnetic third moment, aligned with a gravity contact; could expose buried juxtaposition without a mapped surface scarp | S19 `compute_directional_semivariogram_features` uses second moments / Hurst / sill jumps; S21 PDWC uses waveform / phase. Neither explicitly uses this gravity-normal third-central-moment boundary | Uncertain, highest among these proposals / low CPU cost; E1 only |
| 2 | Tail-weight juxtaposition, B14 + B13 | Change in normalized fourth central moment along gravity normals; concealed contact separates weak texture from rare magnetic inclusions | Distinguishes kurtosis rather than S19 sill or S21 waveform amplitude | Uncertain / low; not run |
| 3 | Ordinal-texture boundary, B14 + B13 | Discontinuity in local rank-pattern entropy corroborated by gravity; targets offset volcanic texture insensitive to absolute magnetic amplitude | Not a variance/Hurst transform; explicit ordinal-pattern counts not found in inspected `src/gems91` | Uncertain / medium; not run |
| 4 | Cross-contact texture decorrelation, B14 + B15 | Compare along-strike magnetic residual autocorrelation on both sides of a basement-depth boundary; seeks truncated buried fabric rather than a gradient maximum | Explicit paired autocorrelation distributions across a basement normal, rather than scalar semivariogram maps | Uncertain / higher; not run |

These are proposed new combinations within inspected source, not a guarantee they have never been tried in private or sibling work. No new external data is needed. The stack is hash-pinned to `registry/data_manifest.json`; a matching community-mirror hash does not independently authenticate organizer origin. Avoid ambiguous B06/B11/B18 band identities entirely.

## Frozen experiment and gates
- E1 only: sigma background 12 px; moment window 3 px; derivatives sigma 1 px for skewness and 3 px for gravity; floor = 10th percentile positive local variance; skewness clipped to [-5,5]; edge strengths normalized by in-footprint 95th percentiles to [0,1]. Combined surface = cube root(edge_strength * gravity_strength * squared_alignment). No parameter search after results.
- Use existing `vendor/gems57/spatial.folds`, 80 px training buffer, whole 8-connected fault components; no catalogue-derived feature is used. Evaluation masks known/visible pixels exactly. Use shared `vendor/gems57/evaluate_holdout.py`, pooled alpha .2, beta .8, 300 m triangular kernel, 1,000 paired 20 km block bootstrap draws. Record actual positive count, not an assumed count.
- E1 holdout dots allocated in proportion to each fixed quadrant's footprint area (total 37,654); use existing `pdwc21.emit_dots_nms`, spacing 3.05 px and visible-catalogue collar 3.05 px. Do not score a full-catalogue-masked historical raster as a recovered-fault control. Historical best is context only, not a paired comparison; no promotion without a comparable incumbent re-evaluation.
- Canary every input/derived feature used, including the combined surface: all held positives, every fourth negative, each fold; symmetric AUC > .90 is a hard stop. A pass does not prove no leakage.
- Pre-placement exact full-footprint Spearman via shared `SurfaceProbe` against frozen available registry and all pre-existing local downloads. Pin inventory before construction. No reference is excluded for density. Missing references keep clearance UNVERIFIED.
- After holdout, create one new deterministic full-grid prediction and package with shared `submission_writer.py`; immediately test final dots' exact rank correlation and literal directed 3-px overlap. On first breach stop experiments. Keep any already-written raster only as a negative research deliverable, never submit-ready. Do not optimize around the duplicate gate.
- Three experiments / two-hour ceiling; one is planned. The selector and live weekly quota are separate and not authorized here. No submission slots used.
- Organizer score / leaderboard estimate remain null unless an authenticated receipt / defensible independent calibration exists. User-supplied numbers are retained only as unverified claims, never relabeled ORGANIZER-CONFIRMED.

## Previous-session priorities taken first
Repair the conflicting front-door status; preserve dense-reference strictness; restore pinned data automatically; audit exact nine historical artifacts rather than similarly named substitutes; test one distinct mechanism instead of another spacing variant. Fetching fine DEMs from non-allowlisted hosts is not possible here, so no hypothetical DEM result is presented.
