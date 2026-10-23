# SLOT_PLAN — 1 entity, 3 slots/week, one blind final file by 2026-12-03

**Slots left this week: __ / __ (human).** **TOP_PUBLIC: ____ (human, with date).**
**Best receipt: none** — 20/20 ledger rows have empty receipt columns (IR-91-05).
`R0 = h33-h33-2-b2` verified here: 37,654 dots, twins `c55bafc4…` / `baeae321…`, grid
EPSG:32611 3730×3292 100 m float32, footprint 5,167,373 px.

**Session AXIS: MASS** (chosen here, not assigned). MASS is the only axis in the brief whose
existing variants do **not** test the brief's definition: all three were ranked by
`0.6·clip(d_catalogue_px/50) + 0.4·uniform(seed)` — a synthetic heuristic that is explicitly
"NOT parent model ranking" (`ledger/submissions.csv`, `ranking_basis`). So MASS is open.

## Step 0 — unblock (must happen before slot 1)

`python scripts/preflight.py` currently returns **BUILD BLOCKED**; `sample_submission.tif`,
`existing_faults.tif` and `training_features.tif` are not here and are not public (IR-91-02).
On the machine that holds `data/`, run:

```bash
python src/gems91/pinned.py check          # all 15 pins must say OK
python scripts/preflight.py                # must say BUILD ALLOWED
```

## The next three slots, in order

| # | Candidate | Why this one | Predicted Δ live | What the receipt decides |
|---|---|---|---|---|
| **1** | `h33-h33-2-b2-PRUNEp3px-20261023-6f7ae705` (rebuild; sha must equal `6f7ae705…`) | Only file in the inventory that satisfies constraint 4 at all: deletes the 2,171 dots at 2 < d ≤ 3 px and refills at d > 3 px, count fixed at 37,654. Blind off-catalogue SGMC PROXY 0.096083 vs R0 0.096056 — flat (+0.00003), so this slot is bought on compliance, not on that diagnostic. | **MODEL +0.005 [+0.001, +0.011]** | **≥ R0 + 0.01** → promote to `R1` and adopt the 3 px collar permanently; every later axis is built on R1. **≤ R0 − 0.01** → the 2–3 px shell carries real truth; the ≥3 px gate is wrong for this dataset and must be argued, not obeyed. **\|Δ\| < 0.01** → no evidence; the public chunks are only part of the region, so a sub-0.01 move is the expected outcome. Keep going on R1 anyway: it is the only compliant base. |
| **2** | **`R1-MASSm10minus`** = drop the 10% of R1's dots with the lowest **marginal DTI gain under R1's own model**, refit at fixed seed, count 33,889 | The brief's MASS recipe, run for the first time on its own ranking and on a compliant parent. New (parent, axis, value) triple, no dedupe collision. | **MODEL 0.000 [−0.008, +0.008]** | **≥ R1 + 0.01** → mass is not saturated; the next slot goes to `MASS m10plus on R1` (the add-half) and the field is worth extending. **≤ R1 − 0.01** → the parent is mass-tight; close MASS and spend remaining slots on RELIEF/SPACING, which have never been built. **\|Δ\| < 0.01** → mass is flat over 30–45k dots, which matches the ledger's confound warning; stop dosing mass. |
| **3** | If slot 1 ≥ R0 + 0.01: **`R1-CONCb10px-m20`** (20% of dots from coldest → hottest 1 km blocks, block CV reported before/after). If slot 1 inconclusive: **`R1-SNAPscarp2px`** (≤2 px onto Bands 19/12 scarp + 18/3 gradient, `d_nn ≥ 2.83 px`). | Concentration is the largest MODEL gain on the board (+0.020) but was never gate-clean; on R1 it becomes legal. SNAP-scarp is the only SNAP variant with a positive blind SGMC delta (+0.00075) that is free of dedupe collisions on R1. | CONC **MODEL +0.020 [−0.006, +0.056]** / SNAP **MODEL +0.006 [−0.005, +0.016]** | CONC **≥ +0.01** → clustering beats even spacing at fixed count; then test the *opposite* dose (CV target ≈ 0.55, the best-file band) to locate the optimum instead of assuming more is better. SNAP **≥ +0.01** → scarp re-centring beats the H19 field; combine with CONC in weeks 3–4. Either **< 0.01** → retire that axis with a receipt and move to RELIEF. |

Do **not** spend a slot on: `MASSm10plus` (MODEL −0.010, HOLD), `MASSm20minus` (nested in
`m10minus`, HOLD), `PRUNEp1px` (MODEL −0.006, and it re-legalises the 1–2 px shell we just
paid to remove), or any exact repeat (8+ slots were wasted this way upstream).

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
