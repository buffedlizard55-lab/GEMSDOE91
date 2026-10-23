# SLOT_PLAN — 1 entity, 3 slots/week, one blind final file by 2026-12-03

**Slots left this week: __ / __ (human).** **TOP_PUBLIC: ____ (human, with date).**
**Best receipt: none** — 23/23 ledger rows have empty receipt columns (IR-91-05).
`R0 = h33-h33-2-b2` verified: 37,654 dots, twins `c55bafc4…` / `baeae321…`, and — new in
session 3 — its **dot set is reproduced exactly from two independent ancestors** (0 differing
cells; IR-91-12). Session axis: **SPACING**, the only axis with zero prior builds.

## Step 0 — already done (sessions 1–2 thought it was impossible)

Sessions 1–2 declared **BUILD BLOCKED** because `sample_submission.tif`, `existing_faults.tif`
and the ancestors were "not publicly mirrored" (IR-91-02). They are: `scripts/restore_data.py`
pulls all of them from immutable GitHub commits and verifies every sha256 in **3 s / 5 MB**.
The premise is withdrawn (IR-91-11) — and re-stated as the data-use problem it actually is.
`training_features.tif` (419 MB) is the only input with no pinned mirror and is not needed for
this axis.

**Action 0, costing no slot:** have the human paste R0's receipt (0.2778) and `TOP_PUBLIC`
into the ledger. Until then every MODEL below is unscaled and the 0.01 evidence floor cannot
be applied to anything.

## What session 3 measured, and why it caps the axis

The SPACING arms are matched on everything but the treatment: same 40 % of dots (densest 1 km
blocks), same displacement budget (radius-2 ring, 2.0–2.236 px), same constraints. Only the
choice of ring cell differs, ranked by a Gaussian-smoothed density potential (σ = 2 px).

| arm | relocated | density at target | predicted (MODEL) |
|---|---:|---|---|
| `SPACINGspread40` | 15,056 (39.99 %) | 0.066 → **0.035** | **+0.0042** [−0.004, +0.012] |
| `SPACINGclump40` | 14,973 (39.76 %) | 0.066 → 0.058 | **−0.0023** [−0.010, +0.006] |
| `SPACINGjitter40` | 15,038 (39.94 %) | 0.066 → 0.047 | **0.000** (null) [−0.008, +0.008] |

Under a uniform truth prior the edit changes expected kernel credit by −0.17 % (spread) to
−2.4 % (clump), so **the plausible live effect is ≤ 0.003**. That is the useful result: the
axis cannot produce a ≥ 0.01 win, so one slot buys a *decision* (is arrangement a lever at
all?) rather than a score.

## The next three slots, in order (session-3 ordering)

| # | candidate | why this one | what the receipt decides |
|---|---|---|---|
| **1** | `PRUNE-le3p000` (built by GEMSDOE86; re-validate before upload) | the only axis in the project with a **measured live dose-response**: 0.2708 → 0.2778 for 2,545 collar dots, +2.75 × 10⁻⁶ per dot — an order of magnitude above the metric's own zero-credit estimate. Also the only file that satisfies constraint 4 at all. | **≥ +0.01** → the collar is not exhausted; cut a 4 px rung and adopt the 3 px collar as R1. **≤ −0.01** → the 2–3 px shell carries real truth; IR-91-13 becomes the binding argument. **abs < 0.01** → no evidence; PRUNE closes for Phase 1 |
| **2** | `SPACINGspread40` (this session; rebuild then upload the `-zeros` twin) | closes the last unbuilt axis, with its null and sign-flip controls already built and matched | **≥ +0.01** → arrangement carries signal; next cut is spread at 50 % and ring-4. **abs < 0.01** → **geometry is retired**: no more slots on SPACING, MASS or SNAP. **≤ −0.01** → the parent's clusters are real structure; protect them |
| **3** | `RELIEF-frontp15` (GEMSDOE86) **or** `CONC b10px-m20 on R1` if slot 1 promoted R1 | the only built variants that move mass between places instead of deleting it | **≥ +0.01** → build RELIEF-ADD (count raised) and combine with PRUNE. Otherwise the final file is the better of PRUNE and RELIEF plus whichever arm separates from 0 |

Do **not** spend a slot on: `SPACINGclump40` / `SPACINGjitter40` (controls), `MASSm10plus`
(MODEL −0.010, HOLD), `MASSm20minus` (nested in `m10minus`), `PRUNEp1px` (re-legalises the
1–2 px shell), any SNAP arm (prior sessions measured its proxy as negative and its dose is not
separable from a jitter null), or any exact repeat (8+ slots were wasted this way upstream).

## Better axes (proposals only — none built this session)

- **Anisotropic packing (structure-tensor, σ = 3 px).** 2 px along-strike, 4 px across-strike
  at matched area density, using the catalogue's local orientation. *Confounder:* the parent
  is already line-like, so it may be a no-op; new faults may be oblique to mapped strands.
  *Falsifier:* no separation from `jitter40` in two independent draws.
