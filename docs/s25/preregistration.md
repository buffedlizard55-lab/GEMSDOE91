# S25-FABRIC — preregistration (written before experimental results)

Date: 2026-10-28. Branch: `arena/6c45b779-gemsdoe91`. Values: **Maximize P(Win) · Own the Outcome.**

## Lane status (honest statement)

The supplied prompt says "Your lane is the single method paragraph below" but contains **no
single method paragraph** (verified again in this checkout; `registry/experiment_plan.json`
records `lane: null`). The same prompt instructs: generate 3–5 new candidate hypotheses, rank
them, validate the top candidate on the spatially blocked holdout before touching a submission
slot, and work the previous sessions' next steps first. Session 24 executed rank 1 of the merged
2026-10-27 shortlist (CCKM, verdict negative) and explicitly reserved its rank-2/rank-3 items.
This session therefore runs **one self-assigned narrow lane** built from those two reserved,
still-unimplemented items (verified by `grep` over `src/gems91/` on 2026-10-28: no
`granulometr*`, `phase-lag`, `cross-spectral`, `pattern spectrum`, or morphological-opening
implementation exists). This is not a claimed coordinator assignment and is recorded as an
irregularity. No weekly submission slot is used; promotion remains a separate selector step
(parallel-run protocol rule 6).

## The single method (this session's lane)

