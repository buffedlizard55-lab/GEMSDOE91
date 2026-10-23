# Variant cards — SPACING axis on R0 (built 2026-10-23)

Parent **R0** = `h33-h33-2-b2-20261004T220000Z-e5eb6e7e` (GEMSDOE32), 37,654 unit
dots, sha256 `c55bafc4…` (zeros) / `baeae321…` (NaN), dot-set digest
`905cee9d…` — the same digest GEMSDOE86 recorded, so the two sessions are
editing the same dot set. R0's 0.2778 is a **CLAIM** (owner report; no
submission-page receipt exists in any ledger). Nothing below is a score.

## The design, and why it is matched

All three arms take **the same dots** (the 40 % sitting in the densest 1 km
blocks: 3,182 blocks with ≥ 4 dots, 15,065 dots) and move each one to a cell on
the **same radius-2 integer ring** (12 cells at 2.0–2.2361 px). Every arm obeys
the same constraints: inside the footprint, farther than the parent's own
catalogue floor (d_cat > 2.0 px), no cell reused, and no two dots closer than
2.0 px afterwards (measured: 0 pairs < 2 px in all six files). **Only the
choice of ring cell differs**, so a difference in outcome is attributable to
spacing direction and not to how far the dots travel or how many there are.

The choice is not a hand-rolled angle. It minimises / maximises / randomises a
stated potential: **D = Gaussian-smoothed dot density, σ = 2 px** — the local
overlap of triangular kernels, i.e. exactly the redundancy the metric's
`0.2(S − M)` term is supposed to punish. Realised dose is measured, not
assumed: mean density at the target cell falls 0.066 → 0.035 (`spread40`),
stays 0.058 (`clump40`), lands between at 0.047 (`jitter40`).

---

### 1. `SPACINGspread40` — move the densest 40 % of dots to emptier ground

- **Hypothesis.** At fixed mass, R0's local arrangement wastes credit: two dots
  3 px apart cover largely the same truth, and the second one adds to `S`
  without adding to `T`. Redistributing the same dots to the emptiest legal
  neighbour cell buys coverage of truth not already covered.
- **Mechanism.** The kernel (triangular, R = 3 px = 300 m) means every pair of
  dots closer than 6 px shares part of its credit. R0's median nearest-neighbour
  distance is 3.0 px and 11,415 of its dots have a neighbour inside 2.83 px, so
  a third of the field is inside the saturation radius. Moving a dot from a
  saturated cell to an adjacent unsaturated one raises the number of distinct
  truth cells receiving credit, while the triangular falloff costs only the
  first-order term (2.2 px of displacement ≈ 0.07 of a unit of peak credit).
