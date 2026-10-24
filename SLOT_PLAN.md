# SLOT PLAN — 1 entity, 3 scored slots / rolling week, 1 blind final pick

**Calendar (`2026-10-24` UTC):** `40 days` (`5.71` rolling 7-day weeks = `15–18` scored slots if none has been spent yet) to the **unconfirmed** `2026-12-03` deadline ([DrivenData #306](https://www.drivendata.org/competitions/306/gems-geothermal-fault-mapping/)). **Ledger:** `50` `BUILT` rows across seven axis families (`CONCENTRATION`, `PRUNE`, `MASS`, `SPACING`, `RELIEF`, `SNAP`, `TRACKB`), `0` `SUBMITTED`, `0` live `RECEIPT`s (`R0 = 0.2778` `CLAIM`). Never use multi-account feedback; `|Δ| < 0.01` = no evidence.

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

## Session 8 (`arena/6f079276-gemsdoe91`) addition: `CONCENTRATION` geodetic-strain prior (`strn25m10`, `strn25m20`, `strd25m10`)

Implements pre-proposed better-axis #1 below (sponsor bands 4/7/8, percentile ranks,
same builder/settings as the GDR arms, donors collar-quarantined per IR-91-27/33;
`docs/MECHANISM_CARDS_STRAIN.md`, `evidence/strain_concentration_20261024.json`).
**All three arms are predicted negative under the frozen SGMC translator, dose-monotone:**
`strn25m10` (`85cc49d2`, **−0.0056** `MODEL`), `strn25m20` (`a88ce2c2`, **−0.0200**),
`strd25m10` (`106e87d9`, **−0.0152`). Calibrated controls (`reports/strain_control_diagnostics_20261024.json`):
the same operation under a random prior costs −0.0040 and under the GDR priors only
−0.0009/−0.0024 (`PROXY`) — strain is worse than random relocation on the off-catalogue
map, and the catalogue's strain-decile rise does not replicate on SGMC-only faults
(IR-91-35). Per the session's preregistered slot rule (strain takes slot 3 only at
predicted ≥ +0.010), **the Week-1 queue below is unchanged.** Strain joins SNAP as a
reserve retirement test: at most one slot, `strn25m10`, and only if the GDR slot-1
receipt first discredits the SGMC translator for concentration edits generally.
What the receipt would change: `strn25m10` ≥ +0.010 live ⇒ SGMC transfer fails for
block priors and province-scale priors reopen; ≤ −0.006 ⇒ the geodetic-prior family
(incl. the literal `geod_2ndinv x S_struct` form, IR-91-34) is retired without
spending slots on `strn25m20`/`strd25m10`.

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

1. ~~**`GEODETIC-STRAIN CONCENTRATION`**~~ (`Band 4 geod_2ndinv` + `Band 7 geod_shearrate`) — **BUILT Session 8** (`strn25m10`/`strn25m20`/`strd25m10`, all predicted negative; do not rebuild; IR-91-34/35)
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

4. **`STRAIN-SURPLUS CONCENTRATION`** (not built; Session 8 proposal)
   - **Mechanism:** interseismic strain must be released on structures; blocks whose geodetic strain percentile is high *relative to what the block's catalogue fault density can account for* (spatially held-out residual of block strain on block catalogue density) are where the missing structures should be — the strain budget the map has not yet spent.
   - **Confounder:** mapping completeness is heterogeneous (quadrangle vintage, access, cover), so "surplus" may map under-mapping, not under-faulting; the residual is also partly a re-statement of catalogue sparsity, and acceptor anchoring must not re-import the parent field (IR-91-07).
   - **Falsifier:** before any build, the residual prior's SGMC-off decile profile is flat or falling (`PROXY` screen, IR-91-35); or a built 10% arm scores `Δ < +0.010` live. Only admissible after a CONCENTRATION receipt exists, so the operation itself is not re-tested at the same time.

## Session 7 (`arena/0ed37053-gemsdoe91`) addition: `TRACKB` (Phase 2 only — does NOT change the queue above)

Three count-fixed trace-densification arms built and gated (`8343ab38` t1k10 `+0.004` MODEL, `ab72339b` t1k20 `+0.005`, `6d16fd7a` t2k10 `+0.002`), each with a GeoJSON of >=1 km strike-consistent traces carrying one evidence paragraph per trace (2,214 / 2,214 / 675 traces). They spend **no** weekly slot unless the human decides; their value is Phase-2 expert review. Spacing confound and invariant PROXY: IR-91-31. What would change this: a human ruling that Phase-2 trace review outweighs a weekly DTI read, in which case `t1k10` goes first (lowest dose, full trace set).
