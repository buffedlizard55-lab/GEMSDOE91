# ASC91 — preregistered lane: antisymmetric cross-fault step concordance

**Session:** 2026-10-24, branch `arena/5486e004-gemsdoe91`. Written **before** any
ASC91 holdout number was computed. Budget: at most 3 experiments (E1–E3 below).
Every number produced by this lane is labelled **HOLDOUT-DTI** (evaluator,
withheld positives, 95% CI), **MODEL**, **RECEIPT** (re-read from disk) or
**CLAIM** (fleet-reported, no receipt in this repo). No number here is an
organiser-confirmed score for a file from this session.

## 0. Why did `h33-h33-2-b2…-zeros` (0.2778 CLAIM) lead the fleet, and can it be beaten?

Verified in this repo from the pinned rasters (`docs/DENOVO_20261024.md` §2,
`evidence/forensics_r0_20261024.json`; hashes in `registry/data_manifest.json`):
R0 (37,654 dots) is a strict dot subset of solo-d2.8 (40,199) and dotted-h19-5
(44,090). Under the official DTI (α=0.2, β=0.8, 300 m triangular kernel,
per-truth-pixel **max** credit — DrivenData #306 problem page
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>):

1. **Sparsification** of a solid 121 kpx surface to dots ≥ 2.828 px apart
   removed mass that paid `0.2·FPw` without raising the capped `TPw` (the
   largest rung, +0.068 CLAIM ladder).
2. **Catalogue-collar deletion** (>2 px, later lanes >3 px) removed dots that
   can earn ~0 hidden credit because mapped-fault pixels are masked in scoring.
3. The underlying **h19-5 ranking surface** was simply the fleet's best
   detector. Its implied weighted recall is only ≈ 37 % (MODEL, DENOVO §2), so
   rearrangements of the same dots are capped near ~ +0.01–0.025; the public
   leader (0.4413 CLAIM-in-brief / leaderboard read in DENOVO §2) implies
   ≈ 1.65× R0's per-dot credit, which requires a better **detector**, not a
   better emission of the h19 field.

Conclusion (PhD-level judgement, labelled MODEL): beating 0.2778 materially
requires extracting fault signal the fleet's ridge/crest machinery cannot see.
This lane targets exactly one such blind spot (below). Whether it beats
0.2778 on the hidden set is unknown until an organiser receipt exists; the
gate used here is the repo's spatially-blocked holdout best.

## 1. Five candidate hypotheses not yet tried in this repo (ranked)

Searched `src/`, `scripts/`, `docs/*.md` on 2026-10-24 for step/matched-filter,
phase-congruency/monogenic, texture/coherence-length, drainage-deflection and
1 m-DEM supervised lanes. Existing lanes: R0 dot edits (prune/spacing/collar/
concentration/snap/relief/trackb/strain), TRI3 ridge concordance, SUP logreg,
HGB-CTX (raw percentiles + symmetric 11×11 means), DD-VTC (Verduzco tilt +
openness + PU + submodular), CED (mag–grav edge-centroid displacement),
basement-step ridge (S10, failed its control).

