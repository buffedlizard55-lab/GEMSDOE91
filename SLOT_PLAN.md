# SLOT PLAN — merged state, 2026-10-23 (CONCENTRATION + PRUNE + MASS)

**Status: 38 BUILT rows, 0 SUBMITTED, 0 receipts.** R0's 0.2778 is a **CLAIM**. Four sessions
have now produced files on the same parent without a single live number coming back. That is the
governing fact: every prediction here is MODEL, and a live |Δ| < 0.01 is **no evidence**.

## Week 1 should measure each axis once, not re-dose one axis

Three slots, three different axes, one receipt each — because with zero receipts the repository
cannot yet distinguish "PRUNE works" from "CONCENTRATION works" from "MASS works". Re-dosing one
axis before that is spending a slot on a hypothesis that cannot be separated from its neighbours.

## Next three scored slots, in order

| # | candidate (built?) | file / sha8 | predicted (MODEL) | what the receipt changes |
|---|---|---|---|---|
| 1 | `CONCENTRATION/gdr25rm10` — 10 % of dots moved into the highest-prior 2.5 km blocks, prior **independent** of both the catalogue and the lineage mask (built, merged PR #13) | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01` | **+0.0123** [−0.022, …] | Highest predicted gain on the board and the only arm whose prior is external. ≥ +0.01 ⇒ prior transfer is real and slot 3 becomes a second prior scale; ≤ −0.01 ⇒ block-scale relayout destroys coverage (the measured 88.6 %→80.2 % H19-5 coverage loss is that failure mode). |
| 2 | `PRUNE/le10-norefill` — delete-only 10 px collar, 26,294 dots (built) | `…-PRUNE-le10-norefill-20261023-04002dae` | **+0.008** [−0.006, +0.019] | The only family exempt from the collar ruling (brief §4.4 exempts AXIS=PRUNE), so this slot cannot be blocked by IR-91-03. ≥ +0.01 ⇒ far-from-catalogue mass is mostly denominator cost; flat ⇒ stop buying PRUNE doses. |
| 3 | `MASS/cons3add` — add 10 % (3,765 dots) at the best-supported unspent cells, strictly >3 px off the catalogue (built) | `…-MASScons3add-20261023-2803126d` | **+0.009** [−0.002, +0.019] | **Contingent on the IR-91-03 ruling** (see below). Tests whether the d2.8 thinning cut real structure. If the collar is ruled binding on every file, put `gdr25m10` (`d54e8815`, +0.0113) here instead and MASS waits for a PRUNE-rebased parent. |

Do **not** spend a slot on: `MASS/cons2drop` (a nested deeper cut), `p4.5px-h19cover`
(MODEL −0.015, falsifier only), any further `SPACING` arm (bound ≤0.003), another
`CONCENTRATION` arm this week (the three GDR arms are one experiment, IR-91-19 of the merged
PR), `SNAP` ≤2 px (±0.002, nine rows), or `RELIEF` (its declared inputs contain no elevation band).

## The ruling that can block slot 3 (IR-91-03)

R0 keeps 2,171 dots at 2–3 px from the catalogue; **R0 itself fails** the brief's 3 px collar, and
every non-PRUNE child inherits them. If the collar binds *new mass only*, MASS is testable as
built. If it binds *every file*, no non-PRUNE child of R0 can ship — and that also affects
`gdr25rm10`, which is itself a non-PRUNE child (its new cells are >3 px, but it inherits the same
2,171 dots). The human rules; the PRUNE slot is unaffected either way.

## Weeks to the deadline (2026-12-03, unconfirmed on the competition page)

- **Wk 1:** rule on IR-91-03, fill TOP_PUBLIC + slots, then submit the three files above, one per
  slot. Paste `receipt_score` + `receipt_date` the same day. 38 builds and no receipts is the
  largest single weakness in this repository, larger than any axis choice.
- **Wk 2:** read the three receipts as a *ranking of axes*, not of files. Whichever axis cleared
  +0.01 gets the next dose; if none did, the honest conclusion is that this parent is at a local
  optimum and the remaining weeks should go to the final-file choice rather than to new axes.
- **Wk 3–4:** combine the winning axis with the runner-up only if the receipt supports both;
  otherwise confirm the winner with a second, independent dose.
- **Wk 5–6:** confirm the strongest file, build its fallback twin, re-validate both from disk,
  and choose **one** final file blind. One entity, three scored files a week, no agent submits.

## Proposed axes for later sessions — NOT built here (mechanism / confounder / falsifier)

1. **FRACTIONAL-MASS at fixed geometry.** Emit 0.5 rather than 1.0 on the lowest-support half of
   R0's dots. Mechanism: mass is nearly free within 2.83 px of truth (a dot's own match discounts
   its own penalty), so half-credit on doubtful ground keeps ~half the upside and halves the cost.
   Confounder: the reader may reject non-binary values — the template is binary and this is
   **unverified**. Falsifier: a validation error, or a score that moves like a pure prune.
