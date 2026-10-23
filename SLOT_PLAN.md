# SLOT PLAN — state after 2026-10-23, merged (PRUNE queue + MASS/consensus, PR #14)

**Status: 35 BUILT rows, 0 SUBMITTED, 0 receipts.** R0's 0.2778 is a CLAIM. With no live
number anywhere, every prediction below is MODEL and the brief's rule stands: a live |Δ| under
0.01 is **no evidence**. This session added the MASS axis; PRUNE arms came from the merged PR.

MASS had to substitute its ranking: the parent's own continuous ranking is not recoverable from
pinned bytes (IR-91-19). It is ranked by cross-field support over the three pinned lineage fields
(measured on R0: 26,913 / 6,200 / 4,541 dots at support 3 / 2 / 1), in whole strata so no arm
needs a tie-break. Break-even precision is 11.8 % (IR-91-20), so every arm is a ±0.01 bet.

## The one ruling that decides the queue (IR-91-03)

R0 keeps 2,171 dots at 2–3 px from the catalogue, so **R0 itself fails** the brief's 3 px collar.
- **Collar binds new mass only** → the MASS arms are testable and slot 2 is `MASScons3add`.
- **Collar binds every file** → no non-PRUNE child of R0 can ship, slot 2 becomes
  `PRUNEp2p9h19cover`, and MASS waits for a PRUNE-rebased parent.

Slot 1 does not depend on this ruling: `AXIS=PRUNE` is the brief's own exemption.

## Next three scored slots, in order

| # | candidate (built?) | file / sha8 | predicted (MODEL) | what the receipt changes |
|---|---|---|---|---|
| 1 | `PRUNE/le10-norefill` — delete-only 10 px collar, 26,294 dots (built, merged) | `…-PRUNE-le10-norefill-20261023-04002dae` | **+0.008** [−0.006, +0.019] | ≥ +0.01: far-from-catalogue mass is mostly denominator cost → slot 3 escalates to `le15`. Flat: no evidence; stop buying PRUNE doses and use slot 3 on the MASS pair. |
| 2 | `MASS/cons3add` — add 10 % (3,765 dots) at the best-supported unspent cells, strictly >3 px off catalogue (built) | `…-MASScons3add-20261023-2803126d` | **+0.009** [−0.002, +0.019] | ≥ +0.01: the d2.8 thinning was too aggressive → slot 3 extends the dose (`cons3add20`, new value, pre-registered). ≤ −0.005: retires the support ordering in the add direction and, with a flat slot 1, retires MASS for the season. **Replaced by `p2p9h19cover` if the collar ruling goes against non-PRUNE children.** |
| 3 | decided by slots 1–2: `PRUNE/le15-norefill` if slot 1 gained; else `MASS/cons1drop` (built, MODEL −0.000) as the paired opposite direction | `…-PRUNEle15norefill-…` / `…-MASScons1drop-20261023-fc8f5500` | +0.010 / −0.000 | Slot 3 is not spent blind: it is chosen by the two receipts. If both were flat, `cons1drop` still identifies whether the support ordering carries signal at all. |

Do **not** spend a slot on: `MASS/cons2drop` (nested deeper cut of `cons1drop`), `p4.5px-h19cover`
(MODEL −0.015, an explicit falsifier only), any `SPACING` arm (bound ≤0.003), any new
`CONCENTRATION` arm (IR-91-22: R0's 10 px block-density CV is already 0.531, inside the reported
0.51–0.59 band, and all four existing CONC rows moved CV *up* to 1.02–1.36), `SNAP` ≤2 px
(±0.002, nine rows), or `RELIEF` (its declared inputs contain no elevation band).

## Weeks to the deadline (2026-12-03, unconfirmed on the competition page)

- **Wk 1 (now):** human rules on IR-91-03, fills TOP_PUBLIC + slots, submits slot 1 (`le10`).
  Paste `receipt_score` + `receipt_date` the same day: 35 builds and zero receipts is the
  single biggest weakness in this repository.
- **Wk 2:** slot 2 per the ruling. Read slots 1–2 as a pair: one PRUNE receipt and one MASS
  receipt is the first measurement this lineage has ever had of *which* axis matters.
- **Wk 3–4:** slot 3 as decided above; then, with receipts in hand, combine the winning axis
  rather than opening a new one. A second axis only after one has cleared +0.01.
- **Wk 5–6:** confirm the strongest file, build its fallback twin, re-validate both from disk,
  and choose **one** final file blind. No agent submits; one entity, three scored files a week.

## Proposed axes for later sessions — NOT built here (mechanism / confounder / falsifier)

1. **FRACTIONAL-MASS at fixed geometry.** Emit 0.5 instead of 1.0 on the lowest-support half of
   R0's dots. Mechanism: mass is nearly free within 2.83 px of truth (a dot's own match discounts
   its own penalty), so half-credit on doubtful ground keeps ~half the upside and halves the
   penalty. Confounder: the organiser's reader may reject or threshold non-binary values — **the
   sample template is binary and this is unverified**. Falsifier: a validation error, or a score
   that moves like a pure prune.
