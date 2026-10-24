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
---

# Mechanism cards — RELIEF tercile reallocation, parent R0 (Session 5, 2026-10-23)

For a structural geologist. One card per build (`evidence/relief_axis_20261023.json`).
Parent **R0** = `h33-h33-2-b2` (`37,654` unit-mass dots `RECEIPT`, sha256 `baeae321…c77dd`
primary / `c55bafc4…6fa9` zeros, live baseline `0.2778` `CLAIM` in earlier repo notes
or `0.3698` `CLAIM` in `SLOT_PLAN.md`; unreceipted in `ledger/submissions.csv`).

## Shared structural setup, measured on the GeoDAWN / INGENIOUS stack

Using official GEMS `training_features` (`gems-geodawn-numerical-features.tif`, sha256
`4371c82e…3bc5` `RECEIPT`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)),
we partition the `5,167,373`-pixel (`51,674 km²`) Great Basin evaluation footprint into
exact equal-area relief terciles via `R_rel = 0.90·pct(Band 12 det_elev) + 0.10·pct(Band 19 det_elev_slope)`:

| Tercile | Footprint px (`RECEIPT`) | Med. `det_elev` (`RECEIPT`) | Med. slope (`RECEIPT`) | Med. sediment depth (`RECEIPT`) | R0 dots (`RECEIPT`) | R0 share (`RECEIPT`) |
|---|---:|---:|---:|---:|---:|---:|
| **T1 Basin floor** (`basin`) | 1,722,459 (33.33%) | −220.9 m | 0.93° | 559.9 m | 6,654 | 17.67% |
| **T2 Piedmont / bajada** (`pied`) | 1,722,456 (33.33%) | −75.6 m | 3.20° | 327.6 m | 16,689 | 44.32% |
| **T3 Range-front / horst** (`range`) | 1,722,458 (33.33%) | +211.1 m | 13.83° | 98.9 m | 14,311 | 38.01% |

**Experimental controls held fixed across all three arms:**
1. **Total mass fixed** at `37,654` unit dots (`S = 37,654` `RECEIPT`), isolating spatial
   relief allocation from `MASS`.
2. **Exact dose fixed** at `4,518` relocated dots (`12.00%` of parent dots moved; `9,036`
   symmetric pixel changes = `24.00%` `RECEIPT`, inside the `1–50%` non-SNAP band).
3. **Zero catalogue-collar drift**: R0's `2,171` inherited dots in `2.236 ≤ d_cat ≤ 3.0 px`
   are quarantined (`0` removed, `0` added; `collar_le3px = 2,171` before and after
   `RECEIPT`), preventing confounding with `PRUNE`.
4. **2×2 experimental geometry**: `r2p12` and `r2b12` drop the **exact same 4,518 T3
   donor pixels** (`r2p12_r2b12_donor_set_identical = true` `RECEIPT`), while `r2b12` and
   `b2r12` form an **exact directional sign flip** between T3 Range and T1 Basin.
