# Mechanism cards — PRUNE dose-response, parent R0

For a structural geologist. One card per build. All three share one mechanism and one
falsifier; they differ only in dose.

## Shared setup, measured not assumed

R0 (`h33-h33-2-b2`, sha256 `baeae321…c77dd`, verified against the parent repo's own
manifest) is 37,654 unit-mass dots, 0 on the catalogue, minimum 2.236 px from it.
It is exactly *solo-d28* (40,199 dots) minus the 2,545 dots within ≤2 px of the
catalogue, with no refill — differencing the two public rasters gives 0 dots present
in R0 but not in solo-d28. So this lineage's PRUNE means *delete*, and the parent
never held mass constant.

Measured on R0 against the catalogue mask (60,988 px, = labels > 0):

| dose | dots removed | % of R0 | of which zero catalogue credit | catalogue credit lost |
|---|---|---|---|---|
| ≤3 px | 2,171 | 5.77 % | 560 | 277.9 (100 % of R0's total) |
| ≤8 px | 9,164 | 24.34 % | 7,553 | 277.9 |
| ≤15 px | 15,665 | 41.60 % | 14,054 | 277.9 |

**All of R0's credit against the catalogue lies within 3 px** — necessarily, since the
kernel radius is 3 px. Consequently every dot removed between 3 and 15 px has *zero*
credit against known faults. Its only possible value is credit against new-fault truth.

## The mechanism, in the metric's own terms

Removing a dot whose credit is 0 leaves the numerator alone and cuts the denominator
by `0.2` (the `alpha·(S−M)` term), so the score rises:

    Δscore = DTI · 0.2 / (den − 0.2)   per zero-credit dot removed

Removing a dot that *does* earn credit `k` costs `k` in the numerator. It pays only
if `k < 0.2·DTI ≈ 0.056`, i.e. below about 5.6 % of a full kernel weight.

So the axis is a pure trade: **denominator mass saved vs new-fault credit destroyed.**
Because known USGS/INGENIOUS pixels are masked when scoring, credit collected against
the *catalogue* is worth nothing live — which is why losing all 277.9 units above is
not automatically a loss. The whole question is how much new-fault credit those dots
were quietly earning.

Denominator is bounded: `den = T/DTI` with `T ≤ S = 37,654`, so `den ≤ 135,528`; and
`den ≥ 0.8·|G|`, with the new-fault count plausibly at least the catalogue's 60,988,
so `den ≳ 48,800`. That bracket drives the predicted sizes below.

## Card 1 — `R0-PRUNE3-20261023` (≤3 px, 2,171 dots removed, 5.77 %)

- **Hypothesis.** The 2 px margin in R0 is slightly too conservative: the 1,611 dots
  at 2–3 px are close enough to known traces to be largely redundant with masked
  geometry, yet far enough to be adding denominator cost.
- **Mechanism.** Delete dots at 2 < d ≤ 3 px. Buys 0.2 × 2,171 of denominator;
  risks the new-fault credit of dots that are 300 m from a known fault, which is
  exactly the distance at which the organizer says new faults may occur.
- **What could mimic it.** A real geological reason for dots at 2–3 px: splays and
  step-overs genuinely sit 200–300 m off the main trace, and the 400 m flight spacing
  (GeoDAWN Area 2) blurs positions by about this much. Those dots could be correct
  and still be deleted.
- **Predicted live change.** +0.002, range −0.002 to +0.006. **Most likely below the
  brief's 0.01 evidence threshold** — treat a result here as refinement, not discovery.
- **Falsifier.** If the score falls, R0's 2–3 px dots were carrying real new-fault
  credit and the 2 px margin is already past the optimum; no later file should prune
  further.

## Card 2 — `R0-PRUNE8-20261023` (≤8 px, 9,164 dots removed, 24.34 %)

- **Hypothesis.** The 3–8 px shell (6,993 dots, all zero catalogue credit) is mostly
  background that the parent's ranking carried along, and it is pure denominator cost.
- **Mechanism.** Same as card 1, larger dose. Unlike card 1, this dose is not defended
  by the organizer's "new faults within 300 m" statement: 300–800 m is outside it.
- **What could mimic it.** Structurally faithful traces that run parallel to known
  faults at 300–800 m — common in this terrane's step-over relay zones. If those are
  in the truth set, this dose deletes real positives.
- **Predicted live change.** +0.006, range −0.004 to +0.014.
- **Falsifier.** A loss here that is *larger* than card 1's loss would mean the cost
  grows with distance from the catalogue — i.e. new faults sit *away* from known
  traces, and the next axis should add mass at 3–8 px rather than remove it.

## Card 3 — `R0-PRUNE15-20261023` (≤15 px, 15,665 dots removed, 41.60 %)

- **Hypothesis.** Most of R0's mass is uninformative: 14,054 of these dots have no
  catalogue credit at all, and at 1.5 km from known faults a coincidental hit on new
  truth is unlikely.
- **Mechanism.** Largest dose that stays inside the brief's 1–50 % band with room to
  spare. This is the only card with a plausible path past +0.01.
- **What could mimic it.** Basin-scale detrital/structural fabric that is not mapped
  as a fault, or genuinely unmapped faults at km distances from known systems — the
  forum answer explicitly allows newly mapped geometry of existing systems, which can
  sit far along strike.
- **Predicted live change.** +0.010, range −0.008 to +0.024. Highest variance of the
  three, because the new-fault credit term is largest here.
- **Falsifier.** If all three scores are flat or identical, the denominator saving is
  cancelled by credit loss at every dose and PRUNE is exhausted as an axis; the next
  slot should go to CONCENTRATION or RELIEF instead. If ≤15 is the best and ≤3 the
  worst, the axis is a "throw mass away" axis, not a "avoid the catalogue" axis, and
  the next build should test the same dose *with* refill from an explicit ranking.

## What none of these cards claim

No card claims a live score. The numbers are MODEL projections from the metric
algebra plus a bracketed denominator. The hide-and-recover PROXY (report only,
`reports/proxy.json`) came out at 0.0047–0.0050 for all four files with overlapping
95 % CIs — it cannot separate these doses and is not evidence either way.

---

# Session 2026-10-23 — CONCENTRATION on R0 (GDR thermal-feature prior)

Built by `scripts/build_concentration.py`; numbers in `evidence/concentration_axis_20261023.json`.
Parent: R0, 37,654 unit dots, claimed 0.2778 (CLAIM). Dot count and mass per dot are fixed in
every arm; only *where* 3,765 dots sit changes.

## Card — `…-CONCENTRATIONgdr25m10-20261023-08bf80cf` (2.5 km blocks, all thermal features)

**Hypothesis.** At a fixed dot budget the live score rises when 10 % of the dots move from the
km blocks furthest from any thermal feature into the km blocks closest to one.

**Mechanism.** A dot pays only through kernel credit from truth within 3 px, and it costs
`0.2·(1 − max_g k)` in the denominator. Springs and hot wells sit on *structure*: they require a
permeable pathway to depth, which in the Basin and Range is a fault or a fault intersection. If
new-fault truth is concentrated near those pathways, moving mass there raises T at almost no
cost in S (the count is unchanged) or in (S − M) (the acceptors land among existing dots, not on
top of them). Acceptors' mean prior 0.110 versus donors' 5.4 × 10⁻⁶: the dots leave blocks whose
cells are ~14 km from any thermal feature. The edit is large in space — mean displacement
1,632 px (163 km), max 3,726 px — because the donors are exactly the featureless part of the
footprint. It also *empties* 570 of the 5,219 occupied 2.5 km blocks (3,763 dots) and occupies
409 new ones.

**Non-fault process that could mimic it.** (a) *Land use and access*: wells are drilled in
valleys, near roads and playas, so the prior partly maps "basin floor", and basin-floor faults
may be sampled or mapped differently. (b) *Catalogue re-encoding*: 15 % of the thermal features
sit within 3 px of a mapped trace, so the prior is partly a re-statement of what is already
masked — this is why the third arm keeps only features >8 px off the map. (c) *Measurement
effort*: 27,092 CSV rows for 12,570 distinct cells (one well repeated 52 times); de-duplicating
to one feature per cell removes that, but an inventory is still denser where someone looked.

**Predicted sign and size.** **+0.0114 (MODEL)**, interval **−0.022 … +0.034**. The interval is
not decoration: +0.034 is 3 × the point estimate, and −0.022 is *measured*, not assumed — if
truth followed the lineage's own 121,131-px H19-5 field, this same relocation would lose 0.022,
because the dots no longer cover 8.4 percentage points of that field (88.6 % → 80.2 %). The
point estimate comes from scoring the arm against its own prior network (9,501 cells within
1 px of a feature) and claiming a tenth of the +41 % relative gain. That instrument is
**circular by construction**: it says what happens if the prior is right, nothing more.
Uniform random truth (9,501 cells) puts the same edit at −0.006. Reported, labelled, and never
called a score.

**Falsifier.** Live Δ ≤ 0 while the moved fraction (10.00 %), the block-CV change (0.762 →
0.808 at 2.5 km) and the donor/acceptor prior gap all match the design ⇒ the thermal prior
carries no transferable information about new-fault location; retire the axis. Live Δ ≥ +0.01
⇒ it does, and the 20 % dose (`w20`) is the next build. **A live change under 0.01 is no
evidence** (public chunks only).

**Controls.** Same seed, same 10 %, same placement rules, random block ranking (`null
diagnostic`, no release, no slot): it already earns +0.0087 of the prior-as-truth +0.114, so
~8 % of the surrogate gain is generic relocation and the remaining ~92 % is the prior. The
catalogue hide-and-recover proxy falls 0.006186 → 0.005407 (−12.6 %, PROXY, report-only): the
edit moves mass away from mapped traces, which is the intended mechanism, but IR-91-15 explains
why that number does not adjudicate anything. Leakage canary 0.4496 (stop threshold 0.90).

## Card — `…-CONCENTRATIONgdr10m10-20261023-d54e8815` (1 km blocks)

Identical except the block size: +0.0113 (MODEL), −0.021 … +0.034, block CV (1 km) 0.6187 →
0.6459. It exists to ask whether the prior's information lives at 1 km or 2.5 km; the arms come
out within 0.0001 of each other, so **it does not** — do not spend a slot on the scale question
before one 2.5 km arm has a receipt (IR-91-17).

## Card — `…-CONCENTRATIONgdr25rm10-20261023-c19adb01` (2.5 km blocks, remote features only)

Prior built from the 1,406 thermal features more than 8 px from the mapped catalogue.
+0.0123 (MODEL), −0.022 … +0.037; block CV 0.762 → 0.819. This is the cleanest test of the
mechanism as written — "structure the map has not captured" — and therefore **slot 1**, because
its prior cannot be a re-statement of the masked catalogue. Its surrogate-truth DTI start is
lower (0.0359, fewer features) but the relative gain is the largest (+44 %).

## What these cards do not claim

- No live effect has been measured. Every number above is MODEL or PROXY.
- The co-registered 400 m flight-line geometry, the Faulds inventory and the SGMC control were
  not used as priors here; only the GDR well/spring inventory, which is public domain and
  already pinned for "prior layer only".
- These are one experiment, not three: 10 % moved, same seed, same collar, three ways of
  choosing high-prior blocks. Only receipts separate them.
