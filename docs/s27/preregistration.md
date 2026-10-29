# S27-FABRIC-FAR — preregistration (written before any S27 experimental result)

Date: 2026-10-29. Branch: `arena/4b95209e-gemsdoe91`. Base commit `45a2a43`.
Values: **Maximize P(Win) · Own the Outcome.**

This file was written and hashed **before** S27 features were built, before any
S27 holdout number existed, and before any S27 dot was placed. The runner
(`scripts/run_s27_far.py`) refuses to run if this file's hash changes after the
feature receipt is written.

## Lane status (honest statement)

The supplied prompt says "Your lane is the single method paragraph below" but
contains **no single method paragraph** (re-verified in this checkout;
`registry/experiment_plan.json` records `lane: null`). This is the same gap
recorded by S24/S25/S26 and is logged again as an irregularity (IR-S27-01).
The same prompt instructs: work the previous sessions' next steps first;
generate 3–5 candidate hypotheses, rank them, validate the top one on the
spatially blocked holdout before touching a slot. S25 (`docs/s25/REVIEW.md`,
"Limitations & next steps" item 2 and the merged README banner) explicitly
preregistered the next lane in words:

> "Next lane (preregister first): FABRIC surface + distance-stratified,
> uniqueness-capped emission (collar ≥~10 px arm vs 3.05 px arm; caps ≤65% vs
> bhar/spac/h28ridge/cover91 families), gated on SGMC->500 m + paired holdout,
> with LFI kept strictly post-hoc."

S27 executes exactly that reserved lane. It is a **self-assigned narrow lane**,
not a claimed coordinator assignment. No weekly submission slot is used;
promotion remains a separate selector step (protocol rule 6).

## The single method (this session's lane)

**FABRIC-FAR.** The detector is frozen from S25 without modification:
`src/gems91/fabric25.build_all` (19 raw bands + gradient magnitudes of
B02/B12/B13/B14 + 8 oriented-granulometry features on B12/B19 + 6
cross-spectral phase-lag features on B13/B14 = 37 features), the same HGB
learner (`max_iter=300, learning_rate=0.06, max_leaf_nodes=63,
min_samples_leaf=40, l2_regularization=1.0, early_stopping=False,
random_state=520810`), the same 4× negatives per fold, and the same shared
v3 folds (`vendor/gems57/spatial.folds(buffer_px=80)`).

**Only the emission geometry changes.** S25 measured its own failure mode:
the detector beat its matched control on the holdout
(HOLDOUT-DTI 0.147741 [0.129760, 0.167562], paired +0.022997 over base),
but 45.9% of its dots sat 3–5 px from mapped traces (median 5.831 px) where
masked known pixels make them nearly pure false-positive weight under
DTI = T/(T + 0.2·FP + 0.8·FN), while the best claimed fleet raster (R0,
GEMSDOE32, 0.2778 USER-REPORTED) has median 19.647 px. FABRIC-FAR tests
whether the *same validated surface*, emitted with distance-stratified
quotas and uniqueness caps, keeps the holdout skill while fixing the
catalogue-hugging geography.

The catalogue enters only as training labels inside each fold's training
domain, as the emission collar/distance field, and as the pixel-exact
scoring mask. No catalogue-distance *feature*, no prior submission raster,
no LFI output, and no external raster is used as a model feature. Distance
to the *visible* catalogue is used only at emission time (exactly as the
S25 collar already used it), never to train.

**Named non-fault mimics (inherited from S25, still binding):** unfaulted
dipping lithologic contacts (also produce gravity–magnetic lag),
remanent-magnetization offsets, alluvial-fan lobe boundaries and
shoreline/beach-ridge fabrics, GeoDAWN flight-line levelling seams.
A fault prediction is not evidence of a geothermal vent, permeability,
temperature, or a productive reservoir.

## Ranked candidate hypotheses (3–5, qualitative — not score forecasts)

