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

# Variant cards — RELIEF axis on R0 (Session 5, built 2026-10-23)

Full structural-geologist mechanism cards and equal-area tercile diagnostics live in
[`docs/MECHANISM_CARDS.md`](../docs/MECHANISM_CARDS.md) and
[`evidence/relief_axis_20261023.json`](../evidence/relief_axis_20261023.json).
All three arms hold total mass fixed at `37,654` unit dots (`RECEIPT`), relocate
exactly `4,518` dots (`12.00%` moved; `9,036` pixel symmetric diff = `24.00%`
`RECEIPT`), keep `0` pairs `< 2 px`, and quarantine R0's `2,171` inherited
`2 < d_cat ≤ 3 px` collar dots (`0` removed, `0` added `RECEIPT`) across relief
terciles `R_rel = 0.90·pct(det_elev) + 0.10·pct(det_elev_slope)` from official
`training_features` ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).

### 1. `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` (`range -> pied`, 12.00%)
- **Hypothesis.** Unmapped geothermal-controlling faults concentrate along T2
  piedmont-toe scarps, synthetic range-front step-overs, and thin-alluvium relay
  ramps (`~328 m` median basin depth `RECEIPT`), whereas R0 over-weights T3 horst
  erosional ridges (`38.01%` of R0).
- **Mechanism.** Strips `4,518` lowest-corroborated T3 dots (`d_cat > 3 px`) and
  places `4,518` dots on T2 lineage ridges (`2,686` at `d ≥ 2.8 px`, `1,832` at
  `d ≥ 2.0 px`); tercile shares shift `17.67 / 44.32 / 38.01% -> 17.67 / 56.32 / 26.01%`
  (`RECEIPT`). 4-fold rebuilt `PROXY` delta `−0.0017` (`0.1116` vs `0.1133`);
  off-catalogue SGMC `PROXY` delta `−0.0049` (`0.0905` vs `0.0954`,
  [USGS DS-1052](https://pubs.usgs.gov/ds/1052/)).
- **Non-fault mimic.** Coalescing alluvial-fan toes, Pleistocene pluvial-lake
  shorelines, and shallow pediment-alluvium onlap contacts.
- **Predicted live change.** **+0.006 `MODEL`** (`[-0.006, +0.018]`; `|Δ| < 0.01` = no evidence).
- **Falsifier.** Live delta `≤ −0.010` vs R0, or `b2r12` beating `r2p12` by `≥ +0.010`.

### 2. `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` (`range -> basin`, 12.00%)
- **Hypothesis.** Because subaerial range fronts are largely mapped, concealed
  intrabasin grabens, transfer zones, and basement horst steps beneath deep
  (`~560 m` median `RECEIPT`) T1 basin fill carry the highest density of unmapped
  geothermal conduits.
- **Mechanism.** **Donor-identical twin of `r2p12`** (drops the exact same `4,518`
  T3 dots `RECEIPT`) and **sign flip of `b2r12`**; places `4,518` dots into T1
  (`954` `d ≥ 2.8` lineage, `1,791` `d ≥ 2.0` lineage, `1,773` `d ≥ 2.8` dual
  magnetic+gravity horizontal-gradient crests); terciles `29.67 / 44.32 / 26.01%`
  (`RECEIPT`). 4-fold rebuilt `PROXY` delta `−0.0032` (`0.1101`); SGMC `PROXY`
  delta `−0.0091` (`0.0863`).
- **Non-fault mimic.** Buried volcanic paleochannels, axial fluvial/playa facies
  transitions, and intrabasin basaltic sills/pluton edges.
- **Predicted live change.** **+0.003 `MODEL`** (`[-0.010, +0.016]`; `|Δ| < 0.01` = no evidence).
- **Falsifier.** `DTI(r2b12) − DTI(r2p12) ≤ −0.010` (donor loss cancels identically,
  isolating deep-basin geophysical crests as net mimics vs piedmont traces).

### 3. `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` (`basin -> range`, 12.00%)
- **Hypothesis.** Withheld sponsor truth reflects detailed 1:24k–1:100k bedrock
  fault mapping (`64–70%` of off-catalogue SGMC traces sit in T3 `RECEIPT`), while
  T1 basin-floor dots sit on unverified geophysical gradients absent from surface truth.
- **Mechanism.** **Exact directional sign flip of `r2b12`**: moves `4,518` T1 dots
  (`17.67% -> 5.67%` Basin) onto corroborated T3 lineage ridges (`3,036` at
  `d ≥ 2.8 px`, `1,482` at `d ≥ 2.0 px`; `38.01% -> 50.01%` Range `RECEIPT`).
  Sole arm gaining on off-catalogue USGS SGMC bedrock faults (`+0.0050` / `+5.2%`,
  `0.1003` vs `0.0954` `PROXY`), while trading `−0.0113` on Quaternary-heavy
  INGENIOUS 4-fold recovery (`0.1020` `PROXY`, [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)).
- **Non-fault mimic.** Differential erosion of tilted ash-flow tuffs, carbonate
  cliffs, intrusive contacts, and canyon walls in exhumed horsts.
- **Predicted live change.** **+0.005 `MODEL`** (`[-0.010, +0.020]`; `|Δ| < 0.01` = no evidence).
- **Falsifier.** `DTI(b2r12) − DTI(r2b12) ≤ −0.010` falsifies bedrock enrichment;
  `|Δ| < 0.010` on both `r2b12` and `b2r12` across a `24 pp` T1/T3 swing retires `RELIEF`.

