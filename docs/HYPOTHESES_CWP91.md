# CWP91 preregistration — completeness-weighted PU (frozen before any CWP91 scoring)

**Session:** `arena/24569eef-gemsdoe91`, lane **CWP91**, date 2026-10-25.
**Protocol compliance:** Parallel-Run Protocol Rules 1–6 (see §4). No CWP91 holdout
score, surface, or dot existed when this file was written. §5 is appended after the
run; nothing above §5 is edited afterwards.

The prompt supplied no single assigned method paragraph (irregularity
**IR-CWP91-01**). This session therefore declares exactly one lane — completeness-
weighted PU — and stays inside it. It is OLC91's pre-ranked H2
(`docs/HYPOTHESES_OLC91.md` §2), which OLC91 never ran, with the hole-shuffled
control that OLC91's remaining-work list required.

---

## 1. Why did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` score 0.2778? (forensic re-measurement)

**Evidence class first.** The value 0.2778 is **USER-REPORTED, unverified**. The
GEMSDOE32 site itself, fetched live by this session on 2026-10-25, states of this
exact file: "projected live DTI 0.2747 (a MODEL, not a score). **NO ORGANISER SCORE
EXISTS** for this or any artifact in this repository." The file the user names
(`h33-h33-2-b2-…-e5eb6e7e-zeros`, sha256 `c55bafc4…`, 37,654 dots) is byte-identical
to the pinned registry copy used below. So "why did it score 0.2778" must be read as
"why does the *reported lineage* 0.1922 → 0.2600 → 0.2708 → 0.2778 behave as it
does". The mechanism below is measured from the rasters, not taken from any site's
prose. Likewise the prompt's "0.3195 is the highest score right now" is **wrong**:
the DrivenData public leaderboard fetched live by this session on 2026-10-25 shows
rank 1 = **0.4413** (xiaofanhu), then 0.3916, 0.3904; 0.3195 would sit around
rank 24. The prompt's other statement "Current competition leaderboard … 0.4413" is
the correct one. The target to beat is **0.4413**, not 0.3195.

**Lineage, re-measured this session from the pinned registry rasters**
(footprint 5,167,373 px; catalogue 60,988 px; grid 3730×3292, 100 m):

| Step | File (pinned) | Positive px | 8-conn components | Median comp. size | Reported live |
|---|---|---:|---:|---:|---:|
| 0 | `calib_h161_01855` (h16-1) | 123,939 | 30,345 | 2 | 0.1855 |
| 1 | `calib_h195_01922` (h19-5) | 121,131 | 26,645 | 2 | 0.1922 |
| 2 | dotted h19-5 d2-8 | 44,090 | 44,090 singletons | 1 | 0.2600 |
| 3 | solo d2-8 | 40,199 | 40,199 | 1 | 0.2708 |
| 4 | **R0 `h33-2-b2` zeros** | **37,654** | 37,654 | 1 | **0.2778** |

Containment is exact and verified pixel-by-pixel: d2-8 ⊂ h19-5 (0 px outside),
solo ⊂ d2-8 (removes exactly 3,891 dots, **all at distance exactly 1.0 px** from the
catalogue), R0 ⊂ solo (removes exactly 2,545 dots, **all at √2–2.0 px**). R0's
nearest-dot spacing: minimum 2.828 px, median 3.0 px (a 2.8 px Poisson-disk thin).
R0's minimum distance to the catalogue is √5 ≈ 2.236 px; its dot distance-to-
catalogue median is 19.6 px, and 70% of its dots lie >1 km (10 px) from any mapped
fault. Lift vs area by distance band: 2.10 at (2,3] px, 1.75 at (3,5], 1.30 at
(5,10], 0.98 at (10,30], 0.88 at (30,100] — i.e. the parent surface is a
**catalogue-blind lineament network spread over the whole footprint**, mildly
enriched near mapped faults but earning its score far from them.