- **The non-fault process that could mimic it.** GeoDAWN Area 2 was flown at
  400 m line spacing 150–200 m above terrain
  ([USGS](https://data.usgs.gov/datacatalog/data/USGS:657e1d85d34e23d3533209f7)),
  so lineament positions are uncertain by about the kernel radius itself. Under
  that uncertainty **spreading is favourable even if the field is perfect** —
  which means a live gain here would not prove the field is right, only that
  the dots were too tightly packed. A second mimic: `spread40` also pushes 815
  dots into the 2–3 px catalogue collar against 485 out, so part of any gain
  could be collar re-entry rather than coverage (that is why the collar drift is
  in the evidence file and why the hidden-catalogue proxy is not treated as
  support).
- **Predicted sign and size.** **+0.004 MODEL** (band −0.004 … +0.012). The
  mechanism's own ceiling is small: uniform-truth expected credit moves
  −0.17 %, i.e. ≤ 0.003 at DTI 0.28.
- **Falsifier.** A live change ≤ −0.010 says the clusters are real structure
  (fault intersections, relay ramps) and de-clustering destroys them; stop the
  axis and treat the parent's concentration as a geological prior. A change
  |Δ| < 0.010 retires geometry as a lever for Phase 1.

### 2. `SPACINGclump40` — the sign flip: move the same dots to denser ground

- **Hypothesis.** The opposite of (1): if the field's ridges are real traces, a
  dot is 2 px of *positional noise* away from the trace it is trying to sit on,
  and pulling it toward its neighbours' centre sharpens the line. Sharpening is
  what raises the peak triangular credit above the 0.056 threshold at which a
  dot starts to pay at DTI ≈ 0.28.
- **Mechanism.** The parent is *jammed*: its minimum separation is 2.83 px and
  its median is 3.0 px, so a 2 px inward move usually lands on top of a
  neighbour. The realised dose is the proof — density at target only rises to
  0.058 and 14,973 of 15,065 dots could move at all. The arm is therefore
  **under-dosed by geometry**, and a null result from it is weak evidence.
- **Non-fault process that could mimic it.** Any smooth, isotropic field:
  clumping sharpens noise ridges as readily as fault ridges. Near the collar it
  also pulls dots *out* of the 2–3 px ring (260 in / 461 out), which is the same
  confound as (1) with the opposite sign.
- **Predicted sign and size.** **−0.002 MODEL** (−0.010 … +0.006), i.e. the
  sign flip is expected to be at or inside the floor.
- **Falsifier.** If `clump40` scores *above* `spread40` by ≥ 0.01, the field's
  ridges are real traces and the next axis is anisotropic packing
  (`SLOT_PLAN.md`), not spreading. If both arms land within 0.01 of each other
  and of the parent, arrangement is not a lever.

### 3. `SPACINGjitter40` — the null: same dots, same ring, random cell

- **Hypothesis.** None: this arm exists to price the *act* of moving 40 % of the
  dots by 2 px. Any displacement perturbs coverage, changes the collar count and
  changes the block-density CV; the null measures that sum so the two dosed arms
  can be read against it.
- **Mechanism.** Random legal cells preserve count, footprint and the collar
  floor but destroy the local arrangement, so `jitter40` sits between `spread40`
  and `clump40` in every geometry statistic (density at target 0.047,
  block-density CV 0.558, collar 454 in / 476 out).
- **Non-fault process that could mimic it.** It *is* the mimic. Its purpose is
  to be the process that could mimic the other two.
- **Predicted sign and size.** **0.000** by construction (band ±0.008).
- **Falsifier.** If `jitter40` separates from the parent by ≥ 0.01, then 2 px of
  displacement is itself worth something and neither dosed arm is interpretable:
  rebuild the axis with displacement held at zero (in-place re-spacing) before
  spending another slot.

---

## How the three are meant to be read

| if the live result is … | the conclusion |
|---|---|
| spread ≫ jitter ≈ clump | arrangement matters, saturation is the mechanism; next cut is spread at 50 % / ring-4 |
| clump ≫ spread | the ridges are real traces; switch to anisotropic packing |
| all three within 0.01 of each other and of the parent | geometry is retired for Phase 1; spend the remaining slots on mass/prior allocation and on getting a receipt for the baseline |

**Common caveat, stated once.** No local instrument can adjudicate this axis.
`labels.tif` is byte-identical to `existing_faults.tif` (IR-91-10), so the only
truth-adjacent local instrument is catalogue recovery, and a candidate's dots are
by construction > 2 px from that catalogue: only the 2–3 px collar can ever touch
a withheld catalogue cell (proxy coverage 3.9 % of held cells, mean credit
0.006 ≈ two orders of magnitude below a real DTI). Its sign on these arms
therefore tracks collar drift, which is why it is reported and not believed.

---

# Variant cards — MASS axis on R0, cross-field support (built 2026-10-23, session 4)

For a structural geologist. Three builds, one axis, one parent, one ranking.
Nothing here is a score: every number labelled MODEL comes from the DTI algebra in
`src/gems91/metric.py`, and R0's 0.2778 is a **CLAIM** (no receipt exists).

## Why the ranking is not the parent's own

Brief §5 says to rank by "the parent's own ranking". It cannot be rebuilt: every
pinned ancestor (`calib_h195_01922`, `calib_h194_01894`, `calib_h161_01855`,
`calib_d15_02477`, d2.8, solo-d28) is **binary**, and `training_features.tif` — the
only input that ever carried a continuous score — has no public mirror and is absent
(IR-91-17). What the lineage does carry, pinned and hash-verified, is its support
structure. Measured on the parent's 37,654 dots:

| cross-field support | dots | share | reading |
|---|---:|---:|---|
| 3 of 3 fields (H19.5 + H19.4 + H16.1) | 26,913 | 71.5 % | three independent hand-drawn interpretations agree |
| 2 of 3 | 6,200 | 16.5 % | |
| 1 of 3 (H19.5 only) | 4,541 | 12.1 % | single-interpretation support |
| 0 of 3 | 0 | — | every R0 dot is inside at least one field |

Support is an ordinal precision proxy, not a score. Whole strata are removed so no
arm needs an arbitrary tie-break inside the ordering under test. The add arm ranks by
support, then by distance from the nearest existing dot (the d2.8 thinning suppressed
77,041 field pixels on a *spacing* rule, so the cells it dropped beside survivors are
exactly what a "was the thinning too aggressive" test should retry), then row-major.

## The metric arithmetic that sizes every arm

For the triangular kernel (R = 3 px, α = 0.2) the per-dot change in DTI at precision
`p` (chance the nearest truth pixel is within 2.83 px) and mean credit `c̄` is

    E[ΔDTI] ≈ (p·c̄ − γ)/D,     γ = α·d/(1 − α·d) = 0.0556 at d = 0.2778

so **a dot is worth emitting iff its precision exceeds 11.8 %** (at c̄ = 0.5), and
equivalently iff it is within 2.83 px of a truth pixel. Every arm below is therefore a
bet on one number — the precision of the mass it moves — and a ±0.01 live move is the
whole dynamic range of the axis (D ∈ [1e4, 3.5e4], so 1,000 dots ≈ 0.002–0.006).

Two controls say what the ranking is *not*. (a) A canary on the 0–3 px catalogue ring
gives AUC **0.526**: the support ordering is essentially blind to proximity to known
traces, so it is not a disguised PRUNE — the lineage's fields, like R0 itself, are
catalogue-masked (0 of 60,988 catalogue pixels carry any field). (b) SGMC overlap is
8.4 % (R0) → 8.4–8.8 % (arms): no arm starts tracking a public state map.
The catalogue hide-and-recover PROXY separates nothing: 0.00465 (R0) vs
0.00449/0.00426/0.00382, CI ±0.002–0.003 over 4 spatial folds. As reported by prior
sessions, that instrument has never tracked live scores reliably (n = 12–14,
r = −0.87 to +0.54); it is not evidence here either way.

---

## 1. `MASScons1drop` — drop the single-interpretation stratum

- **Hypothesis.** The 4,541 dots that only H19.5 supports are drawn from the
  lowest-precision part of R0; removing them raises precision-weighted score.
- **Mechanism.** 4,541 dots leave `S` by 4,541 and leave `T` by whatever credit they
  earned. First-order that is +4,541·0.0556/D = +0.007 to +0.025 if the stratum is
  pure noise, and −0.020 to −0.006 if its precision is 25 %. Break-even is p = 11.8 %.
- **Non-fault process that mimics it.** H19.4 and H16.1 are *different interpretations
  of the same geophysics*, not independent observers. Their disagreement may mark
  survey-quality or lithology boundaries (a contact, a basalt flow edge, an alluvial
  margin) rather than fault candidates — in which case the "disagreed" dots are
  exactly the ones that were right.
- **Predicted sign and size.** MODEL **−0.0002** [−0.013, +0.007], ×0.64–2.25 for
  denominator uncertainty. Deliberately near zero: the arm is a measurement of the
  stratum's precision, not a bet on its sign.
- **Falsifier.** A live change ≥ +0.01 says single-field mass is net-negative and the
  ordering is usable; ≤ −0.01 says the unique-interpretation dots carry real credit
  and this ranking must not be used to cut.

## 2. `MASScons2drop` — the next whole stratum

- **Hypothesis.** If support is informative, the slope continues: dropping both
  low-support strata (10,741 dots, 28.5 %) should gain roughly twice as much as arm 1.
- **Mechanism.** Same arithmetic at 2.4× the dose, so the same precision is amplified:
  at p = 18 % it is −0.015, at p = 8 % it is +0.009.
- **Non-fault process that mimics it.** Redundancy. R0's median nearest-neighbour
  distance is 3.0 px, so many of these dots share a truth pixel with a neighbour;
  removing one of a redundant pair costs `T` far less than `S`, which would make a
  drop look good even when the pair was right. If arm 1 is flat and arm 2 gains, this
  is the more likely explanation than support, because arm 2 exposes more pairs.
- **Predicted sign and size.** MODEL **−0.015** [−0.044, +0.009], ×0.64–2.25.
- **Falsifier.** A gain here, with arm 1 flat, points at redundancy rather than
  precision — distinguishable later by a count-matched variant (SPACING) rather than
  another drop.

## 3. `MASScons3add` — add 10 % at the best-supported unspent cells

- **Hypothesis.** The lineage thinned 121,131 field pixels down to 37,654 dots on a
  spacing rule (d2.8), not on a precision rule. The 46,827 three-way-agreed cells that
  sit ≥ 3 px from the catalogue and are not yet dots are the best remaining mass.
- **Mechanism.** Each added dot pays iff its precision exceeds 11.8 %. Adding 3,765
  dots at p = 22 % is +0.009; at p = 10 % it is −0.002. Unlike the drops, this arm
  cannot lose much: the downside is bounded by the unmatched-mass cost per dot
  (0.0556), while the upside per matched dot is c̄ ≈ 0.5 — a 9:1 payoff ratio.
- **Non-fault process that mimics it.** Junction and step-over thickenings: three-way
  agreement concentrates exactly where several traces, or a thick fault zone, occupy
  the same 100 m cell. Those are real fault pixels, but they are also where R0 is
  already densest, so the added mass may be redundant (costs `S`, earns credit already
  earned by a neighbour) rather than new.
- **Predicted sign and size.** MODEL **+0.0086** [−0.002, +0.019], ×0.64–2.25. This is
  the arm on the board with a plausible path past +0.01, and the only one whose
  failure is cheap.
- **Falsifier.** A live change ≤ −0.005 retires the support ordering in the *add*
  direction and says the thinning was not over-aggressive; combined with a negative
  arm 1/2 it says the ordering carries no usable precision signal at all, and MASS
  should be closed rather than re-dosed.