| Rank | Layers → signature | Why it could catch a catalogue-missing fault (not one already in USGS/INGENIOUS) | How it differs from what this repo already implements | Expected benefit / cost; data gate |
|---|---|---|---|---|
| **1 (this lane)** | **FABRIC surface (B12/B19 oriented granulometry + B13/B14 phase lag + 19-band context) → distance-stratified, uniqueness-capped emission** | Buried/subdued faults under bajada/Lake Lahontan sediment still separate surface fabrics and mis-register density vs magnetization boundaries. The S25 detector already proved paired holdout skill; what failed was *where dots were spent* (45.9% at 3–5 px). Expert-mapped *new* faults by construction were missed by the catalogue mapping; the fleet evidence (S25 dot profile, S20/S22 inversions) is that live truth is concentrated far from mapped traces | S25 emitted the identical surface with a 3.05 px collar and uncapped NMS. S21 used uniqueness caps but on a different (PDWC) surface at 3.05 px. S20 optimized dots directly against the LFI model (circular). No prior lane combines the S25-validated fabric surface with preregistered distance quotas + caps and keeps LFI strictly post-hoc | Highest executable-here / ~1–1.5 h CPU. No new data |
| 2 | B12 detrended elevation + B19 slope → **two-sided topographic scaling-break contrast**: robust local relief-texture scale-break estimated on opposite sides of a candidate cross-strike edge, required to persist over multiple windows | A subdued buried/eroded fault may juxtapose different geomorphic texture (fan vs bedrock scaling) even with no sharp scarp for a mapper to trace | Exact *paired, cross-edge* scale-break contrast not found by code search in `src/gems91/`; Hurst/variogram (hgbr18, svhf19) and granulometry (fabric25) are adjacent one-sided controls, not the paired operator. Mimics: lithologic contacts, fan margins, paleoshorelines, roads | Uncertain / medium CPU. No new data in principle; deferred — would need its own lane and canary |
| 3 | B12 + B02 RTP magnetics + B13 gravity → **edge-tangent vs contour-tangent discordance** (rule-of-Vs inspired interaction) with transverse slope jumps | A steep structure crossing relief can discordantly offset potential-field contours where a subdued trace was never mapped | Proposed in S26 preregistration, never implemented. Existing lanes use edge/coherence *magnitudes*, not the tangent-discordance interaction. Mimics: dikes, dipping contacts. **Caveat from S26:** detrended elevation is not hydraulic head or absolute elevation | Uncertain / medium CPU. No new data; deferred |
| 4 | B12/B19 → **multi-valley drainage-steepening alignment**: slope discontinuities conditioned on valley concavity, requiring aligned responses across adjacent valleys | Repeated channel steepening can retain displaced-drainage evidence after a scarp erodes below mapping visibility | Multi-valley *consistency* requirement differs from single ridge/scarp responses used before. Mimics: lithologic boundaries, fan-lobe switching, culverts/roads | Uncertain-low at 100 m / medium-high cost. Reliable routing needs an actual DEM — weak on competition-grid terrain; deferred |
| 5 | USGS 3DEP 1 m DEM → scarp curvature/openness at metre scale, aggregated to 100 m | Metre-scale scarps invisible at 100 m are the most direct signature of young surface-rupturing faults experts map from lidar | Repo DEM work uses 100 m bands; a derived `lidar_scarp_features_u8` exists but is licence-unchecked in `registry/data_manifest.json` and already exploited by S14/S15 lanes | Highest expected value overall but **not executable in this sandbox**: official bulk hosts (`usgs.gov`, `prd-tnm.s3.amazonaws.com`, `tnmaccess.nationalmap.gov`) are outside the sandbox allowlist (tested S22/S26). Free official source if pursued on an unrestricted machine: USGS 3DEP, https://www.usgs.gov/3d-elevation-program/about-3dep-products-services — tile coverage/licence must be pinned before it is proposed as viable. **Not viable this session** |

Ranking is by expected DTI improvement per implementation cost given what is
already measured: rank 1 fixes a *measured* failure mode of a *validated*
detector; ranks 2–4 are unvalidated new operators; rank 5 is unobtainable here.

## Frozen experiments (budget: 2 holdout experiments + 1 packaging step ≤ 3)

