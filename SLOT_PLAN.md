# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (2026-10-24 UTC):** 40 days (5.7 rolling weeks ≈ 15–17 slots) to the **unconfirmed**
2026-12-03 deadline ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).
**Ledger:** 50 `BUILT`, **0 `SUBMITTED`, 0 live `RECEIPT`s** (R0 0.2778 = `CLAIM`).
**TOP_PUBLIC:** `____` (human fills, with date). **Slots left this week:** `__ / 3`.
`|Δ| < 0.01` = no evidence. Per-session history lives in `README.md`, `evidence/`,
`ledger/variant-cards*`, `reports/` — this file is only the forward plan.

## ⚠ The binding constraint is receipts, not candidates (IR-91-35)

Eight sessions have built 50 gate-clean files and measured nothing live. Every prediction in the
fleet is a `MODEL` against an unreceipted `CLAIM`. **No further build session should run until at
least the Week-1 receipts below are pasted into `ledger/submissions.csv`** (`receipt_score`,
`receipt_date`) — otherwise session 9 re-derives this same queue blind.

## Next 3 scored slots, in order

| # | File (`releases/`, rebuild per `docs/SUBMIT.md`) | Pred. Δ (`MODEL`) | What the receipt changes |
|---:|---|---|---|
| 0* | **R0 anchor** `gemsdoe32-h33-h33-2-b2-…-e5eb6e7e-nan.tif` (pinned `baeae321…`) — *only if the human holds no receipt for these exact bytes*; else free | — (denominator) | Converts every other receipt into a Δ. Without it, deltas vs the 0.2778 `CLAIM` are uninterpretable. |
| 1 | `h33-h33-2-b2-SPACINGredcov10-20261024-8113d448.tif` (37,654 dots) | **+0.011** `[−0.003,+0.021]` | Kernel-redundancy→coverage (session 8; strongest methodology in fleet: exact metric on independent control, shrunk; IR-91-34). `≥ +0.010` → coverage binds: bracket `redcov20` (`191caf71`) in Week 2. `≤ 0.000` → truth sits where R0 clusters: retire coverage family, promote `SPACING/clump40` (sign flip, already built). |
| 2 | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` (37,654) | **+0.0123** | External GDR thermal prior transfer. `≥ +0.010` → dose 15–20 % Week 2. `≤ −0.010` → retire CONCENTRATION. (Its MODEL came from a partly circular instrument, IR-91-19 — hence slot 2, not 1.) |
| 3 | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` (26,294) | **+0.008** | Collar direction: are ≤10 px dots denominator waste? `≥ +0.010` → rebase Week-2 winners on a pruned parent. `≤ −0.010` → near-catalogue dots are gold (new geometry of existing systems): build the contingent ring-enrichment arm (screened session 8, deliberately unbuilt pending this receipt). |

Reserves, already built, in order: `RELIEFr2p12` (`6ff08e5c`, +0.006) → `MASScons3add`
(`2803126d`, +0.009 MODEL but screened sub-break-even on SGMC precision this session, IR-91-33) →
`SNAPs2c` (`86b27de1`, +0.000, axis-retirement test only). `TRACKB` (`8343ab38` first) spends a
slot only if the human rules Phase-2 expert review outweighs a DTI read.

## Weeks to the deadline

- **Week 2:** dose-bracket any Week-1 `≥ +0.010` winner only (`redcov20`, GDR 15–20 %, or
  `PRUNE-le15`); one decomposition arm at most (`redcov10v2` if redcov10 ≈ 0).
- **Weeks 3–4:** compose two *orthogonal receipted* winners one step at a time onto the receipted
  parent (e.g. coverage × prune). No composition of unreceipted MODELs.
- **Weeks 5–6:** re-verify best receipted file + conservative fallback (R0 / `-zeros` twin) from
  disk, choose the **one blind final**, freeze. Keep ≥ 2 slots unused as insurance against a
  format surprise.
- Missing axis families from the fleet by design: none unbuilt except the contingent ring arm
  above and the proposals below. MASS is *measured* exhausted at constructible rankings
  (IR-91-33); SNAP is measured negative on its control (IR-91-28..30).

## Proposed better axes (not built; build only on the stated trigger)

1. **`MASS/reddrop`** — delete-only version of redcov10's donors (33,889 dots, no refill).
   *Mechanism:* if redundant dots are pure denominator cost, deletion alone should score
   ≥ redcov10 − recipient value; it decomposes the swap. *Confounder:* same count as
   `MASS/m10minus` but near-disjoint dot set — receipts must not be conflated. *Falsifier:*
   receipts `< R0 − 0.005` while redcov10 `≥ +0.010` ⇒ all the value was recipients.
   *Trigger:* redcov10 receipt in hand (either sign).
2. **`SPACING/fieldcov`** — recipients maximise *uncovered lineage-field mass* within the 3 px
   kernel (vote-weighted), not raw distance-to-dot. *Mechanism:* DTI pays per truth pixel;
   lineage field pixels are the only truth-free stand-in for where fault length may sit.
   *Confounder:* optimises toward the lineage's own false positives at field edges.
   *Falsifier:* fixed-count exact SGMC relT does not beat redcov10's +7.7 % in screening —
   then do not build. *Trigger:* redcov10 `≥ +0.010` (coverage confirmed worth refining).
3. **Catalogue-ring enrichment (`CONCENTRATION`, catalogue-density prior)** — screened session 8
   (exact SGMC relT −1.1 %: ring recipients duplicate surviving collar coverage) and left unbuilt
   *on purpose*. *Trigger:* only a `PRUNE-le10` receipt `≤ −0.010`, which would prove the SGMC
   redundancy reading wrong for live truth. *Falsifier:* built only in that world; receipts
   `≤ le10` there retires catalogue proximity in both directions.
