# S16-PC91 — preregistered lane: Kovesi phase congruency (monogenic local energy)

> Merge note (2026-10-25): filed as `HYPOTHESES_S16PC.md` after a parallel session (`S16-PGRD`, arena/400a3f1a) took the canonical `HYPOTHESES_S16.md` name on main. Content unchanged from preregistration except the timestamped E3 amendment below.

**Session:** 2026-10-25, branch `arena/3b49ef79-gemsdoe91`. Written **before** any
S16 holdout number was computed. Budget: at most 3 experiments (E1–E3 below).
Every number is labelled **HOLDOUT-DTI** (evaluator version, withheld positives,
95% CI), **MEASURED** (re-read from disk this session), **LEADERBOARD-READ**
(fetched 2026-10-25), **USER-REPORTED CLAIM** (from the brief; no receipt in this
repo) or **MODEL** (reasoning/projection — never a score).

## 0. Why did `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` lead the fleet, and can it be beaten?

**Verification status first (no hallucinations):** the brief's `0.2778` for this
file is a **USER-REPORTED CLAIM**. No DrivenData receipt exists in this repo
(`IRREGULARITIES.md` IR-91-S10-05), and the file does not appear in the public
top-50. The official public leaderboard fetched today (**LEADERBOARD-READ**,
<https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/>)
reads #1 = 0.4413, #2 = 0.3916, #3 = 0.3904. So "highest" means *highest among
the GEMSDOE fleet sites listed in the brief*, not highest in the competition.

**Measured geometry of R0** (this session, `scripts/forensics_s16.py` →
`evidence/s16_forensics.json`; pinned sha256 `c55bafc4…` zeros twin):
37,654 unit-mass binary dots (single positive value 1.0), 0 dots on the
catalogue, nearest-neighbour spacing min/med = 2.828/3.0 px, distance to
catalogue p0/p5/p50/p95 = 2.236/3.0/19.6/81.9 px, 3-px dilation coverage =
15.09% of the 5,167,373-px footprint. R0 is a strict dot subset of solo-d2.8
(40,199 dots) and dotted-h19-5 (44,090 dots) per ASC91 §0 (registry-verified
2026-10-24).

**Mechanism (MODEL, grounded in the official metric).** The official metric
(verified today against the problem page
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>:
α=0.2, β=0.8, R=300 m triangular kernel, per-truth-pixel **max** credit) is
algebraically identical to this repo's `scripts/dti.py`
(`T/(0.2T + 0.2(S−M) + 0.8|G|)`; TPw=T, FPw=S−M, FNw=|G|−T). Three consequences:

1. **Max-credit saturation → sparsification wins.** A truth pixel can earn at
   most 1.0 no matter how many predicted pixels surround it, while every extra
   unit of predicted mass pays 0.2·(1−k) in the denominator. Thinning a solid
   ~121k-px surface to dots ≥2.828 px apart deletes mass that paid penalty
   without raising credit. Fleet ladder (USER-REPORTED): continuous h19-5
   0.1922 → dotted d1.5 0.2477 → d2.8 0.2600 → solo-d2.8 0.2708 → R0 0.2778.
2. **Catalogue-collar deletion.** Test truth is expert-mapped faults *not* in
   the USGS catalogue (official problem page), and catalogue pixels themselves
   earn no hidden credit; dots there are pure penalty. R0's lineage pruned the
   ≤2 px collar (measured min distance 2.236 px).
3. **The h19-5 detector surface was the fleet's best ranking.** All top fleet
   files (0.2449–0.2778) are emissions/rearrangements of that one surface;
   rearrangements differ by ≤0.033 while the public leader (0.4413) implies
   ~1.65× R0's weighted recall at comparable mass (MODEL arithmetic in ASC91
   §0). Emission geometry is therefore nearly exhausted; only a better
   *detector* — signal the amplitude/ridge machinery cannot see — can move
   materially past 0.2778.

**Can we generate a submission scoring higher than 0.2778?** Honest answer:
unknown until an organizer receipt exists. The only legitimate in-repo gate is
the spatially-blocked hide-and-recover holdout. Comparable best today:
S14-HVDC **0.262209 HOLDOUT-DTI** (`gems91-hide-recover-v1.0`, 60,988 withheld,
95% CI [0.248940, 0.275209]) — but S14-HVDC is a Rule-1 duplicate stop (final
dots 84.7% within 3 px of S13-PTHA). This lane therefore must (a) use a
mechanistically new detector, (b) beat 0.262209 on the *same* evaluator to be
promoted, and (c) pass Rule 1 vs every registry raster. If it does not, the
deliverable is a labelled negative — per protocol Rule 5 that is a valid
result, and the file will be marked **DO NOT SUBMIT**.