All arms share one OOF surface (`fabric_e2_oof_full` recipe retrained
identically), identical v3 folds, identical per-fold budgets
(`allocate(37654, region areas)` as in S25), identical spacing 3.05 px, and
the shared evaluator (`vendor/gems57/evaluate_holdout.py`, pooled DTI,
α=0.2, β=0.8, 300 m triangular kernel). Only emission differs.

- **CTRL arm (matched incumbent, included in every experiment):**
  `emit_dots_nms(surface, visible, region, collar_px=3.05)` — the exact S25
  emission. This is "the current holdout best" on today's instrument
  (S25: HOLDOUT-DTI 0.147741). Reproduction is expected within numerical
  tolerance; any drift is reported, not hidden.
- **E1 — collar ablation:** `emit_dots_nms(..., collar_px=10.0)`.
  Tests S25's "collar ≥~10 px" arm in isolation.
- **E2 — candidate arm (FABRIC-FAR stratified):** global greedy by surface
  descending, spacing 3.05 px, collar 3.05 px, with per-distance-band quotas
  on distance-to-visible-catalogue (px): bands `(3.05,5], (5,10], (10,20],
  (20,40], (40,∞)` with preregistered round shares **5% / 15% / 25% / 25% /
  30%** of each fold budget. A candidate is accepted only if its band quota
  is unfilled and spacing allows; unfilled quota (band exhausted) is
  redistributed in a second pass by global surface order. Actual shares are
  recorded. Rationale frozen here: staff clarify new faults *can* lie within
  300 m of known traces, so the near bands are reduced but not zeroed; the
  majority is pushed far because catalogue-*missing* faults are the target.
  These are round a-priori shares, **not** R0's histogram copied
  (R0: 9.2/15.2/20.6/22.3/26.9 plus 5.8% at ≤3 px) and **not** fitted to LFI.
- **Packaging (not a scored experiment):** the E2 stratified rule is applied
  to the final full-footprint surface with preregistered uniqueness caps
  (below). E1 is an ablation only and is never packaged, whatever it scores.

## Frozen uniqueness caps for final emission (declared before placement)

Cap = at most `floor(0.65 × 37654) = 24475` final dots within 3 px of any
one cap reference. Cap references are frozen from *prior-session* receipts
only (legitimate pre-registration input, not tuned on S27 output):

1. All nine focus leaders (paths + SHAs in `docs/s22/nine-site-audit.json`).
2. Every *competitive* (≤90,000 positive px) reference whose S25 overlap
   exceeded 0.65 in `docs/s25/final-dot-checks.json` — the 16 paths heading
   that table (bhar-e3, spac-e3, calib_h28ridge, cover91-e1, fuse91-e1,
   spid-e3, ccr91-e1, mhtr-e2, s14-lsrg-e3, olc91-e1, s14-hvdc-e2,
   denovo-hgbctx, s17-cdsc-e1, cwp91-e1, s14-ptac-e2, ddvtc-e1).
3. The S25 candidate itself (`docs/downloads/gems91-s25-fabric-e2-...tif`).

Caps are enforced *during* greedy placement (a candidate that would breach
any cap is skipped). After placement, the final dots are checked against
**all** frozen registry references in three reported scopes, exactly as S25:
(nine leaders) / (competitive ≤90,000 px) / (all including dense blankets).
The lattice capacity bound (`src/gems91/capacity.py`) is reported; dots are
**never** steered into lattice holes to evade it (S26 rule).

## Frozen gates (automated; no human inspection anywhere)

- **G1 Leakage canary (protocol rule 4):** every rebuilt feature alone,
  per fold, symmetric AUC ≤ 0.90 on withheld positives. Fail ⇒ stop, no TIF.
- **G2 Surface duplicate (protocol rule 1, phase 1):** final full-footprint
  surface rank-correlation |ρ| ≤ 0.90 vs every frozen reference, checked
  **before** placement. Fail ⇒ stop before placement, log duplicate.
- **G3 Dot duplicate (protocol rule 1, phase 2):** final dots ≤ 70% within
  3 px of any one reference in the nine-leader scope **and** in the
  competitive ≤90,000 px scope. The all-including-blankets scope is reported
  separately with its capacity bound; it is geometrically impossible at this
  budget (S25/S26 evidence) and is flagged for coordinator policy, never
  silently exempted and never evaded.
