# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (`2026-10-23` UTC):** `41 days` (`5.86` rolling 7-day weeks = `15–18` scored slots) to the **unconfirmed** `2026-12-03` deadline ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)). **Ledger:** `44` `BUILT` rows across six merged axis families (`CONCENTRATION`, `PRUNE`, `MASS`, `SPACING`, `RELIEF`, `SNAP`), `0` `SUBMITTED`, `0` live `RECEIPT`s (`R0 = 0.2778` `CLAIM`). Never use multi-account feedback; `|Δ| < 0.01` = no evidence.

## Session 5 (`arena/42de3fed-gemsdoe91`) addition: `RELIEF` (`r2p12`, `r2b12`, `b2r12`)

Restoring `training_features` (`gems-geodawn-numerical-features.tif`, sha256 `4371c82e…3bc5` `RECEIPT`) unblocked all six axes (`16/16` manifest checks pass `RECEIPT`). `RELIEF` relocates `4,518` dots (`12.00%` moved; `9,036` symmetric pixel diff = `24.00%` `RECEIPT`) at fixed count (`37,654` `RECEIPT`) and zero catalogue-collar drift (`2,171 -> 2,171` `RECEIPT`) across equal-area terciles `0.90·pct(det_elev) + 0.10·pct(det_elev_slope)`: `RELIEFr2p12` (`6ff08e5c`, `+0.006` `MODEL`), donor-twin `RELIEFr2b12` (`27443c30`, `+0.003` `MODEL`), and directional sign-flip `RELIEFb2r12` (`e1fd28d5`, `+0.005` `MODEL`, `+5.2%` off-catalogue SGMC `PROXY`, [USGS DS-1052](https://pubs.usgs.gov/ds/1052/)).

## Session 6 (`arena/9b8f7d01-gemsdoe91`) addition: `SNAP` (`s2c`, `s2q75`, `s2f`)

First SNAP build in the repo. Shared driver = bands 3 `tmi_hg` + 18 `iso_grav_anom_hg`,
600 m high-pass, 1.5 px smoothing; radius 2 px; targets `> 3 px` off-catalogue; R0's
2,171 collar dots quarantined (`0` collar drift `RECEIPT`); count fixed 37,654.
Measured dose: 2,047 / 4,495 / 35,174 dots moved, mean displacement 0.080 / 0.237 / 1.733 px.

**The axis fails its control.** The catalogue PROXY cannot move by construction (targets
floored at 3 px; only the quarantined collar sits closer, IR-91-28), so the only independent
locator is the off-catalogue USGS SGMC map, and there the sign is negative and grows with dose
(`+0.00008`, `−0.00234`, `−0.00926` ΔDTI). With `DTI = T/(0.2T + 0.2(S−M) + 0.8|G|)`, a live
`+0.01` needs `ΔT/T ≈ +3.6 %`; the arms deliver `+0.08 %`, `−2.5 %`, `−9.8 %` on SGMC.

| id | rule | `MODEL` prediction | what the receipt would change |
|---|---|---|---|
| `…-SNAPs2c-…-86b27de1` | 3×3 crest, 5.44 % moved | **+0.000** `[−0.006,+0.006]` | `≥ +0.006`: local crests carry locational signal → raise the dose in Week 2. `≤ −0.006`: gradient crests sit off-trace at this scale → retire SNAP. |
| `…-SNAPs2q75-…-8aa75390` | window max, gain ≥ p75, 11.94 % | **−0.004** `[−0.012,+0.005]` | Beating `s2c` by `≥ +0.006` would mean the negative SGMC signal is a mapped-fault artefact; otherwise it confirms the control. |
| `…-SNAPs2f-…-c2391234` | full window max, 93.41 % moved | **−0.014** `[−0.028,+0.004]` | Pre-registered extreme: a re-layout, not a snap (IR-91-29). Live `≥ 0` would refute the SGMC transfer for new faults; `≈ −0.014` retires SNAP. |

**Slot guidance:** SNAP stays out of the top 3. If the human wants an axis-retirement test, spend
one slot on `s2c` (predicted no change); `s2f` is a negative control, not a slot candidate.
The three arms are one dose-response experiment — do not spend three slots on them.

## Session 6b (`arena/f8d67617-gemsdoe91`) — `SNAP` on the `|VG|` crest: a second, independent SNAP build, also negative

PR #18 used a high-passed **horizontal**-gradient driver over a *quantile* ladder (5.4 / 11.9 / 93.4 % of dots). This session used the **vertical**-gradient bands (`|Band 9 tmi_vg|`, `|Band 11 iso_grav_anom_vg|`), which no SNAP row had ever used, over a **radius** ladder: every movable dot moves ≤ 1 / 2 / 3 px (Euclidean) to the crest. Same parent, same count `37,654`, collar `2,171 → 2,171`, spacing floor `2.000 px`, both gate suites PASS (`evidence/snap_axis_vg_20261023.json`).

| id | r | moved | mean disp | driver pct | SGMC Δ `PROXY` | frozen `MODEL` |
|---|---:|---:|---:|---|---:|---|
| `…-SNAPvg1px-20261023-97606a78` | 1 px | 89.78 % | 0.898 px | 0.536→0.588 | −0.0033 | +0.002 |
| `…-SNAPvg2px-20261023-353a9dda` | 2 px | 91.05 % | 1.554 px | 0.536→0.614 | −0.0058 | +0.003 |
| `…-SNAPvg3px-20261023-435435a3` | 3 px | 91.98 % | 2.298 px | 0.536→0.637 | −0.0098 | +0.004 |

**The control PR #18 did not have:** an identical r = 2 pass with a **random** legal target (no driver) moves 85.40 % of dots and costs only **−0.0013** on SGMC. So the VG treatment loses 2.5 / 4.4 / 7.4× more fault proximity than a coin flip at r = 1 / 2 / 3, monotonically with dose, while its own driver objective improves monotonically. A field that gets better at its own objective while getting worse on every independent fault map is not a positional instrument at this scale.

**Consequence for the plan:** two independent SNAP sessions, two different drivers and two different dose parametrisations, both at or below R0 and both losing on SGMC. **SNAP is retired as an axis**, not re-dosed; `SNAPvg2px`/`SNAPs2c` stay available only as axis-retirement tests. The interesting follow-up is not another SNAP arm but the *sign flip* of this one (proposed axis 4 below).

## Next 3 scored slots in order (Week 1: one orthogonal axis per slot)

| Slot | Candidate (`releases/`) | Dots (`RECEIPT`) | Pred. `Δ` (`MODEL`) | What the live receipt changes |
|---:|---|---:|---|---|
| **1** | `…-CONCENTRATIONgdr25rm10-20261023-c19adb01.tif` *(or R0 anchor if `baeae321…` has no receipt yet)* | 37,654 | **+0.0123** `[-0.022,+0.037]` | Highest-upside external thermal prior. `Δ ≥ +0.010`: prior transfer works -> test `15–20%` dose in Week 2. `Δ ≤ -0.010`: macro block-relayout costs structural recall -> retire `CONCENTRATION`. |
| **2** | `h33-h33-2-b2-PRUNE-le10-norefill-20261023-04002dae.tif` | 26,294 | **+0.008** `[-0.006,+0.019]` | Collar-exempt (`AXIS=PRUNE`) denominator-cost test. `Δ ≥ +0.010`: rebase Week 2 winners onto pruned parent (`le10`/`le15`). `|Δ| < 0.010`: retire `PRUNE`. |
| **3** | `h33-h33-2-b2-RELIEFr2p12-20261023-6ff08e5c.tif` *(swap in `MASScons3add` `2803126d`, `+0.009` `MODEL`, if testing count expansion first)* | 37,654 | **+0.006** `[-0.006,+0.018]` | Tests concealed piedmont-toe scarp enrichment (`-0.0017` 4-fold INGENIOUS `PROXY`, [GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)) at zero collar drift. `Δ ≥ +0.010`: test donor-twin `RELIEFr2b12` (`27443c30`) in Week 2; `Δ ≤ -0.010`: flip to bedrock `RELIEFb2r12` (`e1fd28d5`). |

## Rolling budget to deadline (`5.86` weeks remaining)

- **Week 1 (slots 1–3):** Anchor R0 receipt (cost 0 if already held, else Slot 1) + test 1 prior axis (`CONCENTRATION`), 1 mass/collar axis (`PRUNE`), and 1 terrain-regime axis (`RELIEF` or `MASScons3add`).
- **Week 2 (slots 4–6):** Bracket any Week-1 `≥ +0.010` `RECEIPT` winner (`RELIEFb2r12` vs `RELIEFr2b12`, `MASScons3add`, or top proposed axis below).
- **Weeks 3–4 (slots 7–12):** Compose two orthogonal `≥ +0.010` `RECEIPT` winners one step at a time onto a receipted parent.
- **Weeks 5–6 (slots 13–18 + 1 blind final):** Re-verify best receipted build + conservative fallback (`-zeros` / R0) on disk; pick **one** blind final file before `2026-12-03`.

4. **`SNAP-2` — downdip-offset crest snap (`sign-flipped` SNAP)**
   - **Mechanism:** SNAP failed its control because a horizontal-gradient maximum sits *downdip*
     of the fault trace when the source dips or is magnetised (upward continuation); the session's
     monotone negative SGMC response is exactly what that offset predicts. If the offset is real,
     moving dots 1-2 px **away** from the crest, toward the basin, should recover credit where
     moving onto the crest lost it.
   - **Confounder:** the offset varies with dip (40-65 deg) and depth to basement, so a constant
     shift over-corrects on steep, shallow sources; pixel noise maxima are still in the driver.
   - **Falsifier:** a 10 % / 20 % downdip-shift ladder (count fixed, collar quarantined) that does
     not beat `SNAPs2c` (`86b27de1`) by `>= +0.006` on the off-catalogue SGMC control and is not
     `>= +0.010` live — then the gradient field is simply a worse locator and SNAP is closed.

## Proposed better axes (not built this session; all inputs now verified)

1. **`GEODETIC-STRAIN CONCENTRATION` (`Band 4 geod_2ndinv` + `Band 7 geod_shearrate`)**
   - **Mechanism:** Active transtensional shear maintains dilational geothermal permeability and unmapped Quaternary splays ([GBCGE INGENIOUS](https://gbcge.org/current-projects/ingenious/)); `geod_2ndinv` (`0.5793` `PROXY`) and `geod_shearrate` (`0.5761` `PROXY`) lead all 19 GeoDAWN bands on fault separation.
   - **Confounder:** ~50 km GPS station spacing smears strain across adjacent aseismic blocks.
   - **Falsifier:** Moving 20% of R0 mass into top-tercile `geod_2ndinv × S_struct` yields `Δ < +0.010` live vs R0.
2. **`SEDIMENT-DEPTH KERNEL BRACKETING` (`Band 15 depth_to_base_surf`-gated lateral pairing)**
   - **Mechanism:** Upward continuation through `>500 m` Cenozoic basin fill shifts gravity/magnetic gradient crests downdip of dipping normal fault surface traces, missing DTI's `300 m` kernel unless bracketed (`±200 m`).
   - **Confounder:** Variable listric fault dip (`40°–65°`) creates asymmetric hanging-wall offset.
   - **Falsifier:** Depth-bracketed basin dots fail to beat `RELIEFr2b12` (`27443c30`) by `≥ +0.010` live.
3. **`THERMAL-ANOMALY DILATIONAL GATING` (`Band 16 ieq_n100a15` × lineage terminations)**
   - **Mechanism:** Blind geothermal systems localize at fault tips/step-overs with elevated conductive temperature (`ieq_n100a15` AUC `0.5749` `PROXY`, [DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)).
   - **Confounder:** Shallow groundwater outflow plumes advect heat `2–8 km` down-gradient off the fault conduit.
   - **Falsifier:** Thermal-gated step-over reallocation scores `≤` isothermal `RELIEFr2p12` (`6ff08e5c`).

4. **`SNAP-ANTI` — the sign flip of the session-6b treatment (`|VG|` *minimum*, r = 2 px)**
   - **Mechanism:** the vertical-gradient crest was 2.5–7.4× *worse* than a random shuffle on the only independent fault map available (USGS SGMC), monotonically with dose. If that control is even roughly right, the lineage's dots sit deliberately *between* geophysical crests — consistent with a thick-zone or deeply dipping source whose surface trace is offset from the potential-field maximum — so moving dots *away* from crests should recover credit.
   - **Confounder:** the control could be wrong in the same direction at every dose; a gain would then only mean "the SGMC map prefers flatter gradients".
   - **Falsifier:** `SNAP-ANTI` failing to beat `vg2px` by ≥ +0.005 live, with both receipts in hand, retires the whole VG family rather than escalating it.
