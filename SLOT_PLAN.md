# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (2026-10-24 UTC):** 40 days (5.7 rolling weeks ≈ 15–17 slots) to the **unconfirmed**
2026-12-03 deadline ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).
**Ledger:** 53 `BUILT`, **0 `SUBMITTED`, 0 live `RECEIPT`s** (R0 0.2778 = `CLAIM`).
**TOP_PUBLIC:** `____` (human fills, with date). **Slots left this week:** `__ / 3`.
`|Δ| < 0.01` = no evidence. This file is the forward plan only, merged across Sessions 8+9
(2026-10-24); per-session history lives in `README.md`, `evidence/`, mechanism cards.

## ⚠ The binding constraint is receipts, not candidates (IR-91-38)

Nine sessions, 53 gate-clean files, zero live measurements. **No further build session should
run until the Week-1 receipts below are pasted into `ledger/submissions.csv`** — every queue in
this repo is `MODEL`s anchored to an unreceipted `CLAIM`.

## What the two 2026-10-24 sessions established (all `PROXY`/`MODEL`, no receipts)

- **Catalogue-collar enrichment loses on the independent control** (Session 8 built it:
  `collar10` −2.0 %, `collar20` −3.9 % SGMC rel, worse than uniform −0.66 %; mirror `anti10`
  +2.1 %). Session 9 screened the same family independently (relT −1.1 %) and left it unbuilt.
  But no local instrument can truly test it (IR-91-33): the SGMC control cannot reward collar
  placement, so the question stays open until a `le10` receipt speaks to collar cost.
- **Coverage beats clustering at fixed count** (Session 9 `redcov10`: exact SGMC relT +7.7 %
  moving the most kernel-redundant dots to supported uncovered cells, donors/recipients at
  matched catalogue distance). Selection-on-surrogate disclosed + shrunk (IR-91-37).
- **MASS is measured exhausted** at constructible rankings (IR-91-36); **`gdr25rm10`'s +0.0123
  is the prior scored against itself** (IR-91-34) and is demoted out of the queue.

## Next 3 scored slots, in order (one orthogonal mechanism each)

| # | File (`releases/`, rebuild per `docs/SUBMIT.md`) | Pred. Δ (`MODEL`) | What the receipt changes |
|---:|---|---|---|
| 0* | **R0 anchor** (pinned `baeae321…`) — *only if no receipt held for these exact bytes* | — | Denominator for every Δ below. Cheapest information available; no axis substitutes. |
| 1 | `h33-h33-2-b2-SPACINGredcov10-20261024-8113d448.tif` (37,654) | **+0.011** `[−0.003,+0.021]` | `≥ +0.010` → coverage binds: bracket `redcov20` (`191caf71`) Week 2. `≤ 0.000` → truth sits where R0 clusters: retire coverage family, promote `SPACING/clump40`. |
| 2 | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` (26,294) | **+0.008** | Only algebra-signed arm (zero-credit dots cost `0.2·(1−m)` each). `≥ +0.010` → rebase winners on pruned parent. `≤ −0.010` → near-catalogue dots are gold despite IR-91-33's blind control: `collar10` (`00cfbe95`, already built) becomes the test. Ambiguous middle → `anti10` reserve. |
| 3 | `h33-h33-2-b2-MASScons3add-20261023-2803126d.tif` (41,419) | **+0.009** | Count-up direction. Session 8's numerator-asymmetry argument vs Session 9's precision screen (recipients 11.3 % vs 11.8 % break-even) disagree by construction — the receipt settles which. With slot 2, brackets the optimum vs 37.7 k dots. |

Reserves in order: `CONCENTRATIONanti10` (`0e42d6ab`, +0.006; only arm that settles
collar-vs-remote at matched dose) → `RELIEFr2p12` (`6ff08e5c`, +0.006) → `gdr25rm10` (demoted,
IR-91-34) → `SNAPs2c` (retirement test). `TRACKB` spends a slot only on an explicit human
Phase-2 ruling. Never spend 2 slots on one ladder (`redcov10/20/10v2`, `collar10/20`, cons drops).

## Weeks to the deadline

- **Week 2:** dose-bracket only Week-1 `≥ +0.010` winners (`redcov20`, `le15`, or count ladder);
  at most one decomposition arm (`redcov10v2` / `anti10`) if its parent arm receipts ≈ 0.
- **Weeks 3–4:** compose two *orthogonal receipted* winners one step at a time. No composing
  unreceipted `MODEL`s.
- **Weeks 5–6:** re-verify best receipted file + fallback (R0/`-zeros`) from disk, pick the one
  blind final, freeze ≥ 2 slots unused as format insurance.

## Proposed better axes (not built; triggers stated)

1. **Coverage ADD family** (convergent proposals, Sessions 8+9): add dots at supported cells
   > 3 px from every existing dot — Session 8's substitution-ranked add and Session 9's
   `fieldcov` (recipients maximise uncovered lineage-field mass) / `reddrop` (redcov donors,
   delete-only). *Mechanism:* per-truth-pixel max ⇒ marginal credit lives in kernel gaps.
   *Confounder:* gaps may be genuinely absent traces; lineage-referenced objectives are
   circular as validators (IR-91-34) — screen on SGMC only. *Falsifier:* screened fixed-count
   relT ≤ redcov10's +7.7 % ⇒ do not build. *Trigger:* redcov10 receipt (either sign) in hand.
2. **Along-strike tip extension** (Session 8): mass 3–6 px beyond mapped-trace *terminations*,
   not flanks. *Mechanism:* "new fault" includes new geometry of existing systems; tips/step-overs
   are where it appears. *Confounder:* 1:250 k trace ends are often cartographic. *Caution:*
   Session 9's dot-pair tip-extension *swap* screened −6.3 % relT — build only if the
   catalogue-endpoint version beats `collar10` by ≥ +0.006 on SGMC screening first.
3. **PRUNE collar-cost titration** (Session 8): exclusion radius 1–6 px in 0.5 px steps at fixed
   count. *Mechanism:* brief §4.4's 3 px floor is a hypothesis about the scorer, not a
   measurement. *Confounder:* refills move location with collar membership. *Falsifier:* no
   monotone receipt trend closes the collar question from the cost side. *Trigger:* `le10`
   receipt ambiguous (|Δ| < 0.010).