2. **SUPPORT-GRADED REFILL.** Use support-2/1 cells as refill material for a collar prune, holding
   mass constant while changing its precision mix. Confounder: it is neither a PRUNE (collar not
   tested) nor a MASS (mass unchanged) — label it honestly. Note the merged finding that
   fixed-count refill under a preserved d2.8 exclusion is infeasible (IR-91-18); this design would
   have to drop that exclusion and say so.
3. **RELIEF with a real elevation band.** `axis_requirements.RELIEF` lists `ext_lidar_scarp_u8`, a
   scarp-detection product rather than detrended elevation, so the axis as briefed cannot be built
   from it. Needs the DEM-derived bands the human holds.

**Human must supply:** the IR-91-03 collar ruling (it decides whether slot 3 and `gdr25rm10` are
uploadable), TOP_PUBLIC with the date it was read, slots remaining this week, the 2026-12-03
deadline confirmation, and a receipt per slot.

---

## Appendix — the merged sessions' own slot plans (kept verbatim, not superseded silently)

**State.** Parent R0 `h33-h33-2-b2` (37,654 dots, 2.236 px catalogue floor, claimed 0.2778 =
**CLAIM**, no receipt anywhere). Ledger: 32 BUILT rows, **0 SUBMITTED**, **0 receipts**. Two axes
were built today on that parent, all gate-clean and byte-reproducible:

| axis | arms built | predicted (MODEL) | what it varies |
|---|---|---|---|
| PRUNE (delete-only) | `le4` +0.003, `le5` +0.005, `le10` +0.008, plus earlier `le3` +0.002, `le8` +0.006, `le15` +0.010 | +0.002 … +0.010 | how much mass to remove |
| CONCENTRATION (GDR thermal prior) | `gdr25rm10` **+0.0123** [−0.022,+0.037], `gdr25m10` +0.0114, `gdr10m10` +0.0113 | +0.011 … +0.012 | where the mass sits |

**Two things the numbers say, and they shape the slots.**

1. **PRUNE is a dose ladder, not six experiments** — the six rungs differ only in how much collar
   mass is deleted, and their predictions are monotone. One receipt anywhere on the ladder
   (preferably the top) tells you the sign of the whole axis.
2. **The three CONCENTRATION arms are one experiment, not three** — within 0.001 of each other on
   every local instrument (IR-91-17). Their floor is *measured*: if truth followed the lineage's
   own H19-5 field the edit costs −0.022 (mask coverage 88.6 % → 80.2 %); under uniform random
   truth −0.006; under the prior itself +0.114 before a ×0.1 claim (IR-91-19).

