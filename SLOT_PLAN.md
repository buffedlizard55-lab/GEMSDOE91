# SLOT PLAN — one entity, 3 scored slots/week, deadline 2026-12-03 (unconfirmed)

## Session axis: PRUNE (chosen, not assigned)

The prior sessions chose MASS and CONCENTRATION; both are still blocked on
`training_features`. **PRUNE is the only axis whose inputs are now hash-verified in this
workspace** (`scripts/verify_manifest.py` → `[READY] PRUNE`), which is why it is the axis
this session executes to receipt quality rather than proposing.

Within PRUNE, the brief's own values (≤1, ≤2) are **no-ops on R0**: the parent already sits
at 2.236 px, so nothing is within 2 px. The only meaningful direction is upward. That makes
a **delete-only dose ladder** the correct design, not three different edits.

The design is backed by a measurement rather than a hunch: **all of R0's credit against the
catalogue lies within 3 px** (necessarily, since the kernel radius is 3 px). So every dot
removed between 3 and 15 px earns **zero** credit on known faults while still costing `0.2`
in the denominator. The ladder therefore isolates exactly one unknown: how much *new-fault*
credit those dots were earning.

## Next 3 slots — the ladder, in this order

| # | build | dots | removed | % R0 | predicted | what the result would change |
|---|---|---|---|---|---|---|
| 1 | `PRUNEle3norefill` | 35,483 | 2,171 | 5.77 % | +0.002 | Smallest step off the parent. Most likely below the 0.01 bar, so a flat result is *expected*. A loss means 2 px is already past the optimum and nothing further should be pruned. |
| 2 | `PRUNEle8norefill` | 28,490 | 9,164 | 24.34 % | +0.006 | Separates denominator saving from new-fault credit. 7,553 of the 9,164 removed dots are zero-credit against the catalogue. |
| 3 | `PRUNEle15norefill` | 21,989 | 15,665 | 41.60 % | +0.010 | Largest dose inside the 1–50 % band and the only rung with a plausible path past +0.01. |

All three are built and gate-clean (`releases/`). Predictions, confounders and falsifiers
are in `docs/MECHANISM_CARDS.md`.

**This ladder directly tests a recorded disagreement.** The imported `PRUNE/p4px` row
predicts **−0.009** for removing the 2–4 px collar; the metric algebra says removal *gains*
because zero-credit dots are pure denominator cost. If `le8`/`le15` gain, that imported
prediction is wrong. See `IRREGULARITIES.md` IR-91-13.

**Do not** spend slots on the existing refill-based `p1px`/`p3px`/`p4px` rows: they were
built by an earlier session and never scored, and their predictions are non-monotone in dose
(−0.006, +0.005, −0.009), which a single mechanism cannot produce.

## Session-3 addendum: the SPACING axis, and where it belongs

Built here, matched on everything but the treatment (same 40 % of dots, same radius-2
displacement budget, same constraints), with a **null** arm (`jitter40`) and a **sign flip**
(`clump40`) so any live difference is attributable to spacing direction:

| arm | relocated | density at target | predicted (MODEL) |
|---|---:|---|---|
| `SPACINGspread40` | 15,056 (39.99 %) | 0.066 → **0.035** | **+0.0042** [−0.004, +0.012] |
| `SPACINGclump40` | 14,973 (39.76 %) | 0.066 → 0.058 | **−0.0023** [−0.010, +0.006] |
| `SPACINGjitter40` | 15,038 (39.94 %) | 0.066 → 0.047 | **0.000** (null) [−0.008, +0.008] |

The uniform-truth ceiling (−0.17 % to −2.4 % of expected credit) caps the plausible live
effect near **0.003**: this axis cannot win a slot on expected score. It earns one only as a
retirement test — a flat result says arrangement is not a lever and frees every later slot.

**Where it sits relative to the PRUNE ladder above.** Slot 1 stays PRUNE (`le3`, the ladder's
first rung, +0.002). Slot 2 should be the ladder's **`le15`** rung (+0.010, the largest
predicted gain in the ledger) *if* `le3` lands ≥ +0.01; otherwise slot 2 is
**`SPACINGspread40`**. Do not spend a slot on `clump40` or `jitter40` (controls), and do not
build a fourth SPACING dose before the first receipt exists.

## Weeks to the deadline

| week | plan |
|---|---|
| now | Spend this week's slots on the ladder. Copy every receipt number into `ledger/submissions.csv`. |
| wk 2 | Read the ladder. **Monotone gain** → keep cutting mass; next axis should be MASS-SHAPE at fixed count. **Monotone loss** → new faults hug the known traces; stop pruning and add mass in the 3–8 px band instead. **Flat** → PRUNE is exhausted, move to CONCENTRATION. |
| wk 3–4 | Whatever the ladder says, the next build needs `training_features` (it unblocks MASS, SNAP and CONCENTRATION). Ask the human to supply it; it is the single highest-value missing input. |
| wk 5–6 | Confirm the winner, build a fallback, re-validate both formats, re-read both from disk, choose the final file blind from the ledger. |

## Better axes (proposed, not built this session)

1. **MASS-SHAPE at fixed count.** Keep 37,654 dots but redistribute from dense clusters to
   sparse ones. Mechanism: the denominator charges `0.2(S−M)`, so credit already collected by
   a neighbour is nearly free while fresh credit is not — overlapping dots waste count
   without buying credit. Confounder: true fault density varies at km scale, so flattening a
   real cluster costs recall. Falsifier: were the removed dots' neighbourhoods already
   credited by a neighbour? *Blocked on* `training_features`.
2. **MARGINAL-PRUNE by exact gain.** Rank R0's dots by exact marginal gain
   (`scripts/dti.py::rank_dots`) and drop the bottom decile instead of dropping by distance to
   the catalogue. Confounder: the holdout is the catalogue, not new-fault truth. Falsifier:
   the dropped set should not overlap the hide-and-recover positives.
3. **TRACKB (Phase 2 only).** Strike-consistent traces ≥1 km as GeoJSON + raster with one
   evidence paragraph per trace. Cannot be scored in Phase 1 in a way that transfers, so it
   should not consume a weekly slot unless the human decides otherwise.

## Honest note on information per slot

The brief's evidence bar is ±0.01 on public chunks. The parent's best single step was +0.0070
(CLAIM). **No one-pixel prune step can clear that bar.** If you would rather spend all three
slots on moves that can plausibly exceed 0.01, replace slot 1 with the upper doses. That is a
judgement about information per slot, and it is yours, not mine.