**Mechanism (PhD-level reading).** The metric is a budget, not a detector contest.
With the official definition k(d)=max(1−d/300 m,0), TP_w = Σ_truth max p·k,
FP_w = Σ p·(1−max k), DTI = TP/(TP+0.2·FP+0.8·FN):

1. **Dotting is the dominant gain (+0.068 of the +0.086 total).** A truth pixel is
   credited once, by its best dot (the max-kernel); every additional nearby dot
   still pays ~0.2 in FP. The h19-5 surface spends 121k px in 26.6k fragments —
   most of that mass double-covers ground already credited. Thinning to 44,090
   dots at ≥2.8 px spacing keeps ~most of the 300 m coverage at 36% of the mass.
   This is pure emission geometry: no new geology was added between 0.1922 and
   0.2600.
2. **Collar pruning (+0.0108, then +0.0070).** Known-fault pixels are masked from
   scoring (DrivenData staff, forum 11516). A dot 1–2 px from a mapped trace points
   most of its kernel at masked or empty ground. Inverting each prune step under
   the exact DTI algebra (this session, independently) implies TP_w ∈ [5027, 5121]·φ
   for step 3 and [5393, 5549]·φ for step 4 (φ = unknown public fraction). The
   intervals do not overlap, so the pruned dots were **not** exactly zero-credit —
   their mean marginal credit was simply below the break-even bar k > 0.2·DTI ≈
   0.054. Either way, dots adjacent to the catalogue are the worst mass in the file.
3. **Implied geometry of the hidden truth.** With T≈5.2k·φ and the measured
   n=37,654, the algebra gives weighted coverage T/G ≈ 0.36–0.39 and FP/G ≈ 2.1–2.4.
   To reach the public 0.4413 at the same FP costs coverage ≈ **0.62**; even the
   prompt's 0.3195 needs ≈0.44. No emission trick can do that — emission is
   already near its optimum (thin, collared, budget-matched). **Only a better
   localiser — a surface whose top-ranked pixels have higher credit density — can
   beat 0.2778, and only a much better one can approach 0.4413.**
4. **Where new faults are not.** Live evidence across the fleet (USER-REPORTED):
   pure catalogue-proximity lanes scored *below* the ≈0.052 uniform-random floor
   for 37,654 dots (km-faultzone 0.0106, relay-ramp 0.0053, basement-step 0.0009),
   and dots 1–2 px from the catalogue earned ≈0. The hidden set is therefore
   **depleted near mapped faults**: the catalogue is locally *complete* where it
   exists. A naive hide-and-recover holdout hides components clustered next to
   visible faults (55% of seed-20 withheld truth lies within 1 km of visible
   faults — OLC91 §5) and so *over-rewards proximity and catalogue-context
   features*. Any lane that claims a live gain must either exclude catalogue-context
   features or, as here, model the depletion explicitly and control for the
   artefact it creates.

**Can we generate a submission scoring higher than 0.2778?** Not demonstrably
offline, and nobody can: R0 was built with the full catalogue so it cannot be
scored on any hide-and-recover split, and no offline instrument has a verified
calibration to the live board. What *can* be shown offline, and what this session
tests, is narrower and honest: whether the completeness-weighted transform beats
the identical incumbent recipe on identical folds without exploiting the holdout's
artificial holes. If it does, it is a *candidate* for the separate selector step;
if it does not, it is a negative deliverable. No live number is projected.

---

## 2. Ranked untried hypotheses (5 candidates)

Surveyed against every lane already in this repo (H91/DD-VTC, CED91, DENOVO, ASC91,
BHAR91, CCR91, DRN91, FUSE91, G91/GEO91, MTD91, OLC91, S10–S17 incl. PTAC/SCGF/CDSC/
CGRD/EULR, SPID91, UCD91, XG91, DZEDGE, H1-blind-zone) and the fleet results in the
prompt. "Untried" means: not implemented and scored here before (OLC91-H2 was
*specified* but never run; that is disclosed, not hidden).

