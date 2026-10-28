# S25-FABRIC session review — 2026-10-28

Branch `arena/6c45b779-gemsdoe91`. Experiments used: **3 of 3** (preregistered).
Weekly submission slots used: **0**. Values: **Maximize P(Win)** — do not spend a
slot on a raster whose live-aligned estimate is low; **Own the Outcome** — the
negative verdict, its receipts and its failure mode are preserved and linked.

## Executive verdict

**A new, unique-vs-the-nine, format-valid TIF was generated. OK TO DOWNLOAD:
YES (research only). OK TO SUBMIT: NO.**

| File to download (research) | Estimated leaderboard score (labelled) | Unique vs GEMSDOE24/25/27/28/30/31/32/33/36? | OK to submit? |
|---|---|---|---|
| [`gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif`](../downloads/gems91-s25-fabric-e2-37654dots-20261028T115403Z-3188f6e6-zeros.tif) (SHA-256 `0046fca5…`) | ORGANIZER-CONFIRMED: none. LFI **MODEL_PROJECTION_NOT_A_SCORE 0.07917** (ridge10 0.08072; LOSO RMSE 0.0196; 112 anchors, set hash in `diagnostics.json`). HOLDOUT-DTI **0.147741 [0.129760, 0.167562]** (`gems57-pooled-hide-v2` arithmetic, `label-blind-quadrants-v3-feature-buffered` folds, 60,988 withheld — not a leaderboard score). SGMC-offcat diagnostic 0.079042 | **YES** — max 40.19% of dots within 3 px of any one leader; surface \|ρ\| max 0.2138. **NO literal** — 74.89% vs closest competitive reference, 98.75% vs the 206,895-dot lattice (capacity-forced ≥82.34% at this budget) | **NO** |

Front door with generated tables: [`executive-summary.html`](executive-summary.html)
(rendered from JSON receipts by `scripts/render_s25_portal.py`; no hand-typed scores).

## What the science showed (the useful part)

- **The new feature physics works on the holdout instrument.** 14 fabric
  features alone (oriented granulometry of B12/B19 + B13/B14 phase lag) reach
  HOLDOUT-DTI 0.116031 vs 0.124744 for the 23-feature base model; fused (E2)
  they add **+0.022997 [+0.014272, +0.031866]** paired over the base model —
  the first lane in several sessions to beat its best matched control with CI
  excluding 0. Leakage canaries: max symmetric AUC 0.6130 (band06 fold3) over
  156 feature-fold tests; best new feature 0.5978. No leakage signal.
- **…and it still would probably score poorly live, for a measured reason.**
  The emitted dots hug the mapped catalogue: median distance 5.831 px, 45.9%
  at 3–5 px (R0: 19.647 px median, 9.2% at 3–5 px). Supervision on catalogue
  labels + a 3.05 px collar ranks just-off-trace halos highest; hide-and-recover
  rewards exactly that, while live truth concentrates far from mapped traces
  (refit LFI θ: dcat 3–5 px = −1.76 vs >40 px = +2.15). Hence LFI projection
  0.07917 vs R0's 0.27342 under the identical refit, while SGMC (which keeps
  many near-catalogue positives) is a kinder 0.079042 vs R0 0.095386.
  Instruments disagree exactly where S22 measured they would
  (hide-v2↔live ρ≈+0.105; SGMC↔live ρ≈+0.44; LFI LOSO ρ≈+0.95 on anchors).
- **Uniqueness is now a two-sided measurement, not a slogan.** Vs the nine
  leaders the candidate is comfortably unique (≤40.19%). Vs competitive
  references it breaches 70% four times (bhar-e3 74.89%, spac-e3 73.40%,
  calib_h28ridge 70.57%, cover91-e1 70.42% — all denser/nearer references),
  because strong learners on one stack converge to similar dot sets. A future
  lane needs uniqueness-capped emission (S21 precedent: ≤64% caps) preregistered
  *before* placement; retrofitting caps after seeing overlaps would be tuning
  against the witness.

