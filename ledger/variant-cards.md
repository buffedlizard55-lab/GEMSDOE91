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
