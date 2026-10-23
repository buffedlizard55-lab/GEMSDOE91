# SLOT PLAN — state after 2026-10-23 session 4 (MASS / cross-field support)

**Status: 3 variants built; every MUST gate passes; the 4.4 collar is inherited-not-cleared (IR-91-03). 0 receipts.** The ledger now
holds 29 BUILT rows and **not one live score**. R0's 0.2778 is still a CLAIM. That single fact
dominates the plan: with no receipt, every model below is unanchored, and the brief's own rule —
a live change under 0.01 is no evidence — applies to all of them.

The session-4 arms had to substitute a ranking: the parent's own continuous ranking is not
recoverable from pinned bytes (IR-91-17). MASS is ranked by cross-field support over the three
pinned lineage fields (measured on R0: 26,913 / 6,200 / 4,541 dots at support 3 / 2 / 1).
Break-even precision for any mass edit is 11.8 % (IR-91-18), so every arm is a ±0.01 bet.

## Next three scored slots, in order

| # | candidate (built?) | file / sha8 | predicted (MODEL) | what the receipt changes |
|---|---|---|---|---|
| 1 | `MASS/cons3add` — add 10 % (3,765 dots) at the best-supported unspent cells, ≥3 px off catalogue (built) | `…-MASScons3add-20261023-2803126d` | **+0.009** [−0.002, +0.019] | ≥ +0.01: the d2.8 thinning was too aggressive → slot 3 extends the dose (`cons3add20`, new value, pre-registered). Flat/negative: mass is not the constraint and the support ordering has no add-direction signal. |
| 2 | `MASS/cons1drop` — drop the 4,541 single-support dots, count 33,113 (built) | `…-MASScons1drop-20261023-fc8f5500` | **−0.000** [−0.013, +0.007] | The paired opposite direction: together with slot 1 it brackets the ordering for ±0.01. Gain ⇒ single-field mass is net-negative; loss ≥0.01 ⇒ the unique-interpretation dots carry real credit, and MASS/consensus must not be used to cut. |
| 3 | `PRUNE/le15-norefill` — delete-only 15 px collar, 21,989 dots, **rebuild first** (`1ca1ff6f`) | `…-PRUNEle15norefill-20261023-1ca1ff6f` | **+0.010** [−0.008, +0.024] | The only other rung with a plausible path past +0.01, and it tests a different claim: whether the 3–15 px shell (zero catalogue credit, 14,054 of 15,665 dots) carries new-fault truth. Taken only if slots 1–2 are both flat; if slot 1 succeeded, spend the slot on `cons3add20` instead. |

Do **not** spend a slot on: `MASS/cons2drop` (nested deeper cut of slot 2 — same information,
larger dose; keep as the confirmation arm), any `SPACING` arm (bound ≤0.003, session 3), any new
`CONCENTRATION` arm (IR-91-20: R0's 10 px block-density CV is already 0.531, inside the reported
0.51–0.59 best-file band, and all four existing CONC rows moved CV *up* to 1.02–1.36), any
`SNAP` ≤2 px displacement (±0.002, nine rows, none receipt-backed), or `RELIEF` (its declared
inputs contain no elevation band — see below).

## Weeks to the deadline (2026-12-03, unconfirmed on the competition page)

- **Wk 1 (now):** spend slot 1 on `cons3add`. Paste `receipt_score` + `receipt_date` into
  `ledger/submissions.csv` the same day — 29 builds and no receipts is a broken feedback loop.
- **Wk 2:** slot 2 (`cons1drop`), read as a pair with slot 1. If both sit inside ±0.01, MASS is
  retired as a lever and slot 3 goes to `PRUNE/le15`.
- **Wk 3–4:** `cons3add20` (add 20 %, new value) if the add direction won; otherwise `le8` vs `le15`
  to map the collar dose-response. Only these two axes have any mechanism left.
- **Wk 5–6:** confirm the strongest single axis, build a fallback twin, re-validate the format of
  both from disk, then choose **one** final file blind. No agent submits; no agent submits from
  more than one entity.

## Proposed axes for later sessions — NOT built here (mechanism / confounder / falsifier)

1. **FRACTIONAL-MASS at fixed geometry.** Emit 0.5 instead of 1.0 on the lowest-support half of
   R0's dots. Mechanism: the algebra makes mass nearly free where a dot is within 2.83 px of
   truth (the dot's own match discounts its own penalty), so a half-credit dot on doubtful ground
   keeps ~50 % of its upside and halves its penalty. Confounder: the organiser's reader may
   threshold or complain about non-binary values — **unverified, and the sample template is
   binary**. Falsifier: a validation error or a score that moves like a pure prune.
2. **SUPPORT-GRADED REFILL.** Use support 2 and 1 cells as refill material for a collar prune, so
   mass is held constant while its *precision* composition changes. Confounder: refill is not a
   PRUNE (does not test the collar) and not a MASS (does not change total mass) — label honestly.
3. **RELIEF, once a real elevation band exists.** `axis_requirements.RELIEF` currently lists
   `ext_lidar_scarp_u8`, which is a scarp-detection product, not detrended elevation; the axis as
   briefed cannot be built from it. Needs the DEM-derived bands the human holds.

**Human must supply:** receipt scores + dates for at least slots 1–2; `TOP_PUBLIC` with the date
it was read; slots remaining this week; confirmation of the 2026-12-03 deadline. Nothing here is
PROXY- or MODEL-supported enough to justify an unconfirmed submission beyond the three files above.