5. **Report-only local instruments** (never gates):
   - Single-band leakage canary across all 19 `training_features` bands: max symmetric
     Mann-Whitney AUC = `0.5793` `PROXY` (`Band 4 geod_2ndinv`; `det_elev = 0.5063`,
     `det_elev_slope = 0.5633`, `relief_index = 0.5007`, all `≪ 0.90` stop rule).
   - 4-fold spatial-block rebuilt hide-and-recover `PROXY` (`n = 16,844 / 17,873 / 14,311 / 11,960`
     withheld INGENIOUS fault pixels per quadrant, [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)):
     `R0 = 0.1133` (95% CI `[0.0538, 0.1728]` `PROXY`).
   - Off-catalogue USGS SGMC bedrock fault control (`62,122` pixels > 300 m from masked
     INGENIOUS faults, [USGS DS-1052](https://pubs.usgs.gov/ds/1052/)): `R0 = 0.0954` `PROXY`.

---

## Card 4 — `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c` (`range -> pied`, 12.00% relocated)

- **Hypothesis.** Unmapped Great Basin geothermal-controlling faults in the sponsor's
  withheld post-2022 truth set concentrate disproportionately along T2 piedmont-toe
  scarps, range-front synthetic step-overs, and relay ramps masked by thin (`~100–350 m`)
  alluvial fans, whereas R0 over-allocates `38.01%` of its mass into T3 bedrock horst
  interiors where topographic-slope edge detectors fire on unfaulted erosional ridges.
- **Mechanism.** Strips the `4,518` weakest-corroborated T3 horst dots (`d_cat > 3 px`,
  mean `S_struct = 0.530` `PROXY`) and places `4,518` unit dots onto corroborated T2
  piedmont-bajada structural traces (`2,686` on `d ≥ 2.8 px` multi-ancestor lineage +
  `1,832` on `d ≥ 2.0 px` lineage infill, mean `S_struct = 0.631` `PROXY`, `0` pairs
  `< 2 px`). Shifts tercile shares from `17.67 / 44.32 / 38.01%` to
  `17.67 / 56.32 / 26.01%` (`Basin / Piedmont / Range` `RECEIPT`). Under DTI's `300 m`
  triangular kernel (`alpha = 0.2`, `beta = 0.8`), swapping horst false-positive ridges
  for synthetic piedmont step-overs raises numerator `T` at constant `S = 37,654` while
  incurring almost zero substitution loss on INGENIOUS-style Quaternary fault geometry
  (4-fold rebuilt `PROXY` delta `−0.0017`, `0.1116` vs `0.1133`, 95% CI `[0.0543, 0.1689]`).
- **Non-fault mimic.** Coalescing alluvial-fan apron toes, Pleistocene pluvial-lake
  shorelines (Lahontan/Bonneville highstands), and shallow bedrock pediment-alluvium
  onlap contacts produce strike-parallel gravity/magnetic horizontal-gradient inflections
  and subtle break-in-slope lineaments across T2 bajadas without brittle offset.
- **Predicted live change.** **+0.006 `MODEL`** (plausible band `−0.006` to `+0.018`
  `MODEL`; note `|Δ| < 0.01` = no evidence under the competition's noise/resolution bar).
- **Falsifier.** Live DTI delta `≤ −0.010` vs R0 (proving the stripped T3 horst dots
  carried real unmapped bedrock fault credit), OR `b2r12` outscoring `r2p12` by `≥ +0.010`
  (proving withheld truth is exhumed bedrock-dominated rather than piedmont-concealed).

## Card 5 — `h33-h33-2-b2-RELIEFr2b12-20261023-27443c30` (`range -> basin`, 12.00% relocated)

- **Hypothesis.** Because subaerial range fronts and upper bajadas have been mapped for
  decades in USGS QFF and NBMG quadrangles, the highest-value *unmapped* geothermal
  conduits lie concealed beneath deep (`~560 m` median) T1 playal/alluvial basin fill as
  intrabasin antithetic grabens, accommodation-zone transfer faults, and blind basement
  horsts detectable only in GeoDAWN magnetic (`tmi_hg`) and isostatic gravity (`iso_grav_anom_slope`, `iso_grav_anom_hg`) gradients.
- **Mechanism.** **Donor-identical twin of `r2p12`** (removes the exact same `4,518` T3
  horst dots `RECEIPT`) and **exact directional sign flip of `b2r12`**, placing all
  `4,518` dots onto T1 basin-floor structural targets (`954` on `d ≥ 2.8 px` lineage +
  `1,791` on `d ≥ 2.0 px` lineage + `1,773` on `d ≥ 2.8 px` dual magnetic+gravity
  potential-field crests where `pct(tmi_hg) ≥ 0.80` and `max(pct(grav_slope), pct(|grav_hg|)) ≥ 0.80`,
  `0` pairs `< 2 px` `RECEIPT`). Shifts tercile shares to `29.67 / 44.32 / 26.01%` `RECEIPT`.
  4-fold rebuilt `PROXY` is `0.1101` (`−0.0032` vs R0, 95% CI `[0.0559, 0.1643]`);
  off-catalogue SGMC bedrock `PROXY` drops `−0.0091` (`0.0863` vs `0.0954`) as expected
  because state geologic maps rarely map blind playal faults.
- **Non-fault mimic.** Buried Cenozoic volcanic paleochannels, compacted axial fluvial/playa
  facies boundaries, and reversely magnetized basaltic sills or pluton margins within
  basin fill generate sharp potential-field horizontal-gradient crests (`tmi_hg` +
  `iso_grav_anom_hg`) without Quaternary or geothermal fault slip.
- **Predicted live change.** **+0.003 `MODEL`** (band `−0.010` to `+0.016` `MODEL`;
  `|Δ| < 0.01` = no evidence). Higher upside if sponsor truth relies on 3D gravity/MT/well
  inversions, higher downside if sponsor truth is surface-rupture/LiDAR mapping.
- **Falsifier.** Since `r2p12` and `r2b12` remove the **exact same 4,518 T3 dots**, their
  live difference `DTI(r2b12) − DTI(r2p12)` cancels donor loss identically: if
  `DTI(r2b12) − DTI(r2p12) ≤ −0.010`, deep-basin potential-field crests are net mimics
  relative to piedmont-toe traces and basin-floor enrichment is falsified.

## Card 6 — `h33-h33-2-b2-RELIEFb2r12-20261023-e1fd28d5` (`basin -> range`, 12.00% relocated)

- **Hypothesis.** Withheld sponsor truth resembles detailed 1:24k–1:100k bedrock
  quadrangle mapping (cross-range accommodation faults, intra-horst relay splays, and
  exhumed footwall damage zones) where `64–70%` of off-catalogue USGS SGMC bedrock fault
  traces reside (`RECEIPT` on `sgmc_faults_px.tif`), whereas R0's T1 basin-floor dots sit
  on unverified geophysical anomalies that the sponsor's surface/LiDAR truth never labels
  as faults.
- **Mechanism.** **Exact directional sign flip of `r2b12`**: strips `4,518` T1 basin-floor
  dots (`67.9%` of R0's off-collar T1 dots, reducing T1 share from `17.67%` to `5.67%`
  `RECEIPT`) and places `4,518` dots onto corroborated T3 range-front/horst lineage
  ridges (`3,036` at `d ≥ 2.8 px` + `1,482` at `d ≥ 2.0 px`, raising T3 share from
  `38.01%` to `50.01%`, `0` pairs `< 2 px` `RECEIPT`). On independent off-catalogue USGS
  SGMC bedrock faults (`62,122` px `PROXY`), `b2r12` is the **only** arm that improves over
  R0 (`0.1003` vs `0.0954`, `+0.0050` / `+5.2%` `PROXY`), whereas on INGENIOUS Quaternary-heavy
  4-fold recovery it loses `−0.0113` (`0.1020` vs `0.1133`, 95% CI `[0.0523, 0.1518]` `PROXY`).
- **Non-fault mimic.** Differential erosion along tilted volcanic/ash-flow tuff cooling
  units, carbonate cliff-forming strata, intrusive stock contacts, and glacial/fluvial
  canyon walls in T3 horsts creates crisp topographic and radiometric/magnetic edges that
  mimic intra-range brittle faults.
- **Predicted live change.** **+0.005 `MODEL`** (band `−0.010` to `+0.020` `MODEL`;
  `|Δ| < 0.01` = no evidence).
- **Falsifier.** If `DTI(b2r12) − DTI(r2b12) ≤ −0.010`, withheld truth is concealed
  basin/piedmont-dominated rather than bedrock-dominated, falsifying horst enrichment; if
  both `r2b12` and `b2r12` move by `|Δ| < 0.010` across a `24 percentage-point` swing in
  T1/T3 mass (`5.67%↔29.67%` Basin, `26.01%↔50.01%` Range), `RELIEF` tercile allocation
  is non-leveraging at `12%` dose and is retired.


---

# SNAP axis — vertical-gradient dose ladder on R0 (Session 6, built 2026-10-23)

Built by `scripts/build_snap_geodetic.py`; every number in `evidence/snap_axis_vg_20261023.json`.
A **second, independent SNAP session (PR #18)** shipped the same week on a *horizontal*-gradient
driver (`scripts/build_snap.py`, cards in [`MECHANISM_CARDS_SNAP.md`](MECHANISM_CARDS_SNAP.md)).
It reached the same conclusion from a different field, which is why the SNAP family — not just
this driver — is now recommended closed.
Parent: R0 (`h33-h33-2-b2`), 37,654 unit dots, claimed 0.2778 (`CLAIM`). The prediction in
each card was fixed in `ARMS` **before** any control was computed, and is what the ledger
row carries; the post-hoc control result is reported separately and labelled as such.

## Why this field and not another

Nine SNAP rows already exist and all of them snap to a *horizontal* composite
(`tmi_hg`, `iso_grav_anom_hg`, `det_elev_slope`, `tc`). None has ever used the
**vertical-gradient** bands the sponsor supplies — `Band 9 tmi_vg` and
`Band 11 iso_grav_anom_vg`. That distinction is the whole mechanism: for a thin,
dipping magnetic/density sheet, the horizontal-gradient maximum sits *over the flank*,
offset from the surface trace by roughly the depth-to-top divided by the dip, whereas
the vertical-gradient maximum sits closest to the **top edge** of the source — i.e. nearer
to where the fault breaks the surface. If the lineage's dots are misplaced along dip
(rather than along strike), the VG crest is the field that can pull them back.

## Shared design, measured not assumed

| invariant | value | how it was held |
|---|---|---|
| dot count | 37,654 `RECEIPT` | never added, never deleted |
| catalogue collar | 2,171 → 2,171 dots at 2 < d_cat ≤ 3 px `RECEIPT` | the 2,171 inherited collar dots are **frozen**; no target cell is ever allowed at d_cat ≤ 3 px |
| spacing floor | min nearest-neighbour 2.000 px `RECEIPT` (R0: 3.735 px mean, 0 pairs < 2 px) | every target reserves a 3×3 exclusion around it; a cell within < 2 px of any finalised or still-queued dot is illegal |
| determinism | no RNG on the treatment path `RECEIPT` | row-major processing, ties to the shortest displacement |
| driver | `0.50·pct(|tmi_vg|) + 0.50·pct(|iso_grav_anom_vg|)`, percentile-ranked inside the footprint | `|.|` because VG polarity is remanence/density dependent; the crest *location* is not |
| canary | max single-band symmetric AUC 0.5793 (`geod_2ndinv`), threshold 0.90 `PROXY` | no band leaks the catalogue |

Measured on R0: the mean driver percentile at R0's own dots is **0.536**, so R0 is
already slightly better than random on this field but nowhere near its crests.

## Card — `…-SNAPvg1px-20261023-97606a78` (radius 1 px, 100 m)

- **Hypothesis.** Most of R0's positional error is smaller than one cell; a 100 m nudge
  onto the VG crest recovers kernel credit at almost no risk of jumping to a different
  structure.
- **Mechanism.** 33,807 dots (89.78 % of the field, 95.28 % of the 35,483 movable dots)
  move up to 1 px; mean displacement 0.898 px, max 1.000 px. The mean driver percentile at
  the dots rises 0.5360 → 0.5884.
- **What could mimic it.** Any smooth potential-field texture: a shallow basalt flow edge,
  an intrusive contact, a playa-margin density step, or a survey-line artefact in the
  vertical derivative all produce crests that a dot can snap to without being a fault.
- **Predicted live change (frozen, `MODEL`).** **+0.002**, range −0.004 … +0.008.
  Below the brief's 0.01 evidence bar by construction — this card is a *falsifier carrier*,
  not a candidate.
- **Falsifier.** A live change ≤ −0.004, or no separation from the random-shuffle control
  below, says the VG crest carries no positional information at 100 m and the axis is
  closed at this scale.

## Card — `…-SNAPvg2px-20261023-353a9dda` (radius 2 px, 200 m)

- **Hypothesis.** The stated physical cause of the misplacement is the survey geometry:
  GeoDAWN Area 2 was flown at 400 m line spacing, so a lineament's position is uncertain
  by roughly the kernel radius. A 200 m correction is therefore the dose that matches the
  error process, not an arbitrary one.
- **Mechanism.** 34,285 dots (91.05 %; 96.62 % of movable) move up to 2 px; mean
  displacement 1.554 px overall, 1.707 px for the dots that move, max 2.000 px. Driver
  percentile 0.5360 → 0.6142. This is the only arm that stays inside the brief's own
  "move each dot ≤ 2 px" SNAP definition *and* matches the survey error.
- **What could mimic it.** As card 1, plus: at 200 m the window reaches across a 100 m
  cell boundary, so a dot can cross from a hanging-wall scarp onto the footwall crest of
  the *adjacent* structure in a relay zone — a real fault, but the wrong one, which costs
  numerator credit while looking like a successful snap.
- **Predicted live change (frozen, `MODEL`).** **+0.003**, range −0.005 … +0.011.
- **Falsifier.** Beaten by the radius-2 random-shuffle control on any independent fault
  map (see the control section): then the treatment is not "snapping to structure", it is
  "moving dots", and the VG field is not a positional instrument.

## Card — `…-SNAPvg3px-20261023-435435a3` (radius 3 px, 300 m)

- **Hypothesis.** If the error is at the full kernel scale, the useful correction is also
  at the full kernel scale: R = 3 px is the reach at which credit is lost, so it is the
  reach at which a misplacement costs most.
- **Mechanism.** 34,635 dots (91.98 %; 97.61 % of movable) move up to 3 px; mean
  displacement 2.298 px (2.499 px for movers), max 3.000 px. Driver percentile
  0.5360 → 0.6367 — the strongest treatment in the ladder.
- **What could mimic it.** At 300 m the window spans a whole kernel: a dot can be dragged
  from a genuine fault trace onto a nearby non-fault gradient (a canyon wall, a fan toe, a
  lithological contact) and still improve the driver. This card is the one most exposed to
  that failure, and it is why it exists.
- **Predicted live change (frozen, `MODEL`).** **+0.004**, range −0.008 … +0.016.
- **Brief deviation, stated:** 3 px exceeds the brief's "move each dot ≤ 2 px" SNAP
  specification. It is logged as IR-91-31 and is the top of the dose ladder, not a
  spec-compliant candidate.
- **Falsifier.** A monotone *decrease* with dose (the mechanism gets worse the harder it is
  applied) is decisive against the field, not merely against the dose.

## The control that decides how to read all three

A fourth, **report-only** arm (`null_diagnostic` in the evidence file; no raster, no ledger
row, no slot) runs the identical radius-2 machinery with a uniformly random legal target
instead of the best driver cell: 32,157 dots moved (85.40 %), driver percentile stays at
0.5363 (i.e. it does *not* improve the field), collar unchanged at 2,171.

| file | SGMC off-catalogue DTI `PROXY` | Δ vs R0 | × the null's loss |
|---|---:|---:|---:|
| R0 | 0.09539 | — | — |
| null (random, r = 2) | 0.09406 | −0.00133 | 1.0 |
| `vg1px` | 0.09210 | −0.00326 | 2.5 |
| `vg2px` | 0.08960 | −0.00582 | 4.4 |
| `vg3px` | 0.08560 | −0.00978 | 7.4 |

USGS SGMC faults ([DS-1052](https://pubs.usgs.gov/ds/1052/), public domain) are the only
independent fault compilation this repo may read. The treatment loses **more** fault
proximity than a coin-flip shuffle of the same size, and the loss grows monotonically with
dose while the driver percentile rises monotonically too. That combination is the signature
of a field that is anti-correlated with fault position at this scale: the harder the arm
optimises it, the further the dots sit from mapped faults.

**Post-hoc reading (not pre-registered, do not confuse with the frozen predictions):** the
expected live change is therefore **negative**. The size is not measured: carrying the
control's Δ over at 1:1 gives −0.003 … −0.010, carrying it over as a relative change (live
`0.2778` against SGMC `0.0954`) gives roughly three times that, and no transfer gives zero.
Only the **sign** is robust, and it is enough: the ladder is a mechanism falsification rather
than a candidate set. Do not spend a slot expecting a
gain. A live result that *gains* despite this control would be the most informative outcome
of the session: it would say either that the withheld truth is systematically offset from
the compiled map (plausible — the map is 1:24k–1:100k compilation, the truth is a new
interpretation), or that the SGMC control is a poor guide.

## What these cards do not claim

No card claims a live score. The frozen numbers are `MODEL` projections from the metric
algebra (a dot pays iff within 2.83 px of truth; break-even credit 0.0556 at DTI 0.2778).
The catalogue hide-and-recover `PROXY` is **identically 0.006186 for all four builds
including R0** — it is structurally blind here and must not be cited as "no effect":
with the collar dots frozen and every movable dot required to stay > 3 px from the
catalogue, no reachable arrangement can change the credit on catalogue cells. See IR-91-31.
