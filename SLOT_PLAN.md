# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (`2026-10-24` UTC):** `40 days` (`5.7` rolling 7-day weeks = `15–18` scored slots) to
the **unconfirmed** `2026-12-03` deadline — confirm it on the competition page. **Ledger:** `53`
`BUILT`/`GATED` rows across seven axis families, **`0` SUBMITTED, `0` live `RECEIPT`s**;
`R0 = 0.2778` is a `CLAIM`. Never use multi-account feedback; `|Δ| < 0.01` = no evidence.
Session detail lives in `docs/MECHANISM_CARDS*.md` and `ledger/`; this page is only the plan.

## Blockers the human must clear (no AI can)

1. **`TOP_PUBLIC` + date.** Until it is filled no target number exists. If `TOP_PUBLIC ≳ 0.35`,
   **no built row has a predicted path to it** (best MODEL projection anywhere in the ledger is
   `+0.017`) and this is the wrong plan: the answer would be Phase-2 trace quality (`TRACKB`) plus
   a new locator, not another ±0.01 dose.
2. **R0 receipt.** One slot on R0 converts the whole fleet's baseline from `CLAIM` to `RECEIPT`.
   Every prediction here is relative to an unverified number.
3. **Slots left this week**, and the `IR-91-03` collar ruling (R0 breaks §4.4 at 2.236 px).

## Next 3 scored slots, in order (merged from the collar and MASS sessions)

| Slot | Upload (`releases/`) | Dots | Pred. (`MODEL`) | What the receipt changes |
|---:|---|---:|---|---|
| **1** | **R0 anchor** — `data/registry/GEMSDOE32__h33-2-b2-zeros.tif` | 37,654 | `0.2778` `CLAIM` | Cheapest information in the plan and no axis substitutes for it: it turns the baseline into a `RECEIPT` and gives all three predictions a denominator. Skip only if a receipt already exists. |
| **2** | `h33-h33-2-b2-MASSa25adj-20261024-c658eb33.tif` | 47,068 (+25.0 %) | **+0.017** `[−0.009,+0.085]` | The recall direction at the first dose above 10 %: \`p*≈2–4 %` break-even vs ~12 % for the lineage's own cells. `Δ ≥ +0.010` ⇒ mass is the binding constraint: week 2 pushes to the 50 % ceiling and rebases the best receipt onto it. `≤ −0.010` ⇒ the denominator punishes unmatched mass harder than `0.2(S−M)` allows: retire MASS. |
| **3** | `h33-h33-2-b2-MASSa12spc-20261024-d466d2ac.tif` | 42,361 (+12.5 %, no 8-adjacency anywhere) | **+0.005** `[−0.003,+0.025]` | Matched-count geometry control and the safest fallback file for the final pick (its texture is identical to R0's). Matches slot 2's dose response ⇒ the effect is *count*, not clustering; underperforms ⇒ clustering on accepted mass is the active ingredient. If the human prefers a second mechanism over a control, swap in `PRUNE-le10-norefill` (`04002dae`, +0.008, algebra-signed). |

Reserves, in order: `PRUNE-le10-norefill` (`04002dae`), `PRUNE-le15-norefill` (`1ca1ff6f`, largest
dose in the 1–50 % band), `CONCENTRATIONanti10` (`0e42d6ab`, the one arm that would settle
collar-vs-remote), `MASSa12adj` (`d3de6292`, the dose anchor that makes slot 2 a slope).

**Do not spend a slot on** `CONCENTRATIONgdr25rm10` (`c19adb01`, +0.0123 MODEL): its prediction is a
shrinkage of a prior scored against itself, and the collar session measured that relocation answers
to exactly that circularity. `SNAP` stays out (IR-91-28..30); the `collar10/20` arms are predicted
losses.

## Rolling budget to the deadline (`5.7` weeks)

- **Week 1 (slots 1–3):** the table above — baseline + recall dose + matched control.
- **Week 2 (slots 4–6):** if slot 2 ≥ +0.010, bracket it (`+50 %` adjacent = the §5 ceiling, and the
  same rule extended to the vote-2 stratum); if flat, stop spending on count and take
  `PRUNE-le10` / `le15` to fix the deletion direction.
- **Weeks 3–4 (slots 7–12):** compose the two best *receipted* axes one step at a time onto a
  receipted parent (`MASS` winner × `PRUNE` winner, or × `CONCENTRATIONanti10` if the collar wins).
- **Weeks 5–6 (slots 13–18 + 1 blind final):** re-validate both encodings of the best file and the
  fallback on disk, then pick **one** blind final file.

## Proposed better axes (not built this session)

1. **`MASS × PRUNE` composition** — thin the lowest-ranked 12 % *and* add the top 25 % in one build.
   Mechanism: precision and count move together, which is what the algebra rewards; confounder: two
   changes cannot be attributed, so it may only be built on a receipted parent; falsifier: fails to
   beat the better of its two parents by +0.010 live.
2. **`SGMC-ANCHORED EXPANSION`** — use the off-catalogue USGS state-map faults as the acceptor field
   (R0's dots are 1.6× enriched on it, and 1.18× at the stacked MASS cells). Mechanism: independent,
   public-domain fault geometry that is *not* the competition catalogue
   ([USGS DS-1052](https://pubs.usgs.gov/ds/1052/)). Confounder: compilation scale and regional
   coverage vary, so a gain can be a survey artefact. Cost: **it retires the only independent control
   in this repo** — that trade is the human's decision, not an AI's.

## Tested and rejected (do not rebuild)

- **Global translation / re-registration** (shift all dots ±2 px): enrichment of R0's dots against
  off-catalogue SGMC faults is flat over all 25 integer shifts (1.60 at (0,0), peak 1.61 at (−1,0)).
  There is no systematic misregistration for a global shift to fix; local `SNAP` already retired the
  local version.
- **Catalogue tip-corridor concentration** (extend every elongated trace 1.5 km past its mapped end,
  concentrate dots on those corridors): corridor cells are only 1.37× enriched for independent SGMC
  faults at 1 px, against **1.60×** for the dots R0 already has — a weaker locator than the parent.
- **Collar placement** (`collar10/20`, `anti10`) and **parent-density relocation** (`gdr*`, `CONCb*`):
  see IR-91-33/34 and the collar session — no local instrument can reward collar placement, and
  relocation by the parent's own density is circular.
