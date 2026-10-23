# SLOT PLAN — combined PRUNE queue (2026-10-23)

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