A third session (#10) added three refill-held PRUNE arms (`p2.5px-h19cover` +0.002, `p2.9px-h19cover` +0.004, `p4.5px-h19cover` **−0.015**): count held, refilled from H19-5 coverage. The negative one at 4.5 px is the first negative PRUNE prediction on the board and marks the collar dose as that axis's risky end. It does not change the ordering below.

So the whole board is **two bets**: *remove mass* (PRUNE) and *move mass to an independent prior*
(CONCENTRATION). Spend slots to separate those two, not to refine either by a notch.

## Next three scored slots, in order

| order | candidate (file in `releases/`) | what the receipt decides |
|---|---|---|
| 1 | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` (+0.0123; prior from GDR features **>8 px off the catalogue**, 2.5 km blocks) | The only file in the repo that adds *location* information the catalogue and the lineage mask do not contain. Δ ≥ +0.01 ⇒ the prior transfers: build the 20 % dose (`w20`, new pair). Δ ≤ −0.01 ⇒ the lineage mask carries real recall, retire this axis. \|Δ\| < 0.01 ⇒ no evidence; do not re-tune the fraction. |
| 2 | `…-PRUNEle15-norefill-20261023-1ca1ff6f.tif` (+0.010; verified byte-reproducible today, `scripts/build.py --axis PRUNE --value 15`) | The best expected value among the remove-mass files and independent of slot 1. Δ ≥ +0.01 ⇒ the field is over-massed far from known traces: bisect upwards (`le20`, new pair) or test refill-held once a ranking exists. \|Δ\| < 0.01 ⇒ mass is not the binding constraint at this dose; the sign of `le4` then locates the optimum. Δ ≤ −0.01 ⇒ the >3 px halo carries new-fault truth; stop pruning and spend everything on the prior axis. |
| 3 | **Conditional.** If slot 1 ≥ +0.005 → `…-CONCENTRATIONgdr25m10-20261023-08bf80cf.tif` (wider prior; makes the 1 km arm interpretable). If slot 1 flat/negative and slot 2 positive → `…-PRUNEle10-norefill-…-04002dae.tif` (fills the 10–15 px gap). If both flat → `…-SPACINGspread40-…-6d389309.tif` (retires arrangement for one slot, bounded ≤0.003). | Turns two single points into a direction: prior-vs-mask for CONCENTRATION, dose shape for PRUNE, or a clean retirement of the geometry axis. |

Do **not** spend a slot on `gdr10m10` or on `le4`/`le5` before a 2.5 km arm and the top PRUNE
dose have receipts; both are refinements of an unanswered question.

## Weeks to the deadline (2026-12-03, still unconfirmed on the competition page)

- **Wk 1 (now):** slot 1 = `gdr25rm10`. Paste `receipt_score` + `receipt_date` the same day.
- **Wk 2:** slot 2 = `PRUNEle15`. The entity gets three scored files per rolling week; that is
  two bets and one receipt each — enough to choose a direction.
- **Wk 3–4:** follow the conditional slot 3. If CONCENTRATION transferred, build the 20 % dose;
  if PRUNE transferred, bisect. Combine the two axes only if both are ≥ +0.01, and then one
  change at a time from the better parent.
- **Wk 5–6:** confirm on the best parent, build the `-zeros` fallback twin, re-validate both from
  disk (`scripts/validate.py` prints PASS), choose the final file **blind**.

## Better axes to propose (none built)

1. **PRIOR-BLEND at fixed count.** `p = λ·thermal + (1−λ)·lineage-mask`, λ = 0.3, instead of
   replacing one prior with the other. It is the only version of the CONCENTRATION idea that can
   win under *both* measured truth models. Confounder: λ is a free knob; falsifier: λ = 0.3 and
   λ = 0.7 disagree in sign.
2. **COVERAGE-FLOOR.** Move 10 % but only from dots that duplicate an already-covered field cell,
   so the 8.4 pp H19-5 coverage loss measured today cannot happen.
3. **RELIEF terciles** (blocked, not time-limited): still needs `training_features.tif` (or a
   licensed DEM) to define basin/piedmont/range-front terciles.

**Human must supply:** TOP_PUBLIC with a date, this week's slot count, deadline confirmation,
R0's receipt for 0.2778, and a ruling on IR-91-03 (2 px vs 3 px collar). Do not contact
drivendata.org or leaderboard pages programmatically; no agent submits.

## Session 4 addendum (`arena/086eff6b`) — the top of the PRUNE band

Three more delete-only rungs, at the only doses the 1–50 % band left open:
`le16norefill` (16,375 removed, 43.49 %, **+0.012** MODEL), `le18norefill` (17,791, 47.25 %,
**+0.013**), `le19norefill` (18,450, 49.00 %, **+0.014**). `le19` is the band limit; `le20`
would be 50.80 % and is therefore out of bounds. All gate-clean on both validators.

They matter for one reason: **the ladder has not rolled over.** On the rebuild-based
hide-and-recover instrument the marginal gain per removed dot is flat from le3 to le19
(+1.2e-8 to +4.0e-8 DTI per dot, no saturation), so the optimum is at or beyond the band
limit — and `le19` is also the cleanest read on the mass confound, because it halves the
parent's mass (37,654 → 19,204 dots, 0.37 % of the footprint) while the fleet's best files
use 37–44 k dots.

Slot advice: if a mid-ladder receipt comes back positive, spend the next slot on `le19`
rather than another interior rung. If `le19` comes back ≤ −0.01, the far halo carries truth,
the delete-only family is finished, and the remaining slots belong to the refill-held arms
and to CONCENTRATION. Two caveats carried forward: `le4`/`le5` have canary AUCs above 0.90
(IR-91-26), and no receipt exists anywhere, so every number here is MODEL.