- **Ring-4 spacing (4 px, 25 % of dots).** Tests whether the ceiling above is a dose artefact:
  if 2 px is capped at 0.003 but 4 px is not, the mechanism is real and merely under-dosed.
  *Falsifier:* live effect stays flat while uniform-truth credit moves > 1 %.
- **Receipt-first calibration.** No axis at all: re-submit the parent to convert 0.2778 from
  CLAIM to RECEIPT and re-anchor every MODEL in the ledger. Cheapest information per slot in
  the project, and the only action that lets the 0.01 floor do any work.

## Weeks to the deadline (2026-10-30 → 2026-12-03, ~15 slots)

- **Wk 2 (4–6):** finish MASS on R1 (slot 2) and CONC on R1 (slot 3); if both are flat,
  switch to the two never-built axes, RELIEF (elevation-tercile mass shift) and SPACING
  (Poisson-disk vs lattice at matched count).
- **Wk 3–4 (7–12):** combine the two axes that cleared +0.01, on R1, one change at a time.
  Re-validate format of every candidate from disk on the day it is uploaded.
- **Wk 5–6 (13–18):** confirm the leader, build `TRACKB` traces for Phase 2 (GeoJSON + raster,
  one evidence paragraph per trace, ≥1 km strike-consistent), then freeze **one** final file
  plus **one** `-zeros` fallback and re-run `scripts/validate_release.py` on both.

## Proposed better axes (not built this session)

1. **FRACTIONAL MASS** (a MASS value, not a new letter): in the 2.5–3.5 px shell emit dots at
   `p ≈ 0.33` instead of all-or-nothing. *Mechanism:* the triangular kernel pays 1/3 credit at
   3 px while the (S−M) penalty scales with `p`, so a partial dot dominates both "1" and "0"
   near the collar — this is the only way to buy collar-adjacent credit without violating
   constraint 4. *Confounder:* the organiser may threshold tiny values, and the mass
   normalisation is unverified (IR-91-06). *Falsifier:* < +0.01 live over R1.
2. **RELIEF** (never built by anyone in this lineage): move 10–15% of mass between basin /
   piedmont / range-front terciles of detrended elevation at fixed count. *Mechanism:* new
   faults concentrate at range fronts and basin margins. *Confounder:* Lake Lahontan
   shorelines sit at 1,212–1,334 m and mimic scarps. *Falsifier:* < +0.01 over R1.
3. **DIP_OFFSET_ASYM** (carried from upstream, credit theirs): back-project gravity HG and
   basement gradient updip by `z·cot 60°` before snapping. *Confounder:* sub-horizontal
   basalt caprock margins. *Falsifier:* < +0.01 over R1-SNAPscarp2px.

---

## Session 2 addendum (`arena/a6416f7b`, 2026-10-23) — what changes in the order above

**Nothing in the first three slots is cancelled.** Two things are now known that were not:

1. **A builder exists for CONCENTRATION only** (`tools/run_concentration.py`). The plan's
   slot 1 and slot 2 (`MASS m10minus`, and PRUNE-with-refill) still have **no builder**;
   building them is not a slot cost, it is an hour of work plus the `training_features.tif`
   ranking rebuild. Slot 1 as written cannot start without it.
2. **The three imported CONCENTRATION rows are clustering edits, not prior tests**
   (IR-91-07): their block prior is the parent's own dot density. So "CONC was already
   tried" is false, and "CONC worked" would be over-read. If a CONC result is wanted, run
   the *external-prior* version at the low dose (10%, 5 km blocks), which is exactly what
   the builder does.

**Order I would run, given the above (unchanged ranking, one addition):**

| slot | file | why now |
|---|---|---|
| 1 | `PRUNEp3px` (rebuild, sha `6f7ae705…`) | still the only collar-compliant base; unchanged |
| 2 | `R1-MASS m10minus` on **R1** | needs the R1 ranking, which the builder must emit as a sidecar (`ranking_basis` is the trap identified in IR-91-07) |
| 3 | `R1-CONC f10-blk50` **external prior** | the builder is ready; it is the only axis whose code and tests already exist |

**Hypotheses worth a slot after that (mechanism · confounder · falsifier):**

- **EDGE-FLOOR** — mass just *outside* the collar may be where new-fault truth adjacent to
  known traces lives (forum: new fault can lie within 300 m of known geometry). Confounder:
  collar proximity tracks survey quality. Falsifier: matched count, same marginal-gain
  ranking, dots pushed to 3–6 px vs dots pulled away — if the far version wins, the
  adjacency story is wrong.
- **DENSITY-CAP** — T saturates at 1 per truth pixel, so over-dense clusters buy nothing;
  the 0.51–0.59 CV band reported for the best files is consistent with even coverage.
  Confounder: CV correlates with how much of the grid the prior marks high. Falsifier: two
  files at matched count, CV 0.55 vs 1.2, same prior; if the tighter one wins, spacing is
  causal and CONCENTRATION should be dosed *down*, not up.