## Per focus-site answer (recomputed 2026-10-28)

Claims are **USER-REPORTED, not ORGANIZER-CONFIRMED** (no receipt exists for any
of them). Leaders re-fetched by git blob and re-hashed today; all nine repos
have new main commits since the 2026-10-26 audit (several within this session's
hours — parallel lanes are live; only GEMSDOE25/GEMSDOE33 front doors yielded an
extractable OK-TO-SUBMIT snippet, both NO; see `nine-site-audit.json`).

| Site | Best claimed file | Claim | Unique among the nine? | Submit as new? |
|---|---|---:|---|---|
| GEMSDOE32 | `gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif` (37,654 dots) | 0.2778 | No — 100.00% vs GEMSDOE24 | No |
| GEMSDOE36 | `…anderson-geothermal-pinn-38854…zeros` (38,854) | 0.2750 | No — 97.58% vs GEMSDOE27 | No |
| GEMSDOE28 | `…h36-1-rung30-blind-r1…nan` (37,660) | 0.2710 | No — 100.00% vs GEMSDOE24 | No |
| GEMSDOE31 | `…h27-4-solo-d28…nan` (40,199) | 0.2708 | No — 100.00% vs GEMSDOE24 | No |
| GEMSDOE33 | `…h33d-analog-tip-stepover-r30…` (41,865) | 0.2632 | No — 99.71% vs GEMSDOE27 | No |
| GEMSDOE25 | `…dotted-h19-5-d2-8…nan` (44,090) | 0.2600 | No — 100.00% vs GEMSDOE24 | No |
| GEMSDOE30 | `…d28-poisson300m-offcat-44090…` (44,090) | 0.2600 | No — identical support class, 100.00% vs GEMSDOE24 | No |
| GEMSDOE24 | `…h25-1-dotted-h19-5-d1-5…nan` (60,069) | 0.2477 | No — 100.00% vs GEMSDOE25 | No |
| GEMSDOE27 | `…topo-gap-closure-t-v2-on-d1-5…nan` (61,328) | 0.2449 | No — 98.02% vs GEMSDOE24 | No |

Prompt runner-up claims are all lower (checked line by line against
`registry/lfi_live_anchors.csv` + `docs/reported-results.csv`: no discrepancies
with the pinned leaders; e.g. GEMSDOE27 H31 0.2250 < 0.2449, GEMSDOE36 KPL36
0.1647 < 0.2750).

## Why 0.2778, and can a unique file beat it? (PhD-level summary)