## 1. Five candidate hypotheses not yet tried in this repo (ranked)

Novelty verified 2026-10-25 by grep over `src/`, `scripts/`, `docs/HYPOTHESES*.md`
for: phase-congruency/monogenic/log-Gabor (proposed in ASC91 §1 #2, **never
implemented**), pseudogravity/Poisson (absent), Euler deconvolution (absent in
repo; fleet-only), drainage-χ (absent), texture coherence-length (**implemented**
— MTD91, excluded), basement curvature (**implemented** — BHAR-S12, excluded),
demagnetization (**implemented** — S12-SPAC, excluded).

| # | hypothesis | layers / physical signature | why it should catch a *missing* fault | differs from this repo | expected ΔDTI (MODEL) / cost |
|---|---|---|---|---|---|
| 1 | **PC91 — Kovesi phase congruency via monogenic signal (log-Gabor radial × Riesz) on B02 `rtp`, B13 `iso_grav_anom`, B12 `det_elev`** (this lane) | Contrast-invariant step+line energy: Fourier components align in phase at a fault offset regardless of amplitude; orientation/coherence from Riesz odd components. 4 wavelengths (3/6/12/24 px). | A deeply buried basement fault under basin fill has *low gradient amplitude* but preserved multi-scale phase alignment. Every fleet detector (tilt, HG maxima, Frangi, worms, ASC step filter) is amplitude-scaled, so such faults rank below shallow high-amplitude noise. PC normalizes amplitude away. | No frequency-domain phase method exists in repo code (`grep -ri "gabor\|congruency\|monogenic" src/ scripts/` = 0 implementation hits). | Medium-high / medium (FFT bank, ~40 transforms of 3730×3292) |
| 2 | Pseudogravity misfit (Poisson relation) | FFT pseudogravity of B02 vs observed B13; misfit corridors = density/magnetization decoupling (alteration, non-magnetic offsets) | Faults that offset basement without magnetized contrast are invisible to mag-only and grav-only edges but break the Poisson proportionality | Absent (`grep pseudogravity` = 0) | Medium / low-medium |
| 3 | Euler deconvolution source clustering | B14/B02 + FFT derivatives; clustered solutions at structural index 0–1 trace contacts/faults with depth | Adds explicit depth+geometry inversion vs edge filters | Absent in repo; fleet Euler lanes USER-REPORTED 0.0355–0.0984 (weak standalone) | Low-medium / medium |
| 4 | Drainage-deflection + channel-steepness (χ) on B12 | Flow routing on 100 m detrended DEM; knickpoint/deflection alignment | Young faults offset drainages where scarp is buried | Absent in repo; fleet χ USER-REPORTED ≤0.05; 100 m DEM likely too coarse | Low / medium-high |
| 5 | 1 m DEM supervised scarp features | USGS 3DEP 1 m DEM via competition `1m_DEM_links.csv` (free, official: <https://www.usgs.gov/the-national-map-data-delivery>) | Expert hidden faults are primarily geomorphic scarps invisible at 100 m | Fleet lidar lanes emitted scarps standalone | Highest ceiling / **BLOCKED HERE**: sandbox egress = github/pypi/npm only; USGS/DrivenData unreachable from bash. Pinned derived `lidar_scarp_features_u8.tif` exists but provenance unverified. Not viable this session — documented, not proposed. |

**Named non-fault mimics:** PC91 — GeoDAWN flight-line seams and survey
gridding artifacts (phase-coherent straight lines at flight azimuth);
pseudogravity — remanent magnetization reversals; Euler — isolated volcanic
plugs; χ — lithologic knickpoints; 1 m DEM — Lahontan shorelines/roads.

## 2. Frozen PC91 method (single lane)

Inputs: only pinned sponsor stack `training_features` (sha256 `4371c82e…`,
bands verified from file tags this session: B02 rtp, B12 det_elev, B13
iso_grav_anom; E2 adds all-19 raw robust-z), `existing_faults.tif`
(sha256 `7ba308cc…`; labels/exclusion only), `sample_submission.tif`
(sha256 `2176d08e…`; footprint/grid). No previous submission raster is a
feature. Sentinel −3.4028235e+38 → nearest-valid EDT fill inside footprint
(shared `gems91.dd_vtc_pu._clean_band_edt`).

Per field F ∈ {B02, B12, B13}, scales λ ∈ {3, 6, 12, 24} px:
log-Gabor radial bandpass `G(r)=exp(−ln²(r/r0)/(2 ln²0.55))`, Riesz pair
`(−i·kr/|k|, −i·kc/|k|)` → monogenic triple (even e, odd (o_r, o_c));
local amplitude `A=√(e²+|o|²)`, local phase `φ=atan2(|o|, e)`.
Phase congruency `PC = Σ_s A_s·max(cos(φ_s−φ̄)−0.0,0)·Δφ_s / (Σ_s A_s + ε)`
with `Δφ` the phase-deviation weighting `sin(|φ_s−φ̄|)` complement
(Kovesi monogenic formulation), implemented in `src/gems91/pc91.py` and
unit-tested on a synthetic contrast-varied step (PC invariant to step
amplitude/sign) before any real-data use.

Features per field: `pc`, `energy=Σ_s A_s` (robust-scaled), orientation
coherence `|Σ_s o_s|/Σ_s|o_s|` (3-px smoothed), odd-vector strike components
`cos2ψ, sin2ψ`. Cross-field: `pc_min3`, `pc_geomean3`, pairwise strike
agreement `cos2(ψ_a−ψ_b)` weighted by PC. E1 = PC features only;
E2 = E1 + 19 raw-band robust-z; E3 = winner emission sweep
{30,000 / 37,654 / 44,000 dots}.

Training/emission reuse shared tools only (Rule 2):
`dd_vtc_pu.fit_and_predict_oof_fold` (HGB+LR, visible-fault positives,
>3.5 px off-collar negatives, buffer/withheld excluded),
`dd_vtc_pu.submodular_dti_emit` (min spacing 2.85 px, >3.0 px catalogue
collar), `evaluate_holdout.build_segment_buffered_folds` +
`score_pooled_holdout` (report **both** v1.0 comparable-to-S14 and
v1.1-nohalo; never mix), `run_leakage_canary` (Rule 4: symmetric AUC ≤ 0.90
per feature), `check_registry_surface_uniqueness` before placement +
`check_registry_uniqueness` on final dots (Rule 1: |ρ| ≤ 0.90, ≤70% dots
within 3 px vs **every** registry raster), blind SGMC off-catalogue control
(report-only), `submission_writer.write_validated_submission_bundle`
(triple gate suites; all-finite zeros twin in [0,1]).

### Amendment (2026-10-25, after E1/E2, before E3 — process stopped pre-write)

Observed: E1 PC-only = **0.123600 HOLDOUT-DTI** (v1.0, CI [0.114867, 0.133738]);
E2 PC+raw19 = **0.137450** (CI [0.124169, 0.151986]) ≈ B0 raw-only 0.138999 —
PC adds no measurable signal over raw bands for catalogue recovery. A ±15%
budget sweep (fleet sensitivity ≈ ±0.01, MODEL) cannot close a 0.125 gap to
0.262209, so the frozen E3 sweep is replaced, within the same 3-experiment
budget, by: **E3 = shared static feature stack (49 cols,
`dd_vtc_pu.build_or_load_static_feature_memmap`, Rule 2 cached stack) + PC91
(24 cols) at fixed 37,654-dot quota**, canaried on all 73 features. This tests
the only remaining lane question — whether PC adds over the repo's engineered
stack — instead of tuning emission on a detector already shown weak. Final
budget is fixed at 37,654 (R0-matched). No candidate file had been written
when this amendment was made (run stopped at the E3 boundary; log
`evidence/s16_run.log`).

Promotion gate (all required): canary pass; surface+dot uniqueness pass;
**v1.0 HOLDOUT-DTI > 0.262209** (S14 comparable best); triple format gates
CERTIFIED. Promotion means "eligible for the separate human selector step
within the weekly cap" (protocol Rule 6) — this session does not submit.
Any failure ⇒ verdict negative, `ok_to_submit=false`.
