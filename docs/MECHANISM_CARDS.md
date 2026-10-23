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

# Session 5 — MASS axis on R0 (three arms, one ranking)

Parent **R0** = `h33-h33-2-b2-20261004-e5eb6e7e` (GEMSDOE32), 37,654 unit dots,
sha256 `baeae321…` (nan) / `c55bafc4…` (zeros), dot-set digest `905cee9d…`,
reproduced here from **both** pinned ancestors before any edit. 0.2778 is a **CLAIM**.

## The ranking, and why it is not the one the brief asks for

The brief asks for the parent's *own* ranking. R0's marginal-gain ranking needs
`training_features.tif` (419 MB, never mirrored, still absent — IR-91-16). What the
lineage *does* pin is the field every dot was thinned from: `anc_h19_5`, 121,131 px.
Rank = `gaussian_filter(H19-5, σ = 1 px)` at the dot, i.e. **how much of the parent's
own generation field the dot sits in**. Ties are broken row-major; the largest tie
group is 0.03 % of the dots.

*(A triangular-kernel support version was built first and withdrawn: 4,849 dots tie at
exactly 1.0, and the row-major tie-break pushed the drop to the north — mean row 808
against 1,325. It is in the ledger as `…-triDraft`.)*

That ranking carries a **weak but positive** signal about real faults: AUC 0.54 for
"this dot is within 3 px of an independent mapped fault" (SGMC compilation).

## One edit that is not part of the axis

R0 has 1,611 dots closer than 3 px to the catalogue (2,171 at ≤ 3 px), so **every**
R0-derived file fails constraint 4 at construction (IR-91-03). All three arms
therefore drop those collar dots identically. It is the same edit in each arm, so the
arms still differ only on MASS — but both percentages are recorded: axis dose and
total change against R0. Consequence for the *prediction*: the common edit removes
100 % of R0's 277.9 units of catalogue credit, which the organizers mask anyway.

## The instrument, and why the raw version had to be thrown away

`sgmc_faults_control` scores every candidate with the exact DTI algebra. **Raw SGMC
runs backwards against the lineage's own winning steps**:

| file | dots | DTI vs SGMC | DTI vs SGMC minus 3 px of catalogue | live (CLAIM) |
|---|---:|---:|---:|---:|
| H19-5 field | 121,131 | 0.15244 | 0.09917 | 0.1922 |
| d2.8 | 44,090 | 0.13766 | 0.09417 | 0.2600 |
| solo | 40,199 | 0.10774 | 0.09530 | 0.2708 |
| **R0** | 37,654 | **0.08938** | 0.09539 | **0.2778** |

The raw instrument falls monotonically while the live score rises: it pays for mass
sitting on mapped faults that the organizers **mask**. Restricting it to cells > 3 px
from the catalogue (the mask analogue) restores the sign on both collar steps
(+0.00112, +0.00009 against live +0.0108, +0.0070). It does *not* explain the
field→dots step. So: the restrained version is used for signs only, and its magnitude
is rescaled through the lineage's own per-dot economics (den = 19,877, T = 5,452 from
the two collar steps; 2.76e-6 per zero-credit dot).

---

## Card 1 — `MASSsup10minus` (−3,765 dots by field rank, + common collar)

- **Hypothesis.** The dots in the thinnest parts of the parent's own field are the
  ones the generator's sampling barely supported; they cost `0.2` in the denominator
  and should be the cheapest mass to give up.
- **Mechanism.** Delete the bottom decile; the denominator falls by `0.2 × 3,765`.
  It pays iff the removed dots' credit is under `0.2 · DTI ≈ 0.056` each.
- **What could mimic it.** Fault tips and isolated splays are *also* low-support: a
  short unmapped trace is exactly what a sparse part of the field looks like. And the
  max-kernel means an isolated dot's credit is uniquely its own while a dot in a dense
  patch shares its truth with neighbours — so "redundant-looking" is the opposite of
  "low-support".
- **Measured.** Removed dots carry **0.185 credit each** on the restrained instrument
  (696.7 / 3,765) — 3× the break-even. Predicted live change **−0.018**
  [−0.039, +0.007]; −0.008 if the live denominator sits at the bracket's other end
  (42,800).
- **Falsifier.** A live result **above** +0.01 would mean the withheld new-fault truth
  is far sparser than any unmasked fault map here (credit per dot under 0.056), i.e.
  the whole lineage has been paying for mass it does not need. That would make PRUNE
  the axis to press, not retire.

## Card 2 — `MASSsup24minus` (−9,164 dots, dose-matched to PRUNE `le8`)

- **Hypothesis.** Same mechanism at 2.4× the dose, and the one experiment that
  separates *which* dots go from *how many*: `le8-norefill` removes 9,164 dots chosen
  by distance to the catalogue, this removes 9,164 chosen by field rank.
- **Mechanism.** Pure dose response. If the ranking mattered, the two files' outcomes
  would differ; if not, they move together.
- **What could mimic it.** Nothing new — the confounder is the same sparse-field one.
- **Measured.** 0.145 credit per removed dot (1,327 / 9,164) against `le8`'s 0.143
  (1,306.2 / 9,164) on the same instrument: **the two rankings are
  indistinguishable**. Predicted **−0.034** [−0.071, +0.009]; −0.016 at the wide-den
  bracket.
- **Falsifier.** `sup24minus` beating `le8` by more than 0.01 live would say the
  ranking carries real information; they measuring the same would say MASS is a pure
  dose axis and the choice of dots is noise.

## Card 3 — `MASSsup10plus` (+3,765 cells by field rank, + common collar)

- **Hypothesis.** The 2.83 px suppression rule inherited from Poisson-disk thinking
  may be leaving usable coverage on the table: on line-like truth, a dot 2 px off a
  neighbour covers truth cells the neighbour reaches only at weight ≈ 0.07.
- **Mechanism.** Add the highest-rank undotted cells that are ≥ 3 px from the
  catalogue and ≥ 2 px from every dot (greedy). Each pays `0.2(1 − M)`.
- **What could mimic it.** Any coverage that only looks fresh: the mean new credit is
  0.041 per added dot on the restrained instrument, **below** the 0.056 bar, because
  these cells are by construction inside a neighbour's shadow.
- **Measured.** dT = +39.1 for 3,540 added dots. Predicted **−0.002**
  [−0.007, +0.003] — a wash, not a win.
- **Falsifier.** A live gain above +0.01 here means the live metric is far more
  forgiving of unmatched mass than the algebra says, or that the truth is much denser
  under these ridges than any map shows. Either would reopen MASS+.

## What none of these cards claim

No card claims a live score. All three are MODEL projections. The catalogue
hide-and-recover PROXY is **undefined** on these files, not zero: every dot is now
> 3 px from the catalogue by construction, so the proxy (which only ever sees the 2–3 px
collar) has zero coverage. That is a limitation of the instrument, not evidence.