R0's advantage is **emission economics on shared support**, proven from bytes
in S22 and re-verified here: one H19-5 ridge network → dotting at 2.8 px
(+0.0678 of the +0.0856 total gain) → deleting dots ≤1 px from the catalogue
(+0.0108) → deleting (1,2] px (+0.0070). Under DTI = T/(0.2T+0.2FP+0.8|G|) with
mapped pixels masked, near-catalogue dots are nearly pure FP weight; deleting
6,436 of them while 300 m kernels keep covering the same truth is almost free
score. The one-parameter pure-FP model predicts the family's next scores within
0.001 (T≈5,073; |G|≈12–13k; recall ≈38–42%). **Beating it with a unique raster**
requires either (a) dots with higher mean credit placed where the family is
not — but anchors say truth concentrates where the fleet already agrees
(cons≥3 θ=+2.97), so uniqueness itself caps projections near ~0.20–0.22 on this
stack (PDWC: 0.1977 under today's refit); or (b) new information (1 m LiDAR).
This session improved the *detector* (paired holdout win) but emitted it with
the family's worst habit (catalogue hugging) in milder form. The next lane is
therefore an **emission-geometry lane on this validated surface**, not new
features: wider collar / distance quotas + competitive-overlap caps,
arbitrated by SGMC->500 m and an LFI model the lane was not fitted to.

Public leaderboard fetched 2026-10-28: #1 0.4544, #2 0.3916, #22 0.3261
(`evidence/public-leaderboard-2026-10-28.json`). The prompt's 0.4413/0.3195 are
stale. Even the family's 0.2778 claim sits below #22.

## Three passes

**Pass 1 — implement + verify.** Restored 15/15 pinned inputs + 62/64 frozen
registry rasters + 108 LFI anchors + 9 leaders (all SHA-verified). Froze the
registry before candidate construction. Preregistered 5 ranked hypotheses and
3 frozen experiments. Implemented `fabric25` (masked statistics only; synthetic
tests incl. phase-lag sign recovery), ran E1/E2/E3 on shared v3 folds/evaluator,
packaged E2 per the frozen selection rule via the shared writer, re-audited
downloads (candidate PASS), refitted LFI + SGMC diagnostics, profiled dot
geography, rendered the portal from receipts.

**Pass 2 — adversarial review (bugs/edge cases found & fixed).**
(a) Phase-correlation sign was inverted — caught by synthetic shift test, fixed
and pinned by test. (b) 135° structuring element built the wrong diagonal —
fixed. (c) CSPL coherence accumulation had a convoluted double division —
rewritten with an explicit count accumulator. (d) Two file edits were lost to
parallel tool-call races in this session (CSPL accumulator key; front-door
callout insertion) — both caught by immediate failing tests/runs and reapplied
sequentially; final state grep-verified. (e) Portal renderer KeyError on the
run-card withheld-count key — fixed to the card's schema. (f) Instrument drift
line-by-line: current `spatial.py` hash ≠ S24's; S24 folds were v2, today's are
v3 — so no historical HOLDOUT-DTI is quoted anywhere as a matched bar.
(g) The 19-band cache was removed from feature building to bound RAM (~0.9 GB).
(h) Front-door snippet extraction on sibling sites only matched 2/9 markups —
recorded as a method limit, not evidence of status.

**Pass 3 — re-check against the original request.**
Unique TIF generated and one-click downloadable at the front door + executive
summary with the required file/estimate/uniqueness table and per-site tables;
submission name + 94-char note recorded; [0,1] error prevented by construction
and independently audited; every number labelled HOLDOUT-DTI /
MODEL_PROJECTION_NOT_A_SCORE / USER-REPORTED / ORGANIZER-CONFIRMED(none);
holdout gate enforced before any slot consideration; run card emitted
(`run-card.json`). Unmet by evidence, not by omission: no file in this repo —
including this session's — is OK TO SUBMIT under the protocol, and no honest
estimate puts a unique-on-this-stack raster above 0.2778 yet.

## Limitations & next steps

1. **Coordinator policy needed** on the duplicate-rule scope: dense calibration
   blankets make the literal ≤70% rule geometrically impossible at competitive
   budgets (≥82.34% forced at 37,654 dots), and competitive references now also
   bind (74.89%). Decide the scope explicitly; do not let sessions improvise it.
2. **Next lane (preregister first):** FABRIC surface + distance-stratified,
   uniqueness-capped emission (collar ≥~10 px arm vs 3.05 px arm; caps ≤65% vs
   bhar/spac/h28ridge/cover91 families), gated on SGMC->500 m + paired holdout,
   with LFI kept strictly post-hoc.
3. **Calibration probes remain the highest-information slot spend** (S22 plan,
   pre-registered predictions) — a selector decision, not this session's.
4. **1 m LiDAR lane** needs an unrestricted machine (USGS 3DEP tiles pinned by
   SHA into a GitHub-restorable stack). The in-repo `lidar_scarp_features_u8`
   is licence-unchecked — resolve provenance before any feature use.
5. No organizer receipt exists for any number in this repo; the first real
   submission receipt should be recorded against the exact uploaded SHA-256.