2. **SUPPORT-GRADED REFILL.** Use support-2 and support-1 cells as refill material for a collar
   prune, holding mass constant while changing its precision mix. Confounder: it is neither a
   PRUNE (collar not tested) nor a MASS (total mass unchanged) — label it honestly. Note the
   merged finding that fixed-count refill under a preserved d2.8 exclusion is infeasible
   (IR-91-18); this design would have to drop that exclusion and say so.
3. **RELIEF, once a real elevation band exists.** `axis_requirements.RELIEF` lists
   `ext_lidar_scarp_u8`, a scarp-detection product, not detrended elevation, so the axis as
   briefed cannot be built from it. Needs the DEM-derived bands the human holds.

**Human must supply:** the IR-91-03 collar ruling (it reorders the queue), TOP_PUBLIC with the
date it was read, slots remaining this week, the 2026-12-03 deadline confirmation, and a receipt
per slot. Nothing here justifies an unconfirmed submission beyond the three files above.

---

## Appendix — the merged PRUNE queue (unchanged, from PR #10)

**Parent R0:** `h33-h33-2-b2`, 37,654 dots; both encodings now rebuild byte-exactly.
R0's 0.2778 is **CLAIM**. Ledger: **32 BUILT, 0 SUBMITTED, 0 receipts**. All predictions
below are **MODEL**, not scores; live |Δ|<0.01 is **no evidence**. TOP_PUBLIC, remaining
weekly slots, and the deadline still require human confirmation.

## Next three scored slots, in order

| order | candidate / sha8 | changed; N | prediction | decision it buys |
|---|---|---:|---:|---|
| 1 | **`PRUNE-le10-norefill` / `04002dae`** | 30.17%; 26,294 | **+0.008** [−0.006,+0.019] | Largest positive delete-only dose. Tests whether far-from-catalogue mass is mostly denominator cost. |
| 2 | **`PRUNEp2p9h19cover` / `9829bb66`** | 4.278430%; 37,654 | **+0.004** [−0.005,+0.013] | Complementary fixed-count test: move the below-3 px tail to exact marginal-DTI H19-5 cells without changing mass. |
| 3 | **`PRUNE-le4-norefill` / `360fe57e`** | 10.16%; 33,829 | **+0.003** [−0.003,+0.009] | Brackets the large-dose result and isolates the 3–4 px collar. |

Upload one encoding per slot; the zeros twin is a fallback, never another entry. Full
filenames, SHA-256 values, byte lengths, and ≤140-character notes are in `docs/SUBMIT.md`
and the two release manifests.

## Receipt conditions

- **Slot 1 ≥ R0 + 0.01:** mass far from known faults is costly. Keep slot 2 as the
  mass-held contrast; use slot 3 to locate the lower dose rather than escalating blindly.
- **Slot 1 flat:** this is no evidence. Slot 2 still tests placement at fixed mass, but do
  not claim a PRUNE dose-response from flat public chunks.
- **Slot 1 ≤ R0 − 0.01:** the 10 px halo carries truth; stop wide pruning. Replace slot 2
  with the smaller **`p2.5` (`e6f2000d`, +0.002 MODEL)** if a below-3 px test is still worth
  a slot. Do not use `p4.5`.
- **After slots 1–2:** use `le4` only if it can distinguish a dose/placement hypothesis.
  If both receipts are losses, leave the third slot unused rather than spending it on a
  predicted loser. **`p4.5` (`691438f8`, −0.015 MODEL)** is only an explicit falsifier for
  unexpectedly strong fixed-count gains; it is not in the default queue.

## Weeks to deadline (human must confirm date)

- **Now:** human confirms TOP_PUBLIC/date and rolling-week capacity, then submits slot 1.
  Paste score/date into the ledger the same day. One entity, at most three scored files per
  rolling week; no agent submissions or leaderboard automation.
- **Following slots:** apply the conditions above. Never use catalogue hide/recover,
  SGMC, or the leakage canary as a score gate; they are report-only diagnostics.
- **Later:** with a verified ranking input, test MASS-SHAPE/refill at the winning collar.
  Otherwise use a licensed external prior for CONCENTRATION, or a one-way SPACING/RELIEF
  follow-up. No lattice/region-isolated test-location designs.
- **By the real deadline:** human re-verifies and blind-picks one final file plus a local
  fallback. There is still no R0 receipt, so do not call any variant receipt-proven best.

## Mechanism limits

The fixed-count refill cannot preserve R0's inherited d2.8 inhibition spacing at these
counts: only 722/621/498 legal cells remain versus 941/1,611/4,848 needed. The disclosed
PRUNE amendment therefore drops that extra rule and measures nearest-neighbour drift;
`SLOT_PLAN.md` and the mechanism cards carry this limitation. Delete-only variants instead
confound placement with mass loss. The two families are complementary, not interchangeable.
