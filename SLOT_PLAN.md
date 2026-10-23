# SLOT PLAN — after the cross-check (2026-10-23)

**Parent R0** `h33-h33-2-b2`, 37,654 unit-mass dots, 2.236 px collar floor. R0's `0.2778` is a
**CLAIM** — this lineage has 32 ledger rows and **zero receipts**.

The board, in one line: **12 pairs shipped and byte-reproducible** (6 PRUNE doses, 3 RELIEF arms,
3 SPACING arms), all 14/14 gates, all in `releases/MANIFEST.json`, none ever submitted.
The human spends the slots; nothing here uploads.

## The measurement that reorganises the plan (IR-91-21)

Scoring every shipped file against the only truth visible from this sandbox — the 60,988-cell
catalogue — and decomposing the metric into credit *T* and unmatched mass:

| band to nearest catalogue cell | dots | share | share of measurable credit `T` |
|---|---:|---:|---:|
| **0–3 px** | 1,611 | 4.3 % | **100 %** |
| 3–5 px | 3,237 | 8.6 % | 0 % |
| 5–10 px | 6,292 | 16.7 % | 0 % |
| 10–20 px | 7,908 | 21.0 % | 0 % |
| 20–40 px | 8,454 | 22.5 % | 0 % |
| ≥ 40 px | 10,152 | 27.0 % | 0 % |

- R0: `dti_proxy` **0.006778**, `T` 381.9, `M` 277.9.
- **Every PRUNE dose computes to `T = 0`, `dti_proxy` 0.000000** — `le3` deletes exactly the band
  that carries all of it, and every deeper dose deletes that band too. On this instrument the
  whole ladder is −100 %.
- Break-even, exactly: deleting one unit-mass dot raises DTI iff `K < 0.2·DTI·(1−m)/(1−0.2·DTI)`
  = **0.044 credit** at DTI 0.2778 with the parent's own `m = 0.25`. The 1,611 collar dots average
  **0.237** — five times the bar; the other 36,043 score 0 *on mapped faults only*.
- RELIEF's arm ordering is reproduced independently: `r2m15 −0.00089 > null15 −0.00103 >
  m2r15 −0.00096` — the same order the mechanism cards predict.
- **`SPACINGspread40` is the only shipped arm that raises measurable credit**: `T` 381.9 → 442.9
  (+16 %), `dti_proxy` +0.00108.

The consequence: the PRUNE ladder is not a statement about "dose", it is one conditional claim —
*the organisers' new faults lie nowhere near the parent's dots*. Nothing in this sandbox can test
that, so the ladder's six doses are six bets on the same coin, and the first receipt is read as a
test of the claim, not as a point on a curve.

## Next three scored slots (in order)

| # | candidate | MODEL prediction | why this slot |
|---|---|---|---|
| 1 | **`PRUNE-le15-norefill`** (`1ca1ff6f`) | **+0.010** [−0.008, +0.024] | The only file on the board whose range crosses **+0.01**, the brief's evidence bar. Doses are not independent (they all delete the collar band), so a deeper dose buys no extra *safety* — only extra signal. One receipt, either sign, retires or validates the family. |
| 2 | **`SPACINGspread40`** (`6d389309`) | +0.004 [−0.004, +0.012] | The only arm that *adds* measurable credit rather than deleting it, and it is arrangement-only, so its sign is independent of slot 1's. If slot 1 is flat or negative this is the best remaining idea; if slot 1 wins it is the natural second axis to combine. |
| 3 | **conditional — see the fork below** | — | `PRUNE-le10` to confirm monotonicity after a win; the `RELIEF` **pair** (`r2m15` then `null15`) only if slots are free, because ±0.007 alone is below the bar and the pair costs two slots. |

**Do not** spend a slot on `le3`/`le4`/`le5`/`le8` until slot 1 returns: they delete the same
0–3 px band, so they cannot answer a question slot 1 leaves open, and each is smaller than the
0.01 bar by its own MODEL. Six doses are built; more builds are not the bottleneck.

## The fork, written before the receipt arrives

| slot-1 result | what it means | slot 2 | slot 3 |
|---|---|---|---|
| **≥ +0.01** | mass far from mapped faults is genuinely wasted; the collar band is worth less than its cost | `PRUNE-le10` (confirm monotone) | `SPACINGspread40`, then combine the two winners into one file for the final blind pick |
| **+0.002 … +0.01** | right direction, wrong size — consistent with IR-91-21's warning | `SPACINGspread40` | `le10` only if a second slot is free |
| **−0.002 … +0.002** | **no evidence** (the brief's rule). Do not read this as "PRUNE neutral" | `SPACINGspread40` | RELIEF pair if two slots remain, else stop building and re-verify the final file |
| **≤ −0.01** | the collar band pays; the organiser's 300 m clause is about their mapping, not the metric | stop deleting. `SPACINGspread40` | build the **add-in-collar** arm (3–8 px) and submit it |

Whatever happens, paste `receipt_score` + `receipt_date` into `ledger/submissions.csv`, set
`status=SUBMITTED`, and never overwrite `predicted_change`. Treat a change inside ±0.01 as
**no evidence** — the public chunks are small.

## Weeks to the deadline (2026-12-03, unconfirmed by a human)

- **Wk 1 (now):** slot 1 = `le15`, slot 2 = `SPACINGspread40`. Read both against the fork table.
- **Wk 2:** slot 3 per the fork. If both came back flat, stop spending slots on new axes and
  spend one on a **repeat of the best-scoring file at a different dose** only if the fork says the
  direction is live; otherwise hold slots and bank the best receipt.
- **Wk 3–4:** combine the two winners (PRUNE dose + SPACING spread is the cheapest combination:
  arrangement does not change which cells exist at the collar). Build the combination as a *new*
  `(parent, axis, value)` triple so the ledger stays honest.
- **Wk 5–6 (by 2026-12-03):** re-validate the final file from disk (`validate_raster.py` → PASS,
  `update_release_manifest.py --check` → 0 problems), ship it with its `-zeros` twin held as the
  fallback, and make the final choice **blind** — with no fresh private-chunk feedback.

## What would change my mind

- A receipt for **R0 itself** (any dated leaderboard row). It settles IR-91-22 — whether 0.2778 is
  the right scale — and would let every prediction in the ledger be recalibrated.
- A human-supplied **ranking artifact** for the parent's dots. That alone makes MASS (drop lowest
  10 % / add next 10 % by the parent's own ranking) buildable; it is currently unbuildable for a
  documented reason, not for lack of time (IR-91-23).
- Any sign that the organisers' truth extends **within 300 m of the catalogue**, which would invert
  IR-91-21 and make every PRUNE dose a loss.

## Later axes, in the order I would build them

1. **MASS with a real rank** (blocked, IR-91-23) — the experiment the axis was supposed to be.
2. **CONCENTRATION at 2 km on a licensed prior** — needs a priors file whose licence permits
   sponsor sharing; the two candidate rasters in `registry/` are marked *licence unchecked* and are
   therefore **not** usable as build inputs.
3. **RELIEF as a matched pair** — only worth a slot if a pair is free; single arms are below the bar.
4. **TRACKB** (Phase-2 submission), only after at least one receipt exists.

## What the human must supply

`TOP_PUBLIC` with its date · slots remaining this week · confirmation of the deadline · any
leaderboard row for R0 · the parent's ranking artifact if it exists. Do not contact
drivendata.org, the leaderboard, or dropbox.com from this repo — the human reads the numbers.
