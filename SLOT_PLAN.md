# SLOT PLAN — merged after the two 2026-10-23 sessions (PRUNE ladder + CONCENTRATION)

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