| Rank | ID | Layers | Physical signature / transform | Why it should catch a fault *missing* from the catalogue | Difference from anything in this repo | Expected ΔDTI (holdout) | Cost |
|---|---|---|---|---|---|---|---|
| **1** | **H1 CWP** (tested as E1) | PU posterior `p` (19 official bands + gradient magnitudes, OLC91 E0 recipe) + *visible* catalogue only | `s = p·(1−ĉ)`, `ĉ = clip((G_σ∗cat)/(G_σ∗p̂_vis), 0, 1)`, σ=10 px — spatially-varying Elkan–Noto label frequency | PU theory: P(unlabelled positive\|x) ∝ p(x)·(1−c(x)). Where mapping is already dense (ĉ→1) a high `p` is most likely an *already-mapped* fault; where the catalogue is sparser than the geology predicts (ĉ→0) the same `p` is a genuine discovery candidate. Directly encodes the measured live depletion near mapped faults | H91 used an Elkan *exposure* propensity from slope/depth/elevation gated on subsurface support; S15/S17 used *prior-shift calibration* (global prevalence). **No lane has estimated the label frequency as a spatial field from observed-vs-expected catalogue density and used it as the emission surface** | +0.005 to +0.02 if the depletion is real at 1 km scale; sign uncertain offline (see §3 control) | Low (~30 min compute) |
| 2 | H2 pluvial-shoreline mimic suppression | B12 det_elev, B19 det_elev_slope, posterior | Suppress lineaments whose strike is parallel to local elevation contours (structure-tensor strike ∥ contour direction) | Lake Lahontan shoreline terraces are horizontal, contour-parallel scarps — the dominant false "fault scarp" in NW Nevada. Real fault scarps cross contours. Removing contour-parallel mass raises credit density without new data | No repo lane tests the contour-parallel angle. OLC91 listed it as H3 and found the *absolute-datum* version infeasible (B12 is detrended); the *angle-only* version needs no datum and remains viable | Uncertain; small positive if shoreline mass is a large FP share | Medium |
| 3 | H3 Andersonian slip-tendency orientation weighting from the *vector* strain field | External: EarthScope/GAGE GNSS velocities → principal extension azimuth field | Weight posterior by slip tendency of the local lineament strike under the regional extension direction (normal faults strike ⟂ to σ₃ extension) | The 19-band stack carries only *scalar* strain rates (B04/B07/B08), no azimuth. A strike inconsistent with the active stress field is more likely a lithologic contact or artefact | `dd_vtc_pu` weights ridges by a fixed Morris WNW–ESE tendency; no lane uses a spatially-varying measured azimuth field | Uncertain | **High — NOT viable this session:** the free official source (EarthScope/GAGE, https://www.earthscope.org/data/) is not reachable from this sandbox (only github/npm/pypi egress), so obtainability here is unverified. Deferred, not proposed as viable |
| 4 | H4 thermal-inertia / night LST fault-zone moisture lineaments | External: Landsat 8/9 TIRS or ECOSTRESS LST (USGS/NASA, free) | Along-fault shallow groundwater raises thermal inertia; night-time LST lineaments over concealed faults | A genuinely new information source (OLC91's lesson: HGB-on-19-bands converges to the same 15–25% of the footprint). Concealed intrabasin faults with no scarp and weak potential-field expression can still channel groundwater | No repo lane uses any thermal/optical satellite layer | Unknown; potentially the largest if the signal exists | **High — NOT viable this session:** USGS EarthExplorer / LP DAAC egress is blocked from this sandbox; named source is free and official (https://earthexplorer.usgs.gov/, https://www.earthdata.nasa.gov/) but not obtainable here. Deferred |
| 5 | H5 drainage-deflection confluence asymmetry on an external 10 m DEM | External: USGS 3DEP 10 m DEM (free) via the competition's own 1 m/10 m DEM links | Systematic same-sense deflection / knickpoint alignment of drainages crossing a blind fault | Blind faults under alluvium deflect drainages before they build a scarp detectable at 100 m | DRN91 used drainage ideas on the 100 m stack; no lane has used 10 m topography. (The pinned lidar-scarp stack in `registry/data_manifest.json` is licence-unchecked and was **not** used by prior sessions; it stays unused here.) | Unknown | **High — NOT viable this session:** 3DEP egress blocked here; source is free/official (https://www.usgs.gov/3d-elevation-program) but unverified-obtainable in-sandbox. Deferred |

**Named non-fault mimic for H1 (required):** a *mapping-effort gradient* — e.g. the
edge of a detailed 1:24k quadrangle map or a county/land-ownership boundary where
field mapping simply stopped. There `ĉ` drops because nobody mapped, not because
faults are unmapped-but-present; CWP would promote ordinary lineaments along the
survey boundary. Secondary mimic: young alluvial/playa cover where `p̂_vis` is
itself depressed, making `ĉ` noisy. The hole-shuffled control (§3) bounds the
first-order version of this risk inside the holdout.

---

## 3. Instrument (frozen)

* **Template reuse (Rule 2).** Cached feature stack = the 19 official bands +
  per-band gradient magnitude, built exactly as OLC91's `build_features`
  (EDT sentinel scrub, robust-z). Evaluator `vendor/gems57/evaluate_holdout.py`
  (`gems57-pooled-hide-v2`, pinned sha256 in `registry/template_pin.json`), split
  `vendor/gems57/holdout.buffered_component_draw(seed=20, hide_frac=0.20,
  buffer_px=3, boundary_px=12)`, writer `vendor/gems57/submission_writer.py`,
  validator `vendor/gems57/validate.py`, emitter
  `gems91.dd_vtc_pu.submodular_dti_emit`. **No private fork of any of these.** The
  only new code is the CWP transform and its controls (`src/gems91/cwp.py`).
* **Holdout = hide-and-recover.** Whole 8-connected fault components withheld with a
  3 px feature-context buffer; every catalogue-based quantity (including `ĉ`) is
  derived **only from visible faults**; visible faults masked pixel-exactly; pooled
  DTI (α 0.2, β 0.8, 300 m triangular kernel), paired 20 km-block bootstrap
  (1,000 draws). Training is leave-one-quadrant-out with a 40 px buffer; hidden
  components stay unlabelled (PU), exactly as OLC91 E0.
* **Arms (identical emission; only the ranking surface differs).** Budget 37,654 ×
  area share per fold; **collar: no dots on or within 2.0 px of any still-known
  catalogue pixel** (R0's natural experiment).
  * **E0** — incumbent recipe (PU-HGB posterior `p`). Comparable best on this
    instrument: 0.085260 HOLDOUT-DTI (OLC91 E0, same seed/recipe).
  * **E1** — CWP candidate: `s = p·(1−ĉ)`, σ = 10 px (1 km), `p̂_vis` = the
    calibration-fold posterior (choice (b) below).
  * **CTL** — hole-shuffled control: identical to E1 except `ĉ` is computed from a
    **rigidly shifted** visible catalogue (fixed offset (+173, −211) px, wrapped
    within the footprint bounding box; shifted catalogue re-masked to the
    footprint). This preserves the catalogue's density field statistics and the
    smoothing, but destroys the alignment between true mapping completeness and
    true hole locations. CTL isolates "any spatially-smooth density reweighting
    helps the holdout" (artefact) from "the *aligned* completeness field helps"
    (science).
  * **RND** — uniform random dots in the same eligible mask (floor).
* **`p̂_vis` choice (frozen).** (b): within each holdout fold, `p̂_vis` is the same
  LOQO model's posterior `p` predicted on the calibration domain = the scored
  region (the model never saw the scored quadrant in training, and hidden
  components are unlabelled, so `p` is uncontaminated by the truth). For the final
  full-map build, `p̂_vis` is an out-of-fold-style posterior: the full-catalogue
  model is trained on all data, but `ĉ` uses 4-fold LOQO stitched predictions so
  that `p̂_vis` at each pixel comes from a model that did not train on that
  quadrant. Both are computed from visible faults only.
* **Experiments (Rule 6: max 3).** Exp 1 = seed 20, arms E0/E1/CTL/RND. Exp 2 =
  seed 21 replication, **only if** E1 passes both promotion conditions on seed 20.
  Exp 3 reserved, unused unless Exp 2 runs and time remains. The CWP file is always
  written (research download); its submit verdict follows the gates, not the wish.
* **Frozen estimator addendum (added before any scoring, same session).** The
  `p̂_vis` in `ĉ = clip((G_σ∗cat)/(G_σ∗p̂_vis), 0, 1)` is the Elkan–Noto calibrated
  fault posterior `p_y = clip(p_s / c_bar, 0, 1)`, where `c_bar` = mean of `p_s`
  over visible-catalogue pixels in the calibration domain (scored region per fold;
  full footprint for the final). Gaussian: σ = 10 px, `truncate=3.0`,
  `mode='constant'`; `ĉ = 0` where the denominator ≤ 1e-6. The emission surface
  is `s = p_s·(1−ĉ)`, ranking-equivalent to `p_y·(1−ĉ)` (global factor `1/c_bar`).
  The more aggressive exact-SCAR form `p_s·(1−ĉ)/ĉ` is **not** used and is not
  tuned in later. Per-fold prediction extends 32 px beyond the scored region so
  the 30 px Gaussian support never sees an unpredicted (zero) posterior inside
  the scored region. Implementation: `src/gems91/cwp.py` (unit-tested in
  `tests/test_cwp91.py`).

## 4. Gates (frozen)

* **Leakage canary (Rule 4).** Every input feature **and** `ĉ` and `(1−ĉ)` alone on
  the holdout (withheld truth vs unlabelled scored pixels); symmetric AUC > 0.90
  ⇒ leakage until proven otherwise, STOP and report. (Expected: `ĉ` is *negatively*
  associated with withheld truth by construction — holes are where truth was
  removed — so its symmetric AUC is reported and interpreted, not hidden. The
  canary threshold still applies as written.)
* **Promotion (both required, paired bootstrap 95% CI lower bound > 0):**
  (i) Δ(E1 − E0) > 0; **and** (ii) Δ(E1 − CTL) > 0. Beating E0 but not CTL = the
  gain is a holdout-hole artefact ⇒ **negative**, however large. Then Exp 2
  (seed 21) must agree in sign on both deltas.
* **Uniqueness (Rule 1).** Checked on the continuous surface **before** placement
  and on the final dots **after**: duplicate-stop if |Spearman ρ| > 0.90 vs any
  registry raster, or > 70% of dots within 3 px of one registry raster's dots.
  Registry = all locally restorable pinned rasters + this repo's prior downloads +
  the frozen 64-row fleet inventory (`registry/comparison_inventory.json`) restored
  via its pinned git blobs. Blanket references (3 px footprint coverage ≥ 0.70)
  are reported literally **and** chance-corrected; no reference is dropped.
  **No exemption is invented:** if the literal rule fires, the verdict is
  duplicate-stop / negative, full stop.
* **Format.** `vendor/gems57` validator must pass on the re-read file: single-band
  float32, EPSG:32611, 3730×3292, transform (100, 0, 243350, 0, −100, 4508550),
  **no NaN anywhere**, values in [0,1], 0 outside footprint, 0 dots on the
  catalogue. This is the fix for the portal error "Predicted values must be in
  range [0, 1]" (raw −3.4028235e38 sentinels / NaN-nodata twins).
* **Labels (Rule 3).** Every number is HOLDOUT-DTI (evaluator version, withheld
  positives, 95% CI) or USER-REPORTED. Nothing is ORGANIZER-CONFIRMED without a
  submission-page receipt; no projection is written as a score.
* **Slots (Rule 6).** This session spends **0** weekly slots and never selects a
  submission. `OK TO SUBMIT: YES` in the run card means only "passes every
  automated gate above; eligible for the separate selector step".

---

## 5. Results (appended after the run; everything above was frozen first)

**Experiment 1 (seed 20): NEGATIVE — both promotion conditions fail.**
HOLDOUT-DTI, `gems57-pooled-hide-v2`, 11,321 withheld positive px, LOQO models,
identical emission for every arm (evidence: `docs/cwp91/holdout-seed20.json`):

| Arm | HOLDOUT-DTI | 95% CI | NW | NE | SW | SE |
|---|---:|---|---:|---:|---:|---:|
| E1 CWP `p·(1−ĉ)` | 0.083170 | [0.066671, 0.100489] | 0.0809 | 0.0993 | 0.0657 | 0.0906 |
| E0 incumbent recipe | 0.085260 | [0.068716, 0.102299] | 0.0814 | 0.1011 | 0.0683 | 0.0936 |
| CTL hole-shuffled | 0.085723 | [0.069190, 0.102954] | 0.0809 | 0.1027 | 0.0679 | 0.0947 |
| RND floor | 0.043165 | [0.037666, 0.048476] | 0.0364 | 0.0422 | 0.0446 | 0.0475 |

Paired Δ(E1−E0) = −0.002090, 95% CI [−0.003218, −0.001158] (E1 lower in 4/4 folds).
Paired Δ(E1−CTL) = −0.002553, 95% CI [−0.004043, −0.001187]. The aligned
completeness field loses significantly to *both* the incumbent recipe and its own
hole-shuffled control, so per the frozen gates: **no promotion, no seed-21
replication** (Experiment 2 not run). E0 re-measured here is numerically identical
to OLC91's E0 on the same instrument (0.085260, per-fold identical), confirming the
recipe/instrument was reproduced exactly and the deltas belong to the transform.

**Leakage canary: PASS (no stop).** Worst single quantity is `cwp_chat` itself,
symmetric AUC 0.7348 < 0.90 (worst input feature `grad_det_elev_slope`, 0.6009).
`ĉ` is *positively* associated with withheld truth — the withheld components sit
inside mapped neighbourhoods at the 1 km smoothing scale — which mechanistically
explains the loss: E1's coverage deficit concentrates in the 4–10 px distance band
(0.1081 vs E0 0.1135) that holds 55% of this instrument's truth, while its >30 px
gain (0.1378 vs 0.1355, n = 748) is negligible. Two readings remain open —
instrument mismatch (hide-and-recover holes are components, not catalogue-scale
gaps) vs a false mechanism — and this offline instrument cannot separate them.
The gate therefore correctly refuses promotion; no live claim is made either way.

**Final file and uniqueness: DUPLICATE-STOP.** `gemsdoe91-cwp91-e1-completenesspu-
37654-20261025-562325b2.tif` (sha256 `a9bcec2a…f659d68`, 37,654 dots, format PASS).
Pre-placement surface: max |ρ| 0.21473 (PASS). Post-placement dots: **90.8% within
3 px of the OLC91-E1 file** (89.5% chance-corrected) across 95 unique registry
rasters — Rule 1 drift, logged as a duplicate, experiments stopped (1 of 3 used,
0 slots spent). Overlap vs the GEMSDOE32 champion R0 is only 36.6%: the file is a
new byte-level artifact genuinely different from the 0.2778 lineage, but it is a
near-duplicate of this repo's own PU-HGB family. Third consecutive confirmation
that transforms of the same 19-band posterior cannot produce a lane-unique file;
the next lane needs a new information source (candidates H3–H5 in §2, each with
its named free official source and sandbox-egress blocker) or the H2
shoreline-angle test, which at least uses a different geometric quantity.