**FABRIC — cross-fabric discontinuity, spatially cross-fitted.** A fault is a boundary across
which the *fabric* of the crust changes: the scale/orientation content of the topography and the
spatial registration between the density and magnetization boundaries. Catalogue-missing faults
(buried under bajada/Lake Lahontan sediment, or with scarps too subdued for the mapping that
built the USGS/INGENIOUS catalogue) should still (a) separate fan/bedrock surfaces whose
oriented morphological-granulometry spectra differ across the trace, and (b) offset the gravity
boundary from the magnetic boundary, producing a coherent local **cross-spectral phase lag**
between B13 and B14 that a vertical, unfaulted contact does not. The lane measures exactly these
two fabric contrasts, adds the raw 19-band GeoDAWN context, and lets a spatially cross-fitted
gradient-boosted model (the repo's established OOF pattern) decide their joint value. The
catalogue enters **only** as training labels inside each fold's training domain, as the
emission collar, and as the pixel-exact scoring mask. No catalogue-distance feature, no prior
submission raster, and no external raster is used as a feature.

**Named non-fault mimics:** unfaulted dipping lithologic contacts (also produce gravity–magnetic
lag), remanent-magnetization offsets, alluvial-fan lobe boundaries and shoreline/beach-ridge
fabrics (granulometry contrasts without displacement), GeoDAWN flight-line levelling seams.
A fault prediction is not evidence of a geothermal vent, permeability, temperature, or a
productive reservoir.

## Ranked hypotheses (qualitative; not score forecasts)

| Rank | Layers → signature | Why it could catch a catalogue-missing fault | Difference from inspected implementation | Expected benefit / cost; data gate |
|---|---|---|---|---|
| 1 | **B12+B19 oriented granulometry contrast + B13/B14 cross-spectral phase lag + 19-band context → spatial OOF (this lane)** | Buried/subdued traces separate different surface fabrics and mis-register density vs magnetization boundaries even with no mapped scarp | S24 rank-2/rank-3 were preregistered but never implemented; no opening-spectrum or phase-lag code exists in `src/`. Prior OOF lanes (PDWC/SVHF/…) used derivative/waveform/variogram features, never fabric spectra or inter-field lag | Highest executable-here / ~1 h CPU. No new data |
| 2 | B12+B19 oriented granulometry contrast alone as a standalone surface | Same fabric argument, topography only | Not implemented anywhere in repo | Uncertain-low alone: standalone single surfaces measured HOLDOUT-DTI 0.0148 (S23) and 0.0460–0.0759 (S24) on their instruments. Included as a preregistered control arm, not a separate experiment |
| 3 | B13+B14 phase-lag magnitude × coherence alone as a standalone surface | Offset density–magnetization contacts at depth | `cwpc17` computes cross-wavelet features inside an ensemble; a standalone tile phase-correlation lag field was not found | Uncertain-low alone (same single-surface evidence). Control-arm component |
| 4 | GeoDAWN radiometric K/Th/U ternary alteration lineaments (`ext_geodawn_rad_u8`) | Hydrothermal K-metasomatism / leaching along permeable fault conduits | Radiometrics appear in fleet repos; in this repo the stack is pinned as **REPORT-ONLY, licence unchecked** (`registry/data_manifest.json`) | **Not viable as a feature source until licence/provenance is resolved.** Free official source if pursued: USGS GeoDAWN airborne radiometric surveys, https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and (sandbox cannot fetch bulk data; verified S22) |
| 5 | USGS 3DEP 1 m DEM → scarp curvature/openness U-Net | Metre-scale scarps invisible at 100 m | Repo DEM work uses 100 m bands; a derived `lidar_scarp_features_u8` exists but is licence-unchecked and already exploited by S14/S15 lanes | Highest expected value overall but **not executable in this sandbox** (official hosts unreachable, tested S22). Free official source: USGS 3DEP, https://www.usgs.gov/3d-elevation-program/about-3dep-products-services — needs an unrestricted machine + tile pinning first |

## Instrument statement (why no prior number is the bar)

`vendor/gems57/spatial.folds` is now **v3** (`label-blind-quadrants-v3-feature-buffered`); its
docstring states v2 results "must not be compared as matched holdouts". Verified line by line:
current `spatial.py` sha256 `dd3c4e5d…` ≠ S24's recorded `fad7b09d…`, and S24's fold receipts say
`label-blind-quadrants-v2`. Therefore **no earlier HOLDOUT-DTI in this repo (including
S21-PDWC 0.195724 and S24-CCKM 0.075896) is a matched incumbent on today's instrument**. This
session establishes the v3 bar with **matched controls on identical folds, budgets and
emission**; historical numbers are context only and will be labelled as such wherever quoted.

## Inputs (all SHA-pinned, restored and re-hashed this session)

- `training_features` 19-band stack (`4371c82e…`, `data/bridge/gems-geodawn-numerical-features.tif`).
  Band identities are claims from embedded descriptions, checked label-blind before features:
  B19 vs |∇B12|, B03 vs |∇B14|, B05 vs |∇B13|, B18 vs ∂xB13 correlations on 2-px-eroded valid
  pixels (S24 pattern). Results recorded; a failed identity is reported, not silently repaired.
- `existing_faults` catalogue (`7ba308cc…`) and `sample_submission` grid/footprint (`2176d08e…`).
- Registry references frozen **before** candidate construction: the 62/64 restorable frozen
  inventory rasters (2 known-missing recorded), the nine focus leaders by the SHAs in
  `docs/s22/nine-site-audit.json` (re-fetched by git blob and re-hashed 2026-10-28), and every
  pre-existing `docs/downloads/*.tif`.
- Declared NoData `-3.4028234663852886e+38` (and any |value| ≥ 1e30 or non-finite cell) is
  **excluded, never read as a value**: all filtering is masked normalised convolution; features
  are `NaN` outside their eroded support (the learner handles `NaN` natively); no filled value
  can influence a retained feature because every support is eroded beyond that feature's maximum
  influence radius.

## Frozen feature construction (`src/gems91/fabric25.py`)

- **Base context (23):** the 19 raw bands (sentinel→NaN) + masked gradient magnitudes of
  B02/B12/B13/B14 (masked σ=2 px smoothing; support = valid eroded 3 px).
- **OGC — oriented granulometry contrast (8):** on detrended elevation B12 (masked σ=1.5 px
  smoothing `E`): grey openings of `E` with linear structuring elements of length 5 and 11 px at
  0°/45°/90°/135°; oriented top-hat residuals `R = E − open(E)`; local energies = masked 15-px
  mean of `|R|`. Features: per-scale max-over-orientation energy (2), anisotropy
  `(max−min)/(max+min)` per scale (2), scale ratio of max energies (1), coarse-energy on B19
  slope at length 11 max-over-orientation (1), and **across-break contrasts**: the length-11
  max-energy map and the anisotropy map sampled ±7 px along the local ∇(slope) unit normal,
  absolute differences (2). Morphology input may use masked-mean fill; OGC support = valid
  eroded 20 px (opening 5 + mean 7 + offset 7 + gradient 1), so filled cells cannot touch any
  retained value.
- **CSPL — cross-spectral phase lag (6):** high-pass residuals of B13 and B14 (masked σ=6 px
  background removed). Tiles 64×64 px, stride 32 px, Hann window; per tile, phase-correlation
  peak between the two residual fields → integer lag `(dy, dx)` ∈ [−8, 8]² and coherence =
  peak / median correlation surface. Tile estimates accumulated to the grid weighted by
  coherence, then masked σ=8 px smoothing. Features: `lag_dy, lag_dx, |lag|, coherence,
  |lag|·coherence`, and across-normal contrast of `|lag|·coherence` sampled ±7 px along the
  ∇B13 normal (1). Support: tiles with ≥80% jointly valid pixels; grid support eroded 10 px.
- **Standalone new-physics surface (control):** `sqrt(rank(ogc_contrast) · rank(cspl_|lag|·coh))`
  on joint support, ranks over support only, in [0,1].

## Frozen learner, folds, emission

- Learner: `HistGradientBoostingClassifier(max_iter=300, learning_rate=0.06,
  max_leaf_nodes=63, min_samples_leaf=40, l2_regularization=1.0, early_stopping=False,
  random_state=520810)`. No tuning after results.
- Folds: shared `vendor/gems57/spatial.folds(catalogue, footprint, buffer_px=80)` (v3).
  Per fold: positives = catalogue pixels inside `fold['train']` with at least one finite
  feature; negatives = uniform random sample (seed 520810 + fold) of `4 × n_pos` pixels from
  `fold['train'] & ~catalogue`. Predict `fold['region']`. Final model: same recipe on the full
  footprint (positives = all catalogue pixels; negatives 4× from footprint & ~catalogue).
- Emission: shared `gems91.pdwc21.emit_dots_nms`, spacing = collar = 3.05 px, budget
  **37,654** dots (fleet/live emission optimum; S24's paired 20k→37,654 arm gained +0.0299
  HOLDOUT-DTI on an identical surface). Per-fold budgets proportional to quadrant footprint
  area (S24 matched-density protocol).
- Scoring: shared `vendor/gems57/evaluate_holdout.py` (`gems57-pooled-hide-v2` arithmetic:
  α=0.2, β=0.8, 300 m triangular kernel), `pooled_summary`, 1,000 paired spatial-block bootstrap
  draws, seed 520810. Every number labelled HOLDOUT-DTI with evaluator version, split version,
  implementation hashes, withheld-positive count and 95% CI.
- Leakage canary (rule 4): every feature alone per fold (all withheld positives + every 4th
  negative in region & ~visible; NaN pairs dropped). Symmetric AUC > 0.90 for any feature is a
  hard stop. A pass does not prove absence of leakage.
- Uniqueness (rule 1), two phases, three scopes, no exemptions in the data: (a) final-model
  surface full-footprint Spearman |ρ| ≤ 0.90 vs every frozen reference **before final
  placement** — breach stops emission; (b) final dots ≤ 70% within 3 px. Scopes reported
  separately: the **nine focus leaders**, all **competitive references** (≤ 90,000 positive px),
  and the **dense calibration blankets** (the 206,895-dot lattice's 3-px dilation covers all but
  6,649 footprint pixels, so any honest geological raster with ≳22k dots is geometrically forced
  above 70% against it — capacity bound recorded; reported, never deleted or evaded).

## Frozen experiments (max 3; arms are paired within each experiment)

- **E1 — do the new families carry signal alone?** Candidate `fabric_e1_oof_new` (OOF on
  OGC+CSPL only). Controls: `control_oof_base` (OOF on base only), `control_new_surface`
  (standalone, no learner), `control_gravgrad` (rank|∇B13|, continuity with S24).
- **E2 — does fusion beat the best component?** Candidate `fabric_e2_oof_full` (OOF on
  base+OGC+CSPL). Same three controls (identical folds/budgets; control terms reused only if
  bitwise-identical inputs are re-verified, else recomputed).
- **E3 — conditional variance reduction.** Only if E2's candidate beats its best control:
  candidate `fabric_e3_oof_bagged` = mean of 3 full-feature OOF models (seeds 520810/520811/
  520812, negative resampling per seed). Same controls. If E2 does not beat its best control,
  E3 is **not** spent.
- **Packaging selection rule (frozen):** package the candidate arm with the highest
  HOLDOUT-DTI among {E1, E2, E3-if-run}; ties → lower experiment number. Packaging = final
  full-footprint model for that arm's feature set → surface check → 37,654-dot emission →
  dot checks → shared writer + independent re-read validation.
- **Verdict `promote` requires ALL of:** canary pass; surface pass vs every frozen reference;
  final-dot pass vs every frozen reference **including dense blankets** (protocol-literal);
  packaged candidate beats the best matched control with paired 95% CI excluding 0; validator
  pass. Anything else is `negative` — a deliverable. `ok_to_submit` mirrors `promote` only;
  competitive-scope uniqueness (nine + ≤90k references) is reported as separate explicit fields
  so the coordinator's policy decision on the blanket scope is fully informed, never assumed.
  Even a `promote` still requires the separate selector/quota check on the authenticated
  submission page before any slot is spent.
- **Post-hoc diagnostics (computed only after the final raster is frozen; never used in
  selection):** blind USGS SGMC off-catalogue DTI (report-only proxy truth) and the repo's LFI
  leaderboard-feedback inversion refitted on the restored anchor set. The LFI output is a
  `MODEL_PROJECTION_NOT_A_SCORE` fitted to USER-REPORTED anchors — it is the "estimated score"
  only in that labelled sense; `organizer_confirmed_score` stays `null` (no receipt exists).
