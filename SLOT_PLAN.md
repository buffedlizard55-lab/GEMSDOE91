# SLOT PLAN — after the 2026-10-23 CONCENTRATION session

**Session result: three gate-clean CONCENTRATION arms on R0, none submitted.** All three move
10.00 % of R0's dots (3,765) out of the lowest-prior km blocks and into the highest-prior
ones of an independent, public-domain prior (GDR thermal features). Count fixed at 37,654 in
every arm, single seed, identical placement rules; only the block scale and the prior set
differ. Evidence: `evidence/concentration_axis_20261023.json`.

**The honest read: these are one experiment, not three.** The three arms land within 0.001 of
each other on every local instrument (predicted +0.0113 … +0.0123; surrogate-truth DTI +41 %,
+41 %, +44 %; lineage-mask bound −0.021 … −0.022). Block scale (1 vs 2.5 km) and the
"remote-features-only" prior barely change the outcome, so **spending three slots on them
would buy one number three times** (IR-91-17). Submit one; keep the other two only as
fallbacks.

**The bet, stated as a decision.** If new-fault truth follows thermal features more closely
than it follows the mask this lineage was thinned from, the arm gains; if it follows the
lineage's own H19-5 mask, the arm loses about 0.022 (measured, pessimistic because that mask
is ~3× denser than truth). Nothing in this repo can tell which; only a receipt can.

## Next three scored slots, in order

| order | candidate (file in `releases/`) | what the receipt decides |
|---|---|---|
| 1 | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` — prior from GDR thermal features **>8 px off the mapped catalogue**, 2.5 km blocks | The only arm whose prior cannot be a re-encoding of the known traces, so it is the cleanest test of "location information the map does not have". Δ ≥ +0.01 ⇒ the prior transfers: scale the dose to 20 % (`w20` values are free). Δ ≤ −0.01 ⇒ the mask carries real recall and this axis is retired. \|Δ\| < 0.01 ⇒ no evidence; do not re-tune the fraction. |
| 2 | `…-PRUNEle15-norefill-20261023-1ca1ff6f.tif` (built earlier, still unsubmitted) | The only existing file with a *measured-algebra* path past +0.01 (+0.010 MODEL) and no new inputs. Independent of slot 1's outcome: if 1 is flat, this is the fallback with the best expected value. |
| 3 | `…-CONCENTRATIONgdr25m10-20261023-08bf80cf.tif` (primary scale/target pair, 2.5 km, all features) — **only if slot 1 is ≥ +0.005** | Confirms the mechanism at the wider prior and makes the 1 km arm interpretable. If slot 1 was flat or negative, skip it and use `…-PRUNEle8-norefill-20261023-e1dd69d0.tif` instead. |

Do **not** spend a slot on `gdr10m10` unless both 2.5 km arms are ≥ +0.01: the scale contrast
is worth less than a dose increase.

## Weeks to the deadline (2026-12-03, still unconfirmed on the competition page)

- **Wk 1 (now):** slot 1 = `gdr25rm10`. Paste the receipt into `ledger/submissions.csv`.
- **Wk 2:** follow the decision table above; at most one more scored file in the same rolling
  week as slot 1 (the entity gets three, not three per axis).
- **Wk 3–4:** if the prior transfers, build the 20 % dose (new `(CONCENTRATION, w20…)` pair,
  same prior, same seed, same collar) and take it; otherwise combine the two best
  *independent* levers on whatever parent has the best receipt.
- **Wk 5–6:** confirm on the best parent, build a fallback, re-validate both from disk
  (`scripts/validate.py` must print PASS on each), choose the final file blind.

## Better axes to propose (not built this session)

1. **PRIOR-BLEND at fixed count.** Combine the thermal prior with the lineage mask
   (`p = λ·thermal + (1−λ)·mask-smoothed`) instead of replacing one with the other, λ = 0.3.
   Mechanism: keeps recall on the mask while adding the independent signal; the two bounds
   above say a blend is the only version of this axis that can win on both truth models.
   Confounder: λ is a free knob; falsifier: λ = 0.3 and λ = 0.7 disagree in sign.
2. **COVERAGE-FLOOR.** Move 10 % but only from dots that duplicate an already-covered cell
   (a second dot within 3 px of the same field cell). Mechanism: spend the relocation on
   redundant mass only, so the H19-5 coverage loss measured here (88.6 % → 80.2 %) cannot
   happen. Confounder: pairs are how the lineage buys recall near trace ends.
3. **COLLAR-RESERVE.** The arms *lowered* the ≤3 px collar count (2,171 → 1,897). Test the
   opposite: hold the collar and let the collar-adjacent band (3–6 px) carry the thermal
   prior. Requires a decision on IR-91-03 first.

**Human must supply:** TOP_PUBLIC with a date, this week's slot count, the deadline
confirmation, R0's receipt for 0.2778, and a ruling on IR-91-03 (the 2 px vs 3 px collar).