- **G4 Holdout (protocol: do not spend a slot on an idea that has not beaten
  the current holdout best):** E2 stratified arm beats CTRL arm on pooled
  HOLDOUT-DTI with paired 95% CI lower bound > 0 (same folds, same budgets,
  same evaluator version, withheld count reported).
- **G5 SGMC diagnostic gate:** final candidate's SGMC off-catalogue DTI at
  `min_cat_dist_px=5` (500 m; shared `score_off_catalogue_sgmc`) exceeds
  R0's at the identical parameter. Report-only proxy truth; labelled as such.
- **G6 Format:** shared writer + independent re-read: single band float32,
  EPSG:32611, 3730×3292, transform match, all-finite, values in [0,1]
  (the user's reported "Predicted values must be in range [0, 1]" portal
  error is prevented by construction: binary {0.0, 1.0} on all-finite
  zeros, no nodata tag, no sentinel), 0 dots on catalogue,
  0 positives outside footprint.

**Verdict rule:** `promote` (i.e. "present to selector as slot-worthy")
requires G1+G2+G3+G4+G5+G6 all PASS. Anything else is `negative` with
**OK TO SUBMIT: NO**. A research TIF is still generated and downloadable
whenever G1+G2+G6 pass (negative results are deliverables), clearly marked
research-only. Slot selection itself is never made here (rule 6).

## Score estimation policy (protocol rule 3)

- `ORGANIZER-CONFIRMED`: none exists for any file in this repo; null until a
  submission-page receipt is recorded. Never inferred.
- `HOLDOUT-DTI`: labelled with evaluator version, withheld count, 95% CI.
  Never converted into a leaderboard number.
- Leaderboard **estimate** for the executive table: the LFI model
  (`src/gems91/lfi.py`, refitted this session via `scripts/run_lfi.py` on
  the restored 108-anchor USER-REPORTED set, anchor-set hash recorded),
  applied **post-hoc only**, after the candidate raster is frozen. Reported
  as `MODEL_PROJECTION_NOT_A_SCORE` with the fit's LOSO RMSE/Spearman.
  The candidate is not built, selected, or tuned with LFI; E1/E2/CTRL and
  the packaging rule above were frozen without it. Public→private transfer
  is untested; a projection is never written as a score.

## Inputs (all SHA-pinned; restored and re-hashed this session)

- 15/15 manifest inputs (`scripts/restore_data.py`): training features
  `4371c82e…`, existing faults `7ba308cc…`, sample submission `2176d08e…`,
  R0 zeros `c55bafc4…`, SGMC control `643cbe99…`, ancestors, externals
  (externals are restored for hash completeness only; the licence-unchecked
  lidar/radiometric stacks are **not used** by this lane).
- Registry frozen before candidate construction: 62/64 comparison-inventory
  references (2 known-missing retracted files recorded), nine leaders by
  pinned blob SHAs, every pre-existing `docs/downloads/*.tif`, 108 LFI
  anchors (diagnostics only). Organizer-complete registry: **false**
  (private/team submissions are not observable).
- Official facts re-verified 2026-10-29: problem/metric/format at
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  (DTI α=0.2 β=0.8, triangular R=300 m, EPSG:32611 100 m float32 [0,1],
  single selected submission across both prize rounds) and public
  leaderboard #1 = 0.4544, #2 = 0.3916 at
  https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
  (public observation, not a receipt for any file here). The prompt's
  0.4413 / 0.3195 are stale (IR-S26-01, re-confirmed).

## Falsification

This lane is falsified if E2 does not beat CTRL on G4, or its SGMC->500 m
does not beat R0 on G5, or G3 fails in the competitive scope — in which case
the verdict is negative, no slot is recommended, and the receipts stand as
the deliverable. If a future organizer receipt for this exact SHA-256 ever
lands below 0.2778, the LFI projection was wrong; record it in
`registry/lfi_live_anchors.csv` and retire the lane.