| # | hypothesis | layers / physical signature | why it should catch a *missing* fault | differs from this repo | expected Δ vs holdout best (MODEL) / cost |
|---|---|---|---|---|---|
| 1 | **ASC91 — antisymmetric (odd-symmetric) cross-fault step matched filter with cross-physics azimuth + polarity concordance** (this lane, E1–E3) | Sponsor bands 12 `det_elev`, 13 `iso_grav_anom`, 2 `rtp`, 15 `depth_to_base_surf`, 17 `cond_surf`. A fault is a **step**: field level differs across the trace. Response = along-strike-smoothed difference of across-strike strip means at ±2/±4 px, 8 strike azimuths. | A buried normal fault with no scarp/ridge crest still offsets elevation, basement depth, density and magnetisation across its trace. Symmetric means (HGB-CTX contexts) and ridge/crest filters (TRI3, worms, tilt HD) mathematically cancel or ignore a pure step. | No lane here uses an odd-symmetric across-strike difference, signed cross-field polarity (footwall: elev ↑, basement depth ↓, gravity ↑, conductivity ↓), or modal-azimuth agreement across 5 fields. CED uses edge-centroid *displacement between mag/grav*, not a step in each field. | Highest / medium |
| 2 | Phase congruency / monogenic local energy (log-Gabor) on `rtp`, `iso_grav_anom`, `det_elev` | Contrast-invariant step+line energy; orientation from monogenic phase | Deep basement faults have low amplitude but preserved phase structure; amplitude-based ridges rank them below shallow noise | No frequency-domain phase method in repo | Medium-high / high (FFT filter bank, 3.8 GiB RAM) |
| 3 | Magnetic texture destruction: local anisotropy / coherence-length of `tmi_vg`/`rtp` (structure-tensor eigenvalue ratio + local autocorrelation length) | Fault-zone fracturing/alteration shortens magnetic coherence along the damage zone | A wide, altered fault zone can lack a single offset edge but still decorrelates the magnetic fabric | DD-VTC uses topo coherence only; no magnetic texture statistic | Medium / medium |
| 4 | Drainage-deflection + channel-steepness (χ) discontinuities routed on band 12 | Stream deflections/knickpoints align along active traces crossing piedmonts | Young faults offset drainages even where the scarp is buried | Not in this repo (fleet χ lanes elsewhere scored ≤0.05 CLAIM); 100 m detrended DEM likely too coarse | Low / medium-high |
| 5 | 1 m DEM scarp detector as supervised features | USGS 3DEP 1 m DEM (free, official, public domain; The National Map <https://www.usgs.gov/the-national-map-data-delivery>), reached via the competition's `1m_DEM_links.csv` | Expert-mapped hidden faults are primarily geomorphic scarps invisible at 100 m | Fleet lidar lanes emitted scarps standalone, never as supervised features with spaced off-catalogue emission | Highest ceiling / **BLOCKED HERE**: sandbox egress allows only github/pypi/npm hosts, so USGS/DrivenData download is not obtainable in-session; the pinned derived lidar copy's provenance is unverified (DENOVO IR-91-40). **Not viable this session** — documented, not proposed. |

Non-fault mimics (named): ASC91 — lithologic/intrusive contacts and Lake
Lahontan shoreline terraces are also cross-line steps (polarity + multi-physics
azimuth agreement are the mitigations; a volcanic margin can still pass all
five fields). Phase congruency — survey flight-line seams. Texture — young
volcanic flows. Drainage — lithology-controlled knickpoints. 1 m DEM —
shorelines, roads, terraces, landslide headscarps.

## 2. Frozen ASC91 method (single lane)

Inputs: only the pinned sponsor stack (`training_features`, sha256 in
`registry/data_manifest.json`; bands verified from file tags 2026-10-24),
`existing_faults.tif` (exclusion + holdout labels only) and
`sample_submission.tif` (footprint/grid). No previous submission raster is
read as a feature. Sentinel fill: nearest-valid EDT inside the footprint
(same pattern as `gems91.dd_vtc_pu._clean_band_edt`).

Step response per field F ∈ {12, 13, 2, 15, 17}, strike azimuth
θ ∈ {0°, 22.5°, …, 157.5°} (unit strike **s**, across-strike **n**):

```
S_F(θ) = strike_smooth[ (F(+2n)+F(+4n))/2 − (F(−2n)+F(−4n))/2 ]
strike_smooth: mean of samples at offsets −4,−2,0,+2,+4 px along s
(all sampling bilinear, scipy.ndimage.shift order=1)
```

Per-field features: footprint percentile of max_θ |S_F(θ)| (`stepabs`),
percentile of directional anisotropy max_θ|S| − median_θ|S| (`aniso`), and the
signed step at the cross-field modal azimuth oriented so the `det_elev` step
is positive (`signed`, robust-z clipped ±6). Cross-field: modal azimuth over
the 5 per-field argmax maps, `az_agree` = fraction of fields within one
22.5° bin of the mode, axial azimuth encoding (sin 2θ, cos 2θ). Total 18
features. No distance-to-catalogue feature anywhere.

### Experiments (all: identical emission — greedy spaced dots, 2.8 px,
### 37,654-dot total budget, candidates > 3 px from the *visible* catalogue)

- **E1 ASC-U (unsupervised):** surface = (Π_F P_stepabs,F)^(1/5) · (0.75 + 0.25·az_agree).
- **E2 ASC-S (supervised):** HistGradientBoosting (same hyper-parameters as
  the repo's `_train_hgb`: 300 iters, lr 0.06, 63 leaves, min-leaf 40,
  L2 1.0, seed 20261024) on the 18 ASC features only.
- **E3 (branch frozen in advance):** if E2 > E1 pooled, E3 = E2 + TRI3-surface
  percentile as one extra feature (TRI3 reused from `gems91.denovo`, not
  rebuilt). If E1 ≥ E2, E3 = E1 surface × polarity-consistency multiplier
  (0.7 + 0.3·pol), pol = fraction of {depth step < 0, gravity step > 0,
  conductivity step < 0} under the elevation-oriented sign convention.

## 3. Validation protocol (reused, not rebuilt)

Primary instrument = the DENOVO whole-component checkerboard holdout exactly
as implemented in `scripts/build_denovo.py` (`fold_setup`: 8-connected
catalogue components assigned whole to 4 folds by centroid in 400 px blocks;
per-fold >3 px exclusion derived from visible components only; supervised
training outside the fold region only, positives = visible catalogue,
negatives = 3× sampled >5 px from visible, seed 20261024+7 stream) scored by
`scripts/dti.py` (official max-per-truth-pixel DTI, α 0.2, β 0.8, R 3 px),
pooled over folds with per-fold values and a t-based 95 % CI on the fold mean
(`mean_ci` reused). Withheld positives must reproduce 60,988
(15,105/15,978/12,874/17,031) — the identical-instrument receipt that makes
HGB-CTX's 0.142885 HOLDOUT-DTI (`evidence/holdout3_hgbctx_20261024.json`) the
comparable prior best to beat. Known instrument property (kept for
comparability, flagged not silently fixed): components are assigned by
centroid, so a withheld component may extend outside its fold region; those
pixels still count in pooled G for every method scored on this instrument.

Known incomparable numbers: CED 0.06215 (vendor `gems57-pooled-hide-v2`),
DD-VTC 0.174030 (`gems91-hide-recover-v1.0`, 38,400-dot submodular emission) —
different folds/budgets; reported for context, never subtracted from ASC91.

Leakage canary (protocol §4): every ASC feature alone, symmetric AUC of
withheld-component pixels vs sampled negatives (>5 px off visible catalogue),
must be ≤ 0.90 before any E1–E3 number is trusted.

Novelty gates (protocol §1), checked on the winning surface *before* placement
and on final dots, against every raster in `data/registry/` plus the three
on-disk `docs/downloads/*.tif` lanes (CED, DD-VTC, DENOVO): sampled Spearman
|ρ| ≤ 0.90 and ≤ 70 % of our dots within 3 px of any single registry raster's
positive pixels. The near-universal lattice raster that blocked CED
(`calib_r13lattice_00904.tif`, 99.87 % footprint coverage within 3 px;
`docs/parent-forensics.json`) is **not** in this restored registry; if it
were, the literal rule would reject any footprint-filling candidate — flagged
as an instrument property in the run card, no exemption silently applied:
the registry actually checked is enumerated file-by-file in the evidence.

Promotion gate: build a submission file only from the E-winner, and mark it
**OK TO SUBMIT** only if pooled HOLDOUT-DTI beats 0.142885 on the identical
instrument **and** both novelty gates pass **and** the independent validator
passes on the written bytes. Otherwise the site says **NOT OK TO SUBMIT**.
Spending a weekly slot remains a separate selector step either way.
