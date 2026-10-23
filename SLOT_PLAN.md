# SLOT PLAN — one entity, 3 scored slots/week, deadline 2026-12-03 (unconfirmed)

**State going in:** 29 ledger rows, **0 receipts**, no slot spent from this repo. 15 pinned
inputs verified. Every axis is technically buildable now, so the plan is no longer "what can
we build" but "which 3 files buy the most information".

## Session axis: RELIEF (chosen, not assigned)

RELIEF had **zero ledger rows** while PRUNE (7), SNAP (9), CONCENTRATION (4), MASS (3) and
SPACING (3) all had some. It was also the last axis in the brief's list that had never been
executed anywhere in this lineage. Three matched arms were built (`releases/`, `ledger/`):

| arm | what it changes | moved | predicted (MODEL) |
|---|---|---:|---|
| `r2m15` | 15 % of dots, range front → piedmont | 5,648 | **+0.0070** [−0.003, +0.017] |
| `m2r15` | the exact sign flip | 5,648 | **−0.0070** [−0.017, +0.003] |
| `null15` | same moves, tercile counts preserved | 5,648 | **0.0000** [−0.010, +0.010] |

**Do not spend a slot on RELIEF this week**, for two measured reasons:

1. **The effect is below the evidence bar.** 15 % of the mass must be relocated *off* the
   parent's detector support (only 90 support cells in the whole footprint are legal at the
   parent's own 2.8 px spacing floor). The prediction is ±0.007, and the bar for "evidence" is
   0.01. One receipt would be unreadable: `r2m15` alone cannot be separated from "moving dots
   off support costs score".
2. **It would need two slots to say anything.** The contrast that matters is
   `r2m15 − null15`; the null arm is the control for the off-support placement. Two slots out
   of three, for a ±0.007 effect, is a bad trade while the PRUNE ladder is unscored.

Keep the three files. They are the cheapest available answer if a slot ever goes spare, and
they pre-register the mechanism so a later receipt is interpretable.

## Next 3 slots — in this order

| # | file | why this one | what the result changes |
|---|---|---|---|
| 1 | `…-PRUNEle15norefill-20261023-1ca1ff6f.tif` (zeros twin as fallback) | The largest predicted gain on the board (**+0.010**), and it is the **only** arm that tests the live disagreement between the metric algebra (off-catalogue mass is pure denominator cost) and the imported `p4px` row (predicts −0.009). It rebuilds byte-identically here (`make releases` → sha256 `1ca1ff6f…`). | **Gain ≥ +0.01** → delete-only is confirmed, the 3 px collar is right, and every later slot should push the same lever (next dose 25–30 %, a new `(PRUNE, le25-norefill)` pair). **Flat** → the 3–15 px shell carries no new-fault credit and mass is not the lever. **Loss ≥ −0.01** → new faults hug known traces (the `p4px` story); stop pruning and add mass *inside* 3–8 px instead. |
| 2 | if slot 1 gained: `…-PRUNEle8norefill-…-e1dd69d0.tif`; if it lost: a MASS **add-in-collar** arm built from the feature stack | Locating the optimum (le8) versus testing the opposite sign (add) — both are one change off R0. | Slot 2's reading decides whether the final file is a deletion or an addition lineage. |
| 3 | `…-CONC…` km-block arm on a **feature-stack** prior (bands 3/18/19 + 12), or `RELIEFr2m15 + null15` only if a spare slot exists | CONCENTRATION is the one axis where the brief's own prior ("faults cluster at km scale") has never been tested against an external, non-dot-density prior in this repo. | A gain ≥ 0.01 makes prior transfer the winning family for Phase 2; a flat result retires block-scale priors and pushes everything into TRACKB. |

Rules that stay in force: one change per file, `validate_raster` PASS before upload, paste
`receipt_score` + `receipt_date` the same day, and treat **any** live |Δ| < 0.01 as *no
evidence* (public chunks only; the private score may differ).

## Weeks to the deadline (2026-12-03, ≈ 6 weeks)

| week | plan |
|---|---|
| now | Spend this week's slots on the PRUNE ladder: `le15` first, then `le8` or the add-arm depending on the sign. |
| wk 2 | Read the ladder. Monotone gain → keep cutting mass, build `le25`/`le30`. Loss → build the 3–8 px **add** arm. Flat → retire mass, go to CONCENTRATION. |
| wk 3–4 | Take the winning family and **combine two axes** (e.g. prune + concentration) — the first build where two changes are allowed, because each has a receipt. |
| wk 5 | Confirm the winner on a fresh build, and re-validate the format of both winner and fallback. |
| wk 6 | Choose the final file **blind** from the ledger (highest receipt, not highest hope), re-read both files from disk, upload. Keep TRACKB out of the weekly slots unless the human decides otherwise — it is Phase-2 currency (expert-expanded labels reward coherent traces), not Phase-1. |

## What would change my mind

- **A receipt that disagrees with the algebra.** If `le15` loses while `le8` gains, the
  dose-response is non-monotone and nothing here is understood; stop and re-derive before
  spending again.
- **A TOP_PUBLIC number.** The plan optimises *information per slot*; if the gap to the top is
  smaller than 0.01, only variance-reduction moves make sense, and the plan inverts.

## Axes proposed for later (mechanism · confounder · falsifier) — not built this session

1. **MASS-IN-COLLAR (add 3–8 px, not delete).** Mechanism: new faults are new *geometry of
   existing systems* and the organiser says they can lie within 300 m of known traces; if the
   lineage's 3 px collar was too aggressive, mass just outside it pays. Confounder: that band
   is also where flight-line artefacts live. Falsifier: `le15` gains *and* this loses.
2. **CONCENTRATION on a multi-layer feature prior at 2 km blocks.** Mechanism: block-scale
   structural prior transfers; count fixed so only the numerator moves. Confounder: the prior
   tracks survey quality (400 m line spacing over Area 2), which is why the *external*
   non-dot-density requirement exists. Falsifier: gain ≤ 0 while block CV moves as designed.
3. **TRACKB (Phase 2 only).** Strike-consistent traces ≥ 1 km from R0's best-supported dots,
   as GeoJSON + raster, one evidence paragraph each. Mechanism: Phase 2 labels are expanded by
   experts reviewing submissions, so a geologically coherent trace can be *adopted*.
   Confounder: reviewer anchoring. Falsifier: traces that disagree with the local strike field.