- **AMBIGUITY-BUDGET** — one dot per plausible trace position (400 m line spacing ≈ 2–3 px
  positional uncertainty) instead of one per confident pixel. Confounder: it is SPACING
  renamed. Falsifier: a jitter-only twin (±1 px of every dot, same count) — if jitter is
  free, positional uncertainty is not what the metric is paying for.


- **Wk 2 (4–6):** finish MASS on R1 (slot 2) and CONC on R1 (slot 3); if both are flat,
  switch to the two never-built axes, RELIEF (elevation-tercile mass shift) and SPACING
  (Poisson-disk vs lattice at matched count).
- **Wk 3–4 (7–12):** combine the two axes that cleared +0.01, on R1, one change at a time.
  Re-validate format of every candidate from disk on the day it is uploaded.
- **Wk 5–6 (13–18):** confirm the leader, build `TRACKB` traces for Phase 2 (GeoJSON + raster,
  one evidence paragraph per trace, ≥1 km strike-consistent), then freeze **one** final file
  plus **one** `-zeros` fallback and re-run `scripts/validate_release.py` on both.

## Proposed better axes (not built this session)

1. **FRACTIONAL MASS** (a MASS value, not a new letter): in the 2.5–3.5 px shell emit dots at
   `p ≈ 0.33` instead of all-or-nothing. *Mechanism:* the triangular kernel pays 1/3 credit at
   3 px while the (S−M) penalty scales with `p`, so a partial dot dominates both "1" and "0"
   near the collar — this is the only way to buy collar-adjacent credit without violating
   constraint 4. *Confounder:* the organiser may threshold tiny values, and the mass
   normalisation is unverified (IR-91-06). *Falsifier:* < +0.01 live over R1.
2. **RELIEF** (never built by anyone in this lineage): move 10–15% of mass between basin /
   piedmont / range-front terciles of detrended elevation at fixed count. *Mechanism:* new
   faults concentrate at range fronts and basin margins. *Confounder:* Lake Lahontan
   shorelines sit at 1,212–1,334 m and mimic scarps. *Falsifier:* < +0.01 over R1.
3. **DIP_OFFSET_ASYM** (carried from upstream, credit theirs): back-project gravity HG and
   basement gradient updip by `z·cot 60°` before snapping. *Confounder:* sub-horizontal
   basalt caprock margins. *Falsifier:* < +0.01 over R1-SNAPscarp2px.

---

## Session 2 addendum (`arena/a6416f7b`, 2026-10-23) — what changes in the order above

**Nothing in the first three slots is cancelled.** Two things are now known that were not:

1. **A builder exists for CONCENTRATION only** (`tools/run_concentration.py`). The plan's
   slot 1 and slot 2 (`MASS m10minus`, and PRUNE-with-refill) still have **no builder**;
   building them is not a slot cost, it is an hour of work plus the `training_features.tif`
   ranking rebuild. Slot 1 as written cannot start without it.
2. **The three imported CONCENTRATION rows are clustering edits, not prior tests**
   (IR-91-07): their block prior is the parent's own dot density. So "CONC was already
   tried" is false, and "CONC worked" would be over-read. If a CONC result is wanted, run
   the *external-prior* version at the low dose (10%, 5 km blocks), which is exactly what
   the builder does.

**Order I would run, given the above (unchanged ranking, one addition):**

| slot | file | why now |
|---|---|---|
| 1 | `PRUNEp3px` (rebuild, sha `6f7ae705…`) | still the only collar-compliant base; unchanged |
| 2 | `R1-MASS m10minus` on **R1** | needs the R1 ranking, which the builder must emit as a sidecar (`ranking_basis` is the trap identified in IR-91-07) |
| 3 | `R1-CONC f10-blk50` **external prior** | the builder is ready; it is the only axis whose code and tests already exist |

**Hypotheses worth a slot after that (mechanism · confounder · falsifier):**

- **EDGE-FLOOR** — mass just *outside* the collar may be where new-fault truth adjacent to
  known traces lives (forum: new fault can lie within 300 m of known geometry). Confounder:
  collar proximity tracks survey quality. Falsifier: matched count, same marginal-gain
  ranking, dots pushed to 3–6 px vs dots pulled away — if the far version wins, the
  adjacency story is wrong.
- **DENSITY-CAP** — T saturates at 1 per truth pixel, so over-dense clusters buy nothing;
  the 0.51–0.59 CV band reported for the best files is consistent with even coverage.
  Confounder: CV correlates with how much of the grid the prior marks high. Falsifier: two
  files at matched count, CV 0.55 vs 1.2, same prior; if the tighter one wins, spacing is
  causal and CONCENTRATION should be dosed *down*, not up.
- **AMBIGUITY-BUDGET** — one dot per plausible trace position (400 m line spacing ≈ 2–3 px
  positional uncertainty) instead of one per confident pixel. Confounder: it is SPACING
  renamed. Falsifier: a jitter-only twin (±1 px of every dot, same count) — if jitter is
  free, positional uncertainty is not what the metric is paying for.
