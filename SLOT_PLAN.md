# SLOT PLAN — one entity, 3 scored slots/week

Deadline unconfirmed (competition page not fetched; IRREGULARITIES §6). The plan is
phrased in weeks so it survives a corrected date.

## Session axis (chosen, not assigned): PRUNE

Rationale, now evidenced rather than argued. The last two rungs of the climb are both
prune-like, and the parent's operation is verified: R0 = solo-d28 (40,199 dots) minus
the 2,545 dots within ≤2 px of the catalogue, **no refill**. PRUNE is the only axis that
needs no data product that is missing — MASS needs the parent's ranking, SNAP needs a
driver band, RELIEF needs lidar. So PRUNE is the axis this session can execute to
receipt quality.

Within PRUNE the brief's own values (≤1, ≤2) are **no-ops** on R0: the parent already
sits at 2.236 px, so nothing is within 2 px. The only meaningful direction is upward,
which makes the correct design a **dose-response**, not three different edits:

| dose | dots removed | % of R0 | file |
|---|---|---|---|
| ≤3 px | 2,171 | 5.77 % | `R0-PRUNE3-20261023` |
| ≤8 px | 9,164 | 24.34 % | `R0-PRUNE8-20261023` |
| ≤15 px | 15,665 | 41.60 % | `R0-PRUNE15-20261023` |

All three are built, gate-clean, in `releases/`. Predictions and falsifiers are in
`docs/MECHANISM_CARDS.md`.

**What makes this a real experiment:** all of R0's credit against the catalogue lies
within 3 px, so every dot removed between 3 and 15 px earns *zero* credit on known
faults and only costs `0.2` in the denominator. The dose therefore isolates one term:
how much *new-fault* credit those dots were earning. A monotone rise says throw mass
away; a monotone fall says new faults hug the known traces.

## The next three slots

| # | build | what each result would change |
|---|---|---|
| 1 | **`R0-PRUNE3`** — 5.77 % removed | If it gains, the 2 px margin is too tight and the next slot pushes further. If it loses, 2 px is already past the optimum and no later file should prune at all. Predicted +0.002: **most likely below the 0.01 evidence bar**, so a flat result is expected and is not a failure. |
| 2 | **`R0-PRUNE8`** — 24.34 % removed | Separates "denominator cost" from "new-fault credit". A gain materially larger than slot 1's means the 3–8 px shell is background; a loss means those dots sit on unmapped structure 300–800 m off the known traces. |
| 3 | **`R0-PRUNE15`** — 41.60 % removed | The only card with a plausible path past +0.01. If it wins, the next axis should keep cutting mass; if all three are flat, **PRUNE is exhausted** and slots 4+ go to CONCENTRATION and RELIEF. |

Order is a deliberate dose ladder: slot 1 is cheap and sharpens the interpretation of
slots 2–3. Do not reorder.

## Weeks to the deadline

| week | plan |
|---|---|
| now | Upload the three PRUNE files across the week's slots. Copy every receipt number back into `ledger/submissions.csv`. |
| wk 2 | Read the ladder. If monotone gain: build PRUNE ≤25 px (needs a cap on removals). If monotone loss: stop pruning; build **MASS +10 %** instead, which needs the parent's ranking (see below). If flat: move to CONCENTRATION. |
| wk 3–4 | **CONCENTRATION** at block 16 px = 1.6 km, 15 % of dots from lowest-prior to highest-prior blocks, reporting block-density CV before/after (target band 0.51–0.59). Then combine with the best PRUNE dose, one change at a time. |
| wk 5–6 | Confirm the winner, build a fallback, re-validate both formats, re-read both from disk, choose the final file blind from the ledger. |

Slot budget: 3/week. At least 8 historical slots went to exact repeats; `ledger.py
check` before every build now prevents that. Current week's usage is unknown (README).

## Better axes (proposed, not built this session)

1. **MASS-SHAPE at fixed count.** Keep 37,654 dots but redistribute from dense clusters
   to sparse ones. Mechanism: the denominator charges `0.2(S−M)`, so credit already
   collected by a neighbour is nearly free while fresh credit is not — overlapping dots
   waste count without buying credit. Confounder: true fault density genuinely varies at
   km scale, so flattening a real cluster costs recall. Falsifier: check whether removed
   dots' neighbourhoods were already credited by a neighbour.
   *Blocked on:* the parent's ranking, which was never stored. Would need rebuilding
   from GEMSDOE32's recorded recipe and `training_features.tif`.
2. **MARGINAL-PRUNE by exact gain.** Rank R0's dots by exact marginal gain under a local
   holdout (`dti.rank_dots`) and drop the bottom 10 %, instead of dropping by distance to
   catalogue. Mechanism: cut the dots the metric values least. Confounder: the holdout is
   the catalogue, not new-fault truth, so this can select for already-mapped geometry.
   Falsifier: the dropped set should not overlap the hide-and-recover positives.
3. **TRACKB (Phase 2 only).** Strike-consistent traces ≥1 km from the top-ranked dots as
   GeoJSON + raster, with one evidence paragraph per trace for a geologist. Not a weekly
   slot candidate — it cannot be scored in Phase 1 in a way that transfers.

## Recommended next step, honestly

The brief's evidence bar is ±0.01 on public chunks. The parent's best single step was
+0.0070 (CLAIM). **No prune dose of one or two pixels can clear that bar**, so slots 1
and 2 are refinements and only slot 3 can produce evidence. If you would rather spend
all three slots on moves that can plausibly exceed 0.01, replace slot 1 with
CONCENTRATION 15 % and keep slots 2–3 as the upper doses. That is a judgement call
about information per slot, and it is yours.
